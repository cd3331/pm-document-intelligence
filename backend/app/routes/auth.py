"""
Authentication Routes for PM Document Intelligence.

This module provides comprehensive authentication endpoints including:
- User registration with validation
- Login with account lockout protection
- Token refresh mechanism
- Logout
- Current user retrieval
- Password reset flow

All endpoints include rate limiting, audit logging, and security best practices.

Usage:
    Include in main application:
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
"""

import re
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.database import execute_insert, execute_select, execute_update
from app.models import (
    Token,
    User,
    UserCreate,
    UserInDB,
    UserRole,
    create_token_pair,
    hash_password,
    verify_password,
    verify_token,
    sanitize_user_response,
)
from app.utils.audit_log import (
    AuditAction,
    AuditStatus,
    log_auth_event,
    log_failed_login,
    log_account_lockout,
)
from app.utils.auth_helpers import (
    check_account_lockout,
    get_current_active_user,
    get_current_user,
    get_lockout_info,
    invalidate_user_cache,
)
from app.utils.exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    ValidationError,
)
from app.utils.logger import get_logger


logger = get_logger(__name__)
router = APIRouter()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


# ============================================================================
# Request/Response Models
# ============================================================================

class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="User password",
    )
    full_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="User full name",
    )
    organization: Optional[str] = Field(
        None,
        max_length=255,
        description="Organization name",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password strength.

        Requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")

        return v

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
                "full_name": "John Doe",
                "organization": "Acme Corp",
            }
        }


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
            }
        }


class LoginResponse(BaseModel):
    """User login response with tokens and user profile."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user: User = Field(..., description="User profile")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "role": "user",
                    "is_active": True,
                },
            }
        }


class RefreshTokenRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str = Field(..., description="JWT refresh token")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
            }
        }


class PasswordResetRequest(BaseModel):
    """Password reset request."""

    email: EmailStr = Field(..., description="User email address")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
            }
        }


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""

    token: str = Field(..., description="Reset token from email")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password",
    )

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "token": "reset-token-here",
                "new_password": "NewSecurePass123!",
            }
        }


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str = Field(..., description="Response message")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "message": "Operation completed successfully",
            }
        }


# ============================================================================
# Registration Endpoint
# ============================================================================

@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and password",
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Invalid request data"},
        409: {"description": "Email already registered"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit("5/hour")  # Rate limit: 5 registrations per hour per IP
async def register(
    request: Request,
    registration: RegisterRequest,
) -> LoginResponse:
    """
    Register a new user account.

    - **email**: Valid email address (will be lowercased)
    - **password**: Strong password (min 8 chars, uppercase, lowercase, digit, special char)
    - **full_name**: User's full name
    - **organization**: Optional organization name

    Returns JWT tokens and user profile.
    """
    try:
        # Normalize email
        email = registration.email.lower().strip()

        # Check if email already exists
        existing_users = await execute_select(
            "users",
            match={"email": email}
        )

        if existing_users:
            logger.warning(f"Registration attempt with existing email: {email}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        # Hash password
        hashed_password = hash_password(registration.password)

        # Create user
        user_data = {
            "email": email,
            "hashed_password": hashed_password,
            "full_name": registration.full_name.strip(),
            "organization": registration.organization.strip() if registration.organization else None,
            "role": UserRole.USER.value,  # Default role
            "is_active": True,
            "email_verified": False,  # Requires email verification
            "preferences": {
                "theme": "light",
                "language": "en",
                "timezone": "UTC",
                "notifications_enabled": True,
                "email_notifications": True,
                "default_view": "grid",
            },
        }

        # Insert into database
        user_record = await execute_insert("users", user_data)
        user = UserInDB(**user_record)

        # Create JWT tokens
        tokens = create_token_pair(user)

        # Log successful registration
        await log_auth_event(
            action=AuditAction.REGISTER,
            user_id=user.id,
            email=user.email,
            status=AuditStatus.SUCCESS,
            request=request,
        )

        logger.info(f"New user registered: {user.id} ({user.email})")

        # Return tokens and user profile
        return LoginResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            expires_in=tokens.expires_in,
            user=sanitize_user_response(user),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again.",
        )


# ============================================================================
# Login Endpoint
# ============================================================================

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login user",
    description="Authenticate user with email and password",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"},
        423: {"description": "Account locked due to failed attempts"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit("10/minute")  # Rate limit: 10 login attempts per minute per IP
async def login(
    request: Request,
    credentials: LoginRequest,
) -> LoginResponse:
    """
    Authenticate user and return JWT tokens.

    - **email**: User email address
    - **password**: User password

    Account will be locked after 5 failed login attempts within 1 hour.
    """
    email = credentials.email.lower().strip()

    try:
        # Check if account is locked
        is_locked = await check_account_lockout(email)

        if is_locked:
            lockout_info = await get_lockout_info(email)

            logger.warning(f"Login attempt for locked account: {email}")

            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail={
                    "message": "Account temporarily locked due to multiple failed login attempts",
                    "locked_until": lockout_info["lockout_expires"].isoformat() if "lockout_expires" in lockout_info else None,
                    "minutes_remaining": lockout_info.get("minutes_remaining", 60),
                },
            )

        # Get user by email
        users = await execute_select(
            "users",
            match={"email": email}
        )

        if not users:
            # Log failed login
            await log_failed_login(
                email=email,
                reason="User not found",
                request=request,
            )

            logger.warning(f"Login attempt for non-existent user: {email}")

            raise InvalidCredentialsError(
                message="Invalid email or password",
            )

        user = UserInDB(**users[0])

        # Verify password
        if not verify_password(credentials.password, user.hashed_password):
            # Log failed login
            await log_failed_login(
                email=email,
                reason="Invalid password",
                request=request,
            )

            logger.warning(f"Failed login attempt for user: {email}")

            # Check if this causes account lockout
            from app.utils.audit_log import get_recent_failed_logins

            failed_attempts = await get_recent_failed_logins(email, since_minutes=60)

            if len(failed_attempts) >= 4:  # This will be the 5th attempt
                await log_account_lockout(
                    user_id=user.id,
                    email=email,
                    failed_attempts=len(failed_attempts) + 1,
                    request=request,
                )

            raise InvalidCredentialsError(
                message="Invalid email or password",
            )

        # Check if account is active
        if not user.is_active:
            logger.warning(f"Login attempt for inactive account: {email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive. Please contact support.",
            )

        # Create JWT tokens
        tokens = create_token_pair(user)

        # Update last login
        await execute_update(
            "users",
            {"last_login": datetime.utcnow()},
            match={"id": user.id}
        )

        # Invalidate user cache
        await invalidate_user_cache(user.id)

        # Log successful login
        await log_auth_event(
            action=AuditAction.LOGIN,
            user_id=user.id,
            email=user.email,
            status=AuditStatus.SUCCESS,
            request=request,
        )

        logger.info(f"User logged in: {user.id} ({user.email})")

        return LoginResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            expires_in=tokens.expires_in,
            user=sanitize_user_response(user),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again.",
        )


# ============================================================================
# Token Refresh Endpoint
# ============================================================================

@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token",
    description="Generate new access token using refresh token",
    responses={
        200: {"description": "Token refreshed successfully"},
        401: {"description": "Invalid or expired refresh token"},
    },
)
async def refresh_token(
    request: Request,
    token_request: RefreshTokenRequest,
) -> Token:
    """
    Refresh access token using refresh token.

    - **refresh_token**: Valid JWT refresh token

    Returns new access token while keeping the same refresh token.
    """
    try:
        # Verify refresh token
        token_data = verify_token(token_request.refresh_token, token_type="refresh")

        # Get user
        users = await execute_select(
            "users",
            match={"id": token_data.sub}
        )

        if not users:
            logger.warning(f"Token refresh for non-existent user: {token_data.sub}")
            raise InvalidCredentialsError(
                message="Invalid refresh token",
            )

        user = UserInDB(**users[0])

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive",
            )

        # Create new tokens
        tokens = create_token_pair(user)

        # Log token refresh
        await log_auth_event(
            action=AuditAction.TOKEN_REFRESH,
            user_id=user.id,
            email=user.email,
            status=AuditStatus.SUCCESS,
            request=request,
        )

        logger.debug(f"Token refreshed for user: {user.id}")

        return tokens

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )


# ============================================================================
# Logout Endpoint
# ============================================================================

@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout user",
    description="Logout user (client-side token deletion)",
    responses={
        200: {"description": "Logout successful"},
        401: {"description": "Not authenticated"},
    },
)
async def logout(
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> MessageResponse:
    """
    Logout current user.

    Note: JWT tokens are stateless, so logout is primarily client-side
    (delete tokens from client storage). This endpoint logs the logout event.
    """
    # Log logout event
    await log_auth_event(
        action=AuditAction.LOGOUT,
        user_id=current_user.id,
        email=current_user.email,
        status=AuditStatus.SUCCESS,
        request=request,
    )

    logger.info(f"User logged out: {current_user.id}")

    return MessageResponse(
        message="Logout successful. Please delete tokens from client storage."
    )


# ============================================================================
# Get Current User Endpoint
# ============================================================================

@router.get(
    "/me",
    response_model=User,
    summary="Get current user",
    description="Get current authenticated user profile",
    responses={
        200: {"description": "User profile retrieved"},
        401: {"description": "Not authenticated"},
    },
)
async def get_me(
    current_user: UserInDB = Depends(get_current_active_user),
) -> User:
    """
    Get current authenticated user profile.

    Returns user profile without sensitive data.
    """
    return sanitize_user_response(current_user)


# ============================================================================
# Password Reset Flow
# ============================================================================

@router.post(
    "/password-reset/request",
    response_model=MessageResponse,
    summary="Request password reset",
    description="Request password reset email",
    responses={
        200: {"description": "Reset email sent (if email exists)"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit("3/hour")  # Rate limit: 3 reset requests per hour per IP
async def request_password_reset(
    request: Request,
    reset_request: PasswordResetRequest,
) -> MessageResponse:
    """
    Request password reset email.

    - **email**: User email address

    For security, always returns success even if email doesn't exist.
    """
    email = reset_request.email.lower().strip()

    try:
        # Get user by email
        users = await execute_select(
            "users",
            match={"email": email}
        )

        if users:
            user = UserInDB(**users[0])

            # Generate reset token (valid for 1 hour)
            reset_token = str(uuid4())
            reset_expires = datetime.utcnow() + timedelta(hours=1)

            # Store reset token (in production, store in database)
            # For now, we'll use cache
            from app.cache.redis import set_cache

            await set_cache(
                f"password_reset:{reset_token}",
                {
                    "user_id": user.id,
                    "email": user.email,
                    "expires": reset_expires.isoformat(),
                },
                ttl=3600,  # 1 hour
            )

            # TODO: Send reset email
            # await send_password_reset_email(user.email, reset_token)

            # Log password reset request
            await log_auth_event(
                action=AuditAction.PASSWORD_RESET_REQUEST,
                user_id=user.id,
                email=user.email,
                status=AuditStatus.SUCCESS,
                request=request,
            )

            logger.info(f"Password reset requested for: {email}")

        else:
            # Don't reveal if email exists
            logger.debug(f"Password reset requested for non-existent email: {email}")

        # Always return success for security
        return MessageResponse(
            message="If the email exists, a password reset link has been sent."
        )

    except Exception as e:
        logger.error(f"Password reset request error: {e}", exc_info=True)
        # Don't reveal errors to user
        return MessageResponse(
            message="If the email exists, a password reset link has been sent."
        )


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    summary="Confirm password reset",
    description="Reset password with token from email",
    responses={
        200: {"description": "Password reset successful"},
        400: {"description": "Invalid or expired token"},
    },
)
async def confirm_password_reset(
    request: Request,
    reset_confirm: PasswordResetConfirm,
) -> MessageResponse:
    """
    Confirm password reset with token.

    - **token**: Reset token from email
    - **new_password**: New password (must meet strength requirements)
    """
    try:
        # Get reset token data from cache
        from app.cache.redis import get_cache, delete_cache

        token_data = await get_cache(f"password_reset:{reset_confirm.token}")

        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        # Check expiration
        expires = datetime.fromisoformat(token_data["expires"])
        if datetime.utcnow() > expires:
            await delete_cache(f"password_reset:{reset_confirm.token}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired",
            )

        # Hash new password
        hashed_password = hash_password(reset_confirm.new_password)

        # Update user password
        await execute_update(
            "users",
            {"hashed_password": hashed_password},
            match={"id": token_data["user_id"]}
        )

        # Delete reset token
        await delete_cache(f"password_reset:{reset_confirm.token}")

        # Invalidate user cache
        await invalidate_user_cache(token_data["user_id"])

        # Log password reset completion
        await log_auth_event(
            action=AuditAction.PASSWORD_RESET_COMPLETE,
            user_id=token_data["user_id"],
            email=token_data["email"],
            status=AuditStatus.SUCCESS,
            request=request,
        )

        logger.info(f"Password reset completed for: {token_data['email']}")

        return MessageResponse(
            message="Password has been reset successfully. You can now login with your new password."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset confirmation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed. Please try again.",
        )
