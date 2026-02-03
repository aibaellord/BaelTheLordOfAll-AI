#!/usr/bin/env python3
"""
BAEL - Dependency Injection Container
Advanced dependency injection and IoC container system.

This module provides comprehensive dependency injection capabilities
for building loosely coupled, testable, and maintainable systems.

Features:
- Service registration and resolution
- Lifetime management (singleton, transient, scoped)
- Constructor injection
- Property injection
- Factory functions
- Lazy loading
- Circular dependency detection
- Module organization
- Auto-wiring
- Decorators for registration
"""

import asyncio
import functools
import inspect
import logging
import threading
import weakref
from abc import ABC, abstractmethod
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Callable, Dict, ForwardRef, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union, get_type_hints)
from uuid import uuid4

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class Lifetime(Enum):
    """Service lifetime."""
    TRANSIENT = "transient"      # New instance every time
    SINGLETON = "singleton"      # Single instance
    SCOPED = "scoped"            # Single instance per scope


class RegistrationType(Enum):
    """Registration type."""
    TYPE = "type"
    INSTANCE = "instance"
    FACTORY = "factory"


class InjectionType(Enum):
    """Injection type."""
    CONSTRUCTOR = "constructor"
    PROPERTY = "property"
    METHOD = "method"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ServiceDescriptor:
    """Describes a registered service."""
    service_type: Type
    implementation: Union[Type, Callable, Any]
    lifetime: Lifetime
    registration_type: RegistrationType
    name: Optional[str] = None
    factory_args: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[Type] = field(default_factory=list)
    lazy: bool = False


@dataclass
class Scope:
    """Represents a service scope."""
    id: str = field(default_factory=lambda: str(uuid4()))
    parent: Optional['Scope'] = None
    instances: Dict[Type, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ResolutionContext:
    """Context for service resolution."""
    scope: Optional[Scope] = None
    resolution_stack: List[Type] = field(default_factory=list)
    resolved_instances: Dict[Type, Any] = field(default_factory=dict)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class DependencyInjectionError(Exception):
    """Base exception for DI errors."""
    pass


class ServiceNotRegisteredError(DependencyInjectionError):
    """Service is not registered."""
    pass


class CircularDependencyError(DependencyInjectionError):
    """Circular dependency detected."""
    pass


class ResolutionError(DependencyInjectionError):
    """Failed to resolve service."""
    pass


class ScopeError(DependencyInjectionError):
    """Scope-related error."""
    pass


# =============================================================================
# LAZY PROXY
# =============================================================================

class LazyProxy(Generic[T]):
    """Lazy proxy for delayed service resolution."""

    def __init__(self, resolver: Callable[[], T]):
        self._resolver = resolver
        self._instance: Optional[T] = None
        self._resolved = False

    def _resolve(self) -> T:
        if not self._resolved:
            self._instance = self._resolver()
            self._resolved = True
        return self._instance

    def __getattr__(self, name: str) -> Any:
        instance = self._resolve()
        return getattr(instance, name)

    def __call__(self, *args, **kwargs) -> Any:
        instance = self._resolve()
        return instance(*args, **kwargs)


# =============================================================================
# DEPENDENCY RESOLVER
# =============================================================================

class DependencyResolver:
    """Resolves dependencies for a type."""

    @staticmethod
    def get_constructor_dependencies(service_type: Type) -> List[Tuple[str, Type]]:
        """Get constructor dependencies."""
        try:
            init_method = service_type.__init__
            hints = get_type_hints(init_method)
            sig = inspect.signature(init_method)

            dependencies = []
            for name, param in sig.parameters.items():
                if name == 'self':
                    continue

                param_type = hints.get(name)
                if param_type and not isinstance(param_type, (str, ForwardRef)):
                    dependencies.append((name, param_type))

            return dependencies
        except Exception:
            return []

    @staticmethod
    def get_property_dependencies(service_type: Type) -> List[Tuple[str, Type]]:
        """Get property dependencies (marked with Inject annotation)."""
        dependencies = []

        try:
            hints = get_type_hints(service_type)

            for name, type_hint in hints.items():
                if hasattr(service_type, f"_inject_{name}"):
                    dependencies.append((name, type_hint))
        except Exception:
            pass

        return dependencies


# =============================================================================
# SERVICE PROVIDER
# =============================================================================

class ServiceProvider:
    """Provides resolved services."""

    def __init__(self, container: 'Container'):
        self.container = container
        self._scope: Optional[Scope] = None

    def get_service(self, service_type: Type[T]) -> T:
        """Get a service."""
        return self.container.resolve(service_type, scope=self._scope)

    def get_services(self, service_type: Type[T]) -> List[T]:
        """Get all services of a type."""
        return self.container.resolve_all(service_type, scope=self._scope)

    def get_optional_service(self, service_type: Type[T]) -> Optional[T]:
        """Get a service or None if not registered."""
        try:
            return self.get_service(service_type)
        except ServiceNotRegisteredError:
            return None

    @contextmanager
    def create_scope(self):
        """Create a new scope."""
        scope = Scope(parent=self._scope)
        old_scope = self._scope
        self._scope = scope
        try:
            yield scope
        finally:
            self._scope = old_scope


# =============================================================================
# CONTAINER BUILDER
# =============================================================================

class ContainerBuilder:
    """Builds and configures the container."""

    def __init__(self):
        self.descriptors: List[ServiceDescriptor] = []
        self.modules: List['Module'] = []

    def register(
        self,
        service_type: Type,
        implementation: Type = None,
        lifetime: Lifetime = Lifetime.TRANSIENT,
        name: str = None
    ) -> 'ContainerBuilder':
        """Register a service type."""
        impl = implementation or service_type

        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=impl,
            lifetime=lifetime,
            registration_type=RegistrationType.TYPE,
            name=name
        )

        self.descriptors.append(descriptor)
        return self

    def register_instance(
        self,
        service_type: Type,
        instance: Any,
        name: str = None
    ) -> 'ContainerBuilder':
        """Register a singleton instance."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=instance,
            lifetime=Lifetime.SINGLETON,
            registration_type=RegistrationType.INSTANCE,
            name=name
        )

        self.descriptors.append(descriptor)
        return self

    def register_factory(
        self,
        service_type: Type,
        factory: Callable,
        lifetime: Lifetime = Lifetime.TRANSIENT,
        name: str = None,
        **kwargs
    ) -> 'ContainerBuilder':
        """Register a factory function."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=factory,
            lifetime=lifetime,
            registration_type=RegistrationType.FACTORY,
            name=name,
            factory_args=kwargs
        )

        self.descriptors.append(descriptor)
        return self

    def register_singleton(
        self,
        service_type: Type,
        implementation: Type = None,
        name: str = None
    ) -> 'ContainerBuilder':
        """Register as singleton."""
        return self.register(service_type, implementation, Lifetime.SINGLETON, name)

    def register_scoped(
        self,
        service_type: Type,
        implementation: Type = None,
        name: str = None
    ) -> 'ContainerBuilder':
        """Register as scoped."""
        return self.register(service_type, implementation, Lifetime.SCOPED, name)

    def register_transient(
        self,
        service_type: Type,
        implementation: Type = None,
        name: str = None
    ) -> 'ContainerBuilder':
        """Register as transient."""
        return self.register(service_type, implementation, Lifetime.TRANSIENT, name)

    def register_lazy(
        self,
        service_type: Type,
        implementation: Type = None,
        lifetime: Lifetime = Lifetime.SINGLETON,
        name: str = None
    ) -> 'ContainerBuilder':
        """Register as lazy-loaded."""
        impl = implementation or service_type

        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=impl,
            lifetime=lifetime,
            registration_type=RegistrationType.TYPE,
            name=name,
            lazy=True
        )

        self.descriptors.append(descriptor)
        return self

    def add_module(self, module: 'Module') -> 'ContainerBuilder':
        """Add a module to the builder."""
        self.modules.append(module)
        return self

    def build(self) -> 'Container':
        """Build the container."""
        container = Container()

        # Register from modules
        for module in self.modules:
            module.configure(self)

        # Register all descriptors
        for descriptor in self.descriptors:
            container._register_descriptor(descriptor)

        return container


# =============================================================================
# CONTAINER
# =============================================================================

class Container:
    """
    Main dependency injection container.

    Manages service registration, resolution, and lifetimes.
    """

    def __init__(self):
        self._descriptors: Dict[Type, List[ServiceDescriptor]] = defaultdict(list)
        self._named_descriptors: Dict[str, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        self._named_singletons: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def _register_descriptor(self, descriptor: ServiceDescriptor) -> None:
        """Register a service descriptor."""
        self._descriptors[descriptor.service_type].append(descriptor)

        if descriptor.name:
            self._named_descriptors[descriptor.name] = descriptor

    def is_registered(self, service_type: Type, name: str = None) -> bool:
        """Check if a service is registered."""
        if name:
            return name in self._named_descriptors
        return service_type in self._descriptors

    def resolve(
        self,
        service_type: Type[T],
        name: str = None,
        scope: Scope = None
    ) -> T:
        """Resolve a service."""
        context = ResolutionContext(scope=scope)
        return self._resolve_internal(service_type, name, context)

    def resolve_all(
        self,
        service_type: Type[T],
        scope: Scope = None
    ) -> List[T]:
        """Resolve all registered implementations."""
        context = ResolutionContext(scope=scope)
        instances = []

        for descriptor in self._descriptors.get(service_type, []):
            instance = self._resolve_descriptor(descriptor, context)
            instances.append(instance)

        return instances

    def _resolve_internal(
        self,
        service_type: Type[T],
        name: str,
        context: ResolutionContext
    ) -> T:
        """Internal resolution logic."""
        # Get descriptor
        descriptor = self._get_descriptor(service_type, name)

        if not descriptor:
            raise ServiceNotRegisteredError(
                f"Service {service_type.__name__} is not registered"
            )

        # Check for circular dependency
        if service_type in context.resolution_stack:
            raise CircularDependencyError(
                f"Circular dependency detected: {' -> '.join(t.__name__ for t in context.resolution_stack)} -> {service_type.__name__}"
            )

        context.resolution_stack.append(service_type)

        try:
            return self._resolve_descriptor(descriptor, context)
        finally:
            context.resolution_stack.pop()

    def _get_descriptor(
        self,
        service_type: Type,
        name: str = None
    ) -> Optional[ServiceDescriptor]:
        """Get service descriptor."""
        if name:
            return self._named_descriptors.get(name)

        descriptors = self._descriptors.get(service_type, [])
        return descriptors[-1] if descriptors else None

    def _resolve_descriptor(
        self,
        descriptor: ServiceDescriptor,
        context: ResolutionContext
    ) -> Any:
        """Resolve a service from its descriptor."""
        # Check lifetime
        if descriptor.lifetime == Lifetime.SINGLETON:
            return self._resolve_singleton(descriptor, context)
        elif descriptor.lifetime == Lifetime.SCOPED:
            return self._resolve_scoped(descriptor, context)
        else:
            return self._create_instance(descriptor, context)

    def _resolve_singleton(
        self,
        descriptor: ServiceDescriptor,
        context: ResolutionContext
    ) -> Any:
        """Resolve a singleton."""
        key = descriptor.name or descriptor.service_type

        # For instance registrations, return directly
        if descriptor.registration_type == RegistrationType.INSTANCE:
            return descriptor.implementation

        cache = self._named_singletons if descriptor.name else self._singletons

        with self._lock:
            if key in cache:
                return cache[key]

            if descriptor.lazy:
                instance = LazyProxy(lambda: self._create_instance(descriptor, context))
            else:
                instance = self._create_instance(descriptor, context)

            cache[key] = instance
            return instance

    def _resolve_scoped(
        self,
        descriptor: ServiceDescriptor,
        context: ResolutionContext
    ) -> Any:
        """Resolve a scoped service."""
        if not context.scope:
            raise ScopeError(
                f"Cannot resolve scoped service {descriptor.service_type.__name__} without a scope"
            )

        key = descriptor.name or descriptor.service_type
        scope = context.scope

        if key in scope.instances:
            return scope.instances[key]

        instance = self._create_instance(descriptor, context)
        scope.instances[key] = instance

        return instance

    def _create_instance(
        self,
        descriptor: ServiceDescriptor,
        context: ResolutionContext
    ) -> Any:
        """Create a new instance."""
        if descriptor.registration_type == RegistrationType.INSTANCE:
            return descriptor.implementation

        elif descriptor.registration_type == RegistrationType.FACTORY:
            factory = descriptor.implementation

            # Resolve factory dependencies
            sig = inspect.signature(factory)
            kwargs = dict(descriptor.factory_args)

            for name, param in sig.parameters.items():
                if name in kwargs:
                    continue

                hints = get_type_hints(factory)
                if name in hints:
                    param_type = hints[name]
                    if self.is_registered(param_type):
                        kwargs[name] = self._resolve_internal(param_type, None, context)

            return factory(**kwargs)

        else:  # TYPE registration
            impl_type = descriptor.implementation

            # Resolve constructor dependencies
            dependencies = DependencyResolver.get_constructor_dependencies(impl_type)
            kwargs = {}

            for name, dep_type in dependencies:
                if self.is_registered(dep_type):
                    kwargs[name] = self._resolve_internal(dep_type, None, context)

            instance = impl_type(**kwargs)

            # Property injection
            property_deps = DependencyResolver.get_property_dependencies(impl_type)
            for name, dep_type in property_deps:
                if self.is_registered(dep_type):
                    setattr(instance, name, self._resolve_internal(dep_type, None, context))

            return instance

    @contextmanager
    def create_scope(self):
        """Create a new scope."""
        scope = Scope()
        try:
            yield scope
        finally:
            # Cleanup scoped instances
            scope.instances.clear()

    def get_provider(self) -> ServiceProvider:
        """Get a service provider."""
        return ServiceProvider(self)

    def get_registered_types(self) -> List[Type]:
        """Get all registered types."""
        return list(self._descriptors.keys())

    def get_statistics(self) -> Dict[str, Any]:
        """Get container statistics."""
        return {
            "registered_types": len(self._descriptors),
            "total_descriptors": sum(len(d) for d in self._descriptors.values()),
            "singletons_created": len(self._singletons),
            "named_services": len(self._named_descriptors)
        }


# =============================================================================
# MODULE
# =============================================================================

class Module(ABC):
    """Abstract module for organizing registrations."""

    @abstractmethod
    def configure(self, builder: ContainerBuilder) -> None:
        """Configure the module."""
        pass


# =============================================================================
# DECORATORS
# =============================================================================

_registration_metadata: Dict[Type, Dict[str, Any]] = {}


def injectable(
    lifetime: Lifetime = Lifetime.TRANSIENT,
    as_type: Type = None,
    name: str = None
):
    """Mark a class as injectable."""
    def decorator(cls):
        _registration_metadata[cls] = {
            "lifetime": lifetime,
            "as_type": as_type or cls,
            "name": name
        }
        return cls
    return decorator


def inject(name: str = None):
    """Mark a property for injection."""
    def decorator(func):
        func._inject_name = name
        return func
    return decorator


def auto_register(builder: ContainerBuilder, *classes: Type) -> ContainerBuilder:
    """Auto-register classes with injectable decorator."""
    for cls in classes:
        metadata = _registration_metadata.get(cls)
        if metadata:
            builder.register(
                metadata["as_type"],
                cls,
                metadata["lifetime"],
                metadata["name"]
            )
        else:
            builder.register(cls)
    return builder


# =============================================================================
# EXAMPLE SERVICES
# =============================================================================

class ILogger(ABC):
    """Logger interface."""
    @abstractmethod
    def log(self, message: str) -> None:
        pass


class IDatabase(ABC):
    """Database interface."""
    @abstractmethod
    def query(self, sql: str) -> List[Any]:
        pass


class ICache(ABC):
    """Cache interface."""
    @abstractmethod
    def get(self, key: str) -> Any:
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        pass


@injectable(lifetime=Lifetime.SINGLETON)
class ConsoleLogger(ILogger):
    """Console logger implementation."""
    def log(self, message: str) -> None:
        print(f"[LOG] {message}")


@injectable(lifetime=Lifetime.SCOPED)
class InMemoryDatabase(IDatabase):
    """In-memory database implementation."""
    def __init__(self):
        self.data = {}

    def query(self, sql: str) -> List[Any]:
        return [f"Result for: {sql}"]


@injectable(lifetime=Lifetime.SINGLETON)
class MemoryCache(ICache):
    """Memory cache implementation."""
    def __init__(self):
        self.cache = {}

    def get(self, key: str) -> Any:
        return self.cache.get(key)

    def set(self, key: str, value: Any) -> None:
        self.cache[key] = value


class UserService:
    """Example service with dependencies."""

    def __init__(self, logger: ILogger, database: IDatabase, cache: ICache):
        self.logger = logger
        self.database = database
        self.cache = cache

    def get_user(self, user_id: str) -> Dict[str, Any]:
        self.logger.log(f"Getting user {user_id}")

        cached = self.cache.get(f"user:{user_id}")
        if cached:
            return cached

        results = self.database.query(f"SELECT * FROM users WHERE id = {user_id}")

        user = {"id": user_id, "data": results}
        self.cache.set(f"user:{user_id}", user)

        return user


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Dependency Injection Container."""
    print("=" * 70)
    print("BAEL - DEPENDENCY INJECTION CONTAINER DEMO")
    print("IoC Container System")
    print("=" * 70)
    print()

    # 1. Basic Registration
    print("1. BASIC REGISTRATION:")
    print("-" * 40)

    builder = ContainerBuilder()

    builder.register_singleton(ILogger, ConsoleLogger)
    builder.register_scoped(IDatabase, InMemoryDatabase)
    builder.register_singleton(ICache, MemoryCache)
    builder.register_transient(UserService)

    container = builder.build()

    print("   Registered services:")
    for service_type in container.get_registered_types():
        print(f"   - {service_type.__name__}")
    print()

    # 2. Service Resolution
    print("2. SERVICE RESOLUTION:")
    print("-" * 40)

    logger = container.resolve(ILogger)
    logger.log("Hello from resolved logger!")

    cache = container.resolve(ICache)
    cache.set("test", "value")
    print(f"   Cache get: {cache.get('test')}")
    print()

    # 3. Scoped Services
    print("3. SCOPED SERVICES:")
    print("-" * 40)

    with container.create_scope() as scope:
        db1 = container.resolve(IDatabase, scope=scope)
        db2 = container.resolve(IDatabase, scope=scope)
        print(f"   Same scope - same instance: {db1 is db2}")

    with container.create_scope() as scope2:
        db3 = container.resolve(IDatabase, scope=scope2)
        print(f"   Different scope - different instance: {db1 is not db3}")
    print()

    # 4. Constructor Injection
    print("4. CONSTRUCTOR INJECTION:")
    print("-" * 40)

    with container.create_scope() as scope:
        user_service = container.resolve(UserService, scope=scope)
        user = user_service.get_user("123")
        print(f"   User retrieved: {user}")
    print()

    # 5. Factory Registration
    print("5. FACTORY REGISTRATION:")
    print("-" * 40)

    builder2 = ContainerBuilder()

    def create_connection(host: str = "localhost", port: int = 5432):
        return {"host": host, "port": port, "connected": True}

    builder2.register_factory(
        dict,
        create_connection,
        Lifetime.SINGLETON,
        name="db_connection",
        host="db.example.com",
        port=3306
    )

    container2 = builder2.build()
    connection = container2.resolve(dict, name="db_connection")
    print(f"   Connection: {connection}")
    print()

    # 6. Instance Registration
    print("6. INSTANCE REGISTRATION:")
    print("-" * 40)

    builder3 = ContainerBuilder()

    config = {"debug": True, "version": "1.0.0"}
    builder3.register_instance(dict, config, name="config")

    container3 = builder3.build()
    resolved_config = container3.resolve(dict, name="config")
    print(f"   Config: {resolved_config}")
    print(f"   Same instance: {config is resolved_config}")
    print()

    # 7. Module Pattern
    print("7. MODULE PATTERN:")
    print("-" * 40)

    class LoggingModule(Module):
        def configure(self, builder: ContainerBuilder) -> None:
            builder.register_singleton(ILogger, ConsoleLogger)

    class DataModule(Module):
        def configure(self, builder: ContainerBuilder) -> None:
            builder.register_scoped(IDatabase, InMemoryDatabase)
            builder.register_singleton(ICache, MemoryCache)

    builder4 = ContainerBuilder()
    builder4.add_module(LoggingModule())
    builder4.add_module(DataModule())

    container4 = builder4.build()
    print(f"   Registered via modules: {len(container4.get_registered_types())} types")
    print()

    # 8. Service Provider
    print("8. SERVICE PROVIDER:")
    print("-" * 40)

    provider = container.get_provider()

    logger = provider.get_service(ILogger)
    logger.log("From service provider!")

    optional = provider.get_optional_service(UserService)
    print(f"   Optional service exists: {optional is not None}")
    print()

    # 9. Circular Dependency Detection
    print("9. CIRCULAR DEPENDENCY DETECTION:")
    print("-" * 40)

    class ServiceA:
        def __init__(self, b: 'ServiceB'):
            self.b = b

    class ServiceB:
        def __init__(self, a: ServiceA):
            self.a = a

    builder5 = ContainerBuilder()
    builder5.register_transient(ServiceA)
    builder5.register_transient(ServiceB)
    container5 = builder5.build()

    try:
        container5.resolve(ServiceA)
        print("   No circular dependency detected (shouldn't reach here)")
    except CircularDependencyError as e:
        print(f"   Caught: {type(e).__name__}")
        print(f"   Message: {str(e)[:60]}...")
    print()

    # 10. Statistics
    print("10. CONTAINER STATISTICS:")
    print("-" * 40)

    stats = container.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Dependency Injection Container Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
