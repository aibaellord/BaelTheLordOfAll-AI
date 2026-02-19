"""
BAEL Own-Age Bias Engine
==========================

Better recognition for same-age faces.
Cross-age identification difficulties.

"Ba'el transcends age barriers." — Ba'el
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

logger = logging.getLogger("BAEL.OwnAgeBias")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class AgeGroup(Enum):
    """Age group categories."""
    CHILD = auto()          # 0-12
    ADOLESCENT = auto()     # 13-17
    YOUNG_ADULT = auto()    # 18-30
    MIDDLE_ADULT = auto()   # 31-55
    OLDER_ADULT = auto()    # 56+


class FaceType(Enum):
    """Type of face stimulus."""
    SAME_AGE = auto()
    OTHER_AGE = auto()


class TaskType(Enum):
    """Type of recognition task."""
    OLD_NEW = auto()        # Was this face studied?
    FORCED_CHOICE = auto()  # Which face was studied?
    LINEUP = auto()         # Identify from array


class ExposureType(Enum):
    """Type of cross-age exposure."""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


@dataclass
class Face:
    """
    A face stimulus.
    """
    id: str
    age_group: AgeGroup
    age_years: int
    distinctiveness: float
    emotional_expression: str
    exposure_duration_ms: int


@dataclass
class Participant:
    """
    A participant in the study.
    """
    id: str
    own_age_group: AgeGroup
    own_age_years: int
    cross_age_exposure: Dict[AgeGroup, ExposureType]


@dataclass
class RecognitionResult:
    """
    Result of recognition attempt.
    """
    face_id: str
    face_age_group: AgeGroup
    participant_age_group: AgeGroup
    hit: bool               # Correctly identified studied face
    false_alarm: bool       # Incorrectly identified new face
    confidence: float


@dataclass
class BiasMetrics:
    """
    Own-age bias metrics.
    """
    own_age_accuracy: float
    other_age_accuracy: float
    bias_magnitude: float
    by_age_group: Dict[str, float]


# ============================================================================
# OWN-AGE BIAS MODEL
# ============================================================================

class OwnAgeBiasModel:
    """
    Model of own-age bias.

    "Ba'el's age perception." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base recognition accuracy
        self._base_accuracy = 0.70

        # Own-age advantage
        self._own_age_boost = 0.15

        # Cross-age penalty by distance
        self._adjacent_penalty = 0.05
        self._two_away_penalty = 0.10
        self._three_away_penalty = 0.15
        self._four_away_penalty = 0.20

        # Exposure effects
        self._exposure_effects = {
            ExposureType.LOW: 0.0,
            ExposureType.MEDIUM: 0.05,
            ExposureType.HIGH: 0.10
        }

        # Age ordering for distance calculation
        self._age_order = [
            AgeGroup.CHILD,
            AgeGroup.ADOLESCENT,
            AgeGroup.YOUNG_ADULT,
            AgeGroup.MIDDLE_ADULT,
            AgeGroup.OLDER_ADULT
        ]

        self._lock = threading.RLock()

    def calculate_age_distance(
        self,
        age1: AgeGroup,
        age2: AgeGroup
    ) -> int:
        """Calculate distance between age groups."""
        idx1 = self._age_order.index(age1)
        idx2 = self._age_order.index(age2)
        return abs(idx1 - idx2)

    def calculate_recognition_accuracy(
        self,
        participant: Participant,
        face: Face
    ) -> float:
        """Calculate recognition accuracy."""
        accuracy = self._base_accuracy

        # Own-age advantage
        if face.age_group == participant.own_age_group:
            accuracy += self._own_age_boost
        else:
            # Cross-age penalty based on distance
            distance = self.calculate_age_distance(
                participant.own_age_group,
                face.age_group
            )

            penalties = {
                1: self._adjacent_penalty,
                2: self._two_away_penalty,
                3: self._three_away_penalty,
                4: self._four_away_penalty
            }

            accuracy -= penalties.get(distance, self._four_away_penalty)

        # Exposure effect
        exposure = participant.cross_age_exposure.get(
            face.age_group, ExposureType.LOW
        )
        accuracy += self._exposure_effects[exposure]

        # Distinctiveness effect
        accuracy += (face.distinctiveness - 0.5) * 0.1

        return max(0.0, min(1.0, accuracy))

    def calculate_confidence(
        self,
        accuracy: float,
        correct: bool
    ) -> float:
        """Calculate confidence rating."""
        if correct:
            # Higher confidence for correct responses
            return accuracy * random.uniform(0.8, 1.0)
        else:
            # Lower but variable confidence for errors
            return (1 - accuracy) * random.uniform(0.4, 0.8)


# ============================================================================
# OWN-AGE BIAS SYSTEM
# ============================================================================

class OwnAgeBiasSystem:
    """
    Own-age bias simulation system.

    "Ba'el's cross-age system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = OwnAgeBiasModel()

        self._faces: Dict[str, Face] = {}
        self._participants: Dict[str, Participant] = {}
        self._results: List[RecognitionResult] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def create_face(
        self,
        age_group: AgeGroup,
        distinctiveness: float = 0.5
    ) -> Face:
        """Create a face."""
        # Assign age based on group
        age_ranges = {
            AgeGroup.CHILD: (5, 12),
            AgeGroup.ADOLESCENT: (13, 17),
            AgeGroup.YOUNG_ADULT: (18, 30),
            AgeGroup.MIDDLE_ADULT: (31, 55),
            AgeGroup.OLDER_ADULT: (56, 80)
        }

        low, high = age_ranges[age_group]
        age = random.randint(low, high)

        face = Face(
            id=self._generate_id(),
            age_group=age_group,
            age_years=age,
            distinctiveness=distinctiveness,
            emotional_expression="neutral",
            exposure_duration_ms=2000
        )

        self._faces[face.id] = face

        return face

    def create_participant(
        self,
        age_group: AgeGroup
    ) -> Participant:
        """Create a participant."""
        age_ranges = {
            AgeGroup.CHILD: (8, 12),
            AgeGroup.ADOLESCENT: (13, 17),
            AgeGroup.YOUNG_ADULT: (18, 30),
            AgeGroup.MIDDLE_ADULT: (31, 55),
            AgeGroup.OLDER_ADULT: (56, 75)
        }

        low, high = age_ranges[age_group]
        age = random.randint(low, high)

        # Random exposure levels
        exposure = {}
        for group in AgeGroup:
            if group == age_group:
                exposure[group] = ExposureType.HIGH
            else:
                exposure[group] = random.choice(list(ExposureType))

        participant = Participant(
            id=self._generate_id(),
            own_age_group=age_group,
            own_age_years=age,
            cross_age_exposure=exposure
        )

        self._participants[participant.id] = participant

        return participant

    def run_recognition(
        self,
        participant_id: str,
        face_id: str,
        is_old: bool = True
    ) -> RecognitionResult:
        """Run recognition trial."""
        participant = self._participants.get(participant_id)
        face = self._faces.get(face_id)

        if not participant or not face:
            return None

        accuracy = self._model.calculate_recognition_accuracy(participant, face)

        # Determine outcome
        if is_old:
            # Face was studied
            hit = random.random() < accuracy
            false_alarm = False
        else:
            # Face is new
            hit = False
            false_alarm = random.random() > accuracy

        correct = hit or (not is_old and not false_alarm)
        confidence = self._model.calculate_confidence(accuracy, correct)

        result = RecognitionResult(
            face_id=face_id,
            face_age_group=face.age_group,
            participant_age_group=participant.own_age_group,
            hit=hit,
            false_alarm=false_alarm,
            confidence=confidence
        )

        self._results.append(result)

        return result


# ============================================================================
# OWN-AGE BIAS PARADIGM
# ============================================================================

class OwnAgeBiasParadigm:
    """
    Own-age bias paradigm.

    "Ba'el's age bias study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self,
        n_faces_per_age: int = 10,
        n_participants_per_age: int = 5
    ) -> Dict[str, Any]:
        """Run classic own-age bias paradigm."""
        system = OwnAgeBiasSystem()

        # Create faces for each age group
        faces_by_age = {}
        for age_group in AgeGroup:
            faces_by_age[age_group] = [
                system.create_face(age_group)
                for _ in range(n_faces_per_age)
            ]

        # Create participants
        participants_by_age = {}
        for age_group in AgeGroup:
            participants_by_age[age_group] = [
                system.create_participant(age_group)
                for _ in range(n_participants_per_age)
            ]

        # Run recognition for each participant on faces
        results_matrix = {}

        for p_age, participants in participants_by_age.items():
            results_matrix[p_age.name] = {}

            for f_age, faces in faces_by_age.items():
                hits = 0
                total = 0

                for participant in participants:
                    for face in faces:
                        result = system.run_recognition(
                            participant.id, face.id, is_old=True
                        )
                        if result.hit:
                            hits += 1
                        total += 1

                accuracy = hits / max(1, total)
                results_matrix[p_age.name][f_age.name] = accuracy

        # Calculate own-age bias
        own_age_accs = []
        other_age_accs = []

        for p_age in results_matrix:
            for f_age, acc in results_matrix[p_age].items():
                if p_age == f_age:
                    own_age_accs.append(acc)
                else:
                    other_age_accs.append(acc)

        own_age_mean = sum(own_age_accs) / max(1, len(own_age_accs))
        other_age_mean = sum(other_age_accs) / max(1, len(other_age_accs))
        bias = own_age_mean - other_age_mean

        return {
            'matrix': results_matrix,
            'own_age_accuracy': own_age_mean,
            'other_age_accuracy': other_age_mean,
            'bias_magnitude': bias,
            'interpretation': f'Own-age advantage: {bias:.0%}'
        }

    def run_developmental_study(
        self
    ) -> Dict[str, Any]:
        """Study development of own-age bias."""
        results = {}

        for participant_age in AgeGroup:
            system = OwnAgeBiasSystem()

            # Create participant
            participant = system.create_participant(participant_age)

            # Test on all age groups
            age_accuracies = {}

            for face_age in AgeGroup:
                hits = 0
                n_trials = 20

                for _ in range(n_trials):
                    face = system.create_face(face_age)
                    result = system.run_recognition(
                        participant.id, face.id, is_old=True
                    )
                    if result.hit:
                        hits += 1

                age_accuracies[face_age.name] = hits / n_trials

            results[participant_age.name] = {
                'accuracies': age_accuracies,
                'own_age': age_accuracies[participant_age.name]
            }

        return {
            'by_participant_age': results,
            'interpretation': 'Bias present across all age groups'
        }

    def run_exposure_study(
        self
    ) -> Dict[str, Any]:
        """Study exposure effects."""
        system = OwnAgeBiasSystem()

        results = {}

        for exposure in ExposureType:
            # Young adult recognizing older adults
            participant = system.create_participant(AgeGroup.YOUNG_ADULT)
            participant.cross_age_exposure[AgeGroup.OLDER_ADULT] = exposure

            hits = 0
            n_trials = 30

            for _ in range(n_trials):
                face = system.create_face(AgeGroup.OLDER_ADULT)
                result = system.run_recognition(
                    participant.id, face.id, is_old=True
                )
                if result.hit:
                    hits += 1

            results[exposure.name] = {
                'accuracy': hits / n_trials
            }

        return {
            'by_exposure': results,
            'interpretation': 'Higher exposure reduces bias'
        }

    def run_contact_hypothesis_study(
        self
    ) -> Dict[str, Any]:
        """Test contact hypothesis."""
        # More contact with other-age = less bias
        conditions = {
            'low_contact': ExposureType.LOW,
            'high_contact': ExposureType.HIGH
        }

        results = {}

        for condition, exposure in conditions.items():
            system = OwnAgeBiasSystem()

            participant = system.create_participant(AgeGroup.YOUNG_ADULT)
            participant.cross_age_exposure[AgeGroup.OLDER_ADULT] = exposure

            own_age_hits = 0
            other_age_hits = 0
            n_trials = 30

            for _ in range(n_trials):
                own_face = system.create_face(AgeGroup.YOUNG_ADULT)
                other_face = system.create_face(AgeGroup.OLDER_ADULT)

                own_result = system.run_recognition(
                    participant.id, own_face.id, is_old=True
                )
                other_result = system.run_recognition(
                    participant.id, other_face.id, is_old=True
                )

                if own_result.hit:
                    own_age_hits += 1
                if other_result.hit:
                    other_age_hits += 1

            own_acc = own_age_hits / n_trials
            other_acc = other_age_hits / n_trials

            results[condition] = {
                'own_age': own_acc,
                'other_age': other_acc,
                'bias': own_acc - other_acc
            }

        return {
            'by_contact': results,
            'interpretation': 'Contact reduces own-age bias'
        }

    def run_eyewitness_study(
        self
    ) -> Dict[str, Any]:
        """Study eyewitness implications."""
        system = OwnAgeBiasSystem()

        # Simulate lineup scenario
        results = {}

        for witness_age in [AgeGroup.YOUNG_ADULT, AgeGroup.OLDER_ADULT]:
            for suspect_age in [AgeGroup.YOUNG_ADULT, AgeGroup.OLDER_ADULT]:
                witness = system.create_participant(witness_age)
                suspect = system.create_face(suspect_age)

                hits = 0
                false_alarms = 0
                n_trials = 30

                for _ in range(n_trials):
                    # Half old, half new
                    is_old = random.random() < 0.5

                    if is_old:
                        result = system.run_recognition(
                            witness.id, suspect.id, is_old=True
                        )
                        if result.hit:
                            hits += 1
                    else:
                        new_face = system.create_face(suspect_age)
                        result = system.run_recognition(
                            witness.id, new_face.id, is_old=False
                        )
                        if result.false_alarm:
                            false_alarms += 1

                key = f"{witness_age.name}_witness_{suspect_age.name}_suspect"
                results[key] = {
                    'hit_rate': hits / (n_trials // 2),
                    'false_alarm_rate': false_alarms / (n_trials // 2)
                }

        return {
            'lineup_performance': results,
            'interpretation': 'Cross-age identification more error-prone'
        }


# ============================================================================
# OWN-AGE BIAS ENGINE
# ============================================================================

class OwnAgeBiasEngine:
    """
    Complete own-age bias engine.

    "Ba'el's age bias engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = OwnAgeBiasParadigm()
        self._system = OwnAgeBiasSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Face/participant operations

    def create_face(
        self,
        age_group: AgeGroup
    ) -> Face:
        """Create face."""
        return self._system.create_face(age_group)

    def create_participant(
        self,
        age_group: AgeGroup
    ) -> Participant:
        """Create participant."""
        return self._system.create_participant(age_group)

    def recognize(
        self,
        participant_id: str,
        face_id: str
    ) -> RecognitionResult:
        """Run recognition."""
        return self._system.run_recognition(participant_id, face_id)

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def study_development(
        self
    ) -> Dict[str, Any]:
        """Study developmental effects."""
        return self._paradigm.run_developmental_study()

    def study_exposure(
        self
    ) -> Dict[str, Any]:
        """Study exposure effects."""
        return self._paradigm.run_exposure_study()

    def study_contact(
        self
    ) -> Dict[str, Any]:
        """Study contact hypothesis."""
        return self._paradigm.run_contact_hypothesis_study()

    def study_eyewitness(
        self
    ) -> Dict[str, Any]:
        """Study eyewitness implications."""
        return self._paradigm.run_eyewitness_study()

    # Analysis

    def get_metrics(self) -> BiasMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_classic()

        last = self._experiment_results[-1]

        return BiasMetrics(
            own_age_accuracy=last['own_age_accuracy'],
            other_age_accuracy=last['other_age_accuracy'],
            bias_magnitude=last['bias_magnitude'],
            by_age_group={}
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'faces': len(self._system._faces),
            'participants': len(self._system._participants),
            'trials': len(self._system._results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_own_age_bias_engine() -> OwnAgeBiasEngine:
    """Create own-age bias engine."""
    return OwnAgeBiasEngine()


def demonstrate_own_age_bias() -> Dict[str, Any]:
    """Demonstrate own-age bias."""
    engine = create_own_age_bias_engine()

    # Classic
    classic = engine.run_classic()

    # Exposure
    exposure = engine.study_exposure()

    # Contact
    contact = engine.study_contact()

    # Eyewitness
    eyewitness = engine.study_eyewitness()

    return {
        'own_age_accuracy': f"{classic['own_age_accuracy']:.0%}",
        'other_age_accuracy': f"{classic['other_age_accuracy']:.0%}",
        'bias': f"{classic['bias_magnitude']:.0%}",
        'exposure_effect': {
            k: f"{v['accuracy']:.0%}"
            for k, v in exposure['by_exposure'].items()
        },
        'contact_effect': {
            k: f"bias: {v['bias']:.0%}"
            for k, v in contact['by_contact'].items()
        },
        'interpretation': (
            f"Own-age advantage: {classic['bias_magnitude']:.0%}. "
            f"Contact reduces bias. "
            f"Important for eyewitness testimony."
        )
    }


def get_own_age_bias_facts() -> Dict[str, str]:
    """Get facts about own-age bias."""
    return {
        'definition': 'Better recognition for same-age faces',
        'magnitude': '~10-15% accuracy advantage',
        'mechanism': 'Perceptual expertise, contact',
        'development': 'Present in children and adults',
        'reduction': 'Increased cross-age contact',
        'applications': 'Eyewitness testimony, identification',
        'related': 'Own-race bias, own-gender bias',
        'theories': 'Contact hypothesis, perceptual expertise'
    }
