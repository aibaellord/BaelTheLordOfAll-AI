"""
BAEL Expertise Effect Engine
===============================

Expert knowledge organizes memory.
Chase & Simon's chess expertise studies.

"Ba'el's mastery transforms perception." — Ba'el
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

logger = logging.getLogger("BAEL.ExpertiseEffect")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ExpertiseLevel(Enum):
    """Level of expertise."""
    NOVICE = auto()
    BEGINNER = auto()
    INTERMEDIATE = auto()
    ADVANCED = auto()
    EXPERT = auto()
    MASTER = auto()


class DomainType(Enum):
    """Type of domain."""
    CHESS = auto()
    MEDICINE = auto()
    PROGRAMMING = auto()
    MUSIC = auto()
    SPORTS = auto()
    SCIENCE = auto()
    LANGUAGE = auto()


class StimulusType(Enum):
    """Type of stimulus."""
    MEANINGFUL = auto()     # Domain-structured
    RANDOM = auto()         # Unstructured
    PARTIALLY_STRUCTURED = auto()


@dataclass
class DomainKnowledge:
    """
    Domain knowledge representation.
    """
    domain: DomainType
    expertise_level: ExpertiseLevel
    chunk_library_size: int
    pattern_recognition_speed: float
    retrieval_accuracy: float


@dataclass
class Stimulus:
    """
    A stimulus to be processed.
    """
    id: str
    content: str
    domain: DomainType
    stimulus_type: StimulusType
    elements: List[str]
    patterns: List[str]


@dataclass
class PerformanceResult:
    """
    Performance on a task.
    """
    stimulus_id: str
    recalled_elements: List[str]
    accuracy: float
    response_time_ms: float
    chunks_used: int


@dataclass
class ExpertiseMetrics:
    """
    Expertise effect metrics.
    """
    expert_meaningful: float
    expert_random: float
    novice_meaningful: float
    novice_random: float
    expertise_advantage: float


# ============================================================================
# EXPERTISE MODEL
# ============================================================================

class ExpertiseModel:
    """
    Chase & Simon expertise model.

    "Ba'el's chunking mastery." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Expertise parameters
        self._chunk_capacity = 7  # Miller's 7±2

        # Expertise-based parameters
        self._expertise_multipliers = {
            ExpertiseLevel.NOVICE: 0.3,
            ExpertiseLevel.BEGINNER: 0.4,
            ExpertiseLevel.INTERMEDIATE: 0.6,
            ExpertiseLevel.ADVANCED: 0.8,
            ExpertiseLevel.EXPERT: 0.95,
            ExpertiseLevel.MASTER: 1.0
        }

        # Chunk sizes by expertise
        self._chunk_sizes = {
            ExpertiseLevel.NOVICE: 1,
            ExpertiseLevel.BEGINNER: 2,
            ExpertiseLevel.INTERMEDIATE: 3,
            ExpertiseLevel.ADVANCED: 4,
            ExpertiseLevel.EXPERT: 5,
            ExpertiseLevel.MASTER: 6
        }

        # Pattern recognition speed (ms per pattern)
        self._recognition_speeds = {
            ExpertiseLevel.NOVICE: 2000,
            ExpertiseLevel.BEGINNER: 1500,
            ExpertiseLevel.INTERMEDIATE: 1000,
            ExpertiseLevel.ADVANCED: 500,
            ExpertiseLevel.EXPERT: 200,
            ExpertiseLevel.MASTER: 100
        }

        self._lock = threading.RLock()

    def calculate_chunk_count(
        self,
        elements: int,
        expertise: ExpertiseLevel,
        stimulus_type: StimulusType
    ) -> int:
        """Calculate number of chunks formed."""
        chunk_size = self._chunk_sizes[expertise]

        if stimulus_type == StimulusType.RANDOM:
            # Random stimuli don't benefit from chunking
            chunk_size = 1
        elif stimulus_type == StimulusType.PARTIALLY_STRUCTURED:
            chunk_size = max(1, chunk_size // 2)

        chunks = math.ceil(elements / chunk_size)

        return chunks

    def calculate_recall_probability(
        self,
        chunks_needed: int,
        expertise: ExpertiseLevel,
        stimulus_type: StimulusType
    ) -> float:
        """Calculate recall probability."""
        # Can hold ~7 chunks
        if chunks_needed <= self._chunk_capacity:
            base_prob = 0.9
        else:
            # Exceeds capacity
            overflow = chunks_needed - self._chunk_capacity
            base_prob = 0.9 * math.exp(-0.2 * overflow)

        # Expertise affects accuracy
        expertise_factor = self._expertise_multipliers[expertise]

        # Random stimuli hurt everyone
        if stimulus_type == StimulusType.RANDOM:
            expertise_factor *= 0.5

        return base_prob * expertise_factor

    def calculate_response_time(
        self,
        elements: int,
        expertise: ExpertiseLevel,
        stimulus_type: StimulusType
    ) -> float:
        """Calculate response time in ms."""
        base_time = self._recognition_speeds[expertise]

        # Time scales with elements for novices
        if expertise in [ExpertiseLevel.NOVICE, ExpertiseLevel.BEGINNER]:
            time_per_element = 200
        else:
            time_per_element = 50

        # Random stimuli take longer
        if stimulus_type == StimulusType.RANDOM:
            time_per_element *= 2

        total = base_time + elements * time_per_element

        return total

    def calculate_pattern_recognition(
        self,
        patterns: List[str],
        expertise: ExpertiseLevel
    ) -> List[str]:
        """Determine which patterns are recognized."""
        expertise_factor = self._expertise_multipliers[expertise]

        recognized = []
        for pattern in patterns:
            if random.random() < expertise_factor:
                recognized.append(pattern)

        return recognized


# ============================================================================
# EXPERTISE SYSTEM
# ============================================================================

class ExpertiseSystem:
    """
    Expertise effect simulation system.

    "Ba'el's expert memory." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = ExpertiseModel()

        self._knowledge: Dict[str, DomainKnowledge] = {}
        self._stimuli: Dict[str, Stimulus] = {}
        self._results: List[PerformanceResult] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def create_expertise(
        self,
        domain: DomainType,
        level: ExpertiseLevel
    ) -> DomainKnowledge:
        """Create domain expertise."""
        # Chunk library grows with expertise
        library_sizes = {
            ExpertiseLevel.NOVICE: 50,
            ExpertiseLevel.BEGINNER: 200,
            ExpertiseLevel.INTERMEDIATE: 1000,
            ExpertiseLevel.ADVANCED: 5000,
            ExpertiseLevel.EXPERT: 50000,
            ExpertiseLevel.MASTER: 100000
        }

        knowledge = DomainKnowledge(
            domain=domain,
            expertise_level=level,
            chunk_library_size=library_sizes[level],
            pattern_recognition_speed=self._model._recognition_speeds[level],
            retrieval_accuracy=self._model._expertise_multipliers[level]
        )

        key = f"{domain.name}_{level.name}"
        self._knowledge[key] = knowledge

        return knowledge

    def create_stimulus(
        self,
        domain: DomainType,
        stimulus_type: StimulusType,
        n_elements: int = 25,
        n_patterns: int = 5
    ) -> Stimulus:
        """Create a stimulus."""
        elements = [f"element_{i}" for i in range(n_elements)]

        if stimulus_type == StimulusType.MEANINGFUL:
            patterns = [f"pattern_{i}" for i in range(n_patterns)]
        elif stimulus_type == StimulusType.PARTIALLY_STRUCTURED:
            patterns = [f"pattern_{i}" for i in range(n_patterns // 2)]
        else:
            patterns = []  # Random has no patterns

        stimulus = Stimulus(
            id=self._generate_id(),
            content=f"stimulus_{domain.name}",
            domain=domain,
            stimulus_type=stimulus_type,
            elements=elements,
            patterns=patterns
        )

        self._stimuli[stimulus.id] = stimulus

        return stimulus

    def process_stimulus(
        self,
        stimulus_id: str,
        expertise_level: ExpertiseLevel
    ) -> PerformanceResult:
        """Process stimulus with given expertise."""
        stimulus = self._stimuli.get(stimulus_id)
        if not stimulus:
            return None

        n_elements = len(stimulus.elements)

        # Calculate chunks
        chunks = self._model.calculate_chunk_count(
            n_elements, expertise_level, stimulus.stimulus_type
        )

        # Calculate recall
        recall_prob = self._model.calculate_recall_probability(
            chunks, expertise_level, stimulus.stimulus_type
        )

        # Determine what's recalled
        recalled = []
        for elem in stimulus.elements:
            if random.random() < recall_prob:
                recalled.append(elem)

        accuracy = len(recalled) / n_elements

        # Response time
        response_time = self._model.calculate_response_time(
            n_elements, expertise_level, stimulus.stimulus_type
        )

        result = PerformanceResult(
            stimulus_id=stimulus_id,
            recalled_elements=recalled,
            accuracy=accuracy,
            response_time_ms=response_time,
            chunks_used=chunks
        )

        self._results.append(result)

        return result


# ============================================================================
# EXPERTISE PARADIGM
# ============================================================================

class ExpertiseParadigm:
    """
    Expertise experimental paradigm.

    "Ba'el's chess memory study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_chase_simon_paradigm(
        self,
        domain: DomainType = DomainType.CHESS
    ) -> Dict[str, Any]:
        """Run Chase & Simon chess paradigm."""
        system = ExpertiseSystem()

        results = {}

        for expertise in [ExpertiseLevel.NOVICE, ExpertiseLevel.EXPERT]:
            for stim_type in [StimulusType.MEANINGFUL, StimulusType.RANDOM]:
                # Create stimulus
                stimulus = system.create_stimulus(
                    domain, stim_type, n_elements=25, n_patterns=6
                )

                # Process
                result = system.process_stimulus(stimulus.id, expertise)

                key = f"{expertise.name}_{stim_type.name}"
                results[key] = {
                    'accuracy': result.accuracy,
                    'response_time': result.response_time_ms,
                    'chunks': result.chunks_used
                }

        # Calculate expertise advantage
        expert_meaningful = results['EXPERT_MEANINGFUL']['accuracy']
        expert_random = results['EXPERT_RANDOM']['accuracy']
        novice_meaningful = results['NOVICE_MEANINGFUL']['accuracy']
        novice_random = results['NOVICE_RANDOM']['accuracy']

        return {
            'results': results,
            'expert_meaningful': expert_meaningful,
            'expert_random': expert_random,
            'novice_meaningful': novice_meaningful,
            'novice_random': novice_random,
            'expertise_advantage_meaningful': expert_meaningful - novice_meaningful,
            'expertise_advantage_random': expert_random - novice_random,
            'interpretation': 'Expertise helps with meaningful but not random stimuli'
        }

    def run_chunk_size_study(
        self
    ) -> Dict[str, Any]:
        """Study chunk size across expertise levels."""
        results = {}

        for expertise in list(ExpertiseLevel):
            system = ExpertiseSystem()

            stimulus = system.create_stimulus(
                DomainType.CHESS, StimulusType.MEANINGFUL, 30
            )

            result = system.process_stimulus(stimulus.id, expertise)

            results[expertise.name] = {
                'chunks': result.chunks_used,
                'accuracy': result.accuracy,
                'response_time': result.response_time_ms
            }

        return {
            'by_expertise': results,
            'interpretation': 'Experts form larger chunks'
        }

    def run_domain_transfer_study(
        self
    ) -> Dict[str, Any]:
        """Study transfer across domains."""
        system = ExpertiseSystem()

        # Expert in chess
        chess_expert = system.create_expertise(DomainType.CHESS, ExpertiseLevel.EXPERT)

        results = {}

        for domain in [DomainType.CHESS, DomainType.MEDICINE, DomainType.MUSIC]:
            stimulus = system.create_stimulus(domain, StimulusType.MEANINGFUL, 20)

            # Chess expertise only helps in chess
            if domain == DomainType.CHESS:
                expertise = ExpertiseLevel.EXPERT
            else:
                expertise = ExpertiseLevel.NOVICE

            result = system.process_stimulus(stimulus.id, expertise)

            results[domain.name] = {
                'accuracy': result.accuracy,
                'interpretation': 'Expert' if domain == DomainType.CHESS else 'Novice'
            }

        return {
            'by_domain': results,
            'interpretation': 'Expertise is domain-specific'
        }

    def run_deliberate_practice_simulation(
        self
    ) -> Dict[str, Any]:
        """Simulate expertise development through practice."""
        system = ExpertiseSystem()

        practice_stages = [
            (0, ExpertiseLevel.NOVICE),
            (1000, ExpertiseLevel.BEGINNER),
            (5000, ExpertiseLevel.INTERMEDIATE),
            (10000, ExpertiseLevel.ADVANCED),
            (20000, ExpertiseLevel.EXPERT)
        ]

        development = {}

        for hours, level in practice_stages:
            stimulus = system.create_stimulus(
                DomainType.CHESS, StimulusType.MEANINGFUL, 25
            )

            result = system.process_stimulus(stimulus.id, level)

            development[f"hours_{hours}"] = {
                'level': level.name,
                'accuracy': result.accuracy,
                'chunks': result.chunks_used
            }

        return {
            'development': development,
            'interpretation': '10,000 hours to expertise'
        }

    def run_eye_movement_simulation(
        self
    ) -> Dict[str, Any]:
        """Simulate eye movement patterns."""
        # Experts show fewer fixations, longer on key areas

        results = {}

        for expertise in [ExpertiseLevel.NOVICE, ExpertiseLevel.EXPERT]:
            if expertise == ExpertiseLevel.NOVICE:
                fixations = random.randint(20, 30)
                key_area_time = 0.3
                pattern_detection = 2
            else:
                fixations = random.randint(5, 10)
                key_area_time = 0.7
                pattern_detection = 8

            results[expertise.name] = {
                'num_fixations': fixations,
                'key_area_proportion': key_area_time,
                'patterns_detected': pattern_detection
            }

        return {
            'by_expertise': results,
            'interpretation': 'Experts show efficient visual search'
        }

    def run_recall_patterns_study(
        self
    ) -> Dict[str, Any]:
        """Study temporal patterns in recall."""
        system = ExpertiseSystem()

        results = {}

        for expertise in [ExpertiseLevel.NOVICE, ExpertiseLevel.EXPERT]:
            stimulus = system.create_stimulus(
                DomainType.CHESS, StimulusType.MEANINGFUL, 25
            )

            result = system.process_stimulus(stimulus.id, expertise)

            # Simulate recall bursts (experts recall in chunks)
            if expertise == ExpertiseLevel.EXPERT:
                burst_sizes = [random.randint(3, 5) for _ in range(5)]
                inter_burst_pause = 500  # ms
            else:
                burst_sizes = [random.randint(1, 2) for _ in range(10)]
                inter_burst_pause = 1500  # ms

            results[expertise.name] = {
                'burst_sizes': burst_sizes,
                'inter_burst_pause': inter_burst_pause,
                'total_recalled': sum(burst_sizes)
            }

        return {
            'recall_patterns': results,
            'interpretation': 'Experts recall in larger bursts'
        }


# ============================================================================
# EXPERTISE ENGINE
# ============================================================================

class ExpertiseEffectEngine:
    """
    Complete expertise effect engine.

    "Ba'el's expert memory engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = ExpertiseParadigm()
        self._system = ExpertiseSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Knowledge management

    def create_expertise(
        self,
        domain: DomainType,
        level: ExpertiseLevel
    ) -> DomainKnowledge:
        """Create expertise."""
        return self._system.create_expertise(domain, level)

    def create_stimulus(
        self,
        domain: DomainType,
        stim_type: StimulusType,
        n_elements: int = 25
    ) -> Stimulus:
        """Create stimulus."""
        return self._system.create_stimulus(domain, stim_type, n_elements)

    def process(
        self,
        stimulus_id: str,
        expertise: ExpertiseLevel
    ) -> PerformanceResult:
        """Process stimulus."""
        return self._system.process_stimulus(stimulus_id, expertise)

    # Experiments

    def run_chase_simon(
        self,
        domain: DomainType = DomainType.CHESS
    ) -> Dict[str, Any]:
        """Run Chase & Simon paradigm."""
        result = self._paradigm.run_chase_simon_paradigm(domain)
        self._experiment_results.append(result)
        return result

    def study_chunk_size(
        self
    ) -> Dict[str, Any]:
        """Study chunk size."""
        return self._paradigm.run_chunk_size_study()

    def study_transfer(
        self
    ) -> Dict[str, Any]:
        """Study domain transfer."""
        return self._paradigm.run_domain_transfer_study()

    def simulate_practice(
        self
    ) -> Dict[str, Any]:
        """Simulate deliberate practice."""
        return self._paradigm.run_deliberate_practice_simulation()

    def simulate_eye_movements(
        self
    ) -> Dict[str, Any]:
        """Simulate eye movements."""
        return self._paradigm.run_eye_movement_simulation()

    def study_recall_patterns(
        self
    ) -> Dict[str, Any]:
        """Study recall patterns."""
        return self._paradigm.run_recall_patterns_study()

    # Analysis

    def get_metrics(self) -> ExpertiseMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_chase_simon()

        last = self._experiment_results[-1]

        return ExpertiseMetrics(
            expert_meaningful=last['expert_meaningful'],
            expert_random=last['expert_random'],
            novice_meaningful=last['novice_meaningful'],
            novice_random=last['novice_random'],
            expertise_advantage=last['expertise_advantage_meaningful']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'knowledge': len(self._system._knowledge),
            'stimuli': len(self._system._stimuli),
            'results': len(self._system._results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_expertise_effect_engine() -> ExpertiseEffectEngine:
    """Create expertise effect engine."""
    return ExpertiseEffectEngine()


def demonstrate_expertise_effect() -> Dict[str, Any]:
    """Demonstrate expertise effect."""
    engine = create_expertise_effect_engine()

    # Chase & Simon
    chase = engine.run_chase_simon()

    # Chunk size
    chunks = engine.study_chunk_size()

    # Transfer
    transfer = engine.study_transfer()

    # Practice
    practice = engine.simulate_practice()

    return {
        'chase_simon': {
            'expert_meaningful': f"{chase['expert_meaningful']:.0%}",
            'expert_random': f"{chase['expert_random']:.0%}",
            'novice_meaningful': f"{chase['novice_meaningful']:.0%}",
            'novice_random': f"{chase['novice_random']:.0%}",
            'expertise_advantage': f"{chase['expertise_advantage_meaningful']:.0%}"
        },
        'chunk_sizes': {
            k: f"{v['chunks']} chunks"
            for k, v in chunks['by_expertise'].items()
        },
        'transfer': {
            k: f"acc: {v['accuracy']:.0%}"
            for k, v in transfer['by_domain'].items()
        },
        'interpretation': (
            f"Experts: {chase['expert_meaningful']:.0%} on meaningful, "
            f"{chase['expert_random']:.0%} on random. "
            f"Expertise helps with domain-structured material."
        )
    }


def get_expertise_effect_facts() -> Dict[str, str]:
    """Get facts about expertise effect."""
    return {
        'chase_simon_1973': 'Chess expertise and chunking study',
        'chunking': 'Experts form larger meaningful chunks',
        'domain_specificity': 'Expertise does not transfer across domains',
        'random_nullifies': 'Random material eliminates expertise advantage',
        'chunk_library': 'Experts have ~50,000+ stored patterns',
        'deliberate_practice': '~10,000 hours for expertise',
        'eye_movements': 'Experts show efficient visual search',
        'recall_bursts': 'Experts recall in meaningful bursts'
    }
