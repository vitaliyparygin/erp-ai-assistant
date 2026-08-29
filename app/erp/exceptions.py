"""
Exception hierarchy for the ERP integration layer.

Rooted under the application's existing ``ERPAssistantError`` so the
catch-all exception handler already registered in app.main continues to
cover ERP errors without any changes to app/main.py. Concrete connector
implementations (e.g. a future Odoo connector) are responsible for
translating vendor-specific errors into this hierarchy.
"""

from typing import Any

from app.core.exceptions import ERPAssistantError


class ERPError(ERPAssistantError):
    """Base exception for all ERP integration errors."""


class ERPConnectionError(ERPError):
    """Raised when the ERP connector cannot reach the ERP system."""

    status_code = 503


class ERPAuthenticationError(ERPError):
    """Raised when authentication with the ERP system fails."""

    status_code = 401


class ERPNotFoundError(ERPError):
    """Raised when a requested ERP entity does not exist."""

    status_code = 404

    def __init__(
        self,
        message: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged_details = dict(details or {})
        if entity_type is not None:
            merged_details.setdefault("entity_type", entity_type)
        if entity_id is not None:
            merged_details.setdefault("entity_id", entity_id)
        super().__init__(message, code=code, details=merged_details)


class ERPValidationError(ERPError):
    """Raised when data sent to or received from the ERP system is invalid."""

    status_code = 422


class ERPOperationError(ERPError):
    """Raised when an ERP operation fails for a reason not covered above."""

    status_code = 502
