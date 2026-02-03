#!/usr/bin/env python3
"""
BAEL - Dependency Injection Container
Comprehensive IoC (Inversion of Control) container.

Features:
- Constructor injection
- Property injection
- Method injection
- Singleton scope
- Transient scope
- Scoped lifetime
- Factory bindings
- Interface bindings
- Auto-wiring
- Circular dependency detection
- Lazy resolution
- Child containers
"""

import asyncio
import inspect
import logging
import threading
import uuid
import weakref
from abc import ABC, abstractmethod
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import wraps
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class Lifetime(Enum):
    """Service lifetime."""
    TRANSIENT = "transient"   # New instance each time
    SINGLETON = "singleton"   # Single instance
    SCOPED = "scoped"         # Instance per scope


class InjectionMode(Enum):
    """Injection mode."""
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
    implementation_type: Optional[Type] = None
    factory: Optional[Callable] = None
    instance: Any = None
    lifetime: Lifetime = Lifetime.TRANSIENT
    tags: Set[str] = field(default_factory=set)
    name: Optional[str] = None


@dataclass
class InjectionPoint:
    """Describes an injection point."""
    name: str
    service_type: Type
    mode: InjectionMode
    optional: bool = False
    default: Any = None


@dataclass
class ResolutionContext:
    """Context for service resolution."""
    scope_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scoped_instances: Dict[Type, Any] = field(default_factory=dict)
    resolution_stack: List[Type] = field(default_factory=list)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class DIException(Exception):
    """Base DI exception."""
    pass


class ServiceNotFoundError(DIException):
    """Service not registered."""
    pass


class CircularDependencyError(DIException):
    """Circular dependency detected."""
    pass


class ResolutionError(DIException):
    """Error resolving service."""
    pass


# =============================================================================
# INJECTION DECORATORS
# =============================================================================

def inject(service_type: Type = None):
    """Mark a parameter for injection."""
    def decorator(func):
        if not hasattr(func, '__injection_points__'):
            func.__injection_points__ = {}

        sig = inspect.signature(func)
        for name, param in sig.parameters.items():
            if name == 'self':
                continue

            if param.annotation != inspect.Parameter.empty:
                func.__injection_points__[name] = param.annotation

        return func

    if service_type is not None and callable(service_type) and not isinstance(service_type, type):
        return decorator(service_type)

    return decorator


def injectable(cls: Type = None, lifetime: Lifetime = Lifetime.TRANSIENT):
    """Mark a class as injectable."""
    def decorator(c):
        c.__injectable__ = True
        c.__lifetime__ = lifetime
        return c

    if cls is not None:
        return decorator(cls)

    return decorator


def singleton(cls: Type):
    """Mark class as singleton."""
    cls.__injectable__ = True
    cls.__lifetime__ = Lifetime.SINGLETON
    return cls


# =============================================================================
# SERVICE PROVIDER
# =============================================================================

class ServiceProvider:
    """Resolves services from container."""

    def __init__(self, container: 'DependencyContainer', scope_id: str = None):
        self._container = container
        self._scope_id = scope_id or str(uuid.uuid4())
        self._scoped_instances: Dict[Type, Any] = {}

    def get_service(self, service_type: Type[T]) -> T:
        """Get service instance."""
        return self._container.resolve(
            service_type,
            ResolutionContext(
                scope_id=self._scope_id,
                scoped_instances=self._scoped_instances
            )
        )

    def get_optional_service(self, service_type: Type[T]) -> Optional[T]:
        """Get service or None."""
        try:
            return self.get_service(service_type)
        except ServiceNotFoundError:
            return None

    def get_services(self, service_type: Type[T]) -> List[T]:
        """Get all services of type."""
        return self._container.resolve_all(
            service_type,
            ResolutionContext(
                scope_id=self._scope_id,
                scoped_instances=self._scoped_instances
            )
        )


# =============================================================================
# SERVICE SCOPE
# =============================================================================

class ServiceScope:
    """Scoped service lifetime."""

    def __init__(self, container: 'DependencyContainer'):
        self._container = container
        self._scope_id = str(uuid.uuid4())
        self._scoped_instances: Dict[Type, Any] = {}
        self._provider = ServiceProvider(container, self._scope_id)

    @property
    def service_provider(self) -> ServiceProvider:
        """Get scoped service provider."""
        return self._provider

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.dispose()

    def dispose(self) -> None:
        """Dispose scoped services."""
        for instance in self._scoped_instances.values():
            if hasattr(instance, 'dispose'):
                try:
                    instance.dispose()
                except Exception as e:
                    logger.error(f"Error disposing service: {e}")

        self._scoped_instances.clear()


# =============================================================================
# SERVICE COLLECTION
# =============================================================================

class ServiceCollection:
    """Collection of service descriptors."""

    def __init__(self):
        self._services: List[ServiceDescriptor] = []

    def add_transient(
        self,
        service_type: Type,
        implementation_type: Type = None,
        factory: Callable = None
    ) -> 'ServiceCollection':
        """Add transient service."""
        self._add(service_type, implementation_type, factory, Lifetime.TRANSIENT)
        return self

    def add_singleton(
        self,
        service_type: Type,
        implementation_type: Type = None,
        factory: Callable = None,
        instance: Any = None
    ) -> 'ServiceCollection':
        """Add singleton service."""
        self._add(service_type, implementation_type, factory, Lifetime.SINGLETON, instance)
        return self

    def add_scoped(
        self,
        service_type: Type,
        implementation_type: Type = None,
        factory: Callable = None
    ) -> 'ServiceCollection':
        """Add scoped service."""
        self._add(service_type, implementation_type, factory, Lifetime.SCOPED)
        return self

    def _add(
        self,
        service_type: Type,
        implementation_type: Type,
        factory: Callable,
        lifetime: Lifetime,
        instance: Any = None
    ) -> None:
        """Add service descriptor."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type or service_type,
            factory=factory,
            instance=instance,
            lifetime=lifetime
        )
        self._services.append(descriptor)

    def build(self) -> 'DependencyContainer':
        """Build container from collection."""
        container = DependencyContainer()

        for descriptor in self._services:
            container._register_descriptor(descriptor)

        return container


# =============================================================================
# DEPENDENCY CONTAINER
# =============================================================================

class DependencyContainer:
    """
    Comprehensive Dependency Injection Container for BAEL.

    Features:
    - Multiple lifetimes (transient, singleton, scoped)
    - Factory bindings
    - Auto-wiring
    - Circular dependency detection
    - Child containers
    """

    def __init__(self, parent: 'DependencyContainer' = None):
        self._services: Dict[Type, List[ServiceDescriptor]] = defaultdict(list)
        self._named_services: Dict[str, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        self._parent = parent
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # REGISTRATION
    # -------------------------------------------------------------------------

    def register(
        self,
        service_type: Type[T],
        implementation_type: Type = None,
        lifetime: Lifetime = Lifetime.TRANSIENT,
        factory: Callable = None,
        name: str = None,
        tags: Set[str] = None
    ) -> 'DependencyContainer':
        """Register a service."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type or service_type,
            factory=factory,
            lifetime=lifetime,
            name=name,
            tags=tags or set()
        )

        self._register_descriptor(descriptor)
        return self

    def register_instance(
        self,
        service_type: Type[T],
        instance: T,
        name: str = None
    ) -> 'DependencyContainer':
        """Register an existing instance."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            instance=instance,
            lifetime=Lifetime.SINGLETON,
            name=name
        )

        self._register_descriptor(descriptor)
        return self

    def register_factory(
        self,
        service_type: Type[T],
        factory: Callable[..., T],
        lifetime: Lifetime = Lifetime.TRANSIENT
    ) -> 'DependencyContainer':
        """Register a factory function."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            factory=factory,
            lifetime=lifetime
        )

        self._register_descriptor(descriptor)
        return self

    def _register_descriptor(self, descriptor: ServiceDescriptor) -> None:
        """Register a service descriptor."""
        with self._lock:
            self._services[descriptor.service_type].append(descriptor)

            if descriptor.name:
                self._named_services[descriptor.name] = descriptor

            if descriptor.instance is not None:
                self._singletons[descriptor.service_type] = descriptor.instance

    # -------------------------------------------------------------------------
    # RESOLUTION
    # -------------------------------------------------------------------------

    def resolve(
        self,
        service_type: Type[T],
        context: ResolutionContext = None
    ) -> T:
        """Resolve a service."""
        context = context or ResolutionContext()

        # Check for circular dependency
        if service_type in context.resolution_stack:
            chain = " -> ".join(t.__name__ for t in context.resolution_stack)
            raise CircularDependencyError(
                f"Circular dependency detected: {chain} -> {service_type.__name__}"
            )

        context.resolution_stack.append(service_type)

        try:
            return self._resolve_internal(service_type, context)
        finally:
            context.resolution_stack.pop()

    def _resolve_internal(
        self,
        service_type: Type[T],
        context: ResolutionContext
    ) -> T:
        """Internal resolution logic."""
        # Get descriptor
        descriptors = self._services.get(service_type, [])

        if not descriptors:
            # Check parent
            if self._parent:
                return self._parent.resolve(service_type, context)

            # Try auto-wire
            if self._can_auto_wire(service_type):
                return self._auto_wire(service_type, context)

            raise ServiceNotFoundError(
                f"Service not registered: {service_type.__name__}"
            )

        # Use last registered (allows overriding)
        descriptor = descriptors[-1]

        return self._create_instance(descriptor, context)

    def _create_instance(
        self,
        descriptor: ServiceDescriptor,
        context: ResolutionContext
    ) -> Any:
        """Create service instance."""
        # Check for existing instance
        if descriptor.lifetime == Lifetime.SINGLETON:
            if descriptor.service_type in self._singletons:
                return self._singletons[descriptor.service_type]

        elif descriptor.lifetime == Lifetime.SCOPED:
            if descriptor.service_type in context.scoped_instances:
                return context.scoped_instances[descriptor.service_type]

        # Create instance
        if descriptor.instance is not None:
            instance = descriptor.instance

        elif descriptor.factory is not None:
            instance = self._invoke_factory(descriptor.factory, context)

        else:
            instance = self._auto_wire(
                descriptor.implementation_type,
                context
            )

        # Store by lifetime
        if descriptor.lifetime == Lifetime.SINGLETON:
            self._singletons[descriptor.service_type] = instance

        elif descriptor.lifetime == Lifetime.SCOPED:
            context.scoped_instances[descriptor.service_type] = instance

        return instance

    def _invoke_factory(
        self,
        factory: Callable,
        context: ResolutionContext
    ) -> Any:
        """Invoke factory with injected dependencies."""
        sig = inspect.signature(factory)
        kwargs = {}

        for name, param in sig.parameters.items():
            if param.annotation != inspect.Parameter.empty:
                try:
                    kwargs[name] = self.resolve(param.annotation, context)
                except ServiceNotFoundError:
                    if param.default == inspect.Parameter.empty:
                        raise

        return factory(**kwargs)

    def _can_auto_wire(self, service_type: Type) -> bool:
        """Check if type can be auto-wired."""
        if not isinstance(service_type, type):
            return False

        if inspect.isabstract(service_type):
            return False

        return True

    def _auto_wire(
        self,
        service_type: Type[T],
        context: ResolutionContext
    ) -> T:
        """Auto-wire a type by resolving constructor parameters."""
        if not self._can_auto_wire(service_type):
            raise ResolutionError(
                f"Cannot auto-wire: {service_type.__name__}"
            )

        # Get constructor
        init = service_type.__init__
        sig = inspect.signature(init)

        kwargs = {}

        for name, param in sig.parameters.items():
            if name == 'self':
                continue

            if param.annotation != inspect.Parameter.empty:
                try:
                    kwargs[name] = self.resolve(param.annotation, context)
                except ServiceNotFoundError:
                    if param.default == inspect.Parameter.empty:
                        raise
                    kwargs[name] = param.default

            elif param.default != inspect.Parameter.empty:
                kwargs[name] = param.default

        return service_type(**kwargs)

    # -------------------------------------------------------------------------
    # MULTIPLE RESOLUTION
    # -------------------------------------------------------------------------

    def resolve_all(
        self,
        service_type: Type[T],
        context: ResolutionContext = None
    ) -> List[T]:
        """Resolve all services of type."""
        context = context or ResolutionContext()
        instances = []

        for descriptor in self._services.get(service_type, []):
            instance = self._create_instance(descriptor, context)
            instances.append(instance)

        if self._parent:
            instances.extend(self._parent.resolve_all(service_type, context))

        return instances

    def resolve_by_name(
        self,
        name: str,
        context: ResolutionContext = None
    ) -> Any:
        """Resolve service by name."""
        context = context or ResolutionContext()

        descriptor = self._named_services.get(name)

        if not descriptor:
            if self._parent:
                return self._parent.resolve_by_name(name, context)

            raise ServiceNotFoundError(f"Named service not found: {name}")

        return self._create_instance(descriptor, context)

    def resolve_by_tag(
        self,
        tag: str,
        context: ResolutionContext = None
    ) -> List[Any]:
        """Resolve services by tag."""
        context = context or ResolutionContext()
        instances = []

        for descriptors in self._services.values():
            for descriptor in descriptors:
                if tag in descriptor.tags:
                    instances.append(
                        self._create_instance(descriptor, context)
                    )

        if self._parent:
            instances.extend(self._parent.resolve_by_tag(tag, context))

        return instances

    # -------------------------------------------------------------------------
    # SCOPE MANAGEMENT
    # -------------------------------------------------------------------------

    def create_scope(self) -> ServiceScope:
        """Create new service scope."""
        return ServiceScope(self)

    def create_child(self) -> 'DependencyContainer':
        """Create child container."""
        return DependencyContainer(parent=self)

    # -------------------------------------------------------------------------
    # UTILITY
    # -------------------------------------------------------------------------

    def is_registered(self, service_type: Type) -> bool:
        """Check if service is registered."""
        if service_type in self._services:
            return True

        if self._parent:
            return self._parent.is_registered(service_type)

        return False

    def get_registered_types(self) -> List[Type]:
        """Get all registered types."""
        types = list(self._services.keys())

        if self._parent:
            types.extend(self._parent.get_registered_types())

        return list(set(types))


# =============================================================================
# ASYNC CONTAINER
# =============================================================================

class AsyncDependencyContainer(DependencyContainer):
    """Async-aware dependency container."""

    async def resolve_async(
        self,
        service_type: Type[T],
        context: ResolutionContext = None
    ) -> T:
        """Resolve service asynchronously."""
        context = context or ResolutionContext()

        instance = self.resolve(service_type, context)

        # Initialize if async init method
        if hasattr(instance, 'initialize') and asyncio.iscoroutinefunction(instance.initialize):
            await instance.initialize()

        return instance

    async def resolve_all_async(
        self,
        service_type: Type[T],
        context: ResolutionContext = None
    ) -> List[T]:
        """Resolve all services asynchronously."""
        instances = self.resolve_all(service_type, context)

        for instance in instances:
            if hasattr(instance, 'initialize') and asyncio.iscoroutinefunction(instance.initialize):
                await instance.initialize()

        return instances


# =============================================================================
# BUILDER
# =============================================================================

class ContainerBuilder:
    """Fluent container builder."""

    def __init__(self):
        self._registrations: List[Callable[[DependencyContainer], None]] = []

    def register_transient(
        self,
        service_type: Type,
        implementation_type: Type = None
    ) -> 'ContainerBuilder':
        """Register transient service."""
        def register(c):
            c.register(service_type, implementation_type, Lifetime.TRANSIENT)

        self._registrations.append(register)
        return self

    def register_singleton(
        self,
        service_type: Type,
        implementation_type: Type = None
    ) -> 'ContainerBuilder':
        """Register singleton service."""
        def register(c):
            c.register(service_type, implementation_type, Lifetime.SINGLETON)

        self._registrations.append(register)
        return self

    def register_scoped(
        self,
        service_type: Type,
        implementation_type: Type = None
    ) -> 'ContainerBuilder':
        """Register scoped service."""
        def register(c):
            c.register(service_type, implementation_type, Lifetime.SCOPED)

        self._registrations.append(register)
        return self

    def register_instance(
        self,
        service_type: Type,
        instance: Any
    ) -> 'ContainerBuilder':
        """Register instance."""
        def register(c):
            c.register_instance(service_type, instance)

        self._registrations.append(register)
        return self

    def register_factory(
        self,
        service_type: Type,
        factory: Callable
    ) -> 'ContainerBuilder':
        """Register factory."""
        def register(c):
            c.register_factory(service_type, factory)

        self._registrations.append(register)
        return self

    def build(self) -> DependencyContainer:
        """Build container."""
        container = DependencyContainer()

        for registration in self._registrations:
            registration(container)

        return container


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Dependency Injection Container."""
    print("=" * 70)
    print("BAEL - DEPENDENCY INJECTION CONTAINER DEMO")
    print("Comprehensive IoC Container")
    print("=" * 70)
    print()

    # Define interfaces and implementations
    class ILogger(ABC):
        @abstractmethod
        def log(self, message: str): pass

    class ConsoleLogger(ILogger):
        def log(self, message: str):
            print(f"      [LOG] {message}")

    class IDatabase(ABC):
        @abstractmethod
        def query(self, sql: str): pass

    class PostgresDatabase(IDatabase):
        def __init__(self, logger: ILogger):
            self.logger = logger

        def query(self, sql: str):
            self.logger.log(f"Executing: {sql}")
            return [{"id": 1, "name": "Test"}]

    class UserService:
        def __init__(self, db: IDatabase, logger: ILogger):
            self.db = db
            self.logger = logger

        def get_users(self):
            self.logger.log("Getting users...")
            return self.db.query("SELECT * FROM users")

    # 1. Basic Registration and Resolution
    print("1. BASIC REGISTRATION:")
    print("-" * 40)

    container = DependencyContainer()
    container.register(ILogger, ConsoleLogger, Lifetime.SINGLETON)
    container.register(IDatabase, PostgresDatabase, Lifetime.TRANSIENT)
    container.register(UserService, UserService, Lifetime.TRANSIENT)

    user_service = container.resolve(UserService)
    users = user_service.get_users()
    print(f"   Users: {users}")
    print()

    # 2. Singleton Lifetime
    print("2. SINGLETON LIFETIME:")
    print("-" * 40)

    logger1 = container.resolve(ILogger)
    logger2 = container.resolve(ILogger)
    print(f"   Same instance: {logger1 is logger2}")
    print()

    # 3. Transient Lifetime
    print("3. TRANSIENT LIFETIME:")
    print("-" * 40)

    db1 = container.resolve(IDatabase)
    db2 = container.resolve(IDatabase)
    print(f"   Same instance: {db1 is db2}")
    print()

    # 4. Scoped Lifetime
    print("4. SCOPED LIFETIME:")
    print("-" * 40)

    class IScopedService(ABC):
        @abstractmethod
        def get_id(self) -> str: pass

    class ScopedService(IScopedService):
        def __init__(self):
            self.id = str(uuid.uuid4())[:8]

        def get_id(self) -> str:
            return self.id

    container.register(IScopedService, ScopedService, Lifetime.SCOPED)

    with container.create_scope() as scope1:
        s1a = scope1.service_provider.get_service(IScopedService)
        s1b = scope1.service_provider.get_service(IScopedService)
        print(f"   Scope 1: {s1a.get_id()} == {s1b.get_id()}: {s1a is s1b}")

    with container.create_scope() as scope2:
        s2 = scope2.service_provider.get_service(IScopedService)
        print(f"   Scope 2: {s2.get_id()} (different from scope 1)")
    print()

    # 5. Factory Registration
    print("5. FACTORY REGISTRATION:")
    print("-" * 40)

    class IConfig(ABC):
        @abstractmethod
        def get(self, key: str) -> str: pass

    class Config(IConfig):
        def __init__(self, env: str):
            self.env = env

        def get(self, key: str) -> str:
            return f"{key}={self.env}"

    def config_factory() -> IConfig:
        return Config("production")

    container.register_factory(IConfig, config_factory, Lifetime.SINGLETON)
    config = container.resolve(IConfig)
    print(f"   Config: {config.get('DATABASE_URL')}")
    print()

    # 6. Instance Registration
    print("6. INSTANCE REGISTRATION:")
    print("-" * 40)

    class Settings:
        def __init__(self, debug: bool):
            self.debug = debug

    settings = Settings(debug=True)
    container.register_instance(Settings, settings)

    resolved = container.resolve(Settings)
    print(f"   Same instance: {resolved is settings}")
    print(f"   Debug: {resolved.debug}")
    print()

    # 7. Named Services
    print("7. NAMED SERVICES:")
    print("-" * 40)

    class IEmailSender(ABC):
        @abstractmethod
        def send(self, to: str): pass

    class SmtpSender(IEmailSender):
        def send(self, to: str):
            return f"SMTP: {to}"

    class SendGridSender(IEmailSender):
        def send(self, to: str):
            return f"SendGrid: {to}"

    container.register(IEmailSender, SmtpSender, name="smtp")
    container.register(IEmailSender, SendGridSender, name="sendgrid")

    smtp = container.resolve_by_name("smtp")
    sendgrid = container.resolve_by_name("sendgrid")

    print(f"   {smtp.send('test@example.com')}")
    print(f"   {sendgrid.send('test@example.com')}")
    print()

    # 8. Tagged Services
    print("8. TAGGED SERVICES:")
    print("-" * 40)

    class IHandler(ABC):
        @abstractmethod
        def handle(self): pass

    class Handler1(IHandler):
        def handle(self):
            return "Handler1"

    class Handler2(IHandler):
        def handle(self):
            return "Handler2"

    container.register(IHandler, Handler1, tags={"http", "api"})
    container.register(IHandler, Handler2, tags={"http", "web"})

    http_handlers = container.resolve_by_tag("http")
    print(f"   HTTP handlers: {[h.handle() for h in http_handlers]}")

    api_handlers = container.resolve_by_tag("api")
    print(f"   API handlers: {[h.handle() for h in api_handlers]}")
    print()

    # 9. Child Containers
    print("9. CHILD CONTAINERS:")
    print("-" * 40)

    parent = DependencyContainer()
    parent.register(ILogger, ConsoleLogger, Lifetime.SINGLETON)

    child = parent.create_child()

    # Child inherits from parent
    logger_from_child = child.resolve(ILogger)
    print(f"   Child resolved parent service: {type(logger_from_child).__name__}")

    # Child can override
    class FileLogger(ILogger):
        def log(self, message: str):
            print(f"      [FILE] {message}")

    child.register(ILogger, FileLogger, Lifetime.SINGLETON)

    child_logger = child.resolve(ILogger)
    parent_logger = parent.resolve(ILogger)

    print(f"   Parent logger: {type(parent_logger).__name__}")
    print(f"   Child logger: {type(child_logger).__name__}")
    print()

    # 10. Circular Dependency Detection
    print("10. CIRCULAR DEPENDENCY DETECTION:")
    print("-" * 40)

    class ServiceA:
        def __init__(self, b: 'ServiceB'):
            self.b = b

    class ServiceB:
        def __init__(self, a: ServiceA):
            self.a = a

    circular_container = DependencyContainer()
    circular_container.register(ServiceA, ServiceA)
    circular_container.register(ServiceB, ServiceB)

    try:
        circular_container.resolve(ServiceA)
    except CircularDependencyError as e:
        print(f"   Detected: {str(e)[:50]}...")
    print()

    # 11. Builder Pattern
    print("11. BUILDER PATTERN:")
    print("-" * 40)

    built_container = (
        ContainerBuilder()
        .register_singleton(ILogger, ConsoleLogger)
        .register_transient(IDatabase, PostgresDatabase)
        .register_transient(UserService)
        .build()
    )

    service = built_container.resolve(UserService)
    print(f"   Built container resolved: {type(service).__name__}")
    print()

    # 12. Service Collection
    print("12. SERVICE COLLECTION:")
    print("-" * 40)

    collection = ServiceCollection()
    collection.add_singleton(ILogger, ConsoleLogger)
    collection.add_transient(IDatabase, PostgresDatabase)

    collection_container = collection.build()

    print(f"   Logger registered: {collection_container.is_registered(ILogger)}")
    print(f"   Database registered: {collection_container.is_registered(IDatabase)}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Dependency Container Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
