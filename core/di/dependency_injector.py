#!/usr/bin/env python3
"""
BAEL - Dependency Injection Container
Advanced dependency injection for AI agents.

Features:
- Constructor injection
- Property injection
- Interface binding
- Singleton/Transient/Scoped lifetimes
- Factory registration
- Lazy loading
- Circular dependency detection
- Auto-wiring
- Named bindings
- Decorators
"""

import asyncio
import functools
import inspect
import logging
import threading
import uuid
import weakref
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union, get_type_hints)

logger = logging.getLogger(__name__)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class Lifetime(Enum):
    """Service lifetimes."""
    TRANSIENT = "transient"    # New instance every time
    SINGLETON = "singleton"     # Single instance forever
    SCOPED = "scoped"          # Single instance per scope


class BindingType(Enum):
    """Binding types."""
    TYPE = "type"
    INSTANCE = "instance"
    FACTORY = "factory"
    LAZY = "lazy"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ServiceDescriptor:
    """Describes a service registration."""
    service_type: Type
    implementation_type: Optional[Type] = None
    instance: Optional[Any] = None
    factory: Optional[Callable] = None
    lifetime: Lifetime = Lifetime.TRANSIENT
    binding_type: BindingType = BindingType.TYPE
    name: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ResolutionContext:
    """Context for service resolution."""
    resolving: Set[Type] = field(default_factory=set)
    scope_id: Optional[str] = None
    parent_type: Optional[Type] = None


@dataclass
class DependencyInfo:
    """Information about a dependency."""
    name: str
    type_hint: Type
    default: Any = None
    required: bool = True
    is_optional: bool = False


@dataclass
class InjectionPoint:
    """An injection point in a class."""
    target: Type
    dependencies: List[DependencyInfo] = field(default_factory=list)


# =============================================================================
# SCOPE
# =============================================================================

class Scope:
    """Dependency injection scope."""

    def __init__(self, container: 'Container', parent: Optional['Scope'] = None):
        self.id = str(uuid.uuid4())
        self._container = container
        self._parent = parent
        self._instances: Dict[Type, Any] = {}
        self._lock = threading.RLock()

    def get_instance(self, service_type: Type) -> Optional[Any]:
        """Get scoped instance."""
        with self._lock:
            if service_type in self._instances:
                return self._instances[service_type]
            if self._parent:
                return self._parent.get_instance(service_type)
            return None

    def set_instance(self, service_type: Type, instance: Any) -> None:
        """Set scoped instance."""
        with self._lock:
            self._instances[service_type] = instance

    def __enter__(self) -> 'Scope':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._instances.clear()


# =============================================================================
# SERVICE COLLECTION
# =============================================================================

class ServiceCollection:
    """Collection of service descriptors."""

    def __init__(self):
        self._descriptors: Dict[Type, List[ServiceDescriptor]] = defaultdict(list)
        self._named: Dict[str, ServiceDescriptor] = {}

    def add(self, descriptor: ServiceDescriptor) -> None:
        """Add a service descriptor."""
        self._descriptors[descriptor.service_type].append(descriptor)
        if descriptor.name:
            self._named[descriptor.name] = descriptor

    def get(self, service_type: Type, name: Optional[str] = None) -> Optional[ServiceDescriptor]:
        """Get a service descriptor."""
        if name:
            return self._named.get(name)

        descriptors = self._descriptors.get(service_type)
        if descriptors:
            return descriptors[-1]  # Return last registered
        return None

    def get_all(self, service_type: Type) -> List[ServiceDescriptor]:
        """Get all descriptors for a type."""
        return self._descriptors.get(service_type, [])

    def contains(self, service_type: Type) -> bool:
        """Check if type is registered."""
        return service_type in self._descriptors

    def all_types(self) -> Set[Type]:
        """Get all registered types."""
        return set(self._descriptors.keys())


# =============================================================================
# CONTAINER BUILDER
# =============================================================================

class ContainerBuilder:
    """Builder for creating containers."""

    def __init__(self):
        self._services = ServiceCollection()

    def register(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        lifetime: Lifetime = Lifetime.TRANSIENT,
        name: Optional[str] = None
    ) -> 'ContainerBuilder':
        """Register a service by type."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation or service_type,
            lifetime=lifetime,
            binding_type=BindingType.TYPE,
            name=name
        )
        self._services.add(descriptor)
        return self

    def register_instance(
        self,
        service_type: Type[T],
        instance: T,
        name: Optional[str] = None
    ) -> 'ContainerBuilder':
        """Register a singleton instance."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            instance=instance,
            lifetime=Lifetime.SINGLETON,
            binding_type=BindingType.INSTANCE,
            name=name
        )
        self._services.add(descriptor)
        return self

    def register_factory(
        self,
        service_type: Type[T],
        factory: Callable[['Container'], T],
        lifetime: Lifetime = Lifetime.TRANSIENT,
        name: Optional[str] = None
    ) -> 'ContainerBuilder':
        """Register a factory function."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            factory=factory,
            lifetime=lifetime,
            binding_type=BindingType.FACTORY,
            name=name
        )
        self._services.add(descriptor)
        return self

    def register_lazy(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        name: Optional[str] = None
    ) -> 'ContainerBuilder':
        """Register a lazy-loaded service."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation or service_type,
            lifetime=Lifetime.SINGLETON,
            binding_type=BindingType.LAZY,
            name=name
        )
        self._services.add(descriptor)
        return self

    def register_singleton(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        name: Optional[str] = None
    ) -> 'ContainerBuilder':
        """Register a singleton service."""
        return self.register(service_type, implementation, Lifetime.SINGLETON, name)

    def register_scoped(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        name: Optional[str] = None
    ) -> 'ContainerBuilder':
        """Register a scoped service."""
        return self.register(service_type, implementation, Lifetime.SCOPED, name)

    def register_transient(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        name: Optional[str] = None
    ) -> 'ContainerBuilder':
        """Register a transient service."""
        return self.register(service_type, implementation, Lifetime.TRANSIENT, name)

    def build(self) -> 'Container':
        """Build the container."""
        return Container(self._services)


# =============================================================================
# LAZY PROXY
# =============================================================================

class LazyProxy(Generic[T]):
    """Lazy loading proxy for services."""

    def __init__(self, factory: Callable[[], T]):
        self._factory = factory
        self._instance: Optional[T] = None
        self._lock = threading.RLock()

    def _get_instance(self) -> T:
        """Get or create the instance."""
        with self._lock:
            if self._instance is None:
                self._instance = self._factory()
            return self._instance

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_instance(), name)

    def __call__(self, *args, **kwargs) -> Any:
        return self._get_instance()(*args, **kwargs)


# =============================================================================
# DEPENDENCY ANALYZER
# =============================================================================

class DependencyAnalyzer:
    """Analyze dependencies of a type."""

    def analyze(self, type_: Type) -> InjectionPoint:
        """Analyze constructor dependencies."""
        dependencies = []

        # Get init signature
        if hasattr(type_, '__init__'):
            sig = inspect.signature(type_.__init__)
            hints = get_type_hints(type_.__init__) if hasattr(type_.__init__, '__annotations__') else {}

            for name, param in sig.parameters.items():
                if name == 'self':
                    continue

                type_hint = hints.get(name, Any)

                # Handle Optional types
                is_optional = False
                origin = getattr(type_hint, '__origin__', None)
                if origin is Union:
                    args = getattr(type_hint, '__args__', ())
                    if type(None) in args:
                        is_optional = True
                        # Get the non-None type
                        type_hint = next((a for a in args if a is not type(None)), Any)

                # Determine if required
                has_default = param.default is not inspect.Parameter.empty
                required = not has_default and not is_optional

                dependencies.append(DependencyInfo(
                    name=name,
                    type_hint=type_hint,
                    default=param.default if has_default else None,
                    required=required,
                    is_optional=is_optional
                ))

        return InjectionPoint(target=type_, dependencies=dependencies)


# =============================================================================
# CONTAINER
# =============================================================================

class Container:
    """
    Dependency Injection Container for BAEL.

    Manages service registration and resolution.
    """

    def __init__(self, services: Optional[ServiceCollection] = None):
        self._services = services or ServiceCollection()
        self._singletons: Dict[Type, Any] = {}
        self._analyzer = DependencyAnalyzer()
        self._lock = threading.RLock()
        self._current_scope: Optional[Scope] = None

    # -------------------------------------------------------------------------
    # RESOLUTION
    # -------------------------------------------------------------------------

    def resolve(
        self,
        service_type: Type[T],
        name: Optional[str] = None,
        context: Optional[ResolutionContext] = None
    ) -> T:
        """Resolve a service."""
        context = context or ResolutionContext()

        # Check for circular dependency
        if service_type in context.resolving:
            raise CircularDependencyError(
                f"Circular dependency detected for {service_type.__name__}"
            )

        context.resolving.add(service_type)

        try:
            return self._resolve_internal(service_type, name, context)
        finally:
            context.resolving.discard(service_type)

    def _resolve_internal(
        self,
        service_type: Type[T],
        name: Optional[str],
        context: ResolutionContext
    ) -> T:
        """Internal resolution logic."""
        descriptor = self._services.get(service_type, name)

        if not descriptor:
            # Try auto-wiring if it's a concrete type
            if inspect.isclass(service_type) and not inspect.isabstract(service_type):
                return self._create_instance(service_type, context)
            raise ServiceNotFoundError(f"Service not found: {service_type.__name__}")

        # Check for existing instance
        if descriptor.binding_type == BindingType.INSTANCE:
            return descriptor.instance

        if descriptor.lifetime == Lifetime.SINGLETON:
            with self._lock:
                if service_type in self._singletons:
                    return self._singletons[service_type]

                instance = self._create_from_descriptor(descriptor, context)
                self._singletons[service_type] = instance
                return instance

        elif descriptor.lifetime == Lifetime.SCOPED:
            if self._current_scope:
                instance = self._current_scope.get_instance(service_type)
                if instance:
                    return instance

                instance = self._create_from_descriptor(descriptor, context)
                self._current_scope.set_instance(service_type, instance)
                return instance
            else:
                # No scope, treat as transient
                return self._create_from_descriptor(descriptor, context)

        else:  # TRANSIENT
            return self._create_from_descriptor(descriptor, context)

    def _create_from_descriptor(
        self,
        descriptor: ServiceDescriptor,
        context: ResolutionContext
    ) -> Any:
        """Create instance from descriptor."""
        if descriptor.binding_type == BindingType.FACTORY:
            return descriptor.factory(self)

        elif descriptor.binding_type == BindingType.LAZY:
            return LazyProxy(
                lambda: self._create_instance(descriptor.implementation_type, context)
            )

        else:
            return self._create_instance(descriptor.implementation_type, context)

    def _create_instance(self, type_: Type, context: ResolutionContext) -> Any:
        """Create a new instance with injected dependencies."""
        injection = self._analyzer.analyze(type_)

        kwargs = {}
        for dep in injection.dependencies:
            if self._services.contains(dep.type_hint):
                kwargs[dep.name] = self.resolve(dep.type_hint, context=context)
            elif dep.required:
                if dep.type_hint in (str, int, float, bool, list, dict):
                    # Primitive types - use default if available
                    if dep.default is not None:
                        kwargs[dep.name] = dep.default
                else:
                    # Try to resolve anyway
                    try:
                        kwargs[dep.name] = self.resolve(dep.type_hint, context=context)
                    except ServiceNotFoundError:
                        if dep.default is not None:
                            kwargs[dep.name] = dep.default
                        elif not dep.is_optional:
                            raise
            elif dep.default is not None:
                kwargs[dep.name] = dep.default

        return type_(**kwargs)

    # -------------------------------------------------------------------------
    # CONVENIENCE METHODS
    # -------------------------------------------------------------------------

    def get(self, service_type: Type[T], name: Optional[str] = None) -> T:
        """Get a service (alias for resolve)."""
        return self.resolve(service_type, name)

    def get_optional(self, service_type: Type[T], name: Optional[str] = None) -> Optional[T]:
        """Get a service or None if not found."""
        try:
            return self.resolve(service_type, name)
        except ServiceNotFoundError:
            return None

    def get_all(self, service_type: Type[T]) -> List[T]:
        """Get all registered implementations of a type."""
        descriptors = self._services.get_all(service_type)
        return [
            self._create_from_descriptor(d, ResolutionContext())
            for d in descriptors
        ]

    def is_registered(self, service_type: Type) -> bool:
        """Check if a type is registered."""
        return self._services.contains(service_type)

    # -------------------------------------------------------------------------
    # SCOPES
    # -------------------------------------------------------------------------

    def create_scope(self) -> Scope:
        """Create a new scope."""
        return Scope(self, self._current_scope)

    def use_scope(self, scope: Scope) -> None:
        """Use a scope for resolution."""
        self._current_scope = scope

    def end_scope(self) -> None:
        """End the current scope."""
        self._current_scope = None

    # -------------------------------------------------------------------------
    # REGISTRATION (for dynamic registration)
    # -------------------------------------------------------------------------

    def register(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        lifetime: Lifetime = Lifetime.TRANSIENT,
        name: Optional[str] = None
    ) -> None:
        """Register a service dynamically."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation or service_type,
            lifetime=lifetime,
            binding_type=BindingType.TYPE,
            name=name
        )
        self._services.add(descriptor)

    def register_instance(
        self,
        service_type: Type[T],
        instance: T,
        name: Optional[str] = None
    ) -> None:
        """Register an instance dynamically."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            instance=instance,
            lifetime=Lifetime.SINGLETON,
            binding_type=BindingType.INSTANCE,
            name=name
        )
        self._services.add(descriptor)

    def register_factory(
        self,
        service_type: Type[T],
        factory: Callable[['Container'], T],
        lifetime: Lifetime = Lifetime.TRANSIENT,
        name: Optional[str] = None
    ) -> None:
        """Register a factory dynamically."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            factory=factory,
            lifetime=lifetime,
            binding_type=BindingType.FACTORY,
            name=name
        )
        self._services.add(descriptor)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class DIException(Exception):
    """Base DI exception."""
    pass


class ServiceNotFoundError(DIException):
    """Service not found."""
    pass


class CircularDependencyError(DIException):
    """Circular dependency detected."""
    pass


# =============================================================================
# DECORATORS
# =============================================================================

def injectable(lifetime: Lifetime = Lifetime.TRANSIENT, name: Optional[str] = None):
    """Mark a class as injectable."""
    def decorator(cls: Type[T]) -> Type[T]:
        cls.__di_lifetime__ = lifetime
        cls.__di_name__ = name
        return cls
    return decorator


def inject(service_type: Optional[Type] = None, name: Optional[str] = None):
    """Mark a parameter for injection."""
    def decorator(func: Callable) -> Callable:
        if not hasattr(func, '__di_injections__'):
            func.__di_injections__ = {}
        func.__di_injections__[name] = service_type
        return func
    return decorator


def singleton(cls: Type[T]) -> Type[T]:
    """Mark a class as singleton."""
    cls.__di_lifetime__ = Lifetime.SINGLETON
    return cls


def scoped(cls: Type[T]) -> Type[T]:
    """Mark a class as scoped."""
    cls.__di_lifetime__ = Lifetime.SCOPED
    return cls


# =============================================================================
# DEPENDENCY INJECTOR
# =============================================================================

class DependencyInjector:
    """
    Dependency Injector for BAEL.

    High-level API for dependency injection.
    """

    def __init__(self):
        self._builder = ContainerBuilder()
        self._container: Optional[Container] = None

    # -------------------------------------------------------------------------
    # CONFIGURATION
    # -------------------------------------------------------------------------

    def configure(self, config_func: Callable[[ContainerBuilder], None]) -> 'DependencyInjector':
        """Configure services using a function."""
        config_func(self._builder)
        return self

    def register(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        lifetime: Lifetime = Lifetime.TRANSIENT,
        name: Optional[str] = None
    ) -> 'DependencyInjector':
        """Register a service."""
        self._builder.register(service_type, implementation, lifetime, name)
        return self

    def register_instance(
        self,
        service_type: Type[T],
        instance: T,
        name: Optional[str] = None
    ) -> 'DependencyInjector':
        """Register an instance."""
        self._builder.register_instance(service_type, instance, name)
        return self

    def register_factory(
        self,
        service_type: Type[T],
        factory: Callable[[Container], T],
        lifetime: Lifetime = Lifetime.TRANSIENT,
        name: Optional[str] = None
    ) -> 'DependencyInjector':
        """Register a factory."""
        self._builder.register_factory(service_type, factory, lifetime, name)
        return self

    def singleton(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None
    ) -> 'DependencyInjector':
        """Register a singleton."""
        self._builder.register_singleton(service_type, implementation)
        return self

    def transient(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None
    ) -> 'DependencyInjector':
        """Register a transient."""
        self._builder.register_transient(service_type, implementation)
        return self

    def scoped(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None
    ) -> 'DependencyInjector':
        """Register a scoped service."""
        self._builder.register_scoped(service_type, implementation)
        return self

    # -------------------------------------------------------------------------
    # BUILDING
    # -------------------------------------------------------------------------

    def build(self) -> Container:
        """Build and return the container."""
        self._container = self._builder.build()
        return self._container

    @property
    def container(self) -> Container:
        """Get the container (building if necessary)."""
        if self._container is None:
            self._container = self.build()
        return self._container

    # -------------------------------------------------------------------------
    # RESOLUTION
    # -------------------------------------------------------------------------

    def resolve(self, service_type: Type[T], name: Optional[str] = None) -> T:
        """Resolve a service."""
        return self.container.resolve(service_type, name)

    def get(self, service_type: Type[T], name: Optional[str] = None) -> T:
        """Get a service (alias for resolve)."""
        return self.resolve(service_type, name)

    def get_optional(self, service_type: Type[T]) -> Optional[T]:
        """Get a service or None."""
        return self.container.get_optional(service_type)

    # -------------------------------------------------------------------------
    # SCOPES
    # -------------------------------------------------------------------------

    def create_scope(self) -> Scope:
        """Create a new scope."""
        return self.container.create_scope()

    def scope(self) -> 'ScopeContext':
        """Create a scope context manager."""
        return ScopeContext(self.container)


class ScopeContext:
    """Context manager for scopes."""

    def __init__(self, container: Container):
        self._container = container
        self._scope: Optional[Scope] = None

    def __enter__(self) -> Scope:
        self._scope = self._container.create_scope()
        self._container.use_scope(self._scope)
        return self._scope

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._container.end_scope()


# =============================================================================
# AUTO-WIRE DECORATOR
# =============================================================================

def autowire(container_getter: Callable[[], Container]):
    """Decorator to auto-wire dependencies into a function."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            container = container_getter()

            # Get function signature
            sig = inspect.signature(func)
            hints = get_type_hints(func) if hasattr(func, '__annotations__') else {}

            # Inject missing parameters
            bound = sig.bind_partial(*args, **kwargs)

            for name, param in sig.parameters.items():
                if name not in bound.arguments:
                    type_hint = hints.get(name)
                    if type_hint and container.is_registered(type_hint):
                        kwargs[name] = container.resolve(type_hint)

            return func(*args, **kwargs)

        return wrapper
    return decorator


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Dependency Injector."""
    print("=" * 70)
    print("BAEL - DEPENDENCY INJECTION DEMO")
    print("Advanced Dependency Injection for AI Agents")
    print("=" * 70)
    print()

    # Sample services for demo
    class ILogger(ABC):
        @abstractmethod
        def log(self, message: str) -> None:
            pass

    class ConsoleLogger(ILogger):
        def log(self, message: str) -> None:
            print(f"   [LOG] {message}")

    class IDatabase(ABC):
        @abstractmethod
        def query(self, sql: str) -> str:
            pass

    class MemoryDatabase(IDatabase):
        def __init__(self, logger: ILogger):
            self.logger = logger
            self.logger.log("Database initialized")

        def query(self, sql: str) -> str:
            self.logger.log(f"Executing: {sql}")
            return f"Result for: {sql}"

    class UserService:
        def __init__(self, database: IDatabase, logger: ILogger):
            self.database = database
            self.logger = logger

        def get_user(self, user_id: int) -> str:
            self.logger.log(f"Getting user {user_id}")
            return self.database.query(f"SELECT * FROM users WHERE id = {user_id}")

    # 1. Basic Registration
    print("1. BASIC REGISTRATION:")
    print("-" * 40)

    di = DependencyInjector()
    di.singleton(ILogger, ConsoleLogger)
    di.transient(IDatabase, MemoryDatabase)
    di.transient(UserService)

    container = di.build()

    logger = container.resolve(ILogger)
    logger.log("Dependency Injection initialized")
    print()

    # 2. Singleton Behavior
    print("2. SINGLETON BEHAVIOR:")
    print("-" * 40)

    logger1 = container.resolve(ILogger)
    logger2 = container.resolve(ILogger)
    print(f"   Same instance: {logger1 is logger2}")
    print()

    # 3. Transient Behavior
    print("3. TRANSIENT BEHAVIOR:")
    print("-" * 40)

    db1 = container.resolve(IDatabase)
    db2 = container.resolve(IDatabase)
    print(f"   Same instance: {db1 is db2}")
    print()

    # 4. Constructor Injection
    print("4. CONSTRUCTOR INJECTION:")
    print("-" * 40)

    service = container.resolve(UserService)
    result = service.get_user(42)
    print(f"   Result: {result}")
    print()

    # 5. Factory Registration
    print("5. FACTORY REGISTRATION:")
    print("-" * 40)

    class Config:
        def __init__(self, value: str):
            self.value = value

    di2 = DependencyInjector()
    di2.register_factory(
        Config,
        lambda c: Config("production"),
        Lifetime.SINGLETON
    )

    config = di2.build().resolve(Config)
    print(f"   Config value: {config.value}")
    print()

    # 6. Named Bindings
    print("6. NAMED BINDINGS:")
    print("-" * 40)

    di3 = DependencyInjector()

    builder = ContainerBuilder()
    builder.register(ILogger, ConsoleLogger, name="console")

    container3 = builder.build()
    named_logger = container3.resolve(ILogger, name="console")
    named_logger.log("Named binding works!")
    print()

    # 7. Scoped Services
    print("7. SCOPED SERVICES:")
    print("-" * 40)

    class ScopedService:
        def __init__(self):
            self.id = str(uuid.uuid4())[:8]

    di4 = DependencyInjector()
    di4.scoped(ScopedService)
    container4 = di4.build()

    with di4.scope() as scope:
        s1 = container4.resolve(ScopedService)
        s2 = container4.resolve(ScopedService)
        print(f"   Scope 1 - Same instance: {s1 is s2}")
        print(f"   Instance ID: {s1.id}")

    with di4.scope() as scope:
        s3 = container4.resolve(ScopedService)
        print(f"   Scope 2 - Different from Scope 1: {s3 is not s1}")
        print(f"   Instance ID: {s3.id}")
    print()

    # 8. Lazy Loading
    print("8. LAZY LOADING:")
    print("-" * 40)

    class HeavyService:
        def __init__(self):
            print("   [HeavyService] Initializing...")
            self.data = "Heavy data loaded"

        def get_data(self) -> str:
            return self.data

    builder5 = ContainerBuilder()
    builder5.register_lazy(HeavyService)
    container5 = builder5.build()

    print("   Getting lazy proxy...")
    lazy_service = container5.resolve(HeavyService)
    print("   Proxy obtained (not initialized yet)")
    print(f"   Accessing data: {lazy_service.get_data()}")
    print()

    # 9. Auto-Wiring
    print("9. AUTO-WIRING:")
    print("-" * 40)

    class SimpleService:
        pass

    di6 = DependencyInjector()
    container6 = di6.build()

    # Auto-wire a concrete type without registration
    simple = container6.resolve(SimpleService)
    print(f"   Auto-wired: {simple.__class__.__name__}")
    print()

    # 10. Decorators
    print("10. DECORATORS:")
    print("-" * 40)

    @injectable(Lifetime.SINGLETON)
    class DecoratedService:
        def action(self) -> str:
            return "Decorated action"

    print(f"   Lifetime: {DecoratedService.__di_lifetime__.value}")
    print(f"   Action: {DecoratedService().action()}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Dependency Injector Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
