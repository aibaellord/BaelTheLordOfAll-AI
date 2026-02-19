"""
BAEL LLM Provider Bridge - Real Provider Implementations

This module implements actual connections to LLM providers,
replacing the simulated providers with real API calls.

Supports:
- OpenRouter (aggregates many free models)
- Anthropic Claude
- OpenAI GPT
- Groq (ultra-fast inference)
- Ollama (local models)
- Google Gemini
- Mistral

Zero-Cost Strategy:
- Rotate between free tiers
- Track usage against limits
- Fallback chains when limits hit
- Local models as ultimate fallback
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple
from uuid import uuid4
from .oauth import OAuthConfig, OAuthTokenManager

logger = logging.getLogger("BAEL.Providers")


# =============================================================================
# CONFIGURATION
# =============================================================================

class ProviderType(Enum):
    """Supported LLM providers."""
    OPENROUTER = "openrouter"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GROQ = "groq"
    OLLAMA = "ollama"
    GOOGLE = "google"
    MISTRAL = "mistral"
    LOCAL = "local"


class CostTier(Enum):
    """Cost tier classification."""
    FREE = "free"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PREMIUM = "premium"


@dataclass
class ProviderModel:
    """Model available from a provider."""
    provider: ProviderType
    model_id: str
    display_name: str
    cost_tier: CostTier
    context_length: int
    supports_streaming: bool
    supports_functions: bool
    supports_vision: bool
    rate_limit_rpm: int  # Requests per minute
    rate_limit_tpd: int  # Tokens per day
    cost_per_1k_input: float
    cost_per_1k_output: float
    quality_score: float  # 0-1, estimated quality
    latency_ms: float  # Average latency


@dataclass
class ProviderConfig:
    """Configuration for a provider."""
    provider_type: ProviderType
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    organization_id: Optional[str] = None
    enabled: bool = True
    priority: int = 1  # Lower = higher priority
    timeout_seconds: int = 60
    max_retries: int = 3

    # Rate limit tracking
    requests_this_minute: int = 0
    tokens_today: int = 0
    last_minute_reset: datetime = field(default_factory=datetime.now)
    last_day_reset: datetime = field(default_factory=datetime.now)


@dataclass
class CompletionRequest:
    """Request for LLM completion."""
    messages: List[Dict[str, str]]
    model: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    stream: bool = False
    stop: Optional[List[str]] = None
    functions: Optional[List[Dict]] = None
    function_call: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompletionResponse:
    """Response from LLM completion."""
    id: str
    content: str
    model: str
    provider: ProviderType
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: float
    cost: float
    finish_reason: str
    function_call: Optional[Dict] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# PROVIDER REGISTRY
# =============================================================================

# Free and low-cost models across providers
PROVIDER_MODELS = {
    ProviderType.OPENROUTER: [
        ProviderModel(
            provider=ProviderType.OPENROUTER,
            model_id="meta-llama/llama-3.1-8b-instruct:free",
            display_name="Llama 3.1 8B (Free)",
            cost_tier=CostTier.FREE,
            context_length=128000,
            supports_streaming=True,
            supports_functions=True,
            supports_vision=False,
            rate_limit_rpm=20,
            rate_limit_tpd=100000,
            cost_per_1k_input=0,
            cost_per_1k_output=0,
            quality_score=0.75,
            latency_ms=500
        ),
        ProviderModel(
            provider=ProviderType.OPENROUTER,
            model_id="google/gemma-2-9b-it:free",
            display_name="Gemma 2 9B (Free)",
            cost_tier=CostTier.FREE,
            context_length=8192,
            supports_streaming=True,
            supports_functions=False,
            supports_vision=False,
            rate_limit_rpm=20,
            rate_limit_tpd=100000,
            cost_per_1k_input=0,
            cost_per_1k_output=0,
            quality_score=0.7,
            latency_ms=400
        ),
        ProviderModel(
            provider=ProviderType.OPENROUTER,
            model_id="mistralai/mistral-7b-instruct:free",
            display_name="Mistral 7B (Free)",
            cost_tier=CostTier.FREE,
            context_length=32768,
            supports_streaming=True,
            supports_functions=False,
            supports_vision=False,
            rate_limit_rpm=20,
            rate_limit_tpd=100000,
            cost_per_1k_input=0,
            cost_per_1k_output=0,
            quality_score=0.72,
            latency_ms=350
        ),
        ProviderModel(
            provider=ProviderType.OPENROUTER,
            model_id="qwen/qwen-2-7b-instruct:free",
            display_name="Qwen 2 7B (Free)",
            cost_tier=CostTier.FREE,
            context_length=32768,
            supports_streaming=True,
            supports_functions=False,
            supports_vision=False,
            rate_limit_rpm=20,
            rate_limit_tpd=100000,
            cost_per_1k_input=0,
            cost_per_1k_output=0,
            quality_score=0.73,
            latency_ms=400
        ),
    ],
    ProviderType.GROQ: [
        ProviderModel(
            provider=ProviderType.GROQ,
            model_id="llama-3.1-70b-versatile",
            display_name="Llama 3.1 70B",
            cost_tier=CostTier.FREE,
            context_length=128000,
            supports_streaming=True,
            supports_functions=True,
            supports_vision=False,
            rate_limit_rpm=30,
            rate_limit_tpd=500000,
            cost_per_1k_input=0,
            cost_per_1k_output=0,
            quality_score=0.85,
            latency_ms=200
        ),
        ProviderModel(
            provider=ProviderType.GROQ,
            model_id="llama-3.1-8b-instant",
            display_name="Llama 3.1 8B Instant",
            cost_tier=CostTier.FREE,
            context_length=128000,
            supports_streaming=True,
            supports_functions=True,
            supports_vision=False,
            rate_limit_rpm=30,
            rate_limit_tpd=500000,
            cost_per_1k_input=0,
            cost_per_1k_output=0,
            quality_score=0.75,
            latency_ms=100
        ),
        ProviderModel(
            provider=ProviderType.GROQ,
            model_id="mixtral-8x7b-32768",
            display_name="Mixtral 8x7B",
            cost_tier=CostTier.FREE,
            context_length=32768,
            supports_streaming=True,
            supports_functions=True,
            supports_vision=False,
            rate_limit_rpm=30,
            rate_limit_tpd=500000,
            cost_per_1k_input=0,
            cost_per_1k_output=0,
            quality_score=0.8,
            latency_ms=150
        ),
    ],
    ProviderType.OLLAMA: [
        ProviderModel(
            provider=ProviderType.OLLAMA,
            model_id="llama3.2",
            display_name="Llama 3.2 (Local)",
            cost_tier=CostTier.FREE,
            context_length=128000,
            supports_streaming=True,
            supports_functions=True,
            supports_vision=True,
            rate_limit_rpm=1000,
            rate_limit_tpd=10000000,
            cost_per_1k_input=0,
            cost_per_1k_output=0,
            quality_score=0.78,
            latency_ms=1000
        ),
        ProviderModel(
            provider=ProviderType.OLLAMA,
            model_id="qwen2.5:7b",
            display_name="Qwen 2.5 7B (Local)",
            cost_tier=CostTier.FREE,
            context_length=32768,
            supports_streaming=True,
            supports_functions=True,
            supports_vision=False,
            rate_limit_rpm=1000,
            rate_limit_tpd=10000000,
            cost_per_1k_input=0,
            cost_per_1k_output=0,
            quality_score=0.76,
            latency_ms=800
        ),
        ProviderModel(
            provider=ProviderType.OLLAMA,
            model_id="deepseek-r1:8b",
            display_name="DeepSeek R1 8B (Local)",
            cost_tier=CostTier.FREE,
            context_length=64000,
            supports_streaming=True,
            supports_functions=True,
            supports_vision=False,
            rate_limit_rpm=1000,
            rate_limit_tpd=10000000,
            cost_per_1k_input=0,
            cost_per_1k_output=0,
            quality_score=0.82,
            latency_ms=900
        ),
    ],
}


# =============================================================================
# BASE PROVIDER
# =============================================================================

class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._client = None
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the provider connection."""
        pass

    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Execute a completion request."""
        pass

    @abstractmethod
    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Stream a completion request."""
        pass

    def can_handle_request(self, request: CompletionRequest) -> bool:
        """Check if provider can handle the request."""
        self._update_rate_limits()

        # Check rate limits
        models = PROVIDER_MODELS.get(self.config.provider_type, [])
        if not models:
            return False

        model = models[0]  # Use first model for limits

        if self.config.requests_this_minute >= model.rate_limit_rpm:
            return False

        if self.config.tokens_today >= model.rate_limit_tpd:
            return False

        return True

    def _update_rate_limits(self) -> None:
        """Reset rate limit counters if needed."""
        now = datetime.now()

        # Reset minute counter
        if (now - self.config.last_minute_reset).total_seconds() >= 60:
            self.config.requests_this_minute = 0
            self.config.last_minute_reset = now

        # Reset day counter
        if (now - self.config.last_day_reset).total_seconds() >= 86400:
            self.config.tokens_today = 0
            self.config.last_day_reset = now

    def record_usage(self, tokens: int) -> None:
        """Record token usage for rate limiting."""
        self.config.requests_this_minute += 1
        self.config.tokens_today += tokens


# =============================================================================
# OPENROUTER PROVIDER
# =============================================================================

class OpenRouterProvider(BaseProvider):
    """OpenRouter API provider - aggregates many free models."""

    async def initialize(self) -> bool:
        """Initialize OpenRouter connection."""
        try:
            # Get API key from config or environment
            api_key = self.config.api_key or os.environ.get("OPENROUTER_API_KEY")

            if not api_key:
                logger.warning("OpenRouter API key not found")
                return False

            self.config.api_key = api_key
            self.config.base_url = "https://openrouter.ai/api/v1"
            self._initialized = True

            logger.info("OpenRouter provider initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize OpenRouter: {e}")
            return False

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Execute completion via OpenRouter."""
        start_time = time.time()

        try:
            import aiohttp

            # Select model
            model = request.model or "meta-llama/llama-3.1-8b-instruct:free"

            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://bael.ai",
                "X-Title": "BAEL AI System"
            }

            payload = {
                "model": model,
                "messages": request.messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "stream": False
            }

            if request.stop:
                payload["stop"] = request.stop

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as response:
                    data = await response.json()

            latency = (time.time() - start_time) * 1000

            # Parse response
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)

            self.record_usage(input_tokens + output_tokens)

            return CompletionResponse(
                id=data.get("id", str(uuid4())),
                content=content,
                model=model,
                provider=ProviderType.OPENROUTER,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                latency_ms=latency,
                cost=0.0,  # Free tier
                finish_reason=data["choices"][0].get("finish_reason", "stop")
            )

        except ImportError:
            logger.error("aiohttp not installed. Run: pip install aiohttp")
            raise
        except Exception as e:
            logger.error(f"OpenRouter completion failed: {e}")
            raise

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Stream completion via OpenRouter."""
        try:
            import aiohttp

            model = request.model or "meta-llama/llama-3.1-8b-instruct:free"

            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://bael.ai",
                "X-Title": "BAEL AI System"
            }

            payload = {
                "model": model,
                "messages": request.messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "stream": True
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as response:
                    async for line in response.content:
                        line = line.decode().strip()
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                            except json.JSONDecodeError:
                                continue

        except ImportError:
            logger.error("aiohttp not installed")
            raise


# =============================================================================
# GROQ PROVIDER
# =============================================================================

class GroqProvider(BaseProvider):
    """Groq API provider - ultra-fast inference."""

    async def initialize(self) -> bool:
        """Initialize Groq connection."""
        try:
            api_key = self.config.api_key or os.environ.get("GROQ_API_KEY")

            if not api_key:
                logger.warning("Groq API key not found")
                return False

            self.config.api_key = api_key
            self.config.base_url = "https://api.groq.com/openai/v1"
            self._initialized = True

            logger.info("Groq provider initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Groq: {e}")
            return False

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Execute completion via Groq."""
        start_time = time.time()

        try:
            import aiohttp

            model = request.model or "llama-3.1-70b-versatile"

            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": model,
                "messages": request.messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "stream": False
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as response:
                    data = await response.json()

            latency = (time.time() - start_time) * 1000

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)

            self.record_usage(input_tokens + output_tokens)

            return CompletionResponse(
                id=data.get("id", str(uuid4())),
                content=content,
                model=model,
                provider=ProviderType.GROQ,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                latency_ms=latency,
                cost=0.0,
                finish_reason=data["choices"][0].get("finish_reason", "stop")
            )

        except Exception as e:
            logger.error(f"Groq completion failed: {e}")
            raise

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Stream completion via Groq."""
        try:
            import aiohttp

            model = request.model or "llama-3.1-70b-versatile"

            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": model,
                "messages": request.messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "stream": True
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as response:
                    async for line in response.content:
                        line = line.decode().strip()
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"Groq streaming failed: {e}")
            raise


# =============================================================================
# OLLAMA PROVIDER
# =============================================================================

class OllamaProvider(BaseProvider):
    """Ollama local provider - runs models locally."""

    async def initialize(self) -> bool:
        """Initialize Ollama connection."""
        try:
            self.config.base_url = self.config.base_url or "http://localhost:11434"

            # Check if Ollama is running
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.config.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        self._initialized = True
                        logger.info("Ollama provider initialized")
                        return True

            logger.warning("Ollama not running or not accessible")
            return False

        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Execute completion via Ollama."""
        start_time = time.time()

        try:
            import aiohttp

            model = request.model or "llama3.2"

            # Convert messages to Ollama format
            prompt = self._format_messages(request.messages)

            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens
                }
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.base_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as response:
                    data = await response.json()

            latency = (time.time() - start_time) * 1000

            content = data.get("response", "")

            # Estimate tokens (Ollama doesn't always return this)
            input_tokens = len(prompt.split()) * 1.3
            output_tokens = len(content.split()) * 1.3

            return CompletionResponse(
                id=str(uuid4()),
                content=content,
                model=model,
                provider=ProviderType.OLLAMA,
                input_tokens=int(input_tokens),
                output_tokens=int(output_tokens),
                total_tokens=int(input_tokens + output_tokens),
                latency_ms=latency,
                cost=0.0,  # Always free
                finish_reason="stop"
            )

        except Exception as e:
            logger.error(f"Ollama completion failed: {e}")
            raise

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Stream completion via Ollama."""
        try:
            import aiohttp

            model = request.model or "llama3.2"
            prompt = self._format_messages(request.messages)

            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens
                }
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.base_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as response:
                    async for line in response.content:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}")
            raise

    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format messages for Ollama."""
        parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                parts.append(f"System: {content}")
            elif role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        return "\n\n".join(parts) + "\n\nAssistant:"


# =============================================================================
# GOOGLE PROVIDER (OAuth example)
# =============================================================================


class GoogleProvider(BaseProvider):
    """Google (Gemini) provider example using OAuth token manager."""

    async def initialize(self) -> bool:
        try:
            # Build OAuth config from environment if available
            client_id = os.environ.get("GOOGLE_CLIENT_ID")
            client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
            refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")
            token_url = os.environ.get("GOOGLE_TOKEN_URL", "https://oauth2.googleapis.com/token")

            oauth_cfg = OAuthConfig(
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                token_url=token_url,
                cache_path=os.environ.get("GOOGLE_OAUTH_CACHE", ".cache/google_oauth.json")
            )

            token = await OAuthTokenManager.refresh_or_get(oauth_cfg)

            if not token:
                logger.warning("Google OAuth token not available; skipping Google provider")
                return False

            # Store token in api_key for reuse by complete()/stream()
            self.config.api_key = token
            self.config.base_url = os.environ.get("GOOGLE_API_BASE", "https://gemini.googleapis.com/v1")
            self._initialized = True
            logger.info("Google provider initialized (OAuth)")
            return True

        except Exception as e:
            logger.warning(f"Google provider initialization failed: {e}")
            return False

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        start_time = time.time()
        try:
            import aiohttp

            model = request.model or "gemini-1.5"  # default

            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": model,
                "messages": request.messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.base_url}/models/{model}:generate",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as resp:
                    data = await resp.json()

            latency = (time.time() - start_time) * 1000

            # Best-effort parsing; provider responses vary
            content = ""
            if isinstance(data, dict):
                # Gemini style may include 'candidates' or 'output'
                if "candidates" in data and data["candidates"]:
                    content = data["candidates"][0].get("content", "")
                elif "output" in data:
                    # output can be structured
                    content = json.dumps(data["output"]) if not isinstance(data["output"], str) else data["output"]

            input_tokens = 0
            output_tokens = 0

            self.record_usage(input_tokens + output_tokens)

            return CompletionResponse(
                id=data.get("id", str(uuid4())) if isinstance(data, dict) else str(uuid4()),
                content=content,
                model=model,
                provider=ProviderType.GOOGLE,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                latency_ms=latency,
                cost=0.0,
                finish_reason="stop"
            )

        except Exception as e:
            logger.error(f"Google completion failed: {e}")
            raise

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        # For now, fallback to non-streaming complete
        resp = await self.complete(request)
        yield resp.content


# =============================================================================
# PROVIDER ROUTER
# =============================================================================

class ProviderRouter:
    """
    Intelligent router for LLM providers.

    Features:
    - Zero-cost routing: Prioritizes free providers
    - Fallback chains: Automatic failover when limits hit
    - Load balancing: Distributes requests across providers
    - Cost tracking: Ensures zero-cost operation
    """

    def __init__(self):
        self._providers: Dict[ProviderType, BaseProvider] = {}
        self._priority_order: List[ProviderType] = []
        self._initialized = False

        # Metrics
        self._metrics = {
            "total_requests": 0,
            "provider_usage": {},
            "total_tokens": 0,
            "total_cost": 0.0,
            "errors": 0,
            "fallbacks": 0
        }

    async def initialize(self) -> None:
        """Initialize all providers."""
        logger.info("Initializing Provider Router...")

        # Initialize providers in priority order
        provider_configs = [
            (ProviderType.GROQ, GroqProvider, 1),
            (ProviderType.OPENROUTER, OpenRouterProvider, 2),
            (ProviderType.OLLAMA, OllamaProvider, 3),
            (ProviderType.GOOGLE, GoogleProvider, 4),
        ]

        for ptype, provider_class, priority in provider_configs:
            try:
                config = ProviderConfig(provider_type=ptype, priority=priority)
                provider = provider_class(config)

                if await provider.initialize():
                    self._providers[ptype] = provider
                    self._priority_order.append(ptype)
                    self._metrics["provider_usage"][ptype.value] = 0

            except Exception as e:
                logger.warning(f"Failed to initialize {ptype.value}: {e}")

        # Sort by priority
        self._priority_order.sort(key=lambda p: self._providers[p].config.priority)

        self._initialized = True
        logger.info(f"Initialized {len(self._providers)} providers: {[p.value for p in self._priority_order]}")

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Route completion request to best available provider."""
        if not self._initialized:
            await self.initialize()

        self._metrics["total_requests"] += 1

        # Try providers in priority order
        last_error = None

        for ptype in self._priority_order:
            provider = self._providers.get(ptype)
            if not provider:
                continue

            if not provider.can_handle_request(request):
                logger.debug(f"Provider {ptype.value} at rate limit, trying next")
                continue

            try:
                response = await provider.complete(request)

                # Update metrics
                self._metrics["provider_usage"][ptype.value] += 1
                self._metrics["total_tokens"] += response.total_tokens
                self._metrics["total_cost"] += response.cost

                return response

            except Exception as e:
                logger.warning(f"Provider {ptype.value} failed: {e}")
                last_error = e
                self._metrics["fallbacks"] += 1
                continue

        # All providers failed
        self._metrics["errors"] += 1
        raise Exception(f"All providers failed. Last error: {last_error}")

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Stream completion from best available provider."""
        if not self._initialized:
            await self.initialize()

        for ptype in self._priority_order:
            provider = self._providers.get(ptype)
            if not provider or not provider.can_handle_request(request):
                continue

            try:
                async for chunk in provider.stream(request):
                    yield chunk
                return

            except Exception as e:
                logger.warning(f"Provider {ptype.value} streaming failed: {e}")
                continue

        raise Exception("All providers failed for streaming")

    async def ensemble_complete(self, request: CompletionRequest, top_k: int = 2, timeout: int = 20) -> CompletionResponse:
        """Query the top_k providers in parallel and return the best response.

        Strategy:
        - Select up to `top_k` available providers (by priority and availability).
        - Run their `complete()` calls in parallel with timeouts.
        - Score responses by provider model `quality_score` and response length.
        - Return the highest-scoring single `CompletionResponse`.
        - If none succeed, raise an exception.
        """
        if not self._initialized:
            await self.initialize()

        # Select candidate providers
        candidates: List[Tuple[ProviderType, BaseProvider]] = []
        for ptype in self._priority_order:
            provider = self._providers.get(ptype)
            if not provider:
                continue
            if provider.can_handle_request(request):
                candidates.append((ptype, provider))
            if len(candidates) >= top_k:
                break

        if not candidates:
            raise Exception("No available providers for ensemble")

        async def _call_provider(ptype: ProviderType, provider: BaseProvider):
            try:
                coro = provider.complete(request)
                return await asyncio.wait_for(coro, timeout=timeout)
            except Exception as e:
                logger.debug(f"Ensemble provider {ptype.value} call failed: {e}")
                return None

        tasks = [asyncio.create_task(_call_provider(ptype, prov)) for ptype, prov in candidates]

        done, pending = await asyncio.wait(tasks, timeout=timeout)

        responses: List[CompletionResponse] = [t.result() for t in done if t.result() is not None]

        for p in pending:
            p.cancel()

        if not responses:
            self._metrics["errors"] += 1
            raise Exception("Ensemble failed: no providers returned responses")

        # Score responses using provider quality and content length
        def _score(resp: CompletionResponse) -> float:
            quality = 0.5
            # try to find quality score for model
            models = PROVIDER_MODELS.get(resp.provider, [])
            for m in models:
                if m.model_id == resp.model or resp.model.startswith(m.model_id.split(":")[0]):
                    quality = m.quality_score
                    break
            length_score = max(1.0, len(resp.content))
            return quality * (1.0 + (length_score / 200.0))

        best = max(responses, key=_score)

        # Update metrics
        self._metrics["total_tokens"] += best.total_tokens
        self._metrics["total_cost"] += best.cost
        self._metrics["provider_usage"].setdefault(best.provider.value, 0)
        self._metrics["provider_usage"][best.provider.value] += 1

        return best

    def get_available_models(self) -> List[ProviderModel]:
        """Get all available models across initialized providers."""
        models = []
        for ptype in self._priority_order:
            if ptype in PROVIDER_MODELS:
                models.extend(PROVIDER_MODELS[ptype])
        return models

    def get_metrics(self) -> Dict[str, Any]:
        """Get router metrics."""
        return {
            **self._metrics,
            "providers_available": [p.value for p in self._priority_order],
            "zero_cost_maintained": self._metrics["total_cost"] == 0
        }


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

# Global router instance
_router: Optional[ProviderRouter] = None


async def get_router() -> ProviderRouter:
    """Get or create the global provider router."""
    global _router
    if _router is None:
        _router = ProviderRouter()
        await _router.initialize()
    return _router


async def complete(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096
) -> CompletionResponse:
    """Quick completion using the global router."""
    router = await get_router()
    request = CompletionRequest(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens
    )
    return await router.complete(request)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate provider router capabilities."""
    router = ProviderRouter()
    await router.initialize()

    print("Available Models:")
    for model in router.get_available_models():
        print(f"  [{model.provider.value}] {model.display_name} - {model.cost_tier.value}")

    print("\nTesting completion...")

    request = CompletionRequest(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is 2+2? Reply in one word."}
        ],
        max_tokens=10,
        temperature=0
    )

    try:
        response = await router.complete(request)
        print(f"\nResponse: {response.content}")
        print(f"Provider: {response.provider.value}")
        print(f"Model: {response.model}")
        print(f"Latency: {response.latency_ms:.0f}ms")
        print(f"Tokens: {response.total_tokens}")
        print(f"Cost: ${response.cost:.6f}")
    except Exception as e:
        print(f"Error: {e}")

    print("\nMetrics:")
    print(json.dumps(router.get_metrics(), indent=2))


if __name__ == "__main__":
    asyncio.run(demo())
