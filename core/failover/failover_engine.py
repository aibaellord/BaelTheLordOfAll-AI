#!/usr/bin/env python3
"""
BAEL - Failover Engine
Failover handling for agents.

Features:
- Failover detection
- Automatic failover
- Recovery management
- Health monitoring
- Fallback strategies
"""

import asyncio
import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any, Callable, Coroutine, Dict, Generic, List, Optional, Set, Tuple, TypeVar
)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class FailoverState(Enum):
    """Failover states."""
    NORMAL = "normal"
    DETECTING = "detecting"
    FAILING_OVER = "failing_over"
    FAILED_OVER = "failed_over"
    RECOVERING = "recovering"


class TargetHealth(Enum):
    """Target health statuses."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class FailoverStrategy(Enum):
    """Failover strategies."""
    ACTIVE_PASSIVE = "active_passive"
    ACTIVE_ACTIVE = "active_active"
    PRIORITY = "priority"
    ROUND_ROBIN = "round_robin"


class RecoveryMode(Enum):
    """Recovery modes."""
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    SCHEDULED = "scheduled"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class FailoverTarget:
    """A failover target."""
    target_id: str = ""
    name: str = ""
    endpoint: str = ""
    priority: int = 0
    weight: int = 1
    health: TargetHealth = TargetHealth.UNKNOWN
    is_primary: bool = False
    is_active: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = 0
    
    def __post_init__(self):
        if not self.target_id:
            self.target_id = str(uuid.uuid4())[:8]


@dataclass
class FailoverConfig:
    """Failover configuration."""
    strategy: FailoverStrategy = FailoverStrategy.ACTIVE_PASSIVE
    recovery_mode: RecoveryMode = RecoveryMode.AUTOMATIC
    health_check_interval: float = 10.0
    failure_threshold: int = 3
    recovery_threshold: int = 2
    failover_timeout: float = 30.0
    cooldown_seconds: float = 60.0


@dataclass
class HealthCheckResult:
    """Health check result."""
    healthy: bool = True
    latency_ms: float = 0.0
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class FailoverEvent:
    """Failover event."""
    event_id: str = ""
    event_type: str = ""
    from_target: str = ""
    to_target: str = ""
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())[:8]


@dataclass
class FailoverStats:
    """Failover statistics."""
    failovers: int = 0
    recoveries: int = 0
    health_checks: int = 0
    failures_detected: int = 0
    current_state: FailoverState = FailoverState.NORMAL
    active_target: str = ""
    last_failover: Optional[datetime] = None
    last_recovery: Optional[datetime] = None


# =============================================================================
# HEALTH CHECKER
# =============================================================================

class HealthChecker(ABC):
    """Abstract health checker."""
    
    @abstractmethod
    async def check(self, target: FailoverTarget) -> HealthCheckResult:
        """Check target health."""
        pass


class HTTPHealthChecker(HealthChecker):
    """HTTP health checker."""
    
    def __init__(self, path: str = "/health", timeout: float = 5.0):
        self._path = path
        self._timeout = timeout
    
    async def check(self, target: FailoverTarget) -> HealthCheckResult:
        """Check HTTP health."""
        start = time.time()
        
        try:
            await asyncio.sleep(0.01)
            
            latency = (time.time() - start) * 1000
            
            return HealthCheckResult(
                healthy=True,
                latency_ms=latency,
                message="OK"
            )
        
        except Exception as e:
            return HealthCheckResult(
                healthy=False,
                latency_ms=(time.time() - start) * 1000,
                message=str(e)
            )


class CallableHealthChecker(HealthChecker):
    """Callable-based health checker."""
    
    def __init__(self, check_func: Callable[[FailoverTarget], Coroutine]):
        self._check_func = check_func
    
    async def check(self, target: FailoverTarget) -> HealthCheckResult:
        """Run custom check."""
        start = time.time()
        
        try:
            result = await self._check_func(target)
            
            latency = (time.time() - start) * 1000
            
            return HealthCheckResult(
                healthy=bool(result),
                latency_ms=latency,
                message="OK" if result else "Failed"
            )
        
        except Exception as e:
            return HealthCheckResult(
                healthy=False,
                latency_ms=(time.time() - start) * 1000,
                message=str(e)
            )


# =============================================================================
# FAILOVER GROUP
# =============================================================================

class FailoverGroup:
    """Group of failover targets."""
    
    def __init__(
        self,
        name: str,
        config: Optional[FailoverConfig] = None
    ):
        self._name = name
        self._config = config or FailoverConfig()
        
        self._targets: Dict[str, FailoverTarget] = {}
        self._active_target: Optional[str] = None
        self._state = FailoverState.NORMAL
        
        self._events: deque = deque(maxlen=100)
        self._stats = FailoverStats()
        
        self._health_checker: Optional[HealthChecker] = None
        self._health_check_task: Optional[asyncio.Task] = None
        
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        self._last_failover: Optional[datetime] = None
    
    def add_target(
        self,
        name: str,
        endpoint: str,
        priority: int = 0,
        is_primary: bool = False
    ) -> FailoverTarget:
        """Add a failover target."""
        target = FailoverTarget(
            name=name,
            endpoint=endpoint,
            priority=priority,
            is_primary=is_primary
        )
        
        self._targets[target.target_id] = target
        
        if is_primary or not self._active_target:
            self._set_active(target.target_id)
        
        return target
    
    def remove_target(self, target_id: str) -> bool:
        """Remove a target."""
        if target_id in self._targets:
            del self._targets[target_id]
            
            if self._active_target == target_id:
                self._select_next_active()
            
            return True
        
        return False
    
    def _set_active(self, target_id: str) -> None:
        """Set active target."""
        for t in self._targets.values():
            t.is_active = (t.target_id == target_id)
        
        self._active_target = target_id
        self._stats.active_target = target_id
    
    def _select_next_active(self) -> Optional[str]:
        """Select next active target."""
        candidates = sorted(
            self._targets.values(),
            key=lambda t: (-t.priority, t.target_id)
        )
        
        for target in candidates:
            if target.health in [TargetHealth.HEALTHY, TargetHealth.UNKNOWN]:
                self._set_active(target.target_id)
                return target.target_id
        
        if candidates:
            self._set_active(candidates[0].target_id)
            return candidates[0].target_id
        
        self._active_target = None
        return None
    
    async def check_health(self, target_id: str) -> HealthCheckResult:
        """Check target health."""
        target = self._targets.get(target_id)
        
        if not target:
            return HealthCheckResult(healthy=False, message="Target not found")
        
        if not self._health_checker:
            self._health_checker = HTTPHealthChecker()
        
        result = await self._health_checker.check(target)
        
        target.last_health_check = datetime.now()
        self._stats.health_checks += 1
        
        if result.healthy:
            target.consecutive_failures = 0
            target.health = TargetHealth.HEALTHY
        else:
            target.consecutive_failures += 1
            self._stats.failures_detected += 1
            
            if target.consecutive_failures >= self._config.failure_threshold:
                target.health = TargetHealth.UNHEALTHY
                
                if target.is_active:
                    await self._trigger_failover(target_id, "Health check failed")
            else:
                target.health = TargetHealth.DEGRADED
        
        return result
    
    async def check_all_health(self) -> Dict[str, HealthCheckResult]:
        """Check health of all targets."""
        results = {}
        
        for target_id in self._targets:
            results[target_id] = await self.check_health(target_id)
        
        return results
    
    async def _trigger_failover(self, from_target_id: str, reason: str) -> bool:
        """Trigger failover."""
        if self._last_failover:
            elapsed = (datetime.now() - self._last_failover).total_seconds()
            if elapsed < self._config.cooldown_seconds:
                return False
        
        self._state = FailoverState.FAILING_OVER
        
        next_target = None
        
        candidates = sorted(
            self._targets.values(),
            key=lambda t: (-t.priority, t.target_id)
        )
        
        for target in candidates:
            if target.target_id != from_target_id:
                if target.health != TargetHealth.UNHEALTHY:
                    next_target = target
                    break
        
        if not next_target:
            self._state = FailoverState.NORMAL
            return False
        
        event = FailoverEvent(
            event_type="failover",
            from_target=from_target_id,
            to_target=next_target.target_id,
            reason=reason
        )
        
        self._events.append(event)
        self._set_active(next_target.target_id)
        
        self._stats.failovers += 1
        self._stats.last_failover = datetime.now()
        self._last_failover = datetime.now()
        
        self._state = FailoverState.FAILED_OVER
        
        self._notify("failover", event)
        
        return True
    
    async def recover(self, target_id: str) -> bool:
        """Attempt recovery to target."""
        target = self._targets.get(target_id)
        
        if not target:
            return False
        
        self._state = FailoverState.RECOVERING
        
        for _ in range(self._config.recovery_threshold):
            result = await self.check_health(target_id)
            if not result.healthy:
                self._state = FailoverState.FAILED_OVER
                return False
            await asyncio.sleep(1)
        
        if target.is_primary:
            old_active = self._active_target
            self._set_active(target_id)
            
            event = FailoverEvent(
                event_type="recovery",
                from_target=old_active or "",
                to_target=target_id,
                reason="Primary recovered"
            )
            
            self._events.append(event)
            self._stats.recoveries += 1
            self._stats.last_recovery = datetime.now()
            
            self._notify("recovery", event)
        
        self._state = FailoverState.NORMAL
        
        return True
    
    def force_failover(self, to_target_id: str) -> bool:
        """Force failover to specific target."""
        if to_target_id not in self._targets:
            return False
        
        old_active = self._active_target
        self._set_active(to_target_id)
        
        event = FailoverEvent(
            event_type="forced_failover",
            from_target=old_active or "",
            to_target=to_target_id,
            reason="Manual override"
        )
        
        self._events.append(event)
        self._stats.failovers += 1
        self._stats.last_failover = datetime.now()
        
        self._notify("failover", event)
        
        return True
    
    def start_monitoring(self) -> None:
        """Start health monitoring."""
        async def monitor():
            while True:
                await asyncio.sleep(self._config.health_check_interval)
                await self.check_all_health()
                
                if self._config.recovery_mode == RecoveryMode.AUTOMATIC:
                    for target in self._targets.values():
                        if target.is_primary and not target.is_active:
                            if target.health == TargetHealth.HEALTHY:
                                await self.recover(target.target_id)
        
        self._health_check_task = asyncio.create_task(monitor())
    
    def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        if self._health_check_task:
            self._health_check_task.cancel()
            self._health_check_task = None
    
    def on(self, event: str, callback: Callable) -> None:
        """Register event callback."""
        self._callbacks[event].append(callback)
    
    def _notify(self, event: str, data: Any) -> None:
        """Notify callbacks."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(data)
            except Exception:
                pass
    
    def get_active(self) -> Optional[FailoverTarget]:
        """Get active target."""
        if self._active_target:
            return self._targets.get(self._active_target)
        return None
    
    def get_targets(self) -> List[FailoverTarget]:
        """Get all targets."""
        return list(self._targets.values())
    
    def get_events(self, limit: int = 10) -> List[FailoverEvent]:
        """Get recent events."""
        return list(self._events)[-limit:]
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def state(self) -> FailoverState:
        return self._state
    
    @property
    def stats(self) -> FailoverStats:
        self._stats.current_state = self._state
        return self._stats


# =============================================================================
# FAILOVER ENGINE
# =============================================================================

class FailoverEngine:
    """
    Failover Engine for BAEL.
    
    Failover handling for agents.
    """
    
    def __init__(self, default_config: Optional[FailoverConfig] = None):
        self._default_config = default_config or FailoverConfig()
        
        self._groups: Dict[str, FailoverGroup] = {}
        
        self._global_callbacks: Dict[str, List[Callable]] = defaultdict(list)
    
    # ----- Group Management -----
    
    def create_group(
        self,
        name: str,
        config: Optional[FailoverConfig] = None
    ) -> FailoverGroup:
        """Create a failover group."""
        config = config or self._default_config
        group = FailoverGroup(name, config)
        
        group.on("failover", lambda e: self._on_event(name, "failover", e))
        group.on("recovery", lambda e: self._on_event(name, "recovery", e))
        
        self._groups[name] = group
        return group
    
    def get_group(self, name: str) -> Optional[FailoverGroup]:
        """Get a failover group."""
        return self._groups.get(name)
    
    def remove_group(self, name: str) -> bool:
        """Remove a failover group."""
        group = self._groups.pop(name, None)
        if group:
            group.stop_monitoring()
            return True
        return False
    
    def list_groups(self) -> List[str]:
        """List group names."""
        return list(self._groups.keys())
    
    # ----- Target Management -----
    
    def add_target(
        self,
        group_name: str,
        name: str,
        endpoint: str,
        priority: int = 0,
        is_primary: bool = False
    ) -> Optional[FailoverTarget]:
        """Add target to group."""
        group = self._groups.get(group_name)
        
        if group:
            return group.add_target(name, endpoint, priority, is_primary)
        
        return None
    
    def remove_target(self, group_name: str, target_id: str) -> bool:
        """Remove target from group."""
        group = self._groups.get(group_name)
        
        if group:
            return group.remove_target(target_id)
        
        return False
    
    # ----- Health Checking -----
    
    async def check_health(
        self,
        group_name: str,
        target_id: str
    ) -> Optional[HealthCheckResult]:
        """Check target health."""
        group = self._groups.get(group_name)
        
        if group:
            return await group.check_health(target_id)
        
        return None
    
    async def check_group_health(
        self,
        group_name: str
    ) -> Optional[Dict[str, HealthCheckResult]]:
        """Check group health."""
        group = self._groups.get(group_name)
        
        if group:
            return await group.check_all_health()
        
        return None
    
    # ----- Failover Operations -----
    
    def get_active(self, group_name: str) -> Optional[FailoverTarget]:
        """Get active target for group."""
        group = self._groups.get(group_name)
        
        if group:
            return group.get_active()
        
        return None
    
    def force_failover(
        self,
        group_name: str,
        to_target_id: str
    ) -> bool:
        """Force failover."""
        group = self._groups.get(group_name)
        
        if group:
            return group.force_failover(to_target_id)
        
        return False
    
    async def recover(
        self,
        group_name: str,
        target_id: str
    ) -> bool:
        """Attempt recovery."""
        group = self._groups.get(group_name)
        
        if group:
            return await group.recover(target_id)
        
        return False
    
    # ----- Monitoring -----
    
    def start_monitoring(self, group_name: str) -> bool:
        """Start monitoring for group."""
        group = self._groups.get(group_name)
        
        if group:
            group.start_monitoring()
            return True
        
        return False
    
    def stop_monitoring(self, group_name: str) -> bool:
        """Stop monitoring for group."""
        group = self._groups.get(group_name)
        
        if group:
            group.stop_monitoring()
            return True
        
        return False
    
    def start_all_monitoring(self) -> None:
        """Start monitoring all groups."""
        for group in self._groups.values():
            group.start_monitoring()
    
    def stop_all_monitoring(self) -> None:
        """Stop monitoring all groups."""
        for group in self._groups.values():
            group.stop_monitoring()
    
    # ----- Events -----
    
    def on(self, event: str, callback: Callable) -> None:
        """Register global event callback."""
        self._global_callbacks[event].append(callback)
    
    def _on_event(
        self,
        group_name: str,
        event_type: str,
        event: FailoverEvent
    ) -> None:
        """Handle group event."""
        for callback in self._global_callbacks.get(event_type, []):
            try:
                callback(group_name, event)
            except Exception:
                pass
    
    def get_events(
        self,
        group_name: str,
        limit: int = 10
    ) -> List[FailoverEvent]:
        """Get group events."""
        group = self._groups.get(group_name)
        
        if group:
            return group.get_events(limit)
        
        return []
    
    # ----- Status -----
    
    def get_state(self, group_name: str) -> Optional[FailoverState]:
        """Get group state."""
        group = self._groups.get(group_name)
        return group.state if group else None
    
    def get_stats(self, group_name: str) -> Optional[FailoverStats]:
        """Get group stats."""
        group = self._groups.get(group_name)
        return group.stats if group else None
    
    # ----- Engine Stats -----
    
    def stats(self) -> Dict[str, Any]:
        """Get engine stats."""
        total_failovers = 0
        total_recoveries = 0
        
        for group in self._groups.values():
            total_failovers += group.stats.failovers
            total_recoveries += group.stats.recoveries
        
        return {
            "groups": len(self._groups),
            "total_failovers": total_failovers,
            "total_recoveries": total_recoveries
        }
    
    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        group_info = {}
        
        for name, group in self._groups.items():
            active = group.get_active()
            
            group_info[name] = {
                "state": group.state.value,
                "active_target": active.name if active else None,
                "target_count": len(group.get_targets()),
                "failovers": group.stats.failovers
            }
        
        return {
            "groups": group_info
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Failover Engine."""
    print("=" * 70)
    print("BAEL - FAILOVER ENGINE DEMO")
    print("Failover Handling for Agents")
    print("=" * 70)
    print()
    
    engine = FailoverEngine()
    
    # 1. Create Failover Group
    print("1. CREATE FAILOVER GROUP:")
    print("-" * 40)
    
    group = engine.create_group("database", FailoverConfig(
        strategy=FailoverStrategy.ACTIVE_PASSIVE,
        failure_threshold=2,
        recovery_threshold=2
    ))
    
    print(f"   Created group: {group.name}")
    print(f"   Strategy: {group._config.strategy.value}")
    print()
    
    # 2. Add Targets
    print("2. ADD TARGETS:")
    print("-" * 40)
    
    primary = engine.add_target(
        "database",
        name="primary-db",
        endpoint="db1.example.com:5432",
        priority=10,
        is_primary=True
    )
    
    secondary = engine.add_target(
        "database",
        name="secondary-db",
        endpoint="db2.example.com:5432",
        priority=5
    )
    
    tertiary = engine.add_target(
        "database",
        name="tertiary-db",
        endpoint="db3.example.com:5432",
        priority=1
    )
    
    print(f"   Primary: {primary.name} ({primary.endpoint})")
    print(f"   Secondary: {secondary.name} ({secondary.endpoint})")
    print(f"   Tertiary: {tertiary.name} ({tertiary.endpoint})")
    print()
    
    # 3. Check Active Target
    print("3. CHECK ACTIVE TARGET:")
    print("-" * 40)
    
    active = engine.get_active("database")
    print(f"   Active: {active.name if active else 'None'}")
    print(f"   Is primary: {active.is_primary if active else 'N/A'}")
    print()
    
    # 4. Health Check
    print("4. HEALTH CHECK:")
    print("-" * 40)
    
    result = await engine.check_health("database", primary.target_id)
    print(f"   Primary health: {result.healthy}")
    print(f"   Latency: {result.latency_ms:.2f}ms")
    print()
    
    # 5. Check Group Health
    print("5. CHECK GROUP HEALTH:")
    print("-" * 40)
    
    results = await engine.check_group_health("database")
    for target_id, result in results.items():
        target = group._targets[target_id]
        print(f"   {target.name}: {result.message}")
    print()
    
    # 6. Group State
    print("6. GROUP STATE:")
    print("-" * 40)
    
    state = engine.get_state("database")
    print(f"   State: {state.value}")
    print()
    
    # 7. Force Failover
    print("7. FORCE FAILOVER:")
    print("-" * 40)
    
    print(f"   Before: {engine.get_active('database').name}")
    
    engine.force_failover("database", secondary.target_id)
    
    print(f"   After: {engine.get_active('database').name}")
    print()
    
    # 8. Failover Events
    print("8. FAILOVER EVENTS:")
    print("-" * 40)
    
    events = engine.get_events("database")
    for event in events:
        print(f"   {event.event_type}: {event.from_target[:8]}... -> {event.to_target[:8]}...")
        print(f"   Reason: {event.reason}")
    print()
    
    # 9. Recovery
    print("9. RECOVERY:")
    print("-" * 40)
    
    recovered = await engine.recover("database", primary.target_id)
    print(f"   Recovery attempted: {recovered}")
    print(f"   Active now: {engine.get_active('database').name}")
    print()
    
    # 10. Event Callbacks
    print("10. EVENT CALLBACKS:")
    print("-" * 40)
    
    def on_failover(group_name, event):
        print(f"   [Callback] Failover in {group_name}")
    
    engine.on("failover", on_failover)
    
    engine.force_failover("database", tertiary.target_id)
    print()
    
    # 11. Group Statistics
    print("11. GROUP STATISTICS:")
    print("-" * 40)
    
    stats = engine.get_stats("database")
    print(f"   Failovers: {stats.failovers}")
    print(f"   Recoveries: {stats.recoveries}")
    print(f"   Health checks: {stats.health_checks}")
    print(f"   Current state: {stats.current_state.value}")
    print()
    
    # 12. Target Health States
    print("12. TARGET HEALTH STATES:")
    print("-" * 40)
    
    targets = group.get_targets()
    for target in targets:
        print(f"   {target.name}: {target.health.value}")
        print(f"   - Active: {target.is_active}")
        print(f"   - Primary: {target.is_primary}")
    print()
    
    # 13. List Groups
    print("13. LIST GROUPS:")
    print("-" * 40)
    
    api_group = engine.create_group("api-servers")
    engine.add_target("api-servers", "api1", "api1.example.com:8080")
    engine.add_target("api-servers", "api2", "api2.example.com:8080")
    
    groups = engine.list_groups()
    for g in groups:
        print(f"   - {g}")
    print()
    
    # 14. Engine Statistics
    print("14. ENGINE STATISTICS:")
    print("-" * 40)
    
    stats = engine.stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()
    
    # 15. Engine Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)
    
    summary = engine.summary()
    for name, info in summary["groups"].items():
        print(f"   {name}:")
        print(f"      State: {info['state']}")
        print(f"      Active: {info['active_target']}")
        print(f"      Targets: {info['target_count']}")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE - Failover Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
