"""
BAEL Verbatim-Gist Memory Engine
==================================

Fuzzy Trace Theory - parallel verbatim and gist memory traces.
Brainerd & Reyna's dual-trace model.

"Ba'el remembers both word and meaning." — Ba'el
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

logger = logging.getLogger("BAEL.VerbatimGist")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class TraceType(Enum):
    """Types of memory traces."""
    VERBATIM = auto()   # Exact surface form
    GIST = auto()       # Semantic meaning


class MaterialType(Enum):
    """Types of material."""
    WORDS = auto()
    NUMBERS = auto()
    SENTENCES = auto()
    STORIES = auto()


class TaskType(Enum):
    """Types of memory tasks."""
    RECOGNITION = auto()
    FREE_RECALL = auto()
    CUED_RECALL = auto()


@dataclass
class VerbatimTrace:
    """
    Verbatim memory trace - exact form.
    """
    id: str
    surface_form: str
    encoding_strength: float
    decay_rate: float


@dataclass
class GistTrace:
    """
    Gist memory trace - semantic meaning.
    """
    id: str
    meaning: str
    category: str
    encoding_strength: float
    decay_rate: float


@dataclass
class DualTrace:
    """
    Combined verbatim and gist trace.
    """
    item_id: str
    verbatim: VerbatimTrace
    gist: GistTrace
    age_minutes: float


@dataclass
class VerbatimGistMetrics:
    """
    Verbatim-gist metrics.
    """
    verbatim_retention: float
    gist_retention: float
    gist_based_false_alarms: float
    dissociation_index: float


# ============================================================================
# FUZZY TRACE MODEL
# ============================================================================

class FuzzyTraceModel:
    """
    Fuzzy Trace Theory model.

    "Ba'el's dual traces." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Verbatim parameters
        self._verbatim_encoding = 0.8
        self._verbatim_decay = 0.15  # Fast decay

        # Gist parameters
        self._gist_encoding = 0.7
        self._gist_decay = 0.03  # Slow decay

        # Retrieval parameters
        self._verbatim_threshold = 0.4
        self._gist_threshold = 0.3

        self._lock = threading.RLock()

    def encode_verbatim(
        self,
        surface_form: str
    ) -> VerbatimTrace:
        """Encode verbatim trace."""
        # Verbatim encoding varies with distinctiveness
        distinctiveness = len(set(surface_form)) / len(surface_form) if surface_form else 0.5
        strength = self._verbatim_encoding * (0.8 + 0.4 * distinctiveness)

        return VerbatimTrace(
            id=f"verb_{hash(surface_form) % 10000}",
            surface_form=surface_form,
            encoding_strength=min(1.0, strength),
            decay_rate=self._verbatim_decay
        )

    def encode_gist(
        self,
        meaning: str,
        category: str
    ) -> GistTrace:
        """Encode gist trace."""
        strength = self._gist_encoding

        return GistTrace(
            id=f"gist_{hash(meaning) % 10000}",
            meaning=meaning,
            category=category,
            encoding_strength=strength,
            decay_rate=self._gist_decay
        )

    def calculate_retention(
        self,
        trace_type: TraceType,
        initial_strength: float,
        decay_rate: float,
        age_minutes: float
    ) -> float:
        """Calculate trace retention."""
        hours = age_minutes / 60
        retention = initial_strength * math.exp(-decay_rate * math.sqrt(hours))
        return max(0.05, retention)

    def retrieval_probability(
        self,
        trace_type: TraceType,
        strength: float
    ) -> float:
        """Calculate retrieval probability."""
        threshold = self._verbatim_threshold if trace_type == TraceType.VERBATIM else self._gist_threshold

        if strength < threshold:
            return 0.1 * (strength / threshold)
        else:
            return 0.5 + 0.5 * ((strength - threshold) / (1 - threshold))


# ============================================================================
# VERBATIM-GIST MEMORY SYSTEM
# ============================================================================

class VerbatimGistMemory:
    """
    Verbatim-gist memory system.

    "Ba'el's parallel traces." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = FuzzyTraceModel()

        self._items: Dict[str, Dict[str, Any]] = {}
        self._traces: Dict[str, DualTrace] = {}

        self._item_counter = 0
        self._encode_time: float = time.time()

        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._item_counter += 1
        return f"item_{self._item_counter}"

    def encode_item(
        self,
        surface_form: str,
        meaning: str,
        category: str
    ) -> str:
        """Encode an item with both traces."""
        item_id = self._generate_id()

        self._items[item_id] = {
            'surface': surface_form,
            'meaning': meaning,
            'category': category
        }

        verbatim = self._model.encode_verbatim(surface_form)
        gist = self._model.encode_gist(meaning, category)

        self._traces[item_id] = DualTrace(
            item_id=item_id,
            verbatim=verbatim,
            gist=gist,
            age_minutes=0
        )

        return item_id

    def probe_memory(
        self,
        probe: str,
        age_minutes: float
    ) -> Dict[str, Any]:
        """Probe memory with a test item."""
        # Check verbatim match
        verbatim_match = None
        gist_match = None

        for item_id, info in self._items.items():
            trace = self._traces[item_id]
            trace.age_minutes = age_minutes

            # Verbatim match?
            if info['surface'] == probe:
                v_retention = self._model.calculate_retention(
                    TraceType.VERBATIM,
                    trace.verbatim.encoding_strength,
                    trace.verbatim.decay_rate,
                    age_minutes
                )
                v_prob = self._model.retrieval_probability(TraceType.VERBATIM, v_retention)

                if random.random() < v_prob:
                    verbatim_match = {
                        'item_id': item_id,
                        'type': 'verbatim',
                        'strength': v_retention
                    }
                    break

        # Gist match (even if no verbatim match)
        if not verbatim_match:
            for item_id, info in self._items.items():
                trace = self._traces[item_id]

                # Check semantic similarity (simplified)
                if info['category'] in probe or probe in info['meaning']:
                    g_retention = self._model.calculate_retention(
                        TraceType.GIST,
                        trace.gist.encoding_strength,
                        trace.gist.decay_rate,
                        age_minutes
                    )
                    g_prob = self._model.retrieval_probability(TraceType.GIST, g_retention)

                    if random.random() < g_prob:
                        gist_match = {
                            'item_id': item_id,
                            'type': 'gist',
                            'strength': g_retention
                        }
                        break

        return {
            'probe': probe,
            'verbatim_match': verbatim_match,
            'gist_match': gist_match,
            'recognized': verbatim_match is not None or gist_match is not None
        }

    def test_recognition(
        self,
        item_id: str,
        age_minutes: float
    ) -> Dict[str, Any]:
        """Test recognition of a specific item."""
        trace = self._traces.get(item_id)
        if not trace:
            return {'recognized': False}

        trace.age_minutes = age_minutes

        # Verbatim retention
        v_retention = self._model.calculate_retention(
            TraceType.VERBATIM,
            trace.verbatim.encoding_strength,
            trace.verbatim.decay_rate,
            age_minutes
        )

        # Gist retention
        g_retention = self._model.calculate_retention(
            TraceType.GIST,
            trace.gist.encoding_strength,
            trace.gist.decay_rate,
            age_minutes
        )

        v_recognized = random.random() < self._model.retrieval_probability(TraceType.VERBATIM, v_retention)
        g_recognized = random.random() < self._model.retrieval_probability(TraceType.GIST, g_retention)

        return {
            'item_id': item_id,
            'verbatim_retention': v_retention,
            'gist_retention': g_retention,
            'verbatim_recognized': v_recognized,
            'gist_recognized': g_recognized,
            'recognized': v_recognized or g_recognized
        }


# ============================================================================
# EXPERIMENTAL PARADIGM
# ============================================================================

class VerbatimGistParadigm:
    """
    Verbatim-gist experimental paradigm.

    "Ba'el's trace dissociation." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_drm_paradigm(
        self,
        n_lists: int = 5,
        words_per_list: int = 12,
        delay_minutes: float = 30
    ) -> Dict[str, Any]:
        """Run DRM (Deese-Roediger-McDermott) false memory paradigm."""
        memory = VerbatimGistMemory()

        # Create word lists with semantic theme
        categories = ['sleep', 'cold', 'sweet', 'slow', 'high']

        studied_words = []
        lures = []  # Critical lures (theme words not presented)

        for i, category in enumerate(categories[:n_lists]):
            # Study words related to theme
            for j in range(words_per_list):
                word = f"{category}_word_{j}"
                memory.encode_item(word, category, category)
                studied_words.append(word)

            # Create critical lure
            lures.append(f"LURE_{category}")

        # Test phase
        studied_hits = 0
        lure_false_alarms = 0

        for word in studied_words:
            result = memory.probe_memory(word, delay_minutes)
            if result['verbatim_match']:
                studied_hits += 1

        for lure in lures:
            # Lures match gist but not verbatim
            result = memory.probe_memory(lure, delay_minutes)
            if result['gist_match'] and not result['verbatim_match']:
                lure_false_alarms += 1

        hit_rate = studied_hits / len(studied_words) if studied_words else 0
        false_alarm_rate = lure_false_alarms / len(lures) if lures else 0

        return {
            'n_lists': n_lists,
            'delay_minutes': delay_minutes,
            'hit_rate': hit_rate,
            'critical_lure_fa': false_alarm_rate,
            'gist_based_errors': false_alarm_rate > 0.3
        }

    def run_retention_interval_study(
        self,
        intervals: List[float] = None
    ) -> Dict[str, Any]:
        """Compare verbatim vs gist across retention intervals."""
        if intervals is None:
            intervals = [5, 60, 1440, 10080]  # 5min, 1h, 1day, 1week

        results = {}

        for interval in intervals:
            memory = VerbatimGistMemory()

            # Encode items
            for i in range(20):
                memory.encode_item(f"word_{i}", f"meaning_{i}", "category")

            # Test retention
            v_retained = 0
            g_retained = 0

            for item_id in memory._traces.keys():
                result = memory.test_recognition(item_id, interval)
                if result['verbatim_recognized']:
                    v_retained += 1
                if result['gist_recognized']:
                    g_retained += 1

            total = len(memory._traces)
            results[f"{interval}min"] = {
                'verbatim': v_retained / total if total > 0 else 0,
                'gist': g_retained / total if total > 0 else 0
            }

        return results

    def run_developmental_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare fuzzy trace patterns (simulated age groups)."""
        # Children: stronger verbatim, weaker gist
        # Adults: weaker verbatim, stronger gist

        results = {}

        for age_group, (v_mult, g_mult) in [
            ('children', (1.2, 0.7)),
            ('adults', (0.9, 1.1)),
            ('elderly', (0.7, 1.0))
        ]:
            memory = VerbatimGistMemory()

            # Modify trace strengths
            original_v = memory._model._verbatim_encoding
            original_g = memory._model._gist_encoding

            memory._model._verbatim_encoding = original_v * v_mult
            memory._model._gist_encoding = original_g * g_mult

            # Encode and test
            for i in range(15):
                memory.encode_item(f"word_{i}", "meaning", "category")

            v_correct = 0
            g_errors = 0

            for item_id in memory._traces.keys():
                result = memory.test_recognition(item_id, 60)
                if result['verbatim_recognized']:
                    v_correct += 1

            # Test lures
            for i in range(5):
                result = memory.probe_memory(f"LURE_category", 60)
                if result['gist_match']:
                    g_errors += 1

            results[age_group] = {
                'verbatim_accuracy': v_correct / 15,
                'gist_false_alarms': g_errors / 5
            }

            memory._model._verbatim_encoding = original_v
            memory._model._gist_encoding = original_g

        return results


# ============================================================================
# VERBATIM-GIST ENGINE
# ============================================================================

class VerbatimGistEngine:
    """
    Complete verbatim-gist memory engine.

    "Ba'el's dual-trace system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = VerbatimGistParadigm()
        self._memory = VerbatimGistMemory()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Encoding

    def encode(
        self,
        surface: str,
        meaning: str,
        category: str
    ) -> str:
        """Encode an item."""
        return self._memory.encode_item(surface, meaning, category)

    # Retrieval

    def probe(
        self,
        probe: str,
        age_minutes: float
    ) -> Dict[str, Any]:
        """Probe memory."""
        return self._memory.probe_memory(probe, age_minutes)

    def test_recognition(
        self,
        item_id: str,
        age_minutes: float
    ) -> Dict[str, Any]:
        """Test recognition."""
        return self._memory.test_recognition(item_id, age_minutes)

    # Experiments

    def run_drm_paradigm(
        self,
        n_lists: int = 5
    ) -> Dict[str, Any]:
        """Run DRM false memory paradigm."""
        result = self._paradigm.run_drm_paradigm(n_lists, 12, 30)
        self._experiment_results.append(result)
        return result

    def run_retention_study(
        self
    ) -> Dict[str, Any]:
        """Run retention interval study."""
        return self._paradigm.run_retention_interval_study()

    def run_developmental_comparison(
        self
    ) -> Dict[str, Any]:
        """Run developmental comparison."""
        return self._paradigm.run_developmental_comparison()

    def run_dissociation_test(
        self
    ) -> Dict[str, Any]:
        """Test verbatim-gist dissociation."""
        memory = VerbatimGistMemory()

        # Encode items
        for i in range(20):
            memory.encode_item(f"exact_word_{i}", f"meaning_{i}", "semantic_cat")

        # Immediate test
        immediate_v = 0
        immediate_g = 0
        for item_id in memory._traces.keys():
            result = memory.test_recognition(item_id, 1)
            if result['verbatim_recognized']:
                immediate_v += 1
            if result['gist_recognized']:
                immediate_g += 1

        # Delayed test (new memory to simulate)
        memory2 = VerbatimGistMemory()
        for i in range(20):
            memory2.encode_item(f"exact_word_{i}", f"meaning_{i}", "semantic_cat")

        delayed_v = 0
        delayed_g = 0
        for item_id in memory2._traces.keys():
            result = memory2.test_recognition(item_id, 1440)
            if result['verbatim_recognized']:
                delayed_v += 1
            if result['gist_recognized']:
                delayed_g += 1

        total = 20

        return {
            'immediate': {
                'verbatim': immediate_v / total,
                'gist': immediate_g / total
            },
            'delayed_1day': {
                'verbatim': delayed_v / total,
                'gist': delayed_g / total
            },
            'dissociation': (immediate_v / total) - (delayed_v / total) > 0.2 and (immediate_g / total) - (delayed_g / total) < 0.1
        }

    # Analysis

    def get_metrics(self) -> VerbatimGistMetrics:
        """Get verbatim-gist metrics."""
        if not self._experiment_results:
            self.run_drm_paradigm(5)

        last = self._experiment_results[-1]

        return VerbatimGistMetrics(
            verbatim_retention=last['hit_rate'],
            gist_retention=0.8,  # Would need proper tracking
            gist_based_false_alarms=last['critical_lure_fa'],
            dissociation_index=last['hit_rate'] - last['critical_lure_fa']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'items': len(self._memory._items),
            'traces': len(self._memory._traces),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_verbatim_gist_engine() -> VerbatimGistEngine:
    """Create verbatim-gist engine."""
    return VerbatimGistEngine()


def demonstrate_verbatim_gist() -> Dict[str, Any]:
    """Demonstrate verbatim-gist memory."""
    engine = create_verbatim_gist_engine()

    # DRM paradigm
    drm = engine.run_drm_paradigm(5)

    # Retention study
    retention = engine.run_retention_study()

    # Developmental comparison
    developmental = engine.run_developmental_comparison()

    # Dissociation test
    dissociation = engine.run_dissociation_test()

    return {
        'drm_paradigm': {
            'hit_rate': f"{drm['hit_rate']:.0%}",
            'critical_lure_fa': f"{drm['critical_lure_fa']:.0%}",
            'gist_based_errors': drm['gist_based_errors']
        },
        'retention_intervals': {
            interval: f"V:{data['verbatim']:.0%} G:{data['gist']:.0%}"
            for interval, data in retention.items()
        },
        'developmental': {
            group: f"V:{data['verbatim_accuracy']:.0%} FA:{data['gist_false_alarms']:.0%}"
            for group, data in developmental.items()
        },
        'dissociation': {
            'immediate_v': f"{dissociation['immediate']['verbatim']:.0%}",
            'delayed_v': f"{dissociation['delayed_1day']['verbatim']:.0%}",
            'dissociation_found': dissociation['dissociation']
        },
        'interpretation': (
            f"Hit rate: {drm['hit_rate']:.0%}, Lure FA: {drm['critical_lure_fa']:.0%}. "
            f"Gist traces lead to false memories for semantically related lures."
        )
    }


def get_verbatim_gist_facts() -> Dict[str, str]:
    """Get facts about verbatim-gist memory."""
    return {
        'brainerd_reyna': 'Fuzzy Trace Theory originators',
        'dual_traces': 'Parallel verbatim and gist representations',
        'verbatim_fast_decay': 'Verbatim traces decay faster',
        'gist_persistence': 'Gist traces are more durable',
        'false_memory': 'Gist-based recognition causes false alarms',
        'drm_paradigm': 'Classic demonstration of gist-based errors',
        'developmental': 'Children rely more on verbatim',
        'intuition': 'Gist basis for intuitive reasoning'
    }
