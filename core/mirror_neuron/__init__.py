"""
BAEL Mirror Neuron Engine
==========================

Action understanding through motor simulation.
Mirroring observed actions internally.

"Ba'el understands by mirroring." — Ba'el
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

logger = logging.getLogger("BAEL.MirrorNeuron")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ActionType(Enum):
    """Types of actions."""
    REACH = auto()
    GRASP = auto()
    MANIPULATE = auto()
    COMMUNICATE = auto()
    LOCOMOTE = auto()
    GESTURE = auto()
    EXPRESSION = auto()


class MirrorState(Enum):
    """State of mirror neuron system."""
    IDLE = auto()
    OBSERVING = auto()
    MIRRORING = auto()
    SIMULATING = auto()
    PREDICTING = auto()


@dataclass
class MotorProgram:
    """
    A motor program (action representation).
    """
    id: str
    action_type: ActionType
    parameters: Dict[str, float]
    sequence: List[str]
    duration_ms: float = 500.0

    def execute(self) -> List[str]:
        """Return action sequence."""
        return self.sequence.copy()


@dataclass
class ObservedAction:
    """
    An observed action from another agent.
    """
    id: str
    actor: str
    action_type: ActionType
    parameters: Dict[str, Any]
    goal: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    @property
    def age(self) -> float:
        return time.time() - self.timestamp


@dataclass
class MirrorActivation:
    """
    Activation of mirror system.
    """
    observed_action_id: str
    motor_program_id: str
    activation_strength: float
    goal_inference: Optional[str] = None
    intention_inference: Optional[str] = None


@dataclass
class Imitation:
    """
    An imitation attempt.
    """
    id: str
    observed_action_id: str
    executed_program: MotorProgram
    accuracy: float
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# MOTOR REPERTOIRE
# ============================================================================

class MotorRepertoire:
    """
    Collection of motor programs.

    "Ba'el's motor knowledge." — Ba'el
    """

    def __init__(self):
        """Initialize repertoire."""
        self._programs: Dict[str, MotorProgram] = {}
        self._action_index: Dict[ActionType, List[str]] = defaultdict(list)
        self._program_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._program_counter += 1
        return f"motor_{self._program_counter}"

    def add_program(
        self,
        action_type: ActionType,
        parameters: Dict[str, float],
        sequence: List[str]
    ) -> MotorProgram:
        """Add motor program."""
        with self._lock:
            program = MotorProgram(
                id=self._generate_id(),
                action_type=action_type,
                parameters=parameters,
                sequence=sequence
            )

            self._programs[program.id] = program
            self._action_index[action_type].append(program.id)

            return program

    def get_program(self, program_id: str) -> Optional[MotorProgram]:
        """Get program by ID."""
        return self._programs.get(program_id)

    def find_by_type(self, action_type: ActionType) -> List[MotorProgram]:
        """Find programs by action type."""
        with self._lock:
            program_ids = self._action_index.get(action_type, [])
            return [self._programs[pid] for pid in program_ids]

    def find_similar(
        self,
        observed: ObservedAction,
        threshold: float = 0.5
    ) -> List[Tuple[MotorProgram, float]]:
        """Find similar programs to observed action."""
        with self._lock:
            matches = []

            # First filter by type
            candidates = self.find_by_type(observed.action_type)

            for program in candidates:
                similarity = self._compute_similarity(program, observed)
                if similarity >= threshold:
                    matches.append((program, similarity))

            # Sort by similarity
            matches.sort(key=lambda x: x[1], reverse=True)
            return matches

    def _compute_similarity(
        self,
        program: MotorProgram,
        observed: ObservedAction
    ) -> float:
        """Compute similarity between program and observation."""
        # Type match
        if program.action_type != observed.action_type:
            return 0.0

        # Parameter match
        param_sim = 0.0
        common_params = set(program.parameters.keys()) & set(observed.parameters.keys())

        if common_params:
            for param in common_params:
                prog_val = program.parameters[param]
                obs_val = observed.parameters.get(param, 0)

                if isinstance(obs_val, (int, float)):
                    diff = abs(prog_val - obs_val)
                    param_sim += 1.0 / (1.0 + diff)

            param_sim /= len(common_params)
        else:
            param_sim = 0.5  # Neutral if no common params

        return param_sim

    @property
    def programs(self) -> List[MotorProgram]:
        return list(self._programs.values())


# ============================================================================
# MIRROR NEURONS
# ============================================================================

class MirrorNeuronSystem:
    """
    Mirror neuron simulation.

    "Ba'el mirrors observed actions." — Ba'el
    """

    def __init__(self, repertoire: MotorRepertoire):
        """Initialize mirror system."""
        self._repertoire = repertoire
        self._state = MirrorState.IDLE
        self._current_activation: Optional[MirrorActivation] = None
        self._activation_history: List[MirrorActivation] = []
        self._observation_counter = 0
        self._lock = threading.RLock()

    def _generate_obs_id(self) -> str:
        self._observation_counter += 1
        return f"obs_{self._observation_counter}"

    def observe(
        self,
        actor: str,
        action_type: ActionType,
        parameters: Dict[str, Any],
        goal: Optional[str] = None
    ) -> MirrorActivation:
        """Observe action and activate mirror system."""
        with self._lock:
            self._state = MirrorState.OBSERVING

            # Create observation
            observed = ObservedAction(
                id=self._generate_obs_id(),
                actor=actor,
                action_type=action_type,
                parameters=parameters,
                goal=goal
            )

            # Find matching motor program
            matches = self._repertoire.find_similar(observed)

            if matches:
                best_program, similarity = matches[0]

                self._state = MirrorState.MIRRORING

                activation = MirrorActivation(
                    observed_action_id=observed.id,
                    motor_program_id=best_program.id,
                    activation_strength=similarity,
                    goal_inference=goal or self._infer_goal(best_program),
                    intention_inference=self._infer_intention(observed, best_program)
                )
            else:
                activation = MirrorActivation(
                    observed_action_id=observed.id,
                    motor_program_id="none",
                    activation_strength=0.0,
                    goal_inference=None,
                    intention_inference=None
                )

            self._current_activation = activation
            self._activation_history.append(activation)

            return activation

    def _infer_goal(self, program: MotorProgram) -> str:
        """Infer goal from motor program."""
        # Simple goal inference based on action type
        goal_map = {
            ActionType.REACH: "acquire_object",
            ActionType.GRASP: "hold_object",
            ActionType.MANIPULATE: "change_object_state",
            ActionType.COMMUNICATE: "convey_information",
            ActionType.LOCOMOTE: "change_location",
            ActionType.GESTURE: "express_meaning",
            ActionType.EXPRESSION: "convey_emotion"
        }
        return goal_map.get(program.action_type, "unknown")

    def _infer_intention(
        self,
        observed: ObservedAction,
        program: MotorProgram
    ) -> str:
        """Infer intention behind action."""
        # Simple intention inference
        if observed.goal:
            return f"To {observed.goal}"

        return f"To {self._infer_goal(program)}"

    def simulate(self) -> Optional[List[str]]:
        """Simulate current mirror activation."""
        with self._lock:
            if not self._current_activation:
                return None

            if self._current_activation.motor_program_id == "none":
                return None

            self._state = MirrorState.SIMULATING

            program = self._repertoire.get_program(
                self._current_activation.motor_program_id
            )

            if program:
                return program.execute()

            return None

    def predict_next(self) -> Optional[str]:
        """Predict next action in sequence."""
        with self._lock:
            self._state = MirrorState.PREDICTING

            if not self._current_activation:
                return None

            program = self._repertoire.get_program(
                self._current_activation.motor_program_id
            )

            if program and program.sequence:
                # Return next step in sequence
                return program.sequence[-1] if program.sequence else None

            return None

    @property
    def state(self) -> MirrorState:
        return self._state

    @property
    def current_activation(self) -> Optional[MirrorActivation]:
        return self._current_activation


# ============================================================================
# ACTION UNDERSTANDING
# ============================================================================

class ActionUnderstanding:
    """
    Understanding actions through mirroring.

    "Ba'el understands actions by simulating them." — Ba'el
    """

    def __init__(self, mirror_system: MirrorNeuronSystem):
        """Initialize action understanding."""
        self._mirror = mirror_system
        self._understanding_cache: Dict[str, Dict] = {}
        self._lock = threading.RLock()

    def understand(
        self,
        actor: str,
        action_type: ActionType,
        parameters: Dict[str, Any],
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Understand observed action."""
        with self._lock:
            # Mirror the action
            activation = self._mirror.observe(actor, action_type, parameters)

            # Simulate internally
            simulated_sequence = self._mirror.simulate()

            understanding = {
                'action_type': action_type.name,
                'actor': actor,
                'activation_strength': activation.activation_strength,
                'inferred_goal': activation.goal_inference,
                'inferred_intention': activation.intention_inference,
                'simulated_as': simulated_sequence,
                'understood': activation.activation_strength > 0.3,
                'context': context
            }

            self._understanding_cache[activation.observed_action_id] = understanding

            return understanding

    def predict_outcome(
        self,
        action_type: ActionType,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Predict outcome of action."""
        with self._lock:
            # Observe self-generated action
            activation = self._mirror.observe("self", action_type, parameters)

            predicted_next = self._mirror.predict_next()

            return {
                'action': action_type.name,
                'predicted_next': predicted_next,
                'confidence': activation.activation_strength
            }

    def empathize(
        self,
        actor: str,
        expression_type: ActionType,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Empathize with observed expression/emotion."""
        with self._lock:
            # Mirror the expression
            activation = self._mirror.observe(actor, expression_type, parameters)

            # Infer emotional state
            emotional_inference = self._infer_emotion(expression_type, parameters)

            return {
                'actor': actor,
                'observed_expression': expression_type.name,
                'mirrored_activation': activation.activation_strength,
                'inferred_emotion': emotional_inference,
                'empathy_level': activation.activation_strength * 0.8
            }

    def _infer_emotion(
        self,
        expression_type: ActionType,
        parameters: Dict[str, Any]
    ) -> str:
        """Infer emotion from expression."""
        if expression_type == ActionType.EXPRESSION:
            # Simple inference from parameters
            valence = parameters.get('valence', 0)
            arousal = parameters.get('arousal', 0.5)

            if valence > 0.5:
                return "positive" if arousal < 0.5 else "excited"
            elif valence < -0.5:
                return "negative" if arousal < 0.5 else "distressed"
            else:
                return "neutral"

        return "unknown"


# ============================================================================
# IMITATION LEARNING
# ============================================================================

class ImitationLearning:
    """
    Learn through imitation.

    "Ba'el learns by imitating." — Ba'el
    """

    def __init__(
        self,
        repertoire: MotorRepertoire,
        mirror_system: MirrorNeuronSystem
    ):
        """Initialize imitation learning."""
        self._repertoire = repertoire
        self._mirror = mirror_system
        self._imitations: List[Imitation] = []
        self._imitation_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._imitation_counter += 1
        return f"imitation_{self._imitation_counter}"

    def imitate(
        self,
        observed: ObservedAction
    ) -> Imitation:
        """Imitate observed action."""
        with self._lock:
            # Mirror the observation
            activation = self._mirror.observe(
                observed.actor,
                observed.action_type,
                observed.parameters,
                observed.goal
            )

            if activation.motor_program_id == "none":
                # Need to learn new program
                new_program = self._learn_new_program(observed)
                executed = new_program
                accuracy = 0.5  # Initial attempt
            else:
                # Use existing program
                executed = self._repertoire.get_program(activation.motor_program_id)
                accuracy = activation.activation_strength

            imitation = Imitation(
                id=self._generate_id(),
                observed_action_id=observed.id,
                executed_program=executed,
                accuracy=accuracy
            )

            self._imitations.append(imitation)

            return imitation

    def _learn_new_program(self, observed: ObservedAction) -> MotorProgram:
        """Learn new motor program from observation."""
        with self._lock:
            # Create new program based on observation
            sequence = [f"step_{i}" for i in range(3)]  # Placeholder

            program = self._repertoire.add_program(
                action_type=observed.action_type,
                parameters={k: float(v) if isinstance(v, (int, float)) else 0.5
                           for k, v in observed.parameters.items()},
                sequence=sequence
            )

            return program

    def practice(
        self,
        program_id: str,
        repetitions: int = 5
    ) -> Dict[str, Any]:
        """Practice motor program."""
        with self._lock:
            program = self._repertoire.get_program(program_id)

            if not program:
                return {'error': 'Program not found'}

            # Simulate practice improvement
            improvement = min(0.3, repetitions * 0.02)

            return {
                'program': program_id,
                'repetitions': repetitions,
                'improvement': improvement
            }

    @property
    def imitations(self) -> List[Imitation]:
        return self._imitations.copy()


# ============================================================================
# MIRROR NEURON ENGINE
# ============================================================================

class MirrorNeuronEngine:
    """
    Complete mirror neuron system implementation.

    "Ba'el's mirror neurons fire." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._repertoire = MotorRepertoire()
        self._mirror = MirrorNeuronSystem(self._repertoire)
        self._understanding = ActionUnderstanding(self._mirror)
        self._imitation = ImitationLearning(self._repertoire, self._mirror)
        self._observation_counter = 0
        self._lock = threading.RLock()

    def _generate_obs_id(self) -> str:
        self._observation_counter += 1
        return f"obs_{self._observation_counter}"

    # Motor repertoire

    def add_motor_program(
        self,
        action_type: ActionType,
        parameters: Dict[str, float],
        sequence: List[str]
    ) -> MotorProgram:
        """Add motor program to repertoire."""
        return self._repertoire.add_program(action_type, parameters, sequence)

    def get_programs(self, action_type: ActionType = None) -> List[MotorProgram]:
        """Get motor programs."""
        if action_type:
            return self._repertoire.find_by_type(action_type)
        return self._repertoire.programs

    # Mirror system

    def observe(
        self,
        actor: str,
        action_type: ActionType,
        parameters: Dict[str, Any],
        goal: Optional[str] = None
    ) -> MirrorActivation:
        """Observe action."""
        return self._mirror.observe(actor, action_type, parameters, goal)

    def simulate(self) -> Optional[List[str]]:
        """Simulate current mirror activation."""
        return self._mirror.simulate()

    # Action understanding

    def understand(
        self,
        actor: str,
        action_type: ActionType,
        parameters: Dict[str, Any],
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Understand observed action."""
        return self._understanding.understand(actor, action_type, parameters, context)

    def empathize(
        self,
        actor: str,
        expression_type: ActionType,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Empathize with expression."""
        return self._understanding.empathize(actor, expression_type, parameters)

    # Imitation

    def imitate(
        self,
        actor: str,
        action_type: ActionType,
        parameters: Dict[str, Any],
        goal: Optional[str] = None
    ) -> Imitation:
        """Imitate observed action."""
        observed = ObservedAction(
            id=self._generate_obs_id(),
            actor=actor,
            action_type=action_type,
            parameters=parameters,
            goal=goal
        )
        return self._imitation.imitate(observed)

    def practice(self, program_id: str, repetitions: int = 5) -> Dict[str, Any]:
        """Practice motor program."""
        return self._imitation.practice(program_id, repetitions)

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'mirror_state': self._mirror.state.name,
            'programs': len(self._repertoire.programs),
            'imitations': len(self._imitation.imitations),
            'current_activation': self._mirror.current_activation is not None
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_mirror_neuron_engine() -> MirrorNeuronEngine:
    """Create mirror neuron engine."""
    return MirrorNeuronEngine()


def create_motor_repertoire() -> MotorRepertoire:
    """Create motor repertoire."""
    return MotorRepertoire()


def create_observed_action(
    actor: str,
    action_type: ActionType,
    parameters: Dict[str, Any],
    goal: Optional[str] = None
) -> ObservedAction:
    """Create observed action."""
    return ObservedAction(
        id=f"obs_{random.randint(1000, 9999)}",
        actor=actor,
        action_type=action_type,
        parameters=parameters,
        goal=goal
    )
