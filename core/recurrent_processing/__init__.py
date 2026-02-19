"""
BAEL Recurrent Processing Theory Engine
========================================

Visual awareness through recurrent processing.
Feedforward vs recurrent dynamics.

"Ba'el achieves awareness through feedback." — Ba'el
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

logger = logging.getLogger("BAEL.RecurrentProcessing")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ProcessingPhase(Enum):
    """Processing phases."""
    FEEDFORWARD = auto()   # Initial sweep
    LOCAL_RECURRENT = auto()  # V1 recurrence
    GLOBAL_RECURRENT = auto() # Fronto-parietal
    CONSOLIDATED = auto()     # Stable representation


class AwarenessLevel(Enum):
    """Levels of awareness."""
    UNCONSCIOUS = auto()
    PRECONSCIOUS = auto()
    PHENOMENAL = auto()     # Basic awareness
    ACCESS = auto()         # Reportable


class MaskingType(Enum):
    """Types of visual masking."""
    FORWARD = auto()       # Mask before target
    BACKWARD = auto()      # Mask after target
    METACONTRAST = auto()  # Surrounding mask
    PATTERN = auto()       # Pattern mask


@dataclass
class VisualInput:
    """
    A visual input.
    """
    id: str
    features: Dict[str, float]
    onset_time: float = field(default_factory=time.time)
    duration: float = 0.05  # 50ms typical
    position: Tuple[float, float] = (0.0, 0.0)
    strength: float = 1.0


@dataclass
class Activation:
    """
    Neural activation state.
    """
    id: str
    level: float
    phase: ProcessingPhase
    timestamp: float = field(default_factory=time.time)


@dataclass
class ProcessingResult:
    """
    Result of processing.
    """
    input_id: str
    feedforward_activation: float
    recurrent_activation: float
    awareness_level: AwarenessLevel
    processing_time: float
    phases_completed: List[ProcessingPhase]
    report_available: bool


@dataclass
class MaskingResult:
    """
    Result of masking.
    """
    target_id: str
    mask_id: str
    masking_type: MaskingType
    soa: float  # Stimulus onset asynchrony
    target_visibility: float
    awareness_achieved: bool


# ============================================================================
# FEEDFORWARD SWEEP
# ============================================================================

class FeedforwardProcessor:
    """
    Feedforward processing sweep.

    "Ba'el's initial sweep." — Ba'el
    """

    def __init__(self):
        """Initialize processor."""
        self._latency = 0.05  # 50ms
        self._lock = threading.RLock()

    def process(
        self,
        visual_input: VisualInput
    ) -> Activation:
        """Run feedforward sweep."""
        with self._lock:
            # Feature extraction
            activation_level = 0.0

            for feature, value in visual_input.features.items():
                # Combine features
                activation_level += value

            # Normalize
            activation_level = min(1.0, activation_level / max(1, len(visual_input.features)))

            # Scale by input strength
            activation_level *= visual_input.strength

            return Activation(
                id=f"ff_{visual_input.id}",
                level=activation_level,
                phase=ProcessingPhase.FEEDFORWARD
            )

    @property
    def latency(self) -> float:
        return self._latency


# ============================================================================
# RECURRENT PROCESSING
# ============================================================================

class RecurrentProcessor:
    """
    Recurrent processing loops.

    "Ba'el's feedback loops." — Ba'el
    """

    def __init__(self):
        """Initialize processor."""
        self._local_latency = 0.08   # 80ms
        self._global_latency = 0.15  # 150ms
        self._amplification = 1.5
        self._lock = threading.RLock()

    def local_recurrence(
        self,
        feedforward: Activation,
        context: Dict[str, float] = None
    ) -> Activation:
        """Run local recurrent processing."""
        with self._lock:
            level = feedforward.level

            # Amplification through local loops
            level *= self._amplification

            # Context modulation
            if context:
                context_boost = sum(context.values()) / len(context)
                level *= (1.0 + context_boost * 0.5)

            level = min(1.0, level)

            return Activation(
                id=f"local_{feedforward.id}",
                level=level,
                phase=ProcessingPhase.LOCAL_RECURRENT
            )

    def global_recurrence(
        self,
        local: Activation,
        attention: float = 0.5
    ) -> Activation:
        """Run global recurrent processing."""
        with self._lock:
            level = local.level

            # Attention amplification
            level *= (1.0 + attention)

            # Stabilization
            level = min(1.0, level)

            return Activation(
                id=f"global_{local.id}",
                level=level,
                phase=ProcessingPhase.GLOBAL_RECURRENT
            )

    @property
    def local_latency(self) -> float:
        return self._local_latency

    @property
    def global_latency(self) -> float:
        return self._global_latency


# ============================================================================
# AWARENESS GATING
# ============================================================================

class AwarenessGate:
    """
    Gate for conscious access.

    "Ba'el gates awareness." — Ba'el
    """

    def __init__(
        self,
        phenomenal_threshold: float = 0.3,
        access_threshold: float = 0.5
    ):
        """Initialize gate."""
        self._phenomenal_threshold = phenomenal_threshold
        self._access_threshold = access_threshold
        self._lock = threading.RLock()

    def evaluate(
        self,
        activation: Activation,
        recurrent_complete: bool
    ) -> AwarenessLevel:
        """Evaluate awareness level."""
        with self._lock:
            level = activation.level

            # Without recurrence, no phenomenal awareness
            if not recurrent_complete:
                if level > 0.1:
                    return AwarenessLevel.PRECONSCIOUS
                return AwarenessLevel.UNCONSCIOUS

            # With recurrence
            if level >= self._access_threshold:
                return AwarenessLevel.ACCESS
            elif level >= self._phenomenal_threshold:
                return AwarenessLevel.PHENOMENAL
            elif level > 0.1:
                return AwarenessLevel.PRECONSCIOUS
            else:
                return AwarenessLevel.UNCONSCIOUS

    def is_reportable(self, awareness: AwarenessLevel) -> bool:
        """Check if awareness level allows report."""
        return awareness == AwarenessLevel.ACCESS


# ============================================================================
# VISUAL MASKING
# ============================================================================

class VisualMasker:
    """
    Visual masking effects.

    "Ba'el masks percepts." — Ba'el
    """

    def __init__(self):
        """Initialize masker."""
        self._lock = threading.RLock()

    def apply_mask(
        self,
        target: VisualInput,
        mask: VisualInput,
        masking_type: MaskingType,
        soa: float
    ) -> MaskingResult:
        """Apply visual masking."""
        with self._lock:
            # Calculate masking effectiveness
            masking_strength = self._calculate_masking(masking_type, soa, mask.strength)

            # Target visibility
            visibility = target.strength * (1.0 - masking_strength)

            # Awareness depends on visibility and recurrence time
            # Mask interrupts recurrence if SOA is short
            awareness = visibility > 0.3 and soa > 0.08  # Need ~80ms for local recurrence

            return MaskingResult(
                target_id=target.id,
                mask_id=mask.id,
                masking_type=masking_type,
                soa=soa,
                target_visibility=visibility,
                awareness_achieved=awareness
            )

    def _calculate_masking(
        self,
        masking_type: MaskingType,
        soa: float,
        mask_strength: float
    ) -> float:
        """Calculate masking strength."""
        if masking_type == MaskingType.BACKWARD:
            # Backward masking strongest at ~50ms SOA
            optimal_soa = 0.05
            soa_factor = math.exp(-((soa - optimal_soa) ** 2) / 0.002)
            return mask_strength * soa_factor

        elif masking_type == MaskingType.FORWARD:
            # Forward masking decreases with SOA
            return mask_strength * max(0, 1.0 - soa * 10)

        elif masking_type == MaskingType.METACONTRAST:
            # U-shaped function
            peak_soa = 0.07
            soa_factor = 1.0 - abs(soa - peak_soa) / 0.1
            return mask_strength * max(0, soa_factor)

        else:  # Pattern masking
            return mask_strength * max(0, 1.0 - soa * 5)


# ============================================================================
# RECURRENT PROCESSING ENGINE
# ============================================================================

class RecurrentProcessingEngine:
    """
    Complete recurrent processing engine.

    "Ba'el's visual awareness." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._feedforward = FeedforwardProcessor()
        self._recurrent = RecurrentProcessor()
        self._gate = AwarenessGate()
        self._masker = VisualMasker()

        self._inputs: Dict[str, VisualInput] = {}
        self._results: List[ProcessingResult] = []

        self._input_counter = 0
        self._lock = threading.RLock()

    def _generate_input_id(self) -> str:
        self._input_counter += 1
        return f"input_{self._input_counter}"

    def create_input(
        self,
        features: Dict[str, float],
        duration: float = 0.05,
        strength: float = 1.0
    ) -> VisualInput:
        """Create visual input."""
        inp = VisualInput(
            id=self._generate_input_id(),
            features=features,
            duration=duration,
            strength=strength
        )
        self._inputs[inp.id] = inp
        return inp

    def process(
        self,
        visual_input: VisualInput,
        attention: float = 0.5,
        allow_recurrence: bool = True
    ) -> ProcessingResult:
        """Process visual input through all phases."""
        with self._lock:
            start_time = time.time()
            phases = []

            # Feedforward sweep
            ff_activation = self._feedforward.process(visual_input)
            phases.append(ProcessingPhase.FEEDFORWARD)

            recurrent_activation = ff_activation.level

            if allow_recurrence:
                # Local recurrence
                local_activation = self._recurrent.local_recurrence(ff_activation)
                phases.append(ProcessingPhase.LOCAL_RECURRENT)

                # Global recurrence
                global_activation = self._recurrent.global_recurrence(
                    local_activation, attention
                )
                phases.append(ProcessingPhase.GLOBAL_RECURRENT)

                recurrent_activation = global_activation.level

            # Evaluate awareness
            final_activation = Activation(
                id=f"final_{visual_input.id}",
                level=recurrent_activation,
                phase=phases[-1]
            )

            awareness = self._gate.evaluate(final_activation, allow_recurrence)
            reportable = self._gate.is_reportable(awareness)

            processing_time = time.time() - start_time

            result = ProcessingResult(
                input_id=visual_input.id,
                feedforward_activation=ff_activation.level,
                recurrent_activation=recurrent_activation,
                awareness_level=awareness,
                processing_time=processing_time,
                phases_completed=phases,
                report_available=reportable
            )

            self._results.append(result)

            return result

    def mask(
        self,
        target: VisualInput,
        mask: VisualInput,
        soa: float,
        masking_type: MaskingType = MaskingType.BACKWARD
    ) -> MaskingResult:
        """Apply visual masking."""
        return self._masker.apply_mask(target, mask, masking_type, soa)

    def simulate_masking_curve(
        self,
        target_strength: float = 1.0,
        mask_strength: float = 1.0,
        soa_range: Tuple[float, float] = (0.0, 0.2),
        steps: int = 20
    ) -> List[Tuple[float, float]]:
        """Simulate masking function."""
        results = []

        target = self.create_input({'feature': 1.0}, strength=target_strength)
        mask = self.create_input({'feature': 1.0}, strength=mask_strength)

        for i in range(steps):
            soa = soa_range[0] + (soa_range[1] - soa_range[0]) * i / steps
            result = self.mask(target, mask, soa)
            results.append((soa, result.target_visibility))

        return results

    # Analysis

    def get_awareness_rate(self) -> float:
        """Get rate of conscious access."""
        if not self._results:
            return 0.0

        access_count = sum(
            1 for r in self._results
            if r.awareness_level == AwarenessLevel.ACCESS
        )
        return access_count / len(self._results)

    @property
    def results(self) -> List[ProcessingResult]:
        return list(self._results)

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'inputs_processed': len(self._inputs),
            'results': len(self._results),
            'awareness_rate': self.get_awareness_rate()
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_recurrent_processing_engine() -> RecurrentProcessingEngine:
    """Create recurrent processing engine."""
    return RecurrentProcessingEngine()


def process_visual_input(
    features: Dict[str, float],
    attention: float = 0.5
) -> ProcessingResult:
    """Quick visual processing."""
    engine = create_recurrent_processing_engine()
    inp = engine.create_input(features)
    return engine.process(inp, attention)
