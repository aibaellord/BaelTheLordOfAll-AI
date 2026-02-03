#!/usr/bin/env python3
"""
BAEL - Experiment Tracker
Comprehensive experiment tracking for ML research.

Features:
- Experiment logging
- Hyperparameter tracking
- Metrics tracking
- Artifact management
- Comparison and analysis
- Reproducibility
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

class ExperimentStatus(Enum):
    """Experiment status."""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class MetricDirection(Enum):
    """Metric optimization direction."""
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


class ArtifactType(Enum):
    """Artifact types."""
    MODEL = "model"
    DATA = "data"
    CONFIG = "config"
    LOG = "log"
    PLOT = "plot"
    CODE = "code"
    OTHER = "other"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Hyperparameter:
    """A hyperparameter."""
    name: str = ""
    value: Any = None
    dtype: str = ""
    description: str = ""

    def __post_init__(self):
        if not self.dtype:
            self.dtype = type(self.value).__name__


@dataclass
class MetricValue:
    """A metric value at a step."""
    value: float = 0.0
    step: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Metric:
    """A tracked metric."""
    name: str = ""
    direction: MetricDirection = MetricDirection.MINIMIZE
    values: List[MetricValue] = field(default_factory=list)
    best_value: Optional[float] = None
    best_step: Optional[int] = None

    def add(self, value: float, step: int) -> None:
        """Add a value."""
        self.values.append(MetricValue(value=value, step=step))

        if self.best_value is None:
            self.best_value = value
            self.best_step = step
        elif self.direction == MetricDirection.MINIMIZE:
            if value < self.best_value:
                self.best_value = value
                self.best_step = step
        else:
            if value > self.best_value:
                self.best_value = value
                self.best_step = step


@dataclass
class Artifact:
    """An experiment artifact."""
    name: str = ""
    artifact_type: ArtifactType = ArtifactType.OTHER
    path: str = ""
    size: int = 0
    checksum: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ExperimentConfig:
    """Experiment configuration."""
    name: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    project: str = "default"
    base_dir: str = "./experiments"
    auto_save: bool = True
    save_interval: int = 100


@dataclass
class Experiment:
    """An experiment."""
    experiment_id: str = ""
    config: ExperimentConfig = field(default_factory=ExperimentConfig)
    status: ExperimentStatus = ExperimentStatus.CREATED
    hyperparameters: Dict[str, Hyperparameter] = field(default_factory=dict)
    metrics: Dict[str, Metric] = field(default_factory=dict)
    artifacts: Dict[str, Artifact] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration: float = 0.0
    current_step: int = 0

    def __post_init__(self):
        if not self.experiment_id:
            self.experiment_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "experiment_id": self.experiment_id,
            "name": self.config.name,
            "description": self.config.description,
            "project": self.config.project,
            "tags": self.config.tags,
            "status": self.status.value,
            "hyperparameters": {
                k: {"name": v.name, "value": v.value, "dtype": v.dtype}
                for k, v in self.hyperparameters.items()
            },
            "metrics_summary": {
                k: {"best": v.best_value, "best_step": v.best_step, "n_values": len(v.values)}
                for k, v in self.metrics.items()
            },
            "artifacts": list(self.artifacts.keys()),
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration": self.duration,
            "current_step": self.current_step
        }


@dataclass
class ComparisonResult:
    """Result of experiment comparison."""
    experiments: List[str] = field(default_factory=list)
    metrics_comparison: Dict[str, Dict[str, float]] = field(default_factory=dict)
    hyperparameter_diff: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    best_experiment: Optional[str] = None
    best_metric: Optional[str] = None


# =============================================================================
# EXPERIMENT RUN
# =============================================================================

class ExperimentRun:
    """Active experiment run."""

    def __init__(self, experiment: Experiment):
        self._experiment = experiment
        self._start_time: Optional[float] = None

    def start(self) -> None:
        """Start the run."""
        self._experiment.status = ExperimentStatus.RUNNING
        self._experiment.started_at = datetime.now()
        self._start_time = time.time()

    def end(self, status: ExperimentStatus = ExperimentStatus.COMPLETED) -> None:
        """End the run."""
        self._experiment.status = status
        self._experiment.ended_at = datetime.now()

        if self._start_time:
            self._experiment.duration = time.time() - self._start_time

    def log_param(self, name: str, value: Any, description: str = "") -> None:
        """Log a hyperparameter."""
        self._experiment.hyperparameters[name] = Hyperparameter(
            name=name,
            value=value,
            description=description
        )

    def log_params(self, params: Dict[str, Any]) -> None:
        """Log multiple hyperparameters."""
        for name, value in params.items():
            self.log_param(name, value)

    def log_metric(
        self,
        name: str,
        value: float,
        step: Optional[int] = None,
        direction: MetricDirection = MetricDirection.MINIMIZE
    ) -> None:
        """Log a metric."""
        if step is None:
            step = self._experiment.current_step

        if name not in self._experiment.metrics:
            self._experiment.metrics[name] = Metric(name=name, direction=direction)

        self._experiment.metrics[name].add(value, step)

    def log_metrics(
        self,
        metrics: Dict[str, float],
        step: Optional[int] = None
    ) -> None:
        """Log multiple metrics."""
        for name, value in metrics.items():
            self.log_metric(name, value, step)

    def log_artifact(
        self,
        name: str,
        path: str,
        artifact_type: ArtifactType = ArtifactType.OTHER,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an artifact."""
        size = 0
        checksum = ""

        if os.path.exists(path):
            size = os.path.getsize(path)
            with open(path, "rb") as f:
                checksum = hashlib.md5(f.read()).hexdigest()

        self._experiment.artifacts[name] = Artifact(
            name=name,
            artifact_type=artifact_type,
            path=path,
            size=size,
            checksum=checksum,
            metadata=metadata or {}
        )

    def log_note(self, note: str) -> None:
        """Log a note."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._experiment.notes.append(f"[{timestamp}] {note}")

    def step(self, step: Optional[int] = None) -> None:
        """Advance or set step."""
        if step is not None:
            self._experiment.current_step = step
        else:
            self._experiment.current_step += 1

    def get_experiment(self) -> Experiment:
        """Get the experiment."""
        return self._experiment

    def get_best_metric(self, name: str) -> Optional[float]:
        """Get best value for a metric."""
        if name in self._experiment.metrics:
            return self._experiment.metrics[name].best_value
        return None


# =============================================================================
# EXPERIMENT TRACKER
# =============================================================================

class ExperimentTracker:
    """
    Experiment Tracker for BAEL.

    Comprehensive experiment tracking for ML research.
    """

    def __init__(self, base_dir: str = "./experiments"):
        self._base_dir = Path(base_dir)
        self._experiments: Dict[str, Experiment] = {}
        self._active_run: Optional[ExperimentRun] = None

    def create_experiment(
        self,
        name: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        project: str = "default"
    ) -> ExperimentRun:
        """Create a new experiment."""
        config = ExperimentConfig(
            name=name,
            description=description,
            tags=tags or [],
            project=project,
            base_dir=str(self._base_dir)
        )

        experiment = Experiment(config=config)
        self._experiments[experiment.experiment_id] = experiment

        return ExperimentRun(experiment)

    def start_run(
        self,
        name: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        project: str = "default"
    ) -> ExperimentRun:
        """Start a new experiment run."""
        run = self.create_experiment(name, description, tags, project)
        run.start()
        self._active_run = run
        return run

    def end_run(self, status: ExperimentStatus = ExperimentStatus.COMPLETED) -> None:
        """End the active run."""
        if self._active_run:
            self._active_run.end(status)
            self._active_run = None

    def get_active_run(self) -> Optional[ExperimentRun]:
        """Get the active run."""
        return self._active_run

    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID."""
        return self._experiments.get(experiment_id)

    def list_experiments(
        self,
        project: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: Optional[ExperimentStatus] = None
    ) -> List[Experiment]:
        """List experiments with optional filters."""
        results = list(self._experiments.values())

        if project:
            results = [e for e in results if e.config.project == project]

        if tags:
            tag_set = set(tags)
            results = [e for e in results if tag_set.issubset(set(e.config.tags))]

        if status:
            results = [e for e in results if e.status == status]

        return results

    def compare_experiments(
        self,
        experiment_ids: List[str],
        metric_name: str
    ) -> ComparisonResult:
        """Compare experiments."""
        result = ComparisonResult(experiments=experiment_ids)

        best_value = None
        best_exp = None

        for exp_id in experiment_ids:
            exp = self._experiments.get(exp_id)
            if not exp:
                continue

            if metric_name in exp.metrics:
                metric = exp.metrics[metric_name]
                result.metrics_comparison[exp_id] = {
                    "best": metric.best_value,
                    "best_step": metric.best_step
                }

                if metric.best_value is not None:
                    if best_value is None:
                        best_value = metric.best_value
                        best_exp = exp_id
                    elif metric.direction == MetricDirection.MINIMIZE:
                        if metric.best_value < best_value:
                            best_value = metric.best_value
                            best_exp = exp_id
                    else:
                        if metric.best_value > best_value:
                            best_value = metric.best_value
                            best_exp = exp_id

            result.hyperparameter_diff[exp_id] = {
                k: v.value for k, v in exp.hyperparameters.items()
            }

        result.best_experiment = best_exp
        result.best_metric = str(best_value) if best_value else None

        return result

    def get_best_experiment(
        self,
        metric_name: str,
        project: Optional[str] = None
    ) -> Optional[Experiment]:
        """Get the best experiment for a metric."""
        experiments = self.list_experiments(project=project)

        best_exp = None
        best_value = None

        for exp in experiments:
            if metric_name not in exp.metrics:
                continue

            metric = exp.metrics[metric_name]

            if metric.best_value is None:
                continue

            if best_value is None:
                best_value = metric.best_value
                best_exp = exp
            elif metric.direction == MetricDirection.MINIMIZE:
                if metric.best_value < best_value:
                    best_value = metric.best_value
                    best_exp = exp
            else:
                if metric.best_value > best_value:
                    best_value = metric.best_value
                    best_exp = exp

        return best_exp

    def save_experiment(self, experiment_id: str) -> bool:
        """Save experiment to disk."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return False

        exp_dir = self._base_dir / exp.config.project / experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)

        exp_file = exp_dir / "experiment.json"
        with open(exp_file, "w") as f:
            json.dump(exp.to_dict(), f, indent=2)

        if exp.metrics:
            metrics_file = exp_dir / "metrics.json"
            metrics_data = {}

            for name, metric in exp.metrics.items():
                metrics_data[name] = {
                    "values": [
                        {"value": v.value, "step": v.step}
                        for v in metric.values
                    ],
                    "best_value": metric.best_value,
                    "best_step": metric.best_step
                }

            with open(metrics_file, "w") as f:
                json.dump(metrics_data, f, indent=2)

        return True

    def summary(self) -> Dict[str, Any]:
        """Get tracker summary."""
        experiments = list(self._experiments.values())

        return {
            "total_experiments": len(experiments),
            "by_status": {
                status.value: sum(1 for e in experiments if e.status == status)
                for status in ExperimentStatus
            },
            "by_project": dict(defaultdict(int, {
                e.config.project: sum(1 for ex in experiments if ex.config.project == e.config.project)
                for e in experiments
            })),
            "active_run": self._active_run is not None
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Experiment Tracker."""
    print("=" * 70)
    print("BAEL - EXPERIMENT TRACKER DEMO")
    print("Comprehensive Experiment Tracking for ML Research")
    print("=" * 70)
    print()

    tracker = ExperimentTracker()

    # 1. Create and Start Experiment
    print("1. CREATE AND START EXPERIMENT:")
    print("-" * 40)

    run = tracker.start_run(
        name="baseline_model",
        description="Initial baseline experiment",
        tags=["baseline", "v1"],
        project="bael-demo"
    )

    print(f"   Experiment ID: {run.get_experiment().experiment_id}")
    print(f"   Status: {run.get_experiment().status.value}")
    print()

    # 2. Log Hyperparameters
    print("2. LOG HYPERPARAMETERS:")
    print("-" * 40)

    run.log_params({
        "learning_rate": 0.001,
        "batch_size": 32,
        "epochs": 100,
        "optimizer": "adam",
        "hidden_units": [256, 128, 64]
    })

    for name, param in run.get_experiment().hyperparameters.items():
        print(f"   {name}: {param.value} ({param.dtype})")
    print()

    # 3. Log Metrics
    print("3. LOG METRICS:")
    print("-" * 40)

    for epoch in range(1, 6):
        run.step(epoch)

        train_loss = 1.0 / epoch + 0.1
        val_loss = 1.0 / epoch + 0.15
        accuracy = 0.5 + 0.1 * epoch

        run.log_metrics({
            "train_loss": train_loss,
            "val_loss": val_loss,
            "accuracy": accuracy
        })

        print(f"   Epoch {epoch}: loss={train_loss:.3f}, val_loss={val_loss:.3f}, acc={accuracy:.3f}")
    print()

    # 4. Best Metrics
    print("4. BEST METRICS:")
    print("-" * 40)

    for name, metric in run.get_experiment().metrics.items():
        print(f"   {name}: best={metric.best_value:.4f} at step {metric.best_step}")
    print()

    # 5. Log Notes
    print("5. LOG NOTES:")
    print("-" * 40)

    run.log_note("Started training with baseline configuration")
    run.log_note("Model converging well after epoch 3")

    for note in run.get_experiment().notes:
        print(f"   {note}")
    print()

    # 6. End Experiment
    print("6. END EXPERIMENT:")
    print("-" * 40)

    exp1_id = run.get_experiment().experiment_id
    tracker.end_run()

    exp = tracker.get_experiment(exp1_id)
    print(f"   Status: {exp.status.value}")
    print(f"   Duration: {exp.duration:.2f}s")
    print()

    # 7. Create Second Experiment
    print("7. CREATE SECOND EXPERIMENT:")
    print("-" * 40)

    run2 = tracker.start_run(
        name="improved_model",
        description="Experiment with tuned hyperparameters",
        tags=["improved", "v2"],
        project="bael-demo"
    )

    run2.log_params({
        "learning_rate": 0.0005,
        "batch_size": 64,
        "epochs": 100,
        "optimizer": "adamw",
        "hidden_units": [512, 256, 128]
    })

    for epoch in range(1, 6):
        run2.step(epoch)
        run2.log_metrics({
            "train_loss": 0.8 / epoch + 0.05,
            "val_loss": 0.8 / epoch + 0.1,
            "accuracy": 0.6 + 0.08 * epoch
        })

    exp2_id = run2.get_experiment().experiment_id
    tracker.end_run()

    print(f"   Created experiment: {exp2_id}")
    print()

    # 8. Compare Experiments
    print("8. COMPARE EXPERIMENTS:")
    print("-" * 40)

    comparison = tracker.compare_experiments([exp1_id, exp2_id], "accuracy")

    print(f"   Metric: accuracy")
    for exp_id, data in comparison.metrics_comparison.items():
        print(f"   {exp_id}: best={data['best']:.4f}")
    print(f"   Best experiment: {comparison.best_experiment}")
    print()

    # 9. List Experiments
    print("9. LIST EXPERIMENTS:")
    print("-" * 40)

    experiments = tracker.list_experiments(project="bael-demo")

    for exp in experiments:
        print(f"   {exp.experiment_id}: {exp.config.name} ({exp.status.value})")
    print()

    # 10. Tracker Summary
    print("10. TRACKER SUMMARY:")
    print("-" * 40)

    summary = tracker.summary()

    print(f"   Total experiments: {summary['total_experiments']}")
    print(f"   Completed: {summary['by_status']['completed']}")
    print(f"   Active run: {summary['active_run']}")
    print()

    # 11. Export Experiment
    print("11. EXPORT EXPERIMENT:")
    print("-" * 40)

    exp_dict = tracker.get_experiment(exp1_id).to_dict()

    print(f"   Name: {exp_dict['name']}")
    print(f"   Project: {exp_dict['project']}")
    print(f"   Tags: {exp_dict['tags']}")
    print(f"   Hyperparameters: {len(exp_dict['hyperparameters'])}")
    print(f"   Metrics: {list(exp_dict['metrics_summary'].keys())}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Experiment Tracker Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
