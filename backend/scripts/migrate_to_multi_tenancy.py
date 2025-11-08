"""
Data Migration Script: Single-Tenant to Multi-Tenant
Migrates existing users and documents to multi-tenant organization structure

Run this AFTER applying the add_multi_tenancy migration
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from datetime import datetime
import uuid

from app.core.config import settings
from app.models.user import User
from app.models.document import Document
from app.models.organization import (
    Organization,
    OrganizationMember,
    OrganizationUsage,
    PlanTier,
    OrganizationStatus,
)
from app.services.audit_logger import AuditLogger


def create_default_organization(db: Session) -> Organization:
    """
    Create a default organization for migrating existing data
    """
    print("Creating default organization...")

    # Check if default org already exists
    existing = db.query(Organization).filter(Organization.slug == "default-org").first()

    if existing:
        print(f"Default organization already exists: {existing.name}")
        return existing

    # Create default organization
    org = Organization(
        name="Default Organization",
        slug="default-org",
        plan=PlanTier.PRO,  # Start with PRO plan for existing users
        status=OrganizationStatus.ACTIVE,
        settings={},
    )

    db.add(org)
    db.commit()
    db.refresh(org)

    print(f"Created default organization: {org.name} (ID: {org.id})")

    # Create usage record
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        period_end = period_start.replace(year=now.year + 1, month=1)
    else:
        period_end = period_start.replace(month=now.month + 1)

    usage = OrganizationUsage(
        organization_id=org.id,
        period_start=period_start,
        period_end=period_end,
        documents_created=0,
        api_calls=0,
        ai_queries=0,
        storage_used_bytes=0,
        total_cost=0,
        usage_details={},
    )

    db.add(usage)
    db.commit()

    return org


def migrate_users_to_organization(db: Session, organization: Organization):
    """
    Add all existing users as members of the default organization
    First user becomes org admin, others become members
    """
    print("\nMigrating users to organization...")

    users = db.query(User).all()
    print(f"Found {len(users)} users to migrate")

    first_user = True
    migrated = 0

    for user in users:
        # Check if already a member
        existing = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == organization.id,
                OrganizationMember.user_id == user.id,
            )
            .first()
        )

        if existing:
            print(f"  - User {user.username} already a member, skipping")
            continue

        # First user becomes admin, others become members
        role = "org_admin" if first_user else "member"

        member = OrganizationMember(
            organization_id=organization.id,
            user_id=user.id,
            role=role,
            is_active=True,
            joined_at=user.created_at if hasattr(user, "created_at") else datetime.utcnow(),
        )

        db.add(member)
        migrated += 1

        print(f"  - Added {user.username} as {role}")

        if first_user:
            # Update organization created_by
            organization.created_by = user.id
            first_user = False

    db.commit()
    print(f"Successfully migrated {migrated} users")


def migrate_documents_to_organization(db: Session, organization: Organization):
    """
    Associate all existing documents with the default organization
    """
    print("\nMigrating documents to organization...")

    # Count documents without organization
    documents = db.query(Document).filter(Document.organization_id.is_(None)).all()

    print(f"Found {len(documents)} documents to migrate")

    migrated = 0
    for doc in documents:
        doc.organization_id = organization.id
        migrated += 1

        if migrated % 100 == 0:
            print(f"  - Migrated {migrated} documents...")
            db.commit()

    db.commit()
    print(f"Successfully migrated {migrated} documents")

    # Update usage stats
    usage = (
        db.query(OrganizationUsage)
        .filter(OrganizationUsage.organization_id == organization.id)
        .first()
    )

    if usage:
        usage.documents_created = migrated
        db.commit()
        print(f"Updated organization usage: {migrated} documents")


def verify_migration(db: Session, organization: Organization):
    """
    Verify that the migration was successful
    """
    print("\nVerifying migration...")

    # Check organization
    org_count = db.query(Organization).count()
    print(f"✓ Organizations: {org_count}")

    # Check members
    member_count = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.organization_id == organization.id)
        .count()
    )
    print(f"✓ Organization members: {member_count}")

    # Check documents
    doc_count = db.query(Document).filter(Document.organization_id == organization.id).count()
    print(f"✓ Documents in organization: {doc_count}")

    # Check for unmigrated documents
    unmigrated_docs = db.query(Document).filter(Document.organization_id.is_(None)).count()

    if unmigrated_docs > 0:
        print(f"⚠ Warning: {unmigrated_docs} documents not yet migrated")
    else:
        print(f"✓ All documents migrated")

    # Check for users without organization
    user_count = db.query(User).count()
    if user_count != member_count:
        print(f"⚠ Warning: {user_count - member_count} users not in organization")
    else:
        print(f"✓ All users migrated")

    print("\nMigration verification complete!")


async def log_migration_event(db: Session, organization: Organization):
    """
    Log the migration event in audit logs
    """
    audit_logger = AuditLogger(db)

    await audit_logger.log_event(
        action="system_migration_complete",
        category="system",
        organization_id=organization.id,
        status="success",
        details={
            "migration_type": "single_tenant_to_multi_tenant",
            "organization_name": organization.name,
            "migration_date": datetime.utcnow().isoformat(),
        },
    )

    print("\n✓ Migration event logged to audit trail")


def main():
    """
    Main migration script
    """
    print("=" * 60)
    print("Data Migration: Single-Tenant to Multi-Tenant")
    print("=" * 60)
    print()

    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    db = Session(engine)

    try:
        # Step 1: Create default organization
        organization = create_default_organization(db)

        # Step 2: Migrate users
        migrate_users_to_organization(db, organization)

        # Step 3: Migrate documents
        migrate_documents_to_organization(db, organization)

        # Step 4: Verify migration
        verify_migration(db, organization)

        # Step 5: Log migration event
        asyncio.run(log_migration_event(db, organization))

        print()
        print("=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Review the default organization settings in the admin dashboard")
        print("2. Update organization plan if needed")
        print("3. Create additional organizations for different tenants")
        print("4. Invite new users to appropriate organizations")
        print()

    except Exception as e:
        print(f"\n✗ Migration failed: {str(e)}")
        db.rollback()
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    # Confirmation prompt
    print("\n⚠ WARNING: This script will modify your database.")
    print("Make sure you have backed up your database before proceeding.\n")

    response = input("Have you backed up your database? (yes/no): ")

    if response.lower() != "yes":
        print("Migration cancelled. Please backup your database first.")
        sys.exit(0)

    response = input("Proceed with migration? (yes/no): ")

    if response.lower() == "yes":
        main()
    else:
        print("Migration cancelled.")
        sys.exit(0)
