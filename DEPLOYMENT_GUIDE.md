# Production Deployment Guide
# PM Document Intelligence - AWS Production Deployment

## 🚀 Quick Start

This guide walks you through deploying the PM Document Intelligence platform to AWS using GitHub Actions for CI/CD automation.

---

## 📋 Prerequisites

### ✅ Completed
- [x] GitHub repository with code
- [x] AWS credentials configured in GitHub Secrets
- [x] GitHub Actions workflow files in place

### 🔧 Required Before First Deployment

1. **AWS Account Access**
   - Active AWS account with admin or deployment permissions
   - Billing enabled
   - Service limits verified for your region

2. **Domain & SSL Certificate (Optional but Recommended)**
   - Domain name (e.g., pmdocintel.com)
   - SSL certificate in AWS Certificate Manager (ACM)

3. **External Services API Keys**
   - ✅ OpenAI API key
   - ✅ AWS Bedrock access enabled
   - ✅ PubNub keys
   - ✅ Supabase credentials
   - ✅ Sentry DSN (optional)

---

## 🏗️ Deployment Architecture

```
GitHub Repository (master branch)
         ↓
   GitHub Actions
         ↓
    Build & Test
         ↓
   Docker Image → AWS ECR
         ↓
   AWS ECS Fargate
         ↓
   Production Environment
   - Application Load Balancer
   - ECS Tasks (Auto-scaling)
   - RDS PostgreSQL
   - ElastiCache Redis
   - S3 Storage
   - CloudWatch Monitoring
```

---

## 📝 Step-by-Step Deployment

### Step 1: Initial AWS Infrastructure Setup (First Time Only)

The first deployment requires manual infrastructure setup using Terraform.

#### 1.1 Configure Terraform Variables

```bash
cd infrastructure/terraform

# Copy example to create your config
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars  # or use your editor
```

**Key values to configure in `terraform.tfvars`:**

```hcl
# General
project_name = "pm-doc-intel"
environment  = "production"
aws_region   = "us-east-1"

# Network
vpc_cidr = "10.0.0.0/16"
az_count = 2

# ECS
ecs_task_cpu              = "2048"  # Start smaller, scale up
ecs_task_memory           = "4096"
ecs_service_desired_count = 2

# Database
db_instance_class    = "db.t3.medium"  # Cost-effective start
db_allocated_storage = 50

# Redis
redis_node_type = "cache.t3.small"

# SSL (if you have a domain)
ssl_certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/xxxxx"
domain_name         = "your-domain.com"

# Features for production
enable_multi_az            = true
enable_deletion_protection = true
enable_container_insights  = true
```

#### 1.2 Deploy Infrastructure with Terraform

```bash
# Initialize Terraform
terraform init

# Review the infrastructure plan
terraform plan -out=tfplan

# Apply the infrastructure (will take 10-15 minutes)
terraform apply tfplan
```

**Important outputs to note:**
- ECR Repository URL
- ECS Cluster Name
- ALB DNS Name
- Database Endpoint
- Redis Endpoint

#### 1.3 Update GitHub Secrets with Terraform Outputs

After Terraform completes, add these additional secrets to GitHub:

```bash
# Get ECR repository URL from Terraform output
terraform output ecr_repository_url
```

Go to GitHub → Settings → Secrets → Actions → Add:

```
ECR_REPOSITORY_URL     = <from terraform output>
ECS_CLUSTER_NAME       = pm-doc-intel-cluster-production
ECS_SERVICE_NAME       = pm-doc-intel-backend-service-production
DATABASE_URL           = <from terraform output>
REDIS_URL              = <from terraform output>
```

---

### Step 2: Configure Production Environment Variables

Create production environment file (store in GitHub Secrets or AWS Secrets Manager):

**Required Environment Variables for Production:**

```bash
# Application
APP_NAME=pm-document-intelligence
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<generate-random-64-char-string>

# Database (from Terraform output)
DATABASE_URL=postgresql://user:pass@db-endpoint:5432/pm_document_intelligence

# Redis (from Terraform output)
REDIS_URL=redis://redis-endpoint:6379/0

# AWS Services
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# OpenAI
OPENAI_API_KEY=<your-key>
OPENAI_MODEL=gpt-4o

# Supabase
SUPABASE_URL=<your-url>
SUPABASE_KEY=<your-key>
SUPABASE_SERVICE_KEY=<your-service-key>

# PubNub
PUBNUB_PUBLISH_KEY=<your-key>
PUBNUB_SUBSCRIBE_KEY=<your-key>

# Security
JWT_SECRET_KEY=<generate-random-64-char-string>
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Monitoring
SENTRY_DSN=<your-sentry-dsn>
SENTRY_ENABLED=true
SENTRY_ENVIRONMENT=production

# Feature Flags
FEATURE_CACHING_ENABLED=true
FEATURE_VECTOR_SEARCH_ENABLED=true
FEATURE_REAL_TIME_UPDATES_ENABLED=true
```

**Store these in AWS Secrets Manager:**

```bash
# Create secrets in AWS
aws secretsmanager create-secret \
  --name pm-doc-intel/production/env \
  --secret-string file://production.env \
  --region us-east-1
```

---

### Step 3: Deploy via GitHub Actions

Now that infrastructure is ready, GitHub Actions will handle all future deployments automatically!

#### Option A: Automatic Deployment (Push to master)

```bash
# Commit your changes
git add .
git commit -m "deploy: configure production environment"

# Push to master - this triggers automatic deployment
git push origin master
```

#### Option B: Manual Deployment Trigger

1. Go to: https://github.com/cd3331/pm-document-intelligence/actions
2. Click "Deploy to AWS ECS" workflow
3. Click "Run workflow"
4. Select "production" environment
5. Click "Run workflow"

---

### Step 4: Monitor Deployment

#### 4.1 Watch GitHub Actions

```
https://github.com/cd3331/pm-document-intelligence/actions
```

Deployment stages:
1. ✅ Lint & Format Check (~2 min)
2. ✅ Security Scan (~2 min)
3. ✅ Run Tests (~3 min)
4. ✅ Build & Push Docker Image (~5 min)
5. ✅ Deploy to ECS (~3 min)
6. ✅ Post-deployment Tests (~2 min)

**Total time: ~15-20 minutes**

#### 4.2 Monitor AWS Deployment

```bash
# Watch ECS service deployment
aws ecs describe-services \
  --cluster pm-doc-intel-cluster-production \
  --services pm-doc-intel-backend-service-production \
  --region us-east-1

# Watch task status
aws ecs list-tasks \
  --cluster pm-doc-intel-cluster-production \
  --service-name pm-doc-intel-backend-service-production \
  --region us-east-1

# View logs
aws logs tail /ecs/pm-doc-intel-backend-production --follow
```

---

### Step 5: Verify Deployment

#### 5.1 Health Check

```bash
# Get ALB DNS name from Terraform
ALB_URL=$(terraform output alb_dns_name)

# Check health endpoint
curl https://$ALB_URL/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": 1699564800.123,
  "environment": "production",
  "version": "1.0.1",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    },
    "redis": {
      "status": "healthy",
      "message": "Redis connection successful"
    },
    "aws": {
      "status": "healthy",
      "services": {
        "bedrock": true,
        "s3": true,
        "textract": true,
        "comprehend": true
      }
    }
  }
}
```

#### 5.2 Smoke Tests

```bash
# API Documentation
curl https://$ALB_URL/docs

# Basic API test
curl -X POST https://$ALB_URL/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_document.pdf"
```

---

## 🔄 Ongoing Deployments

After the initial setup, deployments are automatic:

### Automatic Deployments

Every push to `master` branch triggers:
1. Automated testing
2. Docker image build
3. Push to ECR
4. Deploy to ECS production
5. Health checks

### Rollback Strategy

If deployment fails:

```bash
# View previous task definitions
aws ecs list-task-definitions \
  --family-prefix pm-doc-intel-backend \
  --region us-east-1

# Rollback to previous version
aws ecs update-service \
  --cluster pm-doc-intel-cluster-production \
  --service pm-doc-intel-backend-service-production \
  --task-definition pm-doc-intel-backend-production:PREVIOUS_VERSION \
  --region us-east-1
```

Or use GitHub Actions:
1. Go to previous successful deployment
2. Click "Re-run jobs"

---

## 📊 Monitoring & Alerts

### CloudWatch Dashboards

Access metrics at:
```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:
```

Key metrics:
- ECS CPU/Memory utilization
- ALB request count & latency
- RDS connections & performance
- Redis hit rate
- Application errors

### Sentry Error Tracking

Monitor application errors:
```
https://sentry.io/organizations/your-org/issues/
```

### Cost Monitoring

```bash
# View monthly costs
aws ce get-cost-and-usage \
  --time-period Start=2025-11-01,End=2025-11-30 \
  --granularity MONTHLY \
  --metrics "BlendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE
```

---

## 🛠️ Troubleshooting

### Deployment Fails

**Check GitHub Actions logs:**
1. Go to Actions tab
2. Click failed workflow
3. Check which step failed

**Common issues:**
- ❌ Tests failing → Fix code and push again
- ❌ Docker build failing → Check Dockerfile syntax
- ❌ ECR push failing → Verify AWS credentials
- ❌ ECS deployment failing → Check task definition, secrets

### Application Not Starting

```bash
# Check ECS task logs
aws logs tail /ecs/pm-doc-intel-backend-production --follow

# Common issues:
# - Missing environment variables
# - Database connection issues
# - Port conflicts
# - Memory/CPU limits too low
```

### Performance Issues

```bash
# Scale up ECS tasks
aws ecs update-service \
  --cluster pm-doc-intel-cluster-production \
  --service pm-doc-intel-backend-service-production \
  --desired-count 5 \
  --region us-east-1

# Upgrade task size (requires task definition update)
# Edit terraform.tfvars:
ecs_task_cpu    = "4096"
ecs_task_memory = "8192"

# Apply changes
terraform apply
```

---

## 💰 Cost Optimization

### Current Estimated Costs (Production)

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| ECS Fargate | 2 tasks, 2 vCPU, 4GB each | ~$60 |
| ALB | Load balancer + data transfer | ~$20 |
| RDS PostgreSQL | db.t3.medium | ~$50 |
| ElastiCache Redis | cache.t3.small | ~$30 |
| S3 | 100GB storage, 1M requests | ~$5 |
| CloudWatch Logs | 10GB/month | ~$5 |
| Data Transfer | 100GB/month | ~$10 |
| **Total** | | **~$180/month** |

**Cost-saving tips:**
- Use Savings Plans for 30-40% discount
- Enable auto-scaling to scale down during low traffic
- Use S3 lifecycle policies for old documents
- Compress CloudWatch logs
- Use RDS reserved instances

---

## 🔐 Security Best Practices

### Implemented

- ✅ SSL/TLS encryption (ALB)
- ✅ Private subnets for database/redis
- ✅ Security groups with least privilege
- ✅ Secrets in AWS Secrets Manager
- ✅ IAM roles with minimal permissions
- ✅ CloudWatch log encryption
- ✅ S3 bucket encryption
- ✅ Database encryption at rest

### Recommended Additions

- [ ] Enable AWS WAF on ALB
- [ ] Set up AWS GuardDuty
- [ ] Configure AWS Security Hub
- [ ] Enable VPC Flow Logs
- [ ] Set up AWS Config rules
- [ ] Regular security audits

---

## 📞 Support & Escalation

### Issue Priority Levels

**P0 - Critical (Production Down)**
- Complete service outage
- Data loss
- Security breach
→ Immediate rollback + investigation

**P1 - High (Degraded Service)**
- Slow performance
- Intermittent errors
- High error rates
→ Scale resources + investigate

**P2 - Medium (Non-Critical)**
- Minor bugs
- Feature issues
→ Fix in next deployment

### Contact

- **Owner**: Chandra Dunn
- **Email**: cd3331github@gmail.com
- **GitHub**: @cd3331

---

## 📚 Additional Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Application Documentation](docs/)

---

**Last Updated**: 2025-11-05
**Version**: 1.0.1
**Deployment Method**: GitHub Actions + Terraform
