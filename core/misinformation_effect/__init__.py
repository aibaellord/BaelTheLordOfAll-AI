"""
BAEL Misinformation Effect Engine
===================================

Post-event information distorts memory.
Loftus's misinformation paradigm.

"Ba'el's memory can be rewritten." — Ba'el
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

logger = logging.getLogger("BAEL.MisinformationEffect")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class MisinformationType(Enum):
    """Types of misinformation."""
    SUPPLEMENTARY = auto()    # Adds new false info
    CONTRADICTORY = auto()    # Contradicts original
    SUBTLE = auto()           # Minor detail change
    BLATANT = auto()          # Obvious false info


class SourceType(Enum):
    """Source of information."""
    EVENT = auto()            # Original event
    NARRATIVE = auto()        # Post-event narrative
    QUESTION = auto()         # Suggestive question


class MemorySource(Enum):
    """Attributed source of memory."""
    ORIGINAL_EVENT = auto()
    POST_EVENT_INFO = auto()
    UNCERTAIN = auto()


@dataclass
class EventDetail:
    """
    A detail from the original event.
    """
    id: str
    description: str
    original_value: str
    encoding_strength: float


@dataclass
class MisinformationItem:
    """
    Misinformation about an event detail.
    """
    detail_id: str
    misinformation_value: str
    misinformation_type: MisinformationType
    source: SourceType
    credibility: float


@dataclass
class MemoryReport:
    """
    A participant's memory report.
    """
    detail_id: str
    reported_value: str
    correct: bool
    misinformed: bool
    source_attribution: MemorySource
    confidence: float


@dataclass
class MisinformationMetrics:
    """
    Misinformation effect metrics.
    """
    control_accuracy: float
    misinformed_accuracy: float
    misinformation_effect: float
    source_confusion: float


# ============================================================================
# SOURCE MONITORING MODEL
# ============================================================================

class SourceMonitoringModel:
    """
    Source monitoring model for misinformation.

    "Ba'el's source confusion." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Encoding parameters
        self._event_encoding = 0.6
        self._misinformation_encoding = 0.7

        # Source discrimination
        self._source_discrimination = 0.5

        # Misinformation susceptibility
        self._susceptibility = {
            MisinformationType.SUPPLEMENTARY: 0.5,
            MisinformationType.CONTRADICTORY: 0.35,
            MisinformationType.SUBTLE: 0.6,
            MisinformationType.BLATANT: 0.25
        }

        # Source credibility effects
        self._credibility_weight = 0.3

        self._lock = threading.RLock()

    def calculate_misinformation_acceptance(
        self,
        detail: EventDetail,
        misinfo: MisinformationItem
    ) -> float:
        """Calculate probability of accepting misinformation."""
        # Base susceptibility by type
        base = self._susceptibility.get(misinfo.misinformation_type, 0.4)

        # Weaker original encoding increases susceptibility
        encoding_factor = 1 - detail.encoding_strength * 0.3

        # Credibility of source
        credibility_factor = misinfo.credibility * self._credibility_weight

        prob = base * encoding_factor + credibility_factor

        return min(0.8, max(0.1, prob))

    def calculate_source_confusion(
        self,
        detail: EventDetail,
        misinfo: MisinformationItem
    ) -> float:
        """Calculate probability of source confusion."""
        # Base source discrimination
        base_confusion = 1 - self._source_discrimination

        # Similar sources harder to discriminate
        if misinfo.source == SourceType.NARRATIVE:
            base_confusion += 0.1

        # Time delay would increase confusion (simulated)
        time_factor = random.uniform(0, 0.2)

        confusion = base_confusion + time_factor

        return min(0.7, max(0.1, confusion))


# ============================================================================
# MISINFORMATION SYSTEM
# ============================================================================

class MisinformationSystem:
    """
    Misinformation effect system.

    "Ba'el's memory contamination." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = SourceMonitoringModel()

        self._details: Dict[str, EventDetail] = {}
        self._misinformation: Dict[str, MisinformationItem] = {}
        self._reports: List[MemoryReport] = []

        self._detail_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._detail_counter += 1
        return f"detail_{self._detail_counter}"

    def encode_event(
        self,
        description: str,
        original_value: str
    ) -> EventDetail:
        """Encode an event detail."""
        detail = EventDetail(
            id=self._generate_id(),
            description=description,
            original_value=original_value,
            encoding_strength=random.uniform(0.4, 0.8)
        )

        self._details[detail.id] = detail

        return detail

    def present_misinformation(
        self,
        detail_id: str,
        false_value: str,
        misinfo_type: MisinformationType = MisinformationType.CONTRADICTORY,
        source: SourceType = SourceType.NARRATIVE,
        credibility: float = 0.7
    ) -> MisinformationItem:
        """Present misinformation about a detail."""
        misinfo = MisinformationItem(
            detail_id=detail_id,
            misinformation_value=false_value,
            misinformation_type=misinfo_type,
            source=source,
            credibility=credibility
        )

        self._misinformation[detail_id] = misinfo

        return misinfo

    def test_memory(
        self,
        detail_id: str
    ) -> MemoryReport:
        """Test memory for a detail."""
        detail = self._details.get(detail_id)
        if not detail:
            return None

        misinfo = self._misinformation.get(detail_id)

        if misinfo:
            # Misinformed condition
            acceptance_prob = self._model.calculate_misinformation_acceptance(
                detail, misinfo
            )

            if random.random() < acceptance_prob:
                # Accepted misinformation
                reported_value = misinfo.misinformation_value
                correct = False
                misinformed = True

                # Source attribution
                confusion_prob = self._model.calculate_source_confusion(detail, misinfo)
                if random.random() < confusion_prob:
                    source_attr = MemorySource.ORIGINAL_EVENT  # Wrong attribution
                else:
                    source_attr = MemorySource.UNCERTAIN
            else:
                # Rejected misinformation
                reported_value = detail.original_value
                correct = True
                misinformed = False
                source_attr = MemorySource.ORIGINAL_EVENT
        else:
            # Control condition
            recall_prob = 0.5 + detail.encoding_strength * 0.3

            if random.random() < recall_prob:
                reported_value = detail.original_value
                correct = True
            else:
                reported_value = "don't remember"
                correct = False

            misinformed = False
            source_attr = MemorySource.ORIGINAL_EVENT

        report = MemoryReport(
            detail_id=detail_id,
            reported_value=reported_value,
            correct=correct,
            misinformed=misinformed,
            source_attribution=source_attr,
            confidence=random.uniform(0.5, 0.9)
        )

        self._reports.append(report)

        return report


# ============================================================================
# EXPERIMENTAL PARADIGM
# ============================================================================

class MisinformationParadigm:
    """
    Misinformation effect paradigm.

    "Ba'el's post-event information study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_standard_experiment(
        self,
        n_details: int = 20
    ) -> Dict[str, Any]:
        """Run standard misinformation experiment."""
        system = MisinformationSystem()

        # Phase 1: Encode event
        details = []
        for i in range(n_details):
            detail = system.encode_event(
                f"detail_{i}",
                f"original_value_{i}"
            )
            details.append(detail)

        # Phase 2: Post-event information (half misinformed)
        misinformed_details = details[:n_details // 2]
        control_details = details[n_details // 2:]

        for detail in misinformed_details:
            system.present_misinformation(
                detail.id,
                f"false_value_{detail.id}",
                MisinformationType.CONTRADICTORY
            )

        # Phase 3: Memory test
        misinformed_correct = 0
        control_correct = 0
        source_confused = 0

        for detail in misinformed_details:
            report = system.test_memory(detail.id)
            if report.correct:
                misinformed_correct += 1
            if report.source_attribution == MemorySource.ORIGINAL_EVENT and report.misinformed:
                source_confused += 1

        for detail in control_details:
            report = system.test_memory(detail.id)
            if report.correct:
                control_correct += 1

        n_mis = len(misinformed_details)
        n_con = len(control_details)

        return {
            'control_accuracy': control_correct / n_con if n_con > 0 else 0,
            'misinformed_accuracy': misinformed_correct / n_mis if n_mis > 0 else 0,
            'misinformation_effect': (control_correct / n_con if n_con > 0 else 0) - (misinformed_correct / n_mis if n_mis > 0 else 0),
            'source_confusion': source_confused / n_mis if n_mis > 0 else 0
        }

    def run_misinformation_type_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare different types of misinformation."""
        results = {}

        for misinfo_type in MisinformationType:
            system = MisinformationSystem()

            details = []
            for i in range(10):
                detail = system.encode_event(f"detail_{i}", f"original_{i}")
                details.append(detail)

            # All misinformed
            for detail in details:
                system.present_misinformation(
                    detail.id,
                    f"false_{detail.id}",
                    misinfo_type
                )

            # Test
            correct = sum(1 for d in details if system.test_memory(d.id).correct)

            results[misinfo_type.name] = 1 - correct / 10  # Misinformation acceptance rate

        return results

    def run_source_credibility_test(
        self
    ) -> Dict[str, Any]:
        """Test effect of source credibility."""
        credibility_levels = [0.3, 0.5, 0.7, 0.9]
        results = {}

        for cred in credibility_levels:
            system = MisinformationSystem()

            details = []
            for i in range(10):
                detail = system.encode_event(f"detail_{i}", f"original_{i}")
                details.append(detail)

            for detail in details:
                system.present_misinformation(
                    detail.id,
                    f"false_{detail.id}",
                    MisinformationType.CONTRADICTORY,
                    SourceType.NARRATIVE,
                    cred
                )

            misinformed = sum(1 for d in details if system.test_memory(d.id).misinformed)

            results[f"credibility_{cred}"] = misinformed / 10

        return results

    def run_leading_question_test(
        self
    ) -> Dict[str, Any]:
        """Test leading question effect."""
        system = MisinformationSystem()

        # Encode event
        stop_sign = system.encode_event("traffic_sign", "stop_sign")
        car_color = system.encode_event("car_color", "blue")

        # Leading questions
        system.present_misinformation(
            stop_sign.id,
            "yield_sign",
            MisinformationType.SUBTLE,
            SourceType.QUESTION,  # Embedded in question
            0.6
        )

        # Test
        sign_report = system.test_memory(stop_sign.id)
        color_report = system.test_memory(car_color.id)

        return {
            'misled_item_correct': sign_report.correct,
            'control_item_correct': color_report.correct,
            'leading_question_effect': color_report.correct and not sign_report.correct
        }


# ============================================================================
# MISINFORMATION ENGINE
# ============================================================================

class MisinformationEngine:
    """
    Complete misinformation effect engine.

    "Ba'el's memory malleability engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = MisinformationParadigm()
        self._system = MisinformationSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Event encoding

    def encode_event(
        self,
        description: str,
        value: str
    ) -> EventDetail:
        """Encode an event detail."""
        return self._system.encode_event(description, value)

    # Misinformation

    def present_misinformation(
        self,
        detail_id: str,
        false_value: str,
        misinfo_type: MisinformationType = MisinformationType.CONTRADICTORY
    ) -> MisinformationItem:
        """Present misinformation."""
        return self._system.present_misinformation(
            detail_id, false_value, misinfo_type
        )

    # Memory test

    def test_memory(
        self,
        detail_id: str
    ) -> MemoryReport:
        """Test memory."""
        return self._system.test_memory(detail_id)

    # Experiments

    def run_standard_experiment(
        self,
        n_details: int = 20
    ) -> Dict[str, Any]:
        """Run standard experiment."""
        result = self._paradigm.run_standard_experiment(n_details)
        self._experiment_results.append(result)
        return result

    def compare_misinformation_types(
        self
    ) -> Dict[str, Any]:
        """Compare misinformation types."""
        return self._paradigm.run_misinformation_type_comparison()

    def test_source_credibility(
        self
    ) -> Dict[str, Any]:
        """Test source credibility."""
        return self._paradigm.run_source_credibility_test()

    def test_leading_questions(
        self
    ) -> Dict[str, Any]:
        """Test leading questions."""
        return self._paradigm.run_leading_question_test()

    def run_eyewitness_simulation(
        self
    ) -> Dict[str, Any]:
        """Simulate eyewitness misinformation scenario."""
        system = MisinformationSystem()

        # Witness sees crime
        perpetrator = system.encode_event("perpetrator_shirt", "red")
        weapon = system.encode_event("weapon", "knife")
        vehicle = system.encode_event("getaway_vehicle", "black_sedan")

        # Police interview (with misinformation)
        system.present_misinformation(
            perpetrator.id,
            "blue",
            MisinformationType.SUBTLE,
            SourceType.QUESTION,
            0.8  # High credibility source
        )

        # Later memory test
        shirt_report = system.test_memory(perpetrator.id)
        weapon_report = system.test_memory(weapon.id)
        vehicle_report = system.test_memory(vehicle.id)

        return {
            'perpetrator_correct': shirt_report.correct,
            'perpetrator_misled': shirt_report.misinformed,
            'weapon_correct': weapon_report.correct,
            'vehicle_correct': vehicle_report.correct,
            'implications': 'Post-event information from authorities can contaminate witness memory'
        }

    # Analysis

    def get_metrics(self) -> MisinformationMetrics:
        """Get misinformation metrics."""
        if not self._experiment_results:
            self.run_standard_experiment()

        last = self._experiment_results[-1]

        return MisinformationMetrics(
            control_accuracy=last['control_accuracy'],
            misinformed_accuracy=last['misinformed_accuracy'],
            misinformation_effect=last['misinformation_effect'],
            source_confusion=last['source_confusion']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'details': len(self._system._details),
            'misinformation': len(self._system._misinformation),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_misinformation_engine() -> MisinformationEngine:
    """Create misinformation engine."""
    return MisinformationEngine()


def demonstrate_misinformation() -> Dict[str, Any]:
    """Demonstrate misinformation effect."""
    engine = create_misinformation_engine()

    # Standard experiment
    standard = engine.run_standard_experiment(20)

    # Type comparison
    types = engine.compare_misinformation_types()

    # Credibility test
    credibility = engine.test_source_credibility()

    # Leading questions
    leading = engine.test_leading_questions()

    # Eyewitness simulation
    eyewitness = engine.run_eyewitness_simulation()

    return {
        'misinformation_effect': {
            'control': f"{standard['control_accuracy']:.0%}",
            'misinformed': f"{standard['misinformed_accuracy']:.0%}",
            'effect': f"{standard['misinformation_effect']:.0%}",
            'source_confusion': f"{standard['source_confusion']:.0%}"
        },
        'by_type': {
            t: f"{rate:.0%}" for t, rate in types.items()
        },
        'credibility_effect': {
            level: f"{rate:.0%}" for level, rate in credibility.items()
        },
        'eyewitness': {
            'perpetrator_correct': eyewitness['perpetrator_correct'],
            'contaminated': eyewitness['perpetrator_misled']
        },
        'interpretation': (
            f"Misinformation effect: {standard['misinformation_effect']:.0%}. "
            f"Post-event information can systematically distort memory."
        )
    }


def get_misinformation_facts() -> Dict[str, str]:
    """Get facts about misinformation effect."""
    return {
        'loftus_palmer_1974': 'Classic car crash study',
        'loftus_1979': 'Systematic misinformation research',
        'eyewitness': 'Major implications for eyewitness testimony',
        'source_monitoring': 'Failure to attribute memory source correctly',
        'discrepancy_detection': 'Blatant changes more likely rejected',
        'warnings': 'Warnings reduce but don\'t eliminate effect',
        'false_memory': 'Can create entirely false memories',
        'malleability': 'Memory is reconstructive, not reproductive'
    }
