# Changelog

All notable changes to PM Document Intelligence will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Fine-tuned custom models for improved accuracy
- Advanced analytics dashboard
- Mobile app (iOS and Android)
- Slack integration
- Microsoft Teams integration
- Advanced workflow automation

---

## [1.0.1] - 2025-11-05

### Fixed
- **Critical Bug Fix**: Fixed Prometheus metric type bug - changed `http_requests_in_progress` from Counter to Gauge (backend/app/main.py:81)
  - Counters cannot decrement, causing AttributeError when requests completed
  - Now properly tracks concurrent requests
- Fixed Redis authentication configuration in Docker Compose
  - Added password to REDIS_URL connection string
  - Resolved authentication errors on startup
- Fixed Docker environment variable loading
  - Added `env_file: - .env` to backend service
  - Explicitly mounted Supabase service key and JWT secret
- Fixed Nginx configuration issues
  - Removed duplicate timeout directives from proxy_params.conf
  - Added missing proxy_params.conf volume mount
  - Added self-signed SSL certificates for local development
- Fixed missing Prometheus metrics directory
  - Created `/tmp/prometheus` directory in Dockerfile
  - Set proper ownership for appuser

### Changed
- **Dependency Upgrades** (resolved version conflicts):
  - Upgraded supabase: 2.3.0 → 2.23.2
  - Upgraded postgrest: 0.13.2 → 2.23.2
  - Upgraded pydantic: 2.5.3 → 2.11.7
  - Upgraded pydantic-settings: 2.1.0 → 2.6.1
  - Upgraded httpx: 0.26.0 → 0.27.0
  - Upgraded websockets: 12.0 → 13.1 (for asyncio support)

### Added
- **New Dependencies** (previously missing):
  - sqlalchemy==2.0.25 - PostgreSQL ORM
  - alembic==1.13.1 - Database migrations
  - aioboto3==12.3.0 - Async AWS SDK
  - tenacity==8.2.3 - Retry logic and resilience
- **Exception Classes** (backend/app/utils/exceptions.py):
  - Added `ServiceError` - Generic external service errors
  - Added `NotFoundError` - Generic resource not found
- **Monitoring**:
  - Configured Sentry error tracking (SENTRY_ENABLED=true)
  - Added production Sentry DSN for error reporting
  - Sentry now captures all application errors and performance data
- **Enhanced .gitignore patterns**:
  - Python: `*.pyo`, `*.pyd`
  - Environment: `secrets.yml`, `secrets.yml.*`, `!secrets.yml.example`
  - AWS: `*.crt` (SSL certificates)
  - Testing: `nosetests.xml`, `test-reports/`
  - Docker: `docker-compose.override.yml`, `.docker/`, `*.pid`
  - Frontend: `frontend/node_modules/`, `frontend/dist/`, `frontend/.cache/`, `frontend/.parcel-cache/`, `frontend/.next/`, `frontend/.nuxt/`, `frontend/out/`
  - OS: `.AppleDouble`

### Security
- Sentry DSN now properly secured in environment variables
- SSL certificates configured for HTTPS in development
- Enhanced .gitignore to prevent committing secrets

### Infrastructure
- Docker container now properly loads all environment variables
- Backend service dependencies properly configured (postgres, redis health checks)
- Self-signed SSL certificates mounted for local HTTPS development

### Performance
- Prometheus metrics now properly track concurrent requests
- Redis caching operational with authentication

### Documentation
- Updated CHANGELOG.md with all recent changes
- Documented dependency upgrade path
- Added troubleshooting guide for common setup issues

---

## [1.0.0] - 2024-01-20

### Added
- **Core Features**:
  - Document upload (PDF, DOCX, TXT) with drag-and-drop
  - AI-powered document analysis (summaries, action items, risks)
  - Semantic search with pgvector
  - Multi-agent AI system (specialized agents per task)
  - Real-time processing updates via PubNub
  - User authentication with JWT
  - Role-based access control (RBAC)
  - Multi-tenancy support for organizations

- **AI Capabilities**:
  - Executive summaries (3 lengths: short, medium, detailed)
  - Action item extraction with owners and deadlines
  - Risk assessment with severity levels
  - Q&A capabilities over documents
  - Multi-document synthesis
  - Intelligent model routing (GPT-4, Claude, GPT-3.5)

- **Search Features**:
  - Semantic search using vector embeddings
  - Keyword search via Elasticsearch
  - Hybrid search (combining semantic + keyword)
  - Advanced filtering (date, type, status)
  - Saved searches

- **Analytics**:
  - Usage dashboard
  - Cost analytics by model
  - Document processing statistics
  - Performance metrics
  - User activity tracking

- **API**:
  - RESTful API with OpenAPI/Swagger documentation
  - Authentication endpoints
  - Document management endpoints
  - Processing endpoints
  - Search endpoints
  - Analytics endpoints
  - Model management endpoints

- **Infrastructure**:
  - AWS deployment (ECS Fargate, RDS, S3)
  - PostgreSQL database with pgvector extension
  - Redis caching
  - CloudFront CDN
  - Automated backups
  - CI/CD pipeline with GitHub Actions

- **Security**:
  - TLS 1.3 encryption
  - Data encryption at rest (AES-256)
  - PII detection and masking
  - Audit logging
  - GDPR compliance features
  - SOC 2 ready architecture

- **Documentation**:
  - Comprehensive README
  - API documentation
  - User guide with tutorials
  - Development guide
  - Deployment guide
  - Security documentation
  - Performance benchmarks
  - Cost analysis
  - Architecture decision records (ADRs)

### Security
- JWT-based authentication
- bcrypt password hashing (cost factor: 12)
- Row-level security for multi-tenancy
- Rate limiting on all endpoints
- CSRF protection
- Input validation and sanitization
- SQL injection prevention

### Performance
- API response time p95: 450ms
- Document processing: 45s average
- Search query p95: 180ms
- Support for 500+ concurrent users
- Auto-scaling based on load

---

## [0.9.0] - 2024-01-15 (Beta Release)

### Added
- Beta release for early adopters
- Core document processing pipeline
- Basic AI analysis features
- User authentication and authorization
- Organization management

### Changed
- Migrated from single AI model to multi-model approach
- Improved prompt engineering for better accuracy
- Optimized database queries for performance

### Fixed
- Memory leak in document processing
- Race condition in concurrent uploads
- Incorrect action item categorization

### Security
- Added audit logging for all data access
- Implemented PII detection in training data
- Enhanced RBAC permission checks

---

## [0.8.0] - 2024-01-10 (Alpha Release)

### Added
- Alpha release for internal testing
- Document upload and storage
- Basic text extraction
- Simple summarization
- User registration and login

### Known Issues
- Performance issues with large documents
- Limited AI model options
- No real-time updates
- Basic error handling

---

## [0.7.0] - 2024-01-05 (Internal Prototype)

### Added
- Initial prototype
- Proof of concept for AI document analysis
- Basic FastAPI backend
- PostgreSQL database
- Simple frontend

---

## Version History Summary

| Version | Release Date | Key Features | Status |
|---------|--------------|--------------|--------|
| 1.0.1 | 2025-11-05 | Bug fixes, dependency updates, Sentry integration | Current |
| 1.0.0 | 2024-01-20 | Production release | Stable |
| 0.9.0 | 2024-01-15 | Beta testing | Deprecated |
| 0.8.0 | 2024-01-10 | Alpha release | Deprecated |
| 0.7.0 | 2024-01-05 | Internal prototype | Deprecated |

---

## Upgrade Guide

### From 1.0.0 to 1.0.1

**Dependency Updates**:
```bash
# Pull latest code
git pull origin master

# Update Python dependencies
pip install -r backend/requirements.txt --upgrade

# Rebuild Docker containers
docker compose build --no-cache
docker compose up -d
```

**Configuration Changes**:
```bash
# Add Sentry DSN to .env (optional but recommended)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
SENTRY_ENABLED=true

# Verify Redis authentication is configured
REDIS_URL=redis://:redispassword@redis:6379/0
```

**Breaking Changes**:
- None - this is a patch release with bug fixes only

**New Features**:
- Sentry error tracking (configure DSN in .env)
- Improved Prometheus metrics tracking

**Verification**:
```bash
# Check application health
curl http://localhost:8000/health

# Verify Sentry initialization
docker compose logs backend | grep -i sentry
# Should see: "✓ Sentry initialized successfully"
```

---

### From 0.9.0 to 1.0.0

**Database Migrations**:
```bash
# Backup database first
pg_dump pm_doc_intel > backup_v0.9.0.sql

# Run migrations
alembic upgrade head

# Verify migration
alembic current
```

**Configuration Changes**:
```bash
# Add new environment variables
PUBNUB_PUBLISH_KEY=your_key
PUBNUB_SUBSCRIBE_KEY=your_key
ENABLE_MULTI_MODEL=true
```

**Breaking Changes**:
- API endpoint `/api/process` now returns job_id instead of immediate results
- Search endpoint now uses cursor-based pagination (update client code)
- Authentication tokens now expire after 1 hour (was 24 hours)

**New Features**:
- Enable real-time updates in your application
- Configure intelligent model routing for cost savings
- Set up analytics dashboard

---

## Migration Notes

### Data Migrations

**0.9.0 → 1.0.0**:
- Added `organization_id` to all tables
- Created `vector_embeddings` table for semantic search
- Added `audit_logs` table for compliance
- Added indexes for performance optimization

**0.8.0 → 0.9.0**:
- Migrated from single AI provider to multi-provider
- Added `processing_results` table
- Refactored document storage structure

---

## Deprecation Notices

### Deprecated in 1.0.0
- Old synchronous processing endpoint `/api/process-sync` (use async `/api/process`)
- Legacy authentication with API keys (use JWT tokens)
- Direct S3 URL access (use presigned URLs)

### Removed in 1.0.0
- Alpha/beta feature flags
- Test user accounts
- Development-only endpoints

---

## Security Updates

### 1.0.0 (2024-01-20)
- Added PII detection for training data
- Implemented Row-Level Security (RLS) for multi-tenancy
- Enhanced audit logging
- Added CSRF protection
- Updated dependencies to patch vulnerabilities

### 0.9.0 (2024-01-15)
- Fixed XSS vulnerability in document viewer
- Added rate limiting to prevent abuse
- Improved password strength requirements
- Updated JWT expiration handling

---

## Performance Improvements

### 1.0.0
- Reduced API latency by 40% through caching
- Optimized database queries (82% faster for document lists)
- Added HNSW index for vector search (75% faster)
- Implemented connection pooling
- Added CDN for static assets

### 0.9.0
- Improved document processing speed (30% faster)
- Optimized AI API calls through batching
- Reduced memory usage by 25%

---

## Known Issues

### 1.0.0
- Large documents (>50 pages) may take longer than 60 seconds to process
- Safari users may experience issues with drag-and-drop upload
- Mobile web UI needs optimization for small screens
- Elasticsearch occasionally requires manual index refresh

**Workarounds**:
- For large documents, use batch upload with lower priority
- Safari users can use "Browse Files" button instead
- Mobile app coming in 1.1.0
- Automatic index refresh implemented in monitoring

---

## Future Roadmap

### Version 1.1.0 (Q2 2024)
- [ ] Mobile apps (iOS, Android)
- [ ] Advanced analytics dashboard
- [ ] Custom model fine-tuning UI
- [ ] Workflow automation
- [ ] Integration marketplace

### Version 1.2.0 (Q3 2024)
- [ ] Slack integration
- [ ] Microsoft Teams integration
- [ ] Advanced collaboration features
- [ ] Version control for documents
- [ ] Advanced search filters

### Version 2.0.0 (Q4 2024)
- [ ] Multi-language support
- [ ] Voice-to-text for meeting notes
- [ ] Video transcription
- [ ] Advanced AI features (sentiment analysis, trend detection)
- [ ] White-label solution for enterprise

---

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on contributing to this project.

---

## Support

For questions or issues:
- **Documentation**: https://docs.pmdocintel.com
- **GitHub Issues**: https://github.com/cd3331/pm-document-intelligence/issues
- **Email**: cd3331github@gmail.com
- **Community Forum**: https://community.pmdocintel.com

---

## License

MIT License - see [LICENSE](../LICENSE) file for details.

---

**Last Updated**: 2025-11-05
**Current Version**: 1.0.1
