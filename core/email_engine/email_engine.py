"""
BAEL Email Engine
==================

Comprehensive email system with templates and tracking.

"Ba'el's messages reach all corners of existence." — Ba'el
"""

import asyncio
import logging
import uuid
import re
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
import base64

logger = logging.getLogger("BAEL.Email")


# ============================================================================
# ENUMS
# ============================================================================

class EmailStatus(Enum):
    """Email status."""
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    FAILED = "failed"
    SPAM = "spam"


class EmailPriority(Enum):
    """Email priority."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class EmailProvider(Enum):
    """Email provider."""
    SMTP = "smtp"
    SENDGRID = "sendgrid"
    MAILGUN = "mailgun"
    SES = "ses"
    POSTMARK = "postmark"
    MOCK = "mock"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class EmailAddress:
    """An email address."""
    email: str
    name: Optional[str] = None

    def __str__(self) -> str:
        if self.name:
            return f'"{self.name}" <{self.email}>'
        return self.email

    @classmethod
    def parse(cls, value: Union[str, 'EmailAddress']) -> 'EmailAddress':
        """Parse an email address."""
        if isinstance(value, cls):
            return value

        # Try to parse "Name <email>" format
        match = re.match(r'"?([^"<]+)"?\s*<([^>]+)>', value)
        if match:
            return cls(email=match.group(2).strip(), name=match.group(1).strip())

        return cls(email=value.strip())


@dataclass
class EmailAttachment:
    """An email attachment."""
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"
    inline: bool = False
    content_id: Optional[str] = None


@dataclass
class Email:
    """An email message."""
    id: str

    # Addresses
    to: List[EmailAddress]
    from_address: EmailAddress

    # Content
    subject: str
    html_body: Optional[str] = None
    text_body: Optional[str] = None

    # CC/BCC
    cc: List[EmailAddress] = field(default_factory=list)
    bcc: List[EmailAddress] = field(default_factory=list)

    # Reply-to
    reply_to: Optional[EmailAddress] = None

    # Attachments
    attachments: List[EmailAttachment] = field(default_factory=list)

    # Priority
    priority: EmailPriority = EmailPriority.NORMAL

    # Status
    status: EmailStatus = EmailStatus.PENDING

    # Tracking
    track_opens: bool = True
    track_clicks: bool = True
    tracking_id: Optional[str] = None

    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None

    # Error
    error: Optional[str] = None


@dataclass
class EmailTemplate:
    """An email template."""
    id: str
    name: str

    # Content
    subject_template: str
    html_template: Optional[str] = None
    text_template: Optional[str] = None

    # Defaults
    default_from: Optional[EmailAddress] = None

    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def render(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Render template with context."""
        result = {}

        # Simple variable substitution
        result['subject'] = self._render_string(self.subject_template, context)

        if self.html_template:
            result['html_body'] = self._render_string(self.html_template, context)

        if self.text_template:
            result['text_body'] = self._render_string(self.text_template, context)

        return result

    def _render_string(self, template: str, context: Dict[str, Any]) -> str:
        """Render a string template."""
        result = template

        for key, value in context.items():
            result = result.replace(f'{{{{{key}}}}}', str(value))
            result = result.replace(f'{{{{ {key} }}}}', str(value))

        return result


@dataclass
class EmailConfig:
    """Email engine configuration."""
    provider: EmailProvider = EmailProvider.MOCK

    # SMTP settings
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True

    # API settings
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None

    # Defaults
    default_from_email: str = "noreply@bael.ai"
    default_from_name: str = "BAEL"

    # Queue settings
    queue_enabled: bool = True
    max_retries: int = 3
    retry_delay_seconds: float = 60.0

    # Tracking
    tracking_enabled: bool = True
    tracking_domain: Optional[str] = None


# ============================================================================
# EMAIL SENDER
# ============================================================================

class EmailSender:
    """Base class for email senders."""

    async def send(self, email: Email) -> bool:
        """Send an email."""
        raise NotImplementedError


class SMTPSender(EmailSender):
    """SMTP email sender."""

    def __init__(self, config: EmailConfig):
        """Initialize SMTP sender."""
        self.config = config

    async def send(self, email: Email) -> bool:
        """Send email via SMTP."""
        try:
            # Create message
            if email.html_body and email.text_body:
                msg = MIMEMultipart('alternative')
                msg.attach(MIMEText(email.text_body, 'plain'))
                msg.attach(MIMEText(email.html_body, 'html'))
            elif email.html_body:
                msg = MIMEMultipart()
                msg.attach(MIMEText(email.html_body, 'html'))
            else:
                msg = MIMEText(email.text_body or '', 'plain')

            # Headers
            msg['Subject'] = email.subject
            msg['From'] = str(email.from_address)
            msg['To'] = ', '.join(str(a) for a in email.to)

            if email.cc:
                msg['Cc'] = ', '.join(str(a) for a in email.cc)

            if email.reply_to:
                msg['Reply-To'] = str(email.reply_to)

            # Attachments
            for attachment in email.attachments:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.content)
                encoders.encode_base64(part)

                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{attachment.filename}"'
                )

                if isinstance(msg, MIMEMultipart):
                    msg.attach(part)

            # Send
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_sync, msg, email)

            return True

        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            email.error = str(e)
            return False

    def _send_sync(self, msg: MIMEBase, email: Email) -> None:
        """Send synchronously."""
        with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
            if self.config.smtp_use_tls:
                server.starttls()

            if self.config.smtp_username and self.config.smtp_password:
                server.login(self.config.smtp_username, self.config.smtp_password)

            all_recipients = [a.email for a in email.to + email.cc + email.bcc]
            server.send_message(msg, to_addrs=all_recipients)


class MockSender(EmailSender):
    """Mock email sender for testing."""

    def __init__(self):
        """Initialize mock sender."""
        self.sent_emails: List[Email] = []

    async def send(self, email: Email) -> bool:
        """Mock send email."""
        logger.info(f"Mock sending email: {email.subject} to {email.to}")
        self.sent_emails.append(email)
        return True


# ============================================================================
# EMAIL QUEUE
# ============================================================================

class EmailQueue:
    """Queue for email processing."""

    def __init__(self):
        """Initialize queue."""
        self._queue: List[Email] = []
        self._lock = threading.Lock()

    def enqueue(self, email: Email) -> None:
        """Add email to queue."""
        with self._lock:
            email.status = EmailStatus.QUEUED
            self._queue.append(email)
            self._queue.sort(key=lambda e: (-e.priority.value, e.created_at))

    def dequeue(self) -> Optional[Email]:
        """Get next email from queue."""
        with self._lock:
            if self._queue:
                return self._queue.pop(0)
            return None

    def size(self) -> int:
        """Get queue size."""
        return len(self._queue)


# ============================================================================
# MAIN EMAIL ENGINE
# ============================================================================

class EmailEngine:
    """
    Main email engine.

    Features:
    - Multiple providers
    - Templates
    - Tracking
    - Queueing

    "Ba'el's voice echoes across all channels." — Ba'el
    """

    def __init__(self, config: Optional[EmailConfig] = None):
        """Initialize email engine."""
        self.config = config or EmailConfig()

        # Sender
        self._sender = self._create_sender()

        # Queue
        self._queue = EmailQueue()

        # Templates
        self._templates: Dict[str, EmailTemplate] = {}

        # Tracking
        self._sent: Dict[str, Email] = {}
        self._stats: Dict[str, int] = defaultdict(int)

        # Processing
        self._running = False
        self._task: Optional[asyncio.Task] = None

        self._lock = threading.RLock()

        logger.info("EmailEngine initialized")

    def _create_sender(self) -> EmailSender:
        """Create sender based on config."""
        if self.config.provider == EmailProvider.SMTP:
            return SMTPSender(self.config)
        else:
            return MockSender()

    # ========================================================================
    # SENDING
    # ========================================================================

    async def send(
        self,
        to: Union[str, List[str], EmailAddress, List[EmailAddress]],
        subject: str,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
        from_address: Optional[Union[str, EmailAddress]] = None,
        **kwargs
    ) -> Email:
        """
        Send an email.

        Args:
            to: Recipient(s)
            subject: Email subject
            html_body: HTML body
            text_body: Plain text body
            from_address: Sender address

        Returns:
            Email object
        """
        # Normalize recipients
        if isinstance(to, str):
            to = [EmailAddress.parse(to)]
        elif isinstance(to, EmailAddress):
            to = [to]
        else:
            to = [EmailAddress.parse(r) for r in to]

        # From address
        if from_address:
            from_addr = EmailAddress.parse(from_address)
        else:
            from_addr = EmailAddress(
                email=self.config.default_from_email,
                name=self.config.default_from_name
            )

        # Create email
        email = Email(
            id=str(uuid.uuid4()),
            to=to,
            from_address=from_addr,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            tracking_id=str(uuid.uuid4()) if self.config.tracking_enabled else None,
            **kwargs
        )

        # Queue or send immediately
        if self.config.queue_enabled:
            self._queue.enqueue(email)
        else:
            await self._send_email(email)

        return email

    async def send_template(
        self,
        template_name: str,
        to: Union[str, List[str], EmailAddress, List[EmailAddress]],
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Email:
        """Send an email using a template."""
        template = self._templates.get(template_name)

        if not template:
            raise ValueError(f"Template not found: {template_name}")

        # Render template
        rendered = template.render(context or {})

        # Merge kwargs
        send_kwargs = {
            'subject': rendered['subject'],
            'html_body': rendered.get('html_body'),
            'text_body': rendered.get('text_body'),
            **kwargs
        }

        if template.default_from and 'from_address' not in kwargs:
            send_kwargs['from_address'] = template.default_from

        return await self.send(to, **send_kwargs)

    async def _send_email(self, email: Email) -> bool:
        """Actually send an email."""
        email.status = EmailStatus.SENDING

        try:
            success = await self._sender.send(email)

            if success:
                email.status = EmailStatus.SENT
                email.sent_at = datetime.now()
                self._stats['sent'] += 1
            else:
                email.status = EmailStatus.FAILED
                self._stats['failed'] += 1

            # Store for tracking
            with self._lock:
                self._sent[email.id] = email

            return success

        except Exception as e:
            logger.error(f"Send failed: {e}")
            email.status = EmailStatus.FAILED
            email.error = str(e)
            self._stats['failed'] += 1
            return False

    # ========================================================================
    # TEMPLATES
    # ========================================================================

    def register_template(
        self,
        name: str,
        subject_template: str,
        html_template: Optional[str] = None,
        text_template: Optional[str] = None,
        **kwargs
    ) -> EmailTemplate:
        """Register an email template."""
        template = EmailTemplate(
            id=str(uuid.uuid4()),
            name=name,
            subject_template=subject_template,
            html_template=html_template,
            text_template=text_template,
            **kwargs
        )

        with self._lock:
            self._templates[name] = template

        return template

    def get_template(self, name: str) -> Optional[EmailTemplate]:
        """Get a template by name."""
        return self._templates.get(name)

    # ========================================================================
    # QUEUE PROCESSING
    # ========================================================================

    async def start_processing(self) -> None:
        """Start queue processing."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._process_loop())

    async def stop_processing(self) -> None:
        """Stop queue processing."""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _process_loop(self) -> None:
        """Process queue loop."""
        while self._running:
            try:
                email = self._queue.dequeue()

                if email:
                    await self._send_email(email)
                else:
                    await asyncio.sleep(1.0)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Processing error: {e}")

    # ========================================================================
    # TRACKING
    # ========================================================================

    def track_open(self, email_id: str) -> bool:
        """Track email open."""
        with self._lock:
            if email_id in self._sent:
                email = self._sent[email_id]
                if email.status == EmailStatus.SENT:
                    email.status = EmailStatus.OPENED
                    email.opened_at = datetime.now()
                    self._stats['opened'] += 1
                    return True
        return False

    def track_click(self, email_id: str, url: str) -> bool:
        """Track link click."""
        with self._lock:
            if email_id in self._sent:
                email = self._sent[email_id]
                email.status = EmailStatus.CLICKED
                self._stats['clicked'] += 1
                return True
        return False

    def track_bounce(self, email_id: str, reason: str = "") -> bool:
        """Track bounce."""
        with self._lock:
            if email_id in self._sent:
                email = self._sent[email_id]
                email.status = EmailStatus.BOUNCED
                email.error = reason
                self._stats['bounced'] += 1
                return True
        return False

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_email(self, email_id: str) -> Optional[Email]:
        """Get an email by ID."""
        return self._sent.get(email_id)

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'provider': self.config.provider.value,
            'queue_size': self._queue.size(),
            'templates': len(self._templates),
            'sent': self._stats['sent'],
            'failed': self._stats['failed'],
            'opened': self._stats['opened'],
            'clicked': self._stats['clicked'],
            'bounced': self._stats['bounced'],
            'processing': self._running
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

email_engine = EmailEngine()
