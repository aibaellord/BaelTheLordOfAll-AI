"""
BAEL TTS Engine
================

Multi-provider text-to-speech synthesis.
Enables voice output for BAEL responses.

Features:
- Multiple TTS providers
- Voice selection
- SSML support
- Streaming audio output
- Local and cloud synthesis
- Voice cloning support
"""

import asyncio
import base64
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TTSProvider(Enum):
    """TTS providers."""
    # Cloud providers
    OPENAI = "openai"
    GOOGLE = "google"
    AZURE = "azure"
    AWS_POLLY = "aws_polly"
    ELEVENLABS = "elevenlabs"

    # Local/free providers
    PYTTSX3 = "pyttsx3"
    ESPEAK = "espeak"
    COQUI = "coqui"
    BARK = "bark"

    # System
    SYSTEM = "system"


@dataclass
class Voice:
    """Voice definition."""
    id: str
    name: str
    language: str = "en-US"
    gender: str = "neutral"  # male, female, neutral
    provider: TTSProvider = TTSProvider.SYSTEM

    # Voice characteristics
    pitch: float = 1.0
    rate: float = 1.0

    # Preview
    preview_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "language": self.language,
            "gender": self.gender,
            "provider": self.provider.value,
        }


@dataclass
class TTSConfig:
    """TTS configuration."""
    provider: TTSProvider = TTSProvider.PYTTSX3
    api_key: Optional[str] = None

    # Voice
    voice_id: Optional[str] = None
    language: str = "en-US"

    # Speech parameters
    rate: float = 1.0       # Speech rate multiplier
    pitch: float = 1.0      # Pitch multiplier
    volume: float = 1.0     # Volume (0-1)

    # Audio format
    sample_rate: int = 24000
    audio_format: str = "mp3"  # mp3, wav, ogg

    # Streaming
    enable_streaming: bool = True
    chunk_size: int = 4096


@dataclass
class TTSResult:
    """TTS synthesis result."""
    audio_data: bytes
    audio_format: str = "mp3"
    sample_rate: int = 24000
    duration_seconds: float = 0.0

    # Metadata
    text_length: int = 0
    processing_time_ms: float = 0.0

    # Error
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and len(self.audio_data) > 0


class TTSEngine:
    """
    Multi-provider TTS engine for BAEL.
    """

    # Built-in voices
    DEFAULT_VOICES = {
        TTSProvider.OPENAI: [
            Voice("alloy", "Alloy", "en-US", "neutral", TTSProvider.OPENAI),
            Voice("echo", "Echo", "en-US", "male", TTSProvider.OPENAI),
            Voice("fable", "Fable", "en-US", "female", TTSProvider.OPENAI),
            Voice("onyx", "Onyx", "en-US", "male", TTSProvider.OPENAI),
            Voice("nova", "Nova", "en-US", "female", TTSProvider.OPENAI),
            Voice("shimmer", "Shimmer", "en-US", "female", TTSProvider.OPENAI),
        ],
        TTSProvider.ELEVENLABS: [
            Voice("21m00Tcm4TlvDq8ikWAM", "Rachel", "en-US", "female", TTSProvider.ELEVENLABS),
            Voice("AZnzlk1XvdvUeBnXmlld", "Domi", "en-US", "female", TTSProvider.ELEVENLABS),
            Voice("EXAVITQu4vr4xnSDxMaL", "Bella", "en-US", "female", TTSProvider.ELEVENLABS),
            Voice("ErXwobaYiN019PkySvjV", "Antoni", "en-US", "male", TTSProvider.ELEVENLABS),
            Voice("MF3mGyEYCl7XYWbV9V6O", "Elli", "en-US", "female", TTSProvider.ELEVENLABS),
            Voice("TxGEqnHWrfWFTfGW9XjX", "Josh", "en-US", "male", TTSProvider.ELEVENLABS),
        ],
    }

    def __init__(
        self,
        config: Optional[TTSConfig] = None,
    ):
        self.config = config or TTSConfig()

        # Engine instance (lazy loaded)
        self._engine = None

        # Voice cache
        self._voices: Dict[str, Voice] = {}

        # Stats
        self.stats = {
            "total_syntheses": 0,
            "successful_syntheses": 0,
            "characters_synthesized": 0,
            "total_audio_seconds": 0.0,
            "total_processing_ms": 0.0,
        }

    async def synthesize(
        self,
        text: str,
        voice: Optional[Voice] = None,
    ) -> TTSResult:
        """
        Synthesize speech from text.

        Args:
            text: Text to synthesize
            voice: Optional voice override

        Returns:
            TTSResult
        """
        if not text.strip():
            return TTSResult(
                audio_data=b"",
                error="Empty text",
            )

        self.stats["total_syntheses"] += 1
        start_time = time.monotonic()

        try:
            if self.config.provider == TTSProvider.OPENAI:
                result = await self._synthesize_openai(text, voice)
            elif self.config.provider == TTSProvider.ELEVENLABS:
                result = await self._synthesize_elevenlabs(text, voice)
            elif self.config.provider == TTSProvider.GOOGLE:
                result = await self._synthesize_google(text, voice)
            elif self.config.provider == TTSProvider.PYTTSX3:
                result = await self._synthesize_pyttsx3(text, voice)
            elif self.config.provider == TTSProvider.COQUI:
                result = await self._synthesize_coqui(text, voice)
            else:
                result = await self._synthesize_pyttsx3(text, voice)

            elapsed = (time.monotonic() - start_time) * 1000
            result.processing_time_ms = elapsed
            result.text_length = len(text)

            if result.success:
                self.stats["successful_syntheses"] += 1
                self.stats["characters_synthesized"] += len(text)
                self.stats["total_audio_seconds"] += result.duration_seconds

            self.stats["total_processing_ms"] += elapsed

            return result

        except Exception as e:
            logger.error(f"TTS error: {e}")
            return TTSResult(
                audio_data=b"",
                error=str(e),
            )

    async def synthesize_stream(
        self,
        text: str,
        voice: Optional[Voice] = None,
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream synthesized audio.

        Args:
            text: Text to synthesize
            voice: Optional voice override

        Yields:
            Audio chunks
        """
        if self.config.provider == TTSProvider.OPENAI:
            async for chunk in self._stream_openai(text, voice):
                yield chunk
        elif self.config.provider == TTSProvider.ELEVENLABS:
            async for chunk in self._stream_elevenlabs(text, voice):
                yield chunk
        else:
            # Fallback to non-streaming
            result = await self.synthesize(text, voice)
            if result.success:
                for i in range(0, len(result.audio_data), self.config.chunk_size):
                    yield result.audio_data[i:i+self.config.chunk_size]

    async def _synthesize_openai(
        self,
        text: str,
        voice: Optional[Voice] = None,
    ) -> TTSResult:
        """Synthesize using OpenAI TTS."""
        try:
            import httpx
        except ImportError:
            return TTSResult(audio_data=b"", error="httpx not installed")

        if not self.config.api_key:
            return TTSResult(audio_data=b"", error="OpenAI API key required")

        voice_id = voice.id if voice else (self.config.voice_id or "alloy")

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "tts-1",
                        "input": text,
                        "voice": voice_id,
                        "response_format": self.config.audio_format,
                        "speed": self.config.rate,
                    },
                )

                if response.status_code != 200:
                    return TTSResult(
                        audio_data=b"",
                        error=f"API error: {response.status_code}",
                    )

                return TTSResult(
                    audio_data=response.content,
                    audio_format=self.config.audio_format,
                    sample_rate=self.config.sample_rate,
                )

        except Exception as e:
            return TTSResult(audio_data=b"", error=str(e))

    async def _stream_openai(
        self,
        text: str,
        voice: Optional[Voice] = None,
    ) -> AsyncGenerator[bytes, None]:
        """Stream from OpenAI TTS."""
        try:
            import httpx
        except ImportError:
            return

        if not self.config.api_key:
            return

        voice_id = voice.id if voice else (self.config.voice_id or "alloy")

        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": voice_id,
                    "response_format": self.config.audio_format,
                    "speed": self.config.rate,
                },
            ) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk

    async def _synthesize_elevenlabs(
        self,
        text: str,
        voice: Optional[Voice] = None,
    ) -> TTSResult:
        """Synthesize using ElevenLabs."""
        try:
            import httpx
        except ImportError:
            return TTSResult(audio_data=b"", error="httpx not installed")

        if not self.config.api_key:
            return TTSResult(audio_data=b"", error="ElevenLabs API key required")

        voice_id = voice.id if voice else (self.config.voice_id or "21m00Tcm4TlvDq8ikWAM")

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    headers={
                        "xi-api-key": self.config.api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_monolingual_v1",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75,
                        },
                    },
                )

                if response.status_code != 200:
                    return TTSResult(
                        audio_data=b"",
                        error=f"API error: {response.status_code}",
                    )

                return TTSResult(
                    audio_data=response.content,
                    audio_format="mp3",
                    sample_rate=44100,
                )

        except Exception as e:
            return TTSResult(audio_data=b"", error=str(e))

    async def _stream_elevenlabs(
        self,
        text: str,
        voice: Optional[Voice] = None,
    ) -> AsyncGenerator[bytes, None]:
        """Stream from ElevenLabs."""
        try:
            import httpx
        except ImportError:
            return

        if not self.config.api_key:
            return

        voice_id = voice.id if voice else (self.config.voice_id or "21m00Tcm4TlvDq8ikWAM")

        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream",
                headers={
                    "xi-api-key": self.config.api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                },
            ) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk

    async def _synthesize_google(
        self,
        text: str,
        voice: Optional[Voice] = None,
    ) -> TTSResult:
        """Synthesize using Google Cloud TTS."""
        try:
            from google.cloud import texttospeech
        except ImportError:
            return TTSResult(
                audio_data=b"",
                error="google-cloud-texttospeech not installed",
            )

        client = texttospeech.TextToSpeechClient()

        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice_params = texttospeech.VoiceSelectionParams(
            language_code=self.config.language,
            name=voice.id if voice else None,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=self.config.rate,
            pitch=self.config.pitch,
        )

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice_params,
            audio_config=audio_config,
        )

        return TTSResult(
            audio_data=response.audio_content,
            audio_format="mp3",
            sample_rate=24000,
        )

    async def _synthesize_pyttsx3(
        self,
        text: str,
        voice: Optional[Voice] = None,
    ) -> TTSResult:
        """Synthesize using pyttsx3 (offline)."""
        try:
            import os
            import tempfile

            import pyttsx3
        except ImportError:
            return TTSResult(
                audio_data=b"",
                error="pyttsx3 not installed. Run: pip install pyttsx3",
            )

        try:
            engine = pyttsx3.init()

            # Set properties
            engine.setProperty('rate', int(200 * self.config.rate))
            engine.setProperty('volume', self.config.volume)

            # Set voice if specified
            if voice:
                voices = engine.getProperty('voices')
                for v in voices:
                    if voice.id in v.id:
                        engine.setProperty('voice', v.id)
                        break

            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name

            engine.save_to_file(text, temp_path)
            engine.runAndWait()

            with open(temp_path, "rb") as f:
                audio_data = f.read()

            os.unlink(temp_path)

            return TTSResult(
                audio_data=audio_data,
                audio_format="wav",
                sample_rate=22050,
            )

        except Exception as e:
            return TTSResult(audio_data=b"", error=str(e))

    async def _synthesize_coqui(
        self,
        text: str,
        voice: Optional[Voice] = None,
    ) -> TTSResult:
        """Synthesize using Coqui TTS (offline, high quality)."""
        try:
            from TTS.api import TTS
        except ImportError:
            return TTSResult(
                audio_data=b"",
                error="TTS not installed. Run: pip install TTS",
            )

        try:
            # Initialize TTS model
            tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")

            # Generate speech
            import os
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name

            tts.tts_to_file(text=text, file_path=temp_path)

            with open(temp_path, "rb") as f:
                audio_data = f.read()

            os.unlink(temp_path)

            return TTSResult(
                audio_data=audio_data,
                audio_format="wav",
                sample_rate=22050,
            )

        except Exception as e:
            return TTSResult(audio_data=b"", error=str(e))

    def list_voices(
        self,
        provider: Optional[TTSProvider] = None,
    ) -> List[Voice]:
        """List available voices."""
        target_provider = provider or self.config.provider

        if target_provider in self.DEFAULT_VOICES:
            return self.DEFAULT_VOICES[target_provider]

        # For local providers, try to get system voices
        if target_provider == TTSProvider.PYTTSX3:
            try:
                import pyttsx3
                engine = pyttsx3.init()
                voices = engine.getProperty('voices')
                return [
                    Voice(
                        id=v.id,
                        name=v.name,
                        language=v.languages[0] if v.languages else "en-US",
                        gender=v.gender or "neutral",
                        provider=TTSProvider.PYTTSX3,
                    )
                    for v in voices
                ]
            except:
                pass

        return []

    async def play_audio(
        self,
        audio_data: bytes,
        audio_format: str = "mp3",
    ) -> bool:
        """
        Play audio data through speakers.

        Args:
            audio_data: Audio bytes
            audio_format: Audio format

        Returns:
            Success status
        """
        try:
            import io

            import pygame

            pygame.mixer.init()
            sound = pygame.mixer.Sound(io.BytesIO(audio_data))
            sound.play()

            # Wait for playback to finish
            while pygame.mixer.get_busy():
                await asyncio.sleep(0.1)

            return True

        except ImportError:
            logger.warning("pygame not installed for audio playback")
            return False
        except Exception as e:
            logger.error(f"Playback error: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        avg_time = 0.0
        if self.stats["total_syntheses"] > 0:
            avg_time = self.stats["total_processing_ms"] / self.stats["total_syntheses"]

        return {
            **self.stats,
            "provider": self.config.provider.value,
            "avg_processing_time_ms": avg_time,
        }


def demo():
    """Demonstrate TTS engine."""
    print("=" * 60)
    print("BAEL TTS Engine Demo")
    print("=" * 60)

    config = TTSConfig(
        provider=TTSProvider.PYTTSX3,
        rate=1.0,
    )

    engine = TTSEngine(config)

    print(f"\nTTS configuration:")
    print(f"  Provider: {config.provider.value}")
    print(f"  Rate: {config.rate}")
    print(f"  Audio format: {config.audio_format}")

    # List voices
    voices = engine.list_voices()
    print(f"\nAvailable voices: {len(voices)}")
    for v in voices[:3]:
        print(f"  • {v.name} ({v.language}, {v.gender})")

    print(f"\nStats: {engine.get_stats()}")


if __name__ == "__main__":
    demo()
