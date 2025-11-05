# Demo Data - Sample Documents

This directory contains sample documents for demonstrating PM Document Intelligence capabilities.

## Document Collection

### 1. Project Status Report (`project_status_report.pdf`)

**Purpose**: Demonstrates summary generation and action item extraction

**Content Summary**:
- Project Alpha Q1 status update
- Current progress at 75% completion
- 3 critical blockers identified
- Budget increase of $50K approved
- Team velocity metrics
- Risk assessment section
- Next steps and action items

**Key Features to Showcase**:
- Executive summary (3 lengths)
- Action item extraction with owners and deadlines
- Risk identification
- Semantic search for "budget concerns"

**Sample Content**:
```
PROJECT ALPHA - Q1 STATUS REPORT
Date: January 15, 2024
Author: Sarah Chen, Project Manager

EXECUTIVE SUMMARY
Project Alpha continues to make strong progress toward Q1 milestones, currently at 75% completion. However, we have identified three critical blockers that require immediate attention...

[Full content continues with sections on:]
- Progress Overview
- Key Accomplishments
- Current Blockers
- Budget Status
- Resource Allocation
- Risk Assessment
- Action Items
- Next Steps
```

---

### 2. Meeting Minutes (`weekly_team_meeting.docx`)

**Purpose**: Demonstrates meeting notes processing and action extraction

**Content Summary**:
- Weekly team sync meeting notes
- 8 participants
- 4 agenda items discussed
- 6 action items assigned
- 2 decisions made
- Follow-up meeting scheduled

**Key Features to Showcase**:
- Participant extraction
- Action item detection with implicit owners
- Decision tracking
- Date/time parsing
- Meeting summary generation

**Sample Content**:
```
WEEKLY TEAM SYNC - MEETING MINUTES
Date: January 15, 2024, 2:00 PM - 3:00 PM
Location: Conference Room B / Zoom
Attendees: Sarah Chen, John Doe, Jane Smith, Mike Johnson,
           Lisa Wang, Tom Brown, Amy Lee, Chris Martinez

AGENDA
1. Q1 Progress Review
2. Blocker Discussion
3. Resource Planning
4. Next Sprint Planning

DISCUSSION NOTES

1. Q1 Progress Review
   - Currently at 75% completion
   - API integration ahead of schedule
   - Frontend development slightly behind
   - John to provide updated timeline by EOW

2. Blocker Discussion
   - Vendor API integration delayed by 2 weeks
   - Sarah to escalate to vendor management team
   - Need additional QA resources
   - Lisa to start recruitment process this week

[Content continues...]

ACTION ITEMS
1. John Doe: Update project timeline - Due: Jan 19
2. Sarah Chen: Escalate vendor issue - Due: Jan 16
3. Lisa Wang: Post QA job listing - Due: Jan 18
4. Mike Johnson: Complete API documentation - Due: Jan 22
5. Team: Review updated requirements - Due: Jan 20
6. Jane Smith: Schedule stakeholder meeting - Due: Jan 23
```

---

### 3. Project Charter (`project_charter.pdf`)

**Purpose**: Demonstrates long-form document analysis and multi-document synthesis

**Content Summary**:
- Project Alpha kick-off document
- Project objectives and scope
- Stakeholder list
- Success criteria
- Timeline and milestones
- Budget allocation
- Risk register
- Team structure

**Key Features to Showcase**:
- Long document processing (10+ pages)
- Structured information extraction
- Multi-section analysis
- Cross-reference capability

**Sample Content**:
```
PROJECT ALPHA - PROJECT CHARTER
Version 1.0 | Approved: December 1, 2023

1. PROJECT OVERVIEW
Project Alpha aims to modernize our customer-facing platform
by implementing a new microservices architecture...

2. BUSINESS CASE
Current system limitations:
- Scalability constraints
- High maintenance costs
- Poor user experience
- Security vulnerabilities

Expected benefits:
- 10× scalability improvement
- 40% cost reduction
- Enhanced security
- Improved user satisfaction

3. PROJECT OBJECTIVES
Primary objectives:
1. Migrate to microservices architecture
2. Improve system performance by 5×
3. Reduce operational costs by 40%
4. Achieve 99.9% uptime

[Content continues with sections on:]
- Scope and Deliverables
- Timeline and Milestones
- Budget and Resources
- Stakeholder Analysis
- Risk Register
- Success Criteria
- Governance Structure
```

---

### 4. Risk Assessment (`risk_assessment_document.pdf`)

**Purpose**: Demonstrates risk identification and analysis capabilities

**Content Summary**:
- Comprehensive project risk analysis
- 12 identified risks with severity levels
- Risk mitigation strategies
- Risk ownership assigned
- Monthly risk review schedule

**Key Features to Showcase**:
- Risk detection and categorization
- Severity assessment
- Mitigation strategy extraction
- Risk trend analysis

**Sample Content**:
```
PROJECT ALPHA - RISK ASSESSMENT
Assessment Date: January 10, 2024
Assessed By: Sarah Chen, Project Manager

RISK REGISTER

RISK #1: Budget Overrun
Severity: HIGH | Likelihood: MEDIUM | Impact: HIGH
Description: Current spending trends indicate potential $50K
overage in Q1 due to additional resource needs.

Root Causes:
- Underestimated complexity of vendor integration
- Need for additional QA resources
- Infrastructure costs higher than projected

Impact Analysis:
- Direct cost: $50K over budget
- Delayed feature delivery
- Reduced scope for Q2 initiatives

Mitigation Strategy:
- Request budget increase approval (approved)
- Optimize cloud resource usage
- Negotiate better vendor pricing
- Consider contractor vs. FTE for QA

Owner: Sarah Chen
Review Date: Weekly
Status: ACTIVE - Mitigation in progress

RISK #2: Key Personnel Departure
Severity: HIGH | Likelihood: LOW | Impact: CRITICAL
Description: Lead architect considering external opportunities.
Loss would significantly impact project timeline.

[Content continues with 10 more risks...]

RISK SUMMARY BY CATEGORY
Technical Risks: 5
Resource Risks: 3
External Risks: 2
Schedule Risks: 2

RISK TREND ANALYSIS
- 3 risks escalated since last review
- 2 risks mitigated and closed
- 1 new risk identified
```

---

### 5. Budget Spreadsheet (`budget_report.pdf`)

**Purpose**: Demonstrates table extraction and financial data processing

**Content Summary**:
- Q1 budget vs. actual spending
- Cost breakdown by category
- Forecast for Q2
- Variance analysis

**Key Features to Showcase**:
- Table data extraction
- Financial calculations
- Trend identification
- Variance detection

**Sample Content**:
```
PROJECT ALPHA - Q1 BUDGET REPORT
Report Period: January 1 - January 15, 2024

BUDGET SUMMARY
                Budget      Actual      Variance    % Variance
Personnel       $250,000    $265,000    +$15,000    +6%
Infrastructure  $50,000     $58,000     +$8,000     +16%
Software        $30,000     $28,000     -$2,000     -7%
Vendors         $100,000    $127,000    +$27,000    +27%
Misc            $20,000     $18,000     -$2,000     -10%
────────────────────────────────────────────────────────────
TOTAL           $450,000    $496,000    +$46,000    +10.2%

COST BREAKDOWN BY MONTH
Month       Budget      Actual      Variance
December    $150,000    $142,000    -$8,000
January     $150,000    $171,000    +$21,000
(projected)

VARIANCE ANALYSIS

Positive Variances (Under Budget):
- Software licenses: Negotiated volume discount
- Miscellaneous: Reduced travel expenses

Negative Variances (Over Budget):
- Personnel: Additional QA contractor hired
- Infrastructure: Unexpected AWS scaling costs
- Vendors: Vendor integration more complex than estimated

[Content continues with forecast and recommendations...]
```

---

### 6. Email Thread Compilation (`email_thread.pdf`)

**Purpose**: Demonstrates email parsing and action item extraction from conversations

**Content Summary**:
- Email thread about vendor escalation
- 5 participants
- Spans 3 days
- Multiple action items buried in conversation
- Decision points in thread

**Key Features to Showcase**:
- Email thread parsing
- Conversational action item extraction
- Implicit deadline detection
- Decision point identification

**Sample Content**:
```
EMAIL THREAD: Vendor API Integration Issue
Thread Date: January 12-15, 2024

────────────────────────────────────────────────────────────
From: Sarah Chen <sarah.chen@company.com>
To: Vendor Support <support@vendorapi.com>
Date: January 12, 2024, 9:15 AM
Subject: URGENT: API Integration Delay Impact

Hi Vendor Support Team,

We're experiencing significant delays with the API integration
for Project Alpha. The original timeline indicated completion
by Jan 5, but we're still encountering authentication issues.

This is blocking our Q1 launch and impacting 5 downstream teams.
Can we schedule an escalation call today?

Best regards,
Sarah Chen
Project Manager

────────────────────────────────────────────────────────────
From: Mike Thompson <mthompson@vendorapi.com>
To: Sarah Chen <sarah.chen@company.com>
CC: John Martinez <john.martinez@vendorapi.com>
Date: January 12, 2024, 2:30 PM
Subject: RE: URGENT: API Integration Delay Impact

Hi Sarah,

My apologies for the delays. I'm escalating this to our
engineering team lead, John Martinez (CC'd).

John will review the authentication logs and schedule a call
for Monday morning. Can you prepare:
- Current error logs
- Your API implementation code
- List of specific endpoints having issues

Best,
Mike Thompson

[Thread continues with 3 more emails discussing resolution...]

────────────────────────────────────────────────────────────
From: John Martinez <john.martinez@vendorapi.com>
To: Sarah Chen; Mike Thompson
Date: January 15, 2024, 10:45 AM
Subject: RE: URGENT: API Integration Delay Impact - RESOLVED

Team,

Good news - we've identified and fixed the authentication issue.
It was a token refresh bug on our side.

Next steps:
1. Deploy fix to production (John M.) - Today by 5 PM
2. Sarah to retest integration - Tomorrow morning
3. Schedule follow-up call if issues persist - Friday

Let me know if you need anything else.

John Martinez
Senior Engineering Lead
```

---

### 7. Technical Specification (`technical_spec.pdf`)

**Purpose**: Demonstrates technical document processing and complex terminology handling

**Content Summary**:
- API design specification
- Technical architecture
- Security requirements
- Performance requirements
- Integration points

**Key Features to Showcase**:
- Technical terminology understanding
- Architecture diagram description
- Requirement extraction
- Specification parsing

**Sample Content**:
```
PROJECT ALPHA - API DESIGN SPECIFICATION
Version: 2.1 | Date: January 10, 2024
Author: Mike Johnson, Lead Architect

1. OVERVIEW
This document specifies the REST API design for Project Alpha's
microservices architecture.

2. ARCHITECTURE

┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Frontend   │─────▶│  API Gateway│─────▶│   Services  │
└─────────────┘      └─────────────┘      └─────────────┘
                            │
                            ▼
                      ┌─────────────┐
                      │  Auth Service│
                      └─────────────┘

3. API ENDPOINTS

3.1 Authentication Endpoints

POST /api/v1/auth/login
Description: Authenticate user and return JWT token
Request Body:
{
  "email": "string",
  "password": "string"
}

Response (200 OK):
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 3600
}

[Content continues with 15 more endpoints...]

4. SECURITY REQUIREMENTS

4.1 Authentication
- JWT-based authentication
- Token expiration: 1 hour
- Refresh tokens: 30 days
- bcrypt for password hashing

4.2 Authorization
- Role-based access control (RBAC)
- Three roles: Admin, User, Guest
- Permission-based access to endpoints

4.3 Data Protection
- TLS 1.3 for all traffic
- AES-256 encryption at rest
- PII detection and masking
- Rate limiting: 100 req/min per user

5. PERFORMANCE REQUIREMENTS
- API response time: < 200ms (p95)
- Throughput: 1000 req/s minimum
- Uptime: 99.9% SLA
- Database query time: < 50ms (p95)

[Content continues with integration points, error handling, etc...]
```

---

## Document Statistics

| Document | Type | Pages | Words | Complexity | AI Features Tested |
|----------|------|-------|-------|------------|--------------------|
| Project Status Report | PDF | 5 | 2,100 | Moderate | Summary, Actions, Risks |
| Meeting Minutes | DOCX | 3 | 1,450 | Simple | Actions, Decisions, Dates |
| Project Charter | PDF | 12 | 4,800 | Complex | Long-form, Structured |
| Risk Assessment | PDF | 8 | 3,200 | Complex | Risk Detection, Analysis |
| Budget Report | PDF | 6 | 1,800 | Moderate | Table Extraction, Numbers |
| Email Thread | PDF | 4 | 1,600 | Simple | Conversation Parsing |
| Technical Spec | PDF | 15 | 5,400 | Complex | Technical Terms, Specs |

---

## Demo Scenarios

### Scenario 1: Quick Demo (5 minutes)
**Upload**: Project Status Report
**Show**:
- Real-time processing
- Summary (all 3 lengths)
- Action items with owners
- Search for "budget"

### Scenario 2: Feature Demo (15 minutes)
**Upload**:
1. Meeting Minutes (show action extraction)
2. Risk Assessment (show risk detection)

**Show**:
- Different document types
- AI accuracy
- Search capabilities
- Analytics dashboard

### Scenario 3: Technical Deep Dive (30 minutes)
**Upload**: All documents
**Show**:
- Document variety handling
- Long document processing
- Table extraction
- Multi-document search
- Cost optimization (check analytics)
- Performance metrics

---

## Creating Your Own Demo Documents

### Guidelines

1. **Make it realistic**: Use actual project management language
2. **Include action items**: Clearly stated and implied
3. **Add complexity**: Mix of well-formatted and challenging sections
4. **Use real names**: Makes demo more relatable
5. **Include numbers**: Budgets, dates, metrics
6. **Add some issues**: Risks, blockers, concerns (more interesting)

### Template Structure

```markdown
[DOCUMENT TYPE] - [TITLE]
Date: [Date]
Author: [Name, Title]

EXECUTIVE SUMMARY
[2-3 paragraphs summarizing key points]

SECTION 1: [TOPIC]
[Content with specific details, numbers, names]
- Key Point 1
- Key Point 2

ACTION ITEMS
1. [Name]: [Task] - Due: [Date]
2. [Name]: [Task] - Due: [Date]

RISKS/CONCERNS
- [Risk with severity]
- [Risk with mitigation]

NEXT STEPS
[What happens next]
```

---

## Generating Demo Documents

### Option 1: Use AI to Generate Content

```python
# Generate realistic demo content
from openai import OpenAI

client = OpenAI()

prompt = """
Create a realistic project status report for a software development project.
Include:
- Project name and summary
- Progress metrics (75% complete)
- 3 specific blockers
- Budget status ($50K over)
- 6 action items with owners and dates
- 3 project risks with mitigation strategies
- Make it sound like a real PM wrote it
"""

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}]
)

print(response.choices[0].message.content)
```

### Option 2: Convert to PDF

```bash
# Convert markdown to PDF using pandoc
pandoc document.md -o document.pdf \
  --pdf-engine=xelatex \
  --variable geometry:margin=1in \
  --variable fontsize=11pt

# Or use a word processor
# - Microsoft Word: Save As > PDF
# - Google Docs: File > Download > PDF
# - LibreOffice: File > Export as PDF
```

---

## Pre-processing Demo Documents

Before the demo, process all documents to have results ready:

```python
# scripts/preprocess_demo_docs.py
import asyncio
from backend.app.services.document_service import DocumentService

async def preprocess_demo_documents():
    """Pre-process all demo documents"""
    demo_docs = [
        "demo_data/project_status_report.pdf",
        "demo_data/weekly_team_meeting.docx",
        "demo_data/project_charter.pdf",
        "demo_data/risk_assessment_document.pdf",
        "demo_data/budget_report.pdf",
        "demo_data/email_thread.pdf",
        "demo_data/technical_spec.pdf"
    ]

    service = DocumentService(db, s3_client, ai_service)

    for doc_path in demo_docs:
        print(f"Processing {doc_path}...")
        with open(doc_path, 'rb') as f:
            await service.upload_and_process(
                file=f,
                filename=os.path.basename(doc_path),
                user_id=DEMO_USER_ID
            )
        print(f"✓ Complete: {doc_path}")

if __name__ == "__main__":
    asyncio.run(preprocess_demo_documents())
```

---

## Backup Documents

Store backup copies in multiple locations:

1. **Local**: `demo_data/` directory
2. **Cloud**: Google Drive / Dropbox
3. **USB**: Physical backup for offline demos
4. **GitHub**: Version control (be careful with sensitive data)

---

## Document Refresh Schedule

**Before each demo**:
- [ ] Verify all documents still process correctly
- [ ] Update dates to recent (keeps demo feeling current)
- [ ] Check for any broken links or references
- [ ] Test search queries
- [ ] Verify action items display properly

**Monthly**:
- [ ] Create new versions with updated content
- [ ] Add new document types if features added
- [ ] Remove outdated references

---

## Related Resources

- [Demo Script](../docs/DEMO_SCRIPT.md) - Step-by-step demo guide
- [Setup Script](../scripts/setup_demo.sh) - Automated demo environment setup
- [Troubleshooting Guide](../docs/DEMO_TROUBLESHOOTING.md) - Fix common issues

---

**Last Updated**: 2024-01-20
**Document Version**: 1.0.0
