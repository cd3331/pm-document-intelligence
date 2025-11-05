# Contributing to PM Document Intelligence

Thank you for your interest in contributing to PM Document Intelligence! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Coding Standards](#coding-standards)
5. [Testing](#testing)
6. [Submitting Changes](#submitting-changes)
7. [Reporting Bugs](#reporting-bugs)
8. [Suggesting Features](#suggesting-features)
9. [Community](#community)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inspiring community for everyone. Please read and follow our Code of Conduct.

### Our Standards

**Positive behavior includes**:
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behavior includes**:
- Trolling, insulting/derogatory comments, and personal attacks
- Public or private harassment
- Publishing others' private information without permission
- Other conduct which could reasonably be considered inappropriate

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by contacting the project team at conduct@pmdocintel.com. All complaints will be reviewed and investigated promptly and fairly.

---

## Getting Started

### Prerequisites

Before contributing, ensure you have:
- Python 3.11+
- PostgreSQL 15+ with pgvector
- Redis 7+
- Git
- GitHub account
- Familiarity with FastAPI, SQLAlchemy, and async Python

### Fork and Clone

1. **Fork the repository** on GitHub

2. **Clone your fork**:
```bash
git clone https://github.com/YOUR_USERNAME/pm-document-intelligence.git
cd pm-document-intelligence
```

3. **Add upstream remote**:
```bash
git remote add upstream https://github.com/cd3331/pm-document-intelligence.git
```

4. **Verify remotes**:
```bash
git remote -v
# origin    https://github.com/YOUR_USERNAME/pm-document-intelligence.git (fetch)
# origin    https://github.com/YOUR_USERNAME/pm-document-intelligence.git (push)
# upstream  https://github.com/cd3331/pm-document-intelligence.git (fetch)
# upstream  https://github.com/cd3331/pm-document-intelligence.git (push)
```

### Set Up Development Environment

Follow the [Development Guide](docs/DEVELOPMENT.md) for detailed setup instructions:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Initialize database
alembic upgrade head

# Install pre-commit hooks
pre-commit install

# Run tests to verify setup
pytest
```

---

## Development Workflow

### 1. Stay Updated

Before starting work, sync with upstream:

```bash
git checkout main
git fetch upstream
git merge upstream/main
git push origin main
```

### 2. Create a Branch

Create a feature branch from `main`:

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

**Branch naming conventions**:
- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation changes
- `refactor/description` - Code refactoring
- `test/description` - Test additions/changes
- `chore/description` - Maintenance tasks

### 3. Make Changes

- Write clean, readable code
- Follow our coding standards (see below)
- Add tests for new functionality
- Update documentation as needed
- Commit frequently with clear messages

### 4. Commit Your Changes

**Commit message format**:
```
<type>: <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code formatting (no functional changes)
- `refactor`: Code refactoring
- `test`: Test additions or changes
- `chore`: Maintenance tasks
- `perf`: Performance improvements

**Example**:
```bash
git commit -m "feat: add semantic search for documents

Implement pgvector-based semantic search allowing users
to find documents by meaning rather than just keywords.

- Added vector_embeddings table
- Created HNSW index for fast similarity search
- Implemented search API endpoint
- Added tests for search functionality

Closes #123"
```

### 5. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 6. Create Pull Request

1. Go to your fork on GitHub
2. Click "Pull Request"
3. Select your branch
4. Fill out the PR template (see below)
5. Submit for review

---

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with these specifics:

**Formatting**:
- Line length: 88 characters (Black default)
- Indentation: 4 spaces
- Use double quotes for strings
- Use trailing commas in multi-line structures

**Naming Conventions**:
```python
# Variables and functions: snake_case
user_name = "John"
def get_document(document_id):
    pass

# Classes: PascalCase
class DocumentService:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_UPLOAD_SIZE = 50 * 1024 * 1024

# Private methods: _leading_underscore
def _internal_helper():
    pass
```

**Type Hints** (required):
```python
def process_document(
    document_id: uuid.UUID,
    user: User,
    options: Optional[Dict[str, Any]] = None
) -> ProcessingResult:
    """Process a document with AI analysis.

    Args:
        document_id: Document UUID
        user: User performing the action
        options: Optional processing options

    Returns:
        Processing result with AI outputs

    Raises:
        ValueError: If document not found
        ProcessingError: If processing fails
    """
    pass
```

**Docstrings** (Google style):
```python
def calculate_cost(tokens: int, model: str) -> float:
    """Calculate the cost of an AI API call.

    Calculates cost based on token count and model pricing.
    Supports GPT-4, GPT-3.5, and Claude models.

    Args:
        tokens: Number of tokens used
        model: Model name (e.g., "gpt-4", "claude-2")

    Returns:
        Cost in USD

    Raises:
        ValueError: If model is not recognized

    Example:
        >>> calculate_cost(1000, "gpt-4")
        0.03
    """
    pass
```

### Code Quality Tools

We use automated tools to maintain code quality:

```bash
# Format code
black backend/
isort backend/

# Lint code
flake8 backend/
pylint backend/
mypy backend/

# Run all checks
make lint
```

**Pre-commit hooks** automatically run these on every commit.

### Best Practices

**Do**:
- ✅ Write tests for new code
- ✅ Use type hints everywhere
- ✅ Add docstrings to functions and classes
- ✅ Keep functions small and focused
- ✅ Use meaningful variable names
- ✅ Handle errors gracefully
- ✅ Log important events
- ✅ Update documentation

**Don't**:
- ❌ Commit commented-out code
- ❌ Use print() for debugging (use logging)
- ❌ Commit secrets or API keys
- ❌ Skip tests
- ❌ Ignore linter warnings
- ❌ Write overly complex code
- ❌ Copy-paste code (DRY principle)

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_document_service.py

# Run with coverage
pytest --cov=backend tests/

# Run only fast tests (skip integration)
pytest -m "not slow"
```

### Writing Tests

**Test Structure**:
```python
# tests/unit/test_document_service.py
import pytest
from backend.app.services.document_service import DocumentService

@pytest.fixture
def document_service(db_session):
    """Provide document service instance"""
    return DocumentService(db_session)

def test_upload_document(document_service, mock_file):
    """Test successful document upload"""
    # Arrange
    filename = "test.pdf"
    file_content = b"test content"

    # Act
    result = document_service.upload(
        file=mock_file,
        filename=filename,
        user_id="user_123"
    )

    # Assert
    assert result.id is not None
    assert result.filename == filename
    assert result.status == "uploaded"

def test_upload_invalid_file_type(document_service):
    """Test upload rejects invalid file types"""
    with pytest.raises(ValueError, match="Invalid file type"):
        document_service.upload(
            file=mock_file,
            filename="test.exe",
            user_id="user_123"
        )
```

**Test Coverage Requirements**:
- Unit tests: 80% minimum
- Integration tests: Critical paths
- All new features must have tests
- Bug fixes must include regression tests

### Test Fixtures

Use `conftest.py` for shared fixtures:

```python
# tests/conftest.py
@pytest.fixture
def db_session():
    """Provide database session for tests"""
    # Setup
    session = create_test_session()
    yield session
    # Teardown
    session.rollback()
    session.close()

@pytest.fixture
def mock_file():
    """Provide mock file for upload tests"""
    return BytesIO(b"test file content")
```

---

## Submitting Changes

### Pull Request Process

1. **Update your branch** with latest upstream:
```bash
git fetch upstream
git rebase upstream/main
```

2. **Run all checks**:
```bash
# Format code
make format

# Lint
make lint

# Run tests
make test

# Verify everything passes
```

3. **Create pull request** on GitHub

4. **Fill out PR template**:
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe the tests you ran

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests passing
- [ ] No new warnings
```

### PR Review Process

**What reviewers look for**:
- Code quality and readability
- Test coverage
- Documentation updates
- Performance implications
- Security considerations
- Breaking changes

**Review timeline**:
- Initial review: Within 2 business days
- Follow-up: Within 1 business day
- Approval needed: 1 maintainer

**After approval**:
- Maintainer will merge PR
- Your contribution will be in next release
- You'll be added to contributors list

### Merge Requirements

Before merging, PRs must:
- ✅ Pass all CI/CD checks
- ✅ Have 1+ approvals
- ✅ Be up-to-date with main
- ✅ Have no merge conflicts
- ✅ Pass all tests
- ✅ Meet coverage requirements
- ✅ Have updated documentation

---

## Reporting Bugs

### Before Reporting

1. **Check existing issues**: Search [GitHub Issues](https://github.com/cd3331/pm-document-intelligence/issues)
2. **Verify the bug**: Reproduce in latest version
3. **Gather information**: Logs, error messages, steps to reproduce

### Bug Report Template

```markdown
## Bug Description
Clear description of the bug

## Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. See error

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., macOS 12.0]
- Python: [e.g., 3.11.1]
- Version: [e.g., 1.0.0]

## Logs
```
Paste relevant logs here
```

## Screenshots
If applicable, add screenshots
```

### Reporting Security Issues

**Do not** create public GitHub issues for security vulnerabilities.

Instead, email: security@pmdocintel.com

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours.

---

## Suggesting Features

### Before Suggesting

1. **Check existing requests**: Search [GitHub Issues](https://github.com/cd3331/pm-document-intelligence/issues?q=is%3Aissue+label%3Aenhancement)
2. **Consider scope**: Does it fit project goals?
3. **Think about implementation**: How might it work?

### Feature Request Template

```markdown
## Feature Description
Clear description of the feature

## Problem It Solves
What problem does this solve?

## Proposed Solution
How should this feature work?

## Alternatives Considered
What other solutions did you consider?

## Additional Context
Any other information, mockups, or examples
```

### Feature Discussion

1. **Submit feature request** as GitHub issue
2. **Community discussion** on feasibility and design
3. **Approval** by maintainers
4. **Implementation** by contributor or maintainer
5. **Review and merge**

---

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and discussions
- **Discord**: Real-time chat (link in README)
- **Email**: team@pmdocintel.com

### Getting Help

**For development questions**:
1. Check [Development Guide](docs/DEVELOPMENT.md)
2. Search [GitHub Discussions](https://github.com/cd3331/pm-document-intelligence/discussions)
3. Ask in Discord #development channel
4. Create GitHub Discussion

**For bug reports**:
1. Create GitHub Issue with bug template
2. Provide detailed information
3. Be responsive to questions

### Recognition

Contributors are recognized in:
- GitHub contributors page
- CHANGELOG.md for each release
- README.md contributors section

Significant contributors may be invited to join the maintainers team.

---

## Development Tips

### Useful Commands

```bash
# Development
make dev          # Start development server
make test         # Run tests
make lint         # Run linters
make format       # Format code
make clean        # Clean temporary files

# Database
make migrate      # Run migrations
make seed-db      # Seed database with test data

# Docker
docker-compose up -d      # Start services
docker-compose logs -f    # View logs
docker-compose down       # Stop services
```

### Debugging

**Using debugger**:
```python
# Add breakpoint
import ipdb; ipdb.set_trace()

# Or use built-in
breakpoint()
```

**Logging**:
```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Detailed information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error message")
```

**VS Code debugging**: See `.vscode/launch.json` for configurations

### Common Issues

**Import errors**:
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH="${PYTHONPATH}:${PWD}"
```

**Database connection errors**:
```bash
# Check PostgreSQL is running
pg_isready

# Check connection string in .env
echo $DATABASE_URL
```

**Test failures**:
```bash
# Run with verbose output
pytest -vv

# Run specific test
pytest tests/unit/test_file.py::test_function -vv
```

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## Questions?

If you have questions about contributing, please:
1. Check this guide and [Development Guide](docs/DEVELOPMENT.md)
2. Search [GitHub Discussions](https://github.com/cd3331/pm-document-intelligence/discussions)
3. Ask in Discord #development channel
4. Email: developers@pmdocintel.com

---

## Thank You!

Your contributions make PM Document Intelligence better for everyone. We appreciate your time and effort!

---

**Last Updated**: 2024-01-20
**Maintainers**: Engineering Team
