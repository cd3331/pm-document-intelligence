"""
User Models and Authentication for PM Document Intelligence.

This module provides user models, authentication utilities, and role-based
access control (RBAC) functionality.

Features:
- Pydantic models for user data validation
- Password hashing with bcrypt
- JWT token creation and validation
- Role-based access control
- User preferences management

Usage:
    from app.models.user import User, create_user, verify_password

    # Create user
    user = await create_user(user_data)

    # Verify password
    is_valid = verify_password(password, user.hashed_password)

    # Create JWT token
    token = create_access_token({"sub": user.id})
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.config import settings
from app.utils.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Password Hashing
# ============================================================================

# Password context for hashing
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.security.bcrypt_rounds,
)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password

    Example:
        hashed = hash_password("mypassword123")
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches, False otherwise

    Example:
        is_valid = verify_password("mypassword123", user.hashed_password)
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


# ============================================================================
# Role-Based Access Control (RBAC)
# ============================================================================


class UserRole(str, Enum):
    """User roles for access control."""

    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    GUEST = "guest"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


class PermissionLevel(int, Enum):
    """Permission levels for access control."""

    NONE = 0
    READ = 1
    WRITE = 2
    DELETE = 3
    ADMIN = 4


# Role permission mappings
ROLE_PERMISSIONS: dict[UserRole, PermissionLevel] = {
    UserRole.GUEST: PermissionLevel.READ,
    UserRole.USER: PermissionLevel.WRITE,
    UserRole.MANAGER: PermissionLevel.DELETE,
    UserRole.ADMIN: PermissionLevel.ADMIN,
}


def has_permission(user_role: UserRole, required_level: PermissionLevel) -> bool:
    """
    Check if user role has required permission level.

    Args:
        user_role: User's role
        required_level: Required permission level

    Returns:
        True if user has permission, False otherwise

    Example:
        if has_permission(user.role, PermissionLevel.WRITE):
            # Allow operation
    """
    user_level = ROLE_PERMISSIONS.get(user_role, PermissionLevel.NONE)
    return user_level >= required_level


# ============================================================================
# User Preferences
# ============================================================================


class UserPreferences(BaseModel):
    """User preferences and settings."""

    theme: str = Field(default="light", description="UI theme (light/dark)")
    language: str = Field(default="en", description="Preferred language")
    timezone: str = Field(default="UTC", description="User timezone")
    notifications_enabled: bool = Field(default=True, description="Enable notifications")
    email_notifications: bool = Field(default=True, description="Email notifications")
    default_view: str = Field(default="grid", description="Default document view")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "theme": "dark",
                "language": "en",
                "timezone": "America/New_York",
                "notifications_enabled": True,
                "email_notifications": False,
                "default_view": "list",
            }
        }


# ============================================================================
# User Models
# ============================================================================


class UserBase(BaseModel):
    """Base user model with common fields."""

    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=1, max_length=255, description="User full name")
    organization: str | None = Field(None, max_length=255, description="Organization name")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    is_active: bool = Field(default=True, description="Account active status")
    preferences: UserPreferences = Field(
        default_factory=UserPreferences,
        description="User preferences",
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate and normalize email."""
        return v.lower().strip()

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate full name."""
        if not v.strip():
            raise ValueError("Full name cannot be empty")
        return v.strip()


class UserCreate(UserBase):
    """Model for creating a new user."""

    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="User password (min 8 characters)",
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Validate password strength.

        Requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")

        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")

        return v

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "full_name": "John Doe",
                "organization": "Acme Corp",
                "password": "SecurePass123",
                "role": "user",
            }
        }


class UserUpdate(BaseModel):
    """Model for updating user information."""

    full_name: str | None = Field(None, min_length=1, max_length=255)
    organization: str | None = Field(None, max_length=255)
    preferences: UserPreferences | None = None
    is_active: bool | None = None

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "full_name": "Jane Doe",
                "organization": "New Corp",
                "preferences": {
                    "theme": "dark",
                    "notifications_enabled": True,
                },
            }
        }


class UserInDB(UserBase):
    """User model as stored in database."""

    id: str = Field(..., description="User ID (UUID)")
    hashed_password: str = Field(..., description="Hashed password")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_login: datetime | None = Field(None, description="Last login timestamp")
    email_verified: bool = Field(default=False, description="Email verification status")

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v: UUID | str) -> str:
        """Convert UUID to string if needed."""
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        """Pydantic configuration."""

        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "full_name": "John Doe",
                "organization": "Acme Corp",
                "role": "user",
                "is_active": True,
                "email_verified": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }


class User(UserBase):
    """User model for API responses (excludes sensitive data)."""

    id: str = Field(..., description="User ID (UUID)")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_login: datetime | None = Field(None, description="Last login timestamp")
    email_verified: bool = Field(default=False, description="Email verification status")

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v: UUID | str) -> str:
        """Convert UUID to string if needed."""
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        """Pydantic configuration."""

        from_attributes = True


# ============================================================================
# JWT Token Models
# ============================================================================


class Token(BaseModel):
    """JWT token response."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
            }
        }


class TokenData(BaseModel):
    """Token payload data."""

    sub: str = Field(..., description="Subject (user ID)")
    email: str | None = Field(None, description="User email")
    role: str | None = Field(None, description="User role")
    exp: datetime | None = Field(None, description="Expiration time")


# ============================================================================
# JWT Token Functions
# ============================================================================


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create JWT access token.

    Args:
        data: Token payload data
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token

    Example:
        token = create_access_token({"sub": user.id, "email": user.email})
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.security.jwt_access_token_expire_minutes
        )

    to_encode.update({"exp": expire, "type": "access"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.security.jwt_secret_key,
        algorithm=settings.security.jwt_algorithm,
    )

    logger.debug(f"Access token created for user: {data.get('sub')}")
    return encoded_jwt


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create JWT refresh token.

    Args:
        data: Token payload data
        expires_delta: Token expiration time

    Returns:
        Encoded JWT refresh token

    Example:
        token = create_refresh_token({"sub": user.id})
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.security.jwt_refresh_token_expire_days)

    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.security.jwt_secret_key,
        algorithm=settings.security.jwt_algorithm,
    )

    logger.debug(f"Refresh token created for user: {data.get('sub')}")
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> TokenData:
    """
    Verify and decode JWT token.

    Args:
        token: JWT token to verify
        token_type: Expected token type (access or refresh)

    Returns:
        Decoded token data

    Raises:
        InvalidTokenError: If token is invalid
        TokenExpiredError: If token has expired

    Example:
        token_data = verify_token(token)
        user_id = token_data.sub
    """
    try:
        payload = jwt.decode(
            token,
            settings.security.jwt_secret_key,
            algorithms=[settings.security.jwt_algorithm],
        )

        # Check token type
        if payload.get("type") != token_type:
            raise InvalidTokenError(
                message=f"Invalid token type. Expected {token_type}",
                details={"expected": token_type, "got": payload.get("type")},
            )

        # Extract data
        user_id: str = payload.get("sub")
        if user_id is None:
            raise InvalidTokenError(
                message="Token missing subject claim",
            )

        token_data = TokenData(
            sub=user_id,
            email=payload.get("email"),
            role=payload.get("role"),
            exp=(datetime.fromtimestamp(payload.get("exp")) if payload.get("exp") else None),
        )

        logger.debug(f"Token verified for user: {user_id}")
        return token_data

    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise TokenExpiredError(
            message="Token has expired",
        )

    except JWTError as e:
        logger.error(f"Token verification failed: {e}")
        raise InvalidTokenError(
            message="Could not validate credentials",
            details={"error": str(e)},
        )


def create_token_pair(user: UserInDB) -> Token:
    """
    Create both access and refresh tokens for a user.

    Args:
        user: User object

    Returns:
        Token pair with access and refresh tokens

    Example:
        tokens = create_token_pair(user)
        return tokens
    """
    # Create access token
    access_token = create_access_token(
        data={
            "sub": user.id,
            "email": user.email,
            "role": user.role.value,
        }
    )

    # Create refresh token
    refresh_token = create_refresh_token(data={"sub": user.id})

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.security.jwt_access_token_expire_minutes * 60,
    )


# ============================================================================
# User Helper Functions
# ============================================================================


def user_to_dict(user: UserInDB, include_sensitive: bool = False) -> dict[str, Any]:
    """
    Convert user model to dictionary.

    Args:
        user: User object
        include_sensitive: Include sensitive fields

    Returns:
        User dictionary
    """
    user_dict = user.model_dump()

    if not include_sensitive:
        # Remove sensitive fields
        user_dict.pop("hashed_password", None)

    return user_dict


def sanitize_user_response(user: UserInDB) -> User:
    """
    Convert UserInDB to User (removes sensitive data).

    Args:
        user: User object from database

    Returns:
        User object for API response
    """
    return User(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        organization=user.organization,
        role=user.role,
        is_active=user.is_active,
        preferences=user.preferences,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
        email_verified=user.email_verified,
    )
