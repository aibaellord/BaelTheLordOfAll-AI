#!/usr/bin/env python3
"""
BAEL - Model Version Registry
Comprehensive model versioning and registry management.

Features:
- Model registration
- Version control
- Model metadata
- Model lineage tracking
- Model staging
- Model deployment tracking
"""

import asyncio
import hashlib
import json
import os
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ModelStage(Enum):
    """Model deployment stage."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class ModelStatus(Enum):
    """Model status."""
    REGISTERED = "registered"
    VALIDATED = "validated"
    APPROVED = "approved"
    DEPLOYED = "deployed"
    DEPRECATED = "deprecated"


class ArtifactFormat(Enum):
    """Model artifact formats."""
    PICKLE = "pickle"
    JOBLIB = "joblib"
    ONNX = "onnx"
    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    SAFETENSORS = "safetensors"
    CUSTOM = "custom"


class TransitionAction(Enum):
    """Stage transition actions."""
    PROMOTE = "promote"
    DEMOTE = "demote"
    ARCHIVE = "archive"
    RESTORE = "restore"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ModelMetrics:
    """Model performance metrics."""
    metrics: Dict[str, float] = field(default_factory=dict)
    dataset: str = ""
    evaluated_at: datetime = field(default_factory=datetime.now)

    def add(self, name: str, value: float) -> None:
        """Add a metric."""
        self.metrics[name] = value

    def get(self, name: str, default: float = 0.0) -> float:
        """Get a metric value."""
        return self.metrics.get(name, default)


@dataclass
class ModelArtifact:
    """A model artifact."""
    artifact_id: str = ""
    path: str = ""
    format: ArtifactFormat = ArtifactFormat.CUSTOM
    size: int = 0
    checksum: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.artifact_id:
            self.artifact_id = str(uuid.uuid4())[:8]


@dataclass
class ModelVersion:
    """A specific model version."""
    version_id: str = ""
    version: str = "1.0.0"
    description: str = ""
    artifact: Optional[ModelArtifact] = None
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    metrics: Optional[ModelMetrics] = None
    stage: ModelStage = ModelStage.DEVELOPMENT
    status: ModelStatus = ModelStatus.REGISTERED
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    parent_version: Optional[str] = None
    run_id: Optional[str] = None

    def __post_init__(self):
        if not self.version_id:
            self.version_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version_id": self.version_id,
            "version": self.version,
            "description": self.description,
            "stage": self.stage.value,
            "status": self.status.value,
            "tags": self.tags,
            "hyperparameters": self.hyperparameters,
            "metrics": self.metrics.metrics if self.metrics else {},
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "parent_version": self.parent_version,
            "run_id": self.run_id
        }


@dataclass
class RegisteredModel:
    """A registered model with multiple versions."""
    model_id: str = ""
    name: str = ""
    description: str = ""
    versions: Dict[str, ModelVersion] = field(default_factory=dict)
    latest_version: Optional[str] = None
    production_version: Optional[str] = None
    staging_version: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    owners: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.model_id:
            self.model_id = str(uuid.uuid4())[:8]

    def add_version(self, version: ModelVersion) -> None:
        """Add a new version."""
        self.versions[version.version_id] = version
        self.latest_version = version.version_id
        self.updated_at = datetime.now()

        if version.stage == ModelStage.PRODUCTION:
            self.production_version = version.version_id
        elif version.stage == ModelStage.STAGING:
            self.staging_version = version.version_id

    def get_version(self, version_id: str) -> Optional[ModelVersion]:
        """Get a specific version."""
        return self.versions.get(version_id)

    def get_latest(self) -> Optional[ModelVersion]:
        """Get the latest version."""
        if self.latest_version:
            return self.versions.get(self.latest_version)
        return None

    def get_production(self) -> Optional[ModelVersion]:
        """Get the production version."""
        if self.production_version:
            return self.versions.get(self.production_version)
        return None

    def get_staging(self) -> Optional[ModelVersion]:
        """Get the staging version."""
        if self.staging_version:
            return self.versions.get(self.staging_version)
        return None

    def list_versions(
        self,
        stage: Optional[ModelStage] = None,
        status: Optional[ModelStatus] = None
    ) -> List[ModelVersion]:
        """List versions with optional filters."""
        versions = list(self.versions.values())

        if stage:
            versions = [v for v in versions if v.stage == stage]

        if status:
            versions = [v for v in versions if v.status == status]

        return sorted(versions, key=lambda v: v.created_at, reverse=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model_id": self.model_id,
            "name": self.name,
            "description": self.description,
            "n_versions": len(self.versions),
            "latest_version": self.latest_version,
            "production_version": self.production_version,
            "staging_version": self.staging_version,
            "tags": self.tags,
            "owners": self.owners,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class DeploymentRecord:
    """Record of a model deployment."""
    deployment_id: str = ""
    model_id: str = ""
    version_id: str = ""
    environment: str = ""
    endpoint: str = ""
    deployed_at: datetime = field(default_factory=datetime.now)
    deployed_by: str = ""
    status: str = "active"
    config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.deployment_id:
            self.deployment_id = str(uuid.uuid4())[:8]


@dataclass
class TransitionRecord:
    """Record of a stage transition."""
    record_id: str = ""
    model_id: str = ""
    version_id: str = ""
    from_stage: ModelStage = ModelStage.DEVELOPMENT
    to_stage: ModelStage = ModelStage.STAGING
    action: TransitionAction = TransitionAction.PROMOTE
    transitioned_at: datetime = field(default_factory=datetime.now)
    transitioned_by: str = ""
    comment: str = ""

    def __post_init__(self):
        if not self.record_id:
            self.record_id = str(uuid.uuid4())[:8]


@dataclass
class RegistryConfig:
    """Registry configuration."""
    base_dir: str = "./model_registry"
    auto_save: bool = True
    max_versions_per_model: int = 100
    require_approval: bool = False
    allowed_transitions: Dict[str, List[str]] = field(default_factory=dict)

    def __post_init__(self):
        if not self.allowed_transitions:
            self.allowed_transitions = {
                "development": ["staging", "archived"],
                "staging": ["production", "development", "archived"],
                "production": ["archived", "staging"],
                "archived": ["development"]
            }


# =============================================================================
# MODEL VERSION REGISTRY
# =============================================================================

class ModelVersionRegistry:
    """
    Model Version Registry for BAEL.

    Comprehensive model versioning and registry management.
    """

    def __init__(self, config: Optional[RegistryConfig] = None):
        self._config = config or RegistryConfig()
        self._models: Dict[str, RegisteredModel] = {}
        self._deployments: Dict[str, DeploymentRecord] = {}
        self._transitions: List[TransitionRecord] = []
        self._name_to_id: Dict[str, str] = {}

    def register_model(
        self,
        name: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        owners: Optional[List[str]] = None
    ) -> RegisteredModel:
        """Register a new model."""
        if name in self._name_to_id:
            return self._models[self._name_to_id[name]]

        model = RegisteredModel(
            name=name,
            description=description,
            tags=tags or [],
            owners=owners or []
        )

        self._models[model.model_id] = model
        self._name_to_id[name] = model.model_id

        return model

    def get_model(self, name_or_id: str) -> Optional[RegisteredModel]:
        """Get a model by name or ID."""
        if name_or_id in self._models:
            return self._models[name_or_id]

        if name_or_id in self._name_to_id:
            return self._models[self._name_to_id[name_or_id]]

        return None

    def log_model(
        self,
        model_name: str,
        version: str = "1.0.0",
        artifact_path: Optional[str] = None,
        artifact_format: ArtifactFormat = ArtifactFormat.CUSTOM,
        hyperparameters: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, float]] = None,
        description: str = "",
        tags: Optional[List[str]] = None,
        created_by: str = "",
        run_id: Optional[str] = None
    ) -> ModelVersion:
        """Log a new model version."""
        model = self.get_model(model_name)

        if not model:
            model = self.register_model(model_name)

        artifact = None
        if artifact_path:
            size = 0
            checksum = ""

            if os.path.exists(artifact_path):
                size = os.path.getsize(artifact_path)
                with open(artifact_path, "rb") as f:
                    checksum = hashlib.md5(f.read()).hexdigest()

            artifact = ModelArtifact(
                path=artifact_path,
                format=artifact_format,
                size=size,
                checksum=checksum
            )

        model_metrics = None
        if metrics:
            model_metrics = ModelMetrics(metrics=metrics)

        parent_version = model.latest_version

        model_version = ModelVersion(
            version=version,
            description=description,
            artifact=artifact,
            hyperparameters=hyperparameters or {},
            metrics=model_metrics,
            tags=tags or [],
            created_by=created_by,
            parent_version=parent_version,
            run_id=run_id
        )

        model.add_version(model_version)

        return model_version

    def transition_stage(
        self,
        model_name: str,
        version_id: str,
        stage: ModelStage,
        transitioned_by: str = "",
        comment: str = ""
    ) -> bool:
        """Transition a model version to a new stage."""
        model = self.get_model(model_name)

        if not model:
            return False

        version = model.get_version(version_id)

        if not version:
            return False

        old_stage = version.stage

        allowed = self._config.allowed_transitions.get(old_stage.value, [])
        if stage.value not in allowed:
            return False

        action = TransitionAction.PROMOTE
        if stage == ModelStage.ARCHIVED:
            action = TransitionAction.ARCHIVE
        elif old_stage == ModelStage.ARCHIVED:
            action = TransitionAction.RESTORE
        elif stage == ModelStage.DEVELOPMENT:
            action = TransitionAction.DEMOTE

        self._transitions.append(TransitionRecord(
            model_id=model.model_id,
            version_id=version_id,
            from_stage=old_stage,
            to_stage=stage,
            action=action,
            transitioned_by=transitioned_by,
            comment=comment
        ))

        version.stage = stage
        model.updated_at = datetime.now()

        if stage == ModelStage.PRODUCTION:
            if model.production_version and model.production_version != version_id:
                old_prod = model.get_version(model.production_version)
                if old_prod:
                    old_prod.stage = ModelStage.ARCHIVED
            model.production_version = version_id

        elif stage == ModelStage.STAGING:
            if model.staging_version and model.staging_version != version_id:
                old_staging = model.get_version(model.staging_version)
                if old_staging and old_staging.stage == ModelStage.STAGING:
                    old_staging.stage = ModelStage.DEVELOPMENT
            model.staging_version = version_id

        elif old_stage == ModelStage.PRODUCTION:
            model.production_version = None

        elif old_stage == ModelStage.STAGING:
            model.staging_version = None

        return True

    def update_status(
        self,
        model_name: str,
        version_id: str,
        status: ModelStatus
    ) -> bool:
        """Update version status."""
        model = self.get_model(model_name)

        if not model:
            return False

        version = model.get_version(version_id)

        if not version:
            return False

        version.status = status
        model.updated_at = datetime.now()

        return True

    def log_metrics(
        self,
        model_name: str,
        version_id: str,
        metrics: Dict[str, float],
        dataset: str = ""
    ) -> bool:
        """Log metrics for a version."""
        model = self.get_model(model_name)

        if not model:
            return False

        version = model.get_version(version_id)

        if not version:
            return False

        if version.metrics is None:
            version.metrics = ModelMetrics(dataset=dataset)

        for name, value in metrics.items():
            version.metrics.add(name, value)

        return True

    def record_deployment(
        self,
        model_name: str,
        version_id: str,
        environment: str,
        endpoint: str = "",
        deployed_by: str = "",
        config: Optional[Dict[str, Any]] = None
    ) -> DeploymentRecord:
        """Record a deployment."""
        model = self.get_model(model_name)

        if not model:
            raise ValueError(f"Model not found: {model_name}")

        version = model.get_version(version_id)

        if not version:
            raise ValueError(f"Version not found: {version_id}")

        record = DeploymentRecord(
            model_id=model.model_id,
            version_id=version_id,
            environment=environment,
            endpoint=endpoint,
            deployed_by=deployed_by,
            config=config or {}
        )

        self._deployments[record.deployment_id] = record

        version.status = ModelStatus.DEPLOYED

        return record

    def list_models(
        self,
        tags: Optional[List[str]] = None
    ) -> List[RegisteredModel]:
        """List all registered models."""
        models = list(self._models.values())

        if tags:
            tag_set = set(tags)
            models = [m for m in models if tag_set.issubset(set(m.tags))]

        return sorted(models, key=lambda m: m.updated_at, reverse=True)

    def search_models(
        self,
        query: str
    ) -> List[RegisteredModel]:
        """Search models by name or description."""
        query_lower = query.lower()

        results = []

        for model in self._models.values():
            if (query_lower in model.name.lower() or
                query_lower in model.description.lower()):
                results.append(model)

        return results

    def get_model_lineage(
        self,
        model_name: str,
        version_id: str
    ) -> List[ModelVersion]:
        """Get the lineage (ancestry) of a model version."""
        model = self.get_model(model_name)

        if not model:
            return []

        lineage = []
        current_id = version_id

        while current_id:
            version = model.get_version(current_id)
            if not version:
                break

            lineage.append(version)
            current_id = version.parent_version

        return lineage

    def get_transition_history(
        self,
        model_name: Optional[str] = None,
        version_id: Optional[str] = None
    ) -> List[TransitionRecord]:
        """Get transition history."""
        records = self._transitions

        if model_name:
            model = self.get_model(model_name)
            if model:
                records = [r for r in records if r.model_id == model.model_id]

        if version_id:
            records = [r for r in records if r.version_id == version_id]

        return sorted(records, key=lambda r: r.transitioned_at, reverse=True)

    def compare_versions(
        self,
        model_name: str,
        version_ids: List[str]
    ) -> Dict[str, Any]:
        """Compare multiple versions."""
        model = self.get_model(model_name)

        if not model:
            return {}

        comparison = {
            "versions": {},
            "metrics_comparison": {},
            "hyperparameter_diff": {}
        }

        for vid in version_ids:
            version = model.get_version(vid)
            if version:
                comparison["versions"][vid] = {
                    "version": version.version,
                    "stage": version.stage.value,
                    "status": version.status.value,
                    "created_at": version.created_at.isoformat()
                }

                if version.metrics:
                    comparison["metrics_comparison"][vid] = version.metrics.metrics

                comparison["hyperparameter_diff"][vid] = version.hyperparameters

        return comparison

    def get_best_version(
        self,
        model_name: str,
        metric_name: str,
        higher_is_better: bool = True
    ) -> Optional[ModelVersion]:
        """Get the best version by metric."""
        model = self.get_model(model_name)

        if not model:
            return None

        best_version = None
        best_value = None

        for version in model.versions.values():
            if not version.metrics:
                continue

            value = version.metrics.get(metric_name)

            if value is None:
                continue

            if best_value is None:
                best_value = value
                best_version = version
            elif higher_is_better and value > best_value:
                best_value = value
                best_version = version
            elif not higher_is_better and value < best_value:
                best_value = value
                best_version = version

        return best_version

    def delete_version(
        self,
        model_name: str,
        version_id: str
    ) -> bool:
        """Delete a model version."""
        model = self.get_model(model_name)

        if not model:
            return False

        if version_id not in model.versions:
            return False

        version = model.versions[version_id]

        if version.stage == ModelStage.PRODUCTION:
            return False

        del model.versions[version_id]

        if model.latest_version == version_id:
            versions = list(model.versions.values())
            if versions:
                model.latest_version = sorted(
                    versions, key=lambda v: v.created_at, reverse=True
                )[0].version_id
            else:
                model.latest_version = None

        if model.staging_version == version_id:
            model.staging_version = None

        return True

    def summary(self) -> Dict[str, Any]:
        """Get registry summary."""
        all_versions = []

        for model in self._models.values():
            all_versions.extend(model.versions.values())

        return {
            "total_models": len(self._models),
            "total_versions": len(all_versions),
            "total_deployments": len(self._deployments),
            "total_transitions": len(self._transitions),
            "versions_by_stage": {
                stage.value: sum(1 for v in all_versions if v.stage == stage)
                for stage in ModelStage
            },
            "versions_by_status": {
                status.value: sum(1 for v in all_versions if v.status == status)
                for status in ModelStatus
            }
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Model Version Registry."""
    print("=" * 70)
    print("BAEL - MODEL VERSION REGISTRY DEMO")
    print("Model Versioning and Registry Management")
    print("=" * 70)
    print()

    registry = ModelVersionRegistry()

    # 1. Register Model
    print("1. REGISTER MODEL:")
    print("-" * 40)

    model = registry.register_model(
        name="bael-classifier",
        description="BAEL's main classification model",
        tags=["classification", "nlp"],
        owners=["bael-team"]
    )

    print(f"   Model ID: {model.model_id}")
    print(f"   Name: {model.name}")
    print(f"   Tags: {model.tags}")
    print()

    # 2. Log Model Versions
    print("2. LOG MODEL VERSIONS:")
    print("-" * 40)

    v1 = registry.log_model(
        model_name="bael-classifier",
        version="1.0.0",
        hyperparameters={"learning_rate": 0.001, "hidden_units": 256},
        metrics={"accuracy": 0.85, "f1_score": 0.82},
        description="Initial baseline model",
        created_by="researcher-1"
    )

    print(f"   Version 1: {v1.version} ({v1.version_id})")

    v2 = registry.log_model(
        model_name="bael-classifier",
        version="1.1.0",
        hyperparameters={"learning_rate": 0.0005, "hidden_units": 512},
        metrics={"accuracy": 0.88, "f1_score": 0.86},
        description="Improved model with larger hidden layer",
        created_by="researcher-1"
    )

    print(f"   Version 2: {v2.version} ({v2.version_id})")

    v3 = registry.log_model(
        model_name="bael-classifier",
        version="1.2.0",
        hyperparameters={"learning_rate": 0.0003, "hidden_units": 512, "dropout": 0.3},
        metrics={"accuracy": 0.91, "f1_score": 0.89},
        description="Added dropout for regularization",
        created_by="researcher-2"
    )

    print(f"   Version 3: {v3.version} ({v3.version_id})")
    print()

    # 3. Transition Stages
    print("3. TRANSITION STAGES:")
    print("-" * 40)

    registry.transition_stage("bael-classifier", v2.version_id, ModelStage.STAGING, "ops-1")
    print(f"   {v2.version}: → STAGING")

    registry.transition_stage("bael-classifier", v3.version_id, ModelStage.STAGING, "ops-1")
    registry.transition_stage("bael-classifier", v3.version_id, ModelStage.PRODUCTION, "ops-1")
    print(f"   {v3.version}: → PRODUCTION")

    model = registry.get_model("bael-classifier")
    print(f"   Production version: {model.production_version}")
    print()

    # 4. Transition History
    print("4. TRANSITION HISTORY:")
    print("-" * 40)

    history = registry.get_transition_history("bael-classifier")

    for record in history[:5]:
        print(f"   {record.from_stage.value} → {record.to_stage.value} ({record.action.value})")
    print()

    # 5. Get Best Version
    print("5. GET BEST VERSION:")
    print("-" * 40)

    best = registry.get_best_version("bael-classifier", "accuracy", higher_is_better=True)

    if best:
        print(f"   Best by accuracy: {best.version} (acc={best.metrics.get('accuracy'):.2f})")
    print()

    # 6. Model Lineage
    print("6. MODEL LINEAGE:")
    print("-" * 40)

    lineage = registry.get_model_lineage("bael-classifier", v3.version_id)

    for i, v in enumerate(lineage):
        print(f"   {i}: {v.version} ({v.version_id})")
    print()

    # 7. Compare Versions
    print("7. COMPARE VERSIONS:")
    print("-" * 40)

    comparison = registry.compare_versions(
        "bael-classifier",
        [v1.version_id, v2.version_id, v3.version_id]
    )

    print("   Metrics:")
    for vid, metrics in comparison["metrics_comparison"].items():
        print(f"      {vid}: acc={metrics.get('accuracy', 0):.2f}")
    print()

    # 8. Record Deployment
    print("8. RECORD DEPLOYMENT:")
    print("-" * 40)

    deployment = registry.record_deployment(
        model_name="bael-classifier",
        version_id=v3.version_id,
        environment="production",
        endpoint="https://api.bael.ai/classify",
        deployed_by="devops-1"
    )

    print(f"   Deployment ID: {deployment.deployment_id}")
    print(f"   Environment: {deployment.environment}")
    print()

    # 9. Registry Summary
    print("9. REGISTRY SUMMARY:")
    print("-" * 40)

    summary = registry.summary()

    print(f"   Total models: {summary['total_models']}")
    print(f"   Total versions: {summary['total_versions']}")
    print(f"   Total transitions: {summary['total_transitions']}")
    print(f"   In production: {summary['versions_by_stage']['production']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Model Version Registry Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
