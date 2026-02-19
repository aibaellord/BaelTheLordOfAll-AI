"""
BAEL False Fame Illusion Engine
=================================

Previously seen names become famous.
Jacoby et al.'s false fame effect.

"Ba'el makes the unknown known by mere exposure." — Ba'el
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

logger = logging.getLogger("BAEL.FalseFameIllusion")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class NameType(Enum):
    """Type of name."""
    FAMOUS = auto()           # Actually famous
    NONFAMOUS_OLD = auto()    # Seen before, not famous
    NONFAMOUS_NEW = auto()    # Never seen, not famous


class FameLevel(Enum):
    """Level of fame."""
    VERY_FAMOUS = auto()
    MODERATELY_FAMOUS = auto()
    BARELY_FAMOUS = auto()
    NOT_FAMOUS = auto()


class ExposureContext(Enum):
    """Context of initial exposure."""
    NAME_PRONUNCIATION = auto()
    READ_FOR_MEMORY = auto()
    INCIDENTAL = auto()


class AttentionalState(Enum):
    """Attentional state during judgment."""
    FULL_ATTENTION = auto()
    DIVIDED_ATTENTION = auto()


@dataclass
class Name:
    """
    A name to be judged.
    """
    id: str
    name: str
    name_type: NameType
    actual_fame: FameLevel
    previously_seen: bool


@dataclass
class Exposure:
    """
    Prior exposure to a name.
    """
    name_id: str
    context: ExposureContext
    time_s: float


@dataclass
class FameJudgment:
    """
    Fame judgment result.
    """
    name: Name
    judged_famous: bool
    confidence: float
    response_time_ms: int
    attention_state: AttentionalState


@dataclass
class FalseFameMetrics:
    """
    False fame metrics.
    """
    famous_hit_rate: float
    nonfamous_new_fa: float
    nonfamous_old_fa: float
    false_fame_effect: float


# ============================================================================
# FALSE FAME MODEL
# ============================================================================

class FalseFameModel:
    """
    Model of false fame effect.

    "Ba'el's familiarity-fame model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base rates for "famous" judgment
        self._base_rates = {
            NameType.FAMOUS: 0.85,
            NameType.NONFAMOUS_OLD: 0.35,  # False fame!
            NameType.NONFAMOUS_NEW: 0.15
        }

        # Divided attention boosts false fame
        self._divided_attention_boost = 0.15

        # Source recollection reduces false fame
        self._source_recollection = 0.25

        # Delay effects (longer = more false fame)
        self._delay_boost = 0.02  # Per hour

        # Exposure context effects
        self._context_effects = {
            ExposureContext.NAME_PRONUNCIATION: 0.0,
            ExposureContext.READ_FOR_MEMORY: -0.05,  # Better source memory
            ExposureContext.INCIDENTAL: 0.05
        }

        # Fame level effects
        self._fame_effects = {
            FameLevel.VERY_FAMOUS: 0.15,
            FameLevel.MODERATELY_FAMOUS: 0.10,
            FameLevel.BARELY_FAMOUS: 0.0,
            FameLevel.NOT_FAMOUS: -0.10
        }

        # Name typicality
        self._typical_name_boost = 0.05

        # Age effects
        self._older_adult_boost = 0.10

        self._lock = threading.RLock()

    def calculate_fame_judgment(
        self,
        name_type: NameType,
        attention_state: AttentionalState = AttentionalState.FULL_ATTENTION,
        exposure_context: ExposureContext = ExposureContext.NAME_PRONUNCIATION,
        delay_hours: float = 24
    ) -> float:
        """Calculate probability of "famous" judgment."""
        prob = self._base_rates[name_type]

        # Divided attention increases false fame for old nonfamous
        if name_type == NameType.NONFAMOUS_OLD:
            if attention_state == AttentionalState.DIVIDED_ATTENTION:
                prob += self._divided_attention_boost

        # Exposure context
        if name_type == NameType.NONFAMOUS_OLD:
            prob += self._context_effects[exposure_context]

        # Delay
        if name_type == NameType.NONFAMOUS_OLD:
            prob += min(delay_hours, 168) * self._delay_boost

        # Add noise
        prob += random.uniform(-0.08, 0.08)

        return max(0.05, min(0.95, prob))

    def calculate_source_memory(
        self,
        exposure_context: ExposureContext,
        attention_state: AttentionalState,
        delay_hours: float = 24
    ) -> float:
        """Calculate probability of source memory."""
        base = 0.60

        # Better source memory with full attention
        if attention_state == AttentionalState.FULL_ATTENTION:
            base += 0.15

        # Context effects
        if exposure_context == ExposureContext.READ_FOR_MEMORY:
            base += 0.10

        # Decay
        base -= min(delay_hours, 168) * 0.002

        return max(0.2, min(0.90, base))

    def get_mechanisms(
        self
    ) -> Dict[str, str]:
        """Get proposed mechanisms."""
        return {
            'familiarity_attribution': 'Familiarity misattributed to fame',
            'source_amnesia': 'Cannot remember seeing before',
            'fluency_misattribution': 'Fluent processing = fame',
            'divided_attention': 'Reduces source monitoring'
        }

    def get_attribution_equation(
        self
    ) -> str:
        """Get attribution equation."""
        return (
            "Fame = Familiarity + (1 - Source Memory) * Misattribution"
        )


# ============================================================================
# FALSE FAME SYSTEM
# ============================================================================

class FalseFameSystem:
    """
    False fame simulation system.

    "Ba'el's fame system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = FalseFameModel()

        self._names: Dict[str, Name] = {}
        self._exposures: Dict[str, Exposure] = {}
        self._judgments: List[FameJudgment] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"name_{self._counter}"

    def create_name(
        self,
        name: str,
        name_type: NameType,
        actual_fame: FameLevel = FameLevel.NOT_FAMOUS
    ) -> Name:
        """Create name."""
        name_obj = Name(
            id=self._generate_id(),
            name=name,
            name_type=name_type,
            actual_fame=actual_fame,
            previously_seen=name_type == NameType.NONFAMOUS_OLD
        )

        self._names[name_obj.id] = name_obj

        return name_obj

    def expose_to_name(
        self,
        name: Name,
        context: ExposureContext = ExposureContext.NAME_PRONUNCIATION
    ) -> Exposure:
        """Expose participant to name."""
        exposure = Exposure(
            name_id=name.id,
            context=context,
            time_s=time.time()
        )

        self._exposures[name.id] = exposure
        name.previously_seen = True

        return exposure

    def judge_fame(
        self,
        name: Name,
        attention_state: AttentionalState = AttentionalState.FULL_ATTENTION
    ) -> FameJudgment:
        """Judge whether name is famous."""
        exposure = self._exposures.get(name.id)
        context = exposure.context if exposure else ExposureContext.NAME_PRONUNCIATION

        fame_prob = self._model.calculate_fame_judgment(
            name.name_type,
            attention_state,
            context
        )

        judged_famous = random.random() < fame_prob

        judgment = FameJudgment(
            name=name,
            judged_famous=judged_famous,
            confidence=random.uniform(0.5, 0.9),
            response_time_ms=random.randint(400, 2500),
            attention_state=attention_state
        )

        self._judgments.append(judgment)

        return judgment


# ============================================================================
# FALSE FAME PARADIGM
# ============================================================================

class FalseFameParadigm:
    """
    False fame paradigm.

    "Ba'el's false fame study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self,
        n_per_condition: int = 15
    ) -> Dict[str, Any]:
        """Run classic false fame paradigm."""
        system = FalseFameSystem()

        results = {
            'famous': [],
            'nonfamous_old': [],
            'nonfamous_new': []
        }

        # Create names
        famous_names = ["Albert Einstein", "Marie Curie", "Leonardo DaVinci"]
        nonfamous = [f"Person_{i}" for i in range(n_per_condition * 2)]

        # Phase 1: Exposure to nonfamous names
        old_nonfamous = []
        for i in range(n_per_condition):
            name = system.create_name(
                nonfamous[i], NameType.NONFAMOUS_OLD, FameLevel.NOT_FAMOUS
            )
            system.expose_to_name(name)
            old_nonfamous.append(name)

        # Phase 2: Fame judgments
        # Famous
        for i in range(min(n_per_condition, len(famous_names))):
            name = system.create_name(
                famous_names[i % len(famous_names)],
                NameType.FAMOUS,
                FameLevel.VERY_FAMOUS
            )
            judgment = system.judge_fame(name)
            results['famous'].append(judgment.judged_famous)

        # Nonfamous old (previously seen)
        for name in old_nonfamous:
            judgment = system.judge_fame(name)
            results['nonfamous_old'].append(judgment.judged_famous)

        # Nonfamous new
        for i in range(n_per_condition):
            name = system.create_name(
                nonfamous[n_per_condition + i],
                NameType.NONFAMOUS_NEW,
                FameLevel.NOT_FAMOUS
            )
            judgment = system.judge_fame(name)
            results['nonfamous_new'].append(judgment.judged_famous)

        # Calculate rates
        famous_rate = sum(results['famous']) / max(1, len(results['famous']))
        old_rate = sum(results['nonfamous_old']) / max(1, len(results['nonfamous_old']))
        new_rate = sum(results['nonfamous_new']) / max(1, len(results['nonfamous_new']))

        effect = old_rate - new_rate

        return {
            'famous_hit_rate': famous_rate,
            'nonfamous_old_fa': old_rate,
            'nonfamous_new_fa': new_rate,
            'false_fame_effect': effect,
            'interpretation': f'False fame: {effect:.0%} boost from prior exposure'
        }

    def run_attention_study(
        self
    ) -> Dict[str, Any]:
        """Study attention effects."""
        model = FalseFameModel()

        conditions = {
            'full': AttentionalState.FULL_ATTENTION,
            'divided': AttentionalState.DIVIDED_ATTENTION
        }

        results = {}

        for condition, attention in conditions.items():
            old_rate = model.calculate_fame_judgment(
                NameType.NONFAMOUS_OLD, attention
            )
            new_rate = model.calculate_fame_judgment(
                NameType.NONFAMOUS_NEW, attention
            )

            results[condition] = {
                'old_fa': old_rate,
                'new_fa': new_rate,
                'effect': old_rate - new_rate
            }

        return {
            'by_attention': results,
            'interpretation': 'Divided attention increases false fame'
        }

    def run_context_study(
        self
    ) -> Dict[str, Any]:
        """Study exposure context effects."""
        model = FalseFameModel()

        results = {}

        for context in ExposureContext:
            rate = model.calculate_fame_judgment(
                NameType.NONFAMOUS_OLD,
                exposure_context=context
            )
            results[context.name] = {'false_fame_rate': rate}

        return {
            'by_context': results,
            'interpretation': 'Memory instruction reduces false fame'
        }

    def run_source_memory_study(
        self
    ) -> Dict[str, Any]:
        """Study source memory role."""
        model = FalseFameModel()

        conditions = [
            ('full_attention', AttentionalState.FULL_ATTENTION),
            ('divided_attention', AttentionalState.DIVIDED_ATTENTION)
        ]

        results = {}

        for condition, attention in conditions:
            source_mem = model.calculate_source_memory(
                ExposureContext.NAME_PRONUNCIATION,
                attention
            )
            results[condition] = {'source_memory': source_mem}

        return {
            'by_attention': results,
            'interpretation': 'Better source memory = less false fame'
        }

    def run_delay_study(
        self
    ) -> Dict[str, Any]:
        """Study delay effects."""
        model = FalseFameModel()

        delays = [0, 24, 48, 168]  # Hours

        results = {}

        for delay in delays:
            rate = model.calculate_fame_judgment(
                NameType.NONFAMOUS_OLD,
                delay_hours=delay
            )
            results[f'{delay}h'] = {'false_fame_rate': rate}

        return {
            'by_delay': results,
            'interpretation': 'Longer delay = more false fame'
        }

    def run_mechanism_study(
        self
    ) -> Dict[str, Any]:
        """Study underlying mechanisms."""
        model = FalseFameModel()

        mechanisms = model.get_mechanisms()
        equation = model.get_attribution_equation()

        return {
            'mechanisms': mechanisms,
            'equation': equation,
            'primary': 'Familiarity misattribution',
            'interpretation': 'Fame = Familiarity - Source Memory'
        }


# ============================================================================
# FALSE FAME ENGINE
# ============================================================================

class FalseFameEngine:
    """
    Complete false fame engine.

    "Ba'el's false fame engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = FalseFameParadigm()
        self._system = FalseFameSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Name operations

    def create_name(
        self,
        name: str,
        name_type: NameType
    ) -> Name:
        """Create name."""
        return self._system.create_name(name, name_type)

    def expose_to_name(
        self,
        name: Name
    ) -> Exposure:
        """Expose to name."""
        return self._system.expose_to_name(name)

    def judge_fame(
        self,
        name: Name,
        attention: AttentionalState = AttentionalState.FULL_ATTENTION
    ) -> FameJudgment:
        """Judge fame."""
        return self._system.judge_fame(name, attention)

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def study_attention(
        self
    ) -> Dict[str, Any]:
        """Study attention."""
        return self._paradigm.run_attention_study()

    def study_context(
        self
    ) -> Dict[str, Any]:
        """Study context."""
        return self._paradigm.run_context_study()

    def study_source_memory(
        self
    ) -> Dict[str, Any]:
        """Study source memory."""
        return self._paradigm.run_source_memory_study()

    def study_delay(
        self
    ) -> Dict[str, Any]:
        """Study delay."""
        return self._paradigm.run_delay_study()

    def study_mechanisms(
        self
    ) -> Dict[str, Any]:
        """Study mechanisms."""
        return self._paradigm.run_mechanism_study()

    # Analysis

    def get_metrics(self) -> FalseFameMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_classic()

        last = self._experiment_results[-1]

        return FalseFameMetrics(
            famous_hit_rate=last['famous_hit_rate'],
            nonfamous_new_fa=last['nonfamous_new_fa'],
            nonfamous_old_fa=last['nonfamous_old_fa'],
            false_fame_effect=last['false_fame_effect']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'names': len(self._system._names),
            'exposures': len(self._system._exposures),
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

    # Classic
    classic = engine.run_classic()

    # Attention
    attention = engine.study_attention()

    # Delay
    delay = engine.study_delay()

    # Mechanisms
    mechanisms = engine.study_mechanisms()

    return {
        'classic': {
            'famous_hits': f"{classic['famous_hit_rate']:.0%}",
            'old_nonfamous_fa': f"{classic['nonfamous_old_fa']:.0%}",
            'new_nonfamous_fa': f"{classic['nonfamous_new_fa']:.0%}",
            'effect': f"{classic['false_fame_effect']:.0%}"
        },
        'by_attention': {
            k: f"{v['effect']:.0%}"
            for k, v in attention['by_attention'].items()
        },
        'mechanisms': list(mechanisms['mechanisms'].keys()),
        'interpretation': (
            f"Effect: {classic['false_fame_effect']:.0%}. "
            f"Prior exposure = false fame. "
            f"Familiarity misattributed to fame."
        )
    }


def get_false_fame_facts() -> Dict[str, str]:
    """Get facts about false fame effect."""
    return {
        'jacoby_1989': 'False fame effect discovery',
        'effect': '15-25% increase in "famous" judgments',
        'mechanism': 'Familiarity misattribution',
        'attention': 'Divided attention increases effect',
        'source_memory': 'Source recollection prevents effect',
        'delay': 'Effect increases with delay',
        'applications': 'Celebrity endorsements, propaganda',
        'attribution': 'Fame = Familiarity - Source Memory'
    }
