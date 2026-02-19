"""
BAEL Inhibitory Control Engine
===============================

Response inhibition, interference control, and impulse management.
Executive function for behavioral control.

"Ba'el masters impulse." — Ba'el
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

logger = logging.getLogger("BAEL.InhibitoryControl")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class InhibitionType(Enum):
    """Types of inhibition."""
    RESPONSE_INHIBITION = auto()    # Stop ongoing response
    INTERFERENCE_CONTROL = auto()  # Resist interference
    COGNITIVE_INHIBITION = auto()  # Suppress thoughts
    PROACTIVE_INHIBITION = auto()  # Prevent initiation
    REACTIVE_INHIBITION = auto()   # Stop after start


class TrialType(Enum):
    """Types of trials in inhibition tasks."""
    GO = auto()        # Respond
    NOGO = auto()      # Don't respond
    STOP = auto()      # Stop after signal


class ResponseState(Enum):
    """State of response."""
    INITIATED = auto()
    EXECUTING = auto()
    COMPLETED = auto()
    INHIBITED = auto()
    FAILED_INHIBITION = auto()


class ConflictLevel(Enum):
    """Level of conflict."""
    NONE = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


@dataclass
class Stimulus:
    """
    A stimulus requiring response.
    """
    id: str
    trial_type: TrialType
    features: Dict[str, Any]
    onset_time: float
    stop_signal_delay: Optional[float] = None  # For stop trials


@dataclass
class Response:
    """
    A response to stimulus.
    """
    id: str
    stimulus_id: str
    state: ResponseState
    initiation_time: float
    execution_time: Optional[float] = None
    inhibition_time: Optional[float] = None
    correct: bool = False


@dataclass
class InhibitionAttempt:
    """
    An attempt to inhibit response.
    """
    id: str
    stimulus_id: str
    signal_time: float
    success: bool
    reaction_time: float  # Time from signal to inhibition


@dataclass
class InhibitionMetrics:
    """
    Metrics for inhibitory control.
    """
    go_accuracy: float
    nogo_accuracy: float
    stop_signal_reaction_time: float  # SSRT
    commission_errors: int  # Responding when shouldn't
    omission_errors: int    # Not responding when should
    interference_effect: float  # Slowdown from interference


@dataclass
class ConflictTrial:
    """
    A trial with conflicting information.
    """
    id: str
    congruent: bool
    target: str
    distractor: str
    correct_response: str
    actual_response: Optional[str] = None
    response_time: Optional[float] = None


# ============================================================================
# RESPONSE ACCUMULATOR
# ============================================================================

class ResponseAccumulator:
    """
    Evidence accumulator for response selection.
    Race model for go/stop processes.

    "Ba'el accumulates evidence." — Ba'el
    """

    def __init__(self):
        """Initialize accumulator."""
        self._threshold = 1.0
        self._go_rate = 0.1      # Evidence accumulation rate for go
        self._stop_rate = 0.15   # Faster for stop

        self._lock = threading.RLock()

    def simulate_race(
        self,
        stop_signal_delay: float = None
    ) -> Tuple[str, float]:
        """
        Simulate race between go and stop processes.
        Returns winner and finishing time.
        """
        with self._lock:
            go_evidence = 0.0
            stop_evidence = 0.0

            dt = 0.01
            time_elapsed = 0.0
            stop_started = False

            while True:
                # Go process
                go_evidence += self._go_rate + random.gauss(0, 0.02)

                # Stop process (starts after SSD)
                if stop_signal_delay is not None and time_elapsed >= stop_signal_delay:
                    if not stop_started:
                        stop_started = True
                    stop_evidence += self._stop_rate + random.gauss(0, 0.02)

                time_elapsed += dt

                # Check thresholds
                if go_evidence >= self._threshold:
                    return "go", time_elapsed

                if stop_evidence >= self._threshold:
                    return "stop", time_elapsed

                # Timeout
                if time_elapsed > 2.0:
                    return "timeout", time_elapsed


# ============================================================================
# GO/NOGO TASK
# ============================================================================

class GoNoGoTask:
    """
    Go/No-Go task simulation.

    "Ba'el knows when to act." — Ba'el
    """

    def __init__(self):
        """Initialize task."""
        self._trials: List[Tuple[Stimulus, Response]] = []
        self._stim_counter = 0
        self._resp_counter = 0

        self._go_probability = 0.75  # 75% go trials
        self._commission_rate = 0.1  # False alarm rate
        self._omission_rate = 0.05   # Miss rate

        self._lock = threading.RLock()

    def _generate_stim_id(self) -> str:
        self._stim_counter += 1
        return f"stim_{self._stim_counter}"

    def _generate_resp_id(self) -> str:
        self._resp_counter += 1
        return f"resp_{self._resp_counter}"

    def generate_trial(self) -> Stimulus:
        """Generate a trial."""
        is_go = random.random() < self._go_probability

        return Stimulus(
            id=self._generate_stim_id(),
            trial_type=TrialType.GO if is_go else TrialType.NOGO,
            features={'type': 'go' if is_go else 'nogo'},
            onset_time=time.time()
        )

    def execute_trial(
        self,
        stimulus: Stimulus
    ) -> Response:
        """Execute a trial."""
        with self._lock:
            initiation_time = random.gauss(0.3, 0.05)

            if stimulus.trial_type == TrialType.GO:
                # Should respond
                if random.random() < self._omission_rate:
                    # Miss (omission error)
                    state = ResponseState.INHIBITED
                    correct = False
                else:
                    # Correct response
                    state = ResponseState.COMPLETED
                    correct = True
            else:
                # Should not respond
                if random.random() < self._commission_rate:
                    # False alarm (commission error)
                    state = ResponseState.FAILED_INHIBITION
                    correct = False
                else:
                    # Correct inhibition
                    state = ResponseState.INHIBITED
                    correct = True

            response = Response(
                id=self._generate_resp_id(),
                stimulus_id=stimulus.id,
                state=state,
                initiation_time=initiation_time,
                execution_time=initiation_time + 0.1 if state == ResponseState.COMPLETED else None,
                correct=correct
            )

            self._trials.append((stimulus, response))
            return response

    def get_accuracy(self) -> Tuple[float, float]:
        """Get go and nogo accuracy."""
        go_correct = 0
        go_total = 0
        nogo_correct = 0
        nogo_total = 0

        for stim, resp in self._trials:
            if stim.trial_type == TrialType.GO:
                go_total += 1
                if resp.correct:
                    go_correct += 1
            else:
                nogo_total += 1
                if resp.correct:
                    nogo_correct += 1

        go_acc = go_correct / go_total if go_total > 0 else 0.0
        nogo_acc = nogo_correct / nogo_total if nogo_total > 0 else 0.0

        return go_acc, nogo_acc


# ============================================================================
# STOP SIGNAL TASK
# ============================================================================

class StopSignalTask:
    """
    Stop Signal task simulation.

    "Ba'el stops on command." — Ba'el
    """

    def __init__(self):
        """Initialize task."""
        self._accumulator = ResponseAccumulator()
        self._trials: List[Tuple[Stimulus, Response]] = []

        self._stop_probability = 0.25  # 25% stop trials
        self._initial_ssd = 0.2  # Initial stop signal delay
        self._ssd = self._initial_ssd
        self._ssd_step = 0.05  # Adjustment step

        self._stim_counter = 0
        self._resp_counter = 0
        self._lock = threading.RLock()

    def _generate_stim_id(self) -> str:
        self._stim_counter += 1
        return f"stop_stim_{self._stim_counter}"

    def _generate_resp_id(self) -> str:
        self._resp_counter += 1
        return f"stop_resp_{self._resp_counter}"

    def generate_trial(self) -> Stimulus:
        """Generate a trial."""
        is_stop = random.random() < self._stop_probability

        return Stimulus(
            id=self._generate_stim_id(),
            trial_type=TrialType.STOP if is_stop else TrialType.GO,
            features={'type': 'stop' if is_stop else 'go'},
            onset_time=time.time(),
            stop_signal_delay=self._ssd if is_stop else None
        )

    def execute_trial(
        self,
        stimulus: Stimulus
    ) -> Response:
        """Execute a trial."""
        with self._lock:
            if stimulus.trial_type == TrialType.GO:
                # Regular go trial
                winner, rt = self._accumulator.simulate_race(None)

                response = Response(
                    id=self._generate_resp_id(),
                    stimulus_id=stimulus.id,
                    state=ResponseState.COMPLETED if winner == "go" else ResponseState.INHIBITED,
                    initiation_time=rt * 0.3,
                    execution_time=rt,
                    correct=True
                )
            else:
                # Stop trial
                winner, rt = self._accumulator.simulate_race(stimulus.stop_signal_delay)

                if winner == "stop":
                    state = ResponseState.INHIBITED
                    correct = True
                    # Make it harder next time
                    self._ssd = min(0.5, self._ssd + self._ssd_step)
                else:
                    state = ResponseState.FAILED_INHIBITION
                    correct = False
                    # Make it easier next time
                    self._ssd = max(0.05, self._ssd - self._ssd_step)

                response = Response(
                    id=self._generate_resp_id(),
                    stimulus_id=stimulus.id,
                    state=state,
                    initiation_time=rt * 0.3,
                    execution_time=rt if winner == "go" else None,
                    inhibition_time=rt if winner == "stop" else None,
                    correct=correct
                )

            self._trials.append((stimulus, response))
            return response

    def estimate_ssrt(self) -> float:
        """Estimate Stop Signal Reaction Time."""
        # Integration method (simplified)
        go_rts = []
        for stim, resp in self._trials:
            if stim.trial_type == TrialType.GO and resp.execution_time:
                go_rts.append(resp.execution_time)

        if not go_rts:
            return 0.0

        # Average SSD
        ssds = [stim.stop_signal_delay for stim, _ in self._trials
                if stim.trial_type == TrialType.STOP and stim.stop_signal_delay]

        if not ssds:
            return 0.0

        avg_ssd = sum(ssds) / len(ssds)

        # Inhibition rate
        stop_trials = [(s, r) for s, r in self._trials if s.trial_type == TrialType.STOP]
        if not stop_trials:
            return 0.0

        inhibition_rate = sum(1 for _, r in stop_trials if r.correct) / len(stop_trials)

        # SSRT = nth percentile of go RT - mean SSD
        go_rts.sort()
        n = int((1 - inhibition_rate) * len(go_rts))
        n = min(n, len(go_rts) - 1)

        ssrt = go_rts[n] - avg_ssd
        return max(0, ssrt)


# ============================================================================
# STROOP TASK
# ============================================================================

class StroopTask:
    """
    Stroop task for interference control.

    "Ba'el resists interference." — Ba'el
    """

    def __init__(self):
        """Initialize task."""
        self._trials: List[ConflictTrial] = []
        self._trial_counter = 0

        self._congruence_effect = 0.1  # RT difference
        self._error_rate_congruent = 0.02
        self._error_rate_incongruent = 0.08

        self._colors = ['red', 'blue', 'green', 'yellow']

        self._lock = threading.RLock()

    def _generate_trial_id(self) -> str:
        self._trial_counter += 1
        return f"stroop_{self._trial_counter}"

    def generate_trial(
        self,
        congruent: bool = None
    ) -> ConflictTrial:
        """Generate a Stroop trial."""
        if congruent is None:
            congruent = random.random() < 0.5

        target = random.choice(self._colors)

        if congruent:
            distractor = target  # Word matches color
        else:
            others = [c for c in self._colors if c != target]
            distractor = random.choice(others)

        return ConflictTrial(
            id=self._generate_trial_id(),
            congruent=congruent,
            target=target,
            distractor=distractor,
            correct_response=target
        )

    def execute_trial(
        self,
        trial: ConflictTrial
    ) -> ConflictTrial:
        """Execute a Stroop trial."""
        with self._lock:
            # Base RT
            base_rt = random.gauss(0.6, 0.1)

            if trial.congruent:
                rt = base_rt
                error_rate = self._error_rate_congruent
            else:
                rt = base_rt + self._congruence_effect
                error_rate = self._error_rate_incongruent

            if random.random() < error_rate:
                # Error: respond with distractor
                trial.actual_response = trial.distractor
            else:
                trial.actual_response = trial.correct_response

            trial.response_time = rt
            self._trials.append(trial)

            return trial

    def get_stroop_effect(self) -> float:
        """Calculate Stroop interference effect."""
        congruent_rts = [
            t.response_time for t in self._trials
            if t.congruent and t.response_time
        ]

        incongruent_rts = [
            t.response_time for t in self._trials
            if not t.congruent and t.response_time
        ]

        if not congruent_rts or not incongruent_rts:
            return 0.0

        return (sum(incongruent_rts) / len(incongruent_rts) -
                sum(congruent_rts) / len(congruent_rts))


# ============================================================================
# INHIBITORY CONTROL ENGINE
# ============================================================================

class InhibitoryControlEngine:
    """
    Complete inhibitory control engine.

    "Ba'el's control over action." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._go_nogo = GoNoGoTask()
        self._stop_signal = StopSignalTask()
        self._stroop = StroopTask()

        self._lock = threading.RLock()

    # Go/No-Go

    def run_go_nogo_trial(self) -> Response:
        """Run a Go/No-Go trial."""
        stim = self._go_nogo.generate_trial()
        return self._go_nogo.execute_trial(stim)

    def run_go_nogo_block(
        self,
        num_trials: int = 20
    ) -> List[Response]:
        """Run a block of Go/No-Go trials."""
        responses = []
        for _ in range(num_trials):
            responses.append(self.run_go_nogo_trial())
        return responses

    def get_go_nogo_accuracy(self) -> Tuple[float, float]:
        """Get Go/No-Go accuracy."""
        return self._go_nogo.get_accuracy()

    # Stop Signal

    def run_stop_signal_trial(self) -> Response:
        """Run a Stop Signal trial."""
        stim = self._stop_signal.generate_trial()
        return self._stop_signal.execute_trial(stim)

    def run_stop_signal_block(
        self,
        num_trials: int = 20
    ) -> List[Response]:
        """Run a block of Stop Signal trials."""
        responses = []
        for _ in range(num_trials):
            responses.append(self.run_stop_signal_trial())
        return responses

    def get_ssrt(self) -> float:
        """Get Stop Signal Reaction Time."""
        return self._stop_signal.estimate_ssrt()

    # Stroop

    def run_stroop_trial(
        self,
        congruent: bool = None
    ) -> ConflictTrial:
        """Run a Stroop trial."""
        trial = self._stroop.generate_trial(congruent)
        return self._stroop.execute_trial(trial)

    def run_stroop_block(
        self,
        num_trials: int = 20
    ) -> List[ConflictTrial]:
        """Run a block of Stroop trials."""
        trials = []
        for _ in range(num_trials):
            trials.append(self.run_stroop_trial())
        return trials

    def get_stroop_effect(self) -> float:
        """Get Stroop interference effect."""
        return self._stroop.get_stroop_effect()

    # Overall metrics

    def get_metrics(self) -> InhibitionMetrics:
        """Get overall inhibition metrics."""
        go_acc, nogo_acc = self.get_go_nogo_accuracy()
        ssrt = self.get_ssrt()
        stroop_effect = self.get_stroop_effect()

        # Count errors
        commission = sum(
            1 for _, r in self._go_nogo._trials
            if r.state == ResponseState.FAILED_INHIBITION
        )

        omission = sum(
            1 for s, r in self._go_nogo._trials
            if s.trial_type == TrialType.GO and r.state == ResponseState.INHIBITED
        )

        return InhibitionMetrics(
            go_accuracy=go_acc,
            nogo_accuracy=nogo_acc,
            stop_signal_reaction_time=ssrt,
            commission_errors=commission,
            omission_errors=omission,
            interference_effect=stroop_effect
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'go_nogo_trials': len(self._go_nogo._trials),
            'stop_signal_trials': len(self._stop_signal._trials),
            'stroop_trials': len(self._stroop._trials)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_inhibitory_control_engine() -> InhibitoryControlEngine:
    """Create inhibitory control engine."""
    return InhibitoryControlEngine()


def run_inhibition_battery(
    trials_per_task: int = 40
) -> InhibitionMetrics:
    """Run complete inhibition battery."""
    engine = create_inhibitory_control_engine()

    # Run all tasks
    engine.run_go_nogo_block(trials_per_task)
    engine.run_stop_signal_block(trials_per_task)
    engine.run_stroop_block(trials_per_task)

    return engine.get_metrics()
