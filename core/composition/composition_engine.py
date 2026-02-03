#!/usr/bin/env python3
"""
BAEL - Composition Engine
System composition and component assembly for agents.

Features:
- Component registration
- Dependency injection
- Pipeline composition
- Module assembly
- Service composition
"""

import asyncio
import hashlib
import json
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class ComponentState(Enum):
    """Component states."""
    UNINITIALIZED = "uninitialized"
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class LifecycleHook(Enum):
    """Lifecycle hooks."""
    PRE_INIT = "pre_init"
    POST_INIT = "post_init"
    PRE_START = "pre_start"
    POST_START = "post_start"
    PRE_STOP = "pre_stop"
    POST_STOP = "post_stop"


class DependencyScope(Enum):
    """Dependency scopes."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class PipelineMode(Enum):
    """Pipeline execution modes."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"


class CompositionType(Enum):
    """Composition types."""
    AGGREGATION = "aggregation"
    DELEGATION = "delegation"
    DECORATION = "decoration"
    PROXY = "proxy"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ComponentDef:
    """Component definition."""
    component_id: str = ""
    name: str = ""
    factory: Optional[Callable] = None
    instance: Any = None
    scope: DependencyScope = DependencyScope.SINGLETON
    dependencies: List[str] = field(default_factory=list)
    state: ComponentState = ComponentState.UNINITIALIZED
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.component_id:
            self.component_id = str(uuid.uuid4())[:8]


@dataclass
class PipelineStage:
    """Pipeline stage."""
    stage_id: str = ""
    name: str = ""
    handler: Optional[Callable] = None
    order: int = 0
    condition: Optional[Callable] = None
    enabled: bool = True

    def __post_init__(self):
        if not self.stage_id:
            self.stage_id = str(uuid.uuid4())[:8]


@dataclass
class Pipeline:
    """A processing pipeline."""
    pipeline_id: str = ""
    name: str = ""
    stages: List[PipelineStage] = field(default_factory=list)
    mode: PipelineMode = PipelineMode.SEQUENTIAL
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.pipeline_id:
            self.pipeline_id = str(uuid.uuid4())[:8]


@dataclass
class CompositeComponent:
    """A composite component."""
    composite_id: str = ""
    name: str = ""
    components: List[str] = field(default_factory=list)
    composition_type: CompositionType = CompositionType.AGGREGATION

    def __post_init__(self):
        if not self.composite_id:
            self.composite_id = str(uuid.uuid4())[:8]


@dataclass
class CompositionConfig:
    """Composition engine configuration."""
    auto_wire: bool = True
    lazy_init: bool = False
    enable_hooks: bool = True


# =============================================================================
# COMPONENT BASE
# =============================================================================

class Component(ABC):
    """Base component class."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize component."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start component."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop component."""
        pass


# =============================================================================
# DEPENDENCY CONTAINER
# =============================================================================

class DependencyContainer:
    """Dependency injection container."""

    def __init__(self):
        self._definitions: Dict[str, ComponentDef] = {}
        self._instances: Dict[str, Any] = {}
        self._scoped: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        factory: Optional[Callable] = None,
        instance: Any = None,
        scope: DependencyScope = DependencyScope.SINGLETON,
        dependencies: Optional[List[str]] = None
    ) -> ComponentDef:
        """Register a component."""
        definition = ComponentDef(
            name=name,
            factory=factory,
            instance=instance,
            scope=scope,
            dependencies=dependencies or []
        )

        self._definitions[name] = definition

        if instance is not None:
            self._instances[name] = instance

        return definition

    def resolve(self, name: str, scope_id: Optional[str] = None) -> Any:
        """Resolve a component."""
        definition = self._definitions.get(name)

        if not definition:
            raise KeyError(f"Component not found: {name}")

        if definition.scope == DependencyScope.SINGLETON:
            if name in self._instances:
                return self._instances[name]

            instance = self._create_instance(definition)
            self._instances[name] = instance
            return instance

        elif definition.scope == DependencyScope.TRANSIENT:
            return self._create_instance(definition)

        elif definition.scope == DependencyScope.SCOPED:
            if not scope_id:
                scope_id = "default"

            if scope_id not in self._scoped:
                self._scoped[scope_id] = {}

            if name in self._scoped[scope_id]:
                return self._scoped[scope_id][name]

            instance = self._create_instance(definition)
            self._scoped[scope_id][name] = instance
            return instance

        return None

    def _create_instance(self, definition: ComponentDef) -> Any:
        """Create component instance."""
        if definition.instance is not None:
            return definition.instance

        if definition.factory is None:
            raise ValueError(f"No factory for component: {definition.name}")

        deps = {}
        for dep_name in definition.dependencies:
            deps[dep_name] = self.resolve(dep_name)

        if deps:
            return definition.factory(**deps)
        else:
            return definition.factory()

    def has(self, name: str) -> bool:
        """Check if component registered."""
        return name in self._definitions

    def get_definition(self, name: str) -> Optional[ComponentDef]:
        """Get component definition."""
        return self._definitions.get(name)

    def clear_scope(self, scope_id: str) -> int:
        """Clear scoped instances."""
        if scope_id in self._scoped:
            count = len(self._scoped[scope_id])
            del self._scoped[scope_id]
            return count
        return 0

    def list_components(self) -> List[str]:
        """List registered components."""
        return list(self._definitions.keys())

    def count(self) -> int:
        """Count registered components."""
        return len(self._definitions)


# =============================================================================
# LIFECYCLE MANAGER
# =============================================================================

class LifecycleManager:
    """Manage component lifecycle."""

    def __init__(self):
        self._hooks: Dict[LifecycleHook, List[Callable]] = defaultdict(list)
        self._states: Dict[str, ComponentState] = {}

    def add_hook(self, hook: LifecycleHook, callback: Callable) -> None:
        """Add lifecycle hook."""
        self._hooks[hook].append(callback)

    async def _run_hooks(self, hook: LifecycleHook, component_id: str) -> None:
        """Run lifecycle hooks."""
        for callback in self._hooks[hook]:
            if asyncio.iscoroutinefunction(callback):
                await callback(component_id)
            else:
                callback(component_id)

    async def initialize(self, component_id: str, component: Any) -> bool:
        """Initialize component."""
        try:
            await self._run_hooks(LifecycleHook.PRE_INIT, component_id)

            if hasattr(component, "initialize"):
                if asyncio.iscoroutinefunction(component.initialize):
                    await component.initialize()
                else:
                    component.initialize()

            self._states[component_id] = ComponentState.INITIALIZED

            await self._run_hooks(LifecycleHook.POST_INIT, component_id)

            return True
        except Exception:
            self._states[component_id] = ComponentState.ERROR
            return False

    async def start(self, component_id: str, component: Any) -> bool:
        """Start component."""
        try:
            self._states[component_id] = ComponentState.STARTING

            await self._run_hooks(LifecycleHook.PRE_START, component_id)

            if hasattr(component, "start"):
                if asyncio.iscoroutinefunction(component.start):
                    await component.start()
                else:
                    component.start()

            self._states[component_id] = ComponentState.RUNNING

            await self._run_hooks(LifecycleHook.POST_START, component_id)

            return True
        except Exception:
            self._states[component_id] = ComponentState.ERROR
            return False

    async def stop(self, component_id: str, component: Any) -> bool:
        """Stop component."""
        try:
            self._states[component_id] = ComponentState.STOPPING

            await self._run_hooks(LifecycleHook.PRE_STOP, component_id)

            if hasattr(component, "stop"):
                if asyncio.iscoroutinefunction(component.stop):
                    await component.stop()
                else:
                    component.stop()

            self._states[component_id] = ComponentState.STOPPED

            await self._run_hooks(LifecycleHook.POST_STOP, component_id)

            return True
        except Exception:
            self._states[component_id] = ComponentState.ERROR
            return False

    def get_state(self, component_id: str) -> ComponentState:
        """Get component state."""
        return self._states.get(component_id, ComponentState.UNINITIALIZED)


# =============================================================================
# PIPELINE BUILDER
# =============================================================================

class PipelineBuilder:
    """Build processing pipelines."""

    def __init__(self, name: str):
        self._name = name
        self._stages: List[PipelineStage] = []
        self._mode = PipelineMode.SEQUENTIAL

    def add(
        self,
        name: str,
        handler: Callable,
        condition: Optional[Callable] = None
    ) -> "PipelineBuilder":
        """Add a stage."""
        stage = PipelineStage(
            name=name,
            handler=handler,
            order=len(self._stages),
            condition=condition
        )
        self._stages.append(stage)
        return self

    def parallel(self) -> "PipelineBuilder":
        """Set parallel mode."""
        self._mode = PipelineMode.PARALLEL
        return self

    def sequential(self) -> "PipelineBuilder":
        """Set sequential mode."""
        self._mode = PipelineMode.SEQUENTIAL
        return self

    def conditional(self) -> "PipelineBuilder":
        """Set conditional mode."""
        self._mode = PipelineMode.CONDITIONAL
        return self

    def build(self) -> Pipeline:
        """Build the pipeline."""
        return Pipeline(
            name=self._name,
            stages=self._stages,
            mode=self._mode
        )


# =============================================================================
# PIPELINE EXECUTOR
# =============================================================================

class PipelineExecutor:
    """Execute pipelines."""

    async def execute(self, pipeline: Pipeline, context: Any = None) -> Any:
        """Execute pipeline."""
        if pipeline.mode == PipelineMode.SEQUENTIAL:
            return await self._execute_sequential(pipeline, context)
        elif pipeline.mode == PipelineMode.PARALLEL:
            return await self._execute_parallel(pipeline, context)
        elif pipeline.mode == PipelineMode.CONDITIONAL:
            return await self._execute_conditional(pipeline, context)

        return context

    async def _execute_sequential(self, pipeline: Pipeline, context: Any) -> Any:
        """Execute stages sequentially."""
        result = context

        for stage in sorted(pipeline.stages, key=lambda s: s.order):
            if not stage.enabled:
                continue

            if stage.handler:
                if asyncio.iscoroutinefunction(stage.handler):
                    result = await stage.handler(result)
                else:
                    result = stage.handler(result)

        return result

    async def _execute_parallel(self, pipeline: Pipeline, context: Any) -> List[Any]:
        """Execute stages in parallel."""
        tasks = []

        for stage in pipeline.stages:
            if not stage.enabled:
                continue

            if stage.handler:
                if asyncio.iscoroutinefunction(stage.handler):
                    tasks.append(stage.handler(context))
                else:
                    async def wrap(h, c):
                        return h(c)
                    tasks.append(wrap(stage.handler, context))

        if tasks:
            return await asyncio.gather(*tasks)

        return []

    async def _execute_conditional(self, pipeline: Pipeline, context: Any) -> Any:
        """Execute stages conditionally."""
        result = context

        for stage in sorted(pipeline.stages, key=lambda s: s.order):
            if not stage.enabled:
                continue

            should_run = True
            if stage.condition:
                if asyncio.iscoroutinefunction(stage.condition):
                    should_run = await stage.condition(result)
                else:
                    should_run = stage.condition(result)

            if should_run and stage.handler:
                if asyncio.iscoroutinefunction(stage.handler):
                    result = await stage.handler(result)
                else:
                    result = stage.handler(result)

        return result


# =============================================================================
# COMPOSITE BUILDER
# =============================================================================

class CompositeBuilder:
    """Build composite components."""

    def __init__(self, container: DependencyContainer):
        self._container = container

    def aggregate(self, name: str, components: List[str]) -> CompositeComponent:
        """Create aggregation composite."""
        composite = CompositeComponent(
            name=name,
            components=components,
            composition_type=CompositionType.AGGREGATION
        )
        return composite

    def delegate(self, name: str, target: str) -> CompositeComponent:
        """Create delegation composite."""
        composite = CompositeComponent(
            name=name,
            components=[target],
            composition_type=CompositionType.DELEGATION
        )
        return composite

    def decorate(self, name: str, components: List[str]) -> CompositeComponent:
        """Create decoration chain."""
        composite = CompositeComponent(
            name=name,
            components=components,
            composition_type=CompositionType.DECORATION
        )
        return composite


# =============================================================================
# WIRING
# =============================================================================

class AutoWire:
    """Auto-wiring decorator."""

    def __init__(self, container: DependencyContainer):
        self._container = container

    def __call__(self, cls: Type[T]) -> Type[T]:
        """Wire dependencies into class."""
        original_init = cls.__init__
        container = self._container

        @wraps(original_init)
        def new_init(self, *args, **kwargs):
            annotations = getattr(cls, "__annotations__", {})

            for name, type_hint in annotations.items():
                if name not in kwargs and container.has(name):
                    kwargs[name] = container.resolve(name)

            original_init(self, *args, **kwargs)

        cls.__init__ = new_init
        return cls


# =============================================================================
# COMPOSITION ENGINE
# =============================================================================

class CompositionEngine:
    """
    Composition Engine for BAEL.

    System composition and component assembly.
    """

    def __init__(self, config: Optional[CompositionConfig] = None):
        self._config = config or CompositionConfig()

        self._container = DependencyContainer()
        self._lifecycle = LifecycleManager()
        self._executor = PipelineExecutor()

        self._pipelines: Dict[str, Pipeline] = {}
        self._composites: Dict[str, CompositeComponent] = {}

    # ----- Registration -----

    def register(
        self,
        name: str,
        factory: Optional[Callable] = None,
        instance: Any = None,
        scope: DependencyScope = DependencyScope.SINGLETON,
        dependencies: Optional[List[str]] = None
    ) -> ComponentDef:
        """Register a component."""
        return self._container.register(
            name, factory, instance, scope, dependencies
        )

    def register_instance(self, name: str, instance: Any) -> ComponentDef:
        """Register an instance."""
        return self._container.register(name, instance=instance)

    def register_factory(
        self,
        name: str,
        factory: Callable,
        scope: DependencyScope = DependencyScope.SINGLETON
    ) -> ComponentDef:
        """Register a factory."""
        return self._container.register(name, factory=factory, scope=scope)

    # ----- Resolution -----

    def resolve(self, name: str) -> Any:
        """Resolve a component."""
        return self._container.resolve(name)

    def has(self, name: str) -> bool:
        """Check if component exists."""
        return self._container.has(name)

    def wire(self, cls: Type[T]) -> Type[T]:
        """Auto-wire a class."""
        return AutoWire(self._container)(cls)

    # ----- Lifecycle -----

    def on_init(self, callback: Callable) -> None:
        """Add init hook."""
        self._lifecycle.add_hook(LifecycleHook.POST_INIT, callback)

    def on_start(self, callback: Callable) -> None:
        """Add start hook."""
        self._lifecycle.add_hook(LifecycleHook.POST_START, callback)

    def on_stop(self, callback: Callable) -> None:
        """Add stop hook."""
        self._lifecycle.add_hook(LifecycleHook.POST_STOP, callback)

    async def initialize(self, name: str) -> bool:
        """Initialize a component."""
        component = self._container.resolve(name)
        definition = self._container.get_definition(name)

        if not definition:
            return False

        result = await self._lifecycle.initialize(definition.component_id, component)
        definition.state = self._lifecycle.get_state(definition.component_id)

        return result

    async def start(self, name: str) -> bool:
        """Start a component."""
        component = self._container.resolve(name)
        definition = self._container.get_definition(name)

        if not definition:
            return False

        result = await self._lifecycle.start(definition.component_id, component)
        definition.state = self._lifecycle.get_state(definition.component_id)

        return result

    async def stop(self, name: str) -> bool:
        """Stop a component."""
        component = self._container.resolve(name)
        definition = self._container.get_definition(name)

        if not definition:
            return False

        result = await self._lifecycle.stop(definition.component_id, component)
        definition.state = self._lifecycle.get_state(definition.component_id)

        return result

    def get_state(self, name: str) -> ComponentState:
        """Get component state."""
        definition = self._container.get_definition(name)
        if definition:
            return definition.state
        return ComponentState.UNINITIALIZED

    # ----- Pipelines -----

    def pipeline(self, name: str) -> PipelineBuilder:
        """Create a pipeline builder."""
        return PipelineBuilder(name)

    def add_pipeline(self, pipeline: Pipeline) -> None:
        """Add a pipeline."""
        self._pipelines[pipeline.name] = pipeline

    def get_pipeline(self, name: str) -> Optional[Pipeline]:
        """Get a pipeline."""
        return self._pipelines.get(name)

    async def execute_pipeline(self, name: str, context: Any = None) -> Any:
        """Execute a pipeline."""
        pipeline = self._pipelines.get(name)

        if not pipeline:
            raise KeyError(f"Pipeline not found: {name}")

        return await self._executor.execute(pipeline, context)

    # ----- Composites -----

    def aggregate(self, name: str, components: List[str]) -> CompositeComponent:
        """Create aggregate composite."""
        builder = CompositeBuilder(self._container)
        composite = builder.aggregate(name, components)
        self._composites[name] = composite
        return composite

    def delegate(self, name: str, target: str) -> CompositeComponent:
        """Create delegation composite."""
        builder = CompositeBuilder(self._container)
        composite = builder.delegate(name, target)
        self._composites[name] = composite
        return composite

    def get_composite(self, name: str) -> Optional[CompositeComponent]:
        """Get a composite."""
        return self._composites.get(name)

    def resolve_composite(self, name: str) -> List[Any]:
        """Resolve all components in composite."""
        composite = self._composites.get(name)

        if not composite:
            return []

        return [self._container.resolve(c) for c in composite.components]

    # ----- Info -----

    def list_components(self) -> List[str]:
        """List all components."""
        return self._container.list_components()

    def list_pipelines(self) -> List[str]:
        """List all pipelines."""
        return list(self._pipelines.keys())

    def list_composites(self) -> List[str]:
        """List all composites."""
        return list(self._composites.keys())

    # ----- Summary -----

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        components = self._container.list_components()

        by_scope = defaultdict(int)
        by_state = defaultdict(int)

        for name in components:
            definition = self._container.get_definition(name)
            if definition:
                by_scope[definition.scope.value] += 1
                by_state[definition.state.value] += 1

        return {
            "components": len(components),
            "by_scope": dict(by_scope),
            "by_state": dict(by_state),
            "pipelines": len(self._pipelines),
            "composites": len(self._composites)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Composition Engine."""
    print("=" * 70)
    print("BAEL - COMPOSITION ENGINE DEMO")
    print("System Composition and Component Assembly")
    print("=" * 70)
    print()

    engine = CompositionEngine()

    # 1. Register Components
    print("1. REGISTER COMPONENTS:")
    print("-" * 40)

    class Database:
        def __init__(self):
            self.connected = False

        async def initialize(self):
            self.connected = True

        async def start(self):
            pass

        async def stop(self):
            self.connected = False

    class Cache:
        def __init__(self):
            self.data = {}

        def get(self, key):
            return self.data.get(key)

        def set(self, key, value):
            self.data[key] = value

    class Service:
        def __init__(self, database=None, cache=None):
            self.database = database
            self.cache = cache

        async def initialize(self):
            pass

        async def start(self):
            pass

        async def stop(self):
            pass

    engine.register_factory("database", Database)
    engine.register_factory("cache", Cache)
    engine.register(
        "service",
        factory=Service,
        dependencies=["database", "cache"]
    )

    print(f"   Registered: database, cache, service")
    print(f"   Total components: {engine._container.count()}")
    print()

    # 2. Resolve Components
    print("2. RESOLVE COMPONENTS:")
    print("-" * 40)

    db = engine.resolve("database")
    cache = engine.resolve("cache")
    service = engine.resolve("service")

    print(f"   Database: {type(db).__name__}")
    print(f"   Cache: {type(cache).__name__}")
    print(f"   Service: {type(service).__name__}")
    print(f"   Service.database: {type(service.database).__name__}")
    print(f"   Service.cache: {type(service.cache).__name__}")
    print()

    # 3. Singleton Behavior
    print("3. SINGLETON BEHAVIOR:")
    print("-" * 40)

    db2 = engine.resolve("database")
    print(f"   Same instance: {db is db2}")
    print()

    # 4. Transient Scope
    print("4. TRANSIENT SCOPE:")
    print("-" * 40)

    engine.register_factory(
        "transient_cache",
        Cache,
        scope=DependencyScope.TRANSIENT
    )

    t1 = engine.resolve("transient_cache")
    t2 = engine.resolve("transient_cache")

    print(f"   Same instance: {t1 is t2}")
    print()

    # 5. Lifecycle Management
    print("5. LIFECYCLE MANAGEMENT:")
    print("-" * 40)

    print(f"   Database state before: {engine.get_state('database').value}")

    await engine.initialize("database")
    print(f"   Database state after init: {engine.get_state('database').value}")

    await engine.start("database")
    print(f"   Database state after start: {engine.get_state('database').value}")

    await engine.stop("database")
    print(f"   Database state after stop: {engine.get_state('database').value}")
    print()

    # 6. Lifecycle Hooks
    print("6. LIFECYCLE HOOKS:")
    print("-" * 40)

    hooks_called = []

    engine.on_init(lambda cid: hooks_called.append(f"init:{cid}"))
    engine.on_start(lambda cid: hooks_called.append(f"start:{cid}"))
    engine.on_stop(lambda cid: hooks_called.append(f"stop:{cid}"))

    await engine.initialize("service")
    await engine.start("service")
    await engine.stop("service")

    print(f"   Hooks called: {len(hooks_called)}")
    for hook in hooks_called:
        print(f"   - {hook}")
    print()

    # 7. Build Pipeline
    print("7. BUILD PIPELINE:")
    print("-" * 40)

    def double(x):
        return x * 2

    def add_ten(x):
        return x + 10

    def square(x):
        return x ** 2

    pipeline = (engine.pipeline("math")
        .add("double", double)
        .add("add_ten", add_ten)
        .add("square", square)
        .build())

    engine.add_pipeline(pipeline)

    print(f"   Created pipeline: {pipeline.name}")
    print(f"   Stages: {len(pipeline.stages)}")
    print()

    # 8. Execute Pipeline
    print("8. EXECUTE PIPELINE:")
    print("-" * 40)

    result = await engine.execute_pipeline("math", 5)
    print(f"   Input: 5")
    print(f"   Stages: double -> add_ten -> square")
    print(f"   Result: {result}")
    print(f"   Expected: ((5 * 2) + 10) ^ 2 = 400")
    print()

    # 9. Parallel Pipeline
    print("9. PARALLEL PIPELINE:")
    print("-" * 40)

    async def async_op1(x):
        await asyncio.sleep(0.01)
        return x * 2

    async def async_op2(x):
        await asyncio.sleep(0.01)
        return x + 10

    async def async_op3(x):
        await asyncio.sleep(0.01)
        return x ** 2

    parallel_pipeline = (engine.pipeline("parallel_math")
        .add("op1", async_op1)
        .add("op2", async_op2)
        .add("op3", async_op3)
        .parallel()
        .build())

    engine.add_pipeline(parallel_pipeline)

    results = await engine.execute_pipeline("parallel_math", 5)
    print(f"   Input: 5")
    print(f"   Parallel results: {results}")
    print()

    # 10. Conditional Pipeline
    print("10. CONDITIONAL PIPELINE:")
    print("-" * 40)

    def is_positive(x):
        return x > 0

    def is_large(x):
        return x > 100

    cond_pipeline = (engine.pipeline("conditional")
        .add("double", double, condition=is_positive)
        .add("add_ten", add_ten, condition=is_positive)
        .add("square", square, condition=is_large)
        .conditional()
        .build())

    engine.add_pipeline(cond_pipeline)

    result = await engine.execute_pipeline("conditional", 50)
    print(f"   Input: 50")
    print(f"   Result: {result}")
    print(f"   (squared skipped because 110 > 100)")

    result2 = await engine.execute_pipeline("conditional", -5)
    print(f"   Input: -5")
    print(f"   Result: {result2}")
    print(f"   (all ops skipped because negative)")
    print()

    # 11. Aggregate Composite
    print("11. AGGREGATE COMPOSITE:")
    print("-" * 40)

    engine.aggregate("storage", ["database", "cache"])

    composite = engine.get_composite("storage")
    print(f"   Composite: {composite.name}")
    print(f"   Type: {composite.composition_type.value}")
    print(f"   Components: {composite.components}")

    resolved = engine.resolve_composite("storage")
    print(f"   Resolved: {[type(c).__name__ for c in resolved]}")
    print()

    # 12. Auto-wire
    print("12. AUTO-WIRE:")
    print("-" * 40)

    @engine.wire
    class Controller:
        database: Database
        cache: Cache

        def __init__(self, database=None, cache=None):
            self.database = database
            self.cache = cache

    controller = Controller()
    print(f"   Controller.database: {type(controller.database).__name__}")
    print(f"   Controller.cache: {type(controller.cache).__name__}")
    print()

    # 13. Check Component
    print("13. CHECK COMPONENT:")
    print("-" * 40)

    print(f"   has('database'): {engine.has('database')}")
    print(f"   has('nonexistent'): {engine.has('nonexistent')}")
    print()

    # 14. List All
    print("14. LIST ALL:")
    print("-" * 40)

    print(f"   Components: {engine.list_components()}")
    print(f"   Pipelines: {engine.list_pipelines()}")
    print(f"   Composites: {engine.list_composites()}")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Composition Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
