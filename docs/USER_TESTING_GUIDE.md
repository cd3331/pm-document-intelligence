# PM Document Intelligence - User Testing Guide

## Quick Test (5 minutes)

### 1. Access the Application
Visit: https://app.joyofpm.com

### 2. Create an Account
- Click "Get Started Free"
- Enter your name, email, and password (min 8 characters)
- Click "Create Account"
- You'll be automatically logged in

### 3. Upload a Document
- Create a simple text file (test.txt) with some content
- Drag and drop it to the upload area, or click to browse
- Wait for upload to complete (should be instant)

### 4. View Your Document
- Click "View Analysis" on your uploaded document
- You'll see the document detail page

### 5. Process the Document
- Click the "Process Document" button
- Wait for AI processing (may take 30-60 seconds)
- Page will reload with analysis results

### 6. Review Analysis
- Summary tab: AI-generated executive summary
- Action Items tab: Extracted tasks and to-dos
- Risk Assessment tab: Identified project risks
- Q&A tab: Ask questions about your document

## Expected Results

✅ **Working Features:**
- User registration and login
- Document upload (.txt, .md files)
- Document listing
- Document viewing
- AI processing with OpenAI
- Document summaries
- Action item extraction
- Risk assessment
- Q&A about documents

⚠️ **Limited Features (until AWS services enabled):**
- PDF text extraction (Textract not enabled)
- AWS Bedrock models (requires model access request)
- Can use OpenAI instead for AI processing

## Troubleshooting

**"Network error" on upload:**
- Check that you're using a supported file type (.txt, .pdf, .doc, .docx, .md)
- File must be under 100MB

**"Process document endpoint not yet implemented":**
- This message should NOT appear anymore
- If you see it, the latest deployment may not be live yet

**"Loading summary..." forever:**
- This should NOT happen anymore
- Page should show placeholder text if not processed
- Or actual analysis if processed

## API Endpoints for Testing

All endpoints at: https://api.joyofpm.com/api/v1

**Health Check:**
```bash
curl https://api.joyofpm.com/ready
```

**Register:**
```bash
curl -X POST https://api.joyofpm.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123!","full_name":"Test User"}'
```

**Login:**
```bash
curl -X POST https://api.joyofpm.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123!"}'
```

## Support

Issues? Check:
1. Browser console for errors (F12)
2. Network tab to see failed requests
3. Try logging out and back in
4. Clear browser cache and cookies

## Next Steps to Enable Full Functionality

1. **Enable AWS Bedrock Models:**
   - Go to https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess
   - Request access to Claude 3 Sonnet or Titan models
   - Wait for approval (usually instant for some models)

2. **Enable Textract (optional):**
   - Textract is already permitted in IAM
   - Should work automatically for PDF files
   - If not, check service quotas in AWS Console

3. **Test with Real Documents:**
   - Upload meeting notes
   - Upload project status reports
   - Upload project plans
   - Ask specific questions about the content
