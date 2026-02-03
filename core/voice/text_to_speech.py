"""
BAEL - Text to Speech Module
Multiple TTS backends for voice output.
"""

import asyncio
import logging
import os
import platform
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import TTSRequest, VoiceEngine

logger = logging.getLogger("BAEL.Voice.TTS")


class TTSBackend(ABC):
    """Abstract base class for TTS backends."""

    @abstractmethod
    async def speak(self, text: str) -> bool:
        """Speak text."""
        pass

    @abstractmethod
    async def synthesize(self, text: str) -> Optional[bytes]:
        """Synthesize speech to audio bytes."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if backend is available."""
        pass

    @abstractmethod
    def get_voices(self) -> List[Dict[str, Any]]:
        """Get available voices."""
        pass


class Pyttsx3Backend(TTSBackend):
    """pyttsx3 local TTS backend."""

    def __init__(self):
        self._engine = None
        self._initialize()

    def _initialize(self) -> None:
        """Initialize pyttsx3."""
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            logger.info("Initialized pyttsx3 TTS")
        except Exception as e:
            logger.warning(f"pyttsx3 not available: {e}")

    def is_available(self) -> bool:
        return self._engine is not None

    async def speak(self, text: str) -> bool:
        """Speak text using pyttsx3."""
        if not self._engine:
            return False

        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: (self._engine.say(text), self._engine.runAndWait())
            )
            return True
        except Exception as e:
            logger.error(f"pyttsx3 speak error: {e}")
            return False

    async def synthesize(self, text: str) -> Optional[bytes]:
        """Synthesize to audio bytes."""
        if not self._engine:
            return None

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                self._engine.save_to_file(text, f.name)
                self._engine.runAndWait()

                with open(f.name, "rb") as audio_file:
                    audio_data = audio_file.read()

                os.unlink(f.name)
                return audio_data
        except Exception as e:
            logger.error(f"pyttsx3 synthesize error: {e}")
            return None

    def get_voices(self) -> List[Dict[str, Any]]:
        """Get available voices."""
        if not self._engine:
            return []

        voices = []
        for voice in self._engine.getProperty("voices"):
            voices.append({
                "id": voice.id,
                "name": voice.name,
                "languages": getattr(voice, "languages", []),
                "gender": getattr(voice, "gender", "unknown"),
                "backend": "pyttsx3"
            })
        return voices

    def set_voice(self, voice_id: str) -> bool:
        """Set voice."""
        if self._engine:
            try:
                self._engine.setProperty("voice", voice_id)
                return True
            except Exception:
                pass
        return False

    def set_rate(self, rate: int) -> bool:
        """Set speech rate."""
        if self._engine:
            try:
                self._engine.setProperty("rate", rate)
                return True
            except Exception:
                pass
        return False


class GTTSBackend(TTSBackend):
    """Google Text-to-Speech backend."""

    def __init__(self, language: str = "en"):
        self._available = False
        self._language = language
        self._initialize()

    def _initialize(self) -> None:
        """Check if gTTS is available."""
        try:
            from gtts import gTTS
            self._available = True
            logger.info("gTTS available")
        except ImportError:
            logger.warning("gTTS not available")

    def is_available(self) -> bool:
        return self._available

    async def speak(self, text: str) -> bool:
        """Speak text using gTTS."""
        audio_data = await self.synthesize(text)
        if not audio_data:
            return False

        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(audio_data)
                await self._play_audio(f.name)
                os.unlink(f.name)
            return True
        except Exception as e:
            logger.error(f"gTTS playback error: {e}")
            return False

    async def synthesize(self, text: str) -> Optional[bytes]:
        """Synthesize to audio bytes."""
        if not self._available:
            return None

        try:
            import io

            from gtts import gTTS

            tts = gTTS(text=text, lang=self._language)
            buffer = io.BytesIO()
            tts.write_to_fp(buffer)
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"gTTS synthesize error: {e}")
            return None

    async def _play_audio(self, filepath: str) -> None:
        """Play audio file."""
        system = platform.system()

        try:
            import subprocess

            if system == "Darwin":
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: subprocess.run(["afplay", filepath], check=True)
                )
            elif system == "Linux":
                # Try various players
                for player in ["mpg123", "mpv", "aplay"]:
                    try:
                        await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda p=player: subprocess.run([p, filepath], check=True)
                        )
                        break
                    except Exception:
                        continue
            elif system == "Windows":
                os.startfile(filepath)
        except Exception as e:
            logger.error(f"Audio playback error: {e}")

    def get_voices(self) -> List[Dict[str, Any]]:
        """gTTS doesn't have multiple voices, just languages."""
        return [
            {"id": "en", "name": "English", "backend": "gtts"},
            {"id": "es", "name": "Spanish", "backend": "gtts"},
            {"id": "fr", "name": "French", "backend": "gtts"},
            {"id": "de", "name": "German", "backend": "gtts"},
            {"id": "it", "name": "Italian", "backend": "gtts"},
            {"id": "ja", "name": "Japanese", "backend": "gtts"},
            {"id": "ko", "name": "Korean", "backend": "gtts"},
            {"id": "zh-CN", "name": "Chinese (Simplified)", "backend": "gtts"},
        ]


class EspeakBackend(TTSBackend):
    """espeak local TTS backend."""

    def __init__(self):
        self._available = False
        self._initialize()

    def _initialize(self) -> None:
        """Check if espeak is available."""
        import subprocess
        try:
            subprocess.run(
                ["espeak", "--version"],
                capture_output=True,
                check=True
            )
            self._available = True
            logger.info("espeak available")
        except Exception:
            logger.warning("espeak not available")

    def is_available(self) -> bool:
        return self._available

    async def speak(self, text: str) -> bool:
        """Speak text using espeak."""
        if not self._available:
            return False

        try:
            import subprocess
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(["espeak", text], check=True)
            )
            return True
        except Exception as e:
            logger.error(f"espeak error: {e}")
            return False

    async def synthesize(self, text: str) -> Optional[bytes]:
        """Synthesize to audio bytes."""
        if not self._available:
            return None

        try:
            import subprocess

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                subprocess.run(
                    ["espeak", "-w", f.name, text],
                    check=True
                )

                with open(f.name, "rb") as audio_file:
                    audio_data = audio_file.read()

                os.unlink(f.name)
                return audio_data
        except Exception as e:
            logger.error(f"espeak synthesize error: {e}")
            return None

    def get_voices(self) -> List[Dict[str, Any]]:
        """Get espeak voices."""
        voices = []
        try:
            import subprocess
            result = subprocess.run(
                ["espeak", "--voices"],
                capture_output=True,
                text=True
            )

            for line in result.stdout.strip().split("\n")[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 4:
                    voices.append({
                        "id": parts[4] if len(parts) > 4 else parts[0],
                        "name": parts[3] if len(parts) > 3 else parts[0],
                        "language": parts[1] if len(parts) > 1 else "en",
                        "backend": "espeak"
                    })
        except Exception:
            pass

        return voices


class TextToSpeech:
    """
    Multi-backend text-to-speech engine.

    Features:
    - Multiple backend support
    - Automatic fallback
    - Voice selection
    - Rate and volume control
    - Audio file generation
    """

    def __init__(self, preferred_backend: Optional[VoiceEngine] = None):
        self._backends: Dict[str, TTSBackend] = {}
        self._preferred = preferred_backend
        self._current_backend: Optional[str] = None

        self._initialize_backends()

    def _initialize_backends(self) -> None:
        """Initialize available backends."""
        backends = [
            ("pyttsx3", Pyttsx3Backend()),
            ("gtts", GTTSBackend()),
            ("espeak", EspeakBackend())
        ]

        for name, backend in backends:
            if backend.is_available():
                self._backends[name] = backend
                if self._current_backend is None:
                    self._current_backend = name
                logger.info(f"TTS backend available: {name}")

    def get_available_backends(self) -> List[str]:
        """Get list of available backends."""
        return list(self._backends.keys())

    async def speak(
        self,
        text: str,
        backend: Optional[str] = None
    ) -> bool:
        """
        Speak text.

        Args:
            text: Text to speak
            backend: Specific backend to use

        Returns:
            Success status
        """
        if not self._backends:
            logger.error("No TTS backends available")
            return False

        # Select backend
        backend_name = backend or self._current_backend
        if backend_name and backend_name in self._backends:
            result = await self._backends[backend_name].speak(text)
            if result:
                return True

        # Fallback to other backends
        for name, backend_instance in self._backends.items():
            if name != backend_name:
                try:
                    result = await backend_instance.speak(text)
                    if result:
                        return True
                except Exception:
                    continue

        return False

    async def synthesize(
        self,
        text: str,
        backend: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Synthesize speech to audio bytes.

        Args:
            text: Text to synthesize
            backend: Specific backend to use

        Returns:
            Audio bytes or None
        """
        if not self._backends:
            return None

        backend_name = backend or self._current_backend
        if backend_name and backend_name in self._backends:
            result = await self._backends[backend_name].synthesize(text)
            if result:
                return result

        # Fallback
        for name, backend_instance in self._backends.items():
            if name != backend_name:
                try:
                    result = await backend_instance.synthesize(text)
                    if result:
                        return result
                except Exception:
                    continue

        return None

    async def save_to_file(
        self,
        text: str,
        filepath: str,
        backend: Optional[str] = None
    ) -> bool:
        """
        Save synthesized speech to file.

        Args:
            text: Text to synthesize
            filepath: Output file path
            backend: Specific backend to use

        Returns:
            Success status
        """
        audio_data = await self.synthesize(text, backend)
        if not audio_data:
            return False

        try:
            with open(filepath, "wb") as f:
                f.write(audio_data)
            return True
        except Exception as e:
            logger.error(f"Failed to save audio: {e}")
            return False

    def get_all_voices(self) -> List[Dict[str, Any]]:
        """Get all voices from all backends."""
        voices = []
        for name, backend in self._backends.items():
            try:
                voices.extend(backend.get_voices())
            except Exception:
                pass
        return voices

    def set_backend(self, backend: str) -> bool:
        """Set preferred backend."""
        if backend in self._backends:
            self._current_backend = backend
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        """Get TTS status."""
        return {
            "backends_available": list(self._backends.keys()),
            "current_backend": self._current_backend,
            "voice_count": len(self.get_all_voices())
        }


# Global instance
_text_to_speech: Optional[TextToSpeech] = None


def get_text_to_speech(
    preferred_backend: Optional[VoiceEngine] = None
) -> TextToSpeech:
    """Get or create text-to-speech instance."""
    global _text_to_speech
    if _text_to_speech is None:
        _text_to_speech = TextToSpeech(preferred_backend)
    return _text_to_speech
