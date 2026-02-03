"""
BAEL - Voice Interface Module
Complete voice input/output with free TTS/STT options.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger("BAEL.Voice")


class VoiceEngine(Enum):
    """Available voice engines."""
    # TTS
    PYTTSX3 = "pyttsx3"           # Local, offline
    GTTS = "gtts"                  # Google TTS (free tier)
    ESPEAK = "espeak"              # Local, offline
    COQUI = "coqui"                # Open source neural TTS

    # STT
    VOSK = "vosk"                  # Local, offline
    WHISPER = "whisper"            # OpenAI Whisper (local)
    SPEECH_RECOGNITION = "sr"      # Google Speech Recognition


class VoiceState(Enum):
    """Voice system states."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass
class VoiceConfig:
    """Configuration for voice interface."""
    tts_engine: VoiceEngine = VoiceEngine.PYTTSX3
    stt_engine: VoiceEngine = VoiceEngine.VOSK
    voice_id: Optional[str] = None
    rate: int = 150
    volume: float = 1.0
    language: str = "en-US"
    wake_word: Optional[str] = "bael"
    auto_listen: bool = False


@dataclass
class VoiceCommand:
    """A voice command."""
    text: str
    confidence: float
    language: str
    duration: float
    timestamp: float


@dataclass
class TTSRequest:
    """A text-to-speech request."""
    text: str
    voice_id: Optional[str] = None
    rate: Optional[int] = None
    emotion: Optional[str] = None
    ssml: bool = False


# Lazy imports
def get_voice_engine():
    """Get the voice engine."""
    from .voice_engine import VoiceEngineManager
    return VoiceEngineManager()


def get_speech_recognizer():
    """Get the speech recognizer."""
    from .speech_recognition import SpeechRecognizer
    return SpeechRecognizer()


def get_text_to_speech():
    """Get the text-to-speech engine."""
    from .text_to_speech import TextToSpeech
    return TextToSpeech()


__all__ = [
    "VoiceEngine",
    "VoiceState",
    "VoiceConfig",
    "VoiceCommand",
    "TTSRequest",
    "get_voice_engine",
    "get_speech_recognizer",
    "get_text_to_speech"
]
