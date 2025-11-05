"""
Model Management API Routes
Endpoints for model performance, feedback, and version management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.feedback_loop import FeedbackCollector, FeedbackAnalyzer
from ml.monitoring.model_performance import ModelPerformanceMonitor, AlertManager
from ml.models.prompt_templates import get_optimization_tracker


router = APIRouter(prefix="/api/models", tags=["models"])


# Request/Response Models
class FeedbackSubmission(BaseModel):
    result_id: uuid.UUID
    rating: str  # 'positive', 'negative', 'neutral'
    corrections: Optional[dict] = None
    comments: Optional[str] = None
    specific_issues: Optional[List[str]] = None


class ModelVersionInfo(BaseModel):
    version: str
    name: str
    description: str
    is_active: bool
    performance_metrics: dict


# ============================================================================
# Model Performance Endpoints
# ============================================================================


@router.get("/performance")
async def get_model_performance(
    model_version: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get model performance metrics

    Query Parameters:
    - model_version: Specific model version
    - task_type: Task type filter
    - days: Time window in days
    """
    monitor = ModelPerformanceMonitor(db)

    if model_version and task_type:
        metrics = monitor.calculate_accuracy_metrics(
            model_version, task_type, timedelta(days=days)
        )
    else:
        metrics = monitor.get_success_metrics_summary(timedelta(days=days))

    return {
        "metrics": metrics,
        "time_window_days": days,
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/performance/drift")
async def check_model_drift(
    model_version: str = Query(...),
    task_type: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Check for model drift

    Returns drift detection results
    """
    monitor = ModelPerformanceMonitor(db)

    drift_results = monitor.detect_drift(
        model_version,
        task_type,
        baseline_window=timedelta(days=30),
        current_window=timedelta(days=7),
    )

    return drift_results


@router.get("/performance/alerts")
async def get_performance_alerts(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get active performance alerts
    """
    monitor = ModelPerformanceMonitor(db)
    alert_manager = AlertManager()

    # Get current and baseline metrics
    current = monitor.get_success_metrics_summary(timedelta(days=7))
    baseline = monitor.get_success_metrics_summary(timedelta(days=30))

    alerts = alert_manager.check_alerts(current, baseline)

    return {
        "alerts": alerts,
        "alert_count": len(alerts),
        "checked_at": datetime.utcnow().isoformat(),
    }


# ============================================================================
# Feedback Endpoints
# ============================================================================


@router.post("/feedback")
async def submit_feedback(
    feedback: FeedbackSubmission,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submit feedback on AI output

    Request body:
    {
        "result_id": "uuid",
        "rating": "positive|negative|neutral",
        "corrections": {...},  # Optional corrected output
        "comments": "text",    # Optional comments
        "specific_issues": ["issue1", "issue2"]  # Optional issue list
    }
    """
    collector = FeedbackCollector(db)

    result = collector.submit_feedback(
        result_id=feedback.result_id,
        user_id=current_user.id,
        rating=feedback.rating,
        corrections=feedback.corrections,
        comments=feedback.comments,
        specific_issues=feedback.specific_issues,
    )

    return result


@router.get("/feedback/summary")
async def get_feedback_summary(
    document_type: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get feedback summary statistics
    """
    collector = FeedbackCollector(db)

    summary = collector.get_feedback_summary(
        document_type=document_type, task_type=task_type, time_window_days=days
    )

    return summary


@router.get("/feedback/improvements")
async def get_improvement_opportunities(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get identified improvement opportunities based on feedback
    """
    analyzer = FeedbackAnalyzer(db)

    opportunities = analyzer.identify_improvement_opportunities()

    return {"opportunities": opportunities, "count": len(opportunities)}


@router.get("/feedback/retraining-needed")
async def check_retraining_needed(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Check if model retraining is recommended
    """
    collector = FeedbackCollector(db)

    should_retrain = collector.should_trigger_retraining()

    summary = collector.get_feedback_summary(time_window_days=30)

    return {
        "retraining_recommended": should_retrain,
        "reason": (
            "High negative feedback rate or sufficient corrections"
            if should_retrain
            else None
        ),
        "feedback_summary": summary,
    }


# ============================================================================
# Model Version Management
# ============================================================================


@router.get("/versions")
async def list_model_versions(current_user: User = Depends(get_current_user)):
    """
    List available model versions
    """
    # This would query a model registry
    # For now, return hardcoded versions

    versions = [
        {
            "version": "1.0.0",
            "name": "Base Model",
            "description": "Initial production model",
            "is_active": False,
            "deployed_at": "2024-01-01T00:00:00Z",
        },
        {
            "version": "1.1.0",
            "name": "Fine-tuned v1",
            "description": "First fine-tuning iteration",
            "is_active": True,
            "deployed_at": "2024-02-01T00:00:00Z",
        },
    ]

    return {"versions": versions}


@router.post("/versions/{version}/activate")
async def activate_model_version(
    version: str, current_user: User = Depends(get_current_user)
):
    """
    Activate a specific model version

    Requires admin permissions
    """
    # TODO: Check admin permissions

    # TODO: Update active model version in config

    return {
        "message": f"Model version {version} activated",
        "version": version,
        "activated_at": datetime.utcnow().isoformat(),
    }


@router.get("/versions/compare")
async def compare_model_versions(
    version_a: str = Query(...),
    version_b: str = Query(...),
    metric: str = Query("accuracy"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Compare performance between two model versions
    """
    monitor = ModelPerformanceMonitor(db)

    # Get metrics for both versions
    metrics_a = monitor.calculate_accuracy_metrics(
        version_a, "summary", timedelta(days=30)  # Default task
    )

    metrics_b = monitor.calculate_accuracy_metrics(
        version_b, "summary", timedelta(days=30)
    )

    # Calculate difference
    diff = {}
    for key in metrics_a.keys():
        if isinstance(metrics_a[key], (int, float)) and key in metrics_b:
            diff[key] = metrics_b[key] - metrics_a[key]

    return {
        "version_a": {"version": version_a, "metrics": metrics_a},
        "version_b": {"version": version_b, "metrics": metrics_b},
        "difference": diff,
    }


# ============================================================================
# Prompt Performance
# ============================================================================


@router.get("/prompts/performance")
async def get_prompt_performance(
    template_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """
    Get prompt template performance metrics
    """
    tracker = get_optimization_tracker()

    if template_id:
        performance = tracker.get_template_performance(template_id)
        return {"template_id": template_id, "performance": performance}
    else:
        # Return all templates
        from ml.models.prompt_templates import get_prompt_library

        library = get_prompt_library()
        templates = library.list_templates()

        return {"templates": templates}


@router.get("/prompts/compare")
async def compare_prompts(
    template_ids: List[str] = Query(...), current_user: User = Depends(get_current_user)
):
    """
    Compare performance across multiple prompt templates
    """
    tracker = get_optimization_tracker()

    comparison = tracker.compare_templates(template_ids)

    return comparison


# ============================================================================
# Cost Analytics
# ============================================================================


@router.get("/costs/summary")
async def get_cost_summary(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get AI cost summary
    """
    monitor = ModelPerformanceMonitor(db)

    metrics = monitor.get_success_metrics_summary(timedelta(days=days))

    # Add cost breakdown
    # This would query actual cost data
    cost_summary = {
        "total_cost": 1250.50,  # Example
        "cost_per_document": 0.15,
        "cost_by_model": {"gpt-4": 850.30, "gpt-3.5-turbo": 200.20, "claude-2": 200.00},
        "cost_trend": "decreasing",  # or "increasing", "stable"
        "savings_from_caching": 125.50,
    }

    return {**cost_summary, "time_window_days": days}
