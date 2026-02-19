"""
BAEL Webhook Manager
=====================

Manage webhooks for external integrations.
Enables event-driven communication.

Features:
- Webhook registration
- Event routing
- Signature verification
- Retry handling
- Webhook monitoring
"""

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class WebhookStatus(Enum):
    """Webhook status."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    FAILED = "failed"


class EventType(Enum):
    """Event types for webhooks."""
    TASK_CREATED = "task.created"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    MESSAGE_RECEIVED = "message.received"
    ALERT_TRIGGERED = "alert.triggered"
    CUSTOM = "custom"


@dataclass
class WebhookEvent:
    """A webhook event."""
    id: str
    event_type: EventType

    # Payload
    data: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "bael"


@dataclass
class WebhookDelivery:
    """Webhook delivery record."""
    id: str
    webhook_id: str
    event_id: str

    # Delivery info
    status_code: int = 0
    response_body: str = ""

    # Timing
    delivered_at: Optional[datetime] = None
    duration_ms: float = 0.0

    # Retries
    attempt: int = 1
    success: bool = False


@dataclass
class Webhook:
    """A webhook endpoint."""
    id: str
    name: str
    url: str

    # Authentication
    secret: str = ""
    headers: Dict[str, str] = field(default_factory=dict)

    # Events
    events: List[EventType] = field(default_factory=list)

    # Status
    status: WebhookStatus = WebhookStatus.ACTIVE

    # Config
    retry_count: int = 3
    timeout_seconds: int = 30

    # Stats
    deliveries: int = 0
    failures: int = 0
    last_delivery: Optional[datetime] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class WebhookConfig:
    """Webhook manager configuration."""
    # Defaults
    default_retry_count: int = 3
    default_timeout: int = 30

    # Retry backoff
    retry_delay_seconds: int = 5
    max_retry_delay: int = 300

    # Security
    require_signature: bool = True
    signature_header: str = "X-BAEL-Signature"


class WebhookManager:
    """
    Webhook management for BAEL.

    Handles external integrations via webhooks.
    """

    def __init__(self, config: Optional[WebhookConfig] = None):
        self.config = config or WebhookConfig()

        # Registered webhooks
        self._webhooks: Dict[str, Webhook] = {}

        # Event handlers
        self._event_handlers: Dict[EventType, List[Callable]] = {}

        # Delivery history
        self._deliveries: List[WebhookDelivery] = []

        # Stats
        self.stats = {
            "events_processed": 0,
            "deliveries_success": 0,
            "deliveries_failed": 0,
        }

    def register(
        self,
        name: str,
        url: str,
        events: List[EventType],
        secret: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Webhook:
        """
        Register a webhook.

        Args:
            name: Webhook name
            url: Endpoint URL
            events: Events to subscribe to
            secret: Signing secret
            headers: Custom headers

        Returns:
            Registered webhook
        """
        webhook_id = hashlib.md5(
            f"{name}:{url}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        webhook = Webhook(
            id=webhook_id,
            name=name,
            url=url,
            secret=secret or secrets.token_hex(32),
            headers=headers or {},
            events=events,
            retry_count=self.config.default_retry_count,
            timeout_seconds=self.config.default_timeout,
        )

        self._webhooks[webhook_id] = webhook

        logger.info(f"Registered webhook: {name} ({webhook_id})")

        return webhook

    def unregister(self, webhook_id: str) -> bool:
        """Unregister a webhook."""
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]
            logger.info(f"Unregistered webhook: {webhook_id}")
            return True
        return False

    def get(self, webhook_id: str) -> Optional[Webhook]:
        """Get a webhook by ID."""
        return self._webhooks.get(webhook_id)

    def list(self) -> List[Webhook]:
        """List all webhooks."""
        return list(self._webhooks.values())

    async def emit(
        self,
        event_type: EventType,
        data: Dict[str, Any],
    ) -> List[WebhookDelivery]:
        """
        Emit an event to webhooks.

        Args:
            event_type: Type of event
            data: Event data

        Returns:
            List of delivery results
        """
        self.stats["events_processed"] += 1

        event_id = hashlib.md5(
            f"{event_type}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        event = WebhookEvent(
            id=event_id,
            event_type=event_type,
            data=data,
        )

        # Find matching webhooks
        matching = [
            w for w in self._webhooks.values()
            if w.status == WebhookStatus.ACTIVE and event_type in w.events
        ]

        # Deliver to all matching webhooks
        deliveries = []
        for webhook in matching:
            delivery = await self._deliver(webhook, event)
            deliveries.append(delivery)

        return deliveries

    async def _deliver(
        self,
        webhook: Webhook,
        event: WebhookEvent,
    ) -> WebhookDelivery:
        """Deliver event to webhook."""
        delivery_id = hashlib.md5(
            f"{webhook.id}:{event.id}".encode()
        ).hexdigest()[:12]

        delivery = WebhookDelivery(
            id=delivery_id,
            webhook_id=webhook.id,
            event_id=event.id,
        )

        # Build payload
        payload = {
            "event": event.event_type.value,
            "id": event.id,
            "timestamp": event.timestamp.isoformat(),
            "data": event.data,
        }

        # Sign payload
        signature = self._sign_payload(payload, webhook.secret)

        # Attempt delivery with retries
        for attempt in range(1, webhook.retry_count + 1):
            delivery.attempt = attempt

            try:
                # In production, would make actual HTTP request
                logger.info(
                    f"[WEBHOOK] Delivering to {webhook.url}: "
                    f"event={event.event_type.value}"
                )

                # Simulate successful delivery
                import time
                start = time.time()
                await asyncio.sleep(0.1)  # Simulate network

                delivery.status_code = 200
                delivery.response_body = '{"status": "received"}'
                delivery.duration_ms = (time.time() - start) * 1000
                delivery.delivered_at = datetime.now()
                delivery.success = True

                # Update webhook stats
                webhook.deliveries += 1
                webhook.last_delivery = delivery.delivered_at

                self.stats["deliveries_success"] += 1

                break

            except Exception as e:
                logger.error(f"Webhook delivery failed: {e}")

                if attempt < webhook.retry_count:
                    delay = min(
                        self.config.retry_delay_seconds * (2 ** (attempt - 1)),
                        self.config.max_retry_delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    delivery.success = False
                    webhook.failures += 1
                    self.stats["deliveries_failed"] += 1

        self._deliveries.append(delivery)

        return delivery

    def _sign_payload(
        self,
        payload: Dict[str, Any],
        secret: str,
    ) -> str:
        """Sign payload with HMAC."""
        payload_str = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            secret.encode(),
            payload_str.encode(),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def verify_signature(
        self,
        payload: Dict[str, Any],
        signature: str,
        secret: str,
    ) -> bool:
        """Verify webhook signature."""
        expected = self._sign_payload(payload, secret)
        return hmac.compare_digest(signature, expected)

    def pause(self, webhook_id: str) -> bool:
        """Pause a webhook."""
        if webhook_id in self._webhooks:
            self._webhooks[webhook_id].status = WebhookStatus.PAUSED
            return True
        return False

    def resume(self, webhook_id: str) -> bool:
        """Resume a webhook."""
        if webhook_id in self._webhooks:
            self._webhooks[webhook_id].status = WebhookStatus.ACTIVE
            return True
        return False

    def get_deliveries(
        self,
        webhook_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[WebhookDelivery]:
        """Get delivery history."""
        deliveries = self._deliveries

        if webhook_id:
            deliveries = [d for d in deliveries if d.webhook_id == webhook_id]

        return deliveries[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            **self.stats,
            "webhooks_count": len(self._webhooks),
            "active_webhooks": sum(
                1 for w in self._webhooks.values()
                if w.status == WebhookStatus.ACTIVE
            ),
        }


def demo():
    """Demonstrate webhook manager."""
    import asyncio

    print("=" * 60)
    print("BAEL Webhook Manager Demo")
    print("=" * 60)

    manager = WebhookManager()

    # Register webhooks
    webhook1 = manager.register(
        name="Task Notifications",
        url="https://example.com/webhooks/tasks",
        events=[EventType.TASK_CREATED, EventType.TASK_COMPLETED],
    )

    webhook2 = manager.register(
        name="Alert Handler",
        url="https://example.com/webhooks/alerts",
        events=[EventType.ALERT_TRIGGERED],
    )

    print(f"\nRegistered Webhooks:")
    for webhook in manager.list():
        print(f"  - {webhook.name} ({webhook.id})")
        print(f"    URL: {webhook.url}")
        print(f"    Events: {[e.value for e in webhook.events]}")

    # Emit events
    async def emit_events():
        # Task created event
        deliveries = await manager.emit(
            EventType.TASK_CREATED,
            {"task_id": "task_123", "title": "Test Task"},
        )

        print(f"\nTask Created - Deliveries: {len(deliveries)}")
        for d in deliveries:
            print(f"  - {d.webhook_id}: {d.status_code} ({d.duration_ms:.1f}ms)")

        # Alert event
        deliveries = await manager.emit(
            EventType.ALERT_TRIGGERED,
            {"alert_id": "alert_456", "severity": "high"},
        )

        print(f"\nAlert Triggered - Deliveries: {len(deliveries)}")
        for d in deliveries:
            print(f"  - {d.webhook_id}: {d.status_code}")

    asyncio.run(emit_events())

    # Verify signature
    payload = {"test": "data"}
    signature = manager._sign_payload(payload, webhook1.secret)
    valid = manager.verify_signature(payload, signature, webhook1.secret)
    print(f"\nSignature verification: {'✓ Valid' if valid else '✗ Invalid'}")

    print(f"\nStats: {manager.get_stats()}")


if __name__ == "__main__":
    demo()
