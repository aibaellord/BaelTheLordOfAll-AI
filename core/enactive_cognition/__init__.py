"""
BAEL Enactive Cognition Engine
===============================

Cognition through interaction and structural coupling.

"Ba'el enacts its world." — Ba'el
"""

import logging
import threading
import time
import random
import math
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod

logger = logging.getLogger("BAEL.EnactiveCognition")


T = TypeVar('T')


# ============================================================================
# CORE CONCEPTS
# ============================================================================

class InteractionType(Enum):
    """Types of enactive interaction."""
    SENSORIMOTOR = auto()
    SOCIAL = auto()
    LINGUISTIC = auto()
    EMOTIONAL = auto()
    COGNITIVE = auto()


class CouplingStrength(Enum):
    """Strength of structural coupling."""
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    TIGHT = 4


@dataclass
class Interaction:
    """
    An enactive interaction.
    """
    id: str
    interaction_type: InteractionType
    action: str
    perception: str
    result: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    success: bool = True

    @property
    def age(self) -> float:
        return time.time() - self.timestamp


@dataclass
class SensorimotorPattern:
    """
    A learned sensorimotor pattern (know-how).
    """
    id: str
    action_sequence: List[str]
    expected_perceptions: List[str]
    activation: float = 0.5
    usage_count: int = 0
    success_rate: float = 1.0

    def match(self, perception: str) -> bool:
        """Check if pattern matches perception."""
        return perception in self.expected_perceptions

    def update_success(self, success: bool) -> None:
        """Update success rate."""
        self.usage_count += 1
        if success:
            self.success_rate = (self.success_rate * (self.usage_count - 1) + 1) / self.usage_count
        else:
            self.success_rate = (self.success_rate * (self.usage_count - 1)) / self.usage_count


# ============================================================================
# SENSORIMOTOR CONTINGENCY
# ============================================================================

class SensorimotorContingency:
    """
    Law relating actions to sensory changes.

    "Ba'el knows what happens when it acts." — Ba'el
    """

    def __init__(self, name: str):
        """Initialize contingency."""
        self._name = name
        self._mappings: Dict[str, Dict[str, float]] = {}  # action -> {perception -> probability}
        self._lock = threading.RLock()

    def record(self, action: str, perception: str) -> None:
        """Record action-perception pair."""
        with self._lock:
            if action not in self._mappings:
                self._mappings[action] = {}

            if perception not in self._mappings[action]:
                self._mappings[action][perception] = 0.0

            self._mappings[action][perception] += 1.0

    def predict(self, action: str) -> Dict[str, float]:
        """Predict perceptions for action."""
        with self._lock:
            if action not in self._mappings:
                return {}

            total = sum(self._mappings[action].values())
            if total == 0:
                return {}

            return {
                p: c / total
                for p, c in self._mappings[action].items()
            }

    def most_likely(self, action: str) -> Optional[str]:
        """Get most likely perception for action."""
        predictions = self.predict(action)
        if not predictions:
            return None
        return max(predictions, key=predictions.get)

    def action_for(self, desired_perception: str) -> Optional[str]:
        """Find action that produces perception."""
        with self._lock:
            best_action = None
            best_prob = 0.0

            for action, perceptions in self._mappings.items():
                if desired_perception in perceptions:
                    total = sum(perceptions.values())
                    prob = perceptions[desired_perception] / total if total > 0 else 0
                    if prob > best_prob:
                        best_prob = prob
                        best_action = action

            return best_action


# ============================================================================
# STRUCTURAL COUPLING
# ============================================================================

class StructuralCoupling:
    """
    Coupling between cognitive system and environment.

    "Ba'el is coupled with its world." — Ba'el
    """

    def __init__(self):
        """Initialize coupling."""
        self._domains: Dict[str, Dict[str, Any]] = {}
        self._coupling_history: List[Interaction] = []
        self._perturbations: List[Dict] = []
        self._lock = threading.RLock()

    def add_domain(self, name: str, properties: Dict[str, Any]) -> None:
        """Add interaction domain."""
        with self._lock:
            self._domains[name] = properties

    def perturb(
        self,
        domain: str,
        perturbation: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Perturb the system from environment.

        Response is determined by internal structure, not perturbation.
        """
        with self._lock:
            self._perturbations.append({
                'domain': domain,
                'perturbation': perturbation,
                'timestamp': time.time()
            })

            if domain not in self._domains:
                return None

            # Response based on internal structure
            domain_props = self._domains[domain]
            response = {}

            for key, value in perturbation.items():
                if key in domain_props:
                    # Modulated by internal structure
                    response[key] = domain_props[key] * 0.5 + value * 0.5

            return response

    def record_interaction(self, interaction: Interaction) -> None:
        """Record interaction in coupling history."""
        with self._lock:
            self._coupling_history.append(interaction)

            # Bound history
            if len(self._coupling_history) > 10000:
                self._coupling_history = self._coupling_history[-5000:]

    def coupling_strength(self, domain: str) -> CouplingStrength:
        """Assess coupling strength with domain."""
        with self._lock:
            relevant = [
                i for i in self._coupling_history[-100:]
                if i.action.startswith(domain) or i.perception.startswith(domain)
            ]

            count = len(relevant)

            if count > 75:
                return CouplingStrength.TIGHT
            elif count > 50:
                return CouplingStrength.STRONG
            elif count > 25:
                return CouplingStrength.MODERATE
            else:
                return CouplingStrength.WEAK

    @property
    def interaction_count(self) -> int:
        """Get total interaction count."""
        return len(self._coupling_history)


# ============================================================================
# PARTICIPATORY SENSE-MAKING
# ============================================================================

class ParticipatorySenseMaking:
    """
    Collaborative meaning-making between agents.

    "Ba'el makes meaning with others." — Ba'el
    """

    def __init__(self):
        """Initialize participatory sense-making."""
        self._participants: Dict[str, Dict] = {}
        self._shared_meanings: Dict[str, Any] = {}
        self._interactions: List[Dict] = []
        self._lock = threading.RLock()

    def add_participant(self, agent_id: str, capabilities: List[str]) -> None:
        """Add participant."""
        with self._lock:
            self._participants[agent_id] = {
                'capabilities': capabilities,
                'meanings': {},
                'interaction_count': 0
            }

    def propose_meaning(
        self,
        agent_id: str,
        symbol: str,
        meaning: Any
    ) -> bool:
        """Agent proposes meaning for symbol."""
        with self._lock:
            if agent_id not in self._participants:
                return False

            self._participants[agent_id]['meanings'][symbol] = meaning

            self._interactions.append({
                'type': 'propose',
                'agent': agent_id,
                'symbol': symbol,
                'meaning': str(meaning),
                'timestamp': time.time()
            })

            return True

    def negotiate_meaning(self, symbol: str) -> Optional[Any]:
        """Negotiate shared meaning for symbol."""
        with self._lock:
            proposals = []

            for agent_id, data in self._participants.items():
                if symbol in data['meanings']:
                    proposals.append(data['meanings'][symbol])

            if not proposals:
                return None

            # Simple consensus: most common
            from collections import Counter
            proposal_strs = [str(p) for p in proposals]
            most_common = Counter(proposal_strs).most_common(1)[0][0]

            # Find original proposal
            for p in proposals:
                if str(p) == most_common:
                    self._shared_meanings[symbol] = p
                    return p

            return proposals[0]

    def interact(
        self,
        agent1_id: str,
        agent2_id: str,
        content: Any
    ) -> Dict[str, Any]:
        """Record interaction between agents."""
        with self._lock:
            if agent1_id in self._participants:
                self._participants[agent1_id]['interaction_count'] += 1
            if agent2_id in self._participants:
                self._participants[agent2_id]['interaction_count'] += 1

            interaction = {
                'agents': [agent1_id, agent2_id],
                'content': content,
                'timestamp': time.time()
            }
            self._interactions.append(interaction)

            return interaction

    @property
    def shared_meanings(self) -> Dict[str, Any]:
        """Get all shared meanings."""
        return self._shared_meanings.copy()


# ============================================================================
# ENACTIVE INTERFACE
# ============================================================================

class EnactiveInterface:
    """
    Interface between cognitive system and environment.

    "Ba'el interfaces through action." — Ba'el
    """

    def __init__(self):
        """Initialize interface."""
        self._actions: Dict[str, Callable] = {}
        self._perceptions: Dict[str, Callable] = {}
        self._environment_state: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def register_action(
        self,
        name: str,
        handler: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]
    ) -> None:
        """Register action handler."""
        with self._lock:
            self._actions[name] = handler

    def register_perception(
        self,
        name: str,
        handler: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """Register perception handler."""
        with self._lock:
            self._perceptions[name] = handler

    def set_environment(self, state: Dict[str, Any]) -> None:
        """Set environment state."""
        with self._lock:
            self._environment_state = state.copy()

    def act(self, action_name: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Perform action."""
        with self._lock:
            if action_name not in self._actions:
                return None

            handler = self._actions[action_name]
            result = handler(params, self._environment_state)

            # Update environment based on action
            if isinstance(result, dict) and 'env_changes' in result:
                self._environment_state.update(result['env_changes'])

            return result

    def perceive(self, perception_name: str) -> Any:
        """Get perception."""
        with self._lock:
            if perception_name not in self._perceptions:
                return None

            handler = self._perceptions[perception_name]
            return handler(self._environment_state)

    def perceive_all(self) -> Dict[str, Any]:
        """Get all perceptions."""
        with self._lock:
            return {
                name: handler(self._environment_state)
                for name, handler in self._perceptions.items()
            }


# ============================================================================
# ENACTIVE MEMORY
# ============================================================================

class EnactiveMemory:
    """
    Memory as re-enactment of past interactions.

    "Ba'el remembers by re-enacting." — Ba'el
    """

    def __init__(self):
        """Initialize enactive memory."""
        self._patterns: Dict[str, SensorimotorPattern] = {}
        self._traces: List[Interaction] = []
        self._lock = threading.RLock()

    def store_pattern(self, pattern: SensorimotorPattern) -> None:
        """Store sensorimotor pattern."""
        with self._lock:
            self._patterns[pattern.id] = pattern

    def store_trace(self, interaction: Interaction) -> None:
        """Store interaction trace."""
        with self._lock:
            self._traces.append(interaction)

            # Bound
            if len(self._traces) > 10000:
                self._traces = self._traces[-5000:]

    def retrieve_pattern(self, perception: str) -> Optional[SensorimotorPattern]:
        """Retrieve pattern matching perception."""
        with self._lock:
            matches = [
                p for p in self._patterns.values()
                if p.match(perception)
            ]

            if not matches:
                return None

            # Return most activated
            return max(matches, key=lambda p: p.activation * p.success_rate)

    def reenact(self, pattern: SensorimotorPattern) -> List[str]:
        """Re-enact pattern (return action sequence)."""
        with self._lock:
            if pattern.id not in self._patterns:
                return []

            pattern.usage_count += 1
            pattern.activation += 0.1

            return pattern.action_sequence.copy()

    def consolidate(self) -> None:
        """Consolidate memory (strengthen used, decay unused)."""
        with self._lock:
            for pattern in self._patterns.values():
                if pattern.usage_count > 0:
                    # Strengthen
                    pattern.activation = min(1.0, pattern.activation * 1.1)
                else:
                    # Decay
                    pattern.activation *= 0.95

    def similar_traces(self, current: Interaction, n: int = 5) -> List[Interaction]:
        """Find similar past traces."""
        with self._lock:
            # Simple similarity based on action/perception overlap
            def similarity(trace: Interaction) -> float:
                action_sim = 1.0 if trace.action == current.action else 0.0
                perception_sim = 1.0 if trace.perception == current.perception else 0.0
                return action_sim * 0.5 + perception_sim * 0.5

            sorted_traces = sorted(
                self._traces,
                key=similarity,
                reverse=True
            )

            return sorted_traces[:n]


# ============================================================================
# ENACTIVE COGNITION ENGINE
# ============================================================================

class EnactiveCognitionEngine:
    """
    Complete enactive cognition engine.

    "Ba'el knows through doing." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._interface = EnactiveInterface()
        self._contingencies: Dict[str, SensorimotorContingency] = {}
        self._coupling = StructuralCoupling()
        self._sense_making = ParticipatorySenseMaking()
        self._memory = EnactiveMemory()
        self._current_interaction: Optional[Interaction] = None
        self._interaction_id = 0
        self._lock = threading.RLock()

    def _generate_interaction_id(self) -> str:
        self._interaction_id += 1
        return f"interaction_{self._interaction_id}"

    def add_contingency(self, name: str) -> SensorimotorContingency:
        """Add sensorimotor contingency domain."""
        with self._lock:
            contingency = SensorimotorContingency(name)
            self._contingencies[name] = contingency
            return contingency

    def act(
        self,
        action: str,
        domain: str = "default",
        params: Optional[Dict] = None
    ) -> Interaction:
        """Perform action and create interaction."""
        with self._lock:
            # Perform action
            result = self._interface.act(action, params or {})

            # Get perception
            perceptions = self._interface.perceive_all()
            perception_str = str(perceptions)

            # Record contingency
            if domain in self._contingencies:
                self._contingencies[domain].record(action, perception_str)

            # Create interaction
            interaction = Interaction(
                id=self._generate_interaction_id(),
                interaction_type=InteractionType.SENSORIMOTOR,
                action=action,
                perception=perception_str,
                result=result or {},
                success=result is not None
            )

            # Store in memory and coupling
            self._memory.store_trace(interaction)
            self._coupling.record_interaction(interaction)

            self._current_interaction = interaction

            return interaction

    def predict_perception(self, action: str, domain: str = "default") -> Optional[str]:
        """Predict perception for action."""
        if domain in self._contingencies:
            return self._contingencies[domain].most_likely(action)
        return None

    def find_action(self, desired_perception: str, domain: str = "default") -> Optional[str]:
        """Find action to produce perception."""
        if domain in self._contingencies:
            return self._contingencies[domain].action_for(desired_perception)
        return None

    def learn_pattern(
        self,
        pattern_id: str,
        actions: List[str],
        perceptions: List[str]
    ) -> SensorimotorPattern:
        """Learn new sensorimotor pattern."""
        pattern = SensorimotorPattern(
            id=pattern_id,
            action_sequence=actions,
            expected_perceptions=perceptions
        )
        self._memory.store_pattern(pattern)
        return pattern

    def recall_and_reenact(self, current_perception: str) -> Optional[List[str]]:
        """Recall pattern and re-enact."""
        pattern = self._memory.retrieve_pattern(current_perception)
        if pattern:
            return self._memory.reenact(pattern)
        return None

    def couple_with_domain(self, domain: str, properties: Dict[str, Any]) -> None:
        """Establish structural coupling with domain."""
        self._coupling.add_domain(domain, properties)

    def add_participant(self, agent_id: str, capabilities: List[str]) -> None:
        """Add sense-making participant."""
        self._sense_making.add_participant(agent_id, capabilities)

    def negotiate_meaning(self, symbol: str, proposal: Any, agent_id: str) -> Optional[Any]:
        """Participate in meaning negotiation."""
        self._sense_making.propose_meaning(agent_id, symbol, proposal)
        return self._sense_making.negotiate_meaning(symbol)

    def step(self) -> Dict[str, Any]:
        """Execute one cognitive step."""
        with self._lock:
            # Consolidate memory
            self._memory.consolidate()

            return {
                'current_interaction': self._current_interaction.id if self._current_interaction else None,
                'patterns_known': len(self._memory._patterns),
                'traces_stored': len(self._memory._traces),
                'coupling_domains': len(self._coupling._domains),
                'shared_meanings': len(self._sense_making.shared_meanings)
            }

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'contingencies': list(self._contingencies.keys()),
            'patterns': len(self._memory._patterns),
            'traces': len(self._memory._traces),
            'coupling': {
                'domains': list(self._coupling._domains.keys()),
                'interactions': self._coupling.interaction_count
            },
            'sense_making': {
                'participants': len(self._sense_making._participants),
                'shared_meanings': len(self._sense_making.shared_meanings)
            }
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_enactive_cognition_engine() -> EnactiveCognitionEngine:
    """Create enactive cognition engine."""
    return EnactiveCognitionEngine()


def create_sensorimotor_contingency(name: str) -> SensorimotorContingency:
    """Create sensorimotor contingency."""
    return SensorimotorContingency(name)


def create_structural_coupling() -> StructuralCoupling:
    """Create structural coupling."""
    return StructuralCoupling()


def create_enactive_interface() -> EnactiveInterface:
    """Create enactive interface."""
    return EnactiveInterface()


def create_sensorimotor_pattern(
    pattern_id: str,
    actions: List[str],
    perceptions: List[str]
) -> SensorimotorPattern:
    """Create sensorimotor pattern."""
    return SensorimotorPattern(
        id=pattern_id,
        action_sequence=actions,
        expected_perceptions=perceptions
    )
