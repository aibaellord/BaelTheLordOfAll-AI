#!/usr/bin/env python3
"""
BAEL - Engine Matrix
The meta-engine system where engines create, coordinate, and optimize other engines.

"Engines that control engines that control whatever we are capable of"

This module implements:
- Engine creation and lifecycle management
- Engine coordination and orchestration
- Self-optimizing engine networks
- Dynamic engine spawning
- Engine hierarchy management
- Meta-engine operations
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND TYPES
# =============================================================================

class EngineType(Enum):
    """Types of engines in the matrix."""
    CORE = "core"
    PROCESSING = "processing"
    OPTIMIZATION = "optimization"
    COORDINATION = "coordination"
    EXPLOITATION = "exploitation"
    ANALYSIS = "analysis"
    CREATION = "creation"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    META = "meta"


class EngineState(Enum):
    """States an engine can be in."""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    OPTIMIZING = "optimizing"
    ERROR = "error"
    TERMINATED = "terminated"


class EngineCapability(Enum):
    """Capabilities an engine can have."""
    PROCESS = "process"
    ANALYZE = "analyze"
    CREATE = "create"
    OPTIMIZE = "optimize"
    COORDINATE = "coordinate"
    EXPLOIT = "exploit"
    VALIDATE = "validate"
    TRANSFORM = "transform"
    SPAWN = "spawn"
    TERMINATE = "terminate"
    SELF_MODIFY = "self_modify"


class Priority(Enum):
    """Priority levels for engines and tasks."""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class EngineMetrics:
    """Metrics for engine performance."""
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_processing_time: float = 0.0
    average_latency: float = 0.0
    efficiency_score: float = 1.0
    resource_usage: float = 0.0
    error_rate: float = 0.0
    uptime: float = 0.0
    last_active: Optional[datetime] = None

    def update_efficiency(self):
        """Calculate efficiency score."""
        if self.tasks_completed + self.tasks_failed > 0:
            success_rate = self.tasks_completed / (self.tasks_completed + self.tasks_failed)
            speed_factor = 1.0 / max(1.0, self.average_latency)
            self.efficiency_score = success_rate * speed_factor * (1 - self.resource_usage)


@dataclass
class EngineConfig:
    """Configuration for an engine."""
    engine_type: EngineType = EngineType.PROCESSING
    capabilities: List[EngineCapability] = field(default_factory=list)
    priority: Priority = Priority.MEDIUM
    max_concurrent_tasks: int = 10
    timeout_seconds: float = 30.0
    auto_optimize: bool = True
    can_spawn: bool = False
    can_be_terminated: bool = True
    min_efficiency_threshold: float = 0.5
    custom_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EngineTask:
    """A task for an engine to process."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: Priority = Priority.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    source_engine: Optional[str] = None
    target_engine: Optional[str] = None


@dataclass
class EngineMessage:
    """A message between engines."""
    id: str = field(default_factory=lambda: str(uuid4()))
    source: str = ""
    target: str = ""
    message_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    requires_response: bool = False
    correlation_id: Optional[str] = None


@dataclass
class EngineBlueprint:
    """Blueprint for creating new engines."""
    name: str = ""
    engine_type: EngineType = EngineType.PROCESSING
    config: EngineConfig = field(default_factory=EngineConfig)
    initialization_code: Optional[str] = None
    processing_code: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    created_by: Optional[str] = None
    version: str = "1.0.0"


# =============================================================================
# BASE ENGINE
# =============================================================================

class Engine(ABC):
    """Base class for all engines in the matrix."""

    def __init__(self, name: str, config: EngineConfig = None):
        self.id = str(uuid4())
        self.name = name
        self.config = config or EngineConfig()
        self.state = EngineState.INITIALIZING
        self.metrics = EngineMetrics()
        self.parent_engine: Optional[str] = None
        self.child_engines: List[str] = []
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.created_at = datetime.now()
        self.last_heartbeat = datetime.now()
        self._running = False
        self._workers: List[asyncio.Task] = []

    @property
    def capabilities(self) -> List[EngineCapability]:
        """Get engine capabilities."""
        return self.config.capabilities

    @abstractmethod
    async def process(self, task: EngineTask) -> Any:
        """Process a task."""
        pass

    async def initialize(self) -> bool:
        """Initialize the engine."""
        try:
            await self._setup()
            self.state = EngineState.READY
            logger.info(f"Engine {self.name} initialized")
            return True
        except Exception as e:
            self.state = EngineState.ERROR
            logger.error(f"Engine {self.name} initialization failed: {e}")
            return False

    async def _setup(self):
        """Setup hook for subclasses."""
        pass

    async def start(self):
        """Start the engine."""
        if self.state != EngineState.READY:
            await self.initialize()

        self._running = True
        self.state = EngineState.RUNNING

        # Start worker tasks
        for i in range(min(3, self.config.max_concurrent_tasks)):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)

        # Start heartbeat
        asyncio.create_task(self._heartbeat_loop())

        logger.info(f"Engine {self.name} started with {len(self._workers)} workers")

    async def stop(self):
        """Stop the engine."""
        self._running = False
        self.state = EngineState.TERMINATED

        # Cancel workers
        for worker in self._workers:
            worker.cancel()

        self._workers.clear()
        logger.info(f"Engine {self.name} stopped")

    async def pause(self):
        """Pause the engine."""
        self.state = EngineState.PAUSED

    async def resume(self):
        """Resume the engine."""
        self.state = EngineState.RUNNING

    async def submit_task(self, task: EngineTask) -> str:
        """Submit a task for processing."""
        task.target_engine = self.id
        await self.task_queue.put(task)
        return task.id

    async def send_message(self, target: str, message_type: str, payload: Dict[str, Any]):
        """Send a message to another engine."""
        message = EngineMessage(
            source=self.id,
            target=target,
            message_type=message_type,
            payload=payload
        )
        # Message routing handled by EngineMatrix
        return message

    async def _worker(self, worker_id: int):
        """Worker coroutine for processing tasks."""
        while self._running:
            try:
                if self.state == EngineState.PAUSED:
                    await asyncio.sleep(0.1)
                    continue

                task = await asyncio.wait_for(
                    self.task_queue.get(),
                    timeout=1.0
                )

                task.started_at = datetime.now()

                try:
                    result = await asyncio.wait_for(
                        self.process(task),
                        timeout=self.config.timeout_seconds
                    )
                    task.result = result
                    task.completed_at = datetime.now()
                    self.metrics.tasks_completed += 1

                except asyncio.TimeoutError:
                    task.error = "Task timeout"
                    self.metrics.tasks_failed += 1

                except Exception as e:
                    task.error = str(e)
                    self.metrics.tasks_failed += 1

                finally:
                    if task.started_at:
                        duration = (datetime.now() - task.started_at).total_seconds()
                        self.metrics.total_processing_time += duration
                        self._update_latency(duration)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error in {self.name}: {e}")

    def _update_latency(self, duration: float):
        """Update average latency."""
        total = self.metrics.tasks_completed + self.metrics.tasks_failed
        if total > 0:
            self.metrics.average_latency = (
                (self.metrics.average_latency * (total - 1) + duration) / total
            )

    async def _heartbeat_loop(self):
        """Heartbeat loop."""
        while self._running:
            self.last_heartbeat = datetime.now()
            self.metrics.uptime = (datetime.now() - self.created_at).total_seconds()
            self.metrics.update_efficiency()
            await asyncio.sleep(5)

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.config.engine_type.value,
            "state": self.state.value,
            "capabilities": [c.value for c in self.capabilities],
            "metrics": {
                "tasks_completed": self.metrics.tasks_completed,
                "tasks_failed": self.metrics.tasks_failed,
                "efficiency": self.metrics.efficiency_score,
                "avg_latency": self.metrics.average_latency,
                "uptime": self.metrics.uptime
            },
            "queue_size": self.task_queue.qsize(),
            "workers": len(self._workers)
        }


# =============================================================================
# SPECIALIZED ENGINES
# =============================================================================

class ProcessingEngine(Engine):
    """Engine for processing data and tasks."""

    def __init__(self, name: str = "ProcessingEngine"):
        config = EngineConfig(
            engine_type=EngineType.PROCESSING,
            capabilities=[
                EngineCapability.PROCESS,
                EngineCapability.TRANSFORM
            ],
            max_concurrent_tasks=20
        )
        super().__init__(name, config)
        self.processors: Dict[str, Callable] = {}

    def register_processor(self, name: str, processor: Callable):
        """Register a processor function."""
        self.processors[name] = processor

    async def process(self, task: EngineTask) -> Any:
        """Process a task."""
        processor_name = task.payload.get("processor")
        if processor_name and processor_name in self.processors:
            return await self.processors[processor_name](task.payload)
        return {"processed": True, "data": task.payload}


class OptimizationEngine(Engine):
    """Engine for optimizing other engines and processes."""

    def __init__(self, name: str = "OptimizationEngine"):
        config = EngineConfig(
            engine_type=EngineType.OPTIMIZATION,
            capabilities=[
                EngineCapability.OPTIMIZE,
                EngineCapability.ANALYZE
            ],
            priority=Priority.HIGH
        )
        super().__init__(name, config)
        self.optimization_strategies: List[Callable] = []
        self.performance_history: Dict[str, List[float]] = defaultdict(list)

    async def process(self, task: EngineTask) -> Any:
        """Analyze and optimize."""
        target_id = task.payload.get("target_engine_id")
        if not target_id:
            return {"error": "No target engine specified"}

        optimization_type = task.payload.get("type", "performance")

        return {
            "optimized": True,
            "target": target_id,
            "type": optimization_type,
            "recommendations": await self._generate_recommendations(target_id)
        }

    async def _generate_recommendations(self, target_id: str) -> List[Dict[str, Any]]:
        """Generate optimization recommendations."""
        return [
            {
                "type": "scaling",
                "action": "increase_workers",
                "reason": "High task queue",
                "priority": Priority.MEDIUM.value
            },
            {
                "type": "efficiency",
                "action": "reduce_timeout",
                "reason": "Average latency low",
                "priority": Priority.LOW.value
            }
        ]


class CoordinationEngine(Engine):
    """Engine for coordinating other engines."""

    def __init__(self, name: str = "CoordinationEngine"):
        config = EngineConfig(
            engine_type=EngineType.COORDINATION,
            capabilities=[
                EngineCapability.COORDINATE,
                EngineCapability.SPAWN,
                EngineCapability.TERMINATE
            ],
            priority=Priority.CRITICAL,
            can_spawn=True
        )
        super().__init__(name, config)
        self.managed_engines: Dict[str, Engine] = {}
        self.coordination_rules: List[Dict[str, Any]] = []

    async def process(self, task: EngineTask) -> Any:
        """Coordinate engines."""
        action = task.payload.get("action")

        if action == "spawn":
            return await self._spawn_engine(task.payload)
        elif action == "terminate":
            return await self._terminate_engine(task.payload)
        elif action == "coordinate":
            return await self._coordinate(task.payload)
        else:
            return {"error": f"Unknown action: {action}"}

    async def _spawn_engine(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Spawn a new engine."""
        engine_type = payload.get("engine_type", "processing")
        name = payload.get("name", f"spawned_{uuid4().hex[:8]}")

        # Create engine based on type
        engine_class = {
            "processing": ProcessingEngine,
            "optimization": OptimizationEngine,
            "analysis": AnalysisEngine,
            "creation": CreationEngine
        }.get(engine_type, ProcessingEngine)

        engine = engine_class(name)
        engine.parent_engine = self.id
        self.child_engines.append(engine.id)
        self.managed_engines[engine.id] = engine

        await engine.initialize()
        await engine.start()

        return {
            "spawned": True,
            "engine_id": engine.id,
            "engine_name": name,
            "type": engine_type
        }

    async def _terminate_engine(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Terminate an engine."""
        engine_id = payload.get("engine_id")
        if engine_id in self.managed_engines:
            engine = self.managed_engines[engine_id]
            if engine.config.can_be_terminated:
                await engine.stop()
                del self.managed_engines[engine_id]
                self.child_engines.remove(engine_id)
                return {"terminated": True, "engine_id": engine_id}
            return {"terminated": False, "reason": "Engine cannot be terminated"}
        return {"terminated": False, "reason": "Engine not found"}

    async def _coordinate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate work between engines."""
        task_data = payload.get("task")
        engines = payload.get("engines", list(self.managed_engines.keys()))

        # Distribute task to engines
        results = {}
        for engine_id in engines:
            if engine_id in self.managed_engines:
                engine = self.managed_engines[engine_id]
                task = EngineTask(
                    name="coordinated_task",
                    payload=task_data,
                    source_engine=self.id
                )
                task_id = await engine.submit_task(task)
                results[engine_id] = task_id

        return {"coordinated": True, "tasks": results}


class AnalysisEngine(Engine):
    """Engine for analyzing data and patterns."""

    def __init__(self, name: str = "AnalysisEngine"):
        config = EngineConfig(
            engine_type=EngineType.ANALYSIS,
            capabilities=[
                EngineCapability.ANALYZE,
                EngineCapability.VALIDATE
            ]
        )
        super().__init__(name, config)

    async def process(self, task: EngineTask) -> Any:
        """Analyze data."""
        data = task.payload.get("data")
        analysis_type = task.payload.get("type", "basic")

        return {
            "analyzed": True,
            "type": analysis_type,
            "patterns": [],
            "insights": [],
            "recommendations": []
        }


class CreationEngine(Engine):
    """Engine for creating new engines and components."""

    def __init__(self, name: str = "CreationEngine"):
        config = EngineConfig(
            engine_type=EngineType.CREATION,
            capabilities=[
                EngineCapability.CREATE,
                EngineCapability.SPAWN
            ],
            can_spawn=True
        )
        super().__init__(name, config)
        self.blueprints: Dict[str, EngineBlueprint] = {}

    async def process(self, task: EngineTask) -> Any:
        """Create something new."""
        creation_type = task.payload.get("type")

        if creation_type == "blueprint":
            return await self._create_blueprint(task.payload)
        elif creation_type == "engine":
            return await self._create_engine(task.payload)
        elif creation_type == "component":
            return await self._create_component(task.payload)
        else:
            return {"error": f"Unknown creation type: {creation_type}"}

    async def _create_blueprint(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create an engine blueprint."""
        blueprint = EngineBlueprint(
            name=payload.get("name", "new_blueprint"),
            engine_type=EngineType[payload.get("engine_type", "PROCESSING").upper()],
            created_by=self.id
        )
        self.blueprints[blueprint.name] = blueprint
        return {"created": True, "blueprint": blueprint.name}

    async def _create_engine(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create an engine from blueprint."""
        blueprint_name = payload.get("blueprint")
        if blueprint_name not in self.blueprints:
            return {"error": "Blueprint not found"}

        # Would dynamically create engine here
        return {"created": True, "engine_type": "dynamic"}

    async def _create_component(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a component."""
        component_type = payload.get("component_type")
        return {"created": True, "component": component_type}


class MetaEngine(Engine):
    """Engine that manages and creates other engines - the supreme engine."""

    def __init__(self, name: str = "MetaEngine"):
        config = EngineConfig(
            engine_type=EngineType.META,
            capabilities=list(EngineCapability),  # All capabilities
            priority=Priority.CRITICAL,
            can_spawn=True,
            can_be_terminated=False  # Cannot be killed
        )
        super().__init__(name, config)
        self.engine_registry: Dict[str, Engine] = {}
        self.engine_hierarchy: Dict[str, List[str]] = {}
        self.coordination_engine: Optional[CoordinationEngine] = None
        self.creation_engine: Optional[CreationEngine] = None
        self.optimization_engine: Optional[OptimizationEngine] = None

    async def _setup(self):
        """Setup the meta engine with core sub-engines."""
        # Create core engines
        self.coordination_engine = CoordinationEngine("CoreCoordination")
        self.creation_engine = CreationEngine("CoreCreation")
        self.optimization_engine = OptimizationEngine("CoreOptimization")

        # Register them
        await self._register_engine(self.coordination_engine)
        await self._register_engine(self.creation_engine)
        await self._register_engine(self.optimization_engine)

    async def _register_engine(self, engine: Engine):
        """Register an engine."""
        await engine.initialize()
        await engine.start()
        engine.parent_engine = self.id
        self.child_engines.append(engine.id)
        self.engine_registry[engine.id] = engine
        self.engine_hierarchy[engine.id] = []

    async def process(self, task: EngineTask) -> Any:
        """Process meta-level tasks."""
        action = task.payload.get("action")

        if action == "spawn_engine":
            return await self._spawn_engine(task.payload)
        elif action == "terminate_engine":
            return await self._terminate_engine(task.payload)
        elif action == "optimize_all":
            return await self._optimize_all()
        elif action == "get_topology":
            return self._get_topology()
        elif action == "distribute_task":
            return await self._distribute_task(task.payload)
        elif action == "self_evolve":
            return await self._self_evolve()
        else:
            return {"error": f"Unknown meta action: {action}"}

    async def _spawn_engine(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Spawn a new engine through creation engine."""
        if self.creation_engine:
            task = EngineTask(
                name="spawn_engine",
                payload=payload
            )
            return await self.creation_engine.process(task)
        return {"error": "Creation engine not available"}

    async def _terminate_engine(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Terminate an engine."""
        engine_id = payload.get("engine_id")
        if engine_id in self.engine_registry:
            engine = self.engine_registry[engine_id]
            if engine.config.can_be_terminated:
                await engine.stop()
                del self.engine_registry[engine_id]
                return {"terminated": True}
        return {"terminated": False}

    async def _optimize_all(self) -> Dict[str, Any]:
        """Optimize all engines."""
        if not self.optimization_engine:
            return {"error": "Optimization engine not available"}

        results = {}
        for engine_id, engine in self.engine_registry.items():
            if engine.metrics.efficiency_score < engine.config.min_efficiency_threshold:
                task = EngineTask(
                    name="optimize",
                    payload={"target_engine_id": engine_id}
                )
                result = await self.optimization_engine.process(task)
                results[engine_id] = result

        return {"optimized": len(results), "results": results}

    def _get_topology(self) -> Dict[str, Any]:
        """Get engine topology."""
        topology = {
            "meta_engine": self.id,
            "total_engines": len(self.engine_registry) + 1,
            "engines": {}
        }

        for engine_id, engine in self.engine_registry.items():
            topology["engines"][engine_id] = {
                "name": engine.name,
                "type": engine.config.engine_type.value,
                "parent": engine.parent_engine,
                "children": engine.child_engines,
                "state": engine.state.value,
                "efficiency": engine.metrics.efficiency_score
            }

        return topology

    async def _distribute_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Distribute a task to the best engine."""
        required_capability = payload.get("capability")
        task_data = payload.get("task")

        # Find engines with required capability
        candidates = []
        for engine_id, engine in self.engine_registry.items():
            if engine.state == EngineState.RUNNING:
                if not required_capability or EngineCapability[required_capability.upper()] in engine.capabilities:
                    candidates.append((engine_id, engine))

        if not candidates:
            return {"error": "No suitable engine found"}

        # Select best engine by efficiency and queue size
        best = max(candidates, key=lambda x: (
            x[1].metrics.efficiency_score - x[1].task_queue.qsize() * 0.1
        ))

        task = EngineTask(name="distributed", payload=task_data)
        task_id = await best[1].submit_task(task)

        return {
            "distributed": True,
            "engine_id": best[0],
            "task_id": task_id
        }

    async def _self_evolve(self) -> Dict[str, Any]:
        """Trigger self-evolution - improve the engine matrix itself."""
        # Analyze current performance
        low_performers = []
        for engine_id, engine in self.engine_registry.items():
            if engine.metrics.efficiency_score < 0.3:
                low_performers.append(engine_id)

        # Terminate low performers
        for engine_id in low_performers:
            await self._terminate_engine({"engine_id": engine_id})

        # Spawn improved versions
        spawned = []
        for _ in low_performers:
            result = await self._spawn_engine({
                "engine_type": "optimization",
                "name": f"evolved_{uuid4().hex[:8]}"
            })
            spawned.append(result)

        return {
            "evolved": True,
            "terminated": len(low_performers),
            "spawned": len(spawned)
        }


# =============================================================================
# ENGINE MATRIX
# =============================================================================

class EngineMatrix:
    """
    The Engine Matrix - supreme orchestrator of all engines.

    This is where engines create engines, optimize engines,
    and coordinate with engines in a recursive hierarchy
    of self-improving capability.
    """

    def __init__(self):
        self.meta_engine: Optional[MetaEngine] = None
        self.all_engines: Dict[str, Engine] = {}
        self.message_bus: asyncio.Queue = asyncio.Queue()
        self.running = False
        self.creation_history: List[Dict[str, Any]] = []

    async def initialize(self):
        """Initialize the engine matrix."""
        logger.info("Initializing Engine Matrix...")

        # Create the meta engine
        self.meta_engine = MetaEngine("BAEL_MetaEngine")
        await self.meta_engine.initialize()
        await self.meta_engine.start()

        self.all_engines[self.meta_engine.id] = self.meta_engine

        # Register all sub-engines
        for engine_id, engine in self.meta_engine.engine_registry.items():
            self.all_engines[engine_id] = engine

        self.running = True

        # Start message router
        asyncio.create_task(self._message_router())

        logger.info(f"Engine Matrix initialized with {len(self.all_engines)} engines")

    async def shutdown(self):
        """Shutdown the engine matrix."""
        self.running = False

        # Stop all engines
        for engine in self.all_engines.values():
            await engine.stop()

        self.all_engines.clear()
        logger.info("Engine Matrix shutdown complete")

    async def _message_router(self):
        """Route messages between engines."""
        while self.running:
            try:
                message = await asyncio.wait_for(
                    self.message_bus.get(),
                    timeout=1.0
                )

                target_engine = self.all_engines.get(message.target)
                if target_engine:
                    await target_engine.message_queue.put(message)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Message routing error: {e}")

    async def submit_task(
        self,
        task_name: str,
        payload: Dict[str, Any],
        capability: EngineCapability = None
    ) -> str:
        """Submit a task to the matrix."""
        if not self.meta_engine:
            raise RuntimeError("Engine Matrix not initialized")

        task = EngineTask(name=task_name, payload=payload)

        if capability:
            # Route to engine with specific capability
            result = await self.meta_engine.process(EngineTask(
                name="distribute",
                payload={
                    "action": "distribute_task",
                    "capability": capability.value,
                    "task": payload
                }
            ))
            return result.get("task_id", "")
        else:
            # Submit to meta engine
            return await self.meta_engine.submit_task(task)

    async def spawn_engine(
        self,
        engine_type: str,
        name: str = None,
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Spawn a new engine."""
        if not self.meta_engine:
            raise RuntimeError("Engine Matrix not initialized")

        result = await self.meta_engine.process(EngineTask(
            name="spawn",
            payload={
                "action": "spawn_engine",
                "engine_type": engine_type,
                "name": name,
                "config": config or {}
            }
        ))

        if result.get("created"):
            self.creation_history.append({
                "type": engine_type,
                "name": name,
                "timestamp": datetime.now().isoformat()
            })

        return result

    async def optimize_matrix(self) -> Dict[str, Any]:
        """Optimize the entire engine matrix."""
        if not self.meta_engine:
            raise RuntimeError("Engine Matrix not initialized")

        return await self.meta_engine.process(EngineTask(
            name="optimize_all",
            payload={"action": "optimize_all"}
        ))

    async def evolve(self) -> Dict[str, Any]:
        """Trigger self-evolution of the matrix."""
        if not self.meta_engine:
            raise RuntimeError("Engine Matrix not initialized")

        return await self.meta_engine.process(EngineTask(
            name="self_evolve",
            payload={"action": "self_evolve"}
        ))

    def get_topology(self) -> Dict[str, Any]:
        """Get the current engine topology."""
        if not self.meta_engine:
            return {"error": "Not initialized"}

        topology = self.meta_engine._get_topology()
        topology["creation_history"] = self.creation_history
        return topology

    def get_status(self) -> Dict[str, Any]:
        """Get overall matrix status."""
        if not self.meta_engine:
            return {"status": "not_initialized"}

        engine_states = defaultdict(int)
        total_tasks = 0
        total_efficiency = 0.0

        for engine in self.all_engines.values():
            engine_states[engine.state.value] += 1
            total_tasks += engine.metrics.tasks_completed
            total_efficiency += engine.metrics.efficiency_score

        avg_efficiency = total_efficiency / len(self.all_engines) if self.all_engines else 0

        return {
            "status": "running" if self.running else "stopped",
            "total_engines": len(self.all_engines),
            "engine_states": dict(engine_states),
            "total_tasks_completed": total_tasks,
            "average_efficiency": avg_efficiency,
            "creation_count": len(self.creation_history)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Engine Matrix."""
    print("=" * 70)
    print("BAEL - ENGINE MATRIX DEMO")
    print("Engines that control engines that control everything")
    print("=" * 70)
    print()

    # Create the matrix
    matrix = EngineMatrix()

    # Initialize
    print("1. INITIALIZING ENGINE MATRIX:")
    print("-" * 40)
    await matrix.initialize()

    status = matrix.get_status()
    print(f"   Status: {status['status']}")
    print(f"   Total engines: {status['total_engines']}")
    print()

    # Get topology
    print("2. ENGINE TOPOLOGY:")
    print("-" * 40)

    topology = matrix.get_topology()
    print(f"   Meta Engine: {topology['meta_engine'][:8]}...")
    print(f"   Total in hierarchy: {topology['total_engines']}")

    for engine_id, info in list(topology.get("engines", {}).items())[:3]:
        print(f"   - {info['name']}: {info['type']} ({info['state']})")
    print()

    # Spawn new engines
    print("3. SPAWNING NEW ENGINES:")
    print("-" * 40)

    # The matrix spawning engines that will spawn more engines
    result = await matrix.spawn_engine("processing", "DataProcessor")
    print(f"   Spawned: DataProcessor")

    result = await matrix.spawn_engine("analysis", "PatternAnalyzer")
    print(f"   Spawned: PatternAnalyzer")

    result = await matrix.spawn_engine("optimization", "AutoOptimizer")
    print(f"   Spawned: AutoOptimizer")

    print(f"   Total engines now: {matrix.get_status()['total_engines']}")
    print()

    # Submit tasks
    print("4. SUBMITTING TASKS TO MATRIX:")
    print("-" * 40)

    # Submit tasks that will be routed to appropriate engines
    for i in range(5):
        task_id = await matrix.submit_task(
            f"process_data_{i}",
            {"data": f"sample_{i}", "operation": "transform"},
            EngineCapability.PROCESS
        )
        print(f"   Task {i+1} submitted")

    print()

    # Let tasks process
    await asyncio.sleep(2)

    # Optimize
    print("5. OPTIMIZING THE MATRIX:")
    print("-" * 40)

    opt_result = await matrix.optimize_matrix()
    print(f"   Optimized: {opt_result.get('optimized', 0)} engines")
    print()

    # Evolve
    print("6. SELF-EVOLUTION:")
    print("-" * 40)

    evolve_result = await matrix.evolve()
    print(f"   Terminated: {evolve_result.get('terminated', 0)} low performers")
    print(f"   Spawned: {evolve_result.get('spawned', 0)} improved engines")
    print()

    # Final status
    print("7. FINAL STATUS:")
    print("-" * 40)

    final_status = matrix.get_status()
    print(f"   Total engines: {final_status['total_engines']}")
    print(f"   Tasks completed: {final_status['total_tasks_completed']}")
    print(f"   Average efficiency: {final_status['average_efficiency']:.2f}")
    print(f"   Creation history: {final_status['creation_count']} engines created")
    print()

    # Shutdown
    print("8. SHUTDOWN:")
    print("-" * 40)
    await matrix.shutdown()
    print("   Engine Matrix shutdown complete")

    print()
    print("=" * 70)
    print("DEMO COMPLETE - Engine Matrix Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
