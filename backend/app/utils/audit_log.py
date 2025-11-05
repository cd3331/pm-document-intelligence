"""
Audit Logging System for PM Document Intelligence.

This module provides comprehensive audit logging for security, compliance,
and troubleshooting purposes.

Features:
- Authentication event logging
- Document access tracking
- AI service usage monitoring
- IP address and user agent tracking
- Automatic timestamp recording
- Sensitive data masking

Usage:
    from app.utils.audit_log import log_auth_event, log_document_access

    # Log authentication
    await log_auth_event(
        action="login",
        user_id=user.id,
        status="success",
        request=request
    )

    # Log document access
    await log_document_access(
        user_id=user.id,
        document_id=doc_id,
        action="view",
        request=request
    )
"""

from datetime import datetime
from typing import Any

from app.database import execute_insert
from app.utils.logger import get_logger
from fastapi import Request

logger = get_logger(__name__)


# ============================================================================
# Audit Event Types
# ============================================================================


class AuditAction:
    """Audit action constants."""

    # Authentication actions
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_COMPLETE = "password_reset_complete"
    TOKEN_REFRESH = "token_refresh"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"

    # Document actions
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_VIEW = "document_view"
    DOCUMENT_DOWNLOAD = "document_download"
    DOCUMENT_UPDATE = "document_update"
    DOCUMENT_DELETE = "document_delete"
    DOCUMENT_SHARE = "document_share"

    # Analysis actions
    ANALYSIS_CREATE = "analysis_create"
    ANALYSIS_VIEW = "analysis_view"
    ANALYSIS_UPDATE = "analysis_update"
    ANALYSIS_DELETE = "analysis_delete"

    # AI service actions
    AI_BEDROCK_CALL = "ai_bedrock_call"
    AI_OPENAI_CALL = "ai_openai_call"
    AI_TEXTRACT_CALL = "ai_textract_call"
    AI_COMPREHEND_CALL = "ai_comprehend_call"

    # User management actions
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    ROLE_CHANGE = "role_change"

    # Admin actions
    ADMIN_ACCESS = "admin_access"
    CONFIG_CHANGE = "config_change"


class AuditStatus:
    """Audit status constants."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


# ============================================================================
# Helper Functions
# ============================================================================


def get_client_ip(request: Request) -> str | None:
    """
    Extract client IP address from request.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address or None
    """
    # Check X-Forwarded-For header (for proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Get first IP in the chain
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct client
    if request.client:
        return request.client.host

    return None


def get_user_agent(request: Request) -> str | None:
    """
    Extract user agent from request.

    Args:
        request: FastAPI request object

    Returns:
        User agent string or None
    """
    return request.headers.get("User-Agent")


def get_request_id(request: Request) -> str | None:
    """
    Extract request ID from request state.

    Args:
        request: FastAPI request object

    Returns:
        Request ID or None
    """
    return getattr(request.state, "request_id", None)


def mask_sensitive_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Mask sensitive data in audit log.

    Args:
        data: Data dictionary

    Returns:
        Data with sensitive fields masked
    """
    sensitive_keys = {
        "password",
        "token",
        "secret",
        "api_key",
        "access_token",
        "refresh_token",
        "hashed_password",
        "credit_card",
        "ssn",
    }

    masked_data = data.copy()

    for key, value in masked_data.items():
        if isinstance(value, dict):
            masked_data[key] = mask_sensitive_data(value)
        elif any(sensitive in key.lower() for sensitive in sensitive_keys):
            if value:
                masked_data[key] = "***MASKED***"

    return masked_data


# ============================================================================
# Core Audit Logging Function
# ============================================================================


async def create_audit_log(
    action: str,
    resource_type: str,
    user_id: str | None = None,
    resource_id: str | None = None,
    status: str = AuditStatus.SUCCESS,
    error_message: str | None = None,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> bool:
    """
    Create an audit log entry.

    Args:
        action: Action performed
        resource_type: Type of resource
        user_id: User ID (optional for anonymous actions)
        resource_id: Resource ID
        status: Operation status
        error_message: Error message if failed
        old_values: Previous values (for updates)
        new_values: New values (for updates/creates)
        metadata: Additional metadata
        ip_address: Client IP address
        user_agent: User agent string
        request_id: Request ID for tracing

    Returns:
        True if successful, False otherwise
    """
    try:
        # Mask sensitive data
        if old_values:
            old_values = mask_sensitive_data(old_values)
        if new_values:
            new_values = mask_sensitive_data(new_values)
        if metadata:
            metadata = mask_sensitive_data(metadata)

        # Create audit log entry
        audit_data = {
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "status": status,
            "error_message": error_message,
            "old_values": old_values,
            "new_values": new_values,
            "metadata": metadata or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_id": request_id,
        }

        # Insert into database
        await execute_insert("audit_logs", audit_data)

        logger.debug(
            f"Audit log created: {action} on {resource_type} by user {user_id}",
            extra={
                "action": action,
                "resource_type": resource_type,
                "user_id": user_id,
                "status": status,
            },
        )

        return True

    except Exception as e:
        # Don't fail the main operation if audit logging fails
        logger.error(f"Failed to create audit log: {e}", exc_info=True)
        return False


# ============================================================================
# Authentication Event Logging
# ============================================================================


async def log_auth_event(
    action: str,
    user_id: str | None = None,
    email: str | None = None,
    status: str = AuditStatus.SUCCESS,
    error_message: str | None = None,
    request: Request | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """
    Log authentication event.

    Args:
        action: Authentication action (login, logout, register, etc.)
        user_id: User ID
        email: User email
        status: Event status
        error_message: Error message if failed
        request: FastAPI request object
        metadata: Additional metadata

    Returns:
        True if successful, False otherwise

    Example:
        await log_auth_event(
            action=AuditAction.LOGIN,
            user_id=user.id,
            email=user.email,
            status=AuditStatus.SUCCESS,
            request=request
        )
    """
    meta = metadata or {}
    if email:
        meta["email"] = email

    ip_address = None
    user_agent = None
    request_id = None

    if request:
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        request_id = get_request_id(request)

    return await create_audit_log(
        action=action,
        resource_type="authentication",
        user_id=user_id,
        status=status,
        error_message=error_message,
        metadata=meta,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )


async def log_failed_login(
    email: str,
    reason: str,
    request: Request | None = None,
) -> bool:
    """
    Log failed login attempt.

    Args:
        email: Email address attempted
        reason: Failure reason
        request: FastAPI request object

    Returns:
        True if successful, False otherwise
    """
    return await log_auth_event(
        action=AuditAction.LOGIN,
        email=email,
        status=AuditStatus.FAILURE,
        error_message=reason,
        request=request,
        metadata={"reason": reason},
    )


async def log_account_lockout(
    user_id: str,
    email: str,
    failed_attempts: int,
    request: Request | None = None,
) -> bool:
    """
    Log account lockout event.

    Args:
        user_id: User ID
        email: User email
        failed_attempts: Number of failed attempts
        request: FastAPI request object

    Returns:
        True if successful, False otherwise
    """
    return await log_auth_event(
        action=AuditAction.ACCOUNT_LOCKED,
        user_id=user_id,
        email=email,
        status=AuditStatus.SUCCESS,
        request=request,
        metadata={
            "failed_attempts": failed_attempts,
            "lockout_reason": "exceeded_max_attempts",
        },
    )


# ============================================================================
# Document Event Logging
# ============================================================================


async def log_document_access(
    user_id: str,
    document_id: str,
    action: str,
    request: Request | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """
    Log document access event.

    Args:
        user_id: User ID
        document_id: Document ID
        action: Action performed (view, download, update, delete)
        request: FastAPI request object
        metadata: Additional metadata

    Returns:
        True if successful, False otherwise

    Example:
        await log_document_access(
            user_id=user.id,
            document_id=doc_id,
            action=AuditAction.DOCUMENT_VIEW,
            request=request
        )
    """
    ip_address = None
    user_agent = None
    request_id = None

    if request:
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        request_id = get_request_id(request)

    return await create_audit_log(
        action=action,
        resource_type="document",
        user_id=user_id,
        resource_id=document_id,
        status=AuditStatus.SUCCESS,
        metadata=metadata,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )


async def log_document_change(
    user_id: str,
    document_id: str,
    action: str,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    request: Request | None = None,
) -> bool:
    """
    Log document change event.

    Args:
        user_id: User ID
        document_id: Document ID
        action: Action performed (upload, update, delete)
        old_values: Previous values
        new_values: New values
        request: FastAPI request object

    Returns:
        True if successful, False otherwise
    """
    ip_address = None
    user_agent = None
    request_id = None

    if request:
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        request_id = get_request_id(request)

    return await create_audit_log(
        action=action,
        resource_type="document",
        user_id=user_id,
        resource_id=document_id,
        status=AuditStatus.SUCCESS,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )


# ============================================================================
# AI Service Event Logging
# ============================================================================


async def log_ai_service_call(
    user_id: str,
    service: str,
    action: str,
    document_id: str | None = None,
    tokens_used: int | None = None,
    cost: float | None = None,
    duration_seconds: float | None = None,
    status: str = AuditStatus.SUCCESS,
    error_message: str | None = None,
    request: Request | None = None,
) -> bool:
    """
    Log AI service usage.

    Args:
        user_id: User ID
        service: Service name (bedrock, openai, textract, comprehend)
        action: Action performed
        document_id: Associated document ID
        tokens_used: Number of tokens consumed
        cost: Estimated cost in USD
        duration_seconds: Call duration
        status: Call status
        error_message: Error message if failed
        request: FastAPI request object

    Returns:
        True if successful, False otherwise

    Example:
        await log_ai_service_call(
            user_id=user.id,
            service="bedrock",
            action=AuditAction.AI_BEDROCK_CALL,
            document_id=doc_id,
            tokens_used=1500,
            cost=0.0045,
            duration_seconds=2.3,
            request=request
        )
    """
    metadata = {
        "service": service,
        "tokens_used": tokens_used,
        "cost_usd": cost,
        "duration_seconds": duration_seconds,
    }

    ip_address = None
    request_id = None

    if request:
        ip_address = get_client_ip(request)
        request_id = get_request_id(request)

    return await create_audit_log(
        action=action,
        resource_type="ai_service",
        user_id=user_id,
        resource_id=document_id,
        status=status,
        error_message=error_message,
        metadata=metadata,
        ip_address=ip_address,
        request_id=request_id,
    )


# ============================================================================
# Admin Event Logging
# ============================================================================


async def log_admin_action(
    admin_user_id: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    request: Request | None = None,
) -> bool:
    """
    Log administrative action.

    Args:
        admin_user_id: Admin user ID
        action: Action performed
        resource_type: Type of resource
        resource_id: Resource ID
        old_values: Previous values
        new_values: New values
        request: FastAPI request object

    Returns:
        True if successful, False otherwise
    """
    ip_address = None
    user_agent = None
    request_id = None

    if request:
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        request_id = get_request_id(request)

    return await create_audit_log(
        action=action,
        resource_type=resource_type,
        user_id=admin_user_id,
        resource_id=resource_id,
        status=AuditStatus.SUCCESS,
        old_values=old_values,
        new_values=new_values,
        metadata={"admin_action": True},
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )


# ============================================================================
# Audit Log Queries
# ============================================================================


async def get_user_audit_logs(
    user_id: str,
    limit: int = 100,
    offset: int = 0,
) -> list:
    """
    Get audit logs for a specific user.

    Args:
        user_id: User ID
        limit: Maximum number of logs to return
        offset: Offset for pagination

    Returns:
        List of audit log entries
    """
    try:
        from app.database import execute_select

        logs = await execute_select(
            "audit_logs",
            match={"user_id": user_id},
            order="created_at.desc",
            limit=limit,
            offset=offset,
        )

        return logs

    except Exception as e:
        logger.error(f"Failed to retrieve audit logs: {e}", exc_info=True)
        return []


async def get_recent_failed_logins(
    email: str,
    since_minutes: int = 60,
) -> list:
    """
    Get recent failed login attempts for an email.

    Args:
        email: Email address
        since_minutes: Look back this many minutes

    Returns:
        List of failed login attempts
    """
    try:
        from datetime import timedelta

        from app.database import execute_query

        since_time = datetime.utcnow() - timedelta(minutes=since_minutes)

        query = """
        SELECT * FROM audit_logs
        WHERE action = %s
        AND status = %s
        AND metadata->>'email' = %s
        AND created_at > %s
        ORDER BY created_at DESC
        """

        logs = await execute_query(
            query,
            (AuditAction.LOGIN, AuditStatus.FAILURE, email, since_time),
        )

        return logs or []

    except Exception as e:
        logger.error(f"Failed to retrieve failed login attempts: {e}", exc_info=True)
        return []
