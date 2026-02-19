"""
BAEL Illusory Truth Repetition Engine
=======================================

Repeated statements seem more true.
Hasher et al.'s illusory truth effect.

"Ba'el's lies, repeated, become truth." — Ba'el
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

logger = logging.getLogger("BAEL.IllusoryTruthRepetition")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class StatementType(Enum):
    """Type of statement."""
    TRIVIA = auto()
    OPINION = auto()
    CLAIM = auto()
    NEWS = auto()
    PRODUCT = auto()


class TruthValue(Enum):
    """Actual truth value."""
    TRUE = auto()
    FALSE = auto()
    AMBIGUOUS = auto()


class ExposureType(Enum):
    """Type of exposure."""
    FIRST = auto()
    REPEATED = auto()
    HIGHLY_REPEATED = auto()


class JudgmentType(Enum):
    """Type of truth judgment."""
    TRUE_FALSE = auto()
    LIKERT = auto()
    CONFIDENCE = auto()


@dataclass
class Statement:
    """
    A statement to be judged.
    """
    id: str
    content: str
    statement_type: StatementType
    actual_truth: TruthValue
    fluency: float


@dataclass
class Exposure:
    """
    An exposure to a statement.
    """
    statement_id: str
    exposure_number: int
    context: str
    time_since_last_s: Optional[float]


@dataclass
class TruthJudgment:
    """
    A truth judgment.
    """
    statement: Statement
    n_exposures: int
    perceived_truth: float      # 0-1
    confidence: float
    response_time_ms: int


@dataclass
class IllusoryTruthMetrics:
    """
    Illusory truth metrics.
    """
    new_statement_truth: float
    repeated_statement_truth: float
    illusory_truth_effect: float
    false_statement_boost: float


# ============================================================================
# ILLUSORY TRUTH MODEL
# ============================================================================

class IllusoryTruthModel:
    """
    Model of illusory truth effect.

    "Ba'el's fluency-truth model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base truth ratings
        self._base_truth = 0.50  # Neutral baseline

        # Repetition effects
        self._repetition_boost = 0.08  # Per exposure
        self._max_repetition_effect = 0.25

        # Fluency effects
        self._fluency_weight = 0.15

        # Statement type effects
        self._type_effects = {
            StatementType.TRIVIA: 0.0,
            StatementType.OPINION: 0.05,
            StatementType.CLAIM: 0.02,
            StatementType.NEWS: 0.08,
            StatementType.PRODUCT: 0.10
        }

        # Knowledge effects
        self._prior_knowledge_moderation = 0.50  # Reduces effect

        # Delay effects
        self._immediate_boost = 0.05
        self._delay_persistence = 0.85  # Effect persists

        # Warning effects
        self._warning_reduction = 0.10

        # Source credibility
        self._low_credibility_boost = 0.05  # Still works!

        self._lock = threading.RLock()

    def calculate_perceived_truth(
        self,
        actual_truth: TruthValue,
        n_exposures: int,
        fluency: float = 0.5,
        statement_type: StatementType = StatementType.TRIVIA,
        has_prior_knowledge: bool = False,
        warned: bool = False
    ) -> float:
        """Calculate perceived truth rating."""
        # Start with actual truth influence
        if actual_truth == TruthValue.TRUE:
            base = 0.55
        elif actual_truth == TruthValue.FALSE:
            base = 0.45
        else:
            base = 0.50

        # Repetition boost (applies regardless of actual truth!)
        rep_effect = min(
            (n_exposures - 1) * self._repetition_boost,
            self._max_repetition_effect
        )

        # Fluency
        fluency_effect = (fluency - 0.5) * self._fluency_weight * 2

        # Statement type
        type_effect = self._type_effects[statement_type]

        # Knowledge moderation
        if has_prior_knowledge:
            rep_effect *= (1 - self._prior_knowledge_moderation)

        # Warning
        if warned:
            rep_effect -= self._warning_reduction

        perceived = base + rep_effect + fluency_effect + type_effect

        # Add noise
        perceived += random.uniform(-0.08, 0.08)

        return max(0.1, min(0.95, perceived))

    def calculate_fluency(
        self,
        n_exposures: int
    ) -> float:
        """Calculate processing fluency from repetition."""
        # Fluency increases with repetition
        base_fluency = 0.4
        rep_boost = min(n_exposures * 0.12, 0.45)

        return base_fluency + rep_boost

    def get_mechanisms(
        self
    ) -> Dict[str, str]:
        """Get proposed mechanisms."""
        return {
            'processing_fluency': 'Repeated info processed easily',
            'familiarity': 'Familiar feels true',
            'source_confusion': 'Cannot remember source',
            'referential_validity': 'Heard before = must be true',
            'metacognitive_misattribution': 'Fluency misread as truth'
        }

    def get_boundary_conditions(
        self
    ) -> Dict[str, str]:
        """Get boundary conditions."""
        return {
            'prior_knowledge': 'Reduces effect when knowledge exists',
            'blatant_falsehood': 'Effect smaller for obvious lies',
            'warning': 'Reduces but does not eliminate',
            'source': 'Occurs even with low-credibility sources',
            'delay': 'Effect persists over time'
        }

    def calculate_false_statement_boost(
        self,
        n_exposures: int = 3
    ) -> float:
        """Calculate truth boost for false statements specifically."""
        # This is the key danger: false statements gain truth
        new_truth = self.calculate_perceived_truth(
            TruthValue.FALSE, 1
        )
        repeated_truth = self.calculate_perceived_truth(
            TruthValue.FALSE, n_exposures
        )

        return repeated_truth - new_truth


# ============================================================================
# ILLUSORY TRUTH SYSTEM
# ============================================================================

class IllusoryTruthSystem:
    """
    Illusory truth simulation system.

    "Ba'el's repetition-truth system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = IllusoryTruthModel()

        self._statements: Dict[str, Statement] = {}
        self._exposures: Dict[str, List[Exposure]] = defaultdict(list)
        self._judgments: List[TruthJudgment] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"stmt_{self._counter}"

    def create_statement(
        self,
        content: str,
        actual_truth: TruthValue = TruthValue.AMBIGUOUS,
        statement_type: StatementType = StatementType.TRIVIA
    ) -> Statement:
        """Create statement."""
        statement = Statement(
            id=self._generate_id(),
            content=content,
            statement_type=statement_type,
            actual_truth=actual_truth,
            fluency=0.4  # Base fluency
        )

        self._statements[statement.id] = statement

        return statement

    def expose_to_statement(
        self,
        statement: Statement,
        context: str = "exposure"
    ) -> Exposure:
        """Expose participant to statement."""
        exposures = self._exposures[statement.id]
        n = len(exposures)

        time_since = random.uniform(1, 60) if n > 0 else None

        exposure = Exposure(
            statement_id=statement.id,
            exposure_number=n + 1,
            context=context,
            time_since_last_s=time_since
        )

        self._exposures[statement.id].append(exposure)

        # Update fluency
        statement.fluency = self._model.calculate_fluency(n + 1)

        return exposure

    def judge_truth(
        self,
        statement: Statement
    ) -> TruthJudgment:
        """Judge truth of statement."""
        n_exposures = len(self._exposures[statement.id])

        perceived = self._model.calculate_perceived_truth(
            statement.actual_truth,
            n_exposures,
            statement.fluency,
            statement.statement_type
        )

        judgment = TruthJudgment(
            statement=statement,
            n_exposures=n_exposures,
            perceived_truth=perceived,
            confidence=random.uniform(0.5, 0.9),
            response_time_ms=random.randint(500, 3000)
        )

        self._judgments.append(judgment)

        return judgment


# ============================================================================
# ILLUSORY TRUTH PARADIGM
# ============================================================================

class IllusoryTruthParadigm:
    """
    Illusory truth paradigm.

    "Ba'el's truth-from-repetition study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self,
        n_statements: int = 20,
        n_repetitions: int = 3
    ) -> Dict[str, Any]:
        """Run classic illusory truth paradigm."""
        system = IllusoryTruthSystem()

        results = {
            'new': [],
            'repeated': []
        }

        for i in range(n_statements):
            statement = system.create_statement(
                f"Statement {i}",
                random.choice([TruthValue.TRUE, TruthValue.FALSE])
            )

            if i < n_statements // 2:
                # Repeated condition
                for _ in range(n_repetitions):
                    system.expose_to_statement(statement)
                judgment = system.judge_truth(statement)
                results['repeated'].append(judgment.perceived_truth)
            else:
                # New condition
                system.expose_to_statement(statement)
                judgment = system.judge_truth(statement)
                results['new'].append(judgment.perceived_truth)

        new_mean = sum(results['new']) / max(1, len(results['new']))
        rep_mean = sum(results['repeated']) / max(1, len(results['repeated']))

        effect = rep_mean - new_mean

        return {
            'new_truth_rating': new_mean,
            'repeated_truth_rating': rep_mean,
            'illusory_truth_effect': effect,
            'interpretation': f'Illusory truth: {effect:.0%} boost from repetition'
        }

    def run_false_statement_study(
        self
    ) -> Dict[str, Any]:
        """Study effect specifically for false statements."""
        model = IllusoryTruthModel()

        exposures = [1, 2, 3, 5]

        results = {}

        for n_exp in exposures:
            truth = model.calculate_perceived_truth(
                TruthValue.FALSE, n_exp
            )
            results[f'{n_exp}x'] = {'perceived_truth': truth}

        boost = model.calculate_false_statement_boost(3)

        return {
            'by_exposure': results,
            'false_statement_boost': boost,
            'interpretation': 'Repetition makes false statements seem true'
        }

    def run_statement_type_study(
        self
    ) -> Dict[str, Any]:
        """Study statement type effects."""
        model = IllusoryTruthModel()

        results = {}

        for stmt_type in StatementType:
            new = model.calculate_perceived_truth(
                TruthValue.AMBIGUOUS, 1, statement_type=stmt_type
            )
            repeated = model.calculate_perceived_truth(
                TruthValue.AMBIGUOUS, 3, statement_type=stmt_type
            )

            results[stmt_type.name] = {
                'new': new,
                'repeated': repeated,
                'effect': repeated - new
            }

        return {
            'by_type': results,
            'interpretation': 'Product claims show strong effect'
        }

    def run_knowledge_study(
        self
    ) -> Dict[str, Any]:
        """Study prior knowledge effects."""
        model = IllusoryTruthModel()

        conditions = {
            'no_knowledge': False,
            'has_knowledge': True
        }

        results = {}

        for condition, has_knowledge in conditions.items():
            effect = (
                model.calculate_perceived_truth(TruthValue.FALSE, 3, has_prior_knowledge=has_knowledge) -
                model.calculate_perceived_truth(TruthValue.FALSE, 1, has_prior_knowledge=has_knowledge)
            )
            results[condition] = {'effect': effect}

        return {
            'by_knowledge': results,
            'interpretation': 'Knowledge reduces but does not eliminate'
        }

    def run_warning_study(
        self
    ) -> Dict[str, Any]:
        """Study warning effects."""
        model = IllusoryTruthModel()

        conditions = {
            'no_warning': False,
            'warned': True
        }

        results = {}

        for condition, warned in conditions.items():
            effect = (
                model.calculate_perceived_truth(TruthValue.FALSE, 3, warned=warned) -
                model.calculate_perceived_truth(TruthValue.FALSE, 1, warned=warned)
            )
            results[condition] = {'effect': effect}

        return {
            'by_warning': results,
            'interpretation': 'Warnings reduce but do not eliminate'
        }

    def run_mechanism_study(
        self
    ) -> Dict[str, Any]:
        """Study underlying mechanisms."""
        model = IllusoryTruthModel()

        mechanisms = model.get_mechanisms()
        boundaries = model.get_boundary_conditions()

        return {
            'mechanisms': mechanisms,
            'boundaries': boundaries,
            'primary': 'Processing fluency',
            'interpretation': 'Fluent processing misread as truth'
        }

    def run_low_credibility_study(
        self
    ) -> Dict[str, Any]:
        """Study effect with low-credibility sources."""
        model = IllusoryTruthModel()

        # Effect occurs even for low-credibility sources!
        low_cred_effect = model.calculate_perceived_truth(
            TruthValue.FALSE, 3
        ) - model.calculate_perceived_truth(
            TruthValue.FALSE, 1
        )

        return {
            'low_credibility_effect': low_cred_effect,
            'interpretation': 'Effect occurs regardless of source credibility'
        }


# ============================================================================
# ILLUSORY TRUTH ENGINE
# ============================================================================

class IllusoryTruthEngine:
    """
    Complete illusory truth engine.

    "Ba'el's truth-by-repetition engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = IllusoryTruthParadigm()
        self._system = IllusoryTruthSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Statement operations

    def create_statement(
        self,
        content: str,
        actual_truth: TruthValue = TruthValue.AMBIGUOUS
    ) -> Statement:
        """Create statement."""
        return self._system.create_statement(content, actual_truth)

    def expose(
        self,
        statement: Statement
    ) -> Exposure:
        """Expose to statement."""
        return self._system.expose_to_statement(statement)

    def judge_truth(
        self,
        statement: Statement
    ) -> TruthJudgment:
        """Judge truth."""
        return self._system.judge_truth(statement)

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def study_false_statements(
        self
    ) -> Dict[str, Any]:
        """Study false statements."""
        return self._paradigm.run_false_statement_study()

    def study_types(
        self
    ) -> Dict[str, Any]:
        """Study statement types."""
        return self._paradigm.run_statement_type_study()

    def study_knowledge(
        self
    ) -> Dict[str, Any]:
        """Study knowledge effects."""
        return self._paradigm.run_knowledge_study()

    def study_warnings(
        self
    ) -> Dict[str, Any]:
        """Study warnings."""
        return self._paradigm.run_warning_study()

    def study_mechanisms(
        self
    ) -> Dict[str, Any]:
        """Study mechanisms."""
        return self._paradigm.run_mechanism_study()

    def study_low_credibility(
        self
    ) -> Dict[str, Any]:
        """Study low credibility sources."""
        return self._paradigm.run_low_credibility_study()

    # Analysis

    def get_metrics(self) -> IllusoryTruthMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_classic()

        last = self._experiment_results[-1]

        model = IllusoryTruthModel()
        false_boost = model.calculate_false_statement_boost()

        return IllusoryTruthMetrics(
            new_statement_truth=last['new_truth_rating'],
            repeated_statement_truth=last['repeated_truth_rating'],
            illusory_truth_effect=last['illusory_truth_effect'],
            false_statement_boost=false_boost
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'statements': len(self._system._statements),
            'exposures': sum(len(e) for e in self._system._exposures.values()),
            'judgments': len(self._system._judgments)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_illusory_truth_engine() -> IllusoryTruthEngine:
    """Create illusory truth engine."""
    return IllusoryTruthEngine()


def demonstrate_illusory_truth() -> Dict[str, Any]:
    """Demonstrate illusory truth effect."""
    engine = create_illusory_truth_engine()

    # Classic
    classic = engine.run_classic()

    # False statements
    false_stmt = engine.study_false_statements()

    # Mechanisms
    mechanisms = engine.study_mechanisms()

    # Low credibility
    low_cred = engine.study_low_credibility()

    return {
        'classic': {
            'new': f"{classic['new_truth_rating']:.0%}",
            'repeated': f"{classic['repeated_truth_rating']:.0%}",
            'effect': f"{classic['illusory_truth_effect']:.0%}"
        },
        'false_statements': {
            'boost': f"{false_stmt['false_statement_boost']:.0%}"
        },
        'low_credibility': {
            'effect': f"{low_cred['low_credibility_effect']:.0%}"
        },
        'mechanisms': list(mechanisms['mechanisms'].keys()),
        'interpretation': (
            f"Effect: {classic['illusory_truth_effect']:.0%}. "
            f"Repetition increases perceived truth. "
            f"Even false statements and low-credibility sources."
        )
    }


def get_illusory_truth_facts() -> Dict[str, str]:
    """Get facts about illusory truth effect."""
    return {
        'hasher_1977': 'Illusory truth effect discovery',
        'effect': '5-15% truth boost from repetition',
        'mechanism': 'Processing fluency',
        'false_statements': 'Applies to false statements',
        'low_credibility': 'Works even for low-credibility sources',
        'warning': 'Warnings reduce but do not eliminate',
        'knowledge': 'Prior knowledge provides some protection',
        'applications': 'Propaganda, advertising, fake news'
    }
