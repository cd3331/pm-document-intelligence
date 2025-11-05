"""
RBAC Middleware for Permission Enforcement
Provides decorators and middleware for role-based access control
"""

import uuid
from collections.abc import Callable
from functools import wraps

from app.core.database import get_db
from app.models.organization import Organization, OrganizationMember, Team, TeamMember
from app.models.roles import (
    Permission,
    RBACService,
    Role,
    check_resource_permission,
)
from app.models.user import User
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session


class OrganizationContext:
    """
    Container for organization context in request
    Automatically injected by middleware
    """

    def __init__(
        self,
        organization_id: uuid.UUID | None = None,
        organization: Organization | None = None,
        member: OrganizationMember | None = None,
        role: Role | None = None,
        team_id: uuid.UUID | None = None,
        team: Team | None = None,
    ):
        self.organization_id = organization_id
        self.organization = organization
        self.member = member
        self.role = role
        self.team_id = team_id
        self.team = team

    @property
    def is_admin(self) -> bool:
        """Check if user is admin in organization"""
        if not self.role:
            return False
        return self.role in [Role.ORG_ADMIN, Role.SUPER_ADMIN]

    @property
    def is_manager_or_above(self) -> bool:
        """Check if user is manager or higher"""
        if not self.role:
            return False
        return self.role.hierarchy_level >= Role.MANAGER.hierarchy_level

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has permission in this organization"""
        if not self.role:
            return False
        return RBACService.has_permission(self.role, permission)

    def has_any_permission(self, permissions: list[Permission]) -> bool:
        """Check if user has any of the specified permissions"""
        if not self.role:
            return False
        return RBACService.has_any_permission(self.role, set(permissions))

    def has_all_permissions(self, permissions: list[Permission]) -> bool:
        """Check if user has all specified permissions"""
        if not self.role:
            return False
        return RBACService.has_all_permissions(self.role, set(permissions))

    def can_perform_action(self, resource: str, action: str) -> bool:
        """Check if user can perform action on resource"""
        if not self.role:
            return False
        return RBACService.can_perform_action(self.role, resource, action)


async def get_organization_context(
    request: Request,
    current_user: User,
    db: Session = Depends(get_db),
    organization_id: str | None = None,
) -> OrganizationContext:
    """
    Dependency to get organization context for current user
    Can be used in route handlers

    Usage:
        @app.get("/api/documents")
        async def get_documents(
            org_ctx: OrganizationContext = Depends(get_organization_context)
        ):
            if not org_ctx.has_permission(Permission.DOCUMENT_READ):
                raise HTTPException(403, "No permission")
    """
    # Get organization_id from various sources
    org_id = None

    # 1. From parameter
    if organization_id:
        try:
            org_id = uuid.UUID(organization_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid organization ID format",
            )

    # 2. From request state (set by middleware)
    elif hasattr(request.state, "organization_id"):
        org_id = request.state.organization_id

    # 3. From query parameter
    elif "organization_id" in request.query_params:
        try:
            org_id = uuid.UUID(request.query_params["organization_id"])
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid organization ID in query parameter",
            )

    # 4. From header
    elif "X-Organization-ID" in request.headers:
        try:
            org_id = uuid.UUID(request.headers["X-Organization-ID"])
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid organization ID in header",
            )

    if not org_id:
        # Get user's first organization as default
        user_orgs = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.is_active,
            )
            .first()
        )

        if not user_orgs:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a member of any organization",
            )

        org_id = user_orgs.organization_id

    # Get organization and membership
    organization = db.query(Organization).filter(Organization.id == org_id).first()

    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.organization_id == org_id,
            OrganizationMember.is_active,
        )
        .first()
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this organization",
        )

    # Get role
    try:
        role = Role(member.role)
    except ValueError:
        role = Role.MEMBER  # Default to member if invalid role

    # Get team context if available
    team_id = None
    team = None

    if hasattr(request.state, "team_id"):
        team_id = request.state.team_id
    elif "team_id" in request.query_params:
        try:
            team_id = uuid.UUID(request.query_params["team_id"])
        except ValueError:
            pass

    if team_id:
        team = db.query(Team).filter(Team.id == team_id, Team.organization_id == org_id).first()

    return OrganizationContext(
        organization_id=org_id,
        organization=organization,
        member=member,
        role=role,
        team_id=team_id,
        team=team,
    )


def require_permission(permission: Permission):
    """
    Decorator to require a specific permission for a route

    Usage:
        @app.get("/api/documents")
        @require_permission(Permission.DOCUMENT_READ)
        async def get_documents(
            current_user: User = Depends(get_current_user),
            org_ctx: OrganizationContext = Depends(get_organization_context),
            db: Session = Depends(get_db)
        ):
            return {"documents": []}
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract organization context from kwargs
            org_ctx = kwargs.get("org_ctx")
            if not org_ctx or not isinstance(org_ctx, OrganizationContext):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Organization context not found. Ensure get_organization_context dependency is used.",
                )

            # Check permission
            if not org_ctx.has_permission(permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission.value} required",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(permissions: list[Permission]):
    """
    Decorator to require any one of multiple permissions

    Usage:
        @app.get("/api/documents/manage")
        @require_any_permission([Permission.DOCUMENT_UPDATE, Permission.DOCUMENT_DELETE])
        async def manage_documents(...):
            pass
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            org_ctx = kwargs.get("org_ctx")
            if not org_ctx or not isinstance(org_ctx, OrganizationContext):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Organization context not found",
                )

            if not org_ctx.has_any_permission(permissions):
                perm_str = " or ".join([p.value for p in permissions])
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: One of [{perm_str}] required",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_all_permissions(permissions: list[Permission]):
    """
    Decorator to require all specified permissions

    Usage:
        @app.post("/api/documents/publish")
        @require_all_permissions([
            Permission.DOCUMENT_UPDATE,
            Permission.DOCUMENT_APPROVE
        ])
        async def publish_document(...):
            pass
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            org_ctx = kwargs.get("org_ctx")
            if not org_ctx or not isinstance(org_ctx, OrganizationContext):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Organization context not found",
                )

            if not org_ctx.has_all_permissions(permissions):
                perm_str = ", ".join([p.value for p in permissions])
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: All of [{perm_str}] required",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(min_role: Role):
    """
    Decorator to require a minimum role level

    Usage:
        @app.post("/api/users/invite")
        @require_role(Role.MANAGER)
        async def invite_user(...):
            pass
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            org_ctx = kwargs.get("org_ctx")
            if not org_ctx or not isinstance(org_ctx, OrganizationContext):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Organization context not found",
                )

            if not org_ctx.role or org_ctx.role.hierarchy_level < min_role.hierarchy_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {min_role.value} role or higher required",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_org_admin(func: Callable):
    """
    Decorator to require organization admin role

    Usage:
        @app.put("/api/organization/settings")
        @require_org_admin
        async def update_org_settings(...):
            pass
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        org_ctx = kwargs.get("org_ctx")
        if not org_ctx or not isinstance(org_ctx, OrganizationContext):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Organization context not found",
            )

        if not org_ctx.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: Organization admin role required",
            )

        return await func(*args, **kwargs)

    return wrapper


def require_org_feature(feature_name: str):
    """
    Decorator to require organization to have a specific feature (plan-based)

    Usage:
        @app.post("/api/documents/semantic-search")
        @require_org_feature("semantic_search")
        async def semantic_search(...):
            pass
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            org_ctx = kwargs.get("org_ctx")
            if not org_ctx or not isinstance(org_ctx, OrganizationContext):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Organization context not found",
                )

            if not org_ctx.organization.has_feature(feature_name):
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Feature '{feature_name}' not available in your plan. Please upgrade.",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


async def check_resource_access(
    current_user: User,
    resource_type: str,
    resource_id: uuid.UUID,
    permission: Permission,
    org_ctx: OrganizationContext,
    db: Session,
) -> bool:
    """
    Check if user has access to a specific resource

    This checks:
    1. Role-based permissions (general access)
    2. Resource ownership (creator/owner)
    3. Team membership (if resource is team-scoped)
    4. Resource-specific permissions

    Args:
        current_user: Current user
        resource_type: Type of resource (e.g., 'document')
        resource_id: Resource UUID
        permission: Permission to check
        org_ctx: Organization context
        db: Database session

    Returns:
        bool: True if user has access

    Usage:
        has_access = await check_resource_access(
            current_user=current_user,
            resource_type="document",
            resource_id=document_id,
            permission=Permission.DOCUMENT_UPDATE,
            org_ctx=org_ctx,
            db=db
        )
        if not has_access:
            raise HTTPException(403, "Access denied")
    """
    # Super admins have access to everything
    if org_ctx.role == Role.SUPER_ADMIN:
        return True

    # Check general permission
    if org_ctx.has_permission(permission):
        # Check if resource belongs to organization
        if resource_type == "document":
            from app.models.document import Document

            resource = (
                db.query(Document)
                .filter(
                    Document.id == resource_id,
                    Document.organization_id == org_ctx.organization_id,
                )
                .first()
            )

            if not resource:
                return False

            # Check ownership for certain permissions
            if permission in [Permission.DOCUMENT_UPDATE, Permission.DOCUMENT_DELETE]:
                # Owner or manager+ can modify
                if resource.user_id == current_user.id:
                    return True
                if org_ctx.is_manager_or_above:
                    return True
                # Check resource-specific permission
                return check_resource_permission(
                    user_id=current_user.id,
                    organization_id=org_ctx.organization_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    permission=permission,
                    db=db,
                )

            return True

        # Add more resource types as needed
        return True

    # Check resource-specific permissions
    return check_resource_permission(
        user_id=current_user.id,
        organization_id=org_ctx.organization_id,
        resource_type=resource_type,
        resource_id=resource_id,
        permission=permission,
        db=db,
    )


def require_resource_access(resource_type: str, permission: Permission):
    """
    Decorator to require access to a specific resource

    The resource ID should be in kwargs as '{resource_type}_id'

    Usage:
        @app.put("/api/documents/{document_id}")
        @require_resource_access("document", Permission.DOCUMENT_UPDATE)
        async def update_document(
            document_id: str,
            current_user: User = Depends(get_current_user),
            org_ctx: OrganizationContext = Depends(get_organization_context),
            db: Session = Depends(get_db)
        ):
            pass
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get resource ID from kwargs
            resource_id_key = f"{resource_type}_id"
            resource_id_str = kwargs.get(resource_id_key)

            if not resource_id_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Resource ID '{resource_id_key}' not found in request",
                )

            try:
                resource_id = uuid.UUID(resource_id_str)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid {resource_type} ID format",
                )

            # Get required dependencies
            current_user = kwargs.get("current_user")
            org_ctx = kwargs.get("org_ctx")
            db = kwargs.get("db")

            if not all([current_user, org_ctx, db]):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Required dependencies not found",
                )

            # Check access
            has_access = await check_resource_access(
                current_user=current_user,
                resource_type=resource_type,
                resource_id=resource_id,
                permission=permission,
                org_ctx=org_ctx,
                db=db,
            )

            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied to {resource_type}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_team_membership(func: Callable):
    """
    Decorator to require user to be a member of the team in context

    Usage:
        @app.get("/api/teams/{team_id}/documents")
        @require_team_membership
        async def get_team_documents(
            team_id: str,
            org_ctx: OrganizationContext = Depends(get_organization_context),
            db: Session = Depends(get_db)
        ):
            pass
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        org_ctx = kwargs.get("org_ctx")
        current_user = kwargs.get("current_user")
        db = kwargs.get("db")

        if not all([org_ctx, current_user, db]):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Required dependencies not found",
            )

        # Get team_id from kwargs or context
        team_id = kwargs.get("team_id")
        if team_id:
            try:
                team_id = uuid.UUID(team_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid team ID format",
                )
        elif org_ctx.team_id:
            team_id = org_ctx.team_id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Team ID not found in request",
            )

        # Check team membership
        membership = (
            db.query(TeamMember)
            .filter(TeamMember.team_id == team_id, TeamMember.user_id == current_user.id)
            .first()
        )

        if not membership and not org_ctx.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a member of this team",
            )

        return await func(*args, **kwargs)

    return wrapper


def check_quota(quota_name: str):
    """
    Decorator to check if organization has quota available

    Usage:
        @app.post("/api/documents")
        @check_quota("documents_per_month")
        async def create_document(
            org_ctx: OrganizationContext = Depends(get_organization_context),
            db: Session = Depends(get_db)
        ):
            pass
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            org_ctx = kwargs.get("org_ctx")
            db = kwargs.get("db")

            if not all([org_ctx, db]):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Required dependencies not found",
                )

            # Get plan limits
            limits = org_ctx.organization.get_plan_limits()
            quota_limit = limits.get(quota_name)

            if quota_limit is None:
                # Quota not defined, allow
                return await func(*args, **kwargs)

            if quota_limit == -1:
                # Unlimited quota
                return await func(*args, **kwargs)

            # Check current usage (this would need to be implemented in quota_manager)
            from app.services.quota_manager import QuotaManager

            quota_manager = QuotaManager(db)

            current_usage = await quota_manager.get_current_usage(
                org_ctx.organization_id, quota_name
            )

            if current_usage >= quota_limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Quota exceeded: {quota_name}. Current: {current_usage}, Limit: {quota_limit}. Please upgrade your plan.",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Middleware for automatic organization context injection
class OrganizationContextMiddleware:
    """
    Middleware to automatically inject organization context into request state
    This makes organization context available throughout the request lifecycle
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Organization ID can come from:
            # 1. X-Organization-ID header
            # 2. Query parameter
            # 3. Path parameter (would need path parsing)

            headers = dict(scope.get("headers", []))
            org_id_header = headers.get(b"x-organization-id")

            if org_id_header:
                try:
                    org_id = uuid.UUID(org_id_header.decode())
                    # Store in request state
                    if "state" not in scope:
                        scope["state"] = {}
                    scope["state"]["organization_id"] = org_id
                except (ValueError, AttributeError):
                    pass

        await self.app(scope, receive, send)
