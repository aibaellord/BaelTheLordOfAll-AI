"""
BAEL - Voice Engine Manager
Manages voice input/output with multiple backends.
"""

import asyncio
import logging
import os
import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from . import TTSRequest, VoiceCommand, VoiceConfig, VoiceEngine, VoiceState

logger = logging.getLogger("BAEL.Voice.Engine")


class VoiceEngineManager:
    """
    Manages the complete voice interface.

    Features:
    - Multiple TTS/STT backends
    - Wake word detection
    - Continuous listening mode
    - Voice activity detection
    - Audio streaming
    """

    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()

        self._state = VoiceState.IDLE
        self._tts = None
        self._stt = None
        self._audio_queue: queue.Queue = queue.Queue()
        self._text_queue: queue.Queue = queue.Queue()
        self._running = False
        self._listen_thread: Optional[threading.Thread] = None
        self._callbacks: Dict[str, List[Callable]] = {
            "on_wake": [],
            "on_command": [],
            "on_speech_start": [],
            "on_speech_end": [],
            "on_error": []
        }

        self._initialize_engines()

    def _initialize_engines(self) -> None:
        """Initialize TTS and STT engines."""
        # Initialize TTS
        self._tts = self._create_tts_engine()

        # Initialize STT
        self._stt = self._create_stt_engine()

    def _create_tts_engine(self) -> Optional[Any]:
        """Create TTS engine based on config."""
        engine = self.config.tts_engine

        if engine == VoiceEngine.PYTTSX3:
            try:
                import pyttsx3
                tts = pyttsx3.init()
                tts.setProperty("rate", self.config.rate)
                tts.setProperty("volume", self.config.volume)

                # Set voice if specified
                if self.config.voice_id:
                    tts.setProperty("voice", self.config.voice_id)

                logger.info("Initialized pyttsx3 TTS engine")
                return tts
            except Exception as e:
                logger.warning(f"Failed to initialize pyttsx3: {e}")

        elif engine == VoiceEngine.GTTS:
            try:
                from gtts import gTTS
                logger.info("gTTS available (will create on demand)")
                return "gtts"  # Placeholder
            except ImportError:
                logger.warning("gTTS not available")

        elif engine == VoiceEngine.ESPEAK:
            # Check if espeak is available
            import subprocess
            try:
                subprocess.run(["espeak", "--version"], capture_output=True, check=True)
                logger.info("espeak available")
                return "espeak"
            except Exception:
                logger.warning("espeak not available")

        return None

    def _create_stt_engine(self) -> Optional[Any]:
        """Create STT engine based on config."""
        engine = self.config.stt_engine

        if engine == VoiceEngine.VOSK:
            try:
                from vosk import KaldiRecognizer, Model

                # Check for model
                model_path = os.environ.get("VOSK_MODEL_PATH", "models/vosk-model-small-en-us")
                if Path(model_path).exists():
                    model = Model(model_path)
                    logger.info("Initialized Vosk STT engine")
                    return {"type": "vosk", "model": model}
                else:
                    logger.warning(f"Vosk model not found at {model_path}")
            except ImportError:
                logger.warning("Vosk not available")

        elif engine == VoiceEngine.WHISPER:
            try:
                import whisper
                model = whisper.load_model("base")
                logger.info("Initialized Whisper STT engine")
                return {"type": "whisper", "model": model}
            except ImportError:
                logger.warning("Whisper not available")

        elif engine == VoiceEngine.SPEECH_RECOGNITION:
            try:
                import speech_recognition as sr
                recognizer = sr.Recognizer()
                logger.info("Initialized SpeechRecognition engine")
                return {"type": "sr", "recognizer": recognizer}
            except ImportError:
                logger.warning("SpeechRecognition not available")

        return None

    @property
    def state(self) -> VoiceState:
        """Get current voice state."""
        return self._state

    def add_callback(
        self,
        event: str,
        callback: Callable
    ) -> None:
        """Add a callback for voice events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _trigger_callbacks(self, event: str, *args) -> None:
        """Trigger callbacks for an event."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args)
            except Exception as e:
                logger.warning(f"Callback error for {event}: {e}")

    async def speak(
        self,
        text: str,
        voice_id: Optional[str] = None,
        wait: bool = True
    ) -> bool:
        """
        Speak text using TTS.

        Args:
            text: Text to speak
            voice_id: Optional voice override
            wait: Wait for speech to complete

        Returns:
            Success status
        """
        if not self._tts:
            logger.error("No TTS engine available")
            return False

        self._state = VoiceState.SPEAKING
        self._trigger_callbacks("on_speech_start", text)

        try:
            if isinstance(self._tts, str):
                if self._tts == "gtts":
                    await self._speak_gtts(text)
                elif self._tts == "espeak":
                    await self._speak_espeak(text)
            else:
                # pyttsx3
                self._tts.say(text)
                if wait:
                    self._tts.runAndWait()

            self._state = VoiceState.IDLE
            self._trigger_callbacks("on_speech_end")
            return True

        except Exception as e:
            logger.error(f"TTS error: {e}")
            self._state = VoiceState.ERROR
            self._trigger_callbacks("on_error", str(e))
            return False

    async def _speak_gtts(self, text: str) -> None:
        """Speak using gTTS."""
        import tempfile

        from gtts import gTTS

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tts = gTTS(text=text, lang=self.config.language[:2])
            tts.save(f.name)

            # Play the audio
            await self._play_audio(f.name)
            os.unlink(f.name)

    async def _speak_espeak(self, text: str) -> None:
        """Speak using espeak."""
        import subprocess
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                ["espeak", "-v", self.config.language[:2], text],
                capture_output=True
            )
        )

    async def _play_audio(self, filepath: str) -> None:
        """Play audio file."""
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
        except ImportError:
            # Fallback to system command
            import platform
            import subprocess

            system = platform.system()
            if system == "Darwin":
                subprocess.run(["afplay", filepath])
            elif system == "Linux":
                subprocess.run(["aplay", filepath])
            elif system == "Windows":
                os.startfile(filepath)

    async def listen(
        self,
        timeout: float = 5.0,
        phrase_time_limit: float = 10.0
    ) -> Optional[VoiceCommand]:
        """
        Listen for voice input.

        Args:
            timeout: Time to wait for speech to start
            phrase_time_limit: Maximum phrase duration

        Returns:
            Recognized voice command or None
        """
        if not self._stt:
            logger.error("No STT engine available")
            return None

        self._state = VoiceState.LISTENING

        try:
            if self._stt["type"] == "sr":
                return await self._listen_sr(timeout, phrase_time_limit)
            elif self._stt["type"] == "vosk":
                return await self._listen_vosk(timeout)
            elif self._stt["type"] == "whisper":
                return await self._listen_whisper(timeout)

        except Exception as e:
            logger.error(f"STT error: {e}")
            self._state = VoiceState.ERROR
            self._trigger_callbacks("on_error", str(e))

        finally:
            if self._state == VoiceState.LISTENING:
                self._state = VoiceState.IDLE

        return None

    async def _listen_sr(
        self,
        timeout: float,
        phrase_time_limit: float
    ) -> Optional[VoiceCommand]:
        """Listen using SpeechRecognition."""
        import speech_recognition as sr

        recognizer = self._stt["recognizer"]

        with sr.Microphone() as source:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)

            try:
                audio = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: recognizer.listen(
                        source,
                        timeout=timeout,
                        phrase_time_limit=phrase_time_limit
                    )
                )

                self._state = VoiceState.PROCESSING

                # Use Google Speech Recognition (free tier)
                text = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: recognizer.recognize_google(audio)
                )

                return VoiceCommand(
                    text=text,
                    confidence=0.9,
                    language=self.config.language,
                    duration=len(audio.frame_data) / audio.sample_rate,
                    timestamp=time.time()
                )

            except sr.WaitTimeoutError:
                logger.debug("No speech detected within timeout")
            except sr.UnknownValueError:
                logger.debug("Speech not recognized")
            except sr.RequestError as e:
                logger.error(f"Speech recognition API error: {e}")

        return None

    async def _listen_vosk(self, timeout: float) -> Optional[VoiceCommand]:
        """Listen using Vosk (offline)."""
        import json

        import pyaudio
        from vosk import KaldiRecognizer

        model = self._stt["model"]
        recognizer = KaldiRecognizer(model, 16000)

        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=4000
        )

        start_time = time.time()
        full_text = ""

        try:
            while time.time() - start_time < timeout:
                data = stream.read(4000, exception_on_overflow=False)

                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "")
                    if text:
                        full_text = text
                        break

            # Get final result
            final = json.loads(recognizer.FinalResult())
            if final.get("text"):
                full_text = final["text"]

            if full_text:
                return VoiceCommand(
                    text=full_text,
                    confidence=0.85,
                    language=self.config.language,
                    duration=time.time() - start_time,
                    timestamp=time.time()
                )

        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()

        return None

    async def _listen_whisper(self, timeout: float) -> Optional[VoiceCommand]:
        """Listen using Whisper (local)."""
        import tempfile
        import wave

        import pyaudio

        model = self._stt["model"]

        # Record audio
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

        try:
            while time.time() - start_time < timeout:
                data = stream.read(1024, exception_on_overflow=False)
                frames.append(data)
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wf = wave.open(f.name, "wb")
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"".join(frames))
            wf.close()

            self._state = VoiceState.PROCESSING

            # Transcribe
            result = model.transcribe(f.name)
            os.unlink(f.name)

            text = result.get("text", "").strip()
            if text:
                return VoiceCommand(
                    text=text,
                    confidence=0.95,
                    language=result.get("language", self.config.language),
                    duration=timeout,
                    timestamp=time.time()
                )

        return None

    async def start_continuous_listening(
        self,
        command_callback: Callable[[VoiceCommand], Awaitable[None]]
    ) -> None:
        """
        Start continuous listening mode.

        Args:
            command_callback: Async callback for recognized commands
        """
        self._running = True
        logger.info("Starting continuous listening mode")

        while self._running:
            try:
                # Check for wake word if configured
                if self.config.wake_word:
                    command = await self.listen(timeout=3.0)
                    if command and self.config.wake_word.lower() in command.text.lower():
                        self._trigger_callbacks("on_wake")
                        # Listen for actual command
                        await self.speak("Yes?")
                        command = await self.listen(timeout=5.0)
                else:
                    command = await self.listen(timeout=3.0)

                if command:
                    self._trigger_callbacks("on_command", command)
                    await command_callback(command)

                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Continuous listening error: {e}")
                await asyncio.sleep(1)

        logger.info("Continuous listening stopped")

    def stop_continuous_listening(self) -> None:
        """Stop continuous listening mode."""
        self._running = False

    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get available TTS voices."""
        voices = []

        if self._tts and hasattr(self._tts, "getProperty"):
            try:
                for voice in self._tts.getProperty("voices"):
                    voices.append({
                        "id": voice.id,
                        "name": voice.name,
                        "languages": voice.languages,
                        "gender": getattr(voice, "gender", "unknown")
                    })
            except Exception:
                pass

        return voices

    def set_voice(self, voice_id: str) -> bool:
        """Set the TTS voice."""
        if self._tts and hasattr(self._tts, "setProperty"):
            try:
                self._tts.setProperty("voice", voice_id)
                return True
            except Exception as e:
                logger.error(f"Failed to set voice: {e}")
        return False

    def get_status(self) -> Dict[str, Any]:
        """Get voice system status."""
        return {
            "state": self._state.value,
            "tts_available": self._tts is not None,
            "stt_available": self._stt is not None,
            "tts_engine": self.config.tts_engine.value,
            "stt_engine": self.config.stt_engine.value,
            "language": self.config.language,
            "wake_word": self.config.wake_word
        }


# Global instance
_voice_engine: Optional[VoiceEngineManager] = None


def get_voice_engine(
    config: Optional[VoiceConfig] = None
) -> VoiceEngineManager:
    """Get or create voice engine instance."""
    global _voice_engine
    if _voice_engine is None or config is not None:
        _voice_engine = VoiceEngineManager(config)
    return _voice_engine
