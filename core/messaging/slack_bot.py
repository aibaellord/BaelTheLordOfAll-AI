"""
BAEL Slack Bot Integration
===========================

Slack bot for BAEL communication and control.
Enables enterprise communication via Slack.

Features:
- Message handling
- Slash commands
- Block Kit UI
- Workflow automation
- App mentions
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SlackBlockType(Enum):
    """Slack block types."""
    SECTION = "section"
    DIVIDER = "divider"
    ACTIONS = "actions"
    CONTEXT = "context"
    HEADER = "header"
    IMAGE = "image"


@dataclass
class SlackUser:
    """Slack user."""
    id: str
    name: str
    real_name: str = ""
    email: str = ""
    is_bot: bool = False


@dataclass
class SlackChannel:
    """Slack channel."""
    id: str
    name: str
    is_private: bool = False
    is_im: bool = False


@dataclass
class SlackBlock:
    """Slack block element."""
    block_type: SlackBlockType

    # Content
    text: str = ""
    fields: List[str] = field(default_factory=list)
    accessory: Optional[Dict[str, Any]] = None

    # Actions
    elements: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API format."""
        block = {"type": self.block_type.value}

        if self.block_type == SlackBlockType.SECTION:
            if self.text:
                block["text"] = {
                    "type": "mrkdwn",
                    "text": self.text,
                }
            if self.fields:
                block["fields"] = [
                    {"type": "mrkdwn", "text": f} for f in self.fields
                ]
            if self.accessory:
                block["accessory"] = self.accessory

        elif self.block_type == SlackBlockType.HEADER:
            block["text"] = {
                "type": "plain_text",
                "text": self.text,
            }

        elif self.block_type == SlackBlockType.ACTIONS:
            block["elements"] = self.elements

        elif self.block_type == SlackBlockType.CONTEXT:
            block["elements"] = [
                {"type": "mrkdwn", "text": self.text}
            ] if self.text else self.elements

        return block


@dataclass
class SlackMessage:
    """Slack message."""
    ts: str  # Message timestamp (ID)
    channel: SlackChannel

    # Content
    text: str = ""
    blocks: List[SlackBlock] = field(default_factory=list)
    attachments: List[Dict] = field(default_factory=list)

    # Author
    user: Optional[SlackUser] = None

    # Thread
    thread_ts: Optional[str] = None

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SlackConfig:
    """Slack bot configuration."""
    # Tokens
    bot_token: str
    app_token: str = ""
    signing_secret: str = ""

    # Settings
    default_channel: str = ""

    # Socket mode
    socket_mode: bool = True


class SlackBot:
    """
    Slack bot for BAEL.

    Provides messaging and control via Slack.
    """

    def __init__(self, config: SlackConfig):
        self.config = config

        # Command handlers
        self._command_handlers: Dict[str, Callable] = {}

        # Event handlers
        self._event_handlers: Dict[str, List[Callable]] = {}

        # Action handlers (button clicks, etc.)
        self._action_handlers: Dict[str, Callable] = {}

        # State
        self._running = False

        # Stats
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "commands_processed": 0,
        }

        # Register defaults
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default handlers."""
        @self.command("/bael")
        async def bael_slash(channel: str, user: str, text: str) -> List[SlackBlock]:
            return [
                SlackBlock(
                    block_type=SlackBlockType.HEADER,
                    text="🔥 BAEL - The Lord of All AI",
                ),
                SlackBlock(
                    block_type=SlackBlockType.SECTION,
                    text="Welcome! I am your AI agent interface.",
                ),
                SlackBlock(
                    block_type=SlackBlockType.SECTION,
                    fields=[
                        "*Status:* Online",
                        "*Version:* 3.0",
                    ],
                ),
            ]

        @self.command("/status")
        async def status_slash(channel: str, user: str, text: str) -> List[SlackBlock]:
            return [
                SlackBlock(
                    block_type=SlackBlockType.HEADER,
                    text="📊 BAEL Status",
                ),
                SlackBlock(
                    block_type=SlackBlockType.SECTION,
                    fields=[
                        f"*Messages:* {self.stats['messages_received']}",
                        f"*Commands:* {self.stats['commands_processed']}",
                    ],
                ),
            ]

    def command(self, command: str):
        """Decorator to register slash command handler."""
        def decorator(func: Callable):
            self._command_handlers[command] = func
            return func
        return decorator

    def event(self, event_type: str):
        """Decorator to register event handler."""
        def decorator(func: Callable):
            if event_type not in self._event_handlers:
                self._event_handlers[event_type] = []
            self._event_handlers[event_type].append(func)
            return func
        return decorator

    def action(self, action_id: str):
        """Decorator to register action handler."""
        def decorator(func: Callable):
            self._action_handlers[action_id] = func
            return func
        return decorator

    async def send_message(
        self,
        channel: str,
        text: str = "",
        blocks: Optional[List[SlackBlock]] = None,
        thread_ts: Optional[str] = None,
    ) -> Optional[SlackMessage]:
        """
        Send a message.

        Args:
            channel: Channel ID
            text: Fallback text
            blocks: Block Kit blocks
            thread_ts: Thread timestamp for replies

        Returns:
            Sent message
        """
        self.stats["messages_sent"] += 1

        logger.info(f"[SLACK] Sending to {channel}: {text[:50] if text else 'blocks'}...")

        ts = f"{datetime.now().timestamp()}"

        return SlackMessage(
            ts=ts,
            channel=SlackChannel(id=channel, name="channel"),
            text=text,
            blocks=blocks or [],
            thread_ts=thread_ts,
        )

    async def send_blocks(
        self,
        channel: str,
        blocks: List[SlackBlock],
        text: str = "Message from BAEL",
    ) -> Optional[SlackMessage]:
        """Send block message."""
        return await self.send_message(channel, text=text, blocks=blocks)

    async def update_message(
        self,
        channel: str,
        ts: str,
        text: str = "",
        blocks: Optional[List[SlackBlock]] = None,
    ) -> bool:
        """Update a message."""
        logger.info(f"[SLACK] Updating {ts} in {channel}")
        return True

    async def delete_message(
        self,
        channel: str,
        ts: str,
    ) -> bool:
        """Delete a message."""
        logger.info(f"[SLACK] Deleting {ts} in {channel}")
        return True

    async def add_reaction(
        self,
        channel: str,
        ts: str,
        emoji: str,
    ) -> bool:
        """Add reaction to message."""
        logger.info(f"[SLACK] Adding :{emoji}: to {ts}")
        return True

    async def _process_message(self, message: SlackMessage) -> None:
        """Process incoming message."""
        self.stats["messages_received"] += 1

        # Ignore bots
        if message.user and message.user.is_bot:
            return

        # Check for app mentions
        if "<@" in message.text:
            await self._emit_event("app_mention", message)

        # Emit message event
        await self._emit_event("message", message)

    async def _process_slash_command(
        self,
        command: str,
        channel: str,
        user: str,
        text: str,
    ) -> Optional[List[SlackBlock]]:
        """Process slash command."""
        self.stats["commands_processed"] += 1

        if command in self._command_handlers:
            try:
                handler = self._command_handlers[command]
                return await handler(channel, user, text)
            except Exception as e:
                logger.error(f"Slash command error: {e}")
                return [
                    SlackBlock(
                        block_type=SlackBlockType.SECTION,
                        text=f"❌ Error: {str(e)[:100]}",
                    )
                ]

        return None

    async def _process_action(
        self,
        action_id: str,
        payload: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Process block action."""
        if action_id in self._action_handlers:
            try:
                handler = self._action_handlers[action_id]
                return await handler(payload)
            except Exception as e:
                logger.error(f"Action handler error: {e}")

        return None

    async def _emit_event(self, event_type: str, *args: Any) -> None:
        """Emit event to handlers."""
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    await handler(*args)
                except Exception as e:
                    logger.error(f"Event handler error: {e}")

    async def start(self) -> None:
        """Start the bot."""
        self._running = True
        logger.info("Slack bot started")

        await self._emit_event("app_home_opened", None)

        while self._running:
            await asyncio.sleep(1)

    def stop(self) -> None:
        """Stop the bot."""
        self._running = False
        logger.info("Slack bot stopped")

    def create_button(
        self,
        text: str,
        action_id: str,
        value: str = "",
        style: str = "primary",
    ) -> Dict[str, Any]:
        """Create a button element."""
        return {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": text,
            },
            "action_id": action_id,
            "value": value,
            "style": style,
        }

    def create_select(
        self,
        placeholder: str,
        action_id: str,
        options: List[tuple],
    ) -> Dict[str, Any]:
        """Create a select menu."""
        return {
            "type": "static_select",
            "placeholder": {
                "type": "plain_text",
                "text": placeholder,
            },
            "action_id": action_id,
            "options": [
                {
                    "text": {"type": "plain_text", "text": text},
                    "value": value,
                }
                for text, value in options
            ],
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get bot statistics."""
        return {
            **self.stats,
            "running": self._running,
            "commands_registered": len(self._command_handlers),
        }


def demo():
    """Demonstrate Slack bot."""
    import asyncio

    print("=" * 60)
    print("BAEL Slack Bot Demo")
    print("=" * 60)

    config = SlackConfig(
        bot_token="xoxb-YOUR-TOKEN",
        app_token="xapp-YOUR-TOKEN",
    )

    bot = SlackBot(config)

    # Register custom command
    @bot.command("/task")
    async def task_slash(channel: str, user: str, text: str) -> List[SlackBlock]:
        return [
            SlackBlock(
                block_type=SlackBlockType.HEADER,
                text="📋 New Task Created",
            ),
            SlackBlock(
                block_type=SlackBlockType.SECTION,
                text=text or "No description",
            ),
            SlackBlock(
                block_type=SlackBlockType.ACTIONS,
                elements=[
                    bot.create_button("Start", "task_start", style="primary"),
                    bot.create_button("Cancel", "task_cancel", style="danger"),
                ],
            ),
        ]

    # Register action handler
    @bot.action("task_start")
    async def handle_start(payload: Dict) -> Dict:
        return {"text": "Task started!"}

    # Simulate
    async def simulate():
        # Simulate /bael command
        blocks = await bot._process_slash_command(
            "/bael", "C12345", "U12345", ""
        )

        if blocks:
            print(f"\n/bael response ({len(blocks)} blocks):")
            for block in blocks:
                print(f"  - {block.block_type.value}: {block.text[:40] if block.text else 'fields/elements'}")

        # Simulate /task command
        blocks = await bot._process_slash_command(
            "/task", "C12345", "U12345", "Implement new feature"
        )

        if blocks:
            print(f"\n/task response ({len(blocks)} blocks):")
            for block in blocks:
                print(f"  - {block.block_type.value}")

        # Send blocks
        await bot.send_blocks(
            "C12345",
            [
                SlackBlock(
                    block_type=SlackBlockType.SECTION,
                    text="*BAEL Alert:* Task completed successfully!",
                ),
            ],
        )

    asyncio.run(simulate())

    print(f"\nStats: {bot.get_stats()}")


if __name__ == "__main__":
    demo()
