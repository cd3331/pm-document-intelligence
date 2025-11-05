# FastAPI Application Setup Guide

This guide explains how to set up and run the PM Document Intelligence FastAPI application with production-grade security, monitoring, and error handling.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Configuration](#configuration)
4. [Running the Application](#running-the-application)
5. [API Documentation](#api-documentation)
6. [Monitoring & Health Checks](#monitoring--health-checks)
7. [Security Features](#security-features)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Install Dependencies

```bash
# Install using Poetry (recommended)
cd backend
poetry install

# Or install specific groups
poetry install --with dev  # Include development dependencies
poetry install --with ml   # Include ML dependencies
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp ../.env.example ../.env

# Edit .env with your actual values
nano ../.env
```

**Required Environment Variables:**

```bash
# Application
SECRET_KEY=your-secret-key-here-min-32-chars
ENVIRONMENT=development  # development, staging, or production

# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
SUPABASE_SERVICE_KEY=your-service-key
SUPABASE_JWT_SECRET=your-jwt-secret

# OpenAI
OPENAI_API_KEY=your-openai-key

# PubNub
PUBNUB_PUBLISH_KEY=your-publish-key
PUBNUB_SUBSCRIBE_KEY=your-subscribe-key
PUBNUB_SECRET_KEY=your-secret-key

# Security
JWT_SECRET_KEY=your-jwt-secret-min-32-chars
API_KEY_SALT=your-api-key-salt-min-16-chars
```

### 3. Run the Application

```bash
# Development mode (with auto-reload)
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using the main.py directly
poetry run python app/main.py

# Production mode
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. Access the Application

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

---

## Architecture Overview

### Application Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration management
│   ├── routes/              # API route handlers
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── documents.py     # Document processing
│   │   ├── agents.py        # AI agent interactions
│   │   ├── realtime.py      # WebSocket/PubNub
│   │   └── admin.py         # Admin operations
│   ├── middleware/          # Custom middleware
│   │   └── security.py      # Security headers & tracking
│   ├── utils/               # Utility modules
│   │   ├── logger.py        # Structured logging
│   │   └── exceptions.py    # Custom exceptions
│   ├── db/                  # Database management
│   │   └── session.py       # DB session handling
│   ├── cache/               # Caching layer
│   │   └── redis.py         # Redis operations
│   └── services/            # External services
│       └── aws.py           # AWS service clients
```

### Key Components

1. **Lifespan Manager**: Handles startup/shutdown operations
   - Tests database connectivity
   - Verifies AWS service availability
   - Initializes Redis cache
   - Graceful connection cleanup

2. **Middleware Stack** (execution order):
   ```
   Request → CORS → TrustedHost → Security Headers → Request Tracking
          → Request Timing → Rate Limiting → Compression → Application
   ```

3. **Error Handling**:
   - Custom exception hierarchy
   - Structured error responses
   - Automatic error logging
   - Sentry integration

4. **Monitoring**:
   - Prometheus metrics
   - Sentry error tracking
   - Health check endpoints
   - Structured logging

---

## Configuration

### Configuration System

The application uses **Pydantic Settings** for type-safe configuration management.

**Configuration File**: `app/config.py`

```python
from app.config import settings

# Access configuration
print(settings.environment)          # Environment name
print(settings.debug)                # Debug mode
print(settings.aws.s3_bucket_name)   # AWS S3 bucket
print(settings.bedrock.model_id)     # Bedrock model ID
```

### Configuration Sections

| Section | Purpose |
|---------|---------|
| `AWSConfig` | AWS services (S3, Bedrock, Textract, Comprehend) |
| `BedrockConfig` | AWS Bedrock model settings |
| `OpenAIConfig` | OpenAI API configuration |
| `SupabaseConfig` | Database and authentication |
| `PubNubConfig` | Real-time messaging |
| `SecurityConfig` | JWT, API keys, password hashing |
| `RateLimitConfig` | API rate limiting |
| `MonitoringConfig` | Sentry, metrics, logging |
| `FeatureFlags` | Feature toggles |
| `CacheConfig` | Redis caching settings |

### Environment-Specific Behavior

**Development**:
- Debug mode enabled
- Detailed error messages
- API documentation available
- Permissive CORS
- Colorful console logs

**Production**:
- Debug mode disabled
- Generic error messages
- API docs hidden
- Strict security headers
- JSON-formatted logs
- HSTS enabled

---

## Running the Application

### Development Mode

```bash
# With auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# With custom log level
uvicorn app.main:app --reload --log-level debug

# Using the main.py script
python app/main.py
```

### Production Mode

```bash
# With multiple workers
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info \
  --access-log \
  --proxy-headers

# With Gunicorn (recommended for production)
gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Docker

```bash
# Build image
docker build -t pm-document-intelligence .

# Run container
docker run -p 8000:8000 --env-file .env pm-document-intelligence

# With Docker Compose
docker-compose up -d
```

---

## API Documentation

### Interactive Documentation

Access the interactive API documentation at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Authentication

The API uses **JWT Bearer tokens** for authentication.

#### Get Access Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

#### Use Access Token

```bash
curl http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

### Rate Limits

| Endpoint | Limit |
|----------|-------|
| Global | 1000/hour, 100/minute |
| Upload | 10/minute |
| Process | 20/minute |
| Query | 100/minute |

Rate limit headers:
- `X-RateLimit-Limit`: Request limit
- `X-RateLimit-Remaining`: Remaining requests
- `Retry-After`: Seconds until retry (when limited)

---

## Monitoring & Health Checks

### Health Check Endpoint

**GET /health**

Returns detailed health status of all services:

```json
{
  "status": "healthy",
  "timestamp": 1234567890.123,
  "environment": "production",
  "version": "1.0.0",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    },
    "aws": {
      "status": "healthy",
      "services": {
        "bedrock": true,
        "s3": true,
        "textract": true,
        "comprehend": true,
        "all_available": true
      }
    },
    "redis": {
      "status": "healthy",
      "message": "Redis connection successful"
    }
  }
}
```

### Readiness Check

**GET /ready**

Kubernetes readiness probe:

```json
{
  "ready": true,
  "timestamp": 1234567890.123
}
```

### Prometheus Metrics

**GET /metrics**

Prometheus-formatted metrics:

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/health",status_code="200"} 42

# HELP http_request_duration_seconds HTTP request duration
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="GET",endpoint="/health",le="0.1"} 40
```

**Available Metrics**:
- `http_requests_total` - Total HTTP requests by method, endpoint, status
- `http_request_duration_seconds` - Request duration histogram
- `http_requests_in_progress` - Currently processing requests
- `document_processing_total` - Total documents processed
- `ai_service_requests_total` - AI service API calls
- `errors_total` - Total errors by type

### Logging

Logs are structured JSON (production) or colored text (development).

**Log Levels**:
- `DEBUG`: Detailed debugging information
- `INFO`: General informational messages
- `WARNING`: Warning messages
- `ERROR`: Error messages with stack traces
- `CRITICAL`: Critical errors

**Log Context**:
- `request_id`: Unique request identifier
- `user_id`: Authenticated user ID (if applicable)
- `timestamp`: ISO 8601 timestamp
- `level`: Log level
- `module`: Source module
- `function`: Source function

**Example Log Entry**:
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "app.routes.documents",
  "module": "documents",
  "function": "upload_document",
  "request_id": "a1b2c3d4-e5f6-7890",
  "user_id": "user_123",
  "message": "Document uploaded successfully",
  "document_id": "doc_456",
  "file_size": 1024000
}
```

---

## Security Features

### Security Headers

All responses include security headers:

| Header | Purpose |
|--------|---------|
| `Content-Security-Policy` | Prevent XSS attacks |
| `Strict-Transport-Security` | Enforce HTTPS (production) |
| `X-Frame-Options` | Prevent clickjacking |
| `X-Content-Type-Options` | Prevent MIME sniffing |
| `X-XSS-Protection` | Enable browser XSS filter |
| `Referrer-Policy` | Control referrer information |
| `Permissions-Policy` | Control browser features |

### Request Tracking

Every request includes:
- `X-Request-ID`: Unique request identifier
- `X-Response-Time`: Response time in milliseconds

### Rate Limiting

Protection against abuse:
- Per-user/IP rate limiting
- Redis-backed distributed limiting
- Automatic retry-after headers

### Input Validation

- Pydantic models for request validation
- SQL injection prevention
- XSS protection
- Path traversal detection

### Authentication

- JWT-based authentication
- Secure password hashing (bcrypt)
- Token refresh mechanism
- API key support

---

## Troubleshooting

### Common Issues

#### 1. Application Won't Start

**Error**: `Failed to initialize Sentry`

**Solution**: Check `SENTRY_DSN` in `.env` or disable Sentry:
```bash
SENTRY_ENABLED=false
```

---

#### 2. Database Connection Failed

**Error**: `Database connection failed`

**Solution**:
- Verify `DATABASE_URL` is correct
- Check database is running
- Test connection:
  ```bash
  psql $DATABASE_URL
  ```

---

#### 3. Redis Connection Failed

**Error**: `Redis connection failed`

**Solution**:
- Check Redis is running: `redis-cli ping`
- Verify `REDIS_URL` in `.env`
- Or disable caching:
  ```bash
  CACHE_ENABLED=false
  ```

---

#### 4. AWS Services Unavailable

**Error**: `AWS services unavailable`

**Solution**:
- Verify AWS credentials are set
- Check IAM permissions
- Test with AWS CLI:
  ```bash
  aws s3 ls
  aws bedrock list-foundation-models
  ```

---

### Debug Mode

Enable debug mode for detailed error messages:

```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

### View Logs

**Console Logs**:
```bash
# Real-time logs
tail -f logs/app.log

# JSON formatted
cat logs/app.log | jq
```

**Specific Request**:
```bash
# Find by request ID
grep "a1b2c3d4-e5f6-7890" logs/app.log | jq
```

---

## Next Steps

1. **Implement Authentication**: Add authentication logic to `routes/auth.py`
2. **Add Document Processing**: Implement document upload in `routes/documents.py`
3. **Configure AWS Services**: Set up Bedrock, Textract, Comprehend
4. **Set Up Database**: Create database schema and migrations
5. **Add Tests**: Write unit and integration tests
6. **Deploy**: Deploy to production environment

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/usage/pydantic_settings/)
- [AWS Bedrock](https://docs.aws.amazon.com/bedrock/)
- [Supabase](https://supabase.com/docs)
- [Prometheus](https://prometheus.io/docs/)
- [Sentry](https://docs.sentry.io/)

---

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/pm-document-intelligence/issues
- Documentation: `/docs`
- Health Check: `/health`
