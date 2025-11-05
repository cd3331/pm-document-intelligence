"""
Analytics Service for PM Document Intelligence
Handles analytics calculations, aggregations, and insights generation
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, extract
from collections import defaultdict
import json

from app.models.user import User
from app.models.document import Document
from app.monitoring.log_aggregation import app_logger


class AnalyticsService:
    """Service for analytics calculations and insights"""

    def __init__(self, db: Session):
        self.db = db

    # ==========================================
    # Document Analytics
    # ==========================================

    def get_avg_processing_time(
        self,
        start_date: datetime,
        end_date: datetime,
        document_type: Optional[str],
        current_user: User,
    ) -> float:
        """Calculate average processing time for documents"""
        try:
            query = self.db.query(
                func.avg(
                    func.extract("epoch", Document.processed_at)
                    - func.extract("epoch", Document.created_at)
                ).label("avg_time")
            ).filter(
                Document.status == "completed",
                Document.processed_at.isnot(None),
                Document.created_at.between(start_date, end_date),
            )

            if not current_user.is_superuser:
                query = query.filter(Document.user_id == current_user.id)

            if document_type:
                query = query.filter(Document.document_type == document_type)

            result = query.scalar()
            return result if result else 0.0

        except Exception as e:
            app_logger.error(f"Error calculating avg processing time: {str(e)}")
            return 0.0

    def get_document_time_series(
        self,
        start_date: datetime,
        end_date: datetime,
        document_type: Optional[str],
        current_user: User,
    ) -> List[Dict]:
        """Get time series data for document creation"""
        try:
            query = self.db.query(
                func.date(Document.created_at).label("date"),
                func.count(Document.id).label("count"),
                Document.status,
            ).filter(Document.created_at.between(start_date, end_date))

            if not current_user.is_superuser:
                query = query.filter(Document.user_id == current_user.id)

            if document_type:
                query = query.filter(Document.document_type == document_type)

            results = (
                query.group_by(func.date(Document.created_at), Document.status)
                .order_by("date")
                .all()
            )

            # Organize by date
            time_series_data = defaultdict(
                lambda: {"date": None, "total": 0, "by_status": {}}
            )

            for date, count, status in results:
                date_str = date.isoformat()
                time_series_data[date_str]["date"] = date_str
                time_series_data[date_str]["total"] += count
                time_series_data[date_str]["by_status"][status] = count

            return list(time_series_data.values())

        except Exception as e:
            app_logger.error(f"Error getting document time series: {str(e)}")
            return []

    async def generate_document_insights(
        self, start_date: datetime, end_date: datetime, current_user: User
    ) -> Dict[str, Any]:
        """Generate AI-powered insights about documents"""
        try:
            # Base query
            if current_user.is_superuser:
                base_query = self.db.query(Document)
            else:
                base_query = self.db.query(Document).filter(
                    Document.user_id == current_user.id
                )

            documents = base_query.filter(
                Document.created_at.between(start_date, end_date),
                Document.status == "completed",
            ).all()

            if not documents:
                return {
                    "common_themes": [],
                    "trending_topics": [],
                    "sentiment_trends": {},
                    "risk_indicators": [],
                    "action_item_completion_rate": 0,
                }

            # Extract common themes from entities
            entity_counts = defaultdict(int)
            for doc in documents:
                if doc.metadata and "entities" in doc.metadata:
                    for entity in doc.metadata["entities"]:
                        entity_counts[entity.get("text", "")] += 1

            common_themes = [
                {"theme": theme, "count": count}
                for theme, count in sorted(
                    entity_counts.items(), key=lambda x: x[1], reverse=True
                )[:10]
            ]

            # Trending topics (themes that increased recently)
            trending_topics = await self._identify_trending_topics(documents)

            # Sentiment trends
            sentiment_trends = await self._analyze_sentiment_trends(documents)

            # Risk indicators
            risk_indicators = await self._identify_risk_indicators(documents)

            # Action item completion rate
            completion_rate = await self._calculate_action_item_completion(documents)

            return {
                "common_themes": common_themes,
                "trending_topics": trending_topics,
                "sentiment_trends": sentiment_trends,
                "risk_indicators": risk_indicators,
                "action_item_completion_rate": completion_rate,
                "total_documents_analyzed": len(documents),
            }

        except Exception as e:
            app_logger.error(f"Error generating document insights: {str(e)}")
            return {}

    async def _identify_trending_topics(self, documents: List[Document]) -> List[Dict]:
        """Identify trending topics from recent documents"""
        # Simple implementation: topics mentioned more in recent documents
        if len(documents) < 2:
            return []

        # Split into two halves: older and recent
        mid_point = len(documents) // 2
        older_docs = documents[:mid_point]
        recent_docs = documents[mid_point:]

        older_topics = defaultdict(int)
        recent_topics = defaultdict(int)

        for doc in older_docs:
            if doc.metadata and "entities" in doc.metadata:
                for entity in doc.metadata["entities"]:
                    older_topics[entity.get("text", "")] += 1

        for doc in recent_docs:
            if doc.metadata and "entities" in doc.metadata:
                for entity in doc.metadata["entities"]:
                    recent_topics[entity.get("text", "")] += 1

        # Find topics that increased
        trending = []
        for topic, recent_count in recent_topics.items():
            older_count = older_topics.get(topic, 0)
            if recent_count > older_count:
                trending.append(
                    {
                        "topic": topic,
                        "growth": recent_count - older_count,
                        "recent_mentions": recent_count,
                    }
                )

        return sorted(trending, key=lambda x: x["growth"], reverse=True)[:5]

    async def _analyze_sentiment_trends(self, documents: List[Document]) -> Dict:
        """Analyze sentiment trends across documents"""
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}

        for doc in documents:
            if doc.metadata and "sentiment" in doc.metadata:
                sentiment = doc.metadata["sentiment"].get("sentiment", "neutral")
                if sentiment in sentiment_counts:
                    sentiment_counts[sentiment] += 1

        total = sum(sentiment_counts.values())
        if total > 0:
            return {
                "positive_percentage": round(
                    sentiment_counts["positive"] / total * 100, 2
                ),
                "neutral_percentage": round(
                    sentiment_counts["neutral"] / total * 100, 2
                ),
                "negative_percentage": round(
                    sentiment_counts["negative"] / total * 100, 2
                ),
                "overall_sentiment": max(sentiment_counts, key=sentiment_counts.get),
            }

        return {}

    async def _identify_risk_indicators(self, documents: List[Document]) -> List[Dict]:
        """Identify potential risk indicators from documents"""
        risk_keywords = {
            "high": ["critical", "urgent", "emergency", "risk", "danger", "failure"],
            "medium": ["concern", "issue", "problem", "delay", "warning"],
            "low": ["note", "attention", "review", "check"],
        }

        risks = []

        for doc in documents:
            if doc.extracted_text:
                text_lower = doc.extracted_text.lower()

                for severity, keywords in risk_keywords.items():
                    for keyword in keywords:
                        if keyword in text_lower:
                            risks.append(
                                {
                                    "document_id": str(doc.id),
                                    "document_name": doc.filename,
                                    "keyword": keyword,
                                    "severity": severity,
                                    "timestamp": doc.created_at.isoformat(),
                                }
                            )

        # Group by severity and count
        risk_summary = defaultdict(int)
        for risk in risks:
            risk_summary[risk["severity"]] += 1

        return {
            "summary": dict(risk_summary),
            "total_risks": len(risks),
            "recent_high_risks": [r for r in risks if r["severity"] == "high"][:5],
        }

    async def _calculate_action_item_completion(
        self, documents: List[Document]
    ) -> float:
        """Calculate action item completion rate"""
        # This would query the action_items table
        # For now, return mock data
        return 68.5

    # ==========================================
    # User Analytics
    # ==========================================

    def get_search_analytics(self, start_date: datetime, end_date: datetime) -> Dict:
        """Analyze search query patterns"""
        # This would query search logs
        # For now, return mock structure
        return {
            "total_searches": 1543,
            "unique_queries": 876,
            "avg_results_per_search": 12.3,
            "top_queries": [
                {"query": "project requirements", "count": 45},
                {"query": "budget analysis", "count": 38},
                {"query": "meeting notes", "count": 32},
            ],
        }

    def get_feature_usage(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get feature usage statistics"""
        # This would track feature usage from audit logs
        return {
            "document_upload": 543,
            "semantic_search": 876,
            "ai_summary": 432,
            "action_extraction": 387,
            "q_and_a": 654,
            "export": 123,
        }

    def get_peak_usage_times(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Identify peak usage times by hour"""
        try:
            # Query documents by hour of day
            hourly_counts = (
                self.db.query(
                    extract("hour", Document.created_at).label("hour"),
                    func.count(Document.id).label("count"),
                )
                .filter(Document.created_at.between(start_date, end_date))
                .group_by("hour")
                .order_by("hour")
                .all()
            )

            return [
                {"hour": int(hour), "count": count} for hour, count in hourly_counts
            ]

        except Exception as e:
            app_logger.error(f"Error getting peak usage times: {str(e)}")
            return []

    def get_common_workflows(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Identify common user workflows"""
        # This would analyze audit log sequences
        return [
            {
                "workflow": "Upload → Summary → Export",
                "frequency": 234,
                "avg_duration_minutes": 15,
            },
            {
                "workflow": "Search → View → Q&A",
                "frequency": 198,
                "avg_duration_minutes": 8,
            },
            {
                "workflow": "Upload → Action Extraction → Assign",
                "frequency": 156,
                "avg_duration_minutes": 12,
            },
        ]

    def get_feature_adoption_rates(
        self, start_date: datetime, end_date: datetime
    ) -> Dict:
        """Calculate feature adoption rates"""
        total_users = self.db.query(func.count(User.id)).scalar()

        # Users who uploaded documents
        uploaders = (
            self.db.query(func.count(func.distinct(Document.user_id)))
            .filter(Document.created_at.between(start_date, end_date))
            .scalar()
        )

        return {
            "document_upload": {
                "users": uploaders,
                "adoption_rate": round(
                    (uploaders / total_users * 100) if total_users > 0 else 0, 2
                ),
            },
            "semantic_search": {
                "users": int(total_users * 0.65),  # Mock data
                "adoption_rate": 65.0,
            },
            "ai_agents": {
                "users": int(total_users * 0.48),  # Mock data
                "adoption_rate": 48.0,
            },
        }

    # ==========================================
    # Performance Analytics
    # ==========================================

    def get_processing_performance(
        self, start_date: datetime, end_date: datetime
    ) -> Dict:
        """Get document processing performance metrics"""
        try:
            # Processing times by document type
            processing_times = (
                self.db.query(
                    Document.document_type,
                    func.avg(
                        func.extract("epoch", Document.processed_at)
                        - func.extract("epoch", Document.created_at)
                    ).label("avg_time"),
                    func.count(Document.id).label("count"),
                )
                .filter(
                    Document.status == "completed",
                    Document.processed_at.isnot(None),
                    Document.created_at.between(start_date, end_date),
                )
                .group_by(Document.document_type)
                .all()
            )

            by_type = [
                {
                    "document_type": doc_type,
                    "avg_processing_time_seconds": round(float(avg_time), 2),
                    "document_count": count,
                }
                for doc_type, avg_time, count in processing_times
            ]

            # Success/failure rates
            total_docs = (
                self.db.query(func.count(Document.id))
                .filter(Document.created_at.between(start_date, end_date))
                .scalar()
            )

            completed_docs = (
                self.db.query(func.count(Document.id))
                .filter(
                    Document.created_at.between(start_date, end_date),
                    Document.status == "completed",
                )
                .scalar()
            )

            failed_docs = (
                self.db.query(func.count(Document.id))
                .filter(
                    Document.created_at.between(start_date, end_date),
                    Document.status == "failed",
                )
                .scalar()
            )

            # Bottleneck identification
            bottlenecks = []
            for doc_type, avg_time, count in processing_times:
                if avg_time and avg_time > 60:  # More than 60 seconds
                    bottlenecks.append(
                        {
                            "stage": f"{doc_type} processing",
                            "avg_time_seconds": round(float(avg_time), 2),
                            "severity": "high" if avg_time > 120 else "medium",
                        }
                    )

            return {
                "overall_metrics": {
                    "total_processed": total_docs,
                    "completed": completed_docs,
                    "failed": failed_docs,
                    "success_rate": round(
                        (completed_docs / total_docs * 100) if total_docs > 0 else 0, 2
                    ),
                },
                "by_document_type": by_type,
                "bottlenecks": bottlenecks,
                "agent_performance": self._get_agent_performance(start_date, end_date),
            }

        except Exception as e:
            app_logger.error(f"Error getting processing performance: {str(e)}")
            return {}

    def _get_agent_performance(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Compare performance of different AI agents"""
        # This would query agent_executions table
        return [
            {
                "agent": "summary",
                "avg_execution_time_seconds": 3.45,
                "success_rate": 98.2,
                "total_executions": 543,
            },
            {
                "agent": "action_extractor",
                "avg_execution_time_seconds": 4.12,
                "success_rate": 95.7,
                "total_executions": 432,
            },
            {
                "agent": "qa",
                "avg_execution_time_seconds": 2.87,
                "success_rate": 97.5,
                "total_executions": 876,
            },
        ]

    # ==========================================
    # Export Helpers
    # ==========================================

    def get_documents_for_export(
        self, start_date: datetime, end_date: datetime, current_user: User
    ) -> List[Dict]:
        """Get document data for CSV export"""
        try:
            query = self.db.query(Document).filter(
                Document.created_at.between(start_date, end_date)
            )

            if not current_user.is_superuser:
                query = query.filter(Document.user_id == current_user.id)

            documents = query.all()

            return [
                {
                    "id": str(doc.id),
                    "filename": doc.filename,
                    "document_type": doc.document_type,
                    "status": doc.status,
                    "created_at": doc.created_at.isoformat(),
                    "processed_at": (
                        doc.processed_at.isoformat() if doc.processed_at else None
                    ),
                    "file_size": doc.file_size,
                }
                for doc in documents
            ]

        except Exception as e:
            app_logger.error(f"Error getting documents for export: {str(e)}")
            return []

    def get_users_for_export(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get user data for CSV export"""
        try:
            users = (
                self.db.query(
                    User.id,
                    User.username,
                    User.email,
                    User.created_at,
                    func.count(Document.id).label("document_count"),
                )
                .outerjoin(Document, Document.user_id == User.id)
                .filter(User.created_at.between(start_date, end_date))
                .group_by(User.id, User.username, User.email, User.created_at)
                .all()
            )

            return [
                {
                    "id": str(user_id),
                    "username": username,
                    "email": email,
                    "joined_at": created_at.isoformat(),
                    "document_count": doc_count,
                }
                for user_id, username, email, created_at, doc_count in users
            ]

        except Exception as e:
            app_logger.error(f"Error getting users for export: {str(e)}")
            return []

    def get_costs_for_export(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get cost data for CSV export"""
        try:
            from app.monitoring.cost_tracking import cost_tracker

            cost_entries = [
                {
                    "timestamp": entry.timestamp.isoformat(),
                    "service": entry.service,
                    "operation": entry.operation,
                    "units": entry.units,
                    "unit_cost": entry.unit_cost,
                    "total_cost": entry.total_cost,
                }
                for entry in cost_tracker.cost_history
                if start_date <= entry.timestamp <= end_date
            ]

            return cost_entries

        except Exception as e:
            app_logger.error(f"Error getting costs for export: {str(e)}")
            return []
