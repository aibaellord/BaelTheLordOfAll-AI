"""
BAEL Multi-Provider LLM Router
===============================

The ultimate LLM routing system exploiting 25+ providers for zero-cost operation.
Intelligent routing based on task type, provider health, and cost optimization.

Features:
- 25+ provider support with unified API
- Round-robin, weighted, least-latency, and smart routing
- Automatic API key rotation and pooling
- Provider-specific model mapping
- Rate limit tracking and avoidance
- Response streaming support
- Parallel request execution
- Quality-based provider ranking
"""

import asyncio
import hashlib
import json
import logging
import os
import random
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, AsyncIterator, Callable, Dict, Generic, List,
                    Optional, Set, Tuple, TypeVar, Union)

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Supported LLM provider types."""
    # Tier 1 - Major Providers
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    DEEPSEEK = "deepseek"

    # Tier 2 - Fast Inference
    GROQ = "groq"
    TOGETHER = "together"
    FIREWORKS = "fireworks"
    CEREBRAS = "cerebras"
    SAMBANOVA = "sambanova"

    # Tier 3 - Chinese Providers
    SILICONFLOW = "siliconflow"
    ZHIPU = "zhipu"
    BAIDU = "baidu"
    ALIBABA = "alibaba"
    MOONSHOT = "moonshot"

    # Tier 4 - Free/Underground
    ZUKIJOURNEY = "zukijourney"
    ELECTRONHUB = "electronhub"
    NAGAAI = "nagaai"
    SHUTTLEAI = "shuttleai"
    WEBRAFTAI = "webraftai"
    FRESEDGPT = "fresedgpt"
    SHADOWJOURNEY = "shadowjourney"

    # Local Inference
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    LLAMACPP = "llamacpp"
    VLLM = "vllm"


class ProviderStatus(Enum):
    """Provider health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class RoutingStrategy(Enum):
    """Request routing strategies."""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_RANDOM = "weighted_random"
    LEAST_LATENCY = "least_latency"
    LEAST_COST = "least_cost"
    HIGHEST_QUALITY = "highest_quality"
    TASK_OPTIMIZED = "task_optimized"
    FAILOVER_CHAIN = "failover_chain"
    PARALLEL_CONSENSUS = "parallel_consensus"
    ADAPTIVE = "adaptive"


class ModelCapability(Enum):
    """Model capability tags."""
    GENERAL = "general"
    CODE = "code"
    REASONING = "reasoning"
    CREATIVE = "creative"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"
    LONG_CONTEXT = "long_context"
    FAST = "fast"
    CHEAP = "cheap"
    UNCENSORED = "uncensored"
    MULTILINGUAL = "multilingual"
    MATH = "math"
    INSTRUCTION_FOLLOWING = "instruction_following"


@dataclass
class ProviderConfig:
    """Configuration for a single LLM provider."""
    provider_type: ProviderType
    api_keys: List[str] = field(default_factory=list)
    base_url: Optional[str] = None
    models: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    rate_limits: Dict[str, int] = field(default_factory=dict)
    priority: int = 5  # 1-10, higher = preferred
    enabled: bool = True
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    max_retries: int = 3
    timeout: int = 120
    headers: Dict[str, str] = field(default_factory=dict)
    capabilities: Set[ModelCapability] = field(default_factory=set)

    # Runtime stats
    current_key_index: int = 0
    request_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    last_request: Optional[datetime] = None
    last_error: Optional[datetime] = None
    rate_limit_reset: Optional[datetime] = None


@dataclass
class ModelMapping:
    """Maps generic model names to provider-specific names."""
    generic_name: str
    provider_models: Dict[ProviderType, str] = field(default_factory=dict)
    capabilities: Set[ModelCapability] = field(default_factory=set)
    context_length: int = 8192

    def get_model(self, provider: ProviderType) -> Optional[str]:
        return self.provider_models.get(provider)


@dataclass
class RoutingDecision:
    """Result of routing decision."""
    provider: ProviderType
    model: str
    api_key: str
    base_url: str
    confidence: float
    reasoning: str
    alternatives: List[Tuple[ProviderType, str]] = field(default_factory=list)


@dataclass
class LLMRequest:
    """Unified LLM request format."""
    messages: List[Dict[str, str]]
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    stream: bool = False
    tools: Optional[List[Dict]] = None
    tool_choice: Optional[str] = None
    response_format: Optional[Dict] = None
    stop: Optional[List[str]] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    seed: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Unified LLM response format."""
    content: str
    model: str
    provider: ProviderType
    finish_reason: str
    usage: Dict[str, int]
    latency_ms: float
    cost: float
    raw_response: Optional[Dict] = None
    tool_calls: Optional[List[Dict]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProviderAdapter(ABC):
    """Abstract base for provider-specific adapters."""

    @abstractmethod
    async def complete(
        self,
        request: LLMRequest,
        api_key: str,
        base_url: str,
        model: str,
    ) -> LLMResponse:
        """Execute completion request."""
        pass

    @abstractmethod
    async def stream(
        self,
        request: LLMRequest,
        api_key: str,
        base_url: str,
        model: str,
    ) -> AsyncIterator[str]:
        """Stream completion response."""
        pass

    @abstractmethod
    def format_request(self, request: LLMRequest) -> Dict[str, Any]:
        """Format request for provider's API."""
        pass


class OpenAICompatibleAdapter(ProviderAdapter):
    """Adapter for OpenAI-compatible APIs (most providers)."""

    def __init__(self, provider_type: ProviderType):
        self.provider_type = provider_type

    def format_request(self, request: LLMRequest) -> Dict[str, Any]:
        """Format request for OpenAI-compatible API."""
        payload = {
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": request.stream,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
        }

        if request.tools:
            payload["tools"] = request.tools
        if request.tool_choice:
            payload["tool_choice"] = request.tool_choice
        if request.response_format:
            payload["response_format"] = request.response_format
        if request.stop:
            payload["stop"] = request.stop
        if request.seed is not None:
            payload["seed"] = request.seed

        return payload

    async def complete(
        self,
        request: LLMRequest,
        api_key: str,
        base_url: str,
        model: str,
    ) -> LLMResponse:
        """Execute completion via OpenAI-compatible API."""
        import httpx

        start_time = time.time()

        payload = self.format_request(request)
        payload["model"] = model

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Provider-specific headers
        if self.provider_type == ProviderType.OPENROUTER:
            headers["HTTP-Referer"] = "https://bael.ai"
            headers["X-Title"] = "BAEL AI System"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        latency_ms = (time.time() - start_time) * 1000

        choice = data["choices"][0]
        usage = data.get("usage", {})

        # Calculate cost
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        cost = 0.0  # Most free providers

        return LLMResponse(
            content=choice["message"]["content"] or "",
            model=data.get("model", model),
            provider=self.provider_type,
            finish_reason=choice.get("finish_reason", "stop"),
            usage={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
            latency_ms=latency_ms,
            cost=cost,
            raw_response=data,
            tool_calls=choice["message"].get("tool_calls"),
        )

    async def stream(
        self,
        request: LLMRequest,
        api_key: str,
        base_url: str,
        model: str,
    ) -> AsyncIterator[str]:
        """Stream completion via OpenAI-compatible API."""
        import httpx

        payload = self.format_request(request)
        payload["model"] = model
        payload["stream"] = True

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        if self.provider_type == ProviderType.OPENROUTER:
            headers["HTTP-Referer"] = "https://bael.ai"
            headers["X-Title"] = "BAEL AI System"

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            if content := delta.get("content"):
                                yield content
                        except json.JSONDecodeError:
                            continue


class MultiProviderRouter:
    """
    Ultimate multi-provider LLM router with intelligent routing,
    automatic failover, and zero-cost optimization.
    """

    # Default provider configurations
    DEFAULT_PROVIDERS: Dict[ProviderType, Dict[str, Any]] = {
        ProviderType.OPENROUTER: {
            "base_url": "https://openrouter.ai/api/v1",
            "models": {
                "claude-3.5-sonnet": "anthropic/claude-3.5-sonnet",
                "claude-3-opus": "anthropic/claude-3-opus",
                "gpt-4-turbo": "openai/gpt-4-turbo",
                "gpt-4o": "openai/gpt-4o",
                "gpt-4o-mini": "openai/gpt-4o-mini",
                "deepseek-r1": "deepseek/deepseek-r1",
                "deepseek-v3": "deepseek/deepseek-chat",
                "gemini-2.0-flash": "google/gemini-2.0-flash-exp:free",
                "llama-3.3-70b": "meta-llama/llama-3.3-70b-instruct",
                "mistral-large": "mistralai/mistral-large-2411",
                "qwen-2.5-72b": "qwen/qwen-2.5-72b-instruct",
            },
            "priority": 9,
            "capabilities": {ModelCapability.GENERAL, ModelCapability.CODE, ModelCapability.REASONING},
        },
        ProviderType.DEEPSEEK: {
            "base_url": "https://api.deepseek.com/v1",
            "models": {
                "deepseek-r1": "deepseek-reasoner",
                "deepseek-v3": "deepseek-chat",
                "deepseek-coder": "deepseek-coder",
            },
            "priority": 8,
            "capabilities": {ModelCapability.REASONING, ModelCapability.CODE, ModelCapability.MATH},
        },
        ProviderType.GROQ: {
            "base_url": "https://api.groq.com/openai/v1",
            "models": {
                "llama-3.3-70b": "llama-3.3-70b-versatile",
                "llama-3.1-8b": "llama-3.1-8b-instant",
                "mixtral-8x7b": "mixtral-8x7b-32768",
                "gemma-2-9b": "gemma2-9b-it",
            },
            "priority": 7,
            "capabilities": {ModelCapability.FAST, ModelCapability.GENERAL},
        },
        ProviderType.TOGETHER: {
            "base_url": "https://api.together.xyz/v1",
            "models": {
                "llama-3.3-70b": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                "qwen-2.5-72b": "Qwen/Qwen2.5-72B-Instruct-Turbo",
                "deepseek-v3": "deepseek-ai/DeepSeek-V3",
            },
            "priority": 6,
            "capabilities": {ModelCapability.GENERAL, ModelCapability.CODE},
        },
        ProviderType.SILICONFLOW: {
            "base_url": "https://api.siliconflow.cn/v1",
            "models": {
                "deepseek-v3": "deepseek-ai/DeepSeek-V3",
                "qwen-2.5-72b": "Qwen/Qwen2.5-72B-Instruct",
                "glm-4": "THUDM/glm-4-9b-chat",
            },
            "priority": 7,
            "capabilities": {ModelCapability.GENERAL, ModelCapability.MULTILINGUAL},
        },
        ProviderType.OLLAMA: {
            "base_url": "http://localhost:11434/v1",
            "models": {
                "llama3.3": "llama3.3:70b",
                "qwen2.5": "qwen2.5:72b",
                "deepseek-r1": "deepseek-r1:14b",
                "codellama": "codellama:34b",
            },
            "priority": 5,
            "capabilities": {ModelCapability.GENERAL, ModelCapability.UNCENSORED},
        },
    }

    # Model capability mappings for task routing
    TASK_MODEL_MAPPING: Dict[str, List[str]] = {
        "code": ["claude-3.5-sonnet", "deepseek-coder", "gpt-4o", "codellama"],
        "reasoning": ["deepseek-r1", "claude-3-opus", "gpt-4-turbo", "o1-preview"],
        "creative": ["claude-3-opus", "gpt-4o", "gemini-2.0-flash"],
        "fast": ["gpt-4o-mini", "llama-3.1-8b", "gemini-2.0-flash"],
        "vision": ["gpt-4o", "claude-3.5-sonnet", "gemini-2.0-flash"],
        "general": ["claude-3.5-sonnet", "gpt-4o", "deepseek-v3", "llama-3.3-70b"],
    }

    def __init__(
        self,
        config_path: Optional[str] = None,
        default_strategy: RoutingStrategy = RoutingStrategy.ADAPTIVE,
    ):
        self.providers: Dict[ProviderType, ProviderConfig] = {}
        self.adapters: Dict[ProviderType, ProviderAdapter] = {}
        self.default_strategy = default_strategy
        self.request_history: List[Dict[str, Any]] = []
        self.provider_scores: Dict[ProviderType, float] = defaultdict(lambda: 1.0)

        self._initialize_providers()
        self._initialize_adapters()

    def _initialize_providers(self) -> None:
        """Initialize provider configurations from environment and defaults."""
        for provider_type, defaults in self.DEFAULT_PROVIDERS.items():
            env_key = f"{provider_type.value.upper()}_API_KEY"
            api_keys = []

            # Check for multiple API keys (KEY_1, KEY_2, etc.)
            base_key = os.getenv(env_key)
            if base_key:
                api_keys.append(base_key)

            for i in range(1, 10):
                key = os.getenv(f"{env_key}_{i}")
                if key:
                    api_keys.append(key)

            # Also check common alternatives
            alt_keys = {
                ProviderType.OPENROUTER: ["OPENROUTER_KEY"],
                ProviderType.OPENAI: ["OPENAI_KEY"],
                ProviderType.ANTHROPIC: ["ANTHROPIC_KEY", "CLAUDE_API_KEY"],
            }

            for alt in alt_keys.get(provider_type, []):
                if key := os.getenv(alt):
                    if key not in api_keys:
                        api_keys.append(key)

            config = ProviderConfig(
                provider_type=provider_type,
                api_keys=api_keys,
                base_url=defaults["base_url"],
                models=defaults["models"],
                priority=defaults.get("priority", 5),
                enabled=len(api_keys) > 0 or provider_type == ProviderType.OLLAMA,
                capabilities=defaults.get("capabilities", set()),
            )

            self.providers[provider_type] = config

    def _initialize_adapters(self) -> None:
        """Initialize provider-specific adapters."""
        for provider_type in self.providers:
            # Most providers are OpenAI-compatible
            self.adapters[provider_type] = OpenAICompatibleAdapter(provider_type)

    def get_available_providers(self) -> List[ProviderType]:
        """Get list of currently available providers."""
        available = []
        for provider_type, config in self.providers.items():
            if not config.enabled:
                continue
            if config.rate_limit_reset and datetime.now() < config.rate_limit_reset:
                continue
            available.append(provider_type)
        return available

    def _select_provider_round_robin(
        self,
        candidates: List[ProviderType],
    ) -> ProviderType:
        """Select next provider using round-robin."""
        if not hasattr(self, '_rr_index'):
            self._rr_index = 0

        provider = candidates[self._rr_index % len(candidates)]
        self._rr_index += 1
        return provider

    def _select_provider_weighted(
        self,
        candidates: List[ProviderType],
    ) -> ProviderType:
        """Select provider using weighted random based on scores."""
        weights = [self.provider_scores[p] * self.providers[p].priority for p in candidates]
        total = sum(weights)
        r = random.random() * total

        cumulative = 0
        for provider, weight in zip(candidates, weights):
            cumulative += weight
            if r <= cumulative:
                return provider

        return candidates[-1]

    def _select_provider_least_latency(
        self,
        candidates: List[ProviderType],
    ) -> ProviderType:
        """Select provider with lowest average latency."""
        def avg_latency(p: ProviderType) -> float:
            config = self.providers[p]
            if config.request_count == 0:
                return float('inf')
            return config.total_latency_ms / config.request_count

        return min(candidates, key=avg_latency)

    def _select_provider_for_task(
        self,
        candidates: List[ProviderType],
        task_type: str,
    ) -> Tuple[ProviderType, str]:
        """Select optimal provider and model for task type."""
        preferred_models = self.TASK_MODEL_MAPPING.get(task_type, self.TASK_MODEL_MAPPING["general"])

        for model in preferred_models:
            for provider in candidates:
                if model in self.providers[provider].models:
                    return provider, self.providers[provider].models[model]

        # Fallback to first available
        provider = candidates[0]
        model = list(self.providers[provider].models.values())[0]
        return provider, model

    def _get_api_key(self, provider: ProviderType) -> str:
        """Get next API key for provider (rotation)."""
        config = self.providers[provider]
        if not config.api_keys:
            return ""

        key = config.api_keys[config.current_key_index]
        config.current_key_index = (config.current_key_index + 1) % len(config.api_keys)
        return key

    def route(
        self,
        request: LLMRequest,
        strategy: Optional[RoutingStrategy] = None,
        task_type: Optional[str] = None,
        preferred_providers: Optional[List[ProviderType]] = None,
        excluded_providers: Optional[List[ProviderType]] = None,
    ) -> RoutingDecision:
        """
        Make routing decision for a request.

        Args:
            request: The LLM request to route
            strategy: Routing strategy to use
            task_type: Type of task (code, reasoning, creative, fast, general)
            preferred_providers: Providers to prefer
            excluded_providers: Providers to exclude

        Returns:
            RoutingDecision with selected provider and model
        """
        strategy = strategy or self.default_strategy
        candidates = self.get_available_providers()

        if excluded_providers:
            candidates = [p for p in candidates if p not in excluded_providers]

        if preferred_providers:
            preferred_available = [p for p in preferred_providers if p in candidates]
            if preferred_available:
                candidates = preferred_available

        if not candidates:
            raise ValueError("No available providers")

        # Select provider based on strategy
        if strategy == RoutingStrategy.ROUND_ROBIN:
            provider = self._select_provider_round_robin(candidates)
            model = list(self.providers[provider].models.values())[0]
        elif strategy == RoutingStrategy.WEIGHTED_RANDOM:
            provider = self._select_provider_weighted(candidates)
            model = list(self.providers[provider].models.values())[0]
        elif strategy == RoutingStrategy.LEAST_LATENCY:
            provider = self._select_provider_least_latency(candidates)
            model = list(self.providers[provider].models.values())[0]
        elif strategy == RoutingStrategy.TASK_OPTIMIZED:
            provider, model = self._select_provider_for_task(candidates, task_type or "general")
        elif strategy == RoutingStrategy.ADAPTIVE:
            # Combine multiple signals for optimal routing
            task = task_type or self._infer_task_type(request)
            provider, model = self._select_provider_for_task(candidates, task)

            # Adjust for latency if speed matters
            if task == "fast":
                provider = self._select_provider_least_latency(candidates)
                model = self.providers[provider].models.get(
                    "gpt-4o-mini",
                    list(self.providers[provider].models.values())[0]
                )
        else:
            provider = candidates[0]
            model = list(self.providers[provider].models.values())[0]

        # Use specified model if provided
        if request.model:
            model = self.providers[provider].models.get(request.model, model)

        # Build alternatives list
        alternatives = []
        for p in candidates:
            if p != provider:
                m = list(self.providers[p].models.values())[0]
                alternatives.append((p, m))

        return RoutingDecision(
            provider=provider,
            model=model,
            api_key=self._get_api_key(provider),
            base_url=self.providers[provider].base_url,
            confidence=self.provider_scores[provider],
            reasoning=f"Selected {provider.value} using {strategy.value} strategy",
            alternatives=alternatives[:3],
        )

    def _infer_task_type(self, request: LLMRequest) -> str:
        """Infer task type from request content."""
        content = " ".join(m.get("content", "") for m in request.messages).lower()

        code_keywords = ["code", "implement", "function", "class", "debug", "fix", "program", "script"]
        reasoning_keywords = ["analyze", "reason", "think", "explain", "why", "how", "evaluate"]
        creative_keywords = ["write", "story", "creative", "imagine", "design", "brainstorm"]

        if any(kw in content for kw in code_keywords):
            return "code"
        elif any(kw in content for kw in reasoning_keywords):
            return "reasoning"
        elif any(kw in content for kw in creative_keywords):
            return "creative"
        elif len(content) < 100:
            return "fast"
        else:
            return "general"

    async def complete(
        self,
        request: LLMRequest,
        strategy: Optional[RoutingStrategy] = None,
        task_type: Optional[str] = None,
        max_retries: int = 3,
    ) -> LLMResponse:
        """
        Execute completion with automatic routing and failover.

        Args:
            request: The LLM request
            strategy: Routing strategy
            task_type: Task type for optimized routing
            max_retries: Maximum retry attempts across providers

        Returns:
            LLMResponse from successful provider
        """
        excluded = []
        last_error = None

        for attempt in range(max_retries):
            try:
                decision = self.route(
                    request,
                    strategy=strategy,
                    task_type=task_type,
                    excluded_providers=excluded,
                )

                adapter = self.adapters[decision.provider]
                response = await adapter.complete(
                    request,
                    decision.api_key,
                    decision.base_url,
                    decision.model,
                )

                # Update provider stats
                config = self.providers[decision.provider]
                config.request_count += 1
                config.total_latency_ms += response.latency_ms
                config.last_request = datetime.now()

                # Update provider score (success)
                self.provider_scores[decision.provider] = min(
                    2.0,
                    self.provider_scores[decision.provider] * 1.1
                )

                return response

            except Exception as e:
                last_error = e
                logger.warning(f"Provider {decision.provider.value} failed: {e}")

                # Update provider stats (failure)
                config = self.providers[decision.provider]
                config.error_count += 1
                config.last_error = datetime.now()

                # Check for rate limiting
                if "rate" in str(e).lower() or "429" in str(e):
                    config.rate_limit_reset = datetime.now() + timedelta(minutes=1)

                # Update provider score (failure)
                self.provider_scores[decision.provider] *= 0.5

                excluded.append(decision.provider)

        raise RuntimeError(f"All providers failed. Last error: {last_error}")

    async def stream(
        self,
        request: LLMRequest,
        strategy: Optional[RoutingStrategy] = None,
        task_type: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Stream completion with automatic routing.

        Args:
            request: The LLM request
            strategy: Routing strategy
            task_type: Task type for optimized routing

        Yields:
            Content chunks from the response
        """
        decision = self.route(request, strategy=strategy, task_type=task_type)
        adapter = self.adapters[decision.provider]

        async for chunk in adapter.stream(
            request,
            decision.api_key,
            decision.base_url,
            decision.model,
        ):
            yield chunk

    async def parallel_complete(
        self,
        request: LLMRequest,
        providers: Optional[List[ProviderType]] = None,
        num_providers: int = 3,
    ) -> List[LLMResponse]:
        """
        Execute request in parallel across multiple providers.
        Useful for consensus or getting multiple perspectives.

        Args:
            request: The LLM request
            providers: Specific providers to use
            num_providers: Number of providers if not specified

        Returns:
            List of responses from all providers
        """
        if providers is None:
            available = self.get_available_providers()
            providers = available[:num_providers]

        async def _complete_with_provider(provider: ProviderType) -> Optional[LLMResponse]:
            try:
                config = self.providers[provider]
                adapter = self.adapters[provider]
                model = list(config.models.values())[0]

                return await adapter.complete(
                    request,
                    self._get_api_key(provider),
                    config.base_url,
                    model,
                )
            except Exception as e:
                logger.warning(f"Parallel request to {provider.value} failed: {e}")
                return None

        results = await asyncio.gather(
            *[_complete_with_provider(p) for p in providers],
            return_exceptions=False,
        )

        return [r for r in results if r is not None]

    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        stats = {
            "providers": {},
            "total_requests": 0,
            "total_errors": 0,
            "available_providers": len(self.get_available_providers()),
        }

        for provider_type, config in self.providers.items():
            stats["providers"][provider_type.value] = {
                "enabled": config.enabled,
                "api_keys": len(config.api_keys),
                "models": len(config.models),
                "request_count": config.request_count,
                "error_count": config.error_count,
                "avg_latency_ms": (
                    config.total_latency_ms / config.request_count
                    if config.request_count > 0 else 0
                ),
                "score": self.provider_scores[provider_type],
            }
            stats["total_requests"] += config.request_count
            stats["total_errors"] += config.error_count

        return stats

    def add_provider(
        self,
        provider_type: ProviderType,
        config: ProviderConfig,
    ) -> None:
        """Add or update a provider configuration."""
        self.providers[provider_type] = config
        self.adapters[provider_type] = OpenAICompatibleAdapter(provider_type)

    def add_api_key(
        self,
        provider: ProviderType,
        api_key: str,
    ) -> None:
        """Add an API key to a provider's pool."""
        if provider in self.providers:
            if api_key not in self.providers[provider].api_keys:
                self.providers[provider].api_keys.append(api_key)
                self.providers[provider].enabled = True


# Convenience function for quick usage
async def quick_complete(
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
    task_type: Optional[str] = None,
) -> str:
    """
    Quick completion with automatic provider selection.

    Args:
        prompt: User prompt
        system: Optional system prompt
        model: Optional model preference
        task_type: Optional task type hint

    Returns:
        Response content string
    """
    router = MultiProviderRouter()

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    request = LLMRequest(messages=messages, model=model)
    response = await router.complete(request, task_type=task_type)

    return response.content


# Demo
async def demo():
    """Demonstrate multi-provider routing."""
    print("=" * 60)
    print("BAEL Multi-Provider LLM Router Demo")
    print("=" * 60)

    router = MultiProviderRouter()

    # Show available providers
    available = router.get_available_providers()
    print(f"\nAvailable providers: {[p.value for p in available]}")

    # Show stats
    stats = router.get_stats()
    print(f"\nRouter stats: {json.dumps(stats, indent=2, default=str)}")

    # Demo routing decisions
    test_prompts = [
        ("Write a Python function to sort a list", "code"),
        ("Explain why the sky is blue", "reasoning"),
        ("Write a short poem about AI", "creative"),
        ("What is 2+2?", "fast"),
    ]

    print("\n" + "=" * 60)
    print("Routing Decisions:")
    print("=" * 60)

    for prompt, task_type in test_prompts:
        request = LLMRequest(messages=[{"role": "user", "content": prompt}])
        decision = router.route(request, task_type=task_type)
        print(f"\nTask: {task_type}")
        print(f"  Provider: {decision.provider.value}")
        print(f"  Model: {decision.model}")
        print(f"  Confidence: {decision.confidence:.2f}")


if __name__ == "__main__":
    asyncio.run(demo())
