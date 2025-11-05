"""
Model Performance Monitoring
Track model accuracy, drift, and success metrics
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from sqlalchemy.orm import Session
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.app.core.database import SessionLocal
from backend.app.models.document import ProcessingResult


class ModelPerformanceMonitor:
    """Monitor AI model performance over time"""

    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self.metrics_cache = {}

    def track_prediction(
        self,
        model_version: str,
        task_type: str,
        ground_truth: Any,
        prediction: Any,
        confidence: float,
        latency: float,
        cost: float
    ):
        """Track a single prediction for analysis"""
        # Store in metrics cache
        key = f"{model_version}_{task_type}"
        if key not in self.metrics_cache:
            self.metrics_cache[key] = []

        self.metrics_cache[key].append({
            "timestamp": datetime.utcnow(),
            "ground_truth": ground_truth,
            "prediction": prediction,
            "confidence": confidence,
            "latency": latency,
            "cost": cost,
            "correct": self._is_correct(ground_truth, prediction, task_type)
        })

    def _is_correct(self, ground_truth: Any, prediction: Any, task_type: str) -> bool:
        """Determine if prediction is correct"""
        if task_type == "action_items":
            # Compare action item lists
            return self._compare_action_items(ground_truth, prediction)
        elif task_type == "entities":
            return self._compare_entities(ground_truth, prediction)
        else:
            # Simple string comparison for summaries
            return str(ground_truth).lower() == str(prediction).lower()

    def _compare_action_items(self, truth: List, pred: List) -> bool:
        """Compare action item lists with fuzzy matching"""
        if len(truth) != len(pred):
            return False
        # Simplified - in production use better matching
        return len(truth) == len(pred)

    def _compare_entities(self, truth: Dict, pred: Dict) -> bool:
        """Compare entity dictionaries"""
        return set(truth.keys()) == set(pred.keys())

    def calculate_accuracy_metrics(
        self,
        model_version: str,
        task_type: str,
        time_window: timedelta = timedelta(days=7)
    ) -> Dict[str, float]:
        """Calculate accuracy metrics for a model"""
        key = f"{model_version}_{task_type}"
        if key not in self.metrics_cache:
            return {}

        cutoff = datetime.utcnow() - time_window
        recent_metrics = [
            m for m in self.metrics_cache[key]
            if m["timestamp"] >= cutoff
        ]

        if not recent_metrics:
            return {}

        correct = sum(1 for m in recent_metrics if m["correct"])
        total = len(recent_metrics)

        confidences = [m["confidence"] for m in recent_metrics]
        latencies = [m["latency"] for m in recent_metrics]
        costs = [m["cost"] for m in recent_metrics]

        return {
            "accuracy": correct / total,
            "total_predictions": total,
            "avg_confidence": np.mean(confidences),
            "avg_latency": np.mean(latencies),
            "avg_cost": np.mean(costs),
            "total_cost": sum(costs)
        }

    def detect_drift(
        self,
        model_version: str,
        task_type: str,
        baseline_window: timedelta = timedelta(days=30),
        current_window: timedelta = timedelta(days=7),
        threshold: float = 0.05
    ) -> Dict[str, Any]:
        """Detect model drift"""
        baseline_metrics = self.calculate_accuracy_metrics(
            model_version, task_type, baseline_window
        )
        current_metrics = self.calculate_accuracy_metrics(
            model_version, task_type, current_window
        )

        if not baseline_metrics or not current_metrics:
            return {"drift_detected": False}

        accuracy_drift = abs(
            baseline_metrics["accuracy"] - current_metrics["accuracy"]
        )

        drift_detected = accuracy_drift > threshold

        return {
            "drift_detected": drift_detected,
            "accuracy_drift": accuracy_drift,
            "baseline_accuracy": baseline_metrics["accuracy"],
            "current_accuracy": current_metrics["accuracy"],
            "threshold": threshold
        }

    def get_success_metrics_summary(
        self,
        time_window: timedelta = timedelta(days=30)
    ) -> Dict[str, Any]:
        """Get overall success metrics"""
        cutoff = datetime.utcnow() - time_window

        # Query processing results with feedback
        results = self.db.query(ProcessingResult).filter(
            ProcessingResult.created_at >= cutoff
        ).all()

        total = len(results)
        if total == 0:
            return {}

        successful = sum(1 for r in results if r.status == "completed")
        with_feedback = sum(
            1 for r in results
            if r.result_data and "feedback" in r.result_data
        )

        positive_feedback = sum(
            1 for r in results
            if r.result_data and r.result_data.get("feedback", {}).get("rating") == "positive"
        )

        return {
            "total_documents": total,
            "success_rate": successful / total,
            "feedback_rate": with_feedback / total,
            "positive_feedback_rate": positive_feedback / with_feedback if with_feedback > 0 else 0,
            "time_window_days": time_window.days
        }


class AlertManager:
    """Manage alerts for model performance degradation"""

    def __init__(self):
        self.alert_thresholds = {
            "accuracy_drop": 0.10,  # 10% drop triggers alert
            "latency_increase": 2.0,  # 2x increase
            "cost_increase": 1.5,  # 50% increase
            "error_rate": 0.05  # 5% error rate
        }

    def check_alerts(
        self,
        current_metrics: Dict[str, float],
        baseline_metrics: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Check if any alerts should be triggered"""
        alerts = []

        # Check accuracy
        if "accuracy" in current_metrics and "accuracy" in baseline_metrics:
            drop = baseline_metrics["accuracy"] - current_metrics["accuracy"]
            if drop > self.alert_thresholds["accuracy_drop"]:
                alerts.append({
                    "type": "accuracy_degradation",
                    "severity": "high",
                    "message": f"Accuracy dropped by {drop:.1%}",
                    "current": current_metrics["accuracy"],
                    "baseline": baseline_metrics["accuracy"]
                })

        # Check latency
        if "avg_latency" in current_metrics and "avg_latency" in baseline_metrics:
            increase = current_metrics["avg_latency"] / baseline_metrics["avg_latency"]
            if increase > self.alert_thresholds["latency_increase"]:
                alerts.append({
                    "type": "latency_increase",
                    "severity": "medium",
                    "message": f"Latency increased by {(increase-1)*100:.0f}%",
                    "current": current_metrics["avg_latency"],
                    "baseline": baseline_metrics["avg_latency"]
                })

        return alerts
