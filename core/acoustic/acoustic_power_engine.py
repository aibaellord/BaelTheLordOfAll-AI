"""
BAEL - Acoustic Power Engine
==============================

RESONATE. VIBRATE. CONTROL. DOMINATE.

This engine provides:
- Sound frequency generation
- Acoustic manipulation
- Infrasound weapons
- Ultrasonic control
- Binaural entrainment
- Resonance weapons
- Voice synthesis and cloning
- Sonic crowd control
- Audio steganography
- Acoustic levitation
- Sound healing/harming
- Frequency-based mind control

"Ba'el commands the power of sound itself."
"""

import asyncio
import hashlib
import json
import logging
import math
import os
import random
import struct
import time
import wave
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.ACOUSTIC")


class FrequencyBand(Enum):
    """Frequency bands."""
    INFRASOUND = "infrasound"  # < 20 Hz
    BASS = "bass"  # 20-250 Hz
    LOW_MID = "low_mid"  # 250-500 Hz
    MID = "mid"  # 500-2000 Hz
    HIGH_MID = "high_mid"  # 2000-4000 Hz
    TREBLE = "treble"  # 4000-20000 Hz
    ULTRASOUND = "ultrasound"  # > 20000 Hz


class WaveformType(Enum):
    """Waveform types."""
    SINE = "sine"
    SQUARE = "square"
    TRIANGLE = "triangle"
    SAWTOOTH = "sawtooth"
    NOISE_WHITE = "white_noise"
    NOISE_PINK = "pink_noise"
    NOISE_BROWN = "brown_noise"
    CUSTOM = "custom"


class BrainwaveState(Enum):
    """Brainwave states."""
    DELTA = "delta"  # 0.5-4 Hz - Deep sleep
    THETA = "theta"  # 4-8 Hz - Meditation, creativity
    ALPHA = "alpha"  # 8-12 Hz - Relaxation
    BETA = "beta"  # 12-30 Hz - Active thinking
    GAMMA = "gamma"  # 30-100 Hz - Peak focus
    EPSILON = "epsilon"  # < 0.5 Hz - Deep meditation
    LAMBDA = "lambda"  # 100-200 Hz - Transcendence


class AcousticEffect(Enum):
    """Acoustic effects."""
    CALM = "calm"
    ENERGIZE = "energize"
    FOCUS = "focus"
    SLEEP = "sleep"
    FEAR = "fear"
    DISORIENTATION = "disorientation"
    PAIN = "pain"
    NAUSEA = "nausea"
    COMPLIANCE = "compliance"
    EUPHORIA = "euphoria"


class SonicWeaponType(Enum):
    """Types of sonic weapons."""
    LRAD = "lrad"  # Long Range Acoustic Device
    INFRASOUND_GEN = "infrasound_generator"
    DIRECTED_AUDIO = "directed_audio"
    VORTEX_CANNON = "vortex_cannon"
    PARAMETRIC_ARRAY = "parametric_array"
    ACOUSTIC_LASER = "acoustic_laser"


@dataclass
class Frequency:
    """A frequency configuration."""
    hz: float
    amplitude: float = 1.0
    phase: float = 0.0
    waveform: WaveformType = WaveformType.SINE
    modulation: Optional[Dict[str, float]] = None


@dataclass
class BinauralBeat:
    """Binaural beat configuration."""
    base_frequency: float
    beat_frequency: float
    target_state: BrainwaveState
    duration_seconds: int
    volume: float = 0.5


@dataclass
class AcousticWeapon:
    """Acoustic weapon configuration."""
    weapon_type: SonicWeaponType
    frequency_range: Tuple[float, float]
    power_watts: float
    range_meters: float
    effect: AcousticEffect


@dataclass
class VoiceProfile:
    """Voice profile for synthesis/cloning."""
    id: str
    name: str
    sample_rate: int
    characteristics: Dict[str, float]
    embedding: List[float]


class AcousticPowerEngine:
    """
    Acoustic power and sound control engine.

    Features:
    - Frequency generation
    - Binaural entrainment
    - Sonic weapons
    - Voice cloning
    - Audio steganography
    - Crowd control
    """

    def __init__(self):
        self.sample_rate = 44100
        self.bit_depth = 16

        self.active_frequencies: Dict[str, Frequency] = {}
        self.binaural_presets: Dict[str, BinauralBeat] = {}
        self.voice_profiles: Dict[str, VoiceProfile] = {}
        self.weapons: Dict[str, AcousticWeapon] = {}

        self._init_presets()
        self._init_weapons()
        self._init_sacred_frequencies()

        logger.info("AcousticPowerEngine initialized - ready to resonate")

    def _init_presets(self):
        """Initialize binaural presets."""
        presets = [
            ("deep_sleep", 100, 2, BrainwaveState.DELTA, 3600),
            ("meditation", 200, 6, BrainwaveState.THETA, 1800),
            ("relaxation", 300, 10, BrainwaveState.ALPHA, 1200),
            ("focus", 400, 15, BrainwaveState.BETA, 3600),
            ("peak_performance", 500, 40, BrainwaveState.GAMMA, 1800),
            ("transcendence", 100, 150, BrainwaveState.LAMBDA, 2400),
        ]

        for name, base, beat, state, duration in presets:
            self.binaural_presets[name] = BinauralBeat(
                base_frequency=base,
                beat_frequency=beat,
                target_state=state,
                duration_seconds=duration
            )

    def _init_weapons(self):
        """Initialize sonic weapons."""
        weapons = [
            (SonicWeaponType.LRAD, (2000, 3000), 162, 2000, AcousticEffect.PAIN),
            (SonicWeaponType.INFRASOUND_GEN, (7, 19), 100, 500, AcousticEffect.FEAR),
            (SonicWeaponType.DIRECTED_AUDIO, (500, 5000), 50, 100, AcousticEffect.DISORIENTATION),
            (SonicWeaponType.VORTEX_CANNON, (20, 200), 200, 50, AcousticEffect.NAUSEA),
            (SonicWeaponType.PARAMETRIC_ARRAY, (40000, 60000), 30, 200, AcousticEffect.COMPLIANCE),
            (SonicWeaponType.ACOUSTIC_LASER, (1000, 10000), 500, 1000, AcousticEffect.PAIN),
        ]

        for wtype, freq_range, power, range_m, effect in weapons:
            self.weapons[wtype.value] = AcousticWeapon(
                weapon_type=wtype,
                frequency_range=freq_range,
                power_watts=power,
                range_meters=range_m,
                effect=effect
            )

    def _init_sacred_frequencies(self):
        """Initialize sacred/healing frequencies."""
        self.sacred_frequencies = {
            174: "Foundation/Security",
            285: "Healing/Regeneration",
            396: "Liberation from Fear",
            417: "Facilitating Change",
            432: "Universal Harmony",
            528: "DNA Repair/Miracles",
            639: "Connection/Relationships",
            741: "Awakening Intuition",
            852: "Spiritual Order",
            963: "Divine Consciousness",
            7.83: "Schumann Resonance",
            40: "Gamma Cognition",
        }

        # Harmful frequencies
        self.harmful_frequencies = {
            7: "Organ resonance (dangerous)",
            18: "Fear response induction",
            19: "Eyeball resonance",
            110: "Confusion/disorientation",
            2500: "Pain threshold",
        }

    # =========================================================================
    # WAVEFORM GENERATION
    # =========================================================================

    def generate_waveform(
        self,
        frequency: float,
        duration: float,
        waveform: WaveformType = WaveformType.SINE,
        amplitude: float = 1.0
    ) -> bytes:
        """Generate waveform audio data."""
        num_samples = int(self.sample_rate * duration)
        samples = []

        for i in range(num_samples):
            t = i / self.sample_rate

            if waveform == WaveformType.SINE:
                value = math.sin(2 * math.pi * frequency * t)
            elif waveform == WaveformType.SQUARE:
                value = 1.0 if math.sin(2 * math.pi * frequency * t) >= 0 else -1.0
            elif waveform == WaveformType.TRIANGLE:
                value = 2 * abs(2 * (t * frequency - math.floor(t * frequency + 0.5))) - 1
            elif waveform == WaveformType.SAWTOOTH:
                value = 2 * (t * frequency - math.floor(t * frequency + 0.5))
            elif waveform == WaveformType.NOISE_WHITE:
                value = random.uniform(-1, 1)
            elif waveform == WaveformType.NOISE_PINK:
                value = sum(random.gauss(0, 0.5) for _ in range(3)) / 3
            else:
                value = math.sin(2 * math.pi * frequency * t)

            value *= amplitude
            sample = int(value * 32767)
            samples.append(struct.pack('<h', max(-32768, min(32767, sample))))

        return b''.join(samples)

    def generate_binaural(
        self,
        preset: str,
        duration: float = None
    ) -> bytes:
        """Generate binaural beat audio."""
        beat = self.binaural_presets.get(preset)
        if not beat:
            return b''

        dur = duration or beat.duration_seconds
        num_samples = int(self.sample_rate * dur)
        left_samples = []
        right_samples = []

        left_freq = beat.base_frequency
        right_freq = beat.base_frequency + beat.beat_frequency

        for i in range(num_samples):
            t = i / self.sample_rate

            left_val = math.sin(2 * math.pi * left_freq * t) * beat.volume
            right_val = math.sin(2 * math.pi * right_freq * t) * beat.volume

            left_samples.append(int(left_val * 32767))
            right_samples.append(int(right_val * 32767))

        # Interleave stereo
        stereo = []
        for l, r in zip(left_samples, right_samples):
            stereo.append(struct.pack('<hh',
                max(-32768, min(32767, l)),
                max(-32768, min(32767, r))
            ))

        return b''.join(stereo)

    def generate_isochronic(
        self,
        frequency: float,
        pulse_rate: float,
        duration: float
    ) -> bytes:
        """Generate isochronic tones."""
        num_samples = int(self.sample_rate * duration)
        samples = []

        for i in range(num_samples):
            t = i / self.sample_rate

            # Carrier frequency
            carrier = math.sin(2 * math.pi * frequency * t)

            # Pulse modulation
            pulse = 0.5 + 0.5 * math.sin(2 * math.pi * pulse_rate * t)
            pulse = 1.0 if pulse > 0.5 else 0.0  # Sharp on/off

            value = carrier * pulse * 0.7
            sample = int(value * 32767)
            samples.append(struct.pack('<h', max(-32768, min(32767, sample))))

        return b''.join(samples)

    # =========================================================================
    # SONIC WEAPONS
    # =========================================================================

    def generate_weapon_signal(
        self,
        weapon_type: SonicWeaponType,
        duration: float = 5.0
    ) -> bytes:
        """Generate sonic weapon signal."""
        weapon = self.weapons.get(weapon_type.value)
        if not weapon:
            return b''

        freq_low, freq_high = weapon.frequency_range
        center_freq = (freq_low + freq_high) / 2

        num_samples = int(self.sample_rate * duration)
        samples = []

        for i in range(num_samples):
            t = i / self.sample_rate

            # Frequency sweep
            freq = freq_low + (freq_high - freq_low) * (0.5 + 0.5 * math.sin(0.5 * t))

            # Generate high-intensity signal
            value = math.sin(2 * math.pi * freq * t)

            # Add harmonics for more impact
            value += 0.5 * math.sin(4 * math.pi * freq * t)
            value += 0.25 * math.sin(6 * math.pi * freq * t)

            value *= 0.8  # Normalize
            sample = int(value * 32767)
            samples.append(struct.pack('<h', max(-32768, min(32767, sample))))

        return b''.join(samples)

    def generate_fear_frequency(self, duration: float = 10.0) -> bytes:
        """Generate fear-inducing infrasound."""
        # 18-19 Hz range causes unease and fear
        return self._generate_modulated_infrasound(18.5, duration)

    def generate_nausea_frequency(self, duration: float = 10.0) -> bytes:
        """Generate nausea-inducing frequency."""
        # 7 Hz resonates with internal organs
        return self._generate_modulated_infrasound(7, duration)

    def _generate_modulated_infrasound(
        self,
        base_freq: float,
        duration: float
    ) -> bytes:
        """Generate modulated infrasound."""
        num_samples = int(self.sample_rate * duration)
        samples = []

        for i in range(num_samples):
            t = i / self.sample_rate

            # Slow modulation
            mod = 0.5 + 0.5 * math.sin(0.1 * math.pi * t)

            # Infrasound carrier
            value = math.sin(2 * math.pi * base_freq * t) * mod

            sample = int(value * 32767)
            samples.append(struct.pack('<h', max(-32768, min(32767, sample))))

        return b''.join(samples)

    # =========================================================================
    # VOICE CLONING
    # =========================================================================

    async def create_voice_profile(
        self,
        name: str,
        audio_samples: List[bytes]
    ) -> VoiceProfile:
        """Create voice profile from samples."""
        profile_id = self._gen_id("voice")

        # Analyze voice characteristics (simplified)
        characteristics = {
            "pitch_mean": random.uniform(80, 300),
            "pitch_std": random.uniform(10, 50),
            "formant_1": random.uniform(500, 800),
            "formant_2": random.uniform(1000, 2500),
            "speaking_rate": random.uniform(100, 180),
            "energy": random.uniform(0.3, 0.9),
        }

        # Generate embedding (would use neural network)
        embedding = [random.gauss(0, 1) for _ in range(256)]

        profile = VoiceProfile(
            id=profile_id,
            name=name,
            sample_rate=self.sample_rate,
            characteristics=characteristics,
            embedding=embedding
        )

        self.voice_profiles[profile_id] = profile
        logger.info(f"Created voice profile: {name}")

        return profile

    async def synthesize_speech(
        self,
        text: str,
        voice_profile_id: str = None
    ) -> bytes:
        """Synthesize speech from text."""
        # Simplified TTS (would use real TTS engine)
        duration = len(text.split()) * 0.4

        # Generate speech-like audio
        samples = []
        num_samples = int(self.sample_rate * duration)

        for i in range(num_samples):
            t = i / self.sample_rate

            # Mix of frequencies for speech-like sound
            value = 0.3 * math.sin(2 * math.pi * 150 * t)
            value += 0.2 * math.sin(2 * math.pi * 300 * t)
            value += 0.1 * random.gauss(0, 0.3)  # Noise for consonants

            # Amplitude envelope
            envelope = abs(math.sin(3 * math.pi * t))
            value *= envelope

            sample = int(value * 32767)
            samples.append(struct.pack('<h', max(-32768, min(32767, sample))))

        return b''.join(samples)

    # =========================================================================
    # AUDIO STEGANOGRAPHY
    # =========================================================================

    def hide_message(
        self,
        audio_data: bytes,
        message: str
    ) -> bytes:
        """Hide message in audio using LSB steganography."""
        message_bits = ''.join(format(ord(c), '08b') for c in message)
        message_bits += '00000000'  # Null terminator

        samples = list(struct.unpack(f'<{len(audio_data)//2}h', audio_data))

        if len(message_bits) > len(samples):
            raise ValueError("Message too long for audio")

        for i, bit in enumerate(message_bits):
            samples[i] = (samples[i] & ~1) | int(bit)

        return struct.pack(f'<{len(samples)}h', *samples)

    def extract_message(self, audio_data: bytes) -> str:
        """Extract hidden message from audio."""
        samples = struct.unpack(f'<{len(audio_data)//2}h', audio_data)

        bits = ''
        chars = []

        for sample in samples:
            bits += str(sample & 1)

            if len(bits) == 8:
                char_code = int(bits, 2)
                if char_code == 0:
                    break
                chars.append(chr(char_code))
                bits = ''

        return ''.join(chars)

    # =========================================================================
    # ACOUSTIC LEVITATION
    # =========================================================================

    def generate_levitation_signal(
        self,
        frequency: float = 40000
    ) -> bytes:
        """Generate acoustic levitation signal."""
        # Ultrasonic standing wave pattern
        duration = 1.0
        num_samples = int(self.sample_rate * duration)
        samples = []

        for i in range(num_samples):
            t = i / self.sample_rate

            # Two opposing ultrasonic waves
            wave1 = math.sin(2 * math.pi * frequency * t)
            wave2 = math.sin(2 * math.pi * frequency * t + math.pi)

            # Standing wave
            value = (wave1 + wave2) * 0.5

            sample = int(value * 32767)
            samples.append(struct.pack('<h', max(-32768, min(32767, sample))))

        return b''.join(samples)

    # =========================================================================
    # CROWD CONTROL
    # =========================================================================

    async def crowd_control_protocol(
        self,
        effect: AcousticEffect,
        intensity: float = 0.5
    ) -> Dict[str, Any]:
        """Generate crowd control acoustic signal."""
        effect_configs = {
            AcousticEffect.CALM: {
                "frequency": 528,
                "modulation": 6,
                "waveform": WaveformType.SINE
            },
            AcousticEffect.DISORIENTATION: {
                "frequency": 110,
                "modulation": 18,
                "waveform": WaveformType.SQUARE
            },
            AcousticEffect.FEAR: {
                "frequency": 18.5,
                "modulation": 0.5,
                "waveform": WaveformType.SINE
            },
            AcousticEffect.COMPLIANCE: {
                "frequency": 40,
                "modulation": 10,
                "waveform": WaveformType.SINE
            },
            AcousticEffect.PAIN: {
                "frequency": 2500,
                "modulation": 0,
                "waveform": WaveformType.SQUARE
            },
        }

        config = effect_configs.get(effect, effect_configs[AcousticEffect.CALM])

        audio = self.generate_waveform(
            frequency=config["frequency"],
            duration=30,
            waveform=config["waveform"],
            amplitude=intensity
        )

        return {
            "effect": effect.value,
            "config": config,
            "audio_size": len(audio),
            "status": "generated"
        }

    # =========================================================================
    # HEALING FREQUENCIES
    # =========================================================================

    def generate_healing_frequency(
        self,
        purpose: str,
        duration: float = 300
    ) -> bytes:
        """Generate healing frequency."""
        frequency_map = {
            "dna_repair": 528,
            "fear_liberation": 396,
            "change": 417,
            "connection": 639,
            "intuition": 741,
            "divine": 963,
            "harmony": 432,
            "grounding": 174,
            "regeneration": 285,
        }

        freq = frequency_map.get(purpose, 432)
        return self.generate_waveform(freq, duration, WaveformType.SINE, 0.5)

    def generate_schumann_resonance(self, duration: float = 600) -> bytes:
        """Generate Earth's Schumann resonance."""
        # 7.83 Hz - Earth's electromagnetic resonance
        return self.generate_waveform(7.83, duration, WaveformType.SINE, 0.7)

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def save_wav(
        self,
        audio_data: bytes,
        filename: str,
        stereo: bool = False
    ):
        """Save audio data to WAV file."""
        channels = 2 if stereo else 1

        with wave.open(filename, 'wb') as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(2)  # 16-bit
            wav.setframerate(self.sample_rate)
            wav.writeframes(audio_data)

        logger.info(f"Saved WAV: {filename}")

    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "sample_rate": self.sample_rate,
            "binaural_presets": len(self.binaural_presets),
            "voice_profiles": len(self.voice_profiles),
            "weapons": len(self.weapons),
            "sacred_frequencies": len(self.sacred_frequencies),
            "active_frequencies": len(self.active_frequencies)
        }


# ============================================================================
# SINGLETON
# ============================================================================

_engine: Optional[AcousticPowerEngine] = None


def get_acoustic_engine() -> AcousticPowerEngine:
    """Get global acoustic engine."""
    global _engine
    if _engine is None:
        _engine = AcousticPowerEngine()
    return _engine


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate acoustic engine."""
    print("=" * 60)
    print("🔊 ACOUSTIC POWER ENGINE 🔊")
    print("=" * 60)

    engine = get_acoustic_engine()

    # Stats
    print("\n--- Engine Stats ---")
    stats = engine.get_stats()
    print(f"Sample Rate: {stats['sample_rate']} Hz")
    print(f"Binaural Presets: {stats['binaural_presets']}")
    print(f"Sonic Weapons: {stats['weapons']}")

    # Sacred frequencies
    print("\n--- Sacred Frequencies ---")
    for freq, purpose in list(engine.sacred_frequencies.items())[:5]:
        print(f"  {freq} Hz: {purpose}")

    # Generate waveform
    print("\n--- Waveform Generation ---")
    audio = engine.generate_waveform(432, 1.0, WaveformType.SINE)
    print(f"Generated 432 Hz tone: {len(audio)} bytes")

    # Binaural beat
    print("\n--- Binaural Beats ---")
    for name, preset in list(engine.binaural_presets.items())[:3]:
        print(f"  {name}: {preset.target_state.value}")

    # Sonic weapons
    print("\n--- Sonic Weapons ---")
    for name, weapon in list(engine.weapons.items())[:3]:
        print(f"  {weapon.weapon_type.value}: {weapon.effect.value}")

    # Crowd control
    print("\n--- Crowd Control ---")
    result = await engine.crowd_control_protocol(AcousticEffect.COMPLIANCE)
    print(f"Generated: {result['effect']} ({result['audio_size']} bytes)")

    print("\n" + "=" * 60)
    print("🔊 SOUND IS POWER 🔊")


if __name__ == "__main__":
    asyncio.run(demo())
