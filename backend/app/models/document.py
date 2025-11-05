"""
Document Models for PM Document Intelligence.

This module provides document models for managing uploaded documents,
their processing status, extracted content, and metadata.

Features:
- Document metadata tracking
- Processing status management
- Extracted content storage
- S3 object references
- Vector embeddings tracking
- Error handling and logging

Usage:
    from app.models.document import Document, DocumentCreate

    # Create document
    document = DocumentCreate(
        user_id=user_id,
        filename="report.pdf",
        file_type="application/pdf",
        size=1024000
    )
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Enums
# ============================================================================


class DocumentStatus(str, Enum):
    """Document processing status."""

    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


class DocumentType(str, Enum):
    """Document file types."""

    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    DOC = "application/msword"
    TXT = "text/plain"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    XLS = "application/vnd.ms-excel"
    PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    PPT = "application/vnd.ms-powerpoint"
    CSV = "text/csv"
    MD = "text/markdown"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


class ProcessingStage(str, Enum):
    """Document processing stages."""

    UPLOAD = "upload"
    OCR = "ocr"
    EXTRACTION = "extraction"
    ANALYSIS = "analysis"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETE = "complete"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


# ============================================================================
# Document Content Models
# ============================================================================


class ExtractedEntity(BaseModel):
    """Extracted entity from document."""

    type: str = Field(..., description="Entity type (person, organization, location, etc.)")
    text: str = Field(..., description="Entity text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    start_offset: int | None = Field(None, description="Start character offset")
    end_offset: int | None = Field(None, description="End character offset")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "type": "PERSON",
                "text": "John Doe",
                "confidence": 0.95,
                "start_offset": 0,
                "end_offset": 8,
            }
        }


class ActionItem(BaseModel):
    """Action item extracted from document."""

    text: str = Field(..., description="Action item text")
    priority: str = Field(default="medium", description="Priority level")
    assignee: str | None = Field(None, description="Assigned person")
    due_date: datetime | None = Field(None, description="Due date")
    status: str = Field(default="pending", description="Action item status")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "text": "Review quarterly budget report",
                "priority": "high",
                "assignee": "Jane Smith",
                "due_date": "2024-01-31T00:00:00Z",
                "status": "pending",
                "confidence": 0.88,
            }
        }


class SentimentScore(BaseModel):
    """Sentiment analysis scores."""

    positive: float = Field(..., ge=0.0, le=1.0, description="Positive sentiment score")
    negative: float = Field(..., ge=0.0, le=1.0, description="Negative sentiment score")
    neutral: float = Field(..., ge=0.0, le=1.0, description="Neutral sentiment score")
    mixed: float = Field(..., ge=0.0, le=1.0, description="Mixed sentiment score")
    overall: str = Field(..., description="Overall sentiment (positive/negative/neutral/mixed)")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "positive": 0.75,
                "negative": 0.10,
                "neutral": 0.10,
                "mixed": 0.05,
                "overall": "positive",
            }
        }


class S3Reference(BaseModel):
    """S3 object reference."""

    bucket: str = Field(..., description="S3 bucket name")
    key: str = Field(..., description="S3 object key")
    version_id: str | None = Field(None, description="S3 object version ID")
    etag: str | None = Field(None, description="S3 object ETag")
    size: int | None = Field(None, description="Object size in bytes")
    url: str | None = Field(None, description="Presigned URL")
    expires_at: datetime | None = Field(None, description="URL expiration time")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "bucket": "pm-document-intelligence",
                "key": "documents/user123/report.pdf",
                "version_id": "abc123",
                "etag": '"d41d8cd98f00b204e9800998ecf8427e"',
                "size": 1024000,
            }
        }


class VectorEmbedding(BaseModel):
    """Vector embedding reference."""

    model: str = Field(..., description="Embedding model used")
    dimension: int = Field(..., description="Embedding dimension")
    chunk_count: int = Field(default=0, description="Number of text chunks embedded")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "model": "text-embedding-3-small",
                "dimension": 1536,
                "chunk_count": 42,
                "metadata": {"chunking_strategy": "recursive"},
            }
        }


class ProcessingError(BaseModel):
    """Processing error information."""

    stage: ProcessingStage = Field(..., description="Processing stage where error occurred")
    error_type: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: dict[str, Any] = Field(default_factory=dict, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    retryable: bool = Field(default=False, description="Whether error is retryable")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "stage": "ocr",
                "error_type": "TextractError",
                "message": "OCR processing failed",
                "details": {"reason": "Unsupported file format"},
                "timestamp": "2024-01-15T10:30:00Z",
                "retryable": True,
            }
        }


# ============================================================================
# Document Models
# ============================================================================


class DocumentBase(BaseModel):
    """Base document model."""

    filename: str = Field(..., min_length=1, max_length=255, description="Original filename")
    file_type: str = Field(..., description="MIME type of the file")
    size: int = Field(..., gt=0, description="File size in bytes")
    description: str | None = Field(None, max_length=1000, description="Document description")
    tags: list[str] = Field(default_factory=list, description="Document tags")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Validate filename."""
        if not v.strip():
            raise ValueError("Filename cannot be empty")

        # Check for potentially dangerous characters
        dangerous_chars = ["../", "..\\", "<", ">", "|", ":", "*", "?", '"']
        if any(char in v for char in dangerous_chars):
            raise ValueError("Filename contains invalid characters")

        return v.strip()

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate and normalize tags."""
        # Remove duplicates and normalize
        unique_tags = list({tag.lower().strip() for tag in v if tag.strip()})
        return unique_tags[:50]  # Limit to 50 tags


class DocumentCreate(DocumentBase):
    """Model for creating a new document."""

    user_id: str = Field(..., description="User ID who uploaded the document")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "quarterly_report.pdf",
                "file_type": "application/pdf",
                "size": 1024000,
                "description": "Q4 2023 Financial Report",
                "tags": ["finance", "quarterly", "2023"],
            }
        }


class DocumentUpdate(BaseModel):
    """Model for updating document metadata."""

    description: str | None = Field(None, max_length=1000)
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None
    status: DocumentStatus | None = None

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "description": "Updated Q4 2023 Financial Report",
                "tags": ["finance", "quarterly", "2023", "final"],
                "status": "completed",
            }
        }


class DocumentInDB(DocumentBase):
    """Document model as stored in database."""

    id: str = Field(..., description="Document ID (UUID)")
    user_id: str = Field(..., description="User ID who uploaded the document")
    status: DocumentStatus = Field(
        default=DocumentStatus.UPLOADED,
        description="Processing status",
    )
    current_stage: ProcessingStage | None = Field(
        None,
        description="Current processing stage",
    )

    # Extracted content
    extracted_text: str | None = Field(None, description="Extracted text content")
    entities: list[ExtractedEntity] = Field(
        default_factory=list,
        description="Extracted entities",
    )
    action_items: list[ActionItem] = Field(
        default_factory=list,
        description="Extracted action items",
    )
    sentiment: SentimentScore | None = Field(None, description="Sentiment analysis")
    key_phrases: list[str] = Field(default_factory=list, description="Key phrases")
    summary: str | None = Field(None, description="Document summary")

    # Storage references
    s3_reference: S3Reference | None = Field(None, description="S3 storage reference")
    vector_embedding: VectorEmbedding | None = Field(
        None,
        description="Vector embedding reference",
    )

    # Processing metadata
    processing_started_at: datetime | None = Field(
        None,
        description="Processing start time",
    )
    processing_completed_at: datetime | None = Field(
        None,
        description="Processing completion time",
    )
    processing_duration_seconds: float | None = Field(
        None,
        description="Processing duration in seconds",
    )
    ai_models_used: list[str] = Field(
        default_factory=list,
        description="AI models used for processing",
    )

    # Error tracking
    errors: list[ProcessingError] = Field(
        default_factory=list,
        description="Processing errors",
    )
    retry_count: int = Field(default=0, description="Number of retry attempts")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    accessed_at: datetime | None = Field(None, description="Last access timestamp")

    # Page count for multi-page documents
    page_count: int | None = Field(None, description="Number of pages")

    # Character and word counts
    character_count: int | None = Field(None, description="Character count")
    word_count: int | None = Field(None, description="Word count")

    class Config:
        """Pydantic configuration."""

        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "doc_123456",
                "user_id": "user_789",
                "filename": "project_plan.pdf",
                "file_type": "application/pdf",
                "size": 2048000,
                "status": "completed",
                "current_stage": "complete",
                "extracted_text": "Project plan for Q1 2024...",
                "page_count": 15,
                "word_count": 5000,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }


class Document(DocumentBase):
    """Document model for API responses."""

    id: str = Field(..., description="Document ID (UUID)")
    user_id: str = Field(..., description="User ID who uploaded the document")
    status: DocumentStatus = Field(..., description="Processing status")
    current_stage: ProcessingStage | None = Field(None, description="Current processing stage")

    # Summary information (not full content)
    has_extracted_text: bool = Field(default=False, description="Whether text was extracted")
    entity_count: int = Field(default=0, description="Number of extracted entities")
    action_item_count: int = Field(default=0, description="Number of action items")
    has_sentiment: bool = Field(default=False, description="Whether sentiment was analyzed")

    # Storage info
    s3_reference: S3Reference | None = None

    # Processing info
    processing_completed_at: datetime | None = None
    processing_duration_seconds: float | None = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    # Page and word counts
    page_count: int | None = None
    word_count: int | None = None

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class DocumentDetail(DocumentInDB):
    """Detailed document model with full content (for authorized access)."""

    pass


# ============================================================================
# Document Statistics
# ============================================================================


class DocumentStats(BaseModel):
    """Document statistics."""

    total_documents: int = Field(..., description="Total number of documents")
    by_status: dict[str, int] = Field(..., description="Document count by status")
    by_type: dict[str, int] = Field(..., description="Document count by type")
    total_size_bytes: int = Field(..., description="Total size of all documents")
    average_processing_time: float = Field(..., description="Average processing time in seconds")
    total_entities: int = Field(..., description="Total extracted entities")
    total_action_items: int = Field(..., description="Total action items")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "total_documents": 150,
                "by_status": {
                    "completed": 120,
                    "processing": 15,
                    "failed": 10,
                    "uploaded": 5,
                },
                "by_type": {
                    "application/pdf": 100,
                    "application/docx": 40,
                    "text/plain": 10,
                },
                "total_size_bytes": 524288000,
                "average_processing_time": 45.5,
                "total_entities": 3500,
                "total_action_items": 450,
            }
        }


# ============================================================================
# Helper Functions
# ============================================================================


def calculate_processing_duration(
    started_at: datetime,
    completed_at: datetime,
) -> float:
    """
    Calculate processing duration in seconds.

    Args:
        started_at: Processing start time
        completed_at: Processing completion time

    Returns:
        Duration in seconds
    """
    delta = completed_at - started_at
    return delta.total_seconds()


def is_supported_file_type(mime_type: str) -> bool:
    """
    Check if file type is supported.

    Args:
        mime_type: MIME type to check

    Returns:
        True if supported, False otherwise
    """
    try:
        DocumentType(mime_type)
        return True
    except ValueError:
        return False


def get_file_extension(filename: str) -> str:
    """
    Get file extension from filename.

    Args:
        filename: Filename

    Returns:
        File extension (without dot)
    """
    parts = filename.rsplit(".", 1)
    if len(parts) > 1:
        return parts[1].lower()
    return ""


def sanitize_document_response(doc: DocumentInDB) -> Document:
    """
    Convert DocumentInDB to Document (summary version).

    Args:
        doc: Document from database

    Returns:
        Document for API response
    """
    return Document(
        id=doc.id,
        user_id=doc.user_id,
        filename=doc.filename,
        file_type=doc.file_type,
        size=doc.size,
        description=doc.description,
        tags=doc.tags,
        metadata=doc.metadata,
        status=doc.status,
        current_stage=doc.current_stage,
        has_extracted_text=bool(doc.extracted_text),
        entity_count=len(doc.entities),
        action_item_count=len(doc.action_items),
        has_sentiment=doc.sentiment is not None,
        s3_reference=doc.s3_reference,
        processing_completed_at=doc.processing_completed_at,
        processing_duration_seconds=doc.processing_duration_seconds,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        page_count=doc.page_count,
        word_count=doc.word_count,
    )
