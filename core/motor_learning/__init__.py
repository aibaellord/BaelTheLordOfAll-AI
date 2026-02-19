"""
BAEL Motor Learning Engine
============================

Skill acquisition and procedural memory.
Power law of practice.

"Ba'el masters motor skills." — Ba'el
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

logger = logging.getLogger("BAEL.MotorLearning")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class LearningStage(Enum):
    """Stages of motor learning (Fitts & Posner)."""
    COGNITIVE = auto()      # Understanding the task
    ASSOCIATIVE = auto()    # Refining the skill
    AUTONOMOUS = auto()     # Automatic execution


class SkillType(Enum):
    """Types of motor skills."""
    DISCRETE = auto()       # Single action (throw)
    SERIAL = auto()         # Sequence (typing)
    CONTINUOUS = auto()     # Ongoing (steering)


class PracticeType(Enum):
    """Types of practice."""
    BLOCKED = auto()        # AAA BBB CCC
    RANDOM = auto()         # ABC CAB BCA
    VARIABLE = auto()       # Different parameters
    CONSTANT = auto()        # Same parameters


class FeedbackType(Enum):
    """Types of feedback."""
    INTRINSIC = auto()      # Natural sensory feedback
    EXTRINSIC = auto()      # External augmented feedback
    KNOWLEDGE_OF_RESULTS = auto()
    KNOWLEDGE_OF_PERFORMANCE = auto()


@dataclass
class MotorSkill:
    """
    A motor skill.
    """
    id: str
    name: str
    skill_type: SkillType
    components: List[str]
    base_error: float
    min_error: float


@dataclass
class PracticeTrial:
    """
    A practice trial.
    """
    trial_number: int
    skill_id: str
    performance_error: float
    execution_time: float
    feedback_received: FeedbackType


@dataclass
class SkillState:
    """
    Current state of a skill.
    """
    skill_id: str
    current_error: float
    current_speed: float
    practice_count: int
    learning_stage: LearningStage
    retention_strength: float


@dataclass
class TransferResult:
    """
    Result of skill transfer test.
    """
    source_skill: str
    target_skill: str
    transfer_amount: float
    transfer_type: str  # positive, negative, zero


@dataclass
class MotorLearningMetrics:
    """
    Motor learning metrics.
    """
    acquisition_rate: float
    retention: float
    transfer: float
    power_law_fit: float


# ============================================================================
# POWER LAW MODEL
# ============================================================================

class PowerLawModel:
    """
    Power Law of Practice.
    Performance = a * Practice^(-b)

    "Ba'el's practice curve." — Ba'el
    """

    def __init__(
        self,
        initial_performance: float = 1.0,
        learning_rate: float = 0.3,
        asymptote: float = 0.1
    ):
        """Initialize model."""
        self._a = initial_performance - asymptote  # Scaling
        self._b = learning_rate                     # Rate
        self._c = asymptote                         # Minimum error

        self._lock = threading.RLock()

    def predict_performance(
        self,
        practice_count: int
    ) -> float:
        """Predict performance (error) at given practice count."""
        if practice_count <= 0:
            return self._a + self._c

        # Power law: T = a * N^(-b) + c
        error = self._a * (practice_count ** (-self._b)) + self._c
        return max(self._c, error)

    def predict_speed(
        self,
        practice_count: int,
        base_time: float = 1000
    ) -> float:
        """Predict execution speed at given practice count."""
        if practice_count <= 0:
            return base_time

        # Speed increases with practice (time decreases)
        time = base_time * (practice_count ** (-self._b * 0.5))
        return max(base_time * 0.2, time)  # Minimum 20% of base

    def fit_to_data(
        self,
        practice_counts: List[int],
        performances: List[float]
    ) -> float:
        """Fit model to data and return R²."""
        if len(practice_counts) != len(performances):
            return 0.0

        # Simple R² calculation
        predictions = [self.predict_performance(n) for n in practice_counts]

        mean_actual = sum(performances) / len(performances)
        ss_tot = sum((y - mean_actual) ** 2 for y in performances)
        ss_res = sum((y - pred) ** 2 for y, pred in zip(performances, predictions))

        if ss_tot == 0:
            return 1.0

        r_squared = 1 - (ss_res / ss_tot)
        return max(0, r_squared)


# ============================================================================
# SKILL MEMORY
# ============================================================================

class ProceduralMemory:
    """
    Procedural memory for motor skills.

    "Ba'el's skill memory." — Ba'el
    """

    def __init__(self):
        """Initialize memory."""
        self._skills: Dict[str, MotorSkill] = {}
        self._states: Dict[str, SkillState] = {}
        self._practice_history: Dict[str, List[PracticeTrial]] = defaultdict(list)

        self._power_models: Dict[str, PowerLawModel] = {}

        self._lock = threading.RLock()

    def register_skill(
        self,
        skill: MotorSkill
    ) -> None:
        """Register a new skill."""
        self._skills[skill.id] = skill

        # Initialize state
        self._states[skill.id] = SkillState(
            skill_id=skill.id,
            current_error=skill.base_error,
            current_speed=1000,  # Base time in ms
            practice_count=0,
            learning_stage=LearningStage.COGNITIVE,
            retention_strength=0.0
        )

        # Initialize power law model
        self._power_models[skill.id] = PowerLawModel(
            initial_performance=skill.base_error,
            learning_rate=0.3,
            asymptote=skill.min_error
        )

    def practice(
        self,
        skill_id: str,
        feedback_type: FeedbackType = FeedbackType.KNOWLEDGE_OF_RESULTS
    ) -> PracticeTrial:
        """Perform practice trial."""
        skill = self._skills.get(skill_id)
        state = self._states.get(skill_id)
        model = self._power_models.get(skill_id)

        if not skill or not state or not model:
            raise ValueError(f"Unknown skill: {skill_id}")

        # Increment practice count
        state.practice_count += 1

        # Predict performance based on power law
        predicted_error = model.predict_performance(state.practice_count)
        predicted_speed = model.predict_speed(state.practice_count)

        # Add noise
        actual_error = predicted_error + random.gauss(0, predicted_error * 0.1)
        actual_speed = predicted_speed + random.gauss(0, predicted_speed * 0.1)

        # Update state
        state.current_error = max(skill.min_error, actual_error)
        state.current_speed = max(200, actual_speed)  # Min 200ms
        state.retention_strength = min(1.0, state.practice_count / 100)

        # Update learning stage
        if state.practice_count < 10:
            state.learning_stage = LearningStage.COGNITIVE
        elif state.practice_count < 100:
            state.learning_stage = LearningStage.ASSOCIATIVE
        else:
            state.learning_stage = LearningStage.AUTONOMOUS

        # Create trial record
        trial = PracticeTrial(
            trial_number=state.practice_count,
            skill_id=skill_id,
            performance_error=state.current_error,
            execution_time=state.current_speed,
            feedback_received=feedback_type
        )

        self._practice_history[skill_id].append(trial)

        return trial

    def test_retention(
        self,
        skill_id: str,
        delay_days: float
    ) -> float:
        """Test skill retention after delay."""
        state = self._states.get(skill_id)
        skill = self._skills.get(skill_id)

        if not state or not skill:
            return 0.0

        # Retention decay
        # Procedural memories are resistant but not immune to forgetting
        decay = math.exp(-delay_days / 30)  # Slow decay

        # Skills at autonomous stage retain better
        if state.learning_stage == LearningStage.AUTONOMOUS:
            decay = decay ** 0.5  # Less forgetting

        retained_performance = state.current_error + (skill.base_error - state.current_error) * (1 - decay)

        return retained_performance

    def get_skill_state(
        self,
        skill_id: str
    ) -> Optional[SkillState]:
        """Get current skill state."""
        return self._states.get(skill_id)

    def get_learning_curve(
        self,
        skill_id: str
    ) -> List[Tuple[int, float]]:
        """Get learning curve data."""
        history = self._practice_history.get(skill_id, [])
        return [(t.trial_number, t.performance_error) for t in history]


# ============================================================================
# PRACTICE SCHEDULER
# ============================================================================

class PracticeScheduler:
    """
    Schedules practice for optimal learning.

    "Ba'el optimizes practice." — Ba'el
    """

    def __init__(
        self,
        memory: ProceduralMemory
    ):
        """Initialize scheduler."""
        self._memory = memory
        self._lock = threading.RLock()

    def blocked_practice(
        self,
        skill_ids: List[str],
        trials_per_skill: int = 10
    ) -> List[str]:
        """Create blocked practice schedule."""
        schedule = []
        for skill_id in skill_ids:
            schedule.extend([skill_id] * trials_per_skill)
        return schedule

    def random_practice(
        self,
        skill_ids: List[str],
        trials_per_skill: int = 10
    ) -> List[str]:
        """Create random practice schedule."""
        schedule = []
        for skill_id in skill_ids:
            schedule.extend([skill_id] * trials_per_skill)
        random.shuffle(schedule)
        return schedule

    def run_practice_schedule(
        self,
        schedule: List[str],
        feedback_type: FeedbackType = FeedbackType.KNOWLEDGE_OF_RESULTS
    ) -> List[PracticeTrial]:
        """Execute practice schedule."""
        trials = []
        for skill_id in schedule:
            trial = self._memory.practice(skill_id, feedback_type)
            trials.append(trial)
        return trials

    def compare_practice_types(
        self,
        skill_ids: List[str],
        trials_per_skill: int = 20
    ) -> Dict[str, Any]:
        """Compare blocked vs random practice."""
        # Blocked practice
        blocked_memory = ProceduralMemory()
        for sid in skill_ids:
            skill = self._memory._skills.get(sid)
            if skill:
                blocked_memory.register_skill(copy.deepcopy(skill))

        blocked_sched = self.blocked_practice(skill_ids, trials_per_skill)
        blocked_trials = []
        for sid in blocked_sched:
            blocked_trials.append(blocked_memory.practice(sid))

        # Random practice
        random_memory = ProceduralMemory()
        for sid in skill_ids:
            skill = self._memory._skills.get(sid)
            if skill:
                random_memory.register_skill(copy.deepcopy(skill))

        random_sched = self.random_practice(skill_ids, trials_per_skill)
        random_trials = []
        for sid in random_sched:
            random_trials.append(random_memory.practice(sid))

        # Calculate final performance
        blocked_final = {
            sid: blocked_memory.get_skill_state(sid).current_error
            for sid in skill_ids
        }
        random_final = {
            sid: random_memory.get_skill_state(sid).current_error
            for sid in skill_ids
        }

        # Test retention
        delay_days = 7
        blocked_retention = {
            sid: blocked_memory.test_retention(sid, delay_days)
            for sid in skill_ids
        }
        random_retention = {
            sid: random_memory.test_retention(sid, delay_days)
            for sid in skill_ids
        }

        return {
            'blocked': {
                'final_performance': blocked_final,
                'retention': blocked_retention
            },
            'random': {
                'final_performance': random_final,
                'retention': random_retention
            },
            'contextual_interference': (
                sum(blocked_final.values()) / len(blocked_final) <
                sum(random_final.values()) / len(random_final)  # Lower = better
            ),
            'retention_advantage_random': (
                sum(random_retention.values()) / len(random_retention) <
                sum(blocked_retention.values()) / len(blocked_retention)
            )
        }


# ============================================================================
# SKILL TRANSFER
# ============================================================================

class SkillTransfer:
    """
    Handles skill transfer.

    "Ba'el transfers skills." — Ba'el
    """

    def __init__(
        self,
        memory: ProceduralMemory
    ):
        """Initialize transfer handler."""
        self._memory = memory
        self._lock = threading.RLock()

    def calculate_similarity(
        self,
        skill1: MotorSkill,
        skill2: MotorSkill
    ) -> float:
        """Calculate skill similarity."""
        # Component overlap
        common = set(skill1.components) & set(skill2.components)
        total = set(skill1.components) | set(skill2.components)

        component_sim = len(common) / len(total) if total else 0

        # Same type bonus
        type_sim = 1.0 if skill1.skill_type == skill2.skill_type else 0.5

        return (component_sim + type_sim) / 2

    def test_transfer(
        self,
        source_skill_id: str,
        target_skill_id: str
    ) -> TransferResult:
        """Test transfer from source to target skill."""
        source_skill = self._memory._skills.get(source_skill_id)
        target_skill = self._memory._skills.get(target_skill_id)

        if not source_skill or not target_skill:
            return TransferResult(
                source_skill=source_skill_id,
                target_skill=target_skill_id,
                transfer_amount=0.0,
                transfer_type="zero"
            )

        source_state = self._memory.get_skill_state(source_skill_id)

        # Calculate similarity
        similarity = self.calculate_similarity(source_skill, target_skill)

        # Transfer amount depends on source proficiency and similarity
        if source_state:
            source_proficiency = 1 - (source_state.current_error / source_skill.base_error)
            transfer = similarity * source_proficiency * 0.5
        else:
            transfer = 0.0

        # Determine transfer type
        if transfer > 0.1:
            transfer_type = "positive"
        elif transfer < -0.1:
            transfer_type = "negative"
        else:
            transfer_type = "zero"

        return TransferResult(
            source_skill=source_skill_id,
            target_skill=target_skill_id,
            transfer_amount=transfer,
            transfer_type=transfer_type
        )


# ============================================================================
# MOTOR LEARNING ENGINE
# ============================================================================

class MotorLearningEngine:
    """
    Complete motor learning engine.

    "Ba'el's motor learning system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._memory = ProceduralMemory()
        self._scheduler = PracticeScheduler(self._memory)
        self._transfer = SkillTransfer(self._memory)

        self._skill_counter = 0
        self._lock = threading.RLock()

    def _generate_skill_id(self) -> str:
        self._skill_counter += 1
        return f"skill_{self._skill_counter}"

    # Skill management

    def create_skill(
        self,
        name: str,
        skill_type: SkillType = SkillType.DISCRETE,
        components: List[str] = None,
        difficulty: float = 0.5
    ) -> MotorSkill:
        """Create a new motor skill."""
        skill = MotorSkill(
            id=self._generate_skill_id(),
            name=name,
            skill_type=skill_type,
            components=components or [],
            base_error=difficulty,
            min_error=difficulty * 0.1
        )

        self._memory.register_skill(skill)
        return skill

    def practice_skill(
        self,
        skill_id: str,
        n_trials: int = 1
    ) -> List[PracticeTrial]:
        """Practice a skill."""
        trials = []
        for _ in range(n_trials):
            trial = self._memory.practice(skill_id)
            trials.append(trial)
        return trials

    def get_skill_state(
        self,
        skill_id: str
    ) -> Optional[SkillState]:
        """Get skill state."""
        return self._memory.get_skill_state(skill_id)

    def get_learning_curve(
        self,
        skill_id: str
    ) -> List[Tuple[int, float]]:
        """Get learning curve."""
        return self._memory.get_learning_curve(skill_id)

    # Practice scheduling

    def run_blocked_practice(
        self,
        skill_ids: List[str],
        trials_per_skill: int = 10
    ) -> List[PracticeTrial]:
        """Run blocked practice."""
        schedule = self._scheduler.blocked_practice(skill_ids, trials_per_skill)
        return self._scheduler.run_practice_schedule(schedule)

    def run_random_practice(
        self,
        skill_ids: List[str],
        trials_per_skill: int = 10
    ) -> List[PracticeTrial]:
        """Run random practice."""
        schedule = self._scheduler.random_practice(skill_ids, trials_per_skill)
        return self._scheduler.run_practice_schedule(schedule)

    def compare_practice_types(
        self,
        skill_ids: List[str],
        trials_per_skill: int = 20
    ) -> Dict[str, Any]:
        """Compare practice types."""
        return self._scheduler.compare_practice_types(skill_ids, trials_per_skill)

    # Retention and transfer

    def test_retention(
        self,
        skill_id: str,
        delay_days: float
    ) -> float:
        """Test skill retention."""
        return self._memory.test_retention(skill_id, delay_days)

    def test_transfer(
        self,
        source_id: str,
        target_id: str
    ) -> TransferResult:
        """Test skill transfer."""
        return self._transfer.test_transfer(source_id, target_id)

    # Analysis

    def get_metrics(self) -> MotorLearningMetrics:
        """Get motor learning metrics."""
        all_states = list(self._memory._states.values())

        if not all_states:
            return MotorLearningMetrics(
                acquisition_rate=0.0,
                retention=0.0,
                transfer=0.0,
                power_law_fit=0.0
            )

        # Acquisition: average reduction in error
        avg_improvement = sum(
            1 - (s.current_error / self._memory._skills[s.skill_id].base_error)
            for s in all_states
        ) / len(all_states)

        # Retention: average retention strength
        avg_retention = sum(s.retention_strength for s in all_states) / len(all_states)

        # Power law fit
        fits = []
        for skill_id in self._memory._skills:
            curve = self.get_learning_curve(skill_id)
            if len(curve) > 3:
                model = self._memory._power_models.get(skill_id)
                if model:
                    r2 = model.fit_to_data(
                        [c[0] for c in curve],
                        [c[1] for c in curve]
                    )
                    fits.append(r2)

        avg_fit = sum(fits) / len(fits) if fits else 0.0

        return MotorLearningMetrics(
            acquisition_rate=avg_improvement,
            retention=avg_retention,
            transfer=0.5,  # Would need actual transfer tests
            power_law_fit=avg_fit
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'skills': len(self._memory._skills),
            'total_trials': sum(
                len(h) for h in self._memory._practice_history.values()
            )
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_motor_learning_engine() -> MotorLearningEngine:
    """Create motor learning engine."""
    return MotorLearningEngine()


def demonstrate_motor_learning() -> Dict[str, Any]:
    """Demonstrate motor learning."""
    engine = create_motor_learning_engine()

    # Create skills
    throw = engine.create_skill("throwing", SkillType.DISCRETE, ["arm", "release"], 0.6)
    type_skill = engine.create_skill("typing", SkillType.SERIAL, ["finger", "eye"], 0.5)
    drive = engine.create_skill("driving", SkillType.CONTINUOUS, ["steering", "pedal"], 0.7)

    # Practice
    trials = engine.practice_skill(throw.id, 50)

    # Get learning curve
    curve = engine.get_learning_curve(throw.id)

    # Get state
    state = engine.get_skill_state(throw.id)

    # Test retention
    retention = engine.test_retention(throw.id, 7)

    metrics = engine.get_metrics()

    return {
        'skill': throw.name,
        'practice_trials': len(trials),
        'initial_error': f"{throw.base_error:.2f}",
        'final_error': f"{state.current_error:.2f}" if state else "N/A",
        'learning_stage': state.learning_stage.name if state else "N/A",
        'retention_7_days': f"{retention:.2f}",
        'power_law_fit': f"{metrics.power_law_fit:.2f}",
        'interpretation': (
            f"After {len(trials)} trials, error reduced from {throw.base_error:.2f} to {state.current_error:.2f}. "
            f"Stage: {state.learning_stage.name}"
        )
    }


def get_motor_learning_facts() -> Dict[str, str]:
    """Get facts about motor learning."""
    return {
        'power_law': 'Practice follows power law: rapid initial gains, gradual improvement',
        'fitts_posner': 'Three stages: cognitive, associative, autonomous',
        'contextual_interference': 'Random practice hurts acquisition but helps retention',
        'specificity': 'Learning is specific to practiced conditions',
        'transfer': 'Skills transfer based on shared components',
        'feedback': 'Augmented feedback can help or hurt depending on timing',
        'schema_theory': 'Generalized motor programs are parameterized',
        'implicit_learning': 'Much motor learning occurs without awareness'
    }
