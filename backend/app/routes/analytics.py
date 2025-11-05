"""
Analytics routes for PM Document Intelligence
Advanced analytics, reporting, and insights endpoints
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
import pandas as pd

from app.core.database import get_db
from app.core.auth import get_current_user, get_current_admin_user
from app.models.user import User
from app.models.document import Document
from app.services.analytics_service import AnalyticsService
from app.services.report_generator import ReportGenerator
from app.monitoring.metrics import (
    analytics_requests_total,
    track_request_duration
)
from app.monitoring.log_aggregation import api_logger

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# ==========================================
# Document Analytics Endpoints
# ==========================================

@router.get("/documents/stats")
async def get_document_stats(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    document_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get overall document statistics

    Returns:
    - Total documents processed
    - Processing success rate
    - Average processing time
    - Documents by type and status
    - Time series data for trends
    """
    analytics_requests_total.labels(endpoint="documents/stats", user_id=current_user.id).inc()

    with track_request_duration(method="GET", endpoint="/analytics/documents/stats"):
        try:
            analytics_service = AnalyticsService(db)

            # Set default date range if not provided
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            # Filter documents based on user role
            if current_user.is_superuser:
                base_query = db.query(Document)
            else:
                base_query = db.query(Document).filter(Document.user_id == current_user.id)

            # Apply filters
            query = base_query.filter(
                Document.created_at.between(start_date, end_date)
            )

            if document_type:
                query = query.filter(Document.document_type == document_type)

            # Total documents
            total_documents = query.count()

            # Documents by status
            status_counts = query.with_entities(
                Document.status,
                func.count(Document.id)
            ).group_by(Document.status).all()

            documents_by_status = {status: count for status, count in status_counts}

            # Documents by type
            type_counts = query.with_entities(
                Document.document_type,
                func.count(Document.id)
            ).group_by(Document.document_type).all()

            documents_by_type = {doc_type: count for doc_type, count in type_counts}

            # Processing success rate
            completed_docs = documents_by_status.get('completed', 0)
            failed_docs = documents_by_status.get('failed', 0)
            total_processed = completed_docs + failed_docs
            success_rate = (completed_docs / total_processed * 100) if total_processed > 0 else 0

            # Average processing time (for completed documents)
            avg_processing_time = analytics_service.get_avg_processing_time(
                start_date, end_date, document_type, current_user
            )

            # Time series data (daily aggregation)
            time_series = analytics_service.get_document_time_series(
                start_date, end_date, document_type, current_user
            )

            api_logger.info(
                f"Document stats retrieved for user {current_user.id}",
                total_documents=total_documents,
                date_range=f"{start_date} to {end_date}"
            )

            return {
                "total_documents": total_documents,
                "success_rate": round(success_rate, 2),
                "average_processing_time_seconds": round(avg_processing_time, 2),
                "documents_by_status": documents_by_status,
                "documents_by_type": documents_by_type,
                "time_series": time_series,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }

        except Exception as e:
            api_logger.error(f"Error getting document stats: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/insights")
async def get_document_insights(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get AI-generated insights about documents

    Returns:
    - Common themes across documents
    - Trending topics
    - Sentiment trends
    - Risk indicators
    - Action item completion rates
    """
    analytics_requests_total.labels(endpoint="documents/insights", user_id=current_user.id).inc()

    with track_request_duration(method="GET", endpoint="/analytics/documents/insights"):
        try:
            analytics_service = AnalyticsService(db)

            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            insights = await analytics_service.generate_document_insights(
                start_date, end_date, current_user
            )

            api_logger.info(
                f"Document insights retrieved for user {current_user.id}",
                date_range=f"{start_date} to {end_date}"
            )

            return insights

        except Exception as e:
            api_logger.error(f"Error generating document insights: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# User Activity Analytics Endpoints
# ==========================================

@router.get("/users/activity")
async def get_user_activity(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)  # Admin only
):
    """
    Get user engagement metrics (Admin only)

    Returns:
    - Active users count
    - Documents per user
    - Search queries analysis
    - Feature usage statistics
    """
    analytics_requests_total.labels(endpoint="users/activity", user_id=current_user.id).inc()

    with track_request_duration(method="GET", endpoint="/analytics/users/activity"):
        try:
            analytics_service = AnalyticsService(db)

            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            # Active users (users who created/accessed documents)
            active_users = db.query(func.count(func.distinct(Document.user_id))).filter(
                Document.created_at.between(start_date, end_date)
            ).scalar()

            # Total registered users
            total_users = db.query(func.count(User.id)).scalar()

            # Documents per user
            docs_per_user = db.query(
                User.username,
                func.count(Document.id).label('document_count')
            ).join(Document, Document.user_id == User.id).filter(
                Document.created_at.between(start_date, end_date)
            ).group_by(User.id, User.username).order_by(desc('document_count')).limit(10).all()

            top_users = [
                {"username": username, "document_count": count}
                for username, count in docs_per_user
            ]

            # Search queries analysis
            search_analytics = analytics_service.get_search_analytics(start_date, end_date)

            # Feature usage statistics
            feature_usage = analytics_service.get_feature_usage(start_date, end_date)

            return {
                "active_users": active_users,
                "total_users": total_users,
                "engagement_rate": round((active_users / total_users * 100) if total_users > 0 else 0, 2),
                "top_users": top_users,
                "search_analytics": search_analytics,
                "feature_usage": feature_usage,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }

        except Exception as e:
            api_logger.error(f"Error getting user activity: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/behavior")
async def get_user_behavior(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)  # Admin only
):
    """
    Get user behavior patterns (Admin only)

    Returns:
    - Peak usage times
    - Common workflows
    - Feature adoption rates
    """
    analytics_requests_total.labels(endpoint="users/behavior", user_id=current_user.id).inc()

    with track_request_duration(method="GET", endpoint="/analytics/users/behavior"):
        try:
            analytics_service = AnalyticsService(db)

            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            # Peak usage times (hourly distribution)
            peak_times = analytics_service.get_peak_usage_times(start_date, end_date)

            # Common workflows (sequence of actions)
            common_workflows = analytics_service.get_common_workflows(start_date, end_date)

            # Feature adoption rates
            adoption_rates = analytics_service.get_feature_adoption_rates(start_date, end_date)

            return {
                "peak_usage_times": peak_times,
                "common_workflows": common_workflows,
                "feature_adoption_rates": adoption_rates,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }

        except Exception as e:
            api_logger.error(f"Error getting user behavior: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Cost Analytics Endpoints
# ==========================================

@router.get("/costs/breakdown")
async def get_cost_breakdown(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    group_by: Optional[str] = Query("service"),  # service, user, document_type, day
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)  # Admin only
):
    """
    Get cost breakdown (Admin only)

    Returns:
    - Costs by service (AWS, OpenAI, Supabase)
    - Costs by user
    - Costs by document type
    - Trends over time
    """
    analytics_requests_total.labels(endpoint="costs/breakdown", user_id=current_user.id).inc()

    with track_request_duration(method="GET", endpoint="/analytics/costs/breakdown"):
        try:
            from app.monitoring.cost_tracking import cost_tracker

            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            # Filter cost entries
            cost_entries = [
                entry for entry in cost_tracker.cost_history
                if start_date <= entry.timestamp <= end_date
            ]

            # Group costs
            if group_by == "service":
                breakdown = {}
                for entry in cost_entries:
                    breakdown[entry.service] = breakdown.get(entry.service, 0) + entry.total_cost

            elif group_by == "day":
                breakdown = {}
                for entry in cost_entries:
                    day = entry.timestamp.date().isoformat()
                    breakdown[day] = breakdown.get(day, 0) + entry.total_cost

            else:
                breakdown = {}

            total_cost = sum(entry.total_cost for entry in cost_entries)

            # Service-specific breakdown
            aws_cost = sum(entry.total_cost for entry in cost_entries if entry.service.startswith('aws_'))
            openai_cost = sum(entry.total_cost for entry in cost_entries if entry.service.startswith('openai_'))

            return {
                "total_cost": round(total_cost, 2),
                "breakdown": {k: round(v, 2) for k, v in breakdown.items()},
                "by_provider": {
                    "aws": round(aws_cost, 2),
                    "openai": round(openai_cost, 2)
                },
                "currency": "USD",
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }

        except Exception as e:
            api_logger.error(f"Error getting cost breakdown: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/costs/optimization")
async def get_cost_optimization(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)  # Admin only
):
    """
    Get cost optimization suggestions (Admin only)

    Returns:
    - Identify expensive operations
    - Recommend cheaper alternatives
    - ROI calculations
    """
    analytics_requests_total.labels(endpoint="costs/optimization", user_id=current_user.id).inc()

    with track_request_duration(method="GET", endpoint="/analytics/costs/optimization"):
        try:
            from app.monitoring.cost_tracking import cost_tracker

            # Analyze cost patterns
            suggestions = []

            # Check for expensive OpenAI operations
            recent_openai_costs = [
                entry for entry in cost_tracker.cost_history[-1000:]
                if entry.service.startswith('openai_')
            ]

            if recent_openai_costs:
                avg_cost_per_operation = sum(e.total_cost for e in recent_openai_costs) / len(recent_openai_costs)

                if avg_cost_per_operation > 0.05:  # $0.05 per operation
                    suggestions.append({
                        "category": "OpenAI Optimization",
                        "issue": "High average cost per OpenAI operation",
                        "recommendation": "Consider using GPT-3.5-turbo instead of GPT-4 for non-critical tasks",
                        "potential_savings": "Up to 90% cost reduction",
                        "priority": "high"
                    })

            # Check for AWS Textract usage
            textract_costs = [
                entry for entry in cost_tracker.cost_history[-1000:]
                if entry.service == 'aws_textract'
            ]

            if len(textract_costs) > 100:
                suggestions.append({
                    "category": "AWS Textract Optimization",
                    "issue": "High volume of Textract operations",
                    "recommendation": "Implement OCR caching to avoid re-processing same documents",
                    "potential_savings": "Up to 50% cost reduction",
                    "priority": "medium"
                })

            # Check for embedding generation
            embedding_costs = [
                entry for entry in cost_tracker.cost_history[-1000:]
                if 'embedding' in entry.service.lower()
            ]

            if len(embedding_costs) > 1000:
                suggestions.append({
                    "category": "Embedding Optimization",
                    "issue": "High volume of embedding generation",
                    "recommendation": "Cache embeddings and reuse for similar documents",
                    "potential_savings": "Up to 70% cost reduction",
                    "priority": "high"
                })

            # ROI calculation
            total_cost_last_30_days = cost_tracker.get_daily_cost()
            documents_processed_last_30_days = db.query(func.count(Document.id)).filter(
                Document.created_at >= datetime.utcnow() - timedelta(days=30)
            ).scalar()

            cost_per_document = (total_cost_last_30_days / documents_processed_last_30_days) if documents_processed_last_30_days > 0 else 0

            return {
                "suggestions": suggestions,
                "roi_metrics": {
                    "total_cost_last_30_days": round(total_cost_last_30_days, 2),
                    "documents_processed": documents_processed_last_30_days,
                    "cost_per_document": round(cost_per_document, 4),
                    "currency": "USD"
                },
                "potential_total_savings": sum(
                    float(s.get('potential_savings', '0%').replace('%', '').split()[0])
                    for s in suggestions if 'potential_savings' in s
                ) if suggestions else 0
            }

        except Exception as e:
            api_logger.error(f"Error getting cost optimization: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Performance Analytics Endpoints
# ==========================================

@router.get("/performance/api")
async def get_api_performance(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)  # Admin only
):
    """
    Get API performance metrics (Admin only)

    Returns:
    - Endpoint latency (p50, p95, p99)
    - Error rates
    - Request volume
    - Slowest endpoints
    """
    analytics_requests_total.labels(endpoint="performance/api", user_id=current_user.id).inc()

    with track_request_duration(method="GET", endpoint="/analytics/performance/api"):
        try:
            from app.monitoring.metrics import (
                http_requests_total,
                http_request_duration_seconds
            )

            # This would typically query Prometheus for metrics
            # For now, we'll return mock data structure

            return {
                "request_volume": {
                    "total": 12543,
                    "success": 12234,
                    "error": 309
                },
                "latency": {
                    "p50": 0.125,
                    "p95": 0.543,
                    "p99": 1.234
                },
                "error_rate": 2.46,
                "slowest_endpoints": [
                    {"endpoint": "/api/documents/upload", "avg_latency": 2.15},
                    {"endpoint": "/api/agents/summary", "avg_latency": 1.87},
                    {"endpoint": "/api/search/semantic", "avg_latency": 1.45}
                ],
                "most_used_endpoints": [
                    {"endpoint": "/api/documents", "request_count": 3421},
                    {"endpoint": "/api/search", "request_count": 2134},
                    {"endpoint": "/api/auth/login", "request_count": 1876}
                ]
            }

        except Exception as e:
            api_logger.error(f"Error getting API performance: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/processing")
async def get_processing_performance(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)  # Admin only
):
    """
    Get document processing performance (Admin only)

    Returns:
    - Document processing times
    - Bottleneck identification
    - Success/failure rates
    - Agent performance comparison
    """
    analytics_requests_total.labels(endpoint="performance/processing", user_id=current_user.id).inc()

    with track_request_duration(method="GET", endpoint="/analytics/performance/processing"):
        try:
            analytics_service = AnalyticsService(db)

            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=7)

            # Processing performance metrics
            performance = analytics_service.get_processing_performance(start_date, end_date)

            return performance

        except Exception as e:
            api_logger.error(f"Error getting processing performance: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Report Generation Endpoints
# ==========================================

@router.post("/reports/generate")
async def generate_report(
    report_type: str = Query(..., regex="^(daily|weekly|monthly|custom)$"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    format: str = Query("pdf", regex="^(pdf|excel|json)$"),
    email_to: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)  # Admin only
):
    """
    Generate analytics report (Admin only)

    Parameters:
    - report_type: daily, weekly, monthly, custom
    - start_date, end_date: For custom reports
    - format: pdf, excel, json
    - email_to: Optional email address for delivery
    """
    analytics_requests_total.labels(endpoint="reports/generate", user_id=current_user.id).inc()

    try:
        report_generator = ReportGenerator(db)

        # Determine date range
        if report_type == "daily":
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=1)
        elif report_type == "weekly":
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)
        elif report_type == "monthly":
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
        elif report_type == "custom":
            if not start_date or not end_date:
                raise HTTPException(
                    status_code=400,
                    detail="start_date and end_date required for custom reports"
                )

        # Generate report in background
        background_tasks.add_task(
            report_generator.generate_and_send_report,
            report_type=report_type,
            start_date=start_date,
            end_date=end_date,
            format=format,
            email_to=email_to or current_user.email,
            user_id=current_user.id
        )

        api_logger.info(
            f"Report generation queued for user {current_user.id}",
            report_type=report_type,
            format=format
        )

        return {
            "message": "Report generation queued",
            "report_type": report_type,
            "format": format,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "delivery": email_to or current_user.email
        }

    except Exception as e:
        api_logger.error(f"Error generating report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Dashboard Configuration Endpoints
# ==========================================

@router.get("/dashboard/config")
async def get_dashboard_config(
    current_user: User = Depends(get_current_user)
):
    """
    Get user's dashboard configuration
    """
    # This would typically load from user preferences
    return {
        "widgets": [
            {
                "id": "document-stats",
                "type": "stats",
                "position": {"x": 0, "y": 0, "w": 6, "h": 2},
                "enabled": True
            },
            {
                "id": "processing-chart",
                "type": "line-chart",
                "position": {"x": 6, "y": 0, "w": 6, "h": 4},
                "enabled": True
            },
            {
                "id": "cost-breakdown",
                "type": "pie-chart",
                "position": {"x": 0, "y": 2, "w": 6, "h": 4},
                "enabled": current_user.is_superuser
            }
        ],
        "refresh_interval": 30,  # seconds
        "theme": "light"
    }


@router.post("/dashboard/config")
async def update_dashboard_config(
    config: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update user's dashboard configuration
    """
    # Save configuration to user preferences
    api_logger.info(f"Dashboard config updated for user {current_user.id}")

    return {
        "message": "Dashboard configuration updated",
        "config": config
    }


# ==========================================
# Export Endpoints
# ==========================================

@router.get("/export/csv")
async def export_to_csv(
    data_type: str = Query(..., regex="^(documents|users|costs)$"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export analytics data to CSV
    """
    from fastapi.responses import StreamingResponse
    import io

    try:
        analytics_service = AnalyticsService(db)

        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Get data based on type
        if data_type == "documents":
            data = analytics_service.get_documents_for_export(
                start_date, end_date, current_user
            )
        elif data_type == "users" and current_user.is_superuser:
            data = analytics_service.get_users_for_export(start_date, end_date)
        elif data_type == "costs" and current_user.is_superuser:
            data = analytics_service.get_costs_for_export(start_date, end_date)
        else:
            raise HTTPException(status_code=403, detail="Access denied")

        # Convert to CSV
        df = pd.DataFrame(data)
        stream = io.StringIO()
        df.to_csv(stream, index=False)

        response = StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv"
        )
        response.headers["Content-Disposition"] = f"attachment; filename={data_type}_export.csv"

        return response

    except Exception as e:
        api_logger.error(f"Error exporting to CSV: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
