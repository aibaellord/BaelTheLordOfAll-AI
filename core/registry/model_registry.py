#!/usr/bin/env python3
"""
BAEL - Model Registry
Advanced model management for AI agent ML operations.

Features:
- Model versioning and lineage
- Model artifacts storage
- Model metadata management
- A/B testing support
- Model staging (dev/staging/prod)
- Deployment tracking
- Model comparison
- Experiment tracking
"""

import asyncio
import copy
import hashlib
import json
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ModelStage(Enum):
    """Model deployment stages."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class ModelStatus(Enum):
    """Model status."""
    REGISTERED = "registered"
    TRAINING = "training"
    VALIDATED = "validated"
    DEPLOYED = "deployed"
    RETIRED = "retired"


class ArtifactType(Enum):
    """Model artifact types."""
    WEIGHTS = "weights"
    CONFIG = "config"
    TOKENIZER = "tokenizer"
    PREPROCESSOR = "preprocessor"
    METADATA = "metadata"
    CHECKPOINT = "checkpoint"


class MetricType(Enum):
    """Metric types."""
    ACCURACY = "accuracy"
    LOSS = "loss"
    F1 = "f1"
    PRECISION = "precision"
    RECALL = "recall"
    AUC = "auc"
    MSE = "mse"
    MAE = "mae"
    LATENCY = "latency"
    THROUGHPUT = "throughput"


class ExperimentStatus(Enum):
    """Experiment status."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ModelArtifact:
    """Model artifact."""
    artifact_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    artifact_type: ArtifactType = ArtifactType.WEIGHTS
    path: str = ""
    size_bytes: int = 0
    hash: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelMetrics:
    """Model performance metrics."""
    metrics: Dict[str, float] = field(default_factory=dict)
    dataset: str = ""
    evaluated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ModelVersion:
    """Model version."""
    version: int
    model_name: str
    description: str = ""
    status: ModelStatus = ModelStatus.REGISTERED
    stage: ModelStage = ModelStage.DEVELOPMENT
    artifacts: List[ModelArtifact] = field(default_factory=list)
    metrics: List[ModelMetrics] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    parent_version: Optional[int] = None


@dataclass
class RegisteredModel:
    """Registered model with versions."""
    name: str
    description: str = ""
    versions: Dict[int, ModelVersion] = field(default_factory=dict)
    latest_version: int = 0
    tags: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    owner: str = ""


@dataclass
class Experiment:
    """ML experiment."""
    experiment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    status: ExperimentStatus = ExperimentStatus.RUNNING
    params: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    model_version: Optional[Tuple[str, int]] = None
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Deployment:
    """Model deployment."""
    deployment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_name: str = ""
    version: int = 0
    environment: str = ""
    endpoint: str = ""
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.now)
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ABTest:
    """A/B test configuration."""
    test_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    model_a: Tuple[str, int] = ("", 0)
    model_b: Tuple[str, int] = ("", 0)
    traffic_split: float = 0.5
    status: str = "active"
    metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None


# =============================================================================
# MODEL STORE
# =============================================================================

class ModelStore:
    """In-memory model store."""

    def __init__(self):
        self._models: Dict[str, RegisteredModel] = {}

    def register(
        self,
        name: str,
        description: str = "",
        owner: str = ""
    ) -> RegisteredModel:
        """Register new model."""
        if name in self._models:
            return self._models[name]

        model = RegisteredModel(
            name=name,
            description=description,
            owner=owner
        )

        self._models[name] = model
        return model

    def get(self, name: str) -> Optional[RegisteredModel]:
        """Get registered model."""
        return self._models.get(name)

    def list_models(self) -> List[str]:
        """List model names."""
        return list(self._models.keys())

    def delete(self, name: str) -> bool:
        """Delete model."""
        if name in self._models:
            del self._models[name]
            return True
        return False

    def add_version(
        self,
        model_name: str,
        description: str = "",
        created_by: str = ""
    ) -> Optional[ModelVersion]:
        """Add new version."""
        model = self._models.get(model_name)
        if not model:
            return None

        version_num = model.latest_version + 1

        version = ModelVersion(
            version=version_num,
            model_name=model_name,
            description=description,
            created_by=created_by,
            parent_version=model.latest_version if model.latest_version > 0 else None
        )

        model.versions[version_num] = version
        model.latest_version = version_num
        model.updated_at = datetime.now()

        return version

    def get_version(
        self,
        model_name: str,
        version: int
    ) -> Optional[ModelVersion]:
        """Get specific version."""
        model = self._models.get(model_name)
        if model:
            return model.versions.get(version)
        return None

    def get_latest_version(self, model_name: str) -> Optional[ModelVersion]:
        """Get latest version."""
        model = self._models.get(model_name)
        if model and model.latest_version > 0:
            return model.versions.get(model.latest_version)
        return None

    def list_versions(self, model_name: str) -> List[int]:
        """List version numbers."""
        model = self._models.get(model_name)
        if model:
            return sorted(model.versions.keys())
        return []


# =============================================================================
# EXPERIMENT TRACKER
# =============================================================================

class ExperimentTracker:
    """Track ML experiments."""

    def __init__(self):
        self._experiments: Dict[str, Experiment] = {}
        self._by_model: Dict[str, List[str]] = defaultdict(list)

    def create(
        self,
        name: str,
        description: str = "",
        params: Optional[Dict[str, Any]] = None
    ) -> Experiment:
        """Create experiment."""
        exp = Experiment(
            name=name,
            description=description,
            params=params or {}
        )

        self._experiments[exp.experiment_id] = exp
        return exp

    def get(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment."""
        return self._experiments.get(experiment_id)

    def log_metric(
        self,
        experiment_id: str,
        name: str,
        value: float
    ) -> bool:
        """Log metric."""
        exp = self._experiments.get(experiment_id)
        if exp:
            exp.metrics[name] = value
            return True
        return False

    def log_param(
        self,
        experiment_id: str,
        name: str,
        value: Any
    ) -> bool:
        """Log parameter."""
        exp = self._experiments.get(experiment_id)
        if exp:
            exp.params[name] = value
            return True
        return False

    def set_model(
        self,
        experiment_id: str,
        model_name: str,
        version: int
    ) -> bool:
        """Associate model with experiment."""
        exp = self._experiments.get(experiment_id)
        if exp:
            exp.model_version = (model_name, version)
            self._by_model[model_name].append(experiment_id)
            return True
        return False

    def complete(
        self,
        experiment_id: str,
        status: ExperimentStatus = ExperimentStatus.COMPLETED
    ) -> bool:
        """Complete experiment."""
        exp = self._experiments.get(experiment_id)
        if exp:
            exp.status = status
            exp.ended_at = datetime.now()
            return True
        return False

    def list_experiments(
        self,
        model_name: Optional[str] = None
    ) -> List[Experiment]:
        """List experiments."""
        if model_name:
            exp_ids = self._by_model.get(model_name, [])
            return [
                self._experiments[eid]
                for eid in exp_ids
                if eid in self._experiments
            ]
        return list(self._experiments.values())


# =============================================================================
# DEPLOYMENT MANAGER
# =============================================================================

class DeploymentManager:
    """Manage model deployments."""

    def __init__(self):
        self._deployments: Dict[str, Deployment] = {}
        self._by_model: Dict[str, List[str]] = defaultdict(list)
        self._by_environment: Dict[str, List[str]] = defaultdict(list)

    def deploy(
        self,
        model_name: str,
        version: int,
        environment: str,
        endpoint: str = "",
        config: Optional[Dict[str, Any]] = None
    ) -> Deployment:
        """Deploy model."""
        deployment = Deployment(
            model_name=model_name,
            version=version,
            environment=environment,
            endpoint=endpoint or f"/{model_name}/v{version}",
            config=config or {}
        )

        self._deployments[deployment.deployment_id] = deployment
        self._by_model[model_name].append(deployment.deployment_id)
        self._by_environment[environment].append(deployment.deployment_id)

        return deployment

    def get(self, deployment_id: str) -> Optional[Deployment]:
        """Get deployment."""
        return self._deployments.get(deployment_id)

    def list_deployments(
        self,
        model_name: Optional[str] = None,
        environment: Optional[str] = None
    ) -> List[Deployment]:
        """List deployments."""
        if model_name:
            dep_ids = self._by_model.get(model_name, [])
        elif environment:
            dep_ids = self._by_environment.get(environment, [])
        else:
            dep_ids = list(self._deployments.keys())

        return [
            self._deployments[did]
            for did in dep_ids
            if did in self._deployments
        ]

    def undeploy(self, deployment_id: str) -> bool:
        """Undeploy model."""
        dep = self._deployments.get(deployment_id)
        if dep:
            dep.status = "inactive"
            return True
        return False

    def get_active_deployment(
        self,
        model_name: str,
        environment: str
    ) -> Optional[Deployment]:
        """Get active deployment for model in environment."""
        deployments = self.list_deployments(model_name=model_name)

        for dep in deployments:
            if dep.environment == environment and dep.status == "active":
                return dep

        return None


# =============================================================================
# AB TEST MANAGER
# =============================================================================

class ABTestManager:
    """Manage A/B tests."""

    def __init__(self):
        self._tests: Dict[str, ABTest] = {}

    def create(
        self,
        name: str,
        model_a: Tuple[str, int],
        model_b: Tuple[str, int],
        traffic_split: float = 0.5
    ) -> ABTest:
        """Create A/B test."""
        test = ABTest(
            name=name,
            model_a=model_a,
            model_b=model_b,
            traffic_split=traffic_split
        )

        self._tests[test.test_id] = test
        return test

    def get(self, test_id: str) -> Optional[ABTest]:
        """Get A/B test."""
        return self._tests.get(test_id)

    def log_metrics(
        self,
        test_id: str,
        model: str,  # "a" or "b"
        metrics: Dict[str, float]
    ) -> bool:
        """Log metrics for model in test."""
        test = self._tests.get(test_id)
        if test:
            if model not in test.metrics:
                test.metrics[model] = {}
            test.metrics[model].update(metrics)
            return True
        return False

    def select_model(self, test_id: str) -> Optional[Tuple[str, int]]:
        """Select model based on traffic split."""
        import random

        test = self._tests.get(test_id)
        if not test:
            return None

        if random.random() < test.traffic_split:
            return test.model_a
        else:
            return test.model_b

    def end_test(
        self,
        test_id: str,
        winner: Optional[str] = None
    ) -> bool:
        """End A/B test."""
        test = self._tests.get(test_id)
        if test:
            test.status = "completed"
            test.ended_at = datetime.now()
            if winner:
                test.metrics["winner"] = {"model": winner}
            return True
        return False

    def list_tests(
        self,
        status: Optional[str] = None
    ) -> List[ABTest]:
        """List A/B tests."""
        tests = list(self._tests.values())
        if status:
            tests = [t for t in tests if t.status == status]
        return tests


# =============================================================================
# MODEL REGISTRY MANAGER
# =============================================================================

class ModelRegistryManager:
    """
    Model Registry Manager for BAEL.

    Advanced model management for ML operations.
    """

    def __init__(self):
        self._store = ModelStore()
        self._experiments = ExperimentTracker()
        self._deployments = DeploymentManager()
        self._ab_tests = ABTestManager()

    # -------------------------------------------------------------------------
    # MODEL REGISTRATION
    # -------------------------------------------------------------------------

    def register_model(
        self,
        name: str,
        description: str = "",
        owner: str = ""
    ) -> RegisteredModel:
        """Register a new model."""
        return self._store.register(name, description, owner)

    def get_model(self, name: str) -> Optional[RegisteredModel]:
        """Get registered model."""
        return self._store.get(name)

    def list_models(self) -> List[str]:
        """List all registered models."""
        return self._store.list_models()

    def delete_model(self, name: str) -> bool:
        """Delete model."""
        return self._store.delete(name)

    # -------------------------------------------------------------------------
    # VERSION MANAGEMENT
    # -------------------------------------------------------------------------

    def create_version(
        self,
        model_name: str,
        description: str = "",
        created_by: str = ""
    ) -> Optional[ModelVersion]:
        """Create new model version."""
        return self._store.add_version(model_name, description, created_by)

    def get_version(
        self,
        model_name: str,
        version: int
    ) -> Optional[ModelVersion]:
        """Get model version."""
        return self._store.get_version(model_name, version)

    def get_latest_version(self, model_name: str) -> Optional[ModelVersion]:
        """Get latest version."""
        return self._store.get_latest_version(model_name)

    def list_versions(self, model_name: str) -> List[int]:
        """List versions."""
        return self._store.list_versions(model_name)

    # -------------------------------------------------------------------------
    # ARTIFACTS
    # -------------------------------------------------------------------------

    def add_artifact(
        self,
        model_name: str,
        version: int,
        artifact_type: ArtifactType,
        path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add artifact to version."""
        mv = self._store.get_version(model_name, version)
        if mv:
            artifact = ModelArtifact(
                artifact_type=artifact_type,
                path=path,
                metadata=metadata or {}
            )
            mv.artifacts.append(artifact)
            mv.updated_at = datetime.now()
            return True
        return False

    def get_artifacts(
        self,
        model_name: str,
        version: int
    ) -> List[ModelArtifact]:
        """Get version artifacts."""
        mv = self._store.get_version(model_name, version)
        return mv.artifacts if mv else []

    # -------------------------------------------------------------------------
    # METRICS
    # -------------------------------------------------------------------------

    def log_metrics(
        self,
        model_name: str,
        version: int,
        metrics: Dict[str, float],
        dataset: str = ""
    ) -> bool:
        """Log model metrics."""
        mv = self._store.get_version(model_name, version)
        if mv:
            m = ModelMetrics(
                metrics=metrics,
                dataset=dataset
            )
            mv.metrics.append(m)
            mv.updated_at = datetime.now()
            return True
        return False

    def get_metrics(
        self,
        model_name: str,
        version: int
    ) -> List[ModelMetrics]:
        """Get version metrics."""
        mv = self._store.get_version(model_name, version)
        return mv.metrics if mv else []

    # -------------------------------------------------------------------------
    # STAGING
    # -------------------------------------------------------------------------

    def transition_stage(
        self,
        model_name: str,
        version: int,
        stage: ModelStage
    ) -> bool:
        """Transition model to stage."""
        mv = self._store.get_version(model_name, version)
        if mv:
            mv.stage = stage
            mv.updated_at = datetime.now()
            return True
        return False

    def get_by_stage(
        self,
        model_name: str,
        stage: ModelStage
    ) -> List[ModelVersion]:
        """Get versions in stage."""
        model = self._store.get(model_name)
        if not model:
            return []

        return [
            v for v in model.versions.values()
            if v.stage == stage
        ]

    def promote_to_production(
        self,
        model_name: str,
        version: int
    ) -> bool:
        """Promote version to production."""
        return self.transition_stage(model_name, version, ModelStage.PRODUCTION)

    # -------------------------------------------------------------------------
    # EXPERIMENTS
    # -------------------------------------------------------------------------

    def create_experiment(
        self,
        name: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Experiment:
        """Create experiment."""
        return self._experiments.create(name, "", params)

    def log_experiment_metric(
        self,
        experiment_id: str,
        name: str,
        value: float
    ) -> bool:
        """Log experiment metric."""
        return self._experiments.log_metric(experiment_id, name, value)

    def associate_experiment(
        self,
        experiment_id: str,
        model_name: str,
        version: int
    ) -> bool:
        """Associate experiment with model."""
        return self._experiments.set_model(experiment_id, model_name, version)

    def complete_experiment(
        self,
        experiment_id: str
    ) -> bool:
        """Complete experiment."""
        return self._experiments.complete(experiment_id)

    def list_experiments(
        self,
        model_name: Optional[str] = None
    ) -> List[Experiment]:
        """List experiments."""
        return self._experiments.list_experiments(model_name)

    # -------------------------------------------------------------------------
    # DEPLOYMENTS
    # -------------------------------------------------------------------------

    def deploy(
        self,
        model_name: str,
        version: int,
        environment: str
    ) -> Deployment:
        """Deploy model."""
        return self._deployments.deploy(model_name, version, environment)

    def list_deployments(
        self,
        model_name: Optional[str] = None
    ) -> List[Deployment]:
        """List deployments."""
        return self._deployments.list_deployments(model_name)

    def undeploy(self, deployment_id: str) -> bool:
        """Undeploy model."""
        return self._deployments.undeploy(deployment_id)

    # -------------------------------------------------------------------------
    # A/B TESTING
    # -------------------------------------------------------------------------

    def create_ab_test(
        self,
        name: str,
        model_a: Tuple[str, int],
        model_b: Tuple[str, int],
        traffic_split: float = 0.5
    ) -> ABTest:
        """Create A/B test."""
        return self._ab_tests.create(name, model_a, model_b, traffic_split)

    def select_ab_model(self, test_id: str) -> Optional[Tuple[str, int]]:
        """Select model from A/B test."""
        return self._ab_tests.select_model(test_id)

    def end_ab_test(
        self,
        test_id: str,
        winner: Optional[str] = None
    ) -> bool:
        """End A/B test."""
        return self._ab_tests.end_test(test_id, winner)

    def list_ab_tests(self) -> List[ABTest]:
        """List A/B tests."""
        return self._ab_tests.list_tests()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Model Registry."""
    print("=" * 70)
    print("BAEL - MODEL REGISTRY DEMO")
    print("Advanced Model Management for AI Agents")
    print("=" * 70)
    print()

    registry = ModelRegistryManager()

    # 1. Register Model
    print("1. REGISTER MODEL:")
    print("-" * 40)

    model = registry.register_model(
        "text-classifier",
        description="Text classification model",
        owner="ml-team"
    )

    print(f"   Registered: {model.name}")
    print(f"   Owner: {model.owner}")
    print()

    # 2. Create Version
    print("2. CREATE VERSION:")
    print("-" * 40)

    v1 = registry.create_version(
        "text-classifier",
        description="Initial version",
        created_by="alice"
    )

    print(f"   Version: {v1.version}")
    print(f"   Stage: {v1.stage.value}")
    print()

    # 3. Add Artifacts
    print("3. ADD ARTIFACTS:")
    print("-" * 40)

    registry.add_artifact(
        "text-classifier", 1,
        ArtifactType.WEIGHTS,
        "/models/text-classifier/v1/weights.pt",
        {"format": "pytorch"}
    )

    registry.add_artifact(
        "text-classifier", 1,
        ArtifactType.CONFIG,
        "/models/text-classifier/v1/config.json"
    )

    artifacts = registry.get_artifacts("text-classifier", 1)
    print(f"   Artifacts: {len(artifacts)}")
    for a in artifacts:
        print(f"   - {a.artifact_type.value}: {a.path}")
    print()

    # 4. Log Metrics
    print("4. LOG METRICS:")
    print("-" * 40)

    registry.log_metrics(
        "text-classifier", 1,
        {"accuracy": 0.92, "f1": 0.89, "latency_ms": 45},
        dataset="test-set"
    )

    metrics = registry.get_metrics("text-classifier", 1)
    for m in metrics:
        print(f"   Dataset: {m.dataset}")
        for name, value in m.metrics.items():
            print(f"   - {name}: {value}")
    print()

    # 5. Stage Transition
    print("5. STAGE TRANSITION:")
    print("-" * 40)

    registry.transition_stage("text-classifier", 1, ModelStage.STAGING)
    v1 = registry.get_version("text-classifier", 1)
    print(f"   Current stage: {v1.stage.value}")

    registry.promote_to_production("text-classifier", 1)
    v1 = registry.get_version("text-classifier", 1)
    print(f"   After promotion: {v1.stage.value}")
    print()

    # 6. Create More Versions
    print("6. MULTIPLE VERSIONS:")
    print("-" * 40)

    v2 = registry.create_version("text-classifier", "Improved accuracy")
    v3 = registry.create_version("text-classifier", "Added multilingual")

    versions = registry.list_versions("text-classifier")
    print(f"   Versions: {versions}")
    print()

    # 7. Experiments
    print("7. EXPERIMENT TRACKING:")
    print("-" * 40)

    exp = registry.create_experiment(
        "hyperparameter-search",
        {"learning_rate": 0.001, "batch_size": 32}
    )

    registry.log_experiment_metric(exp.experiment_id, "accuracy", 0.94)
    registry.log_experiment_metric(exp.experiment_id, "loss", 0.15)
    registry.associate_experiment(exp.experiment_id, "text-classifier", 2)
    registry.complete_experiment(exp.experiment_id)

    experiments = registry.list_experiments("text-classifier")
    print(f"   Experiments: {len(experiments)}")
    for e in experiments:
        print(f"   - {e.name}: {e.status.value}")
    print()

    # 8. Deployment
    print("8. DEPLOYMENT:")
    print("-" * 40)

    dep = registry.deploy("text-classifier", 1, "production")

    print(f"   Deployed: {dep.model_name} v{dep.version}")
    print(f"   Environment: {dep.environment}")
    print(f"   Endpoint: {dep.endpoint}")
    print()

    # 9. A/B Testing
    print("9. A/B TESTING:")
    print("-" * 40)

    test = registry.create_ab_test(
        "classifier-ab-test",
        ("text-classifier", 1),
        ("text-classifier", 2),
        traffic_split=0.7
    )

    print(f"   Test: {test.name}")
    print(f"   Model A: v{test.model_a[1]}")
    print(f"   Model B: v{test.model_b[1]}")
    print(f"   Split: {test.traffic_split:.0%} / {1-test.traffic_split:.0%}")

    # Simulate selections
    selections = {"a": 0, "b": 0}
    for _ in range(100):
        selected = registry.select_ab_model(test.test_id)
        if selected == test.model_a:
            selections["a"] += 1
        else:
            selections["b"] += 1

    print(f"   100 selections: A={selections['a']}, B={selections['b']}")
    print()

    # 10. List Models
    print("10. LIST MODELS:")
    print("-" * 40)

    models = registry.list_models()
    print(f"   Models: {models}")
    print()

    # 11. Get Latest Version
    print("11. LATEST VERSION:")
    print("-" * 40)

    latest = registry.get_latest_version("text-classifier")
    if latest:
        print(f"   Latest: v{latest.version}")
        print(f"   Description: {latest.description}")
    print()

    # 12. Get by Stage
    print("12. GET BY STAGE:")
    print("-" * 40)

    prod_versions = registry.get_by_stage("text-classifier", ModelStage.PRODUCTION)
    print(f"   Production versions: {[v.version for v in prod_versions]}")
    print()

    # 13. List Deployments
    print("13. LIST DEPLOYMENTS:")
    print("-" * 40)

    deployments = registry.list_deployments("text-classifier")
    for d in deployments:
        print(f"   - v{d.version} -> {d.environment} ({d.status})")
    print()

    # 14. End A/B Test
    print("14. END A/B TEST:")
    print("-" * 40)

    registry.end_ab_test(test.test_id, winner="a")
    tests = registry.list_ab_tests()

    for t in tests:
        print(f"   - {t.name}: {t.status}")
    print()

    # 15. Model Info
    print("15. MODEL INFO:")
    print("-" * 40)

    model = registry.get_model("text-classifier")
    if model:
        print(f"   Name: {model.name}")
        print(f"   Versions: {model.latest_version}")
        print(f"   Created: {model.created_at.strftime('%Y-%m-%d')}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Model Registry Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
