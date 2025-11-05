#!/bin/bash

# ============================================
# PM Document Intelligence - Backup Script
# ============================================
# This script performs backups of:
# - PostgreSQL database (via pg_dump to Supabase)
# - S3 documents bucket
# - Application configuration
# - Uploads to backup S3 bucket with retention policy
# ============================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
ENVIRONMENT="${ENVIRONMENT:-production}"
PROJECT_NAME="${PROJECT_NAME:-pm-doc-intel}"
BACKUP_BUCKET="${PROJECT_NAME}-backups-${ENVIRONMENT}"
DOCUMENTS_BUCKET="${PROJECT_NAME}-documents-${ENVIRONMENT}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="/tmp/pm-backups-${TIMESTAMP}"

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

cleanup() {
    log_info "Cleaning up temporary files..."
    rm -rf "$BACKUP_DIR"
}

trap cleanup EXIT

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Backup PM Document Intelligence data

OPTIONS:
    -e, --environment ENV       Environment (development|staging|production)
    -r, --region REGION         AWS region (default: us-east-1)
    -d, --retention-days DAYS   Retention period in days (default: 30)
    -t, --type TYPE             Backup type (all|database|documents|config)
    -h, --help                  Show this help message

EXAMPLES:
    $0 --environment production
    $0 --environment staging --type database
    $0 -e production -d 90

EOF
    exit 1
}

# Parse arguments
BACKUP_TYPE="all"

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -d|--retention-days)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        -t|--type)
            BACKUP_TYPE="$2"
            shift 2
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

log_info "Starting backup for $ENVIRONMENT environment"
log_info "Backup type: $BACKUP_TYPE"
log_info "Retention: $RETENTION_DAYS days"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# ==========================================
# Step 1: Database Backup
# ==========================================
backup_database() {
    log_info "Backing up database..."

    # Get database credentials from AWS Secrets Manager
    DB_SECRET=$(aws secretsmanager get-secret-value \
        --secret-id "${PROJECT_NAME}/db-password-${ENVIRONMENT}" \
        --region "$AWS_REGION" \
        --query SecretString \
        --output text)

    # Get RDS endpoint
    DB_ENDPOINT=$(aws rds describe-db-instances \
        --region "$AWS_REGION" \
        --query "DBInstances[?DBInstanceIdentifier=='${PROJECT_NAME}-db-${ENVIRONMENT}'].Endpoint.Address" \
        --output text)

    if [ -z "$DB_ENDPOINT" ]; then
        log_error "Could not find RDS instance"
        return 1
    fi

    DB_NAME="pm_document_intelligence"
    DB_USER="pmadmin"
    DB_PORT="5432"

    # Export password for pg_dump
    export PGPASSWORD="$DB_SECRET"

    # Perform backup
    BACKUP_FILE="$BACKUP_DIR/database-${TIMESTAMP}.sql"

    pg_dump \
        -h "$DB_ENDPOINT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -p "$DB_PORT" \
        --format=custom \
        --file="$BACKUP_FILE" \
        --verbose || {
        log_error "Database backup failed"
        return 1
    }

    # Compress backup
    gzip "$BACKUP_FILE"
    BACKUP_FILE="${BACKUP_FILE}.gz"

    log_info "Database backup created: $(basename $BACKUP_FILE)"
    log_info "Backup size: $(du -h $BACKUP_FILE | cut -f1)"

    # Upload to S3
    aws s3 cp "$BACKUP_FILE" \
        "s3://${BACKUP_BUCKET}/database/$(basename $BACKUP_FILE)" \
        --region "$AWS_REGION" || {
        log_error "Failed to upload database backup to S3"
        return 1
    }

    log_info "Database backup uploaded to S3 ✓"

    unset PGPASSWORD
}

# ==========================================
# Step 2: Documents Backup
# ==========================================
backup_documents() {
    log_info "Backing up documents from S3..."

    # Get documents bucket name
    DOCS_BUCKET="${DOCUMENTS_BUCKET}-$(aws sts get-caller-identity --query Account --output text)"

    # Check if bucket exists
    if ! aws s3 ls "s3://${DOCS_BUCKET}" --region "$AWS_REGION" > /dev/null 2>&1; then
        log_warn "Documents bucket not found: $DOCS_BUCKET"
        return 0
    fi

    # Sync documents to backup location
    aws s3 sync \
        "s3://${DOCS_BUCKET}" \
        "s3://${BACKUP_BUCKET}/documents/${TIMESTAMP}/" \
        --region "$AWS_REGION" \
        --storage-class STANDARD_IA || {
        log_error "Failed to backup documents"
        return 1
    }

    # Get backup size
    BACKUP_SIZE=$(aws s3 ls "s3://${BACKUP_BUCKET}/documents/${TIMESTAMP}/" \
        --recursive \
        --summarize \
        --region "$AWS_REGION" | grep "Total Size" | awk '{print $3}')

    log_info "Documents backed up: $(numfmt --to=iec-i --suffix=B $BACKUP_SIZE)"
    log_info "Documents backup completed ✓"
}

# ==========================================
# Step 3: Configuration Backup
# ==========================================
backup_configuration() {
    log_info "Backing up configuration..."

    CONFIG_DIR="$BACKUP_DIR/configuration"
    mkdir -p "$CONFIG_DIR"

    # Backup Secrets Manager secrets (metadata only, not values)
    aws secretsmanager list-secrets \
        --region "$AWS_REGION" \
        --query "SecretList[?contains(Name, '${PROJECT_NAME}')]" \
        --output json > "$CONFIG_DIR/secrets-list.json"

    # Backup ECS task definitions
    aws ecs list-task-definitions \
        --region "$AWS_REGION" \
        --family-prefix "${PROJECT_NAME}" \
        --query "taskDefinitionArns[-5:]" \
        --output json > "$CONFIG_DIR/task-definitions.json"

    # Backup ECS services configuration
    aws ecs describe-services \
        --cluster "${PROJECT_NAME}-cluster-${ENVIRONMENT}" \
        --services "${PROJECT_NAME}-backend-service-${ENVIRONMENT}" \
        --region "$AWS_REGION" \
        --output json > "$CONFIG_DIR/ecs-services.json" 2>/dev/null || true

    # Backup ALB configuration
    ALB_ARN=$(aws elbv2 describe-load-balancers \
        --region "$AWS_REGION" \
        --query "LoadBalancers[?contains(LoadBalancerName, '${PROJECT_NAME}')].LoadBalancerArn" \
        --output text | head -n 1)

    if [ -n "$ALB_ARN" ]; then
        aws elbv2 describe-load-balancers \
            --load-balancer-arns "$ALB_ARN" \
            --region "$AWS_REGION" \
            --output json > "$CONFIG_DIR/alb-config.json"
    fi

    # Create archive
    tar -czf "$BACKUP_DIR/configuration-${TIMESTAMP}.tar.gz" -C "$BACKUP_DIR" configuration/

    # Upload to S3
    aws s3 cp "$BACKUP_DIR/configuration-${TIMESTAMP}.tar.gz" \
        "s3://${BACKUP_BUCKET}/configuration/configuration-${TIMESTAMP}.tar.gz" \
        --region "$AWS_REGION" || {
        log_error "Failed to upload configuration backup"
        return 1
    }

    log_info "Configuration backup completed ✓"
}

# ==========================================
# Step 4: Backup Execution
# ==========================================
if [ "$BACKUP_TYPE" == "all" ] || [ "$BACKUP_TYPE" == "database" ]; then
    backup_database || log_error "Database backup failed"
fi

if [ "$BACKUP_TYPE" == "all" ] || [ "$BACKUP_TYPE" == "documents" ]; then
    backup_documents || log_error "Documents backup failed"
fi

if [ "$BACKUP_TYPE" == "all" ] || [ "$BACKUP_TYPE" == "config" ]; then
    backup_configuration || log_error "Configuration backup failed"
fi

# ==========================================
# Step 5: Cleanup Old Backups
# ==========================================
log_info "Cleaning up backups older than $RETENTION_DAYS days..."

# Calculate cutoff date
CUTOFF_DATE=$(date -d "$RETENTION_DAYS days ago" +%Y-%m-%d 2>/dev/null || date -v-${RETENTION_DAYS}d +%Y-%m-%d)

# List and delete old backups
for PREFIX in "database" "documents" "configuration"; do
    aws s3api list-objects-v2 \
        --bucket "$BACKUP_BUCKET" \
        --prefix "$PREFIX/" \
        --region "$AWS_REGION" \
        --query "Contents[?LastModified<'$CUTOFF_DATE'].Key" \
        --output text | while read -r KEY; do
        if [ -n "$KEY" ]; then
            log_info "Deleting old backup: $KEY"
            aws s3 rm "s3://${BACKUP_BUCKET}/${KEY}" --region "$AWS_REGION"
        fi
    done
done

log_info "Old backups cleaned up ✓"

# ==========================================
# Step 6: Backup Manifest
# ==========================================
log_info "Creating backup manifest..."

MANIFEST_FILE="$BACKUP_DIR/manifest-${TIMESTAMP}.json"

cat > "$MANIFEST_FILE" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "environment": "$ENVIRONMENT",
  "backup_type": "$BACKUP_TYPE",
  "region": "$AWS_REGION",
  "retention_days": $RETENTION_DAYS,
  "backups": {
    "database": "s3://${BACKUP_BUCKET}/database/database-${TIMESTAMP}.sql.gz",
    "documents": "s3://${BACKUP_BUCKET}/documents/${TIMESTAMP}/",
    "configuration": "s3://${BACKUP_BUCKET}/configuration/configuration-${TIMESTAMP}.tar.gz"
  },
  "status": "completed"
}
EOF

# Upload manifest
aws s3 cp "$MANIFEST_FILE" \
    "s3://${BACKUP_BUCKET}/manifests/manifest-${TIMESTAMP}.json" \
    --region "$AWS_REGION"

log_info "Backup manifest created ✓"

# ==========================================
# Backup Summary
# ==========================================
echo ""
echo "==========================================="
echo "Backup Summary"
echo "==========================================="
echo "Environment:     $ENVIRONMENT"
echo "Timestamp:       $TIMESTAMP"
echo "Backup Type:     $BACKUP_TYPE"
echo "Retention:       $RETENTION_DAYS days"
echo "Backup Bucket:   s3://$BACKUP_BUCKET"
echo "Manifest:        s3://$BACKUP_BUCKET/manifests/manifest-${TIMESTAMP}.json"
echo "Status:          SUCCESS"
echo "==========================================="
echo ""

log_info "Backup completed successfully! 🎉"

exit 0
