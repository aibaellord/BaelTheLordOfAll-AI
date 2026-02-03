#!/usr/bin/env python3
"""
BAEL - Feature Toggle System
Comprehensive feature flag and toggle management.

Features:
- Feature flags management
- Percentage rollouts
- User/group targeting
- A/B testing
- Kill switches
- Scheduled toggles
- Dependency management
- Override system
- Analytics
- Audit trail
"""

import asyncio
import hashlib
import json
import logging
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, TypeVar, Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class FeatureState(Enum):
    """Feature states."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    CONDITIONAL = "conditional"
    PERCENTAGE = "percentage"
    SCHEDULED = "scheduled"


class TargetType(Enum):
    """Target types."""
    ALL = "all"
    USER = "user"
    GROUP = "group"
    PERCENTAGE = "percentage"
    ATTRIBUTE = "attribute"


class RolloutStrategy(Enum):
    """Rollout strategies."""
    ALL_USERS = "all_users"
    PERCENTAGE = "percentage"
    USER_LIST = "user_list"
    GROUP_LIST = "group_list"
    GRADUAL = "gradual"
    CANARY = "canary"


class VariantType(Enum):
    """Variant types for A/B testing."""
    CONTROL = "control"
    TREATMENT_A = "treatment_a"
    TREATMENT_B = "treatment_b"
    TREATMENT_C = "treatment_c"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class FeatureContext:
    """Context for feature evaluation."""
    user_id: str = ""
    group_id: str = ""
    session_id: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    environment: str = "production"

    def get_attribute(self, key: str, default: Any = None) -> Any:
        return self.attributes.get(key, default)


@dataclass
class TargetRule:
    """Targeting rule."""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    target_type: TargetType = TargetType.ALL
    target_values: List[str] = field(default_factory=list)
    attribute_key: str = ""
    attribute_operator: str = "eq"  # eq, ne, gt, lt, contains, in
    attribute_value: Any = None
    enabled: bool = True


@dataclass
class ScheduleWindow:
    """Schedule window for feature."""
    start_time: float = 0.0
    end_time: float = 0.0
    timezone: str = "UTC"
    days_of_week: List[int] = field(default_factory=list)  # 0=Mon, 6=Sun


@dataclass
class RolloutConfig:
    """Rollout configuration."""
    strategy: RolloutStrategy = RolloutStrategy.ALL_USERS
    percentage: int = 100
    user_ids: List[str] = field(default_factory=list)
    group_ids: List[str] = field(default_factory=list)
    gradual_steps: List[int] = field(default_factory=list)
    current_step: int = 0


@dataclass
class Variant:
    """A/B test variant."""
    name: str = ""
    weight: int = 50  # percentage weight
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Feature:
    """Feature definition."""
    feature_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    key: str = ""
    name: str = ""
    description: str = ""
    state: FeatureState = FeatureState.DISABLED
    default_value: bool = False

    # Targeting
    rules: List[TargetRule] = field(default_factory=list)

    # Rollout
    rollout: RolloutConfig = field(default_factory=RolloutConfig)

    # Schedule
    schedule: Optional[ScheduleWindow] = None

    # A/B Testing
    variants: List[Variant] = field(default_factory=list)

    # Dependencies
    dependencies: List[str] = field(default_factory=list)

    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    # Kill switch
    is_kill_switch: bool = False


@dataclass
class EvaluationResult:
    """Feature evaluation result."""
    feature_key: str = ""
    enabled: bool = False
    variant: Optional[str] = None
    reason: str = ""
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeatureEvent:
    """Feature evaluation event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    feature_key: str = ""
    user_id: str = ""
    enabled: bool = False
    variant: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class Override:
    """Feature override."""
    override_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    feature_key: str = ""
    target_type: str = "user"  # user, group, global
    target_id: str = ""
    value: bool = True
    expires_at: float = 0.0

    @property
    def is_expired(self) -> bool:
        if self.expires_at == 0.0:
            return False
        return time.time() > self.expires_at


# =============================================================================
# FEATURE STORE
# =============================================================================

class FeatureStore(ABC):
    """Abstract feature store."""

    @abstractmethod
    async def save(self, feature: Feature) -> bool:
        pass

    @abstractmethod
    async def get(self, key: str) -> Optional[Feature]:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def list_all(self) -> List[Feature]:
        pass


class InMemoryFeatureStore(FeatureStore):
    """In-memory feature store."""

    def __init__(self):
        self._features: Dict[str, Feature] = {}

    async def save(self, feature: Feature) -> bool:
        self._features[feature.key] = feature
        return True

    async def get(self, key: str) -> Optional[Feature]:
        return self._features.get(key)

    async def delete(self, key: str) -> bool:
        if key in self._features:
            del self._features[key]
            return True
        return False

    async def list_all(self) -> List[Feature]:
        return list(self._features.values())


# =============================================================================
# RULE EVALUATOR
# =============================================================================

class RuleEvaluator:
    """Evaluates targeting rules."""

    def evaluate(
        self,
        rule: TargetRule,
        context: FeatureContext
    ) -> bool:
        """Evaluate a single rule."""
        if not rule.enabled:
            return False

        if rule.target_type == TargetType.ALL:
            return True

        if rule.target_type == TargetType.USER:
            return context.user_id in rule.target_values

        if rule.target_type == TargetType.GROUP:
            return context.group_id in rule.target_values

        if rule.target_type == TargetType.ATTRIBUTE:
            return self._evaluate_attribute(rule, context)

        return False

    def _evaluate_attribute(
        self,
        rule: TargetRule,
        context: FeatureContext
    ) -> bool:
        """Evaluate attribute-based rule."""
        value = context.get_attribute(rule.attribute_key)

        if value is None:
            return False

        expected = rule.attribute_value
        operator = rule.attribute_operator

        if operator == "eq":
            return value == expected

        if operator == "ne":
            return value != expected

        if operator == "gt":
            return value > expected

        if operator == "lt":
            return value < expected

        if operator == "gte":
            return value >= expected

        if operator == "lte":
            return value <= expected

        if operator == "contains":
            return expected in str(value)

        if operator == "in":
            return value in expected

        if operator == "starts_with":
            return str(value).startswith(str(expected))

        if operator == "ends_with":
            return str(value).endswith(str(expected))

        return False


# =============================================================================
# PERCENTAGE CALCULATOR
# =============================================================================

class PercentageCalculator:
    """Calculates consistent percentage bucketing."""

    def __init__(self, salt: str = "bael_feature_salt"):
        self.salt = salt

    def get_bucket(self, feature_key: str, user_id: str) -> int:
        """Get bucket (0-99) for user."""
        key = f"{self.salt}:{feature_key}:{user_id}"
        hash_value = hashlib.md5(key.encode()).hexdigest()
        return int(hash_value[:8], 16) % 100

    def is_in_percentage(
        self,
        feature_key: str,
        user_id: str,
        percentage: int
    ) -> bool:
        """Check if user is in percentage."""
        if percentage >= 100:
            return True

        if percentage <= 0:
            return False

        bucket = self.get_bucket(feature_key, user_id)
        return bucket < percentage


# =============================================================================
# VARIANT SELECTOR
# =============================================================================

class VariantSelector:
    """Selects A/B test variants."""

    def __init__(self, salt: str = "bael_variant_salt"):
        self.salt = salt

    def select_variant(
        self,
        feature_key: str,
        user_id: str,
        variants: List[Variant]
    ) -> Optional[Variant]:
        """Select variant for user."""
        if not variants:
            return None

        # Get consistent bucket
        key = f"{self.salt}:{feature_key}:{user_id}"
        hash_value = hashlib.md5(key.encode()).hexdigest()
        bucket = int(hash_value[:8], 16) % 100

        # Find variant based on weights
        cumulative = 0

        for variant in variants:
            cumulative += variant.weight

            if bucket < cumulative:
                return variant

        # Fallback to first variant
        return variants[0]


# =============================================================================
# ANALYTICS TRACKER
# =============================================================================

class AnalyticsTracker:
    """Tracks feature usage analytics."""

    def __init__(self):
        self._events: List[FeatureEvent] = []
        self._stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

    def track(
        self,
        feature_key: str,
        user_id: str,
        enabled: bool,
        variant: Optional[str] = None
    ) -> None:
        """Track feature evaluation."""
        event = FeatureEvent(
            feature_key=feature_key,
            user_id=user_id,
            enabled=enabled,
            variant=variant
        )

        self._events.append(event)

        # Update stats
        self._stats[feature_key]["total"] += 1

        if enabled:
            self._stats[feature_key]["enabled"] += 1
        else:
            self._stats[feature_key]["disabled"] += 1

        if variant:
            self._stats[feature_key][f"variant_{variant}"] += 1

    def get_stats(self, feature_key: str) -> Dict[str, Any]:
        """Get stats for feature."""
        stats = self._stats.get(feature_key, {})

        total = stats.get("total", 0)
        enabled = stats.get("enabled", 0)

        return {
            "total_evaluations": total,
            "enabled_count": enabled,
            "disabled_count": stats.get("disabled", 0),
            "enabled_rate": enabled / total if total > 0 else 0.0,
            "variants": {
                k: v for k, v in stats.items()
                if k.startswith("variant_")
            }
        }

    def get_recent_events(
        self,
        feature_key: str = None,
        limit: int = 100
    ) -> List[FeatureEvent]:
        """Get recent events."""
        events = self._events

        if feature_key:
            events = [e for e in events if e.feature_key == feature_key]

        return events[-limit:]


# =============================================================================
# FEATURE TOGGLE MANAGER
# =============================================================================

class FeatureToggleManager:
    """
    Comprehensive Feature Toggle Manager for BAEL.
    """

    def __init__(self):
        self.store = InMemoryFeatureStore()
        self.rule_evaluator = RuleEvaluator()
        self.percentage_calc = PercentageCalculator()
        self.variant_selector = VariantSelector()
        self.analytics = AnalyticsTracker()
        self._overrides: Dict[str, List[Override]] = defaultdict(list)
        self._cache: Dict[str, Tuple[Feature, float]] = {}
        self._cache_ttl = 60  # seconds

    # -------------------------------------------------------------------------
    # FEATURE MANAGEMENT
    # -------------------------------------------------------------------------

    async def create_feature(
        self,
        key: str,
        name: str,
        description: str = "",
        state: FeatureState = FeatureState.DISABLED,
        default_value: bool = False,
        tags: List[str] = None
    ) -> Feature:
        """Create a new feature."""
        feature = Feature(
            key=key,
            name=name,
            description=description,
            state=state,
            default_value=default_value,
            tags=tags or []
        )

        await self.store.save(feature)

        return feature

    async def update_feature(
        self,
        key: str,
        **updates
    ) -> Optional[Feature]:
        """Update a feature."""
        feature = await self.store.get(key)

        if not feature:
            return None

        for attr, value in updates.items():
            if hasattr(feature, attr):
                setattr(feature, attr, value)

        feature.updated_at = time.time()

        await self.store.save(feature)

        # Invalidate cache
        if key in self._cache:
            del self._cache[key]

        return feature

    async def delete_feature(self, key: str) -> bool:
        """Delete a feature."""
        if key in self._cache:
            del self._cache[key]

        return await self.store.delete(key)

    async def get_feature(self, key: str) -> Optional[Feature]:
        """Get a feature."""
        # Check cache
        if key in self._cache:
            feature, cached_at = self._cache[key]

            if time.time() - cached_at < self._cache_ttl:
                return feature

        feature = await self.store.get(key)

        if feature:
            self._cache[key] = (feature, time.time())

        return feature

    async def list_features(
        self,
        tags: List[str] = None,
        state: FeatureState = None
    ) -> List[Feature]:
        """List all features."""
        features = await self.store.list_all()

        if tags:
            features = [
                f for f in features
                if any(t in f.tags for t in tags)
            ]

        if state:
            features = [f for f in features if f.state == state]

        return features

    # -------------------------------------------------------------------------
    # FEATURE EVALUATION
    # -------------------------------------------------------------------------

    async def is_enabled(
        self,
        key: str,
        context: FeatureContext = None
    ) -> bool:
        """Check if feature is enabled."""
        result = await self.evaluate(key, context)
        return result.enabled

    async def evaluate(
        self,
        key: str,
        context: FeatureContext = None
    ) -> EvaluationResult:
        """Evaluate feature for context."""
        context = context or FeatureContext()

        # Check overrides first
        override = self._get_override(key, context)

        if override:
            return EvaluationResult(
                feature_key=key,
                enabled=override.value,
                reason="override"
            )

        # Get feature
        feature = await self.get_feature(key)

        if not feature:
            return EvaluationResult(
                feature_key=key,
                enabled=False,
                reason="feature_not_found"
            )

        # Check kill switch
        if feature.is_kill_switch:
            result = EvaluationResult(
                feature_key=key,
                enabled=feature.state == FeatureState.ENABLED,
                reason="kill_switch"
            )

            self._track_evaluation(result, context)
            return result

        # Check dependencies
        if not await self._check_dependencies(feature, context):
            return EvaluationResult(
                feature_key=key,
                enabled=False,
                reason="dependency_not_met"
            )

        # Evaluate based on state
        result = await self._evaluate_by_state(feature, context)

        self._track_evaluation(result, context)

        return result

    async def _evaluate_by_state(
        self,
        feature: Feature,
        context: FeatureContext
    ) -> EvaluationResult:
        """Evaluate based on feature state."""
        if feature.state == FeatureState.ENABLED:
            return EvaluationResult(
                feature_key=feature.key,
                enabled=True,
                reason="enabled"
            )

        if feature.state == FeatureState.DISABLED:
            return EvaluationResult(
                feature_key=feature.key,
                enabled=False,
                reason="disabled"
            )

        if feature.state == FeatureState.CONDITIONAL:
            return self._evaluate_rules(feature, context)

        if feature.state == FeatureState.PERCENTAGE:
            return self._evaluate_percentage(feature, context)

        if feature.state == FeatureState.SCHEDULED:
            return self._evaluate_schedule(feature, context)

        return EvaluationResult(
            feature_key=feature.key,
            enabled=feature.default_value,
            reason="default"
        )

    def _evaluate_rules(
        self,
        feature: Feature,
        context: FeatureContext
    ) -> EvaluationResult:
        """Evaluate targeting rules."""
        for rule in feature.rules:
            if self.rule_evaluator.evaluate(rule, context):
                return EvaluationResult(
                    feature_key=feature.key,
                    enabled=True,
                    reason=f"rule_{rule.rule_id}"
                )

        return EvaluationResult(
            feature_key=feature.key,
            enabled=feature.default_value,
            reason="no_rule_matched"
        )

    def _evaluate_percentage(
        self,
        feature: Feature,
        context: FeatureContext
    ) -> EvaluationResult:
        """Evaluate percentage rollout."""
        if not context.user_id:
            return EvaluationResult(
                feature_key=feature.key,
                enabled=feature.default_value,
                reason="no_user_id"
            )

        rollout = feature.rollout

        # Check user/group lists
        if rollout.strategy == RolloutStrategy.USER_LIST:
            enabled = context.user_id in rollout.user_ids

            return EvaluationResult(
                feature_key=feature.key,
                enabled=enabled,
                reason="user_list"
            )

        if rollout.strategy == RolloutStrategy.GROUP_LIST:
            enabled = context.group_id in rollout.group_ids

            return EvaluationResult(
                feature_key=feature.key,
                enabled=enabled,
                reason="group_list"
            )

        # Percentage rollout
        enabled = self.percentage_calc.is_in_percentage(
            feature.key,
            context.user_id,
            rollout.percentage
        )

        return EvaluationResult(
            feature_key=feature.key,
            enabled=enabled,
            reason=f"percentage_{rollout.percentage}"
        )

    def _evaluate_schedule(
        self,
        feature: Feature,
        context: FeatureContext
    ) -> EvaluationResult:
        """Evaluate scheduled feature."""
        if not feature.schedule:
            return EvaluationResult(
                feature_key=feature.key,
                enabled=feature.default_value,
                reason="no_schedule"
            )

        now = time.time()
        schedule = feature.schedule

        # Check time window
        if schedule.start_time > 0 and now < schedule.start_time:
            return EvaluationResult(
                feature_key=feature.key,
                enabled=False,
                reason="before_schedule"
            )

        if schedule.end_time > 0 and now > schedule.end_time:
            return EvaluationResult(
                feature_key=feature.key,
                enabled=False,
                reason="after_schedule"
            )

        # Check day of week
        if schedule.days_of_week:
            current_day = datetime.now().weekday()

            if current_day not in schedule.days_of_week:
                return EvaluationResult(
                    feature_key=feature.key,
                    enabled=False,
                    reason="wrong_day"
                )

        return EvaluationResult(
            feature_key=feature.key,
            enabled=True,
            reason="in_schedule"
        )

    async def _check_dependencies(
        self,
        feature: Feature,
        context: FeatureContext
    ) -> bool:
        """Check feature dependencies."""
        for dep_key in feature.dependencies:
            dep_result = await self.evaluate(dep_key, context)

            if not dep_result.enabled:
                return False

        return True

    def _track_evaluation(
        self,
        result: EvaluationResult,
        context: FeatureContext
    ) -> None:
        """Track evaluation for analytics."""
        self.analytics.track(
            result.feature_key,
            context.user_id,
            result.enabled,
            result.variant
        )

    # -------------------------------------------------------------------------
    # A/B TESTING
    # -------------------------------------------------------------------------

    async def get_variant(
        self,
        key: str,
        context: FeatureContext = None
    ) -> Optional[Variant]:
        """Get variant for A/B test."""
        context = context or FeatureContext()

        feature = await self.get_feature(key)

        if not feature or not feature.variants:
            return None

        if not context.user_id:
            return feature.variants[0]

        return self.variant_selector.select_variant(
            key,
            context.user_id,
            feature.variants
        )

    async def add_variants(
        self,
        key: str,
        variants: List[Variant]
    ) -> Optional[Feature]:
        """Add variants to feature."""
        return await self.update_feature(key, variants=variants)

    # -------------------------------------------------------------------------
    # OVERRIDES
    # -------------------------------------------------------------------------

    def add_override(
        self,
        feature_key: str,
        target_type: str,
        target_id: str,
        value: bool,
        expires_in: int = 0
    ) -> Override:
        """Add feature override."""
        override = Override(
            feature_key=feature_key,
            target_type=target_type,
            target_id=target_id,
            value=value,
            expires_at=time.time() + expires_in if expires_in > 0 else 0.0
        )

        self._overrides[feature_key].append(override)

        return override

    def remove_override(
        self,
        feature_key: str,
        override_id: str
    ) -> bool:
        """Remove override."""
        overrides = self._overrides.get(feature_key, [])

        for i, override in enumerate(overrides):
            if override.override_id == override_id:
                del overrides[i]
                return True

        return False

    def _get_override(
        self,
        key: str,
        context: FeatureContext
    ) -> Optional[Override]:
        """Get applicable override."""
        overrides = self._overrides.get(key, [])

        for override in overrides:
            if override.is_expired:
                continue

            if override.target_type == "global":
                return override

            if override.target_type == "user":
                if override.target_id == context.user_id:
                    return override

            if override.target_type == "group":
                if override.target_id == context.group_id:
                    return override

        return None

    def get_overrides(self, feature_key: str) -> List[Override]:
        """Get all overrides for feature."""
        return [
            o for o in self._overrides.get(feature_key, [])
            if not o.is_expired
        ]

    # -------------------------------------------------------------------------
    # TARGETING RULES
    # -------------------------------------------------------------------------

    async def add_rule(
        self,
        key: str,
        target_type: TargetType,
        target_values: List[str] = None,
        attribute_key: str = "",
        attribute_operator: str = "eq",
        attribute_value: Any = None
    ) -> Optional[TargetRule]:
        """Add targeting rule."""
        feature = await self.get_feature(key)

        if not feature:
            return None

        rule = TargetRule(
            target_type=target_type,
            target_values=target_values or [],
            attribute_key=attribute_key,
            attribute_operator=attribute_operator,
            attribute_value=attribute_value
        )

        feature.rules.append(rule)
        await self.store.save(feature)

        # Invalidate cache
        if key in self._cache:
            del self._cache[key]

        return rule

    async def remove_rule(self, key: str, rule_id: str) -> bool:
        """Remove targeting rule."""
        feature = await self.get_feature(key)

        if not feature:
            return False

        for i, rule in enumerate(feature.rules):
            if rule.rule_id == rule_id:
                del feature.rules[i]
                await self.store.save(feature)

                if key in self._cache:
                    del self._cache[key]

                return True

        return False

    # -------------------------------------------------------------------------
    # ROLLOUT MANAGEMENT
    # -------------------------------------------------------------------------

    async def set_rollout_percentage(
        self,
        key: str,
        percentage: int
    ) -> Optional[Feature]:
        """Set rollout percentage."""
        feature = await self.get_feature(key)

        if not feature:
            return None

        feature.rollout.percentage = max(0, min(100, percentage))
        feature.rollout.strategy = RolloutStrategy.PERCENTAGE
        feature.state = FeatureState.PERCENTAGE

        await self.store.save(feature)

        if key in self._cache:
            del self._cache[key]

        return feature

    async def gradual_rollout(
        self,
        key: str,
        target_percentage: int,
        step_size: int = 10,
        step_delay: float = 0.0  # seconds
    ) -> None:
        """Gradually rollout feature."""
        feature = await self.get_feature(key)

        if not feature:
            return

        current = feature.rollout.percentage

        while current < target_percentage:
            current = min(current + step_size, target_percentage)
            await self.set_rollout_percentage(key, current)

            if step_delay > 0:
                await asyncio.sleep(step_delay)

    # -------------------------------------------------------------------------
    # KILL SWITCH
    # -------------------------------------------------------------------------

    async def create_kill_switch(
        self,
        key: str,
        name: str,
        enabled: bool = True
    ) -> Feature:
        """Create a kill switch feature."""
        feature = await self.create_feature(
            key=key,
            name=name,
            description="Kill switch",
            state=FeatureState.ENABLED if enabled else FeatureState.DISABLED
        )

        feature.is_kill_switch = True
        await self.store.save(feature)

        return feature

    async def toggle_kill_switch(
        self,
        key: str,
        enabled: bool
    ) -> Optional[Feature]:
        """Toggle kill switch."""
        feature = await self.get_feature(key)

        if not feature or not feature.is_kill_switch:
            return None

        feature.state = FeatureState.ENABLED if enabled else FeatureState.DISABLED
        await self.store.save(feature)

        if key in self._cache:
            del self._cache[key]

        return feature

    # -------------------------------------------------------------------------
    # SCHEDULING
    # -------------------------------------------------------------------------

    async def schedule_feature(
        self,
        key: str,
        start_time: float,
        end_time: float = 0.0,
        days_of_week: List[int] = None
    ) -> Optional[Feature]:
        """Schedule feature activation."""
        feature = await self.get_feature(key)

        if not feature:
            return None

        feature.schedule = ScheduleWindow(
            start_time=start_time,
            end_time=end_time,
            days_of_week=days_of_week or []
        )
        feature.state = FeatureState.SCHEDULED

        await self.store.save(feature)

        if key in self._cache:
            del self._cache[key]

        return feature

    # -------------------------------------------------------------------------
    # ANALYTICS
    # -------------------------------------------------------------------------

    def get_analytics(self, key: str) -> Dict[str, Any]:
        """Get feature analytics."""
        return self.analytics.get_stats(key)

    def get_recent_evaluations(
        self,
        key: str = None,
        limit: int = 100
    ) -> List[FeatureEvent]:
        """Get recent evaluations."""
        return self.analytics.get_recent_events(key, limit)


# =============================================================================
# FEATURE BUILDER
# =============================================================================

class FeatureBuilder:
    """Fluent builder for features."""

    def __init__(self, key: str, name: str):
        self._feature = Feature(key=key, name=name)

    def with_description(self, description: str) -> 'FeatureBuilder':
        self._feature.description = description
        return self

    def with_state(self, state: FeatureState) -> 'FeatureBuilder':
        self._feature.state = state
        return self

    def with_default(self, value: bool) -> 'FeatureBuilder':
        self._feature.default_value = value
        return self

    def with_percentage(self, percentage: int) -> 'FeatureBuilder':
        self._feature.state = FeatureState.PERCENTAGE
        self._feature.rollout.percentage = percentage
        self._feature.rollout.strategy = RolloutStrategy.PERCENTAGE
        return self

    def with_users(self, user_ids: List[str]) -> 'FeatureBuilder':
        self._feature.rollout.user_ids = user_ids
        self._feature.rollout.strategy = RolloutStrategy.USER_LIST
        return self

    def with_groups(self, group_ids: List[str]) -> 'FeatureBuilder':
        self._feature.rollout.group_ids = group_ids
        self._feature.rollout.strategy = RolloutStrategy.GROUP_LIST
        return self

    def with_variant(
        self,
        name: str,
        weight: int,
        payload: Dict[str, Any] = None
    ) -> 'FeatureBuilder':
        variant = Variant(name=name, weight=weight, payload=payload or {})
        self._feature.variants.append(variant)
        return self

    def with_tags(self, tags: List[str]) -> 'FeatureBuilder':
        self._feature.tags = tags
        return self

    def with_dependency(self, dep_key: str) -> 'FeatureBuilder':
        self._feature.dependencies.append(dep_key)
        return self

    def as_kill_switch(self) -> 'FeatureBuilder':
        self._feature.is_kill_switch = True
        return self

    def build(self) -> Feature:
        return self._feature


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Feature Toggle System."""
    print("=" * 70)
    print("BAEL - FEATURE TOGGLE SYSTEM DEMO")
    print("Comprehensive Feature Flag Management")
    print("=" * 70)
    print()

    manager = FeatureToggleManager()

    # 1. Create Basic Features
    print("1. CREATE BASIC FEATURES:")
    print("-" * 40)

    await manager.create_feature(
        key="dark_mode",
        name="Dark Mode",
        description="Enable dark mode UI",
        state=FeatureState.ENABLED,
        tags=["ui", "theme"]
    )
    print("   Created: dark_mode (enabled)")

    await manager.create_feature(
        key="new_checkout",
        name="New Checkout Flow",
        description="New checkout experience",
        state=FeatureState.DISABLED,
        tags=["checkout", "experimental"]
    )
    print("   Created: new_checkout (disabled)")
    print()

    # 2. Evaluate Features
    print("2. EVALUATE FEATURES:")
    print("-" * 40)

    context = FeatureContext(
        user_id="user_123",
        group_id="beta_testers"
    )

    result = await manager.evaluate("dark_mode", context)
    print(f"   dark_mode: {result.enabled} (reason: {result.reason})")

    result = await manager.evaluate("new_checkout", context)
    print(f"   new_checkout: {result.enabled} (reason: {result.reason})")
    print()

    # 3. Percentage Rollout
    print("3. PERCENTAGE ROLLOUT:")
    print("-" * 40)

    await manager.create_feature(
        key="new_algorithm",
        name="New Recommendation Algorithm",
        state=FeatureState.PERCENTAGE
    )
    await manager.set_rollout_percentage("new_algorithm", 30)

    print("   Created: new_algorithm (30% rollout)")

    # Test with different users
    enabled_count = 0

    for i in range(10):
        ctx = FeatureContext(user_id=f"user_{i}")
        result = await manager.evaluate("new_algorithm", ctx)

        if result.enabled:
            enabled_count += 1

    print(f"   Enabled for {enabled_count}/10 users")
    print()

    # 4. Targeting Rules
    print("4. TARGETING RULES:")
    print("-" * 40)

    await manager.create_feature(
        key="premium_feature",
        name="Premium Feature",
        state=FeatureState.CONDITIONAL
    )

    await manager.add_rule(
        "premium_feature",
        TargetType.ATTRIBUTE,
        attribute_key="subscription",
        attribute_operator="eq",
        attribute_value="premium"
    )

    print("   Created: premium_feature with subscription rule")

    # Test premium user
    premium_ctx = FeatureContext(
        user_id="user_456",
        attributes={"subscription": "premium"}
    )
    result = await manager.evaluate("premium_feature", premium_ctx)
    print(f"   Premium user: {result.enabled}")

    # Test free user
    free_ctx = FeatureContext(
        user_id="user_789",
        attributes={"subscription": "free"}
    )
    result = await manager.evaluate("premium_feature", free_ctx)
    print(f"   Free user: {result.enabled}")
    print()

    # 5. A/B Testing
    print("5. A/B TESTING:")
    print("-" * 40)

    feature = (
        FeatureBuilder("checkout_button", "Checkout Button Color")
        .with_state(FeatureState.ENABLED)
        .with_variant("control", 34, {"color": "blue"})
        .with_variant("treatment_a", 33, {"color": "green"})
        .with_variant("treatment_b", 33, {"color": "orange"})
        .build()
    )
    await manager.store.save(feature)

    print("   Created: checkout_button with 3 variants")

    # Get variants for users
    variant_counts = defaultdict(int)

    for i in range(9):
        ctx = FeatureContext(user_id=f"test_user_{i}")
        variant = await manager.get_variant("checkout_button", ctx)

        if variant:
            variant_counts[variant.name] += 1

    print("   Variant distribution (9 users):")

    for name, count in variant_counts.items():
        print(f"      {name}: {count}")
    print()

    # 6. Overrides
    print("6. OVERRIDES:")
    print("-" * 40)

    manager.add_override(
        "new_checkout",
        target_type="user",
        target_id="vip_user",
        value=True
    )

    print("   Added override for vip_user on new_checkout")

    vip_ctx = FeatureContext(user_id="vip_user")
    result = await manager.evaluate("new_checkout", vip_ctx)

    print(f"   VIP user can access new_checkout: {result.enabled}")
    print(f"   Reason: {result.reason}")
    print()

    # 7. Kill Switch
    print("7. KILL SWITCH:")
    print("-" * 40)

    await manager.create_kill_switch(
        "maintenance_mode",
        "Maintenance Mode",
        enabled=False
    )

    print("   Created: maintenance_mode kill switch (disabled)")

    result = await manager.evaluate("maintenance_mode")
    print(f"   Status: {result.enabled}")

    await manager.toggle_kill_switch("maintenance_mode", True)

    print("   Toggled: maintenance_mode ON")

    result = await manager.evaluate("maintenance_mode")
    print(f"   Status: {result.enabled}")
    print()

    # 8. Scheduled Features
    print("8. SCHEDULED FEATURES:")
    print("-" * 40)

    await manager.create_feature(
        key="holiday_banner",
        name="Holiday Banner",
        state=FeatureState.SCHEDULED
    )

    # Schedule for now
    now = time.time()
    await manager.schedule_feature(
        "holiday_banner",
        start_time=now - 3600,  # Started 1 hour ago
        end_time=now + 3600,  # Ends in 1 hour
        days_of_week=[0, 1, 2, 3, 4, 5, 6]
    )

    print("   Created: holiday_banner (scheduled)")

    result = await manager.evaluate("holiday_banner")
    print(f"   Status: {result.enabled} (reason: {result.reason})")
    print()

    # 9. Feature Dependencies
    print("9. FEATURE DEPENDENCIES:")
    print("-" * 40)

    feature = (
        FeatureBuilder("advanced_checkout", "Advanced Checkout")
        .with_state(FeatureState.ENABLED)
        .with_dependency("new_checkout")
        .build()
    )
    await manager.store.save(feature)

    print("   Created: advanced_checkout (depends on new_checkout)")

    # new_checkout is disabled, so advanced_checkout should be disabled
    result = await manager.evaluate("advanced_checkout")
    print(f"   Status: {result.enabled} (reason: {result.reason})")
    print()

    # 10. List Features
    print("10. LIST FEATURES:")
    print("-" * 40)

    features = await manager.list_features()

    print(f"   Total features: {len(features)}")

    for f in features:
        tags = ", ".join(f.tags) if f.tags else "none"
        print(f"      - {f.key}: {f.state.value} (tags: {tags})")
    print()

    # 11. Analytics
    print("11. ANALYTICS:")
    print("-" * 40)

    analytics = manager.get_analytics("new_algorithm")

    print(f"   Feature: new_algorithm")
    print(f"   Total evaluations: {analytics['total_evaluations']}")
    print(f"   Enabled rate: {analytics['enabled_rate']*100:.1f}%")
    print()

    # 12. Gradual Rollout
    print("12. GRADUAL ROLLOUT:")
    print("-" * 40)

    await manager.create_feature(
        key="gradual_feature",
        name="Gradual Feature",
        state=FeatureState.PERCENTAGE
    )
    await manager.set_rollout_percentage("gradual_feature", 0)

    print("   Starting gradual rollout: 0% -> 50%")
    await manager.gradual_rollout("gradual_feature", 50, step_size=10)

    feature = await manager.get_feature("gradual_feature")
    print(f"   Current percentage: {feature.rollout.percentage}%")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Feature Toggle System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
