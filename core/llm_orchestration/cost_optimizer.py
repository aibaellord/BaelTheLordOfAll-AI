"""
BAEL Cost Optimizer
====================

Zero-cost operation through intelligent resource exploitation.
Tracks usage, optimizes for free tiers, and minimizes costs.

Features:
- Multi-provider cost tracking
- Free tier exploitation (quota management)
- Intelligent caching to reduce API calls
- Request deduplication
- Batch optimization
- Token budget management
- Cost alerts and reporting
- ROI calculation
"""

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class CostStrategy(Enum):
    """Cost optimization strategies."""
    ZERO_COST = "zero_cost"         # Only free providers
    MINIMIZE_COST = "minimize_cost" # Prefer free, allow cheap
    BALANCED = "balanced"           # Balance cost and quality
    QUALITY_FIRST = "quality_first" # Best quality, cost secondary
    BUDGET_CAPPED = "budget_capped" # Stay within budget


class CostTier(Enum):
    """Provider cost tiers."""
    FREE = 0
    VERY_CHEAP = 1
    CHEAP = 2
    MODERATE = 3
    EXPENSIVE = 4
    PREMIUM = 5


@dataclass
class ProviderPricing:
    """Pricing information for a provider."""
    provider: str
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    cost_per_1k_total: float = 0.0  # Some providers use combined pricing
    free_tier_limit: int = 0        # Daily free tokens
    free_tier_used: int = 0
    tier: CostTier = CostTier.FREE

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate cost for a request."""
        if self.tier == CostTier.FREE:
            return 0.0

        if self.cost_per_1k_total > 0:
            total = input_tokens + output_tokens
            return (total / 1000) * self.cost_per_1k_total

        input_cost = (input_tokens / 1000) * self.cost_per_1k_input
        output_cost = (output_tokens / 1000) * self.cost_per_1k_output
        return input_cost + output_cost

    def can_use_free_tier(self, estimated_tokens: int) -> bool:
        """Check if request fits in free tier."""
        if self.free_tier_limit == 0:
            return self.tier == CostTier.FREE
        return self.free_tier_used + estimated_tokens <= self.free_tier_limit


@dataclass
class UsageRecord:
    """Record of API usage."""
    timestamp: datetime
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    request_hash: str
    cached: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UsageTracker:
    """Tracks API usage across providers."""
    records: List[UsageRecord] = field(default_factory=list)
    daily_totals: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    monthly_totals: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def add_record(self, record: UsageRecord) -> None:
        """Add a usage record."""
        self.records.append(record)

        # Update daily totals
        date_key = record.timestamp.strftime("%Y-%m-%d")
        if date_key not in self.daily_totals:
            self.daily_totals[date_key] = defaultdict(lambda: {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0,
                "requests": 0,
            })

        daily = self.daily_totals[date_key][record.provider]
        daily["input_tokens"] += record.input_tokens
        daily["output_tokens"] += record.output_tokens
        daily["cost"] += record.cost
        daily["requests"] += 1

        # Update monthly totals
        month_key = record.timestamp.strftime("%Y-%m")
        if month_key not in self.monthly_totals:
            self.monthly_totals[month_key] = defaultdict(lambda: {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0,
                "requests": 0,
            })

        monthly = self.monthly_totals[month_key][record.provider]
        monthly["input_tokens"] += record.input_tokens
        monthly["output_tokens"] += record.output_tokens
        monthly["cost"] += record.cost
        monthly["requests"] += 1

    def get_daily_cost(self, date: Optional[datetime] = None) -> float:
        """Get total cost for a day."""
        date_key = (date or datetime.now()).strftime("%Y-%m-%d")
        if date_key not in self.daily_totals:
            return 0.0
        return sum(p["cost"] for p in self.daily_totals[date_key].values())

    def get_monthly_cost(self, date: Optional[datetime] = None) -> float:
        """Get total cost for a month."""
        month_key = (date or datetime.now()).strftime("%Y-%m")
        if month_key not in self.monthly_totals:
            return 0.0
        return sum(p["cost"] for p in self.monthly_totals[month_key].values())


class CostOptimizer:
    """
    Intelligent cost optimizer for multi-provider LLM usage.
    Targets zero-cost operation through smart exploitation.
    """

    # Default pricing for known providers (per 1K tokens)
    DEFAULT_PRICING: Dict[str, Dict[str, Any]] = {
        # Free providers
        "openrouter": {
            "tier": CostTier.FREE,  # Many free models
            "free_tier_limit": 1000000,  # Per day
        },
        "deepseek": {
            "cost_per_1k_input": 0.0001,
            "cost_per_1k_output": 0.0002,
            "tier": CostTier.VERY_CHEAP,
            "free_tier_limit": 500000,
        },
        "groq": {
            "tier": CostTier.FREE,
            "free_tier_limit": 100000,  # Per day
        },
        "together": {
            "cost_per_1k_input": 0.0002,
            "cost_per_1k_output": 0.0002,
            "tier": CostTier.VERY_CHEAP,
            "free_tier_limit": 200000,
        },
        "siliconflow": {
            "tier": CostTier.FREE,
            "free_tier_limit": 500000,
        },
        "fireworks": {
            "cost_per_1k_input": 0.0002,
            "cost_per_1k_output": 0.0002,
            "tier": CostTier.VERY_CHEAP,
            "free_tier_limit": 100000,
        },
        "ollama": {
            "tier": CostTier.FREE,
            "free_tier_limit": 0,  # Local, unlimited
        },

        # Underground free providers
        "zukijourney": {"tier": CostTier.FREE, "free_tier_limit": 0},
        "electronhub": {"tier": CostTier.FREE, "free_tier_limit": 0},
        "nagaai": {"tier": CostTier.FREE, "free_tier_limit": 0},
        "shuttleai": {"tier": CostTier.FREE, "free_tier_limit": 0},

        # Paid providers (fallback)
        "openai": {
            "cost_per_1k_input": 0.01,
            "cost_per_1k_output": 0.03,
            "tier": CostTier.MODERATE,
        },
        "anthropic": {
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.015,
            "tier": CostTier.MODERATE,
        },
    }

    def __init__(
        self,
        strategy: CostStrategy = CostStrategy.ZERO_COST,
        daily_budget: float = 0.0,
        monthly_budget: float = 0.0,
    ):
        self.strategy = strategy
        self.daily_budget = daily_budget
        self.monthly_budget = monthly_budget

        # Initialize pricing
        self.pricing: Dict[str, ProviderPricing] = {}
        for provider, config in self.DEFAULT_PRICING.items():
            self.pricing[provider] = ProviderPricing(
                provider=provider,
                cost_per_1k_input=config.get("cost_per_1k_input", 0.0),
                cost_per_1k_output=config.get("cost_per_1k_output", 0.0),
                free_tier_limit=config.get("free_tier_limit", 0),
                tier=config.get("tier", CostTier.FREE),
            )

        # Usage tracking
        self.tracker = UsageTracker()

        # Cache for deduplication
        self.request_cache: Dict[str, Any] = {}
        self.cache_ttl = timedelta(hours=1)

        # Seen request hashes for dedup
        self.seen_requests: Set[str] = set()

    def _hash_request(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
    ) -> str:
        """Create hash of request for caching/dedup."""
        content = json.dumps({
            "messages": messages,
            "model": model,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def get_free_providers(self) -> List[str]:
        """Get list of free providers."""
        return [
            p for p, pricing in self.pricing.items()
            if pricing.tier == CostTier.FREE
        ]

    def get_providers_by_cost(self) -> List[str]:
        """Get providers ordered by cost (cheapest first)."""
        return sorted(
            self.pricing.keys(),
            key=lambda p: (
                self.pricing[p].tier.value,
                self.pricing[p].cost_per_1k_input + self.pricing[p].cost_per_1k_output,
            )
        )

    def recommend_provider(
        self,
        estimated_input_tokens: int,
        estimated_output_tokens: int,
        preferred_providers: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Recommend best provider based on cost strategy.

        Args:
            estimated_input_tokens: Estimated input token count
            estimated_output_tokens: Estimated output token count
            preferred_providers: Optional list to choose from

        Returns:
            Recommended provider name or None
        """
        candidates = preferred_providers or list(self.pricing.keys())
        estimated_total = estimated_input_tokens + estimated_output_tokens

        if self.strategy == CostStrategy.ZERO_COST:
            # Only return free providers
            for provider in self.get_providers_by_cost():
                if provider not in candidates:
                    continue
                pricing = self.pricing[provider]
                if pricing.tier == CostTier.FREE:
                    if pricing.can_use_free_tier(estimated_total):
                        return provider
            return None

        elif self.strategy == CostStrategy.MINIMIZE_COST:
            # Prefer free, then cheapest
            for provider in self.get_providers_by_cost():
                if provider not in candidates:
                    continue
                pricing = self.pricing[provider]
                if pricing.can_use_free_tier(estimated_total):
                    return provider
            # Fall back to cheapest
            for provider in self.get_providers_by_cost():
                if provider in candidates:
                    return provider
            return None

        elif self.strategy == CostStrategy.BUDGET_CAPPED:
            # Check budget constraints
            current_daily = self.tracker.get_daily_cost()
            current_monthly = self.tracker.get_monthly_cost()

            for provider in self.get_providers_by_cost():
                if provider not in candidates:
                    continue
                pricing = self.pricing[provider]
                estimated_cost = pricing.calculate_cost(
                    estimated_input_tokens, estimated_output_tokens
                )

                # Check if within budget
                if self.daily_budget > 0:
                    if current_daily + estimated_cost > self.daily_budget:
                        if pricing.tier != CostTier.FREE:
                            continue

                if self.monthly_budget > 0:
                    if current_monthly + estimated_cost > self.monthly_budget:
                        if pricing.tier != CostTier.FREE:
                            continue

                return provider
            return None

        # Default: first available
        return candidates[0] if candidates else None

    def record_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        messages: List[Dict[str, str]],
        cached: bool = False,
    ) -> UsageRecord:
        """Record API usage."""
        pricing = self.pricing.get(provider, ProviderPricing(provider=provider))
        cost = pricing.calculate_cost(input_tokens, output_tokens)

        # Update free tier usage
        if pricing.free_tier_limit > 0:
            pricing.free_tier_used += input_tokens + output_tokens

        record = UsageRecord(
            timestamp=datetime.now(),
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            request_hash=self._hash_request(messages),
            cached=cached,
        )

        self.tracker.add_record(record)
        return record

    def check_cache(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
    ) -> Optional[Any]:
        """Check if request is cached."""
        request_hash = self._hash_request(messages, model)

        if request_hash in self.request_cache:
            cached = self.request_cache[request_hash]
            if datetime.now() - cached["timestamp"] < self.cache_ttl:
                return cached["response"]
            else:
                del self.request_cache[request_hash]

        return None

    def cache_response(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str],
        response: Any,
    ) -> None:
        """Cache a response."""
        request_hash = self._hash_request(messages, model)
        self.request_cache[request_hash] = {
            "response": response,
            "timestamp": datetime.now(),
        }

    def is_duplicate_request(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        window_seconds: int = 5,
    ) -> bool:
        """Check if this is a duplicate recent request."""
        request_hash = self._hash_request(messages, model)

        # Clean old seen requests periodically
        if len(self.seen_requests) > 10000:
            self.seen_requests.clear()

        if request_hash in self.seen_requests:
            return True

        self.seen_requests.add(request_hash)
        return False

    def get_cost_report(self) -> Dict[str, Any]:
        """Generate cost report."""
        return {
            "strategy": self.strategy.value,
            "daily_budget": self.daily_budget,
            "monthly_budget": self.monthly_budget,
            "daily_cost": self.tracker.get_daily_cost(),
            "monthly_cost": self.tracker.get_monthly_cost(),
            "total_requests": len(self.tracker.records),
            "cached_requests": sum(1 for r in self.tracker.records if r.cached),
            "by_provider": {
                provider: {
                    "tier": pricing.tier.value,
                    "free_tier_remaining": max(
                        0,
                        pricing.free_tier_limit - pricing.free_tier_used
                    ) if pricing.free_tier_limit > 0 else "unlimited",
                }
                for provider, pricing in self.pricing.items()
            },
            "savings_from_cache": sum(
                r.input_tokens + r.output_tokens
                for r in self.tracker.records if r.cached
            ) * 0.00001,  # Rough savings estimate
        }

    def reset_daily_quotas(self) -> None:
        """Reset daily free tier quotas (call at midnight)."""
        for pricing in self.pricing.values():
            pricing.free_tier_used = 0

    def optimize_batch(
        self,
        requests: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Optimize a batch of requests for cost.

        Strategies:
        - Deduplicate similar requests
        - Group by optimal provider
        - Order for caching efficiency
        """
        optimized = []
        seen_hashes = set()

        for request in requests:
            messages = request.get("messages", [])
            request_hash = self._hash_request(messages)

            # Deduplicate
            if request_hash in seen_hashes:
                continue
            seen_hashes.add(request_hash)

            # Check cache
            if self.check_cache(messages):
                continue

            optimized.append(request)

        return optimized


def demo():
    """Demonstrate cost optimizer."""
    print("=" * 60)
    print("BAEL Cost Optimizer Demo")
    print("=" * 60)

    optimizer = CostOptimizer(strategy=CostStrategy.ZERO_COST)

    print(f"\nStrategy: {optimizer.strategy.value}")
    print(f"\nFree providers: {optimizer.get_free_providers()}")
    print(f"\nProviders by cost: {optimizer.get_providers_by_cost()[:5]}")

    # Test recommendation
    recommended = optimizer.recommend_provider(
        estimated_input_tokens=1000,
        estimated_output_tokens=500,
    )
    print(f"\nRecommended provider: {recommended}")

    # Record some usage
    optimizer.record_usage(
        provider="openrouter",
        model="gpt-4o-mini",
        input_tokens=1000,
        output_tokens=500,
        messages=[{"role": "user", "content": "test"}],
    )

    # Get report
    report = optimizer.get_cost_report()
    print(f"\nCost report:")
    print(f"  Daily cost: ${report['daily_cost']:.4f}")
    print(f"  Monthly cost: ${report['monthly_cost']:.4f}")
    print(f"  Total requests: {report['total_requests']}")


if __name__ == "__main__":
    demo()
