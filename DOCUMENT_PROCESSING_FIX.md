# Document Processing Fix - Root Cause Analysis & Resolution

**Date**: 2025-11-10
**Status**: ✅ FIXED - Ready for Deployment
**Severity**: CRITICAL - Documents not processing

## Problem Statement

When users clicked "Process Document" at app.joyofpm.com, they received the message:
> "Document processing started! This may take a few minutes. The page will refresh when complete."

However, processing never completed and no extracted text or analysis was displayed.

## Root Cause Analysis

After comprehensive log analysis, I identified **TWO critical issues**:

### Issue #1: Office Format Support Not Deployed ⚠️

**Error from logs**:
```
DocumentProcessingError: 422: {
  'error': {
    'code': 'DOCUMENT_PROCESSING_ERROR',
    'message': 'Unsupported file type',
    'details': {'filename': 'test.docx', 'extension': '.docx'}
  }
}
```

**Root Cause**:
- Office format support (`.docx`, `.xlsx`, `.pptx`, etc.) was added in commit `72a771d`
- But the new code hasn't been deployed yet - old code is still running
- Old code doesn't support Office formats, causing all Office documents to fail

**Impact**:
- `.docx`, `.doc`, `.xlsx`, `.xls`, `.pptx`, `.ppt` files fail with "Unsupported file type"
- Only `.pdf`, `.txt`, `.md`, and image files work

### Issue #2: Database Schema Mismatch ❌

**Error from logs**:
```
sqlalchemy.exc.CompileError: Unconsumed column names: processing_checkpoint, processing_state, error_message
```

**Root Cause**:
- `DocumentProcessor` tries to update columns that don't exist in the `documents` table:
  - `processing_checkpoint` (JSONB) - for checkpoint tracking
  - `processing_state` (JSONB) - for state tracking
  - `error_message` (TEXT) - for error messages
  - `risks` (JSONB) - for risk extraction
  - `processing_metadata` (JSONB) - for extraction metadata

**Impact**:
- Database update fails when saving processing checkpoints
- Processing appears to start but crashes silently
- Document status stuck at "processing" forever
- No error messages shown to user

## Fixes Applied

### Fix #1: Admin Endpoint for Database Migration

**File**: `backend/app/routes/admin.py`

**Added**:
- `/api/v1/admin/migrate-processing-columns` endpoint
- Adds all missing columns to `documents` table
- Creates indexes for efficient querying
- Safe to run multiple times (uses `IF NOT EXISTS`)

**Columns Added**:
```sql
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_checkpoint JSONB DEFAULT NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_state JSONB DEFAULT NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS error_message TEXT DEFAULT NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS risks JSONB DEFAULT '[]'::jsonb;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_metadata JSONB DEFAULT '{}'::jsonb;
```

**Indexes Created**:
```sql
CREATE INDEX IF NOT EXISTS idx_documents_processing_checkpoint ON documents USING gin (processing_checkpoint);
CREATE INDEX IF NOT EXISTS idx_documents_processing_state ON documents USING gin (processing_state);
CREATE INDEX IF NOT EXISTS idx_documents_error_message ON documents (error_message);
CREATE INDEX IF NOT EXISTS idx_documents_risks ON documents USING gin (risks);
```

### Fix #2: Office Format Support (Already Committed)

**Status**: Code ready, awaiting deployment

**From commit**: `72a771d`

**Includes**:
- New `OfficeExtractor` service (`backend/app/services/office_extractor.py`)
- Support for modern formats: `.docx`, `.xlsx`, `.pptx`
- Support for legacy formats: `.doc`, `.xls`, `.ppt`
- Integration with `DocumentProcessor`
- Updated route validation

## Deployment Steps

### Step 1: Wait for Current Deployment

Check if the Office format support deployment has completed:

```bash
aws ecs describe-services \
  --cluster pm-doc-intel-cluster-production \
  --services pm-doc-intel-backend-service-production \
  --query 'services[0].deployments'
```

### Step 2: Deploy Latest Changes

Push this commit to trigger GitHub Actions deployment:

```bash
git add backend/app/routes/admin.py \
  backend/migrations/add_processing_columns.sql \
  backend/app/migrations/add_processing_columns.py \
  run_migration.sh \
  quick_migration.py \
  DOCUMENT_PROCESSING_FIX.md

git commit -m "fix: add database migration for processing columns"
git push origin master
```

### Step 3: Run Database Migration

After deployment completes (~10-15 minutes), run the migration:

```bash
curl -X POST https://api.joyofpm.com/api/v1/admin/migrate-processing-columns \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "success": true,
  "message": "Migration completed successfully",
  "columns_added": [
    "processing_checkpoint",
    "processing_state",
    "error_message",
    "risks",
    "processing_metadata"
  ],
  "indexes_created": 4
}
```

### Step 4: Verify Processing Works

1. Go to https://app.joyofpm.com
2. Login
3. Upload a document (PDF, DOCX, TXT, etc.)
4. Click "Process Document"
5. Wait for processing to complete (~30-60 seconds)
6. Verify extracted text and analysis appear

## Testing Checklist

After deployment:

- [ ] Database migration completed successfully
- [ ] `.pdf` files process correctly
- [ ] `.docx` files process correctly (NEW)
- [ ] `.txt` files process correctly
- [ ] `.xlsx` files process correctly (NEW)
- [ ] `.pptx` files process correctly (NEW)
- [ ] Extracted text appears in document view
- [ ] Summary is generated
- [ ] Action items are extracted
- [ ] Risks are identified
- [ ] No errors in CloudWatch logs
- [ ] Processing completes within 60 seconds for small files

## Files Modified

### New Files:
1. `backend/migrations/add_processing_columns.sql` - SQL migration script
2. `backend/app/migrations/add_processing_columns.py` - Python migration script
3. `run_migration.sh` - Shell script for ECS task execution
4. `quick_migration.py` - Quick Python migration script
5. `DOCUMENT_PROCESSING_FIX.md` - This document

### Modified Files:
1. `backend/app/routes/admin.py` - Added migration endpoint

## Rollback Plan

If issues persist:

### Rollback Database Migration:

```sql
ALTER TABLE documents DROP COLUMN IF EXISTS processing_checkpoint;
ALTER TABLE documents DROP COLUMN IF EXISTS processing_state;
ALTER TABLE documents DROP COLUMN IF EXISTS error_message;
ALTER TABLE documents DROP COLUMN IF EXISTS risks;
ALTER TABLE documents DROP COLUMN IF EXISTS processing_metadata;
```

### Rollback Code:

```bash
# Revert to previous ECS task definition
aws ecs update-service \
  --cluster pm-doc-intel-cluster-production \
  --service pm-doc-intel-backend-service-production \
  --task-definition <previous-task-definition-arn>
```

## Monitoring

### Key Metrics to Watch:

1. **CloudWatch Logs**: `/ecs/pm-doc-intel/production`
   - Look for: "Document processed successfully"
   - Avoid: "CompileError", "Unsupported file type"

2. **Processing Success Rate**:
   - Should be > 95% for supported file types

3. **Processing Duration**:
   - Small files (<1MB): 30-60 seconds
   - Medium files (1-10MB): 60-180 seconds
   - Large files (10-50MB): 3-10 minutes

### Logs to Check:

```bash
# Real-time logs
aws logs tail /ecs/pm-doc-intel/production --follow

# Filter for processing logs
aws logs tail /ecs/pm-doc-intel/production --since 1h | grep "process"

# Filter for errors
aws logs tail /ecs/pm-doc-intel/production --since 1h | grep -i "error"
```

## Expected Behavior After Fix

### For PDF Files:
1. User uploads PDF
2. Clicks "Process Document"
3. Status updates to "processing"
4. Text extracted via AWS Textract (30-60 seconds)
5. AI analysis via Bedrock (20-40 seconds)
6. Status updates to "completed"
7. Extracted text, summary, action items, and risks appear
8. ✅ WORKING

### For Office Files (NEW):
1. User uploads .docx, .xlsx, or .pptx
2. Clicks "Process Document"
3. Status updates to "processing"
4. Text extracted via python-docx/openpyxl/python-pptx (5-10 seconds)
5. AI analysis via Bedrock (20-40 seconds)
6. Status updates to "completed"
7. Extracted text, summary, action items, and risks appear
8. ✅ SHOULD WORK after deployment

### For Text Files:
1. User uploads .txt or .md
2. Clicks "Process Document"
3. Status updates to "processing"
4. Text extracted directly (1-2 seconds)
5. AI analysis via Bedrock (20-40 seconds)
6. Status updates to "completed"
7. Summary, action items, and risks appear
8. ✅ WORKING

## Known Limitations

### Current Limitations:
- Max file size: 100MB
- Max concurrent processing: 5 documents
- Processing timeout: 600 seconds (10 minutes)
- Office formats: Modern formats preferred over legacy

### Legacy Office Format Notes:
- `.doc`, `.xls`, `.ppt` use OLE parsing
- Formatting may be lost
- Encoding detection is best-effort
- Confidence scores lower (60-70% vs 100%)
- Recommend users convert to modern formats

## Success Criteria

✅ **Fix is successful when**:
1. Database migration runs without errors
2. All supported file types process successfully
3. Extracted text appears in UI
4. AI analysis completes (summary, actions, risks)
5. No "Unsupported file type" errors for Office files
6. No "Unconsumed column names" errors in logs
7. Processing completes within expected timeframes
8. User sees results without page refresh issues

## Support & Troubleshooting

### If Processing Still Fails:

1. **Check deployment status**:
   ```bash
   aws ecs describe-services --cluster pm-doc-intel-cluster-production --services pm-doc-intel-backend-service-production
   ```

2. **Verify migration ran**:
   ```bash
   curl https://api.joyofpm.com/api/v1/admin/migrate-processing-columns -X POST
   ```

3. **Check database columns**:
   ```sql
   SELECT column_name, data_type
   FROM information_schema.columns
   WHERE table_name = 'documents'
   AND column_name IN ('processing_checkpoint', 'processing_state', 'error_message', 'risks', 'processing_metadata');
   ```

4. **Review logs**:
   ```bash
   aws logs tail /ecs/pm-doc-intel/production --since 30m | grep -i "error\|process"
   ```

### Contact

- **Logs**: CloudWatch Logs `/ecs/pm-doc-intel/production`
- **Monitoring**: ECS Service Health Dashboard
- **Database**: Supabase Dashboard

---

## Timeline

- **2025-11-10 03:06**: User reported processing not working
- **2025-11-10 03:30**: Root cause identified (2 issues)
- **2025-11-10 03:45**: Fix #1 created (admin migration endpoint)
- **2025-11-10 04:00**: Fix #2 verified (Office support already in code)
- **2025-11-10 04:15**: Documentation completed
- **2025-11-10 04:30**: Ready for deployment

## Conclusion

Both root causes have been identified and fixed:

1. ✅ **Database schema mismatch** - Fixed via admin endpoint
2. ✅ **Office format support** - Already in code, awaiting deployment

After deploying this commit and running the migration endpoint, document processing should work correctly for all supported file types.

---

**Next Action**: Deploy this commit and run the migration endpoint.
