"""
Custom Exception Classes for PM Document Intelligence.

This module defines custom exception classes for different error scenarios
throughout the application. Each exception includes proper HTTP status codes,
user-friendly messages, and structured error details.

Features:
- Domain-specific exception types
- HTTP status code mapping
- User-friendly error messages
- Structured error details for debugging
- Error tracking integration
- Consistent error response format

Usage:
    from app.utils.exceptions import DocumentProcessingError, ValidationError

    if not document.is_valid():
        raise ValidationError(
            message="Invalid document format",
            details={"format": document.format}
        )
"""

from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class BaseAPIException(HTTPException):
    """
    Base exception class for all API exceptions.

    All custom exceptions should inherit from this class to ensure
    consistent error handling and response formatting.

    Attributes:
        status_code: HTTP status code
        message: User-friendly error message
        error_code: Application-specific error code
        details: Additional error details
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"
    message: str = "An internal error occurred"

    def __init__(
        self,
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
    ):
        """
        Initialize base API exception.

        Args:
            message: Custom error message
            error_code: Custom error code
            details: Additional error details
            status_code: HTTP status code override
        """
        self.message = message or self.message
        self.error_code = error_code or self.error_code
        self.details = details or {}
        if status_code:
            self.status_code = status_code

        super().__init__(
            status_code=self.status_code,
            detail=self.to_dict(),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary format.

        Returns:
            Dictionary representation of the error
        """
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
                "status_code": self.status_code,
            }
        }


class DocumentProcessingError(BaseAPIException):
    """
    Exception raised when document processing fails.

    This exception is used for errors during document upload, parsing,
    OCR, or any other document processing operations.

    Examples:
        - Unsupported file format
        - Corrupted document
        - OCR failure
        - Document too large
        - Processing timeout
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "DOCUMENT_PROCESSING_ERROR"
    message = "Failed to process document"


class DocumentNotFoundError(BaseAPIException):
    """
    Exception raised when a requested document cannot be found.

    This exception is used when a document ID doesn't exist in the
    database or storage system.
    """

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "DOCUMENT_NOT_FOUND"
    message = "Document not found"


class DocumentTooLargeError(BaseAPIException):
    """
    Exception raised when an uploaded document exceeds size limits.

    This exception is used to enforce maximum file size restrictions
    for document uploads.
    """

    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    error_code = "DOCUMENT_TOO_LARGE"
    message = "Document exceeds maximum allowed size"


class UnsupportedDocumentFormatError(BaseAPIException):
    """
    Exception raised when document format is not supported.

    This exception is used when a user uploads a file type that
    the system cannot process.
    """

    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    error_code = "UNSUPPORTED_DOCUMENT_FORMAT"
    message = "Document format is not supported"


class AIServiceError(BaseAPIException):
    """
    Exception raised when an AI service (Bedrock, OpenAI, etc.) fails.

    This exception is used for errors during communication with
    external AI services or when AI operations fail.

    Examples:
        - API rate limit exceeded
        - Service timeout
        - Invalid API response
        - Model not available
        - Token limit exceeded
    """

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "AI_SERVICE_ERROR"
    message = "AI service is temporarily unavailable"


class BedrockError(AIServiceError):
    """Exception raised for AWS Bedrock-specific errors."""

    error_code = "BEDROCK_ERROR"
    message = "AWS Bedrock service error"


class OpenAIError(AIServiceError):
    """Exception raised for OpenAI API errors."""

    error_code = "OPENAI_ERROR"
    message = "OpenAI API error"


class TextractError(AIServiceError):
    """Exception raised for AWS Textract errors."""

    error_code = "TEXTRACT_ERROR"
    message = "AWS Textract service error"


class ComprehendError(AIServiceError):
    """Exception raised for AWS Comprehend errors."""

    error_code = "COMPREHEND_ERROR"
    message = "AWS Comprehend service error"


class TokenLimitExceededError(AIServiceError):
    """Exception raised when token limit is exceeded."""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "TOKEN_LIMIT_EXCEEDED"
    message = "Request exceeds maximum token limit"


class AuthenticationError(BaseAPIException):
    """
    Exception raised for authentication failures.

    This exception is used when authentication credentials are
    invalid, missing, or expired.

    Examples:
        - Invalid credentials
        - Missing authentication token
        - Expired token
        - Invalid API key
        - Unauthorized access
    """

    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "AUTHENTICATION_ERROR"
    message = "Authentication failed"

    def __init__(
        self,
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
    ):
        """Initialize authentication error with WWW-Authenticate header."""
        super().__init__(message, error_code, details, status_code)
        self.headers = {"WWW-Authenticate": "Bearer"}


class InvalidCredentialsError(AuthenticationError):
    """Exception raised when credentials are invalid."""

    error_code = "INVALID_CREDENTIALS"
    message = "Invalid username or password"


class TokenExpiredError(AuthenticationError):
    """Exception raised when authentication token has expired."""

    error_code = "TOKEN_EXPIRED"
    message = "Authentication token has expired"


class InvalidTokenError(AuthenticationError):
    """Exception raised when authentication token is invalid."""

    error_code = "INVALID_TOKEN"
    message = "Invalid authentication token"


class AuthorizationError(BaseAPIException):
    """
    Exception raised for authorization failures.

    This exception is used when an authenticated user attempts to
    access a resource they don't have permission for.

    Examples:
        - Insufficient permissions
        - Resource access denied
        - Operation not allowed
    """

    status_code = status.HTTP_403_FORBIDDEN
    error_code = "AUTHORIZATION_ERROR"
    message = "You don't have permission to access this resource"


class InsufficientPermissionsError(AuthorizationError):
    """Exception raised when user lacks required permissions."""

    error_code = "INSUFFICIENT_PERMISSIONS"
    message = "Insufficient permissions for this operation"


class RateLimitError(BaseAPIException):
    """
    Exception raised when rate limit is exceeded.

    This exception is used to enforce API rate limiting and prevent
    abuse. It includes retry-after information for the client.

    Examples:
        - Too many requests per minute
        - API quota exceeded
        - Service overload protection
    """

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "RATE_LIMIT_EXCEEDED"
    message = "Rate limit exceeded. Please try again later."

    def __init__(
        self,
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
        retry_after: Optional[int] = None,
    ):
        """
        Initialize rate limit error.

        Args:
            message: Custom error message
            error_code: Custom error code
            details: Additional error details
            status_code: HTTP status code override
            retry_after: Seconds until retry is allowed
        """
        super().__init__(message, error_code, details, status_code)
        self.retry_after = retry_after or 60
        self.headers = {"Retry-After": str(self.retry_after)}


class ValidationError(BaseAPIException):
    """
    Exception raised for request validation failures.

    This exception is used when request data doesn't meet validation
    requirements or contains invalid values.

    Examples:
        - Missing required fields
        - Invalid field format
        - Value out of range
        - Type mismatch
        - Invalid enum value
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "VALIDATION_ERROR"
    message = "Request validation failed"


class InvalidParameterError(ValidationError):
    """Exception raised when a parameter value is invalid."""

    error_code = "INVALID_PARAMETER"
    message = "Invalid parameter value"


class MissingParameterError(ValidationError):
    """Exception raised when a required parameter is missing."""

    error_code = "MISSING_PARAMETER"
    message = "Required parameter is missing"


class StorageError(BaseAPIException):
    """
    Exception raised for storage operations failures.

    This exception is used when file storage operations (S3, local
    filesystem, etc.) fail.

    Examples:
        - Failed to upload file
        - Failed to download file
        - Storage quota exceeded
        - Storage service unavailable
        - File not found in storage
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "STORAGE_ERROR"
    message = "Storage operation failed"


class S3Error(StorageError):
    """Exception raised for AWS S3 errors."""

    error_code = "S3_ERROR"
    message = "AWS S3 storage error"


class StorageQuotaExceededError(StorageError):
    """Exception raised when storage quota is exceeded."""

    status_code = status.HTTP_507_INSUFFICIENT_STORAGE
    error_code = "STORAGE_QUOTA_EXCEEDED"
    message = "Storage quota exceeded"


class DatabaseError(BaseAPIException):
    """
    Exception raised for database operations failures.

    This exception is used when database operations fail or
    data integrity issues are detected.

    Examples:
        - Connection failure
        - Query timeout
        - Constraint violation
        - Deadlock detected
        - Data integrity error
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "DATABASE_ERROR"
    message = "Database operation failed"


class NotFoundError(BaseAPIException):
    """Generic exception for resource not found."""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"
    message = "Resource not found"


class RecordNotFoundError(DatabaseError):
    """Exception raised when a database record is not found."""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "RECORD_NOT_FOUND"
    message = "Requested record not found"


class DuplicateRecordError(DatabaseError):
    """Exception raised when attempting to create a duplicate record."""

    status_code = status.HTTP_409_CONFLICT
    error_code = "DUPLICATE_RECORD"
    message = "Record already exists"


class VectorSearchError(BaseAPIException):
    """
    Exception raised for vector search operations failures.

    This exception is used when vector database operations or
    similarity searches fail.

    Examples:
        - Embedding generation failure
        - Vector database unavailable
        - Invalid query vector
        - Index not found
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "VECTOR_SEARCH_ERROR"
    message = "Vector search operation failed"


class EmbeddingError(VectorSearchError):
    """Exception raised when embedding generation fails."""

    error_code = "EMBEDDING_ERROR"
    message = "Failed to generate embeddings"


class ConfigurationError(BaseAPIException):
    """
    Exception raised for configuration errors.

    This exception is used when the application is misconfigured
    or required configuration is missing.

    Examples:
        - Missing environment variable
        - Invalid configuration value
        - Required service not configured
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "CONFIGURATION_ERROR"
    message = "Application configuration error"


class FeatureNotEnabledError(BaseAPIException):
    """
    Exception raised when accessing a disabled feature.

    This exception is used when a user attempts to use a feature
    that is disabled via feature flags.
    """

    status_code = status.HTTP_501_NOT_IMPLEMENTED
    error_code = "FEATURE_NOT_ENABLED"
    message = "This feature is not currently enabled"


class ServiceUnavailableError(BaseAPIException):
    """
    Exception raised when a service is temporarily unavailable.

    This exception is used for planned maintenance, service overload,
    or temporary outages.
    """

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "SERVICE_UNAVAILABLE"
    message = "Service is temporarily unavailable"


class ServiceError(BaseAPIException):
    """
    Generic exception for external service errors.

    This exception is used when an external service (PubNub, AWS, etc.)
    encounters an error.
    """

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "SERVICE_ERROR"
    message = "External service error"


# Exception handler for FastAPI
async def api_exception_handler(request: Request, exc: BaseAPIException) -> JSONResponse:
    """
    Global exception handler for API exceptions.

    This handler catches all BaseAPIException instances and returns
    a consistent JSON error response.

    Args:
        request: FastAPI request object
        exc: Exception instance

    Returns:
        JSON response with error details
    """
    from app.utils.logger import get_logger

    logger = get_logger(__name__)

    # Log the exception
    logger.error(
        f"API Exception: {exc.error_code}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )

    # Build response
    response_data = exc.to_dict()

    # Add request context
    if hasattr(request.state, "request_id"):
        response_data["request_id"] = request.state.request_id

    # Create response with headers
    headers = getattr(exc, "headers", {})

    return JSONResponse(
        status_code=exc.status_code,
        content=response_data,
        headers=headers,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unexpected exceptions.

    This handler catches all unexpected exceptions and returns a
    generic error response without exposing internal details.

    Args:
        request: FastAPI request object
        exc: Exception instance

    Returns:
        JSON response with generic error message
    """
    from app.utils.logger import get_logger

    logger = get_logger(__name__)

    # Log the exception with full details
    logger.error(
        f"Unhandled Exception: {type(exc).__name__}",
        extra={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )

    # Build generic response (don't expose internal details)
    response_data = {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An internal error occurred. Please try again later.",
            "status_code": 500,
        }
    }

    # Add request context
    if hasattr(request.state, "request_id"):
        response_data["request_id"] = request.state.request_id

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_data,
    )


def setup_exception_handlers(app) -> None:
    """
    Setup exception handlers for FastAPI application.

    Args:
        app: FastAPI application instance
    """
    from fastapi import FastAPI

    if isinstance(app, FastAPI):
        # Register custom exception handler
        app.add_exception_handler(BaseAPIException, api_exception_handler)

        # Register generic exception handler for unexpected errors
        app.add_exception_handler(Exception, generic_exception_handler)

        from app.utils.logger import get_logger

        logger = get_logger(__name__)
        logger.info("Exception handlers configured successfully")


# Convenience functions for common error scenarios
def raise_document_not_found(document_id: str) -> None:
    """
    Raise DocumentNotFoundError with document ID.

    Args:
        document_id: Document identifier
    """
    raise DocumentNotFoundError(
        message=f"Document with ID '{document_id}' not found",
        details={"document_id": document_id},
    )


def raise_unsupported_format(file_format: str, supported_formats: list[str]) -> None:
    """
    Raise UnsupportedDocumentFormatError with format details.

    Args:
        file_format: Unsupported file format
        supported_formats: List of supported formats
    """
    raise UnsupportedDocumentFormatError(
        message=f"File format '{file_format}' is not supported",
        details={
            "provided_format": file_format,
            "supported_formats": supported_formats,
        },
    )


def raise_validation_error(field: str, reason: str) -> None:
    """
    Raise ValidationError with field details.

    Args:
        field: Field name that failed validation
        reason: Reason for validation failure
    """
    raise ValidationError(
        message=f"Validation failed for field '{field}'",
        details={"field": field, "reason": reason},
    )


def raise_rate_limit_error(limit: str, retry_after: int = 60) -> None:
    """
    Raise RateLimitError with limit details.

    Args:
        limit: Rate limit description
        retry_after: Seconds until retry is allowed
    """
    raise RateLimitError(
        message=f"Rate limit exceeded: {limit}",
        details={"limit": limit},
        retry_after=retry_after,
    )
