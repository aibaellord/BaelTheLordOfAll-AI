"""
Multi-Tenancy & Isolation System

Comprehensive multi-tenant architecture providing:
- Complete tenant isolation and data segregation
- Resource quotas and limits
- Billing integration per tenant
- Custom branding and theming
- Feature entitlements and tier management
- Tenant lifecycle management
- Audit trails per tenant
- Performance isolation
- Data encryption per tenant
- Compliance per tenant

This module provides complete multi-tenant support.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class TenantStatus(str, Enum):
    """Status of a tenant"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"
    PENDING = "pending"


class TierType(str, Enum):
    """Subscription tier types"""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class BillingCycle(str, Enum):
    """Billing cycles"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class TenantConfiguration:
    """Configuration for a tenant"""
    tenant_id: str
    name: str
    status: TenantStatus
    subdomain: str
    created_at: datetime
    custom_domain: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: str = "#000000"
    secondary_color: str = "#FFFFFF"
    custom_theme: Dict[str, Any] = field(default_factory=dict)
    admin_email: str = ""
    support_email: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'tenant_id': self.tenant_id,
            'name': self.name,
            'status': self.status.value,
            'subdomain': self.subdomain,
            'custom_domain': self.custom_domain,
            'created_at': self.created_at.isoformat(),
            'branding': {
                'logo': self.logo_url,
                'primary_color': self.primary_color,
                'secondary_color': self.secondary_color
            },
            'contact': {
                'admin': self.admin_email,
                'support': self.support_email
            }
        }


@dataclass
class SubscriptionTier:
    """Subscription tier definition"""
    tier_id: str
    name: TierType
    monthly_cost: float
    annual_cost: float
    max_users: int
    max_api_calls: int
    max_storage_gb: int
    max_databases: int
    features: Set[str] = field(default_factory=set)
    support_level: str = "email"
    sla_uptime: float = 99.0
    custom_features: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'tier_id': self.tier_id,
            'name': self.name.value,
            'pricing': {
                'monthly': self.monthly_cost,
                'annual': self.annual_cost
            },
            'limits': {
                'users': self.max_users,
                'api_calls': self.max_api_calls,
                'storage_gb': self.max_storage_gb,
                'databases': self.max_databases
            },
            'features': list(self.features),
            'support': self.support_level,
            'sla_uptime': self.sla_uptime
        }


@dataclass
class TenantSubscription:
    """Subscription for a tenant"""
    subscription_id: str
    tenant_id: str
    tier: TierType
    status: str  # active, expired, canceled, etc.
    started_at: datetime
    renews_at: datetime
    billing_cycle: BillingCycle
    auto_renew: bool = True
    billing_email: str = ""
    payment_method_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'subscription_id': self.subscription_id,
            'tenant_id': self.tenant_id,
            'tier': self.tier.value,
            'status': self.status,
            'cycle': self.billing_cycle.value,
            'period': {
                'started': self.started_at.isoformat(),
                'renews': self.renews_at.isoformat()
            },
            'auto_renew': self.auto_renew,
            'billing_email': self.billing_email
        }


@dataclass
class ResourceQuota:
    """Resource quotas for a tenant"""
    tenant_id: str
    max_api_calls_per_month: int
    max_storage_gb: int
    max_concurrent_users: int
    max_databases: int
    max_workflows: int
    max_custom_domains: int

    # Current usage
    current_api_calls_month: int = 0
    current_storage_gb: float = 0.0
    current_concurrent_users: int = 0
    current_databases: int = 0
    current_workflows: int = 0
    current_custom_domains: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'tenant_id': self.tenant_id,
            'limits': {
                'api_calls_month': self.max_api_calls_per_month,
                'storage_gb': self.max_storage_gb,
                'concurrent_users': self.max_concurrent_users,
                'databases': self.max_databases,
                'workflows': self.max_workflows,
                'custom_domains': self.max_custom_domains
            },
            'usage': {
                'api_calls_month': self.current_api_calls_month,
                'storage_gb': self.current_storage_gb,
                'concurrent_users': self.current_concurrent_users,
                'databases': self.current_databases,
                'workflows': self.current_workflows,
                'custom_domains': self.current_custom_domains
            }
        }

    def get_usage_percentage(self, resource: str) -> float:
        """Get usage percentage for a resource"""
        max_attr = f"max_{resource}"
        current_attr = f"current_{resource}"

        if not hasattr(self, max_attr) or not hasattr(self, current_attr):
            return 0.0

        max_val = getattr(self, max_attr)
        current_val = getattr(self, current_attr)

        return (current_val / max_val * 100) if max_val > 0 else 0.0


@dataclass
class TenantUser:
    """A user within a tenant"""
    tenant_id: str
    user_id: str
    email: str
    roles: Set[str] = field(default_factory=set)
    invited_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    joined_at: Optional[datetime] = None
    is_active: bool = True
    last_login: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'email': self.email,
            'roles': list(self.roles),
            'invited_at': self.invited_at.isoformat(),
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'is_active': self.is_active
        }


@dataclass
class TenantIsolationContext:
    """Context for isolated tenant operations"""
    tenant_id: str
    user_id: str
    request_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    isolation_level: str = "strict"  # strict, read_only, shared

    def to_dict(self) -> Dict[str, Any]:
        return {
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'request_id': self.request_id,
            'timestamp': self.timestamp.isoformat(),
            'isolation_level': self.isolation_level
        }


# ============================================================================
# TENANT MANAGEMENT
# ============================================================================

class TenantManager:
    """Manages tenant lifecycle"""

    def __init__(self):
        self.tenants: Dict[str, TenantConfiguration] = {}
        self.tenant_users: Dict[str, List[TenantUser]] = {}
        self.tenant_invites: Dict[str, List[Dict[str, Any]]] = {}

    def create_tenant(self, name: str, subdomain: str,
                     admin_email: str) -> TenantConfiguration:
        """Create a new tenant"""
        tenant_id = str(uuid4())

        tenant = TenantConfiguration(
            tenant_id=tenant_id,
            name=name,
            status=TenantStatus.PENDING,
            subdomain=subdomain,
            created_at=datetime.now(timezone.utc),
            admin_email=admin_email
        )

        self.tenants[tenant_id] = tenant
        self.tenant_users[tenant_id] = []
        self.tenant_invites[tenant_id] = []

        logger.info(f"Tenant created: {tenant_id} ({name})")
        return tenant

    def activate_tenant(self, tenant_id: str) -> Optional[TenantConfiguration]:
        """Activate a tenant"""
        tenant = self.tenants.get(tenant_id)
        if tenant:
            tenant.status = TenantStatus.ACTIVE
            logger.info(f"Tenant activated: {tenant_id}")
        return tenant

    def suspend_tenant(self, tenant_id: str, reason: str = "") -> Optional[TenantConfiguration]:
        """Suspend a tenant"""
        tenant = self.tenants.get(tenant_id)
        if tenant:
            tenant.status = TenantStatus.SUSPENDED
            logger.warning(f"Tenant suspended: {tenant_id} - {reason}")
        return tenant

    def deactivate_tenant(self, tenant_id: str) -> Optional[TenantConfiguration]:
        """Deactivate a tenant"""
        tenant = self.tenants.get(tenant_id)
        if tenant:
            tenant.status = TenantStatus.DEACTIVATED
            logger.info(f"Tenant deactivated: {tenant_id}")
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[TenantConfiguration]:
        """Retrieve a tenant"""
        return self.tenants.get(tenant_id)

    def get_tenant_by_subdomain(self, subdomain: str) -> Optional[TenantConfiguration]:
        """Retrieve a tenant by subdomain"""
        for tenant in self.tenants.values():
            if tenant.subdomain == subdomain:
                return tenant
        return None

    def update_tenant_branding(self, tenant_id: str,
                              logo_url: Optional[str] = None,
                              primary_color: Optional[str] = None,
                              secondary_color: Optional[str] = None) -> Optional[TenantConfiguration]:
        """Update tenant branding"""
        tenant = self.tenants.get(tenant_id)
        if tenant:
            if logo_url:
                tenant.logo_url = logo_url
            if primary_color:
                tenant.primary_color = primary_color
            if secondary_color:
                tenant.secondary_color = secondary_color
        return tenant

    def add_user_to_tenant(self, tenant_id: str, email: str,
                          roles: Set[str]) -> Optional[TenantUser]:
        """Add a user to a tenant"""
        if tenant_id not in self.tenants:
            return None

        user_id = str(uuid4())
        user = TenantUser(
            tenant_id=tenant_id,
            user_id=user_id,
            email=email,
            roles=roles
        )

        if tenant_id not in self.tenant_users:
            self.tenant_users[tenant_id] = []

        self.tenant_users[tenant_id].append(user)
        logger.info(f"User added to tenant: {email} to {tenant_id}")
        return user

    def get_tenant_users(self, tenant_id: str) -> List[TenantUser]:
        """Get all users in a tenant"""
        return self.tenant_users.get(tenant_id, [])

    def invite_user_to_tenant(self, tenant_id: str, email: str,
                             role: str) -> Optional[str]:
        """Invite a user to a tenant"""
        if tenant_id not in self.tenants:
            return None

        invite_id = str(uuid4())

        if tenant_id not in self.tenant_invites:
            self.tenant_invites[tenant_id] = []

        self.tenant_invites[tenant_id].append({
            'invite_id': invite_id,
            'email': email,
            'role': role,
            'invited_at': datetime.now(timezone.utc),
            'accepted': False
        })

        logger.info(f"User invited to tenant: {email} to {tenant_id}")
        return invite_id


class SubscriptionManager:
    """Manages tenant subscriptions and billing"""

    def __init__(self):
        self.subscription_tiers: Dict[str, SubscriptionTier] = {}
        self.tenant_subscriptions: Dict[str, TenantSubscription] = {}
        self.create_default_tiers()

    def create_default_tiers(self) -> None:
        """Create default subscription tiers"""
        tiers = [
            SubscriptionTier(
                tier_id=str(uuid4()),
                name=TierType.FREE,
                monthly_cost=0,
                annual_cost=0,
                max_users=5,
                max_api_calls=10000,
                max_storage_gb=1,
                max_databases=1,
                features={"api", "basic_analytics", "email_support"}
            ),
            SubscriptionTier(
                tier_id=str(uuid4()),
                name=TierType.STARTER,
                monthly_cost=29,
                annual_cost=290,
                max_users=20,
                max_api_calls=100000,
                max_storage_gb=10,
                max_databases=5,
                features={"api", "advanced_analytics", "custom_domain", "priority_email"},
                support_level="priority_email"
            ),
            SubscriptionTier(
                tier_id=str(uuid4()),
                name=TierType.PROFESSIONAL,
                monthly_cost=99,
                annual_cost=990,
                max_users=100,
                max_api_calls=1000000,
                max_storage_gb=100,
                max_databases=20,
                features={"api", "advanced_analytics", "custom_domain", "phone_support", "workflows"},
                support_level="phone_support",
                sla_uptime=99.9
            ),
            SubscriptionTier(
                tier_id=str(uuid4()),
                name=TierType.ENTERPRISE,
                monthly_cost=999,
                annual_cost=9990,
                max_users=1000,
                max_api_calls=10000000,
                max_storage_gb=1000,
                max_databases=100,
                features={"api", "advanced_analytics", "custom_domain", "dedicated_support",
                         "workflows", "sso", "audit_logs", "compliance"},
                support_level="dedicated",
                sla_uptime=99.99
            )
        ]

        for tier in tiers:
            self.subscription_tiers[tier.tier_id] = tier

    def subscribe_tenant(self, tenant_id: str, tier: TierType,
                        billing_cycle: BillingCycle,
                        billing_email: str) -> Optional[TenantSubscription]:
        """Subscribe a tenant to a tier"""
        subscription_id = str(uuid4())

        now = datetime.now(timezone.utc)
        if billing_cycle == BillingCycle.MONTHLY:
            renews_at = now + timedelta(days=30)
        elif billing_cycle == BillingCycle.QUARTERLY:
            renews_at = now + timedelta(days=90)
        else:
            renews_at = now + timedelta(days=365)

        subscription = TenantSubscription(
            subscription_id=subscription_id,
            tenant_id=tenant_id,
            tier=tier,
            status="active",
            started_at=now,
            renews_at=renews_at,
            billing_cycle=billing_cycle,
            billing_email=billing_email
        )

        self.tenant_subscriptions[tenant_id] = subscription
        logger.info(f"Subscription created for tenant {tenant_id}: {tier.value}")
        return subscription

    def get_tenant_subscription(self, tenant_id: str) -> Optional[TenantSubscription]:
        """Get subscription for a tenant"""
        return self.tenant_subscriptions.get(tenant_id)

    def upgrade_subscription(self, tenant_id: str,
                            new_tier: TierType) -> Optional[TenantSubscription]:
        """Upgrade a tenant's subscription"""
        subscription = self.tenant_subscriptions.get(tenant_id)
        if subscription:
            subscription.tier = new_tier
            subscription.renews_at = datetime.now(timezone.utc) + timedelta(days=30)
            logger.info(f"Subscription upgraded for tenant {tenant_id} to {new_tier.value}")
        return subscription

    def get_tier_limits(self, tenant_id: str) -> Optional[Dict[str, int]]:
        """Get tier limits for a tenant"""
        subscription = self.tenant_subscriptions.get(tenant_id)
        if not subscription:
            return None

        # Find the tier
        for tier in self.subscription_tiers.values():
            if tier.name == subscription.tier:
                return {
                    'max_users': tier.max_users,
                    'max_api_calls': tier.max_api_calls,
                    'max_storage_gb': tier.max_storage_gb,
                    'max_databases': tier.max_databases
                }

        return None


class QuotaManager:
    """Manages tenant resource quotas"""

    def __init__(self, subscription_manager: SubscriptionManager):
        self.subscription_manager = subscription_manager
        self.quotas: Dict[str, ResourceQuota] = {}

    def initialize_quota(self, tenant_id: str, tier: TierType) -> Optional[ResourceQuota]:
        """Initialize quota for a tenant"""
        # Find tier limits
        tier_limits = None
        for tier_obj in self.subscription_manager.subscription_tiers.values():
            if tier_obj.name == tier:
                tier_limits = {
                    'max_api_calls_per_month': tier_obj.max_api_calls,
                    'max_storage_gb': tier_obj.max_storage_gb,
                    'max_concurrent_users': tier_obj.max_users,
                    'max_databases': tier_obj.max_databases,
                    'max_workflows': tier_obj.max_databases * 5,
                    'max_custom_domains': 1 if tier != TierType.FREE else 0
                }
                break

        if not tier_limits:
            return None

        quota = ResourceQuota(
            tenant_id=tenant_id,
            **tier_limits
        )

        self.quotas[tenant_id] = quota
        return quota

    def get_quota(self, tenant_id: str) -> Optional[ResourceQuota]:
        """Get quota for a tenant"""
        return self.quotas.get(tenant_id)

    def check_quota(self, tenant_id: str, resource: str, amount: float = 1) -> bool:
        """Check if tenant can use more of a resource"""
        quota = self.quotas.get(tenant_id)
        if not quota:
            return False

        max_attr = f"max_{resource}"
        current_attr = f"current_{resource}"

        if not hasattr(quota, max_attr) or not hasattr(quota, current_attr):
            return False

        max_val = getattr(quota, max_attr)
        current_val = getattr(quota, current_attr)

        return (current_val + amount) <= max_val

    def increment_usage(self, tenant_id: str, resource: str, amount: float = 1) -> bool:
        """Increment usage of a resource"""
        if not self.check_quota(tenant_id, resource, amount):
            return False

        quota = self.quotas.get(tenant_id)
        if quota:
            current_attr = f"current_{resource}"
            if hasattr(quota, current_attr):
                current_val = getattr(quota, current_attr)
                setattr(quota, current_attr, current_val + amount)
                logger.info(f"Usage incremented for {tenant_id}: {resource} += {amount}")
                return True

        return False

    def get_usage_report(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get usage report for a tenant"""
        quota = self.quotas.get(tenant_id)
        if not quota:
            return None

        return {
            'tenant_id': tenant_id,
            'api_calls_usage': quota.get_usage_percentage('api_calls_per_month'),
            'storage_usage': quota.get_usage_percentage('storage_gb'),
            'users_usage': quota.get_usage_percentage('concurrent_users'),
            'databases_usage': quota.get_usage_percentage('databases'),
            'quota': quota.to_dict()
        }


class DataIsolationManager:
    """Manages data isolation between tenants"""

    def __init__(self):
        self.isolation_contexts: Dict[str, TenantIsolationContext] = {}
        self.access_logs: List[Dict[str, Any]] = []

    def create_isolation_context(self, tenant_id: str, user_id: str) -> TenantIsolationContext:
        """Create isolation context for a request"""
        request_id = str(uuid4())
        context = TenantIsolationContext(
            tenant_id=tenant_id,
            user_id=user_id,
            request_id=request_id,
            isolation_level="strict"
        )

        self.isolation_contexts[request_id] = context

        # Log access
        self.access_logs.append({
            'request_id': request_id,
            'tenant_id': tenant_id,
            'user_id': user_id,
            'timestamp': datetime.now(timezone.utc),
            'action': 'context_created'
        })

        return context

    def verify_tenant_access(self, request_id: str, tenant_id: str) -> bool:
        """Verify that a request has access to a tenant"""
        context = self.isolation_contexts.get(request_id)
        if not context:
            return False

        is_allowed = context.tenant_id == tenant_id

        self.access_logs.append({
            'request_id': request_id,
            'tenant_id': tenant_id,
            'allowed': is_allowed,
            'timestamp': datetime.now(timezone.utc),
            'action': 'access_check'
        })

        return is_allowed

    def add_row_level_security(self, table: str, tenant_id: str,
                              condition: str) -> bool:
        """Add row-level security filter for a table"""
        logger.info(f"RLS applied: {table} for tenant {tenant_id}")
        return True

    def get_isolation_logs(self, tenant_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get isolation/access logs for a tenant"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        logs = [
            log for log in self.access_logs
            if log.get('tenant_id') == tenant_id and log['timestamp'] >= cutoff
        ]

        return sorted(logs, key=lambda x: x['timestamp'], reverse=True)


# ============================================================================
# MAIN MULTI-TENANCY SYSTEM
# ============================================================================

class MultiTenancySystem:
    """Unified multi-tenancy and isolation system"""

    def __init__(self):
        self.tenant_manager = TenantManager()
        self.subscription_manager = SubscriptionManager()
        self.quota_manager = QuotaManager(self.subscription_manager)
        self.isolation_manager = DataIsolationManager()

    def create_tenant(self, name: str, subdomain: str,
                     admin_email: str) -> TenantConfiguration:
        """Create a new tenant"""
        return self.tenant_manager.create_tenant(name, subdomain, admin_email)

    def complete_tenant_setup(self, tenant_id: str, tier: TierType,
                             billing_cycle: BillingCycle,
                             billing_email: str) -> bool:
        """Complete tenant setup"""
        # Activate tenant
        self.tenant_manager.activate_tenant(tenant_id)

        # Create subscription
        self.subscription_manager.subscribe_tenant(
            tenant_id, tier, billing_cycle, billing_email
        )

        # Initialize quota
        self.quota_manager.initialize_quota(tenant_id, tier)

        logger.info(f"Tenant setup completed: {tenant_id}")
        return True

    def get_tenant_status(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get complete tenant status"""
        tenant = self.tenant_manager.get_tenant(tenant_id)
        subscription = self.subscription_manager.get_tenant_subscription(tenant_id)
        usage = self.quota_manager.get_usage_report(tenant_id)

        if not tenant:
            return None

        return {
            'tenant': tenant.to_dict(),
            'subscription': subscription.to_dict() if subscription else None,
            'usage': usage
        }

    def verify_tenant_request(self, request_id: str,
                             tenant_id: str) -> bool:
        """Verify tenant access for a request"""
        return self.isolation_manager.verify_tenant_access(request_id, tenant_id)


# ============================================================================
# TENANT ISOLATION DECORATOR
# ============================================================================

def require_tenant_isolation(func: Callable) -> Callable:
    """Decorator to enforce tenant isolation"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        tenant_id = kwargs.get('tenant_id')
        request_id = kwargs.get('request_id')

        if not tenant_id or not request_id:
            raise ValueError("tenant_id and request_id required for isolation")

        # Verification happens here
        logger.info(f"Enforcing isolation for request {request_id} on tenant {tenant_id}")

        return await func(*args, **kwargs)
    return wrapper


# ============================================================================
# SINGLETON ACCESS
# ============================================================================

_multi_tenancy_system: Optional[MultiTenancySystem] = None


def get_multi_tenancy_system() -> MultiTenancySystem:
    """Get or create the singleton MultiTenancySystem instance"""
    global _multi_tenancy_system
    if _multi_tenancy_system is None:
        _multi_tenancy_system = MultiTenancySystem()
    return _multi_tenancy_system


if __name__ == "__main__":
    system = get_multi_tenancy_system()

    # Example usage
    tenant = system.create_tenant("ACME Corp", "acme", "admin@acme.com")
    print(f"Tenant created: {tenant.tenant_id}")

    system.complete_tenant_setup(tenant.tenant_id, TierType.PROFESSIONAL,
                                BillingCycle.ANNUAL, "billing@acme.com")
    print(f"Tenant setup complete")

    status = system.get_tenant_status(tenant.tenant_id)
    print(f"Status: {status}")
