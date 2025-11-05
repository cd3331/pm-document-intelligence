"""
Analytics Background Jobs for PM Document Intelligence
Scheduled tasks for data aggregation, caching, and report generation
"""

from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.models.analytics import AnalyticsSnapshot, CachedMetric
from app.models.document import Document
from app.models.user import User
from app.monitoring.log_aggregation import app_logger
from app.monitoring.metrics import analytics_jobs_completed_total
from app.services.analytics_service import AnalyticsService
from app.services.report_generator import ReportGenerator
from sqlalchemy import func
from sqlalchemy.orm import Session


class AnalyticsJobs:
    """Background jobs for analytics processing"""

    def __init__(self):
        self.db: Session | None = None

    def get_db(self) -> Session:
        """Get database session"""
        if not self.db:
            self.db = SessionLocal()
        return self.db

    def close_db(self):
        """Close database session"""
        if self.db:
            self.db.close()
            self.db = None

    # ==========================================
    # Daily Aggregation Jobs
    # ==========================================

    async def run_daily_aggregation(self):
        """
        Run daily aggregation of metrics
        Should be scheduled to run at midnight UTC
        """
        try:
            app_logger.info("Starting daily analytics aggregation")

            db = self.get_db()
            yesterday = datetime.utcnow().date() - timedelta(days=1)
            start_of_day = datetime.combine(yesterday, datetime.min.time())
            end_of_day = datetime.combine(yesterday, datetime.max.time())

            # Aggregate document stats
            await self._aggregate_document_stats(db, start_of_day, end_of_day)

            # Aggregate user activity
            await self._aggregate_user_activity(db, start_of_day, end_of_day)

            # Aggregate costs
            await self._aggregate_costs(db, start_of_day, end_of_day)

            # Aggregate performance metrics
            await self._aggregate_performance(db, start_of_day, end_of_day)

            # Cleanup old data
            await self._cleanup_old_snapshots(db)

            db.commit()

            analytics_jobs_completed_total.labels(job_type="daily_aggregation").inc()

            app_logger.info("Daily analytics aggregation completed successfully")

        except Exception as e:
            app_logger.error(f"Error in daily aggregation: {str(e)}", exc_info=True)
            if db:
                db.rollback()
        finally:
            self.close_db()

    async def _aggregate_document_stats(
        self, db: Session, start_date: datetime, end_date: datetime
    ):
        """Aggregate document statistics for a day"""
        try:
            total_docs = (
                db.query(func.count(Document.id))
                .filter(Document.created_at.between(start_date, end_date))
                .scalar()
            )

            completed_docs = (
                db.query(func.count(Document.id))
                .filter(
                    Document.created_at.between(start_date, end_date),
                    Document.status == "completed",
                )
                .scalar()
            )

            failed_docs = (
                db.query(func.count(Document.id))
                .filter(
                    Document.created_at.between(start_date, end_date),
                    Document.status == "failed",
                )
                .scalar()
            )

            # Average processing time
            avg_processing_time = (
                db.query(
                    func.avg(
                        func.extract("epoch", Document.processed_at)
                        - func.extract("epoch", Document.created_at)
                    )
                )
                .filter(
                    Document.created_at.between(start_date, end_date),
                    Document.status == "completed",
                    Document.processed_at.isnot(None),
                )
                .scalar()
            )

            # Documents by type
            docs_by_type = (
                db.query(Document.document_type, func.count(Document.id))
                .filter(Document.created_at.between(start_date, end_date))
                .group_by(Document.document_type)
                .all()
            )

            # Create snapshot
            snapshot = AnalyticsSnapshot(
                date=start_date.date(),
                metric_type="documents",
                data={
                    "total_documents": total_docs,
                    "completed": completed_docs,
                    "failed": failed_docs,
                    "success_rate": round(
                        (completed_docs / total_docs * 100) if total_docs > 0 else 0, 2
                    ),
                    "avg_processing_time": (
                        float(avg_processing_time) if avg_processing_time else 0
                    ),
                    "by_type": dict(docs_by_type),
                },
            )

            db.add(snapshot)

            app_logger.info(f"Aggregated document stats for {start_date.date()}: {total_docs} docs")

        except Exception as e:
            app_logger.error(f"Error aggregating document stats: {str(e)}")
            raise

    async def _aggregate_user_activity(self, db: Session, start_date: datetime, end_date: datetime):
        """Aggregate user activity for a day"""
        try:
            total_users = db.query(func.count(User.id)).scalar()

            active_users = (
                db.query(func.count(func.distinct(Document.user_id)))
                .filter(Document.created_at.between(start_date, end_date))
                .scalar()
            )

            # New registrations
            new_users = (
                db.query(func.count(User.id))
                .filter(User.created_at.between(start_date, end_date))
                .scalar()
            )

            # Create snapshot
            snapshot = AnalyticsSnapshot(
                date=start_date.date(),
                metric_type="users",
                data={
                    "total_users": total_users,
                    "active_users": active_users,
                    "new_users": new_users,
                    "engagement_rate": round(
                        (active_users / total_users * 100) if total_users > 0 else 0, 2
                    ),
                },
            )

            db.add(snapshot)

            app_logger.info(f"Aggregated user activity for {start_date.date()}")

        except Exception as e:
            app_logger.error(f"Error aggregating user activity: {str(e)}")
            raise

    async def _aggregate_costs(self, db: Session, start_date: datetime, end_date: datetime):
        """Aggregate costs for a day"""
        try:
            from app.monitoring.cost_tracking import cost_tracker

            cost_entries = [
                entry
                for entry in cost_tracker.cost_history
                if start_date <= entry.timestamp <= end_date
            ]

            total_cost = sum(entry.total_cost for entry in cost_entries)

            # Costs by service
            costs_by_service = {}
            for entry in cost_entries:
                costs_by_service[entry.service] = (
                    costs_by_service.get(entry.service, 0) + entry.total_cost
                )

            # Create snapshot
            snapshot = AnalyticsSnapshot(
                date=start_date.date(),
                metric_type="costs",
                data={
                    "total_cost": round(total_cost, 2),
                    "by_service": {k: round(v, 2) for k, v in costs_by_service.items()},
                    "currency": "USD",
                },
            )

            db.add(snapshot)

            app_logger.info(f"Aggregated costs for {start_date.date()}: ${total_cost:.2f}")

        except Exception as e:
            app_logger.error(f"Error aggregating costs: {str(e)}")
            raise

    async def _aggregate_performance(self, db: Session, start_date: datetime, end_date: datetime):
        """Aggregate performance metrics for a day"""
        try:
            analytics_service = AnalyticsService(db)
            performance = analytics_service.get_processing_performance(start_date, end_date)

            # Create snapshot
            snapshot = AnalyticsSnapshot(
                date=start_date.date(), metric_type="performance", data=performance
            )

            db.add(snapshot)

            app_logger.info(f"Aggregated performance metrics for {start_date.date()}")

        except Exception as e:
            app_logger.error(f"Error aggregating performance: {str(e)}")
            raise

    async def _cleanup_old_snapshots(self, db: Session, retention_days: int = 90):
        """Clean up old analytics snapshots"""
        try:
            cutoff_date = datetime.utcnow().date() - timedelta(days=retention_days)

            deleted = (
                db.query(AnalyticsSnapshot).filter(AnalyticsSnapshot.date < cutoff_date).delete()
            )

            app_logger.info(f"Cleaned up {deleted} old analytics snapshots")

        except Exception as e:
            app_logger.error(f"Error cleaning up snapshots: {str(e)}")

    # ==========================================
    # Cache Warming Jobs
    # ==========================================

    async def warm_analytics_cache(self):
        """
        Pre-compute and cache expensive analytics queries
        Should be scheduled to run every hour
        """
        try:
            app_logger.info("Starting analytics cache warming")

            db = self.get_db()
            analytics_service = AnalyticsService(db)

            # Cache document stats for last 30 days
            await self._cache_document_stats(db, analytics_service, days=30)

            # Cache user activity
            await self._cache_user_activity(db, analytics_service, days=30)

            # Cache performance metrics
            await self._cache_performance_metrics(db, analytics_service, days=7)

            db.commit()

            analytics_jobs_completed_total.labels(job_type="cache_warming").inc()

            app_logger.info("Analytics cache warming completed")

        except Exception as e:
            app_logger.error(f"Error warming cache: {str(e)}", exc_info=True)
            if db:
                db.rollback()
        finally:
            self.close_db()

    async def _cache_document_stats(
        self, db: Session, analytics_service: AnalyticsService, days: int
    ):
        """Cache document statistics"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # Create temporary admin user for full data access
            class TempAdmin:
                is_superuser = True
                id = "system"

            admin_user = TempAdmin()

            time_series = analytics_service.get_document_time_series(
                start_date, end_date, None, admin_user
            )

            # Store in cache
            cache_entry = (
                db.query(CachedMetric)
                .filter(CachedMetric.metric_key == "document_stats_30d")
                .first()
            )

            if cache_entry:
                cache_entry.metric_value = {"time_series": time_series}
                cache_entry.updated_at = datetime.utcnow()
            else:
                cache_entry = CachedMetric(
                    metric_key="document_stats_30d",
                    metric_value={"time_series": time_series},
                    expires_at=datetime.utcnow() + timedelta(hours=1),
                )
                db.add(cache_entry)

            app_logger.info("Cached document stats for 30 days")

        except Exception as e:
            app_logger.error(f"Error caching document stats: {str(e)}")

    async def _cache_user_activity(
        self, db: Session, analytics_service: AnalyticsService, days: int
    ):
        """Cache user activity metrics"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            peak_times = analytics_service.get_peak_usage_times(start_date, end_date)

            # Store in cache
            cache_entry = (
                db.query(CachedMetric)
                .filter(CachedMetric.metric_key == "user_activity_30d")
                .first()
            )

            if cache_entry:
                cache_entry.metric_value = {"peak_times": peak_times}
                cache_entry.updated_at = datetime.utcnow()
            else:
                cache_entry = CachedMetric(
                    metric_key="user_activity_30d",
                    metric_value={"peak_times": peak_times},
                    expires_at=datetime.utcnow() + timedelta(hours=1),
                )
                db.add(cache_entry)

            app_logger.info("Cached user activity for 30 days")

        except Exception as e:
            app_logger.error(f"Error caching user activity: {str(e)}")

    async def _cache_performance_metrics(
        self, db: Session, analytics_service: AnalyticsService, days: int
    ):
        """Cache performance metrics"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            performance = analytics_service.get_processing_performance(start_date, end_date)

            # Store in cache
            cache_entry = (
                db.query(CachedMetric).filter(CachedMetric.metric_key == "performance_7d").first()
            )

            if cache_entry:
                cache_entry.metric_value = performance
                cache_entry.updated_at = datetime.utcnow()
            else:
                cache_entry = CachedMetric(
                    metric_key="performance_7d",
                    metric_value=performance,
                    expires_at=datetime.utcnow() + timedelta(hours=1),
                )
                db.add(cache_entry)

            app_logger.info("Cached performance metrics for 7 days")

        except Exception as e:
            app_logger.error(f"Error caching performance metrics: {str(e)}")

    # ==========================================
    # Automated Report Generation
    # ==========================================

    async def generate_scheduled_reports(self):
        """
        Generate and send scheduled reports
        Should be scheduled based on report frequency
        """
        try:
            app_logger.info("Starting scheduled report generation")

            db = self.get_db()
            report_generator = ReportGenerator(db)

            # Generate daily report
            await self._generate_daily_report(db, report_generator)

            # Check if it's Monday for weekly report
            if datetime.utcnow().weekday() == 0:  # Monday
                await self._generate_weekly_report(db, report_generator)

            # Check if it's first day of month for monthly report
            if datetime.utcnow().day == 1:
                await self._generate_monthly_report(db, report_generator)

            analytics_jobs_completed_total.labels(job_type="scheduled_reports").inc()

            app_logger.info("Scheduled report generation completed")

        except Exception as e:
            app_logger.error(f"Error generating scheduled reports: {str(e)}", exc_info=True)
        finally:
            self.close_db()

    async def _generate_daily_report(self, db: Session, report_generator: ReportGenerator):
        """Generate daily report"""
        try:
            # Get admin users who should receive reports
            admin_users = db.query(User).filter(User.is_superuser).all()

            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=1)

            for user in admin_users:
                await report_generator.generate_and_send_report(
                    report_type="daily",
                    start_date=start_date,
                    end_date=end_date,
                    format="pdf",
                    email_to=user.email,
                    user_id=str(user.id),
                )

            app_logger.info(f"Generated daily reports for {len(admin_users)} admins")

        except Exception as e:
            app_logger.error(f"Error generating daily report: {str(e)}")

    async def _generate_weekly_report(self, db: Session, report_generator: ReportGenerator):
        """Generate weekly report"""
        try:
            admin_users = db.query(User).filter(User.is_superuser).all()

            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)

            for user in admin_users:
                await report_generator.generate_and_send_report(
                    report_type="weekly",
                    start_date=start_date,
                    end_date=end_date,
                    format="pdf",
                    email_to=user.email,
                    user_id=str(user.id),
                )

            app_logger.info(f"Generated weekly reports for {len(admin_users)} admins")

        except Exception as e:
            app_logger.error(f"Error generating weekly report: {str(e)}")

    async def _generate_monthly_report(self, db: Session, report_generator: ReportGenerator):
        """Generate monthly report"""
        try:
            admin_users = db.query(User).filter(User.is_superuser).all()

            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)

            for user in admin_users:
                await report_generator.generate_and_send_report(
                    report_type="monthly",
                    start_date=start_date,
                    end_date=end_date,
                    format="pdf",
                    email_to=user.email,
                    user_id=str(user.id),
                )

            app_logger.info(f"Generated monthly reports for {len(admin_users)} admins")

        except Exception as e:
            app_logger.error(f"Error generating monthly report: {str(e)}")


# ==========================================
# Job Scheduler Setup
# ==========================================

# This would be integrated with a job scheduler like Celery, APScheduler, etc.
# Example with APScheduler:

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

analytics_jobs = AnalyticsJobs()
scheduler = AsyncIOScheduler()

# Schedule daily aggregation at midnight UTC
scheduler.add_job(
    analytics_jobs.run_daily_aggregation,
    CronTrigger(hour=0, minute=0),
    id="daily_aggregation",
    name="Daily Analytics Aggregation",
)

# Schedule cache warming every hour
scheduler.add_job(
    analytics_jobs.warm_analytics_cache,
    CronTrigger(minute=0),
    id="cache_warming",
    name="Analytics Cache Warming",
)

# Schedule daily report at 6 AM UTC
scheduler.add_job(
    analytics_jobs.generate_scheduled_reports,
    CronTrigger(hour=6, minute=0),
    id="scheduled_reports",
    name="Scheduled Report Generation",
)


def start_analytics_scheduler():
    """Start the analytics job scheduler"""
    try:
        scheduler.start()
        app_logger.info("Analytics job scheduler started")
    except Exception as e:
        app_logger.error(f"Error starting scheduler: {str(e)}")


def stop_analytics_scheduler():
    """Stop the analytics job scheduler"""
    try:
        scheduler.shutdown()
        app_logger.info("Analytics job scheduler stopped")
    except Exception as e:
        app_logger.error(f"Error stopping scheduler: {str(e)}")
