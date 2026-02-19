"""
BAEL Implicit Learning Engine
================================

Statistical learning and sequence learning.
Implicit knowledge acquisition.

"Ba'el learns without knowing." — Ba'el
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

logger = logging.getLogger("BAEL.ImplicitLearning")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class LearningType(Enum):
    """Types of implicit learning."""
    STATISTICAL = auto()       # Transitional probabilities
    SEQUENCE = auto()          # Serial reaction time
    ARTIFICIAL_GRAMMAR = auto() # Reber's AG
    CONTEXTUAL_CUEING = auto() # Chun & Jiang
    PROTOTYPE = auto()         # Category learning


class AwarenessLevel(Enum):
    """Awareness of learned knowledge."""
    NONE = auto()              # No awareness
    FEELING = auto()           # Gut feeling
    STRUCTURAL = auto()        # Some awareness of structure
    FULL = auto()              # Explicit knowledge


class GrammarType(Enum):
    """Types of artificial grammar."""
    FINITE_STATE = auto()
    BICONDITIONAL = auto()
    HIERARCHICAL = auto()


@dataclass
class TransitionProbability:
    """
    A learned transitional probability.
    """
    from_element: Any
    to_element: Any
    probability: float
    count: int


@dataclass
class SequencePattern:
    """
    A learned sequence pattern.
    """
    pattern: Tuple[Any, ...]
    frequency: int
    reaction_times: List[float]


@dataclass
class GrammarRule:
    """
    An artificial grammar rule.
    """
    state: str
    transitions: Dict[str, str]  # symbol -> next state
    is_terminal: bool


@dataclass
class LearningResult:
    """
    Result of implicit learning.
    """
    learning_type: LearningType
    exposure_count: int
    accuracy: float
    awareness_level: AwarenessLevel
    reaction_time_reduction: float


@dataclass
class ImplicitMetrics:
    """
    Implicit learning metrics.
    """
    statistical_learning_score: float
    sequence_learning_score: float
    grammar_learning_score: float
    overall_implicit_learning: float


# ============================================================================
# STATISTICAL LEARNER
# ============================================================================

class StatisticalLearner:
    """
    Saffran et al. statistical learning.

    "Ba'el tracks probabilities." — Ba'el
    """

    def __init__(self):
        """Initialize learner."""
        self._transitions: Dict[Tuple[Any, Any], TransitionProbability] = {}
        self._element_counts: Dict[Any, int] = defaultdict(int)
        self._total_transitions = 0

        self._lock = threading.RLock()

    def observe_sequence(
        self,
        sequence: List[Any]
    ) -> None:
        """Observe a sequence to learn statistics."""
        for i in range(len(sequence)):
            element = sequence[i]
            self._element_counts[element] += 1

            if i < len(sequence) - 1:
                next_element = sequence[i + 1]
                key = (element, next_element)

                if key not in self._transitions:
                    self._transitions[key] = TransitionProbability(
                        from_element=element,
                        to_element=next_element,
                        probability=0.0,
                        count=0
                    )

                self._transitions[key].count += 1
                self._total_transitions += 1

        # Update probabilities
        self._update_probabilities()

    def _update_probabilities(self) -> None:
        """Update transitional probabilities."""
        for key, tp in self._transitions.items():
            from_element = key[0]
            from_count = self._element_counts[from_element]

            if from_count > 0:
                tp.probability = tp.count / from_count

    def get_transitional_probability(
        self,
        from_element: Any,
        to_element: Any
    ) -> float:
        """Get learned transitional probability."""
        key = (from_element, to_element)
        tp = self._transitions.get(key)
        return tp.probability if tp else 0.0

    def predict_next(
        self,
        current: Any
    ) -> List[Tuple[Any, float]]:
        """Predict likely next elements."""
        predictions = []

        for key, tp in self._transitions.items():
            if key[0] == current:
                predictions.append((key[1], tp.probability))

        return sorted(predictions, key=lambda x: x[1], reverse=True)

    def segment_stream(
        self,
        stream: List[Any],
        threshold: float = 0.5
    ) -> List[List[Any]]:
        """Segment stream based on low TPs."""
        if not stream:
            return []

        segments = []
        current_segment = [stream[0]]

        for i in range(1, len(stream)):
            tp = self.get_transitional_probability(
                stream[i - 1], stream[i]
            )

            if tp < threshold:
                # Low TP = word boundary
                segments.append(current_segment)
                current_segment = []

            current_segment.append(stream[i])

        if current_segment:
            segments.append(current_segment)

        return segments

    def test_word_recognition(
        self,
        word: List[Any],
        partword: List[Any]
    ) -> Tuple[bool, float]:
        """Test word vs partword recognition."""
        word_tp = self._calculate_average_tp(word)
        partword_tp = self._calculate_average_tp(partword)

        # Word should have higher internal TPs
        chose_word = word_tp > partword_tp
        confidence = abs(word_tp - partword_tp)

        return chose_word, confidence

    def _calculate_average_tp(
        self,
        sequence: List[Any]
    ) -> float:
        """Calculate average transitional probability."""
        if len(sequence) < 2:
            return 0.0

        tps = []
        for i in range(len(sequence) - 1):
            tp = self.get_transitional_probability(
                sequence[i], sequence[i + 1]
            )
            tps.append(tp)

        return sum(tps) / len(tps) if tps else 0.0


# ============================================================================
# SEQUENCE LEARNER (SRT)
# ============================================================================

class SequenceLearner:
    """
    Serial Reaction Time sequence learning.

    "Ba'el anticipates the pattern." — Ba'el
    """

    def __init__(self):
        """Initialize learner."""
        self._patterns: Dict[Tuple, SequencePattern] = {}
        self._context_size = 3

        self._history: deque = deque(maxlen=100)
        self._reaction_times: List[float] = []

        self._lock = threading.RLock()

    def observe_and_respond(
        self,
        stimulus: Any
    ) -> float:
        """Observe stimulus and return reaction time."""
        # Base reaction time
        base_rt = 400.0  # ms

        # Check if we can predict
        if len(self._history) >= self._context_size:
            context = tuple(list(self._history)[-self._context_size:])
            pattern_key = (*context, stimulus)

            if pattern_key in self._patterns:
                # We've seen this before - faster RT
                pattern = self._patterns[pattern_key]
                pattern.frequency += 1

                # RT decreases with learning
                learning_reduction = min(
                    150, pattern.frequency * 10
                )
                rt = base_rt - learning_reduction

                pattern.reaction_times.append(rt)
            else:
                # New pattern - slower RT
                rt = base_rt + random.gauss(0, 20)
                self._patterns[pattern_key] = SequencePattern(
                    pattern=pattern_key,
                    frequency=1,
                    reaction_times=[rt]
                )
        else:
            rt = base_rt + random.gauss(0, 20)

        self._history.append(stimulus)
        self._reaction_times.append(rt)

        return max(200, rt)

    def run_srt_block(
        self,
        sequence: List[Any],
        random_block: bool = False
    ) -> Dict[str, float]:
        """Run an SRT block."""
        rts = []

        for stimulus in sequence:
            if random_block:
                # Random sequence - can't predict
                rt = 400 + random.gauss(0, 30)
            else:
                rt = self.observe_and_respond(stimulus)

            rts.append(rt)

        return {
            'mean_rt': sum(rts) / len(rts),
            'min_rt': min(rts),
            'max_rt': max(rts)
        }

    def demonstrate_learning(
        self,
        pattern: List[Any],
        repetitions: int = 10
    ) -> Dict[str, Any]:
        """Demonstrate sequence learning."""
        # Training blocks
        training_rts = []
        for _ in range(repetitions):
            result = self.run_srt_block(pattern)
            training_rts.append(result['mean_rt'])

        # Random block (transfer)
        random_seq = pattern.copy()
        random.shuffle(random_seq)
        random_result = self.run_srt_block(random_seq, random_block=True)

        # Return to pattern
        return_result = self.run_srt_block(pattern)

        return {
            'initial_rt': training_rts[0],
            'final_training_rt': training_rts[-1],
            'random_block_rt': random_result['mean_rt'],
            'return_rt': return_result['mean_rt'],
            'learning': training_rts[0] - training_rts[-1],
            'interference': random_result['mean_rt'] - training_rts[-1]
        }


# ============================================================================
# ARTIFICIAL GRAMMAR LEARNER
# ============================================================================

class ArtificialGrammarLearner:
    """
    Reber's artificial grammar learning.

    "Ba'el infers the rules." — Ba'el
    """

    def __init__(self):
        """Initialize learner."""
        self._grammar: Dict[str, GrammarRule] = {}
        self._training_strings: List[str] = []
        self._chunk_counts: Dict[str, int] = defaultdict(int)

        self._lock = threading.RLock()

    def define_grammar(
        self,
        rules: Dict[str, Dict[str, str]],
        terminal_states: List[str]
    ) -> None:
        """Define artificial grammar rules."""
        for state, transitions in rules.items():
            self._grammar[state] = GrammarRule(
                state=state,
                transitions=transitions,
                is_terminal=state in terminal_states
            )

    def generate_grammatical_string(
        self,
        max_length: int = 10
    ) -> str:
        """Generate a grammatical string."""
        if not self._grammar:
            return ""

        result = ""
        current_state = "S0"  # Start state

        for _ in range(max_length):
            if current_state not in self._grammar:
                break

            rule = self._grammar[current_state]

            if rule.is_terminal:
                break

            # Choose random transition
            if not rule.transitions:
                break

            symbol = random.choice(list(rule.transitions.keys()))
            result += symbol
            current_state = rule.transitions[symbol]

        return result

    def train(
        self,
        strings: List[str]
    ) -> None:
        """Train on grammatical strings."""
        self._training_strings.extend(strings)

        # Learn chunks
        for string in strings:
            for size in range(2, 4):
                for i in range(len(string) - size + 1):
                    chunk = string[i:i + size]
                    self._chunk_counts[chunk] += 1

    def judge_grammaticality(
        self,
        string: str
    ) -> Tuple[bool, float]:
        """Judge if string is grammatical."""
        # Use chunk familiarity
        total_chunks = 0
        familiar_chunks = 0

        for size in range(2, 4):
            for i in range(len(string) - size + 1):
                chunk = string[i:i + size]
                total_chunks += 1

                if chunk in self._chunk_counts:
                    familiar_chunks += 1

        if total_chunks == 0:
            return False, 0.5

        familiarity = familiar_chunks / total_chunks

        # Grammatical if high familiarity
        is_grammatical = familiarity > 0.5
        confidence = abs(familiarity - 0.5) * 2

        return is_grammatical, confidence

    def test_classification(
        self,
        grammatical_strings: List[str],
        ungrammatical_strings: List[str]
    ) -> Dict[str, float]:
        """Test grammaticality classification."""
        correct_grammatical = 0
        correct_ungrammatical = 0

        for string in grammatical_strings:
            is_gram, _ = self.judge_grammaticality(string)
            if is_gram:
                correct_grammatical += 1

        for string in ungrammatical_strings:
            is_gram, _ = self.judge_grammaticality(string)
            if not is_gram:
                correct_ungrammatical += 1

        total = len(grammatical_strings) + len(ungrammatical_strings)

        return {
            'hit_rate': correct_grammatical / len(grammatical_strings) if grammatical_strings else 0,
            'correct_rejection': correct_ungrammatical / len(ungrammatical_strings) if ungrammatical_strings else 0,
            'overall_accuracy': (correct_grammatical + correct_ungrammatical) / total if total > 0 else 0
        }


# ============================================================================
# IMPLICIT LEARNING ENGINE
# ============================================================================

class ImplicitLearningEngine:
    """
    Complete implicit learning engine.

    "Ba'el's unconscious knowledge." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._statistical = StatisticalLearner()
        self._sequence = SequenceLearner()
        self._grammar = ArtificialGrammarLearner()

        self._learning_history: List[LearningResult] = []

        self._lock = threading.RLock()

    # Statistical learning

    def learn_statistics(
        self,
        stream: List[Any],
        repetitions: int = 5
    ) -> Dict[str, Any]:
        """Learn statistical regularities."""
        for _ in range(repetitions):
            self._statistical.observe_sequence(stream)

        # Test with word segmentation
        unique_elements = list(set(stream))

        return {
            'unique_elements': len(unique_elements),
            'transitions_learned': len(self._statistical._transitions),
            'top_transitions': sorted(
                [(k, v.probability) for k, v in self._statistical._transitions.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }

    def test_word_segmentation(
        self,
        word: List[Any],
        partword: List[Any]
    ) -> Dict[str, Any]:
        """Test word vs partword."""
        chose_word, confidence = self._statistical.test_word_recognition(
            word, partword
        )

        result = LearningResult(
            learning_type=LearningType.STATISTICAL,
            exposure_count=self._statistical._total_transitions,
            accuracy=1.0 if chose_word else 0.0,
            awareness_level=AwarenessLevel.FEELING,
            reaction_time_reduction=0.0
        )
        self._learning_history.append(result)

        return {
            'chose_word': chose_word,
            'confidence': confidence,
            'word_avg_tp': self._statistical._calculate_average_tp(word),
            'partword_avg_tp': self._statistical._calculate_average_tp(partword)
        }

    # Sequence learning

    def learn_sequence(
        self,
        pattern: List[Any],
        repetitions: int = 10
    ) -> Dict[str, Any]:
        """Learn a sequence pattern."""
        demo = self._sequence.demonstrate_learning(pattern, repetitions)

        rt_reduction = demo['learning']

        result = LearningResult(
            learning_type=LearningType.SEQUENCE,
            exposure_count=repetitions,
            accuracy=0.0,  # Not applicable
            awareness_level=AwarenessLevel.NONE,
            reaction_time_reduction=rt_reduction
        )
        self._learning_history.append(result)

        return demo

    # Grammar learning

    def define_reber_grammar(self) -> None:
        """Define Reber's grammar."""
        # Classic Reber grammar
        rules = {
            'S0': {'T': 'S1', 'V': 'S2'},
            'S1': {'P': 'S1', 'X': 'S3'},
            'S2': {'X': 'S2', 'V': 'S4'},
            'S3': {'S': 'S4', 'T': 'S5'},
            'S4': {'P': 'S3', 'S': 'S5'},
            'S5': {}
        }
        self._grammar.define_grammar(rules, ['S5'])

    def train_grammar(
        self,
        n_strings: int = 20
    ) -> List[str]:
        """Train on grammatical strings."""
        if not self._grammar._grammar:
            self.define_reber_grammar()

        strings = []
        for _ in range(n_strings):
            string = self._grammar.generate_grammatical_string()
            if string:
                strings.append(string)

        self._grammar.train(strings)

        return strings

    def test_grammar(
        self,
        test_strings: List[str],
        labels: List[bool]
    ) -> Dict[str, Any]:
        """Test grammaticality classification."""
        grammatical = [s for s, l in zip(test_strings, labels) if l]
        ungrammatical = [s for s, l in zip(test_strings, labels) if not l]

        classification = self._grammar.test_classification(
            grammatical, ungrammatical
        )

        result = LearningResult(
            learning_type=LearningType.ARTIFICIAL_GRAMMAR,
            exposure_count=len(self._grammar._training_strings),
            accuracy=classification['overall_accuracy'],
            awareness_level=AwarenessLevel.STRUCTURAL,
            reaction_time_reduction=0.0
        )
        self._learning_history.append(result)

        return classification

    # Analysis

    def assess_awareness(
        self,
        learning_type: LearningType
    ) -> AwarenessLevel:
        """Assess awareness of learned knowledge."""
        # Implicit learning typically produces low awareness
        results = [
            r for r in self._learning_history
            if r.learning_type == learning_type
        ]

        if not results:
            return AwarenessLevel.NONE

        avg_accuracy = sum(r.accuracy for r in results) / len(results)

        if avg_accuracy > 0.7:
            return AwarenessLevel.STRUCTURAL
        elif avg_accuracy > 0.5:
            return AwarenessLevel.FEELING
        else:
            return AwarenessLevel.NONE

    def get_metrics(self) -> ImplicitMetrics:
        """Get implicit learning metrics."""
        stat_results = [
            r for r in self._learning_history
            if r.learning_type == LearningType.STATISTICAL
        ]
        seq_results = [
            r for r in self._learning_history
            if r.learning_type == LearningType.SEQUENCE
        ]
        gram_results = [
            r for r in self._learning_history
            if r.learning_type == LearningType.ARTIFICIAL_GRAMMAR
        ]

        stat_score = (
            sum(r.accuracy for r in stat_results) / len(stat_results)
            if stat_results else 0.0
        )

        seq_score = (
            sum(r.reaction_time_reduction for r in seq_results) / len(seq_results)
            if seq_results else 0.0
        ) / 100  # Normalize

        gram_score = (
            sum(r.accuracy for r in gram_results) / len(gram_results)
            if gram_results else 0.0
        )

        overall = (stat_score + seq_score + gram_score) / 3

        return ImplicitMetrics(
            statistical_learning_score=stat_score,
            sequence_learning_score=seq_score,
            grammar_learning_score=gram_score,
            overall_implicit_learning=overall
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'statistical_transitions': len(self._statistical._transitions),
            'sequence_patterns': len(self._sequence._patterns),
            'grammar_chunks': len(self._grammar._chunk_counts),
            'learning_events': len(self._learning_history)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_implicit_learning_engine() -> ImplicitLearningEngine:
    """Create implicit learning engine."""
    return ImplicitLearningEngine()


def demonstrate_implicit_learning() -> Dict[str, Any]:
    """Demonstrate implicit learning."""
    engine = create_implicit_learning_engine()

    # Statistical learning (word segmentation)
    # Saffran: babies learn words from statistical structure
    syllables = ['pa', 'bi', 'ku', 'do', 'ti', 'ga', 'la', 'bu', 'pi']
    word1 = ['pa', 'bi', 'ku']
    word2 = ['do', 'ti', 'ga']
    word3 = ['la', 'bu', 'pi']

    stream = (word1 + word2 + word3) * 10  # Continuous stream
    engine.learn_statistics(stream, repetitions=5)

    # Test: word vs partword
    word_test = ['pa', 'bi', 'ku']
    partword = ['ku', 'do', 'ti']  # Crosses word boundary
    seg_result = engine.test_word_segmentation(word_test, partword)

    # Sequence learning
    pattern = [1, 2, 3, 4, 2, 1, 3, 4]
    seq_result = engine.learn_sequence(pattern, repetitions=8)

    # Grammar learning
    training = engine.train_grammar(20)
    test_result = engine.test_grammar(
        training[:5] + ['XYZ', 'QQQ', 'PPP'],
        [True, True, True, True, True, False, False, False]
    )

    metrics = engine.get_metrics()

    return {
        'statistical_learning': {
            'chose_word': seg_result['chose_word'],
            'word_tp': seg_result['word_avg_tp'],
            'partword_tp': seg_result['partword_avg_tp']
        },
        'sequence_learning': {
            'initial_rt': seq_result['initial_rt'],
            'final_rt': seq_result['final_training_rt'],
            'rt_reduction': seq_result['learning']
        },
        'grammar_learning': {
            'accuracy': test_result['overall_accuracy']
        },
        'interpretation': (
            f"Statistical: chose word={seg_result['chose_word']}, "
            f"Sequence: {seq_result['learning']:.0f}ms faster, "
            f"Grammar: {test_result['overall_accuracy']:.0%} accurate"
        )
    }


def get_implicit_learning_facts() -> Dict[str, str]:
    """Get facts about implicit learning."""
    return {
        'saffran_1996': 'Infants track transitional probabilities',
        'reber_1967': 'Artificial grammar learning',
        'nissen_bullemer': 'Serial reaction time task',
        'awareness': 'Implicit knowledge without explicit awareness',
        'neuroanatomy': 'Basal ganglia and procedural learning',
        'robustness': 'Implicit learning preserved in amnesia',
        'age_invariance': 'Relatively stable across lifespan',
        'statistical_learning': 'Domain-general mechanism'
    }
