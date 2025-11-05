"""
Quota Management Service
Tracks and enforces usage limits based on organization plan tiers
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid

from app.models.organization import Organization, OrganizationUsage, PlanTier
from app.models.document import Document
from app.models.user import User
from app.services.audit_logger import AuditLogger


class QuotaExceededException(Exception):
    """Raised when quota limit is exceeded"""

    def __init__(self, quota_name: str, current: int, limit: int, message: str = None):
        self.quota_name = quota_name
        self.current = current
        self.limit = limit
        self.message = message or f"Quota exceeded for {quota_name}: {current}/{limit}"
        super().__init__(self.message)


class QuotaWarning:
    """Container for quota warning information"""

    def __init__(self, quota_name: str, current: int, limit: int, percentage: float):
        self.quota_name = quota_name
        self.current = current
        self.limit = limit
        self.percentage = percentage
        self.warning_level = self._get_warning_level()

    def _get_warning_level(self) -> str:
        """Determine warning severity"""
        if self.percentage >= 95:
            return "critical"
        elif self.percentage >= 80:
            return "warning"
        elif self.percentage >= 70:
            return "info"
        return "none"

    def should_notify(self) -> bool:
        """Check if notification should be sent"""
        return self.warning_level in ["critical", "warning"]


class QuotaManager:
    """
    Manages organization quotas and usage tracking
    """

    def __init__(self, db: Session):
        self.db = db

    # ============================================================================
    # Current Period Management
    # ============================================================================

    def get_current_period(self) -> tuple[datetime, datetime]:
        """
        Get current billing period (monthly)
        Returns (period_start, period_end)
        """
        now = datetime.utcnow()
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Calculate period end (first day of next month)
        if now.month == 12:
            period_end = period_start.replace(year=now.year + 1, month=1)
        else:
            period_end = period_start.replace(month=now.month + 1)

        return period_start, period_end

    def get_current_day_period(self) -> tuple[datetime, datetime]:
        """
        Get current day period for daily limits
        Returns (day_start, day_end)
        """
        now = datetime.utcnow()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        return day_start, day_end

    def get_or_create_usage_record(
        self, organization_id: uuid.UUID
    ) -> OrganizationUsage:
        """
        Get or create usage record for current period
        """
        period_start, period_end = self.get_current_period()

        usage = (
            self.db.query(OrganizationUsage)
            .filter(
                OrganizationUsage.organization_id == organization_id,
                OrganizationUsage.period_start == period_start,
            )
            .first()
        )

        if not usage:
            usage = OrganizationUsage(
                organization_id=organization_id,
                period_start=period_start,
                period_end=period_end,
                documents_created=0,
                api_calls=0,
                ai_queries=0,
                storage_used_bytes=0,
                total_cost=0,
                usage_details={},
            )
            self.db.add(usage)
            self.db.commit()
            self.db.refresh(usage)

        return usage

    # ============================================================================
    # Usage Tracking
    # ============================================================================

    async def get_period_usage(self, organization_id: uuid.UUID) -> Dict[str, int]:
        """
        Get current usage for all tracked metrics

        Returns:
            dict with usage counters:
            {
                "documents_created": 45,
                "api_calls": 230,
                "ai_queries": 67,
                "storage_used_gb": 0.5,
                "users": 3
            }
        """
        usage = self.get_or_create_usage_record(organization_id)

        # Count active users
        from app.models.organization import OrganizationMember

        user_count = (
            self.db.query(func.count(OrganizationMember.id))
            .filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.is_active == True,
            )
            .scalar()
        )

        return {
            "documents_created": usage.documents_created,
            "api_calls": usage.api_calls,
            "api_calls_today": await self._get_api_calls_today(organization_id),
            "ai_queries": usage.ai_queries,
            "storage_used_gb": round(usage.storage_used_gb, 2),
            "storage_used_bytes": usage.storage_used_bytes,
            "users": user_count,
            "total_cost_cents": usage.total_cost,
        }

    async def _get_api_calls_today(self, organization_id: uuid.UUID) -> int:
        """Get API calls made today"""
        usage = self.get_or_create_usage_record(organization_id)
        details = usage.usage_details or {}

        today_key = datetime.utcnow().strftime("%Y-%m-%d")
        daily_usage = details.get("daily_api_calls", {})

        return daily_usage.get(today_key, 0)

    async def get_current_usage(
        self, organization_id: uuid.UUID, quota_name: str
    ) -> int:
        """
        Get current usage for a specific quota

        Args:
            organization_id: Organization UUID
            quota_name: Name of quota (e.g., 'documents_per_month', 'api_calls_per_day')

        Returns:
            Current usage count
        """
        if quota_name == "documents_per_month":
            usage = self.get_or_create_usage_record(organization_id)
            return usage.documents_created

        elif quota_name == "api_calls_per_day":
            return await self._get_api_calls_today(organization_id)

        elif quota_name == "ai_queries_per_month":
            usage = self.get_or_create_usage_record(organization_id)
            return usage.ai_queries

        elif quota_name == "storage_gb":
            usage = self.get_or_create_usage_record(organization_id)
            return int(usage.storage_used_gb)

        elif quota_name == "users":
            from app.models.organization import OrganizationMember

            return (
                self.db.query(func.count(OrganizationMember.id))
                .filter(
                    OrganizationMember.organization_id == organization_id,
                    OrganizationMember.is_active == True,
                )
                .scalar()
            )

        elif quota_name == "teams":
            from app.models.organization import Team

            return (
                self.db.query(func.count(Team.id))
                .filter(Team.organization_id == organization_id)
                .scalar()
            )

        return 0

    # ============================================================================
    # Quota Checking
    # ============================================================================

    async def check_quota(
        self, organization_id: uuid.UUID, quota_name: str, increment: int = 1
    ) -> tuple[bool, Optional[str]]:
        """
        Check if organization has quota available

        Args:
            organization_id: Organization UUID
            quota_name: Name of quota to check
            increment: Amount to increment (default 1)

        Returns:
            (has_quota, error_message)
            - (True, None) if quota available
            - (False, error_message) if quota exceeded
        """
        organization = (
            self.db.query(Organization)
            .filter(Organization.id == organization_id)
            .first()
        )

        if not organization:
            return False, "Organization not found"

        # Get plan limits
        limits = organization.get_plan_limits()
        quota_limit = limits.get(quota_name)

        if quota_limit is None:
            # Quota not defined, allow
            return True, None

        if quota_limit == -1:
            # Unlimited quota
            return True, None

        # Get current usage
        current_usage = await self.get_current_usage(organization_id, quota_name)

        # Check if would exceed
        if current_usage + increment > quota_limit:
            overage = current_usage + increment - quota_limit
            return False, (
                f"Quota exceeded for {quota_name}. "
                f"Current: {current_usage}, Limit: {quota_limit}, "
                f"Attempted: +{increment} (would exceed by {overage}). "
                f"Please upgrade your plan."
            )

        return True, None

    async def enforce_quota(
        self, organization_id: uuid.UUID, quota_name: str, increment: int = 1
    ):
        """
        Enforce quota - raises exception if exceeded

        Args:
            organization_id: Organization UUID
            quota_name: Name of quota to check
            increment: Amount to increment

        Raises:
            QuotaExceededException: If quota would be exceeded
        """
        has_quota, error_msg = await self.check_quota(
            organization_id, quota_name, increment
        )

        if not has_quota:
            current = await self.get_current_usage(organization_id, quota_name)
            organization = (
                self.db.query(Organization)
                .filter(Organization.id == organization_id)
                .first()
            )
            limit = organization.get_plan_limits().get(quota_name, 0)

            raise QuotaExceededException(
                quota_name=quota_name, current=current, limit=limit, message=error_msg
            )

    # ============================================================================
    # Usage Incrementing
    # ============================================================================

    async def increment_document_count(
        self, organization_id: uuid.UUID, count: int = 1
    ):
        """
        Increment document creation count
        Checks quota before incrementing

        Raises:
            QuotaExceededException: If quota exceeded
        """
        await self.enforce_quota(organization_id, "documents_per_month", count)

        usage = self.get_or_create_usage_record(organization_id)
        usage.documents_created += count
        self.db.commit()

        # Check for warnings
        await self._check_and_notify_warnings(organization_id, "documents_per_month")

    async def increment_api_calls(self, organization_id: uuid.UUID, count: int = 1):
        """
        Increment API call count for today
        Checks daily quota

        Raises:
            QuotaExceededException: If daily quota exceeded
        """
        await self.enforce_quota(organization_id, "api_calls_per_day", count)

        usage = self.get_or_create_usage_record(organization_id)
        usage.api_calls += count

        # Track daily breakdown
        today_key = datetime.utcnow().strftime("%Y-%m-%d")
        details = usage.usage_details or {}

        if "daily_api_calls" not in details:
            details["daily_api_calls"] = {}

        details["daily_api_calls"][today_key] = (
            details["daily_api_calls"].get(today_key, 0) + count
        )
        usage.usage_details = details

        self.db.commit()

        # Check for warnings
        await self._check_and_notify_warnings(organization_id, "api_calls_per_day")

    async def increment_ai_queries(self, organization_id: uuid.UUID, count: int = 1):
        """
        Increment AI query count

        Raises:
            QuotaExceededException: If quota exceeded
        """
        await self.enforce_quota(organization_id, "ai_queries_per_month", count)

        usage = self.get_or_create_usage_record(organization_id)
        usage.ai_queries += count
        self.db.commit()

        await self._check_and_notify_warnings(organization_id, "ai_queries_per_month")

    async def update_storage_usage(self, organization_id: uuid.UUID, bytes_delta: int):
        """
        Update storage usage (can be positive or negative)

        Args:
            organization_id: Organization UUID
            bytes_delta: Change in storage bytes (positive = increase, negative = decrease)

        Raises:
            QuotaExceededException: If quota would be exceeded
        """
        usage = self.get_or_create_usage_record(organization_id)
        new_storage = max(0, usage.storage_used_bytes + bytes_delta)

        # Check quota if increasing
        if bytes_delta > 0:
            new_gb = new_storage / (1024**3)
            organization = (
                self.db.query(Organization)
                .filter(Organization.id == organization_id)
                .first()
            )
            limits = organization.get_plan_limits()
            storage_limit_gb = limits.get("storage_gb", 0)

            if storage_limit_gb != -1 and new_gb > storage_limit_gb:
                raise QuotaExceededException(
                    quota_name="storage_gb",
                    current=int(usage.storage_used_gb),
                    limit=storage_limit_gb,
                    message=f"Storage quota exceeded. Current: {usage.storage_used_gb:.2f} GB, Limit: {storage_limit_gb} GB",
                )

        usage.storage_used_bytes = new_storage
        self.db.commit()

        await self._check_and_notify_warnings(organization_id, "storage_gb")

    async def add_cost(
        self,
        organization_id: uuid.UUID,
        cost_cents: int,
        details: Optional[dict] = None,
    ):
        """
        Add cost to organization usage tracking

        Args:
            organization_id: Organization UUID
            cost_cents: Cost in cents
            details: Optional breakdown of cost
        """
        usage = self.get_or_create_usage_record(organization_id)
        usage.total_cost += cost_cents

        if details:
            usage_details = usage.usage_details or {}
            if "cost_breakdown" not in usage_details:
                usage_details["cost_breakdown"] = []
            usage_details["cost_breakdown"].append(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "amount_cents": cost_cents,
                    **details,
                }
            )
            usage.usage_details = usage_details

        self.db.commit()

    # ============================================================================
    # Quota Warnings and Notifications
    # ============================================================================

    async def _check_and_notify_warnings(
        self, organization_id: uuid.UUID, quota_name: str
    ):
        """
        Check if quota is approaching limit and send notifications

        Sends notifications at 70%, 80%, 95% thresholds
        """
        organization = (
            self.db.query(Organization)
            .filter(Organization.id == organization_id)
            .first()
        )

        limits = organization.get_plan_limits()
        quota_limit = limits.get(quota_name)

        if not quota_limit or quota_limit == -1:
            return

        current_usage = await self.get_current_usage(organization_id, quota_name)
        percentage = (current_usage / quota_limit) * 100

        warning = QuotaWarning(quota_name, current_usage, quota_limit, percentage)

        if warning.should_notify():
            await self._send_quota_warning(organization, warning)

    async def _send_quota_warning(
        self, organization: Organization, warning: QuotaWarning
    ):
        """
        Send quota warning notification

        In production, this would send emails to org admins
        For now, just logs the warning
        """
        # Get organization admins
        from app.models.organization import OrganizationMember
        from app.models.roles import Role

        admins = (
            self.db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == organization.id,
                OrganizationMember.role.in_(
                    [Role.ORG_ADMIN.value, Role.SUPER_ADMIN.value]
                ),
                OrganizationMember.is_active == True,
            )
            .all()
        )

        # Log audit event
        audit_logger = AuditLogger(self.db)
        for admin in admins:
            await audit_logger.log_event(
                user_id=admin.user_id,
                organization_id=organization.id,
                action="quota_warning",
                resource_type="organization",
                resource_id=organization.id,
                details={
                    "quota_name": warning.quota_name,
                    "current": warning.current,
                    "limit": warning.limit,
                    "percentage": warning.percentage,
                    "warning_level": warning.warning_level,
                },
            )

        # TODO: Send email notification
        # await send_email(
        #     to=[admin.user.email for admin in admins],
        #     subject=f"Quota Warning: {warning.quota_name}",
        #     body=f"Your organization is at {warning.percentage:.1f}% of {warning.quota_name} quota"
        # )

    async def get_quota_warnings(
        self, organization_id: uuid.UUID
    ) -> list[QuotaWarning]:
        """
        Get all current quota warnings for an organization

        Returns:
            List of QuotaWarning objects for quotas above threshold
        """
        organization = (
            self.db.query(Organization)
            .filter(Organization.id == organization_id)
            .first()
        )

        if not organization:
            return []

        limits = organization.get_plan_limits()
        warnings = []

        # Check each quota
        for quota_name, quota_limit in limits.items():
            if isinstance(quota_limit, int) and quota_limit > 0:
                current_usage = await self.get_current_usage(
                    organization_id, quota_name
                )
                percentage = (current_usage / quota_limit) * 100

                if percentage >= 70:  # Threshold for warnings
                    warnings.append(
                        QuotaWarning(quota_name, current_usage, quota_limit, percentage)
                    )

        return warnings

    # ============================================================================
    # Quota Status and Reporting
    # ============================================================================

    async def get_quota_status(self, organization_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get comprehensive quota status for an organization

        Returns:
            dict with quota information:
            {
                "plan": "pro",
                "quotas": {
                    "documents_per_month": {
                        "current": 45,
                        "limit": 500,
                        "percentage": 9.0,
                        "available": 455
                    },
                    ...
                },
                "warnings": [...],
                "exceeded": [...]
            }
        """
        organization = (
            self.db.query(Organization)
            .filter(Organization.id == organization_id)
            .first()
        )

        if not organization:
            return {}

        limits = organization.get_plan_limits()
        usage = await self.get_period_usage(organization_id)

        # Map usage keys to quota limit keys
        quota_mapping = {
            "documents_per_month": "documents_created",
            "api_calls_per_day": "api_calls_today",
            "ai_queries_per_month": "ai_queries",
            "storage_gb": "storage_used_gb",
            "users": "users",
        }

        quotas = {}
        exceeded = []

        for quota_name, limit in limits.items():
            if not isinstance(limit, int):
                continue

            usage_key = quota_mapping.get(quota_name)
            if not usage_key:
                continue

            current = usage.get(usage_key, 0)

            quota_info = {
                "current": current,
                "limit": limit if limit != -1 else "unlimited",
                "available": limit - current if limit != -1 else "unlimited",
            }

            if limit > 0:
                percentage = (current / limit) * 100
                quota_info["percentage"] = round(percentage, 1)

                if percentage > 100:
                    exceeded.append(quota_name)

            quotas[quota_name] = quota_info

        warnings = await self.get_quota_warnings(organization_id)

        return {
            "plan": organization.plan.value,
            "status": organization.status.value,
            "quotas": quotas,
            "warnings": [
                {
                    "quota": w.quota_name,
                    "level": w.warning_level,
                    "percentage": round(w.percentage, 1),
                    "current": w.current,
                    "limit": w.limit,
                }
                for w in warnings
            ],
            "exceeded": exceeded,
            "features": limits.get("features", {}),
        }

    async def can_upgrade(self, organization_id: uuid.UUID) -> Dict[str, Any]:
        """
        Check if organization can upgrade and get upgrade information

        Returns:
            dict with upgrade information:
            {
                "can_upgrade": True,
                "current_plan": "free",
                "available_plans": ["pro", "enterprise"],
                "benefits": {...}
            }
        """
        organization = (
            self.db.query(Organization)
            .filter(Organization.id == organization_id)
            .first()
        )

        if not organization:
            return {"can_upgrade": False}

        current_plan = organization.plan

        # Determine available upgrades
        available_plans = []
        if current_plan == PlanTier.FREE:
            available_plans = [PlanTier.PRO, PlanTier.ENTERPRISE]
        elif current_plan == PlanTier.PRO:
            available_plans = [PlanTier.ENTERPRISE]

        if not available_plans:
            return {
                "can_upgrade": False,
                "current_plan": current_plan.value,
                "message": "You are already on the highest plan",
            }

        # Get benefits of upgrading
        benefits = {}
        current_limits = organization.get_plan_limits()

        for plan in available_plans:
            # Create temporary org with target plan to get limits
            temp_org = Organization(plan=plan)
            target_limits = temp_org.get_plan_limits()

            benefits[plan.value] = {
                "limits": target_limits,
                "improvements": {
                    key: {
                        "current": current_limits.get(key),
                        "upgraded": target_limits.get(key),
                    }
                    for key in target_limits.keys()
                    if key != "features"
                },
                "new_features": [
                    feature
                    for feature, enabled in target_limits.get("features", {}).items()
                    if enabled and not current_limits.get("features", {}).get(feature)
                ],
            }

        return {
            "can_upgrade": True,
            "current_plan": current_plan.value,
            "available_plans": [p.value for p in available_plans],
            "benefits": benefits,
        }

    # ============================================================================
    # Reset and Cleanup
    # ============================================================================

    async def reset_period_usage(self, organization_id: uuid.UUID):
        """
        Reset usage for new billing period
        Called at the start of each month
        """
        period_start, period_end = self.get_current_period()

        # Archive current usage
        current_usage = self.get_or_create_usage_record(organization_id)

        # Create new usage record for new period
        new_usage = OrganizationUsage(
            organization_id=organization_id,
            period_start=period_start,
            period_end=period_end,
            documents_created=0,
            api_calls=0,
            ai_queries=0,
            storage_used_bytes=current_usage.storage_used_bytes,  # Carry over storage
            total_cost=0,
            usage_details={},
        )

        self.db.add(new_usage)
        self.db.commit()

        # Log audit event
        audit_logger = AuditLogger(self.db)
        await audit_logger.log_event(
            user_id=None,
            organization_id=organization_id,
            action="usage_period_reset",
            resource_type="organization",
            resource_id=organization_id,
            details={"period_start": period_start.isoformat()},
        )
