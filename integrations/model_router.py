"""
BAEL - The Lord of All AI Agents
Model Router - Intelligent Multi-Model Orchestration

Routes requests to the optimal AI model based on task type,
complexity, cost constraints, and performance requirements.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

import aiohttp

logger = logging.getLogger("BAEL.ModelRouter")


class ModelProvider(Enum):
    """Supported AI model providers."""
    OPENROUTER = "openrouter"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LOCAL = "local"
    OLLAMA = "ollama"
    TOGETHER = "together"
    GROQ = "groq"


class ModelCapability(Enum):
    """Model capabilities."""
    GENERAL = "general"
    CODE = "code"
    REASONING = "reasoning"
    CREATIVE = "creative"
    FAST = "fast"
    VISION = "vision"
    EMBEDDING = "embedding"
    FUNCTION_CALLING = "function_calling"


@dataclass
class ModelConfig:
    """Configuration for a single model."""
    id: str
    name: str
    provider: ModelProvider
    capabilities: List[ModelCapability]
    context_window: int = 128000
    max_output: int = 4096
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    supports_streaming: bool = True
    supports_tools: bool = True
    api_base: Optional[str] = None
    api_key_env: str = "OPENROUTER_API_KEY"
    default_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelResponse:
    """Response from a model."""
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=dict)
    cost: float = 0.0
    latency_ms: int = 0
    finish_reason: str = "stop"
    tool_calls: Optional[List[Dict]] = None


@dataclass
class ModelStats:
    """Statistics for a model."""
    total_requests: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_cost: float = 0.0
    average_latency_ms: float = 0.0
    error_count: int = 0
    last_used: Optional[datetime] = None


class ModelRouter:
    """
    Intelligent Model Router - Orchestrates multiple AI models.

    Features:
    - Automatic model selection based on task type
    - Load balancing across providers
    - Fallback handling
    - Cost optimization
    - Performance tracking
    """

    # Default model configurations
    DEFAULT_MODELS = {
        'primary': ModelConfig(
            id='anthropic/claude-sonnet-4-20250514',
            name='Claude Sonnet 4',
            provider=ModelProvider.OPENROUTER,
            capabilities=[ModelCapability.GENERAL, ModelCapability.CODE, ModelCapability.REASONING],
            context_window=200000,
            max_output=8192,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
            api_key_env="OPENROUTER_API_KEY"
        ),
        'fast': ModelConfig(
            id='anthropic/claude-3-haiku-20240307',
            name='Claude 3 Haiku',
            provider=ModelProvider.OPENROUTER,
            capabilities=[ModelCapability.FAST, ModelCapability.GENERAL],
            context_window=200000,
            max_output=4096,
            cost_per_1k_input=0.00025,
            cost_per_1k_output=0.00125,
            api_key_env="OPENROUTER_API_KEY"
        ),
        'code': ModelConfig(
            id='anthropic/claude-sonnet-4-20250514',
            name='Claude Sonnet 4',
            provider=ModelProvider.OPENROUTER,
            capabilities=[ModelCapability.CODE, ModelCapability.REASONING],
            context_window=200000,
            max_output=8192,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
            api_key_env="OPENROUTER_API_KEY"
        ),
        'creative': ModelConfig(
            id='anthropic/claude-sonnet-4-20250514',
            name='Claude Sonnet 4',
            provider=ModelProvider.OPENROUTER,
            capabilities=[ModelCapability.CREATIVE, ModelCapability.GENERAL],
            context_window=200000,
            max_output=8192,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
            default_params={'temperature': 1.0},
            api_key_env="OPENROUTER_API_KEY"
        ),
        'reasoning': ModelConfig(
            id='anthropic/claude-sonnet-4-20250514',
            name='Claude Sonnet 4',
            provider=ModelProvider.OPENROUTER,
            capabilities=[ModelCapability.REASONING],
            context_window=200000,
            max_output=16384,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
            api_key_env="OPENROUTER_API_KEY"
        ),
        'vision': ModelConfig(
            id='anthropic/claude-sonnet-4-20250514',
            name='Claude Sonnet 4',
            provider=ModelProvider.OPENROUTER,
            capabilities=[ModelCapability.VISION, ModelCapability.GENERAL],
            context_window=200000,
            max_output=8192,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
            api_key_env="OPENROUTER_API_KEY"
        ),
        'embedding': ModelConfig(
            id='text-embedding-3-small',
            name='OpenAI Text Embedding 3 Small',
            provider=ModelProvider.OPENAI,
            capabilities=[ModelCapability.EMBEDDING],
            context_window=8192,
            max_output=0,
            cost_per_1k_input=0.00002,
            cost_per_1k_output=0.0,
            api_key_env="OPENAI_API_KEY"
        )
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the model router."""
        self.config = config or {}
        self.models: Dict[str, ModelConfig] = {}
        self.stats: Dict[str, ModelStats] = {}
        self._session: Optional[aiohttp.ClientSession] = None

        # Load model configurations
        self._load_models()

        logger.info(f"🔀 Model Router initialized with {len(self.models)} models")

    def _load_models(self):
        """Load model configurations from config or defaults."""
        # Start with defaults
        for model_type, model_config in self.DEFAULT_MODELS.items():
            self.models[model_type] = model_config
            self.stats[model_type] = ModelStats()

        # Override with config
        models_config = self.config.get('models', {})
        for model_type, model_data in models_config.items():
            if model_type in self.models:
                # Update existing model
                for key, value in model_data.items():
                    if hasattr(self.models[model_type], key):
                        setattr(self.models[model_type], key, value)
            else:
                # Add new model
                self.models[model_type] = ModelConfig(**model_data)
                self.stats[model_type] = ModelStats()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def _get_api_key(self, model_config: ModelConfig) -> str:
        """Get API key for a model."""
        env_var = model_config.api_key_env
        return os.environ.get(env_var, "")

    def _get_api_base(self, model_config: ModelConfig) -> str:
        """Get API base URL for a model."""
        if model_config.api_base:
            return model_config.api_base

        provider_bases = {
            ModelProvider.OPENROUTER: "https://openrouter.ai/api/v1",
            ModelProvider.ANTHROPIC: "https://api.anthropic.com/v1",
            ModelProvider.OPENAI: "https://api.openai.com/v1",
            ModelProvider.OLLAMA: "http://localhost:11434/api",
            ModelProvider.TOGETHER: "https://api.together.xyz/v1",
            ModelProvider.GROQ: "https://api.groq.com/openai/v1"
        }

        return provider_bases.get(model_config.provider, "https://openrouter.ai/api/v1")

    async def generate(
        self,
        prompt: str,
        model_type: str = "primary",
        context: Optional[Dict] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        **kwargs
    ) -> str:
        """
        Generate a response from the specified model type.

        Args:
            prompt: The user prompt
            model_type: Type of model to use (primary, fast, code, creative, reasoning)
            context: Additional context dictionary
            system_prompt: Optional system prompt
            tools: Optional list of tool definitions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream response

        Returns:
            Generated text response
        """
        if model_type not in self.models:
            logger.warning(f"Unknown model type {model_type}, falling back to primary")
            model_type = "primary"

        model_config = self.models[model_type]

        # Build messages
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        elif context and 'system_prompt' in context:
            messages.append({"role": "system", "content": context['system_prompt']})

        # Add context as assistant message if provided
        if context and 'previous_context' in context:
            messages.append({"role": "assistant", "content": context['previous_context']})

        messages.append({"role": "user", "content": prompt})

        # Make API call
        try:
            response = await self._call_api(
                model_config=model_config,
                messages=messages,
                tools=tools,
                max_tokens=max_tokens or model_config.max_output,
                temperature=temperature,
                stream=stream
            )

            # Update stats
            self._update_stats(model_type, response)

            return response.content

        except Exception as e:
            logger.error(f"Error calling {model_type} model: {e}")
            self.stats[model_type].error_count += 1

            # Try fallback
            return await self._fallback_generate(prompt, model_type, context, system_prompt, tools)

    async def _call_api(
        self,
        model_config: ModelConfig,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 4096,
        temperature: Optional[float] = None,
        stream: bool = False
    ) -> ModelResponse:
        """Make API call to the model provider."""
        start_time = datetime.now()

        api_key = self._get_api_key(model_config)
        api_base = self._get_api_base(model_config)

        if not api_key:
            logger.warning(f"No API key found for {model_config.provider.value}")
            return ModelResponse(
                content="Error: No API key configured. Please set the appropriate environment variable.",
                model=model_config.id,
                provider=model_config.provider.value
            )

        # Build request
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        if model_config.provider == ModelProvider.OPENROUTER:
            headers["HTTP-Referer"] = "https://bael.ai"
            headers["X-Title"] = "BAEL - The Lord of All AI Agents"

        data = {
            "model": model_config.id,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": stream
        }

        if temperature is not None:
            data["temperature"] = temperature
        elif 'temperature' in model_config.default_params:
            data["temperature"] = model_config.default_params['temperature']

        if tools and model_config.supports_tools:
            data["tools"] = tools

        # Make request
        session = await self._get_session()

        endpoint = f"{api_base}/chat/completions"

        async with session.post(endpoint, headers=headers, json=data) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"API error {resp.status}: {error_text}")

            result = await resp.json()

        latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Parse response
        choice = result.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = result.get("usage", {})

        # Calculate cost
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        cost = (
            (input_tokens / 1000 * model_config.cost_per_1k_input) +
            (output_tokens / 1000 * model_config.cost_per_1k_output)
        )

        return ModelResponse(
            content=message.get("content", ""),
            model=model_config.id,
            provider=model_config.provider.value,
            usage={
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            },
            cost=cost,
            latency_ms=latency_ms,
            finish_reason=choice.get("finish_reason", "stop"),
            tool_calls=message.get("tool_calls")
        )

    async def _fallback_generate(
        self,
        prompt: str,
        failed_model_type: str,
        context: Optional[Dict],
        system_prompt: Optional[str],
        tools: Optional[List[Dict]]
    ) -> str:
        """Attempt generation with fallback models."""
        fallback_order = ["primary", "fast", "code"]

        for fallback_type in fallback_order:
            if fallback_type == failed_model_type:
                continue

            try:
                logger.info(f"🔄 Falling back to {fallback_type} model")
                return await self.generate(
                    prompt=prompt,
                    model_type=fallback_type,
                    context=context,
                    system_prompt=system_prompt,
                    tools=tools
                )
            except Exception as e:
                logger.error(f"Fallback to {fallback_type} failed: {e}")
                continue

        return "I apologize, but I'm unable to generate a response at this time. All models are unavailable."

    def _update_stats(self, model_type: str, response: ModelResponse):
        """Update statistics for a model."""
        stats = self.stats[model_type]

        stats.total_requests += 1
        stats.total_tokens_input += response.usage.get("prompt_tokens", 0)
        stats.total_tokens_output += response.usage.get("completion_tokens", 0)
        stats.total_cost += response.cost
        stats.last_used = datetime.now()

        # Update average latency
        if stats.average_latency_ms == 0:
            stats.average_latency_ms = response.latency_ms
        else:
            stats.average_latency_ms = (
                (stats.average_latency_ms * (stats.total_requests - 1) + response.latency_ms)
                / stats.total_requests
            )

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        model_config = self.models.get("embedding")
        if not model_config:
            raise ValueError("No embedding model configured")

        api_key = self._get_api_key(model_config)
        api_base = self._get_api_base(model_config)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": model_config.id,
            "input": text
        }

        session = await self._get_session()

        async with session.post(f"{api_base}/embeddings", headers=headers, json=data) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"Embedding API error {resp.status}: {error_text}")

            result = await resp.json()

        return result["data"][0]["embedding"]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return [await self.embed(text) for text in texts]

    def select_model(self, capability: ModelCapability) -> str:
        """Select best model for a given capability."""
        for model_type, model_config in self.models.items():
            if capability in model_config.capabilities:
                return model_type
        return "primary"

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all models."""
        return {
            model_type: {
                "total_requests": stats.total_requests,
                "total_tokens_input": stats.total_tokens_input,
                "total_tokens_output": stats.total_tokens_output,
                "total_cost": round(stats.total_cost, 4),
                "average_latency_ms": round(stats.average_latency_ms, 2),
                "error_count": stats.error_count,
                "last_used": stats.last_used.isoformat() if stats.last_used else None
            }
            for model_type, stats in self.stats.items()
        }

    def get_total_cost(self) -> float:
        """Get total cost across all models."""
        return sum(stats.total_cost for stats in self.stats.values())

    async def close(self):
        """Close the router and cleanup resources."""
        if self._session and not self._session.closed:
            await self._session.close()
        logger.info("🔀 Model Router closed")


class MultiModelChain:
    """
    Chain multiple models for complex reasoning tasks.

    Example: Use fast model for initial analysis, then
    reasoning model for deep thinking, then code model
    for implementation.
    """

    def __init__(self, router: ModelRouter):
        self.router = router
        self.chain: List[Dict[str, Any]] = []

    def add_step(
        self,
        model_type: str,
        prompt_template: str,
        input_vars: Optional[List[str]] = None
    ) -> 'MultiModelChain':
        """Add a step to the chain."""
        self.chain.append({
            "model_type": model_type,
            "prompt_template": prompt_template,
            "input_vars": input_vars or []
        })
        return self

    async def execute(self, initial_input: str, **kwargs) -> Dict[str, Any]:
        """Execute the chain."""
        results = []
        current_input = initial_input

        for i, step in enumerate(self.chain):
            # Build prompt
            prompt = step["prompt_template"]

            # Replace variables
            prompt = prompt.replace("{input}", current_input)
            for var in step["input_vars"]:
                if var in kwargs:
                    prompt = prompt.replace(f"{{{var}}}", str(kwargs[var]))

            # Also replace with previous results
            for j, prev_result in enumerate(results):
                prompt = prompt.replace(f"{{step_{j}_output}}", prev_result["output"])

            # Generate
            output = await self.router.generate(
                prompt=prompt,
                model_type=step["model_type"]
            )

            results.append({
                "step": i,
                "model_type": step["model_type"],
                "prompt": prompt,
                "output": output
            })

            current_input = output

        return {
            "final_output": results[-1]["output"] if results else "",
            "steps": results
        }


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'ModelRouter',
    'ModelConfig',
    'ModelResponse',
    'ModelProvider',
    'ModelCapability',
    'MultiModelChain'
]
