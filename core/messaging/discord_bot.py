"""
BAEL Discord Bot Integration
=============================

Discord bot for BAEL communication and control.
Enables rich interaction via Discord servers.

Features:
- Message handling
- Slash commands
- Embeds and rich content
- Voice channel support
- Role management
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class DiscordMessageType(Enum):
    """Discord message types."""
    TEXT = "text"
    EMBED = "embed"
    FILE = "file"
    REPLY = "reply"


class ChannelType(Enum):
    """Discord channel types."""
    TEXT = "text"
    VOICE = "voice"
    DM = "dm"
    THREAD = "thread"


@dataclass
class DiscordUser:
    """Discord user."""
    id: int
    username: str
    discriminator: str = "0000"
    avatar: Optional[str] = None
    bot: bool = False

    @property
    def tag(self) -> str:
        """Get user tag."""
        return f"{self.username}#{self.discriminator}"


@dataclass
class DiscordGuild:
    """Discord guild (server)."""
    id: int
    name: str
    icon: Optional[str] = None
    owner_id: int = 0


@dataclass
class DiscordChannel:
    """Discord channel."""
    id: int
    name: str
    channel_type: ChannelType = ChannelType.TEXT
    guild_id: Optional[int] = None


@dataclass
class DiscordEmbed:
    """Discord embed."""
    title: str = ""
    description: str = ""
    color: int = 0x7289DA  # Discord blurple

    # Author
    author_name: str = ""
    author_icon: str = ""
    author_url: str = ""

    # Thumbnail and image
    thumbnail: str = ""
    image: str = ""

    # Fields
    fields: List[Dict[str, Any]] = field(default_factory=list)

    # Footer
    footer: str = ""
    footer_icon: str = ""

    # Timestamp
    timestamp: Optional[datetime] = None

    def add_field(
        self,
        name: str,
        value: str,
        inline: bool = False,
    ) -> "DiscordEmbed":
        """Add a field."""
        self.fields.append({
            "name": name,
            "value": value,
            "inline": inline,
        })
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API format."""
        embed = {}

        if self.title:
            embed["title"] = self.title
        if self.description:
            embed["description"] = self.description

        embed["color"] = self.color

        if self.author_name:
            embed["author"] = {
                "name": self.author_name,
                **({"icon_url": self.author_icon} if self.author_icon else {}),
                **({"url": self.author_url} if self.author_url else {}),
            }

        if self.thumbnail:
            embed["thumbnail"] = {"url": self.thumbnail}

        if self.image:
            embed["image"] = {"url": self.image}

        if self.fields:
            embed["fields"] = self.fields

        if self.footer:
            embed["footer"] = {
                "text": self.footer,
                **({"icon_url": self.footer_icon} if self.footer_icon else {}),
            }

        if self.timestamp:
            embed["timestamp"] = self.timestamp.isoformat()

        return embed


@dataclass
class DiscordMessage:
    """Discord message."""
    id: int
    channel: DiscordChannel

    # Content
    content: str = ""
    embeds: List[DiscordEmbed] = field(default_factory=list)

    # Author
    author: Optional[DiscordUser] = None

    # References
    guild: Optional[DiscordGuild] = None
    reference: Optional[int] = None  # Reply reference

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SlashCommand:
    """Slash command definition."""
    name: str
    description: str

    # Options
    options: List[Dict[str, Any]] = field(default_factory=list)

    # Handler
    handler: Optional[Callable] = None


@dataclass
class DiscordConfig:
    """Discord bot configuration."""
    token: str

    # Bot settings
    prefix: str = "!"
    activity: str = "BAEL - AI Agent"

    # Intents
    intents: List[str] = field(default_factory=lambda: [
        "guilds", "guild_messages", "direct_messages"
    ])

    # Allowed guilds (empty = all)
    allowed_guilds: List[int] = field(default_factory=list)


class DiscordBot:
    """
    Discord bot for BAEL.

    Provides messaging and control via Discord.
    """

    def __init__(self, config: DiscordConfig):
        self.config = config

        # Command handlers
        self._command_handlers: Dict[str, Callable] = {}

        # Slash commands
        self._slash_commands: Dict[str, SlashCommand] = {}

        # Event handlers
        self._event_handlers: Dict[str, List[Callable]] = {}

        # State
        self._running = False
        self._guilds: Dict[int, DiscordGuild] = {}

        # Stats
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "commands_processed": 0,
        }

        # Register defaults
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default commands."""
        @self.command("bael")
        async def bael_command(message: DiscordMessage, args: str) -> str:
            return "🔥 **BAEL - The Lord of All AI** is online and ready!"

        @self.command("status")
        async def status_command(message: DiscordMessage, args: str) -> DiscordEmbed:
            return DiscordEmbed(
                title="📊 BAEL Status",
                description="System is operational",
                color=0x00FF00,
            ).add_field(
                "Messages", str(self.stats["messages_received"]), inline=True
            ).add_field(
                "Commands", str(self.stats["commands_processed"]), inline=True
            )

        @self.command("help")
        async def help_command(message: DiscordMessage, args: str) -> DiscordEmbed:
            return DiscordEmbed(
                title="📖 BAEL Commands",
                description="Available commands:",
                color=0x7289DA,
            ).add_field(
                f"{self.config.prefix}bael", "Show welcome message"
            ).add_field(
                f"{self.config.prefix}status", "Check system status"
            ).add_field(
                f"{self.config.prefix}task <desc>", "Create a new task"
            )

    def command(self, name: str):
        """Decorator to register command handler."""
        def decorator(func: Callable):
            self._command_handlers[name.lower()] = func
            return func
        return decorator

    def slash_command(
        self,
        name: str,
        description: str,
        options: Optional[List[Dict]] = None,
    ):
        """Decorator to register slash command."""
        def decorator(func: Callable):
            self._slash_commands[name] = SlashCommand(
                name=name,
                description=description,
                options=options or [],
                handler=func,
            )
            return func
        return decorator

    def event(self, event_name: str):
        """Decorator to register event handler."""
        def decorator(func: Callable):
            if event_name not in self._event_handlers:
                self._event_handlers[event_name] = []
            self._event_handlers[event_name].append(func)
            return func
        return decorator

    async def send_message(
        self,
        channel_id: int,
        content: str = "",
        embed: Optional[DiscordEmbed] = None,
        reply_to: Optional[int] = None,
    ) -> Optional[DiscordMessage]:
        """
        Send a message.

        Args:
            channel_id: Target channel
            content: Message content
            embed: Optional embed
            reply_to: Message to reply to

        Returns:
            Sent message
        """
        self.stats["messages_sent"] += 1

        logger.info(f"[DISCORD] Sending to {channel_id}: {content[:50] if content else 'embed'}...")

        return DiscordMessage(
            id=self.stats["messages_sent"],
            channel=DiscordChannel(id=channel_id, name="channel"),
            content=content,
            embeds=[embed] if embed else [],
        )

    async def send_embed(
        self,
        channel_id: int,
        embed: DiscordEmbed,
    ) -> Optional[DiscordMessage]:
        """Send an embed message."""
        return await self.send_message(channel_id, embed=embed)

    async def edit_message(
        self,
        channel_id: int,
        message_id: int,
        content: str = "",
        embed: Optional[DiscordEmbed] = None,
    ) -> bool:
        """Edit a message."""
        logger.info(f"[DISCORD] Editing {message_id} in {channel_id}")
        return True

    async def delete_message(
        self,
        channel_id: int,
        message_id: int,
    ) -> bool:
        """Delete a message."""
        logger.info(f"[DISCORD] Deleting {message_id} in {channel_id}")
        return True

    async def add_reaction(
        self,
        channel_id: int,
        message_id: int,
        emoji: str,
    ) -> bool:
        """Add reaction to message."""
        logger.info(f"[DISCORD] Adding {emoji} to {message_id}")
        return True

    async def _process_message(self, message: DiscordMessage) -> None:
        """Process incoming message."""
        self.stats["messages_received"] += 1

        # Ignore bots
        if message.author and message.author.bot:
            return

        content = message.content.strip()

        # Check for prefix commands
        if content.startswith(self.config.prefix):
            await self._process_command(message)

        # Trigger message events
        await self._emit_event("message", message)

    async def _process_command(self, message: DiscordMessage) -> None:
        """Process command message."""
        self.stats["commands_processed"] += 1

        content = message.content.strip()
        content = content[len(self.config.prefix):]  # Remove prefix

        parts = content.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command in self._command_handlers:
            try:
                handler = self._command_handlers[command]
                response = await handler(message, args)

                if isinstance(response, str):
                    await self.send_message(message.channel.id, response)
                elif isinstance(response, DiscordEmbed):
                    await self.send_embed(message.channel.id, response)
            except Exception as e:
                logger.error(f"Command error: {e}")
                await self.send_message(
                    message.channel.id,
                    f"❌ Error: {str(e)[:100]}"
                )

    async def _emit_event(self, event_name: str, *args: Any) -> None:
        """Emit event to handlers."""
        if event_name in self._event_handlers:
            for handler in self._event_handlers[event_name]:
                try:
                    await handler(*args)
                except Exception as e:
                    logger.error(f"Event handler error: {e}")

    async def start(self) -> None:
        """Start the bot."""
        self._running = True
        logger.info("Discord bot started")

        await self._emit_event("ready")

        while self._running:
            await asyncio.sleep(1)

    def stop(self) -> None:
        """Stop the bot."""
        self._running = False
        logger.info("Discord bot stopped")

    def create_embed(
        self,
        title: str = "",
        description: str = "",
        color: int = 0x7289DA,
    ) -> DiscordEmbed:
        """Create an embed helper."""
        return DiscordEmbed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now(),
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get bot statistics."""
        return {
            **self.stats,
            "running": self._running,
            "commands_registered": len(self._command_handlers),
            "slash_commands": len(self._slash_commands),
        }


def demo():
    """Demonstrate Discord bot."""
    import asyncio

    print("=" * 60)
    print("BAEL Discord Bot Demo")
    print("=" * 60)

    config = DiscordConfig(
        token="YOUR_BOT_TOKEN",
        prefix="!",
    )

    bot = DiscordBot(config)

    # Register custom command
    @bot.command("task")
    async def task_command(message: DiscordMessage, args: str) -> DiscordEmbed:
        return bot.create_embed(
            title="📋 Task Created",
            description=args or "No description provided",
            color=0x00FF00,
        ).add_field("Status", "Pending", inline=True)

    # Register event
    @bot.event("ready")
    async def on_ready():
        print("Bot is ready!")

    # Simulate messages
    async def simulate():
        user = DiscordUser(id=12345, username="TestUser")
        channel = DiscordChannel(id=67890, name="general")

        # Simulate !bael command
        msg = DiscordMessage(
            id=1,
            channel=channel,
            content="!bael",
            author=user,
        )
        await bot._process_message(msg)

        # Simulate !status command
        msg.content = "!status"
        msg.id = 2
        await bot._process_message(msg)

        # Simulate !task command
        msg.content = "!task Implement new feature"
        msg.id = 3
        await bot._process_message(msg)

        # Send embed directly
        embed = bot.create_embed(
            title="🔥 BAEL Alert",
            description="Agent completed task successfully!",
            color=0xFF5500,
        )
        await bot.send_embed(channel.id, embed)

    asyncio.run(simulate())

    print(f"\nStats: {bot.get_stats()}")


if __name__ == "__main__":
    demo()
