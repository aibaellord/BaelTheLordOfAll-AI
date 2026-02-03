#!/usr/bin/env python3
"""
BAEL - Model Persistence Engine
Comprehensive model checkpointing for AI training pipelines.

Features:
- Model state saving/loading
- Optimizer state management
- Best model tracking
- Checkpoint rotation
- Recovery from failures
- Distributed checkpoint support
"""

import asyncio
import hashlib
import json
import math
import os
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class PersistenceType(Enum):
    """Persistence types."""
    FULL = "full"
    MODEL_ONLY = "model_only"
    OPTIMIZER_ONLY = "optimizer_only"
    INCREMENTAL = "incremental"
    BEST = "best"
    LATEST = "latest"


class PersistenceStatus(Enum):
    """Persistence status."""
    PENDING = "pending"
    SAVING = "saving"
    COMPLETE = "complete"
    FAILED = "failed"
    CORRUPTED = "corrupted"


class PersistMode(Enum):
    """Persist mode."""
    SYNC = "sync"
    ASYNC = "async"
    BACKGROUND = "background"


class SelectStrategy(Enum):
    """Strategy for selecting persisted states."""
    BEST_METRIC = "best_metric"
    LATEST = "latest"
    OLDEST = "oldest"
    BY_EPOCH = "by_epoch"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class LayerState:
    """Layer state for persistence."""
    layer_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    weights: List[List[float]] = field(default_factory=list)
    biases: List[float] = field(default_factory=list)
    layer_type: str = "dense"


@dataclass
class NetworkState:
    """Network state for persistence."""
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    layers: Dict[str, LayerState] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class OptState:
    """Optimizer state for persistence."""
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    lr: float = 0.001
    momentum: Dict[str, List[float]] = field(default_factory=dict)
    velocity: Dict[str, List[float]] = field(default_factory=dict)
    steps: int = 0


@dataclass
class TrainState:
    """Training state for persistence."""
    epoch: int = 0
    step: int = 0
    best_loss: float = float('inf')
    history: List[Dict[str, float]] = field(default_factory=list)
    seed: Optional[int] = None


@dataclass
class PersistedModel:
    """Complete persisted model."""
    persist_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    persist_type: PersistenceType = PersistenceType.FULL
    network_state: Optional[NetworkState] = None
    opt_state: Optional[OptState] = None
    train_state: Optional[TrainState] = None
    status: PersistenceStatus = PersistenceStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    path: Optional[str] = None
    hash: Optional[str] = None
    bytes: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PersistConfig:
    """Configuration for persistence."""
    dir: str = "./models"
    frequency: int = 1
    keep_n: int = 5
    best_only: bool = False
    metric: str = "loss"
    mode: str = "min"
    save_opt: bool = True


@dataclass
class PersistStats:
    """Statistics for persistence."""
    saved: int = 0
    loaded: int = 0
    deleted: int = 0
    best_epoch: int = 0
    best_loss: float = float('inf')
    avg_time_ms: float = 0.0


# =============================================================================
# STATE SERIALIZER
# =============================================================================

class ModelSerializer:
    """Serialize and deserialize states."""

    def serialize_network(self, state: NetworkState) -> Dict[str, Any]:
        """Serialize network state."""
        layers = {}
        for name, layer in state.layers.items():
            layers[name] = {
                'layer_id': layer.layer_id,
                'weights': layer.weights,
                'biases': layer.biases,
                'layer_type': layer.layer_type
            }

        return {
            'state_id': state.state_id,
            'layers': layers,
            'config': state.config,
            'created_at': state.created_at.isoformat()
        }

    def deserialize_network(self, data: Dict[str, Any]) -> NetworkState:
        """Deserialize network state."""
        layers = {}
        for name, layer_data in data.get('layers', {}).items():
            layers[name] = LayerState(
                layer_id=layer_data.get('layer_id', str(uuid.uuid4())),
                weights=layer_data.get('weights', []),
                biases=layer_data.get('biases', []),
                layer_type=layer_data.get('layer_type', 'dense')
            )

        return NetworkState(
            state_id=data.get('state_id', str(uuid.uuid4())),
            layers=layers,
            config=data.get('config', {}),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
        )

    def serialize_opt(self, state: OptState) -> Dict[str, Any]:
        """Serialize optimizer state."""
        return {
            'state_id': state.state_id,
            'lr': state.lr,
            'momentum': state.momentum,
            'velocity': state.velocity,
            'steps': state.steps
        }

    def deserialize_opt(self, data: Dict[str, Any]) -> OptState:
        """Deserialize optimizer state."""
        return OptState(
            state_id=data.get('state_id', str(uuid.uuid4())),
            lr=data.get('lr', 0.001),
            momentum=data.get('momentum', {}),
            velocity=data.get('velocity', {}),
            steps=data.get('steps', 0)
        )

    def serialize_train(self, state: TrainState) -> Dict[str, Any]:
        """Serialize training state."""
        return {
            'epoch': state.epoch,
            'step': state.step,
            'best_loss': state.best_loss,
            'history': state.history,
            'seed': state.seed
        }

    def deserialize_train(self, data: Dict[str, Any]) -> TrainState:
        """Deserialize training state."""
        return TrainState(
            epoch=data.get('epoch', 0),
            step=data.get('step', 0),
            best_loss=data.get('best_loss', float('inf')),
            history=data.get('history', []),
            seed=data.get('seed')
        )

    def serialize_model(self, model: PersistedModel) -> Dict[str, Any]:
        """Serialize full model."""
        data = {
            'persist_id': model.persist_id,
            'persist_type': model.persist_type.value,
            'status': model.status.value,
            'created_at': model.created_at.isoformat(),
            'path': model.path,
            'hash': model.hash,
            'bytes': model.bytes,
            'extra': model.extra
        }

        if model.network_state:
            data['network_state'] = self.serialize_network(model.network_state)

        if model.opt_state:
            data['opt_state'] = self.serialize_opt(model.opt_state)

        if model.train_state:
            data['train_state'] = self.serialize_train(model.train_state)

        return data

    def deserialize_model(self, data: Dict[str, Any]) -> PersistedModel:
        """Deserialize full model."""
        model = PersistedModel(
            persist_id=data.get('persist_id', str(uuid.uuid4())),
            persist_type=PersistenceType(data.get('persist_type', 'full')),
            status=PersistenceStatus(data.get('status', 'complete')),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            path=data.get('path'),
            hash=data.get('hash'),
            bytes=data.get('bytes', 0),
            extra=data.get('extra', {})
        )

        if 'network_state' in data:
            model.network_state = self.deserialize_network(data['network_state'])

        if 'opt_state' in data:
            model.opt_state = self.deserialize_opt(data['opt_state'])

        if 'train_state' in data:
            model.train_state = self.deserialize_train(data['train_state'])

        return model


# =============================================================================
# PERSISTENCE STORAGE
# =============================================================================

class PersistStorage:
    """Storage backend for persistence."""

    def __init__(self, base_dir: str = "./models"):
        self._base_dir = base_dir
        self._serializer = ModelSerializer()

    def _hash(self, data: str) -> str:
        """Compute hash of data."""
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def save(self, model: PersistedModel, filename: str) -> bool:
        """Save model (simulated)."""
        try:
            data = self._serializer.serialize_model(model)
            json_str = json.dumps(data, indent=2)

            model.hash = self._hash(json_str)
            model.bytes = len(json_str)
            model.path = f"{self._base_dir}/{filename}"
            model.status = PersistenceStatus.COMPLETE

            return True
        except Exception:
            model.status = PersistenceStatus.FAILED
            return False

    def load(self, path: str, data: Dict[str, Any]) -> Optional[PersistedModel]:
        """Load model from data."""
        try:
            model = self._serializer.deserialize_model(data)
            model.path = path
            return model
        except Exception:
            return None

    def verify(self, model: PersistedModel, data: str) -> bool:
        """Verify model integrity."""
        if not model.hash:
            return True

        computed = self._hash(data)
        return computed == model.hash


# =============================================================================
# MODEL SELECTOR
# =============================================================================

class ModelSelector:
    """Select models based on strategy."""

    def select_best(
        self,
        models: List[PersistedModel],
        mode: str = "min"
    ) -> Optional[PersistedModel]:
        """Select best model by loss."""
        if not models:
            return None

        valid = [m for m in models if m.train_state]
        if not valid:
            return models[-1]

        if mode == "min":
            return min(valid, key=lambda m: m.train_state.best_loss)
        else:
            return max(valid, key=lambda m: m.train_state.best_loss)

    def select_by_epoch(
        self,
        models: List[PersistedModel],
        epoch: int
    ) -> Optional[PersistedModel]:
        """Select model by epoch."""
        for model in models:
            if model.train_state and model.train_state.epoch == epoch:
                return model
        return None

    def select_latest(
        self,
        models: List[PersistedModel]
    ) -> Optional[PersistedModel]:
        """Select latest model."""
        if not models:
            return None
        return max(models, key=lambda m: m.created_at)

    def select_oldest(
        self,
        models: List[PersistedModel]
    ) -> Optional[PersistedModel]:
        """Select oldest model."""
        if not models:
            return None
        return min(models, key=lambda m: m.created_at)


# =============================================================================
# MODEL ROTATION
# =============================================================================

class ModelRotator:
    """Manage model rotation."""

    def __init__(self, keep_n: int = 5):
        self._keep_n = keep_n

    def rotate(
        self,
        models: List[PersistedModel],
        keep_best: bool = True
    ) -> Tuple[List[PersistedModel], List[PersistedModel]]:
        """Rotate models, return (keep, delete)."""
        if len(models) <= self._keep_n:
            return models, []

        sorted_models = sorted(
            models,
            key=lambda m: m.created_at,
            reverse=True
        )

        to_keep = sorted_models[:self._keep_n]
        to_delete = sorted_models[self._keep_n:]

        if keep_best:
            best = None
            best_loss = float('inf')

            for m in to_delete:
                if m.train_state and m.train_state.best_loss < best_loss:
                    best_loss = m.train_state.best_loss
                    best = m

            if best and best not in to_keep:
                to_keep.append(best)
                to_delete.remove(best)

        return to_keep, to_delete


# =============================================================================
# EARLY STOP MONITOR
# =============================================================================

class EarlyStopMonitor:
    """Early stopping monitor."""

    def __init__(
        self,
        patience: int = 10,
        delta: float = 0.0,
        mode: str = "min"
    ):
        self._patience = patience
        self._delta = delta
        self._mode = mode
        self._counter = 0
        self._best: Optional[float] = None
        self._stopped = False

    def step(self, metric: float) -> bool:
        """Step and check. Returns True if should stop."""
        if self._best is None:
            self._best = metric
            return False

        if self._mode == "min":
            improved = metric < self._best - self._delta
        else:
            improved = metric > self._best + self._delta

        if improved:
            self._best = metric
            self._counter = 0
        else:
            self._counter += 1

        if self._counter >= self._patience:
            self._stopped = True
            return True

        return False

    def reset(self) -> None:
        """Reset monitor."""
        self._counter = 0
        self._best = None
        self._stopped = False

    @property
    def stopped(self) -> bool:
        return self._stopped

    @property
    def counter(self) -> int:
        return self._counter


# =============================================================================
# MODEL PERSISTENCE ENGINE
# =============================================================================

class ModelPersistenceEngine:
    """
    Model Persistence Engine for BAEL.

    Comprehensive model checkpointing for AI training pipelines.
    """

    def __init__(
        self,
        save_dir: str = "./models",
        keep_n: int = 5
    ):
        self._save_dir = save_dir
        self._storage = PersistStorage(save_dir)
        self._serializer = ModelSerializer()
        self._selector = ModelSelector()
        self._rotator = ModelRotator(keep_n)
        self._early_stop = EarlyStopMonitor()
        self._models: List[PersistedModel] = []
        self._best_model: Optional[PersistedModel] = None
        self._stats = PersistStats()

    def create(
        self,
        network_state: Optional[NetworkState] = None,
        opt_state: Optional[OptState] = None,
        train_state: Optional[TrainState] = None,
        persist_type: PersistenceType = PersistenceType.FULL,
        extra: Optional[Dict[str, Any]] = None
    ) -> PersistedModel:
        """Create a new persisted model."""
        model = PersistedModel(
            persist_type=persist_type,
            network_state=network_state,
            opt_state=opt_state,
            train_state=train_state,
            extra=extra or {}
        )

        return model

    def save(
        self,
        model: PersistedModel,
        filename: Optional[str] = None
    ) -> bool:
        """Save model."""
        if not filename:
            epoch = model.train_state.epoch if model.train_state else 0
            filename = f"model_epoch_{epoch}_{model.persist_id[:8]}.json"

        success = self._storage.save(model, filename)

        if success:
            self._models.append(model)
            self._stats.saved += 1

            self._models, to_delete = self._rotator.rotate(self._models)
            self._stats.deleted += len(to_delete)

            self._update_best(model)

        return success

    def _update_best(self, model: PersistedModel) -> None:
        """Update best model."""
        if not model.train_state:
            return

        loss = model.train_state.best_loss

        if self._best_model is None:
            self._best_model = model
            self._stats.best_loss = loss
            self._stats.best_epoch = model.train_state.epoch
        elif loss < self._stats.best_loss:
            self._best_model = model
            self._stats.best_loss = loss
            self._stats.best_epoch = model.train_state.epoch

    def load_latest(self) -> Optional[PersistedModel]:
        """Load latest model."""
        model = self._selector.select_latest(self._models)
        if model:
            self._stats.loaded += 1
        return model

    def load_best(self) -> Optional[PersistedModel]:
        """Load best model."""
        if self._best_model:
            self._stats.loaded += 1
            return self._best_model
        return self._selector.select_best(self._models)

    def load_by_epoch(self, epoch: int) -> Optional[PersistedModel]:
        """Load model by epoch."""
        model = self._selector.select_by_epoch(self._models, epoch)
        if model:
            self._stats.loaded += 1
        return model

    def should_save(
        self,
        epoch: int,
        loss: Optional[float] = None,
        frequency: int = 1,
        best_only: bool = False
    ) -> bool:
        """Determine if should save."""
        if best_only:
            if loss is None:
                return False

            if self._stats.best_loss == float('inf'):
                return True

            return loss < self._stats.best_loss

        return epoch % frequency == 0

    def check_early_stop(
        self,
        loss: float,
        patience: int = 10
    ) -> bool:
        """Check early stopping."""
        self._early_stop._patience = patience
        return self._early_stop.step(loss)

    def get_models(self) -> List[PersistedModel]:
        """Get all models."""
        return self._models.copy()

    def get_stats(self) -> PersistStats:
        """Get statistics."""
        return self._stats

    def clear(self) -> None:
        """Clear all models."""
        self._stats.deleted += len(self._models)
        self._models.clear()
        self._best_model = None


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Model Persistence Engine."""
    print("=" * 70)
    print("BAEL - MODEL PERSISTENCE ENGINE DEMO")
    print("Comprehensive Model Checkpointing for AI Training Pipelines")
    print("=" * 70)
    print()

    engine = ModelPersistenceEngine(keep_n=3)

    # 1. Create Network State
    print("1. CREATE NETWORK STATE:")
    print("-" * 40)

    network_state = NetworkState(
        layers={
            'fc1': LayerState(
                weights=[[0.1, 0.2], [0.3, 0.4]],
                biases=[0.01, 0.02],
                layer_type='dense'
            ),
            'fc2': LayerState(
                weights=[[0.5, 0.6]],
                biases=[0.03],
                layer_type='dense'
            )
        },
        config={'hidden': 128, 'layers': 2}
    )

    print(f"   State ID: {network_state.state_id[:8]}...")
    print(f"   Layers: {list(network_state.layers.keys())}")
    print()

    # 2. Create Optimizer State
    print("2. CREATE OPTIMIZER STATE:")
    print("-" * 40)

    opt_state = OptState(
        lr=0.001,
        momentum={'fc1': [0.0, 0.0], 'fc2': [0.0]},
        steps=1000
    )

    print(f"   Learning rate: {opt_state.lr}")
    print(f"   Steps: {opt_state.steps}")
    print()

    # 3. Save Models
    print("3. SAVE MODELS:")
    print("-" * 40)

    for epoch in range(5):
        loss = 1.0 - epoch * 0.15 + random.uniform(-0.05, 0.05)

        train_state = TrainState(
            epoch=epoch,
            step=epoch * 100,
            best_loss=loss,
            history=[{'loss': loss}]
        )

        model = engine.create(
            network_state=network_state,
            opt_state=opt_state,
            train_state=train_state
        )

        success = engine.save(model)
        print(f"   Epoch {epoch}: loss={loss:.4f}, saved={success}")
    print()

    # 4. Load Latest
    print("4. LOAD LATEST MODEL:")
    print("-" * 40)

    latest = engine.load_latest()
    if latest:
        print(f"   Model ID: {latest.persist_id[:8]}...")
        print(f"   Epoch: {latest.train_state.epoch}")
        print(f"   Status: {latest.status.value}")
    print()

    # 5. Load Best
    print("5. LOAD BEST MODEL:")
    print("-" * 40)

    best = engine.load_best()
    if best:
        print(f"   Model ID: {best.persist_id[:8]}...")
        print(f"   Epoch: {best.train_state.epoch}")
        print(f"   Best loss: {best.train_state.best_loss:.4f}")
    print()

    # 6. Model Rotation
    print("6. MODEL ROTATION:")
    print("-" * 40)

    models = engine.get_models()
    print(f"   Total models kept: {len(models)}")
    print(f"   Keep N setting: 3")
    print()

    # 7. Should Save Logic
    print("7. SAVE DECISION LOGIC:")
    print("-" * 40)

    print(f"   Should save epoch 5 (freq=1): {engine.should_save(5, frequency=1)}")
    print(f"   Should save epoch 5 (freq=2): {engine.should_save(5, frequency=2)}")
    print(f"   Should save if best (0.3): {engine.should_save(5, loss=0.3, best_only=True)}")
    print(f"   Should save if best (0.9): {engine.should_save(5, loss=0.9, best_only=True)}")
    print()

    # 8. Early Stopping
    print("8. EARLY STOPPING:")
    print("-" * 40)

    monitor = EarlyStopMonitor(patience=3)
    losses = [1.0, 0.9, 0.85, 0.84, 0.84, 0.84, 0.84]

    for i, l in enumerate(losses):
        should_stop = monitor.step(l)
        print(f"   Step {i}: loss={l}, counter={monitor.counter}, stop={should_stop}")
    print()

    # 9. Serialization
    print("9. MODEL SERIALIZATION:")
    print("-" * 40)

    serializer = ModelSerializer()
    if latest:
        data = serializer.serialize_model(latest)
        print(f"   Keys: {list(data.keys())}")
        print(f"   Has network: {'network_state' in data}")
        print(f"   Has optimizer: {'opt_state' in data}")
    print()

    # 10. Statistics
    print("10. PERSISTENCE STATISTICS:")
    print("-" * 40)

    stats = engine.get_stats()
    print(f"   Total saved: {stats.saved}")
    print(f"   Total loaded: {stats.loaded}")
    print(f"   Total deleted: {stats.deleted}")
    print(f"   Best epoch: {stats.best_epoch}")
    print(f"   Best loss: {stats.best_loss:.4f}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Model Persistence Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
