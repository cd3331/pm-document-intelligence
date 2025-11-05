"""
Feedback Loop Service
Collect user feedback on AI outputs for continuous improvement
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.models.document import ProcessingResult, Document
from app.models.user import User


class FeedbackCollector:
    """Collect and store user feedback on AI outputs"""

    def __init__(self, db: Session):
        self.db = db

    def submit_feedback(
        self,
        result_id: uuid.UUID,
        user_id: uuid.UUID,
        rating: str,  # 'positive', 'negative', 'neutral'
        corrections: Optional[Dict[str, Any]] = None,
        comments: Optional[str] = None,
        specific_issues: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Submit feedback on a processing result

        Args:
            result_id: Processing result UUID
            user_id: User providing feedback
            rating: Overall rating
            corrections: Corrected outputs
            comments: Free-form comments
            specific_issues: List of issues (e.g., ['missing_action_items', 'wrong_summary'])

        Returns:
            Feedback record
        """
        result = self.db.query(ProcessingResult).filter(
            ProcessingResult.id == result_id
        ).first()

        if not result:
            raise ValueError(f"Result {result_id} not found")

        # Update result with feedback
        if not result.result_data:
            result.result_data = {}

        result.result_data["feedback"] = {
            "user_id": str(user_id),
            "rating": rating,
            "corrections": corrections,
            "comments": comments,
            "specific_issues": specific_issues or [],
            "submitted_at": datetime.utcnow().isoformat()
        }

        self.db.commit()

        return {
            "result_id": str(result_id),
            "feedback_recorded": True,
            "rating": rating
        }

    def get_feedback_summary(
        self,
        document_type: Optional[str] = None,
        task_type: Optional[str] = None,
        time_window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get summary of feedback

        Args:
            document_type: Filter by document type
            task_type: Filter by task (summary, action_items, etc.)
            time_window_days: Days to look back

        Returns:
            Feedback statistics
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=time_window_days)

        query = self.db.query(ProcessingResult).filter(
            ProcessingResult.created_at >= cutoff
        )

        if document_type:
            query = query.join(Document).filter(
                Document.document_type == document_type
            )

        results = query.all()

        # Analyze feedback
        total_with_feedback = 0
        positive = 0
        negative = 0
        neutral = 0
        issue_counts = {}

        for result in results:
            if result.result_data and "feedback" in result.result_data:
                total_with_feedback += 1
                feedback = result.result_data["feedback"]

                rating = feedback.get("rating")
                if rating == "positive":
                    positive += 1
                elif rating == "negative":
                    negative += 1
                else:
                    neutral += 1

                # Count specific issues
                for issue in feedback.get("specific_issues", []):
                    issue_counts[issue] = issue_counts.get(issue, 0) + 1

        return {
            "total_results": len(results),
            "total_with_feedback": total_with_feedback,
            "feedback_rate": total_with_feedback / len(results) if results else 0,
            "ratings": {
                "positive": positive,
                "negative": negative,
                "neutral": neutral
            },
            "positive_rate": positive / total_with_feedback if total_with_feedback > 0 else 0,
            "common_issues": sorted(
                issue_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }

    def get_corrections_for_training(
        self,
        min_confidence: float = 0.8,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get high-quality corrections for fine-tuning

        Args:
            min_confidence: Minimum confidence in correction
            limit: Maximum examples

        Returns:
            List of correction examples
        """
        results = self.db.query(ProcessingResult).filter(
            ProcessingResult.result_data.isnot(None)
        ).limit(limit * 2).all()  # Get more to filter

        corrections = []

        for result in results:
            if not result.result_data or "feedback" not in result.result_data:
                continue

            feedback = result.result_data["feedback"]

            if not feedback.get("corrections"):
                continue

            # Only use corrections with high confidence
            if feedback.get("rating") != "positive":
                continue

            doc = result.document

            corrections.append({
                "id": str(result.id),
                "original_output": result.result_data,
                "corrected_output": feedback["corrections"],
                "input_text": doc.extracted_text[:4000] if doc.extracted_text else "",
                "document_type": doc.document_type,
                "confidence": 1.0 if feedback["rating"] == "positive" else 0.5
            })

            if len(corrections) >= limit:
                break

        return corrections

    def should_trigger_retraining(self) -> bool:
        """
        Determine if model should be retrained based on feedback

        Triggers:
        - Negative feedback rate > 20%
        - More than 100 corrections collected
        - Significant drift detected
        """
        summary = self.get_feedback_summary(time_window_days=30)

        # Check negative feedback rate
        if summary["total_with_feedback"] < 50:
            return False  # Not enough data

        negative_rate = summary["ratings"]["negative"] / summary["total_with_feedback"]

        if negative_rate > 0.20:
            return True

        # Check number of corrections
        corrections = self.get_corrections_for_training(limit=100)
        if len(corrections) >= 100:
            return True

        return False


class FeedbackAnalyzer:
    """Analyze feedback patterns and trends"""

    def __init__(self, db: Session):
        self.db = db

    def analyze_issue_trends(
        self,
        time_window_days: int = 90
    ) -> Dict[str, Any]:
        """Analyze trends in reported issues"""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=time_window_days)

        results = self.db.query(ProcessingResult).filter(
            ProcessingResult.created_at >= cutoff
        ).all()

        # Group by week
        weekly_issues = {}

        for result in results:
            if not result.result_data or "feedback" not in result.result_data:
                continue

            feedback = result.result_data["feedback"]
            week = result.created_at.strftime("%Y-W%W")

            if week not in weekly_issues:
                weekly_issues[week] = {}

            for issue in feedback.get("specific_issues", []):
                weekly_issues[week][issue] = weekly_issues[week].get(issue, 0) + 1

        return {"weekly_trends": weekly_issues}

    def identify_improvement_opportunities(self) -> List[Dict[str, Any]]:
        """Identify areas for improvement based on feedback"""
        collector = FeedbackCollector(self.db)
        summary = collector.get_feedback_summary()

        opportunities = []

        # Check common issues
        for issue, count in summary["common_issues"]:
            if count > 10:  # Significant issue
                opportunities.append({
                    "type": "frequent_issue",
                    "issue": issue,
                    "occurrences": count,
                    "priority": "high" if count > 50 else "medium",
                    "recommendation": f"Focus on improving {issue} detection/extraction"
                })

        # Check feedback rate
        if summary["feedback_rate"] < 0.10:
            opportunities.append({
                "type": "low_feedback_rate",
                "current_rate": summary["feedback_rate"],
                "priority": "medium",
                "recommendation": "Improve feedback collection UI/prompts"
            })

        return opportunities
