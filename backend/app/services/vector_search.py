"""
Vector Search Service for PM Document Intelligence.

This module provides semantic search capabilities using OpenAI embeddings
and Supabase pgvector for fast similarity search.

Features:
- Store document embeddings in pgvector
- Semantic search with cosine similarity
- Hybrid search (vector + keyword)
- Document recommendations
- Configurable similarity thresholds
- User-based filtering

Usage:
    from app.services.vector_search import VectorSearch

    vector_search = VectorSearch()
    results = await vector_search.semantic_search(
        query="Find all project risks",
        user_id="user_123",
        limit=10
    )
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.database import execute_insert, execute_select, execute_query, execute_update
from app.services.embedding_service import EmbeddingService
from app.cache.redis import get_cache, set_cache
from app.utils.exceptions import AIServiceError, DatabaseError
from app.utils.logger import get_logger


logger = get_logger(__name__)


# ============================================================================
# Vector Search Service
# ============================================================================


class VectorSearch:
    """Vector search service with pgvector."""

    def __init__(self):
        """Initialize vector search service."""
        self.embedding_service = EmbeddingService()

        # Default search parameters
        self.default_limit = 10
        self.default_similarity_threshold = 0.7

        logger.info("Vector search service initialized")

    async def store_document_embeddings(
        self,
        document_id: str,
        embeddings: List[Dict[str, Any]],
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Store document embeddings in database.

        Args:
            document_id: Document ID
            embeddings: List of embedding dictionaries from embedding_service
            user_id: User ID
            metadata: Additional metadata

        Returns:
            Number of embeddings stored
        """
        try:
            stored_count = 0

            for embedding_data in embeddings:
                # Prepare embedding record
                embedding_record = {
                    "document_id": document_id,
                    "user_id": user_id,
                    "embedding": embedding_data[
                        "embedding"
                    ],  # pgvector will handle this
                    "chunk_index": embedding_data["chunk_index"],
                    "chunk_text": embedding_data["chunk_text"],
                    "tokens": embedding_data["tokens"],
                    "start_char": embedding_data["start_char"],
                    "end_char": embedding_data["end_char"],
                    "model": embeddings[0].get("model", "text-embedding-3-small"),
                    "dimensions": len(embedding_data["embedding"]),
                    "metadata": metadata or {},
                }

                # Insert into database
                await execute_insert("embeddings", embedding_record)
                stored_count += 1

            logger.info(f"Stored {stored_count} embeddings for document {document_id}")

            return stored_count

        except Exception as e:
            logger.error(f"Failed to store embeddings: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to store embeddings",
                details={"document_id": document_id, "error": str(e)},
            )

    async def semantic_search(
        self,
        query: str,
        user_id: Optional[str] = None,
        document_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        similarity_threshold: Optional[float] = None,
        limit: int = 10,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Perform semantic search on documents.

        Args:
            query: Search query text
            user_id: Filter by user ID
            document_type: Filter by document type
            date_from: Filter by date range start
            date_to: Filter by date range end
            similarity_threshold: Minimum similarity score (0-1)
            limit: Maximum number of results
            use_cache: Whether to cache results

        Returns:
            Search results with scores and metadata
        """
        try:
            start_time = datetime.utcnow()

            # Check cache
            if use_cache:
                cache_key = self._generate_search_cache_key(
                    query, user_id, document_type, date_from, date_to, limit
                )
                cached = await get_cache(cache_key)

                if cached:
                    logger.info("Search cache hit")
                    return cached

            # Generate query embedding
            logger.info(f"Generating query embedding for: {query[:50]}...")

            query_result = await self.embedding_service.generate_query_embedding(
                query, use_cache=True
            )

            query_embedding = query_result["embedding"]

            # Set similarity threshold
            threshold = similarity_threshold or self.default_similarity_threshold

            # Build SQL query
            # Using cosine similarity: 1 - (embedding <=> query_embedding)
            sql = """
            SELECT
                e.id,
                e.document_id,
                e.user_id,
                e.chunk_text,
                e.chunk_index,
                e.start_char,
                e.end_char,
                d.filename,
                d.document_type,
                d.created_at,
                d.word_count,
                1 - (e.embedding <=> %s::vector) AS similarity_score
            FROM embeddings e
            INNER JOIN documents d ON e.document_id = d.id
            WHERE 1=1
            """

            params = [query_embedding]

            # Add filters
            if user_id:
                sql += " AND e.user_id = %s"
                params.append(user_id)

            if document_type:
                sql += " AND d.document_type = %s"
                params.append(document_type)

            if date_from:
                sql += " AND d.created_at >= %s"
                params.append(date_from)

            if date_to:
                sql += " AND d.created_at <= %s"
                params.append(date_to)

            # Add similarity threshold
            sql += f" AND (1 - (e.embedding <=> %s::vector)) >= %s"
            params.append(query_embedding)
            params.append(threshold)

            # Order by similarity and limit
            sql += " ORDER BY similarity_score DESC LIMIT %s"
            params.append(limit)

            # Execute query
            results = await execute_query(sql, tuple(params))

            # Process results
            search_results = []
            seen_documents = set()

            for row in results:
                # Group by document (take highest scoring chunk per document)
                doc_id = row["document_id"]

                if doc_id not in seen_documents:
                    seen_documents.add(doc_id)

                    search_results.append(
                        {
                            "document_id": doc_id,
                            "filename": row["filename"],
                            "document_type": row["document_type"],
                            "similarity_score": float(row["similarity_score"]),
                            "created_at": (
                                row["created_at"].isoformat()
                                if row["created_at"]
                                else None
                            ),
                            "word_count": row["word_count"],
                            "matched_chunk": {
                                "text": row["chunk_text"],
                                "chunk_index": row["chunk_index"],
                                "start_char": row["start_char"],
                                "end_char": row["end_char"],
                            },
                        }
                    )

            duration = (datetime.utcnow() - start_time).total_seconds()

            result = {
                "query": query,
                "results": search_results,
                "total_results": len(search_results),
                "similarity_threshold": threshold,
                "duration_seconds": duration,
                "embedding_cost": query_result["cost"],
            }

            # Cache results
            if use_cache and results:
                await set_cache(
                    cache_key,
                    result,
                    ttl=300,  # Cache for 5 minutes
                )

            logger.info(
                f"Semantic search: {len(search_results)} results, {duration:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Semantic search failed: {e}", exc_info=True)
            raise AIServiceError(
                message="Semantic search failed",
                details={"query": query, "error": str(e)},
            )

    async def hybrid_search(
        self,
        query: str,
        user_id: Optional[str] = None,
        document_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Perform hybrid search combining vector and keyword search.

        Args:
            query: Search query text
            user_id: Filter by user ID
            document_type: Filter by document type
            date_from: Filter by date range start
            date_to: Filter by date range end
            vector_weight: Weight for vector similarity (0-1)
            keyword_weight: Weight for keyword matching (0-1)
            limit: Maximum number of results

        Returns:
            Search results with combined scores
        """
        try:
            logger.info(f"Hybrid search for: {query}")

            # Normalize weights
            total_weight = vector_weight + keyword_weight
            vector_weight = vector_weight / total_weight
            keyword_weight = keyword_weight / total_weight

            # Generate query embedding
            query_result = await self.embedding_service.generate_query_embedding(
                query, use_cache=True
            )

            query_embedding = query_result["embedding"]

            # Build hybrid search SQL
            # Combines cosine similarity with full-text search ranking
            sql = """
            WITH vector_scores AS (
                SELECT
                    e.document_id,
                    MAX(1 - (e.embedding <=> %s::vector)) as vector_score,
                    MAX(e.chunk_text) as matched_chunk
                FROM embeddings e
                WHERE 1=1
            """

            params = [query_embedding]

            if user_id:
                sql += " AND e.user_id = %s"
                params.append(user_id)

            sql += " GROUP BY e.document_id"
            sql += ")"

            # Full-text search on documents
            sql += """
            , keyword_scores AS (
                SELECT
                    d.id as document_id,
                    ts_rank(
                        to_tsvector('english', d.extracted_text),
                        plainto_tsquery('english', %s)
                    ) as keyword_score
                FROM documents d
                WHERE to_tsvector('english', d.extracted_text) @@ plainto_tsquery('english', %s)
            """

            params.append(query)
            params.append(query)

            if user_id:
                sql += " AND d.user_id = %s"
                params.append(user_id)

            if document_type:
                sql += " AND d.document_type = %s"
                params.append(document_type)

            if date_from:
                sql += " AND d.created_at >= %s"
                params.append(date_from)

            if date_to:
                sql += " AND d.created_at <= %s"
                params.append(date_to)

            sql += ")"

            # Combine scores
            sql += f"""
            SELECT
                d.id,
                d.filename,
                d.document_type,
                d.created_at,
                d.word_count,
                COALESCE(vs.vector_score, 0) * {vector_weight} +
                COALESCE(ks.keyword_score, 0) * {keyword_weight} as combined_score,
                COALESCE(vs.vector_score, 0) as vector_score,
                COALESCE(ks.keyword_score, 0) as keyword_score,
                vs.matched_chunk
            FROM documents d
            LEFT JOIN vector_scores vs ON d.id = vs.document_id
            LEFT JOIN keyword_scores ks ON d.id = ks.document_id
            WHERE (vs.vector_score IS NOT NULL OR ks.keyword_score IS NOT NULL)
            ORDER BY combined_score DESC
            LIMIT %s
            """

            params.append(limit)

            # Execute query
            results = await execute_query(sql, tuple(params))

            # Process results
            search_results = []

            for row in results:
                search_results.append(
                    {
                        "document_id": row["id"],
                        "filename": row["filename"],
                        "document_type": row["document_type"],
                        "created_at": (
                            row["created_at"].isoformat() if row["created_at"] else None
                        ),
                        "word_count": row["word_count"],
                        "combined_score": float(row["combined_score"]),
                        "vector_score": float(row["vector_score"]),
                        "keyword_score": float(row["keyword_score"]),
                        "matched_chunk": row["matched_chunk"],
                    }
                )

            logger.info(f"Hybrid search: {len(search_results)} results")

            return {
                "query": query,
                "results": search_results,
                "total_results": len(search_results),
                "vector_weight": vector_weight,
                "keyword_weight": keyword_weight,
                "embedding_cost": query_result["cost"],
            }

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}", exc_info=True)
            raise AIServiceError(
                message="Hybrid search failed",
                details={"query": query, "error": str(e)},
            )

    async def find_similar_documents(
        self,
        document_id: str,
        user_id: Optional[str] = None,
        similarity_threshold: float = 0.75,
        limit: int = 5,
    ) -> Dict[str, Any]:
        """
        Find documents similar to a given document.

        Args:
            document_id: Source document ID
            user_id: Filter by user ID
            similarity_threshold: Minimum similarity score
            limit: Maximum number of results

        Returns:
            Similar documents with scores
        """
        try:
            logger.info(f"Finding similar documents to {document_id}")

            # Get embeddings for source document
            source_embeddings = await execute_select(
                "embeddings", match={"document_id": document_id}, limit=1
            )

            if not source_embeddings:
                return {
                    "document_id": document_id,
                    "results": [],
                    "total_results": 0,
                    "message": "No embeddings found for document",
                }

            source_embedding = source_embeddings[0]["embedding"]

            # Find similar documents
            sql = """
            SELECT DISTINCT
                e.document_id,
                d.filename,
                d.document_type,
                d.created_at,
                d.word_count,
                AVG(1 - (e.embedding <=> %s::vector)) as similarity_score
            FROM embeddings e
            INNER JOIN documents d ON e.document_id = d.id
            WHERE e.document_id != %s
            """

            params = [source_embedding, document_id]

            if user_id:
                sql += " AND e.user_id = %s"
                params.append(user_id)

            sql += """
            GROUP BY e.document_id, d.filename, d.document_type, d.created_at, d.word_count
            HAVING AVG(1 - (e.embedding <=> %s::vector)) >= %s
            ORDER BY similarity_score DESC
            LIMIT %s
            """

            params.extend([source_embedding, similarity_threshold, limit])

            # Execute query
            results = await execute_query(sql, tuple(params))

            # Process results
            similar_docs = []

            for row in results:
                similar_docs.append(
                    {
                        "document_id": row["document_id"],
                        "filename": row["filename"],
                        "document_type": row["document_type"],
                        "created_at": (
                            row["created_at"].isoformat() if row["created_at"] else None
                        ),
                        "word_count": row["word_count"],
                        "similarity_score": float(row["similarity_score"]),
                    }
                )

            logger.info(f"Found {len(similar_docs)} similar documents")

            return {
                "document_id": document_id,
                "results": similar_docs,
                "total_results": len(similar_docs),
                "similarity_threshold": similarity_threshold,
            }

        except Exception as e:
            logger.error(f"Find similar documents failed: {e}", exc_info=True)
            raise AIServiceError(
                message="Find similar documents failed",
                details={"document_id": document_id, "error": str(e)},
            )

    async def delete_document_embeddings(
        self,
        document_id: str,
    ) -> int:
        """
        Delete embeddings for a document.

        Args:
            document_id: Document ID

        Returns:
            Number of embeddings deleted
        """
        try:
            # In a real implementation, we'd execute a DELETE query
            # For now, we'll use a workaround with our execute functions

            sql = "DELETE FROM embeddings WHERE document_id = %s RETURNING id"
            results = await execute_query(sql, (document_id,))

            deleted_count = len(results)

            logger.info(
                f"Deleted {deleted_count} embeddings for document {document_id}"
            )

            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete embeddings: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to delete embeddings",
                details={"document_id": document_id, "error": str(e)},
            )

    async def update_document_embeddings(
        self,
        document_id: str,
        new_text: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Update embeddings for a document (delete old, generate new).

        Args:
            document_id: Document ID
            new_text: Updated document text
            user_id: User ID
            metadata: Additional metadata

        Returns:
            Update result with counts
        """
        try:
            logger.info(f"Updating embeddings for document {document_id}")

            # Delete old embeddings
            deleted = await self.delete_document_embeddings(document_id)

            # Generate new embeddings
            embeddings_result = await self.embedding_service.generate_embeddings(
                new_text,
                use_cache=False,  # Don't cache during updates
            )

            # Store new embeddings
            stored = await self.store_document_embeddings(
                document_id,
                embeddings_result["embeddings"],
                user_id,
                metadata,
            )

            return {
                "document_id": document_id,
                "deleted_embeddings": deleted,
                "stored_embeddings": stored,
                "cost": embeddings_result["total_cost"],
            }

        except Exception as e:
            logger.error(f"Failed to update embeddings: {e}", exc_info=True)
            raise AIServiceError(
                message="Failed to update embeddings",
                details={"document_id": document_id, "error": str(e)},
            )

    async def get_search_suggestions(
        self,
        partial_query: str,
        user_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[str]:
        """
        Get search query suggestions based on previous searches and document content.

        Args:
            partial_query: Partial search query
            user_id: Filter by user ID
            limit: Maximum number of suggestions

        Returns:
            List of suggested queries
        """
        try:
            # Check cache for previous searches
            cache_key = f"search_suggestions:{user_id}:{partial_query.lower()}"
            cached = await get_cache(cache_key)

            if cached:
                return cached

            # Get common phrases from documents
            sql = """
            SELECT DISTINCT
                ts_headline('english', d.extracted_text, plainto_tsquery('english', %s),
                    'MaxWords=5, MinWords=2, MaxFragments=1') as suggestion
            FROM documents d
            WHERE to_tsvector('english', d.extracted_text) @@ plainto_tsquery('english', %s)
            """

            params = [partial_query, partial_query]

            if user_id:
                sql += " AND d.user_id = %s"
                params.append(user_id)

            sql += " LIMIT %s"
            params.append(limit)

            results = await execute_query(sql, tuple(params))

            suggestions = [row["suggestion"] for row in results if row["suggestion"]]

            # Cache suggestions
            if suggestions:
                await set_cache(cache_key, suggestions, ttl=3600)

            return suggestions

        except Exception as e:
            logger.error(f"Failed to get search suggestions: {e}")
            return []

    def _generate_search_cache_key(
        self,
        query: str,
        user_id: Optional[str],
        document_type: Optional[str],
        date_from: Optional[datetime],
        date_to: Optional[datetime],
        limit: int,
    ) -> str:
        """Generate cache key for search results."""
        import hashlib

        key_parts = [
            query,
            user_id or "all",
            document_type or "all",
            date_from.isoformat() if date_from else "none",
            date_to.isoformat() if date_to else "none",
            str(limit),
        ]

        key_str = ":".join(key_parts)
        key_hash = hashlib.sha256(key_str.encode()).hexdigest()[:16]

        return f"search:{key_hash}"

    async def get_search_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get search statistics.

        Args:
            user_id: Filter by user ID

        Returns:
            Statistics dictionary
        """
        try:
            sql = """
            SELECT
                COUNT(DISTINCT document_id) as total_documents,
                COUNT(*) as total_embeddings,
                AVG(tokens) as avg_tokens_per_chunk,
                SUM(tokens) as total_tokens
            FROM embeddings
            WHERE 1=1
            """

            params = []

            if user_id:
                sql += " AND user_id = %s"
                params.append(user_id)

            results = await execute_query(sql, tuple(params) if params else ())

            if results:
                row = results[0]
                return {
                    "total_documents": row["total_documents"] or 0,
                    "total_embeddings": row["total_embeddings"] or 0,
                    "avg_tokens_per_chunk": float(row["avg_tokens_per_chunk"] or 0),
                    "total_tokens": row["total_tokens"] or 0,
                }

            return {
                "total_documents": 0,
                "total_embeddings": 0,
                "avg_tokens_per_chunk": 0,
                "total_tokens": 0,
            }

        except Exception as e:
            logger.error(f"Failed to get search stats: {e}")
            return {
                "total_documents": 0,
                "total_embeddings": 0,
                "avg_tokens_per_chunk": 0,
                "total_tokens": 0,
            }
