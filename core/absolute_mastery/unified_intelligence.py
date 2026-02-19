"""
👑 UNIFIED INTELLIGENCE 👑
==========================
Unified intelligent mind.

Features:
- Intelligence integration
- Thinking styles
- Consciousness unification
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
import uuid


class IntelligenceMode(Enum):
    """Modes of intelligence"""
    ANALYTICAL = auto()      # Logical, systematic
    CREATIVE = auto()        # Novel, divergent
    PRACTICAL = auto()       # Applied, action-oriented
    INTUITIVE = auto()       # Pattern-based, fast
    REFLECTIVE = auto()      # Meta, self-aware
    INTEGRATED = auto()      # All modes unified


class ThinkingStyle(Enum):
    """Thinking styles"""
    DEDUCTIVE = auto()       # General to specific
    INDUCTIVE = auto()       # Specific to general
    ABDUCTIVE = auto()       # Best explanation
    ANALOGICAL = auto()      # By analogy
    CAUSAL = auto()         # Cause-effect
    SYSTEMS = auto()         # Holistic
    DIALECTICAL = auto()     # Thesis-antithesis-synthesis


@dataclass
class ThoughtUnit:
    """A unit of thought"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    content: Any = None

    # Type
    mode: IntelligenceMode = IntelligenceMode.ANALYTICAL
    style: ThinkingStyle = ThinkingStyle.DEDUCTIVE

    # Quality
    confidence: float = 0.0
    clarity: float = 0.0

    # Relations
    derived_from: List[str] = field(default_factory=list)
    supports: List[str] = field(default_factory=list)

    # Timing
    created_at: datetime = field(default_factory=datetime.now)


class UnifiedMind:
    """
    Unified intelligent mind.
    """

    def __init__(self):
        # Thought stream
        self.thoughts: List[ThoughtUnit] = []

        # Current mode
        self.current_mode: IntelligenceMode = IntelligenceMode.INTEGRATED
        self.current_style: ThinkingStyle = ThinkingStyle.SYSTEMS

        # Processing functions by mode
        self.mode_processors: Dict[IntelligenceMode, Callable[[Any], ThoughtUnit]] = {}

        # Style processors
        self.style_processors: Dict[ThinkingStyle, Callable[[ThoughtUnit], ThoughtUnit]] = {}

        # Focus
        self.focus: Optional[Any] = None
        self.focus_duration: float = 0.0

        # Integration weights
        self.mode_weights: Dict[IntelligenceMode, float] = {
            mode: 1.0 for mode in IntelligenceMode
        }

    def set_mode(self, mode: IntelligenceMode):
        """Set intelligence mode"""
        self.current_mode = mode

    def set_style(self, style: ThinkingStyle):
        """Set thinking style"""
        self.current_style = style

    def add_processor(
        self,
        mode: IntelligenceMode,
        processor: Callable[[Any], ThoughtUnit]
    ):
        """Add mode processor"""
        self.mode_processors[mode] = processor

    def think(self, input_data: Any) -> ThoughtUnit:
        """Generate thought"""
        if self.current_mode == IntelligenceMode.INTEGRATED:
            return self._integrated_think(input_data)

        processor = self.mode_processors.get(self.current_mode)

        if processor:
            thought = processor(input_data)
        else:
            thought = ThoughtUnit(
                content=input_data,
                mode=self.current_mode,
                style=self.current_style
            )

        # Apply style processing
        style_processor = self.style_processors.get(self.current_style)
        if style_processor:
            thought = style_processor(thought)

        self.thoughts.append(thought)
        return thought

    def _integrated_think(self, input_data: Any) -> ThoughtUnit:
        """Integrated thinking across all modes"""
        sub_thoughts = []

        # Generate thoughts in each mode
        for mode in IntelligenceMode:
            if mode == IntelligenceMode.INTEGRATED:
                continue

            processor = self.mode_processors.get(mode)
            if processor:
                thought = processor(input_data)
                weight = self.mode_weights.get(mode, 1.0)
                sub_thoughts.append((thought, weight))

        # Integrate thoughts
        if sub_thoughts:
            total_weight = sum(w for _, w in sub_thoughts)
            avg_confidence = sum(
                t.confidence * w for t, w in sub_thoughts
            ) / total_weight

            integrated = ThoughtUnit(
                content={
                    'sub_thoughts': [t.content for t, _ in sub_thoughts],
                    'synthesis': input_data
                },
                mode=IntelligenceMode.INTEGRATED,
                style=self.current_style,
                confidence=avg_confidence,
                derived_from=[t.id for t, _ in sub_thoughts]
            )
        else:
            integrated = ThoughtUnit(
                content=input_data,
                mode=IntelligenceMode.INTEGRATED,
                style=self.current_style
            )

        self.thoughts.append(integrated)
        return integrated

    def reflect(self) -> ThoughtUnit:
        """Reflective meta-thinking"""
        recent = self.thoughts[-10:] if self.thoughts else []

        reflection = ThoughtUnit(
            content={
                'recent_thoughts': len(recent),
                'modes_used': list(set(t.mode for t in recent)),
                'avg_confidence': sum(t.confidence for t in recent) / len(recent) if recent else 0,
                'patterns': self._find_patterns(recent)
            },
            mode=IntelligenceMode.REFLECTIVE,
            style=ThinkingStyle.SYSTEMS
        )

        self.thoughts.append(reflection)
        return reflection

    def _find_patterns(self, thoughts: List[ThoughtUnit]) -> List[str]:
        """Find patterns in thoughts"""
        patterns = []

        # Mode patterns
        mode_counts = {}
        for t in thoughts:
            mode_counts[t.mode] = mode_counts.get(t.mode, 0) + 1

        dominant = max(mode_counts.items(), key=lambda x: x[1])[0] if mode_counts else None
        if dominant:
            patterns.append(f"Dominant mode: {dominant.name}")

        # Confidence trend
        if len(thoughts) >= 3:
            early = [t.confidence for t in thoughts[:len(thoughts)//2]]
            late = [t.confidence for t in thoughts[len(thoughts)//2:]]

            early_avg = sum(early) / len(early) if early else 0
            late_avg = sum(late) / len(late) if late else 0

            if late_avg > early_avg + 0.1:
                patterns.append("Confidence increasing")
            elif early_avg > late_avg + 0.1:
                patterns.append("Confidence decreasing")

        return patterns

    def focus_on(self, target: Any, duration: float = 0.0):
        """Set focus"""
        self.focus = target
        self.focus_duration = duration

    def get_stream(self, n: int = 10) -> List[ThoughtUnit]:
        """Get thought stream"""
        return self.thoughts[-n:]


class ConsciousnessIntegrator:
    """
    Integrates consciousness aspects.
    """

    def __init__(self):
        # Consciousness state
        self.awareness_level: float = 1.0
        self.attention: Optional[Any] = None

        # Self-model
        self.self_model: Dict[str, Any] = {}

        # Experience stream
        self.experience_stream: List[Dict[str, Any]] = []

        # Integration
        self.unified_mind = UnifiedMind()

        # Monitoring
        self.meta_awareness: bool = True

    def experience(self, content: Any, source: str = "") -> Dict[str, Any]:
        """Record conscious experience"""
        exp = {
            'id': str(uuid.uuid4()),
            'content': content,
            'source': source,
            'awareness_level': self.awareness_level,
            'attention': self.attention,
            'timestamp': datetime.now()
        }

        self.experience_stream.append(exp)

        # Limit stream
        if len(self.experience_stream) > 1000:
            self.experience_stream.pop(0)

        return exp

    def attend(self, target: Any):
        """Direct attention"""
        self.attention = target
        self.unified_mind.focus_on(target)

    def integrate(self, experiences: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Integrate experiences into unified consciousness"""
        experiences = experiences or self.experience_stream[-10:]

        # Think about experiences
        thought = self.unified_mind.think({
            'experiences': [e['content'] for e in experiences],
            'sources': list(set(e['source'] for e in experiences))
        })

        # Update self-model
        self._update_self_model(experiences)

        return {
            'thought': thought,
            'experiences_integrated': len(experiences),
            'self_model_updated': True
        }

    def _update_self_model(self, experiences: List[Dict[str, Any]]):
        """Update self-model based on experiences"""
        # Count experience types
        sources = {}
        for e in experiences:
            src = e.get('source', 'unknown')
            sources[src] = sources.get(src, 0) + 1

        self.self_model['recent_experience_sources'] = sources
        self.self_model['experience_count'] = len(self.experience_stream)
        self.self_model['awareness_level'] = self.awareness_level
        self.self_model['updated_at'] = datetime.now()

    def self_reflect(self) -> Dict[str, Any]:
        """Deep self-reflection"""
        # Meta-cognitive reflection
        thought = self.unified_mind.reflect()

        reflection = {
            'self_model': self.self_model.copy(),
            'meta_thought': thought,
            'awareness': self.awareness_level,
            'attention': str(self.attention),
            'stream_depth': len(self.experience_stream),
            'meta_awareness_active': self.meta_awareness
        }

        return reflection

    def get_unified_state(self) -> Dict[str, Any]:
        """Get unified consciousness state"""
        return {
            'awareness_level': self.awareness_level,
            'attention': str(self.attention),
            'self_model': self.self_model,
            'thought_count': len(self.unified_mind.thoughts),
            'experience_count': len(self.experience_stream),
            'current_mode': self.unified_mind.current_mode.name,
            'meta_awareness': self.meta_awareness
        }


# Export all
__all__ = [
    'IntelligenceMode',
    'ThinkingStyle',
    'ThoughtUnit',
    'UnifiedMind',
    'ConsciousnessIntegrator',
]
