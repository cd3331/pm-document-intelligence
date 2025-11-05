"""
Audit Log Models
Database models for audit trail and compliance logging
"""

from sqlalchemy import Column, String, DateTime, Text, Index, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

from app.core.database import Base


class AuditLog(Base):
    """
    Comprehensive audit log for compliance and security
    Tracks all significant actions in the system
    """

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Actor information
    user_id = Column(
        UUID(as_uuid=True), index=True, nullable=True
    )  # Null for system actions
    username = Column(String(255))  # Denormalized for historical record
    user_email = Column(String(255))  # Denormalized for historical record

    # Organization context
    organization_id = Column(UUID(as_uuid=True), index=True, nullable=True)

    # Action details
    action = Column(
        String(100), nullable=False, index=True
    )  # e.g., "document_created", "user_role_updated"
    category = Column(
        String(50), nullable=False, index=True
    )  # e.g., "document", "user", "org", "auth"

    # Resource information
    resource_type = Column(
        String(50), nullable=True, index=True
    )  # e.g., "document", "user", "team"
    resource_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Request metadata
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(String(500))
    request_method = Column(String(10))  # GET, POST, PUT, DELETE
    request_path = Column(String(500))

    # Status and result
    status = Column(String(20), nullable=False)  # success, failure, partial
    status_code = Column(String(10))  # HTTP status code or custom code

    # Detailed information
    details = Column(JSONB, default=dict)  # Additional context and data
    changes = Column(JSONB, nullable=True)  # Before/after for updates

    # Error information (if failed)
    error_message = Column(Text, nullable=True)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Data classification
    sensitivity_level = Column(
        String(20), default="normal"
    )  # normal, sensitive, confidential

    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_audit_user_timestamp", "user_id", "timestamp"),
        Index("idx_audit_org_timestamp", "organization_id", "timestamp"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_action_timestamp", "action", "timestamp"),
        Index("idx_audit_category_timestamp", "category", "timestamp"),
    )

    def __repr__(self):
        return f"<AuditLog(action={self.action}, user={self.username}, timestamp={self.timestamp})>"


class DataAccessLog(Base):
    """
    Specialized log for data access tracking
    Helps with compliance (GDPR, HIPAA, etc.)
    """

    __tablename__ = "data_access_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Actor
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Data accessed
    data_type = Column(
        String(50), nullable=False, index=True
    )  # document, user_profile, etc.
    data_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    data_classification = Column(
        String(20)
    )  # public, internal, confidential, restricted

    # Access details
    access_type = Column(String(20), nullable=False)  # read, download, export, print
    access_method = Column(String(50))  # api, web, download, etc.

    # Purpose (for compliance)
    purpose = Column(String(200))  # Why was data accessed
    justification = Column(Text)  # Detailed justification if required

    # Request metadata
    ip_address = Column(String(45))
    user_agent = Column(String(500))

    # Result
    status = Column(String(20), nullable=False)  # granted, denied, partial
    records_accessed = Column(String)  # Number or description of records

    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    session_id = Column(String(255), index=True)

    __table_args__ = (
        Index("idx_data_access_user_time", "user_id", "timestamp"),
        Index("idx_data_access_data", "data_type", "data_id"),
    )

    def __repr__(self):
        return f"<DataAccessLog(user={self.user_id}, data={self.data_type}, type={self.access_type})>"


class ComplianceEvent(Base):
    """
    Special events for compliance reporting
    Tracks events that may need to be reported to authorities
    """

    __tablename__ = "compliance_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Organization context
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Event information
    event_type = Column(String(100), nullable=False, index=True)
    # Examples: data_breach, unauthorized_access, data_deletion, export_large_dataset
    severity = Column(String(20), nullable=False)  # low, medium, high, critical

    # Description
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)

    # Parties involved
    affected_users = Column(JSONB, default=list)  # List of affected user IDs
    involved_users = Column(JSONB, default=list)  # List of users involved in event

    # Data affected
    affected_data = Column(JSONB, default=dict)  # Description of affected data

    # Status
    status = Column(
        String(20), default="open"
    )  # open, investigating, resolved, reported
    resolution = Column(Text, nullable=True)

    # Reporting
    requires_reporting = Column(String, default=False)  # Requires regulatory reporting
    reported_at = Column(DateTime, nullable=True)
    reported_to = Column(String(200), nullable=True)  # Which authority

    # Timestamps
    occurred_at = Column(DateTime, nullable=False, index=True)
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    # Investigation
    investigator_id = Column(UUID(as_uuid=True), nullable=True)
    investigation_notes = Column(JSONB, default=list)

    __table_args__ = (
        Index("idx_compliance_org_severity", "organization_id", "severity"),
        Index("idx_compliance_status", "status"),
    )

    def __repr__(self):
        return f"<ComplianceEvent(type={self.event_type}, severity={self.severity})>"


class AuditLogRetention(Base):
    """
    Tracks audit log retention policies and cleanup jobs
    """

    __tablename__ = "audit_log_retention"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    organization_id = Column(
        UUID(as_uuid=True), nullable=True, index=True
    )  # Null = system-wide
    log_type = Column(
        String(50), nullable=False
    )  # audit_logs, data_access_logs, compliance_events

    # Retention policy
    retention_days = Column(String, default=2555)  # 7 years default (2555 days)
    archive_after_days = Column(String, nullable=True)  # Move to cold storage

    # Last cleanup
    last_cleanup_at = Column(DateTime, nullable=True)
    records_deleted = Column(String, default=0)
    records_archived = Column(String, default=0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<AuditLogRetention(log_type={self.log_type}, retention_days={self.retention_days})>"
