"""
BAEL Multi-LLM Orchestration Engine
====================================

The most advanced multi-provider LLM orchestration system ever created.
Zero-cost operation through intelligent exploitation of 25+ free API providers.

Features:
- Round-robin rotation across unlimited providers
- Intelligent task-based routing (code→Claude, reasoning→DeepSeek-R1, fast→GPT-4-mini)
- Automatic rate-limit detection and provider health monitoring
- Smart caching with semantic deduplication
- Cost optimization targeting $0 operation
- Fallback chains with automatic failover
- Response quality scoring and provider ranking
- Parallel execution for consensus/ensemble responses
- Token counting and budget management
- Provider-specific prompt optimization

Providers Supported:
- OpenRouter (100+ models, unified API)
- DeepSeek (R1, V3, Coder)
- SiliconFlow (Chinese models)
- Groq (ultra-fast inference)
- Together AI (open models)
- Fireworks AI (fast inference)
- Mistral AI (Mistral models)
- Anthropic (Claude models)
- OpenAI (GPT models)
- Google AI (Gemini models)
- Ollama (local models)
- LM Studio (local models)
- ZukiJourney (free tier)
- ElectronHub (free tier)
- NagaAI (free tier)
- Shuttle AI (free tier)
- And 15+ more underground providers

Author: BAEL System
Version: 1.0.0
"""

from .cache_layer import CacheEntry, CacheStrategy, SemanticCache
from .cost_optimizer import CostOptimizer, CostStrategy, UsageTracker
from .fallback_chain import FailoverEvent, FallbackChain, FallbackStrategy
from .multi_provider_router import (MultiProviderRouter, ProviderConfig,
                                    ProviderStatus, RoutingStrategy)
from .prompt_optimizer import OptimizationStrategy, PromptOptimizer
from .provider_health import HealthMetrics, HealthStatus, ProviderHealthMonitor
from .response_aggregator import (AggregationStrategy, ConsensusResult,
                                  ResponseAggregator)
from .task_classifier import (ClassificationResult, TaskClassifier,
                              TaskComplexity, TaskType)

__all__ = [
    # Router
    "MultiProviderRouter",
    "ProviderConfig",
    "ProviderStatus",
    "RoutingStrategy",
    # Classifier
    "TaskClassifier",
    "TaskType",
    "TaskComplexity",
    "ClassificationResult",
    # Fallback
    "FallbackChain",
    "FallbackStrategy",
    "FailoverEvent",
    # Cost
    "CostOptimizer",
    "CostStrategy",
    "UsageTracker",
    # Aggregator
    "ResponseAggregator",
    "AggregationStrategy",
    "ConsensusResult",
    # Health
    "ProviderHealthMonitor",
    "HealthStatus",
    "HealthMetrics",
    # Cache
    "SemanticCache",
    "CacheStrategy",
    "CacheEntry",
    # Optimizer
    "PromptOptimizer",
    "OptimizationStrategy",
]
