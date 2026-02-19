"""
BAEL Dependency Injection Engine Implementation
===============================================

Inversion of Control container for dependency injection.

"Ba'el orchestrates all dependencies with divine precision." — Ba'el
"""

import asyncio
import functools
import inspect
import logging
import threading
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Generic, get_type_hints
from dataclasses import dataclass, field
from enum import Enum
from contextvars import ContextVar

logger = logging.getLogger("BAEL.DI")

T = TypeVar('T')


# ============================================================================
# ENUMS
# ============================================================================

class Scope(Enum):
    """Service lifetime scopes."""
    TRANSIENT = "transient"    # New instance each time
    SINGLETON = "singleton"    # One instance for container
    SCOPED = "scoped"          # One instance per scope
    THREAD = "thread"          # One instance per thread


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ServiceDescriptor:
    """Describes a registered service."""
    service_type: Type

    # Implementation
    implementation_type: Optional[Type] = None
    factory: Optional[Callable] = None
    instance: Any = None

    # Lifecycle
    scope: Scope = Scope.SINGLETON

    # Dependencies
    dependencies: List[Type] = field(default_factory=list)

    # Metadata
    name: Optional[str] = None
    tags: List[str] = field(default_factory=list)


# ============================================================================
# SCOPE CONTEXT
# ============================================================================

_scope_context: ContextVar[Optional[Dict[Type, Any]]] = ContextVar(
    'di_scope',
    default=None
)


class ScopeContext:
    """Context manager for scoped services."""

    def __init__(self, container: 'Container'):
        self.container = container
        self._instances: Dict[Type, Any] = {}
        self._token = None

    def __enter__(self) -> 'ScopeContext':
        self._token = _scope_context.set(self._instances)
        return self

    def __exit__(self, *args):
        _scope_context.reset(self._token)

        # Dispose scoped instances
        for instance in self._instances.values():
            if hasattr(instance, 'dispose'):
                instance.dispose()

    async def __aenter__(self) -> 'ScopeContext':
        return self.__enter__()

    async def __aexit__(self, *args):
        _scope_context.reset(self._token)

        for instance in self._instances.values():
            if hasattr(instance, 'dispose'):
                if asyncio.iscoroutinefunction(instance.dispose):
                    await instance.dispose()
                else:
                    instance.dispose()


# ============================================================================
# MAIN CONTAINER
# ============================================================================

class Container:
    """
    Dependency Injection Container.

    Features:
    - Multiple scopes (transient, singleton, scoped, thread)
    - Constructor injection
    - Factory functions
    - Lazy resolution
    - Async support

    "Ba'el's container holds the essence of all services." — Ba'el
    """

    def __init__(self):
        """Initialize container."""
        # Service descriptors: type -> descriptor
        self._descriptors: Dict[Type, ServiceDescriptor] = {}

        # Named services: name -> type
        self._named: Dict[str, Type] = {}

        # Singleton instances
        self._singletons: Dict[Type, Any] = {}

        # Thread-local instances
        self._thread_local = threading.local()

        self._lock = threading.RLock()

        logger.info("DI Container initialized")

    # ========================================================================
    # REGISTRATION
    # ========================================================================

    def register(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        instance: Optional[T] = None,
        scope: Scope = Scope.SINGLETON,
        name: Optional[str] = None
    ) -> 'Container':
        """
        Register a service.

        Args:
            service_type: Service interface/type
            implementation: Implementation class
            factory: Factory function
            instance: Pre-created instance
            scope: Lifetime scope
            name: Optional service name

        Returns:
            Self for chaining
        """
        with self._lock:
            # Determine dependencies from constructor
            dependencies = []
            impl = implementation or service_type

            if impl and not factory and not instance:
                dependencies = self._get_dependencies(impl)

            descriptor = ServiceDescriptor(
                service_type=service_type,
                implementation_type=implementation or service_type,
                factory=factory,
                instance=instance,
                scope=scope,
                dependencies=dependencies,
                name=name
            )

            self._descriptors[service_type] = descriptor

            if name:
                self._named[name] = service_type

            # If instance provided, it's effectively a singleton
            if instance:
                self._singletons[service_type] = instance

        return self

    def register_singleton(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None
    ) -> 'Container':
        """Register as singleton."""
        return self.register(service_type, implementation, scope=Scope.SINGLETON)

    def register_transient(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None
    ) -> 'Container':
        """Register as transient."""
        return self.register(service_type, implementation, scope=Scope.TRANSIENT)

    def register_scoped(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None
    ) -> 'Container':
        """Register as scoped."""
        return self.register(service_type, implementation, scope=Scope.SCOPED)

    def register_factory(
        self,
        service_type: Type[T],
        factory: Callable[[], T],
        scope: Scope = Scope.TRANSIENT
    ) -> 'Container':
        """Register with factory."""
        return self.register(service_type, factory=factory, scope=scope)

    def register_instance(
        self,
        service_type: Type[T],
        instance: T
    ) -> 'Container':
        """Register existing instance."""
        return self.register(service_type, instance=instance)

    # ========================================================================
    # RESOLUTION
    # ========================================================================

    def resolve(self, service_type: Type[T]) -> T:
        """
        Resolve a service.

        Args:
            service_type: Service type to resolve

        Returns:
            Service instance
        """
        with self._lock:
            descriptor = self._descriptors.get(service_type)

        if not descriptor:
            raise KeyError(f"Service not registered: {service_type}")

        return self._resolve_descriptor(descriptor)

    def resolve_optional(self, service_type: Type[T]) -> Optional[T]:
        """Resolve service, returning None if not registered."""
        try:
            return self.resolve(service_type)
        except KeyError:
            return None

    def resolve_by_name(self, name: str) -> Any:
        """Resolve service by name."""
        with self._lock:
            service_type = self._named.get(name)

        if not service_type:
            raise KeyError(f"Named service not found: {name}")

        return self.resolve(service_type)

    def resolve_all(self, base_type: Type[T]) -> List[T]:
        """Resolve all services of a base type."""
        results = []

        with self._lock:
            for service_type, descriptor in self._descriptors.items():
                if (service_type != base_type and
                    issubclass(descriptor.implementation_type or service_type, base_type)):
                    results.append(self._resolve_descriptor(descriptor))

        return results

    def _resolve_descriptor(self, descriptor: ServiceDescriptor) -> Any:
        """Resolve a service descriptor."""
        # Check for existing instance based on scope
        if descriptor.scope == Scope.SINGLETON:
            if descriptor.service_type in self._singletons:
                return self._singletons[descriptor.service_type]

        elif descriptor.scope == Scope.SCOPED:
            scope_instances = _scope_context.get()
            if scope_instances is not None:
                if descriptor.service_type in scope_instances:
                    return scope_instances[descriptor.service_type]

        elif descriptor.scope == Scope.THREAD:
            if hasattr(self._thread_local, 'instances'):
                if descriptor.service_type in self._thread_local.instances:
                    return self._thread_local.instances[descriptor.service_type]

        # Create instance
        if descriptor.instance:
            instance = descriptor.instance
        elif descriptor.factory:
            instance = descriptor.factory()
        else:
            instance = self._create_instance(descriptor)

        # Store based on scope
        if descriptor.scope == Scope.SINGLETON:
            self._singletons[descriptor.service_type] = instance

        elif descriptor.scope == Scope.SCOPED:
            scope_instances = _scope_context.get()
            if scope_instances is not None:
                scope_instances[descriptor.service_type] = instance

        elif descriptor.scope == Scope.THREAD:
            if not hasattr(self._thread_local, 'instances'):
                self._thread_local.instances = {}
            self._thread_local.instances[descriptor.service_type] = instance

        return instance

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create a new instance with dependencies."""
        impl = descriptor.implementation_type or descriptor.service_type

        # Resolve dependencies
        deps = {}
        for dep_type in descriptor.dependencies:
            deps[dep_type.__name__.lower()] = self.resolve(dep_type)

        # Get constructor parameters
        try:
            sig = inspect.signature(impl.__init__)
            kwargs = {}

            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue

                if param.annotation != inspect.Parameter.empty:
                    try:
                        kwargs[param_name] = self.resolve(param.annotation)
                    except KeyError:
                        if param.default != inspect.Parameter.empty:
                            kwargs[param_name] = param.default

            return impl(**kwargs)
        except Exception:
            # Fallback: try creating without arguments
            return impl()

    def _get_dependencies(self, impl: Type) -> List[Type]:
        """Get constructor dependencies."""
        deps = []

        try:
            hints = get_type_hints(impl.__init__)

            for name, hint in hints.items():
                if name == 'return':
                    continue
                if isinstance(hint, type):
                    deps.append(hint)
        except Exception:
            pass

        return deps

    # ========================================================================
    # SCOPE
    # ========================================================================

    def create_scope(self) -> ScopeContext:
        """Create a new scope context."""
        return ScopeContext(self)

    # ========================================================================
    # ASYNC
    # ========================================================================

    async def resolve_async(self, service_type: Type[T]) -> T:
        """Resolve asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.resolve(service_type))

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def is_registered(self, service_type: Type) -> bool:
        """Check if service is registered."""
        return service_type in self._descriptors

    def clear(self) -> None:
        """Clear all registrations."""
        with self._lock:
            self._descriptors.clear()
            self._named.clear()
            self._singletons.clear()

    def get_status(self) -> Dict[str, Any]:
        """Get container status."""
        with self._lock:
            return {
                'registered': len(self._descriptors),
                'singletons': len(self._singletons),
                'named': len(self._named),
                'services': [str(t) for t in self._descriptors.keys()]
            }


# ============================================================================
# DECORATORS
# ============================================================================

def injectable(
    scope: Scope = Scope.SINGLETON,
    name: Optional[str] = None
):
    """
    Mark class as injectable.

    Usage:
        @injectable(scope=Scope.SINGLETON)
        class MyService:
            ...
    """
    def decorator(cls: Type[T]) -> Type[T]:
        # Store metadata on class
        cls.__di_scope__ = scope
        cls.__di_name__ = name

        # Auto-register with global container
        container.register(cls, cls, scope=scope, name=name)

        return cls

    return decorator


def inject(service_type: Type[T]) -> T:
    """
    Inject dependency.

    Usage:
        class MyClass:
            def __init__(self):
                self.service = inject(MyService)
    """
    return container.resolve(service_type)


# ============================================================================
# CONVENIENCE
# ============================================================================

container = Container()


def register(
    service_type: Type[T],
    implementation: Optional[Type[T]] = None,
    **kwargs
) -> Container:
    """Register service."""
    return container.register(service_type, implementation, **kwargs)


def resolve(service_type: Type[T]) -> T:
    """Resolve service."""
    return container.resolve(service_type)
