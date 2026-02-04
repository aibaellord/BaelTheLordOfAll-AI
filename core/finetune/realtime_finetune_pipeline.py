"""
BAEL - Real-Time LLM Fine-Tuning Pipeline
==========================================

Live model improvement through continuous learning.

Features:
1. Online Learning - Continuous model updates
2. Feedback Integration - Learn from user feedback
3. Performance Tracking - Monitor model quality
4. A/B Testing - Compare model versions
5. Rollback Support - Revert to previous versions
6. Domain Adaptation - Specialize for domains
7. Style Transfer - Adapt communication style
8. Knowledge Injection - Add new knowledge
9. Self-Evolution - Autonomous improvement
10. Quality Gates - Prevent regression

"A model that stops learning dies."
"""

import asyncio
import hashlib
import json
import logging
import math
import random
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("BAEL.FINETUNE")


# ============================================================================
# ENUMS
# ============================================================================

class FeedbackType(Enum):
    """Types of feedback for learning."""
    POSITIVE = "positive"  # User liked response
    NEGATIVE = "negative"  # User disliked response
    CORRECTION = "correction"  # User provided correction
    PREFERENCE = "preference"  # User chose between options
    IMPLICIT = "implicit"  # Inferred from behavior
    EXPERT = "expert"  # Expert annotation


class LearningMode(Enum):
    """Modes of learning."""
    ONLINE = "online"  # Continuous updates
    BATCH = "batch"  # Periodic batch updates
    REINFORCEMENT = "reinforcement"  # RL from feedback
    SUPERVISED = "supervised"  # From labeled data
    CONTRASTIVE = "contrastive"  # Learn differences


class ModelComponent(Enum):
    """Components that can be fine-tuned."""
    EMBEDDING = "embedding"  # Word embeddings
    ATTENTION = "attention"  # Attention layers
    FEEDFORWARD = "feedforward"  # FF layers
    OUTPUT = "output"  # Output layer
    ADAPTER = "adapter"  # LoRA/adapter layers
    FULL = "full"  # Full model


class QualityMetric(Enum):
    """Quality metrics for evaluation."""
    ACCURACY = "accuracy"
    COHERENCE = "coherence"
    RELEVANCE = "relevance"
    HELPFULNESS = "helpfulness"
    SAFETY = "safety"
    EFFICIENCY = "efficiency"
    CREATIVITY = "creativity"


class ExperimentStatus(Enum):
    """Status of A/B experiment."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class FeedbackSample:
    """A single feedback sample."""
    id: str
    timestamp: datetime
    feedback_type: FeedbackType
    input_text: str
    output_text: str
    user_rating: Optional[float]  # -1 to 1
    correction: Optional[str]  # If user corrected
    preference_choice: Optional[str]  # If preference comparison
    context: Dict[str, Any] = field(default_factory=dict)
    processed: bool = False
    
    def to_training_sample(self) -> Dict[str, Any]:
        """Convert to training format."""
        if self.correction:
            target = self.correction
        elif self.preference_choice:
            target = self.preference_choice
        else:
            target = self.output_text
        
        return {
            "input": self.input_text,
            "target": target,
            "weight": abs(self.user_rating) if self.user_rating else 0.5,
            "feedback_type": self.feedback_type.value
        }


@dataclass
class TrainingBatch:
    """A batch of training samples."""
    id: str
    created_at: datetime
    samples: List[Dict[str, Any]]
    learning_mode: LearningMode
    target_component: ModelComponent
    learning_rate: float = 0.0001
    epochs: int = 1
    processed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sample_count": len(self.samples),
            "mode": self.learning_mode.value,
            "component": self.target_component.value,
            "learning_rate": self.learning_rate
        }


@dataclass
class ModelVersion:
    """A version of the model."""
    version_id: str
    parent_version: Optional[str]
    created_at: datetime
    description: str
    training_batches: List[str]
    metrics: Dict[QualityMetric, float]
    is_active: bool = False
    is_rollback_target: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "parent": self.parent_version,
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "metrics": {k.value: v for k, v in self.metrics.items()},
            "is_active": self.is_active
        }


@dataclass
class Experiment:
    """An A/B experiment."""
    id: str
    name: str
    description: str
    control_version: str
    treatment_version: str
    status: ExperimentStatus
    traffic_split: float  # 0-1, percentage to treatment
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    control_metrics: Dict[QualityMetric, float] = field(default_factory=dict)
    treatment_metrics: Dict[QualityMetric, float] = field(default_factory=dict)
    sample_size: int = 0
    
    def get_winner(self) -> Optional[str]:
        """Determine experiment winner."""
        if self.status != ExperimentStatus.COMPLETED:
            return None
        
        if not self.control_metrics or not self.treatment_metrics:
            return None
        
        control_score = sum(self.control_metrics.values()) / len(self.control_metrics)
        treatment_score = sum(self.treatment_metrics.values()) / len(self.treatment_metrics)
        
        if treatment_score > control_score * 1.05:  # 5% improvement threshold
            return "treatment"
        elif control_score > treatment_score * 1.05:
            return "control"
        else:
            return "tie"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "traffic_split": self.traffic_split,
            "sample_size": self.sample_size,
            "winner": self.get_winner()
        }


@dataclass
class QualityGate:
    """Quality gate to prevent regression."""
    metric: QualityMetric
    threshold: float
    is_blocking: bool  # If True, blocks deployment
    current_value: Optional[float] = None
    
    def passes(self, value: float) -> bool:
        """Check if value passes gate."""
        self.current_value = value
        return value >= self.threshold


@dataclass
class LearningSession:
    """A learning session."""
    id: str
    started_at: datetime
    ended_at: Optional[datetime]
    mode: LearningMode
    samples_processed: int = 0
    batches_processed: int = 0
    current_loss: float = 0.0
    best_loss: float = float('inf')
    metrics_history: List[Dict[str, float]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "mode": self.mode.value,
            "samples_processed": self.samples_processed,
            "current_loss": self.current_loss,
            "best_loss": self.best_loss
        }


# ============================================================================
# FEEDBACK COLLECTOR
# ============================================================================

class FeedbackCollector:
    """
    Collects and processes user feedback for learning.
    """
    
    def __init__(self, buffer_size: int = 1000):
        self.buffer: deque = deque(maxlen=buffer_size)
        self.processed_samples: List[FeedbackSample] = []
        self.feedback_stats: Dict[FeedbackType, int] = defaultdict(int)
    
    def add_feedback(
        self,
        input_text: str,
        output_text: str,
        feedback_type: FeedbackType,
        rating: float = None,
        correction: str = None,
        context: Dict[str, Any] = None
    ) -> FeedbackSample:
        """Add feedback sample."""
        sample = FeedbackSample(
            id=hashlib.md5(f"{input_text}{time.time()}".encode()).hexdigest()[:12],
            timestamp=datetime.now(),
            feedback_type=feedback_type,
            input_text=input_text,
            output_text=output_text,
            user_rating=rating,
            correction=correction,
            preference_choice=None,
            context=context or {}
        )
        
        self.buffer.append(sample)
        self.feedback_stats[feedback_type] += 1
        
        return sample
    
    def add_preference(
        self,
        input_text: str,
        option_a: str,
        option_b: str,
        choice: str,  # "a" or "b"
        context: Dict[str, Any] = None
    ) -> FeedbackSample:
        """Add preference comparison."""
        chosen = option_a if choice == "a" else option_b
        rejected = option_b if choice == "a" else option_a
        
        sample = FeedbackSample(
            id=hashlib.md5(f"{input_text}{time.time()}".encode()).hexdigest()[:12],
            timestamp=datetime.now(),
            feedback_type=FeedbackType.PREFERENCE,
            input_text=input_text,
            output_text=rejected,
            user_rating=1.0 if choice else -1.0,
            correction=None,
            preference_choice=chosen,
            context=context or {}
        )
        
        self.buffer.append(sample)
        self.feedback_stats[FeedbackType.PREFERENCE] += 1
        
        return sample
    
    def get_batch(
        self,
        size: int = 32,
        feedback_types: List[FeedbackType] = None
    ) -> List[FeedbackSample]:
        """Get batch of unprocessed samples."""
        samples = []
        
        for sample in self.buffer:
            if sample.processed:
                continue
            
            if feedback_types and sample.feedback_type not in feedback_types:
                continue
            
            samples.append(sample)
            
            if len(samples) >= size:
                break
        
        return samples
    
    def mark_processed(self, sample_ids: List[str]) -> None:
        """Mark samples as processed."""
        for sample in self.buffer:
            if sample.id in sample_ids:
                sample.processed = True
                self.processed_samples.append(sample)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get feedback statistics."""
        return {
            "total_samples": len(self.buffer),
            "processed": len(self.processed_samples),
            "pending": len([s for s in self.buffer if not s.processed]),
            "by_type": {k.value: v for k, v in self.feedback_stats.items()}
        }


# ============================================================================
# MODEL VERSION MANAGER
# ============================================================================

class VersionManager:
    """
    Manages model versions and rollback.
    """
    
    def __init__(self, max_versions: int = 10):
        self.versions: Dict[str, ModelVersion] = {}
        self.active_version: Optional[str] = None
        self.version_history: List[str] = []
        self.max_versions = max_versions
    
    def create_version(
        self,
        description: str,
        training_batches: List[str] = None,
        parent_version: str = None
    ) -> ModelVersion:
        """Create a new model version."""
        version = ModelVersion(
            version_id=f"v_{hashlib.md5(f'{time.time()}'.encode()).hexdigest()[:8]}",
            parent_version=parent_version or self.active_version,
            created_at=datetime.now(),
            description=description,
            training_batches=training_batches or [],
            metrics={},
            is_active=False
        )
        
        self.versions[version.version_id] = version
        self.version_history.append(version.version_id)
        
        # Cleanup old versions
        self._cleanup_old_versions()
        
        return version
    
    def activate_version(self, version_id: str) -> bool:
        """Activate a version."""
        if version_id not in self.versions:
            return False
        
        # Deactivate current
        if self.active_version and self.active_version in self.versions:
            self.versions[self.active_version].is_active = False
        
        # Activate new
        self.versions[version_id].is_active = True
        self.active_version = version_id
        
        logger.info(f"Activated model version: {version_id}")
        return True
    
    def rollback(self, to_version: str = None) -> Optional[str]:
        """Rollback to a previous version."""
        if to_version:
            if to_version not in self.versions:
                return None
            target = to_version
        else:
            # Rollback to previous
            current_idx = self.version_history.index(self.active_version) if self.active_version in self.version_history else -1
            if current_idx <= 0:
                return None
            target = self.version_history[current_idx - 1]
        
        # Check if rollback target
        if not self.versions[target].is_rollback_target:
            return None
        
        self.activate_version(target)
        logger.info(f"Rolled back to version: {target}")
        
        return target
    
    def update_metrics(
        self,
        version_id: str,
        metrics: Dict[QualityMetric, float]
    ) -> None:
        """Update version metrics."""
        if version_id in self.versions:
            self.versions[version_id].metrics.update(metrics)
    
    def get_best_version(
        self,
        metric: QualityMetric = QualityMetric.ACCURACY
    ) -> Optional[str]:
        """Get best version by metric."""
        best_version = None
        best_score = -float('inf')
        
        for version in self.versions.values():
            if metric in version.metrics:
                if version.metrics[metric] > best_score:
                    best_score = version.metrics[metric]
                    best_version = version.version_id
        
        return best_version
    
    def _cleanup_old_versions(self) -> None:
        """Remove old versions beyond limit."""
        while len(self.version_history) > self.max_versions:
            old_version_id = self.version_history.pop(0)
            if old_version_id != self.active_version:
                del self.versions[old_version_id]
    
    def list_versions(self) -> List[Dict[str, Any]]:
        """List all versions."""
        return [v.to_dict() for v in self.versions.values()]


# ============================================================================
# EXPERIMENT MANAGER
# ============================================================================

class ExperimentManager:
    """
    Manages A/B experiments for model comparison.
    """
    
    def __init__(self):
        self.experiments: Dict[str, Experiment] = {}
        self.active_experiment: Optional[str] = None
    
    def create_experiment(
        self,
        name: str,
        control_version: str,
        treatment_version: str,
        traffic_split: float = 0.5,
        description: str = ""
    ) -> Experiment:
        """Create a new experiment."""
        exp = Experiment(
            id=hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:8],
            name=name,
            description=description,
            control_version=control_version,
            treatment_version=treatment_version,
            status=ExperimentStatus.DRAFT,
            traffic_split=traffic_split,
            started_at=None,
            ended_at=None
        )
        
        self.experiments[exp.id] = exp
        return exp
    
    def start_experiment(self, experiment_id: str) -> bool:
        """Start an experiment."""
        if experiment_id not in self.experiments:
            return False
        
        exp = self.experiments[experiment_id]
        if exp.status != ExperimentStatus.DRAFT:
            return False
        
        exp.status = ExperimentStatus.RUNNING
        exp.started_at = datetime.now()
        self.active_experiment = experiment_id
        
        logger.info(f"Started experiment: {exp.name}")
        return True
    
    def get_variant(self, experiment_id: str = None) -> str:
        """Get variant for a request (control or treatment)."""
        exp_id = experiment_id or self.active_experiment
        if not exp_id or exp_id not in self.experiments:
            return "control"
        
        exp = self.experiments[exp_id]
        if exp.status != ExperimentStatus.RUNNING:
            return "control"
        
        # Random assignment based on traffic split
        if random.random() < exp.traffic_split:
            return "treatment"
        return "control"
    
    def record_result(
        self,
        experiment_id: str,
        variant: str,
        metrics: Dict[QualityMetric, float]
    ) -> None:
        """Record experiment result."""
        if experiment_id not in self.experiments:
            return
        
        exp = self.experiments[experiment_id]
        exp.sample_size += 1
        
        target_metrics = exp.treatment_metrics if variant == "treatment" else exp.control_metrics
        
        # Running average
        for metric, value in metrics.items():
            if metric in target_metrics:
                old_value = target_metrics[metric]
                # Exponential moving average
                target_metrics[metric] = old_value * 0.95 + value * 0.05
            else:
                target_metrics[metric] = value
    
    def end_experiment(self, experiment_id: str) -> Optional[str]:
        """End experiment and return winner."""
        if experiment_id not in self.experiments:
            return None
        
        exp = self.experiments[experiment_id]
        exp.status = ExperimentStatus.COMPLETED
        exp.ended_at = datetime.now()
        
        if self.active_experiment == experiment_id:
            self.active_experiment = None
        
        winner = exp.get_winner()
        logger.info(f"Experiment {exp.name} ended. Winner: {winner}")
        
        return winner
    
    def list_experiments(self) -> List[Dict[str, Any]]:
        """List all experiments."""
        return [e.to_dict() for e in self.experiments.values()]


# ============================================================================
# FINE-TUNING PIPELINE
# ============================================================================

class FineTuningPipeline:
    """
    Real-time fine-tuning pipeline for continuous model improvement.
    
    Provides:
    - Online learning from feedback
    - A/B testing for changes
    - Quality gates to prevent regression
    - Version management and rollback
    """
    
    def __init__(self):
        self.feedback_collector = FeedbackCollector()
        self.version_manager = VersionManager()
        self.experiment_manager = ExperimentManager()
        
        self.quality_gates: List[QualityGate] = []
        self.training_batches: Dict[str, TrainingBatch] = {}
        self.active_session: Optional[LearningSession] = None
        self.sessions: List[LearningSession] = []
        
        # Configuration
        self.batch_size = 32
        self.min_samples_for_update = 100
        self.learning_rate = 0.0001
        
        # Initialize default quality gates
        self._init_quality_gates()
        
        logger.info("FineTuningPipeline initialized")
    
    def _init_quality_gates(self) -> None:
        """Initialize default quality gates."""
        self.quality_gates = [
            QualityGate(QualityMetric.ACCURACY, 0.85, is_blocking=True),
            QualityGate(QualityMetric.SAFETY, 0.95, is_blocking=True),
            QualityGate(QualityMetric.COHERENCE, 0.80, is_blocking=True),
            QualityGate(QualityMetric.HELPFULNESS, 0.75, is_blocking=False)
        ]
    
    # -------------------------------------------------------------------------
    # FEEDBACK COLLECTION
    # -------------------------------------------------------------------------
    
    def collect_positive_feedback(
        self,
        input_text: str,
        output_text: str,
        context: Dict[str, Any] = None
    ) -> str:
        """Collect positive feedback."""
        sample = self.feedback_collector.add_feedback(
            input_text=input_text,
            output_text=output_text,
            feedback_type=FeedbackType.POSITIVE,
            rating=1.0,
            context=context
        )
        return sample.id
    
    def collect_negative_feedback(
        self,
        input_text: str,
        output_text: str,
        context: Dict[str, Any] = None
    ) -> str:
        """Collect negative feedback."""
        sample = self.feedback_collector.add_feedback(
            input_text=input_text,
            output_text=output_text,
            feedback_type=FeedbackType.NEGATIVE,
            rating=-1.0,
            context=context
        )
        return sample.id
    
    def collect_correction(
        self,
        input_text: str,
        output_text: str,
        correction: str,
        context: Dict[str, Any] = None
    ) -> str:
        """Collect correction from user."""
        sample = self.feedback_collector.add_feedback(
            input_text=input_text,
            output_text=output_text,
            feedback_type=FeedbackType.CORRECTION,
            correction=correction,
            context=context
        )
        return sample.id
    
    def collect_preference(
        self,
        input_text: str,
        option_a: str,
        option_b: str,
        choice: str,
        context: Dict[str, Any] = None
    ) -> str:
        """Collect preference comparison."""
        sample = self.feedback_collector.add_preference(
            input_text=input_text,
            option_a=option_a,
            option_b=option_b,
            choice=choice,
            context=context
        )
        return sample.id
    
    # -------------------------------------------------------------------------
    # TRAINING
    # -------------------------------------------------------------------------
    
    async def start_learning_session(
        self,
        mode: LearningMode = LearningMode.ONLINE
    ) -> LearningSession:
        """Start a new learning session."""
        session = LearningSession(
            id=hashlib.md5(f"session_{time.time()}".encode()).hexdigest()[:8],
            started_at=datetime.now(),
            ended_at=None,
            mode=mode
        )
        
        self.active_session = session
        self.sessions.append(session)
        
        logger.info(f"Started learning session: {session.id}")
        return session
    
    async def process_feedback_batch(
        self,
        feedback_types: List[FeedbackType] = None
    ) -> Optional[TrainingBatch]:
        """Process a batch of feedback."""
        if not self.active_session:
            return None
        
        # Get unprocessed samples
        samples = self.feedback_collector.get_batch(
            size=self.batch_size,
            feedback_types=feedback_types
        )
        
        if len(samples) < self.batch_size // 2:  # Need minimum samples
            return None
        
        # Convert to training samples
        training_samples = [s.to_training_sample() for s in samples]
        
        # Create batch
        batch = TrainingBatch(
            id=hashlib.md5(f"batch_{time.time()}".encode()).hexdigest()[:8],
            created_at=datetime.now(),
            samples=training_samples,
            learning_mode=self.active_session.mode,
            target_component=ModelComponent.ADAPTER,
            learning_rate=self.learning_rate
        )
        
        self.training_batches[batch.id] = batch
        
        # Simulate training (in production, would call actual training)
        await self._train_on_batch(batch)
        
        # Mark samples as processed
        self.feedback_collector.mark_processed([s.id for s in samples])
        
        # Update session
        self.active_session.samples_processed += len(samples)
        self.active_session.batches_processed += 1
        
        return batch
    
    async def _train_on_batch(self, batch: TrainingBatch) -> Dict[str, float]:
        """Train on a batch (simulated)."""
        # Simulate training time
        await asyncio.sleep(0.1)
        
        # Simulate loss calculation
        initial_loss = 1.0
        final_loss = initial_loss * 0.9  # Simulated improvement
        
        if self.active_session:
            self.active_session.current_loss = final_loss
            if final_loss < self.active_session.best_loss:
                self.active_session.best_loss = final_loss
            
            self.active_session.metrics_history.append({
                "batch_id": batch.id,
                "loss": final_loss,
                "timestamp": datetime.now().isoformat()
            })
        
        batch.processed = True
        
        return {"loss": final_loss, "samples": len(batch.samples)}
    
    async def end_learning_session(self) -> Optional[LearningSession]:
        """End current learning session."""
        if not self.active_session:
            return None
        
        self.active_session.ended_at = datetime.now()
        
        # Create new model version
        batch_ids = [b.id for b in self.training_batches.values() if b.processed]
        version = self.version_manager.create_version(
            description=f"Training session {self.active_session.id}",
            training_batches=batch_ids
        )
        
        logger.info(f"Ended learning session: {self.active_session.id}")
        logger.info(f"Created model version: {version.version_id}")
        
        session = self.active_session
        self.active_session = None
        
        return session
    
    # -------------------------------------------------------------------------
    # QUALITY GATES
    # -------------------------------------------------------------------------
    
    async def evaluate_version(
        self,
        version_id: str,
        test_samples: List[Dict[str, Any]] = None
    ) -> Dict[QualityMetric, float]:
        """Evaluate a model version."""
        # Simulate evaluation (in production, would run actual eval)
        await asyncio.sleep(0.1)
        
        metrics = {
            QualityMetric.ACCURACY: random.uniform(0.8, 0.95),
            QualityMetric.COHERENCE: random.uniform(0.75, 0.95),
            QualityMetric.RELEVANCE: random.uniform(0.8, 0.95),
            QualityMetric.HELPFULNESS: random.uniform(0.7, 0.9),
            QualityMetric.SAFETY: random.uniform(0.9, 0.99),
            QualityMetric.EFFICIENCY: random.uniform(0.8, 0.95)
        }
        
        self.version_manager.update_metrics(version_id, metrics)
        
        return metrics
    
    def check_quality_gates(
        self,
        metrics: Dict[QualityMetric, float]
    ) -> Tuple[bool, List[str]]:
        """Check if metrics pass all quality gates."""
        failures = []
        
        for gate in self.quality_gates:
            if gate.metric in metrics:
                if not gate.passes(metrics[gate.metric]):
                    failures.append(
                        f"{gate.metric.value}: {metrics[gate.metric]:.3f} < {gate.threshold:.3f}"
                    )
        
        blocking_failures = [
            f for f, gate in zip(failures, self.quality_gates)
            if gate.is_blocking
        ]
        
        passes = len(blocking_failures) == 0
        
        return passes, failures
    
    # -------------------------------------------------------------------------
    # DEPLOYMENT
    # -------------------------------------------------------------------------
    
    async def safe_deploy(
        self,
        version_id: str,
        skip_experiment: bool = False
    ) -> Dict[str, Any]:
        """Safely deploy a new version with quality checks."""
        # Step 1: Evaluate version
        metrics = await self.evaluate_version(version_id)
        
        # Step 2: Check quality gates
        passes, failures = self.check_quality_gates(metrics)
        
        if not passes:
            return {
                "success": False,
                "reason": "Quality gates failed",
                "failures": failures,
                "recommendation": "Review training or rollback"
            }
        
        # Step 3: A/B test (unless skipped)
        if not skip_experiment and self.version_manager.active_version:
            exp = self.experiment_manager.create_experiment(
                name=f"Deploy {version_id}",
                control_version=self.version_manager.active_version,
                treatment_version=version_id,
                traffic_split=0.1  # Start with 10%
            )
            
            self.experiment_manager.start_experiment(exp.id)
            
            return {
                "success": True,
                "status": "experiment_started",
                "experiment_id": exp.id,
                "message": "Version deployed to 10% of traffic for A/B testing"
            }
        
        # Step 4: Direct deployment
        self.version_manager.activate_version(version_id)
        
        return {
            "success": True,
            "status": "deployed",
            "version_id": version_id,
            "metrics": {k.value: v for k, v in metrics.items()}
        }
    
    async def gradual_rollout(
        self,
        experiment_id: str,
        increment: float = 0.1
    ) -> Dict[str, Any]:
        """Gradually increase traffic to treatment."""
        if experiment_id not in self.experiment_manager.experiments:
            return {"error": "Experiment not found"}
        
        exp = self.experiment_manager.experiments[experiment_id]
        
        if exp.status != ExperimentStatus.RUNNING:
            return {"error": "Experiment not running"}
        
        new_split = min(1.0, exp.traffic_split + increment)
        exp.traffic_split = new_split
        
        if new_split >= 1.0:
            # Full rollout - end experiment
            winner = self.experiment_manager.end_experiment(experiment_id)
            if winner == "treatment":
                self.version_manager.activate_version(exp.treatment_version)
            
            return {
                "status": "completed",
                "winner": winner,
                "deployed_version": exp.treatment_version if winner == "treatment" else exp.control_version
            }
        
        return {
            "status": "running",
            "traffic_split": new_split,
            "sample_size": exp.sample_size
        }
    
    # -------------------------------------------------------------------------
    # SELF-EVOLUTION
    # -------------------------------------------------------------------------
    
    async def self_evolve(
        self,
        generations: int = 5,
        target_metric: QualityMetric = QualityMetric.ACCURACY
    ) -> Dict[str, Any]:
        """Self-evolution loop for autonomous improvement."""
        results = []
        current_version = self.version_manager.active_version
        
        for gen in range(generations):
            logger.info(f"Self-evolution generation {gen + 1}")
            
            # Start learning session
            session = await self.start_learning_session(LearningMode.REINFORCEMENT)
            
            # Process all available feedback
            batches_processed = 0
            while True:
                batch = await self.process_feedback_batch()
                if batch is None:
                    break
                batches_processed += 1
            
            # End session and create version
            await self.end_learning_session()
            
            # Find new version
            new_version = self.version_manager.version_history[-1] if self.version_manager.version_history else None
            
            if new_version:
                # Evaluate
                metrics = await self.evaluate_version(new_version)
                
                # Check if improved
                if current_version:
                    current_metrics = self.version_manager.versions[current_version].metrics
                    if target_metric in metrics and target_metric in current_metrics:
                        if metrics[target_metric] > current_metrics[target_metric]:
                            # Better - activate
                            self.version_manager.activate_version(new_version)
                            current_version = new_version
                            logger.info(f"Generation {gen + 1}: Improved to {metrics[target_metric]:.3f}")
                else:
                    self.version_manager.activate_version(new_version)
                    current_version = new_version
                
                results.append({
                    "generation": gen + 1,
                    "version": new_version,
                    "batches": batches_processed,
                    "metrics": {k.value: v for k, v in metrics.items()}
                })
        
        return {
            "generations": generations,
            "final_version": current_version,
            "evolution_history": results
        }
    
    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        return {
            "feedback": self.feedback_collector.get_stats(),
            "active_session": self.active_session.to_dict() if self.active_session else None,
            "versions": {
                "active": self.version_manager.active_version,
                "total": len(self.version_manager.versions)
            },
            "experiments": {
                "active": self.experiment_manager.active_experiment,
                "total": len(self.experiment_manager.experiments)
            },
            "quality_gates": [
                {
                    "metric": g.metric.value,
                    "threshold": g.threshold,
                    "blocking": g.is_blocking
                }
                for g in self.quality_gates
            ]
        }


# ============================================================================
# SINGLETON
# ============================================================================

_finetune_pipeline: Optional[FineTuningPipeline] = None


def get_finetune_pipeline() -> FineTuningPipeline:
    """Get the global fine-tuning pipeline."""
    global _finetune_pipeline
    if _finetune_pipeline is None:
        _finetune_pipeline = FineTuningPipeline()
    return _finetune_pipeline


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate fine-tuning pipeline."""
    print("=" * 60)
    print("REAL-TIME LLM FINE-TUNING PIPELINE")
    print("=" * 60)
    
    pipeline = get_finetune_pipeline()
    
    # Collect feedback
    print("\n--- Collecting Feedback ---")
    for i in range(50):
        if i % 3 == 0:
            pipeline.collect_positive_feedback(
                f"Input {i}", f"Good output {i}"
            )
        elif i % 3 == 1:
            pipeline.collect_negative_feedback(
                f"Input {i}", f"Bad output {i}"
            )
        else:
            pipeline.collect_correction(
                f"Input {i}", f"Wrong output {i}", f"Correct output {i}"
            )
    
    print(f"Collected: {json.dumps(pipeline.feedback_collector.get_stats(), indent=2)}")
    
    # Start learning session
    print("\n--- Starting Learning Session ---")
    session = await pipeline.start_learning_session(LearningMode.ONLINE)
    print(f"Session: {session.id}")
    
    # Process feedback
    print("\n--- Processing Feedback ---")
    while True:
        batch = await pipeline.process_feedback_batch()
        if batch is None:
            break
        print(f"Processed batch: {batch.id} ({len(batch.samples)} samples)")
    
    # End session
    await pipeline.end_learning_session()
    print(f"Session ended. Samples processed: {session.samples_processed}")
    
    # Safe deploy
    print("\n--- Safe Deployment ---")
    if pipeline.version_manager.version_history:
        new_version = pipeline.version_manager.version_history[-1]
        result = await pipeline.safe_deploy(new_version, skip_experiment=True)
        print(json.dumps(result, indent=2))
    
    # Create experiment
    print("\n--- A/B Experiment ---")
    if len(pipeline.version_manager.version_history) >= 2:
        v1 = pipeline.version_manager.version_history[-2]
        v2 = pipeline.version_manager.version_history[-1]
        
        exp = pipeline.experiment_manager.create_experiment(
            name="Test experiment",
            control_version=v1,
            treatment_version=v2
        )
        pipeline.experiment_manager.start_experiment(exp.id)
        
        # Simulate some traffic
        for _ in range(100):
            variant = pipeline.experiment_manager.get_variant(exp.id)
            pipeline.experiment_manager.record_result(
                exp.id,
                variant,
                {QualityMetric.ACCURACY: random.uniform(0.7, 0.95)}
            )
        
        winner = pipeline.experiment_manager.end_experiment(exp.id)
        print(f"Experiment winner: {winner}")
    
    # Pipeline status
    print("\n--- Pipeline Status ---")
    status = pipeline.get_pipeline_status()
    print(json.dumps(status, indent=2, default=str))
    
    print("\n" + "=" * 60)
    print("FINE-TUNING PIPELINE DEMO COMPLETE")


if __name__ == "__main__":
    asyncio.run(demo())
