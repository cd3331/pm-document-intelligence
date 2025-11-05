# PM Document Intelligence - Testing Suite

Comprehensive testing suite with unit, integration, E2E, and load tests.

## Overview

This testing suite provides complete coverage of the PM Document Intelligence application with:
- **Unit Tests**: Fast, isolated tests for individual components
- **Integration Tests**: Tests for component interactions and API endpoints
- **E2E Tests**: Full user journey tests using Playwright
- **Load Tests**: Performance and stress testing using Locust
- **CI/CD**: Automated testing with GitHub Actions

## Test Structure

```
tests/
├── conftest.py                          # Shared fixtures and mocks
├── unit/
│   ├── test_auth.py                     # Authentication tests
│   ├── test_document_processor.py       # Document processing tests
│   ├── test_agents.py                   # AI agent tests
│   └── test_vector_search.py            # Vector search tests
├── integration/
│   ├── test_document_flow.py            # End-to-end document flow
│   └── test_api_endpoints.py            # API endpoint tests
├── e2e/
│   └── test_user_journey.py             # Playwright E2E tests
└── load/
    └── test_performance.py              # Locust load tests
```

## Requirements

### Install Testing Dependencies

```bash
# Core testing dependencies
pip install pytest pytest-cov pytest-asyncio pytest-mock pytest-xdist

# E2E testing
pip install pytest-playwright
playwright install chromium

# Load testing
pip install locust

# Code quality tools
pip install black ruff mypy bandit safety
```

## Running Tests

### Quick Start

```bash
# Run all unit tests (fast)
pytest -m unit

# Run all tests except slow ones
pytest -m "not slow and not e2e"

# Run with coverage report
pytest --cov=app --cov-report=html
```

### Unit Tests

```bash
# Run all unit tests
pytest -m unit

# Run specific test file
pytest tests/unit/test_auth.py

# Run specific test class
pytest tests/unit/test_auth.py::TestPasswordHashing

# Run specific test
pytest tests/unit/test_auth.py::TestPasswordHashing::test_hash_password

# Run in parallel (faster)
pytest -m unit -n auto
```

### Integration Tests

```bash
# Run all integration tests
pytest -m integration

# Run without slow tests
pytest -m "integration and not slow"

# Run with database
pytest -m database
```

### E2E Tests

```bash
# Run all E2E tests
pytest -m e2e

# Run with headed browser (see what's happening)
pytest -m e2e --headed

# Run with video recording
pytest -m e2e --video=on

# Run specific test
pytest tests/e2e/test_user_journey.py::TestUserRegistrationAndLogin
```

### Load Tests

```bash
# Run Locust with web UI
locust -f tests/load/test_performance.py --host=http://localhost:8000

# Open browser to http://localhost:8089 to configure and start test

# Run headless (automated)
locust -f tests/load/test_performance.py \
  --host=http://localhost:8000 \
  --headless \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --html=report.html
```

## Test Markers

Tests are categorized using pytest markers:

- `unit`: Fast unit tests
- `integration`: Integration tests
- `e2e`: End-to-end browser tests
- `slow`: Tests taking > 5 seconds
- `aws`: Tests requiring AWS services
- `database`: Tests requiring database
- `visual`: Visual regression tests

### Examples

```bash
# Run only unit tests
pytest -m unit

# Run unit and integration tests
pytest -m "unit or integration"

# Run all except slow tests
pytest -m "not slow"

# Run AWS-dependent tests
pytest -m aws
```

## Coverage

### Generate Coverage Reports

```bash
# Terminal report
pytest --cov=app --cov-report=term-missing

# HTML report (open htmlcov/index.html)
pytest --cov=app --cov-report=html

# XML report (for CI/CD)
pytest --cov=app --cov-report=xml

# Enforce minimum coverage (80%)
pytest --cov=app --cov-fail-under=80
```

## CI/CD

The GitHub Actions workflow (`.github/workflows/test.yml`) automatically:

1. **Linting**: Runs Black, Ruff, and MyPy
2. **Security**: Runs Bandit and Safety checks
3. **Tests**: Runs unit and integration tests on Python 3.11 and 3.12
4. **E2E**: Runs Playwright tests
5. **Performance**: Runs Locust load tests
6. **Coverage**: Uploads to Codecov
7. **Deploy**: Deploys to staging on main branch

### Triggering CI

```bash
# Push to main or develop branch
git push origin main

# Create pull request
gh pr create --base main
```

## Test Data

### Mock Services

The `conftest.py` provides mocks for:
- AWS Services (S3, Textract, Comprehend, Bedrock)
- OpenAI API
- Supabase
- PubNub

### Sample Files

Create `tests/fixtures/` directory with sample files:

```bash
mkdir -p tests/fixtures
# Add sample.pdf, sample.txt, sample.docx
```

## Best Practices

### Writing Tests

1. **Use fixtures**: Leverage `conftest.py` fixtures for setup
2. **Mark appropriately**: Add correct markers (`@pytest.mark.unit`)
3. **Mock external services**: Don't make real API calls in unit tests
4. **Test isolation**: Each test should be independent
5. **Descriptive names**: Test names should explain what they test

### Example Test

```python
import pytest
from app.auth import hash_password, verify_password

@pytest.mark.unit
def test_password_verification():
    """Test password hashing and verification"""
    password = "secure123"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True
    assert verify_password("wrong", hashed) is False
```

## Debugging Tests

```bash
# Stop on first failure
pytest -x

# Show print statements
pytest -s

# Verbose output
pytest -vv

# Show slowest tests
pytest --durations=10

# Run failed tests from last run
pytest --lf

# Run last failed, then all
pytest --ff

# Enter debugger on failure
pytest --pdb
```

## Performance Testing

### Locust Scenarios

The load tests include multiple user types:
- `DocumentIntelligenceUser`: Regular user workflow
- `AdminUser`: Administrative operations
- `ApiOnlyUser`: API-only clients
- `SpikeLoadTest`: Sudden traffic spikes
- `SteadyStateTest`: Long-running steady load

### Performance Metrics

Locust tracks:
- Response times (avg, min, max, percentiles)
- Requests per second
- Failure rates
- Concurrent users

### Identifying Bottlenecks

The performance tests automatically identify:
- Endpoints with avg response time > 1000ms
- High failure rates
- Resource exhaustion

## Continuous Improvement

### Coverage Goals

- Minimum: 80% overall coverage
- Target: 90% coverage for critical paths
- Unit tests: 95%+ coverage

### Test Maintenance

- Review and update tests monthly
- Remove flaky tests
- Add tests for new features
- Keep test data current

## Troubleshooting

### Common Issues

**Tests hang or timeout**:
```bash
# Increase timeout
pytest --timeout=600
```

**Database locked errors**:
```bash
# Use in-memory database (already default in conftest.py)
```

**AWS service errors**:
```bash
# Ensure mocks are properly configured in conftest.py
# Or use LocalStack for local AWS emulation
```

**E2E tests fail**:
```bash
# Ensure Playwright browsers are installed
playwright install chromium

# Check if app is running
curl http://localhost:8000/health
```

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Playwright Documentation](https://playwright.dev/python/)
- [Locust Documentation](https://docs.locust.io/)
- [Codecov](https://about.codecov.io/)

## Support

For issues with tests:
1. Check test logs: `pytest.log`
2. Run with verbose output: `pytest -vv`
3. Review GitHub Actions logs
4. Open an issue with test output

---

**Test Coverage Goal**: 80%+
**Test Execution Time**: < 5 minutes (unit + integration)
**E2E Tests**: Run on push to main
**Load Tests**: Run weekly and before releases
