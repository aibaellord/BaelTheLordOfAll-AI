"""
BAEL Temporal Discounting Engine
==================================

Value decreases with delay.
Mazur's hyperbolic discounting model.

"Ba'el knows patience has a price." — Ba'el
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

logger = logging.getLogger("BAEL.TemporalDiscounting")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class DiscountingType(Enum):
    """Type of discounting function."""
    EXPONENTIAL = auto()    # Normative
    HYPERBOLIC = auto()     # Descriptive (human-like)
    QUASI_HYPERBOLIC = auto()  # Beta-delta model


class OutcomeType(Enum):
    """Type of outcome."""
    MONETARY = auto()
    HEALTH = auto()
    ENVIRONMENTAL = auto()
    SOCIAL = auto()


class DelayUnit(Enum):
    """Unit of delay."""
    DAYS = auto()
    WEEKS = auto()
    MONTHS = auto()
    YEARS = auto()


@dataclass
class DelayedReward:
    """
    A reward available after delay.
    """
    id: str
    amount: float
    delay_days: int
    outcome_type: OutcomeType


@dataclass
class Choice:
    """
    A choice between rewards.
    """
    id: str
    immediate: DelayedReward
    delayed: DelayedReward
    chosen: Optional[str] = None


@dataclass
class DiscountingMetrics:
    """
    Temporal discounting metrics.
    """
    k_parameter: float          # Discounting rate
    indifference_delay: float   # Delay at which values equal
    impulsivity_score: float    # Higher k = more impulsive
    consistency: float          # How consistent are choices


# ============================================================================
# DISCOUNTING MODEL
# ============================================================================

class DiscountingModel:
    """
    Temporal discounting model.

    "Ba'el's value decay over time." — Ba'el
    """

    def __init__(
        self,
        k: float = 0.1,
        discounting_type: DiscountingType = DiscountingType.HYPERBOLIC
    ):
        """Initialize model."""
        # Discounting parameter
        self._k = k  # Higher k = more impulsive

        # Type of discounting
        self._type = discounting_type

        # For quasi-hyperbolic
        self._beta = 0.7   # Present bias
        self._delta = 0.99  # Per-period discount

        # Decision noise
        self._noise = 0.05

        self._lock = threading.RLock()

    @property
    def k(self) -> float:
        """Get k parameter."""
        return self._k

    @k.setter
    def k(self, value: float):
        """Set k parameter."""
        self._k = value

    def discount_value(
        self,
        amount: float,
        delay_days: int
    ) -> float:
        """Calculate discounted value."""
        if delay_days <= 0:
            return amount

        if self._type == DiscountingType.EXPONENTIAL:
            # V = A * exp(-k * D)
            return amount * math.exp(-self._k * delay_days)

        elif self._type == DiscountingType.HYPERBOLIC:
            # V = A / (1 + k * D)
            return amount / (1 + self._k * delay_days)

        elif self._type == DiscountingType.QUASI_HYPERBOLIC:
            # V = beta * delta^D * A if D > 0
            return self._beta * (self._delta ** delay_days) * amount

        return amount

    def choose(
        self,
        immediate: DelayedReward,
        delayed: DelayedReward
    ) -> str:
        """Choose between two rewards."""
        # Calculate subjective values
        v_immediate = self.discount_value(
            immediate.amount, immediate.delay_days
        )
        v_delayed = self.discount_value(
            delayed.amount, delayed.delay_days
        )

        # Add noise
        v_immediate += random.gauss(0, self._noise * immediate.amount)
        v_delayed += random.gauss(0, self._noise * delayed.amount)

        # Choose higher value
        if v_immediate >= v_delayed:
            return immediate.id
        else:
            return delayed.id

    def find_indifference_point(
        self,
        larger_amount: float,
        smaller_amount: float
    ) -> float:
        """Find delay at which values are equal."""
        # At indifference: smaller = larger / (1 + k * D)
        # Solving: D = (larger/smaller - 1) / k

        if self._k <= 0:
            return float('inf')

        ratio = larger_amount / smaller_amount
        delay = (ratio - 1) / self._k

        return max(0, delay)


# ============================================================================
# TEMPORAL DISCOUNTING SYSTEM
# ============================================================================

class TemporalDiscountingSystem:
    """
    Temporal discounting simulation system.

    "Ba'el's intertemporal choice." — Ba'el
    """

    def __init__(
        self,
        k: float = 0.1
    ):
        """Initialize system."""
        self._model = DiscountingModel(k=k)

        self._rewards: Dict[str, DelayedReward] = {}
        self._choices: List[Choice] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"reward_{self._counter}"

    def create_reward(
        self,
        amount: float,
        delay_days: int = 0,
        outcome_type: OutcomeType = OutcomeType.MONETARY
    ) -> DelayedReward:
        """Create a reward."""
        reward = DelayedReward(
            id=self._generate_id(),
            amount=amount,
            delay_days=delay_days,
            outcome_type=outcome_type
        )

        self._rewards[reward.id] = reward

        return reward

    def create_choice(
        self,
        immediate_amount: float,
        delayed_amount: float,
        delay_days: int
    ) -> Choice:
        """Create a choice."""
        immediate = self.create_reward(immediate_amount, 0)
        delayed = self.create_reward(delayed_amount, delay_days)

        choice = Choice(
            id=self._generate_id(),
            immediate=immediate,
            delayed=delayed
        )

        self._choices.append(choice)

        return choice

    def make_choice(
        self,
        choice: Choice
    ) -> str:
        """Make a choice."""
        chosen_id = self._model.choose(choice.immediate, choice.delayed)
        choice.chosen = chosen_id
        return chosen_id

    def run_titration(
        self,
        delayed_amount: float,
        delay_days: int,
        step_size: float = 5
    ) -> float:
        """Find indifference point through titration."""
        low = 0
        high = delayed_amount

        for _ in range(20):  # Binary search
            mid = (low + high) / 2

            choice = self.create_choice(mid, delayed_amount, delay_days)
            chosen = self.make_choice(choice)

            if chosen == choice.immediate.id:
                # Chose immediate, so it was too valuable
                high = mid
            else:
                # Chose delayed, so immediate was too small
                low = mid

        return (low + high) / 2


# ============================================================================
# TEMPORAL DISCOUNTING PARADIGM
# ============================================================================

class TemporalDiscountingParadigm:
    """
    Temporal discounting experimental paradigm.

    "Ba'el's delay study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_basic_paradigm(
        self,
        k: float = 0.1,
        n_trials: int = 50
    ) -> Dict[str, Any]:
        """Run basic discounting paradigm."""
        system = TemporalDiscountingSystem(k=k)

        immediate_choices = 0

        for _ in range(n_trials):
            immediate_amount = random.uniform(10, 90)
            delayed_amount = 100
            delay = random.randint(7, 365)

            choice = system.create_choice(immediate_amount, delayed_amount, delay)
            chosen = system.make_choice(choice)

            if chosen == choice.immediate.id:
                immediate_choices += 1

        return {
            'k_parameter': k,
            'immediate_choice_rate': immediate_choices / n_trials,
            'impulsivity': 'high' if immediate_choices / n_trials > 0.6 else 'low'
        }

    def run_discounting_curve(
        self,
        k: float = 0.1
    ) -> Dict[str, Any]:
        """Generate discounting curve across delays."""
        system = TemporalDiscountingSystem(k=k)
        model = DiscountingModel(k=k)

        delays = [1, 7, 30, 90, 180, 365, 730]
        amount = 100

        curve = {}
        for delay in delays:
            subjective_value = model.discount_value(amount, delay)
            curve[delay] = subjective_value

        return {
            'delays': delays,
            'values': curve,
            'k': k,
            'half_life': math.log(2) / k if k > 0 else float('inf')
        }

    def run_k_estimation(
        self,
        n_trials: int = 30
    ) -> Dict[str, Any]:
        """Estimate k from titration."""
        delays = [7, 30, 90, 180, 365]
        delayed_amount = 100

        indifference_points = {}

        for k_true in [0.01, 0.05, 0.1, 0.2]:
            system = TemporalDiscountingSystem(k=k_true)

            points = {}
            for delay in delays:
                indiff = system.run_titration(delayed_amount, delay)
                points[delay] = indiff

            # Estimate k from indifference points
            # At indifference: immediate = delayed / (1 + k * D)
            # k = (delayed/immediate - 1) / D
            k_estimates = []
            for delay, indiff in points.items():
                if indiff > 0:
                    k_est = (delayed_amount / indiff - 1) / delay
                    k_estimates.append(k_est)

            estimated_k = sum(k_estimates) / len(k_estimates) if k_estimates else 0

            indifference_points[f"k_true_{k_true}"] = {
                'points': points,
                'estimated_k': estimated_k,
                'error': abs(estimated_k - k_true)
            }

        return indifference_points

    def run_domain_comparison(
        self,
        k: float = 0.1
    ) -> Dict[str, Any]:
        """Compare discounting across domains."""
        domains = list(OutcomeType)

        # Different domains have different discounting rates
        domain_k_modifiers = {
            OutcomeType.MONETARY: 1.0,
            OutcomeType.HEALTH: 0.7,     # Less discounting for health
            OutcomeType.ENVIRONMENTAL: 0.5,  # Even less for environment
            OutcomeType.SOCIAL: 1.2      # More for social
        }

        results = {}

        for domain in domains:
            modified_k = k * domain_k_modifiers[domain]
            system = TemporalDiscountingSystem(k=modified_k)

            immediate_choices = 0
            for _ in range(30):
                choice = system.create_choice(
                    random.uniform(20, 80),
                    100,
                    random.randint(30, 180)
                )
                if system.make_choice(choice) == choice.immediate.id:
                    immediate_choices += 1

            results[domain.name] = {
                'effective_k': modified_k,
                'immediate_rate': immediate_choices / 30
            }

        return results

    def run_magnitude_effect(
        self,
        k: float = 0.1
    ) -> Dict[str, Any]:
        """Study magnitude effect (smaller amounts discounted more)."""
        magnitudes = [10, 100, 1000, 10000]

        results = {}

        for magnitude in magnitudes:
            # Smaller magnitudes have effectively higher k
            effective_k = k / math.log10(magnitude + 1)

            system = TemporalDiscountingSystem(k=effective_k)

            # Find indifference for 30-day delay
            indiff = system.run_titration(magnitude, 30)
            discount = (magnitude - indiff) / magnitude

            results[magnitude] = {
                'effective_k': effective_k,
                'discount_30_days': discount
            }

        return {
            'by_magnitude': results,
            'interpretation': 'Smaller amounts discounted more steeply'
        }

    def compare_exponential_hyperbolic(
        self
    ) -> Dict[str, Any]:
        """Compare exponential vs hyperbolic discounting."""
        delays = [1, 7, 30, 90, 180, 365]
        amount = 100
        k = 0.02

        exponential = DiscountingModel(k=k, discounting_type=DiscountingType.EXPONENTIAL)
        hyperbolic = DiscountingModel(k=k, discounting_type=DiscountingType.HYPERBOLIC)

        exp_values = {d: exponential.discount_value(amount, d) for d in delays}
        hyp_values = {d: hyperbolic.discount_value(amount, d) for d in delays}

        return {
            'exponential': exp_values,
            'hyperbolic': hyp_values,
            'interpretation': 'Hyperbolic shows steeper initial decline, flatter later'
        }


# ============================================================================
# TEMPORAL DISCOUNTING ENGINE
# ============================================================================

class TemporalDiscountingEngine:
    """
    Complete temporal discounting engine.

    "Ba'el's intertemporal choice engine." — Ba'el
    """

    def __init__(
        self,
        k: float = 0.1
    ):
        """Initialize engine."""
        self._paradigm = TemporalDiscountingParadigm()
        self._system = TemporalDiscountingSystem(k=k)

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    @property
    def k(self) -> float:
        """Get k parameter."""
        return self._system._model.k

    @k.setter
    def k(self, value: float):
        """Set k parameter."""
        self._system._model.k = value

    # Choice management

    def create_choice(
        self,
        immediate: float,
        delayed: float,
        delay_days: int
    ) -> Choice:
        """Create a choice."""
        return self._system.create_choice(immediate, delayed, delay_days)

    def make_choice(
        self,
        choice: Choice
    ) -> str:
        """Make choice."""
        return self._system.make_choice(choice)

    def discount(
        self,
        amount: float,
        delay_days: int
    ) -> float:
        """Discount a value."""
        return self._system._model.discount_value(amount, delay_days)

    def find_indifference(
        self,
        delayed_amount: float,
        delay_days: int
    ) -> float:
        """Find indifference point."""
        return self._system.run_titration(delayed_amount, delay_days)

    # Experiments

    def run_basic_experiment(
        self
    ) -> Dict[str, Any]:
        """Run basic experiment."""
        result = self._paradigm.run_basic_paradigm(self.k)
        self._experiment_results.append(result)
        return result

    def generate_curve(
        self
    ) -> Dict[str, Any]:
        """Generate discounting curve."""
        return self._paradigm.run_discounting_curve(self.k)

    def estimate_k(
        self
    ) -> Dict[str, Any]:
        """Estimate k parameter."""
        return self._paradigm.run_k_estimation()

    def compare_domains(
        self
    ) -> Dict[str, Any]:
        """Compare domains."""
        return self._paradigm.run_domain_comparison(self.k)

    def study_magnitude(
        self
    ) -> Dict[str, Any]:
        """Study magnitude effect."""
        return self._paradigm.run_magnitude_effect(self.k)

    def compare_models(
        self
    ) -> Dict[str, Any]:
        """Compare exponential vs hyperbolic."""
        return self._paradigm.compare_exponential_hyperbolic()

    # Analysis

    def get_metrics(self) -> DiscountingMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_basic_experiment()

        last = self._experiment_results[-1]
        curve = self.generate_curve()

        return DiscountingMetrics(
            k_parameter=self.k,
            indifference_delay=curve['half_life'],
            impulsivity_score=self.k * 100,
            consistency=0.8
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'k': self.k,
            'rewards': len(self._system._rewards),
            'choices': len(self._system._choices)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_temporal_discounting_engine(
    k: float = 0.1
) -> TemporalDiscountingEngine:
    """Create temporal discounting engine."""
    return TemporalDiscountingEngine(k=k)


def demonstrate_temporal_discounting() -> Dict[str, Any]:
    """Demonstrate temporal discounting."""
    engine = create_temporal_discounting_engine(k=0.05)

    # Basic experiment
    basic = engine.run_basic_experiment()

    # Discounting curve
    curve = engine.generate_curve()

    # Domain comparison
    domains = engine.compare_domains()

    # Magnitude effect
    magnitude = engine.study_magnitude()

    # Model comparison
    models = engine.compare_models()

    return {
        'basic': {
            'k': basic['k_parameter'],
            'immediate_rate': f"{basic['immediate_choice_rate']:.0%}",
            'impulsivity': basic['impulsivity']
        },
        'discounting_curve': {
            str(delay): f"${value:.2f}"
            for delay, value in list(curve['values'].items())[:4]
        },
        'half_life_days': f"{curve['half_life']:.0f}",
        'by_domain': {
            domain: f"k={data['effective_k']:.3f}"
            for domain, data in domains.items()
        },
        'interpretation': (
            f"k = {basic['k_parameter']}, "
            f"immediate choice: {basic['immediate_choice_rate']:.0%}. "
            f"Hyperbolic discounting describes human choices."
        )
    }


def get_temporal_discounting_facts() -> Dict[str, str]:
    """Get facts about temporal discounting."""
    return {
        'mazur_1987': 'Hyperbolic discounting model',
        'ainslie_1975': 'Early work on self-control',
        'hyperbolic': 'Steeper initial decline, preference reversals',
        'impulsivity': 'Higher k = more impulsive',
        'magnitude_effect': 'Smaller amounts discounted more',
        'domain_differences': 'Health, money, environment differ',
        'clinical': 'High k in addiction, ADHD',
        'applications': 'Savings, health behavior, policy'
    }
