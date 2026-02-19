"""
BAEL Embodied Cognition Engine
===============================

Cognition through body and environment interaction.

"Ba'el thinks through acting." — Ba'el
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

logger = logging.getLogger("BAEL.EmbodiedCognition")


T = TypeVar('T')


# ============================================================================
# BODY SCHEMA
# ============================================================================

class BodyPartType(Enum):
    """Types of body parts."""
    SENSOR = auto()     # Input sensors
    EFFECTOR = auto()   # Action actuators
    INTERNAL = auto()   # Internal state
    INTERFACE = auto()  # Environment interface


@dataclass
class BodyPart:
    """
    A part of the embodied agent.
    """
    id: str
    part_type: BodyPartType
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    capabilities: List[str] = field(default_factory=list)
    state: Dict[str, float] = field(default_factory=dict)
    active: bool = True

    def sense(self, environment: Dict[str, Any]) -> Dict[str, float]:
        """Sense environment (for sensors)."""
        if self.part_type != BodyPartType.SENSOR:
            return {}

        sensations = {}
        for cap in self.capabilities:
            if cap in environment:
                value = environment[cap]
                if isinstance(value, (int, float)):
                    sensations[cap] = float(value)
                else:
                    sensations[cap] = hash(str(value)) % 1000 / 1000.0

        self.state.update(sensations)
        return sensations

    def act(self, action: Dict[str, float]) -> Dict[str, float]:
        """Perform action (for effectors)."""
        if self.part_type != BodyPartType.EFFECTOR:
            return {}

        results = {}
        for cap in self.capabilities:
            if cap in action:
                magnitude = action[cap]
                # Simulate action effect
                results[cap] = magnitude * (0.8 + random.random() * 0.4)

        self.state.update(results)
        return results


class BodySchema:
    """
    Mental representation of the body.

    "Ba'el knows its body." — Ba'el
    """

    def __init__(self):
        """Initialize body schema."""
        self._parts: Dict[str, BodyPart] = {}
        self._connections: Dict[str, List[str]] = {}
        self._proprioception: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def add_part(self, part: BodyPart) -> None:
        """Add body part."""
        with self._lock:
            self._parts[part.id] = part
            self._connections[part.id] = []

    def connect_parts(self, part1_id: str, part2_id: str) -> bool:
        """Connect body parts."""
        with self._lock:
            if part1_id in self._parts and part2_id in self._parts:
                self._connections[part1_id].append(part2_id)
                self._connections[part2_id].append(part1_id)
                return True
            return False

    def sense_all(self, environment: Dict[str, Any]) -> Dict[str, Dict]:
        """Sense through all sensors."""
        with self._lock:
            sensations = {}

            for part_id, part in self._parts.items():
                if part.part_type == BodyPartType.SENSOR and part.active:
                    sensations[part_id] = part.sense(environment)

            return sensations

    def act_all(self, actions: Dict[str, Dict]) -> Dict[str, Dict]:
        """Perform actions through all effectors."""
        with self._lock:
            results = {}

            for part_id, action in actions.items():
                if part_id in self._parts:
                    part = self._parts[part_id]
                    if part.part_type == BodyPartType.EFFECTOR and part.active:
                        results[part_id] = part.act(action)

            return results

    def update_proprioception(self) -> Dict[str, Any]:
        """Update proprioceptive sense."""
        with self._lock:
            self._proprioception = {
                'part_states': {
                    p_id: p.state.copy()
                    for p_id, p in self._parts.items()
                },
                'active_parts': [
                    p_id for p_id, p in self._parts.items() if p.active
                ]
            }
            return self._proprioception.copy()

    def get_part(self, part_id: str) -> Optional[BodyPart]:
        """Get body part."""
        return self._parts.get(part_id)

    @property
    def state(self) -> Dict[str, Any]:
        """Get body schema state."""
        return {
            'parts': len(self._parts),
            'sensors': len([p for p in self._parts.values() if p.part_type == BodyPartType.SENSOR]),
            'effectors': len([p for p in self._parts.values() if p.part_type == BodyPartType.EFFECTOR]),
            'proprioception': self._proprioception.copy()
        }


# ============================================================================
# SENSORIMOTOR LOOP
# ============================================================================

@dataclass
class SensorimotorState:
    """State of the sensorimotor loop."""
    sensations: Dict[str, float]
    actions: Dict[str, float]
    predictions: Dict[str, float]
    errors: Dict[str, float]
    timestamp: float = field(default_factory=time.time)


class SensorimotorLoop:
    """
    Core sensorimotor processing loop.

    "Ba'el perceives through action." — Ba'el
    """

    def __init__(self, body: BodySchema):
        """Initialize loop."""
        self._body = body
        self._state_history: List[SensorimotorState] = []
        self._forward_model: Dict[str, Callable] = {}
        self._inverse_model: Dict[str, Callable] = {}
        self._lock = threading.RLock()

    def register_forward_model(
        self,
        name: str,
        model: Callable[[Dict, Dict], Dict]
    ) -> None:
        """
        Register forward model.

        Forward model: (state, action) -> predicted_next_state
        """
        with self._lock:
            self._forward_model[name] = model

    def register_inverse_model(
        self,
        name: str,
        model: Callable[[Dict, Dict], Dict]
    ) -> None:
        """
        Register inverse model.

        Inverse model: (current_state, desired_state) -> required_action
        """
        with self._lock:
            self._inverse_model[name] = model

    def predict_sensations(
        self,
        current_state: Dict[str, float],
        action: Dict[str, float]
    ) -> Dict[str, float]:
        """Predict sensations after action."""
        predictions = {}

        for name, model in self._forward_model.items():
            try:
                pred = model(current_state, action)
                predictions.update(pred)
            except Exception as e:
                logger.warning(f"Forward model {name} failed: {e}")

        return predictions

    def compute_action(
        self,
        current_state: Dict[str, float],
        desired_state: Dict[str, float]
    ) -> Dict[str, float]:
        """Compute action to reach desired state."""
        actions = {}

        for name, model in self._inverse_model.items():
            try:
                action = model(current_state, desired_state)
                actions.update(action)
            except Exception as e:
                logger.warning(f"Inverse model {name} failed: {e}")

        return actions

    def step(
        self,
        environment: Dict[str, Any],
        action: Optional[Dict[str, Dict]] = None
    ) -> SensorimotorState:
        """Execute one sensorimotor step."""
        with self._lock:
            # Sense
            sensations_raw = self._body.sense_all(environment)
            sensations = {}
            for part_id, senses in sensations_raw.items():
                for key, value in senses.items():
                    sensations[f"{part_id}_{key}"] = value

            # Act (if action provided)
            action_results = {}
            if action:
                results_raw = self._body.act_all(action)
                for part_id, results in results_raw.items():
                    for key, value in results.items():
                        action_results[f"{part_id}_{key}"] = value

            # Predict
            predictions = self.predict_sensations(
                sensations,
                action_results
            )

            # Calculate errors
            errors = {}
            for key in predictions:
                if key in sensations:
                    errors[key] = abs(predictions[key] - sensations[key])

            # Record state
            state = SensorimotorState(
                sensations=sensations,
                actions=action_results,
                predictions=predictions,
                errors=errors
            )
            self._state_history.append(state)

            # Keep history bounded
            if len(self._state_history) > 1000:
                self._state_history = self._state_history[-500:]

            return state

    @property
    def recent_states(self) -> List[SensorimotorState]:
        """Get recent states."""
        return self._state_history[-10:]


# ============================================================================
# AFFORDANCE
# ============================================================================

@dataclass
class Affordance:
    """
    An action possibility offered by the environment.

    "Ba'el sees possibilities." — Ba'el
    """
    id: str
    name: str
    object_id: str
    action_type: str
    requirements: Dict[str, Any] = field(default_factory=dict)
    estimated_outcome: Dict[str, float] = field(default_factory=dict)
    salience: float = 0.5

    def is_available(self, agent_capabilities: List[str]) -> bool:
        """Check if affordance is available to agent."""
        for req in self.requirements.get('capabilities', []):
            if req not in agent_capabilities:
                return False
        return True


class AffordanceDetector:
    """
    Detects affordances in the environment.

    "Ba'el perceives action possibilities." — Ba'el
    """

    def __init__(self):
        """Initialize detector."""
        self._templates: Dict[str, Callable] = {}
        self._detected: List[Affordance] = []
        self._lock = threading.RLock()

    def register_template(
        self,
        name: str,
        detector: Callable[[Dict[str, Any]], Optional[Affordance]]
    ) -> None:
        """Register affordance detection template."""
        with self._lock:
            self._templates[name] = detector

    def detect(self, environment: Dict[str, Any]) -> List[Affordance]:
        """Detect affordances in environment."""
        with self._lock:
            self._detected = []

            for name, detector in self._templates.items():
                try:
                    affordance = detector(environment)
                    if affordance:
                        self._detected.append(affordance)
                except Exception as e:
                    logger.warning(f"Affordance detector {name} failed: {e}")

            return self._detected.copy()

    def filter_available(
        self,
        affordances: List[Affordance],
        capabilities: List[str]
    ) -> List[Affordance]:
        """Filter affordances by agent capabilities."""
        return [a for a in affordances if a.is_available(capabilities)]

    def most_salient(self, n: int = 3) -> List[Affordance]:
        """Get most salient affordances."""
        sorted_aff = sorted(self._detected, key=lambda a: a.salience, reverse=True)
        return sorted_aff[:n]


# ============================================================================
# MOTOR IMAGERY
# ============================================================================

class MotorImagery:
    """
    Mental simulation of actions.

    "Ba'el imagines before acting." — Ba'el
    """

    def __init__(self, body: BodySchema):
        """Initialize motor imagery."""
        self._body = body
        self._simulated_states: List[Dict] = []
        self._lock = threading.RLock()

    def simulate_action(
        self,
        action: Dict[str, Dict],
        duration: int = 10
    ) -> List[Dict]:
        """Mentally simulate an action sequence."""
        with self._lock:
            self._simulated_states = []

            # Create simulated body state
            simulated_state = {
                part_id: part.state.copy()
                for part_id, part in self._body._parts.items()
            }

            for step in range(duration):
                # Apply action effects mentally
                for part_id, part_action in action.items():
                    if part_id in simulated_state:
                        for key, value in part_action.items():
                            # Simulate gradual change
                            current = simulated_state[part_id].get(key, 0)
                            simulated_state[part_id][key] = current + value * 0.1

                self._simulated_states.append({
                    'step': step,
                    'state': {k: v.copy() for k, v in simulated_state.items()}
                })

            return self._simulated_states.copy()

    def evaluate_imagined(self, goal_state: Dict[str, Dict]) -> float:
        """Evaluate how close imagined end-state is to goal."""
        if not self._simulated_states:
            return 0.0

        final_state = self._simulated_states[-1]['state']

        # Calculate similarity
        total_diff = 0.0
        count = 0

        for part_id, goal_values in goal_state.items():
            if part_id in final_state:
                for key, goal_value in goal_values.items():
                    if key in final_state[part_id]:
                        diff = abs(final_state[part_id][key] - goal_value)
                        total_diff += diff
                        count += 1

        if count == 0:
            return 0.0

        avg_diff = total_diff / count
        return max(0, 1 - avg_diff)


# ============================================================================
# PERIPERSONAL SPACE
# ============================================================================

class PeripersonalSpace:
    """
    Space immediately surrounding the body.

    "Ba'el guards its space." — Ba'el
    """

    def __init__(self, radius: float = 1.0):
        """Initialize peripersonal space."""
        self._radius = radius
        self._objects: Dict[str, Dict] = {}
        self._intrusions: List[Dict] = []
        self._lock = threading.RLock()

    def update_object(
        self,
        obj_id: str,
        position: Tuple[float, float, float],
        velocity: Optional[Tuple[float, float, float]] = None
    ) -> None:
        """Update object in/near peripersonal space."""
        with self._lock:
            distance = math.sqrt(sum(p*p for p in position))

            self._objects[obj_id] = {
                'position': position,
                'velocity': velocity or (0, 0, 0),
                'distance': distance,
                'in_space': distance <= self._radius
            }

            # Check for intrusion
            if distance <= self._radius:
                self._intrusions.append({
                    'object_id': obj_id,
                    'distance': distance,
                    'timestamp': time.time()
                })

    def approaching_objects(self) -> List[str]:
        """Get objects approaching the body."""
        approaching = []

        for obj_id, obj in self._objects.items():
            if obj['velocity']:
                # Simple check: velocity toward origin
                pos = obj['position']
                vel = obj['velocity']

                # Dot product of position and velocity (negative = approaching)
                dot = sum(p * v for p, v in zip(pos, vel))

                if dot < 0:
                    approaching.append(obj_id)

        return approaching

    def objects_in_reach(self) -> List[str]:
        """Get objects within reach."""
        return [
            obj_id for obj_id, obj in self._objects.items()
            if obj['in_space']
        ]

    def clear_intrusions(self) -> None:
        """Clear intrusion history."""
        self._intrusions = []

    @property
    def intrusion_count(self) -> int:
        """Get number of recent intrusions."""
        return len(self._intrusions)


# ============================================================================
# EMBODIED COGNITION ENGINE
# ============================================================================

class EmbodiedCognitionEngine:
    """
    Complete embodied cognition system.

    "Ba'el is embodied." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._body = BodySchema()
        self._sensorimotor = SensorimotorLoop(self._body)
        self._affordance_detector = AffordanceDetector()
        self._motor_imagery = MotorImagery(self._body)
        self._peripersonal_space = PeripersonalSpace()
        self._lock = threading.RLock()

        # Build default body
        self._build_default_body()

    def _build_default_body(self) -> None:
        """Build default body."""
        # Sensors
        self._body.add_part(BodyPart(
            id="eyes",
            part_type=BodyPartType.SENSOR,
            position=(0, 0, 0.5),
            capabilities=["light", "color", "motion", "depth"]
        ))

        self._body.add_part(BodyPart(
            id="hands_sensor",
            part_type=BodyPartType.SENSOR,
            position=(0.5, 0, 0),
            capabilities=["touch", "pressure", "temperature"]
        ))

        # Effectors
        self._body.add_part(BodyPart(
            id="hands_effector",
            part_type=BodyPartType.EFFECTOR,
            position=(0.5, 0, 0),
            capabilities=["grasp", "push", "pull", "point"]
        ))

        self._body.add_part(BodyPart(
            id="legs",
            part_type=BodyPartType.EFFECTOR,
            position=(0, 0, -0.5),
            capabilities=["walk", "run", "jump"]
        ))

        # Connect parts
        self._body.connect_parts("eyes", "hands_sensor")
        self._body.connect_parts("hands_sensor", "hands_effector")

        # Register simple forward/inverse models
        self._sensorimotor.register_forward_model(
            "simple_forward",
            lambda state, action: {
                k: state.get(k, 0) + action.get(k, 0) * 0.1
                for k in set(state.keys()) | set(action.keys())
            }
        )

        self._sensorimotor.register_inverse_model(
            "simple_inverse",
            lambda current, desired: {
                k: (desired.get(k, 0) - current.get(k, 0)) * 2
                for k in set(current.keys()) | set(desired.keys())
            }
        )

    def sense_and_act(
        self,
        environment: Dict[str, Any],
        goal: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Main sense-act cycle."""
        with self._lock:
            # Sense
            state = self._sensorimotor.step(environment)

            # Detect affordances
            affordances = self._affordance_detector.detect(environment)

            # Update proprioception
            proprioception = self._body.update_proprioception()

            # Compute action if goal provided
            action = None
            if goal:
                action = self._sensorimotor.compute_action(
                    state.sensations,
                    goal
                )

            return {
                'sensations': state.sensations,
                'predictions': state.predictions,
                'errors': state.errors,
                'affordances': [a.name for a in affordances],
                'proprioception': proprioception,
                'computed_action': action
            }

    def imagine_action(
        self,
        action: Dict[str, Dict],
        goal: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """Use motor imagery to plan action."""
        # Simulate
        trajectory = self._motor_imagery.simulate_action(action)

        # Evaluate
        success = self._motor_imagery.evaluate_imagined(goal)

        return {
            'trajectory_length': len(trajectory),
            'estimated_success': success,
            'final_state': trajectory[-1] if trajectory else None
        }

    def add_affordance_detector(
        self,
        name: str,
        detector: Callable[[Dict[str, Any]], Optional[Affordance]]
    ) -> None:
        """Add affordance detector."""
        self._affordance_detector.register_template(name, detector)

    def track_object(
        self,
        obj_id: str,
        position: Tuple[float, float, float],
        velocity: Optional[Tuple[float, float, float]] = None
    ) -> None:
        """Track object in peripersonal space."""
        self._peripersonal_space.update_object(obj_id, position, velocity)

    def get_reachable(self) -> List[str]:
        """Get reachable objects."""
        return self._peripersonal_space.objects_in_reach()

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'body': self._body.state,
            'recent_states': len(self._sensorimotor._state_history),
            'peripersonal_space': {
                'objects': len(self._peripersonal_space._objects),
                'intrusions': self._peripersonal_space.intrusion_count
            }
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_embodied_cognition_engine() -> EmbodiedCognitionEngine:
    """Create embodied cognition engine."""
    return EmbodiedCognitionEngine()


def create_body_schema() -> BodySchema:
    """Create body schema."""
    return BodySchema()


def create_sensorimotor_loop(body: BodySchema) -> SensorimotorLoop:
    """Create sensorimotor loop."""
    return SensorimotorLoop(body)


def create_affordance_detector() -> AffordanceDetector:
    """Create affordance detector."""
    return AffordanceDetector()


def create_affordance(
    name: str,
    object_id: str,
    action_type: str
) -> Affordance:
    """Create affordance."""
    return Affordance(
        id=f"aff_{time.time()}",
        name=name,
        object_id=object_id,
        action_type=action_type
    )
