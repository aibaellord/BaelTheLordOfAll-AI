"""
BAEL AI Tools - LLM Interaction and AI Utilities
Provides LLM routing, embeddings, summarization, classification, and more.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("BAEL.Tools.AI")


# =============================================================================
# DATA CLASSES & ENUMS
# =============================================================================

class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    GOOGLE = "google"
    GROQ = "groq"
    MISTRAL = "mistral"
    COHERE = "cohere"
    LOCAL = "local"


class ModelTier(Enum):
    """Model capability tiers."""
    FLAGSHIP = "flagship"       # GPT-4, Claude 3 Opus
    STANDARD = "standard"       # GPT-3.5, Claude Haiku
    FAST = "fast"               # Groq, fast inference
    CHEAP = "cheap"             # Free tier, low cost
    EMBEDDING = "embedding"     # Embedding models
    VISION = "vision"           # Vision models
    CODE = "code"               # Code-specialized


@dataclass
class LLMResponse:
    """Response from an LLM."""
    content: str
    model: str
    provider: LLMProvider
    usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    cost: float = 0.0
    finish_reason: str = "stop"
    raw_response: Optional[Dict[str, Any]] = None
    cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider.value,
            "usage": self.usage,
            "latency_ms": self.latency_ms,
            "cost": self.cost,
            "finish_reason": self.finish_reason,
            "cached": self.cached
        }


@dataclass
class EmbeddingResult:
    """Result from embedding generation."""
    embedding: List[float]
    model: str
    dimensions: int
    usage: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "embedding": self.embedding[:10] + ["..."],  # Truncate for display
            "model": self.model,
            "dimensions": self.dimensions
        }


@dataclass
class ClassificationResult:
    """Result from text classification."""
    label: str
    confidence: float
    all_scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class SentimentResult:
    """Result from sentiment analysis."""
    sentiment: str  # positive, negative, neutral
    score: float   # -1 to 1
    confidence: float


@dataclass
class Entity:
    """Extracted entity."""
    text: str
    type: str
    start: int
    end: int
    confidence: float = 1.0


# =============================================================================
# MODEL REGISTRY
# =============================================================================

class ModelRegistry:
    """Registry of available models and their capabilities."""

    MODELS = {
        # OpenAI
        "gpt-4o": {
            "provider": LLMProvider.OPENAI,
            "tier": ModelTier.FLAGSHIP,
            "max_tokens": 128000,
            "cost_per_1k_input": 0.005,
            "cost_per_1k_output": 0.015,
            "supports_vision": True,
            "supports_functions": True
        },
        "gpt-4-turbo": {
            "provider": LLMProvider.OPENAI,
            "tier": ModelTier.FLAGSHIP,
            "max_tokens": 128000,
            "cost_per_1k_input": 0.01,
            "cost_per_1k_output": 0.03,
            "supports_vision": True,
            "supports_functions": True
        },
        "gpt-3.5-turbo": {
            "provider": LLMProvider.OPENAI,
            "tier": ModelTier.STANDARD,
            "max_tokens": 16385,
            "cost_per_1k_input": 0.0005,
            "cost_per_1k_output": 0.0015,
            "supports_functions": True
        },

        # Anthropic
        "claude-3-opus": {
            "provider": LLMProvider.ANTHROPIC,
            "tier": ModelTier.FLAGSHIP,
            "max_tokens": 200000,
            "cost_per_1k_input": 0.015,
            "cost_per_1k_output": 0.075,
            "supports_vision": True
        },
        "claude-3-sonnet": {
            "provider": LLMProvider.ANTHROPIC,
            "tier": ModelTier.STANDARD,
            "max_tokens": 200000,
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.015,
            "supports_vision": True
        },
        "claude-3-haiku": {
            "provider": LLMProvider.ANTHROPIC,
            "tier": ModelTier.FAST,
            "max_tokens": 200000,
            "cost_per_1k_input": 0.00025,
            "cost_per_1k_output": 0.00125,
            "supports_vision": True
        },

        # Groq (Fast inference)
        "llama-3.1-70b": {
            "provider": LLMProvider.GROQ,
            "tier": ModelTier.FAST,
            "max_tokens": 8192,
            "cost_per_1k_input": 0.00059,
            "cost_per_1k_output": 0.00079
        },
        "mixtral-8x7b": {
            "provider": LLMProvider.GROQ,
            "tier": ModelTier.FAST,
            "max_tokens": 32768,
            "cost_per_1k_input": 0.00024,
            "cost_per_1k_output": 0.00024
        },

        # OpenRouter (aggregator)
        "openrouter/auto": {
            "provider": LLMProvider.OPENROUTER,
            "tier": ModelTier.STANDARD,
            "max_tokens": 100000,
            "cost_per_1k_input": 0.001,
            "cost_per_1k_output": 0.002
        },

        # Embedding models
        "text-embedding-3-small": {
            "provider": LLMProvider.OPENAI,
            "tier": ModelTier.EMBEDDING,
            "dimensions": 1536,
            "cost_per_1k_tokens": 0.00002
        },
        "text-embedding-3-large": {
            "provider": LLMProvider.OPENAI,
            "tier": ModelTier.EMBEDDING,
            "dimensions": 3072,
            "cost_per_1k_tokens": 0.00013
        }
    }

    @classmethod
    def get_model(cls, name: str) -> Optional[Dict[str, Any]]:
        """Get model info by name."""
        return cls.MODELS.get(name)

    @classmethod
    def get_models_by_tier(cls, tier: ModelTier) -> List[str]:
        """Get all models of a specific tier."""
        return [
            name for name, info in cls.MODELS.items()
            if info.get("tier") == tier
        ]

    @classmethod
    def get_models_by_provider(cls, provider: LLMProvider) -> List[str]:
        """Get all models from a provider."""
        return [
            name for name, info in cls.MODELS.items()
            if info.get("provider") == provider
        ]

    @classmethod
    def get_cheapest_model(cls) -> str:
        """Get the cheapest model."""
        cheapest = min(
            ((name, info.get("cost_per_1k_input", float('inf')))
             for name, info in cls.MODELS.items()
             if info.get("tier") != ModelTier.EMBEDDING),
            key=lambda x: x[1]
        )
        return cheapest[0]


# =============================================================================
# LLM ROUTER
# =============================================================================

class LLMRouter:
    """
    Intelligent router for LLM requests.
    Routes to the best model based on requirements.
    """

    def __init__(
        self,
        default_model: str = "gpt-3.5-turbo",
        api_keys: Optional[Dict[str, str]] = None,
        enable_caching: bool = True,
        max_retries: int = 3
    ):
        self.default_model = default_model
        self.api_keys = api_keys or {}
        self.enable_caching = enable_caching
        self.max_retries = max_retries
        self._cache: Dict[str, LLMResponse] = {}
        self._provider_status: Dict[LLMProvider, bool] = {}

        # Load API keys from environment if not provided
        self._load_api_keys()

    def _load_api_keys(self) -> None:
        """Load API keys from environment."""
        env_mappings = {
            LLMProvider.OPENAI: "OPENAI_API_KEY",
            LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
            LLMProvider.OPENROUTER: "OPENROUTER_API_KEY",
            LLMProvider.GROQ: "GROQ_API_KEY",
            LLMProvider.GOOGLE: "GOOGLE_API_KEY",
            LLMProvider.COHERE: "COHERE_API_KEY",
            LLMProvider.MISTRAL: "MISTRAL_API_KEY"
        }

        for provider, env_var in env_mappings.items():
            if provider.value not in self.api_keys:
                key = os.environ.get(env_var)
                if key:
                    self.api_keys[provider.value] = key
                    self._provider_status[provider] = True

    def select_model(
        self,
        task: str = "general",
        prefer_fast: bool = False,
        prefer_cheap: bool = False,
        require_vision: bool = False,
        require_functions: bool = False,
        max_tokens: Optional[int] = None
    ) -> str:
        """Select the best model for the task."""
        candidates = []

        for name, info in ModelRegistry.MODELS.items():
            # Skip embedding models
            if info.get("tier") == ModelTier.EMBEDDING:
                continue

            # Check requirements
            if require_vision and not info.get("supports_vision"):
                continue
            if require_functions and not info.get("supports_functions"):
                continue
            if max_tokens and info.get("max_tokens", 0) < max_tokens:
                continue

            # Check if provider is available
            provider = info.get("provider")
            if provider and provider.value not in self.api_keys:
                continue

            candidates.append((name, info))

        if not candidates:
            return self.default_model

        # Sort by preference
        if prefer_cheap:
            candidates.sort(key=lambda x: x[1].get("cost_per_1k_input", float('inf')))
        elif prefer_fast:
            # Prefer fast tier
            candidates.sort(key=lambda x: (
                0 if x[1].get("tier") == ModelTier.FAST else 1,
                x[1].get("cost_per_1k_input", 0)
            ))
        else:
            # Default: prefer flagship
            candidates.sort(key=lambda x: (
                0 if x[1].get("tier") == ModelTier.FLAGSHIP else 1,
                -x[1].get("max_tokens", 0)
            ))

        return candidates[0][0]

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Complete a chat conversation."""
        model = model or self.default_model
        model_info = ModelRegistry.get_model(model)

        if not model_info:
            model_info = {"provider": LLMProvider.OPENAI, "tier": ModelTier.STANDARD}

        provider = model_info.get("provider", LLMProvider.OPENAI)

        # Check cache
        if self.enable_caching:
            cache_key = self._cache_key(messages, model, temperature, system)
            if cache_key in self._cache:
                cached = self._cache[cache_key]
                cached.cached = True
                return cached

        start_time = time.time()

        # Build request
        request_messages = []
        if system:
            request_messages.append({"role": "system", "content": system})
        request_messages.extend(messages)

        # Dispatch to provider (simulated - in real impl, call actual APIs)
        try:
            response = await self._call_provider(
                provider=provider,
                model=model,
                messages=request_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            latency = (time.time() - start_time) * 1000
            response.latency_ms = latency

            # Calculate cost
            response.cost = self._calculate_cost(
                model=model,
                input_tokens=response.usage.get("prompt_tokens", 0),
                output_tokens=response.usage.get("completion_tokens", 0)
            )

            # Cache response
            if self.enable_caching:
                self._cache[cache_key] = response

            return response

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=model,
                provider=provider,
                finish_reason="error"
            )

    async def _call_provider(
        self,
        provider: LLMProvider,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> LLMResponse:
        """Call the actual LLM provider (simulated)."""
        # This is a simulation - in real implementation, call actual APIs
        # For now, return a simulated response

        # Simulate API latency
        await asyncio.sleep(0.1)

        # Simulate response
        content = f"[Simulated {provider.value} response using {model}]\n\n"
        content += f"This is a simulated response. To enable real LLM calls:\n"
        content += f"1. Set {provider.value.upper()}_API_KEY environment variable\n"
        content += f"2. Install required SDK (openai, anthropic, etc.)\n"
        content += f"3. Implement actual API calls in _call_provider method"

        return LLMResponse(
            content=content,
            model=model,
            provider=provider,
            usage={
                "prompt_tokens": sum(len(m.get("content", "").split()) for m in messages),
                "completion_tokens": len(content.split()),
                "total_tokens": sum(len(m.get("content", "").split()) for m in messages) + len(content.split())
            },
            finish_reason="stop"
        )

    def _cache_key(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        system: Optional[str]
    ) -> str:
        """Generate cache key."""
        data = json.dumps({
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "system": system
        }, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate cost for a request."""
        model_info = ModelRegistry.get_model(model)
        if not model_info:
            return 0.0

        input_cost = (input_tokens / 1000) * model_info.get("cost_per_1k_input", 0)
        output_cost = (output_tokens / 1000) * model_info.get("cost_per_1k_output", 0)

        return input_cost + output_cost

    def clear_cache(self) -> None:
        """Clear the response cache."""
        self._cache.clear()


# =============================================================================
# EMBEDDING GENERATOR
# =============================================================================

class EmbeddingGenerator:
    """Generate embeddings for text."""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: Optional[str] = None
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._cache: Dict[str, EmbeddingResult] = {}

    async def embed(
        self,
        text: str,
        use_cache: bool = True
    ) -> EmbeddingResult:
        """Generate embedding for text."""
        # Check cache
        cache_key = hashlib.sha256(f"{self.model}:{text}".encode()).hexdigest()
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        model_info = ModelRegistry.get_model(self.model)
        dimensions = model_info.get("dimensions", 1536) if model_info else 1536

        # Simulated embedding - in real impl, call OpenAI/Cohere API
        # For now, generate a deterministic fake embedding
        import random
        random.seed(hash(text) % 2**32)
        embedding = [random.gauss(0, 1) for _ in range(dimensions)]

        # Normalize
        norm = sum(x**2 for x in embedding) ** 0.5
        embedding = [x / norm for x in embedding]

        result = EmbeddingResult(
            embedding=embedding,
            model=self.model,
            dimensions=dimensions,
            usage={"tokens": len(text.split())}
        )

        if use_cache:
            self._cache[cache_key] = result

        return result

    async def embed_batch(
        self,
        texts: List[str],
        use_cache: bool = True
    ) -> List[EmbeddingResult]:
        """Generate embeddings for multiple texts."""
        results = []
        for text in texts:
            result = await self.embed(text, use_cache)
            results.append(result)
        return results

    def similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """Calculate cosine similarity between embeddings."""
        dot = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = sum(a ** 2 for a in embedding1) ** 0.5
        norm2 = sum(b ** 2 for b in embedding2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)


# =============================================================================
# TEXT SUMMARIZER
# =============================================================================

class TextSummarizer:
    """Summarize text using LLMs."""

    def __init__(self, llm: Optional[LLMRouter] = None):
        self.llm = llm or LLMRouter()

    async def summarize(
        self,
        text: str,
        max_length: int = 200,
        style: str = "concise"
    ) -> str:
        """Summarize text."""
        if len(text.split()) <= max_length:
            return text

        prompt = f"""Summarize the following text in a {style} manner.
Keep the summary under {max_length} words.

Text to summarize:
{text}

Summary:"""

        response = await self.llm.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=max_length * 2
        )

        return response.content

    async def extract_key_points(
        self,
        text: str,
        num_points: int = 5
    ) -> List[str]:
        """Extract key points from text."""
        prompt = f"""Extract the {num_points} most important key points from this text.
Return them as a numbered list.

Text:
{text}

Key points:"""

        response = await self.llm.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        # Parse numbered list
        lines = response.content.strip().split("\n")
        points = []
        for line in lines:
            line = re.sub(r"^\d+[\.\)]\s*", "", line.strip())
            if line:
                points.append(line)

        return points[:num_points]


# =============================================================================
# TEXT CLASSIFIER
# =============================================================================

class TextClassifier:
    """Classify text into categories."""

    def __init__(self, llm: Optional[LLMRouter] = None):
        self.llm = llm or LLMRouter()

    async def classify(
        self,
        text: str,
        categories: List[str],
        multi_label: bool = False
    ) -> ClassificationResult:
        """Classify text into categories."""
        cat_str = ", ".join(categories)

        if multi_label:
            prompt = f"""Classify the following text into one or more of these categories: {cat_str}
Return the matching categories separated by commas.

Text: {text}

Categories:"""
        else:
            prompt = f"""Classify the following text into exactly one of these categories: {cat_str}
Return only the category name.

Text: {text}

Category:"""

        response = await self.llm.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )

        result_text = response.content.strip()

        # Parse result
        if multi_label:
            labels = [l.strip() for l in result_text.split(",")]
            label = labels[0] if labels else categories[0]
        else:
            label = result_text.split("\n")[0].strip()
            # Fuzzy match to valid category
            label_lower = label.lower()
            for cat in categories:
                if cat.lower() in label_lower or label_lower in cat.lower():
                    label = cat
                    break

        return ClassificationResult(
            label=label,
            confidence=0.8,  # Simulated confidence
            all_scores={cat: 0.8 if cat == label else 0.1 for cat in categories}
        )

    async def topic_classification(
        self,
        text: str
    ) -> ClassificationResult:
        """Classify text by topic."""
        topics = [
            "technology", "science", "business", "politics",
            "entertainment", "sports", "health", "education", "other"
        ]
        return await self.classify(text, topics)


# =============================================================================
# SENTIMENT ANALYZER
# =============================================================================

class SentimentAnalyzer:
    """Analyze sentiment of text."""

    def __init__(self, llm: Optional[LLMRouter] = None):
        self.llm = llm or LLMRouter()

    async def analyze(self, text: str) -> SentimentResult:
        """Analyze sentiment of text."""
        prompt = f"""Analyze the sentiment of this text.
Return a JSON object with:
- sentiment: one of "positive", "negative", or "neutral"
- score: a number from -1 (most negative) to 1 (most positive)
- confidence: a number from 0 to 1

Text: {text}

JSON:"""

        response = await self.llm.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )

        # Parse JSON response
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response.content)
            if json_match:
                data = json.loads(json_match.group())
                return SentimentResult(
                    sentiment=data.get("sentiment", "neutral"),
                    score=float(data.get("score", 0)),
                    confidence=float(data.get("confidence", 0.5))
                )
        except:
            pass

        # Fallback to simple analysis
        text_lower = text.lower()
        positive_words = ["good", "great", "excellent", "love", "happy", "amazing"]
        negative_words = ["bad", "terrible", "hate", "awful", "disappointed", "poor"]

        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)

        if pos_count > neg_count:
            return SentimentResult("positive", 0.5, 0.6)
        elif neg_count > pos_count:
            return SentimentResult("negative", -0.5, 0.6)
        else:
            return SentimentResult("neutral", 0.0, 0.5)


# =============================================================================
# ENTITY EXTRACTOR
# =============================================================================

class EntityExtractor:
    """Extract named entities from text."""

    ENTITY_TYPES = [
        "PERSON", "ORGANIZATION", "LOCATION", "DATE", "TIME",
        "MONEY", "PERCENT", "PRODUCT", "EVENT", "WORK_OF_ART"
    ]

    def __init__(self, llm: Optional[LLMRouter] = None):
        self.llm = llm or LLMRouter()

    async def extract(
        self,
        text: str,
        entity_types: Optional[List[str]] = None
    ) -> List[Entity]:
        """Extract named entities from text."""
        types = entity_types or self.ENTITY_TYPES
        types_str = ", ".join(types)

        prompt = f"""Extract named entities from this text.
Return a JSON array of entities, each with:
- text: the entity text
- type: one of {types_str}

Text: {text}

JSON array:"""

        response = await self.llm.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )

        entities = []

        # Parse JSON response
        try:
            json_match = re.search(r'\[[\s\S]*\]', response.content)
            if json_match:
                data = json.loads(json_match.group())
                for item in data:
                    entity_text = item.get("text", "")
                    entity_type = item.get("type", "UNKNOWN")

                    # Find position in text
                    start = text.find(entity_text)
                    end = start + len(entity_text) if start >= 0 else -1

                    entities.append(Entity(
                        text=entity_text,
                        type=entity_type,
                        start=start,
                        end=end,
                        confidence=0.8
                    ))
        except:
            pass

        return entities

    async def extract_relations(
        self,
        text: str
    ) -> List[Dict[str, Any]]:
        """Extract relations between entities."""
        prompt = f"""Extract relationships between entities in this text.
Return a JSON array where each item has:
- subject: the subject entity
- relation: the relationship type
- object: the object entity

Text: {text}

JSON array:"""

        response = await self.llm.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )

        relations = []

        try:
            json_match = re.search(r'\[[\s\S]*\]', response.content)
            if json_match:
                relations = json.loads(json_match.group())
        except:
            pass

        return relations


# =============================================================================
# AI TOOLKIT - UNIFIED INTERFACE
# =============================================================================

class AIToolkit:
    """
    Unified AI toolkit providing all AI capabilities.

    Main entry point for AI operations in BAEL.
    """

    def __init__(
        self,
        default_model: str = "gpt-3.5-turbo",
        embedding_model: str = "text-embedding-3-small",
        api_keys: Optional[Dict[str, str]] = None
    ):
        self.llm = LLMRouter(default_model, api_keys)
        self.embeddings = EmbeddingGenerator(embedding_model)
        self.summarizer = TextSummarizer(self.llm)
        self.classifier = TextClassifier(self.llm)
        self.sentiment = SentimentAnalyzer(self.llm)
        self.entities = EntityExtractor(self.llm)

    async def chat(
        self,
        message: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7
    ) -> LLMResponse:
        """Simple chat interface."""
        return await self.llm.complete(
            messages=[{"role": "user", "content": message}],
            model=model,
            system=system,
            temperature=temperature
        )

    async def embed(self, text: str) -> EmbeddingResult:
        """Generate embedding for text."""
        return await self.embeddings.embed(text)

    async def summarize(
        self,
        text: str,
        max_length: int = 200
    ) -> str:
        """Summarize text."""
        return await self.summarizer.summarize(text, max_length)

    async def classify(
        self,
        text: str,
        categories: List[str]
    ) -> ClassificationResult:
        """Classify text."""
        return await self.classifier.classify(text, categories)

    async def analyze_sentiment(self, text: str) -> SentimentResult:
        """Analyze sentiment."""
        return await self.sentiment.analyze(text)

    async def extract_entities(self, text: str) -> List[Entity]:
        """Extract entities."""
        return await self.entities.extract(text)

    def select_model(
        self,
        prefer_fast: bool = False,
        prefer_cheap: bool = False,
        **kwargs
    ) -> str:
        """Select best model for task."""
        return self.llm.select_model(prefer_fast=prefer_fast, prefer_cheap=prefer_cheap, **kwargs)

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for BAEL integration."""
        return [
            {
                "name": "ai_chat",
                "description": "Chat with an AI model",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "model": {"type": "string"},
                        "system": {"type": "string"},
                        "temperature": {"type": "number", "default": 0.7}
                    },
                    "required": ["message"]
                },
                "handler": self.chat
            },
            {
                "name": "ai_embed",
                "description": "Generate embedding for text",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"}
                    },
                    "required": ["text"]
                },
                "handler": self.embed
            },
            {
                "name": "ai_summarize",
                "description": "Summarize text",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "max_length": {"type": "integer", "default": 200}
                    },
                    "required": ["text"]
                },
                "handler": self.summarize
            },
            {
                "name": "ai_classify",
                "description": "Classify text into categories",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "categories": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["text", "categories"]
                },
                "handler": self.classify
            },
            {
                "name": "ai_sentiment",
                "description": "Analyze text sentiment",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"}
                    },
                    "required": ["text"]
                },
                "handler": self.analyze_sentiment
            },
            {
                "name": "ai_entities",
                "description": "Extract named entities from text",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"}
                    },
                    "required": ["text"]
                },
                "handler": self.extract_entities
            }
        ]


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "AIToolkit",
    "LLMRouter",
    "EmbeddingGenerator",
    "TextSummarizer",
    "TextClassifier",
    "SentimentAnalyzer",
    "EntityExtractor",
    "LLMResponse",
    "EmbeddingResult",
    "LLMProvider",
    "ModelTier",
    "ModelRegistry",
    "ClassificationResult",
    "SentimentResult",
    "Entity"
]
