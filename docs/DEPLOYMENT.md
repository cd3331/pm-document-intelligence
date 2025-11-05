# Deployment Guide

Complete guide for deploying PM Document Intelligence to production on AWS.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Infrastructure Setup](#infrastructure-setup)
4. [Container Deployment](#container-deployment)
5. [Database Setup](#database-setup)
6. [CI/CD Pipeline](#cicd-pipeline)
7. [Monitoring & Alerts](#monitoring--alerts)
8. [Scaling Configuration](#scaling-configuration)
9. [Security Hardening](#security-hardening)
10. [Backup & Recovery](#backup--recovery)
11. [Troubleshooting](#troubleshooting)

---

## Overview

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Route 53 (DNS)                      │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│            CloudFront CDN (Static Assets)                │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│    AWS WAF (Web Application Firewall)                    │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│    Application Load Balancer (ALB)                       │
│    - SSL Termination                                     │
│    - Health Checks                                       │
└──────────┬────────────────────────┬──────────────────────┘
           │                        │
    ┌──────▼───────┐        ┌──────▼───────┐
    │  ECS Cluster │        │  ECS Cluster │
    │  (AZ1)       │        │  (AZ2)       │
    │              │        │              │
    │  API Tasks   │        │  API Tasks   │
    │  (2-10)      │        │  (2-10)      │
    └──────┬───────┘        └──────┬───────┘
           │                        │
    ┌──────▼────────────────────────▼───────┐
    │        RDS PostgreSQL (Primary)        │
    │        + Read Replicas (2)             │
    └────────────────────────────────────────┘
```

### Deployment Strategy

- **Blue-Green Deployment**: Zero-downtime updates
- **Auto-scaling**: Based on CPU, memory, and request metrics
- **Multi-AZ**: High availability across availability zones
- **Health Checks**: Automated monitoring and recovery

---

## Prerequisites

### Required AWS Services

| Service | Purpose | Estimated Cost |
|---------|---------|----------------|
| ECS Fargate | Container orchestration | $200-800/mo |
| RDS PostgreSQL | Database | $150-600/mo |
| ElastiCache Redis | Caching | $50-200/mo |
| S3 | Document storage | $20-100/mo |
| CloudFront | CDN | $10-50/mo |
| ALB | Load balancing | $20-40/mo |
| Route 53 | DNS | $1/mo |
| CloudWatch | Monitoring | $20-50/mo |
| Secrets Manager | Secret storage | $5-15/mo |

**Total**: $476-1,855/month (excluding AI API costs)

### Required Tools

```bash
# Install AWS CLI
brew install awscli  # macOS
# OR
pip install awscli

# Configure AWS credentials
aws configure

# Install Terraform (optional)
brew install terraform

# Install Docker
brew install docker
```

### IAM Permissions Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:*",
        "ec2:*",
        "rds:*",
        "elasticache:*",
        "s3:*",
        "cloudfront:*",
        "route53:*",
        "logs:*",
        "secretsmanager:*",
        "iam:PassRole"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Infrastructure Setup

### Option 1: Terraform (Recommended)

**Directory Structure**:
```
terraform/
├── main.tf
├── variables.tf
├── outputs.tf
├── vpc.tf
├── ecs.tf
├── rds.tf
├── redis.tf
├── s3.tf
└── alb.tf
```

**terraform/main.tf**:
```hcl
terraform {
  required_version = ">= 1.0"

  backend "s3" {
    bucket = "pm-doc-intel-terraform-state"
    key    = "production/terraform.tfstate"
    region = "us-east-1"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "PM Document Intelligence"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
```

**terraform/variables.tf**:
```hcl
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.r5.xlarge"
}

variable "ecs_task_cpu" {
  description = "ECS task CPU units"
  type        = number
  default     = 1024
}

variable "ecs_task_memory" {
  description = "ECS task memory (MB)"
  type        = number
  default     = 2048
}
```

**terraform/vpc.tf**:
```hcl
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.environment}-vpc"
  }
}

# Public subnets
resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  map_public_ip_on_launch = true

  tags = {
    Name = "${var.environment}-public-${count.index + 1}"
  }
}

# Private subnets
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.environment}-private-${count.index + 1}"
  }
}

# NAT Gateway
resource "aws_eip" "nat" {
  count  = 2
  domain = "vpc"
}

resource "aws_nat_gateway" "main" {
  count         = 2
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name = "${var.environment}-nat-${count.index + 1}"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.environment}-igw"
  }
}
```

**Deploy with Terraform**:
```bash
cd terraform/

# Initialize Terraform
terraform init

# Review plan
terraform plan -out=tfplan

# Apply infrastructure
terraform apply tfplan

# Get outputs
terraform output
```

### Option 2: AWS Console

See [AWS Console Deployment Guide](DEPLOYMENT_AWS_CONSOLE.md) for manual setup.

---

## Container Deployment

### 1. Build Docker Images

**Dockerfile (Production)**:
```dockerfile
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production image
FROM python:3.11-slim

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY backend/ backend/
COPY ml/ ml/
COPY frontend/ frontend/

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run application
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 2. Build and Push to ECR

```bash
# Set variables
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO=pm-doc-intel
IMAGE_TAG=$(git rev-parse --short HEAD)

# Create ECR repository (first time only)
aws ecr create-repository \
    --repository-name $ECR_REPO \
    --region $AWS_REGION

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build image
docker build -t $ECR_REPO:$IMAGE_TAG .
docker tag $ECR_REPO:$IMAGE_TAG \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG

# Push to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG

# Tag as latest
docker tag $ECR_REPO:$IMAGE_TAG \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest
```

### 3. Create ECS Task Definition

**task-definition.json**:
```json
{
  "family": "pm-doc-intel-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/pm-doc-intel:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENV",
          "value": "production"
        },
        {
          "name": "AWS_REGION",
          "value": "us-east-1"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:db-url"
        },
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:openai-key"
        },
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:app-secret"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/pm-doc-intel-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

**Register Task Definition**:
```bash
aws ecs register-task-definition \
    --cli-input-json file://task-definition.json
```

### 4. Create ECS Service

```bash
aws ecs create-service \
    --cluster production \
    --service-name pm-doc-intel-api \
    --task-definition pm-doc-intel-api:1 \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={
        subnets=[subnet-xxx,subnet-yyy],
        securityGroups=[sg-xxx],
        assignPublicIp=DISABLED
    }" \
    --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=api,containerPort=8000" \
    --health-check-grace-period-seconds 60 \
    --deployment-configuration "maximumPercent=200,minimumHealthyPercent=100"
```

---

## Database Setup

### 1. Create RDS PostgreSQL

**Via AWS CLI**:
```bash
aws rds create-db-instance \
    --db-instance-identifier pm-doc-intel-prod \
    --db-instance-class db.r5.xlarge \
    --engine postgres \
    --engine-version 15.4 \
    --master-username pmadmin \
    --master-user-password 'SECURE_PASSWORD' \
    --allocated-storage 100 \
    --storage-type gp3 \
    --storage-encrypted \
    --vpc-security-group-ids sg-xxx \
    --db-subnet-group-name production-db-subnet \
    --backup-retention-period 7 \
    --preferred-backup-window "03:00-04:00" \
    --preferred-maintenance-window "mon:04:00-mon:05:00" \
    --multi-az \
    --publicly-accessible false \
    --enable-cloudwatch-logs-exports '["postgresql"]' \
    --deletion-protection
```

### 2. Install pgvector Extension

```bash
# Connect to RDS
psql -h pm-doc-intel-prod.xxx.us-east-1.rds.amazonaws.com \
     -U pmadmin -d postgres

# Create database
CREATE DATABASE pm_doc_intel;

# Connect to database
\c pm_doc_intel

# Install pgvector
CREATE EXTENSION vector;

# Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';

# Exit
\q
```

### 3. Run Migrations

```bash
# Set DATABASE_URL environment variable
export DATABASE_URL="postgresql://pmadmin:PASSWORD@HOST:5432/pm_doc_intel"

# Run migrations
alembic upgrade head

# Verify
alembic current
```

### 4. Create Read Replicas

```bash
aws rds create-db-instance-read-replica \
    --db-instance-identifier pm-doc-intel-replica-1 \
    --source-db-instance-identifier pm-doc-intel-prod \
    --db-instance-class db.r5.large \
    --availability-zone us-east-1b \
    --publicly-accessible false

aws rds create-db-instance-read-replica \
    --db-instance-identifier pm-doc-intel-replica-2 \
    --source-db-instance-identifier pm-doc-intel-prod \
    --db-instance-class db.r5.large \
    --availability-zone us-east-1c \
    --publicly-accessible false
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

**.github/workflows/deploy.yml**:
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: pm-doc-intel
  ECS_CLUSTER: production
  ECS_SERVICE: pm-doc-intel-api

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests
        run: pytest --cov=backend --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  build-and-push:
    needs: [test, security-scan]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1

      - name: Build, tag, and push image to Amazon ECR
        id: build-image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG \
            $ECR_REGISTRY/$ECR_REPOSITORY:latest
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
          echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT

      - name: Scan image with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ steps.build-image.outputs.image }}
          format: 'sarif'
          output: 'trivy-image-results.sarif'

  deploy-staging:
    needs: build-and-push
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Deploy to ECS Staging
        run: |
          aws ecs update-service \
            --cluster staging \
            --service pm-doc-intel-api \
            --force-new-deployment \
            --desired-count 1

      - name: Wait for staging deployment
        run: |
          aws ecs wait services-stable \
            --cluster staging \
            --services pm-doc-intel-api

      - name: Run smoke tests
        run: |
          curl -f https://staging-api.pmdocintel.com/health || exit 1

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Deploy to ECS Production (Blue-Green)
        run: |
          # Create new task definition revision
          TASK_DEF=$(aws ecs describe-task-definition \
            --task-definition pm-doc-intel-api \
            --query 'taskDefinition' --output json)

          NEW_TASK_DEF=$(echo $TASK_DEF | jq --arg IMAGE "${{ needs.build-and-push.outputs.image }}" \
            '.containerDefinitions[0].image = $IMAGE | del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy)')

          NEW_TASK_INFO=$(aws ecs register-task-definition \
            --cli-input-json "$NEW_TASK_DEF")

          NEW_REVISION=$(echo $NEW_TASK_INFO | jq -r '.taskDefinition.revision')

          # Update service
          aws ecs update-service \
            --cluster ${{ env.ECS_CLUSTER }} \
            --service ${{ env.ECS_SERVICE }} \
            --task-definition pm-doc-intel-api:$NEW_REVISION \
            --desired-count 3 \
            --deployment-configuration "maximumPercent=200,minimumHealthyPercent=100"

      - name: Wait for production deployment
        run: |
          aws ecs wait services-stable \
            --cluster ${{ env.ECS_CLUSTER }} \
            --services ${{ env.ECS_SERVICE }}

      - name: Run production smoke tests
        run: |
          curl -f https://api.pmdocintel.com/health || exit 1

      - name: Notify Slack
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Production deployment ${{ job.status }}'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## Monitoring & Alerts

### CloudWatch Alarms

**CPU Utilization**:
```bash
aws cloudwatch put-metric-alarm \
    --alarm-name pm-doc-intel-high-cpu \
    --alarm-description "Alert when CPU exceeds 80%" \
    --metric-name CPUUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2 \
    --dimensions Name=ServiceName,Value=pm-doc-intel-api \
                 Name=ClusterName,Value=production \
    --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:alerts
```

**Memory Utilization**:
```bash
aws cloudwatch put-metric-alarm \
    --alarm-name pm-doc-intel-high-memory \
    --alarm-description "Alert when memory exceeds 85%" \
    --metric-name MemoryUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 85 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2 \
    --dimensions Name=ServiceName,Value=pm-doc-intel-api \
                 Name=ClusterName,Value=production \
    --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:alerts
```

**Error Rate**:
```bash
aws cloudwatch put-metric-alarm \
    --alarm-name pm-doc-intel-high-error-rate \
    --alarm-description "Alert when error rate exceeds 5%" \
    --metric-name 5XXError \
    --namespace AWS/ApplicationELB \
    --statistic Average \
    --period 300 \
    --threshold 5 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 1 \
    --dimensions Name=LoadBalancer,Value=app/pm-doc-intel-alb/xxx \
    --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:alerts
```

### Log Aggregation

**CloudWatch Logs Insights Queries**:

```sql
-- Top 10 slowest endpoints
fields @timestamp, request.path, request.duration_ms
| filter request.duration_ms > 1000
| sort request.duration_ms desc
| limit 10

-- Error rate over time
fields @timestamp
| filter @message like /ERROR/
| stats count() as error_count by bin(5m)

-- Top users by document uploads
fields user_id, document_id
| filter event_type = "document_upload"
| stats count() as upload_count by user_id
| sort upload_count desc
| limit 20
```

### Sentry Error Tracking

**Setup Sentry** (Configured in v1.0.1+):

1. Create Sentry project at https://sentry.io
2. Add DSN to environment variables:
```bash
SENTRY_DSN=https://your-key@sentry.io/project-id
SENTRY_ENABLED=true
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% of transactions
```

3. Deploy with environment variables:
```bash
# Via ECS task definition
{
  "name": "SENTRY_DSN",
  "value": "https://your-key@sentry.io/project-id"
},
{
  "name": "SENTRY_ENABLED",
  "value": "true"
}
```

**Features**:
- Automatic error capture and stack traces
- Performance monitoring with distributed tracing
- Release tracking for deployments
- User context and breadcrumbs
- Alert integration with Slack/email

**View Errors**:
- Dashboard: https://sentry.io/organizations/your-org/issues/
- Set up alerts for critical errors
- Configure issue assignment rules

---

## Scaling Configuration

### Auto Scaling Policy

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --resource-id service/production/pm-doc-intel-api \
    --scalable-dimension ecs:service:DesiredCount \
    --min-capacity 2 \
    --max-capacity 20

# CPU-based scaling
aws application-autoscaling put-scaling-policy \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/production/pm-doc-intel-api \
    --policy-name cpu-scaling \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration '{
        "TargetValue": 70.0,
        "PredefinedMetricSpecification": {
            "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
        },
        "ScaleInCooldown": 300,
        "ScaleOutCooldown": 60
    }'

# Memory-based scaling
aws application-autoscaling put-scaling-policy \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/production/pm-doc-intel-api \
    --policy-name memory-scaling \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration '{
        "TargetValue": 80.0,
        "PredefinedMetricSpecification": {
            "PredefinedMetricType": "ECSServiceAverageMemoryUtilization"
        },
        "ScaleInCooldown": 300,
        "ScaleOutCooldown": 60
    }'
```

---

## Security Hardening

### 1. Enable AWS WAF

```bash
# Create WAF WebACL
aws wafv2 create-web-acl \
    --name pm-doc-intel-waf \
    --scope REGIONAL \
    --default-action Allow={} \
    --rules file://waf-rules.json \
    --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=pm-doc-intel-waf

# Associate with ALB
aws wafv2 associate-web-acl \
    --web-acl-arn arn:aws:wafv2:... \
    --resource-arn arn:aws:elasticloadbalancing:...
```

### 2. Enable GuardDuty

```bash
aws guardduty create-detector \
    --enable \
    --finding-publishing-frequency FIFTEEN_MINUTES
```

### 3. Enable Security Hub

```bash
aws securityhub enable-security-hub
aws securityhub batch-enable-standards \
    --standards-subscription-requests StandardsArn=arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0
```

---

## Backup & Recovery

### RDS Automated Backups

```bash
# Configure automated backups
aws rds modify-db-instance \
    --db-instance-identifier pm-doc-intel-prod \
    --backup-retention-period 7 \
    --preferred-backup-window "03:00-04:00"

# Create manual snapshot
aws rds create-db-snapshot \
    --db-instance-identifier pm-doc-intel-prod \
    --db-snapshot-identifier pm-doc-intel-prod-$(date +%Y%m%d)
```

### S3 Versioning & Lifecycle

```bash
# Enable versioning
aws s3api put-bucket-versioning \
    --bucket pm-doc-intel-documents \
    --versioning-configuration Status=Enabled

# Lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
    --bucket pm-doc-intel-documents \
    --lifecycle-configuration file://lifecycle.json
```

**lifecycle.json**:
```json
{
  "Rules": [
    {
      "Id": "Archive old documents",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 365,
          "StorageClass": "GLACIER"
        }
      ]
    }
  ]
}
```

### Disaster Recovery Plan

**RTO (Recovery Time Objective)**: 4 hours
**RPO (Recovery Point Objective)**: 1 hour

**Recovery Steps**:
1. Restore RDS from snapshot (2 hours)
2. Update ECS service with healthy tasks (30 minutes)
3. Verify data integrity (1 hour)
4. Route traffic to recovered infrastructure (30 minutes)

---

## Troubleshooting

### Common Issues

#### ECS Tasks Failing

```bash
# View task logs
aws logs tail /ecs/pm-doc-intel-api --follow

# Describe stopped tasks
aws ecs describe-tasks \
    --cluster production \
    --tasks $(aws ecs list-tasks --cluster production --desired-status STOPPED | jq -r '.taskArns[0]')
```

#### Database Connection Issues

```bash
# Test connectivity
psql -h pm-doc-intel-prod.xxx.rds.amazonaws.com -U pmadmin -d pm_doc_intel

# Check security groups
aws ec2 describe-security-groups --group-ids sg-xxx

# Check connection pooling
SELECT count(*) FROM pg_stat_activity;
```

#### High Latency

```bash
# Check ALB metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/ApplicationELB \
    --metric-name TargetResponseTime \
    --dimensions Name=LoadBalancer,Value=app/pm-doc-intel-alb/xxx \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Average

# Check ECS service health
aws ecs describe-services \
    --cluster production \
    --services pm-doc-intel-api
```

---

## Post-Deployment Checklist

- [ ] Verify all ECS tasks are running
- [ ] Check ALB health checks passing
- [ ] Confirm database connectivity
- [ ] Test API endpoints
- [ ] Verify CloudWatch logs
- [ ] Check monitoring dashboards
- [ ] Test auto-scaling behavior
- [ ] Verify backup schedules
- [ ] Review security group rules
- [ ] Test disaster recovery plan
- [ ] Update documentation
- [ ] Notify stakeholders

---

## Additional Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS RDS PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [GitHub Actions for AWS](https://github.com/aws-actions)

---

**Last Updated**: January 2024
**Maintained By**: DevOps Team
