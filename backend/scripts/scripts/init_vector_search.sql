-- ============================================================================
-- Vector Search Database Migration for PM Document Intelligence
-- ============================================================================
--
-- This migration adds vector search capabilities using pgvector extension.
--
-- Features:
-- - Enable pgvector extension
-- - Create embeddings table with vector column
-- - Create indexes for fast similarity search
-- - Add full-text search capabilities
-- - Create helper functions and views
--
-- Prerequisites:
-- - PostgreSQL 12+
-- - pgvector extension installed
-- - Supabase database initialized
--
-- Usage:
--   Execute this script in your Supabase SQL editor or via psql:
--   psql -U postgres -d your_database -f init_vector_search.sql
--
-- ============================================================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify extension
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

COMMENT ON EXTENSION vector IS 'Vector similarity search using pgvector';


-- ============================================================================
-- Embeddings Table
-- ============================================================================

-- Create embeddings table for storing document chunk embeddings
CREATE TABLE IF NOT EXISTS embeddings (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign keys
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Vector embedding (1536 dimensions for text-embedding-3-small)
    -- Note: Can be 3072 for text-embedding-3-large
    embedding VECTOR(1536) NOT NULL,

    -- Chunk information
    chunk_index INTEGER NOT NULL DEFAULT 0,
    chunk_text TEXT NOT NULL,
    tokens INTEGER NOT NULL DEFAULT 0,
    start_char INTEGER NOT NULL DEFAULT 0,
    end_char INTEGER NOT NULL DEFAULT 0,

    -- Model information
    model VARCHAR(100) NOT NULL DEFAULT 'text-embedding-3-small',
    dimensions INTEGER NOT NULL DEFAULT 1536,

    -- Metadata (JSONB for flexible schema)
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT embeddings_chunk_index_check CHECK (chunk_index >= 0),
    CONSTRAINT embeddings_tokens_check CHECK (tokens >= 0),
    CONSTRAINT embeddings_dimensions_check CHECK (dimensions > 0)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_embeddings_document_id ON embeddings(document_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_user_id ON embeddings(user_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_created_at ON embeddings(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_embeddings_chunk_index ON embeddings(document_id, chunk_index);

-- Create vector similarity search indexes
-- IVFFlat index for approximate nearest neighbor search (faster, less accurate)
CREATE INDEX IF NOT EXISTS idx_embeddings_vector_ivfflat
ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Note: For HNSW index (more accurate, slightly slower), use:
-- CREATE INDEX idx_embeddings_vector_hnsw
-- ON embeddings
-- USING hnsw (embedding vector_cosine_ops)
-- WITH (m = 16, ef_construction = 64);

-- Full-text search index on chunk_text
CREATE INDEX IF NOT EXISTS idx_embeddings_chunk_text_fts
ON embeddings
USING GIN (to_tsvector('english', chunk_text));

-- Metadata index
CREATE INDEX IF NOT EXISTS idx_embeddings_metadata ON embeddings USING GIN (metadata);

-- Composite index for user + document lookups
CREATE INDEX IF NOT EXISTS idx_embeddings_user_document
ON embeddings(user_id, document_id);

-- Add comments
COMMENT ON TABLE embeddings IS 'Document chunk embeddings for semantic search';
COMMENT ON COLUMN embeddings.embedding IS 'Vector embedding from OpenAI (1536 or 3072 dimensions)';
COMMENT ON COLUMN embeddings.chunk_text IS 'Text chunk that was embedded';
COMMENT ON COLUMN embeddings.chunk_index IS 'Index of chunk within document (0-based)';
COMMENT ON COLUMN embeddings.tokens IS 'Number of tokens in chunk';
COMMENT ON INDEX idx_embeddings_vector_ivfflat IS 'IVFFlat index for fast approximate vector similarity search';


-- ============================================================================
-- Trigger for updated_at
-- ============================================================================

-- Create trigger function if not exists
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS update_embeddings_updated_at ON embeddings;
CREATE TRIGGER update_embeddings_updated_at
    BEFORE UPDATE ON embeddings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- Full-Text Search on Documents
-- ============================================================================

-- Add full-text search index to documents table if not exists
CREATE INDEX IF NOT EXISTS idx_documents_extracted_text_fts
ON documents
USING GIN (to_tsvector('english', extracted_text));

COMMENT ON INDEX idx_documents_extracted_text_fts IS 'Full-text search index on document text';


-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Function to calculate cosine similarity
CREATE OR REPLACE FUNCTION cosine_similarity(a VECTOR, b VECTOR)
RETURNS FLOAT AS $$
BEGIN
    RETURN 1 - (a <=> b);
END;
$$ LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE;

COMMENT ON FUNCTION cosine_similarity IS 'Calculate cosine similarity between two vectors (returns 0-1)';


-- Function to find similar embeddings
CREATE OR REPLACE FUNCTION find_similar_embeddings(
    query_embedding VECTOR,
    similarity_threshold FLOAT DEFAULT 0.7,
    max_results INTEGER DEFAULT 10,
    filter_user_id UUID DEFAULT NULL,
    filter_document_type VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    document_id UUID,
    chunk_text TEXT,
    similarity_score FLOAT,
    chunk_index INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.document_id,
        e.chunk_text,
        (1 - (e.embedding <=> query_embedding))::FLOAT AS similarity_score,
        e.chunk_index
    FROM embeddings e
    INNER JOIN documents d ON e.document_id = d.id
    WHERE
        (1 - (e.embedding <=> query_embedding)) >= similarity_threshold
        AND (filter_user_id IS NULL OR e.user_id = filter_user_id)
        AND (filter_document_type IS NULL OR d.document_type = filter_document_type)
    ORDER BY similarity_score DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_similar_embeddings IS 'Find embeddings similar to query vector with optional filters';


-- Function to get document embeddings count
CREATE OR REPLACE FUNCTION get_document_embeddings_count(doc_id UUID)
RETURNS INTEGER AS $$
DECLARE
    count INTEGER;
BEGIN
    SELECT COUNT(*) INTO count
    FROM embeddings
    WHERE document_id = doc_id;

    RETURN count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_document_embeddings_count IS 'Get number of embeddings for a document';


-- ============================================================================
-- Views
-- ============================================================================

-- View: Document embedding statistics
CREATE OR REPLACE VIEW document_embedding_stats AS
SELECT
    d.id AS document_id,
    d.filename,
    d.user_id,
    d.document_type,
    COUNT(e.id) AS embedding_count,
    AVG(e.tokens) AS avg_tokens_per_chunk,
    SUM(e.tokens) AS total_tokens,
    MIN(e.created_at) AS first_embedding_created,
    MAX(e.created_at) AS last_embedding_created
FROM documents d
LEFT JOIN embeddings e ON d.id = e.document_id
GROUP BY d.id, d.filename, d.user_id, d.document_type;

COMMENT ON VIEW document_embedding_stats IS 'Statistics about embeddings per document';


-- View: User embedding statistics
CREATE OR REPLACE VIEW user_embedding_stats AS
SELECT
    u.id AS user_id,
    u.email,
    COUNT(DISTINCT e.document_id) AS documents_with_embeddings,
    COUNT(e.id) AS total_embeddings,
    AVG(e.tokens) AS avg_tokens_per_chunk,
    SUM(e.tokens) AS total_tokens,
    -- Estimate cost (assuming text-embedding-3-small at $0.02 per 1M tokens)
    ROUND((SUM(e.tokens) / 1000000.0 * 0.02)::NUMERIC, 4) AS estimated_cost_usd
FROM users u
LEFT JOIN embeddings e ON u.id = e.user_id
GROUP BY u.id, u.email;

COMMENT ON VIEW user_embedding_stats IS 'Embedding statistics and cost estimates per user';


-- ============================================================================
-- Row Level Security (RLS)
-- ============================================================================

-- Enable RLS on embeddings table
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own embeddings
CREATE POLICY embeddings_select_own
    ON embeddings
    FOR SELECT
    USING (user_id = auth.uid());

-- Policy: Users can insert their own embeddings
CREATE POLICY embeddings_insert_own
    ON embeddings
    FOR INSERT
    WITH CHECK (user_id = auth.uid());

-- Policy: Users can update their own embeddings
CREATE POLICY embeddings_update_own
    ON embeddings
    FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Policy: Users can delete their own embeddings
CREATE POLICY embeddings_delete_own
    ON embeddings
    FOR DELETE
    USING (user_id = auth.uid());

-- Policy: Admins can see all embeddings
CREATE POLICY embeddings_select_admin
    ON embeddings
    FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.role = 'admin'
        )
    );

COMMENT ON POLICY embeddings_select_own ON embeddings IS 'Users can only view their own embeddings';
COMMENT ON POLICY embeddings_select_admin ON embeddings IS 'Admins can view all embeddings';


-- ============================================================================
-- Sample Queries
-- ============================================================================

-- Example 1: Semantic search
/*
WITH query_embedding AS (
    SELECT '{{embedding_vector}}'::VECTOR AS embedding
)
SELECT
    e.document_id,
    d.filename,
    e.chunk_text,
    1 - (e.embedding <=> q.embedding) AS similarity_score
FROM embeddings e
CROSS JOIN query_embedding q
INNER JOIN documents d ON e.document_id = d.id
WHERE (1 - (e.embedding <=> q.embedding)) > 0.7
ORDER BY similarity_score DESC
LIMIT 10;
*/

-- Example 2: Find similar documents
/*
SELECT
    d1.id,
    d1.filename,
    AVG(1 - (e1.embedding <=> e2.embedding)) AS avg_similarity
FROM embeddings e1
INNER JOIN embeddings e2 ON e1.document_id != e2.document_id
INNER JOIN documents d1 ON e2.document_id = d1.id
WHERE e1.document_id = 'source_document_id'
GROUP BY d1.id, d1.filename
HAVING AVG(1 - (e1.embedding <=> e2.embedding)) > 0.75
ORDER BY avg_similarity DESC
LIMIT 5;
*/

-- Example 3: Hybrid search (vector + keyword)
/*
WITH query_embedding AS (
    SELECT '{{embedding_vector}}'::VECTOR AS embedding
),
vector_scores AS (
    SELECT
        e.document_id,
        MAX(1 - (e.embedding <=> q.embedding)) AS vector_score
    FROM embeddings e
    CROSS JOIN query_embedding q
    GROUP BY e.document_id
),
keyword_scores AS (
    SELECT
        d.id AS document_id,
        ts_rank(
            to_tsvector('english', d.extracted_text),
            plainto_tsquery('english', 'your search query')
        ) AS keyword_score
    FROM documents d
    WHERE to_tsvector('english', d.extracted_text)
        @@ plainto_tsquery('english', 'your search query')
)
SELECT
    d.id,
    d.filename,
    COALESCE(vs.vector_score, 0) * 0.7 + COALESCE(ks.keyword_score, 0) * 0.3 AS combined_score
FROM documents d
LEFT JOIN vector_scores vs ON d.id = vs.document_id
LEFT JOIN keyword_scores ks ON d.id = ks.document_id
WHERE (vs.vector_score IS NOT NULL OR ks.keyword_score IS NOT NULL)
ORDER BY combined_score DESC
LIMIT 10;
*/


-- ============================================================================
-- Performance Optimization
-- ============================================================================

-- Analyze tables for query planner
ANALYZE embeddings;
ANALYZE documents;

-- Vacuum tables to reclaim storage
VACUUM ANALYZE embeddings;


-- ============================================================================
-- Monitoring Queries
-- ============================================================================

-- Check index usage
/*
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'embeddings'
ORDER BY idx_scan DESC;
*/

-- Check table size
/*
SELECT
    pg_size_pretty(pg_total_relation_size('embeddings')) AS total_size,
    pg_size_pretty(pg_relation_size('embeddings')) AS table_size,
    pg_size_pretty(pg_total_relation_size('embeddings') - pg_relation_size('embeddings')) AS indexes_size;
*/

-- Check vector index statistics
/*
SELECT
    indexrelname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE indexrelname LIKE '%vector%';
*/


-- ============================================================================
-- Cleanup (Optional - for development/testing)
-- ============================================================================

-- To drop all vector search objects:
/*
DROP VIEW IF EXISTS user_embedding_stats CASCADE;
DROP VIEW IF EXISTS document_embedding_stats CASCADE;
DROP FUNCTION IF EXISTS get_document_embeddings_count CASCADE;
DROP FUNCTION IF EXISTS find_similar_embeddings CASCADE;
DROP FUNCTION IF EXISTS cosine_similarity CASCADE;
DROP TABLE IF EXISTS embeddings CASCADE;
DROP EXTENSION IF EXISTS vector CASCADE;
*/


-- ============================================================================
-- Migration Complete
-- ============================================================================

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'Vector search migration completed successfully!';
    RAISE NOTICE 'pgvector extension: %', (SELECT extversion FROM pg_extension WHERE extname = 'vector');
    RAISE NOTICE 'Embeddings table created with indexes';
    RAISE NOTICE 'Row Level Security enabled';
    RAISE NOTICE 'Helper functions and views created';
END $$;

-- Show statistics
SELECT
    'embeddings' AS table_name,
    COUNT(*) AS row_count
FROM embeddings
UNION ALL
SELECT
    'documents with embeddings',
    COUNT(DISTINCT document_id)
FROM embeddings;
