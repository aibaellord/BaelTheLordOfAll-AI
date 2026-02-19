"""
BAEL Free Energy Engine
========================

Free Energy Principle and Active Inference.
Minimizing surprise through perception and action.

"Ba'el minimizes its free energy." — Ba'el
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

logger = logging.getLogger("BAEL.FreeEnergy")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class BeliefState(Enum):
    """State of a belief."""
    CERTAIN = auto()
    PROBABLE = auto()
    UNCERTAIN = auto()
    UNKNOWN = auto()


@dataclass
class GenerativeModel:
    """
    A generative model of the world.
    P(observations, hidden states | parameters)
    """
    id: str
    hidden_states: Dict[str, float]  # Beliefs about hidden states
    observations: Dict[str, float]   # Expected observations
    transitions: Dict[str, Dict[str, float]]  # State transitions
    likelihood: Dict[str, Dict[str, float]]  # Observation likelihoods
    prior: Dict[str, float]  # Prior beliefs


@dataclass
class Prediction:
    """
    A prediction from the generative model.
    """
    id: str
    predicted_observation: Any
    confidence: float
    hidden_state_estimate: Dict[str, float]


@dataclass
class PredictionError:
    """
    Error between prediction and observation.
    """
    prediction_id: str
    predicted: Any
    observed: Any
    error_magnitude: float
    precision: float


@dataclass
class Action:
    """
    An action to minimize free energy.
    """
    id: str
    action_type: str
    parameters: Dict[str, Any]
    expected_free_energy: float


# ============================================================================
# VARIATIONAL FREE ENERGY
# ============================================================================

class VariationalFreeEnergy:
    """
    Variational Free Energy calculations.

    "Ba'el measures its uncertainty." — Ba'el
    """

    def __init__(self):
        """Initialize VFE calculator."""
        self._lock = threading.RLock()

    def compute_vfe(
        self,
        recognition_density: Dict[str, float],
        generative_model: GenerativeModel,
        observation: Any
    ) -> float:
        """
        Compute Variational Free Energy.

        F = -log P(o) + KL[Q(s) || P(s|o)]
        ≈ Complexity - Accuracy
        """
        with self._lock:
            # Accuracy: Expected log likelihood
            accuracy = self._compute_accuracy(
                recognition_density,
                generative_model,
                observation
            )

            # Complexity: KL divergence from prior
            complexity = self._compute_kl_divergence(
                recognition_density,
                generative_model.prior
            )

            # VFE = Complexity - Accuracy
            vfe = complexity - accuracy

            return vfe

    def _compute_accuracy(
        self,
        recognition: Dict[str, float],
        model: GenerativeModel,
        observation: Any
    ) -> float:
        """Compute expected log likelihood (accuracy)."""
        accuracy = 0.0

        for state, q in recognition.items():
            if state in model.likelihood:
                for obs, p in model.likelihood[state].items():
                    if str(observation) == str(obs):
                        accuracy += q * math.log(max(p, 1e-10))

        return accuracy

    def _compute_kl_divergence(
        self,
        q: Dict[str, float],
        p: Dict[str, float]
    ) -> float:
        """Compute KL divergence KL[Q || P]."""
        kl = 0.0

        for state in q:
            q_val = max(q[state], 1e-10)
            p_val = max(p.get(state, 1e-10), 1e-10)

            kl += q_val * math.log(q_val / p_val)

        return kl

    def compute_surprise(self, observation: Any, model: GenerativeModel) -> float:
        """
        Compute surprise (negative log evidence).

        -log P(o) under model
        """
        # Marginalize over hidden states
        evidence = 0.0

        for state, prior_prob in model.prior.items():
            if state in model.likelihood:
                for obs, likelihood in model.likelihood[state].items():
                    if str(observation) == str(obs):
                        evidence += prior_prob * likelihood

        if evidence > 0:
            return -math.log(evidence)
        else:
            return float('inf')


# ============================================================================
# EXPECTED FREE ENERGY
# ============================================================================

class ExpectedFreeEnergy:
    """
    Expected Free Energy for action selection.

    "Ba'el chooses actions that reduce uncertainty." — Ba'el
    """

    def __init__(self):
        """Initialize EFE calculator."""
        self._lock = threading.RLock()

    def compute_efe(
        self,
        action: Action,
        current_belief: Dict[str, float],
        generative_model: GenerativeModel,
        preferences: Dict[str, float]
    ) -> float:
        """
        Compute Expected Free Energy for action.

        G = Epistemic value + Pragmatic value
        G = Expected Information Gain + Expected Utility
        """
        with self._lock:
            # Epistemic value: information gain (exploration)
            epistemic = self._compute_epistemic_value(
                action,
                current_belief,
                generative_model
            )

            # Pragmatic value: expected utility (exploitation)
            pragmatic = self._compute_pragmatic_value(
                action,
                current_belief,
                generative_model,
                preferences
            )

            # EFE = -Epistemic - Pragmatic (minimize this)
            efe = -epistemic - pragmatic

            return efe

    def _compute_epistemic_value(
        self,
        action: Action,
        belief: Dict[str, float],
        model: GenerativeModel
    ) -> float:
        """Compute expected information gain."""
        # Simplified: Higher for uncertain states
        uncertainty = 0.0

        for state, prob in belief.items():
            if 0 < prob < 1:
                uncertainty -= prob * math.log(max(prob, 1e-10))

        return uncertainty

    def _compute_pragmatic_value(
        self,
        action: Action,
        belief: Dict[str, float],
        model: GenerativeModel,
        preferences: Dict[str, float]
    ) -> float:
        """Compute expected utility."""
        utility = 0.0

        # Expected observations under action
        for state, prob in belief.items():
            if state in model.transitions and action.action_type in model.transitions[state]:
                next_state = model.transitions[state][action.action_type]

                # Preference for next state
                if next_state in preferences:
                    utility += prob * preferences[next_state]

        return utility

    def select_action(
        self,
        actions: List[Action],
        current_belief: Dict[str, float],
        model: GenerativeModel,
        preferences: Dict[str, float]
    ) -> Action:
        """Select action with lowest EFE."""
        if not actions:
            return None

        best_action = None
        best_efe = float('inf')

        for action in actions:
            efe = self.compute_efe(action, current_belief, model, preferences)
            action.expected_free_energy = efe

            if efe < best_efe:
                best_efe = efe
                best_action = action

        return best_action


# ============================================================================
# BELIEF UPDATING
# ============================================================================

class BeliefUpdater:
    """
    Update beliefs using prediction errors.

    "Ba'el updates its beliefs." — Ba'el
    """

    def __init__(self):
        """Initialize belief updater."""
        self._lock = threading.RLock()

    def update_belief(
        self,
        current_belief: Dict[str, float],
        observation: Any,
        generative_model: GenerativeModel,
        learning_rate: float = 0.1
    ) -> Dict[str, float]:
        """
        Update belief given observation.

        Approximate Bayesian inference.
        """
        with self._lock:
            new_belief = current_belief.copy()

            # Compute likelihood of observation for each state
            likelihoods = {}
            for state in current_belief:
                if state in generative_model.likelihood:
                    for obs, p in generative_model.likelihood[state].items():
                        if str(observation) == str(obs):
                            likelihoods[state] = p
                            break
                    else:
                        likelihoods[state] = 0.01  # Low likelihood
                else:
                    likelihoods[state] = 0.01

            # Bayesian update
            for state in new_belief:
                prior = current_belief[state]
                likelihood = likelihoods.get(state, 0.01)

                # Unnormalized posterior
                new_belief[state] = prior * likelihood

            # Normalize
            total = sum(new_belief.values())
            if total > 0:
                for state in new_belief:
                    new_belief[state] /= total

            # Blend with learning rate
            for state in new_belief:
                new_belief[state] = (
                    (1 - learning_rate) * current_belief[state] +
                    learning_rate * new_belief[state]
                )

            return new_belief

    def compute_prediction_error(
        self,
        prediction: Prediction,
        observation: Any
    ) -> PredictionError:
        """Compute prediction error."""
        # Simple error magnitude
        pred_str = str(prediction.predicted_observation)
        obs_str = str(observation)

        if pred_str == obs_str:
            error_magnitude = 0.0
        else:
            # Levenshtein-like distance normalized
            max_len = max(len(pred_str), len(obs_str), 1)
            diff = sum(1 for a, b in zip(pred_str, obs_str) if a != b)
            diff += abs(len(pred_str) - len(obs_str))
            error_magnitude = diff / max_len

        return PredictionError(
            prediction_id=prediction.id,
            predicted=prediction.predicted_observation,
            observed=observation,
            error_magnitude=error_magnitude,
            precision=prediction.confidence
        )


# ============================================================================
# ACTIVE INFERENCE AGENT
# ============================================================================

class ActiveInferenceAgent:
    """
    An agent that uses active inference.

    "Ba'el acts to minimize surprise." — Ba'el
    """

    def __init__(self, model: GenerativeModel):
        """Initialize agent."""
        self._model = model
        self._belief = model.prior.copy()
        self._preferences: Dict[str, float] = {}
        self._vfe_calc = VariationalFreeEnergy()
        self._efe_calc = ExpectedFreeEnergy()
        self._updater = BeliefUpdater()
        self._action_history: List[Action] = []
        self._observation_history: List[Any] = []
        self._free_energy_history: List[float] = []
        self._action_counter = 0
        self._lock = threading.RLock()

    def _generate_action_id(self) -> str:
        self._action_counter += 1
        return f"action_{self._action_counter}"

    def set_preferences(self, preferences: Dict[str, float]) -> None:
        """Set preferred states."""
        with self._lock:
            self._preferences = preferences

    def observe(self, observation: Any) -> float:
        """
        Process observation and return surprise.
        """
        with self._lock:
            self._observation_history.append(observation)

            # Compute surprise
            surprise = self._vfe_calc.compute_surprise(observation, self._model)

            # Update beliefs
            self._belief = self._updater.update_belief(
                self._belief,
                observation,
                self._model
            )

            # Track free energy
            vfe = self._vfe_calc.compute_vfe(
                self._belief,
                self._model,
                observation
            )
            self._free_energy_history.append(vfe)

            return surprise

    def generate_actions(self, n: int = 5) -> List[Action]:
        """Generate possible actions."""
        actions = []

        # Generate actions based on model transitions
        for state in self._model.transitions:
            for action_type in self._model.transitions[state]:
                action = Action(
                    id=self._generate_action_id(),
                    action_type=action_type,
                    parameters={},
                    expected_free_energy=0.0
                )
                actions.append(action)

                if len(actions) >= n:
                    break

        return actions[:n]

    def select_action(self) -> Optional[Action]:
        """Select action using active inference."""
        with self._lock:
            actions = self.generate_actions()

            if not actions:
                return None

            best = self._efe_calc.select_action(
                actions,
                self._belief,
                self._model,
                self._preferences
            )

            if best:
                self._action_history.append(best)

            return best

    def act(self, action: Action) -> Dict[str, Any]:
        """Execute action and return expected outcome."""
        with self._lock:
            # Predict next state
            expected_next = {}

            for state, prob in self._belief.items():
                if state in self._model.transitions:
                    transitions = self._model.transitions[state]
                    if action.action_type in transitions:
                        next_state = transitions[action.action_type]
                        expected_next[next_state] = expected_next.get(next_state, 0) + prob

            return {
                'action': action.action_type,
                'expected_next_state': expected_next,
                'current_belief': self._belief.copy()
            }

    def step(self, observation: Any) -> Dict[str, Any]:
        """Complete perception-action cycle."""
        with self._lock:
            # Observe
            surprise = self.observe(observation)

            # Select action
            action = self.select_action()

            # Execute
            result = None
            if action:
                result = self.act(action)

            return {
                'surprise': surprise,
                'action': action.action_type if action else None,
                'belief': self._belief.copy(),
                'free_energy': self._free_energy_history[-1] if self._free_energy_history else 0
            }

    @property
    def belief(self) -> Dict[str, float]:
        return self._belief.copy()

    @property
    def free_energy(self) -> float:
        return self._free_energy_history[-1] if self._free_energy_history else 0


# ============================================================================
# FREE ENERGY ENGINE
# ============================================================================

class FreeEnergyEngine:
    """
    Complete Free Energy Principle engine.

    "Ba'el lives by the free energy principle." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._models: Dict[str, GenerativeModel] = {}
        self._agents: Dict[str, ActiveInferenceAgent] = {}
        self._vfe = VariationalFreeEnergy()
        self._efe = ExpectedFreeEnergy()
        self._model_counter = 0
        self._lock = threading.RLock()

    def _generate_model_id(self) -> str:
        self._model_counter += 1
        return f"model_{self._model_counter}"

    def create_model(
        self,
        hidden_states: List[str],
        observations: List[str],
        transitions: Dict[str, Dict[str, str]] = None,
        likelihood: Dict[str, Dict[str, float]] = None
    ) -> GenerativeModel:
        """Create generative model."""
        with self._lock:
            n_states = len(hidden_states)
            uniform_prior = 1.0 / n_states

            model = GenerativeModel(
                id=self._generate_model_id(),
                hidden_states={s: uniform_prior for s in hidden_states},
                observations={o: 0.0 for o in observations},
                transitions=transitions or {},
                likelihood=likelihood or {},
                prior={s: uniform_prior for s in hidden_states}
            )

            self._models[model.id] = model
            return model

    def create_agent(
        self,
        model: GenerativeModel,
        preferences: Optional[Dict[str, float]] = None
    ) -> ActiveInferenceAgent:
        """Create active inference agent."""
        with self._lock:
            agent = ActiveInferenceAgent(model)

            if preferences:
                agent.set_preferences(preferences)

            agent_id = f"agent_{len(self._agents)}"
            self._agents[agent_id] = agent

            return agent

    def compute_vfe(
        self,
        belief: Dict[str, float],
        model: GenerativeModel,
        observation: Any
    ) -> float:
        """Compute variational free energy."""
        return self._vfe.compute_vfe(belief, model, observation)

    def compute_efe(
        self,
        action: Action,
        belief: Dict[str, float],
        model: GenerativeModel,
        preferences: Dict[str, float]
    ) -> float:
        """Compute expected free energy."""
        return self._efe.compute_efe(action, belief, model, preferences)

    def simulate(
        self,
        agent: ActiveInferenceAgent,
        observations: List[Any]
    ) -> List[Dict]:
        """Simulate agent over observations."""
        results = []

        for obs in observations:
            result = agent.step(obs)
            results.append(result)

        return results

    @property
    def models(self) -> List[GenerativeModel]:
        return list(self._models.values())

    @property
    def agents(self) -> List[ActiveInferenceAgent]:
        return list(self._agents.values())

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'models': len(self._models),
            'agents': len(self._agents),
            'total_observations': sum(
                len(a._observation_history) for a in self._agents.values()
            )
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_free_energy_engine() -> FreeEnergyEngine:
    """Create free energy engine."""
    return FreeEnergyEngine()


def create_generative_model(
    states: List[str],
    observations: List[str]
) -> GenerativeModel:
    """Create simple generative model."""
    engine = FreeEnergyEngine()
    return engine.create_model(states, observations)


def create_active_inference_agent(
    model: GenerativeModel,
    preferences: Optional[Dict[str, float]] = None
) -> ActiveInferenceAgent:
    """Create active inference agent."""
    agent = ActiveInferenceAgent(model)
    if preferences:
        agent.set_preferences(preferences)
    return agent
