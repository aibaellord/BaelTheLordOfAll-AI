"""
BAEL - Integration Connectors
External service integrations and connectors.

Features:
- Slack integration
- Discord integration
- Email (SMTP/IMAP)
- Webhook handling
- Notion integration
- GitHub integration
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ConnectorType(Enum):
    """Types of connectors."""
    SLACK = "slack"
    DISCORD = "discord"
    EMAIL = "email"
    WEBHOOK = "webhook"
    NOTION = "notion"
    GITHUB = "github"
    JIRA = "jira"
    LINEAR = "linear"


class MessagePriority(Enum):
    """Message priority."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Message:
    """Universal message format."""
    id: str
    content: str
    author: str
    channel: str
    timestamp: float
    source: ConnectorType
    thread_id: Optional[str] = None
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SendResult:
    """Result of sending a message."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectorConfig:
    """Configuration for a connector."""
    connector_type: ConnectorType
    credentials: Dict[str, str]
    settings: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# BASE CONNECTOR
# =============================================================================

class Connector(ABC):
    """Abstract connector base class."""

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self._connected = False
        self._message_handlers: List[Callable] = []

    @property
    @abstractmethod
    def connector_type(self) -> ConnectorType:
        pass

    @abstractmethod
    async def connect(self) -> bool:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        pass

    @abstractmethod
    async def send_message(
        self,
        channel: str,
        content: str,
        **kwargs
    ) -> SendResult:
        pass

    @abstractmethod
    async def get_messages(
        self,
        channel: str,
        limit: int = 100
    ) -> List[Message]:
        pass

    def on_message(self, handler: Callable) -> None:
        """Register message handler."""
        self._message_handlers.append(handler)

    async def _dispatch_message(self, message: Message) -> None:
        """Dispatch message to handlers."""
        for handler in self._message_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Handler error: {e}")


# =============================================================================
# SLACK CONNECTOR
# =============================================================================

class SlackConnector(Connector):
    """Slack integration connector."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.token = config.credentials.get("token")
        self.signing_secret = config.credentials.get("signing_secret")
        self._base_url = "https://slack.com/api"

    @property
    def connector_type(self) -> ConnectorType:
        return ConnectorType.SLACK

    async def connect(self) -> bool:
        """Connect to Slack API."""
        try:
            # Test connection with auth.test
            result = await self._api_call("auth.test")
            self._connected = result.get("ok", False)

            if self._connected:
                self._team_id = result.get("team_id")
                self._bot_id = result.get("user_id")
                logger.info(f"Connected to Slack team: {result.get('team')}")

            return self._connected

        except Exception as e:
            logger.error(f"Slack connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Slack."""
        self._connected = False

    async def send_message(
        self,
        channel: str,
        content: str,
        thread_ts: Optional[str] = None,
        blocks: Optional[List[Dict]] = None,
        attachments: Optional[List[Dict]] = None
    ) -> SendResult:
        """Send message to Slack channel."""
        try:
            payload = {
                "channel": channel,
                "text": content
            }

            if thread_ts:
                payload["thread_ts"] = thread_ts

            if blocks:
                payload["blocks"] = blocks

            if attachments:
                payload["attachments"] = attachments

            result = await self._api_call("chat.postMessage", payload)

            if result.get("ok"):
                return SendResult(
                    success=True,
                    message_id=result.get("ts"),
                    metadata={"channel": result.get("channel")}
                )
            else:
                return SendResult(
                    success=False,
                    error=result.get("error", "Unknown error")
                )

        except Exception as e:
            return SendResult(success=False, error=str(e))

    async def get_messages(
        self,
        channel: str,
        limit: int = 100
    ) -> List[Message]:
        """Get messages from channel."""
        try:
            result = await self._api_call("conversations.history", {
                "channel": channel,
                "limit": limit
            })

            if not result.get("ok"):
                return []

            messages = []
            for msg in result.get("messages", []):
                messages.append(Message(
                    id=msg.get("ts", ""),
                    content=msg.get("text", ""),
                    author=msg.get("user", ""),
                    channel=channel,
                    timestamp=float(msg.get("ts", 0)),
                    source=ConnectorType.SLACK,
                    thread_id=msg.get("thread_ts"),
                    metadata={"blocks": msg.get("blocks")}
                ))

            return messages

        except Exception as e:
            logger.error(f"Failed to get Slack messages: {e}")
            return []

    async def _api_call(
        self,
        method: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make Slack API call."""
        import httpx

        url = f"{self._base_url}/{method}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            if data:
                response = await client.post(url, headers=headers, json=data)
            else:
                response = await client.get(url, headers=headers)

            return response.json()

    def verify_signature(
        self,
        signature: str,
        timestamp: str,
        body: str
    ) -> bool:
        """Verify Slack request signature."""
        if not self.signing_secret:
            return False

        sig_basestring = f"v0:{timestamp}:{body}"
        computed = "v0=" + hmac.new(
            self.signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(computed, signature)

    def create_block_kit(self) -> "SlackBlockBuilder":
        """Create Block Kit builder."""
        return SlackBlockBuilder()


class SlackBlockBuilder:
    """Slack Block Kit builder."""

    def __init__(self):
        self._blocks: List[Dict] = []

    def section(
        self,
        text: str,
        accessory: Optional[Dict] = None
    ) -> "SlackBlockBuilder":
        """Add section block."""
        block = {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text}
        }

        if accessory:
            block["accessory"] = accessory

        self._blocks.append(block)
        return self

    def divider(self) -> "SlackBlockBuilder":
        """Add divider."""
        self._blocks.append({"type": "divider"})
        return self

    def header(self, text: str) -> "SlackBlockBuilder":
        """Add header block."""
        self._blocks.append({
            "type": "header",
            "text": {"type": "plain_text", "text": text}
        })
        return self

    def actions(self, elements: List[Dict]) -> "SlackBlockBuilder":
        """Add actions block."""
        self._blocks.append({
            "type": "actions",
            "elements": elements
        })
        return self

    def button(
        self,
        text: str,
        action_id: str,
        value: str = "",
        style: Optional[str] = None
    ) -> Dict:
        """Create button element."""
        btn = {
            "type": "button",
            "text": {"type": "plain_text", "text": text},
            "action_id": action_id,
            "value": value
        }

        if style in ("primary", "danger"):
            btn["style"] = style

        return btn

    def build(self) -> List[Dict]:
        """Build blocks."""
        return self._blocks


# =============================================================================
# DISCORD CONNECTOR
# =============================================================================

class DiscordConnector(Connector):
    """Discord integration connector."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.token = config.credentials.get("token")
        self._base_url = "https://discord.com/api/v10"

    @property
    def connector_type(self) -> ConnectorType:
        return ConnectorType.DISCORD

    async def connect(self) -> bool:
        """Connect to Discord API."""
        try:
            result = await self._api_call("GET", "/users/@me")
            self._connected = "id" in result

            if self._connected:
                self._bot_id = result.get("id")
                logger.info(f"Connected to Discord as: {result.get('username')}")

            return self._connected

        except Exception as e:
            logger.error(f"Discord connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        self._connected = False

    async def send_message(
        self,
        channel: str,
        content: str,
        embed: Optional[Dict] = None,
        components: Optional[List[Dict]] = None
    ) -> SendResult:
        """Send message to Discord channel."""
        try:
            payload = {"content": content}

            if embed:
                payload["embeds"] = [embed]

            if components:
                payload["components"] = components

            result = await self._api_call(
                "POST",
                f"/channels/{channel}/messages",
                payload
            )

            return SendResult(
                success="id" in result,
                message_id=result.get("id"),
                error=result.get("message") if "id" not in result else None
            )

        except Exception as e:
            return SendResult(success=False, error=str(e))

    async def get_messages(
        self,
        channel: str,
        limit: int = 100
    ) -> List[Message]:
        """Get messages from channel."""
        try:
            result = await self._api_call(
                "GET",
                f"/channels/{channel}/messages?limit={limit}"
            )

            if not isinstance(result, list):
                return []

            messages = []
            for msg in result:
                messages.append(Message(
                    id=msg.get("id", ""),
                    content=msg.get("content", ""),
                    author=msg.get("author", {}).get("username", ""),
                    channel=channel,
                    timestamp=time.time(),  # Would parse ISO timestamp
                    source=ConnectorType.DISCORD,
                    metadata={"embeds": msg.get("embeds")}
                ))

            return messages

        except Exception as e:
            logger.error(f"Failed to get Discord messages: {e}")
            return []

    async def _api_call(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make Discord API call."""
        import httpx

        url = f"{self._base_url}{endpoint}"
        headers = {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=data)
            else:
                response = await client.request(
                    method, url, headers=headers, json=data
                )

            return response.json()

    def create_embed(
        self,
        title: str,
        description: str = "",
        color: int = 0x5865F2
    ) -> Dict:
        """Create Discord embed."""
        return {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat()
        }


# =============================================================================
# EMAIL CONNECTOR
# =============================================================================

class EmailConnector(Connector):
    """Email (SMTP/IMAP) connector."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.smtp_host = config.credentials.get("smtp_host", "smtp.gmail.com")
        self.smtp_port = int(config.credentials.get("smtp_port", 587))
        self.imap_host = config.credentials.get("imap_host", "imap.gmail.com")
        self.imap_port = int(config.credentials.get("imap_port", 993))
        self.username = config.credentials.get("username")
        self.password = config.credentials.get("password")

    @property
    def connector_type(self) -> ConnectorType:
        return ConnectorType.EMAIL

    async def connect(self) -> bool:
        """Test email connection."""
        # In production, would test SMTP/IMAP connection
        self._connected = bool(self.username and self.password)
        return self._connected

    async def disconnect(self) -> None:
        self._connected = False

    async def send_message(
        self,
        channel: str,  # recipient email
        content: str,
        subject: str = "",
        html: bool = False,
        attachments: Optional[List[Dict]] = None
    ) -> SendResult:
        """Send email."""
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart()
            msg["From"] = self.username
            msg["To"] = channel
            msg["Subject"] = subject or "Message from BAEL"

            # Add body
            content_type = "html" if html else "plain"
            msg.attach(MIMEText(content, content_type))

            # Send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            return SendResult(success=True, message_id=msg["Message-ID"])

        except Exception as e:
            return SendResult(success=False, error=str(e))

    async def get_messages(
        self,
        channel: str = "INBOX",
        limit: int = 100
    ) -> List[Message]:
        """Get emails from folder."""
        try:
            import email
            import imaplib

            messages = []

            with imaplib.IMAP4_SSL(self.imap_host, self.imap_port) as imap:
                imap.login(self.username, self.password)
                imap.select(channel)

                _, data = imap.search(None, "ALL")
                email_ids = data[0].split()[-limit:]

                for email_id in email_ids:
                    _, msg_data = imap.fetch(email_id, "(RFC822)")
                    msg = email.message_from_bytes(msg_data[0][1])

                    # Extract body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()

                    messages.append(Message(
                        id=email_id.decode(),
                        content=body,
                        author=msg["From"],
                        channel=channel,
                        timestamp=time.time(),
                        source=ConnectorType.EMAIL,
                        metadata={"subject": msg["Subject"]}
                    ))

            return messages

        except Exception as e:
            logger.error(f"Failed to get emails: {e}")
            return []


# =============================================================================
# WEBHOOK CONNECTOR
# =============================================================================

class WebhookConnector(Connector):
    """Webhook connector for receiving/sending webhooks."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._webhooks: Dict[str, str] = config.settings.get("webhooks", {})
        self._secret = config.credentials.get("secret")

    @property
    def connector_type(self) -> ConnectorType:
        return ConnectorType.WEBHOOK

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def send_message(
        self,
        channel: str,  # webhook name
        content: str,
        json_payload: Optional[Dict] = None
    ) -> SendResult:
        """Send webhook."""
        try:
            import httpx

            url = self._webhooks.get(channel)
            if not url:
                return SendResult(success=False, error=f"Unknown webhook: {channel}")

            payload = json_payload or {"content": content}

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)

                return SendResult(
                    success=response.status_code < 400,
                    metadata={"status_code": response.status_code}
                )

        except Exception as e:
            return SendResult(success=False, error=str(e))

    async def get_messages(
        self,
        channel: str,
        limit: int = 100
    ) -> List[Message]:
        """Webhooks don't support fetching messages."""
        return []

    def register_webhook(self, name: str, url: str) -> None:
        """Register a webhook URL."""
        self._webhooks[name] = url

    def verify_signature(
        self,
        signature: str,
        payload: str
    ) -> bool:
        """Verify webhook signature."""
        if not self._secret:
            return True

        computed = hmac.new(
            self._secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(computed, signature)


# =============================================================================
# GITHUB CONNECTOR
# =============================================================================

class GitHubConnector(Connector):
    """GitHub integration connector."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.token = config.credentials.get("token")
        self._base_url = "https://api.github.com"

    @property
    def connector_type(self) -> ConnectorType:
        return ConnectorType.GITHUB

    async def connect(self) -> bool:
        try:
            result = await self._api_call("GET", "/user")
            self._connected = "login" in result

            if self._connected:
                logger.info(f"Connected to GitHub as: {result.get('login')}")

            return self._connected

        except Exception as e:
            logger.error(f"GitHub connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        self._connected = False

    async def send_message(
        self,
        channel: str,  # repo/issue format: "owner/repo/issues/1"
        content: str,
        **kwargs
    ) -> SendResult:
        """Add comment to issue/PR."""
        try:
            parts = channel.split("/")
            if len(parts) >= 4:
                owner, repo, _, number = parts[:4]

                result = await self._api_call(
                    "POST",
                    f"/repos/{owner}/{repo}/issues/{number}/comments",
                    {"body": content}
                )

                return SendResult(
                    success="id" in result,
                    message_id=str(result.get("id")),
                    error=result.get("message") if "id" not in result else None
                )

            return SendResult(success=False, error="Invalid channel format")

        except Exception as e:
            return SendResult(success=False, error=str(e))

    async def get_messages(
        self,
        channel: str,  # repo format: "owner/repo"
        limit: int = 100
    ) -> List[Message]:
        """Get issues from repo."""
        try:
            parts = channel.split("/")
            if len(parts) >= 2:
                owner, repo = parts[:2]

                result = await self._api_call(
                    "GET",
                    f"/repos/{owner}/{repo}/issues?per_page={limit}"
                )

                if isinstance(result, list):
                    return [
                        Message(
                            id=str(issue.get("number")),
                            content=issue.get("body", ""),
                            author=issue.get("user", {}).get("login", ""),
                            channel=channel,
                            timestamp=time.time(),
                            source=ConnectorType.GITHUB,
                            metadata={
                                "title": issue.get("title"),
                                "state": issue.get("state"),
                                "labels": issue.get("labels")
                            }
                        )
                        for issue in result
                    ]

            return []

        except Exception as e:
            logger.error(f"Failed to get GitHub issues: {e}")
            return []

    async def _api_call(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Any:
        """Make GitHub API call."""
        import httpx

        url = f"{self._base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, headers=headers)
            else:
                response = await client.request(
                    method, url, headers=headers, json=data
                )

            return response.json()

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        labels: List[str] = None
    ) -> SendResult:
        """Create GitHub issue."""
        try:
            payload = {"title": title, "body": body}
            if labels:
                payload["labels"] = labels

            result = await self._api_call(
                "POST",
                f"/repos/{owner}/{repo}/issues",
                payload
            )

            return SendResult(
                success="number" in result,
                message_id=str(result.get("number")),
                metadata={"url": result.get("html_url")}
            )

        except Exception as e:
            return SendResult(success=False, error=str(e))


# =============================================================================
# CONNECTOR MANAGER
# =============================================================================

class ConnectorManager:
    """Manages multiple connectors."""

    def __init__(self):
        self._connectors: Dict[str, Connector] = {}
        self._factories: Dict[ConnectorType, type] = {
            ConnectorType.SLACK: SlackConnector,
            ConnectorType.DISCORD: DiscordConnector,
            ConnectorType.EMAIL: EmailConnector,
            ConnectorType.WEBHOOK: WebhookConnector,
            ConnectorType.GITHUB: GitHubConnector
        }

    def create(
        self,
        name: str,
        connector_type: ConnectorType,
        credentials: Dict[str, str],
        settings: Dict[str, Any] = None
    ) -> Connector:
        """Create and register connector."""
        config = ConnectorConfig(
            connector_type=connector_type,
            credentials=credentials,
            settings=settings or {}
        )

        factory = self._factories.get(connector_type)
        if not factory:
            raise ValueError(f"Unknown connector type: {connector_type}")

        connector = factory(config)
        self._connectors[name] = connector
        return connector

    def get(self, name: str) -> Optional[Connector]:
        """Get connector by name."""
        return self._connectors.get(name)

    async def connect_all(self) -> Dict[str, bool]:
        """Connect all connectors."""
        results = {}

        for name, connector in self._connectors.items():
            results[name] = await connector.connect()

        return results

    async def disconnect_all(self) -> None:
        """Disconnect all connectors."""
        for connector in self._connectors.values():
            await connector.disconnect()

    def list_connectors(self) -> List[Dict[str, Any]]:
        """List all connectors."""
        return [
            {
                "name": name,
                "type": conn.connector_type.value,
                "connected": conn._connected
            }
            for name, conn in self._connectors.items()
        ]


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def main():
    """Demonstrate connectors."""
    print("=== BAEL Integration Connectors ===\n")

    manager = ConnectorManager()

    # Create Slack connector (demo)
    slack = manager.create(
        "slack_main",
        ConnectorType.SLACK,
        {"token": os.getenv("SLACK_TOKEN", "xoxb-demo")}
    )

    # Create Discord connector (demo)
    discord = manager.create(
        "discord_main",
        ConnectorType.DISCORD,
        {"token": os.getenv("DISCORD_TOKEN", "demo")}
    )

    # Create webhook connector
    webhook = manager.create(
        "webhooks",
        ConnectorType.WEBHOOK,
        {"secret": "webhook-secret"},
        {"webhooks": {"alert": "https://example.com/webhook"}}
    )

    # Create GitHub connector (demo)
    github = manager.create(
        "github",
        ConnectorType.GITHUB,
        {"token": os.getenv("GITHUB_TOKEN", "ghp_demo")}
    )

    print("Registered connectors:")
    for conn in manager.list_connectors():
        print(f"  - {conn['name']}: {conn['type']}")

    # Demonstrate Slack Block Kit builder
    print("\n--- Slack Block Kit ---")
    blocks = (
        slack.create_block_kit()
        .header("Task Update")
        .section("*Task:* Complete documentation\n*Status:* In Progress")
        .divider()
        .section("Click a button to update status:")
        .actions([
            slack.create_block_kit().button("Complete", "complete_btn", "complete", "primary"),
            slack.create_block_kit().button("Cancel", "cancel_btn", "cancel", "danger")
        ])
        .build()
    )

    print(f"Generated {len(blocks)} blocks")

    # Demonstrate Discord embed
    print("\n--- Discord Embed ---")
    embed = discord.create_embed(
        "BAEL Agent Status",
        "All systems operational",
        color=0x00FF00
    )
    print(f"Embed: {embed}")

    # Demonstrate webhook
    print("\n--- Webhook Connector ---")
    webhook_conn = manager.get("webhooks")
    webhook_conn.register_webhook("deploy", "https://example.com/deploy-hook")

    # List all webhooks
    print(f"Registered webhooks: {list(webhook_conn._webhooks.keys())}")

    print("\n=== Connectors ready for use ===")
    print("Set environment variables to use:")
    print("  SLACK_TOKEN, DISCORD_TOKEN, GITHUB_TOKEN")


if __name__ == "__main__":
    asyncio.run(main())
