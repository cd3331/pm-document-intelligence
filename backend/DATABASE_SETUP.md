

# Database Setup Guide

Comprehensive guide for setting up and using the Supabase database with Row Level Security for the PM Document Intelligence project.

## Table of Contents

1. [Overview](#overview)
2. [Database Schema](#database-schema)
3. [Setup Instructions](#setup-instructions)
4. [Models Usage](#models-usage)
5. [Row Level Security](#row-level-security)
6. [Common Operations](#common-operations)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The PM Document Intelligence database uses **PostgreSQL** via **Supabase** with the following features:

- **Row Level Security (RLS)** for data isolation
- **Automatic timestamps** with triggers
- **Audit logging** for compliance
- **Full-text search** with trigram indexes
- **JSONB** for flexible schema
- **Optimized indexes** for performance

### Database Tables

| Table | Purpose |
|-------|---------|
| `users` | User accounts and profiles |
| `documents` | Uploaded documents and metadata |
| `analysis` | AI analysis results |
| `audit_logs` | Audit trail for compliance |

---

## Database Schema

### Users Table

Stores user accounts with authentication and profile information.

**Key Fields:**
- `id` (UUID) - Primary key
- `email` - Unique email address
- `hashed_password` - Bcrypt hashed password
- `full_name` - User's full name
- `organization` - Organization name
- `role` - User role (admin, manager, user, guest)
- `preferences` (JSONB) - User preferences
- `created_at`, `updated_at`, `last_login` - Timestamps

**Indexes:**
- Email (unique)
- Role
- Active status
- Created date
- Organization

### Documents Table

Stores uploaded documents with processing status and extracted content.

**Key Fields:**
- `id` (UUID) - Primary key
- `user_id` (UUID) - Foreign key to users
- `filename` - Original filename
- `file_type` - MIME type
- `size` - File size in bytes
- `status` - Processing status (uploaded, processing, completed, failed)
- `extracted_text` - OCR extracted text
- `entities` (JSONB) - Extracted entities
- `action_items` (JSONB) - Extracted action items
- `sentiment` (JSONB) - Sentiment analysis
- `s3_reference` (JSONB) - S3 storage details
- `vector_embedding` (JSONB) - Vector embedding metadata

**Indexes:**
- User ID
- Status
- Created date
- User + Status (composite)
- Tags (GIN)
- Full-text search on filename and text

### Analysis Table

Stores detailed AI analysis results.

**Key Fields:**
- `id` (UUID) - Primary key
- `document_id` (UUID) - Foreign key to documents (unique)
- `user_id` (UUID) - Foreign key to users
- `entities` (JSONB) - Entity extraction results
- `action_items` (JSONB) - Action items with metadata
- `sentiment` (JSONB) - Sentiment analysis
- `topics` (JSONB) - Identified topics
- `risks` (JSONB) - Risk indicators
- `overall_confidence` - Confidence score
- `ai_models_used` - Array of model names

**Indexes:**
- Document ID (unique)
- User ID
- Risk level
- Confidence
- JSONB indexes on all major fields

### Audit Logs Table

Tracks all database changes for compliance.

**Key Fields:**
- `id` (UUID) - Primary key
- `user_id` (UUID) - User who made the change
- `action` - Action type (create, update, delete)
- `resource_type` - Resource type (user, document, analysis)
- `resource_id` - Resource ID
- `old_values` (JSONB) - Before state
- `new_values` (JSONB) - After state
- `ip_address` - Client IP
- `status` - Success/failure

---

## Setup Instructions

### 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Create a new project
3. Note your project URL and API keys

### 2. Configure Environment

Add to your `.env` file:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret

# Database
DATABASE_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

### 3. Run Database Initialization

```bash
# Option 1: Using psql
psql $DATABASE_URL -f scripts/init_database.sql

# Option 2: Using Supabase CLI
supabase db push

# Option 3: Copy-paste into Supabase SQL Editor
# Open scripts/init_database.sql and paste into the SQL editor
```

### 4. Verify Setup

```bash
# Test database connection
poetry run python -c "
from app.database import check_database_connection
import asyncio
result = asyncio.run(check_database_connection())
print(f'Database connected: {result}')
"
```

---

## Models Usage

### User Models

#### Create a New User

```python
from app.models import UserCreate, hash_password
from app.database import execute_insert

# Create user data
user_data = UserCreate(
    email="user@example.com",
    full_name="John Doe",
    organization="Acme Corp",
    password="SecurePass123",
    role="user"
)

# Hash password
hashed_password = hash_password(user_data.password)

# Insert into database
user_record = await execute_insert(
    "users",
    {
        "email": user_data.email,
        "full_name": user_data.full_name,
        "organization": user_data.organization,
        "hashed_password": hashed_password,
        "role": user_data.role.value,
        "preferences": user_data.preferences.model_dump(),
    }
)
```

#### Authenticate User

```python
from app.models import verify_password, create_token_pair, UserInDB
from app.database import execute_select

# Get user by email
users = await execute_select(
    "users",
    match={"email": email}
)

if not users:
    raise AuthenticationError("Invalid credentials")

user = UserInDB(**users[0])

# Verify password
if not verify_password(password, user.hashed_password):
    raise AuthenticationError("Invalid credentials")

# Create JWT tokens
tokens = create_token_pair(user)

# tokens.access_token
# tokens.refresh_token
```

#### Verify JWT Token

```python
from app.models import verify_token

try:
    token_data = verify_token(access_token)
    user_id = token_data.sub
    # Use user_id to fetch user
except TokenExpiredError:
    # Handle expired token
    pass
except InvalidTokenError:
    # Handle invalid token
    pass
```

### Document Models

#### Create a Document

```python
from app.models import DocumentCreate
from app.database import execute_insert

# Create document
doc_data = DocumentCreate(
    user_id=user_id,
    filename="report.pdf",
    file_type="application/pdf",
    size=1024000,
    description="Q4 Financial Report",
    tags=["finance", "quarterly", "2024"]
)

# Insert into database
document = await execute_insert(
    "documents",
    doc_data.model_dump()
)
```

#### Update Document Status

```python
from app.models import DocumentStatus
from app.database import execute_update

# Update status
updated_doc = await execute_update(
    "documents",
    {
        "status": DocumentStatus.COMPLETED.value,
        "processing_completed_at": datetime.utcnow(),
    },
    match={"id": document_id}
)
```

#### Get Documents with Filtering

```python
from app.database import execute_select

# Get user's completed documents
documents = await execute_select(
    "documents",
    columns="id,filename,status,created_at",
    match={
        "user_id": user_id,
        "status": "completed"
    },
    order="created_at.desc",
    limit=10
)
```

### Analysis Models

#### Create Analysis Results

```python
from app.models import (
    AnalysisCreate,
    EntityExtraction,
    ActionItemDetail,
    SentimentAnalysis
)
from app.database import execute_insert

# Create entities
entities = [
    EntityExtraction(
        type="person",
        text="John Doe",
        confidence=0.95,
        start_offset=0,
        end_offset=8
    )
]

# Create action items
action_items = [
    ActionItemDetail(
        text="Review budget",
        priority="high",
        assignee="Finance Team",
        confidence=0.88
    )
]

# Create sentiment
sentiment = SentimentAnalysis(
    overall_sentiment="positive",
    positive_score=0.75,
    negative_score=0.10,
    neutral_score=0.10,
    mixed_score=0.05,
    confidence=0.88
)

# Create analysis
analysis_data = AnalysisCreate(
    document_id=document_id,
    ai_models_used=["claude-3-5-sonnet", "text-embedding-3-small"],
    processing_duration_seconds=45.2,
    entities=entities,
    action_items=action_items,
    sentiment=sentiment
)

# Insert into database
analysis = await execute_insert(
    "analysis",
    {
        **analysis_data.model_dump(),
        "user_id": user_id,
        "entities": [e.model_dump() for e in entities],
        "action_items": [a.model_dump() for a in action_items],
        "sentiment": sentiment.model_dump(),
        "total_entities": len(entities),
    }
)
```

---

## Row Level Security

### How RLS Works

Row Level Security ensures users can only access their own data. Policies are enforced at the database level, providing security even if application code has bugs.

### RLS Policies

#### Users Table

- ✅ Users can **read** their own profile
- ✅ Users can **update** their own profile (except role)
- ✅ Admins can do **anything** with users

#### Documents Table

- ✅ Users can **read** their own documents
- ✅ Users can **create** documents (as themselves)
- ✅ Users can **update** their own documents
- ✅ Users can **delete** their own documents
- ✅ Admins can do **anything** with documents

#### Analysis Table

- ✅ Users can **read** analysis for their documents
- ✅ System can **create** analysis
- ✅ Users can **update/delete** their own analysis
- ✅ Admins can do **anything** with analysis

#### Audit Logs Table

- ✅ Users can **read** their own audit logs
- ✅ Admins can **read** all audit logs
- ✅ System can **create** audit logs (automatic)

### Testing RLS

```python
from app.database import get_supabase_client

# Regular user client
supabase = get_supabase_client()

# This will only return documents owned by the authenticated user
documents = supabase.table("documents").select("*").execute()

# Admin client (bypasses RLS)
from app.database import get_supabase_admin_client

admin_supabase = get_supabase_admin_client()

# This returns ALL documents
all_documents = admin_supabase.table("documents").select("*").execute()
```

---

## Common Operations

### Search Documents

```python
from app.database import search_full_text

# Full-text search
results = await search_full_text(
    table="documents",
    column="extracted_text",
    search_term="budget analysis",
    limit=10
)
```

### Batch Insert

```python
from app.database import batch_insert

# Insert multiple action items
action_items = [
    {"document_id": doc_id, "text": "Task 1", "priority": "high"},
    {"document_id": doc_id, "text": "Task 2", "priority": "medium"},
    # ... more items
]

results = await batch_insert(
    "action_items",
    action_items,
    chunk_size=100
)
```

### Get Document with Analysis

```sql
-- Using the custom function
SELECT * FROM get_document_with_analysis('document-uuid-here');
```

### Search with Filters

```python
from app.database import build_filter_query, get_supabase_client

supabase = get_supabase_client()

# Build filtered query
query = supabase.table("documents").select("*")

filters = {
    "status": "completed",
    "file_type": "application/pdf"
}

query = build_filter_query(query, filters)
results = query.execute()
```

---

## Troubleshooting

### Connection Issues

**Problem**: `DatabaseError: Database connection check failed`

**Solution**:
```bash
# Check DATABASE_URL is correct
echo $DATABASE_URL

# Test direct connection
psql $DATABASE_URL -c "SELECT 1"

# Check Supabase project status
# Visit supabase.com/dashboard
```

---

### RLS Policy Errors

**Problem**: `new row violates row-level security policy`

**Solution**:
```python
# Ensure auth context is set
from app.database import get_supabase_client

# Use authenticated client
supabase = get_supabase_client()

# OR use admin client to bypass RLS
from app.database import get_supabase_admin_client
admin_supabase = get_supabase_admin_client()
```

---

### Migration Errors

**Problem**: `ERROR: relation "users" already exists`

**Solution**:
```sql
-- Drop all tables (WARNING: deletes data)
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS analysis CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Then re-run migration
\i scripts/init_database.sql
```

---

### Query Performance

**Problem**: Slow queries on large datasets

**Solution**:
```sql
-- Check query plan
EXPLAIN ANALYZE
SELECT * FROM documents WHERE user_id = 'uuid-here';

-- Add missing indexes
CREATE INDEX idx_custom ON table_name (column_name);

-- Update statistics
ANALYZE documents;
```

---

## Database Maintenance

### Backup Database

```bash
# Backup via Supabase CLI
supabase db dump > backup.sql

# Backup via pg_dump
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
# Restore via psql
psql $DATABASE_URL < backup.sql
```

### View Statistics

```sql
-- Document statistics by user
SELECT * FROM user_document_stats;

-- Analysis statistics
SELECT * FROM analysis_stats;

-- Table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC;
```

---

## Next Steps

1. **Add Migrations**: Set up Alembic for schema migrations
2. **Add Tests**: Write integration tests for database operations
3. **Monitor Performance**: Set up query logging and slow query alerts
4. **Backup Strategy**: Implement automated backups
5. **Scale**: Configure read replicas for high traffic

---

## Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [PostgreSQL RLS Guide](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

