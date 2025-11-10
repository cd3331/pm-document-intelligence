# PM Document Intelligence

<div align="center">

**AI-Powered Project Management Document Processing & Intelligence Platform**

[![Build Status](https://img.shields.io/github/workflow/status/cd3331/pm-document-intelligence/CI?style=flat-square)](https://github.com/cd3331/pm-document-intelligence/actions)
[![Coverage](https://img.shields.io/codecov/c/github/cd3331/pm-document-intelligence?style=flat-square)](https://codecov.io/gh/cd3331/pm-document-intelligence)
[![License: Custom](https://img.shields.io/badge/License-Portfolio%20Demo-blue.svg?style=flat-square)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?style=flat-square)](https://www.python.org/downloads/)

[Live Demo](https://app.joyofpm.com) • [Documentation](docs/) • [API](https://api.joyofpm.com)

</div>

---

> **📌 Portfolio Demonstration Project**
> This is an **AI Engineering capstone project** showcasing advanced AI/ML capabilities.
> The full commercial product is proprietary to **JoyofPM AI Solutions**.
> For commercial licensing: **cd3331github@gmail.com**

---

## 📋 Overview

PM Document Intelligence is an enterprise-grade AI platform that transforms project management documents into actionable insights. Upload meeting notes, project plans, status reports, or technical specs, and get instant summaries, action items, risk assessments, and intelligent Q&A capabilities.

### 🎯 Key Features

- **🤖 Advanced AI Processing**: Multi-model AI (Claude, GPT-4, custom fine-tuned models)
- **📊 Multi-Agent Intelligence**: Specialized agents for different document types
- **🔍 Semantic Search**: Vector embeddings with pgvector for context-aware search
- **📈 Analytics & Insights**: Real-time dashboards with comprehensive metrics
- **🏢 Enterprise Multi-Tenancy**: Organization management with RBAC
- **🔄 Real-Time Collaboration**: PubNub-powered live updates
- **🎨 Modern UX**: htmx-powered dynamic interface with Tailwind CSS
- **🔐 Production-Ready Security**: JWT authentication, data encryption, GDPR compliance

See [full feature list](docs/FEATURES.md) for details.

---

## 🏗️ Architecture

High-level system architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                       AWS WAF (7 Security Rules)                 │
│  • OWASP Top 10  • SQL Injection  • Rate Limiting  • IP Rep     │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                Application Load Balancer (ALB)                   │
│            TLS 1.2+  •  Health Checks  •  Auto Scaling           │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│        FastAPI Backend (ECS Fargate)  •  CSP Headers             │
│        Redis Rate Limiting  •  Request Tracking                  │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
      ┌──────────────────────┼──────────────────────┐
      ↓                      ↓                       ↓
┌──────────┐         ┌──────────────┐        ┌────────────┐
│ AWS RDS  │         │  Redis Cache │        │   AWS S3   │
│PostgreSQL│         │  ElastiCache │        │  Documents │
│ +pgvector│         │              │        │            │
└──────────┘         └──────────────┘        └────────────┘
                             ↓
                   AI Services (Claude/GPT-4)
```

**Infrastructure Highlights:**
- **Multi-layered Security**: WAF → ALB → Application → Database
- **Auto-scaling**: ECS Fargate (1-4 tasks) with CPU-based scaling
- **Production Database**: AWS RDS PostgreSQL 15.14 with pgvector
- **Distributed Caching**: Redis ElastiCache for rate limiting & performance
- **Enterprise Monitoring**: CloudWatch metrics, logs, and alarms
- **Cost-Optimized**: ~$246/month for small-scale production

**Latest Updates (January 2025)**:
- ✅ Migrated from Supabase to AWS RDS PostgreSQL
- ✅ Fixed document deletion and processing endpoints
- ✅ Fixed HTMX routes for dynamic UI updates
- ✅ Optimized infrastructure costs (-21%)

See [Technical Architecture](TECHNICAL_ARCHITECTURE.md) for comprehensive details.

---

## 🔐 Security

Enterprise-grade security with defense-in-depth approach:

### Network Security
- **AWS WAF** with 7 managed rule sets (OWASP Top 10, SQLi, Linux exploits)
- **ALB Security Groups** restricting traffic to HTTPS only
- **Private Subnets** for all compute and data resources
- **NAT Gateways** for secure outbound traffic

### Application Security
- **Redis-Based Rate Limiting** (configurable per endpoint)
- **Content Security Policy (CSP)** with strict directives
- **JWT Authentication** with secure secret rotation
- **Request Tracking** with unique IDs for audit trails

### Data Security
- **Encrypted at Rest**: RDS encryption, S3 server-side encryption
- **Encrypted in Transit**: TLS 1.2+ everywhere
- **AWS Secrets Manager**: Secure credential storage with rotation
- **Database Isolation**: Private subnet, security group restrictions

### Monitoring & Compliance
- **CloudWatch Logging**: All requests, security events, and errors
- **Structured Logging**: JSON format with sensitive data redaction
- **Security Metrics**: WAF blocks, rate limits, suspicious patterns
- **Audit Trails**: Complete request/response logging

**Security Audit Status**: ✅ All CRITICAL and HIGH issues resolved

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **AWS Account** with:
  - RDS PostgreSQL 15.14+ (with pgvector extension)
  - ElastiCache Redis 7+
  - S3 Bucket for document storage
  - Bedrock (Claude 3.5 Sonnet access)
  - Textract & Comprehend (for document processing)
  - ECS Fargate, ALB, VPC (for deployment)
- **Environment Variables**:
  - `DATABASE_URL` - PostgreSQL connection string
  - `S3_BUCKET_NAME` - S3 bucket name
  - `JWT_SECRET_KEY` - JWT signing key (32+ chars)
  - `API_KEY_SALT` - API key salt (16+ chars)
- **Optional**:
  - OpenAI API Key (fallback AI)
  - PubNub Account (real-time features)

### Installation

```bash
# Clone repository
git clone https://github.com/cd3331/pm-document-intelligence.git
cd pm-document-intelligence

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Initialize database
alembic upgrade head

# Start application
uvicorn backend.app.main:app --reload
```

Access at http://localhost:8000

### Docker Quick Start

```bash
docker-compose up -d
open http://localhost:8000
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Technical Architecture](TECHNICAL_ARCHITECTURE.md) | **Complete tech stack & architecture** |
| [Functionality Test Report](FUNCTIONALITY_TEST_REPORT.md) | Production testing results (Jan 2025) |
| [Architecture](docs/ARCHITECTURE.md) | System design and components |
| [API Reference](docs/API.md) | Complete API documentation |
| [User Guide](docs/USER_GUIDE.md) | End-user tutorials |
| [Development](docs/DEVELOPMENT.md) | Developer setup guide |
| [Deployment](docs/DEPLOYMENT.md) | Production deployment |
| [Security](docs/SECURITY.md) | Security architecture & best practices |
| [Multi-Tenancy](docs/MULTI_TENANCY_GUIDE.md) | Enterprise features |
| [ML Optimization](docs/ML_OPTIMIZATION_GUIDE.md) | AI fine-tuning guide |
| [Cost Analysis](docs/COST_ANALYSIS.md) | Infrastructure cost breakdown |
| [Changelog](docs/CHANGELOG.md) | Version history and updates |

---

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=backend --cov-report=html

# Load tests
locust -f tests/load/locustfile.py
```

---

## 💰 Cost Estimation

**Current Infrastructure**: ~$246/month (cost-optimized for small-scale production)

**At Scale (10,000 documents/month)**:
- Infrastructure: ~$246-310/month
- AWS AI Services (variable): ~$330-740/month
- **Total**: ~$600-1,050/month

**Cost Breakdown**:
- ECS Fargate (1 vCPU, 2GB): $37
- RDS PostgreSQL (db.t3.medium, Single-AZ): $60
- ElastiCache Redis: $25
- ALB: $24
- NAT Gateways (2): $80
- S3 + CloudWatch: $20

See [Cost Analysis](docs/COST_ANALYSIS.md) for detailed breakdown and [Cost Optimization Report](infrastructure/COST_OPTIMIZATION_2025-01-10.md) for recent optimizations.

---

## 🤝 Contributing

Contributions welcome! See [Contributing Guide](CONTRIBUTING.md).

---

## 📄 License & Usage

**Portfolio Demonstration - Educational & Evaluation Purposes Only**

This repository is a **portfolio demonstration** of the PM Document Intelligence platform, created as part of an AI Engineering capstone project.

**✅ Permitted Uses:**
- View and study the code for educational purposes
- Reference the architecture in your own learning
- Evaluate as part of portfolio or job application review
- Link to this repository in academic or professional contexts

**❌ Prohibited Uses:**
- Use in production or commercial applications
- Modify or create derivative works for commercial purposes
- Sell, sublicense, or redistribute this code
- Remove copyright notices

**🏢 Commercial Product:**

The full commercial product is proprietary and owned by **JoyofPM AI Solutions**.

For commercial licensing inquiries, contact: **cd3331github@gmail.com**

---

© 2025 Chandra Dunn / JoyofPM AI Solutions. All Rights Reserved.

See [LICENSE](LICENSE) file for complete terms.

---

## 👤 Author

**Chandra Dunn**

- **GitHub**: [@cd3331](https://github.com/cd3331)
- **LinkedIn**: [chandra-dunn](https://linkedin.com/in/chandra-dunn)
- **Email**: cd3331github@gmail.com

---

## 📞 Contact

For questions, collaboration opportunities, or support:
- **Email**: cd3331github@gmail.com
- **GitHub Issues**: [pm-document-intelligence/issues](https://github.com/cd3331/pm-document-intelligence/issues)
- **Documentation**: [docs/](docs/)

---

<div align="center">

Made with ❤️ by developers, for developers

</div>
