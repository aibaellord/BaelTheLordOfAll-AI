"""
⚡ SIMULATION ENGINE ⚡
======================
World simulation and prediction.

Features:
- State evolution simulation
- Monte Carlo methods
- Trajectory prediction
- What-if scenarios
"""

import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid


@dataclass
class SimulationState:
    """State of a simulation"""
    step: int = 0
    time: float = 0.0
    values: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def copy(self) -> 'SimulationState':
        """Create copy of state"""
        return SimulationState(
            step=self.step,
            time=self.time,
            values=dict(self.values),
            metadata=dict(self.metadata)
        )


@dataclass
class SimulationStep:
    """Single step in simulation"""
    from_state: SimulationState
    to_state: SimulationState
    action: Optional[str] = None
    transition_prob: float = 1.0
    reward: float = 0.0


@dataclass
class SimulationConfig:
    """Configuration for simulation"""
    max_steps: int = 1000
    time_step: float = 1.0
    stochastic: bool = True
    random_seed: Optional[int] = None
    record_trajectory: bool = True

    # Termination conditions
    terminate_on: Optional[Callable[[SimulationState], bool]] = None

    # Callbacks
    on_step: Optional[Callable[[SimulationStep], None]] = None


class Simulator:
    """
    General-purpose simulator.

    Simulates state evolution according to dynamics.
    """

    def __init__(
        self,
        dynamics: Callable[[SimulationState, Optional[str]], SimulationState],
        config: SimulationConfig = None
    ):
        """
        Initialize simulator.

        Args:
            dynamics: Function (state, action) -> next_state
            config: Simulation configuration
        """
        self.dynamics = dynamics
        self.config = config or SimulationConfig()

        if self.config.random_seed is not None:
            np.random.seed(self.config.random_seed)

        # Trajectory storage
        self.trajectory: List[SimulationStep] = []

    def step(
        self,
        state: SimulationState,
        action: Optional[str] = None
    ) -> SimulationState:
        """Execute single simulation step"""
        next_state = self.dynamics(state, action)
        next_state.step = state.step + 1
        next_state.time = state.time + self.config.time_step

        step = SimulationStep(
            from_state=state.copy(),
            to_state=next_state.copy(),
            action=action
        )

        if self.config.record_trajectory:
            self.trajectory.append(step)

        if self.config.on_step:
            self.config.on_step(step)

        return next_state

    def run(
        self,
        initial_state: SimulationState,
        actions: List[str] = None
    ) -> Tuple[SimulationState, List[SimulationStep]]:
        """Run full simulation"""
        self.trajectory = []
        state = initial_state.copy()
        action_idx = 0

        for _ in range(self.config.max_steps):
            # Check termination
            if self.config.terminate_on and self.config.terminate_on(state):
                break

            # Get action
            action = None
            if actions and action_idx < len(actions):
                action = actions[action_idx]
                action_idx += 1

            # Step
            state = self.step(state, action)

        return state, self.trajectory

    def rollout(
        self,
        initial_state: SimulationState,
        policy: Callable[[SimulationState], str],
        n_steps: int = None
    ) -> Tuple[SimulationState, float]:
        """Rollout with policy"""
        self.trajectory = []
        state = initial_state.copy()
        total_reward = 0.0

        steps = n_steps or self.config.max_steps

        for _ in range(steps):
            if self.config.terminate_on and self.config.terminate_on(state):
                break

            action = policy(state)
            state = self.step(state, action)

            if self.trajectory:
                total_reward += self.trajectory[-1].reward

        return state, total_reward


class MonteCarloSimulator:
    """
    Monte Carlo simulation for stochastic systems.
    """

    def __init__(
        self,
        dynamics: Callable[[SimulationState, Optional[str]], SimulationState],
        n_samples: int = 1000
    ):
        self.dynamics = dynamics
        self.n_samples = n_samples

    def estimate_distribution(
        self,
        initial_state: SimulationState,
        n_steps: int,
        variable: str
    ) -> Dict[str, float]:
        """Estimate distribution of variable after n steps"""
        samples = []

        for _ in range(self.n_samples):
            state = initial_state.copy()

            for _ in range(n_steps):
                state = self.dynamics(state, None)
                state.step += 1

            if variable in state.values:
                try:
                    samples.append(float(state.values[variable]))
                except (TypeError, ValueError):
                    pass

        if not samples:
            return {'error': 'No samples collected'}

        return {
            'mean': np.mean(samples),
            'std': np.std(samples),
            'min': np.min(samples),
            'max': np.max(samples),
            'median': np.median(samples),
            'n_samples': len(samples)
        }

    def estimate_probability(
        self,
        initial_state: SimulationState,
        condition: Callable[[SimulationState], bool],
        n_steps: int
    ) -> float:
        """Estimate probability of condition being true"""
        successes = 0

        for _ in range(self.n_samples):
            state = initial_state.copy()

            for _ in range(n_steps):
                state = self.dynamics(state, None)
                state.step += 1

            if condition(state):
                successes += 1

        return successes / self.n_samples

    def expected_value(
        self,
        initial_state: SimulationState,
        value_function: Callable[[SimulationState], float],
        n_steps: int
    ) -> Dict[str, float]:
        """Compute expected value"""
        values = []

        for _ in range(self.n_samples):
            state = initial_state.copy()

            for _ in range(n_steps):
                state = self.dynamics(state, None)
                state.step += 1

            values.append(value_function(state))

        return {
            'expected_value': np.mean(values),
            'std_error': np.std(values) / np.sqrt(len(values)),
            'confidence_interval': (
                np.percentile(values, 2.5),
                np.percentile(values, 97.5)
            )
        }

    def sensitivity_analysis(
        self,
        initial_state: SimulationState,
        parameter: str,
        parameter_range: List[float],
        output_variable: str,
        n_steps: int
    ) -> Dict[float, Dict[str, float]]:
        """Analyze sensitivity to parameter"""
        results = {}

        for param_value in parameter_range:
            # Set parameter
            state = initial_state.copy()
            state.values[parameter] = param_value

            # Run simulation
            dist = self.estimate_distribution(state, n_steps, output_variable)
            results[param_value] = dist

        return results


class PredictiveModel:
    """
    Predictive model for trajectory forecasting.
    """

    def __init__(self, history_length: int = 10):
        self.history_length = history_length

        # Store historical trajectories for learning
        self.trajectories: List[List[SimulationState]] = []

        # Simple prediction coefficients
        self.coefficients: Dict[str, np.ndarray] = {}

    def add_trajectory(self, trajectory: List[SimulationState]):
        """Add observed trajectory"""
        self.trajectories.append(trajectory)

        # Update model
        if len(self.trajectories) >= 5:
            self._fit()

    def _fit(self):
        """Fit prediction model to trajectories"""
        if not self.trajectories:
            return

        # Collect variable names
        variables = set()
        for traj in self.trajectories:
            for state in traj:
                variables.update(state.values.keys())

        # Fit linear model for each variable
        for var in variables:
            X_data = []
            y_data = []

            for traj in self.trajectories:
                for i in range(self.history_length, len(traj)):
                    # Features: past values
                    features = []
                    for j in range(self.history_length):
                        val = traj[i - self.history_length + j].values.get(var, 0)
                        try:
                            features.append(float(val))
                        except:
                            features.append(0)

                    # Target: current value
                    try:
                        target = float(traj[i].values.get(var, 0))
                    except:
                        continue

                    X_data.append(features)
                    y_data.append(target)

            if len(X_data) >= 10:
                X = np.array(X_data)
                y = np.array(y_data)

                # Simple least squares
                try:
                    self.coefficients[var] = np.linalg.lstsq(X, y, rcond=None)[0]
                except:
                    pass

    def predict(
        self,
        history: List[SimulationState],
        n_steps: int
    ) -> List[SimulationState]:
        """Predict future states"""
        if len(history) < self.history_length:
            return []

        predictions = []
        current_history = list(history[-self.history_length:])

        for step in range(n_steps):
            # Predict next state
            next_values = {}

            for var, coefs in self.coefficients.items():
                if len(coefs) != self.history_length:
                    continue

                features = []
                for state in current_history:
                    val = state.values.get(var, 0)
                    try:
                        features.append(float(val))
                    except:
                        features.append(0)

                next_values[var] = np.dot(coefs, features)

            next_state = SimulationState(
                step=history[-1].step + step + 1,
                time=history[-1].time + step + 1,
                values=next_values
            )

            predictions.append(next_state)

            # Update history
            current_history.pop(0)
            current_history.append(next_state)

        return predictions

    def predict_with_uncertainty(
        self,
        history: List[SimulationState],
        n_steps: int,
        n_samples: int = 100
    ) -> Dict[str, List[Dict[str, float]]]:
        """Predict with uncertainty quantification"""
        # Collect multiple predictions with noise
        all_predictions = defaultdict(list)

        for _ in range(n_samples):
            # Add noise to history
            noisy_history = []
            for state in history:
                noisy_values = {}
                for var, val in state.values.items():
                    try:
                        noisy_values[var] = float(val) + np.random.normal(0, 0.1)
                    except:
                        noisy_values[var] = val

                noisy_state = SimulationState(
                    step=state.step,
                    time=state.time,
                    values=noisy_values
                )
                noisy_history.append(noisy_state)

            # Predict
            preds = self.predict(noisy_history, n_steps)

            for i, pred in enumerate(preds):
                for var, val in pred.values.items():
                    all_predictions[(i, var)].append(val)

        # Aggregate
        results = {}
        for (step_idx, var), values in all_predictions.items():
            if var not in results:
                results[var] = []

            while len(results[var]) <= step_idx:
                results[var].append({})

            results[var][step_idx] = {
                'mean': np.mean(values),
                'std': np.std(values),
                'ci_low': np.percentile(values, 5),
                'ci_high': np.percentile(values, 95)
            }

        return results


# Export all
__all__ = [
    'SimulationState',
    'SimulationStep',
    'SimulationConfig',
    'Simulator',
    'MonteCarloSimulator',
    'PredictiveModel',
]
