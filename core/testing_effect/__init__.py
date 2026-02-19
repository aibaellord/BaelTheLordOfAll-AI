"""
BAEL Testing Effect Engine
===========================

Retrieval practice and test-enhanced learning.
Roediger & Karpicke testing effect implementation.

"Ba'el strengthens through testing." — Ba'el
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

logger = logging.getLogger("BAEL.TestingEffect")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class PracticeType(Enum):
    """Types of learning practice."""
    RESTUDY = auto()        # Read again
    FREE_RECALL = auto()    # Recall without cues
    CUED_RECALL = auto()    # Recall with cues
    RECOGNITION = auto()    # Multiple choice
    SHORT_ANSWER = auto()   # Brief written response
    ELABORATION = auto()    # Explain in own words


class FeedbackType(Enum):
    """Types of feedback after testing."""
    NONE = auto()           # No feedback
    CORRECT_ONLY = auto()   # Just right/wrong
    ANSWER = auto()         # Show correct answer
    ELABORATED = auto()     # Detailed explanation


class RetentionInterval(Enum):
    """Retention test intervals."""
    IMMEDIATE = auto()      # Right after
    SHORT = auto()          # Hours later
    MEDIUM = auto()         # Days later
    LONG = auto()           # Weeks/months later


@dataclass
class StudyMaterial:
    """
    Material to study.
    """
    id: str
    content: Any
    facts: List[str]  # Key facts to remember
    difficulty: float = 0.5  # 0-1


@dataclass
class TestItem:
    """
    A test item.
    """
    id: str
    material_id: str
    question: str
    answer: str
    practice_type: PracticeType
    distractors: List[str] = field(default_factory=list)  # For recognition


@dataclass
class TestAttempt:
    """
    A test attempt.
    """
    item_id: str
    response: str
    correct: bool
    response_time: float
    confidence: float
    timestamp: float


@dataclass
class LearningCurve:
    """
    Learning curve data.
    """
    practice_counts: List[int]
    accuracy_rates: List[float]
    slope: float


@dataclass
class TestingEffectMetrics:
    """
    Testing effect metrics.
    """
    restudy_retention: float
    testing_retention: float
    testing_advantage: float
    attempts: int


# ============================================================================
# MEMORY STRENGTH MODEL
# ============================================================================

class MemoryStrengthModel:
    """
    Model of memory strength.

    "Ba'el measures memory strength." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        self._storage_strength: Dict[str, float] = {}
        self._retrieval_strength: Dict[str, float] = {}

        self._lock = threading.RLock()

    def initialize_item(
        self,
        item_id: str,
        initial_storage: float = 0.3
    ) -> None:
        """Initialize memory for item."""
        with self._lock:
            self._storage_strength[item_id] = initial_storage
            self._retrieval_strength[item_id] = initial_storage

    def restudy(
        self,
        item_id: str
    ) -> Tuple[float, float]:
        """Update strength after restudying."""
        with self._lock:
            if item_id not in self._storage_strength:
                self.initialize_item(item_id)

            # Restudy increases storage but less retrieval
            old_storage = self._storage_strength[item_id]
            new_storage = old_storage + (1 - old_storage) * 0.2

            # Retrieval strength increases less
            old_retrieval = self._retrieval_strength[item_id]
            new_retrieval = old_retrieval + (1 - old_retrieval) * 0.1

            self._storage_strength[item_id] = new_storage
            self._retrieval_strength[item_id] = new_retrieval

            return new_storage, new_retrieval

    def test(
        self,
        item_id: str,
        success: bool
    ) -> Tuple[float, float]:
        """Update strength after testing."""
        with self._lock:
            if item_id not in self._storage_strength:
                self.initialize_item(item_id)

            if success:
                # Successful retrieval strengthens both
                old_storage = self._storage_strength[item_id]
                new_storage = old_storage + (1 - old_storage) * 0.3

                old_retrieval = self._retrieval_strength[item_id]
                new_retrieval = old_retrieval + (1 - old_retrieval) * 0.4
            else:
                # Failed retrieval still helps (especially with feedback)
                old_storage = self._storage_strength[item_id]
                new_storage = old_storage + (1 - old_storage) * 0.15

                old_retrieval = self._retrieval_strength[item_id]
                new_retrieval = old_retrieval + (1 - old_retrieval) * 0.2

            self._storage_strength[item_id] = new_storage
            self._retrieval_strength[item_id] = new_retrieval

            return new_storage, new_retrieval

    def decay(
        self,
        item_id: str,
        time_passed: float  # in days
    ) -> None:
        """Apply decay over time."""
        with self._lock:
            if item_id not in self._storage_strength:
                return

            # Storage decays slowly
            storage = self._storage_strength[item_id]
            storage_decay = 0.01 * time_passed
            self._storage_strength[item_id] = max(0, storage - storage_decay)

            # Retrieval decays faster
            retrieval = self._retrieval_strength[item_id]
            retrieval_decay = 0.05 * time_passed
            self._retrieval_strength[item_id] = max(0, retrieval - retrieval_decay)

    def recall_probability(
        self,
        item_id: str
    ) -> float:
        """Get probability of successful recall."""
        with self._lock:
            if item_id not in self._retrieval_strength:
                return 0.0
            return self._retrieval_strength[item_id]

    def get_strength(
        self,
        item_id: str
    ) -> Tuple[float, float]:
        """Get storage and retrieval strength."""
        with self._lock:
            storage = self._storage_strength.get(item_id, 0.0)
            retrieval = self._retrieval_strength.get(item_id, 0.0)
            return storage, retrieval


# ============================================================================
# TEST GENERATOR
# ============================================================================

class TestGenerator:
    """
    Generate test items from study material.

    "Ba'el creates assessments." — Ba'el
    """

    def __init__(self):
        """Initialize generator."""
        self._test_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._test_counter += 1
        return f"test_{self._test_counter}"

    def generate_free_recall(
        self,
        material: StudyMaterial
    ) -> TestItem:
        """Generate free recall test."""
        return TestItem(
            id=self._generate_id(),
            material_id=material.id,
            question=f"Recall everything you remember about: {material.content}",
            answer="; ".join(material.facts),
            practice_type=PracticeType.FREE_RECALL
        )

    def generate_cued_recall(
        self,
        material: StudyMaterial,
        fact_index: int = 0
    ) -> TestItem:
        """Generate cued recall test."""
        if fact_index >= len(material.facts):
            fact_index = 0

        fact = material.facts[fact_index]
        words = fact.split()

        # Create cue by hiding some words
        cue_words = words[:len(words)//2] + ["___"]
        cue = " ".join(cue_words)

        return TestItem(
            id=self._generate_id(),
            material_id=material.id,
            question=f"Complete: {cue}",
            answer=fact,
            practice_type=PracticeType.CUED_RECALL
        )

    def generate_recognition(
        self,
        material: StudyMaterial,
        all_facts: List[str]
    ) -> TestItem:
        """Generate recognition (multiple choice) test."""
        if not material.facts:
            return self.generate_free_recall(material)

        correct_fact = random.choice(material.facts)

        # Generate distractors
        distractors = []
        for fact in all_facts:
            if fact not in material.facts and len(distractors) < 3:
                distractors.append(fact)

        # If not enough distractors, create some
        while len(distractors) < 3:
            distractors.append(f"Alternative fact {len(distractors)}")

        return TestItem(
            id=self._generate_id(),
            material_id=material.id,
            question=f"Which fact is correct about {material.content}?",
            answer=correct_fact,
            practice_type=PracticeType.RECOGNITION,
            distractors=distractors
        )

    def generate_short_answer(
        self,
        material: StudyMaterial
    ) -> TestItem:
        """Generate short answer test."""
        return TestItem(
            id=self._generate_id(),
            material_id=material.id,
            question=f"Briefly explain: {material.content}",
            answer=material.facts[0] if material.facts else str(material.content),
            practice_type=PracticeType.SHORT_ANSWER
        )


# ============================================================================
# FEEDBACK PROVIDER
# ============================================================================

class FeedbackProvider:
    """
    Provide feedback after testing.

    "Ba'el gives learning feedback." — Ba'el
    """

    def __init__(self):
        """Initialize provider."""
        self._lock = threading.RLock()

    def provide_feedback(
        self,
        test_item: TestItem,
        response: str,
        correct: bool,
        feedback_type: FeedbackType
    ) -> Dict[str, Any]:
        """Provide feedback for test attempt."""
        feedback = {
            'correct': correct,
            'response': response
        }

        if feedback_type == FeedbackType.NONE:
            pass

        elif feedback_type == FeedbackType.CORRECT_ONLY:
            feedback['result'] = "Correct!" if correct else "Incorrect."

        elif feedback_type == FeedbackType.ANSWER:
            feedback['result'] = "Correct!" if correct else "Incorrect."
            if not correct:
                feedback['correct_answer'] = test_item.answer

        elif feedback_type == FeedbackType.ELABORATED:
            feedback['result'] = "Correct!" if correct else "Incorrect."
            feedback['correct_answer'] = test_item.answer
            feedback['explanation'] = f"The answer involves: {test_item.answer}"
            if not correct:
                feedback['comparison'] = f"You said '{response}' but the answer was '{test_item.answer}'"

        return feedback


# ============================================================================
# RETENTION PREDICTOR
# ============================================================================

class RetentionPredictor:
    """
    Predict retention based on practice type.

    "Ba'el forecasts memory." — Ba'el
    """

    def __init__(self):
        """Initialize predictor."""
        # Based on Roediger & Karpicke (2006) findings
        self._immediate_rates = {
            PracticeType.RESTUDY: 0.80,
            PracticeType.FREE_RECALL: 0.60,
            PracticeType.CUED_RECALL: 0.65,
            PracticeType.RECOGNITION: 0.70,
            PracticeType.SHORT_ANSWER: 0.62,
            PracticeType.ELABORATION: 0.68
        }

        self._delayed_rates = {
            PracticeType.RESTUDY: 0.40,
            PracticeType.FREE_RECALL: 0.65,
            PracticeType.CUED_RECALL: 0.60,
            PracticeType.RECOGNITION: 0.55,
            PracticeType.SHORT_ANSWER: 0.58,
            PracticeType.ELABORATION: 0.62
        }

        self._lock = threading.RLock()

    def predict_retention(
        self,
        practice_type: PracticeType,
        interval: RetentionInterval,
        practice_count: int = 1
    ) -> float:
        """Predict retention rate."""
        # Get base rate
        if interval == RetentionInterval.IMMEDIATE:
            base_rate = self._immediate_rates.get(practice_type, 0.5)
        else:
            base_rate = self._delayed_rates.get(practice_type, 0.4)

        # Adjust for interval
        interval_decay = {
            RetentionInterval.IMMEDIATE: 1.0,
            RetentionInterval.SHORT: 0.9,
            RetentionInterval.MEDIUM: 0.7,
            RetentionInterval.LONG: 0.5
        }
        decay = interval_decay.get(interval, 0.5)

        # Adjust for practice count (diminishing returns)
        practice_bonus = 1.0 + math.log(practice_count) * 0.1

        retention = base_rate * decay * practice_bonus

        return min(1.0, retention)

    def calculate_testing_advantage(
        self,
        interval: RetentionInterval
    ) -> float:
        """Calculate testing effect advantage over restudying."""
        restudy = self.predict_retention(PracticeType.RESTUDY, interval)
        testing = self.predict_retention(PracticeType.FREE_RECALL, interval)

        return testing - restudy


# ============================================================================
# TESTING EFFECT ENGINE
# ============================================================================

class TestingEffectEngine:
    """
    Complete testing effect engine.

    "Ba'el's retrieval practice system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._memory = MemoryStrengthModel()
        self._generator = TestGenerator()
        self._feedback = FeedbackProvider()
        self._predictor = RetentionPredictor()

        self._materials: Dict[str, StudyMaterial] = {}
        self._test_items: Dict[str, TestItem] = {}
        self._attempts: List[TestAttempt] = []

        self._material_counter = 0

        self._lock = threading.RLock()

    def _generate_material_id(self) -> str:
        self._material_counter += 1
        return f"material_{self._material_counter}"

    # Material management

    def add_material(
        self,
        content: Any,
        facts: List[str],
        difficulty: float = 0.5
    ) -> StudyMaterial:
        """Add study material."""
        material = StudyMaterial(
            id=self._generate_material_id(),
            content=content,
            facts=facts,
            difficulty=difficulty
        )

        self._materials[material.id] = material
        self._memory.initialize_item(material.id)

        return material

    # Study and test

    def study(
        self,
        material_id: str
    ) -> Dict[str, Any]:
        """Study (restudy) material."""
        if material_id not in self._materials:
            raise ValueError(f"Material {material_id} not found")

        storage, retrieval = self._memory.restudy(material_id)

        return {
            'type': 'restudy',
            'material_id': material_id,
            'storage_strength': storage,
            'retrieval_strength': retrieval
        }

    def test(
        self,
        material_id: str,
        practice_type: PracticeType = PracticeType.FREE_RECALL
    ) -> TestItem:
        """Generate test for material."""
        if material_id not in self._materials:
            raise ValueError(f"Material {material_id} not found")

        material = self._materials[material_id]

        if practice_type == PracticeType.FREE_RECALL:
            test_item = self._generator.generate_free_recall(material)
        elif practice_type == PracticeType.CUED_RECALL:
            test_item = self._generator.generate_cued_recall(material)
        elif practice_type == PracticeType.RECOGNITION:
            all_facts = [f for m in self._materials.values() for f in m.facts]
            test_item = self._generator.generate_recognition(material, all_facts)
        else:
            test_item = self._generator.generate_short_answer(material)

        self._test_items[test_item.id] = test_item
        return test_item

    def answer(
        self,
        test_id: str,
        response: str,
        confidence: float = 0.5,
        feedback_type: FeedbackType = FeedbackType.ANSWER
    ) -> Dict[str, Any]:
        """Answer a test and get feedback."""
        if test_id not in self._test_items:
            raise ValueError(f"Test {test_id} not found")

        test_item = self._test_items[test_id]

        # Simple correctness check
        correct = response.lower().strip() in test_item.answer.lower()

        # Update memory
        storage, retrieval = self._memory.test(test_item.material_id, correct)

        # Record attempt
        attempt = TestAttempt(
            item_id=test_id,
            response=response,
            correct=correct,
            response_time=0.0,
            confidence=confidence,
            timestamp=time.time()
        )
        self._attempts.append(attempt)

        # Get feedback
        feedback = self._feedback.provide_feedback(
            test_item, response, correct, feedback_type
        )

        feedback['storage_strength'] = storage
        feedback['retrieval_strength'] = retrieval

        return feedback

    # Predictions

    def predict_retention(
        self,
        practice_type: PracticeType,
        interval: RetentionInterval,
        repetitions: int = 1
    ) -> float:
        """Predict retention rate."""
        return self._predictor.predict_retention(practice_type, interval, repetitions)

    def get_testing_advantage(
        self,
        interval: RetentionInterval = RetentionInterval.LONG
    ) -> float:
        """Get advantage of testing over restudying."""
        return self._predictor.calculate_testing_advantage(interval)

    def compare_strategies(
        self,
        interval: RetentionInterval = RetentionInterval.MEDIUM
    ) -> Dict[str, float]:
        """Compare different practice strategies."""
        return {
            practice_type.name: self.predict_retention(practice_type, interval)
            for practice_type in PracticeType
        }

    # Analysis

    def get_recall_probability(
        self,
        material_id: str
    ) -> float:
        """Get current recall probability."""
        return self._memory.recall_probability(material_id)

    def get_learning_curve(
        self,
        material_id: str
    ) -> LearningCurve:
        """Get learning curve for material."""
        attempts = [
            a for a in self._attempts
            if self._test_items.get(a.item_id, TestItem("", material_id, "", "", PracticeType.FREE_RECALL)).material_id == material_id
        ]

        if not attempts:
            return LearningCurve([], [], 0.0)

        # Group by practice count
        accuracy_by_count: Dict[int, List[bool]] = defaultdict(list)
        for i, attempt in enumerate(attempts):
            accuracy_by_count[i + 1].append(attempt.correct)

        practice_counts = list(sorted(accuracy_by_count.keys()))
        accuracy_rates = [
            sum(accuracy_by_count[c]) / len(accuracy_by_count[c])
            for c in practice_counts
        ]

        # Calculate slope
        if len(practice_counts) > 1:
            slope = (accuracy_rates[-1] - accuracy_rates[0]) / len(practice_counts)
        else:
            slope = 0.0

        return LearningCurve(practice_counts, accuracy_rates, slope)

    # Metrics

    def get_metrics(self) -> TestingEffectMetrics:
        """Get testing effect metrics."""
        # Calculate retention rates from actual attempts
        restudy_ret = self.predict_retention(PracticeType.RESTUDY, RetentionInterval.MEDIUM)
        testing_ret = self.predict_retention(PracticeType.FREE_RECALL, RetentionInterval.MEDIUM)

        return TestingEffectMetrics(
            restudy_retention=restudy_ret,
            testing_retention=testing_ret,
            testing_advantage=testing_ret - restudy_ret,
            attempts=len(self._attempts)
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        correct_attempts = sum(1 for a in self._attempts if a.correct)
        return {
            'materials': len(self._materials),
            'test_items': len(self._test_items),
            'attempts': len(self._attempts),
            'accuracy': correct_attempts / len(self._attempts) if self._attempts else 0.0
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_testing_effect_engine() -> TestingEffectEngine:
    """Create testing effect engine."""
    return TestingEffectEngine()


def demonstrate_testing_effect() -> Dict[str, Any]:
    """Demonstrate the testing effect."""
    engine = create_testing_effect_engine()

    # Add material
    material = engine.add_material(
        "Psychology of Learning",
        [
            "Testing enhances long-term retention",
            "Retrieval practice is more effective than restudying",
            "Feedback after testing further improves learning"
        ]
    )

    # Study vs test comparison
    restudy_retention = engine.predict_retention(
        PracticeType.RESTUDY, RetentionInterval.LONG
    )
    testing_retention = engine.predict_retention(
        PracticeType.FREE_RECALL, RetentionInterval.LONG
    )

    return {
        'material_id': material.id,
        'restudy_retention': restudy_retention,
        'testing_retention': testing_retention,
        'testing_advantage': testing_retention - restudy_retention,
        'recommendation': 'Use testing instead of restudying for better long-term retention'
    }


def get_testing_effect_principles() -> Dict[str, str]:
    """Get testing effect principles."""
    return {
        'retrieval_practice': 'Actively retrieving information strengthens memory',
        'desirable_difficulty': 'Effortful retrieval leads to stronger memories',
        'feedback': 'Feedback after testing enhances the effect',
        'transfer': 'Testing improves transfer to new contexts',
        'metacognition': 'Testing provides accurate assessment of learning',
        'spacing': 'Combining testing with spacing maximizes retention',
        'pretesting': 'Even unsuccessful pretests can enhance learning',
        'elaborative_retrieval': 'Generating explanations during retrieval helps'
    }
