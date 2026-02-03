"""
BAEL - Speech Recognition Module
Multiple STT backends for voice input.
"""

import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import VoiceCommand, VoiceEngine

logger = logging.getLogger("BAEL.Voice.STT")


class STTBackend(ABC):
    """Abstract base class for STT backends."""

    @abstractmethod
    async def recognize(
        self,
        audio_data: bytes,
        sample_rate: int = 16000
    ) -> Optional[Tuple[str, float]]:
        """Recognize speech from audio data."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if backend is available."""
        pass


class VoskBackend(STTBackend):
    """Vosk offline speech recognition."""

    def __init__(self, model_path: Optional[str] = None):
        self._model = None
        self._model_path = model_path or os.environ.get(
            "VOSK_MODEL_PATH",
            "models/vosk-model-small-en-us"
        )
        self._initialize()

    def _initialize(self) -> None:
        """Initialize Vosk model."""
        try:
            from vosk import Model
            if Path(self._model_path).exists():
                self._model = Model(self._model_path)
                logger.info(f"Loaded Vosk model from {self._model_path}")
        except ImportError:
            logger.warning("Vosk not available")
        except Exception as e:
            logger.error(f"Failed to load Vosk model: {e}")

    def is_available(self) -> bool:
        return self._model is not None

    async def recognize(
        self,
        audio_data: bytes,
        sample_rate: int = 16000
    ) -> Optional[Tuple[str, float]]:
        """Recognize speech using Vosk."""
        if not self._model:
            return None

        try:
            import json

            from vosk import KaldiRecognizer

            recognizer = KaldiRecognizer(self._model, sample_rate)

            # Process audio
            if recognizer.AcceptWaveform(audio_data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "")
                if text:
                    return (text, 0.85)

            # Get final result
            final = json.loads(recognizer.FinalResult())
            text = final.get("text", "")
            if text:
                return (text, 0.85)

        except Exception as e:
            logger.error(f"Vosk recognition error: {e}")

        return None


class WhisperBackend(STTBackend):
    """OpenAI Whisper local speech recognition."""

    def __init__(self, model_size: str = "base"):
        self._model = None
        self._model_size = model_size
        self._initialize()

    def _initialize(self) -> None:
        """Initialize Whisper model."""
        try:
            import whisper
            self._model = whisper.load_model(self._model_size)
            logger.info(f"Loaded Whisper {self._model_size} model")
        except ImportError:
            logger.warning("Whisper not available")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")

    def is_available(self) -> bool:
        return self._model is not None

    async def recognize(
        self,
        audio_data: bytes,
        sample_rate: int = 16000
    ) -> Optional[Tuple[str, float]]:
        """Recognize speech using Whisper."""
        if not self._model:
            return None

        try:
            import tempfile
            import wave

            import numpy as np

            # Save audio to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wf = wave.open(f.name, "wb")
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_data)
                wf.close()

                # Transcribe
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._model.transcribe(f.name)
                )

                os.unlink(f.name)

                text = result.get("text", "").strip()
                if text:
                    return (text, 0.95)

        except Exception as e:
            logger.error(f"Whisper recognition error: {e}")

        return None


class GoogleSRBackend(STTBackend):
    """Google Speech Recognition via speech_recognition library."""

    def __init__(self):
        self._recognizer = None
        self._initialize()

    def _initialize(self) -> None:
        """Initialize speech_recognition."""
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            logger.info("Initialized Google Speech Recognition")
        except ImportError:
            logger.warning("speech_recognition not available")

    def is_available(self) -> bool:
        return self._recognizer is not None

    async def recognize(
        self,
        audio_data: bytes,
        sample_rate: int = 16000
    ) -> Optional[Tuple[str, float]]:
        """Recognize speech using Google SR."""
        if not self._recognizer:
            return None

        try:
            import speech_recognition as sr

            # Create AudioData object
            audio = sr.AudioData(audio_data, sample_rate, 2)

            # Recognize
            text = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._recognizer.recognize_google(audio)
            )

            if text:
                return (text, 0.9)

        except Exception as e:
            logger.error(f"Google SR error: {e}")

        return None


class SpeechRecognizer:
    """
    Multi-backend speech recognizer.

    Features:
    - Multiple backend support (Vosk, Whisper, Google)
    - Automatic fallback
    - Microphone handling
    - Voice activity detection
    """

    def __init__(self, preferred_backend: Optional[VoiceEngine] = None):
        self._backends: Dict[str, STTBackend] = {}
        self._preferred = preferred_backend
        self._audio = None

        self._initialize_backends()

    def _initialize_backends(self) -> None:
        """Initialize available backends."""
        # Try to initialize all backends
        backends = [
            ("vosk", VoskBackend()),
            ("whisper", WhisperBackend()),
            ("google", GoogleSRBackend())
        ]

        for name, backend in backends:
            if backend.is_available():
                self._backends[name] = backend
                logger.info(f"STT backend available: {name}")

    def get_available_backends(self) -> List[str]:
        """Get list of available backends."""
        return list(self._backends.keys())

    async def listen_and_recognize(
        self,
        timeout: float = 5.0,
        phrase_time_limit: float = 10.0,
        backend: Optional[str] = None
    ) -> Optional[VoiceCommand]:
        """
        Listen from microphone and recognize speech.

        Args:
            timeout: Time to wait for speech to start
            phrase_time_limit: Maximum phrase duration
            backend: Specific backend to use

        Returns:
            Recognized command or None
        """
        try:
            import pyaudio

            # Initialize audio
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )

            frames = []
            start_time = time.time()
            silence_start = None
            speaking = False

            try:
                while time.time() - start_time < timeout + phrase_time_limit:
                    data = stream.read(1024, exception_on_overflow=False)

                    # Simple VAD based on volume
                    import struct
                    samples = struct.unpack(f"{len(data)//2}h", data)
                    volume = sum(abs(s) for s in samples) / len(samples)

                    if volume > 500:  # Voice detected
                        speaking = True
                        silence_start = None
                        frames.append(data)
                    elif speaking:
                        frames.append(data)
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > 1.0:
                            # End of speech
                            break

                    # Check timeout
                    if not speaking and time.time() - start_time > timeout:
                        break

            finally:
                stream.stop_stream()
                stream.close()
                p.terminate()

            if not frames:
                return None

            audio_data = b"".join(frames)

            # Recognize
            result = await self.recognize(audio_data, backend=backend)

            if result:
                return VoiceCommand(
                    text=result[0],
                    confidence=result[1],
                    language="en",
                    duration=len(audio_data) / 32000,  # 16kHz, 2 bytes
                    timestamp=time.time()
                )

        except ImportError:
            logger.error("PyAudio not available for microphone input")
        except Exception as e:
            logger.error(f"Listen error: {e}")

        return None

    async def recognize(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        backend: Optional[str] = None
    ) -> Optional[Tuple[str, float]]:
        """
        Recognize speech from audio data.

        Args:
            audio_data: Raw audio bytes
            sample_rate: Audio sample rate
            backend: Specific backend to use

        Returns:
            Tuple of (text, confidence) or None
        """
        if not self._backends:
            logger.error("No STT backends available")
            return None

        # Use specified backend
        if backend and backend in self._backends:
            return await self._backends[backend].recognize(audio_data, sample_rate)

        # Use preferred backend
        if self._preferred:
            preferred_name = self._preferred.value
            if preferred_name in self._backends:
                result = await self._backends[preferred_name].recognize(
                    audio_data, sample_rate
                )
                if result:
                    return result

        # Try all backends with fallback
        for name, backend_instance in self._backends.items():
            try:
                result = await backend_instance.recognize(audio_data, sample_rate)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Backend {name} failed: {e}")
                continue

        return None

    async def recognize_file(
        self,
        filepath: str,
        backend: Optional[str] = None
    ) -> Optional[Tuple[str, float]]:
        """
        Recognize speech from audio file.

        Args:
            filepath: Path to audio file
            backend: Specific backend to use

        Returns:
            Tuple of (text, confidence) or None
        """
        try:
            import wave

            with wave.open(filepath, "rb") as wf:
                sample_rate = wf.getframerate()
                audio_data = wf.readframes(wf.getnframes())

                return await self.recognize(
                    audio_data,
                    sample_rate=sample_rate,
                    backend=backend
                )

        except Exception as e:
            logger.error(f"Failed to read audio file: {e}")

        return None


# Global instance
_speech_recognizer: Optional[SpeechRecognizer] = None


def get_speech_recognizer(
    preferred_backend: Optional[VoiceEngine] = None
) -> SpeechRecognizer:
    """Get or create speech recognizer instance."""
    global _speech_recognizer
    if _speech_recognizer is None:
        _speech_recognizer = SpeechRecognizer(preferred_backend)
    return _speech_recognizer
