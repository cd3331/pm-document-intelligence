# Demo Troubleshooting Guide

Comprehensive troubleshooting guide for PM Document Intelligence demos. Use this guide to prevent, identify, and quickly fix common demo issues.

---

## Table of Contents

1. [Pre-Demo Checklist](#pre-demo-checklist)
2. [Common Issues & Solutions](#common-issues--solutions)
3. [Backup Plans](#backup-plans)
4. [Quick Fixes](#quick-fixes)
5. [Recovery Procedures](#recovery-procedures)
6. [Demo Environment Setup](#demo-environment-setup)
7. [Network & Connectivity Issues](#network--connectivity-issues)
8. [Browser & Display Issues](#browser--display-issues)
9. [Emergency Contacts](#emergency-contacts)

---

## Pre-Demo Checklist

### 24 Hours Before Demo

- [ ] **Test demo environment**: Upload and process a test document
- [ ] **Verify all services are running**:
  ```bash
  docker-compose ps
  # All services should be "Up"
  ```
- [ ] **Check database connectivity**:
  ```bash
  psql $DATABASE_URL -c "SELECT COUNT(*) FROM documents;"
  ```
- [ ] **Verify S3 access**:
  ```bash
  aws s3 ls s3://pm-doc-intel-demo/
  ```
- [ ] **Test AI APIs**:
  ```bash
  curl https://api.openai.com/v1/models \
    -H "Authorization: Bearer $OPENAI_API_KEY"
  ```
- [ ] **Verify PubNub connection**:
  ```bash
  curl "https://ps.pndsn.com/v2/subscribe/$PUBNUB_SUBSCRIBE_KEY/test_channel/0"
  ```
- [ ] **Check SSL certificates** (if using HTTPS):
  ```bash
  openssl s_client -connect demo.pmdocintel.com:443 -servername demo.pmdocintel.com
  ```
- [ ] **Test demo account login**:
  - Email: demo@pmdocintel.com
  - Password: demo2024
- [ ] **Verify sample documents are loaded**:
  ```bash
  ls -lh demo_data/
  # Should see 7 PDF/DOCX files
  ```
- [ ] **Test all demo scenarios**:
  - 5-minute quick demo
  - 15-minute feature demo
  - 30-minute deep dive
- [ ] **Prepare backup laptop** (if presenting in-person)
- [ ] **Download offline version** (if internet might be unreliable)
- [ ] **Charge all devices** (laptop, backup laptop, phone)

### 1 Hour Before Demo

- [ ] **Close all unnecessary applications**
- [ ] **Clear browser cache and cookies**
- [ ] **Disable browser extensions** (except essential ones)
- [ ] **Set browser zoom to 100%**
- [ ] **Hide bookmarks bar** (Cmd+Shift+B / Ctrl+Shift+B)
- [ ] **Close all tabs except demo**
- [ ] **Turn off notifications**:
  - macOS: System Preferences → Notifications → Do Not Disturb
  - Windows: Settings → System → Notifications → Turn off
- [ ] **Set display resolution** (1920x1080 recommended for sharing)
- [ ] **Test screen sharing** (if virtual demo)
- [ ] **Test audio** (if presenting with voice)
- [ ] **Open demo in incognito/private window** (fresh session)
- [ ] **Have GitHub repo open in another tab** (for code walkthrough)
- [ ] **Have architecture diagram ready** (separate tab)
- [ ] **Prepare terminal with useful commands** (pre-typed, don't execute yet)
- [ ] **Test demo flow one more time** (quick run-through)

### 5 Minutes Before Demo

- [ ] **Final service health check**:
  ```bash
  curl http://localhost:8000/health
  # Should return {"status": "healthy"}
  ```
- [ ] **Login to demo account**
- [ ] **Clear demo database** (if starting fresh):
  ```bash
  python scripts/reset_demo_environment.py
  ```
- [ ] **Upload sample document** (to have one ready)
- [ ] **Close all other windows**
- [ ] **Silence phone**
- [ ] **Have water nearby**
- [ ] **Take deep breath** 😊

---

## Common Issues & Solutions

### Issue 1: Document Upload Fails

**Symptoms:**
- "Upload failed" error message
- Upload progress bar stuck at 0%
- File not appearing in document list

**Possible Causes:**
1. File too large (>50MB limit)
2. Invalid file type (not PDF/DOCX/TXT)
3. S3 connectivity issue
4. Database connection issue
5. Insufficient permissions

**Quick Fixes:**

```bash
# 1. Check file size
ls -lh document.pdf
# If > 50MB, use smaller demo document

# 2. Verify file type
file document.pdf
# Should show: "PDF document, version X.X"

# 3. Test S3 access
aws s3 ls s3://pm-doc-intel-demo/

# 4. Check database connection
psql $DATABASE_URL -c "SELECT 1;"

# 5. Check logs
docker-compose logs -f backend | grep -i error
```

**Workaround:**
- Use pre-uploaded document from demo_data/
- Switch to backup sample document (smaller file)
- Use local file storage (if S3 is down)

**Time to Fix:** 30 seconds - 2 minutes

---

### Issue 2: Processing Stuck

**Symptoms:**
- Document stuck in "processing" status
- No progress updates
- Processing time > 2 minutes

**Possible Causes:**
1. Celery worker not running
2. AI API timeout
3. Redis connection lost
4. PubNub not publishing updates

**Quick Fixes:**

```bash
# 1. Check Celery worker
docker-compose logs celery-worker | tail -n 20
# Should see "Task document_processing.process_document succeeded"

# 2. Restart Celery worker
docker-compose restart celery-worker

# 3. Check Redis
redis-cli ping
# Should return: PONG

# 4. Check OpenAI API status
curl https://status.openai.com/api/v2/status.json

# 5. Manually trigger processing
python scripts/retry_processing.py --document-id=<uuid>
```

**Workaround:**
- Refresh page to see if processing completed
- Use pre-processed document with results
- Show cached results from previous demo

**Time to Fix:** 1-3 minutes

---

### Issue 3: Real-Time Updates Not Working

**Symptoms:**
- Progress bar not updating
- No "processing" → "completed" status change
- Have to manually refresh page

**Possible Causes:**
1. PubNub connection issue
2. JavaScript error
3. Ad blocker interfering
4. Incorrect channel subscription

**Quick Fixes:**

```bash
# 1. Check browser console (F12)
# Look for errors related to PubNub

# 2. Verify PubNub credentials
echo $PUBNUB_SUBSCRIBE_KEY
# Should not be empty

# 3. Test PubNub connection
curl "https://ps.pndsn.com/v2/subscribe/$PUBNUB_SUBSCRIBE_KEY/test_channel/0"

# 4. Check firewall/network
# PubNub uses ports 80 and 443
```

**Workaround:**
- Enable page auto-refresh (every 5 seconds)
- Manually refresh to show updated status
- Mention: "In production, you'd see real-time updates here"
- Show pre-recorded video of real-time updates

**Time to Fix:** 30 seconds - 1 minute

---

### Issue 4: Search Returns No Results

**Symptoms:**
- Search query returns empty results
- "No documents found" message
- Known documents not appearing

**Possible Causes:**
1. Vector embeddings not generated
2. pgvector extension not installed
3. Search index not built
4. Organization filter too restrictive
5. Similarity threshold too high

**Quick Fixes:**

```bash
# 1. Check if embeddings exist
psql $DATABASE_URL -c "SELECT COUNT(*) FROM vector_embeddings;"
# Should return > 0

# 2. Verify pgvector extension
psql $DATABASE_URL -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# 3. Rebuild embeddings for demo documents
python scripts/rebuild_embeddings.py --organization-id=<demo-org-id>

# 4. Lower similarity threshold temporarily
# In code: similarity_threshold = 0.5 (instead of 0.7)
```

**Workaround:**
- Use keyword search instead (exact match)
- Show pre-recorded search demo
- Use different search query that you've tested
- Explain: "Let me show you the architecture instead"

**Time to Fix:** 2-5 minutes

---

### Issue 5: Slow Performance / Timeout

**Symptoms:**
- Pages loading slowly (>5 seconds)
- API timeout errors
- "Gateway timeout" messages

**Possible Causes:**
1. Database connection pool exhausted
2. Too many concurrent requests
3. Cold start (services just started)
4. Network congestion
5. Demo running on underpowered machine

**Quick Fixes:**

```bash
# 1. Check database connections
psql $DATABASE_URL -c "SELECT COUNT(*) FROM pg_stat_activity;"
# Should be < 100

# 2. Restart services (cold start)
docker-compose restart backend

# 3. Clear Redis cache
redis-cli FLUSHALL

# 4. Check system resources
docker stats
# CPU should be < 80%, Memory < 90%

# 5. Reduce workers if needed
# Edit docker-compose.yml: --workers=2 (instead of 4)
```

**Workaround:**
- Wait 30 seconds for cold start to complete
- Use smaller dataset for demo
- Switch to backup environment
- Show screenshots instead of live demo

**Time to Fix:** 1-2 minutes

---

### Issue 6: Authentication Fails

**Symptoms:**
- Cannot log in with demo credentials
- "Invalid username or password" error
- JWT token expired

**Possible Causes:**
1. Demo account not created
2. Wrong credentials
3. Database reset (deleted users)
4. Token expiration issue

**Quick Fixes:**

```bash
# 1. Verify demo account exists
psql $DATABASE_URL -c "SELECT email FROM users WHERE email = 'demo@pmdocintel.com';"

# 2. Reset demo password
python scripts/reset_demo_password.py

# 3. Create demo account (if missing)
python scripts/create_demo_account.py

# 4. Check JWT secret
echo $JWT_SECRET_KEY
# Should not be empty
```

**Workaround:**
- Use your personal account
- Create new demo account on the spot
- Show screenshots of logged-in state
- Skip authentication, start at dashboard

**Time to Fix:** 30 seconds - 1 minute

---

### Issue 7: AI Analysis Quality Issues

**Symptoms:**
- Inaccurate summaries
- Missing action items
- Incorrect risk identification

**Possible Causes:**
1. Wrong AI model selected
2. Prompt engineering issue
3. Document format not supported well
4. API rate limiting (falling back to weaker model)

**Quick Fixes:**

```bash
# 1. Check which model was used
docker-compose logs backend | grep -i "model_selection"

# 2. Verify API quotas
curl https://api.openai.com/v1/usage \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# 3. Force specific model
# In code: force_model = "gpt-4" (for demo)

# 4. Re-process document
python scripts/reprocess_document.py --document-id=<uuid> --force-model=gpt-4
```

**Workaround:**
- Acknowledge: "This is an edge case, typical accuracy is 91%"
- Use pre-processed document with good results
- Show different document
- Explain AI limitations honestly

**Time to Fix:** 1-3 minutes

---

## Backup Plans

### Backup Plan A: Pre-Recorded Demo

**When to Use:**
- Technical issues cannot be resolved quickly
- Internet connection lost
- Critical service down

**How to Execute:**
1. Open pre-recorded demo video
2. Say: "Let me show you a recording while we troubleshoot"
3. Play video with narration
4. Answer questions during/after video
5. Offer to send GitHub link for code review

**Preparation:**
- Record 5-min, 15-min, 30-min demo videos
- Store locally (not streaming)
- Include voiceover narration
- Update regularly with latest features

---

### Backup Plan B: Screenshot Walkthrough

**When to Use:**
- Demo environment down
- Cannot screen share
- Network too slow for live demo

**How to Execute:**
1. Open slide deck with screenshots
2. Walk through each feature with images
3. Explain architecture with diagrams
4. Offer to schedule follow-up live demo

**Preparation:**
- Create slide deck with high-quality screenshots
- Include all key features
- Add architecture diagrams
- Export as PDF (offline access)

---

### Backup Plan C: Code Walkthrough

**When to Use:**
- Frontend issues but backend working
- Audience is technical and prefers code
- Want to show technical depth

**How to Execute:**
1. Open GitHub repository
2. Walk through key files:
   - `backend/app/services/ai_service.py` (multi-model routing)
   - `backend/app/services/search_service.py` (vector search)
   - `backend/app/tasks/document_processing.py` (async processing)
3. Explain architecture decisions
4. Show test coverage
5. Discuss deployment pipeline

**Preparation:**
- Know which files to show
- Highlight key code sections
- Prepare talking points for each file

---

### Backup Plan D: Architecture Discussion

**When to Use:**
- Complete system failure
- Very technical audience
- Want to pivot to system design

**How to Execute:**
1. Open architecture diagram
2. Discuss each layer:
   - Frontend (htmx + Tailwind)
   - API (FastAPI)
   - Processing (Celery)
   - AI (Multi-model)
   - Data (PostgreSQL + pgvector)
   - Cache (Redis)
   - Storage (S3)
3. Explain design decisions (ADRs)
4. Discuss trade-offs and alternatives
5. Show performance metrics

**Preparation:**
- Have architecture diagrams ready
- Know ADRs by heart
- Prepare metrics/benchmarks
- Ready to whiteboard if needed

---

## Quick Fixes

### Quick Fix 1: Restart All Services (30 seconds)

```bash
# Full restart
docker-compose down
docker-compose up -d

# Check health
curl http://localhost:8000/health
```

### Quick Fix 2: Clear Cache (10 seconds)

```bash
# Clear Redis cache
redis-cli FLUSHALL

# Or via Docker
docker-compose exec redis redis-cli FLUSHALL
```

### Quick Fix 3: Reset Demo Database (1 minute)

```bash
# Reset to clean state with sample data
python scripts/reset_demo_environment.py

# Or manually
psql $DATABASE_URL -f scripts/demo_data.sql
```

### Quick Fix 4: Switch to Backup Document (5 seconds)

```bash
# Use known-good document
cp demo_data/project_status_report.pdf /tmp/demo_upload.pdf

# Upload via API
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/demo_upload.pdf"
```

### Quick Fix 5: Bypass AI Processing (Show Cached Results)

```bash
# Use pre-processed results
python scripts/load_cached_results.py --document-id=<uuid>
```

### Quick Fix 6: Emergency Rollback

```bash
# Rollback to previous working version
git checkout demo-stable
docker-compose down
docker-compose up -d
```

---

## Recovery Procedures

### Recovery 1: Database Corruption

**Symptoms:**
- SQL errors
- Foreign key violations
- Data inconsistency

**Recovery Steps:**

```bash
# 1. Stop all services
docker-compose down

# 2. Backup current database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# 3. Restore from known-good backup
psql $DATABASE_URL < backups/demo_environment_good.sql

# 4. Run migrations
alembic upgrade head

# 5. Rebuild indexes
psql $DATABASE_URL -c "REINDEX DATABASE pm_doc_intel_demo;"

# 6. Restart services
docker-compose up -d
```

**Time to Recover:** 3-5 minutes

---

### Recovery 2: S3 Access Lost

**Symptoms:**
- Cannot upload documents
- Cannot download documents
- "Access Denied" errors

**Recovery Steps:**

```bash
# 1. Verify AWS credentials
aws sts get-caller-identity

# 2. Test S3 access
aws s3 ls s3://pm-doc-intel-demo/

# 3. Switch to local file storage (temporary)
# Edit docker-compose.yml:
#   environment:
#     - STORAGE_BACKEND=local
#     - LOCAL_STORAGE_PATH=/app/uploads

# 4. Restart backend
docker-compose restart backend

# 5. Upload test document to verify
```

**Time to Recover:** 1-2 minutes

---

### Recovery 3: AI API Rate Limited

**Symptoms:**
- 429 errors from OpenAI/Claude
- Processing fails consistently
- "Rate limit exceeded" messages

**Recovery Steps:**

```bash
# 1. Check API usage
curl https://api.openai.com/v1/usage \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# 2. Switch to backup API key
export OPENAI_API_KEY=$OPENAI_BACKUP_KEY

# 3. Reduce request rate
# Edit config: MAX_CONCURRENT_AI_REQUESTS = 2 (instead of 5)

# 4. Enable request queuing
# Edit config: ENABLE_AI_REQUEST_QUEUE = true

# 5. Restart processing
docker-compose restart celery-worker
```

**Time to Recover:** 2-3 minutes

---

### Recovery 4: Complete System Failure

**Symptoms:**
- Nothing works
- All services down
- Panic mode 😱

**Recovery Steps:**

```bash
# 1. Stay calm 🧘
# Take deep breath

# 2. Switch to Backup Plan A (video)
# Open pre-recorded demo

# 3. In parallel, diagnose issue
docker-compose logs --tail=50

# 4. If time allows, restart everything
docker-compose down --volumes
docker-compose up -d

# 5. If still failing, proceed with video/screenshots
# Offer to schedule follow-up demo
```

**Time to Recover:** Switch to backup immediately (0 seconds)

---

## Demo Environment Setup

### Local Development Setup

```bash
# Clone repository
git clone https://github.com/cd3331/pm-document-intelligence.git
cd pm-document-intelligence

# Set up environment variables
cp .env.example .env.demo
# Edit .env.demo with demo credentials

# Start services
docker-compose -f docker-compose.demo.yml up -d

# Initialize database
docker-compose exec backend alembic upgrade head

# Load demo data
docker-compose exec backend python scripts/load_demo_data.py

# Create demo account
docker-compose exec backend python scripts/create_demo_account.py \
  --email demo@pmdocintel.com \
  --password demo2024 \
  --role admin

# Verify setup
curl http://localhost:8000/health
# Should return: {"status": "healthy"}

# Login test
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@pmdocintel.com", "password": "demo2024"}'
# Should return JWT token
```

### Cloud Demo Environment (AWS)

```bash
# Deploy to demo environment
cd terraform/environments/demo
terraform init
terraform apply -var-file=demo.tfvars

# Get demo URL
terraform output demo_url
# Example: https://demo.pmdocintel.com

# Verify deployment
curl https://demo.pmdocintel.com/health

# Load demo data
ssh ec2-user@demo.pmdocintel.com \
  'cd /app && python scripts/load_demo_data.py'
```

---

## Network & Connectivity Issues

### Issue: Slow Internet Connection

**Symptoms:**
- Pages loading slowly
- Video streaming buffering
- Screen share laggy

**Solutions:**

1. **Reduce quality settings:**
   - Zoom/Teams: Lower video quality to 360p
   - Turn off HD video
   - Disable virtual backgrounds

2. **Close bandwidth-heavy apps:**
   - Stop file syncing (Dropbox, Google Drive)
   - Close Spotify/YouTube
   - Pause software updates

3. **Use wired connection:**
   - Ethernet instead of WiFi
   - Mobile hotspot as backup

4. **Switch to backup plan:**
   - Pre-recorded video (local file)
   - Screenshot walkthrough
   - Code walkthrough (less bandwidth)

---

### Issue: Firewall Blocking Ports

**Symptoms:**
- Cannot connect to database
- Redis connection refused
- API requests timing out

**Solutions:**

```bash
# Check firewall rules
sudo iptables -L
# or
sudo ufw status

# Allow necessary ports
sudo ufw allow 8000  # Backend API
sudo ufw allow 5432  # PostgreSQL
sudo ufw allow 6379  # Redis

# Test port connectivity
nc -zv localhost 8000
nc -zv localhost 5432
nc -zv localhost 6379
```

---

## Browser & Display Issues

### Issue: Display Resolution Too High/Low

**Symptoms:**
- Text too small to read
- UI elements cut off
- Aspect ratio wrong

**Solutions:**

1. **Set recommended resolution:**
   - 1920x1080 (Full HD) for most presentations
   - 1280x720 if bandwidth limited
   - Test before demo

2. **Adjust browser zoom:**
   - Zoom in: Cmd/Ctrl + Plus
   - Zoom out: Cmd/Ctrl + Minus
   - Reset: Cmd/Ctrl + 0

3. **Use browser dev tools device simulation:**
   - F12 → Device toolbar
   - Select appropriate device size

---

### Issue: Browser Extensions Interfering

**Symptoms:**
- Unexpected popups
- Ad blocker hiding elements
- Script errors

**Solutions:**

1. **Disable all extensions:**
   ```
   Chrome: chrome://extensions → Disable all
   Firefox: about:addons → Disable all
   ```

2. **Use incognito/private mode:**
   - Automatically disables most extensions
   - Fresh session each time

3. **Create demo browser profile:**
   - Separate profile just for demos
   - No extensions installed
   - Clean history/cache

---

## Emergency Contacts

### Internal Team

**Lead Developer:** Your Name
- Email: your@email.com
- Phone: +1-XXX-XXX-XXXX
- Slack: @yourname

**DevOps:** DevOps Name
- Email: devops@company.com
- Phone: +1-XXX-XXX-XXXX
- On-call: Use PagerDuty

### External Services

**AWS Support:**
- Portal: https://console.aws.amazon.com/support
- Phone: 1-866-626-0777 (US)

**OpenAI Support:**
- Email: support@openai.com
- Status: https://status.openai.com

**Anthropic Support:**
- Email: support@anthropic.com

**PubNub Support:**
- Email: support@pubnub.com
- Status: https://status.pubnub.com

---

## Post-Demo Checklist

**After Demo:**

- [ ] **Reset demo environment** (for next demo)
  ```bash
  python scripts/reset_demo_environment.py
  ```
- [ ] **Clear demo data** (if sensitive)
- [ ] **Review logs** for any errors
- [ ] **Note any issues** encountered
- [ ] **Update troubleshooting guide** with new learnings
- [ ] **Send follow-up email** with links
- [ ] **Backup database** if good demo data
- [ ] **Update demo video** if features changed
- [ ] **Thank attendees**

---

## Demo Troubleshooting Scripts

### Script 1: Health Check Script

```bash
#!/bin/bash
# scripts/demo_health_check.sh

echo "=== PM Document Intelligence Demo Health Check ==="
echo

# Check services
echo "1. Checking Docker containers..."
docker-compose ps

# Check database
echo -e "\n2. Checking database connection..."
psql $DATABASE_URL -c "SELECT 'Database OK' as status;" 2>&1 | grep -q "Database OK" && echo "✅ Database OK" || echo "❌ Database FAILED"

# Check Redis
echo -e "\n3. Checking Redis..."
redis-cli ping | grep -q "PONG" && echo "✅ Redis OK" || echo "❌ Redis FAILED"

# Check S3
echo -e "\n4. Checking S3 access..."
aws s3 ls s3://pm-doc-intel-demo/ >/dev/null 2>&1 && echo "✅ S3 OK" || echo "❌ S3 FAILED"

# Check API health endpoint
echo -e "\n5. Checking API health..."
curl -s http://localhost:8000/health | grep -q "healthy" && echo "✅ API OK" || echo "❌ API FAILED"

# Check OpenAI API
echo -e "\n6. Checking OpenAI API..."
curl -s https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | grep -q "gpt-4" && echo "✅ OpenAI OK" || echo "❌ OpenAI FAILED"

# Check demo account
echo -e "\n7. Checking demo account..."
psql $DATABASE_URL -c "SELECT email FROM users WHERE email = 'demo@pmdocintel.com';" 2>&1 | grep -q "demo@pmdocintel.com" && echo "✅ Demo account OK" || echo "❌ Demo account FAILED"

echo -e "\n=== Health Check Complete ==="
```

### Script 2: Quick Reset Script

```bash
#!/bin/bash
# scripts/quick_reset.sh

echo "Resetting demo environment..."

# Clear Redis cache
echo "Clearing cache..."
redis-cli FLUSHALL

# Reset demo documents
echo "Resetting documents..."
psql $DATABASE_URL -c "DELETE FROM documents WHERE organization_id = (SELECT id FROM organizations WHERE name = 'Demo Organization');"

# Reload sample data
echo "Loading sample data..."
python scripts/load_demo_data.py

# Restart services
echo "Restarting services..."
docker-compose restart backend celery-worker

echo "✅ Demo environment reset complete!"
```

---

## Tips for Smooth Demos

### General Tips

1. **Practice, practice, practice**
   - Do full run-through 3+ times
   - Time yourself
   - Practice talking points

2. **Know your backup plans**
   - Don't panic if something breaks
   - Smoothly transition to backup
   - Have fun with it

3. **Engage the audience**
   - Ask questions
   - Encourage interaction
   - Be enthusiastic

4. **Be honest about limitations**
   - "This is an edge case"
   - "Typical accuracy is 91%"
   - "Here's what we're working on"

5. **Have fun!**
   - You built something awesome
   - Be proud
   - Enjoy showing it off

### Technical Tips

1. **Close all unnecessary apps**
2. **Disable notifications**
3. **Use incognito mode**
4. **Have terminal ready**
5. **Know keyboard shortcuts**
6. **Use dual monitors** (if available)
7. **Test audio/video beforehand**
8. **Have water nearby**

### Communication Tips

1. **Speak clearly and slowly**
2. **Pause for questions**
3. **Use analogies for non-technical audience**
4. **Show enthusiasm**
5. **Make eye contact** (in person) or **look at camera** (virtual)

---

**Last Updated**: 2025-01-20
**Document Version**: 1.0.0

---

**Remember**: The best troubleshooting is prevention. Test everything before the demo, have backups ready, and stay calm if issues arise. You've got this! 🚀
