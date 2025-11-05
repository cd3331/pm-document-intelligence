# PM Document Intelligence - Deployment Guide

This comprehensive guide covers deploying PM Document Intelligence to production on AWS using ECS, Terraform, and CI/CD.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Environment Setup](#environment-setup)
4. [Secrets Configuration](#secrets-configuration)
5. [Infrastructure Deployment](#infrastructure-deployment)
6. [Application Deployment](#application-deployment)
7. [Post-Deployment Verification](#post-deployment-verification)
8. [Monitoring Setup](#monitoring-setup)
9. [Backup Configuration](#backup-configuration)
10. [Rollback Procedures](#rollback-procedures)
11. [Troubleshooting](#troubleshooting)
12. [Cost Estimation](#cost-estimation)

---

## Prerequisites

### Required Tools

- **AWS CLI** (v2.x or later)
  ```bash
  aws --version
  aws configure
  ```

- **Terraform** (v1.5.0 or later)
  ```bash
  terraform version
  ```

- **Docker** (v20.x or later)
  ```bash
  docker --version
  ```

- **Git**
  ```bash
  git --version
  ```

- **Python** 3.11+
  ```bash
  python --version
  ```

### AWS Account Requirements

- **IAM User/Role** with permissions for:
  - ECS (Fargate)
  - RDS
  - ElastiCache
  - S3
  - ECR
  - VPC
  - Route53
  - CloudWatch
  - Secrets Manager
  - IAM
  - Certificate Manager

- **AWS Account Limits**:
  - VPC limit: At least 1 available
  - Elastic IP limit: At least 2 available (for NAT gateways)
  - ECS tasks: At least 10 concurrent tasks

### Domain and SSL

- **Domain Name**: Registered domain (e.g., example.com)
- **SSL Certificate**: Valid SSL certificate in AWS Certificate Manager
  ```bash
  aws acm request-certificate \
    --domain-name api.example.com \
    --validation-method DNS \
    --region us-east-1
  ```

### Third-Party Services

- **Supabase Account**: For PostgreSQL database (or use RDS)
- **OpenAI API Key**: For AI/ML features
- **PubNub Account**: For real-time messaging

---

## Architecture Overview

### Infrastructure Components

```
┌─────────────────────────────────────────────────────────┐
│                      Internet                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
            ┌────────────────┐
            │ Route53 (DNS)  │
            └────────┬───────┘
                     │
                     ▼
            ┌────────────────┐
            │      ALB       │
            │  (443, 80)     │
            └────────┬───────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌────────────────┐      ┌────────────────┐
│  ECS Fargate   │      │  ECS Fargate   │
│  (Backend)     │      │  (Backend)     │
│  AZ-1          │      │  AZ-2          │
└────────┬───────┘      └────────┬───────┘
         │                       │
    ┌────┴───────────────────────┴────┐
    │                                  │
    ▼                                  ▼
┌──────────┐                    ┌──────────┐
│   RDS    │                    │  ElastiCache│
│PostgreSQL│                    │   Redis   │
│Multi-AZ  │                    │           │
└──────────┘                    └──────────┘
```

### Network Architecture

- **VPC**: 10.0.0.0/16
- **Public Subnets**: 10.0.0.0/24, 10.0.1.0/24 (ALB, NAT Gateway)
- **Private Subnets**: 10.0.10.0/24, 10.0.11.0/24 (ECS, RDS, ElastiCache)
- **Availability Zones**: 2 (for high availability)

---

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/pm-document-intelligence.git
cd pm-document-intelligence
```

### 2. Configure AWS Credentials

```bash
aws configure
# Enter AWS Access Key ID
# Enter AWS Secret Access Key
# Default region: us-east-1
# Default output format: json
```

Verify credentials:
```bash
aws sts get-caller-identity
```

### 3. Set Environment Variables

```bash
export AWS_REGION=us-east-1
export ENVIRONMENT=production  # or staging, development
export PROJECT_NAME=pm-doc-intel
```

---

## Secrets Configuration

### 1. Create Secrets File

```bash
cp secrets.yml.example secrets.yml
```

### 2. Fill in Actual Values

Edit `secrets.yml` with real credentials:

```yaml
aws:
  access_key_id: "YOUR_ACCESS_KEY"
  secret_access_key: "YOUR_SECRET_KEY"
  region: "us-east-1"

database:
  production:
    password: "STRONG_RANDOM_PASSWORD"

openai:
  api_key: "sk-YOUR_OPENAI_KEY"

jwt:
  secret_key: "GENERATE_WITH: openssl rand -base64 32"
```

### 3. Store Secrets in AWS Secrets Manager

```bash
# JWT Secret
aws secretsmanager create-secret \
  --name pm-doc-intel/jwt-secret-production \
  --secret-string "YOUR_JWT_SECRET" \
  --region us-east-1

# OpenAI API Key
aws secretsmanager create-secret \
  --name pm-doc-intel/openai-api-key-production \
  --secret-string "YOUR_OPENAI_KEY" \
  --region us-east-1

# Database Password
aws secretsmanager create-secret \
  --name pm-doc-intel/db-password-production \
  --secret-string "YOUR_DB_PASSWORD" \
  --region us-east-1
```

### 4. Store GitHub Secrets

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `SLACK_WEBHOOK_URL`
- `OPENAI_API_KEY`

---

## Infrastructure Deployment

### 1. Initialize Terraform Backend

#### Option A: Create Backend Resources First

```bash
cd infrastructure/terraform

# Uncomment backend resources in backend.tf
# Run terraform to create S3 bucket and DynamoDB table
terraform init
terraform plan
terraform apply

# Comment out backend resources
# Uncomment backend configuration
terraform init -migrate-state
```

#### Option B: Use Existing S3 Bucket

Update `backend.tf` with your bucket name:
```hcl
backend "s3" {
  bucket         = "your-existing-terraform-state-bucket"
  key            = "pm-doc-intel/terraform.tfstate"
  region         = "us-east-1"
  dynamodb_table = "your-terraform-locks-table"
  encrypt        = true
}
```

### 2. Configure Terraform Variables

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

```hcl
project_name = "pm-doc-intel"
environment  = "production"
aws_region   = "us-east-1"

# ECS Configuration
ecs_task_cpu              = "4096"
ecs_task_memory           = "8192"
ecs_service_desired_count = 3

# Database
db_instance_class = "db.r6g.xlarge"

# SSL Certificate ARN (from ACM)
ssl_certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/xxxxx"

# Domain
domain_name = "example.com"

# ECR Repository URL
ecr_repository_url = "123456789012.dkr.ecr.us-east-1.amazonaws.com/pm-document-intelligence"
```

### 3. Create ECR Repository

```bash
aws ecr create-repository \
  --repository-name pm-document-intelligence \
  --region us-east-1

# Get repository URI
aws ecr describe-repositories \
  --repository-names pm-document-intelligence \
  --region us-east-1 \
  --query 'repositories[0].repositoryUri' \
  --output text
```

### 4. Deploy Infrastructure

```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Review plan
terraform plan

# Apply infrastructure changes
terraform apply
```

This will create:
- VPC with public/private subnets
- ECS Cluster
- Application Load Balancer
- RDS PostgreSQL database
- ElastiCache Redis
- S3 buckets
- IAM roles and policies
- CloudWatch log groups
- Route53 DNS records

**Deployment time**: ~15-20 minutes

### 5. Save Terraform Outputs

```bash
terraform output > ../deployment-outputs.txt
```

Important outputs:
- `alb_dns_name`: Load balancer URL
- `rds_endpoint`: Database endpoint
- `redis_endpoint`: Redis endpoint
- `api_url`: API endpoint

---

## Application Deployment

### 1. Build and Push Docker Image

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  123456789012.dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t pm-document-intelligence:latest .

# Tag image
docker tag pm-document-intelligence:latest \
  123456789012.dkr.ecr.us-east-1.amazonaws.com/pm-document-intelligence:latest

# Push to ECR
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/pm-document-intelligence:latest
```

### 2. Update ECS Service

The infrastructure deployment already created the ECS service, but you need to trigger a new deployment:

```bash
aws ecs update-service \
  --cluster pm-doc-intel-cluster-production \
  --service pm-doc-intel-backend-service-production \
  --force-new-deployment \
  --region us-east-1
```

### 3. Monitor Deployment

```bash
# Watch service status
aws ecs describe-services \
  --cluster pm-doc-intel-cluster-production \
  --services pm-doc-intel-backend-service-production \
  --region us-east-1 \
  --query 'services[0].deployments'

# View logs
aws logs tail /ecs/pm-doc-intel/production --follow
```

### 4. Using Deployment Script

Alternatively, use the deployment script:

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh --environment production --tag v1.0.0
```

---

## Post-Deployment Verification

### 1. Health Checks

```bash
# Get ALB DNS
ALB_DNS=$(terraform output -raw alb_dns_name)

# Test liveness
curl https://$ALB_DNS/health/live

# Test readiness
curl https://$ALB_DNS/health/ready

# Test API
curl https://$ALB_DNS/api/v1/health
```

### 2. Verify Database Connection

```bash
# Get RDS endpoint
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)

# Connect to database (from bastion or local with VPN)
psql postgresql://pmadmin:PASSWORD@$RDS_ENDPOINT/pm_document_intelligence

# Check tables
\dt
```

### 3. Verify Redis Connection

```bash
# Get Redis endpoint
REDIS_ENDPOINT=$(terraform output -raw redis_endpoint)

# Test connection
redis-cli -h $REDIS_ENDPOINT ping
```

### 4. Test API Endpoints

```bash
# Register user
curl -X POST https://api.example.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPassword123!"
  }'

# Login
curl -X POST https://api.example.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "TestPassword123!"
  }'
```

---

## Monitoring Setup

### 1. Access Grafana

```bash
# Get Grafana URL from Terraform outputs
terraform output grafana_url

# Default credentials: admin/admin
# Change password on first login
```

### 2. Configure Alerts

Alerts are automatically configured via Terraform. Verify:

```bash
# Check Prometheus alerts
curl http://PROMETHEUS_URL:9090/api/v1/rules

# Check Alertmanager
curl http://ALERTMANAGER_URL:9093/api/v2/alerts
```

### 3. Set Up CloudWatch Dashboards

AWS Console → CloudWatch → Dashboards

Create dashboard with:
- ECS CPU/Memory utilization
- RDS performance metrics
- ALB request counts
- Application logs

---

## Backup Configuration

### 1. Automated Database Backups

RDS automated backups are configured via Terraform:
- Retention: 7 days
- Backup window: 03:00-04:00 UTC
- Multi-AZ: Enabled

### 2. Manual Backup Script

```bash
chmod +x scripts/backup.sh

# Run backup
./scripts/backup.sh --environment production

# Scheduled backup (cron)
# Add to crontab:
0 2 * * * /path/to/scripts/backup.sh --environment production
```

### 3. S3 Backup Verification

```bash
aws s3 ls s3://pm-doc-intel-backups-production/ --recursive
```

---

## Rollback Procedures

### 1. Rollback ECS Deployment

```bash
# Get previous task definition
PREVIOUS_TASK_DEF=$(aws ecs describe-services \
  --cluster pm-doc-intel-cluster-production \
  --services pm-doc-intel-backend-service-production \
  --query 'services[0].deployments[1].taskDefinition' \
  --output text)

# Update service to previous version
aws ecs update-service \
  --cluster pm-doc-intel-cluster-production \
  --service pm-doc-intel-backend-service-production \
  --task-definition $PREVIOUS_TASK_DEF
```

### 2. Rollback Database Migration

```bash
# Connect to database
psql postgresql://pmadmin:PASSWORD@RDS_ENDPOINT/pm_document_intelligence

# Run down migration
# (Implement using Alembic or similar)
alembic downgrade -1
```

### 3. Rollback Infrastructure

```bash
cd infrastructure/terraform

# Revert to previous Terraform state
terraform state list
terraform state pull > backup.tfstate

# Apply previous configuration
git checkout previous-commit
terraform plan
terraform apply
```

---

## Troubleshooting

### ECS Tasks Failing to Start

**Symptoms**: Tasks immediately fail after starting

**Solutions**:
1. Check CloudWatch logs:
   ```bash
   aws logs tail /ecs/pm-doc-intel/production --follow
   ```

2. Verify environment variables in task definition

3. Check IAM role permissions

4. Verify ECR image exists and is accessible

### Database Connection Issues

**Symptoms**: Application cannot connect to RDS

**Solutions**:
1. Verify security group allows traffic from ECS tasks
2. Check database endpoint and credentials
3. Verify database is in same VPC as ECS tasks
4. Test connection from ECS task:
   ```bash
   aws ecs execute-command \
     --cluster pm-doc-intel-cluster-production \
     --task TASK_ID \
     --container backend \
     --interactive \
     --command "/bin/bash"
   ```

### High CPU/Memory Usage

**Symptoms**: ECS tasks using >80% CPU/memory

**Solutions**:
1. Scale up task resources:
   - Update `ecs_task_cpu` and `ecs_task_memory` in terraform.tfvars
   - Apply changes: `terraform apply`

2. Scale out (more tasks):
   - Increase `ecs_service_desired_count`
   - Or let auto-scaling handle it

3. Optimize application code
4. Enable caching for frequently accessed data

### SSL Certificate Errors

**Symptoms**: HTTPS not working, certificate errors

**Solutions**:
1. Verify certificate is validated in ACM
2. Check certificate ARN in terraform.tfvars
3. Verify domain points to ALB
4. Wait for DNS propagation (up to 48 hours)

---

## Cost Estimation

### Monthly Cost Breakdown (Production)

| Service | Configuration | Estimated Cost |
|---------|--------------|----------------|
| **ECS Fargate** | 3 tasks × 4 vCPU × 8GB | $150-200 |
| **RDS PostgreSQL** | db.r6g.xlarge Multi-AZ | $300-400 |
| **ElastiCache Redis** | cache.r6g.large | $100-150 |
| **Application Load Balancer** | 1 ALB | $20-30 |
| **NAT Gateway** | 2 NAT Gateways | $70 |
| **Data Transfer** | ~500 GB/month | $40-50 |
| **S3 Storage** | ~100 GB | $3-5 |
| **CloudWatch Logs** | ~50 GB/month | $25-30 |
| **Secrets Manager** | 5 secrets | $2 |
| **Route53** | 1 hosted zone | $1 |
| **ECR** | ~10 GB images | $1 |
| **TOTAL** | | **$712-938/month** |

### Cost Optimization Tips

1. **Use Fargate Spot** for non-critical tasks (50-70% savings)
2. **Reserved Instances** for RDS (up to 60% savings)
3. **S3 Lifecycle Policies** to move old data to Glacier
4. **CloudWatch Log Retention** reduce from 30 to 7 days
5. **ElastiCache Reserved Nodes** (up to 55% savings)

### Development Environment

For development, costs can be reduced to ~$200-300/month:
- ECS: 1 task × 1 vCPU × 2GB (~$30)
- RDS: db.t3.small (~$30)
- ElastiCache: cache.t3.micro (~$15)
- NAT Gateway: 1 instead of 2 (~$35)

---

## Launch Checklist

### Pre-Launch

- [ ] All secrets configured in AWS Secrets Manager
- [ ] SSL certificate validated in ACM
- [ ] Domain DNS configured
- [ ] Terraform infrastructure deployed
- [ ] Docker image built and pushed to ECR
- [ ] ECS service running with healthy tasks
- [ ] Database migrations applied
- [ ] Health checks passing
- [ ] Monitoring dashboards configured
- [ ] Alert channels configured (Slack, PagerDuty)
- [ ] Backup scripts tested
- [ ] Load testing completed
- [ ] Security scanning passed
- [ ] Documentation reviewed

### Post-Launch

- [ ] Monitor CloudWatch metrics for 24 hours
- [ ] Verify automated backups working
- [ ] Test disaster recovery procedures
- [ ] Review cost and set budgets/alerts
- [ ] Schedule regular maintenance windows
- [ ] Document any issues encountered
- [ ] Update runbooks with production specifics
- [ ] Train team on deployment and rollback procedures

---

## Disaster Recovery

### Recovery Time Objective (RTO): 1 hour
### Recovery Point Objective (RPO): 5 minutes

### DR Procedures

1. **Database Failure**:
   - RDS Multi-AZ automatic failover (~2 minutes)
   - Restore from snapshot if needed (~15 minutes)

2. **Region Failure**:
   - Deploy to secondary region using Terraform
   - Restore latest backup
   - Update DNS to point to new region

3. **Data Corruption**:
   - Restore from most recent good backup
   - Replay transaction logs if available

---

## Support and Resources

- **Documentation**: `/docs`
- **API Documentation**: `https://api.example.com/docs`
- **Monitoring**: `https://grafana.example.com`
- **Issue Tracking**: GitHub Issues
- **Team Slack**: `#pm-doc-intel`
- **On-call**: PagerDuty rotation

---

**Last Updated**: 2024-01-XX
**Version**: 1.0.0
