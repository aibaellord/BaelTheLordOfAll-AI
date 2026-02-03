"""
Comprehensive error handling and response utilities for BAEL API.
Provides consistent error responses, logging, and recovery mechanisms.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger("BAEL.ErrorHandler")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    suggestion: Optional[str] = None


class ValidationError(HTTPException):
    """Validation error with user-friendly message."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ErrorResponse(
                error="ValidationError",
                code="VALIDATION_FAILED",
                message=message,
                details=details,
                suggestion="Please check your input parameters and try again."
            ).dict()
        )
        logger.warning(f"Validation error: {message}")


class NotFoundError(HTTPException):
    """Resource not found error."""
    def __init__(self, resource: str, identifier: str):
        message = f"{resource} not found: {identifier}"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error="NotFoundError",
                code="RESOURCE_NOT_FOUND",
                message=message,
                suggestion=f"Please verify the {resource} identifier and try again."
            ).dict()
        )
        logger.info(f"Resource not found: {resource} {identifier}")


class UnauthorizedError(HTTPException):
    """Unauthorized access error."""
    def __init__(self, message: str = "Unauthorized access"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                error="UnauthorizedError",
                code="UNAUTHORIZED",
                message=message,
                suggestion="Please authenticate and try again."
            ).dict()
        )
        logger.warning(f"Unauthorized access attempt: {message}")


class ForbiddenError(HTTPException):
    """Forbidden access error."""
    def __init__(self, message: str = "Forbidden access"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ErrorResponse(
                error="ForbiddenError",
                code="FORBIDDEN",
                message=message,
                suggestion="You do not have permission to access this resource."
            ).dict()
        )
        logger.warning(f"Forbidden access attempt: {message}")


class ConflictError(HTTPException):
    """Conflict error (e.g., duplicate resource)."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=ErrorResponse(
                error="ConflictError",
                code="CONFLICT",
                message=message,
                details=details,
                suggestion="A resource with this identifier may already exist."
            ).dict()
        )
        logger.warning(f"Conflict: {message}")


class InternalServerError(HTTPException):
    """Internal server error with logging."""
    def __init__(self, message: str, error: Optional[Exception] = None):
        if error:
            logger.error(f"Internal server error: {message}", exc_info=error)
        else:
            logger.error(f"Internal server error: {message}")

        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="InternalServerError",
                code="INTERNAL_ERROR",
                message="An unexpected error occurred",
                details={"original_message": message} if error else None,
                suggestion="Please try again later or contact support if the problem persists."
            ).dict()
        )


class ServiceUnavailableError(HTTPException):
    """Service unavailable error."""
    def __init__(self, service: str = "BAEL"):
        message = f"{service} is not initialized or unavailable"
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error="ServiceUnavailableError",
                code="SERVICE_UNAVAILABLE",
                message=message,
                suggestion="The service is temporarily unavailable. Please try again in a moment."
            ).dict()
        )
        logger.warning(f"Service unavailable: {service}")


def wrap_operation(operation_name: str):
    """Decorator to wrap operations with error handling."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error in {operation_name}: {str(e)}", exc_info=e)
                raise InternalServerError(f"Failed to {operation_name}", e)
        return wrapper
    return decorator


def log_and_respond(status_code: int, message: str, code: str, details: Optional[Dict] = None, suggestion: Optional[str] = None):
    """Create a standardized error response with logging."""
    logger.error(f"[{code}] {message}")
    raise HTTPException(
        status_code=status_code,
        detail=ErrorResponse(
            error=code.split("_")[0],
            code=code,
            message=message,
            details=details,
            suggestion=suggestion or "Please try again or contact support."
        ).dict()
    )
