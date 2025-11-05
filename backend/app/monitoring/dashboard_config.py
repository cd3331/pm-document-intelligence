"""
Grafana dashboard configurations
Export these as JSON files for version control
"""

import json


# System Overview Dashboard
SYSTEM_OVERVIEW_DASHBOARD = {
    "dashboard": {
        "title": "PM Document Intelligence - System Overview",
        "tags": ["overview", "system"],
        "timezone": "browser",
        "schemaVersion": 16,
        "version": 0,
        "refresh": "30s",
        "panels": [
            {
                "id": 1,
                "title": "Request Rate",
                "targets": [
                    {
                        "expr": "rate(http_requests_total[5m])",
                        "legendFormat": "{{method}} {{endpoint}}"
                    }
                ],
                "type": "graph"
            },
            {
                "id": 2,
                "title": "Error Rate",
                "targets": [
                    {
                        "expr": "rate(http_requests_total{status_code=~\"5..\"}[5m])",
                        "legendFormat": "Errors"
                    }
                ],
                "type": "graph"
            },
            {
                "id": 3,
                "title": "Response Time (P95)",
                "targets": [
                    {
                        "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
                        "legendFormat": "p95"
                    }
                ],
                "type": "graph"
            },
            {
                "id": 4,
                "title": "CPU Usage",
                "targets": [
                    {
                        "expr": "system_cpu_usage_percent",
                        "legendFormat": "CPU %"
                    }
                ],
                "type": "graph"
            },
            {
                "id": 5,
                "title": "Memory Usage",
                "targets": [
                    {
                        "expr": "system_memory_usage_bytes",
                        "legendFormat": "Memory"
                    }
                ],
                "type": "graph"
            }
        ]
    }
}

# Document Processing Dashboard
DOCUMENT_PROCESSING_DASHBOARD = {
    "dashboard": {
        "title": "Document Processing Metrics",
        "tags": ["documents", "processing"],
        "panels": [
            {
                "id": 1,
                "title": "Documents Uploaded",
                "targets": [
                    {
                        "expr": "rate(documents_uploaded_total[5m])",
                        "legendFormat": "{{document_type}}"
                    }
                ]
            },
            {
                "id": 2,
                "title": "Processing Duration",
                "targets": [
                    {
                        "expr": "histogram_quantile(0.95, rate(document_processing_duration_seconds_bucket[5m]))",
                        "legendFormat": "{{processing_stage}}"
                    }
                ]
            },
            {
                "id": 3,
                "title": "Failed Documents",
                "targets": [
                    {
                        "expr": "rate(documents_failed_total[5m])",
                        "legendFormat": "{{error_type}}"
                    }
                ]
            }
        ]
    }
}

# Cost Tracking Dashboard
COST_DASHBOARD = {
    "dashboard": {
        "title": "Cost Tracking",
        "tags": ["cost", "billing"],
        "panels": [
            {
                "id": 1,
                "title": "Daily Cost",
                "targets": [
                    {
                        "expr": "total_cost_usd_daily",
                        "legendFormat": "Total Daily Cost"
                    }
                ]
            },
            {
                "id": 2,
                "title": "AWS Costs by Service",
                "targets": [
                    {
                        "expr": "rate(aws_cost_usd_total[1d])",
                        "legendFormat": "{{service}}"
                    }
                ]
            },
            {
                "id": 3,
                "title": "OpenAI Costs",
                "targets": [
                    {
                        "expr": "rate(openai_cost_usd_total[1d])",
                        "legendFormat": "{{model}}"
                    }
                ]
            }
        ]
    }
}


def export_dashboards():
    """Export all dashboards as JSON files"""
    dashboards = {
        "system_overview": SYSTEM_OVERVIEW_DASHBOARD,
        "document_processing": DOCUMENT_PROCESSING_DASHBOARD,
        "cost_tracking": COST_DASHBOARD
    }

    for name, config in dashboards.items():
        with open(f"dashboards/{name}.json", "w") as f:
            json.dump(config, f, indent=2)


if __name__ == "__main__":
    export_dashboards()
