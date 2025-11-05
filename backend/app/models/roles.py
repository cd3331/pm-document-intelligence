"""
Role-Based Access Control (RBAC) System
Defines roles, permissions, and their mappings for multi-tenant access control
"""

import enum
from typing import Set, Optional
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Index, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Role(str, enum.Enum):
    """
    Role hierarchy for RBAC
    Higher roles inherit permissions from lower roles
    """

    SUPER_ADMIN = "super_admin"  # System-wide admin, all permissions
    ORG_ADMIN = "org_admin"  # Organization admin, full org control
    MANAGER = "manager"  # Can manage teams, users, approve content
    MEMBER = "member"  # Regular user, standard access
    VIEWER = "viewer"  # Read-only access

    @property
    def hierarchy_level(self) -> int:
        """Get role hierarchy level (higher = more permissions)"""
        hierarchy = {
            Role.SUPER_ADMIN: 5,
            Role.ORG_ADMIN: 4,
            Role.MANAGER: 3,
            Role.MEMBER: 2,
            Role.VIEWER: 1,
        }
        return hierarchy.get(self, 0)

    def has_higher_privilege_than(self, other_role: "Role") -> bool:
        """Check if this role has higher privileges than another role"""
        return self.hierarchy_level > other_role.hierarchy_level

    def can_assign_role(self, target_role: "Role") -> bool:
        """Check if this role can assign another role"""
        # Can only assign roles at same level or lower
        return self.hierarchy_level >= target_role.hierarchy_level


class Permission(str, enum.Enum):
    """
    Granular permissions for resources
    Grouped by resource type for clarity
    """

    # Document Permissions
    DOCUMENT_READ = "document:read"
    DOCUMENT_CREATE = "document:create"
    DOCUMENT_UPDATE = "document:update"
    DOCUMENT_DELETE = "document:delete"
    DOCUMENT_APPROVE = "document:approve"
    DOCUMENT_SHARE = "document:share"

    # User Management Permissions
    USER_READ = "user:read"
    USER_INVITE = "user:invite"
    USER_UPDATE = "user:update"
    USER_REMOVE = "user:remove"
    USER_MANAGE_ROLES = "user:manage_roles"

    # Team Management Permissions
    TEAM_READ = "team:read"
    TEAM_CREATE = "team:create"
    TEAM_UPDATE = "team:update"
    TEAM_DELETE = "team:delete"
    TEAM_MANAGE_MEMBERS = "team:manage_members"

    # Organization Management Permissions
    ORG_READ = "org:read"
    ORG_UPDATE = "org:update"
    ORG_MANAGE_BILLING = "org:manage_billing"
    ORG_DELETE = "org:delete"
    ORG_MANAGE_SETTINGS = "org:manage_settings"

    # Analytics & Reporting Permissions
    ANALYTICS_VIEW = "analytics:view"
    ANALYTICS_VIEW_ALL_USERS = "analytics:view_all_users"
    ANALYTICS_EXPORT = "analytics:export"
    REPORT_GENERATE = "report:generate"
    REPORT_SCHEDULE = "report:schedule"

    # Audit & Compliance Permissions
    AUDIT_LOG_VIEW = "audit:view"
    AUDIT_LOG_EXPORT = "audit:export"

    # System Administration Permissions
    SYSTEM_SETTINGS_UPDATE = "system:settings_update"
    SYSTEM_MANAGE_ALL_ORGS = "system:manage_all_orgs"

    # API Access Permissions
    API_ACCESS = "api:access"
    API_MANAGE_KEYS = "api:manage_keys"

    @property
    def resource(self) -> str:
        """Get the resource this permission applies to"""
        return self.value.split(":")[0]

    @property
    def action(self) -> str:
        """Get the action this permission allows"""
        return self.value.split(":")[1]


# Role-Permission Mapping
# Defines which permissions each role has
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.VIEWER: {
        # Read-only access
        Permission.DOCUMENT_READ,
        Permission.USER_READ,
        Permission.TEAM_READ,
        Permission.ORG_READ,
        Permission.ANALYTICS_VIEW,
    },
    Role.MEMBER: {
        # All viewer permissions plus standard user capabilities
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_CREATE,
        Permission.DOCUMENT_UPDATE,
        Permission.DOCUMENT_SHARE,
        Permission.USER_READ,
        Permission.TEAM_READ,
        Permission.ORG_READ,
        Permission.ANALYTICS_VIEW,
        Permission.REPORT_GENERATE,
    },
    Role.MANAGER: {
        # All member permissions plus team/user management
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_CREATE,
        Permission.DOCUMENT_UPDATE,
        Permission.DOCUMENT_DELETE,
        Permission.DOCUMENT_APPROVE,
        Permission.DOCUMENT_SHARE,
        Permission.USER_READ,
        Permission.USER_INVITE,
        Permission.USER_UPDATE,
        Permission.TEAM_READ,
        Permission.TEAM_CREATE,
        Permission.TEAM_UPDATE,
        Permission.TEAM_MANAGE_MEMBERS,
        Permission.ORG_READ,
        Permission.ANALYTICS_VIEW,
        Permission.ANALYTICS_VIEW_ALL_USERS,
        Permission.ANALYTICS_EXPORT,
        Permission.REPORT_GENERATE,
        Permission.REPORT_SCHEDULE,
    },
    Role.ORG_ADMIN: {
        # All manager permissions plus org administration
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_CREATE,
        Permission.DOCUMENT_UPDATE,
        Permission.DOCUMENT_DELETE,
        Permission.DOCUMENT_APPROVE,
        Permission.DOCUMENT_SHARE,
        Permission.USER_READ,
        Permission.USER_INVITE,
        Permission.USER_UPDATE,
        Permission.USER_REMOVE,
        Permission.USER_MANAGE_ROLES,
        Permission.TEAM_READ,
        Permission.TEAM_CREATE,
        Permission.TEAM_UPDATE,
        Permission.TEAM_DELETE,
        Permission.TEAM_MANAGE_MEMBERS,
        Permission.ORG_READ,
        Permission.ORG_UPDATE,
        Permission.ORG_MANAGE_BILLING,
        Permission.ORG_MANAGE_SETTINGS,
        Permission.ANALYTICS_VIEW,
        Permission.ANALYTICS_VIEW_ALL_USERS,
        Permission.ANALYTICS_EXPORT,
        Permission.REPORT_GENERATE,
        Permission.REPORT_SCHEDULE,
        Permission.AUDIT_LOG_VIEW,
        Permission.AUDIT_LOG_EXPORT,
        Permission.API_ACCESS,
        Permission.API_MANAGE_KEYS,
    },
    Role.SUPER_ADMIN: {
        # All permissions - system-wide admin
        *[p for p in Permission]
    },
}


class RBACService:
    """
    Service class for RBAC operations
    Provides helper methods for permission checking
    """

    @staticmethod
    def get_role_permissions(role: Role) -> Set[Permission]:
        """Get all permissions for a given role"""
        return ROLE_PERMISSIONS.get(role, set())

    @staticmethod
    def has_permission(role: Role, permission: Permission) -> bool:
        """Check if a role has a specific permission"""
        role_perms = ROLE_PERMISSIONS.get(role, set())
        return permission in role_perms

    @staticmethod
    def has_any_permission(role: Role, permissions: Set[Permission]) -> bool:
        """Check if role has any of the specified permissions"""
        role_perms = ROLE_PERMISSIONS.get(role, set())
        return bool(role_perms.intersection(permissions))

    @staticmethod
    def has_all_permissions(role: Role, permissions: Set[Permission]) -> bool:
        """Check if role has all specified permissions"""
        role_perms = ROLE_PERMISSIONS.get(role, set())
        return permissions.issubset(role_perms)

    @staticmethod
    def can_perform_action(role: Role, resource: str, action: str) -> bool:
        """
        Check if role can perform an action on a resource

        Args:
            role: User's role
            resource: Resource name (e.g., 'document', 'user', 'team')
            action: Action to perform (e.g., 'read', 'create', 'delete')

        Returns:
            bool: True if role has permission
        """
        permission_string = f"{resource}:{action}"
        try:
            permission = Permission(permission_string)
            return RBACService.has_permission(role, permission)
        except ValueError:
            # Permission doesn't exist
            return False

    @staticmethod
    def get_accessible_resources(role: Role) -> dict[str, Set[str]]:
        """
        Get all resources and actions accessible to a role

        Returns:
            dict: Mapping of resource -> set of actions
        """
        role_perms = ROLE_PERMISSIONS.get(role, set())
        resources: dict[str, Set[str]] = {}

        for perm in role_perms:
            resource = perm.resource
            action = perm.action

            if resource not in resources:
                resources[resource] = set()
            resources[resource].add(action)

        return resources

    @staticmethod
    def get_minimum_role_for_permission(permission: Permission) -> Optional[Role]:
        """
        Get the minimum role required for a permission

        Returns:
            Role: Lowest role that has the permission, or None if no role has it
        """
        roles_with_permission = [
            role for role, perms in ROLE_PERMISSIONS.items() if permission in perms
        ]

        if not roles_with_permission:
            return None

        # Return role with lowest hierarchy level
        return min(roles_with_permission, key=lambda r: r.hierarchy_level)


class CustomRole(Base):
    """
    Custom roles for fine-grained permission control
    Allows organizations to define custom roles beyond default ones
    """

    __tablename__ = "custom_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(100), nullable=False)
    description = Column(String(500))

    # Base role this extends from
    base_role = Column(String(50), nullable=False)  # References Role enum

    # Additional permissions beyond base role
    additional_permissions = Column(
        String, nullable=False, default=""
    )  # Comma-separated Permission values

    # Permissions to remove from base role
    removed_permissions = Column(
        String, nullable=False, default=""
    )  # Comma-separated Permission values

    # Metadata
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=False)

    # Relationships
    assignments = relationship(
        "CustomRoleAssignment",
        back_populates="custom_role",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("idx_custom_role_org", "organization_id"),)

    def __repr__(self):
        return f"<CustomRole(name={self.name}, org={self.organization_id})>"

    def get_permissions(self) -> Set[Permission]:
        """Get all permissions for this custom role"""
        try:
            base_role = Role(self.base_role)
            base_perms = ROLE_PERMISSIONS.get(base_role, set()).copy()
        except ValueError:
            base_perms = set()

        # Add additional permissions
        if self.additional_permissions:
            for perm_str in self.additional_permissions.split(","):
                try:
                    base_perms.add(Permission(perm_str.strip()))
                except ValueError:
                    pass

        # Remove specified permissions
        if self.removed_permissions:
            for perm_str in self.removed_permissions.split(","):
                try:
                    base_perms.discard(Permission(perm_str.strip()))
                except ValueError:
                    pass

        return base_perms

    def has_permission(self, permission: Permission) -> bool:
        """Check if custom role has a specific permission"""
        return permission in self.get_permissions()


class CustomRoleAssignment(Base):
    """
    Assigns custom roles to users within an organization
    Alternative to standard role in OrganizationMember
    """

    __tablename__ = "custom_role_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    custom_role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("custom_roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional: scope to specific teams
    team_id = Column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Metadata
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    assigned_by = Column(UUID(as_uuid=True), nullable=False)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration

    # Relationships
    custom_role = relationship("CustomRole", back_populates="assignments")

    __table_args__ = (Index("idx_custom_assignment_user_org", "user_id", "organization_id"),)

    def __repr__(self):
        return f"<CustomRoleAssignment(role={self.custom_role_id}, user={self.user_id})>"

    @property
    def is_expired(self) -> bool:
        """Check if role assignment has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at


class ResourcePermission(Base):
    """
    Resource-level permissions for fine-grained access control
    Allows granting specific permissions on individual resources
    Example: User A can edit Document X even if their role doesn't normally allow it
    """

    __tablename__ = "resource_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User being granted permission
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Resource information
    resource_type = Column(String(50), nullable=False, index=True)  # document, team, folder, etc.
    resource_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Permissions granted
    permissions = Column(String, nullable=False)  # Comma-separated Permission values

    # Metadata
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    granted_by = Column(UUID(as_uuid=True), nullable=False)
    expires_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_resource_perm_user_resource", "user_id", "resource_type", "resource_id"),
    )

    def __repr__(self):
        return f"<ResourcePermission(user={self.user_id}, resource={self.resource_type}:{self.resource_id})>"

    def get_permissions(self) -> Set[Permission]:
        """Get all permissions granted by this resource permission"""
        perms = set()
        if self.permissions:
            for perm_str in self.permissions.split(","):
                try:
                    perms.add(Permission(perm_str.strip()))
                except ValueError:
                    pass
        return perms

    @property
    def is_expired(self) -> bool:
        """Check if resource permission has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def has_permission(self, permission: Permission) -> bool:
        """Check if this resource permission includes a specific permission"""
        return permission in self.get_permissions()


class PermissionCache(Base):
    """
    Cache for computed user permissions
    Improves performance by avoiding repeated permission calculations
    """

    __tablename__ = "permission_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Cached permissions as comma-separated values
    permissions = Column(String, nullable=False)

    # Cache metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)

    __table_args__ = (Index("idx_perm_cache_user_org", "user_id", "organization_id"),)

    def __repr__(self):
        return f"<PermissionCache(user={self.user_id}, org={self.organization_id})>"

    @property
    def is_expired(self) -> bool:
        """Check if cache has expired"""
        return datetime.utcnow() > self.expires_at

    def get_permissions(self) -> Set[Permission]:
        """Get cached permissions"""
        perms = set()
        if self.permissions:
            for perm_str in self.permissions.split(","):
                try:
                    perms.add(Permission(perm_str.strip()))
                except ValueError:
                    pass
        return perms


# Utility functions for common permission checks


def get_user_role_in_org(user_id: uuid.UUID, organization_id: uuid.UUID, db) -> Optional[Role]:
    """
    Get user's role in an organization
    Helper function to retrieve role from OrganizationMember
    """
    from app.models.organization import OrganizationMember

    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.is_active == True,
        )
        .first()
    )

    if not member:
        return None

    try:
        return Role(member.role)
    except ValueError:
        return None


def get_user_permissions(user_id: uuid.UUID, organization_id: uuid.UUID, db) -> Set[Permission]:
    """
    Get all permissions for a user in an organization
    Combines role permissions, custom role permissions, and resource permissions
    """
    # Check cache first
    cache = (
        db.query(PermissionCache)
        .filter(
            PermissionCache.user_id == user_id,
            PermissionCache.organization_id == organization_id,
        )
        .first()
    )

    if cache and not cache.is_expired:
        return cache.get_permissions()

    # Compute permissions
    all_permissions = set()

    # 1. Get base role permissions
    role = get_user_role_in_org(user_id, organization_id, db)
    if role:
        all_permissions.update(ROLE_PERMISSIONS.get(role, set()))

    # 2. Get custom role permissions
    custom_assignments = (
        db.query(CustomRoleAssignment)
        .filter(
            CustomRoleAssignment.user_id == user_id,
            CustomRoleAssignment.organization_id == organization_id,
        )
        .all()
    )

    for assignment in custom_assignments:
        if not assignment.is_expired and assignment.custom_role.is_active:
            all_permissions.update(assignment.custom_role.get_permissions())

    # 3. Get resource-specific permissions
    resource_perms = (
        db.query(ResourcePermission)
        .filter(
            ResourcePermission.user_id == user_id,
            ResourcePermission.organization_id == organization_id,
        )
        .all()
    )

    for res_perm in resource_perms:
        if not res_perm.is_expired:
            all_permissions.update(res_perm.get_permissions())

    # Cache the result (cache for 15 minutes)
    if cache:
        cache.permissions = ",".join([p.value for p in all_permissions])
        cache.expires_at = datetime.utcnow() + timedelta(minutes=15)
    else:
        from datetime import timedelta

        cache = PermissionCache(
            user_id=user_id,
            organization_id=organization_id,
            permissions=",".join([p.value for p in all_permissions]),
            expires_at=datetime.utcnow() + timedelta(minutes=15),
        )
        db.add(cache)

    db.commit()

    return all_permissions


def check_permission(
    user_id: uuid.UUID, organization_id: uuid.UUID, permission: Permission, db
) -> bool:
    """
    Check if user has a specific permission in an organization

    Args:
        user_id: User UUID
        organization_id: Organization UUID
        permission: Permission to check
        db: Database session

    Returns:
        bool: True if user has the permission
    """
    user_permissions = get_user_permissions(user_id, organization_id, db)
    return permission in user_permissions


def check_resource_permission(
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    resource_type: str,
    resource_id: uuid.UUID,
    permission: Permission,
    db,
) -> bool:
    """
    Check if user has permission on a specific resource

    This checks:
    1. Role-based permissions
    2. Custom role permissions
    3. Resource-specific permissions

    Args:
        user_id: User UUID
        organization_id: Organization UUID
        resource_type: Type of resource (e.g., 'document')
        resource_id: Resource UUID
        permission: Permission to check
        db: Database session

    Returns:
        bool: True if user has permission on the resource
    """
    # First check general permissions
    if check_permission(user_id, organization_id, permission, db):
        return True

    # Check resource-specific permissions
    res_perm = (
        db.query(ResourcePermission)
        .filter(
            ResourcePermission.user_id == user_id,
            ResourcePermission.organization_id == organization_id,
            ResourcePermission.resource_type == resource_type,
            ResourcePermission.resource_id == resource_id,
        )
        .first()
    )

    if res_perm and not res_perm.is_expired:
        return res_perm.has_permission(permission)

    return False
