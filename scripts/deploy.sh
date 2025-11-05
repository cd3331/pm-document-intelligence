#!/bin/bash

# ============================================
# PM Document Intelligence - Deployment Script
# ============================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPOSITORY="${ECR_REPOSITORY:-pm-document-intelligence}"
ECS_CLUSTER="${ECS_CLUSTER:-pm-doc-intel-cluster}"
ECS_SERVICE="${ECS_SERVICE:-pm-doc-intel-backend-service}"
CONTAINER_NAME="${CONTAINER_NAME:-backend}"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy PM Document Intelligence to AWS ECS

OPTIONS:
    -e, --environment ENV    Environment to deploy (development|staging|production)
    -t, --tag TAG           Docker image tag (default: latest)
    -r, --region REGION     AWS region (default: us-east-1)
    -s, --skip-tests        Skip running tests before deployment
    -f, --force             Force deployment without confirmation
    -h, --help              Show this help message

EXAMPLES:
    $0 --environment staging
    $0 --environment production --tag v1.2.3
    $0 -e development -s -f

EOF
    exit 1
}

# Parse arguments
ENVIRONMENT=""
IMAGE_TAG="latest"
SKIP_TESTS=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -s|--skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required arguments
if [ -z "$ENVIRONMENT" ]; then
    log_error "Environment is required"
    usage
fi

if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT"
    usage
fi

# Confirmation for production
if [ "$ENVIRONMENT" == "production" ] && [ "$FORCE" != true ]; then
    log_warn "You are about to deploy to PRODUCTION!"
    read -p "Are you sure you want to continue? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_info "Deployment cancelled"
        exit 0
    fi
fi

log_info "Starting deployment to $ENVIRONMENT"
log_info "AWS Region: $AWS_REGION"
log_info "Image Tag: $IMAGE_TAG"

# ==========================================
# Step 1: Pre-deployment checks
# ==========================================
log_info "Running pre-deployment checks..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed"
    exit 1
fi

# Verify AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials are not configured"
    exit 1
fi

log_info "Pre-deployment checks passed ✓"

# ==========================================
# Step 2: Run tests (optional)
# ==========================================
if [ "$SKIP_TESTS" != true ]; then
    log_info "Running tests..."
    cd "$(dirname "$0")/../backend"

    if [ -f "requirements.txt" ]; then
        python -m pytest tests/ -v || {
            log_error "Tests failed"
            exit 1
        }
        log_info "Tests passed ✓"
    else
        log_warn "No requirements.txt found, skipping tests"
    fi

    cd - > /dev/null
else
    log_warn "Skipping tests as requested"
fi

# ==========================================
# Step 3: Build Docker image
# ==========================================
log_info "Building Docker image..."

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Build image
FULL_IMAGE_TAG="${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"
FULL_ENV_TAG="${ECR_REGISTRY}/${ECR_REPOSITORY}:${ENVIRONMENT}-latest"

log_info "Building image: $FULL_IMAGE_TAG"

docker build \
    --target production \
    --tag "$FULL_IMAGE_TAG" \
    --tag "$FULL_ENV_TAG" \
    --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    --build-arg VCS_REF="$(git rev-parse --short HEAD)" \
    --build-arg VERSION="$IMAGE_TAG" \
    . || {
    log_error "Docker build failed"
    exit 1
}

log_info "Docker image built successfully ✓"

# ==========================================
# Step 4: Push to ECR
# ==========================================
log_info "Pushing image to ECR..."

# Login to ECR
aws ecr get-login-password --region "$AWS_REGION" | \
    docker login --username AWS --password-stdin "$ECR_REGISTRY" || {
    log_error "ECR login failed"
    exit 1
}

# Push images
docker push "$FULL_IMAGE_TAG" || {
    log_error "Failed to push image with tag: $IMAGE_TAG"
    exit 1
}

docker push "$FULL_ENV_TAG" || {
    log_error "Failed to push image with environment tag"
    exit 1
}

log_info "Image pushed to ECR successfully ✓"

# ==========================================
# Step 5: Update ECS service
# ==========================================
log_info "Updating ECS service..."

# Get current task definition
TASK_DEFINITION=$(aws ecs describe-services \
    --cluster "${ECS_CLUSTER}-${ENVIRONMENT}" \
    --services "${ECS_SERVICE}-${ENVIRONMENT}" \
    --region "$AWS_REGION" \
    --query 'services[0].taskDefinition' \
    --output text)

log_info "Current task definition: $TASK_DEFINITION"

# Force new deployment
aws ecs update-service \
    --cluster "${ECS_CLUSTER}-${ENVIRONMENT}" \
    --service "${ECS_SERVICE}-${ENVIRONMENT}" \
    --force-new-deployment \
    --region "$AWS_REGION" \
    --output json > /dev/null || {
    log_error "Failed to update ECS service"
    exit 1
}

log_info "ECS service update initiated ✓"

# ==========================================
# Step 6: Wait for deployment
# ==========================================
log_info "Waiting for deployment to stabilize (this may take a few minutes)..."

TIMEOUT=600
ELAPSED=0
INTERVAL=10

while [ $ELAPSED -lt $TIMEOUT ]; do
    # Check deployment status
    DEPLOYMENT_STATUS=$(aws ecs describe-services \
        --cluster "${ECS_CLUSTER}-${ENVIRONMENT}" \
        --services "${ECS_SERVICE}-${ENVIRONMENT}" \
        --region "$AWS_REGION" \
        --query 'services[0].deployments[0].rolloutState' \
        --output text)

    RUNNING_COUNT=$(aws ecs describe-services \
        --cluster "${ECS_CLUSTER}-${ENVIRONMENT}" \
        --services "${ECS_SERVICE}-${ENVIRONMENT}" \
        --region "$AWS_REGION" \
        --query 'services[0].runningCount' \
        --output text)

    DESIRED_COUNT=$(aws ecs describe-services \
        --cluster "${ECS_CLUSTER}-${ENVIRONMENT}" \
        --services "${ECS_SERVICE}-${ENVIRONMENT}" \
        --region "$AWS_REGION" \
        --query 'services[0].desiredCount' \
        --output text)

    log_info "Status: $DEPLOYMENT_STATUS | Running: $RUNNING_COUNT/$DESIRED_COUNT"

    if [ "$DEPLOYMENT_STATUS" == "COMPLETED" ] && [ "$RUNNING_COUNT" == "$DESIRED_COUNT" ]; then
        log_info "Deployment completed successfully ✓"
        break
    fi

    if [ "$DEPLOYMENT_STATUS" == "FAILED" ]; then
        log_error "Deployment failed"

        # Rollback
        log_warn "Rolling back to previous task definition..."
        aws ecs update-service \
            --cluster "${ECS_CLUSTER}-${ENVIRONMENT}" \
            --service "${ECS_SERVICE}-${ENVIRONMENT}" \
            --task-definition "$TASK_DEFINITION" \
            --force-new-deployment \
            --region "$AWS_REGION" > /dev/null

        exit 1
    fi

    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    log_error "Deployment timed out after ${TIMEOUT} seconds"
    exit 1
fi

# ==========================================
# Step 7: Run smoke tests
# ==========================================
log_info "Running smoke tests..."

# Get load balancer URL
ALB_DNS=$(aws elbv2 describe-load-balancers \
    --region "$AWS_REGION" \
    --query "LoadBalancers[?contains(LoadBalancerName, 'pm-doc-intel')].DNSName" \
    --output text | head -n 1)

if [ -n "$ALB_DNS" ]; then
    API_ENDPOINT="https://${ALB_DNS}"
else
    log_warn "Could not find load balancer, skipping smoke tests"
    API_ENDPOINT=""
fi

if [ -n "$API_ENDPOINT" ]; then
    # Health check
    if curl -f -s "$API_ENDPOINT/health/live" > /dev/null; then
        log_info "Liveness check passed ✓"
    else
        log_error "Liveness check failed"
        exit 1
    fi

    if curl -f -s "$API_ENDPOINT/health/ready" > /dev/null; then
        log_info "Readiness check passed ✓"
    else
        log_error "Readiness check failed"
        exit 1
    fi

    log_info "Smoke tests passed ✓"
fi

# ==========================================
# Deployment Summary
# ==========================================
echo ""
echo "==========================================="
echo "Deployment Summary"
echo "==========================================="
echo "Environment:     $ENVIRONMENT"
echo "AWS Region:      $AWS_REGION"
echo "Image Tag:       $IMAGE_TAG"
echo "ECS Cluster:     ${ECS_CLUSTER}-${ENVIRONMENT}"
echo "ECS Service:     ${ECS_SERVICE}-${ENVIRONMENT}"
if [ -n "$API_ENDPOINT" ]; then
    echo "API Endpoint:    $API_ENDPOINT"
fi
echo "Status:          SUCCESS"
echo "==========================================="
echo ""

log_info "Deployment completed successfully! 🎉"

exit 0
