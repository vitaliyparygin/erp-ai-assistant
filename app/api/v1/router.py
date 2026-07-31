"""V1 API router — aggregates all endpoint modules."""

from fastapi import APIRouter

from app.api.v1 import chat, conversations, documents, health

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(
    conversations.router, prefix="/conversations", tags=["Conversations"]
)
