"""
Audit Logging Service
Comprehensive audit trail for compliance and security
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import uuid
import csv
import io
import json

from app.models.audit import AuditLog, DataAccessLog, ComplianceEvent, AuditLogRetention
from app.models.user import User


class AuditLogger:
    """
    Service for logging audit events
    Provides comprehensive audit trail for compliance
    """

    def __init__(self, db: Session):
        self.db = db

    # ============================================================================
    # Event Logging
    # ============================================================================

    async def log_event(
        self,
        action: str,
        category: str = None,
        user_id: Optional[uuid.UUID] = None,
        organization_id: Optional[uuid.UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[uuid.UUID] = None,
        status: str = "success",
        status_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        changes: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        sensitivity_level: str = "normal",
    ) -> AuditLog:
        """
        Log a general audit event

        Args:
            action: Action performed (e.g., "document_created", "user_deleted")
            category: Category of action (auto-derived from resource_type if not provided)
            user_id: User who performed action (None for system actions)
            organization_id: Organization context
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            status: Result status (success, failure, partial)
            status_code: HTTP or custom status code
            details: Additional context
            changes: Before/after state for updates
            error_message: Error details if failed
            ip_address: Request IP
            user_agent: Request user agent
            request_method: HTTP method
            request_path: Request path
            sensitivity_level: Data sensitivity (normal, sensitive, confidential)

        Returns:
            AuditLog: Created audit log entry
        """
        # Get user details if user_id provided
        username = None
        user_email = None
        if user_id:
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                username = user.username
                user_email = user.email

        # Auto-derive category if not provided
        if not category and resource_type:
            category = resource_type
        elif not category:
            category = "system"

        # Create audit log entry
        audit_log = AuditLog(
            user_id=user_id,
            username=username,
            user_email=user_email,
            organization_id=organization_id,
            action=action,
            category=category,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            status_code=status_code,
            details=details or {},
            changes=changes,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            sensitivity_level=sensitivity_level,
            timestamp=datetime.utcnow(),
        )

        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)

        return audit_log

    async def log_data_access(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        data_type: str,
        data_id: uuid.UUID,
        access_type: str,
        data_classification: Optional[str] = None,
        access_method: Optional[str] = None,
        purpose: Optional[str] = None,
        justification: Optional[str] = None,
        status: str = "granted",
        records_accessed: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> DataAccessLog:
        """
        Log data access for compliance

        Args:
            user_id: User accessing data
            organization_id: Organization context
            data_type: Type of data (document, user_profile, etc.)
            data_id: ID of data accessed
            access_type: Type of access (read, download, export, print)
            data_classification: Data sensitivity level
            access_method: How data was accessed (api, web, etc.)
            purpose: Purpose of access
            justification: Detailed justification if required
            status: Access status (granted, denied, partial)
            records_accessed: Count or description of records
            ip_address: Request IP
            user_agent: Request user agent
            session_id: Session identifier

        Returns:
            DataAccessLog: Created log entry
        """
        data_access_log = DataAccessLog(
            user_id=user_id,
            organization_id=organization_id,
            data_type=data_type,
            data_id=data_id,
            data_classification=data_classification,
            access_type=access_type,
            access_method=access_method,
            purpose=purpose,
            justification=justification,
            status=status,
            records_accessed=records_accessed,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            timestamp=datetime.utcnow(),
        )

        self.db.add(data_access_log)
        self.db.commit()
        self.db.refresh(data_access_log)

        return data_access_log

    async def log_compliance_event(
        self,
        organization_id: uuid.UUID,
        event_type: str,
        severity: str,
        title: str,
        description: str,
        affected_users: Optional[List[uuid.UUID]] = None,
        involved_users: Optional[List[uuid.UUID]] = None,
        affected_data: Optional[Dict[str, Any]] = None,
        requires_reporting: bool = False,
        occurred_at: Optional[datetime] = None,
    ) -> ComplianceEvent:
        """
        Log a compliance event

        Args:
            organization_id: Organization context
            event_type: Type of event (data_breach, unauthorized_access, etc.)
            severity: Event severity (low, medium, high, critical)
            title: Brief title
            description: Detailed description
            affected_users: List of affected user IDs
            involved_users: List of involved user IDs
            affected_data: Description of affected data
            requires_reporting: Whether regulatory reporting is required
            occurred_at: When event occurred (defaults to now)

        Returns:
            ComplianceEvent: Created compliance event
        """
        compliance_event = ComplianceEvent(
            organization_id=organization_id,
            event_type=event_type,
            severity=severity,
            title=title,
            description=description,
            affected_users=affected_users or [],
            involved_users=involved_users or [],
            affected_data=affected_data or {},
            requires_reporting=requires_reporting,
            occurred_at=occurred_at or datetime.utcnow(),
            detected_at=datetime.utcnow(),
            status="open",
        )

        self.db.add(compliance_event)
        self.db.commit()
        self.db.refresh(compliance_event)

        return compliance_event

    # ============================================================================
    # Convenience Methods for Common Actions
    # ============================================================================

    async def log_login(
        self,
        user_id: uuid.UUID,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """Log user login attempt"""
        return await self.log_event(
            action="user_login" if success else "user_login_failed",
            category="auth",
            user_id=user_id if success else None,
            status="success" if success else "failure",
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"login_successful": success},
        )

    async def log_logout(self, user_id: uuid.UUID, ip_address: Optional[str] = None):
        """Log user logout"""
        return await self.log_event(
            action="user_logout",
            category="auth",
            user_id=user_id,
            status="success",
            ip_address=ip_address,
        )

    async def log_permission_change(
        self,
        actor_id: uuid.UUID,
        organization_id: uuid.UUID,
        target_user_id: uuid.UUID,
        old_role: str,
        new_role: str,
        resource_type: str = "user",
        resource_id: Optional[uuid.UUID] = None,
    ):
        """Log permission/role change"""
        return await self.log_event(
            action="permission_changed",
            category="access_control",
            user_id=actor_id,
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=resource_id or target_user_id,
            status="success",
            changes={"before": {"role": old_role}, "after": {"role": new_role}},
            details={
                "target_user_id": str(target_user_id),
                "old_role": old_role,
                "new_role": new_role,
            },
            sensitivity_level="sensitive",
        )

    async def log_data_export(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        export_type: str,
        record_count: int,
        file_size_bytes: int,
    ):
        """Log data export"""
        return await self.log_event(
            action="data_exported",
            category="data_access",
            user_id=user_id,
            organization_id=organization_id,
            status="success",
            details={
                "export_type": export_type,
                "record_count": record_count,
                "file_size_bytes": file_size_bytes,
            },
            sensitivity_level="sensitive",
        )

    # ============================================================================
    # Query Methods
    # ============================================================================

    async def get_audit_logs(
        self,
        organization_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        category: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AuditLog]:
        """
        Query audit logs with filters

        Returns:
            List of matching audit logs
        """
        query = self.db.query(AuditLog)

        # Apply filters
        if organization_id:
            query = query.filter(AuditLog.organization_id == organization_id)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        if action:
            query = query.filter(AuditLog.action == action)

        if category:
            query = query.filter(AuditLog.category == category)

        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)

        if resource_id:
            query = query.filter(AuditLog.resource_id == resource_id)

        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)

        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)

        if status:
            query = query.filter(AuditLog.status == status)

        # Order by timestamp descending
        query = query.order_by(desc(AuditLog.timestamp))

        # Pagination
        query = query.offset(skip).limit(limit)

        return query.all()

    async def get_data_access_logs(
        self,
        organization_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        data_type: Optional[str] = None,
        data_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[DataAccessLog]:
        """Query data access logs with filters"""
        query = self.db.query(DataAccessLog)

        if organization_id:
            query = query.filter(DataAccessLog.organization_id == organization_id)

        if user_id:
            query = query.filter(DataAccessLog.user_id == user_id)

        if data_type:
            query = query.filter(DataAccessLog.data_type == data_type)

        if data_id:
            query = query.filter(DataAccessLog.data_id == data_id)

        if start_date:
            query = query.filter(DataAccessLog.timestamp >= start_date)

        if end_date:
            query = query.filter(DataAccessLog.timestamp <= end_date)

        query = query.order_by(desc(DataAccessLog.timestamp))
        query = query.offset(skip).limit(limit)

        return query.all()

    async def get_compliance_events(
        self,
        organization_id: Optional[uuid.UUID] = None,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        requires_reporting: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ComplianceEvent]:
        """Query compliance events with filters"""
        query = self.db.query(ComplianceEvent)

        if organization_id:
            query = query.filter(ComplianceEvent.organization_id == organization_id)

        if event_type:
            query = query.filter(ComplianceEvent.event_type == event_type)

        if severity:
            query = query.filter(ComplianceEvent.severity == severity)

        if status:
            query = query.filter(ComplianceEvent.status == status)

        if requires_reporting is not None:
            query = query.filter(ComplianceEvent.requires_reporting == requires_reporting)

        if start_date:
            query = query.filter(ComplianceEvent.occurred_at >= start_date)

        if end_date:
            query = query.filter(ComplianceEvent.occurred_at <= end_date)

        query = query.order_by(desc(ComplianceEvent.occurred_at))
        query = query.offset(skip).limit(limit)

        return query.all()

    # ============================================================================
    # Export Methods
    # ============================================================================

    async def export_audit_logs_csv(
        self,
        organization_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> str:
        """
        Export audit logs to CSV format

        Returns:
            CSV string
        """
        logs = await self.get_audit_logs(
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000,  # Large limit for export
        )

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "Timestamp",
                "User",
                "Email",
                "Organization ID",
                "Action",
                "Category",
                "Resource Type",
                "Resource ID",
                "Status",
                "IP Address",
                "Details",
            ]
        )

        # Data rows
        for log in logs:
            writer.writerow(
                [
                    log.timestamp.isoformat(),
                    log.username or "System",
                    log.user_email or "",
                    str(log.organization_id) if log.organization_id else "",
                    log.action,
                    log.category,
                    log.resource_type or "",
                    str(log.resource_id) if log.resource_id else "",
                    log.status,
                    log.ip_address or "",
                    json.dumps(log.details) if log.details else "",
                ]
            )

        return output.getvalue()

    async def export_audit_logs_json(
        self,
        organization_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> str:
        """
        Export audit logs to JSON format

        Returns:
            JSON string
        """
        logs = await self.get_audit_logs(
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000,
        )

        logs_data = []
        for log in logs:
            logs_data.append(
                {
                    "id": str(log.id),
                    "timestamp": log.timestamp.isoformat(),
                    "user_id": str(log.user_id) if log.user_id else None,
                    "username": log.username,
                    "user_email": log.user_email,
                    "organization_id": (str(log.organization_id) if log.organization_id else None),
                    "action": log.action,
                    "category": log.category,
                    "resource_type": log.resource_type,
                    "resource_id": str(log.resource_id) if log.resource_id else None,
                    "status": log.status,
                    "status_code": log.status_code,
                    "details": log.details,
                    "changes": log.changes,
                    "error_message": log.error_message,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "request_method": log.request_method,
                    "request_path": log.request_path,
                    "sensitivity_level": log.sensitivity_level,
                }
            )

        return json.dumps(
            {
                "export_timestamp": datetime.utcnow().isoformat(),
                "organization_id": str(organization_id) if organization_id else None,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "total_records": len(logs_data),
                "logs": logs_data,
            },
            indent=2,
        )

    # ============================================================================
    # Analytics
    # ============================================================================

    async def get_audit_summary(
        self, organization_id: uuid.UUID, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get audit log summary for a period

        Returns:
            dict with summary statistics
        """
        # Total events
        total_events = (
            self.db.query(func.count(AuditLog.id))
            .filter(
                AuditLog.organization_id == organization_id,
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
            )
            .scalar()
        )

        # Events by category
        events_by_category = (
            self.db.query(AuditLog.category, func.count(AuditLog.id))
            .filter(
                AuditLog.organization_id == organization_id,
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
            )
            .group_by(AuditLog.category)
            .all()
        )

        # Failed events
        failed_events = (
            self.db.query(func.count(AuditLog.id))
            .filter(
                AuditLog.organization_id == organization_id,
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
                AuditLog.status == "failure",
            )
            .scalar()
        )

        # Top users by activity
        top_users = (
            self.db.query(
                AuditLog.user_id,
                AuditLog.username,
                func.count(AuditLog.id).label("event_count"),
            )
            .filter(
                AuditLog.organization_id == organization_id,
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
                AuditLog.user_id.isnot(None),
            )
            .group_by(AuditLog.user_id, AuditLog.username)
            .order_by(desc("event_count"))
            .limit(10)
            .all()
        )

        # Sensitive actions
        sensitive_actions = (
            self.db.query(func.count(AuditLog.id))
            .filter(
                AuditLog.organization_id == organization_id,
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
                AuditLog.sensitivity_level.in_(["sensitive", "confidential"]),
            )
            .scalar()
        )

        return {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "total_events": total_events,
            "failed_events": failed_events,
            "sensitive_actions": sensitive_actions,
            "events_by_category": {category: count for category, count in events_by_category},
            "top_users": [
                {"user_id": str(user_id), "username": username, "event_count": count}
                for user_id, username, count in top_users
            ],
        }

    # ============================================================================
    # Retention Management
    # ============================================================================

    async def cleanup_old_logs(self):
        """
        Clean up old audit logs based on retention policies
        Should be run as a scheduled job
        """
        retention_policies = self.db.query(AuditLogRetention).all()

        cleanup_results = []

        for policy in retention_policies:
            cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_days)

            if policy.log_type == "audit_logs":
                deleted = (
                    self.db.query(AuditLog)
                    .filter(
                        and_(
                            AuditLog.timestamp < cutoff_date,
                            or_(
                                policy.organization_id.is_(None),
                                AuditLog.organization_id == policy.organization_id,
                            ),
                        )
                    )
                    .delete()
                )

            elif policy.log_type == "data_access_logs":
                deleted = (
                    self.db.query(DataAccessLog)
                    .filter(
                        and_(
                            DataAccessLog.timestamp < cutoff_date,
                            or_(
                                policy.organization_id.is_(None),
                                DataAccessLog.organization_id == policy.organization_id,
                            ),
                        )
                    )
                    .delete()
                )

            elif policy.log_type == "compliance_events":
                # Never delete compliance events automatically, only archive
                deleted = 0

            policy.last_cleanup_at = datetime.utcnow()
            policy.records_deleted += deleted

            cleanup_results.append(
                {
                    "log_type": policy.log_type,
                    "organization_id": (
                        str(policy.organization_id) if policy.organization_id else "system"
                    ),
                    "records_deleted": deleted,
                    "cutoff_date": cutoff_date.isoformat(),
                }
            )

        self.db.commit()

        return cleanup_results
