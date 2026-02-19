"""
BAEL Theory of Mind Engine
===========================

Reasoning about mental states of others.
Understanding beliefs, desires, and intentions.

"Ba'el understands what others think." — Ba'el
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
from collections import defaultdict
import copy

logger = logging.getLogger("BAEL.TheoryOfMind")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class MentalStateType(Enum):
    """Types of mental states."""
    BELIEF = auto()
    DESIRE = auto()
    INTENTION = auto()
    KNOWLEDGE = auto()
    EMOTION = auto()
    GOAL = auto()
    PREFERENCE = auto()
    PERCEPTION = auto()


class BeliefLevel(Enum):
    """Levels of belief attribution."""
    FIRST_ORDER = 1    # I believe X
    SECOND_ORDER = 2   # I believe you believe X
    THIRD_ORDER = 3    # I believe you believe I believe X
    HIGHER = 4         # Even deeper


class AgentType(Enum):
    """Types of agents."""
    SELF = auto()
    HUMAN = auto()
    AI = auto()
    GROUP = auto()
    UNKNOWN = auto()


@dataclass
class MentalState:
    """
    A mental state attributed to an agent.
    """
    id: str
    agent_id: str
    state_type: MentalStateType
    content: Any
    confidence: float = 0.7
    timestamp: float = field(default_factory=time.time)
    source: str = "inference"  # "inference", "observation", "communication"
    target_agent: Optional[str] = None  # For second-order beliefs

    @property
    def age(self) -> float:
        return time.time() - self.timestamp


@dataclass
class Agent:
    """
    Representation of an agent.
    """
    id: str
    name: str
    agent_type: AgentType
    mental_states: Dict[str, MentalState] = field(default_factory=dict)
    traits: Dict[str, float] = field(default_factory=dict)  # Personality traits
    relationship: float = 0.5  # Relationship with self (-1 to 1)

    def add_state(self, state: MentalState) -> None:
        self.mental_states[state.id] = state

    def get_beliefs(self) -> List[MentalState]:
        return [s for s in self.mental_states.values() if s.state_type == MentalStateType.BELIEF]

    def get_desires(self) -> List[MentalState]:
        return [s for s in self.mental_states.values() if s.state_type == MentalStateType.DESIRE]

    def get_intentions(self) -> List[MentalState]:
        return [s for s in self.mental_states.values() if s.state_type == MentalStateType.INTENTION]


@dataclass
class Prediction:
    """
    Prediction about agent behavior.
    """
    agent_id: str
    predicted_action: str
    confidence: float
    reasoning: List[str]
    based_on_states: List[str]


# ============================================================================
# BELIEF TRACKER
# ============================================================================

class BeliefTracker:
    """
    Track and update beliefs about agents.

    "Ba'el tracks what others believe." — Ba'el
    """

    def __init__(self):
        """Initialize belief tracker."""
        self._beliefs: Dict[str, Dict[str, MentalState]] = defaultdict(dict)  # agent -> {belief_id -> state}
        self._belief_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._belief_counter += 1
        return f"belief_{self._belief_counter}"

    def attribute_belief(
        self,
        agent_id: str,
        content: Any,
        confidence: float = 0.7,
        source: str = "inference"
    ) -> MentalState:
        """Attribute belief to agent."""
        with self._lock:
            belief = MentalState(
                id=self._generate_id(),
                agent_id=agent_id,
                state_type=MentalStateType.BELIEF,
                content=content,
                confidence=confidence,
                source=source
            )

            self._beliefs[agent_id][belief.id] = belief
            return belief

    def attribute_second_order(
        self,
        agent_id: str,
        target_agent: str,
        believed_content: Any,
        confidence: float = 0.6
    ) -> MentalState:
        """Attribute second-order belief (agent believes target believes X)."""
        with self._lock:
            content = f"{target_agent} believes: {believed_content}"

            belief = MentalState(
                id=self._generate_id(),
                agent_id=agent_id,
                state_type=MentalStateType.BELIEF,
                content=content,
                confidence=confidence,
                target_agent=target_agent,
                source="inference"
            )

            self._beliefs[agent_id][belief.id] = belief
            return belief

    def update_belief(
        self,
        agent_id: str,
        belief_id: str,
        new_content: Any = None,
        new_confidence: float = None
    ) -> Optional[MentalState]:
        """Update existing belief."""
        with self._lock:
            if agent_id not in self._beliefs:
                return None
            if belief_id not in self._beliefs[agent_id]:
                return None

            belief = self._beliefs[agent_id][belief_id]

            if new_content is not None:
                belief.content = new_content
            if new_confidence is not None:
                belief.confidence = new_confidence

            belief.timestamp = time.time()

            return belief

    def get_beliefs(self, agent_id: str) -> List[MentalState]:
        """Get all beliefs for agent."""
        with self._lock:
            if agent_id not in self._beliefs:
                return []
            return list(self._beliefs[agent_id].values())

    def belief_about(self, agent_id: str, topic: str) -> Optional[MentalState]:
        """Get belief about specific topic."""
        with self._lock:
            for belief in self._beliefs.get(agent_id, {}).values():
                if topic.lower() in str(belief.content).lower():
                    return belief
            return None

    def contradiction_check(self, agent_id: str) -> List[Tuple[MentalState, MentalState]]:
        """Check for contradictory beliefs."""
        with self._lock:
            beliefs = self.get_beliefs(agent_id)
            contradictions = []

            # Simple check: opposite content
            for i, b1 in enumerate(beliefs):
                for b2 in beliefs[i+1:]:
                    # Check for "not X" vs "X"
                    c1 = str(b1.content).lower()
                    c2 = str(b2.content).lower()

                    if f"not {c1}" == c2 or f"not {c2}" == c1:
                        contradictions.append((b1, b2))

            return contradictions


# ============================================================================
# DESIRE MODEL
# ============================================================================

class DesireModel:
    """
    Model of agent desires and goals.

    "Ba'el understands what others want." — Ba'el
    """

    def __init__(self):
        """Initialize desire model."""
        self._desires: Dict[str, Dict[str, MentalState]] = defaultdict(dict)
        self._desire_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._desire_counter += 1
        return f"desire_{self._desire_counter}"

    def attribute_desire(
        self,
        agent_id: str,
        content: Any,
        intensity: float = 0.5,
        source: str = "inference"
    ) -> MentalState:
        """Attribute desire to agent."""
        with self._lock:
            desire = MentalState(
                id=self._generate_id(),
                agent_id=agent_id,
                state_type=MentalStateType.DESIRE,
                content=content,
                confidence=intensity,
                source=source
            )

            self._desires[agent_id][desire.id] = desire
            return desire

    def attribute_goal(
        self,
        agent_id: str,
        content: Any,
        priority: float = 0.5
    ) -> MentalState:
        """Attribute goal to agent."""
        with self._lock:
            goal = MentalState(
                id=self._generate_id(),
                agent_id=agent_id,
                state_type=MentalStateType.GOAL,
                content=content,
                confidence=priority,
                source="inference"
            )

            self._desires[agent_id][goal.id] = goal
            return goal

    def get_desires(self, agent_id: str) -> List[MentalState]:
        """Get all desires for agent."""
        with self._lock:
            return [
                d for d in self._desires.get(agent_id, {}).values()
                if d.state_type == MentalStateType.DESIRE
            ]

    def get_goals(self, agent_id: str) -> List[MentalState]:
        """Get all goals for agent."""
        with self._lock:
            return [
                d for d in self._desires.get(agent_id, {}).values()
                if d.state_type == MentalStateType.GOAL
            ]

    def prioritized_desires(self, agent_id: str) -> List[MentalState]:
        """Get desires sorted by priority."""
        desires = self.get_desires(agent_id) + self.get_goals(agent_id)
        return sorted(desires, key=lambda d: d.confidence, reverse=True)


# ============================================================================
# INTENTION RECOGNIZER
# ============================================================================

class IntentionRecognizer:
    """
    Recognize and attribute intentions.

    "Ba'el recognizes what others intend." — Ba'el
    """

    def __init__(self, belief_tracker: BeliefTracker, desire_model: DesireModel):
        """Initialize intention recognizer."""
        self._beliefs = belief_tracker
        self._desires = desire_model
        self._intentions: Dict[str, Dict[str, MentalState]] = defaultdict(dict)
        self._intention_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._intention_counter += 1
        return f"intention_{self._intention_counter}"

    def infer_intention(
        self,
        agent_id: str,
        observed_action: str
    ) -> Optional[MentalState]:
        """Infer intention from observed action."""
        with self._lock:
            # Get relevant beliefs and desires
            beliefs = self._beliefs.get_beliefs(agent_id)
            desires = self._desires.get_desires(agent_id)

            # Find desire that action might serve
            for desire in desires:
                desire_content = str(desire.content).lower()
                action_lower = observed_action.lower()

                # Simple match: action relates to desire
                if any(word in action_lower for word in desire_content.split()):
                    intention = MentalState(
                        id=self._generate_id(),
                        agent_id=agent_id,
                        state_type=MentalStateType.INTENTION,
                        content=f"To {observed_action} in order to {desire.content}",
                        confidence=desire.confidence * 0.8,
                        source="inference"
                    )

                    self._intentions[agent_id][intention.id] = intention
                    return intention

            # Default: intention matches action
            intention = MentalState(
                id=self._generate_id(),
                agent_id=agent_id,
                state_type=MentalStateType.INTENTION,
                content=f"To {observed_action}",
                confidence=0.5,
                source="inference"
            )

            self._intentions[agent_id][intention.id] = intention
            return intention

    def attribute_intention(
        self,
        agent_id: str,
        content: Any,
        confidence: float = 0.7
    ) -> MentalState:
        """Directly attribute intention."""
        with self._lock:
            intention = MentalState(
                id=self._generate_id(),
                agent_id=agent_id,
                state_type=MentalStateType.INTENTION,
                content=content,
                confidence=confidence,
                source="attribution"
            )

            self._intentions[agent_id][intention.id] = intention
            return intention

    def get_intentions(self, agent_id: str) -> List[MentalState]:
        """Get all intentions for agent."""
        return list(self._intentions.get(agent_id, {}).values())


# ============================================================================
# PERSPECTIVE TAKER
# ============================================================================

class PerspectiveTaker:
    """
    Take perspective of other agents.

    "Ba'el sees through others' eyes." — Ba'el
    """

    def __init__(self, belief_tracker: BeliefTracker):
        """Initialize perspective taker."""
        self._beliefs = belief_tracker
        self._perspective_cache: Dict[str, Dict] = {}
        self._lock = threading.RLock()

    def take_perspective(
        self,
        agent_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Take perspective of agent in context."""
        with self._lock:
            beliefs = self._beliefs.get_beliefs(agent_id)

            # Build perspective
            perspective = {
                'agent_id': agent_id,
                'visible_objects': context.get('visible_to_' + agent_id, []),
                'known_facts': [b.content for b in beliefs],
                'false_beliefs': self._identify_false_beliefs(beliefs, context),
                'knowledge_gaps': self._identify_gaps(beliefs, context)
            }

            self._perspective_cache[agent_id] = perspective
            return perspective

    def _identify_false_beliefs(
        self,
        beliefs: List[MentalState],
        reality: Dict[str, Any]
    ) -> List[Dict]:
        """Identify beliefs that don't match reality."""
        false_beliefs = []

        for belief in beliefs:
            content = str(belief.content)

            # Check against reality
            for key, value in reality.items():
                if key in content:
                    if str(value) not in content:
                        false_beliefs.append({
                            'belief': belief.content,
                            'reality': {key: value}
                        })

        return false_beliefs

    def _identify_gaps(
        self,
        beliefs: List[MentalState],
        reality: Dict[str, Any]
    ) -> List[str]:
        """Identify what agent doesn't know."""
        known_topics = set()

        for belief in beliefs:
            words = str(belief.content).lower().split()
            known_topics.update(words)

        gaps = []
        for key in reality.keys():
            if key.lower() not in known_topics:
                gaps.append(key)

        return gaps

    def sally_anne_test(
        self,
        sally_id: str,
        anne_id: str,
        object_location: str,
        object_moved_to: str
    ) -> Dict[str, Any]:
        """
        Sally-Anne test implementation.

        Sally puts object in location A, leaves.
        Anne moves object to location B.
        Where will Sally look for the object?
        """
        with self._lock:
            # Sally believes object is in original location
            sally_belief = self._beliefs.attribute_belief(
                sally_id,
                f"Object is in {object_location}",
                confidence=0.9,
                source="observation"
            )

            # Anne knows true location
            anne_belief = self._beliefs.attribute_belief(
                anne_id,
                f"Object is in {object_moved_to}",
                confidence=0.9,
                source="observation"
            )

            return {
                'sally_will_look': object_location,  # False belief!
                'reality': object_moved_to,
                'sally_belief': sally_belief,
                'anne_belief': anne_belief,
                'false_belief_recognized': True
            }


# ============================================================================
# BEHAVIOR PREDICTOR
# ============================================================================

class BehaviorPredictor:
    """
    Predict behavior from mental states.

    "Ba'el predicts what others will do." — Ba'el
    """

    def __init__(
        self,
        belief_tracker: BeliefTracker,
        desire_model: DesireModel,
        intention_recognizer: IntentionRecognizer
    ):
        """Initialize behavior predictor."""
        self._beliefs = belief_tracker
        self._desires = desire_model
        self._intentions = intention_recognizer
        self._prediction_history: List[Prediction] = []
        self._lock = threading.RLock()

    def predict(self, agent_id: str) -> Optional[Prediction]:
        """Predict agent's next action."""
        with self._lock:
            beliefs = self._beliefs.get_beliefs(agent_id)
            desires = self._desires.prioritized_desires(agent_id)
            intentions = self._intentions.get_intentions(agent_id)

            if not desires and not intentions:
                return None

            # BDI logic: action follows from beliefs + desires → intention → action
            reasoning = []

            # Get top desire
            if desires:
                top_desire = desires[0]
                reasoning.append(f"Agent desires: {top_desire.content}")

            # Get relevant beliefs
            if beliefs:
                reasoning.append(f"Agent believes: {beliefs[0].content}")

            # Infer action
            if intentions:
                predicted = intentions[0].content
            elif desires:
                predicted = f"Act to achieve: {desires[0].content}"
            else:
                predicted = "Unknown action"

            prediction = Prediction(
                agent_id=agent_id,
                predicted_action=predicted,
                confidence=0.6,
                reasoning=reasoning,
                based_on_states=[b.id for b in beliefs[:3]]
            )

            self._prediction_history.append(prediction)
            return prediction

    def predict_given_situation(
        self,
        agent_id: str,
        situation: Dict[str, Any]
    ) -> Prediction:
        """Predict behavior in specific situation."""
        with self._lock:
            beliefs = self._beliefs.get_beliefs(agent_id)
            desires = self._desires.prioritized_desires(agent_id)

            reasoning = [f"Situation: {situation}"]

            # Match situation to desires
            relevant_desire = None
            for desire in desires:
                for key in situation:
                    if key.lower() in str(desire.content).lower():
                        relevant_desire = desire
                        break

            if relevant_desire:
                reasoning.append(f"Relevant desire: {relevant_desire.content}")
                predicted = f"Pursue {relevant_desire.content} given {situation}"
            else:
                predicted = "Default/unclear action"

            return Prediction(
                agent_id=agent_id,
                predicted_action=predicted,
                confidence=0.5,
                reasoning=reasoning,
                based_on_states=[d.id for d in desires[:2]]
            )


# ============================================================================
# THEORY OF MIND ENGINE
# ============================================================================

class TheoryOfMindEngine:
    """
    Complete Theory of Mind implementation.

    "Ba'el understands minds." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._agents: Dict[str, Agent] = {}
        self._belief_tracker = BeliefTracker()
        self._desire_model = DesireModel()
        self._intention_recognizer = IntentionRecognizer(
            self._belief_tracker,
            self._desire_model
        )
        self._perspective_taker = PerspectiveTaker(self._belief_tracker)
        self._behavior_predictor = BehaviorPredictor(
            self._belief_tracker,
            self._desire_model,
            self._intention_recognizer
        )
        self._agent_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._agent_counter += 1
        return f"agent_{self._agent_counter}"

    def create_agent(
        self,
        name: str,
        agent_type: AgentType = AgentType.HUMAN,
        traits: Optional[Dict[str, float]] = None
    ) -> Agent:
        """Create new agent model."""
        with self._lock:
            agent = Agent(
                id=self._generate_id(),
                name=name,
                agent_type=agent_type,
                traits=traits or {}
            )

            self._agents[agent.id] = agent
            return agent

    def attribute_belief(
        self,
        agent_id: str,
        content: Any,
        confidence: float = 0.7
    ) -> MentalState:
        """Attribute belief to agent."""
        return self._belief_tracker.attribute_belief(
            agent_id, content, confidence
        )

    def attribute_desire(
        self,
        agent_id: str,
        content: Any,
        intensity: float = 0.5
    ) -> MentalState:
        """Attribute desire to agent."""
        return self._desire_model.attribute_desire(
            agent_id, content, intensity
        )

    def infer_intention(self, agent_id: str, action: str) -> Optional[MentalState]:
        """Infer intention from action."""
        return self._intention_recognizer.infer_intention(agent_id, action)

    def take_perspective(
        self,
        agent_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Take agent's perspective."""
        return self._perspective_taker.take_perspective(agent_id, context)

    def predict_behavior(self, agent_id: str) -> Optional[Prediction]:
        """Predict agent behavior."""
        return self._behavior_predictor.predict(agent_id)

    def false_belief_test(
        self,
        agent_id: str,
        reality: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Test for false belief understanding."""
        perspective = self.take_perspective(agent_id, reality)

        return {
            'agent': agent_id,
            'false_beliefs': perspective.get('false_beliefs', []),
            'knowledge_gaps': perspective.get('knowledge_gaps', []),
            'understands_false_belief': len(perspective.get('false_beliefs', [])) > 0
        }

    def get_mental_state(
        self,
        agent_id: str
    ) -> Dict[str, List[MentalState]]:
        """Get complete mental state of agent."""
        return {
            'beliefs': self._belief_tracker.get_beliefs(agent_id),
            'desires': self._desire_model.get_desires(agent_id),
            'goals': self._desire_model.get_goals(agent_id),
            'intentions': self._intention_recognizer.get_intentions(agent_id)
        }

    @property
    def agents(self) -> List[Agent]:
        """Get all agents."""
        return list(self._agents.values())

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'agents': len(self._agents),
            'total_beliefs': sum(
                len(self._belief_tracker._beliefs.get(a.id, {}))
                for a in self._agents.values()
            ),
            'total_desires': sum(
                len(self._desire_model._desires.get(a.id, {}))
                for a in self._agents.values()
            )
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_theory_of_mind_engine() -> TheoryOfMindEngine:
    """Create ToM engine."""
    return TheoryOfMindEngine()


def create_agent(
    name: str,
    agent_type: AgentType = AgentType.HUMAN
) -> Agent:
    """Create agent."""
    return Agent(
        id=f"agent_{random.randint(1000, 9999)}",
        name=name,
        agent_type=agent_type
    )


def sally_anne_test(engine: TheoryOfMindEngine) -> Dict:
    """Run Sally-Anne false belief test."""
    sally = engine.create_agent("Sally")
    anne = engine.create_agent("Anne")

    return engine._perspective_taker.sally_anne_test(
        sally.id, anne.id,
        "basket", "box"
    )
