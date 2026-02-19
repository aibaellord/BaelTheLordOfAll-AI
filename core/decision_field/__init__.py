"""
BAEL Decision Field Theory Engine
==================================

Dynamic accumulator model of decision making.
Preference development over time.

"Ba'el deliberates before choosing." — Ba'el
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

logger = logging.getLogger("BAEL.DecisionField")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class DecisionState(Enum):
    """State of decision process."""
    DELIBERATING = auto()
    THRESHOLD_REACHED = auto()
    TIMEOUT = auto()
    INHIBITED = auto()


class AttentionMode(Enum):
    """Attention allocation mode."""
    RANDOM = auto()       # Random attention switching
    SEQUENTIAL = auto()   # Sequential attribute focus
    SALIENCE = auto()     # Salience-based


class ThresholdType(Enum):
    """Threshold type."""
    FIXED = auto()        # Fixed threshold
    COLLAPSING = auto()   # Decreasing over time
    URGENCY = auto()      # Urgency-gated


@dataclass
class Alternative:
    """
    A decision alternative.
    """
    id: str
    name: str
    attributes: Dict[str, float]  # Attribute -> value
    preference: float = 0.0       # Current preference state

    def reset(self) -> None:
        self.preference = 0.0


@dataclass
class Attribute:
    """
    A decision attribute.
    """
    id: str
    name: str
    weight: float = 1.0
    salience: float = 0.5


@dataclass
class Valence:
    """
    Momentary valence (evaluation).
    """
    alternative_id: str
    value: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class DecisionResult:
    """
    Result of decision process.
    """
    chosen_id: str
    chosen_name: str
    final_preference: float
    deliberation_time: float
    time_steps: int
    state: DecisionState
    preference_history: Dict[str, List[float]]


@dataclass
class DriftDiffusionParams:
    """
    Parameters for drift-diffusion.
    """
    drift_rate: float = 0.1
    noise: float = 0.3
    threshold: float = 1.0
    starting_point: float = 0.0
    non_decision_time: float = 0.1


# ============================================================================
# VALENCE COMPUTATION
# ============================================================================

class ValenceComputer:
    """
    Compute momentary valences.

    "Ba'el computes values." — Ba'el
    """

    def __init__(self, noise: float = 0.1):
        """Initialize computer."""
        self._noise = noise
        self._lock = threading.RLock()

    def compute(
        self,
        alternative: Alternative,
        attended_attribute: Attribute
    ) -> Valence:
        """Compute valence for alternative on attended attribute."""
        with self._lock:
            attr_value = alternative.attributes.get(attended_attribute.name, 0.0)

            # Weight by attribute weight
            weighted = attr_value * attended_attribute.weight

            # Add noise
            noise = random.gauss(0, self._noise)

            value = weighted + noise

            return Valence(
                alternative_id=alternative.id,
                value=value
            )

    def compute_all(
        self,
        alternatives: List[Alternative],
        attended_attribute: Attribute
    ) -> List[Valence]:
        """Compute valences for all alternatives."""
        return [self.compute(alt, attended_attribute) for alt in alternatives]


# ============================================================================
# ATTENTION SWITCHING
# ============================================================================

class AttentionSwitcher:
    """
    Switch attention between attributes.

    "Ba'el shifts focus." — Ba'el
    """

    def __init__(
        self,
        mode: AttentionMode = AttentionMode.RANDOM
    ):
        """Initialize switcher."""
        self._mode = mode
        self._current_index = 0
        self._lock = threading.RLock()

    def switch(
        self,
        attributes: List[Attribute]
    ) -> Attribute:
        """Switch attention to next attribute."""
        with self._lock:
            if not attributes:
                raise ValueError("No attributes")

            if self._mode == AttentionMode.RANDOM:
                return random.choice(attributes)

            elif self._mode == AttentionMode.SEQUENTIAL:
                attr = attributes[self._current_index % len(attributes)]
                self._current_index += 1
                return attr

            elif self._mode == AttentionMode.SALIENCE:
                # Probability proportional to salience
                total_salience = sum(a.salience for a in attributes)
                r = random.random() * total_salience

                cumulative = 0.0
                for attr in attributes:
                    cumulative += attr.salience
                    if r <= cumulative:
                        return attr

                return attributes[-1]

    def reset(self) -> None:
        """Reset attention state."""
        self._current_index = 0


# ============================================================================
# PREFERENCE INTEGRATOR
# ============================================================================

class PreferenceIntegrator:
    """
    Integrate preferences over time.

    "Ba'el accumulates preference." — Ba'el
    """

    def __init__(
        self,
        decay: float = 0.1,
        lateral_inhibition: float = 0.05
    ):
        """Initialize integrator."""
        self._decay = decay
        self._lateral_inhibition = lateral_inhibition
        self._lock = threading.RLock()

    def update(
        self,
        alternatives: List[Alternative],
        valences: List[Valence]
    ) -> None:
        """Update preferences based on valences."""
        with self._lock:
            # Create valence map
            valence_map = {v.alternative_id: v.value for v in valences}

            # Update each alternative
            for alt in alternatives:
                valence = valence_map.get(alt.id, 0.0)

                # Decay current preference
                alt.preference *= (1.0 - self._decay)

                # Add new valence
                alt.preference += valence

                # Lateral inhibition from other preferences
                others_pref = sum(
                    a.preference for a in alternatives
                    if a.id != alt.id
                ) / max(1, len(alternatives) - 1)

                alt.preference -= self._lateral_inhibition * others_pref

    def normalize(
        self,
        alternatives: List[Alternative]
    ) -> None:
        """Normalize preferences."""
        with self._lock:
            total = sum(abs(alt.preference) for alt in alternatives)
            if total > 0:
                for alt in alternatives:
                    alt.preference /= total


# ============================================================================
# DECISION FIELD THEORY ENGINE
# ============================================================================

class DecisionFieldEngine:
    """
    Complete Decision Field Theory engine.

    "Ba'el's deliberative choice." — Ba'el
    """

    def __init__(
        self,
        threshold: float = 1.0,
        max_steps: int = 100,
        threshold_type: ThresholdType = ThresholdType.FIXED
    ):
        """Initialize engine."""
        self._threshold = threshold
        self._max_steps = max_steps
        self._threshold_type = threshold_type

        self._valence = ValenceComputer()
        self._attention = AttentionSwitcher()
        self._integrator = PreferenceIntegrator()

        self._alt_counter = 0
        self._attr_counter = 0
        self._lock = threading.RLock()

    def _generate_alt_id(self) -> str:
        self._alt_counter += 1
        return f"alt_{self._alt_counter}"

    def _generate_attr_id(self) -> str:
        self._attr_counter += 1
        return f"attr_{self._attr_counter}"

    def _get_threshold(self, step: int) -> float:
        """Get threshold for current step."""
        if self._threshold_type == ThresholdType.FIXED:
            return self._threshold

        elif self._threshold_type == ThresholdType.COLLAPSING:
            # Threshold decreases over time
            progress = step / self._max_steps
            return self._threshold * (1.0 - 0.5 * progress)

        elif self._threshold_type == ThresholdType.URGENCY:
            # Threshold decreases faster near deadline
            urgency = (step / self._max_steps) ** 2
            return self._threshold * (1.0 - 0.8 * urgency)

        return self._threshold

    def create_alternative(
        self,
        name: str,
        attributes: Dict[str, float]
    ) -> Alternative:
        """Create decision alternative."""
        return Alternative(
            id=self._generate_alt_id(),
            name=name,
            attributes=attributes
        )

    def create_attribute(
        self,
        name: str,
        weight: float = 1.0,
        salience: float = 0.5
    ) -> Attribute:
        """Create decision attribute."""
        return Attribute(
            id=self._generate_attr_id(),
            name=name,
            weight=weight,
            salience=salience
        )

    def decide(
        self,
        alternatives: List[Alternative],
        attributes: List[Attribute]
    ) -> DecisionResult:
        """Run decision process."""
        with self._lock:
            start_time = time.time()

            # Reset preferences
            for alt in alternatives:
                alt.reset()

            self._attention.reset()

            # Track preference history
            history = {alt.id: [] for alt in alternatives}

            # Deliberation loop
            state = DecisionState.DELIBERATING

            for step in range(self._max_steps):
                # Switch attention
                attended = self._attention.switch(attributes)

                # Compute valences
                valences = self._valence.compute_all(alternatives, attended)

                # Update preferences
                self._integrator.update(alternatives, valences)

                # Record history
                for alt in alternatives:
                    history[alt.id].append(alt.preference)

                # Check threshold
                threshold = self._get_threshold(step)

                for alt in alternatives:
                    if alt.preference >= threshold:
                        state = DecisionState.THRESHOLD_REACHED

                        return DecisionResult(
                            chosen_id=alt.id,
                            chosen_name=alt.name,
                            final_preference=alt.preference,
                            deliberation_time=time.time() - start_time,
                            time_steps=step + 1,
                            state=state,
                            preference_history=history
                        )

            # Timeout - choose highest preference
            state = DecisionState.TIMEOUT
            best = max(alternatives, key=lambda a: a.preference)

            return DecisionResult(
                chosen_id=best.id,
                chosen_name=best.name,
                final_preference=best.preference,
                deliberation_time=time.time() - start_time,
                time_steps=self._max_steps,
                state=state,
                preference_history=history
            )

    def quick_decide(
        self,
        options: Dict[str, Dict[str, float]],
        weights: Dict[str, float] = None
    ) -> str:
        """Quick decision from options dict."""
        # Extract attribute names
        all_attrs = set()
        for attrs in options.values():
            all_attrs.update(attrs.keys())

        # Create alternatives
        alternatives = [
            self.create_alternative(name, attrs)
            for name, attrs in options.items()
        ]

        # Create attributes
        attributes = [
            self.create_attribute(
                name,
                weight=weights.get(name, 1.0) if weights else 1.0
            )
            for name in all_attrs
        ]

        result = self.decide(alternatives, attributes)
        return result.chosen_name


# ============================================================================
# DRIFT DIFFUSION MODEL
# ============================================================================

class DriftDiffusionModel:
    """
    Two-alternative drift diffusion.

    "Ba'el accumulates evidence." — Ba'el
    """

    def __init__(self, params: DriftDiffusionParams = None):
        """Initialize DDM."""
        self._params = params or DriftDiffusionParams()
        self._lock = threading.RLock()

    def simulate(
        self,
        drift: float = None,
        max_time: float = 5.0,
        dt: float = 0.01
    ) -> Tuple[int, float, List[float]]:
        """
        Simulate DDM.

        Returns: (choice, reaction_time, trajectory)
        """
        with self._lock:
            p = self._params

            d = drift if drift is not None else p.drift_rate

            x = p.starting_point
            trajectory = [x]
            t = 0.0

            while abs(x) < p.threshold and t < max_time:
                # Drift + noise
                dx = d * dt + math.sqrt(dt) * p.noise * random.gauss(0, 1)
                x += dx
                trajectory.append(x)
                t += dt

            choice = 1 if x >= p.threshold else 0
            rt = t + p.non_decision_time

            return choice, rt, trajectory

    def estimate_accuracy(
        self,
        drift: float,
        threshold: float = None
    ) -> float:
        """Estimate choice accuracy."""
        a = threshold or self._params.threshold
        v = drift
        s = self._params.noise

        # Analytical accuracy
        return 1.0 / (1.0 + math.exp(-2.0 * a * v / (s * s)))

    def estimate_mean_rt(
        self,
        drift: float,
        threshold: float = None
    ) -> float:
        """Estimate mean RT."""
        a = threshold or self._params.threshold
        v = drift
        s = self._params.noise
        z = self._params.starting_point

        if abs(v) < 0.001:
            return a * a / (s * s)

        # Approximation
        return a / v * math.tanh(a * v / (s * s))


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_decision_field_engine(
    threshold: float = 1.0,
    max_steps: int = 100
) -> DecisionFieldEngine:
    """Create Decision Field Theory engine."""
    return DecisionFieldEngine(threshold, max_steps)


def decide(
    options: Dict[str, Dict[str, float]],
    weights: Dict[str, float] = None
) -> str:
    """Quick decision."""
    engine = create_decision_field_engine()
    return engine.quick_decide(options, weights)


def drift_diffusion(
    drift: float = 0.1,
    threshold: float = 1.0
) -> Tuple[int, float]:
    """Run drift diffusion."""
    ddm = DriftDiffusionModel(DriftDiffusionParams(
        drift_rate=drift,
        threshold=threshold
    ))
    choice, rt, _ = ddm.simulate()
    return choice, rt
