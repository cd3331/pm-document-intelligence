"""
Analysis Results Models for PM Document Intelligence.

This module provides models for storing and managing AI analysis results
including entity extraction, action items, sentiment analysis, topics,
and risk indicators.

Features:
- Entity extraction results
- Action item tracking
- Sentiment analysis
- Topic and theme identification
- Risk indicators
- Confidence scores
- Model version tracking

Usage:
    from app.models.analysis import Analysis, AnalysisCreate

    # Create analysis
    analysis = AnalysisCreate(
        document_id=doc_id,
        entities=extracted_entities,
        action_items=action_items
    )
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.utils.logger import get_logger


logger = get_logger(__name__)


# ============================================================================
# Enums
# ============================================================================


class EntityType(str, Enum):
    """Types of entities that can be extracted."""

    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    DATE = "date"
    TIME = "time"
    MONEY = "money"
    PERCENTAGE = "percentage"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    METRIC = "metric"
    PRODUCT = "product"
    EVENT = "event"
    OTHER = "other"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


class ActionPriority(str, Enum):
    """Action item priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


class RiskLevel(str, Enum):
    """Risk indicator levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


class SentimentType(str, Enum):
    """Sentiment types."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


# ============================================================================
# Entity Models
# ============================================================================


class EntityExtraction(BaseModel):
    """Extracted entity with metadata."""

    type: EntityType = Field(..., description="Entity type")
    text: str = Field(..., description="Entity text")
    normalized_text: Optional[str] = Field(None, description="Normalized entity text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    start_offset: int = Field(..., description="Start character offset in document")
    end_offset: int = Field(..., description="End character offset in document")
    page_number: Optional[int] = Field(
        None, description="Page number where entity appears"
    )
    context: Optional[str] = Field(
        None, max_length=500, description="Surrounding context"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "type": "person",
                "text": "John Doe",
                "normalized_text": "JOHN DOE",
                "confidence": 0.95,
                "start_offset": 150,
                "end_offset": 158,
                "page_number": 1,
                "context": "...project manager John Doe will oversee...",
                "metadata": {"title": "Project Manager"},
            }
        }


class EntitySummary(BaseModel):
    """Summary of entities by type."""

    entity_type: EntityType = Field(..., description="Entity type")
    count: int = Field(..., description="Number of entities of this type")
    unique_values: List[str] = Field(..., description="Unique entity values")
    most_common: Optional[str] = Field(
        None, description="Most frequently mentioned entity"
    )
    frequency: Dict[str, int] = Field(
        default_factory=dict,
        description="Frequency count for each entity",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "entity_type": "person",
                "count": 15,
                "unique_values": ["John Doe", "Jane Smith", "Bob Wilson"],
                "most_common": "John Doe",
                "frequency": {"John Doe": 8, "Jane Smith": 4, "Bob Wilson": 3},
            }
        }


# ============================================================================
# Action Item Models
# ============================================================================


class ActionItemDetail(BaseModel):
    """Detailed action item with all metadata."""

    text: str = Field(..., max_length=1000, description="Action item description")
    priority: ActionPriority = Field(
        default=ActionPriority.MEDIUM,
        description="Priority level",
    )
    assignee: Optional[str] = Field(None, description="Assigned person or team")
    due_date: Optional[datetime] = Field(None, description="Due date")
    status: str = Field(
        default="pending", description="Status (pending, in_progress, completed)"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    page_number: Optional[int] = Field(
        None, description="Page number where action appears"
    )
    context: Optional[str] = Field(
        None, max_length=500, description="Surrounding context"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Dependencies (other action items)",
    )
    tags: List[str] = Field(default_factory=list, description="Action item tags")
    estimated_effort: Optional[str] = Field(
        None, description="Estimated effort (hours/days)"
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate and normalize tags."""
        return list(set(tag.lower().strip() for tag in v if tag.strip()))[:20]

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "text": "Complete budget analysis by end of quarter",
                "priority": "high",
                "assignee": "Finance Team",
                "due_date": "2024-03-31T23:59:59Z",
                "status": "pending",
                "confidence": 0.92,
                "page_number": 5,
                "context": "...Q1 objectives include complete budget analysis...",
                "tags": ["finance", "q1", "budget"],
                "estimated_effort": "3 days",
            }
        }


# ============================================================================
# Sentiment Analysis Models
# ============================================================================


class SentimentAnalysis(BaseModel):
    """Detailed sentiment analysis."""

    overall_sentiment: SentimentType = Field(
        ..., description="Overall document sentiment"
    )
    positive_score: float = Field(
        ..., ge=0.0, le=1.0, description="Positive sentiment score"
    )
    negative_score: float = Field(
        ..., ge=0.0, le=1.0, description="Negative sentiment score"
    )
    neutral_score: float = Field(
        ..., ge=0.0, le=1.0, description="Neutral sentiment score"
    )
    mixed_score: float = Field(..., ge=0.0, le=1.0, description="Mixed sentiment score")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")

    # Sentiment by section
    section_sentiments: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Sentiment scores by document section",
    )

    # Key phrases by sentiment
    positive_phrases: List[str] = Field(
        default_factory=list,
        description="Positive key phrases",
    )
    negative_phrases: List[str] = Field(
        default_factory=list,
        description="Negative key phrases",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "overall_sentiment": "positive",
                "positive_score": 0.75,
                "negative_score": 0.10,
                "neutral_score": 0.10,
                "mixed_score": 0.05,
                "confidence": 0.88,
                "positive_phrases": ["excellent progress", "ahead of schedule"],
                "negative_phrases": ["budget concerns", "delayed delivery"],
            }
        }


# ============================================================================
# Topic and Theme Models
# ============================================================================


class Topic(BaseModel):
    """Identified topic or theme."""

    name: str = Field(..., description="Topic name")
    keywords: List[str] = Field(..., description="Topic keywords")
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Topic relevance score"
    )
    mentions: int = Field(..., description="Number of mentions")
    page_numbers: List[int] = Field(
        default_factory=list,
        description="Pages where topic appears",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "name": "Budget Planning",
                "keywords": ["budget", "financial", "allocation", "resources"],
                "relevance_score": 0.85,
                "mentions": 12,
                "page_numbers": [1, 3, 5, 7],
            }
        }


class KeyPhrase(BaseModel):
    """Key phrase with importance score."""

    text: str = Field(..., description="Key phrase text")
    importance_score: float = Field(..., ge=0.0, le=1.0, description="Importance score")
    frequency: int = Field(..., description="Frequency count")
    category: Optional[str] = Field(None, description="Phrase category")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "text": "project timeline",
                "importance_score": 0.92,
                "frequency": 8,
                "category": "planning",
            }
        }


# ============================================================================
# Risk Indicator Models
# ============================================================================


class RiskIndicator(BaseModel):
    """Risk indicator identified in document."""

    category: str = Field(
        ..., description="Risk category (budget, timeline, resource, etc.)"
    )
    description: str = Field(..., description="Risk description")
    level: RiskLevel = Field(..., description="Risk level")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    evidence: List[str] = Field(..., description="Evidence supporting this risk")
    page_numbers: List[int] = Field(
        default_factory=list,
        description="Pages where risk is mentioned",
    )
    mitigation_suggestions: List[str] = Field(
        default_factory=list,
        description="Suggested mitigation strategies",
    )
    impact: Optional[str] = Field(None, description="Potential impact description")
    likelihood: Optional[str] = Field(None, description="Likelihood assessment")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "category": "timeline",
                "description": "Project may miss Q1 deadline",
                "level": "high",
                "confidence": 0.87,
                "evidence": [
                    "Multiple delays mentioned",
                    "Resource constraints identified",
                ],
                "page_numbers": [2, 5, 8],
                "mitigation_suggestions": [
                    "Increase team resources",
                    "Adjust scope or timeline",
                ],
                "impact": "Revenue impact of $500K",
                "likelihood": "high",
            }
        }


# ============================================================================
# Analysis Models
# ============================================================================


class AnalysisBase(BaseModel):
    """Base analysis model."""

    document_id: str = Field(..., description="Document ID being analyzed")
    ai_models_used: List[str] = Field(..., description="AI models used for analysis")
    processing_duration_seconds: float = Field(..., description="Processing duration")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "document_id": "doc_123456",
                "ai_models_used": [
                    "anthropic.claude-3-5-sonnet-20241022-v2:0",
                    "text-embedding-3-small",
                ],
                "processing_duration_seconds": 45.5,
            }
        }


class AnalysisCreate(AnalysisBase):
    """Model for creating new analysis."""

    entities: List[EntityExtraction] = Field(default_factory=list)
    action_items: List[ActionItemDetail] = Field(default_factory=list)
    sentiment: Optional[SentimentAnalysis] = None
    topics: List[Topic] = Field(default_factory=list)
    key_phrases: List[KeyPhrase] = Field(default_factory=list)
    risks: List[RiskIndicator] = Field(default_factory=list)


class AnalysisInDB(AnalysisBase):
    """Analysis model as stored in database."""

    id: str = Field(..., description="Analysis ID (UUID)")
    user_id: str = Field(..., description="User ID who owns the document")

    # Entity extraction
    entities: List[EntityExtraction] = Field(default_factory=list)
    entity_summary: List[EntitySummary] = Field(default_factory=list)
    total_entities: int = Field(default=0, description="Total number of entities")

    # Action items
    action_items: List[ActionItemDetail] = Field(default_factory=list)
    action_items_by_priority: Dict[str, int] = Field(
        default_factory=dict,
        description="Action item count by priority",
    )

    # Sentiment
    sentiment: Optional[SentimentAnalysis] = None

    # Topics and themes
    topics: List[Topic] = Field(default_factory=list)
    key_phrases: List[KeyPhrase] = Field(default_factory=list)
    top_keywords: List[str] = Field(
        default_factory=list, description="Most important keywords"
    )

    # Risk indicators
    risks: List[RiskIndicator] = Field(default_factory=list)
    overall_risk_level: RiskLevel = Field(default=RiskLevel.NONE)

    # Confidence scores
    overall_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall analysis confidence",
    )
    entity_extraction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    action_item_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    sentiment_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # Model versions
    bedrock_model_version: Optional[str] = None
    comprehend_model_version: Optional[str] = None
    textract_model_version: Optional[str] = None
    openai_model_version: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(..., description="Analysis creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class Analysis(AnalysisBase):
    """Analysis model for API responses."""

    id: str = Field(..., description="Analysis ID (UUID)")
    user_id: str = Field(..., description="User ID")

    # Summary statistics
    total_entities: int = Field(default=0)
    total_action_items: int = Field(default=0)
    total_risks: int = Field(default=0)
    total_topics: int = Field(default=0)

    # High-level results
    overall_sentiment: Optional[SentimentType] = None
    overall_risk_level: RiskLevel = Field(default=RiskLevel.NONE)
    overall_confidence: float = Field(default=0.0)

    # Top results
    top_entities: List[EntityExtraction] = Field(default_factory=list)
    top_action_items: List[ActionItemDetail] = Field(default_factory=list)
    top_topics: List[Topic] = Field(default_factory=list)
    top_risks: List[RiskIndicator] = Field(default_factory=list)

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class AnalysisDetail(AnalysisInDB):
    """Detailed analysis with full results."""

    pass


# ============================================================================
# Analysis Statistics
# ============================================================================


class AnalysisStats(BaseModel):
    """Statistics across multiple analyses."""

    total_analyses: int = Field(..., description="Total number of analyses")
    total_entities: int = Field(..., description="Total entities extracted")
    total_action_items: int = Field(..., description="Total action items")
    total_risks: int = Field(..., description="Total risks identified")

    # Average scores
    average_confidence: float = Field(..., description="Average confidence score")
    average_processing_time: float = Field(
        ..., description="Average processing time in seconds"
    )

    # Sentiment distribution
    sentiment_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Document count by sentiment",
    )

    # Risk distribution
    risk_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Risk count by level",
    )

    # Most common entities
    most_common_entities: Dict[str, int] = Field(
        default_factory=dict,
        description="Most frequently mentioned entities",
    )

    # Most common topics
    most_common_topics: List[str] = Field(
        default_factory=list,
        description="Most common topics across documents",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "total_analyses": 100,
                "total_entities": 5000,
                "total_action_items": 800,
                "total_risks": 150,
                "average_confidence": 0.87,
                "average_processing_time": 42.3,
                "sentiment_distribution": {
                    "positive": 60,
                    "neutral": 30,
                    "negative": 10,
                },
                "risk_distribution": {
                    "high": 30,
                    "medium": 70,
                    "low": 50,
                },
            }
        }


# ============================================================================
# Helper Functions
# ============================================================================


def calculate_overall_confidence(analysis: AnalysisInDB) -> float:
    """
    Calculate overall confidence score for analysis.

    Args:
        analysis: Analysis object

    Returns:
        Overall confidence score (0.0-1.0)
    """
    confidence_scores = []

    if analysis.entity_extraction_confidence > 0:
        confidence_scores.append(analysis.entity_extraction_confidence)

    if analysis.action_item_confidence > 0:
        confidence_scores.append(analysis.action_item_confidence)

    if analysis.sentiment_confidence > 0:
        confidence_scores.append(analysis.sentiment_confidence)

    if confidence_scores:
        return sum(confidence_scores) / len(confidence_scores)

    return 0.0


def determine_overall_risk_level(risks: List[RiskIndicator]) -> RiskLevel:
    """
    Determine overall risk level from individual risks.

    Args:
        risks: List of risk indicators

    Returns:
        Overall risk level
    """
    if not risks:
        return RiskLevel.NONE

    # Priority: CRITICAL > HIGH > MEDIUM > LOW
    for risk in risks:
        if risk.level == RiskLevel.CRITICAL:
            return RiskLevel.CRITICAL

    for risk in risks:
        if risk.level == RiskLevel.HIGH:
            return RiskLevel.HIGH

    for risk in risks:
        if risk.level == RiskLevel.MEDIUM:
            return RiskLevel.MEDIUM

    return RiskLevel.LOW


def sanitize_analysis_response(
    analysis: AnalysisInDB, limit_results: int = 10
) -> Analysis:
    """
    Convert AnalysisInDB to Analysis (summary version).

    Args:
        analysis: Analysis from database
        limit_results: Number of top results to include

    Returns:
        Analysis for API response
    """
    # Sort entities by confidence
    top_entities = sorted(
        analysis.entities,
        key=lambda x: x.confidence,
        reverse=True,
    )[:limit_results]

    # Sort action items by priority and confidence
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    top_action_items = sorted(
        analysis.action_items,
        key=lambda x: (priority_order.get(x.priority.value, 4), -x.confidence),
    )[:limit_results]

    # Sort topics by relevance
    top_topics = sorted(
        analysis.topics,
        key=lambda x: x.relevance_score,
        reverse=True,
    )[:limit_results]

    # Sort risks by level and confidence
    risk_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 4}
    top_risks = sorted(
        analysis.risks,
        key=lambda x: (risk_order.get(x.level.value, 5), -x.confidence),
    )[:limit_results]

    return Analysis(
        id=analysis.id,
        user_id=analysis.user_id,
        document_id=analysis.document_id,
        ai_models_used=analysis.ai_models_used,
        processing_duration_seconds=analysis.processing_duration_seconds,
        total_entities=analysis.total_entities,
        total_action_items=len(analysis.action_items),
        total_risks=len(analysis.risks),
        total_topics=len(analysis.topics),
        overall_sentiment=(
            analysis.sentiment.overall_sentiment if analysis.sentiment else None
        ),
        overall_risk_level=analysis.overall_risk_level,
        overall_confidence=analysis.overall_confidence,
        top_entities=top_entities,
        top_action_items=top_action_items,
        top_topics=top_topics,
        top_risks=top_risks,
        created_at=analysis.created_at,
        updated_at=analysis.updated_at,
    )
