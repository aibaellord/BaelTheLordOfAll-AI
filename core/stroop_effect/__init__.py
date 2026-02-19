"""
BAEL Stroop Effect Engine
===========================

Interference between automatic and controlled processing.
Stroop's classic color-word task.

"Ba'el manages interference." — Ba'el
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

logger = logging.getLogger("BAEL.StroopEffect")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class Color(Enum):
    """Colors for Stroop task."""
    RED = "red"
    GREEN = "green"
    BLUE = "blue"
    YELLOW = "yellow"
    BLACK = "black"


class TrialType(Enum):
    """Types of Stroop trials."""
    CONGRUENT = auto()      # Word RED in red ink
    INCONGRUENT = auto()    # Word RED in blue ink
    NEUTRAL = auto()         # Word TABLE in red ink
    CONTROL = auto()         # Color patch only


class TaskType(Enum):
    """Types of Stroop tasks."""
    NAME_COLOR = auto()     # Name the ink color
    READ_WORD = auto()      # Read the word


class ProcessType(Enum):
    """Types of processing."""
    AUTOMATIC = auto()      # Reading (over-learned)
    CONTROLLED = auto()     # Color naming


@dataclass
class StroopStimulus:
    """
    A Stroop stimulus.
    """
    id: str
    word: str
    ink_color: Color
    trial_type: TrialType


@dataclass
class StroopTrial:
    """
    A Stroop trial result.
    """
    stimulus_id: str
    trial_type: TrialType
    task_type: TaskType
    response: Color
    correct: bool
    reaction_time_ms: float
    interference: float


@dataclass
class StroopMetrics:
    """
    Stroop effect metrics.
    """
    congruent_rt: float
    incongruent_rt: float
    neutral_rt: float
    stroop_effect: float
    facilitation: float
    interference: float
    accuracy: float


# ============================================================================
# DUAL-ROUTE MODEL
# ============================================================================

class DualRouteProcessor:
    """
    Dual-route model of Stroop processing.

    "Ba'el's parallel pathways." — Ba'el
    """

    def __init__(self):
        """Initialize processor."""
        # Processing parameters
        self._word_reading_speed = 150     # ms (automatic, fast)
        self._color_naming_speed = 350     # ms (controlled, slower)

        # Interference parameters
        self._interference_cost = 100       # ms cost for incongruent
        self._facilitation_benefit = 30     # ms benefit for congruent

        # Accuracy parameters
        self._base_accuracy = 0.95
        self._interference_error = 0.15    # Error rate increase

        self._lock = threading.RLock()

    def process_word_reading(
        self,
        word: str
    ) -> Tuple[str, float]:
        """Process word reading (automatic)."""
        # Very fast, automatic
        rt = self._word_reading_speed + random.gauss(0, 20)
        return word.lower(), max(100, rt)

    def process_color_naming(
        self,
        color: Color,
        word: str,
        trial_type: TrialType
    ) -> Tuple[Color, float, bool]:
        """Process color naming (controlled)."""
        base_rt = self._color_naming_speed

        # Apply trial type effects
        if trial_type == TrialType.INCONGRUENT:
            # Interference: word pathway conflicts
            rt = base_rt + self._interference_cost
            error_rate = self._interference_error
        elif trial_type == TrialType.CONGRUENT:
            # Facilitation: word pathway helps
            rt = base_rt - self._facilitation_benefit
            error_rate = 0.02
        else:  # NEUTRAL or CONTROL
            rt = base_rt
            error_rate = 0.05

        # Add noise
        rt += random.gauss(0, 30)
        rt = max(150, rt)

        # Accuracy
        correct = random.random() > error_rate

        # Response
        if correct:
            response = color
        else:
            # Error: might respond with word color
            if trial_type == TrialType.INCONGRUENT and word.upper() in [c.value.upper() for c in Color]:
                response = Color(word.lower())
            else:
                response = random.choice(list(Color))

        return response, rt, correct


# ============================================================================
# COGNITIVE CONTROL
# ============================================================================

class CognitiveControlUnit:
    """
    Cognitive control for Stroop task.

    "Ba'el's executive control." — Ba'el
    """

    def __init__(self):
        """Initialize control unit."""
        # Control parameters
        self._conflict_threshold = 0.5
        self._adjustment_rate = 0.1

        # Trial-to-trial effects
        self._previous_conflict = 0.0
        self._current_control = 0.5

        self._lock = threading.RLock()

    def detect_conflict(
        self,
        trial_type: TrialType
    ) -> float:
        """Detect conflict level."""
        if trial_type == TrialType.INCONGRUENT:
            return 0.8 + random.gauss(0, 0.1)
        elif trial_type == TrialType.CONGRUENT:
            return 0.1 + random.gauss(0, 0.05)
        else:
            return 0.3 + random.gauss(0, 0.1)

    def adjust_control(
        self,
        conflict: float
    ) -> float:
        """Adjust control based on conflict."""
        # Gratton effect: high conflict increases control
        if conflict > self._conflict_threshold:
            self._current_control += self._adjustment_rate
        else:
            self._current_control -= self._adjustment_rate * 0.5

        self._current_control = max(0, min(1, self._current_control))
        self._previous_conflict = conflict

        return self._current_control

    def modulate_rt(
        self,
        base_rt: float,
        trial_type: TrialType
    ) -> float:
        """Modulate RT based on control state."""
        conflict = self.detect_conflict(trial_type)

        # Higher control = less interference
        control_effect = (1 - self._current_control) * 50

        # Gratton effect: post-conflict trials are faster
        if self._previous_conflict > self._conflict_threshold:
            control_effect *= 0.7

        self.adjust_control(conflict)

        return base_rt + control_effect


# ============================================================================
# EXPERIMENTAL PARADIGM
# ============================================================================

class StroopParadigm:
    """
    Classic Stroop experimental paradigm.

    "Ba'el's Stroop experiment." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._processor = DualRouteProcessor()
        self._control = CognitiveControlUnit()

        self._stimuli: Dict[str, StroopStimulus] = {}
        self._trials: List[StroopTrial] = []

        self._stim_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._stim_counter += 1
        return f"stim_{self._stim_counter}"

    def create_congruent(
        self,
        color: Color
    ) -> StroopStimulus:
        """Create congruent stimulus."""
        stim = StroopStimulus(
            id=self._generate_id(),
            word=color.value.upper(),
            ink_color=color,
            trial_type=TrialType.CONGRUENT
        )
        self._stimuli[stim.id] = stim
        return stim

    def create_incongruent(
        self,
        word_color: Color,
        ink_color: Color
    ) -> StroopStimulus:
        """Create incongruent stimulus."""
        assert word_color != ink_color
        stim = StroopStimulus(
            id=self._generate_id(),
            word=word_color.value.upper(),
            ink_color=ink_color,
            trial_type=TrialType.INCONGRUENT
        )
        self._stimuli[stim.id] = stim
        return stim

    def create_neutral(
        self,
        ink_color: Color,
        word: str = "XXXXX"
    ) -> StroopStimulus:
        """Create neutral stimulus."""
        stim = StroopStimulus(
            id=self._generate_id(),
            word=word,
            ink_color=ink_color,
            trial_type=TrialType.NEUTRAL
        )
        self._stimuli[stim.id] = stim
        return stim

    def run_trial(
        self,
        stimulus: StroopStimulus,
        task: TaskType = TaskType.NAME_COLOR
    ) -> StroopTrial:
        """Run a single trial."""
        if task == TaskType.NAME_COLOR:
            response, rt, correct = self._processor.process_color_naming(
                stimulus.ink_color, stimulus.word, stimulus.trial_type
            )

            # Apply cognitive control modulation
            rt = self._control.modulate_rt(rt, stimulus.trial_type)

            # Calculate interference
            if stimulus.trial_type == TrialType.INCONGRUENT:
                interference = rt - self._processor._color_naming_speed
            else:
                interference = 0

        else:  # READ_WORD
            word_response, rt = self._processor.process_word_reading(stimulus.word)
            # Word reading is largely immune to interference
            correct = True
            response = stimulus.ink_color  # Not used for word reading
            interference = 0

        trial = StroopTrial(
            stimulus_id=stimulus.id,
            trial_type=stimulus.trial_type,
            task_type=task,
            response=response,
            correct=correct,
            reaction_time_ms=rt,
            interference=interference
        )

        self._trials.append(trial)
        return trial

    def run_experiment(
        self,
        n_per_condition: int = 20
    ) -> Dict[str, Any]:
        """Run full Stroop experiment."""
        colors = [Color.RED, Color.GREEN, Color.BLUE, Color.YELLOW]

        # Create stimuli
        congruent = []
        for _ in range(n_per_condition):
            color = random.choice(colors)
            congruent.append(self.create_congruent(color))

        incongruent = []
        for _ in range(n_per_condition):
            word_color = random.choice(colors)
            ink_color = random.choice([c for c in colors if c != word_color])
            incongruent.append(self.create_incongruent(word_color, ink_color))

        neutral = []
        for _ in range(n_per_condition):
            color = random.choice(colors)
            neutral.append(self.create_neutral(color))

        # Randomize and run
        all_stimuli = congruent + incongruent + neutral
        random.shuffle(all_stimuli)

        for stim in all_stimuli:
            self.run_trial(stim, TaskType.NAME_COLOR)

        # Calculate results
        cong_trials = [t for t in self._trials if t.trial_type == TrialType.CONGRUENT]
        incong_trials = [t for t in self._trials if t.trial_type == TrialType.INCONGRUENT]
        neut_trials = [t for t in self._trials if t.trial_type == TrialType.NEUTRAL]

        cong_rt = sum(t.reaction_time_ms for t in cong_trials) / len(cong_trials)
        incong_rt = sum(t.reaction_time_ms for t in incong_trials) / len(incong_trials)
        neut_rt = sum(t.reaction_time_ms for t in neut_trials) / len(neut_trials)

        stroop_effect = incong_rt - cong_rt
        interference = incong_rt - neut_rt
        facilitation = neut_rt - cong_rt

        accuracy = sum(1 for t in self._trials if t.correct) / len(self._trials)

        return {
            'congruent_rt': cong_rt,
            'incongruent_rt': incong_rt,
            'neutral_rt': neut_rt,
            'stroop_effect': stroop_effect,
            'interference': interference,
            'facilitation': facilitation,
            'accuracy': accuracy,
            'n_per_condition': n_per_condition
        }


# ============================================================================
# STROOP EFFECT ENGINE
# ============================================================================

class StroopEffectEngine:
    """
    Complete Stroop effect engine.

    "Ba'el's automatic-controlled conflict." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = StroopParadigm()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Stimulus creation

    def create_congruent(
        self,
        color: Color
    ) -> StroopStimulus:
        """Create congruent stimulus."""
        return self._paradigm.create_congruent(color)

    def create_incongruent(
        self,
        word: Color,
        ink: Color
    ) -> StroopStimulus:
        """Create incongruent stimulus."""
        return self._paradigm.create_incongruent(word, ink)

    def create_neutral(
        self,
        color: Color
    ) -> StroopStimulus:
        """Create neutral stimulus."""
        return self._paradigm.create_neutral(color)

    # Trial execution

    def run_trial(
        self,
        stimulus: StroopStimulus,
        task: TaskType = TaskType.NAME_COLOR
    ) -> StroopTrial:
        """Run a Stroop trial."""
        return self._paradigm.run_trial(stimulus, task)

    # Experiments

    def run_stroop_experiment(
        self,
        n_per_condition: int = 20
    ) -> Dict[str, Any]:
        """Run classic Stroop experiment."""
        result = self._paradigm.run_experiment(n_per_condition)
        self._experiment_results.append(result)
        return result

    def run_reverse_stroop(
        self,
        n_per_condition: int = 20
    ) -> Dict[str, Any]:
        """Run reverse Stroop (read word, ignore color)."""
        colors = [Color.RED, Color.GREEN, Color.BLUE]

        # Reset paradigm
        self._paradigm = StroopParadigm()

        congruent = []
        for _ in range(n_per_condition):
            color = random.choice(colors)
            congruent.append(self._paradigm.create_congruent(color))

        incongruent = []
        for _ in range(n_per_condition):
            word_color = random.choice(colors)
            ink_color = random.choice([c for c in colors if c != word_color])
            incongruent.append(self._paradigm.create_incongruent(word_color, ink_color))

        all_stimuli = congruent + incongruent
        random.shuffle(all_stimuli)

        for stim in all_stimuli:
            self._paradigm.run_trial(stim, TaskType.READ_WORD)

        # Word reading shows minimal interference
        cong_trials = [t for t in self._paradigm._trials if t.trial_type == TrialType.CONGRUENT]
        incong_trials = [t for t in self._paradigm._trials if t.trial_type == TrialType.INCONGRUENT]

        cong_rt = sum(t.reaction_time_ms for t in cong_trials) / len(cong_trials) if cong_trials else 0
        incong_rt = sum(t.reaction_time_ms for t in incong_trials) / len(incong_trials) if incong_trials else 0

        return {
            'congruent_rt': cong_rt,
            'incongruent_rt': incong_rt,
            'reverse_stroop_effect': incong_rt - cong_rt,
            'interpretation': 'Word reading is largely automatic and immune to color interference'
        }

    # Analysis

    def get_metrics(self) -> StroopMetrics:
        """Get Stroop metrics."""
        if not self._experiment_results:
            self.run_stroop_experiment(20)

        last = self._experiment_results[-1]

        return StroopMetrics(
            congruent_rt=last['congruent_rt'],
            incongruent_rt=last['incongruent_rt'],
            neutral_rt=last['neutral_rt'],
            stroop_effect=last['stroop_effect'],
            facilitation=last['facilitation'],
            interference=last['interference'],
            accuracy=last['accuracy']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'trials': len(self._paradigm._trials),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_stroop_effect_engine() -> StroopEffectEngine:
    """Create Stroop effect engine."""
    return StroopEffectEngine()


def demonstrate_stroop_effect() -> Dict[str, Any]:
    """Demonstrate Stroop effect."""
    engine = create_stroop_effect_engine()

    # Classic Stroop
    classic = engine.run_stroop_experiment(25)

    # Reverse Stroop
    reverse = engine.run_reverse_stroop(20)

    return {
        'classic_stroop': {
            'congruent_rt': f"{classic['congruent_rt']:.0f} ms",
            'incongruent_rt': f"{classic['incongruent_rt']:.0f} ms",
            'neutral_rt': f"{classic['neutral_rt']:.0f} ms",
            'stroop_effect': f"{classic['stroop_effect']:.0f} ms",
            'interference': f"{classic['interference']:.0f} ms",
            'facilitation': f"{classic['facilitation']:.0f} ms"
        },
        'reverse_stroop': {
            'effect': f"{reverse['reverse_stroop_effect']:.0f} ms",
            'interpretation': reverse['interpretation']
        },
        'accuracy': f"{classic['accuracy']:.0%}",
        'interpretation': (
            f"Stroop effect: {classic['stroop_effect']:.0f} ms. "
            f"Automatic word reading interferes with color naming."
        )
    }


def get_stroop_effect_facts() -> Dict[str, str]:
    """Get facts about Stroop effect."""
    return {
        'stroop_1935': 'Classic demonstration of automatic vs controlled processing',
        'automaticity': 'Word reading is automatic and cannot be suppressed',
        'interference': 'Incongruent trials are slower due to response conflict',
        'facilitation': 'Congruent trials are faster due to response convergence',
        'asymmetry': 'Color naming shows more interference than word reading',
        'gratton_effect': 'Post-conflict trials show reduced interference',
        'conflict_adaptation': 'Cognitive control adjusts based on conflict history',
        'individual_differences': 'Reading ability and age affect Stroop performance'
    }
