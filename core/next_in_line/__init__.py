"""
BAEL Next-in-Line Effect Engine
=================================

Impaired memory for items immediately preceding one's own performance.
Rehearsal displacement and self-focused attention.

"Ba'el's performance anxiety memory." — Ba'el
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

logger = logging.getLogger("BAEL.NextInLineEffect")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class PerformanceType(Enum):
    """Types of performance."""
    SPEAKING = auto()
    READING = auto()
    RECITING = auto()
    PRESENTING = auto()


class AttentionFocus(Enum):
    """Focus of attention."""
    EXTERNAL = auto()      # Focused on others
    SELF = auto()          # Focused on self/preparation
    MIXED = auto()


class AnxietyLevel(Enum):
    """Level of performance anxiety."""
    NONE = 0
    LOW = 1
    MODERATE = 2
    HIGH = 3


@dataclass
class Performer:
    """
    A performer in a sequence.
    """
    id: str
    name: str
    position: int
    content: str
    anxiety_level: AnxietyLevel


@dataclass
class MemoryForPerformer:
    """
    Memory for a performer's content.
    """
    performer_id: str
    content_recalled: bool
    recall_accuracy: float
    position_effect: str  # "preceding", "following", "distant"


@dataclass
class NextInLineMetrics:
    """
    Next-in-line effect metrics.
    """
    preceding_recall: float
    following_recall: float
    distant_recall: float
    next_in_line_effect: float


# ============================================================================
# ATTENTION ALLOCATION MODEL
# ============================================================================

class AttentionAllocationModel:
    """
    Model of attention allocation during anticipation.

    "Ba'el's self-focus drain." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Attention parameters
        self._total_attention = 1.0
        self._self_focus_drain = 0.4  # Attention diverted to self when next
        self._rehearsal_interference = 0.3

        self._lock = threading.RLock()

    def calculate_attention_to_others(
        self,
        positions_until_turn: int,
        anxiety: AnxietyLevel
    ) -> float:
        """Calculate attention available for others' content."""
        if positions_until_turn > 3:
            # Not worried yet, full attention
            return self._total_attention * 0.8
        elif positions_until_turn == 0:
            # Just performed, relieved, attention returning
            return self._total_attention * 0.6
        else:
            # Approaching turn, attention diverted to self
            self_focus = self._self_focus_drain * (4 - positions_until_turn) / 3

            # Anxiety increases self-focus
            anxiety_boost = anxiety.value * 0.1
            self_focus += anxiety_boost

            return max(0.2, self._total_attention - self_focus)

    def calculate_encoding_strength(
        self,
        attention: float,
        positions_until_turn: int
    ) -> float:
        """Calculate encoding strength."""
        # Rehearsal interference when close to turn
        if positions_until_turn <= 2:
            rehearsal_cost = self._rehearsal_interference * (3 - positions_until_turn) / 2
        else:
            rehearsal_cost = 0

        encoding = attention * (1 - rehearsal_cost)

        return max(0.1, encoding)


# ============================================================================
# PERFORMANCE SEQUENCE
# ============================================================================

class PerformanceSequence:
    """
    A sequence of performances.

    "Ba'el's performance line." — Ba'el
    """

    def __init__(self):
        """Initialize sequence."""
        self._attention_model = AttentionAllocationModel()

        self._performers: List[Performer] = []
        self._self_position: int = -1
        self._memories: Dict[str, MemoryForPerformer] = {}

        self._perf_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._perf_counter += 1
        return f"performer_{self._perf_counter}"

    def create_sequence(
        self,
        n_performers: int,
        self_position: int,
        anxiety: AnxietyLevel = AnxietyLevel.MODERATE
    ) -> List[Performer]:
        """Create a performance sequence."""
        self._self_position = self_position
        self._performers = []

        for i in range(n_performers):
            is_self = (i == self_position)

            performer = Performer(
                id=self._generate_id(),
                name=f"person_{i}" if not is_self else "SELF",
                position=i,
                content=f"content_{i}",
                anxiety_level=anxiety if is_self else AnxietyLevel.NONE
            )

            self._performers.append(performer)

        return self._performers

    def observe_sequence(
        self
    ) -> Dict[str, MemoryForPerformer]:
        """Observe the performance sequence."""
        self._memories = {}

        for performer in self._performers:
            if performer.position == self._self_position:
                # Skip self (we performed, didn't observe)
                continue

            # Calculate positions until our turn
            positions_until_turn = self._self_position - performer.position

            if positions_until_turn < 0:
                # Already performed, full attention returning
                positions_until_turn = 5  # Treat as distant

            # Get attention allocation
            attention = self._attention_model.calculate_attention_to_others(
                positions_until_turn,
                AnxietyLevel.MODERATE
            )

            # Calculate encoding
            encoding = self._attention_model.calculate_encoding_strength(
                attention, positions_until_turn
            )

            # Memory formation
            recall_prob = encoding * 0.8 + 0.1
            recalled = random.random() < recall_prob

            # Determine position category
            if positions_until_turn == 1:
                position_effect = "preceding"
            elif positions_until_turn < 0 and positions_until_turn > -3:
                position_effect = "following"
            else:
                position_effect = "distant"

            memory = MemoryForPerformer(
                performer_id=performer.id,
                content_recalled=recalled,
                recall_accuracy=encoding * random.uniform(0.8, 1.0) if recalled else 0,
                position_effect=position_effect
            )

            self._memories[performer.id] = memory

        return self._memories


# ============================================================================
# EXPERIMENTAL PARADIGM
# ============================================================================

class NextInLineParadigm:
    """
    Next-in-line effect experimental paradigm.

    "Ba'el's serial performance study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_experiment(
        self,
        n_performers: int = 8,
        self_position: int = 4,
        anxiety: AnxietyLevel = AnxietyLevel.MODERATE
    ) -> Dict[str, Any]:
        """Run next-in-line experiment."""
        sequence = PerformanceSequence()
        sequence.create_sequence(n_performers, self_position, anxiety)
        memories = sequence.observe_sequence()

        # Categorize by position
        preceding_memories = [m for m in memories.values() if m.position_effect == "preceding"]
        following_memories = [m for m in memories.values() if m.position_effect == "following"]
        distant_memories = [m for m in memories.values() if m.position_effect == "distant"]

        preceding_recall = sum(1 for m in preceding_memories if m.content_recalled) / len(preceding_memories) if preceding_memories else 0
        following_recall = sum(1 for m in following_memories if m.content_recalled) / len(following_memories) if following_memories else 0
        distant_recall = sum(1 for m in distant_memories if m.content_recalled) / len(distant_memories) if distant_memories else 0

        # Next-in-line effect = distant - preceding
        nil_effect = distant_recall - preceding_recall

        return {
            'n_performers': n_performers,
            'self_position': self_position,
            'preceding_recall': preceding_recall,
            'following_recall': following_recall,
            'distant_recall': distant_recall,
            'next_in_line_effect': nil_effect
        }

    def run_anxiety_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare effect across anxiety levels."""
        results = {}

        for anxiety in AnxietyLevel:
            if anxiety == AnxietyLevel.NONE:
                continue

            result = self.run_experiment(8, 4, anxiety)
            results[anxiety.name] = {
                'preceding_recall': result['preceding_recall'],
                'effect': result['next_in_line_effect']
            }

        return results

    def run_position_analysis(
        self,
        n_performers: int = 10
    ) -> Dict[str, Any]:
        """Analyze effect by self position."""
        results = {}

        for self_pos in [2, 5, 8]:  # Early, middle, late
            result = self.run_experiment(n_performers, self_pos)
            results[f"position_{self_pos}"] = {
                'preceding_recall': result['preceding_recall'],
                'effect': result['next_in_line_effect']
            }

        return results


# ============================================================================
# NEXT-IN-LINE EFFECT ENGINE
# ============================================================================

class NextInLineEffectEngine:
    """
    Complete next-in-line effect engine.

    "Ba'el's anticipation amnesia." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = NextInLineParadigm()
        self._sequence = PerformanceSequence()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Sequence creation

    def create_sequence(
        self,
        n_performers: int,
        self_position: int,
        anxiety: AnxietyLevel = AnxietyLevel.MODERATE
    ) -> List[Performer]:
        """Create a performance sequence."""
        return self._sequence.create_sequence(n_performers, self_position, anxiety)

    # Observation

    def observe(
        self
    ) -> Dict[str, MemoryForPerformer]:
        """Observe the sequence."""
        return self._sequence.observe_sequence()

    # Experiments

    def run_nil_experiment(
        self,
        n_performers: int = 8,
        self_position: int = 4
    ) -> Dict[str, Any]:
        """Run next-in-line experiment."""
        result = self._paradigm.run_experiment(n_performers, self_position)
        self._experiment_results.append(result)
        return result

    def run_anxiety_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare across anxiety levels."""
        return self._paradigm.run_anxiety_comparison()

    def run_position_analysis(
        self,
        n_performers: int = 10
    ) -> Dict[str, Any]:
        """Analyze by position."""
        return self._paradigm.run_position_analysis(n_performers)

    def run_rehearsal_hypothesis_test(
        self
    ) -> Dict[str, Any]:
        """Test rehearsal interference hypothesis."""
        # Compare conditions with/without rehearsal requirement

        # With rehearsal (normal condition)
        with_rehearsal = self._paradigm.run_experiment(8, 4, AnxietyLevel.MODERATE)

        # Simulate without rehearsal (low anxiety, nothing to prepare)
        without_rehearsal = self._paradigm.run_experiment(8, 4, AnxietyLevel.NONE)

        return {
            'with_rehearsal': {
                'preceding_recall': with_rehearsal['preceding_recall'],
                'effect': with_rehearsal['next_in_line_effect']
            },
            'without_rehearsal': {
                'preceding_recall': without_rehearsal['preceding_recall'],
                'effect': without_rehearsal['next_in_line_effect']
            },
            'interpretation': 'Rehearsal requirement increases effect'
        }

    # Analysis

    def get_metrics(self) -> NextInLineMetrics:
        """Get next-in-line metrics."""
        if not self._experiment_results:
            self.run_nil_experiment(8, 4)

        last = self._experiment_results[-1]

        return NextInLineMetrics(
            preceding_recall=last['preceding_recall'],
            following_recall=last['following_recall'],
            distant_recall=last['distant_recall'],
            next_in_line_effect=last['next_in_line_effect']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'performers': len(self._sequence._performers),
            'memories': len(self._sequence._memories),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_next_in_line_engine() -> NextInLineEffectEngine:
    """Create next-in-line effect engine."""
    return NextInLineEffectEngine()


def demonstrate_next_in_line_effect() -> Dict[str, Any]:
    """Demonstrate next-in-line effect."""
    engine = create_next_in_line_engine()

    # Basic experiment
    basic = engine.run_nil_experiment(8, 4)

    # Anxiety comparison
    anxiety = engine.run_anxiety_comparison()

    # Position analysis
    position = engine.run_position_analysis(10)

    # Rehearsal hypothesis
    rehearsal = engine.run_rehearsal_hypothesis_test()

    return {
        'next_in_line_effect': {
            'preceding_recall': f"{basic['preceding_recall']:.0%}",
            'following_recall': f"{basic['following_recall']:.0%}",
            'distant_recall': f"{basic['distant_recall']:.0%}",
            'effect': f"{basic['next_in_line_effect']:.0%}"
        },
        'anxiety_effect': {
            level: f"effect: {data['effect']:.0%}"
            for level, data in anxiety.items()
        },
        'position_effect': {
            pos: f"preceding: {data['preceding_recall']:.0%}"
            for pos, data in position.items()
        },
        'rehearsal_hypothesis': {
            'with_rehearsal': f"{rehearsal['with_rehearsal']['effect']:.0%}",
            'without_rehearsal': f"{rehearsal['without_rehearsal']['effect']:.0%}"
        },
        'interpretation': (
            f"Next-in-line effect: {basic['next_in_line_effect']:.0%}. "
            f"Preceding performer's content is poorly remembered due to self-focus."
        )
    }


def get_next_in_line_effect_facts() -> Dict[str, str]:
    """Get facts about next-in-line effect."""
    return {
        'brenner_1973': 'Original demonstration of next-in-line effect',
        'self_focused_attention': 'Attention diverted to own upcoming performance',
        'rehearsal_interference': 'Rehearsing own content interferes with encoding others',
        'anticipatory_anxiety': 'Performance anxiety reduces attention to others',
        'position_effect': 'Effect strongest for immediately preceding performer',
        'following_recovery': 'Memory improves for performers after own turn',
        'social_situations': 'Common in meetings, classes, introductions',
        'mitigation': 'Recording or notes can help'
    }
