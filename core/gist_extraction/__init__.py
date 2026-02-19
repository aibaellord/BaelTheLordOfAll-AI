"""
BAEL Gist Extraction Engine
=============================

Extracting the essence of experiences.
Fuzzy-trace theory and gist memory.

"Ba'el preserves the essence." — Ba'el
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

logger = logging.getLogger("BAEL.GistExtraction")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class TraceType(Enum):
    """Type of memory trace."""
    VERBATIM = auto()    # Exact surface details
    GIST = auto()        # Meaning/essence


class GistLevel(Enum):
    """Level of gist abstraction."""
    SURFACE = auto()     # Near-verbatim
    BASIC = auto()       # Basic meaning
    ABSTRACT = auto()    # High-level theme
    SCHEMATIC = auto()   # Schema-level


class ContentType(Enum):
    """Type of content."""
    NARRATIVE = auto()
    NUMERICAL = auto()
    SPATIAL = auto()
    PROCEDURAL = auto()


class ExtractionStrategy(Enum):
    """Strategy for gist extraction."""
    BOTTOM_UP = auto()    # From details to meaning
    TOP_DOWN = auto()     # Schema-guided
    INTERACTIVE = auto()  # Both


@dataclass
class Experience:
    """
    An experience to encode.
    """
    id: str
    content: str
    content_type: ContentType
    details: Dict[str, Any]
    themes: List[str]
    emotional_intensity: float


@dataclass
class VerbatimTrace:
    """
    A verbatim memory trace.
    """
    experience_id: str
    exact_content: str
    surface_features: Dict[str, Any]
    encoding_time: float
    decay_rate: float


@dataclass
class GistTrace:
    """
    A gist memory trace.
    """
    experience_id: str
    meaning: str
    themes: List[str]
    level: GistLevel
    confidence: float


@dataclass
class MemoryTest:
    """
    A memory test item.
    """
    id: str
    probe: str
    correct_answer: str
    requires_verbatim: bool
    requires_gist: bool


@dataclass
class RecognitionResult:
    """
    Result of recognition.
    """
    test_id: str
    response: str
    correct: bool
    used_verbatim: bool
    used_gist: bool
    false_memory: bool


@dataclass
class GistMetrics:
    """
    Gist extraction metrics.
    """
    verbatim_retention: float
    gist_retention: float
    verbatim_decay_rate: float
    gist_stability: float
    false_memory_rate: float


# ============================================================================
# GIST EXTRACTION MODEL
# ============================================================================

class GistExtractionModel:
    """
    Model of gist extraction (fuzzy-trace theory).

    "Ba'el's essence model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Encoding parameters
        self._verbatim_strength = 0.8
        self._gist_strength = 0.9

        # Decay parameters
        self._verbatim_decay = 0.15     # Per time unit
        self._gist_decay = 0.02         # Much slower

        # Retrieval parameters
        self._verbatim_threshold = 0.5
        self._gist_threshold = 0.3

        # False memory parameters
        self._gist_false_memory = 0.20  # Rate of gist-consistent false memories

        self._lock = threading.RLock()

    def extract_gist(
        self,
        experience: Experience,
        strategy: ExtractionStrategy
    ) -> Tuple[GistLevel, List[str]]:
        """Extract gist from experience."""
        # Strategy affects level
        if strategy == ExtractionStrategy.TOP_DOWN:
            level = GistLevel.SCHEMATIC
        elif strategy == ExtractionStrategy.BOTTOM_UP:
            level = GistLevel.BASIC
        else:
            level = GistLevel.ABSTRACT

        # Extract themes
        themes = experience.themes.copy()

        # Add inferred themes based on content type
        if experience.content_type == ContentType.NARRATIVE:
            themes.append("story")
        elif experience.content_type == ContentType.NUMERICAL:
            themes.append("quantities")

        return level, themes

    def calculate_verbatim_retention(
        self,
        time_elapsed: float,
        initial_strength: float = None
    ) -> float:
        """Calculate verbatim retention."""
        if initial_strength is None:
            initial_strength = self._verbatim_strength

        retention = initial_strength * math.exp(-self._verbatim_decay * time_elapsed)
        return max(0.0, retention)

    def calculate_gist_retention(
        self,
        time_elapsed: float,
        initial_strength: float = None
    ) -> float:
        """Calculate gist retention."""
        if initial_strength is None:
            initial_strength = self._gist_strength

        retention = initial_strength * math.exp(-self._gist_decay * time_elapsed)
        return max(0.0, retention)

    def calculate_false_memory_probability(
        self,
        gist_strength: float,
        verbatim_strength: float,
        semantic_similarity: float
    ) -> float:
        """Calculate false memory probability."""
        # False memories more likely when:
        # - Gist is strong
        # - Verbatim is weak
        # - Item is semantically similar

        if verbatim_strength > self._verbatim_threshold:
            # Verbatim can reject false items
            return self._gist_false_memory * 0.3

        prob = self._gist_false_memory * gist_strength * semantic_similarity
        return min(0.8, prob)

    def should_use_gist(
        self,
        verbatim_available: bool,
        requires_verbatim: bool
    ) -> bool:
        """Determine if gist should be used."""
        if requires_verbatim and verbatim_available:
            return False  # Use verbatim

        return True  # Default to gist


# ============================================================================
# GIST EXTRACTION SYSTEM
# ============================================================================

class GistExtractionSystem:
    """
    Gist extraction system.

    "Ba'el's essence system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = GistExtractionModel()

        self._experiences: Dict[str, Experience] = {}
        self._verbatim_traces: Dict[str, VerbatimTrace] = {}
        self._gist_traces: Dict[str, GistTrace] = {}

        self._start_time = time.time()

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def _current_time(self) -> float:
        return time.time() - self._start_time

    def encode_experience(
        self,
        content: str,
        content_type: ContentType,
        details: Dict[str, Any],
        themes: List[str]
    ) -> Tuple[Experience, VerbatimTrace, GistTrace]:
        """Encode an experience."""
        experience = Experience(
            id=self._generate_id(),
            content=content,
            content_type=content_type,
            details=details,
            themes=themes,
            emotional_intensity=random.uniform(0.3, 0.7)
        )

        self._experiences[experience.id] = experience

        # Create verbatim trace
        verbatim = VerbatimTrace(
            experience_id=experience.id,
            exact_content=content,
            surface_features=details,
            encoding_time=self._current_time(),
            decay_rate=self._model._verbatim_decay
        )

        self._verbatim_traces[experience.id] = verbatim

        # Extract gist
        level, extracted_themes = self._model.extract_gist(
            experience, ExtractionStrategy.INTERACTIVE
        )

        gist = GistTrace(
            experience_id=experience.id,
            meaning=f"Event about {', '.join(themes)}",
            themes=extracted_themes,
            level=level,
            confidence=random.uniform(0.7, 0.95)
        )

        self._gist_traces[experience.id] = gist

        return experience, verbatim, gist

    def test_recognition(
        self,
        experience_id: str,
        probe: str,
        is_old: bool,
        requires_verbatim: bool = False
    ) -> RecognitionResult:
        """Test recognition."""
        experience = self._experiences.get(experience_id)
        if not experience:
            return None

        current_time = self._current_time()
        verbatim = self._verbatim_traces.get(experience_id)
        gist = self._gist_traces.get(experience_id)

        # Calculate retention
        time_elapsed = current_time - verbatim.encoding_time

        verbatim_strength = self._model.calculate_verbatim_retention(time_elapsed)
        gist_strength = self._model.calculate_gist_retention(time_elapsed)

        verbatim_available = verbatim_strength > self._model._verbatim_threshold
        gist_available = gist_strength > self._model._gist_threshold

        used_verbatim = False
        used_gist = False
        correct = False
        false_memory = False

        if is_old:
            # Target item
            if verbatim_available and random.random() < verbatim_strength:
                used_verbatim = True
                correct = True
            elif gist_available and random.random() < gist_strength:
                used_gist = True
                correct = True
        else:
            # Lure item
            # Check for false memory
            semantic_sim = random.uniform(0.3, 0.8)  # Simulated similarity

            false_mem_prob = self._model.calculate_false_memory_probability(
                gist_strength, verbatim_strength, semantic_sim
            )

            if random.random() < false_mem_prob:
                false_memory = True
                used_gist = True
                correct = False
            else:
                correct = True  # Correctly rejected

        response = "old" if (correct and is_old) or false_memory else "new"

        return RecognitionResult(
            test_id=self._generate_id(),
            response=response,
            correct=correct and not false_memory,
            used_verbatim=used_verbatim,
            used_gist=used_gist,
            false_memory=false_memory
        )


# ============================================================================
# GIST EXTRACTION PARADIGM
# ============================================================================

class GistExtractionParadigm:
    """
    Gist extraction paradigm.

    "Ba'el's essence study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_drm_paradigm(
        self,
        n_lists: int = 5
    ) -> Dict[str, Any]:
        """Run DRM (Deese-Roediger-McDermott) paradigm."""
        system = GistExtractionSystem()

        # DRM lists (simplified)
        lists = [
            {
                'words': ['bed', 'rest', 'awake', 'tired', 'dream', 'wake'],
                'theme': 'sleep',
                'critical_lure': 'sleep'
            },
            {
                'words': ['nurse', 'sick', 'hospital', 'medicine', 'health'],
                'theme': 'doctor',
                'critical_lure': 'doctor'
            },
            {
                'words': ['hot', 'snow', 'warm', 'winter', 'ice', 'freeze'],
                'theme': 'cold',
                'critical_lure': 'cold'
            },
            {
                'words': ['sour', 'candy', 'sugar', 'bitter', 'taste'],
                'theme': 'sweet',
                'critical_lure': 'sweet'
            },
            {
                'words': ['table', 'sit', 'legs', 'seat', 'desk'],
                'theme': 'chair',
                'critical_lure': 'chair'
            }
        ]

        # Encode lists
        encoded = []
        for lst in lists[:n_lists]:
            for word in lst['words']:
                exp, _, _ = system.encode_experience(
                    word,
                    ContentType.NARRATIVE,
                    {'word': word},
                    [lst['theme']]
                )
                encoded.append(exp)

        # Simulate delay
        time.sleep(0.1)

        # Test
        results = {
            'studied': [],
            'critical_lure': [],
            'unrelated': []
        }

        # Test studied words
        for exp in encoded[:10]:
            result = system.test_recognition(exp.id, exp.content, is_old=True)
            if result:
                results['studied'].append(result.correct)

        # Test critical lures (gist-consistent but not studied)
        for lst in lists[:n_lists]:
            # Create fake experience for lure
            lure_exp, _, _ = system.encode_experience(
                lst['critical_lure'],
                ContentType.NARRATIVE,
                {'word': lst['critical_lure']},
                [lst['theme']]
            )
            result = system.test_recognition(lure_exp.id, lst['critical_lure'], is_old=False)
            if result:
                results['critical_lure'].append(result.false_memory)

        studied_hit = sum(results['studied']) / max(1, len(results['studied']))
        lure_fa = sum(results['critical_lure']) / max(1, len(results['critical_lure']))

        return {
            'studied_hit_rate': studied_hit,
            'critical_lure_fa': lure_fa,
            'gist_false_memory': lure_fa > 0.3,
            'interpretation': 'Gist causes false memories for related lures'
        }

    def run_retention_study(
        self
    ) -> Dict[str, Any]:
        """Study verbatim vs gist retention."""
        system = GistExtractionSystem()
        model = GistExtractionModel()

        # Simulate retention over time
        time_points = [0, 1, 5, 10, 20, 50]

        retention = {}

        for t in time_points:
            verbatim_ret = model.calculate_verbatim_retention(t)
            gist_ret = model.calculate_gist_retention(t)

            retention[f"time_{t}"] = {
                'verbatim': verbatim_ret,
                'gist': gist_ret
            }

        return {
            'retention_curve': retention,
            'verbatim_halflife': math.log(2) / model._verbatim_decay,
            'gist_halflife': math.log(2) / model._gist_decay,
            'interpretation': 'Verbatim decays fast, gist persists'
        }

    def run_developmental_study(
        self
    ) -> Dict[str, Any]:
        """Study developmental differences."""
        # Children rely more on gist
        conditions = {
            'child': {'verbatim_strength': 0.6, 'gist_strength': 0.8},
            'adult': {'verbatim_strength': 0.8, 'gist_strength': 0.9},
            'older_adult': {'verbatim_strength': 0.5, 'gist_strength': 0.85}
        }

        results = {}

        for condition, params in conditions.items():
            system = GistExtractionSystem()
            system._model._verbatim_strength = params['verbatim_strength']
            system._model._gist_strength = params['gist_strength']

            # Encode
            experiences = []
            for i in range(10):
                exp, _, _ = system.encode_experience(
                    f"Event {i}",
                    ContentType.NARRATIVE,
                    {'id': i},
                    ['general']
                )
                experiences.append(exp)

            # Test
            hits = 0
            false_alarms = 0

            for exp in experiences:
                # Test old
                result = system.test_recognition(exp.id, exp.content, is_old=True)
                if result and result.correct:
                    hits += 1

                # Test lure
                result = system.test_recognition(exp.id, "lure", is_old=False)
                if result and result.false_memory:
                    false_alarms += 1

            results[condition] = {
                'hit_rate': hits / len(experiences),
                'false_alarm_rate': false_alarms / len(experiences)
            }

        return {
            'by_age': results,
            'interpretation': 'Verbatim declines with age, gist-based false memories vary'
        }

    def run_inference_study(
        self
    ) -> Dict[str, Any]:
        """Study gist-based inferences."""
        system = GistExtractionSystem()

        # Encode story with inferrable conclusion
        story_parts = [
            "John was getting ready for a trip",
            "He packed his suitcase",
            "He called a taxi to the airport"
        ]

        experiences = []
        for part in story_parts:
            exp, _, _ = system.encode_experience(
                part,
                ContentType.NARRATIVE,
                {},
                ['travel', 'journey']
            )
            experiences.append(exp)

        # Test explicit (studied)
        explicit_result = system.test_recognition(
            experiences[0].id, story_parts[0], is_old=True
        )

        # Test inference (not studied but gist-consistent)
        inference_exp, _, _ = system.encode_experience(
            "John took a flight",
            ContentType.NARRATIVE,
            {},
            ['travel']
        )
        inference_result = system.test_recognition(
            inference_exp.id, "John took a flight", is_old=False
        )

        return {
            'explicit_memory': explicit_result.correct if explicit_result else False,
            'inference_accepted': inference_result.false_memory if inference_result else False,
            'interpretation': 'Gist supports inferences and false memories for consistent info'
        }

    def run_emotional_study(
        self
    ) -> Dict[str, Any]:
        """Study emotional effects on gist."""
        system = GistExtractionSystem()

        conditions = {
            'neutral': {'intensity': 0.3},
            'emotional': {'intensity': 0.8}
        }

        results = {}

        for condition, params in conditions.items():
            experiences = []
            for i in range(10):
                exp, _, _ = system.encode_experience(
                    f"Event {i}",
                    ContentType.NARRATIVE,
                    {'id': i},
                    ['general']
                )
                exp.emotional_intensity = params['intensity']
                experiences.append(exp)

            # Test after delay
            time.sleep(0.1)

            hits = 0
            gist_used = 0

            for exp in experiences:
                result = system.test_recognition(exp.id, exp.content, is_old=True)
                if result:
                    if result.correct:
                        hits += 1
                    if result.used_gist:
                        gist_used += 1

            results[condition] = {
                'hit_rate': hits / len(experiences),
                'gist_use': gist_used / len(experiences)
            }

        return {
            'by_emotion': results,
            'interpretation': 'Emotional content enhances gist extraction'
        }


# ============================================================================
# GIST EXTRACTION ENGINE
# ============================================================================

class GistExtractionEngine:
    """
    Complete gist extraction engine.

    "Ba'el's essence engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = GistExtractionParadigm()
        self._system = GistExtractionSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Encoding operations

    def encode(
        self,
        content: str,
        themes: List[str]
    ) -> Tuple[Experience, VerbatimTrace, GistTrace]:
        """Encode experience."""
        return self._system.encode_experience(
            content, ContentType.NARRATIVE, {}, themes
        )

    def test(
        self,
        experience_id: str,
        probe: str,
        is_old: bool
    ) -> RecognitionResult:
        """Test recognition."""
        return self._system.test_recognition(experience_id, probe, is_old)

    # Experiments

    def run_drm(
        self
    ) -> Dict[str, Any]:
        """Run DRM paradigm."""
        result = self._paradigm.run_drm_paradigm()
        self._experiment_results.append(result)
        return result

    def study_retention(
        self
    ) -> Dict[str, Any]:
        """Study retention."""
        return self._paradigm.run_retention_study()

    def study_development(
        self
    ) -> Dict[str, Any]:
        """Study developmental effects."""
        return self._paradigm.run_developmental_study()

    def study_inference(
        self
    ) -> Dict[str, Any]:
        """Study inferences."""
        return self._paradigm.run_inference_study()

    def study_emotion(
        self
    ) -> Dict[str, Any]:
        """Study emotional effects."""
        return self._paradigm.run_emotional_study()

    # Analysis

    def get_metrics(self) -> GistMetrics:
        """Get metrics."""
        model = self._system._model

        return GistMetrics(
            verbatim_retention=model._verbatim_strength,
            gist_retention=model._gist_strength,
            verbatim_decay_rate=model._verbatim_decay,
            gist_stability=1 - model._gist_decay,
            false_memory_rate=model._gist_false_memory
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'experiences': len(self._system._experiences),
            'verbatim_traces': len(self._system._verbatim_traces),
            'gist_traces': len(self._system._gist_traces)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_gist_extraction_engine() -> GistExtractionEngine:
    """Create gist extraction engine."""
    return GistExtractionEngine()


def demonstrate_gist_extraction() -> Dict[str, Any]:
    """Demonstrate gist extraction."""
    engine = create_gist_extraction_engine()

    # DRM
    drm = engine.run_drm()

    # Retention
    retention = engine.study_retention()

    # Development
    development = engine.study_development()

    # Metrics
    metrics = engine.get_metrics()

    return {
        'drm': {
            'studied_hits': f"{drm['studied_hit_rate']:.0%}",
            'lure_false_alarms': f"{drm['critical_lure_fa']:.0%}"
        },
        'retention': {
            'verbatim_halflife': f"{retention['verbatim_halflife']:.1f}",
            'gist_halflife': f"{retention['gist_halflife']:.1f}"
        },
        'development': {
            k: f"hits: {v['hit_rate']:.0%}, FA: {v['false_alarm_rate']:.0%}"
            for k, v in development['by_age'].items()
        },
        'metrics': {
            'verbatim_retention': f"{metrics.verbatim_retention:.0%}",
            'gist_retention': f"{metrics.gist_retention:.0%}",
            'false_memory_rate': f"{metrics.false_memory_rate:.0%}"
        },
        'interpretation': (
            f"Gist persists, verbatim fades. "
            f"False memory rate: {metrics.false_memory_rate:.0%}. "
            f"Gist supports meaning, causes false memories for related items."
        )
    }


def get_gist_extraction_facts() -> Dict[str, str]:
    """Get facts about gist extraction."""
    return {
        'fuzzy_trace_theory': 'Brainerd & Reyna - parallel traces',
        'verbatim_trace': 'Surface form, exact details',
        'gist_trace': 'Meaning, essence, pattern',
        'decay': 'Verbatim decays fast, gist persists',
        'drm_paradigm': 'False memories for related lures',
        'development': 'Gist extraction develops with age',
        'false_memories': 'Gist causes consistent false memories',
        'applications': 'Education, eyewitness memory, decision making'
    }
