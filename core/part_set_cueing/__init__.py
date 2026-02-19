"""
BAEL Part-Set Cueing Inhibition Engine
========================================

Providing part of a list impairs recall of the rest.
Slamecka's part-set cueing effect.

"Ba'el's cues cast shadows on the unseen." — Ba'el
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

logger = logging.getLogger("BAEL.PartSetCueing")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class CueCondition(Enum):
    """Cueing condition."""
    NO_CUES = auto()
    WEAK_CUES = auto()
    STRONG_CUES = auto()
    MANY_CUES = auto()


class MaterialType(Enum):
    """Type of material."""
    WORD_LIST = auto()
    CATEGORY = auto()
    EPISODIC = auto()
    ASSOCIATIVE = auto()


class InhibitionType(Enum):
    """Type of inhibition."""
    STRATEGY_DISRUPTION = auto()
    RETRIEVAL_INTERFERENCE = auto()
    OUTPUT_EDITING = auto()
    CUE_OVERLOAD = auto()


class RecallPhase(Enum):
    """Phase of recall."""
    CUE_PROCESSING = auto()
    FREE_RECALL = auto()
    CUED_RECALL = auto()


@dataclass
class StudyList:
    """
    A list of items to study.
    """
    id: str
    items: List[str]
    category: Optional[str]
    organization: float   # 0-1, how organized


@dataclass
class CueSet:
    """
    A set of cues provided at test.
    """
    list_id: str
    cues: List[str]
    cue_proportion: float
    cue_strength: float


@dataclass
class RecallResult:
    """
    Recall test result.
    """
    list_id: str
    cue_condition: CueCondition
    items_recalled: List[str]
    cued_items: int
    non_cued_items: int
    total_possible: int


@dataclass
class PartSetMetrics:
    """
    Part-set cueing metrics.
    """
    no_cue_recall: float
    cued_recall: float
    inhibition_effect: float
    non_cued_impairment: float


# ============================================================================
# PART SET CUEING MODEL
# ============================================================================

class PartSetCueingModel:
    """
    Model of part-set cueing inhibition.

    "Ba'el's cue interference model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base free recall rate
        self._base_recall = 0.55

        # Inhibition from cues
        self._base_inhibition = 0.15

        # Cue proportion effects
        self._proportion_effects = {
            0.25: 0.10,   # Few cues
            0.50: 0.18,   # Many cues
            0.75: 0.22    # Very many cues
        }

        # Material effects
        self._material_effects = {
            MaterialType.WORD_LIST: 0.0,
            MaterialType.CATEGORY: 0.05,
            MaterialType.EPISODIC: 0.08,
            MaterialType.ASSOCIATIVE: 0.10
        }

        # Organization effects
        self._organization_effect = 0.10  # Organized = more inhibition

        # Cue strength effects
        self._strong_cue_inhibition = 0.05

        # Mechanism weights
        self._strategy_disruption_weight = 0.40
        self._retrieval_interference_weight = 0.35
        self._editing_weight = 0.25

        self._lock = threading.RLock()

    def calculate_non_cued_recall(
        self,
        cue_condition: CueCondition,
        material_type: MaterialType = MaterialType.WORD_LIST,
        cue_proportion: float = 0.50,
        organization: float = 0.5
    ) -> float:
        """Calculate recall of non-cued items."""
        recall = self._base_recall

        if cue_condition == CueCondition.NO_CUES:
            # Free recall baseline
            return recall + random.uniform(-0.1, 0.1)

        # Apply inhibition
        inhibition = self._base_inhibition

        # Proportion effect
        closest_prop = min(self._proportion_effects.keys(),
                          key=lambda x: abs(x - cue_proportion))
        inhibition += self._proportion_effects[closest_prop]

        # Material
        inhibition += self._material_effects[material_type]

        # Organization
        inhibition += organization * self._organization_effect

        # Strong cues hurt more
        if cue_condition == CueCondition.STRONG_CUES:
            inhibition += self._strong_cue_inhibition

        recall -= inhibition

        # Add noise
        recall += random.uniform(-0.1, 0.1)

        return max(0.2, min(0.70, recall))

    def calculate_cued_item_recall(
        self
    ) -> float:
        """Calculate recall of cued items (given as part of task)."""
        # Cued items are "recalled" by definition
        return 0.95 + random.uniform(0, 0.05)

    def calculate_total_recall(
        self,
        cue_condition: CueCondition,
        cue_proportion: float = 0.50,
        material_type: MaterialType = MaterialType.WORD_LIST,
        organization: float = 0.5
    ) -> float:
        """Calculate total recall including cued items."""
        if cue_condition == CueCondition.NO_CUES:
            return self._base_recall + random.uniform(-0.1, 0.1)

        # Non-cued items
        non_cued_recall = self.calculate_non_cued_recall(
            cue_condition, material_type, cue_proportion, organization
        )

        # Cued items
        cued_recall = self.calculate_cued_item_recall()

        # Weighted average
        total = (cued_recall * cue_proportion +
                non_cued_recall * (1 - cue_proportion))

        return total

    def get_mechanisms(
        self
    ) -> Dict[str, str]:
        """Get proposed mechanisms."""
        return {
            'strategy_disruption': 'Cues disrupt organized retrieval',
            'retrieval_interference': 'Cues compete at retrieval',
            'output_editing': 'Cues mark items as already recalled',
            'cue_overload': 'Too many cues reduce effectiveness'
        }

    def get_mechanism_weights(
        self
    ) -> Dict[str, float]:
        """Get mechanism contribution weights."""
        return {
            'strategy_disruption': self._strategy_disruption_weight,
            'retrieval_interference': self._retrieval_interference_weight,
            'output_editing': self._editing_weight
        }

    def get_boundary_conditions(
        self
    ) -> Dict[str, str]:
        """Get boundary conditions for the effect."""
        return {
            'organized_material': 'Effect stronger for organized material',
            'strong_cues': 'Strong cues produce more inhibition',
            'many_cues': 'More cues = more inhibition',
            'category': 'Stronger within categories',
            'individual_differences': 'Varies with retrieval strategy'
        }


# ============================================================================
# PART SET CUEING SYSTEM
# ============================================================================

class PartSetCueingSystem:
    """
    Part-set cueing simulation system.

    "Ba'el's cue system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = PartSetCueingModel()

        self._lists: Dict[str, StudyList] = {}
        self._cue_sets: Dict[str, CueSet] = {}
        self._results: List[RecallResult] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"list_{self._counter}"

    def create_study_list(
        self,
        items: List[str],
        category: Optional[str] = None,
        organization: float = 0.5
    ) -> StudyList:
        """Create study list."""
        study_list = StudyList(
            id=self._generate_id(),
            items=items,
            category=category,
            organization=organization
        )

        self._lists[study_list.id] = study_list

        return study_list

    def create_cue_set(
        self,
        list_id: str,
        cue_proportion: float = 0.50,
        cue_strength: float = 0.5
    ) -> CueSet:
        """Create cue set from list."""
        study_list = self._lists.get(list_id)
        if not study_list:
            return None

        n_cues = int(len(study_list.items) * cue_proportion)
        cues = random.sample(study_list.items, n_cues)

        cue_set = CueSet(
            list_id=list_id,
            cues=cues,
            cue_proportion=cue_proportion,
            cue_strength=cue_strength
        )

        self._cue_sets[list_id] = cue_set

        return cue_set

    def test_recall(
        self,
        list_id: str,
        cue_condition: CueCondition
    ) -> RecallResult:
        """Test recall with or without cues."""
        study_list = self._lists.get(list_id)
        if not study_list:
            return None

        cue_set = self._cue_sets.get(list_id)
        cue_proportion = cue_set.cue_proportion if cue_set else 0.0

        # Calculate recall probabilities
        if cue_condition == CueCondition.NO_CUES:
            recall_prob = self._model.calculate_non_cued_recall(
                CueCondition.NO_CUES
            )

            # Simulate recall
            recalled = [item for item in study_list.items
                       if random.random() < recall_prob]

            result = RecallResult(
                list_id=list_id,
                cue_condition=cue_condition,
                items_recalled=recalled,
                cued_items=0,
                non_cued_items=len(recalled),
                total_possible=len(study_list.items)
            )
        else:
            # Cued condition
            cued_items = cue_set.cues if cue_set else []
            non_cued_items = [i for i in study_list.items if i not in cued_items]

            # Non-cued recall
            non_cued_prob = self._model.calculate_non_cued_recall(
                cue_condition,
                organization=study_list.organization
            )

            recalled_non_cued = [item for item in non_cued_items
                                if random.random() < non_cued_prob]

            recalled = cued_items + recalled_non_cued

            result = RecallResult(
                list_id=list_id,
                cue_condition=cue_condition,
                items_recalled=recalled,
                cued_items=len(cued_items),
                non_cued_items=len(recalled_non_cued),
                total_possible=len(study_list.items)
            )

        self._results.append(result)

        return result


# ============================================================================
# PART SET CUEING PARADIGM
# ============================================================================

class PartSetCueingParadigm:
    """
    Part-set cueing paradigm.

    "Ba'el's cue study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self,
        n_trials: int = 20,
        list_length: int = 20
    ) -> Dict[str, Any]:
        """Run classic part-set cueing paradigm."""
        system = PartSetCueingSystem()

        results = {
            'no_cues': [],
            'with_cues': []
        }

        for i in range(n_trials):
            items = [f"word_{i}_{j}" for j in range(list_length)]
            study_list = system.create_study_list(items)

            if i < n_trials // 2:
                # No cues
                result = system.test_recall(study_list.id, CueCondition.NO_CUES)
                recall_rate = result.non_cued_items / result.total_possible
                results['no_cues'].append(recall_rate)
            else:
                # With cues
                system.create_cue_set(study_list.id, 0.50)
                result = system.test_recall(study_list.id, CueCondition.STRONG_CUES)
                # Measure non-cued recall only
                non_cued_possible = int(result.total_possible * 0.50)
                recall_rate = result.non_cued_items / max(1, non_cued_possible)
                results['with_cues'].append(recall_rate)

        no_cue_mean = sum(results['no_cues']) / max(1, len(results['no_cues']))
        cued_mean = sum(results['with_cues']) / max(1, len(results['with_cues']))

        inhibition = no_cue_mean - cued_mean

        return {
            'no_cue_recall': no_cue_mean,
            'cued_recall': cued_mean,
            'inhibition_effect': inhibition,
            'interpretation': f'Part-set inhibition: {inhibition:.0%}'
        }

    def run_proportion_study(
        self
    ) -> Dict[str, Any]:
        """Study cue proportion effects."""
        model = PartSetCueingModel()

        proportions = [0.25, 0.50, 0.75]

        results = {}

        for prop in proportions:
            recall = model.calculate_non_cued_recall(
                CueCondition.STRONG_CUES,
                cue_proportion=prop
            )

            results[f'{int(prop * 100)}%'] = {
                'non_cued_recall': recall
            }

        return {
            'by_proportion': results,
            'interpretation': 'More cues = more inhibition'
        }

    def run_material_study(
        self
    ) -> Dict[str, Any]:
        """Study material type effects."""
        model = PartSetCueingModel()

        results = {}

        for material in MaterialType:
            recall = model.calculate_non_cued_recall(
                CueCondition.STRONG_CUES,
                material_type=material
            )

            results[material.name] = {
                'non_cued_recall': recall
            }

        return {
            'by_material': results,
            'interpretation': 'Associative material shows most inhibition'
        }

    def run_organization_study(
        self
    ) -> Dict[str, Any]:
        """Study organization effects."""
        model = PartSetCueingModel()

        levels = [0.2, 0.5, 0.8]

        results = {}

        for org in levels:
            recall = model.calculate_non_cued_recall(
                CueCondition.STRONG_CUES,
                organization=org
            )

            results[f'{int(org * 100)}%'] = {
                'non_cued_recall': recall
            }

        return {
            'by_organization': results,
            'interpretation': 'Organized material shows more inhibition'
        }

    def run_mechanism_study(
        self
    ) -> Dict[str, Any]:
        """Study underlying mechanisms."""
        model = PartSetCueingModel()

        mechanisms = model.get_mechanisms()
        weights = model.get_mechanism_weights()
        boundaries = model.get_boundary_conditions()

        return {
            'mechanisms': mechanisms,
            'weights': weights,
            'boundaries': boundaries,
            'primary': 'Strategy disruption',
            'interpretation': 'Cues disrupt organized retrieval strategies'
        }

    def run_total_recall_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare total recall (including cued items)."""
        model = PartSetCueingModel()

        no_cue = model.calculate_total_recall(CueCondition.NO_CUES)
        with_cue = model.calculate_total_recall(
            CueCondition.STRONG_CUES, cue_proportion=0.50
        )

        return {
            'no_cues': no_cue,
            'with_cues': with_cue,
            'difference': with_cue - no_cue,
            'interpretation': 'Total may be similar but distribution differs'
        }


# ============================================================================
# PART SET CUEING ENGINE
# ============================================================================

class PartSetCueingEngine:
    """
    Complete part-set cueing engine.

    "Ba'el's cue engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = PartSetCueingParadigm()
        self._system = PartSetCueingSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # List operations

    def create_study_list(
        self,
        items: List[str]
    ) -> StudyList:
        """Create study list."""
        return self._system.create_study_list(items)

    def create_cue_set(
        self,
        list_id: str,
        proportion: float = 0.50
    ) -> CueSet:
        """Create cue set."""
        return self._system.create_cue_set(list_id, proportion)

    def test_recall(
        self,
        list_id: str,
        cue_condition: CueCondition
    ) -> RecallResult:
        """Test recall."""
        return self._system.test_recall(list_id, cue_condition)

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def study_proportion(
        self
    ) -> Dict[str, Any]:
        """Study cue proportion."""
        return self._paradigm.run_proportion_study()

    def study_material(
        self
    ) -> Dict[str, Any]:
        """Study material type."""
        return self._paradigm.run_material_study()

    def study_organization(
        self
    ) -> Dict[str, Any]:
        """Study organization."""
        return self._paradigm.run_organization_study()

    def study_mechanisms(
        self
    ) -> Dict[str, Any]:
        """Study mechanisms."""
        return self._paradigm.run_mechanism_study()

    def compare_total_recall(
        self
    ) -> Dict[str, Any]:
        """Compare total recall."""
        return self._paradigm.run_total_recall_comparison()

    # Analysis

    def get_metrics(self) -> PartSetMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_classic()

        last = self._experiment_results[-1]

        return PartSetMetrics(
            no_cue_recall=last['no_cue_recall'],
            cued_recall=last['cued_recall'],
            inhibition_effect=last['inhibition_effect'],
            non_cued_impairment=last['inhibition_effect']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'lists': len(self._system._lists),
            'cue_sets': len(self._system._cue_sets),
            'results': len(self._system._results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_part_set_cueing_engine() -> PartSetCueingEngine:
    """Create part-set cueing engine."""
    return PartSetCueingEngine()


def demonstrate_part_set_cueing() -> Dict[str, Any]:
    """Demonstrate part-set cueing."""
    engine = create_part_set_cueing_engine()

    # Classic
    classic = engine.run_classic()

    # Proportion
    proportion = engine.study_proportion()

    # Mechanisms
    mechanisms = engine.study_mechanisms()

    # Total
    total = engine.compare_total_recall()

    return {
        'classic': {
            'no_cues': f"{classic['no_cue_recall']:.0%}",
            'with_cues': f"{classic['cued_recall']:.0%}",
            'inhibition': f"{classic['inhibition_effect']:.0%}"
        },
        'by_proportion': {
            k: f"{v['non_cued_recall']:.0%}"
            for k, v in proportion['by_proportion'].items()
        },
        'mechanisms': mechanisms['mechanisms'],
        'total_recall': {
            'no_cues': f"{total['no_cues']:.0%}",
            'with_cues': f"{total['with_cues']:.0%}"
        },
        'interpretation': (
            f"Inhibition: {classic['inhibition_effect']:.0%}. "
            f"Part cues impair recall of rest. "
            f"Strategy disruption primary mechanism."
        )
    }


def get_part_set_cueing_facts() -> Dict[str, str]:
    """Get facts about part-set cueing."""
    return {
        'slamecka_1968': 'Part-set cueing effect discovery',
        'effect': '15-25% reduction in non-cued recall',
        'mechanism': 'Strategy disruption',
        'organization': 'Stronger for organized material',
        'proportion': 'More cues = more inhibition',
        'paradox': 'Cues intended to help actually hurt',
        'applications': 'Testing, eyewitness memory',
        'forensic': 'Avoid prompting with partial info'
    }
