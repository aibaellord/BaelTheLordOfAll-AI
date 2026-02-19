"""
BAEL - Ultra-Comfort Automation Layer
======================================

Zero-friction interface for maximum user comfort.

Features:
1. One-Word Commands - Single word triggers complex actions
2. Context-Aware Shortcuts - Smart command abbreviations
3. Predictive Completion - Auto-complete before typing
4. Gesture Recognition - Natural language shortcuts
5. Mood-Based Adaptation - Adjust to user's state
6. Smart Defaults - Intelligent default selections
7. Memory Macros - Remember and replay sequences
8. Voice Shortcuts - Natural speech commands
9. Ambient Intelligence - Background optimization
10. Frictionless Flow - Remove all obstacles

"The best UX is invisible - it just works."
"""

import asyncio
import hashlib
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("BAEL.COMFORT")


# ============================================================================
# ENUMS
# ============================================================================

class ComfortLevel(Enum):
    """User comfort levels."""
    MAXIMUM = "maximum"  # Zero friction
    HIGH = "high"  # Minimal interaction
    MODERATE = "moderate"  # Standard interaction
    DETAILED = "detailed"  # Full control
    EXPERT = "expert"  # All options exposed


class CommandType(Enum):
    """Types of comfort commands."""
    SINGLE_WORD = "single_word"
    ABBREVIATION = "abbreviation"
    GESTURE = "gesture"
    VOICE = "voice"
    SHORTCUT = "shortcut"
    MACRO = "macro"


class TriggerType(Enum):
    """Types of command triggers."""
    KEYWORD = "keyword"
    PATTERN = "pattern"
    CONTEXT = "context"
    TIME = "time"
    LOCATION = "location"
    EMOTION = "emotion"


class ExecutionMode(Enum):
    """How to execute commands."""
    IMMEDIATE = "immediate"  # No confirmation
    CONFIRM = "confirm"  # Ask first
    PREVIEW = "preview"  # Show what will happen
    UNDO_SAFE = "undo_safe"  # Can be undone


class AdaptationType(Enum):
    """Types of adaptation."""
    SPEED = "speed"  # Faster/slower
    VERBOSITY = "verbosity"  # More/less detail
    FORMALITY = "formality"  # Casual/formal
    COMPLEXITY = "complexity"  # Simple/advanced


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ComfortCommand:
    """A comfort command definition."""
    id: str
    trigger: str  # What activates it
    trigger_type: TriggerType
    command_type: CommandType
    action: str  # What it does
    description: str
    execution_mode: ExecutionMode = ExecutionMode.IMMEDIATE
    parameters: Dict[str, Any] = field(default_factory=dict)
    aliases: List[str] = field(default_factory=list)
    usage_count: int = 0
    last_used: Optional[datetime] = None
    context_requirements: Dict[str, Any] = field(default_factory=dict)

    def matches(self, input_text: str, context: Dict[str, Any] = None) -> float:
        """Check if input matches this command. Returns confidence 0-1."""
        input_lower = input_text.lower().strip()

        # Exact match
        if input_lower == self.trigger.lower():
            return 1.0

        # Alias match
        for alias in self.aliases:
            if input_lower == alias.lower():
                return 0.95

        # Prefix match
        if self.trigger.lower().startswith(input_lower):
            return 0.7 + (len(input_lower) / len(self.trigger)) * 0.2

        # Contains match
        if self.trigger_type == TriggerType.KEYWORD:
            if self.trigger.lower() in input_lower:
                return 0.5

        # Pattern match
        if self.trigger_type == TriggerType.PATTERN:
            if re.search(self.trigger, input_lower, re.IGNORECASE):
                return 0.8

        # Context match
        if context and self.context_requirements:
            matches = all(
                context.get(k) == v
                for k, v in self.context_requirements.items()
            )
            if matches:
                return 0.6

        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "trigger": self.trigger,
            "action": self.action,
            "description": self.description,
            "usage_count": self.usage_count
        }


@dataclass
class Macro:
    """A recorded macro of actions."""
    id: str
    name: str
    trigger: str
    actions: List[Dict[str, Any]]
    created_at: datetime
    usage_count: int = 0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "trigger": self.trigger,
            "action_count": len(self.actions),
            "usage_count": self.usage_count
        }


@dataclass
class SmartDefault:
    """A context-aware default value."""
    field_name: str
    value: Any
    context: Dict[str, Any]
    confidence: float
    source: str  # Where this default came from

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field_name,
            "value": str(self.value)[:50],
            "confidence": self.confidence,
            "source": self.source
        }


@dataclass
class UserPreferences:
    """User comfort preferences."""
    user_id: str
    comfort_level: ComfortLevel = ComfortLevel.HIGH
    verbosity: float = 0.5  # 0 = minimal, 1 = verbose
    speed: float = 0.7  # 0 = slow, 1 = fast
    formality: float = 0.5  # 0 = casual, 1 = formal
    auto_confirm: bool = True  # Auto-confirm low-risk actions
    predictive_enabled: bool = True
    custom_commands: List[ComfortCommand] = field(default_factory=list)
    macros: List[Macro] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """Result of executing a comfort command."""
    success: bool
    command_id: str
    action: str
    result: Any
    duration_ms: float
    message: str
    undoable: bool = False
    undo_action: Optional[str] = None


# ============================================================================
# ULTRA-COMFORT ENGINE
# ============================================================================

class UltraComfortEngine:
    """
    Zero-friction automation layer.

    Provides maximum comfort through:
    - Single-word commands
    - Context-aware shortcuts
    - Predictive completion
    - Smart defaults
    - Macro recording
    """

    def __init__(self):
        self.commands: Dict[str, ComfortCommand] = {}
        self.macros: Dict[str, Macro] = {}
        self.user_preferences: Dict[str, UserPreferences] = {}
        self.smart_defaults: Dict[str, List[SmartDefault]] = defaultdict(list)
        self.command_history: deque = deque(maxlen=1000)
        self.recording_macro: Optional[List[Dict[str, Any]]] = None

        # Action handlers
        self.action_handlers: Dict[str, Callable] = {}

        # Initialize built-in commands
        self._init_builtin_commands()

        logger.info("UltraComfortEngine initialized")

    def _init_builtin_commands(self) -> None:
        """Initialize built-in comfort commands."""
        builtin = [
            # Single-word commands
            ComfortCommand(
                id="help",
                trigger="help",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.SINGLE_WORD,
                action="show_help",
                description="Show available commands",
                aliases=["?", "h", "commands"]
            ),
            ComfortCommand(
                id="run",
                trigger="run",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.SINGLE_WORD,
                action="run_last_action",
                description="Run the last action again",
                aliases=["go", "do", "again"]
            ),
            ComfortCommand(
                id="undo",
                trigger="undo",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.SINGLE_WORD,
                action="undo_last",
                description="Undo the last action",
                aliases=["back", "revert", "z"]
            ),
            ComfortCommand(
                id="save",
                trigger="save",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.SINGLE_WORD,
                action="save_current",
                description="Save current work",
                aliases=["s", "store", "keep"]
            ),
            ComfortCommand(
                id="status",
                trigger="status",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.SINGLE_WORD,
                action="show_status",
                description="Show current status",
                aliases=["st", "state", "info"]
            ),
            ComfortCommand(
                id="clear",
                trigger="clear",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.SINGLE_WORD,
                action="clear_context",
                description="Clear current context",
                aliases=["cls", "reset", "fresh"]
            ),
            ComfortCommand(
                id="done",
                trigger="done",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.SINGLE_WORD,
                action="complete_task",
                description="Mark current task as done",
                aliases=["finish", "complete", "end"]
            ),
            ComfortCommand(
                id="next",
                trigger="next",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.SINGLE_WORD,
                action="next_item",
                description="Move to next item",
                aliases=["n", "forward", "continue"]
            ),
            ComfortCommand(
                id="back",
                trigger="back",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.SINGLE_WORD,
                action="previous_item",
                description="Go back to previous",
                aliases=["b", "prev", "previous"]
            ),
            ComfortCommand(
                id="skip",
                trigger="skip",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.SINGLE_WORD,
                action="skip_current",
                description="Skip current item",
                aliases=["pass", "ignore"]
            ),

            # Context-aware shortcuts
            ComfortCommand(
                id="yes",
                trigger="yes",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.SINGLE_WORD,
                action="confirm_action",
                description="Confirm/approve",
                aliases=["y", "ok", "sure", "yep", "yeah"]
            ),
            ComfortCommand(
                id="no",
                trigger="no",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.SINGLE_WORD,
                action="cancel_action",
                description="Cancel/reject",
                aliases=["n", "nope", "cancel", "abort"]
            ),

            # Power shortcuts
            ComfortCommand(
                id="all",
                trigger="all",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.SINGLE_WORD,
                action="select_all",
                description="Select all items",
                aliases=["everything", "every"]
            ),
            ComfortCommand(
                id="none",
                trigger="none",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.SINGLE_WORD,
                action="select_none",
                description="Deselect all",
                aliases=["nothing", "zero"]
            ),

            # Abbreviation commands
            ComfortCommand(
                id="q",
                trigger="q",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.ABBREVIATION,
                action="quick_action",
                description="Quick action menu"
            ),
            ComfortCommand(
                id="x",
                trigger="x",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.ABBREVIATION,
                action="execute",
                description="Execute command"
            ),
            ComfortCommand(
                id="f",
                trigger="f",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.ABBREVIATION,
                action="find",
                description="Find/search"
            ),
            ComfortCommand(
                id="r",
                trigger="r",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.ABBREVIATION,
                action="replace",
                description="Replace"
            ),
            ComfortCommand(
                id="c",
                trigger="c",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.ABBREVIATION,
                action="create",
                description="Create new"
            ),
            ComfortCommand(
                id="d",
                trigger="d",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.ABBREVIATION,
                action="delete",
                description="Delete"
            ),
            ComfortCommand(
                id="e",
                trigger="e",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.ABBREVIATION,
                action="edit",
                description="Edit"
            ),
            ComfortCommand(
                id="v",
                trigger="v",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.ABBREVIATION,
                action="view",
                description="View details"
            ),
            ComfortCommand(
                id="l",
                trigger="l",
                trigger_type=TriggerType.KEYWORD,
                command_type=CommandType.ABBREVIATION,
                action="list",
                description="List items"
            ),
        ]

        for cmd in builtin:
            self.commands[cmd.id] = cmd

    # -------------------------------------------------------------------------
    # PREFERENCES
    # -------------------------------------------------------------------------

    def get_preferences(self, user_id: str = "default") -> UserPreferences:
        """Get or create user preferences."""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = UserPreferences(user_id=user_id)
        return self.user_preferences[user_id]

    def set_comfort_level(
        self,
        level: ComfortLevel,
        user_id: str = "default"
    ) -> None:
        """Set user's comfort level."""
        prefs = self.get_preferences(user_id)
        prefs.comfort_level = level

        # Adjust settings based on comfort level
        if level == ComfortLevel.MAXIMUM:
            prefs.verbosity = 0.1
            prefs.speed = 1.0
            prefs.auto_confirm = True
            prefs.predictive_enabled = True
        elif level == ComfortLevel.HIGH:
            prefs.verbosity = 0.3
            prefs.speed = 0.8
            prefs.auto_confirm = True
        elif level == ComfortLevel.MODERATE:
            prefs.verbosity = 0.5
            prefs.speed = 0.6
            prefs.auto_confirm = False
        elif level == ComfortLevel.DETAILED:
            prefs.verbosity = 0.8
            prefs.speed = 0.4
            prefs.auto_confirm = False
        elif level == ComfortLevel.EXPERT:
            prefs.verbosity = 1.0
            prefs.speed = 0.5
            prefs.auto_confirm = False
            prefs.predictive_enabled = False

    # -------------------------------------------------------------------------
    # COMMAND MATCHING
    # -------------------------------------------------------------------------

    def match_command(
        self,
        input_text: str,
        context: Dict[str, Any] = None,
        user_id: str = "default"
    ) -> List[Tuple[ComfortCommand, float]]:
        """Match input to comfort commands. Returns [(command, confidence)]."""
        results = []

        # Check all commands
        for cmd in self.commands.values():
            confidence = cmd.matches(input_text, context)
            if confidence > 0:
                results.append((cmd, confidence))

        # Check user's custom commands
        prefs = self.get_preferences(user_id)
        for cmd in prefs.custom_commands:
            confidence = cmd.matches(input_text, context)
            if confidence > 0:
                results.append((cmd, confidence))

        # Check macros
        for macro in self.macros.values():
            if input_text.lower().strip() == macro.trigger.lower():
                # Create a pseudo-command for the macro
                macro_cmd = ComfortCommand(
                    id=f"macro_{macro.id}",
                    trigger=macro.trigger,
                    trigger_type=TriggerType.KEYWORD,
                    command_type=CommandType.MACRO,
                    action=f"run_macro:{macro.id}",
                    description=macro.description or f"Run macro: {macro.name}"
                )
                results.append((macro_cmd, 1.0))

        # Sort by confidence
        results.sort(key=lambda x: x[1], reverse=True)

        return results

    def get_best_match(
        self,
        input_text: str,
        context: Dict[str, Any] = None,
        user_id: str = "default"
    ) -> Optional[Tuple[ComfortCommand, float]]:
        """Get the best matching command."""
        matches = self.match_command(input_text, context, user_id)
        if matches and matches[0][1] >= 0.5:  # Minimum confidence threshold
            return matches[0]
        return None

    # -------------------------------------------------------------------------
    # COMMAND EXECUTION
    # -------------------------------------------------------------------------

    async def execute(
        self,
        input_text: str,
        context: Dict[str, Any] = None,
        user_id: str = "default"
    ) -> ExecutionResult:
        """Execute a comfort command."""
        start_time = time.time()

        # Find matching command
        match = self.get_best_match(input_text, context, user_id)

        if not match:
            return ExecutionResult(
                success=False,
                command_id="",
                action="",
                result=None,
                duration_ms=(time.time() - start_time) * 1000,
                message=f"No matching command for: {input_text}"
            )

        command, confidence = match

        # Record in history
        self.command_history.append({
            "command_id": command.id,
            "input": input_text,
            "timestamp": datetime.now(),
            "confidence": confidence
        })

        # Update usage stats
        command.usage_count += 1
        command.last_used = datetime.now()

        # Record in macro if recording
        if self.recording_macro is not None:
            self.recording_macro.append({
                "command_id": command.id,
                "input": input_text,
                "action": command.action
            })

        # Execute action
        try:
            if command.action.startswith("run_macro:"):
                macro_id = command.action.split(":")[1]
                result = await self.run_macro(macro_id)
            elif command.action in self.action_handlers:
                handler = self.action_handlers[command.action]
                result = await handler(context or {})
            else:
                # Default action simulation
                result = await self._simulate_action(command.action, context)

            duration = (time.time() - start_time) * 1000

            return ExecutionResult(
                success=True,
                command_id=command.id,
                action=command.action,
                result=result,
                duration_ms=duration,
                message=f"Executed: {command.description}",
                undoable=command.execution_mode in [ExecutionMode.UNDO_SAFE, ExecutionMode.PREVIEW]
            )

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return ExecutionResult(
                success=False,
                command_id=command.id,
                action=command.action,
                result=None,
                duration_ms=duration,
                message=f"Error: {str(e)}"
            )

    async def _simulate_action(
        self,
        action: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Simulate an action for demo purposes."""
        return {
            "action": action,
            "status": "simulated",
            "context": context
        }

    def register_handler(
        self,
        action: str,
        handler: Callable
    ) -> None:
        """Register an action handler."""
        self.action_handlers[action] = handler

    # -------------------------------------------------------------------------
    # MACRO SYSTEM
    # -------------------------------------------------------------------------

    def start_recording(self, macro_name: str) -> None:
        """Start recording a macro."""
        self.recording_macro = []
        logger.info(f"Started recording macro: {macro_name}")

    def stop_recording(
        self,
        macro_name: str,
        trigger: str
    ) -> Optional[Macro]:
        """Stop recording and save macro."""
        if self.recording_macro is None:
            return None

        if not self.recording_macro:
            self.recording_macro = None
            return None

        macro = Macro(
            id=hashlib.md5(f"{macro_name}{time.time()}".encode()).hexdigest()[:8],
            name=macro_name,
            trigger=trigger,
            actions=self.recording_macro.copy(),
            created_at=datetime.now()
        )

        self.macros[macro.id] = macro
        self.recording_macro = None

        logger.info(f"Saved macro '{macro_name}' with {len(macro.actions)} actions")

        return macro

    def cancel_recording(self) -> None:
        """Cancel macro recording."""
        self.recording_macro = None

    async def run_macro(self, macro_id: str) -> List[ExecutionResult]:
        """Run a recorded macro."""
        macro = self.macros.get(macro_id)
        if not macro:
            return []

        results = []
        for action_data in macro.actions:
            result = await self.execute(action_data.get("input", ""))
            results.append(result)

        macro.usage_count += 1

        return results

    def list_macros(self) -> List[Dict[str, Any]]:
        """List all macros."""
        return [macro.to_dict() for macro in self.macros.values()]

    # -------------------------------------------------------------------------
    # SMART DEFAULTS
    # -------------------------------------------------------------------------

    def learn_default(
        self,
        field_name: str,
        value: Any,
        context: Dict[str, Any],
        source: str = "user"
    ) -> None:
        """Learn a smart default from user behavior."""
        default = SmartDefault(
            field_name=field_name,
            value=value,
            context=context.copy(),
            confidence=0.5,
            source=source
        )

        # Check if similar default exists
        existing = self.smart_defaults[field_name]
        for i, existing_default in enumerate(existing):
            if existing_default.context == context:
                # Update existing
                existing[i].value = value
                existing[i].confidence = min(existing[i].confidence + 0.1, 1.0)
                return

        # Add new
        self.smart_defaults[field_name].append(default)

    def get_smart_default(
        self,
        field_name: str,
        context: Dict[str, Any]
    ) -> Optional[Any]:
        """Get a smart default for a field based on context."""
        defaults = self.smart_defaults.get(field_name, [])

        if not defaults:
            return None

        # Find best matching context
        best_match = None
        best_score = 0.0

        for default in defaults:
            # Calculate context match score
            if not default.context:
                score = default.confidence * 0.5  # Low priority for no context
            else:
                matching_keys = sum(
                    1 for k, v in default.context.items()
                    if context.get(k) == v
                )
                score = (matching_keys / len(default.context)) * default.confidence

            if score > best_score:
                best_score = score
                best_match = default

        return best_match.value if best_match and best_score > 0.3 else None

    # -------------------------------------------------------------------------
    # PREDICTIVE COMPLETION
    # -------------------------------------------------------------------------

    def predict_next(
        self,
        partial_input: str = "",
        context: Dict[str, Any] = None,
        user_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Predict what the user might want next."""
        predictions = []

        # Based on partial input
        if partial_input:
            matches = self.match_command(partial_input, context, user_id)
            for cmd, confidence in matches[:5]:
                predictions.append({
                    "type": "command",
                    "text": cmd.trigger,
                    "description": cmd.description,
                    "confidence": confidence
                })

        # Based on history
        if len(self.command_history) >= 3:
            recent = list(self.command_history)[-10:]

            # Find commonly followed commands
            last_cmd = recent[-1]["command_id"] if recent else None
            if last_cmd:
                # Look for patterns of what follows this command
                followers: Dict[str, int] = defaultdict(int)
                for i, entry in enumerate(recent[:-1]):
                    if entry["command_id"] == last_cmd and i + 1 < len(recent):
                        next_cmd = recent[i + 1]["command_id"]
                        followers[next_cmd] += 1

                for cmd_id, count in sorted(followers.items(), key=lambda x: x[1], reverse=True)[:3]:
                    if cmd_id in self.commands:
                        cmd = self.commands[cmd_id]
                        predictions.append({
                            "type": "sequence",
                            "text": cmd.trigger,
                            "description": f"Often follows previous action",
                            "confidence": min(0.8, 0.3 + count * 0.2)
                        })

        # Time-based predictions
        hour = datetime.now().hour
        time_commands = {
            (9, 10): ["status", "list"],  # Morning: check status
            (12, 13): ["save", "status"],  # Lunch: save work
            (17, 18): ["save", "done"]  # End of day: wrap up
        }

        for (start, end), cmds in time_commands.items():
            if start <= hour <= end:
                for cmd_id in cmds:
                    if cmd_id in self.commands:
                        cmd = self.commands[cmd_id]
                        predictions.append({
                            "type": "time",
                            "text": cmd.trigger,
                            "description": cmd.description,
                            "confidence": 0.4
                        })

        # Sort by confidence and deduplicate
        seen = set()
        unique_predictions = []
        for pred in sorted(predictions, key=lambda x: x["confidence"], reverse=True):
            if pred["text"] not in seen:
                seen.add(pred["text"])
                unique_predictions.append(pred)

        return unique_predictions[:5]

    # -------------------------------------------------------------------------
    # CUSTOM COMMANDS
    # -------------------------------------------------------------------------

    def create_custom_command(
        self,
        trigger: str,
        action: str,
        description: str,
        user_id: str = "default",
        aliases: List[str] = None
    ) -> ComfortCommand:
        """Create a custom comfort command."""
        cmd = ComfortCommand(
            id=hashlib.md5(f"custom_{trigger}{time.time()}".encode()).hexdigest()[:8],
            trigger=trigger,
            trigger_type=TriggerType.KEYWORD,
            command_type=CommandType.SINGLE_WORD,
            action=action,
            description=description,
            aliases=aliases or []
        )

        prefs = self.get_preferences(user_id)
        prefs.custom_commands.append(cmd)

        return cmd

    # -------------------------------------------------------------------------
    # ADAPTATION
    # -------------------------------------------------------------------------

    def adapt_response(
        self,
        content: str,
        user_id: str = "default"
    ) -> str:
        """Adapt response based on user preferences."""
        prefs = self.get_preferences(user_id)

        # Verbosity adaptation
        if prefs.verbosity < 0.3:
            # Minimal: Take first sentence only
            sentences = content.split(". ")
            content = sentences[0] + "." if sentences else content
        elif prefs.verbosity > 0.7:
            # Verbose: Add helpful context
            content = f"📋 {content}\n\n💡 Tip: Use 'help' for more options."

        # Speed adaptation (affects how much we ask for confirmation)
        if prefs.speed > 0.8:
            # Fast: Skip confirmations in response
            content = content.replace("Are you sure?", "Done.")
            content = content.replace("Would you like to", "I will")

        # Formality adaptation
        if prefs.formality < 0.3:
            # Casual
            content = content.replace("Please ", "")
            content = content.replace("Would you mind", "Want to")
        elif prefs.formality > 0.7:
            # Formal
            content = content.replace("Hey", "Greetings")
            content = content.replace("Sure", "Certainly")

        return content

    # -------------------------------------------------------------------------
    # AMBIENT INTELLIGENCE
    # -------------------------------------------------------------------------

    async def ambient_optimize(
        self,
        context: Dict[str, Any],
        user_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Background optimization suggestions."""
        optimizations = []

        # Analyze command history for inefficiencies
        if len(self.command_history) >= 10:
            recent = list(self.command_history)[-50:]

            # Find repeated sequences that could be macros
            sequence_length = 3
            sequences: Dict[str, int] = defaultdict(int)

            for i in range(len(recent) - sequence_length + 1):
                seq = tuple(entry["command_id"] for entry in recent[i:i + sequence_length])
                sequences[seq] += 1

            for seq, count in sequences.items():
                if count >= 3:
                    optimizations.append({
                        "type": "macro_suggestion",
                        "message": f"You've repeated a sequence {count} times. Create a macro?",
                        "sequence": list(seq),
                        "priority": count
                    })

        # Suggest underused but relevant commands
        prefs = self.get_preferences(user_id)
        if prefs.comfort_level == ComfortLevel.MODERATE:
            optimizations.append({
                "type": "comfort_upgrade",
                "message": "Consider upgrading to HIGH comfort level for faster workflow",
                "priority": 3
            })

        return optimizations

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def get_help(self, category: CommandType = None) -> str:
        """Get help text for commands."""
        lines = ["🚀 **Ultra-Comfort Commands**\n"]

        # Group by category
        by_category: Dict[CommandType, List[ComfortCommand]] = defaultdict(list)
        for cmd in self.commands.values():
            by_category[cmd.command_type].append(cmd)

        for cmd_type, commands in by_category.items():
            if category and cmd_type != category:
                continue

            lines.append(f"\n**{cmd_type.value.replace('_', ' ').title()}**")
            for cmd in sorted(commands, key=lambda c: c.trigger):
                aliases = f" ({', '.join(cmd.aliases)})" if cmd.aliases else ""
                lines.append(f"  `{cmd.trigger}`{aliases} - {cmd.description}")

        return "\n".join(lines)

    def list_commands(self) -> List[Dict[str, Any]]:
        """List all available commands."""
        return [cmd.to_dict() for cmd in self.commands.values()]


# ============================================================================
# SINGLETON
# ============================================================================

_comfort_engine: Optional[UltraComfortEngine] = None


def get_comfort_engine() -> UltraComfortEngine:
    """Get the global ultra-comfort engine."""
    global _comfort_engine
    if _comfort_engine is None:
        _comfort_engine = UltraComfortEngine()
    return _comfort_engine


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate ultra-comfort automation."""
    print("=" * 60)
    print("ULTRA-COMFORT AUTOMATION LAYER")
    print("=" * 60)

    engine = get_comfort_engine()

    # Set comfort level
    print("\n--- Setting Comfort Level ---")
    engine.set_comfort_level(ComfortLevel.MAXIMUM)
    prefs = engine.get_preferences()
    print(f"Comfort Level: {prefs.comfort_level.value}")
    print(f"Verbosity: {prefs.verbosity}")
    print(f"Speed: {prefs.speed}")

    # Execute single-word commands
    print("\n--- Executing Commands ---")
    test_inputs = ["help", "status", "run", "y", "q"]

    for input_text in test_inputs:
        result = await engine.execute(input_text)
        print(f"'{input_text}' -> {result.message}")

    # Predictive completion
    print("\n--- Predictive Completion ---")
    predictions = engine.predict_next("s", {})
    for pred in predictions:
        print(f"  {pred['text']}: {pred['description']} ({pred['confidence']:.2f})")

    # Smart defaults
    print("\n--- Smart Defaults ---")
    engine.learn_default("output_format", "json", {"context": "api"})
    engine.learn_default("output_format", "json", {"context": "api"})  # Reinforce
    default = engine.get_smart_default("output_format", {"context": "api"})
    print(f"Learned default for output_format: {default}")

    # Macro recording
    print("\n--- Macro Recording ---")
    engine.start_recording("daily_routine")
    await engine.execute("status")
    await engine.execute("list")
    await engine.execute("next")
    macro = engine.stop_recording("daily_routine", "daily")
    if macro:
        print(f"Created macro: {macro.name} with {len(macro.actions)} actions")

    # Custom command
    print("\n--- Custom Command ---")
    custom = engine.create_custom_command(
        trigger="deploy",
        action="deploy_to_production",
        description="Deploy to production",
        aliases=["ship", "push"]
    )
    print(f"Created: {custom.trigger} -> {custom.action}")

    # Adaptation
    print("\n--- Response Adaptation ---")
    response = "Please wait while I process your request. Are you sure?"
    adapted = engine.adapt_response(response)
    print(f"Original: {response}")
    print(f"Adapted:  {adapted}")

    # Help
    print("\n--- Available Commands ---")
    print(engine.get_help())

    print("\n" + "=" * 60)
    print("ULTRA-COMFORT DEMO COMPLETE")


if __name__ == "__main__":
    asyncio.run(demo())
