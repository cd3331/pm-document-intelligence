"""
Organization and Team Models for Multi-Tenancy
Implements enterprise-grade multi-tenancy with organizations, teams, and plans
"""

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    Integer,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
import enum

from app.core.database import Base


class PlanTier(str, enum.Enum):
    """Subscription plan tiers"""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class OrganizationStatus(str, enum.Enum):
    """Organization status"""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    TRIAL = "trial"


class Organization(Base):
    """
    Organization model for multi-tenancy
    Each organization represents a separate tenant with isolated data
    """

    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)

    # Plan and billing
    plan = Column(SQLEnum(PlanTier), default=PlanTier.FREE, nullable=False, index=True)
    status = Column(
        SQLEnum(OrganizationStatus), default=OrganizationStatus.ACTIVE, nullable=False
    )
    trial_ends_at = Column(DateTime, nullable=True)
    subscription_id = Column(String(255), nullable=True)  # External billing system ID

    # Limits based on plan
    settings = Column(JSONB, default=dict, nullable=False)

    # Branding
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), nullable=True)  # Hex color
    custom_domain = Column(String(255), nullable=True)

    # Contact info
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)

    # Address
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    created_by = Column(UUID(as_uuid=True), nullable=True)  # User who created org

    # Relationships
    members = relationship(
        "OrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    teams = relationship(
        "Team", back_populates="organization", cascade="all, delete-orphan"
    )
    documents = relationship("Document", back_populates="organization")

    def __repr__(self):
        return f"<Organization(name={self.name}, plan={self.plan})>"

    @property
    def is_active(self) -> bool:
        """Check if organization is active"""
        return self.status == OrganizationStatus.ACTIVE

    @property
    def is_trial(self) -> bool:
        """Check if organization is in trial"""
        return self.status == OrganizationStatus.TRIAL

    @property
    def trial_days_remaining(self) -> int:
        """Get remaining trial days"""
        if not self.trial_ends_at:
            return 0
        delta = self.trial_ends_at - datetime.utcnow()
        return max(0, delta.days)

    def get_plan_limits(self) -> dict:
        """Get plan limits based on tier"""
        limits = {
            PlanTier.FREE: {
                "documents_per_month": 50,
                "storage_gb": 1,
                "api_calls_per_day": 100,
                "users": 3,
                "teams": 1,
                "ai_queries_per_month": 100,
                "features": {
                    "semantic_search": False,
                    "ai_agents": True,
                    "custom_branding": False,
                    "sso": False,
                    "audit_logs": False,
                    "api_access": False,
                    "priority_support": False,
                },
            },
            PlanTier.PRO: {
                "documents_per_month": 500,
                "storage_gb": 50,
                "api_calls_per_day": 1000,
                "users": 20,
                "teams": 10,
                "ai_queries_per_month": 1000,
                "features": {
                    "semantic_search": True,
                    "ai_agents": True,
                    "custom_branding": True,
                    "sso": False,
                    "audit_logs": True,
                    "api_access": True,
                    "priority_support": False,
                },
            },
            PlanTier.ENTERPRISE: {
                "documents_per_month": -1,  # Unlimited
                "storage_gb": -1,  # Unlimited
                "api_calls_per_day": -1,  # Unlimited
                "users": -1,  # Unlimited
                "teams": -1,  # Unlimited
                "ai_queries_per_month": -1,  # Unlimited
                "features": {
                    "semantic_search": True,
                    "ai_agents": True,
                    "custom_branding": True,
                    "sso": True,
                    "audit_logs": True,
                    "api_access": True,
                    "priority_support": True,
                    "dedicated_support": True,
                    "custom_integrations": True,
                },
            },
        }

        plan_limits = limits.get(self.plan, limits[PlanTier.FREE])

        # Override with custom settings if present
        if self.settings and "limits" in self.settings:
            plan_limits.update(self.settings["limits"])

        return plan_limits

    def has_feature(self, feature_name: str) -> bool:
        """Check if organization has access to a feature"""
        limits = self.get_plan_limits()
        return limits["features"].get(feature_name, False)

    def can_add_user(self) -> bool:
        """Check if organization can add more users"""
        limits = self.get_plan_limits()
        max_users = limits["users"]

        if max_users == -1:  # Unlimited
            return True

        current_users = len(self.members)
        return current_users < max_users


class Team(Base):
    """
    Team model for organizing users within an organization
    """

    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)

    # Settings
    settings = Column(JSONB, default=dict, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    created_by = Column(UUID(as_uuid=True), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="teams")
    members = relationship(
        "TeamMember", back_populates="team", cascade="all, delete-orphan"
    )

    # Unique constraint: team name must be unique within organization
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uix_org_team_name"),
        Index("idx_team_org_id", "organization_id"),
    )

    def __repr__(self):
        return f"<Team(name={self.name}, org={self.organization_id})>"


class OrganizationMember(Base):
    """
    Organization membership - links users to organizations with roles
    """

    __tablename__ = "organization_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Role in organization (references roles.py Role enum)
    role = Column(String(50), nullable=False, default="member")

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Metadata
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    invited_by = Column(UUID(as_uuid=True), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="organizations")

    # Unique constraint: user can only be a member once per organization
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uix_org_user"),
        Index("idx_org_member_user", "user_id"),
        Index("idx_org_member_role", "role"),
    )

    def __repr__(self):
        return f"<OrganizationMember(org={self.organization_id}, user={self.user_id}, role={self.role})>"


class TeamMember(Base):
    """
    Team membership - links users to teams
    """

    __tablename__ = "team_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Role within team (optional, inherits from org role if not set)
    role = Column(String(50), nullable=True)

    # Metadata
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    added_by = Column(UUID(as_uuid=True), nullable=True)

    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="teams")

    # Unique constraint: user can only be in team once
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uix_team_user"),
        Index("idx_team_member_user", "user_id"),
    )

    def __repr__(self):
        return f"<TeamMember(team={self.team_id}, user={self.user_id})>"


class OrganizationInvitation(Base):
    """
    Invitation system for adding users to organizations
    """

    __tablename__ = "organization_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False)

    # Invitation token
    token = Column(String(255), unique=True, nullable=False, index=True)

    # Status
    status = Column(
        String(20), default="pending", nullable=False
    )  # pending, accepted, expired, cancelled

    # Teams to add user to upon acceptance
    teams = Column(JSONB, default=list, nullable=False)  # List of team IDs

    # Expiration
    expires_at = Column(DateTime, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    invited_by = Column(UUID(as_uuid=True), nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    accepted_by = Column(UUID(as_uuid=True), nullable=True)

    # Relationships
    organization = relationship("Organization")

    __table_args__ = (
        Index("idx_invitation_email_org", "email", "organization_id"),
        Index("idx_invitation_status", "status"),
    )

    def __repr__(self):
        return f"<OrganizationInvitation(email={self.email}, org={self.organization_id}, status={self.status})>"

    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired"""
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if invitation is valid"""
        return self.status == "pending" and not self.is_expired


class OrganizationUsage(Base):
    """
    Track organization usage for quota management
    """

    __tablename__ = "organization_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Time period
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)

    # Usage metrics
    documents_created = Column(Integer, default=0, nullable=False)
    api_calls = Column(Integer, default=0, nullable=False)
    ai_queries = Column(Integer, default=0, nullable=False)
    storage_used_bytes = Column(Integer, default=0, nullable=False)

    # Cost tracking
    total_cost = Column(Integer, default=0, nullable=False)  # In cents

    # Detailed breakdown
    usage_details = Column(JSONB, default=dict, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    organization = relationship("Organization")

    __table_args__ = (
        UniqueConstraint("organization_id", "period_start", name="uix_org_period"),
        Index("idx_usage_org_period", "organization_id", "period_start"),
    )

    def __repr__(self):
        return f"<OrganizationUsage(org={self.organization_id}, period={self.period_start})>"

    @property
    def storage_used_gb(self) -> float:
        """Get storage used in GB"""
        return self.storage_used_bytes / (1024**3)


# Update User model to include organization relationships
# This would be added to app/models/user.py:
"""
from sqlalchemy.orm import relationship

class User(Base):
    # ... existing fields ...

    # Organization relationships
    organizations = relationship("OrganizationMember", back_populates="user")
    teams = relationship("TeamMember", back_populates="user")

    def get_organization_role(self, organization_id: UUID) -> Optional[str]:
        '''Get user's role in an organization'''
        for org_member in self.organizations:
            if org_member.organization_id == organization_id:
                return org_member.role
        return None

    def is_org_admin(self, organization_id: UUID) -> bool:
        '''Check if user is admin of organization'''
        role = self.get_organization_role(organization_id)
        return role in ['org_admin', 'super_admin']
"""

# Update Document model to include organization_id
# This would be added to app/models/document.py:
"""
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class Document(Base):
    # ... existing fields ...

    # Multi-tenancy
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    organization = relationship("Organization", back_populates="documents")
"""
