"""
Alert definitions and delivery for monitoring system
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json
import os
from datetime import datetime


class AlertSeverity(Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert delivery channels"""

    EMAIL = "email"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    WEBHOOK = "webhook"


@dataclass
class Alert:
    """Alert definition"""

    name: str
    severity: AlertSeverity
    message: str
    metric_name: str
    threshold: float
    comparison: str  # gt, lt, gte, lte, eq
    duration: str  # e.g., "5m", "1h"
    channels: List[AlertChannel]
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# Alert Definitions
# ============================================================================

# High error rate alert
HIGH_ERROR_RATE = Alert(
    name="high_error_rate",
    severity=AlertSeverity.CRITICAL,
    message="Error rate exceeded 5% over the last 5 minutes",
    metric_name="http_requests_total",
    threshold=0.05,
    comparison="gt",
    duration="5m",
    channels=[AlertChannel.SLACK, AlertChannel.PAGERDUTY],
)

# Slow response time alert
SLOW_RESPONSE_TIME = Alert(
    name="slow_response_time",
    severity=AlertSeverity.WARNING,
    message="P95 response time exceeded 2 seconds",
    metric_name="http_request_duration_seconds",
    threshold=2.0,
    comparison="gt",
    duration="10m",
    channels=[AlertChannel.SLACK],
)

# AWS service failure alert
AWS_SERVICE_FAILURE = Alert(
    name="aws_service_failure",
    severity=AlertSeverity.ERROR,
    message="AWS service calls failing",
    metric_name="aws_api_calls_total",
    threshold=0.1,  # 10% failure rate
    comparison="gt",
    duration="5m",
    channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
)

# Database connection alert
DATABASE_CONNECTION_ERROR = Alert(
    name="database_connection_error",
    severity=AlertSeverity.CRITICAL,
    message="Database connection issues detected",
    metric_name="db_queries_total",
    threshold=0.05,
    comparison="gt",
    duration="2m",
    channels=[AlertChannel.SLACK, AlertChannel.PAGERDUTY],
)

# Cost threshold alert
COST_THRESHOLD_EXCEEDED = Alert(
    name="cost_threshold_exceeded",
    severity=AlertSeverity.WARNING,
    message="Daily cost threshold exceeded $100",
    metric_name="total_cost_usd_daily",
    threshold=100.0,
    comparison="gt",
    duration="1h",
    channels=[AlertChannel.EMAIL, AlertChannel.SLACK],
)

# Disk space alert
DISK_SPACE_LOW = Alert(
    name="disk_space_low",
    severity=AlertSeverity.WARNING,
    message="Disk space below 10%",
    metric_name="system_disk_usage_bytes",
    threshold=0.9,  # 90% used
    comparison="gt",
    duration="5m",
    channels=[AlertChannel.SLACK],
)

# Memory usage alert
MEMORY_USAGE_HIGH = Alert(
    name="memory_usage_high",
    severity=AlertSeverity.WARNING,
    message="Memory usage above 85%",
    metric_name="system_memory_usage_bytes",
    threshold=0.85,
    comparison="gt",
    duration="10m",
    channels=[AlertChannel.SLACK],
)

# Document processing failure alert
DOCUMENT_PROCESSING_FAILURES = Alert(
    name="document_processing_failures",
    severity=AlertSeverity.ERROR,
    message="High rate of document processing failures",
    metric_name="documents_failed_total",
    threshold=10,  # More than 10 failures
    comparison="gt",
    duration="15m",
    channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
)


# All alert definitions
ALL_ALERTS = [
    HIGH_ERROR_RATE,
    SLOW_RESPONSE_TIME,
    AWS_SERVICE_FAILURE,
    DATABASE_CONNECTION_ERROR,
    COST_THRESHOLD_EXCEEDED,
    DISK_SPACE_LOW,
    MEMORY_USAGE_HIGH,
    DOCUMENT_PROCESSING_FAILURES,
]


# ============================================================================
# Alert Delivery
# ============================================================================


class AlertDelivery:
    """Handles alert delivery to various channels"""

    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.pagerduty_api_key = os.getenv("PAGERDUTY_API_KEY")
        self.pagerduty_service_id = os.getenv("PAGERDUTY_SERVICE_ID")

    def send_alert(self, alert: Alert, current_value: float):
        """Send alert through all configured channels"""
        for channel in alert.channels:
            try:
                if channel == AlertChannel.EMAIL:
                    self.send_email(alert, current_value)
                elif channel == AlertChannel.SLACK:
                    self.send_slack(alert, current_value)
                elif channel == AlertChannel.PAGERDUTY:
                    self.send_pagerduty(alert, current_value)
            except Exception as e:
                print(f"Failed to send alert via {channel.value}: {e}")

    def send_email(self, alert: Alert, current_value: float):
        """Send alert via email"""
        if not self.smtp_user or not self.smtp_password:
            print("SMTP credentials not configured")
            return

        recipients = os.getenv("ALERT_EMAIL_RECIPIENTS", "").split(",")
        if not recipients:
            return

        msg = MIMEMultipart()
        msg["From"] = self.smtp_user
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = f"[{alert.severity.value.upper()}] {alert.name}"

        body = f"""
Alert: {alert.name}
Severity: {alert.severity.value}
Message: {alert.message}

Current Value: {current_value}
Threshold: {alert.threshold}
Comparison: {alert.comparison}

Metric: {alert.metric_name}
Duration: {alert.duration}

Timestamp: {datetime.utcnow().isoformat()}

This is an automated alert from PM Document Intelligence monitoring system.
        """

        msg.attach(MIMEText(body, "plain"))

        try:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()
            print(f"Alert email sent: {alert.name}")
        except Exception as e:
            print(f"Failed to send email: {e}")

    def send_slack(self, alert: Alert, current_value: float):
        """Send alert to Slack"""
        if not self.slack_webhook_url:
            print("Slack webhook URL not configured")
            return

        color_map = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ff9900",
            AlertSeverity.ERROR: "#ff4444",
            AlertSeverity.CRITICAL: "#cc0000",
        }

        payload = {
            "attachments": [
                {
                    "fallback": f"{alert.severity.value.upper()}: {alert.name}",
                    "color": color_map.get(alert.severity, "#808080"),
                    "title": f":rotating_light: {alert.name}",
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity.value.upper(),
                            "short": True,
                        },
                        {
                            "title": "Current Value",
                            "value": f"{current_value:.2f}",
                            "short": True,
                        },
                        {
                            "title": "Threshold",
                            "value": f"{alert.threshold}",
                            "short": True,
                        },
                        {"title": "Metric", "value": alert.metric_name, "short": True},
                    ],
                    "footer": "PM Document Intelligence Monitoring",
                    "ts": int(datetime.utcnow().timestamp()),
                }
            ]
        }

        try:
            response = requests.post(
                self.slack_webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            print(f"Alert sent to Slack: {alert.name}")
        except Exception as e:
            print(f"Failed to send Slack alert: {e}")

    def send_pagerduty(self, alert: Alert, current_value: float):
        """Send alert to PagerDuty"""
        if not self.pagerduty_api_key or not self.pagerduty_service_id:
            print("PagerDuty credentials not configured")
            return

        severity_map = {
            AlertSeverity.INFO: "info",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.ERROR: "error",
            AlertSeverity.CRITICAL: "critical",
        }

        payload = {
            "routing_key": self.pagerduty_api_key,
            "event_action": "trigger",
            "payload": {
                "summary": alert.message,
                "severity": severity_map.get(alert.severity, "error"),
                "source": "pm-document-intelligence",
                "custom_details": {
                    "alert_name": alert.name,
                    "metric": alert.metric_name,
                    "current_value": current_value,
                    "threshold": alert.threshold,
                    "comparison": alert.comparison,
                },
            },
        }

        try:
            response = requests.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            print(f"Alert sent to PagerDuty: {alert.name}")
        except Exception as e:
            print(f"Failed to send PagerDuty alert: {e}")


# ============================================================================
# Prometheus AlertManager Rules
# ============================================================================


def generate_prometheus_rules() -> str:
    """Generate Prometheus AlertManager rules YAML"""
    rules = {"groups": [{"name": "pm_document_intelligence", "rules": []}]}

    for alert in ALL_ALERTS:
        rule = {
            "alert": alert.name,
            "expr": f"{alert.metric_name} {alert.comparison} {alert.threshold}",
            "for": alert.duration,
            "labels": {"severity": alert.severity.value},
            "annotations": {
                "summary": alert.message,
                "description": f"{alert.metric_name} is {alert.comparison} {alert.threshold}",
            },
        }
        rules["groups"][0]["rules"].append(rule)

    import yaml

    return yaml.dump(rules, default_flow_style=False)


# ============================================================================
# Alert Runbooks
# ============================================================================

RUNBOOKS = {
    "high_error_rate": """
# High Error Rate Runbook

## Problem
Error rate has exceeded 5% over the last 5 minutes.

## Impact
Users are experiencing failures when using the application.

## Investigation Steps
1. Check application logs for error patterns
2. Check recent deployments
3. Review infrastructure metrics (CPU, memory, disk)
4. Check external service status (AWS, OpenAI)

## Resolution Steps
1. Identify root cause from logs
2. Roll back recent changes if applicable
3. Scale infrastructure if resource constrained
4. Contact service providers if external issue

## Prevention
- Implement better error handling
- Add circuit breakers for external services
- Increase test coverage
    """,
    "slow_response_time": """
# Slow Response Time Runbook

## Problem
P95 response time has exceeded 2 seconds.

## Impact
Users experiencing slow application performance.

## Investigation Steps
1. Check slow query logs
2. Review APM traces for bottlenecks
3. Check database connection pool
4. Review external API latencies

## Resolution Steps
1. Optimize slow queries
2. Add database indexes
3. Implement caching
4. Scale application instances

## Prevention
- Regular performance testing
- Query optimization reviews
- Implement proper caching strategy
    """,
    "database_connection_error": """
# Database Connection Error Runbook

## Problem
Database connection errors detected.

## Impact
CRITICAL - Application cannot access database.

## Investigation Steps
1. Check database server status
2. Review connection pool settings
3. Check network connectivity
4. Review database logs

## Resolution Steps
1. Restart database if crashed
2. Adjust connection pool settings
3. Fix network issues
4. Failover to replica if available

## Prevention
- Implement connection pooling
- Set up database monitoring
- Configure automatic failover
- Regular database maintenance
    """,
}


def get_runbook(alert_name: str) -> str:
    """Get runbook for alert"""
    return RUNBOOKS.get(alert_name, "No runbook available for this alert.")
