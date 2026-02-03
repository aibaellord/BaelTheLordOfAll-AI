"""
BAEL - Audio Processing Module
Advanced audio processing, transcription, and synthesis.

Features:
- Speech-to-text (Whisper)
- Text-to-speech
- Audio analysis
- Voice activity detection
- Speaker diarization
- Audio effects
"""

import asyncio
import base64
import io
import logging
import os
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (Any, AsyncIterator, Callable, Dict, List, Optional, Tuple,
                    Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class AudioFormat(Enum):
    """Supported audio formats."""
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    FLAC = "flac"
    M4A = "m4a"
    WEBM = "webm"


class TranscriptionModel(Enum):
    """Transcription model providers."""
    WHISPER_LOCAL = "whisper_local"
    WHISPER_API = "whisper_api"
    DEEPGRAM = "deepgram"
    ASSEMBLY_AI = "assembly_ai"
    GOOGLE_SPEECH = "google_speech"


class TTSProvider(Enum):
    """Text-to-speech providers."""
    OPENAI = "openai"
    ELEVEN_LABS = "eleven_labs"
    GOOGLE = "google"
    AZURE = "azure"
    LOCAL = "local"


class Voice(Enum):
    """Available voices."""
    # OpenAI voices
    ALLOY = "alloy"
    ECHO = "echo"
    FABLE = "fable"
    ONYX = "onyx"
    NOVA = "nova"
    SHIMMER = "shimmer"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class AudioData:
    """Audio data container."""
    data: bytes
    format: AudioFormat
    sample_rate: int = 16000
    channels: int = 1
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: str) -> "AudioData":
        """Load audio from file."""
        path = Path(path)
        format_map = {
            ".wav": AudioFormat.WAV,
            ".mp3": AudioFormat.MP3,
            ".ogg": AudioFormat.OGG,
            ".flac": AudioFormat.FLAC,
            ".m4a": AudioFormat.M4A,
            ".webm": AudioFormat.WEBM
        }

        audio_format = format_map.get(path.suffix.lower(), AudioFormat.WAV)

        with open(path, "rb") as f:
            data = f.read()

        return cls(
            data=data,
            format=audio_format,
            metadata={"source_file": str(path)}
        )

    @classmethod
    def from_base64(cls, b64_data: str, format: AudioFormat = AudioFormat.WAV) -> "AudioData":
        """Create from base64 string."""
        data = base64.b64decode(b64_data)
        return cls(data=data, format=format)

    def to_base64(self) -> str:
        """Convert to base64 string."""
        return base64.b64encode(self.data).decode()

    def save(self, path: str) -> None:
        """Save audio to file."""
        with open(path, "wb") as f:
            f.write(self.data)


@dataclass
class TranscriptionSegment:
    """Transcription segment."""
    text: str
    start: float
    end: float
    confidence: float = 1.0
    speaker: Optional[str] = None
    words: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TranscriptionResult:
    """Full transcription result."""
    text: str
    segments: List[TranscriptionSegment]
    language: str = "en"
    duration: float = 0.0
    model: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AudioAnalysis:
    """Audio analysis result."""
    duration: float
    sample_rate: int
    channels: int
    loudness_db: float = 0.0
    peak_db: float = 0.0
    silence_ratio: float = 0.0
    speech_ratio: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpeakerSegment:
    """Speaker diarization segment."""
    speaker_id: str
    start: float
    end: float
    confidence: float = 1.0


# =============================================================================
# TRANSCRIPTION PROVIDERS
# =============================================================================

class TranscriptionProvider(ABC):
    """Abstract transcription provider."""

    @abstractmethod
    async def transcribe(
        self,
        audio: AudioData,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        pass


class WhisperAPIProvider(TranscriptionProvider):
    """OpenAI Whisper API provider."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._base_url = "https://api.openai.com/v1"

    async def transcribe(
        self,
        audio: AudioData,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """Transcribe using Whisper API."""
        import httpx

        # Save audio to temp file
        with tempfile.NamedTemporaryFile(
            suffix=f".{audio.format.value}",
            delete=False
        ) as f:
            f.write(audio.data)
            temp_path = f.name

        try:
            async with httpx.AsyncClient() as client:
                with open(temp_path, "rb") as audio_file:
                    files = {"file": audio_file}
                    data = {"model": "whisper-1", "response_format": "verbose_json"}

                    if language:
                        data["language"] = language

                    response = await client.post(
                        f"{self._base_url}/audio/transcriptions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        files=files,
                        data=data,
                        timeout=120.0
                    )

                    result = response.json()

            # Parse response
            segments = []
            for seg in result.get("segments", []):
                segments.append(TranscriptionSegment(
                    text=seg.get("text", ""),
                    start=seg.get("start", 0),
                    end=seg.get("end", 0),
                    confidence=seg.get("confidence", 1.0)
                ))

            return TranscriptionResult(
                text=result.get("text", ""),
                segments=segments,
                language=result.get("language", "en"),
                duration=result.get("duration", 0),
                model="whisper-1"
            )

        finally:
            os.unlink(temp_path)


class LocalWhisperProvider(TranscriptionProvider):
    """Local Whisper model provider."""

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None

    def _load_model(self):
        """Load Whisper model."""
        if self._model is None:
            try:
                import whisper
                self._model = whisper.load_model(self.model_size)
            except ImportError:
                logger.warning("whisper not installed, using mock")

    async def transcribe(
        self,
        audio: AudioData,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """Transcribe using local Whisper."""
        self._load_model()

        if self._model is None:
            # Return mock result if whisper not available
            return TranscriptionResult(
                text="[Local Whisper not available]",
                segments=[],
                model=f"whisper-{self.model_size}"
            )

        # Save to temp file
        with tempfile.NamedTemporaryFile(
            suffix=f".{audio.format.value}",
            delete=False
        ) as f:
            f.write(audio.data)
            temp_path = f.name

        try:
            # Run transcription in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._model.transcribe(
                    temp_path,
                    language=language
                )
            )

            segments = []
            for seg in result.get("segments", []):
                segments.append(TranscriptionSegment(
                    text=seg.get("text", ""),
                    start=seg.get("start", 0),
                    end=seg.get("end", 0)
                ))

            return TranscriptionResult(
                text=result.get("text", ""),
                segments=segments,
                language=result.get("language", "en"),
                model=f"whisper-{self.model_size}"
            )

        finally:
            os.unlink(temp_path)


# =============================================================================
# TTS PROVIDERS
# =============================================================================

class TTSProvider(ABC):
    """Abstract TTS provider."""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str = "alloy"
    ) -> AudioData:
        pass


class OpenAITTSProvider(TTSProvider):
    """OpenAI TTS provider."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._base_url = "https://api.openai.com/v1"

    async def synthesize(
        self,
        text: str,
        voice: str = "alloy",
        speed: float = 1.0
    ) -> AudioData:
        """Synthesize speech using OpenAI TTS."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/audio/speech",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": voice,
                    "speed": speed,
                    "response_format": "mp3"
                },
                timeout=60.0
            )

            return AudioData(
                data=response.content,
                format=AudioFormat.MP3,
                metadata={
                    "voice": voice,
                    "text_length": len(text)
                }
            )


class ElevenLabsTTSProvider(TTSProvider):
    """Eleven Labs TTS provider."""

    def __init__(self, api_key: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM"):
        self.api_key = api_key
        self.voice_id = voice_id
        self._base_url = "https://api.elevenlabs.io/v1"

    async def synthesize(
        self,
        text: str,
        voice: str = None,
        stability: float = 0.5,
        similarity_boost: float = 0.75
    ) -> AudioData:
        """Synthesize using Eleven Labs."""
        import httpx

        voice_id = voice or self.voice_id

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "voice_settings": {
                        "stability": stability,
                        "similarity_boost": similarity_boost
                    }
                },
                timeout=60.0
            )

            return AudioData(
                data=response.content,
                format=AudioFormat.MP3,
                metadata={
                    "voice_id": voice_id,
                    "text_length": len(text)
                }
            )


# =============================================================================
# AUDIO ANALYZER
# =============================================================================

class AudioAnalyzer:
    """Audio analysis utilities."""

    def __init__(self):
        self._has_numpy = False
        try:
            import numpy as np
            self._has_numpy = True
        except ImportError:
            pass

    def analyze(self, audio: AudioData) -> AudioAnalysis:
        """Analyze audio data."""
        if not self._has_numpy:
            return AudioAnalysis(
                duration=audio.duration or len(audio.data) / audio.sample_rate / 2,
                sample_rate=audio.sample_rate,
                channels=audio.channels
            )

        import numpy as np

        # Convert bytes to numpy array (assuming 16-bit PCM)
        samples = np.frombuffer(audio.data, dtype=np.int16)

        # Calculate metrics
        duration = len(samples) / audio.sample_rate

        # Normalize to float
        samples_float = samples.astype(np.float32) / 32768.0

        # RMS loudness
        rms = np.sqrt(np.mean(samples_float ** 2))
        loudness_db = 20 * np.log10(rms + 1e-10)

        # Peak
        peak = np.max(np.abs(samples_float))
        peak_db = 20 * np.log10(peak + 1e-10)

        # Silence detection (threshold-based)
        threshold = 0.01
        silence_samples = np.sum(np.abs(samples_float) < threshold)
        silence_ratio = silence_samples / len(samples_float)

        return AudioAnalysis(
            duration=duration,
            sample_rate=audio.sample_rate,
            channels=audio.channels,
            loudness_db=float(loudness_db),
            peak_db=float(peak_db),
            silence_ratio=float(silence_ratio),
            speech_ratio=float(1.0 - silence_ratio)
        )

    def detect_voice_activity(
        self,
        audio: AudioData,
        threshold: float = 0.02,
        min_speech_duration: float = 0.1
    ) -> List[Tuple[float, float]]:
        """Detect voice activity regions."""
        if not self._has_numpy:
            return [(0, audio.duration or 1.0)]

        import numpy as np

        samples = np.frombuffer(audio.data, dtype=np.int16)
        samples_float = samples.astype(np.float32) / 32768.0

        # Frame-based analysis
        frame_size = int(0.025 * audio.sample_rate)  # 25ms frames
        hop_size = int(0.010 * audio.sample_rate)    # 10ms hop

        regions = []
        in_speech = False
        speech_start = 0

        for i in range(0, len(samples_float) - frame_size, hop_size):
            frame = samples_float[i:i + frame_size]
            energy = np.sqrt(np.mean(frame ** 2))

            time_s = i / audio.sample_rate

            if energy > threshold:
                if not in_speech:
                    in_speech = True
                    speech_start = time_s
            else:
                if in_speech:
                    if time_s - speech_start >= min_speech_duration:
                        regions.append((speech_start, time_s))
                    in_speech = False

        # Handle case where speech extends to end
        if in_speech:
            end_time = len(samples_float) / audio.sample_rate
            if end_time - speech_start >= min_speech_duration:
                regions.append((speech_start, end_time))

        return regions


# =============================================================================
# SPEAKER DIARIZATION
# =============================================================================

class SpeakerDiarizer:
    """Speaker diarization for multi-speaker audio."""

    def __init__(self, num_speakers: Optional[int] = None):
        self.num_speakers = num_speakers

    async def diarize(
        self,
        audio: AudioData,
        transcription: Optional[TranscriptionResult] = None
    ) -> List[SpeakerSegment]:
        """Perform speaker diarization."""
        # Simplified implementation
        # In production, would use pyannote.audio or similar

        if transcription and transcription.segments:
            # Assign speakers based on segment patterns
            segments = []
            current_speaker = "SPEAKER_0"

            for i, seg in enumerate(transcription.segments):
                # Simple heuristic: switch speaker on long pauses
                if i > 0:
                    gap = seg.start - transcription.segments[i-1].end
                    if gap > 1.0:  # 1 second gap
                        current_speaker = f"SPEAKER_{(int(current_speaker[-1]) + 1) % (self.num_speakers or 2)}"

                segments.append(SpeakerSegment(
                    speaker_id=current_speaker,
                    start=seg.start,
                    end=seg.end,
                    confidence=0.8
                ))

            return segments

        # Default: single speaker
        return [SpeakerSegment(
            speaker_id="SPEAKER_0",
            start=0,
            end=audio.duration or 1.0,
            confidence=0.5
        )]


# =============================================================================
# AUDIO EFFECTS
# =============================================================================

class AudioEffects:
    """Audio effects processor."""

    def __init__(self):
        self._has_numpy = False
        try:
            import numpy as np
            self._has_numpy = True
        except ImportError:
            pass

    def normalize(self, audio: AudioData, target_db: float = -3.0) -> AudioData:
        """Normalize audio to target loudness."""
        if not self._has_numpy:
            return audio

        import numpy as np

        samples = np.frombuffer(audio.data, dtype=np.int16)
        samples_float = samples.astype(np.float32) / 32768.0

        # Calculate current peak
        peak = np.max(np.abs(samples_float))
        target_peak = 10 ** (target_db / 20)

        # Apply gain
        gain = target_peak / (peak + 1e-10)
        normalized = samples_float * gain

        # Clip and convert back
        normalized = np.clip(normalized, -1.0, 1.0)
        normalized_int = (normalized * 32767).astype(np.int16)

        return AudioData(
            data=normalized_int.tobytes(),
            format=audio.format,
            sample_rate=audio.sample_rate,
            channels=audio.channels,
            duration=audio.duration,
            metadata={**audio.metadata, "normalized": True}
        )

    def trim_silence(
        self,
        audio: AudioData,
        threshold: float = 0.01,
        min_silence_duration: float = 0.1
    ) -> AudioData:
        """Trim silence from audio."""
        if not self._has_numpy:
            return audio

        import numpy as np

        samples = np.frombuffer(audio.data, dtype=np.int16)
        samples_float = samples.astype(np.float32) / 32768.0

        # Find non-silent regions
        non_silent = np.abs(samples_float) > threshold

        # Find first and last non-silent sample
        non_silent_indices = np.where(non_silent)[0]
        if len(non_silent_indices) == 0:
            return audio

        start_idx = non_silent_indices[0]
        end_idx = non_silent_indices[-1]

        # Trim
        trimmed = samples[start_idx:end_idx + 1]

        return AudioData(
            data=trimmed.tobytes(),
            format=audio.format,
            sample_rate=audio.sample_rate,
            channels=audio.channels,
            duration=len(trimmed) / audio.sample_rate,
            metadata={**audio.metadata, "trimmed": True}
        )

    def change_speed(self, audio: AudioData, speed: float = 1.0) -> AudioData:
        """Change audio playback speed."""
        if not self._has_numpy or speed == 1.0:
            return audio

        import numpy as np
        from scipy import signal

        samples = np.frombuffer(audio.data, dtype=np.int16)

        # Resample
        new_length = int(len(samples) / speed)
        resampled = signal.resample(samples, new_length)
        resampled = np.clip(resampled, -32768, 32767).astype(np.int16)

        return AudioData(
            data=resampled.tobytes(),
            format=audio.format,
            sample_rate=audio.sample_rate,
            channels=audio.channels,
            duration=audio.duration / speed if audio.duration else None,
            metadata={**audio.metadata, "speed": speed}
        )


# =============================================================================
# MAIN AUDIO PROCESSOR
# =============================================================================

class AudioProcessor:
    """Main audio processing orchestrator."""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        elevenlabs_api_key: Optional[str] = None,
        whisper_model: str = "base"
    ):
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.elevenlabs_api_key = elevenlabs_api_key or os.getenv("ELEVENLABS_API_KEY")

        # Initialize providers
        self._transcription_providers: Dict[str, TranscriptionProvider] = {}
        self._tts_providers: Dict[str, TTSProvider] = {}

        if self.openai_api_key:
            self._transcription_providers["whisper_api"] = WhisperAPIProvider(self.openai_api_key)
            self._tts_providers["openai"] = OpenAITTSProvider(self.openai_api_key)

        if self.elevenlabs_api_key:
            self._tts_providers["elevenlabs"] = ElevenLabsTTSProvider(self.elevenlabs_api_key)

        self._transcription_providers["whisper_local"] = LocalWhisperProvider(whisper_model)

        # Initialize utilities
        self.analyzer = AudioAnalyzer()
        self.diarizer = SpeakerDiarizer()
        self.effects = AudioEffects()

    async def transcribe(
        self,
        audio: Union[AudioData, str, bytes],
        provider: str = "whisper_api",
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """Transcribe audio to text."""
        # Convert to AudioData if needed
        if isinstance(audio, str):
            audio = AudioData.from_file(audio)
        elif isinstance(audio, bytes):
            audio = AudioData(data=audio, format=AudioFormat.WAV)

        transcription_provider = self._transcription_providers.get(provider)
        if not transcription_provider:
            # Fallback to local
            transcription_provider = self._transcription_providers.get("whisper_local")

        return await transcription_provider.transcribe(audio, language)

    async def synthesize(
        self,
        text: str,
        provider: str = "openai",
        voice: str = "alloy",
        **kwargs
    ) -> AudioData:
        """Synthesize text to speech."""
        tts_provider = self._tts_providers.get(provider)
        if not tts_provider:
            raise ValueError(f"TTS provider not available: {provider}")

        return await tts_provider.synthesize(text, voice, **kwargs)

    async def transcribe_with_speakers(
        self,
        audio: Union[AudioData, str],
        language: Optional[str] = None,
        num_speakers: Optional[int] = None
    ) -> Tuple[TranscriptionResult, List[SpeakerSegment]]:
        """Transcribe with speaker diarization."""
        if isinstance(audio, str):
            audio = AudioData.from_file(audio)

        # Transcribe
        transcription = await self.transcribe(audio, language=language)

        # Diarize
        self.diarizer.num_speakers = num_speakers
        speakers = await self.diarizer.diarize(audio, transcription)

        return transcription, speakers

    def analyze(self, audio: Union[AudioData, str]) -> AudioAnalysis:
        """Analyze audio properties."""
        if isinstance(audio, str):
            audio = AudioData.from_file(audio)

        return self.analyzer.analyze(audio)

    def detect_speech_regions(
        self,
        audio: Union[AudioData, str],
        threshold: float = 0.02
    ) -> List[Tuple[float, float]]:
        """Detect speech/voice activity regions."""
        if isinstance(audio, str):
            audio = AudioData.from_file(audio)

        return self.analyzer.detect_voice_activity(audio, threshold)

    def normalize(self, audio: AudioData, target_db: float = -3.0) -> AudioData:
        """Normalize audio loudness."""
        return self.effects.normalize(audio, target_db)

    def trim_silence(self, audio: AudioData) -> AudioData:
        """Remove silence from beginning and end."""
        return self.effects.trim_silence(audio)

    def change_speed(self, audio: AudioData, speed: float) -> AudioData:
        """Change playback speed."""
        return self.effects.change_speed(audio, speed)

    async def stream_transcription(
        self,
        audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[str]:
        """Stream transcription from audio stream."""
        buffer = b""
        chunk_duration = 2.0  # Process 2 seconds at a time
        bytes_per_chunk = int(16000 * 2 * chunk_duration)  # 16kHz, 16-bit

        async for audio_bytes in audio_stream:
            buffer += audio_bytes

            while len(buffer) >= bytes_per_chunk:
                chunk = buffer[:bytes_per_chunk]
                buffer = buffer[bytes_per_chunk:]

                audio = AudioData(data=chunk, format=AudioFormat.WAV)
                result = await self.transcribe(audio)

                if result.text.strip():
                    yield result.text.strip()

        # Process remaining buffer
        if len(buffer) > 1000:  # At least some audio
            audio = AudioData(data=buffer, format=AudioFormat.WAV)
            result = await self.transcribe(audio)
            if result.text.strip():
                yield result.text.strip()


# =============================================================================
# REAL-TIME AUDIO HANDLER
# =============================================================================

class RealtimeAudioHandler:
    """Real-time audio streaming handler."""

    def __init__(self, processor: AudioProcessor):
        self.processor = processor
        self._listeners: List[Callable] = []
        self._running = False

    def on_transcription(self, callback: Callable[[str], None]) -> None:
        """Register transcription callback."""
        self._listeners.append(callback)

    async def start_listening(
        self,
        sample_rate: int = 16000,
        chunk_size: int = 1024
    ) -> None:
        """Start real-time audio capture and transcription."""
        try:
            import pyaudio
        except ImportError:
            logger.error("pyaudio not available for real-time audio")
            return

        self._running = True
        audio = pyaudio.PyAudio()

        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            input=True,
            frames_per_buffer=chunk_size
        )

        buffer = b""
        chunk_duration = 2.0
        bytes_needed = int(sample_rate * 2 * chunk_duration)

        try:
            while self._running:
                data = stream.read(chunk_size, exception_on_overflow=False)
                buffer += data

                if len(buffer) >= bytes_needed:
                    audio_data = AudioData(
                        data=buffer,
                        format=AudioFormat.WAV,
                        sample_rate=sample_rate
                    )

                    result = await self.processor.transcribe(audio_data)

                    if result.text.strip():
                        for listener in self._listeners:
                            try:
                                listener(result.text.strip())
                            except Exception as e:
                                logger.error(f"Listener error: {e}")

                    buffer = b""

                await asyncio.sleep(0.01)

        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()

    def stop_listening(self) -> None:
        """Stop real-time audio capture."""
        self._running = False


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def main():
    """Demonstrate audio processing."""
    print("=== BAEL Audio Processor ===\n")

    processor = AudioProcessor()

    # Demonstrate audio analysis
    print("--- Audio Analysis ---")

    # Create sample audio data (silence for demo)
    sample_audio = AudioData(
        data=bytes(16000 * 2),  # 1 second of silence
        format=AudioFormat.WAV,
        sample_rate=16000,
        channels=1,
        duration=1.0
    )

    analysis = processor.analyze(sample_audio)
    print(f"Duration: {analysis.duration:.2f}s")
    print(f"Sample rate: {analysis.sample_rate} Hz")
    print(f"Channels: {analysis.channels}")
    print(f"Loudness: {analysis.loudness_db:.1f} dB")
    print(f"Silence ratio: {analysis.silence_ratio:.1%}")

    # Demonstrate effects
    print("\n--- Audio Effects ---")
    normalized = processor.normalize(sample_audio)
    print(f"Normalized: {normalized.metadata}")

    trimmed = processor.trim_silence(sample_audio)
    print(f"Trimmed: {trimmed.metadata}")

    # TTS demo (if configured)
    print("\n--- Text-to-Speech ---")
    if processor.openai_api_key and processor.openai_api_key != "":
        try:
            audio = await processor.synthesize(
                "Hello, I am BAEL, the Lord of All AI Agents.",
                voice="onyx"
            )
            print(f"Generated {len(audio.data)} bytes of audio")
        except Exception as e:
            print(f"TTS requires valid API key: {e}")
    else:
        print("Set OPENAI_API_KEY for TTS functionality")

    # Transcription demo (if configured)
    print("\n--- Transcription ---")
    print("Providers available:")
    for name in processor._transcription_providers:
        print(f"  - {name}")

    print("\n=== Audio Processor ready ===")
    print("Set API keys for full functionality:")
    print("  OPENAI_API_KEY - Whisper & TTS")
    print("  ELEVENLABS_API_KEY - Premium TTS")


if __name__ == "__main__":
    asyncio.run(main())
