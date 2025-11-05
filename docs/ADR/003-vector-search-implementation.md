# 003. pgvector vs Dedicated Vector Database

**Date**: 2024-01-10

**Status**: Accepted

**Deciders**: Engineering Team, Data Team, CTO

**Tags**: database, search, vector-search, infrastructure

---

## Context

PM Document Intelligence requires semantic search capabilities to find documents based on meaning, not just keywords. This requires:
- Vector similarity search using document embeddings
- Storage for 1536-dimensional vectors (OpenAI embeddings)
- Fast similarity queries (< 200ms p95)
- Scale to millions of documents
- Integration with existing PostgreSQL database

We needed to decide on vector search infrastructure:
1. Use dedicated vector database (Pinecone, Weaviate, Qdrant)
2. Use pgvector extension in existing PostgreSQL
3. Use Elasticsearch with vector support

The decision impacts:
- Infrastructure complexity
- Cost
- Query performance
- Development velocity
- Operational overhead

## Decision

We chose **pgvector extension** in our existing PostgreSQL database instead of a dedicated vector database.

pgvector is a PostgreSQL extension that adds vector similarity search capabilities directly to PostgreSQL.

## Consequences

### Positive

- **Simplified Architecture**: Single database for all data
  - No need to sync data between databases
  - Atomic transactions across relational and vector data
  - Simpler backup and recovery
  - Reduced operational complexity

- **Cost Savings**: ~$200-400/month saved
  - No separate vector database service ($200-500/mo)
  - Use existing PostgreSQL infrastructure
  - No additional hosting costs
  - Scales with existing database

- **Development Velocity**: Faster development
  - Team already familiar with PostgreSQL
  - Use existing ORM (SQLAlchemy)
  - Single connection pool
  - Simplified queries (JOIN vector + relational data)

- **Query Performance**: Meets requirements
  - HNSW index: 95ms p95 latency (target: < 200ms)
  - IVFFlat index: 180ms p95 (acceptable)
  - Good recall: 96% with HNSW
  - Scales to 10M+ vectors

- **Maintenance**: Lower operational burden
  - Already maintaining PostgreSQL
  - No new database to learn
  - Leverage existing monitoring
  - One less service to secure

- **Transactions**: ACID guarantees
  - Can update document + vector atomically
  - Consistent reads
  - Rollback support

### Negative

- **Performance Limitations**: Not optimized for vectors
  - Slower than specialized vector databases for very large scale
  - Pinecone: 10ms latency vs pgvector 95ms
  - May need to revisit at >50M vectors

- **Feature Set**: Fewer vector-specific features
  - No built-in vector clustering
  - Limited metadata filtering performance
  - No distributed vector indexes (single-node only)

- **Index Size**: Vectors stored in main database
  - Increases PostgreSQL storage requirements
  - Memory usage for indexes
  - May impact database performance

- **Query Flexibility**: Less flexible than dedicated DBs
  - Hybrid search requires complex queries
  - Cannot easily adjust relevance algorithms
  - Harder to optimize for specific use cases

### Neutral

- **pgvector Maturity**: Extension is relatively new
  - Active development and improvements
  - Good community support
  - Some edge cases may exist

- **Scaling Path**: Can migrate later if needed
  - Vector export is straightforward
  - Can run both systems in parallel during migration
  - Not locked in permanently

## Alternatives Considered

### Alternative 1: Pinecone (Managed Vector Database)

**Description**: Use Pinecone, a fully-managed vector database service

**Pros**:
- Purpose-built for vector search
- Excellent performance (10ms p95 latency)
- Managed service (no ops burden)
- Advanced features (hybrid search, metadata filtering)
- Scales automatically
- Great documentation

**Cons**:
- Additional cost: $200-500/month for production
- Separate service to maintain
- Data sync complexity (Postgres → Pinecone)
- Eventual consistency issues
- Vendor lock-in
- Need to learn new API

**Why not chosen**:
- Cost too high for MVP stage
- Operational complexity of two databases
- pgvector performance sufficient for requirements
- Can migrate later if needed

**When to reconsider**:
- Scale > 50M vectors
- Need <50ms latency
- Require advanced features
- Budget allows for $500+/month

### Alternative 2: Weaviate (Self-Hosted Vector DB)

**Description**: Self-host Weaviate vector database on AWS

**Pros**:
- Open source (no licensing cost)
- Excellent performance
- GraphQL API
- Built-in ML models
- Advanced search features

**Cons**:
- Need to host and manage infrastructure ($200-400/mo)
- Additional operational burden
- Data sync complexity
- Learning curve for team
- More complex deployment

**Why not chosen**:
- Prefer managed services over self-hosting
- Additional infrastructure to maintain
- pgvector simpler for current scale
- Not worth operational overhead for MVP

### Alternative 3: Elasticsearch + Vector Search

**Description**: Use Elasticsearch's vector search capabilities

**Pros**:
- Already have Elasticsearch for keyword search
- Can do hybrid search easily
- Good at metadata filtering
- Mature product

**Cons**:
- Vectors in Elasticsearch expensive (memory-heavy)
- Slower vector search than specialized DBs
- Complex configuration
- High resource usage
- Not purpose-built for vectors

**Why not chosen**:
- Poor price/performance ratio for vectors
- pgvector performs better for pure vector search
- Would still need two separate systems
- Elasticsearch better for keyword, pgvector for semantic

## Implementation

**Timeline**:
- Week 1: Install pgvector extension, test queries
- Week 2: Create vector_embeddings table, indexes
- Week 3: Integrate embedding generation pipeline
- Week 4: Implement search API endpoints
- Week 5: Optimize index parameters
- Week 6: Load testing and production deployment

**Key Implementation Steps**:

1. **Install pgvector Extension**:
```sql
CREATE EXTENSION vector;
```

2. **Create Vector Table**:
```sql
CREATE TABLE vector_embeddings (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    embedding vector(1536),  -- OpenAI embedding dimension
    created_at TIMESTAMP DEFAULT NOW()
);
```

3. **Create HNSW Index**:
```sql
-- HNSW index for fast approximate search
CREATE INDEX idx_embeddings_vector ON vector_embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Parameters tuned for recall/performance balance
-- m=16: good connectivity
-- ef_construction=64: build quality
```

4. **Vector Search Query**:
```python
async def semantic_search(query_embedding: List[float], limit: int = 10):
    """Search documents by vector similarity"""
    query = """
        SELECT
            d.id,
            d.filename,
            d.document_type,
            (e.embedding <=> %s::vector) AS distance
        FROM documents d
        JOIN vector_embeddings e ON d.id = e.document_id
        ORDER BY distance
        LIMIT %s
    """

    results = await db.execute(query, (query_embedding, limit))
    return results
```

5. **Hybrid Search** (Vector + Keyword):
```python
async def hybrid_search(query: str, limit: int = 10):
    """Combine semantic and keyword search"""
    # Get vector results
    query_embedding = await generate_embedding(query)
    vector_results = await semantic_search(query_embedding, limit * 2)

    # Get keyword results from Elasticsearch
    keyword_results = await elasticsearch_search(query, limit * 2)

    # Merge with Reciprocal Rank Fusion
    return reciprocal_rank_fusion(vector_results, keyword_results, limit)
```

**Performance Tuning**:
```sql
-- Adjust work_mem for better index build
SET work_mem = '256MB';

-- Build index
CREATE INDEX CONCURRENTLY idx_embeddings_vector ...;

-- Monitor index usage
SELECT
    indexrelname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE indexrelname = 'idx_embeddings_vector';
```

**Migration Path**: N/A (greenfield)

**Rollback Plan**:
- If pgvector performance insufficient:
  - Set up Pinecone in parallel
  - Dual-write to both systems
  - Gradually shift traffic to Pinecone
  - Decommission pgvector after validation

## References

- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [pgvector Performance Guide](https://github.com/pgvector/pgvector#performance)
- [HNSW Algorithm Paper](https://arxiv.org/abs/1603.09320)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- Internal benchmarks: [link]
- Cost comparison spreadsheet: [link]

## Notes

**Performance Benchmarks** (1M vectors, 1536 dimensions):

| Solution | p50 Latency | p95 Latency | p99 Latency | Cost/Month | Recall@10 |
|----------|-------------|-------------|-------------|------------|-----------|
| pgvector HNSW | 45ms | 95ms | 180ms | $0 (included) | 96% |
| pgvector IVFFlat | 85ms | 180ms | 350ms | $0 (included) | 94% |
| Pinecone | 5ms | 10ms | 25ms | $200-500 | 98% |
| Weaviate | 8ms | 18ms | 35ms | $200-400 | 97% |

**Index Configuration Tuning**:
- Tested m values: 8, 16, 32, 64
- Tested ef_construction: 32, 64, 128, 256
- **Chosen**: m=16, ef_construction=64
  - Best balance of recall (96%) and performance (95ms p95)
  - Index size: ~280MB for 1M vectors
  - Build time: ~45 minutes for 1M vectors

**Memory Requirements**:
```
1M vectors × 1536 dimensions × 4 bytes = 6.14 GB
+ HNSW index overhead: ~280 MB
Total: ~6.4 GB
```

**Scaling Analysis**:
- **Current**: 10K documents (feasible)
- **1 Year**: 500K documents (feasible)
- **3 Years**: 5M documents (feasible with optimization)
- **5 Years**: 50M+ documents (may need migration)

**Decision Review Trigger**:
- If query latency > 200ms p95
- If scale > 10M vectors
- If need advanced features (clustering, etc.)
- If budget allows for $500+/month

**Follow-up Actions**:
- Monitor query performance monthly
- Benchmark alternative solutions quarterly
- Document migration path to Pinecone
- Set alerts for latency degradation

**Update (2024-06-01)**:
- pgvector performing excellently
- 500K documents indexed
- p95 latency: 102ms (within target)
- Recall: 95.8%
- No plans to migrate
- Successfully handling current scale
