"""
Security Middleware for PM Document Intelligence.

This module provides comprehensive security headers and request tracking middleware
to protect against common web vulnerabilities and enable request tracing.

Features:
- Content Security Policy (CSP) headers
- HTTP Strict Transport Security (HSTS)
- X-Frame-Options to prevent clickjacking
- X-Content-Type-Options to prevent MIME sniffing
- XSS Protection headers
- Request ID generation and tracking
- Security event logging
- Rate limiting integration
- CORS preflight handling

Usage:
    from fastapi import FastAPI
    from app.middleware.security import SecurityHeadersMiddleware, RequestTrackingMiddleware

    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestTrackingMiddleware)
"""

import time
import uuid
from collections.abc import Callable

from app.cache.redis import get_cache_ttl, increment_cache
from app.config import settings
from app.utils.logger import (
    clear_request_context,
    get_structured_logger,
    set_request_context,
)
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = get_structured_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    This middleware adds various security headers to protect against
    common web vulnerabilities including XSS, clickjacking, MIME sniffing,
    and other attacks.

    Security Headers Added:
        - Content-Security-Policy: Controls resource loading
        - Strict-Transport-Security: Enforces HTTPS
        - X-Frame-Options: Prevents clickjacking
        - X-Content-Type-Options: Prevents MIME sniffing
        - X-XSS-Protection: Enables XSS filtering
        - Referrer-Policy: Controls referrer information
        - Permissions-Policy: Controls browser features
    """

    def __init__(
        self,
        app: ASGIApp,
        enable_hsts: bool = True,
        hsts_max_age: int = 31536000,
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
        csp_directives: dict[str, str] | None = None,
    ):
        """
        Initialize security headers middleware.

        Args:
            app: ASGI application
            enable_hsts: Enable HTTP Strict Transport Security
            hsts_max_age: HSTS max-age in seconds (default 1 year)
            hsts_include_subdomains: Include subdomains in HSTS
            hsts_preload: Enable HSTS preload
            csp_directives: Custom CSP directives
        """
        super().__init__(app)
        self.enable_hsts = enable_hsts and settings.is_production
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        self.csp_directives = csp_directives or self._default_csp_directives()

    def _default_csp_directives(self) -> dict[str, str]:
        """
        Get default Content Security Policy directives.

        Returns:
            Dictionary of CSP directives

        Security Notes:
            - 'unsafe-eval' removed: No eval() usage in codebase
            - 'unsafe-inline' kept: Required for inline scripts in Jinja2 templates
            - TODO: Implement nonce-based CSP for inline scripts (future improvement)
        """
        if settings.is_production:
            return {
                "default-src": "'self'",
                # Script sources: removed unsafe-eval, kept unsafe-inline for templates
                # Explicit CDN allowlist for external libraries
                "script-src": " ".join([
                    "'self'",
                    "'unsafe-inline'",  # TODO: Replace with nonce-based CSP
                    "https://cdn.tailwindcss.com",
                    "https://unpkg.com",
                    "https://cdn.jsdelivr.net",
                    "https://cdn.pubnub.com",
                ]),
                # Style sources: kept unsafe-inline for Tailwind and inline styles
                "style-src": " ".join([
                    "'self'",
                    "'unsafe-inline'",  # TODO: Replace with nonce-based CSP
                    "https://cdn.tailwindcss.com",
                    "https://cdn.jsdelivr.net",
                ]),
                "img-src": "'self' data: https:",
                "font-src": "'self' data:",
                # Connect sources: Updated for RDS migration (removed Supabase)
                "connect-src": " ".join([
                    "'self'",
                    "https://api.openai.com",
                    "https://pubsub.pubnub.com",
                    "https://*.pubnub.com",
                ]),
                "frame-ancestors": "'none'",
                "base-uri": "'self'",
                "form-action": "'self'",
                "upgrade-insecure-requests": "",
            }
        else:
            # More permissive CSP for development
            return {
                "default-src": "'self' 'unsafe-inline'",  # Removed unsafe-eval
                "script-src": "'self' 'unsafe-inline' http: https:",
                "style-src": "'self' 'unsafe-inline' http: https:",
                "img-src": "'self' data: https: http:",
                "connect-src": "'self' http://localhost:* https://*",
            }

    def _build_csp_header(self) -> str:
        """
        Build Content Security Policy header value.

        Returns:
            CSP header string
        """
        return "; ".join(
            f"{key} {value}" if value else key for key, value in self.csp_directives.items()
        )

    def _build_hsts_header(self) -> str:
        """
        Build HTTP Strict Transport Security header value.

        Returns:
            HSTS header string
        """
        hsts_parts = [f"max-age={self.hsts_max_age}"]

        if self.hsts_include_subdomains:
            hsts_parts.append("includeSubDomains")

        if self.hsts_preload:
            hsts_parts.append("preload")

        return "; ".join(hsts_parts)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add security headers to response.

        Args:
            request: Incoming request
            call_next: Next middleware or endpoint

        Returns:
            Response with security headers
        """
        # Process request
        response = await call_next(request)

        # Add security headers
        self._add_security_headers(response)

        return response

    def _add_security_headers(self, response: Response) -> None:
        """
        Add all security headers to the response.

        Args:
            response: Response object to modify
        """
        # Content Security Policy
        response.headers["Content-Security-Policy"] = self._build_csp_header()

        # HTTP Strict Transport Security (HTTPS only)
        if self.enable_hsts:
            response.headers["Strict-Transport-Security"] = self._build_hsts_header()

        # X-Frame-Options: Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options: Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-XSS-Protection: Enable XSS filter
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy: Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy: Control browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )

        # X-Permitted-Cross-Domain-Policies: Restrict cross-domain policies
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        # Cache-Control for sensitive endpoints
        if settings.is_production:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request tracking and performance monitoring.

    This middleware:
    - Generates unique request IDs
    - Tracks request duration
    - Logs all requests with structured data
    - Sets request context for logging
    - Monitors security events

    The request ID is added to response headers and can be used for
    distributed tracing across services.
    """

    def __init__(
        self,
        app: ASGIApp,
        enable_performance_logging: bool = True,
        slow_request_threshold_ms: float = 1000.0,
    ):
        """
        Initialize request tracking middleware.

        Args:
            app: ASGI application
            enable_performance_logging: Enable performance logging
            slow_request_threshold_ms: Threshold for slow request warnings (ms)
        """
        super().__init__(app)
        self.enable_performance_logging = enable_performance_logging
        self.slow_request_threshold_ms = slow_request_threshold_ms

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with tracking and logging.

        Args:
            request: Incoming request
            call_next: Next middleware or endpoint

        Returns:
            Response with tracking headers
        """
        # Generate request ID
        request_id = self._generate_request_id(request)
        request.state.request_id = request_id

        # Extract user ID if available (from auth)
        user_id = self._extract_user_id(request)

        # Set request context for logging
        set_request_context(request_id, user_id)

        # Track request start time
        start_time = time.time()

        # Log request start
        logger.logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "event": "request_start",
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
        )

        # Check for potential security issues
        self._check_security_concerns(request)

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Add tracking headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            # Log request completion
            if self.enable_performance_logging:
                if duration_ms > self.slow_request_threshold_ms:
                    pass

                logger.log_api_request(
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    user_id=user_id,
                )

                if duration_ms > self.slow_request_threshold_ms:
                    logger.logger.warning(
                        f"Slow request detected: {request.method} {request.url.path}",
                        extra={
                            "event": "slow_request",
                            "duration_ms": duration_ms,
                            "threshold_ms": self.slow_request_threshold_ms,
                        },
                    )

            return response

        except Exception as e:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            logger.logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "event": "request_error",
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(e),
                },
                exc_info=True,
            )

            raise

        finally:
            # Clear request context
            clear_request_context()

    def _generate_request_id(self, request: Request) -> str:
        """
        Generate or extract request ID.

        Args:
            request: Incoming request

        Returns:
            Unique request ID
        """
        # Check if request already has an ID (from upstream proxy)
        request_id = request.headers.get("X-Request-ID")

        if not request_id:
            # Generate new UUID-based request ID
            request_id = str(uuid.uuid4())

        return request_id

    def _extract_user_id(self, request: Request) -> str | None:
        """
        Extract user ID from request if authenticated.

        Args:
            request: Incoming request

        Returns:
            User ID if available, None otherwise
        """
        # Try to get user from request state (set by auth middleware)
        if hasattr(request.state, "user"):
            user = request.state.user
            if hasattr(user, "id"):
                return str(user.id)
            elif isinstance(user, dict) and "id" in user:
                return str(user["id"])

        # Try to extract from JWT claims
        if hasattr(request.state, "jwt_claims"):
            claims = request.state.jwt_claims
            if isinstance(claims, dict):
                return claims.get("sub") or claims.get("user_id")

        return None

    def _check_security_concerns(self, request: Request) -> None:
        """
        Check for potential security concerns in the request.

        Args:
            request: Incoming request
        """
        # Check for suspicious patterns
        suspicious_patterns = [
            "../",  # Path traversal
            "<script",  # XSS attempt
            "union select",  # SQL injection
            "drop table",  # SQL injection
            "exec(",  # Command injection
        ]

        # Check URL and query params
        url_str = str(request.url).lower()
        for pattern in suspicious_patterns:
            if pattern in url_str:
                logger.log_security_event(
                    event_type="suspicious_request",
                    severity="medium",
                    description=f"Suspicious pattern detected: {pattern}",
                    pattern=pattern,
                    method=request.method,
                    path=request.url.path,
                    client_host=request.client.host if request.client else None,
                )

        # Check for missing security headers in request
        if settings.is_production:
            # Check for missing Origin header on POST/PUT/DELETE
            if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
                origin = request.headers.get("origin")
                referer = request.headers.get("referer")

                if not origin and not referer:
                    logger.log_security_event(
                        event_type="missing_origin_header",
                        severity="low",
                        description="Request missing both Origin and Referer headers",
                        method=request.method,
                        path=request.url.path,
                    )

        # Check for excessively long URLs (potential DoS)
        if len(str(request.url)) > 2048:
            logger.log_security_event(
                event_type="long_url",
                severity="low",
                description="Excessively long URL detected",
                url_length=len(str(request.url)),
                path=request.url.path,
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent abuse.

    This middleware enforces rate limits on API endpoints to prevent
    abuse and ensure fair resource usage. It integrates with Redis
    for distributed rate limiting across multiple instances.
    """

    def __init__(
        self,
        app: ASGIApp,
        enabled: bool = True,
        default_limit: str = "100/minute",
    ):
        """
        Initialize rate limit middleware.

        Args:
            app: ASGI application
            enabled: Enable rate limiting
            default_limit: Default rate limit string (e.g., "100/minute")
        """
        super().__init__(app)
        self.enabled = enabled and settings.rate_limit.rate_limit_enabled
        self.default_limit = default_limit

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware or endpoint

        Returns:
            Response or 429 Too Many Requests
        """
        if not self.enabled:
            return await call_next(request)

        # Get client identifier (IP or user ID)
        client_id = self._get_client_identifier(request)

        # Get rate limit for this endpoint
        limit_key = self._get_limit_key(request)

        # Check rate limit
        is_allowed, retry_after = await self._check_rate_limit(client_id, limit_key)

        if not is_allowed:
            # Log rate limit exceeded
            logger.log_security_event(
                event_type="rate_limit_exceeded",
                severity="medium",
                description="Rate limit exceeded",
                client_id=client_id,
                path=request.url.path,
                retry_after=retry_after,
            )

            # Return 429 response
            return Response(
                content='{"detail": "Rate limit exceeded. Please try again later."}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": self.default_limit,
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Process request
        return await call_next(request)

    def _get_client_identifier(self, request: Request) -> str:
        """
        Get unique client identifier for rate limiting.

        Args:
            request: Incoming request

        Returns:
            Client identifier (user ID or IP address)
        """
        # Use user ID if authenticated
        if hasattr(request.state, "user"):
            user = request.state.user
            if hasattr(user, "id"):
                return f"user:{user.id}"
            elif isinstance(user, dict) and "id" in user:
                return f"user:{user['id']}"

        # Use IP address for unauthenticated requests
        if request.client:
            return f"ip:{request.client.host}"

        # Fallback
        return "unknown"

    def _get_limit_key(self, request: Request) -> str:
        """
        Get rate limit key for the request path.

        Args:
            request: Incoming request

        Returns:
            Rate limit key
        """
        # Map paths to rate limit configurations
        path = request.url.path

        if "/upload" in path:
            return "upload"
        elif "/process" in path:
            return "process"
        elif "/query" in path or "/search" in path:
            return "query"
        else:
            return "default"

    async def _check_rate_limit(self, client_id: str, limit_key: str) -> tuple[bool, int]:
        """
        Check if request is within rate limit using Redis-based fixed-window counter.

        Algorithm:
        1. Build rate limit key with current time window
        2. Increment counter atomically in Redis
        3. Set TTL on first increment
        4. Check if counter exceeds limit
        5. Return result with retry-after seconds

        Args:
            client_id: Client identifier
            limit_key: Rate limit key

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        try:
            # Get rate limit configuration for this endpoint
            limit_config = self._get_rate_limit_config(limit_key)
            limit = limit_config["limit"]
            window_seconds = limit_config["window_seconds"]

            # Build Redis key with current time window
            # This creates a new counter for each time window (fixed-window algorithm)
            current_window = int(time.time() / window_seconds)
            redis_key = f"ratelimit:{limit_key}:{client_id}:{current_window}"

            # Increment counter atomically
            # The increment_cache function handles TTL setting for new keys
            current_count = await increment_cache(
                key=redis_key,
                amount=1,
                prefix=None,  # Key already has full prefix
                ttl=window_seconds,
            )

            # If Redis is unavailable, allow the request (fail open for availability)
            if current_count is None:
                logger.warning(
                    "Rate limiting unavailable (Redis error), allowing request",
                    extra={"client_id": client_id, "limit_key": limit_key},
                )
                return True, 0

            # Check if limit exceeded
            if current_count > limit:
                # Calculate retry-after: remaining time in current window
                ttl = await get_cache_ttl(redis_key, prefix=None)
                retry_after = ttl if ttl and ttl > 0 else window_seconds

                logger.info(
                    f"Rate limit exceeded: {current_count}/{limit}",
                    extra={
                        "client_id": client_id,
                        "limit_key": limit_key,
                        "current_count": current_count,
                        "limit": limit,
                        "retry_after": retry_after,
                    },
                )

                return False, retry_after

            # Log if approaching limit (80% threshold)
            if current_count >= limit * 0.8:
                logger.debug(
                    f"Rate limit approaching: {current_count}/{limit}",
                    extra={
                        "client_id": client_id,
                        "limit_key": limit_key,
                        "current_count": current_count,
                        "limit": limit,
                    },
                )

            return True, 0

        except Exception as e:
            # Fail open: allow request if rate limiting fails
            logger.error(
                f"Rate limiting error: {e}",
                extra={"client_id": client_id, "limit_key": limit_key},
                exc_info=True,
            )
            return True, 0

    def _get_rate_limit_config(self, limit_key: str) -> dict[str, int]:
        """
        Get rate limit configuration for a specific endpoint.

        Args:
            limit_key: Rate limit key

        Returns:
            Dictionary with 'limit' and 'window_seconds'
        """
        # Parse rate limit configuration from settings
        # Format: "N/period" where period is minute, hour, day
        if limit_key == "upload":
            limit_str = settings.rate_limit.rate_limit_upload
        elif limit_key == "process":
            limit_str = settings.rate_limit.rate_limit_process
        elif limit_key == "query":
            limit_str = settings.rate_limit.rate_limit_query
        else:
            limit_str = settings.rate_limit.rate_limit_default

        # Parse limit string (e.g., "100/minute")
        parts = limit_str.split("/")
        limit = int(parts[0])

        # Convert period to seconds
        period = parts[1].lower()
        if period.startswith("second"):
            window_seconds = 1
        elif period.startswith("minute"):
            window_seconds = 60
        elif period.startswith("hour"):
            window_seconds = 3600
        elif period.startswith("day"):
            window_seconds = 86400
        else:
            # Default to minute
            window_seconds = 60

        return {"limit": limit, "window_seconds": window_seconds}


def setup_security_middleware(app: ASGIApp) -> None:
    """
    Setup all security middleware for the application.

    Args:
        app: FastAPI application instance
    """
    from fastapi import FastAPI

    if isinstance(app, FastAPI):
        # Add middleware in reverse order (last added = first executed)
        app.add_middleware(RateLimitMiddleware)
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(RequestTrackingMiddleware)

        logger.logger.info("Security middleware configured successfully")
