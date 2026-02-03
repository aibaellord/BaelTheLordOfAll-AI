"""
BAEL - Slack Integration
Integration with Slack for messaging and notifications.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from integrations import BaseIntegration, IntegrationConfig, IntegrationStatus

logger = logging.getLogger("BAEL.Integrations.Slack")


@dataclass
class SlackChannel:
    """Slack channel representation."""
    id: str
    name: str
    is_private: bool
    topic: Optional[str]
    purpose: Optional[str]


@dataclass
class SlackMessage:
    """Slack message representation."""
    ts: str  # Message timestamp (serves as ID)
    channel: str
    user: str
    text: str
    thread_ts: Optional[str]


class SlackIntegration(BaseIntegration):
    """
    Slack integration for messaging and notifications.

    Supports:
    - Channel listing
    - Message sending
    - Thread replies
    - File uploads
    - Notifications
    """

    API_BASE = "https://slack.com/api"

    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self._token = config.credentials.get("bot_token", "")
        self._default_channel = config.settings.get("default_channel", "")

    async def connect(self) -> bool:
        """Connect to Slack API."""
        try:
            result = await self._make_request("auth.test")
            if result and result.get("ok"):
                self.status = IntegrationStatus.CONNECTED
                logger.info(f"Connected to Slack as {result.get('user')}")
                return True
        except Exception as e:
            logger.error(f"Failed to connect to Slack: {e}")
            self.status = IntegrationStatus.ERROR
        return False

    async def disconnect(self) -> None:
        """Disconnect from Slack."""
        self.status = IntegrationStatus.DISCONNECTED

    async def test_connection(self) -> bool:
        """Test Slack connection."""
        try:
            result = await self._make_request("auth.test")
            return result and result.get("ok", False)
        except:
            return False

    async def _make_request(
        self,
        method: str,
        data: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Make an API request to Slack."""
        import json
        import urllib.request

        url = f"{self.API_BASE}/{method}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }

        req = urllib.request.Request(url, headers=headers, method="POST")

        if data:
            req.data = json.dumps(data).encode()

        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            logger.error(f"Slack API error: {e}")
            return None

    # -------------------------------------------------------------------------
    # Channel Operations
    # -------------------------------------------------------------------------

    async def list_channels(self, limit: int = 100) -> List[SlackChannel]:
        """List available channels."""
        result = await self._make_request(
            "conversations.list",
            {"limit": limit}
        )

        if not result or not result.get("ok"):
            return []

        return [
            SlackChannel(
                id=ch["id"],
                name=ch["name"],
                is_private=ch.get("is_private", False),
                topic=ch.get("topic", {}).get("value"),
                purpose=ch.get("purpose", {}).get("value")
            )
            for ch in result.get("channels", [])
        ]

    async def get_channel_id(self, name: str) -> Optional[str]:
        """Get channel ID by name."""
        channels = await self.list_channels()
        for ch in channels:
            if ch.name == name:
                return ch.id
        return None

    # -------------------------------------------------------------------------
    # Message Operations
    # -------------------------------------------------------------------------

    async def send_message(
        self,
        text: str,
        channel: Optional[str] = None,
        thread_ts: Optional[str] = None,
        blocks: Optional[List[Dict]] = None
    ) -> Optional[SlackMessage]:
        """Send a message to a channel."""
        channel = channel or self._default_channel

        data = {
            "channel": channel,
            "text": text
        }

        if thread_ts:
            data["thread_ts"] = thread_ts

        if blocks:
            data["blocks"] = blocks

        result = await self._make_request("chat.postMessage", data)

        if not result or not result.get("ok"):
            logger.error(f"Failed to send message: {result}")
            return None

        return SlackMessage(
            ts=result["ts"],
            channel=result["channel"],
            user=result.get("message", {}).get("user", "bot"),
            text=text,
            thread_ts=thread_ts
        )

    async def send_notification(
        self,
        title: str,
        message: str,
        channel: Optional[str] = None,
        color: str = "good",  # good, warning, danger, or hex
        fields: Optional[List[Dict]] = None
    ) -> Optional[SlackMessage]:
        """Send a notification with rich formatting."""
        channel = channel or self._default_channel

        attachment = {
            "color": color,
            "title": title,
            "text": message,
            "ts": datetime.now().timestamp()
        }

        if fields:
            attachment["fields"] = fields

        data = {
            "channel": channel,
            "text": title,
            "attachments": [attachment]
        }

        result = await self._make_request("chat.postMessage", data)

        if not result or not result.get("ok"):
            return None

        return SlackMessage(
            ts=result["ts"],
            channel=result["channel"],
            user="bot",
            text=message,
            thread_ts=None
        )

    async def reply_in_thread(
        self,
        thread_ts: str,
        text: str,
        channel: Optional[str] = None
    ) -> Optional[SlackMessage]:
        """Reply in a thread."""
        return await self.send_message(
            text=text,
            channel=channel,
            thread_ts=thread_ts
        )

    async def update_message(
        self,
        channel: str,
        ts: str,
        text: str,
        blocks: Optional[List[Dict]] = None
    ) -> bool:
        """Update an existing message."""
        data = {
            "channel": channel,
            "ts": ts,
            "text": text
        }

        if blocks:
            data["blocks"] = blocks

        result = await self._make_request("chat.update", data)
        return result and result.get("ok", False)

    async def add_reaction(
        self,
        channel: str,
        ts: str,
        emoji: str
    ) -> bool:
        """Add a reaction to a message."""
        result = await self._make_request("reactions.add", {
            "channel": channel,
            "timestamp": ts,
            "name": emoji
        })
        return result and result.get("ok", False)


# Register the integration
from integrations import registry

registry.register_provider("slack", SlackIntegration)
