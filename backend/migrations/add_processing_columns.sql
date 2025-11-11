-- ============================================================================
-- Add Missing Processing Columns to Documents Table
-- ============================================================================
-- Date: 2025-11-10
-- Purpose: Add columns required by DocumentProcessor for checkpoint/state tracking
--
-- This migration adds three columns that the document processor uses:
-- 1. processing_checkpoint: Stores the current processing step (JSON)
-- 2. processing_state: Stores the full processing state for resume (JSON)
-- 3. error_message: Stores the last error message if processing fails
--
-- Usage:
--   psql $DATABASE_URL -f backend/migrations/add_processing_columns.sql
-- ============================================================================

-- Add processing_checkpoint column (JSONB for structured checkpoint data)
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS processing_checkpoint JSONB DEFAULT NULL;

-- Add processing_state column (JSONB for full state tracking)
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS processing_state JSONB DEFAULT NULL;

-- Add error_message column (TEXT for error details)
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS error_message TEXT DEFAULT NULL;

-- Add risks column if missing (JSONB for risk tracking)
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS risks JSONB DEFAULT '[]'::jsonb;

-- Add processing_metadata column if missing (JSONB for misc metadata)
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS processing_metadata JSONB DEFAULT '{}'::jsonb;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_processing_checkpoint
ON documents USING gin (processing_checkpoint)
WHERE processing_checkpoint IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_documents_processing_state
ON documents USING gin (processing_state)
WHERE processing_state IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_documents_error_message
ON documents (error_message)
WHERE error_message IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_documents_risks
ON documents USING gin (risks);

-- Add comment for documentation
COMMENT ON COLUMN documents.processing_checkpoint IS 'Current processing checkpoint for resume capability';
COMMENT ON COLUMN documents.processing_state IS 'Full processing state including intermediate results';
COMMENT ON COLUMN documents.error_message IS 'Last error message if processing failed';
COMMENT ON COLUMN documents.risks IS 'Extracted risk items from document analysis';
COMMENT ON COLUMN documents.processing_metadata IS 'Additional processing metadata (extraction method, confidence, etc.)';

-- Verify the changes
\d documents;

-- Success message
\echo 'SUCCESS: Added missing processing columns to documents table'
\echo 'Columns added: processing_checkpoint, processing_state, error_message, risks, processing_metadata'
\echo 'Indexes created for efficient querying'
