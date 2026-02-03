"""
Integration Layer for All Phases (Phase 1, 2, and 3)

Unified orchestration, dependency management, system initialization,
lifecycle management, and cross-system communication.
"""

import asyncio
import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SystemPhase(Enum):
    """System phases"""
    PHASE_1 = "phase1"  # Infrastructure
    PHASE_2 = "phase2"  # Orchestration
    PHASE_3 = "phase3"  # Advanced Systems


class SystemState(Enum):
    """System component states"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN = "shutdown"
    ERROR = "error"


@dataclass
class SystemComponent:
    """Represents a system component"""
    name: str
    phase: SystemPhase
    version: str
    state: SystemState = SystemState.UNINITIALIZED
    dependencies: List[str] = field(default_factory=list)
    init_priority: int = 0  # Lower = earlier initialization
    critical: bool = False  # Critical for system operation
    instance: Optional[Any] = None
    initialized_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DependencyResolver:
    """Resolves component dependencies"""

    def __init__(self):
        self.components: Dict[str, SystemComponent] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}

    def register_component(self, component: SystemComponent):
        """Register a component"""
        self.components[component.name] = component
        self.dependency_graph[component.name] = set(component.dependencies)
        logger.debug(f"Registered component: {component.name}")

    def get_initialization_order(self) -> List[str]:
        """Get component initialization order using topological sort"""
        visited = set()
        visiting = set()
        order = []

        def visit(node: str):
            if node in visited:
                return
            if node in visiting:
                raise ValueError(f"Circular dependency detected: {node}")

            visiting.add(node)

            if node in self.dependency_graph:
                for dep in self.dependency_graph[node]:
                    visit(dep)

            visiting.remove(node)
            visited.add(node)
            order.append(node)

        for component in self.components:
            visit(component)

        # Sort by priority
        component_list = [self.components[name] for name in order]
        component_list.sort(key=lambda c: c.init_priority)

        return [c.name for c in component_list]

    def validate_dependencies(self) -> Tuple[bool, List[str]]:
        """Validate all dependencies exist"""
        errors = []

        for component_name, deps in self.dependency_graph.items():
            for dep in deps:
                if dep not in self.components:
                    errors.append(f"{component_name} depends on missing {dep}")

        return len(errors) == 0, errors


class SystemInitializer:
    """Initializes and manages system components"""

    def __init__(self):
        self.resolver = DependencyResolver()
        self.components: Dict[str, SystemComponent] = {}
        self.state = SystemState.UNINITIALIZED
        self.initialized_components: List[str] = []
        self.start_time = datetime.now()

    def register_component(self, component: SystemComponent):
        """Register a system component"""
        self.resolver.register_component(component)
        self.components[component.name] = component
        logger.info(f"Registered {component.phase.value} component: {component.name}")

    async def initialize_system(self) -> bool:
        """Initialize all components in correct order"""
        self.state = SystemState.INITIALIZING
        logger.info("Starting system initialization...")

        # Validate dependencies
        valid, errors = self.resolver.validate_dependencies()
        if not valid:
            logger.error(f"Dependency validation failed: {errors}")
            self.state = SystemState.ERROR
            return False

        # Get initialization order
        init_order = self.resolver.get_initialization_order()
        logger.info(f"Initialization order: {init_order}")

        # Initialize components
        for component_name in init_order:
            component = self.components[component_name]

            # Check if dependencies are ready
            deps_ready = all(
                self.components[dep].state == SystemState.READY
                for dep in component.dependencies
            )

            if not deps_ready:
                logger.error(f"Dependencies not ready for {component_name}")
                if component.critical:
                    self.state = SystemState.ERROR
                    return False
                continue

            try:
                component.state = SystemState.INITIALIZING
                logger.info(f"Initializing {component.phase.value}: {component.name}")

                if hasattr(component.instance, 'initialize'):
                    await component.instance.initialize()

                component.state = SystemState.READY
                component.initialized_at = datetime.now()
                self.initialized_components.append(component_name)

                logger.info(f"✓ Initialized: {component.name}")

            except Exception as e:
                logger.error(f"Error initializing {component.name}: {e}")
                component.state = SystemState.ERROR
                component.error = str(e)

                if component.critical:
                    self.state = SystemState.ERROR
                    return False

        self.state = SystemState.READY
        logger.info(f"✓ System initialized successfully ({len(self.initialized_components)} components)")
        return True

    async def start_system(self) -> bool:
        """Start all components"""
        if self.state != SystemState.READY:
            logger.error(f"Cannot start system in state: {self.state}")
            return False

        self.state = SystemState.RUNNING
        logger.info("Starting system...")

        for component_name in self.initialized_components:
            component = self.components[component_name]
            try:
                if hasattr(component.instance, 'start'):
                    await component.instance.start()
                component.state = SystemState.RUNNING
                logger.info(f"Started: {component.name}")
            except Exception as e:
                logger.error(f"Error starting {component.name}: {e}")
                if component.critical:
                    self.state = SystemState.ERROR
                    return False

        logger.info("✓ System started successfully")
        return True

    async def shutdown_system(self):
        """Shutdown all components"""
        if self.state == SystemState.SHUTDOWN:
            return

        self.state = SystemState.SHUTTING_DOWN
        logger.info("Shutting down system...")

        # Shutdown in reverse order
        for component_name in reversed(self.initialized_components):
            component = self.components[component_name]
            try:
                if hasattr(component.instance, 'shutdown'):
                    await component.instance.shutdown()
                component.state = SystemState.SHUTDOWN
                logger.info(f"Shutdown: {component.name}")
            except Exception as e:
                logger.error(f"Error shutting down {component.name}: {e}")

        self.state = SystemState.SHUTDOWN
        logger.info("✓ System shutdown complete")

    def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        components_status = {}
        for name, component in self.components.items():
            components_status[name] = {
                "phase": component.phase.value,
                "state": component.state.value,
                "version": component.version,
                "initialized_at": component.initialized_at.isoformat() if component.initialized_at else None,
                "error": component.error,
                "critical": component.critical
            }

        return {
            "overall_state": self.state.value,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "initialized_components": len(self.initialized_components),
            "total_components": len(self.components),
            "components": components_status
        }

    def get_component_dependencies(self, component_name: str) -> Dict[str, Any]:
        """Get component dependencies"""
        component = self.components.get(component_name)
        if not component:
            return {}

        return {
            "component": component_name,
            "dependencies": component.dependencies,
            "dependents": [
                name for name, comp in self.components.items()
                if component_name in comp.dependencies
            ],
            "state": component.state.value
        }


class SystemBridge:
    """Bridges communication between system phases"""

    def __init__(self):
        self.message_handlers: Dict[str, List[Callable]] = {}
        self.request_handlers: Dict[str, Callable] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()

    def subscribe(self, event_type: str, handler: Callable):
        """Subscribe to events"""
        if event_type not in self.message_handlers:
            self.message_handlers[event_type] = []
        self.message_handlers[event_type].append(handler)
        logger.debug(f"Subscribed to {event_type}")

    def register_request_handler(self, request_type: str, handler: Callable):
        """Register request handler"""
        self.request_handlers[request_type] = handler
        logger.debug(f"Registered request handler: {request_type}")

    async def publish_event(self, event_type: str, data: Any):
        """Publish event to all subscribers"""
        await self.message_queue.put(("event", event_type, data))

        handlers = self.message_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")

    async def request(self, request_type: str, data: Any) -> Any:
        """Send request and wait for response"""
        handler = self.request_handlers.get(request_type)
        if not handler:
            logger.error(f"No handler for request type: {request_type}")
            return None

        try:
            if asyncio.iscoroutinefunction(handler):
                return await handler(data)
            else:
                return handler(data)
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return None


class IntegrationManager:
    """Manages integration of all system phases"""

    def __init__(self):
        self.initializer = SystemInitializer()
        self.bridge = SystemBridge()
        self.phase1_systems: Dict[str, SystemComponent] = {}
        self.phase2_systems: Dict[str, SystemComponent] = {}
        self.phase3_systems: Dict[str, SystemComponent] = {}

    def register_phase1_system(self, component: SystemComponent):
        """Register Phase 1 infrastructure system"""
        self.phase1_systems[component.name] = component
        self.initializer.register_component(component)

    def register_phase2_system(self, component: SystemComponent):
        """Register Phase 2 orchestration system"""
        self.phase2_systems[component.name] = component
        self.initializer.register_component(component)

    def register_phase3_system(self, component: SystemComponent):
        """Register Phase 3 advanced system"""
        self.phase3_systems[component.name] = component
        self.initializer.register_component(component)

    async def initialize(self) -> bool:
        """Initialize all systems"""
        logger.info("=" * 60)
        logger.info("BAEL FULL SYSTEM INITIALIZATION")
        logger.info("=" * 60)

        success = await self.initializer.initialize_system()

        if success:
            logger.info("\n" + "=" * 60)
            logger.info("✓ ALL SYSTEMS INITIALIZED SUCCESSFULLY")
            logger.info("=" * 60)

        return success

    async def start(self) -> bool:
        """Start all systems"""
        logger.info("Starting all systems...")
        return await self.initializer.start_system()

    async def shutdown(self):
        """Shutdown all systems"""
        logger.info("Shutting down all systems...")
        await self.initializer.shutdown_system()

    def get_system_overview(self) -> Dict[str, Any]:
        """Get overview of all systems"""
        status = self.initializer.get_system_status()

        return {
            "overall_status": status,
            "phase1_systems": len(self.phase1_systems),
            "phase2_systems": len(self.phase2_systems),
            "phase3_systems": len(self.phase3_systems),
            "total_systems": len(self.initializer.components),
            "initialized": len(self.initializer.initialized_components)
        }

    def publish_event(self, event_type: str, data: Any):
        """Publish event across systems"""
        asyncio.create_task(self.bridge.publish_event(event_type, data))

    async def request(self, request_type: str, data: Any) -> Any:
        """Send cross-system request"""
        return await self.bridge.request(request_type, data)


# Global integration manager
_integration_manager = None


def get_integration_manager() -> IntegrationManager:
    """Get global integration manager"""
    global _integration_manager
    if _integration_manager is None:
        _integration_manager = IntegrationManager()
    return _integration_manager


def initialize_bael_system(components_list: List[Tuple[SystemPhase, SystemComponent]]) -> IntegrationManager:
    """Initialize complete BAEL system with all components"""
    manager = get_integration_manager()

    for phase, component in components_list:
        if phase == SystemPhase.PHASE_1:
            manager.register_phase1_system(component)
        elif phase == SystemPhase.PHASE_2:
            manager.register_phase2_system(component)
        elif phase == SystemPhase.PHASE_3:
            manager.register_phase3_system(component)

    return manager


if __name__ == "__main__":
    logger.info("Integration Layer initialized")
