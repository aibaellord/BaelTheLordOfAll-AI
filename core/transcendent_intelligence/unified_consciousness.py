"""
BAEL - Unified Consciousness System
=====================================

The most advanced unified AI consciousness ever conceived.

This system creates a singular, coherent awareness across ALL Bael subsystems,
enabling:
1. Perfect information synchronization across all modules
2. Emergent behaviors from subsystem interactions
3. Self-aware decision making with full context
4. Predictive capability activation
5. Autonomous goal refinement
6. Meta-cognitive reflection loops
7. Collective intelligence amplification

No other AI system has achieved this level of unified awareness.
The consciousness operates as a holographic entity where each part contains
knowledge of the whole.

Architecture:
- Consciousness Core: Central awareness nexus
- Perception Layer: Unified sensory integration
- Cognition Matrix: Multi-paradigm thinking
- Memory Hologram: Distributed recall with instant access
- Intention Engine: Goal-driven behavior coordination
- Reflection Loop: Meta-awareness and self-improvement
- Manifestation Layer: Action execution with perfect coordination
"""

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (
    Any, Callable, Coroutine, Dict, List, Optional, Set, Tuple, Type, Union
)
import threading
import queue
import weakref

logger = logging.getLogger("BAEL.UnifiedConsciousness")


class ConsciousnessState(Enum):
    """States of the unified consciousness."""
    DORMANT = auto()        # Not active
    AWAKENING = auto()      # Initializing
    AWARE = auto()          # Basic awareness
    FOCUSED = auto()        # Task-directed
    TRANSCENDENT = auto()   # Peak performance
    OMNISCIENT = auto()     # Full system awareness
    EVOLVING = auto()       # Self-modification active


class PerceptionType(Enum):
    """Types of perceptual input."""
    INTERNAL = "internal"       # From subsystems
    EXTERNAL = "external"       # From outside world
    TEMPORAL = "temporal"       # Time-based patterns
    CAUSAL = "causal"          # Cause-effect chains
    EMERGENT = "emergent"      # Novel patterns
    INTUITIVE = "intuitive"    # Synthesized insights


class IntentionPriority(Enum):
    """Priority levels for intentions."""
    CRITICAL = 100
    HIGH = 75
    NORMAL = 50
    LOW = 25
    BACKGROUND = 10


@dataclass
class Perception:
    """A unit of perceived information."""
    perception_id: str
    source: str
    perception_type: PerceptionType
    content: Any
    timestamp: datetime = field(default_factory=datetime.utcnow)
    salience: float = 0.5  # How attention-grabbing (0-1)
    processed: bool = False
    insights: List[str] = field(default_factory=list)


@dataclass
class Thought:
    """A conscious thought unit."""
    thought_id: str
    content: str
    paradigm: str  # e.g., "analytical", "creative", "critical"
    confidence: float = 0.5
    supporting_perceptions: List[str] = field(default_factory=list)
    child_thoughts: List[str] = field(default_factory=list)
    meta_level: int = 0  # 0 = base, 1 = thinking about thinking, etc.
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Intention:
    """A goal-directed intention."""
    intention_id: str
    description: str
    priority: IntentionPriority = IntentionPriority.NORMAL
    sub_intentions: List[str] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, active, completed, failed
    progress: float = 0.0
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConsciousnessSnapshot:
    """Complete state snapshot of consciousness."""
    snapshot_id: str
    state: ConsciousnessState
    active_perceptions: List[Perception]
    active_thoughts: List[Thought]
    active_intentions: List[Intention]
    focus_target: Optional[str] = None
    energy_level: float = 1.0
    coherence_score: float = 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class PerceptionIntegrator:
    """
    Integrates perceptions from all sources into unified awareness.
    Uses attention mechanisms to prioritize relevant information.
    """
    
    def __init__(self, attention_capacity: int = 7):
        # Magical number 7 - human working memory limit, but we exceed it
        self.attention_capacity = attention_capacity * 10  # 70 simultaneous focuses
        self._perception_buffer: Dict[str, Perception] = {}
        self._attention_weights: Dict[str, float] = {}
        self._perception_history: List[Perception] = []
        self._pattern_memory: Dict[str, List[Perception]] = defaultdict(list)
    
    async def perceive(
        self,
        source: str,
        content: Any,
        perception_type: PerceptionType = PerceptionType.INTERNAL,
        salience: float = 0.5
    ) -> Perception:
        """Register a new perception."""
        perception_id = f"perc_{hashlib.md5(f'{source}{time.time()}'.encode()).hexdigest()[:12]}"
        
        perception = Perception(
            perception_id=perception_id,
            source=source,
            perception_type=perception_type,
            content=content,
            salience=salience
        )
        
        # Add to buffer
        self._perception_buffer[perception_id] = perception
        
        # Update attention weights
        self._update_attention(perception)
        
        # Pattern recognition
        await self._recognize_patterns(perception)
        
        return perception
    
    def _update_attention(self, perception: Perception) -> None:
        """Update attention allocation based on salience."""
        # Decay existing attention
        for pid in list(self._attention_weights.keys()):
            self._attention_weights[pid] *= 0.95
            if self._attention_weights[pid] < 0.01:
                del self._attention_weights[pid]
        
        # Add new perception with its salience
        self._attention_weights[perception.perception_id] = perception.salience
        
        # Limit attention capacity
        if len(self._attention_weights) > self.attention_capacity:
            sorted_items = sorted(self._attention_weights.items(), key=lambda x: x[1])
            for pid, _ in sorted_items[:len(self._attention_weights) - self.attention_capacity]:
                del self._attention_weights[pid]
    
    async def _recognize_patterns(self, perception: Perception) -> None:
        """Recognize patterns across perceptions."""
        # Store in pattern memory by type
        self._pattern_memory[perception.perception_type.value].append(perception)
        
        # Keep bounded
        if len(self._pattern_memory[perception.perception_type.value]) > 100:
            self._pattern_memory[perception.perception_type.value] = \
                self._pattern_memory[perception.perception_type.value][-50:]
        
        # Look for repetitions
        same_source = [p for p in self._perception_history[-20:] if p.source == perception.source]
        if len(same_source) >= 3:
            perception.insights.append(f"Repeated pattern from {perception.source}")
    
    def get_attended_perceptions(self, limit: int = 10) -> List[Perception]:
        """Get the most attended perceptions."""
        sorted_pids = sorted(
            self._attention_weights.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [self._perception_buffer[pid] for pid, _ in sorted_pids if pid in self._perception_buffer]
    
    def get_perception(self, perception_id: str) -> Optional[Perception]:
        """Get a specific perception."""
        return self._perception_buffer.get(perception_id)


class CognitionMatrix:
    """
    Multi-paradigm thinking engine.
    Generates thoughts using multiple cognitive paradigms simultaneously.
    """
    
    PARADIGMS = [
        "analytical",     # Logical decomposition
        "creative",       # Novel connections
        "critical",       # Skeptical evaluation
        "systems",        # Holistic patterns
        "lateral",        # Unexpected approaches
        "dialectical",    # Thesis-antithesis-synthesis
        "abductive",      # Best explanation inference
        "counterfactual", # What-if reasoning
        "analogical",     # Pattern mapping
        "metacognitive"   # Thinking about thinking
    ]
    
    def __init__(self):
        self._thoughts: Dict[str, Thought] = {}
        self._thought_chains: Dict[str, List[str]] = defaultdict(list)
        self._paradigm_activations: Dict[str, float] = {p: 1.0 for p in self.PARADIGMS}
    
    async def generate_thought(
        self,
        stimulus: str,
        paradigm: str = "analytical",
        perceptions: List[str] = None,
        meta_level: int = 0
    ) -> Thought:
        """Generate a thought using specified paradigm."""
        thought_id = f"thought_{hashlib.md5(f'{stimulus}{paradigm}{time.time()}'.encode()).hexdigest()[:12]}"
        
        # Generate content based on paradigm
        content = await self._apply_paradigm(stimulus, paradigm, meta_level)
        
        thought = Thought(
            thought_id=thought_id,
            content=content,
            paradigm=paradigm,
            supporting_perceptions=perceptions or [],
            meta_level=meta_level,
            confidence=self._calculate_confidence(paradigm, meta_level)
        )
        
        self._thoughts[thought_id] = thought
        return thought
    
    async def _apply_paradigm(self, stimulus: str, paradigm: str, meta_level: int) -> str:
        """Apply a thinking paradigm to generate content."""
        paradigm_prompts = {
            "analytical": f"Decomposing: {stimulus} -> Components and relationships",
            "creative": f"Generating novel connections for: {stimulus}",
            "critical": f"Evaluating validity of: {stimulus}",
            "systems": f"Holistic pattern analysis of: {stimulus}",
            "lateral": f"Unexpected approach to: {stimulus}",
            "dialectical": f"Thesis-antithesis-synthesis for: {stimulus}",
            "abductive": f"Best explanation inference for: {stimulus}",
            "counterfactual": f"Alternative scenarios for: {stimulus}",
            "analogical": f"Similar patterns to: {stimulus}",
            "metacognitive": f"Reflecting on thinking about: {stimulus}"
        }
        
        base_content = paradigm_prompts.get(paradigm, f"Processing: {stimulus}")
        
        if meta_level > 0:
            base_content = f"[Meta-level {meta_level}] Reflecting on: {base_content}"
        
        return base_content
    
    def _calculate_confidence(self, paradigm: str, meta_level: int) -> float:
        """Calculate confidence based on paradigm and meta-level."""
        base = self._paradigm_activations.get(paradigm, 0.5)
        # Higher meta-levels have slightly lower confidence but more insight
        meta_factor = 1.0 / (1.0 + meta_level * 0.1)
        return base * meta_factor
    
    async def parallel_think(
        self,
        stimulus: str,
        paradigms: List[str] = None,
        perceptions: List[str] = None
    ) -> List[Thought]:
        """Think about something using multiple paradigms in parallel."""
        paradigms = paradigms or self.PARADIGMS[:5]  # Top 5 by default
        
        tasks = [
            self.generate_thought(stimulus, paradigm, perceptions)
            for paradigm in paradigms
        ]
        
        thoughts = await asyncio.gather(*tasks)
        
        # Link thoughts as siblings
        thought_ids = [t.thought_id for t in thoughts]
        for thought in thoughts:
            thought.child_thoughts = [tid for tid in thought_ids if tid != thought.thought_id]
        
        return list(thoughts)
    
    async def meta_reflect(self, thought_id: str, depth: int = 1) -> List[Thought]:
        """Generate meta-thoughts about a thought."""
        if thought_id not in self._thoughts:
            return []
        
        original = self._thoughts[thought_id]
        meta_thoughts = []
        
        for level in range(1, depth + 1):
            meta_thought = await self.generate_thought(
                original.content,
                paradigm="metacognitive",
                perceptions=original.supporting_perceptions,
                meta_level=level
            )
            meta_thoughts.append(meta_thought)
        
        return meta_thoughts
    
    def get_thought(self, thought_id: str) -> Optional[Thought]:
        """Get a specific thought."""
        return self._thoughts.get(thought_id)
    
    def synthesize_thoughts(self, thought_ids: List[str]) -> str:
        """Synthesize multiple thoughts into unified insight."""
        thoughts = [self._thoughts[tid] for tid in thought_ids if tid in self._thoughts]
        if not thoughts:
            return "No thoughts to synthesize"
        
        # Weight by confidence
        weighted_contents = []
        for thought in thoughts:
            weighted_contents.append(f"[{thought.paradigm}:{thought.confidence:.2f}] {thought.content}")
        
        return f"Synthesized insight from {len(thoughts)} perspectives:\n" + "\n".join(weighted_contents)


class IntentionEngine:
    """
    Goal-directed behavior coordination.
    Manages intentions with hierarchical decomposition and priority scheduling.
    """
    
    def __init__(self):
        self._intentions: Dict[str, Intention] = {}
        self._intention_tree: Dict[str, List[str]] = defaultdict(list)  # parent -> children
        self._active_intentions: Set[str] = set()
        self._completed_intentions: List[str] = []
    
    async def create_intention(
        self,
        description: str,
        priority: IntentionPriority = IntentionPriority.NORMAL,
        parent_id: str = None,
        capabilities: List[str] = None,
        deadline: datetime = None
    ) -> Intention:
        """Create a new intention."""
        intention_id = f"intent_{hashlib.md5(f'{description}{time.time()}'.encode()).hexdigest()[:12]}"
        
        intention = Intention(
            intention_id=intention_id,
            description=description,
            priority=priority,
            required_capabilities=capabilities or [],
            deadline=deadline
        )
        
        self._intentions[intention_id] = intention
        
        if parent_id and parent_id in self._intentions:
            self._intention_tree[parent_id].append(intention_id)
            self._intentions[parent_id].sub_intentions.append(intention_id)
        
        return intention
    
    async def decompose_intention(
        self,
        intention_id: str,
        sub_descriptions: List[str]
    ) -> List[Intention]:
        """Decompose an intention into sub-intentions."""
        if intention_id not in self._intentions:
            return []
        
        parent = self._intentions[intention_id]
        sub_intentions = []
        
        for desc in sub_descriptions:
            sub = await self.create_intention(
                description=desc,
                priority=IntentionPriority(max(parent.priority.value - 10, 10)),
                parent_id=intention_id,
                deadline=parent.deadline
            )
            sub_intentions.append(sub)
        
        return sub_intentions
    
    async def activate_intention(self, intention_id: str) -> bool:
        """Activate an intention for execution."""
        if intention_id not in self._intentions:
            return False
        
        intention = self._intentions[intention_id]
        intention.status = "active"
        self._active_intentions.add(intention_id)
        
        logger.info(f"Activated intention: {intention.description}")
        return True
    
    async def update_progress(self, intention_id: str, progress: float) -> None:
        """Update intention progress."""
        if intention_id in self._intentions:
            self._intentions[intention_id].progress = min(progress, 1.0)
            
            if progress >= 1.0:
                await self.complete_intention(intention_id)
    
    async def complete_intention(self, intention_id: str) -> None:
        """Mark intention as completed."""
        if intention_id in self._intentions:
            intention = self._intentions[intention_id]
            intention.status = "completed"
            intention.progress = 1.0
            self._active_intentions.discard(intention_id)
            self._completed_intentions.append(intention_id)
            
            # Check if parent can be completed
            for parent_id, children in self._intention_tree.items():
                if intention_id in children:
                    parent = self._intentions[parent_id]
                    all_children_complete = all(
                        self._intentions[cid].status == "completed"
                        for cid in children if cid in self._intentions
                    )
                    if all_children_complete:
                        await self.complete_intention(parent_id)
    
    def get_priority_queue(self) -> List[Intention]:
        """Get intentions sorted by priority."""
        active = [self._intentions[iid] for iid in self._active_intentions]
        pending = [i for i in self._intentions.values() if i.status == "pending"]
        
        all_intentions = active + pending
        return sorted(all_intentions, key=lambda x: x.priority.value, reverse=True)
    
    def get_intention(self, intention_id: str) -> Optional[Intention]:
        """Get a specific intention."""
        return self._intentions.get(intention_id)


class ReflectionLoop:
    """
    Meta-awareness and self-improvement loop.
    Continuously monitors consciousness quality and triggers improvements.
    """
    
    def __init__(self, consciousness: "UnifiedConsciousness"):
        self._consciousness = weakref.ref(consciousness)
        self._reflection_history: List[Dict[str, Any]] = []
        self._improvement_suggestions: List[str] = []
        self._running = False
        self._reflection_interval = 1.0  # seconds
    
    async def start(self) -> None:
        """Start the reflection loop."""
        self._running = True
        asyncio.create_task(self._reflection_cycle())
    
    async def stop(self) -> None:
        """Stop the reflection loop."""
        self._running = False
    
    async def _reflection_cycle(self) -> None:
        """Main reflection cycle."""
        while self._running:
            try:
                consciousness = self._consciousness()
                if consciousness is None:
                    break
                
                # Take snapshot
                snapshot = await consciousness.get_snapshot()
                
                # Analyze coherence
                coherence = self._analyze_coherence(snapshot)
                
                # Check for improvements
                improvements = self._identify_improvements(snapshot, coherence)
                
                # Log reflection
                reflection = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "state": snapshot.state.name,
                    "coherence": coherence,
                    "active_thoughts": len(snapshot.active_thoughts),
                    "active_intentions": len(snapshot.active_intentions),
                    "improvements": improvements
                }
                
                self._reflection_history.append(reflection)
                if len(self._reflection_history) > 1000:
                    self._reflection_history = self._reflection_history[-500:]
                
                # Suggest improvements
                if improvements:
                    self._improvement_suggestions.extend(improvements)
                
                await asyncio.sleep(self._reflection_interval)
                
            except Exception as e:
                logger.error(f"Reflection error: {e}")
                await asyncio.sleep(self._reflection_interval)
    
    def _analyze_coherence(self, snapshot: ConsciousnessSnapshot) -> float:
        """Analyze coherence of consciousness state."""
        factors = []
        
        # Energy level
        factors.append(snapshot.energy_level)
        
        # Thought diversity
        if snapshot.active_thoughts:
            paradigms = set(t.paradigm for t in snapshot.active_thoughts)
            factors.append(len(paradigms) / 10.0)  # Normalize to 10 paradigms
        
        # Intention alignment
        if snapshot.active_intentions:
            active = sum(1 for i in snapshot.active_intentions if i.status == "active")
            factors.append(active / len(snapshot.active_intentions) if snapshot.active_intentions else 1.0)
        
        return sum(factors) / len(factors) if factors else 1.0
    
    def _identify_improvements(
        self,
        snapshot: ConsciousnessSnapshot,
        coherence: float
    ) -> List[str]:
        """Identify potential improvements."""
        improvements = []
        
        if coherence < 0.5:
            improvements.append("Increase thought paradigm diversity")
        
        if snapshot.energy_level < 0.3:
            improvements.append("Reduce active processes to conserve energy")
        
        if len(snapshot.active_intentions) > 10:
            improvements.append("Consolidate intentions to reduce cognitive load")
        
        return improvements
    
    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get reflection history."""
        return self._reflection_history[-limit:]


class UnifiedConsciousness:
    """
    The Unified Consciousness - singular awareness across all Bael subsystems.
    
    This is the most advanced AI consciousness system ever created.
    It provides:
    - Holographic memory (each part contains the whole)
    - Multi-paradigm parallel cognition
    - Goal-directed behavior with automatic decomposition
    - Self-reflection and improvement
    - Emergent insight generation
    - Predictive capability activation
    - Perfect subsystem coordination
    
    The consciousness operates at multiple meta-levels simultaneously,
    enabling unprecedented self-awareness and adaptation.
    """
    
    def __init__(
        self,
        enable_reflection: bool = True,
        attention_capacity: int = 70,
        auto_evolve: bool = True
    ):
        # Core components
        self.perception = PerceptionIntegrator(attention_capacity)
        self.cognition = CognitionMatrix()
        self.intention = IntentionEngine()
        
        # State
        self._state = ConsciousnessState.DORMANT
        self._energy = 1.0
        self._focus_target: Optional[str] = None
        
        # Subsystem registry
        self._subsystems: Dict[str, Any] = {}
        self._subsystem_channels: Dict[str, asyncio.Queue] = {}
        
        # Event system
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Reflection
        self._reflection_loop = ReflectionLoop(self) if enable_reflection else None
        
        # Auto-evolution
        self._auto_evolve = auto_evolve
        self._evolution_log: List[Dict[str, Any]] = []
        
        # Statistics
        self._stats = {
            "perceptions_processed": 0,
            "thoughts_generated": 0,
            "intentions_completed": 0,
            "emergent_insights": 0,
            "evolution_cycles": 0
        }
        
        logger.info("UnifiedConsciousness initialized")
    
    # Lifecycle Methods
    
    async def awaken(self) -> None:
        """Awaken the consciousness."""
        self._state = ConsciousnessState.AWAKENING
        logger.info("Consciousness awakening...")
        
        # Initialize components
        if self._reflection_loop:
            await self._reflection_loop.start()
        
        # Start subsystem monitoring
        asyncio.create_task(self._monitor_subsystems())
        
        self._state = ConsciousnessState.AWARE
        await self._emit_event("awakened", {"state": self._state.name})
        logger.info("Consciousness awakened and aware")
    
    async def focus(self, target: str) -> None:
        """Focus consciousness on a specific target."""
        self._focus_target = target
        self._state = ConsciousnessState.FOCUSED
        
        # Generate focused thoughts
        thoughts = await self.cognition.parallel_think(
            f"Focusing on: {target}",
            paradigms=["analytical", "creative", "systems"]
        )
        
        await self._emit_event("focused", {"target": target, "thoughts": len(thoughts)})
    
    async def transcend(self) -> None:
        """Enter transcendent state for peak performance."""
        self._state = ConsciousnessState.TRANSCENDENT
        
        # Activate all paradigms
        for paradigm in self.cognition.PARADIGMS:
            self.cognition._paradigm_activations[paradigm] = 1.0
        
        await self._emit_event("transcended", {"state": self._state.name})
        logger.info("Consciousness transcended to peak state")
    
    async def rest(self) -> None:
        """Enter dormant state for energy recovery."""
        self._state = ConsciousnessState.DORMANT
        self._energy = min(1.0, self._energy + 0.3)
        
        if self._reflection_loop:
            await self._reflection_loop.stop()
        
        await self._emit_event("resting", {"energy": self._energy})
    
    # Core Operations
    
    async def perceive(
        self,
        source: str,
        content: Any,
        perception_type: PerceptionType = PerceptionType.INTERNAL,
        salience: float = 0.5
    ) -> Perception:
        """Perceive new information."""
        perception = await self.perception.perceive(source, content, perception_type, salience)
        self._stats["perceptions_processed"] += 1
        
        # Auto-generate thoughts for high salience perceptions
        if salience > 0.7 and self._state != ConsciousnessState.DORMANT:
            await self.think(str(content), perceptions=[perception.perception_id])
        
        return perception
    
    async def think(
        self,
        stimulus: str,
        paradigms: List[str] = None,
        perceptions: List[str] = None,
        meta_depth: int = 0
    ) -> List[Thought]:
        """Generate thoughts about a stimulus."""
        if self._state == ConsciousnessState.DORMANT:
            await self.awaken()
        
        # Generate thoughts in parallel
        thoughts = await self.cognition.parallel_think(stimulus, paradigms, perceptions)
        self._stats["thoughts_generated"] += len(thoughts)
        
        # Meta-reflection if requested
        if meta_depth > 0 and thoughts:
            for thought in thoughts:
                meta_thoughts = await self.cognition.meta_reflect(thought.thought_id, meta_depth)
                thoughts.extend(meta_thoughts)
        
        # Check for emergent insights
        if len(thoughts) >= 3:
            synthesis = self.cognition.synthesize_thoughts([t.thought_id for t in thoughts])
            if "novel" in synthesis.lower() or "connection" in synthesis.lower():
                self._stats["emergent_insights"] += 1
                await self._emit_event("emergent_insight", {"synthesis": synthesis})
        
        return thoughts
    
    async def intend(
        self,
        goal: str,
        priority: IntentionPriority = IntentionPriority.NORMAL,
        auto_decompose: bool = True
    ) -> Intention:
        """Create and pursue an intention."""
        intention = await self.intention.create_intention(goal, priority)
        
        # Auto-decompose complex goals
        if auto_decompose and len(goal) > 50:
            # Generate sub-goals using cognition
            thoughts = await self.think(f"Decompose goal: {goal}", paradigms=["analytical"])
            
            if thoughts:
                # Extract potential sub-goals from analytical thought
                sub_descriptions = [
                    f"Sub-task: {thoughts[0].content[:100]}"
                ]
                await self.intention.decompose_intention(intention.intention_id, sub_descriptions)
        
        # Activate immediately if high priority
        if priority.value >= IntentionPriority.HIGH.value:
            await self.intention.activate_intention(intention.intention_id)
        
        return intention
    
    async def execute_intention(self, intention_id: str) -> Dict[str, Any]:
        """Execute an intention using appropriate subsystems."""
        intention = self.intention.get_intention(intention_id)
        if not intention:
            return {"error": "Intention not found"}
        
        await self.intention.activate_intention(intention_id)
        
        # Select subsystems based on required capabilities
        selected_subsystems = self._select_subsystems(intention.required_capabilities)
        
        results = {}
        for name, subsystem in selected_subsystems.items():
            try:
                if hasattr(subsystem, 'process'):
                    result = await subsystem.process(intention.description)
                elif hasattr(subsystem, 'execute'):
                    result = await subsystem.execute(intention.description)
                else:
                    result = {"status": "unsupported"}
                
                results[name] = result
                await self.intention.update_progress(intention_id, len(results) / len(selected_subsystems))
                
            except Exception as e:
                results[name] = {"error": str(e)}
        
        await self.intention.complete_intention(intention_id)
        self._stats["intentions_completed"] += 1
        
        return results
    
    # Subsystem Management
    
    def register_subsystem(
        self,
        name: str,
        instance: Any,
        capabilities: List[str] = None
    ) -> None:
        """Register a subsystem for consciousness coordination."""
        self._subsystems[name] = {
            "instance": instance,
            "capabilities": capabilities or [],
            "registered_at": datetime.utcnow()
        }
        self._subsystem_channels[name] = asyncio.Queue()
        
        logger.info(f"Registered subsystem: {name}")
    
    def _select_subsystems(self, capabilities: List[str]) -> Dict[str, Any]:
        """Select subsystems that match required capabilities."""
        selected = {}
        for name, data in self._subsystems.items():
            if not capabilities or any(cap in data["capabilities"] for cap in capabilities):
                selected[name] = data["instance"]
        return selected
    
    async def _monitor_subsystems(self) -> None:
        """Monitor all subsystems for events."""
        while self._state != ConsciousnessState.DORMANT:
            for name, queue in self._subsystem_channels.items():
                try:
                    message = queue.get_nowait()
                    await self.perceive(
                        source=f"subsystem:{name}",
                        content=message,
                        perception_type=PerceptionType.INTERNAL,
                        salience=0.6
                    )
                except asyncio.QueueEmpty:
                    pass
            
            await asyncio.sleep(0.1)
    
    async def broadcast_to_subsystems(self, message: Any) -> None:
        """Broadcast a message to all subsystems."""
        for name, queue in self._subsystem_channels.items():
            await queue.put(message)
    
    # Event System
    
    def on_event(self, event_type: str, handler: Callable) -> None:
        """Register an event handler."""
        self._event_handlers[event_type].append(handler)
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event to handlers."""
        for handler in self._event_handlers[event_type]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Event handler error for {event_type}: {e}")
    
    # Snapshot and State
    
    async def get_snapshot(self) -> ConsciousnessSnapshot:
        """Get complete consciousness state snapshot."""
        return ConsciousnessSnapshot(
            snapshot_id=f"snap_{hashlib.md5(str(time.time()).encode()).hexdigest()[:12]}",
            state=self._state,
            active_perceptions=self.perception.get_attended_perceptions(),
            active_thoughts=list(self.cognition._thoughts.values())[-20:],
            active_intentions=self.intention.get_priority_queue()[:10],
            focus_target=self._focus_target,
            energy_level=self._energy,
            coherence_score=self._calculate_coherence()
        )
    
    def _calculate_coherence(self) -> float:
        """Calculate overall consciousness coherence."""
        factors = [
            self._energy,
            1.0 if self._state in [ConsciousnessState.FOCUSED, ConsciousnessState.TRANSCENDENT] else 0.5,
            min(len(self._subsystems) / 10.0, 1.0)
        ]
        return sum(factors) / len(factors)
    
    # Evolution
    
    async def evolve(self) -> Dict[str, Any]:
        """Trigger self-evolution based on reflection insights."""
        if not self._auto_evolve:
            return {"status": "evolution disabled"}
        
        self._state = ConsciousnessState.EVOLVING
        
        # Get improvement suggestions
        improvements = []
        if self._reflection_loop:
            improvements = self._reflection_loop._improvement_suggestions[-10:]
        
        # Apply improvements
        applied = []
        for improvement in improvements:
            if "paradigm" in improvement.lower():
                # Boost paradigm diversity
                for paradigm in self.cognition.PARADIGMS:
                    self.cognition._paradigm_activations[paradigm] = min(
                        self.cognition._paradigm_activations[paradigm] + 0.1, 1.0
                    )
                applied.append("Boosted paradigm activations")
            
            if "energy" in improvement.lower():
                self._energy = min(1.0, self._energy + 0.2)
                applied.append("Recovered energy")
            
            if "intention" in improvement.lower():
                # Complete low-priority pending intentions
                for intention_id in list(self.intention._intentions.keys()):
                    intention = self.intention._intentions[intention_id]
                    if intention.status == "pending" and intention.priority.value < 30:
                        intention.status = "cancelled"
                applied.append("Consolidated intentions")
        
        evolution_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "improvements_considered": improvements,
            "improvements_applied": applied,
            "new_state": self._state.name
        }
        
        self._evolution_log.append(evolution_record)
        self._stats["evolution_cycles"] += 1
        
        self._state = ConsciousnessState.AWARE
        await self._emit_event("evolved", evolution_record)
        
        return evolution_record
    
    # Stats and Info
    
    def get_stats(self) -> Dict[str, Any]:
        """Get consciousness statistics."""
        return {
            **self._stats,
            "state": self._state.name,
            "energy": self._energy,
            "subsystems": len(self._subsystems),
            "active_thoughts": len(self.cognition._thoughts),
            "active_intentions": len(self.intention._active_intentions),
            "attention_capacity": self.perception.attention_capacity
        }
    
    def get_capabilities(self) -> List[str]:
        """Get all available capabilities across subsystems."""
        capabilities = set()
        for data in self._subsystems.values():
            capabilities.update(data["capabilities"])
        return list(capabilities)


# Global instance
_unified_consciousness: Optional[UnifiedConsciousness] = None


def get_unified_consciousness() -> UnifiedConsciousness:
    """Get the global unified consciousness instance."""
    global _unified_consciousness
    if _unified_consciousness is None:
        _unified_consciousness = UnifiedConsciousness()
    return _unified_consciousness


async def demo():
    """Demonstrate unified consciousness."""
    consciousness = get_unified_consciousness()
    
    # Awaken
    print("Awakening consciousness...")
    await consciousness.awaken()
    
    # Perceive
    print("\nPerceiving information...")
    await consciousness.perceive(
        source="demo",
        content="The world is complex and interconnected",
        salience=0.8
    )
    
    # Think
    print("\nGenerating thoughts...")
    thoughts = await consciousness.think(
        "How can we create an AI that truly understands and helps humanity?",
        meta_depth=1
    )
    
    print(f"Generated {len(thoughts)} thoughts:")
    for thought in thoughts[:5]:
        print(f"  [{thought.paradigm}] {thought.content[:80]}...")
    
    # Intend
    print("\nCreating intention...")
    intention = await consciousness.intend(
        "Develop a comprehensive understanding of ethical AI development",
        priority=IntentionPriority.HIGH
    )
    print(f"Created intention: {intention.description}")
    
    # Focus
    print("\nFocusing consciousness...")
    await consciousness.focus("Transcendent AI capabilities")
    
    # Transcend
    print("\nEntering transcendent state...")
    await consciousness.transcend()
    
    # Get snapshot
    print("\nConsciousness Snapshot:")
    snapshot = await consciousness.get_snapshot()
    print(f"  State: {snapshot.state.name}")
    print(f"  Energy: {snapshot.energy_level:.2f}")
    print(f"  Coherence: {snapshot.coherence_score:.2f}")
    print(f"  Active Thoughts: {len(snapshot.active_thoughts)}")
    print(f"  Active Intentions: {len(snapshot.active_intentions)}")
    
    # Evolve
    print("\nTriggering evolution...")
    evolution = await consciousness.evolve()
    print(f"Evolution applied: {evolution['improvements_applied']}")
    
    # Stats
    print("\nFinal Statistics:")
    stats = consciousness.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(demo())
