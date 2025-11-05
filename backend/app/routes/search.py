"""
Search API Routes for PM Document Intelligence.

This module provides semantic and hybrid search endpoints using
OpenAI embeddings and pgvector.

Features:
- Semantic search with natural language queries
- Hybrid search combining vector + keyword search
- Similar document recommendations
- Search suggestions and auto-complete
- Rate limiting and caching

Usage:
    GET /api/search/semantic?query=find%20project%20risks
    GET /api/search/similar/{document_id}
    GET /api/search/suggestions?q=project
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status, Request
from pydantic import BaseModel, Field, validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models import UserInDB
from app.services.vector_search import VectorSearch
from app.utils.auth_helpers import get_current_active_user
from app.utils.exceptions import ValidationError, AIServiceError
from app.utils.logger import get_logger


logger = get_logger(__name__)

# Initialize router
router = APIRouter(prefix="/api/search", tags=["search"])

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize vector search service
vector_search = VectorSearch()


# ============================================================================
# Request/Response Models
# ============================================================================

class SemanticSearchRequest(BaseModel):
    """Semantic search request."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural language search query"
    )
    document_type: Optional[str] = Field(
        None,
        description="Filter by document type"
    )
    date_from: Optional[datetime] = Field(
        None,
        description="Filter by date range start"
    )
    date_to: Optional[datetime] = Field(
        None,
        description="Filter by date range end"
    )
    similarity_threshold: Optional[float] = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score (0-1)"
    )
    limit: int = Field(
        10,
        ge=1,
        le=50,
        description="Maximum number of results"
    )

    @validator("query")
    def validate_query(cls, v):
        """Validate query string."""
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


class SearchResult(BaseModel):
    """Single search result."""

    document_id: str
    filename: str
    document_type: str
    similarity_score: float
    created_at: Optional[str]
    word_count: Optional[int]
    matched_chunk: Dict[str, Any]


class SemanticSearchResponse(BaseModel):
    """Semantic search response."""

    query: str
    results: List[SearchResult]
    total_results: int
    similarity_threshold: float
    duration_seconds: float
    embedding_cost: float


class HybridSearchRequest(BaseModel):
    """Hybrid search request."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query"
    )
    document_type: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    vector_weight: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="Weight for vector similarity"
    )
    keyword_weight: float = Field(
        0.3,
        ge=0.0,
        le=1.0,
        description="Weight for keyword matching"
    )
    limit: int = Field(10, ge=1, le=50)


class HybridSearchResult(BaseModel):
    """Hybrid search result."""

    document_id: str
    filename: str
    document_type: str
    combined_score: float
    vector_score: float
    keyword_score: float
    created_at: Optional[str]
    word_count: Optional[int]
    matched_chunk: Optional[str]


class HybridSearchResponse(BaseModel):
    """Hybrid search response."""

    query: str
    results: List[HybridSearchResult]
    total_results: int
    vector_weight: float
    keyword_weight: float
    embedding_cost: float


class SimilarDocument(BaseModel):
    """Similar document."""

    document_id: str
    filename: str
    document_type: str
    similarity_score: float
    created_at: Optional[str]
    word_count: Optional[int]


class SimilarDocumentsResponse(BaseModel):
    """Similar documents response."""

    document_id: str
    results: List[SimilarDocument]
    total_results: int
    similarity_threshold: float


class SearchSuggestionsResponse(BaseModel):
    """Search suggestions response."""

    partial_query: str
    suggestions: List[str]


class SearchStatsResponse(BaseModel):
    """Search statistics response."""

    total_documents: int
    total_embeddings: int
    avg_tokens_per_chunk: float
    total_tokens: int


# ============================================================================
# Search Endpoints
# ============================================================================

@router.get(
    "/semantic",
    response_model=SemanticSearchResponse,
    summary="Semantic search",
    description="Perform semantic search using natural language queries"
)
@limiter.limit("30/minute")
async def semantic_search(
    request: Request,
    query: str = Query(..., description="Search query", min_length=1, max_length=500),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    date_from: Optional[datetime] = Query(None, description="Filter by date range start"),
    date_to: Optional[datetime] = Query(None, description="Filter by date range end"),
    similarity_threshold: float = Query(0.7, ge=0.0, le=1.0, description="Minimum similarity"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    current_user: UserInDB = Depends(get_current_active_user),
):
    """
    Perform semantic search on documents using natural language queries.

    This endpoint uses OpenAI embeddings and pgvector for fast similarity search.

    **Rate Limit:** 30 requests per minute

    **Example:**
    ```
    GET /api/search/semantic?query=find all project risks&limit=10
    ```
    """
    try:
        logger.info(f"Semantic search: '{query}' by user {current_user.id}")

        # Perform search
        result = await vector_search.semantic_search(
            query=query,
            user_id=current_user.id,
            document_type=document_type,
            date_from=date_from,
            date_to=date_to,
            similarity_threshold=similarity_threshold,
            limit=limit,
            use_cache=True,
        )

        return result

    except AIServiceError as e:
        logger.error(f"Semantic search failed: {e}")
        raise

    except Exception as e:
        logger.error(f"Unexpected search error: {e}", exc_info=True)
        raise AIServiceError(
            message="Search failed",
            details={"error": str(e)}
        )


@router.post(
    "/semantic",
    response_model=SemanticSearchResponse,
    summary="Semantic search (POST)",
    description="Perform semantic search with advanced options"
)
@limiter.limit("30/minute")
async def semantic_search_post(
    request: Request,
    search_request: SemanticSearchRequest,
    current_user: UserInDB = Depends(get_current_active_user),
):
    """
    Perform semantic search on documents (POST version for complex queries).

    **Rate Limit:** 30 requests per minute

    **Example:**
    ```json
    POST /api/search/semantic
    {
        "query": "find project risks and blockers",
        "document_type": "project_plan",
        "similarity_threshold": 0.75,
        "limit": 20
    }
    ```
    """
    try:
        logger.info(f"Semantic search (POST): '{search_request.query}' by user {current_user.id}")

        result = await vector_search.semantic_search(
            query=search_request.query,
            user_id=current_user.id,
            document_type=search_request.document_type,
            date_from=search_request.date_from,
            date_to=search_request.date_to,
            similarity_threshold=search_request.similarity_threshold,
            limit=search_request.limit,
            use_cache=True,
        )

        return result

    except AIServiceError as e:
        logger.error(f"Semantic search failed: {e}")
        raise


@router.post(
    "/hybrid",
    response_model=HybridSearchResponse,
    summary="Hybrid search",
    description="Combine vector similarity with keyword search"
)
@limiter.limit("30/minute")
async def hybrid_search(
    request: Request,
    search_request: HybridSearchRequest,
    current_user: UserInDB = Depends(get_current_active_user),
):
    """
    Perform hybrid search combining vector similarity and keyword matching.

    This provides better results for queries that benefit from both semantic
    understanding and exact keyword matches.

    **Rate Limit:** 30 requests per minute

    **Example:**
    ```json
    POST /api/search/hybrid
    {
        "query": "budget overrun Q4",
        "vector_weight": 0.6,
        "keyword_weight": 0.4,
        "limit": 10
    }
    ```
    """
    try:
        logger.info(f"Hybrid search: '{search_request.query}' by user {current_user.id}")

        result = await vector_search.hybrid_search(
            query=search_request.query,
            user_id=current_user.id,
            document_type=search_request.document_type,
            date_from=search_request.date_from,
            date_to=search_request.date_to,
            vector_weight=search_request.vector_weight,
            keyword_weight=search_request.keyword_weight,
            limit=search_request.limit,
        )

        return result

    except AIServiceError as e:
        logger.error(f"Hybrid search failed: {e}")
        raise


@router.get(
    "/similar/{document_id}",
    response_model=SimilarDocumentsResponse,
    summary="Find similar documents",
    description="Find documents similar to a given document"
)
@limiter.limit("60/minute")
async def find_similar_documents(
    request: Request,
    document_id: str,
    similarity_threshold: float = Query(0.75, ge=0.0, le=1.0),
    limit: int = Query(5, ge=1, le=20),
    current_user: UserInDB = Depends(get_current_active_user),
):
    """
    Find documents similar to a given document.

    Useful for document recommendations and finding related content.

    **Rate Limit:** 60 requests per minute

    **Example:**
    ```
    GET /api/search/similar/doc_123?limit=5
    ```
    """
    try:
        logger.info(f"Finding similar documents to {document_id} by user {current_user.id}")

        result = await vector_search.find_similar_documents(
            document_id=document_id,
            user_id=current_user.id,
            similarity_threshold=similarity_threshold,
            limit=limit,
        )

        return result

    except AIServiceError as e:
        logger.error(f"Find similar failed: {e}")
        raise


@router.get(
    "/suggestions",
    response_model=SearchSuggestionsResponse,
    summary="Search suggestions",
    description="Get search query suggestions"
)
@limiter.limit("60/minute")
async def get_search_suggestions(
    request: Request,
    q: str = Query(..., description="Partial query", min_length=1, max_length=100),
    limit: int = Query(5, ge=1, le=10),
    current_user: UserInDB = Depends(get_current_active_user),
):
    """
    Get search query suggestions based on document content.

    Useful for auto-complete and search assistance.

    **Rate Limit:** 60 requests per minute

    **Example:**
    ```
    GET /api/search/suggestions?q=project&limit=5
    ```
    """
    try:
        logger.info(f"Getting search suggestions for '{q}' by user {current_user.id}")

        suggestions = await vector_search.get_search_suggestions(
            partial_query=q,
            user_id=current_user.id,
            limit=limit,
        )

        return {
            "partial_query": q,
            "suggestions": suggestions,
        }

    except Exception as e:
        logger.error(f"Get suggestions failed: {e}")
        # Return empty suggestions on error
        return {
            "partial_query": q,
            "suggestions": [],
        }


@router.get(
    "/stats",
    response_model=SearchStatsResponse,
    summary="Search statistics",
    description="Get search and embedding statistics"
)
async def get_search_stats(
    current_user: UserInDB = Depends(get_current_active_user),
):
    """
    Get search statistics for the current user.

    Shows number of documents with embeddings, total embeddings, and token usage.

    **Example:**
    ```
    GET /api/search/stats
    ```
    """
    try:
        logger.info(f"Getting search stats for user {current_user.id}")

        stats = await vector_search.get_search_stats(user_id=current_user.id)

        return stats

    except Exception as e:
        logger.error(f"Get stats failed: {e}")
        return {
            "total_documents": 0,
            "total_embeddings": 0,
            "avg_tokens_per_chunk": 0,
            "total_tokens": 0,
        }


# ============================================================================
# Health Check
# ============================================================================

@router.get(
    "/health",
    summary="Search service health check",
    description="Check if search service is operational"
)
async def search_health():
    """
    Health check endpoint for search service.

    Returns status of vector search components.
    """
    try:
        # Test embedding service
        embedding_service_ok = True
        try:
            await vector_search.embedding_service.generate_embedding(
                "test",
                use_cache=False
            )
        except Exception as e:
            logger.error(f"Embedding service health check failed: {e}")
            embedding_service_ok = False

        # Test database
        db_ok = True
        try:
            stats = await vector_search.get_search_stats()
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            db_ok = False

        overall_ok = embedding_service_ok and db_ok

        return {
            "status": "healthy" if overall_ok else "degraded",
            "components": {
                "embedding_service": "ok" if embedding_service_ok else "error",
                "database": "ok" if db_ok else "error",
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
