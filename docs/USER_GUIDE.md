# User Guide

Complete guide to using PM Document Intelligence for project managers, team leads, and document analysts.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Uploading Documents](#uploading-documents)
3. [Understanding Results](#understanding-results)
4. [Searching Documents](#searching-documents)
5. [Managing Action Items](#managing-action-items)
6. [Team Collaboration](#team-collaboration)
7. [Analytics & Insights](#analytics--insights)
8. [Best Practices](#best-practices)
9. [Tips & Tricks](#tips--tricks)
10. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Creating Your Account

1. Navigate to [https://pmdocintel.com](https://pmdocintel.com)
2. Click **Sign Up** in the top right corner
3. Enter your email, password, and organization name
4. Verify your email address
5. Complete your profile setup

**First Time Setup**:
- Set up your organization details
- Invite team members
- Configure default preferences
- Review pricing plans

### Dashboard Overview

```
┌─────────────────────────────────────────────────────┐
│  PM Document Intelligence                     [User]│
├─────────────────────────────────────────────────────┤
│                                                     │
│  Quick Stats                                        │
│  ┌──────────┬──────────┬──────────┬──────────┐    │
│  │ 487 Docs │ 452 Proc │ 8 Active │ $245 Cost│    │
│  └──────────┴──────────┴──────────┴──────────┘    │
│                                                     │
│  Recent Documents                                   │
│  ┌───────────────────────────────────────────┐    │
│  │ ● meeting-notes.pdf      [Completed]      │    │
│  │ ● q1-report.docx         [Processing...]  │    │
│  │ ● project-plan.pdf       [Completed]      │    │
│  └───────────────────────────────────────────┘    │
│                                                     │
│  [Upload Document] [Search] [Analytics]            │
└─────────────────────────────────────────────────────┘
```

**Key Areas**:
- **Documents**: Upload and manage documents
- **Search**: Find information across all documents
- **Analytics**: View usage statistics and insights
- **Settings**: Configure preferences and team access

---

## Uploading Documents

### Supported File Types

| Format | Extension | Max Size | Notes |
|--------|-----------|----------|-------|
| PDF | `.pdf` | 50 MB | Most common format |
| Word | `.docx`, `.doc` | 50 MB | Full text extraction |
| Text | `.txt` | 10 MB | Plain text only |
| Rich Text | `.rtf` | 10 MB | Formatted text |

### Upload Methods

#### Method 1: Drag & Drop (Recommended)

1. Open the **Documents** page
2. Drag your file into the upload area
3. Drop to start uploading
4. Processing begins automatically

**Visual Guide**:
```
┌─────────────────────────────────────┐
│                                     │
│     📄                              │
│                                     │
│  Drag & Drop your document here    │
│           or                        │
│  [Browse Files]                     │
│                                     │
│  Supported: PDF, DOCX, TXT         │
└─────────────────────────────────────┘
```

#### Method 2: Browse & Upload

1. Click **Browse Files** button
2. Select file from your computer
3. Click **Open**
4. Review and confirm upload

#### Method 3: API Upload

For programmatic access, use the API:

```python
import requests

url = 'https://api.pmdocintel.com/api/documents/upload'
headers = {'Authorization': f'Bearer {your_token}'}
files = {'file': open('document.pdf', 'rb')}

response = requests.post(url, headers=headers, files=files)
document = response.json()
print(f"Uploaded: {document['id']}")
```

### Document Types

Selecting the correct document type improves AI accuracy:

| Type | When to Use | Example |
|------|-------------|---------|
| **Meeting Notes** | Team meetings, standups, retrospectives | "Weekly Project Alpha Sync" |
| **Project Plan** | Project charters, roadmaps, timelines | "Q1 2024 Product Roadmap" |
| **Status Report** | Weekly/monthly updates, progress reports | "January Status Update" |
| **Technical Spec** | Architecture docs, technical designs | "API Design Specification" |
| **Requirements Doc** | User stories, feature requirements | "Payment Feature Requirements" |

**How to Set Document Type**:
1. After selecting file, choose type from dropdown
2. Or let AI auto-detect (80% accuracy)
3. You can change it later in document settings

### Adding Metadata

Metadata helps organize and search documents:

```json
{
  "project": "Project Alpha",
  "quarter": "Q1 2024",
  "team": "Engineering",
  "priority": "high",
  "tags": ["budget", "timeline", "risks"]
}
```

**Common Metadata Fields**:
- **Project**: Project name or code
- **Date**: Meeting or report date
- **Attendees**: List of participants
- **Status**: Draft, final, approved
- **Tags**: Custom labels for filtering

---

## Understanding Results

### Processing Timeline

```
Upload → Text Extraction → AI Analysis → Results Ready
  ↓           ↓               ↓            ↓
 0s          5s              30s          45s
```

**Processing Steps**:
1. **Text Extraction** (5-10s): Extract text from PDF/DOCX
2. **Classification** (2-5s): Identify document type
3. **AI Analysis** (20-40s): Generate insights
4. **Quality Check** (3-5s): Validate results

### Summary Results

Three summary lengths are automatically generated:

#### Short Summary (2-3 sentences)
```
Project Alpha team discussed Q1 milestones and identified
3 blockers. Budget increase of $50K approved. Next meeting
scheduled for Jan 22.
```

**Use When**: Quick overview needed, executive briefing

#### Medium Summary (1 paragraph)
```
The Project Alpha team held their weekly sync meeting to
review Q1 milestone progress, currently at 75% completion.
Three critical blockers were identified: API integration
delays, resource constraints, and vendor dependencies. The
team approved a budget increase of $50K to address resource
gaps. Action items were assigned to resolve blockers by
end of month. Next meeting scheduled for January 22 with
stakeholder update.
```

**Use When**: Team updates, weekly reports

#### Detailed Summary (structured)
```
# Project Alpha Weekly Sync

## Overview
Weekly project sync meeting held on January 15, 2024.

## Key Discussion Points
- Q1 milestone progress review (75% complete)
- Critical blocker identification and mitigation
- Budget approval for additional resources
- Stakeholder communication strategy

## Decisions Made
1. Approved $50K budget increase
2. Prioritized API integration completion
3. Scheduled stakeholder update meeting

## Blockers Identified
1. API Integration Delays (High Priority)
   - Vendor dependencies causing 2-week delay
   - Mitigation: Direct escalation to vendor

2. Resource Constraints (High Priority)
   - Need 2 additional engineers for Q1
   - Mitigation: Budget approved for contractors

3. Third-party Dependencies (Medium Priority)
   - External API stability concerns
   - Mitigation: Implement failover strategy

## Next Steps
- Resolve blockers by month end
- Stakeholder update on Jan 22
- Continue weekly syncs
```

**Use When**: Detailed documentation, handoff documents

### Action Items

**Action Item Structure**:
```json
{
  "description": "Complete API documentation",
  "owner": "John Doe",
  "deadline": "2024-01-19",
  "priority": "high",
  "status": "pending",
  "category": "documentation",
  "context": "Mentioned in project sync meeting",
  "confidence": 0.95
}
```

**Priority Levels**:
- 🔴 **High**: Critical, blocking others
- 🟡 **Medium**: Important, not blocking
- 🟢 **Low**: Nice to have, can be deferred

**Example Action Items**:
```
┌────────────────────────────────────────────────────────┐
│ Action Items (8 total)                                 │
├────────────────────────────────────────────────────────┤
│                                                        │
│ 🔴 Complete API documentation                         │
│    Owner: John Doe                                    │
│    Due: Jan 19 (4 days)                               │
│    Category: Documentation                            │
│                                                        │
│ 🔴 Resolve vendor API integration                     │
│    Owner: Jane Smith                                  │
│    Due: Jan 20 (5 days)                               │
│    Category: Development                              │
│                                                        │
│ 🟡 Schedule stakeholder meeting                       │
│    Owner: John Doe                                    │
│    Due: Jan 22 (7 days)                               │
│    Category: Meeting                                  │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### Risk Assessment

**Risk Structure**:
```json
{
  "risk": "API vendor delays impacting Q1 delivery",
  "severity": "high",
  "likelihood": "medium",
  "impact": "Could delay Q1 launch by 2 weeks",
  "mitigation": "Direct escalation to vendor management",
  "owner": "Jane Smith",
  "status": "active"
}
```

**Risk Matrix**:
```
          High    [6] [8] [9]
Likelihood Med    [3] [5] [7]
          Low     [1] [2] [4]

                  Low Med High
                    Impact
```

**Risk Categories**:
- **Schedule**: Timeline delays
- **Budget**: Cost overruns
- **Resource**: Team availability
- **Technical**: Technical challenges
- **External**: Vendor dependencies

---

## Searching Documents

### Basic Search

Simple keyword search across all documents:

```
Search: "budget overrun"

Results:
✓ q1-financial-review.pdf (Score: 0.92)
  "...identified significant budget overruns in Q1..."

✓ project-alpha-meeting.pdf (Score: 0.85)
  "...discussed Q1 budget challenges and overrun..."
```

**Search Tips**:
- Use quotes for exact phrases: `"budget overrun"`
- Use AND/OR for multiple terms: `budget AND Q1`
- Use minus for exclusions: `budget -approved`

### Semantic Search

Natural language queries understand intent:

**Query**: "What risks were identified for Project Alpha?"

**Result**:
```
AI Answer:
Based on the documents, three main risks were identified:

1. Budget overruns of $50K in Q1
   Source: q1-financial-review.pdf

2. Key developer leaving the team in March
   Source: team-updates.pdf

3. Delayed API integration with external vendor
   Source: project-alpha-meeting.pdf

All risks have mitigation plans in place.

Confidence: 89%
```

### Advanced Filters

Narrow results with filters:

```
┌────────────────────────────────────┐
│ Search Filters                     │
├────────────────────────────────────┤
│ Document Type:                     │
│ ☐ Meeting Notes                    │
│ ☑ Status Reports                   │
│ ☐ Technical Specs                  │
│                                    │
│ Date Range:                        │
│ From: [Jan 1, 2024]               │
│ To:   [Jan 31, 2024]              │
│                                    │
│ Project:                           │
│ ☑ Project Alpha                    │
│ ☐ Project Beta                     │
│                                    │
│ [Apply Filters]                    │
└────────────────────────────────────┘
```

### Saved Searches

Save frequent searches for quick access:

1. Perform a search with filters
2. Click **Save Search**
3. Name your search: "Q1 Budget Reports"
4. Access from sidebar under **Saved Searches**

**Common Saved Searches**:
- "This Week's Meeting Notes"
- "High Priority Action Items"
- "Budget-Related Documents"
- "Technical Specifications"

---

## Managing Action Items

### Action Item Dashboard

```
┌─────────────────────────────────────────────────────────┐
│ Action Items Dashboard                                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Overview                                                │
│ ┌──────────────┬──────────────┬──────────────┐        │
│ │ 8 Total      │ 3 Overdue    │ 5 This Week  │        │
│ └──────────────┴──────────────┴──────────────┘        │
│                                                         │
│ By Priority      By Status         By Owner            │
│ High: 3         Pending: 6         John: 4             │
│ Med:  4         In Progress: 2     Jane: 3             │
│ Low:  1         Blocked: 0         Sam: 1              │
│                                                         │
│ ┌─────────────────────────────────────────────┐       │
│ │ 🔴 Complete API documentation               │       │
│ │    John Doe · Due: Jan 19 · OVERDUE         │       │
│ │    [Mark Complete] [Reassign] [Edit]        │       │
│ ├─────────────────────────────────────────────┤       │
│ │ 🔴 Resolve vendor API integration           │       │
│ │    Jane Smith · Due: Jan 20 · In Progress   │       │
│ │    [Mark Complete] [Reassign] [Edit]        │       │
│ └─────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────┘
```

### Tracking Action Items

**Mark as Complete**:
1. Click on action item
2. Click **Mark Complete** button
3. Add optional completion notes
4. Linked document is updated

**Reassign Action Item**:
1. Click **Reassign** button
2. Select new owner from dropdown
3. Add reassignment reason
4. Owner receives notification

**Edit Action Item**:
1. Click **Edit** button
2. Modify description, deadline, or priority
3. Save changes
4. Change log is tracked

### Exporting Action Items

Export to popular formats:

**CSV Export**:
```csv
Description,Owner,Deadline,Priority,Status,Source
Complete API documentation,John Doe,2024-01-19,high,pending,meeting-notes.pdf
Resolve vendor API,Jane Smith,2024-01-20,high,in_progress,project-sync.pdf
```

**JSON Export**:
```json
{
  "action_items": [
    {
      "id": "action_1",
      "description": "Complete API documentation",
      "owner": "John Doe",
      "deadline": "2024-01-19",
      "priority": "high",
      "status": "pending",
      "source_document": "meeting-notes.pdf"
    }
  ]
}
```

**Integration with Tools**:
- **Jira**: Export to Jira issues
- **Asana**: Create Asana tasks
- **Monday.com**: Sync with Monday boards
- **Trello**: Create Trello cards

---

## Team Collaboration

### Inviting Team Members

1. Go to **Settings** → **Team**
2. Click **Invite Member**
3. Enter email address
4. Select role (Admin, Member, Viewer)
5. Add optional welcome message
6. Click **Send Invitation**

**Role Permissions**:

| Permission | Admin | Member | Viewer |
|------------|-------|--------|--------|
| Upload documents | ✅ | ✅ | ❌ |
| View documents | ✅ | ✅ | ✅ |
| Delete documents | ✅ | ✅ | ❌ |
| Manage team | ✅ | ❌ | ❌ |
| View analytics | ✅ | ✅ | ✅ |
| Billing access | ✅ | ❌ | ❌ |

### Sharing Documents

**Share Individual Document**:
1. Open document
2. Click **Share** button
3. Add team member emails
4. Set permissions (view/edit)
5. Click **Share**

**Share via Link**:
1. Click **Get Shareable Link**
2. Set expiration (24h, 7d, 30d, never)
3. Toggle password protection (optional)
4. Copy link
5. Share with stakeholders

```
🔗 Share Link
https://pmdocintel.com/share/abc123xyz?token=...

⚙️ Settings
□ Password protected
Expires: 7 days from now

[Copy Link] [Revoke Access]
```

### Comments & Annotations

Add comments to specific sections:

```
┌────────────────────────────────────────────┐
│ "...budget overruns in Q1 totaling $50K"  │
├────────────────────────────────────────────┤
│ 💬 John Doe (2 hours ago)                 │
│ This needs clarification - is this        │
│ operational or capital budget?            │
│                                            │
│ 💬 Jane Smith (1 hour ago)                │
│ It's capital budget. Details in           │
│ the financial appendix.                   │
│                                            │
│ [Reply] [Resolve]                          │
└────────────────────────────────────────────┘
```

### Real-time Collaboration

See who's viewing documents in real-time:

```
👁️ Viewing now: John Doe, Jane Smith

🟢 John is reading page 3
🟢 Jane is reading page 5
```

---

## Analytics & Insights

### Usage Dashboard

```
┌─────────────────────────────────────────────────────┐
│ Usage Analytics - Last 30 Days                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Documents Processed Over Time                      │
│  ┌───────────────────────────────────────────┐    │
│  │ 20│         ╱╲                            │    │
│  │ 15│     ╱╲╱  ╲  ╱╲                        │    │
│  │ 10│ ╱╲╱      ╲╱  ╲                        │    │
│  │  5│                ╲╱                      │    │
│  │  0└─────────────────────────────────────  │    │
│  └───────────────────────────────────────────┘    │
│                                                     │
│  Top Users                                          │
│  1. John Doe         87 documents                   │
│  2. Jane Smith       62 documents                   │
│  3. Sam Johnson      43 documents                   │
│                                                     │
│  Document Types                                     │
│  Meeting Notes       40%  ████████                  │
│  Status Reports      30%  ██████                    │
│  Technical Specs     20%  ████                      │
│  Other              10%  ██                         │
└─────────────────────────────────────────────────────┘
```

### Cost Analytics

Track AI processing costs:

```
┌─────────────────────────────────────────────────────┐
│ Cost Breakdown - January 2024                       │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Total Cost: $245.67                                │
│  Per Document: $0.54                                │
│                                                     │
│  By Model                                           │
│  GPT-4           $125.30  (51%)  ████████████       │
│  GPT-3.5 Turbo   $65.20   (27%)  ██████             │
│  Claude 2        $55.17   (22%)  █████              │
│                                                     │
│  By Task Type                                       │
│  Summaries       $98.20   (40%)                     │
│  Action Items    $73.65   (30%)                     │
│  Risk Analysis   $49.10   (20%)                     │
│  Q&A             $24.72   (10%)                     │
│                                                     │
│  Estimated Next Month: $280 (↑ 14%)                │
│  Budget: $500                                       │
│  ████████████████░░░░░░░░ 56% of budget used       │
└─────────────────────────────────────────────────────┘
```

### Performance Insights

AI model performance tracking:

```
┌─────────────────────────────────────────────────────┐
│ AI Performance Metrics                              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Overall Accuracy: 92.4%  ✅ Above Target (90%)    │
│  Avg Confidence:   88.7%                            │
│  Avg Latency:      2.45s                            │
│  Success Rate:     98.2%                            │
│                                                     │
│  By Task Type                                       │
│  Summaries         93.5% accuracy                   │
│  Action Items      91.8% accuracy                   │
│  Risk Assessment   90.2% accuracy                   │
│                                                     │
│  Model Drift: None detected ✅                      │
│  Last Check: 2 hours ago                            │
└─────────────────────────────────────────────────────┘
```

---

## Best Practices

### Document Preparation

**Before Uploading**:
1. ✅ Use clear, descriptive filenames
2. ✅ Ensure text is searchable (not scanned images)
3. ✅ Remove sensitive information (PII, passwords)
4. ✅ Use standard fonts and formatting
5. ❌ Avoid password-protected files
6. ❌ Don't include low-quality scans

**Optimal Document Structure**:
```
✅ Good Structure:
   - Clear headings
   - Bullet points for lists
   - Consistent formatting
   - Table of contents

❌ Poor Structure:
   - All one paragraph
   - No headings
   - Mixed formatting
   - Scanned images only
```

### Writing Effective Queries

**Search Best Practices**:

❌ **Poor Query**: "stuff about budget"
✅ **Better Query**: "Q1 budget overruns Project Alpha"
✅ **Best Query**: "What caused the budget overrun in Q1 2024 for Project Alpha?"

**Question Format Tips**:
- Use complete sentences for semantic search
- Be specific about time periods
- Include project names or context
- Ask one question at a time

### Organization Tips

**Folder Structure**:
```
Organization
├── Projects
│   ├── Project Alpha
│   │   ├── Meeting Notes
│   │   ├── Status Reports
│   │   └── Technical Specs
│   └── Project Beta
│       ├── Meeting Notes
│       └── Planning Docs
├── Quarterly Reports
│   ├── Q1 2024
│   └── Q4 2023
└── Team Documents
    ├── Engineering
    └── Product
```

**Tagging Strategy**:
- Use consistent tag names
- Create tag taxonomy
- Limit to 3-5 tags per document
- Use tags for cross-project themes

**Example Tags**:
```
Projects: #project-alpha, #project-beta
Themes: #budget, #timeline, #risks, #staffing
Quarters: #q1-2024, #q2-2024
Status: #draft, #final, #approved
```

### Regular Maintenance

**Weekly Tasks**:
- Review and complete action items
- Update document metadata
- Clean up old/obsolete documents
- Check for processing failures

**Monthly Tasks**:
- Review cost analytics
- Audit team access permissions
- Archive completed project documents
- Update organization settings

**Quarterly Tasks**:
- Export historical data for backup
- Review and optimize document taxonomy
- Train new team members
- Evaluate plan/quota needs

---

## Tips & Tricks

### Power User Shortcuts

**Keyboard Shortcuts**:
```
Ctrl+U        Quick upload
Ctrl+F        Search documents
Ctrl+N        New document
Ctrl+S        Save changes
Esc           Close modal
?             Show help
```

**Quick Actions**:
```
@mention      Notify team member
#tag          Add tag inline
/command      Quick commands
```

### Bulk Operations

**Process Multiple Documents**:
1. Select documents (checkbox)
2. Click **Bulk Actions**
3. Choose action (process, tag, delete)
4. Confirm

**Example**:
```
☑ meeting-notes-jan-1.pdf
☑ meeting-notes-jan-8.pdf
☑ meeting-notes-jan-15.pdf

[Bulk Actions ▾]
  ├─ Process All
  ├─ Add Tags
  ├─ Move to Folder
  └─ Delete
```

### API Integration

**Automate Uploads**:
```python
import os
import requests
from pathlib import Path

def auto_upload_folder(folder_path, api_key):
    """Upload all PDFs in a folder"""
    url = 'https://api.pmdocintel.com/api/documents/upload'
    headers = {'Authorization': f'Bearer {api_key}'}

    for file_path in Path(folder_path).glob('*.pdf'):
        files = {'file': open(file_path, 'rb')}
        data = {'document_type': 'meeting_notes'}

        response = requests.post(url, headers=headers,
                               files=files, data=data)
        print(f"Uploaded: {file_path.name}")

# Usage
auto_upload_folder('/path/to/meeting-notes', 'your_api_key')
```

### Mobile Access

**Mobile Web Features**:
- Upload from mobile camera
- Voice-to-text for search
- Push notifications for processing
- Offline document viewing

**Mobile Tips**:
- Enable notifications for action items
- Use voice search for hands-free
- Download documents for offline access
- Enable biometric authentication

### Integration Tips

**Slack Integration**:
```
/pm-doc search budget overruns
/pm-doc upload @attachment
/pm-doc actions @john
```

**Email Integration**:
```
Forward email to:
documents@pmdocintel.com

Subject: [meeting-notes] Weekly Sync
Body: Document content...
Attachments: Processed automatically
```

---

## Troubleshooting

### Common Issues

#### Upload Fails

**Problem**: Document upload keeps failing

**Solutions**:
1. ✅ Check file size (max 50 MB)
2. ✅ Verify file format (PDF, DOCX, TXT)
3. ✅ Ensure stable internet connection
4. ✅ Try different browser
5. ✅ Clear browser cache

**Error Codes**:
```
413: File too large
415: Unsupported file type
429: Rate limit exceeded (wait 1 hour)
503: Service temporarily unavailable
```

#### Processing Stuck

**Problem**: Document stuck in "Processing" status

**Solutions**:
1. Wait 5-10 minutes (normal for large documents)
2. Check status page: https://status.pmdocintel.com
3. Refresh page (Ctrl+R)
4. Contact support if > 30 minutes

**Processing Times**:
```
Small docs (<5 pages):    20-45 seconds
Medium docs (5-20 pages): 45-90 seconds
Large docs (20+ pages):   90-180 seconds
```

#### Poor Results Quality

**Problem**: AI results are inaccurate or incomplete

**Solutions**:
1. ✅ Verify document is text-searchable (not scanned image)
2. ✅ Choose correct document type
3. ✅ Provide better metadata
4. ✅ Submit feedback to improve AI
5. ✅ Try reprocessing document

**Submit Feedback**:
```
1. Open result page
2. Click "👍 Helpful" or "👎 Not Helpful"
3. Provide specific feedback
4. Suggest corrections
5. Submit
```

#### Search Not Finding Results

**Problem**: Search returns no results or wrong results

**Solutions**:
1. ✅ Check spelling
2. ✅ Try different keywords
3. ✅ Remove filters
4. ✅ Use semantic search (natural language)
5. ✅ Verify document is processed

**Search Debug Tips**:
```
Issue: "No results found"
Try:
  - Broader terms: "budget" instead of "budget overrun"
  - Remove quotes: budget overrun (not "budget overrun")
  - Check filters: Date range might be too narrow
  - Try different document types
```

### Performance Issues

**Slow Page Load**:
1. Clear browser cache
2. Disable browser extensions
3. Use Chrome/Firefox/Safari
4. Check internet speed
5. Try incognito mode

**Timeout Errors**:
1. Refresh page
2. Check status page
3. Retry in 5 minutes
4. Contact support

### Getting Help

**Self-Service Resources**:
- 📚 **Documentation**: https://docs.pmdocintel.com
- 💬 **Community Forum**: https://community.pmdocintel.com
- 📺 **Video Tutorials**: https://youtube.com/pmdocintel
- 📖 **Knowledge Base**: https://help.pmdocintel.com

**Contact Support**:
- 📧 **Email**: support@pmdocintel.com
- 💬 **Live Chat**: Available 9am-5pm EST
- 📞 **Phone**: Enterprise customers only
- 🎫 **Ticket**: Submit at https://support.pmdocintel.com

**Response Times**:
- Email: Within 24 hours
- Live Chat: Immediate during business hours
- Critical Issues: Within 4 hours

---

## Additional Resources

### Video Tutorials

1. **Getting Started** (5 min) - Account setup and first upload
2. **Advanced Search** (8 min) - Semantic search and filters
3. **Team Collaboration** (6 min) - Sharing and permissions
4. **API Integration** (12 min) - Programmatic access

### Webinars

- **Monthly**: "PM Document Intelligence Tips & Tricks"
- **Quarterly**: "New Features Showcase"
- **On-Demand**: Full webinar library available

### Community

Join our community:
- **Forum**: Ask questions, share tips
- **Slack**: Real-time community chat
- **LinkedIn**: Product updates and news
- **Twitter**: @pmdocintel

---

## Feedback

We're always improving! Share your feedback:

- 💡 **Feature Requests**: https://feedback.pmdocintel.com
- 🐛 **Bug Reports**: https://github.com/pmdocintel/issues
- ⭐ **Product Reviews**: G2, Capterra, Product Hunt

---

**Last Updated**: January 2024
**Guide Version**: 1.0.0

Need more help? Contact us at support@pmdocintel.com
