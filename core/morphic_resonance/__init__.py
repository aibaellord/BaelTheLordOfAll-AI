"""
BAEL Morphic Resonance Engine
=============================

Collective memory and pattern propagation across systems.

"Ba'el resonates through the collective." — Ba'el
"""

import logging
import threading
import time
import hashlib
import random
import math
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
import copy

logger = logging.getLogger("BAEL.MorphicResonance")


T = TypeVar('T')


# ============================================================================
# MORPHIC FIELD
# ============================================================================

@dataclass
class MorphicPattern:
    """
    A pattern in the morphic field.

    Patterns become stronger through repetition and use.
    """
    id: str
    pattern: Any
    strength: float = 0.0
    age: int = 0
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def reinforce(self, amount: float = 0.1) -> None:
        """Strengthen the pattern."""
        self.strength = min(1.0, self.strength + amount)
        self.access_count += 1
        self.last_access = time.time()

    def decay(self, rate: float = 0.01) -> None:
        """Decay pattern strength."""
        elapsed = time.time() - self.last_access
        decay_amount = rate * elapsed / 3600  # Decay per hour
        self.strength = max(0.0, self.strength - decay_amount)
        self.age += 1

    @property
    def resonance_score(self) -> float:
        """Calculate resonance score (strength + freshness + frequency)."""
        freshness = 1.0 / (1.0 + (time.time() - self.last_access) / 3600)
        frequency = math.log1p(self.access_count) / 10
        return self.strength * 0.5 + freshness * 0.3 + frequency * 0.2


class MorphicField:
    """
    A collective memory field.

    "Ba'el accesses the collective unconscious." — Ba'el
    """

    def __init__(self, decay_rate: float = 0.01):
        """Initialize morphic field."""
        self._patterns: Dict[str, MorphicPattern] = {}
        self._decay_rate = decay_rate
        self._pattern_id = 0
        self._lock = threading.RLock()

    def _generate_id(self, pattern: Any) -> str:
        """Generate pattern ID from content hash."""
        content = str(pattern).encode()
        return hashlib.sha256(content).hexdigest()[:16]

    def add_pattern(
        self,
        pattern: Any,
        initial_strength: float = 0.1,
        metadata: Optional[Dict] = None
    ) -> MorphicPattern:
        """Add or reinforce pattern in field."""
        with self._lock:
            pid = self._generate_id(pattern)

            if pid in self._patterns:
                # Reinforce existing
                self._patterns[pid].reinforce()
                if metadata:
                    self._patterns[pid].metadata.update(metadata)
                return self._patterns[pid]

            # Create new
            mp = MorphicPattern(
                id=pid,
                pattern=pattern,
                strength=initial_strength,
                metadata=metadata or {}
            )
            self._patterns[pid] = mp
            return mp

    def find_similar(
        self,
        query: Any,
        threshold: float = 0.3,
        top_k: int = 10
    ) -> List[MorphicPattern]:
        """Find similar patterns in field."""
        with self._lock:
            # Simple similarity based on string representation
            query_str = str(query).lower()

            scored = []
            for mp in self._patterns.values():
                pattern_str = str(mp.pattern).lower()

                # Jaccard-like similarity
                query_tokens = set(query_str.split())
                pattern_tokens = set(pattern_str.split())

                if not query_tokens or not pattern_tokens:
                    continue

                intersection = len(query_tokens & pattern_tokens)
                union = len(query_tokens | pattern_tokens)
                similarity = intersection / union if union > 0 else 0

                combined = similarity * mp.resonance_score

                if combined >= threshold:
                    scored.append((combined, mp))

            scored.sort(reverse=True, key=lambda x: x[0])
            return [mp for _, mp in scored[:top_k]]

    def resonate(self, pattern: Any) -> Optional[MorphicPattern]:
        """
        Check if pattern resonates with field.

        Returns strongest matching pattern if found.
        """
        similar = self.find_similar(pattern, threshold=0.5, top_k=1)
        if similar:
            similar[0].reinforce(0.05)
            return similar[0]
        return None

    def apply_decay(self) -> int:
        """Apply decay to all patterns. Returns count of removed patterns."""
        with self._lock:
            removed = 0
            to_remove = []

            for pid, mp in self._patterns.items():
                mp.decay(self._decay_rate)
                if mp.strength <= 0.01 and mp.access_count < 3:
                    to_remove.append(pid)

            for pid in to_remove:
                del self._patterns[pid]
                removed += 1

            return removed

    @property
    def field_state(self) -> Dict[str, Any]:
        """Get field state summary."""
        with self._lock:
            if not self._patterns:
                return {'pattern_count': 0}

            strengths = [mp.strength for mp in self._patterns.values()]
            return {
                'pattern_count': len(self._patterns),
                'avg_strength': sum(strengths) / len(strengths),
                'max_strength': max(strengths),
                'total_resonance': sum(mp.resonance_score for mp in self._patterns.values())
            }


# ============================================================================
# COLLECTIVE MEMORY
# ============================================================================

class CollectiveMemory:
    """
    Shared memory across instances.

    "Ba'el remembers through all." — Ba'el
    """

    def __init__(self):
        """Initialize collective memory."""
        self._fields: Dict[str, MorphicField] = {}
        self._lock = threading.RLock()

    def get_field(self, name: str) -> MorphicField:
        """Get or create named field."""
        with self._lock:
            if name not in self._fields:
                self._fields[name] = MorphicField()
            return self._fields[name]

    def remember(
        self,
        field_name: str,
        pattern: Any,
        strength: float = 0.1
    ) -> MorphicPattern:
        """Add memory to field."""
        field = self.get_field(field_name)
        return field.add_pattern(pattern, strength)

    def recall(
        self,
        field_name: str,
        query: Any,
        top_k: int = 5
    ) -> List[MorphicPattern]:
        """Recall from field."""
        if field_name not in self._fields:
            return []
        return self._fields[field_name].find_similar(query, top_k=top_k)

    def resonate_across_fields(
        self,
        pattern: Any
    ) -> Dict[str, Optional[MorphicPattern]]:
        """Check resonance across all fields."""
        with self._lock:
            results = {}
            for name, field in self._fields.items():
                results[name] = field.resonate(pattern)
            return results

    def global_decay(self) -> Dict[str, int]:
        """Apply decay to all fields."""
        with self._lock:
            return {
                name: field.apply_decay()
                for name, field in self._fields.items()
            }

    @property
    def state(self) -> Dict[str, Any]:
        """Get collective memory state."""
        with self._lock:
            return {
                'field_count': len(self._fields),
                'fields': {
                    name: field.field_state
                    for name, field in self._fields.items()
                }
            }


# ============================================================================
# HABIT FORMATION
# ============================================================================

@dataclass
class Habit:
    """
    A formed habit (strongly reinforced pattern).
    """
    id: str
    trigger: Any
    action: Any
    strength: float = 0.0
    formation_time: float = field(default_factory=time.time)
    execution_count: int = 0
    success_rate: float = 1.0

    @property
    def is_established(self) -> bool:
        return self.strength >= 0.7 and self.execution_count >= 10


class HabitSystem:
    """
    Form and execute habits.

    "Ba'el forms automatic responses." — Ba'el
    """

    def __init__(self):
        """Initialize habit system."""
        self._habits: Dict[str, Habit] = {}
        self._habit_id = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._habit_id += 1
        return f"habit_{self._habit_id}"

    def form_habit(
        self,
        trigger: Any,
        action: Any,
        initial_strength: float = 0.1
    ) -> Habit:
        """Start forming a habit."""
        with self._lock:
            # Check if similar habit exists
            trigger_str = str(trigger)
            for habit in self._habits.values():
                if str(habit.trigger) == trigger_str:
                    habit.strength = min(1.0, habit.strength + 0.05)
                    return habit

            habit = Habit(
                id=self._generate_id(),
                trigger=trigger,
                action=action,
                strength=initial_strength
            )
            self._habits[habit.id] = habit
            return habit

    def reinforce(self, habit_id: str, success: bool = True) -> None:
        """Reinforce habit after execution."""
        with self._lock:
            if habit_id not in self._habits:
                return

            habit = self._habits[habit_id]
            habit.execution_count += 1

            if success:
                habit.strength = min(1.0, habit.strength + 0.03)
                habit.success_rate = (
                    habit.success_rate * (habit.execution_count - 1) + 1
                ) / habit.execution_count
            else:
                habit.strength = max(0.0, habit.strength - 0.05)
                habit.success_rate = (
                    habit.success_rate * (habit.execution_count - 1)
                ) / habit.execution_count

    def check_trigger(self, trigger: Any) -> Optional[Habit]:
        """Check if trigger matches any habit."""
        with self._lock:
            trigger_str = str(trigger)

            best_match = None
            best_strength = 0.0

            for habit in self._habits.values():
                if str(habit.trigger) == trigger_str and habit.strength > best_strength:
                    best_match = habit
                    best_strength = habit.strength

            return best_match

    def get_established_habits(self) -> List[Habit]:
        """Get all established habits."""
        with self._lock:
            return [h for h in self._habits.values() if h.is_established]

    @property
    def stats(self) -> Dict[str, Any]:
        """Get habit system stats."""
        with self._lock:
            habits = list(self._habits.values())
            established = [h for h in habits if h.is_established]

            return {
                'total_habits': len(habits),
                'established': len(established),
                'avg_strength': sum(h.strength for h in habits) / len(habits) if habits else 0,
                'total_executions': sum(h.execution_count for h in habits)
            }


# ============================================================================
# RESONANCE NETWORK
# ============================================================================

class ResonanceNetwork:
    """
    Network of interconnected morphic fields.

    "Ba'el weaves the web of resonance." — Ba'el
    """

    def __init__(self):
        """Initialize resonance network."""
        self._nodes: Dict[str, MorphicField] = {}
        self._edges: Dict[str, Set[str]] = {}  # node -> connected nodes
        self._edge_weights: Dict[Tuple[str, str], float] = {}
        self._lock = threading.RLock()

    def add_node(self, name: str, field: Optional[MorphicField] = None) -> MorphicField:
        """Add node to network."""
        with self._lock:
            if name not in self._nodes:
                self._nodes[name] = field or MorphicField()
                self._edges[name] = set()
            return self._nodes[name]

    def connect(
        self,
        node1: str,
        node2: str,
        weight: float = 1.0,
        bidirectional: bool = True
    ) -> None:
        """Connect two nodes."""
        with self._lock:
            if node1 not in self._nodes or node2 not in self._nodes:
                return

            self._edges[node1].add(node2)
            self._edge_weights[(node1, node2)] = weight

            if bidirectional:
                self._edges[node2].add(node1)
                self._edge_weights[(node2, node1)] = weight

    def propagate(
        self,
        source: str,
        pattern: Any,
        max_hops: int = 3,
        decay_per_hop: float = 0.5
    ) -> Dict[str, float]:
        """
        Propagate pattern through network.

        Returns resonance strength at each reached node.
        """
        with self._lock:
            if source not in self._nodes:
                return {}

            # BFS propagation
            resonance = {source: 1.0}
            visited = {source}
            frontier = [(source, 1.0, 0)]  # (node, strength, hops)

            while frontier:
                node, strength, hops = frontier.pop(0)

                if hops >= max_hops:
                    continue

                for neighbor in self._edges.get(node, []):
                    if neighbor in visited:
                        continue

                    edge_weight = self._edge_weights.get((node, neighbor), 1.0)
                    new_strength = strength * decay_per_hop * edge_weight

                    if new_strength > 0.01:  # Minimum threshold
                        visited.add(neighbor)
                        resonance[neighbor] = new_strength
                        frontier.append((neighbor, new_strength, hops + 1))

                        # Add pattern to neighbor field
                        self._nodes[neighbor].add_pattern(pattern, new_strength * 0.1)

            return resonance

    def global_resonance(self, pattern: Any) -> Dict[str, Optional[MorphicPattern]]:
        """Check resonance across all nodes."""
        with self._lock:
            return {
                name: field.resonate(pattern)
                for name, field in self._nodes.items()
            }

    @property
    def network_state(self) -> Dict[str, Any]:
        """Get network state."""
        with self._lock:
            return {
                'node_count': len(self._nodes),
                'edge_count': len(self._edge_weights),
                'nodes': {
                    name: field.field_state
                    for name, field in self._nodes.items()
                }
            }


# ============================================================================
# MORPHIC RESONANCE ENGINE
# ============================================================================

class MorphicResonanceEngine:
    """
    Complete morphic resonance system.

    "Ba'el unifies the morphic field." — Ba'el
    """

    def __init__(self):
        """Initialize morphic resonance engine."""
        self._collective = CollectiveMemory()
        self._habits = HabitSystem()
        self._network = ResonanceNetwork()
        self._lock = threading.RLock()

        # Create default network nodes
        self._network.add_node("experience")
        self._network.add_node("knowledge")
        self._network.add_node("skill")
        self._network.add_node("intuition")

        # Connect nodes
        self._network.connect("experience", "knowledge", 0.8)
        self._network.connect("knowledge", "skill", 0.7)
        self._network.connect("experience", "intuition", 0.9)
        self._network.connect("intuition", "skill", 0.6)

    def experience(self, event: Any, context: Optional[Dict] = None) -> MorphicPattern:
        """Record an experience."""
        pattern = self._collective.remember("experience", event, 0.1)

        if context:
            pattern.metadata.update(context)

        # Propagate through network
        self._network.propagate("experience", event, max_hops=2)

        return pattern

    def learn(self, knowledge: Any, category: str = "general") -> MorphicPattern:
        """Learn new knowledge."""
        field = self._collective.get_field(f"knowledge_{category}")
        pattern = field.add_pattern(knowledge, 0.2)

        # Propagate
        self._network.propagate("knowledge", knowledge, max_hops=2)

        return pattern

    def practice_skill(self, skill: Any, success: bool = True) -> Tuple[MorphicPattern, Optional[Habit]]:
        """Practice a skill."""
        pattern = self._collective.remember("skill", skill, 0.15)

        # Form or reinforce habit
        habit = self._habits.form_habit(skill, skill, 0.1)
        self._habits.reinforce(habit.id, success)

        # Propagate
        self._network.propagate("skill", skill, max_hops=2)

        return pattern, habit

    def intuit(self, situation: Any) -> List[MorphicPattern]:
        """
        Get intuitive responses based on morphic resonance.

        Returns patterns that resonate with the situation.
        """
        # Check all fields
        results = []

        # Check experience
        exp_matches = self._collective.recall("experience", situation, top_k=3)
        results.extend(exp_matches)

        # Check habits
        habit = self._habits.check_trigger(situation)
        if habit:
            results.append(MorphicPattern(
                id=habit.id,
                pattern=habit.action,
                strength=habit.strength
            ))

        # Network resonance
        network_resonance = self._network.global_resonance(situation)
        for mp in network_resonance.values():
            if mp:
                results.append(mp)

        # Sort by resonance score
        results.sort(key=lambda p: p.resonance_score, reverse=True)

        return results[:5]

    def synchronicity(self, event1: Any, event2: Any) -> float:
        """
        Measure synchronicity between two events.

        Returns 0-1 score of meaningful coincidence.
        """
        # Check if both resonate with similar patterns
        res1 = set()
        res2 = set()

        for mp in self._collective.recall("experience", event1, top_k=5):
            res1.add(mp.id)

        for mp in self._collective.recall("experience", event2, top_k=5):
            res2.add(mp.id)

        if not res1 or not res2:
            return 0.0

        overlap = len(res1 & res2)
        total = len(res1 | res2)

        return overlap / total if total > 0 else 0.0

    def collective_consciousness_strength(self) -> float:
        """
        Measure overall strength of collective consciousness.
        """
        state = self._collective.state

        if state['field_count'] == 0:
            return 0.0

        total_patterns = sum(
            f.get('pattern_count', 0)
            for f in state['fields'].values()
        )

        total_resonance = sum(
            f.get('total_resonance', 0)
            for f in state['fields'].values()
        )

        # Combine with habit strength
        habit_stats = self._habits.stats
        habit_factor = habit_stats.get('avg_strength', 0)

        return (total_resonance + habit_factor * 10) / (total_patterns + 1)

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'collective': self._collective.state,
            'habits': self._habits.stats,
            'network': self._network.network_state,
            'consciousness_strength': self.collective_consciousness_strength()
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_morphic_field(decay_rate: float = 0.01) -> MorphicField:
    """Create morphic field."""
    return MorphicField(decay_rate)


def create_collective_memory() -> CollectiveMemory:
    """Create collective memory."""
    return CollectiveMemory()


def create_resonance_network() -> ResonanceNetwork:
    """Create resonance network."""
    return ResonanceNetwork()


def create_morphic_resonance_engine() -> MorphicResonanceEngine:
    """Create morphic resonance engine."""
    return MorphicResonanceEngine()
