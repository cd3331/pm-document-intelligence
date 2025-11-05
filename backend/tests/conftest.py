"""
Pytest configuration and shared fixtures for all tests.

This module provides common fixtures and configuration for the test suite.
"""

import asyncio
import os
import pytest
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "true"


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# ============================================================================
# Event Loop Fixture
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Mock Services
# ============================================================================

@pytest.fixture
def mock_bedrock_service():
    """Mock BedrockService for testing."""
    mock = Mock()
    mock.invoke_claude = AsyncMock(return_value={
        "text": '{"result": "success"}',
        "cost": 0.001,
        "tokens": {"input": 100, "output": 50}
    })
    return mock


@pytest.fixture
def mock_comprehend_service():
    """Mock ComprehendService for testing."""
    mock = Mock()
    mock.analyze_document_entities = AsyncMock(return_value={
        "entities": [
            {"text": "Test Entity", "type": "PERSON", "score": 0.95}
        ],
        "cost": 0.0001
    })
    return mock


@pytest.fixture
def mock_vector_search():
    """Mock VectorSearch for testing."""
    mock = Mock()
    mock.semantic_search = AsyncMock(return_value={
        "results": [
            {
                "document_id": "doc_test",
                "filename": "test.pdf",
                "matched_chunk": {
                    "text": "Test context",
                    "chunk_index": 0
                },
                "similarity_score": 0.85
            }
        ],
        "total_results": 1
    })
    return mock


@pytest.fixture
def mock_embedding_service():
    """Mock EmbeddingService for testing."""
    mock = Mock()
    mock.generate_embeddings = AsyncMock(return_value={
        "embeddings": [[0.1] * 1536],  # Mock 1536-dim embedding
        "chunks": ["Test chunk"],
        "cost": 0.0001,
        "model": "text-embedding-3-small"
    })
    return mock


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_user():
    """Sample user for testing."""
    return {
        "id": "user_test_123",
        "email": "test@example.com",
        "username": "testuser",
        "is_active": True,
        "role": "user"
    }


@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return {
        "id": "doc_test_123",
        "user_id": "user_test_123",
        "filename": "test_document.pdf",
        "file_size": 1024,
        "document_type": "meeting_notes",
        "extracted_text": "This is a test document with some content.",
        "processing_status": "completed",
        "created_at": "2024-12-15T10:00:00Z",
    }


@pytest.fixture
def sample_analysis_result():
    """Sample analysis result for testing."""
    return {
        "document_id": "doc_test_123",
        "analysis": {
            "executive_summary": "Test document analysis",
            "key_insights": [
                "Insight 1",
                "Insight 2"
            ],
            "patterns_identified": [
                "Pattern 1"
            ],
            "recommendations": [
                {
                    "recommendation": "Test recommendation",
                    "priority": "MEDIUM",
                    "rationale": "Test rationale"
                }
            ],
            "risks_and_concerns": [],
            "opportunities": [],
            "confidence_score": 0.85
        },
        "cost": 0.003
    }


@pytest.fixture
def sample_action_items():
    """Sample action items for testing."""
    return [
        {
            "action": "Complete testing",
            "assignee": "John Doe",
            "due_date": "2024-12-31",
            "priority": "HIGH",
            "status": "TODO",
            "dependencies": [],
            "confidence": 0.9
        },
        {
            "action": "Review documentation",
            "assignee": "Jane Smith",
            "due_date": "2025-01-15",
            "priority": "MEDIUM",
            "status": "IN_PROGRESS",
            "dependencies": ["Complete testing"],
            "confidence": 0.85
        }
    ]


@pytest.fixture
def sample_summary():
    """Sample summary for testing."""
    return {
        "executive_summary": "Brief summary of the document",
        "key_points": [
            "Point 1",
            "Point 2",
            "Point 3"
        ],
        "decisions": [
            "Decision 1"
        ],
        "next_steps": [
            "Step 1",
            "Step 2"
        ],
        "concerns": [
            "Concern 1"
        ]
    }


# ============================================================================
# Database Fixtures (if needed)
# ============================================================================

@pytest.fixture
async def db_session():
    """
    Mock database session for testing.

    In a real implementation, this would create a test database
    and provide a session for testing.
    """
    # Mock session
    mock_session = AsyncMock()
    yield mock_session
    # Cleanup would happen here


# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest.fixture
def api_client():
    """
    Mock API client for testing endpoints.

    In a real implementation, this would use FastAPI TestClient.
    """
    from fastapi.testclient import TestClient
    # Would import app here
    # client = TestClient(app)
    # return client
    return Mock()


# ============================================================================
# Environment Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up test environment variables."""
    test_env = {
        "ENVIRONMENT": "test",
        "DEBUG": "true",
        "DATABASE_URL": "postgresql://test:test@localhost:5432/test_db",
        "REDIS_URL": "redis://localhost:6379/1",
        "AWS_REGION": "us-east-1",
        "OPENAI_API_KEY": "test-key-123",
        "SECRET_KEY": "test-secret-key-for-jwt-signing",
        "LOG_LEVEL": "DEBUG",
    }

    for key, value in test_env.items():
        monkeypatch.setenv(key, value)


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
async def cleanup():
    """Clean up after each test."""
    yield
    # Cleanup code here
    # e.g., clear caches, reset mocks, etc.


# ============================================================================
# Performance Testing Fixtures
# ============================================================================

@pytest.fixture
def performance_timer():
    """Timer for performance testing."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()

        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return Timer()
