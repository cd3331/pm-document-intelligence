# AWS Service Enablement Guide
## PM Document Intelligence - Bedrock and Textract Setup

This guide provides step-by-step instructions to enable AWS Bedrock and Textract services for the PM Document Intelligence application.

---

## Part 1: AWS Bedrock - Automatic Access (Updated 2024)

**IMPORTANT UPDATE**: AWS Bedrock has changed their access model. All serverless foundation models are now **automatically enabled** for your AWS account. You no longer need to manually request model access!

### What This Means

- ✅ **Automatic**: All Bedrock models are immediately available
- ✅ **No manual approval**: The Model Access page has been retired
- ✅ **IAM-controlled**: Your existing IAM policy already grants access
- ⚠️ **Anthropic exception**: Some first-time users may need to submit use case details for Claude models

### Step 1: Verify Bedrock is Ready (Optional)

1. Navigate to Bedrock Console:
   - Direct link: https://console.aws.amazon.com/bedrock/home?region=us-east-1
   - Or search for "Bedrock" in AWS Console

2. Click **"Model catalog"** in the left sidebar

3. You should see all available models without any "Request access" buttons

### Step 2: Test a Model (Optional - Verify Access)

1. In the Model catalog, select any model (e.g., "Claude 3.5 Sonnet" or "Titan Text Express")
2. Click **"Open in playground"**
3. If you can access the playground, Bedrock is working correctly

### Step 3: Handle Anthropic Use Case Requirement (If Needed)

**Only for first-time Anthropic Claude users:**

If you see a prompt asking for use case details when trying to use Claude models:

1. A dialog will appear: "Submit use case details"
2. Fill in the required information:
   - **Use case**: "Project management document analysis and intelligence"
   - **Description**: "AI-powered analysis of project documents including meeting notes, status reports, and project plans to extract action items, risks, and key insights"
   - **Industry**: Select appropriate industry (e.g., "Technology" or "Professional Services")
3. Click **"Submit"**
4. Approval is typically instant or within a few minutes

### Step 4: Review EULAs (For Compliance)

All Bedrock serverless foundation model EULAs can be accessed here:
- https://docs.aws.amazon.com/bedrock/latest/userguide/model-license.html
- Also accessible from model details pages in the model catalog

### Recommended Models for Your Application

Your application can use any of these (all automatically available):

**Best for quality:**
- **Claude 3.5 Sonnet** (anthropic.claude-3-5-sonnet-20240620-v1:0)
- **Claude 3 Sonnet** (anthropic.claude-3-sonnet-20240229-v1:0)

**Best for cost:**
- **Claude 3 Haiku** (anthropic.claude-3-haiku-20240307-v1:0)
- **Amazon Titan Text Express** (amazon.titan-text-express-v1)

**Your IAM policy already grants access to all of these models.**

---

## Part 2: Verify AWS Textract Access

AWS Textract is generally available and should work automatically with your existing IAM permissions. However, let's verify it's enabled and check quotas.

### Step 1: Navigate to Textract Console

1. In the AWS Console search bar, type **"Textract"**
2. Click on **"Amazon Textract"**
   - Direct link: https://console.aws.amazon.com/textract/home?region=us-east-1

### Step 2: Verify Service is Available

1. You should see the Textract dashboard
2. If you see a welcome screen or "Get started" button, the service is available
3. No additional enablement is typically required for Textract

### Step 3: Check Service Quotas (Optional but Recommended)

1. Navigate to Service Quotas:
   - Search for **"Service Quotas"** in the AWS Console
   - Direct link: https://console.aws.amazon.com/servicequotas/home?region=us-east-1

2. In Service Quotas console:
   - Click **"AWS services"** in the left sidebar
   - Search for **"Amazon Textract"**
   - Click on **"Amazon Textract"**

3. Review key quotas:
   - **DetectDocumentText transactions per second**: Default is 1-5 TPS
   - **AnalyzeDocument transactions per second**: Default is 1-5 TPS
   - These defaults should be sufficient for initial usage

### Step 4: Request Quota Increase (If Needed)

Only do this if you expect high traffic:

1. Select a quota (e.g., "DetectDocumentText transactions per second")
2. Click **"Request quota increase"**
3. Enter desired value (e.g., 10 TPS)
4. Click **"Request"**
5. AWS will review and typically approve within 24-48 hours

### Step 5: Test Textract (Optional)

1. Return to Textract Console
2. Click **"Try Amazon Textract"** or **"Demos"**
3. Upload a sample PDF or image
4. Click **"Analyze"**
5. If results appear, Textract is working correctly

---

## Part 3: Verify Integration with Your Application

After enabling both services, verify they work with your application.

### Step 1: Check Application Health Status

```bash
curl https://api.joyofpm.com/ready
```

Expected output should show:
```json
{
  "status": "healthy",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "s3": "healthy",
    "comprehend": "healthy",
    "bedrock": "healthy",        // Should change from "degraded" to "healthy"
    "textract": "healthy"        // Should change from "degraded" to "healthy"
  }
}
```

### Step 2: Force ECS Service to Check Again

The application caches health check results. To force a refresh:

**Option A: Restart ECS Service (Recommended)**

```bash
# Force new deployment to pick up changes
aws ecs update-service \
  --cluster pm-doc-intel-production \
  --service pm-doc-intel-api-production \
  --force-new-deployment \
  --region us-east-1

# Wait for deployment to complete
aws ecs wait services-stable \
  --cluster pm-doc-intel-production \
  --services pm-doc-intel-api-production \
  --region us-east-1
```

**Option B: Wait for Natural Health Check** (5-10 minutes)

The application checks service health periodically. Just wait a few minutes and check again.

### Step 3: Test Document Processing with Bedrock

1. Go to https://app.joyofpm.com
2. Log in to your account
3. Upload a PDF document
4. Click **"Process Document"**
5. Wait for processing to complete (30-60 seconds)
6. Verify you see:
   - AI-generated summary
   - Extracted action items
   - Risk assessment

### Step 4: Test PDF Text Extraction with Textract

1. Upload a PDF file (not a text file)
2. Click **"Process Document"**
3. The backend should use Textract to extract text from the PDF
4. Check the document detail page - you should see extracted text content

---

## Troubleshooting

### Issue: "Access denied" when calling Bedrock

**Cause**: IAM permissions issue or use case approval needed

**Solutions**:
1. Verify you're using **us-east-1** region
2. Check if Anthropic use case details are required (first-time users)
3. Submit use case details in Bedrock console if prompted
4. Verify the model ID exists and is spelled correctly
5. Check IAM policy includes: `bedrock:InvokeModel` permission

### Issue: "Throttling" errors from Bedrock

**Cause**: Rate limits on free tier or initial quotas

**Solutions**:
1. Navigate to Service Quotas → AWS Bedrock
2. Request increase for "Requests per minute" quota
3. Consider using Claude Haiku (faster, higher throughput)

### Issue: Textract still shows "degraded"

**Cause**: Service quota too low or service not available in region

**Solutions**:
1. Verify you're in us-east-1 region
2. Check Service Quotas as described above
3. Request quota increase if TPS is 0 or very low
4. Wait 24 hours after account creation (new account limits)

### Issue: Health check still shows "degraded" after enabling

**Cause**: Application hasn't rechecked yet

**Solutions**:
1. Force ECS deployment (see Step 2 above)
2. Wait 5-10 minutes for natural health check cycle
3. Check CloudWatch Logs for any error messages:
   ```bash
   aws logs tail /ecs/pm-doc-intel/production --since 5m --follow
   ```

---

## Cost Considerations

### AWS Bedrock Pricing (us-east-1)

- **Claude 3 Haiku**: ~$0.25 per 1K input tokens, ~$1.25 per 1K output tokens
- **Claude 3 Sonnet**: ~$3 per 1K input tokens, ~$15 per 1K output tokens
- **Claude 3.5 Sonnet**: ~$3 per 1K input tokens, ~$15 per 1K output tokens
- **Amazon Titan Express**: ~$0.20 per 1K input tokens, ~$0.60 per 1K output tokens

**Estimate**: Processing a 10-page document (~5K tokens) with Claude Haiku = ~$0.02 per document

### AWS Textract Pricing

- **DetectDocumentText**: $0.0015 per page (first 1M pages/month)
- **AnalyzeDocument**: $0.05 per page (first 1M pages/month)

**Estimate**: Processing a 10-page PDF = ~$0.015 to $0.50 depending on analysis type

### Cost Optimization Tips

1. Use **Claude Haiku** for most tasks (10x cheaper than Sonnet)
2. Use **OpenAI** instead if you already have credits
3. Cache extracted text to avoid re-processing
4. Use **DetectDocumentText** instead of AnalyzeDocument when only text is needed

---

## Summary Checklist

Use this checklist to track your progress:

**Bedrock Setup (Automatic - Nothing Required!)**
- [ ] ✅ All Bedrock models are automatically enabled (no action needed)
- [ ] (Optional) Submitted Anthropic use case details if prompted
- [ ] (Optional) Tested a model in Bedrock playground

**Textract Verification**
- [ ] Checked Textract console and confirmed service is available
- [ ] (Optional) Reviewed Textract service quotas

**Application Verification**
- [ ] Forced ECS service redeployment or waited for health check
- [ ] Verified `/ready` endpoint shows "healthy" for Bedrock
- [ ] Verified `/ready` endpoint shows "healthy" for Textract
- [ ] Tested document upload and processing in application
- [ ] Confirmed AI analysis results appear correctly

---

## Next Steps After Enablement

Once both services are enabled and showing "healthy":

1. **Test with real documents**: Upload meeting notes, project plans, status reports
2. **Try Q&A feature**: Ask questions about uploaded documents
3. **Monitor costs**: Set up AWS Budgets alert for Bedrock/Textract usage
4. **Optimize**: Switch to cheaper models if quality is acceptable

---

## Support Resources

- **AWS Bedrock Documentation**: https://docs.aws.amazon.com/bedrock/
- **AWS Textract Documentation**: https://docs.aws.amazon.com/textract/
- **Service Quotas**: https://docs.aws.amazon.com/servicequotas/
- **Application Logs**: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group//ecs/pm-doc-intel/production

---

**Document Version**: 1.0
**Last Updated**: 2025-11-08
**Application**: PM Document Intelligence
**AWS Account**: 488678936715
**Region**: us-east-1
