"""
BAEL Reality Monitoring Engine
================================

Distinguishing real from imagined.
Johnson's reality monitoring framework.

"Ba'el knows what was real and what was dreamed." — Ba'el
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

logger = logging.getLogger("BAEL.RealityMonitoring")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class MemorySource(Enum):
    """Source of memory."""
    PERCEIVED = auto()      # Actually experienced
    IMAGINED = auto()       # Mentally generated
    DREAMED = auto()        # From dreams
    TOLD = auto()           # Heard from others


class AttributedSource(Enum):
    """Attributed (judged) source."""
    REAL = auto()           # Judged as really happened
    IMAGINED = auto()       # Judged as imagined
    UNCERTAIN = auto()


class QualitativeCharacteristic(Enum):
    """Memory characteristics for monitoring."""
    SENSORY_DETAIL = auto()
    CONTEXTUAL_INFO = auto()
    COGNITIVE_OPERATIONS = auto()
    EMOTIONAL_INTENSITY = auto()


@dataclass
class MemoryRecord:
    """
    A memory record with source characteristics.
    """
    id: str
    content: str
    true_source: MemorySource
    sensory_detail: float      # 0-1
    contextual_info: float     # 0-1
    cognitive_operations: float  # 0-1 (higher = more effortful)
    emotional_intensity: float  # 0-1
    plausibility: float        # 0-1


@dataclass
class RealityJudgment:
    """
    A reality monitoring judgment.
    """
    memory_id: str
    true_source: MemorySource
    attributed_source: AttributedSource
    confidence: float
    correct: bool


@dataclass
class RealityMonitoringMetrics:
    """
    Reality monitoring metrics.
    """
    accuracy: float
    perceived_hit_rate: float
    imagined_correct_rejection: float
    false_alarm_rate: float
    miss_rate: float


# ============================================================================
# REALITY MONITORING MODEL
# ============================================================================

class RealityMonitoringModel:
    """
    Johnson's reality monitoring model.

    "Ba'el's source discrimination." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Characteristic weights for reality judgment
        self._sensory_weight = 0.35
        self._context_weight = 0.25
        self._cognitive_weight = -0.30  # Higher cognitive ops = more likely imagined
        self._plausibility_weight = 0.10

        # Thresholds
        self._real_threshold = 0.55
        self._imagined_threshold = 0.45

        # Noise in judgment
        self._judgment_noise = 0.1

        self._lock = threading.RLock()

    def calculate_reality_score(
        self,
        memory: MemoryRecord
    ) -> float:
        """Calculate likelihood memory is from external source."""
        score = 0.5  # Base

        # High sensory detail → more likely real
        score += memory.sensory_detail * self._sensory_weight

        # High contextual info → more likely real
        score += memory.contextual_info * self._context_weight

        # High cognitive operations → more likely imagined
        score += memory.cognitive_operations * self._cognitive_weight

        # Plausibility
        score += memory.plausibility * self._plausibility_weight

        # Add noise
        score += random.uniform(-self._judgment_noise, self._judgment_noise)

        return max(0, min(1, score))

    def make_judgment(
        self,
        memory: MemoryRecord
    ) -> Tuple[AttributedSource, float]:
        """Make reality monitoring judgment."""
        reality_score = self.calculate_reality_score(memory)

        if reality_score >= self._real_threshold:
            attribution = AttributedSource.REAL
            confidence = (reality_score - self._real_threshold) / (1 - self._real_threshold)
        elif reality_score <= self._imagined_threshold:
            attribution = AttributedSource.IMAGINED
            confidence = (self._imagined_threshold - reality_score) / self._imagined_threshold
        else:
            attribution = AttributedSource.UNCERTAIN
            confidence = 0.3

        return attribution, min(1, confidence + 0.3)

    def is_correct(
        self,
        true_source: MemorySource,
        attributed: AttributedSource
    ) -> bool:
        """Check if attribution is correct."""
        if true_source == MemorySource.PERCEIVED:
            return attributed == AttributedSource.REAL
        elif true_source in [MemorySource.IMAGINED, MemorySource.DREAMED]:
            return attributed == AttributedSource.IMAGINED
        elif true_source == MemorySource.TOLD:
            # Told events are tricky - could be judged either way
            return attributed in [AttributedSource.REAL, AttributedSource.IMAGINED]
        return False


# ============================================================================
# REALITY MONITORING SYSTEM
# ============================================================================

class RealityMonitoringSystem:
    """
    Reality monitoring simulation system.

    "Ba'el's real/imagined discrimination." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = RealityMonitoringModel()

        self._memories: Dict[str, MemoryRecord] = {}
        self._judgments: List[RealityJudgment] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"mem_{self._counter}"

    def create_perceived_memory(
        self,
        content: str
    ) -> MemoryRecord:
        """Create a memory from perception."""
        memory = MemoryRecord(
            id=self._generate_id(),
            content=content,
            true_source=MemorySource.PERCEIVED,
            sensory_detail=random.uniform(0.6, 0.9),   # High sensory
            contextual_info=random.uniform(0.5, 0.8),  # Good context
            cognitive_operations=random.uniform(0.1, 0.3),  # Low cognitive ops
            emotional_intensity=random.uniform(0.3, 0.7),
            plausibility=random.uniform(0.7, 1.0)
        )

        self._memories[memory.id] = memory

        return memory

    def create_imagined_memory(
        self,
        content: str
    ) -> MemoryRecord:
        """Create a memory from imagination."""
        memory = MemoryRecord(
            id=self._generate_id(),
            content=content,
            true_source=MemorySource.IMAGINED,
            sensory_detail=random.uniform(0.2, 0.5),   # Lower sensory
            contextual_info=random.uniform(0.2, 0.5),  # Less context
            cognitive_operations=random.uniform(0.5, 0.8),  # High cognitive ops
            emotional_intensity=random.uniform(0.2, 0.6),
            plausibility=random.uniform(0.4, 0.8)
        )

        self._memories[memory.id] = memory

        return memory

    def create_dreamed_memory(
        self,
        content: str
    ) -> MemoryRecord:
        """Create a memory from a dream."""
        memory = MemoryRecord(
            id=self._generate_id(),
            content=content,
            true_source=MemorySource.DREAMED,
            sensory_detail=random.uniform(0.4, 0.7),   # Variable sensory
            contextual_info=random.uniform(0.2, 0.4),  # Fragmented context
            cognitive_operations=random.uniform(0.3, 0.6),
            emotional_intensity=random.uniform(0.4, 0.9),
            plausibility=random.uniform(0.2, 0.6)  # Often implausible
        )

        self._memories[memory.id] = memory

        return memory

    def judge_memory(
        self,
        memory_id: str
    ) -> RealityJudgment:
        """Judge source of a memory."""
        memory = self._memories.get(memory_id)
        if not memory:
            return None

        attributed, confidence = self._model.make_judgment(memory)
        correct = self._model.is_correct(memory.true_source, attributed)

        judgment = RealityJudgment(
            memory_id=memory_id,
            true_source=memory.true_source,
            attributed_source=attributed,
            confidence=confidence,
            correct=correct
        )

        self._judgments.append(judgment)

        return judgment


# ============================================================================
# REALITY MONITORING PARADIGM
# ============================================================================

class RealityMonitoringParadigm:
    """
    Reality monitoring experimental paradigm.

    "Ba'el's source attribution study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_basic_paradigm(
        self,
        n_perceived: int = 20,
        n_imagined: int = 20
    ) -> Dict[str, Any]:
        """Run basic reality monitoring paradigm."""
        system = RealityMonitoringSystem()

        # Create memories
        perceived = []
        imagined = []

        for i in range(n_perceived):
            mem = system.create_perceived_memory(f"perceived_{i}")
            perceived.append(mem)

        for i in range(n_imagined):
            mem = system.create_imagined_memory(f"imagined_{i}")
            imagined.append(mem)

        # Judge all
        perceived_hits = 0
        perceived_misses = 0
        imagined_correct = 0
        imagined_false_alarm = 0

        for mem in perceived:
            judgment = system.judge_memory(mem.id)
            if judgment.attributed_source == AttributedSource.REAL:
                perceived_hits += 1
            else:
                perceived_misses += 1

        for mem in imagined:
            judgment = system.judge_memory(mem.id)
            if judgment.attributed_source == AttributedSource.IMAGINED:
                imagined_correct += 1
            elif judgment.attributed_source == AttributedSource.REAL:
                imagined_false_alarm += 1

        return {
            'perceived_hit_rate': perceived_hits / n_perceived,
            'perceived_miss_rate': perceived_misses / n_perceived,
            'imagined_correct_rejection': imagined_correct / n_imagined,
            'imagined_false_alarm': imagined_false_alarm / n_imagined,
            'overall_accuracy': (perceived_hits + imagined_correct) / (n_perceived + n_imagined)
        }

    def run_vividness_manipulation(
        self
    ) -> Dict[str, Any]:
        """Manipulate vividness of imagined events."""
        results = {}

        for condition, sensory_boost in [('low_vivid', 0.0), ('high_vivid', 0.4)]:
            system = RealityMonitoringSystem()

            # Create vivid vs non-vivid imagined memories
            imagined = []
            for i in range(20):
                mem = system.create_imagined_memory(f"imagined_{i}")
                mem.sensory_detail += sensory_boost  # Boost vividness
                mem.sensory_detail = min(1.0, mem.sensory_detail)
                imagined.append(mem)

            # Judge
            false_alarms = 0
            for mem in imagined:
                judgment = system.judge_memory(mem.id)
                if judgment.attributed_source == AttributedSource.REAL:
                    false_alarms += 1

            results[condition] = {
                'false_alarm_rate': false_alarms / 20,
                'avg_sensory': sum(m.sensory_detail for m in imagined) / 20
            }

        return results

    def run_repeated_imagination_study(
        self
    ) -> Dict[str, Any]:
        """Study how repeated imagination creates false memories."""
        system = RealityMonitoringSystem()

        # Initially imagined events
        imagined_events = []
        for i in range(15):
            mem = system.create_imagined_memory(f"imagined_{i}")
            imagined_events.append(mem)

        # Simulate repeated imagination (increases sensory/context)
        for mem in imagined_events:
            # Repeated imagination increases sensory detail
            mem.sensory_detail += random.uniform(0.1, 0.3)
            mem.sensory_detail = min(0.9, mem.sensory_detail)
            mem.contextual_info += random.uniform(0.1, 0.2)
            mem.contextual_info = min(0.8, mem.contextual_info)

        # Judge after repeated imagination
        false_alarms = 0
        for mem in imagined_events:
            judgment = system.judge_memory(mem.id)
            if judgment.attributed_source == AttributedSource.REAL:
                false_alarms += 1

        return {
            'false_alarm_rate_after_imagination': false_alarms / len(imagined_events),
            'interpretation': 'Repeated imagination increases sensory detail, creating source confusion'
        }

    def run_dream_confusion_study(
        self
    ) -> Dict[str, Any]:
        """Study confusion between dreams and reality."""
        system = RealityMonitoringSystem()

        # Create dream memories
        dreams = []
        for i in range(20):
            mem = system.create_dreamed_memory(f"dream_{i}")
            dreams.append(mem)

        # Judge
        judged_real = 0
        judged_imagined = 0
        uncertain = 0

        for mem in dreams:
            judgment = system.judge_memory(mem.id)
            if judgment.attributed_source == AttributedSource.REAL:
                judged_real += 1
            elif judgment.attributed_source == AttributedSource.IMAGINED:
                judged_imagined += 1
            else:
                uncertain += 1

        return {
            'dreams_judged_real': judged_real / len(dreams),
            'dreams_judged_imagined': judged_imagined / len(dreams),
            'dreams_uncertain': uncertain / len(dreams),
            'interpretation': 'Dreams can be confused with reality due to sensory vividness'
        }

    def run_aging_study(
        self
    ) -> Dict[str, Any]:
        """Study age-related changes in reality monitoring."""
        conditions = {
            'young': {'sensory_noise': 0.1, 'judgment_noise': 0.1},
            'older': {'sensory_noise': 0.2, 'judgment_noise': 0.2}
        }

        results = {}

        for age, params in conditions.items():
            system = RealityMonitoringSystem()
            system._model._judgment_noise = params['judgment_noise']

            # Create memories with increased noise for older
            perceived = []
            imagined = []

            for i in range(15):
                mem = system.create_perceived_memory(f"perc_{i}")
                # Add sensory noise
                mem.sensory_detail -= random.uniform(0, params['sensory_noise'])
                mem.sensory_detail = max(0.2, mem.sensory_detail)
                perceived.append(mem)

            for i in range(15):
                mem = system.create_imagined_memory(f"imag_{i}")
                imagined.append(mem)

            # Judge
            correct = 0
            total = len(perceived) + len(imagined)

            for mem in perceived:
                j = system.judge_memory(mem.id)
                if j.correct:
                    correct += 1

            for mem in imagined:
                j = system.judge_memory(mem.id)
                if j.correct:
                    correct += 1

            results[age] = {
                'accuracy': correct / total,
                'interpretation': 'Reality monitoring declines with age'
            }

        return results


# ============================================================================
# REALITY MONITORING ENGINE
# ============================================================================

class RealityMonitoringEngine:
    """
    Complete reality monitoring engine.

    "Ba'el's source discrimination engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = RealityMonitoringParadigm()
        self._system = RealityMonitoringSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Memory management

    def create_perceived(
        self,
        content: str
    ) -> MemoryRecord:
        """Create perceived memory."""
        return self._system.create_perceived_memory(content)

    def create_imagined(
        self,
        content: str
    ) -> MemoryRecord:
        """Create imagined memory."""
        return self._system.create_imagined_memory(content)

    def create_dreamed(
        self,
        content: str
    ) -> MemoryRecord:
        """Create dreamed memory."""
        return self._system.create_dreamed_memory(content)

    def judge(
        self,
        memory_id: str
    ) -> RealityJudgment:
        """Judge memory source."""
        return self._system.judge_memory(memory_id)

    # Experiments

    def run_basic_experiment(
        self
    ) -> Dict[str, Any]:
        """Run basic experiment."""
        result = self._paradigm.run_basic_paradigm()
        self._experiment_results.append(result)
        return result

    def study_vividness(
        self
    ) -> Dict[str, Any]:
        """Study vividness effects."""
        return self._paradigm.run_vividness_manipulation()

    def study_repeated_imagination(
        self
    ) -> Dict[str, Any]:
        """Study repeated imagination."""
        return self._paradigm.run_repeated_imagination_study()

    def study_dream_confusion(
        self
    ) -> Dict[str, Any]:
        """Study dream confusion."""
        return self._paradigm.run_dream_confusion_study()

    def study_aging(
        self
    ) -> Dict[str, Any]:
        """Study aging effects."""
        return self._paradigm.run_aging_study()

    # Analysis

    def get_metrics(self) -> RealityMonitoringMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_basic_experiment()

        last = self._experiment_results[-1]

        return RealityMonitoringMetrics(
            accuracy=last['overall_accuracy'],
            perceived_hit_rate=last['perceived_hit_rate'],
            imagined_correct_rejection=last['imagined_correct_rejection'],
            false_alarm_rate=last['imagined_false_alarm'],
            miss_rate=last['perceived_miss_rate']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'memories': len(self._system._memories),
            'judgments': len(self._system._judgments)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_reality_monitoring_engine() -> RealityMonitoringEngine:
    """Create reality monitoring engine."""
    return RealityMonitoringEngine()


def demonstrate_reality_monitoring() -> Dict[str, Any]:
    """Demonstrate reality monitoring."""
    engine = create_reality_monitoring_engine()

    # Basic experiment
    basic = engine.run_basic_experiment()

    # Vividness study
    vividness = engine.study_vividness()

    # Repeated imagination
    repeated = engine.study_repeated_imagination()

    # Dream confusion
    dreams = engine.study_dream_confusion()

    # Aging
    aging = engine.study_aging()

    return {
        'basic': {
            'accuracy': f"{basic['overall_accuracy']:.0%}",
            'perceived_hits': f"{basic['perceived_hit_rate']:.0%}",
            'imagined_correct': f"{basic['imagined_correct_rejection']:.0%}",
            'false_alarms': f"{basic['imagined_false_alarm']:.0%}"
        },
        'vividness': {
            cond: f"FA: {data['false_alarm_rate']:.0%}"
            for cond, data in vividness.items()
        },
        'repeated_imagination': {
            'false_alarm': f"{repeated['false_alarm_rate_after_imagination']:.0%}"
        },
        'dreams': {
            'judged_real': f"{dreams['dreams_judged_real']:.0%}",
            'judged_imagined': f"{dreams['dreams_judged_imagined']:.0%}"
        },
        'interpretation': (
            f"Reality monitoring accuracy: {basic['overall_accuracy']:.0%}. "
            f"Vivid imagination can be mistaken for reality."
        )
    }


def get_reality_monitoring_facts() -> Dict[str, str]:
    """Get facts about reality monitoring."""
    return {
        'johnson_raye_1981': 'Reality monitoring framework',
        'sensory_detail': 'Real memories have more sensory detail',
        'cognitive_operations': 'Imagined memories have more cognitive ops',
        'vividness': 'Vivid imagination can fool reality monitoring',
        'repeated_imagination': 'Increases false memories',
        'dreams': 'Can be confused with reality',
        'aging': 'Reality monitoring declines with age',
        'clinical': 'Impaired in schizophrenia'
    }
