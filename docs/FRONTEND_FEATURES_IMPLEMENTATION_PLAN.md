# PM Document Intelligence - Frontend Features Implementation Plan

## Executive Summary

This plan outlines a phased approach to implementing 8 major frontend features with a focus on **long-term sustainability**. The implementation is structured in 4 phases over an estimated 12-16 weeks, prioritizing foundational infrastructure before feature development.

**Total Estimated Effort:** 12-16 weeks (1 senior full-stack developer)
**Priority Focus:** Code maintainability, scalability, reusability, testing

---

## Sustainability Principles

All implementation will follow these core principles:

### 1. **Component Reusability**
- Build a shared component library
- Use composition over inheritance
- Create atomic design patterns

### 2. **Testing First**
- Unit tests for all business logic
- Integration tests for user flows
- E2E tests for critical paths
- Minimum 80% code coverage

### 3. **Performance by Default**
- Code splitting and lazy loading
- Optimistic UI updates
- Efficient state management
- Caching strategies

### 4. **Scalable Architecture**
- Feature-based folder structure
- Clear separation of concerns
- Dependency injection patterns
- API abstraction layers

### 5. **Documentation**
- Storybook for component library
- API documentation
- Architecture decision records (ADRs)
- Developer onboarding guides

---

## Feature Prioritization Matrix

| Feature | Business Value | Technical Complexity | Dependencies | Priority |
|---------|---------------|---------------------|--------------|----------|
| User Profile Settings | HIGH | LOW | None | **Phase 1** |
| Bulk Document Upload | HIGH | MEDIUM | File handling | **Phase 1** |
| Export Functionality | HIGH | LOW | Document API | **Phase 2** |
| Semantic Search | VERY HIGH | HIGH | Backend embeddings | **Phase 2** |
| Notification Center | MEDIUM | MEDIUM | Real-time infra | **Phase 3** |
| Document Comparison | MEDIUM | HIGH | Document viewer | **Phase 3** |
| Analytics Dashboard | HIGH | MEDIUM | Analytics API | **Phase 4** |
| Team/Collaboration | VERY HIGH | VERY HIGH | Auth + Permissions | **Phase 4** |

---

## Phase 1: Foundation & Quick Wins (Weeks 1-3)

**Goal:** Establish sustainable development practices and deliver immediate value

### 1.1 Development Infrastructure Setup (Week 1)

**Tasks:**
- [ ] Set up component library with Storybook
- [ ] Configure comprehensive testing framework (Vitest + React Testing Library)
- [ ] Implement E2E testing with Playwright
- [ ] Set up code quality tools (ESLint, Prettier, TypeScript strict mode)
- [ ] Create CI/CD pipeline for frontend tests
- [ ] Set up bundle analyzer and performance monitoring

**Deliverables:**
- Storybook running at `http://localhost:6006`
- Test coverage reporting in CI/CD
- Automated code quality checks

**Effort:** 5 days

---

### 1.2 Shared Component Library (Week 1-2)

Build reusable components that will be used across all features.

**Components to Build:**

```typescript
// File: frontend/src/components/ui/
- Button (primary, secondary, danger, ghost variants)
- Input (text, email, password, file)
- Card (container, header, body, footer)
- Modal (dialog, drawer)
- Table (sortable, filterable, paginated)
- Tabs (horizontal, vertical)
- Badge (status indicators)
- Toast (success, error, warning, info)
- Loader (spinner, skeleton)
- Dropdown (select, multi-select)
- ProgressBar
- EmptyState
- ErrorBoundary
```

**Sustainability Features:**
- TypeScript types for all props
- Accessibility (ARIA labels, keyboard navigation)
- Dark mode support
- Responsive design
- Unit tests for each component
- Storybook stories with documentation

**File Structure:**
```
frontend/src/
├── components/
│   ├── ui/                    # Reusable UI components
│   │   ├── Button/
│   │   │   ├── Button.tsx
│   │   │   ├── Button.test.tsx
│   │   │   ├── Button.stories.tsx
│   │   │   └── index.ts
│   │   └── ...
│   ├── features/              # Feature-specific components
│   └── layouts/               # Page layouts
├── hooks/                     # Custom React hooks
├── utils/                     # Utility functions
├── services/                  # API services
├── types/                     # TypeScript types
└── styles/                    # Global styles
```

**Effort:** 10 days

---

### 1.3 User Profile Settings (Week 3)

**Features:**
- View/edit user profile (name, email)
- Change password
- Notification preferences
- API key management
- Account deletion

**Implementation Details:**

```typescript
// File: frontend/src/features/settings/
- ProfileSettings.tsx
- NotificationPreferences.tsx
- SecuritySettings.tsx
- APIKeyManagement.tsx
- AccountDangerZone.tsx
```

**API Endpoints Needed:**
```bash
GET    /api/v1/users/me
PUT    /api/v1/users/me
POST   /api/v1/users/me/password
GET    /api/v1/users/me/preferences
PUT    /api/v1/users/me/preferences
POST   /api/v1/users/me/api-keys
DELETE /api/v1/users/me/api-keys/:id
DELETE /api/v1/users/me/account
```

**Testing Strategy:**
- Unit tests for each settings component
- Integration tests for save/update flows
- E2E test for complete profile update journey

**Effort:** 5 days

---

### 1.4 Bulk Document Upload (Week 3)

**Features:**
- Drag-and-drop multiple files
- Upload progress tracking
- Parallel uploads (max 3 concurrent)
- File validation and preview
- Retry failed uploads
- Auto-tagging and categorization

**Implementation Details:**

```typescript
// File: frontend/src/features/documents/upload/
- BulkUploader.tsx
- FileList.tsx
- UploadProgress.tsx
- FileValidator.ts
- useUploadQueue.ts (custom hook)
```

**Key Technical Decisions:**

1. **Upload Strategy:**
   - Use `Promise.allSettled()` for parallel uploads
   - Implement queue with max concurrency limit
   - Store upload state in React Context or Zustand

2. **Progress Tracking:**
   - Use `XMLHttpRequest` for upload progress events
   - Or use `fetch` with ReadableStream

3. **Error Handling:**
   - Automatic retry with exponential backoff
   - Clear error messages per file
   - Partial success handling

**Code Example:**
```typescript
// useUploadQueue.ts
interface UploadQueueItem {
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
}

export function useUploadQueue(maxConcurrent = 3) {
  const [queue, setQueue] = useState<UploadQueueItem[]>([]);

  const uploadFile = async (item: UploadQueueItem) => {
    // Implementation with progress tracking
  };

  const processQueue = async () => {
    // Process items with concurrency limit
  };

  return { queue, addFiles, processQueue, clearQueue };
}
```

**Sustainability Considerations:**
- Reusable upload queue logic
- Testable file validation utilities
- Optimistic UI updates
- Memory-efficient for large files (use streams)

**Effort:** 5 days

---

## Phase 2: Search & Export (Weeks 4-6)

**Goal:** Enable advanced document discovery and data portability

### 2.1 Backend: Semantic Search Infrastructure (Week 4)

**Prerequisites:**
- Document embeddings generated during processing
- Vector similarity search capability (pgvector already installed)

**Backend Tasks:**

```python
# File: backend/app/services/search_service.py
- EmbeddingService (generate embeddings for queries)
- SemanticSearchService (vector similarity search)
- HybridSearchService (combine semantic + keyword search)
- SearchRankingService (re-rank results)
```

**API Endpoints:**
```bash
POST /api/v1/search/semantic
  Body: { "query": "string", "limit": 10, "filters": {...} }

GET /api/v1/search/suggestions?q=query

POST /api/v1/documents/:id/similar
  Body: { "limit": 5 }
```

**Database Schema:**
```sql
-- Already exists in pgvector setup
ALTER TABLE documents ADD COLUMN embedding vector(1536);
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops);
```

**Effort:** 5 days

---

### 2.2 Frontend: Semantic Search Interface (Week 5)

**Features:**
- Natural language search input
- Search filters (date, type, status, tags)
- Search results with relevance scores
- Search history and saved searches
- "Similar documents" suggestions
- Export search results

**Implementation Details:**

```typescript
// File: frontend/src/features/search/
- SearchBar.tsx
- SearchFilters.tsx
- SearchResults.tsx
- SearchResultCard.tsx
- SavedSearches.tsx
- useSemanticSearch.ts
```

**UI/UX Design:**

```
┌─────────────────────────────────────────────────┐
│  🔍  Find documents about...                    │
│      "project risks and mitigation strategies"  │
│                                                  │
│  Filters: [Date ▼] [Type ▼] [Status ▼] [+]    │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  📄 Q3 Risk Assessment Report         95% match │
│     "Identified 12 critical risks in..."       │
│     Last modified: 2 days ago                   │
│     [View] [Similar] [Export]                   │
├─────────────────────────────────────────────────┤
│  📄 Project Mitigation Plan           89% match │
│     "Comprehensive mitigation strategies..."    │
│     Last modified: 1 week ago                   │
│     [View] [Similar] [Export]                   │
└─────────────────────────────────────────────────┘
```

**Performance Optimizations:**
- Debounced search input (300ms)
- Virtualized result list (react-window)
- Cached search results (React Query)
- Optimistic search suggestions

**Accessibility:**
- Keyboard navigation (↑↓ for results)
- Screen reader announcements for result count
- Focus management in modals

**Testing:**
- E2E: Complete search journey
- Unit: Search filter logic
- Integration: API integration with mock responses

**Effort:** 7 days

---

### 2.3 Export Functionality (Week 6)

**Features:**
- Export single document (PDF, DOCX, MD, JSON)
- Export multiple documents (ZIP)
- Export search results
- Export with/without analysis
- Schedule exports (future enhancement)

**Implementation Details:**

```typescript
// File: frontend/src/features/export/
- ExportModal.tsx
- ExportFormatSelector.tsx
- ExportProgress.tsx
- useExport.ts
```

**Export Formats:**

1. **PDF** - Formatted document with analysis
2. **DOCX** - Microsoft Word format
3. **Markdown** - Plain text with formatting
4. **JSON** - Structured data with metadata
5. **ZIP** - Multiple documents bundled

**Backend API:**
```bash
POST /api/v1/documents/:id/export
  Body: {
    "format": "pdf|docx|md|json",
    "include_analysis": true,
    "include_comments": true
  }

POST /api/v1/documents/bulk-export
  Body: {
    "document_ids": ["id1", "id2"],
    "format": "zip",
    "include_analysis": true
  }
```

**Technical Implementation:**

```typescript
// useExport.ts
export function useExport() {
  const exportDocument = async (
    documentId: string,
    format: ExportFormat,
    options: ExportOptions
  ) => {
    // 1. Request export from backend
    const response = await api.post(`/documents/${documentId}/export`, {
      format,
      ...options
    });

    // 2. Download file
    const blob = await response.blob();
    downloadBlob(blob, `document-${documentId}.${format}`);
  };

  return { exportDocument, exportMultiple };
}
```

**Sustainability Considerations:**
- Reusable export logic across features
- Progress indication for large exports
- Error handling with retry
- Download queue for multiple exports

**Effort:** 3 days

---

## Phase 3: Collaboration & Notifications (Weeks 7-10)

**Goal:** Enable real-time collaboration and user engagement

### 3.1 Notification Infrastructure (Week 7)

**Backend Setup:**

```python
# File: backend/app/services/notification_service.py
- NotificationService (create, send, mark read)
- NotificationChannels (in-app, email, webhook)
- NotificationPreferences (user settings)
```

**Notification Types:**
- Document processed
- Comment received
- Mentioned in document
- Share invitation
- Export ready
- System announcements

**Real-time Delivery:**
- WebSocket connection for live updates
- Or Server-Sent Events (SSE)
- Or PubNub (already configured)

**Database Schema:**
```sql
CREATE TABLE notifications (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  type VARCHAR(50) NOT NULL,
  title VARCHAR(255) NOT NULL,
  message TEXT,
  data JSONB,
  read BOOLEAN DEFAULT FALSE,
  read_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_unread
  ON notifications(user_id, read, created_at DESC);
```

**API Endpoints:**
```bash
GET    /api/v1/notifications
GET    /api/v1/notifications/unread-count
PUT    /api/v1/notifications/:id/read
PUT    /api/v1/notifications/mark-all-read
DELETE /api/v1/notifications/:id
```

**Effort:** 5 days

---

### 3.2 Frontend: Notification Center (Week 8)

**Features:**
- Real-time notification badge
- Notification dropdown/panel
- Mark as read/unread
- Filter by type
- Notification preferences
- Desktop notifications (browser API)

**Implementation Details:**

```typescript
// File: frontend/src/features/notifications/
- NotificationCenter.tsx
- NotificationDropdown.tsx
- NotificationItem.tsx
- NotificationPreferences.tsx
- useNotifications.ts
- useWebSocket.ts
```

**UI Design:**

```
┌─────────────────────────────────────────┐
│  🔔 Notifications (3)        [Mark all] │
├─────────────────────────────────────────┤
│  📄 Document "Q3 Report" processed      │
│     2 minutes ago                  [×]  │
├─────────────────────────────────────────┤
│  💬 @john mentioned you in "Project..."│
│     1 hour ago                     [×]  │
├─────────────────────────────────────────┤
│  ✅ Export ready for download          │
│     Yesterday                      [×]  │
├─────────────────────────────────────────┤
│             [View All]                  │
└─────────────────────────────────────────┘
```

**Real-time Updates:**

```typescript
// useNotifications.ts
export function useNotifications() {
  const { data, mutate } = useSWR('/api/v1/notifications');

  useWebSocket('/ws/notifications', (notification) => {
    // Optimistic update
    mutate([notification, ...data], false);

    // Show browser notification
    if (Notification.permission === 'granted') {
      new Notification(notification.title, {
        body: notification.message,
        icon: '/logo.png'
      });
    }
  });

  return { notifications: data, markAsRead, markAllAsRead };
}
```

**Effort:** 5 days

---

### 3.3 Document Comparison (Week 9-10)

**Features:**
- Side-by-side document comparison
- Highlight differences
- Compare content, analysis, metadata
- Version comparison (if versioning exists)
- Export comparison report

**Implementation Details:**

```typescript
// File: frontend/src/features/comparison/
- DocumentComparison.tsx
- ComparisonView.tsx
- DiffViewer.tsx
- ComparisonSidebar.tsx
- useDocumentDiff.ts
```

**Backend API:**
```bash
POST /api/v1/documents/compare
  Body: {
    "document_ids": ["id1", "id2"],
    "compare_fields": ["content", "summary", "action_items"]
  }
```

**Diff Algorithm:**
- Use `diff-match-patch` library for text diffing
- Or `react-diff-viewer-continued` for UI

**UI Layout:**

```
┌──────────────────────┬──────────────────────┐
│   Document A         │   Document B         │
│   (Version 1)        │   (Version 2)        │
├──────────────────────┼──────────────────────┤
│  [Content]           │  [Content]           │
│  This is the same    │  This is the same    │
│  - This was removed  │                      │
│                      │  + This was added    │
│  Another paragraph   │  Another paragraph   │
│                      │                      │
├──────────────────────┴──────────────────────┤
│  📊 Analysis Comparison                     │
│  ├─ Summary: 85% similar                    │
│  ├─ Action Items: 3 added, 1 removed        │
│  └─ Risks: 2 new risks identified           │
└─────────────────────────────────────────────┘
```

**Sustainability Considerations:**
- Reusable diff components
- Efficient diffing (worker threads for large docs)
- Cached comparison results
- Accessible comparison UI

**Effort:** 10 days

---

## Phase 4: Analytics & Team Features (Weeks 11-16)

**Goal:** Enable team collaboration and data-driven insights

### 4.1 Analytics Backend (Week 11)

**Metrics to Track:**

1. **User Activity:**
   - Documents uploaded/processed
   - Searches performed
   - Exports generated
   - Time spent

2. **Document Metrics:**
   - Processing time
   - Document types distribution
   - Most viewed documents
   - Action item completion rate

3. **System Health:**
   - API response times
   - Error rates
   - Storage usage

**Database Schema:**
```sql
CREATE TABLE analytics_events (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  event_type VARCHAR(50) NOT NULL,
  event_data JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_analytics_user_time
  ON analytics_events(user_id, created_at DESC);
CREATE INDEX idx_analytics_type
  ON analytics_events(event_type, created_at DESC);
```

**API Endpoints:**
```bash
GET /api/v1/analytics/overview
  Query: { start_date, end_date }

GET /api/v1/analytics/documents
GET /api/v1/analytics/searches
GET /api/v1/analytics/users
GET /api/v1/analytics/export
```

**Effort:** 5 days

---

### 4.2 Frontend: Analytics Dashboard (Week 12)

**Features:**
- Overview metrics (cards)
- Document upload trends (chart)
- Search analytics
- User activity heatmap
- Export usage
- Processing time distribution

**Implementation Details:**

```typescript
// File: frontend/src/features/analytics/
- AnalyticsDashboard.tsx
- MetricCard.tsx
- DocumentTrendsChart.tsx
- SearchAnalytics.tsx
- ActivityHeatmap.tsx
- useAnalytics.ts
```

**Charts Library:**
- Use Recharts or Chart.js
- Or Tremor (modern analytics components)

**Dashboard Layout:**

```
┌─────────────────────────────────────────────────┐
│  📊 Analytics Dashboard    [Last 30 days ▼]    │
├──────────────┬──────────────┬──────────────────┤
│ 📄 Documents │ 🔍 Searches  │ ⬇️ Exports       │
│    127       │    1,543     │    89            │
│    +12%      │    +23%      │    -5%           │
├──────────────┴──────────────┴──────────────────┤
│  Document Upload Trends                         │
│  ┌─────────────────────────────────────────┐   │
│  │         📈                              │   │
│  │                                         │   │
│  └─────────────────────────────────────────┘   │
├─────────────────────────────────────────────────┤
│  Top Searches              │  Processing Times │
│  1. "project risks"        │  Avg: 42s         │
│  2. "meeting notes"        │  P95: 89s         │
│  3. "action items"         │  P99: 134s        │
└─────────────────────────────────────────────────┘
```

**Performance:**
- Lazy load charts
- Virtualized tables for large datasets
- Cached analytics data (React Query with stale time)

**Effort:** 7 days

---

### 4.3 Team & Collaboration Backend (Week 13-14)

**Features:**
- Team creation and management
- Role-based access control (RBAC)
- Document sharing within team
- Team member invitations
- Activity audit log

**Database Schema:**

```sql
CREATE TABLE teams (
  id UUID PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  owner_id UUID REFERENCES users(id),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE team_members (
  id UUID PRIMARY KEY,
  team_id UUID REFERENCES teams(id),
  user_id UUID REFERENCES users(id),
  role VARCHAR(50) NOT NULL, -- owner, admin, member, viewer
  joined_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(team_id, user_id)
);

CREATE TABLE team_invitations (
  id UUID PRIMARY KEY,
  team_id UUID REFERENCES teams(id),
  email VARCHAR(255) NOT NULL,
  role VARCHAR(50) NOT NULL,
  invited_by UUID REFERENCES users(id),
  token VARCHAR(255) UNIQUE,
  expires_at TIMESTAMP,
  accepted_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE document_shares (
  id UUID PRIMARY KEY,
  document_id UUID REFERENCES documents(id),
  shared_with_team UUID REFERENCES teams(id),
  shared_with_user UUID REFERENCES users(id),
  permission VARCHAR(50) NOT NULL, -- view, comment, edit
  shared_by UUID REFERENCES users(id),
  created_at TIMESTAMP DEFAULT NOW(),
  CHECK (
    (shared_with_team IS NOT NULL AND shared_with_user IS NULL) OR
    (shared_with_team IS NULL AND shared_with_user IS NOT NULL)
  )
);
```

**API Endpoints:**
```bash
# Teams
POST   /api/v1/teams
GET    /api/v1/teams
GET    /api/v1/teams/:id
PUT    /api/v1/teams/:id
DELETE /api/v1/teams/:id

# Team Members
GET    /api/v1/teams/:id/members
POST   /api/v1/teams/:id/members (invite)
PUT    /api/v1/teams/:id/members/:userId (update role)
DELETE /api/v1/teams/:id/members/:userId

# Document Sharing
POST   /api/v1/documents/:id/share
GET    /api/v1/documents/:id/shares
DELETE /api/v1/documents/:id/shares/:shareId
```

**Authorization Logic:**

```python
# backend/app/utils/permissions.py

class Permission(Enum):
    VIEW = "view"
    COMMENT = "comment"
    EDIT = "edit"
    DELETE = "delete"
    SHARE = "share"

def check_document_permission(
    user_id: str,
    document_id: str,
    required_permission: Permission
) -> bool:
    """
    Check if user has permission on document.

    Rules:
    1. Document owner has all permissions
    2. Team members have permissions based on share settings
    3. Individual shares have explicit permissions
    """
    # Implementation
    pass
```

**Effort:** 10 days

---

### 4.4 Frontend: Team Collaboration UI (Week 15-16)

**Features:**
- Team management dashboard
- Member invitation flow
- Document sharing modal
- Shared documents view
- Team activity feed
- Role management

**Implementation Details:**

```typescript
// File: frontend/src/features/teams/
- TeamDashboard.tsx
- TeamSettings.tsx
- TeamMembers.tsx
- InviteMemberModal.tsx
- DocumentSharingModal.tsx
- SharedDocuments.tsx
- TeamActivityFeed.tsx
- useTeam.ts
- useTeamMembers.ts
```

**Team Dashboard UI:**

```
┌─────────────────────────────────────────────────┐
│  👥 My Team: Product Team       [Settings ⚙️]  │
├─────────────────────────────────────────────────┤
│  Team Members (12)                   [+ Invite] │
│  ┌───────────────────────────────────────────┐ │
│  │ 👤 John Doe (Owner)          john@...     │ │
│  │ 👤 Jane Smith (Admin)        jane@...     │ │
│  │ 👤 Bob Wilson (Member)       bob@...      │ │
│  └───────────────────────────────────────────┘ │
├─────────────────────────────────────────────────┤
│  Shared Documents (47)          [Share New 📤] │
│  ┌───────────────────────────────────────────┐ │
│  │ 📄 Q4 Planning Doc          Shared: 5/12  │ │
│  │ 📄 Meeting Notes 2024-01    Shared: 3/12  │ │
│  └───────────────────────────────────────────┘ │
├─────────────────────────────────────────────────┤
│  Recent Activity                                │
│  • John shared "Q4 Report" - 2h ago            │
│  • Jane commented on "Project Plan" - 5h ago   │
│  • Bob joined the team - 1 day ago             │
└─────────────────────────────────────────────────┘
```

**Document Sharing Flow:**

```
User clicks "Share" on document
  ↓
Modal opens with options:
  - Share with team
  - Share with individual
  - Set permissions (view/comment/edit)
  ↓
API call to create share
  ↓
Optimistic UI update
  ↓
Notification sent to recipients
```

**Permission Display:**

```typescript
// Document card shows share status
<DocumentCard>
  <DocumentTitle>Q4 Report</DocumentTitle>
  <ShareBadge>
    {isShared && (
      <Badge>
        <Users size={14} />
        Shared with {shareCount} people
      </Badge>
    )}
  </ShareBadge>
</DocumentCard>
```

**Effort:** 10 days

---

## Technical Architecture

### Component Library Structure

```
frontend/src/components/
├── ui/                        # Atomic UI components
│   ├── Button/
│   ├── Input/
│   ├── Card/
│   └── ...
├── features/                  # Feature-specific components
│   ├── documents/
│   │   ├── DocumentCard.tsx
│   │   ├── DocumentList.tsx
│   │   ├── DocumentViewer.tsx
│   │   └── upload/
│   │       ├── BulkUploader.tsx
│   │       └── useUploadQueue.ts
│   ├── search/
│   │   ├── SearchBar.tsx
│   │   └── SearchResults.tsx
│   ├── analytics/
│   ├── teams/
│   └── notifications/
└── layouts/
    ├── AppLayout.tsx
    ├── DashboardLayout.tsx
    └── AuthLayout.tsx
```

### State Management

**Recommended: Zustand + React Query**

```typescript
// Global state with Zustand
import create from 'zustand';

interface AppState {
  user: User | null;
  theme: 'light' | 'dark';
  setUser: (user: User) => void;
  setTheme: (theme: 'light' | 'dark') => void;
}

export const useAppStore = create<AppState>((set) => ({
  user: null,
  theme: 'light',
  setUser: (user) => set({ user }),
  setTheme: (theme) => set({ theme }),
}));

// Server state with React Query
import { useQuery } from '@tanstack/react-query';

export function useDocuments() {
  return useQuery({
    queryKey: ['documents'],
    queryFn: () => api.get('/documents'),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
```

### API Service Layer

```typescript
// services/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 30000,
});

// Request interceptor (add auth token)
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor (handle errors)
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// Feature-specific services
// services/documents.ts
export const documentsService = {
  list: () => api.get('/documents'),
  get: (id: string) => api.get(`/documents/${id}`),
  upload: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/documents/upload', formData);
  },
  process: (id: string) => api.post(`/documents/${id}/process`),
  delete: (id: string) => api.delete(`/documents/${id}`),
};
```

### Error Handling

```typescript
// utils/errors.ts
export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string
  ) {
    super(message);
    this.name = 'APIError';
  }
}

// Custom error boundary
import { ErrorBoundary } from 'react-error-boundary';

function ErrorFallback({ error, resetErrorBoundary }) {
  return (
    <div>
      <h2>Something went wrong</h2>
      <pre>{error.message}</pre>
      <button onClick={resetErrorBoundary}>Try again</button>
    </div>
  );
}

// Usage in App
<ErrorBoundary FallbackComponent={ErrorFallback}>
  <YourComponent />
</ErrorBoundary>
```

### Performance Optimization

**1. Code Splitting:**
```typescript
// Lazy load features
const Analytics = lazy(() => import('./features/analytics/AnalyticsDashboard'));
const TeamDashboard = lazy(() => import('./features/teams/TeamDashboard'));

// Route-based code splitting
<Route
  path="/analytics"
  element={
    <Suspense fallback={<Loader />}>
      <Analytics />
    </Suspense>
  }
/>
```

**2. Memoization:**
```typescript
// Expensive calculations
const sortedDocuments = useMemo(() => {
  return documents.sort((a, b) =>
    new Date(b.created_at) - new Date(a.created_at)
  );
}, [documents]);

// Prevent re-renders
const MemoizedDocumentCard = memo(DocumentCard);
```

**3. Virtualization:**
```typescript
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={documents.length}
  itemSize={100}
  width="100%"
>
  {({ index, style }) => (
    <DocumentCard
      style={style}
      document={documents[index]}
    />
  )}
</FixedSizeList>
```

---

## Testing Strategy

### Unit Tests (Vitest + React Testing Library)

```typescript
// Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from './Button';

describe('Button', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click</Button>);
    fireEvent.click(screen.getByText('Click'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Click</Button>);
    expect(screen.getByText('Click')).toBeDisabled();
  });
});
```

### Integration Tests

```typescript
// DocumentUpload.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BulkUploader } from './BulkUploader';

describe('BulkUploader', () => {
  it('uploads multiple files successfully', async () => {
    const user = userEvent.setup();
    const mockUpload = vi.fn().mockResolvedValue({ success: true });

    render(<BulkUploader onUpload={mockUpload} />);

    const files = [
      new File(['content1'], 'doc1.txt', { type: 'text/plain' }),
      new File(['content2'], 'doc2.txt', { type: 'text/plain' }),
    ];

    const input = screen.getByLabelText('Upload files');
    await user.upload(input, files);

    await waitFor(() => {
      expect(mockUpload).toHaveBeenCalledTimes(2);
    });
  });
});
```

### E2E Tests (Playwright)

```typescript
// e2e/document-workflow.spec.ts
import { test, expect } from '@playwright/test';

test('complete document workflow', async ({ page }) => {
  // Login
  await page.goto('/login');
  await page.fill('input[name="email"]', 'test@example.com');
  await page.fill('input[name="password"]', 'password123');
  await page.click('button[type="submit"]');

  // Upload document
  await page.goto('/documents');
  await page.setInputFiles('input[type="file"]', './test-doc.txt');
  await expect(page.locator('text=Upload successful')).toBeVisible();

  // Process document
  await page.click('button:has-text("Process Document")');
  await expect(page.locator('text=Processing complete')).toBeVisible({
    timeout: 60000,
  });

  // View analysis
  await page.click('text=View Analysis');
  await expect(page.locator('text=Summary')).toBeVisible();
  await expect(page.locator('text=Action Items')).toBeVisible();
});
```

### Test Coverage Goals

- **Unit tests:** 80%+ coverage
- **Integration tests:** Critical user flows
- **E2E tests:** Happy paths and critical failures
- **Visual regression:** Storybook snapshots

---

## Documentation Requirements

### 1. Component Documentation (Storybook)

```typescript
// Button.stories.tsx
import type { Meta, StoryObj } from '@storybook/react';
import { Button } from './Button';

const meta: Meta<typeof Button> = {
  title: 'UI/Button',
  component: Button,
  parameters: {
    docs: {
      description: {
        component: 'A versatile button component with multiple variants and sizes.',
      },
    },
  },
  argTypes: {
    variant: {
      control: 'select',
      options: ['primary', 'secondary', 'danger', 'ghost'],
      description: 'Visual style of the button',
    },
  },
};

export default meta;
type Story = StoryObj<typeof Button>;

export const Primary: Story = {
  args: {
    children: 'Primary Button',
    variant: 'primary',
  },
};
```

### 2. API Documentation

Generate OpenAPI/Swagger docs for all endpoints:

```yaml
# swagger.yaml
/api/v1/documents/upload:
  post:
    summary: Upload a new document
    tags:
      - Documents
    requestBody:
      content:
        multipart/form-data:
          schema:
            type: object
            properties:
              file:
                type: string
                format: binary
    responses:
      201:
        description: Document uploaded successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Document'
```

### 3. Architecture Decision Records (ADRs)

```markdown
# ADR 001: Use Zustand for Global State Management

## Status
Accepted

## Context
We need a global state management solution for user authentication, theme, and other app-wide state.

## Decision
We will use Zustand instead of Redux or Context API.

## Consequences
Positive:
- Minimal boilerplate
- TypeScript support
- Good performance
- Small bundle size (1.2kb)

Negative:
- Less ecosystem compared to Redux
- Team needs to learn new library

## Alternatives Considered
- Redux Toolkit: Too much boilerplate
- Context API: Performance issues with many consumers
```

### 4. Developer Onboarding Guide

```markdown
# Developer Onboarding

## Setup (15 minutes)
1. Clone repository
2. Install dependencies: `npm install`
3. Copy `.env.example` to `.env`
4. Run development server: `npm run dev`
5. Run tests: `npm test`

## Project Structure
See ARCHITECTURE.md for detailed structure.

## Development Workflow
1. Create feature branch: `git checkout -b feature/your-feature`
2. Write tests first (TDD)
3. Implement feature
4. Run linter: `npm run lint`
5. Run tests: `npm test`
6. Create pull request

## Code Style
- Use TypeScript strict mode
- Follow ESLint rules
- Write meaningful commit messages
- Add tests for new features
```

---

## Migration Strategy

### Phase 1 Prerequisites
- [ ] Current codebase is stable
- [ ] All existing features tested
- [ ] CI/CD pipeline configured
- [ ] Development environment documented

### Incremental Rollout
1. Feature flags for gradual rollout
2. A/B testing for new features
3. Monitor performance metrics
4. Rollback plan if issues occur

### Data Migration (if needed)
- Document schema changes
- Write migration scripts
- Test on staging environment
- Plan downtime window (if required)

---

## Risk Management

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Performance degradation with large datasets | HIGH | MEDIUM | Implement virtualization, pagination, caching |
| Real-time features increase complexity | MEDIUM | HIGH | Use managed service (PubNub), extensive testing |
| Team features require complex permissions | HIGH | MEDIUM | Use well-tested RBAC library, thorough testing |
| Third-party dependencies break | MEDIUM | LOW | Pin versions, regular updates, monitoring |

### Schedule Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Features take longer than estimated | HIGH | Buffer time in schedule, prioritize MVPs |
| Dependencies on backend changes | HIGH | Parallel development, mock APIs |
| Testing reveals major issues | MEDIUM | Early testing, continuous integration |

---

## Success Metrics

### Development Metrics
- Test coverage: >80%
- Build time: <2 minutes
- Bundle size: <500KB (gzipped)
- Lighthouse score: >90

### User Metrics
- Page load time: <2s
- Time to interactive: <3s
- Error rate: <0.1%
- User satisfaction: >4.5/5

### Business Metrics
- Feature adoption rate
- User retention
- Document processing volume
- Team collaboration engagement

---

## Budget & Resources

### Time Estimate
- **Phase 1:** 3 weeks (Foundation)
- **Phase 2:** 3 weeks (Search & Export)
- **Phase 3:** 4 weeks (Collaboration)
- **Phase 4:** 6 weeks (Analytics & Teams)
- **Total:** 16 weeks

### Team Requirements
- 1 Senior Frontend Developer (full-time)
- 1 Backend Developer (50% time for API support)
- 1 Designer (25% time for UI/UX)
- 1 QA Engineer (25% time for testing)

### Third-party Services
- Storybook Cloud (optional): $0-99/month
- Testing infrastructure: Included in CI/CD
- Analytics (if using external): $0-49/month
- Total: ~$100-200/month

---

## Maintenance Plan

### Code Maintenance
- Weekly dependency updates
- Monthly security audits
- Quarterly code reviews
- Annual architecture review

### Documentation Updates
- Update docs with each feature
- Quarterly documentation review
- Keep ADRs current
- Maintain changelog

### Technical Debt Management
- Allocate 20% time for refactoring
- Track technical debt in backlog
- Regular code quality reviews
- Address deprecations promptly

---

## Appendix

### A. Technology Stack

**Frontend:**
- React 18+ (with Concurrent features)
- TypeScript 5+
- Vite (build tool)
- Tailwind CSS (styling)
- Shadcn/ui (component library base)
- React Router (routing)
- Zustand (state management)
- React Query (server state)
- Axios (HTTP client)
- React Hook Form (forms)
- Zod (validation)
- Recharts (charts)
- React Window (virtualization)
- Storybook (component docs)

**Testing:**
- Vitest (unit tests)
- React Testing Library
- Playwright (E2E)
- MSW (API mocking)

**Development:**
- ESLint + Prettier
- Husky (git hooks)
- Commitlint
- TypeScript strict mode

### B. File Size Budgets

- Main bundle: <300KB gzipped
- Vendor bundle: <150KB gzipped
- Feature chunks: <50KB each
- Total initial load: <450KB

### C. Browser Support

- Chrome/Edge: Last 2 versions
- Firefox: Last 2 versions
- Safari: Last 2 versions
- Mobile browsers: iOS 14+, Android 10+

### D. Accessibility Requirements

- WCAG 2.1 Level AA compliance
- Keyboard navigation support
- Screen reader support
- Color contrast ratios
- Focus indicators
- ARIA labels

---

**Document Version:** 1.0
**Created:** 2025-11-08
**Author:** Claude (AI Assistant)
**Status:** Draft - Pending Review
