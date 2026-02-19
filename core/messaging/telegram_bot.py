"""
BAEL Telegram Bot Integration
==============================

Telegram bot for BAEL communication and control.
Enables remote interaction with BAEL via Telegram.

Features:
- Message sending/receiving
- Command handling
- Inline keyboards
- File sharing
- Group management
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Telegram message types."""
    TEXT = "text"
    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"
    VOICE = "voice"
    STICKER = "sticker"
    LOCATION = "location"


class ChatType(Enum):
    """Telegram chat types."""
    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"


@dataclass
class TelegramUser:
    """Telegram user."""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    is_bot: bool = False


@dataclass
class TelegramChat:
    """Telegram chat."""
    id: int
    chat_type: ChatType = ChatType.PRIVATE
    title: Optional[str] = None
    username: Optional[str] = None


@dataclass
class TelegramMessage:
    """Telegram message."""
    message_id: int
    chat: TelegramChat

    # Content
    text: str = ""
    message_type: MessageType = MessageType.TEXT

    # Sender
    from_user: Optional[TelegramUser] = None

    # Reply
    reply_to_message: Optional["TelegramMessage"] = None

    # Attachments
    photo: Optional[str] = None
    document: Optional[str] = None

    # Metadata
    date: datetime = field(default_factory=datetime.now)


@dataclass
class InlineButton:
    """Inline keyboard button."""
    text: str
    callback_data: Optional[str] = None
    url: Optional[str] = None


@dataclass
class InlineKeyboard:
    """Inline keyboard."""
    buttons: List[List[InlineButton]] = field(default_factory=list)

    def add_row(self, *buttons: InlineButton) -> None:
        """Add a row of buttons."""
        self.buttons.append(list(buttons))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API format."""
        return {
            "inline_keyboard": [
                [
                    {
                        "text": btn.text,
                        **({"callback_data": btn.callback_data} if btn.callback_data else {}),
                        **({"url": btn.url} if btn.url else {}),
                    }
                    for btn in row
                ]
                for row in self.buttons
            ]
        }


@dataclass
class TelegramConfig:
    """Telegram bot configuration."""
    token: str

    # Behavior
    parse_mode: str = "HTML"
    disable_notifications: bool = False

    # Polling
    poll_timeout: int = 30
    poll_limit: int = 100

    # Allowed users (empty = all)
    allowed_users: List[int] = field(default_factory=list)


class TelegramBot:
    """
    Telegram bot for BAEL.

    Provides messaging and control via Telegram.
    """

    def __init__(self, config: TelegramConfig):
        self.config = config

        # Command handlers
        self._command_handlers: Dict[str, Callable] = {}

        # Message handlers
        self._message_handlers: List[Callable] = []

        # Callback query handlers
        self._callback_handlers: Dict[str, Callable] = {}

        # State
        self._running = False
        self._offset = 0

        # Stats
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "commands_processed": 0,
        }

        # Register default commands
        self._register_default_commands()

    def _register_default_commands(self) -> None:
        """Register default command handlers."""
        @self.command("start")
        async def start_handler(message: TelegramMessage) -> str:
            return (
                "🔥 <b>BAEL - The Lord of All AI</b>\n\n"
                "Welcome! I am your AI agent interface.\n\n"
                "Commands:\n"
                "/status - System status\n"
                "/help - Show help\n"
                "/task - Create new task\n"
            )

        @self.command("help")
        async def help_handler(message: TelegramMessage) -> str:
            return (
                "📖 <b>BAEL Commands</b>\n\n"
                "/start - Initialize bot\n"
                "/status - Check system status\n"
                "/task <description> - Create task\n"
                "/agents - List active agents\n"
                "/stop - Stop current task\n"
            )

        @self.command("status")
        async def status_handler(message: TelegramMessage) -> str:
            return (
                "📊 <b>BAEL Status</b>\n\n"
                f"✅ System: Online\n"
                f"📨 Messages: {self.stats['messages_received']}\n"
                f"⚡ Commands: {self.stats['commands_processed']}\n"
            )

    def command(self, name: str):
        """Decorator to register command handler."""
        def decorator(func: Callable):
            self._command_handlers[name.lower()] = func
            return func
        return decorator

    def message_handler(self, func: Callable):
        """Decorator to register message handler."""
        self._message_handlers.append(func)
        return func

    def callback_handler(self, pattern: str):
        """Decorator to register callback handler."""
        def decorator(func: Callable):
            self._callback_handlers[pattern] = func
            return func
        return decorator

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_to: Optional[int] = None,
        keyboard: Optional[InlineKeyboard] = None,
    ) -> Optional[TelegramMessage]:
        """
        Send a message.

        Args:
            chat_id: Target chat ID
            text: Message text
            reply_to: Message to reply to
            keyboard: Inline keyboard

        Returns:
            Sent message
        """
        self.stats["messages_sent"] += 1

        # Build API payload
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": self.config.parse_mode,
            "disable_notification": self.config.disable_notifications,
        }

        if reply_to:
            payload["reply_to_message_id"] = reply_to

        if keyboard:
            payload["reply_markup"] = json.dumps(keyboard.to_dict())

        # In production, would make actual API call
        logger.info(f"[TELEGRAM] Sending to {chat_id}: {text[:50]}...")

        # Simulate response
        return TelegramMessage(
            message_id=self.stats["messages_sent"],
            chat=TelegramChat(id=chat_id),
            text=text,
        )

    async def send_photo(
        self,
        chat_id: int,
        photo: str,
        caption: str = "",
    ) -> Optional[TelegramMessage]:
        """Send a photo."""
        self.stats["messages_sent"] += 1

        logger.info(f"[TELEGRAM] Sending photo to {chat_id}")

        return TelegramMessage(
            message_id=self.stats["messages_sent"],
            chat=TelegramChat(id=chat_id),
            text=caption,
            message_type=MessageType.PHOTO,
            photo=photo,
        )

    async def send_document(
        self,
        chat_id: int,
        document: str,
        caption: str = "",
    ) -> Optional[TelegramMessage]:
        """Send a document."""
        self.stats["messages_sent"] += 1

        logger.info(f"[TELEGRAM] Sending document to {chat_id}")

        return TelegramMessage(
            message_id=self.stats["messages_sent"],
            chat=TelegramChat(id=chat_id),
            text=caption,
            message_type=MessageType.DOCUMENT,
            document=document,
        )

    async def edit_message(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        keyboard: Optional[InlineKeyboard] = None,
    ) -> bool:
        """Edit a message."""
        logger.info(f"[TELEGRAM] Editing message {message_id} in {chat_id}")
        return True

    async def delete_message(
        self,
        chat_id: int,
        message_id: int,
    ) -> bool:
        """Delete a message."""
        logger.info(f"[TELEGRAM] Deleting message {message_id} in {chat_id}")
        return True

    async def _process_message(self, message: TelegramMessage) -> None:
        """Process incoming message."""
        self.stats["messages_received"] += 1

        # Check authorization
        if self.config.allowed_users:
            if message.from_user and message.from_user.id not in self.config.allowed_users:
                logger.warning(f"Unauthorized user: {message.from_user.id}")
                return

        text = message.text.strip()

        # Check for commands
        if text.startswith("/"):
            await self._process_command(message)
        else:
            # Process with message handlers
            for handler in self._message_handlers:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(f"Message handler error: {e}")

    async def _process_command(self, message: TelegramMessage) -> None:
        """Process command message."""
        self.stats["commands_processed"] += 1

        text = message.text.strip()
        parts = text.split(maxsplit=1)

        command = parts[0][1:].lower()  # Remove /
        if "@" in command:
            command = command.split("@")[0]

        args = parts[1] if len(parts) > 1 else ""

        if command in self._command_handlers:
            try:
                handler = self._command_handlers[command]
                response = await handler(message)

                if response:
                    await self.send_message(message.chat.id, response)
            except Exception as e:
                logger.error(f"Command error: {e}")
                await self.send_message(
                    message.chat.id,
                    f"❌ Error: {str(e)[:100]}"
                )

    async def _process_callback(
        self,
        callback_id: str,
        data: str,
        message: TelegramMessage,
    ) -> None:
        """Process callback query."""
        for pattern, handler in self._callback_handlers.items():
            if data.startswith(pattern):
                try:
                    await handler(callback_id, data, message)
                except Exception as e:
                    logger.error(f"Callback error: {e}")

    async def start_polling(self) -> None:
        """Start polling for updates."""
        self._running = True
        logger.info("Telegram bot polling started")

        while self._running:
            try:
                # In production, would poll Telegram API
                await asyncio.sleep(self.config.poll_timeout)
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(5)

    def stop_polling(self) -> None:
        """Stop polling."""
        self._running = False
        logger.info("Telegram bot polling stopped")

    def create_keyboard(
        self,
        buttons: List[List[tuple]],
    ) -> InlineKeyboard:
        """
        Create inline keyboard.

        Args:
            buttons: List of rows, each row is list of (text, callback_data) tuples

        Returns:
            InlineKeyboard
        """
        keyboard = InlineKeyboard()

        for row in buttons:
            row_buttons = []
            for text, data in row:
                row_buttons.append(InlineButton(text=text, callback_data=data))
            keyboard.buttons.append(row_buttons)

        return keyboard

    def get_stats(self) -> Dict[str, Any]:
        """Get bot statistics."""
        return {
            **self.stats,
            "running": self._running,
            "commands_registered": len(self._command_handlers),
        }


def demo():
    """Demonstrate Telegram bot."""
    import asyncio

    print("=" * 60)
    print("BAEL Telegram Bot Demo")
    print("=" * 60)

    config = TelegramConfig(
        token="YOUR_BOT_TOKEN",
    )

    bot = TelegramBot(config)

    # Register custom command
    @bot.command("task")
    async def task_handler(message: TelegramMessage) -> str:
        return "📋 Task created! I'll work on it."

    # Register message handler
    @bot.message_handler
    async def echo_handler(message: TelegramMessage) -> None:
        await bot.send_message(
            message.chat.id,
            f"You said: {message.text}"
        )

    # Simulate messages
    async def simulate():
        # Simulate /start command
        msg = TelegramMessage(
            message_id=1,
            chat=TelegramChat(id=12345),
            text="/start",
            from_user=TelegramUser(id=12345, first_name="User"),
        )

        await bot._process_message(msg)

        # Simulate /status command
        msg.text = "/status"
        msg.message_id = 2
        await bot._process_message(msg)

        # Send with keyboard
        keyboard = bot.create_keyboard([
            [("Option 1", "opt_1"), ("Option 2", "opt_2")],
            [("Cancel", "cancel")],
        ])

        await bot.send_message(
            12345,
            "Choose an option:",
            keyboard=keyboard,
        )

    asyncio.run(simulate())

    print(f"\nStats: {bot.get_stats()}")


if __name__ == "__main__":
    demo()
