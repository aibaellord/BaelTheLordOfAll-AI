"""
BAEL - Proactive Engine
Core engine for proactive behavior orchestration.
"""

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional

from . import (ActionUrgency, ProactiveAction, ProactiveTrigger, TriggerType,
               UserPattern)

logger = logging.getLogger("BAEL.Proactive.Engine")


@dataclass
class EngineConfig:
    """Configuration for proactive engine."""
    enabled: bool = True
    check_interval_seconds: float = 60.0
    max_pending_actions: int = 10
    auto_execute_low_urgency: bool = False
    learn_patterns: bool = True
    notification_callback: Optional[Callable] = None


class ProactiveEngine:
    """
    Main engine for proactive behavior.

    Features:
    - Trigger management and evaluation
    - Action queue management
    - Pattern learning from interactions
    - Background monitoring coordination
    - Urgency-based prioritization
    """

    def __init__(self, config: Optional[EngineConfig] = None):
        self.config = config or EngineConfig()

        self._triggers: Dict[str, ProactiveTrigger] = {}
        self._pending_actions: List[ProactiveAction] = []
        self._patterns: Dict[str, UserPattern] = {}
        self._event_history: List[Dict[str, Any]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Built-in triggers
        self._register_builtin_triggers()

    def _register_builtin_triggers(self):
        """Register built-in proactive triggers."""
        # Long idle detection
        self.register_trigger(ProactiveTrigger(
            id="idle_check",
            name="Idle Detection",
            trigger_type=TriggerType.TIME,
            condition={"idle_minutes": 30},
            action="suggest_break_or_review",
            urgency=ActionUrgency.LOW,
            cooldown_seconds=1800
        ))

        # Error pattern detection
        self.register_trigger(ProactiveTrigger(
            id="error_pattern",
            name="Repeated Errors",
            trigger_type=TriggerType.PATTERN,
            condition={"error_count": 3, "time_window_minutes": 10},
            action="offer_debugging_help",
            urgency=ActionUrgency.HIGH,
            cooldown_seconds=300
        ))

        # Context switch detection
        self.register_trigger(ProactiveTrigger(
            id="context_switch",
            name="Context Change",
            trigger_type=TriggerType.CONTEXT,
            condition={"topic_change": True},
            action="offer_context_summary",
            urgency=ActionUrgency.MEDIUM,
            cooldown_seconds=600
        ))

        # Task completion opportunity
        self.register_trigger(ProactiveTrigger(
            id="task_completion",
            name="Task Completion",
            trigger_type=TriggerType.PATTERN,
            condition={"partial_task": True, "user_paused": True},
            action="offer_task_completion",
            urgency=ActionUrgency.MEDIUM,
            cooldown_seconds=300
        ))

        # Learning opportunity
        self.register_trigger(ProactiveTrigger(
            id="learning_opportunity",
            name="Learning Suggestion",
            trigger_type=TriggerType.PATTERN,
            condition={"repeated_question_pattern": True},
            action="suggest_learning_resource",
            urgency=ActionUrgency.LOW,
            cooldown_seconds=3600
        ))

    def register_trigger(self, trigger: ProactiveTrigger) -> None:
        """Register a new trigger."""
        self._triggers[trigger.id] = trigger
        logger.debug(f"Registered trigger: {trigger.name}")

    def unregister_trigger(self, trigger_id: str) -> bool:
        """Unregister a trigger."""
        if trigger_id in self._triggers:
            del self._triggers[trigger_id]
            return True
        return False

    async def start(self) -> None:
        """Start the proactive engine."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Proactive engine started")

    async def stop(self) -> None:
        """Stop the proactive engine."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Proactive engine stopped")

    async def _run_loop(self) -> None:
        """Main proactive monitoring loop."""
        while self._running:
            try:
                await self._check_triggers()
                await asyncio.sleep(self.config.check_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in proactive loop: {e}")
                await asyncio.sleep(5)

    async def _check_triggers(self) -> None:
        """Check all triggers and create actions if needed."""
        current_time = time.time()
        context = await self._gather_context()

        for trigger in self._triggers.values():
            if not trigger.enabled:
                continue

            # Check cooldown
            if trigger.last_triggered:
                elapsed = current_time - trigger.last_triggered
                if elapsed < trigger.cooldown_seconds:
                    continue

            # Evaluate trigger condition
            if await self._evaluate_trigger(trigger, context):
                action = await self._create_action(trigger, context)
                self._pending_actions.append(action)
                trigger.last_triggered = current_time

                logger.info(f"Trigger fired: {trigger.name}")

                # Notify if callback set
                if self.config.notification_callback:
                    try:
                        await self.config.notification_callback(action)
                    except Exception as e:
                        logger.error(f"Notification callback error: {e}")

                # Auto-execute if configured
                if action.auto_execute or (
                    self.config.auto_execute_low_urgency and
                    action.urgency == ActionUrgency.LOW
                ):
                    await self.execute_action(action)

        # Trim pending actions if too many
        while len(self._pending_actions) > self.config.max_pending_actions:
            self._pending_actions.pop(0)

    async def _gather_context(self) -> Dict[str, Any]:
        """Gather current context for trigger evaluation."""
        context = {
            "timestamp": time.time(),
            "event_count": len(self._event_history),
            "pending_actions": len(self._pending_actions)
        }

        # Recent events
        recent_events = [
            e for e in self._event_history
            if time.time() - e.get("timestamp", 0) < 600
        ]
        context["recent_events"] = recent_events
        context["recent_event_count"] = len(recent_events)

        # Error count
        context["recent_errors"] = sum(
            1 for e in recent_events if e.get("type") == "error"
        )

        # Idle time (if available)
        if self._event_history:
            last_event = max(e.get("timestamp", 0) for e in self._event_history)
            context["idle_seconds"] = time.time() - last_event
        else:
            context["idle_seconds"] = 0

        return context

    async def _evaluate_trigger(
        self,
        trigger: ProactiveTrigger,
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate if a trigger condition is met."""
        condition = trigger.condition

        if trigger.trigger_type == TriggerType.TIME:
            if "idle_minutes" in condition:
                idle_minutes = context.get("idle_seconds", 0) / 60
                return idle_minutes >= condition["idle_minutes"]
            return False

        elif trigger.trigger_type == TriggerType.PATTERN:
            if "error_count" in condition:
                return context.get("recent_errors", 0) >= condition["error_count"]
            if "repeated_question_pattern" in condition:
                return self._detect_repeated_pattern(context)
            return False

        elif trigger.trigger_type == TriggerType.CONTEXT:
            if "topic_change" in condition:
                return self._detect_topic_change(context)
            return False

        elif trigger.trigger_type == TriggerType.THRESHOLD:
            return self._evaluate_threshold(condition, context)

        elif trigger.trigger_type == TriggerType.EVENT:
            return self._check_event_trigger(condition, context)

        return False

    def _detect_repeated_pattern(self, context: Dict[str, Any]) -> bool:
        """Detect if user is repeating similar queries."""
        recent = context.get("recent_events", [])
        queries = [e.get("query", "") for e in recent if e.get("query")]

        if len(queries) < 3:
            return False

        # Simple check: are queries similar?
        # In real implementation, would use embeddings
        for i, q1 in enumerate(queries[:-1]):
            for q2 in queries[i+1:]:
                if self._text_similarity(q1, q2) > 0.7:
                    return True

        return False

    def _detect_topic_change(self, context: Dict[str, Any]) -> bool:
        """Detect if conversation topic has changed significantly."""
        recent = context.get("recent_events", [])
        if len(recent) < 2:
            return False

        # Compare recent topics
        # Simplified - would use embeddings in production
        return False

    def _evaluate_threshold(
        self,
        condition: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate threshold-based conditions."""
        for key, threshold in condition.items():
            if key in context:
                if context[key] >= threshold:
                    return True
        return False

    def _check_event_trigger(
        self,
        condition: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """Check if specific event has occurred."""
        event_type = condition.get("event_type")
        if not event_type:
            return False

        recent = context.get("recent_events", [])
        return any(e.get("type") == event_type for e in recent)

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity."""
        if not text1 or not text2:
            return 0.0

        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)

    async def _create_action(
        self,
        trigger: ProactiveTrigger,
        context: Dict[str, Any]
    ) -> ProactiveAction:
        """Create a proactive action from a triggered event."""
        # Generate suggested response based on action type
        responses = {
            "suggest_break_or_review": "You've been working for a while. Would you like me to summarize what we've covered, or suggest a break?",
            "offer_debugging_help": "I've noticed several errors recently. Would you like me to help debug the issue or suggest solutions?",
            "offer_context_summary": "It seems like we're shifting topics. Would you like a summary of our previous discussion?",
            "offer_task_completion": "I noticed we started a task that wasn't completed. Would you like me to help finish it?",
            "suggest_learning_resource": "You've asked about this topic multiple times. Would you like me to provide a comprehensive explanation or resources?"
        }

        return ProactiveAction(
            id=f"action_{uuid.uuid4().hex[:8]}",
            trigger_id=trigger.id,
            description=trigger.name,
            urgency=trigger.urgency,
            suggested_response=responses.get(
                trigger.action,
                f"I noticed something that might need attention: {trigger.name}"
            ),
            context=context,
            auto_execute=False,
            requires_confirmation=trigger.urgency.value < 4
        )

    async def execute_action(self, action: ProactiveAction) -> Dict[str, Any]:
        """Execute a proactive action."""
        logger.info(f"Executing proactive action: {action.description}")

        # Remove from pending
        self._pending_actions = [a for a in self._pending_actions if a.id != action.id]

        # Record execution
        self.record_event({
            "type": "proactive_action",
            "action_id": action.id,
            "trigger_id": action.trigger_id,
            "description": action.description
        })

        return {
            "executed": True,
            "action_id": action.id,
            "response": action.suggested_response
        }

    def record_event(self, event: Dict[str, Any]) -> None:
        """Record an event for pattern learning."""
        event["timestamp"] = time.time()
        self._event_history.append(event)

        # Trim old events
        cutoff = time.time() - 3600  # Keep 1 hour of history
        self._event_history = [
            e for e in self._event_history
            if e.get("timestamp", 0) > cutoff
        ]

        # Learn patterns if enabled
        if self.config.learn_patterns:
            self._update_patterns(event)

    def _update_patterns(self, event: Dict[str, Any]) -> None:
        """Update learned patterns from event."""
        event_type = event.get("type", "unknown")
        pattern_id = f"pattern_{event_type}"

        if pattern_id in self._patterns:
            pattern = self._patterns[pattern_id]
            pattern.frequency += 1
            pattern.last_occurrence = time.time()
        else:
            self._patterns[pattern_id] = UserPattern(
                id=pattern_id,
                pattern_type=event_type,
                frequency=1,
                last_occurrence=time.time(),
                context=event,
                confidence=0.5
            )

    def get_pending_actions(
        self,
        min_urgency: Optional[ActionUrgency] = None
    ) -> List[ProactiveAction]:
        """Get pending proactive actions."""
        actions = self._pending_actions

        if min_urgency:
            actions = [a for a in actions if a.urgency.value >= min_urgency.value]

        # Sort by urgency (highest first)
        return sorted(actions, key=lambda a: a.urgency.value, reverse=True)

    def dismiss_action(self, action_id: str) -> bool:
        """Dismiss a pending action."""
        initial_count = len(self._pending_actions)
        self._pending_actions = [a for a in self._pending_actions if a.id != action_id]
        return len(self._pending_actions) < initial_count

    def get_patterns(self) -> List[UserPattern]:
        """Get learned user patterns."""
        return list(self._patterns.values())


# Global instance
_proactive_engine: Optional[ProactiveEngine] = None


def get_proactive_engine(config: Optional[EngineConfig] = None) -> ProactiveEngine:
    """Get or create proactive engine instance."""
    global _proactive_engine
    if _proactive_engine is None or config is not None:
        _proactive_engine = ProactiveEngine(config)
    return _proactive_engine
