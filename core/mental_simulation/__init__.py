"""
BAEL Mental Simulation Engine
==============================

Mental simulation and imagery.
Prospection and retrospection.

"Ba'el simulates possibilities." — Ba'el
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

logger = logging.getLogger("BAEL.MentalSimulation")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class SimulationDirection(Enum):
    """Direction of mental simulation."""
    PROSPECTIVE = auto()   # Future simulation
    RETROSPECTIVE = auto() # Past simulation
    COUNTERFACTUAL = auto()  # Alternative present


class SimulationModality(Enum):
    """Modality of simulation."""
    VISUAL = auto()
    AUDITORY = auto()
    MOTOR = auto()
    EMOTIONAL = auto()
    CONCEPTUAL = auto()
    MULTIMODAL = auto()


class SimulationResolution(Enum):
    """Resolution of simulation."""
    SCHEMATIC = auto()     # Abstract, gist
    INTERMEDIATE = auto()
    DETAILED = auto()      # Vivid, specific


class OutcomeValence(Enum):
    """Valence of simulated outcome."""
    POSITIVE = auto()
    NEUTRAL = auto()
    NEGATIVE = auto()


@dataclass
class SimulationState:
    """
    A state in a simulation.
    """
    id: str
    content: Any
    timestamp: float = 0.0  # Time in simulation
    modalities: Set[SimulationModality] = field(default_factory=set)
    vividness: float = 0.5
    confidence: float = 0.5


@dataclass
class SimulationTransition:
    """
    A transition between states.
    """
    id: str
    source_id: str
    target_id: str
    action: str
    probability: float = 1.0
    duration: float = 1.0


@dataclass
class Simulation:
    """
    A complete mental simulation.
    """
    id: str
    direction: SimulationDirection
    states: List[SimulationState]
    transitions: List[SimulationTransition]
    start_time: float
    end_time: float = 0.0
    resolution: SimulationResolution = SimulationResolution.INTERMEDIATE
    outcome_valence: OutcomeValence = OutcomeValence.NEUTRAL

    @property
    def duration(self) -> float:
        if self.end_time > 0:
            return self.end_time - self.start_time
        return 0.0

    @property
    def average_vividness(self) -> float:
        if not self.states:
            return 0.0
        return sum(s.vividness for s in self.states) / len(self.states)


@dataclass
class Scenario:
    """
    A scenario for simulation.
    """
    id: str
    name: str
    initial_state: Dict[str, Any]
    goal_state: Optional[Dict[str, Any]] = None
    constraints: List[str] = field(default_factory=list)
    actors: List[str] = field(default_factory=list)


@dataclass
class SimulationOutcome:
    """
    Outcome of a simulation.
    """
    simulation_id: str
    achieved_goal: bool
    final_state: SimulationState
    path_length: int
    valence: OutcomeValence
    insights: List[str]


# ============================================================================
# SIMULATION BUILDER
# ============================================================================

class SimulationBuilder:
    """
    Build mental simulations.

    "Ba'el builds simulations." — Ba'el
    """

    def __init__(self):
        """Initialize builder."""
        self._state_counter = 0
        self._transition_counter = 0
        self._sim_counter = 0
        self._lock = threading.RLock()

    def _generate_state_id(self) -> str:
        self._state_counter += 1
        return f"state_{self._state_counter}"

    def _generate_transition_id(self) -> str:
        self._transition_counter += 1
        return f"trans_{self._transition_counter}"

    def _generate_sim_id(self) -> str:
        self._sim_counter += 1
        return f"sim_{self._sim_counter}"

    def create_state(
        self,
        content: Any,
        modalities: Set[SimulationModality] = None,
        vividness: float = 0.5
    ) -> SimulationState:
        """Create simulation state."""
        return SimulationState(
            id=self._generate_state_id(),
            content=content,
            modalities=modalities or {SimulationModality.CONCEPTUAL},
            vividness=vividness
        )

    def create_transition(
        self,
        source: SimulationState,
        target: SimulationState,
        action: str,
        probability: float = 1.0
    ) -> SimulationTransition:
        """Create state transition."""
        return SimulationTransition(
            id=self._generate_transition_id(),
            source_id=source.id,
            target_id=target.id,
            action=action,
            probability=probability
        )

    def build_simulation(
        self,
        direction: SimulationDirection,
        states: List[SimulationState],
        transitions: List[SimulationTransition],
        resolution: SimulationResolution = SimulationResolution.INTERMEDIATE
    ) -> Simulation:
        """Build complete simulation."""
        with self._lock:
            return Simulation(
                id=self._generate_sim_id(),
                direction=direction,
                states=states,
                transitions=transitions,
                start_time=time.time(),
                resolution=resolution
            )

    def build_linear_simulation(
        self,
        direction: SimulationDirection,
        contents: List[Any],
        actions: List[str] = None
    ) -> Simulation:
        """Build linear simulation from contents."""
        with self._lock:
            states = [self.create_state(c) for c in contents]

            transitions = []
            actions = actions or ["next"] * (len(states) - 1)

            for i in range(len(states) - 1):
                trans = self.create_transition(
                    states[i],
                    states[i + 1],
                    actions[i] if i < len(actions) else "next"
                )
                transitions.append(trans)

            return self.build_simulation(direction, states, transitions)


# ============================================================================
# PROSPECTIVE SIMULATION
# ============================================================================

class ProspectiveSimulator:
    """
    Simulate future possibilities.

    "Ba'el imagines futures." — Ba'el
    """

    def __init__(self, builder: SimulationBuilder):
        """Initialize prospector."""
        self._builder = builder
        self._simulations: List[Simulation] = []
        self._lock = threading.RLock()

    def simulate_future(
        self,
        current_state: Dict[str, Any],
        action_sequence: List[str],
        state_predictor: Callable[[Dict[str, Any], str], Dict[str, Any]] = None
    ) -> Simulation:
        """Simulate future from current state."""
        with self._lock:
            states = []
            transitions = []

            # Initial state
            current = self._builder.create_state(current_state)
            states.append(current)

            # Simulate each action
            state_data = current_state.copy()

            for action in action_sequence:
                # Predict next state
                if state_predictor:
                    state_data = state_predictor(state_data, action)
                else:
                    state_data = self._default_predict(state_data, action)

                next_state = self._builder.create_state(state_data)
                states.append(next_state)

                trans = self._builder.create_transition(current, next_state, action)
                transitions.append(trans)

                current = next_state

            sim = self._builder.build_simulation(
                SimulationDirection.PROSPECTIVE,
                states,
                transitions
            )

            self._simulations.append(sim)
            return sim

    def _default_predict(
        self,
        state: Dict[str, Any],
        action: str
    ) -> Dict[str, Any]:
        """Default state predictor."""
        new_state = state.copy()
        new_state['last_action'] = action
        new_state['time'] = state.get('time', 0) + 1
        return new_state

    def monte_carlo_futures(
        self,
        current_state: Dict[str, Any],
        possible_actions: List[str],
        depth: int = 3,
        samples: int = 10
    ) -> List[Simulation]:
        """Monte Carlo sampling of future paths."""
        with self._lock:
            simulations = []

            for _ in range(samples):
                actions = [
                    random.choice(possible_actions)
                    for _ in range(depth)
                ]

                sim = self.simulate_future(current_state, actions)
                simulations.append(sim)

            return simulations

    def best_action(
        self,
        current_state: Dict[str, Any],
        possible_actions: List[str],
        value_fn: Callable[[Dict[str, Any]], float],
        depth: int = 3,
        samples_per_action: int = 5
    ) -> str:
        """Find best first action through simulation."""
        with self._lock:
            action_values = {}

            for action in possible_actions:
                values = []

                for _ in range(samples_per_action):
                    # Start with this action, then random
                    actions = [action] + [
                        random.choice(possible_actions)
                        for _ in range(depth - 1)
                    ]

                    sim = self.simulate_future(current_state, actions)

                    # Evaluate final state
                    final_state = sim.states[-1].content
                    value = value_fn(final_state)
                    values.append(value)

                action_values[action] = sum(values) / len(values)

            return max(action_values, key=action_values.get)


# ============================================================================
# COUNTERFACTUAL SIMULATION
# ============================================================================

class CounterfactualSimulator:
    """
    Simulate counterfactual alternatives.

    "Ba'el imagines what could have been." — Ba'el
    """

    def __init__(self, builder: SimulationBuilder):
        """Initialize counterfactual simulator."""
        self._builder = builder
        self._lock = threading.RLock()

    def what_if(
        self,
        actual_states: List[Dict[str, Any]],
        change_point: int,
        alternative_action: str,
        state_predictor: Callable = None
    ) -> Tuple[Simulation, Simulation]:
        """Simulate 'what if' alternative."""
        with self._lock:
            # Actual simulation
            actual_sim = self._builder.build_linear_simulation(
                SimulationDirection.RETROSPECTIVE,
                actual_states
            )

            # Counterfactual simulation
            cf_states = actual_states[:change_point + 1].copy()

            # Different path from change point
            current = cf_states[-1].copy()
            current['alternative'] = True
            current['action'] = alternative_action

            for i in range(len(actual_states) - change_point - 1):
                if state_predictor:
                    current = state_predictor(current, alternative_action)
                else:
                    current = current.copy()
                    current['step'] = current.get('step', 0) + 1

                cf_states.append(current)

            cf_sim = self._builder.build_linear_simulation(
                SimulationDirection.COUNTERFACTUAL,
                cf_states
            )

            return actual_sim, cf_sim

    def regret_analysis(
        self,
        actual_outcome: float,
        counterfactual_outcome: float
    ) -> Dict[str, float]:
        """Analyze regret from counterfactual."""
        diff = counterfactual_outcome - actual_outcome

        return {
            'regret': max(0, diff),  # Positive = missed opportunity
            'relief': max(0, -diff),  # Positive = avoided worse
            'difference': diff,
            'relative': diff / max(0.001, abs(actual_outcome))
        }


# ============================================================================
# MENTAL SIMULATION ENGINE
# ============================================================================

class MentalSimulationEngine:
    """
    Complete mental simulation engine.

    "Ba'el's imagination." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._builder = SimulationBuilder()
        self._prospector = ProspectiveSimulator(self._builder)
        self._counterfactual = CounterfactualSimulator(self._builder)
        self._simulations: Dict[str, Simulation] = {}
        self._scenario_counter = 0
        self._lock = threading.RLock()

    def _generate_scenario_id(self) -> str:
        self._scenario_counter += 1
        return f"scenario_{self._scenario_counter}"

    # Prospective simulation

    def imagine_future(
        self,
        current: Dict[str, Any],
        actions: List[str]
    ) -> Simulation:
        """Imagine future from actions."""
        sim = self._prospector.simulate_future(current, actions)
        self._simulations[sim.id] = sim
        return sim

    def explore_futures(
        self,
        current: Dict[str, Any],
        possible_actions: List[str],
        depth: int = 3,
        samples: int = 10
    ) -> List[Simulation]:
        """Explore multiple futures."""
        sims = self._prospector.monte_carlo_futures(
            current, possible_actions, depth, samples
        )
        for sim in sims:
            self._simulations[sim.id] = sim
        return sims

    def decide(
        self,
        current: Dict[str, Any],
        actions: List[str],
        value_fn: Callable[[Dict[str, Any]], float]
    ) -> str:
        """Decide best action through simulation."""
        return self._prospector.best_action(current, actions, value_fn)

    # Counterfactual simulation

    def what_if(
        self,
        history: List[Dict[str, Any]],
        change_at: int,
        alternative: str
    ) -> Tuple[Simulation, Simulation]:
        """Counterfactual 'what if'."""
        actual, cf = self._counterfactual.what_if(
            history, change_at, alternative
        )
        self._simulations[actual.id] = actual
        self._simulations[cf.id] = cf
        return actual, cf

    def compute_regret(
        self,
        actual: float,
        counterfactual: float
    ) -> Dict[str, float]:
        """Compute regret."""
        return self._counterfactual.regret_analysis(actual, counterfactual)

    # Simple simulation

    def simulate(
        self,
        scenario: str,
        steps: int = 5,
        direction: SimulationDirection = SimulationDirection.PROSPECTIVE
    ) -> Simulation:
        """Run simple simulation."""
        contents = [{'scenario': scenario, 'step': i} for i in range(steps)]
        sim = self._builder.build_linear_simulation(direction, contents)
        self._simulations[sim.id] = sim
        return sim

    def replay(
        self,
        events: List[Any]
    ) -> Simulation:
        """Replay past events."""
        sim = self._builder.build_linear_simulation(
            SimulationDirection.RETROSPECTIVE,
            events
        )
        self._simulations[sim.id] = sim
        return sim

    # Scenario management

    def create_scenario(
        self,
        name: str,
        initial: Dict[str, Any],
        goal: Dict[str, Any] = None
    ) -> Scenario:
        """Create simulation scenario."""
        return Scenario(
            id=self._generate_scenario_id(),
            name=name,
            initial_state=initial,
            goal_state=goal
        )

    # Analysis

    def evaluate_outcome(
        self,
        simulation: Simulation,
        goal: Dict[str, Any]
    ) -> SimulationOutcome:
        """Evaluate simulation outcome."""
        final_state = simulation.states[-1]
        final_content = final_state.content

        # Check goal achievement
        achieved = True
        for key, value in goal.items():
            if final_content.get(key) != value:
                achieved = False
                break

        # Determine valence
        valence = OutcomeValence.NEUTRAL
        if achieved:
            valence = OutcomeValence.POSITIVE
        elif 'failure' in str(final_content).lower():
            valence = OutcomeValence.NEGATIVE

        simulation.outcome_valence = valence

        return SimulationOutcome(
            simulation_id=simulation.id,
            achieved_goal=achieved,
            final_state=final_state,
            path_length=len(simulation.states),
            valence=valence,
            insights=[]
        )

    def get_simulation(self, sim_id: str) -> Optional[Simulation]:
        """Get simulation by ID."""
        return self._simulations.get(sim_id)

    @property
    def simulations(self) -> List[Simulation]:
        return list(self._simulations.values())

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'simulations': len(self._simulations),
            'prospective': sum(
                1 for s in self._simulations.values()
                if s.direction == SimulationDirection.PROSPECTIVE
            ),
            'counterfactual': sum(
                1 for s in self._simulations.values()
                if s.direction == SimulationDirection.COUNTERFACTUAL
            )
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_mental_simulation_engine() -> MentalSimulationEngine:
    """Create mental simulation engine."""
    return MentalSimulationEngine()


def imagine(
    scenario: str,
    steps: int = 5
) -> Simulation:
    """Quick imagination."""
    engine = create_mental_simulation_engine()
    return engine.simulate(scenario, steps)
