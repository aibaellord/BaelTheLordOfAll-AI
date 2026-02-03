#!/usr/bin/env python3
"""
BAEL - Health Engine
Health monitoring for agents.

Features:
- Health checks
- Liveness and readiness probes
- Dependency checking
- Health aggregation
- Alert thresholds
"""

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any, Callable, Dict, Generic, List, Optional, Set, Tuple, Type, TypeVar, Union
)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class HealthStatus(Enum):
    """Health status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CheckType(Enum):
    """Health check types."""
    LIVENESS = "liveness"
    READINESS = "readiness"
    STARTUP = "startup"
    CUSTOM = "custom"


class DependencyType(Enum):
    """Dependency types."""
    DATABASE = "database"
    CACHE = "cache"
    API = "api"
    QUEUE = "queue"
    STORAGE = "storage"
    SERVICE = "service"
    OTHER = "other"


class AlertLevel(Enum):
    """Alert levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class HealthConfig:
    """Health configuration."""
    check_interval: float = 30.0
    timeout: float = 10.0
    failure_threshold: int = 3
    success_threshold: int = 1
    enable_alerts: bool = True


@dataclass
class CheckResult:
    """Result of a health check."""
    name: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN
    message: str = ""
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyInfo:
    """Information about a dependency."""
    name: str = ""
    dependency_type: DependencyType = DependencyType.OTHER
    endpoint: str = ""
    required: bool = True
    status: HealthStatus = HealthStatus.UNKNOWN
    last_check: Optional[datetime] = None
    consecutive_failures: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthReport:
    """Overall health report."""
    status: HealthStatus = HealthStatus.UNKNOWN
    timestamp: datetime = field(default_factory=datetime.now)
    checks: Dict[str, CheckResult] = field(default_factory=dict)
    dependencies: Dict[str, DependencyInfo] = field(default_factory=dict)
    uptime_seconds: float = 0.0
    version: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertConfig:
    """Alert configuration."""
    level: AlertLevel = AlertLevel.WARNING
    consecutive_failures: int = 3
    cooldown_seconds: float = 300.0


@dataclass
class Alert:
    """Health alert."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    level: AlertLevel = AlertLevel.WARNING
    check_name: str = ""
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class HealthStats:
    """Health statistics."""
    checks_performed: int = 0
    checks_passed: int = 0
    checks_failed: int = 0
    alerts_triggered: int = 0
    uptime_percentage: float = 100.0


# =============================================================================
# HEALTH CHECK INTERFACE
# =============================================================================

class HealthCheck(ABC):
    """Abstract health check."""
    
    def __init__(self, name: str, check_type: CheckType = CheckType.CUSTOM):
        self._name = name
        self._check_type = check_type
        self._last_result: Optional[CheckResult] = None
        self._consecutive_failures = 0
        self._consecutive_successes = 0
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def check_type(self) -> CheckType:
        return self._check_type
    
    @property
    def last_result(self) -> Optional[CheckResult]:
        return self._last_result
    
    @abstractmethod
    async def check(self) -> CheckResult:
        """Perform the health check."""
        pass
    
    async def run(self) -> CheckResult:
        """Run the health check and track state."""
        start_time = time.perf_counter()
        
        try:
            result = await self.check()
            result.duration_ms = (time.perf_counter() - start_time) * 1000
            
            if result.status == HealthStatus.HEALTHY:
                self._consecutive_successes += 1
                self._consecutive_failures = 0
            else:
                self._consecutive_failures += 1
                self._consecutive_successes = 0
            
            self._last_result = result
            return result
        
        except Exception as e:
            self._consecutive_failures += 1
            self._consecutive_successes = 0
            
            result = CheckResult(
                name=self._name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                duration_ms=(time.perf_counter() - start_time) * 1000
            )
            
            self._last_result = result
            return result


# =============================================================================
# BUILT-IN HEALTH CHECKS
# =============================================================================

class CallableHealthCheck(HealthCheck):
    """Health check from a callable."""
    
    def __init__(
        self,
        name: str,
        func: Callable[[], Union[bool, Tuple[bool, str]]],
        check_type: CheckType = CheckType.CUSTOM
    ):
        super().__init__(name, check_type)
        self._func = func
    
    async def check(self) -> CheckResult:
        """Run the callable."""
        try:
            if asyncio.iscoroutinefunction(self._func):
                result = await self._func()
            else:
                result = self._func()
            
            if isinstance(result, tuple):
                healthy, message = result
            else:
                healthy = bool(result)
                message = "OK" if healthy else "Check failed"
            
            return CheckResult(
                name=self._name,
                status=HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY,
                message=message
            )
        
        except Exception as e:
            return CheckResult(
                name=self._name,
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            )


class DependencyHealthCheck(HealthCheck):
    """Health check for a dependency."""
    
    def __init__(
        self,
        name: str,
        dependency: DependencyInfo,
        check_func: Callable[[], bool]
    ):
        super().__init__(name, CheckType.READINESS)
        self._dependency = dependency
        self._check_func = check_func
    
    async def check(self) -> CheckResult:
        """Check the dependency."""
        try:
            if asyncio.iscoroutinefunction(self._check_func):
                healthy = await self._check_func()
            else:
                healthy = self._check_func()
            
            self._dependency.status = HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY
            self._dependency.last_check = datetime.now()
            
            if healthy:
                self._dependency.consecutive_failures = 0
            else:
                self._dependency.consecutive_failures += 1
            
            return CheckResult(
                name=self._name,
                status=self._dependency.status,
                message=f"Dependency {self._dependency.name}: {self._dependency.status.value}",
                details={
                    "dependency_type": self._dependency.dependency_type.value,
                    "endpoint": self._dependency.endpoint
                }
            )
        
        except Exception as e:
            self._dependency.status = HealthStatus.UNHEALTHY
            self._dependency.consecutive_failures += 1
            
            return CheckResult(
                name=self._name,
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            )


class MemoryHealthCheck(HealthCheck):
    """Check memory usage."""
    
    def __init__(
        self,
        name: str = "memory",
        threshold_percent: float = 90.0
    ):
        super().__init__(name, CheckType.LIVENESS)
        self._threshold = threshold_percent
    
    async def check(self) -> CheckResult:
        """Check memory usage."""
        import gc
        
        gc.collect()
        
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            memory_mb = usage.ru_maxrss / 1024
            
            status = HealthStatus.HEALTHY
            message = f"Memory usage: {memory_mb:.1f} MB"
            
            if memory_mb > 1000:
                status = HealthStatus.DEGRADED
            
            return CheckResult(
                name=self._name,
                status=status,
                message=message,
                details={"memory_mb": memory_mb}
            )
        
        except ImportError:
            return CheckResult(
                name=self._name,
                status=HealthStatus.HEALTHY,
                message="Memory check not available on this platform"
            )


class AlwaysHealthyCheck(HealthCheck):
    """Always returns healthy (for testing)."""
    
    def __init__(self, name: str = "always_healthy"):
        super().__init__(name, CheckType.LIVENESS)
    
    async def check(self) -> CheckResult:
        return CheckResult(
            name=self._name,
            status=HealthStatus.HEALTHY,
            message="Always healthy"
        )


# =============================================================================
# HEALTH AGGREGATOR
# =============================================================================

class HealthAggregator:
    """Aggregates multiple health checks."""
    
    def __init__(self):
        self._checks: Dict[str, HealthCheck] = {}
        self._dependencies: Dict[str, DependencyInfo] = {}
    
    def add_check(self, check: HealthCheck) -> None:
        """Add a health check."""
        self._checks[check.name] = check
    
    def remove_check(self, name: str) -> None:
        """Remove a health check."""
        if name in self._checks:
            del self._checks[name]
    
    def add_dependency(self, dependency: DependencyInfo) -> None:
        """Add a dependency."""
        self._dependencies[dependency.name] = dependency
    
    async def run_all(self) -> Dict[str, CheckResult]:
        """Run all health checks."""
        results = {}
        
        tasks = [check.run() for check in self._checks.values()]
        check_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for check, result in zip(self._checks.values(), check_results):
            if isinstance(result, Exception):
                results[check.name] = CheckResult(
                    name=check.name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(result)
                )
            else:
                results[check.name] = result
        
        return results
    
    async def run_by_type(self, check_type: CheckType) -> Dict[str, CheckResult]:
        """Run health checks by type."""
        results = {}
        
        for check in self._checks.values():
            if check.check_type == check_type:
                results[check.name] = await check.run()
        
        return results
    
    def get_aggregate_status(self, results: Dict[str, CheckResult]) -> HealthStatus:
        """Get aggregate health status."""
        if not results:
            return HealthStatus.UNKNOWN
        
        statuses = [r.status for r in results.values()]
        
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        
        if any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        
        return HealthStatus.UNKNOWN
    
    def get_check(self, name: str) -> Optional[HealthCheck]:
        """Get a health check."""
        return self._checks.get(name)
    
    def list_checks(self) -> List[str]:
        """List all check names."""
        return list(self._checks.keys())


# =============================================================================
# ALERT MANAGER
# =============================================================================

class AlertManager:
    """Manages health alerts."""
    
    def __init__(self, config: Optional[AlertConfig] = None):
        self._config = config or AlertConfig()
        self._alerts: Dict[str, Alert] = {}
        self._history: List[Alert] = []
        self._callbacks: List[Callable[[Alert], None]] = []
        self._cooldowns: Dict[str, datetime] = {}
    
    def check_and_alert(self, result: CheckResult, check: HealthCheck) -> Optional[Alert]:
        """Check if an alert should be triggered."""
        if result.status == HealthStatus.HEALTHY:
            existing = self._alerts.get(result.name)
            if existing and not existing.resolved:
                existing.resolved = True
                existing.resolved_at = datetime.now()
            return None
        
        if check._consecutive_failures < self._config.consecutive_failures:
            return None
        
        cooldown = self._cooldowns.get(result.name)
        if cooldown and datetime.now() < cooldown:
            return None
        
        level = AlertLevel.CRITICAL if result.status == HealthStatus.UNHEALTHY else AlertLevel.WARNING
        
        alert = Alert(
            level=level,
            check_name=result.name,
            message=result.message
        )
        
        self._alerts[result.name] = alert
        self._history.append(alert)
        self._cooldowns[result.name] = datetime.now() + timedelta(seconds=self._config.cooldown_seconds)
        
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception:
                pass
        
        return alert
    
    def add_callback(self, callback: Callable[[Alert], None]) -> None:
        """Add an alert callback."""
        self._callbacks.append(callback)
    
    def get_active_alerts(self) -> List[Alert]:
        """Get active (unresolved) alerts."""
        return [a for a in self._alerts.values() if not a.resolved]
    
    def get_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history."""
        return list(reversed(self._history[-limit:]))
    
    def clear_alert(self, check_name: str) -> None:
        """Clear an alert."""
        if check_name in self._alerts:
            self._alerts[check_name].resolved = True
            self._alerts[check_name].resolved_at = datetime.now()


# =============================================================================
# HEALTH ENGINE
# =============================================================================

class HealthEngine:
    """
    Health Engine for BAEL.
    
    Health monitoring for agents.
    """
    
    def __init__(self, config: Optional[HealthConfig] = None):
        self._config = config or HealthConfig()
        self._aggregator = HealthAggregator()
        self._alert_manager = AlertManager()
        self._start_time = datetime.now()
        self._version = "1.0.0"
        self._stats = HealthStats()
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._metadata: Dict[str, Any] = {}
    
    # ----- Check Management -----
    
    def add_check(self, check: HealthCheck) -> None:
        """Add a health check."""
        self._aggregator.add_check(check)
    
    def add_callable_check(
        self,
        name: str,
        func: Callable[[], Union[bool, Tuple[bool, str]]],
        check_type: CheckType = CheckType.CUSTOM
    ) -> None:
        """Add a health check from a callable."""
        check = CallableHealthCheck(name, func, check_type)
        self._aggregator.add_check(check)
    
    def add_liveness_check(
        self,
        name: str,
        func: Callable[[], Union[bool, Tuple[bool, str]]]
    ) -> None:
        """Add a liveness check."""
        self.add_callable_check(name, func, CheckType.LIVENESS)
    
    def add_readiness_check(
        self,
        name: str,
        func: Callable[[], Union[bool, Tuple[bool, str]]]
    ) -> None:
        """Add a readiness check."""
        self.add_callable_check(name, func, CheckType.READINESS)
    
    def remove_check(self, name: str) -> None:
        """Remove a health check."""
        self._aggregator.remove_check(name)
    
    def list_checks(self) -> List[str]:
        """List all check names."""
        return self._aggregator.list_checks()
    
    # ----- Dependency Management -----
    
    def add_dependency(
        self,
        name: str,
        dependency_type: DependencyType,
        check_func: Callable[[], bool],
        endpoint: str = "",
        required: bool = True
    ) -> None:
        """Add a dependency with health check."""
        dependency = DependencyInfo(
            name=name,
            dependency_type=dependency_type,
            endpoint=endpoint,
            required=required
        )
        
        self._aggregator.add_dependency(dependency)
        
        check = DependencyHealthCheck(f"dep:{name}", dependency, check_func)
        self._aggregator.add_check(check)
    
    # ----- Check Execution -----
    
    async def check_health(self) -> HealthReport:
        """Run all health checks and return report."""
        results = await self._aggregator.run_all()
        
        for name, result in results.items():
            self._stats.checks_performed += 1
            
            if result.status == HealthStatus.HEALTHY:
                self._stats.checks_passed += 1
            else:
                self._stats.checks_failed += 1
            
            check = self._aggregator.get_check(name)
            if check and self._config.enable_alerts:
                alert = self._alert_manager.check_and_alert(result, check)
                if alert:
                    self._stats.alerts_triggered += 1
        
        status = self._aggregator.get_aggregate_status(results)
        uptime = (datetime.now() - self._start_time).total_seconds()
        
        return HealthReport(
            status=status,
            checks=results,
            dependencies=self._aggregator._dependencies,
            uptime_seconds=uptime,
            version=self._version,
            metadata=self._metadata
        )
    
    async def check_liveness(self) -> HealthReport:
        """Run liveness checks."""
        results = await self._aggregator.run_by_type(CheckType.LIVENESS)
        status = self._aggregator.get_aggregate_status(results)
        
        return HealthReport(
            status=status,
            checks=results,
            uptime_seconds=(datetime.now() - self._start_time).total_seconds()
        )
    
    async def check_readiness(self) -> HealthReport:
        """Run readiness checks."""
        results = await self._aggregator.run_by_type(CheckType.READINESS)
        status = self._aggregator.get_aggregate_status(results)
        
        return HealthReport(
            status=status,
            checks=results,
            dependencies=self._aggregator._dependencies
        )
    
    async def check_startup(self) -> HealthReport:
        """Run startup checks."""
        results = await self._aggregator.run_by_type(CheckType.STARTUP)
        status = self._aggregator.get_aggregate_status(results)
        
        return HealthReport(
            status=status,
            checks=results
        )
    
    # ----- Monitoring -----
    
    async def start_monitoring(self) -> None:
        """Start continuous health monitoring."""
        self._running = True
        
        while self._running:
            await self.check_health()
            await asyncio.sleep(self._config.check_interval)
    
    def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        self._running = False
    
    # ----- Alerts -----
    
    def add_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        """Add an alert callback."""
        self._alert_manager.add_callback(callback)
    
    def get_active_alerts(self) -> List[Alert]:
        """Get active alerts."""
        return self._alert_manager.get_active_alerts()
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history."""
        return self._alert_manager.get_history(limit)
    
    # ----- Status -----
    
    def is_healthy(self, report: HealthReport) -> bool:
        """Check if the report indicates healthy status."""
        return report.status == HealthStatus.HEALTHY
    
    def is_ready(self, report: HealthReport) -> bool:
        """Check if ready based on report."""
        return report.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
    
    # ----- Metadata -----
    
    def set_version(self, version: str) -> None:
        """Set the application version."""
        self._version = version
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata."""
        self._metadata[key] = value
    
    # ----- Stats -----
    
    @property
    def stats(self) -> HealthStats:
        total = self._stats.checks_passed + self._stats.checks_failed
        if total > 0:
            self._stats.uptime_percentage = (self._stats.checks_passed / total) * 100
        return self._stats
    
    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "checks_registered": len(self._aggregator.list_checks()),
            "dependencies_registered": len(self._aggregator._dependencies),
            "checks_performed": self._stats.checks_performed,
            "checks_passed": self._stats.checks_passed,
            "checks_failed": self._stats.checks_failed,
            "alerts_triggered": self._stats.alerts_triggered,
            "uptime_percentage": self.stats.uptime_percentage,
            "version": self._version
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Health Engine."""
    print("=" * 70)
    print("BAEL - HEALTH ENGINE DEMO")
    print("Health Monitoring for Agents")
    print("=" * 70)
    print()
    
    engine = HealthEngine(HealthConfig(
        check_interval=5.0,
        enable_alerts=True
    ))
    
    engine.set_version("1.0.0")
    engine.set_metadata("environment", "development")
    
    # 1. Add Liveness Check
    print("1. ADD LIVENESS CHECK:")
    print("-" * 40)
    
    def simple_liveness():
        return True, "Application is alive"
    
    engine.add_liveness_check("simple_liveness", simple_liveness)
    print(f"   Added liveness check")
    print()
    
    # 2. Add Readiness Check
    print("2. ADD READINESS CHECK:")
    print("-" * 40)
    
    ready_state = {"ready": True}
    
    def readiness_check():
        return ready_state["ready"], "Ready to serve requests"
    
    engine.add_readiness_check("app_readiness", readiness_check)
    print(f"   Added readiness check")
    print()
    
    # 3. Add Memory Check
    print("3. ADD MEMORY CHECK:")
    print("-" * 40)
    
    memory_check = MemoryHealthCheck()
    engine.add_check(memory_check)
    print(f"   Added memory check")
    print()
    
    # 4. Add Dependency
    print("4. ADD DEPENDENCY:")
    print("-" * 40)
    
    def check_database():
        return True
    
    engine.add_dependency(
        name="postgres",
        dependency_type=DependencyType.DATABASE,
        check_func=check_database,
        endpoint="localhost:5432",
        required=True
    )
    
    print(f"   Added database dependency")
    print()
    
    # 5. Add Always Healthy Check
    print("5. ADD ALWAYS HEALTHY CHECK:")
    print("-" * 40)
    
    engine.add_check(AlwaysHealthyCheck())
    print(f"   Added always healthy check")
    print()
    
    # 6. List Checks
    print("6. LIST CHECKS:")
    print("-" * 40)
    
    checks = engine.list_checks()
    for check in checks:
        print(f"   - {check}")
    print()
    
    # 7. Run Health Check
    print("7. RUN HEALTH CHECK:")
    print("-" * 40)
    
    report = await engine.check_health()
    
    print(f"   Status: {report.status.value}")
    print(f"   Uptime: {report.uptime_seconds:.1f}s")
    print(f"   Version: {report.version}")
    print()
    
    # 8. Check Results
    print("8. CHECK RESULTS:")
    print("-" * 40)
    
    for name, result in report.checks.items():
        print(f"   {name}:")
        print(f"     Status: {result.status.value}")
        print(f"     Message: {result.message}")
        print(f"     Duration: {result.duration_ms:.2f}ms")
    print()
    
    # 9. Check Liveness
    print("9. CHECK LIVENESS:")
    print("-" * 40)
    
    liveness = await engine.check_liveness()
    print(f"   Liveness status: {liveness.status.value}")
    print(f"   Checks: {list(liveness.checks.keys())}")
    print()
    
    # 10. Check Readiness
    print("10. CHECK READINESS:")
    print("-" * 40)
    
    readiness = await engine.check_readiness()
    print(f"   Readiness status: {readiness.status.value}")
    print(f"   Is ready: {engine.is_ready(readiness)}")
    print()
    
    # 11. Simulate Failure
    print("11. SIMULATE FAILURE:")
    print("-" * 40)
    
    def failing_check():
        return False, "Simulated failure"
    
    engine.add_callable_check("failing_service", failing_check, CheckType.CUSTOM)
    
    for i in range(4):
        report = await engine.check_health()
        print(f"   Check {i + 1}: {report.status.value}")
    
    print()
    
    # 12. Active Alerts
    print("12. ACTIVE ALERTS:")
    print("-" * 40)
    
    alerts = engine.get_active_alerts()
    print(f"   Active alerts: {len(alerts)}")
    for alert in alerts:
        print(f"   - {alert.check_name}: {alert.level.value} - {alert.message}")
    print()
    
    # 13. Alert Callback
    print("13. ALERT CALLBACK:")
    print("-" * 40)
    
    alert_log = []
    
    def on_alert(alert: Alert):
        alert_log.append(alert)
        print(f"   ALERT: {alert.check_name} - {alert.message}")
    
    engine.add_alert_callback(on_alert)
    await engine.check_health()
    print(f"   Alerts logged: {len(alert_log)}")
    print()
    
    # 14. Dependencies
    print("14. DEPENDENCIES:")
    print("-" * 40)
    
    for name, dep in report.dependencies.items():
        print(f"   {name}:")
        print(f"     Type: {dep.dependency_type.value}")
        print(f"     Status: {dep.status.value}")
        print(f"     Required: {dep.required}")
    print()
    
    # 15. Statistics
    print("15. STATISTICS:")
    print("-" * 40)
    
    stats = engine.stats
    print(f"   Checks performed: {stats.checks_performed}")
    print(f"   Checks passed: {stats.checks_passed}")
    print(f"   Checks failed: {stats.checks_failed}")
    print(f"   Alerts triggered: {stats.alerts_triggered}")
    print(f"   Uptime percentage: {stats.uptime_percentage:.1f}%")
    print()
    
    # 16. Engine Summary
    print("16. ENGINE SUMMARY:")
    print("-" * 40)
    
    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE - Health Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
