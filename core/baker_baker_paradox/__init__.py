"""
BAEL Baker-Baker Paradox Engine
================================

Names harder to remember than occupations.
McWeeny et al.'s name-face association effect.

"Ba'el knows what you do, not what you're called." — Ba'el
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

logger = logging.getLogger("BAEL.BakerBakerParadox")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class LabelType(Enum):
    """Type of label."""
    PROPER_NAME = auto()       # "Mr. Baker" (surname)
    OCCUPATION = auto()        # "a baker" (job)
    NICKNAME = auto()
    HOBBY = auto()


class WordProperty(Enum):
    """Properties of word labels."""
    IMAGEABLE = auto()
    MEANINGFUL = auto()
    ARBITRARY = auto()


class AssociationType(Enum):
    """Type of face-label association."""
    SEMANTIC = auto()
    EPISODIC = auto()
    ARBITRARY = auto()


class FaceType(Enum):
    """Type of face."""
    DISTINCTIVE = auto()
    TYPICAL = auto()


@dataclass
class Face:
    """
    A face to be remembered.
    """
    id: str
    face_type: FaceType
    distinctiveness: float


@dataclass
class FaceLabel:
    """
    A label for a face.
    """
    face_id: str
    label: str
    label_type: LabelType
    imageability: float
    meaningfulness: float


@dataclass
class RecallTest:
    """
    Recall test result.
    """
    face: Face
    label: FaceLabel
    recalled: bool
    response: str
    response_time_ms: int


@dataclass
class BakerParadoxMetrics:
    """
    Baker-Baker paradox metrics.
    """
    name_recall: float
    occupation_recall: float
    paradox_magnitude: float
    tip_of_tongue_rate: float


# ============================================================================
# BAKER BAKER MODEL
# ============================================================================

class BakerBakerModel:
    """
    Model of baker-baker paradox.

    "Ba'el's meaningfulness model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base recall rates
        self._base_recall = {
            LabelType.PROPER_NAME: 0.45,
            LabelType.OCCUPATION: 0.70,
            LabelType.NICKNAME: 0.55,
            LabelType.HOBBY: 0.65
        }

        # Meaningfulness effect
        self._meaningfulness_weight = 0.15

        # Imageability effect
        self._imageability_weight = 0.12

        # Face distinctiveness effect
        self._distinctiveness_weight = 0.10

        # Semantic network activation
        self._semantic_activation = 0.20

        # Tip of tongue for names
        self._name_tot_rate = 0.35
        self._occupation_tot_rate = 0.15

        # Encoding strategy effects
        self._elaboration_benefit = 0.12

        # Repetition effects
        self._repetition_benefit = 0.05

        self._lock = threading.RLock()

    def calculate_recall_probability(
        self,
        label_type: LabelType,
        imageability: float = 0.5,
        meaningfulness: float = 0.5,
        face_distinctiveness: float = 0.5,
        elaborated: bool = False,
        n_exposures: int = 1
    ) -> float:
        """Calculate recall probability."""
        prob = self._base_recall[label_type]

        # Meaningfulness (high for occupations, low for names)
        prob += (meaningfulness - 0.5) * self._meaningfulness_weight * 2

        # Imageability
        prob += (imageability - 0.5) * self._imageability_weight * 2

        # Face distinctiveness
        prob += (face_distinctiveness - 0.5) * self._distinctiveness_weight * 2

        # Semantic activation (occupations benefit more)
        if label_type == LabelType.OCCUPATION:
            prob += self._semantic_activation

        # Elaboration
        if elaborated:
            prob += self._elaboration_benefit

        # Repetition
        prob += min(n_exposures - 1, 5) * self._repetition_benefit

        # Add noise
        prob += random.uniform(-0.08, 0.08)

        return max(0.2, min(0.90, prob))

    def calculate_tot_probability(
        self,
        label_type: LabelType
    ) -> float:
        """Calculate tip-of-tongue probability."""
        if label_type == LabelType.PROPER_NAME:
            return self._name_tot_rate
        else:
            return self._occupation_tot_rate

    def get_semantic_richness(
        self,
        label_type: LabelType
    ) -> float:
        """Get semantic richness of label type."""
        richness = {
            LabelType.PROPER_NAME: 0.15,    # Arbitrary, few associations
            LabelType.OCCUPATION: 0.85,     # Rich associations
            LabelType.NICKNAME: 0.40,
            LabelType.HOBBY: 0.75
        }
        return richness[label_type]

    def get_mechanisms(
        self
    ) -> Dict[str, str]:
        """Get proposed mechanisms."""
        return {
            'semantic_network': 'Occupations activate rich networks',
            'meaningfulness': 'Names are arbitrary labels',
            'imageability': 'Occupations can be visualized',
            'uniqueness': 'Names point to individuals',
            'retrieval_routes': 'Occupations have multiple routes'
        }

    def get_mitigation_strategies(
        self
    ) -> Dict[str, str]:
        """Get strategies to improve name memory."""
        return {
            'elaboration': 'Create meaningful associations',
            'visualization': 'Imagine name meaning',
            'face_feature': 'Link to distinctive feature',
            'repetition': 'Multiple exposures',
            'generation': 'Self-generate associations'
        }


# ============================================================================
# BAKER BAKER SYSTEM
# ============================================================================

class BakerBakerSystem:
    """
    Baker-baker simulation system.

    "Ba'el's name-face system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = BakerBakerModel()

        self._faces: Dict[str, Face] = {}
        self._labels: Dict[str, FaceLabel] = {}
        self._tests: List[RecallTest] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"face_{self._counter}"

    def create_face(
        self,
        face_type: FaceType = FaceType.TYPICAL,
        distinctiveness: float = 0.5
    ) -> Face:
        """Create face."""
        face = Face(
            id=self._generate_id(),
            face_type=face_type,
            distinctiveness=distinctiveness
        )

        self._faces[face.id] = face

        return face

    def assign_label(
        self,
        face: Face,
        label: str,
        label_type: LabelType
    ) -> FaceLabel:
        """Assign label to face."""
        # Set properties based on label type
        if label_type == LabelType.PROPER_NAME:
            imageability = 0.2
            meaningfulness = 0.15
        elif label_type == LabelType.OCCUPATION:
            imageability = 0.75
            meaningfulness = 0.85
        else:
            imageability = 0.5
            meaningfulness = 0.5

        face_label = FaceLabel(
            face_id=face.id,
            label=label,
            label_type=label_type,
            imageability=imageability,
            meaningfulness=meaningfulness
        )

        self._labels[face.id] = face_label

        return face_label

    def test_recall(
        self,
        face: Face
    ) -> RecallTest:
        """Test label recall for face."""
        label = self._labels.get(face.id)
        if not label:
            return None

        recall_prob = self._model.calculate_recall_probability(
            label.label_type,
            label.imageability,
            label.meaningfulness,
            face.distinctiveness
        )

        recalled = random.random() < recall_prob

        # Check for TOT
        tot_prob = self._model.calculate_tot_probability(label.label_type)
        is_tot = not recalled and random.random() < tot_prob

        if recalled:
            response = label.label
        elif is_tot:
            response = "TOT"
        else:
            response = "DK"

        test = RecallTest(
            face=face,
            label=label,
            recalled=recalled,
            response=response,
            response_time_ms=random.randint(500, 4000)
        )

        self._tests.append(test)

        return test


# ============================================================================
# BAKER BAKER PARADIGM
# ============================================================================

class BakerBakerParadigm:
    """
    Baker-baker paradigm.

    "Ba'el's name-occupation study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self,
        n_faces: int = 20
    ) -> Dict[str, Any]:
        """Run classic baker-baker paradigm."""
        system = BakerBakerSystem()

        results = {
            'name': [],
            'occupation': []
        }

        name_labels = ["Baker", "Carpenter", "Farmer", "Fisher", "Hunter",
                      "Mason", "Miller", "Potter", "Smith", "Taylor"]

        occupation_labels = ["baker", "carpenter", "farmer", "fisher", "hunter",
                            "mason", "miller", "potter", "smith", "tailor"]

        for i in range(n_faces):
            face = system.create_face()

            if i < n_faces // 2:
                # Name condition
                label = random.choice(name_labels)
                system.assign_label(face, f"Mr. {label}", LabelType.PROPER_NAME)
                test = system.test_recall(face)
                results['name'].append(test.recalled)
            else:
                # Occupation condition
                label = random.choice(occupation_labels)
                system.assign_label(face, f"a {label}", LabelType.OCCUPATION)
                test = system.test_recall(face)
                results['occupation'].append(test.recalled)

        name_recall = sum(results['name']) / max(1, len(results['name']))
        occ_recall = sum(results['occupation']) / max(1, len(results['occupation']))

        paradox = occ_recall - name_recall

        return {
            'name_recall': name_recall,
            'occupation_recall': occ_recall,
            'paradox_magnitude': paradox,
            'interpretation': f'Baker-baker paradox: {paradox:.0%} advantage for occupations'
        }

    def run_same_word_study(
        self
    ) -> Dict[str, Any]:
        """Run study with same word as name vs occupation."""
        model = BakerBakerModel()

        # Same word "Baker" - as name vs as occupation
        name_recall = model.calculate_recall_probability(
            LabelType.PROPER_NAME,
            imageability=0.2,
            meaningfulness=0.15
        )

        occ_recall = model.calculate_recall_probability(
            LabelType.OCCUPATION,
            imageability=0.75,
            meaningfulness=0.85
        )

        return {
            'same_word_different_meaning': {
                'as_name': name_recall,
                'as_occupation': occ_recall,
                'difference': occ_recall - name_recall
            },
            'interpretation': 'Same word recalled better as occupation'
        }

    def run_semantic_richness_study(
        self
    ) -> Dict[str, Any]:
        """Study semantic richness."""
        model = BakerBakerModel()

        results = {}

        for label_type in LabelType:
            richness = model.get_semantic_richness(label_type)
            recall = model.calculate_recall_probability(label_type)

            results[label_type.name] = {
                'semantic_richness': richness,
                'recall': recall
            }

        return {
            'by_label_type': results,
            'interpretation': 'Semantic richness predicts recall'
        }

    def run_tot_study(
        self
    ) -> Dict[str, Any]:
        """Study tip-of-tongue rates."""
        model = BakerBakerModel()

        results = {}

        for label_type in [LabelType.PROPER_NAME, LabelType.OCCUPATION]:
            tot = model.calculate_tot_probability(label_type)
            results[label_type.name] = {'tot_rate': tot}

        return {
            'by_type': results,
            'interpretation': 'Names more prone to TOT states'
        }

    def run_elaboration_study(
        self
    ) -> Dict[str, Any]:
        """Study elaboration effects."""
        model = BakerBakerModel()

        conditions = {
            'no_elaboration': False,
            'elaborated': True
        }

        results = {}

        for condition, elaborated in conditions.items():
            name_recall = model.calculate_recall_probability(
                LabelType.PROPER_NAME, elaborated=elaborated
            )
            results[condition] = {'name_recall': name_recall}

        return {
            'by_elaboration': results,
            'improvement': (results['elaborated']['name_recall'] -
                          results['no_elaboration']['name_recall']),
            'interpretation': 'Elaboration reduces paradox'
        }

    def run_mechanism_study(
        self
    ) -> Dict[str, Any]:
        """Study underlying mechanisms."""
        model = BakerBakerModel()

        mechanisms = model.get_mechanisms()
        mitigation = model.get_mitigation_strategies()

        return {
            'mechanisms': mechanisms,
            'mitigation': mitigation,
            'primary': 'Semantic network activation',
            'interpretation': 'Names lack semantic support'
        }

    def run_distinctiveness_study(
        self
    ) -> Dict[str, Any]:
        """Study face distinctiveness effects."""
        model = BakerBakerModel()

        levels = [0.2, 0.5, 0.8]

        results = {}

        for dist in levels:
            name_recall = model.calculate_recall_probability(
                LabelType.PROPER_NAME,
                face_distinctiveness=dist
            )
            results[f'{int(dist * 100)}%'] = {'name_recall': name_recall}

        return {
            'by_distinctiveness': results,
            'interpretation': 'Distinctive faces help name recall'
        }


# ============================================================================
# BAKER BAKER ENGINE
# ============================================================================

class BakerBakerEngine:
    """
    Complete baker-baker paradox engine.

    "Ba'el's baker-baker engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = BakerBakerParadigm()
        self._system = BakerBakerSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Face operations

    def create_face(
        self,
        face_type: FaceType = FaceType.TYPICAL
    ) -> Face:
        """Create face."""
        return self._system.create_face(face_type)

    def assign_label(
        self,
        face: Face,
        label: str,
        label_type: LabelType
    ) -> FaceLabel:
        """Assign label."""
        return self._system.assign_label(face, label, label_type)

    def test_recall(
        self,
        face: Face
    ) -> RecallTest:
        """Test recall."""
        return self._system.test_recall(face)

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def study_same_word(
        self
    ) -> Dict[str, Any]:
        """Study same word effect."""
        return self._paradigm.run_same_word_study()

    def study_semantic_richness(
        self
    ) -> Dict[str, Any]:
        """Study semantic richness."""
        return self._paradigm.run_semantic_richness_study()

    def study_tot(
        self
    ) -> Dict[str, Any]:
        """Study TOT rates."""
        return self._paradigm.run_tot_study()

    def study_elaboration(
        self
    ) -> Dict[str, Any]:
        """Study elaboration."""
        return self._paradigm.run_elaboration_study()

    def study_mechanisms(
        self
    ) -> Dict[str, Any]:
        """Study mechanisms."""
        return self._paradigm.run_mechanism_study()

    def study_distinctiveness(
        self
    ) -> Dict[str, Any]:
        """Study face distinctiveness."""
        return self._paradigm.run_distinctiveness_study()

    # Analysis

    def get_metrics(self) -> BakerParadoxMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_classic()

        last = self._experiment_results[-1]

        model = BakerBakerModel()

        return BakerParadoxMetrics(
            name_recall=last['name_recall'],
            occupation_recall=last['occupation_recall'],
            paradox_magnitude=last['paradox_magnitude'],
            tip_of_tongue_rate=model.calculate_tot_probability(LabelType.PROPER_NAME)
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'faces': len(self._system._faces),
            'labels': len(self._system._labels),
            'tests': len(self._system._tests)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_baker_baker_engine() -> BakerBakerEngine:
    """Create baker-baker paradox engine."""
    return BakerBakerEngine()


def demonstrate_baker_baker_paradox() -> Dict[str, Any]:
    """Demonstrate baker-baker paradox."""
    engine = create_baker_baker_engine()

    # Classic
    classic = engine.run_classic()

    # Same word
    same_word = engine.study_same_word()

    # TOT
    tot = engine.study_tot()

    # Mechanisms
    mechanisms = engine.study_mechanisms()

    return {
        'classic': {
            'name_recall': f"{classic['name_recall']:.0%}",
            'occupation_recall': f"{classic['occupation_recall']:.0%}",
            'paradox': f"{classic['paradox_magnitude']:.0%}"
        },
        'same_word': {
            'as_name': f"{same_word['same_word_different_meaning']['as_name']:.0%}",
            'as_occupation': f"{same_word['same_word_different_meaning']['as_occupation']:.0%}"
        },
        'tot_rates': {
            k: f"{v['tot_rate']:.0%}"
            for k, v in tot['by_type'].items()
        },
        'mechanisms': list(mechanisms['mechanisms'].keys()),
        'interpretation': (
            f"Paradox: {classic['paradox_magnitude']:.0%}. "
            f"'Baker' (name) harder than 'baker' (job). "
            f"Names lack semantic richness."
        )
    }


def get_baker_baker_facts() -> Dict[str, str]:
    """Get facts about baker-baker paradox."""
    return {
        'mcweeny_1987': 'Baker-baker paradox discovery',
        'effect': '20-30% better recall for occupations',
        'mechanism': 'Semantic network activation',
        'tot': 'Names prone to tip-of-tongue',
        'same_word': 'Same word, different recall',
        'elaboration': 'Reduces the paradox',
        'social': 'Names socially important but hard',
        'applications': 'Memory training, name badges'
    }
