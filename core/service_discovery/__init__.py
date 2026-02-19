"""
BAEL Service Discovery Engine
==============================

Microservices infrastructure:
- Service registry
- Health checks
- Load balancing
- Service mesh
- DNS resolution

"All services bow to Ba'el's orchestration." — Ba'el
"""

from .service_registry import (
    # Enums
    ServiceStatus,
    HealthCheckType,
    LoadBalancerAlgorithm,
    RegistrationMode,

    # Data structures
    ServiceInstance,
    ServiceDefinition,
    HealthCheck,
    HealthCheckResult,
    LoadBalancerConfig,
    ServiceDiscoveryConfig,

    # Classes
    ServiceDiscoveryEngine,
    ServiceRegistry,
    HealthChecker,
    LoadBalancer,
    ServiceResolver,

    # Instance
    service_discovery,
)

__all__ = [
    # Enums
    'ServiceStatus',
    'HealthCheckType',
    'LoadBalancerAlgorithm',
    'RegistrationMode',

    # Data structures
    'ServiceInstance',
    'ServiceDefinition',
    'HealthCheck',
    'HealthCheckResult',
    'LoadBalancerConfig',
    'ServiceDiscoveryConfig',

    # Classes
    'ServiceDiscoveryEngine',
    'ServiceRegistry',
    'HealthChecker',
    'LoadBalancer',
    'ServiceResolver',

    # Instance
    'service_discovery',
]
