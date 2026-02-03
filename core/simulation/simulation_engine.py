#!/usr/bin/env python3
"""
BAEL - Simulation Engine
Advanced world simulation and scenario modeling.

Features:
- World state simulation
- Entity simulation
- Event simulation
- Outcome prediction
- Monte Carlo simulation
- What-if analysis
- Scenario modeling
- Time progression
"""

import asyncio
import copy
import hashlib
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class SimulationType(Enum):
    """Simulation types."""
    DISCRETE_EVENT = "discrete_event"
    CONTINUOUS = "continuous"
    AGENT_BASED = "agent_based"
    MONTE_CARLO = "monte_carlo"
    HYBRID = "hybrid"


class EntityType(Enum):
    """Simulated entity types."""
    AGENT = "agent"
    RESOURCE = "resource"
    ENVIRONMENT = "environment"
    PROCESS = "process"
    EVENT_SOURCE = "event_source"


class EventType(Enum):
    """Simulation event types."""
    STATE_CHANGE = "state_change"
    INTERACTION = "interaction"
    SPAWN = "spawn"
    DESTROY = "destroy"
    TRIGGER = "trigger"
    SCHEDULED = "scheduled"


class SimulationStatus(Enum):
    """Simulation status."""
    CREATED = "created"
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class TimeUnit(Enum):
    """Time units."""
    TICK = "tick"
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SimulationTime:
    """Simulation time."""
    ticks: int = 0
    time_unit: TimeUnit = TimeUnit.TICK
    real_start: Optional[datetime] = None
    time_scale: float = 1.0  # Simulation time / real time

    def advance(self, delta: int = 1) -> None:
        """Advance time."""
        self.ticks += delta

    def to_seconds(self) -> float:
        """Convert to seconds."""
        multipliers = {
            TimeUnit.TICK: 1.0,
            TimeUnit.SECOND: 1.0,
            TimeUnit.MINUTE: 60.0,
            TimeUnit.HOUR: 3600.0,
            TimeUnit.DAY: 86400.0,
        }
        return self.ticks * multipliers.get(self.time_unit, 1.0)


@dataclass
class EntityState:
    """Entity state."""
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: EntityType = EntityType.AGENT
    name: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    properties: Dict[str, Any] = field(default_factory=dict)
    active: bool = True
    created_at: int = 0
    updated_at: int = 0


@dataclass
class SimulationEvent:
    """Simulation event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.STATE_CHANGE
    source_id: Optional[str] = None
    target_id: Optional[str] = None
    scheduled_time: int = 0
    data: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    processed: bool = False


@dataclass
class WorldState:
    """World state snapshot."""
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    time: int = 0
    entities: Dict[str, EntityState] = field(default_factory=dict)
    global_properties: Dict[str, Any] = field(default_factory=dict)
    checksum: str = ""


@dataclass
class ScenarioConfig:
    """Scenario configuration."""
    scenario_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    initial_state: Optional[WorldState] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    duration: int = 1000


@dataclass
class SimulationResult:
    """Simulation result."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scenario_id: str = ""
    final_state: Optional[WorldState] = None
    history: List[WorldState] = field(default_factory=list)
    events_processed: int = 0
    duration_ticks: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None


@dataclass
class MonteCarloResult:
    """Monte Carlo simulation result."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    iterations: int = 0
    outcomes: List[Dict[str, Any]] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    confidence_intervals: Dict[str, Tuple[float, float]] = field(default_factory=dict)


@dataclass
class SimulationStats:
    """Simulation engine statistics."""
    total_simulations: int = 0
    total_events_processed: int = 0
    total_ticks_simulated: int = 0
    monte_carlo_runs: int = 0


# =============================================================================
# ENTITY BEHAVIOR
# =============================================================================

class EntityBehavior(ABC):
    """Abstract entity behavior."""

    @abstractmethod
    def update(
        self,
        entity: EntityState,
        world: WorldState,
        dt: float
    ) -> List[SimulationEvent]:
        """Update entity and return generated events."""
        pass


class StaticBehavior(EntityBehavior):
    """Static entity behavior."""

    def update(
        self,
        entity: EntityState,
        world: WorldState,
        dt: float
    ) -> List[SimulationEvent]:
        return []


class MovingBehavior(EntityBehavior):
    """Moving entity behavior."""

    def update(
        self,
        entity: EntityState,
        world: WorldState,
        dt: float
    ) -> List[SimulationEvent]:
        # Update position based on velocity
        vx, vy, vz = entity.velocity
        x, y, z = entity.position

        entity.position = (
            x + vx * dt,
            y + vy * dt,
            z + vz * dt
        )

        return []


class ResourceBehavior(EntityBehavior):
    """Resource entity behavior."""

    def __init__(
        self,
        regeneration_rate: float = 0.01,
        max_value: float = 100.0
    ):
        self._regen_rate = regeneration_rate
        self._max_value = max_value

    def update(
        self,
        entity: EntityState,
        world: WorldState,
        dt: float
    ) -> List[SimulationEvent]:
        current = entity.properties.get("value", 0)
        new_value = min(self._max_value, current + self._regen_rate * dt)
        entity.properties["value"] = new_value

        return []


class RandomWalkBehavior(EntityBehavior):
    """Random walk behavior."""

    def __init__(self, step_size: float = 1.0):
        self._step_size = step_size

    def update(
        self,
        entity: EntityState,
        world: WorldState,
        dt: float
    ) -> List[SimulationEvent]:
        x, y, z = entity.position

        dx = random.gauss(0, self._step_size) * dt
        dy = random.gauss(0, self._step_size) * dt
        dz = 0  # Keep 2D for simplicity

        entity.position = (x + dx, y + dy, z + dz)

        return []


# =============================================================================
# EVENT QUEUE
# =============================================================================

class EventQueue:
    """Priority event queue."""

    def __init__(self):
        self._events: List[SimulationEvent] = []
        self._event_count = 0

    def schedule(self, event: SimulationEvent) -> None:
        """Schedule event."""
        self._events.append(event)
        self._events.sort(key=lambda e: (e.scheduled_time, -e.priority))
        self._event_count += 1

    def pop_due_events(self, current_time: int) -> List[SimulationEvent]:
        """Pop all events due at or before current time."""
        due = []

        while self._events and self._events[0].scheduled_time <= current_time:
            event = self._events.pop(0)
            event.processed = True
            due.append(event)

        return due

    def peek_next_time(self) -> Optional[int]:
        """Peek at next event time."""
        if self._events:
            return self._events[0].scheduled_time
        return None

    def clear(self) -> None:
        """Clear queue."""
        self._events.clear()

    def __len__(self) -> int:
        return len(self._events)


# =============================================================================
# WORLD SIMULATOR
# =============================================================================

class WorldSimulator:
    """World state simulator."""

    def __init__(self):
        self._world: Optional[WorldState] = None
        self._behaviors: Dict[str, EntityBehavior] = {}
        self._event_queue = EventQueue()
        self._time = SimulationTime()
        self._history: deque = deque(maxlen=1000)
        self._event_handlers: Dict[EventType, List[Callable]] = defaultdict(list)

    def initialize(self, initial_state: Optional[WorldState] = None) -> None:
        """Initialize simulation."""
        if initial_state:
            self._world = copy.deepcopy(initial_state)
        else:
            self._world = WorldState()

        self._time = SimulationTime()
        self._event_queue.clear()
        self._history.clear()

    def set_behavior(
        self,
        entity_id: str,
        behavior: EntityBehavior
    ) -> None:
        """Set entity behavior."""
        self._behaviors[entity_id] = behavior

    def add_entity(self, entity: EntityState) -> None:
        """Add entity to world."""
        if self._world:
            entity.created_at = self._time.ticks
            entity.updated_at = self._time.ticks
            self._world.entities[entity.entity_id] = entity

    def remove_entity(self, entity_id: str) -> None:
        """Remove entity from world."""
        if self._world and entity_id in self._world.entities:
            del self._world.entities[entity_id]
            self._behaviors.pop(entity_id, None)

    def schedule_event(self, event: SimulationEvent) -> None:
        """Schedule simulation event."""
        self._event_queue.schedule(event)

    def register_handler(
        self,
        event_type: EventType,
        handler: Callable[[SimulationEvent, WorldState], None]
    ) -> None:
        """Register event handler."""
        self._event_handlers[event_type].append(handler)

    def step(self, dt: float = 1.0) -> List[SimulationEvent]:
        """Advance simulation by dt."""
        if not self._world:
            return []

        processed_events = []

        # Advance time
        self._time.advance(int(dt))
        self._world.time = self._time.ticks

        # Process due events
        due_events = self._event_queue.pop_due_events(self._time.ticks)
        for event in due_events:
            self._process_event(event)
            processed_events.append(event)

        # Update entities
        new_events = []
        for entity_id, entity in list(self._world.entities.items()):
            if not entity.active:
                continue

            behavior = self._behaviors.get(entity_id, StaticBehavior())
            events = behavior.update(entity, self._world, dt)
            new_events.extend(events)
            entity.updated_at = self._time.ticks

        # Schedule new events
        for event in new_events:
            self.schedule_event(event)

        # Save snapshot
        self._save_snapshot()

        return processed_events

    def _process_event(self, event: SimulationEvent) -> None:
        """Process simulation event."""
        handlers = self._event_handlers.get(event.event_type, [])
        for handler in handlers:
            handler(event, self._world)

        # Built-in event handling
        if event.event_type == EventType.STATE_CHANGE:
            if event.target_id and event.target_id in self._world.entities:
                entity = self._world.entities[event.target_id]
                for key, value in event.data.items():
                    entity.properties[key] = value

        elif event.event_type == EventType.SPAWN:
            entity_data = event.data.get("entity")
            if entity_data:
                entity = EntityState(**entity_data)
                self.add_entity(entity)

        elif event.event_type == EventType.DESTROY:
            if event.target_id:
                self.remove_entity(event.target_id)

    def _save_snapshot(self) -> None:
        """Save world state snapshot."""
        if self._world:
            snapshot = copy.deepcopy(self._world)
            snapshot.checksum = self._compute_checksum(snapshot)
            self._history.append(snapshot)

    def _compute_checksum(self, state: WorldState) -> str:
        """Compute state checksum."""
        data = f"{state.time}:{len(state.entities)}"
        return hashlib.md5(data.encode()).hexdigest()[:8]

    def get_state(self) -> Optional[WorldState]:
        """Get current world state."""
        return copy.deepcopy(self._world) if self._world else None

    def get_history(self) -> List[WorldState]:
        """Get state history."""
        return list(self._history)

    def get_time(self) -> int:
        """Get current simulation time."""
        return self._time.ticks


# =============================================================================
# SCENARIO RUNNER
# =============================================================================

class ScenarioRunner:
    """Run simulation scenarios."""

    def __init__(self):
        self._simulator = WorldSimulator()

    def run(
        self,
        scenario: ScenarioConfig,
        record_history: bool = True,
        step_size: float = 1.0
    ) -> SimulationResult:
        """Run scenario."""
        result = SimulationResult(scenario_id=scenario.scenario_id)

        try:
            # Initialize
            self._simulator.initialize(scenario.initial_state)

            # Apply parameters
            if self._simulator._world:
                self._simulator._world.global_properties.update(scenario.parameters)

            # Run simulation
            events_processed = 0
            history = []

            for tick in range(scenario.duration):
                events = self._simulator.step(step_size)
                events_processed += len(events)

                if record_history and tick % 10 == 0:
                    state = self._simulator.get_state()
                    if state:
                        history.append(state)

                # Check constraints
                if not self._check_constraints(scenario.constraints):
                    break

            result.final_state = self._simulator.get_state()
            result.history = history if record_history else []
            result.events_processed = events_processed
            result.duration_ticks = self._simulator.get_time()
            result.success = True

            # Compute metrics
            result.metrics = self._compute_metrics()

        except Exception as e:
            result.success = False
            result.error = str(e)

        return result

    def _check_constraints(self, constraints: Dict[str, Any]) -> bool:
        """Check if constraints are satisfied."""
        state = self._simulator.get_state()
        if not state:
            return True

        for key, value in constraints.items():
            if key == "max_entities":
                if len(state.entities) > value:
                    return False
            elif key == "min_entities":
                if len(state.entities) < value:
                    return False

        return True

    def _compute_metrics(self) -> Dict[str, Any]:
        """Compute simulation metrics."""
        state = self._simulator.get_state()
        if not state:
            return {}

        return {
            "entity_count": len(state.entities),
            "active_entities": sum(1 for e in state.entities.values() if e.active),
            "simulation_time": state.time,
        }


# =============================================================================
# MONTE CARLO SIMULATOR
# =============================================================================

class MonteCarloSimulator:
    """Monte Carlo simulation."""

    def __init__(self, base_scenario: ScenarioConfig):
        self._base_scenario = base_scenario
        self._runner = ScenarioRunner()
        self._outcomes: List[Dict[str, Any]] = []

    def run(
        self,
        iterations: int,
        parameter_distributions: Dict[str, Callable[[], Any]],
        outcome_extractor: Optional[Callable[[SimulationResult], Dict[str, Any]]] = None
    ) -> MonteCarloResult:
        """Run Monte Carlo simulation."""
        self._outcomes.clear()

        for i in range(iterations):
            # Create scenario with sampled parameters
            scenario = copy.deepcopy(self._base_scenario)

            for param, distribution in parameter_distributions.items():
                scenario.parameters[param] = distribution()

            # Run simulation
            result = self._runner.run(scenario, record_history=False)

            # Extract outcome
            if outcome_extractor:
                outcome = outcome_extractor(result)
            else:
                outcome = self._default_outcome_extractor(result)

            outcome["iteration"] = i
            outcome["parameters"] = dict(scenario.parameters)
            self._outcomes.append(outcome)

        # Compute statistics
        statistics = self._compute_statistics()
        confidence_intervals = self._compute_confidence_intervals()

        return MonteCarloResult(
            iterations=iterations,
            outcomes=self._outcomes,
            statistics=statistics,
            confidence_intervals=confidence_intervals
        )

    def _default_outcome_extractor(
        self,
        result: SimulationResult
    ) -> Dict[str, Any]:
        """Default outcome extractor."""
        return {
            "success": result.success,
            "duration": result.duration_ticks,
            "events": result.events_processed,
            **result.metrics
        }

    def _compute_statistics(self) -> Dict[str, Any]:
        """Compute outcome statistics."""
        if not self._outcomes:
            return {}

        stats = {}

        # Collect numeric values
        numeric_keys = set()
        for outcome in self._outcomes:
            for key, value in outcome.items():
                if isinstance(value, (int, float)) and key != "iteration":
                    numeric_keys.add(key)

        # Compute stats for each numeric field
        for key in numeric_keys:
            values = [o.get(key, 0) for o in self._outcomes if key in o]
            if values:
                stats[key] = {
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "std": self._std(values),
                }

        # Success rate
        successes = sum(1 for o in self._outcomes if o.get("success", False))
        stats["success_rate"] = successes / len(self._outcomes)

        return stats

    def _compute_confidence_intervals(
        self,
        confidence: float = 0.95
    ) -> Dict[str, Tuple[float, float]]:
        """Compute confidence intervals."""
        if not self._outcomes:
            return {}

        intervals = {}
        z = 1.96  # For 95% confidence

        numeric_keys = set()
        for outcome in self._outcomes:
            for key, value in outcome.items():
                if isinstance(value, (int, float)) and key != "iteration":
                    numeric_keys.add(key)

        for key in numeric_keys:
            values = [o.get(key, 0) for o in self._outcomes if key in o]
            if values:
                mean = sum(values) / len(values)
                std = self._std(values)
                margin = z * std / math.sqrt(len(values))
                intervals[key] = (mean - margin, mean + margin)

        return intervals

    def _std(self, values: List[float]) -> float:
        """Compute standard deviation."""
        if len(values) < 2:
            return 0.0

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)


# =============================================================================
# WHAT-IF ANALYZER
# =============================================================================

class WhatIfAnalyzer:
    """What-if analysis."""

    def __init__(self):
        self._runner = ScenarioRunner()

    def analyze(
        self,
        base_scenario: ScenarioConfig,
        variations: List[Dict[str, Any]],
        comparison_metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Analyze what-if scenarios."""
        results = {}

        # Run base scenario
        base_result = self._runner.run(base_scenario)
        results["base"] = {
            "scenario": base_scenario.name,
            "result": base_result,
            "metrics": base_result.metrics
        }

        # Run variations
        for i, variation in enumerate(variations):
            varied_scenario = copy.deepcopy(base_scenario)
            varied_scenario.scenario_id = str(uuid.uuid4())
            varied_scenario.name = f"variation_{i}"
            varied_scenario.parameters.update(variation)

            result = self._runner.run(varied_scenario)
            results[f"variation_{i}"] = {
                "scenario": varied_scenario.name,
                "changes": variation,
                "result": result,
                "metrics": result.metrics
            }

        # Compute comparisons
        comparisons = self._compute_comparisons(results, comparison_metrics)

        return {
            "results": results,
            "comparisons": comparisons
        }

    def _compute_comparisons(
        self,
        results: Dict[str, Any],
        metrics: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Compute result comparisons."""
        comparisons = {}

        base_metrics = results.get("base", {}).get("metrics", {})

        if metrics is None:
            metrics = list(base_metrics.keys())

        for key, data in results.items():
            if key == "base":
                continue

            var_metrics = data.get("metrics", {})
            comparison = {}

            for metric in metrics:
                base_val = base_metrics.get(metric, 0)
                var_val = var_metrics.get(metric, 0)

                if isinstance(base_val, (int, float)) and isinstance(var_val, (int, float)):
                    comparison[metric] = {
                        "base": base_val,
                        "variation": var_val,
                        "difference": var_val - base_val,
                        "percent_change": (
                            (var_val - base_val) / base_val * 100
                            if base_val != 0 else 0
                        )
                    }

            comparisons[key] = comparison

        return comparisons


# =============================================================================
# SIMULATION ENGINE
# =============================================================================

class SimulationEngine:
    """
    Simulation Engine for BAEL.

    Advanced world simulation and scenario modeling.
    """

    def __init__(self):
        self._simulators: Dict[str, WorldSimulator] = {}
        self._scenarios: Dict[str, ScenarioConfig] = {}
        self._results: Dict[str, SimulationResult] = {}
        self._stats = SimulationStats()

    # -------------------------------------------------------------------------
    # SIMULATOR MANAGEMENT
    # -------------------------------------------------------------------------

    def create_simulator(
        self,
        name: str
    ) -> WorldSimulator:
        """Create new simulator."""
        simulator = WorldSimulator()
        self._simulators[name] = simulator
        return simulator

    def get_simulator(self, name: str) -> Optional[WorldSimulator]:
        """Get simulator by name."""
        return self._simulators.get(name)

    def initialize_simulator(
        self,
        name: str,
        initial_state: Optional[WorldState] = None
    ) -> bool:
        """Initialize simulator."""
        simulator = self._simulators.get(name)
        if simulator:
            simulator.initialize(initial_state)
            return True
        return False

    # -------------------------------------------------------------------------
    # ENTITY MANAGEMENT
    # -------------------------------------------------------------------------

    def add_entity(
        self,
        simulator_name: str,
        entity_type: EntityType,
        name: str,
        position: Tuple[float, float, float] = (0, 0, 0),
        properties: Optional[Dict[str, Any]] = None,
        behavior: Optional[EntityBehavior] = None
    ) -> Optional[EntityState]:
        """Add entity to simulator."""
        simulator = self._simulators.get(simulator_name)
        if not simulator:
            return None

        entity = EntityState(
            entity_type=entity_type,
            name=name,
            position=position,
            properties=properties or {}
        )

        simulator.add_entity(entity)

        if behavior:
            simulator.set_behavior(entity.entity_id, behavior)

        return entity

    def remove_entity(
        self,
        simulator_name: str,
        entity_id: str
    ) -> bool:
        """Remove entity from simulator."""
        simulator = self._simulators.get(simulator_name)
        if simulator:
            simulator.remove_entity(entity_id)
            return True
        return False

    # -------------------------------------------------------------------------
    # SIMULATION CONTROL
    # -------------------------------------------------------------------------

    def step(
        self,
        simulator_name: str,
        dt: float = 1.0
    ) -> List[SimulationEvent]:
        """Step simulator."""
        simulator = self._simulators.get(simulator_name)
        if not simulator:
            return []

        events = simulator.step(dt)
        self._stats.total_events_processed += len(events)
        self._stats.total_ticks_simulated += int(dt)

        return events

    def run(
        self,
        simulator_name: str,
        duration: int,
        step_size: float = 1.0
    ) -> SimulationResult:
        """Run simulation for duration."""
        simulator = self._simulators.get(simulator_name)
        if not simulator:
            return SimulationResult(success=False, error="Simulator not found")

        result = SimulationResult()
        events_processed = 0
        history = []

        for tick in range(duration):
            events = simulator.step(step_size)
            events_processed += len(events)

            if tick % max(1, duration // 100) == 0:
                state = simulator.get_state()
                if state:
                    history.append(state)

        result.final_state = simulator.get_state()
        result.history = history
        result.events_processed = events_processed
        result.duration_ticks = simulator.get_time()
        result.success = True

        self._stats.total_simulations += 1
        self._stats.total_events_processed += events_processed
        self._stats.total_ticks_simulated += duration

        return result

    def get_state(
        self,
        simulator_name: str
    ) -> Optional[WorldState]:
        """Get simulator state."""
        simulator = self._simulators.get(simulator_name)
        if simulator:
            return simulator.get_state()
        return None

    # -------------------------------------------------------------------------
    # SCENARIO MANAGEMENT
    # -------------------------------------------------------------------------

    def create_scenario(
        self,
        name: str,
        description: str = "",
        initial_state: Optional[WorldState] = None,
        parameters: Optional[Dict[str, Any]] = None,
        duration: int = 1000
    ) -> ScenarioConfig:
        """Create scenario."""
        scenario = ScenarioConfig(
            name=name,
            description=description,
            initial_state=initial_state,
            parameters=parameters or {},
            duration=duration
        )

        self._scenarios[scenario.scenario_id] = scenario
        return scenario

    def run_scenario(
        self,
        scenario_id: str,
        record_history: bool = True
    ) -> SimulationResult:
        """Run scenario."""
        scenario = self._scenarios.get(scenario_id)
        if not scenario:
            return SimulationResult(success=False, error="Scenario not found")

        runner = ScenarioRunner()
        result = runner.run(scenario, record_history)

        self._results[result.result_id] = result
        self._stats.total_simulations += 1
        self._stats.total_events_processed += result.events_processed
        self._stats.total_ticks_simulated += result.duration_ticks

        return result

    # -------------------------------------------------------------------------
    # MONTE CARLO
    # -------------------------------------------------------------------------

    def run_monte_carlo(
        self,
        scenario_id: str,
        iterations: int,
        parameter_distributions: Dict[str, Callable[[], Any]],
        outcome_extractor: Optional[Callable[[SimulationResult], Dict[str, Any]]] = None
    ) -> MonteCarloResult:
        """Run Monte Carlo simulation."""
        scenario = self._scenarios.get(scenario_id)
        if not scenario:
            return MonteCarloResult()

        mc_simulator = MonteCarloSimulator(scenario)
        result = mc_simulator.run(iterations, parameter_distributions, outcome_extractor)

        self._stats.monte_carlo_runs += 1
        self._stats.total_simulations += iterations

        return result

    # -------------------------------------------------------------------------
    # WHAT-IF ANALYSIS
    # -------------------------------------------------------------------------

    def analyze_what_if(
        self,
        scenario_id: str,
        variations: List[Dict[str, Any]],
        comparison_metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Run what-if analysis."""
        scenario = self._scenarios.get(scenario_id)
        if not scenario:
            return {}

        analyzer = WhatIfAnalyzer()
        return analyzer.analyze(scenario, variations, comparison_metrics)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> SimulationStats:
        """Get engine statistics."""
        return self._stats


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Simulation Engine."""
    print("=" * 70)
    print("BAEL - SIMULATION ENGINE DEMO")
    print("Advanced World Simulation and Scenario Modeling")
    print("=" * 70)
    print()

    engine = SimulationEngine()

    # 1. Create Simulator
    print("1. CREATE SIMULATOR:")
    print("-" * 40)

    sim = engine.create_simulator("world1")
    engine.initialize_simulator("world1")
    print("   Created and initialized 'world1' simulator")
    print()

    # 2. Add Entities
    print("2. ADD ENTITIES:")
    print("-" * 40)

    agent1 = engine.add_entity(
        "world1",
        EntityType.AGENT,
        "Agent1",
        position=(0, 0, 0),
        properties={"health": 100, "energy": 50},
        behavior=RandomWalkBehavior(step_size=0.5)
    )

    agent2 = engine.add_entity(
        "world1",
        EntityType.AGENT,
        "Agent2",
        position=(10, 10, 0),
        properties={"health": 100, "energy": 75},
        behavior=RandomWalkBehavior(step_size=0.3)
    )

    resource = engine.add_entity(
        "world1",
        EntityType.RESOURCE,
        "GoldMine",
        position=(5, 5, 0),
        properties={"value": 50},
        behavior=ResourceBehavior(regeneration_rate=0.1)
    )

    print(f"   Added: {agent1.name} at {agent1.position}")
    print(f"   Added: {agent2.name} at {agent2.position}")
    print(f"   Added: {resource.name} at {resource.position}")
    print()

    # 3. Step Simulation
    print("3. STEP SIMULATION:")
    print("-" * 40)

    for i in range(5):
        events = engine.step("world1", dt=1.0)
        state = engine.get_state("world1")
        if state:
            agent = state.entities.get(agent1.entity_id)
            if agent:
                print(f"   Tick {state.time}: Agent1 at ({agent.position[0]:.2f}, {agent.position[1]:.2f})")
    print()

    # 4. Run Simulation
    print("4. RUN SIMULATION:")
    print("-" * 40)

    result = engine.run("world1", duration=100, step_size=1.0)
    print(f"   Duration: {result.duration_ticks} ticks")
    print(f"   Events processed: {result.events_processed}")
    print(f"   History snapshots: {len(result.history)}")

    if result.final_state:
        print(f"   Final entities: {len(result.final_state.entities)}")
    print()

    # 5. Create Scenario
    print("5. CREATE SCENARIO:")
    print("-" * 40)

    initial_state = WorldState()
    for i in range(10):
        entity = EntityState(
            entity_type=EntityType.AGENT,
            name=f"Bot_{i}",
            position=(random.uniform(-50, 50), random.uniform(-50, 50), 0),
            properties={"health": 100}
        )
        initial_state.entities[entity.entity_id] = entity

    scenario = engine.create_scenario(
        name="Population Test",
        description="Test with 10 agents",
        initial_state=initial_state,
        parameters={"growth_rate": 0.1},
        duration=500
    )

    print(f"   Created scenario: {scenario.name}")
    print(f"   Initial entities: {len(initial_state.entities)}")
    print(f"   Duration: {scenario.duration} ticks")
    print()

    # 6. Run Scenario
    print("6. RUN SCENARIO:")
    print("-" * 40)

    result = engine.run_scenario(scenario.scenario_id)
    print(f"   Success: {result.success}")
    print(f"   Duration: {result.duration_ticks}")
    print(f"   Metrics: {result.metrics}")
    print()

    # 7. Monte Carlo Simulation
    print("7. MONTE CARLO SIMULATION:")
    print("-" * 40)

    mc_result = engine.run_monte_carlo(
        scenario.scenario_id,
        iterations=50,
        parameter_distributions={
            "growth_rate": lambda: random.uniform(0.05, 0.2),
            "decay_rate": lambda: random.uniform(0.01, 0.1),
        }
    )

    print(f"   Iterations: {mc_result.iterations}")
    print(f"   Statistics:")
    for key, stats in mc_result.statistics.items():
        if isinstance(stats, dict):
            print(f"     {key}: mean={stats.get('mean', 0):.2f}, std={stats.get('std', 0):.2f}")
        else:
            print(f"     {key}: {stats:.2f}")
    print()

    # 8. Confidence Intervals
    print("8. CONFIDENCE INTERVALS:")
    print("-" * 40)

    for key, (low, high) in mc_result.confidence_intervals.items():
        print(f"   {key}: [{low:.2f}, {high:.2f}]")
    print()

    # 9. What-If Analysis
    print("9. WHAT-IF ANALYSIS:")
    print("-" * 40)

    analysis = engine.analyze_what_if(
        scenario.scenario_id,
        variations=[
            {"growth_rate": 0.05},
            {"growth_rate": 0.2},
            {"growth_rate": 0.5},
        ],
        comparison_metrics=["entity_count", "simulation_time"]
    )

    print("   Comparisons:")
    for var_name, comparison in analysis.get("comparisons", {}).items():
        print(f"   {var_name}:")
        for metric, data in comparison.items():
            if isinstance(data, dict):
                pct = data.get('percent_change', 0)
                print(f"     {metric}: {pct:+.1f}%")
    print()

    # 10. Get States
    print("10. GET SIMULATOR STATE:")
    print("-" * 40)

    state = engine.get_state("world1")
    if state:
        print(f"   Time: {state.time}")
        print(f"   Entities: {len(state.entities)}")
        print(f"   Checksum: {state.checksum}")
    print()

    # 11. Statistics
    print("11. STATISTICS:")
    print("-" * 40)

    stats = engine.get_stats()
    print(f"   Total simulations: {stats.total_simulations}")
    print(f"   Events processed: {stats.total_events_processed}")
    print(f"   Ticks simulated: {stats.total_ticks_simulated}")
    print(f"   Monte Carlo runs: {stats.monte_carlo_runs}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Simulation Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
