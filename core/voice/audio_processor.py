"""
BAEL Audio Processor
=====================

Audio capture, processing, and voice activity detection.
Handles microphone input and audio preprocessing.

Features:
- Microphone capture
- Voice activity detection (VAD)
- Noise reduction
- Audio normalization
- Chunking and buffering
- Format conversion
"""

import asyncio
import collections
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


class VADMode(Enum):
    """Voice activity detection modes."""
    DISABLED = 0
    LOW_BITRATE = 1  # Aggressive filtering, for low quality audio
    QUALITY = 2      # Balanced
    AGGRESSIVE = 3   # Aggressive, good for noisy environments


@dataclass
class AudioConfig:
    """Audio configuration."""
    # Format
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2  # bytes per sample

    # VAD
    vad_mode: VADMode = VADMode.QUALITY
    vad_frame_ms: int = 30  # Frame duration in ms

    # Silence detection
    silence_threshold: float = 0.01
    speech_pad_ms: int = 300  # Padding around speech
    min_speech_ms: int = 250  # Minimum speech duration
    max_speech_ms: int = 30000  # Maximum recording duration

    # Buffering
    buffer_size: int = 4096
    max_buffer_seconds: float = 60.0

    # Processing
    enable_noise_reduction: bool = True
    normalize_audio: bool = True


@dataclass
class AudioChunk:
    """An audio chunk with metadata."""
    data: bytes
    timestamp: float = 0.0
    is_speech: bool = False
    energy: float = 0.0

    @property
    def duration_ms(self) -> float:
        """Calculate chunk duration in milliseconds."""
        # Assuming 16-bit mono at 16kHz
        return (len(self.data) / 2) / 16 * 1000


class RingBuffer:
    """Circular buffer for audio data."""

    def __init__(self, max_samples: int):
        self.max_samples = max_samples
        self.buffer: Deque[int] = collections.deque(maxlen=max_samples)

    def append(self, data: bytes) -> None:
        """Append audio data."""
        import struct
        samples = struct.unpack(f"<{len(data)//2}h", data)
        self.buffer.extend(samples)

    def get_all(self) -> bytes:
        """Get all buffered audio."""
        import struct
        return struct.pack(f"<{len(self.buffer)}h", *self.buffer)

    def clear(self) -> None:
        """Clear buffer."""
        self.buffer.clear()

    def __len__(self) -> int:
        return len(self.buffer)


class AudioProcessor:
    """
    Audio processing engine for BAEL.
    """

    def __init__(
        self,
        config: Optional[AudioConfig] = None,
    ):
        self.config = config or AudioConfig()

        # VAD
        self._vad = None
        self._vad_available = False
        self._init_vad()

        # State
        self._is_recording = False
        self._speech_buffer: List[AudioChunk] = []
        self._silence_frames = 0
        self._speech_frames = 0

        # Ring buffer for pre-speech audio
        samples_per_second = self.config.sample_rate
        buffer_samples = int(self.config.max_buffer_seconds * samples_per_second)
        self._ring_buffer = RingBuffer(buffer_samples)

        # Stats
        self.stats = {
            "chunks_processed": 0,
            "speech_chunks": 0,
            "silence_chunks": 0,
            "total_audio_seconds": 0.0,
        }

    def _init_vad(self) -> None:
        """Initialize voice activity detector."""
        if self.config.vad_mode == VADMode.DISABLED:
            return

        try:
            import webrtcvad
            self._vad = webrtcvad.Vad(self.config.vad_mode.value)
            self._vad_available = True
        except ImportError:
            logger.warning("webrtcvad not available, using energy-based VAD")

    def _calculate_energy(self, data: bytes) -> float:
        """Calculate audio energy level."""
        import struct

        if not data:
            return 0.0

        samples = struct.unpack(f"<{len(data)//2}h", data)
        if not samples:
            return 0.0

        # RMS energy
        sum_squares = sum(s * s for s in samples)
        rms = (sum_squares / len(samples)) ** 0.5

        # Normalize to 0-1 range (16-bit audio max is 32767)
        return rms / 32767.0

    def _is_speech(self, data: bytes) -> bool:
        """Detect if audio chunk contains speech."""
        if self.config.vad_mode == VADMode.DISABLED:
            return True

        if self._vad_available and self._vad:
            try:
                # WebRTC VAD requires specific frame sizes
                frame_samples = self.config.sample_rate * self.config.vad_frame_ms // 1000
                frame_bytes = frame_samples * 2  # 16-bit samples

                if len(data) >= frame_bytes:
                    return self._vad.is_speech(data[:frame_bytes], self.config.sample_rate)
            except Exception as e:
                logger.debug(f"VAD error: {e}")

        # Fallback to energy-based detection
        energy = self._calculate_energy(data)
        return energy > self.config.silence_threshold

    def process_chunk(self, data: bytes) -> AudioChunk:
        """
        Process an audio chunk.

        Args:
            data: Raw audio bytes

        Returns:
            Processed AudioChunk
        """
        self.stats["chunks_processed"] += 1
        self.stats["total_audio_seconds"] += len(data) / 2 / self.config.sample_rate

        is_speech = self._is_speech(data)
        energy = self._calculate_energy(data)

        if is_speech:
            self.stats["speech_chunks"] += 1
        else:
            self.stats["silence_chunks"] += 1

        return AudioChunk(
            data=data,
            timestamp=time.time(),
            is_speech=is_speech,
            energy=energy,
        )

    async def capture_microphone(
        self,
        duration_seconds: Optional[float] = None,
    ) -> AsyncGenerator[AudioChunk, None]:
        """
        Capture audio from microphone.

        Args:
            duration_seconds: Optional capture duration limit

        Yields:
            AudioChunk objects
        """
        try:
            import pyaudio
        except ImportError:
            logger.error("pyaudio not installed. Run: pip install pyaudio")
            return

        pa = pyaudio.PyAudio()

        try:
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                frames_per_buffer=self.config.buffer_size,
            )

            self._is_recording = True
            start_time = time.time()

            while self._is_recording:
                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    break

                try:
                    data = stream.read(self.config.buffer_size, exception_on_overflow=False)
                    chunk = self.process_chunk(data)
                    yield chunk
                except Exception as e:
                    logger.error(f"Audio capture error: {e}")
                    break

                await asyncio.sleep(0.001)  # Yield to event loop

        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()
            self._is_recording = False

    async def capture_speech(
        self,
        max_duration_seconds: Optional[float] = None,
    ) -> Optional[bytes]:
        """
        Capture speech segment with VAD.

        Args:
            max_duration_seconds: Maximum recording duration

        Returns:
            Audio data or None if no speech detected
        """
        max_duration = max_duration_seconds or (self.config.max_speech_ms / 1000)
        min_frames = self.config.min_speech_ms // self.config.vad_frame_ms
        pad_frames = self.config.speech_pad_ms // self.config.vad_frame_ms

        speech_buffer: List[bytes] = []
        triggered = False
        silence_count = 0

        async for chunk in self.capture_microphone(duration_seconds=max_duration):
            if chunk.is_speech:
                if not triggered:
                    triggered = True
                    # Add ring buffer for pre-speech audio
                    # speech_buffer.append(self._ring_buffer.get_all())

                speech_buffer.append(chunk.data)
                silence_count = 0
            else:
                if triggered:
                    speech_buffer.append(chunk.data)
                    silence_count += 1

                    if silence_count >= pad_frames:
                        # End of speech
                        if len(speech_buffer) >= min_frames:
                            return b"".join(speech_buffer)
                        else:
                            # Too short, continue
                            triggered = False
                            speech_buffer.clear()
                            silence_count = 0
                else:
                    # Store pre-speech audio
                    self._ring_buffer.append(chunk.data)

        if speech_buffer and len(speech_buffer) >= min_frames:
            return b"".join(speech_buffer)

        return None

    def stop_recording(self) -> None:
        """Stop audio recording."""
        self._is_recording = False

    @staticmethod
    def normalize_audio(data: bytes, target_level: float = 0.5) -> bytes:
        """
        Normalize audio level.

        Args:
            data: Audio data
            target_level: Target peak level (0-1)

        Returns:
            Normalized audio
        """
        import struct

        if not data:
            return data

        samples = list(struct.unpack(f"<{len(data)//2}h", data))

        if not samples:
            return data

        # Find peak
        peak = max(abs(s) for s in samples)

        if peak == 0:
            return data

        # Calculate multiplier
        target = int(32767 * target_level)
        multiplier = target / peak

        # Apply
        normalized = [int(s * multiplier) for s in samples]

        # Clamp
        normalized = [max(-32767, min(32767, s)) for s in normalized]

        return struct.pack(f"<{len(normalized)}h", *normalized)

    @staticmethod
    def convert_sample_rate(
        data: bytes,
        from_rate: int,
        to_rate: int,
    ) -> bytes:
        """Convert audio sample rate."""
        try:
            import numpy as np
            from scipy import signal
        except ImportError:
            logger.error("numpy/scipy required for sample rate conversion")
            return data

        import struct

        samples = np.array(struct.unpack(f"<{len(data)//2}h", data))

        # Resample
        num_samples = int(len(samples) * to_rate / from_rate)
        resampled = signal.resample(samples, num_samples)

        # Convert back to bytes
        resampled = np.clip(resampled, -32767, 32767).astype(np.int16)
        return struct.pack(f"<{len(resampled)}h", *resampled)

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            **self.stats,
            "is_recording": self._is_recording,
            "vad_available": self._vad_available,
            "vad_mode": self.config.vad_mode.value,
        }


def demo():
    """Demonstrate audio processor."""
    print("=" * 60)
    print("BAEL Audio Processor Demo")
    print("=" * 60)

    config = AudioConfig(
        sample_rate=16000,
        vad_mode=VADMode.QUALITY,
    )

    processor = AudioProcessor(config)

    print(f"\nAudio configuration:")
    print(f"  Sample rate: {config.sample_rate} Hz")
    print(f"  Channels: {config.channels}")
    print(f"  VAD mode: {config.vad_mode.value}")
    print(f"  VAD available: {processor._vad_available}")

    # Test energy calculation
    import struct
    test_audio = struct.pack("<100h", *([1000] * 100))  # Constant tone
    energy = processor._calculate_energy(test_audio)
    print(f"\nTest audio energy: {energy:.4f}")

    print(f"\nStats: {processor.get_stats()}")


if __name__ == "__main__":
    demo()
