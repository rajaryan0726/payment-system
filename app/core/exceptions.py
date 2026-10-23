from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class PaymentServiceException(HTTPException):
    """Base exception for all domain errors within BHIV Payment Service."""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(
            status_code=status_code,
            detail={
                "error": {
                    "code": error_code,
                    "message": message,
                    "details": self.details,
                }
            },
        )


class AuthenticationError(PaymentServiceException):
    def __init__(self, message: str = "Invalid or missing client credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_FAILED",
            message=message,
        )


class AuthorizationError(PaymentServiceException):
    def __init__(self, message: str = "Client not authorized to access this resource"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
            message=message,
        )


class ResourceNotFoundError(PaymentServiceException):
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            message=f"{resource_type} with ID '{resource_id}' was not found.",
            details={"resource_type": resource_type, "resource_id": resource_id},
        )


class IdempotencyConflictError(PaymentServiceException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="IDEMPOTENCY_CONFLICT",
            message=message,
            details=details,
        )


class InvalidStateTransitionError(PaymentServiceException):
    def __init__(self, current_status: str, attempted_status: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="INVALID_STATE_TRANSITION",
            message=f"Cannot transition payment from '{current_status}' to '{attempted_status}'.",
            details={"current_status": current_status, "attempted_status": attempted_status},
        )


class ProviderError(PaymentServiceException):
    def __init__(self, message: str, provider_error_code: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="PROVIDER_ERROR",
            message=f"Downstream payment provider error: {message}",
            details={"provider_code": provider_error_code} if provider_error_code else {},
        )


class SignatureVerificationError(PaymentServiceException):
    def __init__(self, message: str = "Signature verification failed"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_SIGNATURE",
            message=message,
        )


class RefundValidationError(PaymentServiceException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="REFUND_VALIDATION_FAILED",
            message=message,
            details=details,
        )
