#!/usr/bin/env python3
"""
BAEL - Permission Manager
Comprehensive Attribute-Based Access Control (ABAC) system.

Features:
- Attribute-based access control
- Policy-based authorization
- Permission evaluation engine
- Role management
- Resource permissions
- Context-aware authorization
- Policy caching
- Audit logging
- Permission inheritance
- Dynamic policy loading
"""

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class Effect(Enum):
    """Policy effect."""
    ALLOW = "allow"
    DENY = "deny"


class PolicyType(Enum):
    """Policy type."""
    IDENTITY = "identity"
    RESOURCE = "resource"
    COMPOSITE = "composite"


class ConditionOperator(Enum):
    """Condition operators."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    MATCHES = "matches"
    BETWEEN = "between"


class ResourceType(Enum):
    """Resource types."""
    FILE = "file"
    API = "api"
    DATA = "data"
    SERVICE = "service"
    FEATURE = "feature"
    ADMIN = "admin"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Subject:
    """Authorization subject (user/service)."""
    id: str
    type: str = "user"
    attributes: Dict[str, Any] = field(default_factory=dict)
    roles: Set[str] = field(default_factory=set)
    groups: Set[str] = field(default_factory=set)

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_any_role(self, roles: Set[str]) -> bool:
        return bool(self.roles & roles)

    def get_attribute(self, key: str, default: Any = None) -> Any:
        return self.attributes.get(key, default)


@dataclass
class Resource:
    """Authorization resource."""
    id: str
    type: ResourceType
    owner_id: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    parent_id: str = ""

    def get_attribute(self, key: str, default: Any = None) -> Any:
        return self.attributes.get(key, default)


@dataclass
class Action:
    """Authorization action."""
    name: str
    resource_type: ResourceType
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthContext:
    """Authorization context."""
    subject: Subject
    resource: Resource
    action: Action
    environment: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def get_env(self, key: str, default: Any = None) -> Any:
        return self.environment.get(key, default)


@dataclass
class Condition:
    """Policy condition."""
    attribute: str
    operator: ConditionOperator
    value: Any
    source: str = "subject"  # subject, resource, environment

    def evaluate(self, context: AuthContext) -> bool:
        """Evaluate condition against context."""
        # Get attribute value
        if self.source == "subject":
            actual = context.subject.get_attribute(self.attribute)
        elif self.source == "resource":
            actual = context.resource.get_attribute(self.attribute)
        elif self.source == "environment":
            actual = context.get_env(self.attribute)
        else:
            actual = None

        # Evaluate operator
        if self.operator == ConditionOperator.EQUALS:
            return actual == self.value

        if self.operator == ConditionOperator.NOT_EQUALS:
            return actual != self.value

        if self.operator == ConditionOperator.CONTAINS:
            return self.value in str(actual) if actual else False

        if self.operator == ConditionOperator.STARTS_WITH:
            return str(actual).startswith(self.value) if actual else False

        if self.operator == ConditionOperator.ENDS_WITH:
            return str(actual).endswith(self.value) if actual else False

        if self.operator == ConditionOperator.GREATER_THAN:
            return actual > self.value if actual is not None else False

        if self.operator == ConditionOperator.LESS_THAN:
            return actual < self.value if actual is not None else False

        if self.operator == ConditionOperator.IN:
            return actual in self.value if self.value else False

        if self.operator == ConditionOperator.NOT_IN:
            return actual not in self.value if self.value else True

        if self.operator == ConditionOperator.EXISTS:
            return actual is not None

        if self.operator == ConditionOperator.NOT_EXISTS:
            return actual is None

        if self.operator == ConditionOperator.MATCHES:
            return bool(re.match(self.value, str(actual))) if actual else False

        if self.operator == ConditionOperator.BETWEEN:
            min_val, max_val = self.value
            return min_val <= actual <= max_val if actual is not None else False

        return False


@dataclass
class Policy:
    """Authorization policy."""
    policy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    effect: Effect = Effect.ALLOW
    policy_type: PolicyType = PolicyType.RESOURCE
    subjects: List[str] = field(default_factory=list)  # Subject patterns
    resources: List[str] = field(default_factory=list)  # Resource patterns
    actions: List[str] = field(default_factory=list)  # Action patterns
    conditions: List[Condition] = field(default_factory=list)
    priority: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def matches_subject(self, subject: Subject) -> bool:
        """Check if policy matches subject."""
        if not self.subjects:
            return True

        for pattern in self.subjects:
            if pattern == "*":
                return True

            if pattern.startswith("role:"):
                role = pattern[5:]
                if subject.has_role(role):
                    return True

            if pattern.startswith("group:"):
                group = pattern[6:]
                if group in subject.groups:
                    return True

            if pattern == subject.id:
                return True

            if self._matches_pattern(subject.id, pattern):
                return True

        return False

    def matches_resource(self, resource: Resource) -> bool:
        """Check if policy matches resource."""
        if not self.resources:
            return True

        for pattern in self.resources:
            if pattern == "*":
                return True

            if pattern.startswith("type:"):
                res_type = pattern[5:]
                if resource.type.value == res_type:
                    return True

            if pattern == resource.id:
                return True

            if self._matches_pattern(resource.id, pattern):
                return True

        return False

    def matches_action(self, action: Action) -> bool:
        """Check if policy matches action."""
        if not self.actions:
            return True

        for pattern in self.actions:
            if pattern == "*":
                return True

            if pattern == action.name:
                return True

            if self._matches_pattern(action.name, pattern):
                return True

        return False

    def evaluate_conditions(self, context: AuthContext) -> bool:
        """Evaluate all conditions."""
        if not self.conditions:
            return True

        return all(cond.evaluate(context) for cond in self.conditions)

    def _matches_pattern(self, value: str, pattern: str) -> bool:
        """Match value against pattern (supports * wildcard)."""
        regex = pattern.replace("*", ".*")
        return bool(re.match(f"^{regex}$", value))


@dataclass
class AuthDecision:
    """Authorization decision."""
    allowed: bool
    effect: Effect
    policy_id: str = ""
    policy_name: str = ""
    reason: str = ""
    evaluated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditEntry:
    """Authorization audit entry."""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    subject_id: str = ""
    resource_id: str = ""
    action: str = ""
    decision: bool = False
    policy_id: str = ""
    reason: str = ""
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# POLICY STORE
# =============================================================================

class PolicyStore(ABC):
    """Abstract policy store."""

    @abstractmethod
    async def add(self, policy: Policy) -> None:
        pass

    @abstractmethod
    async def get(self, policy_id: str) -> Optional[Policy]:
        pass

    @abstractmethod
    async def list_all(self) -> List[Policy]:
        pass

    @abstractmethod
    async def delete(self, policy_id: str) -> bool:
        pass


class InMemoryPolicyStore(PolicyStore):
    """In-memory policy store."""

    def __init__(self):
        self.policies: Dict[str, Policy] = {}

    async def add(self, policy: Policy) -> None:
        self.policies[policy.policy_id] = policy

    async def get(self, policy_id: str) -> Optional[Policy]:
        return self.policies.get(policy_id)

    async def list_all(self) -> List[Policy]:
        # Return sorted by priority
        return sorted(
            self.policies.values(),
            key=lambda p: p.priority,
            reverse=True
        )

    async def delete(self, policy_id: str) -> bool:
        if policy_id in self.policies:
            del self.policies[policy_id]
            return True
        return False


# =============================================================================
# POLICY EVALUATOR
# =============================================================================

class PolicyEvaluator:
    """Policy evaluation engine."""

    def __init__(self, store: PolicyStore):
        self.store = store
        self._cache: Dict[str, AuthDecision] = {}
        self._cache_ttl = 300  # 5 minutes

    def _get_cache_key(self, context: AuthContext) -> str:
        """Generate cache key."""
        key_parts = [
            context.subject.id,
            context.resource.id,
            context.action.name,
            json.dumps(context.environment, sort_keys=True)
        ]
        return hashlib.md5(":".join(key_parts).encode()).hexdigest()

    async def evaluate(self, context: AuthContext) -> AuthDecision:
        """Evaluate authorization request."""
        # Check cache
        cache_key = self._get_cache_key(context)

        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached.evaluated_at < self._cache_ttl:
                return cached

        # Get all policies
        policies = await self.store.list_all()

        # Filter applicable policies
        applicable = [
            p for p in policies
            if p.enabled
            and p.matches_subject(context.subject)
            and p.matches_resource(context.resource)
            and p.matches_action(context.action)
        ]

        if not applicable:
            decision = AuthDecision(
                allowed=False,
                effect=Effect.DENY,
                reason="No matching policy found"
            )
            self._cache[cache_key] = decision
            return decision

        # Evaluate conditions and find decision
        for policy in applicable:
            if policy.evaluate_conditions(context):
                decision = AuthDecision(
                    allowed=policy.effect == Effect.ALLOW,
                    effect=policy.effect,
                    policy_id=policy.policy_id,
                    policy_name=policy.name,
                    reason=f"Policy '{policy.name}' matched"
                )

                self._cache[cache_key] = decision
                return decision

        # Default deny
        decision = AuthDecision(
            allowed=False,
            effect=Effect.DENY,
            reason="No policy conditions satisfied"
        )

        self._cache[cache_key] = decision
        return decision

    def clear_cache(self) -> None:
        """Clear evaluation cache."""
        self._cache.clear()


# =============================================================================
# ROLE MANAGER
# =============================================================================

@dataclass
class Role:
    """Role definition."""
    name: str
    description: str = ""
    permissions: Set[str] = field(default_factory=set)
    parent_roles: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RoleManager:
    """Role management."""

    def __init__(self):
        self.roles: Dict[str, Role] = {}

    def add_role(self, role: Role) -> None:
        """Add role."""
        self.roles[role.name] = role

    def get_role(self, name: str) -> Optional[Role]:
        """Get role."""
        return self.roles.get(name)

    def delete_role(self, name: str) -> bool:
        """Delete role."""
        if name in self.roles:
            del self.roles[name]
            return True
        return False

    def get_permissions(self, role_name: str) -> Set[str]:
        """Get all permissions for role (including inherited)."""
        role = self.roles.get(role_name)

        if not role:
            return set()

        permissions = set(role.permissions)

        # Add inherited permissions
        for parent_name in role.parent_roles:
            permissions |= self.get_permissions(parent_name)

        return permissions

    def has_permission(self, role_name: str, permission: str) -> bool:
        """Check if role has permission."""
        return permission in self.get_permissions(role_name)

    def add_permission(self, role_name: str, permission: str) -> bool:
        """Add permission to role."""
        role = self.roles.get(role_name)

        if role:
            role.permissions.add(permission)
            return True

        return False

    def remove_permission(self, role_name: str, permission: str) -> bool:
        """Remove permission from role."""
        role = self.roles.get(role_name)

        if role and permission in role.permissions:
            role.permissions.remove(permission)
            return True

        return False


# =============================================================================
# PERMISSION MANAGER
# =============================================================================

class PermissionManager:
    """
    Comprehensive Permission Manager for BAEL.
    """

    def __init__(
        self,
        policy_store: PolicyStore = None
    ):
        self.policy_store = policy_store or InMemoryPolicyStore()
        self.evaluator = PolicyEvaluator(self.policy_store)
        self.role_manager = RoleManager()
        self.audit_log: List[AuditEntry] = []
        self._audit_enabled = True

    # -------------------------------------------------------------------------
    # POLICY MANAGEMENT
    # -------------------------------------------------------------------------

    async def add_policy(self, policy: Policy) -> str:
        """Add authorization policy."""
        await self.policy_store.add(policy)
        self.evaluator.clear_cache()
        return policy.policy_id

    async def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get policy by ID."""
        return await self.policy_store.get(policy_id)

    async def list_policies(self) -> List[Policy]:
        """List all policies."""
        return await self.policy_store.list_all()

    async def delete_policy(self, policy_id: str) -> bool:
        """Delete policy."""
        result = await self.policy_store.delete(policy_id)
        self.evaluator.clear_cache()
        return result

    # -------------------------------------------------------------------------
    # AUTHORIZATION
    # -------------------------------------------------------------------------

    async def authorize(
        self,
        subject: Subject,
        resource: Resource,
        action: Action,
        environment: Dict[str, Any] = None
    ) -> AuthDecision:
        """Authorize action."""
        context = AuthContext(
            subject=subject,
            resource=resource,
            action=action,
            environment=environment or {}
        )

        decision = await self.evaluator.evaluate(context)

        # Audit log
        if self._audit_enabled:
            self._log_audit(context, decision)

        return decision

    async def is_allowed(
        self,
        subject: Subject,
        resource: Resource,
        action: Action,
        environment: Dict[str, Any] = None
    ) -> bool:
        """Check if action is allowed."""
        decision = await self.authorize(subject, resource, action, environment)
        return decision.allowed

    async def check_permission(
        self,
        subject: Subject,
        permission: str
    ) -> bool:
        """Check if subject has permission."""
        for role in subject.roles:
            if self.role_manager.has_permission(role, permission):
                return True
        return False

    # -------------------------------------------------------------------------
    # ROLE MANAGEMENT
    # -------------------------------------------------------------------------

    def add_role(self, role: Role) -> None:
        """Add role."""
        self.role_manager.add_role(role)

    def get_role(self, name: str) -> Optional[Role]:
        """Get role."""
        return self.role_manager.get_role(name)

    def get_role_permissions(self, role_name: str) -> Set[str]:
        """Get role permissions."""
        return self.role_manager.get_permissions(role_name)

    def add_permission_to_role(
        self,
        role_name: str,
        permission: str
    ) -> bool:
        """Add permission to role."""
        return self.role_manager.add_permission(role_name, permission)

    # -------------------------------------------------------------------------
    # AUDIT
    # -------------------------------------------------------------------------

    def _log_audit(
        self,
        context: AuthContext,
        decision: AuthDecision
    ) -> None:
        """Log authorization decision."""
        entry = AuditEntry(
            subject_id=context.subject.id,
            resource_id=context.resource.id,
            action=context.action.name,
            decision=decision.allowed,
            policy_id=decision.policy_id,
            reason=decision.reason,
            context={
                "subject_roles": list(context.subject.roles),
                "resource_type": context.resource.type.value,
                "environment": context.environment
            }
        )

        self.audit_log.append(entry)

        # Trim log if too large
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-10000:]

    def get_audit_log(
        self,
        subject_id: str = None,
        resource_id: str = None,
        limit: int = 100
    ) -> List[AuditEntry]:
        """Get audit log entries."""
        entries = self.audit_log

        if subject_id:
            entries = [e for e in entries if e.subject_id == subject_id]

        if resource_id:
            entries = [e for e in entries if e.resource_id == resource_id]

        return entries[-limit:]

    def enable_audit(self, enabled: bool = True) -> None:
        """Enable/disable audit logging."""
        self._audit_enabled = enabled

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def clear_cache(self) -> None:
        """Clear evaluation cache."""
        self.evaluator.clear_cache()

    def get_stats(self) -> Dict[str, Any]:
        """Get permission manager statistics."""
        return {
            "total_policies": len(self.evaluator.store.policies) if hasattr(self.evaluator.store, 'policies') else 0,
            "total_roles": len(self.role_manager.roles),
            "audit_entries": len(self.audit_log),
            "cache_size": len(self.evaluator._cache)
        }


# =============================================================================
# POLICY BUILDER
# =============================================================================

class PolicyBuilder:
    """Fluent policy builder."""

    def __init__(self, name: str):
        self.policy = Policy(name=name)

    def description(self, desc: str) -> 'PolicyBuilder':
        self.policy.description = desc
        return self

    def allow(self) -> 'PolicyBuilder':
        self.policy.effect = Effect.ALLOW
        return self

    def deny(self) -> 'PolicyBuilder':
        self.policy.effect = Effect.DENY
        return self

    def for_subjects(self, *subjects: str) -> 'PolicyBuilder':
        self.policy.subjects = list(subjects)
        return self

    def for_roles(self, *roles: str) -> 'PolicyBuilder':
        self.policy.subjects = [f"role:{r}" for r in roles]
        return self

    def on_resources(self, *resources: str) -> 'PolicyBuilder':
        self.policy.resources = list(resources)
        return self

    def on_resource_type(self, res_type: ResourceType) -> 'PolicyBuilder':
        self.policy.resources = [f"type:{res_type.value}"]
        return self

    def for_actions(self, *actions: str) -> 'PolicyBuilder':
        self.policy.actions = list(actions)
        return self

    def when(
        self,
        attribute: str,
        operator: ConditionOperator,
        value: Any,
        source: str = "subject"
    ) -> 'PolicyBuilder':
        self.policy.conditions.append(
            Condition(attribute, operator, value, source)
        )
        return self

    def priority(self, priority: int) -> 'PolicyBuilder':
        self.policy.priority = priority
        return self

    def build(self) -> Policy:
        return self.policy


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Permission Manager System."""
    print("=" * 70)
    print("BAEL - PERMISSION MANAGER SYSTEM DEMO")
    print("Comprehensive ABAC Authorization")
    print("=" * 70)
    print()

    pm = PermissionManager()

    # 1. Define Roles
    print("1. DEFINE ROLES:")
    print("-" * 40)

    pm.add_role(Role(
        name="admin",
        description="Administrator role",
        permissions={"users:read", "users:write", "users:delete", "admin:access"}
    ))

    pm.add_role(Role(
        name="moderator",
        description="Moderator role",
        permissions={"users:read", "content:moderate"},
        parent_roles={"user"}
    ))

    pm.add_role(Role(
        name="user",
        description="Basic user role",
        permissions={"profile:read", "profile:write"}
    ))

    print(f"   Roles defined: {len(pm.role_manager.roles)}")

    admin_perms = pm.get_role_permissions("admin")
    print(f"   Admin permissions: {admin_perms}")
    print()

    # 2. Create Policies
    print("2. CREATE POLICIES:")
    print("-" * 40)

    # Admin policy
    admin_policy = (
        PolicyBuilder("AdminFullAccess")
        .description("Admins have full access")
        .allow()
        .for_roles("admin")
        .on_resources("*")
        .for_actions("*")
        .priority(100)
        .build()
    )

    await pm.add_policy(admin_policy)

    # Resource owner policy
    owner_policy = (
        PolicyBuilder("OwnerAccess")
        .description("Resource owners can access their resources")
        .allow()
        .for_subjects("*")
        .on_resources("*")
        .for_actions("read", "update", "delete")
        .when("id", ConditionOperator.EQUALS, "${resource.owner_id}", "subject")
        .priority(50)
        .build()
    )

    await pm.add_policy(owner_policy)

    # Public read policy
    public_policy = (
        PolicyBuilder("PublicRead")
        .description("Anyone can read public resources")
        .allow()
        .for_subjects("*")
        .on_resource_type(ResourceType.DATA)
        .for_actions("read")
        .when("visibility", ConditionOperator.EQUALS, "public", "resource")
        .priority(10)
        .build()
    )

    await pm.add_policy(public_policy)

    # Deny delete for non-admins
    deny_policy = (
        PolicyBuilder("DenyDeleteNonAdmin")
        .description("Non-admins cannot delete")
        .deny()
        .for_subjects("*")
        .on_resource_type(ResourceType.DATA)
        .for_actions("delete")
        .priority(75)
        .build()
    )

    await pm.add_policy(deny_policy)

    policies = await pm.list_policies()
    print(f"   Policies created: {len(policies)}")

    for p in policies:
        print(f"      - {p.name} ({p.effect.value})")
    print()

    # 3. Create Subjects
    print("3. CREATE SUBJECTS:")
    print("-" * 40)

    admin_user = Subject(
        id="user-001",
        type="user",
        attributes={"name": "Admin Alice", "department": "IT"},
        roles={"admin"}
    )

    regular_user = Subject(
        id="user-002",
        type="user",
        attributes={"name": "Bob User", "department": "Sales"},
        roles={"user"}
    )

    print(f"   Admin: {admin_user.id} (roles: {admin_user.roles})")
    print(f"   User: {regular_user.id} (roles: {regular_user.roles})")
    print()

    # 4. Create Resources
    print("4. CREATE RESOURCES:")
    print("-" * 40)

    public_doc = Resource(
        id="doc-001",
        type=ResourceType.DATA,
        owner_id="user-002",
        attributes={"visibility": "public", "title": "Public Document"}
    )

    private_doc = Resource(
        id="doc-002",
        type=ResourceType.DATA,
        owner_id="user-002",
        attributes={"visibility": "private", "title": "Private Document"}
    )

    admin_resource = Resource(
        id="admin-001",
        type=ResourceType.ADMIN,
        attributes={"section": "user-management"}
    )

    print(f"   Public doc: {public_doc.id}")
    print(f"   Private doc: {private_doc.id}")
    print(f"   Admin resource: {admin_resource.id}")
    print()

    # 5. Authorization Tests
    print("5. AUTHORIZATION TESTS:")
    print("-" * 40)

    # Admin reading anything
    decision = await pm.authorize(
        admin_user,
        public_doc,
        Action("read", ResourceType.DATA)
    )
    print(f"   Admin read public: {decision.allowed} ({decision.reason})")

    # User reading public
    decision = await pm.authorize(
        regular_user,
        public_doc,
        Action("read", ResourceType.DATA)
    )
    print(f"   User read public: {decision.allowed} ({decision.reason})")

    # User reading private (not owner)
    other_user = Subject(id="user-003", roles={"user"})

    decision = await pm.authorize(
        other_user,
        private_doc,
        Action("read", ResourceType.DATA)
    )
    print(f"   Other read private: {decision.allowed} ({decision.reason})")

    # Owner accessing own resource
    decision = await pm.authorize(
        regular_user,
        private_doc,
        Action("update", ResourceType.DATA)
    )
    print(f"   Owner update own: {decision.allowed}")
    print()

    # 6. Delete Authorization
    print("6. DELETE AUTHORIZATION:")
    print("-" * 40)

    # Admin delete
    decision = await pm.authorize(
        admin_user,
        public_doc,
        Action("delete", ResourceType.DATA)
    )
    print(f"   Admin delete: {decision.allowed} ({decision.policy_name})")

    # User delete (should be denied)
    decision = await pm.authorize(
        regular_user,
        private_doc,
        Action("delete", ResourceType.DATA)
    )
    print(f"   User delete: {decision.allowed} ({decision.reason})")
    print()

    # 7. Permission Check
    print("7. PERMISSION CHECK:")
    print("-" * 40)

    has_perm = await pm.check_permission(admin_user, "admin:access")
    print(f"   Admin has 'admin:access': {has_perm}")

    has_perm = await pm.check_permission(regular_user, "admin:access")
    print(f"   User has 'admin:access': {has_perm}")

    has_perm = await pm.check_permission(regular_user, "profile:read")
    print(f"   User has 'profile:read': {has_perm}")
    print()

    # 8. Conditional Policies
    print("8. CONDITIONAL POLICIES:")
    print("-" * 40)

    # Time-based policy
    time_policy = (
        PolicyBuilder("BusinessHoursOnly")
        .description("Access only during business hours")
        .allow()
        .for_roles("user")
        .on_resource_type(ResourceType.SERVICE)
        .for_actions("access")
        .when("hour", ConditionOperator.BETWEEN, (9, 17), "environment")
        .priority(20)
        .build()
    )

    await pm.add_policy(time_policy)

    service = Resource(id="svc-001", type=ResourceType.SERVICE)

    # During business hours
    decision = await pm.authorize(
        regular_user,
        service,
        Action("access", ResourceType.SERVICE),
        {"hour": 14}
    )
    print(f"   Access at 14:00: {decision.allowed}")

    # Outside business hours
    decision = await pm.authorize(
        regular_user,
        service,
        Action("access", ResourceType.SERVICE),
        {"hour": 22}
    )
    print(f"   Access at 22:00: {decision.allowed}")
    print()

    # 9. Role Inheritance
    print("9. ROLE INHERITANCE:")
    print("-" * 40)

    mod_user = Subject(
        id="user-mod",
        roles={"moderator"}
    )

    mod_perms = pm.get_role_permissions("moderator")
    print(f"   Moderator permissions: {mod_perms}")

    has_perm = await pm.check_permission(mod_user, "profile:read")
    print(f"   Moderator has 'profile:read' (inherited): {has_perm}")
    print()

    # 10. Audit Log
    print("10. AUDIT LOG:")
    print("-" * 40)

    audit = pm.get_audit_log(limit=5)
    print(f"   Audit entries: {len(audit)}")

    for entry in audit[-3:]:
        print(f"      - {entry.subject_id} -> {entry.action} -> {entry.decision}")
    print()

    # 11. Add Permission to Role
    print("11. MODIFY ROLE:")
    print("-" * 40)

    pm.add_permission_to_role("user", "files:upload")

    new_perms = pm.get_role_permissions("user")
    print(f"   User permissions after add: {new_perms}")
    print()

    # 12. Statistics
    print("12. STATISTICS:")
    print("-" * 40)

    stats = pm.get_stats()

    print(f"   Total policies: {stats['total_policies']}")
    print(f"   Total roles: {stats['total_roles']}")
    print(f"   Audit entries: {stats['audit_entries']}")
    print(f"   Cache size: {stats['cache_size']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Permission Manager System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
