#!/usr/bin/env python3
"""
BAEL - LLM Router
Intelligent routing for Large Language Model requests.

Features:
- Multi-provider support (OpenAI, Anthropic, Local, etc.)
- Cost optimization routing
- Latency-based routing
- Fallback chains
- Token counting
- Rate limiting
- Response caching
- Load balancing across providers
- Model capability matching
- Streaming support
- Usage tracking
"""

import asyncio
import hashlib
import logging
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, AsyncIterator, Awaitable, Callable, Dict, Generator,
                    List, Optional, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class LLMProvider(Enum):
    """LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    COHERE = "cohere"
    LOCAL = "local"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"


class RoutingStrategy(Enum):
    """Routing strategies."""
    COST_OPTIMIZED = "cost_optimized"
    LATENCY_OPTIMIZED = "latency_optimized"
    QUALITY_OPTIMIZED = "quality_optimized"
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    FALLBACK = "fallback"
    CAPABILITY_MATCH = "capability_match"


class ModelCapability(Enum):
    """Model capabilities."""
    CHAT = "chat"
    COMPLETION = "completion"
    CODE = "code"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"
    LONG_CONTEXT = "long_context"
    REASONING = "reasoning"
    CREATIVE = "creative"


class RequestPriority(Enum):
    """Request priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ModelConfig:
    """Configuration for an LLM model."""
    id: str
    provider: LLMProvider
    model_name: str
    context_length: int = 4096
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    avg_latency: float = 0.5
    capabilities: Set[ModelCapability] = field(default_factory=set)
    rate_limit: int = 100  # requests per minute
    enabled: bool = True
    weight: int = 1


@dataclass
class ChatMessage:
    """Chat message."""
    role: str  # system, user, assistant
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None


@dataclass
class LLMRequest:
    """Request to LLM."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[ChatMessage] = field(default_factory=list)
    model: Optional[str] = None
    max_tokens: int = 1024
    temperature: float = 0.7
    top_p: float = 1.0
    stop: Optional[List[str]] = None
    stream: bool = False
    functions: Optional[List[Dict]] = None
    priority: RequestPriority = RequestPriority.NORMAL
    required_capabilities: Set[ModelCapability] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Response from LLM."""
    id: str
    model: str
    provider: str
    content: str
    finish_reason: str = "stop"
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    latency: float = 0.0
    from_cache: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UsageStats:
    """Usage statistics."""
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    avg_latency: float = 0.0
    errors: int = 0


# =============================================================================
# TOKEN COUNTER
# =============================================================================

class TokenCounter:
    """Estimate token counts."""

    @staticmethod
    def count_text(text: str) -> int:
        """Estimate token count for text."""
        # Rough estimate: 4 characters per token
        return max(1, len(text) // 4)

    @staticmethod
    def count_messages(messages: List[ChatMessage]) -> int:
        """Estimate token count for messages."""
        total = 0
        for msg in messages:
            total += 4  # Message overhead
            total += TokenCounter.count_text(msg.content)
            if msg.name:
                total += TokenCounter.count_text(msg.name)
        return total


# =============================================================================
# CACHE
# =============================================================================

class ResponseCache:
    """Cache for LLM responses."""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self._cache: Dict[str, Tuple[LLMResponse, datetime]] = {}
        self._max_size = max_size
        self._ttl = ttl

    def _hash_request(self, request: LLMRequest) -> str:
        """Generate cache key for request."""
        messages = [(m.role, m.content) for m in request.messages]
        key_data = f"{request.model}:{request.temperature}:{messages}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(self, request: LLMRequest) -> Optional[LLMResponse]:
        """Get cached response."""
        key = self._hash_request(request)

        if key in self._cache:
            response, created = self._cache[key]
            if datetime.utcnow() - created < timedelta(seconds=self._ttl):
                return response
            del self._cache[key]

        return None

    def set(self, request: LLMRequest, response: LLMResponse) -> None:
        """Cache response."""
        if len(self._cache) >= self._max_size:
            # Remove oldest entry
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

        key = self._hash_request(request)
        self._cache[key] = (response, datetime.utcnow())

    def clear(self) -> None:
        """Clear cache."""
        self._cache.clear()


# =============================================================================
# RATE LIMITER
# =============================================================================

class RateLimiter:
    """Rate limiter for providers."""

    def __init__(self):
        self._requests: Dict[str, List[datetime]] = defaultdict(list)
        self._limits: Dict[str, int] = {}

    def set_limit(self, model_id: str, limit: int) -> None:
        """Set rate limit for model."""
        self._limits[model_id] = limit

    def check(self, model_id: str) -> bool:
        """Check if request is allowed."""
        limit = self._limits.get(model_id, 100)
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)

        # Clean old requests
        self._requests[model_id] = [
            t for t in self._requests[model_id] if t > minute_ago
        ]

        return len(self._requests[model_id]) < limit

    def record(self, model_id: str) -> None:
        """Record a request."""
        self._requests[model_id].append(datetime.utcnow())

    async def wait_if_needed(self, model_id: str) -> None:
        """Wait if rate limit exceeded."""
        while not self.check(model_id):
            await asyncio.sleep(0.1)


# =============================================================================
# PROVIDERS
# =============================================================================

class BaseLLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    async def complete(self, request: LLMRequest, model: ModelConfig) -> LLMResponse:
        """Complete a request."""
        pass

    @abstractmethod
    async def stream(self, request: LLMRequest, model: ModelConfig) -> AsyncIterator[str]:
        """Stream a response."""
        pass


class SimulatedProvider(BaseLLMProvider):
    """Simulated LLM provider for testing."""

    def __init__(self, provider: LLMProvider, latency: float = 0.5):
        self.provider = provider
        self.base_latency = latency

    async def complete(self, request: LLMRequest, model: ModelConfig) -> LLMResponse:
        """Complete a request."""
        # Simulate processing
        latency = self.base_latency + random.uniform(0, 0.3)
        await asyncio.sleep(latency)

        # Count tokens
        input_tokens = TokenCounter.count_messages(request.messages)

        # Generate simulated response
        response_text = f"This is a simulated response from {model.model_name}. "
        response_text += "I would process your request and provide helpful information. "
        response_text += f"Temperature: {request.temperature}, Max tokens: {request.max_tokens}"

        output_tokens = TokenCounter.count_text(response_text)

        # Calculate cost
        cost = (input_tokens / 1000 * model.cost_per_1k_input +
                output_tokens / 1000 * model.cost_per_1k_output)

        return LLMResponse(
            id=str(uuid.uuid4()),
            model=model.model_name,
            provider=self.provider.value,
            content=response_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost=cost,
            latency=latency
        )

    async def stream(self, request: LLMRequest, model: ModelConfig) -> AsyncIterator[str]:
        """Stream a response."""
        response = await self.complete(request, model)

        # Simulate streaming
        words = response.content.split()
        for word in words:
            yield word + " "
            await asyncio.sleep(0.02)


# =============================================================================
# ROUTERS
# =============================================================================

class BaseRouter(ABC):
    """Base router for model selection."""

    @abstractmethod
    def select(
        self,
        request: LLMRequest,
        models: List[ModelConfig]
    ) -> Optional[ModelConfig]:
        """Select a model for the request."""
        pass


class CostOptimizedRouter(BaseRouter):
    """Select cheapest model that meets requirements."""

    def select(
        self,
        request: LLMRequest,
        models: List[ModelConfig]
    ) -> Optional[ModelConfig]:
        eligible = self._filter_eligible(request, models)
        if not eligible:
            return None

        # Sort by total cost estimate
        def cost_score(m: ModelConfig) -> float:
            input_tokens = TokenCounter.count_messages(request.messages)
            output_estimate = request.max_tokens
            return (input_tokens / 1000 * m.cost_per_1k_input +
                    output_estimate / 1000 * m.cost_per_1k_output)

        return min(eligible, key=cost_score)

    def _filter_eligible(
        self,
        request: LLMRequest,
        models: List[ModelConfig]
    ) -> List[ModelConfig]:
        """Filter models that meet requirements."""
        eligible = []

        for model in models:
            if not model.enabled:
                continue

            # Check capabilities
            if request.required_capabilities:
                if not request.required_capabilities.issubset(model.capabilities):
                    continue

            # Check context length
            input_tokens = TokenCounter.count_messages(request.messages)
            if input_tokens + request.max_tokens > model.context_length:
                continue

            eligible.append(model)

        return eligible


class LatencyOptimizedRouter(BaseRouter):
    """Select fastest model."""

    def select(
        self,
        request: LLMRequest,
        models: List[ModelConfig]
    ) -> Optional[ModelConfig]:
        eligible = [m for m in models if m.enabled]

        if not eligible:
            return None

        return min(eligible, key=lambda m: m.avg_latency)


class QualityOptimizedRouter(BaseRouter):
    """Select highest quality model (most capable/expensive)."""

    def select(
        self,
        request: LLMRequest,
        models: List[ModelConfig]
    ) -> Optional[ModelConfig]:
        eligible = [m for m in models if m.enabled]

        if not eligible:
            return None

        # Use cost as proxy for quality
        return max(eligible, key=lambda m: m.cost_per_1k_output)


class RoundRobinRouter(BaseRouter):
    """Round robin selection."""

    def __init__(self):
        self._index = 0

    def select(
        self,
        request: LLMRequest,
        models: List[ModelConfig]
    ) -> Optional[ModelConfig]:
        eligible = [m for m in models if m.enabled]

        if not eligible:
            return None

        model = eligible[self._index % len(eligible)]
        self._index += 1
        return model


class CapabilityMatchRouter(BaseRouter):
    """Select model that best matches required capabilities."""

    def select(
        self,
        request: LLMRequest,
        models: List[ModelConfig]
    ) -> Optional[ModelConfig]:
        eligible = [m for m in models if m.enabled]

        if not eligible:
            return None

        if not request.required_capabilities:
            return eligible[0]

        # Score by capability match
        best = None
        best_score = -1

        for model in eligible:
            matching = len(request.required_capabilities & model.capabilities)
            total = len(model.capabilities)

            if matching >= len(request.required_capabilities):
                score = matching - total * 0.1  # Prefer focused models
                if score > best_score:
                    best_score = score
                    best = model

        return best


# =============================================================================
# LLM ROUTER
# =============================================================================

class LLMRouter:
    """
    LLM Router for BAEL.

    Intelligent routing for Large Language Model requests.
    """

    def __init__(
        self,
        strategy: RoutingStrategy = RoutingStrategy.COST_OPTIMIZED,
        enable_cache: bool = True
    ):
        self._strategy = strategy
        self._models: Dict[str, ModelConfig] = {}
        self._providers: Dict[LLMProvider, BaseLLMProvider] = {}
        self._router = self._create_router(strategy)
        self._cache = ResponseCache() if enable_cache else None
        self._rate_limiter = RateLimiter()
        self._usage: Dict[str, UsageStats] = defaultdict(UsageStats)
        self._fallback_order: List[str] = []

        # Initialize simulated providers
        self._init_providers()

    def _create_router(self, strategy: RoutingStrategy) -> BaseRouter:
        """Create router for strategy."""
        routers = {
            RoutingStrategy.COST_OPTIMIZED: CostOptimizedRouter,
            RoutingStrategy.LATENCY_OPTIMIZED: LatencyOptimizedRouter,
            RoutingStrategy.QUALITY_OPTIMIZED: QualityOptimizedRouter,
            RoutingStrategy.ROUND_ROBIN: RoundRobinRouter,
            RoutingStrategy.CAPABILITY_MATCH: CapabilityMatchRouter,
        }
        return routers.get(strategy, CostOptimizedRouter)()

    def _init_providers(self) -> None:
        """Initialize providers."""
        self._providers[LLMProvider.OPENAI] = SimulatedProvider(LLMProvider.OPENAI, 0.5)
        self._providers[LLMProvider.ANTHROPIC] = SimulatedProvider(LLMProvider.ANTHROPIC, 0.6)
        self._providers[LLMProvider.LOCAL] = SimulatedProvider(LLMProvider.LOCAL, 0.1)

    # -------------------------------------------------------------------------
    # MODEL MANAGEMENT
    # -------------------------------------------------------------------------

    def register_model(self, model: ModelConfig) -> None:
        """Register a model."""
        self._models[model.id] = model
        self._rate_limiter.set_limit(model.id, model.rate_limit)

    def unregister_model(self, model_id: str) -> None:
        """Unregister a model."""
        if model_id in self._models:
            del self._models[model_id]

    def enable_model(self, model_id: str) -> None:
        """Enable a model."""
        if model_id in self._models:
            self._models[model_id].enabled = True

    def disable_model(self, model_id: str) -> None:
        """Disable a model."""
        if model_id in self._models:
            self._models[model_id].enabled = False

    def list_models(self) -> List[ModelConfig]:
        """List all models."""
        return list(self._models.values())

    def set_fallback_order(self, model_ids: List[str]) -> None:
        """Set fallback order for models."""
        self._fallback_order = model_ids

    # -------------------------------------------------------------------------
    # COMPLETION
    # -------------------------------------------------------------------------

    async def complete(
        self,
        request: LLMRequest,
        use_cache: bool = True
    ) -> LLMResponse:
        """Complete a request."""
        # Check cache
        if self._cache and use_cache:
            cached = self._cache.get(request)
            if cached:
                cached.from_cache = True
                return cached

        # Select model
        if request.model:
            model = self._models.get(request.model)
        else:
            model = self._router.select(request, list(self._models.values()))

        if not model:
            raise ValueError("No suitable model found")

        # Rate limiting
        await self._rate_limiter.wait_if_needed(model.id)

        # Get provider
        provider = self._providers.get(model.provider)
        if not provider:
            raise ValueError(f"Provider {model.provider} not available")

        # Execute with fallback
        last_error = None
        models_to_try = [model]

        if self._fallback_order:
            models_to_try.extend([
                self._models[mid] for mid in self._fallback_order
                if mid in self._models and mid != model.id
            ])

        for try_model in models_to_try:
            try:
                self._rate_limiter.record(try_model.id)
                response = await provider.complete(request, try_model)

                # Update usage
                self._update_usage(try_model.id, response)

                # Cache
                if self._cache and use_cache:
                    self._cache.set(request, response)

                return response

            except Exception as e:
                last_error = e
                self._usage[try_model.id].errors += 1
                continue

        raise last_error or ValueError("All models failed")

    async def stream(
        self,
        request: LLMRequest
    ) -> AsyncIterator[str]:
        """Stream a response."""
        # Select model
        if request.model:
            model = self._models.get(request.model)
        else:
            model = self._router.select(request, list(self._models.values()))

        if not model:
            raise ValueError("No suitable model found")

        # Get provider
        provider = self._providers.get(model.provider)
        if not provider:
            raise ValueError(f"Provider {model.provider} not available")

        async for chunk in provider.stream(request, model):
            yield chunk

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _update_usage(self, model_id: str, response: LLMResponse) -> None:
        """Update usage statistics."""
        stats = self._usage[model_id]
        stats.total_requests += 1
        stats.total_input_tokens += response.input_tokens
        stats.total_output_tokens += response.output_tokens
        stats.total_cost += response.cost

        # Update average latency
        n = stats.total_requests
        stats.avg_latency = (stats.avg_latency * (n - 1) + response.latency) / n

    # -------------------------------------------------------------------------
    # CONVENIENCE METHODS
    # -------------------------------------------------------------------------

    async def chat(
        self,
        message: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """Simple chat interface."""
        messages = []

        if system:
            messages.append(ChatMessage(role="system", content=system))

        messages.append(ChatMessage(role="user", content=message))

        request = LLMRequest(
            messages=messages,
            model=model,
            temperature=temperature
        )

        response = await self.complete(request)
        return response.content

    async def summarize(self, text: str, max_length: int = 100) -> str:
        """Summarize text."""
        return await self.chat(
            f"Summarize the following text in about {max_length} words:\n\n{text}",
            system="You are a helpful assistant that creates concise summaries."
        )

    async def translate(self, text: str, target_language: str) -> str:
        """Translate text."""
        return await self.chat(
            f"Translate the following text to {target_language}:\n\n{text}",
            system="You are a professional translator."
        )

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_usage(self, model_id: Optional[str] = None) -> Dict[str, UsageStats]:
        """Get usage statistics."""
        if model_id:
            return {model_id: self._usage[model_id]}
        return dict(self._usage)

    def get_total_cost(self) -> float:
        """Get total cost across all models."""
        return sum(s.total_cost for s in self._usage.values())

    def reset_usage(self) -> None:
        """Reset usage statistics."""
        self._usage.clear()

    # -------------------------------------------------------------------------
    # CONFIGURATION
    # -------------------------------------------------------------------------

    def set_strategy(self, strategy: RoutingStrategy) -> None:
        """Change routing strategy."""
        self._strategy = strategy
        self._router = self._create_router(strategy)

    def clear_cache(self) -> None:
        """Clear response cache."""
        if self._cache:
            self._cache.clear()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the LLM Router."""
    print("=" * 70)
    print("BAEL - LLM ROUTER DEMO")
    print("Intelligent Model Routing")
    print("=" * 70)
    print()

    router = LLMRouter(strategy=RoutingStrategy.COST_OPTIMIZED)

    # 1. Register Models
    print("1. REGISTER MODELS:")
    print("-" * 40)

    models = [
        ModelConfig(
            id="gpt-4",
            provider=LLMProvider.OPENAI,
            model_name="gpt-4",
            context_length=8192,
            cost_per_1k_input=0.03,
            cost_per_1k_output=0.06,
            avg_latency=1.0,
            capabilities={ModelCapability.CHAT, ModelCapability.CODE, ModelCapability.FUNCTION_CALLING}
        ),
        ModelConfig(
            id="gpt-3.5",
            provider=LLMProvider.OPENAI,
            model_name="gpt-3.5-turbo",
            context_length=4096,
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.002,
            avg_latency=0.5,
            capabilities={ModelCapability.CHAT}
        ),
        ModelConfig(
            id="claude-3",
            provider=LLMProvider.ANTHROPIC,
            model_name="claude-3-sonnet",
            context_length=200000,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
            avg_latency=0.6,
            capabilities={ModelCapability.CHAT, ModelCapability.LONG_CONTEXT, ModelCapability.REASONING}
        ),
        ModelConfig(
            id="local-llama",
            provider=LLMProvider.LOCAL,
            model_name="llama-3-8b",
            context_length=8192,
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
            avg_latency=0.1,
            capabilities={ModelCapability.CHAT}
        ),
    ]

    for model in models:
        router.register_model(model)
        print(f"   Registered: {model.id} ({model.provider.value})")

    print()

    # 2. Cost-Optimized Routing
    print("2. COST-OPTIMIZED ROUTING:")
    print("-" * 40)

    request = LLMRequest(
        messages=[ChatMessage(role="user", content="What is 2+2?")]
    )

    response = await router.complete(request)

    print(f"   Selected model: {response.model}")
    print(f"   Provider: {response.provider}")
    print(f"   Cost: ${response.cost:.6f}")
    print(f"   Latency: {response.latency:.3f}s")
    print()

    # 3. Capability-Based Routing
    print("3. CAPABILITY-BASED ROUTING:")
    print("-" * 40)

    router.set_strategy(RoutingStrategy.CAPABILITY_MATCH)

    request = LLMRequest(
        messages=[ChatMessage(role="user", content="Write a Python function")],
        required_capabilities={ModelCapability.CODE}
    )

    response = await router.complete(request)

    print(f"   Required: CODE capability")
    print(f"   Selected: {response.model}")
    print()

    # 4. Quality-Optimized Routing
    print("4. QUALITY-OPTIMIZED ROUTING:")
    print("-" * 40)

    router.set_strategy(RoutingStrategy.QUALITY_OPTIMIZED)

    request = LLMRequest(
        messages=[ChatMessage(role="user", content="Complex reasoning task")]
    )

    response = await router.complete(request)

    print(f"   Selected model: {response.model}")
    print(f"   (Highest quality/cost model)")
    print()

    # 5. Simple Chat Interface
    print("5. SIMPLE CHAT:")
    print("-" * 40)

    router.set_strategy(RoutingStrategy.COST_OPTIMIZED)

    reply = await router.chat(
        "Hello, how are you?",
        system="You are a friendly assistant."
    )

    print(f"   Response: {reply[:60]}...")
    print()

    # 6. Caching
    print("6. RESPONSE CACHING:")
    print("-" * 40)

    request = LLMRequest(
        messages=[ChatMessage(role="user", content="Cache test")]
    )

    r1 = await router.complete(request)
    r2 = await router.complete(request)

    print(f"   First request - from cache: {r1.from_cache}")
    print(f"   Second request - from cache: {r2.from_cache}")
    print()

    # 7. Usage Statistics
    print("7. USAGE STATISTICS:")
    print("-" * 40)

    usage = router.get_usage()
    for model_id, stats in usage.items():
        if stats.total_requests > 0:
            print(f"   {model_id}:")
            print(f"      Requests: {stats.total_requests}")
            print(f"      Tokens: {stats.total_input_tokens}+{stats.total_output_tokens}")
            print(f"      Cost: ${stats.total_cost:.6f}")

    print(f"\n   Total cost: ${router.get_total_cost():.6f}")
    print()

    # 8. Streaming
    print("8. STREAMING RESPONSE:")
    print("-" * 40)

    request = LLMRequest(
        messages=[ChatMessage(role="user", content="Stream test")],
        stream=True
    )

    print("   Streaming: ", end="")
    async for chunk in router.stream(request):
        print(chunk, end="", flush=True)
    print("\n")

    # 9. Round Robin
    print("9. ROUND ROBIN ROUTING:")
    print("-" * 40)

    router.set_strategy(RoutingStrategy.ROUND_ROBIN)

    for i in range(4):
        request = LLMRequest(
            messages=[ChatMessage(role="user", content=f"Request {i+1}")]
        )
        response = await router.complete(request, use_cache=False)
        print(f"   Request {i+1}: {response.model}")
    print()

    # 10. Fallback Chain
    print("10. FALLBACK CHAIN:")
    print("-" * 40)

    router.set_fallback_order(["gpt-3.5", "local-llama"])
    print("   Fallback order: gpt-3.5 -> local-llama")
    print()

    # 11. Model Enable/Disable
    print("11. MODEL MANAGEMENT:")
    print("-" * 40)

    router.disable_model("gpt-4")
    print("   Disabled: gpt-4")

    models = router.list_models()
    enabled = [m.id for m in models if m.enabled]
    print(f"   Enabled models: {enabled}")

    router.enable_model("gpt-4")
    print("   Re-enabled: gpt-4")
    print()

    # 12. Token Counting
    print("12. TOKEN COUNTING:")
    print("-" * 40)

    messages = [
        ChatMessage(role="system", content="You are helpful."),
        ChatMessage(role="user", content="This is a test message for token counting.")
    ]

    tokens = TokenCounter.count_messages(messages)
    print(f"   Message count: {len(messages)}")
    print(f"   Estimated tokens: {tokens}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - LLM Router Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
