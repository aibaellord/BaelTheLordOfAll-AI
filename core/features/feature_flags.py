#!/usr/bin/env python3
"""
BAEL - Feature Flag System
Comprehensive feature flag and toggle management.

This module provides a complete feature flag implementation
for dynamic feature control and A/B testing.

Features:
- Boolean and percentage-based flags
- User/group targeting
- Gradual rollouts
- A/B testing
- Flag scheduling
- Environment-based flags
- Flag dependencies
- Analytics and tracking
- Remote config
- Kill switches
"""

import asyncio
import hashlib
import json
import logging
import os
import random
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class FlagType(Enum):
    """Types of feature flags."""
    BOOLEAN = "boolean"
    PERCENTAGE = "percentage"
    VARIANT = "variant"
    JSON = "json"
    STRING = "string"
    NUMBER = "number"


class RolloutStrategy(Enum):
    """Rollout strategies."""
    ALL = "all"
    NONE = "none"
    PERCENTAGE = "percentage"
    USER_ID = "user_id"
    USER_GROUP = "user_group"
    GRADUAL = "gradual"
    SCHEDULED = "scheduled"
    RING = "ring"


class EvaluationReason(Enum):
    """Reason for flag evaluation result."""
    DEFAULT = "default"
    TARGETING_MATCH = "targeting_match"
    PERCENTAGE_MATCH = "percentage_match"
    SCHEDULE_MATCH = "schedule_match"
    KILL_SWITCH = "kill_switch"
    DEPENDENCY_FAILED = "dependency_failed"
    ERROR = "error"


class FlagStatus(Enum):
    """Flag status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    SCHEDULED = "scheduled"


class Environment(Enum):
    """Deployment environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class TargetingRule:
    """Targeting rule for flag evaluation."""
    id: str = ""
    attribute: str = ""
    operator: str = "equals"  # equals, contains, regex, in, gt, lt, gte, lte
    value: Any = None
    negate: bool = False

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate rule against context."""
        attr_value = context.get(self.attribute)

        if attr_value is None:
            return self.negate

        result = False

        if self.operator == "equals":
            result = attr_value == self.value
        elif self.operator == "not_equals":
            result = attr_value != self.value
        elif self.operator == "contains":
            result = self.value in str(attr_value)
        elif self.operator == "regex":
            result = bool(re.match(self.value, str(attr_value)))
        elif self.operator == "in":
            result = attr_value in self.value
        elif self.operator == "not_in":
            result = attr_value not in self.value
        elif self.operator == "gt":
            result = attr_value > self.value
        elif self.operator == "lt":
            result = attr_value < self.value
        elif self.operator == "gte":
            result = attr_value >= self.value
        elif self.operator == "lte":
            result = attr_value <= self.value
        elif self.operator == "exists":
            result = attr_value is not None
        elif self.operator == "starts_with":
            result = str(attr_value).startswith(str(self.value))
        elif self.operator == "ends_with":
            result = str(attr_value).endswith(str(self.value))

        return not result if self.negate else result


@dataclass
class Segment:
    """User segment for targeting."""
    id: str = ""
    name: str = ""
    rules: List[TargetingRule] = field(default_factory=list)
    match_type: str = "all"  # all, any

    def matches(self, context: Dict[str, Any]) -> bool:
        """Check if context matches segment."""
        if not self.rules:
            return False

        if self.match_type == "all":
            return all(rule.evaluate(context) for rule in self.rules)
        else:  # any
            return any(rule.evaluate(context) for rule in self.rules)


@dataclass
class Variant:
    """A/B test variant."""
    id: str = ""
    name: str = ""
    value: Any = None
    weight: float = 0.0  # 0-100
    description: str = ""


@dataclass
class Schedule:
    """Flag schedule."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    timezone: str = "UTC"
    days_of_week: List[int] = field(default_factory=list)  # 0=Monday

    def is_active(self, now: datetime = None) -> bool:
        """Check if schedule is currently active."""
        now = now or datetime.now()

        if self.start_time and now < self.start_time:
            return False

        if self.end_time and now > self.end_time:
            return False

        if self.days_of_week:
            if now.weekday() not in self.days_of_week:
                return False

        return True


@dataclass
class FlagConfig:
    """Feature flag configuration."""
    key: str
    name: str = ""
    description: str = ""
    flag_type: FlagType = FlagType.BOOLEAN

    # Values
    default_value: Any = False
    enabled_value: Any = True

    # Rollout
    rollout_strategy: RolloutStrategy = RolloutStrategy.ALL
    rollout_percentage: float = 100.0

    # Targeting
    targeting_rules: List[TargetingRule] = field(default_factory=list)
    segments: List[str] = field(default_factory=list)  # Segment IDs

    # Variants
    variants: List[Variant] = field(default_factory=list)

    # Schedule
    schedule: Optional[Schedule] = None

    # Dependencies
    dependencies: List[str] = field(default_factory=list)  # Other flag keys

    # Environments
    environments: List[Environment] = field(default_factory=lambda: [Environment.PRODUCTION])

    # Status
    status: FlagStatus = FlagStatus.ACTIVE
    kill_switch: bool = False

    # Metadata
    tags: List[str] = field(default_factory=list)
    owner: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class EvaluationResult:
    """Result of flag evaluation."""
    flag_key: str
    value: Any
    reason: EvaluationReason
    variant_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    evaluated_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None


@dataclass
class FlagEvent:
    """Analytics event for flag evaluation."""
    flag_key: str
    value: Any
    user_id: str
    context: Dict[str, Any]
    reason: EvaluationReason
    timestamp: datetime = field(default_factory=datetime.now)


# =============================================================================
# STORAGE
# =============================================================================

class FlagStorage(ABC):
    """Abstract flag storage."""

    @abstractmethod
    async def get_flag(self, key: str) -> Optional[FlagConfig]:
        """Get flag by key."""
        pass

    @abstractmethod
    async def get_all_flags(self) -> Dict[str, FlagConfig]:
        """Get all flags."""
        pass

    @abstractmethod
    async def save_flag(self, flag: FlagConfig) -> bool:
        """Save flag."""
        pass

    @abstractmethod
    async def delete_flag(self, key: str) -> bool:
        """Delete flag."""
        pass


class MemoryFlagStorage(FlagStorage):
    """In-memory flag storage."""

    def __init__(self):
        self.flags: Dict[str, FlagConfig] = {}

    async def get_flag(self, key: str) -> Optional[FlagConfig]:
        return self.flags.get(key)

    async def get_all_flags(self) -> Dict[str, FlagConfig]:
        return self.flags.copy()

    async def save_flag(self, flag: FlagConfig) -> bool:
        self.flags[flag.key] = flag
        return True

    async def delete_flag(self, key: str) -> bool:
        if key in self.flags:
            del self.flags[key]
            return True
        return False


class FileFlagStorage(FlagStorage):
    """File-based flag storage."""

    def __init__(self, directory: str):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _get_path(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    async def get_flag(self, key: str) -> Optional[FlagConfig]:
        path = self._get_path(key)
        if not path.exists():
            return None

        try:
            with open(path, 'r') as f:
                data = json.load(f)
            return self._from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load flag {key}: {e}")
            return None

    async def get_all_flags(self) -> Dict[str, FlagConfig]:
        flags = {}
        for path in self.directory.glob("*.json"):
            key = path.stem
            flag = await self.get_flag(key)
            if flag:
                flags[key] = flag
        return flags

    async def save_flag(self, flag: FlagConfig) -> bool:
        try:
            path = self._get_path(flag.key)
            with open(path, 'w') as f:
                json.dump(self._to_dict(flag), f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save flag {flag.key}: {e}")
            return False

    async def delete_flag(self, key: str) -> bool:
        path = self._get_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def _to_dict(self, flag: FlagConfig) -> Dict:
        return {
            "key": flag.key,
            "name": flag.name,
            "description": flag.description,
            "flag_type": flag.flag_type.value,
            "default_value": flag.default_value,
            "enabled_value": flag.enabled_value,
            "rollout_strategy": flag.rollout_strategy.value,
            "rollout_percentage": flag.rollout_percentage,
            "status": flag.status.value,
            "kill_switch": flag.kill_switch,
            "tags": flag.tags,
            "owner": flag.owner,
            "created_at": flag.created_at.isoformat(),
            "updated_at": flag.updated_at.isoformat()
        }

    def _from_dict(self, data: Dict) -> FlagConfig:
        return FlagConfig(
            key=data["key"],
            name=data.get("name", ""),
            description=data.get("description", ""),
            flag_type=FlagType(data.get("flag_type", "boolean")),
            default_value=data.get("default_value", False),
            enabled_value=data.get("enabled_value", True),
            rollout_strategy=RolloutStrategy(data.get("rollout_strategy", "all")),
            rollout_percentage=data.get("rollout_percentage", 100.0),
            status=FlagStatus(data.get("status", "active")),
            kill_switch=data.get("kill_switch", False),
            tags=data.get("tags", []),
            owner=data.get("owner", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now()
        )


# =============================================================================
# EVALUATOR
# =============================================================================

class FlagEvaluator:
    """Flag evaluation engine."""

    def __init__(self, storage: FlagStorage):
        self.storage = storage
        self.segments: Dict[str, Segment] = {}
        self.cache: Dict[str, Tuple[FlagConfig, datetime]] = {}
        self.cache_ttl = 60  # seconds

    def add_segment(self, segment: Segment) -> None:
        """Add a segment."""
        self.segments[segment.id] = segment

    async def evaluate(
        self,
        flag_key: str,
        context: Dict[str, Any] = None,
        default: Any = None
    ) -> EvaluationResult:
        """Evaluate a feature flag."""
        context = context or {}

        try:
            # Get flag
            flag = await self._get_flag_cached(flag_key)

            if not flag:
                return EvaluationResult(
                    flag_key=flag_key,
                    value=default,
                    reason=EvaluationReason.DEFAULT,
                    context=context,
                    error=f"Flag {flag_key} not found"
                )

            # Check status
            if flag.status != FlagStatus.ACTIVE:
                return EvaluationResult(
                    flag_key=flag_key,
                    value=flag.default_value,
                    reason=EvaluationReason.DEFAULT,
                    context=context
                )

            # Kill switch
            if flag.kill_switch:
                return EvaluationResult(
                    flag_key=flag_key,
                    value=flag.default_value,
                    reason=EvaluationReason.KILL_SWITCH,
                    context=context
                )

            # Check dependencies
            for dep_key in flag.dependencies:
                dep_result = await self.evaluate(dep_key, context)
                if not dep_result.value:
                    return EvaluationResult(
                        flag_key=flag_key,
                        value=flag.default_value,
                        reason=EvaluationReason.DEPENDENCY_FAILED,
                        context=context
                    )

            # Check schedule
            if flag.schedule and not flag.schedule.is_active():
                return EvaluationResult(
                    flag_key=flag_key,
                    value=flag.default_value,
                    reason=EvaluationReason.DEFAULT,
                    context=context
                )

            # Evaluate based on strategy
            return await self._evaluate_strategy(flag, context)

        except Exception as e:
            logger.error(f"Error evaluating flag {flag_key}: {e}")
            return EvaluationResult(
                flag_key=flag_key,
                value=default,
                reason=EvaluationReason.ERROR,
                context=context,
                error=str(e)
            )

    async def _get_flag_cached(self, key: str) -> Optional[FlagConfig]:
        """Get flag with caching."""
        if key in self.cache:
            flag, cached_at = self.cache[key]
            if (datetime.now() - cached_at).total_seconds() < self.cache_ttl:
                return flag

        flag = await self.storage.get_flag(key)
        if flag:
            self.cache[key] = (flag, datetime.now())

        return flag

    async def _evaluate_strategy(
        self,
        flag: FlagConfig,
        context: Dict[str, Any]
    ) -> EvaluationResult:
        """Evaluate based on rollout strategy."""

        # Check targeting rules
        if flag.targeting_rules:
            for rule in flag.targeting_rules:
                if rule.evaluate(context):
                    value = self._get_value(flag, context)
                    return EvaluationResult(
                        flag_key=flag.key,
                        value=value,
                        reason=EvaluationReason.TARGETING_MATCH,
                        context=context
                    )

        # Check segments
        if flag.segments:
            for segment_id in flag.segments:
                if segment_id in self.segments:
                    segment = self.segments[segment_id]
                    if segment.matches(context):
                        value = self._get_value(flag, context)
                        return EvaluationResult(
                            flag_key=flag.key,
                            value=value,
                            reason=EvaluationReason.TARGETING_MATCH,
                            context=context
                        )

        # Apply rollout strategy
        if flag.rollout_strategy == RolloutStrategy.ALL:
            return EvaluationResult(
                flag_key=flag.key,
                value=self._get_value(flag, context),
                reason=EvaluationReason.PERCENTAGE_MATCH,
                context=context
            )

        elif flag.rollout_strategy == RolloutStrategy.NONE:
            return EvaluationResult(
                flag_key=flag.key,
                value=flag.default_value,
                reason=EvaluationReason.DEFAULT,
                context=context
            )

        elif flag.rollout_strategy == RolloutStrategy.PERCENTAGE:
            if self._in_percentage(flag.key, context, flag.rollout_percentage):
                return EvaluationResult(
                    flag_key=flag.key,
                    value=self._get_value(flag, context),
                    reason=EvaluationReason.PERCENTAGE_MATCH,
                    context=context
                )

        elif flag.rollout_strategy == RolloutStrategy.SCHEDULED:
            if flag.schedule and flag.schedule.is_active():
                return EvaluationResult(
                    flag_key=flag.key,
                    value=self._get_value(flag, context),
                    reason=EvaluationReason.SCHEDULE_MATCH,
                    context=context
                )

        return EvaluationResult(
            flag_key=flag.key,
            value=flag.default_value,
            reason=EvaluationReason.DEFAULT,
            context=context
        )

    def _get_value(self, flag: FlagConfig, context: Dict[str, Any]) -> Any:
        """Get flag value (with variant selection if applicable)."""
        if flag.variants:
            return self._select_variant(flag, context)
        return flag.enabled_value

    def _select_variant(self, flag: FlagConfig, context: Dict[str, Any]) -> Any:
        """Select variant based on user."""
        user_id = context.get("user_id", str(random.random()))

        # Consistent hashing
        hash_input = f"{flag.key}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        bucket = (hash_value % 10000) / 100.0  # 0-100

        cumulative = 0.0
        for variant in flag.variants:
            cumulative += variant.weight
            if bucket < cumulative:
                return variant.value

        # Fallback to last variant
        return flag.variants[-1].value if flag.variants else flag.enabled_value

    def _in_percentage(
        self,
        flag_key: str,
        context: Dict[str, Any],
        percentage: float
    ) -> bool:
        """Check if user is in percentage bucket."""
        user_id = context.get("user_id", str(random.random()))

        hash_input = f"{flag_key}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        bucket = (hash_value % 10000) / 100.0  # 0-100

        return bucket < percentage


# =============================================================================
# FEATURE FLAG MANAGER
# =============================================================================

class FeatureFlagManager:
    """
    Master feature flag management for BAEL.

    Provides complete feature flag functionality including
    A/B testing, gradual rollouts, and targeting.
    """

    def __init__(self, storage: FlagStorage = None):
        self.storage = storage or MemoryFlagStorage()
        self.evaluator = FlagEvaluator(self.storage)
        self.events: List[FlagEvent] = []
        self.max_events = 10000

        # Current environment
        self.environment = Environment.PRODUCTION

        # Override cache
        self.overrides: Dict[str, Any] = {}

    # Flag management
    async def create_flag(
        self,
        key: str,
        name: str = "",
        description: str = "",
        flag_type: FlagType = FlagType.BOOLEAN,
        default_value: Any = False,
        enabled_value: Any = True,
        **kwargs
    ) -> FlagConfig:
        """Create a new flag."""
        flag = FlagConfig(
            key=key,
            name=name or key,
            description=description,
            flag_type=flag_type,
            default_value=default_value,
            enabled_value=enabled_value,
            **kwargs
        )

        await self.storage.save_flag(flag)
        return flag

    async def get_flag(self, key: str) -> Optional[FlagConfig]:
        """Get a flag configuration."""
        return await self.storage.get_flag(key)

    async def update_flag(self, key: str, **updates) -> Optional[FlagConfig]:
        """Update a flag."""
        flag = await self.storage.get_flag(key)
        if not flag:
            return None

        for attr, value in updates.items():
            if hasattr(flag, attr):
                setattr(flag, attr, value)

        flag.updated_at = datetime.now()
        await self.storage.save_flag(flag)
        return flag

    async def delete_flag(self, key: str) -> bool:
        """Delete a flag."""
        return await self.storage.delete_flag(key)

    async def list_flags(
        self,
        status: FlagStatus = None,
        tags: List[str] = None
    ) -> List[FlagConfig]:
        """List flags with optional filtering."""
        flags = await self.storage.get_all_flags()
        result = list(flags.values())

        if status:
            result = [f for f in result if f.status == status]

        if tags:
            result = [f for f in result if any(t in f.tags for t in tags)]

        return result

    # Evaluation
    async def is_enabled(
        self,
        key: str,
        context: Dict[str, Any] = None,
        default: bool = False
    ) -> bool:
        """Check if flag is enabled."""
        # Check overrides first
        if key in self.overrides:
            return bool(self.overrides[key])

        result = await self.evaluator.evaluate(key, context, default)
        self._track_event(result, context)
        return bool(result.value)

    async def get_value(
        self,
        key: str,
        context: Dict[str, Any] = None,
        default: Any = None
    ) -> Any:
        """Get flag value."""
        if key in self.overrides:
            return self.overrides[key]

        result = await self.evaluator.evaluate(key, context, default)
        self._track_event(result, context)
        return result.value

    async def get_variant(
        self,
        key: str,
        context: Dict[str, Any] = None,
        default: str = None
    ) -> Optional[str]:
        """Get variant for A/B test."""
        result = await self.evaluator.evaluate(key, context, default)
        self._track_event(result, context)
        return result.variant_id

    async def evaluate(
        self,
        key: str,
        context: Dict[str, Any] = None
    ) -> EvaluationResult:
        """Get full evaluation result."""
        result = await self.evaluator.evaluate(key, context)
        self._track_event(result, context)
        return result

    # Segments
    def create_segment(
        self,
        segment_id: str,
        name: str,
        rules: List[TargetingRule],
        match_type: str = "all"
    ) -> Segment:
        """Create a user segment."""
        segment = Segment(
            id=segment_id,
            name=name,
            rules=rules,
            match_type=match_type
        )
        self.evaluator.add_segment(segment)
        return segment

    # Overrides
    def set_override(self, key: str, value: Any) -> None:
        """Set local override for a flag."""
        self.overrides[key] = value

    def clear_override(self, key: str) -> None:
        """Clear local override."""
        self.overrides.pop(key, None)

    def clear_all_overrides(self) -> None:
        """Clear all overrides."""
        self.overrides.clear()

    # Kill switch
    async def enable_kill_switch(self, key: str) -> bool:
        """Enable kill switch for a flag."""
        flag = await self.update_flag(key, kill_switch=True)
        return flag is not None

    async def disable_kill_switch(self, key: str) -> bool:
        """Disable kill switch for a flag."""
        flag = await self.update_flag(key, kill_switch=False)
        return flag is not None

    # Rollout management
    async def set_rollout_percentage(self, key: str, percentage: float) -> bool:
        """Set rollout percentage."""
        flag = await self.update_flag(
            key,
            rollout_strategy=RolloutStrategy.PERCENTAGE,
            rollout_percentage=max(0, min(100, percentage))
        )
        return flag is not None

    async def gradual_rollout(
        self,
        key: str,
        start_percentage: float,
        end_percentage: float,
        duration_hours: float,
        step_hours: float = 1.0
    ) -> None:
        """Perform gradual rollout."""
        steps = int(duration_hours / step_hours)
        increment = (end_percentage - start_percentage) / steps

        current = start_percentage

        for _ in range(steps):
            await self.set_rollout_percentage(key, current)
            current += increment
            await asyncio.sleep(step_hours * 3600)

        await self.set_rollout_percentage(key, end_percentage)

    # Analytics
    def _track_event(
        self,
        result: EvaluationResult,
        context: Dict[str, Any] = None
    ) -> None:
        """Track evaluation event."""
        context = context or {}

        event = FlagEvent(
            flag_key=result.flag_key,
            value=result.value,
            user_id=context.get("user_id", "anonymous"),
            context=context,
            reason=result.reason
        )

        self.events.append(event)

        # Trim events if too many
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

    def get_flag_stats(self, key: str) -> Dict[str, Any]:
        """Get statistics for a flag."""
        flag_events = [e for e in self.events if e.flag_key == key]

        if not flag_events:
            return {"evaluations": 0}

        true_count = sum(1 for e in flag_events if e.value)
        false_count = len(flag_events) - true_count

        reasons = {}
        for e in flag_events:
            reasons[e.reason.value] = reasons.get(e.reason.value, 0) + 1

        return {
            "evaluations": len(flag_events),
            "true_count": true_count,
            "false_count": false_count,
            "true_percentage": (true_count / len(flag_events)) * 100,
            "reasons": reasons
        }

    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all flags."""
        flag_keys = set(e.flag_key for e in self.events)
        return {key: self.get_flag_stats(key) for key in flag_keys}

    # Batch operations
    async def evaluate_all(
        self,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Evaluate all flags."""
        flags = await self.storage.get_all_flags()
        results = {}

        for key in flags:
            result = await self.evaluate(key, context)
            results[key] = result.value

        return results


# =============================================================================
# DECORATOR
# =============================================================================

def feature_flag(
    key: str,
    default: Any = False,
    manager: FeatureFlagManager = None
):
    """Decorator for feature flag controlled functions."""
    def decorator(func: Callable):
        async def async_wrapper(*args, **kwargs):
            nonlocal manager
            if manager is None:
                manager = FeatureFlagManager()

            context = kwargs.pop("flag_context", {})
            enabled = await manager.is_enabled(key, context, default)

            if enabled:
                return await func(*args, **kwargs)
            return None

        def sync_wrapper(*args, **kwargs):
            nonlocal manager
            if manager is None:
                manager = FeatureFlagManager()

            context = kwargs.pop("flag_context", {})

            # Run async evaluation
            loop = asyncio.new_event_loop()
            try:
                enabled = loop.run_until_complete(
                    manager.is_enabled(key, context, default)
                )
            finally:
                loop.close()

            if enabled:
                return func(*args, **kwargs)
            return None

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Feature Flag System."""
    print("=" * 70)
    print("BAEL - FEATURE FLAG SYSTEM DEMO")
    print("Feature Toggles and A/B Testing")
    print("=" * 70)
    print()

    manager = FeatureFlagManager()

    # 1. Boolean Flag
    print("1. BOOLEAN FLAG:")
    print("-" * 40)

    await manager.create_flag(
        key="dark_mode",
        name="Dark Mode",
        description="Enable dark mode UI",
        default_value=False,
        enabled_value=True
    )

    enabled = await manager.is_enabled("dark_mode")
    print(f"   dark_mode enabled: {enabled}")
    print()

    # 2. Percentage Rollout
    print("2. PERCENTAGE ROLLOUT:")
    print("-" * 40)

    await manager.create_flag(
        key="new_feature",
        rollout_strategy=RolloutStrategy.PERCENTAGE,
        rollout_percentage=50.0
    )

    # Simulate multiple users
    enabled_count = 0
    for i in range(100):
        context = {"user_id": f"user_{i}"}
        if await manager.is_enabled("new_feature", context):
            enabled_count += 1

    print(f"   new_feature enabled for {enabled_count}/100 users")
    print()

    # 3. Targeting Rules
    print("3. TARGETING RULES:")
    print("-" * 40)

    await manager.create_flag(
        key="beta_feature",
        targeting_rules=[
            TargetingRule(
                attribute="subscription",
                operator="equals",
                value="premium"
            )
        ]
    )

    free_user = await manager.is_enabled("beta_feature", {"subscription": "free"})
    premium_user = await manager.is_enabled("beta_feature", {"subscription": "premium"})

    print(f"   Free user: {free_user}")
    print(f"   Premium user: {premium_user}")
    print()

    # 4. Segments
    print("4. USER SEGMENTS:")
    print("-" * 40)

    manager.create_segment(
        "early_adopters",
        "Early Adopters",
        [
            TargetingRule(attribute="signup_date", operator="lt", value="2024-01-01"),
            TargetingRule(attribute="active", operator="equals", value=True)
        ]
    )

    await manager.create_flag(
        key="experimental_feature",
        segments=["early_adopters"]
    )

    early_adopter = await manager.is_enabled(
        "experimental_feature",
        {"signup_date": "2023-06-15", "active": True}
    )
    new_user = await manager.is_enabled(
        "experimental_feature",
        {"signup_date": "2024-03-01", "active": True}
    )

    print(f"   Early adopter: {early_adopter}")
    print(f"   New user: {new_user}")
    print()

    # 5. A/B Testing Variants
    print("5. A/B TESTING:")
    print("-" * 40)

    await manager.create_flag(
        key="checkout_button_color",
        flag_type=FlagType.VARIANT,
        variants=[
            Variant(id="control", name="Control", value="blue", weight=50),
            Variant(id="variant_a", name="Variant A", value="green", weight=25),
            Variant(id="variant_b", name="Variant B", value="red", weight=25)
        ]
    )

    variant_counts = {"blue": 0, "green": 0, "red": 0}
    for i in range(100):
        color = await manager.get_value(
            "checkout_button_color",
            {"user_id": f"user_{i}"}
        )
        variant_counts[color] = variant_counts.get(color, 0) + 1

    print(f"   Variant distribution: {variant_counts}")
    print()

    # 6. Kill Switch
    print("6. KILL SWITCH:")
    print("-" * 40)

    await manager.create_flag(key="risky_feature")

    before = await manager.is_enabled("risky_feature")
    print(f"   Before kill switch: {before}")

    await manager.enable_kill_switch("risky_feature")
    after = await manager.is_enabled("risky_feature")
    print(f"   After kill switch: {after}")

    await manager.disable_kill_switch("risky_feature")
    print()

    # 7. Overrides
    print("7. LOCAL OVERRIDES:")
    print("-" * 40)

    original = await manager.is_enabled("dark_mode")
    print(f"   Original value: {original}")

    manager.set_override("dark_mode", True)
    overridden = await manager.is_enabled("dark_mode")
    print(f"   With override: {overridden}")

    manager.clear_override("dark_mode")
    print()

    # 8. Evaluation Details
    print("8. EVALUATION DETAILS:")
    print("-" * 40)

    result = await manager.evaluate(
        "beta_feature",
        {"subscription": "premium", "user_id": "123"}
    )
    print(f"   Flag: {result.flag_key}")
    print(f"   Value: {result.value}")
    print(f"   Reason: {result.reason.value}")
    print()

    # 9. Statistics
    print("9. FLAG STATISTICS:")
    print("-" * 40)

    stats = manager.get_flag_stats("new_feature")
    print(f"   new_feature stats:")
    for key, value in stats.items():
        print(f"      {key}: {value}")
    print()

    # 10. Batch Evaluation
    print("10. BATCH EVALUATION:")
    print("-" * 40)

    all_values = await manager.evaluate_all({"user_id": "test_user"})
    for key, value in list(all_values.items())[:5]:
        print(f"    {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Feature Flag System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
