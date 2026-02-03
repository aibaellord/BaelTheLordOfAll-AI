"""
Advanced Governance System - Policy engine for organizational rules.

Features:
- Policy definition and enforcement
- Data access controls
- Model usage quotas
- Cost controls and budget alerts
- Compliance monitoring
- Audit logging

Target: 1,200+ lines for complete governance
"""

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

# ============================================================================
# GOVERNANCE ENUMS
# ============================================================================

class PolicyType(Enum):
    """Type of governance policy."""
    ACCESS_CONTROL = "ACCESS_CONTROL"
    USAGE_QUOTA = "USAGE_QUOTA"
    COST_LIMIT = "COST_LIMIT"
    COMPLIANCE = "COMPLIANCE"
    DATA_CLASSIFICATION = "DATA_CLASSIFICATION"

class AccessLevel(Enum):
    """Access permission levels."""
    NONE = "NONE"
    READ = "READ"
    WRITE = "WRITE"
    ADMIN = "ADMIN"

class PolicyAction(Enum):
    """Actions taken when policy violated."""
    ALLOW = "ALLOW"
    DENY = "DENY"
    WARN = "WARN"
    THROTTLE = "THROTTLE"
    AUDIT = "AUDIT"

class ComplianceStandard(Enum):
    """Compliance standards."""
    GDPR = "GDPR"
    HIPAA = "HIPAA"
    SOC2 = "SOC2"
    ISO27001 = "ISO27001"
    CCPA = "CCPA"

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Policy:
    """Governance policy definition."""
    policy_id: str
    name: str
    policy_type: PolicyType
    description: str

    # Conditions
    applies_to: List[str] = field(default_factory=list)  # Users, groups, resources
    conditions: Dict[str, Any] = field(default_factory=dict)

    # Action
    action: PolicyAction = PolicyAction.DENY

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    enabled: bool = True
    priority: int = 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            'policy_id': self.policy_id,
            'name': self.name,
            'type': self.policy_type.value,
            'action': self.action.value,
            'enabled': self.enabled,
            'priority': self.priority
        }

@dataclass
class AccessRequest:
    """Request for resource access."""
    request_id: str
    user_id: str
    resource: str
    action: str
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PolicyDecision:
    """Decision from policy evaluation."""
    request_id: str
    decision: PolicyAction
    policies_applied: List[str]
    reason: str = ""
    warnings: List[str] = field(default_factory=list)

@dataclass
class UsageQuota:
    """Usage quota definition."""
    quota_id: str
    resource_type: str
    limit: float
    period: str  # "daily", "monthly", etc.
    applies_to: List[str]
    current_usage: float = 0.0

    def is_exceeded(self) -> bool:
        return self.current_usage >= self.limit

    def remaining(self) -> float:
        return max(0, self.limit - self.current_usage)

@dataclass
class CostBudget:
    """Cost budget and limits."""
    budget_id: str
    name: str
    limit_usd: float
    period: str
    current_spend: float = 0.0
    alert_threshold: float = 0.8  # Alert at 80%

    def is_exceeded(self) -> bool:
        return self.current_spend >= self.limit_usd

    def is_near_limit(self) -> bool:
        return self.current_spend >= (self.limit_usd * self.alert_threshold)

    def remaining(self) -> float:
        return max(0, self.limit_usd - self.current_spend)

# ============================================================================
# POLICY ENGINE
# ============================================================================

class PolicyEngine:
    """Evaluate and enforce policies."""

    def __init__(self):
        self.policies: Dict[str, Policy] = {}
        self.logger = logging.getLogger("policy_engine")

    def add_policy(self, policy: Policy) -> None:
        """Add policy to engine."""
        self.policies[policy.policy_id] = policy
        self.logger.info(f"Added policy: {policy.name}")

    def remove_policy(self, policy_id: str) -> bool:
        """Remove policy."""
        if policy_id in self.policies:
            del self.policies[policy_id]
            return True
        return False

    async def evaluate_request(self, request: AccessRequest) -> PolicyDecision:
        """Evaluate access request against policies."""
        # Get applicable policies
        applicable = self._get_applicable_policies(request)

        if not applicable:
            return PolicyDecision(
                request_id=request.request_id,
                decision=PolicyAction.ALLOW,
                policies_applied=[],
                reason="No applicable policies"
            )

        # Sort by priority
        applicable.sort(key=lambda p: p.priority)

        # Evaluate policies
        decision = PolicyAction.ALLOW
        applied_policies = []
        warnings = []
        reason = ""

        for policy in applicable:
            if not policy.enabled:
                continue

            # Check conditions
            if self._check_conditions(policy, request):
                applied_policies.append(policy.policy_id)

                if policy.action == PolicyAction.DENY:
                    decision = PolicyAction.DENY
                    reason = f"Denied by policy: {policy.name}"
                    break

                elif policy.action == PolicyAction.WARN:
                    warnings.append(f"Warning from policy: {policy.name}")

                elif policy.action == PolicyAction.THROTTLE:
                    warnings.append(f"Throttled by policy: {policy.name}")

        return PolicyDecision(
            request_id=request.request_id,
            decision=decision,
            policies_applied=applied_policies,
            reason=reason or "Allowed",
            warnings=warnings
        )

    def _get_applicable_policies(self, request: AccessRequest) -> List[Policy]:
        """Get policies applicable to request."""
        applicable = []

        for policy in self.policies.values():
            # Check if applies to user
            if policy.applies_to:
                if request.user_id in policy.applies_to:
                    applicable.append(policy)
                elif request.resource in policy.applies_to:
                    applicable.append(policy)
            else:
                # Applies to all if no specific targets
                applicable.append(policy)

        return applicable

    def _check_conditions(self, policy: Policy, request: AccessRequest) -> bool:
        """Check if policy conditions are met."""
        if not policy.conditions:
            return True

        # Check resource patterns
        if 'resource_pattern' in policy.conditions:
            pattern = policy.conditions['resource_pattern']
            if pattern not in request.resource:
                return False

        # Check time restrictions
        if 'time_restriction' in policy.conditions:
            restriction = policy.conditions['time_restriction']
            current_hour = datetime.now().hour

            if 'start_hour' in restriction and current_hour < restriction['start_hour']:
                return False
            if 'end_hour' in restriction and current_hour > restriction['end_hour']:
                return False

        return True

# ============================================================================
# ACCESS CONTROL
# ============================================================================

class AccessControl:
    """Manage access control lists."""

    def __init__(self):
        self.acls: Dict[str, Dict[str, AccessLevel]] = defaultdict(dict)
        self.logger = logging.getLogger("access_control")

    def grant_access(self, user_id: str, resource: str, level: AccessLevel) -> None:
        """Grant access to user."""
        self.acls[resource][user_id] = level
        self.logger.info(f"Granted {level.value} access to {user_id} for {resource}")

    def revoke_access(self, user_id: str, resource: str) -> bool:
        """Revoke access."""
        if resource in self.acls and user_id in self.acls[resource]:
            del self.acls[resource][user_id]
            self.logger.info(f"Revoked access for {user_id} from {resource}")
            return True
        return False

    def check_access(self, user_id: str, resource: str, required_level: AccessLevel) -> bool:
        """Check if user has required access level."""
        if resource not in self.acls:
            return False

        user_level = self.acls[resource].get(user_id, AccessLevel.NONE)

        # Access hierarchy: ADMIN > WRITE > READ > NONE
        levels = [AccessLevel.NONE, AccessLevel.READ, AccessLevel.WRITE, AccessLevel.ADMIN]
        return levels.index(user_level) >= levels.index(required_level)

    def get_user_resources(self, user_id: str) -> Dict[str, AccessLevel]:
        """Get all resources user can access."""
        resources = {}
        for resource, users in self.acls.items():
            if user_id in users:
                resources[resource] = users[user_id]
        return resources

# ============================================================================
# QUOTA MANAGER
# ============================================================================

class QuotaManager:
    """Manage usage quotas."""

    def __init__(self):
        self.quotas: Dict[str, UsageQuota] = {}
        self.usage_history: List[Dict[str, Any]] = []
        self.logger = logging.getLogger("quota_manager")

    def create_quota(self, resource_type: str, limit: float, period: str,
                    applies_to: List[str]) -> str:
        """Create usage quota."""
        quota_id = f"quota-{uuid.uuid4().hex[:16]}"

        quota = UsageQuota(
            quota_id=quota_id,
            resource_type=resource_type,
            limit=limit,
            period=period,
            applies_to=applies_to
        )

        self.quotas[quota_id] = quota
        self.logger.info(f"Created quota: {resource_type} limit={limit}/{period}")
        return quota_id

    def record_usage(self, user_id: str, resource_type: str, amount: float) -> bool:
        """Record resource usage."""
        # Find applicable quotas
        applicable_quotas = [
            q for q in self.quotas.values()
            if q.resource_type == resource_type and user_id in q.applies_to
        ]

        if not applicable_quotas:
            return True  # No quota limits

        # Check if any quota would be exceeded
        for quota in applicable_quotas:
            if quota.current_usage + amount > quota.limit:
                self.logger.warning(f"Quota exceeded for {user_id}: {resource_type}")
                return False

        # Record usage
        for quota in applicable_quotas:
            quota.current_usage += amount

        self.usage_history.append({
            'user_id': user_id,
            'resource_type': resource_type,
            'amount': amount,
            'timestamp': datetime.now()
        })

        return True

    def get_quota_status(self, user_id: str) -> List[Dict[str, Any]]:
        """Get quota status for user."""
        status = []

        for quota in self.quotas.values():
            if user_id in quota.applies_to:
                status.append({
                    'quota_id': quota.quota_id,
                    'resource_type': quota.resource_type,
                    'limit': quota.limit,
                    'used': quota.current_usage,
                    'remaining': quota.remaining(),
                    'exceeded': quota.is_exceeded()
                })

        return status

# ============================================================================
# COST CONTROLLER
# ============================================================================

class CostController:
    """Control and monitor costs."""

    def __init__(self):
        self.budgets: Dict[str, CostBudget] = {}
        self.cost_events: List[Dict[str, Any]] = []
        self.logger = logging.getLogger("cost_controller")

    def create_budget(self, name: str, limit_usd: float, period: str,
                     alert_threshold: float = 0.8) -> str:
        """Create cost budget."""
        budget_id = f"budget-{uuid.uuid4().hex[:8]}"

        budget = CostBudget(
            budget_id=budget_id,
            name=name,
            limit_usd=limit_usd,
            period=period,
            alert_threshold=alert_threshold
        )

        self.budgets[budget_id] = budget
        self.logger.info(f"Created budget: {name} ${limit_usd}/{period}")
        return budget_id

    def record_cost(self, budget_id: str, amount_usd: float, description: str = "") -> bool:
        """Record cost against budget."""
        if budget_id not in self.budgets:
            return False

        budget = self.budgets[budget_id]

        # Check if would exceed
        if budget.current_spend + amount_usd > budget.limit_usd:
            self.logger.error(f"Budget exceeded: {budget.name}")
            return False

        # Record cost
        budget.current_spend += amount_usd

        self.cost_events.append({
            'budget_id': budget_id,
            'amount': amount_usd,
            'description': description,
            'timestamp': datetime.now()
        })

        # Check for alerts
        if budget.is_near_limit():
            self.logger.warning(f"Budget alert: {budget.name} at {budget.current_spend/budget.limit_usd*100:.1f}%")

        return True

    def get_budget_status(self) -> List[Dict[str, Any]]:
        """Get status of all budgets."""
        return [
            {
                'budget_id': b.budget_id,
                'name': b.name,
                'limit': b.limit_usd,
                'spent': b.current_spend,
                'remaining': b.remaining(),
                'percentage': b.current_spend / b.limit_usd * 100,
                'exceeded': b.is_exceeded(),
                'near_limit': b.is_near_limit()
            }
            for b in self.budgets.values()
        ]

# ============================================================================
# GOVERNANCE SYSTEM
# ============================================================================

class GovernanceSystem:
    """Complete governance system."""

    def __init__(self):
        self.policy_engine = PolicyEngine()
        self.access_control = AccessControl()
        self.quota_manager = QuotaManager()
        self.cost_controller = CostController()
        self.logger = logging.getLogger("governance")

    async def authorize_action(self, user_id: str, resource: str, action: str,
                              context: Optional[Dict[str, Any]] = None) -> PolicyDecision:
        """Authorize user action."""
        # Create request
        request = AccessRequest(
            request_id=f"req-{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            resource=resource,
            action=action,
            context=context or {}
        )

        # Evaluate policies
        decision = await self.policy_engine.evaluate_request(request)

        self.logger.info(f"Authorization decision for {user_id}/{resource}: {decision.decision.value}")
        return decision

    def setup_access_controls(self, acl_config: List[Dict[str, Any]]) -> None:
        """Setup access control lists."""
        for acl in acl_config:
            self.access_control.grant_access(
                user_id=acl['user_id'],
                resource=acl['resource'],
                level=AccessLevel[acl['level']]
            )

    def setup_quotas(self, quota_config: List[Dict[str, Any]]) -> List[str]:
        """Setup usage quotas."""
        quota_ids = []
        for config in quota_config:
            quota_id = self.quota_manager.create_quota(
                resource_type=config['resource_type'],
                limit=config['limit'],
                period=config['period'],
                applies_to=config['applies_to']
            )
            quota_ids.append(quota_id)
        return quota_ids

    def setup_budgets(self, budget_config: List[Dict[str, Any]]) -> List[str]:
        """Setup cost budgets."""
        budget_ids = []
        for config in budget_config:
            budget_id = self.cost_controller.create_budget(
                name=config['name'],
                limit_usd=config['limit_usd'],
                period=config['period'],
                alert_threshold=config.get('alert_threshold', 0.8)
            )
            budget_ids.append(budget_id)
        return budget_ids

    def get_governance_status(self) -> Dict[str, Any]:
        """Get complete governance status."""
        return {
            'policies': len(self.policy_engine.policies),
            'access_controls': sum(len(users) for users in self.access_control.acls.values()),
            'quotas': len(self.quota_manager.quotas),
            'budgets': self.cost_controller.get_budget_status()
        }

def create_governance_system() -> GovernanceSystem:
    """Create governance system."""
    return GovernanceSystem()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    governance = create_governance_system()
    print("Governance system initialized")
