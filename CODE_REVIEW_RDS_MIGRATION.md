# Code Review: Supabase to AWS RDS PostgreSQL Migration

## Executive Summary

**Status**: 🔴 **CRITICAL** - Application attempting to use Supabase PostgREST API but infrastructure uses AWS RDS
**Impact**: Production sign-up functionality broken due to architectural mismatch
**Priority**: P0 - Immediate action required
**Estimated Effort**: 4-6 hours

---

## Critical Issues Identified

### 1. 🔴 **CRITICAL**: Dual Database Architecture Conflict

**Location**: `backend/app/database.py:1-708`

**Issue**: Application uses Supabase client library while infrastructure uses AWS RDS PostgreSQL

```python
# ❌ CURRENT (Incorrect)
from supabase import Client, create_client
_supabase_client: Client | None = None

def get_supabase_client() -> Client:
    _supabase_client = create_client(
        supabase_url=str(settings.supabase.supabase_url),
        supabase_key=settings.supabase.supabase_key,
    )
```

**Root Cause**: Supabase's PostgREST API expects schema cache which doesn't exist in plain RDS

**Evidence from Logs**:
```
postgrest.exceptions.APIError: {'message': "Could not find the table 'public.users'
in the schema cache", 'code': 'PGRST205'}
```

**Impact**:
- ❌ All database operations failing
- ❌ User registration broken
- ❌ Authentication endpoints non-functional
- 💰 AWS RDS instance running but unused
- 🔐 Potential security implications from misconfiguration

---

### 2. ⚠️ **HIGH**: Inconsistent Database Configuration

**Location**: `backend/app/config.py:231-268`

**Issue**: Configuration includes both Supabase and RDS settings

```python
# ❌ CURRENT (Conflicting)
class SupabaseConfig(BaseSettings):
    supabase_url: AnyHttpUrl = Field(..., description="Supabase project URL")
    supabase_key: str = Field(..., description="Supabase anonymous key")
    supabase_service_key: str = Field(..., description="Supabase service role key")
    database_url: PostgresDsn = Field(..., description="PostgreSQL connection URL")
```

**Recommendation**: Remove Supabase-specific configuration, keep only `database_url`

---

### 3. ⚠️ **HIGH**: SQLAlchemy Infrastructure Underutilized

**Location**: `backend/app/db/session.py:1-169`

**Observation**: Excellent SQLAlchemy async infrastructure exists but is unused

```python
# ✅ ALREADY EXISTS (Good!)
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Action Required**: Migrate all `database.py` functions to use `get_db()` instead of Supabase client

---

##Security Implications

### 🔐 **SECURITY**: Row Level Security (RLS) Not Enforced

**Current State**: Supabase code expects RLS policies, but plain PostgreSQL RDS doesn't enforce them

**Impact**:
- Data isolation between users not enforced at database level
- Application must handle all authorization
- SQL injection risks if not properly parameterized

**Recommendations**:
1. ✅ Use SQLAlchemy ORM (parameterized queries by default)
2. ✅ Implement application-level authorization checks
3. ✅ Add database-level triggers for audit logging
4. ⚠️ Consider AWS RDS IAM authentication for additional security

---

### 🔐 **SECURITY**: Connection String Security

**Current**: Database credentials stored in AWS Secrets Manager ✅
**Current**: URL-encoded special characters causing connection issues ⚠️

**Password**: `D$%WyQqhMQf#NQS7X#hH}:juE0VUU)(e`
**Issue**: Special characters in password need proper escaping

```python
# ✅ RECOMMENDED
from urllib.parse import quote_plus
password = quote_plus("D$%WyQqhMQf#NQS7X#hH}:juE0VUU)(e")
db_url = f"postgresql://pmadmin:{password}@host:5432/database"
```

---

## Refactoring Plan

### Phase 1: Database Layer Rewrite (2-3 hours)

**File**: `backend/app/database.py`

Replace all functions to use SQLAlchemy:

```python
# ✅ PROPOSED IMPLEMENTATION
from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

async def execute_select(
    table_name: str,
    match: dict[str, Any] | None = None,
    select_cols: list[str] | None = None,
) -> list[dict]:
    """Execute SELECT query using SQLAlchemy."""
    async with get_db() as session:
        # Use SQLAlchemy Core for dynamic table queries
        from sqlalchemy import MetaData, Table
        metadata = MetaData()
        table = Table(table_name, metadata, autoload_with=session.bind)

        query = select(table)
        if match:
            for key, value in match.items():
                query = query.where(table.c[key] == value)

        result = await session.execute(query)
        return [dict(row._mapping) for row in result]
```

**Functions to Replace** (in priority order):
1. ✅ `execute_select()` - Most critical (used in auth)
2. ✅ `execute_insert()` - Required for user registration
3. ✅ `execute_update()` - Required for user updates
4. ✅ `execute_delete()` - Required for data cleanup
5. ✅ `execute_count()` - Used in pagination
6. ✅ `transaction()` - Transaction management
7. ✅ `batch_insert()` - Bulk operations
8. ✅ `search_full_text()` - Search functionality
9. ✅ `upsert_data()` - Upsert operations

---

### Phase 2: Configuration Cleanup (30 minutes)

**File**: `backend/app/config.py`

```python
# ❌ REMOVE
class SupabaseConfig(BaseSettings):
    supabase_url: AnyHttpUrl
    supabase_key: str
    supabase_service_key: str
    supabase_jwt_secret: str
    # ...

# ✅ REPLACE WITH
class DatabaseConfig(BaseSettings):
    """PostgreSQL database configuration."""
    database_url: PostgresDsn = Field(
        ...,
        description="PostgreSQL connection URL (required)"
    )
    database_pool_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Connection pool size"
    )
    database_max_overflow: int = Field(
        default=10,
        ge=0,
        le=50,
        description="Maximum overflow connections"
    )
```

---

### Phase 3: Remove Supabase Dependencies (15 minutes)

**Files to Update**:
- `backend/requirements.txt`: Remove `supabase` package
- `backend/app/database.py`: Remove `from supabase import ...`
- `backend/app/db/session.py`: Update references from `settings.supabase.*` to `settings.database.*`
- `backend/app/middleware/security.py`: Update any Supabase references
- `backend/app/services/vector_search.py`: Migrate to pgvector extension

---

### Phase 4: Secrets Manager Updates (15 minutes)

**Remove Obsolete Secrets**:
```bash
# No longer needed:
- pm-doc-intel/supabase-url-production
- pm-doc-intel/supabase-key-production
- pm-doc-intel/supabase-service-key-production
- pm-doc-intel/supabase-jwt-secret-production

# Keep:
- pm-doc-intel/database-url-production ✅
```

---

### Phase 5: Testing Strategy (1 hour)

**Test Cases**:
1. ✅ User registration with new PostgreSQL backend
2. ✅ User login and JWT token generation
3. ✅ Document upload and storage
4. ✅ Database connection pooling under load
5. ✅ Transaction rollback on errors
6. ✅ Concurrent user operations
7. ✅ SQL injection prevention validation

---

## Best Practices & Recommendations

### ✅ **DO**:
1. Use SQLAlchemy ORM for all database operations
2. Use async/await for all database calls
3. Implement proper connection pooling
4. Use parameterized queries (SQLAlchemy handles this)
5. Add database indexes for frequently queried columns
6. Implement retry logic with exponential backoff
7. Log all database errors with structured logging
8. Use transactions for multi-step operations
9. Add database migration scripts (Alembic)
10. Monitor connection pool metrics

### ❌ **DON'T**:
1. Mix Supabase client with direct PostgreSQL connections
2. Use string concatenation for SQL queries
3. Store database credentials in code
4. Skip connection pool configuration
5. Ignore transaction boundaries
6. Use synchronous database calls in async code
7. Leave unused Supabase dependencies in place

---

## Migration Checklist

- [x] Audit existing Supabase usage
- [ ] Rewrite `database.py` with SQLAlchemy
- [ ] Update `config.py` to remove Supabase config
- [ ] Remove Supabase from `requirements.txt`
- [ ] Update ECS task definition (remove Supabase env vars)
- [ ] Test user registration endpoint
- [ ] Test authentication flow
- [ ] Test document operations
- [ ] Load test connection pooling
- [ ] Monitor production metrics
- [ ] Remove obsolete AWS Secrets

---

## Performance Considerations

### Connection Pooling
- **Current**: Supabase client (unknown pooling)
- **Proposed**: SQLAlchemy QueuePool
  - Pool size: 20 connections
  - Max overflow: 10 connections
  - Pool recycle: 3600 seconds
  - Pre-ping enabled for connection health checks

### Query Performance
- ✅ Add indexes on frequently queried columns (already in schema)
- ✅ Use EXPLAIN ANALYZE for slow queries
- ✅ Implement query result caching where appropriate
- ✅ Monitor query execution times

---

## Deployment Strategy

### 1. Build & Test Locally
```bash
# Update dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Run tests
pytest tests/integration/test_database.py
```

### 2. Deploy to Production
```bash
# Build Docker image
docker build -t pm-document-intelligence:rds-migration .

# Push to ECR
docker push 488678936715.dkr.ecr.us-east-1.amazonaws.com/pm-document-intelligence:rds-migration

# Update ECS service
aws ecs update-service \
  --cluster pm-doc-intel-cluster-production \
  --service pm-doc-intel-backend-service-production \
  --force-new-deployment
```

### 3. Rollback Plan
- Keep previous ECS task definition revision
- Revert to previous Docker image if issues arise
- Database schema changes are backwards compatible

---

## Cost Impact

### Before (Supabase + RDS):
- AWS RDS: ~$50-150/month (running but unused)
- Supabase: $0 (free tier, not actually working)

### After (RDS Only):
- AWS RDS: ~$50-150/month (actively used)
- **Savings**: Eliminated complexity, no Supabase costs

---

## Timeline

| Phase | Duration | Priority |
|-------|----------|----------|
| Database Layer Rewrite | 2-3 hours | P0 |
| Configuration Cleanup | 30 min | P0 |
| Remove Dependencies | 15 min | P1 |
| Secrets Cleanup | 15 min | P2 |
| Testing | 1 hour | P0 |
| Deployment | 30 min | P0 |
| **TOTAL** | **4-6 hours** | **P0** |

---

## Conclusion

This migration is **critical** and should be completed immediately. The current architecture has a fundamental mismatch between application code (Supabase) and infrastructure (RDS PostgreSQL), causing production failures.

The good news: SQLAlchemy infrastructure already exists in `db/session.py`, making the migration straightforward. Focus on rewriting `database.py` functions to use SQLAlchemy instead of Supabase client.

**Recommended Action**: Begin Phase 1 (Database Layer Rewrite) immediately.

---

**Review Status**: 🔴 **REJECT** - Code cannot be merged until Supabase dependencies are removed and RDS integration is complete.

**Reviewer**: AI Code Review System
**Date**: 2025-11-07
**Severity**: Critical
