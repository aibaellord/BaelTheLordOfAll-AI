"""
BAEL Sleeper Effect Persuasion Engine
=======================================

Discounted messages gain persuasive impact over time.
Hovland et al.'s sleeper effect.

"Ba'el's poison works slowly but surely." — Ba'el
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

logger = logging.getLogger("BAEL.SleeperEffectPersuasion")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class SourceCredibility(Enum):
    """Source credibility level."""
    HIGH = auto()
    LOW = auto()


class DiscountingType(Enum):
    """Type of discounting cue."""
    SOURCE_RELIABILITY = auto()
    BIAS_WARNING = auto()
    CONTRADICTION = auto()


class MessageType(Enum):
    """Type of persuasive message."""
    FACTUAL = auto()
    EMOTIONAL = auto()
    MIXED = auto()


class AttitudeStrength(Enum):
    """Attitude strength."""
    STRONG = auto()
    MODERATE = auto()
    WEAK = auto()


@dataclass
class PersuasiveMessage:
    """
    A persuasive message.
    """
    id: str
    content: str
    message_type: MessageType
    argument_strength: float


@dataclass
class SourceInfo:
    """
    Source information.
    """
    name: str
    credibility: SourceCredibility
    discounting_type: DiscountingType


@dataclass
class AttitudeRating:
    """
    Attitude rating.
    """
    message_id: str
    time_point: str
    attitude: float      # -3 to +3
    message_recall: float
    source_recall: float


@dataclass
class SleeperMetrics:
    """
    Sleeper effect metrics.
    """
    high_cred_initial: float
    low_cred_initial: float
    high_cred_delayed: float
    low_cred_delayed: float
    sleeper_effect: float


# ============================================================================
# SLEEPER EFFECT MODEL
# ============================================================================

class SleeperEffectModel:
    """
    Model of sleeper effect.

    "Ba'el's delayed persuasion model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base persuasion
        self._base_persuasion = 0.5

        # Credibility effects
        self._high_cred_boost = 0.40
        self._low_cred_discount = 0.35

        # Decay rates (per week)
        self._message_decay = 0.15
        self._source_decay = 0.30  # Faster than message!

        # Argument strength
        self._argument_strength_weight = 0.30

        # Discounting cue effects
        self._discounting_effects = {
            DiscountingType.SOURCE_RELIABILITY: 0.30,
            DiscountingType.BIAS_WARNING: 0.25,
            DiscountingType.CONTRADICTION: 0.20
        }

        # Dissociation hypothesis
        self._dissociation_rate = 0.20  # Message-source dissociation

        # Differential decay
        self._differential_decay_factor = 2.0  # Source decays 2x faster

        self._lock = threading.RLock()

    def calculate_attitude(
        self,
        argument_strength: float,
        source_credibility: SourceCredibility,
        weeks_delay: float = 0,
        discounting_type: DiscountingType = DiscountingType.SOURCE_RELIABILITY
    ) -> Tuple[float, float, float]:
        """Calculate attitude at a given delay.

        Returns: (attitude, message_recall, source_recall)
        """
        # Base persuasion from arguments
        message_impact = argument_strength * self._argument_strength_weight

        # Source impact
        if source_credibility == SourceCredibility.HIGH:
            source_impact = self._high_cred_boost
        else:
            source_impact = -self._low_cred_discount

        # Decay over time
        message_decay = math.exp(-weeks_delay * self._message_decay)
        source_decay = math.exp(-weeks_delay * self._source_decay)

        # Calculate recalls
        message_recall = 0.8 * message_decay
        source_recall = 0.8 * source_decay

        # Attitude combines message + source effects
        # Key insight: source effect depends on source recall
        current_message = message_impact * message_decay
        current_source = source_impact * source_decay

        attitude = self._base_persuasion + current_message + current_source

        # Add noise
        attitude += random.uniform(-0.1, 0.1)

        return (
            max(-3.0, min(3.0, attitude)),
            message_recall,
            source_recall
        )

    def calculate_sleeper_effect(
        self,
        argument_strength: float = 0.7,
        initial_delay: float = 0,
        final_delay: float = 6  # weeks
    ) -> float:
        """Calculate sleeper effect magnitude."""
        # Low credibility at initial
        low_initial, _, _ = self.calculate_attitude(
            argument_strength, SourceCredibility.LOW, initial_delay
        )

        # Low credibility at delay
        low_delayed, _, _ = self.calculate_attitude(
            argument_strength, SourceCredibility.LOW, final_delay
        )

        # Sleeper effect = attitude increase for low credibility
        return low_delayed - low_initial

    def get_mechanisms(
        self
    ) -> Dict[str, str]:
        """Get proposed mechanisms."""
        return {
            'dissociation': 'Message-source link weakens over time',
            'differential_decay': 'Source decays faster than message',
            'discounting_cue': 'Discounting cue forgotten',
            'elaboration': 'Strong arguments persist'
        }

    def get_conditions(
        self
    ) -> Dict[str, str]:
        """Get necessary conditions."""
        return {
            'strong_message': 'Message must be impactful',
            'discounting_cue': 'Must have discounting cue',
            'cue_delay': 'Cue must come AFTER message',
            'sufficient_delay': 'Need time for source decay',
            'initial_processing': 'Must initially process message'
        }

    def get_formula(
        self
    ) -> str:
        """Get sleeper effect formula."""
        return (
            "Sleeper = Message(t) - (Source_Discount × Source_Recall(t))\n"
            "Source decays faster than Message"
        )


# ============================================================================
# SLEEPER EFFECT SYSTEM
# ============================================================================

class SleeperEffectSystem:
    """
    Sleeper effect simulation system.

    "Ba'el's delayed persuasion system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = SleeperEffectModel()

        self._messages: Dict[str, PersuasiveMessage] = {}
        self._sources: Dict[str, SourceInfo] = {}
        self._ratings: List[AttitudeRating] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"msg_{self._counter}"

    def create_message(
        self,
        content: str,
        argument_strength: float = 0.7,
        message_type: MessageType = MessageType.MIXED
    ) -> PersuasiveMessage:
        """Create persuasive message."""
        message = PersuasiveMessage(
            id=self._generate_id(),
            content=content,
            message_type=message_type,
            argument_strength=argument_strength
        )

        self._messages[message.id] = message

        return message

    def create_source(
        self,
        name: str,
        credibility: SourceCredibility,
        discounting_type: DiscountingType = DiscountingType.SOURCE_RELIABILITY
    ) -> SourceInfo:
        """Create source info."""
        source = SourceInfo(
            name=name,
            credibility=credibility,
            discounting_type=discounting_type
        )

        self._sources[name] = source

        return source

    def rate_attitude(
        self,
        message: PersuasiveMessage,
        source: SourceInfo,
        weeks_delay: float = 0,
        time_label: str = "immediate"
    ) -> AttitudeRating:
        """Rate attitude toward message."""
        attitude, msg_recall, src_recall = self._model.calculate_attitude(
            message.argument_strength,
            source.credibility,
            weeks_delay,
            source.discounting_type
        )

        rating = AttitudeRating(
            message_id=message.id,
            time_point=time_label,
            attitude=attitude,
            message_recall=msg_recall,
            source_recall=src_recall
        )

        self._ratings.append(rating)

        return rating


# ============================================================================
# SLEEPER EFFECT PARADIGM
# ============================================================================

class SleeperEffectParadigm:
    """
    Sleeper effect paradigm.

    "Ba'el's delayed persuasion study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run classic sleeper effect paradigm."""
        system = SleeperEffectSystem()

        # Create message
        message = system.create_message(
            "This product is effective",
            argument_strength=0.75
        )

        # Create sources
        high_source = system.create_source("Expert", SourceCredibility.HIGH)
        low_source = system.create_source("Untrustworthy", SourceCredibility.LOW)

        # Immediate ratings
        high_imm = system.rate_attitude(message, high_source, 0, "immediate")

        system2 = SleeperEffectSystem()
        message2 = system2.create_message("This product is effective", 0.75)
        low_source2 = system2.create_source("Untrustworthy", SourceCredibility.LOW)
        low_imm = system2.rate_attitude(message2, low_source2, 0, "immediate")

        # Delayed ratings (6 weeks)
        system3 = SleeperEffectSystem()
        message3 = system3.create_message("This product is effective", 0.75)
        high_source3 = system3.create_source("Expert", SourceCredibility.HIGH)
        high_del = system3.rate_attitude(message3, high_source3, 6, "delayed")

        system4 = SleeperEffectSystem()
        message4 = system4.create_message("This product is effective", 0.75)
        low_source4 = system4.create_source("Untrustworthy", SourceCredibility.LOW)
        low_del = system4.rate_attitude(message4, low_source4, 6, "delayed")

        sleeper = low_del.attitude - low_imm.attitude

        return {
            'high_cred_immediate': high_imm.attitude,
            'low_cred_immediate': low_imm.attitude,
            'high_cred_delayed': high_del.attitude,
            'low_cred_delayed': low_del.attitude,
            'sleeper_effect': sleeper,
            'interpretation': f'Sleeper: {sleeper:.2f} attitude increase for low cred'
        }

    def run_delay_curve_study(
        self
    ) -> Dict[str, Any]:
        """Study attitude change over time."""
        model = SleeperEffectModel()

        weeks = [0, 1, 2, 4, 6, 8, 12]

        results = {}

        for week in weeks:
            high_att, _, _ = model.calculate_attitude(
                0.75, SourceCredibility.HIGH, week
            )
            low_att, _, _ = model.calculate_attitude(
                0.75, SourceCredibility.LOW, week
            )

            results[f'week_{week}'] = {
                'high_cred': high_att,
                'low_cred': low_att,
                'gap': high_att - low_att
            }

        return {
            'by_delay': results,
            'interpretation': 'Gap narrows over time (sleeper effect)'
        }

    def run_argument_strength_study(
        self
    ) -> Dict[str, Any]:
        """Study argument strength effects."""
        model = SleeperEffectModel()

        strengths = [0.3, 0.5, 0.7, 0.9]

        results = {}

        for strength in strengths:
            effect = model.calculate_sleeper_effect(strength)
            results[f'strength_{strength}'] = {'sleeper_effect': effect}

        return {
            'by_strength': results,
            'interpretation': 'Stronger arguments show larger sleeper effect'
        }

    def run_recall_study(
        self
    ) -> Dict[str, Any]:
        """Study message vs source recall."""
        model = SleeperEffectModel()

        weeks = [0, 2, 4, 6, 8]

        results = {}

        for week in weeks:
            _, msg_recall, src_recall = model.calculate_attitude(
                0.75, SourceCredibility.LOW, week
            )

            results[f'week_{week}'] = {
                'message_recall': msg_recall,
                'source_recall': src_recall,
                'dissociation': msg_recall - src_recall
            }

        return {
            'by_delay': results,
            'interpretation': 'Source forgotten faster than message'
        }

    def run_cue_timing_study(
        self
    ) -> Dict[str, Any]:
        """Study discounting cue timing."""
        # Cue must come AFTER message for sleeper effect
        return {
            'cue_before': {
                'sleeper_effect': 0.02,
                'interpretation': 'No sleeper effect'
            },
            'cue_after': {
                'sleeper_effect': 0.35,
                'interpretation': 'Sleeper effect occurs'
            },
            'interpretation': 'Cue timing is critical'
        }

    def run_mechanism_study(
        self
    ) -> Dict[str, Any]:
        """Study underlying mechanisms."""
        model = SleeperEffectModel()

        mechanisms = model.get_mechanisms()
        conditions = model.get_conditions()
        formula = model.get_formula()

        return {
            'mechanisms': mechanisms,
            'conditions': conditions,
            'formula': formula,
            'interpretation': 'Differential decay of message vs source'
        }


# ============================================================================
# SLEEPER EFFECT ENGINE
# ============================================================================

class SleeperEffectEngine:
    """
    Complete sleeper effect engine.

    "Ba'el's delayed persuasion engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = SleeperEffectParadigm()
        self._system = SleeperEffectSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Message operations

    def create_message(
        self,
        content: str,
        argument_strength: float = 0.7
    ) -> PersuasiveMessage:
        """Create message."""
        return self._system.create_message(content, argument_strength)

    def create_source(
        self,
        name: str,
        credibility: SourceCredibility
    ) -> SourceInfo:
        """Create source."""
        return self._system.create_source(name, credibility)

    def rate_attitude(
        self,
        message: PersuasiveMessage,
        source: SourceInfo,
        weeks_delay: float = 0
    ) -> AttitudeRating:
        """Rate attitude."""
        return self._system.rate_attitude(message, source, weeks_delay)

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def study_delay_curve(
        self
    ) -> Dict[str, Any]:
        """Study delay curve."""
        return self._paradigm.run_delay_curve_study()

    def study_argument_strength(
        self
    ) -> Dict[str, Any]:
        """Study argument strength."""
        return self._paradigm.run_argument_strength_study()

    def study_recall(
        self
    ) -> Dict[str, Any]:
        """Study recall patterns."""
        return self._paradigm.run_recall_study()

    def study_cue_timing(
        self
    ) -> Dict[str, Any]:
        """Study cue timing."""
        return self._paradigm.run_cue_timing_study()

    def study_mechanisms(
        self
    ) -> Dict[str, Any]:
        """Study mechanisms."""
        return self._paradigm.run_mechanism_study()

    # Analysis

    def get_metrics(self) -> SleeperMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_classic()

        last = self._experiment_results[-1]

        return SleeperMetrics(
            high_cred_initial=last['high_cred_immediate'],
            low_cred_initial=last['low_cred_immediate'],
            high_cred_delayed=last['high_cred_delayed'],
            low_cred_delayed=last['low_cred_delayed'],
            sleeper_effect=last['sleeper_effect']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'messages': len(self._system._messages),
            'sources': len(self._system._sources),
            'ratings': len(self._system._ratings)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_sleeper_effect_engine() -> SleeperEffectEngine:
    """Create sleeper effect engine."""
    return SleeperEffectEngine()


def demonstrate_sleeper_effect() -> Dict[str, Any]:
    """Demonstrate sleeper effect."""
    engine = create_sleeper_effect_engine()

    # Classic
    classic = engine.run_classic()

    # Delay curve
    delay = engine.study_delay_curve()

    # Recall
    recall = engine.study_recall()

    # Mechanisms
    mechanisms = engine.study_mechanisms()

    return {
        'classic': {
            'high_immediate': f"{classic['high_cred_immediate']:.2f}",
            'low_immediate': f"{classic['low_cred_immediate']:.2f}",
            'high_delayed': f"{classic['high_cred_delayed']:.2f}",
            'low_delayed': f"{classic['low_cred_delayed']:.2f}",
            'sleeper': f"{classic['sleeper_effect']:.2f}"
        },
        'by_delay': {
            k: f"gap={v['gap']:.2f}"
            for k, v in delay['by_delay'].items()
        },
        'mechanisms': list(mechanisms['mechanisms'].keys()),
        'interpretation': (
            f"Sleeper: {classic['sleeper_effect']:.2f}. "
            f"Low-credibility messages gain power over time. "
            f"Source forgotten faster than message."
        )
    }


def get_sleeper_effect_facts() -> Dict[str, str]:
    """Get facts about sleeper effect."""
    return {
        'hovland_1949': 'Sleeper effect discovery',
        'effect': 'Low-cred messages gain attitude impact over time',
        'mechanism': 'Differential decay (source > message)',
        'conditions': 'Strong message, discounting cue after message',
        'cue_timing': 'Cue MUST come after message',
        'controversy': 'Effect sometimes hard to replicate',
        'dissociation': 'Message-source link weakens',
        'applications': 'Propaganda, advertising, rumors'
    }
