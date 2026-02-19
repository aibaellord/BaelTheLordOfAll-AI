"""
BAEL Social Cognition Engine
=============================

Theory of mind, social reasoning, and mentalizing.

"Ba'el understands others' minds." — Ba'el
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
from collections import defaultdict, deque
import copy

logger = logging.getLogger("BAEL.SocialCognition")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class BeliefType(Enum):
    """Types of beliefs."""
    FIRST_ORDER = auto()   # X believes P
    SECOND_ORDER = auto()  # X believes Y believes P
    FALSE_BELIEF = auto()  # X believes P, but P is false
    SHARED = auto()        # X and Y both believe P


class IntentionType(Enum):
    """Types of intentions."""
    INDIVIDUAL = auto()    # X intends to do A
    SHARED = auto()        # X and Y intend to do A together
    COMMUNICATIVE = auto() # X intends to communicate P to Y


class EmotionAttribution(Enum):
    """Emotional attributions."""
    HAPPY = auto()
    SAD = auto()
    ANGRY = auto()
    AFRAID = auto()
    SURPRISED = auto()
    NEUTRAL = auto()


class RelationshipType(Enum):
    """Social relationship types."""
    FRIEND = auto()
    ENEMY = auto()
    STRANGER = auto()
    FAMILY = auto()
    COLLEAGUE = auto()
    SUPERIOR = auto()
    SUBORDINATE = auto()


class SocialAction(Enum):
    """Social actions."""
    COOPERATE = auto()
    COMPETE = auto()
    HELP = auto()
    HARM = auto()
    DECEIVE = auto()
    TRUST = auto()
    RECIPROCATE = auto()


@dataclass
class Agent:
    """
    A social agent.
    """
    id: str
    name: str
    traits: Dict[str, float] = field(default_factory=dict)
    current_emotion: EmotionAttribution = EmotionAttribution.NEUTRAL


@dataclass
class Belief:
    """
    A belief attribution.
    """
    agent_id: str
    content: str
    belief_type: BeliefType
    confidence: float = 0.5
    is_true: bool = True  # Ground truth


@dataclass
class Intention:
    """
    An intention attribution.
    """
    agent_id: str
    action: str
    target_id: Optional[str] = None
    intention_type: IntentionType = IntentionType.INDIVIDUAL
    confidence: float = 0.5


@dataclass
class Relationship:
    """
    A social relationship.
    """
    agent1_id: str
    agent2_id: str
    type: RelationshipType
    strength: float = 0.5  # -1 to 1
    trust: float = 0.5
    history: List[SocialAction] = field(default_factory=list)


@dataclass
class MentalState:
    """
    Mental state attribution.
    """
    agent_id: str
    beliefs: List[Belief]
    intentions: List[Intention]
    emotion: EmotionAttribution
    goals: List[str]


@dataclass
class SocialPrediction:
    """
    Prediction of social behavior.
    """
    agent_id: str
    predicted_action: SocialAction
    target_id: Optional[str]
    confidence: float
    reasoning: str


# ============================================================================
# THEORY OF MIND
# ============================================================================

class TheoryOfMind:
    """
    Theory of mind / mentalizing.

    "Ba'el reads minds." — Ba'el
    """

    def __init__(self):
        """Initialize theory of mind."""
        self._mental_states: Dict[str, MentalState] = {}
        self._lock = threading.RLock()

    def attribute_belief(
        self,
        agent_id: str,
        content: str,
        belief_type: BeliefType = BeliefType.FIRST_ORDER,
        confidence: float = 0.5,
        is_true: bool = True
    ) -> Belief:
        """Attribute belief to agent."""
        with self._lock:
            belief = Belief(
                agent_id=agent_id,
                content=content,
                belief_type=belief_type,
                confidence=confidence,
                is_true=is_true
            )

            if agent_id not in self._mental_states:
                self._mental_states[agent_id] = MentalState(
                    agent_id=agent_id,
                    beliefs=[],
                    intentions=[],
                    emotion=EmotionAttribution.NEUTRAL,
                    goals=[]
                )

            self._mental_states[agent_id].beliefs.append(belief)

            return belief

    def attribute_intention(
        self,
        agent_id: str,
        action: str,
        target_id: str = None,
        intention_type: IntentionType = IntentionType.INDIVIDUAL,
        confidence: float = 0.5
    ) -> Intention:
        """Attribute intention to agent."""
        with self._lock:
            intention = Intention(
                agent_id=agent_id,
                action=action,
                target_id=target_id,
                intention_type=intention_type,
                confidence=confidence
            )

            if agent_id not in self._mental_states:
                self._mental_states[agent_id] = MentalState(
                    agent_id=agent_id,
                    beliefs=[],
                    intentions=[],
                    emotion=EmotionAttribution.NEUTRAL,
                    goals=[]
                )

            self._mental_states[agent_id].intentions.append(intention)

            return intention

    def attribute_emotion(
        self,
        agent_id: str,
        emotion: EmotionAttribution
    ) -> None:
        """Attribute emotion to agent."""
        with self._lock:
            if agent_id not in self._mental_states:
                self._mental_states[agent_id] = MentalState(
                    agent_id=agent_id,
                    beliefs=[],
                    intentions=[],
                    emotion=emotion,
                    goals=[]
                )
            else:
                self._mental_states[agent_id].emotion = emotion

    def get_mental_state(
        self,
        agent_id: str
    ) -> Optional[MentalState]:
        """Get mental state of agent."""
        return self._mental_states.get(agent_id)

    def false_belief_reasoning(
        self,
        agent_id: str,
        actual_state: str,
        believed_state: str
    ) -> Belief:
        """Reason about false beliefs (Sally-Anne type)."""
        with self._lock:
            # Agent believes something false
            belief = self.attribute_belief(
                agent_id=agent_id,
                content=believed_state,
                belief_type=BeliefType.FALSE_BELIEF,
                confidence=0.8,
                is_true=False
            )

            # Track actual state
            self.attribute_belief(
                agent_id="_reality",
                content=actual_state,
                belief_type=BeliefType.FIRST_ORDER,
                confidence=1.0,
                is_true=True
            )

            return belief

    def second_order_belief(
        self,
        agent1_id: str,
        agent2_id: str,
        content: str
    ) -> Belief:
        """Model second-order beliefs: A believes B believes P."""
        with self._lock:
            nested = f"{agent2_id} believes: {content}"

            return self.attribute_belief(
                agent_id=agent1_id,
                content=nested,
                belief_type=BeliefType.SECOND_ORDER,
                confidence=0.6
            )


# ============================================================================
# SOCIAL RELATIONSHIP MODEL
# ============================================================================

class SocialRelationshipModel:
    """
    Model social relationships.

    "Ba'el maps social networks." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        self._relationships: Dict[Tuple[str, str], Relationship] = {}
        self._agents: Dict[str, Agent] = {}
        self._agent_counter = 0
        self._lock = threading.RLock()

    def _generate_agent_id(self) -> str:
        self._agent_counter += 1
        return f"agent_{self._agent_counter}"

    def _relationship_key(
        self,
        agent1_id: str,
        agent2_id: str
    ) -> Tuple[str, str]:
        return (min(agent1_id, agent2_id), max(agent1_id, agent2_id))

    def create_agent(
        self,
        name: str,
        traits: Dict[str, float] = None
    ) -> Agent:
        """Create social agent."""
        with self._lock:
            agent = Agent(
                id=self._generate_agent_id(),
                name=name,
                traits=traits or {}
            )

            self._agents[agent.id] = agent
            return agent

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        return self._agents.get(agent_id)

    def set_relationship(
        self,
        agent1_id: str,
        agent2_id: str,
        rel_type: RelationshipType,
        strength: float = 0.5,
        trust: float = 0.5
    ) -> Relationship:
        """Set relationship between agents."""
        with self._lock:
            key = self._relationship_key(agent1_id, agent2_id)

            relationship = Relationship(
                agent1_id=agent1_id,
                agent2_id=agent2_id,
                type=rel_type,
                strength=max(-1, min(1, strength)),
                trust=max(0, min(1, trust))
            )

            self._relationships[key] = relationship
            return relationship

    def get_relationship(
        self,
        agent1_id: str,
        agent2_id: str
    ) -> Optional[Relationship]:
        """Get relationship between agents."""
        key = self._relationship_key(agent1_id, agent2_id)
        return self._relationships.get(key)

    def record_interaction(
        self,
        agent1_id: str,
        agent2_id: str,
        action: SocialAction
    ) -> None:
        """Record social interaction."""
        with self._lock:
            key = self._relationship_key(agent1_id, agent2_id)

            if key not in self._relationships:
                self.set_relationship(agent1_id, agent2_id, RelationshipType.STRANGER)

            rel = self._relationships[key]
            rel.history.append(action)

            # Update relationship based on action
            if action in [SocialAction.COOPERATE, SocialAction.HELP, SocialAction.TRUST]:
                rel.strength = min(1, rel.strength + 0.1)
                rel.trust = min(1, rel.trust + 0.05)
            elif action in [SocialAction.COMPETE, SocialAction.HARM, SocialAction.DECEIVE]:
                rel.strength = max(-1, rel.strength - 0.15)
                rel.trust = max(0, rel.trust - 0.1)

    def get_social_network(
        self,
        agent_id: str
    ) -> List[Tuple[str, Relationship]]:
        """Get agent's social network."""
        with self._lock:
            network = []

            for key, rel in self._relationships.items():
                if agent_id in key:
                    other_id = key[0] if key[1] == agent_id else key[1]
                    network.append((other_id, rel))

            return network


# ============================================================================
# SOCIAL ACTION PREDICTOR
# ============================================================================

class SocialActionPredictor:
    """
    Predict social actions.

    "Ba'el anticipates behavior." — Ba'el
    """

    def __init__(
        self,
        tom: TheoryOfMind,
        relationships: SocialRelationshipModel
    ):
        """Initialize predictor."""
        self._tom = tom
        self._relationships = relationships
        self._lock = threading.RLock()

    def predict_action(
        self,
        agent_id: str,
        target_id: str = None
    ) -> SocialPrediction:
        """Predict what action agent will take."""
        with self._lock:
            # Get mental state
            mental_state = self._tom.get_mental_state(agent_id)

            # Get relationship
            relationship = None
            if target_id:
                relationship = self._relationships.get_relationship(agent_id, target_id)

            # Predict based on mental state and relationship
            if relationship:
                if relationship.trust > 0.7:
                    action = SocialAction.COOPERATE
                    confidence = relationship.trust
                    reasoning = "High trust indicates cooperative behavior"
                elif relationship.strength < -0.3:
                    action = SocialAction.COMPETE
                    confidence = abs(relationship.strength)
                    reasoning = "Negative relationship suggests competition"
                elif relationship.strength > 0.5:
                    action = SocialAction.HELP
                    confidence = relationship.strength
                    reasoning = "Positive relationship suggests helping"
                else:
                    action = SocialAction.RECIPROCATE
                    confidence = 0.5
                    reasoning = "Neutral relationship - likely to reciprocate"
            else:
                # No relationship info
                action = SocialAction.COOPERATE
                confidence = 0.3
                reasoning = "Default to cooperation with unknown agent"

            # Adjust based on emotional state
            if mental_state:
                if mental_state.emotion == EmotionAttribution.ANGRY:
                    if action == SocialAction.COOPERATE:
                        action = SocialAction.COMPETE
                        reasoning += " (adjusted for anger)"
                elif mental_state.emotion == EmotionAttribution.AFRAID:
                    if action == SocialAction.COMPETE:
                        action = SocialAction.COOPERATE
                        reasoning += " (adjusted for fear)"

            return SocialPrediction(
                agent_id=agent_id,
                predicted_action=action,
                target_id=target_id,
                confidence=confidence,
                reasoning=reasoning
            )

    def predict_reaction(
        self,
        agent_id: str,
        stimulus_action: SocialAction,
        stimulus_agent_id: str
    ) -> SocialPrediction:
        """Predict reaction to social action."""
        with self._lock:
            relationship = self._relationships.get_relationship(agent_id, stimulus_agent_id)

            # Reciprocity principle
            if stimulus_action in [SocialAction.COOPERATE, SocialAction.HELP]:
                reaction = SocialAction.RECIPROCATE
                confidence = 0.7
                reasoning = "Reciprocity for positive action"
            elif stimulus_action in [SocialAction.COMPETE, SocialAction.HARM]:
                if relationship and relationship.trust < 0.3:
                    reaction = SocialAction.HARM
                    confidence = 0.6
                    reasoning = "Retaliation for harm (low trust)"
                else:
                    reaction = SocialAction.COMPETE
                    confidence = 0.5
                    reasoning = "Defensive competition"
            elif stimulus_action == SocialAction.DECEIVE:
                reaction = SocialAction.COMPETE
                confidence = 0.8
                reasoning = "Trust broken by deception"
            else:
                reaction = SocialAction.COOPERATE
                confidence = 0.4
                reasoning = "Default cooperative response"

            return SocialPrediction(
                agent_id=agent_id,
                predicted_action=reaction,
                target_id=stimulus_agent_id,
                confidence=confidence,
                reasoning=reasoning
            )


# ============================================================================
# SOCIAL COGNITION ENGINE
# ============================================================================

class SocialCognitionEngine:
    """
    Complete social cognition engine.

    "Ba'el's social intelligence." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._tom = TheoryOfMind()
        self._relationships = SocialRelationshipModel()
        self._predictor = SocialActionPredictor(self._tom, self._relationships)

        self._lock = threading.RLock()

    # Agent management

    def create_agent(
        self,
        name: str,
        traits: Dict[str, float] = None
    ) -> Agent:
        """Create social agent."""
        return self._relationships.create_agent(name, traits)

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent."""
        return self._relationships.get_agent(agent_id)

    # Relationship management

    def set_relationship(
        self,
        agent1_id: str,
        agent2_id: str,
        rel_type: RelationshipType,
        strength: float = 0.5
    ) -> Relationship:
        """Set relationship."""
        return self._relationships.set_relationship(
            agent1_id, agent2_id, rel_type, strength
        )

    def get_relationship(
        self,
        agent1_id: str,
        agent2_id: str
    ) -> Optional[Relationship]:
        """Get relationship."""
        return self._relationships.get_relationship(agent1_id, agent2_id)

    # Theory of mind

    def attribute_belief(
        self,
        agent_id: str,
        content: str,
        is_true: bool = True
    ) -> Belief:
        """Attribute belief to agent."""
        return self._tom.attribute_belief(
            agent_id, content,
            is_true=is_true
        )

    def attribute_intention(
        self,
        agent_id: str,
        action: str,
        target_id: str = None
    ) -> Intention:
        """Attribute intention to agent."""
        return self._tom.attribute_intention(
            agent_id, action, target_id
        )

    def attribute_emotion(
        self,
        agent_id: str,
        emotion: EmotionAttribution
    ) -> None:
        """Attribute emotion to agent."""
        self._tom.attribute_emotion(agent_id, emotion)

    def get_mental_state(
        self,
        agent_id: str
    ) -> Optional[MentalState]:
        """Get mental state."""
        return self._tom.get_mental_state(agent_id)

    def false_belief_task(
        self,
        agent_id: str,
        reality: str,
        belief: str
    ) -> Belief:
        """Sally-Anne false belief task."""
        return self._tom.false_belief_reasoning(agent_id, reality, belief)

    def second_order_belief(
        self,
        agent1_id: str,
        agent2_id: str,
        content: str
    ) -> Belief:
        """Second-order belief attribution."""
        return self._tom.second_order_belief(agent1_id, agent2_id, content)

    # Interaction

    def record_interaction(
        self,
        agent1_id: str,
        agent2_id: str,
        action: SocialAction
    ) -> None:
        """Record social interaction."""
        self._relationships.record_interaction(agent1_id, agent2_id, action)

    # Prediction

    def predict_action(
        self,
        agent_id: str,
        target_id: str = None
    ) -> SocialPrediction:
        """Predict social action."""
        return self._predictor.predict_action(agent_id, target_id)

    def predict_reaction(
        self,
        agent_id: str,
        action: SocialAction,
        from_agent_id: str
    ) -> SocialPrediction:
        """Predict reaction to action."""
        return self._predictor.predict_reaction(agent_id, action, from_agent_id)

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'agents': len(self._relationships._agents),
            'relationships': len(self._relationships._relationships),
            'mental_states': len(self._tom._mental_states)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_social_cognition_engine() -> SocialCognitionEngine:
    """Create social cognition engine."""
    return SocialCognitionEngine()


def predict_behavior(
    agent_traits: Dict[str, float],
    relationship_strength: float
) -> str:
    """Quick behavior prediction."""
    if relationship_strength > 0.5:
        return "cooperate"
    elif relationship_strength < -0.3:
        return "compete"
    else:
        return "reciprocate"
