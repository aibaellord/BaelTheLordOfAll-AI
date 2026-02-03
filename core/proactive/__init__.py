"""
BAEL - Proactive Behavior System
Anticipates user needs, initiates tasks autonomously, and monitors for opportunities.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BAEL.Proactive")


class TriggerType(Enum):
    """Types of proactive triggers."""
    TIME = "time"          # Time-based triggers
    EVENT = "event"        # Event-based triggers
    PATTERN = "pattern"    # Pattern recognition triggers
    THRESHOLD = "threshold" # Threshold-based triggers
    CONTEXT = "context"    # Context change triggers


class ActionUrgency(Enum):
    """Urgency levels for proactive actions."""
    LOW = 1       # Can wait, background
    MEDIUM = 2    # Should address soon
    HIGH = 3      # Important, address promptly
    CRITICAL = 4  # Urgent, needs immediate attention


@dataclass
class ProactiveTrigger:
    """A trigger for proactive behavior."""
    id: str
    name: str
    trigger_type: TriggerType
    condition: Dict[str, Any]
    action: str
    urgency: ActionUrgency = ActionUrgency.MEDIUM
    enabled: bool = True
    last_triggered: Optional[float] = None
    cooldown_seconds: float = 300  # Min time between triggers


@dataclass
class ProactiveAction:
    """An action to be taken proactively."""
    id: str
    trigger_id: str
    description: str
    urgency: ActionUrgency
    suggested_response: str
    context: Dict[str, Any] = field(default_factory=dict)
    auto_execute: bool = False
    requires_confirmation: bool = True


@dataclass
class UserPattern:
    """A learned user behavior pattern."""
    id: str
    pattern_type: str
    frequency: float  # How often this pattern occurs
    last_occurrence: float
    context: Dict[str, Any]
    confidence: float


# Lazy imports
def get_proactive_engine():
    """Get the proactive engine."""
    from .proactive_engine import ProactiveEngine
    return ProactiveEngine()


def get_need_anticipator():
    """Get the need anticipator."""
    from .need_anticipator import NeedAnticipator
    return NeedAnticipator()


def get_background_monitor():
    """Get the background monitor."""
    from .background_monitor import BackgroundMonitor
    return BackgroundMonitor()


__all__ = [
    "TriggerType",
    "ActionUrgency",
    "ProactiveTrigger",
    "ProactiveAction",
    "UserPattern",
    "get_proactive_engine",
    "get_need_anticipator",
    "get_background_monitor"
]
