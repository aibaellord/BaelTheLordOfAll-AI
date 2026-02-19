"""
👑 MASTERY PROTOCOLS 👑
=======================
Protocols for mastery achievement.

Features:
- Evolution protocols
- Transcendence paths
- Mastery rituals
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
import uuid

from .mastery_core import MasteryLevel, MasteryCore


class ProtocolPhase(Enum):
    """Protocol phases"""
    INITIALIZATION = auto()
    PREPARATION = auto()
    EXECUTION = auto()
    INTEGRATION = auto()
    COMPLETION = auto()
    TRANSCENDENCE = auto()


@dataclass
class Protocol:
    """A mastery protocol"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Identity
    name: str = ""
    description: str = ""

    # Phases
    current_phase: ProtocolPhase = ProtocolPhase.INITIALIZATION
    phases: List[ProtocolPhase] = field(default_factory=list)

    # Progress
    progress: float = 0.0
    phase_progress: Dict[ProtocolPhase, float] = field(default_factory=dict)

    # Requirements
    prerequisites: List[str] = field(default_factory=list)

    # Actions
    actions: List[Dict[str, Any]] = field(default_factory=list)

    # Status
    is_active: bool = False
    is_complete: bool = False

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def start(self):
        """Start protocol"""
        self.is_active = True
        self.started_at = datetime.now()
        self.current_phase = self.phases[0] if self.phases else ProtocolPhase.INITIALIZATION

    def advance_phase(self) -> bool:
        """Advance to next phase"""
        if not self.phases:
            return False

        try:
            idx = self.phases.index(self.current_phase)
            if idx < len(self.phases) - 1:
                self.current_phase = self.phases[idx + 1]
                return True
        except ValueError:
            pass

        return False

    def complete(self):
        """Complete protocol"""
        self.is_complete = True
        self.is_active = False
        self.completed_at = datetime.now()
        self.progress = 1.0

    def get_duration(self) -> float:
        """Get protocol duration in seconds"""
        if not self.started_at:
            return 0.0

        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()


class MasteryProtocol:
    """
    Protocol for achieving mastery.
    """

    def __init__(self, mastery_core: MasteryCore):
        self.mastery_core = mastery_core

        # Protocols
        self.active_protocols: Dict[str, Protocol] = {}
        self.completed_protocols: List[str] = []

        # Phase actions
        self.phase_actions: Dict[ProtocolPhase, List[Callable]] = {
            phase: [] for phase in ProtocolPhase
        }

    def add_phase_action(
        self,
        phase: ProtocolPhase,
        action: Callable[[], bool]
    ):
        """Add action for phase"""
        self.phase_actions[phase].append(action)

    def create_protocol(
        self,
        name: str,
        phases: List[ProtocolPhase] = None
    ) -> Protocol:
        """Create new protocol"""
        protocol = Protocol(
            name=name,
            phases=phases or list(ProtocolPhase)
        )
        return protocol

    def start_protocol(self, protocol: Protocol) -> bool:
        """Start a protocol"""
        # Check prerequisites
        for prereq in protocol.prerequisites:
            if prereq not in self.completed_protocols:
                return False

        protocol.start()
        self.active_protocols[protocol.id] = protocol

        return True

    def execute_phase(self, protocol_id: str) -> bool:
        """Execute current phase of protocol"""
        protocol = self.active_protocols.get(protocol_id)
        if not protocol:
            return False

        phase = protocol.current_phase
        actions = self.phase_actions.get(phase, [])

        success = True
        for action in actions:
            try:
                result = action()
                if not result:
                    success = False
            except Exception:
                success = False

        if success:
            protocol.phase_progress[phase] = 1.0
            protocol.progress = len([p for p in protocol.phase_progress.values() if p >= 1.0]) / len(protocol.phases)

        return success

    def advance_protocol(self, protocol_id: str) -> bool:
        """Advance protocol to next phase"""
        protocol = self.active_protocols.get(protocol_id)
        if not protocol:
            return False

        if protocol.advance_phase():
            return True
        else:
            # No more phases - complete
            self.complete_protocol(protocol_id)
            return True

    def complete_protocol(self, protocol_id: str):
        """Complete a protocol"""
        protocol = self.active_protocols.get(protocol_id)
        if protocol:
            protocol.complete()
            self.completed_protocols.append(protocol.id)
            del self.active_protocols[protocol_id]

    def run_protocol(self, protocol: Protocol) -> bool:
        """Run full protocol"""
        if not self.start_protocol(protocol):
            return False

        for phase in protocol.phases:
            success = self.execute_phase(protocol.id)
            if not success:
                return False

            if not self.advance_protocol(protocol.id):
                break

        return protocol.is_complete


class EvolutionProtocol:
    """
    Protocol for system evolution.
    """

    def __init__(self, mastery_core: MasteryCore):
        self.mastery_core = mastery_core

        # Evolution stages
        self.evolution_stages: List[Dict[str, Any]] = []

        # Current stage
        self.current_stage: int = 0

        # Evolution requirements
        self.stage_requirements: Dict[int, Dict[str, Any]] = {}

    def define_stage(
        self,
        stage: int,
        requirements: Dict[str, Any],
        transformations: List[Callable]
    ):
        """Define evolution stage"""
        self.stage_requirements[stage] = requirements
        self.evolution_stages.append({
            'stage': stage,
            'requirements': requirements,
            'transformations': transformations
        })

    def can_evolve(self) -> bool:
        """Check if evolution is possible"""
        next_stage = self.current_stage + 1
        requirements = self.stage_requirements.get(next_stage, {})

        # Check mastery level requirement
        min_mastery = requirements.get('min_mastery_level', 0)
        if self.mastery_core.state.overall_mastery.value < min_mastery:
            return False

        # Check capability requirements
        required_caps = requirements.get('capabilities', [])
        for cap_type in required_caps:
            caps = self.mastery_core.get_capabilities_by_type(cap_type)
            if not caps:
                return False

        return True

    def evolve(self) -> bool:
        """Perform evolution"""
        if not self.can_evolve():
            return False

        next_stage = self.current_stage + 1
        stage_def = next((s for s in self.evolution_stages if s['stage'] == next_stage), None)

        if not stage_def:
            return False

        # Apply transformations
        for transform in stage_def['transformations']:
            try:
                transform(self.mastery_core)
            except Exception:
                pass

        self.current_stage = next_stage
        self.mastery_core.evolve()

        return True

    def get_evolution_path(self) -> List[Dict[str, Any]]:
        """Get evolution path"""
        path = []

        for stage in self.evolution_stages:
            status = 'completed' if stage['stage'] <= self.current_stage else 'pending'
            if stage['stage'] == self.current_stage + 1:
                status = 'next'

            path.append({
                'stage': stage['stage'],
                'requirements': stage['requirements'],
                'status': status
            })

        return path


class TranscendenceProtocol:
    """
    Protocol for transcendence.
    """

    def __init__(self, mastery_core: MasteryCore):
        self.mastery_core = mastery_core

        # Transcendence progress
        self.progress: float = 0.0

        # Transcendence gates
        self.gates: List[Dict[str, Any]] = []

        # Gates passed
        self.gates_passed: Set[str] = set()

        # Transcendence state
        self.is_transcending: bool = False
        self.transcendence_achieved: bool = False

    def add_gate(
        self,
        name: str,
        condition: Callable[[], bool],
        reward: Callable[[], None]
    ):
        """Add transcendence gate"""
        self.gates.append({
            'name': name,
            'condition': condition,
            'reward': reward
        })

    def check_gates(self) -> List[str]:
        """Check which gates can be passed"""
        passable = []

        for gate in self.gates:
            if gate['name'] not in self.gates_passed:
                try:
                    if gate['condition']():
                        passable.append(gate['name'])
                except Exception:
                    pass

        return passable

    def pass_gate(self, gate_name: str) -> bool:
        """Pass a gate"""
        gate = next((g for g in self.gates if g['name'] == gate_name), None)

        if not gate:
            return False

        if gate_name in self.gates_passed:
            return False

        try:
            if gate['condition']():
                gate['reward']()
                self.gates_passed.add(gate_name)
                self._update_progress()
                return True
        except Exception:
            pass

        return False

    def _update_progress(self):
        """Update transcendence progress"""
        if not self.gates:
            self.progress = 0.0
        else:
            self.progress = len(self.gates_passed) / len(self.gates)

        if self.progress >= 1.0:
            self.transcendence_achieved = True

    def begin_transcendence(self) -> bool:
        """Begin transcendence process"""
        if self.progress < 1.0:
            return False

        self.is_transcending = True

        # Apply final transcendence
        for cap in self.mastery_core.capabilities.values():
            cap.level = MasteryLevel.TRANSCENDENT
            cap.experience = 1000.0

        self.mastery_core.state.transcendence_progress = 1.0
        self.transcendence_achieved = True

        return True

    def get_transcendence_status(self) -> Dict[str, Any]:
        """Get transcendence status"""
        return {
            'progress': self.progress,
            'gates_total': len(self.gates),
            'gates_passed': len(self.gates_passed),
            'gates_remaining': len(self.gates) - len(self.gates_passed),
            'is_transcending': self.is_transcending,
            'transcendence_achieved': self.transcendence_achieved
        }


# Export all
__all__ = [
    'ProtocolPhase',
    'Protocol',
    'MasteryProtocol',
    'EvolutionProtocol',
    'TranscendenceProtocol',
]
