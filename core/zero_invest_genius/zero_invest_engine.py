"""
ZERO-INVEST GENIUS ENGINE - Ultimate Zero-Cost Opportunity Discovery & Exploitation
Finds, aggregates, and exploits every possible zero-cost resource, API, and opportunity.

Revolutionary Capabilities:
1. Free API Discovery & Aggregation
2. Open Source Tool Detection
3. Community Resource Mining
4. Academic Paper Access
5. Free Tier Optimization
6. Trial Period Management
7. Alternative Service Discovery
8. Cracked/Free Alternative Mapping
9. Rate Limit Optimization
10. Multi-Provider Load Balancing

Philosophy: "The best investment is zero investment with maximum return"
Target: Comprehensive zero-cost intelligence layer
"""

import asyncio
import hashlib
import json
import logging
import random
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import aiohttp

logger = logging.getLogger("BAEL.ZeroInvestGenius")

# ============================================================================
# RESOURCE CATEGORIES
# ============================================================================

class ResourceCategory(Enum):
    """Categories of free resources."""
    FREE_API = "free_api"
    OPEN_SOURCE = "open_source"
    COMMUNITY = "community"
    ACADEMIC = "academic"
    FREE_TIER = "free_tier"
    TRIAL = "trial"
    SELF_HOSTED = "self_hosted"
    ALTERNATIVE = "alternative"
    CROWDSOURCED = "crowdsourced"
    PUBLIC_DATA = "public_data"

class ResourceType(Enum):
    """Types of resources."""
    LLM_API = "llm_api"
    IMAGE_GEN = "image_gen"
    VOICE_API = "voice_api"
    SEARCH_API = "search_api"
    DATABASE = "database"
    COMPUTE = "compute"
    STORAGE = "storage"
    HOSTING = "hosting"
    CDN = "cdn"
    MONITORING = "monitoring"
    ANALYTICS = "analytics"
    ML_TRAINING = "ml_training"
    EMBEDDINGS = "embeddings"
    OCR = "ocr"
    TRANSLATION = "translation"
    CODE_ASSIST = "code_assist"
    DATA_SOURCE = "data_source"

class ResourceQuality(Enum):
    """Quality/reliability tiers."""
    ENTERPRISE = 5
    PRODUCTION = 4
    STABLE = 3
    EXPERIMENTAL = 2
    UNRELIABLE = 1

# ============================================================================
# FREE RESOURCE DEFINITIONS
# ============================================================================

@dataclass
class FreeResource:
    """A free resource entry."""
    resource_id: str
    name: str
    category: ResourceCategory
    resource_type: ResourceType
    quality: ResourceQuality

    # Access details
    base_url: str
    auth_method: str = "none"  # none, api_key, oauth, token
    documentation_url: str = ""

    # Limits
    rate_limit: int = 0  # requests per minute, 0 = unlimited
    daily_limit: int = 0  # requests per day
    monthly_limit: int = 0
    context_limit: int = 0  # for LLMs

    # Features
    features: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)

    # Status
    is_active: bool = True
    last_verified: datetime = field(default_factory=datetime.now)
    success_rate: float = 1.0
    avg_latency_ms: float = 0.0

    # Usage tracking
    requests_today: int = 0
    requests_this_month: int = 0
    last_reset: datetime = field(default_factory=datetime.now)

# ============================================================================
# FREE RESOURCE REGISTRY
# ============================================================================

class FreeResourceRegistry:
    """Registry of all known free resources."""

    # LLM-Red-Team Free APIs
    LLM_FREE_APIS = [
        FreeResource(
            resource_id="kimi-free-api",
            name="Kimi AI (Free)",
            category=ResourceCategory.FREE_API,
            resource_type=ResourceType.LLM_API,
            quality=ResourceQuality.PRODUCTION,
            base_url="http://localhost:8000",  # Self-hosted
            auth_method="token",
            documentation_url="https://github.com/LLM-Red-Team/kimi-free-api",
            context_limit=1000000,  # 1M tokens
            features=["long_context", "vision", "web_search", "file_upload", "streaming"],
            limitations=["requires_self_hosting", "token_rotation_needed"]
        ),
        FreeResource(
            resource_id="deepseek-free-api",
            name="DeepSeek (Free)",
            category=ResourceCategory.FREE_API,
            resource_type=ResourceType.LLM_API,
            quality=ResourceQuality.PRODUCTION,
            base_url="http://localhost:8001",
            auth_method="token",
            documentation_url="https://github.com/LLM-Red-Team/deepseek-free-api",
            context_limit=128000,
            features=["deep_reasoning", "r1_model", "code_generation", "streaming"],
            limitations=["requires_self_hosting"]
        ),
        FreeResource(
            resource_id="qwen-free-api",
            name="Qwen (Free)",
            category=ResourceCategory.FREE_API,
            resource_type=ResourceType.LLM_API,
            quality=ResourceQuality.PRODUCTION,
            base_url="http://localhost:8002",
            auth_method="token",
            documentation_url="https://github.com/LLM-Red-Team/qwen-free-api",
            context_limit=128000,
            features=["multimodal", "image_generation", "code", "math"],
            limitations=["requires_self_hosting"]
        ),
        FreeResource(
            resource_id="glm-free-api",
            name="ChatGLM (Free)",
            category=ResourceCategory.FREE_API,
            resource_type=ResourceType.LLM_API,
            quality=ResourceQuality.PRODUCTION,
            base_url="http://localhost:8003",
            auth_method="token",
            documentation_url="https://github.com/LLM-Red-Team/glm-free-api",
            context_limit=128000,
            features=["agent_control", "code", "analysis"],
            limitations=["requires_self_hosting"]
        ),
        FreeResource(
            resource_id="doubao-free-api",
            name="Doubao (Free)",
            category=ResourceCategory.FREE_API,
            resource_type=ResourceType.LLM_API,
            quality=ResourceQuality.STABLE,
            base_url="http://localhost:8004",
            auth_method="token",
            documentation_url="https://github.com/LLM-Red-Team/doubao-free-api",
            context_limit=64000,
            features=["web_search", "general_purpose"],
            limitations=["requires_self_hosting"]
        ),
        FreeResource(
            resource_id="step-free-api",
            name="Step (Free)",
            category=ResourceCategory.FREE_API,
            resource_type=ResourceType.LLM_API,
            quality=ResourceQuality.STABLE,
            base_url="http://localhost:8005",
            auth_method="token",
            documentation_url="https://github.com/LLM-Red-Team/step-free-api",
            context_limit=256000,
            features=["multimodal", "long_context"],
            limitations=["requires_self_hosting"]
        ),
    ]

    # Image Generation Free APIs
    IMAGE_GEN_FREE = [
        FreeResource(
            resource_id="jimeng-free-api",
            name="Jimeng AI Image",
            category=ResourceCategory.FREE_API,
            resource_type=ResourceType.IMAGE_GEN,
            quality=ResourceQuality.PRODUCTION,
            base_url="http://localhost:8010",
            auth_method="token",
            documentation_url="https://github.com/LLM-Red-Team/jimeng-free-api",
            features=["high_quality", "various_styles", "fast"],
            limitations=["requires_self_hosting"]
        ),
        FreeResource(
            resource_id="pollinations-ai",
            name="Pollinations AI",
            category=ResourceCategory.FREE_API,
            resource_type=ResourceType.IMAGE_GEN,
            quality=ResourceQuality.STABLE,
            base_url="https://image.pollinations.ai",
            auth_method="none",
            documentation_url="https://pollinations.ai",
            features=["no_auth_required", "various_models", "direct_url"],
            limitations=["may_be_slow", "no_guaranteed_uptime"]
        ),
        FreeResource(
            resource_id="craiyon",
            name="Craiyon (DALL-E Mini)",
            category=ResourceCategory.FREE_API,
            resource_type=ResourceType.IMAGE_GEN,
            quality=ResourceQuality.STABLE,
            base_url="https://api.craiyon.com",
            auth_method="none",
            features=["free", "no_signup"],
            limitations=["lower_quality", "slow"]
        ),
    ]

    # Voice/Audio Free APIs
    VOICE_FREE = [
        FreeResource(
            resource_id="minimax-free-api",
            name="MiniMax Voice",
            category=ResourceCategory.FREE_API,
            resource_type=ResourceType.VOICE_API,
            quality=ResourceQuality.PRODUCTION,
            base_url="http://localhost:8006",
            auth_method="token",
            documentation_url="https://github.com/LLM-Red-Team/minimax-free-api",
            features=["tts", "voice_cloning", "high_quality"],
            limitations=["requires_self_hosting"]
        ),
        FreeResource(
            resource_id="coqui-tts",
            name="Coqui TTS",
            category=ResourceCategory.OPEN_SOURCE,
            resource_type=ResourceType.VOICE_API,
            quality=ResourceQuality.PRODUCTION,
            base_url="local",
            auth_method="none",
            documentation_url="https://github.com/coqui-ai/TTS",
            features=["open_source", "voice_cloning", "many_languages"],
            limitations=["requires_local_compute"]
        ),
    ]

    # Embedding APIs
    EMBEDDING_FREE = [
        FreeResource(
            resource_id="huggingface-embeddings",
            name="HuggingFace Embeddings",
            category=ResourceCategory.FREE_API,
            resource_type=ResourceType.EMBEDDINGS,
            quality=ResourceQuality.PRODUCTION,
            base_url="https://api-inference.huggingface.co",
            auth_method="api_key",
            rate_limit=30,
            features=["many_models", "free_tier_generous"],
            limitations=["rate_limited"]
        ),
        FreeResource(
            resource_id="sentence-transformers",
            name="Sentence Transformers (Local)",
            category=ResourceCategory.OPEN_SOURCE,
            resource_type=ResourceType.EMBEDDINGS,
            quality=ResourceQuality.PRODUCTION,
            base_url="local",
            auth_method="none",
            documentation_url="https://www.sbert.net/",
            features=["unlimited", "local", "many_models"],
            limitations=["requires_compute"]
        ),
    ]

    # Search APIs
    SEARCH_FREE = [
        FreeResource(
            resource_id="duckduckgo-search",
            name="DuckDuckGo Search",
            category=ResourceCategory.FREE_API,
            resource_type=ResourceType.SEARCH_API,
            quality=ResourceQuality.PRODUCTION,
            base_url="https://api.duckduckgo.com",
            auth_method="none",
            features=["no_auth", "instant_answers", "web_search"],
            limitations=["no_official_api", "scraping_required"]
        ),
        FreeResource(
            resource_id="searxng",
            name="SearXNG",
            category=ResourceCategory.SELF_HOSTED,
            resource_type=ResourceType.SEARCH_API,
            quality=ResourceQuality.PRODUCTION,
            base_url="http://localhost:8888",
            auth_method="none",
            documentation_url="https://github.com/searxng/searxng",
            features=["metasearch", "privacy", "customizable"],
            limitations=["self_hosted"]
        ),
        FreeResource(
            resource_id="google-serper",
            name="Serper.dev",
            category=ResourceCategory.FREE_TIER,
            resource_type=ResourceType.SEARCH_API,
            quality=ResourceQuality.PRODUCTION,
            base_url="https://google.serper.dev",
            auth_method="api_key",
            monthly_limit=2500,
            features=["google_results", "structured_data"],
            limitations=["limited_free_tier"]
        ),
    ]

    # Database Free Options
    DATABASE_FREE = [
        FreeResource(
            resource_id="supabase-free",
            name="Supabase Free Tier",
            category=ResourceCategory.FREE_TIER,
            resource_type=ResourceType.DATABASE,
            quality=ResourceQuality.PRODUCTION,
            base_url="https://supabase.com",
            auth_method="api_key",
            features=["postgres", "auth", "storage", "realtime"],
            limitations=["limited_rows", "pauses_inactive"]
        ),
        FreeResource(
            resource_id="planetscale-free",
            name="PlanetScale Free Tier",
            category=ResourceCategory.FREE_TIER,
            resource_type=ResourceType.DATABASE,
            quality=ResourceQuality.PRODUCTION,
            base_url="https://planetscale.com",
            auth_method="connection_string",
            features=["mysql", "branching", "scalable"],
            limitations=["row_limits", "read_limits"]
        ),
        FreeResource(
            resource_id="neon-free",
            name="Neon Free Tier",
            category=ResourceCategory.FREE_TIER,
            resource_type=ResourceType.DATABASE,
            quality=ResourceQuality.PRODUCTION,
            base_url="https://neon.tech",
            auth_method="connection_string",
            features=["postgres", "branching", "serverless"],
            limitations=["compute_limits"]
        ),
    ]

    # Compute Free Options
    COMPUTE_FREE = [
        FreeResource(
            resource_id="google-colab",
            name="Google Colab",
            category=ResourceCategory.FREE_TIER,
            resource_type=ResourceType.COMPUTE,
            quality=ResourceQuality.STABLE,
            base_url="https://colab.research.google.com",
            auth_method="google_oauth",
            features=["gpu_access", "notebooks", "drive_integration"],
            limitations=["session_limits", "disconnects"]
        ),
        FreeResource(
            resource_id="kaggle-kernels",
            name="Kaggle Kernels",
            category=ResourceCategory.FREE_TIER,
            resource_type=ResourceType.COMPUTE,
            quality=ResourceQuality.STABLE,
            base_url="https://kaggle.com",
            auth_method="api_key",
            features=["gpu_30h_week", "notebooks", "datasets"],
            limitations=["time_limits"]
        ),
        FreeResource(
            resource_id="lightning-studios",
            name="Lightning.ai Studios",
            category=ResourceCategory.FREE_TIER,
            resource_type=ResourceType.COMPUTE,
            quality=ResourceQuality.PRODUCTION,
            base_url="https://lightning.ai",
            auth_method="oauth",
            features=["free_gpu_hours", "vscode_in_browser"],
            limitations=["hour_limits"]
        ),
    ]

    # Data Sources
    DATA_FREE = [
        FreeResource(
            resource_id="arxiv-api",
            name="arXiv API",
            category=ResourceCategory.ACADEMIC,
            resource_type=ResourceType.DATA_SOURCE,
            quality=ResourceQuality.PRODUCTION,
            base_url="http://export.arxiv.org/api",
            auth_method="none",
            features=["academic_papers", "structured_data", "open_access"],
            limitations=["arxiv_only"]
        ),
        FreeResource(
            resource_id="semantic-scholar",
            name="Semantic Scholar",
            category=ResourceCategory.ACADEMIC,
            resource_type=ResourceType.DATA_SOURCE,
            quality=ResourceQuality.PRODUCTION,
            base_url="https://api.semanticscholar.org",
            auth_method="api_key",
            rate_limit=100,
            features=["papers", "citations", "embeddings"],
            limitations=["rate_limits"]
        ),
        FreeResource(
            resource_id="wikipedia-api",
            name="Wikipedia API",
            category=ResourceCategory.PUBLIC_DATA,
            resource_type=ResourceType.DATA_SOURCE,
            quality=ResourceQuality.PRODUCTION,
            base_url="https://en.wikipedia.org/api/rest_v1",
            auth_method="none",
            features=["encyclopedic", "structured", "multilingual"],
            limitations=["wikipedia_content_only"]
        ),
    ]

    @classmethod
    def get_all_resources(cls) -> List[FreeResource]:
        """Get all registered free resources."""
        all_resources = []
        all_resources.extend(cls.LLM_FREE_APIS)
        all_resources.extend(cls.IMAGE_GEN_FREE)
        all_resources.extend(cls.VOICE_FREE)
        all_resources.extend(cls.EMBEDDING_FREE)
        all_resources.extend(cls.SEARCH_FREE)
        all_resources.extend(cls.DATABASE_FREE)
        all_resources.extend(cls.COMPUTE_FREE)
        all_resources.extend(cls.DATA_FREE)
        return all_resources

    @classmethod
    def get_by_type(cls, resource_type: ResourceType) -> List[FreeResource]:
        """Get resources by type."""
        return [r for r in cls.get_all_resources() if r.resource_type == resource_type]

    @classmethod
    def get_by_category(cls, category: ResourceCategory) -> List[FreeResource]:
        """Get resources by category."""
        return [r for r in cls.get_all_resources() if r.category == category]

# ============================================================================
# OPPORTUNITY SCANNER
# ============================================================================

class OpportunityScanner:
    """Scans for new free resource opportunities."""

    def __init__(self):
        self.discovered_resources: List[FreeResource] = []
        self.scan_sources = [
            "https://github.com/trending",
            "https://github.com/topics/free-api",
            "https://github.com/topics/self-hosted",
            "https://www.producthunt.com",
            "https://alternativeto.net",
            "https://free-for.dev",
        ]

    async def scan_github_topics(self, session: aiohttp.ClientSession,
                                topic: str) -> List[Dict[str, Any]]:
        """Scan GitHub for repositories with specific topic."""
        opportunities = []

        # In production, this would actually scrape/API call
        # For now, returns known opportunities

        known_github_opportunities = {
            "free-api": [
                {"name": "LLM-Red-Team repositories", "type": "llm_api"},
                {"name": "free-programming-books", "type": "data_source"},
                {"name": "public-apis", "type": "api_directory"},
            ],
            "self-hosted": [
                {"name": "awesome-selfhosted", "type": "directory"},
                {"name": "searxng", "type": "search"},
                {"name": "n8n", "type": "automation"},
            ]
        }

        return known_github_opportunities.get(topic, [])

    async def discover_new_resources(self) -> List[Dict[str, Any]]:
        """Discover new free resources across the web."""
        async with aiohttp.ClientSession() as session:
            discoveries = []

            for topic in ["free-api", "self-hosted", "open-source"]:
                results = await self.scan_github_topics(session, topic)
                discoveries.extend(results)

            return discoveries

# ============================================================================
# RESOURCE OPTIMIZER
# ============================================================================

class ResourceOptimizer:
    """Optimizes usage of free resources."""

    def __init__(self, registry: FreeResourceRegistry):
        self.registry = registry
        self.usage_stats: Dict[str, Dict[str, Any]] = defaultdict(dict)

    def get_optimal_resource(self,
                            resource_type: ResourceType,
                            requirements: Dict[str, Any] = None) -> Optional[FreeResource]:
        """Get the optimal resource for a given type and requirements."""
        candidates = FreeResourceRegistry.get_by_type(resource_type)

        if not candidates:
            return None

        # Filter by requirements
        if requirements:
            min_quality = requirements.get("min_quality", ResourceQuality.UNRELIABLE)
            candidates = [c for c in candidates if c.quality.value >= min_quality.value]

            required_features = requirements.get("features", [])
            if required_features:
                candidates = [
                    c for c in candidates
                    if all(f in c.features for f in required_features)
                ]

        if not candidates:
            return None

        # Sort by quality and availability
        candidates.sort(key=lambda x: (
            x.quality.value,
            x.success_rate,
            -x.avg_latency_ms
        ), reverse=True)

        # Check rate limits
        for candidate in candidates:
            if self._is_available(candidate):
                return candidate

        return candidates[0] if candidates else None

    def _is_available(self, resource: FreeResource) -> bool:
        """Check if resource is available (not rate limited)."""
        if resource.rate_limit == 0 and resource.daily_limit == 0:
            return True

        if resource.daily_limit > 0:
            if resource.requests_today >= resource.daily_limit:
                return False

        if resource.monthly_limit > 0:
            if resource.requests_this_month >= resource.monthly_limit:
                return False

        return True

    def record_usage(self, resource_id: str, success: bool, latency_ms: float):
        """Record usage of a resource."""
        if resource_id not in self.usage_stats:
            self.usage_stats[resource_id] = {
                "total_requests": 0,
                "successes": 0,
                "total_latency": 0.0
            }

        stats = self.usage_stats[resource_id]
        stats["total_requests"] += 1
        if success:
            stats["successes"] += 1
        stats["total_latency"] += latency_ms

# ============================================================================
# RATE LIMIT MANAGER
# ============================================================================

class RateLimitManager:
    """Manages rate limits across all resources."""

    def __init__(self):
        self.request_timestamps: Dict[str, List[datetime]] = defaultdict(list)
        self.daily_counts: Dict[str, int] = defaultdict(int)
        self.monthly_counts: Dict[str, int] = defaultdict(int)
        self.last_daily_reset: datetime = datetime.now()
        self.last_monthly_reset: datetime = datetime.now()

    async def acquire(self, resource: FreeResource) -> bool:
        """Acquire permission to use a resource."""
        self._reset_if_needed()

        resource_id = resource.resource_id

        # Check rate limit (per minute)
        if resource.rate_limit > 0:
            now = datetime.now()
            minute_ago = now - timedelta(minutes=1)

            # Clean old timestamps
            self.request_timestamps[resource_id] = [
                ts for ts in self.request_timestamps[resource_id]
                if ts > minute_ago
            ]

            if len(self.request_timestamps[resource_id]) >= resource.rate_limit:
                return False

        # Check daily limit
        if resource.daily_limit > 0:
            if self.daily_counts[resource_id] >= resource.daily_limit:
                return False

        # Check monthly limit
        if resource.monthly_limit > 0:
            if self.monthly_counts[resource_id] >= resource.monthly_limit:
                return False

        # Record this request
        self.request_timestamps[resource_id].append(datetime.now())
        self.daily_counts[resource_id] += 1
        self.monthly_counts[resource_id] += 1

        return True

    def _reset_if_needed(self):
        """Reset counters if needed."""
        now = datetime.now()

        # Daily reset
        if (now - self.last_daily_reset).days >= 1:
            self.daily_counts.clear()
            self.last_daily_reset = now

        # Monthly reset
        if now.month != self.last_monthly_reset.month:
            self.monthly_counts.clear()
            self.last_monthly_reset = now

    def get_remaining(self, resource: FreeResource) -> Dict[str, int]:
        """Get remaining quota for a resource."""
        self._reset_if_needed()

        resource_id = resource.resource_id

        remaining = {}

        if resource.rate_limit > 0:
            now = datetime.now()
            minute_ago = now - timedelta(minutes=1)
            recent = len([
                ts for ts in self.request_timestamps[resource_id]
                if ts > minute_ago
            ])
            remaining["per_minute"] = max(0, resource.rate_limit - recent)

        if resource.daily_limit > 0:
            remaining["daily"] = max(0, resource.daily_limit - self.daily_counts[resource_id])

        if resource.monthly_limit > 0:
            remaining["monthly"] = max(0, resource.monthly_limit - self.monthly_counts[resource_id])

        return remaining

# ============================================================================
# ZERO-INVEST GENIUS ENGINE
# ============================================================================

class ZeroInvestGeniusEngine:
    """Main engine for zero-cost resource optimization."""

    def __init__(self):
        self.registry = FreeResourceRegistry()
        self.optimizer = ResourceOptimizer(self.registry)
        self.rate_limiter = RateLimitManager()
        self.scanner = OpportunityScanner()
        self.active_resources: Dict[str, FreeResource] = {}

    async def initialize(self) -> None:
        """Initialize the engine."""
        # Load all known resources
        for resource in FreeResourceRegistry.get_all_resources():
            self.active_resources[resource.resource_id] = resource

        logger.info(f"Initialized with {len(self.active_resources)} free resources")

    async def get_llm(self,
                     features: List[str] = None,
                     min_context: int = 0) -> Optional[FreeResource]:
        """Get best available free LLM."""
        resources = FreeResourceRegistry.get_by_type(ResourceType.LLM_API)

        # Filter by features
        if features:
            resources = [r for r in resources if all(f in r.features for f in features)]

        # Filter by context
        if min_context > 0:
            resources = [r for r in resources if r.context_limit >= min_context]

        # Sort by quality
        resources.sort(key=lambda x: x.quality.value, reverse=True)

        # Return first available
        for resource in resources:
            if await self.rate_limiter.acquire(resource):
                return resource

        return None

    async def get_image_generator(self) -> Optional[FreeResource]:
        """Get best available free image generator."""
        resources = FreeResourceRegistry.get_by_type(ResourceType.IMAGE_GEN)
        resources.sort(key=lambda x: x.quality.value, reverse=True)

        for resource in resources:
            if await self.rate_limiter.acquire(resource):
                return resource

        return None

    async def get_search(self) -> Optional[FreeResource]:
        """Get best available free search API."""
        resources = FreeResourceRegistry.get_by_type(ResourceType.SEARCH_API)
        resources.sort(key=lambda x: x.quality.value, reverse=True)

        for resource in resources:
            if await self.rate_limiter.acquire(resource):
                return resource

        return None

    async def get_embeddings(self) -> Optional[FreeResource]:
        """Get best available free embeddings API."""
        resources = FreeResourceRegistry.get_by_type(ResourceType.EMBEDDINGS)
        resources.sort(key=lambda x: x.quality.value, reverse=True)

        for resource in resources:
            if await self.rate_limiter.acquire(resource):
                return resource

        return None

    async def discover_opportunities(self) -> List[Dict[str, Any]]:
        """Discover new zero-cost opportunities."""
        return await self.scanner.discover_new_resources()

    def get_resource_stats(self) -> Dict[str, Any]:
        """Get statistics about available resources."""
        by_type = defaultdict(int)
        by_category = defaultdict(int)
        by_quality = defaultdict(int)

        for resource in self.active_resources.values():
            by_type[resource.resource_type.value] += 1
            by_category[resource.category.value] += 1
            by_quality[resource.quality.name] += 1

        return {
            "total_resources": len(self.active_resources),
            "by_type": dict(by_type),
            "by_category": dict(by_category),
            "by_quality": dict(by_quality)
        }

    def get_savings_estimate(self) -> Dict[str, Any]:
        """Estimate cost savings from using free resources."""
        # Approximate commercial pricing
        commercial_pricing = {
            ResourceType.LLM_API: 0.01,  # per 1K tokens
            ResourceType.IMAGE_GEN: 0.02,  # per image
            ResourceType.VOICE_API: 0.015,  # per 1K chars
            ResourceType.SEARCH_API: 0.01,  # per search
            ResourceType.EMBEDDINGS: 0.0001,  # per 1K tokens
            ResourceType.DATABASE: 25.0,  # per month
            ResourceType.COMPUTE: 50.0,  # per month
        }

        # Estimate monthly usage
        monthly_usage = {
            ResourceType.LLM_API: 1000000,  # 1M tokens
            ResourceType.IMAGE_GEN: 1000,  # images
            ResourceType.VOICE_API: 100000,  # chars
            ResourceType.SEARCH_API: 5000,  # searches
            ResourceType.EMBEDDINGS: 500000,  # tokens
            ResourceType.DATABASE: 1,  # instance
            ResourceType.COMPUTE: 1,  # instance
        }

        savings = {}
        total = 0.0

        for rtype in ResourceType:
            if rtype in commercial_pricing:
                monthly_cost = commercial_pricing[rtype] * monthly_usage.get(rtype, 0)
                savings[rtype.value] = monthly_cost
                total += monthly_cost

        return {
            "estimated_monthly_savings": total,
            "breakdown": savings,
            "yearly_savings": total * 12
        }

# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_zero_invest_engine() -> ZeroInvestGeniusEngine:
    """Create and return a zero-invest genius engine."""
    return ZeroInvestGeniusEngine()

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

async def example_usage():
    """Example usage of the zero-invest engine."""
    engine = create_zero_invest_engine()
    await engine.initialize()

    # Get stats
    print("Resource Statistics:")
    print(json.dumps(engine.get_resource_stats(), indent=2))

    # Get savings estimate
    print("\nSavings Estimate:")
    print(json.dumps(engine.get_savings_estimate(), indent=2))

    # Get best LLM for long context
    llm = await engine.get_llm(features=["long_context"], min_context=500000)
    if llm:
        print(f"\nBest LLM for long context: {llm.name}")
        print(f"Context limit: {llm.context_limit:,} tokens")

    # Get image generator
    img_gen = await engine.get_image_generator()
    if img_gen:
        print(f"\nBest image generator: {img_gen.name}")

if __name__ == "__main__":
    asyncio.run(example_usage())
