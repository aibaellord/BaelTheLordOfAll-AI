"""
BAEL Sensory Memory Engine
===========================

Iconic (visual) and echoic (auditory) sensory memory.
Ultra-short-term memory traces.

"Ba'el remembers the fleeting moment." — Ba'el
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

logger = logging.getLogger("BAEL.SensoryMemory")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ModalityType(Enum):
    """Sensory modality types."""
    VISUAL = auto()    # Iconic memory
    AUDITORY = auto()  # Echoic memory
    TACTILE = auto()   # Haptic memory
    OLFACTORY = auto() # Smell memory


class DecayType(Enum):
    """Types of memory decay."""
    EXPONENTIAL = auto()
    LINEAR = auto()
    SUDDEN = auto()  # Mask-based


class CueType(Enum):
    """Types of recall cues."""
    FULL_REPORT = auto()    # Report everything
    PARTIAL_REPORT = auto()  # Cued subset
    DELAYED = auto()        # Delayed cue


@dataclass
class SensoryTrace:
    """
    A sensory memory trace.
    """
    id: str
    modality: ModalityType
    content: Any
    creation_time: float
    intensity: float  # 0-1
    location: Optional[Tuple[float, float]] = None  # For spatial info


@dataclass
class IconicBuffer:
    """
    Iconic (visual) memory buffer.
    ~250-500ms duration, high capacity.
    """
    traces: Dict[str, SensoryTrace]
    capacity: int = 12  # Sperling's estimate
    duration: float = 0.25  # 250ms


@dataclass
class EchoicBuffer:
    """
    Echoic (auditory) memory buffer.
    ~3-4 seconds duration.
    """
    traces: Dict[str, SensoryTrace]
    capacity: int = 8
    duration: float = 3.0  # 3 seconds


@dataclass
class RecallResult:
    """
    Result of sensory memory recall.
    """
    cue_type: CueType
    items_available: int
    items_recalled: int
    accuracy: float
    delay: float


@dataclass
class SensoryMetrics:
    """
    Metrics for sensory memory.
    """
    iconic_capacity: int
    iconic_duration: float
    echoic_capacity: int
    echoic_duration: float
    decay_rate: float
    partial_report_advantage: float


# ============================================================================
# TRACE MANAGER
# ============================================================================

class TraceManager:
    """
    Manage sensory traces.

    "Ba'el holds fleeting impressions." — Ba'el
    """

    def __init__(self):
        """Initialize manager."""
        self._traces: Dict[str, SensoryTrace] = {}
        self._trace_counter = 0
        self._lock = threading.RLock()

    def _generate_trace_id(self) -> str:
        self._trace_counter += 1
        return f"trace_{self._trace_counter}"

    def create_trace(
        self,
        modality: ModalityType,
        content: Any,
        intensity: float = 1.0,
        location: Tuple[float, float] = None
    ) -> SensoryTrace:
        """Create sensory trace."""
        with self._lock:
            trace = SensoryTrace(
                id=self._generate_trace_id(),
                modality=modality,
                content=content,
                creation_time=time.time(),
                intensity=intensity,
                location=location
            )

            self._traces[trace.id] = trace
            return trace

    def get_trace(
        self,
        trace_id: str
    ) -> Optional[SensoryTrace]:
        """Get trace by ID."""
        return self._traces.get(trace_id)

    def get_traces_by_modality(
        self,
        modality: ModalityType
    ) -> List[SensoryTrace]:
        """Get all traces of a modality."""
        return [t for t in self._traces.values() if t.modality == modality]

    def clear_traces(
        self,
        modality: ModalityType = None
    ) -> None:
        """Clear traces."""
        with self._lock:
            if modality is None:
                self._traces.clear()
            else:
                self._traces = {
                    k: v for k, v in self._traces.items()
                    if v.modality != modality
                }


# ============================================================================
# ICONIC MEMORY
# ============================================================================

class IconicMemory:
    """
    Visual sensory memory.
    Based on Sperling (1960).

    "Ba'el's visual echo." — Ba'el
    """

    def __init__(self, trace_manager: TraceManager):
        """Initialize iconic memory."""
        self._trace_manager = trace_manager

        self._capacity = 12  # High capacity
        self._duration = 0.25  # 250ms
        self._decay_rate = 0.95  # Per 100ms

        self._buffer: IconicBuffer = IconicBuffer(
            traces={},
            capacity=self._capacity,
            duration=self._duration
        )

        self._lock = threading.RLock()

    def register_display(
        self,
        items: List[Any],
        locations: List[Tuple[float, float]] = None
    ) -> List[SensoryTrace]:
        """Register visual display."""
        with self._lock:
            # Clear old traces
            self._buffer.traces.clear()

            # Create new traces
            traces = []
            for i, item in enumerate(items):
                loc = locations[i] if locations else None

                trace = self._trace_manager.create_trace(
                    modality=ModalityType.VISUAL,
                    content=item,
                    intensity=1.0,
                    location=loc
                )

                self._buffer.traces[trace.id] = trace
                traces.append(trace)

            return traces

    def decay_traces(
        self,
        elapsed_time: float
    ) -> None:
        """Apply decay to traces."""
        with self._lock:
            # Calculate decay
            decay_steps = elapsed_time / 0.1  # Per 100ms
            decay_factor = self._decay_rate ** decay_steps

            to_remove = []
            for trace_id, trace in self._buffer.traces.items():
                trace.intensity *= decay_factor

                if trace.intensity < 0.1:
                    to_remove.append(trace_id)

            for trace_id in to_remove:
                del self._buffer.traces[trace_id]

    def full_report(self) -> RecallResult:
        """Full report recall."""
        with self._lock:
            available = len(self._buffer.traces)

            # Limited by attention/WM capacity (~4 items)
            recalled = min(available, 4 + random.randint(-1, 1))

            return RecallResult(
                cue_type=CueType.FULL_REPORT,
                items_available=available,
                items_recalled=recalled,
                accuracy=recalled / max(1, available),
                delay=0.0
            )

    def partial_report(
        self,
        cue_location: str,  # 'top', 'middle', 'bottom' or row number
        delay: float = 0.0
    ) -> RecallResult:
        """Partial report with cue."""
        with self._lock:
            # Apply delay decay
            self.decay_traces(delay)

            # Get items in cued location
            all_traces = list(self._buffer.traces.values())

            if not all_traces:
                return RecallResult(
                    cue_type=CueType.PARTIAL_REPORT,
                    items_available=0,
                    items_recalled=0,
                    accuracy=0.0,
                    delay=delay
                )

            # Assume 3 rows
            per_row = len(all_traces) // 3 + 1

            if cue_location == 'top':
                cued = all_traces[:per_row]
            elif cue_location == 'middle':
                cued = all_traces[per_row:2*per_row]
            else:  # bottom
                cued = all_traces[2*per_row:]

            # High accuracy for cued items (if no delay)
            if delay < 0.1:
                accuracy = 0.9
            elif delay < 0.3:
                accuracy = 0.7
            elif delay < 0.5:
                accuracy = 0.5
            else:
                accuracy = 0.33  # Same as full report

            recalled = int(len(cued) * accuracy)

            return RecallResult(
                cue_type=CueType.PARTIAL_REPORT,
                items_available=len(cued),
                items_recalled=recalled,
                accuracy=accuracy,
                delay=delay
            )

    def get_available_count(self) -> int:
        """Get number of available traces."""
        return len(self._buffer.traces)


# ============================================================================
# ECHOIC MEMORY
# ============================================================================

class EchoicMemory:
    """
    Auditory sensory memory.

    "Ba'el's auditory echo." — Ba'el
    """

    def __init__(self, trace_manager: TraceManager):
        """Initialize echoic memory."""
        self._trace_manager = trace_manager

        self._capacity = 8
        self._duration = 3.0  # 3 seconds
        self._decay_rate = 0.9

        self._buffer: EchoicBuffer = EchoicBuffer(
            traces={},
            capacity=self._capacity,
            duration=self._duration
        )

        self._stream: deque = deque(maxlen=100)  # Audio stream

        self._lock = threading.RLock()

    def register_sound(
        self,
        content: Any,
        intensity: float = 1.0
    ) -> SensoryTrace:
        """Register auditory input."""
        with self._lock:
            trace = self._trace_manager.create_trace(
                modality=ModalityType.AUDITORY,
                content=content,
                intensity=intensity
            )

            self._buffer.traces[trace.id] = trace
            self._stream.append(trace)

            # Enforce capacity
            while len(self._buffer.traces) > self._capacity:
                oldest = min(
                    self._buffer.traces.values(),
                    key=lambda t: t.creation_time
                )
                del self._buffer.traces[oldest.id]

            return trace

    def register_stream(
        self,
        sounds: List[Any],
        interval: float = 0.1
    ) -> List[SensoryTrace]:
        """Register stream of sounds."""
        traces = []
        for sound in sounds:
            trace = self.register_sound(sound)
            traces.append(trace)
        return traces

    def decay_traces(
        self,
        elapsed_time: float
    ) -> None:
        """Apply decay to traces."""
        with self._lock:
            decay_factor = self._decay_rate ** (elapsed_time / 1.0)

            to_remove = []
            for trace_id, trace in self._buffer.traces.items():
                trace.intensity *= decay_factor

                if trace.intensity < 0.1:
                    to_remove.append(trace_id)

            for trace_id in to_remove:
                del self._buffer.traces[trace_id]

    def recall(
        self,
        delay: float = 0.0
    ) -> RecallResult:
        """Recall from echoic memory."""
        with self._lock:
            self.decay_traces(delay)

            available = len(self._buffer.traces)

            # Echoic has longer duration but similar capacity limit
            if delay < 1.0:
                accuracy = 0.85
            elif delay < 2.0:
                accuracy = 0.7
            elif delay < 3.0:
                accuracy = 0.5
            else:
                accuracy = 0.2

            recalled = int(available * accuracy)

            return RecallResult(
                cue_type=CueType.FULL_REPORT,
                items_available=available,
                items_recalled=recalled,
                accuracy=accuracy,
                delay=delay
            )

    def get_suffix_effect(
        self,
        suffix_type: str = 'speech'
    ) -> float:
        """
        Get suffix effect - extra sound impairs recall of last item.
        """
        # Suffix effect: speech suffix hurts more than tone
        if suffix_type == 'speech':
            return 0.3  # 30% reduction
        else:
            return 0.1  # 10% reduction

    def get_available_count(self) -> int:
        """Get number of available traces."""
        return len(self._buffer.traces)


# ============================================================================
# HAPTIC MEMORY
# ============================================================================

class HapticMemory:
    """
    Tactile sensory memory.

    "Ba'el feels the lingering touch." — Ba'el
    """

    def __init__(self, trace_manager: TraceManager):
        """Initialize haptic memory."""
        self._trace_manager = trace_manager

        self._capacity = 4
        self._duration = 0.8  # ~800ms

        self._traces: Dict[str, SensoryTrace] = {}
        self._lock = threading.RLock()

    def register_touch(
        self,
        content: Any,
        location: Tuple[float, float] = None,
        intensity: float = 1.0
    ) -> SensoryTrace:
        """Register tactile input."""
        with self._lock:
            trace = self._trace_manager.create_trace(
                modality=ModalityType.TACTILE,
                content=content,
                intensity=intensity,
                location=location
            )

            self._traces[trace.id] = trace

            # Enforce capacity
            while len(self._traces) > self._capacity:
                oldest = min(
                    self._traces.values(),
                    key=lambda t: t.creation_time
                )
                del self._traces[oldest.id]

            return trace

    def recall(
        self,
        delay: float = 0.0
    ) -> RecallResult:
        """Recall from haptic memory."""
        available = len(self._traces)

        if delay < 0.3:
            accuracy = 0.9
        elif delay < 0.6:
            accuracy = 0.6
        else:
            accuracy = 0.2

        recalled = int(available * accuracy)

        return RecallResult(
            cue_type=CueType.FULL_REPORT,
            items_available=available,
            items_recalled=recalled,
            accuracy=accuracy,
            delay=delay
        )


# ============================================================================
# SENSORY MEMORY ENGINE
# ============================================================================

class SensoryMemoryEngine:
    """
    Complete sensory memory engine.

    "Ba'el's sensory registers." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._trace_manager = TraceManager()

        self._iconic = IconicMemory(self._trace_manager)
        self._echoic = EchoicMemory(self._trace_manager)
        self._haptic = HapticMemory(self._trace_manager)

        self._results: List[RecallResult] = []

        self._lock = threading.RLock()

    # Iconic memory

    def present_visual_display(
        self,
        items: List[Any],
        locations: List[Tuple[float, float]] = None
    ) -> List[SensoryTrace]:
        """Present visual display."""
        return self._iconic.register_display(items, locations)

    def iconic_full_report(self) -> RecallResult:
        """Full report from iconic memory."""
        result = self._iconic.full_report()
        self._results.append(result)
        return result

    def iconic_partial_report(
        self,
        cue: str,
        delay: float = 0.0
    ) -> RecallResult:
        """Partial report from iconic memory."""
        result = self._iconic.partial_report(cue, delay)
        self._results.append(result)
        return result

    # Echoic memory

    def present_sound(
        self,
        content: Any,
        intensity: float = 1.0
    ) -> SensoryTrace:
        """Present sound."""
        return self._echoic.register_sound(content, intensity)

    def present_sound_stream(
        self,
        sounds: List[Any]
    ) -> List[SensoryTrace]:
        """Present sound stream."""
        return self._echoic.register_stream(sounds)

    def echoic_recall(
        self,
        delay: float = 0.0
    ) -> RecallResult:
        """Recall from echoic memory."""
        result = self._echoic.recall(delay)
        self._results.append(result)
        return result

    # Haptic memory

    def present_touch(
        self,
        content: Any,
        location: Tuple[float, float] = None
    ) -> SensoryTrace:
        """Present tactile stimulus."""
        return self._haptic.register_touch(content, location)

    def haptic_recall(
        self,
        delay: float = 0.0
    ) -> RecallResult:
        """Recall from haptic memory."""
        result = self._haptic.recall(delay)
        self._results.append(result)
        return result

    # Sperling experiment

    def run_sperling_experiment(
        self,
        display_size: int = 12,
        delays: List[float] = None
    ) -> Dict[float, float]:
        """
        Run Sperling (1960) partial report experiment.
        """
        if delays is None:
            delays = [0.0, 0.1, 0.2, 0.3, 0.5, 1.0]

        results = {}

        for delay in delays:
            # Generate display
            items = [chr(65 + i % 26) for i in range(display_size)]

            # Present
            self.present_visual_display(items)

            # Partial report with delay
            cue = random.choice(['top', 'middle', 'bottom'])
            result = self.iconic_partial_report(cue, delay)

            results[delay] = result.accuracy

        return results

    # Metrics

    def get_metrics(self) -> SensoryMetrics:
        """Get sensory memory metrics."""
        return SensoryMetrics(
            iconic_capacity=self._iconic._capacity,
            iconic_duration=self._iconic._duration,
            echoic_capacity=self._echoic._capacity,
            echoic_duration=self._echoic._duration,
            decay_rate=self._iconic._decay_rate,
            partial_report_advantage=0.3  # Typical advantage
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'iconic_traces': self._iconic.get_available_count(),
            'echoic_traces': self._echoic.get_available_count(),
            'total_recalls': len(self._results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_sensory_memory_engine() -> SensoryMemoryEngine:
    """Create sensory memory engine."""
    return SensoryMemoryEngine()


def run_sperling_experiment(
    display_size: int = 12
) -> Dict[float, float]:
    """Run Sperling partial report experiment."""
    engine = create_sensory_memory_engine()
    return engine.run_sperling_experiment(display_size)


def get_modality_durations() -> Dict[ModalityType, float]:
    """Get typical sensory memory durations."""
    return {
        ModalityType.VISUAL: 0.25,    # 250ms
        ModalityType.AUDITORY: 3.0,   # 3-4 seconds
        ModalityType.TACTILE: 0.8,    # ~800ms
        ModalityType.OLFACTORY: 0.5   # ~500ms (less studied)
    }
