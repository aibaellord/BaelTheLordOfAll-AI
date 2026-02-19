"""
BAEL Counterfactual Thinking Engine
=====================================

What-if reasoning and alternative outcomes.
Counterfactual conditionals and causal reasoning.

"Ba'el contemplates what might have been." — Ba'el
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

logger = logging.getLogger("BAEL.CounterfactualThinking")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class CounterfactualType(Enum):
    """Types of counterfactuals."""
    UPWARD = auto()      # Better outcome could have occurred
    DOWNWARD = auto()    # Worse outcome could have occurred
    ADDITIVE = auto()    # Adding an action
    SUBTRACTIVE = auto() # Removing an action


class MutabilityLevel(Enum):
    """How easily an antecedent can be mentally mutated."""
    HIGH = auto()        # Easy to change
    MEDIUM = auto()      # Moderate effort
    LOW = auto()         # Difficult to change
    IMMUTABLE = auto()   # Cannot be changed


class FocusType(Enum):
    """Focus of counterfactual."""
    SELF = auto()        # Own actions
    OTHER = auto()       # Others' actions
    SITUATION = auto()   # Circumstances
    NORM = auto()        # Deviation from normal


class EmotionalValence(Enum):
    """Emotional response."""
    REGRET = auto()
    RELIEF = auto()
    GUILT = auto()
    GRATITUDE = auto()
    DISAPPOINTMENT = auto()


@dataclass
class Event:
    """
    An event or action.
    """
    id: str
    description: str
    actor: str
    timestamp: float
    controllable: bool
    normality: float  # 0-1, how normal/expected


@dataclass
class Outcome:
    """
    An outcome of events.
    """
    id: str
    description: str
    valence: float  # -1 to 1, negative to positive
    actual: bool    # Whether this actually occurred


@dataclass
class Antecedent:
    """
    An antecedent that could be mutated.
    """
    event: Event
    mutability: MutabilityLevel
    mutation: str  # How it would be different


@dataclass
class Counterfactual:
    """
    A counterfactual thought.
    """
    id: str
    antecedent: Antecedent
    consequent: Outcome
    type: CounterfactualType
    focus: FocusType
    strength: float  # 0-1, likelihood
    emotion: EmotionalValence


@dataclass
class CausalChain:
    """
    A causal chain of events.
    """
    id: str
    events: List[Event]
    outcome: Outcome
    causal_links: Dict[str, List[str]]  # event_id -> caused event_ids


@dataclass
class CounterfactualMetrics:
    """
    Metrics for counterfactual thinking.
    """
    upward_ratio: float
    downward_ratio: float
    self_focus_ratio: float
    average_mutability: float
    dominant_emotion: EmotionalValence


# ============================================================================
# MUTABILITY ANALYZER
# ============================================================================

class MutabilityAnalyzer:
    """
    Analyze mutability of events.

    "Ba'el knows what can be changed." — Ba'el
    """

    def __init__(self):
        """Initialize analyzer."""
        self._lock = threading.RLock()

    def analyze_mutability(
        self,
        event: Event
    ) -> MutabilityLevel:
        """Analyze how mutable an event is."""
        # Factors affecting mutability:
        # 1. Controllability
        # 2. Normality (exceptions are more mutable)
        # 3. Actor (self-actions more mutable)

        score = 0.0

        if event.controllable:
            score += 0.3

        # Abnormal events are more mutable (easier to imagine as normal)
        if event.normality < 0.5:
            score += 0.3

        # Self-actions are more mutable
        if event.actor == "self":
            score += 0.2

        # Recent events are more mutable
        age = time.time() - event.timestamp
        if age < 3600:  # Less than 1 hour
            score += 0.2

        if score > 0.7:
            return MutabilityLevel.HIGH
        elif score > 0.4:
            return MutabilityLevel.MEDIUM
        elif score > 0.2:
            return MutabilityLevel.LOW
        else:
            return MutabilityLevel.IMMUTABLE

    def get_mutation(
        self,
        event: Event,
        cf_type: CounterfactualType
    ) -> str:
        """Get a plausible mutation for event."""
        if cf_type == CounterfactualType.ADDITIVE:
            return f"If {event.actor} had also [additional action]..."
        elif cf_type == CounterfactualType.SUBTRACTIVE:
            return f"If {event.actor} had not {event.description}..."
        else:
            return f"If {event.description} had been different..."


# ============================================================================
# CAUSAL MODELER
# ============================================================================

class CausalModeler:
    """
    Model causal relationships.

    "Ba'el traces the causal web." — Ba'el
    """

    def __init__(self):
        """Initialize modeler."""
        self._chains: Dict[str, CausalChain] = {}
        self._chain_counter = 0
        self._lock = threading.RLock()

    def _generate_chain_id(self) -> str:
        self._chain_counter += 1
        return f"chain_{self._chain_counter}"

    def create_chain(
        self,
        events: List[Event],
        outcome: Outcome
    ) -> CausalChain:
        """Create causal chain."""
        with self._lock:
            # Simple linear causation
            causal_links = {}
            for i in range(len(events) - 1):
                causal_links[events[i].id] = [events[i + 1].id]

            # Last event causes outcome
            if events:
                causal_links[events[-1].id] = [outcome.id]

            chain = CausalChain(
                id=self._generate_chain_id(),
                events=events,
                outcome=outcome,
                causal_links=causal_links
            )

            self._chains[chain.id] = chain
            return chain

    def get_closest_cause(
        self,
        chain: CausalChain
    ) -> Optional[Event]:
        """Get the closest cause to outcome."""
        if chain.events:
            return chain.events[-1]
        return None

    def get_pivotal_events(
        self,
        chain: CausalChain
    ) -> List[Event]:
        """Get pivotal events in the chain."""
        # Events that if changed would likely change outcome
        pivotal = []
        for event in chain.events:
            if event.controllable and event.normality < 0.5:
                pivotal.append(event)
        return pivotal

    def propagate_change(
        self,
        chain: CausalChain,
        changed_event: Event,
        change: str
    ) -> Outcome:
        """Propagate change through causal chain."""
        # Simulate what would happen if event changed
        # Simplified: just flip the outcome valence

        new_valence = -chain.outcome.valence  # Flip

        return Outcome(
            id=chain.outcome.id + "_cf",
            description=f"Alternative: {change}",
            valence=new_valence,
            actual=False
        )


# ============================================================================
# COUNTERFACTUAL GENERATOR
# ============================================================================

class CounterfactualGenerator:
    """
    Generate counterfactual thoughts.

    "Ba'el imagines alternatives." — Ba'el
    """

    def __init__(
        self,
        mutability_analyzer: MutabilityAnalyzer,
        causal_modeler: CausalModeler
    ):
        """Initialize generator."""
        self._mutability = mutability_analyzer
        self._causal = causal_modeler

        self._counterfactuals: List[Counterfactual] = []
        self._cf_counter = 0

        self._lock = threading.RLock()

    def _generate_cf_id(self) -> str:
        self._cf_counter += 1
        return f"cf_{self._cf_counter}"

    def generate(
        self,
        chain: CausalChain
    ) -> List[Counterfactual]:
        """Generate counterfactuals for causal chain."""
        with self._lock:
            counterfactuals = []

            # Get mutable events
            for event in chain.events:
                mutability = self._mutability.analyze_mutability(event)

                if mutability == MutabilityLevel.IMMUTABLE:
                    continue

                # Determine type based on outcome valence
                if chain.outcome.valence < 0:
                    cf_type = CounterfactualType.UPWARD
                    emotion = EmotionalValence.REGRET
                else:
                    cf_type = CounterfactualType.DOWNWARD
                    emotion = EmotionalValence.RELIEF

                # Get mutation
                mutation = self._mutability.get_mutation(event, cf_type)

                antecedent = Antecedent(
                    event=event,
                    mutability=mutability,
                    mutation=mutation
                )

                # Get alternative outcome
                consequent = self._causal.propagate_change(chain, event, mutation)

                # Determine focus
                if event.actor == "self":
                    focus = FocusType.SELF
                elif event.actor == "other":
                    focus = FocusType.OTHER
                else:
                    focus = FocusType.SITUATION

                # Calculate strength (likelihood of counterfactual)
                strength = 0.5
                if mutability == MutabilityLevel.HIGH:
                    strength += 0.3
                if event.normality < 0.3:
                    strength += 0.2

                cf = Counterfactual(
                    id=self._generate_cf_id(),
                    antecedent=antecedent,
                    consequent=consequent,
                    type=cf_type,
                    focus=focus,
                    strength=min(1.0, strength),
                    emotion=emotion
                )

                counterfactuals.append(cf)
                self._counterfactuals.append(cf)

            return counterfactuals

    def generate_upward(
        self,
        chain: CausalChain
    ) -> List[Counterfactual]:
        """Generate upward counterfactuals (better outcomes)."""
        all_cfs = self.generate(chain)
        return [cf for cf in all_cfs if cf.type == CounterfactualType.UPWARD]

    def generate_downward(
        self,
        chain: CausalChain
    ) -> List[Counterfactual]:
        """Generate downward counterfactuals (worse outcomes)."""
        all_cfs = self.generate(chain)
        return [cf for cf in all_cfs if cf.type == CounterfactualType.DOWNWARD]


# ============================================================================
# EMOTION ANALYZER
# ============================================================================

class EmotionAnalyzer:
    """
    Analyze emotions from counterfactuals.

    "Ba'el feels the weight of what-ifs." — Ba'el
    """

    def __init__(self):
        """Initialize analyzer."""
        self._lock = threading.RLock()

    def analyze_emotion(
        self,
        counterfactual: Counterfactual,
        chain: CausalChain
    ) -> EmotionalValence:
        """Analyze emotional response to counterfactual."""
        outcome_valence = chain.outcome.valence
        cf_type = counterfactual.type
        focus = counterfactual.focus

        if cf_type == CounterfactualType.UPWARD:
            # Better outcome could have occurred
            if focus == FocusType.SELF:
                if counterfactual.antecedent.event.controllable:
                    return EmotionalValence.REGRET
                else:
                    return EmotionalValence.DISAPPOINTMENT
            else:
                return EmotionalValence.DISAPPOINTMENT
        else:
            # Worse outcome could have occurred
            if focus == FocusType.SELF:
                return EmotionalValence.RELIEF
            else:
                return EmotionalValence.GRATITUDE

    def get_intensity(
        self,
        counterfactual: Counterfactual
    ) -> float:
        """Get emotional intensity."""
        # Higher mutability = stronger emotion
        mutability_weight = {
            MutabilityLevel.HIGH: 1.0,
            MutabilityLevel.MEDIUM: 0.7,
            MutabilityLevel.LOW: 0.4,
            MutabilityLevel.IMMUTABLE: 0.1
        }

        return (counterfactual.strength *
                mutability_weight.get(counterfactual.antecedent.mutability, 0.5))


# ============================================================================
# FUNCTIONAL ANALYSIS
# ============================================================================

class FunctionalAnalyzer:
    """
    Analyze functions of counterfactual thinking.

    "Ba'el learns from alternatives." — Ba'el
    """

    def __init__(self):
        """Initialize analyzer."""
        self._lock = threading.RLock()

    def extract_lessons(
        self,
        counterfactual: Counterfactual
    ) -> List[str]:
        """Extract lessons from counterfactual."""
        lessons = []

        event = counterfactual.antecedent.event

        if counterfactual.type == CounterfactualType.UPWARD:
            # Learn what to do differently
            if counterfactual.focus == FocusType.SELF:
                lessons.append(f"Next time, consider: {counterfactual.antecedent.mutation}")
            else:
                lessons.append(f"Be aware of: {event.description}")
        else:
            # Appreciate what went well
            lessons.append(f"Fortunate that: {event.description}")

        return lessons

    def get_preparation_value(
        self,
        counterfactual: Counterfactual
    ) -> float:
        """How useful is this counterfactual for future preparation?"""
        value = 0.0

        # Controllable events are more useful
        if counterfactual.antecedent.event.controllable:
            value += 0.4

        # Upward counterfactuals are more preparative
        if counterfactual.type == CounterfactualType.UPWARD:
            value += 0.3

        # Self-focused are more actionable
        if counterfactual.focus == FocusType.SELF:
            value += 0.3

        return value


# ============================================================================
# COUNTERFACTUAL THINKING ENGINE
# ============================================================================

class CounterfactualThinkingEngine:
    """
    Complete counterfactual thinking engine.

    "Ba'el's what-if reasoning." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._mutability = MutabilityAnalyzer()
        self._causal = CausalModeler()
        self._generator = CounterfactualGenerator(self._mutability, self._causal)
        self._emotion = EmotionAnalyzer()
        self._functional = FunctionalAnalyzer()

        self._event_counter = 0
        self._outcome_counter = 0

        self._lock = threading.RLock()

    def _generate_event_id(self) -> str:
        self._event_counter += 1
        return f"event_{self._event_counter}"

    def _generate_outcome_id(self) -> str:
        self._outcome_counter += 1
        return f"outcome_{self._outcome_counter}"

    # Event creation

    def create_event(
        self,
        description: str,
        actor: str = "self",
        controllable: bool = True,
        normality: float = 0.5
    ) -> Event:
        """Create an event."""
        return Event(
            id=self._generate_event_id(),
            description=description,
            actor=actor,
            timestamp=time.time(),
            controllable=controllable,
            normality=normality
        )

    def create_outcome(
        self,
        description: str,
        valence: float,
        actual: bool = True
    ) -> Outcome:
        """Create an outcome."""
        return Outcome(
            id=self._generate_outcome_id(),
            description=description,
            valence=valence,
            actual=actual
        )

    # Causal chain

    def create_causal_chain(
        self,
        events: List[Event],
        outcome: Outcome
    ) -> CausalChain:
        """Create causal chain."""
        return self._causal.create_chain(events, outcome)

    # Counterfactual generation

    def generate_counterfactuals(
        self,
        chain: CausalChain
    ) -> List[Counterfactual]:
        """Generate counterfactuals for chain."""
        return self._generator.generate(chain)

    def generate_upward_counterfactuals(
        self,
        chain: CausalChain
    ) -> List[Counterfactual]:
        """Generate upward counterfactuals."""
        return self._generator.generate_upward(chain)

    def generate_downward_counterfactuals(
        self,
        chain: CausalChain
    ) -> List[Counterfactual]:
        """Generate downward counterfactuals."""
        return self._generator.generate_downward(chain)

    # Analysis

    def analyze_emotion(
        self,
        counterfactual: Counterfactual,
        chain: CausalChain
    ) -> Tuple[EmotionalValence, float]:
        """Analyze emotion and intensity."""
        emotion = self._emotion.analyze_emotion(counterfactual, chain)
        intensity = self._emotion.get_intensity(counterfactual)
        return emotion, intensity

    def extract_lessons(
        self,
        counterfactual: Counterfactual
    ) -> List[str]:
        """Extract lessons from counterfactual."""
        return self._functional.extract_lessons(counterfactual)

    def get_preparation_value(
        self,
        counterfactual: Counterfactual
    ) -> float:
        """Get preparation value."""
        return self._functional.get_preparation_value(counterfactual)

    # Metrics

    def get_metrics(self) -> CounterfactualMetrics:
        """Get counterfactual metrics."""
        cfs = self._generator._counterfactuals

        if not cfs:
            return CounterfactualMetrics(
                upward_ratio=0.0,
                downward_ratio=0.0,
                self_focus_ratio=0.0,
                average_mutability=0.0,
                dominant_emotion=EmotionalValence.REGRET
            )

        upward = sum(1 for cf in cfs if cf.type == CounterfactualType.UPWARD)
        self_focus = sum(1 for cf in cfs if cf.focus == FocusType.SELF)

        mutability_scores = {
            MutabilityLevel.HIGH: 1.0,
            MutabilityLevel.MEDIUM: 0.66,
            MutabilityLevel.LOW: 0.33,
            MutabilityLevel.IMMUTABLE: 0.0
        }
        avg_mut = sum(
            mutability_scores[cf.antecedent.mutability] for cf in cfs
        ) / len(cfs)

        # Dominant emotion
        emotion_counts = defaultdict(int)
        for cf in cfs:
            emotion_counts[cf.emotion] += 1
        dominant = max(emotion_counts.items(), key=lambda x: x[1])[0]

        return CounterfactualMetrics(
            upward_ratio=upward / len(cfs),
            downward_ratio=(len(cfs) - upward) / len(cfs),
            self_focus_ratio=self_focus / len(cfs),
            average_mutability=avg_mut,
            dominant_emotion=dominant
        )

    # Scenario analysis

    def analyze_scenario(
        self,
        events: List[Dict[str, Any]],
        outcome_description: str,
        outcome_valence: float
    ) -> Dict[str, Any]:
        """Analyze a complete scenario."""
        # Create events
        event_objs = [
            self.create_event(
                e.get('description', 'Event'),
                e.get('actor', 'self'),
                e.get('controllable', True),
                e.get('normality', 0.5)
            )
            for e in events
        ]

        # Create outcome
        outcome = self.create_outcome(outcome_description, outcome_valence)

        # Create chain
        chain = self.create_causal_chain(event_objs, outcome)

        # Generate counterfactuals
        cfs = self.generate_counterfactuals(chain)

        # Analyze
        analyses = []
        for cf in cfs:
            emotion, intensity = self.analyze_emotion(cf, chain)
            lessons = self.extract_lessons(cf)
            prep_value = self.get_preparation_value(cf)

            analyses.append({
                'counterfactual': cf,
                'emotion': emotion,
                'intensity': intensity,
                'lessons': lessons,
                'preparation_value': prep_value
            })

        return {
            'chain': chain,
            'counterfactuals': cfs,
            'analyses': analyses,
            'metrics': self.get_metrics()
        }

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'chains': len(self._causal._chains),
            'counterfactuals': len(self._generator._counterfactuals)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_counterfactual_engine() -> CounterfactualThinkingEngine:
    """Create counterfactual thinking engine."""
    return CounterfactualThinkingEngine()


def analyze_regret_scenario(
    action: str,
    outcome: str,
    outcome_valence: float = -0.7
) -> Dict[str, Any]:
    """Analyze a scenario that might cause regret."""
    engine = create_counterfactual_engine()

    events = [
        {'description': action, 'actor': 'self', 'controllable': True, 'normality': 0.4}
    ]

    return engine.analyze_scenario(events, outcome, outcome_valence)


def get_counterfactual_functions() -> Dict[str, str]:
    """Get functions of counterfactual thinking."""
    return {
        'preparative': 'Helps prepare for future similar situations',
        'affective': 'Generates emotions like regret and relief',
        'causal_inference': 'Helps understand causal relationships',
        'contrast': 'Provides comparison to appreciate/depreciate outcomes',
        'behavioral_change': 'Motivates different behavior in future'
    }
