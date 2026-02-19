"""
BAEL Imagination Inflation Effect Engine
==========================================

Imagining events makes them seem real.
Garry et al.'s imagination inflation effect.

"Ba'el's imagination becomes reality." — Ba'el
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

logger = logging.getLogger("BAEL.ImaginationInflation")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class EventType(Enum):
    """Type of childhood event."""
    COMMON = auto()
    UNCOMMON = auto()
    UNLIKELY = auto()


class ImaginationCondition(Enum):
    """Imagination condition."""
    IMAGINED = auto()
    NOT_IMAGINED = auto()


class ConfidenceLevel(Enum):
    """Confidence level."""
    DEFINITELY_HAPPENED = auto()
    PROBABLY_HAPPENED = auto()
    MIGHT_HAVE_HAPPENED = auto()
    UNSURE = auto()
    PROBABLY_NOT = auto()
    DEFINITELY_NOT = auto()


class ImageryDetail(Enum):
    """Level of imagery detail."""
    MINIMAL = auto()
    MODERATE = auto()
    ELABORATE = auto()


@dataclass
class ChildhoodEvent:
    """
    A childhood event to rate.
    """
    id: str
    description: str
    event_type: EventType
    base_plausibility: float


@dataclass
class ImaginationTrial:
    """
    An imagination trial.
    """
    event: ChildhoodEvent
    imagery_detail: ImageryDetail
    duration_s: float
    vividness: float


@dataclass
class ConfidenceRating:
    """
    Confidence rating for event occurrence.
    """
    event: ChildhoodEvent
    condition: ImaginationCondition
    rating: float   # 1-8 scale
    phase: str      # pre or post


@dataclass
class InflationMetrics:
    """
    Imagination inflation metrics.
    """
    imagined_increase: float
    not_imagined_increase: float
    inflation_effect: float


# ============================================================================
# IMAGINATION INFLATION MODEL
# ============================================================================

class ImaginationInflationModel:
    """
    Model of imagination inflation.

    "Ba'el's imagination-reality model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base confidence shift
        self._test_retest_shift = 0.15  # Natural shift

        # Imagination effects
        self._imagination_boost = 0.45  # Main effect
        self._detail_effects = {
            ImageryDetail.MINIMAL: 0.20,
            ImageryDetail.MODERATE: 0.40,
            ImageryDetail.ELABORATE: 0.60
        }

        # Number of imaginations
        self._repetition_boost = 0.12  # Per imagination
        self._max_repetition_effect = 0.40

        # Event plausibility effects
        self._plausibility_weight = 0.15

        # Vividness effects
        self._vividness_weight = 0.20

        # Source monitoring
        self._source_confusion = 0.35  # Probability of source error

        # Delay effects
        self._delay_boost = 0.02  # Per day

        # Individual differences
        self._fantasy_proneness = 0.15
        self._dissociation = 0.10

        self._lock = threading.RLock()

    def calculate_confidence_change(
        self,
        condition: ImaginationCondition,
        base_plausibility: float = 0.5,
        imagery_detail: ImageryDetail = ImageryDetail.MODERATE,
        n_imaginations: int = 1,
        vividness: float = 0.5
    ) -> float:
        """Calculate change in confidence rating."""
        if condition == ImaginationCondition.NOT_IMAGINED:
            # Just test-retest shift
            return self._test_retest_shift + random.uniform(-0.1, 0.1)

        # Imagined condition
        base_boost = self._imagination_boost

        # Detail level
        detail_boost = self._detail_effects[imagery_detail]

        # Repetition
        rep_boost = min(
            (n_imaginations - 1) * self._repetition_boost,
            self._max_repetition_effect
        )

        # Plausibility
        plaus_mod = 0.5 + base_plausibility * self._plausibility_weight

        # Vividness
        vivid_boost = (vividness - 0.5) * self._vividness_weight * 2

        change = (base_boost + detail_boost + rep_boost + vivid_boost) * plaus_mod

        # Add noise
        change += random.uniform(-0.2, 0.2)

        return max(0.1, min(2.0, change))

    def calculate_source_confusion(
        self,
        n_imaginations: int,
        imagery_detail: ImageryDetail
    ) -> float:
        """Calculate probability of source confusion."""
        base = self._source_confusion

        # More imaginations = more confusion
        base += n_imaginations * 0.05

        # More detail = more confusion
        if imagery_detail == ImageryDetail.ELABORATE:
            base += 0.15
        elif imagery_detail == ImageryDetail.MODERATE:
            base += 0.08

        return min(0.75, base)

    def get_mechanisms(
        self
    ) -> Dict[str, str]:
        """Get proposed mechanisms."""
        return {
            'source_monitoring': 'Confuse imagination for memory',
            'familiarity': 'Imagined events feel familiar',
            'fluency': 'Easy to imagine = must have happened',
            'schema_activation': 'Activates related memories',
            'imagery_rehearsal': 'Creates memory-like traces'
        }

    def get_boundary_conditions(
        self
    ) -> Dict[str, str]:
        """Get boundary conditions."""
        return {
            'plausibility': 'Effect stronger for plausible events',
            'detail': 'More detail = stronger effect',
            'repetition': 'Multiple imaginations increase effect',
            'delay': 'Effect persists and may increase',
            'individual_differences': 'Fantasy proneness increases effect'
        }


# ============================================================================
# IMAGINATION INFLATION SYSTEM
# ============================================================================

class ImaginationInflationSystem:
    """
    Imagination inflation simulation system.

    "Ba'el's imagination system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = ImaginationInflationModel()

        self._events: Dict[str, ChildhoodEvent] = {}
        self._imaginations: Dict[str, List[ImaginationTrial]] = defaultdict(list)
        self._ratings: List[ConfidenceRating] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"event_{self._counter}"

    def create_event(
        self,
        description: str,
        event_type: EventType = EventType.COMMON
    ) -> ChildhoodEvent:
        """Create childhood event."""
        plausibility = {
            EventType.COMMON: 0.7,
            EventType.UNCOMMON: 0.5,
            EventType.UNLIKELY: 0.3
        }[event_type]

        event = ChildhoodEvent(
            id=self._generate_id(),
            description=description,
            event_type=event_type,
            base_plausibility=plausibility
        )

        self._events[event.id] = event

        return event

    def get_standard_events(
        self
    ) -> List[ChildhoodEvent]:
        """Get standard LEI events."""
        events = []

        descriptions = [
            ("Broke a window with your hand", EventType.UNCOMMON),
            ("Found a $10 bill in a parking lot", EventType.COMMON),
            ("Got stuck in a tree and had to have someone help you down", EventType.COMMON),
            ("Called 911 in an emergency", EventType.UNCOMMON),
            ("Had a lifeguard pull you out of the water", EventType.UNLIKELY),
            ("Won a stuffed animal at a carnival game", EventType.COMMON),
            ("Shook hands with a famous person", EventType.UNLIKELY),
            ("Got in trouble for calling 911", EventType.UNLIKELY)
        ]

        for desc, event_type in descriptions:
            event = self.create_event(desc, event_type)
            events.append(event)

        return events

    def rate_confidence(
        self,
        event: ChildhoodEvent,
        phase: str = "pre"
    ) -> ConfidenceRating:
        """Rate confidence that event occurred."""
        # Base rating (1-8 scale)
        base = 3.0 + event.base_plausibility * 2

        # Add noise
        base += random.uniform(-1, 1)

        rating = ConfidenceRating(
            event=event,
            condition=ImaginationCondition.NOT_IMAGINED,
            rating=max(1, min(8, base)),
            phase=phase
        )

        self._ratings.append(rating)

        return rating

    def imagine_event(
        self,
        event: ChildhoodEvent,
        detail: ImageryDetail = ImageryDetail.MODERATE,
        duration_s: float = 60
    ) -> ImaginationTrial:
        """Imagine an event."""
        vividness = random.uniform(0.4, 0.9)

        trial = ImaginationTrial(
            event=event,
            imagery_detail=detail,
            duration_s=duration_s,
            vividness=vividness
        )

        self._imaginations[event.id].append(trial)

        return trial

    def rate_post_imagination(
        self,
        event: ChildhoodEvent
    ) -> ConfidenceRating:
        """Rate confidence after imagination."""
        # Get imaginations for this event
        imaginations = self._imaginations.get(event.id, [])

        if imaginations:
            condition = ImaginationCondition.IMAGINED
            n_imag = len(imaginations)
            detail = imaginations[-1].imagery_detail
            vividness = imaginations[-1].vividness
        else:
            condition = ImaginationCondition.NOT_IMAGINED
            n_imag = 0
            detail = ImageryDetail.MINIMAL
            vividness = 0.5

        # Get pre-rating
        pre_ratings = [r for r in self._ratings if r.event.id == event.id and r.phase == "pre"]
        pre_rating = pre_ratings[-1].rating if pre_ratings else 4.0

        # Calculate change
        change = self._model.calculate_confidence_change(
            condition, event.base_plausibility, detail, n_imag, vividness
        )

        new_rating = pre_rating + change

        rating = ConfidenceRating(
            event=event,
            condition=condition,
            rating=max(1, min(8, new_rating)),
            phase="post"
        )

        self._ratings.append(rating)

        return rating


# ============================================================================
# IMAGINATION INFLATION PARADIGM
# ============================================================================

class ImaginationInflationParadigm:
    """
    Imagination inflation paradigm.

    "Ba'el's imagination-makes-real study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self,
        n_events: int = 8
    ) -> Dict[str, Any]:
        """Run classic imagination inflation paradigm."""
        system = ImaginationInflationSystem()

        # Get standard events
        events = system.get_standard_events()[:n_events]

        # Phase 1: Pre-ratings
        pre_ratings = {}
        for event in events:
            rating = system.rate_confidence(event, "pre")
            pre_ratings[event.id] = rating.rating

        # Phase 2: Imagination (half of events)
        imagined_ids = set()
        for i, event in enumerate(events):
            if i % 2 == 0:  # Alternate
                system.imagine_event(event)
                imagined_ids.add(event.id)

        # Phase 3: Post-ratings
        results = {
            'imagined': [],
            'not_imagined': []
        }

        for event in events:
            post = system.rate_post_imagination(event)
            pre = pre_ratings[event.id]

            change = post.rating - pre

            if event.id in imagined_ids:
                results['imagined'].append(change)
            else:
                results['not_imagined'].append(change)

        # Calculate means
        imag_mean = sum(results['imagined']) / max(1, len(results['imagined']))
        not_imag_mean = sum(results['not_imagined']) / max(1, len(results['not_imagined']))

        effect = imag_mean - not_imag_mean

        return {
            'imagined_change': imag_mean,
            'not_imagined_change': not_imag_mean,
            'inflation_effect': effect,
            'interpretation': f'Inflation: {effect:.2f} point increase for imagined events'
        }

    def run_detail_study(
        self
    ) -> Dict[str, Any]:
        """Study imagery detail effects."""
        model = ImaginationInflationModel()

        results = {}

        for detail in ImageryDetail:
            change = model.calculate_confidence_change(
                ImaginationCondition.IMAGINED,
                imagery_detail=detail
            )
            results[detail.name] = {'change': change}

        return {
            'by_detail': results,
            'interpretation': 'More detailed imagination = more inflation'
        }

    def run_repetition_study(
        self
    ) -> Dict[str, Any]:
        """Study repetition effects."""
        model = ImaginationInflationModel()

        repetitions = [1, 2, 3, 5]

        results = {}

        for n in repetitions:
            change = model.calculate_confidence_change(
                ImaginationCondition.IMAGINED,
                n_imaginations=n
            )
            results[f'{n}x'] = {'change': change}

        return {
            'by_repetition': results,
            'interpretation': 'More imaginations = more inflation'
        }

    def run_plausibility_study(
        self
    ) -> Dict[str, Any]:
        """Study event plausibility effects."""
        model = ImaginationInflationModel()

        plausibilities = [0.3, 0.5, 0.7, 0.9]

        results = {}

        for plaus in plausibilities:
            change = model.calculate_confidence_change(
                ImaginationCondition.IMAGINED,
                base_plausibility=plaus
            )
            results[f'plaus_{plaus}'] = {'change': change}

        return {
            'by_plausibility': results,
            'interpretation': 'More plausible events show more inflation'
        }

    def run_source_confusion_study(
        self
    ) -> Dict[str, Any]:
        """Study source confusion."""
        model = ImaginationInflationModel()

        conditions = [
            ('1x_minimal', 1, ImageryDetail.MINIMAL),
            ('1x_elaborate', 1, ImageryDetail.ELABORATE),
            ('3x_minimal', 3, ImageryDetail.MINIMAL),
            ('3x_elaborate', 3, ImageryDetail.ELABORATE)
        ]

        results = {}

        for condition, n, detail in conditions:
            confusion = model.calculate_source_confusion(n, detail)
            results[condition] = {'source_confusion': confusion}

        return {
            'by_condition': results,
            'interpretation': 'More detail and repetitions = more source confusion'
        }

    def run_mechanism_study(
        self
    ) -> Dict[str, Any]:
        """Study underlying mechanisms."""
        model = ImaginationInflationModel()

        mechanisms = model.get_mechanisms()
        boundaries = model.get_boundary_conditions()

        return {
            'mechanisms': mechanisms,
            'boundaries': boundaries,
            'primary': 'Source monitoring failure',
            'interpretation': 'Imagination creates memory-like traces'
        }


# ============================================================================
# IMAGINATION INFLATION ENGINE
# ============================================================================

class ImaginationInflationEngine:
    """
    Complete imagination inflation engine.

    "Ba'el's imagination-makes-reality engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = ImaginationInflationParadigm()
        self._system = ImaginationInflationSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Event operations

    def create_event(
        self,
        description: str,
        event_type: EventType = EventType.COMMON
    ) -> ChildhoodEvent:
        """Create event."""
        return self._system.create_event(description, event_type)

    def get_standard_events(
        self
    ) -> List[ChildhoodEvent]:
        """Get standard events."""
        return self._system.get_standard_events()

    def rate_confidence(
        self,
        event: ChildhoodEvent,
        phase: str = "pre"
    ) -> ConfidenceRating:
        """Rate confidence."""
        return self._system.rate_confidence(event, phase)

    def imagine_event(
        self,
        event: ChildhoodEvent
    ) -> ImaginationTrial:
        """Imagine event."""
        return self._system.imagine_event(event)

    def rate_post(
        self,
        event: ChildhoodEvent
    ) -> ConfidenceRating:
        """Rate post-imagination."""
        return self._system.rate_post_imagination(event)

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def study_detail(
        self
    ) -> Dict[str, Any]:
        """Study detail."""
        return self._paradigm.run_detail_study()

    def study_repetition(
        self
    ) -> Dict[str, Any]:
        """Study repetition."""
        return self._paradigm.run_repetition_study()

    def study_plausibility(
        self
    ) -> Dict[str, Any]:
        """Study plausibility."""
        return self._paradigm.run_plausibility_study()

    def study_source_confusion(
        self
    ) -> Dict[str, Any]:
        """Study source confusion."""
        return self._paradigm.run_source_confusion_study()

    def study_mechanisms(
        self
    ) -> Dict[str, Any]:
        """Study mechanisms."""
        return self._paradigm.run_mechanism_study()

    # Analysis

    def get_metrics(self) -> InflationMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_classic()

        last = self._experiment_results[-1]

        return InflationMetrics(
            imagined_increase=last['imagined_change'],
            not_imagined_increase=last['not_imagined_change'],
            inflation_effect=last['inflation_effect']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'events': len(self._system._events),
            'imaginations': sum(len(i) for i in self._system._imaginations.values()),
            'ratings': len(self._system._ratings)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_imagination_inflation_engine() -> ImaginationInflationEngine:
    """Create imagination inflation engine."""
    return ImaginationInflationEngine()


def demonstrate_imagination_inflation() -> Dict[str, Any]:
    """Demonstrate imagination inflation effect."""
    engine = create_imagination_inflation_engine()

    # Classic
    classic = engine.run_classic()

    # Detail
    detail = engine.study_detail()

    # Repetition
    repetition = engine.study_repetition()

    # Mechanisms
    mechanisms = engine.study_mechanisms()

    return {
        'classic': {
            'imagined_change': f"{classic['imagined_change']:.2f}",
            'not_imagined_change': f"{classic['not_imagined_change']:.2f}",
            'effect': f"{classic['inflation_effect']:.2f}"
        },
        'by_detail': {
            k: f"{v['change']:.2f}"
            for k, v in detail['by_detail'].items()
        },
        'by_repetition': {
            k: f"{v['change']:.2f}"
            for k, v in repetition['by_repetition'].items()
        },
        'mechanisms': list(mechanisms['mechanisms'].keys()),
        'interpretation': (
            f"Effect: {classic['inflation_effect']:.2f} points. "
            f"Imagining events increases belief they happened. "
            f"Source monitoring confusion."
        )
    }


def get_imagination_inflation_facts() -> Dict[str, str]:
    """Get facts about imagination inflation."""
    return {
        'garry_1996': 'Imagination inflation discovery',
        'effect': '0.5-1.5 point increase on 8-point scale',
        'mechanism': 'Source monitoring failure',
        'detail': 'More elaborate = stronger effect',
        'repetition': 'Multiple imaginations increase effect',
        'plausibility': 'Plausible events more susceptible',
        'therapy': 'Implications for recovered memory therapy',
        'applications': 'False memory research, therapy'
    }
