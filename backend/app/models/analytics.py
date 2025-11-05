"""
Analytics Models for PM Document Intelligence
Database models for storing aggregated analytics data
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base


class AnalyticsSnapshot(Base):
    """
    Stores daily snapshots of analytics metrics
    Reduces need to recompute historical analytics
    """

    __tablename__ = "analytics_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(Date, nullable=False, index=True)
    metric_type = Column(
        String(50), nullable=False, index=True
    )  # documents, users, costs, performance
    data = Column(JSONB, nullable=False)  # Flexible JSON storage for metrics
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Composite index for efficient querying
    __table_args__ = (Index("idx_snapshot_date_type", "date", "metric_type"),)

    def __repr__(self):
        return f"<AnalyticsSnapshot(date={self.date}, type={self.metric_type})>"


class CachedMetric(Base):
    """
    Stores cached expensive analytics queries
    Improves dashboard load times
    """

    __tablename__ = "cached_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_key = Column(String(255), unique=True, nullable=False, index=True)
    metric_value = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)

    def __repr__(self):
        return f"<CachedMetric(key={self.metric_key})>"

    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return datetime.utcnow() > self.expires_at


class ReportSchedule(Base):
    """
    Stores report generation schedules
    """

    __tablename__ = "report_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    report_type = Column(String(50), nullable=False)  # daily, weekly, monthly
    format = Column(String(20), nullable=False)  # pdf, excel, json
    frequency = Column(String(50), nullable=False)  # daily, weekly, monthly
    email_to = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_generated_at = Column(DateTime)
    next_scheduled_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ReportSchedule(type={self.report_type}, frequency={self.frequency})>"


class UserDashboardConfig(Base):
    """
    Stores user-specific dashboard configurations
    Allows users to customize their analytics dashboard
    """

    __tablename__ = "user_dashboard_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    widgets = Column(JSONB, nullable=False, default=list)  # List of widget configurations
    layout = Column(JSONB, nullable=False, default=dict)  # Grid layout configuration
    theme = Column(String(20), default="light")  # light, dark
    refresh_interval = Column(Integer, default=30)  # seconds
    date_range_default = Column(String(20), default="30d")  # Default date range
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<UserDashboardConfig(user_id={self.user_id})>"


class AnalyticsEvent(Base):
    """
    Stores analytics events for detailed tracking
    Used for behavioral analytics and audit trails
    """

    __tablename__ = "analytics_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), index=True)
    event_type = Column(
        String(100), nullable=False, index=True
    )  # page_view, button_click, feature_usage
    event_name = Column(String(255), nullable=False)
    properties = Column(JSONB, default=dict)  # Additional event properties
    session_id = Column(String(255), index=True)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Composite index for common queries
    __table_args__ = (
        Index("idx_event_user_timestamp", "user_id", "timestamp"),
        Index("idx_event_type_timestamp", "event_type", "timestamp"),
    )

    def __repr__(self):
        return f"<AnalyticsEvent(type={self.event_type}, name={self.event_name})>"


class MetricAlert(Base):
    """
    Stores metric alert configurations
    Triggers notifications when metrics exceed thresholds
    """

    __tablename__ = "metric_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    metric_type = Column(String(100), nullable=False, index=True)  # documents, costs, performance
    metric_key = Column(String(255), nullable=False)
    condition = Column(String(20), nullable=False)  # gt, lt, eq, gte, lte
    threshold = Column(Float, nullable=False)
    notification_channels = Column(JSONB, default=list)  # email, slack, pagerduty
    recipients = Column(JSONB, default=list)
    is_active = Column(Boolean, default=True, nullable=False)
    last_triggered_at = Column(DateTime)
    cooldown_minutes = Column(Integer, default=60)  # Minimum time between alerts
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<MetricAlert(name={self.name}, metric={self.metric_key})>"

    def should_trigger(self, current_value: float) -> bool:
        """Check if alert should trigger based on current value"""
        if not self.is_active:
            return False

        # Check cooldown
        if self.last_triggered_at:
            minutes_since_last = (datetime.utcnow() - self.last_triggered_at).total_seconds() / 60
            if minutes_since_last < self.cooldown_minutes:
                return False

        # Check condition
        if self.condition == "gt":
            return current_value > self.threshold
        elif self.condition == "lt":
            return current_value < self.threshold
        elif self.condition == "eq":
            return current_value == self.threshold
        elif self.condition == "gte":
            return current_value >= self.threshold
        elif self.condition == "lte":
            return current_value <= self.threshold

        return False


class ExportLog(Base):
    """
    Logs data exports for audit and tracking
    """

    __tablename__ = "export_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    export_type = Column(String(50), nullable=False)  # csv, pdf, excel
    data_type = Column(String(50), nullable=False)  # documents, users, costs, reports
    filters = Column(JSONB, default=dict)  # Filters applied to export
    row_count = Column(Integer)
    file_size_bytes = Column(Integer)
    status = Column(String(20), default="pending")  # pending, completed, failed
    error_message = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime)

    __table_args__ = (Index("idx_export_user_created", "user_id", "created_at"),)

    def __repr__(self):
        return f"<ExportLog(type={self.export_type}, data={self.data_type}, status={self.status})>"
