"""
BAEL - Trigger System
Advanced trigger definitions and management.
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

logger = logging.getLogger("BAEL.Proactive.Triggers")


class TriggerOperator(Enum):
    """Operators for trigger conditions."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_OR_EQUAL = "gte"
    LESS_OR_EQUAL = "lte"
    CONTAINS = "contains"
    MATCHES = "matches"  # Regex
    IN = "in"
    NOT_IN = "not_in"


class CombineOperator(Enum):
    """How to combine multiple conditions."""
    AND = "and"
    OR = "or"
    NOT = "not"


@dataclass
class Condition:
    """A single trigger condition."""
    field: str
    operator: TriggerOperator
    value: Any
    transform: Optional[str] = None  # Optional transformation


@dataclass
class CompositeCondition:
    """A composite condition combining multiple conditions."""
    operator: CombineOperator
    conditions: List[Union["Condition", "CompositeCondition"]]


@dataclass
class TriggerDefinition:
    """A complete trigger definition."""
    id: str
    name: str
    description: str
    condition: Union[Condition, CompositeCondition]
    action: str
    priority: int = 5
    enabled: bool = True
    cooldown_seconds: float = 300
    max_fires_per_hour: int = 10
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TriggerFire:
    """Record of a trigger firing."""
    trigger_id: str
    timestamp: float
    context: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None


class TriggerEvaluator:
    """
    Evaluates trigger conditions against context.
    """

    def __init__(self):
        self._transforms = {
            "lower": lambda x: x.lower() if isinstance(x, str) else x,
            "upper": lambda x: x.upper() if isinstance(x, str) else x,
            "len": lambda x: len(x) if hasattr(x, "__len__") else 0,
            "int": lambda x: int(x) if x else 0,
            "float": lambda x: float(x) if x else 0.0,
            "bool": lambda x: bool(x),
            "strip": lambda x: x.strip() if isinstance(x, str) else x,
            "words": lambda x: len(x.split()) if isinstance(x, str) else 0,
        }

    def evaluate(
        self,
        condition: Union[Condition, CompositeCondition],
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate a condition against context."""
        if isinstance(condition, Condition):
            return self._evaluate_simple(condition, context)
        else:
            return self._evaluate_composite(condition, context)

    def _evaluate_simple(
        self,
        condition: Condition,
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate a simple condition."""
        # Get field value
        value = self._get_field_value(condition.field, context)

        # Apply transform if specified
        if condition.transform and condition.transform in self._transforms:
            value = self._transforms[condition.transform](value)

        expected = condition.value
        op = condition.operator

        try:
            if op == TriggerOperator.EQUALS:
                return value == expected
            elif op == TriggerOperator.NOT_EQUALS:
                return value != expected
            elif op == TriggerOperator.GREATER_THAN:
                return value > expected
            elif op == TriggerOperator.LESS_THAN:
                return value < expected
            elif op == TriggerOperator.GREATER_OR_EQUAL:
                return value >= expected
            elif op == TriggerOperator.LESS_OR_EQUAL:
                return value <= expected
            elif op == TriggerOperator.CONTAINS:
                return expected in value if hasattr(value, "__contains__") else False
            elif op == TriggerOperator.MATCHES:
                return bool(re.search(expected, str(value)))
            elif op == TriggerOperator.IN:
                return value in expected
            elif op == TriggerOperator.NOT_IN:
                return value not in expected
        except Exception:
            return False

        return False

    def _evaluate_composite(
        self,
        condition: CompositeCondition,
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate a composite condition."""
        results = [
            self.evaluate(c, context)
            for c in condition.conditions
        ]

        if condition.operator == CombineOperator.AND:
            return all(results)
        elif condition.operator == CombineOperator.OR:
            return any(results)
        elif condition.operator == CombineOperator.NOT:
            return not results[0] if results else True

        return False

    def _get_field_value(
        self,
        field: str,
        context: Dict[str, Any]
    ) -> Any:
        """Get a field value from context, supporting nested access."""
        parts = field.split(".")
        value = context

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None

            if value is None:
                return None

        return value


class TriggerRegistry:
    """
    Registry for managing trigger definitions.
    """

    def __init__(self):
        self._triggers: Dict[str, TriggerDefinition] = {}
        self._fire_history: List[TriggerFire] = []
        self._evaluator = TriggerEvaluator()

        # Register built-in triggers
        self._register_builtin_triggers()

    def _register_builtin_triggers(self):
        """Register built-in trigger definitions."""
        # Error threshold trigger
        self.register(TriggerDefinition(
            id="error_threshold",
            name="Error Threshold",
            description="Fires when error count exceeds threshold",
            condition=Condition(
                field="error_count",
                operator=TriggerOperator.GREATER_OR_EQUAL,
                value=3
            ),
            action="alert_errors",
            priority=8
        ))

        # Idle timeout trigger
        self.register(TriggerDefinition(
            id="idle_timeout",
            name="Idle Timeout",
            description="Fires after period of inactivity",
            condition=Condition(
                field="idle_seconds",
                operator=TriggerOperator.GREATER_THAN,
                value=1800
            ),
            action="suggest_activity",
            priority=3
        ))

        # Long query trigger
        self.register(TriggerDefinition(
            id="long_query",
            name="Long Query",
            description="Fires for complex queries needing planning",
            condition=Condition(
                field="query",
                operator=TriggerOperator.GREATER_THAN,
                value=200,
                transform="len"
            ),
            action="create_plan",
            priority=6
        ))

        # Question pattern trigger
        self.register(TriggerDefinition(
            id="help_request",
            name="Help Request",
            description="Fires when user asks for help",
            condition=Condition(
                field="query",
                operator=TriggerOperator.MATCHES,
                value=r"\b(help|assist|how (do|can|to)|explain)\b"
            ),
            action="provide_assistance",
            priority=7
        ))

        # Repeated failure trigger
        self.register(TriggerDefinition(
            id="repeated_failure",
            name="Repeated Failure",
            description="Fires on repeated failures",
            condition=CompositeCondition(
                operator=CombineOperator.AND,
                conditions=[
                    Condition(
                        field="failure_count",
                        operator=TriggerOperator.GREATER_OR_EQUAL,
                        value=2
                    ),
                    Condition(
                        field="same_error_type",
                        operator=TriggerOperator.EQUALS,
                        value=True
                    )
                ]
            ),
            action="suggest_alternative",
            priority=9
        ))

    def register(self, trigger: TriggerDefinition) -> None:
        """Register a trigger definition."""
        self._triggers[trigger.id] = trigger
        logger.debug(f"Registered trigger: {trigger.name}")

    def unregister(self, trigger_id: str) -> bool:
        """Unregister a trigger."""
        if trigger_id in self._triggers:
            del self._triggers[trigger_id]
            return True
        return False

    def get_trigger(self, trigger_id: str) -> Optional[TriggerDefinition]:
        """Get a trigger by ID."""
        return self._triggers.get(trigger_id)

    def list_triggers(
        self,
        enabled_only: bool = True
    ) -> List[TriggerDefinition]:
        """List all triggers."""
        triggers = list(self._triggers.values())

        if enabled_only:
            triggers = [t for t in triggers if t.enabled]

        return sorted(triggers, key=lambda t: t.priority, reverse=True)

    async def check_triggers(
        self,
        context: Dict[str, Any]
    ) -> List[TriggerFire]:
        """Check all triggers against context."""
        fires = []
        current_time = time.time()
        hour_ago = current_time - 3600

        for trigger in self._triggers.values():
            if not trigger.enabled:
                continue

            # Check cooldown
            recent_fires = [
                f for f in self._fire_history
                if f.trigger_id == trigger.id and f.timestamp > current_time - trigger.cooldown_seconds
            ]
            if recent_fires:
                continue

            # Check rate limit
            hour_fires = [
                f for f in self._fire_history
                if f.trigger_id == trigger.id and f.timestamp > hour_ago
            ]
            if len(hour_fires) >= trigger.max_fires_per_hour:
                continue

            # Evaluate condition
            if self._evaluator.evaluate(trigger.condition, context):
                fire = TriggerFire(
                    trigger_id=trigger.id,
                    timestamp=current_time,
                    context=context
                )
                fires.append(fire)
                self._fire_history.append(fire)
                logger.info(f"Trigger fired: {trigger.name}")

        # Cleanup old fire history
        self._fire_history = [
            f for f in self._fire_history
            if f.timestamp > hour_ago
        ]

        return fires

    def get_fire_history(
        self,
        trigger_id: Optional[str] = None,
        limit: int = 50
    ) -> List[TriggerFire]:
        """Get trigger fire history."""
        history = self._fire_history

        if trigger_id:
            history = [f for f in history if f.trigger_id == trigger_id]

        return sorted(history, key=lambda f: f.timestamp, reverse=True)[:limit]


class TriggerBuilder:
    """
    Fluent builder for creating trigger definitions.

    Example:
        trigger = TriggerBuilder("my_trigger") \
            .name("My Trigger") \
            .when("error_count").greater_than(3) \
            .and_when("user.active").equals(True) \
            .action("alert") \
            .priority(8) \
            .build()
    """

    def __init__(self, trigger_id: str):
        self._id = trigger_id
        self._name = trigger_id
        self._description = ""
        self._conditions: List[Condition] = []
        self._combine = CombineOperator.AND
        self._action = "default"
        self._priority = 5
        self._enabled = True
        self._cooldown = 300
        self._max_fires = 10
        self._metadata: Dict[str, Any] = {}
        self._current_field: Optional[str] = None
        self._current_transform: Optional[str] = None

    def name(self, name: str) -> "TriggerBuilder":
        """Set trigger name."""
        self._name = name
        return self

    def description(self, desc: str) -> "TriggerBuilder":
        """Set trigger description."""
        self._description = desc
        return self

    def when(self, field: str) -> "TriggerBuilder":
        """Start a condition with a field."""
        self._current_field = field
        self._current_transform = None
        return self

    def transform(self, transform: str) -> "TriggerBuilder":
        """Add transformation to current field."""
        self._current_transform = transform
        return self

    def equals(self, value: Any) -> "TriggerBuilder":
        """Add equals condition."""
        return self._add_condition(TriggerOperator.EQUALS, value)

    def not_equals(self, value: Any) -> "TriggerBuilder":
        """Add not equals condition."""
        return self._add_condition(TriggerOperator.NOT_EQUALS, value)

    def greater_than(self, value: Any) -> "TriggerBuilder":
        """Add greater than condition."""
        return self._add_condition(TriggerOperator.GREATER_THAN, value)

    def less_than(self, value: Any) -> "TriggerBuilder":
        """Add less than condition."""
        return self._add_condition(TriggerOperator.LESS_THAN, value)

    def contains(self, value: Any) -> "TriggerBuilder":
        """Add contains condition."""
        return self._add_condition(TriggerOperator.CONTAINS, value)

    def matches(self, pattern: str) -> "TriggerBuilder":
        """Add regex matches condition."""
        return self._add_condition(TriggerOperator.MATCHES, pattern)

    def is_in(self, values: List[Any]) -> "TriggerBuilder":
        """Add in condition."""
        return self._add_condition(TriggerOperator.IN, values)

    def _add_condition(
        self,
        operator: TriggerOperator,
        value: Any
    ) -> "TriggerBuilder":
        """Add a condition."""
        if self._current_field:
            self._conditions.append(Condition(
                field=self._current_field,
                operator=operator,
                value=value,
                transform=self._current_transform
            ))
        return self

    def and_when(self, field: str) -> "TriggerBuilder":
        """Add AND condition."""
        self._combine = CombineOperator.AND
        return self.when(field)

    def or_when(self, field: str) -> "TriggerBuilder":
        """Add OR condition."""
        self._combine = CombineOperator.OR
        return self.when(field)

    def action(self, action: str) -> "TriggerBuilder":
        """Set action."""
        self._action = action
        return self

    def priority(self, priority: int) -> "TriggerBuilder":
        """Set priority."""
        self._priority = priority
        return self

    def cooldown(self, seconds: float) -> "TriggerBuilder":
        """Set cooldown."""
        self._cooldown = seconds
        return self

    def max_fires(self, count: int) -> "TriggerBuilder":
        """Set max fires per hour."""
        self._max_fires = count
        return self

    def metadata(self, key: str, value: Any) -> "TriggerBuilder":
        """Add metadata."""
        self._metadata[key] = value
        return self

    def disabled(self) -> "TriggerBuilder":
        """Disable trigger."""
        self._enabled = False
        return self

    def build(self) -> TriggerDefinition:
        """Build the trigger definition."""
        if len(self._conditions) == 1:
            condition = self._conditions[0]
        else:
            condition = CompositeCondition(
                operator=self._combine,
                conditions=self._conditions
            )

        return TriggerDefinition(
            id=self._id,
            name=self._name,
            description=self._description,
            condition=condition,
            action=self._action,
            priority=self._priority,
            enabled=self._enabled,
            cooldown_seconds=self._cooldown,
            max_fires_per_hour=self._max_fires,
            metadata=self._metadata
        )


# Global instances
_trigger_registry: Optional[TriggerRegistry] = None
_trigger_evaluator: Optional[TriggerEvaluator] = None


def get_trigger_registry() -> TriggerRegistry:
    """Get or create trigger registry."""
    global _trigger_registry
    if _trigger_registry is None:
        _trigger_registry = TriggerRegistry()
    return _trigger_registry


def get_trigger_evaluator() -> TriggerEvaluator:
    """Get or create trigger evaluator."""
    global _trigger_evaluator
    if _trigger_evaluator is None:
        _trigger_evaluator = TriggerEvaluator()
    return _trigger_evaluator
