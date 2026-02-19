"""
⚡ SELF-HEALING ⚡
=================
Self-healing and recovery systems.

Features:
- Health monitoring
- Automatic recovery
- Redundancy management
- Graceful degradation
"""

import math
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
import uuid
import asyncio


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = auto()
    DEGRADED = auto()
    UNHEALTHY = auto()
    CRITICAL = auto()
    UNKNOWN = auto()


@dataclass
class HealthCheck:
    """A health check"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""

    # Check function
    check_function: Callable = None

    # Configuration
    interval_seconds: float = 60.0
    timeout_seconds: float = 10.0

    # State
    last_check: datetime = None
    last_status: HealthStatus = HealthStatus.UNKNOWN
    consecutive_failures: int = 0

    # Thresholds
    failure_threshold: int = 3
    recovery_threshold: int = 2

    # History
    history: List[Tuple[datetime, HealthStatus]] = field(default_factory=list)

    def run(self) -> HealthStatus:
        """Run health check"""
        self.last_check = datetime.now()

        try:
            if self.check_function:
                result = self.check_function()
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
            else:
                status = HealthStatus.UNKNOWN
        except Exception:
            status = HealthStatus.UNHEALTHY

        # Update state
        if status == HealthStatus.HEALTHY:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1

        if self.consecutive_failures >= self.failure_threshold:
            status = HealthStatus.CRITICAL

        self.last_status = status
        self.history.append((self.last_check, status))

        # Keep only recent history
        if len(self.history) > 100:
            self.history = self.history[-100:]

        return status

    def get_availability(self) -> float:
        """Calculate availability percentage"""
        if not self.history:
            return 1.0

        healthy = sum(1 for _, status in self.history if status == HealthStatus.HEALTHY)
        return healthy / len(self.history)


@dataclass
class RecoveryAction:
    """A recovery action"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""

    # Action
    action_function: Callable = None

    # Trigger conditions
    triggers: List[HealthStatus] = field(default_factory=lambda: [HealthStatus.UNHEALTHY])

    # Configuration
    max_attempts: int = 3
    cooldown_seconds: float = 60.0

    # State
    attempts: int = 0
    last_attempt: datetime = None
    successful_recoveries: int = 0

    def can_execute(self) -> bool:
        """Check if action can be executed"""
        if self.attempts >= self.max_attempts:
            return False

        if self.last_attempt:
            cooldown = timedelta(seconds=self.cooldown_seconds)
            if datetime.now() - self.last_attempt < cooldown:
                return False

        return True

    def execute(self) -> bool:
        """Execute recovery action"""
        if not self.can_execute():
            return False

        self.last_attempt = datetime.now()
        self.attempts += 1

        try:
            if self.action_function:
                result = self.action_function()
                if result:
                    self.successful_recoveries += 1
                    self.attempts = 0  # Reset on success
                return result
        except Exception:
            pass

        return False

    def reset(self):
        """Reset action state"""
        self.attempts = 0
        self.last_attempt = None


class SelfHealingSystem:
    """
    Self-healing system with automatic recovery.
    """

    def __init__(self):
        # Health checks
        self.health_checks: Dict[str, HealthCheck] = {}

        # Recovery actions
        self.recovery_actions: Dict[str, RecoveryAction] = {}

        # Mappings
        self.check_to_actions: Dict[str, List[str]] = {}

        # State
        self.is_running = False
        self.overall_health = HealthStatus.UNKNOWN

        # History
        self.incident_history: List[Dict] = []

    def register_health_check(
        self,
        name: str,
        check_function: Callable,
        interval: float = 60.0
    ) -> HealthCheck:
        """Register a health check"""
        check = HealthCheck(
            name=name,
            check_function=check_function,
            interval_seconds=interval
        )
        self.health_checks[name] = check
        return check

    def register_recovery_action(
        self,
        name: str,
        action_function: Callable,
        triggers: List[HealthStatus] = None
    ) -> RecoveryAction:
        """Register a recovery action"""
        action = RecoveryAction(
            name=name,
            action_function=action_function,
            triggers=triggers or [HealthStatus.UNHEALTHY]
        )
        self.recovery_actions[name] = action
        return action

    def link_check_to_action(self, check_name: str, action_name: str):
        """Link a health check to a recovery action"""
        if check_name not in self.check_to_actions:
            self.check_to_actions[check_name] = []
        self.check_to_actions[check_name].append(action_name)

    def run_all_checks(self) -> Dict[str, HealthStatus]:
        """Run all health checks"""
        results = {}

        for name, check in self.health_checks.items():
            status = check.run()
            results[name] = status

            # Trigger recovery if needed
            if status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
                self._trigger_recovery(name, status)

        # Update overall health
        self._update_overall_health(results)

        return results

    def _trigger_recovery(self, check_name: str, status: HealthStatus):
        """Trigger recovery actions for a check"""
        action_names = self.check_to_actions.get(check_name, [])

        for action_name in action_names:
            action = self.recovery_actions.get(action_name)
            if action and status in action.triggers:
                success = action.execute()

                # Log incident
                self.incident_history.append({
                    'timestamp': datetime.now(),
                    'check': check_name,
                    'status': status.name,
                    'action': action_name,
                    'success': success
                })

    def _update_overall_health(self, results: Dict[str, HealthStatus]):
        """Update overall system health"""
        if not results:
            self.overall_health = HealthStatus.UNKNOWN
            return

        statuses = list(results.values())

        if any(s == HealthStatus.CRITICAL for s in statuses):
            self.overall_health = HealthStatus.CRITICAL
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            self.overall_health = HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            self.overall_health = HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            self.overall_health = HealthStatus.HEALTHY
        else:
            self.overall_health = HealthStatus.UNKNOWN

    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        return {
            'overall_health': self.overall_health.name,
            'checks': {
                name: {
                    'status': check.last_status.name,
                    'availability': check.get_availability(),
                    'consecutive_failures': check.consecutive_failures
                }
                for name, check in self.health_checks.items()
            },
            'recent_incidents': self.incident_history[-10:]
        }


class RedundancyManager:
    """
    Manage redundant components.
    """

    def __init__(self):
        # Component groups
        self.component_groups: Dict[str, List[Any]] = {}

        # Health tracking per component
        self.component_health: Dict[str, HealthStatus] = {}

        # Active component per group
        self.active_components: Dict[str, int] = {}

    def register_group(self, group_name: str, components: List[Any]):
        """Register a redundant component group"""
        self.component_groups[group_name] = components
        self.active_components[group_name] = 0

        for i, _ in enumerate(components):
            key = f"{group_name}:{i}"
            self.component_health[key] = HealthStatus.HEALTHY

    def get_active(self, group_name: str) -> Optional[Any]:
        """Get active component from group"""
        if group_name not in self.component_groups:
            return None

        components = self.component_groups[group_name]
        active_idx = self.active_components.get(group_name, 0)

        if 0 <= active_idx < len(components):
            return components[active_idx]

        return None

    def mark_unhealthy(self, group_name: str, component_idx: int):
        """Mark component as unhealthy"""
        key = f"{group_name}:{component_idx}"
        self.component_health[key] = HealthStatus.UNHEALTHY

        # Failover if this was the active component
        if self.active_components.get(group_name) == component_idx:
            self.failover(group_name)

    def failover(self, group_name: str) -> bool:
        """Failover to next healthy component"""
        if group_name not in self.component_groups:
            return False

        components = self.component_groups[group_name]
        current = self.active_components.get(group_name, 0)

        # Find next healthy component
        for offset in range(1, len(components)):
            next_idx = (current + offset) % len(components)
            key = f"{group_name}:{next_idx}"

            if self.component_health.get(key) == HealthStatus.HEALTHY:
                self.active_components[group_name] = next_idx
                return True

        return False

    def get_availability(self, group_name: str) -> float:
        """Get group availability (ratio of healthy components)"""
        if group_name not in self.component_groups:
            return 0.0

        components = self.component_groups[group_name]
        healthy = sum(
            1 for i in range(len(components))
            if self.component_health.get(f"{group_name}:{i}") == HealthStatus.HEALTHY
        )

        return healthy / len(components)


class GracefulDegradation:
    """
    Graceful degradation of capabilities.
    """

    def __init__(self):
        # Capabilities and their priority
        self.capabilities: Dict[str, int] = {}  # name -> priority (higher = more important)

        # Capability requirements
        self.capability_requirements: Dict[str, float] = {}  # name -> resource requirement

        # Current resource level
        self.resource_level: float = 1.0  # 0.0 to 1.0

        # Disabled capabilities
        self.disabled: Set[str] = set()

    def register_capability(
        self,
        name: str,
        priority: int,
        resource_requirement: float
    ):
        """Register a capability"""
        self.capabilities[name] = priority
        self.capability_requirements[name] = resource_requirement

    def set_resource_level(self, level: float):
        """Set current resource level"""
        self.resource_level = max(0.0, min(1.0, level))
        self._update_capabilities()

    def _update_capabilities(self):
        """Update which capabilities are available"""
        self.disabled.clear()

        # Sort by priority (lowest first to disable first)
        sorted_caps = sorted(
            self.capabilities.items(),
            key=lambda x: x[1]
        )

        current_usage = 0.0

        for name, priority in sorted_caps:
            requirement = self.capability_requirements.get(name, 0.0)

            if current_usage + requirement <= self.resource_level:
                current_usage += requirement
            else:
                self.disabled.add(name)

    def is_available(self, capability: str) -> bool:
        """Check if capability is available"""
        return capability not in self.disabled

    def get_available_capabilities(self) -> List[str]:
        """Get list of available capabilities"""
        return [
            name for name in self.capabilities
            if name not in self.disabled
        ]

    def get_degradation_report(self) -> Dict[str, Any]:
        """Get degradation status report"""
        return {
            'resource_level': self.resource_level,
            'total_capabilities': len(self.capabilities),
            'available': len(self.capabilities) - len(self.disabled),
            'disabled': list(self.disabled),
            'degradation_percentage': len(self.disabled) / len(self.capabilities) * 100 if self.capabilities else 0
        }


# Export all
__all__ = [
    'HealthStatus',
    'HealthCheck',
    'RecoveryAction',
    'SelfHealingSystem',
    'RedundancyManager',
    'GracefulDegradation',
]
