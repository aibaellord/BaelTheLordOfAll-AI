"""
BAEL Voice Commands
====================

Voice command parsing, matching, and execution.
Natural language command interface for BAEL.

Features:
- Intent recognition
- Slot/parameter extraction
- Fuzzy matching
- Command aliases
- Context awareness
- Command chaining
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Pattern, Tuple

logger = logging.getLogger(__name__)


class CommandPriority(Enum):
    """Command priority levels."""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 100


@dataclass
class CommandSlot:
    """A parameter slot in a command."""
    name: str
    type: str = "string"  # string, number, boolean, list
    required: bool = True
    default: Any = None
    choices: List[Any] = field(default_factory=list)
    description: str = ""

    def validate(self, value: Any) -> Tuple[bool, Any]:
        """Validate and convert slot value."""
        if value is None:
            if self.required:
                return False, None
            return True, self.default

        try:
            if self.type == "number":
                value = float(value)
            elif self.type == "integer":
                value = int(value)
            elif self.type == "boolean":
                value = str(value).lower() in ("true", "yes", "on", "1")

            if self.choices and value not in self.choices:
                return False, None

            return True, value
        except:
            return False, None


@dataclass
class CommandDefinition:
    """Definition of a voice command."""
    name: str
    patterns: List[str]  # Regex patterns or templates
    handler: Callable

    # Slots
    slots: List[CommandSlot] = field(default_factory=list)

    # Metadata
    description: str = ""
    examples: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)

    # Options
    priority: CommandPriority = CommandPriority.NORMAL
    requires_confirmation: bool = False
    enabled: bool = True

    # Compiled patterns
    _compiled_patterns: List[Pattern] = field(default_factory=list, init=False)

    def __post_init__(self):
        """Compile patterns."""
        self._compiled_patterns = []
        for pattern in self.patterns:
            # Convert template format to regex
            # {slot_name} -> (?P<slot_name>.+?)
            regex_pattern = pattern
            for slot in self.slots:
                regex_pattern = regex_pattern.replace(
                    f"{{{slot.name}}}",
                    f"(?P<{slot.name}>.+?)",
                )

            # Make it case insensitive and match whole string
            self._compiled_patterns.append(
                re.compile(f"^{regex_pattern}$", re.IGNORECASE)
            )


@dataclass
class CommandResult:
    """Result of command execution."""
    success: bool
    command_name: Optional[str] = None
    message: str = ""
    data: Any = None

    # Metadata
    execution_time_ms: float = 0.0
    needs_confirmation: bool = False
    follow_up_prompt: Optional[str] = None


class CommandRegistry:
    """Registry of voice commands."""

    def __init__(self):
        self.commands: Dict[str, CommandDefinition] = {}
        self._alias_map: Dict[str, str] = {}

    def register(
        self,
        command: CommandDefinition,
    ) -> None:
        """Register a command."""
        self.commands[command.name] = command

        for alias in command.aliases:
            self._alias_map[alias.lower()] = command.name

    def unregister(self, name: str) -> bool:
        """Unregister a command."""
        if name in self.commands:
            command = self.commands.pop(name)
            for alias in command.aliases:
                self._alias_map.pop(alias.lower(), None)
            return True
        return False

    def get(self, name: str) -> Optional[CommandDefinition]:
        """Get a command by name or alias."""
        if name in self.commands:
            return self.commands[name]

        actual_name = self._alias_map.get(name.lower())
        if actual_name:
            return self.commands.get(actual_name)

        return None

    def list_all(self) -> List[CommandDefinition]:
        """List all registered commands."""
        return list(self.commands.values())


class VoiceCommandHandler:
    """
    Voice command parsing and execution for BAEL.
    """

    def __init__(self):
        self.registry = CommandRegistry()

        # Context for follow-up commands
        self.context: Dict[str, Any] = {}
        self.last_command: Optional[str] = None

        # Stats
        self.stats = {
            "commands_processed": 0,
            "successful_commands": 0,
            "failed_matches": 0,
        }

        # Register built-in commands
        self._register_builtin_commands()

    def _register_builtin_commands(self) -> None:
        """Register built-in voice commands."""

        # Help command
        self.registry.register(CommandDefinition(
            name="help",
            patterns=[
                r"help",
                r"what can you do",
                r"show commands",
                r"list commands",
            ],
            handler=self._cmd_help,
            description="Show available commands",
            examples=["help", "what can you do"],
            aliases=["?", "commands"],
        ))

        # Cancel command
        self.registry.register(CommandDefinition(
            name="cancel",
            patterns=[
                r"cancel",
                r"stop",
                r"nevermind",
                r"abort",
            ],
            handler=self._cmd_cancel,
            description="Cancel current operation",
            priority=CommandPriority.HIGH,
        ))

        # Confirm command
        self.registry.register(CommandDefinition(
            name="confirm",
            patterns=[
                r"yes",
                r"confirm",
                r"do it",
                r"proceed",
                r"ok",
                r"okay",
            ],
            handler=self._cmd_confirm,
            description="Confirm pending action",
            priority=CommandPriority.HIGH,
        ))

    def register_command(
        self,
        name: str,
        patterns: List[str],
        handler: Callable,
        **kwargs,
    ) -> None:
        """Register a new command."""
        command = CommandDefinition(
            name=name,
            patterns=patterns,
            handler=handler,
            **kwargs,
        )
        self.registry.register(command)

    def match_command(
        self,
        text: str,
    ) -> Tuple[Optional[CommandDefinition], Dict[str, Any]]:
        """
        Match text to a command.

        Args:
            text: Input text

        Returns:
            Tuple of (matched command, extracted slots)
        """
        text = text.strip()
        best_match = None
        best_slots = {}
        best_priority = CommandPriority.LOW

        for command in self.registry.list_all():
            if not command.enabled:
                continue

            for pattern in command._compiled_patterns:
                match = pattern.match(text)
                if match:
                    if command.priority.value > best_priority.value:
                        best_match = command
                        best_slots = match.groupdict()
                        best_priority = command.priority

        # Try fuzzy matching if no exact match
        if not best_match:
            best_match, best_slots = self._fuzzy_match(text)

        return best_match, best_slots

    def _fuzzy_match(
        self,
        text: str,
    ) -> Tuple[Optional[CommandDefinition], Dict[str, Any]]:
        """Fuzzy match for approximate commands."""
        text_lower = text.lower()
        words = set(text_lower.split())

        best_match = None
        best_score = 0.0

        for command in self.registry.list_all():
            if not command.enabled:
                continue

            # Check command name and aliases
            names = [command.name.lower()] + [a.lower() for a in command.aliases]

            for name in names:
                name_words = set(name.split())

                # Calculate word overlap
                overlap = len(words & name_words)
                total = len(words | name_words)

                if total > 0:
                    score = overlap / total
                    if score > best_score and score >= 0.5:
                        best_match = command
                        best_score = score

        return best_match, {}

    async def process(
        self,
        text: str,
    ) -> CommandResult:
        """
        Process voice command text.

        Args:
            text: Voice command text

        Returns:
            CommandResult
        """
        import time

        self.stats["commands_processed"] += 1
        start_time = time.monotonic()

        # Match command
        command, slots = self.match_command(text)

        if not command:
            self.stats["failed_matches"] += 1
            return CommandResult(
                success=False,
                message="I didn't understand that command. Say 'help' for available commands.",
            )

        # Validate slots
        validated_slots = {}
        for slot in command.slots:
            raw_value = slots.get(slot.name)
            is_valid, value = slot.validate(raw_value)

            if not is_valid and slot.required:
                return CommandResult(
                    success=False,
                    command_name=command.name,
                    message=f"Missing required parameter: {slot.name}",
                    follow_up_prompt=f"Please provide {slot.description or slot.name}:",
                )

            validated_slots[slot.name] = value

        # Check confirmation
        if command.requires_confirmation:
            self.context["pending_command"] = command
            self.context["pending_slots"] = validated_slots

            return CommandResult(
                success=True,
                command_name=command.name,
                message=f"Confirm: Execute '{command.name}'?",
                needs_confirmation=True,
            )

        # Execute command
        try:
            result = await self._execute_command(command, validated_slots)
            self.stats["successful_commands"] += 1
            self.last_command = command.name

            elapsed = (time.monotonic() - start_time) * 1000
            result.execution_time_ms = elapsed

            return result

        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return CommandResult(
                success=False,
                command_name=command.name,
                message=f"Error executing command: {e}",
            )

    async def _execute_command(
        self,
        command: CommandDefinition,
        slots: Dict[str, Any],
    ) -> CommandResult:
        """Execute a command."""
        import asyncio

        if asyncio.iscoroutinefunction(command.handler):
            result = await command.handler(self, **slots)
        else:
            result = command.handler(self, **slots)

        if isinstance(result, CommandResult):
            result.command_name = command.name
            return result
        elif isinstance(result, str):
            return CommandResult(
                success=True,
                command_name=command.name,
                message=result,
            )
        else:
            return CommandResult(
                success=True,
                command_name=command.name,
                data=result,
            )

    # Built-in command handlers

    def _cmd_help(self, handler, **kwargs) -> CommandResult:
        """Show help for available commands."""
        commands = self.registry.list_all()
        enabled = [c for c in commands if c.enabled]

        help_text = "Available commands:\n"
        for cmd in sorted(enabled, key=lambda c: c.name):
            help_text += f"  • {cmd.name}: {cmd.description}\n"
            if cmd.examples:
                help_text += f"    Example: '{cmd.examples[0]}'\n"

        return CommandResult(
            success=True,
            message=help_text,
            data={"commands": [c.name for c in enabled]},
        )

    def _cmd_cancel(self, handler, **kwargs) -> CommandResult:
        """Cancel pending operation."""
        if "pending_command" in self.context:
            cmd_name = self.context.pop("pending_command").name
            self.context.pop("pending_slots", None)
            return CommandResult(
                success=True,
                message=f"Cancelled '{cmd_name}'",
            )

        return CommandResult(
            success=True,
            message="Nothing to cancel",
        )

    async def _cmd_confirm(self, handler, **kwargs) -> CommandResult:
        """Confirm pending command."""
        if "pending_command" not in self.context:
            return CommandResult(
                success=False,
                message="Nothing to confirm",
            )

        command = self.context.pop("pending_command")
        slots = self.context.pop("pending_slots", {})

        return await self._execute_command(command, slots)

    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics."""
        return {
            **self.stats,
            "registered_commands": len(self.registry.commands),
            "last_command": self.last_command,
        }


def demo():
    """Demonstrate voice commands."""
    print("=" * 60)
    print("BAEL Voice Commands Demo")
    print("=" * 60)

    handler = VoiceCommandHandler()

    # Register a custom command
    handler.register_command(
        name="search",
        patterns=[
            r"search for {query}",
            r"find {query}",
            r"look up {query}",
        ],
        handler=lambda h, query: f"Searching for: {query}",
        slots=[
            CommandSlot(name="query", description="Search query"),
        ],
        description="Search for information",
        examples=["search for weather"],
    )

    print(f"\nRegistered commands: {len(handler.registry.commands)}")

    # Test matching
    test_inputs = [
        "help",
        "search for python tutorials",
        "what can you do",
    ]

    print("\nCommand matching:")
    for text in test_inputs:
        cmd, slots = handler.match_command(text)
        if cmd:
            print(f"  '{text}' -> {cmd.name} (slots: {slots})")
        else:
            print(f"  '{text}' -> No match")

    print(f"\nStats: {handler.get_stats()}")


if __name__ == "__main__":
    demo()
