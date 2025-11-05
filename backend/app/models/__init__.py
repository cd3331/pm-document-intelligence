"""
Data Models for PM Document Intelligence.

This module provides Pydantic models for all entities in the system
including users, documents, and analysis results.

Available Models:
    User Models:
        - User: User for API responses
        - UserCreate: User creation request
        - UserUpdate: User update request
        - UserInDB: User as stored in database
        - Token: JWT token response
        - UserRole: Role enumeration
        - UserPreferences: User preferences

    Document Models:
        - Document: Document for API responses
        - DocumentCreate: Document creation request
        - DocumentUpdate: Document update request
        - DocumentInDB: Document as stored in database
        - DocumentStatus: Status enumeration
        - DocumentType: File type enumeration
        - ProcessingStage: Processing stage enumeration

    Analysis Models:
        - Analysis: Analysis for API responses
        - AnalysisCreate: Analysis creation request
        - AnalysisInDB: Analysis as stored in database
        - EntityExtraction: Extracted entity
        - ActionItemDetail: Action item with metadata
        - SentimentAnalysis: Sentiment analysis results
        - Topic: Identified topic
        - RiskIndicator: Risk indicator

Usage:
    from app.models import User, Document, Analysis
    from app.models.user import create_access_token, verify_password
    from app.models.document import DocumentStatus
    from app.models.analysis import EntityType, RiskLevel
"""

# User models
from app.models.user import (
    User,
    UserBase,
    UserCreate,
    UserUpdate,
    UserInDB,
    Token,
    TokenData,
    UserRole,
    UserPreferences,
    PermissionLevel,
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    create_token_pair,
    has_permission,
    sanitize_user_response,
)

# Document models
from app.models.document import (
    Document,
    DocumentBase,
    DocumentCreate,
    DocumentUpdate,
    DocumentInDB,
    DocumentDetail,
    DocumentStatus,
    DocumentType,
    ProcessingStage,
    ExtractedEntity,
    ActionItem,
    SentimentScore,
    S3Reference,
    VectorEmbedding,
    ProcessingError,
    DocumentStats,
    is_supported_file_type,
    get_file_extension,
    sanitize_document_response,
)

# Analysis models
from app.models.analysis import (
    Analysis,
    AnalysisBase,
    AnalysisCreate,
    AnalysisInDB,
    AnalysisDetail,
    EntityType,
    ActionPriority,
    RiskLevel,
    SentimentType,
    EntityExtraction,
    EntitySummary,
    ActionItemDetail,
    SentimentAnalysis,
    Topic,
    KeyPhrase,
    RiskIndicator,
    AnalysisStats,
    calculate_overall_confidence,
    determine_overall_risk_level,
    sanitize_analysis_response,
)


__all__ = [
    # User models
    "User",
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserInDB",
    "Token",
    "TokenData",
    "UserRole",
    "UserPreferences",
    "PermissionLevel",
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "create_token_pair",
    "has_permission",
    "sanitize_user_response",
    # Document models
    "Document",
    "DocumentBase",
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentInDB",
    "DocumentDetail",
    "DocumentStatus",
    "DocumentType",
    "ProcessingStage",
    "ExtractedEntity",
    "ActionItem",
    "SentimentScore",
    "S3Reference",
    "VectorEmbedding",
    "ProcessingError",
    "DocumentStats",
    "is_supported_file_type",
    "get_file_extension",
    "sanitize_document_response",
    # Analysis models
    "Analysis",
    "AnalysisBase",
    "AnalysisCreate",
    "AnalysisInDB",
    "AnalysisDetail",
    "EntityType",
    "ActionPriority",
    "RiskLevel",
    "SentimentType",
    "EntityExtraction",
    "EntitySummary",
    "ActionItemDetail",
    "SentimentAnalysis",
    "Topic",
    "KeyPhrase",
    "RiskIndicator",
    "AnalysisStats",
    "calculate_overall_confidence",
    "determine_overall_risk_level",
    "sanitize_analysis_response",
]
