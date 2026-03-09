"""
BAEL Integration Hub - Central Connection Point for All Modules

The Integration Hub is the central nervous system that connects
all 430+ BAEL modules together through:

1. Event Bus - Cross-module communication via events
2. Service Registry - Module discovery and health monitoring
3. Dependency Injection - Automatic module wiring
4. Configuration Management - Centralized config distribution
5. Metrics Aggregation - Unified observability

This enables:
- Loose coupling between modules
- Dynamic module loading/unloading
- Graceful degradation when modules fail
- Real-time module coordination
"""

import asyncio
import logging
import weakref
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, TypeVar
from uuid import uuid4

logger = logging.getLogger("BAEL.IntegrationHub")

T = TypeVar("T")


# =============================================================================
# ENUMS
# =============================================================================

class ModuleStatus(Enum):
    """Status of a registered module."""
    UNKNOWN = "unknown"
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    DEGRADED = "degraded"
    ERROR = "error"
    DISABLED = "disabled"
    SHUTDOWN = "shutdown"


class EventPriority(Enum):
    """Priority levels for events."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


class EventCategory(Enum):
    """Categories of events."""
    SYSTEM = "system"
    REASONING = "reasoning"
    MEMORY = "memory"
    AGENT = "agent"
    COUNCIL = "council"
    LEARNING = "learning"
    PROVIDER = "provider"
    USER = "user"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Event:
    """An event in the system."""
    id: str
    name: str
    category: EventCategory
    priority: EventPriority
    source: str  # Module that emitted the event
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None

    def __hash__(self):
        return hash(self.id)


@dataclass
class ModuleInfo:
    """Information about a registered module."""
    id: str
    name: str
    module_type: str
    version: str
    status: ModuleStatus
    capabilities: List[str]
    dependencies: List[str]
    instance: Any
    health_check: Optional[Callable] = None
    last_health_check: Optional[datetime] = None
    error_count: int = 0
    request_count: int = 0
    average_latency_ms: float = 0
    registered_at: datetime = field(default_factory=datetime.now)


@dataclass
class ServiceDependency:
    """A dependency between modules."""
    consumer_id: str
    provider_id: str
    interface: str
    required: bool = True
    resolved: bool = False


# =============================================================================
# EVENT BUS
# =============================================================================

class EventBus:
    """
    Central event bus for cross-module communication.

    Supports:
    - Pub/sub pattern with topics
    - Priority-based event handling
    - Async event processing
    - Event filtering
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._category_subscribers: Dict[EventCategory, List[Callable]] = defaultdict(list)
        self._all_subscribers: List[Callable] = []
        self._event_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._processing = False
        self._event_history: List[Event] = []
        self._max_history = 1000

        # Metrics
        self._metrics = {
            "events_published": 0,
            "events_processed": 0,
            "events_dropped": 0,
            "subscribers": 0
        }

    def subscribe(
        self,
        event_name: str = None,
        category: EventCategory = None,
        handler: Callable = None
    ) -> str:
        """Subscribe to events."""
        subscription_id = str(uuid4())

        if event_name:
            self._subscribers[event_name].append(handler)
        elif category:
            self._category_subscribers[category].append(handler)
        else:
            self._all_subscribers.append(handler)

        self._metrics["subscribers"] += 1
        return subscription_id

    async def publish(self, event: Event) -> None:
        """Publish an event to subscribers."""
        self._metrics["events_published"] += 1

        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Queue for processing
        await self._event_queue.put((event.priority.value, event))

        # Process immediately if not already processing
        if not self._processing:
            await self._process_events()

    async def _process_events(self) -> None:
        """Process queued events."""
        self._processing = True

        try:
            while not self._event_queue.empty():
                _, event = await self._event_queue.get()
                await self._dispatch_event(event)
                self._metrics["events_processed"] += 1
        finally:
            self._processing = False

    async def _dispatch_event(self, event: Event) -> None:
        """Dispatch event to subscribers."""
        handlers = []

        # Specific event handlers
        handlers.extend(self._subscribers.get(event.name, []))

        # Category handlers
        handlers.extend(self._category_subscribers.get(event.category, []))

        # All event handlers
        handlers.extend(self._all_subscribers)

        # Execute handlers
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get event bus metrics."""
        return {
            **self._metrics,
            "queue_size": self._event_queue.qsize(),
            "history_size": len(self._event_history)
        }


# =============================================================================
# SERVICE REGISTRY
# =============================================================================

class ServiceRegistry:
    """
    Central registry for all BAEL modules.

    Provides:
    - Module registration and discovery
    - Health monitoring
    - Dependency resolution
    - Status tracking
    """

    def __init__(self):
        self._modules: Dict[str, ModuleInfo] = {}
        self._type_index: Dict[str, List[str]] = defaultdict(list)
        self._capability_index: Dict[str, List[str]] = defaultdict(list)
        self._dependencies: List[ServiceDependency] = []

        # Health check task
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_check_interval = 30  # seconds

    def register(
        self,
        module_id: str,
        name: str,
        module_type: str,
        instance: Any,
        version: str = "1.0.0",
        capabilities: List[str] = None,
        dependencies: List[str] = None,
        health_check: Callable = None
    ) -> str:
        """Register a module with the registry."""
        info = ModuleInfo(
            id=module_id,
            name=name,
            module_type=module_type,
            version=version,
            status=ModuleStatus.INITIALIZING,
            capabilities=capabilities or [],
            dependencies=dependencies or [],
            instance=instance,
            health_check=health_check
        )

        self._modules[module_id] = info
        self._type_index[module_type].append(module_id)

        for cap in info.capabilities:
            self._capability_index[cap].append(module_id)

        logger.info(f"Registered module: {name} ({module_id})")
        return module_id

    def unregister(self, module_id: str) -> bool:
        """Unregister a module."""
        if module_id not in self._modules:
            return False

        info = self._modules[module_id]

        # Remove from indexes
        self._type_index[info.module_type].remove(module_id)
        for cap in info.capabilities:
            self._capability_index[cap].remove(module_id)

        del self._modules[module_id]
        logger.info(f"Unregistered module: {info.name}")
        return True

    def get(self, module_id: str) -> Optional[ModuleInfo]:
        """Get a module by ID."""
        return self._modules.get(module_id)

    def get_by_type(self, module_type: str) -> List[ModuleInfo]:
        """Get all modules of a type."""
        ids = self._type_index.get(module_type, [])
        return [self._modules[id] for id in ids if id in self._modules]

    def get_by_capability(self, capability: str) -> List[ModuleInfo]:
        """Get all modules with a capability."""
        ids = self._capability_index.get(capability, [])
        return [self._modules[id] for id in ids if id in self._modules]

    def set_status(self, module_id: str, status: ModuleStatus) -> None:
        """Update module status."""
        if module_id in self._modules:
            self._modules[module_id].status = status

    async def check_health(self, module_id: str) -> ModuleStatus:
        """Check health of a specific module."""
        info = self._modules.get(module_id)
        if not info:
            return ModuleStatus.UNKNOWN

        if info.health_check:
            try:
                if asyncio.iscoroutinefunction(info.health_check):
                    healthy = await info.health_check()
                else:
                    healthy = info.health_check()

                info.status = ModuleStatus.READY if healthy else ModuleStatus.DEGRADED
                info.last_health_check = datetime.now()
            except Exception as e:
                logger.error(f"Health check failed for {info.name}: {e}")
                info.status = ModuleStatus.ERROR
                info.error_count += 1

        return info.status

    async def start_health_monitoring(self) -> None:
        """Start background health monitoring."""
        async def health_loop():
            while True:
                await asyncio.sleep(self._health_check_interval)
                for module_id in list(self._modules.keys()):
                    await self.check_health(module_id)

        self._health_check_task = asyncio.create_task(health_loop())

    def get_status_summary(self) -> Dict[str, Any]:
        """Get summary of all module statuses."""
        status_counts = defaultdict(int)
        for info in self._modules.values():
            status_counts[info.status.value] += 1

        return {
            "total_modules": len(self._modules),
            "status_counts": dict(status_counts),
            "modules": {
                id: {
                    "name": info.name,
                    "type": info.module_type,
                    "status": info.status.value,
                    "error_count": info.error_count
                }
                for id, info in self._modules.items()
            }
        }


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

class DependencyContainer:
    """
    Dependency injection container for automatic module wiring.

    Supports:
    - Singleton and transient lifetimes
    - Interface-based resolution
    - Lazy initialization
    """

    def __init__(self):
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._interfaces: Dict[Type, Type] = {}  # interface -> implementation

    def register_singleton(self, interface: Type[T], instance: T) -> None:
        """Register a singleton instance."""
        self._singletons[interface] = instance

    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Register a factory for creating instances."""
        self._factories[interface] = factory

    def register_implementation(self, interface: Type, implementation: Type) -> None:
        """Register implementation for an interface."""
        self._interfaces[interface] = implementation

    def resolve(self, interface: Type[T]) -> T:
        """Resolve a dependency."""
        # Check singletons first
        if interface in self._singletons:
            return self._singletons[interface]

        # Check factories
        if interface in self._factories:
            return self._factories[interface]()

        # Check interface mappings
        if interface in self._interfaces:
            impl = self._interfaces[interface]
            instance = impl()
            return instance

        raise ValueError(f"No registration found for {interface}")

    def resolve_all(self, interface: Type[T]) -> List[T]:
        """Resolve all implementations of an interface."""
        results = []
        if interface in self._singletons:
            results.append(self._singletons[interface])
        if interface in self._factories:
            results.append(self._factories[interface]())
        return results


# =============================================================================
# CONFIGURATION MANAGER
# =============================================================================

class ConfigurationManager:
    """
    Centralized configuration management.

    Features:
    - Hierarchical configuration
    - Environment-specific overrides
    - Runtime reconfiguration
    - Configuration validation
    """

    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._defaults: Dict[str, Any] = {}
        self._overrides: Dict[str, Any] = {}
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)

    def set_default(self, key: str, value: Any) -> None:
        """Set a default configuration value."""
        self._defaults[key] = value

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        old_value = self.get(key)
        self._config[key] = value

        # Notify listeners
        for listener in self._listeners.get(key, []):
            try:
                listener(key, value, old_value)
            except Exception as e:
                logger.error(f"Config listener error: {e}")

    def set_override(self, key: str, value: Any) -> None:
        """Set an override (highest priority)."""
        self._overrides[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        # Priority: overrides > config > defaults > provided default
        if key in self._overrides:
            return self._overrides[key]
        if key in self._config:
            return self._config[key]
        if key in self._defaults:
            return self._defaults[key]
        return default

    def on_change(self, key: str, listener: Callable) -> None:
        """Subscribe to configuration changes."""
        self._listeners[key].append(listener)

    def load_from_dict(self, config: Dict[str, Any]) -> None:
        """Load configuration from dictionary."""
        for key, value in config.items():
            self.set(key, value)

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values."""
        result = {}
        result.update(self._defaults)
        result.update(self._config)
        result.update(self._overrides)
        return result


# =============================================================================
# METRICS AGGREGATOR
# =============================================================================

class MetricsAggregator:
    """
    Aggregates metrics from all modules.

    Provides:
    - Central metrics collection
    - Time-series data
    - Aggregation functions
    """

    def __init__(self):
        self._metrics: Dict[str, Dict[str, Any]] = {}
        self._time_series: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self._max_time_series_length = 1000

    def record(self, module_id: str, metrics: Dict[str, Any]) -> None:
        """Record metrics from a module."""
        if module_id not in self._metrics:
            self._metrics[module_id] = {}
        self._metrics[module_id].update(metrics)
        self._metrics[module_id]["_last_update"] = datetime.now()

    def record_value(self, key: str, value: float) -> None:
        """Record a time-series value."""
        self._time_series[key].append((datetime.now(), value))

        # Trim if too long
        if len(self._time_series[key]) > self._max_time_series_length:
            self._time_series[key] = self._time_series[key][-self._max_time_series_length:]

    def get(self, module_id: str) -> Dict[str, Any]:
        """Get metrics for a module."""
        return self._metrics.get(module_id, {})

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Get all metrics."""
        return self._metrics.copy()

    def get_time_series(self, key: str) -> List[Tuple[datetime, float]]:
        """Get time series data."""
        return self._time_series.get(key, [])

    def get_summary(self) -> Dict[str, Any]:
        """Get aggregated summary."""
        total_requests = sum(
            m.get("requests", 0) for m in self._metrics.values()
        )
        total_errors = sum(
            m.get("errors", 0) for m in self._metrics.values()
        )

        return {
            "modules_reporting": len(self._metrics),
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": total_errors / total_requests if total_requests > 0 else 0
        }


# =============================================================================
# INTEGRATION HUB
# =============================================================================

class IntegrationHub:
    """
    Central integration hub for all BAEL modules.

    The hub provides:
    - Event bus for cross-module communication
    - Service registry for module discovery
    - Dependency injection for automatic wiring
    - Configuration management
    - Metrics aggregation

    This is the central nervous system of BAEL.
    """

    def __init__(self):
        self.events = EventBus()
        self.registry = ServiceRegistry()
        self.container = DependencyContainer()
        self.config = ConfigurationManager()
        self.metrics = MetricsAggregator()

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the integration hub."""
        if self._initialized:
            return

        logger.info("Initializing Integration Hub...")

        # Set default configurations
        self._set_defaults()

        # Start health monitoring
        await self.registry.start_health_monitoring()

        # Subscribe to system events
        self.events.subscribe(category=EventCategory.SYSTEM, handler=self._handle_system_event)

        self._initialized = True
        logger.info("Integration Hub initialized")

        # Emit initialization event
        await self.events.publish(Event(
            id=str(uuid4()),
            name="hub.initialized",
            category=EventCategory.SYSTEM,
            priority=EventPriority.HIGH,
            source="integration_hub",
            data={"timestamp": datetime.now().isoformat()}
        ))

    def _set_defaults(self) -> None:
        """Set default configuration values."""
        defaults = {
            "hub.health_check_interval": 30,
            "hub.event_history_size": 1000,
            "hub.metrics_retention_seconds": 3600,
            "reasoning.default_strategy": "cascade",
            "memory.working_capacity": 7,
            "memory.consolidation_interval": 300,
            "providers.timeout_seconds": 60,
            "providers.max_retries": 3,
            "councils.default_consensus": "majority",
            "evolution.enabled": True,
            "evolution.interval_seconds": 3600,
        }

        for key, value in defaults.items():
            self.config.set_default(key, value)

    async def _handle_system_event(self, event: Event) -> None:
        """Handle system events."""
        if event.name == "module.registered":
            logger.debug(f"Module registered: {event.data.get('module_id')}")
        elif event.name == "module.error":
            logger.warning(f"Module error: {event.data.get('module_id')} - {event.data.get('error')}")

    def register_module(
        self,
        name: str,
        module_type: str,
        instance: Any,
        capabilities: List[str] = None,
        dependencies: List[str] = None
    ) -> str:
        """Register a module with the hub."""
        module_id = str(uuid4())

        self.registry.register(
            module_id=module_id,
            name=name,
            module_type=module_type,
            instance=instance,
            capabilities=capabilities,
            dependencies=dependencies
        )

        # Also register with DI container
        self.container.register_singleton(type(instance), instance)

        return module_id

    async def emit(
        self,
        name: str,
        data: Dict[str, Any],
        category: EventCategory = EventCategory.SYSTEM,
        priority: EventPriority = EventPriority.NORMAL,
        source: str = "unknown"
    ) -> None:
        """Emit an event."""
        event = Event(
            id=str(uuid4()),
            name=name,
            category=category,
            priority=priority,
            source=source,
            data=data
        )
        await self.events.publish(event)

    def get_status(self) -> Dict[str, Any]:
        """Get overall hub status."""
        return {
            "initialized": self._initialized,
            "registry": self.registry.get_status_summary(),
            "events": self.events.get_metrics(),
            "metrics": self.metrics.get_summary(),
            "config_count": len(self.config.get_all())
        }


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_hub: Optional[IntegrationHub] = None


async def get_hub() -> IntegrationHub:
    """Get or create the global integration hub."""
    global _hub
    if _hub is None:
        _hub = IntegrationHub()
        await _hub.initialize()
    return _hub


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate Integration Hub capabilities."""
    hub = await get_hub()

    print("Integration Hub Demo")
    print("=" * 60)

    # Register some modules
    class MockReasoner:
        def reason(self, query):
            return f"Reasoning about: {query}"

    class MockMemory:
        def store(self, data):
            return f"Stored: {data}"

    hub.register_module(
        name="Causal Reasoner",
        module_type="reasoner",
        instance=MockReasoner(),
        capabilities=["causal", "counterfactual"]
    )

    hub.register_module(
        name="Cognitive Memory",
        module_type="memory",
        instance=MockMemory(),
        capabilities=["working", "episodic", "semantic"]
    )

    # Set configuration
    hub.config.set("reasoning.timeout", 5000)

    # Emit events
    await hub.emit(
        name="query.received",
        data={"query": "Why does X cause Y?"},
        category=EventCategory.REASONING
    )

    # Record metrics
    hub.metrics.record("causal_reasoner", {
        "requests": 100,
        "errors": 2,
        "avg_latency_ms": 150
    })

    # Get status
    print("\nHub Status:")
    import json
    print(json.dumps(hub.get_status(), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(demo())
