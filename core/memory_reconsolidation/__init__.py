"""
BAEL Memory Reconsolidation Engine
====================================

Memories become labile when retrieved.
Nader's reconsolidation paradigm.

"Ba'el knows memories are never fixed." — Ba'el
"""

import logging
import threading
import time
import math
import random
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import defaultdict, deque

logger = logging.getLogger("BAEL.MemoryReconsolidation")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class MemoryState(Enum):
    """State of memory consolidation."""
    LABILE = auto()           # Newly formed, vulnerable
    CONSOLIDATED = auto()     # Stable in long-term
    REACTIVATED = auto()      # Retrieved, temporarily labile
    RECONSOLIDATING = auto()  # Restabilizing
    MODIFIED = auto()         # Changed during reconsolidation
    WEAKENED = auto()         # Disrupted during reconsolidation


class ReactivationType(Enum):
    """How memory is reactivated."""
    DIRECT_CUE = auto()       # Original cue presented
    PARTIAL_CUE = auto()      # Partial reminder
    NOVEL_CONTEXT = auto()    # In new context
    IMAGINED = auto()         # Mentally retrieved


class InterventionType(Enum):
    """Type of intervention during reconsolidation."""
    NONE = auto()
    PHARMACOLOGICAL = auto()   # Protein synthesis inhibitor
    BEHAVIORAL = auto()        # New learning
    EMOTIONAL = auto()         # Stress, arousal
    SLEEP_DEPRIVATION = auto()


@dataclass
class MemoryTrace:
    """
    A memory trace that can be reconsolidated.
    """
    id: str
    content: str
    strength: float           # 0-1
    state: MemoryState
    emotional_intensity: float
    age_hours: float
    modification_count: int = 0


@dataclass
class ReactivationEvent:
    """
    A reactivation of memory.
    """
    memory_id: str
    reactivation_type: ReactivationType
    success: bool
    lability_window_hours: float


@dataclass
class ReconsolidationWindow:
    """
    Time window for reconsolidation.
    """
    memory_id: str
    opens_at: float
    closes_at: float
    is_open: bool
    intervention_applied: Optional[InterventionType] = None


@dataclass
class ReconsolidationMetrics:
    """
    Reconsolidation metrics.
    """
    modification_success_rate: float
    weakening_rate: float
    boundary_condition_met: float
    therapeutic_potential: float


# ============================================================================
# RECONSOLIDATION MODEL
# ============================================================================

class ReconsolidationModel:
    """
    Memory reconsolidation model.

    "Ba'el's memory destabilization." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Reconsolidation window
        self._window_duration_hours = 6.0  # ~6 hour window
        self._window_open_delay = 0.1      # Immediate after reactivation

        # Lability parameters
        self._base_lability = 0.7
        self._age_protection = 0.1    # Older memories more resistant
        self._strength_protection = 0.2

        # Modification parameters
        self._modification_rate = 0.4
        self._weakening_rate = 0.3

        # Boundary conditions
        self._prediction_error_threshold = 0.3  # Need surprise for reconsolidation
        self._minimum_age_hours = 1.0  # Too young = still in consolidation

        self._lock = threading.RLock()

    def can_reactivate(
        self,
        memory: MemoryTrace
    ) -> bool:
        """Check if memory can be reactivated."""
        # Already labile/reactivating
        if memory.state in [MemoryState.LABILE, MemoryState.REACTIVATED]:
            return False

        # Too young (still consolidating)
        if memory.age_hours < self._minimum_age_hours:
            return False

        return True

    def calculate_lability(
        self,
        memory: MemoryTrace,
        prediction_error: float
    ) -> float:
        """Calculate how labile memory becomes upon reactivation."""
        if prediction_error < self._prediction_error_threshold:
            # No prediction error = no reconsolidation
            return 0.0

        lability = self._base_lability

        # Older memories more resistant
        age_factor = 1 / (1 + self._age_protection * memory.age_hours)
        lability *= age_factor

        # Stronger memories more resistant
        strength_factor = 1 - memory.strength * self._strength_protection
        lability *= strength_factor

        # Emotional memories more labile
        lability *= (1 + memory.emotional_intensity * 0.2)

        return max(0, min(1, lability))

    def calculate_window(
        self,
        memory_id: str,
        reactivation_time: float
    ) -> ReconsolidationWindow:
        """Calculate reconsolidation window."""
        opens = reactivation_time + self._window_open_delay
        closes = opens + self._window_duration_hours

        return ReconsolidationWindow(
            memory_id=memory_id,
            opens_at=opens,
            closes_at=closes,
            is_open=True
        )

    def apply_modification(
        self,
        memory: MemoryTrace,
        new_content: str,
        lability: float
    ) -> Tuple[MemoryTrace, bool]:
        """Apply modification during window."""
        if random.random() > lability:
            return memory, False

        if random.random() < self._modification_rate:
            memory.content = new_content
            memory.state = MemoryState.MODIFIED
            memory.modification_count += 1
            return memory, True

        return memory, False

    def apply_disruption(
        self,
        memory: MemoryTrace,
        intervention: InterventionType,
        lability: float
    ) -> Tuple[MemoryTrace, bool]:
        """Apply disruption to weaken memory."""
        if random.random() > lability:
            return memory, False

        disruption_strength = {
            InterventionType.PHARMACOLOGICAL: 0.8,
            InterventionType.BEHAVIORAL: 0.5,
            InterventionType.SLEEP_DEPRIVATION: 0.4,
            InterventionType.EMOTIONAL: 0.3,
            InterventionType.NONE: 0.0
        }

        strength = disruption_strength.get(intervention, 0)

        if random.random() < strength * self._weakening_rate:
            memory.strength *= (1 - strength * 0.5)
            memory.state = MemoryState.WEAKENED
            return memory, True

        return memory, False


# ============================================================================
# RECONSOLIDATION SYSTEM
# ============================================================================

class ReconsolidationSystem:
    """
    Memory reconsolidation system.

    "Ba'el's memory rewriting." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = ReconsolidationModel()

        self._memories: Dict[str, MemoryTrace] = {}
        self._windows: Dict[str, ReconsolidationWindow] = {}
        self._events: List[ReactivationEvent] = []

        self._current_time = 0.0  # Simulated time in hours

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"mem_{self._counter}"

    def advance_time(
        self,
        hours: float
    ):
        """Advance simulated time."""
        self._current_time += hours

        # Update window states
        for window in self._windows.values():
            if window.is_open and self._current_time > window.closes_at:
                window.is_open = False

                # Memory reconsolidates
                memory = self._memories.get(window.memory_id)
                if memory and memory.state == MemoryState.REACTIVATED:
                    memory.state = MemoryState.CONSOLIDATED

    def create_memory(
        self,
        content: str,
        strength: float = 0.8,
        emotional: float = 0.5
    ) -> MemoryTrace:
        """Create a new memory."""
        memory = MemoryTrace(
            id=self._generate_id(),
            content=content,
            strength=strength,
            state=MemoryState.LABILE,
            emotional_intensity=emotional,
            age_hours=0.0
        )

        self._memories[memory.id] = memory

        return memory

    def consolidate_memory(
        self,
        memory_id: str
    ) -> bool:
        """Consolidate a memory (simulate time)."""
        memory = self._memories.get(memory_id)
        if not memory:
            return False

        memory.state = MemoryState.CONSOLIDATED
        memory.age_hours = max(24, memory.age_hours)  # At least 24h

        return True

    def reactivate(
        self,
        memory_id: str,
        reactivation_type: ReactivationType = ReactivationType.DIRECT_CUE,
        prediction_error: float = 0.5
    ) -> Optional[ReconsolidationWindow]:
        """Reactivate a memory."""
        memory = self._memories.get(memory_id)
        if not memory:
            return None

        if not self._model.can_reactivate(memory):
            event = ReactivationEvent(
                memory_id=memory_id,
                reactivation_type=reactivation_type,
                success=False,
                lability_window_hours=0
            )
            self._events.append(event)
            return None

        # Calculate lability
        lability = self._model.calculate_lability(memory, prediction_error)

        if lability > 0:
            memory.state = MemoryState.REACTIVATED

            window = self._model.calculate_window(memory_id, self._current_time)
            self._windows[memory_id] = window

            event = ReactivationEvent(
                memory_id=memory_id,
                reactivation_type=reactivation_type,
                success=True,
                lability_window_hours=window.closes_at - window.opens_at
            )
            self._events.append(event)

            return window

        return None

    def modify_during_window(
        self,
        memory_id: str,
        new_content: str
    ) -> bool:
        """Modify memory during reconsolidation window."""
        memory = self._memories.get(memory_id)
        window = self._windows.get(memory_id)

        if not memory or not window:
            return False

        if not window.is_open:
            return False

        lability = self._model.calculate_lability(memory, 0.5)
        _, success = self._model.apply_modification(memory, new_content, lability)

        return success

    def disrupt_during_window(
        self,
        memory_id: str,
        intervention: InterventionType
    ) -> bool:
        """Disrupt memory during reconsolidation window."""
        memory = self._memories.get(memory_id)
        window = self._windows.get(memory_id)

        if not memory or not window:
            return False

        if not window.is_open:
            return False

        window.intervention_applied = intervention

        lability = self._model.calculate_lability(memory, 0.5)
        _, success = self._model.apply_disruption(memory, intervention, lability)

        return success


# ============================================================================
# RECONSOLIDATION PARADIGM
# ============================================================================

class ReconsolidationParadigm:
    """
    Reconsolidation experimental paradigm.

    "Ba'el's memory destabilization study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_nader_paradigm(
        self,
        n_memories: int = 20
    ) -> Dict[str, Any]:
        """Run Nader-style reconsolidation paradigm."""
        system = ReconsolidationSystem()

        # Create and consolidate memories
        memories = []
        for i in range(n_memories):
            mem = system.create_memory(f"fear_memory_{i}")
            system.consolidate_memory(mem.id)
            memories.append(mem)

        # Split into groups
        mid = len(memories) // 2
        reactivated = memories[:mid]
        control = memories[mid:]

        disrupted = 0

        # Reactivate and disrupt
        for mem in reactivated:
            window = system.reactivate(mem.id, prediction_error=0.6)
            if window:
                success = system.disrupt_during_window(
                    mem.id, InterventionType.PHARMACOLOGICAL
                )
                if success:
                    disrupted += 1

        # Check final states
        reactivated_weakened = sum(
            1 for m in reactivated
            if m.state == MemoryState.WEAKENED
        )
        control_intact = sum(
            1 for m in control
            if m.state == MemoryState.CONSOLIDATED
        )

        return {
            'total_memories': n_memories,
            'reactivated': len(reactivated),
            'disrupted': disrupted,
            'weakened': reactivated_weakened,
            'control_intact': control_intact / len(control),
            'interpretation': 'Reconsolidation allows memory modification'
        }

    def run_boundary_condition_study(
        self
    ) -> Dict[str, Any]:
        """Study boundary conditions for reconsolidation."""
        # Test prediction error requirement
        results = {}

        for prediction_error in [0.0, 0.2, 0.5, 0.8]:
            system = ReconsolidationSystem()

            # Create memories
            reactivated = 0
            for i in range(10):
                mem = system.create_memory(f"memory_{i}")
                system.consolidate_memory(mem.id)

                window = system.reactivate(mem.id, prediction_error=prediction_error)
                if window:
                    reactivated += 1

            results[f"pe_{prediction_error}"] = reactivated / 10

        return {
            'by_prediction_error': results,
            'interpretation': 'Low prediction error prevents reconsolidation'
        }

    def run_therapeutic_paradigm(
        self
    ) -> Dict[str, Any]:
        """Simulate therapeutic application."""
        system = ReconsolidationSystem()

        # Create traumatic memory
        trauma = system.create_memory(
            "traumatic_event",
            strength=0.9,
            emotional=0.95
        )
        system.consolidate_memory(trauma.id)

        # Multiple therapeutic sessions
        sessions = []

        for session_num in range(5):
            original_strength = trauma.strength

            # Reactivate with surprise (new perspective)
            window = system.reactivate(
                trauma.id,
                prediction_error=0.6
            )

            if window:
                # During window, provide corrective information
                success = system.modify_during_window(
                    trauma.id,
                    f"reprocessed_memory_session_{session_num}"
                )

                sessions.append({
                    'session': session_num + 1,
                    'reactivated': True,
                    'modified': success,
                    'strength_before': original_strength,
                    'strength_after': trauma.strength
                })
            else:
                sessions.append({
                    'session': session_num + 1,
                    'reactivated': False
                })

        return {
            'sessions': sessions,
            'final_state': trauma.state.name,
            'final_strength': trauma.strength,
            'modifications': trauma.modification_count,
            'interpretation': 'Reconsolidation enables therapeutic memory updating'
        }

    def run_window_timing_study(
        self
    ) -> Dict[str, Any]:
        """Study timing of interventions."""
        timing_conditions = [0.5, 3.0, 6.0, 10.0]  # Hours after reactivation

        results = {}

        for delay in timing_conditions:
            system = ReconsolidationSystem()

            successful = 0
            for i in range(10):
                mem = system.create_memory(f"memory_{i}")
                system.consolidate_memory(mem.id)

                window = system.reactivate(mem.id, prediction_error=0.5)
                if window:
                    # Wait
                    system.advance_time(delay)

                    # Try to disrupt
                    success = system.disrupt_during_window(
                        mem.id, InterventionType.BEHAVIORAL
                    )
                    if success:
                        successful += 1

            results[f"delay_{delay}h"] = successful / 10

        return {
            'by_delay': results,
            'window_duration': '~6 hours',
            'interpretation': 'Intervention must occur within window'
        }

    def run_emotional_memory_study(
        self
    ) -> Dict[str, Any]:
        """Study reconsolidation of emotional memories."""
        emotional_levels = [0.2, 0.5, 0.8]

        results = {}

        for emotion in emotional_levels:
            system = ReconsolidationSystem()

            lability_scores = []
            for i in range(10):
                mem = system.create_memory(
                    f"memory_{i}",
                    emotional=emotion
                )
                system.consolidate_memory(mem.id)

                # Calculate lability
                lability = system._model.calculate_lability(mem, 0.5)
                lability_scores.append(lability)

            results[f"emotion_{emotion}"] = {
                'avg_lability': sum(lability_scores) / len(lability_scores)
            }

        return {
            'by_emotion': results,
            'interpretation': 'Emotional memories can be more labile'
        }


# ============================================================================
# RECONSOLIDATION ENGINE
# ============================================================================

class MemoryReconsolidationEngine:
    """
    Complete memory reconsolidation engine.

    "Ba'el's memory destabilization engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = ReconsolidationParadigm()
        self._system = ReconsolidationSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Memory management

    def create_memory(
        self,
        content: str,
        strength: float = 0.8,
        emotional: float = 0.5
    ) -> MemoryTrace:
        """Create memory."""
        return self._system.create_memory(content, strength, emotional)

    def consolidate(
        self,
        memory_id: str
    ) -> bool:
        """Consolidate memory."""
        return self._system.consolidate_memory(memory_id)

    def reactivate(
        self,
        memory_id: str,
        prediction_error: float = 0.5
    ) -> Optional[ReconsolidationWindow]:
        """Reactivate memory."""
        return self._system.reactivate(memory_id, prediction_error=prediction_error)

    def modify(
        self,
        memory_id: str,
        new_content: str
    ) -> bool:
        """Modify during window."""
        return self._system.modify_during_window(memory_id, new_content)

    def disrupt(
        self,
        memory_id: str,
        intervention: InterventionType = InterventionType.BEHAVIORAL
    ) -> bool:
        """Disrupt during window."""
        return self._system.disrupt_during_window(memory_id, intervention)

    def advance_time(
        self,
        hours: float
    ):
        """Advance time."""
        self._system.advance_time(hours)

    # Experiments

    def run_nader(
        self
    ) -> Dict[str, Any]:
        """Run Nader paradigm."""
        result = self._paradigm.run_nader_paradigm()
        self._experiment_results.append(result)
        return result

    def study_boundary_conditions(
        self
    ) -> Dict[str, Any]:
        """Study boundary conditions."""
        return self._paradigm.run_boundary_condition_study()

    def run_therapeutic(
        self
    ) -> Dict[str, Any]:
        """Run therapeutic paradigm."""
        return self._paradigm.run_therapeutic_paradigm()

    def study_timing(
        self
    ) -> Dict[str, Any]:
        """Study window timing."""
        return self._paradigm.run_window_timing_study()

    def study_emotion(
        self
    ) -> Dict[str, Any]:
        """Study emotional memories."""
        return self._paradigm.run_emotional_memory_study()

    # Analysis

    def get_metrics(self) -> ReconsolidationMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_nader()

        last = self._experiment_results[-1]

        return ReconsolidationMetrics(
            modification_success_rate=last['disrupted'] / max(1, last['reactivated']),
            weakening_rate=last['weakened'] / max(1, last['reactivated']),
            boundary_condition_met=0.7,
            therapeutic_potential=0.6
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'memories': len(self._system._memories),
            'windows': len(self._system._windows),
            'events': len(self._system._events)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_memory_reconsolidation_engine() -> MemoryReconsolidationEngine:
    """Create memory reconsolidation engine."""
    return MemoryReconsolidationEngine()


def demonstrate_memory_reconsolidation() -> Dict[str, Any]:
    """Demonstrate memory reconsolidation."""
    engine = create_memory_reconsolidation_engine()

    # Nader paradigm
    nader = engine.run_nader()

    # Boundary conditions
    boundaries = engine.study_boundary_conditions()

    # Therapeutic
    therapeutic = engine.run_therapeutic()

    # Timing
    timing = engine.study_timing()

    return {
        'nader_paradigm': {
            'reactivated': nader['reactivated'],
            'disrupted': nader['disrupted'],
            'weakened': nader['weakened'],
            'control_intact': f"{nader['control_intact']:.0%}"
        },
        'boundary_conditions': {
            k: f"{v:.0%}"
            for k, v in boundaries['by_prediction_error'].items()
        },
        'therapeutic': {
            'sessions': len(therapeutic['sessions']),
            'modifications': therapeutic['modifications'],
            'final_strength': f"{therapeutic['final_strength']:.0%}"
        },
        'interpretation': (
            f"Reconsolidation allows memory modification. "
            f"Disrupted: {nader['disrupted']}/{nader['reactivated']}. "
            f"Requires prediction error and window timing."
        )
    }


def get_memory_reconsolidation_facts() -> Dict[str, str]:
    """Get facts about memory reconsolidation."""
    return {
        'nader_2000': 'Reconsolidation discovered in fear memories',
        'window': '~6 hour window after reactivation',
        'prediction_error': 'Required for reconsolidation to occur',
        'lability': 'Memory becomes temporarily modifiable',
        'therapeutic': 'Potential for PTSD treatment',
        'boundary_conditions': 'Strong, old memories more resistant',
        'applications': 'Therapy, addiction treatment',
        'controversy': 'Ecological validity debated'
    }
