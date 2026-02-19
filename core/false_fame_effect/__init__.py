"""
BAEL False Fame Effect Engine
================================

Familiarity mistaken for fame.
Jacoby's false fame paradigm.

"Ba'el knows many seem famous who are not." — Ba'el
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

logger = logging.getLogger("BAEL.FalseFame")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class NameCategory(Enum):
    """Category of name."""
    FAMOUS = auto()           # Actually famous
    NON_FAMOUS_OLD = auto()   # Previously presented, not famous
    NON_FAMOUS_NEW = auto()   # New, not famous


class JudgmentType(Enum):
    """Type of fame judgment."""
    FAMOUS = auto()
    NOT_FAMOUS = auto()


class FamiliaritySource(Enum):
    """Source of familiarity."""
    TRUE_FAME = auto()        # Actually famous
    PRIOR_EXPOSURE = auto()   # Studied before
    PROCESSING_FLUENCY = auto()  # Easy to process
    NONE = auto()


@dataclass
class Name:
    """
    A name to judge.
    """
    id: str
    name: str
    category: NameCategory
    actual_fame: bool
    processing_fluency: float


@dataclass
class StudyItem:
    """
    A studied name.
    """
    name_id: str
    study_time: float
    encoding_strength: float


@dataclass
class FameJudgment:
    """
    A fame judgment.
    """
    name_id: str
    category: NameCategory
    judged_famous: bool
    actual_famous: bool
    familiarity_level: float
    confidence: float


@dataclass
class FalseFameMetrics:
    """
    False fame effect metrics.
    """
    famous_hit_rate: float
    old_nonfamous_false_alarm: float  # FALSE FAME
    new_nonfamous_false_alarm: float
    false_fame_effect: float


# ============================================================================
# FAMILIARITY MISATTRIBUTION MODEL
# ============================================================================

class FamiliarityMisattributionModel:
    """
    Model of familiarity misattribution to fame.

    "Ba'el's fame confusion." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Fame judgment parameters
        self._fame_threshold = 0.5

        # Familiarity sources
        self._fame_familiarity = 0.7
        self._study_familiarity_boost = 0.25
        self._fluency_boost = 0.15

        # Source monitoring
        self._source_monitoring_accuracy = 0.6

        # Base false alarm rate
        self._base_fa_rate = 0.15

        self._lock = threading.RLock()

    def calculate_familiarity(
        self,
        name: Name,
        studied: bool,
        encoding_strength: float = 0.0
    ) -> Tuple[float, FamiliaritySource]:
        """Calculate familiarity and likely source."""
        familiarity = 0.0
        source = FamiliaritySource.NONE

        if name.actual_fame:
            familiarity = self._fame_familiarity + random.uniform(-0.1, 0.1)
            source = FamiliaritySource.TRUE_FAME
        elif studied:
            familiarity = encoding_strength * self._study_familiarity_boost
            source = FamiliaritySource.PRIOR_EXPOSURE

        # Processing fluency adds to familiarity
        fluency_contribution = name.processing_fluency * self._fluency_boost
        familiarity += fluency_contribution

        if fluency_contribution > 0.1 and source == FamiliaritySource.NONE:
            source = FamiliaritySource.PROCESSING_FLUENCY

        return min(1.0, familiarity), source

    def judge_fame(
        self,
        name: Name,
        familiarity: float,
        source: FamiliaritySource,
        attention_level: float = 1.0
    ) -> Tuple[bool, float]:
        """Judge whether a name is famous."""
        # Base judgment on familiarity
        fame_likelihood = familiarity

        if source == FamiliaritySource.TRUE_FAME:
            # Correctly attribute familiarity to fame
            fame_likelihood += 0.2
        elif source == FamiliaritySource.PRIOR_EXPOSURE:
            # Should discount familiarity from study
            # But people often fail at source monitoring
            source_monitoring = self._source_monitoring_accuracy * attention_level

            if random.random() < source_monitoring:
                # Correctly identified as studied
                fame_likelihood -= 0.2  # Discount
            else:
                # Failed source monitoring - attribute to fame
                fame_likelihood += 0.1  # FALSE FAME
        elif source == FamiliaritySource.PROCESSING_FLUENCY:
            # Fluency can be misattributed to fame
            fame_likelihood += 0.05

        # Make judgment
        judge_famous = fame_likelihood >= self._fame_threshold

        # Add noise
        if random.random() < 0.1:
            judge_famous = not judge_famous

        confidence = abs(fame_likelihood - self._fame_threshold) + 0.5

        return judge_famous, min(1.0, confidence)


# ============================================================================
# FALSE FAME SYSTEM
# ============================================================================

class FalseFameSystem:
    """
    False fame experimental system.

    "Ba'el's fame attribution system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = FamiliarityMisattributionModel()

        self._names: Dict[str, Name] = {}
        self._studied: Dict[str, StudyItem] = {}
        self._judgments: List[FameJudgment] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"name_{self._counter}"

    def create_name(
        self,
        name: str,
        category: NameCategory
    ) -> Name:
        """Create a name."""
        name_obj = Name(
            id=self._generate_id(),
            name=name,
            category=category,
            actual_fame=category == NameCategory.FAMOUS,
            processing_fluency=random.uniform(0.3, 0.8)
        )

        self._names[name_obj.id] = name_obj

        return name_obj

    def study_name(
        self,
        name_id: str,
        study_time: float = 2.0
    ) -> StudyItem:
        """Study a name."""
        name = self._names.get(name_id)
        if not name:
            return None

        encoding = 0.3 + study_time / 10  # Longer study = stronger encoding

        item = StudyItem(
            name_id=name_id,
            study_time=study_time,
            encoding_strength=min(0.8, encoding)
        )

        self._studied[name_id] = item

        return item

    def judge_name(
        self,
        name_id: str,
        attention: float = 1.0
    ) -> FameJudgment:
        """Make fame judgment for a name."""
        name = self._names.get(name_id)
        if not name:
            return None

        studied = name_id in self._studied
        encoding = self._studied[name_id].encoding_strength if studied else 0.0

        familiarity, source = self._model.calculate_familiarity(
            name, studied, encoding
        )

        judged_famous, confidence = self._model.judge_fame(
            name, familiarity, source, attention
        )

        judgment = FameJudgment(
            name_id=name_id,
            category=name.category,
            judged_famous=judged_famous,
            actual_famous=name.actual_fame,
            familiarity_level=familiarity,
            confidence=confidence
        )

        self._judgments.append(judgment)

        return judgment


# ============================================================================
# FALSE FAME PARADIGM
# ============================================================================

class FalseFameParadigm:
    """
    False fame experimental paradigm.

    "Ba'el's fame study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_experiment(
        self,
        n_famous: int = 20,
        n_nonfamous_study: int = 20,
        n_nonfamous_new: int = 20
    ) -> Dict[str, Any]:
        """Run classic false fame experiment."""
        system = FalseFameSystem()

        # Create names
        famous_names = []
        nonfamous_study_names = []
        nonfamous_new_names = []

        for i in range(n_famous):
            name = system.create_name(f"Famous Person {i}", NameCategory.FAMOUS)
            famous_names.append(name)

        for i in range(n_nonfamous_study):
            name = system.create_name(f"Sebastian Weisdorf {i}", NameCategory.NON_FAMOUS_OLD)
            nonfamous_study_names.append(name)

        for i in range(n_nonfamous_new):
            name = system.create_name(f"Adrian Marr {i}", NameCategory.NON_FAMOUS_NEW)
            nonfamous_new_names.append(name)

        # Study phase - only nonfamous study names
        for name in nonfamous_study_names:
            system.study_name(name.id, study_time=2.0)

        # Test phase - all names
        famous_hits = 0
        old_nonfamous_fa = 0  # FALSE FAME
        new_nonfamous_fa = 0

        for name in famous_names:
            judgment = system.judge_name(name.id)
            if judgment.judged_famous:
                famous_hits += 1

        for name in nonfamous_study_names:
            judgment = system.judge_name(name.id)
            if judgment.judged_famous:
                old_nonfamous_fa += 1  # FALSE FAME

        for name in nonfamous_new_names:
            judgment = system.judge_name(name.id)
            if judgment.judged_famous:
                new_nonfamous_fa += 1

        # Calculate rates
        hit_rate = famous_hits / n_famous
        old_fa_rate = old_nonfamous_fa / n_nonfamous_study  # FALSE FAME RATE
        new_fa_rate = new_nonfamous_fa / n_nonfamous_new

        return {
            'famous_hit_rate': hit_rate,
            'old_nonfamous_fa_rate': old_fa_rate,  # FALSE FAME
            'new_nonfamous_fa_rate': new_fa_rate,
            'false_fame_effect': old_fa_rate - new_fa_rate
        }

    def run_attention_manipulation(
        self
    ) -> Dict[str, Any]:
        """Manipulate attention at test (divided vs full)."""
        results = {}

        for condition, attention in [('full', 1.0), ('divided', 0.5)]:
            system = FalseFameSystem()

            # Create and study non-famous names
            study_names = []
            for i in range(20):
                name = system.create_name(f"Name {i}", NameCategory.NON_FAMOUS_OLD)
                study_names.append(name)
                system.study_name(name.id)

            # New names
            new_names = []
            for i in range(20):
                name = system.create_name(f"New {i}", NameCategory.NON_FAMOUS_NEW)
                new_names.append(name)

            # Test with manipulation
            old_fa = sum(1 for n in study_names
                        if system.judge_name(n.id, attention).judged_famous)
            new_fa = sum(1 for n in new_names
                        if system.judge_name(n.id, attention).judged_famous)

            results[condition] = {
                'old_fa_rate': old_fa / 20,
                'new_fa_rate': new_fa / 20,
                'false_fame_effect': (old_fa - new_fa) / 20
            }

        return results

    def run_delay_study(
        self
    ) -> Dict[str, Any]:
        """Study effect of delay on false fame."""
        # False fame typically greater after 24h delay
        # because source memory decays faster than familiarity

        delays = {
            'immediate': {'source_decay': 0.0, 'familiarity_decay': 0.0},
            '24h_delay': {'source_decay': 0.4, 'familiarity_decay': 0.1}
        }

        results = {}

        for delay_name, decay in delays.items():
            system = FalseFameSystem()

            # Study names
            study_names = []
            for i in range(20):
                name = system.create_name(f"Name {i}", NameCategory.NON_FAMOUS_OLD)
                study_names.append(name)
                item = system.study_name(name.id)
                # Apply decay to source memory (but not familiarity as much)
                item.encoding_strength *= (1 - decay['source_decay'])

            # Reduce source monitoring accuracy for delay
            system._model._source_monitoring_accuracy *= (1 - decay['source_decay'])

            # Test
            false_fame_count = 0
            for name in study_names:
                judgment = system.judge_name(name.id)
                if judgment.judged_famous:
                    false_fame_count += 1

            results[delay_name] = {
                'false_fame_rate': false_fame_count / 20,
                'source_monitoring': system._model._source_monitoring_accuracy
            }

        return results

    def run_aging_study(
        self
    ) -> Dict[str, Any]:
        """Study age differences in false fame."""
        # Older adults show larger false fame effect due to
        # poorer source monitoring

        age_groups = {
            'young': {'source_monitoring': 0.7, 'familiarity_intact': 0.9},
            'older': {'source_monitoring': 0.4, 'familiarity_intact': 0.85}
        }

        results = {}

        for age, params in age_groups.items():
            system = FalseFameSystem()
            system._model._source_monitoring_accuracy = params['source_monitoring']

            # Study names
            study_names = []
            for i in range(20):
                name = system.create_name(f"Name {i}", NameCategory.NON_FAMOUS_OLD)
                study_names.append(name)
                item = system.study_name(name.id)
                item.encoding_strength *= params['familiarity_intact']

            # Test
            false_fame_count = 0
            for name in study_names:
                judgment = system.judge_name(name.id)
                if judgment.judged_famous:
                    false_fame_count += 1

            results[age] = {
                'false_fame_rate': false_fame_count / 20,
                'source_monitoring': params['source_monitoring']
            }

        return results


# ============================================================================
# FALSE FAME ENGINE
# ============================================================================

class FalseFameEngine:
    """
    Complete false fame engine.

    "Ba'el's fame misattribution engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = FalseFameParadigm()
        self._system = FalseFameSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Name management

    def create_name(
        self,
        name: str,
        category: NameCategory
    ) -> Name:
        """Create a name."""
        return self._system.create_name(name, category)

    def study(
        self,
        name_id: str
    ) -> StudyItem:
        """Study a name."""
        return self._system.study_name(name_id)

    def judge(
        self,
        name_id: str
    ) -> FameJudgment:
        """Judge a name."""
        return self._system.judge_name(name_id)

    # Experiments

    def run_classic_experiment(
        self
    ) -> Dict[str, Any]:
        """Run classic experiment."""
        result = self._paradigm.run_classic_experiment()
        self._experiment_results.append(result)
        return result

    def study_attention(
        self
    ) -> Dict[str, Any]:
        """Study attention effects."""
        return self._paradigm.run_attention_manipulation()

    def study_delay(
        self
    ) -> Dict[str, Any]:
        """Study delay effects."""
        return self._paradigm.run_delay_study()

    def study_aging(
        self
    ) -> Dict[str, Any]:
        """Study aging effects."""
        return self._paradigm.run_aging_study()

    def simulate_real_world(
        self
    ) -> Dict[str, Any]:
        """Simulate real-world false fame scenario."""
        system = FalseFameSystem()

        # You read a list of names in a magazine article
        article_names = []
        for i in range(10):
            name = system.create_name(f"John Henderson {i}", NameCategory.NON_FAMOUS_OLD)
            article_names.append(name)
            system.study_name(name.id, study_time=1.0)  # Brief exposure

        # Later, someone asks if you know these people
        false_recognitions = 0
        for name in article_names:
            judgment = system.judge_name(name.id, attention=0.7)  # Casual judgment
            if judgment.judged_famous:
                false_recognitions += 1

        return {
            'names_read': len(article_names),
            'judged_famous': false_recognitions,
            'false_fame_rate': false_recognitions / len(article_names),
            'scenario': 'Prior exposure in magazine leads to false fame judgments'
        }

    # Analysis

    def get_metrics(self) -> FalseFameMetrics:
        """Get false fame metrics."""
        if not self._experiment_results:
            self.run_classic_experiment()

        last = self._experiment_results[-1]

        return FalseFameMetrics(
            famous_hit_rate=last['famous_hit_rate'],
            old_nonfamous_false_alarm=last['old_nonfamous_fa_rate'],
            new_nonfamous_false_alarm=last['new_nonfamous_fa_rate'],
            false_fame_effect=last['false_fame_effect']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'names': len(self._system._names),
            'studied': len(self._system._studied),
            'judgments': len(self._system._judgments)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_false_fame_engine() -> FalseFameEngine:
    """Create false fame engine."""
    return FalseFameEngine()


def demonstrate_false_fame() -> Dict[str, Any]:
    """Demonstrate false fame effect."""
    engine = create_false_fame_engine()

    # Classic experiment
    classic = engine.run_classic_experiment()

    # Attention study
    attention = engine.study_attention()

    # Delay study
    delay = engine.study_delay()

    # Aging study
    aging = engine.study_aging()

    # Real world
    real_world = engine.simulate_real_world()

    return {
        'false_fame_effect': {
            'famous_hits': f"{classic['famous_hit_rate']:.0%}",
            'old_nonfamous_fa': f"{classic['old_nonfamous_fa_rate']:.0%}",
            'new_nonfamous_fa': f"{classic['new_nonfamous_fa_rate']:.0%}",
            'effect': f"{classic['false_fame_effect']:.0%}"
        },
        'attention': {
            cond: f"effect: {data['false_fame_effect']:.0%}"
            for cond, data in attention.items()
        },
        'delay': {
            cond: f"false fame: {data['false_fame_rate']:.0%}"
            for cond, data in delay.items()
        },
        'aging': {
            age: f"false fame: {data['false_fame_rate']:.0%}"
            for age, data in aging.items()
        },
        'interpretation': (
            f"False fame effect: {classic['false_fame_effect']:.0%}. "
            f"Prior exposure creates familiarity misattributed to fame."
        )
    }


def get_false_fame_facts() -> Dict[str, str]:
    """Get facts about false fame effect."""
    return {
        'jacoby_1989': 'Original false fame experiment',
        'mechanism': 'Familiarity without source recollection',
        'source_monitoring': 'Failure to attribute familiarity correctly',
        'attention': 'Divided attention at test increases effect',
        'delay': 'Larger effect after 24h delay',
        'aging': 'Older adults more susceptible',
        'fluency': 'Processing fluency contributes',
        'real_world': 'May contribute to celebrity recognition errors'
    }
