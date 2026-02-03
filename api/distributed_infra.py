"""
Distributed & Scaling Infrastructure for BAEL

Horizontal scaling support, load balancing, distributed tracing, service mesh
integration, and container orchestration.
"""

import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    IP_HASH = "ip_hash"
    RANDOM = "random"
    WEIGHTED = "weighted"


class HealthStatus(Enum):
    """Service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceInstance:
    """Service instance for scaling."""
    instance_id: str
    service_name: str
    host: str
    port: int
    weight: int = 1
    is_healthy: bool = True
    current_connections: int = 0
    max_connections: int = 1000
    created_at: datetime = field(default_factory=datetime.now)
    last_health_check: Optional[datetime] = None

    def get_load_percentage(self) -> float:
        """Get current load percentage."""
        return (self.current_connections / self.max_connections) * 100


class LoadBalancer:
    """Distributes requests across instances."""

    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self.instances: Dict[str, ServiceInstance] = {}
        self.current_index = 0
        self.request_count = 0

    def register_instance(self, instance: ServiceInstance) -> None:
        """Register service instance."""
        self.instances[instance.instance_id] = instance

    def deregister_instance(self, instance_id: str) -> None:
        """Deregister service instance."""
        if instance_id in self.instances:
            del self.instances[instance_id]

    def select_instance(self, client_id: Optional[str] = None) -> Optional[ServiceInstance]:
        """Select instance based on strategy."""
        healthy_instances = [i for i in self.instances.values() if i.is_healthy]

        if not healthy_instances:
            return None

        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            instance = healthy_instances[self.current_index % len(healthy_instances)]
            self.current_index += 1
            return instance

        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return min(healthy_instances, key=lambda i: i.current_connections)

        elif self.strategy == LoadBalancingStrategy.IP_HASH:
            if client_id:
                index = hash(client_id) % len(healthy_instances)
                return healthy_instances[index]
            return healthy_instances[0]

        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return random.choice(healthy_instances)

        elif self.strategy == LoadBalancingStrategy.WEIGHTED:
            total_weight = sum(i.weight for i in healthy_instances)
            choice = random.uniform(0, total_weight)
            current = 0
            for instance in healthy_instances:
                current += instance.weight
                if choice <= current:
                    return instance
            return healthy_instances[0]

        return healthy_instances[0]

    def route_request(self, client_id: Optional[str] = None) -> Optional[str]:
        """Route request to instance."""
        instance = self.select_instance(client_id)
        if instance:
            instance.current_connections += 1
            self.request_count += 1
            return f"{instance.host}:{instance.port}"
        return None

    def get_load_distribution(self) -> Dict[str, float]:
        """Get load distribution across instances."""
        return {
            instance_id: instance.get_load_percentage()
            for instance_id, instance in self.instances.items()
        }


class HealthChecker:
    """Monitors service health."""

    def __init__(self, check_interval_seconds: int = 30):
        self.check_interval = check_interval_seconds
        self.health_history: Dict[str, List[HealthStatus]] = {}
        self.last_check_time: Dict[str, datetime] = {}

    def check_instance_health(self, instance: ServiceInstance) -> HealthStatus:
        """Check instance health."""
        # In production, would make actual HTTP/gRPC call
        if instance.current_connections > instance.max_connections * 0.9:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY

        # Track history
        if instance.instance_id not in self.health_history:
            self.health_history[instance.instance_id] = []

        self.health_history[instance.instance_id].append(status)
        self.last_check_time[instance.instance_id] = datetime.now()

        return status

    def get_health_summary(self, instance_id: str) -> Dict:
        """Get health summary for instance."""
        history = self.health_history.get(instance_id, [])
        if not history:
            return {"status": "unknown", "checks": 0}

        healthy_count = sum(1 for s in history if s == HealthStatus.HEALTHY)
        return {
            "status": history[-1].value,
            "healthy_percentage": (healthy_count / len(history)) * 100,
            "total_checks": len(history)
        }


class DistributedTracing:
    """Distributed tracing for request flows."""

    def __init__(self):
        self.traces: Dict[str, Dict] = {}
        self.spans: Dict[str, List[Dict]] = {}

    def start_trace(self, trace_id: str, request_id: str) -> None:
        """Start new trace."""
        self.traces[trace_id] = {
            "trace_id": trace_id,
            "request_id": request_id,
            "started_at": datetime.now().isoformat(),
            "status": "in_progress"
        }
        self.spans[trace_id] = []

    def add_span(self, trace_id: str, span_name: str, service: str,
                duration_ms: float, status: str = "success") -> None:
        """Add span to trace."""
        if trace_id not in self.spans:
            self.spans[trace_id] = []

        span = {
            "span_id": f"span_{len(self.spans[trace_id])}",
            "name": span_name,
            "service": service,
            "duration_ms": duration_ms,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }

        self.spans[trace_id].append(span)

    def end_trace(self, trace_id: str, status: str = "success") -> None:
        """End trace."""
        if trace_id in self.traces:
            self.traces[trace_id]["status"] = status
            self.traces[trace_id]["ended_at"] = datetime.now().isoformat()

    def get_trace(self, trace_id: str) -> Optional[Dict]:
        """Get complete trace with spans."""
        if trace_id not in self.traces:
            return None

        return {
            **self.traces[trace_id],
            "spans": self.spans.get(trace_id, [])
        }


class ServiceMesh:
    """Service mesh for inter-service communication."""

    def __init__(self):
        self.services: Dict[str, List[ServiceInstance]] = {}
        self.load_balancers: Dict[str, LoadBalancer] = {}
        self.circuit_breakers: Dict[str, bool] = {}

    def register_service(self, service_name: str, instances: List[ServiceInstance],
                        strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN) -> None:
        """Register service with instances."""
        self.services[service_name] = instances
        lb = LoadBalancer(strategy)
        for instance in instances:
            lb.register_instance(instance)
        self.load_balancers[service_name] = lb
        self.circuit_breakers[service_name] = True  # Closed (operational)

    def call_service(self, service_name: str, client_id: Optional[str] = None) -> Optional[str]:
        """Call service through mesh."""
        if service_name not in self.load_balancers:
            return None

        if not self.circuit_breakers.get(service_name, True):
            return None  # Circuit open

        return self.load_balancers[service_name].route_request(client_id)

    def get_service_status(self, service_name: str) -> Dict:
        """Get service status."""
        if service_name not in self.services:
            return {"status": "unknown"}

        instances = self.services[service_name]
        healthy = sum(1 for i in instances if i.is_healthy)

        return {
            "service_name": service_name,
            "total_instances": len(instances),
            "healthy_instances": healthy,
            "circuit_breaker": "closed" if self.circuit_breakers.get(service_name) else "open",
            "load_distribution": self.load_balancers[service_name].get_load_distribution()
        }


class ContainerOrchestrator:
    """Container orchestration (like Kubernetes)."""

    def __init__(self):
        self.deployments: Dict[str, Dict] = {}
        self.pods: Dict[str, Dict] = {}
        self.services: Dict[str, Dict] = {}

    def create_deployment(self, name: str, image: str, replicas: int = 3) -> Dict:
        """Create deployment."""
        deployment = {
            "name": name,
            "image": image,
            "replicas": replicas,
            "created_at": datetime.now().isoformat(),
            "status": "creating",
            "pods": []
        }
        self.deployments[name] = deployment

        # Create pods
        for i in range(replicas):
            pod_name = f"{name}-pod-{i}"
            pod = {
                "name": pod_name,
                "deployment": name,
                "image": image,
                "status": "running",
                "created_at": datetime.now().isoformat()
            }
            self.pods[pod_name] = pod
            deployment["pods"].append(pod_name)

        deployment["status"] = "running"
        return deployment

    def scale_deployment(self, deployment_name: str, new_replicas: int) -> bool:
        """Scale deployment to new replica count."""
        if deployment_name not in self.deployments:
            return False

        deployment = self.deployments[deployment_name]
        current_replicas = len(deployment["pods"])

        if new_replicas > current_replicas:
            # Scale up
            for i in range(current_replicas, new_replicas):
                pod_name = f"{deployment_name}-pod-{i}"
                pod = {
                    "name": pod_name,
                    "deployment": deployment_name,
                    "image": deployment["image"],
                    "status": "running"
                }
                self.pods[pod_name] = pod
                deployment["pods"].append(pod_name)

        elif new_replicas < current_replicas:
            # Scale down
            pods_to_remove = deployment["pods"][new_replicas:]
            for pod_name in pods_to_remove:
                if pod_name in self.pods:
                    del self.pods[pod_name]
            deployment["pods"] = deployment["pods"][:new_replicas]

        return True

    def get_deployment_status(self, name: str) -> Optional[Dict]:
        """Get deployment status."""
        return self.deployments.get(name)


class DistributedInfrastructure:
    """Main distributed infrastructure orchestrator."""

    def __init__(self):
        self.load_balancer = LoadBalancer()
        self.health_checker = HealthChecker()
        self.tracing = DistributedTracing()
        self.mesh = ServiceMesh()
        self.orchestrator = ContainerOrchestrator()

    def register_and_scale_service(self, service_name: str, initial_replicas: int = 3) -> Dict:
        """Register service and create initial replicas."""
        # Create deployment
        deployment = self.orchestrator.create_deployment(service_name, f"image:{service_name}", initial_replicas)

        # Create service instances
        instances = []
        for i in range(initial_replicas):
            instance = ServiceInstance(
                instance_id=f"{service_name}-{i}",
                service_name=service_name,
                host="localhost",
                port=8000 + i,
                weight=1
            )
            instances.append(instance)

        # Register in mesh
        self.mesh.register_service(service_name, instances)

        return {
            "service": service_name,
            "deployment": deployment,
            "instances": len(instances)
        }

    def get_system_stats(self) -> Dict:
        """Get infrastructure statistics."""
        return {
            "services": len(self.mesh.services),
            "deployments": len(self.orchestrator.deployments),
            "total_pods": len(self.orchestrator.pods),
            "total_requests": self.load_balancer.request_count,
            "timestamp": datetime.now().isoformat()
        }


# Global instance
_distributed_infra = None


def get_distributed_infrastructure() -> DistributedInfrastructure:
    """Get or create global distributed infrastructure."""
    global _distributed_infra
    if _distributed_infra is None:
        _distributed_infra = DistributedInfrastructure()
    return _distributed_infra
