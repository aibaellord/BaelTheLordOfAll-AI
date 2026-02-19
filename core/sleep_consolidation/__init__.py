"""
BAEL Sleep Consolidation Engine
=================================

Memory enhancement during sleep.
Diekelmann & Born's sleep-memory consolidation.

"Ba'el's memories strengthen in slumber." — Ba'el
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

logger = logging.getLogger("BAEL.SleepConsolidation")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class SleepStage(Enum):
    """Stage of sleep."""
    WAKE = auto()
    N1 = auto()       # Light sleep
    N2 = auto()       # Sleep spindles
    N3 = auto()       # Slow wave sleep (SWS)
    REM = auto()      # Rapid eye movement


class MemoryType(Enum):
    """Type of memory."""
    DECLARATIVE = auto()      # Facts and episodes
    PROCEDURAL = auto()       # Skills
    EMOTIONAL = auto()        # Emotional memories


class ConsolidationType(Enum):
    """Type of consolidation process."""
    STABILIZATION = auto()    # Resistance to interference
    ENHANCEMENT = auto()      # Improvement without practice
    INTEGRATION = auto()      # Schema integration


@dataclass
class Memory:
    """
    A memory trace.
    """
    id: str
    content: str
    memory_type: MemoryType
    encoding_strength: float
    stability: float
    emotional_salience: float


@dataclass
class SleepCycle:
    """
    A sleep cycle.
    """
    cycle_number: int
    stages: List[SleepStage]
    duration_minutes: float
    spindle_density: float
    sws_proportion: float
    rem_proportion: float


@dataclass
class ConsolidationResult:
    """
    Result of sleep consolidation.
    """
    memory_id: str
    pre_sleep_strength: float
    post_sleep_strength: float
    enhancement: float
    stabilization_gain: float


@dataclass
class SleepConsolidationMetrics:
    """
    Sleep consolidation metrics.
    """
    sleep_benefit: float
    wake_control: float
    consolidation_effect: float
    sws_correlation: float
    spindle_correlation: float


# ============================================================================
# ACTIVE SYSTEM CONSOLIDATION MODEL
# ============================================================================

class ActiveSystemConsolidationModel:
    """
    Active system consolidation model.

    "Ba'el's hippocampal replay." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Stage-specific consolidation effects
        self._sws_declarative_boost = 0.25
        self._sws_stabilization = 0.3

        self._rem_procedural_boost = 0.2
        self._rem_emotional_boost = 0.25

        self._n2_spindle_boost = 0.15

        # Hippocampal replay parameters
        self._replay_enhancement = 0.15
        self._integration_rate = 0.1

        # Baseline forgetting (wake)
        self._wake_decay_rate = 0.1

        self._lock = threading.RLock()

    def calculate_stage_contribution(
        self,
        memory: Memory,
        stage: SleepStage,
        duration_minutes: float
    ) -> Dict[str, float]:
        """Calculate consolidation contribution from a sleep stage."""
        enhancement = 0.0
        stabilization = 0.0

        normalized_duration = duration_minutes / 30  # ~30 min stages

        if stage == SleepStage.N3:  # SWS
            if memory.memory_type == MemoryType.DECLARATIVE:
                enhancement += self._sws_declarative_boost * normalized_duration
                stabilization += self._sws_stabilization * normalized_duration
            elif memory.memory_type == MemoryType.EMOTIONAL:
                enhancement += self._sws_declarative_boost * 0.7 * normalized_duration
                stabilization += self._sws_stabilization * normalized_duration
            else:
                enhancement += self._sws_declarative_boost * 0.3 * normalized_duration

        elif stage == SleepStage.REM:
            if memory.memory_type == MemoryType.PROCEDURAL:
                enhancement += self._rem_procedural_boost * normalized_duration
            elif memory.memory_type == MemoryType.EMOTIONAL:
                enhancement += self._rem_emotional_boost * normalized_duration
                # REM helps process emotional content
                stabilization += 0.1 * normalized_duration * memory.emotional_salience
            else:
                enhancement += self._rem_procedural_boost * 0.3 * normalized_duration

        elif stage == SleepStage.N2:
            # Sleep spindles help consolidation
            enhancement += self._n2_spindle_boost * normalized_duration
            stabilization += 0.1 * normalized_duration

        return {
            'enhancement': enhancement,
            'stabilization': stabilization
        }

    def calculate_full_night_consolidation(
        self,
        memory: Memory,
        cycles: List[SleepCycle]
    ) -> Dict[str, float]:
        """Calculate consolidation across a full night of sleep."""
        total_enhancement = 0.0
        total_stabilization = 0.0

        for cycle in cycles:
            for stage in cycle.stages:
                # Approximate stage duration
                if stage == SleepStage.N3:
                    duration = cycle.duration_minutes * cycle.sws_proportion
                elif stage == SleepStage.REM:
                    duration = cycle.duration_minutes * cycle.rem_proportion
                else:
                    duration = cycle.duration_minutes * 0.2  # Approximate

                contribution = self.calculate_stage_contribution(
                    memory, stage, duration
                )

                total_enhancement += contribution['enhancement']
                total_stabilization += contribution['stabilization']

            # Later cycles have more REM, less SWS
            # Early night: SWS-rich (good for declarative)
            # Late night: REM-rich (good for procedural/emotional)

        # Hippocampal replay bonus
        total_enhancement += self._replay_enhancement

        return {
            'enhancement': min(0.5, total_enhancement),
            'stabilization': min(0.5, total_stabilization)
        }

    def calculate_wake_forgetting(
        self,
        memory: Memory,
        hours: float
    ) -> float:
        """Calculate forgetting during wake interval."""
        decay = self._wake_decay_rate * (hours / 8)  # Normalized to 8 hours

        # Stronger memories decay less
        decay *= (1 - memory.stability * 0.3)

        return min(0.3, decay)


# ============================================================================
# SLEEP CONSOLIDATION SYSTEM
# ============================================================================

class SleepConsolidationSystem:
    """
    Sleep consolidation experimental system.

    "Ba'el's sleep memory system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = ActiveSystemConsolidationModel()

        self._memories: Dict[str, Memory] = {}
        self._cycles: List[SleepCycle] = []
        self._results: List[ConsolidationResult] = []

        self._memory_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._memory_counter += 1
        return f"memory_{self._memory_counter}"

    def encode_memory(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.DECLARATIVE,
        emotional_salience: float = 0.3
    ) -> Memory:
        """Encode a memory."""
        memory = Memory(
            id=self._generate_id(),
            content=content,
            memory_type=memory_type,
            encoding_strength=random.uniform(0.4, 0.7),
            stability=random.uniform(0.3, 0.6),
            emotional_salience=emotional_salience
        )

        self._memories[memory.id] = memory

        return memory

    def generate_sleep_night(
        self,
        total_hours: float = 8.0,
        n_cycles: int = 5
    ) -> List[SleepCycle]:
        """Generate a typical night of sleep."""
        cycles = []

        cycle_duration = (total_hours * 60) / n_cycles

        for i in range(n_cycles):
            # Early night: more SWS, less REM
            # Late night: less SWS, more REM
            sws_prop = 0.25 * (1 - i / n_cycles)  # Decreases
            rem_prop = 0.1 + 0.15 * (i / n_cycles)  # Increases

            stages = [SleepStage.N1, SleepStage.N2, SleepStage.N3, SleepStage.N2, SleepStage.REM]

            cycle = SleepCycle(
                cycle_number=i + 1,
                stages=stages,
                duration_minutes=cycle_duration,
                spindle_density=random.uniform(0.5, 1.5),
                sws_proportion=sws_prop,
                rem_proportion=rem_prop
            )

            cycles.append(cycle)

        self._cycles = cycles
        return cycles

    def run_sleep_consolidation(
        self,
        memory_id: str
    ) -> ConsolidationResult:
        """Run sleep consolidation on a memory."""
        memory = self._memories.get(memory_id)
        if not memory:
            return None

        if not self._cycles:
            self.generate_sleep_night()

        pre_strength = memory.encoding_strength

        # Calculate consolidation
        consolidation = self._model.calculate_full_night_consolidation(
            memory, self._cycles
        )

        # Apply consolidation
        memory.encoding_strength = min(0.95,
            memory.encoding_strength + consolidation['enhancement']
        )
        memory.stability = min(0.95,
            memory.stability + consolidation['stabilization']
        )

        result = ConsolidationResult(
            memory_id=memory_id,
            pre_sleep_strength=pre_strength,
            post_sleep_strength=memory.encoding_strength,
            enhancement=consolidation['enhancement'],
            stabilization_gain=consolidation['stabilization']
        )

        self._results.append(result)

        return result

    def run_wake_decay(
        self,
        memory_id: str,
        hours: float
    ) -> float:
        """Run wake decay on a memory."""
        memory = self._memories.get(memory_id)
        if not memory:
            return 0

        decay = self._model.calculate_wake_forgetting(memory, hours)

        memory.encoding_strength = max(0.1, memory.encoding_strength - decay)

        return decay


# ============================================================================
# SLEEP CONSOLIDATION PARADIGM
# ============================================================================

class SleepConsolidationParadigm:
    """
    Sleep consolidation experimental paradigm.

    "Ba'el's sleep memory study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_sleep_vs_wake_comparison(
        self,
        n_items: int = 20
    ) -> Dict[str, Any]:
        """Compare sleep vs wake retention."""
        # Sleep condition
        sleep_system = SleepConsolidationSystem()
        sleep_initial = []
        sleep_final = []

        for i in range(n_items):
            memory = sleep_system.encode_memory(f"item_{i}")
            sleep_initial.append(memory.encoding_strength)

            sleep_system.generate_sleep_night(8)
            result = sleep_system.run_sleep_consolidation(memory.id)
            sleep_final.append(result.post_sleep_strength)

        # Wake condition
        wake_system = SleepConsolidationSystem()
        wake_initial = []
        wake_final = []

        for i in range(n_items):
            memory = wake_system.encode_memory(f"item_{i}")
            wake_initial.append(memory.encoding_strength)

            wake_system.run_wake_decay(memory.id, 8)
            wake_final.append(memory.encoding_strength)

        sleep_change = sum(sleep_final) / n_items - sum(sleep_initial) / n_items
        wake_change = sum(wake_final) / n_items - sum(wake_initial) / n_items

        return {
            'sleep_initial': sum(sleep_initial) / n_items,
            'sleep_final': sum(sleep_final) / n_items,
            'sleep_change': sleep_change,
            'wake_initial': sum(wake_initial) / n_items,
            'wake_final': sum(wake_final) / n_items,
            'wake_change': wake_change,
            'sleep_benefit': sleep_change - wake_change
        }

    def run_memory_type_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare consolidation across memory types."""
        results = {}

        for mem_type in MemoryType:
            system = SleepConsolidationSystem()

            initial = []
            final = []

            for i in range(10):
                memory = system.encode_memory(f"item_{i}", mem_type)
                initial.append(memory.encoding_strength)

                system.generate_sleep_night(8)
                result = system.run_sleep_consolidation(memory.id)
                final.append(result.post_sleep_strength)

            enhancement = sum(final) / 10 - sum(initial) / 10

            results[mem_type.name] = {
                'initial': sum(initial) / 10,
                'final': sum(final) / 10,
                'enhancement': enhancement
            }

        return results

    def run_nap_study(
        self
    ) -> Dict[str, Any]:
        """Study effects of a short nap."""
        nap_system = SleepConsolidationSystem()
        no_nap_system = SleepConsolidationSystem()

        # Encode memories
        nap_memories = []
        no_nap_memories = []

        for i in range(10):
            nap_mem = nap_system.encode_memory(f"item_{i}")
            no_nap_mem = no_nap_system.encode_memory(f"item_{i}")
            nap_memories.append(nap_mem)
            no_nap_memories.append(no_nap_mem)

        # Nap condition: 90 min nap (1 cycle)
        nap_cycles = nap_system.generate_sleep_night(1.5, 1)

        nap_results = []
        for mem in nap_memories:
            result = nap_system.run_sleep_consolidation(mem.id)
            nap_results.append(result.post_sleep_strength)

        # No nap: wake interval
        for mem in no_nap_memories:
            no_nap_system.run_wake_decay(mem.id, 1.5)

        no_nap_results = [mem.encoding_strength for mem in no_nap_memories]

        return {
            'nap_retention': sum(nap_results) / 10,
            'no_nap_retention': sum(no_nap_results) / 10,
            'nap_benefit': (sum(nap_results) - sum(no_nap_results)) / 10,
            'interpretation': 'Even short naps can provide consolidation benefits'
        }

    def run_sleep_architecture_analysis(
        self
    ) -> Dict[str, Any]:
        """Analyze role of different sleep stages."""
        system = SleepConsolidationSystem()

        memory = system.encode_memory("test", MemoryType.DECLARATIVE)

        # Analyze stage contributions
        stage_contributions = {}

        for stage in SleepStage:
            if stage == SleepStage.WAKE:
                continue

            contribution = system._model.calculate_stage_contribution(
                memory, stage, 30  # 30 minute stage
            )
            stage_contributions[stage.name] = contribution

        return {
            'stage_contributions': stage_contributions,
            'sws_for_declarative': 'SWS most important for declarative memories',
            'rem_for_procedural': 'REM most important for procedural and emotional',
            'spindles': 'Sleep spindles (N2) predict consolidation'
        }

    def run_targeted_memory_reactivation(
        self
    ) -> Dict[str, Any]:
        """Simulate targeted memory reactivation (TMR)."""
        # TMR: Cueing specific memories during sleep enhances them

        cued_system = SleepConsolidationSystem()
        uncued_system = SleepConsolidationSystem()

        # Encode memories
        for i in range(10):
            cued_system.encode_memory(f"item_{i}")
            uncued_system.encode_memory(f"item_{i}")

        # Generate sleep
        cued_system.generate_sleep_night(8)
        uncued_system.generate_sleep_night(8)

        # Cued condition gets extra boost (TMR)
        cued_results = []
        for mem_id in cued_system._memories:
            result = cued_system.run_sleep_consolidation(mem_id)
            # TMR bonus
            cued_system._memories[mem_id].encoding_strength += 0.1
            cued_results.append(cued_system._memories[mem_id].encoding_strength)

        uncued_results = []
        for mem_id in uncued_system._memories:
            result = uncued_system.run_sleep_consolidation(mem_id)
            uncued_results.append(result.post_sleep_strength)

        return {
            'cued_retention': sum(cued_results) / 10,
            'uncued_retention': sum(uncued_results) / 10,
            'tmr_benefit': (sum(cued_results) - sum(uncued_results)) / 10,
            'interpretation': 'Cuing memories during sleep enhances consolidation'
        }


# ============================================================================
# SLEEP CONSOLIDATION ENGINE
# ============================================================================

class SleepConsolidationEngine:
    """
    Complete sleep consolidation engine.

    "Ba'el's sleep memory engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = SleepConsolidationParadigm()
        self._system = SleepConsolidationSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Memory management

    def encode(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.DECLARATIVE
    ) -> Memory:
        """Encode a memory."""
        return self._system.encode_memory(content, memory_type)

    def sleep(
        self,
        hours: float = 8.0
    ) -> List[SleepCycle]:
        """Generate sleep cycles."""
        return self._system.generate_sleep_night(hours)

    def consolidate(
        self,
        memory_id: str
    ) -> ConsolidationResult:
        """Consolidate a memory during sleep."""
        return self._system.run_sleep_consolidation(memory_id)

    def wake_decay(
        self,
        memory_id: str,
        hours: float
    ) -> float:
        """Apply wake decay."""
        return self._system.run_wake_decay(memory_id, hours)

    # Experiments

    def compare_sleep_wake(
        self,
        n_items: int = 20
    ) -> Dict[str, Any]:
        """Compare sleep vs wake."""
        result = self._paradigm.run_sleep_vs_wake_comparison(n_items)
        self._experiment_results.append(result)
        return result

    def compare_memory_types(
        self
    ) -> Dict[str, Any]:
        """Compare memory types."""
        return self._paradigm.run_memory_type_comparison()

    def study_nap(
        self
    ) -> Dict[str, Any]:
        """Study nap effects."""
        return self._paradigm.run_nap_study()

    def analyze_architecture(
        self
    ) -> Dict[str, Any]:
        """Analyze sleep architecture."""
        return self._paradigm.run_sleep_architecture_analysis()

    def study_tmr(
        self
    ) -> Dict[str, Any]:
        """Study targeted memory reactivation."""
        return self._paradigm.run_targeted_memory_reactivation()

    # Analysis

    def get_metrics(self) -> SleepConsolidationMetrics:
        """Get sleep consolidation metrics."""
        if not self._experiment_results:
            self.compare_sleep_wake()

        last = self._experiment_results[-1]

        return SleepConsolidationMetrics(
            sleep_benefit=last['sleep_change'],
            wake_control=last['wake_change'],
            consolidation_effect=last['sleep_benefit'],
            sws_correlation=0.5,  # Typical correlation
            spindle_correlation=0.4
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'memories': len(self._system._memories),
            'cycles': len(self._system._cycles),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_sleep_consolidation_engine() -> SleepConsolidationEngine:
    """Create sleep consolidation engine."""
    return SleepConsolidationEngine()


def demonstrate_sleep_consolidation() -> Dict[str, Any]:
    """Demonstrate sleep consolidation."""
    engine = create_sleep_consolidation_engine()

    # Sleep vs wake comparison
    sleep_wake = engine.compare_sleep_wake(20)

    # Memory type comparison
    types = engine.compare_memory_types()

    # Nap study
    nap = engine.study_nap()

    # Architecture analysis
    architecture = engine.analyze_architecture()

    # TMR study
    tmr = engine.study_tmr()

    return {
        'sleep_vs_wake': {
            'sleep_change': f"{sleep_wake['sleep_change']:.0%}",
            'wake_change': f"{sleep_wake['wake_change']:.0%}",
            'sleep_benefit': f"{sleep_wake['sleep_benefit']:.0%}"
        },
        'by_memory_type': {
            mtype: f"enhancement: {data['enhancement']:.0%}"
            for mtype, data in types.items()
        },
        'nap': {
            'benefit': f"{nap['nap_benefit']:.0%}"
        },
        'sleep_stages': architecture['stage_contributions'],
        'tmr': {
            'benefit': f"{tmr['tmr_benefit']:.0%}"
        },
        'interpretation': (
            f"Sleep benefit: {sleep_wake['sleep_benefit']:.0%}. "
            f"Sleep actively consolidates memories via hippocampal replay."
        )
    }


def get_sleep_consolidation_facts() -> Dict[str, str]:
    """Get facts about sleep consolidation."""
    return {
        'born_diekelmann': 'Active system consolidation theory',
        'hippocampal_replay': 'Memories replayed during SWS',
        'sws_declarative': 'Slow wave sleep consolidates declarative memories',
        'rem_procedural': 'REM sleep consolidates procedural skills',
        'spindles': 'Sleep spindles predict consolidation success',
        'naps_help': 'Even short naps provide consolidation benefits',
        'tmr': 'Cuing during sleep enhances specific memories',
        'emotional': 'Sleep helps process emotional memories'
    }
