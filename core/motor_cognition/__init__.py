"""
BAEL Motor Cognition Engine
============================

Motor planning, action sequencing, and embodied simulation.

"Ba'el acts with precision." — Ba'el
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
import heapq

logger = logging.getLogger("BAEL.MotorCognition")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class MotorPrimitive(Enum):
    """Basic motor primitives."""
    REACH = auto()
    GRASP = auto()
    RELEASE = auto()
    PUSH = auto()
    PULL = auto()
    ROTATE = auto()
    MOVE = auto()
    LIFT = auto()
    PLACE = auto()
    PRESS = auto()


class EffectorType(Enum):
    """Types of effectors."""
    ARM = auto()
    HAND = auto()
    FINGER = auto()
    LEG = auto()
    HEAD = auto()
    BODY = auto()


class ActionState(Enum):
    """State of motor action."""
    PLANNED = auto()
    EXECUTING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class ConstraintType(Enum):
    """Types of motor constraints."""
    JOINT_LIMIT = auto()
    COLLISION = auto()
    FORCE_LIMIT = auto()
    SPEED_LIMIT = auto()
    COORDINATION = auto()


@dataclass
class JointState:
    """
    State of a joint.
    """
    name: str
    angle: float  # Current angle
    velocity: float = 0.0
    min_angle: float = -math.pi
    max_angle: float = math.pi
    max_velocity: float = 1.0


@dataclass
class EndEffectorState:
    """
    State of end effector (hand, tool, etc).
    """
    position: Tuple[float, float, float]
    orientation: Tuple[float, float, float, float]  # Quaternion
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class MotorCommand:
    """
    A motor command.
    """
    id: str
    primitive: MotorPrimitive
    effector: EffectorType
    target: Dict[str, Any]
    duration: float = 1.0
    force: float = 0.5
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MotorProgram:
    """
    A sequence of motor commands.
    """
    id: str
    name: str
    commands: List[MotorCommand]
    total_duration: float
    state: ActionState = ActionState.PLANNED


@dataclass
class ActionSchema:
    """
    An action schema (template for actions).
    """
    id: str
    name: str
    preconditions: Dict[str, Any]
    effects: Dict[str, Any]
    commands: List[MotorCommand]
    cost: float = 1.0


@dataclass
class Trajectory:
    """
    A trajectory through space.
    """
    id: str
    waypoints: List[Tuple[float, float, float]]
    durations: List[float]

    @property
    def total_duration(self) -> float:
        return sum(self.durations)

    def get_position_at(self, t: float) -> Tuple[float, float, float]:
        """Get position at time t."""
        if t <= 0:
            return self.waypoints[0]

        elapsed = 0.0
        for i, dur in enumerate(self.durations):
            if elapsed + dur >= t:
                # Interpolate
                frac = (t - elapsed) / dur if dur > 0 else 0
                p1 = self.waypoints[i]
                p2 = self.waypoints[i + 1] if i + 1 < len(self.waypoints) else p1

                return (
                    p1[0] + frac * (p2[0] - p1[0]),
                    p1[1] + frac * (p2[1] - p1[1]),
                    p1[2] + frac * (p2[2] - p1[2])
                )
            elapsed += dur

        return self.waypoints[-1]


@dataclass
class MotorPrediction:
    """
    Prediction about motor action outcome.
    """
    predicted_state: EndEffectorState
    predicted_duration: float
    confidence: float
    predicted_success: bool


# ============================================================================
# FORWARD MODEL
# ============================================================================

class ForwardModel:
    """
    Forward model: predict consequences of actions.

    "Ba'el predicts action outcomes." — Ba'el
    """

    def __init__(self):
        """Initialize forward model."""
        self._noise_level = 0.05
        self._lock = threading.RLock()

    def predict(
        self,
        current_state: EndEffectorState,
        command: MotorCommand
    ) -> MotorPrediction:
        """Predict result of motor command."""
        with self._lock:
            # Simplified prediction based on primitive
            new_pos = list(current_state.position)
            duration = command.duration
            success = True

            if command.primitive == MotorPrimitive.REACH:
                target = command.target.get('position', current_state.position)
                new_pos = [
                    target[0] + random.gauss(0, self._noise_level),
                    target[1] + random.gauss(0, self._noise_level),
                    target[2] + random.gauss(0, self._noise_level)
                ]

            elif command.primitive == MotorPrimitive.MOVE:
                delta = command.target.get('delta', (0, 0, 0))
                new_pos = [
                    current_state.position[0] + delta[0],
                    current_state.position[1] + delta[1],
                    current_state.position[2] + delta[2]
                ]

            elif command.primitive == MotorPrimitive.LIFT:
                height = command.target.get('height', 0.1)
                new_pos[2] = current_state.position[2] + height

            elif command.primitive == MotorPrimitive.PLACE:
                target = command.target.get('position', current_state.position)
                new_pos = list(target)

            # Add noise
            new_pos = [p + random.gauss(0, self._noise_level) for p in new_pos]

            # Success probability
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(new_pos, current_state.position)))
            if dist > 2.0:
                success = random.random() > 0.2

            return MotorPrediction(
                predicted_state=EndEffectorState(
                    position=tuple(new_pos),
                    orientation=current_state.orientation
                ),
                predicted_duration=duration * (1 + random.gauss(0, 0.1)),
                confidence=0.8 if success else 0.4,
                predicted_success=success
            )


# ============================================================================
# INVERSE MODEL
# ============================================================================

class InverseModel:
    """
    Inverse model: compute commands to achieve goals.

    "Ba'el plans motor commands." — Ba'el
    """

    def __init__(self):
        """Initialize inverse model."""
        self._command_counter = 0
        self._lock = threading.RLock()

    def _generate_command_id(self) -> str:
        self._command_counter += 1
        return f"cmd_{self._command_counter}"

    def compute_command(
        self,
        current_state: EndEffectorState,
        goal_state: EndEffectorState
    ) -> MotorCommand:
        """Compute motor command to reach goal state."""
        with self._lock:
            # Compute delta
            delta = (
                goal_state.position[0] - current_state.position[0],
                goal_state.position[1] - current_state.position[1],
                goal_state.position[2] - current_state.position[2]
            )

            distance = math.sqrt(sum(d ** 2 for d in delta))

            # Choose primitive based on goal
            if distance < 0.01:
                primitive = MotorPrimitive.GRASP  # Already there
            elif delta[2] > 0.1:
                primitive = MotorPrimitive.LIFT
            elif delta[2] < -0.1:
                primitive = MotorPrimitive.PLACE
            else:
                primitive = MotorPrimitive.REACH

            # Estimate duration based on distance
            duration = max(0.1, distance / 0.5)  # 0.5 units per second

            return MotorCommand(
                id=self._generate_command_id(),
                primitive=primitive,
                effector=EffectorType.ARM,
                target={'position': goal_state.position},
                duration=duration
            )


# ============================================================================
# TRAJECTORY PLANNER
# ============================================================================

class TrajectoryPlanner:
    """
    Plan trajectories through space.

    "Ba'el plots the path." — Ba'el
    """

    def __init__(self):
        """Initialize planner."""
        self._traj_counter = 0
        self._lock = threading.RLock()

    def _generate_traj_id(self) -> str:
        self._traj_counter += 1
        return f"traj_{self._traj_counter}"

    def plan_linear(
        self,
        start: Tuple[float, float, float],
        goal: Tuple[float, float, float],
        speed: float = 0.5
    ) -> Trajectory:
        """Plan linear trajectory."""
        with self._lock:
            distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(start, goal)))
            duration = distance / speed if speed > 0 else 1.0

            return Trajectory(
                id=self._generate_traj_id(),
                waypoints=[start, goal],
                durations=[duration]
            )

    def plan_via_points(
        self,
        waypoints: List[Tuple[float, float, float]],
        speed: float = 0.5
    ) -> Trajectory:
        """Plan trajectory through waypoints."""
        with self._lock:
            durations = []

            for i in range(len(waypoints) - 1):
                p1 = waypoints[i]
                p2 = waypoints[i + 1]
                dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))
                durations.append(dist / speed if speed > 0 else 1.0)

            return Trajectory(
                id=self._generate_traj_id(),
                waypoints=list(waypoints),
                durations=durations
            )

    def plan_obstacle_avoiding(
        self,
        start: Tuple[float, float, float],
        goal: Tuple[float, float, float],
        obstacles: List[Tuple[Tuple[float, float, float], float]],  # (center, radius)
        speed: float = 0.5
    ) -> Optional[Trajectory]:
        """Plan trajectory avoiding obstacles (simplified RRT-like)."""
        with self._lock:
            # Check direct path
            if self._path_clear(start, goal, obstacles):
                return self.plan_linear(start, goal, speed)

            # Try via points
            mid = (
                (start[0] + goal[0]) / 2,
                (start[1] + goal[1]) / 2,
                max(start[2], goal[2]) + 0.2  # Go higher
            )

            if (self._path_clear(start, mid, obstacles) and
                self._path_clear(mid, goal, obstacles)):
                return self.plan_via_points([start, mid, goal], speed)

            # More complex path
            waypoints = self._rrt_simple(start, goal, obstacles)
            if waypoints:
                return self.plan_via_points(waypoints, speed)

            return None

    def _path_clear(
        self,
        p1: Tuple[float, float, float],
        p2: Tuple[float, float, float],
        obstacles: List[Tuple[Tuple[float, float, float], float]]
    ) -> bool:
        """Check if path is clear of obstacles."""
        # Sample points along line
        samples = 10
        for i in range(samples + 1):
            t = i / samples
            point = (
                p1[0] + t * (p2[0] - p1[0]),
                p1[1] + t * (p2[1] - p1[1]),
                p1[2] + t * (p2[2] - p1[2])
            )

            for center, radius in obstacles:
                dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(point, center)))
                if dist < radius:
                    return False

        return True

    def _rrt_simple(
        self,
        start: Tuple[float, float, float],
        goal: Tuple[float, float, float],
        obstacles: List[Tuple[Tuple[float, float, float], float]],
        max_iter: int = 100
    ) -> Optional[List[Tuple[float, float, float]]]:
        """Simple RRT-like path planning."""
        tree = {start: None}
        step_size = 0.1

        for _ in range(max_iter):
            # Random sample (biased toward goal)
            if random.random() < 0.2:
                sample = goal
            else:
                sample = (
                    start[0] + random.uniform(-1, 1),
                    start[1] + random.uniform(-1, 1),
                    start[2] + random.uniform(-0.5, 0.5)
                )

            # Find nearest
            nearest = min(tree.keys(), key=lambda p:
                         sum((a - b) ** 2 for a, b in zip(p, sample)))

            # Extend toward sample
            delta = tuple(s - n for s, n in zip(sample, nearest))
            dist = math.sqrt(sum(d ** 2 for d in delta))

            if dist > step_size:
                new_point = tuple(
                    n + step_size * d / dist
                    for n, d in zip(nearest, delta)
                )
            else:
                new_point = sample

            # Check collision
            if self._path_clear(nearest, new_point, obstacles):
                tree[new_point] = nearest

                # Check if reached goal
                if sum((a - b) ** 2 for a, b in zip(new_point, goal)) < 0.01:
                    # Reconstruct path
                    path = [new_point]
                    node = nearest
                    while node is not None:
                        path.append(node)
                        node = tree[node]
                    return list(reversed(path)) + [goal]

        return None


# ============================================================================
# ACTION EXECUTOR
# ============================================================================

class ActionExecutor:
    """
    Execute motor programs.

    "Ba'el executes actions." — Ba'el
    """

    def __init__(self, forward_model: ForwardModel):
        """Initialize executor."""
        self._forward_model = forward_model
        self._current_state = EndEffectorState(
            position=(0, 0, 0),
            orientation=(1, 0, 0, 0)
        )
        self._lock = threading.RLock()

    def set_state(self, state: EndEffectorState) -> None:
        """Set current state."""
        self._current_state = state

    def get_state(self) -> EndEffectorState:
        """Get current state."""
        return self._current_state

    def execute_command(
        self,
        command: MotorCommand
    ) -> Tuple[bool, EndEffectorState]:
        """Execute single motor command."""
        with self._lock:
            prediction = self._forward_model.predict(self._current_state, command)

            # Simulate execution
            time.sleep(0.01)  # Small delay

            if prediction.predicted_success:
                self._current_state = prediction.predicted_state
                return True, self._current_state
            else:
                return False, self._current_state

    def execute_program(
        self,
        program: MotorProgram,
        callback: Callable[[int, MotorCommand], None] = None
    ) -> bool:
        """Execute motor program."""
        with self._lock:
            program.state = ActionState.EXECUTING

            for i, command in enumerate(program.commands):
                if callback:
                    callback(i, command)

                success, _ = self.execute_command(command)

                if not success:
                    program.state = ActionState.FAILED
                    return False

            program.state = ActionState.COMPLETED
            return True


# ============================================================================
# MOTOR COGNITION ENGINE
# ============================================================================

class MotorCognitionEngine:
    """
    Complete motor cognition engine.

    "Ba'el's motor mind." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._forward_model = ForwardModel()
        self._inverse_model = InverseModel()
        self._trajectory_planner = TrajectoryPlanner()
        self._executor = ActionExecutor(self._forward_model)

        self._schemas: Dict[str, ActionSchema] = {}
        self._programs: Dict[str, MotorProgram] = {}

        self._program_counter = 0
        self._schema_counter = 0
        self._lock = threading.RLock()

    def _generate_program_id(self) -> str:
        self._program_counter += 1
        return f"program_{self._program_counter}"

    def _generate_schema_id(self) -> str:
        self._schema_counter += 1
        return f"schema_{self._schema_counter}"

    # State

    def set_state(self, position: Tuple[float, float, float]) -> None:
        """Set current state."""
        self._executor.set_state(EndEffectorState(
            position=position,
            orientation=(1, 0, 0, 0)
        ))

    def get_state(self) -> EndEffectorState:
        """Get current state."""
        return self._executor.get_state()

    # Commands

    def create_command(
        self,
        primitive: MotorPrimitive,
        target: Dict[str, Any],
        effector: EffectorType = EffectorType.ARM
    ) -> MotorCommand:
        """Create motor command."""
        return self._inverse_model.compute_command(
            self._executor.get_state(),
            EndEffectorState(
                position=target.get('position', (0, 0, 0)),
                orientation=(1, 0, 0, 0)
            )
        )

    def compute_reach(
        self,
        target_position: Tuple[float, float, float]
    ) -> MotorCommand:
        """Compute command to reach position."""
        return self._inverse_model.compute_command(
            self._executor.get_state(),
            EndEffectorState(position=target_position, orientation=(1, 0, 0, 0))
        )

    # Prediction

    def predict_action(
        self,
        command: MotorCommand
    ) -> MotorPrediction:
        """Predict action outcome."""
        return self._forward_model.predict(self._executor.get_state(), command)

    # Trajectory planning

    def plan_trajectory(
        self,
        goal: Tuple[float, float, float]
    ) -> Trajectory:
        """Plan trajectory to goal."""
        return self._trajectory_planner.plan_linear(
            self._executor.get_state().position,
            goal
        )

    def plan_trajectory_avoiding(
        self,
        goal: Tuple[float, float, float],
        obstacles: List[Tuple[Tuple[float, float, float], float]]
    ) -> Optional[Trajectory]:
        """Plan trajectory avoiding obstacles."""
        return self._trajectory_planner.plan_obstacle_avoiding(
            self._executor.get_state().position,
            goal,
            obstacles
        )

    # Programs

    def create_program(
        self,
        name: str,
        commands: List[MotorCommand]
    ) -> MotorProgram:
        """Create motor program."""
        total = sum(c.duration for c in commands)

        program = MotorProgram(
            id=self._generate_program_id(),
            name=name,
            commands=commands,
            total_duration=total
        )

        self._programs[program.id] = program
        return program

    def execute_command(
        self,
        command: MotorCommand
    ) -> bool:
        """Execute single command."""
        success, _ = self._executor.execute_command(command)
        return success

    def execute_program(
        self,
        program_id: str
    ) -> bool:
        """Execute program by ID."""
        program = self._programs.get(program_id)
        if not program:
            return False
        return self._executor.execute_program(program)

    # Schemas

    def create_schema(
        self,
        name: str,
        preconditions: Dict[str, Any],
        effects: Dict[str, Any],
        commands: List[MotorCommand]
    ) -> ActionSchema:
        """Create action schema."""
        schema = ActionSchema(
            id=self._generate_schema_id(),
            name=name,
            preconditions=preconditions,
            effects=effects,
            commands=commands
        )

        self._schemas[schema.id] = schema
        return schema

    def apply_schema(
        self,
        schema_id: str
    ) -> bool:
        """Apply action schema."""
        schema = self._schemas.get(schema_id)
        if not schema:
            return False

        program = self.create_program(schema.name, schema.commands)
        return self.execute_program(program.id)

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'position': self._executor.get_state().position,
            'programs': len(self._programs),
            'schemas': len(self._schemas)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_motor_cognition_engine() -> MotorCognitionEngine:
    """Create motor cognition engine."""
    return MotorCognitionEngine()


def plan_reach(
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float]
) -> Dict[str, Any]:
    """Plan reach movement."""
    engine = create_motor_cognition_engine()
    engine.set_state(start)

    command = engine.compute_reach(goal)
    prediction = engine.predict_action(command)

    return {
        'primitive': command.primitive.name,
        'duration': command.duration,
        'predicted_success': prediction.predicted_success,
        'confidence': prediction.confidence
    }
