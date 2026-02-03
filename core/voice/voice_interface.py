"""
BAEL - Voice Interface
Speech recognition and synthesis for voice interactions.

Features:
- Speech-to-text
- Text-to-speech
- Voice commands
- Wake word detection
- Multi-language support
- Voice authentication
"""

import asyncio
import base64
import io
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("BAEL.Voice")


# =============================================================================
# TYPES & ENUMS
# =============================================================================

class VoiceState(Enum):
    """Voice interface state."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


class AudioFormat(Enum):
    """Audio formats."""
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    WEBM = "webm"
    RAW = "raw"


class Language(Enum):
    """Supported languages."""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    DUTCH = "nl"
    RUSSIAN = "ru"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"


@dataclass
class VoiceConfig:
    """Voice interface configuration."""
    language: Language = Language.ENGLISH

    # Speech recognition
    sample_rate: int = 16000
    channels: int = 1

    # Text-to-speech
    voice_id: str = "default"
    speed: float = 1.0
    pitch: float = 1.0

    # Wake word
    wake_word: str = "hey bael"
    wake_word_sensitivity: float = 0.5

    # Processing
    silence_threshold: float = 0.03
    silence_duration: float = 1.0  # seconds
    max_recording_duration: float = 30.0


@dataclass
class Utterance:
    """A recognized utterance."""
    id: str
    text: str
    language: Language
    confidence: float

    # Timing
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0

    # Metadata
    is_final: bool = True
    alternatives: List[str] = field(default_factory=list)

    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SynthesizedSpeech:
    """Synthesized speech result."""
    text: str
    audio_data: bytes
    audio_format: AudioFormat
    duration: float
    voice_id: str


@dataclass
class VoiceCommand:
    """A registered voice command."""
    phrases: List[str]
    handler: Callable
    description: str
    requires_confirmation: bool = False


# =============================================================================
# SPEECH RECOGNIZER (ABSTRACT)
# =============================================================================

class SpeechRecognizer:
    """Abstract speech recognition interface."""

    def __init__(self, config: VoiceConfig):
        self.config = config
        self._callbacks: List[Callable[[Utterance], None]] = []

    async def start(self) -> None:
        """Start recognition."""
        raise NotImplementedError

    async def stop(self) -> None:
        """Stop recognition."""
        raise NotImplementedError

    async def recognize(self, audio_data: bytes) -> Optional[Utterance]:
        """Recognize speech from audio data."""
        raise NotImplementedError

    def on_utterance(self, callback: Callable[[Utterance], None]) -> None:
        """Register utterance callback."""
        self._callbacks.append(callback)

    def _notify_callbacks(self, utterance: Utterance) -> None:
        """Notify all callbacks."""
        for callback in self._callbacks:
            try:
                callback(utterance)
            except Exception as e:
                logger.error(f"Utterance callback error: {e}")


class LocalSpeechRecognizer(SpeechRecognizer):
    """Local speech recognition (simulated)."""

    async def start(self) -> None:
        """Start recognition."""
        logger.info("Local speech recognizer started")

    async def stop(self) -> None:
        """Stop recognition."""
        logger.info("Local speech recognizer stopped")

    async def recognize(self, audio_data: bytes) -> Optional[Utterance]:
        """Recognize speech from audio data."""
        # Simulated recognition
        # In real implementation, would use Whisper, Vosk, or similar

        utterance = Utterance(
            id=f"utt_{id(audio_data)}",
            text="Simulated recognition result",
            language=self.config.language,
            confidence=0.95,
            duration=len(audio_data) / (self.config.sample_rate * 2)
        )

        self._notify_callbacks(utterance)
        return utterance


class CloudSpeechRecognizer(SpeechRecognizer):
    """Cloud-based speech recognition."""

    def __init__(self, config: VoiceConfig, api_key: str = None):
        super().__init__(config)
        self.api_key = api_key

    async def start(self) -> None:
        """Start recognition."""
        logger.info("Cloud speech recognizer started")

    async def stop(self) -> None:
        """Stop recognition."""
        logger.info("Cloud speech recognizer stopped")

    async def recognize(self, audio_data: bytes) -> Optional[Utterance]:
        """Recognize speech using cloud API."""
        # Would integrate with Google Cloud Speech, Azure, AWS Transcribe, etc.

        utterance = Utterance(
            id=f"cloud_utt_{id(audio_data)}",
            text="Cloud recognition result",
            language=self.config.language,
            confidence=0.98,
            duration=len(audio_data) / (self.config.sample_rate * 2)
        )

        self._notify_callbacks(utterance)
        return utterance


# =============================================================================
# SPEECH SYNTHESIZER (ABSTRACT)
# =============================================================================

class SpeechSynthesizer:
    """Abstract speech synthesis interface."""

    def __init__(self, config: VoiceConfig):
        self.config = config

    async def synthesize(self, text: str) -> SynthesizedSpeech:
        """Synthesize speech from text."""
        raise NotImplementedError

    async def get_voices(self) -> List[Dict[str, Any]]:
        """Get available voices."""
        raise NotImplementedError


class LocalSpeechSynthesizer(SpeechSynthesizer):
    """Local speech synthesis (simulated)."""

    async def synthesize(self, text: str) -> SynthesizedSpeech:
        """Synthesize speech locally."""
        # Simulated synthesis
        # In real implementation, would use pyttsx3, espeak, or similar

        # Generate dummy audio data
        duration = len(text) * 0.05  # Rough estimate
        sample_count = int(duration * self.config.sample_rate)
        audio_data = b'\x00' * (sample_count * 2)  # 16-bit audio

        return SynthesizedSpeech(
            text=text,
            audio_data=audio_data,
            audio_format=AudioFormat.WAV,
            duration=duration,
            voice_id=self.config.voice_id
        )

    async def get_voices(self) -> List[Dict[str, Any]]:
        """Get available voices."""
        return [
            {"id": "default", "name": "Default Voice", "language": "en"},
            {"id": "male_1", "name": "Male Voice 1", "language": "en"},
            {"id": "female_1", "name": "Female Voice 1", "language": "en"}
        ]


class CloudSpeechSynthesizer(SpeechSynthesizer):
    """Cloud-based speech synthesis."""

    def __init__(self, config: VoiceConfig, api_key: str = None):
        super().__init__(config)
        self.api_key = api_key

    async def synthesize(self, text: str) -> SynthesizedSpeech:
        """Synthesize speech using cloud API."""
        # Would integrate with Google Cloud TTS, Azure TTS, ElevenLabs, etc.

        duration = len(text) * 0.05
        sample_count = int(duration * self.config.sample_rate)
        audio_data = b'\x00' * (sample_count * 2)

        return SynthesizedSpeech(
            text=text,
            audio_data=audio_data,
            audio_format=AudioFormat.MP3,
            duration=duration,
            voice_id=self.config.voice_id
        )

    async def get_voices(self) -> List[Dict[str, Any]]:
        """Get available cloud voices."""
        return [
            {"id": "neural-1", "name": "Neural Voice 1", "language": "en"},
            {"id": "neural-2", "name": "Neural Voice 2", "language": "en"},
            {"id": "natural-1", "name": "Natural Voice 1", "language": "en"}
        ]


# =============================================================================
# WAKE WORD DETECTOR
# =============================================================================

class WakeWordDetector:
    """Detects wake words in audio stream."""

    def __init__(self, wake_word: str, sensitivity: float = 0.5):
        self.wake_word = wake_word.lower()
        self.sensitivity = sensitivity
        self._callbacks: List[Callable[[], None]] = []
        self._buffer: deque = deque(maxlen=100)  # Audio buffer

    def on_wake_word(self, callback: Callable[[], None]) -> None:
        """Register wake word callback."""
        self._callbacks.append(callback)

    async def process_audio(self, audio_data: bytes) -> bool:
        """Process audio for wake word detection."""
        # In real implementation, would use Porcupine, Snowboy, or similar
        # For now, simulate detection

        # Add to buffer
        self._buffer.append(audio_data)

        # Simulated detection (random for testing)
        import random
        if random.random() < 0.01:  # 1% chance per chunk
            self._notify_callbacks()
            return True

        return False

    def _notify_callbacks(self) -> None:
        """Notify wake word callbacks."""
        for callback in self._callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Wake word callback error: {e}")


# =============================================================================
# VOICE COMMAND PROCESSOR
# =============================================================================

class VoiceCommandProcessor:
    """Processes voice commands."""

    def __init__(self):
        self._commands: Dict[str, VoiceCommand] = {}
        self._aliases: Dict[str, str] = {}  # alias -> command_id

    def register(
        self,
        command_id: str,
        phrases: List[str],
        handler: Callable,
        description: str = "",
        requires_confirmation: bool = False
    ) -> None:
        """Register a voice command."""
        command = VoiceCommand(
            phrases=phrases,
            handler=handler,
            description=description,
            requires_confirmation=requires_confirmation
        )

        self._commands[command_id] = command

        # Register phrase aliases
        for phrase in phrases:
            self._aliases[phrase.lower()] = command_id

    def unregister(self, command_id: str) -> None:
        """Unregister a voice command."""
        if command_id in self._commands:
            command = self._commands[command_id]
            for phrase in command.phrases:
                self._aliases.pop(phrase.lower(), None)
            del self._commands[command_id]

    async def process(self, utterance: Utterance) -> Optional[Dict[str, Any]]:
        """Process an utterance for commands."""
        text = utterance.text.lower().strip()

        # Check for exact match
        if text in self._aliases:
            command_id = self._aliases[text]
            return await self._execute(command_id, utterance)

        # Check for partial match
        for phrase, command_id in self._aliases.items():
            if phrase in text or text in phrase:
                return await self._execute(command_id, utterance)

        return None

    async def _execute(
        self,
        command_id: str,
        utterance: Utterance
    ) -> Dict[str, Any]:
        """Execute a voice command."""
        command = self._commands[command_id]

        try:
            if asyncio.iscoroutinefunction(command.handler):
                result = await command.handler(utterance)
            else:
                result = command.handler(utterance)

            return {
                "command_id": command_id,
                "status": "success",
                "result": result
            }

        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return {
                "command_id": command_id,
                "status": "error",
                "error": str(e)
            }

    def list_commands(self) -> List[Dict[str, Any]]:
        """List all registered commands."""
        return [
            {
                "id": cmd_id,
                "phrases": cmd.phrases,
                "description": cmd.description
            }
            for cmd_id, cmd in self._commands.items()
        ]


# =============================================================================
# VOICE INTERFACE
# =============================================================================

class VoiceInterface:
    """Main voice interface for BAEL."""

    def __init__(
        self,
        config: VoiceConfig = None,
        recognizer: SpeechRecognizer = None,
        synthesizer: SpeechSynthesizer = None
    ):
        self.config = config or VoiceConfig()

        # Components
        self.recognizer = recognizer or LocalSpeechRecognizer(self.config)
        self.synthesizer = synthesizer or LocalSpeechSynthesizer(self.config)
        self.wake_detector = WakeWordDetector(
            self.config.wake_word,
            self.config.wake_word_sensitivity
        )
        self.command_processor = VoiceCommandProcessor()

        # State
        self.state = VoiceState.IDLE
        self._running = False

        # Callbacks
        self._on_utterance: List[Callable[[Utterance], None]] = []
        self._on_state_change: List[Callable[[VoiceState], None]] = []

        # History
        self._utterance_history: deque = deque(maxlen=100)

        # Setup
        self._register_default_commands()

    def _register_default_commands(self) -> None:
        """Register default voice commands."""

        def stop_listening(utterance):
            return "Stopping"

        def help_command(utterance):
            return self.command_processor.list_commands()

        def repeat_last(utterance):
            if self._utterance_history:
                return self._utterance_history[-1].text
            return "No previous utterance"

        self.command_processor.register(
            "stop",
            ["stop listening", "stop", "quiet"],
            stop_listening,
            "Stop listening for commands"
        )

        self.command_processor.register(
            "help",
            ["help", "what can you do", "list commands"],
            help_command,
            "List available commands"
        )

        self.command_processor.register(
            "repeat",
            ["repeat", "say that again", "what did I say"],
            repeat_last,
            "Repeat the last utterance"
        )

    async def start(self) -> None:
        """Start voice interface."""
        logger.info("Starting voice interface")

        await self.recognizer.start()

        # Register utterance callback
        self.recognizer.on_utterance(self._handle_utterance)

        # Register wake word callback
        self.wake_detector.on_wake_word(self._handle_wake_word)

        self._running = True
        self._set_state(VoiceState.IDLE)

    async def stop(self) -> None:
        """Stop voice interface."""
        logger.info("Stopping voice interface")

        self._running = False
        await self.recognizer.stop()
        self._set_state(VoiceState.IDLE)

    def _set_state(self, state: VoiceState) -> None:
        """Set interface state."""
        old_state = self.state
        self.state = state

        if old_state != state:
            for callback in self._on_state_change:
                try:
                    callback(state)
                except Exception as e:
                    logger.error(f"State change callback error: {e}")

    def _handle_wake_word(self) -> None:
        """Handle wake word detection."""
        logger.info("Wake word detected")
        self._set_state(VoiceState.LISTENING)

    def _handle_utterance(self, utterance: Utterance) -> None:
        """Handle recognized utterance."""
        logger.info(f"Utterance: {utterance.text}")

        self._utterance_history.append(utterance)

        # Notify callbacks
        for callback in self._on_utterance:
            try:
                callback(utterance)
            except Exception as e:
                logger.error(f"Utterance callback error: {e}")

    async def listen(self) -> Optional[Utterance]:
        """Listen for a single utterance."""
        self._set_state(VoiceState.LISTENING)

        # In real implementation, would record audio until silence
        # For now, simulate
        await asyncio.sleep(2)

        utterance = Utterance(
            id="manual_listen",
            text="Simulated manual listen result",
            language=self.config.language,
            confidence=0.95
        )

        self._set_state(VoiceState.IDLE)
        return utterance

    async def speak(self, text: str) -> None:
        """Speak text."""
        self._set_state(VoiceState.SPEAKING)

        speech = await self.synthesizer.synthesize(text)

        # In real implementation, would play audio
        # For now, simulate with delay
        await asyncio.sleep(speech.duration)

        self._set_state(VoiceState.IDLE)

    async def recognize_audio(self, audio_data: bytes) -> Optional[Utterance]:
        """Recognize speech from audio data."""
        self._set_state(VoiceState.PROCESSING)

        utterance = await self.recognizer.recognize(audio_data)

        if utterance:
            self._utterance_history.append(utterance)

        self._set_state(VoiceState.IDLE)
        return utterance

    async def process_command(self, utterance: Utterance) -> Optional[Dict[str, Any]]:
        """Process utterance as command."""
        return await self.command_processor.process(utterance)

    def on_utterance(self, callback: Callable[[Utterance], None]) -> None:
        """Register utterance callback."""
        self._on_utterance.append(callback)

    def on_state_change(self, callback: Callable[[VoiceState], None]) -> None:
        """Register state change callback."""
        self._on_state_change.append(callback)

    def register_command(
        self,
        command_id: str,
        phrases: List[str],
        handler: Callable,
        description: str = ""
    ) -> None:
        """Register a voice command."""
        self.command_processor.register(command_id, phrases, handler, description)

    def get_status(self) -> Dict[str, Any]:
        """Get interface status."""
        return {
            "state": self.state.value,
            "language": self.config.language.value,
            "wake_word": self.config.wake_word,
            "utterance_count": len(self._utterance_history),
            "commands_registered": len(self.command_processor._commands)
        }


# =============================================================================
# CONVERSATION MANAGER
# =============================================================================

class VoiceConversationManager:
    """Manages voice-based conversations."""

    def __init__(self, voice_interface: VoiceInterface, brain=None):
        self.voice = voice_interface
        self.brain = brain

        self._conversation_active = False
        self._conversation_history: List[Dict[str, str]] = []

    async def start_conversation(self) -> None:
        """Start a voice conversation."""
        self._conversation_active = True
        self._conversation_history = []

        await self.voice.speak("Hello! How can I help you?")

        while self._conversation_active:
            utterance = await self.voice.listen()

            if not utterance:
                continue

            # Check for end commands
            if any(end in utterance.text.lower() for end in ["goodbye", "bye", "end", "stop"]):
                await self.voice.speak("Goodbye!")
                break

            # Process through brain or command
            response = await self._process(utterance.text)

            # Speak response
            await self.voice.speak(response)

        self._conversation_active = False

    async def _process(self, text: str) -> str:
        """Process user input."""
        # Add to history
        self._conversation_history.append({"role": "user", "content": text})

        # Check for commands first
        utterance = Utterance(
            id="conv",
            text=text,
            language=self.voice.config.language,
            confidence=1.0
        )

        command_result = await self.voice.process_command(utterance)

        if command_result and command_result["status"] == "success":
            response = str(command_result.get("result", "Command executed"))
        elif self.brain:
            # Process through brain
            result = await self.brain.think(text)
            response = result.get("response", "I'm not sure how to respond to that.")
        else:
            response = f"I heard: {text}"

        # Add to history
        self._conversation_history.append({"role": "assistant", "content": response})

        return response

    def end_conversation(self) -> None:
        """End the conversation."""
        self._conversation_active = False


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Test voice interface."""
    config = VoiceConfig(
        language=Language.ENGLISH,
        wake_word="hey bael"
    )

    voice = VoiceInterface(config)

    await voice.start()

    print(f"Voice interface status: {voice.get_status()}")
    print(f"Available commands: {voice.command_processor.list_commands()}")

    # Test speech synthesis
    print("\nTesting speech synthesis...")
    await voice.speak("Hello, I am BAEL, your AI assistant.")

    # Test recognition
    print("\nTesting speech recognition...")
    utterance = await voice.listen()
    if utterance:
        print(f"Recognized: {utterance.text}")

    # Test command processing
    print("\nTesting command processing...")
    test_utterance = Utterance(
        id="test",
        text="help",
        language=Language.ENGLISH,
        confidence=1.0
    )
    result = await voice.process_command(test_utterance)
    print(f"Command result: {result}")

    await voice.stop()


if __name__ == "__main__":
    asyncio.run(main())
