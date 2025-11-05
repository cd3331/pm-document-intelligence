# Vector Search with OpenAI Embeddings

## Overview

The Vector Search system provides semantic search capabilities for the PM Document Intelligence platform using OpenAI embeddings and PostgreSQL's pgvector extension. This enables natural language queries to find relevant documents based on meaning rather than exact keyword matches.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Vector Search System                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. Text Chunking      ───▶  Break long text into chunks        │
│  2. Embedding Gen      ───▶  OpenAI API (text-embedding-3)      │
│  3. Redis Cache        ───▶  Cache embeddings (7 days)          │
│  4. pgvector Store     ───▶  PostgreSQL with vector column      │
│  5. Similarity Search  ───▶  Cosine distance calculation        │
│  6. Result Ranking     ───▶  Score-based ranking                │
│                                                                   │
│  ✓ IVFFlat Index       ───▶  Fast approximate search            │
│  ✓ Hybrid Search       ───▶  Vector + keyword combination       │
│  ✓ Cost Tracking       ───▶  Per-query cost monitoring          │
│  ✓ Rate Limiting       ───▶  OpenAI API limits respected        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Features

### 1. Embedding Generation

**Service**: `backend/app/services/embedding_service.py`

Features:
- **Text Chunking**: Automatically splits long documents into chunks (max 8,191 tokens)
- **Batch Processing**: Efficient batching for multiple texts
- **Redis Caching**: Avoids re-computing embeddings (7-day TTL)
- **Cost Tracking**: Tracks tokens and costs per embedding
- **Rate Limiting**: Respects OpenAI's 3,000 RPM limit
- **Model Selection**: Supports multiple embedding models

**Supported Models:**
- `text-embedding-3-small`: 1536 dimensions, $0.02 per 1M tokens
- `text-embedding-3-large`: 3072 dimensions, $0.13 per 1M tokens
- `text-embedding-ada-002`: 1536 dimensions, $0.10 per 1M tokens (legacy)

### 2. Vector Search

**Service**: `backend/app/services/vector_search.py`

Features:
- **Semantic Search**: Natural language queries
- **Hybrid Search**: Combines vector similarity with keyword matching
- **Similar Documents**: Find related documents
- **Filtering**: By user, document type, date range
- **Configurable Thresholds**: Adjust similarity requirements
- **Result Caching**: 5-minute TTL for search results

### 3. Database Integration

**Migration**: `scripts/init_vector_search.sql`

Features:
- **pgvector Extension**: Vector similarity operations
- **IVFFlat Index**: Fast approximate nearest neighbor search
- **Full-Text Search**: PostgreSQL FTS for keyword matching
- **Row Level Security**: User-based access control
- **Helper Functions**: Cosine similarity, similar embeddings
- **Views**: Statistics and monitoring

## Setup

### 1. Prerequisites

```bash
# Install pgvector extension in PostgreSQL
# If using Supabase, enable in SQL editor:
CREATE EXTENSION IF NOT EXISTS vector;

# Install Python dependencies
pip install openai tiktoken
```

### 2. Environment Variables

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Redis Configuration (for caching)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### 3. Database Migration

```bash
# Run migration script
psql -U postgres -d your_database -f scripts/init_vector_search.sql

# Or in Supabase SQL editor:
# Copy and paste the contents of init_vector_search.sql
```

### 4. Verify Installation

```sql
-- Check pgvector extension
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- Check embeddings table
SELECT COUNT(*) FROM embeddings;

-- Check indexes
SELECT indexname FROM pg_indexes WHERE tablename = 'embeddings';
```

## Usage

### Generate Embeddings

```python
from app.services.embedding_service import EmbeddingService

embedding_service = EmbeddingService()

# Single short text
result = await embedding_service.generate_embedding(
    text="This is a short document",
    model="text-embedding-3-small",
    use_cache=True
)

# result:
{
    "embedding": [0.123, -0.456, ...],  # 1536 dimensions
    "model": "text-embedding-3-small",
    "dimensions": 1536,
    "tokens": 5,
    "cost": 0.0000001,
    "cached": False
}

# Long document with chunking
result = await embedding_service.generate_embeddings(
    text="Very long document...",
    chunk_size=8000,
    overlap=200,
    use_cache=True
)

# result:
{
    "embeddings": [
        {
            "embedding": [...],
            "chunk_index": 0,
            "chunk_text": "First chunk...",
            "tokens": 500,
            "start_char": 0,
            "end_char": 2000
        },
        ...
    ],
    "total_chunks": 5,
    "total_tokens": 2500,
    "total_cost": 0.00005,
    "cached_chunks": 2
}

# Batch processing
texts = ["Text 1", "Text 2", "Text 3"]
results = await embedding_service.generate_batch_embeddings(
    texts=texts,
    batch_size=100,
    use_cache=True
)
```

### Store Embeddings

```python
from app.services.vector_search import VectorSearch

vector_search = VectorSearch()

# Store document embeddings
await vector_search.store_document_embeddings(
    document_id="doc_123",
    embeddings=result["embeddings"],
    user_id="user_456",
    metadata={
        "document_type": "project_plan",
        "source": "upload"
    }
)
```

### Semantic Search

```python
# Basic semantic search
results = await vector_search.semantic_search(
    query="Find all project risks",
    user_id="user_456",
    limit=10
)

# Advanced search with filters
results = await vector_search.semantic_search(
    query="budget overruns and delays",
    user_id="user_456",
    document_type="status_report",
    date_from=datetime(2024, 1, 1),
    date_to=datetime(2024, 12, 31),
    similarity_threshold=0.75,
    limit=20,
    use_cache=True
)

# Result structure:
{
    "query": "Find all project risks",
    "results": [
        {
            "document_id": "doc_123",
            "filename": "project_plan.pdf",
            "document_type": "project_plan",
            "similarity_score": 0.89,
            "created_at": "2024-01-15T10:30:00Z",
            "word_count": 1234,
            "matched_chunk": {
                "text": "The main risk identified...",
                "chunk_index": 2,
                "start_char": 500,
                "end_char": 1000
            }
        }
    ],
    "total_results": 5,
    "similarity_threshold": 0.7,
    "duration_seconds": 0.234,
    "embedding_cost": 0.00002
}
```

### Hybrid Search

```python
# Combine vector similarity with keyword matching
results = await vector_search.hybrid_search(
    query="Q4 budget review",
    user_id="user_456",
    vector_weight=0.7,   # 70% from semantic similarity
    keyword_weight=0.3,  # 30% from keyword match
    limit=10
)

# Result structure:
{
    "query": "Q4 budget review",
    "results": [
        {
            "document_id": "doc_456",
            "filename": "q4_budget.pdf",
            "combined_score": 0.85,
            "vector_score": 0.82,
            "keyword_score": 0.91,
            "matched_chunk": "Q4 budget review shows..."
        }
    ],
    "vector_weight": 0.7,
    "keyword_weight": 0.3
}
```

### Find Similar Documents

```python
# Find documents similar to a specific document
results = await vector_search.find_similar_documents(
    document_id="doc_123",
    user_id="user_456",
    similarity_threshold=0.75,
    limit=5
)

# Result structure:
{
    "document_id": "doc_123",
    "results": [
        {
            "document_id": "doc_789",
            "filename": "similar_project.pdf",
            "similarity_score": 0.88,
            "document_type": "project_plan"
        }
    ],
    "total_results": 3
}
```

## API Endpoints

### GET /api/search/semantic

Perform semantic search using natural language queries.

**Query Parameters:**
- `query` (required): Search query text
- `document_type` (optional): Filter by document type
- `date_from` (optional): Filter by date range start
- `date_to` (optional): Filter by date range end
- `similarity_threshold` (optional): Minimum similarity (0-1), default: 0.7
- `limit` (optional): Maximum results (1-50), default: 10

**Rate Limit:** 30 requests/minute

**Example:**
```bash
curl -X GET \
  "https://api.example.com/api/search/semantic?query=find%20project%20risks&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "query": "find project risks",
  "results": [
    {
      "document_id": "doc_123",
      "filename": "project_plan.pdf",
      "document_type": "project_plan",
      "similarity_score": 0.89,
      "matched_chunk": {
        "text": "Main risks identified...",
        "chunk_index": 2
      }
    }
  ],
  "total_results": 5,
  "duration_seconds": 0.234
}
```

### POST /api/search/semantic

Advanced semantic search with complex filters.

**Request Body:**
```json
{
  "query": "find project risks and blockers",
  "document_type": "project_plan",
  "date_from": "2024-01-01T00:00:00Z",
  "similarity_threshold": 0.75,
  "limit": 20
}
```

### POST /api/search/hybrid

Hybrid search combining vector and keyword search.

**Request Body:**
```json
{
  "query": "Q4 budget review",
  "vector_weight": 0.6,
  "keyword_weight": 0.4,
  "limit": 10
}
```

### GET /api/search/similar/{document_id}

Find documents similar to a given document.

**Path Parameters:**
- `document_id` (required): Source document ID

**Query Parameters:**
- `similarity_threshold` (optional): Default: 0.75
- `limit` (optional): Default: 5

**Rate Limit:** 60 requests/minute

### GET /api/search/suggestions

Get search query suggestions.

**Query Parameters:**
- `q` (required): Partial query text
- `limit` (optional): Maximum suggestions (1-10), default: 5

**Rate Limit:** 60 requests/minute

**Example:**
```bash
curl -X GET \
  "https://api.example.com/api/search/suggestions?q=project&limit=5" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "partial_query": "project",
  "suggestions": [
    "project timeline",
    "project risks",
    "project budget",
    "project milestones"
  ]
}
```

### GET /api/search/stats

Get search and embedding statistics.

**Response:**
```json
{
  "total_documents": 150,
  "total_embeddings": 1234,
  "avg_tokens_per_chunk": 456,
  "total_tokens": 563904
}
```

## Performance Optimization

### 1. Text Chunking Strategy

**Optimal Chunk Size:**
- Default: 8,091 tokens (leaving 100 token buffer)
- Overlap: 200 tokens for context preservation
- Sentence-based splitting for better coherence

**Chunking Code:**
```python
chunker = TextChunker(model="text-embedding-3-small")

chunks = chunker.chunk_text(
    text=document_text,
    chunk_size=8000,
    overlap=200
)

# Each chunk includes:
# - text: Chunk content
# - chunk_index: Position in document
# - tokens: Token count
# - start_char/end_char: Character positions
```

### 2. Caching Strategy

**Embedding Cache:**
- **Storage**: Redis
- **Key Format**: `embedding:{model}:{text_hash}`
- **TTL**: 7 days
- **Benefits**: Avoid re-computing same text

**Search Cache:**
- **Storage**: Redis
- **Key Format**: `search:{query_hash}`
- **TTL**: 5 minutes
- **Benefits**: Fast responses for common queries

**Cache Hit Rates:**
- Embeddings: 60-80% for frequently accessed documents
- Search: 30-50% for popular queries

### 3. Index Optimization

**IVFFlat Index:**
```sql
CREATE INDEX idx_embeddings_vector_ivfflat
ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**Index Parameters:**
- `lists`: Number of clusters (default: 100)
- Higher lists = more memory, slower build, faster search
- Recommended: ~sqrt(total_rows)

**HNSW Index (Alternative):**
```sql
-- More accurate, slightly slower
CREATE INDEX idx_embeddings_vector_hnsw
ON embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

### 4. Query Performance

**Semantic Search:**
- Average: 200-300ms
- Includes: Embedding generation (150ms) + Vector search (50-100ms)

**Hybrid Search:**
- Average: 300-400ms
- Includes: Vector search + Full-text search + Score combining

**Optimization Tips:**
1. Use caching for repeated queries
2. Adjust `similarity_threshold` to reduce result set
3. Limit results to necessary count
4. Use filters to reduce search space
5. Monitor index usage with `pg_stat_user_indexes`

## Cost Management

### Embedding Costs

**Pricing (as of 2024):**
- `text-embedding-3-small`: $0.02 per 1M tokens
- `text-embedding-3-large`: $0.13 per 1M tokens

**Average Costs:**
- Short query (10 tokens): $0.0000002
- Medium document (1,000 tokens): $0.00002
- Long document (10,000 tokens): $0.0002

**Monthly Cost Estimates:**

| Usage Pattern | Documents/Month | Searches/Month | Cost |
|--------------|-----------------|----------------|------|
| Light | 100 | 1,000 | $0.50 |
| Medium | 1,000 | 10,000 | $5.00 |
| Heavy | 10,000 | 100,000 | $50.00 |

### Cost Optimization

1. **Use Smaller Model**: `text-embedding-3-small` is 6.5x cheaper than large
2. **Enable Caching**: Avoid re-embedding same content (60-80% savings)
3. **Batch Operations**: Process multiple texts together
4. **Chunk Intelligently**: Optimize chunk size to balance accuracy and cost
5. **Cache Search Results**: Reduce query embedding costs

**Cost Tracking:**
```python
# Get cost report
cost_report = embedding_service.get_cost_report()

# {
#   "total_cost": 0.0234,
#   "total_tokens": 12000,
#   "total_embeddings": 50,
#   "average_cost_per_embedding": 0.000468,
#   "costs_by_model": {
#     "text-embedding-3-small": 0.0234
#   }
# }
```

## Monitoring

### Database Queries

**Check Embedding Count:**
```sql
SELECT
    COUNT(*) as total_embeddings,
    COUNT(DISTINCT document_id) as documents_with_embeddings,
    AVG(tokens) as avg_tokens
FROM embeddings;
```

**Check Index Usage:**
```sql
SELECT
    indexname,
    idx_scan as scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE tablename = 'embeddings'
ORDER BY idx_scan DESC;
```

**Check Table Size:**
```sql
SELECT
    pg_size_pretty(pg_total_relation_size('embeddings')) AS total_size,
    pg_size_pretty(pg_relation_size('embeddings')) AS table_size,
    pg_size_pretty(
        pg_total_relation_size('embeddings') - pg_relation_size('embeddings')
    ) AS indexes_size;
```

### Application Metrics

**Key Metrics:**
- Embedding generation time
- Search latency
- Cache hit rate
- Cost per query
- Token usage
- Error rate

**Logging:**
```python
# Automatically logged:
logger.info("Generated embedding: 500 tokens, $0.00001, 0.15s")
logger.info("Semantic search: 5 results, 0.23s")
logger.info("Embedding cache hit")
```

## Troubleshooting

### Common Issues

**1. "Extension vector does not exist"**
```sql
-- Solution: Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
```

**2. "Rate limit exceeded"**
```python
# Solution: Rate limiter handles this automatically
# Wait time logged: "Rate limit reached, waiting 5.2s"
```

**3. "Cache connection failed"**
```bash
# Solution: Check Redis connection
redis-cli ping
# Should return: PONG
```

**4. "Embedding generation timeout"**
```python
# Solution: Increase timeout in OpenAI client
client = AsyncOpenAI(timeout=120.0)  # 2 minutes
```

**5. "Out of memory during indexing"**
```sql
-- Solution: Reduce maintenance_work_mem temporarily
SET maintenance_work_mem = '1GB';
CREATE INDEX ...;
```

**6. "Slow search performance"**
```sql
-- Solution: Analyze tables and rebuild indexes
ANALYZE embeddings;
REINDEX INDEX idx_embeddings_vector_ivfflat;
```

### Debug Mode

```python
import logging

# Enable debug logging
logging.getLogger("app.services.embedding_service").setLevel(logging.DEBUG)
logging.getLogger("app.services.vector_search").setLevel(logging.DEBUG)

# Detailed logs:
# DEBUG: Embedding cache hit for 1234 chars
# DEBUG: Chunked text into 5 chunks (12000 total tokens)
# DEBUG: Generated embedding: 500 tokens, $0.00001, 0.15s
```

## Best Practices

### 1. Embedding Generation

- ✅ Use `text-embedding-3-small` for most use cases
- ✅ Enable caching to reduce costs
- ✅ Batch process when possible
- ✅ Chunk long documents appropriately
- ❌ Don't embed very short texts (<10 words)
- ❌ Don't disable caching in production

### 2. Search Queries

- ✅ Use descriptive, natural language queries
- ✅ Adjust similarity threshold based on needs
- ✅ Use filters to narrow search scope
- ✅ Cache frequent queries
- ❌ Don't use very generic queries
- ❌ Don't set threshold too low (< 0.5)

### 3. Index Management

- ✅ Rebuild indexes periodically
- ✅ Monitor index usage and size
- ✅ Use IVFFlat for large datasets (>100k rows)
- ✅ Run ANALYZE after bulk inserts
- ❌ Don't create too many indexes
- ❌ Don't forget to VACUUM

### 4. Cost Management

- ✅ Monitor monthly costs
- ✅ Set budget alerts
- ✅ Use caching aggressively
- ✅ Track cost per user/document
- ❌ Don't re-embed unchanged content
- ❌ Don't use large model unnecessarily

## Migration Guide

### From Keyword Search

1. **Run Migration Script**: `init_vector_search.sql`
2. **Generate Embeddings**: For existing documents
3. **Update Search Endpoints**: Switch to vector search
4. **Test Performance**: Compare with keyword search
5. **Monitor Costs**: Track embedding costs

### Bulk Embedding Generation

```python
from app.services.document_processor import DocumentProcessor
from app.services.embedding_service import EmbeddingService
from app.services.vector_search import VectorSearch

# Initialize services
embedding_service = EmbeddingService()
vector_search = VectorSearch()

# Get all documents without embeddings
documents = await execute_select(
    "documents",
    columns="id, extracted_text, user_id",
    # Add your filters here
)

# Process in batches
batch_size = 10

for i in range(0, len(documents), batch_size):
    batch = documents[i:i + batch_size]

    for doc in batch:
        # Generate embeddings
        result = await embedding_service.generate_embeddings(
            text=doc["extracted_text"],
            use_cache=False
        )

        # Store embeddings
        await vector_search.store_document_embeddings(
            document_id=doc["id"],
            embeddings=result["embeddings"],
            user_id=doc["user_id"]
        )

        print(f"Processed document {doc['id']}: {result['total_cost']:.6f} USD")

    # Wait between batches to respect rate limits
    await asyncio.sleep(1)
```

## Future Enhancements

Planned features:
- [ ] Support for multiple embedding models simultaneously
- [ ] Automatic model selection based on query
- [ ] Custom fine-tuned embeddings
- [ ] Multilingual support
- [ ] Image embedding integration
- [ ] Incremental index updates
- [ ] Query expansion and rewriting
- [ ] Personalized search rankings

## References

- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- [PostgreSQL Full-Text Search](https://www.postgresql.org/docs/current/textsearch.html)
- [Vector Search Best Practices](https://www.pinecone.io/learn/vector-search/)
