# PM Document Intelligence Agent

A production-ready FastAPI application that intelligently processes project management documents using AWS Bedrock (Claude), Textract, Comprehend, OpenAI, Supabase, and PubNub for real-time collaboration and insights.

## Overview

The PM Document Intelligence Agent is an advanced document processing system designed specifically for project management workflows. It combines state-of-the-art AI models with enterprise-grade infrastructure to extract, analyze, and provide actionable insights from various document types including project plans, status reports, risk registers, and meeting notes.

### Key Features

- **Multi-Modal Document Processing**: Extract text, tables, and structure from PDFs, Word docs, spreadsheets, and presentations
- **Intelligent Analysis**: Leverages AWS Bedrock (Claude 3.5 Sonnet) and OpenAI for deep document understanding
- **Entity Recognition**: Automatic extraction of tasks, risks, stakeholders, dates, and milestones
- **Semantic Search**: Vector-based search powered by embeddings and Supabase
- **Real-Time Updates**: WebSocket and PubNub integration for live collaboration
- **Production-Ready**: Built with security, monitoring, rate limiting, and scalability from day one

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                           │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐   │
│  │   Web UI       │  │   Mobile App   │  │   CLI Tool     │   │
│  │   (Jinja2)     │  │   (Future)     │  │                │   │
│  └────────┬───────┘  └────────┬───────┘  └────────┬───────┘   │
│           └──────────────┬─────────────────────────┘            │
│                          │                                       │
└──────────────────────────┼───────────────────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────────────────┐
│                    FastAPI Backend                               │
│  ┌────────────────────┬─▼──────────────────────────────────┐   │
│  │   API Gateway      │  Routes & Endpoints                 │   │
│  │   - Rate Limiting  │  - /upload                          │   │
│  │   - Auth          │  - /process                         │   │
│  │   - CORS          │  - /query                           │   │
│  └────────────────────┴─────────────────────────────────────┘   │
│                          │                                       │
│  ┌─────────────┬─────────┴───────┬────────────┬──────────┐     │
│  │  Agents     │  Services       │ Middleware │  Utils   │     │
│  │  - PM Agent │  - Document     │ - Auth     │ - Logger │     │
│  │  - Risk     │  - AWS Bedrock  │ - Error    │ - Cache  │     │
│  │  - Task     │  - Textract     │ - Metrics  │ - Retry  │     │
│  │  - MCP      │  - Comprehend   │            │          │     │
│  └─────────────┴─────────────────┴────────────┴──────────┘     │
└──────────────────────────┬───────────────────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────────────────┐
│                   External Services                              │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ AWS Bedrock │  │ AWS Textract │  │ AWS Comprehend│          │
│  │ (Claude 3.5)│  │ (OCR + Forms)│  │ (NLP + NER)   │          │
│  └─────────────┘  └──────────────┘  └──────────────┘           │
│                                                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  OpenAI     │  │  Supabase    │  │   PubNub     │           │
│  │  (GPT-4o)   │  │  (DB + Auth) │  │  (Real-time) │           │
│  └─────────────┘  └──────────────┘  └──────────────┘           │
└───────────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────────────────┐
│              Infrastructure & Monitoring                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Redis     │  │   Celery     │  │  Prometheus  │           │
│  │  (Cache)    │  │  (Tasks)     │  │  (Metrics)   │           │
│  └─────────────┘  └──────────────┘  └──────────────┘           │
│                                                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Sentry    │  │   Logs       │  │   Terraform  │           │
│  │  (Errors)   │  │  (Loguru)    │  │  (IaC)       │           │
│  └─────────────┘  └──────────────┘  └──────────────┘           │
└───────────────────────────────────────────────────────────────────┘
```

## Project Goals

1. **Intelligent Extraction**: Automatically extract structured data from unstructured PM documents
2. **Context-Aware Analysis**: Understand project context, identify risks, track dependencies
3. **Actionable Insights**: Generate summaries, recommendations, and alerts
4. **Seamless Integration**: Easy integration with existing PM tools and workflows
5. **Enterprise-Grade**: Security, scalability, monitoring, and compliance built-in

## Quick Start

### Prerequisites

- Python 3.11+
- Poetry 1.7+
- Redis 7.0+
- PostgreSQL 15+ (via Supabase or local)
- AWS Account with Bedrock, Textract, and Comprehend access
- OpenAI API Key
- Supabase Account
- PubNub Account

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd pm-document-intelligence
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   ```

4. **Start Redis (required for caching and Celery)**
   ```bash
   # Using Docker
   docker run -d -p 6379:6379 redis:7-alpine

   # Or using local installation
   redis-server
   ```

5. **Run database migrations**
   ```bash
   poetry run alembic upgrade head
   ```

6. **Start the development server**
   ```bash
   poetry run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Start Celery worker (in separate terminal)**
   ```bash
   poetry run celery -A backend.app.celery worker --loglevel=info
   ```

8. **Start Celery Flower for monitoring (optional)**
   ```bash
   poetry run celery -A backend.app.celery flower --port=5555
   ```

### Verify Installation

Navigate to:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Metrics: http://localhost:9090/metrics
- Flower (Celery): http://localhost:5555

## Environment Setup

### Development Environment

1. **Configure AWS Credentials**
   ```bash
   aws configure
   # Or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env
   ```

2. **Request AWS Bedrock Model Access**
   - Go to AWS Bedrock console
   - Request access to Claude 3.5 Sonnet (anthropic.claude-3-5-sonnet-20241022-v2:0)
   - Wait for approval (usually instant for dev accounts)

3. **Set up Supabase**
   - Create a new project at https://supabase.com
   - Copy the project URL and anon key to .env
   - Run the provided schema migrations in Supabase SQL editor

4. **Configure PubNub**
   - Create a new app at https://dashboard.pubnub.com
   - Copy publish/subscribe/secret keys to .env

### Production Environment

See `docs/deployment.md` for comprehensive production deployment guide including:
- Infrastructure provisioning with Terraform
- Container orchestration (Docker/Kubernetes)
- CI/CD pipeline setup
- Security hardening
- Performance tuning
- Monitoring and alerting

## Development Workflow

### Code Style & Quality

We use automated tools to maintain code quality:

```bash
# Format code
poetry run black backend/ tests/
poetry run isort backend/ tests/

# Lint code
poetry run ruff check backend/ tests/
poetry run pylint backend/

# Type checking
poetry run mypy backend/

# Security scanning
poetry run bandit -r backend/
poetry run safety check
```

### Pre-commit Hooks

Install pre-commit hooks to automatically run checks:

```bash
poetry run pre-commit install
```

This will run formatting, linting, and security checks before each commit.

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=backend --cov-report=html

# Run specific test types
poetry run pytest -m unit          # Unit tests only
poetry run pytest -m integration   # Integration tests only
poetry run pytest -m e2e           # End-to-end tests only

# Run tests in parallel
poetry run pytest -n auto
```

### Project Structure

```
pm-document-intelligence/
├── backend/
│   └── app/
│       ├── agents/           # AI agents and orchestration
│       ├── mcp/             # Model Context Protocol implementation
│       ├── models/          # Pydantic models and schemas
│       ├── routes/          # API endpoints
│       ├── services/        # Business logic and external service integrations
│       ├── middleware/      # FastAPI middleware (auth, logging, etc.)
│       └── utils/           # Utility functions
├── frontend/
│   ├── templates/           # Jinja2 templates
│   └── static/             # CSS, JS, images
├── infrastructure/
│   ├── terraform/          # Infrastructure as Code
│   ├── scripts/            # Deployment and maintenance scripts
│   └── monitoring/         # Prometheus, Grafana configs
├── ml/
│   ├── models/             # ML model artifacts
│   ├── training/           # Training scripts
│   ├── monitoring/         # Model performance monitoring
│   └── notebooks/          # Jupyter notebooks for experiments
├── tests/
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   ├── e2e/               # End-to-end tests
│   └── load/              # Load testing with Locust
├── docs/
│   ├── api/               # API documentation
│   ├── architecture/      # Architecture decision records
│   └── decisions/         # Technical decision logs
├── .github/
│   └── workflows/         # GitHub Actions CI/CD
├── scripts/               # Development and utility scripts
└── config/               # Configuration files
```

## Testing Strategy

### Test Pyramid

1. **Unit Tests** (70%): Fast, isolated tests for individual functions and classes
2. **Integration Tests** (20%): Test interactions between components and external services
3. **E2E Tests** (10%): Full workflow tests simulating real user scenarios

### Mocking External Services

We use `moto` for mocking AWS services in tests:

```python
from moto import mock_textract, mock_comprehend

@mock_textract
def test_document_extraction():
    # Test code here
    pass
```

### Test Coverage

We maintain >80% code coverage. Check coverage report:

```bash
poetry run pytest --cov=backend --cov-report=html
open htmlcov/index.html
```

## API Documentation

### Key Endpoints

- `POST /api/v1/documents/upload` - Upload a document for processing
- `GET /api/v1/documents/{id}` - Get document details
- `POST /api/v1/documents/{id}/process` - Trigger document processing
- `POST /api/v1/query` - Natural language query across documents
- `GET /api/v1/analytics/dashboard` - Get PM dashboard data
- `WS /ws/updates` - WebSocket for real-time updates

Full API documentation available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

## Deployment Guidelines

### Docker Deployment

```bash
# Build image
docker build -t pm-document-intelligence:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  --env-file .env \
  pm-document-intelligence:latest
```

### Docker Compose

```bash
docker-compose up -d
```

### Kubernetes

See `infrastructure/kubernetes/` for manifests and Helm charts.

### Terraform

Provision AWS infrastructure:

```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

## Security Best Practices

- ✅ Environment variables for all secrets
- ✅ JWT-based authentication
- ✅ Rate limiting on all endpoints
- ✅ Input validation with Pydantic
- ✅ CORS configuration
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ XSS protection
- ✅ HTTPS enforcement in production
- ✅ Security headers middleware
- ✅ Regular dependency updates

## Monitoring & Observability

### Metrics

Prometheus metrics available at `/metrics`:
- Request latency and throughput
- Error rates
- External service call metrics (AWS, OpenAI)
- Custom business metrics

### Logging

Structured JSON logging with Loguru:
- Request/response logging
- Error tracking with stack traces
- Performance profiling
- Audit logs

### Error Tracking

Sentry integration for real-time error monitoring and alerting.

## Performance Optimization

- Redis caching for frequent queries
- Connection pooling for databases
- Async I/O for external API calls
- Celery for background processing
- Rate limiting to prevent abuse
- Compression for API responses

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Support

- Documentation: `/docs`
- Issues: GitHub Issues
- Email: support@example.com

## Roadmap

- [ ] Phase 1: Core document processing (Q1 2025)
- [ ] Phase 2: Advanced analytics and insights (Q2 2025)
- [ ] Phase 3: Integration with PM tools (Jira, Asana) (Q2 2025)
- [ ] Phase 4: Mobile application (Q3 2025)
- [ ] Phase 5: Multi-language support (Q4 2025)

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [AWS Bedrock](https://aws.amazon.com/bedrock/)
- [OpenAI](https://openai.com/)
- [Supabase](https://supabase.com/)
- [PubNub](https://www.pubnub.com/)

---

**Made with ❤️ for Project Managers worldwide**
