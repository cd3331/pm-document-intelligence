"""
PM Document Intelligence - Main FastAPI Application.

This module initializes and configures the FastAPI application with:
- Production-grade security and monitoring
- Comprehensive error handling
- Rate limiting and request tracking
- Health checks and metrics
- Route registration
- Middleware stack

The application follows best practices for production deployment including
graceful startup/shutdown, connection pooling, and observability.

Usage:
    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import time
from contextlib import asynccontextmanager
from typing import Any

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.middleware.security import (
    RequestTrackingMiddleware,
    SecurityHeadersMiddleware,
)
from app.utils.exceptions import (
    BaseAPIException,
    api_exception_handler,
    generic_exception_handler,
)
from app.utils.logger import (
    get_logger,
    get_structured_logger,
    init_logging_from_config,
)

# Initialize logging
init_logging_from_config()
logger = get_logger(__name__)
structured_logger = get_structured_logger(__name__)


# ============================================================================
# Prometheus Metrics
# ============================================================================

# Request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "endpoint"],
)

# Document processing metrics
document_processing_total = Counter(
    "document_processing_total",
    "Total documents processed",
    ["status"],
)

document_processing_duration_seconds = Histogram(
    "document_processing_duration_seconds",
    "Document processing duration in seconds",
)

# AI service metrics
ai_service_requests_total = Counter(
    "ai_service_requests_total",
    "Total AI service requests",
    ["service", "operation"],
)

ai_service_tokens_total = Counter(
    "ai_service_tokens_total",
    "Total AI service tokens consumed",
    ["service"],
)

# Error metrics
errors_total = Counter(
    "errors_total",
    "Total errors",
    ["error_type", "endpoint"],
)


# ============================================================================
# Lifespan Manager
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown operations.

    Startup:
        - Initialize Sentry for error tracking
        - Test database connections
        - Verify AWS service availability
        - Initialize Redis cache
        - Log startup metrics

    Shutdown:
        - Close database connections
        - Flush metrics
        - Close Redis connections
        - Log shutdown metrics
    """
    # ========================================================================
    # STARTUP
    # ========================================================================
    logger.info("=" * 80)
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug Mode: {settings.debug}")
    logger.info("=" * 80)

    startup_errors: list[str] = []

    # Initialize Sentry for error tracking
    if settings.monitoring.sentry_enabled and settings.monitoring.sentry_dsn:
        try:
            sentry_sdk.init(
                dsn=settings.monitoring.sentry_dsn,
                environment=settings.monitoring.sentry_environment,
                traces_sample_rate=settings.monitoring.sentry_traces_sample_rate,
                profiles_sample_rate=settings.monitoring.sentry_profiles_sample_rate,
                enable_tracing=True,
            )
            logger.info("✓ Sentry initialized successfully")
        except Exception as e:
            error_msg = f"Failed to initialize Sentry: {e}"
            logger.error(error_msg, exc_info=True)
            startup_errors.append(error_msg)

    # Test database connection
    try:
        from app.db.session import test_database_connection

        db_connected = await test_database_connection()
        if db_connected:
            logger.info("✓ Database connection successful")
        else:
            error_msg = "Database connection failed"
            logger.warning(error_msg)
            startup_errors.append(error_msg)
    except Exception as e:
        error_msg = f"Database connection error: {e}"
        logger.error(error_msg, exc_info=True)
        startup_errors.append(error_msg)

    # Test AWS services
    try:
        from app.services.aws import test_aws_services

        aws_status = await test_aws_services()
        if aws_status.get("all_available"):
            logger.info("✓ AWS services available")
        else:
            error_msg = f"Some AWS services unavailable: {aws_status}"
            logger.warning(error_msg)
            startup_errors.append(error_msg)
    except Exception as e:
        error_msg = f"AWS services check error: {e}"
        logger.error(error_msg, exc_info=True)
        startup_errors.append(error_msg)

    # Initialize Redis cache
    try:
        from app.cache.redis import initialize_cache, test_redis_connection

        redis_connected = await test_redis_connection()
        if redis_connected:
            await initialize_cache()
            logger.info("✓ Redis cache initialized")
        else:
            error_msg = "Redis connection failed"
            logger.warning(error_msg)
            startup_errors.append(error_msg)
    except Exception as e:
        error_msg = f"Redis initialization error: {e}"
        logger.error(error_msg, exc_info=True)
        startup_errors.append(error_msg)

    # Initialize AI agents
    try:
        from app.agents.orchestrator import initialize_agents

        initialize_agents()
        logger.info("✓ AI agents initialized and registered")
    except Exception as e:
        error_msg = f"Agent initialization error: {e}"
        logger.error(error_msg, exc_info=True)
        startup_errors.append(error_msg)

    # Initialize MCP server
    try:
        from app.mcp import initialize_mcp

        initialize_mcp()
        logger.info("✓ MCP server initialized with tools and resources")
    except Exception as e:
        error_msg = f"MCP initialization error: {e}"
        logger.error(error_msg, exc_info=True)
        startup_errors.append(error_msg)

    # Initialize PubNub for real-time updates
    try:
        from app.services.pubnub_service import initialize_pubnub

        initialize_pubnub()
        logger.info("✓ PubNub service initialized for real-time updates")
    except Exception as e:
        error_msg = f"PubNub initialization error: {e}"
        logger.error(error_msg, exc_info=True)
        startup_errors.append(error_msg)

    # Log startup summary
    logger.info("=" * 80)
    if startup_errors:
        logger.warning(f"Application started with {len(startup_errors)} warnings:")
        for error in startup_errors:
            logger.warning(f"  - {error}")
        logger.warning("Application running in degraded mode")
    else:
        logger.info("✓ All services initialized successfully")

    logger.info(f"Application ready at http://{settings.host}:{settings.port}")
    logger.info("=" * 80)

    # Store startup errors in app state
    app.state.startup_errors = startup_errors

    yield

    # ========================================================================
    # SHUTDOWN
    # ========================================================================
    logger.info("=" * 80)
    logger.info("Shutting down application...")
    logger.info("=" * 80)

    # Close database connections
    try:
        from app.db.session import close_database_connections

        await close_database_connections()
        logger.info("✓ Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}", exc_info=True)

    # Close Redis connections
    try:
        from app.cache.redis import close_redis_connections

        await close_redis_connections()
        logger.info("✓ Redis connections closed")
    except Exception as e:
        logger.error(f"Error closing Redis connections: {e}", exc_info=True)

    # Final metrics flush
    try:
        logger.info("✓ Metrics flushed")
    except Exception as e:
        logger.error(f"Error flushing metrics: {e}", exc_info=True)

    logger.info("=" * 80)
    logger.info("Shutdown complete")
    logger.info("=" * 80)


# ============================================================================
# Application Initialization
# ============================================================================

app = FastAPI(
    title=settings.app_name,
    description="AI-powered document intelligence and analysis platform for project managers",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.debug,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)


# ============================================================================
# Rate Limiting Setup
# ============================================================================


def get_limiter_key(request: Request) -> str:
    """
    Get rate limiter key based on user or IP address.

    Args:
        request: FastAPI request object

    Returns:
        Unique identifier for rate limiting
    """
    # Use user ID if authenticated
    if hasattr(request.state, "user"):
        user = request.state.user
        if hasattr(user, "id"):
            return f"user:{user.id}"
        elif isinstance(user, dict) and "id" in user:
            return f"user:{user['id']}"

    # Fallback to IP address
    return get_remote_address(request)


# Initialize rate limiter
limiter = Limiter(
    key_func=get_limiter_key,
    default_limits=(["1000/hour", "100/minute"] if settings.rate_limit.rate_limit_enabled else []),
    storage_uri=(str(settings.redis.redis_url) if settings.rate_limit.rate_limit_enabled else None),
    strategy=settings.rate_limit.rate_limit_strategy,
    enabled=settings.rate_limit.rate_limit_enabled,
)

# Add rate limiter to app state
app.state.limiter = limiter


# ============================================================================
# Middleware Configuration
# ============================================================================


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Middleware to track request timing and add metrics."""

    async def dispatch(self, request: Request, call_next):
        """Process request with timing."""
        start_time = time.time()

        # Track in-progress requests
        endpoint = request.url.path
        method = request.method
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Record metrics
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)

            return response

        except Exception as e:
            # Record error metrics
            errors_total.labels(
                error_type=type(e).__name__,
                endpoint=endpoint,
            ).inc()
            raise

        finally:
            # Decrement in-progress counter
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()


# Add middleware in correct order (reverse order of execution)
# Last added = First executed

# 1. CORS Middleware (should be first to execute)
if settings.cors_origins_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time"],
    )
    logger.info(f"✓ CORS enabled for origins: {settings.cors_origins_list}")

# 2. Trusted Host Middleware
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts_list,
    )
    logger.info(f"✓ Trusted hosts configured: {settings.allowed_hosts_list}")

# 3. Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# 4. Request Tracking Middleware
app.add_middleware(RequestTrackingMiddleware)

# 5. Request Timing Middleware
app.add_middleware(RequestTimingMiddleware)

# 6. Rate Limiting Middleware
if settings.rate_limit.rate_limit_enabled:
    app.add_middleware(SlowAPIMiddleware)
    logger.info("✓ Rate limiting enabled")

# 7. Compression Middleware (should be last to execute, first to add)
if settings.gzip_enabled:
    app.add_middleware(
        GZipMiddleware,
        minimum_size=settings.gzip_min_size,
        compresslevel=settings.compression_level,
    )
    logger.info("✓ GZIP compression enabled")


# ============================================================================
# Error Handlers
# ============================================================================


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Handle request validation errors (422).

    Args:
        request: FastAPI request object
        exc: Validation error exception

    Returns:
        JSON response with validation error details
    """
    errors_total.labels(
        error_type="ValidationError",
        endpoint=request.url.path,
    ).inc()

    logger.warning(
        f"Validation error on {request.method} {request.url.path}",
        extra={
            "errors": exc.errors(),
            "body": exc.body,
        },
    )

    # Format validation errors
    formatted_errors = []
    for error in exc.errors():
        formatted_errors.append(
            {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    response_data = {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": {
                "validation_errors": formatted_errors,
            },
            "status_code": 422,
        }
    }

    if hasattr(request.state, "request_id"):
        response_data["request_id"] = request.state.request_id

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response_data,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """
    Handle HTTP exceptions.

    Args:
        request: FastAPI request object
        exc: HTTP exception

    Returns:
        JSON response with error details
    """
    errors_total.labels(
        error_type="HTTPException",
        endpoint=request.url.path,
    ).inc()

    logger.warning(
        f"HTTP exception on {request.method} {request.url.path}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
        },
    )

    response_data = {
        "error": {
            "code": "HTTP_ERROR",
            "message": (exc.detail if isinstance(exc.detail, str) else "An error occurred"),
            "status_code": exc.status_code,
        }
    }

    if hasattr(request.state, "request_id"):
        response_data["request_id"] = request.state.request_id

    return JSONResponse(
        status_code=exc.status_code,
        content=response_data,
        headers=exc.headers,
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    """
    Handle rate limit exceeded errors (429).

    Args:
        request: FastAPI request object
        exc: Rate limit exceeded exception

    Returns:
        JSON response with retry information
    """
    errors_total.labels(
        error_type="RateLimitExceeded",
        endpoint=request.url.path,
    ).inc()

    structured_logger.log_security_event(
        event_type="rate_limit_exceeded",
        severity="medium",
        description=f"Rate limit exceeded on {request.url.path}",
        path=request.url.path,
        method=request.method,
    )

    response_data = {
        "error": {
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "Rate limit exceeded. Please try again later.",
            "status_code": 429,
        }
    }

    if hasattr(request.state, "request_id"):
        response_data["request_id"] = request.state.request_id

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=response_data,
        headers={"Retry-After": "60"},
    )


# Register custom exception handlers
app.add_exception_handler(BaseAPIException, api_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


# ============================================================================
# Health Check & Monitoring Endpoints
# ============================================================================


@app.get(
    settings.health_check_path,
    tags=["monitoring"],
    summary="Health check endpoint",
    response_model=None,
)
async def health_check() -> dict[str, Any]:
    """
    Comprehensive health check endpoint.

    Checks:
        - Application status
        - Database connectivity
        - AWS services availability
        - Redis cache connectivity
        - Overall system health

    Returns:
        Detailed health status JSON
    """
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": settings.environment,
        "version": "1.0.0",
        "checks": {},
    }

    all_healthy = True

    # Check database
    try:
        from app.db.session import test_database_connection

        db_healthy = await test_database_connection()
        health_status["checks"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "message": (
                "Database connection successful" if db_healthy else "Database connection failed"
            ),
        }
        if not db_healthy:
            all_healthy = False
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database check error: {str(e)}",
        }
        all_healthy = False

    # Check AWS services
    try:
        from app.services.aws import test_aws_services

        aws_status = await test_aws_services()
        health_status["checks"]["aws"] = {
            "status": "healthy" if aws_status.get("all_available") else "degraded",
            "services": aws_status,
        }
        if not aws_status.get("all_available"):
            all_healthy = False
    except Exception as e:
        health_status["checks"]["aws"] = {
            "status": "unhealthy",
            "message": f"AWS check error: {str(e)}",
        }
        all_healthy = False

    # Check Redis
    try:
        from app.cache.redis import test_redis_connection

        redis_healthy = await test_redis_connection()
        health_status["checks"]["redis"] = {
            "status": "healthy" if redis_healthy else "unhealthy",
            "message": (
                "Redis connection successful" if redis_healthy else "Redis connection failed"
            ),
        }
        if not redis_healthy:
            all_healthy = False
    except Exception as e:
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis check error: {str(e)}",
        }
        all_healthy = False

    # Update overall status
    if not all_healthy:
        health_status["status"] = "degraded"

    # Include startup errors if any
    if hasattr(app.state, "startup_errors") and app.state.startup_errors:
        health_status["startup_errors"] = app.state.startup_errors
        health_status["status"] = "degraded"

    # Return appropriate status code
    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(content=health_status, status_code=status_code)


@app.get(
    settings.readiness_check_path,
    tags=["monitoring"],
    summary="Readiness check endpoint",
)
async def readiness_check() -> dict[str, Any]:
    """
    Kubernetes readiness probe endpoint.

    Checks if the application is ready to receive traffic.

    Returns 200 OK even with non-critical errors to allow the service
    to start and handle requests. Database and AWS service failures are
    logged but don't prevent the application from being marked as ready.

    Returns:
        Simple readiness status
    """
    # Always return ready=true for ALB health checks
    # The application can handle degraded mode
    return {
        "ready": True,
        "timestamp": time.time(),
        "degraded": bool(hasattr(app.state, "startup_errors") and app.state.startup_errors),
    }


@app.get("/metrics", tags=["monitoring"], summary="Prometheus metrics endpoint")
async def metrics() -> Any:
    """
    Prometheus metrics endpoint.

    Returns:
        Prometheus-formatted metrics
    """
    from starlette.responses import Response

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# ============================================================================
# Route Registration
# ============================================================================


# Root endpoint
@app.get("/", tags=["general"])
async def root() -> dict[str, Any]:
    """
    Root endpoint with API information.

    Returns:
        API metadata and links
    """
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "environment": settings.environment,
        "status": "operational",
        "documentation": "/docs" if not settings.is_production else None,
        "health_check": settings.health_check_path,
        "metrics": "/metrics" if settings.monitoring.metrics_enabled else None,
    }


# Import and include routers
def register_routes():
    """Register all application routes."""
    try:
        # Authentication routes
        from app.routes import auth

        app.include_router(
            auth.router,
            prefix="/api/v1/auth",
            tags=["authentication"],
        )
        logger.info("✓ Authentication routes registered")
    except ImportError as e:
        logger.warning(f"Authentication routes not available: {e}")

    try:
        # Document processing routes
        from app.routes import documents

        app.include_router(
            documents.router,
            prefix="/api/v1/documents",
            tags=["documents"],
        )
        logger.info("✓ Document routes registered")
    except ImportError as e:
        logger.warning(f"Document routes not available: {e}")

    try:
        # AI agent routes
        from app.routes import agents

        app.include_router(
            agents.router,
            prefix="/api/v1/agents",
            tags=["agents"],
        )
        logger.info("✓ Agent routes registered")
    except ImportError as e:
        logger.warning(f"Agent routes not available: {e}")

    try:
        # Search routes
        from app.routes import search

        app.include_router(
            search.router,
            prefix="/api/v1/search",
            tags=["search"],
        )
        logger.info("✓ Search routes registered")
    except ImportError as e:
        logger.warning(f"Search routes not available: {e}")

    try:
        # MCP routes
        from app.routes import mcp

        app.include_router(
            mcp.router,
            prefix="/api/v1/mcp",
            tags=["mcp"],
        )
        logger.info("✓ MCP routes registered")
    except ImportError as e:
        logger.warning(f"MCP routes not available: {e}")

    try:
        # Real-time communication routes
        from app.routes import realtime

        app.include_router(
            realtime.router,
            prefix="/api/v1/realtime",
            tags=["realtime"],
        )
        logger.info("✓ Real-time routes registered")
    except ImportError as e:
        logger.warning(f"Real-time routes not available: {e}")

    try:
        # htmx API routes (HTML fragments)
        from app.routes import htmx

        app.include_router(
            htmx.router,
            tags=["htmx"],
        )
        logger.info("✓ htmx API routes registered")
    except ImportError as e:
        logger.warning(f"htmx routes not available: {e}")

    try:
        # Page routes (must be last to avoid conflicts)
        from app.routes import pages

        app.include_router(
            pages.router,
            tags=["pages"],
        )
        logger.info("✓ Page routes registered")
    except ImportError as e:
        logger.warning(f"Page routes not available: {e}")

    try:
        # Admin routes
        from app.routes import admin

        app.include_router(
            admin.router,
            prefix="/api/v1/admin",
            tags=["admin"],
        )
        logger.info("✓ Admin routes registered")
    except ImportError as e:
        logger.warning(f"Admin routes not available: {e}")


# Register routes
register_routes()


# ============================================================================
# Static Files & Templates
# ============================================================================

try:
    from pathlib import Path

    # Mount static files for frontend
    static_path = Path(__file__).parent.parent.parent / "frontend" / "static"
    if static_path.exists():
        app.mount(
            "/static",
            StaticFiles(directory=str(static_path)),
            name="static",
        )
        logger.info(f"✓ Static files mounted from {static_path}")

    # Mount templates for htmx
    templates_path = Path(__file__).parent.parent.parent / "frontend" / "templates"
    if templates_path.exists():
        from fastapi.templating import Jinja2Templates

        templates = Jinja2Templates(directory=str(templates_path))
        app.state.templates = templates
        logger.info(f"✓ Templates loaded from {templates_path}")
except Exception as e:
    logger.warning(f"Failed to mount static files or templates: {e}")


# ============================================================================
# OpenAPI Documentation Configuration
# ============================================================================


# Configure OpenAPI schema
def custom_openapi():
    """Customize OpenAPI schema with security definitions."""
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=settings.app_name,
        version="1.0.0",
        description="""
        # PM Document Intelligence API

        AI-powered document intelligence and analysis platform for project managers.

        ## Features

        - **Document Processing**: Upload and process various document formats (PDF, DOCX, etc.)
        - **AI Analysis**: Extract insights using AWS Bedrock and OpenAI
        - **Vector Search**: Semantic search across documents
        - **Real-time Updates**: WebSocket and PubNub integration
        - **Agent-based Processing**: Autonomous AI agents for document analysis

        ## Authentication

        This API uses JWT (JSON Web Tokens) for authentication. Include the token in the
        `Authorization` header as `Bearer <token>`.

        ## Rate Limiting

        - Global: 1000 requests/hour, 100 requests/minute
        - Upload: 10 requests/minute
        - Processing: 20 requests/minute
        - Queries: 100 requests/minute

        ## Support

        For issues and questions, please contact the development team.
        """,
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from /api/v1/auth/login",
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": settings.security.api_key_header,
            "description": "API key for service-to-service authentication",
        },
    }

    # Apply security globally
    openapi_schema["security"] = [
        {"BearerAuth": []},
        {"ApiKeyAuth": []},
    ]

    # Add tags descriptions
    openapi_schema["tags"] = [
        {
            "name": "authentication",
            "description": "User authentication and authorization operations",
        },
        {
            "name": "documents",
            "description": "Document upload, processing, and retrieval",
        },
        {
            "name": "agents",
            "description": "AI agent interactions and task management",
        },
        {
            "name": "search",
            "description": "Semantic and hybrid search across documents",
        },
        {
            "name": "mcp",
            "description": "Model Context Protocol - Tools, resources, and prompts for extended AI capabilities",
        },
        {
            "name": "realtime",
            "description": "Real-time communication and updates",
        },
        {
            "name": "htmx",
            "description": "htmx API routes - HTML fragments for dynamic page updates",
        },
        {
            "name": "pages",
            "description": "Page routes - HTML template rendering for main application pages",
        },
        {
            "name": "admin",
            "description": "Administrative operations (requires admin role)",
        },
        {
            "name": "monitoring",
            "description": "Health checks and metrics",
        },
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# ============================================================================
# Application Info
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting application in development mode...")

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=1 if settings.reload else settings.workers,
        log_level=settings.monitoring.log_level.lower(),
    )
