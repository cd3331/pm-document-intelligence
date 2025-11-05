# Development Guide

Complete guide for developers contributing to PM Document Intelligence.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Setup](#local-setup)
3. [Project Structure](#project-structure)
4. [Development Workflow](#development-workflow)
5. [Running Tests](#running-tests)
6. [Code Style](#code-style)
7. [Database Management](#database-management)
8. [API Development](#api-development)
9. [Frontend Development](#frontend-development)
10. [Debugging](#debugging)
11. [Performance Optimization](#performance-optimization)
12. [Contributing](#contributing)

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.11+ | Backend runtime |
| PostgreSQL | 15+ | Database |
| Redis | 7+ | Caching & queues |
| Node.js | 18+ | Frontend tooling |
| Git | 2.30+ | Version control |
| Docker | 20+ | Containerization (optional) |

### Development Tools

**Recommended IDE**:
- **VS Code** with extensions:
  - Python
  - Pylance
  - Black Formatter
  - isort
  - autoDocstring
  - Database Client

**Alternative IDEs**:
- PyCharm Professional
- Cursor
- Claude Code (CLI)

### API Keys Required

```bash
# AI Services
OPENAI_API_KEY=sk-...
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# Real-time
PUBNUB_PUBLISH_KEY=pub-c-...
PUBNUB_SUBSCRIBE_KEY=sub-c-...

# Monitoring (Recommended for production)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id  # Error tracking
SENTRY_ENABLED=true  # Set to false for local development if not needed
```

---

## Local Setup

### 1. Clone Repository

```bash
git clone https://github.com/cd3331/pm-document-intelligence.git
cd pm-document-intelligence
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Verify Python version
python --version  # Should be 3.11+
```

### 3. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Install pre-commit hooks
pre-commit install
```

**requirements-dev.txt**:
```txt
# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0

# Code Quality
black==23.12.1
isort==5.13.2
flake8==6.1.0
mypy==1.7.1
pylint==3.0.3

# Documentation
sphinx==7.2.6
sphinx-rtd-theme==2.0.0

# Debugging
ipdb==0.13.13
ipython==8.18.1

# Load Testing
locust==2.20.0
```

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your configuration
nano .env
```

**.env Configuration**:
```bash
# Application
ENV=development
DEBUG=true
SECRET_KEY=your-secret-key-change-in-production

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/pm_doc_intel

# Redis
REDIS_URL=redis://localhost:6379/0

# AI Services
OPENAI_API_KEY=sk-...
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# S3 Storage
S3_BUCKET_NAME=pm-doc-intel-dev
S3_ENDPOINT_URL=http://localhost:9000  # For local MinIO

# PubNub
PUBNUB_PUBLISH_KEY=pub-c-...
PUBNUB_SUBSCRIBE_KEY=sub-c-...

# Monitoring
LOG_LEVEL=DEBUG
```

### 5. Setup Database

**Install PostgreSQL with pgvector**:
```bash
# macOS
brew install postgresql@15
brew install pgvector

# Ubuntu/Debian
sudo apt-get install postgresql-15
sudo apt-get install postgresql-15-pgvector

# Docker (recommended for development)
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=pm_doc_intel \
  -p 5432:5432 \
  ankane/pgvector
```

**Create Database**:
```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE pm_doc_intel;

# Enable pgvector extension
\c pm_doc_intel
CREATE EXTENSION vector;

# Exit
\q
```

**Run Migrations**:
```bash
# Initialize Alembic (first time only)
alembic init alembic

# Run migrations
alembic upgrade head

# Verify migrations
alembic current
```

### 6. Setup Redis

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Docker (recommended)
docker run -d \
  --name redis \
  -p 6379:6379 \
  redis:7-alpine

# Test connection
redis-cli ping
# Should return: PONG
```

### 7. Setup MinIO (Local S3)

```bash
# Run MinIO for local S3 development
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"

# Access MinIO Console: http://localhost:9001
# Create bucket: pm-doc-intel-dev
```

### 8. Start Development Server

```bash
# Start FastAPI server with auto-reload
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# Or use the make command
make dev

# Server running at: http://localhost:8000
# API docs at: http://localhost:8000/docs
```

### 9. Verify Setup

```bash
# Run health check
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "database": "connected",
#   "redis": "connected",
#   "s3": "connected"
# }
```

---

## Project Structure

```
pm-document-intelligence/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application
│   │   ├── core/
│   │   │   ├── config.py           # Configuration
│   │   │   ├── database.py         # Database connection
│   │   │   ├── auth.py             # Authentication
│   │   │   └── security.py         # Security utilities
│   │   ├── models/
│   │   │   ├── user.py             # User model
│   │   │   ├── document.py         # Document models
│   │   │   └── organization.py     # Organization model
│   │   ├── routes/
│   │   │   ├── auth.py             # Auth endpoints
│   │   │   ├── documents.py        # Document endpoints
│   │   │   ├── processing.py       # Processing endpoints
│   │   │   ├── search.py           # Search endpoints
│   │   │   └── models.py           # Model management
│   │   ├── services/
│   │   │   ├── document_service.py
│   │   │   ├── processing_service.py
│   │   │   ├── search_service.py
│   │   │   └── feedback_loop.py
│   │   └── agents/
│   │       ├── base_agent.py
│   │       ├── summary_agent.py
│   │       └── action_item_agent.py
│   └── workers/
│       └── processing_worker.py    # Background workers
├── ml/
│   ├── models/
│   │   ├── embeddings.py           # Embedding generation
│   │   └── prompt_templates.py     # Prompt library
│   ├── training/
│   │   ├── data_preparation.py
│   │   └── fine_tuning.py
│   ├── monitoring/
│   │   └── model_performance.py
│   └── optimization/
│       └── intelligent_router.py
├── frontend/
│   ├── templates/                  # HTML templates
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   └── documents.html
│   ├── static/
│   │   ├── css/
│   │   │   └── main.css
│   │   └── js/
│   │       └── app.js
├── tests/
│   ├── unit/
│   │   ├── test_document_service.py
│   │   ├── test_search_service.py
│   │   └── test_agents.py
│   ├── integration/
│   │   ├── test_api_endpoints.py
│   │   └── test_processing_pipeline.py
│   └── load/
│       └── locustfile.py
├── alembic/
│   ├── versions/                   # Database migrations
│   └── env.py
├── docs/                           # Documentation
├── scripts/                        # Utility scripts
├── .github/
│   └── workflows/
│       └── ci.yml                  # CI/CD pipeline
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── .pre-commit-config.yaml
├── Makefile
└── README.md
```

### Key Directories

**backend/app/**:
- Core application code
- API routes and business logic
- Database models

**ml/**:
- Machine learning components
- Model training and optimization
- Prompt engineering

**tests/**:
- Unit tests for individual components
- Integration tests for workflows
- Load tests for performance

**alembic/**:
- Database migration scripts
- Schema version control

---

## Development Workflow

### 1. Create Feature Branch

```bash
# Update main branch
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/add-new-agent

# Naming conventions:
# feature/description  - New features
# fix/description      - Bug fixes
# docs/description     - Documentation
# refactor/description - Code refactoring
```

### 2. Development Cycle

```bash
# Make changes
# Run tests frequently
pytest tests/unit/test_your_module.py

# Format code
make format

# Lint code
make lint

# Run all tests
make test
```

### 3. Commit Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add new summarization agent

- Implement specialized agent for technical specs
- Add custom prompt templates
- Include unit tests
- Update documentation"

# Commit message format:
# type: subject
#
# body (optional)
#
# footer (optional)

# Types:
# feat:     New feature
# fix:      Bug fix
# docs:     Documentation
# style:    Formatting
# refactor: Code refactoring
# test:     Tests
# chore:    Maintenance
```

### 4. Push and Create PR

```bash
# Push to GitHub
git push origin feature/add-new-agent

# Create Pull Request on GitHub
# - Provide clear description
# - Link related issues
# - Request reviewers
# - Wait for CI checks
```

### 5. Code Review

**Reviewer Checklist**:
- [ ] Code follows style guidelines
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] No security vulnerabilities
- [ ] Performance implications considered
- [ ] API changes are backward compatible

### 6. Merge

```bash
# After approval, merge via GitHub
# Delete branch after merge
git branch -d feature/add-new-agent
```

---

## Running Tests

### Unit Tests

Test individual components in isolation:

```bash
# Run all unit tests
pytest tests/unit/

# Run specific test file
pytest tests/unit/test_document_service.py

# Run specific test
pytest tests/unit/test_document_service.py::test_upload_document

# Run with coverage
pytest --cov=backend tests/unit/

# Generate HTML coverage report
pytest --cov=backend --cov-report=html tests/unit/
open htmlcov/index.html
```

**Example Unit Test**:
```python
# tests/unit/test_document_service.py
import pytest
from backend.app.services.document_service import DocumentService

@pytest.fixture
def document_service(db_session):
    return DocumentService(db_session)

def test_upload_document(document_service, mock_file):
    """Test document upload"""
    result = document_service.upload(
        file=mock_file,
        user_id="user_123",
        document_type="meeting_notes"
    )

    assert result.id is not None
    assert result.filename == "test.pdf"
    assert result.status == "uploaded"

def test_upload_invalid_file_type(document_service):
    """Test upload with invalid file type"""
    with pytest.raises(ValueError, match="Invalid file type"):
        document_service.upload(
            file=mock_file,
            user_id="user_123",
            file_type="exe"
        )
```

### Integration Tests

Test complete workflows:

```bash
# Run integration tests
pytest tests/integration/

# Run with real API calls (slower)
pytest tests/integration/ --with-real-apis
```

**Example Integration Test**:
```python
# tests/integration/test_processing_pipeline.py
import pytest
from fastapi.testclient import TestClient

def test_complete_processing_pipeline(client: TestClient, auth_token):
    """Test full document processing workflow"""
    # Upload document
    with open("tests/fixtures/sample.pdf", "rb") as f:
        response = client.post(
            "/api/documents/upload",
            files={"file": f},
            headers={"Authorization": f"Bearer {auth_token}"}
        )

    assert response.status_code == 201
    doc_id = response.json()["id"]

    # Trigger processing
    response = client.post(
        f"/api/process/{doc_id}",
        json={"tasks": ["summary", "action_items"]},
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # Wait for completion (with timeout)
    # ... polling logic ...

    # Verify results
    response = client.get(
        f"/api/documents/{doc_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "summary" in data["processing_results"]
```

### Load Tests

Test performance under load:

```bash
# Run Locust load tests
locust -f tests/load/locustfile.py

# Or with specific parameters
locust -f tests/load/locustfile.py \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --host https://api.pmdocintel.com
```

**Example Load Test**:
```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class DocumentUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Login before tests"""
        response = self.client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password"
        })
        self.token = response.json()["access_token"]

    @task(3)
    def list_documents(self):
        """List documents (most common operation)"""
        self.client.get(
            "/api/documents",
            headers={"Authorization": f"Bearer {self.token}"}
        )

    @task(1)
    def upload_document(self):
        """Upload document (less frequent)"""
        with open("tests/fixtures/sample.pdf", "rb") as f:
            self.client.post(
                "/api/documents/upload",
                files={"file": f},
                headers={"Authorization": f"Bearer {self.token}"}
            )

    @task(2)
    def search_documents(self):
        """Search documents"""
        self.client.get(
            "/api/search?q=budget",
            headers={"Authorization": f"Bearer {self.token}"}
        )
```

### Test Fixtures

**conftest.py**:
```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import Base, get_db

# Test database
SQLALCHEMY_DATABASE_URL = "postgresql://user:pass@localhost/test_db"

@pytest.fixture(scope="session")
def engine():
    """Create test database engine"""
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(engine):
    """Create database session for tests"""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def client(db_session):
    """Create test client"""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

@pytest.fixture
def auth_token(client):
    """Get authentication token"""
    response = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "password"
    })
    return response.json()["access_token"]

@pytest.fixture
def mock_file():
    """Create mock file for uploads"""
    from io import BytesIO
    return BytesIO(b"fake pdf content")
```

---

## Code Style

### Python Style Guide

Follow [PEP 8](https://pep8.org/) with these specifics:

**Formatting**:
```python
# Use Black formatter (line length: 88)
# Use isort for imports

# Good
from typing import Dict, Any, Optional
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User


def process_document(
    document_id: uuid.UUID,
    user: User,
    db: Session
) -> Dict[str, Any]:
    """Process a document.

    Args:
        document_id: Document UUID
        user: User object
        db: Database session

    Returns:
        Processing result dictionary

    Raises:
        ValueError: If document not found
    """
    # Implementation
    pass
```

**Type Hints**:
```python
# Always use type hints
def get_user(user_id: uuid.UUID, db: Session) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

# For complex types
from typing import Dict, List, Optional, Union

def process_results(
    results: List[Dict[str, Any]],
    options: Optional[Dict[str, Union[str, int]]] = None
) -> Dict[str, List[str]]:
    pass
```

**Docstrings**:
```python
def calculate_cost(
    model: str,
    tokens: int,
    multiplier: float = 1.0
) -> float:
    """Calculate AI API cost.

    Args:
        model: Model name (e.g., "gpt-4")
        tokens: Number of tokens used
        multiplier: Cost multiplier for special pricing

    Returns:
        Cost in USD

    Raises:
        ValueError: If model not recognized

    Example:
        >>> calculate_cost("gpt-4", 1000)
        0.03
    """
    pass
```

### Linting

```bash
# Run all linters
make lint

# Individual linters
black backend/  # Format code
isort backend/  # Sort imports
flake8 backend/  # Style check
mypy backend/   # Type check
pylint backend/ # Code analysis
```

### Pre-commit Hooks

**.pre-commit-config.yaml**:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: ['--max-line-length=88', '--extend-ignore=E203']

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

---

## Database Management

### Creating Migrations

```bash
# Generate migration from model changes
alembic revision --autogenerate -m "add feedback table"

# Edit generated migration file
nano alembic/versions/xxx_add_feedback_table.py

# Apply migration
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

**Example Migration**:
```python
# alembic/versions/xxx_add_feedback_table.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table(
        'feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('result_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rating', sa.String(), nullable=False),
        sa.Column('corrections', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    op.create_index('idx_feedback_result_id', 'feedback', ['result_id'])
    op.create_index('idx_feedback_user_id', 'feedback', ['user_id'])

def downgrade():
    op.drop_table('feedback')
```

### Database Seeds

```bash
# Seed database with test data
python scripts/seed_database.py

# Or use make command
make seed-db
```

**scripts/seed_database.py**:
```python
from backend.app.core.database import SessionLocal
from backend.app.models.user import User
from backend.app.models.organization import Organization

def seed_data():
    db = SessionLocal()

    # Create test organization
    org = Organization(
        name="Test Org",
        plan="pro"
    )
    db.add(org)
    db.commit()

    # Create test users
    users = [
        User(email="admin@test.com", role="admin", organization_id=org.id),
        User(email="user@test.com", role="member", organization_id=org.id),
    ]
    db.add_all(users)
    db.commit()

    print("Database seeded successfully!")

if __name__ == "__main__":
    seed_data()
```

---

## API Development

### Adding New Endpoint

1. **Define Route**:
```python
# backend/app/routes/documents.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/documents", tags=["documents"])

@router.post("/{document_id}/export")
async def export_document(
    document_id: uuid.UUID,
    format: str = "pdf",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export document to specified format.

    Args:
        document_id: Document UUID
        format: Export format (pdf, docx, txt)
        current_user: Authenticated user
        db: Database session

    Returns:
        Export file URL

    Raises:
        HTTPException: If document not found or access denied
    """
    # Implementation
    pass
```

2. **Add Request/Response Models**:
```python
# backend/app/schemas/document.py
from pydantic import BaseModel
from typing import Optional

class ExportRequest(BaseModel):
    format: str = "pdf"
    include_metadata: bool = True
    watermark: Optional[str] = None

class ExportResponse(BaseModel):
    document_id: uuid.UUID
    export_url: str
    format: str
    expires_at: datetime
```

3. **Write Tests**:
```python
# tests/unit/test_export.py
def test_export_document(client, auth_token, document_id):
    response = client.post(
        f"/api/documents/{document_id}/export",
        json={"format": "pdf"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    assert "export_url" in response.json()
```

4. **Update Documentation**:
```python
# Add to docs/API.md
# Add to OpenAPI schema
```

---

## Frontend Development

### htmx Patterns

**Dynamic Content Loading**:
```html
<!-- templates/documents.html -->
<div id="documents-list"
     hx-get="/api/documents"
     hx-trigger="load"
     hx-swap="innerHTML">
    Loading...
</div>
```

**Form Submission**:
```html
<form hx-post="/api/documents/upload"
      hx-encoding="multipart/form-data"
      hx-target="#upload-result">
    <input type="file" name="file">
    <button type="submit">Upload</button>
</form>

<div id="upload-result"></div>
```

**Real-time Updates**:
```javascript
// static/js/app.js
const pubnub = new PubNub({
    publishKey: 'pub-c-...',
    subscribeKey: 'sub-c-...'
});

pubnub.subscribe({
    channels: [`document_${documentId}`]
});

pubnub.addListener({
    message: function(event) {
        updateProgress(event.message);
    }
});
```

---

## Debugging

### VS Code Launch Configuration

**.vscode/launch.json**:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "backend.app.main:app",
                "--reload",
                "--host", "0.0.0.0",
                "--port", "8000"
            ],
            "jinja": true,
            "justMyCode": false
        },
        {
            "name": "Pytest",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": [
                "tests/",
                "-v"
            ]
        }
    ]
}
```

### Logging

```python
# backend/app/core/logging.py
import logging
import sys

def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/app.log')
        ]
    )

# Usage
logger = logging.getLogger(__name__)
logger.info("Processing document", extra={"document_id": doc_id})
```

### Interactive Debugging

```python
# Add breakpoint in code
import ipdb; ipdb.set_trace()

# Or use built-in breakpoint()
breakpoint()
```

---

## Performance Optimization

### Database Query Optimization

```python
# Bad: N+1 query problem
documents = db.query(Document).all()
for doc in documents:
    print(doc.user.name)  # Separate query for each document

# Good: Use joinedload
from sqlalchemy.orm import joinedload

documents = db.query(Document).options(
    joinedload(Document.user)
).all()
```

### Caching

```python
# backend/app/core/cache.py
import redis
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379)

def cache(ttl: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{args}:{kwargs}"
            cached = redis_client.get(key)

            if cached:
                return json.loads(cached)

            result = await func(*args, **kwargs)
            redis_client.setex(key, ttl, json.dumps(result))
            return result

        return wrapper
    return decorator

# Usage
@cache(ttl=600)
async def get_document_summary(document_id: uuid.UUID):
    # Expensive operation
    pass
```

---

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed contribution guidelines.

**Quick Checklist**:
- [ ] Code follows style guide
- [ ] Tests added and passing
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] PR template filled out
- [ ] No merge conflicts

---

## Useful Commands

### Makefile

```makefile
# Makefile
.PHONY: dev test lint format clean

dev:
	uvicorn backend.app.main:app --reload

test:
	pytest --cov=backend tests/

lint:
	black --check backend/
	isort --check backend/
	flake8 backend/
	mypy backend/

format:
	black backend/
	isort backend/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache htmlcov .coverage

seed-db:
	python scripts/seed_database.py

migration:
	alembic revision --autogenerate -m "$(msg)"

migrate:
	alembic upgrade head
```

**Usage**:
```bash
make dev        # Start development server
make test       # Run tests
make lint       # Run linters
make format     # Format code
make clean      # Clean temp files
make seed-db    # Seed database
make migration msg="add new table"  # Create migration
make migrate    # Apply migrations
```

---

## Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **PostgreSQL Docs**: https://www.postgresql.org/docs/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **htmx Docs**: https://htmx.org/docs/
- **Project Wiki**: https://github.com/cd3331/pm-document-intelligence/wiki

---

**Last Updated**: November 2025
**Maintainers**: Engineering Team

**Recent Updates (v1.0.1)**:
- Fixed Prometheus metrics bug (Counter → Gauge for request tracking)
- Added Sentry error tracking integration
- Upgraded dependencies (supabase, pydantic, httpx, websockets)
- Enhanced .gitignore patterns
- See [CHANGELOG.md](CHANGELOG.md) for full details
