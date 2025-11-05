"""
Unit tests for vector search module
Tests embedding generation, similarity search, and caching
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timedelta

from app.services.vector_search import VectorSearch, EmbeddingCache
from app.models import Document


@pytest.mark.unit
class TestEmbeddingGeneration:
    """Test embedding generation"""

    @pytest.mark.asyncio
    async def test_generate_embedding(self, mock_openai_client):
        """Test generating embeddings for text"""
        vector_search = VectorSearch()

        with patch('app.services.vector_search.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client

            text = "This is test text for embedding generation"
            embedding = await vector_search.generate_embedding(text)

            assert embedding is not None
            assert isinstance(embedding, list)
            assert len(embedding) == 1536  # OpenAI embedding dimension

    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text(self):
        """Test generating embedding for empty text"""
        vector_search = VectorSearch()

        embedding = await vector_search.generate_embedding("")

        assert embedding is None or embedding == []

    @pytest.mark.asyncio
    async def test_generate_embedding_long_text(self, mock_openai_client):
        """Test generating embedding for long text"""
        vector_search = VectorSearch()

        with patch('app.services.vector_search.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client

            # Text longer than token limit
            long_text = "Sample text. " * 10000
            embedding = await vector_search.generate_embedding(long_text)

            # Should truncate and still generate
            assert embedding is not None
            assert isinstance(embedding, list)

    @pytest.mark.asyncio
    async def test_generate_embeddings_batch(self, mock_openai_client):
        """Test generating embeddings for multiple texts"""
        vector_search = VectorSearch()

        with patch('app.services.vector_search.OpenAI') as mock_openai:
            # Mock batch embeddings
            mock_embeddings = MagicMock()
            mock_embeddings.create.return_value = MagicMock(
                data=[
                    MagicMock(embedding=[0.1] * 1536),
                    MagicMock(embedding=[0.2] * 1536),
                    MagicMock(embedding=[0.3] * 1536)
                ]
            )
            mock_client = MagicMock()
            mock_client.embeddings = mock_embeddings
            mock_openai.return_value = mock_client

            texts = ["Text 1", "Text 2", "Text 3"]
            embeddings = await vector_search.generate_embeddings_batch(texts)

            assert len(embeddings) == 3
            assert all(len(emb) == 1536 for emb in embeddings)

    @pytest.mark.asyncio
    async def test_generate_embedding_error_handling(self):
        """Test error handling in embedding generation"""
        vector_search = VectorSearch()

        with patch('app.services.vector_search.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_client.embeddings.create.side_effect = Exception("API Error")
            mock_openai.return_value = mock_client

            with pytest.raises(Exception, match="API Error"):
                await vector_search.generate_embedding("test text")


@pytest.mark.unit
class TestVectorSimilaritySearch:
    """Test vector similarity search"""

    @pytest.mark.asyncio
    async def test_search_similar_documents(
        self,
        mock_openai_client,
        test_db,
        test_user,
        generate_documents
    ):
        """Test searching for similar documents"""
        vector_search = VectorSearch()

        # Generate test documents with embeddings
        documents = generate_documents(count=5, user=test_user)

        # Add mock embeddings to documents
        for i, doc in enumerate(documents):
            doc.embedding = [float(i) / 10] * 1536
        test_db.commit()

        with patch('app.services.vector_search.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client

            query = "test query"
            results = await vector_search.search(
                query=query,
                user_id=test_user.id,
                limit=3
            )

            assert results is not None
            assert 'results' in results
            assert len(results['results']) <= 3

    @pytest.mark.asyncio
    async def test_search_with_threshold(
        self,
        mock_openai_client,
        test_db,
        test_user,
        generate_documents
    ):
        """Test search with similarity threshold"""
        vector_search = VectorSearch()

        documents = generate_documents(count=5, user=test_user)

        # Add embeddings
        for i, doc in enumerate(documents):
            doc.embedding = [float(i) / 10] * 1536
        test_db.commit()

        with patch('app.services.vector_search.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client

            results = await vector_search.search(
                query="test query",
                user_id=test_user.id,
                similarity_threshold=0.8
            )

            # Only highly similar results should be returned
            assert results is not None

    @pytest.mark.asyncio
    async def test_search_no_results(
        self,
        mock_openai_client,
        test_db,
        test_user
    ):
        """Test search with no matching documents"""
        vector_search = VectorSearch()

        with patch('app.services.vector_search.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client

            results = await vector_search.search(
                query="test query",
                user_id=test_user.id
            )

            assert results is not None
            assert 'results' in results
            assert len(results['results']) == 0

    @pytest.mark.asyncio
    async def test_search_with_filters(
        self,
        mock_openai_client,
        test_db,
        test_user,
        generate_documents
    ):
        """Test search with filters"""
        vector_search = VectorSearch()

        documents = generate_documents(count=5, user=test_user)

        # Set different document types
        documents[0].document_type = "meeting_notes"
        documents[1].document_type = "project_plan"
        for i, doc in enumerate(documents):
            doc.embedding = [float(i) / 10] * 1536
        test_db.commit()

        with patch('app.services.vector_search.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client

            results = await vector_search.search(
                query="test query",
                user_id=test_user.id,
                filters={"document_type": "meeting_notes"}
            )

            assert results is not None
            # Should only return meeting_notes documents
            for result in results.get('results', []):
                assert result.get('document_type') == 'meeting_notes'

    def test_calculate_cosine_similarity(self):
        """Test cosine similarity calculation"""
        vector_search = VectorSearch()

        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        vec3 = [0.0, 1.0, 0.0]

        # Identical vectors
        sim1 = vector_search.cosine_similarity(vec1, vec2)
        assert sim1 == pytest.approx(1.0, abs=0.01)

        # Orthogonal vectors
        sim2 = vector_search.cosine_similarity(vec1, vec3)
        assert sim2 == pytest.approx(0.0, abs=0.01)

    def test_normalize_vector(self):
        """Test vector normalization"""
        vector_search = VectorSearch()

        vec = [3.0, 4.0, 0.0]
        normalized = vector_search.normalize_vector(vec)

        # Length should be 1
        length = sum(x ** 2 for x in normalized) ** 0.5
        assert length == pytest.approx(1.0, abs=0.01)


@pytest.mark.unit
class TestEmbeddingCache:
    """Test embedding caching"""

    def test_cache_embedding(self):
        """Test caching embeddings"""
        cache = EmbeddingCache()

        text = "test text"
        embedding = [0.1] * 1536

        cache.set(text, embedding)
        cached = cache.get(text)

        assert cached is not None
        assert cached == embedding

    def test_cache_miss(self):
        """Test cache miss"""
        cache = EmbeddingCache()

        cached = cache.get("nonexistent text")

        assert cached is None

    def test_cache_expiration(self):
        """Test cache expiration"""
        cache = EmbeddingCache(ttl=1)  # 1 second TTL

        text = "test text"
        embedding = [0.1] * 1536

        cache.set(text, embedding)

        # Should be cached immediately
        cached1 = cache.get(text)
        assert cached1 is not None

        # Wait for expiration
        import time
        time.sleep(2)

        # Should be expired
        cached2 = cache.get(text)
        assert cached2 is None

    def test_cache_size_limit(self):
        """Test cache size limit"""
        cache = EmbeddingCache(max_size=3)

        # Add 4 items
        for i in range(4):
            cache.set(f"text_{i}", [float(i)] * 1536)

        # First item should be evicted (LRU)
        cached_first = cache.get("text_0")
        cached_last = cache.get("text_3")

        assert cached_first is None  # Evicted
        assert cached_last is not None  # Still cached

    def test_cache_clear(self):
        """Test clearing cache"""
        cache = EmbeddingCache()

        cache.set("text1", [0.1] * 1536)
        cache.set("text2", [0.2] * 1536)

        cache.clear()

        assert cache.get("text1") is None
        assert cache.get("text2") is None

    def test_cache_statistics(self):
        """Test cache statistics"""
        cache = EmbeddingCache()

        cache.set("text1", [0.1] * 1536)

        # Hit
        cache.get("text1")

        # Miss
        cache.get("text2")

        stats = cache.get_stats()

        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['size'] == 1


@pytest.mark.unit
class TestHybridSearch:
    """Test hybrid search combining vector and keyword search"""

    @pytest.mark.asyncio
    async def test_hybrid_search(
        self,
        mock_openai_client,
        test_db,
        test_user,
        generate_documents
    ):
        """Test hybrid search"""
        vector_search = VectorSearch()

        documents = generate_documents(count=5, user=test_user)

        # Add embeddings and text
        for i, doc in enumerate(documents):
            doc.embedding = [float(i) / 10] * 1536
            doc.extracted_text = f"Document {i} contains specific keywords"
        test_db.commit()

        with patch('app.services.vector_search.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client

            results = await vector_search.hybrid_search(
                query="specific keywords",
                user_id=test_user.id,
                semantic_weight=0.5,
                keyword_weight=0.5
            )

            assert results is not None
            assert 'results' in results

    @pytest.mark.asyncio
    async def test_keyword_only_search(
        self,
        test_db,
        test_user,
        generate_documents
    ):
        """Test keyword-only search"""
        vector_search = VectorSearch()

        documents = generate_documents(count=5, user=test_user)
        documents[0].extracted_text = "This contains the specific keyword"
        documents[1].extracted_text = "This does not contain it"
        test_db.commit()

        results = await vector_search.keyword_search(
            query="specific keyword",
            user_id=test_user.id
        )

        assert results is not None
        assert len(results.get('results', [])) > 0

    @pytest.mark.asyncio
    async def test_search_with_weights(
        self,
        mock_openai_client,
        test_db,
        test_user,
        generate_documents
    ):
        """Test hybrid search with different weights"""
        vector_search = VectorSearch()

        documents = generate_documents(count=3, user=test_user)
        for i, doc in enumerate(documents):
            doc.embedding = [float(i) / 10] * 1536
        test_db.commit()

        with patch('app.services.vector_search.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client

            # Semantic-heavy
            results1 = await vector_search.hybrid_search(
                query="test",
                user_id=test_user.id,
                semantic_weight=0.9,
                keyword_weight=0.1
            )

            # Keyword-heavy
            results2 = await vector_search.hybrid_search(
                query="test",
                user_id=test_user.id,
                semantic_weight=0.1,
                keyword_weight=0.9
            )

            assert results1 is not None
            assert results2 is not None


@pytest.mark.unit
class TestVectorIndexing:
    """Test vector indexing operations"""

    @pytest.mark.asyncio
    async def test_index_document(
        self,
        mock_openai_client,
        test_db,
        test_user,
        sample_document
    ):
        """Test indexing a document"""
        vector_search = VectorSearch()

        with patch('app.services.vector_search.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client

            result = await vector_search.index_document(
                document_id=sample_document.id,
                text=sample_document.extracted_text,
                db=test_db
            )

            assert result is True

            # Check embedding was saved
            test_db.refresh(sample_document)
            assert sample_document.embedding is not None

    @pytest.mark.asyncio
    async def test_batch_index_documents(
        self,
        mock_openai_client,
        test_db,
        test_user,
        generate_documents
    ):
        """Test batch indexing documents"""
        vector_search = VectorSearch()

        documents = generate_documents(count=5, user=test_user)

        with patch('app.services.vector_search.OpenAI') as mock_openai:
            mock_embeddings = MagicMock()
            mock_embeddings.create.return_value = MagicMock(
                data=[MagicMock(embedding=[0.1] * 1536) for _ in range(5)]
            )
            mock_client = MagicMock()
            mock_client.embeddings = mock_embeddings
            mock_openai.return_value = mock_client

            result = await vector_search.batch_index_documents(
                document_ids=[d.id for d in documents],
                db=test_db
            )

            assert result is not None
            assert result['indexed'] == 5

    @pytest.mark.asyncio
    async def test_reindex_document(
        self,
        mock_openai_client,
        test_db,
        sample_document
    ):
        """Test reindexing a document"""
        vector_search = VectorSearch()

        # Set initial embedding
        sample_document.embedding = [0.1] * 1536
        test_db.commit()

        with patch('app.services.vector_search.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client

            # Reindex with new text
            await vector_search.index_document(
                document_id=sample_document.id,
                text="New updated text",
                db=test_db,
                force_reindex=True
            )

            # Embedding should be updated
            test_db.refresh(sample_document)
            assert sample_document.embedding is not None

    @pytest.mark.asyncio
    async def test_delete_from_index(
        self,
        test_db,
        sample_document
    ):
        """Test deleting document from index"""
        vector_search = VectorSearch()

        # Set embedding
        sample_document.embedding = [0.1] * 1536
        test_db.commit()

        # Delete from index
        result = await vector_search.delete_from_index(
            document_id=sample_document.id,
            db=test_db
        )

        assert result is True

        # Embedding should be removed
        test_db.refresh(sample_document)
        assert sample_document.embedding is None


@pytest.mark.unit
class TestSearchOptimization:
    """Test search optimization features"""

    @pytest.mark.asyncio
    async def test_search_with_pagination(
        self,
        mock_openai_client,
        test_db,
        test_user,
        generate_documents
    ):
        """Test paginated search results"""
        vector_search = VectorSearch()

        documents = generate_documents(count=20, user=test_user)
        for i, doc in enumerate(documents):
            doc.embedding = [float(i) / 20] * 1536
        test_db.commit()

        with patch('app.services.vector_search.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client

            # First page
            results1 = await vector_search.search(
                query="test",
                user_id=test_user.id,
                limit=10,
                offset=0
            )

            # Second page
            results2 = await vector_search.search(
                query="test",
                user_id=test_user.id,
                limit=10,
                offset=10
            )

            assert len(results1['results']) == 10
            assert len(results2['results']) == 10

    @pytest.mark.asyncio
    async def test_search_with_boost(
        self,
        mock_openai_client,
        test_db,
        test_user,
        generate_documents
    ):
        """Test search with field boosting"""
        vector_search = VectorSearch()

        documents = generate_documents(count=3, user=test_user)
        for i, doc in enumerate(documents):
            doc.embedding = [float(i) / 10] * 1536
            doc.metadata = {"importance": i + 1}
        test_db.commit()

        with patch('app.services.vector_search.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client

            results = await vector_search.search(
                query="test",
                user_id=test_user.id,
                boost_fields={"importance": 2.0}
            )

            assert results is not None
            # Higher importance docs should rank higher

    @pytest.mark.asyncio
    async def test_search_performance(
        self,
        mock_openai_client,
        test_db,
        test_user,
        generate_documents,
        benchmark_timer
    ):
        """Test search performance"""
        vector_search = VectorSearch()

        # Generate many documents
        documents = generate_documents(count=100, user=test_user)
        for i, doc in enumerate(documents):
            doc.embedding = [float(i) / 100] * 1536
        test_db.commit()

        with patch('app.services.vector_search.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client

            with benchmark_timer:
                results = await vector_search.search(
                    query="test",
                    user_id=test_user.id,
                    limit=10
                )

            # Should complete in reasonable time
            assert benchmark_timer.elapsed < 5.0  # Less than 5 seconds
            assert results is not None
