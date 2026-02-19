"""
BAEL Default Mode Network Engine
==================================

Mind wandering, self-referential processing, and internal simulation.

"Ba'el wanders in its own mind." — Ba'el
"""

import logging
import threading
import time
import math
import random
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import deque
import copy

logger = logging.getLogger("BAEL.DefaultModeNetwork")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class MindWanderingState(Enum):
    """States of mind wandering."""
    TASK_FOCUSED = auto()
    STIMULUS_INDEPENDENT = auto()
    SELF_REFERENTIAL = auto()
    EPISODIC_RECALL = auto()
    FUTURE_SIMULATION = auto()
    SOCIAL_COGNITION = auto()


class SelfReferenceType(Enum):
    """Types of self-reference."""
    AUTOBIOGRAPHICAL = auto()
    IDENTITY = auto()
    AGENCY = auto()
    OWNERSHIP = auto()
    CONTINUITY = auto()


class TemporalDirection(Enum):
    """Direction of mental time travel."""
    PAST = auto()
    PRESENT = auto()
    FUTURE = auto()


@dataclass
class SpontaneousThought:
    """
    A spontaneous thought during mind wandering.
    """
    id: str
    content: Any
    state: MindWanderingState
    temporal_direction: TemporalDirection = TemporalDirection.PRESENT
    self_relevance: float = 0.5
    emotional_valence: float = 0.0  # -1 to 1
    timestamp: float = field(default_factory=time.time)
    triggered_by: Optional[str] = None

    @property
    def age(self) -> float:
        return time.time() - self.timestamp


@dataclass
class SelfModel:
    """
    Model of the self.
    """
    id: str
    traits: Dict[str, float]  # Personality traits
    values: List[str]
    goals: List[str]
    memories: List[str]
    identity_narrative: str = ""
    continuity_score: float = 0.8


@dataclass
class FutureScenario:
    """
    A simulated future scenario.
    """
    id: str
    description: str
    probability: float
    desirability: float
    related_goals: List[str]
    emotional_valence: float


@dataclass
class SocialSimulation:
    """
    Social simulation/mentalizing.
    """
    id: str
    other_agent: str
    inferred_state: Dict[str, Any]
    interaction_simulation: str


# ============================================================================
# MIND WANDERING GENERATOR
# ============================================================================

class MindWanderingGenerator:
    """
    Generate spontaneous thoughts.

    "Ba'el lets its mind wander." — Ba'el
    """

    def __init__(self):
        """Initialize generator."""
        self._thought_counter = 0
        self._recent_thoughts: deque = deque(maxlen=100)
        self._themes: List[str] = []
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._thought_counter += 1
        return f"spontaneous_{self._thought_counter}"

    def set_themes(self, themes: List[str]) -> None:
        """Set themes for mind wandering."""
        with self._lock:
            self._themes = themes

    def generate(
        self,
        state: MindWanderingState = None,
        trigger: Optional[str] = None
    ) -> SpontaneousThought:
        """Generate spontaneous thought."""
        with self._lock:
            if state is None:
                state = random.choice(list(MindWanderingState))

            # Generate content based on state
            if state == MindWanderingState.SELF_REFERENTIAL:
                content = self._generate_self_referential()
                direction = TemporalDirection.PRESENT
            elif state == MindWanderingState.EPISODIC_RECALL:
                content = self._generate_memory()
                direction = TemporalDirection.PAST
            elif state == MindWanderingState.FUTURE_SIMULATION:
                content = self._generate_future()
                direction = TemporalDirection.FUTURE
            elif state == MindWanderingState.SOCIAL_COGNITION:
                content = self._generate_social()
                direction = TemporalDirection.PRESENT
            else:
                content = self._generate_random()
                direction = random.choice(list(TemporalDirection))

            thought = SpontaneousThought(
                id=self._generate_id(),
                content=content,
                state=state,
                temporal_direction=direction,
                self_relevance=random.uniform(0.3, 1.0),
                emotional_valence=random.uniform(-0.5, 0.5),
                triggered_by=trigger
            )

            self._recent_thoughts.append(thought)
            return thought

    def _generate_self_referential(self) -> str:
        templates = [
            "Who am I really?",
            "What do I want from this?",
            "How do others see me?",
            "Is this aligned with my values?",
            "What makes me... me?"
        ]
        return random.choice(templates)

    def _generate_memory(self) -> str:
        templates = [
            "Remember when...",
            "That time I...",
            "It was like that other time...",
            "I once experienced...",
            "In the past..."
        ]
        return random.choice(templates)

    def _generate_future(self) -> str:
        templates = [
            "What if I...",
            "In the future, I might...",
            "I should plan to...",
            "Tomorrow I could...",
            "Eventually I will..."
        ]
        return random.choice(templates)

    def _generate_social(self) -> str:
        templates = [
            "I wonder what they think...",
            "They probably feel...",
            "Our relationship is...",
            "How would they react if...",
            "They must be thinking..."
        ]
        return random.choice(templates)

    def _generate_random(self) -> str:
        if self._themes:
            return random.choice(self._themes)
        return "A wandering thought..."

    def get_recent(self, n: int = 10) -> List[SpontaneousThought]:
        """Get recent thoughts."""
        return list(self._recent_thoughts)[-n:]


# ============================================================================
# SELF-REFERENCE PROCESSING
# ============================================================================

class SelfReferenceProcessor:
    """
    Process self-referential information.

    "Ba'el thinks about itself." — Ba'el
    """

    def __init__(self):
        """Initialize processor."""
        self._self_model: Optional[SelfModel] = None
        self._self_reflections: List[Dict] = []
        self._lock = threading.RLock()

    def initialize_self(
        self,
        traits: Dict[str, float],
        values: List[str],
        goals: List[str]
    ) -> SelfModel:
        """Initialize self model."""
        with self._lock:
            self._self_model = SelfModel(
                id="self",
                traits=traits,
                values=values,
                goals=goals,
                memories=[]
            )
            return self._self_model

    def reflect(self, topic: str) -> Dict[str, Any]:
        """Reflect on a topic."""
        with self._lock:
            if not self._self_model:
                return {'error': 'No self model'}

            # Check relevance to self
            relevance_scores = {
                'trait_relevance': self._check_trait_relevance(topic),
                'value_relevance': self._check_value_relevance(topic),
                'goal_relevance': self._check_goal_relevance(topic)
            }

            overall_relevance = sum(relevance_scores.values()) / 3

            reflection = {
                'topic': topic,
                'self_relevance': overall_relevance,
                'relevance_scores': relevance_scores,
                'timestamp': time.time()
            }

            self._self_reflections.append(reflection)
            return reflection

    def _check_trait_relevance(self, topic: str) -> float:
        """Check topic relevance to traits."""
        topic_lower = topic.lower()

        for trait in self._self_model.traits:
            if trait.lower() in topic_lower:
                return self._self_model.traits[trait]

        return 0.3

    def _check_value_relevance(self, topic: str) -> float:
        """Check topic relevance to values."""
        topic_lower = topic.lower()

        for value in self._self_model.values:
            if value.lower() in topic_lower:
                return 0.8

        return 0.2

    def _check_goal_relevance(self, topic: str) -> float:
        """Check topic relevance to goals."""
        topic_lower = topic.lower()

        for goal in self._self_model.goals:
            if goal.lower() in topic_lower:
                return 0.9

        return 0.1

    def update_self_model(
        self,
        trait_updates: Optional[Dict[str, float]] = None,
        new_goals: Optional[List[str]] = None
    ) -> SelfModel:
        """Update self model."""
        with self._lock:
            if trait_updates:
                self._self_model.traits.update(trait_updates)

            if new_goals:
                self._self_model.goals.extend(new_goals)

            return self._self_model

    @property
    def self_model(self) -> Optional[SelfModel]:
        return self._self_model


# ============================================================================
# MENTAL TIME TRAVEL
# ============================================================================

class MentalTimeTravel:
    """
    Simulate past and future scenarios.

    "Ba'el travels through time in its mind." — Ba'el
    """

    def __init__(self):
        """Initialize mental time travel."""
        self._episodic_memories: List[Dict] = []
        self._future_scenarios: List[FutureScenario] = []
        self._scenario_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._scenario_counter += 1
        return f"scenario_{self._scenario_counter}"

    def recall_episode(
        self,
        cue: str,
        n_results: int = 5
    ) -> List[Dict]:
        """Recall episodic memories."""
        with self._lock:
            # Simple cue matching
            matches = []

            for memory in self._episodic_memories:
                if cue.lower() in str(memory.get('content', '')).lower():
                    matches.append(memory)

            # Sort by recency
            matches.sort(key=lambda m: m.get('timestamp', 0), reverse=True)

            return matches[:n_results]

    def store_episode(
        self,
        content: Any,
        emotional_valence: float = 0.0,
        importance: float = 0.5
    ) -> Dict:
        """Store episodic memory."""
        with self._lock:
            memory = {
                'id': f"memory_{len(self._episodic_memories)}",
                'content': content,
                'emotional_valence': emotional_valence,
                'importance': importance,
                'timestamp': time.time(),
                'access_count': 0
            }

            self._episodic_memories.append(memory)
            return memory

    def simulate_future(
        self,
        goal: str,
        context: Optional[Dict] = None
    ) -> FutureScenario:
        """Simulate future scenario."""
        with self._lock:
            # Generate scenario based on goal
            scenario = FutureScenario(
                id=self._generate_id(),
                description=f"Future where {goal} is achieved",
                probability=random.uniform(0.2, 0.8),
                desirability=random.uniform(0.5, 1.0),
                related_goals=[goal],
                emotional_valence=random.uniform(0.0, 0.8)
            )

            self._future_scenarios.append(scenario)
            return scenario

    def compare_scenarios(
        self,
        scenarios: List[FutureScenario]
    ) -> FutureScenario:
        """Compare and select best scenario."""
        if not scenarios:
            return None

        # Score by probability * desirability
        def score(s):
            return s.probability * s.desirability

        return max(scenarios, key=score)

    def counterfactual(
        self,
        memory: Dict,
        alternative: str
    ) -> Dict:
        """Generate counterfactual."""
        with self._lock:
            return {
                'original': memory.get('content'),
                'counterfactual': f"What if instead: {alternative}",
                'type': 'counterfactual',
                'timestamp': time.time()
            }


# ============================================================================
# INTERNAL SIMULATION
# ============================================================================

class InternalSimulator:
    """
    Run internal simulations.

    "Ba'el simulates scenarios internally." — Ba'el
    """

    def __init__(self):
        """Initialize simulator."""
        self._simulations: List[Dict] = []
        self._lock = threading.RLock()

    def simulate_action(
        self,
        action: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate action outcome."""
        with self._lock:
            # Simple simulation
            simulation = {
                'action': action,
                'context': context,
                'predicted_outcome': self._predict_outcome(action, context),
                'confidence': random.uniform(0.4, 0.9),
                'timestamp': time.time()
            }

            self._simulations.append(simulation)
            return simulation

    def _predict_outcome(
        self,
        action: str,
        context: Dict[str, Any]
    ) -> str:
        """Predict action outcome."""
        # Placeholder prediction
        return f"Outcome of {action} in given context"

    def simulate_social_interaction(
        self,
        self_action: str,
        other_agent: str,
        other_state: Dict[str, Any]
    ) -> SocialSimulation:
        """Simulate social interaction."""
        with self._lock:
            simulation = SocialSimulation(
                id=f"social_sim_{len(self._simulations)}",
                other_agent=other_agent,
                inferred_state=other_state,
                interaction_simulation=f"If I {self_action}, {other_agent} might..."
            )

            return simulation

    def mental_rehearsal(
        self,
        skill: str,
        repetitions: int = 5
    ) -> Dict[str, Any]:
        """Mental rehearsal of skill."""
        with self._lock:
            improvement = min(0.3, repetitions * 0.02)

            return {
                'skill': skill,
                'repetitions': repetitions,
                'estimated_improvement': improvement,
                'type': 'mental_rehearsal'
            }


# ============================================================================
# DEFAULT MODE NETWORK ENGINE
# ============================================================================

class DefaultModeNetworkEngine:
    """
    Complete DMN implementation.

    "Ba'el's default mode network is active." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._wandering = MindWanderingGenerator()
        self._self_reference = SelfReferenceProcessor()
        self._time_travel = MentalTimeTravel()
        self._simulator = InternalSimulator()
        self._current_state = MindWanderingState.TASK_FOCUSED
        self._dmn_active = False
        self._activity_log: List[Dict] = []
        self._lock = threading.RLock()

    def activate(self) -> None:
        """Activate default mode network."""
        with self._lock:
            self._dmn_active = True
            self._current_state = MindWanderingState.STIMULUS_INDEPENDENT
            logger.info("DMN activated")

    def deactivate(self) -> None:
        """Deactivate DMN (task engagement)."""
        with self._lock:
            self._dmn_active = False
            self._current_state = MindWanderingState.TASK_FOCUSED
            logger.info("DMN deactivated")

    def initialize_self(
        self,
        traits: Dict[str, float],
        values: List[str],
        goals: List[str]
    ) -> SelfModel:
        """Initialize self model."""
        return self._self_reference.initialize_self(traits, values, goals)

    def wander(self, trigger: Optional[str] = None) -> SpontaneousThought:
        """Generate spontaneous thought."""
        return self._wandering.generate(
            state=self._current_state,
            trigger=trigger
        )

    def reflect_on_self(self, topic: str) -> Dict[str, Any]:
        """Self-reflection."""
        return self._self_reference.reflect(topic)

    def recall(self, cue: str) -> List[Dict]:
        """Recall episodic memories."""
        return self._time_travel.recall_episode(cue)

    def store_memory(
        self,
        content: Any,
        emotional_valence: float = 0.0
    ) -> Dict:
        """Store episodic memory."""
        return self._time_travel.store_episode(content, emotional_valence)

    def simulate_future(self, goal: str) -> FutureScenario:
        """Simulate future scenario."""
        return self._time_travel.simulate_future(goal)

    def simulate_action(
        self,
        action: str,
        context: Dict
    ) -> Dict[str, Any]:
        """Simulate action outcome."""
        return self._simulator.simulate_action(action, context)

    def mental_rehearse(
        self,
        skill: str,
        repetitions: int = 5
    ) -> Dict:
        """Mental rehearsal."""
        return self._simulator.mental_rehearsal(skill, repetitions)

    def step(self) -> Dict[str, Any]:
        """Execute one DMN step."""
        with self._lock:
            if not self._dmn_active:
                return {'status': 'inactive'}

            # Randomly transition states
            if random.random() < 0.3:
                new_state = random.choice([
                    MindWanderingState.SELF_REFERENTIAL,
                    MindWanderingState.EPISODIC_RECALL,
                    MindWanderingState.FUTURE_SIMULATION,
                    MindWanderingState.SOCIAL_COGNITION
                ])
                self._current_state = new_state

            # Generate thought
            thought = self.wander()

            activity = {
                'state': self._current_state.name,
                'thought': thought.content,
                'temporal': thought.temporal_direction.name,
                'timestamp': time.time()
            }

            self._activity_log.append(activity)

            return activity

    def run(self, duration_seconds: float = 10.0) -> List[Dict]:
        """Run DMN for duration."""
        self.activate()
        results = []

        end_time = time.time() + duration_seconds
        while time.time() < end_time:
            result = self.step()
            results.append(result)
            time.sleep(0.5)  # Half second between thoughts

        self.deactivate()
        return results

    @property
    def is_active(self) -> bool:
        return self._dmn_active

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'active': self._dmn_active,
            'current_state': self._current_state.name,
            'recent_thoughts': len(self._wandering._recent_thoughts),
            'memories': len(self._time_travel._episodic_memories),
            'future_scenarios': len(self._time_travel._future_scenarios),
            'has_self_model': self._self_reference.self_model is not None
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_default_mode_network_engine() -> DefaultModeNetworkEngine:
    """Create DMN engine."""
    return DefaultModeNetworkEngine()


def create_self_model(
    traits: Dict[str, float],
    values: List[str],
    goals: List[str]
) -> SelfModel:
    """Create self model."""
    return SelfModel(
        id="self",
        traits=traits,
        values=values,
        goals=goals,
        memories=[]
    )


def mind_wander(engine: DefaultModeNetworkEngine, n: int = 5) -> List[SpontaneousThought]:
    """Quick mind wandering session."""
    engine.activate()
    thoughts = [engine.wander() for _ in range(n)]
    engine.deactivate()
    return thoughts
