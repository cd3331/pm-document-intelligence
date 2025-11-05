# API Reference

Complete API documentation for PM Document Intelligence platform.

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Rate Limiting](#rate-limiting)
4. [Pagination](#pagination)
5. [Error Handling](#error-handling)
6. [API Endpoints](#api-endpoints)
   - [Authentication](#authentication-endpoints)
   - [Documents](#document-endpoints)
   - [Processing](#processing-endpoints)
   - [Search](#search-endpoints)
   - [Analytics](#analytics-endpoints)
   - [Organizations](#organization-endpoints)
   - [Models](#model-endpoints)
7. [Webhooks](#webhooks)
8. [WebSocket Events](#websocket-events)

---

## Overview

**Base URL**: `https://api.pmdocintel.com`

**API Version**: `v1`

**Content Type**: `application/json`

**Interactive Documentation**:
- Swagger UI: `https://api.pmdocintel.com/docs`
- ReDoc: `https://api.pmdocintel.com/redoc`

---

## Authentication

All API requests require authentication using JWT (JSON Web Tokens).

### Obtaining a Token

**Endpoint**: `POST /api/auth/login`

**Request**:
```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "user_abc123",
    "email": "user@example.com",
    "name": "John Doe",
    "organization_id": "org_xyz789",
    "role": "member"
  }
}
```

### Using the Token

Include the token in the `Authorization` header:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Example with curl**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.pmdocintel.com/api/documents
```

**Example with Python**:
```python
import requests

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

response = requests.get('https://api.pmdocintel.com/api/documents', headers=headers)
```

### Token Refresh

**Endpoint**: `POST /api/auth/refresh`

**Request**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

## Rate Limiting

API requests are rate limited to ensure fair usage and system stability.

### Limits by Plan

| Plan | Requests/Hour | Requests/Day | Documents/Month |
|------|---------------|--------------|-----------------|
| Free | 100 | 1,000 | 100 |
| Pro | 1,000 | 10,000 | 1,000 |
| Enterprise | 10,000 | 100,000 | Unlimited |

### Rate Limit Headers

Every API response includes rate limit information:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1640000000
```

### Rate Limit Exceeded

**Status Code**: `429 Too Many Requests`

**Response**:
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Try again in 45 seconds.",
  "retry_after": 45
}
```

---

## Pagination

List endpoints support cursor-based pagination for efficient data retrieval.

### Request Parameters

```
GET /api/documents?limit=50&cursor=eyJpZCI6MTIzfQ
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 20 | Number of items per page (1-100) |
| `cursor` | string | - | Cursor for next page |

### Response Format

```json
{
  "data": [...],
  "pagination": {
    "limit": 20,
    "has_more": true,
    "next_cursor": "eyJpZCI6MTQwfQ",
    "total_count": 487
  }
}
```

### Example

```python
def get_all_documents():
    documents = []
    cursor = None

    while True:
        params = {'limit': 100}
        if cursor:
            params['cursor'] = cursor

        response = requests.get('https://api.pmdocintel.com/api/documents',
                               params=params,
                               headers=headers)
        data = response.json()

        documents.extend(data['data'])

        if not data['pagination']['has_more']:
            break

        cursor = data['pagination']['next_cursor']

    return documents
```

---

## Error Handling

### Error Response Format

```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "details": {
    "field": "Additional context"
  },
  "request_id": "req_abc123xyz",
  "documentation_url": "https://docs.pmdocintel.com/errors/error_code"
}
```

### HTTP Status Codes

| Status Code | Description |
|-------------|-------------|
| `200 OK` | Request succeeded |
| `201 Created` | Resource created successfully |
| `202 Accepted` | Request accepted for async processing |
| `400 Bad Request` | Invalid request parameters |
| `401 Unauthorized` | Missing or invalid authentication |
| `403 Forbidden` | Insufficient permissions |
| `404 Not Found` | Resource not found |
| `409 Conflict` | Resource conflict (e.g., duplicate) |
| `422 Unprocessable Entity` | Validation failed |
| `429 Too Many Requests` | Rate limit exceeded |
| `500 Internal Server Error` | Server error |
| `503 Service Unavailable` | Temporary service outage |

### Common Error Codes

| Error Code | Description |
|------------|-------------|
| `invalid_request` | Request is malformed or missing required fields |
| `authentication_failed` | Invalid credentials |
| `token_expired` | JWT token has expired |
| `permission_denied` | User lacks required permissions |
| `resource_not_found` | Requested resource doesn't exist |
| `validation_error` | Input validation failed |
| `rate_limit_exceeded` | Too many requests |
| `quota_exceeded` | Monthly quota exceeded |
| `processing_failed` | Document processing failed |
| `ai_service_error` | AI service unavailable |

---

## API Endpoints

## Authentication Endpoints

### Register User

Create a new user account.

**Endpoint**: `POST /api/auth/register`

**Request**:
```json
{
  "email": "user@example.com",
  "password": "secure_password123",
  "name": "John Doe",
  "organization_name": "Acme Corp"
}
```

**Response** (201 Created):
```json
{
  "user": {
    "id": "user_abc123",
    "email": "user@example.com",
    "name": "John Doe",
    "organization_id": "org_xyz789",
    "role": "admin",
    "created_at": "2024-01-15T10:30:00Z"
  },
  "organization": {
    "id": "org_xyz789",
    "name": "Acme Corp",
    "plan": "free"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors**:
- `400`: Email already exists
- `422`: Validation failed (weak password, invalid email)

---

### Login

Authenticate and obtain access token.

**Endpoint**: `POST /api/auth/login`

**Request**:
```json
{
  "email": "user@example.com",
  "password": "secure_password123"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "user_abc123",
    "email": "user@example.com",
    "name": "John Doe",
    "organization_id": "org_xyz789",
    "role": "member"
  }
}
```

**Errors**:
- `401`: Invalid credentials

---

### Get Current User

Get authenticated user information.

**Endpoint**: `GET /api/auth/me`

**Headers**:
```
Authorization: Bearer {token}
```

**Response** (200 OK):
```json
{
  "id": "user_abc123",
  "email": "user@example.com",
  "name": "John Doe",
  "organization_id": "org_xyz789",
  "organization_name": "Acme Corp",
  "role": "member",
  "permissions": [
    "documents:read",
    "documents:write",
    "analytics:read"
  ],
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-15T10:30:00Z"
}
```

---

## Document Endpoints

### Upload Document

Upload a new document for processing.

**Endpoint**: `POST /api/documents/upload`

**Content-Type**: `multipart/form-data`

**Request**:
```http
POST /api/documents/upload
Authorization: Bearer {token}
Content-Type: multipart/form-data

--boundary
Content-Disposition: form-data; name="file"; filename="meeting-notes.pdf"
Content-Type: application/pdf

[binary data]
--boundary
Content-Disposition: form-data; name="document_type"

meeting_notes
--boundary
Content-Disposition: form-data; name="metadata"

{"project": "Project Alpha", "date": "2024-01-15"}
--boundary--
```

**Parameters**:
- `file` (required): Document file (PDF, DOCX, TXT)
- `document_type` (optional): One of: `meeting_notes`, `project_plan`, `status_report`, `technical_spec`, `requirements_doc`
- `metadata` (optional): JSON object with custom metadata
- `auto_process` (optional): Boolean, default `true`

**Response** (201 Created):
```json
{
  "id": "doc_abc123xyz",
  "filename": "meeting-notes.pdf",
  "document_type": "meeting_notes",
  "file_size": 1048576,
  "status": "uploaded",
  "s3_key": "documents/org_xyz789/doc_abc123xyz/original.pdf",
  "metadata": {
    "project": "Project Alpha",
    "date": "2024-01-15"
  },
  "uploaded_by": "user_abc123",
  "created_at": "2024-01-15T10:30:00Z",
  "processing_started": true,
  "processing_job_id": "job_def456ghi"
}
```

**Errors**:
- `400`: Invalid file type
- `413`: File too large (max 50 MB)
- `422`: Invalid document_type

**Example**:
```python
import requests

url = 'https://api.pmdocintel.com/api/documents/upload'
headers = {'Authorization': f'Bearer {token}'}

files = {'file': open('meeting-notes.pdf', 'rb')}
data = {
    'document_type': 'meeting_notes',
    'metadata': '{"project": "Project Alpha"}'
}

response = requests.post(url, headers=headers, files=files, data=data)
document = response.json()
```

---

### List Documents

List all documents for the authenticated user's organization.

**Endpoint**: `GET /api/documents`

**Query Parameters**:
- `limit` (optional): Items per page (1-100, default 20)
- `cursor` (optional): Pagination cursor
- `document_type` (optional): Filter by type
- `status` (optional): Filter by status (`uploaded`, `processing`, `completed`, `failed`)
- `search` (optional): Search by filename
- `sort` (optional): Sort field (`created_at`, `filename`, `file_size`)
- `order` (optional): Sort order (`asc`, `desc`, default `desc`)

**Response** (200 OK):
```json
{
  "data": [
    {
      "id": "doc_abc123xyz",
      "filename": "meeting-notes.pdf",
      "document_type": "meeting_notes",
      "file_size": 1048576,
      "status": "completed",
      "uploaded_by": "user_abc123",
      "uploaded_by_name": "John Doe",
      "created_at": "2024-01-15T10:30:00Z",
      "processed_at": "2024-01-15T10:31:45Z",
      "metadata": {
        "project": "Project Alpha"
      },
      "has_summary": true,
      "has_action_items": true,
      "word_count": 1250
    }
  ],
  "pagination": {
    "limit": 20,
    "has_more": true,
    "next_cursor": "eyJpZCI6MTQwfQ",
    "total_count": 487
  }
}
```

---

### Get Document

Get detailed information about a specific document.

**Endpoint**: `GET /api/documents/{document_id}`

**Response** (200 OK):
```json
{
  "id": "doc_abc123xyz",
  "filename": "meeting-notes.pdf",
  "document_type": "meeting_notes",
  "file_size": 1048576,
  "status": "completed",
  "uploaded_by": "user_abc123",
  "uploaded_by_name": "John Doe",
  "created_at": "2024-01-15T10:30:00Z",
  "processed_at": "2024-01-15T10:31:45Z",
  "metadata": {
    "project": "Project Alpha",
    "date": "2024-01-15"
  },
  "extracted_text": "Meeting notes from Project Alpha...",
  "word_count": 1250,
  "page_count": 5,
  "s3_key": "documents/org_xyz789/doc_abc123xyz/original.pdf",
  "download_url": "https://s3.amazonaws.com/...",
  "processing_results": {
    "summary": {
      "id": "result_sum123",
      "created_at": "2024-01-15T10:31:20Z"
    },
    "action_items": {
      "id": "result_act456",
      "created_at": "2024-01-15T10:31:30Z"
    },
    "risk_assessment": {
      "id": "result_risk789",
      "created_at": "2024-01-15T10:31:45Z"
    }
  }
}
```

**Errors**:
- `404`: Document not found

---

### Delete Document

Delete a document and all associated data.

**Endpoint**: `DELETE /api/documents/{document_id}`

**Response** (200 OK):
```json
{
  "id": "doc_abc123xyz",
  "deleted": true,
  "message": "Document and all associated data deleted successfully"
}
```

**Errors**:
- `404`: Document not found
- `403`: Permission denied

---

## Processing Endpoints

### Process Document

Trigger AI processing for an uploaded document.

**Endpoint**: `POST /api/process/{document_id}`

**Request**:
```json
{
  "tasks": ["summary", "action_items", "risk_assessment", "qa"],
  "options": {
    "summary_length": "medium",
    "extract_risks": true,
    "priority": "high"
  }
}
```

**Response** (202 Accepted):
```json
{
  "document_id": "doc_abc123xyz",
  "job_id": "job_def456ghi",
  "status": "queued",
  "tasks": ["summary", "action_items", "risk_assessment", "qa"],
  "estimated_duration_seconds": 45,
  "created_at": "2024-01-15T10:30:00Z",
  "status_url": "/api/process/job_def456ghi/status"
}
```

---

### Get Processing Status

Check the status of a processing job.

**Endpoint**: `GET /api/process/{job_id}/status`

**Response** (200 OK):
```json
{
  "job_id": "job_def456ghi",
  "document_id": "doc_abc123xyz",
  "status": "processing",
  "progress": 65,
  "current_task": "risk_assessment",
  "tasks": {
    "summary": {
      "status": "completed",
      "completed_at": "2024-01-15T10:30:30Z",
      "result_id": "result_sum123"
    },
    "action_items": {
      "status": "completed",
      "completed_at": "2024-01-15T10:30:45Z",
      "result_id": "result_act456"
    },
    "risk_assessment": {
      "status": "processing",
      "started_at": "2024-01-15T10:30:50Z"
    },
    "qa": {
      "status": "queued"
    }
  },
  "started_at": "2024-01-15T10:30:00Z",
  "estimated_completion": "2024-01-15T10:31:30Z"
}
```

---

### Get Processing Result

Get the result of a specific processing task.

**Endpoint**: `GET /api/process/results/{result_id}`

**Response** (200 OK):
```json
{
  "id": "result_sum123",
  "document_id": "doc_abc123xyz",
  "task_type": "summary",
  "status": "completed",
  "model_used": "gpt-4",
  "model_version": "1.1.0",
  "created_at": "2024-01-15T10:30:30Z",
  "processing_time_ms": 2450,
  "cost_usd": 0.045,
  "result": {
    "summary": {
      "short": "Project Alpha team discussed Q1 milestones and identified 3 blockers.",
      "detailed": "The Project Alpha team held their weekly sync meeting...",
      "key_points": [
        "Q1 milestone progress at 75%",
        "Three critical blockers identified",
        "Budget increase approved"
      ]
    }
  },
  "confidence_score": 0.92,
  "metadata": {
    "word_count_original": 1250,
    "word_count_summary": 87,
    "compression_ratio": 14.4
  }
}
```

---

### Get Action Items

Get extracted action items from a document.

**Endpoint**: `GET /api/process/documents/{document_id}/action-items`

**Response** (200 OK):
```json
{
  "document_id": "doc_abc123xyz",
  "result_id": "result_act456",
  "action_items": [
    {
      "id": "action_1",
      "description": "Complete API documentation by end of week",
      "owner": "John Doe",
      "deadline": "2024-01-19",
      "priority": "high",
      "status": "pending",
      "category": "documentation",
      "dependencies": [],
      "confidence": 0.95
    },
    {
      "id": "action_2",
      "description": "Schedule follow-up meeting with stakeholders",
      "owner": "Jane Smith",
      "deadline": "2024-01-22",
      "priority": "medium",
      "status": "pending",
      "category": "meeting",
      "dependencies": [],
      "confidence": 0.88
    }
  ],
  "total_count": 8,
  "by_priority": {
    "high": 2,
    "medium": 4,
    "low": 2
  },
  "created_at": "2024-01-15T10:30:45Z"
}
```

---

## Search Endpoints

### Semantic Search

Search documents using natural language queries.

**Endpoint**: `GET /api/search`

**Query Parameters**:
- `q` (required): Search query
- `limit` (optional): Number of results (1-50, default 10)
- `document_type` (optional): Filter by document type
- `date_from` (optional): Filter by date (ISO 8601)
- `date_to` (optional): Filter by date (ISO 8601)
- `search_mode` (optional): `semantic`, `keyword`, or `hybrid` (default)

**Response** (200 OK):
```json
{
  "query": "budget overruns in Q1",
  "results": [
    {
      "document_id": "doc_abc123xyz",
      "filename": "q1-financial-review.pdf",
      "document_type": "status_report",
      "score": 0.92,
      "excerpt": "...identified significant budget overruns in Q1 totaling $50K...",
      "matched_text": "budget overruns in Q1",
      "created_at": "2024-01-15T10:30:00Z",
      "metadata": {
        "project": "Project Alpha"
      }
    },
    {
      "document_id": "doc_def456uvw",
      "filename": "project-alpha-meeting.pdf",
      "document_type": "meeting_notes",
      "score": 0.85,
      "excerpt": "...discussed Q1 budget challenges and overrun mitigation...",
      "matched_text": "Q1 budget challenges",
      "created_at": "2024-01-10T14:20:00Z",
      "metadata": {
        "project": "Project Alpha"
      }
    }
  ],
  "total_results": 12,
  "search_time_ms": 145,
  "search_mode": "hybrid"
}
```

---

### Ask Question

Ask a question about documents using AI.

**Endpoint**: `POST /api/search/ask`

**Request**:
```json
{
  "question": "What are the main risks identified for Project Alpha?",
  "document_ids": ["doc_abc123xyz", "doc_def456uvw"],
  "max_results": 5
}
```

**Response** (200 OK):
```json
{
  "question": "What are the main risks identified for Project Alpha?",
  "answer": "Based on the documents, three main risks were identified for Project Alpha:\n\n1. Budget overruns of $50K in Q1\n2. Key developer leaving the team in March\n3. Delayed API integration with external vendor\n\nThe team has mitigation plans in place for all three risks.",
  "confidence": 0.89,
  "sources": [
    {
      "document_id": "doc_abc123xyz",
      "filename": "q1-financial-review.pdf",
      "excerpt": "...identified significant budget overruns...",
      "relevance": 0.95
    },
    {
      "document_id": "doc_def456uvw",
      "filename": "risk-assessment.pdf",
      "excerpt": "...key developer resignation poses timeline risk...",
      "relevance": 0.88
    }
  ],
  "model_used": "gpt-4",
  "processing_time_ms": 3200,
  "cost_usd": 0.062
}
```

---

## Analytics Endpoints

### Get Dashboard

Get analytics dashboard data.

**Endpoint**: `GET /api/analytics/dashboard`

**Query Parameters**:
- `period` (optional): `7d`, `30d`, `90d`, `1y` (default `30d`)

**Response** (200 OK):
```json
{
  "period": "30d",
  "summary": {
    "total_documents": 487,
    "documents_processed": 452,
    "total_processing_time_hours": 15.3,
    "total_cost_usd": 245.67,
    "avg_cost_per_document": 0.54,
    "active_users": 24
  },
  "documents_by_type": {
    "meeting_notes": 198,
    "project_plans": 87,
    "status_reports": 95,
    "technical_specs": 64,
    "requirements_docs": 43
  },
  "documents_over_time": [
    {"date": "2024-01-01", "count": 15},
    {"date": "2024-01-02", "count": 18},
    ...
  ],
  "processing_success_rate": 0.928,
  "average_processing_time_seconds": 45.2,
  "top_users": [
    {"user_id": "user_abc123", "name": "John Doe", "document_count": 87},
    {"user_id": "user_def456", "name": "Jane Smith", "document_count": 62}
  ],
  "cost_by_model": {
    "gpt-4": 125.30,
    "gpt-3.5-turbo": 65.20,
    "claude-2": 55.17
  }
}
```

---

### Get Usage Statistics

Get detailed usage statistics.

**Endpoint**: `GET /api/analytics/usage`

**Query Parameters**:
- `start_date` (optional): ISO 8601 date
- `end_date` (optional): ISO 8601 date
- `granularity` (optional): `hour`, `day`, `week`, `month`

**Response** (200 OK):
```json
{
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-31T23:59:59Z",
  "usage": {
    "documents_uploaded": 487,
    "documents_processed": 452,
    "api_requests": 12547,
    "search_queries": 1893,
    "total_processing_time_seconds": 55080,
    "storage_used_gb": 15.7,
    "bandwidth_used_gb": 8.3
  },
  "costs": {
    "ai_models": 245.67,
    "storage": 3.50,
    "bandwidth": 0.83,
    "total": 250.00
  },
  "quota": {
    "documents_limit": 1000,
    "documents_used": 487,
    "documents_remaining": 513,
    "storage_limit_gb": 50,
    "storage_used_gb": 15.7,
    "percentage_used": 48.7
  }
}
```

---

## Organization Endpoints

### Get Organization

Get organization details.

**Endpoint**: `GET /api/organizations/{org_id}`

**Response** (200 OK):
```json
{
  "id": "org_xyz789",
  "name": "Acme Corp",
  "plan": "pro",
  "status": "active",
  "created_at": "2024-01-01T00:00:00Z",
  "settings": {
    "default_document_type": "meeting_notes",
    "auto_process": true,
    "retention_days": 90,
    "allowed_file_types": ["pdf", "docx", "txt"]
  },
  "quota": {
    "documents_per_month": 1000,
    "storage_gb": 50,
    "users": 10
  },
  "usage_current_month": {
    "documents": 487,
    "storage_gb": 15.7,
    "users": 8
  },
  "billing": {
    "status": "active",
    "current_period_start": "2024-01-01",
    "current_period_end": "2024-01-31",
    "amount_usd": 99.00
  }
}
```

---

### List Organization Members

List all members of the organization.

**Endpoint**: `GET /api/organizations/{org_id}/members`

**Response** (200 OK):
```json
{
  "members": [
    {
      "user_id": "user_abc123",
      "email": "john@acme.com",
      "name": "John Doe",
      "role": "admin",
      "joined_at": "2024-01-01T00:00:00Z",
      "last_active": "2024-01-15T10:30:00Z",
      "document_count": 87
    },
    {
      "user_id": "user_def456",
      "email": "jane@acme.com",
      "name": "Jane Smith",
      "role": "member",
      "joined_at": "2024-01-05T00:00:00Z",
      "last_active": "2024-01-15T09:15:00Z",
      "document_count": 62
    }
  ],
  "total_count": 8
}
```

---

### Invite User

Invite a new user to the organization.

**Endpoint**: `POST /api/organizations/{org_id}/invite`

**Request**:
```json
{
  "email": "newuser@acme.com",
  "role": "member",
  "message": "Welcome to Acme Corp's PM Document Intelligence!"
}
```

**Response** (201 Created):
```json
{
  "invitation_id": "inv_ghi789jkl",
  "email": "newuser@acme.com",
  "role": "member",
  "invited_by": "user_abc123",
  "created_at": "2024-01-15T10:30:00Z",
  "expires_at": "2024-01-22T10:30:00Z",
  "invitation_url": "https://pmdocintel.com/invite/inv_ghi789jkl"
}
```

---

## Model Endpoints

### Get Model Performance

Get performance metrics for AI models.

**Endpoint**: `GET /api/models/performance`

**Query Parameters**:
- `model_version` (optional): Specific model version
- `task_type` (optional): Task type filter
- `days` (optional): Time window (1-90, default 7)

**Response** (200 OK):
```json
{
  "metrics": {
    "accuracy": 0.924,
    "avg_confidence": 0.887,
    "avg_latency_ms": 2450,
    "avg_cost_usd": 0.045,
    "total_requests": 1847,
    "success_rate": 0.982
  },
  "by_task_type": {
    "summary": {
      "accuracy": 0.935,
      "requests": 847
    },
    "action_items": {
      "accuracy": 0.918,
      "requests": 652
    },
    "risk_assessment": {
      "accuracy": 0.902,
      "requests": 348
    }
  },
  "time_window_days": 7,
  "generated_at": "2024-01-15T10:30:00Z"
}
```

---

### Submit Feedback

Submit feedback on AI output quality.

**Endpoint**: `POST /api/models/feedback`

**Request**:
```json
{
  "result_id": "result_sum123",
  "rating": "positive",
  "corrections": {
    "summary": {
      "short": "Corrected summary text..."
    }
  },
  "comments": "Good summary but missed one key point",
  "specific_issues": ["missing_key_point"]
}
```

**Response** (200 OK):
```json
{
  "result_id": "result_sum123",
  "feedback_recorded": true,
  "rating": "positive",
  "message": "Thank you for your feedback! This will help improve our AI models."
}
```

---

## Webhooks

Configure webhooks to receive real-time notifications about events.

### Webhook Events

| Event | Description |
|-------|-------------|
| `document.uploaded` | Document successfully uploaded |
| `document.processing.started` | Processing started |
| `document.processing.completed` | Processing completed successfully |
| `document.processing.failed` | Processing failed |
| `organization.member.added` | New member joined |
| `organization.quota.exceeded` | Monthly quota exceeded |

### Webhook Payload

```json
{
  "event": "document.processing.completed",
  "timestamp": "2024-01-15T10:31:45Z",
  "webhook_id": "wh_abc123",
  "data": {
    "document_id": "doc_abc123xyz",
    "filename": "meeting-notes.pdf",
    "status": "completed",
    "results": {
      "summary": "result_sum123",
      "action_items": "result_act456"
    }
  }
}
```

### Webhook Signature

Verify webhook authenticity using HMAC-SHA256 signature in the `X-Webhook-Signature` header:

```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

## WebSocket Events

Real-time updates via WebSocket connection.

### Connect

```javascript
const socket = new WebSocket('wss://api.pmdocintel.com/ws?token=YOUR_TOKEN');

socket.onopen = () => {
  console.log('Connected');
};

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data);
};
```

### Event Types

**Document Processing Update**:
```json
{
  "type": "processing.update",
  "document_id": "doc_abc123xyz",
  "status": "processing",
  "progress": 65,
  "current_task": "risk_assessment"
}
```

**Processing Completed**:
```json
{
  "type": "processing.completed",
  "document_id": "doc_abc123xyz",
  "results": {
    "summary": "result_sum123",
    "action_items": "result_act456"
  }
}
```

---

## Code Examples

### Python SDK

```python
from pm_doc_intel import PMDocIntelClient

client = PMDocIntelClient(api_key='YOUR_API_KEY')

# Upload document
document = client.documents.upload(
    file_path='meeting-notes.pdf',
    document_type='meeting_notes',
    metadata={'project': 'Project Alpha'}
)

# Wait for processing
result = client.documents.wait_for_processing(document.id)

# Get summary
summary = client.processing.get_result(result.summary_id)
print(summary.result['summary']['detailed'])

# Search documents
results = client.search.query('budget overruns')
for result in results:
    print(f"{result.filename}: {result.excerpt}")
```

### JavaScript SDK

```javascript
import { PMDocIntelClient } from '@pm-doc-intel/sdk';

const client = new PMDocIntelClient({ apiKey: 'YOUR_API_KEY' });

// Upload document
const document = await client.documents.upload({
  file: fileBlob,
  documentType: 'meeting_notes',
  metadata: { project: 'Project Alpha' }
});

// Listen for processing updates
client.on('processing.update', (update) => {
  console.log(`Progress: ${update.progress}%`);
});

// Get results
const summary = await client.processing.getResult(document.summaryId);
console.log(summary.result.summary.detailed);
```

---

## Support

- **API Status**: https://status.pmdocintel.com
- **Support Email**: api-cd3331github@gmail.com
- **Documentation**: https://docs.pmdocintel.com
- **Community**: https://community.pmdocintel.com

---

**Last Updated**: January 2024
**API Version**: v1
