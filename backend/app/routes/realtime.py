"""
Real-time Communication Routes for PM Document Intelligence.

This module provides endpoints for PubNub real-time messaging:
- Webhook receivers for PubNub events
- Connection management
- Message history retrieval
- Presence tracking

Features:
- Webhook signature validation
- Presence event handling
- Message delivery confirmation
- Connection status monitoring
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, Request, Response, status
from pydantic import BaseModel, Field

from app.models import UserInDB
from app.services.pubnub_service import (
    get_pubnub_service,
    validate_webhook_signature,
    EventType,
    NotificationPriority,
)
from app.utils.auth_helpers import get_current_active_user
from app.utils.exceptions import ValidationError, AuthorizationError
from app.utils.logger import get_logger


logger = get_logger(__name__)

router = APIRouter(prefix="/api/realtime", tags=["realtime"])


# ============================================================================
# Request/Response Models
# ============================================================================

class WebhookEvent(BaseModel):
    """PubNub webhook event."""
    channel: str
    subscription: Optional[str] = None
    timetoken: str
    message: Dict[str, Any]
    publisher: Optional[str] = None


class PresenceEvent(BaseModel):
    """PubNub presence event."""
    action: str  # join, leave, timeout
    channel: str
    uuid: str
    timestamp: str
    occupancy: Optional[int] = None


class SendNotificationRequest(BaseModel):
    """Request to send notification via PubNub."""
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
    priority: NotificationPriority = NotificationPriority.MEDIUM
    action_url: Optional[str] = None
    action_label: Optional[str] = None


class PresenceResponse(BaseModel):
    """Response with presence information."""
    channel: str
    online: bool
    active_users: List[str]
    total_users: int


# ============================================================================
# Webhook Endpoints
# ============================================================================

@router.post("/webhook/message", summary="PubNub message webhook")
async def pubnub_message_webhook(
    request: Request,
    event: WebhookEvent,
    x_pubnub_signature: Optional[str] = Header(None)
):
    """
    Receive message delivery confirmations from PubNub.

    This webhook is called by PubNub when messages are delivered.

    **Security**: Validates webhook signature if secret key is configured.

    **Events Logged**:
    - Message delivery confirmation
    - Channel and timetoken
    - Publisher information
    """
    try:
        # Get request body for signature validation
        body = await request.body()

        # Validate signature if provided
        if x_pubnub_signature:
            from app.config import settings
            if not validate_webhook_signature(
                body=body,
                signature=x_pubnub_signature,
                secret_key=settings.pubnub.pubnub_secret_key
            ):
                logger.warning("Invalid webhook signature")
                raise AuthorizationError("Invalid webhook signature")

        logger.info(
            f"Message webhook received",
            extra={
                "channel": event.channel,
                "timetoken": event.timetoken,
                "publisher": event.publisher
            }
        )

        # Log the event
        # In production, you might want to store this in database
        # or send to monitoring system

        return {
            "status": "received",
            "channel": event.channel,
            "timetoken": event.timetoken
        }

    except Exception as e:
        logger.error(f"Webhook processing failed: {e}", exc_info=True)
        return Response(
            content=f"Error: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/webhook/presence", summary="PubNub presence webhook")
async def pubnub_presence_webhook(
    request: Request,
    event: PresenceEvent,
    x_pubnub_signature: Optional[str] = Header(None)
):
    """
    Receive presence events from PubNub.

    Handles user online/offline status changes.

    **Events**:
    - join: User comes online
    - leave: User goes offline
    - timeout: User connection times out

    **Use Cases**:
    - Track active users
    - Send queued messages to users coming online
    - Update user status in database
    """
    try:
        # Get request body for signature validation
        body = await request.body()

        # Validate signature if provided
        if x_pubnub_signature:
            from app.config import settings
            if not validate_webhook_signature(
                body=body,
                signature=x_pubnub_signature,
                secret_key=settings.pubnub.pubnub_secret_key
            ):
                logger.warning("Invalid webhook signature")
                raise AuthorizationError("Invalid webhook signature")

        logger.info(
            f"Presence event: {event.action}",
            extra={
                "channel": event.channel,
                "uuid": event.uuid,
                "occupancy": event.occupancy
            }
        )

        pubnub = get_pubnub_service()

        # Handle presence event
        if event.action == "join":
            pubnub.on_user_join(event.channel, event.uuid)
        elif event.action == "leave":
            pubnub.on_user_leave(event.channel, event.uuid)
        elif event.action == "timeout":
            pubnub.on_user_timeout(event.channel, event.uuid)

        return {
            "status": "processed",
            "action": event.action,
            "channel": event.channel,
            "uuid": event.uuid
        }

    except Exception as e:
        logger.error(f"Presence webhook failed: {e}", exc_info=True)
        return Response(
            content=f"Error: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# Client API Endpoints
# ============================================================================

@router.post("/notify", summary="Send notification to user")
async def send_notification(
    notification: SendNotificationRequest,
    current_user: UserInDB = Depends(get_current_active_user),
):
    """
    Send real-time notification to current user.

    **Use Cases**:
    - Test notification delivery
    - Manual notifications
    - Admin notifications

    **Rate Limit**: 30 requests/minute

    **Example**:
    ```json
    {
      "title": "Test Notification",
      "message": "This is a test message",
      "priority": "medium",
      "action_url": "/documents/123",
      "action_label": "View Document"
    }
    ```
    """
    try:
        pubnub = get_pubnub_service()

        success = await pubnub.publish_notification(
            user_id=current_user.id,
            title=notification.title,
            message=notification.message,
            priority=notification.priority,
            action_url=notification.action_url,
            action_label=notification.action_label
        )

        if not success:
            raise ValidationError("Failed to send notification")

        return {
            "success": True,
            "message": "Notification sent successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to send notification: {e}", exc_info=True)
        raise


@router.get("/presence/{channel}", summary="Get channel presence")
async def get_channel_presence(
    channel: str,
    current_user: UserInDB = Depends(get_current_active_user),
) -> PresenceResponse:
    """
    Get presence information for a channel.

    Returns list of active users on the channel.

    **Channels**:
    - User channels: `user-{user_id}`
    - Document channels: `doc-{document_id}`
    - Broadcast: `all-users`

    **Example**: GET `/api/realtime/presence/user-123`
    """
    pubnub = get_pubnub_service()

    # Check authorization
    if channel.startswith("user-"):
        user_id_from_channel = channel.replace("user-", "")
        if user_id_from_channel != current_user.id and current_user.role != "admin":
            raise AuthorizationError("Cannot access other user's presence")

    active_users = pubnub.get_active_users(channel)

    return PresenceResponse(
        channel=channel,
        online=len(active_users) > 0,
        active_users=list(active_users),
        total_users=len(active_users)
    )


@router.get("/status", summary="Get user connection status")
async def get_connection_status(
    current_user: UserInDB = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Get current user's connection status.

    Returns:
    - Online status
    - Active channels
    - Queued messages count

    **Example Response**:
    ```json
    {
      "online": true,
      "user_channel": "user-123",
      "queued_messages": 0,
      "timestamp": "2024-12-15T10:00:00Z"
    }
    ```
    """
    pubnub = get_pubnub_service()

    user_channel = pubnub.get_user_channel(current_user.id)
    is_online = pubnub.is_user_online(current_user.id)
    queued_count = pubnub.offline_queue.get_queue_size(current_user.id)

    return {
        "online": is_online,
        "user_channel": user_channel,
        "queued_messages": queued_count,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/history/{channel}", summary="Get message history")
async def get_message_history(
    channel: str,
    count: int = 100,
    current_user: UserInDB = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Get message history for a channel.

    **Access Control**:
    - Users can only access their own channel history
    - Admins can access any channel

    **Parameters**:
    - count: Number of messages to retrieve (max 100)

    **Example**: GET `/api/realtime/history/user-123?count=50`
    """
    # Check authorization
    if channel.startswith("user-"):
        user_id_from_channel = channel.replace("user-", "")
        if user_id_from_channel != current_user.id and current_user.role != "admin":
            raise AuthorizationError("Cannot access other user's message history")

    pubnub = get_pubnub_service()

    messages = pubnub.get_message_history(channel, count=min(count, 100))

    return {
        "channel": channel,
        "total_messages": len(messages),
        "messages": messages
    }


@router.delete("/queue", summary="Clear queued messages")
async def clear_message_queue(
    current_user: UserInDB = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Clear all queued messages for current user.

    This is useful when a user has been offline and has many queued messages
    that are no longer relevant.

    **Returns**: Number of messages cleared
    """
    pubnub = get_pubnub_service()

    cleared_count = pubnub.offline_queue.clear_messages(current_user.id)

    return {
        "success": True,
        "messages_cleared": cleared_count,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/channels", summary="Get user's channels")
async def get_user_channels(
    current_user: UserInDB = Depends(get_current_active_user),
) -> Dict[str, str]:
    """
    Get all channels relevant to the current user.

    **Returns**:
    - User-specific channel
    - Broadcast channel
    - Admin channel (if admin)

    **Example Response**:
    ```json
    {
      "user": "user-123",
      "broadcast": "all-users"
    }
    ```
    """
    pubnub = get_pubnub_service()

    channels = {
        "user": pubnub.get_user_channel(current_user.id),
        "broadcast": pubnub.get_broadcast_channel()
    }

    if current_user.role == "admin":
        channels["admin"] = pubnub.get_admin_channel()

    return channels


@router.get("/health", summary="PubNub health check")
async def pubnub_health_check() -> Dict[str, Any]:
    """
    Check PubNub service health.

    Returns:
    - Service status
    - Active connections
    - Queue statistics

    **Example Response**:
    ```json
    {
      "status": "healthy",
      "active_channels": 15,
      "total_queued_messages": 5,
      "timestamp": "2024-12-15T10:00:00Z"
    }
    ```
    """
    try:
        pubnub = get_pubnub_service()

        total_channels = len(pubnub.active_users)
        total_active_users = sum(
            len(users) for users in pubnub.active_users.values()
        )
        total_queued = sum(
            pubnub.offline_queue.get_queue_size(user_id)
            for user_id in pubnub.offline_queue.queues.keys()
        )

        return {
            "status": "healthy",
            "active_channels": total_channels,
            "total_active_users": total_active_users,
            "total_queued_messages": total_queued,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"PubNub health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
