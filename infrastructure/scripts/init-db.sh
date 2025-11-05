#!/bin/bash

# ============================================
# PM Document Intelligence - Database Initialization Script
# Executed automatically when PostgreSQL container starts
# ============================================

set -e

echo "Initializing PM Document Intelligence database..."

# This script runs as the postgres user during container initialization

# ==========================================
# Enable Required Extensions
# ==========================================
echo "Enabling PostgreSQL extensions..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- UUID generation
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

    -- Vector similarity search (pgvector)
    CREATE EXTENSION IF NOT EXISTS vector;

    -- Full-text search
    CREATE EXTENSION IF NOT EXISTS pg_trgm;

    -- Case-insensitive text
    CREATE EXTENSION IF NOT EXISTS citext;

    -- Additional useful extensions
    CREATE EXTENSION IF NOT EXISTS "pgcrypto";
    CREATE EXTENSION IF NOT EXISTS "hstore";
EOSQL

echo "Extensions enabled successfully ✓"

# ==========================================
# Create Database Schema
# ==========================================
echo "Creating database schema..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- ==========================================
    -- Users Table
    -- ==========================================
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        username VARCHAR(255) UNIQUE NOT NULL,
        email CITEXT UNIQUE NOT NULL,
        hashed_password VARCHAR(255) NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        is_superuser BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    -- ==========================================
    -- Documents Table
    -- ==========================================
    CREATE TABLE IF NOT EXISTS documents (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        filename VARCHAR(500) NOT NULL,
        file_path VARCHAR(1000) NOT NULL,
        file_size BIGINT,
        mime_type VARCHAR(100),
        document_type VARCHAR(50),
        status VARCHAR(50) DEFAULT 'pending',
        extracted_text TEXT,
        metadata JSONB DEFAULT '{}',
        s3_key VARCHAR(1000),
        s3_bucket VARCHAR(255),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        processed_at TIMESTAMP WITH TIME ZONE
    );

    -- ==========================================
    -- Document Entities Table
    -- ==========================================
    CREATE TABLE IF NOT EXISTS document_entities (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        entity_type VARCHAR(100) NOT NULL,
        entity_text TEXT NOT NULL,
        confidence FLOAT,
        start_offset INTEGER,
        end_offset INTEGER,
        metadata JSONB DEFAULT '{}',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    -- ==========================================
    -- Action Items Table
    -- ==========================================
    CREATE TABLE IF NOT EXISTS action_items (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        description TEXT NOT NULL,
        priority VARCHAR(20) DEFAULT 'medium',
        due_date DATE,
        status VARCHAR(50) DEFAULT 'pending',
        assigned_to UUID REFERENCES users(id),
        metadata JSONB DEFAULT '{}',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        completed_at TIMESTAMP WITH TIME ZONE
    );

    -- ==========================================
    -- Document Vectors Table (for semantic search)
    -- ==========================================
    CREATE TABLE IF NOT EXISTS document_vectors (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        chunk_text TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        embedding vector(1536),  -- OpenAI embeddings dimension
        metadata JSONB DEFAULT '{}',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE(document_id, chunk_index)
    );

    -- ==========================================
    -- Agent Executions Table
    -- ==========================================
    CREATE TABLE IF NOT EXISTS agent_executions (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
        agent_type VARCHAR(100) NOT NULL,
        status VARCHAR(50) DEFAULT 'pending',
        result JSONB DEFAULT '{}',
        error TEXT,
        execution_time_ms INTEGER,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        completed_at TIMESTAMP WITH TIME ZONE
    );

    -- ==========================================
    -- Chat Messages Table
    -- ==========================================
    CREATE TABLE IF NOT EXISTS chat_messages (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
        role VARCHAR(50) NOT NULL,  -- user, assistant, system
        content TEXT NOT NULL,
        metadata JSONB DEFAULT '{}',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    -- ==========================================
    -- API Keys Table
    -- ==========================================
    CREATE TABLE IF NOT EXISTS api_keys (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        key_hash VARCHAR(255) UNIQUE NOT NULL,
        name VARCHAR(255),
        is_active BOOLEAN DEFAULT TRUE,
        last_used_at TIMESTAMP WITH TIME ZONE,
        expires_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    -- ==========================================
    -- Audit Log Table
    -- ==========================================
    CREATE TABLE IF NOT EXISTS audit_log (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        action VARCHAR(100) NOT NULL,
        resource_type VARCHAR(100),
        resource_id UUID,
        details JSONB DEFAULT '{}',
        ip_address INET,
        user_agent TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
EOSQL

echo "Database schema created successfully ✓"

# ==========================================
# Create Indexes
# ==========================================
echo "Creating indexes..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Users indexes
    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
    CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

    -- Documents indexes
    CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
    CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
    CREATE INDEX IF NOT EXISTS idx_documents_document_type ON documents(document_type);
    CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
    CREATE INDEX IF NOT EXISTS idx_documents_s3_key ON documents(s3_key);

    -- Full-text search on extracted_text
    CREATE INDEX IF NOT EXISTS idx_documents_text_search ON documents USING gin(to_tsvector('english', COALESCE(extracted_text, '')));

    -- Document entities indexes
    CREATE INDEX IF NOT EXISTS idx_document_entities_document_id ON document_entities(document_id);
    CREATE INDEX IF NOT EXISTS idx_document_entities_entity_type ON document_entities(entity_type);

    -- Action items indexes
    CREATE INDEX IF NOT EXISTS idx_action_items_document_id ON action_items(document_id);
    CREATE INDEX IF NOT EXISTS idx_action_items_status ON action_items(status);
    CREATE INDEX IF NOT EXISTS idx_action_items_assigned_to ON action_items(assigned_to);
    CREATE INDEX IF NOT EXISTS idx_action_items_due_date ON action_items(due_date);

    -- Document vectors indexes
    CREATE INDEX IF NOT EXISTS idx_document_vectors_document_id ON document_vectors(document_id);

    -- Vector similarity search index (IVFFlat for faster approximate search)
    CREATE INDEX IF NOT EXISTS idx_document_vectors_embedding ON document_vectors USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

    -- Agent executions indexes
    CREATE INDEX IF NOT EXISTS idx_agent_executions_document_id ON agent_executions(document_id);
    CREATE INDEX IF NOT EXISTS idx_agent_executions_agent_type ON agent_executions(agent_type);
    CREATE INDEX IF NOT EXISTS idx_agent_executions_status ON agent_executions(status);

    -- Chat messages indexes
    CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id);
    CREATE INDEX IF NOT EXISTS idx_chat_messages_document_id ON chat_messages(document_id);
    CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);

    -- API keys indexes
    CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
    CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);

    -- Audit log indexes
    CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
    CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
    CREATE INDEX IF NOT EXISTS idx_audit_log_resource_type ON audit_log(resource_type);
    CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);
EOSQL

echo "Indexes created successfully ✓"

# ==========================================
# Create Functions and Triggers
# ==========================================
echo "Creating functions and triggers..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Updated timestamp trigger function
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS \$\$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    \$\$ language 'plpgsql';

    -- Apply updated_at trigger to tables
    DROP TRIGGER IF EXISTS update_users_updated_at ON users;
    CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

    DROP TRIGGER IF EXISTS update_documents_updated_at ON documents;
    CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

    DROP TRIGGER IF EXISTS update_action_items_updated_at ON action_items;
    CREATE TRIGGER update_action_items_updated_at BEFORE UPDATE ON action_items
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EOSQL

echo "Functions and triggers created successfully ✓"

# ==========================================
# Insert Seed Data (Development Only)
# ==========================================
if [ "${POSTGRES_DB}" = "pm_document_intelligence" ] && [ "${ENVIRONMENT:-development}" = "development" ]; then
    echo "Inserting seed data for development..."

    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        -- Create a test user (password: testpassword123)
        INSERT INTO users (username, email, hashed_password, is_superuser)
        VALUES (
            'testuser',
            'test@example.com',
            '\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqJXZLZVp6',
            true
        )
        ON CONFLICT (email) DO NOTHING;
EOSQL

    echo "Seed data inserted successfully ✓"
fi

# ==========================================
# Grant Permissions
# ==========================================
echo "Granting permissions..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Grant all privileges to the database user
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${POSTGRES_USER};
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${POSTGRES_USER};
    GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO ${POSTGRES_USER};

    -- Set default privileges for future objects
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${POSTGRES_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${POSTGRES_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO ${POSTGRES_USER};
EOSQL

echo "Permissions granted successfully ✓"

# ==========================================
# Database Statistics
# ==========================================
echo "Database initialization complete!"
echo ""
echo "Database Statistics:"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT
        'Tables' as type,
        COUNT(*) as count
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    UNION ALL
    SELECT
        'Indexes' as type,
        COUNT(*) as count
    FROM pg_indexes
    WHERE schemaname = 'public'
    UNION ALL
    SELECT
        'Extensions' as type,
        COUNT(*) as count
    FROM pg_extension;
EOSQL

echo ""
echo "✓ Database initialization successful!"
