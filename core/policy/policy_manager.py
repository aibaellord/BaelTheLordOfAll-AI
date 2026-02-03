#!/usr/bin/env python3
"""
BAEL - Policy Manager
Advanced policy management for AI agent governance.

Features:
- Policy definition
- Policy evaluation
- Policy composition
- Access control
- Permission management
- Constraint enforcement
- Policy inheritance
- Policy versioning
"""

import asyncio
import copy
import hashlib
import math
import random
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class PolicyType(Enum):
    """Policy types."""
    ALLOW = "allow"
    DENY = "deny"
    CONDITIONAL = "conditional"
    REQUIRE = "require"


class PolicyStatus(Enum):
    """Policy status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    DRAFT = "draft"


class EvaluationResult(Enum):
    """Policy evaluation result."""
    ALLOW = "allow"
    DENY = "deny"
    NOT_APPLICABLE = "not_applicable"
    INDETERMINATE = "indeterminate"


class CombiningAlgorithm(Enum):
    """Policy combining algorithms."""
    DENY_OVERRIDES = "deny_overrides"
    PERMIT_OVERRIDES = "permit_overrides"
    FIRST_APPLICABLE = "first_applicable"
    ONLY_ONE_APPLICABLE = "only_one_applicable"


class PermissionLevel(Enum):
    """Permission levels."""
    NONE = 0
    READ = 1
    WRITE = 2
    EXECUTE = 3
    ADMIN = 4
    OWNER = 5


class ConstraintType(Enum):
    """Constraint types."""
    TIME = "time"
    LOCATION = "location"
    RATE = "rate"
    RESOURCE = "resource"
    CONDITION = "condition"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Subject:
    """Policy subject."""
    subject_id: str = ""
    name: str = ""
    roles: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Resource:
    """Policy resource."""
    resource_id: str = ""
    name: str = ""
    resource_type: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Action:
    """Policy action."""
    action_id: str = ""
    name: str = ""
    action_type: str = ""


@dataclass
class Condition:
    """Policy condition."""
    condition_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    expression: str = ""
    evaluator: Optional[Callable[[Dict[str, Any]], bool]] = None


@dataclass
class Constraint:
    """Policy constraint."""
    constraint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    constraint_type: ConstraintType = ConstraintType.CONDITION
    name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class PolicyRule:
    """Policy rule."""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    effect: PolicyType = PolicyType.ALLOW
    subjects: List[str] = field(default_factory=list)  # Subject patterns
    resources: List[str] = field(default_factory=list)  # Resource patterns
    actions: List[str] = field(default_factory=list)  # Action patterns
    conditions: List[Condition] = field(default_factory=list)
    priority: int = 0


@dataclass
class Policy:
    """Policy definition."""
    policy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    status: PolicyStatus = PolicyStatus.ACTIVE
    rules: List[PolicyRule] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    parent_id: Optional[str] = None
    combining: CombiningAlgorithm = CombiningAlgorithm.DENY_OVERRIDES
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Permission:
    """Permission definition."""
    permission_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    level: PermissionLevel = PermissionLevel.READ
    resource_pattern: str = "*"
    action_pattern: str = "*"
    granted_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None


@dataclass
class AccessRequest:
    """Access request."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    subject: Subject = field(default_factory=Subject)
    resource: Resource = field(default_factory=Resource)
    action: Action = field(default_factory=Action)
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AccessDecision:
    """Access decision."""
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    result: EvaluationResult = EvaluationResult.DENY
    reason: str = ""
    matched_policy: Optional[str] = None
    matched_rule: Optional[str] = None
    obligations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PolicyStats:
    """Policy statistics."""
    total_policies: int = 0
    active_policies: int = 0
    total_evaluations: int = 0
    allow_count: int = 0
    deny_count: int = 0
    avg_evaluation_time: float = 0.0


# =============================================================================
# CONDITION EVALUATOR
# =============================================================================

class ConditionEvaluator:
    """Evaluate policy conditions."""

    def __init__(self):
        self._custom_functions: Dict[str, Callable] = {}

    def register_function(
        self,
        name: str,
        func: Callable[..., bool]
    ) -> None:
        """Register custom function."""
        self._custom_functions[name] = func

    def evaluate(
        self,
        condition: Condition,
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate condition."""
        # Use custom evaluator if provided
        if condition.evaluator:
            try:
                return condition.evaluator(context)
            except Exception:
                return False

        # Parse and evaluate expression
        return self._evaluate_expression(condition.expression, context)

    def _evaluate_expression(
        self,
        expression: str,
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate expression string."""
        if not expression:
            return True

        # Simple expression evaluation
        # Format: "key operator value"
        parts = expression.split()

        if len(parts) >= 3:
            key = parts[0]
            operator = parts[1]
            value_str = " ".join(parts[2:])

            # Get context value
            ctx_value = context.get(key)
            if ctx_value is None:
                return False

            # Parse value
            try:
                if value_str.startswith('"') and value_str.endswith('"'):
                    value = value_str[1:-1]
                elif value_str.lower() == 'true':
                    value = True
                elif value_str.lower() == 'false':
                    value = False
                elif '.' in value_str:
                    value = float(value_str)
                else:
                    value = int(value_str)
            except ValueError:
                value = value_str

            # Evaluate
            if operator == "==":
                return ctx_value == value
            elif operator == "!=":
                return ctx_value != value
            elif operator == ">":
                return ctx_value > value
            elif operator == "<":
                return ctx_value < value
            elif operator == ">=":
                return ctx_value >= value
            elif operator == "<=":
                return ctx_value <= value
            elif operator == "in":
                return value in ctx_value if isinstance(ctx_value, (list, str)) else False
            elif operator == "contains":
                return ctx_value in value if isinstance(value, (list, str)) else False

        # Check custom functions
        for name, func in self._custom_functions.items():
            if expression.startswith(f"{name}("):
                try:
                    return func(context)
                except Exception:
                    return False

        return False


# =============================================================================
# PATTERN MATCHER
# =============================================================================

class PatternMatcher:
    """Match patterns for policies."""

    def match(self, pattern: str, value: str) -> bool:
        """Match pattern against value."""
        if pattern == "*":
            return True

        if pattern == value:
            return True

        # Wildcard matching
        if "*" in pattern:
            regex = "^" + re.escape(pattern).replace(r"\*", ".*") + "$"
            return bool(re.match(regex, value))

        # Prefix matching
        if pattern.endswith("*"):
            return value.startswith(pattern[:-1])

        # Suffix matching
        if pattern.startswith("*"):
            return value.endswith(pattern[1:])

        return False

    def match_any(self, patterns: List[str], value: str) -> bool:
        """Match any pattern."""
        if not patterns:
            return True  # Empty patterns match all

        return any(self.match(p, value) for p in patterns)


# =============================================================================
# CONSTRAINT ENFORCER
# =============================================================================

class ConstraintEnforcer:
    """Enforce policy constraints."""

    def __init__(self):
        self._rate_limits: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

    def enforce(
        self,
        constraint: Constraint,
        context: Dict[str, Any]
    ) -> bool:
        """Enforce constraint."""
        if not constraint.enabled:
            return True

        if constraint.constraint_type == ConstraintType.TIME:
            return self._enforce_time(constraint, context)

        elif constraint.constraint_type == ConstraintType.RATE:
            return self._enforce_rate(constraint, context)

        elif constraint.constraint_type == ConstraintType.RESOURCE:
            return self._enforce_resource(constraint, context)

        elif constraint.constraint_type == ConstraintType.CONDITION:
            return self._enforce_condition(constraint, context)

        return True

    def _enforce_time(
        self,
        constraint: Constraint,
        context: Dict[str, Any]
    ) -> bool:
        """Enforce time constraint."""
        now = datetime.now()
        params = constraint.parameters

        # Check start time
        start = params.get("start")
        if start and isinstance(start, datetime):
            if now < start:
                return False

        # Check end time
        end = params.get("end")
        if end and isinstance(end, datetime):
            if now > end:
                return False

        # Check time of day
        start_hour = params.get("start_hour", 0)
        end_hour = params.get("end_hour", 24)
        if not (start_hour <= now.hour < end_hour):
            return False

        # Check day of week
        allowed_days = params.get("allowed_days")
        if allowed_days and now.weekday() not in allowed_days:
            return False

        return True

    def _enforce_rate(
        self,
        constraint: Constraint,
        context: Dict[str, Any]
    ) -> bool:
        """Enforce rate limit constraint."""
        params = constraint.parameters
        limit = params.get("limit", 100)
        window = params.get("window", 60)  # seconds
        key = params.get("key", "default")

        # Get subject key
        subject_id = context.get("subject_id", "anonymous")
        rate_key = f"{key}:{subject_id}"

        # Clean old entries
        now = time.time()
        cutoff = now - window

        while self._rate_limits[rate_key] and self._rate_limits[rate_key][0] < cutoff:
            self._rate_limits[rate_key].popleft()

        # Check limit
        if len(self._rate_limits[rate_key]) >= limit:
            return False

        # Record access
        self._rate_limits[rate_key].append(now)
        return True

    def _enforce_resource(
        self,
        constraint: Constraint,
        context: Dict[str, Any]
    ) -> bool:
        """Enforce resource constraint."""
        params = constraint.parameters

        # Check allowed resources
        allowed = params.get("allowed", [])
        resource = context.get("resource", "")

        if allowed and resource not in allowed:
            return False

        # Check blocked resources
        blocked = params.get("blocked", [])
        if resource in blocked:
            return False

        return True

    def _enforce_condition(
        self,
        constraint: Constraint,
        context: Dict[str, Any]
    ) -> bool:
        """Enforce condition constraint."""
        evaluator = ConditionEvaluator()
        condition = Condition(expression=constraint.parameters.get("expression", ""))
        return evaluator.evaluate(condition, context)


# =============================================================================
# RULE EVALUATOR
# =============================================================================

class RuleEvaluator:
    """Evaluate policy rules."""

    def __init__(self):
        self._pattern_matcher = PatternMatcher()
        self._condition_evaluator = ConditionEvaluator()

    def evaluate(
        self,
        rule: PolicyRule,
        request: AccessRequest
    ) -> Tuple[EvaluationResult, str]:
        """Evaluate rule against request."""
        # Check if rule applies
        if not self._matches_request(rule, request):
            return EvaluationResult.NOT_APPLICABLE, "Rule does not match request"

        # Evaluate conditions
        context = self._build_context(request)

        for condition in rule.conditions:
            if not self._condition_evaluator.evaluate(condition, context):
                return EvaluationResult.NOT_APPLICABLE, f"Condition not met: {condition.expression}"

        # Return effect
        if rule.effect == PolicyType.ALLOW:
            return EvaluationResult.ALLOW, f"Allowed by rule: {rule.name}"
        elif rule.effect == PolicyType.DENY:
            return EvaluationResult.DENY, f"Denied by rule: {rule.name}"

        return EvaluationResult.INDETERMINATE, "Indeterminate result"

    def _matches_request(
        self,
        rule: PolicyRule,
        request: AccessRequest
    ) -> bool:
        """Check if rule matches request."""
        # Match subject
        subject_match = self._pattern_matcher.match_any(
            rule.subjects,
            request.subject.subject_id
        ) or any(
            self._pattern_matcher.match_any(rule.subjects, role)
            for role in request.subject.roles
        )

        if not subject_match and rule.subjects:
            return False

        # Match resource
        resource_match = self._pattern_matcher.match_any(
            rule.resources,
            request.resource.resource_id
        ) or self._pattern_matcher.match_any(
            rule.resources,
            request.resource.resource_type
        )

        if not resource_match and rule.resources:
            return False

        # Match action
        action_match = self._pattern_matcher.match_any(
            rule.actions,
            request.action.name
        ) or self._pattern_matcher.match_any(
            rule.actions,
            request.action.action_type
        )

        if not action_match and rule.actions:
            return False

        return True

    def _build_context(self, request: AccessRequest) -> Dict[str, Any]:
        """Build evaluation context."""
        context = request.context.copy()
        context.update({
            "subject_id": request.subject.subject_id,
            "subject_name": request.subject.name,
            "subject_roles": request.subject.roles,
            "resource_id": request.resource.resource_id,
            "resource_type": request.resource.resource_type,
            "action_name": request.action.name,
            "action_type": request.action.action_type,
            "timestamp": request.timestamp.isoformat(),
        })
        context.update(request.subject.attributes)
        context.update(request.resource.attributes)
        return context


# =============================================================================
# POLICY COMBINER
# =============================================================================

class PolicyCombiner:
    """Combine multiple policy results."""

    def combine(
        self,
        results: List[Tuple[EvaluationResult, str]],
        algorithm: CombiningAlgorithm
    ) -> Tuple[EvaluationResult, str]:
        """Combine results using algorithm."""
        if not results:
            return EvaluationResult.NOT_APPLICABLE, "No policies to evaluate"

        if algorithm == CombiningAlgorithm.DENY_OVERRIDES:
            return self._deny_overrides(results)

        elif algorithm == CombiningAlgorithm.PERMIT_OVERRIDES:
            return self._permit_overrides(results)

        elif algorithm == CombiningAlgorithm.FIRST_APPLICABLE:
            return self._first_applicable(results)

        elif algorithm == CombiningAlgorithm.ONLY_ONE_APPLICABLE:
            return self._only_one_applicable(results)

        return EvaluationResult.INDETERMINATE, "Unknown combining algorithm"

    def _deny_overrides(
        self,
        results: List[Tuple[EvaluationResult, str]]
    ) -> Tuple[EvaluationResult, str]:
        """Deny overrides - any deny results in deny."""
        for result, reason in results:
            if result == EvaluationResult.DENY:
                return EvaluationResult.DENY, reason

        for result, reason in results:
            if result == EvaluationResult.ALLOW:
                return EvaluationResult.ALLOW, reason

        return EvaluationResult.NOT_APPLICABLE, "No applicable policy"

    def _permit_overrides(
        self,
        results: List[Tuple[EvaluationResult, str]]
    ) -> Tuple[EvaluationResult, str]:
        """Permit overrides - any allow results in allow."""
        for result, reason in results:
            if result == EvaluationResult.ALLOW:
                return EvaluationResult.ALLOW, reason

        for result, reason in results:
            if result == EvaluationResult.DENY:
                return EvaluationResult.DENY, reason

        return EvaluationResult.NOT_APPLICABLE, "No applicable policy"

    def _first_applicable(
        self,
        results: List[Tuple[EvaluationResult, str]]
    ) -> Tuple[EvaluationResult, str]:
        """First applicable - return first non-NA result."""
        for result, reason in results:
            if result in [EvaluationResult.ALLOW, EvaluationResult.DENY]:
                return result, reason

        return EvaluationResult.NOT_APPLICABLE, "No applicable policy"

    def _only_one_applicable(
        self,
        results: List[Tuple[EvaluationResult, str]]
    ) -> Tuple[EvaluationResult, str]:
        """Only one applicable - exactly one must match."""
        applicable = [
            (r, reason) for r, reason in results
            if r in [EvaluationResult.ALLOW, EvaluationResult.DENY]
        ]

        if len(applicable) == 1:
            return applicable[0]
        elif len(applicable) == 0:
            return EvaluationResult.NOT_APPLICABLE, "No applicable policy"
        else:
            return EvaluationResult.INDETERMINATE, "Multiple policies applicable"


# =============================================================================
# PERMISSION MANAGER
# =============================================================================

class PermissionManager:
    """Manage permissions."""

    def __init__(self):
        self._permissions: Dict[str, Dict[str, Permission]] = defaultdict(dict)
        self._pattern_matcher = PatternMatcher()

    def grant(
        self,
        subject_id: str,
        permission: Permission
    ) -> Permission:
        """Grant permission to subject."""
        self._permissions[subject_id][permission.permission_id] = permission
        return permission

    def revoke(
        self,
        subject_id: str,
        permission_id: str
    ) -> bool:
        """Revoke permission."""
        if subject_id in self._permissions:
            if permission_id in self._permissions[subject_id]:
                del self._permissions[subject_id][permission_id]
                return True
        return False

    def check(
        self,
        subject_id: str,
        resource: str,
        action: str,
        required_level: PermissionLevel = PermissionLevel.READ
    ) -> bool:
        """Check if subject has permission."""
        if subject_id not in self._permissions:
            return False

        now = datetime.now()

        for perm in self._permissions[subject_id].values():
            # Check expiry
            if perm.expires_at and now > perm.expires_at:
                continue

            # Check level
            if perm.level.value < required_level.value:
                continue

            # Check patterns
            if self._pattern_matcher.match(perm.resource_pattern, resource):
                if self._pattern_matcher.match(perm.action_pattern, action):
                    return True

        return False

    def get_permissions(self, subject_id: str) -> List[Permission]:
        """Get subject's permissions."""
        return list(self._permissions.get(subject_id, {}).values())

    def cleanup_expired(self) -> int:
        """Remove expired permissions."""
        now = datetime.now()
        count = 0

        for subject_id in list(self._permissions.keys()):
            for perm_id, perm in list(self._permissions[subject_id].items()):
                if perm.expires_at and now > perm.expires_at:
                    del self._permissions[subject_id][perm_id]
                    count += 1

        return count


# =============================================================================
# POLICY REPOSITORY
# =============================================================================

class PolicyRepository:
    """Store and manage policies."""

    def __init__(self):
        self._policies: Dict[str, Policy] = {}
        self._by_name: Dict[str, str] = {}
        self._versions: Dict[str, List[Policy]] = defaultdict(list)

    def add(self, policy: Policy) -> Policy:
        """Add policy."""
        self._policies[policy.policy_id] = policy
        self._by_name[policy.name] = policy.policy_id
        self._versions[policy.name].append(copy.deepcopy(policy))
        return policy

    def get(self, policy_id: str) -> Optional[Policy]:
        """Get policy by ID."""
        return self._policies.get(policy_id)

    def get_by_name(self, name: str) -> Optional[Policy]:
        """Get policy by name."""
        policy_id = self._by_name.get(name)
        return self._policies.get(policy_id) if policy_id else None

    def update(self, policy: Policy) -> Policy:
        """Update policy."""
        policy.updated_at = datetime.now()
        # Increment version
        version_parts = policy.version.split(".")
        version_parts[-1] = str(int(version_parts[-1]) + 1)
        policy.version = ".".join(version_parts)

        self._policies[policy.policy_id] = policy
        self._versions[policy.name].append(copy.deepcopy(policy))
        return policy

    def delete(self, policy_id: str) -> bool:
        """Delete policy."""
        if policy_id in self._policies:
            policy = self._policies[policy_id]
            del self._by_name[policy.name]
            del self._policies[policy_id]
            return True
        return False

    def get_all(self, status: Optional[PolicyStatus] = None) -> List[Policy]:
        """Get all policies."""
        policies = list(self._policies.values())
        if status:
            policies = [p for p in policies if p.status == status]
        return policies

    def get_versions(self, name: str) -> List[Policy]:
        """Get policy versions."""
        return self._versions.get(name, [])


# =============================================================================
# POLICY MANAGER
# =============================================================================

class PolicyManager:
    """
    Policy Manager for BAEL.

    Advanced policy management and access control.
    """

    def __init__(
        self,
        combining: CombiningAlgorithm = CombiningAlgorithm.DENY_OVERRIDES
    ):
        self._repository = PolicyRepository()
        self._rule_evaluator = RuleEvaluator()
        self._combiner = PolicyCombiner()
        self._constraint_enforcer = ConstraintEnforcer()
        self._permission_manager = PermissionManager()
        self._default_combining = combining
        self._stats = PolicyStats()
        self._evaluation_times: deque = deque(maxlen=1000)

    # -------------------------------------------------------------------------
    # POLICY MANAGEMENT
    # -------------------------------------------------------------------------

    def create_policy(
        self,
        name: str,
        description: str = "",
        combining: Optional[CombiningAlgorithm] = None
    ) -> Policy:
        """Create new policy."""
        policy = Policy(
            name=name,
            description=description,
            combining=combining or self._default_combining
        )
        self._repository.add(policy)
        self._stats.total_policies += 1
        self._stats.active_policies += 1
        return policy

    def add_rule(
        self,
        policy_id: str,
        name: str,
        effect: PolicyType = PolicyType.ALLOW,
        subjects: Optional[List[str]] = None,
        resources: Optional[List[str]] = None,
        actions: Optional[List[str]] = None,
        conditions: Optional[List[str]] = None,
        priority: int = 0
    ) -> Optional[PolicyRule]:
        """Add rule to policy."""
        policy = self._repository.get(policy_id)
        if not policy:
            return None

        # Create conditions
        conds = []
        if conditions:
            conds = [Condition(expression=expr) for expr in conditions]

        rule = PolicyRule(
            name=name,
            effect=effect,
            subjects=subjects or [],
            resources=resources or [],
            actions=actions or [],
            conditions=conds,
            priority=priority
        )

        policy.rules.append(rule)
        policy.rules.sort(key=lambda r: r.priority, reverse=True)
        self._repository.update(policy)

        return rule

    def add_constraint(
        self,
        policy_id: str,
        constraint_type: ConstraintType,
        name: str,
        parameters: Dict[str, Any]
    ) -> Optional[Constraint]:
        """Add constraint to policy."""
        policy = self._repository.get(policy_id)
        if not policy:
            return None

        constraint = Constraint(
            constraint_type=constraint_type,
            name=name,
            parameters=parameters
        )

        policy.constraints.append(constraint)
        self._repository.update(policy)

        return constraint

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get policy."""
        return self._repository.get(policy_id)

    def get_policy_by_name(self, name: str) -> Optional[Policy]:
        """Get policy by name."""
        return self._repository.get_by_name(name)

    def list_policies(
        self,
        status: Optional[PolicyStatus] = None
    ) -> List[Policy]:
        """List policies."""
        return self._repository.get_all(status)

    def activate_policy(self, policy_id: str) -> bool:
        """Activate policy."""
        policy = self._repository.get(policy_id)
        if policy:
            if policy.status != PolicyStatus.ACTIVE:
                policy.status = PolicyStatus.ACTIVE
                self._repository.update(policy)
                self._stats.active_policies += 1
            return True
        return False

    def deactivate_policy(self, policy_id: str) -> bool:
        """Deactivate policy."""
        policy = self._repository.get(policy_id)
        if policy:
            if policy.status == PolicyStatus.ACTIVE:
                policy.status = PolicyStatus.INACTIVE
                self._repository.update(policy)
                self._stats.active_policies -= 1
            return True
        return False

    def delete_policy(self, policy_id: str) -> bool:
        """Delete policy."""
        policy = self._repository.get(policy_id)
        if policy:
            if policy.status == PolicyStatus.ACTIVE:
                self._stats.active_policies -= 1
            self._stats.total_policies -= 1
            return self._repository.delete(policy_id)
        return False

    # -------------------------------------------------------------------------
    # EVALUATION
    # -------------------------------------------------------------------------

    def evaluate(self, request: AccessRequest) -> AccessDecision:
        """Evaluate access request."""
        start_time = time.time()

        # Get active policies
        policies = self._repository.get_all(PolicyStatus.ACTIVE)

        if not policies:
            return AccessDecision(
                result=EvaluationResult.DENY,
                reason="No active policies"
            )

        # Evaluate each policy
        all_results = []
        matched_policy = None
        matched_rule = None

        for policy in policies:
            # Check constraints
            context = request.context.copy()
            context["subject_id"] = request.subject.subject_id
            context["resource"] = request.resource.resource_id

            constraint_ok = True
            for constraint in policy.constraints:
                if not self._constraint_enforcer.enforce(constraint, context):
                    constraint_ok = False
                    break

            if not constraint_ok:
                continue

            # Evaluate rules
            rule_results = []
            for rule in policy.rules:
                result, reason = self._rule_evaluator.evaluate(rule, request)
                if result != EvaluationResult.NOT_APPLICABLE:
                    rule_results.append((result, reason))
                    if result in [EvaluationResult.ALLOW, EvaluationResult.DENY]:
                        matched_rule = rule.rule_id

            if rule_results:
                policy_result = self._combiner.combine(rule_results, policy.combining)
                all_results.append(policy_result)
                matched_policy = policy.policy_id

        # Combine all results
        final_result, reason = self._combiner.combine(
            all_results,
            self._default_combining
        )

        # Update stats
        elapsed = time.time() - start_time
        self._evaluation_times.append(elapsed)
        self._stats.total_evaluations += 1

        if final_result == EvaluationResult.ALLOW:
            self._stats.allow_count += 1
        elif final_result == EvaluationResult.DENY:
            self._stats.deny_count += 1

        self._stats.avg_evaluation_time = (
            sum(self._evaluation_times) / len(self._evaluation_times)
        )

        return AccessDecision(
            result=final_result,
            reason=reason,
            matched_policy=matched_policy,
            matched_rule=matched_rule
        )

    def is_allowed(
        self,
        subject_id: str,
        resource_id: str,
        action: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Quick check if action is allowed."""
        request = AccessRequest(
            subject=Subject(subject_id=subject_id),
            resource=Resource(resource_id=resource_id),
            action=Action(name=action),
            context=context or {}
        )

        decision = self.evaluate(request)
        return decision.result == EvaluationResult.ALLOW

    # -------------------------------------------------------------------------
    # PERMISSIONS
    # -------------------------------------------------------------------------

    def grant_permission(
        self,
        subject_id: str,
        name: str,
        level: PermissionLevel = PermissionLevel.READ,
        resource_pattern: str = "*",
        action_pattern: str = "*",
        expires_in: Optional[timedelta] = None
    ) -> Permission:
        """Grant permission."""
        permission = Permission(
            name=name,
            level=level,
            resource_pattern=resource_pattern,
            action_pattern=action_pattern,
            expires_at=datetime.now() + expires_in if expires_in else None
        )

        return self._permission_manager.grant(subject_id, permission)

    def revoke_permission(
        self,
        subject_id: str,
        permission_id: str
    ) -> bool:
        """Revoke permission."""
        return self._permission_manager.revoke(subject_id, permission_id)

    def check_permission(
        self,
        subject_id: str,
        resource: str,
        action: str,
        required_level: PermissionLevel = PermissionLevel.READ
    ) -> bool:
        """Check permission."""
        return self._permission_manager.check(
            subject_id, resource, action, required_level
        )

    def get_permissions(self, subject_id: str) -> List[Permission]:
        """Get subject's permissions."""
        return self._permission_manager.get_permissions(subject_id)

    # -------------------------------------------------------------------------
    # POLICY INHERITANCE
    # -------------------------------------------------------------------------

    def set_parent_policy(
        self,
        child_id: str,
        parent_id: str
    ) -> bool:
        """Set parent policy for inheritance."""
        child = self._repository.get(child_id)
        parent = self._repository.get(parent_id)

        if child and parent:
            child.parent_id = parent_id
            self._repository.update(child)
            return True
        return False

    def get_inherited_rules(self, policy_id: str) -> List[PolicyRule]:
        """Get all rules including inherited."""
        policy = self._repository.get(policy_id)
        if not policy:
            return []

        rules = list(policy.rules)

        if policy.parent_id:
            parent_rules = self.get_inherited_rules(policy.parent_id)
            rules.extend(parent_rules)

        return rules

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> PolicyStats:
        """Get policy statistics."""
        return self._stats

    def get_policy_versions(self, name: str) -> List[Policy]:
        """Get policy versions."""
        return self._repository.get_versions(name)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Policy Manager."""
    print("=" * 70)
    print("BAEL - POLICY MANAGER DEMO")
    print("Advanced Policy Management and Access Control")
    print("=" * 70)
    print()

    manager = PolicyManager()

    # 1. Create Policy
    print("1. CREATE POLICY:")
    print("-" * 40)

    policy = manager.create_policy(
        name="resource_access",
        description="Controls access to resources"
    )

    print(f"   Created: {policy.name}")
    print(f"   ID: {policy.policy_id[:8]}...")
    print(f"   Version: {policy.version}")
    print()

    # 2. Add Rules
    print("2. ADD RULES:")
    print("-" * 40)

    rule1 = manager.add_rule(
        policy.policy_id,
        name="admin_full_access",
        effect=PolicyType.ALLOW,
        subjects=["admin", "role:admin"],
        resources=["*"],
        actions=["*"]
    )
    print(f"   Added: {rule1.name}")

    rule2 = manager.add_rule(
        policy.policy_id,
        name="user_read_access",
        effect=PolicyType.ALLOW,
        subjects=["role:user"],
        resources=["documents/*"],
        actions=["read", "list"]
    )
    print(f"   Added: {rule2.name}")

    rule3 = manager.add_rule(
        policy.policy_id,
        name="deny_sensitive",
        effect=PolicyType.DENY,
        resources=["sensitive/*"],
        actions=["*"],
        priority=10  # Higher priority
    )
    print(f"   Added: {rule3.name}")
    print()

    # 3. Add Constraints
    print("3. ADD CONSTRAINTS:")
    print("-" * 40)

    constraint = manager.add_constraint(
        policy.policy_id,
        ConstraintType.RATE,
        "rate_limit",
        {"limit": 100, "window": 60, "key": "api"}
    )
    print(f"   Added: {constraint.name} ({constraint.constraint_type.value})")

    time_constraint = manager.add_constraint(
        policy.policy_id,
        ConstraintType.TIME,
        "business_hours",
        {"start_hour": 9, "end_hour": 17}
    )
    print(f"   Added: {time_constraint.name} ({time_constraint.constraint_type.value})")
    print()

    # 4. Evaluate Access
    print("4. EVALUATE ACCESS:")
    print("-" * 40)

    # Admin access
    request = AccessRequest(
        subject=Subject(subject_id="admin_user", roles=["admin"]),
        resource=Resource(resource_id="documents/report.pdf"),
        action=Action(name="delete")
    )

    decision = manager.evaluate(request)
    print(f"   Admin delete document: {decision.result.value}")
    print(f"   Reason: {decision.reason}")
    print()

    # User read access
    request = AccessRequest(
        subject=Subject(subject_id="user1", roles=["user"]),
        resource=Resource(resource_id="documents/public.txt"),
        action=Action(name="read")
    )

    decision = manager.evaluate(request)
    print(f"   User read document: {decision.result.value}")
    print()

    # User write (should be denied)
    request = AccessRequest(
        subject=Subject(subject_id="user1", roles=["user"]),
        resource=Resource(resource_id="documents/public.txt"),
        action=Action(name="write")
    )

    decision = manager.evaluate(request)
    print(f"   User write document: {decision.result.value}")
    print()

    # 5. Quick Check
    print("5. QUICK CHECK:")
    print("-" * 40)

    allowed = manager.is_allowed("admin_user", "files/data.csv", "delete")
    print(f"   Admin delete files: {allowed}")

    allowed = manager.is_allowed("user1", "sensitive/secrets.txt", "read")
    print(f"   User read sensitive: {allowed}")
    print()

    # 6. Permissions
    print("6. PERMISSIONS:")
    print("-" * 40)

    perm = manager.grant_permission(
        "api_client_1",
        "api_access",
        level=PermissionLevel.EXECUTE,
        resource_pattern="api/*",
        action_pattern="*",
        expires_in=timedelta(days=30)
    )
    print(f"   Granted: {perm.name} to api_client_1")

    has_perm = manager.check_permission(
        "api_client_1",
        "api/users",
        "list",
        PermissionLevel.EXECUTE
    )
    print(f"   Check api access: {has_perm}")

    perms = manager.get_permissions("api_client_1")
    print(f"   Total permissions: {len(perms)}")
    print()

    # 7. Policy Inheritance
    print("7. POLICY INHERITANCE:")
    print("-" * 40)

    parent = manager.create_policy("base_policy", "Base security policy")
    manager.add_rule(
        parent.policy_id,
        "base_deny_all",
        effect=PolicyType.DENY,
        resources=["*"],
        actions=["*"],
        priority=-100  # Low priority fallback
    )

    child = manager.create_policy("extended_policy", "Extended policy")
    manager.set_parent_policy(child.policy_id, parent.policy_id)

    inherited = manager.get_inherited_rules(child.policy_id)
    print(f"   Parent: {parent.name}")
    print(f"   Child: {child.name}")
    print(f"   Inherited rules: {len(inherited)}")
    print()

    # 8. List Policies
    print("8. LIST POLICIES:")
    print("-" * 40)

    policies = manager.list_policies(PolicyStatus.ACTIVE)

    for p in policies:
        print(f"   - {p.name} (v{p.version}): {len(p.rules)} rules")
    print()

    # 9. Deactivate Policy
    print("9. DEACTIVATE POLICY:")
    print("-" * 40)

    manager.deactivate_policy(child.policy_id)
    active = manager.list_policies(PolicyStatus.ACTIVE)

    print(f"   Deactivated: {child.name}")
    print(f"   Active policies: {len(active)}")
    print()

    # 10. Policy Versioning
    print("10. POLICY VERSIONING:")
    print("-" * 40)

    # Add another rule to create new version
    manager.add_rule(
        policy.policy_id,
        "new_rule",
        effect=PolicyType.ALLOW,
        resources=["new/*"],
        actions=["*"]
    )

    versions = manager.get_policy_versions("resource_access")
    print(f"   Policy: resource_access")
    print(f"   Versions: {len(versions)}")
    for v in versions:
        print(f"     v{v.version}: {len(v.rules)} rules")
    print()

    # 11. Conditional Rules
    print("11. CONDITIONAL RULES:")
    print("-" * 40)

    manager.add_rule(
        policy.policy_id,
        "time_limited",
        effect=PolicyType.ALLOW,
        resources=["temp/*"],
        actions=["read"],
        conditions=["hour >= 9", "hour <= 17"]
    )
    print("   Added time-limited access rule")
    print()

    # 12. Statistics
    print("12. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()

    print(f"   Total policies: {stats.total_policies}")
    print(f"   Active policies: {stats.active_policies}")
    print(f"   Total evaluations: {stats.total_evaluations}")
    print(f"   Allow count: {stats.allow_count}")
    print(f"   Deny count: {stats.deny_count}")
    print(f"   Avg eval time: {stats.avg_evaluation_time*1000:.3f}ms")
    print()

    # 13. Revoke Permission
    print("13. REVOKE PERMISSION:")
    print("-" * 40)

    revoked = manager.revoke_permission("api_client_1", perm.permission_id)
    print(f"   Revoked: {revoked}")

    has_perm = manager.check_permission(
        "api_client_1",
        "api/users",
        "list",
        PermissionLevel.EXECUTE
    )
    print(f"   Check after revoke: {has_perm}")
    print()

    # 14. Delete Policy
    print("14. DELETE POLICY:")
    print("-" * 40)

    deleted = manager.delete_policy(child.policy_id)
    print(f"   Deleted extended_policy: {deleted}")
    print(f"   Remaining policies: {len(manager.list_policies())}")
    print()

    # 15. Complex Evaluation
    print("15. COMPLEX EVALUATION:")
    print("-" * 40)

    # User with multiple roles
    request = AccessRequest(
        subject=Subject(
            subject_id="power_user",
            roles=["user", "editor"],
            attributes={"department": "engineering"}
        ),
        resource=Resource(
            resource_id="documents/tech/spec.md",
            resource_type="document",
            attributes={"sensitivity": "internal"}
        ),
        action=Action(name="read", action_type="view"),
        context={"ip": "10.0.0.1", "hour": 14}
    )

    decision = manager.evaluate(request)
    print(f"   Complex request: {decision.result.value}")
    print(f"   Matched policy: {decision.matched_policy[:8] if decision.matched_policy else 'None'}...")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Policy Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
