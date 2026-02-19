"""
BAEL Webhook Engine
====================

Webhook management, delivery, verification, and retries.

"Ba'el's notifications reach every corner of the universe." — Ba'el
"""

import asyncio
import logging
import uuid
import hmac
import hashlib
import json
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import base64

logger = logging.getLogger("BAEL.Webhook")


# ============================================================================
# ENUMS
# ============================================================================

class WebhookStatus(Enum):
    """Webhook endpoint status."""
    ACTIVE = "active"
    DISABLED = "disabled"
    FAILING = "failing"
    SUSPENDED = "suspended"


class WebhookEvent(Enum):
    """Standard webhook events."""
    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"

    # Payment events
    PAYMENT_SUCCEEDED = "payment.succeeded"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_REFUNDED = "payment.refunded"

    # Subscription events
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_UPDATED = "subscription.updated"
    SUBSCRIPTION_CANCELLED = "subscription.cancelled"

    # Order events
    ORDER_CREATED = "order.created"
    ORDER_UPDATED = "order.updated"
    ORDER_COMPLETED = "order.completed"

    # Custom
    CUSTOM = "custom"


class DeliveryStatus(Enum):
    """Webhook delivery status."""
    PENDING = "pending"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class WebhookEndpoint:
    """A webhook endpoint."""
    id: str
    url: str

    # Events
    events: List[str] = field(default_factory=list)  # Empty = all events

    # Status
    status: WebhookStatus = WebhookStatus.ACTIVE

    # Security
    secret: str = field(default_factory=lambda: uuid.uuid4().hex)

    # Retry settings
    max_retries: int = 5

    # Stats
    deliveries_succeeded: int = 0
    deliveries_failed: int = 0
    consecutive_failures: int = 0

    # Metadata
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    last_delivery_at: Optional[datetime] = None


@dataclass
class WebhookPayload:
    """A webhook payload."""
    id: str
    event: str
    data: Dict[str, Any]

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'event': self.event,
            'data': self.data,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class WebhookDelivery:
    """A webhook delivery attempt."""
    id: str
    endpoint_id: str
    payload: WebhookPayload

    # Status
    status: DeliveryStatus = DeliveryStatus.PENDING

    # Response
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    response_time_ms: Optional[float] = None

    # Retry
    attempt: int = 1
    next_retry_at: Optional[datetime] = None

    # Error
    error: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    delivered_at: Optional[datetime] = None


@dataclass
class WebhookConfig:
    """Webhook engine configuration."""
    # Delivery
    timeout_seconds: float = 30.0
    max_retries: int = 5
    retry_delays: List[int] = field(default_factory=lambda: [60, 300, 900, 3600, 7200])

    # Processing
    max_concurrent: int = 10

    # Suspension
    suspend_after_failures: int = 10


# ============================================================================
# SIGNATURE VERIFICATION
# ============================================================================

class SignatureGenerator:
    """Generates webhook signatures."""

    @staticmethod
    def generate(
        payload: str,
        secret: str,
        timestamp: Optional[int] = None
    ) -> str:
        """
        Generate a signature for webhook payload.

        Format: t=timestamp,v1=signature
        """
        timestamp = timestamp or int(datetime.now().timestamp())

        # Create signed payload
        signed_payload = f"{timestamp}.{payload}"

        # Generate HMAC-SHA256
        signature = hmac.new(
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()

        return f"t={timestamp},v1={signature}"

    @staticmethod
    def verify(
        payload: str,
        signature: str,
        secret: str,
        tolerance_seconds: int = 300
    ) -> bool:
        """Verify a webhook signature."""
        try:
            # Parse signature
            parts = dict(p.split('=') for p in signature.split(','))
            timestamp = int(parts['t'])
            expected_sig = parts['v1']

            # Check timestamp tolerance
            now = int(datetime.now().timestamp())
            if abs(now - timestamp) > tolerance_seconds:
                return False

            # Regenerate signature
            signed_payload = f"{timestamp}.{payload}"
            computed_sig = hmac.new(
                secret.encode(),
                signed_payload.encode(),
                hashlib.sha256
            ).hexdigest()

            # Constant-time comparison
            return hmac.compare_digest(computed_sig, expected_sig)

        except Exception:
            return False


# ============================================================================
# MOCK HTTP CLIENT
# ============================================================================

class MockHTTPClient:
    """Mock HTTP client for testing."""

    def __init__(self):
        """Initialize client."""
        self.requests: List[Dict] = []
        self.should_fail: Set[str] = set()

    async def post(
        self,
        url: str,
        data: str,
        headers: Dict[str, str],
        timeout: float
    ) -> Dict[str, Any]:
        """Simulate POST request."""
        self.requests.append({
            'url': url,
            'data': data,
            'headers': headers
        })

        # Simulate network delay
        await asyncio.sleep(0.01)

        if url in self.should_fail:
            return {
                'status': 500,
                'body': 'Internal Server Error'
            }

        return {
            'status': 200,
            'body': '{"received": true}'
        }


# ============================================================================
# MAIN WEBHOOK ENGINE
# ============================================================================

class WebhookEngine:
    """
    Main webhook engine.

    Features:
    - Endpoint management
    - Payload delivery with retries
    - Signature generation/verification
    - Event filtering

    "Ba'el's messages are always delivered." — Ba'el
    """

    def __init__(self, config: Optional[WebhookConfig] = None):
        """Initialize webhook engine."""
        self.config = config or WebhookConfig()

        # Storage
        self._endpoints: Dict[str, WebhookEndpoint] = {}
        self._deliveries: Dict[str, WebhookDelivery] = {}
        self._pending: List[WebhookDelivery] = []

        # HTTP client
        self._http = MockHTTPClient()

        # Signature
        self._signer = SignatureGenerator()

        # Processing
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._semaphore: Optional[asyncio.Semaphore] = None

        # Stats
        self._stats = defaultdict(int)

        # Event handlers (for incoming webhooks)
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)

        self._lock = threading.RLock()

        logger.info("WebhookEngine initialized")

    # ========================================================================
    # ENDPOINT MANAGEMENT
    # ========================================================================

    def register_endpoint(
        self,
        url: str,
        events: Optional[List[str]] = None,
        **kwargs
    ) -> WebhookEndpoint:
        """
        Register a webhook endpoint.

        Args:
            url: Endpoint URL
            events: Events to subscribe to (None = all)

        Returns:
            WebhookEndpoint
        """
        endpoint = WebhookEndpoint(
            id=str(uuid.uuid4()),
            url=url,
            events=events or [],
            **kwargs
        )

        with self._lock:
            self._endpoints[endpoint.id] = endpoint

        logger.info(f"Registered webhook endpoint: {endpoint.id}")

        return endpoint

    def get_endpoint(self, endpoint_id: str) -> Optional[WebhookEndpoint]:
        """Get an endpoint by ID."""
        return self._endpoints.get(endpoint_id)

    def update_endpoint(
        self,
        endpoint_id: str,
        **kwargs
    ) -> Optional[WebhookEndpoint]:
        """Update an endpoint."""
        with self._lock:
            if endpoint_id in self._endpoints:
                endpoint = self._endpoints[endpoint_id]
                for key, value in kwargs.items():
                    if hasattr(endpoint, key):
                        setattr(endpoint, key, value)
                return endpoint
        return None

    def disable_endpoint(self, endpoint_id: str) -> bool:
        """Disable an endpoint."""
        with self._lock:
            if endpoint_id in self._endpoints:
                self._endpoints[endpoint_id].status = WebhookStatus.DISABLED
                return True
        return False

    def enable_endpoint(self, endpoint_id: str) -> bool:
        """Enable an endpoint."""
        with self._lock:
            if endpoint_id in self._endpoints:
                endpoint = self._endpoints[endpoint_id]
                endpoint.status = WebhookStatus.ACTIVE
                endpoint.consecutive_failures = 0
                return True
        return False

    def delete_endpoint(self, endpoint_id: str) -> bool:
        """Delete an endpoint."""
        with self._lock:
            if endpoint_id in self._endpoints:
                del self._endpoints[endpoint_id]
                return True
        return False

    def list_endpoints(self) -> List[WebhookEndpoint]:
        """List all endpoints."""
        return list(self._endpoints.values())

    # ========================================================================
    # SENDING WEBHOOKS
    # ========================================================================

    async def send(
        self,
        event: str,
        data: Dict[str, Any],
        endpoint_ids: Optional[List[str]] = None
    ) -> List[WebhookDelivery]:
        """
        Send a webhook event.

        Args:
            event: Event name
            data: Event data
            endpoint_ids: Specific endpoints (None = all matching)

        Returns:
            List of delivery objects
        """
        # Create payload
        payload = WebhookPayload(
            id=str(uuid.uuid4()),
            event=event,
            data=data
        )

        # Find matching endpoints
        endpoints = []

        with self._lock:
            for endpoint in self._endpoints.values():
                # Skip if specific endpoints requested
                if endpoint_ids and endpoint.id not in endpoint_ids:
                    continue

                # Skip disabled/suspended
                if endpoint.status not in [WebhookStatus.ACTIVE, WebhookStatus.FAILING]:
                    continue

                # Check event filter
                if endpoint.events and event not in endpoint.events:
                    continue

                endpoints.append(endpoint)

        # Create deliveries
        deliveries = []

        for endpoint in endpoints:
            delivery = WebhookDelivery(
                id=str(uuid.uuid4()),
                endpoint_id=endpoint.id,
                payload=payload
            )

            with self._lock:
                self._deliveries[delivery.id] = delivery

            deliveries.append(delivery)

            # Deliver immediately
            asyncio.create_task(self._deliver(delivery))

        self._stats['events_sent'] += 1

        return deliveries

    async def _deliver(self, delivery: WebhookDelivery) -> None:
        """Deliver a webhook."""
        endpoint = self._endpoints.get(delivery.endpoint_id)

        if not endpoint:
            delivery.status = DeliveryStatus.FAILED
            delivery.error = "Endpoint not found"
            return

        delivery.status = DeliveryStatus.SENDING

        start_time = datetime.now()

        try:
            # Prepare payload
            payload_json = json.dumps(delivery.payload.to_dict())

            # Generate signature
            signature = self._signer.generate(payload_json, endpoint.secret)

            # Send request
            response = await self._http.post(
                url=endpoint.url,
                data=payload_json,
                headers={
                    'Content-Type': 'application/json',
                    'X-Webhook-Signature': signature,
                    'X-Webhook-ID': delivery.id,
                    'X-Webhook-Event': delivery.payload.event
                },
                timeout=self.config.timeout_seconds
            )

            duration = (datetime.now() - start_time).total_seconds() * 1000

            delivery.response_status = response['status']
            delivery.response_body = response['body'][:1000]  # Limit size
            delivery.response_time_ms = duration

            if 200 <= response['status'] < 300:
                # Success
                delivery.status = DeliveryStatus.DELIVERED
                delivery.delivered_at = datetime.now()

                endpoint.deliveries_succeeded += 1
                endpoint.consecutive_failures = 0
                endpoint.last_delivery_at = datetime.now()

                if endpoint.status == WebhookStatus.FAILING:
                    endpoint.status = WebhookStatus.ACTIVE

                self._stats['deliveries_succeeded'] += 1

            else:
                # Failed
                await self._handle_failure(delivery, endpoint, f"HTTP {response['status']}")

        except Exception as e:
            await self._handle_failure(delivery, endpoint, str(e))

    async def _handle_failure(
        self,
        delivery: WebhookDelivery,
        endpoint: WebhookEndpoint,
        error: str
    ) -> None:
        """Handle delivery failure."""
        delivery.error = error

        endpoint.deliveries_failed += 1
        endpoint.consecutive_failures += 1

        # Check if should retry
        if delivery.attempt < endpoint.max_retries:
            delivery.status = DeliveryStatus.RETRYING
            delivery.attempt += 1

            # Calculate next retry
            delay_idx = min(delivery.attempt - 1, len(self.config.retry_delays) - 1)
            delay = self.config.retry_delays[delay_idx]
            delivery.next_retry_at = datetime.now() + timedelta(seconds=delay)

            # Queue for retry
            with self._lock:
                self._pending.append(delivery)

            self._stats['deliveries_retried'] += 1

        else:
            delivery.status = DeliveryStatus.FAILED
            self._stats['deliveries_failed'] += 1

        # Check if should suspend endpoint
        if endpoint.consecutive_failures >= self.config.suspend_after_failures:
            endpoint.status = WebhookStatus.SUSPENDED
            logger.warning(f"Suspended endpoint {endpoint.id} after {endpoint.consecutive_failures} failures")

        elif endpoint.consecutive_failures > 0:
            endpoint.status = WebhookStatus.FAILING

    # ========================================================================
    # RETRY PROCESSING
    # ========================================================================

    async def start_processing(self) -> None:
        """Start retry processing."""
        if self._running:
            return

        self._running = True
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        self._task = asyncio.create_task(self._process_loop())

        logger.info("Webhook processing started")

    async def stop_processing(self) -> None:
        """Stop retry processing."""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _process_loop(self) -> None:
        """Process pending retries."""
        while self._running:
            try:
                now = datetime.now()

                with self._lock:
                    ready = [
                        d for d in self._pending
                        if d.next_retry_at and d.next_retry_at <= now
                    ]

                    for d in ready:
                        self._pending.remove(d)

                for delivery in ready:
                    async with self._semaphore:
                        await self._deliver(delivery)

                await asyncio.sleep(1.0)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Processing error: {e}")

    # ========================================================================
    # RECEIVING WEBHOOKS
    # ========================================================================

    def on(self, event: str, handler: Callable) -> None:
        """Register a handler for incoming webhooks."""
        self._handlers[event].append(handler)

    async def receive(
        self,
        payload: str,
        signature: str,
        secret: str
    ) -> Dict[str, Any]:
        """
        Receive and process an incoming webhook.

        Args:
            payload: Raw JSON payload
            signature: Webhook signature
            secret: Endpoint secret

        Returns:
            Processing result
        """
        # Verify signature
        if not self._signer.verify(payload, signature, secret):
            return {'error': 'Invalid signature', 'status': 401}

        # Parse payload
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return {'error': 'Invalid JSON', 'status': 400}

        event = data.get('event')

        if not event:
            return {'error': 'Missing event', 'status': 400}

        # Call handlers
        handlers = self._handlers.get(event, []) + self._handlers.get('*', [])

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event, data.get('data', {}))
                else:
                    handler(event, data.get('data', {}))
            except Exception as e:
                logger.error(f"Handler error: {e}")

        self._stats['events_received'] += 1

        return {'status': 200, 'message': 'Received'}

    # ========================================================================
    # SIGNATURE UTILITIES
    # ========================================================================

    def generate_signature(
        self,
        payload: str,
        secret: str
    ) -> str:
        """Generate a signature for a payload."""
        return self._signer.generate(payload, secret)

    def verify_signature(
        self,
        payload: str,
        signature: str,
        secret: str
    ) -> bool:
        """Verify a signature."""
        return self._signer.verify(payload, signature, secret)

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_delivery(self, delivery_id: str) -> Optional[WebhookDelivery]:
        """Get a delivery by ID."""
        return self._deliveries.get(delivery_id)

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        with self._lock:
            endpoints_by_status = defaultdict(int)
            for e in self._endpoints.values():
                endpoints_by_status[e.status.value] += 1

        return {
            'endpoints': len(self._endpoints),
            'endpoints_by_status': dict(endpoints_by_status),
            'pending_retries': len(self._pending),
            'processing': self._running,
            'stats': dict(self._stats)
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

webhook_engine = WebhookEngine()
