"""
Invitation Service
Manages user invitations to organizations
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
import uuid
import secrets
import hashlib

from app.models.organization import (
    Organization,
    OrganizationMember,
    OrganizationInvitation,
    Team,
    TeamMember,
)
from app.models.user import User
from app.models.roles import Role
from app.services.audit_logger import AuditLogger


class InvitationService:
    """
    Service for managing organization invitations
    """

    def __init__(self, db: Session):
        self.db = db

    # ============================================================================
    # Invitation Creation
    # ============================================================================

    def generate_invitation_token(self) -> str:
        """
        Generate a secure invitation token

        Returns:
            Secure random token
        """
        # Generate 32-byte random token
        random_bytes = secrets.token_bytes(32)
        # Create hash for additional security
        token = hashlib.sha256(random_bytes).hexdigest()
        return token

    async def create_invitation(
        self,
        organization_id: uuid.UUID,
        email: str,
        role: str,
        invited_by: uuid.UUID,
        team_ids: Optional[List[uuid.UUID]] = None,
        expires_in_days: int = 7,
    ) -> OrganizationInvitation:
        """
        Create a new organization invitation

        Args:
            organization_id: Organization to invite to
            email: Email address to invite
            role: Role to assign (must be valid Role enum value)
            invited_by: User ID creating the invitation
            team_ids: List of team IDs to add user to
            expires_in_days: Number of days until invitation expires

        Returns:
            OrganizationInvitation: Created invitation

        Raises:
            ValueError: If role is invalid
        """
        # Validate role
        try:
            Role(role)
        except ValueError:
            raise ValueError(f"Invalid role: {role}")

        # Check if pending invitation already exists
        existing = (
            self.db.query(OrganizationInvitation)
            .filter(
                OrganizationInvitation.organization_id == organization_id,
                OrganizationInvitation.email == email,
                OrganizationInvitation.status == "pending",
            )
            .first()
        )

        if existing:
            # Cancel existing invitation
            existing.status = "cancelled"
            self.db.commit()

        # Generate token
        token = self.generate_invitation_token()

        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Create invitation
        invitation = OrganizationInvitation(
            organization_id=organization_id,
            email=email.lower(),
            role=role,
            token=token,
            status="pending",
            teams=team_ids or [],
            expires_at=expires_at,
            invited_by=invited_by,
        )

        self.db.add(invitation)
        self.db.commit()
        self.db.refresh(invitation)

        return invitation

    # ============================================================================
    # Email Sending
    # ============================================================================

    async def send_invitation_email(
        self, invitation_id: uuid.UUID, organization_name: str
    ):
        """
        Send invitation email to user

        Args:
            invitation_id: Invitation UUID
            organization_name: Name of organization

        In production, this would integrate with email service (SendGrid, SES, etc.)
        For now, logs the invitation details
        """
        invitation = (
            self.db.query(OrganizationInvitation)
            .filter(OrganizationInvitation.id == invitation_id)
            .first()
        )

        if not invitation:
            raise ValueError("Invitation not found")

        # Get inviter details
        inviter = self.db.query(User).filter(User.id == invitation.invited_by).first()

        # Build invitation URL
        # In production, this would be the actual frontend URL
        base_url = "https://your-app.com"  # TODO: Get from config
        invitation_url = f"{base_url}/accept-invitation?token={invitation.token}"

        # Email content
        email_subject = f"Invitation to join {organization_name}"
        email_body = f"""
Hello,

{inviter.username if inviter else 'Someone'} has invited you to join {organization_name} on PM Document Intelligence.

Role: {invitation.role}

Click the link below to accept this invitation:
{invitation_url}

This invitation will expire on {invitation.expires_at.strftime('%B %d, %Y at %I:%M %p UTC')}.

If you don't have an account yet, you'll be able to create one when you accept the invitation.

Best regards,
PM Document Intelligence Team
"""

        # TODO: Integrate with actual email service
        # Example with SendGrid:
        # from sendgrid import SendGridAPIClient
        # from sendgrid.helpers.mail import Mail
        #
        # message = Mail(
        #     from_email='noreply@your-app.com',
        #     to_emails=invitation.email,
        #     subject=email_subject,
        #     plain_text_content=email_body
        # )
        # sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        # response = sg.send(message)

        # For now, just log
        print(f"=== EMAIL INVITATION ===")
        print(f"To: {invitation.email}")
        print(f"Subject: {email_subject}")
        print(f"Body:\n{email_body}")
        print(f"=======================")

        # Mark invitation as sent (add sent_at field if needed)
        # invitation.sent_at = datetime.utcnow()
        # self.db.commit()

    # ============================================================================
    # Invitation Validation and Acceptance
    # ============================================================================

    async def validate_invitation_token(
        self, token: str
    ) -> Optional[OrganizationInvitation]:
        """
        Validate an invitation token

        Args:
            token: Invitation token

        Returns:
            OrganizationInvitation if valid, None otherwise
        """
        invitation = (
            self.db.query(OrganizationInvitation)
            .filter(OrganizationInvitation.token == token)
            .first()
        )

        if not invitation:
            return None

        # Check if valid
        if not invitation.is_valid:
            return None

        return invitation

    async def accept_invitation(
        self, token: str, user_id: uuid.UUID
    ) -> OrganizationMember:
        """
        Accept an invitation and add user to organization

        Args:
            token: Invitation token
            user_id: User accepting the invitation

        Returns:
            OrganizationMember: Created membership

        Raises:
            ValueError: If invitation invalid or user already member
        """
        # Validate token
        invitation = await self.validate_invitation_token(token)

        if not invitation:
            raise ValueError("Invalid or expired invitation")

        # Check if user email matches invitation
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        if user.email.lower() != invitation.email.lower():
            raise ValueError(
                "Email mismatch: invitation is for a different email address"
            )

        # Check if user is already a member
        existing_member = (
            self.db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == invitation.organization_id,
                OrganizationMember.user_id == user_id,
            )
            .first()
        )

        if existing_member:
            if existing_member.is_active:
                raise ValueError("User is already a member of this organization")
            else:
                # Reactivate membership
                existing_member.is_active = True
                existing_member.role = invitation.role
                existing_member.joined_at = datetime.utcnow()

                # Mark invitation as accepted
                invitation.status = "accepted"
                invitation.accepted_at = datetime.utcnow()
                invitation.accepted_by = user_id

                self.db.commit()

                # Add to teams if specified
                if invitation.teams:
                    await self._add_user_to_teams(user_id, invitation.teams)

                return existing_member

        # Create new membership
        member = OrganizationMember(
            organization_id=invitation.organization_id,
            user_id=user_id,
            role=invitation.role,
            is_active=True,
            joined_at=datetime.utcnow(),
            invited_by=invitation.invited_by,
        )

        self.db.add(member)

        # Mark invitation as accepted
        invitation.status = "accepted"
        invitation.accepted_at = datetime.utcnow()
        invitation.accepted_by = user_id

        self.db.commit()
        self.db.refresh(member)

        # Add to teams if specified
        if invitation.teams:
            await self._add_user_to_teams(user_id, invitation.teams)

        # Log audit event
        audit_logger = AuditLogger(self.db)
        await audit_logger.log_event(
            user_id=user_id,
            organization_id=invitation.organization_id,
            action="invitation_accepted",
            resource_type="invitation",
            resource_id=invitation.id,
            status="success",
            details={
                "email": invitation.email,
                "role": invitation.role,
                "invited_by": str(invitation.invited_by),
            },
        )

        return member

    async def _add_user_to_teams(self, user_id: uuid.UUID, team_ids: List[uuid.UUID]):
        """
        Add user to specified teams

        Args:
            user_id: User UUID
            team_ids: List of team UUIDs (stored as strings in JSONB)
        """
        for team_id_str in team_ids:
            try:
                # Convert string UUID to UUID object
                if isinstance(team_id_str, str):
                    team_id = uuid.UUID(team_id_str)
                else:
                    team_id = team_id_str

                # Check if team exists
                team = self.db.query(Team).filter(Team.id == team_id).first()
                if not team:
                    continue

                # Check if already a member
                existing = (
                    self.db.query(TeamMember)
                    .filter(
                        TeamMember.team_id == team_id, TeamMember.user_id == user_id
                    )
                    .first()
                )

                if existing:
                    continue

                # Add team member
                team_member = TeamMember(
                    team_id=team_id, user_id=user_id, joined_at=datetime.utcnow()
                )

                self.db.add(team_member)

            except (ValueError, TypeError):
                # Invalid team ID, skip
                continue

        self.db.commit()

    # ============================================================================
    # Invitation Management
    # ============================================================================

    async def cancel_invitation(
        self, invitation_id: uuid.UUID, cancelled_by: uuid.UUID
    ):
        """
        Cancel a pending invitation

        Args:
            invitation_id: Invitation UUID
            cancelled_by: User cancelling the invitation

        Raises:
            ValueError: If invitation not found or not pending
        """
        invitation = (
            self.db.query(OrganizationInvitation)
            .filter(OrganizationInvitation.id == invitation_id)
            .first()
        )

        if not invitation:
            raise ValueError("Invitation not found")

        if invitation.status != "pending":
            raise ValueError(
                f"Cannot cancel invitation with status '{invitation.status}'"
            )

        invitation.status = "cancelled"

        # Log audit event
        audit_logger = AuditLogger(self.db)
        await audit_logger.log_event(
            user_id=cancelled_by,
            organization_id=invitation.organization_id,
            action="invitation_cancelled",
            resource_type="invitation",
            resource_id=invitation.id,
            status="success",
            details={"email": invitation.email, "role": invitation.role},
        )

        self.db.commit()

    async def resend_invitation(self, invitation_id: uuid.UUID, organization_name: str):
        """
        Resend invitation email

        Args:
            invitation_id: Invitation UUID
            organization_name: Organization name

        Raises:
            ValueError: If invitation not valid
        """
        invitation = (
            self.db.query(OrganizationInvitation)
            .filter(OrganizationInvitation.id == invitation_id)
            .first()
        )

        if not invitation:
            raise ValueError("Invitation not found")

        if invitation.status != "pending":
            raise ValueError(
                f"Cannot resend invitation with status '{invitation.status}'"
            )

        # Extend expiration if close to expiring
        time_until_expiry = invitation.expires_at - datetime.utcnow()
        if time_until_expiry.days < 2:
            invitation.expires_at = datetime.utcnow() + timedelta(days=7)
            self.db.commit()

        # Resend email
        await self.send_invitation_email(invitation_id, organization_name)

    async def expire_old_invitations(self):
        """
        Mark expired invitations as expired
        Should be run as a scheduled job
        """
        expired_invitations = (
            self.db.query(OrganizationInvitation)
            .filter(
                OrganizationInvitation.status == "pending",
                OrganizationInvitation.expires_at < datetime.utcnow(),
            )
            .all()
        )

        for invitation in expired_invitations:
            invitation.status = "expired"

        self.db.commit()

        return len(expired_invitations)

    # ============================================================================
    # Invitation Queries
    # ============================================================================

    async def get_user_invitations(self, email: str) -> List[OrganizationInvitation]:
        """
        Get all pending invitations for an email address

        Args:
            email: Email address

        Returns:
            List of pending invitations
        """
        invitations = (
            self.db.query(OrganizationInvitation)
            .filter(
                OrganizationInvitation.email == email.lower(),
                OrganizationInvitation.status == "pending",
            )
            .all()
        )

        # Filter to only valid (not expired)
        valid_invitations = [inv for inv in invitations if inv.is_valid]

        return valid_invitations

    async def get_organization_invitations(
        self, organization_id: uuid.UUID, status: Optional[str] = None
    ) -> List[OrganizationInvitation]:
        """
        Get invitations for an organization

        Args:
            organization_id: Organization UUID
            status: Optional status filter

        Returns:
            List of invitations
        """
        query = self.db.query(OrganizationInvitation).filter(
            OrganizationInvitation.organization_id == organization_id
        )

        if status:
            query = query.filter(OrganizationInvitation.status == status)

        invitations = query.order_by(OrganizationInvitation.created_at.desc()).all()

        return invitations

    async def get_invitation_stats(self, organization_id: uuid.UUID) -> dict:
        """
        Get invitation statistics for an organization

        Returns:
            dict with stats:
            {
                "total": 50,
                "pending": 10,
                "accepted": 35,
                "expired": 3,
                "cancelled": 2,
                "acceptance_rate": 70.0
            }
        """
        invitations = await self.get_organization_invitations(organization_id)

        stats = {
            "total": len(invitations),
            "pending": sum(1 for inv in invitations if inv.status == "pending"),
            "accepted": sum(1 for inv in invitations if inv.status == "accepted"),
            "expired": sum(1 for inv in invitations if inv.status == "expired"),
            "cancelled": sum(1 for inv in invitations if inv.status == "cancelled"),
        }

        # Calculate acceptance rate
        total_sent = stats["accepted"] + stats["expired"] + stats["cancelled"]
        if total_sent > 0:
            stats["acceptance_rate"] = round((stats["accepted"] / total_sent) * 100, 1)
        else:
            stats["acceptance_rate"] = 0.0

        return stats

    # ============================================================================
    # Bulk Operations
    # ============================================================================

    async def bulk_invite(
        self,
        organization_id: uuid.UUID,
        email_list: List[str],
        role: str,
        invited_by: uuid.UUID,
        team_ids: Optional[List[uuid.UUID]] = None,
    ) -> dict:
        """
        Invite multiple users at once

        Args:
            organization_id: Organization UUID
            email_list: List of email addresses
            role: Role to assign
            invited_by: User creating invitations
            team_ids: Teams to add users to

        Returns:
            dict with results:
            {
                "success": 8,
                "failed": 2,
                "details": [...]
            }
        """
        results = {"success": 0, "failed": 0, "details": []}

        organization = (
            self.db.query(Organization)
            .filter(Organization.id == organization_id)
            .first()
        )

        for email in email_list:
            try:
                invitation = await self.create_invitation(
                    organization_id=organization_id,
                    email=email,
                    role=role,
                    invited_by=invited_by,
                    team_ids=team_ids,
                )

                # Send email
                await self.send_invitation_email(invitation.id, organization.name)

                results["success"] += 1
                results["details"].append(
                    {
                        "email": email,
                        "status": "success",
                        "invitation_id": str(invitation.id),
                    }
                )

            except Exception as e:
                results["failed"] += 1
                results["details"].append(
                    {"email": email, "status": "failed", "error": str(e)}
                )

        return results
