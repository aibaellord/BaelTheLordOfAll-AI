"""
FREE LLM API MULTI-PROVIDER HUB - Zero-Cost Intelligence Layer
Inspired by LLM-Red-Team projects for maximum free API utilization.

SUPPORTED FREE PROVIDERS:
- Kimi AI (kimi-free-api) - Long-context specialist, K1 thinking model
- DeepSeek (deepseek-free-api) - DeepSeek-V3/R1, deep reasoning
- Qwen (qwen-free-api) - Alibaba's all-rounder, image generation
- GLM (glm-free-api) - ChatGLM-4-Plus, strongest agents
- Doubao (doubao-free-api) - ByteDance, web search specialist
- MiniMax (minimax-free-api) - Natural voice synthesis
- Step (step-free-api) - Multimodal specialist
- Jimeng (jimeng-free-api) - Image generation top-tier

Features:
- Automatic token rotation across providers
- Intelligent routing based on task type
- Fallback chain for 100% uptime
- Session management and cleanup
- Rate limiting and quota optimization
- Zero-cost operation for unlimited scale
- Streaming support for all providers
- Multi-modal capability aggregation

Target: 3,000+ lines for complete free API mastery
"""

import asyncio
import aiohttp
import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Set, Tuple
import uuid
import base64
from collections import defaultdict

logger = logging.getLogger("BAEL.FreeLLMHub")

# ============================================================================
# PROVIDER ENUMS
# ============================================================================

class FreeProvider(Enum):
    """Free LLM API providers."""
    KIMI = "kimi"           # Long context, K1 thinking
    DEEPSEEK = "deepseek"   # V3/R1 reasoning
    QWEN = "qwen"           # All-rounder, image gen
    GLM = "glm"             # Agent specialist
    DOUBAO = "doubao"       # Web search
    MINIMAX = "minimax"     # Voice synthesis
    STEP = "step"           # Multimodal
    JIMENG = "jimeng"       # Image generation

class ProviderStrength(Enum):
    """Provider specialization strengths."""
    LONG_CONTEXT = "long_context"
    DEEP_REASONING = "deep_reasoning"
    CODE_GENERATION = "code_generation"
    WEB_SEARCH = "web_search"
    IMAGE_GENERATION = "image_generation"
    VOICE_SYNTHESIS = "voice_synthesis"
    MULTIMODAL = "multimodal"
    AGENT_CONTROL = "agent_control"
    THINKING_MODEL = "thinking_model"

class TaskRequirement(Enum):
    """Task requirements for routing."""
    GENERAL = "general"
    LONG_DOCUMENT = "long_document"
    CODE = "code"
    RESEARCH = "research"
    CREATIVE = "creative"
    IMAGE = "image"
    VOICE = "voice"
    REASONING = "reasoning"

# ============================================================================
# PROVIDER PROFILES
# ============================================================================

@dataclass
class ProviderProfile:
    """Profile for a free LLM provider."""
    provider: FreeProvider
    name: str
    base_url: str
    strengths: List[ProviderStrength]
    context_window: int
    supports_streaming: bool = True
    supports_vision: bool = False
    supports_search: bool = False
    supports_image_gen: bool = False
    supports_voice: bool = False
    rate_limit_rpm: int = 60
    cooldown_seconds: float = 1.0
    priority: int = 5  # 1-10, higher = more preferred

@dataclass
class TokenConfig:
    """Token configuration for provider."""
    provider: FreeProvider
    tokens: List[str]
    current_index: int = 0
    last_rotation: datetime = field(default_factory=datetime.now)
    failures: Dict[str, int] = field(default_factory=dict)

@dataclass
class ProviderSession:
    """Active session with provider."""
    session_id: str
    provider: FreeProvider
    token: str
    created_at: datetime
    last_used: datetime
    request_count: int = 0
    error_count: int = 0
    conversation_id: Optional[str] = None

# ============================================================================
# PROVIDER CONFIGURATIONS
# ============================================================================

PROVIDER_PROFILES = {
    FreeProvider.KIMI: ProviderProfile(
        provider=FreeProvider.KIMI,
        name="Kimi AI",
        base_url="http://localhost:8000",  # Local kimi-free-api instance
        strengths=[
            ProviderStrength.LONG_CONTEXT,
            ProviderStrength.THINKING_MODEL,
            ProviderStrength.MULTIMODAL
        ],
        context_window=1000000,  # 1M tokens!
        supports_streaming=True,
        supports_vision=True,
        supports_search=True,
        rate_limit_rpm=30,
        priority=9
    ),
    FreeProvider.DEEPSEEK: ProviderProfile(
        provider=FreeProvider.DEEPSEEK,
        name="DeepSeek",
        base_url="http://localhost:8001",
        strengths=[
            ProviderStrength.DEEP_REASONING,
            ProviderStrength.CODE_GENERATION,
            ProviderStrength.THINKING_MODEL
        ],
        context_window=128000,
        supports_streaming=True,
        supports_search=True,
        rate_limit_rpm=60,
        priority=10  # Highest - best value
    ),
    FreeProvider.QWEN: ProviderProfile(
        provider=FreeProvider.QWEN,
        name="Qwen 2.5",
        base_url="http://localhost:8002",
        strengths=[
            ProviderStrength.CODE_GENERATION,
            ProviderStrength.MULTIMODAL,
            ProviderStrength.IMAGE_GENERATION
        ],
        context_window=128000,
        supports_streaming=True,
        supports_vision=True,
        supports_image_gen=True,
        rate_limit_rpm=30,
        priority=8
    ),
    FreeProvider.GLM: ProviderProfile(
        provider=FreeProvider.GLM,
        name="ChatGLM-4-Plus",
        base_url="http://localhost:8003",
        strengths=[
            ProviderStrength.AGENT_CONTROL,
            ProviderStrength.CODE_GENERATION,
            ProviderStrength.THINKING_MODEL
        ],
        context_window=128000,
        supports_streaming=True,
        supports_vision=True,
        supports_search=True,
        rate_limit_rpm=30,
        priority=8
    ),
    FreeProvider.DOUBAO: ProviderProfile(
        provider=FreeProvider.DOUBAO,
        name="Doubao",
        base_url="http://localhost:8004",
        strengths=[
            ProviderStrength.WEB_SEARCH,
            ProviderStrength.MULTIMODAL
        ],
        context_window=64000,
        supports_streaming=True,
        supports_search=True,
        rate_limit_rpm=30,
        priority=7
    ),
    FreeProvider.MINIMAX: ProviderProfile(
        provider=FreeProvider.MINIMAX,
        name="MiniMax Hailuo",
        base_url="http://localhost:8005",
        strengths=[
            ProviderStrength.VOICE_SYNTHESIS,
            ProviderStrength.MULTIMODAL
        ],
        context_window=64000,
        supports_streaming=True,
        supports_voice=True,
        rate_limit_rpm=20,
        priority=6
    ),
    FreeProvider.STEP: ProviderProfile(
        provider=FreeProvider.STEP,
        name="Step YueWen",
        base_url="http://localhost:8006",
        strengths=[
            ProviderStrength.MULTIMODAL,
            ProviderStrength.LONG_CONTEXT
        ],
        context_window=256000,
        supports_streaming=True,
        supports_vision=True,
        rate_limit_rpm=30,
        priority=7
    ),
    FreeProvider.JIMENG: ProviderProfile(
        provider=FreeProvider.JIMENG,
        name="Jimeng 3.0",
        base_url="http://localhost:8007",
        strengths=[
            ProviderStrength.IMAGE_GENERATION
        ],
        context_window=8000,
        supports_streaming=False,
        supports_image_gen=True,
        rate_limit_rpm=10,
        priority=6
    )
}

# Task to provider mapping
TASK_ROUTING = {
    TaskRequirement.GENERAL: [FreeProvider.DEEPSEEK, FreeProvider.QWEN, FreeProvider.GLM],
    TaskRequirement.LONG_DOCUMENT: [FreeProvider.KIMI, FreeProvider.STEP],
    TaskRequirement.CODE: [FreeProvider.DEEPSEEK, FreeProvider.QWEN, FreeProvider.GLM],
    TaskRequirement.RESEARCH: [FreeProvider.DOUBAO, FreeProvider.KIMI, FreeProvider.DEEPSEEK],
    TaskRequirement.CREATIVE: [FreeProvider.QWEN, FreeProvider.GLM, FreeProvider.KIMI],
    TaskRequirement.IMAGE: [FreeProvider.JIMENG, FreeProvider.QWEN],
    TaskRequirement.VOICE: [FreeProvider.MINIMAX],
    TaskRequirement.REASONING: [FreeProvider.DEEPSEEK, FreeProvider.KIMI, FreeProvider.GLM]
}

# ============================================================================
# TOKEN MANAGER
# ============================================================================

class TokenManager:
    """Manage and rotate tokens across providers."""

    def __init__(self):
        self.configs: Dict[FreeProvider, TokenConfig] = {}
        self.session_cache: Dict[str, ProviderSession] = {}
        self.rate_limiters: Dict[FreeProvider, List[float]] = defaultdict(list)

    def add_tokens(self, provider: FreeProvider, tokens: List[str]) -> None:
        """Add tokens for a provider."""
        self.configs[provider] = TokenConfig(
            provider=provider,
            tokens=tokens
        )

    def get_token(self, provider: FreeProvider) -> Optional[str]:
        """Get next available token with rotation."""
        if provider not in self.configs:
            return None

        config = self.configs[provider]
        if not config.tokens:
            return None

        # Rotate through tokens
        token = config.tokens[config.current_index]
        config.current_index = (config.current_index + 1) % len(config.tokens)
        config.last_rotation = datetime.now()

        return token

    def mark_failure(self, provider: FreeProvider, token: str) -> None:
        """Mark token as failed."""
        if provider in self.configs:
            config = self.configs[provider]
            config.failures[token] = config.failures.get(token, 0) + 1

    def check_rate_limit(self, provider: FreeProvider) -> bool:
        """Check if rate limit allows request."""
        profile = PROVIDER_PROFILES.get(provider)
        if not profile:
            return True

        now = time.time()
        window = 60  # 1 minute window

        # Clean old entries
        self.rate_limiters[provider] = [
            t for t in self.rate_limiters[provider]
            if now - t < window
        ]

        # Check limit
        if len(self.rate_limiters[provider]) >= profile.rate_limit_rpm:
            return False

        self.rate_limiters[provider].append(now)
        return True

# ============================================================================
# INTELLIGENT ROUTER
# ============================================================================

class IntelligentRouter:
    """Route requests to optimal free provider."""

    def __init__(self, token_manager: TokenManager):
        self.token_manager = token_manager
        self.provider_stats: Dict[FreeProvider, Dict[str, float]] = defaultdict(
            lambda: {"success": 0, "failure": 0, "latency": 0.0}
        )

    def analyze_task(self, prompt: str, **kwargs) -> TaskRequirement:
        """Analyze task to determine requirements."""
        prompt_lower = prompt.lower()

        # Check for specific requirements
        if len(prompt) > 50000 or "document" in prompt_lower or "analyze this file" in prompt_lower:
            return TaskRequirement.LONG_DOCUMENT

        if any(kw in prompt_lower for kw in ["code", "function", "implement", "debug", "program"]):
            return TaskRequirement.CODE

        if any(kw in prompt_lower for kw in ["search", "find", "latest", "news", "research"]):
            return TaskRequirement.RESEARCH

        if any(kw in prompt_lower for kw in ["think", "reason", "analyze", "solve", "complex"]):
            return TaskRequirement.REASONING

        if any(kw in prompt_lower for kw in ["image", "picture", "draw", "generate image"]):
            return TaskRequirement.IMAGE

        if any(kw in prompt_lower for kw in ["speak", "voice", "audio", "read aloud"]):
            return TaskRequirement.VOICE

        if any(kw in prompt_lower for kw in ["creative", "story", "imagine", "write"]):
            return TaskRequirement.CREATIVE

        return TaskRequirement.GENERAL

    def select_provider(self, task: TaskRequirement,
                       excluded: Optional[Set[FreeProvider]] = None) -> Optional[FreeProvider]:
        """Select best provider for task."""
        excluded = excluded or set()
        candidates = TASK_ROUTING.get(task, TASK_ROUTING[TaskRequirement.GENERAL])

        # Filter available providers
        available = [
            p for p in candidates
            if p not in excluded
            and self.token_manager.check_rate_limit(p)
            and p in self.token_manager.configs
        ]

        if not available:
            # Fallback to any available
            available = [
                p for p in FreeProvider
                if p not in excluded
                and self.token_manager.check_rate_limit(p)
                and p in self.token_manager.configs
            ]

        if not available:
            return None

        # Sort by priority and success rate
        def score(p: FreeProvider) -> float:
            profile = PROVIDER_PROFILES.get(p)
            stats = self.provider_stats[p]

            priority_score = profile.priority if profile else 5
            total = stats["success"] + stats["failure"]
            success_rate = stats["success"] / max(total, 1)

            return priority_score * 0.6 + success_rate * 10 * 0.4

        available.sort(key=score, reverse=True)
        return available[0]

    def record_result(self, provider: FreeProvider, success: bool, latency: float) -> None:
        """Record request result for learning."""
        stats = self.provider_stats[provider]
        if success:
            stats["success"] += 1
        else:
            stats["failure"] += 1
        # Running average latency
        stats["latency"] = (stats["latency"] * 0.9) + (latency * 0.1)

# ============================================================================
# UNIFIED API CLIENT
# ============================================================================

class UnifiedAPIClient:
    """Unified client for all free LLM APIs."""

    def __init__(self):
        self.token_manager = TokenManager()
        self.router = IntelligentRouter(self.token_manager)
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.active_conversations: Dict[str, Dict[str, Any]] = {}

    async def initialize(self) -> None:
        """Initialize HTTP session."""
        if not self.http_session:
            self.http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=120)
            )

    async def close(self) -> None:
        """Close HTTP session."""
        if self.http_session:
            await self.http_session.close()
            self.http_session = None

    def configure_provider(self, provider: FreeProvider,
                          tokens: List[str],
                          base_url: Optional[str] = None) -> None:
        """Configure a provider with tokens."""
        self.token_manager.add_tokens(provider, tokens)
        if base_url and provider in PROVIDER_PROFILES:
            PROVIDER_PROFILES[provider].base_url = base_url

    async def chat(self,
                   prompt: str,
                   system: Optional[str] = None,
                   provider: Optional[FreeProvider] = None,
                   stream: bool = False,
                   **kwargs) -> Dict[str, Any]:
        """Send chat request to optimal provider."""
        await self.initialize()

        # Determine task and provider
        task = self.router.analyze_task(prompt, **kwargs)

        if not provider:
            provider = self.router.select_provider(task)

        if not provider:
            return {"error": "No available provider", "content": None}

        # Get token and profile
        token = self.token_manager.get_token(provider)
        profile = PROVIDER_PROFILES.get(provider)

        if not token or not profile:
            return {"error": f"Provider {provider.value} not configured", "content": None}

        # Build request
        start_time = time.time()

        try:
            if stream:
                return await self._stream_request(provider, profile, token, prompt, system, **kwargs)
            else:
                return await self._standard_request(provider, profile, token, prompt, system, **kwargs)

        except Exception as e:
            latency = time.time() - start_time
            self.router.record_result(provider, False, latency)
            self.token_manager.mark_failure(provider, token)

            # Try fallback
            fallback = self.router.select_provider(task, excluded={provider})
            if fallback:
                return await self.chat(prompt, system, fallback, stream, **kwargs)

            return {"error": str(e), "content": None}

    async def _standard_request(self, provider: FreeProvider,
                                profile: ProviderProfile,
                                token: str,
                                prompt: str,
                                system: Optional[str],
                                **kwargs) -> Dict[str, Any]:
        """Send standard request."""
        url = f"{profile.base_url}/v1/chat/completions"

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._get_model_name(provider),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "stream": False
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        start_time = time.time()

        async with self.http_session.post(url, json=payload, headers=headers) as response:
            latency = time.time() - start_time

            if response.status == 200:
                data = await response.json()
                self.router.record_result(provider, True, latency)

                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                return {
                    "content": content,
                    "provider": provider.value,
                    "model": self._get_model_name(provider),
                    "latency": latency,
                    "tokens_used": data.get("usage", {})
                }
            else:
                error = await response.text()
                self.router.record_result(provider, False, latency)
                return {"error": error, "content": None}

    async def _stream_request(self, provider: FreeProvider,
                              profile: ProviderProfile,
                              token: str,
                              prompt: str,
                              system: Optional[str],
                              **kwargs) -> AsyncIterator[str]:
        """Stream response from provider."""
        url = f"{profile.base_url}/v1/chat/completions"

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._get_model_name(provider),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "stream": True
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        start_time = time.time()
        full_content = []

        async with self.http_session.post(url, json=payload, headers=headers) as response:
            if response.status == 200:
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if delta:
                                full_content.append(delta)
                                yield delta
                        except json.JSONDecodeError:
                            continue

                latency = time.time() - start_time
                self.router.record_result(provider, True, latency)
            else:
                error = await response.text()
                self.router.record_result(provider, False, time.time() - start_time)
                yield f"[ERROR]: {error}"

    def _get_model_name(self, provider: FreeProvider) -> str:
        """Get model name for provider."""
        model_names = {
            FreeProvider.KIMI: "kimi",
            FreeProvider.DEEPSEEK: "deepseek-chat",
            FreeProvider.QWEN: "qwen-turbo",
            FreeProvider.GLM: "glm-4-plus",
            FreeProvider.DOUBAO: "doubao-pro",
            FreeProvider.MINIMAX: "minimax-text",
            FreeProvider.STEP: "step-1",
            FreeProvider.JIMENG: "jimeng-3.0"
        }
        return model_names.get(provider, "default")

# ============================================================================
# MULTI-PROVIDER ORCHESTRATOR
# ============================================================================

class MultiProviderOrchestrator:
    """Orchestrate multiple free LLM providers for maximum capability."""

    def __init__(self):
        self.client = UnifiedAPIClient()
        self.ensemble_enabled = True
        self.logger = logging.getLogger("BAEL.MultiProviderOrchestrator")

    async def initialize(self) -> None:
        """Initialize orchestrator."""
        await self.client.initialize()

    async def close(self) -> None:
        """Close orchestrator."""
        await self.client.close()

    def configure_all_providers(self, config: Dict[str, Dict[str, Any]]) -> None:
        """Configure all providers from config dict."""
        for provider_name, provider_config in config.items():
            try:
                provider = FreeProvider(provider_name)
                tokens = provider_config.get("tokens", [])
                base_url = provider_config.get("base_url")

                if tokens:
                    self.client.configure_provider(provider, tokens, base_url)
                    self.logger.info(f"Configured {provider.value} with {len(tokens)} tokens")
            except ValueError:
                self.logger.warning(f"Unknown provider: {provider_name}")

    async def smart_complete(self,
                            prompt: str,
                            system: Optional[str] = None,
                            use_ensemble: bool = False,
                            **kwargs) -> Dict[str, Any]:
        """Smart completion with automatic routing."""
        if use_ensemble and self.ensemble_enabled:
            return await self._ensemble_complete(prompt, system, **kwargs)
        else:
            return await self.client.chat(prompt, system, **kwargs)

    async def _ensemble_complete(self,
                                 prompt: str,
                                 system: Optional[str] = None,
                                 **kwargs) -> Dict[str, Any]:
        """Get responses from multiple providers and synthesize."""
        # Select top 3 providers
        task = self.client.router.analyze_task(prompt)
        providers = TASK_ROUTING.get(task, TASK_ROUTING[TaskRequirement.GENERAL])[:3]

        # Query all in parallel
        tasks = [
            self.client.chat(prompt, system, provider, **kwargs)
            for provider in providers
            if provider in self.client.token_manager.configs
        ]

        if not tasks:
            return await self.client.chat(prompt, system, **kwargs)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful responses
        valid_responses = [
            r for r in results
            if isinstance(r, dict) and r.get("content")
        ]

        if not valid_responses:
            return {"error": "All providers failed", "content": None}

        if len(valid_responses) == 1:
            return valid_responses[0]

        # Synthesize responses
        return await self._synthesize_responses(valid_responses, prompt)

    async def _synthesize_responses(self,
                                    responses: List[Dict[str, Any]],
                                    original_prompt: str) -> Dict[str, Any]:
        """Synthesize multiple provider responses into best answer."""
        # For now, return the longest/most detailed response
        best = max(responses, key=lambda r: len(r.get("content", "")))
        best["ensemble"] = True
        best["sources"] = [r.get("provider") for r in responses]
        return best

    async def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate image using image-capable provider."""
        # Use Jimeng or Qwen for image generation
        for provider in [FreeProvider.JIMENG, FreeProvider.QWEN]:
            if provider in self.client.token_manager.configs:
                profile = PROVIDER_PROFILES.get(provider)
                if profile and profile.supports_image_gen:
                    return await self._image_request(provider, prompt, **kwargs)

        return {"error": "No image generation provider available", "content": None}

    async def _image_request(self, provider: FreeProvider,
                            prompt: str, **kwargs) -> Dict[str, Any]:
        """Send image generation request."""
        profile = PROVIDER_PROFILES.get(provider)
        token = self.client.token_manager.get_token(provider)

        if not profile or not token:
            return {"error": "Provider not configured", "content": None}

        url = f"{profile.base_url}/v1/images/generations"

        payload = {
            "prompt": prompt,
            "n": kwargs.get("n", 1),
            "size": kwargs.get("size", "1024x1024")
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        await self.client.initialize()

        async with self.client.http_session.post(url, json=payload, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    "images": data.get("data", []),
                    "provider": provider.value
                }
            else:
                error = await response.text()
                return {"error": error, "content": None}

    async def web_search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Perform web search using search-capable provider."""
        # Use Doubao or Kimi for web search
        for provider in [FreeProvider.DOUBAO, FreeProvider.KIMI, FreeProvider.DEEPSEEK]:
            if provider in self.client.token_manager.configs:
                profile = PROVIDER_PROFILES.get(provider)
                if profile and profile.supports_search:
                    # Add search instruction
                    search_prompt = f"Search the web and find the latest information about: {query}"
                    return await self.client.chat(search_prompt, provider=provider, **kwargs)

        return {"error": "No search provider available", "content": None}

    async def long_document_analysis(self,
                                     document: str,
                                     question: str,
                                     **kwargs) -> Dict[str, Any]:
        """Analyze long document using long-context provider."""
        # Use Kimi (1M context) or Step (256K context)
        for provider in [FreeProvider.KIMI, FreeProvider.STEP]:
            if provider in self.client.token_manager.configs:
                prompt = f"""Analyze the following document and answer the question.

DOCUMENT:
{document}

QUESTION:
{question}

Provide a detailed, accurate answer based on the document content."""

                return await self.client.chat(prompt, provider=provider, **kwargs)

        return {"error": "No long-context provider available", "content": None}

    async def deep_reasoning(self,
                            problem: str,
                            use_thinking_model: bool = True,
                            **kwargs) -> Dict[str, Any]:
        """Perform deep reasoning using thinking models."""
        # Use DeepSeek R1 or Kimi K1
        for provider in [FreeProvider.DEEPSEEK, FreeProvider.KIMI, FreeProvider.GLM]:
            if provider in self.client.token_manager.configs:
                prompt = f"""Think deeply and systematically about this problem.
Show your reasoning step by step.

PROBLEM:
{problem}

Provide a thorough analysis and solution."""

                return await self.client.chat(prompt, provider=provider, **kwargs)

        return {"error": "No reasoning provider available", "content": None}

# ============================================================================
# ZERO-COST SCALING ENGINE
# ============================================================================

class ZeroCostScalingEngine:
    """Scale AI capabilities at zero cost using free APIs."""

    def __init__(self):
        self.orchestrator = MultiProviderOrchestrator()
        self.request_queue: asyncio.Queue = asyncio.Queue()
        self.workers: List[asyncio.Task] = []
        self.running = False

    async def start(self, num_workers: int = 5) -> None:
        """Start the scaling engine."""
        await self.orchestrator.initialize()
        self.running = True

        for i in range(num_workers):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)

    async def stop(self) -> None:
        """Stop the scaling engine."""
        self.running = False

        for worker in self.workers:
            worker.cancel()

        await self.orchestrator.close()

    async def _worker(self, worker_id: int) -> None:
        """Worker that processes requests."""
        while self.running:
            try:
                request = await asyncio.wait_for(
                    self.request_queue.get(),
                    timeout=1.0
                )

                result = await self.orchestrator.smart_complete(
                    request["prompt"],
                    request.get("system"),
                    **request.get("kwargs", {})
                )

                if request.get("callback"):
                    await request["callback"](result)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")

    async def submit(self,
                    prompt: str,
                    system: Optional[str] = None,
                    callback: Optional[Callable] = None,
                    **kwargs) -> None:
        """Submit request to the queue."""
        await self.request_queue.put({
            "prompt": prompt,
            "system": system,
            "callback": callback,
            "kwargs": kwargs
        })

    async def batch_process(self,
                           prompts: List[str],
                           system: Optional[str] = None,
                           **kwargs) -> List[Dict[str, Any]]:
        """Process batch of prompts in parallel."""
        tasks = [
            self.orchestrator.smart_complete(prompt, system, **kwargs)
            for prompt in prompts
        ]

        return await asyncio.gather(*tasks, return_exceptions=True)

# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_free_llm_hub(config: Optional[Dict[str, Any]] = None) -> MultiProviderOrchestrator:
    """Create and configure a free LLM hub."""
    hub = MultiProviderOrchestrator()

    if config:
        hub.configure_all_providers(config)

    return hub

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

async def example_usage():
    """Example of using the free LLM hub."""
    # Configuration with tokens for each provider
    config = {
        "deepseek": {
            "tokens": ["token1", "token2"],
            "base_url": "http://localhost:8001"
        },
        "kimi": {
            "tokens": ["kimi_token1"],
            "base_url": "http://localhost:8000"
        }
    }

    hub = create_free_llm_hub(config)
    await hub.initialize()

    try:
        # Simple chat
        result = await hub.smart_complete("Explain quantum computing")
        print(f"Response from {result.get('provider')}: {result.get('content')[:200]}...")

        # Deep reasoning
        result = await hub.deep_reasoning("How can we solve climate change?")
        print(f"Reasoning result: {result.get('content')[:200]}...")

        # Web search
        result = await hub.web_search("Latest AI research breakthroughs 2026")
        print(f"Search result: {result.get('content')[:200]}...")

    finally:
        await hub.close()

if __name__ == "__main__":
    asyncio.run(example_usage())
