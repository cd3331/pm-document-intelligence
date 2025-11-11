-- Fix database schema by adding missing columns
-- Run this via: psql $DATABASE_URL -f fix_schema.sql

\echo 'Adding missing columns to documents table...'

-- Add processing_checkpoint column
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_checkpoint JSONB DEFAULT NULL;

-- Add processing_state column
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_state JSONB DEFAULT NULL;

-- Add error_message column
ALTER TABLE documents ADD COLUMN IF NOT EXISTS error_message TEXT DEFAULT NULL;

-- Add risks column
ALTER TABLE documents ADD COLUMN IF NOT EXISTS risks JSONB DEFAULT '[]'::jsonb;

-- Add processing_metadata column
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_metadata JSONB DEFAULT '{}'::jsonb;

\echo 'Creating indexes...'

-- Create indexes for efficient querying
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

\echo 'Verifying changes...'

-- Verify columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'documents'
AND column_name IN ('processing_checkpoint', 'processing_state', 'error_message', 'risks', 'processing_metadata')
ORDER BY column_name;

\echo 'Database schema fixed successfully!'
