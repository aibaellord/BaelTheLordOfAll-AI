"""
BAEL Retrieval Practice Engine
================================

Testing effect and retrieval-based learning.
Roediger & Karpicke's work.

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

logger = logging.getLogger("BAEL.RetrievalPractice")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class PracticeType(Enum):
    """Types of practice."""
    RESTUDY = auto()          # Read again
    FREE_RECALL = auto()      # Recall without cues
    CUED_RECALL = auto()      # Recall with cues
    RECOGNITION = auto()       # Choose from options
    SHORT_ANSWER = auto()      # Written response


class TestFormat(Enum):
    """Test format types."""
    FILL_IN_BLANK = auto()
    MULTIPLE_CHOICE = auto()
    FREE_RESPONSE = auto()
    TRUE_FALSE = auto()


class RetentionInterval(Enum):
    """Retention test intervals."""
    IMMEDIATE = auto()        # Right after study
    SHORT = auto()            # Minutes to hours
    MEDIUM = auto()           # Days
    LONG = auto()             # Weeks to months


@dataclass
class StudyItem:
    """
    An item to study.
    """
    id: str
    content: str
    cue: str
    category: str
    difficulty: float


@dataclass
class StudyTrial:
    """
    A single study trial.
    """
    item_id: str
    practice_type: PracticeType
    success: bool
    latency: float
    timestamp: float


@dataclass
class TestResult:
    """
    Result of a test trial.
    """
    item_id: str
    recalled: bool
    confidence: float
    latency: float
    retention_interval: RetentionInterval


@dataclass
class TestingEffect:
    """
    Testing effect measurement.
    """
    restudy_retention: float
    testing_retention: float
    testing_advantage: float
    effect_significant: bool


@dataclass
class RetrievalMetrics:
    """
    Retrieval practice metrics.
    """
    testing_effect_size: float
    retention_slope: float
    practice_retrievals: int
    success_rate: float


# ============================================================================
# MEMORY MODEL
# ============================================================================

class RetrievalMemoryModel:
    """
    Memory model with retrieval strengthening.

    "Ba'el's testing-enhanced memory." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        self._items: Dict[str, StudyItem] = {}
        self._memory_strengths: Dict[str, Dict[str, float]] = {}  # item -> route -> strength

        # Two routes: storage strength and retrieval strength
        # Testing enhances retrieval strength more

        self._item_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._item_counter += 1
        return f"item_{self._item_counter}"

    def add_item(
        self,
        content: str,
        cue: str,
        category: str = "general",
        difficulty: float = 0.5
    ) -> StudyItem:
        """Add a study item."""
        item = StudyItem(
            id=self._generate_id(),
            content=content,
            cue=cue,
            category=category,
            difficulty=difficulty
        )

        self._items[item.id] = item
        self._memory_strengths[item.id] = {
            'storage': 0.0,
            'retrieval': 0.0
        }

        return item

    def restudy(
        self,
        item_id: str,
        duration: float = 1.0
    ) -> StudyTrial:
        """Restudy an item (passive exposure)."""
        item = self._items.get(item_id)
        if not item:
            return None

        strengths = self._memory_strengths[item_id]

        # Restudying mainly increases storage strength
        storage_gain = 0.1 * duration * (1 - strengths['storage'])
        retrieval_gain = 0.02 * duration * (1 - strengths['retrieval'])

        strengths['storage'] = min(1.0, strengths['storage'] + storage_gain)
        strengths['retrieval'] = min(1.0, strengths['retrieval'] + retrieval_gain)

        return StudyTrial(
            item_id=item_id,
            practice_type=PracticeType.RESTUDY,
            success=True,  # Passive, always "success"
            latency=duration,
            timestamp=time.time()
        )

    def retrieval_practice(
        self,
        item_id: str,
        practice_type: PracticeType = PracticeType.FREE_RECALL
    ) -> StudyTrial:
        """Practice retrieving an item."""
        item = self._items.get(item_id)
        if not item:
            return None

        strengths = self._memory_strengths[item_id]

        # Retrieval probability based on current strengths
        total_strength = 0.4 * strengths['storage'] + 0.6 * strengths['retrieval']

        # Difficulty affects success
        adjusted_prob = total_strength * (1 - item.difficulty * 0.3)

        # Practice type affects difficulty
        if practice_type == PracticeType.RECOGNITION:
            adjusted_prob += 0.2  # Recognition is easier
        elif practice_type == PracticeType.FREE_RECALL:
            adjusted_prob -= 0.1  # Free recall is harder

        success = random.random() < adjusted_prob

        # Successful retrieval greatly enhances retrieval strength
        if success:
            # Testing effect: retrieval strengthens memory more than restudy
            retrieval_gain = 0.25 * (1 - strengths['retrieval'])
            storage_gain = 0.1 * (1 - strengths['storage'])

            strengths['retrieval'] = min(1.0, strengths['retrieval'] + retrieval_gain)
            strengths['storage'] = min(1.0, strengths['storage'] + storage_gain)
        else:
            # Failed retrieval + feedback still helps some
            retrieval_gain = 0.08 * (1 - strengths['retrieval'])
            strengths['retrieval'] = min(1.0, strengths['retrieval'] + retrieval_gain)

        latency = 1.0 / (total_strength + 0.1) + random.uniform(0, 0.5)

        return StudyTrial(
            item_id=item_id,
            practice_type=practice_type,
            success=success,
            latency=latency,
            timestamp=time.time()
        )

    def decay_memory(
        self,
        item_id: str,
        time_units: float
    ) -> None:
        """Apply memory decay over time."""
        strengths = self._memory_strengths.get(item_id)
        if not strengths:
            return

        # Storage strength decays slower than retrieval strength
        # But high retrieval strength protects storage
        retrieval_protection = 0.3 * strengths['retrieval']

        storage_decay = 0.05 * time_units * (1 - retrieval_protection)
        retrieval_decay = 0.1 * time_units

        strengths['storage'] = max(0, strengths['storage'] - storage_decay)
        strengths['retrieval'] = max(0, strengths['retrieval'] - retrieval_decay)

    def test_retention(
        self,
        item_id: str,
        interval: RetentionInterval
    ) -> TestResult:
        """Test retention after interval."""
        item = self._items.get(item_id)
        if not item:
            return None

        # Apply decay based on interval
        if interval == RetentionInterval.IMMEDIATE:
            time_units = 0
        elif interval == RetentionInterval.SHORT:
            time_units = 1
        elif interval == RetentionInterval.MEDIUM:
            time_units = 5
        else:  # LONG
            time_units = 20

        # Temporary copy for test without modifying actual state
        strengths = self._memory_strengths[item_id].copy()

        storage_decay = 0.05 * time_units
        retrieval_decay = 0.1 * time_units

        test_storage = max(0, strengths['storage'] - storage_decay)
        test_retrieval = max(0, strengths['retrieval'] - retrieval_decay)

        # Recall probability
        recall_prob = 0.4 * test_storage + 0.6 * test_retrieval
        recalled = random.random() < recall_prob

        return TestResult(
            item_id=item_id,
            recalled=recalled,
            confidence=recall_prob,
            latency=1.0 / (recall_prob + 0.1),
            retention_interval=interval
        )

    def get_strength(
        self,
        item_id: str
    ) -> Dict[str, float]:
        """Get memory strengths."""
        return self._memory_strengths.get(item_id, {})


# ============================================================================
# EXPERIMENTAL PARADIGM
# ============================================================================

class TestingEffectExperiment:
    """
    Testing effect experiment paradigm.

    "Ba'el demonstrates testing's power." — Ba'el
    """

    def __init__(
        self,
        memory: RetrievalMemoryModel
    ):
        """Initialize experiment."""
        self._memory = memory
        self._study_group: List[str] = []
        self._test_group: List[str] = []

        self._study_results: List[StudyTrial] = []
        self._test_results: List[TestResult] = []

        self._lock = threading.RLock()

    def setup_experiment(
        self,
        items: List[Tuple[str, str]],  # (content, cue) pairs
        n_per_condition: int = None
    ) -> None:
        """Setup experiment with items."""
        n = n_per_condition or len(items) // 2

        # Create and add items
        all_items = []
        for content, cue in items:
            item = self._memory.add_item(content, cue)
            all_items.append(item.id)

        # Random assignment
        random.shuffle(all_items)
        self._study_group = all_items[:n]
        self._test_group = all_items[n:2*n]

    def initial_study_phase(
        self,
        duration_per_item: float = 2.0
    ) -> None:
        """Initial study for both groups."""
        for item_id in self._study_group + self._test_group:
            self._memory.restudy(item_id, duration_per_item)

    def practice_phase(
        self,
        repetitions: int = 3
    ) -> None:
        """Practice phase: restudy vs testing."""
        for _ in range(repetitions):
            # Study group restudies
            for item_id in self._study_group:
                trial = self._memory.restudy(item_id)
                self._study_results.append(trial)

            # Test group practices retrieval
            for item_id in self._test_group:
                trial = self._memory.retrieval_practice(item_id)
                self._study_results.append(trial)

    def final_test(
        self,
        interval: RetentionInterval = RetentionInterval.MEDIUM
    ) -> TestingEffect:
        """Final retention test."""
        study_correct = 0
        test_correct = 0

        # Test study group
        for item_id in self._study_group:
            result = self._memory.test_retention(item_id, interval)
            self._test_results.append(result)
            if result.recalled:
                study_correct += 1

        # Test test group
        for item_id in self._test_group:
            result = self._memory.test_retention(item_id, interval)
            self._test_results.append(result)
            if result.recalled:
                test_correct += 1

        # Calculate testing effect
        study_retention = study_correct / len(self._study_group) if self._study_group else 0
        test_retention = test_correct / len(self._test_group) if self._test_group else 0

        advantage = test_retention - study_retention

        return TestingEffect(
            restudy_retention=study_retention,
            testing_retention=test_retention,
            testing_advantage=advantage,
            effect_significant=advantage > 0.1
        )


# ============================================================================
# RETRIEVAL PRACTICE ENGINE
# ============================================================================

class RetrievalPracticeEngine:
    """
    Complete retrieval practice engine.

    "Ba'el's learning through testing." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._memory = RetrievalMemoryModel()
        self._study_history: List[StudyTrial] = []
        self._test_history: List[TestResult] = []

        self._lock = threading.RLock()

    # Item management

    def add_item(
        self,
        content: str,
        cue: str,
        category: str = "general",
        difficulty: float = 0.5
    ) -> StudyItem:
        """Add a study item."""
        return self._memory.add_item(content, cue, category, difficulty)

    # Study methods

    def restudy(
        self,
        item_id: str,
        duration: float = 1.0
    ) -> StudyTrial:
        """Restudy an item."""
        trial = self._memory.restudy(item_id, duration)
        if trial:
            self._study_history.append(trial)
        return trial

    def practice_retrieval(
        self,
        item_id: str,
        practice_type: PracticeType = PracticeType.CUED_RECALL
    ) -> StudyTrial:
        """Practice retrieving an item."""
        trial = self._memory.retrieval_practice(item_id, practice_type)
        if trial:
            self._study_history.append(trial)
        return trial

    def test(
        self,
        item_id: str,
        interval: RetentionInterval = RetentionInterval.IMMEDIATE
    ) -> TestResult:
        """Test retention."""
        result = self._memory.test_retention(item_id, interval)
        if result:
            self._test_history.append(result)
        return result

    # Optimized study schedule

    def optimal_practice_schedule(
        self,
        item_id: str,
        target_retention: float = 0.9,
        max_practices: int = 10
    ) -> List[PracticeType]:
        """Generate optimal practice schedule."""
        schedule = []
        strengths = self._memory.get_strength(item_id)

        # Initial storage if needed
        if strengths.get('storage', 0) < 0.3:
            schedule.append(PracticeType.RESTUDY)

        # Build retrieval strength through testing
        current_retrieval = strengths.get('retrieval', 0)

        while current_retrieval < target_retention and len(schedule) < max_practices:
            # Retrieval practice is more effective
            schedule.append(PracticeType.CUED_RECALL)
            current_retrieval += 0.2 * (1 - current_retrieval)

        return schedule

    def execute_schedule(
        self,
        item_id: str,
        schedule: List[PracticeType]
    ) -> List[StudyTrial]:
        """Execute a practice schedule."""
        trials = []

        for practice_type in schedule:
            if practice_type == PracticeType.RESTUDY:
                trial = self.restudy(item_id)
            else:
                trial = self.practice_retrieval(item_id, practice_type)

            if trial:
                trials.append(trial)

        return trials

    # Run testing effect experiment

    def run_testing_effect_experiment(
        self,
        items: List[Tuple[str, str]],
        practice_reps: int = 3,
        test_interval: RetentionInterval = RetentionInterval.MEDIUM
    ) -> TestingEffect:
        """Run a testing effect experiment."""
        experiment = TestingEffectExperiment(self._memory)

        experiment.setup_experiment(items)
        experiment.initial_study_phase()
        experiment.practice_phase(practice_reps)

        return experiment.final_test(test_interval)

    # Analysis

    def get_testing_effect_estimate(self) -> float:
        """Estimate testing effect from history."""
        restudy_trials = [
            t for t in self._study_history
            if t.practice_type == PracticeType.RESTUDY
        ]
        retrieval_trials = [
            t for t in self._study_history
            if t.practice_type in [PracticeType.FREE_RECALL, PracticeType.CUED_RECALL]
        ]

        if not retrieval_trials:
            return 0.0

        # Get items from each type
        restudy_items = set(t.item_id for t in restudy_trials)
        retrieval_items = set(t.item_id for t in retrieval_trials)

        # Test results for each group
        restudy_tests = [
            t for t in self._test_history
            if t.item_id in restudy_items
        ]
        retrieval_tests = [
            t for t in self._test_history
            if t.item_id in retrieval_items
        ]

        if not restudy_tests or not retrieval_tests:
            return 0.0

        restudy_acc = sum(1 for t in restudy_tests if t.recalled) / len(restudy_tests)
        retrieval_acc = sum(1 for t in retrieval_tests if t.recalled) / len(retrieval_tests)

        return retrieval_acc - restudy_acc

    def get_metrics(self) -> RetrievalMetrics:
        """Get retrieval practice metrics."""
        retrieval_trials = [
            t for t in self._study_history
            if t.practice_type != PracticeType.RESTUDY
        ]

        if not retrieval_trials:
            return RetrievalMetrics(
                testing_effect_size=0.0,
                retention_slope=0.0,
                practice_retrievals=0,
                success_rate=0.0
            )

        success_rate = sum(1 for t in retrieval_trials if t.success) / len(retrieval_trials)

        return RetrievalMetrics(
            testing_effect_size=self.get_testing_effect_estimate(),
            retention_slope=0.0,  # Would need multiple time points
            practice_retrievals=len(retrieval_trials),
            success_rate=success_rate
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'items': len(self._memory._items),
            'study_trials': len(self._study_history),
            'test_trials': len(self._test_history),
            'retrieval_practices': sum(
                1 for t in self._study_history
                if t.practice_type != PracticeType.RESTUDY
            )
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_retrieval_practice_engine() -> RetrievalPracticeEngine:
    """Create retrieval practice engine."""
    return RetrievalPracticeEngine()


def demonstrate_retrieval_practice() -> Dict[str, Any]:
    """Demonstrate retrieval practice."""
    engine = create_retrieval_practice_engine()

    # Create items
    items = [
        ("The mitochondria is the powerhouse of the cell", "cell organelle"),
        ("Water boils at 100 degrees Celsius at sea level", "water boiling"),
        ("The capital of France is Paris", "France capital"),
        ("E = mc^2 is Einstein's famous equation", "Einstein equation"),
        ("DNA stands for deoxyribonucleic acid", "DNA full name"),
        ("The speed of light is approximately 3x10^8 m/s", "light speed"),
        ("Pythagoras theorem: a^2 + b^2 = c^2", "right triangle"),
        ("The Great Wall of China is visible from space (myth)", "Great Wall"),
    ]

    # Run testing effect experiment
    effect = engine.run_testing_effect_experiment(
        items,
        practice_reps=3,
        test_interval=RetentionInterval.MEDIUM
    )

    metrics = engine.get_metrics()

    return {
        'testing_effect': {
            'restudy_retention': f"{effect.restudy_retention:.0%}",
            'testing_retention': f"{effect.testing_retention:.0%}",
            'advantage': f"{effect.testing_advantage:.0%}",
            'significant': effect.effect_significant
        },
        'practice_success_rate': f"{metrics.success_rate:.0%}",
        'interpretation': (
            f"Testing advantage: {effect.testing_advantage:.0%}. "
            f"Retrieval practice enhances long-term retention."
        )
    }


def get_retrieval_practice_facts() -> Dict[str, str]:
    """Get facts about retrieval practice."""
    return {
        'testing_effect': 'Testing enhances long-term retention more than restudying',
        'roediger_karpicke': 'Pioneering research on retrieval practice benefits',
        'desirable_difficulty': 'Effortful retrieval produces better learning',
        'direct_effect': 'Testing strengthens memory traces',
        'indirect_effect': 'Testing reveals what you do not know',
        'transfer': 'Testing benefits transfer to related material',
        'successive_relearning': 'Combining spacing and retrieval practice',
        'test_enhanced_learning': 'Also called the "testing effect"'
    }
