"""
BAEL Fan Effect Associative Engine
====================================

More associations to a concept = slower retrieval.
Anderson's ACT model prediction.

"Ba'el's connections create cognitive friction." — Ba'el
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

logger = logging.getLogger("BAEL.FanEffectAssociative")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ConceptType(Enum):
    """Type of concept."""
    PERSON = auto()
    LOCATION = auto()
    OBJECT = auto()


class AssociationType(Enum):
    """Type of association."""
    PERSON_LOCATION = auto()
    PERSON_OBJECT = auto()
    LOCATION_OBJECT = auto()


class FanLevel(Enum):
    """Level of fan (number of associations)."""
    LOW = auto()     # 1-2
    MEDIUM = auto()  # 3-4
    HIGH = auto()    # 5+


class RetrievalType(Enum):
    """Type of retrieval."""
    VERIFICATION = auto()   # True/false
    PRODUCTION = auto()     # Generate associate


@dataclass
class Concept:
    """
    A concept node.
    """
    id: str
    name: str
    concept_type: ConceptType
    fan: int              # Number of associations


@dataclass
class Association:
    """
    An association between concepts.
    """
    id: str
    source: Concept
    target: Concept
    association_type: AssociationType
    strength: float


@dataclass
class RetrievalTrial:
    """
    A retrieval trial.
    """
    probe: Tuple[Concept, Concept]
    correct_response: bool
    response: bool
    rt_ms: int
    fan_level: FanLevel


@dataclass
class FanMetrics:
    """
    Fan effect metrics.
    """
    low_fan_rt: float
    high_fan_rt: float
    fan_effect_ms: float
    fan_slope: float


# ============================================================================
# FAN EFFECT MODEL
# ============================================================================

class FanEffectModel:
    """
    Model of fan effect.

    "Ba'el's associative interference model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base RT
        self._base_rt_ms = 1200

        # Fan effect (ms per additional association)
        self._fan_slope = 100  # ms per fan

        # Activation parameters (ACT-R style)
        self._base_level_activation = 1.0
        self._spreading_activation = 0.5

        # Source activation limited
        self._source_activation = 1.0

        # Fan divides activation
        self._fan_divisor_power = 0.5  # Sqrt for partial fan effect

        # Interference
        self._interference_weight = 0.15

        # Retrieval threshold
        self._retrieval_threshold = 0.2

        # RT noise
        self._rt_noise_sd = 150

        # Error rate
        self._base_error_rate = 0.05

        # Additive vs multiplicative
        self._additive_fan = True

        self._lock = threading.RLock()

    def calculate_activation(
        self,
        concept: Concept,
        source_fan: int = 1
    ) -> float:
        """Calculate activation level of concept."""
        # Base level
        base = self._base_level_activation

        # Spreading activation divided by fan
        spreading = self._source_activation / (source_fan ** self._fan_divisor_power)

        return base + spreading

    def calculate_retrieval_time(
        self,
        subject_fan: int,
        predicate_fan: int
    ) -> int:
        """Calculate retrieval time in ms."""
        # Average fan
        avg_fan = (subject_fan + predicate_fan) / 2

        if self._additive_fan:
            # Additive model
            rt = self._base_rt_ms + self._fan_slope * avg_fan
        else:
            # Multiplicative (ACT-R)
            total_activation = (
                self.calculate_activation(None, subject_fan) +
                self.calculate_activation(None, predicate_fan)
            )
            rt = self._base_rt_ms * (2.0 / total_activation)

        # Add noise
        rt += random.gauss(0, self._rt_noise_sd)

        return max(400, int(rt))

    def calculate_error_rate(
        self,
        fan: int
    ) -> float:
        """Calculate error rate by fan."""
        return self._base_error_rate + 0.02 * fan

    def get_mechanisms(
        self
    ) -> Dict[str, str]:
        """Get proposed mechanisms."""
        return {
            'spreading_activation': 'Activation divided among associates',
            'competition': 'Associates compete at retrieval',
            'interference': 'More associates = more interference',
            'capacity': 'Limited source activation',
            'inhibition': 'Irrelevant associates inhibited'
        }

    def get_act_r_formula(
        self
    ) -> str:
        """Get ACT-R fan equation."""
        return (
            "Activation_i = B_i + Σ W_j × S_ji\n"
            "S_ji = S - log(fan_j)\n"
            "RT = F × e^(-Activation)"
        )

    def get_key_findings(
        self
    ) -> Dict[str, str]:
        """Get key empirical findings."""
        return {
            'rt_increase': '100-150ms per fan level',
            'errors': 'Error rate increases with fan',
            'asymmetry': 'Person fan > location fan sometimes',
            'expertise': 'Experts show reduced fan effect',
            'unitization': 'Integrated memories show less fan'
        }


# ============================================================================
# FAN EFFECT SYSTEM
# ============================================================================

class FanEffectSystem:
    """
    Fan effect simulation system.

    "Ba'el's associative network system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = FanEffectModel()

        self._concepts: Dict[str, Concept] = {}
        self._associations: Dict[str, Association] = {}
        self._trials: List[RetrievalTrial] = []

        self._concept_associations: Dict[str, List[str]] = defaultdict(list)

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self, prefix: str = "item") -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"

    def create_concept(
        self,
        name: str,
        concept_type: ConceptType = ConceptType.PERSON
    ) -> Concept:
        """Create concept."""
        concept = Concept(
            id=self._generate_id("concept"),
            name=name,
            concept_type=concept_type,
            fan=0
        )

        self._concepts[concept.id] = concept

        return concept

    def create_association(
        self,
        source: Concept,
        target: Concept
    ) -> Association:
        """Create association between concepts."""
        # Determine type
        if source.concept_type == ConceptType.PERSON:
            if target.concept_type == ConceptType.LOCATION:
                assoc_type = AssociationType.PERSON_LOCATION
            else:
                assoc_type = AssociationType.PERSON_OBJECT
        else:
            assoc_type = AssociationType.LOCATION_OBJECT

        association = Association(
            id=self._generate_id("assoc"),
            source=source,
            target=target,
            association_type=assoc_type,
            strength=random.uniform(0.6, 0.9)
        )

        self._associations[association.id] = association

        # Update fans
        source.fan += 1
        target.fan += 1

        self._concept_associations[source.id].append(target.id)
        self._concept_associations[target.id].append(source.id)

        return association

    def _get_fan_level(self, fan: int) -> FanLevel:
        """Get fan level category."""
        if fan <= 2:
            return FanLevel.LOW
        elif fan <= 4:
            return FanLevel.MEDIUM
        else:
            return FanLevel.HIGH

    def verify_association(
        self,
        source: Concept,
        target: Concept,
        exists: bool
    ) -> RetrievalTrial:
        """Verify if association exists."""
        rt = self._model.calculate_retrieval_time(source.fan, target.fan)

        error_rate = self._model.calculate_error_rate((source.fan + target.fan) / 2)

        # Determine response
        if random.random() < error_rate:
            response = not exists  # Error
        else:
            response = exists  # Correct

        fan_level = self._get_fan_level((source.fan + target.fan) // 2)

        trial = RetrievalTrial(
            probe=(source, target),
            correct_response=exists,
            response=response,
            rt_ms=rt,
            fan_level=fan_level
        )

        self._trials.append(trial)

        return trial


# ============================================================================
# FAN EFFECT PARADIGM
# ============================================================================

class FanEffectParadigm:
    """
    Fan effect paradigm.

    "Ba'el's associative study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run classic fan effect paradigm."""
        system = FanEffectSystem()

        # Create people with different fans
        # Fan 1 person
        p1 = system.create_concept("Person1", ConceptType.PERSON)
        l1 = system.create_concept("Location1", ConceptType.LOCATION)
        system.create_association(p1, l1)

        # Fan 3 person
        p3 = system.create_concept("Person3", ConceptType.PERSON)
        for i in range(3):
            loc = system.create_concept(f"Location3_{i}", ConceptType.LOCATION)
            system.create_association(p3, loc)

        # Fan 5 person
        p5 = system.create_concept("Person5", ConceptType.PERSON)
        for i in range(5):
            loc = system.create_concept(f"Location5_{i}", ConceptType.LOCATION)
            system.create_association(p5, loc)

        # Test each
        results = {1: [], 3: [], 5: []}

        # Multiple trials
        for _ in range(10):
            t1 = system.verify_association(p1, l1, True)
            results[1].append(t1.rt_ms)

            t3 = system.verify_association(
                p3,
                system._concepts[system._concept_associations[p3.id][0]],
                True
            )
            results[3].append(t3.rt_ms)

            t5 = system.verify_association(
                p5,
                system._concepts[system._concept_associations[p5.id][0]],
                True
            )
            results[5].append(t5.rt_ms)

        # Average RTs
        avg_1 = sum(results[1]) / len(results[1])
        avg_3 = sum(results[3]) / len(results[3])
        avg_5 = sum(results[5]) / len(results[5])

        fan_effect = avg_5 - avg_1
        slope = (avg_5 - avg_1) / 4

        return {
            'fan_1_rt': avg_1,
            'fan_3_rt': avg_3,
            'fan_5_rt': avg_5,
            'fan_effect_ms': fan_effect,
            'fan_slope': slope,
            'interpretation': f'Fan effect: {fan_effect:.0f}ms, slope: {slope:.0f}ms/fan'
        }

    def run_fan_curve(
        self
    ) -> Dict[str, Any]:
        """Generate fan curve."""
        model = FanEffectModel()

        fans = [1, 2, 3, 4, 5, 6, 7, 8]

        results = {}

        for fan in fans:
            rts = [model.calculate_retrieval_time(fan, 1) for _ in range(20)]
            avg_rt = sum(rts) / len(rts)
            results[f'fan_{fan}'] = {'rt_ms': avg_rt}

        return {
            'by_fan': results,
            'interpretation': 'Linear increase in RT with fan'
        }

    def run_activation_study(
        self
    ) -> Dict[str, Any]:
        """Study activation levels."""
        model = FanEffectModel()

        fans = [1, 2, 4, 8]

        results = {}

        for fan in fans:
            activation = model.calculate_activation(None, fan)
            results[f'fan_{fan}'] = {'activation': activation}

        return {
            'by_fan': results,
            'interpretation': 'Activation decreases with fan (divided)'
        }

    def run_error_study(
        self
    ) -> Dict[str, Any]:
        """Study error rates by fan."""
        model = FanEffectModel()

        fans = [1, 2, 3, 4, 5]

        results = {}

        for fan in fans:
            error = model.calculate_error_rate(fan)
            results[f'fan_{fan}'] = {'error_rate': error}

        return {
            'by_fan': results,
            'interpretation': 'Error rate increases with fan'
        }

    def run_mechanism_study(
        self
    ) -> Dict[str, Any]:
        """Study underlying mechanisms."""
        model = FanEffectModel()

        mechanisms = model.get_mechanisms()
        formula = model.get_act_r_formula()
        findings = model.get_key_findings()

        return {
            'mechanisms': mechanisms,
            'act_r_formula': formula,
            'findings': findings,
            'interpretation': 'Spreading activation divided by fan'
        }

    def run_expertise_study(
        self
    ) -> Dict[str, Any]:
        """Study expertise effects."""
        model = FanEffectModel()

        # Experts show reduced fan effect
        # Simulate by reducing slope for experts

        novice_slope = model._fan_slope
        expert_slope = novice_slope * 0.5  # Reduced

        return {
            'novice_slope': novice_slope,
            'expert_slope': expert_slope,
            'reduction': (novice_slope - expert_slope) / novice_slope,
            'interpretation': 'Experts show reduced fan effect'
        }


# ============================================================================
# FAN EFFECT ENGINE
# ============================================================================

class FanEffectEngine:
    """
    Complete fan effect engine.

    "Ba'el's associative interference engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = FanEffectParadigm()
        self._system = FanEffectSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Concept operations

    def create_concept(
        self,
        name: str,
        concept_type: ConceptType = ConceptType.PERSON
    ) -> Concept:
        """Create concept."""
        return self._system.create_concept(name, concept_type)

    def create_association(
        self,
        source: Concept,
        target: Concept
    ) -> Association:
        """Create association."""
        return self._system.create_association(source, target)

    def verify_association(
        self,
        source: Concept,
        target: Concept,
        exists: bool = True
    ) -> RetrievalTrial:
        """Verify association."""
        return self._system.verify_association(source, target, exists)

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def generate_fan_curve(
        self
    ) -> Dict[str, Any]:
        """Generate fan curve."""
        return self._paradigm.run_fan_curve()

    def study_activation(
        self
    ) -> Dict[str, Any]:
        """Study activation."""
        return self._paradigm.run_activation_study()

    def study_errors(
        self
    ) -> Dict[str, Any]:
        """Study errors."""
        return self._paradigm.run_error_study()

    def study_mechanisms(
        self
    ) -> Dict[str, Any]:
        """Study mechanisms."""
        return self._paradigm.run_mechanism_study()

    def study_expertise(
        self
    ) -> Dict[str, Any]:
        """Study expertise."""
        return self._paradigm.run_expertise_study()

    # Analysis

    def get_metrics(self) -> FanMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_classic()

        last = self._experiment_results[-1]

        return FanMetrics(
            low_fan_rt=last['fan_1_rt'],
            high_fan_rt=last['fan_5_rt'],
            fan_effect_ms=last['fan_effect_ms'],
            fan_slope=last['fan_slope']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'concepts': len(self._system._concepts),
            'associations': len(self._system._associations),
            'trials': len(self._system._trials)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_fan_effect_engine() -> FanEffectEngine:
    """Create fan effect engine."""
    return FanEffectEngine()


def demonstrate_fan_effect() -> Dict[str, Any]:
    """Demonstrate fan effect."""
    engine = create_fan_effect_engine()

    # Classic
    classic = engine.run_classic()

    # Fan curve
    curve = engine.generate_fan_curve()

    # Errors
    errors = engine.study_errors()

    # Mechanisms
    mechanisms = engine.study_mechanisms()

    return {
        'classic': {
            'fan_1': f"{classic['fan_1_rt']:.0f}ms",
            'fan_3': f"{classic['fan_3_rt']:.0f}ms",
            'fan_5': f"{classic['fan_5_rt']:.0f}ms",
            'effect': f"{classic['fan_effect_ms']:.0f}ms",
            'slope': f"{classic['fan_slope']:.0f}ms/fan"
        },
        'by_fan': {
            k: f"{v['rt_ms']:.0f}ms"
            for k, v in list(curve['by_fan'].items())[:4]
        },
        'mechanisms': list(mechanisms['mechanisms'].keys()),
        'interpretation': (
            f"Fan effect: {classic['fan_effect_ms']:.0f}ms. "
            f"More associations = slower retrieval. "
            f"Spreading activation divided by fan."
        )
    }


def get_fan_effect_facts() -> Dict[str, str]:
    """Get facts about fan effect."""
    return {
        'anderson_1974': 'Original discovery',
        'act_r': 'ACT-R model prediction',
        'slope': '~100ms per additional association',
        'mechanism': 'Activation divided among associates',
        'errors': 'Error rate also increases',
        'expertise': 'Experts show reduced effect',
        'unitization': 'Integrated memories reduce effect',
        'applications': 'Database design, education'
    }
