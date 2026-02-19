"""
👑 MASTERY CORE 👑
==================
Core mastery structures.

Features:
- Capability management
- Mastery levels
- System state
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
import uuid


class CapabilityType(Enum):
    """Types of system capabilities"""
    PERCEPTION = auto()
    REASONING = auto()
    LEARNING = auto()
    MEMORY = auto()
    CREATIVITY = auto()
    PLANNING = auto()
    EXECUTION = auto()
    COMMUNICATION = auto()
    ADAPTATION = auto()
    METACOGNITION = auto()


class MasteryLevel(Enum):
    """Levels of capability mastery"""
    NOVICE = 1
    BEGINNER = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5
    MASTER = 6
    TRANSCENDENT = 7


@dataclass
class SystemCapability:
    """A system capability"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Identity
    name: str = ""
    capability_type: CapabilityType = CapabilityType.REASONING

    # Mastery
    level: MasteryLevel = MasteryLevel.NOVICE
    experience: float = 0.0

    # Performance
    accuracy: float = 0.0
    speed: float = 0.0
    reliability: float = 0.0

    # Dependencies
    required_capabilities: List[str] = field(default_factory=list)
    enhanced_by: List[str] = field(default_factory=list)

    # Status
    is_active: bool = True
    is_evolving: bool = False

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None

    def use(self):
        """Record capability usage"""
        self.last_used = datetime.now()
        self.experience += 0.1
        self._check_level_up()

    def _check_level_up(self):
        """Check for level up"""
        thresholds = {
            MasteryLevel.NOVICE: 1.0,
            MasteryLevel.BEGINNER: 5.0,
            MasteryLevel.INTERMEDIATE: 20.0,
            MasteryLevel.ADVANCED: 50.0,
            MasteryLevel.EXPERT: 100.0,
            MasteryLevel.MASTER: 200.0,
            MasteryLevel.TRANSCENDENT: float('inf')
        }

        current_threshold = thresholds.get(self.level, float('inf'))
        if self.experience >= current_threshold:
            next_level = MasteryLevel(min(7, self.level.value + 1))
            self.level = next_level

    def get_power(self) -> float:
        """Get capability power score"""
        return (
            self.level.value * 0.3 +
            self.accuracy * 0.25 +
            self.speed * 0.2 +
            self.reliability * 0.25
        )


@dataclass
class SystemState:
    """Current system state"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Overall status
    overall_mastery: MasteryLevel = MasteryLevel.NOVICE
    power_level: float = 0.0

    # Resources
    energy: float = 1.0
    focus: float = 1.0

    # Active systems
    active_capabilities: Set[str] = field(default_factory=set)
    active_protocols: Set[str] = field(default_factory=set)

    # Performance
    tasks_completed: int = 0
    success_rate: float = 0.0

    # Evolution
    evolution_stage: int = 0
    transcendence_progress: float = 0.0

    # Timestamp
    timestamp: datetime = field(default_factory=datetime.now)

    def update_power(self, capabilities: List[SystemCapability]):
        """Update power level from capabilities"""
        if not capabilities:
            self.power_level = 0.0
            return

        total_power = sum(c.get_power() for c in capabilities)
        self.power_level = total_power / len(capabilities)

        # Update overall mastery
        avg_level = sum(c.level.value for c in capabilities) / len(capabilities)
        self.overall_mastery = MasteryLevel(min(7, int(avg_level)))


class MasteryCore:
    """
    Core mastery management.
    """

    def __init__(self):
        # Capabilities
        self.capabilities: Dict[str, SystemCapability] = {}

        # Current state
        self.state = SystemState()

        # Mastery history
        self.history: List[Dict[str, Any]] = []

        # Achievement tracking
        self.achievements: Set[str] = set()

        # Evolution callbacks
        self.on_level_up: List[Callable[[SystemCapability, MasteryLevel], None]] = []
        self.on_achievement: List[Callable[[str], None]] = []

    def register_capability(self, capability: SystemCapability):
        """Register new capability"""
        self.capabilities[capability.id] = capability
        self.state.active_capabilities.add(capability.id)
        self._update_state()

    def get_capability(self, capability_id: str) -> Optional[SystemCapability]:
        """Get capability by ID"""
        return self.capabilities.get(capability_id)

    def use_capability(self, capability_id: str) -> bool:
        """Use a capability"""
        capability = self.capabilities.get(capability_id)
        if not capability or not capability.is_active:
            return False

        old_level = capability.level
        capability.use()

        # Check level up
        if capability.level != old_level:
            self._trigger_level_up(capability, capability.level)

        self._update_state()
        return True

    def _trigger_level_up(self, capability: SystemCapability, new_level: MasteryLevel):
        """Trigger level up callbacks"""
        for callback in self.on_level_up:
            try:
                callback(capability, new_level)
            except Exception:
                pass

        # Record history
        self.history.append({
            'event': 'level_up',
            'capability': capability.name,
            'new_level': new_level.name,
            'timestamp': datetime.now()
        })

        # Check achievements
        self._check_achievements()

    def _check_achievements(self):
        """Check for new achievements"""
        # First master level
        if any(c.level.value >= 6 for c in self.capabilities.values()):
            self._unlock_achievement("first_master")

        # All advanced
        if all(c.level.value >= 4 for c in self.capabilities.values()):
            self._unlock_achievement("all_advanced")

        # Transcendent
        if any(c.level.value >= 7 for c in self.capabilities.values()):
            self._unlock_achievement("transcendent")

    def _unlock_achievement(self, achievement: str):
        """Unlock achievement"""
        if achievement not in self.achievements:
            self.achievements.add(achievement)

            for callback in self.on_achievement:
                try:
                    callback(achievement)
                except Exception:
                    pass

    def _update_state(self):
        """Update system state"""
        capabilities = list(self.capabilities.values())
        self.state.update_power(capabilities)
        self.state.timestamp = datetime.now()

    def get_capabilities_by_type(
        self,
        capability_type: CapabilityType
    ) -> List[SystemCapability]:
        """Get capabilities by type"""
        return [
            c for c in self.capabilities.values()
            if c.capability_type == capability_type
        ]

    def get_mastery_report(self) -> Dict[str, Any]:
        """Get mastery report"""
        return {
            'overall_mastery': self.state.overall_mastery.name,
            'power_level': self.state.power_level,
            'capabilities': {
                c.name: {
                    'level': c.level.name,
                    'experience': c.experience,
                    'power': c.get_power()
                }
                for c in self.capabilities.values()
            },
            'achievements': list(self.achievements),
            'evolution_stage': self.state.evolution_stage
        }

    def evolve(self):
        """Evolve to next stage"""
        self.state.evolution_stage += 1

        # Boost all capabilities
        for capability in self.capabilities.values():
            capability.experience += 10.0
            capability._check_level_up()

        self._update_state()

        self.history.append({
            'event': 'evolution',
            'stage': self.state.evolution_stage,
            'timestamp': datetime.now()
        })


# Export all
__all__ = [
    'CapabilityType',
    'MasteryLevel',
    'SystemCapability',
    'SystemState',
    'MasteryCore',
]
