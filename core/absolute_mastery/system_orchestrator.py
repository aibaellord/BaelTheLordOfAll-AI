"""
👑 SYSTEM ORCHESTRATOR 👑
=========================
Orchestrates all systems.

Features:
- Module management
- Event routing
- System monitoring
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor


class ModuleStatus(Enum):
    """Module status"""
    INACTIVE = auto()
    INITIALIZING = auto()
    ACTIVE = auto()
    BUSY = auto()
    ERROR = auto()
    SHUTTING_DOWN = auto()


@dataclass
class SystemModule:
    """A system module"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Identity
    name: str = ""
    version: str = "1.0.0"

    # Status
    status: ModuleStatus = ModuleStatus.INACTIVE

    # Dependencies
    dependencies: List[str] = field(default_factory=list)

    # Interface
    capabilities: List[str] = field(default_factory=list)

    # Health
    health: float = 1.0
    last_heartbeat: datetime = field(default_factory=datetime.now)

    # Processing
    process_fn: Optional[Callable[[Any], Any]] = None

    def is_healthy(self, timeout_seconds: int = 30) -> bool:
        """Check if module is healthy"""
        if self.status == ModuleStatus.ERROR:
            return False

        elapsed = (datetime.now() - self.last_heartbeat).total_seconds()
        return elapsed < timeout_seconds and self.health > 0.3

    def heartbeat(self):
        """Record heartbeat"""
        self.last_heartbeat = datetime.now()


@dataclass
class OrchestratorConfig:
    """Orchestrator configuration"""
    max_parallel_modules: int = 10
    heartbeat_interval: float = 5.0
    error_threshold: int = 3
    auto_restart: bool = True
    event_buffer_size: int = 1000


@dataclass
class Event:
    """System event"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    event_type: str = ""
    source: str = ""
    target: str = ""

    data: Any = None

    priority: int = 0

    created_at: datetime = field(default_factory=datetime.now)

    def __lt__(self, other):
        return self.priority > other.priority  # Higher priority first


class EventBus:
    """
    Event bus for system communication.
    """

    def __init__(self, buffer_size: int = 1000):
        self.buffer_size = buffer_size

        # Subscribers
        self.subscribers: Dict[str, List[Callable[[Event], None]]] = {}

        # Event queue
        self.queue: List[Event] = []

        # Event history
        self.history: List[Event] = []

    def subscribe(self, event_type: str, callback: Callable[[Event], None]):
        """Subscribe to event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[Event], None]):
        """Unsubscribe from event type"""
        if event_type in self.subscribers:
            if callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)

    def publish(self, event: Event):
        """Publish event"""
        self.queue.append(event)

        # Enforce buffer size
        if len(self.queue) > self.buffer_size:
            self.queue.pop(0)

    def process(self) -> int:
        """Process pending events"""
        processed = 0

        while self.queue:
            event = self.queue.pop(0)

            # Notify subscribers
            callbacks = self.subscribers.get(event.event_type, [])
            callbacks.extend(self.subscribers.get('*', []))  # Wildcard subscribers

            for callback in callbacks:
                try:
                    callback(event)
                except Exception:
                    pass

            self.history.append(event)
            processed += 1

            # Limit history
            if len(self.history) > self.buffer_size:
                self.history.pop(0)

        return processed

    def get_history(
        self,
        event_type: str = None,
        source: str = None,
        limit: int = 100
    ) -> List[Event]:
        """Get event history"""
        results = self.history

        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if source:
            results = [e for e in results if e.source == source]

        return results[-limit:]


class SystemMonitor:
    """
    Monitors system health.
    """

    def __init__(self):
        # Metrics
        self.metrics: Dict[str, List[float]] = {}

        # Alerts
        self.alerts: List[Dict[str, Any]] = []

        # Thresholds
        self.thresholds: Dict[str, float] = {
            'cpu_usage': 0.9,
            'memory_usage': 0.9,
            'error_rate': 0.1,
            'latency': 1000.0
        }

    def record_metric(self, name: str, value: float):
        """Record metric value"""
        if name not in self.metrics:
            self.metrics[name] = []

        self.metrics[name].append(value)

        # Limit history
        if len(self.metrics[name]) > 1000:
            self.metrics[name].pop(0)

        # Check threshold
        if name in self.thresholds and value > self.thresholds[name]:
            self._raise_alert(name, value)

    def _raise_alert(self, metric: str, value: float):
        """Raise alert"""
        alert = {
            'metric': metric,
            'value': value,
            'threshold': self.thresholds[metric],
            'timestamp': datetime.now()
        }
        self.alerts.append(alert)

    def get_stats(self, metric: str) -> Dict[str, float]:
        """Get metric statistics"""
        values = self.metrics.get(metric, [])

        if not values:
            return {}

        return {
            'current': values[-1],
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'count': len(values)
        }

    def get_health_score(self) -> float:
        """Get overall health score"""
        if not self.metrics:
            return 1.0

        scores = []

        for metric, threshold in self.thresholds.items():
            values = self.metrics.get(metric, [])
            if values:
                # Score based on how far from threshold
                latest = values[-1]
                score = 1.0 - (latest / threshold)
                scores.append(max(0, min(1, score)))

        return sum(scores) / len(scores) if scores else 1.0

    def get_alerts(self, since: datetime = None) -> List[Dict[str, Any]]:
        """Get alerts"""
        if since:
            return [a for a in self.alerts if a['timestamp'] >= since]
        return self.alerts


class SystemOrchestrator:
    """
    The supreme system orchestrator.
    """

    def __init__(self, config: OrchestratorConfig = None):
        self.config = config or OrchestratorConfig()

        # Modules
        self.modules: Dict[str, SystemModule] = {}

        # Event bus
        self.event_bus = EventBus(self.config.event_buffer_size)

        # Monitor
        self.monitor = SystemMonitor()

        # Execution
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_parallel_modules)

        # State
        self.is_running = False
        self.error_counts: Dict[str, int] = {}

    def register_module(self, module: SystemModule):
        """Register a module"""
        self.modules[module.id] = module

        # Publish event
        self.event_bus.publish(Event(
            event_type='module_registered',
            source='orchestrator',
            data={'module_id': module.id, 'name': module.name}
        ))

    def unregister_module(self, module_id: str):
        """Unregister a module"""
        if module_id in self.modules:
            del self.modules[module_id]

            self.event_bus.publish(Event(
                event_type='module_unregistered',
                source='orchestrator',
                data={'module_id': module_id}
            ))

    def start_module(self, module_id: str) -> bool:
        """Start a module"""
        module = self.modules.get(module_id)
        if not module:
            return False

        # Check dependencies
        for dep_id in module.dependencies:
            dep = self.modules.get(dep_id)
            if not dep or dep.status != ModuleStatus.ACTIVE:
                return False

        module.status = ModuleStatus.INITIALIZING

        # Initialize
        module.status = ModuleStatus.ACTIVE
        module.heartbeat()

        self.event_bus.publish(Event(
            event_type='module_started',
            source='orchestrator',
            data={'module_id': module_id}
        ))

        return True

    def stop_module(self, module_id: str) -> bool:
        """Stop a module"""
        module = self.modules.get(module_id)
        if not module:
            return False

        module.status = ModuleStatus.SHUTTING_DOWN
        module.status = ModuleStatus.INACTIVE

        self.event_bus.publish(Event(
            event_type='module_stopped',
            source='orchestrator',
            data={'module_id': module_id}
        ))

        return True

    def route_to_module(
        self,
        module_id: str,
        data: Any
    ) -> Any:
        """Route data to module for processing"""
        module = self.modules.get(module_id)

        if not module or module.status != ModuleStatus.ACTIVE:
            return None

        if not module.process_fn:
            return None

        try:
            module.status = ModuleStatus.BUSY
            result = module.process_fn(data)
            module.status = ModuleStatus.ACTIVE
            module.heartbeat()

            # Clear error count on success
            self.error_counts[module_id] = 0

            return result

        except Exception as e:
            module.status = ModuleStatus.ERROR
            self.error_counts[module_id] = self.error_counts.get(module_id, 0) + 1

            self.event_bus.publish(Event(
                event_type='module_error',
                source='orchestrator',
                data={'module_id': module_id, 'error': str(e)}
            ))

            # Auto restart if configured
            if (self.config.auto_restart and
                self.error_counts[module_id] < self.config.error_threshold):
                self.start_module(module_id)

            return None

    def broadcast(self, event: Event):
        """Broadcast event to all modules"""
        self.event_bus.publish(event)

        for module_id, module in self.modules.items():
            if module.status == ModuleStatus.ACTIVE:
                self.route_to_module(module_id, event)

    def start(self):
        """Start orchestrator"""
        self.is_running = True

        # Start all modules
        for module_id in self.modules:
            self.start_module(module_id)

        self.event_bus.publish(Event(
            event_type='orchestrator_started',
            source='orchestrator'
        ))

    def stop(self):
        """Stop orchestrator"""
        # Stop all modules
        for module_id in list(self.modules.keys()):
            self.stop_module(module_id)

        self.is_running = False
        self.executor.shutdown(wait=False)

        self.event_bus.publish(Event(
            event_type='orchestrator_stopped',
            source='orchestrator'
        ))

    def tick(self):
        """Run one orchestration cycle"""
        # Process events
        self.event_bus.process()

        # Check module health
        for module_id, module in self.modules.items():
            if module.status == ModuleStatus.ACTIVE:
                if not module.is_healthy():
                    self.monitor.record_metric(f'{module_id}_health', module.health)

                    if self.config.auto_restart:
                        self.start_module(module_id)

        # Update monitor
        self.monitor.record_metric('active_modules',
            sum(1 for m in self.modules.values() if m.status == ModuleStatus.ACTIVE))

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        return {
            'is_running': self.is_running,
            'modules': {
                m.name: m.status.name
                for m in self.modules.values()
            },
            'health_score': self.monitor.get_health_score(),
            'pending_events': len(self.event_bus.queue),
            'active_alerts': len(self.monitor.get_alerts())
        }


# Export all
__all__ = [
    'ModuleStatus',
    'SystemModule',
    'OrchestratorConfig',
    'Event',
    'EventBus',
    'SystemMonitor',
    'SystemOrchestrator',
]
