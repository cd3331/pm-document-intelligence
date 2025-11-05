# Testing Guide

Comprehensive testing guide for the PM Document Intelligence backend.

## Table of Contents

- [Overview](#overview)
- [Test Structure](#test-structure)
- [Setup](#setup)
- [Running Tests](#running-tests)
- [Test Categories](#test-categories)
- [Coverage](#coverage)
- [Writing Tests](#writing-tests)
- [CI/CD Integration](#cicd-integration)

---

## Overview

The test suite provides comprehensive coverage for all backend components:

- **Multi-Agent System**: All 5 specialized agents + orchestrator
- **Document Processing**: Pipeline, state machine, AWS integration
- **Vector Search**: Embeddings, semantic search, hybrid search
- **Authentication**: JWT, registration, login, password reset
- **API Endpoints**: All routes with rate limiting
- **Error Handling**: Circuit breakers, retries, validation

### Test Statistics

- **Total Tests**: 50+
- **Coverage Target**: >85%
- **Test Types**: Unit, Integration, End-to-End
- **Async Support**: Full pytest-asyncio integration

---

## Test Structure

```
backend/tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Shared fixtures and configuration
├── test_agents.py           # Multi-agent system tests (50+ tests)
├── test_document_processing.py  # Document pipeline tests
├── test_vector_search.py    # Vector search tests
├── test_auth.py             # Authentication tests
├── test_api_endpoints.py    # API integration tests
└── test_run.log            # Test execution logs
```

---

## Setup

### 1. Install Dependencies

```bash
# Install base requirements
pip install -r requirements.txt

# Install development requirements (includes testing tools)
pip install -r requirements-dev.txt
```

### 2. Environment Configuration

Create a test environment file:

```bash
# backend/.env.test
ENVIRONMENT=test
DEBUG=true
DATABASE_URL=postgresql://test:test@localhost:5432/test_db
REDIS_URL=redis://localhost:6379/1
AWS_REGION=us-east-1
OPENAI_API_KEY=test-key-123
SECRET_KEY=test-secret-key-for-jwt-signing
LOG_LEVEL=DEBUG
```

### 3. Test Database Setup

```bash
# Create test database
createdb test_db

# Run migrations
alembic upgrade head
```

---

## Running Tests

### Run All Tests

```bash
# Run all tests with verbose output
pytest

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term-missing

# Run in parallel (faster)
pytest -n auto
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Agent system tests
pytest -m agents

# Skip slow tests
pytest -m "not slow"

# Multiple markers
pytest -m "unit and agents"
```

### Run Specific Test Files

```bash
# Run agent tests
pytest tests/test_agents.py

# Run specific test class
pytest tests/test_agents.py::TestAnalysisAgent

# Run specific test
pytest tests/test_agents.py::TestAnalysisAgent::test_analysis_agent
```

### Run with Different Verbosity

```bash
# Minimal output
pytest -q

# Verbose output
pytest -v

# Extra verbose (show test names as they run)
pytest -vv

# Show local variables on failure
pytest -l
```

---

## Test Categories

### 1. Multi-Agent System Tests (`test_agents.py`)

Tests for the intelligent agent orchestration system.

#### BaseAgent Tests
- Agent initialization and lifecycle
- Metrics tracking (success rate, cost, duration)
- Circuit breaker patterns (open, closed, half-open)
- Error handling and recovery
- Rate limiting

```bash
pytest tests/test_agents.py::TestBaseAgent -v
```

#### Individual Agent Tests
- **AnalysisAgent**: Deep document analysis
- **ActionItemAgent**: Action item extraction
- **SummaryAgent**: Document summarization
- **EntityAgent**: Entity extraction (Comprehend + Claude)
- **QAAgent**: Question answering with RAG

```bash
# Test all agents
pytest tests/test_agents.py::TestAnalysisAgent
pytest tests/test_agents.py::TestActionItemAgent
pytest tests/test_agents.py::TestSummaryAgent
pytest tests/test_agents.py::TestEntityAgent
pytest tests/test_agents.py::TestQAAgent
```

#### Orchestrator Tests
- Agent registration and routing
- Task type mapping
- Multi-agent workflows (parallel/sequential)
- Conversation memory
- Health checks and status

```bash
pytest tests/test_agents.py::TestAgentOrchestrator -v
```

#### Integration Tests
- End-to-end multi-agent workflows
- Parallel execution
- Error propagation
- Cost tracking across agents

```bash
pytest tests/test_agents.py::TestMultiAgentIntegration -v
```

### 2. Document Processing Tests

Tests for the document processing pipeline.

```bash
# Run when implemented
pytest tests/test_document_processing.py -v
```

### 3. Vector Search Tests

Tests for semantic search and embeddings.

```bash
# Run when implemented
pytest tests/test_vector_search.py -v
```

### 4. Authentication Tests

Tests for JWT authentication and user management.

```bash
# Run when implemented
pytest tests/test_auth.py -v
```

### 5. API Endpoint Tests

Tests for all API routes and rate limiting.

```bash
# Run when implemented
pytest tests/test_api_endpoints.py -v
```

---

## Coverage

### Generate Coverage Reports

```bash
# HTML report (opens in browser)
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Terminal report
pytest --cov=app --cov-report=term-missing

# XML report (for CI/CD)
pytest --cov=app --cov-report=xml
```

### Coverage Targets

| Component | Target | Current |
|-----------|--------|---------|
| Multi-Agent System | 90% | TBD |
| Document Processing | 85% | TBD |
| Vector Search | 85% | TBD |
| Authentication | 95% | TBD |
| API Endpoints | 90% | TBD |
| **Overall** | **85%** | **TBD** |

---

## Writing Tests

### Test Structure Template

```python
"""Test module description."""

import pytest
from unittest.mock import AsyncMock, Mock, patch


class TestYourComponent:
    """Test class for YourComponent."""

    @pytest.fixture
    def sample_data(self):
        """Fixture for test data."""
        return {"key": "value"}

    @pytest.mark.asyncio
    async def test_async_function(self, sample_data):
        """Test async function."""
        # Arrange
        expected_result = "success"

        # Act
        result = await your_async_function(sample_data)

        # Assert
        assert result == expected_result

    def test_sync_function(self):
        """Test synchronous function."""
        # Arrange
        input_data = "test"

        # Act
        result = your_sync_function(input_data)

        # Assert
        assert result is not None
```

### Using Fixtures

All shared fixtures are in `conftest.py`:

```python
def test_with_fixtures(
    mock_bedrock_service,
    mock_vector_search,
    sample_user,
    sample_document
):
    """Test using multiple fixtures."""
    # Fixtures are automatically injected
    assert sample_user["id"] is not None
```

### Mocking AWS Services

```python
@patch('app.agents.analysis_agent.BedrockService')
async def test_with_mocked_bedrock(mock_bedrock):
    """Test with mocked Bedrock."""
    # Configure mock
    mock_instance = mock_bedrock.return_value
    mock_instance.invoke_claude = AsyncMock(return_value={
        "text": "Test response",
        "cost": 0.001
    })

    # Run test
    result = await your_function()

    # Assert
    assert result is not None
    mock_instance.invoke_claude.assert_called_once()
```

### Testing Error Handling

```python
def test_error_handling():
    """Test that errors are handled correctly."""
    with pytest.raises(ValidationError) as exc_info:
        your_function_that_raises()

    assert "expected error message" in str(exc_info.value)
```

---

## Best Practices

### 1. Test Naming

- **Test files**: `test_*.py`
- **Test classes**: `Test*`
- **Test functions**: `test_*`
- Use descriptive names: `test_agent_executes_successfully_with_valid_input`

### 2. Test Organization

- One test file per module
- Group related tests in classes
- Use fixtures for common setup
- Keep tests independent

### 3. Async Testing

Always use `@pytest.mark.asyncio` for async tests:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### 4. Mocking

- Mock external services (AWS, OpenAI, databases)
- Use `AsyncMock` for async functions
- Verify mock calls when important
- Don't mock the code you're testing

### 5. Assertions

- Use specific assertions: `assert x == y` not `assert x`
- Use pytest helpers: `pytest.approx()`, `pytest.raises()`
- Test both success and failure cases
- Verify side effects (DB writes, API calls)

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests
        run: |
          pytest --cov=app --cov-report=xml --cov-report=term-missing

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true
```

---

## Troubleshooting

### Common Issues

#### 1. Async Tests Not Running

**Problem**: `RuntimeWarning: coroutine was never awaited`

**Solution**: Add `@pytest.mark.asyncio` decorator

```python
@pytest.mark.asyncio
async def test_my_async_function():
    ...
```

#### 2. Import Errors

**Problem**: `ModuleNotFoundError: No module named 'app'`

**Solution**: Install package in editable mode

```bash
pip install -e .
```

#### 3. Database Connection Errors

**Problem**: Tests fail with database connection errors

**Solution**: Check test database is running and accessible

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Verify connection
psql -h localhost -U test -d test_db
```

#### 4. Redis Connection Errors

**Problem**: Tests fail with Redis connection errors

**Solution**: Start Redis service

```bash
# Start Redis
docker-compose up -d redis

# Verify connection
redis-cli ping
```

#### 5. Slow Tests

**Problem**: Tests take too long to run

**Solution**: Run in parallel

```bash
pytest -n auto
```

---

## Performance Testing

### Benchmark Tests

Use `pytest-benchmark` for performance testing:

```python
def test_agent_performance(benchmark):
    """Benchmark agent execution time."""
    result = benchmark(run_agent_task)
    assert result is not None
```

### Load Testing

Use `locust` for load testing API endpoints:

```bash
# Start load test
locust -f tests/load_test.py --host=http://localhost:8000
```

---

## Continuous Improvement

### Adding New Tests

1. **Identify Gap**: Check coverage report for untested code
2. **Write Test**: Follow templates and best practices
3. **Run Locally**: Verify test passes
4. **Update Docs**: Document new test if needed
5. **Submit PR**: Include tests with code changes

### Code Review Checklist

- [ ] All new code has tests
- [ ] Tests cover happy path and error cases
- [ ] Tests are independent and isolated
- [ ] Mocks are used for external services
- [ ] Test names are descriptive
- [ ] Coverage meets minimum threshold
- [ ] Tests pass in CI/CD

---

## Resources

### Documentation

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

### Internal Docs

- [Multi-Agent System](./MULTI_AGENT_SYSTEM.md)
- [Document Processing](./DOCUMENT_PROCESSING.md)
- [Vector Search](./VECTOR_SEARCH.md)
- [Architecture Overview](./ARCHITECTURE.md)

---

## Support

For questions or issues with testing:

1. Check this guide
2. Review test examples in `tests/`
3. Consult team documentation
4. Ask in team chat

---

**Happy Testing!** 🧪
