"""
Cost Optimization System for BAEL Phase 2

Implements legitimate free/low-cost API strategies, resource pooling,
and efficient caching to maximize value without paid services.

Key Components:
- API strategy routing (free vs paid)
- Resource pooling and sharing
- Intelligent caching with TTL
- Cost tracking and budgeting
- Efficiency optimization
- Alternative provider strategies
"""

import hashlib
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class APITier(str, Enum):
    """API availability tiers."""
    FREE = "free"  # No cost
    FREEMIUM = "freemium"  # Limited free with paid options
    QUOTA = "quota"  # Limited requests per period
    PAID = "paid"  # Requires payment


class ResourceType(str, Enum):
    """Types of resources that have costs."""
    API_CALL = "api_call"
    COMPUTE = "compute"
    MEMORY = "memory"
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"
    MODEL_INFERENCE = "model_inference"


@dataclass
class APIProvider:
    """Definition of API provider with cost info."""
    provider_id: str
    name: str
    endpoint: str
    tier: APITier
    rate_limit: int  # Requests per hour
    cost_per_request: float  # 0.0 for free
    monthly_quota: int  # -1 for unlimited
    available_credits: float = 0.0
    refresh_date: Optional[datetime] = None  # When quota resets
    reliability: float = 0.95  # Uptime %
    latency_ms: float = 100.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_available(self) -> bool:
        """Check if API is available for use."""
        if self.tier == APITier.FREE:
            return True
        if self.cost_per_request > 0 and self.available_credits <= 0:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "provider_id": self.provider_id,
            "name": self.name,
            "tier": self.tier.value,
            "rate_limit": self.rate_limit,
            "cost_per_request": self.cost_per_request,
            "monthly_quota": self.monthly_quota,
            "available_credits": self.available_credits,
            "reliability": self.reliability,
            "latency_ms": self.latency_ms,
        }


@dataclass
class CostEntry:
    """Record of resource cost."""
    resource_type: ResourceType
    provider_id: str
    amount: float  # Units consumed
    cost: float  # Monetary cost
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "resource_type": self.resource_type.value,
            "provider_id": self.provider_id,
            "amount": self.amount,
            "cost": self.cost,
            "timestamp": self.timestamp.isoformat(),
        }


class FreeResourcePool:
    """Manages free resources and quotas."""

    def __init__(self):
        """Initialize resource pool."""
        self.providers: Dict[str, APIProvider] = {}
        self.usage: Dict[str, int] = defaultdict(int)
        self.reset_times: Dict[str, datetime] = {}

    def register_provider(self, provider: APIProvider) -> None:
        """Register free API provider."""
        self.providers[provider.provider_id] = provider
        logger.info(f"Registered free provider: {provider.name}")

    def get_available_providers(
        self,
        resource_type: ResourceType,
    ) -> List[APIProvider]:
        """Get available providers for resource type."""
        available = []

        for provider in self.providers.values():
            if not provider.is_available():
                continue

            # Check if provider has remaining quota
            usage_key = f"{provider.provider_id}_{resource_type.value}"
            if provider.monthly_quota > 0:
                if self.usage[usage_key] >= provider.monthly_quota:
                    continue

            available.append(provider)

        # Sort by reliability and latency
        available.sort(
            key=lambda p: (-p.reliability, p.latency_ms),
        )
        return available

    def record_usage(
        self,
        provider_id: str,
        resource_type: ResourceType,
        amount: int = 1,
    ) -> bool:
        """Record resource usage."""
        provider = self.providers.get(provider_id)
        if not provider:
            return False

        usage_key = f"{provider_id}_{resource_type.value}"
        self.usage[usage_key] += amount

        return True

    def get_usage_stats(self, provider_id: str) -> Dict[str, Any]:
        """Get usage statistics for provider."""
        provider = self.providers.get(provider_id)
        if not provider:
            return {}

        usage_summary = {}
        for resource_type in ResourceType:
            key = f"{provider_id}_{resource_type.value}"
            usage_summary[resource_type.value] = self.usage.get(key, 0)

        return {
            "provider_id": provider_id,
            "provider_name": provider.name,
            "usage": usage_summary,
            "quota_remaining": max(0, provider.monthly_quota - sum(usage_summary.values())),
        }


class CostBudget:
    """Manages cost budgets and limits."""

    def __init__(self, monthly_budget: float = 0.0):
        """Initialize budget."""
        self.monthly_budget = monthly_budget  # 0 means free-only strategy
        self.spent_this_month = 0.0
        self.cost_entries: List[CostEntry] = []
        self.budget_alerts = []

    def add_cost(self, entry: CostEntry) -> None:
        """Record cost."""
        self.cost_entries.append(entry)
        self.spent_this_month += entry.cost

        # Check budget
        if self.monthly_budget > 0:
            remaining = self.monthly_budget - self.spent_this_month
            if remaining < self.monthly_budget * 0.1:  # Less than 10% remaining
                self.budget_alerts.append({
                    "timestamp": datetime.now(),
                    "message": f"Budget warning: only {remaining:.2f} remaining",
                    "severity": "high" if remaining < 0 else "medium",
                })

    def can_afford(self, cost: float) -> bool:
        """Check if cost can be afforded."""
        if self.monthly_budget <= 0:
            return False  # No budget for paid services

        return self.spent_this_month + cost <= self.monthly_budget

    def get_stats(self) -> Dict[str, Any]:
        """Get budget statistics."""
        return {
            "monthly_budget": self.monthly_budget,
            "spent": self.spent_this_month,
            "remaining": max(0, self.monthly_budget - self.spent_this_month),
            "percentage_used": (self.spent_this_month / self.monthly_budget * 100)
            if self.monthly_budget > 0 else 0,
            "num_alerts": len(self.budget_alerts),
        }


class CachingStrategy:
    """Optimizes caching to reduce API calls."""

    def __init__(self, max_age_hours: int = 24):
        """Initialize caching strategy."""
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.max_age = timedelta(hours=max_age_hours)
        self.hit_count = 0
        self.miss_count = 0

    def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.max_age:
                self.hit_count += 1
                return value
            else:
                del self.cache[key]  # Expired

        self.miss_count += 1
        return None

    def set(self, key: str, value: Any) -> None:
        """Cache value."""
        self.cache[key] = (value, datetime.now())

    def get_hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cached_items": len(self.cache),
            "hits": self.hit_count,
            "misses": self.miss_count,
            "hit_rate": self.get_hit_rate(),
            "max_age_hours": self.max_age.total_seconds() / 3600,
        }


class AlternativeProviderFinder:
    """Finds alternative providers when primary is unavailable."""

    def __init__(self, resource_pool: FreeResourcePool):
        """Initialize finder."""
        self.resource_pool = resource_pool
        self.provider_alternatives: Dict[str, List[str]] = {}  # provider -> alternatives

    def register_alternative(self, primary: str, alternative: str) -> None:
        """Register alternative provider."""
        if primary not in self.provider_alternatives:
            self.provider_alternatives[primary] = []
        self.provider_alternatives[primary].append(alternative)

    def find_alternative(self, primary_provider_id: str) -> Optional[APIProvider]:
        """Find alternative when primary unavailable."""
        alternatives = self.provider_alternatives.get(primary_provider_id, [])

        for alt_id in alternatives:
            provider = self.resource_pool.providers.get(alt_id)
            if provider and provider.is_available():
                logger.info(
                    f"Using alternative: {provider.name} for {primary_provider_id}"
                )
                return provider

        return None

    def find_best_alternative(
        self,
        primary_provider_id: str,
        resource_type: ResourceType,
    ) -> Optional[APIProvider]:
        """Find best alternative provider."""
        available = self.resource_pool.get_available_providers(resource_type)

        if not available:
            return None

        # Return highest reliability option
        return max(available, key=lambda p: p.reliability)


class CostOptimizer:
    """Main cost optimization engine."""

    def __init__(self, monthly_budget: float = 0.0):
        """Initialize optimizer."""
        self.resource_pool = FreeResourcePool()
        self.budget = CostBudget(monthly_budget)
        self.cache = CachingStrategy()
        self.alt_finder = AlternativeProviderFinder(self.resource_pool)
        self.optimization_strategies = {}

    def register_free_provider(self, provider: APIProvider) -> None:
        """Register free API provider."""
        self.resource_pool.register_provider(provider)

    def register_alternative_provider(self, primary_id: str, alt_id: str) -> None:
        """Register alternative provider relationship."""
        self.alt_finder.register_alternative(primary_id, alt_id)

    def get_optimal_provider(
        self,
        resource_type: ResourceType,
        required_latency: float = 1000.0,  # milliseconds
    ) -> Optional[APIProvider]:
        """
        Get optimal provider for resource.

        Prioritizes:
        1. Cache hit if available
        2. Free providers with available quota
        3. Alternative providers
        4. Paid providers (if budget allows)
        """
        # Get available free providers
        free_providers = self.resource_pool.get_available_providers(resource_type)

        # Filter by latency requirement
        suitable = [p for p in free_providers if p.latency_ms <= required_latency]

        if suitable:
            # Return most reliable
            return max(suitable, key=lambda p: p.reliability)

        # No suitable free provider, try alternatives
        if free_providers:
            primary = free_providers[0]
            alt = self.alt_finder.find_best_alternative(primary.provider_id, resource_type)
            if alt:
                return alt

        return None

    def estimate_cost(
        self,
        provider_id: str,
        resource_amount: float,
    ) -> float:
        """Estimate cost of resource usage."""
        provider = self.resource_pool.providers.get(provider_id)
        if not provider:
            return 0.0

        return resource_amount * provider.cost_per_request

    def optimize_request(
        self,
        resource_type: ResourceType,
        request_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Optimize request for cost efficiency.

        Returns optimized request with suggested provider.
        """
        # Check cache first
        cache_key = self._generate_cache_key(resource_type, request_data)
        cached_result = self.cache.get(cache_key)

        if cached_result:
            return {
                "provider": "cache",
                "result": cached_result,
                "cost": 0.0,
                "cached": True,
            }

        # Find optimal provider
        provider = self.get_optimal_provider(resource_type)

        if not provider:
            return {
                "provider": None,
                "result": None,
                "cost": 0.0,
                "error": "No suitable provider found",
            }

        cost = self.estimate_cost(provider.provider_id, 1.0)

        return {
            "provider": provider.to_dict(),
            "cost": cost,
            "cached": False,
            "can_afford": self.budget.can_afford(cost) if cost > 0 else True,
        }

    def get_optimization_report(self) -> Dict[str, Any]:
        """Get optimization effectiveness report."""
        return {
            "budget": self.budget.get_stats(),
            "cache": self.cache.get_stats(),
            "providers": {
                pid: self.resource_pool.get_usage_stats(pid)
                for pid in self.resource_pool.providers
            },
            "total_saved_by_cache": self.cache.hit_count * 0.10,  # Rough estimate
        }

    def _generate_cache_key(
        self,
        resource_type: ResourceType,
        request_data: Dict[str, Any],
    ) -> str:
        """Generate cache key for request."""
        combined = f"{resource_type.value}_{json.dumps(request_data, sort_keys=True)}"
        return hashlib.md5(combined.encode()).hexdigest()


# Global cost optimizer
_optimizer = None


def get_cost_optimizer(monthly_budget: float = 0.0) -> CostOptimizer:
    """Get or create global cost optimizer."""
    global _optimizer
    if _optimizer is None:
        _optimizer = CostOptimizer(monthly_budget)
    return _optimizer
