"""
BAEL Feature Flags Engine
=========================

Feature flags and A/B testing with:
- Boolean flags
- Percentage rollouts
- User targeting
- A/B testing
- Analytics

"Ba'el controls which realities manifest." — Ba'el
"""

import asyncio
import logging
import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Set, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
import threading
import uuid
import random

logger = logging.getLogger("BAEL.FeatureFlags")


# ============================================================================
# ENUMS
# ============================================================================

class FlagType(Enum):
    """Flag types."""
    BOOLEAN = "boolean"
    STRING = "string"
    NUMBER = "number"
    JSON = "json"


class RolloutType(Enum):
    """Rollout strategies."""
    ALL = "all"                 # All users
    NONE = "none"               # No users
    PERCENTAGE = "percentage"   # Percentage of users
    GRADUAL = "gradual"         # Gradual rollout
    TARGETED = "targeted"       # Specific targets
    RING = "ring"               # Ring-based rollout


class TargetType(Enum):
    """Targeting types."""
    USER_ID = "user_id"
    EMAIL = "email"
    ATTRIBUTE = "attribute"
    SEGMENT = "segment"
    PERCENTAGE = "percentage"
    CUSTOM = "custom"


class VariantType(Enum):
    """Experiment variant types."""
    CONTROL = "control"
    TREATMENT = "treatment"
    VARIANT_A = "variant_a"
    VARIANT_B = "variant_b"
    VARIANT_C = "variant_c"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Target:
    """A targeting rule."""
    id: str
    target_type: TargetType

    # Value matchers
    values: List[str] = field(default_factory=list)

    # Attribute matching
    attribute: Optional[str] = None
    operator: str = "eq"  # eq, ne, gt, lt, gte, lte, contains, regex

    # Percentage
    percentage: float = 100.0

    # Custom function
    custom_fn: Optional[Callable[[Dict], bool]] = None

    def matches(self, context: Dict[str, Any]) -> bool:
        """Check if context matches target."""
        if self.target_type == TargetType.USER_ID:
            return context.get('user_id') in self.values

        elif self.target_type == TargetType.EMAIL:
            return context.get('email') in self.values

        elif self.target_type == TargetType.ATTRIBUTE:
            if not self.attribute:
                return False

            value = context.get(self.attribute)

            if self.operator == 'eq':
                return str(value) in self.values
            elif self.operator == 'ne':
                return str(value) not in self.values
            elif self.operator == 'contains':
                return any(v in str(value) for v in self.values)
            elif self.operator == 'gt':
                return float(value) > float(self.values[0]) if self.values else False
            elif self.operator == 'lt':
                return float(value) < float(self.values[0]) if self.values else False

        elif self.target_type == TargetType.PERCENTAGE:
            # Use consistent hashing for percentage
            user_id = context.get('user_id', str(uuid.uuid4()))
            hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16) % 100
            return hash_val < self.percentage

        elif self.target_type == TargetType.CUSTOM:
            if self.custom_fn:
                return self.custom_fn(context)

        return False


@dataclass
class Variant:
    """An experiment variant."""
    id: str
    name: str
    variant_type: VariantType

    # Value
    value: Any = None

    # Weight
    weight: float = 50.0

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Rollout:
    """A rollout strategy."""
    id: str
    rollout_type: RolloutType

    # Percentage (for PERCENTAGE type)
    percentage: float = 0.0

    # Gradual rollout
    start_percentage: float = 0.0
    end_percentage: float = 100.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # Rings (for RING type)
    rings: List[Dict[str, Any]] = field(default_factory=list)

    # Targets
    targets: List[Target] = field(default_factory=list)

    def get_current_percentage(self) -> float:
        """Get current rollout percentage."""
        if self.rollout_type == RolloutType.ALL:
            return 100.0

        elif self.rollout_type == RolloutType.NONE:
            return 0.0

        elif self.rollout_type == RolloutType.PERCENTAGE:
            return self.percentage

        elif self.rollout_type == RolloutType.GRADUAL:
            if not self.start_date or not self.end_date:
                return self.start_percentage

            now = datetime.now()

            if now < self.start_date:
                return self.start_percentage
            elif now > self.end_date:
                return self.end_percentage
            else:
                total_duration = (self.end_date - self.start_date).total_seconds()
                elapsed = (now - self.start_date).total_seconds()
                progress = elapsed / total_duration

                return self.start_percentage + (
                    self.end_percentage - self.start_percentage
                ) * progress

        return 0.0


@dataclass
class Flag:
    """A feature flag."""
    id: str
    key: str
    name: str

    # Type
    flag_type: FlagType = FlagType.BOOLEAN

    # Values
    enabled: bool = False
    default_value: Any = False

    # Variants
    variants: List[Variant] = field(default_factory=list)

    # Rollout
    rollout: Optional[Rollout] = None

    # Targets (whitelist/blacklist)
    whitelist: List[Target] = field(default_factory=list)
    blacklist: List[Target] = field(default_factory=list)

    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Environment
    environment: str = "default"


@dataclass
class Experiment:
    """An A/B experiment."""
    id: str
    key: str
    name: str

    # Flag
    flag_key: str

    # Variants
    control: Variant = field(default_factory=lambda: Variant(
        id=str(uuid.uuid4()),
        name="control",
        variant_type=VariantType.CONTROL,
        weight=50.0
    ))
    treatments: List[Variant] = field(default_factory=list)

    # Targeting
    targets: List[Target] = field(default_factory=list)
    traffic_percentage: float = 100.0

    # Status
    active: bool = False

    # Timestamps
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # Metrics
    primary_metric: Optional[str] = None
    secondary_metrics: List[str] = field(default_factory=list)


@dataclass
class FeatureFlagsConfig:
    """Feature flags configuration."""
    environment: str = "development"
    cache_ttl_seconds: int = 60
    analytics_enabled: bool = True
    default_enabled: bool = False


# ============================================================================
# TARGETING ENGINE
# ============================================================================

class TargetingEngine:
    """
    Evaluates targeting rules.
    """

    def __init__(self):
        """Initialize targeting engine."""
        self._segments: Dict[str, List[Target]] = {}

    def register_segment(self, name: str, targets: List[Target]) -> None:
        """Register a user segment."""
        self._segments[name] = targets

    def evaluate_target(self, target: Target, context: Dict[str, Any]) -> bool:
        """Evaluate a single target."""
        if target.target_type == TargetType.SEGMENT:
            segment_targets = self._segments.get(target.values[0] if target.values else '', [])
            return any(self.evaluate_target(t, context) for t in segment_targets)

        return target.matches(context)

    def evaluate_targets(
        self,
        targets: List[Target],
        context: Dict[str, Any],
        match_all: bool = False
    ) -> bool:
        """Evaluate multiple targets."""
        if not targets:
            return True

        if match_all:
            return all(self.evaluate_target(t, context) for t in targets)
        else:
            return any(self.evaluate_target(t, context) for t in targets)

    def get_hash_bucket(self, key: str, user_id: str, buckets: int = 100) -> int:
        """Get consistent hash bucket for user."""
        hash_input = f"{key}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        return hash_value % buckets


# ============================================================================
# FLAG EVALUATOR
# ============================================================================

class FlagEvaluator:
    """
    Evaluates feature flags.
    """

    def __init__(self, targeting: TargetingEngine, config: FeatureFlagsConfig):
        """Initialize evaluator."""
        self.targeting = targeting
        self.config = config

    def evaluate(
        self,
        flag: Flag,
        context: Dict[str, Any]
    ) -> Any:
        """Evaluate a flag for a context."""
        # Check if flag is enabled globally
        if not flag.enabled:
            return flag.default_value

        # Check blacklist
        if self.targeting.evaluate_targets(flag.blacklist, context):
            return flag.default_value

        # Check whitelist
        if flag.whitelist and self.targeting.evaluate_targets(flag.whitelist, context):
            return self._get_flag_value(flag, context)

        # Check rollout
        if flag.rollout:
            if self._check_rollout(flag, context):
                return self._get_flag_value(flag, context)
            return flag.default_value

        # Return enabled value
        return self._get_flag_value(flag, context)

    def _check_rollout(self, flag: Flag, context: Dict[str, Any]) -> bool:
        """Check if context is in rollout."""
        rollout = flag.rollout
        if not rollout:
            return True

        # Check targets first
        if rollout.targets:
            if not self.targeting.evaluate_targets(rollout.targets, context):
                return False

        # Get current percentage
        percentage = rollout.get_current_percentage()

        # Use consistent hashing
        user_id = context.get('user_id', str(uuid.uuid4()))
        bucket = self.targeting.get_hash_bucket(flag.key, user_id)

        return bucket < percentage

    def _get_flag_value(self, flag: Flag, context: Dict[str, Any]) -> Any:
        """Get the flag value."""
        if flag.flag_type == FlagType.BOOLEAN:
            return True

        if flag.variants:
            return self._select_variant(flag, context)

        return flag.default_value

    def _select_variant(self, flag: Flag, context: Dict[str, Any]) -> Any:
        """Select a variant for the user."""
        if not flag.variants:
            return flag.default_value

        user_id = context.get('user_id', str(uuid.uuid4()))
        bucket = self.targeting.get_hash_bucket(flag.key, user_id, 10000)

        # Calculate weight ranges
        total_weight = sum(v.weight for v in flag.variants)
        normalized_bucket = (bucket / 10000) * total_weight

        cumulative = 0.0
        for variant in flag.variants:
            cumulative += variant.weight
            if normalized_bucket < cumulative:
                return variant.value

        return flag.variants[-1].value if flag.variants else flag.default_value


# ============================================================================
# EXPERIMENT MANAGER
# ============================================================================

class ExperimentManager:
    """
    Manages A/B experiments.
    """

    def __init__(self, targeting: TargetingEngine):
        """Initialize experiment manager."""
        self.targeting = targeting
        self._experiments: Dict[str, Experiment] = {}
        self._assignments: Dict[str, Dict[str, str]] = defaultdict(dict)  # user -> experiment -> variant
        self._metrics: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))

    def register_experiment(self, experiment: Experiment) -> None:
        """Register an experiment."""
        self._experiments[experiment.key] = experiment

    def get_experiment(self, key: str) -> Optional[Experiment]:
        """Get an experiment."""
        return self._experiments.get(key)

    def get_variant(
        self,
        experiment_key: str,
        context: Dict[str, Any]
    ) -> Optional[Variant]:
        """Get variant for user in experiment."""
        experiment = self._experiments.get(experiment_key)
        if not experiment or not experiment.active:
            return None

        user_id = context.get('user_id')
        if not user_id:
            return None

        # Check cached assignment
        if experiment_key in self._assignments.get(user_id, {}):
            variant_id = self._assignments[user_id][experiment_key]
            all_variants = [experiment.control] + experiment.treatments
            for v in all_variants:
                if v.id == variant_id:
                    return v

        # Check targeting
        if experiment.targets:
            if not self.targeting.evaluate_targets(experiment.targets, context):
                return None

        # Check traffic allocation
        traffic_bucket = self.targeting.get_hash_bucket(
            f"{experiment_key}_traffic",
            user_id
        )
        if traffic_bucket >= experiment.traffic_percentage:
            return None

        # Assign variant
        variant = self._assign_variant(experiment, user_id)

        # Cache assignment
        self._assignments[user_id][experiment_key] = variant.id

        return variant

    def _assign_variant(self, experiment: Experiment, user_id: str) -> Variant:
        """Assign user to a variant."""
        all_variants = [experiment.control] + experiment.treatments
        total_weight = sum(v.weight for v in all_variants)

        bucket = self.targeting.get_hash_bucket(experiment.key, user_id, 10000)
        normalized = (bucket / 10000) * total_weight

        cumulative = 0.0
        for variant in all_variants:
            cumulative += variant.weight
            if normalized < cumulative:
                return variant

        return experiment.control

    def track_metric(
        self,
        experiment_key: str,
        variant_id: str,
        metric_name: str,
        value: float
    ) -> None:
        """Track a metric for experiment."""
        key = f"{experiment_key}:{variant_id}"
        self._metrics[key][metric_name].append(value)

    def get_results(self, experiment_key: str) -> Dict[str, Any]:
        """Get experiment results."""
        experiment = self._experiments.get(experiment_key)
        if not experiment:
            return {}

        results = {
            'experiment': experiment_key,
            'variants': {}
        }

        all_variants = [experiment.control] + experiment.treatments

        for variant in all_variants:
            key = f"{experiment_key}:{variant.id}"
            variant_metrics = self._metrics.get(key, {})

            variant_results = {
                'name': variant.name,
                'type': variant.variant_type.value,
                'metrics': {}
            }

            for metric_name, values in variant_metrics.items():
                if values:
                    variant_results['metrics'][metric_name] = {
                        'count': len(values),
                        'sum': sum(values),
                        'mean': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values)
                    }

            results['variants'][variant.id] = variant_results

        return results


# ============================================================================
# MAIN FEATURE FLAGS ENGINE
# ============================================================================

class FeatureFlagsEngine:
    """
    Main feature flags engine.

    Features:
    - Boolean and multivariate flags
    - Percentage rollouts
    - User targeting
    - A/B testing

    "Ba'el decides which features exist in each reality." — Ba'el
    """

    def __init__(self, config: Optional[FeatureFlagsConfig] = None):
        """Initialize feature flags engine."""
        self.config = config or FeatureFlagsConfig()

        # Components
        self.targeting = TargetingEngine()
        self.evaluator = FlagEvaluator(self.targeting, self.config)
        self.experiments = ExperimentManager(self.targeting)

        # Storage
        self._flags: Dict[str, Flag] = {}
        self._cache: Dict[str, Tuple[Any, datetime]] = {}

        # Analytics
        self._evaluations: Dict[str, int] = defaultdict(int)

        self._lock = threading.RLock()

        logger.info("FeatureFlagsEngine initialized")

    # ========================================================================
    # FLAG MANAGEMENT
    # ========================================================================

    def create_flag(
        self,
        key: str,
        name: str,
        flag_type: FlagType = FlagType.BOOLEAN,
        enabled: bool = False,
        default_value: Any = False,
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> Flag:
        """Create a feature flag."""
        flag = Flag(
            id=str(uuid.uuid4()),
            key=key,
            name=name,
            flag_type=flag_type,
            enabled=enabled,
            default_value=default_value,
            description=description,
            tags=tags or [],
            environment=self.config.environment
        )

        with self._lock:
            self._flags[key] = flag

        return flag

    def get_flag(self, key: str) -> Optional[Flag]:
        """Get a flag by key."""
        return self._flags.get(key)

    def update_flag(self, key: str, **updates) -> Optional[Flag]:
        """Update a flag."""
        with self._lock:
            flag = self._flags.get(key)
            if not flag:
                return None

            for attr, value in updates.items():
                if hasattr(flag, attr):
                    setattr(flag, attr, value)

            flag.updated_at = datetime.now()

            # Invalidate cache
            self._invalidate_cache(key)

            return flag

    def delete_flag(self, key: str) -> bool:
        """Delete a flag."""
        with self._lock:
            if key in self._flags:
                del self._flags[key]
                self._invalidate_cache(key)
                return True
            return False

    def list_flags(
        self,
        environment: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Flag]:
        """List flags with optional filters."""
        flags = list(self._flags.values())

        if environment:
            flags = [f for f in flags if f.environment == environment]

        if tags:
            flags = [f for f in flags if any(t in f.tags for t in tags)]

        return flags

    # ========================================================================
    # EVALUATION
    # ========================================================================

    def is_enabled(
        self,
        key: str,
        context: Optional[Dict[str, Any]] = None,
        default: bool = False
    ) -> bool:
        """Check if a flag is enabled."""
        value = self.evaluate(key, context)

        if value is None:
            return default

        return bool(value)

    def evaluate(
        self,
        key: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Evaluate a flag."""
        context = context or {}

        # Check cache
        cache_key = self._cache_key(key, context)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        flag = self._flags.get(key)
        if not flag:
            return self.config.default_enabled

        # Evaluate
        value = self.evaluator.evaluate(flag, context)

        # Cache result
        self._set_cached(cache_key, value)

        # Track evaluation
        if self.config.analytics_enabled:
            self._evaluations[key] += 1

        return value

    def evaluate_all(
        self,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Evaluate all flags."""
        context = context or {}
        results = {}

        for key in self._flags:
            results[key] = self.evaluate(key, context)

        return results

    # ========================================================================
    # ROLLOUTS
    # ========================================================================

    def set_rollout(
        self,
        key: str,
        rollout_type: RolloutType,
        percentage: float = 0.0,
        targets: Optional[List[Target]] = None
    ) -> Optional[Flag]:
        """Set rollout strategy for a flag."""
        flag = self._flags.get(key)
        if not flag:
            return None

        rollout = Rollout(
            id=str(uuid.uuid4()),
            rollout_type=rollout_type,
            percentage=percentage,
            targets=targets or []
        )

        flag.rollout = rollout
        flag.updated_at = datetime.now()

        self._invalidate_cache(key)

        return flag

    def set_gradual_rollout(
        self,
        key: str,
        start_percentage: float,
        end_percentage: float,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[Flag]:
        """Set gradual rollout for a flag."""
        flag = self._flags.get(key)
        if not flag:
            return None

        rollout = Rollout(
            id=str(uuid.uuid4()),
            rollout_type=RolloutType.GRADUAL,
            start_percentage=start_percentage,
            end_percentage=end_percentage,
            start_date=start_date,
            end_date=end_date
        )

        flag.rollout = rollout
        flag.updated_at = datetime.now()

        return flag

    # ========================================================================
    # TARGETING
    # ========================================================================

    def add_whitelist(
        self,
        key: str,
        target: Target
    ) -> Optional[Flag]:
        """Add to flag whitelist."""
        flag = self._flags.get(key)
        if not flag:
            return None

        flag.whitelist.append(target)
        flag.updated_at = datetime.now()

        self._invalidate_cache(key)

        return flag

    def add_blacklist(
        self,
        key: str,
        target: Target
    ) -> Optional[Flag]:
        """Add to flag blacklist."""
        flag = self._flags.get(key)
        if not flag:
            return None

        flag.blacklist.append(target)
        flag.updated_at = datetime.now()

        self._invalidate_cache(key)

        return flag

    def whitelist_users(
        self,
        key: str,
        user_ids: List[str]
    ) -> Optional[Flag]:
        """Whitelist specific users."""
        target = Target(
            id=str(uuid.uuid4()),
            target_type=TargetType.USER_ID,
            values=user_ids
        )
        return self.add_whitelist(key, target)

    def blacklist_users(
        self,
        key: str,
        user_ids: List[str]
    ) -> Optional[Flag]:
        """Blacklist specific users."""
        target = Target(
            id=str(uuid.uuid4()),
            target_type=TargetType.USER_ID,
            values=user_ids
        )
        return self.add_blacklist(key, target)

    # ========================================================================
    # EXPERIMENTS
    # ========================================================================

    def create_experiment(
        self,
        key: str,
        name: str,
        flag_key: str,
        treatments: List[Dict[str, Any]],
        control_value: Any = None,
        traffic_percentage: float = 100.0
    ) -> Experiment:
        """Create an A/B experiment."""
        # Create flag if it doesn't exist
        if flag_key not in self._flags:
            self.create_flag(flag_key, name, FlagType.JSON, enabled=True)

        # Create control variant
        control = Variant(
            id=str(uuid.uuid4()),
            name="control",
            variant_type=VariantType.CONTROL,
            value=control_value,
            weight=50.0
        )

        # Create treatment variants
        treatment_variants = []
        for i, t in enumerate(treatments):
            variant = Variant(
                id=str(uuid.uuid4()),
                name=t.get('name', f'treatment_{i}'),
                variant_type=VariantType.TREATMENT,
                value=t.get('value'),
                weight=t.get('weight', 50.0 / len(treatments))
            )
            treatment_variants.append(variant)

        experiment = Experiment(
            id=str(uuid.uuid4()),
            key=key,
            name=name,
            flag_key=flag_key,
            control=control,
            treatments=treatment_variants,
            traffic_percentage=traffic_percentage
        )

        self.experiments.register_experiment(experiment)

        return experiment

    def get_experiment_variant(
        self,
        experiment_key: str,
        context: Dict[str, Any]
    ) -> Optional[Variant]:
        """Get experiment variant for user."""
        return self.experiments.get_variant(experiment_key, context)

    def start_experiment(self, experiment_key: str) -> bool:
        """Start an experiment."""
        experiment = self.experiments.get_experiment(experiment_key)
        if experiment:
            experiment.active = True
            experiment.start_date = datetime.now()
            return True
        return False

    def stop_experiment(self, experiment_key: str) -> bool:
        """Stop an experiment."""
        experiment = self.experiments.get_experiment(experiment_key)
        if experiment:
            experiment.active = False
            experiment.end_date = datetime.now()
            return True
        return False

    def track_conversion(
        self,
        experiment_key: str,
        context: Dict[str, Any],
        metric_name: str = "conversion",
        value: float = 1.0
    ) -> None:
        """Track a conversion for an experiment."""
        variant = self.experiments.get_variant(experiment_key, context)
        if variant:
            self.experiments.track_metric(
                experiment_key,
                variant.id,
                metric_name,
                value
            )

    def get_experiment_results(self, experiment_key: str) -> Dict[str, Any]:
        """Get experiment results."""
        return self.experiments.get_results(experiment_key)

    # ========================================================================
    # CACHE
    # ========================================================================

    def _cache_key(self, key: str, context: Dict[str, Any]) -> str:
        """Generate cache key."""
        context_hash = hashlib.md5(
            json.dumps(context, sort_keys=True, default=str).encode()
        ).hexdigest()[:8]
        return f"{key}:{context_hash}"

    def _get_cached(self, cache_key: str) -> Optional[Any]:
        """Get cached value."""
        with self._lock:
            if cache_key in self._cache:
                value, timestamp = self._cache[cache_key]
                if (datetime.now() - timestamp).total_seconds() < self.config.cache_ttl_seconds:
                    return value
                del self._cache[cache_key]
        return None

    def _set_cached(self, cache_key: str, value: Any) -> None:
        """Set cached value."""
        with self._lock:
            self._cache[cache_key] = (value, datetime.now())

    def _invalidate_cache(self, key: str) -> None:
        """Invalidate cache for a flag."""
        with self._lock:
            to_delete = [k for k in self._cache if k.startswith(f"{key}:")]
            for k in to_delete:
                del self._cache[k]

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'total_flags': len(self._flags),
            'enabled_flags': sum(1 for f in self._flags.values() if f.enabled),
            'cache_size': len(self._cache),
            'total_evaluations': sum(self._evaluations.values()),
            'environment': self.config.environment
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

feature_flags_engine = FeatureFlagsEngine()
