"""
BAEL Attentional Blink Engine
==============================

Temporal attention and the attentional blink phenomenon.
Rapid serial visual processing.

"Ba'el sees through time's gaps." — Ba'el
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
import copy

logger = logging.getLogger("BAEL.AttentionalBlink")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class StimulusType(Enum):
    """Types of stimuli."""
    TARGET = auto()      # Target to detect
    DISTRACTOR = auto()  # Irrelevant item
    PROBE = auto()       # Second target


class ProcessingStage(Enum):
    """Stages of processing."""
    PERCEPTION = auto()    # Sensory processing
    CONSOLIDATION = auto() # Working memory consolidation
    RESPONSE = auto()      # Response generation


@dataclass
class RSVPItem:
    """
    A rapid serial visual presentation item.
    """
    id: str
    content: str
    type: StimulusType
    position: int        # Position in stream
    onset_time: float    # Relative onset time
    duration: float      # Display duration


@dataclass
class RSVPStream:
    """
    A RSVP stream.
    """
    id: str
    items: List[RSVPItem]
    rate: float          # Items per second
    t1_position: int     # First target position
    t2_position: Optional[int]  # Second target position
    lag: Optional[int]   # Lag between T1 and T2


@dataclass
class DetectionResult:
    """
    Result of target detection.
    """
    stream_id: str
    t1_detected: bool
    t2_detected: bool
    t1_response: Optional[str]
    t2_response: Optional[str]
    t1_correct: bool
    t2_correct: bool
    lag: Optional[int]


@dataclass
class BlinkMetrics:
    """
    Metrics for attentional blink.
    """
    t1_accuracy: float
    t2_accuracy_per_lag: Dict[int, float]
    blink_magnitude: float    # Difference between lag-1 and worst lag
    blink_duration: int       # Lag at which recovery occurs
    sparing_effect: bool      # Is lag-1 spared?


@dataclass
class AttentionalWindow:
    """
    The temporal attentional window.
    """
    open: bool
    closing_time: Optional[float]
    recovery_time: Optional[float]
    capacity: int = 1


# ============================================================================
# RSVP GENERATOR
# ============================================================================

class RSVPGenerator:
    """
    Generate RSVP streams.

    "Ba'el creates rapid streams." — Ba'el
    """

    def __init__(self):
        """Initialize generator."""
        self._item_counter = 0
        self._stream_counter = 0

        self._letters = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        self._digits = list('0123456789')

        self._lock = threading.RLock()

    def _generate_item_id(self) -> str:
        self._item_counter += 1
        return f"item_{self._item_counter}"

    def _generate_stream_id(self) -> str:
        self._stream_counter += 1
        return f"stream_{self._stream_counter}"

    def generate_stream(
        self,
        length: int = 20,
        rate: float = 10.0,  # Items per second
        t1_position: int = 5,
        lag: int = 3
    ) -> RSVPStream:
        """Generate RSVP stream."""
        with self._lock:
            items = []
            t2_position = t1_position + lag

            duration = 1.0 / rate

            for i in range(length):
                onset = i * duration

                if i == t1_position:
                    item_type = StimulusType.TARGET
                    content = random.choice(self._digits)
                elif i == t2_position:
                    item_type = StimulusType.PROBE
                    content = random.choice(self._digits)
                else:
                    item_type = StimulusType.DISTRACTOR
                    content = random.choice(self._letters)

                items.append(RSVPItem(
                    id=self._generate_item_id(),
                    content=content,
                    type=item_type,
                    position=i,
                    onset_time=onset,
                    duration=duration
                ))

            return RSVPStream(
                id=self._generate_stream_id(),
                items=items,
                rate=rate,
                t1_position=t1_position,
                t2_position=t2_position if t2_position < length else None,
                lag=lag if t2_position < length else None
            )

    def generate_stream_set(
        self,
        count: int = 10,
        lags: List[int] = None
    ) -> List[RSVPStream]:
        """Generate set of streams with different lags."""
        if lags is None:
            lags = [1, 2, 3, 4, 5, 7, 9]

        streams = []
        for _ in range(count):
            for lag in lags:
                streams.append(self.generate_stream(lag=lag))

        random.shuffle(streams)
        return streams


# ============================================================================
# TEMPORAL ATTENTION MODEL
# ============================================================================

class TemporalAttentionModel:
    """
    Model of temporal attention.
    Based on Chun & Potter's two-stage model.

    "Ba'el attends across time." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Stage 1: Conceptual short-term memory (unlimited capacity)
        # Stage 2: Consolidation (limited capacity)

        self._consolidation_duration = 0.4  # 400ms
        self._window = AttentionalWindow(open=True, closing_time=None, recovery_time=None)

        self._lock = threading.RLock()

    def process_stream(
        self,
        stream: RSVPStream
    ) -> Tuple[bool, bool]:
        """
        Process RSVP stream and return T1, T2 detection.
        """
        with self._lock:
            t1_detected = False
            t2_detected = False

            # Find targets
            t1_item = None
            t2_item = None

            for item in stream.items:
                if item.type == StimulusType.TARGET:
                    t1_item = item
                elif item.type == StimulusType.PROBE:
                    t2_item = item

            if t1_item:
                # T1 detection (high accuracy, ~90%)
                t1_detected = random.random() < 0.9

                if t1_detected and t2_item:
                    # Calculate blink probability based on lag
                    lag = t2_item.position - t1_item.position

                    # Attentional blink function
                    # Lag-1 sparing: high accuracy at lag 1
                    # Blink: low accuracy at lags 2-5
                    # Recovery: accuracy returns at lags 6+

                    if lag == 1:
                        # Lag-1 sparing
                        t2_prob = 0.85
                    elif lag <= 5:
                        # Blink period
                        # Deepest blink around lag 2-3
                        blink_depth = 0.5 - 0.1 * abs(lag - 2.5)
                        t2_prob = 0.5 + blink_depth
                    else:
                        # Recovery
                        t2_prob = 0.8 + 0.02 * (lag - 5)

                    t2_prob = min(0.95, max(0.3, t2_prob))
                    t2_detected = random.random() < t2_prob
                elif not t1_detected and t2_item:
                    # If T1 missed, T2 might be better
                    t2_detected = random.random() < 0.8

            return t1_detected, t2_detected

    def get_blink_probability(
        self,
        lag: int
    ) -> float:
        """Get probability of blink at given lag."""
        if lag == 1:
            return 0.15  # Lag-1 sparing
        elif lag <= 5:
            # Peak blink around lag 2-3
            return 0.3 + 0.2 * (1 - abs(lag - 2.5) / 2.5)
        else:
            # Recovery
            return max(0.1, 0.2 - 0.02 * (lag - 5))


# ============================================================================
# DETECTION ENGINE
# ============================================================================

class DetectionEngine:
    """
    Engine for target detection.

    "Ba'el detects targets." — Ba'el
    """

    def __init__(self, attention_model: TemporalAttentionModel):
        """Initialize engine."""
        self._attention = attention_model
        self._results: List[DetectionResult] = []
        self._lock = threading.RLock()

    def process_stream(
        self,
        stream: RSVPStream
    ) -> DetectionResult:
        """Process stream and generate detection result."""
        with self._lock:
            t1_detected, t2_detected = self._attention.process_stream(stream)

            # Get actual targets
            t1_content = None
            t2_content = None

            for item in stream.items:
                if item.type == StimulusType.TARGET:
                    t1_content = item.content
                elif item.type == StimulusType.PROBE:
                    t2_content = item.content

            # Simulate responses
            if t1_detected:
                t1_response = t1_content
            else:
                t1_response = None

            if t2_detected:
                t2_response = t2_content
            else:
                t2_response = None

            result = DetectionResult(
                stream_id=stream.id,
                t1_detected=t1_detected,
                t2_detected=t2_detected,
                t1_response=t1_response,
                t2_response=t2_response,
                t1_correct=t1_detected,
                t2_correct=t2_detected,
                lag=stream.lag
            )

            self._results.append(result)
            return result

    def get_accuracy_by_lag(self) -> Dict[int, float]:
        """Get T2 accuracy for each lag."""
        lag_correct = defaultdict(list)

        for result in self._results:
            if result.lag is not None and result.t1_correct:
                lag_correct[result.lag].append(result.t2_correct)

        return {
            lag: sum(correct) / len(correct) if correct else 0.0
            for lag, correct in lag_correct.items()
        }


# ============================================================================
# BLINK ANALYZER
# ============================================================================

class BlinkAnalyzer:
    """
    Analyze attentional blink patterns.

    "Ba'el understands the blink." — Ba'el
    """

    def __init__(self, detection_engine: DetectionEngine):
        """Initialize analyzer."""
        self._detection = detection_engine
        self._lock = threading.RLock()

    def compute_metrics(self) -> BlinkMetrics:
        """Compute blink metrics."""
        with self._lock:
            results = self._detection._results

            if not results:
                return BlinkMetrics(
                    t1_accuracy=0.0,
                    t2_accuracy_per_lag={},
                    blink_magnitude=0.0,
                    blink_duration=0,
                    sparing_effect=False
                )

            # T1 accuracy
            t1_correct = sum(1 for r in results if r.t1_correct)
            t1_accuracy = t1_correct / len(results)

            # T2 accuracy by lag (only for T1-correct trials)
            t2_accuracy = self._detection.get_accuracy_by_lag()

            # Blink magnitude
            if t2_accuracy:
                lag1_acc = t2_accuracy.get(1, 0.0)
                min_acc = min(t2_accuracy.values())
                blink_magnitude = lag1_acc - min_acc
            else:
                blink_magnitude = 0.0

            # Blink duration (lag at which recovery starts)
            blink_duration = 0
            for lag in sorted(t2_accuracy.keys()):
                if lag > 1 and t2_accuracy[lag] < t2_accuracy.get(1, 0.0) - 0.1:
                    blink_duration = lag

            # Lag-1 sparing
            sparing = t2_accuracy.get(1, 0.0) > t2_accuracy.get(2, 0.0) + 0.1

            return BlinkMetrics(
                t1_accuracy=t1_accuracy,
                t2_accuracy_per_lag=t2_accuracy,
                blink_magnitude=blink_magnitude,
                blink_duration=blink_duration,
                sparing_effect=sparing
            )


# ============================================================================
# ATTENTIONAL BLINK ENGINE
# ============================================================================

class AttentionalBlinkEngine:
    """
    Complete attentional blink engine.

    "Ba'el's temporal attention." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._generator = RSVPGenerator()
        self._attention_model = TemporalAttentionModel()
        self._detection = DetectionEngine(self._attention_model)
        self._analyzer = BlinkAnalyzer(self._detection)

        self._lock = threading.RLock()

    # Stream generation

    def generate_stream(
        self,
        length: int = 20,
        rate: float = 10.0,
        lag: int = 3
    ) -> RSVPStream:
        """Generate RSVP stream."""
        return self._generator.generate_stream(length, rate, lag=lag)

    def generate_experiment(
        self,
        trials_per_lag: int = 10,
        lags: List[int] = None
    ) -> List[RSVPStream]:
        """Generate full experiment."""
        if lags is None:
            lags = [1, 2, 3, 4, 5, 7, 9]
        return self._generator.generate_stream_set(trials_per_lag, lags)

    # Detection

    def process_stream(
        self,
        stream: RSVPStream
    ) -> DetectionResult:
        """Process single stream."""
        return self._detection.process_stream(stream)

    def run_experiment(
        self,
        streams: List[RSVPStream]
    ) -> List[DetectionResult]:
        """Run experiment with multiple streams."""
        results = []
        for stream in streams:
            results.append(self.process_stream(stream))
        return results

    # Analysis

    def get_metrics(self) -> BlinkMetrics:
        """Get blink metrics."""
        return self._analyzer.compute_metrics()

    def get_accuracy_by_lag(self) -> Dict[int, float]:
        """Get T2 accuracy by lag."""
        return self._detection.get_accuracy_by_lag()

    def get_blink_curve(self) -> List[Tuple[int, float]]:
        """Get the attentional blink curve."""
        acc = self.get_accuracy_by_lag()
        return sorted(acc.items())

    # Model parameters

    def get_blink_probability(
        self,
        lag: int
    ) -> float:
        """Get theoretical blink probability at lag."""
        return self._attention_model.get_blink_probability(lag)

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'streams_processed': len(self._detection._results),
            'metrics': self.get_metrics().__dict__ if self._detection._results else {}
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_attentional_blink_engine() -> AttentionalBlinkEngine:
    """Create attentional blink engine."""
    return AttentionalBlinkEngine()


def run_attentional_blink_experiment(
    trials_per_lag: int = 20,
    lags: List[int] = None
) -> BlinkMetrics:
    """Run complete attentional blink experiment."""
    engine = create_attentional_blink_engine()

    if lags is None:
        lags = [1, 2, 3, 4, 5, 7, 9]

    streams = engine.generate_experiment(trials_per_lag, lags)
    engine.run_experiment(streams)

    return engine.get_metrics()


def get_theoretical_blink_curve(
    lags: List[int] = None
) -> Dict[int, float]:
    """Get theoretical attentional blink curve."""
    engine = create_attentional_blink_engine()

    if lags is None:
        lags = list(range(1, 10))

    return {
        lag: 1 - engine.get_blink_probability(lag)
        for lag in lags
    }
