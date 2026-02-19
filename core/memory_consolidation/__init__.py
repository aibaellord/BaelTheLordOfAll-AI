"""
BAEL Memory Consolidation Engine
==================================

Sleep-based memory consolidation.
Systems consolidation and replay.

"Ba'el dreams to remember." — Ba'el
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
import copy

logger = logging.getLogger("BAEL.MemoryConsolidation")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class SleepStage(Enum):
    """Stages of sleep."""
    WAKE = auto()
    N1 = auto()          # Light sleep
    N2 = auto()          # Sleep spindles, K-complexes
    N3 = auto()          # Slow-wave sleep (SWS)
    REM = auto()         # Rapid eye movement


class MemorySystem(Enum):
    """Memory systems."""
    HIPPOCAMPAL = auto()    # Fast learning, episodic
    NEOCORTICAL = auto()    # Slow learning, semantic
    PROCEDURAL = auto()     # Motor/skill memory


class ConsolidationType(Enum):
    """Types of consolidation."""
    SYNAPTIC = auto()       # Local, hours
    SYSTEMS = auto()        # Hippocampus to cortex, weeks/months


class ReplayType(Enum):
    """Types of memory replay."""
    FORWARD = auto()        # Normal order
    REVERSE = auto()        # Backward
    COMPRESSED = auto()     # Time-compressed


@dataclass
class MemoryTrace:
    """
    A memory trace.
    """
    id: str
    content: Any
    system: MemorySystem
    strength: float
    hippocampal_binding: float
    cortical_integration: float
    replay_count: int = 0
    creation_time: float = field(default_factory=time.time)


@dataclass
class SleepCycle:
    """
    A sleep cycle.
    """
    cycle_number: int
    stages: List[SleepStage]
    duration_minutes: float
    sws_duration: float
    rem_duration: float


@dataclass
class ReplayEvent:
    """
    A replay event during sleep.
    """
    memory_id: str
    sleep_stage: SleepStage
    replay_type: ReplayType
    compression_factor: float
    strength_gain: float


@dataclass
class ConsolidationResult:
    """
    Result of consolidation.
    """
    memories_consolidated: int
    total_replays: int
    strength_gain: float
    cortical_transfer: float


@dataclass
class ConsolidationMetrics:
    """
    Consolidation metrics.
    """
    total_sleep_time: float
    sws_percentage: float
    rem_percentage: float
    consolidation_efficiency: float
    memories_stabilized: int


# ============================================================================
# HIPPOCAMPAL SYSTEM
# ============================================================================

class HippocampalSystem:
    """
    Hippocampal memory system.

    "Ba'el's rapid encoder." — Ba'el
    """

    def __init__(self):
        """Initialize hippocampus."""
        self._traces: Dict[str, MemoryTrace] = {}
        self._trace_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._trace_counter += 1
        return f"trace_{self._trace_counter}"

    def encode(
        self,
        content: Any,
        strength: float = 0.5
    ) -> MemoryTrace:
        """Encode new memory."""
        trace = MemoryTrace(
            id=self._generate_id(),
            content=content,
            system=MemorySystem.HIPPOCAMPAL,
            strength=strength,
            hippocampal_binding=0.9,  # High initially
            cortical_integration=0.1   # Low initially
        )

        self._traces[trace.id] = trace
        return trace

    def get_traces_for_replay(
        self,
        count: int = 5
    ) -> List[MemoryTrace]:
        """Get traces for replay during sleep."""
        # Prioritize recent and emotionally salient
        traces = sorted(
            self._traces.values(),
            key=lambda t: t.strength * (1 / (time.time() - t.creation_time + 1)),
            reverse=True
        )
        return traces[:count]

    def replay_trace(
        self,
        trace: MemoryTrace,
        compression: float = 5.0
    ) -> ReplayEvent:
        """Replay a memory trace."""
        trace.replay_count += 1

        # Strengthen with replay
        strength_gain = 0.02 * compression
        trace.strength = min(1.0, trace.strength + strength_gain)

        # Increase cortical integration
        trace.cortical_integration = min(
            1.0,
            trace.cortical_integration + 0.01
        )

        return ReplayEvent(
            memory_id=trace.id,
            sleep_stage=SleepStage.N3,
            replay_type=ReplayType.COMPRESSED,
            compression_factor=compression,
            strength_gain=strength_gain
        )

    def get_trace(
        self,
        trace_id: str
    ) -> Optional[MemoryTrace]:
        """Get a trace."""
        return self._traces.get(trace_id)

    def transfer_to_cortex(
        self,
        trace: MemoryTrace,
        amount: float = 0.1
    ) -> None:
        """Transfer hippocampal trace to cortex."""
        trace.cortical_integration = min(1.0, trace.cortical_integration + amount)
        trace.hippocampal_binding = max(0.0, trace.hippocampal_binding - amount * 0.5)

        # When fully cortical, change system
        if trace.cortical_integration > 0.8:
            trace.system = MemorySystem.NEOCORTICAL


# ============================================================================
# SLEEP SIMULATOR
# ============================================================================

class SleepSimulator:
    """
    Simulate sleep cycles.

    "Ba'el orchestrates sleep." — Ba'el
    """

    def __init__(self):
        """Initialize simulator."""
        self._lock = threading.RLock()

    def generate_sleep_cycle(
        self,
        cycle_number: int
    ) -> SleepCycle:
        """Generate a sleep cycle."""
        # Early cycles: more SWS, late cycles: more REM
        sws_ratio = 0.4 - (cycle_number * 0.05)
        rem_ratio = 0.15 + (cycle_number * 0.05)

        sws_ratio = max(0.1, sws_ratio)
        rem_ratio = min(0.4, rem_ratio)

        cycle_duration = 90.0  # ~90 min cycle

        sws_duration = cycle_duration * sws_ratio
        rem_duration = cycle_duration * rem_ratio

        # Generate stage sequence
        stages = []
        stages.extend([SleepStage.N1] * 2)
        stages.extend([SleepStage.N2] * 5)
        stages.extend([SleepStage.N3] * int(sws_duration / 5))
        stages.extend([SleepStage.N2] * 3)
        stages.extend([SleepStage.REM] * int(rem_duration / 5))

        return SleepCycle(
            cycle_number=cycle_number,
            stages=stages,
            duration_minutes=cycle_duration,
            sws_duration=sws_duration,
            rem_duration=rem_duration
        )

    def generate_night_sleep(
        self,
        duration_hours: float = 8.0
    ) -> List[SleepCycle]:
        """Generate a full night's sleep."""
        cycles = []
        total_minutes = duration_hours * 60
        elapsed = 0
        cycle_num = 1

        while elapsed < total_minutes:
            cycle = self.generate_sleep_cycle(cycle_num)
            cycles.append(cycle)
            elapsed += cycle.duration_minutes
            cycle_num += 1

        return cycles


# ============================================================================
# CONSOLIDATION ENGINE
# ============================================================================

class MemoryConsolidationEngine:
    """
    Complete memory consolidation engine.

    "Ba'el's sleep-based memory system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._hippocampus = HippocampalSystem()
        self._sleep_sim = SleepSimulator()

        self._replay_events: List[ReplayEvent] = []
        self._sleep_history: List[SleepCycle] = []
        self._consolidation_results: List[ConsolidationResult] = []

        self._lock = threading.RLock()

    # Memory encoding

    def encode_memory(
        self,
        content: Any,
        importance: float = 0.5
    ) -> MemoryTrace:
        """Encode a new memory."""
        return self._hippocampus.encode(content, importance)

    def encode_episode(
        self,
        events: List[Any]
    ) -> List[MemoryTrace]:
        """Encode an episode as multiple traces."""
        traces = []
        for event in events:
            trace = self.encode_memory(event)
            traces.append(trace)
        return traces

    # Sleep consolidation

    def run_consolidation_cycle(
        self,
        cycle: SleepCycle
    ) -> ConsolidationResult:
        """Run consolidation during a sleep cycle."""
        replays = 0
        strength_sum = 0.0
        cortical_sum = 0.0

        # SWS: systems consolidation, hippocampal replay
        sws_stages = [s for s in cycle.stages if s == SleepStage.N3]

        for _ in sws_stages:
            traces = self._hippocampus.get_traces_for_replay(3)

            for trace in traces:
                event = self._hippocampus.replay_trace(trace)
                self._replay_events.append(event)
                replays += 1
                strength_sum += event.strength_gain

                # Transfer to cortex during SWS
                self._hippocampus.transfer_to_cortex(trace, 0.02)
                cortical_sum += 0.02

        # REM: memory integration, emotional processing
        rem_stages = [s for s in cycle.stages if s == SleepStage.REM]

        for _ in rem_stages:
            traces = self._hippocampus.get_traces_for_replay(2)

            for trace in traces:
                # REM replay is different - more integration
                trace.strength = min(1.0, trace.strength + 0.01)
                strength_sum += 0.01

        result = ConsolidationResult(
            memories_consolidated=len(self._hippocampus._traces),
            total_replays=replays,
            strength_gain=strength_sum,
            cortical_transfer=cortical_sum
        )

        self._consolidation_results.append(result)
        return result

    def sleep_night(
        self,
        duration_hours: float = 8.0
    ) -> ConsolidationResult:
        """Simulate a full night's sleep consolidation."""
        cycles = self._sleep_sim.generate_night_sleep(duration_hours)
        self._sleep_history.extend(cycles)

        total_replays = 0
        total_strength = 0.0
        total_cortical = 0.0

        for cycle in cycles:
            result = self.run_consolidation_cycle(cycle)
            total_replays += result.total_replays
            total_strength += result.strength_gain
            total_cortical += result.cortical_transfer

        return ConsolidationResult(
            memories_consolidated=len(self._hippocampus._traces),
            total_replays=total_replays,
            strength_gain=total_strength,
            cortical_transfer=total_cortical
        )

    # Systems consolidation

    def run_systems_consolidation(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """Run systems consolidation over multiple days."""
        results = []

        for day in range(days):
            # Encode some new memories during "day"
            new_memories = random.randint(5, 15)
            for _ in range(new_memories):
                self.encode_memory(f"day_{day}_memory", random.uniform(0.3, 0.7))

            # Sleep consolidation
            sleep_result = self.sleep_night(7.0 + random.uniform(0, 2))
            results.append(sleep_result)

        # Analyze final state
        traces = list(self._hippocampus._traces.values())
        cortical = [t for t in traces if t.cortical_integration > 0.5]

        return {
            'days': days,
            'total_memories': len(traces),
            'cortical_memories': len(cortical),
            'consolidation_progress': len(cortical) / len(traces) if traces else 0
        }

    # Targeted memory reactivation

    def targeted_reactivation(
        self,
        trace_id: str,
        during_stage: SleepStage = SleepStage.N3
    ) -> Optional[ReplayEvent]:
        """Targeted memory reactivation (TMR)."""
        trace = self._hippocampus.get_trace(trace_id)

        if not trace:
            return None

        # TMR is more effective
        event = self._hippocampus.replay_trace(trace, compression=10.0)
        event.sleep_stage = during_stage
        self._replay_events.append(event)

        return event

    # Memory decay without sleep

    def apply_waking_decay(
        self,
        hours: float = 8.0
    ) -> int:
        """Apply decay during waking hours."""
        decay_rate = 0.01 * hours
        decayed = 0

        for trace in self._hippocampus._traces.values():
            trace.strength = max(0.0, trace.strength - decay_rate)
            if trace.strength < 0.1:
                decayed += 1

        return decayed

    # Memory retrieval

    def retrieve(
        self,
        trace_id: str
    ) -> Optional[MemoryTrace]:
        """Retrieve a memory."""
        return self._hippocampus.get_trace(trace_id)

    def recall_test(
        self,
        trace_id: str
    ) -> Tuple[bool, float]:
        """Test recall of a memory."""
        trace = self._hippocampus.get_trace(trace_id)

        if not trace:
            return False, 0.0

        # Recall probability based on strength
        recalled = random.random() < trace.strength
        return recalled, trace.strength

    # Metrics

    def get_metrics(self) -> ConsolidationMetrics:
        """Get consolidation metrics."""
        if not self._sleep_history:
            return ConsolidationMetrics(
                total_sleep_time=0.0,
                sws_percentage=0.0,
                rem_percentage=0.0,
                consolidation_efficiency=0.0,
                memories_stabilized=0
            )

        total_time = sum(c.duration_minutes for c in self._sleep_history)
        total_sws = sum(c.sws_duration for c in self._sleep_history)
        total_rem = sum(c.rem_duration for c in self._sleep_history)

        sws_pct = total_sws / total_time if total_time > 0 else 0
        rem_pct = total_rem / total_time if total_time > 0 else 0

        # Consolidation efficiency from results
        if self._consolidation_results:
            efficiency = sum(
                r.strength_gain for r in self._consolidation_results
            ) / len(self._consolidation_results)
        else:
            efficiency = 0.0

        stabilized = sum(
            1 for t in self._hippocampus._traces.values()
            if t.strength > 0.7
        )

        return ConsolidationMetrics(
            total_sleep_time=total_time,
            sws_percentage=sws_pct,
            rem_percentage=rem_pct,
            consolidation_efficiency=efficiency,
            memories_stabilized=stabilized
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'memories': len(self._hippocampus._traces),
            'sleep_cycles': len(self._sleep_history),
            'replay_events': len(self._replay_events)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_memory_consolidation_engine() -> MemoryConsolidationEngine:
    """Create memory consolidation engine."""
    return MemoryConsolidationEngine()


def demonstrate_sleep_consolidation() -> Dict[str, Any]:
    """Demonstrate sleep-based consolidation."""
    engine = create_memory_consolidation_engine()

    # Encode memories before sleep
    for i in range(10):
        engine.encode_memory(f"experience_{i}", random.uniform(0.4, 0.8))

    # Simulate sleep
    result = engine.sleep_night(8.0)

    metrics = engine.get_metrics()

    return {
        'memories_encoded': 10,
        'replays_during_sleep': result.total_replays,
        'strength_gain': result.strength_gain,
        'cortical_transfer': result.cortical_transfer,
        'sws_percentage': metrics.sws_percentage,
        'interpretation': (
            f'{result.total_replays} replays during sleep, '
            f'{metrics.memories_stabilized} memories stabilized'
        )
    }


def get_consolidation_facts() -> Dict[str, str]:
    """Get facts about memory consolidation."""
    return {
        'two_stage': 'Hippocampus encodes fast, cortex learns slow',
        'sws_replay': 'Sharp-wave ripples during slow-wave sleep',
        'compression': 'Replay is 5-20x faster than experience',
        'systems': 'Memories gradually become hippocampus-independent',
        'rem_function': 'Integration, emotional processing, creativity',
        'spindles': 'Sleep spindles coordinate hippocampal-cortical dialogue',
        'tmr': 'Targeted reactivation can enhance specific memories',
        'sleep_deprivation': 'Impairs consolidation and memory formation'
    }
