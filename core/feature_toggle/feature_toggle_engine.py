"""
BAEL Feature Toggle Engine Implementation
==========================================

Feature flags with A/B testing, gradual rollouts, and targeting.

"Ba'el controls which features manifest in reality." — Ba'el
"""

import asyncio
import hashlib
import logging
import random
import threading
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger("BAEL.FeatureToggle")


# ============================================================================
# ENUMS
# ============================================================================

class FeatureState(Enum):
    """Feature flag states."""
    OFF = "off"
    ON = "on"
    GRADUAL = "gradual"      # Gradual rollout
    TARGETED = "targeted"    # Specific targets only
    SCHEDULED = "scheduled"  # Time-based
    EXPERIMENT = "experiment"  # A/B test


class RolloutStrategy(Enum):
    """Rollout strategies."""
    PERCENTAGE = "percentage"    # Random percentage
    HASH = "hash"                # Consistent hashing
    RING = "ring"                # Ring-based
    CANARY = "canary"            # Canary deployment
    BLUE_GREEN = "blue_green"    # Blue-green


class TargetType(Enum):
    """Target types for feature flags."""
    USER = "user"
    TENANT = "tenant"
    GROUP = "group"
    REGION = "region"
    DEVICE = "device"
    ENVIRONMENT = "environment"
    CUSTOM = "custom"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class RolloutConfig:
    """Configuration for gradual rollout."""
    strategy: RolloutStrategy = RolloutStrategy.PERCENTAGE
    percentage: float = 0.0  # 0-100

    # Hash-based rollout
    hash_attribute: str = "user_id"
    hash_seed: str = ""

    # Canary/ring rollout
    rings: List[str] = field(default_factory=list)
    current_ring: int = 0

    # Scheduling
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # Ramp-up
    ramp_steps: int = 0
    ramp_interval_hours: int = 24


@dataclass
class FeatureFlag:
    """
    Feature flag definition.
    """
    key: str
    name: str
    description: str = ""

    # State
    state: FeatureState = FeatureState.OFF
    default_value: Any = False

    # Variants (for A/B testing)
    variants: Dict[str, Any] = field(default_factory=dict)
    variant_weights: Dict[str, float] = field(default_factory=dict)

    # Targeting
    target_users: Set[str] = field(default_factory=set)
    target_tenants: Set[str] = field(default_factory=set)
    target_groups: Set[str] = field(default_factory=set)
    target_environments: Set[str] = field(default_factory=set)

    # Rollout
    rollout: Optional[RolloutConfig] = None

    # Metadata
    tags: List[str] = field(default_factory=list)
    owner: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if flag has expired."""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at


@dataclass
class UserContext:
    """Context for feature evaluation."""
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    groups: List[str] = field(default_factory=list)
    environment: str = "production"
    region: Optional[str] = None
    device: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get attribute value."""
        if hasattr(self, key):
            return getattr(self, key)
        return self.attributes.get(key, default)


@dataclass
class FeatureEvaluation:
    """Result of feature evaluation."""
    flag_key: str
    enabled: bool
    value: Any = None
    variant: Optional[str] = None
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # Debug info
    rule_matched: Optional[str] = None
    percentage_bucket: Optional[float] = None


# ============================================================================
# FEATURE TOGGLE ENGINE
# ============================================================================

class FeatureToggleEngine:
    """
    Feature toggle engine with advanced capabilities.

    Features:
    - Simple on/off flags
    - Gradual rollouts
    - A/B testing
    - User/tenant targeting
    - Scheduled releases
    - Consistent hashing

    "Ba'el toggles features across all dimensions." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        # Feature flags
        self._flags: Dict[str, FeatureFlag] = {}

        # Override cache
        self._overrides: Dict[str, Dict[str, Any]] = {}

        # Evaluation history
        self._history: List[FeatureEvaluation] = []
        self._history_enabled = False

        # Listeners
        self._listeners: List[Callable[[str, bool, UserContext], None]] = []

        self._lock = threading.RLock()

        logger.info("Feature Toggle Engine initialized")

    # ========================================================================
    # FLAG MANAGEMENT
    # ========================================================================

    def create_flag(
        self,
        key: str,
        name: str,
        state: FeatureState = FeatureState.OFF,
        **kwargs
    ) -> FeatureFlag:
        """Create a new feature flag."""
        with self._lock:
            flag = FeatureFlag(
                key=key,
                name=name,
                state=state,
                **kwargs
            )
            self._flags[key] = flag

        logger.debug(f"Created feature flag: {key}")
        return flag

    def get_flag(self, key: str) -> Optional[FeatureFlag]:
        """Get flag by key."""
        return self._flags.get(key)

    def update_flag(
        self,
        key: str,
        **updates
    ) -> Optional[FeatureFlag]:
        """Update a feature flag."""
        with self._lock:
            flag = self._flags.get(key)
            if not flag:
                return None

            for attr, value in updates.items():
                if hasattr(flag, attr):
                    setattr(flag, attr, value)

            flag.updated_at = datetime.now()

        return flag

    def delete_flag(self, key: str) -> bool:
        """Delete a feature flag."""
        with self._lock:
            if key in self._flags:
                del self._flags[key]
                return True
        return False

    def list_flags(
        self,
        tags: Optional[List[str]] = None,
        state: Optional[FeatureState] = None
    ) -> List[FeatureFlag]:
        """List all flags with optional filters."""
        flags = list(self._flags.values())

        if tags:
            flags = [f for f in flags if any(t in f.tags for t in tags)]

        if state:
            flags = [f for f in flags if f.state == state]

        return flags

    # ========================================================================
    # EVALUATION
    # ========================================================================

    def is_enabled(
        self,
        key: str,
        context: Optional[UserContext] = None,
        default: bool = False
    ) -> bool:
        """
        Check if feature is enabled.

        Args:
            key: Feature flag key
            context: User context for evaluation
            default: Default value if flag not found

        Returns:
            Whether feature is enabled
        """
        evaluation = self.evaluate(key, context)

        if evaluation:
            return evaluation.enabled
        return default

    def evaluate(
        self,
        key: str,
        context: Optional[UserContext] = None
    ) -> Optional[FeatureEvaluation]:
        """
        Evaluate a feature flag.

        Args:
            key: Feature flag key
            context: User context

        Returns:
            Evaluation result
        """
        context = context or UserContext()

        # Check for override
        override = self._get_override(key, context)
        if override is not None:
            return FeatureEvaluation(
                flag_key=key,
                enabled=bool(override),
                value=override,
                reason="override"
            )

        # Get flag
        flag = self._flags.get(key)
        if not flag:
            return None

        # Check expiration
        if flag.is_expired():
            return FeatureEvaluation(
                flag_key=key,
                enabled=False,
                value=flag.default_value,
                reason="expired"
            )

        # Evaluate based on state
        evaluation = self._evaluate_flag(flag, context)

        # Track history
        if self._history_enabled:
            self._history.append(evaluation)

        # Notify listeners
        for listener in self._listeners:
            try:
                listener(key, evaluation.enabled, context)
            except Exception as e:
                logger.error(f"Listener error: {e}")

        return evaluation

    def _evaluate_flag(
        self,
        flag: FeatureFlag,
        context: UserContext
    ) -> FeatureEvaluation:
        """Evaluate flag based on its state."""
        if flag.state == FeatureState.OFF:
            return FeatureEvaluation(
                flag_key=flag.key,
                enabled=False,
                value=flag.default_value,
                reason="flag_off"
            )

        if flag.state == FeatureState.ON:
            return FeatureEvaluation(
                flag_key=flag.key,
                enabled=True,
                value=True,
                reason="flag_on"
            )

        if flag.state == FeatureState.TARGETED:
            return self._evaluate_targeted(flag, context)

        if flag.state == FeatureState.GRADUAL:
            return self._evaluate_gradual(flag, context)

        if flag.state == FeatureState.SCHEDULED:
            return self._evaluate_scheduled(flag, context)

        if flag.state == FeatureState.EXPERIMENT:
            return self._evaluate_experiment(flag, context)

        return FeatureEvaluation(
            flag_key=flag.key,
            enabled=False,
            value=flag.default_value,
            reason="unknown_state"
        )

    def _evaluate_targeted(
        self,
        flag: FeatureFlag,
        context: UserContext
    ) -> FeatureEvaluation:
        """Evaluate targeted flag."""
        # Check user targeting
        if context.user_id and context.user_id in flag.target_users:
            return FeatureEvaluation(
                flag_key=flag.key,
                enabled=True,
                value=True,
                reason="user_targeted",
                rule_matched=f"user:{context.user_id}"
            )

        # Check tenant targeting
        if context.tenant_id and context.tenant_id in flag.target_tenants:
            return FeatureEvaluation(
                flag_key=flag.key,
                enabled=True,
                value=True,
                reason="tenant_targeted",
                rule_matched=f"tenant:{context.tenant_id}"
            )

        # Check group targeting
        for group in context.groups:
            if group in flag.target_groups:
                return FeatureEvaluation(
                    flag_key=flag.key,
                    enabled=True,
                    value=True,
                    reason="group_targeted",
                    rule_matched=f"group:{group}"
                )

        # Check environment targeting
        if context.environment in flag.target_environments:
            return FeatureEvaluation(
                flag_key=flag.key,
                enabled=True,
                value=True,
                reason="environment_targeted",
                rule_matched=f"env:{context.environment}"
            )

        return FeatureEvaluation(
            flag_key=flag.key,
            enabled=False,
            value=flag.default_value,
            reason="not_targeted"
        )

    def _evaluate_gradual(
        self,
        flag: FeatureFlag,
        context: UserContext
    ) -> FeatureEvaluation:
        """Evaluate gradual rollout."""
        if not flag.rollout:
            return FeatureEvaluation(
                flag_key=flag.key,
                enabled=False,
                value=flag.default_value,
                reason="no_rollout_config"
            )

        rollout = flag.rollout

        if rollout.strategy == RolloutStrategy.PERCENTAGE:
            # Random percentage
            bucket = random.random() * 100
            enabled = bucket < rollout.percentage

            return FeatureEvaluation(
                flag_key=flag.key,
                enabled=enabled,
                value=enabled,
                reason="percentage_rollout",
                percentage_bucket=bucket
            )

        if rollout.strategy == RolloutStrategy.HASH:
            # Consistent hash
            hash_value = context.get(rollout.hash_attribute, "")
            if not hash_value:
                return FeatureEvaluation(
                    flag_key=flag.key,
                    enabled=False,
                    value=flag.default_value,
                    reason="missing_hash_attribute"
                )

            bucket = self._calculate_hash_bucket(
                f"{flag.key}:{hash_value}:{rollout.hash_seed}"
            )
            enabled = bucket < rollout.percentage

            return FeatureEvaluation(
                flag_key=flag.key,
                enabled=enabled,
                value=enabled,
                reason="hash_rollout",
                percentage_bucket=bucket
            )

        return FeatureEvaluation(
            flag_key=flag.key,
            enabled=False,
            value=flag.default_value,
            reason="unknown_rollout_strategy"
        )

    def _evaluate_scheduled(
        self,
        flag: FeatureFlag,
        context: UserContext
    ) -> FeatureEvaluation:
        """Evaluate scheduled flag."""
        if not flag.rollout:
            return FeatureEvaluation(
                flag_key=flag.key,
                enabled=False,
                value=flag.default_value,
                reason="no_schedule"
            )

        now = datetime.now()

        start = flag.rollout.start_time
        end = flag.rollout.end_time

        if start and now < start:
            return FeatureEvaluation(
                flag_key=flag.key,
                enabled=False,
                value=flag.default_value,
                reason="before_start_time"
            )

        if end and now > end:
            return FeatureEvaluation(
                flag_key=flag.key,
                enabled=False,
                value=flag.default_value,
                reason="after_end_time"
            )

        return FeatureEvaluation(
            flag_key=flag.key,
            enabled=True,
            value=True,
            reason="within_schedule"
        )

    def _evaluate_experiment(
        self,
        flag: FeatureFlag,
        context: UserContext
    ) -> FeatureEvaluation:
        """Evaluate A/B test experiment."""
        if not flag.variants:
            return FeatureEvaluation(
                flag_key=flag.key,
                enabled=False,
                value=flag.default_value,
                reason="no_variants"
            )

        # Get consistent variant
        variant = self._select_variant(flag, context)
        value = flag.variants.get(variant, flag.default_value)

        return FeatureEvaluation(
            flag_key=flag.key,
            enabled=True,
            value=value,
            variant=variant,
            reason="experiment"
        )

    def _select_variant(
        self,
        flag: FeatureFlag,
        context: UserContext
    ) -> str:
        """Select variant for user."""
        # Use hash for consistent assignment
        hash_input = f"{flag.key}:{context.user_id or 'anonymous'}"
        bucket = self._calculate_hash_bucket(hash_input)

        # Select variant based on weights
        if flag.variant_weights:
            cumulative = 0.0
            for variant, weight in flag.variant_weights.items():
                cumulative += weight
                if bucket < cumulative:
                    return variant

        # Fall back to random selection
        variants = list(flag.variants.keys())
        if variants:
            index = int(bucket / 100 * len(variants))
            return variants[min(index, len(variants) - 1)]

        return "control"

    def _calculate_hash_bucket(self, value: str) -> float:
        """Calculate hash bucket (0-100)."""
        hash_bytes = hashlib.md5(value.encode()).digest()
        hash_int = int.from_bytes(hash_bytes[:4], 'big')
        return (hash_int / (2**32)) * 100

    # ========================================================================
    # OVERRIDES
    # ========================================================================

    def set_override(
        self,
        key: str,
        value: Any,
        user_id: Optional[str] = None
    ) -> None:
        """Set override for a flag."""
        with self._lock:
            if key not in self._overrides:
                self._overrides[key] = {}

            override_key = user_id or "__global__"
            self._overrides[key][override_key] = value

    def clear_override(
        self,
        key: str,
        user_id: Optional[str] = None
    ) -> None:
        """Clear override for a flag."""
        with self._lock:
            if key in self._overrides:
                override_key = user_id or "__global__"
                self._overrides[key].pop(override_key, None)

    def _get_override(
        self,
        key: str,
        context: UserContext
    ) -> Optional[Any]:
        """Get override value if exists."""
        overrides = self._overrides.get(key, {})

        # Check user-specific override
        if context.user_id and context.user_id in overrides:
            return overrides[context.user_id]

        # Check global override
        return overrides.get("__global__")

    # ========================================================================
    # CONVENIENCE
    # ========================================================================

    def get_variant(
        self,
        key: str,
        context: Optional[UserContext] = None
    ) -> Optional[str]:
        """Get variant for a feature."""
        evaluation = self.evaluate(key, context)
        return evaluation.variant if evaluation else None

    def enable_history(self, enabled: bool = True) -> None:
        """Enable evaluation history tracking."""
        self._history_enabled = enabled

    def get_history(self, key: Optional[str] = None) -> List[FeatureEvaluation]:
        """Get evaluation history."""
        if key:
            return [e for e in self._history if e.flag_key == key]
        return self._history.copy()

    def add_listener(
        self,
        listener: Callable[[str, bool, UserContext], None]
    ) -> None:
        """Add evaluation listener."""
        self._listeners.append(listener)

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        with self._lock:
            states = {}
            for state in FeatureState:
                states[state.value] = sum(
                    1 for f in self._flags.values()
                    if f.state == state
                )

        return {
            'total_flags': len(self._flags),
            'states': states,
            'overrides': sum(len(o) for o in self._overrides.values()),
            'history_size': len(self._history),
            'listeners': len(self._listeners)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

features = FeatureToggleEngine()


def is_enabled(key: str, context: Optional[UserContext] = None) -> bool:
    """Check if feature is enabled."""
    return features.is_enabled(key, context)


def get_variant(key: str, context: Optional[UserContext] = None) -> Optional[str]:
    """Get variant for feature."""
    return features.get_variant(key, context)
