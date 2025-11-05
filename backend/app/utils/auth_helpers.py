"""
Authentication Helper Functions and Dependencies for PM Document Intelligence.

This module provides helper functions and FastAPI dependencies for authentication
and authorization throughout the application.

Features:
- JWT token validation dependencies
- Current user extraction
- Role-based access control (RBAC)
- Account status verification
- User data caching

Usage:
    from app.utils.auth_helpers import get_current_user, require_role
    from app.models import UserRole

    @router.get("/protected")
    async def protected_route(user = Depends(get_current_active_user)):
        return {"user_id": user.id}

    @router.get("/admin")
    async def admin_route(user = Depends(require_role(UserRole.ADMIN))):
        return {"message": "Admin access granted"}
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.cache.redis import get_cache, set_cache
from app.config import settings
from app.database import execute_select, execute_update
from app.models import (
    User,
    UserInDB,
    UserRole,
    verify_token,
    has_permission,
    PermissionLevel,
)
from app.utils.exceptions import (
    AuthenticationError,
    AuthorizationError,
    InvalidTokenError,
    TokenExpiredError,
)
from app.utils.logger import get_logger


logger = get_logger(__name__)


# HTTP Bearer token authentication
security = HTTPBearer()


# ============================================================================
# Token Validation
# ============================================================================


async def get_token_from_header(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    Extract and validate bearer token from Authorization header.

    Args:
        credentials: HTTP bearer credentials

    Returns:
        JWT token string

    Raises:
        AuthenticationError: If token is missing or invalid format
    """
    if not credentials:
        raise AuthenticationError(
            message="Not authenticated",
            details={"reason": "Missing authorization header"},
        )

    if credentials.scheme.lower() != "bearer":
        raise AuthenticationError(
            message="Invalid authentication scheme",
            details={"expected": "Bearer", "got": credentials.scheme},
        )

    return credentials.credentials


# ============================================================================
# User Retrieval
# ============================================================================


async def get_user_by_id(user_id: str) -> Optional[UserInDB]:
    """
    Get user by ID from database or cache.

    Args:
        user_id: User ID

    Returns:
        User object or None if not found
    """
    # Try cache first
    cache_key = f"user:{user_id}"
    cached_user = await get_cache(cache_key)

    if cached_user:
        logger.debug(f"User {user_id} retrieved from cache")
        return UserInDB(**cached_user)

    # Get from database
    try:
        users = await execute_select("users", match={"id": user_id})

        if not users:
            logger.warning(f"User {user_id} not found in database")
            return None

        user = UserInDB(**users[0])

        # Cache user data for 15 minutes
        await set_cache(cache_key, user.model_dump(), ttl=900)

        logger.debug(f"User {user_id} retrieved from database and cached")
        return user

    except Exception as e:
        logger.error(f"Error retrieving user {user_id}: {e}", exc_info=True)
        return None


# ============================================================================
# Current User Dependencies
# ============================================================================


async def get_current_user(
    token: str = Depends(get_token_from_header),
) -> UserInDB:
    """
    Get current user from JWT token.

    This dependency validates the JWT token and retrieves the current user.
    Use this for any protected route that requires authentication.

    Args:
        token: JWT access token

    Returns:
        Current user object

    Raises:
        AuthenticationError: If token is invalid or user not found
        TokenExpiredError: If token has expired

    Example:
        @router.get("/me")
        async def get_me(user: UserInDB = Depends(get_current_user)):
            return user
    """
    try:
        # Verify token
        token_data = verify_token(token, token_type="access")

        # Get user from database
        user = await get_user_by_id(token_data.sub)

        if not user:
            logger.warning(f"User {token_data.sub} from token not found")
            raise AuthenticationError(
                message="User not found",
                details={"user_id": token_data.sub},
            )

        # Update last login time (async, don't wait)
        try:
            await execute_update(
                "users", {"last_login": datetime.utcnow()}, match={"id": user.id}
            )
        except Exception as e:
            logger.error(f"Failed to update last login: {e}")

        return user

    except (TokenExpiredError, InvalidTokenError) as e:
        # Re-raise authentication errors
        raise

    except Exception as e:
        logger.error(f"Error in get_current_user: {e}", exc_info=True)
        raise AuthenticationError(
            message="Could not validate credentials",
            details={"error": str(e)},
        )


async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    """
    Get current active user (account status check).

    This dependency checks if the user account is active.
    Use this for routes that require an active account.

    Args:
        current_user: Current user from get_current_user

    Returns:
        Current active user object

    Raises:
        AuthorizationError: If account is inactive

    Example:
        @router.get("/documents")
        async def get_documents(user: UserInDB = Depends(get_current_active_user)):
            return {"user_id": user.id}
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user {current_user.id} attempted access")
        raise AuthorizationError(
            message="Account is inactive",
            details={
                "user_id": current_user.id,
                "email": current_user.email,
            },
        )

    return current_user


async def get_current_verified_user(
    current_user: UserInDB = Depends(get_current_active_user),
) -> UserInDB:
    """
    Get current verified user (email verification check).

    This dependency checks if the user has verified their email.

    Args:
        current_user: Current active user

    Returns:
        Current verified user object

    Raises:
        AuthorizationError: If email not verified
    """
    if not current_user.email_verified:
        logger.warning(f"Unverified user {current_user.id} attempted access")
        raise AuthorizationError(
            message="Email not verified",
            details={
                "user_id": current_user.id,
                "email": current_user.email,
            },
        )

    return current_user


# ============================================================================
# Role-Based Access Control (RBAC)
# ============================================================================


def require_role(*required_roles: UserRole):
    """
    Dependency factory for role-based access control.

    Creates a dependency that checks if the user has one of the required roles.

    Args:
        *required_roles: One or more required roles

    Returns:
        FastAPI dependency function

    Raises:
        AuthorizationError: If user doesn't have required role

    Example:
        @router.get("/admin")
        async def admin_only(user = Depends(require_role(UserRole.ADMIN))):
            return {"message": "Admin access granted"}

        @router.get("/manager")
        async def manager_or_admin(
            user = Depends(require_role(UserRole.MANAGER, UserRole.ADMIN))
        ):
            return {"message": "Manager or admin access granted"}
    """

    async def role_checker(
        current_user: UserInDB = Depends(get_current_active_user),
    ) -> UserInDB:
        """Check if user has required role."""
        if current_user.role not in required_roles:
            logger.warning(
                f"User {current_user.id} with role {current_user.role} "
                f"attempted access requiring {required_roles}"
            )
            raise AuthorizationError(
                message="Insufficient permissions",
                details={
                    "required_roles": [role.value for role in required_roles],
                    "user_role": current_user.role.value,
                },
            )

        return current_user

    return role_checker


def require_permission(required_level: PermissionLevel):
    """
    Dependency factory for permission-based access control.

    Creates a dependency that checks if the user has the required permission level.

    Args:
        required_level: Required permission level

    Returns:
        FastAPI dependency function

    Raises:
        AuthorizationError: If user doesn't have required permission

    Example:
        @router.delete("/documents/{document_id}")
        async def delete_document(
            document_id: str,
            user = Depends(require_permission(PermissionLevel.DELETE))
        ):
            return {"message": "Document deleted"}
    """

    async def permission_checker(
        current_user: UserInDB = Depends(get_current_active_user),
    ) -> UserInDB:
        """Check if user has required permission level."""
        if not has_permission(current_user.role, required_level):
            logger.warning(
                f"User {current_user.id} with role {current_user.role} "
                f"attempted access requiring {required_level}"
            )
            raise AuthorizationError(
                message="Insufficient permissions",
                details={
                    "required_level": required_level.name,
                    "user_role": current_user.role.value,
                },
            )

        return current_user

    return permission_checker


# ============================================================================
# Account Lockout Management
# ============================================================================


async def check_account_lockout(email: str) -> bool:
    """
    Check if account is locked out due to failed login attempts.

    Args:
        email: User email address

    Returns:
        True if account is locked, False otherwise
    """
    from app.utils.audit_log import get_recent_failed_logins

    # Check failed login attempts in last hour
    failed_logins = await get_recent_failed_logins(email, since_minutes=60)

    # Lock account after 5 failed attempts
    if len(failed_logins) >= 5:
        logger.warning(
            f"Account {email} locked due to {len(failed_logins)} failed attempts"
        )
        return True

    return False


async def clear_failed_login_attempts(email: str) -> None:
    """
    Clear failed login attempts for an email (called on successful login).

    Note: This is a logical clear - we don't delete audit logs.
    The check_account_lockout function looks at recent attempts.

    Args:
        email: User email address
    """
    # In this implementation, we rely on time-based lockout (last 60 minutes)
    # so we don't need to explicitly clear attempts
    logger.debug(f"Successful login for {email}, relying on time-based lockout")


async def get_lockout_info(email: str) -> dict:
    """
    Get account lockout information.

    Args:
        email: User email address

    Returns:
        Dictionary with lockout information
    """
    from app.utils.audit_log import get_recent_failed_logins

    failed_logins = await get_recent_failed_logins(email, since_minutes=60)
    is_locked = len(failed_logins) >= 5

    if is_locked and failed_logins:
        # Get time until lockout expires (60 minutes from first failed attempt)
        first_attempt = failed_logins[-1]["created_at"]
        lockout_expires = first_attempt + timedelta(hours=1)
        minutes_remaining = int(
            (lockout_expires - datetime.utcnow()).total_seconds() / 60
        )

        return {
            "locked": True,
            "failed_attempts": len(failed_logins),
            "lockout_expires": lockout_expires,
            "minutes_remaining": max(0, minutes_remaining),
        }

    return {
        "locked": False,
        "failed_attempts": len(failed_logins),
    }


# ============================================================================
# Cache Management
# ============================================================================


async def invalidate_user_cache(user_id: str) -> None:
    """
    Invalidate cached user data.

    Call this when user data is updated.

    Args:
        user_id: User ID
    """
    from app.cache.redis import delete_cache

    cache_key = f"user:{user_id}"
    await delete_cache(cache_key)

    logger.debug(f"User cache invalidated for {user_id}")


# ============================================================================
# Optional Authentication
# ============================================================================


async def get_current_user_optional(
    token: Optional[str] = Depends(get_token_from_header),
) -> Optional[UserInDB]:
    """
    Get current user if authenticated, None otherwise.

    Use this for routes that can be accessed both authenticated and anonymously.

    Args:
        token: JWT access token (optional)

    Returns:
        Current user or None

    Example:
        @router.get("/public")
        async def public_route(user: Optional[UserInDB] = Depends(get_current_user_optional)):
            if user:
                return {"message": f"Hello, {user.full_name}"}
            return {"message": "Hello, guest"}
    """
    if not token:
        return None

    try:
        return await get_current_user(token)
    except (AuthenticationError, TokenExpiredError, InvalidTokenError):
        return None


# ============================================================================
# Resource Ownership Verification
# ============================================================================


async def verify_document_ownership(
    document_id: str,
    user: UserInDB,
) -> bool:
    """
    Verify that user owns a document.

    Args:
        document_id: Document ID
        user: Current user

    Returns:
        True if user owns document or is admin, False otherwise
    """
    # Admins can access any document
    if user.role == UserRole.ADMIN:
        return True

    # Check document ownership
    try:
        documents = await execute_select(
            "documents", columns="user_id", match={"id": document_id}
        )

        if not documents:
            return False

        return documents[0]["user_id"] == user.id

    except Exception as e:
        logger.error(f"Error verifying document ownership: {e}", exc_info=True)
        return False


async def require_document_ownership(
    document_id: str,
    user: UserInDB = Depends(get_current_active_user),
) -> UserInDB:
    """
    Dependency to verify document ownership.

    Args:
        document_id: Document ID
        user: Current user

    Returns:
        Current user if authorized

    Raises:
        AuthorizationError: If user doesn't own document
    """
    if not await verify_document_ownership(document_id, user):
        raise AuthorizationError(
            message="You don't have permission to access this document",
            details={"document_id": document_id},
        )

    return user
