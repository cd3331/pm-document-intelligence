"""
Test fixtures and configuration for PM Document Intelligence test suite
Provides mock AWS services, test database, sample data, and authenticated clients
"""

import pytest
import os
import tempfile
import json
from datetime import datetime, timedelta
from typing import Generator, Dict, Any
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Import app components
from app.main import app
from app.database import Base, get_db
from app.models import User, Document, ActionItem
from app.auth import create_access_token, hash_password
from app.config import get_settings


# ============================================================================
# Environment Setup
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def set_test_environment():
    """Set environment variables for testing"""
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-do-not-use-in-production"
    os.environ["AWS_ACCESS_KEY_ID"] = "test-aws-key"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "test-aws-secret"
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["OPENAI_API_KEY"] = "test-openai-key"
    os.environ["SUPABASE_URL"] = "https://test.supabase.co"
    os.environ["SUPABASE_KEY"] = "test-supabase-key"
    os.environ["PUBNUB_PUBLISH_KEY"] = "test-pubnub-pub"
    os.environ["PUBNUB_SUBSCRIBE_KEY"] = "test-pubnub-sub"
    os.environ["PUBNUB_SECRET_KEY"] = "test-pubnub-secret"
    yield
    # Cleanup after all tests
    for key in list(os.environ.keys()):
        if key.startswith("TEST_"):
            del os.environ[key]


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """
    Create a fresh test database for each test
    Uses in-memory SQLite for speed
    """
    # Create in-memory SQLite database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session factory
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create session
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db: Session) -> Generator[TestClient, None, None]:
    """
    Create a test client with database override
    """
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def test_user(test_db: Session) -> User:
    """Create a test user"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("testpassword123"),
        is_active=True,
        is_admin=False,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def admin_user(test_db: Session) -> User:
    """Create an admin test user"""
    user = User(
        username="adminuser",
        email="admin@example.com",
        hashed_password=hash_password("adminpassword123"),
        is_active=True,
        is_admin=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_token(test_user: User) -> str:
    """Generate JWT token for test user"""
    return create_access_token(
        data={"sub": test_user.username, "user_id": test_user.id}
    )


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Generate JWT token for admin user"""
    return create_access_token(
        data={"sub": admin_user.username, "user_id": admin_user.id}
    )


@pytest.fixture
def auth_headers(test_token: str) -> Dict[str, str]:
    """Generate authorization headers"""
    return {"Authorization": f"Bearer {test_token}"}


@pytest.fixture
def admin_headers(admin_token: str) -> Dict[str, str]:
    """Generate admin authorization headers"""
    return {"Authorization": f"Bearer {admin_token}"}


# ============================================================================
# Document Fixtures
# ============================================================================

@pytest.fixture
def sample_pdf_file() -> Generator[Path, None, None]:
    """Create a sample PDF file"""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        # Write minimal PDF content
        f.write(b"%PDF-1.4\n")
        f.write(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        f.write(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
        f.write(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents 4 0 R >>\nendobj\n")
        f.write(b"4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 100 700 Td (Test Document) Tj ET\nendstream\nendobj\n")
        f.write(b"xref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000270 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n363\n%%EOF\n")
        filepath = Path(f.name)

    yield filepath

    # Cleanup
    filepath.unlink()


@pytest.fixture
def sample_txt_file() -> Generator[Path, None, None]:
    """Create a sample text file"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is a test document.\n")
        f.write("It contains some sample text for testing.\n")
        f.write("Action Item: Complete the testing suite by Friday.\n")
        f.write("Another task: Review documentation.\n")
        filepath = Path(f.name)

    yield filepath

    # Cleanup
    filepath.unlink()


@pytest.fixture
def sample_document(test_db: Session, test_user: User) -> Document:
    """Create a sample document in the database"""
    document = Document(
        filename="test_document.pdf",
        s3_key="documents/test_document.pdf",
        user_id=test_user.id,
        document_type="general",
        status="completed",
        extracted_text="This is extracted text from the test document.",
        metadata={
            "file_size": 1024,
            "page_count": 1,
            "analysis": {
                "summary": "Test document summary",
                "key_insights": ["Insight 1", "Insight 2"],
                "sentiment": "neutral"
            }
        }
    )
    test_db.add(document)
    test_db.commit()
    test_db.refresh(document)
    return document


@pytest.fixture
def sample_action_item(test_db: Session, test_user: User, sample_document: Document) -> ActionItem:
    """Create a sample action item"""
    action_item = ActionItem(
        title="Complete testing suite",
        description="Write comprehensive tests for all components",
        document_id=sample_document.id,
        user_id=test_user.id,
        priority="high",
        status="pending",
        due_date=datetime.utcnow() + timedelta(days=7),
        assignee="testuser"
    )
    test_db.add(action_item)
    test_db.commit()
    test_db.refresh(action_item)
    return action_item


# ============================================================================
# Mock AWS Services
# ============================================================================

@pytest.fixture
def mock_s3_client():
    """Mock AWS S3 client"""
    mock_client = MagicMock()

    # Mock upload_file
    mock_client.upload_file.return_value = None

    # Mock put_object
    mock_client.put_object.return_value = {
        'ETag': '"test-etag"',
        'VersionId': 'test-version'
    }

    # Mock get_object
    mock_client.get_object.return_value = {
        'Body': MagicMock(read=lambda: b'test file content'),
        'ContentLength': 17
    }

    # Mock delete_object
    mock_client.delete_object.return_value = {'DeleteMarker': True}

    # Mock generate_presigned_url
    mock_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/test-bucket/test-key?signature=test"

    return mock_client


@pytest.fixture
def mock_textract_client():
    """Mock AWS Textract client"""
    mock_client = MagicMock()

    # Mock detect_document_text
    mock_client.detect_document_text.return_value = {
        'Blocks': [
            {
                'BlockType': 'LINE',
                'Text': 'This is extracted text from Textract.',
                'Confidence': 99.5
            },
            {
                'BlockType': 'LINE',
                'Text': 'Another line of text.',
                'Confidence': 98.7
            }
        ]
    }

    # Mock analyze_document
    mock_client.analyze_document.return_value = {
        'Blocks': [
            {
                'BlockType': 'KEY_VALUE_SET',
                'EntityTypes': ['KEY'],
                'Relationships': [{'Type': 'VALUE', 'Ids': ['value-1']}]
            }
        ]
    }

    return mock_client


@pytest.fixture
def mock_comprehend_client():
    """Mock AWS Comprehend client"""
    mock_client = MagicMock()

    # Mock detect_entities
    mock_client.detect_entities.return_value = {
        'Entities': [
            {'Type': 'PERSON', 'Text': 'John Doe', 'Score': 0.99},
            {'Type': 'ORGANIZATION', 'Text': 'Acme Corp', 'Score': 0.95},
            {'Type': 'DATE', 'Text': 'Friday', 'Score': 0.98}
        ]
    }

    # Mock detect_sentiment
    mock_client.detect_sentiment.return_value = {
        'Sentiment': 'NEUTRAL',
        'SentimentScore': {
            'Positive': 0.1,
            'Negative': 0.05,
            'Neutral': 0.8,
            'Mixed': 0.05
        }
    }

    # Mock detect_key_phrases
    mock_client.detect_key_phrases.return_value = {
        'KeyPhrases': [
            {'Text': 'test document', 'Score': 0.99},
            {'Text': 'comprehensive testing', 'Score': 0.97}
        ]
    }

    return mock_client


@pytest.fixture
def mock_bedrock_runtime_client():
    """Mock AWS Bedrock Runtime client"""
    mock_client = MagicMock()

    # Mock invoke_model
    def mock_invoke_model(**kwargs):
        model_id = kwargs.get('modelId', '')

        if 'claude' in model_id.lower():
            response_body = {
                'content': [
                    {
                        'type': 'text',
                        'text': 'This is a mock response from Claude.'
                    }
                ],
                'usage': {
                    'input_tokens': 100,
                    'output_tokens': 50
                }
            }
        else:
            response_body = {
                'completion': 'Mock LLM response',
                'usage': {
                    'prompt_tokens': 100,
                    'completion_tokens': 50
                }
            }

        return {
            'body': MagicMock(read=lambda: json.dumps(response_body).encode()),
            'contentType': 'application/json'
        }

    mock_client.invoke_model.side_effect = mock_invoke_model

    return mock_client


@pytest.fixture
def mock_aws_services(mock_s3_client, mock_textract_client, mock_comprehend_client, mock_bedrock_runtime_client):
    """Patch all AWS services"""
    with patch('boto3.client') as mock_boto_client:
        def get_client(service_name, **kwargs):
            if service_name == 's3':
                return mock_s3_client
            elif service_name == 'textract':
                return mock_textract_client
            elif service_name == 'comprehend':
                return mock_comprehend_client
            elif service_name == 'bedrock-runtime':
                return mock_bedrock_runtime_client
            else:
                return MagicMock()

        mock_boto_client.side_effect = get_client
        yield {
            's3': mock_s3_client,
            'textract': mock_textract_client,
            'comprehend': mock_comprehend_client,
            'bedrock': mock_bedrock_runtime_client
        }


# ============================================================================
# Mock External Services
# ============================================================================

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    with patch('openai.OpenAI') as mock_client:
        # Mock embeddings
        mock_embeddings = MagicMock()
        mock_embeddings.create.return_value = MagicMock(
            data=[
                MagicMock(embedding=[0.1] * 1536)
            ]
        )

        # Mock chat completions
        mock_chat = MagicMock()
        mock_chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(content="Mock OpenAI response"),
                    finish_reason="stop"
                )
            ],
            usage=MagicMock(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150
            )
        )

        mock_instance = MagicMock()
        mock_instance.embeddings = mock_embeddings
        mock_instance.chat = mock_chat
        mock_client.return_value = mock_instance

        yield mock_instance


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client"""
    mock_client = MagicMock()

    # Mock table operations
    mock_table = MagicMock()
    mock_table.insert.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = MagicMock(
        data=[{'id': 1, 'content': 'test'}],
        error=None
    )

    mock_client.table.return_value = mock_table

    # Mock storage operations
    mock_storage = MagicMock()
    mock_storage.upload.return_value = {'path': 'test/path'}
    mock_storage.download.return_value = b'test content'
    mock_client.storage.from_.return_value = mock_storage

    return mock_client


@pytest.fixture
def mock_pubnub_client():
    """Mock PubNub client"""
    mock_client = MagicMock()

    # Mock publish
    mock_client.publish.return_value = MagicMock(
        timetoken=16234567890000000
    )

    # Mock subscribe
    mock_client.subscribe.return_value = None

    # Mock unsubscribe
    mock_client.unsubscribe.return_value = None

    # Mock history
    mock_client.history.return_value = MagicMock(
        messages=[
            {'message': {'type': 'test', 'data': 'test message'}}
        ]
    )

    return mock_client


# ============================================================================
# Test Data Generators
# ============================================================================

@pytest.fixture
def generate_users(test_db: Session):
    """Generate multiple test users"""
    def _generate(count: int = 5):
        users = []
        for i in range(count):
            user = User(
                username=f"user{i}",
                email=f"user{i}@example.com",
                hashed_password=hash_password(f"password{i}"),
                is_active=True,
                is_admin=False
            )
            test_db.add(user)
            users.append(user)
        test_db.commit()
        return users
    return _generate


@pytest.fixture
def generate_documents(test_db: Session, test_user: User):
    """Generate multiple test documents"""
    def _generate(count: int = 10, user: User = None):
        if user is None:
            user = test_user

        documents = []
        for i in range(count):
            doc = Document(
                filename=f"document_{i}.pdf",
                s3_key=f"documents/document_{i}.pdf",
                user_id=user.id,
                document_type="general",
                status="completed" if i % 2 == 0 else "processing",
                extracted_text=f"This is document {i} text content.",
                metadata={
                    "file_size": 1024 * (i + 1),
                    "page_count": i + 1
                }
            )
            test_db.add(doc)
            documents.append(doc)
        test_db.commit()
        return documents
    return _generate


# ============================================================================
# Performance Testing Fixtures
# ============================================================================

@pytest.fixture
def benchmark_timer():
    """Simple benchmark timer"""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.elapsed = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            if self.start_time:
                self.elapsed = time.time() - self.start_time
                return self.elapsed
            return None

        def __enter__(self):
            self.start()
            return self

        def __exit__(self, *args):
            self.stop()

    return Timer()


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Cleanup temporary files after each test"""
    yield
    # Cleanup any leftover temp files
    temp_dir = Path(tempfile.gettempdir())
    for file in temp_dir.glob("test_*"):
        try:
            if file.is_file():
                file.unlink()
        except Exception:
            pass


# ============================================================================
# Pytest Configuration Helpers
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow-running tests")
    config.addinivalue_line("markers", "aws: Tests requiring AWS services")
    config.addinivalue_line("markers", "database: Tests requiring database")
