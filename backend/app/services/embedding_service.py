"""
Embedding Service for PM Document Intelligence.

This module provides OpenAI embedding generation with chunking, batching,
caching, and cost tracking for vector search capabilities.

Features:
- Text chunking for long documents
- Batch embedding generation
- Redis caching to avoid re-computation
- Rate limiting and retry logic
- Cost tracking per embedding
- Support for multiple embedding models

Usage:
    from app.services.embedding_service import EmbeddingService

    embedding_service = EmbeddingService()
    embeddings = await embedding_service.generate_embeddings(
        text="Long document text...",
        model="text-embedding-3-small"
    )
"""

import asyncio
import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

import tiktoken
from openai import AsyncOpenAI, OpenAIError, RateLimitError, APIError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from app.config import settings
from app.cache.redis import get_cache, set_cache
from app.utils.exceptions import AIServiceError
from app.utils.logger import get_logger


logger = get_logger(__name__)


# ============================================================================
# Embedding Models and Pricing
# ============================================================================


class EmbeddingModel:
    """OpenAI embedding model configurations."""

    TEXT_EMBEDDING_3_SMALL = {
        "name": "text-embedding-3-small",
        "dimensions": 1536,
        "max_tokens": 8191,
        "price_per_1k_tokens": 0.00002,  # $0.02 per 1M tokens
    }

    TEXT_EMBEDDING_3_LARGE = {
        "name": "text-embedding-3-large",
        "dimensions": 3072,
        "max_tokens": 8191,
        "price_per_1k_tokens": 0.00013,  # $0.13 per 1M tokens
    }

    # Alias for backward compatibility
    ADA_002 = {
        "name": "text-embedding-ada-002",
        "dimensions": 1536,
        "max_tokens": 8191,
        "price_per_1k_tokens": 0.0001,  # $0.10 per 1M tokens
    }


# ============================================================================
# Cost Tracking
# ============================================================================


class EmbeddingCostTracker:
    """Track embedding generation costs."""

    def __init__(self):
        """Initialize cost tracker."""
        self.total_tokens = 0
        self.total_embeddings = 0
        self.total_cost = 0.0
        self.costs_by_model: Dict[str, float] = {}
        self.tokens_by_model: Dict[str, int] = {}

    def track_usage(self, model: str, tokens: int, price_per_1k: float) -> float:
        """
        Track embedding usage and calculate cost.

        Args:
            model: Model name
            tokens: Number of tokens processed
            price_per_1k: Price per 1000 tokens

        Returns:
            Cost in USD
        """
        cost = (tokens / 1000) * price_per_1k

        self.total_tokens += tokens
        self.total_embeddings += 1
        self.total_cost += cost

        self.costs_by_model[model] = self.costs_by_model.get(model, 0) + cost
        self.tokens_by_model[model] = self.tokens_by_model.get(model, 0) + tokens

        logger.debug(f"Embedding usage: {tokens} tokens, ${cost:.6f}")

        return cost

    def get_report(self) -> Dict[str, Any]:
        """
        Get cost report.

        Returns:
            Cost report dictionary
        """
        return {
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "total_embeddings": self.total_embeddings,
            "average_cost_per_embedding": (
                self.total_cost / self.total_embeddings if self.total_embeddings > 0 else 0
            ),
            "costs_by_model": self.costs_by_model.copy(),
            "tokens_by_model": self.tokens_by_model.copy(),
        }

    def reset(self) -> None:
        """Reset all tracking."""
        self.total_tokens = 0
        self.total_embeddings = 0
        self.total_cost = 0.0
        self.costs_by_model.clear()
        self.tokens_by_model.clear()


# Global cost tracker
embedding_cost_tracker = EmbeddingCostTracker()


# ============================================================================
# Text Chunking
# ============================================================================


class TextChunker:
    """Chunk text for embedding generation."""

    def __init__(self, model: str = "text-embedding-3-small", max_tokens: int = 8191):
        """
        Initialize text chunker.

        Args:
            model: Embedding model name
            max_tokens: Maximum tokens per chunk
        """
        self.model = model
        self.max_tokens = max_tokens

        # Initialize tokenizer (cl100k_base is used by embedding models)
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning(f"Failed to load tiktoken encoding: {e}")
            self.encoding = None

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Input text

        Returns:
            Number of tokens
        """
        if self.encoding:
            return len(self.encoding.encode(text))
        else:
            # Rough estimate: ~4 characters per token
            return len(text) // 4

    def chunk_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        overlap: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Chunk text into smaller pieces for embedding.

        Args:
            text: Input text
            chunk_size: Maximum tokens per chunk (defaults to max_tokens - 100)
            overlap: Number of tokens to overlap between chunks

        Returns:
            List of chunks with metadata
        """
        if not chunk_size:
            chunk_size = self.max_tokens - 100  # Leave some buffer

        # Count total tokens
        total_tokens = self.count_tokens(text)

        # If text fits in one chunk, return as-is
        if total_tokens <= chunk_size:
            return [
                {
                    "text": text,
                    "chunk_index": 0,
                    "total_chunks": 1,
                    "tokens": total_tokens,
                    "start_char": 0,
                    "end_char": len(text),
                }
            ]

        # Split into sentences for better chunking
        sentences = self._split_into_sentences(text)

        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_index = 0
        char_position = 0

        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)

            # If single sentence exceeds chunk size, split it
            if sentence_tokens > chunk_size:
                if current_chunk:
                    # Save current chunk
                    chunk_text = " ".join(current_chunk)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "chunk_index": chunk_index,
                            "tokens": current_tokens,
                            "start_char": char_position - len(chunk_text),
                            "end_char": char_position,
                        }
                    )
                    chunk_index += 1
                    current_chunk = []
                    current_tokens = 0

                # Split long sentence by characters
                sub_chunks = self._split_long_text(sentence, chunk_size)
                for sub_chunk in sub_chunks:
                    chunks.append(
                        {
                            "text": sub_chunk,
                            "chunk_index": chunk_index,
                            "tokens": self.count_tokens(sub_chunk),
                            "start_char": char_position,
                            "end_char": char_position + len(sub_chunk),
                        }
                    )
                    chunk_index += 1
                    char_position += len(sub_chunk)
                continue

            # Check if adding sentence would exceed chunk size
            if current_tokens + sentence_tokens > chunk_size:
                # Save current chunk
                chunk_text = " ".join(current_chunk)
                chunks.append(
                    {
                        "text": chunk_text,
                        "chunk_index": chunk_index,
                        "tokens": current_tokens,
                        "start_char": char_position - len(chunk_text),
                        "end_char": char_position,
                    }
                )
                chunk_index += 1

                # Start new chunk with overlap
                if overlap > 0 and current_chunk:
                    # Keep last few sentences for overlap
                    overlap_tokens = 0
                    overlap_sentences = []
                    for sent in reversed(current_chunk):
                        sent_tokens = self.count_tokens(sent)
                        if overlap_tokens + sent_tokens <= overlap:
                            overlap_sentences.insert(0, sent)
                            overlap_tokens += sent_tokens
                        else:
                            break

                    current_chunk = overlap_sentences
                    current_tokens = overlap_tokens
                else:
                    current_chunk = []
                    current_tokens = 0

            current_chunk.append(sentence)
            current_tokens += sentence_tokens
            char_position += len(sentence) + 1  # +1 for space

        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(
                {
                    "text": chunk_text,
                    "chunk_index": chunk_index,
                    "tokens": current_tokens,
                    "start_char": char_position - len(chunk_text),
                    "end_char": char_position,
                }
            )

        # Add total_chunks to all chunks
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk["total_chunks"] = total_chunks

        logger.info(f"Chunked text into {total_chunks} chunks ({total_tokens} total tokens)")

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        import re

        # Simple sentence splitting (can be improved with nltk/spacy)
        sentences = re.split(r"[.!?]+\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _split_long_text(self, text: str, max_tokens: int) -> List[str]:
        """
        Split long text by character count.

        Args:
            text: Input text
            max_tokens: Maximum tokens per chunk

        Returns:
            List of text chunks
        """
        # Rough estimate: 4 chars per token
        max_chars = max_tokens * 4

        chunks = []
        for i in range(0, len(text), max_chars):
            chunks.append(text[i : i + max_chars])

        return chunks


# ============================================================================
# Embedding Service
# ============================================================================


class EmbeddingService:
    """OpenAI embedding generation service."""

    def __init__(self):
        """Initialize embedding service."""
        # Initialize OpenAI client
        self.client = AsyncOpenAI(
            api_key=settings.openai.openai_api_key,
            timeout=60.0,
            max_retries=0,  # We handle retries with tenacity
        )

        # Default model
        self.default_model = (
            "text-embedding-3-small"
            if settings.is_production
            else "text-embedding-3-small"  # Use small model for dev too
        )

        # Text chunker
        self.chunker = TextChunker(model=self.default_model)

        # Rate limiting
        self.rate_limit_requests = 3000  # OpenAI limit: 3000 RPM for tier 1
        self.rate_limit_window = 60  # seconds
        self.request_timestamps: List[float] = []

        logger.info(f"Embedding service initialized with model: {self.default_model}")

    def _get_model_config(self, model: str) -> Dict[str, Any]:
        """
        Get model configuration.

        Args:
            model: Model name

        Returns:
            Model configuration dictionary
        """
        if model == "text-embedding-3-small":
            return EmbeddingModel.TEXT_EMBEDDING_3_SMALL
        elif model == "text-embedding-3-large":
            return EmbeddingModel.TEXT_EMBEDDING_3_LARGE
        elif model == "text-embedding-ada-002":
            return EmbeddingModel.ADA_002
        else:
            # Default to small
            return EmbeddingModel.TEXT_EMBEDDING_3_SMALL

    async def _check_rate_limit(self) -> None:
        """
        Check and enforce rate limits.

        Raises:
            AIServiceError: If rate limit would be exceeded
        """
        now = time.time()

        # Remove timestamps older than window
        self.request_timestamps = [
            ts for ts in self.request_timestamps if now - ts < self.rate_limit_window
        ]

        # Check if we're at limit
        if len(self.request_timestamps) >= self.rate_limit_requests:
            oldest = self.request_timestamps[0]
            wait_time = self.rate_limit_window - (now - oldest)

            logger.warning(f"Rate limit reached, waiting {wait_time:.2f}s")

            await asyncio.sleep(wait_time)

            # Recheck after waiting
            await self._check_rate_limit()

        # Add current timestamp
        self.request_timestamps.append(now)

    def _generate_cache_key(self, text: str, model: str) -> str:
        """
        Generate cache key for text + model.

        Args:
            text: Input text
            model: Model name

        Returns:
            Cache key
        """
        # Use hash of text + model for cache key
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"embedding:{model}:{text_hash}"

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        before_sleep=before_sleep_log(logger, "WARNING"),
    )
    async def _generate_embedding_api(
        self,
        text: str,
        model: str,
    ) -> List[float]:
        """
        Generate embedding via OpenAI API.

        Args:
            text: Input text
            model: Model name

        Returns:
            Embedding vector

        Raises:
            AIServiceError: If API call fails
        """
        try:
            # Check rate limit
            await self._check_rate_limit()

            start_time = time.time()

            # Call OpenAI API
            response = await self.client.embeddings.create(
                input=text,
                model=model,
            )

            duration = time.time() - start_time

            # Extract embedding
            embedding = response.data[0].embedding

            # Track cost
            tokens = response.usage.total_tokens
            model_config = self._get_model_config(model)
            cost = embedding_cost_tracker.track_usage(
                model, tokens, model_config["price_per_1k_tokens"]
            )

            logger.debug(f"Generated embedding: {tokens} tokens, ${cost:.6f}, {duration:.2f}s")

            return embedding

        except RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            raise

        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise AIServiceError(
                message="Embedding generation failed",
                details={"error": str(e), "model": model},
            )

        except Exception as e:
            logger.error(f"Unexpected embedding error: {e}", exc_info=True)
            raise AIServiceError(
                message="Unexpected error during embedding generation",
                details={"error": str(e)},
            )

    async def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate embedding for text.

        Args:
            text: Input text
            model: Model name (defaults to default_model)
            use_cache: Whether to use cache

        Returns:
            Dictionary with embedding and metadata
        """
        if not text or not text.strip():
            raise AIServiceError(message="Cannot generate embedding for empty text", details={})

        model = model or self.default_model

        # Check cache first
        if use_cache:
            cache_key = self._generate_cache_key(text, model)
            cached = await get_cache(cache_key)

            if cached:
                logger.debug(f"Embedding cache hit for {len(text)} chars")
                return {
                    "embedding": cached["embedding"],
                    "model": model,
                    "dimensions": len(cached["embedding"]),
                    "tokens": cached.get("tokens", 0),
                    "cost": 0.0,  # No cost for cached
                    "cached": True,
                }

        # Count tokens
        tokens = self.chunker.count_tokens(text)

        # Generate embedding
        embedding = await self._generate_embedding_api(text, model)

        model_config = self._get_model_config(model)

        result = {
            "embedding": embedding,
            "model": model,
            "dimensions": len(embedding),
            "tokens": tokens,
            "cost": (tokens / 1000) * model_config["price_per_1k_tokens"],
            "cached": False,
        }

        # Cache result
        if use_cache:
            await set_cache(
                cache_key,
                {
                    "embedding": embedding,
                    "tokens": tokens,
                    "generated_at": datetime.utcnow().isoformat(),
                },
                ttl=86400 * 7,  # Cache for 7 days
            )

        return result

    async def generate_embeddings(
        self,
        text: str,
        model: Optional[str] = None,
        chunk_size: Optional[int] = None,
        overlap: int = 200,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate embeddings for long text with chunking.

        Args:
            text: Input text
            model: Model name (defaults to default_model)
            chunk_size: Maximum tokens per chunk
            overlap: Overlap tokens between chunks
            use_cache: Whether to use cache

        Returns:
            Dictionary with embeddings and metadata
        """
        model = model or self.default_model

        # Chunk text
        chunks = self.chunker.chunk_text(text, chunk_size, overlap)

        logger.info(f"Generating embeddings for {len(chunks)} chunks")

        # Generate embeddings for each chunk
        chunk_embeddings = []
        total_cost = 0.0
        cached_count = 0

        for chunk in chunks:
            result = await self.generate_embedding(
                chunk["text"],
                model=model,
                use_cache=use_cache,
            )

            chunk_embeddings.append(
                {
                    "embedding": result["embedding"],
                    "chunk_index": chunk["chunk_index"],
                    "chunk_text": chunk["text"],
                    "tokens": result["tokens"],
                    "start_char": chunk["start_char"],
                    "end_char": chunk["end_char"],
                }
            )

            total_cost += result["cost"]

            if result["cached"]:
                cached_count += 1

        model_config = self._get_model_config(model)

        return {
            "embeddings": chunk_embeddings,
            "model": model,
            "dimensions": model_config["dimensions"],
            "total_chunks": len(chunks),
            "total_tokens": sum(c["tokens"] for c in chunk_embeddings),
            "total_cost": total_cost,
            "cached_chunks": cached_count,
        }

    async def generate_query_embedding(
        self,
        query: str,
        model: Optional[str] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate embedding for search query.

        Args:
            query: Search query text
            model: Model name (defaults to default_model)
            use_cache: Whether to use cache

        Returns:
            Dictionary with embedding and metadata
        """
        # Queries are typically short, no chunking needed
        return await self.generate_embedding(query, model=model, use_cache=use_cache)

    async def generate_batch_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
        use_cache: bool = True,
        batch_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of input texts
            model: Model name (defaults to default_model)
            use_cache: Whether to use cache
            batch_size: Maximum texts per API call (OpenAI limit: 2048)

        Returns:
            List of embedding results
        """
        model = model or self.default_model

        logger.info(f"Generating batch embeddings for {len(texts)} texts")

        results = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            # Check cache first
            uncached_texts = []
            uncached_indices = []

            for idx, text in enumerate(batch):
                if use_cache:
                    cache_key = self._generate_cache_key(text, model)
                    cached = await get_cache(cache_key)

                    if cached:
                        results.append(
                            {
                                "embedding": cached["embedding"],
                                "model": model,
                                "dimensions": len(cached["embedding"]),
                                "tokens": cached.get("tokens", 0),
                                "cost": 0.0,
                                "cached": True,
                                "text_index": i + idx,
                            }
                        )
                        continue

                uncached_texts.append(text)
                uncached_indices.append(i + idx)

            # Generate embeddings for uncached texts
            if uncached_texts:
                try:
                    await self._check_rate_limit()

                    start_time = time.time()

                    response = await self.client.embeddings.create(
                        input=uncached_texts,
                        model=model,
                    )

                    duration = time.time() - start_time

                    # Track cost
                    tokens = response.usage.total_tokens
                    model_config = self._get_model_config(model)
                    cost = embedding_cost_tracker.track_usage(
                        model, tokens, model_config["price_per_1k_tokens"]
                    )

                    # Process results
                    for idx, (text, embedding_data) in enumerate(
                        zip(uncached_texts, response.data)
                    ):
                        embedding = embedding_data.embedding

                        result = {
                            "embedding": embedding,
                            "model": model,
                            "dimensions": len(embedding),
                            "tokens": tokens // len(uncached_texts),  # Approximate
                            "cost": cost / len(uncached_texts),
                            "cached": False,
                            "text_index": uncached_indices[idx],
                        }

                        results.append(result)

                        # Cache result
                        if use_cache:
                            cache_key = self._generate_cache_key(text, model)
                            await set_cache(
                                cache_key,
                                {
                                    "embedding": embedding,
                                    "tokens": result["tokens"],
                                    "generated_at": datetime.utcnow().isoformat(),
                                },
                                ttl=86400 * 7,
                            )

                    logger.info(
                        f"Batch: {len(uncached_texts)} embeddings, "
                        f"{tokens} tokens, ${cost:.6f}, {duration:.2f}s"
                    )

                except Exception as e:
                    logger.error(f"Batch embedding failed: {e}")
                    raise AIServiceError(
                        message="Batch embedding generation failed",
                        details={"error": str(e), "batch_size": len(uncached_texts)},
                    )

        # Sort by original text index
        results.sort(key=lambda x: x["text_index"])

        return results

    def get_cost_report(self) -> Dict[str, Any]:
        """
        Get embedding cost report.

        Returns:
            Cost report dictionary
        """
        return embedding_cost_tracker.get_report()

    def reset_costs(self) -> None:
        """Reset cost tracking."""
        embedding_cost_tracker.reset()
