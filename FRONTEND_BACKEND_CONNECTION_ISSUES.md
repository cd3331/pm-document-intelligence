# Frontend-Backend Connection Issues & Fixes

**Date**: 2025-11-10
**Status**: CRITICAL - Blocking user access
**Affected**: app.joyofpm.com → api.joyofpm.com

## Executive Summary

The frontend at **app.joyofpm.com** cannot connect to the backend at **api.joyofpm.com** due to multiple configuration issues with API URLs. Users cannot use the application properly.

## Root Cause Analysis

### Issue #1: Wrong JavaScript File Being Served ⚠️ CRITICAL

**Problem**: The backend serves `backend/frontend/static/js/app.js` which uses **RELATIVE paths** instead of absolute URLs.

**Current (BROKEN)**:
```javascript
// backend/frontend/static/js/app.js:21
const response = await fetch('/api/realtime/status', {
    headers: { 'Authorization': `Bearer ${token}` }
});

// backend/frontend/static/js/app.js:547
xhr.open('POST', '/api/v1/documents/upload');
```

**Expected**:
```javascript
const response = await fetch('https://api.joyofpm.com/api/v1/realtime/status', {
    headers: { 'Authorization': `Bearer ${token}` }
});

xhr.open('POST', 'https://api.joyofpm.com/api/v1/documents/upload');
```

**Impact**: When app.joyofpm.com loads the page, JavaScript tries to fetch `/api/...` from app.joyofpm.com (S3/CloudFront), not api.joyofpm.com (the actual API server).

### Issue #2: Multiple Conflicting Frontend Directories

There are THREE separate frontend directories with inconsistent configurations:

1. **`backend/frontend/`** - Served by FastAPI (BROKEN - uses relative paths)
   - Static files: `backend/frontend/static/`
   - Templates: `backend/frontend/templates/`
   - Used by: api.joyofpm.com when serving HTML directly

2. **`frontend/`** - Standalone frontend (CORRECT - has API_BASE_URL)
   - Has `const API_BASE_URL = 'https://api.joyofpm.com';`
   - NOT currently being used

3. **`app/`** - HTML files with embedded JS (MIXED - some correct, some not)
   - Has hardcoded `const API_BASE_URL = 'https://api.joyofpm.com/api/v1';`
   - Unclear if this is being served

### Issue #3: API Route Prefix Inconsistency

**Backend routes** are registered with `/api/v1/` prefix:
- `/api/v1/auth/*`
- `/api/v1/documents/*`
- `/api/v1/realtime/*`
- `/api/v1/agents/*`
- etc.

**Frontend JavaScript** makes requests to:
- ❌ `/api/realtime/status` (missing `/v1/`)
- ✅ `/api/v1/documents/upload` (correct)

### Issue #4: HTMX Routes Don't Have Prefix

The htmx routes in `backend/app/routes/htmx.py` are registered WITHOUT the `/api/v1/` prefix:
- `/api/stats` (not `/api/v1/stats`)
- `/api/documents/list` (not `/api/v1/documents/list`)

This creates inconsistency between API routes and HTMX fragment routes.

## Configuration Status

### ✅ Working Configurations

1. **CORS** - Correctly configured in `.env`:
   ```
   CORS_ORIGINS=http://localhost:3000,http://localhost:8000,https://app.joyofpm.com,https://joyofpm.com
   ```

2. **Allowed Hosts** - Correctly configured:
   ```
   ALLOWED_HOSTS=localhost,127.0.0.1,api.joyofpm.com,app.joyofpm.com,joyofpm.com
   ```

3. **Backend API** - Responding correctly at api.joyofpm.com
   - Health check: ✅ https://api.joyofpm.com/health
   - Ready check: ✅ https://api.joyofpm.com/ready

### ❌ Broken Configurations

1. **Frontend JavaScript** - Uses wrong URLs
2. **Static file mounting** - Serves wrong frontend directory
3. **API route consistency** - Mixed use of `/v1/` prefix

## Required Fixes

### Fix #1: Update backend/frontend/static/js/app.js (PRIORITY 1)

Add API base URL configuration at the top of the file:

```javascript
// API Base URL - use environment-specific API endpoint
const API_BASE_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : 'https://api.joyofpm.com';

// Then use it in all fetch calls:
const response = await fetch(`${API_BASE_URL}/api/v1/realtime/status`, {
    headers: { 'Authorization': `Bearer ${token}` }
});

xhr.open('POST', `${API_BASE_URL}/api/v1/documents/upload');
```

### Fix #2: Ensure Consistent /api/v1/ Prefix

Update Line 21 in `backend/frontend/static/js/app.js`:
```javascript
// WRONG: const response = await fetch('/api/realtime/status', {
// RIGHT:
const response = await fetch(`${API_BASE_URL}/api/v1/realtime/status`, {
```

### Fix #3: Consider Frontend Architecture

**Option A** (Recommended): Fix `backend/frontend/` in place
- Update `backend/frontend/static/js/app.js` with API_BASE_URL
- Keep current setup (backend serves its own frontend)

**Option B**: Switch to standalone frontend
- Deploy `frontend/` directory to S3/CloudFront
- Point app.joyofpm.com to standalone frontend
- Removes dependency on backend for serving HTML

### Fix #4: Add API Base URL to Templates

If templates are dynamically generated, inject API_BASE_URL from backend:

```html
<!-- In backend/frontend/templates/base.html -->
<script>
    window.API_BASE_URL = "{{ api_base_url }}";
</script>
```

Then in FastAPI:
```python
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "api_base_url": "https://api.joyofpm.com" if settings.is_production else "http://localhost:8000"
    })
```

## Testing Plan

After fixes, test these critical flows:

1. **User Registration**:
   - Visit https://app.joyofpm.com
   - Click "Sign Up"
   - Submit form → should POST to https://api.joyofpm.com/api/v1/auth/register

2. **User Login**:
   - Visit https://app.joyofpm.com/login
   - Enter credentials → should POST to https://api.joyofpm.com/api/v1/auth/login
   - Should receive JWT token

3. **Document Upload**:
   - Login → go to https://app.joyofpm.com/upload
   - Select file → should POST to https://api.joyofpm.com/api/v1/documents/upload
   - Should see upload progress

4. **Real-time Updates**:
   - Check browser console for PubNub initialization
   - Should fetch credentials from https://api.joyofpm.com/api/v1/realtime/status

5. **HTMX Fragments**:
   - Dashboard stats → should fetch from https://api.joyofpm.com/api/stats (or /api/v1/stats if we add prefix)
   - Document list → should fetch from https://api.joyofpm.com/api/documents/list

## Files That Need Changes

1. ✅ **backend/frontend/static/js/app.js** - Add API_BASE_URL and fix all fetch calls
2. ⚠️ **backend/frontend/templates/base.html** - Optionally inject API_BASE_URL
3. ⚠️ **backend/app/routes/htmx.py** - Consider adding `/v1/` prefix for consistency
4. ✅ **app/index.html** & **app/document.html** - Already have API_BASE_URL but may not be used

## Next Steps

1. **Immediate**: Fix `backend/frontend/static/js/app.js` (blocks all API calls)
2. **Test**: Verify all API endpoints are reachable from frontend
3. **Deploy**: Push changes and test on production (app.joyofpm.com)
4. **Monitor**: Check browser console and network tab for errors
5. **Long-term**: Consolidate to single frontend directory

## Risk Assessment

- **Severity**: CRITICAL - Application completely non-functional for users
- **Complexity**: LOW - Simple configuration fixes
- **Risk of Fix**: LOW - Changes are isolated to JavaScript configuration
- **Testing Required**: HIGH - Must test all user flows end-to-end

## References

- Backend API docs: https://api.joyofpm.com/docs (if enabled)
- Frontend code: `/backend/frontend/` and `/frontend/`
- Configuration: `/.env` and `/backend/app/config.py`
