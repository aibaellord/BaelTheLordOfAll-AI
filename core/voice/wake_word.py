"""
BAEL Wake Word Detector
========================

Wake word/hot word detection for hands-free activation.
Multiple detection backends supported.

Features:
- Multiple wake word engines
- Custom wake word training
- Low-latency detection
- Sensitivity tuning
- False positive filtering
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class WakeWordEngine(Enum):
    """Wake word detection engines."""
    PORCUPINE = "porcupine"       # Picovoice Porcupine
    SNOWBOY = "snowboy"           # Snowboy (deprecated)
    PRECISE = "precise"           # Mycroft Precise
    VOSK = "vosk"                 # Vosk keyword spotting
    CUSTOM = "custom"             # Custom keyword matching


@dataclass
class WakeWordConfig:
    """Wake word configuration."""
    engine: WakeWordEngine = WakeWordEngine.PORCUPINE

    # Wake words
    keywords: List[str] = field(default_factory=lambda: ["bael", "hey bael"])

    # Sensitivity (0.0 - 1.0)
    sensitivity: float = 0.5

    # Audio
    sample_rate: int = 16000

    # API keys
    porcupine_access_key: Optional[str] = None

    # Custom model paths
    model_paths: Dict[str, str] = field(default_factory=dict)


@dataclass
class DetectionResult:
    """Wake word detection result."""
    detected: bool
    keyword: Optional[str] = None
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    # Audio context
    audio_before: Optional[bytes] = None
    audio_after: Optional[bytes] = None


class WakeWordDetector:
    """
    Wake word detection for BAEL.
    """

    def __init__(
        self,
        config: Optional[WakeWordConfig] = None,
    ):
        self.config = config or WakeWordConfig()

        # Detection engine
        self._engine = None
        self._engine_initialized = False

        # State
        self._is_listening = False
        self._detection_callbacks: List[Callable[[DetectionResult], None]] = []

        # Audio buffer for context
        self._audio_buffer: List[bytes] = []
        self._max_buffer_chunks = 50

        # Stats
        self.stats = {
            "total_detections": 0,
            "false_positives": 0,
            "listening_time_seconds": 0.0,
        }

    async def initialize(self) -> bool:
        """Initialize the wake word engine."""
        if self._engine_initialized:
            return True

        try:
            if self.config.engine == WakeWordEngine.PORCUPINE:
                return await self._init_porcupine()
            elif self.config.engine == WakeWordEngine.VOSK:
                return await self._init_vosk()
            elif self.config.engine == WakeWordEngine.CUSTOM:
                return await self._init_custom()
            else:
                logger.warning(f"Engine not implemented: {self.config.engine.value}")
                return await self._init_custom()
        except Exception as e:
            logger.error(f"Failed to initialize wake word engine: {e}")
            return False

    async def _init_porcupine(self) -> bool:
        """Initialize Porcupine engine."""
        try:
            import pvporcupine
        except ImportError:
            logger.error("pvporcupine not installed. Run: pip install pvporcupine")
            return False

        if not self.config.porcupine_access_key:
            logger.error("Porcupine access key required")
            return False

        try:
            # Get available keywords
            keywords = []
            for kw in self.config.keywords:
                kw_lower = kw.lower().replace(" ", "")
                if kw_lower in pvporcupine.KEYWORDS:
                    keywords.append(kw_lower)

            if not keywords:
                # Use custom keyword paths if provided
                keyword_paths = [
                    self.config.model_paths.get(kw)
                    for kw in self.config.keywords
                    if kw in self.config.model_paths
                ]

                if keyword_paths:
                    self._engine = pvporcupine.create(
                        access_key=self.config.porcupine_access_key,
                        keyword_paths=keyword_paths,
                        sensitivities=[self.config.sensitivity] * len(keyword_paths),
                    )
                else:
                    # Default to "computer" keyword
                    self._engine = pvporcupine.create(
                        access_key=self.config.porcupine_access_key,
                        keywords=["computer"],
                        sensitivities=[self.config.sensitivity],
                    )
            else:
                self._engine = pvporcupine.create(
                    access_key=self.config.porcupine_access_key,
                    keywords=keywords,
                    sensitivities=[self.config.sensitivity] * len(keywords),
                )

            self._engine_initialized = True
            return True

        except Exception as e:
            logger.error(f"Porcupine initialization error: {e}")
            return False

    async def _init_vosk(self) -> bool:
        """Initialize Vosk keyword spotting."""
        try:
            from vosk import KaldiRecognizer, Model
        except ImportError:
            logger.error("vosk not installed. Run: pip install vosk")
            return False

        try:
            model = Model(lang="en-us")
            self._engine = KaldiRecognizer(model, self.config.sample_rate)
            self._engine_initialized = True
            return True
        except Exception as e:
            logger.error(f"Vosk initialization error: {e}")
            return False

    async def _init_custom(self) -> bool:
        """Initialize custom simple keyword matching."""
        # Uses simple audio pattern matching
        self._engine_initialized = True
        return True

    def _process_porcupine(self, audio_data: bytes) -> Optional[str]:
        """Process audio with Porcupine."""
        import struct

        # Porcupine expects specific frame length
        frame_length = self._engine.frame_length

        # Convert to samples
        samples = struct.unpack(f"<{len(audio_data)//2}h", audio_data)

        # Process frames
        for i in range(0, len(samples) - frame_length, frame_length):
            frame = samples[i:i+frame_length]
            keyword_index = self._engine.process(frame)

            if keyword_index >= 0:
                if hasattr(self._engine, 'keywords'):
                    return self._engine.keywords[keyword_index]
                return self.config.keywords[min(keyword_index, len(self.config.keywords)-1)]

        return None

    def _process_vosk(self, audio_data: bytes) -> Optional[str]:
        """Process audio with Vosk."""
        import json

        if self._engine.AcceptWaveform(audio_data):
            result = json.loads(self._engine.Result())
            text = result.get("text", "").lower()

            # Check for wake words in result
            for keyword in self.config.keywords:
                if keyword.lower() in text:
                    return keyword

        return None

    def _process_custom(self, audio_data: bytes) -> Optional[str]:
        """Simple custom detection (placeholder for real implementation)."""
        # In a real implementation, this would use audio fingerprinting
        # or a small neural network for keyword spotting
        return None

    def process_audio(self, audio_data: bytes) -> DetectionResult:
        """
        Process audio chunk for wake word.

        Args:
            audio_data: Raw audio bytes

        Returns:
            DetectionResult
        """
        if not self._engine_initialized:
            return DetectionResult(detected=False)

        # Add to buffer
        self._audio_buffer.append(audio_data)
        if len(self._audio_buffer) > self._max_buffer_chunks:
            self._audio_buffer.pop(0)

        # Process based on engine
        detected_keyword = None

        if self.config.engine == WakeWordEngine.PORCUPINE and self._engine:
            detected_keyword = self._process_porcupine(audio_data)
        elif self.config.engine == WakeWordEngine.VOSK and self._engine:
            detected_keyword = self._process_vosk(audio_data)
        elif self.config.engine == WakeWordEngine.CUSTOM:
            detected_keyword = self._process_custom(audio_data)

        if detected_keyword:
            self.stats["total_detections"] += 1

            # Get context audio
            audio_before = b"".join(self._audio_buffer[-10:]) if len(self._audio_buffer) > 1 else None

            result = DetectionResult(
                detected=True,
                keyword=detected_keyword,
                confidence=1.0 - self.config.sensitivity,
                audio_before=audio_before,
            )

            # Notify callbacks
            for callback in self._detection_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.error(f"Detection callback error: {e}")

            return result

        return DetectionResult(detected=False)

    async def listen(
        self,
        audio_source: AsyncGenerator[bytes, None],
    ) -> AsyncGenerator[DetectionResult, None]:
        """
        Listen for wake word from audio source.

        Args:
            audio_source: Async generator of audio chunks

        Yields:
            DetectionResult when wake word detected
        """
        if not await self.initialize():
            logger.error("Failed to initialize wake word engine")
            return

        self._is_listening = True
        start_time = time.time()

        try:
            async for audio_chunk in audio_source:
                if not self._is_listening:
                    break

                result = self.process_audio(audio_chunk)
                if result.detected:
                    yield result

        finally:
            self.stats["listening_time_seconds"] += time.time() - start_time
            self._is_listening = False

    def stop_listening(self) -> None:
        """Stop listening for wake word."""
        self._is_listening = False

    def on_detection(
        self,
        callback: Callable[[DetectionResult], None],
    ) -> None:
        """Register detection callback."""
        self._detection_callbacks.append(callback)

    def report_false_positive(self) -> None:
        """Report a false positive detection."""
        self.stats["false_positives"] += 1

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._engine and hasattr(self._engine, 'delete'):
            self._engine.delete()
        self._engine = None
        self._engine_initialized = False

    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics."""
        fp_rate = 0.0
        if self.stats["total_detections"] > 0:
            fp_rate = self.stats["false_positives"] / self.stats["total_detections"]

        return {
            **self.stats,
            "engine": self.config.engine.value,
            "keywords": self.config.keywords,
            "sensitivity": self.config.sensitivity,
            "false_positive_rate": fp_rate,
            "is_listening": self._is_listening,
        }


def demo():
    """Demonstrate wake word detector."""
    print("=" * 60)
    print("BAEL Wake Word Detector Demo")
    print("=" * 60)

    config = WakeWordConfig(
        engine=WakeWordEngine.CUSTOM,
        keywords=["bael", "hey bael", "okay bael"],
        sensitivity=0.5,
    )

    detector = WakeWordDetector(config)

    print(f"\nWake word configuration:")
    print(f"  Engine: {config.engine.value}")
    print(f"  Keywords: {config.keywords}")
    print(f"  Sensitivity: {config.sensitivity}")

    # Register callback
    def on_wake(result: DetectionResult):
        print(f"  Wake word detected: {result.keyword}")

    detector.on_detection(on_wake)

    print(f"\nStats: {detector.get_stats()}")


if __name__ == "__main__":
    demo()
