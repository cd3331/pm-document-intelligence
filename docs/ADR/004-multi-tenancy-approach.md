# 004. Multi-Tenancy Implementation Strategy

**Date**: 2024-01-15

**Status**: Accepted

**Deciders**: Engineering Team, Product Manager, Security Team

**Tags**: architecture, multi-tenancy, security, database

---

## Context

PM Document Intelligence needs to support multiple organizations (tenants) on a single deployment:
- Each organization has isolated data (documents, users, settings)
- Need to prevent data leakage between organizations
- Support different pricing tiers per organization
- Enable white-labeling for enterprise customers
- Scale to 1,000+ organizations

Requirements:
- **Data Isolation**: Complete separation of tenant data
- **Performance**: No significant overhead for tenant filtering
- **Security**: Prevent cross-tenant data access
- **Scalability**: Support growing number of tenants
- **Cost**: Minimize infrastructure costs
- **Compliance**: Meet GDPR, SOC 2 requirements

We needed to choose a multi-tenancy approach:
1. Shared database with tenant IDs (row-level isolation)
2. Separate database per tenant
3. Separate schema per tenant
4. Hybrid approach

## Decision

We chose **shared database with organization_id filtering** (row-level multi-tenancy).

All tenants share the same database, with `organization_id` foreign key on all tables. Row-Level Security (RLS) policies enforce isolation.

## Consequences

### Positive

- **Cost Efficiency**: Single database infrastructure
  - No per-tenant database overhead
  - Shared connection pooling
  - Efficient resource utilization
  - Lower operational costs

- **Operational Simplicity**: Easier to manage
  - Single database to backup
  - One migration path for all tenants
  - Centralized monitoring
  - Simpler deployment process

- **Development Velocity**: Faster development
  - Single codebase for all tenants
  - Easy to add new organizations
  - No complex routing logic
  - Standard ORM usage

- **Shared Resources**: Better utilization
  - Connection pooling across all tenants
  - Cache sharing where appropriate
  - Efficient index usage

- **Cross-Tenant Analytics**: Easier to aggregate
  - Platform-wide analytics
  - Usage statistics
  - Performance monitoring

### Negative

- **Security Risk**: Highest risk of data leakage
  - One bug could expose cross-tenant data
  - Requires careful code review
  - Developer errors can be catastrophic
  - Need rigorous testing

- **Noisy Neighbor**: Performance impact
  - One tenant's heavy load affects others
  - No resource isolation
  - Need rate limiting and quotas
  - Cannot guarantee performance per tenant

- **Compliance Complexity**: Harder for some compliance
  - Some regulations require physical separation
  - Auditors may require extra assurances
  - More complex to demonstrate isolation

- **Limited Customization**: Hard to customize per-tenant
  - All tenants share same schema
  - Difficult to add tenant-specific features
  - Cannot easily optimize for specific tenant

### Neutral

- **Migration Path**: Can migrate to separate DBs later
  - Data already partitioned by organization_id
  - Can extract tenant to separate DB if needed
  - Not permanently locked in

- **Scaling**: Vertical scaling initially
  - Single DB limits (but sufficient for 1,000s of tenants)
  - Can shard by organization_id later if needed

## Alternatives Considered

### Alternative 1: Separate Database Per Tenant

**Description**: Each organization gets dedicated PostgreSQL database

**Pros**:
- **Complete Isolation**: No risk of data leakage
- **Performance**: Each tenant has dedicated resources
- **Compliance**: Easier for strict requirements
- **Customization**: Can customize schema per tenant
- **Security**: Physical separation

**Cons**:
- **High Cost**: $200-400/month per database
  - 100 orgs = $20,000-40,000/month
  - Unsustainable at scale
- **Operational Nightmare**: Managing 100s of databases
  - 100× backups to manage
  - 100× migrations to run
  - Complex monitoring
  - Deployment complexity
- **Connection Limits**: Need connection per database
- **Slower Development**: More complex routing

**Why not chosen**:
- Cost prohibitive at scale
- Operational complexity too high
- Not necessary for current compliance requirements
- Can migrate specific tenants later if needed

**When to use**:
- Enterprise customers with strict isolation requirements
- Customers in regulated industries (healthcare, finance)
- Very large customers (>50% of total usage)

### Alternative 2: Separate Schema Per Tenant

**Description**: One database, separate PostgreSQL schema per tenant

**Pros**:
- Good data isolation
- Easier than separate databases
- Still use shared connection pool
- Reasonable security

**Cons**:
- Schema limits in PostgreSQL (~100-1000)
- Migrations still complex (N schemas)
- Query routing complexity
- Connection management harder
- Limited scalability

**Why not chosen**:
- Similar operational burden to separate databases
- PostgreSQL not optimized for many schemas
- Not significantly better than row-level isolation
- More complex than shared tables

### Alternative 3: Hybrid Approach

**Description**: Shared DB for small tenants, dedicated for large

**Pros**:
- Cost-effective for small tenants
- Isolation for large/enterprise tenants
- Flexible based on needs

**Cons**:
- Most complex to implement
- Two code paths to maintain
- Migration complexity when tenant grows
- Operational overhead of both approaches

**Why not chosen**:
- Too complex for MVP
- Can add later if needed
- Start simple, add complexity only if necessary

## Implementation

**Timeline**:
- Week 1: Design organization model and relationships
- Week 2: Add organization_id to all tables
- Week 3: Implement Row-Level Security policies
- Week 4: Update all queries with organization filtering
- Week 5: Security audit and testing
- Week 6: Organization management UI

**Key Implementation Steps**:

1. **Organization Model**:
```python
class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    plan = Column(String, default="free")  # free, pro, enterprise
    status = Column(String, default="active")  # active, suspended
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="organization")
    documents = relationship("Document", back_populates="organization")
    settings = Column(JSONB, default={})
```

2. **Foreign Key on All Tables**:
```python
class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True)
    organization_id = Column(UUID(as_uuid=True),
                            ForeignKey("organizations.id"),
                            nullable=False,
                            index=True)  # Critical index!

    # Composite index for efficient filtering
    __table_args__ = (
        Index('idx_documents_org_created',
              'organization_id', 'created_at'),
    )
```

3. **Row-Level Security** (Defense in Depth):
```sql
-- Enable RLS on documents table
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their org's documents
CREATE POLICY documents_isolation ON documents
    USING (organization_id = current_setting('app.current_org_id')::uuid);

-- Set organization context
SET app.current_org_id = 'org-123-uuid';
```

4. **Application-Level Filtering** (Primary Defense):
```python
async def get_documents(org_id: UUID, db: Session):
    """Always filter by organization_id"""
    return db.query(Document).filter(
        Document.organization_id == org_id
    ).all()

# Use dependency injection to ensure org_id always present
@app.get("/documents")
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get org_id from authenticated user
    org_id = current_user.organization_id

    # All queries automatically filtered
    documents = await get_documents(org_id, db)
    return documents
```

5. **Security Middleware**:
```python
@app.middleware("http")
async def enforce_tenant_isolation(request: Request, call_next):
    """Ensure organization context is set"""
    if request.user.is_authenticated:
        # Set organization context for this request
        g.organization_id = request.user.organization_id

        # Set PostgreSQL session variable for RLS
        await db.execute(
            "SET LOCAL app.current_org_id = %s",
            (str(request.user.organization_id),)
        )

    response = await call_next(request)
    return response
```

6. **Testing Strategy**:
```python
@pytest.fixture
def org_a():
    return create_organization(name="Org A")

@pytest.fixture
def org_b():
    return create_organization(name="Org B")

def test_tenant_isolation(org_a, org_b):
    """Test that tenants cannot access each other's data"""
    # Create document for org A
    doc_a = create_document(org_id=org_a.id, title="Secret A")

    # Try to access as org B user
    user_b = create_user(org_id=org_b.id)

    # Should not be able to access
    with pytest.raises(PermissionError):
        get_document(doc_a.id, user=user_b)

    # Should not appear in list
    docs_b = list_documents(org_id=org_b.id)
    assert doc_a.id not in [d.id for d in docs_b]
```

**Migration Path**: N/A (built-in from start)

**Rollback Plan**: N/A (fundamental architecture decision)

## References

- [Multi-Tenancy Patterns](https://docs.microsoft.com/en-us/azure/architecture/patterns/multi-tenancy)
- [PostgreSQL Row-Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [OWASP Multi-Tenancy](https://cheatsheetseries.owasp.org/cheatsheets/Multitenant_Architecture_Cheat_Sheet.html)
- Internal security review: [link]
- Cost analysis: [link]

## Notes

**Security Measures**:

1. **Defense in Depth**:
   - Application-level filtering (primary)
   - Row-Level Security policies (secondary)
   - Foreign key constraints (data integrity)
   - Audit logging (detection)
   - Automated testing (prevention)

2. **Code Review Checklist**:
   - [ ] All queries filter by organization_id
   - [ ] No raw SQL without org_id filtering
   - [ ] API endpoints check organization ownership
   - [ ] Tests include cross-tenant access attempts
   - [ ] Audit logging for all data access

3. **Automated Checks**:
```python
# Lint rule: All queries must include organization_id
def check_query_has_org_filter(query):
    if "organization_id" not in query:
        raise SecurityError("Query missing organization_id filter!")
```

**Performance Optimization**:

1. **Critical Indexes**:
```sql
-- Every table with organization_id
CREATE INDEX idx_table_org ON table_name(organization_id);

-- Composite indexes for common queries
CREATE INDEX idx_documents_org_created
    ON documents(organization_id, created_at DESC);
```

2. **Query Performance**:
   - Filtered queries use index: 5-10ms
   - Without index: 500ms+ (unacceptable)
   - Monitor slow query log for missing filters

**Scaling Strategy**:

1. **Current**: 10-100 organizations (single DB)
2. **Phase 2**: 100-1,000 organizations
   - Add read replicas
   - Implement caching per-org
3. **Phase 3**: 1,000-10,000 organizations
   - Consider sharding by organization_id
   - Move largest tenants to dedicated DBs
4. **Phase 4**: 10,000+ organizations
   - Horizontal sharding required
   - Multiple database clusters

**Enterprise Escalation Path**:

For enterprise customers requiring dedicated infrastructure:
```python
if customer.plan == "enterprise" and customer.revenue > 100_000:
    # Option 1: Dedicated database
    provision_dedicated_database(customer)

    # Option 2: Dedicated ECS cluster
    provision_dedicated_cluster(customer)

    # Update routing
    route_to_dedicated_infrastructure(customer)
```

**Compliance Notes**:

- **GDPR**: Row-level isolation sufficient
  - Can export/delete org data easily
  - Audit logs track all access
  - Data encryption applies to all

- **SOC 2**: Acceptable with proper controls
  - Documented security architecture
  - Regular security audits
  - Penetration testing
  - Automated testing

- **HIPAA**: May require dedicated DB
  - Evaluate per-customer
  - BAA requirements
  - Extra security measures

**Follow-up Actions**:
- Security audit every 6 months
- Penetration testing annually
- Review tenant isolation in all PRs
- Monitor for slow queries without org_id filter
- Consider dedicated DBs for top 10 customers

**Update (2024-06-01)**:
- Serving 47 organizations successfully
- No cross-tenant data leakage incidents
- Query performance excellent with indexes
- Security measures working as designed
- No plans to change architecture
- Added automated testing for tenant isolation
