"""
BAEL Active Inference Engine
============================

Free Energy Principle and Active Inference implementation.
Based on Karl Friston's theoretical framework.

"Ba'el minimizes surprise." — Ba'el
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
import copy

logger = logging.getLogger("BAEL.ActiveInference")


T = TypeVar('T')


# ============================================================================
# CORE CONCEPTS
# ============================================================================

@dataclass
class Belief:
    """
    A probabilistic belief about the world.
    """
    id: str
    content: Any
    probability: float = 0.5
    precision: float = 1.0  # Inverse variance / confidence
    timestamp: float = field(default_factory=time.time)

    @property
    def entropy(self) -> float:
        """Calculate entropy of belief."""
        if self.probability <= 0 or self.probability >= 1:
            return 0.0
        p = self.probability
        return -(p * math.log(p) + (1-p) * math.log(1-p))

    @property
    def free_energy(self) -> float:
        """
        Variational free energy.

        F = -log p(o|s) + KL[q(s)||p(s)]
        Simplified as: surprise + complexity
        """
        surprise = -math.log(max(self.probability, 1e-10))
        complexity = self.entropy / self.precision
        return surprise + complexity


@dataclass
class Observation:
    """
    A sensory observation.
    """
    id: str
    content: Any
    timestamp: float = field(default_factory=time.time)
    precision: float = 1.0
    source: str = "external"


@dataclass
class Action:
    """
    An action that changes the world.
    """
    id: str
    type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_outcome: Optional[Any] = None
    cost: float = 0.0


@dataclass
class GenerativeModel:
    """
    Generative model: p(outcomes, states | parameters)
    """
    id: str
    states: Dict[str, float]  # State -> probability
    transitions: Dict[str, Dict[str, float]]  # State -> State -> probability
    observations: Dict[str, Dict[str, float]]  # State -> Observation -> probability

    def predict(self, state: str) -> Dict[str, float]:
        """Predict observations given state."""
        return self.observations.get(state, {})

    def transition(self, state: str, action: str = "default") -> Dict[str, float]:
        """Predict next state."""
        key = f"{state}_{action}"
        return self.transitions.get(key, self.transitions.get(state, {}))


# ============================================================================
# FREE ENERGY CALCULATOR
# ============================================================================

class FreeEnergyCalculator:
    """
    Calculate variational free energy.

    "Ba'el quantifies surprise." — Ba'el
    """

    def __init__(self):
        """Initialize calculator."""
        self._lock = threading.RLock()

    def surprise(self, predicted: float, observed: float) -> float:
        """
        Calculate surprise (negative log probability).
        """
        # Gaussian surprise
        diff = abs(predicted - observed)
        return diff ** 2 / 2

    def kl_divergence(
        self,
        q: Dict[str, float],  # Posterior
        p: Dict[str, float]   # Prior
    ) -> float:
        """
        Calculate KL divergence: KL[q||p]
        """
        kl = 0.0
        for state, q_prob in q.items():
            p_prob = p.get(state, 1e-10)
            if q_prob > 0:
                kl += q_prob * math.log(q_prob / p_prob)
        return kl

    def expected_free_energy(
        self,
        policy: List[Action],
        model: GenerativeModel,
        current_state: str,
        preferences: Dict[str, float]
    ) -> float:
        """
        Calculate expected free energy for a policy.

        G = E[H[o|s]] - E[log p(o|C)]
        (Expected uncertainty + Expected disvalue)
        """
        g = 0.0
        state_prob = {current_state: 1.0}

        for action in policy:
            # Predict next state
            next_states = model.transition(current_state, action.type)

            # Calculate expected entropy
            for state, prob in next_states.items():
                observations = model.predict(state)

                # Entropy of observations
                entropy = 0.0
                for obs, obs_prob in observations.items():
                    if obs_prob > 0:
                        entropy -= obs_prob * math.log(obs_prob)

                # Expected value relative to preferences
                value = 0.0
                for obs, obs_prob in observations.items():
                    pref = preferences.get(obs, 0.5)
                    value += obs_prob * math.log(pref + 1e-10)

                g += prob * (entropy - value)

            current_state = max(next_states, key=next_states.get) if next_states else current_state

        return g

    def variational_free_energy(
        self,
        q_states: Dict[str, float],      # Posterior over states
        p_states: Dict[str, float],       # Prior over states
        observations: List[Observation],
        model: GenerativeModel
    ) -> float:
        """
        Calculate total variational free energy.

        F = -E_q[log p(o,s)] + E_q[log q(s)]
          = -E_q[log p(o|s)] - E_q[log p(s)] + E_q[log q(s)]
          = -Accuracy + Complexity
        """
        # Complexity: KL divergence
        complexity = self.kl_divergence(q_states, p_states)

        # Accuracy: expected log likelihood
        accuracy = 0.0
        for state, state_prob in q_states.items():
            predicted = model.predict(state)
            for obs in observations:
                obs_prob = predicted.get(str(obs.content), 0.1)
                accuracy += state_prob * math.log(obs_prob + 1e-10)

        return -accuracy + complexity


# ============================================================================
# BELIEF UPDATER
# ============================================================================

class BeliefUpdater:
    """
    Update beliefs using Bayesian inference.

    "Ba'el refines understanding." — Ba'el
    """

    def __init__(self, learning_rate: float = 0.1):
        """Initialize updater."""
        self._learning_rate = learning_rate
        self._lock = threading.RLock()

    def update_belief(
        self,
        prior: Belief,
        observation: Observation,
        likelihood: float
    ) -> Belief:
        """
        Bayesian belief update.

        posterior = prior * likelihood / evidence
        """
        # Simplified Bayesian update
        prior_prob = prior.probability

        # Evidence approximation
        evidence = prior_prob * likelihood + (1 - prior_prob) * (1 - likelihood)

        # Posterior
        if evidence > 0:
            posterior_prob = (prior_prob * likelihood) / evidence
        else:
            posterior_prob = prior_prob

        # Update precision based on new information
        new_precision = prior.precision + observation.precision * self._learning_rate

        return Belief(
            id=prior.id,
            content=prior.content,
            probability=posterior_prob,
            precision=new_precision
        )

    def prediction_error(
        self,
        predicted: Any,
        observed: Observation
    ) -> float:
        """
        Calculate prediction error.
        """
        if isinstance(predicted, (int, float)) and isinstance(observed.content, (int, float)):
            return abs(predicted - observed.content) * observed.precision
        elif predicted == observed.content:
            return 0.0
        else:
            return 1.0 * observed.precision

    def hierarchical_update(
        self,
        beliefs: List[Belief],
        observation: Observation,
        weights: List[float]
    ) -> List[Belief]:
        """
        Hierarchical belief update.

        Lower levels update faster, higher levels more slowly.
        """
        updated = []

        for i, (belief, weight) in enumerate(zip(beliefs, weights)):
            # Higher levels have lower learning rates
            level_lr = self._learning_rate * (1 - i / len(beliefs))

            # Simplified update
            error = 1.0 if belief.content != observation.content else 0.0
            new_prob = belief.probability + level_lr * weight * (1 - error - belief.probability)

            updated.append(Belief(
                id=belief.id,
                content=belief.content,
                probability=new_prob,
                precision=belief.precision
            ))

        return updated


# ============================================================================
# POLICY SELECTOR
# ============================================================================

class PolicySelector:
    """
    Select actions using active inference.

    "Ba'el chooses optimally." — Ba'el
    """

    def __init__(self, temperature: float = 1.0):
        """Initialize selector."""
        self._temperature = temperature
        self._fe_calculator = FreeEnergyCalculator()
        self._lock = threading.RLock()

    def evaluate_policies(
        self,
        policies: List[List[Action]],
        model: GenerativeModel,
        current_state: str,
        preferences: Dict[str, float]
    ) -> List[Tuple[List[Action], float]]:
        """
        Evaluate all policies by expected free energy.

        Lower G is better.
        """
        evaluated = []

        for policy in policies:
            g = self._fe_calculator.expected_free_energy(
                policy, model, current_state, preferences
            )
            evaluated.append((policy, g))

        # Sort by G (lower is better)
        evaluated.sort(key=lambda x: x[1])

        return evaluated

    def select_policy(
        self,
        policies: List[List[Action]],
        model: GenerativeModel,
        current_state: str,
        preferences: Dict[str, float]
    ) -> List[Action]:
        """
        Select best policy using softmax over negative G.
        """
        evaluated = self.evaluate_policies(policies, model, current_state, preferences)

        if not evaluated:
            return []

        # Softmax selection
        g_values = [g for _, g in evaluated]
        min_g = min(g_values)

        # Convert to probabilities (lower G = higher probability)
        probs = []
        for _, g in evaluated:
            # Negative because lower G is better
            probs.append(math.exp(-(g - min_g) / self._temperature))

        total = sum(probs)
        probs = [p / total for p in probs]

        # Sample
        r = random.random()
        cumsum = 0.0
        for (policy, _), p in zip(evaluated, probs):
            cumsum += p
            if r < cumsum:
                return policy

        return evaluated[0][0]

    def epistemic_value(
        self,
        action: Action,
        model: GenerativeModel,
        current_beliefs: Dict[str, float]
    ) -> float:
        """
        Calculate epistemic value (information gain).

        How much will this action reduce uncertainty?
        """
        # Calculate current entropy
        current_entropy = 0.0
        for prob in current_beliefs.values():
            if prob > 0:
                current_entropy -= prob * math.log(prob)

        # Predict expected entropy after action
        # Simplified: assume action reveals more
        expected_entropy = current_entropy * 0.9

        return current_entropy - expected_entropy


# ============================================================================
# ACTIVE INFERENCE AGENT
# ============================================================================

class ActiveInferenceAgent:
    """
    Agent implementing active inference.

    "Ba'el acts to minimize surprise." — Ba'el
    """

    def __init__(
        self,
        name: str = "agent",
        prior_preferences: Optional[Dict[str, float]] = None
    ):
        """Initialize agent."""
        self._name = name
        self._beliefs: Dict[str, Belief] = {}
        self._preferences = prior_preferences or {}
        self._model = None
        self._observations: List[Observation] = []
        self._actions: List[Action] = []

        self._fe_calculator = FreeEnergyCalculator()
        self._belief_updater = BeliefUpdater()
        self._policy_selector = PolicySelector()

        self._obs_id = 0
        self._action_id = 0
        self._lock = threading.RLock()

    def set_generative_model(self, model: GenerativeModel) -> None:
        """Set agent's generative model."""
        self._model = model

        # Initialize beliefs from model
        for state, prob in model.states.items():
            self._beliefs[state] = Belief(
                id=f"belief_{state}",
                content=state,
                probability=prob
            )

    def observe(self, content: Any, precision: float = 1.0) -> Observation:
        """
        Receive observation and update beliefs.
        """
        with self._lock:
            self._obs_id += 1
            obs = Observation(
                id=f"obs_{self._obs_id}",
                content=content,
                precision=precision
            )
            self._observations.append(obs)

            # Update beliefs based on observation
            self._update_beliefs(obs)

            return obs

    def _update_beliefs(self, observation: Observation) -> None:
        """Update beliefs given observation."""
        if not self._model:
            return

        # For each belief, update based on likelihood
        for state, belief in self._beliefs.items():
            predicted_obs = self._model.predict(state)

            # Likelihood: p(observation | state)
            likelihood = predicted_obs.get(str(observation.content), 0.1)

            # Update
            self._beliefs[state] = self._belief_updater.update_belief(
                belief, observation, likelihood
            )

    def current_state(self) -> str:
        """Get most likely current state."""
        if not self._beliefs:
            return "unknown"

        return max(self._beliefs, key=lambda s: self._beliefs[s].probability)

    def act(self) -> Optional[Action]:
        """
        Select and execute action using active inference.

        Minimizes expected free energy.
        """
        with self._lock:
            if not self._model:
                return None

            # Generate candidate policies
            policies = self._generate_policies()

            if not policies:
                return None

            # Select best policy
            best_policy = self._policy_selector.select_policy(
                policies,
                self._model,
                self.current_state(),
                self._preferences
            )

            if not best_policy:
                return None

            # Execute first action
            action = best_policy[0]
            self._actions.append(action)

            return action

    def _generate_policies(self, horizon: int = 3) -> List[List[Action]]:
        """Generate candidate policies."""
        action_types = ["explore", "exploit", "wait"]
        policies = []

        def generate(current: List[Action], depth: int):
            if depth >= horizon:
                policies.append(current)
                return

            for action_type in action_types:
                self._action_id += 1
                action = Action(
                    id=f"action_{self._action_id}",
                    type=action_type
                )
                generate(current + [action], depth + 1)

        generate([], 0)

        # Limit number of policies
        return policies[:27]  # 3^3

    def free_energy(self) -> float:
        """Calculate current variational free energy."""
        if not self._model:
            return float('inf')

        q_states = {s: b.probability for s, b in self._beliefs.items()}
        p_states = self._model.states

        return self._fe_calculator.variational_free_energy(
            q_states, p_states, self._observations[-10:], self._model
        )

    def precision_weighting(self) -> Dict[str, float]:
        """Get precision weights for each belief."""
        total = sum(b.precision for b in self._beliefs.values())
        if total == 0:
            return {s: 1/len(self._beliefs) for s in self._beliefs}

        return {s: b.precision/total for s, b in self._beliefs.items()}

    @property
    def state(self) -> Dict[str, Any]:
        """Get agent state."""
        return {
            'name': self._name,
            'current_state': self.current_state(),
            'free_energy': self.free_energy(),
            'belief_count': len(self._beliefs),
            'observation_count': len(self._observations),
            'action_count': len(self._actions),
            'beliefs': {
                s: {'prob': b.probability, 'precision': b.precision}
                for s, b in self._beliefs.items()
            }
        }


# ============================================================================
# ACTIVE INFERENCE ENGINE
# ============================================================================

class ActiveInferenceEngine:
    """
    Complete active inference system.

    "Ba'el embodies the Free Energy Principle." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._agents: Dict[str, ActiveInferenceAgent] = {}
        self._fe_calculator = FreeEnergyCalculator()
        self._lock = threading.RLock()

    def create_agent(
        self,
        name: str,
        preferences: Optional[Dict[str, float]] = None
    ) -> ActiveInferenceAgent:
        """Create active inference agent."""
        with self._lock:
            agent = ActiveInferenceAgent(name, preferences)
            self._agents[name] = agent
            return agent

    def create_generative_model(
        self,
        states: List[str],
        initial_probs: Optional[Dict[str, float]] = None
    ) -> GenerativeModel:
        """Create simple generative model."""
        # Uniform initial distribution if not provided
        if initial_probs is None:
            prob = 1 / len(states)
            initial_probs = {s: prob for s in states}

        # Create transition matrix (identity for simplicity)
        transitions = {}
        for state in states:
            transitions[state] = {s: 1/len(states) for s in states}

        # Create observation model (state = observation)
        observations = {}
        for state in states:
            observations[state] = {state: 0.9}
            for other in states:
                if other != state:
                    observations[state][other] = 0.1 / (len(states) - 1)

        return GenerativeModel(
            id=f"model_{time.time()}",
            states=initial_probs,
            transitions=transitions,
            observations=observations
        )

    def simulate(
        self,
        agent: ActiveInferenceAgent,
        observations: List[Any],
        steps: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Simulate agent over steps.

        Returns trajectory of states.
        """
        trajectory = []
        obs_idx = 0

        for step in range(steps):
            # Observe if available
            if obs_idx < len(observations):
                agent.observe(observations[obs_idx])
                obs_idx += 1

            # Act
            action = agent.act()

            # Record state
            trajectory.append({
                'step': step,
                'state': agent.current_state(),
                'free_energy': agent.free_energy(),
                'action': action.type if action else None
            })

        return trajectory

    def global_free_energy(self) -> float:
        """Calculate total free energy across all agents."""
        with self._lock:
            return sum(a.free_energy() for a in self._agents.values())

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'agent_count': len(self._agents),
            'total_free_energy': self.global_free_energy(),
            'agents': {
                name: agent.state
                for name, agent in self._agents.items()
            }
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_active_inference_engine() -> ActiveInferenceEngine:
    """Create active inference engine."""
    return ActiveInferenceEngine()


def create_agent(
    name: str = "agent",
    preferences: Optional[Dict[str, float]] = None
) -> ActiveInferenceAgent:
    """Create active inference agent."""
    return ActiveInferenceAgent(name, preferences)


def calculate_free_energy(
    belief_prob: float,
    observation_likelihood: float
) -> float:
    """Quick free energy calculation."""
    surprise = -math.log(max(observation_likelihood, 1e-10))
    entropy = 0.0
    if 0 < belief_prob < 1:
        entropy = -(belief_prob * math.log(belief_prob) + (1-belief_prob) * math.log(1-belief_prob))
    return surprise + entropy
