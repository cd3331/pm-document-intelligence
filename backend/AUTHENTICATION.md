# Authentication System Documentation

Comprehensive guide for the JWT-based authentication system with refresh tokens and audit logging.

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [API Endpoints](#api-endpoints)
5. [Security Features](#security-features)
6. [Usage Examples](#usage-examples)
7. [Protected Routes](#protected-routes)
8. [Audit Logging](#audit-logging)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The PM Document Intelligence authentication system provides:

- **JWT-based authentication** with access and refresh tokens
- **Password strength validation** (uppercase, lowercase, digit, special character)
- **Account lockout** after 5 failed login attempts
- **Rate limiting** on all auth endpoints
- **Comprehensive audit logging** for compliance
- **User caching** for performance
- **Role-based access control** (RBAC)

---

## Features

### ✅ User Registration
- Email validation and uniqueness check
- Strong password requirements
- Automatic JWT token generation
- Default user role assignment
- Audit logging

### ✅ Login
- Email/password authentication
- Account lockout protection (5 failed attempts in 60 minutes)
- Failed login tracking
- Last login timestamp
- User cache invalidation

### ✅ Token Management
- Access tokens (30 minutes TTL)
- Refresh tokens (7 days TTL)
- Token refresh endpoint
- Automatic token validation

### ✅ Password Reset
- Request reset via email
- Time-limited reset tokens (1 hour)
- Secure token validation
- Password strength requirements

### ✅ Security
- Bcrypt password hashing (12 rounds)
- JWT with HS256 algorithm
- Rate limiting on all endpoints
- No passwords in logs (automatic masking)
- Request ID tracking

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐        ┌──────────────────┐          │
│  │  Auth Routes     │◄───────┤  Auth Helpers    │          │
│  │  /api/v1/auth/*  │        │  Dependencies    │          │
│  └──────────────────┘        └──────────────────┘          │
│           │                            │                     │
│           ▼                            ▼                     │
│  ┌──────────────────┐        ┌──────────────────┐          │
│  │  User Models     │        │  Audit Logging   │          │
│  │  JWT Functions   │        │  System          │          │
│  └──────────────────┘        └──────────────────┘          │
│           │                            │                     │
│           ▼                            ▼                     │
│  ┌────────────────────────────────────────────────┐        │
│  │           Supabase Database                     │        │
│  │  - users table                                  │        │
│  │  - audit_logs table                            │        │
│  └────────────────────────────────────────────────┘        │
│                                                              │
│  ┌────────────────────────────────────────────────┐        │
│  │           Redis Cache                           │        │
│  │  - User data (15 min TTL)                      │        │
│  │  - Password reset tokens (1 hour TTL)         │        │
│  └────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

### Key Files

| File | Purpose |
|------|---------|
| `backend/app/routes/auth.py` | Authentication endpoints |
| `backend/app/utils/auth_helpers.py` | Auth dependencies and helpers |
| `backend/app/utils/audit_log.py` | Audit logging system |
| `backend/app/models/user.py` | User models and JWT functions |

---

## API Endpoints

### Register User

**POST** `/api/v1/auth/register`

**Rate Limit**: 5 requests per hour per IP

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe",
  "organization": "Acme Corp"
}
```

**Password Requirements**:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character (!@#$%^&*(),.?":{}|<>)

**Response** (201 Created):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "full_name": "John Doe",
    "organization": "Acme Corp",
    "role": "user",
    "is_active": true,
    "email_verified": false,
    "created_at": "2024-01-15T10:00:00Z"
  }
}
```

**Errors**:
- `400`: Invalid request data
- `409`: Email already registered
- `429`: Rate limit exceeded

---

### Login

**POST** `/api/v1/auth/login`

**Rate Limit**: 10 requests per minute per IP

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "user"
  }
}
```

**Errors**:
- `401`: Invalid credentials
- `403`: Account inactive
- `423`: Account locked (5 failed attempts)
- `429`: Rate limit exceeded

**Account Lockout** (423):
```json
{
  "detail": {
    "message": "Account temporarily locked due to multiple failed login attempts",
    "locked_until": "2024-01-15T11:00:00Z",
    "minutes_remaining": 45
  }
}
```

---

### Refresh Token

**POST** `/api/v1/auth/refresh`

**Request Body**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

### Logout

**POST** `/api/v1/auth/logout`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "message": "Logout successful. Please delete tokens from client storage."
}
```

---

### Get Current User

**GET** `/api/v1/auth/me`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "full_name": "John Doe",
  "organization": "Acme Corp",
  "role": "user",
  "is_active": true,
  "email_verified": false,
  "preferences": {
    "theme": "light",
    "language": "en",
    "timezone": "UTC"
  },
  "created_at": "2024-01-15T10:00:00Z",
  "last_login": "2024-01-15T12:30:00Z"
}
```

---

### Request Password Reset

**POST** `/api/v1/auth/password-reset/request`

**Rate Limit**: 3 requests per hour per IP

**Request Body**:
```json
{
  "email": "user@example.com"
}
```

**Response** (200 OK):
```json
{
  "message": "If the email exists, a password reset link has been sent."
}
```

_Note: Always returns success for security (doesn't reveal if email exists)_

---

### Confirm Password Reset

**POST** `/api/v1/auth/password-reset/confirm`

**Request Body**:
```json
{
  "token": "reset-token-from-email",
  "new_password": "NewSecurePass123!"
}
```

**Response** (200 OK):
```json
{
  "message": "Password has been reset successfully. You can now login with your new password."
}
```

**Errors**:
- `400`: Invalid or expired token

---

## Security Features

### Password Hashing

- **Algorithm**: bcrypt
- **Rounds**: 12 (configurable via `BCRYPT_ROUNDS`)
- **Function**: `hash_password()` in `app/models/user.py`

```python
from app.models import hash_password, verify_password

# Hash password
hashed = hash_password("SecurePass123!")

# Verify password
is_valid = verify_password("SecurePass123!", hashed)
```

### JWT Tokens

**Access Token**:
- **Expiration**: 30 minutes (configurable via `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Type**: "access"
- **Claims**: `sub` (user ID), `email`, `role`, `exp`, `type`

**Refresh Token**:
- **Expiration**: 7 days (configurable via `JWT_REFRESH_TOKEN_EXPIRE_DAYS`)
- **Type**: "refresh"
- **Claims**: `sub` (user ID), `exp`, `type`

```python
from app.models import create_access_token, verify_token

# Create access token
token = create_access_token({"sub": user.id, "email": user.email})

# Verify token
token_data = verify_token(token, token_type="access")
user_id = token_data.sub
```

### Account Lockout

- **Threshold**: 5 failed login attempts
- **Window**: 60 minutes (rolling window)
- **Lockout Duration**: 60 minutes from first failed attempt
- **Tracking**: Via audit logs table

```python
from app.utils.auth_helpers import check_account_lockout, get_lockout_info

# Check if account is locked
is_locked = await check_account_lockout(email)

# Get lockout details
info = await get_lockout_info(email)
# {
#   "locked": True,
#   "failed_attempts": 5,
#   "lockout_expires": datetime,
#   "minutes_remaining": 45
# }
```

### Rate Limiting

| Endpoint | Limit |
|----------|-------|
| `/register` | 5 per hour per IP |
| `/login` | 10 per minute per IP |
| `/password-reset/request` | 3 per hour per IP |

Rate limiting is enforced using **slowapi** with Redis backend.

---

## Usage Examples

### Client-Side Authentication Flow

```javascript
// 1. Register or Login
const response = await fetch('/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'SecurePass123!'
  })
});

const { access_token, refresh_token, user } = await response.json();

// Store tokens
localStorage.setItem('access_token', access_token);
localStorage.setItem('refresh_token', refresh_token);

// 2. Make authenticated requests
const docResponse = await fetch('/api/v1/documents', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});

// 3. Refresh token when needed
async function refreshAccessToken() {
  const refresh_token = localStorage.getItem('refresh_token');

  const response = await fetch('/api/v1/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token })
  });

  const { access_token } = await response.json();
  localStorage.setItem('access_token', access_token);

  return access_token;
}

// 4. Logout
async function logout() {
  const access_token = localStorage.getItem('access_token');

  await fetch('/api/v1/auth/logout', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${access_token}`
    }
  });

  // Delete tokens
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}
```

---

## Protected Routes

### Using Dependencies

```python
from fastapi import APIRouter, Depends
from app.utils.auth_helpers import (
    get_current_user,
    get_current_active_user,
    require_role,
    require_permission
)
from app.models import UserRole, PermissionLevel, UserInDB

router = APIRouter()

# Basic authentication required
@router.get("/protected")
async def protected_route(user: UserInDB = Depends(get_current_user)):
    return {"user_id": user.id}

# Active account required
@router.get("/documents")
async def get_documents(user: UserInDB = Depends(get_current_active_user)):
    return {"user_id": user.id}

# Role-based access (single role)
@router.get("/admin")
async def admin_only(user: UserInDB = Depends(require_role(UserRole.ADMIN))):
    return {"message": "Admin access granted"}

# Role-based access (multiple roles)
@router.get("/manager")
async def manager_or_admin(
    user: UserInDB = Depends(require_role(UserRole.MANAGER, UserRole.ADMIN))
):
    return {"message": "Manager or admin access"}

# Permission-based access
@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    user: UserInDB = Depends(require_permission(PermissionLevel.DELETE))
):
    return {"message": "Document deleted"}
```

### Resource Ownership Verification

```python
from app.utils.auth_helpers import verify_document_ownership, require_document_ownership

# Manual verification
@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    user: UserInDB = Depends(get_current_active_user)
):
    if not await verify_document_ownership(document_id, user):
        raise AuthorizationError("Access denied")

    # Continue with logic
    ...

# Using dependency
@router.put("/documents/{document_id}")
async def update_document(
    document_id: str,
    user: UserInDB = Depends(require_document_ownership)
):
    # user is automatically verified to own the document
    ...
```

---

## Audit Logging

All authentication events are logged to the `audit_logs` table.

### Logged Events

| Event | Action Constant |
|-------|----------------|
| Registration | `AuditAction.REGISTER` |
| Login (success) | `AuditAction.LOGIN` |
| Login (failure) | `AuditAction.LOGIN` (status=failure) |
| Logout | `AuditAction.LOGOUT` |
| Token Refresh | `AuditAction.TOKEN_REFRESH` |
| Account Lockout | `AuditAction.ACCOUNT_LOCKED` |
| Password Reset Request | `AuditAction.PASSWORD_RESET_REQUEST` |
| Password Reset Complete | `AuditAction.PASSWORD_RESET_COMPLETE` |

### Log Entry Structure

```python
{
  "id": "uuid",
  "user_id": "user-uuid",
  "action": "login",
  "resource_type": "authentication",
  "status": "success",  # or "failure"
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "request_id": "a1b2c3d4-e5f6-7890",
  "metadata": {
    "email": "user@example.com"
  },
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Query Audit Logs

```python
from app.utils.audit_log import get_user_audit_logs, get_recent_failed_logins

# Get user's audit logs
logs = await get_user_audit_logs(user_id, limit=100)

# Get failed login attempts
failed_logins = await get_recent_failed_logins(email, since_minutes=60)
```

---

## Troubleshooting

### Invalid Credentials

**Problem**: Always getting 401 on login

**Solutions**:
1. Verify email is lowercase (automatically converted)
2. Check password meets strength requirements
3. Ensure account exists (check via database)
4. Verify account is active (`is_active=true`)

### Account Locked

**Problem**: Getting 423 error on login

**Solution**:
- Wait 60 minutes from first failed attempt
- Or admin can clear audit logs for the email
- Or manually update account status

### Token Expired

**Problem**: Getting 401 with "token expired" message

**Solution**:
- Use refresh token to get new access token
- Access tokens expire after 30 minutes (configurable)

### Rate Limit Exceeded

**Problem**: Getting 429 error

**Solution**:
- Wait for rate limit window to reset
- Check `Retry-After` header for wait time
- Implement exponential backoff in client

### Password Not Strong Enough

**Problem**: Registration fails with password validation error

**Solution**:
Password must contain:
- ✅ At least 8 characters
- ✅ One uppercase letter (A-Z)
- ✅ One lowercase letter (a-z)
- ✅ One digit (0-9)
- ✅ One special character (!@#$%^&*(),.?":{}|<>)

Examples:
- ❌ `password` - missing uppercase, digit, special
- ❌ `Password` - missing digit, special
- ❌ `Pass123` - missing special, too short
- ✅ `SecurePass123!` - valid

---

## Testing

### Manual Testing with cURL

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "full_name": "Test User"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!"
  }'

# Get current user (use token from login)
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"

# Logout
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer <access_token>"
```

---

## Configuration

Environment variables for authentication:

```bash
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-min-32-chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Password Hashing
BCRYPT_ROUNDS=12

# Rate Limiting
RATE_LIMIT_ENABLED=true
```

---

## Next Steps

1. ✅ Implement email verification
2. ✅ Add 2FA/MFA support
3. ✅ Implement OAuth providers (Google, GitHub)
4. ✅ Add session management (token blacklist)
5. ✅ Implement password history (prevent reuse)

---

## Security Best Practices

1. ✅ **Never log passwords** - Automatic masking in audit logs
2. ✅ **Use HTTPS** - Always in production
3. ✅ **Rotate JWT secrets** - Regularly change `JWT_SECRET_KEY`
4. ✅ **Monitor audit logs** - Watch for suspicious activity
5. ✅ **Set strong password policy** - Enforced by validation
6. ✅ **Implement rate limiting** - Prevent brute force attacks
7. ✅ **Use secure session storage** - HttpOnly cookies or secure storage
8. ✅ **Validate all inputs** - Pydantic models provide validation

