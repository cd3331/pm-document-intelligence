"""
PubNub Real-time Service for PM Document Intelligence.

This module provides real-time updates and notifications using PubNub:
- Document processing progress updates
- User notifications
- System announcements
- Presence tracking
- Message persistence

Features:
- User-specific channels
- Document processing channels
- Broadcast channels
- Message deduplication
- Retry logic
- Offline message queueing
- Rate limiting

Usage:
    from app.services.pubnub_service import get_pubnub_service

    pubnub = get_pubnub_service()
    await pubnub.publish_progress(
        document_id="doc_123",
        user_id="user_123",
        percentage=50,
        step="Extracting text"
    )
"""

import asyncio
import hashlib
import json
import time
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from pubnub.callbacks import SubscribeCallback
from pubnub.enums import PNStatusCategory, PNReconnectionPolicy
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pydantic import BaseModel, Field

from app.config import settings
from app.utils.exceptions import ServiceError
from app.utils.logger import get_logger


logger = get_logger(__name__)


# ============================================================================
# Enums and Models
# ============================================================================


class EventType(str, Enum):
    """Event types for PubNub messages."""

    # Document processing events
    PROCESSING_STARTED = "processing_started"
    PROCESSING_PROGRESS = "processing_progress"
    PROCESSING_COMPLETED = "processing_completed"
    PROCESSING_FAILED = "processing_failed"
    PROCESSING_CANCELLED = "processing_cancelled"

    # Notification events
    NOTIFICATION = "notification"
    ACTION_ASSIGNED = "action_assigned"
    DOCUMENT_SHARED = "document_shared"
    MENTION = "mention"

    # System events
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    MAINTENANCE_SCHEDULED = "maintenance_scheduled"

    # Presence events
    USER_ONLINE = "user_online"
    USER_OFFLINE = "user_offline"


class NotificationPriority(str, Enum):
    """Priority levels for notifications."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PubNubMessage(BaseModel):
    """Standard PubNub message format."""

    event_type: EventType
    timestamp: str
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    data: Dict[str, Any]
    priority: NotificationPriority = NotificationPriority.MEDIUM
    dedupe_key: Optional[str] = None


class ProcessingProgress(BaseModel):
    """Progress update for document processing."""

    document_id: str
    percentage: int = Field(ge=0, le=100)
    current_step: str
    total_steps: int
    step_number: int
    estimated_time_remaining: Optional[int] = None  # seconds
    cancellable: bool = True


class NotificationMessage(BaseModel):
    """User notification message."""

    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.MEDIUM
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# Message Queue for Offline Users
# ============================================================================


class OfflineMessageQueue:
    """Queue messages for offline users."""

    def __init__(self, max_queue_size: int = 100):
        """
        Initialize offline message queue.

        Args:
            max_queue_size: Maximum messages to queue per user
        """
        self.queues: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.max_queue_size = max_queue_size

    def add_message(self, user_id: str, message: Dict[str, Any]) -> None:
        """
        Add message to user's offline queue.

        Args:
            user_id: User ID
            message: Message to queue
        """
        queue = self.queues[user_id]

        # Remove oldest messages if queue is full
        if len(queue) >= self.max_queue_size:
            queue.pop(0)

        queue.append(message)
        logger.info(f"Queued message for offline user {user_id}")

    def get_messages(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all queued messages for user.

        Args:
            user_id: User ID

        Returns:
            List of queued messages
        """
        messages = self.queues.get(user_id, [])
        return messages

    def clear_messages(self, user_id: str) -> int:
        """
        Clear all queued messages for user.

        Args:
            user_id: User ID

        Returns:
            Number of messages cleared
        """
        count = len(self.queues.get(user_id, []))
        self.queues[user_id] = []
        return count

    def get_queue_size(self, user_id: str) -> int:
        """Get queue size for user."""
        return len(self.queues.get(user_id, []))


# ============================================================================
# Rate Limiter
# ============================================================================


class RateLimiter:
    """Rate limit message publishing to prevent spam."""

    def __init__(self, max_messages: int = 60, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_messages: Maximum messages per window
            window_seconds: Time window in seconds
        """
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.message_times: Dict[str, List[float]] = defaultdict(list)

    def check_limit(self, key: str) -> bool:
        """
        Check if rate limit allows message.

        Args:
            key: Rate limit key (e.g., user_id or channel)

        Returns:
            True if message allowed, False if rate limited
        """
        now = time.time()
        cutoff = now - self.window_seconds

        # Remove old timestamps
        self.message_times[key] = [t for t in self.message_times[key] if t > cutoff]

        # Check if under limit
        if len(self.message_times[key]) >= self.max_messages:
            logger.warning(f"Rate limit exceeded for {key}")
            return False

        # Add current timestamp
        self.message_times[key].append(now)
        return True


# ============================================================================
# PubNub Callback Handler
# ============================================================================


class PubNubCallbackHandler(SubscribeCallback):
    """Handle PubNub callbacks for presence and messages."""

    def __init__(self, service: "PubNubService"):
        """Initialize callback handler."""
        self.service = service
        super().__init__()

    def status(self, pubnub, status):
        """Handle status events."""
        if status.category == PNStatusCategory.PNConnectedCategory:
            logger.info("PubNub connected successfully")
        elif status.category == PNStatusCategory.PNReconnectedCategory:
            logger.info("PubNub reconnected")
        elif status.category == PNStatusCategory.PNDisconnectedCategory:
            logger.warning("PubNub disconnected")
        elif status.category == PNStatusCategory.PNUnexpectedDisconnectCategory:
            logger.error("PubNub unexpected disconnect")

    def presence(self, pubnub, presence):
        """Handle presence events."""
        event = presence.event
        channel = presence.channel
        uuid = presence.uuid

        logger.info(f"Presence event: {event} on {channel} for {uuid}")

        if event == "join":
            self.service.on_user_join(channel, uuid)
        elif event == "leave":
            self.service.on_user_leave(channel, uuid)
        elif event == "timeout":
            self.service.on_user_timeout(channel, uuid)

    def message(self, pubnub, message):
        """Handle incoming messages."""
        logger.debug(f"Received message on {message.channel}: {message.message}")
        self.service.on_message_received(message.channel, message.message)


# ============================================================================
# PubNub Service
# ============================================================================


class PubNubService:
    """Service for real-time updates via PubNub."""

    def __init__(
        self,
        publish_key: str,
        subscribe_key: str,
        secret_key: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """
        Initialize PubNub service.

        Args:
            publish_key: PubNub publish key
            subscribe_key: PubNub subscribe key
            secret_key: PubNub secret key (for access manager)
            user_id: User ID for this client
        """
        # Configure PubNub
        pnconfig = PNConfiguration()
        pnconfig.publish_key = publish_key
        pnconfig.subscribe_key = subscribe_key
        pnconfig.secret_key = secret_key
        pnconfig.user_id = user_id or "server"
        pnconfig.reconnect_policy = PNReconnectionPolicy.LINEAR
        pnconfig.ssl = True

        # Initialize client
        self.pubnub = PubNub(pnconfig)
        self.callback_handler = PubNubCallbackHandler(self)
        self.pubnub.add_listener(self.callback_handler)

        # Initialize components
        self.offline_queue = OfflineMessageQueue()
        self.rate_limiter = RateLimiter(max_messages=60, window_seconds=60)
        self.message_cache: Set[str] = set()  # For deduplication
        self.active_users: Dict[str, Set[str]] = defaultdict(set)  # channel -> users

        logger.info("PubNub service initialized")

    # ========================================================================
    # Channel Management
    # ========================================================================

    def get_user_channel(self, user_id: str) -> str:
        """
        Get user-specific channel name.

        Args:
            user_id: User ID

        Returns:
            Channel name
        """
        return f"user-{user_id}"

    def get_document_channel(self, document_id: str) -> str:
        """
        Get document processing channel name.

        Args:
            document_id: Document ID

        Returns:
            Channel name
        """
        return f"doc-{document_id}"

    def get_broadcast_channel(self) -> str:
        """Get broadcast channel for all users."""
        return "all-users"

    def get_admin_channel(self) -> str:
        """Get admin notification channel."""
        return "admin-notifications"

    # ========================================================================
    # Publishing Methods
    # ========================================================================

    async def publish_update(
        self,
        channel: str,
        event_type: EventType,
        data: Dict[str, Any],
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        dedupe_key: Optional[str] = None,
    ) -> bool:
        """
        Publish an update to a channel.

        Args:
            channel: Channel to publish to
            event_type: Type of event
            data: Event data
            priority: Message priority
            dedupe_key: Optional key for deduplication

        Returns:
            True if published successfully
        """
        try:
            # Check rate limit
            if not self.rate_limiter.check_limit(channel):
                logger.warning(f"Rate limit exceeded for channel {channel}")
                return False

            # Create message
            message = PubNubMessage(
                event_type=event_type,
                timestamp=datetime.utcnow().isoformat(),
                data=data,
                priority=priority,
                dedupe_key=dedupe_key,
            )

            # Check for duplicate
            if dedupe_key and dedupe_key in self.message_cache:
                logger.info(f"Skipping duplicate message: {dedupe_key}")
                return True

            # Publish message
            result = await self._publish_with_retry(
                channel=channel, message=message.dict()
            )

            # Cache dedupe key
            if dedupe_key:
                self.message_cache.add(dedupe_key)
                # Clear old cache entries (keep last 1000)
                if len(self.message_cache) > 1000:
                    self.message_cache.clear()

            logger.info(
                f"Published {event_type.value} to {channel}",
                extra={"timetoken": result.timetoken if result else None},
            )

            return True

        except Exception as e:
            logger.error(f"Failed to publish update: {e}", exc_info=True)
            return False

    async def publish_progress(
        self,
        document_id: str,
        user_id: str,
        percentage: int,
        current_step: str,
        total_steps: int,
        step_number: int,
        estimated_time_remaining: Optional[int] = None,
        cancellable: bool = True,
    ) -> bool:
        """
        Publish processing progress update.

        Args:
            document_id: Document being processed
            user_id: User who owns the document
            percentage: Progress percentage (0-100)
            current_step: Description of current step
            total_steps: Total number of steps
            step_number: Current step number
            estimated_time_remaining: ETA in seconds
            cancellable: Whether operation can be cancelled

        Returns:
            True if published successfully
        """
        progress = ProcessingProgress(
            document_id=document_id,
            percentage=percentage,
            current_step=current_step,
            total_steps=total_steps,
            step_number=step_number,
            estimated_time_remaining=estimated_time_remaining,
            cancellable=cancellable,
        )

        # Publish to both user channel and document channel
        user_channel = self.get_user_channel(user_id)
        doc_channel = self.get_document_channel(document_id)

        # Create dedupe key
        dedupe_key = f"{document_id}:{step_number}"

        success = await self.publish_update(
            channel=user_channel,
            event_type=EventType.PROCESSING_PROGRESS,
            data=progress.dict(),
            priority=NotificationPriority.MEDIUM,
            dedupe_key=dedupe_key,
        )

        # Also publish to document channel (for shared access)
        await self.publish_update(
            channel=doc_channel,
            event_type=EventType.PROCESSING_PROGRESS,
            data=progress.dict(),
            priority=NotificationPriority.MEDIUM,
            dedupe_key=dedupe_key,
        )

        return success

    async def publish_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        action_url: Optional[str] = None,
        action_label: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Publish user notification.

        Args:
            user_id: User to notify
            title: Notification title
            message: Notification message
            priority: Notification priority
            action_url: Optional action URL
            action_label: Optional action button label
            metadata: Optional metadata

        Returns:
            True if published successfully
        """
        notification = NotificationMessage(
            title=title,
            message=message,
            priority=priority,
            action_url=action_url,
            action_label=action_label,
            metadata=metadata,
        )

        channel = self.get_user_channel(user_id)

        return await self.publish_update(
            channel=channel,
            event_type=EventType.NOTIFICATION,
            data=notification.dict(),
            priority=priority,
        )

    async def publish_processing_started(
        self, document_id: str, user_id: str, filename: str, total_steps: int
    ) -> bool:
        """
        Publish processing started event.

        Args:
            document_id: Document ID
            user_id: User ID
            filename: Document filename
            total_steps: Total processing steps

        Returns:
            True if published successfully
        """
        return await self.publish_update(
            channel=self.get_user_channel(user_id),
            event_type=EventType.PROCESSING_STARTED,
            data={
                "document_id": document_id,
                "filename": filename,
                "total_steps": total_steps,
                "started_at": datetime.utcnow().isoformat(),
            },
            priority=NotificationPriority.MEDIUM,
        )

    async def publish_processing_completed(
        self,
        document_id: str,
        user_id: str,
        filename: str,
        results_summary: Dict[str, Any],
    ) -> bool:
        """
        Publish processing completed event.

        Args:
            document_id: Document ID
            user_id: User ID
            filename: Document filename
            results_summary: Processing results summary

        Returns:
            True if published successfully
        """
        return await self.publish_update(
            channel=self.get_user_channel(user_id),
            event_type=EventType.PROCESSING_COMPLETED,
            data={
                "document_id": document_id,
                "filename": filename,
                "results_summary": results_summary,
                "completed_at": datetime.utcnow().isoformat(),
            },
            priority=NotificationPriority.HIGH,
        )

    async def publish_processing_failed(
        self,
        document_id: str,
        user_id: str,
        filename: str,
        error: str,
        step_failed: str,
    ) -> bool:
        """
        Publish processing failed event.

        Args:
            document_id: Document ID
            user_id: User ID
            filename: Document filename
            error: Error message
            step_failed: Step that failed

        Returns:
            True if published successfully
        """
        return await self.publish_update(
            channel=self.get_user_channel(user_id),
            event_type=EventType.PROCESSING_FAILED,
            data={
                "document_id": document_id,
                "filename": filename,
                "error": error,
                "step_failed": step_failed,
                "failed_at": datetime.utcnow().isoformat(),
            },
            priority=NotificationPriority.HIGH,
        )

    async def publish_action_assigned(
        self,
        user_id: str,
        action_item_id: str,
        title: str,
        due_date: Optional[str],
        priority: str,
    ) -> bool:
        """
        Publish action item assignment notification.

        Args:
            user_id: User assigned to
            action_item_id: Action item ID
            title: Action item title
            due_date: Due date
            priority: Priority level

        Returns:
            True if published successfully
        """
        return await self.publish_notification(
            user_id=user_id,
            title="New Action Item Assigned",
            message=f"You have been assigned: {title}",
            priority=(
                NotificationPriority.HIGH
                if priority == "HIGH"
                else NotificationPriority.MEDIUM
            ),
            action_url=f"/action-items/{action_item_id}",
            action_label="View Action Item",
            metadata={
                "action_item_id": action_item_id,
                "due_date": due_date,
                "priority": priority,
            },
        )

    async def publish_document_shared(
        self, user_id: str, document_id: str, filename: str, shared_by: str
    ) -> bool:
        """
        Publish document shared notification.

        Args:
            user_id: User document was shared with
            document_id: Document ID
            filename: Document filename
            shared_by: User who shared the document

        Returns:
            True if published successfully
        """
        return await self.publish_notification(
            user_id=user_id,
            title="Document Shared With You",
            message=f"{shared_by} shared '{filename}' with you",
            priority=NotificationPriority.MEDIUM,
            action_url=f"/documents/{document_id}",
            action_label="View Document",
            metadata={"document_id": document_id, "shared_by": shared_by},
        )

    async def publish_system_announcement(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
    ) -> bool:
        """
        Publish system-wide announcement.

        Args:
            title: Announcement title
            message: Announcement message
            priority: Priority level

        Returns:
            True if published successfully
        """
        return await self.publish_update(
            channel=self.get_broadcast_channel(),
            event_type=EventType.SYSTEM_ANNOUNCEMENT,
            data={
                "title": title,
                "message": message,
                "announced_at": datetime.utcnow().isoformat(),
            },
            priority=priority,
        )

    # ========================================================================
    # Internal Publishing with Retry
    # ========================================================================

    async def _publish_with_retry(
        self, channel: str, message: Dict[str, Any], max_retries: int = 3
    ) -> Any:
        """
        Publish message with retry logic.

        Args:
            channel: Channel to publish to
            message: Message to publish
            max_retries: Maximum retry attempts

        Returns:
            Publish result

        Raises:
            ServiceError: If publish fails after retries
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                # Publish message
                envelope = (
                    self.pubnub.publish()
                    .channel(channel)
                    .message(message)
                    .should_store(True)
                    .use_post(True)
                    .sync()
                )

                if envelope.status.is_error():
                    raise ServiceError(
                        message="PubNub publish failed",
                        details={"error": envelope.status.error_data},
                    )

                return envelope.result

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(
                        f"Publish failed (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Publish failed after {max_retries} attempts: {e}")

        raise ServiceError(
            message="Failed to publish message after retries",
            details={"error": str(last_error)},
        )

    # ========================================================================
    # Presence Management
    # ========================================================================

    def on_user_join(self, channel: str, user_id: str) -> None:
        """
        Handle user joining channel.

        Args:
            channel: Channel name
            user_id: User ID
        """
        self.active_users[channel].add(user_id)
        logger.info(f"User {user_id} joined {channel}")

        # Send queued messages if any
        if "user-" in channel:
            queued_count = self.offline_queue.get_queue_size(user_id)
            if queued_count > 0:
                logger.info(f"Sending {queued_count} queued messages to {user_id}")
                # Would send queued messages here

    def on_user_leave(self, channel: str, user_id: str) -> None:
        """
        Handle user leaving channel.

        Args:
            channel: Channel name
            user_id: User ID
        """
        self.active_users[channel].discard(user_id)
        logger.info(f"User {user_id} left {channel}")

    def on_user_timeout(self, channel: str, user_id: str) -> None:
        """
        Handle user timeout on channel.

        Args:
            channel: Channel name
            user_id: User ID
        """
        self.active_users[channel].discard(user_id)
        logger.warning(f"User {user_id} timed out on {channel}")

    def on_message_received(self, channel: str, message: Dict[str, Any]) -> None:
        """
        Handle incoming message.

        Args:
            channel: Channel name
            message: Message data
        """
        # Log message receipt
        logger.debug(f"Message received on {channel}: {message}")

    def is_user_online(self, user_id: str) -> bool:
        """
        Check if user is online.

        Args:
            user_id: User ID

        Returns:
            True if user is online
        """
        channel = self.get_user_channel(user_id)
        return user_id in self.active_users.get(channel, set())

    def get_active_users(self, channel: str) -> Set[str]:
        """
        Get active users on channel.

        Args:
            channel: Channel name

        Returns:
            Set of active user IDs
        """
        return self.active_users.get(channel, set())

    # ========================================================================
    # History and Cleanup
    # ========================================================================

    def get_message_history(
        self, channel: str, count: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get message history for channel.

        Args:
            channel: Channel name
            count: Number of messages to fetch

        Returns:
            List of messages
        """
        try:
            envelope = self.pubnub.history().channel(channel).count(count).sync()

            if envelope.status.is_error():
                logger.error(f"Failed to fetch history: {envelope.status.error_data}")
                return []

            return envelope.result.messages

        except Exception as e:
            logger.error(f"Error fetching history: {e}", exc_info=True)
            return []

    def cleanup(self) -> None:
        """Clean up PubNub resources."""
        try:
            self.pubnub.stop()
            logger.info("PubNub service stopped")
        except Exception as e:
            logger.error(f"Error stopping PubNub: {e}")


# ============================================================================
# Webhook Signature Validation
# ============================================================================


def validate_webhook_signature(body: bytes, signature: str, secret_key: str) -> bool:
    """
    Validate PubNub webhook signature.

    Args:
        body: Request body
        signature: Signature from header
        secret_key: PubNub secret key

    Returns:
        True if signature is valid
    """
    try:
        # Compute expected signature
        expected = hashlib.sha256(secret_key.encode() + body).hexdigest()

        return expected == signature

    except Exception as e:
        logger.error(f"Error validating webhook signature: {e}")
        return False


# ============================================================================
# Global Service Instance
# ============================================================================

_pubnub_service: Optional[PubNubService] = None


def get_pubnub_service() -> PubNubService:
    """
    Get global PubNub service instance.

    Returns:
        PubNubService instance
    """
    global _pubnub_service

    if _pubnub_service is None:
        # Initialize from settings
        _pubnub_service = PubNubService(
            publish_key=settings.pubnub.pubnub_publish_key,
            subscribe_key=settings.pubnub.pubnub_subscribe_key,
            secret_key=settings.pubnub.pubnub_secret_key,
            user_id="server",
        )

    return _pubnub_service


def initialize_pubnub() -> PubNubService:
    """
    Initialize PubNub service (called during app startup).

    Returns:
        Configured PubNub service
    """
    service = get_pubnub_service()
    logger.info("PubNub service initialized successfully")
    return service
