# PM Document Intelligence

<div align="center">

**AI-Powered Project Management Document Processing & Intelligence Platform**

[![Build Status](https://img.shields.io/github/workflow/status/cd3331/pm-document-intelligence/CI?style=flat-square)](https://github.com/cd3331/pm-document-intelligence/actions)
[![Coverage](https://img.shields.io/codecov/c/github/cd3331/pm-document-intelligence?style=flat-square)](https://codecov.io/gh/cd3331/pm-document-intelligence)
[![License: Custom](https://img.shields.io/badge/License-Portfolio%20Demo-blue.svg?style=flat-square)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?style=flat-square)](https://www.python.org/downloads/)

[Live Demo](https://demo.pmdocintel.com) • [Documentation](docs/) • [API Docs](https://api.pmdocintel.com/docs)

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
Frontend (htmx + Tailwind) → FastAPI Backend → AI Services (Claude/GPT-4)
                                ↓
                         PostgreSQL + pgvector
                                ↓
                         AWS S3 + Redis Cache
```

See [Architecture Documentation](docs/ARCHITECTURE.md) for detailed diagrams.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ with pgvector
- Redis 7+
- AWS Account (S3, Bedrock)
- OpenAI API Key

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
| [Architecture](docs/ARCHITECTURE.md) | System design and components |
| [API Reference](docs/API.md) | Complete API documentation |
| [User Guide](docs/USER_GUIDE.md) | End-user tutorials |
| [Development](docs/DEVELOPMENT.md) | Developer setup guide |
| [Deployment](docs/DEPLOYMENT.md) | Production deployment |
| [Multi-Tenancy](docs/MULTI_TENANCY_GUIDE.md) | Enterprise features |
| [ML Optimization](docs/ML_OPTIMIZATION_GUIDE.md) | AI fine-tuning guide |
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

Monthly costs at 10,000 documents/month: **$600-1,050**

See [Cost Analysis](docs/COST_ANALYSIS.md) for breakdown and optimization.

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
