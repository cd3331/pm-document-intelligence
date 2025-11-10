# Quick Start Guide - PM Document Intelligence

**Get up and running in 10 minutes**

Last Updated: January 10, 2025

---

## 🚀 Production System

**Live Application**: https://app.joyofpm.com
**API Endpoint**: https://api.joyofpm.com

### Current Status
- ✅ **Fully Operational** (as of Jan 10, 2025)
- ✅ All critical bugs fixed
- ✅ Document processing working
- ✅ HTMX dynamic updates working
- ⚡ 1-2ms API response times
- 💰 $246/month infrastructure cost

---

## 📋 What This Project Does

PM Document Intelligence is an AI-powered platform that:

1. **Uploads** project management documents (PDF, DOCX, TXT, images)
2. **Processes** them with AWS AI services:
   - **AWS Textract**: Extracts text (OCR)
   - **AWS Comprehend**: Identifies entities and key phrases
   - **AWS Bedrock (Claude)**: Generates summaries, action items, and risk assessments
3. **Analyzes** documents for insights
4. **Searches** across all your documents with semantic search
5. **Manages** everything through a modern web interface

---

## 🛠️ Tech Stack Summary

### **Frontend**
- Vanilla JavaScript + Alpine.js
- HTMX for dynamic updates
- Tailwind CSS
- Jinja2 templates

### **Backend**
- Python 3.11+ with FastAPI
- SQLAlchemy (Core, not ORM)
- PostgreSQL 15.14 with pgvector
- Redis for caching

### **Infrastructure (AWS)**
- **Compute**: ECS Fargate (1 vCPU, 2GB RAM)
- **Database**: RDS PostgreSQL (db.t3.medium)
- **Cache**: ElastiCache Redis
- **Storage**: S3
- **AI**: Bedrock (Claude), Textract, Comprehend
- **Network**: ALB, CloudFront, WAF

**Full tech stack**: See [TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md)

---

## 🏃 Local Development Setup

### Prerequisites

1. **Python 3.11+**
   ```bash
   python --version  # Should be 3.11 or higher
   ```

2. **AWS Account** with access to:
   - RDS PostgreSQL
   - S3
   - Bedrock (Claude 3.5 Sonnet)
   - Textract
   - Comprehend

3. **Required Environment Variables**:
   - `DATABASE_URL` - PostgreSQL connection string
   - `S3_BUCKET_NAME` - S3 bucket name
   - `JWT_SECRET_KEY` - 32+ character secret
   - `API_KEY_SALT` - 16+ character salt

### Installation Steps

```bash
# 1. Clone the repository
git clone https://github.com/cd3331/pm-document-intelligence.git
cd pm-document-intelligence

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
cd backend
pip install -r requirements.txt

# 4. Create .env file
cp .env.example .env
# Edit .env with your configuration

# 5. Set required environment variables
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/pm_doc_intel"
export S3_BUCKET_NAME="your-bucket-name"
export JWT_SECRET_KEY="your-super-secret-key-min-32-chars"
export API_KEY_SALT="your-salt-16chars"

# 6. Run database migrations
alembic upgrade head

# 7. Start the server
uvicorn app.main:app --reload --port 8000

# 8. Access the application
open http://localhost:8000
```

### Verify Installation

```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "database": "healthy - connection successful",
  "redis": "healthy - connection successful",
  "aws": {
    "bedrock": true,
    "s3": true,
    "textract": true,
    "comprehend": true,
    "all_available": true
  }
}
```

---

## 📝 Environment Variables

### Required

```bash
# Database
DATABASE_URL="postgresql+asyncpg://user:password@host:5432/dbname"

# AWS S3
S3_BUCKET_NAME="your-document-bucket"

# Security
JWT_SECRET_KEY="your-secret-key-at-least-32-characters-long"
API_KEY_SALT="your-salt-16chars"

# AWS Credentials (or use IAM roles)
AWS_ACCESS_KEY_ID="your-access-key"
AWS_SECRET_ACCESS_KEY="your-secret-key"
AWS_REGION="us-east-1"
```

### Optional

```bash
# Redis Cache
REDIS_URL="redis://localhost:6379/0"

# Monitoring
SENTRY_DSN="your-sentry-dsn"
SENTRY_ENABLED="false"

# Feature Flags
RATE_LIMIT_ENABLED="true"
PUBNUB_ENABLED="false"
TEXTRACT_ENABLED="true"

# AI Services
OPENAI_API_KEY="your-openai-key"  # Fallback AI
BEDROCK_MODEL_ID="anthropic.claude-3-5-sonnet-20241022-v2:0"
```

---

## 🧪 Testing the Application

### 1. Register a User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "full_name": "Test User"
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!"
  }'

# Save the access_token from response
export TOKEN="your-access-token-here"
```

### 3. Upload a Document

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/document.pdf"

# Save the document ID from response
export DOC_ID="document-id-here"
```

### 4. Process the Document

```bash
curl -X POST http://localhost:8000/api/v1/documents/$DOC_ID/process \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Get Document Details

```bash
curl http://localhost:8000/api/v1/documents/$DOC_ID \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🎯 Key API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get JWT token
- `GET /api/v1/auth/me` - Get current user info

### Documents
- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents` - List user's documents
- `GET /api/v1/documents/{id}` - Get document details
- `POST /api/v1/documents/{id}/process` - Process document with AI
- `DELETE /api/v1/documents/{id}` - Delete document
- `POST /api/v1/documents/{id}/question` - Ask questions about document

### HTMX (HTML Fragments)
- `GET /api/stats` - Dashboard statistics
- `GET /api/documents/list` - Document list HTML
- `GET /api/document/{id}/analysis` - Analysis tab HTML
- `GET /api/document/{id}/actions` - Action items tab HTML

### System
- `GET /` - Root endpoint
- `GET /health` - Comprehensive health check
- `GET /ready` - Readiness probe
- `GET /metrics` - Prometheus metrics

**Full API docs**: See [docs/API.md](docs/API.md)

---

## 🔍 Project Structure

```
pm-document-intelligence/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry
│   │   ├── config.py            # Configuration management
│   │   ├── database.py          # Database helper functions
│   │   ├── routes/              # API endpoints
│   │   │   ├── auth.py          # Authentication routes
│   │   │   ├── documents.py     # Document CRUD + processing
│   │   │   ├── htmx.py          # HTMX HTML fragment routes
│   │   │   └── ...
│   │   ├── services/            # Business logic
│   │   │   ├── aws_service.py   # AWS SDK wrapper
│   │   │   ├── document_processor.py  # AI processing orchestration
│   │   │   └── ...
│   │   ├── models/              # Pydantic models (NOT ORM)
│   │   ├── db/                  # Database session management
│   │   └── utils/               # Utilities (logging, auth, etc.)
│   ├── frontend/                # Frontend templates & static files
│   │   ├── templates/           # Jinja2 HTML templates
│   │   └── static/              # CSS, JS, images
│   ├── requirements.txt         # Python dependencies
│   └── Dockerfile               # Container definition
├── infrastructure/
│   └── terraform/               # Infrastructure as Code
│       ├── main.tf              # ECS, RDS, ElastiCache, etc.
│       ├── terraform.tfvars     # Configuration (gitignored)
│       └── ...
├── docs/                        # Documentation
├── TECHNICAL_ARCHITECTURE.md    # Complete tech stack guide
├── FUNCTIONALITY_TEST_REPORT.md # Production test results
├── README.md                    # Project overview
└── QUICKSTART.md               # This file
```

---

## 🐛 Common Issues & Solutions

### Issue: Database connection fails

**Solution**: Check your `DATABASE_URL` format
```bash
# Correct format for async:
postgresql+asyncpg://user:password@host:5432/database

# NOT:
postgresql://user:password@host:5432/database  # Missing +asyncpg
```

### Issue: AWS services not available

**Solution**:
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify Bedrock access: `aws bedrock list-foundation-models --region us-east-1`
3. Check IAM permissions for Bedrock, Textract, Comprehend, S3

### Issue: Import errors or module not found

**Solution**:
```bash
# Make sure you're in backend/ directory and venv is activated
cd backend
source ../venv/bin/activate
pip install -r requirements.txt
```

### Issue: HTMX routes return 404

**Solution**: This was fixed in v1.1.0. Make sure you're on the latest version:
```bash
git pull origin master
```

### Issue: Document processing returns 501

**Solution**: This was fixed in v1.1.0. Update to latest version.

---

## 📚 Additional Resources

### Documentation
- **[TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md)** - Complete technical architecture
- **[FUNCTIONALITY_TEST_REPORT.md](FUNCTIONALITY_TEST_REPORT.md)** - Production testing results
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design details
- **[docs/API.md](docs/API.md)** - Complete API reference
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment guide
- **[docs/SECURITY.md](docs/SECURITY.md)** - Security architecture
- **[docs/CHANGELOG.md](docs/CHANGELOG.md)** - Version history

### Key Reports
- **[infrastructure/COST_OPTIMIZATION_2025-01-10.md](infrastructure/COST_OPTIMIZATION_2025-01-10.md)** - Cost optimization details
- **[CODE_REVIEW_RDS_MIGRATION.md](CODE_REVIEW_RDS_MIGRATION.md)** - Database migration notes
- **[MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md)** - Migration summary

### External Links
- **Live Application**: https://app.joyofpm.com
- **API Endpoint**: https://api.joyofpm.com
- **GitHub Repo**: https://github.com/cd3331/pm-document-intelligence
- **AWS Bedrock Docs**: https://docs.aws.amazon.com/bedrock/
- **FastAPI Docs**: https://fastapi.tiangolo.com/

---

## 💡 Tips for Development

### 1. Use the helper functions, not ORM
```python
# ✅ Correct way (using helpers)
from app.database import execute_select, execute_insert

documents = await execute_select("documents", match={"user_id": user_id})
doc = await execute_insert("documents", {"filename": "test.pdf"})

# ❌ Wrong way (trying to use ORM models that don't exist)
from app.models import Document  # This is Pydantic, not SQLAlchemy ORM!
db.query(Document).filter(...)  # Won't work
```

### 2. Always use async/await
```python
# ✅ Correct
async def get_user(user_id: str):
    users = await execute_select("users", match={"id": user_id})
    return users[0] if users else None

# ❌ Wrong
def get_user(user_id: str):  # Missing async
    users = execute_select(...)  # Missing await
```

### 3. Check logs for debugging
```bash
# Local development
tail -f logs/app.log

# Production
aws logs tail /ecs/pm-doc-intel/production --follow
```

### 4. Test with curl before frontend
Always test API endpoints with curl first to isolate issues.

---

## 🚀 Deployment

### Quick Deploy to Production

```bash
# 1. Commit your changes
git add .
git commit -m "feat: your changes here"

# 2. Push to master (triggers GitHub Actions)
git push origin master

# 3. Monitor deployment
# Check: https://github.com/cd3331/pm-document-intelligence/actions

# 4. Verify deployment (after ~10 minutes)
curl https://api.joyofpm.com/health
```

**Full deployment guide**: See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## 📞 Getting Help

- **Issues**: [GitHub Issues](https://github.com/cd3331/pm-document-intelligence/issues)
- **Email**: cd3331github@gmail.com
- **Documentation**: [docs/](docs/)

---

## ✅ Success Checklist

After setup, verify everything works:

- [ ] Server starts without errors
- [ ] `/health` endpoint returns "healthy" status
- [ ] Can register a new user
- [ ] Can login and get JWT token
- [ ] Can upload a document
- [ ] Can list documents
- [ ] Can process a document
- [ ] Can view document analysis
- [ ] Can delete a document

If all checked ✅, you're ready to go!

---

**Next Steps**: See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for advanced development topics.

---

© 2025 Chandra Dunn / JoyofPM AI Solutions. Portfolio demonstration project.
