"""
BAEL - Ultimate Frequency & Wave Engine
========================================

CONTROL ALL VIBRATIONS. MASTER ALL FREQUENCIES. DOMINATE ALL WAVES.

This engine provides:
- Complete electromagnetic spectrum mastery
- Sound and acoustic manipulation
- Brainwave entrainment
- Resonance exploitation
- Wave interference patterns
- Frequency synthesis
- Vibration analysis
- Harmonic generation
- Standing wave creation
- Bio-frequency applications

"Everything vibrates. He who controls frequency controls reality."
"""

import asyncio
import hashlib
import json
import logging
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.FREQUENCY")

# Physical constants
SPEED_OF_LIGHT = 299792458  # m/s
PLANCK_CONSTANT = 6.62607015e-34  # J·s
SPEED_OF_SOUND = 343  # m/s in air at 20°C


class WaveCategory(Enum):
    """Categories of waves."""
    ELECTROMAGNETIC = "electromagnetic"
    MECHANICAL = "mechanical"
    MATTER = "matter"
    GRAVITATIONAL = "gravitational"
    ACOUSTIC = "acoustic"
    BRAINWAVE = "brainwave"
    BIOMETRIC = "biometric"


class EMSpectrum(Enum):
    """Electromagnetic spectrum bands."""
    GAMMA = "gamma"
    XRAY = "xray"
    ULTRAVIOLET = "ultraviolet"
    VISIBLE_VIOLET = "visible_violet"
    VISIBLE_BLUE = "visible_blue"
    VISIBLE_GREEN = "visible_green"
    VISIBLE_YELLOW = "visible_yellow"
    VISIBLE_ORANGE = "visible_orange"
    VISIBLE_RED = "visible_red"
    INFRARED = "infrared"
    MICROWAVE = "microwave"
    RADIO_UHF = "radio_uhf"
    RADIO_VHF = "radio_vhf"
    RADIO_HF = "radio_hf"
    RADIO_MF = "radio_mf"
    RADIO_LF = "radio_lf"
    RADIO_VLF = "radio_vlf"
    RADIO_ELF = "radio_elf"


class BrainwaveState(Enum):
    """Brainwave states."""
    DELTA = "delta"      # 0.5-4 Hz - Deep sleep
    THETA = "theta"      # 4-8 Hz - Meditation, creativity
    ALPHA = "alpha"      # 8-12 Hz - Relaxed focus
    LOW_BETA = "low_beta"   # 12-15 Hz - Relaxed awareness
    BETA = "beta"        # 15-20 Hz - Active thinking
    HIGH_BETA = "high_beta"  # 20-30 Hz - Intense focus
    GAMMA = "gamma"      # 30-100 Hz - Peak performance
    LAMBDA = "lambda"    # 100-200 Hz - Mystical states
    EPSILON = "epsilon"  # <0.5 Hz - Deep meditation


class SolfeggioFrequency(Enum):
    """Solfeggio frequencies."""
    UT = 396      # Liberating guilt and fear
    RE = 417      # Undoing situations, facilitating change
    MI = 528      # Transformation, DNA repair
    FA = 639      # Connecting relationships
    SOL = 741     # Awakening intuition
    LA = 852      # Returning to spiritual order
    TI = 963      # Divine consciousness


class ChakraFrequency(Enum):
    """Chakra frequencies."""
    ROOT = 396         # Muladhara
    SACRAL = 417       # Svadhisthana
    SOLAR_PLEXUS = 528 # Manipura
    HEART = 639        # Anahata
    THROAT = 741       # Vishuddha
    THIRD_EYE = 852    # Ajna
    CROWN = 963        # Sahasrara


class WaveForm(Enum):
    """Wave forms."""
    SINE = "sine"
    SQUARE = "square"
    TRIANGLE = "triangle"
    SAWTOOTH = "sawtooth"
    PULSE = "pulse"
    NOISE = "noise"
    CUSTOM = "custom"


class ModulationType(Enum):
    """Types of modulation."""
    AMPLITUDE = "amplitude"
    FREQUENCY = "frequency"
    PHASE = "phase"
    PULSE = "pulse"
    BINAURAL = "binaural"
    ISOCHRONIC = "isochronic"
    MONAURAL = "monaural"


@dataclass
class Wave:
    """A wave representation."""
    id: str
    frequency: float  # Hz
    wavelength: float  # meters
    amplitude: float
    phase: float  # radians
    category: WaveCategory
    waveform: WaveForm
    properties: Dict[str, Any]


@dataclass
class FrequencyBand:
    """A frequency band."""
    name: str
    min_freq: float
    max_freq: float
    category: WaveCategory
    applications: List[str]
    effects: List[str]


@dataclass
class BinauralBeat:
    """A binaural beat."""
    id: str
    carrier_left: float
    carrier_right: float
    beat_frequency: float
    target_state: BrainwaveState
    duration_seconds: float


@dataclass
class ResonanceProfile:
    """A resonance profile."""
    id: str
    name: str
    fundamental: float
    harmonics: List[float]
    target_material: str
    effect: str
    power_required: float


@dataclass
class WaveInterference:
    """Wave interference pattern."""
    wave1: Wave
    wave2: Wave
    pattern_type: str  # constructive, destructive, standing
    nodes: List[float]
    antinodes: List[float]


class FrequencyWaveEngine:
    """
    Engine for frequency and wave manipulation.

    Features:
    - Complete EM spectrum
    - Brainwave entrainment
    - Resonance calculation
    - Wave synthesis
    - Interference patterns
    """

    def __init__(self):
        self.waves: Dict[str, Wave] = {}
        self.frequency_bands: Dict[str, FrequencyBand] = {}
        self.binaural_beats: Dict[str, BinauralBeat] = {}
        self.resonance_profiles: Dict[str, ResonanceProfile] = {}

        self._init_em_spectrum()
        self._init_brainwave_bands()
        self._init_special_frequencies()
        self._init_resonance_profiles()

        logger.info("FrequencyWaveEngine initialized - all frequencies accessible")

    def _init_em_spectrum(self):
        """Initialize electromagnetic spectrum bands."""
        em_bands = [
            ("Gamma Rays", 3e19, 3e24, ["medical imaging", "sterilization"], ["ionizing"]),
            ("X-Rays", 3e16, 3e19, ["medical imaging", "security"], ["ionizing"]),
            ("Ultraviolet", 7.5e14, 3e16, ["sterilization", "tanning"], ["ionizing at high end"]),
            ("Visible Light", 4e14, 7.5e14, ["vision", "communication"], ["perception"]),
            ("Infrared", 3e11, 4e14, ["heat", "remote control", "thermal imaging"], ["heating"]),
            ("Microwave", 3e8, 3e11, ["cooking", "radar", "communication"], ["heating"]),
            ("Radio UHF", 3e8, 3e9, ["TV", "mobile phones", "WiFi"], ["communication"]),
            ("Radio VHF", 3e7, 3e8, ["FM radio", "TV", "emergency"], ["communication"]),
            ("Radio HF", 3e6, 3e7, ["shortwave radio", "amateur radio"], ["long distance"]),
            ("Radio MF", 3e5, 3e6, ["AM radio"], ["ground wave"]),
            ("Radio LF", 3e4, 3e5, ["navigation", "time signals"], ["ground wave"]),
            ("Radio VLF", 3e3, 3e4, ["submarine communication"], ["penetration"]),
            ("Radio ELF", 3, 3e3, ["submarine communication", "earth penetrating"], ["deep penetration"]),
        ]

        for name, min_f, max_f, apps, effects in em_bands:
            band = FrequencyBand(
                name=name,
                min_freq=min_f,
                max_freq=max_f,
                category=WaveCategory.ELECTROMAGNETIC,
                applications=apps,
                effects=effects
            )
            self.frequency_bands[name] = band

    def _init_brainwave_bands(self):
        """Initialize brainwave frequency bands."""
        brainwave_bands = [
            ("Epsilon", 0, 0.5, ["suspended animation", "extraordinary states"], ["ultra-deep"]),
            ("Delta", 0.5, 4, ["deep sleep", "healing", "regeneration"], ["unconscious"]),
            ("Theta", 4, 8, ["meditation", "creativity", "intuition", "memory"], ["subconscious"]),
            ("Alpha", 8, 12, ["relaxation", "calm focus", "learning"], ["bridge state"]),
            ("Low Beta", 12, 15, ["relaxed attention", "positive thinking"], ["conscious"]),
            ("Beta", 15, 20, ["active thinking", "problem solving"], ["alert"]),
            ("High Beta", 20, 30, ["intense focus", "anxiety possible"], ["hyperalert"]),
            ("Gamma", 30, 100, ["peak performance", "higher processing", "insight"], ["transcendent"]),
            ("Lambda", 100, 200, ["mystical experiences", "extraordinary perception"], ["hyper-gamma"]),
        ]

        for name, min_f, max_f, apps, effects in brainwave_bands:
            band = FrequencyBand(
                name=name,
                min_freq=min_f,
                max_freq=max_f,
                category=WaveCategory.BRAINWAVE,
                applications=apps,
                effects=effects
            )
            self.frequency_bands[f"Brainwave_{name}"] = band

    def _init_special_frequencies(self):
        """Initialize special frequencies."""
        # Schumann Resonances
        schumann = [7.83, 14.3, 20.8, 27.3, 33.8]
        for i, freq in enumerate(schumann):
            wave = Wave(
                id=self._gen_id("wave"),
                frequency=freq,
                wavelength=SPEED_OF_LIGHT / freq,
                amplitude=1.0,
                phase=0.0,
                category=WaveCategory.ELECTROMAGNETIC,
                waveform=WaveForm.SINE,
                properties={"type": "schumann", "mode": i+1, "earth_resonance": True}
            )
            self.waves[f"schumann_{i+1}"] = wave

        # Solfeggio
        for solf in SolfeggioFrequency:
            wave = Wave(
                id=self._gen_id("wave"),
                frequency=float(solf.value),
                wavelength=SPEED_OF_SOUND / solf.value,
                amplitude=1.0,
                phase=0.0,
                category=WaveCategory.ACOUSTIC,
                waveform=WaveForm.SINE,
                properties={"type": "solfeggio", "name": solf.name}
            )
            self.waves[f"solfeggio_{solf.name}"] = wave

        # Earth frequency
        self.waves["earth_year"] = Wave(
            id=self._gen_id("wave"),
            frequency=136.1,  # OM frequency, earth year
            wavelength=SPEED_OF_SOUND / 136.1,
            amplitude=1.0,
            phase=0.0,
            category=WaveCategory.ACOUSTIC,
            waveform=WaveForm.SINE,
            properties={"type": "planetary", "body": "earth_year", "effect": "centering"}
        )

        # 432 Hz (natural tuning)
        self.waves["natural_a"] = Wave(
            id=self._gen_id("wave"),
            frequency=432.0,
            wavelength=SPEED_OF_SOUND / 432.0,
            amplitude=1.0,
            phase=0.0,
            category=WaveCategory.ACOUSTIC,
            waveform=WaveForm.SINE,
            properties={"type": "musical", "note": "A", "tuning": "natural/Verdi"}
        )

        # 440 Hz (concert pitch)
        self.waves["concert_a"] = Wave(
            id=self._gen_id("wave"),
            frequency=440.0,
            wavelength=SPEED_OF_SOUND / 440.0,
            amplitude=1.0,
            phase=0.0,
            category=WaveCategory.ACOUSTIC,
            waveform=WaveForm.SINE,
            properties={"type": "musical", "note": "A", "tuning": "concert"}
        )

    def _init_resonance_profiles(self):
        """Initialize resonance profiles."""
        profiles = [
            ("Glass Breaking", 556, [1112, 1668], "glass", "shatter", 100),
            ("Wine Glass", 440, [880, 1320], "crystal glass", "vibrate/shatter", 50),
            ("Human Body", 7.83, [15.66, 23.49], "human body", "resonance/healing", 1),
            ("Brain Sync", 10.0, [20.0, 40.0], "brain", "synchronization", 0.1),
            ("Bone", 25, [50, 75], "bone tissue", "healing", 5),
            ("Cell Membrane", 10000, [20000, 30000], "cell", "stimulation", 0.01),
            ("DNA", 528, [1056, 1584], "DNA", "repair/transformation", 1),
            ("Water Restructure", 432, [864, 1296], "water", "restructuring", 10),
        ]

        for name, fund, harmonics, target, effect, power in profiles:
            profile = ResonanceProfile(
                id=self._gen_id("res"),
                name=name,
                fundamental=fund,
                harmonics=harmonics,
                target_material=target,
                effect=effect,
                power_required=power
            )
            self.resonance_profiles[name] = profile

    # -------------------------------------------------------------------------
    # WAVE CALCULATIONS
    # -------------------------------------------------------------------------

    def frequency_to_wavelength(
        self,
        frequency: float,
        medium: str = "vacuum"
    ) -> float:
        """Convert frequency to wavelength."""
        if medium == "vacuum" or medium == "air":
            speed = SPEED_OF_LIGHT
        elif medium == "sound":
            speed = SPEED_OF_SOUND
        elif medium == "water":
            speed = 1500  # m/s in water
        else:
            speed = SPEED_OF_LIGHT

        return speed / frequency

    def wavelength_to_frequency(
        self,
        wavelength: float,
        medium: str = "vacuum"
    ) -> float:
        """Convert wavelength to frequency."""
        if medium == "vacuum" or medium == "air":
            speed = SPEED_OF_LIGHT
        elif medium == "sound":
            speed = SPEED_OF_SOUND
        elif medium == "water":
            speed = 1500
        else:
            speed = SPEED_OF_LIGHT

        return speed / wavelength

    def calculate_energy(self, frequency: float) -> float:
        """Calculate photon energy (E = hf)."""
        return PLANCK_CONSTANT * frequency

    def calculate_period(self, frequency: float) -> float:
        """Calculate wave period."""
        return 1.0 / frequency

    # -------------------------------------------------------------------------
    # WAVE SYNTHESIS
    # -------------------------------------------------------------------------

    def create_wave(
        self,
        frequency: float,
        amplitude: float = 1.0,
        phase: float = 0.0,
        category: WaveCategory = WaveCategory.ACOUSTIC,
        waveform: WaveForm = WaveForm.SINE
    ) -> Wave:
        """Create a new wave."""
        wave = Wave(
            id=self._gen_id("wave"),
            frequency=frequency,
            wavelength=self.frequency_to_wavelength(frequency, "sound"),
            amplitude=amplitude,
            phase=phase,
            category=category,
            waveform=waveform,
            properties={}
        )
        self.waves[wave.id] = wave
        return wave

    def generate_harmonics(
        self,
        fundamental: float,
        count: int = 8
    ) -> List[float]:
        """Generate harmonic series."""
        return [fundamental * (n + 1) for n in range(count)]

    def create_binaural_beat(
        self,
        target_state: BrainwaveState,
        duration: float = 300
    ) -> BinauralBeat:
        """Create binaural beat for target state."""
        # Target frequencies for each state
        target_freqs = {
            BrainwaveState.DELTA: 2.0,
            BrainwaveState.THETA: 6.0,
            BrainwaveState.ALPHA: 10.0,
            BrainwaveState.LOW_BETA: 13.5,
            BrainwaveState.BETA: 17.5,
            BrainwaveState.HIGH_BETA: 25.0,
            BrainwaveState.GAMMA: 40.0,
            BrainwaveState.LAMBDA: 150.0,
            BrainwaveState.EPSILON: 0.3,
        }

        beat_freq = target_freqs.get(target_state, 10.0)
        carrier = 200.0  # Base carrier frequency

        binaural = BinauralBeat(
            id=self._gen_id("bin"),
            carrier_left=carrier,
            carrier_right=carrier + beat_freq,
            beat_frequency=beat_freq,
            target_state=target_state,
            duration_seconds=duration
        )

        self.binaural_beats[binaural.id] = binaural
        return binaural

    # -------------------------------------------------------------------------
    # INTERFERENCE
    # -------------------------------------------------------------------------

    def calculate_interference(
        self,
        wave1: Wave,
        wave2: Wave
    ) -> WaveInterference:
        """Calculate interference pattern."""
        # Simplified interference calculation
        f1, f2 = wave1.frequency, wave2.frequency
        beat_freq = abs(f1 - f2)

        if abs(f1 - f2) < 0.01:
            pattern_type = "constructive" if abs(wave1.phase - wave2.phase) < 0.1 else "standing"
        else:
            pattern_type = "beating"

        return WaveInterference(
            wave1=wave1,
            wave2=wave2,
            pattern_type=pattern_type,
            nodes=[],
            antinodes=[]
        )

    def create_standing_wave(
        self,
        frequency: float,
        length: float
    ) -> Dict[str, Any]:
        """Create standing wave pattern."""
        wavelength = self.frequency_to_wavelength(frequency, "sound")
        n_modes = int(2 * length / wavelength)

        nodes = [i * wavelength / 2 for i in range(n_modes + 1)]
        antinodes = [(i + 0.5) * wavelength / 2 for i in range(n_modes)]

        return {
            "frequency": frequency,
            "wavelength": wavelength,
            "length": length,
            "mode_number": n_modes,
            "nodes": nodes[:10],  # First 10
            "antinodes": antinodes[:10]
        }

    # -------------------------------------------------------------------------
    # RESONANCE
    # -------------------------------------------------------------------------

    def find_resonance(
        self,
        target: str
    ) -> Optional[ResonanceProfile]:
        """Find resonance profile for target."""
        return self.resonance_profiles.get(target)

    def calculate_resonant_frequency(
        self,
        length: float,
        mode: int = 1,
        medium: str = "air"
    ) -> float:
        """Calculate resonant frequency for a cavity."""
        speed = SPEED_OF_SOUND if medium == "air" else 1500
        return (mode * speed) / (2 * length)

    # -------------------------------------------------------------------------
    # SPECTRUM ANALYSIS
    # -------------------------------------------------------------------------

    def classify_frequency(
        self,
        frequency: float
    ) -> Optional[str]:
        """Classify a frequency into spectrum band."""
        for name, band in self.frequency_bands.items():
            if band.min_freq <= frequency <= band.max_freq:
                return name
        return None

    def get_em_band(
        self,
        frequency: float
    ) -> Optional[EMSpectrum]:
        """Get EM spectrum band for frequency."""
        em_ranges = [
            (EMSpectrum.GAMMA, 3e19, 3e24),
            (EMSpectrum.XRAY, 3e16, 3e19),
            (EMSpectrum.ULTRAVIOLET, 7.5e14, 3e16),
            (EMSpectrum.VISIBLE_VIOLET, 6.5e14, 7.5e14),
            (EMSpectrum.VISIBLE_BLUE, 6e14, 6.5e14),
            (EMSpectrum.VISIBLE_GREEN, 5.3e14, 6e14),
            (EMSpectrum.VISIBLE_YELLOW, 5e14, 5.3e14),
            (EMSpectrum.VISIBLE_ORANGE, 4.8e14, 5e14),
            (EMSpectrum.VISIBLE_RED, 4e14, 4.8e14),
            (EMSpectrum.INFRARED, 3e11, 4e14),
            (EMSpectrum.MICROWAVE, 3e8, 3e11),
        ]

        for band, min_f, max_f in em_ranges:
            if min_f <= frequency <= max_f:
                return band
        return None

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "total_waves": len(self.waves),
            "frequency_bands": len(self.frequency_bands),
            "binaural_beats": len(self.binaural_beats),
            "resonance_profiles": len(self.resonance_profiles),
            "special_frequencies": {
                "solfeggio": len([w for w in self.waves if "solfeggio" in w]),
                "schumann": len([w for w in self.waves if "schumann" in w]),
            }
        }

    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]


# ============================================================================
# SINGLETON
# ============================================================================

_engine: Optional[FrequencyWaveEngine] = None


def get_frequency_engine() -> FrequencyWaveEngine:
    """Get global frequency wave engine."""
    global _engine
    if _engine is None:
        _engine = FrequencyWaveEngine()
    return _engine


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate frequency wave engine."""
    print("=" * 60)
    print("🌊 FREQUENCY & WAVE ENGINE 🌊")
    print("=" * 60)

    engine = get_frequency_engine()

    # Stats
    print("\n--- Engine Statistics ---")
    stats = engine.get_stats()
    print(f"Total Waves: {stats['total_waves']}")
    print(f"Frequency Bands: {stats['frequency_bands']}")
    print(f"Resonance Profiles: {stats['resonance_profiles']}")

    # Special frequencies
    print("\n--- Special Frequencies ---")
    print("Solfeggio:")
    for solf in SolfeggioFrequency:
        print(f"  {solf.name}: {solf.value} Hz")

    print("\nSchumann Resonances:")
    schumann = [7.83, 14.3, 20.8, 27.3, 33.8]
    for i, freq in enumerate(schumann):
        print(f"  Mode {i+1}: {freq} Hz")

    # Brainwave states
    print("\n--- Brainwave States ---")
    for state in [BrainwaveState.THETA, BrainwaveState.ALPHA, BrainwaveState.GAMMA]:
        binaural = engine.create_binaural_beat(state)
        print(f"  {state.value}: {binaural.beat_frequency} Hz beat")

    # Resonance
    print("\n--- Resonance Profiles ---")
    for name, profile in list(engine.resonance_profiles.items())[:3]:
        print(f"  {name}: {profile.fundamental} Hz")
        print(f"      Effect: {profile.effect}")

    # Wave calculations
    print("\n--- Wave Calculations ---")
    print(f"  440 Hz wavelength: {engine.frequency_to_wavelength(440, 'sound'):.2f} m")
    print(f"  Energy of 1 GHz photon: {engine.calculate_energy(1e9):.2e} J")

    # Harmonics
    print("\n--- Harmonics of 100 Hz ---")
    harmonics = engine.generate_harmonics(100, 5)
    print(f"  {harmonics}")

    print("\n" + "=" * 60)
    print("🌊 ALL FREQUENCIES UNDER CONTROL 🌊")


if __name__ == "__main__":
    asyncio.run(demo())
