# PM Document Intelligence - Technical Architecture

**Last Updated**: January 10, 2025
**Status**: Active Production System
**Database**: PostgreSQL (AWS RDS) - Migrated from Supabase

---

## Executive Summary

PM Document Intelligence is an AI-powered document analysis platform built for project managers. The system uses AWS infrastructure with FastAPI backend, PostgreSQL database, and multiple AI services for document processing.

**Key Migration**: The system was originally built with Supabase but has been migrated to AWS RDS PostgreSQL with direct SQLAlchemy connections.

---

## Tech Stack

### **Frontend**
- **Framework**: Vanilla JavaScript with Alpine.js
- **Templating**: Jinja2 (server-side rendering)
- **Dynamic Updates**: HTMX for server-driven UI
- **Styling**: TailwindCSS
- **Real-time**: PubNub (optional)
- **Hosting**: AWS S3 + CloudFront (app.joyofpm.com)

### **Backend**
- **Framework**: FastAPI 0.109.0 (Python 3.11+)
- **Server**: Uvicorn with async workers
- **API**: RESTful JSON + HTMX HTML fragments
- **Authentication**: JWT (JSON Web Tokens)
- **Validation**: Pydantic v2
- **Hosting**: AWS ECS Fargate (api.joyofpm.com)

### **Database Layer**
- **Database**: PostgreSQL 15.14 (AWS RDS)
- **ORM**: SQLAlchemy 2.0.25 (Core + async)
- **Driver**: asyncpg (async) + psycopg2-binary (sync)
- **Migrations**: Alembic 1.13.1
- **Vector Search**: pgvector 0.2.4
- **Connection Pooling**: SQLAlchemy QueuePool (20 connections, 10 overflow)

### **Caching**
- **Cache**: Redis 5.0.1 (AWS ElastiCache)
- **Driver**: hiredis 2.3.2 (high-performance)
- **Use Cases**: Rate limiting, session management, vector embeddings

### **AWS Services**
- **Compute**: ECS Fargate (1 vCPU, 2GB RAM)
- **Database**: RDS PostgreSQL (db.t3.medium, Single-AZ)
- **Cache**: ElastiCache Redis (cache.t3.small)
- **Storage**: S3 (document storage)
- **CDN**: CloudFront (frontend delivery)
- **Load Balancer**: Application Load Balancer (ALB)
- **AI Services**:
  - AWS Bedrock (Claude 3.5 Sonnet) - Text generation
  - AWS Textract - Document OCR
  - AWS Comprehend - Entity extraction, key phrases
- **Networking**: VPC with 2 AZs, NAT Gateways
- **Security**: ACM (SSL/TLS), WAF, Security Groups

### **AI & Embeddings**
- **Primary AI**: AWS Bedrock (Claude 3.5 Sonnet v2)
- **Fallback AI**: OpenAI GPT-4 (optional)
- **Embeddings**: OpenAI text-embedding-ada-002
- **Vector Search**: pgvector in PostgreSQL
- **Protocols**: MCP (Model Context Protocol) via fastmcp

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                            │
│  ┌──────────────┐           ┌──────────────┐                   │
│  │   Browser    │◄─────────►│   PubNub     │ (Real-time)       │
│  │  (Alpine.js) │           │   Client     │                   │
│  └──────┬───────┘           └──────────────┘                   │
│         │                                                        │
└─────────┼────────────────────────────────────────────────────────┘
          │ HTTPS
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AWS INFRASTRUCTURE                         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    CloudFront CDN                        │  │
│  │  ┌────────────────┐         ┌────────────────┐          │  │
│  │  │  Frontend      │         │   Backend      │          │  │
│  │  │  (S3 Static)   │         │   (ALB)        │          │  │
│  │  │app.joyofpm.com │         │api.joyofpm.com │          │  │
│  │  └────────────────┘         └───────┬────────┘          │  │
│  └────────────────────────────────────────┼──────────────────┘  │
│                                            │                     │
│  ┌────────────────────────────────────────▼──────────────────┐  │
│  │              ECS Fargate Cluster                          │  │
│  │  ┌──────────────────────────────────────────────┐         │  │
│  │  │  FastAPI Application (1 task)                │         │  │
│  │  │  ┌────────────┐  ┌────────────┐             │         │  │
│  │  │  │  API       │  │   HTMX     │             │         │  │
│  │  │  │  Routes    │  │   Routes   │             │         │  │
│  │  │  └─────┬──────┘  └─────┬──────┘             │         │  │
│  │  │        │                │                    │         │  │
│  │  │  ┌─────▼────────────────▼──────┐            │         │  │
│  │  │  │   Business Logic Layer      │            │         │  │
│  │  │  │  - Document Processor       │            │         │  │
│  │  │  │  - AWS Service Manager      │            │         │  │
│  │  │  │  - Authentication           │            │         │  │
│  │  │  │  - Vector Search            │            │         │  │
│  │  │  └─────┬───────────────────────┘            │         │  │
│  │  │        │                                     │         │  │
│  │  │  ┌─────▼───────────────────────┐            │         │  │
│  │  │  │   Database Abstraction      │            │         │  │
│  │  │  │  - SQLAlchemy Engine        │            │         │  │
│  │  │  │  - Helper Functions         │            │         │  │
│  │  │  │    execute_select()         │            │         │  │
│  │  │  │    execute_insert()         │            │         │  │
│  │  │  │    execute_update()         │            │         │  │
│  │  │  │    execute_delete()         │            │         │  │
│  │  │  └─────┬───────────────────────┘            │         │  │
│  │  └────────┼───────────────────────────────────┘         │  │
│  └───────────┼─────────────────────────────────────────────┘  │
│              │                                                  │
│     ┌────────┼────────┐            ┌──────────────┐           │
│     │        ▼        │            │              │           │
│  ┌──┴────────────┐    │         ┌──┴──────────┐   │           │
│  │  PostgreSQL   │    └────────►│   Redis     │   │           │
│  │     RDS       │               │ElastiCache  │   │           │
│  │  (Primary DB) │               │  (Cache)    │   │           │
│  └───────────────┘               └─────────────┘   │           │
│                                                     │           │
│  ┌────────────────────────────────────────────────┘           │
│  │  AWS AI Services                                            │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │  │ Bedrock  │  │ Textract │  │Comprehend│                 │
│  │  │ (Claude) │  │  (OCR)   │  │(Entities)│                 │
│  │  └──────────┘  └──────────┘  └──────────┘                 │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  S3 Bucket (Document Storage)                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Architecture

### **Current: PostgreSQL (AWS RDS)**

**Connection String Format**:
```
postgresql+asyncpg://username:password@rds-host:5432/pm_document_intelligence
```

**Connection Management**:
- **Engine**: SQLAlchemy AsyncEngine with asyncpg driver
- **Pool Size**: 20 connections (configurable)
- **Max Overflow**: 10 connections
- **Pool Recycle**: 3600 seconds (1 hour)
- **Pre-ping**: Enabled (health checks before use)
- **Session**: Async sessions with autocommit=False

**Migration from Supabase**:
The system originally used Supabase (managed PostgreSQL with REST API) but was migrated to direct PostgreSQL connections because:
1. Supabase connection issues
2. Need for direct SQL control
3. Better integration with AWS infrastructure
4. Lower latency

### **Database Query Patterns**

The codebase uses **SQLAlchemy Core** (not ORM) with helper functions:

**Helper Functions** (`app/database.py`):
```python
# SELECT queries
documents = await execute_select(
    "documents",
    match={"user_id": user_id, "status": "uploaded"},
    order="created_at.desc",
    limit=10
)

# INSERT queries
document = await execute_insert(
    "documents",
    {"id": doc_id, "filename": "test.pdf", "user_id": user_id}
)

# UPDATE queries
await execute_update(
    "documents",
    data={"status": "processed"},
    match={"id": doc_id}
)

# DELETE queries
await execute_delete(
    "documents",
    match={"id": doc_id}
)
```

**Under the Hood**:
- Reflects database schema at startup
- Uses SQLAlchemy Table objects
- Executes parameterized queries (SQL injection safe)
- Automatic transaction management
- Connection pooling

### **Why Not ORM Models?**

The codebase has **Pydantic models** (for API validation) but **NOT SQLAlchemy ORM models**:

```python
# ❌ This does NOT exist:
from app.models import Document  # This is Pydantic, not SQLAlchemy ORM
db.query(Document).filter(...)   # ❌ Won't work

# ✅ This is the correct approach:
from app.database import execute_select
documents = await execute_select("documents", match={...})  # ✅ Works
```

**Decision Rationale**:
- Flexibility: Direct SQL control when needed
- Simplicity: Less boilerplate than ORM
- Performance: No lazy loading overhead
- Async-first: Better async support with Core

---

## Application Workflow

### **1. Document Upload Flow**

```
User → Upload File → Frontend (Alpine.js)
         ↓
    POST /api/v1/documents/upload (FastAPI)
         ↓
    Validate file type & size
         ↓
    Upload to S3 (boto3)
         ↓
    Insert record: execute_insert("documents", {...})
         ↓
    Return document metadata
         ↓
    Frontend shows success
```

### **2. Document Processing Flow**

```
User → Click "Process Document" → Frontend
         ↓
    POST /api/v1/documents/{id}/process
         ↓
    Update status: execute_update("documents", status="processing")
         ↓
    Download from S3 → Temp file
         ↓
    ┌─ AWS Textract: Extract text (OCR)
    ├─ AWS Comprehend: Extract entities, key phrases
    └─ AWS Bedrock: Generate summary, action items, risks
         ↓
    Update document: execute_update("documents", {
        status: "processed",
        extracted_text: "...",
        summary: "...",
        action_items: [...],
        entities: [...],
        key_phrases: [...]
    })
         ↓
    Delete temp file
         ↓
    Return success
         ↓
    Frontend reloads document (shows analysis)
```

### **3. HTMX Dynamic Updates Flow**

```
User → Click "Analysis" Tab → HTMX Request
         ↓
    GET /api/document/{id}/analysis (HTMX route)
         ↓
    Query document: execute_select("documents", match={id})
         ↓
    Render HTML fragment (Jinja2-like string)
         ↓
    Return HTML (not JSON)
         ↓
    HTMX swaps HTML into #analysis-content div
```

### **4. Authentication Flow**

```
User → Login Form → POST /api/v1/auth/login
         ↓
    Query user: execute_select("users", match={email})
         ↓
    Verify password (bcrypt)
         ↓
    Generate JWT token (access + refresh)
         ↓
    Return {access_token, refresh_token}
         ↓
    Frontend stores in localStorage
         ↓
    Subsequent requests: Authorization: Bearer {token}
         ↓
    Middleware validates JWT → get_current_user()
```

---

## Critical Components

### **1. FastAPI Application** (`app/main.py`)

**Initialization Order**:
1. Load configuration from environment variables
2. Initialize Sentry (error tracking)
3. Test database connection
4. Test AWS services (Bedrock, Textract, S3, Comprehend)
5. Initialize Redis cache
6. Initialize AI agents
7. Initialize MCP server
8. Initialize PubNub (optional)
9. Register routes
10. Mount static files

**Middleware Stack** (execution order):
1. CORS (allow origins)
2. Trusted Host (validate hostname)
3. Security Headers (CSP, HSTS, X-Frame-Options)
4. Request Tracking (add request_id)
5. Request Timing (Prometheus metrics)
6. Rate Limiting (Redis-backed)
7. GZIP Compression

**Route Prefixes**:
- `/` - Root + health checks
- `/api/v1/auth` - Authentication
- `/api/v1/documents` - Document CRUD + processing
- `/api/v1/agents` - AI agent interactions
- `/api/v1/search` - Search endpoints
- `/api/v1/mcp` - Model Context Protocol
- `/api/v1/realtime` - Real-time communication
- `/api/*` - HTMX HTML fragment routes (no /v1 prefix!)
- `/*` - Page routes (Jinja2 templates)

### **2. Database Layer** (`app/database.py`, `app/db/session.py`)

**Key Functions**:
- `get_engine()` - Returns singleton AsyncEngine
- `get_session_factory()` - Returns session factory
- `get_db()` - Context manager for database sessions
- `execute_select()` - SELECT queries
- `execute_insert()` - INSERT queries
- `execute_update()` - UPDATE queries
- `execute_delete()` - DELETE queries
- `execute_count()` - COUNT queries
- `test_database_connection()` - Health check

**Error Handling**:
- Custom exceptions: `DatabaseError`, `RecordNotFoundError`
- Automatic rollback on errors
- Retry logic with tenacity
- Structured logging

### **3. AWS Service Manager** (`app/services/aws_service.py`)

**Services**:
- `S3Service` - Upload, download, delete documents
- `BedrockService` - Claude AI for text generation
- `TextractService` - OCR for document text extraction
- `ComprehendService` - Entity extraction, key phrases

**Key Methods**:
```python
# S3
await s3_service.upload_document(file_content, filename, user_id)
file_content, metadata = await s3_service.download_document(s3_key)
await s3_service.delete_document(s3_key)

# Bedrock
response = await bedrock_service.generate(
    prompt="Summarize this document",
    context=extracted_text
)

# Textract
text = await textract_service.extract_text(file_path)

# Comprehend
entities = await comprehend_service.detect_entities(text)
key_phrases = await comprehend_service.detect_key_phrases(text)
```

### **4. Document Processor** (`app/services/document_processor.py`)

**Orchestrates**:
1. Textract extraction
2. Comprehend analysis
3. Bedrock summarization
4. Result aggregation

**Returns**:
```python
{
    "extracted_text": "...",
    "summary": "...",
    "action_items": [...],
    "entities": [...],
    "key_phrases": [...],
    "risks": [...],
    "metadata": {...}
}
```

---

## Configuration

### **Environment Variables**

**Required**:
- `DATABASE_URL` - PostgreSQL connection string
- `S3_BUCKET_NAME` - S3 bucket for documents
- `JWT_SECRET_KEY` - JWT signing key (32+ chars)
- `API_KEY_SALT` - API key hashing salt (16+ chars)

**Optional**:
- `AWS_ACCESS_KEY_ID` - AWS credentials (or use IAM roles)
- `AWS_SECRET_ACCESS_KEY`
- `REDIS_URL` - Redis connection (default: ElastiCache endpoint)
- `SENTRY_DSN` - Error tracking
- `PUBNUB_PUBLISH_KEY`, `PUBNUB_SUBSCRIBE_KEY` - Real-time updates
- `OPENAI_API_KEY` - Fallback AI

**Feature Flags**:
- `RATE_LIMIT_ENABLED=true` - Enable rate limiting
- `PUBNUB_ENABLED=false` - Enable real-time messaging
- `TEXTRACT_ENABLED=true` - Enable OCR
- `DEBUG=false` - Debug mode

### **Configuration Classes** (`app/config.py`)

- `AWSConfig` - AWS credentials and service config
- `BedrockConfig` - Claude AI parameters
- `TextractConfig` - OCR settings
- `ComprehendConfig` - NLP settings
- `OpenAIConfig` - OpenAI fallback
- `DatabaseConfig` - PostgreSQL connection pooling
- `RedisConfig` - Cache configuration
- `SecurityConfig` - JWT, bcrypt, API keys
- `RateLimitConfig` - Rate limiting strategy
- `MonitoringConfig` - Sentry, logging, metrics
- `PubNubConfig` - Real-time messaging

---

## Deployment

### **Infrastructure as Code** (Terraform)

**Files**:
- `main.tf` - VPC, ECS, RDS, ElastiCache, ALB
- `app.tf` - Frontend S3 + CloudFront
- `website.tf` - Static website
- `variables.tf` - Input variables
- `outputs.tf` - Exported values
- `terraform.tfvars` - Environment-specific values (gitignored)

**Deployment Process**:
1. Code push to `master` branch
2. GitHub Actions triggers
3. Build Docker image
4. Push to ECR (Elastic Container Registry)
5. Update ECS task definition
6. ECS rolls out new tasks (blue/green)
7. ALB health checks
8. Old tasks terminated

**GitHub Actions** (`.github/workflows/deploy.yml`):
- Build backend Docker image
- Run tests
- Push to ECR
- Deploy to ECS
- Notify on failure

### **Docker**

**Dockerfile**:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**ECS Configuration**:
- **CPU**: 1 vCPU (1024 CPU units)
- **Memory**: 2 GB (2048 MB)
- **Tasks**: 1 (minimum), 4 (maximum)
- **Auto-scaling**: CPU > 70% → scale up
- **Health Check**: GET /ready every 30s

---

## Security

### **Authentication**
- JWT tokens (access: 30 min, refresh: 7 days)
- Bcrypt password hashing (12 rounds)
- Token expiry validation
- Refresh token rotation

### **Authorization**
- User-based document ownership
- JWT claims validation
- Role-based access control (planned)

### **Network Security**
- VPC with private subnets
- Security groups (least privilege)
- HTTPS only (TLS 1.2+)
- WAF (Web Application Firewall)

### **Application Security**
- Security headers (CSP, HSTS, X-Frame-Options)
- Input validation (Pydantic)
- SQL injection prevention (parameterized queries)
- Rate limiting (Redis)
- Request ID tracking
- Audit logging

### **Data Security**
- Encryption at rest (RDS, S3)
- Encryption in transit (TLS)
- S3 presigned URLs (temporary access)
- Database connection pooling (prevents exhaustion)

---

## Monitoring & Observability

### **Metrics** (Prometheus)
- HTTP request count, duration, in-progress
- Document processing count, duration
- AI service requests, tokens consumed
- Error counts by type

### **Logging** (CloudWatch Logs)
- Structured JSON logs
- Request/response logging
- Error logging with stack traces
- Audit logging (user actions)

### **Health Checks**
- `/health` - Comprehensive health (DB, Redis, AWS)
- `/ready` - Kubernetes readiness probe
- `/metrics` - Prometheus metrics

### **Error Tracking** (Sentry)
- Automatic error capture
- Stack traces
- User context
- Environment info

---

## Performance Optimizations

### **Database**
- Connection pooling (20 connections)
- Async queries (asyncpg)
- Indexed queries (created_at, user_id)
- Vector search (pgvector)

### **Caching**
- Redis for rate limiting
- Vector embedding cache
- Session caching

### **API**
- GZIP compression
- Async endpoints
- Batch processing
- Pagination

### **Infrastructure**
- ALB connection draining
- ECS auto-scaling
- CloudFront CDN (frontend)
- S3 presigned URLs (direct uploads)

---

## Cost Optimization

**Current Configuration** (~$246/month):
- ECS: 1 task, 1 vCPU, 2GB RAM (~$37)
- RDS: db.t3.medium, Single-AZ (~$60)
- ElastiCache: cache.t3.small (~$25)
- ALB: ~$24
- NAT Gateways (2): ~$80
- S3 + CloudWatch: ~$20

**Trade-offs**:
- Single ECS task (no redundancy)
- Single-AZ RDS (no failover)
- Reduced auto-scaling (max 4 tasks)
- No Container Insights
- No Performance Insights

**Suitable For**: <5,000 documents/month

---

## Known Issues

### **Critical**
1. ~~Document processing returns 501~~ (FIXED in this commit)
2. ~~Document deletion returns 501~~ (FIXED in this commit)
3. ~~HTMX routes return 404~~ (FIXED in this commit)

### **Medium**
1. Vector search not fully implemented
2. Action items table doesn't exist
3. Q&A endpoint placeholder only

### **Low**
1. PubNub integration optional/disabled
2. OpenAI fallback not fully tested
3. MCP implementation incomplete

---

## Development

### **Local Setup**

```bash
# 1. Clone repo
git clone https://github.com/cd3331/pm-document-intelligence.git
cd pm-document-intelligence

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# 3. Install dependencies
cd backend
pip install -r requirements.txt

# 4. Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/pm_doc_intel"
export S3_BUCKET_NAME="my-test-bucket"
export JWT_SECRET_KEY="your-secret-key-here-min-32-chars"
export API_KEY_SALT="your-api-salt-16chars"

# 5. Run migrations
alembic upgrade head

# 6. Start server
uvicorn app.main:app --reload --port 8000
```

### **Testing**

```bash
# Run tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test
pytest tests/test_documents.py -v
```

---

## Future Enhancements

1. **SQLAlchemy ORM Models** - For complex relationships
2. **Vector Search** - Semantic document search
3. **Action Items Table** - Dedicated action tracking
4. **Multi-tenancy** - Organization support
5. **Real-time Processing** - WebSocket status updates
6. **Batch Processing** - Multiple document uploads
7. **Advanced Analytics** - Document insights dashboard
8. **Export Features** - PDF, Excel, JSON exports

---

## References

- **Codebase**: `/home/cd3331/pm-document-intelligence/`
- **Backend**: `backend/app/`
- **Infrastructure**: `infrastructure/terraform/`
- **Documentation**: `docs/`
- **API Docs**: https://api.joyofpm.com/docs (dev only)
- **Frontend**: https://app.joyofpm.com
- **Backend**: https://api.joyofpm.com

---

**Document Maintained By**: Claude Code
**Contact**: cd3331github@gmail.com
