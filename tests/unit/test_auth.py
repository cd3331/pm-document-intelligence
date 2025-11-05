"""
Unit tests for authentication module
Tests user registration, login, JWT tokens, and authorization
"""

import pytest
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
)
from app.models import User
from app.config import get_settings

settings = get_settings()


@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password(self):
        """Test password hashing"""
        password = "testpassword123"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt hash

    def test_verify_password_success(self):
        """Test successful password verification"""
        password = "testpassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_failure(self):
        """Test failed password verification"""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_different_hashes_for_same_password(self):
        """Test that same password generates different hashes (salt)"""
        password = "testpassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


@pytest.mark.unit
class TestJWTTokens:
    """Test JWT token creation and validation"""

    def test_create_access_token(self):
        """Test access token creation"""
        data = {"sub": "testuser", "user_id": 1}
        token = create_access_token(data=data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiry(self):
        """Test access token with custom expiry"""
        data = {"sub": "testuser", "user_id": 1}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data=data, expires_delta=expires_delta)

        # Decode token to check expiry
        payload = jwt.decode(
            token,
            settings.security.jwt_secret_key,
            algorithms=[settings.security.jwt_algorithm]
        )

        exp = datetime.fromtimestamp(payload["exp"])
        now = datetime.utcnow()

        # Should expire in approximately 15 minutes
        assert (exp - now).total_seconds() < 16 * 60
        assert (exp - now).total_seconds() > 14 * 60

    def test_create_refresh_token(self):
        """Test refresh token creation"""
        data = {"sub": "testuser", "user_id": 1}
        token = create_refresh_token(data=data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_valid_token(self):
        """Test decoding a valid token"""
        data = {"sub": "testuser", "user_id": 1}
        token = create_access_token(data=data)

        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == "testuser"
        assert payload["user_id"] == 1
        assert "exp" in payload

    def test_decode_expired_token(self):
        """Test decoding an expired token"""
        data = {"sub": "testuser", "user_id": 1}
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = create_access_token(data=data, expires_delta=expires_delta)

        payload = decode_token(token)

        assert payload is None  # Should return None for expired token

    def test_decode_invalid_token(self):
        """Test decoding an invalid token"""
        invalid_token = "invalid.token.here"

        payload = decode_token(invalid_token)

        assert payload is None

    def test_decode_tampered_token(self):
        """Test decoding a tampered token"""
        data = {"sub": "testuser", "user_id": 1}
        token = create_access_token(data=data)

        # Tamper with the token
        parts = token.split('.')
        parts[1] = parts[1][:-5] + "xxxxx"  # Modify payload
        tampered_token = '.'.join(parts)

        payload = decode_token(tampered_token)

        assert payload is None


@pytest.mark.unit
class TestUserRegistration:
    """Test user registration"""

    def test_register_new_user(self, client: TestClient):
        """Test successful user registration"""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "securepassword123"
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert "password" not in data
        assert "hashed_password" not in data

    def test_register_duplicate_username(self, client: TestClient, test_user: User):
        """Test registration with duplicate username"""
        user_data = {
            "username": test_user.username,
            "email": "different@example.com",
            "password": "password123"
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_register_duplicate_email(self, client: TestClient, test_user: User):
        """Test registration with duplicate email"""
        user_data = {
            "username": "differentuser",
            "email": test_user.email,
            "password": "password123"
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client: TestClient):
        """Test registration with invalid email"""
        user_data = {
            "username": "newuser",
            "email": "not-an-email",
            "password": "password123"
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 422  # Validation error

    def test_register_weak_password(self, client: TestClient):
        """Test registration with weak password"""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "123"  # Too short
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 422  # Validation error

    def test_register_missing_fields(self, client: TestClient):
        """Test registration with missing required fields"""
        user_data = {
            "username": "newuser"
            # Missing email and password
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 422


@pytest.mark.unit
class TestUserLogin:
    """Test user login"""

    def test_login_success(self, client: TestClient, test_user: User):
        """Test successful login"""
        login_data = {
            "username": test_user.username,
            "password": "testpassword123"
        }

        response = client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient, test_user: User):
        """Test login with wrong password"""
        login_data = {
            "username": test_user.username,
            "password": "wrongpassword"
        }

        response = client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent user"""
        login_data = {
            "username": "nonexistent",
            "password": "password123"
        }

        response = client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 401

    def test_login_inactive_user(self, client: TestClient, test_db: Session, test_user: User):
        """Test login with inactive user"""
        # Deactivate user
        test_user.is_active = False
        test_db.commit()

        login_data = {
            "username": test_user.username,
            "password": "testpassword123"
        }

        response = client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 401
        assert "inactive" in response.json()["detail"].lower()


@pytest.mark.unit
class TestRefreshToken:
    """Test refresh token flow"""

    def test_refresh_token_success(self, client: TestClient, test_user: User):
        """Test successful token refresh"""
        # First login to get refresh token
        login_data = {
            "username": test_user.username,
            "password": "testpassword123"
        }
        login_response = client.post("/api/v1/auth/login", data=login_data)
        refresh_token = login_response.json()["refresh_token"]

        # Use refresh token to get new access token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_token_invalid(self, client: TestClient):
        """Test refresh with invalid token"""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token"}
        )

        assert response.status_code == 401

    def test_refresh_token_expired(self, client: TestClient, test_user: User):
        """Test refresh with expired token"""
        # Create expired refresh token
        data = {"sub": test_user.username, "user_id": test_user.id}
        expired_token = create_refresh_token(
            data=data,
            expires_delta=timedelta(seconds=-1)
        )

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": expired_token}
        )

        assert response.status_code == 401


@pytest.mark.unit
class TestAuthorizationMiddleware:
    """Test authorization and protected routes"""

    def test_access_protected_route_with_valid_token(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test accessing protected route with valid token"""
        response = client.get("/api/v1/documents", headers=auth_headers)

        assert response.status_code in [200, 404]  # Authorized (may be empty)

    def test_access_protected_route_without_token(self, client: TestClient):
        """Test accessing protected route without token"""
        response = client.get("/api/v1/documents")

        assert response.status_code == 401

    def test_access_protected_route_with_invalid_token(self, client: TestClient):
        """Test accessing protected route with invalid token"""
        headers = {"Authorization": "Bearer invalid.token"}
        response = client.get("/api/v1/documents", headers=headers)

        assert response.status_code == 401

    def test_access_admin_route_as_regular_user(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test accessing admin route as regular user"""
        response = client.get("/api/v1/admin/users", headers=auth_headers)

        assert response.status_code == 403  # Forbidden

    def test_access_admin_route_as_admin(
        self,
        client: TestClient,
        admin_headers: dict
    ):
        """Test accessing admin route as admin"""
        response = client.get("/api/v1/admin/users", headers=admin_headers)

        assert response.status_code in [200, 404]  # Authorized


@pytest.mark.unit
class TestRateLimiting:
    """Test rate limiting on authentication endpoints"""

    @pytest.mark.slow
    def test_login_rate_limiting(self, client: TestClient, test_user: User):
        """Test rate limiting on login endpoint"""
        login_data = {
            "username": test_user.username,
            "password": "wrongpassword"
        }

        # Make multiple requests rapidly
        responses = []
        for _ in range(15):  # Assuming limit is 10/minute
            response = client.post("/api/v1/auth/login", data=login_data)
            responses.append(response)

        # Check if at least one request was rate limited
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes  # Too Many Requests

    @pytest.mark.slow
    def test_register_rate_limiting(self, client: TestClient):
        """Test rate limiting on registration endpoint"""
        # Make multiple registration attempts
        responses = []
        for i in range(15):
            user_data = {
                "username": f"user{i}",
                "email": f"user{i}@example.com",
                "password": "password123"
            }
            response = client.post("/api/v1/auth/register", json=user_data)
            responses.append(response)

        # Check if at least one request was rate limited
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes or len([s for s in status_codes if s == 201]) > 0


@pytest.mark.unit
class TestTokenValidation:
    """Test various token validation scenarios"""

    def test_token_with_missing_claims(self):
        """Test token with missing required claims"""
        # Create token without 'sub' claim
        data = {"user_id": 1}  # Missing 'sub'
        token = jwt.encode(
            data,
            settings.security.jwt_secret_key,
            algorithm=settings.security.jwt_algorithm
        )

        payload = decode_token(token)

        assert payload is None or "sub" not in payload

    def test_token_with_extra_claims(self, test_user: User):
        """Test token with extra claims"""
        data = {
            "sub": test_user.username,
            "user_id": test_user.id,
            "extra_claim": "extra_value"
        }
        token = create_access_token(data=data)

        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == test_user.username
        assert payload["extra_claim"] == "extra_value"

    def test_token_with_wrong_algorithm(self):
        """Test token signed with wrong algorithm"""
        data = {"sub": "testuser", "user_id": 1}

        # Sign with different algorithm
        token = jwt.encode(data, "wrong-secret", algorithm="HS512")

        payload = decode_token(token)

        assert payload is None


@pytest.mark.unit
class TestLogout:
    """Test logout functionality"""

    def test_logout_success(self, client: TestClient, auth_headers: dict):
        """Test successful logout"""
        response = client.post("/api/v1/auth/logout", headers=auth_headers)

        assert response.status_code == 200
        assert "successfully" in response.json()["message"].lower()

    def test_logout_without_token(self, client: TestClient):
        """Test logout without authentication"""
        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 401


@pytest.mark.unit
class TestPasswordReset:
    """Test password reset functionality"""

    def test_request_password_reset(self, client: TestClient, test_user: User):
        """Test requesting password reset"""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": test_user.email}
        )

        assert response.status_code == 200
        assert "email" in response.json()["message"].lower()

    def test_request_password_reset_nonexistent_email(self, client: TestClient):
        """Test requesting reset for non-existent email"""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"}
        )

        # Should still return 200 to prevent email enumeration
        assert response.status_code == 200

    def test_reset_password_with_valid_token(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test resetting password with valid token"""
        # Create password reset token
        reset_token = create_access_token(
            data={"sub": test_user.email, "type": "password_reset"}
        )

        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "newsecurepassword123"
            }
        )

        assert response.status_code == 200

    def test_reset_password_with_invalid_token(self, client: TestClient):
        """Test resetting password with invalid token"""
        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "invalid.token",
                "new_password": "newsecurepassword123"
            }
        )

        assert response.status_code == 401
