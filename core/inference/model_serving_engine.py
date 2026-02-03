#!/usr/bin/env python3
"""
BAEL - Model Serving Engine
Comprehensive model inference and serving.

Features:
- Model loading
- Batch inference
- Async inference
- Caching
- Latency optimization
- Multi-model serving
"""

import asyncio
import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ServingMode(Enum):
    """Serving modes."""
    SYNC = "sync"
    ASYNC = "async"
    BATCH = "batch"
    STREAM = "stream"


class ModelState(Enum):
    """Model states."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    WARMING = "warming"


class CacheStrategy(Enum):
    """Caching strategies."""
    NONE = "none"
    LRU = "lru"
    TTL = "ttl"
    LFU = "lfu"


class PredictionStatus(Enum):
    """Prediction status."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CACHED = "cached"
    QUEUED = "queued"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ServingRequest:
    """A serving request."""
    request_id: str = ""
    input_data: Any = None
    model_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    timeout: Optional[float] = None
    priority: int = 0

    def __post_init__(self):
        if not self.request_id:
            self.request_id = str(uuid.uuid4())[:8]


@dataclass
class ServingResponse:
    """A serving response."""
    request_id: str = ""
    output: Any = None
    status: PredictionStatus = PredictionStatus.SUCCESS
    latency_ms: float = 0.0
    model_name: str = ""
    model_version: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None


@dataclass
class BatchServingRequest:
    """A batch serving request."""
    batch_id: str = ""
    requests: List[ServingRequest] = field(default_factory=list)
    model_name: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    max_wait_ms: float = 100

    def __post_init__(self):
        if not self.batch_id:
            self.batch_id = str(uuid.uuid4())[:8]

    def __len__(self) -> int:
        return len(self.requests)


@dataclass
class BatchServingResponse:
    """A batch serving response."""
    batch_id: str = ""
    responses: List[ServingResponse] = field(default_factory=list)
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    success_count: int = 0
    error_count: int = 0
    throughput: float = 0.0


@dataclass
class ModelServingConfig:
    """Model serving configuration."""
    name: str = ""
    version: str = "1.0.0"
    max_batch_size: int = 32
    timeout_ms: float = 30000
    warmup_requests: int = 3
    cache_enabled: bool = True
    cache_size: int = 1000
    cache_ttl: float = 300
    max_concurrent: int = 100
    dynamic_batching: bool = False


@dataclass
class ModelServingInfo:
    """Model serving information."""
    name: str = ""
    version: str = ""
    state: ModelState = ModelState.UNLOADED
    config: ModelServingConfig = field(default_factory=ModelServingConfig)
    loaded_at: Optional[datetime] = None
    request_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0


@dataclass
class EngineStats:
    """Engine statistics."""
    total_requests: int = 0
    total_errors: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    models_loaded: int = 0
    throughput_per_sec: float = 0.0


# =============================================================================
# CACHE
# =============================================================================

class ResultCache:
    """LRU cache for serving results."""

    def __init__(self, max_size: int = 1000, ttl: float = 300):
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl
        self._hits = 0
        self._misses = 0

    def _compute_key(self, data: Any) -> str:
        """Compute cache key from input data."""
        if isinstance(data, str):
            return hashlib.md5(data.encode()).hexdigest()
        return hashlib.md5(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()

    def get(self, data: Any) -> Optional[Any]:
        """Get cached result."""
        key = self._compute_key(data)

        if key not in self._cache:
            self._misses += 1
            return None

        value, timestamp = self._cache[key]

        if time.time() - timestamp > self._ttl:
            del self._cache[key]
            self._misses += 1
            return None

        self._cache.move_to_end(key)
        self._hits += 1
        return value

    def put(self, data: Any, result: Any) -> None:
        """Cache a result."""
        key = self._compute_key(data)

        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = (result, time.time())
            return

        while len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)

        self._cache[key] = (result, time.time())

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()

    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache stats."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0

        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate
        }


# =============================================================================
# BASE SERVABLE MODEL
# =============================================================================

class ServableModel(ABC):
    """Abstract base class for servable models."""

    def __init__(self, config: ModelServingConfig):
        self._config = config
        self._state = ModelState.UNLOADED
        self._loaded_at: Optional[datetime] = None
        self._request_count = 0
        self._error_count = 0

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def version(self) -> str:
        return self._config.version

    @property
    def state(self) -> ModelState:
        return self._state

    @abstractmethod
    async def load(self) -> bool:
        """Load the model."""
        pass

    @abstractmethod
    async def unload(self) -> bool:
        """Unload the model."""
        pass

    @abstractmethod
    async def predict(self, input_data: Any) -> Any:
        """Make a prediction."""
        pass

    async def predict_batch(self, inputs: List[Any]) -> List[Any]:
        """Batch prediction (default: sequential)."""
        return [await self.predict(x) for x in inputs]

    async def warmup(self) -> None:
        """Warmup the model."""
        self._state = ModelState.WARMING
        for _ in range(self._config.warmup_requests):
            await self.predict(None)
        self._state = ModelState.READY


# =============================================================================
# MODEL IMPLEMENTATIONS
# =============================================================================

class FunctionServableModel(ServableModel):
    """Model backed by a function."""

    def __init__(self, config: ModelServingConfig, predict_fn: Callable[[Any], Any]):
        super().__init__(config)
        self._predict_fn = predict_fn

    async def load(self) -> bool:
        self._state = ModelState.READY
        self._loaded_at = datetime.now()
        return True

    async def unload(self) -> bool:
        self._state = ModelState.UNLOADED
        return True

    async def predict(self, input_data: Any) -> Any:
        self._request_count += 1

        try:
            if asyncio.iscoroutinefunction(self._predict_fn):
                return await self._predict_fn(input_data)
            return self._predict_fn(input_data)
        except Exception as e:
            self._error_count += 1
            raise


class EchoServableModel(ServableModel):
    """Simple echo model for testing."""

    async def load(self) -> bool:
        self._state = ModelState.READY
        self._loaded_at = datetime.now()
        return True

    async def unload(self) -> bool:
        self._state = ModelState.UNLOADED
        return True

    async def predict(self, input_data: Any) -> Any:
        self._request_count += 1
        return {"echo": input_data, "timestamp": datetime.now().isoformat()}


class TextClassifierModel(ServableModel):
    """Simple text classification model."""

    def __init__(self, config: ModelServingConfig, classes: List[str]):
        super().__init__(config)
        self._classes = classes

    async def load(self) -> bool:
        self._state = ModelState.READY
        self._loaded_at = datetime.now()
        return True

    async def unload(self) -> bool:
        self._state = ModelState.UNLOADED
        return True

    async def predict(self, input_data: Any) -> Dict[str, Any]:
        self._request_count += 1

        import random

        scores = [random.random() for _ in self._classes]
        total = sum(scores)
        probs = [s / total for s in scores]

        best_idx = probs.index(max(probs))

        return {
            "class": self._classes[best_idx],
            "confidence": probs[best_idx],
            "all_scores": dict(zip(self._classes, probs))
        }


class SentimentModel(ServableModel):
    """Simple sentiment analysis model."""

    async def load(self) -> bool:
        self._state = ModelState.READY
        self._loaded_at = datetime.now()
        return True

    async def unload(self) -> bool:
        self._state = ModelState.UNLOADED
        return True

    async def predict(self, input_data: Any) -> Dict[str, Any]:
        self._request_count += 1

        if not isinstance(input_data, str):
            return {"sentiment": "neutral", "score": 0.5}

        text = input_data.lower()

        positive = {"good", "great", "excellent", "amazing", "wonderful", "love", "best"}
        negative = {"bad", "terrible", "awful", "horrible", "poor", "hate", "worst"}

        words = set(text.split())
        pos_count = len(words & positive)
        neg_count = len(words & negative)

        if pos_count > neg_count:
            score = 0.5 + 0.1 * pos_count
            return {"sentiment": "positive", "score": min(1.0, score)}
        elif neg_count > pos_count:
            score = 0.5 - 0.1 * neg_count
            return {"sentiment": "negative", "score": max(0.0, score)}
        else:
            return {"sentiment": "neutral", "score": 0.5}


# =============================================================================
# MODEL SERVING ENGINE
# =============================================================================

class ModelServingEngine:
    """
    Model Serving Engine for BAEL.

    Comprehensive model inference and serving.
    """

    def __init__(self):
        self._models: Dict[str, ServableModel] = {}
        self._caches: Dict[str, ResultCache] = {}
        self._latencies: List[float] = []
        self._start_time = time.time()
        self._request_count = 0
        self._error_count = 0
        self._cache_hits = 0
        self._cache_misses = 0

    async def register_model(
        self,
        model: ServableModel,
        auto_load: bool = True
    ) -> bool:
        """Register a model."""
        name = model.name
        self._models[name] = model

        if model._config.cache_enabled:
            self._caches[name] = ResultCache(
                max_size=model._config.cache_size,
                ttl=model._config.cache_ttl
            )

        if auto_load:
            return await model.load()

        return True

    async def unregister_model(self, name: str) -> bool:
        """Unregister a model."""
        if name not in self._models:
            return False

        model = self._models[name]

        if model.state == ModelState.READY:
            await model.unload()

        del self._models[name]

        if name in self._caches:
            del self._caches[name]

        return True

    async def serve(
        self,
        model_name: str,
        input_data: Any,
        use_cache: bool = True
    ) -> ServingResponse:
        """Serve a single request."""
        request = ServingRequest(
            input_data=input_data,
            model_name=model_name
        )

        return await self._process_request(request, use_cache)

    async def _process_request(
        self,
        request: ServingRequest,
        use_cache: bool = True
    ) -> ServingResponse:
        """Process a serving request."""
        start_time = time.time()
        model_name = request.model_name

        self._request_count += 1

        if model_name not in self._models:
            return ServingResponse(
                request_id=request.request_id,
                status=PredictionStatus.ERROR,
                model_name=model_name,
                error=f"Model not found: {model_name}"
            )

        model = self._models[model_name]

        if model.state != ModelState.READY:
            return ServingResponse(
                request_id=request.request_id,
                status=PredictionStatus.ERROR,
                model_name=model_name,
                error=f"Model not ready: {model.state.value}"
            )

        if use_cache and model_name in self._caches:
            cache = self._caches[model_name]
            cached = cache.get(request.input_data)

            if cached is not None:
                self._cache_hits += 1
                latency_ms = (time.time() - start_time) * 1000
                self._latencies.append(latency_ms)

                return ServingResponse(
                    request_id=request.request_id,
                    output=cached,
                    status=PredictionStatus.CACHED,
                    latency_ms=latency_ms,
                    model_name=model_name,
                    model_version=model.version
                )

            self._cache_misses += 1

        try:
            output = await model.predict(request.input_data)

            latency_ms = (time.time() - start_time) * 1000
            self._latencies.append(latency_ms)

            if use_cache and model_name in self._caches:
                self._caches[model_name].put(request.input_data, output)

            return ServingResponse(
                request_id=request.request_id,
                output=output,
                status=PredictionStatus.SUCCESS,
                latency_ms=latency_ms,
                model_name=model_name,
                model_version=model.version
            )

        except Exception as e:
            self._error_count += 1
            latency_ms = (time.time() - start_time) * 1000
            self._latencies.append(latency_ms)

            return ServingResponse(
                request_id=request.request_id,
                status=PredictionStatus.ERROR,
                latency_ms=latency_ms,
                model_name=model_name,
                error=str(e)
            )

    async def serve_batch(
        self,
        model_name: str,
        inputs: List[Any],
        use_cache: bool = True
    ) -> BatchServingResponse:
        """Serve batch requests."""
        batch_request = BatchServingRequest(
            model_name=model_name,
            requests=[
                ServingRequest(input_data=x, model_name=model_name)
                for x in inputs
            ]
        )

        start_time = time.time()

        responses = []
        success_count = 0
        error_count = 0

        for request in batch_request.requests:
            response = await self._process_request(request, use_cache)
            responses.append(response)

            if response.status in (PredictionStatus.SUCCESS, PredictionStatus.CACHED):
                success_count += 1
            else:
                error_count += 1

        total_latency = (time.time() - start_time) * 1000
        avg_latency = total_latency / len(batch_request) if batch_request else 0
        throughput = len(batch_request) / (total_latency / 1000) if total_latency > 0 else 0

        return BatchServingResponse(
            batch_id=batch_request.batch_id,
            responses=responses,
            total_latency_ms=total_latency,
            avg_latency_ms=avg_latency,
            success_count=success_count,
            error_count=error_count,
            throughput=throughput
        )

    async def serve_async(
        self,
        model_name: str,
        inputs: List[Any],
        use_cache: bool = True
    ) -> List[ServingResponse]:
        """Serve async concurrent requests."""
        tasks = [
            self.serve(model_name, x, use_cache)
            for x in inputs
        ]

        return await asyncio.gather(*tasks)

    def get_model(self, name: str) -> Optional[ServableModel]:
        """Get a model by name."""
        return self._models.get(name)

    def get_model_info(self, name: str) -> Optional[ModelServingInfo]:
        """Get model information."""
        model = self._models.get(name)

        if not model:
            return None

        return ModelServingInfo(
            name=model.name,
            version=model.version,
            state=model.state,
            config=model._config,
            loaded_at=model._loaded_at,
            request_count=model._request_count,
            error_count=model._error_count
        )

    def list_models(self) -> List[str]:
        """List registered model names."""
        return list(self._models.keys())

    def get_cache_stats(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get cache stats for a model."""
        if model_name in self._caches:
            return self._caches[model_name].stats
        return None

    def clear_cache(self, model_name: Optional[str] = None) -> None:
        """Clear cache."""
        if model_name:
            if model_name in self._caches:
                self._caches[model_name].clear()
        else:
            for cache in self._caches.values():
                cache.clear()

    def get_latency_percentiles(self) -> Dict[str, float]:
        """Get latency percentiles."""
        if not self._latencies:
            return {"p50": 0, "p95": 0, "p99": 0}

        sorted_latencies = sorted(self._latencies)
        n = len(sorted_latencies)

        return {
            "p50": sorted_latencies[int(n * 0.5)],
            "p95": sorted_latencies[int(n * 0.95)],
            "p99": sorted_latencies[int(n * 0.99)]
        }

    def stats(self) -> EngineStats:
        """Get engine stats."""
        elapsed = time.time() - self._start_time
        throughput = self._request_count / elapsed if elapsed > 0 else 0

        percentiles = self.get_latency_percentiles()

        return EngineStats(
            total_requests=self._request_count,
            total_errors=self._error_count,
            cache_hits=self._cache_hits,
            cache_misses=self._cache_misses,
            avg_latency_ms=sum(self._latencies) / len(self._latencies) if self._latencies else 0,
            p50_latency_ms=percentiles["p50"],
            p95_latency_ms=percentiles["p95"],
            p99_latency_ms=percentiles["p99"],
            models_loaded=sum(1 for m in self._models.values() if m.state == ModelState.READY),
            throughput_per_sec=throughput
        )

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        stats = self.stats()

        return {
            "models": len(self._models),
            "models_ready": stats.models_loaded,
            "total_requests": stats.total_requests,
            "total_errors": stats.total_errors,
            "cache_hits": stats.cache_hits,
            "avg_latency_ms": stats.avg_latency_ms,
            "p99_latency_ms": stats.p99_latency_ms,
            "throughput_per_sec": stats.throughput_per_sec
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Model Serving Engine."""
    print("=" * 70)
    print("BAEL - MODEL SERVING ENGINE DEMO")
    print("Comprehensive Model Serving")
    print("=" * 70)
    print()

    engine = ModelServingEngine()

    # 1. Register Echo Model
    print("1. REGISTER ECHO MODEL:")
    print("-" * 40)

    echo_config = ModelServingConfig(name="echo", version="1.0.0")
    echo_model = EchoServableModel(echo_config)

    await engine.register_model(echo_model)

    print(f"   Registered: {echo_model.name}")
    print(f"   State: {echo_model.state.value}")
    print()

    # 2. Single Serving
    print("2. SINGLE SERVING:")
    print("-" * 40)

    response = await engine.serve("echo", "Hello BAEL!")

    print(f"   Request ID: {response.request_id}")
    print(f"   Output: {response.output}")
    print(f"   Latency: {response.latency_ms:.2f}ms")
    print()

    # 3. Register Sentiment Model
    print("3. REGISTER SENTIMENT MODEL:")
    print("-" * 40)

    sent_config = ModelServingConfig(name="sentiment", version="1.0.0")
    sent_model = SentimentModel(sent_config)

    await engine.register_model(sent_model)

    response = await engine.serve("sentiment", "This is great and wonderful!")

    print(f"   Input: 'This is great and wonderful!'")
    print(f"   Output: {response.output}")
    print()

    # 4. Batch Serving
    print("4. BATCH SERVING:")
    print("-" * 40)

    inputs = ["Good day", "Terrible experience", "Just okay", "Amazing!", "Horrible"]
    batch_response = await engine.serve_batch("sentiment", inputs)

    print(f"   Batch size: {len(inputs)}")
    print(f"   Success: {batch_response.success_count}")
    print(f"   Throughput: {batch_response.throughput:.2f} req/s")
    print(f"   Avg latency: {batch_response.avg_latency_ms:.2f}ms")
    print()

    # 5. Cache Test
    print("5. CACHE TEST:")
    print("-" * 40)

    r1 = await engine.serve("sentiment", "Same text input")
    r2 = await engine.serve("sentiment", "Same text input")

    print(f"   First status: {r1.status.value}")
    print(f"   Second status: {r2.status.value}")
    print(f"   Cache hits: {engine._cache_hits}")
    print()

    # 6. Concurrent Async Serving
    print("6. CONCURRENT ASYNC SERVING:")
    print("-" * 40)

    start = time.time()
    responses = await engine.serve_async("sentiment", inputs)
    elapsed = (time.time() - start) * 1000

    print(f"   Concurrent requests: {len(inputs)}")
    print(f"   Total time: {elapsed:.2f}ms")
    print()

    # 7. Model Info
    print("7. MODEL INFO:")
    print("-" * 40)

    info = engine.get_model_info("sentiment")

    print(f"   Name: {info.name}")
    print(f"   Version: {info.version}")
    print(f"   Request count: {info.request_count}")
    print()

    # 8. Latency Percentiles
    print("8. LATENCY PERCENTILES:")
    print("-" * 40)

    percentiles = engine.get_latency_percentiles()

    print(f"   p50: {percentiles['p50']:.2f}ms")
    print(f"   p95: {percentiles['p95']:.2f}ms")
    print(f"   p99: {percentiles['p99']:.2f}ms")
    print()

    # 9. Engine Summary
    print("9. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    print(f"   Models: {summary['models']}")
    print(f"   Total requests: {summary['total_requests']}")
    print(f"   Cache hits: {summary['cache_hits']}")
    print(f"   Throughput: {summary['throughput_per_sec']:.2f} req/s")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Model Serving Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
