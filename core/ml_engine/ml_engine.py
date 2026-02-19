"""
BAEL Machine Learning Engine
============================

Comprehensive ML framework with:
- Model training and inference
- Experiment tracking
- Feature store
- Model registry
- Auto-ML capabilities
- Deployment management

"Intelligence that learns is intelligence that grows." — Ba'el
"""

import asyncio
import logging
import json
import pickle
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
import uuid
from pathlib import Path
import math
import random

logger = logging.getLogger("BAEL.MLEngine")


# ============================================================================
# ENUMS
# ============================================================================

class ModelType(Enum):
    """Types of machine learning models."""
    LINEAR_REGRESSION = "linear_regression"
    LOGISTIC_REGRESSION = "logistic_regression"
    DECISION_TREE = "decision_tree"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    NEURAL_NETWORK = "neural_network"
    SVM = "svm"
    KNN = "knn"
    NAIVE_BAYES = "naive_bayes"
    KMEANS = "kmeans"
    CUSTOM = "custom"


class TaskType(Enum):
    """Types of ML tasks."""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    RANKING = "ranking"
    ANOMALY_DETECTION = "anomaly_detection"
    RECOMMENDATION = "recommendation"
    NLP = "nlp"
    TIME_SERIES = "time_series"
    REINFORCEMENT = "reinforcement"


class TrainingStatus(Enum):
    """Status of model training."""
    PENDING = "pending"
    PREPARING = "preparing"
    TRAINING = "training"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InferenceMode(Enum):
    """Inference execution modes."""
    SYNC = "sync"           # Synchronous
    ASYNC = "async"         # Asynchronous
    BATCH = "batch"         # Batch processing
    STREAMING = "streaming" # Streaming


class OptimizationGoal(Enum):
    """Optimization goals for training."""
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Dataset:
    """A dataset for training or inference."""
    id: str
    name: str
    features: List[List[float]]
    labels: Optional[List[Any]] = None

    # Metadata
    feature_names: Optional[List[str]] = None
    label_name: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def num_samples(self) -> int:
        return len(self.features)

    @property
    def num_features(self) -> int:
        return len(self.features[0]) if self.features else 0

    def split(
        self,
        train_ratio: float = 0.8,
        shuffle: bool = True
    ) -> Tuple['Dataset', 'Dataset']:
        """Split dataset into train and validation sets."""
        indices = list(range(self.num_samples))
        if shuffle:
            random.shuffle(indices)

        split_idx = int(len(indices) * train_ratio)
        train_indices = indices[:split_idx]
        val_indices = indices[split_idx:]

        train_dataset = Dataset(
            id=f"{self.id}_train",
            name=f"{self.name}_train",
            features=[self.features[i] for i in train_indices],
            labels=[self.labels[i] for i in train_indices] if self.labels else None,
            feature_names=self.feature_names,
            label_name=self.label_name
        )

        val_dataset = Dataset(
            id=f"{self.id}_val",
            name=f"{self.name}_val",
            features=[self.features[i] for i in val_indices],
            labels=[self.labels[i] for i in val_indices] if self.labels else None,
            feature_names=self.feature_names,
            label_name=self.label_name
        )

        return train_dataset, val_dataset


@dataclass
class TrainingConfig:
    """Configuration for model training."""
    epochs: int = 100
    batch_size: int = 32
    learning_rate: float = 0.01
    validation_split: float = 0.2
    early_stopping_patience: int = 10
    optimization_goal: OptimizationGoal = OptimizationGoal.MINIMIZE
    optimization_metric: str = "loss"

    # Regularization
    l1_regularization: float = 0.0
    l2_regularization: float = 0.0
    dropout_rate: float = 0.0

    # Advanced
    shuffle: bool = True
    seed: Optional[int] = None
    verbose: bool = True

    # Custom parameters
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrainingResult:
    """Result of model training."""
    model_id: str
    status: TrainingStatus
    epochs_completed: int
    training_time_seconds: float

    # Metrics
    final_loss: float
    final_metrics: Dict[str, float]
    history: Dict[str, List[float]] = field(default_factory=dict)

    # Best model
    best_epoch: int = 0
    best_metric: float = 0.0

    # Errors
    error: Optional[str] = None

    # Timestamps
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


@dataclass
class Model:
    """A machine learning model."""
    id: str
    name: str
    model_type: ModelType
    task_type: TaskType

    # Architecture
    weights: Optional[Any] = None
    architecture: Dict[str, Any] = field(default_factory=dict)

    # Training
    training_config: Optional[TrainingConfig] = None
    training_result: Optional[TrainingResult] = None

    # State
    is_trained: bool = False
    version: int = 1

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def predict(self, features: List[List[float]]) -> List[Any]:
        """Make predictions using the model."""
        if not self.is_trained:
            raise ValueError("Model is not trained")

        # Simple linear prediction for demonstration
        if self.weights is None:
            return [0.0] * len(features)

        predictions = []
        for x in features:
            pred = sum(w * xi for w, xi in zip(self.weights, x))

            if self.task_type == TaskType.CLASSIFICATION:
                pred = 1 if pred > 0.5 else 0

            predictions.append(pred)

        return predictions


@dataclass
class Prediction:
    """A model prediction."""
    model_id: str
    input_features: List[float]
    prediction: Any
    probability: Optional[float] = None
    confidence: Optional[float] = None
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Experiment:
    """An ML experiment."""
    id: str
    name: str
    description: str = ""

    # Models
    model_ids: List[str] = field(default_factory=list)

    # Parameters
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Metrics
    metrics: Dict[str, float] = field(default_factory=dict)

    # State
    status: TrainingStatus = TrainingStatus.PENDING

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Artifacts
    artifacts: Dict[str, str] = field(default_factory=dict)

    # Tags
    tags: List[str] = field(default_factory=list)


@dataclass
class MLEngineConfig:
    """Configuration for the ML engine."""
    model_directory: str = "./models"
    experiment_directory: str = "./experiments"
    feature_store_directory: str = "./features"
    max_concurrent_training: int = 2
    enable_auto_ml: bool = True
    enable_experiment_tracking: bool = True


# ============================================================================
# MODEL REGISTRY
# ============================================================================

class ModelRegistry:
    """
    Registry for managing ML models.
    """

    def __init__(self, model_dir: str = "./models"):
        """Initialize model registry."""
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self._models: Dict[str, Model] = {}
        self._versions: Dict[str, List[str]] = defaultdict(list)  # name -> [ids]

    def register(self, model: Model) -> str:
        """Register a model."""
        self._models[model.id] = model
        self._versions[model.name].append(model.id)
        logger.info(f"Registered model: {model.name} v{model.version}")
        return model.id

    def get(self, model_id: str) -> Optional[Model]:
        """Get a model by ID."""
        return self._models.get(model_id)

    def get_by_name(self, name: str, version: Optional[int] = None) -> Optional[Model]:
        """Get a model by name and optional version."""
        versions = self._versions.get(name, [])
        if not versions:
            return None

        if version is not None:
            for model_id in versions:
                model = self._models.get(model_id)
                if model and model.version == version:
                    return model
            return None

        # Return latest version
        return self._models.get(versions[-1])

    def list(self, task_type: Optional[TaskType] = None) -> List[Model]:
        """List all models."""
        models = list(self._models.values())
        if task_type:
            models = [m for m in models if m.task_type == task_type]
        return models

    def delete(self, model_id: str) -> bool:
        """Delete a model."""
        if model_id in self._models:
            model = self._models.pop(model_id)
            if model.name in self._versions:
                if model_id in self._versions[model.name]:
                    self._versions[model.name].remove(model_id)
            return True
        return False

    def save(self, model_id: str) -> str:
        """Save a model to disk."""
        model = self._models.get(model_id)
        if not model:
            raise ValueError(f"Model not found: {model_id}")

        path = self.model_dir / f"{model_id}.pkl"
        with open(path, 'wb') as f:
            pickle.dump(model, f)

        return str(path)

    def load(self, path: str) -> Model:
        """Load a model from disk."""
        with open(path, 'rb') as f:
            model = pickle.load(f)

        self.register(model)
        return model


# ============================================================================
# DATA PROCESSOR
# ============================================================================

class DataProcessor:
    """
    Process data for ML training and inference.
    """

    def __init__(self):
        """Initialize data processor."""
        self._scalers: Dict[str, Dict[str, Any]] = {}
        self._encoders: Dict[str, Dict[str, int]] = {}

    def normalize(
        self,
        data: List[List[float]],
        method: str = "minmax",
        fit: bool = True,
        scaler_id: str = "default"
    ) -> List[List[float]]:
        """Normalize numerical data."""
        if not data:
            return data

        num_features = len(data[0])

        if fit:
            if method == "minmax":
                mins = [min(row[i] for row in data) for i in range(num_features)]
                maxs = [max(row[i] for row in data) for i in range(num_features)]
                ranges = [maxs[i] - mins[i] if maxs[i] != mins[i] else 1.0 for i in range(num_features)]
                self._scalers[scaler_id] = {'method': method, 'mins': mins, 'ranges': ranges}

            elif method == "standard":
                means = [sum(row[i] for row in data) / len(data) for i in range(num_features)]
                stds = [
                    math.sqrt(sum((row[i] - means[i]) ** 2 for row in data) / len(data))
                    for i in range(num_features)
                ]
                stds = [s if s != 0 else 1.0 for s in stds]
                self._scalers[scaler_id] = {'method': method, 'means': means, 'stds': stds}

        scaler = self._scalers.get(scaler_id, {})

        if scaler.get('method') == "minmax":
            mins = scaler['mins']
            ranges = scaler['ranges']
            return [
                [(row[i] - mins[i]) / ranges[i] for i in range(num_features)]
                for row in data
            ]

        elif scaler.get('method') == "standard":
            means = scaler['means']
            stds = scaler['stds']
            return [
                [(row[i] - means[i]) / stds[i] for i in range(num_features)]
                for row in data
            ]

        return data

    def encode_labels(
        self,
        labels: List[Any],
        fit: bool = True,
        encoder_id: str = "default"
    ) -> List[int]:
        """Encode categorical labels as integers."""
        if fit:
            unique = sorted(set(labels))
            self._encoders[encoder_id] = {v: i for i, v in enumerate(unique)}

        encoder = self._encoders.get(encoder_id, {})
        return [encoder.get(label, -1) for label in labels]

    def decode_labels(
        self,
        encoded: List[int],
        encoder_id: str = "default"
    ) -> List[Any]:
        """Decode integer labels back to original values."""
        encoder = self._encoders.get(encoder_id, {})
        reverse = {v: k for k, v in encoder.items()}
        return [reverse.get(e, None) for e in encoded]

    def handle_missing(
        self,
        data: List[List[float]],
        strategy: str = "mean"
    ) -> List[List[float]]:
        """Handle missing values in data."""
        if not data:
            return data

        num_features = len(data[0])

        # Calculate fill values
        fill_values = []
        for i in range(num_features):
            values = [row[i] for row in data if row[i] is not None and not math.isnan(row[i])]

            if strategy == "mean":
                fill = sum(values) / len(values) if values else 0.0
            elif strategy == "median":
                sorted_vals = sorted(values)
                mid = len(sorted_vals) // 2
                fill = sorted_vals[mid] if values else 0.0
            elif strategy == "zero":
                fill = 0.0
            else:
                fill = 0.0

            fill_values.append(fill)

        # Fill missing values
        result = []
        for row in data:
            new_row = []
            for i, val in enumerate(row):
                if val is None or (isinstance(val, float) and math.isnan(val)):
                    new_row.append(fill_values[i])
                else:
                    new_row.append(val)
            result.append(new_row)

        return result


# ============================================================================
# FEATURE STORE
# ============================================================================

class FeatureStore:
    """
    Store and manage features for ML models.
    """

    def __init__(self, store_dir: str = "./features"):
        """Initialize feature store."""
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)

        self._features: Dict[str, Dict[str, Any]] = {}
        self._feature_groups: Dict[str, List[str]] = defaultdict(list)

    def register_feature(
        self,
        name: str,
        description: str = "",
        dtype: str = "float",
        group: Optional[str] = None,
        transformation: Optional[Callable] = None
    ) -> None:
        """Register a feature definition."""
        feature_id = str(uuid.uuid4())
        self._features[name] = {
            'id': feature_id,
            'description': description,
            'dtype': dtype,
            'transformation': transformation,
            'created_at': datetime.now()
        }

        if group:
            self._feature_groups[group].append(name)

        logger.info(f"Registered feature: {name}")

    def compute_feature(
        self,
        name: str,
        data: Any
    ) -> Any:
        """Compute a feature value."""
        if name not in self._features:
            raise ValueError(f"Feature not registered: {name}")

        feature = self._features[name]
        transformation = feature.get('transformation')

        if transformation:
            return transformation(data)

        return data

    def get_feature_group(self, group: str) -> List[str]:
        """Get features in a group."""
        return self._feature_groups.get(group, [])

    def list_features(self) -> List[Dict[str, Any]]:
        """List all registered features."""
        return [
            {'name': name, **info}
            for name, info in self._features.items()
        ]


# ============================================================================
# EXPERIMENT TRACKER
# ============================================================================

class ExperimentTracker:
    """
    Track ML experiments and their results.
    """

    def __init__(self, experiment_dir: str = "./experiments"):
        """Initialize experiment tracker."""
        self.experiment_dir = Path(experiment_dir)
        self.experiment_dir.mkdir(parents=True, exist_ok=True)

        self._experiments: Dict[str, Experiment] = {}
        self._active_experiment: Optional[str] = None

    def create(
        self,
        name: str,
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Experiment:
        """Create a new experiment."""
        experiment = Experiment(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            parameters=parameters or {},
            tags=tags or []
        )

        self._experiments[experiment.id] = experiment
        self._active_experiment = experiment.id

        logger.info(f"Created experiment: {name}")
        return experiment

    def get(self, experiment_id: str) -> Optional[Experiment]:
        """Get an experiment by ID."""
        return self._experiments.get(experiment_id)

    def get_active(self) -> Optional[Experiment]:
        """Get the active experiment."""
        if self._active_experiment:
            return self._experiments.get(self._active_experiment)
        return None

    def log_metric(
        self,
        name: str,
        value: float,
        experiment_id: Optional[str] = None
    ) -> None:
        """Log a metric to an experiment."""
        exp_id = experiment_id or self._active_experiment
        if exp_id and exp_id in self._experiments:
            self._experiments[exp_id].metrics[name] = value

    def log_parameter(
        self,
        name: str,
        value: Any,
        experiment_id: Optional[str] = None
    ) -> None:
        """Log a parameter to an experiment."""
        exp_id = experiment_id or self._active_experiment
        if exp_id and exp_id in self._experiments:
            self._experiments[exp_id].parameters[name] = value

    def log_artifact(
        self,
        name: str,
        path: str,
        experiment_id: Optional[str] = None
    ) -> None:
        """Log an artifact to an experiment."""
        exp_id = experiment_id or self._active_experiment
        if exp_id and exp_id in self._experiments:
            self._experiments[exp_id].artifacts[name] = path

    def add_model(
        self,
        model_id: str,
        experiment_id: Optional[str] = None
    ) -> None:
        """Add a model to an experiment."""
        exp_id = experiment_id or self._active_experiment
        if exp_id and exp_id in self._experiments:
            self._experiments[exp_id].model_ids.append(model_id)

    def complete(
        self,
        status: TrainingStatus = TrainingStatus.COMPLETED,
        experiment_id: Optional[str] = None
    ) -> None:
        """Complete an experiment."""
        exp_id = experiment_id or self._active_experiment
        if exp_id and exp_id in self._experiments:
            self._experiments[exp_id].status = status
            self._experiments[exp_id].completed_at = datetime.now()

    def compare(
        self,
        experiment_ids: List[str],
        metric: str
    ) -> List[Tuple[str, float]]:
        """Compare experiments by a metric."""
        results = []
        for exp_id in experiment_ids:
            exp = self._experiments.get(exp_id)
            if exp and metric in exp.metrics:
                results.append((exp_id, exp.metrics[metric]))

        return sorted(results, key=lambda x: x[1], reverse=True)

    def list(
        self,
        tags: Optional[List[str]] = None,
        status: Optional[TrainingStatus] = None
    ) -> List[Experiment]:
        """List experiments with optional filters."""
        experiments = list(self._experiments.values())

        if tags:
            experiments = [e for e in experiments if any(t in e.tags for t in tags)]

        if status:
            experiments = [e for e in experiments if e.status == status]

        return experiments


# ============================================================================
# MODEL DEPLOYER
# ============================================================================

class ModelDeployer:
    """
    Deploy and manage model serving.
    """

    def __init__(self, registry: ModelRegistry):
        """Initialize model deployer."""
        self.registry = registry
        self._deployed: Dict[str, Dict[str, Any]] = {}
        self._endpoints: Dict[str, str] = {}  # endpoint -> model_id

    def deploy(
        self,
        model_id: str,
        endpoint: str,
        replicas: int = 1,
        resources: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Deploy a model to an endpoint."""
        model = self.registry.get(model_id)
        if not model:
            raise ValueError(f"Model not found: {model_id}")

        if not model.is_trained:
            raise ValueError(f"Model is not trained: {model_id}")

        deployment = {
            'model_id': model_id,
            'endpoint': endpoint,
            'replicas': replicas,
            'resources': resources or {},
            'status': 'running',
            'deployed_at': datetime.now()
        }

        self._deployed[model_id] = deployment
        self._endpoints[endpoint] = model_id

        logger.info(f"Deployed model {model.name} to endpoint {endpoint}")
        return deployment

    def undeploy(self, model_id: str) -> bool:
        """Undeploy a model."""
        if model_id in self._deployed:
            deployment = self._deployed.pop(model_id)
            endpoint = deployment.get('endpoint')
            if endpoint and endpoint in self._endpoints:
                del self._endpoints[endpoint]
            return True
        return False

    def get_endpoint_model(self, endpoint: str) -> Optional[Model]:
        """Get the model deployed at an endpoint."""
        model_id = self._endpoints.get(endpoint)
        if model_id:
            return self.registry.get(model_id)
        return None

    def predict(
        self,
        endpoint: str,
        features: List[List[float]]
    ) -> List[Prediction]:
        """Make predictions using a deployed model."""
        model = self.get_endpoint_model(endpoint)
        if not model:
            raise ValueError(f"No model at endpoint: {endpoint}")

        start = datetime.now()
        raw_predictions = model.predict(features)
        latency = (datetime.now() - start).total_seconds() * 1000

        predictions = []
        for i, (feat, pred) in enumerate(zip(features, raw_predictions)):
            predictions.append(Prediction(
                model_id=model.id,
                input_features=feat,
                prediction=pred,
                latency_ms=latency / len(features)
            ))

        return predictions

    def list_deployments(self) -> List[Dict[str, Any]]:
        """List all deployments."""
        return list(self._deployed.values())


# ============================================================================
# MAIN ML ENGINE
# ============================================================================

class MachineLearningEngine:
    """
    Main machine learning engine.

    Features:
    - Model training and inference
    - Experiment tracking
    - Feature store
    - Model registry
    - Auto-ML capabilities
    - Deployment management

    "Ba'el's learning transcends mortal limits." — Ba'el
    """

    def __init__(self, config: Optional[MLEngineConfig] = None):
        """Initialize ML engine."""
        self.config = config or MLEngineConfig()

        # Components
        self.registry = ModelRegistry(self.config.model_directory)
        self.data_processor = DataProcessor()
        self.feature_store = FeatureStore(self.config.feature_store_directory)
        self.experiments = ExperimentTracker(self.config.experiment_directory)
        self.deployer = ModelDeployer(self.registry)

        # Training semaphore
        self._training_semaphore = asyncio.Semaphore(
            self.config.max_concurrent_training
        )

        # Statistics
        self._stats = {
            'models_trained': 0,
            'predictions_made': 0,
            'experiments_run': 0
        }

        logger.info("MachineLearningEngine initialized")

    # ========================================================================
    # MODEL CREATION
    # ========================================================================

    def create_model(
        self,
        name: str,
        model_type: ModelType,
        task_type: TaskType,
        architecture: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Model:
        """Create a new model."""
        model = Model(
            id=str(uuid.uuid4()),
            name=name,
            model_type=model_type,
            task_type=task_type,
            architecture=architecture or {},
            metadata=metadata or {}
        )

        self.registry.register(model)
        return model

    # ========================================================================
    # TRAINING
    # ========================================================================

    async def train(
        self,
        model_id: str,
        dataset: Dataset,
        config: Optional[TrainingConfig] = None
    ) -> TrainingResult:
        """Train a model."""
        async with self._training_semaphore:
            model = self.registry.get(model_id)
            if not model:
                raise ValueError(f"Model not found: {model_id}")

            config = config or TrainingConfig()
            model.training_config = config

            # Split data
            train_data, val_data = dataset.split(1 - config.validation_split, config.shuffle)

            # Process data
            X_train = self.data_processor.normalize(train_data.features, fit=True)
            X_val = self.data_processor.normalize(val_data.features, fit=False)

            y_train = train_data.labels
            y_val = val_data.labels

            if model.task_type == TaskType.CLASSIFICATION and y_train:
                y_train = self.data_processor.encode_labels(y_train, fit=True)
                y_val = self.data_processor.encode_labels(y_val, fit=False)

            # Training
            start_time = datetime.now()
            history = {'loss': [], 'val_loss': []}

            num_features = len(X_train[0]) if X_train else 0
            model.weights = [random.uniform(-0.1, 0.1) for _ in range(num_features)]

            best_loss = float('inf')
            best_epoch = 0
            patience_counter = 0

            for epoch in range(config.epochs):
                # Simulate training
                epoch_loss = self._train_epoch(
                    model, X_train, y_train, config
                )

                val_loss = self._evaluate(model, X_val, y_val)

                history['loss'].append(epoch_loss)
                history['val_loss'].append(val_loss)

                # Early stopping
                if val_loss < best_loss:
                    best_loss = val_loss
                    best_epoch = epoch
                    patience_counter = 0
                else:
                    patience_counter += 1

                if patience_counter >= config.early_stopping_patience:
                    logger.info(f"Early stopping at epoch {epoch}")
                    break

                if config.verbose and epoch % 10 == 0:
                    logger.info(f"Epoch {epoch}: loss={epoch_loss:.4f}, val_loss={val_loss:.4f}")

            training_time = (datetime.now() - start_time).total_seconds()

            model.is_trained = True
            model.updated_at = datetime.now()

            result = TrainingResult(
                model_id=model.id,
                status=TrainingStatus.COMPLETED,
                epochs_completed=epoch + 1,
                training_time_seconds=training_time,
                final_loss=history['loss'][-1],
                final_metrics={'val_loss': history['val_loss'][-1]},
                history=history,
                best_epoch=best_epoch,
                best_metric=best_loss,
                completed_at=datetime.now()
            )

            model.training_result = result
            self._stats['models_trained'] += 1

            logger.info(f"Model {model.name} trained: loss={result.final_loss:.4f}")
            return result

    def _train_epoch(
        self,
        model: Model,
        X: List[List[float]],
        y: List[Any],
        config: TrainingConfig
    ) -> float:
        """Train for one epoch."""
        total_loss = 0.0
        num_batches = 0

        indices = list(range(len(X)))
        if config.shuffle:
            random.shuffle(indices)

        for i in range(0, len(X), config.batch_size):
            batch_indices = indices[i:i + config.batch_size]
            X_batch = [X[j] for j in batch_indices]
            y_batch = [y[j] for j in batch_indices] if y else None

            batch_loss = self._train_batch(model, X_batch, y_batch, config)
            total_loss += batch_loss
            num_batches += 1

        return total_loss / max(num_batches, 1)

    def _train_batch(
        self,
        model: Model,
        X: List[List[float]],
        y: List[Any],
        config: TrainingConfig
    ) -> float:
        """Train on a batch (simplified gradient descent)."""
        if not X or not y:
            return 0.0

        total_loss = 0.0
        gradients = [0.0] * len(model.weights)

        for xi, yi in zip(X, y):
            # Forward pass
            pred = sum(w * x for w, x in zip(model.weights, xi))

            # Loss (MSE for regression, cross-entropy-ish for classification)
            if model.task_type == TaskType.CLASSIFICATION:
                pred_prob = 1 / (1 + math.exp(-max(min(pred, 500), -500)))  # Sigmoid
                loss = -yi * math.log(max(pred_prob, 1e-10)) - (1 - yi) * math.log(max(1 - pred_prob, 1e-10))
                error = pred_prob - yi
            else:
                loss = (pred - yi) ** 2
                error = 2 * (pred - yi)

            total_loss += loss

            # Gradients
            for j in range(len(gradients)):
                gradients[j] += error * xi[j]

        # Update weights
        for j in range(len(model.weights)):
            grad = gradients[j] / len(X)

            # L2 regularization
            grad += config.l2_regularization * model.weights[j]

            model.weights[j] -= config.learning_rate * grad

        return total_loss / len(X)

    def _evaluate(
        self,
        model: Model,
        X: List[List[float]],
        y: List[Any]
    ) -> float:
        """Evaluate model on data."""
        if not X or not y:
            return 0.0

        total_loss = 0.0

        for xi, yi in zip(X, y):
            pred = sum(w * x for w, x in zip(model.weights, xi))

            if model.task_type == TaskType.CLASSIFICATION:
                pred_prob = 1 / (1 + math.exp(-max(min(pred, 500), -500)))
                loss = -yi * math.log(max(pred_prob, 1e-10)) - (1 - yi) * math.log(max(1 - pred_prob, 1e-10))
            else:
                loss = (pred - yi) ** 2

            total_loss += loss

        return total_loss / len(X)

    # ========================================================================
    # INFERENCE
    # ========================================================================

    def predict(
        self,
        model_id: str,
        features: List[List[float]],
        normalize: bool = True
    ) -> List[Prediction]:
        """Make predictions using a model."""
        model = self.registry.get(model_id)
        if not model:
            raise ValueError(f"Model not found: {model_id}")

        if normalize:
            features = self.data_processor.normalize(features, fit=False)

        start = datetime.now()
        raw_predictions = model.predict(features)
        latency = (datetime.now() - start).total_seconds() * 1000

        predictions = []
        for feat, pred in zip(features, raw_predictions):
            predictions.append(Prediction(
                model_id=model_id,
                input_features=feat,
                prediction=pred,
                latency_ms=latency / max(len(features), 1)
            ))

        self._stats['predictions_made'] += len(predictions)
        return predictions

    # ========================================================================
    # AUTO-ML
    # ========================================================================

    async def auto_train(
        self,
        dataset: Dataset,
        task_type: TaskType,
        time_budget_seconds: int = 300,
        metric: str = "val_loss"
    ) -> Model:
        """Automatically train the best model for a dataset."""
        if not self.config.enable_auto_ml:
            raise ValueError("Auto-ML is disabled")

        logger.info(f"Starting Auto-ML for {task_type.value} task")

        # Create experiment
        experiment = self.experiments.create(
            name=f"auto_ml_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            description=f"Auto-ML for {task_type.value}",
            tags=["auto-ml"]
        )

        # Model types to try
        if task_type == TaskType.CLASSIFICATION:
            model_types = [ModelType.LOGISTIC_REGRESSION]
        elif task_type == TaskType.REGRESSION:
            model_types = [ModelType.LINEAR_REGRESSION]
        else:
            model_types = [ModelType.LINEAR_REGRESSION]

        # Hyperparameter grid
        learning_rates = [0.001, 0.01, 0.1]

        best_model = None
        best_metric_value = float('inf')

        start_time = datetime.now()

        for model_type in model_types:
            for lr in learning_rates:
                if (datetime.now() - start_time).total_seconds() > time_budget_seconds:
                    break

                # Create and train model
                model = self.create_model(
                    name=f"auto_{model_type.value}_{lr}",
                    model_type=model_type,
                    task_type=task_type
                )

                config = TrainingConfig(
                    epochs=50,
                    learning_rate=lr,
                    early_stopping_patience=5,
                    verbose=False
                )

                try:
                    result = await self.train(model.id, dataset, config)

                    metric_value = result.final_metrics.get(metric, result.final_loss)

                    self.experiments.log_metric(f"{model_type.value}_{lr}_{metric}", metric_value)
                    self.experiments.add_model(model.id)

                    if metric_value < best_metric_value:
                        best_metric_value = metric_value
                        best_model = model

                except Exception as e:
                    logger.error(f"Training failed for {model_type.value}: {e}")

        self.experiments.complete()
        self._stats['experiments_run'] += 1

        if best_model:
            logger.info(f"Best model: {best_model.name} with {metric}={best_metric_value:.4f}")

        return best_model

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            **self._stats,
            'registered_models': len(self.registry.list()),
            'trained_models': len([m for m in self.registry.list() if m.is_trained]),
            'deployed_models': len(self.deployer.list_deployments()),
            'experiments': len(self.experiments.list())
        }

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'statistics': self.get_statistics(),
            'auto_ml_enabled': self.config.enable_auto_ml,
            'experiment_tracking_enabled': self.config.enable_experiment_tracking
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

ml_engine = MachineLearningEngine()
