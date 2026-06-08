"""
FastAPI application entrypoint.
Configures middleware, exception handlers, routers, and startup events.
"""
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any
from prometheus_client import make_asgi_app
import traceback
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import (
    AuthorizationError,
    DocumentNotFoundError,
    ERPAssistantError,
    RateLimitError,
)
from app.core.logging import bind_request_context, clear_request_context, get_logger, setup_logging
from app.db.session import create_tables
from app.observability.metrics import APP_INFO, HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL

settings = get_settings()
logger = get_logger(__name__)


# =============================================================================
# Application Lifecycle
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # ---- Startup ----
    setup_logging(
        log_level="DEBUG" if settings.debug else "INFO",
        json_logs=settings.is_production,
    )

    APP_INFO.info({
        "name": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
    })

    logger.info(
        "application_starting",
        name=settings.app_name,
        version=settings.app_version,
        env=settings.app_env,
    )

    await create_tables()
    logger.info("database_tables_ready")

    yield

    # ---- Shutdown ----
    logger.info("application_shutting_down")


# =============================================================================
# Application Instance
# =============================================================================

app = FastAPI(
    title=settings.app_name,
    description=(
        "Production-grade AI ERP Assistant with multi-agent RAG orchestration, "
        "conversational memory, and streaming responses."
    ),
    version=settings.app_version,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()

    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "type": type(exc).__name__,
        },
    )

# =============================================================================
# Middleware
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next) -> Response:
    """
    Per-request middleware that:
    - Assigns a unique request ID
    - Binds structured log context
    - Records Prometheus HTTP metrics
    - Injects X-Request-ID into response headers
    """
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    bind_request_context(
        request_id=request_id,
        path=request.url.path,
        method=request.method,
    )

    start_time = time.monotonic()

    try:
        response: Response = await call_next(request)
        status_code = response.status_code
    except Exception:
        import traceback
        traceback.print_exc()

        status_code = 500
        raise
    finally:
        latency = time.monotonic() - start_time

        # Prometheus metrics
        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            path=request.url.path,
            status_code=str(status_code),
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=request.method,
            path=request.url.path,
        ).observe(latency)

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            latency_ms=round(latency * 1000, 2),
            request_id=request_id,
        )

        clear_request_context()

    response.headers["X-Request-ID"] = request_id
    return response


# =============================================================================
# Exception Handlers
# =============================================================================

@app.exception_handler(RateLimitError)
async def rate_limit_handler(request: Request, exc: RateLimitError) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": exc.message, "code": exc.code},
        headers={"Retry-After": str(settings.rate_limit_window)},
    )


@app.exception_handler(DocumentNotFoundError)
async def document_not_found_handler(request: Request, exc: DocumentNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"detail": exc.message, "code": exc.code},
    )


@app.exception_handler(AuthorizationError)
async def auth_error_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={"detail": exc.message, "code": exc.code},
    )


@app.exception_handler(ERPAssistantError)
async def app_error_handler(request: Request, exc: ERPAssistantError) -> JSONResponse:
    logger.error(
        "application_error",
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": exc.message, "code": exc.code, "details": exc.details},
    )


# =============================================================================
# Routes
# =============================================================================

app.include_router(api_router, prefix=settings.api_v1_prefix)

# Expose Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health", tags=["Health"], include_in_schema=False)
async def health_check() -> dict[str, Any]:
    """Lightweight liveness probe."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }