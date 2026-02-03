#!/usr/bin/env python3
"""
BAEL - Attention Manager
Advanced attention management for AI agents.

Features:
- Multi-head attention
- Self-attention mechanisms
- Cross-attention
- Attention masking
- Attention scoring
- Focus management
- Attention decay
- Priority-based attention
"""

import asyncio
import copy
import hashlib
import math
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

class AttentionType(Enum):
    """Attention mechanism type."""
    SELF = "self"
    CROSS = "cross"
    SPARSE = "sparse"
    LOCAL = "local"
    GLOBAL = "global"


class AttentionStatus(Enum):
    """Attention status."""
    ACTIVE = "active"
    DECAYING = "decaying"
    EXPIRED = "expired"
    BLOCKED = "blocked"


class FocusMode(Enum):
    """Focus mode."""
    SINGLE = "single"
    MULTI = "multi"
    DISTRIBUTED = "distributed"
    HIERARCHICAL = "hierarchical"


class AttentionPriority(Enum):
    """Attention priority."""
    BACKGROUND = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class DecayType(Enum):
    """Decay type."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    STEP = "step"
    NONE = "none"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class AttentionTarget:
    """Target of attention."""
    target_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    content: Any = None
    priority: AttentionPriority = AttentionPriority.NORMAL
    weight: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AttentionSpan:
    """Attention span for a target."""
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    target_id: str = ""
    attention_score: float = 1.0
    start_time: datetime = field(default_factory=datetime.now)
    duration: float = 0.0  # seconds
    decay_type: DecayType = DecayType.EXPONENTIAL
    status: AttentionStatus = AttentionStatus.ACTIVE


@dataclass
class AttentionHead:
    """Attention head configuration."""
    head_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    attention_type: AttentionType = AttentionType.SELF
    dimension: int = 64
    weights: List[float] = field(default_factory=list)


@dataclass
class AttentionMask:
    """Attention mask."""
    mask_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    blocked_targets: Set[str] = field(default_factory=set)
    allowed_targets: Optional[Set[str]] = None
    pattern: Optional[str] = None


@dataclass
class AttentionScore:
    """Attention score result."""
    target_id: str = ""
    score: float = 0.0
    normalized_score: float = 0.0
    rank: int = 0


@dataclass
class FocusState:
    """Current focus state."""
    primary_target: Optional[str] = None
    secondary_targets: List[str] = field(default_factory=list)
    focus_mode: FocusMode = FocusMode.SINGLE
    intensity: float = 1.0
    started_at: datetime = field(default_factory=datetime.now)


@dataclass
class AttentionStats:
    """Attention statistics."""
    total_targets: int = 0
    active_spans: int = 0
    avg_attention_score: float = 0.0
    focus_changes: int = 0
    blocked_targets: int = 0


# =============================================================================
# ATTENTION SCORER
# =============================================================================

class AttentionScorer:
    """Score attention for targets."""

    def __init__(self):
        self._priority_weights = {
            AttentionPriority.BACKGROUND: 0.1,
            AttentionPriority.LOW: 0.3,
            AttentionPriority.NORMAL: 0.5,
            AttentionPriority.HIGH: 0.7,
            AttentionPriority.URGENT: 0.9,
            AttentionPriority.CRITICAL: 1.0
        }

    def score(self, target: AttentionTarget) -> float:
        """Calculate attention score."""
        # Base score from priority
        base = self._priority_weights.get(target.priority, 0.5)

        # Apply weight
        weighted = base * target.weight

        # Recency boost (more recent = higher score)
        age = (datetime.now() - target.created_at).total_seconds()
        recency = max(0.1, 1.0 - (age / 3600))  # Decay over 1 hour

        return min(1.0, weighted * recency)

    def score_batch(
        self,
        targets: List[AttentionTarget]
    ) -> List[AttentionScore]:
        """Score multiple targets."""
        scores = []

        for target in targets:
            score = self.score(target)
            scores.append(AttentionScore(
                target_id=target.target_id,
                score=score
            ))

        # Normalize and rank
        total = sum(s.score for s in scores)

        for i, score in enumerate(sorted(scores, key=lambda s: s.score, reverse=True)):
            score.normalized_score = score.score / total if total > 0 else 0
            score.rank = i + 1

        return scores

    def softmax(self, scores: List[float], temperature: float = 1.0) -> List[float]:
        """Apply softmax normalization."""
        scaled = [s / temperature for s in scores]
        max_val = max(scaled)
        exp_scores = [math.exp(s - max_val) for s in scaled]
        total = sum(exp_scores)

        return [e / total for e in exp_scores]


# =============================================================================
# ATTENTION DECAY
# =============================================================================

class AttentionDecay:
    """Manage attention decay."""

    def __init__(self):
        self._half_life = 60.0  # seconds

    def decay(
        self,
        initial_score: float,
        elapsed_seconds: float,
        decay_type: DecayType
    ) -> float:
        """Apply decay to attention score."""
        if decay_type == DecayType.NONE:
            return initial_score

        if decay_type == DecayType.LINEAR:
            # Linear decay to 0 over 2 * half_life
            rate = initial_score / (2 * self._half_life)
            return max(0.0, initial_score - rate * elapsed_seconds)

        elif decay_type == DecayType.EXPONENTIAL:
            # Exponential decay
            decay_rate = math.log(2) / self._half_life
            return initial_score * math.exp(-decay_rate * elapsed_seconds)

        elif decay_type == DecayType.STEP:
            # Step decay (halve every half_life)
            steps = int(elapsed_seconds / self._half_life)
            return initial_score * (0.5 ** steps)

        return initial_score

    def set_half_life(self, seconds: float) -> None:
        """Set half life."""
        self._half_life = seconds

    def get_half_life(self) -> float:
        """Get half life."""
        return self._half_life


# =============================================================================
# MULTI-HEAD ATTENTION
# =============================================================================

class MultiHeadAttention:
    """Multi-head attention mechanism."""

    def __init__(self, num_heads: int = 8, dimension: int = 64):
        self._num_heads = num_heads
        self._dimension = dimension
        self._heads: List[AttentionHead] = []

        for i in range(num_heads):
            self._heads.append(AttentionHead(
                name=f"head_{i}",
                dimension=dimension
            ))

    def compute_attention(
        self,
        query: List[float],
        keys: List[List[float]],
        values: List[List[float]]
    ) -> List[float]:
        """Compute multi-head attention."""
        if not keys or not values:
            return []

        head_outputs = []

        for head in self._heads:
            # Simulate attention for each head
            head_output = self._single_head_attention(query, keys, values)
            head_outputs.append(head_output)

        # Concatenate and project
        if head_outputs and head_outputs[0]:
            # Average across heads for simplicity
            return [
                sum(h[i] for h in head_outputs) / len(head_outputs)
                for i in range(len(head_outputs[0]))
            ]

        return []

    def _single_head_attention(
        self,
        query: List[float],
        keys: List[List[float]],
        values: List[List[float]]
    ) -> List[float]:
        """Single head attention."""
        # Compute attention scores
        scores = []
        for key in keys:
            # Dot product
            score = sum(q * k for q, k in zip(query, key)) if query and key else 0
            # Scale
            score = score / math.sqrt(len(query)) if query else 0
            scores.append(score)

        # Softmax
        if scores:
            max_score = max(scores)
            exp_scores = [math.exp(s - max_score) for s in scores]
            total = sum(exp_scores)
            weights = [e / total for e in exp_scores]
        else:
            weights = []

        # Weighted sum of values
        if values and weights:
            output_dim = len(values[0])
            result = [0.0] * output_dim

            for weight, value in zip(weights, values):
                for i, v in enumerate(value):
                    result[i] += weight * v

            return result

        return []

    def get_heads(self) -> List[AttentionHead]:
        """Get attention heads."""
        return self._heads


# =============================================================================
# SELF ATTENTION
# =============================================================================

class SelfAttention:
    """Self-attention mechanism."""

    def __init__(self, dimension: int = 64):
        self._dimension = dimension

    def attend(
        self,
        sequence: List[List[float]]
    ) -> List[List[float]]:
        """Apply self-attention to sequence."""
        if not sequence:
            return []

        output = []

        for i, query in enumerate(sequence):
            # Compute attention weights for this position
            scores = []

            for key in sequence:
                score = sum(q * k for q, k in zip(query, key)) if query and key else 0
                score = score / math.sqrt(len(query)) if query else 0
                scores.append(score)

            # Softmax
            if scores:
                max_score = max(scores)
                exp_scores = [math.exp(s - max_score) for s in scores]
                total = sum(exp_scores)
                weights = [e / total for e in exp_scores]
            else:
                weights = []

            # Weighted sum
            if sequence and weights:
                output_dim = len(sequence[0])
                attended = [0.0] * output_dim

                for weight, value in zip(weights, sequence):
                    for j, v in enumerate(value):
                        attended[j] += weight * v

                output.append(attended)

        return output


# =============================================================================
# FOCUS MANAGER
# =============================================================================

class FocusManager:
    """Manage focus state."""

    def __init__(self):
        self._focus_state = FocusState()
        self._focus_history: List[FocusState] = []
        self._focus_changes = 0

    def set_primary(self, target_id: str) -> None:
        """Set primary focus."""
        self._save_current()
        self._focus_state.primary_target = target_id
        self._focus_state.started_at = datetime.now()
        self._focus_changes += 1

    def add_secondary(self, target_id: str) -> None:
        """Add secondary focus."""
        if target_id not in self._focus_state.secondary_targets:
            self._focus_state.secondary_targets.append(target_id)

    def remove_secondary(self, target_id: str) -> bool:
        """Remove secondary focus."""
        if target_id in self._focus_state.secondary_targets:
            self._focus_state.secondary_targets.remove(target_id)
            return True
        return False

    def set_mode(self, mode: FocusMode) -> None:
        """Set focus mode."""
        self._focus_state.focus_mode = mode

    def set_intensity(self, intensity: float) -> None:
        """Set focus intensity."""
        self._focus_state.intensity = max(0.0, min(1.0, intensity))

    def get_state(self) -> FocusState:
        """Get current focus state."""
        return self._focus_state

    def clear(self) -> None:
        """Clear focus."""
        self._save_current()
        self._focus_state = FocusState()
        self._focus_changes += 1

    def _save_current(self) -> None:
        """Save current state to history."""
        if self._focus_state.primary_target:
            self._focus_history.append(copy.deepcopy(self._focus_state))

    def get_history(self, limit: int = 10) -> List[FocusState]:
        """Get focus history."""
        return self._focus_history[-limit:]

    def get_focus_changes(self) -> int:
        """Get focus change count."""
        return self._focus_changes


# =============================================================================
# ATTENTION FILTER
# =============================================================================

class AttentionFilter:
    """Filter attention targets."""

    def __init__(self):
        self._masks: Dict[str, AttentionMask] = {}

    def add_mask(self, mask: AttentionMask) -> str:
        """Add attention mask."""
        self._masks[mask.mask_id] = mask
        return mask.mask_id

    def remove_mask(self, mask_id: str) -> bool:
        """Remove mask."""
        if mask_id in self._masks:
            del self._masks[mask_id]
            return True
        return False

    def block(self, target_id: str, mask_id: Optional[str] = None) -> None:
        """Block target."""
        if mask_id and mask_id in self._masks:
            self._masks[mask_id].blocked_targets.add(target_id)
        else:
            # Create default mask
            mask = AttentionMask(blocked_targets={target_id})
            self._masks[mask.mask_id] = mask

    def unblock(self, target_id: str) -> None:
        """Unblock target."""
        for mask in self._masks.values():
            mask.blocked_targets.discard(target_id)

    def is_blocked(self, target_id: str) -> bool:
        """Check if target is blocked."""
        for mask in self._masks.values():
            if target_id in mask.blocked_targets:
                return True
        return False

    def filter_targets(
        self,
        targets: List[AttentionTarget]
    ) -> List[AttentionTarget]:
        """Filter targets based on masks."""
        return [
            t for t in targets
            if not self.is_blocked(t.target_id)
        ]

    def get_blocked_count(self) -> int:
        """Get count of blocked targets."""
        blocked = set()
        for mask in self._masks.values():
            blocked.update(mask.blocked_targets)
        return len(blocked)


# =============================================================================
# ATTENTION MANAGER
# =============================================================================

class AttentionManager:
    """
    Attention Manager for BAEL.

    Advanced attention management.
    """

    def __init__(self, num_heads: int = 8, dimension: int = 64):
        self._targets: Dict[str, AttentionTarget] = {}
        self._spans: Dict[str, AttentionSpan] = {}
        self._scorer = AttentionScorer()
        self._decay = AttentionDecay()
        self._multi_head = MultiHeadAttention(num_heads, dimension)
        self._self_attention = SelfAttention(dimension)
        self._focus = FocusManager()
        self._filter = AttentionFilter()
        self._stats = AttentionStats()

    # -------------------------------------------------------------------------
    # TARGET MANAGEMENT
    # -------------------------------------------------------------------------

    def add_target(
        self,
        name: str,
        content: Any = None,
        priority: str = "normal",
        weight: float = 1.0
    ) -> str:
        """Add attention target."""
        priority_map = {
            "background": AttentionPriority.BACKGROUND,
            "low": AttentionPriority.LOW,
            "normal": AttentionPriority.NORMAL,
            "high": AttentionPriority.HIGH,
            "urgent": AttentionPriority.URGENT,
            "critical": AttentionPriority.CRITICAL
        }

        target = AttentionTarget(
            name=name,
            content=content,
            priority=priority_map.get(priority.lower(), AttentionPriority.NORMAL),
            weight=weight
        )

        self._targets[target.target_id] = target
        self._stats.total_targets += 1

        # Create attention span
        span = AttentionSpan(
            target_id=target.target_id,
            attention_score=self._scorer.score(target)
        )
        self._spans[span.span_id] = span
        self._stats.active_spans += 1

        return target.target_id

    def get_target(self, target_id: str) -> Optional[AttentionTarget]:
        """Get target."""
        return self._targets.get(target_id)

    def remove_target(self, target_id: str) -> bool:
        """Remove target."""
        if target_id in self._targets:
            del self._targets[target_id]

            # Remove associated spans
            for span_id, span in list(self._spans.items()):
                if span.target_id == target_id:
                    del self._spans[span_id]
                    self._stats.active_spans -= 1

            return True
        return False

    def update_priority(
        self,
        target_id: str,
        priority: str
    ) -> bool:
        """Update target priority."""
        target = self._targets.get(target_id)
        if not target:
            return False

        priority_map = {
            "background": AttentionPriority.BACKGROUND,
            "low": AttentionPriority.LOW,
            "normal": AttentionPriority.NORMAL,
            "high": AttentionPriority.HIGH,
            "urgent": AttentionPriority.URGENT,
            "critical": AttentionPriority.CRITICAL
        }

        target.priority = priority_map.get(priority.lower(), target.priority)
        return True

    # -------------------------------------------------------------------------
    # ATTENTION SCORING
    # -------------------------------------------------------------------------

    def score_target(self, target_id: str) -> float:
        """Score single target."""
        target = self._targets.get(target_id)
        if not target:
            return 0.0
        return self._scorer.score(target)

    def score_all(self) -> List[AttentionScore]:
        """Score all targets."""
        targets = list(self._targets.values())
        filtered = self._filter.filter_targets(targets)
        return self._scorer.score_batch(filtered)

    def get_top_targets(self, n: int = 5) -> List[Tuple[AttentionTarget, float]]:
        """Get top n targets by score."""
        scores = self.score_all()
        scores.sort(key=lambda s: s.score, reverse=True)

        result = []
        for score in scores[:n]:
            target = self._targets.get(score.target_id)
            if target:
                result.append((target, score.score))

        return result

    # -------------------------------------------------------------------------
    # ATTENTION DECAY
    # -------------------------------------------------------------------------

    def apply_decay(self) -> int:
        """Apply decay to all attention spans."""
        updated = 0

        for span in self._spans.values():
            if span.status != AttentionStatus.ACTIVE:
                continue

            elapsed = (datetime.now() - span.start_time).total_seconds()
            new_score = self._decay.decay(
                span.attention_score,
                elapsed,
                span.decay_type
            )

            if new_score < 0.01:
                span.status = AttentionStatus.EXPIRED
                self._stats.active_spans -= 1
            elif new_score < span.attention_score * 0.5:
                span.status = AttentionStatus.DECAYING

            span.attention_score = new_score
            span.duration = elapsed
            updated += 1

        return updated

    def set_decay_half_life(self, seconds: float) -> None:
        """Set decay half life."""
        self._decay.set_half_life(seconds)

    # -------------------------------------------------------------------------
    # FOCUS
    # -------------------------------------------------------------------------

    def focus_on(self, target_id: str) -> bool:
        """Focus on target."""
        if target_id not in self._targets:
            return False

        self._focus.set_primary(target_id)
        self._stats.focus_changes += 1
        return True

    def add_secondary_focus(self, target_id: str) -> bool:
        """Add secondary focus."""
        if target_id not in self._targets:
            return False

        self._focus.add_secondary(target_id)
        return True

    def clear_focus(self) -> None:
        """Clear focus."""
        self._focus.clear()
        self._stats.focus_changes += 1

    def get_focus_state(self) -> FocusState:
        """Get current focus state."""
        return self._focus.get_state()

    def set_focus_mode(self, mode: str) -> None:
        """Set focus mode."""
        mode_map = {
            "single": FocusMode.SINGLE,
            "multi": FocusMode.MULTI,
            "distributed": FocusMode.DISTRIBUTED,
            "hierarchical": FocusMode.HIERARCHICAL
        }

        self._focus.set_mode(mode_map.get(mode.lower(), FocusMode.SINGLE))

    def set_focus_intensity(self, intensity: float) -> None:
        """Set focus intensity."""
        self._focus.set_intensity(intensity)

    # -------------------------------------------------------------------------
    # BLOCKING
    # -------------------------------------------------------------------------

    def block_target(self, target_id: str) -> None:
        """Block target from attention."""
        self._filter.block(target_id)
        self._stats.blocked_targets = self._filter.get_blocked_count()

    def unblock_target(self, target_id: str) -> None:
        """Unblock target."""
        self._filter.unblock(target_id)
        self._stats.blocked_targets = self._filter.get_blocked_count()

    def is_blocked(self, target_id: str) -> bool:
        """Check if target is blocked."""
        return self._filter.is_blocked(target_id)

    # -------------------------------------------------------------------------
    # MULTI-HEAD ATTENTION
    # -------------------------------------------------------------------------

    def compute_multi_head(
        self,
        query: List[float],
        key_target_ids: List[str],
        value_target_ids: Optional[List[str]] = None
    ) -> List[float]:
        """Compute multi-head attention."""
        if value_target_ids is None:
            value_target_ids = key_target_ids

        # For simplicity, use target scores as embeddings
        keys = []
        values = []

        for tid in key_target_ids:
            target = self._targets.get(tid)
            if target:
                score = self._scorer.score(target)
                keys.append([score] * len(query) if query else [score])

        for tid in value_target_ids:
            target = self._targets.get(tid)
            if target:
                score = self._scorer.score(target)
                values.append([score] * len(query) if query else [score])

        return self._multi_head.compute_attention(query, keys, values)

    # -------------------------------------------------------------------------
    # SELF ATTENTION
    # -------------------------------------------------------------------------

    def compute_self_attention(
        self,
        target_ids: List[str]
    ) -> Dict[str, float]:
        """Compute self-attention across targets."""
        # Create sequence of embeddings
        sequence = []
        id_map = []

        for tid in target_ids:
            target = self._targets.get(tid)
            if target:
                score = self._scorer.score(target)
                sequence.append([score, target.weight])
                id_map.append(tid)

        # Apply self-attention
        attended = self._self_attention.attend(sequence)

        # Map back to target IDs
        result = {}
        for i, attended_vec in enumerate(attended):
            if i < len(id_map):
                result[id_map[i]] = sum(attended_vec) / len(attended_vec) if attended_vec else 0

        return result

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> AttentionStats:
        """Get attention statistics."""
        scores = self.score_all()

        self._stats.avg_attention_score = (
            sum(s.score for s in scores) / len(scores)
            if scores else 0.0
        )
        self._stats.total_targets = len(self._targets)
        self._stats.focus_changes = self._focus.get_focus_changes()

        return self._stats

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        return {
            "targets": [
                {
                    "id": t.target_id,
                    "name": t.name,
                    "priority": t.priority.name,
                    "weight": t.weight
                }
                for t in self._targets.values()
            ],
            "focus": {
                "primary": self._focus.get_state().primary_target,
                "secondary": self._focus.get_state().secondary_targets,
                "mode": self._focus.get_state().focus_mode.value
            },
            "stats": {
                "total_targets": len(self._targets),
                "active_spans": self._stats.active_spans,
                "blocked": self._stats.blocked_targets
            }
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Attention Manager."""
    print("=" * 70)
    print("BAEL - ATTENTION MANAGER DEMO")
    print("Advanced Attention Management")
    print("=" * 70)
    print()

    manager = AttentionManager(num_heads=4, dimension=32)

    # 1. Add Targets
    print("1. ADD TARGETS:")
    print("-" * 40)

    t1 = manager.add_target("Task A", {"desc": "Important task"}, "high", 1.0)
    t2 = manager.add_target("Task B", {"desc": "Normal task"}, "normal", 0.8)
    t3 = manager.add_target("Task C", {"desc": "Background task"}, "low", 0.5)
    t4 = manager.add_target("Alert", {"desc": "Critical alert"}, "critical", 1.0)

    print(f"   Added Task A (high): {t1[:8]}...")
    print(f"   Added Task B (normal): {t2[:8]}...")
    print(f"   Added Task C (low): {t3[:8]}...")
    print(f"   Added Alert (critical): {t4[:8]}...")
    print()

    # 2. Score Targets
    print("2. SCORE TARGETS:")
    print("-" * 40)

    scores = manager.score_all()

    for score in sorted(scores, key=lambda s: s.score, reverse=True):
        target = manager.get_target(score.target_id)
        print(f"   {target.name}: score={score.score:.3f}, rank={score.rank}")
    print()

    # 3. Get Top Targets
    print("3. TOP TARGETS:")
    print("-" * 40)

    top = manager.get_top_targets(3)

    for target, score in top:
        print(f"   {target.name}: {score:.3f}")
    print()

    # 4. Focus on Target
    print("4. FOCUS ON TARGET:")
    print("-" * 40)

    manager.focus_on(t4)
    focus = manager.get_focus_state()

    print(f"   Primary focus: {manager.get_target(focus.primary_target).name}")
    print(f"   Intensity: {focus.intensity}")
    print()

    # 5. Add Secondary Focus
    print("5. SECONDARY FOCUS:")
    print("-" * 40)

    manager.add_secondary_focus(t1)
    manager.add_secondary_focus(t2)
    focus = manager.get_focus_state()

    print(f"   Primary: {manager.get_target(focus.primary_target).name}")
    print(f"   Secondary: {[manager.get_target(tid).name for tid in focus.secondary_targets]}")
    print()

    # 6. Focus Modes
    print("6. FOCUS MODES:")
    print("-" * 40)

    manager.set_focus_mode("distributed")
    manager.set_focus_intensity(0.8)
    focus = manager.get_focus_state()

    print(f"   Mode: {focus.focus_mode.value}")
    print(f"   Intensity: {focus.intensity}")
    print()

    # 7. Block Target
    print("7. BLOCK TARGET:")
    print("-" * 40)

    manager.block_target(t3)

    print(f"   Blocked: Task C")
    print(f"   Is blocked: {manager.is_blocked(t3)}")

    scores = manager.score_all()
    print(f"   Active targets: {len(scores)}")
    print()

    # 8. Unblock Target
    print("8. UNBLOCK TARGET:")
    print("-" * 40)

    manager.unblock_target(t3)

    print(f"   Unblocked: Task C")
    print(f"   Is blocked: {manager.is_blocked(t3)}")
    print()

    # 9. Attention Decay
    print("9. ATTENTION DECAY:")
    print("-" * 40)

    manager.set_decay_half_life(30.0)  # 30 seconds

    # Simulate time passing
    initial_score = manager.score_target(t1)
    updated = manager.apply_decay()

    print(f"   Half life: 30 seconds")
    print(f"   Updated spans: {updated}")
    print(f"   Initial score: {initial_score:.3f}")
    print()

    # 10. Update Priority
    print("10. UPDATE PRIORITY:")
    print("-" * 40)

    old_score = manager.score_target(t2)
    manager.update_priority(t2, "urgent")
    new_score = manager.score_target(t2)

    print(f"   Task B priority: normal -> urgent")
    print(f"   Score: {old_score:.3f} -> {new_score:.3f}")
    print()

    # 11. Self Attention
    print("11. SELF ATTENTION:")
    print("-" * 40)

    target_ids = [t1, t2, t3, t4]
    self_attention = manager.compute_self_attention(target_ids)

    print("   Self-attention scores:")
    for tid, score in self_attention.items():
        target = manager.get_target(tid)
        print(f"     {target.name}: {score:.3f}")
    print()

    # 12. Multi-Head Attention
    print("12. MULTI-HEAD ATTENTION:")
    print("-" * 40)

    query = [0.5, 0.5, 0.5, 0.5]
    result = manager.compute_multi_head(query, [t1, t2, t3, t4])

    print(f"   Query: {query}")
    print(f"   Attention output: {[f'{r:.3f}' for r in result]}")
    print()

    # 13. Focus History
    print("13. FOCUS HISTORY:")
    print("-" * 40)

    # Make some focus changes
    manager.focus_on(t1)
    manager.focus_on(t2)

    history = manager._focus.get_history()

    print(f"   Focus changes: {manager._focus.get_focus_changes()}")
    print(f"   History entries: {len(history)}")
    print()

    # 14. Statistics
    print("14. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()

    print(f"   Total targets: {stats.total_targets}")
    print(f"   Active spans: {stats.active_spans}")
    print(f"   Avg attention: {stats.avg_attention_score:.3f}")
    print(f"   Focus changes: {stats.focus_changes}")
    print(f"   Blocked: {stats.blocked_targets}")
    print()

    # 15. Export
    print("15. EXPORT:")
    print("-" * 40)

    export = manager.to_dict()

    print(f"   Targets: {len(export['targets'])}")
    print(f"   Focus mode: {export['focus']['mode']}")
    print(f"   Stats: {export['stats']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Attention Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
