"""Add multi-tenancy and RBAC support

Revision ID: 0006_multi_tenancy
Revises: 0005_analytics
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '0006_multi_tenancy'
down_revision = '0005_analytics'  # Update with actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    # Create organizations table
    op.create_table('organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('slug', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('plan', sa.String(50), nullable=False, index=True, server_default='free'),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('trial_ends_at', sa.DateTime(), nullable=True),
        sa.Column('subscription_id', sa.String(255), nullable=True),
        sa.Column('settings', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('primary_color', sa.String(7), nullable=True),
        sa.Column('custom_domain', sa.String(255), nullable=True),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('contact_phone', sa.String(50), nullable=True),
        sa.Column('address_line1', sa.String(255), nullable=True),
        sa.Column('address_line2', sa.String(255), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True)
    )

    # Create teams table
    op.create_table('teams',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column('settings', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('organization_id', 'name', name='uix_org_team_name')
    )
    op.create_index('idx_team_org_id', 'teams', ['organization_id'])

    # Create organization_members table
    op.create_table('organization_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('role', sa.String(50), nullable=False, server_default='member'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('joined_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('organization_id', 'user_id', name='uix_org_user')
    )
    op.create_index('idx_org_member_user', 'organization_members', ['user_id'])
    op.create_index('idx_org_member_role', 'organization_members', ['role'])

    # Create team_members table
    op.create_table('team_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('team_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('role', sa.String(50), nullable=True),
        sa.Column('joined_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('added_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('team_id', 'user_id', name='uix_team_user')
    )
    op.create_index('idx_team_member_user', 'team_members', ['user_id'])

    # Create organization_invitations table
    op.create_table('organization_invitations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('email', sa.String(255), nullable=False, index=True),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('token', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('teams', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('accepted_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE')
    )
    op.create_index('idx_invitation_email_org', 'organization_invitations', ['email', 'organization_id'])
    op.create_index('idx_invitation_status', 'organization_invitations', ['status'])

    # Create organization_usage table
    op.create_table('organization_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('period_start', sa.DateTime(), nullable=False, index=True),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('documents_created', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('api_calls', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ai_queries', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('storage_used_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('total_cost', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('usage_details', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('organization_id', 'period_start', name='uix_org_period')
    )
    op.create_index('idx_usage_org_period', 'organization_usage', ['organization_id', 'period_start'])

    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('user_email', sa.String(255), nullable=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('action', sa.String(100), nullable=False, index=True),
        sa.Column('category', sa.String(50), nullable=False, index=True),
        sa.Column('resource_type', sa.String(50), nullable=True, index=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('request_method', sa.String(10), nullable=True),
        sa.Column('request_path', sa.String(500), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('status_code', sa.String(10), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('changes', postgresql.JSONB(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()'), index=True),
        sa.Column('sensitivity_level', sa.String(20), server_default='normal')
    )
    op.create_index('idx_audit_user_timestamp', 'audit_logs', ['user_id', 'timestamp'])
    op.create_index('idx_audit_org_timestamp', 'audit_logs', ['organization_id', 'timestamp'])
    op.create_index('idx_audit_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('idx_audit_action_timestamp', 'audit_logs', ['action', 'timestamp'])
    op.create_index('idx_audit_category_timestamp', 'audit_logs', ['category', 'timestamp'])

    # Create custom_roles table
    op.create_table('custom_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('base_role', sa.String(50), nullable=False),
        sa.Column('additional_permissions', sa.Text(), nullable=False, server_default=''),
        sa.Column('removed_permissions', sa.Text(), nullable=False, server_default=''),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE')
    )
    op.create_index('idx_custom_role_org', 'custom_roles', ['organization_id'])

    # Create permission_cache table
    op.create_table('permission_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('permissions', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(), nullable=False, index=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE')
    )
    op.create_index('idx_perm_cache_user_org', 'permission_cache', ['user_id', 'organization_id'])

    # Add organization_id to existing tables
    op.add_column('documents', sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True, index=True))
    op.create_foreign_key('fk_documents_organization', 'documents', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')

    # Note: After running this migration, run the data migration script to:
    # 1. Create a default organization for existing users
    # 2. Migrate existing documents to the default organization
    # 3. Create organization memberships for existing users


def downgrade():
    # Remove foreign keys first
    op.drop_constraint('fk_documents_organization', 'documents', type_='foreignkey')

    # Remove organization_id from existing tables
    op.drop_column('documents', 'organization_id')

    # Drop all new tables (in reverse order of creation)
    op.drop_table('permission_cache')
    op.drop_table('custom_roles')
    op.drop_table('audit_logs')
    op.drop_table('organization_usage')
    op.drop_table('organization_invitations')
    op.drop_table('team_members')
    op.drop_table('organization_members')
    op.drop_table('teams')
    op.drop_table('organizations')
