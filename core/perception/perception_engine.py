#!/usr/bin/env python3
"""
BAEL - Perception Engine
Advanced perception and sensory processing for AI agents.

Features:
- Multi-modal perception
- Sensory data processing
- Pattern recognition
- Feature extraction
- Object detection simulation
- Attention mechanisms
- Salience detection
- Perception fusion
"""

import asyncio
import copy
import hashlib
import json
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ModalityType(Enum):
    """Perception modality types."""
    VISUAL = "visual"
    AUDITORY = "auditory"
    TEXTUAL = "textual"
    NUMERIC = "numeric"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"


class PerceptionStatus(Enum):
    """Perception status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


class AttentionLevel(Enum):
    """Attention level."""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    FOCUSED = 4


class PatternType(Enum):
    """Pattern types."""
    SEQUENCE = "sequence"
    CLUSTER = "cluster"
    ANOMALY = "anomaly"
    TREND = "trend"
    CYCLE = "cycle"


class ObjectType(Enum):
    """Object types for detection."""
    ENTITY = "entity"
    EVENT = "event"
    RELATIONSHIP = "relationship"
    ATTRIBUTE = "attribute"
    ACTION = "action"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SensoryInput:
    """Sensory input data."""
    input_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    modality: ModalityType = ModalityType.TEXTUAL
    data: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Percept:
    """Processed perception."""
    percept_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    modality: ModalityType = ModalityType.TEXTUAL
    content: Any = None
    features: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    salience: float = 0.5
    attention_level: AttentionLevel = AttentionLevel.MEDIUM
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DetectedObject:
    """Detected object."""
    object_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    object_type: ObjectType = ObjectType.ENTITY
    label: str = ""
    confidence: float = 1.0
    features: Dict[str, Any] = field(default_factory=dict)
    bounding_box: Optional[Tuple[float, float, float, float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Pattern:
    """Detected pattern."""
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pattern_type: PatternType = PatternType.SEQUENCE
    description: str = ""
    confidence: float = 1.0
    elements: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AttentionFocus:
    """Attention focus."""
    focus_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    target: str = ""
    level: AttentionLevel = AttentionLevel.MEDIUM
    duration: float = 0.0
    started_at: datetime = field(default_factory=datetime.now)


@dataclass
class PerceptionResult:
    """Perception processing result."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    percepts: List[Percept] = field(default_factory=list)
    objects: List[DetectedObject] = field(default_factory=list)
    patterns: List[Pattern] = field(default_factory=list)
    status: PerceptionStatus = PerceptionStatus.COMPLETE
    processing_time: float = 0.0


@dataclass
class PerceptionStats:
    """Perception statistics."""
    total_inputs: int = 0
    total_percepts: int = 0
    total_objects: int = 0
    total_patterns: int = 0
    avg_processing_time: float = 0.0


# =============================================================================
# FEATURE EXTRACTOR
# =============================================================================

class FeatureExtractor(ABC):
    """Abstract feature extractor."""

    @abstractmethod
    def extract(self, data: Any) -> Dict[str, Any]:
        """Extract features."""
        pass


class TextFeatureExtractor(FeatureExtractor):
    """Text feature extractor."""

    def extract(self, data: Any) -> Dict[str, Any]:
        """Extract text features."""
        if not isinstance(data, str):
            data = str(data)

        words = data.split()

        return {
            "length": len(data),
            "word_count": len(words),
            "avg_word_length": sum(len(w) for w in words) / len(words) if words else 0,
            "unique_words": len(set(words)),
            "has_numbers": any(c.isdigit() for c in data),
            "has_punctuation": any(c in ".,!?;:" for c in data),
            "uppercase_ratio": sum(1 for c in data if c.isupper()) / len(data) if data else 0
        }


class NumericFeatureExtractor(FeatureExtractor):
    """Numeric feature extractor."""

    def extract(self, data: Any) -> Dict[str, Any]:
        """Extract numeric features."""
        if isinstance(data, (int, float)):
            data = [data]
        elif not isinstance(data, (list, tuple)):
            return {}

        values = [v for v in data if isinstance(v, (int, float))]

        if not values:
            return {}

        return {
            "count": len(values),
            "sum": sum(values),
            "mean": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "range": max(values) - min(values),
            "variance": sum((v - sum(values)/len(values))**2 for v in values) / len(values)
        }


class TemporalFeatureExtractor(FeatureExtractor):
    """Temporal feature extractor."""

    def extract(self, data: Any) -> Dict[str, Any]:
        """Extract temporal features."""
        if isinstance(data, datetime):
            return {
                "year": data.year,
                "month": data.month,
                "day": data.day,
                "hour": data.hour,
                "minute": data.minute,
                "day_of_week": data.weekday(),
                "is_weekend": data.weekday() >= 5
            }
        return {}


# =============================================================================
# PATTERN DETECTOR
# =============================================================================

class PatternDetector:
    """Detect patterns in data."""

    def detect_sequence(self, data: List[Any]) -> Optional[Pattern]:
        """Detect sequential patterns."""
        if len(data) < 3:
            return None

        # Check for arithmetic sequence
        if all(isinstance(x, (int, float)) for x in data):
            diffs = [data[i+1] - data[i] for i in range(len(data)-1)]
            if len(set(diffs)) == 1:
                return Pattern(
                    pattern_type=PatternType.SEQUENCE,
                    description=f"Arithmetic sequence with diff={diffs[0]}",
                    confidence=1.0,
                    elements=data
                )

        # Check for repeating pattern
        for pattern_len in range(1, len(data)//2 + 1):
            pattern = data[:pattern_len]
            if all(data[i] == pattern[i % pattern_len] for i in range(len(data))):
                return Pattern(
                    pattern_type=PatternType.CYCLE,
                    description=f"Repeating pattern of length {pattern_len}",
                    confidence=0.9,
                    elements=pattern
                )

        return None

    def detect_trend(self, data: List[float]) -> Optional[Pattern]:
        """Detect trends in numeric data."""
        if len(data) < 2:
            return None

        # Simple linear trend detection
        increasing = all(data[i] <= data[i+1] for i in range(len(data)-1))
        decreasing = all(data[i] >= data[i+1] for i in range(len(data)-1))

        if increasing:
            return Pattern(
                pattern_type=PatternType.TREND,
                description="Increasing trend",
                confidence=0.8,
                elements=data
            )
        elif decreasing:
            return Pattern(
                pattern_type=PatternType.TREND,
                description="Decreasing trend",
                confidence=0.8,
                elements=data
            )

        return None

    def detect_anomaly(
        self,
        data: List[float],
        threshold: float = 2.0
    ) -> List[Pattern]:
        """Detect anomalies in numeric data."""
        if len(data) < 3:
            return []

        mean = sum(data) / len(data)
        variance = sum((x - mean)**2 for x in data) / len(data)
        std_dev = math.sqrt(variance) if variance > 0 else 0

        anomalies = []
        for i, value in enumerate(data):
            if std_dev > 0 and abs(value - mean) > threshold * std_dev:
                anomalies.append(Pattern(
                    pattern_type=PatternType.ANOMALY,
                    description=f"Anomaly at index {i}: {value}",
                    confidence=min(1.0, abs(value - mean) / (threshold * std_dev)),
                    elements=[value],
                    metadata={"index": i, "deviation": abs(value - mean) / std_dev}
                ))

        return anomalies


# =============================================================================
# OBJECT DETECTOR
# =============================================================================

class ObjectDetector:
    """Detect objects in perception data."""

    def __init__(self):
        self._entity_patterns = [
            (r'[A-Z][a-z]+', ObjectType.ENTITY),
            (r'@\w+', ObjectType.ENTITY),
            (r'#\w+', ObjectType.ATTRIBUTE)
        ]

    def detect_in_text(self, text: str) -> List[DetectedObject]:
        """Detect objects in text."""
        import re

        objects = []

        # Detect capitalized words (potential entities)
        for match in re.finditer(r'\b[A-Z][a-z]+\b', text):
            objects.append(DetectedObject(
                object_type=ObjectType.ENTITY,
                label=match.group(),
                confidence=0.7,
                features={"position": match.start()}
            ))

        # Detect quoted strings
        for match in re.finditer(r'"([^"]*)"', text):
            objects.append(DetectedObject(
                object_type=ObjectType.ATTRIBUTE,
                label=match.group(1),
                confidence=0.9,
                features={"position": match.start(), "quoted": True}
            ))

        # Detect action verbs (simple heuristic)
        action_words = ["run", "create", "update", "delete", "send", "process"]
        for word in action_words:
            if word in text.lower():
                objects.append(DetectedObject(
                    object_type=ObjectType.ACTION,
                    label=word,
                    confidence=0.6
                ))

        return objects

    def detect_in_data(self, data: Dict[str, Any]) -> List[DetectedObject]:
        """Detect objects in structured data."""
        objects = []

        for key, value in data.items():
            obj_type = ObjectType.ATTRIBUTE

            if isinstance(value, dict):
                obj_type = ObjectType.ENTITY
            elif isinstance(value, list):
                obj_type = ObjectType.RELATIONSHIP

            objects.append(DetectedObject(
                object_type=obj_type,
                label=key,
                confidence=0.8,
                features={"value_type": type(value).__name__}
            ))

        return objects


# =============================================================================
# ATTENTION MECHANISM
# =============================================================================

class AttentionMechanism:
    """Manage attention."""

    def __init__(self):
        self._focus_stack: List[AttentionFocus] = []
        self._salience_weights: Dict[str, float] = {}

    def calculate_salience(self, percept: Percept) -> float:
        """Calculate salience score."""
        base_salience = 0.5

        # Boost for high confidence
        if percept.confidence > 0.8:
            base_salience += 0.2

        # Boost for certain features
        features = percept.features

        if features.get("has_numbers"):
            base_salience += 0.1

        if features.get("word_count", 0) > 50:
            base_salience += 0.1

        return min(1.0, base_salience)

    def focus(self, target: str, level: AttentionLevel) -> AttentionFocus:
        """Focus attention."""
        focus = AttentionFocus(
            target=target,
            level=level
        )

        self._focus_stack.append(focus)
        return focus

    def unfocus(self) -> Optional[AttentionFocus]:
        """Remove focus."""
        if self._focus_stack:
            return self._focus_stack.pop()
        return None

    def get_current_focus(self) -> Optional[AttentionFocus]:
        """Get current focus."""
        return self._focus_stack[-1] if self._focus_stack else None

    def filter_by_attention(
        self,
        percepts: List[Percept],
        min_level: AttentionLevel = AttentionLevel.LOW
    ) -> List[Percept]:
        """Filter percepts by attention level."""
        return [
            p for p in percepts
            if p.attention_level.value >= min_level.value
        ]

    def prioritize(self, percepts: List[Percept]) -> List[Percept]:
        """Prioritize percepts by salience."""
        return sorted(percepts, key=lambda p: p.salience, reverse=True)


# =============================================================================
# PERCEPTION PROCESSOR
# =============================================================================

class PerceptionProcessor:
    """Process sensory inputs."""

    def __init__(self):
        self._feature_extractors: Dict[ModalityType, FeatureExtractor] = {
            ModalityType.TEXTUAL: TextFeatureExtractor(),
            ModalityType.NUMERIC: NumericFeatureExtractor(),
            ModalityType.TEMPORAL: TemporalFeatureExtractor()
        }
        self._pattern_detector = PatternDetector()
        self._object_detector = ObjectDetector()
        self._attention = AttentionMechanism()

    def process(self, input_: SensoryInput) -> Percept:
        """Process sensory input into percept."""
        # Extract features
        extractor = self._feature_extractors.get(input_.modality)
        features = extractor.extract(input_.data) if extractor else {}

        # Create percept
        percept = Percept(
            modality=input_.modality,
            content=input_.data,
            features=features,
            confidence=0.9,
            metadata=input_.metadata
        )

        # Calculate salience
        percept.salience = self._attention.calculate_salience(percept)

        # Assign attention level based on salience
        if percept.salience > 0.8:
            percept.attention_level = AttentionLevel.HIGH
        elif percept.salience > 0.5:
            percept.attention_level = AttentionLevel.MEDIUM
        else:
            percept.attention_level = AttentionLevel.LOW

        return percept

    def detect_patterns(self, percepts: List[Percept]) -> List[Pattern]:
        """Detect patterns across percepts."""
        patterns = []

        # Collect numeric data
        numeric_data = []
        for percept in percepts:
            if percept.modality == ModalityType.NUMERIC:
                if isinstance(percept.content, (list, tuple)):
                    numeric_data.extend(percept.content)
                else:
                    numeric_data.append(percept.content)

        # Detect patterns
        if numeric_data:
            seq_pattern = self._pattern_detector.detect_sequence(numeric_data)
            if seq_pattern:
                patterns.append(seq_pattern)

            trend = self._pattern_detector.detect_trend(numeric_data)
            if trend:
                patterns.append(trend)

            anomalies = self._pattern_detector.detect_anomaly(numeric_data)
            patterns.extend(anomalies)

        return patterns

    def detect_objects(self, percepts: List[Percept]) -> List[DetectedObject]:
        """Detect objects in percepts."""
        objects = []

        for percept in percepts:
            if percept.modality == ModalityType.TEXTUAL:
                objects.extend(
                    self._object_detector.detect_in_text(str(percept.content))
                )
            elif isinstance(percept.content, dict):
                objects.extend(
                    self._object_detector.detect_in_data(percept.content)
                )

        return objects


# =============================================================================
# PERCEPTION FUSION
# =============================================================================

class PerceptionFusion:
    """Fuse multi-modal perceptions."""

    def fuse(self, percepts: List[Percept]) -> Percept:
        """Fuse multiple percepts."""
        if not percepts:
            return Percept()

        if len(percepts) == 1:
            return percepts[0]

        # Combine features
        combined_features: Dict[str, Any] = {}
        for percept in percepts:
            for key, value in percept.features.items():
                if key not in combined_features:
                    combined_features[key] = []
                combined_features[key].append(value)

        # Average numeric features
        for key, values in combined_features.items():
            if all(isinstance(v, (int, float)) for v in values):
                combined_features[key] = sum(values) / len(values)

        # Average confidence and salience
        avg_confidence = sum(p.confidence for p in percepts) / len(percepts)
        avg_salience = sum(p.salience for p in percepts) / len(percepts)

        # Create fused percept
        return Percept(
            modality=percepts[0].modality,
            content=[p.content for p in percepts],
            features=combined_features,
            confidence=avg_confidence,
            salience=avg_salience,
            attention_level=max(p.attention_level for p in percepts),
            metadata={"fused_from": [p.percept_id for p in percepts]}
        )


# =============================================================================
# PERCEPTION ENGINE
# =============================================================================

class PerceptionEngine:
    """
    Perception Engine for BAEL.

    Advanced perception and sensory processing.
    """

    def __init__(self):
        self._processor = PerceptionProcessor()
        self._fusion = PerceptionFusion()
        self._attention = AttentionMechanism()
        self._percept_history: List[Percept] = []
        self._stats = PerceptionStats()

    # -------------------------------------------------------------------------
    # INPUT PROCESSING
    # -------------------------------------------------------------------------

    def perceive(
        self,
        data: Any,
        modality: str = "textual",
        source: str = ""
    ) -> Percept:
        """Process sensory input."""
        modality_map = {
            "visual": ModalityType.VISUAL,
            "auditory": ModalityType.AUDITORY,
            "textual": ModalityType.TEXTUAL,
            "numeric": ModalityType.NUMERIC,
            "temporal": ModalityType.TEMPORAL,
            "spatial": ModalityType.SPATIAL
        }

        input_ = SensoryInput(
            modality=modality_map.get(modality.lower(), ModalityType.TEXTUAL),
            data=data,
            source=source
        )

        percept = self._processor.process(input_)

        self._percept_history.append(percept)
        self._stats.total_inputs += 1
        self._stats.total_percepts += 1

        return percept

    def perceive_batch(
        self,
        inputs: List[Tuple[Any, str]]
    ) -> List[Percept]:
        """Process batch of inputs."""
        return [
            self.perceive(data, modality)
            for data, modality in inputs
        ]

    async def perceive_async(
        self,
        data: Any,
        modality: str = "textual"
    ) -> Percept:
        """Async perception."""
        await asyncio.sleep(0.001)  # Simulate processing
        return self.perceive(data, modality)

    # -------------------------------------------------------------------------
    # PATTERN DETECTION
    # -------------------------------------------------------------------------

    def detect_patterns(
        self,
        percepts: Optional[List[Percept]] = None
    ) -> List[Pattern]:
        """Detect patterns."""
        if percepts is None:
            percepts = self._percept_history[-100:]

        patterns = self._processor.detect_patterns(percepts)
        self._stats.total_patterns += len(patterns)

        return patterns

    # -------------------------------------------------------------------------
    # OBJECT DETECTION
    # -------------------------------------------------------------------------

    def detect_objects(
        self,
        percepts: Optional[List[Percept]] = None
    ) -> List[DetectedObject]:
        """Detect objects."""
        if percepts is None:
            percepts = self._percept_history[-100:]

        objects = self._processor.detect_objects(percepts)
        self._stats.total_objects += len(objects)

        return objects

    # -------------------------------------------------------------------------
    # ATTENTION
    # -------------------------------------------------------------------------

    def focus(
        self,
        target: str,
        level: str = "medium"
    ) -> AttentionFocus:
        """Focus attention."""
        level_map = {
            "none": AttentionLevel.NONE,
            "low": AttentionLevel.LOW,
            "medium": AttentionLevel.MEDIUM,
            "high": AttentionLevel.HIGH,
            "focused": AttentionLevel.FOCUSED
        }

        return self._attention.focus(
            target,
            level_map.get(level.lower(), AttentionLevel.MEDIUM)
        )

    def unfocus(self) -> Optional[AttentionFocus]:
        """Remove focus."""
        return self._attention.unfocus()

    def get_current_focus(self) -> Optional[AttentionFocus]:
        """Get current focus."""
        return self._attention.get_current_focus()

    def filter_by_attention(
        self,
        percepts: List[Percept],
        min_level: str = "low"
    ) -> List[Percept]:
        """Filter by attention level."""
        level_map = {
            "none": AttentionLevel.NONE,
            "low": AttentionLevel.LOW,
            "medium": AttentionLevel.MEDIUM,
            "high": AttentionLevel.HIGH
        }

        return self._attention.filter_by_attention(
            percepts,
            level_map.get(min_level.lower(), AttentionLevel.LOW)
        )

    def prioritize(self, percepts: List[Percept]) -> List[Percept]:
        """Prioritize by salience."""
        return self._attention.prioritize(percepts)

    # -------------------------------------------------------------------------
    # FUSION
    # -------------------------------------------------------------------------

    def fuse(self, percepts: List[Percept]) -> Percept:
        """Fuse percepts."""
        return self._fusion.fuse(percepts)

    # -------------------------------------------------------------------------
    # COMPREHENSIVE PROCESSING
    # -------------------------------------------------------------------------

    async def process(
        self,
        data: Any,
        modality: str = "textual"
    ) -> PerceptionResult:
        """Full perception processing."""
        start_time = time.time()

        # Perceive
        percept = await self.perceive_async(data, modality)

        # Detect patterns and objects
        patterns = self.detect_patterns([percept])
        objects = self.detect_objects([percept])

        processing_time = time.time() - start_time

        # Update stats
        n = self._stats.total_inputs
        old_avg = self._stats.avg_processing_time
        self._stats.avg_processing_time = (old_avg * (n - 1) + processing_time) / n if n > 0 else processing_time

        return PerceptionResult(
            percepts=[percept],
            objects=objects,
            patterns=patterns,
            status=PerceptionStatus.COMPLETE,
            processing_time=processing_time
        )

    # -------------------------------------------------------------------------
    # HISTORY
    # -------------------------------------------------------------------------

    def get_history(self, limit: int = 100) -> List[Percept]:
        """Get perception history."""
        return self._percept_history[-limit:]

    def clear_history(self) -> int:
        """Clear history."""
        count = len(self._percept_history)
        self._percept_history.clear()
        return count

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> PerceptionStats:
        """Get perception statistics."""
        return self._stats


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Perception Engine."""
    print("=" * 70)
    print("BAEL - PERCEPTION ENGINE DEMO")
    print("Advanced Perception and Sensory Processing")
    print("=" * 70)
    print()

    engine = PerceptionEngine()

    # 1. Text Perception
    print("1. TEXT PERCEPTION:")
    print("-" * 40)

    percept = engine.perceive(
        "BAEL is an advanced AI agent system.",
        modality="textual"
    )

    print(f"   Content: {percept.content}")
    print(f"   Features: {percept.features}")
    print(f"   Salience: {percept.salience:.2f}")
    print(f"   Attention: {percept.attention_level.name}")
    print()

    # 2. Numeric Perception
    print("2. NUMERIC PERCEPTION:")
    print("-" * 40)

    percept = engine.perceive(
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        modality="numeric"
    )

    print(f"   Content: {percept.content}")
    print(f"   Features: {percept.features}")
    print()

    # 3. Temporal Perception
    print("3. TEMPORAL PERCEPTION:")
    print("-" * 40)

    percept = engine.perceive(
        datetime.now(),
        modality="temporal"
    )

    print(f"   Content: {percept.content}")
    print(f"   Features: {percept.features}")
    print()

    # 4. Pattern Detection
    print("4. PATTERN DETECTION:")
    print("-" * 40)

    # Add numeric sequence
    engine.perceive([2, 4, 6, 8, 10], modality="numeric")

    patterns = engine.detect_patterns()

    print(f"   Detected patterns: {len(patterns)}")
    for p in patterns[:3]:
        print(f"     - {p.pattern_type.value}: {p.description}")
    print()

    # 5. Object Detection
    print("5. OBJECT DETECTION:")
    print("-" * 40)

    engine.perceive(
        'Alice sent a message to Bob saying "Hello World"',
        modality="textual"
    )

    objects = engine.detect_objects()

    print(f"   Detected objects: {len(objects)}")
    for obj in objects[:5]:
        print(f"     - {obj.object_type.value}: {obj.label} (conf={obj.confidence:.2f})")
    print()

    # 6. Attention Focus
    print("6. ATTENTION FOCUS:")
    print("-" * 40)

    focus = engine.focus("important_task", "high")

    print(f"   Focused on: {focus.target}")
    print(f"   Level: {focus.level.name}")

    current = engine.get_current_focus()
    print(f"   Current focus: {current.target if current else 'None'}")
    print()

    # 7. Filter by Attention
    print("7. FILTER BY ATTENTION:")
    print("-" * 40)

    history = engine.get_history()
    filtered = engine.filter_by_attention(history, "medium")

    print(f"   Total percepts: {len(history)}")
    print(f"   Medium+ attention: {len(filtered)}")
    print()

    # 8. Prioritize by Salience
    print("8. PRIORITIZE BY SALIENCE:")
    print("-" * 40)

    prioritized = engine.prioritize(history)

    print("   Top 3 by salience:")
    for p in prioritized[:3]:
        content_preview = str(p.content)[:30]
        print(f"     - salience={p.salience:.2f}: {content_preview}...")
    print()

    # 9. Perception Fusion
    print("9. PERCEPTION FUSION:")
    print("-" * 40)

    p1 = engine.perceive("Data point 1", modality="textual")
    p2 = engine.perceive("Data point 2", modality="textual")

    fused = engine.fuse([p1, p2])

    print(f"   Fused from: {len(fused.metadata.get('fused_from', []))} percepts")
    print(f"   Combined confidence: {fused.confidence:.2f}")
    print(f"   Combined salience: {fused.salience:.2f}")
    print()

    # 10. Batch Perception
    print("10. BATCH PERCEPTION:")
    print("-" * 40)

    inputs = [
        ("First input", "textual"),
        ("Second input", "textual"),
        ([100, 200, 300], "numeric")
    ]

    percepts = engine.perceive_batch(inputs)

    print(f"   Processed: {len(percepts)} inputs")
    for p in percepts:
        print(f"     - {p.modality.value}: {str(p.content)[:30]}")
    print()

    # 11. Async Processing
    print("11. ASYNC PROCESSING:")
    print("-" * 40)

    result = await engine.process(
        "This is a comprehensive test message for async processing.",
        modality="textual"
    )

    print(f"   Status: {result.status.value}")
    print(f"   Percepts: {len(result.percepts)}")
    print(f"   Objects: {len(result.objects)}")
    print(f"   Patterns: {len(result.patterns)}")
    print(f"   Processing time: {result.processing_time:.4f}s")
    print()

    # 12. Anomaly Detection
    print("12. ANOMALY DETECTION:")
    print("-" * 40)

    engine.perceive([1, 2, 3, 100, 4, 5], modality="numeric")

    patterns = engine.detect_patterns()
    anomalies = [p for p in patterns if p.pattern_type == PatternType.ANOMALY]

    print(f"   Detected anomalies: {len(anomalies)}")
    for a in anomalies:
        print(f"     - {a.description}")
    print()

    # 13. Perception History
    print("13. PERCEPTION HISTORY:")
    print("-" * 40)

    history = engine.get_history(limit=5)

    print(f"   Recent percepts: {len(history)}")
    for p in history:
        content_preview = str(p.content)[:25]
        print(f"     - [{p.modality.value}] {content_preview}...")
    print()

    # 14. Statistics
    print("14. STATISTICS:")
    print("-" * 40)

    stats = engine.get_stats()

    print(f"   Total inputs: {stats.total_inputs}")
    print(f"   Total percepts: {stats.total_percepts}")
    print(f"   Total objects: {stats.total_objects}")
    print(f"   Total patterns: {stats.total_patterns}")
    print(f"   Avg processing time: {stats.avg_processing_time:.4f}s")
    print()

    # 15. Clear and Reset
    print("15. CLEAR HISTORY:")
    print("-" * 40)

    cleared = engine.clear_history()

    print(f"   Cleared: {cleared} percepts")
    print(f"   Current history: {len(engine.get_history())} percepts")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Perception Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
