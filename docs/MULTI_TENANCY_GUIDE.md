# Multi-Tenancy & RBAC Implementation Guide

## Overview

This document provides a comprehensive guide to the enterprise multi-tenancy and role-based access control (RBAC) system implemented in PM Document Intelligence.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Installation & Setup](#installation--setup)
3. [Organization Management](#organization-management)
4. [Role-Based Access Control](#role-based-access-control)
5. [Usage Limits & Quotas](#usage-limits--quotas)
6. [Audit Logging](#audit-logging)
7. [API Usage Examples](#api-usage-examples)
8. [Security Best Practices](#security-best-practices)

---

## Architecture Overview

### Key Concepts

**Organizations**: Top-level tenants that represent separate companies or entities. Each organization has:
- Isolated data and documents
- Subscription plan (Free, Pro, Enterprise)
- Usage quotas and limits
- Custom branding options
- Members with assigned roles

**Teams**: Sub-groups within an organization for better organization of members and resources.

**Roles**: Hierarchical permission system with five built-in roles:
- `super_admin`: System-wide administrator
- `org_admin`: Organization administrator with full control
- `manager`: Can manage teams and users
- `member`: Regular user with standard access
- `viewer`: Read-only access

**Permissions**: Granular access controls for specific actions (document:read, user:invite, etc.)

### Database Schema

```
organizations
├── organization_members (users in organization)
├── teams
│   └── team_members
├── organization_invitations
├── organization_usage (quota tracking)
└── documents (with organization_id foreign key)

audit_logs (compliance tracking)
custom_roles (organization-specific roles)
permission_cache (performance optimization)
```

---

## Installation & Setup

### 1. Run Database Migrations

```bash
# Apply the multi-tenancy migration
cd backend
alembic upgrade head

# This creates all necessary tables:
# - organizations
# - teams
# - organization_members
# - team_members
# - organization_invitations
# - organization_usage
# - audit_logs
# - custom_roles
# - permission_cache
```

### 2. Migrate Existing Data

If you have existing users and documents from a single-tenant setup:

```bash
# Backup your database first!
pg_dump your_database > backup_$(date +%Y%m%d).sql

# Run the migration script
python backend/scripts/migrate_to_multi_tenancy.py

# This will:
# 1. Create a default organization
# 2. Add all users to the default organization
# 3. Assign documents to the default organization
# 4. Set the first user as org admin
```

### 3. Update Application Configuration

Add the following to your `backend/app/main.py`:

```python
from app.middleware.rbac import OrganizationContextMiddleware
from app.routes import organizations

# Add organization routes
app.include_router(organizations.router)

# Add organization context middleware
app.add_middleware(OrganizationContextMiddleware)
```

### 4. Environment Variables

Add to your `.env` file:

```env
# Multi-tenancy settings
DEFAULT_ORG_PLAN=free
ENABLE_TRIAL_PERIOD=true
TRIAL_DURATION_DAYS=14

# Quota defaults
FREE_PLAN_DOCUMENT_LIMIT=50
PRO_PLAN_DOCUMENT_LIMIT=500
ENTERPRISE_PLAN_DOCUMENT_LIMIT=-1  # Unlimited
```

---

## Organization Management

### Creating an Organization

Organizations are created via the API or admin dashboard:

```bash
POST /api/organizations
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "Acme Corporation",
  "slug": "acme-corp",
  "contact_email": "admin@acme.com",
  "contact_phone": "+1-555-0123"
}
```

The creator automatically becomes the organization admin.

### Organization Settings

Navigate to the organization dashboard at `/organizations/<org_id>` to manage:

- **General Settings**: Name, logo, branding colors
- **Contact Information**: Email, phone, address
- **Plan & Billing**: Current plan, usage statistics
- **Custom Branding**: Logo URL, primary color for UI theming

### Plan Tiers

#### Free Plan
- 50 documents/month
- 1 GB storage
- 100 API calls/day
- 3 users
- 1 team
- 100 AI queries/month
- Features: Basic AI agents only

#### Pro Plan
- 500 documents/month
- 50 GB storage
- 1,000 API calls/day
- 20 users
- 10 teams
- 1,000 AI queries/month
- Features: Semantic search, AI agents, custom branding, audit logs, API access

#### Enterprise Plan
- Unlimited documents
- Unlimited storage
- Unlimited API calls
- Unlimited users & teams
- Unlimited AI queries
- Features: All Pro features + SSO, priority support, dedicated support, custom integrations

---

## Role-Based Access Control

### Built-in Roles

| Role | Hierarchy | Key Permissions |
|------|-----------|-----------------|
| `super_admin` | 5 (highest) | All system permissions |
| `org_admin` | 4 | Full organization control, billing, user management |
| `manager` | 3 | Team management, user invites, document approval |
| `member` | 2 | Create/edit own documents, read team documents |
| `viewer` | 1 | Read-only access |

### Permission Types

Permissions are grouped by resource:

**Documents**:
- `document:read` - View documents
- `document:create` - Create new documents
- `document:update` - Edit documents
- `document:delete` - Delete documents
- `document:approve` - Approve documents for publishing
- `document:share` - Share documents externally

**Users**:
- `user:read` - View user list
- `user:invite` - Invite new users
- `user:update` - Update user profiles
- `user:remove` - Remove users from organization
- `user:manage_roles` - Change user roles

**Teams**:
- `team:read` - View teams
- `team:create` - Create teams
- `team:update` - Edit team details
- `team:delete` - Delete teams
- `team:manage_members` - Add/remove team members

**Organization**:
- `org:read` - View organization details
- `org:update` - Update organization settings
- `org:manage_billing` - Manage subscription and billing
- `org:delete` - Delete organization
- `org:manage_settings` - Configure organization settings

**Analytics & Reporting**:
- `analytics:view` - View analytics dashboard
- `analytics:view_all_users` - View all user analytics (admin only)
- `analytics:export` - Export analytics data
- `report:generate` - Generate reports
- `report:schedule` - Schedule automated reports

**Audit & Compliance**:
- `audit:view` - View audit logs
- `audit:export` - Export audit logs

### Using RBAC in Routes

Protect routes with decorators:

```python
from app.middleware.rbac import (
    require_permission, require_role, require_org_feature,
    get_organization_context, OrganizationContext
)
from app.models.roles import Permission, Role

@router.get("/api/documents")
@require_permission(Permission.DOCUMENT_READ)
async def list_documents(
    current_user: User = Depends(get_current_user),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db)
):
    # Only users with DOCUMENT_READ permission can access
    # org_ctx contains organization context and user's role
    pass

@router.post("/api/users/invite")
@require_role(Role.MANAGER)  # Requires at least Manager role
async def invite_user(...):
    pass

@router.post("/api/documents/semantic-search")
@require_org_feature("semantic_search")  # Requires Pro+ plan
async def semantic_search(...):
    pass
```

### Managing User Roles

**Via API**:
```bash
PUT /api/organizations/<org_id>/members/<user_id>/role
Content-Type: application/json
Authorization: Bearer <token>

{
  "role": "manager"
}
```

**Via Dashboard**:
1. Navigate to Organization → Members
2. Click edit icon next to user
3. Select new role
4. Confirm changes

**Important**: You cannot change your own role or assign a role higher than your own.

---

## Usage Limits & Quotas

### Quota Tracking

The system automatically tracks:
- Documents created per month
- API calls per day
- AI queries per month
- Storage used (GB)
- Active users
- Teams

### Quota Enforcement

Quotas are checked before resource-intensive operations:

```python
from app.services.quota_manager import QuotaManager

quota_manager = QuotaManager(db)

# Check before creating document
try:
    await quota_manager.increment_document_count(organization_id)
    # Proceed with document creation
except QuotaExceededException as e:
    raise HTTPException(
        status_code=429,
        detail=f"Quota exceeded: {e.message}. Please upgrade your plan."
    )
```

### Quota Warnings

Users receive warnings at:
- 70% usage (info level)
- 80% usage (warning level)
- 95% usage (critical level)

Warnings are shown in the organization dashboard and sent via email to org admins.

### Handling Overages

When a quota is exceeded:
1. **Soft Limit**: User sees upgrade prompt but can continue temporarily
2. **Hard Limit**: Operation is blocked, upgrade required
3. **Grace Period**: Organizations get 7 days grace period before hard limits

### Upgrading Plans

Organizations can upgrade via:
- Organization dashboard → Upgrade button
- API endpoint: `POST /api/organizations/<org_id>/upgrade`
- Contact sales for Enterprise plans

---

## Audit Logging

### What's Logged

The system logs:
- All CRUD operations (create, read, update, delete)
- Permission changes and role assignments
- User authentication events (login, logout, failed attempts)
- Data exports and bulk operations
- Organization and team changes
- Settings modifications
- API access

### Audit Log Fields

Each log entry contains:
- Timestamp
- User (username, email)
- Organization context
- Action performed
- Resource affected (type and ID)
- Status (success/failure)
- IP address and user agent
- Detailed information (changes, metadata)
- Sensitivity level

### Viewing Audit Logs

**Via Dashboard**:
1. Navigate to Organization → Audit Logs
2. Filter by action, user, date range
3. View detailed information for each event
4. Export logs to CSV or JSON

**Via API**:
```bash
GET /api/organizations/<org_id>/audit-logs?start_date=2025-01-01&action=user_role_updated
Authorization: Bearer <token>
```

### Exporting Audit Logs

```bash
GET /api/organizations/<org_id>/audit-logs/export?format=csv
Authorization: Bearer <token>
```

Exports include:
- CSV format for spreadsheet analysis
- JSON format for programmatic processing
- Filtered by date range and event type

### Retention Policies

Default retention:
- Audit logs: 7 years (2555 days)
- Data access logs: 7 years
- Compliance events: Permanent (never auto-deleted)

Configure custom retention per organization in settings.

### Compliance Events

Special high-priority events logged separately:
- Data breaches
- Unauthorized access attempts
- Large data exports
- Mass deletions
- Security policy violations

These require investigation and may need regulatory reporting.

---

## API Usage Examples

### Complete Workflow Example

```python
import requests

BASE_URL = "https://api.your-app.com"
TOKEN = "your_auth_token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# 1. Create organization
org_response = requests.post(
    f"{BASE_URL}/api/organizations",
    headers=headers,
    json={
        "name": "Tech Startup Inc",
        "slug": "tech-startup",
        "contact_email": "admin@techstartup.com"
    }
)
org = org_response.json()
org_id = org["id"]

# Set organization context for subsequent requests
headers["X-Organization-ID"] = org_id

# 2. Create team
team_response = requests.post(
    f"{BASE_URL}/api/organizations/{org_id}/teams",
    headers=headers,
    json={
        "name": "Engineering",
        "description": "Engineering team"
    }
)
team = team_response.json()

# 3. Invite users
invitation = requests.post(
    f"{BASE_URL}/api/organizations/{org_id}/invitations",
    headers=headers,
    json={
        "email": "engineer@example.com",
        "role": "member",
        "team_ids": [team["id"]],
        "expires_in_days": 7
    }
)

# 4. Check usage
usage = requests.get(
    f"{BASE_URL}/api/organizations/{org_id}/usage",
    headers=headers
)
print("Current usage:", usage.json())

# 5. Create document (with quota check)
doc_response = requests.post(
    f"{BASE_URL}/api/documents",
    headers=headers,
    files={"file": open("document.pdf", "rb")}
)

# 6. View audit logs
logs = requests.get(
    f"{BASE_URL}/api/organizations/{org_id}/audit-logs",
    headers=headers,
    params={"limit": 10}
)
```

### JavaScript/TypeScript Example

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: 'https://api.your-app.com',
  headers: {
    'Authorization': `Bearer ${authToken}`,
    'X-Organization-ID': organizationId
  }
});

// Create team
const team = await api.post(`/api/organizations/${orgId}/teams`, {
  name: 'Marketing',
  description: 'Marketing team'
});

// List members
const members = await api.get(`/api/organizations/${orgId}/members`);

// Update member role
await api.put(`/api/organizations/${orgId}/members/${userId}/role`, {
  role: 'manager'
});

// Get quota status
const quotaStatus = await api.get(`/api/organizations/${orgId}/usage`);

if (quotaStatus.data.warnings.length > 0) {
  console.log('Quota warnings:', quotaStatus.data.warnings);
}
```

---

## Security Best Practices

### 1. Organization Isolation

- All queries must filter by `organization_id`
- Use middleware to inject organization context
- Never trust client-provided organization IDs directly
- Validate user membership before granting access

```python
# Good
documents = db.query(Document).filter(
    Document.organization_id == org_ctx.organization_id,
    Document.user_id == current_user.id
).all()

# Bad - missing organization filter
documents = db.query(Document).filter(
    Document.user_id == current_user.id
).all()  # Could leak data from other orgs!
```

### 2. Permission Checks

- Always check permissions at the route level
- Use resource-level permissions for sensitive operations
- Cache permission checks for performance
- Re-validate permissions after role changes

```python
# Check general permission
if not org_ctx.has_permission(Permission.DOCUMENT_DELETE):
    raise HTTPException(403, "Permission denied")

# Check resource-specific permission
has_access = await check_resource_access(
    current_user=current_user,
    resource_type="document",
    resource_id=document_id,
    permission=Permission.DOCUMENT_DELETE,
    org_ctx=org_ctx,
    db=db
)
```

### 3. Quota Enforcement

- Check quotas BEFORE expensive operations
- Track usage in real-time
- Implement grace periods appropriately
- Notify users before hard limits

### 4. Audit Everything

- Log all sensitive operations
- Include context (IP, user agent)
- Store audit logs in tamper-proof storage
- Set up alerts for suspicious activity

### 5. Invitation Security

- Use cryptographically secure tokens
- Set reasonable expiration times (7-30 days)
- Verify email ownership before accepting
- Revoke unused invitations

### 6. API Rate Limiting

Implement per-organization rate limiting:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=lambda: org_ctx.organization_id)

@app.post("/api/documents")
@limiter.limit("100/hour")  # Per organization
async def create_document(...):
    pass
```

### 7. Data Export Controls

- Require elevated permissions
- Log all exports to audit trail
- Implement export size limits
- Add watermarks to exported documents

### 8. SSO Integration (Enterprise)

For Enterprise customers:
- Support SAML 2.0 and OAuth 2.0
- Validate IdP certificates
- Enforce organization domain restrictions
- Implement just-in-time provisioning

---

## Troubleshooting

### Common Issues

**Issue**: User can't access organization resources
- **Check**: User is an active member of the organization
- **Check**: User has required role/permissions
- **Check**: Organization status is "active"
- **Check**: `X-Organization-ID` header is set correctly

**Issue**: Quota exceeded errors
- **Check**: Current usage in organization dashboard
- **Check**: Plan limits match organization's plan
- **Check**: Usage reset happened at month boundary
- **Solution**: Upgrade plan or wait for quota reset

**Issue**: Audit logs missing
- **Check**: Audit logger is initialized in route handlers
- **Check**: Database permissions for audit_logs table
- **Check**: No errors in application logs
- **Solution**: Re-run initialization scripts

**Issue**: Migration script fails
- **Check**: Alembic migrations applied first
- **Check**: Database backup completed
- **Check**: All foreign key constraints valid
- **Solution**: Rollback and check error logs

---

## Monitoring & Maintenance

### Regular Maintenance Tasks

**Daily**:
- Monitor quota usage across organizations
- Check for quota warnings and notify users
- Review failed authentication attempts
- Expire old invitations

**Weekly**:
- Review audit logs for anomalies
- Check organization growth metrics
- Analyze feature usage by plan tier
- Clean up inactive invitations

**Monthly**:
- Reset monthly quotas
- Generate usage reports for billing
- Archive old audit logs
- Review and update retention policies

**Quarterly**:
- Security audit of permissions
- Review and optimize database indexes
- Analyze upgrade conversion rates
- Update plan limits based on usage patterns

### Monitoring Queries

```sql
-- Organizations approaching quota limits
SELECT o.name, ou.documents_created, o.plan
FROM organizations o
JOIN organization_usage ou ON o.id = ou.organization_id
WHERE ou.documents_created / 50.0 > 0.8  -- 80% of free tier
  AND o.plan = 'free';

-- Most active organizations
SELECT o.name, COUNT(al.id) as event_count
FROM organizations o
JOIN audit_logs al ON o.id = al.organization_id
WHERE al.timestamp >= NOW() - INTERVAL '7 days'
GROUP BY o.id, o.name
ORDER BY event_count DESC
LIMIT 10;

-- Failed authentication attempts
SELECT username, COUNT(*) as attempts
FROM audit_logs
WHERE action = 'user_login_failed'
  AND timestamp >= NOW() - INTERVAL '1 hour'
GROUP BY username
HAVING COUNT(*) > 5;
```

---

## Support & Resources

- **Documentation**: https://docs.your-app.com
- **API Reference**: https://api.your-app.com/docs
- **Support Email**: support@your-app.com
- **Enterprise Support**: enterprise@your-app.com

For additional help or feature requests, contact your account manager or submit a ticket through the support portal.
