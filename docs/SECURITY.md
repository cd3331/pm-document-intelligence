# Security Documentation

Comprehensive security practices, compliance, and threat mitigation for PM Document Intelligence.

## Table of Contents

1. [Security Overview](#security-overview)
2. [Authentication & Authorization](#authentication--authorization)
3. [Data Security](#data-security)
4. [Network Security](#network-security)
5. [Application Security](#application-security)
6. [Infrastructure Security](#infrastructure-security)
7. [Compliance](#compliance)
8. [Incident Response](#incident-response)
9. [Security Monitoring](#security-monitoring)
10. [Security Checklist](#security-checklist)

---

## Security Overview

### Security Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Defense in Depth                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Layer 1: Perimeter Security                            │
│  ├─ AWS WAF (DDoS, SQL injection, XSS protection)      │
│  ├─ CloudFront (DDoS mitigation, rate limiting)        │
│  └─ Route 53 (DNS security, DDoS protection)           │
│                                                         │
│  Layer 2: Network Security                              │
│  ├─ VPC isolation (private subnets)                    │
│  ├─ Security Groups (stateful firewall)                │
│  ├─ NACLs (stateless firewall)                         │
│  └─ TLS 1.3 for all traffic                            │
│                                                         │
│  Layer 3: Application Security                          │
│  ├─ JWT authentication                                  │
│  ├─ RBAC authorization                                  │
│  ├─ Input validation                                    │
│  ├─ Output sanitization                                 │
│  └─ Rate limiting                                       │
│                                                         │
│  Layer 4: Data Security                                 │
│  ├─ Encryption at rest (AES-256)                       │
│  ├─ Encryption in transit (TLS 1.3)                    │
│  ├─ PII detection and masking                          │
│  └─ Secure key management (AWS KMS)                    │
│                                                         │
│  Layer 5: Monitoring & Response                         │
│  ├─ CloudWatch logs and alarms                         │
│  ├─ GuardDuty threat detection                         │
│  ├─ Security Hub compliance monitoring                 │
│  └─ Audit logging                                       │
└─────────────────────────────────────────────────────────┘
```

### Security Principles

1. **Least Privilege**: Minimum permissions required
2. **Defense in Depth**: Multiple security layers
3. **Fail Secure**: Secure by default, deny by default
4. **Zero Trust**: Never trust, always verify
5. **Encryption Everywhere**: At rest and in transit
6. **Audit Everything**: Complete audit trail

---

## Authentication & Authorization

### JWT Authentication

**Token Structure**:
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user_id",
    "email": "user@example.com",
    "org_id": "org_123",
    "role": "member",
    "permissions": ["documents:read", "documents:write"],
    "exp": 1640000000,
    "iat": 1639996400,
    "jti": "unique_token_id"
  },
  "signature": "..."
}
```

**Token Security**:
```python
# backend/app/core/auth.py

# Strong secret key (256-bit minimum)
SECRET_KEY = os.getenv("SECRET_KEY")  # From AWS Secrets Manager
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30

def create_access_token(data: dict) -> str:
    """Create secure JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4())  # Unique token ID for revocation
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> dict:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Check if token is revoked
        if is_token_revoked(payload["jti"]):
            raise HTTPException(status_code=401, detail="Token revoked")

        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

**Token Revocation**:
```python
# Store revoked tokens in Redis with TTL
def revoke_token(token_id: str, expires_at: datetime):
    """Add token to revocation list"""
    ttl = (expires_at - datetime.utcnow()).total_seconds()
    redis_client.setex(f"revoked:{token_id}", int(ttl), "1")

def is_token_revoked(token_id: str) -> bool:
    """Check if token is revoked"""
    return redis_client.exists(f"revoked:{token_id}")
```

### Password Security

**Requirements**:
```python
# backend/app/core/security.py

PASSWORD_MIN_LENGTH = 12
PASSWORD_REQUIREMENTS = {
    "lowercase": r"[a-z]",
    "uppercase": r"[A-Z]",
    "digit": r"\d",
    "special": r"[!@#$%^&*(),.?\":{}|<>]"
}

def validate_password_strength(password: str) -> bool:
    """Validate password meets security requirements"""
    if len(password) < PASSWORD_MIN_LENGTH:
        return False

    for requirement, pattern in PASSWORD_REQUIREMENTS.items():
        if not re.search(pattern, password):
            return False

    # Check against common passwords
    if password.lower() in COMMON_PASSWORDS:
        return False

    return True
```

**Password Hashing**:
```python
from passlib.context import CryptContext

# Use bcrypt with high cost factor
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # High cost factor for security
)

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)
```

### Multi-Factor Authentication (MFA)

**TOTP Implementation**:
```python
import pyotp
import qrcode

def setup_mfa(user_id: str, user_email: str) -> dict:
    """Setup MFA for user"""
    # Generate secret
    secret = pyotp.random_base32()

    # Store secret encrypted
    encrypted_secret = encrypt_value(secret)
    store_mfa_secret(user_id, encrypted_secret)

    # Generate provisioning URI
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user_email,
        issuer_name="PM Document Intelligence"
    )

    # Generate QR code
    qr = qrcode.QRCode()
    qr.add_data(provisioning_uri)
    qr.make()

    return {
        "secret": secret,
        "provisioning_uri": provisioning_uri,
        "qr_code": qr.make_image()
    }

def verify_mfa_code(user_id: str, code: str) -> bool:
    """Verify MFA code"""
    secret = get_mfa_secret(user_id)
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)  # Allow 30s window
```

### Role-Based Access Control (RBAC)

**Permission System**:
```python
# backend/app/models/permissions.py

class Permission(Enum):
    # Document permissions
    DOCUMENTS_READ = "documents:read"
    DOCUMENTS_WRITE = "documents:write"
    DOCUMENTS_DELETE = "documents:delete"
    DOCUMENTS_SHARE = "documents:share"

    # Organization permissions
    ORG_MANAGE = "org:manage"
    ORG_SETTINGS = "org:settings"
    ORG_BILLING = "org:billing"

    # User permissions
    USERS_INVITE = "users:invite"
    USERS_MANAGE = "users:manage"

    # Analytics permissions
    ANALYTICS_VIEW = "analytics:view"
    ANALYTICS_EXPORT = "analytics:export"

ROLE_PERMISSIONS = {
    "superadmin": list(Permission),
    "org_admin": [
        Permission.DOCUMENTS_READ,
        Permission.DOCUMENTS_WRITE,
        Permission.DOCUMENTS_DELETE,
        Permission.DOCUMENTS_SHARE,
        Permission.ORG_SETTINGS,
        Permission.USERS_INVITE,
        Permission.USERS_MANAGE,
        Permission.ANALYTICS_VIEW,
        Permission.ANALYTICS_EXPORT,
    ],
    "org_member": [
        Permission.DOCUMENTS_READ,
        Permission.DOCUMENTS_WRITE,
        Permission.DOCUMENTS_SHARE,
        Permission.ANALYTICS_VIEW,
    ],
    "org_viewer": [
        Permission.DOCUMENTS_READ,
        Permission.ANALYTICS_VIEW,
    ],
}

def has_permission(user: User, permission: Permission) -> bool:
    """Check if user has specific permission"""
    user_permissions = ROLE_PERMISSIONS.get(user.role, [])
    return permission in user_permissions

# Decorator for endpoint protection
def require_permission(permission: Permission):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            if not has_permission(current_user, permission):
                raise HTTPException(status_code=403, detail="Permission denied")
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

# Usage
@router.delete("/documents/{document_id}")
@require_permission(Permission.DOCUMENTS_DELETE)
async def delete_document(document_id: uuid.UUID, current_user: User):
    pass
```

---

## Data Security

### Encryption at Rest

**Database Encryption**:
```python
# RDS PostgreSQL with AWS KMS
aws rds create-db-instance \
    --db-instance-identifier pm-doc-intel \
    --storage-encrypted \
    --kms-key-id arn:aws:kms:us-east-1:ACCOUNT_ID:key/KEY_ID \
    --backup-retention-period 7 \
    --deletion-protection
```

**S3 Encryption**:
```python
# Default encryption with AWS KMS
aws s3api put-bucket-encryption \
    --bucket pm-doc-intel-documents \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "aws:kms",
                "KMSMasterKeyID": "arn:aws:kms:..."
            },
            "BucketKeyEnabled": true
        }]
    }'

# Enforce encryption
aws s3api put-bucket-policy \
    --bucket pm-doc-intel-documents \
    --policy '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Deny",
            "Principal": "*",
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::pm-doc-intel-documents/*",
            "Condition": {
                "StringNotEquals": {
                    "s3:x-amz-server-side-encryption": "aws:kms"
                }
            }
        }]
    }'
```

**Application-Level Encryption**:
```python
# backend/app/core/encryption.py
from cryptography.fernet import Fernet

class Encryptor:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)

    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()

# Usage for PII fields
def save_user_sensitive_data(user_id: str, ssn: str):
    """Save sensitive data with encryption"""
    encryptor = Encryptor(get_encryption_key())
    encrypted_ssn = encryptor.encrypt(ssn)

    db.execute(
        "UPDATE users SET encrypted_ssn = %s WHERE id = %s",
        (encrypted_ssn, user_id)
    )
```

### Encryption in Transit

**TLS Configuration**:
```python
# Force TLS 1.3
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["pmdocintel.com", "*.pmdocintel.com"])

# ALB SSL Policy
aws elbv2 create-listener \
    --load-balancer-arn arn:aws:... \
    --protocol HTTPS \
    --port 443 \
    --certificates CertificateArn=arn:aws:acm:... \
    --ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06 \
    --default-actions Type=forward,TargetGroupArn=arn:aws:...
```

**HSTS Headers**:
```python
# backend/app/main.py
from fastapi.middleware.cors import CORSMiddleware

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline';"
    return response
```

### PII Detection and Protection

**Automated PII Detection**:
```python
# ml/training/data_preparation.py

class PIIDetector:
    """Detect and mask PII in documents"""

    PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
        "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        "ip_address": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        "passport": r'\b[A-Z]{1,2}\d{6,9}\b',
    }

    @classmethod
    def detect_pii(cls, text: str) -> Dict[str, List[str]]:
        """Detect all PII in text"""
        detected = {}
        for pii_type, pattern in cls.PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                detected[pii_type] = matches
        return detected

    @classmethod
    def mask_pii(cls, text: str) -> str:
        """Replace PII with masked values"""
        masked = text
        for pii_type, pattern in cls.PATTERNS.items():
            masked = re.sub(pattern, f"[{pii_type.upper()}]", masked)
        return masked

# Usage
document_text = "Contact John at john@example.com or 555-123-4567"
if PIIDetector.detect_pii(document_text):
    masked_text = PIIDetector.mask_pii(document_text)
    # Result: "Contact John at [EMAIL] or [PHONE]"
```

### Data Access Logging

**Audit Log Implementation**:
```python
# backend/app/models/audit_log.py

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(String, nullable=False)  # READ, WRITE, DELETE
    resource_type = Column(String, nullable=False)  # document, user, org
    resource_id = Column(String, nullable=False)
    ip_address = Column(String)
    user_agent = Column(String)
    success = Column(Boolean, default=True)
    metadata = Column(JSONB)

def log_data_access(
    user_id: uuid.UUID,
    action: str,
    resource_type: str,
    resource_id: str,
    request: Request
):
    """Log data access for audit trail"""
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        success=True
    )
    db.add(log)
    db.commit()

# Decorator for automatic logging
def audit_log(action: str, resource_type: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, resource_id: str, request: Request, current_user: User, **kwargs):
            log_data_access(current_user.id, action, resource_type, resource_id, request)
            return await func(*args, resource_id=resource_id, request=request, current_user=current_user, **kwargs)
        return wrapper
    return decorator

# Usage
@router.get("/documents/{document_id}")
@audit_log(action="READ", resource_type="document")
async def get_document(document_id: str, request: Request, current_user: User):
    pass
```

---

## Network Security

### VPC Configuration

**Network Isolation**:
```hcl
# terraform/vpc.tf

# Public subnets (ALB only)
resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = false  # No public IPs
}

# Private subnets (application tier)
resource "aws_subnet" "private_app" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]
}

# Private subnets (data tier - even more isolated)
resource "aws_subnet" "private_data" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 20)
  availability_zone = data.aws_availability_zones.available.names[count.index]
}
```

### Security Groups

**Least Privilege Access**:
```hcl
# ALB Security Group
resource "aws_security_group" "alb" {
  name        = "pm-doc-intel-alb"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Public HTTPS
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Redirect to HTTPS
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]  # Only to VPC
  }
}

# ECS Tasks Security Group
resource "aws_security_group" "ecs_tasks" {
  name        = "pm-doc-intel-ecs"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]  # Only from ALB
  }

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # HTTPS to internet (APIs)
  }

  egress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.database.id]  # To database
  }
}

# Database Security Group
resource "aws_security_group" "database" {
  name        = "pm-doc-intel-db"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]  # Only from ECS
  }

  # No egress - database doesn't initiate connections
}
```

### WAF Rules

```json
{
  "Name": "pm-doc-intel-waf",
  "Rules": [
    {
      "Name": "RateLimitRule",
      "Priority": 1,
      "Statement": {
        "RateBasedStatement": {
          "Limit": 2000,
          "AggregateKeyType": "IP"
        }
      },
      "Action": {"Block": {}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "RateLimitRule"
      }
    },
    {
      "Name": "SQLInjectionRule",
      "Priority": 2,
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesSQLiRuleSet"
        }
      },
      "OverrideAction": {"None": {}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "SQLInjectionRule"
      }
    },
    {
      "Name": "XSSRule",
      "Priority": 3,
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesKnownBadInputsRuleSet"
        }
      },
      "OverrideAction": {"None": {}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "XSSRule"
      }
    }
  ]
}
```

---

## Application Security

### Input Validation

```python
# backend/app/core/validation.py

from pydantic import BaseModel, validator, constr

class DocumentUploadRequest(BaseModel):
    filename: constr(min_length=1, max_length=255)
    document_type: Optional[str]
    metadata: Optional[Dict[str, Any]]

    @validator('filename')
    def validate_filename(cls, v):
        # Prevent path traversal
        if '..' in v or '/' in v or '\\' in v:
            raise ValueError("Invalid filename")

        # Check file extension
        allowed_extensions = ['.pdf', '.docx', '.txt']
        if not any(v.lower().endswith(ext) for ext in allowed_extensions):
            raise ValueError("Invalid file type")

        return v

    @validator('metadata')
    def validate_metadata(cls, v):
        if v is None:
            return v

        # Limit metadata size
        if len(json.dumps(v)) > 10000:  # 10KB limit
            raise ValueError("Metadata too large")

        # Sanitize values
        return sanitize_dict(v)

def sanitize_string(value: str) -> str:
    """Remove dangerous characters"""
    # Remove null bytes
    value = value.replace('\x00', '')

    # HTML escape
    value = html.escape(value)

    return value

def sanitize_dict(data: Dict) -> Dict:
    """Recursively sanitize dictionary"""
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_string(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        else:
            sanitized[key] = value
    return sanitized
```

### SQL Injection Prevention

```python
# Always use parameterized queries
from sqlalchemy.orm import Session

# GOOD - Parameterized query
def get_documents_by_type(db: Session, doc_type: str):
    return db.query(Document).filter(
        Document.document_type == doc_type
    ).all()

# BAD - String concatenation (vulnerable to SQL injection)
def get_documents_bad(db: Session, doc_type: str):
    query = f"SELECT * FROM documents WHERE document_type = '{doc_type}'"
    return db.execute(query).fetchall()  # NEVER DO THIS
```

### XSS Prevention

```python
# backend/app/core/sanitization.py

import bleach
from markupsafe import Markup, escape

ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li']
ALLOWED_ATTRIBUTES = {'a': ['href', 'title']}

def sanitize_html(html_content: str) -> str:
    """Sanitize HTML content to prevent XSS"""
    return bleach.clean(
        html_content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )

def escape_user_input(user_input: str) -> str:
    """Escape user input for safe display"""
    return escape(user_input)

# In templates
from jinja2 import Template

template = Template("""
<div class="comment">
    {{ comment | escape }}
</div>
""")
```

### CSRF Protection

```python
# backend/app/middleware/csrf.py

from itsdangerous import URLSafeTimedSerializer

class CSRFProtection:
    def __init__(self, secret_key: str):
        self.serializer = URLSafeTimedSerializer(secret_key)

    def generate_token(self, session_id: str) -> str:
        """Generate CSRF token"""
        return self.serializer.dumps(session_id)

    def validate_token(self, token: str, session_id: str, max_age: int = 3600) -> bool:
        """Validate CSRF token"""
        try:
            data = self.serializer.loads(token, max_age=max_age)
            return data == session_id
        except:
            return False

@app.middleware("http")
async def csrf_protection(request: Request, call_next):
    if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
        csrf_token = request.headers.get("X-CSRF-Token")
        session_id = request.cookies.get("session_id")

        csrf = CSRFProtection(SECRET_KEY)
        if not csrf.validate_token(csrf_token, session_id):
            raise HTTPException(status_code=403, detail="CSRF validation failed")

    response = await call_next(request)
    return response
```

### Rate Limiting

```python
# backend/app/middleware/rate_limit.py

from fastapi import Request, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour", "50 per minute"]
)

# Per-endpoint limits
@app.post("/api/documents/upload")
@limiter.limit("10 per minute")
async def upload_document(request: Request):
    pass

@app.post("/api/auth/login")
@limiter.limit("5 per minute")  # Stricter for auth
async def login(request: Request):
    pass

# Handle rate limit exceeded
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

---

## Infrastructure Security

### IAM Policies

**Least Privilege ECS Task Role**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::pm-doc-intel-documents/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:pm-doc-intel/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt"
      ],
      "Resource": "arn:aws:kms:*:*:key/*",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": [
            "s3.us-east-1.amazonaws.com",
            "secretsmanager.us-east-1.amazonaws.com"
          ]
        }
      }
    }
  ]
}
```

### Secrets Management

**AWS Secrets Manager**:
```bash
# Store secrets
aws secretsmanager create-secret \
    --name pm-doc-intel/database-url \
    --secret-string '{"url":"postgresql://user:pass@host:5432/db"}' \
    --kms-key-id arn:aws:kms:...

# Rotate secrets automatically
aws secretsmanager rotate-secret \
    --secret-id pm-doc-intel/database-url \
    --rotation-lambda-arn arn:aws:lambda:... \
    --rotation-rules AutomaticallyAfterDays=30
```

**Never commit secrets**:
```bash
# .gitignore
.env
.env.*
*.key
*.pem
secrets/
credentials.json

# Use pre-commit hook to detect secrets
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
```

### Container Security

**Dockerfile Best Practices**:
```dockerfile
# Use official minimal base image
FROM python:3.11-slim as builder

# Run as non-root user
RUN useradd -m -u 1000 appuser

# Install only necessary packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Copy application
WORKDIR /app
COPY --chown=appuser:appuser backend/ backend/

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run application
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Scan images for vulnerabilities**:
```bash
# Scan with Trivy
trivy image pm-doc-intel:latest

# Scan in CI/CD
- name: Scan Docker image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ secrets.ECR_REGISTRY }}/pm-doc-intel:${{ github.sha }}
    format: 'sarif'
    output: 'trivy-results.sarif'
    severity: 'CRITICAL,HIGH'
```

---

## Compliance

### GDPR Compliance

**Data Subject Rights**:
```python
# backend/app/routes/gdpr.py

@router.get("/api/gdpr/export")
async def export_user_data(current_user: User, db: Session):
    """Export all user data (GDPR Article 20)"""
    user_data = {
        "profile": {
            "email": current_user.email,
            "name": current_user.name,
            "created_at": current_user.created_at.isoformat()
        },
        "documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "uploaded_at": doc.created_at.isoformat()
            }
            for doc in current_user.documents
        ],
        "audit_logs": [
            {
                "action": log.action,
                "timestamp": log.timestamp.isoformat()
            }
            for log in get_user_audit_logs(current_user.id, db)
        ]
    }

    return {
        "format": "json",
        "data": user_data,
        "generated_at": datetime.utcnow().isoformat()
    }

@router.delete("/api/gdpr/delete")
async def delete_user_data(current_user: User, db: Session):
    """Delete all user data (GDPR Article 17 - Right to Erasure)"""
    # Anonymize audit logs (retain for compliance)
    anonymize_audit_logs(current_user.id, db)

    # Delete documents from S3
    for doc in current_user.documents:
        s3_client.delete_object(
            Bucket=S3_BUCKET,
            Key=doc.s3_key
        )

    # Delete database records
    db.query(Document).filter(Document.user_id == current_user.id).delete()
    db.query(User).filter(User.id == current_user.id).delete()
    db.commit()

    return {"message": "All user data deleted successfully"}
```

### SOC 2 Requirements

**Access Control Matrix**:
```csv
User Type,Documents,Users,Billing,Settings,Audit Logs
SuperAdmin,Full,Full,Full,Full,Full
OrgAdmin,Full,Manage,View,Full,View
Member,Write/Read,None,None,None,None
Viewer,Read Only,None,None,None,None
```

**Change Management**:
```python
# Track all changes for audit
class ChangeLog(Base):
    __tablename__ = "change_logs"

    id = Column(UUID(as_uuid=True), primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(UUID(as_uuid=True))
    entity_type = Column(String)
    entity_id = Column(String)
    action = Column(String)  # CREATE, UPDATE, DELETE
    old_value = Column(JSONB)
    new_value = Column(JSONB)
    ip_address = Column(String)
```

---

## Incident Response

### Incident Response Plan

**Response Team**:
- Security Lead
- Engineering Lead
- DevOps Engineer
- Legal Counsel
- PR/Communications

**Response Phases**:

1. **Detection** (0-5 minutes)
   - Automated alerts trigger
   - Security team notified

2. **Analysis** (5-30 minutes)
   - Assess severity and scope
   - Identify affected systems
   - Determine if customer data is compromised

3. **Containment** (30-60 minutes)
   - Isolate affected systems
   - Block malicious IPs
   - Revoke compromised credentials

4. **Eradication** (1-4 hours)
   - Remove threat
   - Patch vulnerabilities
   - Update security rules

5. **Recovery** (4-24 hours)
   - Restore systems
   - Verify integrity
   - Monitor for recurrence

6. **Post-Incident** (1-7 days)
   - Document incident
   - Update procedures
   - Notify affected parties
   - Submit regulatory reports

### Security Incident Playbooks

**Data Breach Playbook**:
```markdown
1. Immediate Actions (0-1 hour)
   - [ ] Isolate affected systems
   - [ ] Preserve logs and evidence
   - [ ] Assess scope of breach
   - [ ] Notify security team

2. Investigation (1-24 hours)
   - [ ] Identify root cause
   - [ ] Determine data accessed
   - [ ] Identify affected users
   - [ ] Document timeline

3. Notification (24-72 hours)
   - [ ] Notify affected users (GDPR: 72 hours)
   - [ ] File regulatory reports
   - [ ] Prepare public statement
   - [ ] Contact cyber insurance

4. Remediation
   - [ ] Patch vulnerability
   - [ ] Force password resets
   - [ ] Update security controls
   - [ ] Implement monitoring

5. Post-Mortem
   - [ ] Document lessons learned
   - [ ] Update security procedures
   - [ ] Train team on new procedures
   - [ ] Schedule follow-up review
```

---

## Security Monitoring

### Real-time Monitoring

**CloudWatch Alarms**:
```python
# Unusual login activity
- Metric: FailedLoginAttempts
- Threshold: > 10 in 5 minutes
- Action: Alert security team

# Suspicious API activity
- Metric: 4XXErrorRate
- Threshold: > 20% for 10 minutes
- Action: Trigger investigation

# Data exfiltration
- Metric: S3DownloadVolume
- Threshold: > 10 GB in 1 hour
- Action: Block access, alert team
```

**GuardDuty Integration**:
```bash
# Enable GuardDuty
aws guardduty create-detector --enable

# Configure findings
aws guardduty create-filter \
    --detector-id xxx \
    --name high-severity-findings \
    --finding-criteria '{
        "Criterion": {
            "severity": {
                "Gte": 7
            }
        }
    }' \
    --action ARCHIVE
```

### Security Metrics

**Track Key Metrics**:
```python
security_metrics = {
    "authentication": {
        "failed_logins": 0,
        "successful_logins": 0,
        "mfa_enabled_users": 0,
        "password_resets": 0
    },
    "access_control": {
        "permission_denied_count": 0,
        "admin_actions": 0,
        "token_revocations": 0
    },
    "threats": {
        "blocked_ips": 0,
        "sql_injection_attempts": 0,
        "xss_attempts": 0,
        "suspicious_uploads": 0
    },
    "compliance": {
        "encryption_rate": 100,
        "audit_log_coverage": 100,
        "backup_success_rate": 100
    }
}
```

---

## Security Checklist

### Development
- [ ] Input validation on all endpoints
- [ ] Output sanitization for user data
- [ ] Parameterized database queries
- [ ] Secrets stored in Secrets Manager
- [ ] No hardcoded credentials
- [ ] HTTPS for all traffic
- [ ] Security headers implemented
- [ ] CSRF protection enabled
- [ ] Rate limiting configured

### Infrastructure
- [ ] VPC with private subnets
- [ ] Security groups with least privilege
- [ ] WAF rules configured
- [ ] GuardDuty enabled
- [ ] Security Hub enabled
- [ ] CloudTrail logging enabled
- [ ] All data encrypted at rest
- [ ] All data encrypted in transit
- [ ] IAM roles with least privilege

### Compliance
- [ ] GDPR data export implemented
- [ ] GDPR data deletion implemented
- [ ] Audit logging for all data access
- [ ] Change management tracking
- [ ] Incident response plan documented
- [ ] Security training completed
- [ ] Penetration testing scheduled
- [ ] Vulnerability scanning automated

### Monitoring
- [ ] CloudWatch alarms configured
- [ ] Security dashboards created
- [ ] Log aggregation enabled
- [ ] Anomaly detection configured
- [ ] On-call rotation established
- [ ] Incident response team identified

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [AWS Security Best Practices](https://aws.amazon.com/security/best-practices/)
- [GDPR Compliance Guide](https://gdpr.eu/)
- [SOC 2 Requirements](https://www.aicpa.org/soc)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

**Last Updated**: January 2024
**Security Contact**: security@pmdocintel.com
**Bug Bounty Program**: https://pmdocintel.com/security/bounty
