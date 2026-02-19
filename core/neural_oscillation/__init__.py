"""
BAEL Neural Oscillation Engine
===============================

Neural oscillations and brain rhythms.
Gamma, theta, alpha, beta, delta waves.

"Ba'el resonates with neural rhythms." — Ba'el
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
from collections import deque, defaultdict
import copy

logger = logging.getLogger("BAEL.NeuralOscillation")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class FrequencyBand(Enum):
    """Neural frequency bands."""
    DELTA = auto()     # 0.5-4 Hz, deep sleep
    THETA = auto()     # 4-8 Hz, memory, navigation
    ALPHA = auto()     # 8-13 Hz, relaxation, inhibition
    BETA = auto()      # 13-30 Hz, active thinking
    GAMMA = auto()     # 30-100 Hz, binding, consciousness


class PhaseRelation(Enum):
    """Phase relations between oscillations."""
    IN_PHASE = auto()       # 0 degrees
    ANTI_PHASE = auto()     # 180 degrees
    QUARTER_PHASE = auto()  # 90 degrees
    ARBITRARY = auto()


class CouplingType(Enum):
    """Types of oscillation coupling."""
    PHASE_PHASE = auto()      # Phase-phase coupling
    PHASE_AMPLITUDE = auto()  # Phase-amplitude coupling (nested)
    AMPLITUDE_AMPLITUDE = auto()
    FREQUENCY_FREQUENCY = auto()


class OscillationFunction(Enum):
    """Functions of oscillations."""
    BINDING = auto()          # Feature binding (gamma)
    MEMORY_ENCODING = auto()  # Memory (theta)
    ATTENTION = auto()        # Attention (alpha)
    MOTOR = auto()            # Movement (beta)
    SLEEP = auto()            # Sleep (delta)


@dataclass
class Oscillator:
    """
    A neural oscillator.
    """
    id: str
    frequency: float        # Hz
    amplitude: float = 1.0
    phase: float = 0.0      # Radians
    band: FrequencyBand = FrequencyBand.ALPHA
    region: str = "cortex"


@dataclass
class Phase:
    """
    Phase of an oscillation.
    """
    value: float           # 0 to 2*pi
    peak: bool = False     # At peak?
    trough: bool = False   # At trough?

    @property
    def normalized(self) -> float:
        """Phase normalized to 0-1."""
        return (self.value % (2 * math.pi)) / (2 * math.pi)

    @property
    def degrees(self) -> float:
        return math.degrees(self.value % (2 * math.pi))


@dataclass
class PowerSpectrum:
    """
    Power spectrum of neural activity.
    """
    frequencies: List[float]
    powers: List[float]
    dominant_frequency: float = 0.0
    dominant_band: FrequencyBand = FrequencyBand.ALPHA

    @property
    def total_power(self) -> float:
        return sum(self.powers)


@dataclass
class Coupling:
    """
    Coupling between oscillators.
    """
    id: str
    source_id: str
    target_id: str
    coupling_type: CouplingType
    strength: float = 0.5
    phase_lag: float = 0.0


# ============================================================================
# OSCILLATOR
# ============================================================================

class NeuralOscillator:
    """
    Single neural oscillator.

    "Ba'el oscillates." — Ba'el
    """

    BAND_RANGES = {
        FrequencyBand.DELTA: (0.5, 4.0),
        FrequencyBand.THETA: (4.0, 8.0),
        FrequencyBand.ALPHA: (8.0, 13.0),
        FrequencyBand.BETA: (13.0, 30.0),
        FrequencyBand.GAMMA: (30.0, 100.0),
    }

    def __init__(
        self,
        frequency: float = 10.0,
        amplitude: float = 1.0,
        phase: float = 0.0,
        oscillator_id: str = None
    ):
        """Initialize oscillator."""
        self._id = oscillator_id or f"osc_{random.randint(1000, 9999)}"
        self._frequency = frequency
        self._amplitude = amplitude
        self._phase = phase
        self._band = self._determine_band(frequency)
        self._time = 0.0
        self._lock = threading.RLock()

    def _determine_band(self, freq: float) -> FrequencyBand:
        """Determine frequency band."""
        for band, (low, high) in self.BAND_RANGES.items():
            if low <= freq < high:
                return band
        if freq >= 30:
            return FrequencyBand.GAMMA
        return FrequencyBand.DELTA

    def step(self, dt: float) -> float:
        """Advance oscillator by dt seconds."""
        with self._lock:
            self._time += dt
            self._phase = (2 * math.pi * self._frequency * self._time) % (2 * math.pi)
            return self.value

    @property
    def value(self) -> float:
        """Current oscillator value."""
        return self._amplitude * math.sin(self._phase)

    @property
    def phase(self) -> Phase:
        """Current phase."""
        is_peak = abs(self._phase - math.pi/2) < 0.1
        is_trough = abs(self._phase - 3*math.pi/2) < 0.1
        return Phase(
            value=self._phase,
            peak=is_peak,
            trough=is_trough
        )

    @property
    def frequency(self) -> float:
        return self._frequency

    @property
    def amplitude(self) -> float:
        return self._amplitude

    @property
    def band(self) -> FrequencyBand:
        return self._band

    def to_oscillator(self) -> Oscillator:
        """Convert to dataclass."""
        return Oscillator(
            id=self._id,
            frequency=self._frequency,
            amplitude=self._amplitude,
            phase=self._phase,
            band=self._band
        )


# ============================================================================
# OSCILLATOR NETWORK
# ============================================================================

class OscillatorNetwork:
    """
    Network of coupled oscillators.

    "Ba'el's coupled rhythms." — Ba'el
    """

    def __init__(self):
        """Initialize network."""
        self._oscillators: Dict[str, NeuralOscillator] = {}
        self._couplings: Dict[str, Coupling] = {}
        self._time = 0.0
        self._osc_counter = 0
        self._coupling_counter = 0
        self._lock = threading.RLock()

    def _generate_osc_id(self) -> str:
        self._osc_counter += 1
        return f"osc_{self._osc_counter}"

    def _generate_coupling_id(self) -> str:
        self._coupling_counter += 1
        return f"coupling_{self._coupling_counter}"

    def add_oscillator(
        self,
        frequency: float,
        amplitude: float = 1.0,
        oscillator_id: str = None
    ) -> str:
        """Add oscillator to network."""
        with self._lock:
            osc_id = oscillator_id or self._generate_osc_id()
            self._oscillators[osc_id] = NeuralOscillator(
                frequency, amplitude, 0.0, osc_id
            )
            return osc_id

    def add_coupling(
        self,
        source_id: str,
        target_id: str,
        coupling_type: CouplingType,
        strength: float = 0.5
    ) -> Optional[str]:
        """Add coupling between oscillators."""
        with self._lock:
            if source_id not in self._oscillators or target_id not in self._oscillators:
                return None

            coupling_id = self._generate_coupling_id()
            self._couplings[coupling_id] = Coupling(
                id=coupling_id,
                source_id=source_id,
                target_id=target_id,
                coupling_type=coupling_type,
                strength=strength
            )
            return coupling_id

    def step(self, dt: float) -> Dict[str, float]:
        """Advance network by dt seconds."""
        with self._lock:
            self._time += dt

            values = {}

            # Step each oscillator
            for osc_id, osc in self._oscillators.items():
                values[osc_id] = osc.step(dt)

            # Apply couplings
            for coupling in self._couplings.values():
                if coupling.coupling_type == CouplingType.PHASE_PHASE:
                    # Phase synchronization
                    source = self._oscillators[coupling.source_id]
                    target = self._oscillators[coupling.target_id]

                    phase_diff = source.phase.value - target.phase.value
                    adjustment = coupling.strength * math.sin(phase_diff) * dt
                    target._phase += adjustment

            return values

    def get_phase_locking(
        self,
        osc1_id: str,
        osc2_id: str
    ) -> float:
        """Calculate phase locking value."""
        if osc1_id not in self._oscillators or osc2_id not in self._oscillators:
            return 0.0

        phase1 = self._oscillators[osc1_id].phase.value
        phase2 = self._oscillators[osc2_id].phase.value

        # PLV is based on phase difference consistency
        diff = abs(phase1 - phase2)
        return 1.0 - (diff / math.pi)  # Simplified PLV

    def get_power_spectrum(self) -> PowerSpectrum:
        """Calculate power spectrum."""
        frequencies = []
        powers = []

        for osc in self._oscillators.values():
            frequencies.append(osc.frequency)
            powers.append(osc.amplitude ** 2)

        if not frequencies:
            return PowerSpectrum([], [], 0.0)

        max_idx = powers.index(max(powers))
        dom_freq = frequencies[max_idx]
        dom_band = self._oscillators[list(self._oscillators.keys())[max_idx]].band

        return PowerSpectrum(
            frequencies=frequencies,
            powers=powers,
            dominant_frequency=dom_freq,
            dominant_band=dom_band
        )

    @property
    def oscillators(self) -> List[Oscillator]:
        return [osc.to_oscillator() for osc in self._oscillators.values()]

    @property
    def time(self) -> float:
        return self._time


# ============================================================================
# CROSS-FREQUENCY COUPLING
# ============================================================================

class CrossFrequencyCoupling:
    """
    Cross-frequency coupling (e.g., theta-gamma).

    "Ba'el nests frequencies." — Ba'el
    """

    def __init__(self):
        """Initialize CFC."""
        self._network = OscillatorNetwork()
        self._pac_history: deque = deque(maxlen=1000)  # Phase-amplitude coupling
        self._lock = threading.RLock()

    def setup_theta_gamma(self) -> Tuple[str, str]:
        """Set up theta-gamma coupling."""
        with self._lock:
            # Theta (6 Hz) modulates gamma (40 Hz)
            theta_id = self._network.add_oscillator(6.0, 1.0)
            gamma_id = self._network.add_oscillator(40.0, 0.3)

            # Phase-amplitude coupling
            self._network.add_coupling(
                theta_id, gamma_id,
                CouplingType.PHASE_AMPLITUDE,
                strength=0.7
            )

            return theta_id, gamma_id

    def modulate_gamma_by_theta(
        self,
        theta_phase: float,
        base_gamma_amplitude: float
    ) -> float:
        """Modulate gamma amplitude by theta phase."""
        # Gamma is highest at theta peak
        modulation = 0.5 + 0.5 * math.cos(theta_phase)
        return base_gamma_amplitude * modulation

    def compute_pac(
        self,
        phase_signal: List[float],
        amplitude_signal: List[float]
    ) -> float:
        """Compute phase-amplitude coupling."""
        if len(phase_signal) != len(amplitude_signal) or not phase_signal:
            return 0.0

        # Simplified PAC calculation
        n = len(phase_signal)
        mean_amp = sum(amplitude_signal) / n

        # Amplitude at each phase bin
        phase_bins = [[] for _ in range(8)]  # 8 phase bins

        for phase, amp in zip(phase_signal, amplitude_signal):
            bin_idx = int((phase % (2 * math.pi)) / (2 * math.pi / 8))
            bin_idx = min(7, bin_idx)
            phase_bins[bin_idx].append(amp)

        # Calculate modulation index
        bin_means = []
        for bin_amps in phase_bins:
            if bin_amps:
                bin_means.append(sum(bin_amps) / len(bin_amps))
            else:
                bin_means.append(mean_amp)

        if max(bin_means) == 0:
            return 0.0

        # Normalized difference
        pac = (max(bin_means) - min(bin_means)) / max(bin_means)
        self._pac_history.append(pac)

        return pac

    @property
    def network(self) -> OscillatorNetwork:
        return self._network

    @property
    def mean_pac(self) -> float:
        if not self._pac_history:
            return 0.0
        return sum(self._pac_history) / len(self._pac_history)


# ============================================================================
# NEURAL OSCILLATION ENGINE
# ============================================================================

class NeuralOscillationEngine:
    """
    Complete neural oscillation engine.

    "Ba'el's rhythmic cognition." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._network = OscillatorNetwork()
        self._cfc = CrossFrequencyCoupling()
        self._band_oscillators: Dict[FrequencyBand, str] = {}
        self._time = 0.0
        self._dt = 0.001  # 1 ms timestep
        self._lock = threading.RLock()

    # Oscillator management

    def add_oscillator(
        self,
        band: FrequencyBand,
        amplitude: float = 1.0
    ) -> str:
        """Add oscillator for frequency band."""
        freq_ranges = NeuralOscillator.BAND_RANGES
        low, high = freq_ranges[band]
        freq = (low + high) / 2  # Use center frequency

        osc_id = self._network.add_oscillator(freq, amplitude)
        self._band_oscillators[band] = osc_id

        return osc_id

    def add_custom_oscillator(
        self,
        frequency: float,
        amplitude: float = 1.0
    ) -> str:
        """Add oscillator with custom frequency."""
        return self._network.add_oscillator(frequency, amplitude)

    def couple(
        self,
        source_id: str,
        target_id: str,
        coupling_type: CouplingType = CouplingType.PHASE_PHASE,
        strength: float = 0.5
    ) -> Optional[str]:
        """Couple two oscillators."""
        return self._network.add_coupling(
            source_id, target_id, coupling_type, strength
        )

    # Simulation

    def step(self, dt: float = None) -> Dict[str, float]:
        """Advance simulation."""
        dt = dt or self._dt
        self._time += dt
        return self._network.step(dt)

    def run(self, duration: float) -> List[Dict[str, float]]:
        """Run simulation for duration."""
        history = []
        steps = int(duration / self._dt)

        for _ in range(steps):
            values = self.step()
            history.append(values)

        return history

    # Analysis

    def get_power(self, band: FrequencyBand = None) -> float:
        """Get power in frequency band."""
        spectrum = self._network.get_power_spectrum()

        if band is None:
            return spectrum.total_power

        if band not in self._band_oscillators:
            return 0.0

        osc_id = self._band_oscillators[band]
        for osc in self._network.oscillators:
            if osc.id == osc_id:
                return osc.amplitude ** 2

        return 0.0

    def get_dominant_band(self) -> FrequencyBand:
        """Get dominant frequency band."""
        return self._network.get_power_spectrum().dominant_band

    def get_phase_locking(
        self,
        band1: FrequencyBand,
        band2: FrequencyBand
    ) -> float:
        """Get phase locking between bands."""
        if band1 not in self._band_oscillators or band2 not in self._band_oscillators:
            return 0.0

        return self._network.get_phase_locking(
            self._band_oscillators[band1],
            self._band_oscillators[band2]
        )

    # Predefined setups

    def setup_attention(self) -> None:
        """Set up oscillators for attention."""
        self.add_oscillator(FrequencyBand.ALPHA, 1.0)
        self.add_oscillator(FrequencyBand.GAMMA, 0.5)

    def setup_memory(self) -> None:
        """Set up oscillators for memory."""
        theta_id = self.add_oscillator(FrequencyBand.THETA, 1.0)
        gamma_id = self.add_oscillator(FrequencyBand.GAMMA, 0.3)
        self.couple(theta_id, gamma_id, CouplingType.PHASE_AMPLITUDE, 0.7)

    def setup_sleep(self, stage: int = 3) -> None:
        """Set up oscillators for sleep stage."""
        if stage <= 2:
            self.add_oscillator(FrequencyBand.THETA, 0.8)
            self.add_oscillator(FrequencyBand.ALPHA, 0.3)
        else:
            self.add_oscillator(FrequencyBand.DELTA, 1.0)
            self.add_oscillator(FrequencyBand.THETA, 0.2)

    @property
    def time(self) -> float:
        return self._time

    @property
    def oscillators(self) -> List[Oscillator]:
        return self._network.oscillators

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        spectrum = self._network.get_power_spectrum()
        return {
            'time': self._time,
            'oscillator_count': len(self._network.oscillators),
            'dominant_band': spectrum.dominant_band.name,
            'total_power': spectrum.total_power,
            'band_oscillators': {b.name: oid for b, oid in self._band_oscillators.items()}
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_oscillation_engine() -> NeuralOscillationEngine:
    """Create neural oscillation engine."""
    return NeuralOscillationEngine()


def create_memory_oscillations() -> NeuralOscillationEngine:
    """Create engine configured for memory."""
    engine = create_oscillation_engine()
    engine.setup_memory()
    return engine


def create_attention_oscillations() -> NeuralOscillationEngine:
    """Create engine configured for attention."""
    engine = create_oscillation_engine()
    engine.setup_attention()
    return engine
