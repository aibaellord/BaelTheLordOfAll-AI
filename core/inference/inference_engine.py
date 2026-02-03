#!/usr/bin/env python3
"""
BAEL - Inference Engine
Advanced model inference for AI agent operations.

Features:
- Model loading and caching
- Batch inference
- Async inference
- Model warming
- Request batching
- Dynamic batching
- Inference metrics
- Model ensemble support
- Request routing
"""

import asyncio
import copy
import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')
I = TypeVar('I')  # Input type
O = TypeVar('O')  # Output type


# =============================================================================
# ENUMS
# =============================================================================

class ModelStatus(Enum):
    """Model loading status."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"
    WARMING = "warming"


class BatchingMode(Enum):
    """Batching modes."""
    NONE = "none"
    STATIC = "static"
    DYNAMIC = "dynamic"


class RoutingStrategy(Enum):
    """Request routing strategies."""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_LOADED = "least_loaded"
    WEIGHTED = "weighted"


class EnsembleMethod(Enum):
    """Ensemble combination methods."""
    AVERAGE = "average"
    VOTING = "voting"
    WEIGHTED = "weighted"
    STACKING = "stacking"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class InferenceRequest:
    """Inference request."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    inputs: Any = None
    model_name: str = ""
    model_version: Optional[int] = None
    timeout: Optional[float] = None
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class InferenceResult:
    """Inference result."""
    request_id: str
    outputs: Any = None
    model_name: str = ""
    model_version: int = 0
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelConfig:
    """Model configuration."""
    name: str
    version: int = 1
    batch_size: int = 1
    max_batch_size: int = 32
    timeout_ms: float = 1000.0
    warmup_requests: int = 10
    cache_enabled: bool = True


@dataclass
class InferenceMetrics:
    """Inference metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    requests_per_second: float = 0.0

    def update(self, latency_ms: float, success: bool) -> None:
        """Update metrics with new request."""
        self.total_requests += 1

        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        self.total_latency_ms += latency_ms
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)
        self.avg_latency_ms = self.total_latency_ms / self.total_requests


@dataclass
class BatchConfig:
    """Dynamic batching configuration."""
    max_batch_size: int = 32
    max_wait_ms: float = 10.0
    min_batch_size: int = 1


# =============================================================================
# MODEL INTERFACE
# =============================================================================

class Model(ABC, Generic[I, O]):
    """Abstract model interface."""

    @abstractmethod
    async def load(self) -> None:
        """Load model."""
        pass

    @abstractmethod
    async def unload(self) -> None:
        """Unload model."""
        pass

    @abstractmethod
    async def predict(self, inputs: I) -> O:
        """Make prediction."""
        pass

    @abstractmethod
    async def predict_batch(self, inputs: List[I]) -> List[O]:
        """Make batch predictions."""
        pass


class DummyModel(Model):
    """Dummy model for testing."""

    def __init__(self, name: str, latency_ms: float = 10.0):
        self._name = name
        self._latency_ms = latency_ms
        self._loaded = False

    async def load(self) -> None:
        await asyncio.sleep(0.1)
        self._loaded = True

    async def unload(self) -> None:
        self._loaded = False

    async def predict(self, inputs: Any) -> Any:
        if not self._loaded:
            raise RuntimeError("Model not loaded")

        await asyncio.sleep(self._latency_ms / 1000)

        # Simple echo with transformation
        if isinstance(inputs, (int, float)):
            return inputs * 2
        elif isinstance(inputs, str):
            return f"processed: {inputs}"
        elif isinstance(inputs, list):
            return [x * 2 if isinstance(x, (int, float)) else x for x in inputs]
        else:
            return inputs

    async def predict_batch(self, inputs: List[Any]) -> List[Any]:
        if not self._loaded:
            raise RuntimeError("Model not loaded")

        await asyncio.sleep(self._latency_ms / 1000)

        results = []
        for inp in inputs:
            if isinstance(inp, (int, float)):
                results.append(inp * 2)
            elif isinstance(inp, str):
                results.append(f"processed: {inp}")
            else:
                results.append(inp)

        return results


# =============================================================================
# MODEL CACHE
# =============================================================================

class ModelCache:
    """Cache for loaded models."""

    def __init__(self, max_size: int = 10):
        self._cache: Dict[str, Model] = {}
        self._access_order: deque = deque()
        self._max_size = max_size
        self._status: Dict[str, ModelStatus] = {}

    def get(self, key: str) -> Optional[Model]:
        """Get model from cache."""
        if key in self._cache:
            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]
        return None

    async def put(self, key: str, model: Model) -> None:
        """Put model in cache."""
        if len(self._cache) >= self._max_size and key not in self._cache:
            # Evict LRU
            while self._access_order and len(self._cache) >= self._max_size:
                lru_key = self._access_order.popleft()
                if lru_key in self._cache:
                    old_model = self._cache.pop(lru_key)
                    await old_model.unload()
                    del self._status[lru_key]

        self._cache[key] = model
        self._status[key] = ModelStatus.READY
        self._access_order.append(key)

    async def remove(self, key: str) -> bool:
        """Remove model from cache."""
        if key in self._cache:
            model = self._cache.pop(key)
            await model.unload()
            if key in self._access_order:
                self._access_order.remove(key)
            if key in self._status:
                del self._status[key]
            return True
        return False

    def get_status(self, key: str) -> ModelStatus:
        """Get model status."""
        return self._status.get(key, ModelStatus.UNLOADED)

    def set_status(self, key: str, status: ModelStatus) -> None:
        """Set model status."""
        self._status[key] = status

    def list_models(self) -> List[str]:
        """List cached models."""
        return list(self._cache.keys())

    def size(self) -> int:
        """Get cache size."""
        return len(self._cache)


# =============================================================================
# DYNAMIC BATCHER
# =============================================================================

class DynamicBatcher:
    """Dynamic request batching."""

    def __init__(self, config: BatchConfig):
        self.config = config
        self._queue: deque = deque()
        self._lock = asyncio.Lock()
        self._batch_ready = asyncio.Event()

    async def add(self, request: InferenceRequest) -> None:
        """Add request to batch queue."""
        async with self._lock:
            self._queue.append(request)

            if len(self._queue) >= self.config.max_batch_size:
                self._batch_ready.set()

    async def get_batch(self) -> List[InferenceRequest]:
        """Get batch of requests."""
        # Wait for batch or timeout
        try:
            await asyncio.wait_for(
                self._batch_ready.wait(),
                timeout=self.config.max_wait_ms / 1000
            )
        except asyncio.TimeoutError:
            pass

        async with self._lock:
            batch = []
            while self._queue and len(batch) < self.config.max_batch_size:
                batch.append(self._queue.popleft())

            self._batch_ready.clear()
            return batch

    def queue_size(self) -> int:
        """Get queue size."""
        return len(self._queue)


# =============================================================================
# MODEL ENSEMBLE
# =============================================================================

class ModelEnsemble:
    """Ensemble of models."""

    def __init__(
        self,
        name: str,
        method: EnsembleMethod = EnsembleMethod.AVERAGE
    ):
        self._name = name
        self._method = method
        self._models: List[Model] = []
        self._weights: List[float] = []

    def add_model(self, model: Model, weight: float = 1.0) -> None:
        """Add model to ensemble."""
        self._models.append(model)
        self._weights.append(weight)

    async def predict(self, inputs: Any) -> Any:
        """Make ensemble prediction."""
        if not self._models:
            raise RuntimeError("No models in ensemble")

        # Get predictions from all models
        predictions = await asyncio.gather(*[
            m.predict(inputs) for m in self._models
        ])

        return self._combine(predictions)

    def _combine(self, predictions: List[Any]) -> Any:
        """Combine predictions."""
        if not predictions:
            return None

        if self._method == EnsembleMethod.AVERAGE:
            # Numeric average
            if all(isinstance(p, (int, float)) for p in predictions):
                return sum(predictions) / len(predictions)
            return predictions[0]

        elif self._method == EnsembleMethod.VOTING:
            # Majority voting
            from collections import Counter
            votes = Counter(predictions)
            return votes.most_common(1)[0][0]

        elif self._method == EnsembleMethod.WEIGHTED:
            # Weighted average
            if all(isinstance(p, (int, float)) for p in predictions):
                total_weight = sum(self._weights)
                weighted_sum = sum(
                    p * w for p, w in zip(predictions, self._weights)
                )
                return weighted_sum / total_weight
            return predictions[0]

        else:
            return predictions[0]


# =============================================================================
# REQUEST ROUTER
# =============================================================================

class RequestRouter:
    """Route requests to model instances."""

    def __init__(self, strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN):
        self._strategy = strategy
        self._instances: Dict[str, List[str]] = defaultdict(list)
        self._current_idx: Dict[str, int] = defaultdict(int)
        self._load: Dict[str, int] = defaultdict(int)
        self._weights: Dict[str, float] = defaultdict(lambda: 1.0)

    def register_instance(
        self,
        model_name: str,
        instance_id: str,
        weight: float = 1.0
    ) -> None:
        """Register model instance."""
        self._instances[model_name].append(instance_id)
        self._weights[instance_id] = weight

    def unregister_instance(
        self,
        model_name: str,
        instance_id: str
    ) -> None:
        """Unregister model instance."""
        if instance_id in self._instances[model_name]:
            self._instances[model_name].remove(instance_id)

    def route(self, model_name: str) -> Optional[str]:
        """Route request to instance."""
        instances = self._instances.get(model_name, [])
        if not instances:
            return None

        if self._strategy == RoutingStrategy.ROUND_ROBIN:
            idx = self._current_idx[model_name] % len(instances)
            self._current_idx[model_name] += 1
            return instances[idx]

        elif self._strategy == RoutingStrategy.RANDOM:
            import random
            return random.choice(instances)

        elif self._strategy == RoutingStrategy.LEAST_LOADED:
            return min(instances, key=lambda i: self._load.get(i, 0))

        elif self._strategy == RoutingStrategy.WEIGHTED:
            import random
            weights = [self._weights[i] for i in instances]
            total = sum(weights)
            r = random.random() * total
            cumsum = 0
            for inst, w in zip(instances, weights):
                cumsum += w
                if r <= cumsum:
                    return inst
            return instances[-1]

        return instances[0]

    def increment_load(self, instance_id: str) -> None:
        """Increment instance load."""
        self._load[instance_id] += 1

    def decrement_load(self, instance_id: str) -> None:
        """Decrement instance load."""
        self._load[instance_id] = max(0, self._load[instance_id] - 1)


# =============================================================================
# INFERENCE ENGINE
# =============================================================================

class InferenceEngine:
    """
    Inference Engine for BAEL.

    Advanced model inference system.
    """

    def __init__(
        self,
        cache_size: int = 10,
        batching_mode: BatchingMode = BatchingMode.NONE
    ):
        self._cache = ModelCache(cache_size)
        self._batching_mode = batching_mode
        self._batchers: Dict[str, DynamicBatcher] = {}
        self._metrics: Dict[str, InferenceMetrics] = defaultdict(InferenceMetrics)
        self._model_configs: Dict[str, ModelConfig] = {}
        self._router = RequestRouter()
        self._ensembles: Dict[str, ModelEnsemble] = {}
        self._model_factory: Dict[str, Callable[[], Model]] = {}

    # -------------------------------------------------------------------------
    # MODEL REGISTRATION
    # -------------------------------------------------------------------------

    def register_model(
        self,
        name: str,
        factory: Callable[[], Model],
        config: Optional[ModelConfig] = None
    ) -> None:
        """Register model factory."""
        self._model_factory[name] = factory
        self._model_configs[name] = config or ModelConfig(name=name)

        if self._batching_mode == BatchingMode.DYNAMIC:
            self._batchers[name] = DynamicBatcher(BatchConfig(
                max_batch_size=self._model_configs[name].max_batch_size
            ))

    async def load_model(
        self,
        name: str,
        version: int = 1
    ) -> bool:
        """Load model into cache."""
        key = f"{name}:v{version}"

        if self._cache.get(key):
            return True

        if name not in self._model_factory:
            return False

        self._cache.set_status(key, ModelStatus.LOADING)

        try:
            model = self._model_factory[name]()
            await model.load()
            await self._cache.put(key, model)
            return True
        except Exception as e:
            self._cache.set_status(key, ModelStatus.ERROR)
            return False

    async def unload_model(
        self,
        name: str,
        version: int = 1
    ) -> bool:
        """Unload model from cache."""
        key = f"{name}:v{version}"
        return await self._cache.remove(key)

    def get_model_status(
        self,
        name: str,
        version: int = 1
    ) -> ModelStatus:
        """Get model status."""
        key = f"{name}:v{version}"
        return self._cache.get_status(key)

    # -------------------------------------------------------------------------
    # INFERENCE
    # -------------------------------------------------------------------------

    async def infer(
        self,
        request: InferenceRequest
    ) -> InferenceResult:
        """Run inference."""
        start_time = time.time()

        model_name = request.model_name
        version = request.model_version or 1
        key = f"{model_name}:v{version}"

        # Get model
        model = self._cache.get(key)

        if not model:
            # Try to load
            loaded = await self.load_model(model_name, version)
            if not loaded:
                return InferenceResult(
                    request_id=request.request_id,
                    model_name=model_name,
                    success=False,
                    error="Model not found"
                )
            model = self._cache.get(key)

        try:
            # Run prediction
            outputs = await model.predict(request.inputs)

            latency_ms = (time.time() - start_time) * 1000

            # Update metrics
            self._metrics[model_name].update(latency_ms, True)

            return InferenceResult(
                request_id=request.request_id,
                outputs=outputs,
                model_name=model_name,
                model_version=version,
                latency_ms=latency_ms,
                success=True
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._metrics[model_name].update(latency_ms, False)

            return InferenceResult(
                request_id=request.request_id,
                model_name=model_name,
                success=False,
                error=str(e),
                latency_ms=latency_ms
            )

    async def infer_batch(
        self,
        requests: List[InferenceRequest]
    ) -> List[InferenceResult]:
        """Run batch inference."""
        if not requests:
            return []

        start_time = time.time()

        # Group by model
        by_model: Dict[str, List[InferenceRequest]] = defaultdict(list)
        for req in requests:
            key = f"{req.model_name}:v{req.model_version or 1}"
            by_model[key].append(req)

        results = []

        for key, model_requests in by_model.items():
            model = self._cache.get(key)

            if not model:
                for req in model_requests:
                    results.append(InferenceResult(
                        request_id=req.request_id,
                        model_name=req.model_name,
                        success=False,
                        error="Model not loaded"
                    ))
                continue

            try:
                inputs = [r.inputs for r in model_requests]
                outputs = await model.predict_batch(inputs)

                latency_ms = (time.time() - start_time) * 1000
                per_request_latency = latency_ms / len(model_requests)

                for req, out in zip(model_requests, outputs):
                    results.append(InferenceResult(
                        request_id=req.request_id,
                        outputs=out,
                        model_name=req.model_name,
                        model_version=req.model_version or 1,
                        latency_ms=per_request_latency,
                        success=True
                    ))
                    self._metrics[req.model_name].update(per_request_latency, True)

            except Exception as e:
                for req in model_requests:
                    results.append(InferenceResult(
                        request_id=req.request_id,
                        model_name=req.model_name,
                        success=False,
                        error=str(e)
                    ))
                    self._metrics[req.model_name].update(0, False)

        return results

    # -------------------------------------------------------------------------
    # ENSEMBLE
    # -------------------------------------------------------------------------

    def create_ensemble(
        self,
        name: str,
        model_names: List[str],
        method: EnsembleMethod = EnsembleMethod.AVERAGE,
        weights: Optional[List[float]] = None
    ) -> bool:
        """Create model ensemble."""
        ensemble = ModelEnsemble(name, method)
        weights = weights or [1.0] * len(model_names)

        for model_name, weight in zip(model_names, weights):
            key = f"{model_name}:v1"
            model = self._cache.get(key)
            if model:
                ensemble.add_model(model, weight)

        self._ensembles[name] = ensemble
        return True

    async def infer_ensemble(
        self,
        ensemble_name: str,
        inputs: Any
    ) -> Optional[Any]:
        """Run ensemble inference."""
        ensemble = self._ensembles.get(ensemble_name)
        if ensemble:
            return await ensemble.predict(inputs)
        return None

    # -------------------------------------------------------------------------
    # WARMING
    # -------------------------------------------------------------------------

    async def warm_model(
        self,
        name: str,
        version: int = 1,
        sample_inputs: Optional[List[Any]] = None
    ) -> bool:
        """Warm up model with sample requests."""
        key = f"{name}:v{version}"
        model = self._cache.get(key)

        if not model:
            return False

        self._cache.set_status(key, ModelStatus.WARMING)

        config = self._model_configs.get(name)
        num_warmup = config.warmup_requests if config else 10

        sample_inputs = sample_inputs or [0] * num_warmup

        try:
            for inp in sample_inputs[:num_warmup]:
                await model.predict(inp)

            self._cache.set_status(key, ModelStatus.READY)
            return True

        except Exception:
            self._cache.set_status(key, ModelStatus.ERROR)
            return False

    # -------------------------------------------------------------------------
    # METRICS
    # -------------------------------------------------------------------------

    def get_metrics(self, model_name: str) -> Optional[InferenceMetrics]:
        """Get model metrics."""
        return self._metrics.get(model_name)

    def reset_metrics(self, model_name: Optional[str] = None) -> None:
        """Reset metrics."""
        if model_name:
            self._metrics[model_name] = InferenceMetrics()
        else:
            self._metrics.clear()

    # -------------------------------------------------------------------------
    # INFO
    # -------------------------------------------------------------------------

    def list_loaded_models(self) -> List[str]:
        """List loaded models."""
        return self._cache.list_models()

    def list_registered_models(self) -> List[str]:
        """List registered models."""
        return list(self._model_factory.keys())

    def list_ensembles(self) -> List[str]:
        """List ensembles."""
        return list(self._ensembles.keys())


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Inference Engine."""
    print("=" * 70)
    print("BAEL - INFERENCE ENGINE DEMO")
    print("Advanced Model Inference for AI Agents")
    print("=" * 70)
    print()

    engine = InferenceEngine(cache_size=5)

    # 1. Register Models
    print("1. REGISTER MODELS:")
    print("-" * 40)

    engine.register_model(
        "classifier",
        lambda: DummyModel("classifier", latency_ms=5),
        ModelConfig(name="classifier", batch_size=8)
    )

    engine.register_model(
        "regressor",
        lambda: DummyModel("regressor", latency_ms=3),
        ModelConfig(name="regressor", batch_size=16)
    )

    print(f"   Registered: {engine.list_registered_models()}")
    print()

    # 2. Load Model
    print("2. LOAD MODEL:")
    print("-" * 40)

    loaded = await engine.load_model("classifier")
    print(f"   Loaded classifier: {loaded}")
    print(f"   Status: {engine.get_model_status('classifier').value}")
    print()

    # 3. Single Inference
    print("3. SINGLE INFERENCE:")
    print("-" * 40)

    request = InferenceRequest(
        inputs=42,
        model_name="classifier"
    )

    result = await engine.infer(request)
    print(f"   Input: 42")
    print(f"   Output: {result.outputs}")
    print(f"   Latency: {result.latency_ms:.2f}ms")
    print(f"   Success: {result.success}")
    print()

    # 4. Batch Inference
    print("4. BATCH INFERENCE:")
    print("-" * 40)

    requests = [
        InferenceRequest(inputs=i, model_name="classifier")
        for i in range(5)
    ]

    results = await engine.infer_batch(requests)
    print(f"   Inputs: [0, 1, 2, 3, 4]")
    print(f"   Outputs: {[r.outputs for r in results]}")
    print()

    # 5. String Input
    print("5. STRING INPUT:")
    print("-" * 40)

    request = InferenceRequest(
        inputs="hello world",
        model_name="classifier"
    )

    result = await engine.infer(request)
    print(f"   Input: 'hello world'")
    print(f"   Output: '{result.outputs}'")
    print()

    # 6. Model Warming
    print("6. MODEL WARMING:")
    print("-" * 40)

    await engine.load_model("regressor")
    warmed = await engine.warm_model("regressor", sample_inputs=[1, 2, 3, 4, 5])

    print(f"   Warmed regressor: {warmed}")
    print(f"   Status: {engine.get_model_status('regressor').value}")
    print()

    # 7. Metrics
    print("7. INFERENCE METRICS:")
    print("-" * 40)

    metrics = engine.get_metrics("classifier")
    if metrics:
        print(f"   Total requests: {metrics.total_requests}")
        print(f"   Successful: {metrics.successful_requests}")
        print(f"   Avg latency: {metrics.avg_latency_ms:.2f}ms")
        print(f"   Min latency: {metrics.min_latency_ms:.2f}ms")
        print(f"   Max latency: {metrics.max_latency_ms:.2f}ms")
    print()

    # 8. Ensemble
    print("8. MODEL ENSEMBLE:")
    print("-" * 40)

    engine.create_ensemble(
        "combined",
        ["classifier", "regressor"],
        method=EnsembleMethod.AVERAGE
    )

    result = await engine.infer_ensemble("combined", 10)
    print(f"   Ensemble input: 10")
    print(f"   Ensemble output: {result}")
    print()

    # 9. List Models
    print("9. LIST MODELS:")
    print("-" * 40)

    print(f"   Registered: {engine.list_registered_models()}")
    print(f"   Loaded: {engine.list_loaded_models()}")
    print(f"   Ensembles: {engine.list_ensembles()}")
    print()

    # 10. Unload Model
    print("10. UNLOAD MODEL:")
    print("-" * 40)

    unloaded = await engine.unload_model("regressor")
    print(f"   Unloaded regressor: {unloaded}")
    print(f"   Loaded after unload: {engine.list_loaded_models()}")
    print()

    # 11. Auto-load on Inference
    print("11. AUTO-LOAD ON INFERENCE:")
    print("-" * 40)

    request = InferenceRequest(
        inputs=100,
        model_name="regressor"
    )

    result = await engine.infer(request)
    print(f"   Requested regressor (was unloaded)")
    print(f"   Auto-loaded and inferred: {result.success}")
    print(f"   Output: {result.outputs}")
    print()

    # 12. Error Handling
    print("12. ERROR HANDLING:")
    print("-" * 40)

    request = InferenceRequest(
        inputs=42,
        model_name="nonexistent"
    )

    result = await engine.infer(request)
    print(f"   Model: nonexistent")
    print(f"   Success: {result.success}")
    print(f"   Error: {result.error}")
    print()

    # 13. Multiple Batch Inference
    print("13. MULTI-MODEL BATCH:")
    print("-" * 40)

    requests = [
        InferenceRequest(inputs=1, model_name="classifier"),
        InferenceRequest(inputs=2, model_name="regressor"),
        InferenceRequest(inputs=3, model_name="classifier"),
    ]

    results = await engine.infer_batch(requests)
    for r in results:
        print(f"   {r.model_name}: {r.outputs}")
    print()

    # 14. Reset Metrics
    print("14. RESET METRICS:")
    print("-" * 40)

    engine.reset_metrics("classifier")
    metrics = engine.get_metrics("classifier")
    print(f"   After reset - Total requests: {metrics.total_requests if metrics else 0}")
    print()

    # 15. Summary
    print("15. FINAL STATE:")
    print("-" * 40)

    print(f"   Loaded models: {engine.list_loaded_models()}")
    print(f"   Ensembles: {engine.list_ensembles()}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Inference Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
