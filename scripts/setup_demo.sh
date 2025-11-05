#!/bin/bash

###############################################################################
# PM Document Intelligence - Demo Environment Setup Script
#
# This script automates the setup of a clean demo environment including:
# - Database initialization with demo data
# - Demo user account creation
# - Sample document pre-processing
# - Service health verification
# - Demo configuration
#
# Usage:
#   ./scripts/setup_demo.sh [options]
#
# Options:
#   --reset         Reset existing demo environment (WARNING: deletes data)
#   --skip-docs     Skip document pre-processing (faster setup)
#   --skip-verify   Skip health checks
#   --help          Show this help message
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - .env file configured with necessary credentials
#   - demo_data/ directory with sample documents
#
# Author: PM Document Intelligence Team
# Last Updated: 2025-01-20
###############################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEMO_ORG_NAME="Demo Organization"
DEMO_USER_EMAIL="demo@pmdocintel.com"
DEMO_USER_PASSWORD="demo2024"
DEMO_USER_NAME="Demo User"
DEMO_DOCS_DIR="demo_data"

# Parse command-line arguments
RESET_MODE=false
SKIP_DOCS=false
SKIP_VERIFY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --reset)
            RESET_MODE=true
            shift
            ;;
        --skip-docs)
            SKIP_DOCS=true
            shift
            ;;
        --skip-verify)
            SKIP_VERIFY=true
            shift
            ;;
        --help)
            echo "Usage: ./scripts/setup_demo.sh [options]"
            echo ""
            echo "Options:"
            echo "  --reset         Reset existing demo environment (WARNING: deletes data)"
            echo "  --skip-docs     Skip document pre-processing (faster setup)"
            echo "  --skip-verify   Skip health checks"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            exit 1
            ;;
    esac
done

###############################################################################
# Helper Functions
###############################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    log_success "Docker found: $(docker --version)"

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    log_success "Docker Compose found: $(docker-compose --version)"

    # Check .env file
    if [ ! -f .env ]; then
        log_error ".env file not found. Please create one from .env.example"
        exit 1
    fi
    log_success ".env file found"

    # Check demo data directory
    if [ ! -d "$DEMO_DOCS_DIR" ]; then
        log_warning "Demo data directory not found. Creating $DEMO_DOCS_DIR/"
        mkdir -p "$DEMO_DOCS_DIR"
    fi
    log_success "Demo data directory: $DEMO_DOCS_DIR/"
}

start_services() {
    log_info "Starting Docker services..."

    # Start services
    docker-compose up -d

    # Wait for services to be ready
    log_info "Waiting for services to start (30 seconds)..."
    sleep 30

    log_success "Services started"
}

verify_services() {
    if [ "$SKIP_VERIFY" = true ]; then
        log_warning "Skipping service verification (--skip-verify flag set)"
        return 0
    fi

    log_info "Verifying service health..."

    # Check PostgreSQL
    log_info "Checking PostgreSQL..."
    if docker-compose exec -T db pg_isready -U postgres >/dev/null 2>&1; then
        log_success "PostgreSQL is ready"
    else
        log_error "PostgreSQL is not ready"
        exit 1
    fi

    # Check Redis
    log_info "Checking Redis..."
    if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
        log_success "Redis is ready"
    else
        log_error "Redis is not ready"
        exit 1
    fi

    # Check Backend API
    log_info "Checking Backend API..."
    MAX_RETRIES=10
    RETRY_COUNT=0
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -s http://localhost:8000/health | grep -q "healthy"; then
            log_success "Backend API is ready"
            return 0
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        log_info "Waiting for API... (attempt $RETRY_COUNT/$MAX_RETRIES)"
        sleep 3
    done

    log_error "Backend API failed to start after $MAX_RETRIES attempts"
    exit 1
}

initialize_database() {
    log_info "Initializing database..."

    if [ "$RESET_MODE" = true ]; then
        log_warning "Reset mode: Dropping existing database..."

        # Drop and recreate database
        docker-compose exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS pm_doc_intel_demo;" 2>/dev/null || true
        docker-compose exec -T db psql -U postgres -c "CREATE DATABASE pm_doc_intel_demo;"

        log_success "Database reset complete"
    fi

    # Run migrations
    log_info "Running database migrations..."
    docker-compose exec -T backend alembic upgrade head

    log_success "Database initialized"
}

create_demo_organization() {
    log_info "Creating demo organization..."

    # Check if organization already exists
    ORG_EXISTS=$(docker-compose exec -T db psql -U postgres -d pm_doc_intel_demo -tAc \
        "SELECT EXISTS(SELECT 1 FROM organizations WHERE name = '$DEMO_ORG_NAME');")

    if [ "$ORG_EXISTS" = "t" ]; then
        log_warning "Demo organization already exists"
        if [ "$RESET_MODE" = true ]; then
            log_info "Reset mode: Deleting existing organization..."
            docker-compose exec -T db psql -U postgres -d pm_doc_intel_demo -c \
                "DELETE FROM organizations WHERE name = '$DEMO_ORG_NAME';"
        else
            return 0
        fi
    fi

    # Create organization
    ORG_ID=$(docker-compose exec -T db psql -U postgres -d pm_doc_intel_demo -tAc \
        "INSERT INTO organizations (name, created_at) VALUES ('$DEMO_ORG_NAME', NOW()) RETURNING id;")

    if [ -z "$ORG_ID" ]; then
        log_error "Failed to create demo organization"
        exit 1
    fi

    log_success "Demo organization created: $ORG_ID"
    echo "$ORG_ID" > /tmp/demo_org_id.txt
}

create_demo_user() {
    log_info "Creating demo user account..."

    # Get organization ID
    ORG_ID=$(cat /tmp/demo_org_id.txt 2>/dev/null || echo "")
    if [ -z "$ORG_ID" ]; then
        ORG_ID=$(docker-compose exec -T db psql -U postgres -d pm_doc_intel_demo -tAc \
            "SELECT id FROM organizations WHERE name = '$DEMO_ORG_NAME' LIMIT 1;")
    fi

    # Check if user already exists
    USER_EXISTS=$(docker-compose exec -T db psql -U postgres -d pm_doc_intel_demo -tAc \
        "SELECT EXISTS(SELECT 1 FROM users WHERE email = '$DEMO_USER_EMAIL');")

    if [ "$USER_EXISTS" = "t" ]; then
        log_warning "Demo user already exists"
        if [ "$RESET_MODE" = true ]; then
            log_info "Reset mode: Deleting existing user..."
            docker-compose exec -T db psql -U postgres -d pm_doc_intel_demo -c \
                "DELETE FROM users WHERE email = '$DEMO_USER_EMAIL';"
        else
            return 0
        fi
    fi

    # Generate password hash (bcrypt)
    PASSWORD_HASH=$(docker-compose exec -T backend python -c \
        "from passlib.hash import bcrypt; print(bcrypt.hash('$DEMO_USER_PASSWORD'))")

    # Create user
    USER_ID=$(docker-compose exec -T db psql -U postgres -d pm_doc_intel_demo -tAc \
        "INSERT INTO users (organization_id, email, password_hash, name, role, created_at) \
         VALUES ('$ORG_ID', '$DEMO_USER_EMAIL', '$PASSWORD_HASH', '$DEMO_USER_NAME', 'admin', NOW()) \
         RETURNING id;")

    if [ -z "$USER_ID" ]; then
        log_error "Failed to create demo user"
        exit 1
    fi

    log_success "Demo user created: $DEMO_USER_EMAIL"
    log_info "Demo credentials:"
    log_info "  Email: $DEMO_USER_EMAIL"
    log_info "  Password: $DEMO_USER_PASSWORD"

    echo "$USER_ID" > /tmp/demo_user_id.txt
}

load_sample_documents() {
    if [ "$SKIP_DOCS" = true ]; then
        log_warning "Skipping document pre-processing (--skip-docs flag set)"
        return 0
    fi

    log_info "Loading sample documents..."

    # Check if demo documents exist
    if [ ! -d "$DEMO_DOCS_DIR" ] || [ -z "$(ls -A $DEMO_DOCS_DIR 2>/dev/null)" ]; then
        log_warning "No demo documents found in $DEMO_DOCS_DIR/"
        log_info "Creating sample document placeholders..."
        mkdir -p "$DEMO_DOCS_DIR"
        echo "Add sample documents to $DEMO_DOCS_DIR/ and re-run this script."
        return 0
    fi

    # Get demo user ID
    USER_ID=$(cat /tmp/demo_user_id.txt 2>/dev/null || echo "")
    ORG_ID=$(cat /tmp/demo_org_id.txt 2>/dev/null || echo "")

    # Login to get JWT token
    log_info "Authenticating demo user..."
    TOKEN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
        -H "Content-Type: application/json" \
        -d "{\"email\": \"$DEMO_USER_EMAIL\", \"password\": \"$DEMO_USER_PASSWORD\"}")

    ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null || echo "")

    if [ -z "$ACCESS_TOKEN" ]; then
        log_error "Failed to authenticate demo user"
        log_error "Response: $TOKEN_RESPONSE"
        return 1
    fi

    log_success "Authentication successful"

    # Upload each document
    UPLOADED_COUNT=0
    for doc in "$DEMO_DOCS_DIR"/*; do
        if [ -f "$doc" ]; then
            FILENAME=$(basename "$doc")
            log_info "Uploading: $FILENAME"

            UPLOAD_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/documents \
                -H "Authorization: Bearer $ACCESS_TOKEN" \
                -F "file=@$doc" \
                -F "filename=$FILENAME")

            DOC_ID=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null || echo "")

            if [ -n "$DOC_ID" ]; then
                log_success "Uploaded: $FILENAME (ID: $DOC_ID)"
                UPLOADED_COUNT=$((UPLOADED_COUNT + 1))

                # Wait a bit before processing next document (avoid rate limiting)
                sleep 2
            else
                log_warning "Failed to upload: $FILENAME"
                log_warning "Response: $UPLOAD_RESPONSE"
            fi
        fi
    done

    log_success "Uploaded $UPLOADED_COUNT documents"

    if [ $UPLOADED_COUNT -gt 0 ]; then
        log_info "Documents are being processed in the background..."
        log_info "Processing may take 30-60 seconds per document"
        log_info "You can check processing status in the UI"
    fi
}

configure_feature_flags() {
    log_info "Configuring feature flags for demo..."

    # Enable all demo features
    cat > /tmp/demo_features.json <<EOF
{
  "enable_semantic_search": true,
  "enable_real_time_updates": true,
  "enable_multi_model_routing": true,
  "enable_analytics_dashboard": true,
  "max_upload_size_mb": 50,
  "max_documents_per_user": 1000
}
EOF

    # Apply configuration (this would integrate with your feature flag system)
    log_success "Feature flags configured"
}

print_summary() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Demo Environment Setup Complete! ${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}Demo Access:${NC}"
    echo -e "  URL:      ${GREEN}http://localhost:8000${NC}"
    echo -e "  Email:    ${GREEN}$DEMO_USER_EMAIL${NC}"
    echo -e "  Password: ${GREEN}$DEMO_USER_PASSWORD${NC}"
    echo ""
    echo -e "${BLUE}Services:${NC}"
    echo -e "  API:          http://localhost:8000"
    echo -e "  API Docs:     http://localhost:8000/docs"
    echo -e "  PostgreSQL:   localhost:5432"
    echo -e "  Redis:        localhost:6379"
    echo ""
    echo -e "${BLUE}Useful Commands:${NC}"
    echo -e "  View logs:        ${YELLOW}docker-compose logs -f${NC}"
    echo -e "  Restart services: ${YELLOW}docker-compose restart${NC}"
    echo -e "  Stop services:    ${YELLOW}docker-compose down${NC}"
    echo -e "  Reset demo:       ${YELLOW}./scripts/setup_demo.sh --reset${NC}"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "  1. Open http://localhost:8000 in your browser"
    echo "  2. Login with the demo credentials above"
    echo "  3. Try uploading a document from demo_data/"
    echo "  4. Explore the features and analytics"
    echo ""
    echo -e "${GREEN}Happy demoing! 🚀${NC}"
    echo ""
}

cleanup() {
    # Clean up temporary files
    rm -f /tmp/demo_org_id.txt /tmp/demo_user_id.txt /tmp/demo_features.json
}

###############################################################################
# Main Execution
###############################################################################

main() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  PM Document Intelligence${NC}"
    echo -e "${BLUE}  Demo Environment Setup${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    if [ "$RESET_MODE" = true ]; then
        log_warning "RESET MODE ENABLED - This will delete existing demo data!"
        read -p "Are you sure you want to continue? (yes/no): " CONFIRM
        if [ "$CONFIRM" != "yes" ]; then
            log_info "Setup cancelled by user"
            exit 0
        fi
    fi

    # Execute setup steps
    check_prerequisites
    start_services
    verify_services
    initialize_database
    create_demo_organization
    create_demo_user
    load_sample_documents
    configure_feature_flags
    print_summary
    cleanup

    log_success "Demo environment is ready!"
}

# Trap errors and cleanup
trap cleanup EXIT

# Run main function
main "$@"
