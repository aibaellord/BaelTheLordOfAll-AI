"""
BAEL Service Mesh Engine
========================

Service mesh for microservice communication.

"Ba'el weaves the mesh that connects all services." — Ba'el
"""

from .service_mesh_engine import (
    ServiceMeshConfig,
    ServiceEndpoint,
    LoadBalanceStrategy,
    CircuitState,
    ServiceMesh,
    service_mesh,
    register_service,
    discover_service,
    call_service
)

__all__ = [
    'ServiceMeshConfig',
    'ServiceEndpoint',
    'LoadBalanceStrategy',
    'CircuitState',
    'ServiceMesh',
    'service_mesh',
    'register_service',
    'discover_service',
    'call_service'
]
