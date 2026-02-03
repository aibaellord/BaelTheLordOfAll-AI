#!/usr/bin/env python3
"""
BAEL - Email Service System
Comprehensive email handling and management.

Features:
- Email composition
- SMTP-like sending
- Email templates
- Attachments
- HTML emails
- Batch sending
- Email queue
- Delivery tracking
- Bounce handling
- Email validation
"""

import asyncio
import base64
import hashlib
import json
import logging
import mimetypes
import os
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum, auto
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class EmailPriority(Enum):
    """Email priority levels."""
    LOW = 1
    NORMAL = 3
    HIGH = 5
    URGENT = 7


class EmailStatus(Enum):
    """Email delivery status."""
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    FAILED = "failed"
    DEFERRED = "deferred"


class BounceType(Enum):
    """Email bounce types."""
    SOFT = "soft"
    HARD = "hard"
    SPAM = "spam"
    INVALID = "invalid"


class ContentType(Enum):
    """Email content types."""
    PLAIN = "text/plain"
    HTML = "text/html"
    MULTIPART = "multipart/mixed"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class EmailAddress:
    """Email address with validation."""
    address: str
    name: Optional[str] = None

    EMAIL_REGEX = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    def __post_init__(self):
        self.address = self.address.strip().lower()

    @property
    def is_valid(self) -> bool:
        """Check if email is valid."""
        return bool(self.EMAIL_REGEX.match(self.address))

    @property
    def domain(self) -> str:
        """Get email domain."""
        return self.address.split("@")[1] if "@" in self.address else ""

    @property
    def local_part(self) -> str:
        """Get local part (before @)."""
        return self.address.split("@")[0] if "@" in self.address else self.address

    def formatted(self) -> str:
        """Get formatted address."""
        if self.name:
            return f'"{self.name}" <{self.address}>'

        return self.address

    def __str__(self) -> str:
        return self.formatted()


@dataclass
class Attachment:
    """Email attachment."""
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"
    content_id: Optional[str] = None
    inline: bool = False

    @classmethod
    def from_file(cls, filepath: str) -> 'Attachment':
        """Create attachment from file."""
        filename = os.path.basename(filepath)
        content_type, _ = mimetypes.guess_type(filepath)

        with open(filepath, 'rb') as f:
            content = f.read()

        return cls(
            filename=filename,
            content=content,
            content_type=content_type or "application/octet-stream"
        )

    @classmethod
    def from_text(cls, filename: str, text: str) -> 'Attachment':
        """Create text attachment."""
        return cls(
            filename=filename,
            content=text.encode('utf-8'),
            content_type='text/plain'
        )

    @property
    def size(self) -> int:
        """Get attachment size."""
        return len(self.content)

    @property
    def base64_content(self) -> str:
        """Get base64 encoded content."""
        return base64.b64encode(self.content).decode()


@dataclass
class EmailMessage:
    """Email message."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_address: Optional[EmailAddress] = None
    to_addresses: List[EmailAddress] = field(default_factory=list)
    cc_addresses: List[EmailAddress] = field(default_factory=list)
    bcc_addresses: List[EmailAddress] = field(default_factory=list)
    reply_to: Optional[EmailAddress] = None
    subject: str = ""
    text_body: str = ""
    html_body: str = ""
    attachments: List[Attachment] = field(default_factory=list)
    priority: EmailPriority = EmailPriority.NORMAL
    headers: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    send_at: Optional[datetime] = None

    def add_to(self, address: str, name: str = None) -> 'EmailMessage':
        """Add TO recipient."""
        self.to_addresses.append(EmailAddress(address, name))
        return self

    def add_cc(self, address: str, name: str = None) -> 'EmailMessage':
        """Add CC recipient."""
        self.cc_addresses.append(EmailAddress(address, name))
        return self

    def add_bcc(self, address: str, name: str = None) -> 'EmailMessage':
        """Add BCC recipient."""
        self.bcc_addresses.append(EmailAddress(address, name))
        return self

    def set_from(self, address: str, name: str = None) -> 'EmailMessage':
        """Set FROM address."""
        self.from_address = EmailAddress(address, name)
        return self

    def set_subject(self, subject: str) -> 'EmailMessage':
        """Set subject."""
        self.subject = subject
        return self

    def set_body(self, text: str = None, html: str = None) -> 'EmailMessage':
        """Set body."""
        if text:
            self.text_body = text

        if html:
            self.html_body = html

        return self

    def add_attachment(self, attachment: Attachment) -> 'EmailMessage':
        """Add attachment."""
        self.attachments.append(attachment)
        return self

    def set_priority(self, priority: EmailPriority) -> 'EmailMessage':
        """Set priority."""
        self.priority = priority
        return self

    def add_header(self, name: str, value: str) -> 'EmailMessage':
        """Add custom header."""
        self.headers[name] = value
        return self

    def schedule(self, send_at: datetime) -> 'EmailMessage':
        """Schedule email."""
        self.send_at = send_at
        return self

    @property
    def all_recipients(self) -> List[EmailAddress]:
        """Get all recipients."""
        return self.to_addresses + self.cc_addresses + self.bcc_addresses

    @property
    def is_valid(self) -> bool:
        """Check if email is valid for sending."""
        if not self.from_address or not self.from_address.is_valid:
            return False

        if not self.to_addresses:
            return False

        for addr in self.all_recipients:
            if not addr.is_valid:
                return False

        if not self.subject and not self.text_body and not self.html_body:
            return False

        return True

    def to_mime(self) -> MIMEMultipart:
        """Convert to MIME message."""
        if self.attachments or (self.text_body and self.html_body):
            msg = MIMEMultipart('mixed')
        else:
            msg = MIMEMultipart()

        # Headers
        msg['From'] = self.from_address.formatted() if self.from_address else ""
        msg['To'] = ", ".join(a.formatted() for a in self.to_addresses)
        msg['Subject'] = self.subject
        msg['Date'] = self.created_at.strftime("%a, %d %b %Y %H:%M:%S +0000")
        msg['Message-ID'] = f"<{self.id}@bael.local>"

        if self.cc_addresses:
            msg['Cc'] = ", ".join(a.formatted() for a in self.cc_addresses)

        if self.reply_to:
            msg['Reply-To'] = self.reply_to.formatted()

        # Custom headers
        for name, value in self.headers.items():
            msg[name] = value

        # Priority
        if self.priority != EmailPriority.NORMAL:
            msg['X-Priority'] = str(self.priority.value)

        # Body
        if self.text_body and self.html_body:
            alt = MIMEMultipart('alternative')
            alt.attach(MIMEText(self.text_body, 'plain'))
            alt.attach(MIMEText(self.html_body, 'html'))
            msg.attach(alt)

        elif self.html_body:
            msg.attach(MIMEText(self.html_body, 'html'))

        else:
            msg.attach(MIMEText(self.text_body, 'plain'))

        # Attachments
        for attachment in self.attachments:
            part = MIMEBase(*attachment.content_type.split('/'))
            part.set_payload(attachment.content)
            part.add_header(
                'Content-Disposition',
                'inline' if attachment.inline else 'attachment',
                filename=attachment.filename
            )

            if attachment.content_id:
                part.add_header('Content-ID', f'<{attachment.content_id}>')

            msg.attach(part)

        return msg


@dataclass
class DeliveryResult:
    """Email delivery result."""
    message_id: str
    status: EmailStatus
    recipient: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
    smtp_code: Optional[int] = None
    bounce_type: Optional[BounceType] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmailTemplate:
    """Email template."""
    id: str
    name: str
    subject_template: str
    text_template: str = ""
    html_template: str = ""
    variables: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def render(self, context: Dict[str, Any]) -> EmailMessage:
        """Render template to email message."""
        msg = EmailMessage()

        # Render subject
        msg.subject = self._render_string(self.subject_template, context)

        # Render body
        if self.text_template:
            msg.text_body = self._render_string(self.text_template, context)

        if self.html_template:
            msg.html_body = self._render_string(self.html_template, context)

        return msg

    def _render_string(self, template: str, context: Dict[str, Any]) -> str:
        """Simple template rendering."""
        result = template

        for key, value in context.items():
            result = result.replace(f"{{{{ {key} }}}}", str(value))
            result = result.replace(f"{{{{{key}}}}}", str(value))

        return result


# =============================================================================
# EMAIL TRANSPORT
# =============================================================================

class EmailTransport(ABC):
    """Abstract email transport."""

    @abstractmethod
    async def send(self, message: EmailMessage) -> List[DeliveryResult]:
        """Send email message."""
        pass

    @abstractmethod
    async def verify(self) -> bool:
        """Verify transport connection."""
        pass


class MemoryTransport(EmailTransport):
    """In-memory email transport for testing."""

    def __init__(self):
        self.sent_messages: List[EmailMessage] = []
        self.delivery_results: List[DeliveryResult] = []

    async def send(self, message: EmailMessage) -> List[DeliveryResult]:
        """Send email (store in memory)."""
        self.sent_messages.append(message)

        results = []

        for recipient in message.all_recipients:
            result = DeliveryResult(
                message_id=message.id,
                status=EmailStatus.SENT,
                recipient=recipient.address
            )
            results.append(result)
            self.delivery_results.append(result)

        return results

    async def verify(self) -> bool:
        """Verify transport."""
        return True

    def clear(self) -> None:
        """Clear sent messages."""
        self.sent_messages.clear()
        self.delivery_results.clear()


class SMTPTransport(EmailTransport):
    """SMTP email transport (simulated)."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 587,
        username: str = None,
        password: str = None,
        use_tls: bool = True,
        timeout: float = 30.0
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.timeout = timeout

    async def send(self, message: EmailMessage) -> List[DeliveryResult]:
        """Send email via SMTP (simulated)."""
        # Simulate connection delay
        await asyncio.sleep(0.01)

        results = []

        for recipient in message.all_recipients:
            # Simulate sending
            result = DeliveryResult(
                message_id=message.id,
                status=EmailStatus.SENT,
                recipient=recipient.address,
                smtp_code=250
            )
            results.append(result)

        return results

    async def verify(self) -> bool:
        """Verify SMTP connection (simulated)."""
        await asyncio.sleep(0.01)
        return True


# =============================================================================
# EMAIL QUEUE
# =============================================================================

class EmailQueue:
    """Email queue for async sending."""

    def __init__(
        self,
        transport: EmailTransport,
        max_concurrent: int = 10,
        retry_attempts: int = 3,
        retry_delay: float = 60.0
    ):
        self.transport = transport
        self.max_concurrent = max_concurrent
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

        self._queue: asyncio.Queue = asyncio.Queue()
        self._pending: Dict[str, Tuple[EmailMessage, int]] = {}
        self._results: Dict[str, List[DeliveryResult]] = {}
        self._running = False
        self._workers: List[asyncio.Task] = []

    async def enqueue(self, message: EmailMessage) -> str:
        """Add message to queue."""
        await self._queue.put((message, 0))
        self._pending[message.id] = (message, 0)

        return message.id

    async def start(self) -> None:
        """Start queue workers."""
        if self._running:
            return

        self._running = True

        for i in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)

    async def stop(self) -> None:
        """Stop queue workers."""
        self._running = False

        for worker in self._workers:
            worker.cancel()

        self._workers.clear()

    async def _worker(self, worker_id: int) -> None:
        """Queue worker."""
        while self._running:
            try:
                message, attempt = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )

                try:
                    results = await self.transport.send(message)
                    self._results[message.id] = results
                    self._pending.pop(message.id, None)

                except Exception as e:
                    if attempt < self.retry_attempts:
                        # Retry later
                        await asyncio.sleep(self.retry_delay)
                        await self._queue.put((message, attempt + 1))
                        self._pending[message.id] = (message, attempt + 1)

                    else:
                        # Failed permanently
                        results = [
                            DeliveryResult(
                                message_id=message.id,
                                status=EmailStatus.FAILED,
                                recipient=r.address,
                                error_message=str(e)
                            )
                            for r in message.all_recipients
                        ]
                        self._results[message.id] = results
                        self._pending.pop(message.id, None)

            except asyncio.TimeoutError:
                continue

            except asyncio.CancelledError:
                break

    def get_results(self, message_id: str) -> Optional[List[DeliveryResult]]:
        """Get delivery results."""
        return self._results.get(message_id)

    def is_pending(self, message_id: str) -> bool:
        """Check if message is pending."""
        return message_id in self._pending

    @property
    def queue_size(self) -> int:
        """Get queue size."""
        return self._queue.qsize()

    @property
    def pending_count(self) -> int:
        """Get pending count."""
        return len(self._pending)


# =============================================================================
# EMAIL SERVICE
# =============================================================================

class EmailService:
    """
    Comprehensive Email Service for BAEL.

    Provides email sending, templating, and management.
    """

    def __init__(
        self,
        transport: EmailTransport = None,
        default_from: EmailAddress = None
    ):
        self._transport = transport or MemoryTransport()
        self._default_from = default_from
        self._templates: Dict[str, EmailTemplate] = {}
        self._sent_history: List[DeliveryResult] = []
        self._bounce_handlers: List[Callable[[DeliveryResult], None]] = []
        self._queue: Optional[EmailQueue] = None

    # -------------------------------------------------------------------------
    # SENDING
    # -------------------------------------------------------------------------

    async def send(self, message: EmailMessage) -> List[DeliveryResult]:
        """Send email message."""
        # Apply default from
        if not message.from_address and self._default_from:
            message.from_address = self._default_from

        # Validate
        if not message.is_valid:
            raise ValueError("Invalid email message")

        # Send
        results = await self._transport.send(message)
        self._sent_history.extend(results)

        # Handle bounces
        for result in results:
            if result.status == EmailStatus.BOUNCED:
                self._handle_bounce(result)

        return results

    async def send_simple(
        self,
        to: str,
        subject: str,
        body: str,
        html: str = None,
        from_address: str = None
    ) -> List[DeliveryResult]:
        """Send simple email."""
        message = EmailMessage()
        message.add_to(to)
        message.set_subject(subject)
        message.set_body(text=body, html=html)

        if from_address:
            message.set_from(from_address)

        return await self.send(message)

    async def send_batch(
        self,
        messages: List[EmailMessage]
    ) -> Dict[str, List[DeliveryResult]]:
        """Send batch of emails."""
        results = {}

        for message in messages:
            results[message.id] = await self.send(message)

        return results

    async def send_to_many(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        html: str = None,
        personalize: Callable[[str], Dict[str, Any]] = None
    ) -> Dict[str, List[DeliveryResult]]:
        """Send to multiple recipients with personalization."""
        results = {}

        for recipient in recipients:
            message = EmailMessage()
            message.add_to(recipient)
            message.set_subject(subject)

            if personalize:
                context = personalize(recipient)
                msg_body = self._personalize_text(body, context)
                msg_html = self._personalize_text(html, context) if html else None
            else:
                msg_body = body
                msg_html = html

            message.set_body(text=msg_body, html=msg_html)
            results[recipient] = await self.send(message)

        return results

    def _personalize_text(self, text: str, context: Dict[str, Any]) -> str:
        """Personalize text with context."""
        if not text:
            return text

        result = text

        for key, value in context.items():
            result = result.replace(f"{{{{ {key} }}}}", str(value))
            result = result.replace(f"{{{{{key}}}}}", str(value))

        return result

    # -------------------------------------------------------------------------
    # QUEUE
    # -------------------------------------------------------------------------

    async def queue(self, message: EmailMessage) -> str:
        """Add message to queue."""
        if not self._queue:
            self._queue = EmailQueue(self._transport)
            await self._queue.start()

        return await self._queue.enqueue(message)

    async def start_queue(self) -> None:
        """Start email queue."""
        if not self._queue:
            self._queue = EmailQueue(self._transport)

        await self._queue.start()

    async def stop_queue(self) -> None:
        """Stop email queue."""
        if self._queue:
            await self._queue.stop()

    # -------------------------------------------------------------------------
    # TEMPLATES
    # -------------------------------------------------------------------------

    def register_template(self, template: EmailTemplate) -> None:
        """Register email template."""
        self._templates[template.id] = template

    def get_template(self, template_id: str) -> Optional[EmailTemplate]:
        """Get template by ID."""
        return self._templates.get(template_id)

    async def send_template(
        self,
        template_id: str,
        to: str,
        context: Dict[str, Any],
        from_address: str = None
    ) -> List[DeliveryResult]:
        """Send email using template."""
        template = self._templates.get(template_id)

        if not template:
            raise ValueError(f"Template not found: {template_id}")

        message = template.render(context)
        message.add_to(to)

        if from_address:
            message.set_from(from_address)

        return await self.send(message)

    # -------------------------------------------------------------------------
    # BOUNCE HANDLING
    # -------------------------------------------------------------------------

    def on_bounce(self, handler: Callable[[DeliveryResult], None]) -> None:
        """Register bounce handler."""
        self._bounce_handlers.append(handler)

    def _handle_bounce(self, result: DeliveryResult) -> None:
        """Handle bounce."""
        for handler in self._bounce_handlers:
            try:
                handler(result)
            except Exception as e:
                logger.error(f"Bounce handler error: {e}")

    # -------------------------------------------------------------------------
    # VALIDATION
    # -------------------------------------------------------------------------

    def validate_email(self, email: str) -> bool:
        """Validate email address."""
        addr = EmailAddress(email)
        return addr.is_valid

    def validate_domain(self, email: str) -> bool:
        """Validate email domain (simulated MX lookup)."""
        addr = EmailAddress(email)

        if not addr.is_valid:
            return False

        # In real implementation, would do MX lookup
        valid_tlds = ['com', 'net', 'org', 'edu', 'gov', 'io', 'co', 'nl']
        tld = addr.domain.split('.')[-1]

        return tld in valid_tlds

    # -------------------------------------------------------------------------
    # HISTORY
    # -------------------------------------------------------------------------

    def get_history(
        self,
        limit: int = 100,
        status: EmailStatus = None
    ) -> List[DeliveryResult]:
        """Get delivery history."""
        results = self._sent_history

        if status:
            results = [r for r in results if r.status == status]

        return results[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get email statistics."""
        total = len(self._sent_history)

        by_status = defaultdict(int)

        for result in self._sent_history:
            by_status[result.status.value] += 1

        return {
            "total": total,
            "by_status": dict(by_status),
            "templates": len(self._templates),
            "queue_size": self._queue.queue_size if self._queue else 0
        }


# =============================================================================
# BUILDER
# =============================================================================

class EmailBuilder:
    """Fluent email builder."""

    def __init__(self):
        self._message = EmailMessage()

    def from_address(self, address: str, name: str = None) -> 'EmailBuilder':
        """Set from address."""
        self._message.set_from(address, name)
        return self

    def to(self, address: str, name: str = None) -> 'EmailBuilder':
        """Add to recipient."""
        self._message.add_to(address, name)
        return self

    def cc(self, address: str, name: str = None) -> 'EmailBuilder':
        """Add CC recipient."""
        self._message.add_cc(address, name)
        return self

    def bcc(self, address: str, name: str = None) -> 'EmailBuilder':
        """Add BCC recipient."""
        self._message.add_bcc(address, name)
        return self

    def reply_to(self, address: str, name: str = None) -> 'EmailBuilder':
        """Set reply-to."""
        self._message.reply_to = EmailAddress(address, name)
        return self

    def subject(self, subject: str) -> 'EmailBuilder':
        """Set subject."""
        self._message.set_subject(subject)
        return self

    def text(self, body: str) -> 'EmailBuilder':
        """Set text body."""
        self._message.text_body = body
        return self

    def html(self, body: str) -> 'EmailBuilder':
        """Set HTML body."""
        self._message.html_body = body
        return self

    def attachment(
        self,
        filename: str,
        content: bytes,
        content_type: str = None
    ) -> 'EmailBuilder':
        """Add attachment."""
        self._message.add_attachment(Attachment(
            filename=filename,
            content=content,
            content_type=content_type or "application/octet-stream"
        ))
        return self

    def priority(self, priority: EmailPriority) -> 'EmailBuilder':
        """Set priority."""
        self._message.set_priority(priority)
        return self

    def header(self, name: str, value: str) -> 'EmailBuilder':
        """Add header."""
        self._message.add_header(name, value)
        return self

    def tag(self, tag: str) -> 'EmailBuilder':
        """Add tag."""
        self._message.tags.append(tag)
        return self

    def metadata(self, key: str, value: Any) -> 'EmailBuilder':
        """Add metadata."""
        self._message.metadata[key] = value
        return self

    def schedule(self, send_at: datetime) -> 'EmailBuilder':
        """Schedule email."""
        self._message.schedule(send_at)
        return self

    def build(self) -> EmailMessage:
        """Build email message."""
        return self._message


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Email Service System."""
    print("=" * 70)
    print("BAEL - EMAIL SERVICE SYSTEM DEMO")
    print("Comprehensive Email Operations")
    print("=" * 70)
    print()

    # Create service with memory transport
    transport = MemoryTransport()
    service = EmailService(
        transport=transport,
        default_from=EmailAddress("noreply@bael.ai", "BAEL System")
    )

    # 1. Simple Email
    print("1. SIMPLE EMAIL:")
    print("-" * 40)

    results = await service.send_simple(
        to="user@example.com",
        subject="Welcome to BAEL",
        body="Hello! Welcome to the BAEL AI system."
    )

    for result in results:
        print(f"   To: {result.recipient}")
        print(f"   Status: {result.status.value}")
    print()

    # 2. Email Builder
    print("2. EMAIL BUILDER:")
    print("-" * 40)

    message = (EmailBuilder()
        .from_address("admin@bael.ai", "BAEL Admin")
        .to("user@example.com", "Test User")
        .cc("manager@example.com")
        .subject("Important Update")
        .text("This is the plain text version.")
        .html("<h1>Important Update</h1><p>This is HTML.</p>")
        .priority(EmailPriority.HIGH)
        .tag("important")
        .metadata("campaign", "update-v1")
        .build())

    results = await service.send(message)

    print(f"   Subject: {message.subject}")
    print(f"   Recipients: {len(message.all_recipients)}")
    print(f"   Priority: {message.priority.name}")
    print(f"   Tags: {message.tags}")
    print()

    # 3. Email Address Validation
    print("3. EMAIL VALIDATION:")
    print("-" * 40)

    test_emails = [
        "valid@example.com",
        "also.valid@sub.domain.com",
        "invalid-email",
        "missing@domain",
        "@no-local.com"
    ]

    for email in test_emails:
        addr = EmailAddress(email)
        print(f"   {email}: {addr.is_valid}")
    print()

    # 4. Attachments
    print("4. ATTACHMENTS:")
    print("-" * 40)

    message = EmailMessage()
    message.set_from("sender@bael.ai")
    message.add_to("recipient@example.com")
    message.set_subject("Document Attached")
    message.set_body(text="Please find the document attached.")

    attachment = Attachment(
        filename="document.txt",
        content=b"This is the document content.",
        content_type="text/plain"
    )
    message.add_attachment(attachment)

    results = await service.send(message)

    print(f"   Attachment: {attachment.filename}")
    print(f"   Size: {attachment.size} bytes")
    print(f"   Sent: {results[0].status.value}")
    print()

    # 5. Email Templates
    print("5. EMAIL TEMPLATES:")
    print("-" * 40)

    template = EmailTemplate(
        id="welcome",
        name="Welcome Email",
        subject_template="Welcome, {{ name }}!",
        text_template="Hi {{ name }}, welcome to {{ product }}!",
        html_template="<h1>Hi {{ name }}!</h1><p>Welcome to {{ product }}!</p>",
        variables=["name", "product"]
    )

    service.register_template(template)

    results = await service.send_template(
        template_id="welcome",
        to="newuser@example.com",
        context={"name": "John", "product": "BAEL AI"}
    )

    print(f"   Template: {template.name}")
    print(f"   Variables: {template.variables}")
    print(f"   Sent: {results[0].status.value}")
    print()

    # 6. Batch Sending
    print("6. BATCH SENDING:")
    print("-" * 40)

    messages = []

    for i in range(3):
        msg = EmailMessage()
        msg.set_from("batch@bael.ai")
        msg.add_to(f"user{i}@example.com")
        msg.set_subject(f"Batch Message {i}")
        msg.set_body(text=f"This is batch message {i}")
        messages.append(msg)

    batch_results = await service.send_batch(messages)

    print(f"   Messages sent: {len(batch_results)}")

    for msg_id, results in batch_results.items():
        print(f"      {msg_id[:8]}: {results[0].status.value}")
    print()

    # 7. Send to Many
    print("7. SEND TO MANY:")
    print("-" * 40)

    recipients = ["alice@example.com", "bob@example.com", "carol@example.com"]

    def personalize(email: str) -> Dict[str, Any]:
        name = email.split("@")[0].title()
        return {"name": name}

    results = await service.send_to_many(
        recipients=recipients,
        subject="Hello {{ name }}",
        body="Dear {{ name }}, this is a personalized message.",
        personalize=personalize
    )

    for recipient, res in results.items():
        print(f"   {recipient}: {res[0].status.value}")
    print()

    # 8. MIME Message
    print("8. MIME MESSAGE:")
    print("-" * 40)

    message = EmailMessage()
    message.set_from("sender@bael.ai", "BAEL Sender")
    message.add_to("recipient@example.com", "Recipient")
    message.set_subject("MIME Test")
    message.set_body(
        text="Plain text version",
        html="<b>HTML version</b>"
    )

    mime_msg = message.to_mime()

    print(f"   From: {mime_msg['From']}")
    print(f"   To: {mime_msg['To']}")
    print(f"   Subject: {mime_msg['Subject']}")
    print(f"   Message-ID: {mime_msg['Message-ID'][:40]}...")
    print()

    # 9. Email Statistics
    print("9. EMAIL STATISTICS:")
    print("-" * 40)

    stats = service.get_stats()

    print(f"   Total sent: {stats['total']}")
    print(f"   By status: {stats['by_status']}")
    print(f"   Templates: {stats['templates']}")
    print()

    # 10. Memory Transport Inspection
    print("10. MEMORY TRANSPORT:")
    print("-" * 40)

    print(f"   Messages stored: {len(transport.sent_messages)}")
    print(f"   Delivery results: {len(transport.delivery_results)}")

    for msg in transport.sent_messages[:3]:
        print(f"      - {msg.subject}")
    print()

    # 11. Priority Levels
    print("11. PRIORITY LEVELS:")
    print("-" * 40)

    for priority in EmailPriority:
        print(f"   {priority.name}: {priority.value}")
    print()

    # 12. Email History
    print("12. EMAIL HISTORY:")
    print("-" * 40)

    history = service.get_history(limit=5)

    for result in history:
        print(f"   {result.recipient}: {result.status.value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Email Service Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
