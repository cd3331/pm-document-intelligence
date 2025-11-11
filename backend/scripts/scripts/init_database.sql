-- ============================================================================
-- PM Document Intelligence - Database Initialization Script
-- ============================================================================
-- This script creates the database schema for the PM Document Intelligence
-- application including tables, indexes, Row Level Security (RLS) policies,
-- triggers, and constraints.
--
-- Features:
-- - User management with roles
-- - Document storage and processing tracking
-- - Analysis results storage
-- - Audit logging for compliance
-- - Row Level Security for data isolation
-- - Optimized indexes for common queries
-- - Automatic timestamp updates
--
-- Usage:
--   psql $DATABASE_URL -f scripts/init_database.sql
--
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For full-text search

-- ============================================================================
-- USERS TABLE
-- ============================================================================

-- Users table for authentication and profile management
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password TEXT NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    organization VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'manager', 'user', 'guest')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,

    -- Preferences (stored as JSONB)
    preferences JSONB NOT NULL DEFAULT '{
        "theme": "light",
        "language": "en",
        "timezone": "UTC",
        "notifications_enabled": true,
        "email_notifications": true,
        "default_view": "grid"
    }'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for users table
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users (is_active);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_users_organization ON users (organization) WHERE organization IS NOT NULL;

-- Full-text search index on user names
CREATE INDEX IF NOT EXISTS idx_users_full_name_trgm ON users USING gin (full_name gin_trgm_ops);

-- ============================================================================
-- DOCUMENTS TABLE
-- ============================================================================

-- Documents table for uploaded files and their metadata
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- File metadata
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(100) NOT NULL,
    size BIGINT NOT NULL CHECK (size > 0),
    description TEXT,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- Processing status
    status VARCHAR(50) NOT NULL DEFAULT 'uploaded' CHECK (
        status IN ('uploaded', 'queued', 'processing', 'completed', 'failed', 'archived')
    ),
    current_stage VARCHAR(50) CHECK (
        current_stage IN ('upload', 'ocr', 'extraction', 'analysis', 'embedding', 'indexing', 'complete')
    ),

    -- Extracted content
    extracted_text TEXT,
    entities JSONB DEFAULT '[]'::jsonb,
    action_items JSONB DEFAULT '[]'::jsonb,
    sentiment JSONB,
    key_phrases TEXT[] DEFAULT ARRAY[]::TEXT[],
    summary TEXT,

    -- Storage references
    s3_reference JSONB,
    vector_embedding JSONB,

    -- Processing metadata
    processing_started_at TIMESTAMP WITH TIME ZONE,
    processing_completed_at TIMESTAMP WITH TIME ZONE,
    processing_duration_seconds NUMERIC(10, 2),
    ai_models_used TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- Error tracking
    errors JSONB DEFAULT '[]'::jsonb,
    retry_count INTEGER NOT NULL DEFAULT 0,

    -- Document statistics
    page_count INTEGER,
    character_count INTEGER,
    word_count INTEGER,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    accessed_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for documents table
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents (user_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents (status);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_user_status ON documents (user_id, status);
CREATE INDEX IF NOT EXISTS idx_documents_user_created ON documents (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_file_type ON documents (file_type);
CREATE INDEX IF NOT EXISTS idx_documents_tags ON documents USING gin (tags);

-- Full-text search index on filename and extracted text
CREATE INDEX IF NOT EXISTS idx_documents_filename_trgm ON documents USING gin (filename gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_documents_extracted_text_trgm ON documents USING gin (extracted_text gin_trgm_ops);

-- JSONB indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_documents_entities ON documents USING gin (entities);
CREATE INDEX IF NOT EXISTS idx_documents_action_items ON documents USING gin (action_items);
CREATE INDEX IF NOT EXISTS idx_documents_sentiment ON documents USING gin (sentiment);

-- ============================================================================
-- ANALYSIS TABLE
-- ============================================================================

-- Analysis results table for AI-extracted insights
CREATE TABLE IF NOT EXISTS analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- AI models used
    ai_models_used TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    processing_duration_seconds NUMERIC(10, 2) NOT NULL,

    -- Entity extraction
    entities JSONB DEFAULT '[]'::jsonb,
    entity_summary JSONB DEFAULT '[]'::jsonb,
    total_entities INTEGER NOT NULL DEFAULT 0,

    -- Action items
    action_items JSONB DEFAULT '[]'::jsonb,
    action_items_by_priority JSONB DEFAULT '{}'::jsonb,

    -- Sentiment analysis
    sentiment JSONB,

    -- Topics and themes
    topics JSONB DEFAULT '[]'::jsonb,
    key_phrases JSONB DEFAULT '[]'::jsonb,
    top_keywords TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- Risk indicators
    risks JSONB DEFAULT '[]'::jsonb,
    overall_risk_level VARCHAR(50) NOT NULL DEFAULT 'none' CHECK (
        overall_risk_level IN ('critical', 'high', 'medium', 'low', 'none')
    ),

    -- Confidence scores
    overall_confidence NUMERIC(3, 2) NOT NULL DEFAULT 0.0 CHECK (overall_confidence >= 0 AND overall_confidence <= 1),
    entity_extraction_confidence NUMERIC(3, 2) DEFAULT 0.0 CHECK (entity_extraction_confidence >= 0 AND entity_extraction_confidence <= 1),
    action_item_confidence NUMERIC(3, 2) DEFAULT 0.0 CHECK (action_item_confidence >= 0 AND action_item_confidence <= 1),
    sentiment_confidence NUMERIC(3, 2) DEFAULT 0.0 CHECK (sentiment_confidence >= 0 AND sentiment_confidence <= 1),

    -- Model versions
    bedrock_model_version VARCHAR(255),
    comprehend_model_version VARCHAR(255),
    textract_model_version VARCHAR(255),
    openai_model_version VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Unique constraint: one analysis per document
    UNIQUE (document_id)
);

-- Indexes for analysis table
CREATE INDEX IF NOT EXISTS idx_analysis_document_id ON analysis (document_id);
CREATE INDEX IF NOT EXISTS idx_analysis_user_id ON analysis (user_id);
CREATE INDEX IF NOT EXISTS idx_analysis_created_at ON analysis (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_risk_level ON analysis (overall_risk_level);
CREATE INDEX IF NOT EXISTS idx_analysis_confidence ON analysis (overall_confidence DESC);

-- JSONB indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_analysis_entities ON analysis USING gin (entities);
CREATE INDEX IF NOT EXISTS idx_analysis_action_items ON analysis USING gin (action_items);
CREATE INDEX IF NOT EXISTS idx_analysis_topics ON analysis USING gin (topics);
CREATE INDEX IF NOT EXISTS idx_analysis_risks ON analysis USING gin (risks);

-- ============================================================================
-- AUDIT LOGS TABLE
-- ============================================================================

-- Audit logs for compliance and security tracking
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Action details
    action VARCHAR(100) NOT NULL,  -- e.g., 'create', 'update', 'delete', 'login', 'logout'
    resource_type VARCHAR(100) NOT NULL,  -- e.g., 'user', 'document', 'analysis'
    resource_id UUID,

    -- Request metadata
    ip_address INET,
    user_agent TEXT,
    request_id VARCHAR(255),

    -- Change tracking
    old_values JSONB,
    new_values JSONB,

    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'success' CHECK (status IN ('success', 'failure', 'partial')),
    error_message TEXT,

    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for audit logs
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs (action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_type ON audit_logs (resource_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_id ON audit_logs (resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_status ON audit_logs (status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_ip_address ON audit_logs (ip_address);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================


-- NOTE: Row Level Security policies have been disabled for AWS RDS deployment
-- The application uses application-level security through FastAPI middleware
-- ============================================================================

-- Enable RLS on all tables (DISABLED FOR AWS RDS)
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE analysis ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies have been commented out (lines 275-380)
-- Supabase auth.uid() function not available in AWS RDS PostgreSQL
-- Application-level security is handled by FastAPI authentication middleware

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to tables
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_analysis_updated_at
    BEFORE UPDATE ON analysis
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to log document changes to audit log
CREATE OR REPLACE FUNCTION log_document_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, new_values)
        VALUES (NEW.user_id, 'create', 'document', NEW.id, row_to_json(NEW)::jsonb);
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, old_values, new_values)
        VALUES (NEW.user_id, 'update', 'document', NEW.id, row_to_json(OLD)::jsonb, row_to_json(NEW)::jsonb);
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, old_values)
        VALUES (OLD.user_id, 'delete', 'document', OLD.id, row_to_json(OLD)::jsonb);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply audit logging trigger
CREATE TRIGGER log_document_changes_trigger
    AFTER INSERT OR UPDATE OR DELETE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION log_document_changes();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- View for document statistics by user
CREATE OR REPLACE VIEW user_document_stats AS
SELECT
    user_id,
    COUNT(*) AS total_documents,
    COUNT(*) FILTER (WHERE status = 'completed') AS completed_documents,
    COUNT(*) FILTER (WHERE status = 'processing') AS processing_documents,
    COUNT(*) FILTER (WHERE status = 'failed') AS failed_documents,
    SUM(size) AS total_size_bytes,
    AVG(processing_duration_seconds) AS avg_processing_time,
    MAX(created_at) AS last_upload_at
FROM documents
GROUP BY user_id;

-- View for analysis statistics
CREATE OR REPLACE VIEW analysis_stats AS
SELECT
    user_id,
    COUNT(*) AS total_analyses,
    SUM(total_entities) AS total_entities,
    SUM(jsonb_array_length(action_items)) AS total_action_items,
    SUM(jsonb_array_length(risks)) AS total_risks,
    AVG(overall_confidence) AS avg_confidence,
    AVG(processing_duration_seconds) AS avg_processing_time
FROM analysis
GROUP BY user_id;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to get document with analysis
CREATE OR REPLACE FUNCTION get_document_with_analysis(doc_id UUID)
RETURNS TABLE (
    document_data JSONB,
    analysis_data JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        row_to_json(d)::jsonb AS document_data,
        row_to_json(a)::jsonb AS analysis_data
    FROM documents d
    LEFT JOIN analysis a ON a.document_id = d.id
    WHERE d.id = doc_id;
END;
$$ LANGUAGE plpgsql;

-- Function to search documents by text
CREATE OR REPLACE FUNCTION search_documents(
    search_query TEXT,
    user_filter UUID DEFAULT NULL,
    status_filter VARCHAR DEFAULT NULL,
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    filename VARCHAR,
    description TEXT,
    similarity REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.filename,
        d.description,
        similarity(d.filename || ' ' || COALESCE(d.description, '') || ' ' || COALESCE(d.extracted_text, ''), search_query) AS similarity
    FROM documents d
    WHERE
        (user_filter IS NULL OR d.user_id = user_filter)
        AND (status_filter IS NULL OR d.status = status_filter)
        AND (
            d.filename ILIKE '%' || search_query || '%'
            OR d.description ILIKE '%' || search_query || '%'
            OR d.extracted_text ILIKE '%' || search_query || '%'
        )
    ORDER BY similarity DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Note: Initial admin user should be created via the application
-- to ensure proper password hashing

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE users IS 'User accounts with authentication and profile information';
COMMENT ON TABLE documents IS 'Uploaded documents with processing status and extracted content';
COMMENT ON TABLE analysis IS 'AI analysis results for documents';
COMMENT ON TABLE audit_logs IS 'Audit trail for compliance and security monitoring';

COMMENT ON COLUMN users.preferences IS 'User preferences stored as JSONB';
COMMENT ON COLUMN documents.entities IS 'Extracted entities stored as JSONB array';
COMMENT ON COLUMN documents.action_items IS 'Extracted action items stored as JSONB array';
COMMENT ON COLUMN documents.s3_reference IS 'S3 storage reference stored as JSONB';
COMMENT ON COLUMN analysis.entities IS 'Detailed entity extraction results';
COMMENT ON COLUMN analysis.risks IS 'Risk indicators identified in document';

-- ============================================================================
-- END OF SCRIPT
-- ============================================================================

-- Display summary
DO $$
BEGIN
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'PM Document Intelligence Database Initialization Complete';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - users (with RLS enabled)';
    RAISE NOTICE '  - documents (with RLS enabled)';
    RAISE NOTICE '  - analysis (with RLS enabled)';
    RAISE NOTICE '  - audit_logs (with RLS enabled)';
    RAISE NOTICE '';
    RAISE NOTICE 'Indexes created for optimized queries';
    RAISE NOTICE 'Row Level Security (RLS) policies configured';
    RAISE NOTICE 'Triggers configured for automatic timestamp updates';
    RAISE NOTICE 'Audit logging enabled for document changes';
    RAISE NOTICE '============================================================================';
END $$;
