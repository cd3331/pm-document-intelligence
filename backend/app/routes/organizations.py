"""
Organization Management API Routes
Endpoints for managing organizations, teams, members, and invitations
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr, Field
import uuid
import secrets

from app.core.database import get_db
from app.models.user import User
from app.models.organization import (
    Organization,
    OrganizationMember,
    Team,
    TeamMember,
    OrganizationInvitation,
    OrganizationUsage,
    OrganizationStatus,
    PlanTier,
)
from app.models.roles import Role, Permission
from app.middleware.rbac import (
    get_organization_context,
    OrganizationContext,
    require_permission,
    require_role,
    require_org_admin,
)
from app.core.auth import get_current_user
from app.services.audit_logger import AuditLogger
from app.services.invitation_service import InvitationService
from app.services.quota_manager import QuotaManager


router = APIRouter(prefix="/api/organizations", tags=["organizations"])


# ============================================================================
# Pydantic Models for Request/Response
# ============================================================================


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: Optional[str] = Field(None, min_length=2, max_length=255)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    custom_domain: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    status: str
    created_at: datetime
    member_count: int
    team_count: int

    class Config:
        from_attributes = True


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None


class TeamResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    member_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class MemberResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    username: str
    email: str
    role: str
    is_active: bool
    joined_at: datetime

    class Config:
        from_attributes = True


class MemberRoleUpdate(BaseModel):
    role: str


class InviteUserRequest(BaseModel):
    email: EmailStr
    role: str
    team_ids: List[uuid.UUID] = Field(default_factory=list)
    expires_in_days: int = Field(default=7, ge=1, le=30)


class InvitationResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    status: str
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class UsageResponse(BaseModel):
    current_usage: dict
    limits: dict
    period_start: datetime
    period_end: datetime


# ============================================================================
# Organization Endpoints
# ============================================================================


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new organization
    The creator automatically becomes the organization admin
    """
    # Generate slug if not provided
    slug = org_data.slug or org_data.name.lower().replace(" ", "-")

    # Check if slug already exists
    existing = db.query(Organization).filter(Organization.slug == slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Organization with slug '{slug}' already exists",
        )

    # Create organization
    organization = Organization(
        name=org_data.name,
        slug=slug,
        contact_email=org_data.contact_email,
        contact_phone=org_data.contact_phone,
        plan=PlanTier.FREE,
        status=OrganizationStatus.ACTIVE,
        created_by=current_user.id,
    )

    db.add(organization)
    db.flush()

    # Add creator as organization admin
    member = OrganizationMember(
        organization_id=organization.id,
        user_id=current_user.id,
        role=Role.ORG_ADMIN.value,
        is_active=True,
    )

    db.add(member)

    # Log audit event
    audit_logger = AuditLogger(db)
    await audit_logger.log_event(
        user_id=current_user.id,
        organization_id=organization.id,
        action="organization_created",
        resource_type="organization",
        resource_id=organization.id,
        details={"name": organization.name, "slug": organization.slug},
    )

    db.commit()
    db.refresh(organization)

    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        plan=organization.plan.value,
        status=organization.status.value,
        created_at=organization.created_at,
        member_count=1,
        team_count=0,
    )


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
):
    """Get organization details"""
    organization = org_ctx.organization

    # Count members and teams
    member_count = (
        db.query(func.count(OrganizationMember.id))
        .filter(
            OrganizationMember.organization_id == organization.id,
            OrganizationMember.is_active == True,
        )
        .scalar()
    )

    team_count = (
        db.query(func.count(Team.id)).filter(Team.organization_id == organization.id).scalar()
    )

    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        plan=organization.plan.value,
        status=organization.status.value,
        created_at=organization.created_at,
        member_count=member_count,
        team_count=team_count,
    )


@router.put("/{organization_id}")
@require_permission(Permission.ORG_UPDATE)
async def update_organization(
    organization_id: str,
    org_update: OrganizationUpdate,
    current_user: User = Depends(get_current_user),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
):
    """Update organization details (requires ORG_UPDATE permission)"""
    organization = org_ctx.organization

    # Update fields
    update_data = org_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(organization, field, value)

    organization.updated_at = datetime.utcnow()

    # Log audit event
    audit_logger = AuditLogger(db)
    await audit_logger.log_event(
        user_id=current_user.id,
        organization_id=organization.id,
        action="organization_updated",
        resource_type="organization",
        resource_id=organization.id,
        details=update_data,
    )

    db.commit()
    db.refresh(organization)

    return {
        "message": "Organization updated successfully",
        "organization": organization,
    }


@router.delete("/{organization_id}")
@require_org_admin
async def delete_organization(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
):
    """
    Delete organization (requires ORG_ADMIN role)
    This will cascade delete all related data
    """
    organization = org_ctx.organization

    # Only super_admin or the creator can delete
    if org_ctx.role != Role.SUPER_ADMIN and organization.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the organization creator or super admin can delete the organization",
        )

    # Log audit event before deletion
    audit_logger = AuditLogger(db)
    await audit_logger.log_event(
        user_id=current_user.id,
        organization_id=organization.id,
        action="organization_deleted",
        resource_type="organization",
        resource_id=organization.id,
        details={"name": organization.name},
    )

    db.delete(organization)
    db.commit()

    return {"message": "Organization deleted successfully"}


@router.get("/{organization_id}/usage", response_model=UsageResponse)
async def get_organization_usage(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
):
    """Get current usage statistics for the organization"""
    quota_manager = QuotaManager(db)

    # Get current period usage
    current_usage = await quota_manager.get_period_usage(org_ctx.organization_id)
    limits = org_ctx.organization.get_plan_limits()

    # Determine period (current month)
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        period_end = period_start.replace(year=now.year + 1, month=1)
    else:
        period_end = period_start.replace(month=now.month + 1)

    return UsageResponse(
        current_usage=current_usage,
        limits=limits,
        period_start=period_start,
        period_end=period_end,
    )


# ============================================================================
# Organization Member Endpoints
# ============================================================================


@router.get("/{organization_id}/members", response_model=List[MemberResponse])
@require_permission(Permission.USER_READ)
async def list_organization_members(
    organization_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
):
    """List all members of the organization"""
    members = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == org_ctx.organization_id,
            OrganizationMember.is_active == True,
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []
    for member in members:
        user = db.query(User).filter(User.id == member.user_id).first()
        if user:
            result.append(
                MemberResponse(
                    id=member.id,
                    user_id=user.id,
                    username=user.username,
                    email=user.email,
                    role=member.role,
                    is_active=member.is_active,
                    joined_at=member.joined_at,
                )
            )

    return result


@router.put("/{organization_id}/members/{user_id}/role")
@require_permission(Permission.USER_MANAGE_ROLES)
async def update_member_role(
    organization_id: str,
    user_id: str,
    role_update: MemberRoleUpdate,
    current_user: User = Depends(get_current_user),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
):
    """Update a member's role in the organization"""
    try:
        target_user_id = uuid.UUID(user_id)
        new_role = Role(role_update.role)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid input: {str(e)}"
        )

    # Check if current user can assign this role
    if not org_ctx.role.can_assign_role(new_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You cannot assign the role '{new_role.value}'",
        )

    # Get member
    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == org_ctx.organization_id,
            OrganizationMember.user_id == target_user_id,
        )
        .first()
    )

    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    # Prevent changing own role
    if target_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role",
        )

    old_role = member.role
    member.role = new_role.value

    # Log audit event
    audit_logger = AuditLogger(db)
    await audit_logger.log_event(
        user_id=current_user.id,
        organization_id=org_ctx.organization_id,
        action="member_role_updated",
        resource_type="organization_member",
        resource_id=member.id,
        details={
            "user_id": str(target_user_id),
            "old_role": old_role,
            "new_role": new_role.value,
        },
    )

    db.commit()

    return {"message": "Member role updated successfully", "new_role": new_role.value}


@router.delete("/{organization_id}/members/{user_id}")
@require_permission(Permission.USER_REMOVE)
async def remove_member(
    organization_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
):
    """Remove a member from the organization"""
    try:
        target_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")

    # Cannot remove self
    if target_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove yourself from the organization",
        )

    # Get member
    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == org_ctx.organization_id,
            OrganizationMember.user_id == target_user_id,
        )
        .first()
    )

    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    # Check if current user can remove this member
    try:
        member_role = Role(member.role)
        if member_role.hierarchy_level >= org_ctx.role.hierarchy_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot remove a member with equal or higher role",
            )
    except ValueError:
        pass

    # Log audit event
    audit_logger = AuditLogger(db)
    await audit_logger.log_event(
        user_id=current_user.id,
        organization_id=org_ctx.organization_id,
        action="member_removed",
        resource_type="organization_member",
        resource_id=member.id,
        details={"user_id": str(target_user_id), "role": member.role},
    )

    db.delete(member)
    db.commit()

    return {"message": "Member removed successfully"}


# ============================================================================
# Invitation Endpoints
# ============================================================================


@router.post("/{organization_id}/invitations", response_model=InvitationResponse)
@require_permission(Permission.USER_INVITE)
async def invite_user(
    organization_id: str,
    invite_data: InviteUserRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
):
    """
    Invite a user to the organization
    Sends an email with invitation link
    """
    # Validate role
    try:
        role = Role(invite_data.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {invite_data.role}",
        )

    # Check if current user can assign this role
    if not org_ctx.role.can_assign_role(role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You cannot invite users with role '{role.value}'",
        )

    # Check if user already exists in organization
    existing_user = db.query(User).filter(User.email == invite_data.email).first()
    if existing_user:
        existing_member = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == org_ctx.organization_id,
                OrganizationMember.user_id == existing_user.id,
            )
            .first()
        )
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this organization",
            )

    # Check quota
    if not org_ctx.organization.can_add_user():
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="User limit reached for your plan. Please upgrade to add more users.",
        )

    # Create invitation
    invitation_service = InvitationService(db)
    invitation = await invitation_service.create_invitation(
        organization_id=org_ctx.organization_id,
        email=invite_data.email,
        role=role.value,
        team_ids=invite_data.team_ids,
        invited_by=current_user.id,
        expires_in_days=invite_data.expires_in_days,
    )

    # Send invitation email in background
    background_tasks.add_task(
        invitation_service.send_invitation_email,
        invitation_id=invitation.id,
        organization_name=org_ctx.organization.name,
    )

    # Log audit event
    audit_logger = AuditLogger(db)
    await audit_logger.log_event(
        user_id=current_user.id,
        organization_id=org_ctx.organization_id,
        action="user_invited",
        resource_type="invitation",
        resource_id=invitation.id,
        details={"email": invite_data.email, "role": role.value},
    )

    return InvitationResponse(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role,
        status=invitation.status,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
    )


@router.get("/{organization_id}/invitations", response_model=List[InvitationResponse])
@require_permission(Permission.USER_READ)
async def list_invitations(
    organization_id: str,
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
):
    """List all invitations for the organization"""
    query = db.query(OrganizationInvitation).filter(
        OrganizationInvitation.organization_id == org_ctx.organization_id
    )

    if status:
        query = query.filter(OrganizationInvitation.status == status)

    invitations = query.order_by(OrganizationInvitation.created_at.desc()).all()

    return [
        InvitationResponse(
            id=inv.id,
            email=inv.email,
            role=inv.role,
            status=inv.status,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
        )
        for inv in invitations
    ]


@router.delete("/{organization_id}/invitations/{invitation_id}")
@require_permission(Permission.USER_INVITE)
async def cancel_invitation(
    organization_id: str,
    invitation_id: str,
    current_user: User = Depends(get_current_user),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
):
    """Cancel a pending invitation"""
    try:
        inv_id = uuid.UUID(invitation_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid invitation ID")

    invitation = (
        db.query(OrganizationInvitation)
        .filter(
            OrganizationInvitation.id == inv_id,
            OrganizationInvitation.organization_id == org_ctx.organization_id,
        )
        .first()
    )

    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    if invitation.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel invitation with status '{invitation.status}'",
        )

    invitation.status = "cancelled"

    # Log audit event
    audit_logger = AuditLogger(db)
    await audit_logger.log_event(
        user_id=current_user.id,
        organization_id=org_ctx.organization_id,
        action="invitation_cancelled",
        resource_type="invitation",
        resource_id=invitation.id,
        details={"email": invitation.email},
    )

    db.commit()

    return {"message": "Invitation cancelled successfully"}


# ============================================================================
# Team Endpoints
# ============================================================================


@router.post(
    "/{organization_id}/teams",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
)
@require_permission(Permission.TEAM_CREATE)
async def create_team(
    organization_id: str,
    team_data: TeamCreate,
    current_user: User = Depends(get_current_user),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
):
    """Create a new team in the organization"""
    # Check if team name already exists in organization
    existing = (
        db.query(Team)
        .filter(Team.organization_id == org_ctx.organization_id, Team.name == team_data.name)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Team with name '{team_data.name}' already exists in this organization",
        )

    # Create team
    team = Team(
        organization_id=org_ctx.organization_id,
        name=team_data.name,
        description=team_data.description,
        created_by=current_user.id,
    )

    db.add(team)
    db.flush()

    # Add creator as team member
    team_member = TeamMember(team_id=team.id, user_id=current_user.id, added_by=current_user.id)

    db.add(team_member)

    # Log audit event
    audit_logger = AuditLogger(db)
    await audit_logger.log_event(
        user_id=current_user.id,
        organization_id=org_ctx.organization_id,
        action="team_created",
        resource_type="team",
        resource_id=team.id,
        details={"name": team.name},
    )

    db.commit()
    db.refresh(team)

    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        member_count=1,
        created_at=team.created_at,
    )


@router.get("/{organization_id}/teams", response_model=List[TeamResponse])
@require_permission(Permission.TEAM_READ)
async def list_teams(
    organization_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
):
    """List all teams in the organization"""
    teams = (
        db.query(Team)
        .filter(Team.organization_id == org_ctx.organization_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []
    for team in teams:
        member_count = (
            db.query(func.count(TeamMember.id)).filter(TeamMember.team_id == team.id).scalar()
        )

        result.append(
            TeamResponse(
                id=team.id,
                name=team.name,
                description=team.description,
                member_count=member_count,
                created_at=team.created_at,
            )
        )

    return result


@router.get("/{organization_id}/teams/{team_id}", response_model=TeamResponse)
@require_permission(Permission.TEAM_READ)
async def get_team(
    organization_id: str,
    team_id: str,
    current_user: User = Depends(get_current_user),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
):
    """Get team details"""
    try:
        team_uuid = uuid.UUID(team_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid team ID")

    team = (
        db.query(Team)
        .filter(Team.id == team_uuid, Team.organization_id == org_ctx.organization_id)
        .first()
    )

    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    member_count = (
        db.query(func.count(TeamMember.id)).filter(TeamMember.team_id == team.id).scalar()
    )

    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        member_count=member_count,
        created_at=team.created_at,
    )


@router.put("/{organization_id}/teams/{team_id}")
@require_permission(Permission.TEAM_UPDATE)
async def update_team(
    organization_id: str,
    team_id: str,
    team_update: TeamUpdate,
    current_user: User = Depends(get_current_user),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
):
    """Update team details"""
    try:
        team_uuid = uuid.UUID(team_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid team ID")

    team = (
        db.query(Team)
        .filter(Team.id == team_uuid, Team.organization_id == org_ctx.organization_id)
        .first()
    )

    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    # Update fields
    update_data = team_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(team, field, value)

    team.updated_at = datetime.utcnow()

    # Log audit event
    audit_logger = AuditLogger(db)
    await audit_logger.log_event(
        user_id=current_user.id,
        organization_id=org_ctx.organization_id,
        action="team_updated",
        resource_type="team",
        resource_id=team.id,
        details=update_data,
    )

    db.commit()

    return {"message": "Team updated successfully"}


@router.delete("/{organization_id}/teams/{team_id}")
@require_permission(Permission.TEAM_DELETE)
async def delete_team(
    organization_id: str,
    team_id: str,
    current_user: User = Depends(get_current_user),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
):
    """Delete a team"""
    try:
        team_uuid = uuid.UUID(team_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid team ID")

    team = (
        db.query(Team)
        .filter(Team.id == team_uuid, Team.organization_id == org_ctx.organization_id)
        .first()
    )

    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    # Log audit event
    audit_logger = AuditLogger(db)
    await audit_logger.log_event(
        user_id=current_user.id,
        organization_id=org_ctx.organization_id,
        action="team_deleted",
        resource_type="team",
        resource_id=team.id,
        details={"name": team.name},
    )

    db.delete(team)
    db.commit()

    return {"message": "Team deleted successfully"}


@router.get("/{organization_id}/teams/{team_id}/members", response_model=List[MemberResponse])
@require_permission(Permission.TEAM_READ)
async def list_team_members(
    organization_id: str,
    team_id: str,
    current_user: User = Depends(get_current_user),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
):
    """List all members of a team"""
    try:
        team_uuid = uuid.UUID(team_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid team ID")

    # Verify team exists and belongs to organization
    team = (
        db.query(Team)
        .filter(Team.id == team_uuid, Team.organization_id == org_ctx.organization_id)
        .first()
    )

    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    members = db.query(TeamMember).filter(TeamMember.team_id == team_uuid).all()

    result = []
    for member in members:
        user = db.query(User).filter(User.id == member.user_id).first()
        if user:
            result.append(
                MemberResponse(
                    id=member.id,
                    user_id=user.id,
                    username=user.username,
                    email=user.email,
                    role=member.role or "member",
                    is_active=True,
                    joined_at=member.joined_at,
                )
            )

    return result


@router.post("/{organization_id}/teams/{team_id}/members/{user_id}")
@require_permission(Permission.TEAM_MANAGE_MEMBERS)
async def add_team_member(
    organization_id: str,
    team_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
):
    """Add a member to a team"""
    try:
        team_uuid = uuid.UUID(team_id)
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format")

    # Verify team exists
    team = (
        db.query(Team)
        .filter(Team.id == team_uuid, Team.organization_id == org_ctx.organization_id)
        .first()
    )

    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    # Verify user is organization member
    org_member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == org_ctx.organization_id,
            OrganizationMember.user_id == user_uuid,
            OrganizationMember.is_active == True,
        )
        .first()
    )

    if not org_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this organization",
        )

    # Check if already a team member
    existing = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_uuid, TeamMember.user_id == user_uuid)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this team",
        )

    # Add team member
    team_member = TeamMember(team_id=team_uuid, user_id=user_uuid, added_by=current_user.id)

    db.add(team_member)

    # Log audit event
    audit_logger = AuditLogger(db)
    await audit_logger.log_event(
        user_id=current_user.id,
        organization_id=org_ctx.organization_id,
        action="team_member_added",
        resource_type="team",
        resource_id=team.id,
        details={"user_id": str(user_uuid), "team_name": team.name},
    )

    db.commit()

    return {"message": "Member added to team successfully"}


@router.delete("/{organization_id}/teams/{team_id}/members/{user_id}")
@require_permission(Permission.TEAM_MANAGE_MEMBERS)
async def remove_team_member(
    organization_id: str,
    team_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
):
    """Remove a member from a team"""
    try:
        team_uuid = uuid.UUID(team_id)
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format")

    # Get team member
    team_member = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_uuid, TeamMember.user_id == user_uuid)
        .first()
    )

    if not team_member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found")

    # Log audit event
    audit_logger = AuditLogger(db)
    await audit_logger.log_event(
        user_id=current_user.id,
        organization_id=org_ctx.organization_id,
        action="team_member_removed",
        resource_type="team",
        resource_id=team_uuid,
        details={"user_id": str(user_uuid)},
    )

    db.delete(team_member)
    db.commit()

    return {"message": "Member removed from team successfully"}
