#!/usr/bin/env python3
"""
BAEL - Ensemble Manager
Advanced ensemble learning and model combination.

Features:
- Bagging and boosting
- Stacking
- Voting ensembles
- Model weighting
- Diversity measures
- Dynamic ensemble selection
"""

import asyncio
import copy
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class EnsembleType(Enum):
    """Types of ensembles."""
    BAGGING = "bagging"
    BOOSTING = "boosting"
    STACKING = "stacking"
    VOTING = "voting"


class VotingType(Enum):
    """Types of voting."""
    HARD = "hard"
    SOFT = "soft"
    WEIGHTED = "weighted"


class SelectionStrategy(Enum):
    """Dynamic selection strategies."""
    OVERALL_BEST = "overall_best"
    LOCAL_BEST = "local_best"
    ORACLE = "oracle"


class CombinationType(Enum):
    """Prediction combination types."""
    AVERAGE = "average"
    WEIGHTED_AVERAGE = "weighted_average"
    MEDIAN = "median"
    MAX = "max"


class DiversityMeasure(Enum):
    """Diversity measures."""
    DISAGREEMENT = "disagreement"
    Q_STATISTIC = "q_statistic"
    CORRELATION = "correlation"
    KAPPA = "kappa"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Model:
    """A base model in the ensemble."""
    model_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    model_type: str = ""
    weight: float = 1.0
    accuracy: float = 0.0
    trained: bool = False


@dataclass
class Prediction:
    """A model prediction."""
    pred_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_id: str = ""
    sample_id: str = ""
    predicted_class: Optional[str] = None
    probabilities: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0


@dataclass
class EnsemblePrediction:
    """Combined ensemble prediction."""
    sample_id: str = ""
    final_class: Optional[str] = None
    final_probabilities: Dict[str, float] = field(default_factory=dict)
    model_predictions: List[Prediction] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class DiversityReport:
    """Diversity analysis report."""
    measure: DiversityMeasure = DiversityMeasure.DISAGREEMENT
    value: float = 0.0
    pairwise_values: Dict[Tuple[str, str], float] = field(default_factory=dict)


@dataclass
class EnsembleConfig:
    """Ensemble configuration."""
    ensemble_type: EnsembleType = EnsembleType.VOTING
    voting_type: VotingType = VotingType.SOFT
    n_models: int = 5
    combination: CombinationType = CombinationType.AVERAGE


# =============================================================================
# MODEL POOL
# =============================================================================

class ModelPool:
    """Pool of models."""

    def __init__(self):
        self._models: Dict[str, Model] = {}

    def add(
        self,
        name: str,
        model_type: str = "",
        weight: float = 1.0
    ) -> Model:
        """Add a model."""
        model = Model(name=name, model_type=model_type, weight=weight)
        self._models[model.model_id] = model
        return model

    def get(self, model_id: str) -> Optional[Model]:
        """Get a model."""
        return self._models.get(model_id)

    def get_by_name(self, name: str) -> Optional[Model]:
        """Get a model by name."""
        for model in self._models.values():
            if model.name == name:
                return model
        return None

    def set_weight(self, model_id: str, weight: float) -> None:
        """Set model weight."""
        model = self._models.get(model_id)
        if model:
            model.weight = weight

    def set_accuracy(self, model_id: str, accuracy: float) -> None:
        """Set model accuracy."""
        model = self._models.get(model_id)
        if model:
            model.accuracy = accuracy

    def all_models(self) -> List[Model]:
        """Get all models."""
        return list(self._models.values())

    def top_models(self, n: int = 5) -> List[Model]:
        """Get top n models by accuracy."""
        sorted_models = sorted(
            self._models.values(),
            key=lambda m: m.accuracy,
            reverse=True
        )
        return sorted_models[:n]


# =============================================================================
# VOTING ENSEMBLE
# =============================================================================

class VotingEnsemble:
    """Voting-based ensemble."""

    def __init__(self, voting_type: VotingType = VotingType.SOFT):
        self._voting_type = voting_type

    def vote(
        self,
        predictions: List[Prediction],
        weights: Optional[Dict[str, float]] = None
    ) -> EnsemblePrediction:
        """Combine predictions via voting."""
        if not predictions:
            return EnsemblePrediction()

        sample_id = predictions[0].sample_id

        if self._voting_type == VotingType.HARD:
            return self._hard_vote(predictions, sample_id)
        elif self._voting_type == VotingType.SOFT:
            return self._soft_vote(predictions, sample_id, weights)
        elif self._voting_type == VotingType.WEIGHTED:
            return self._weighted_vote(predictions, sample_id, weights)

        return EnsemblePrediction(sample_id=sample_id)

    def _hard_vote(
        self,
        predictions: List[Prediction],
        sample_id: str
    ) -> EnsemblePrediction:
        """Hard voting (majority)."""
        votes = Counter(p.predicted_class for p in predictions if p.predicted_class)

        if not votes:
            return EnsemblePrediction(sample_id=sample_id)

        final_class, count = votes.most_common(1)[0]
        confidence = count / len(predictions)

        # Calculate class probabilities from votes
        total = sum(votes.values())
        final_probs = {cls: c / total for cls, c in votes.items()}

        return EnsemblePrediction(
            sample_id=sample_id,
            final_class=final_class,
            final_probabilities=final_probs,
            model_predictions=predictions,
            confidence=confidence
        )

    def _soft_vote(
        self,
        predictions: List[Prediction],
        sample_id: str,
        weights: Optional[Dict[str, float]] = None
    ) -> EnsemblePrediction:
        """Soft voting (average probabilities)."""
        aggregated: Dict[str, float] = defaultdict(float)
        total_weight = 0.0

        for pred in predictions:
            w = weights.get(pred.model_id, 1.0) if weights else 1.0
            total_weight += w

            for cls, prob in pred.probabilities.items():
                aggregated[cls] += prob * w

        if total_weight > 0:
            for cls in aggregated:
                aggregated[cls] /= total_weight

        final_class = max(aggregated.keys(), key=lambda k: aggregated[k]) if aggregated else None
        confidence = aggregated.get(final_class, 0.0) if final_class else 0.0

        return EnsemblePrediction(
            sample_id=sample_id,
            final_class=final_class,
            final_probabilities=dict(aggregated),
            model_predictions=predictions,
            confidence=confidence
        )

    def _weighted_vote(
        self,
        predictions: List[Prediction],
        sample_id: str,
        weights: Optional[Dict[str, float]] = None
    ) -> EnsemblePrediction:
        """Weighted voting."""
        return self._soft_vote(predictions, sample_id, weights)


# =============================================================================
# STACKING ENSEMBLE
# =============================================================================

class StackingEnsemble:
    """Stacking (meta-learning) ensemble."""

    def __init__(self):
        self._meta_weights: Dict[str, Dict[str, float]] = {}

    def train_meta(
        self,
        model_predictions: Dict[str, List[Prediction]],
        true_labels: List[str]
    ) -> None:
        """Train meta-learner weights."""
        # Simple: weight by accuracy
        for model_id, predictions in model_predictions.items():
            correct = sum(
                1 for pred, true in zip(predictions, true_labels)
                if pred.predicted_class == true
            )
            accuracy = correct / len(predictions) if predictions else 0.0
            self._meta_weights[model_id] = {"accuracy": accuracy}

    def predict(
        self,
        predictions: List[Prediction]
    ) -> EnsemblePrediction:
        """Make stacked prediction."""
        if not predictions:
            return EnsemblePrediction()

        sample_id = predictions[0].sample_id

        # Weight by learned meta-weights
        aggregated: Dict[str, float] = defaultdict(float)
        total_weight = 0.0

        for pred in predictions:
            w = self._meta_weights.get(pred.model_id, {}).get("accuracy", 1.0)
            total_weight += w

            for cls, prob in pred.probabilities.items():
                aggregated[cls] += prob * w

        if total_weight > 0:
            for cls in aggregated:
                aggregated[cls] /= total_weight

        final_class = max(aggregated.keys(), key=lambda k: aggregated[k]) if aggregated else None
        confidence = aggregated.get(final_class, 0.0) if final_class else 0.0

        return EnsemblePrediction(
            sample_id=sample_id,
            final_class=final_class,
            final_probabilities=dict(aggregated),
            model_predictions=predictions,
            confidence=confidence
        )


# =============================================================================
# DIVERSITY ANALYZER
# =============================================================================

class DiversityAnalyzer:
    """Analyze ensemble diversity."""

    def disagreement(
        self,
        predictions1: List[Prediction],
        predictions2: List[Prediction]
    ) -> float:
        """Calculate disagreement between two models."""
        if len(predictions1) != len(predictions2):
            return 0.0

        disagreements = sum(
            1 for p1, p2 in zip(predictions1, predictions2)
            if p1.predicted_class != p2.predicted_class
        )

        return disagreements / len(predictions1) if predictions1 else 0.0

    def pairwise_diversity(
        self,
        model_predictions: Dict[str, List[Prediction]]
    ) -> DiversityReport:
        """Calculate pairwise diversity."""
        pairwise = {}
        model_ids = list(model_predictions.keys())

        for i, m1 in enumerate(model_ids):
            for m2 in model_ids[i + 1:]:
                d = self.disagreement(
                    model_predictions[m1],
                    model_predictions[m2]
                )
                pairwise[(m1, m2)] = d

        avg_diversity = sum(pairwise.values()) / len(pairwise) if pairwise else 0.0

        return DiversityReport(
            measure=DiversityMeasure.DISAGREEMENT,
            value=avg_diversity,
            pairwise_values=pairwise
        )

    def q_statistic(
        self,
        predictions1: List[Prediction],
        predictions2: List[Prediction],
        true_labels: List[str]
    ) -> float:
        """Calculate Q-statistic."""
        n11 = n00 = n10 = n01 = 0

        for p1, p2, true in zip(predictions1, predictions2, true_labels):
            c1 = p1.predicted_class == true
            c2 = p2.predicted_class == true

            if c1 and c2:
                n11 += 1
            elif not c1 and not c2:
                n00 += 1
            elif c1 and not c2:
                n10 += 1
            else:
                n01 += 1

        num = n11 * n00 - n01 * n10
        den = n11 * n00 + n01 * n10

        return num / den if den != 0 else 0.0


# =============================================================================
# DYNAMIC SELECTOR
# =============================================================================

class DynamicSelector:
    """Dynamic ensemble selection."""

    def __init__(self, strategy: SelectionStrategy = SelectionStrategy.OVERALL_BEST):
        self._strategy = strategy
        self._local_accuracies: Dict[str, Dict[str, float]] = {}

    def train(
        self,
        model_predictions: Dict[str, List[Prediction]],
        true_labels: List[str]
    ) -> None:
        """Train selector with validation data."""
        for model_id, predictions in model_predictions.items():
            correct = sum(
                1 for pred, true in zip(predictions, true_labels)
                if pred.predicted_class == true
            )
            accuracy = correct / len(predictions) if predictions else 0.0
            self._local_accuracies[model_id] = {"overall": accuracy}

    def select(
        self,
        sample_id: str,
        predictions: List[Prediction],
        n: int = 3
    ) -> List[Prediction]:
        """Select best models for a sample."""
        if self._strategy == SelectionStrategy.OVERALL_BEST:
            # Sort by overall accuracy
            sorted_preds = sorted(
                predictions,
                key=lambda p: self._local_accuracies.get(p.model_id, {}).get("overall", 0),
                reverse=True
            )
            return sorted_preds[:n]

        elif self._strategy == SelectionStrategy.LOCAL_BEST:
            # Would need local competence regions
            # Fallback to overall for now
            return self.select(sample_id, predictions, n)

        return predictions[:n]


# =============================================================================
# ENSEMBLE MANAGER
# =============================================================================

class EnsembleManager:
    """
    Ensemble Manager for BAEL.

    Advanced ensemble learning and model combination.
    """

    def __init__(self):
        self._model_pool = ModelPool()
        self._voting = VotingEnsemble()
        self._stacking = StackingEnsemble()
        self._diversity = DiversityAnalyzer()
        self._selector = DynamicSelector()
        self._predictions: Dict[str, Dict[str, Prediction]] = {}
        self._ensemble_type = EnsembleType.VOTING

    # -------------------------------------------------------------------------
    # MODELS
    # -------------------------------------------------------------------------

    def add_model(
        self,
        name: str,
        model_type: str = "",
        weight: float = 1.0
    ) -> Model:
        """Add a model to the ensemble."""
        return self._model_pool.add(name, model_type, weight)

    def get_model(self, model_id: str) -> Optional[Model]:
        """Get a model."""
        return self._model_pool.get(model_id)

    def set_model_weight(self, model_id: str, weight: float) -> None:
        """Set model weight."""
        self._model_pool.set_weight(model_id, weight)

    def set_model_accuracy(self, model_id: str, accuracy: float) -> None:
        """Set model accuracy."""
        self._model_pool.set_accuracy(model_id, accuracy)

    def all_models(self) -> List[Model]:
        """Get all models."""
        return self._model_pool.all_models()

    # -------------------------------------------------------------------------
    # PREDICTIONS
    # -------------------------------------------------------------------------

    def add_prediction(
        self,
        model_id: str,
        sample_id: str,
        predicted_class: str,
        probabilities: Optional[Dict[str, float]] = None
    ) -> Prediction:
        """Add a model prediction."""
        pred = Prediction(
            model_id=model_id,
            sample_id=sample_id,
            predicted_class=predicted_class,
            probabilities=probabilities or {predicted_class: 1.0},
            confidence=max(probabilities.values()) if probabilities else 1.0
        )

        if sample_id not in self._predictions:
            self._predictions[sample_id] = {}

        self._predictions[sample_id][model_id] = pred
        return pred

    def get_predictions(self, sample_id: str) -> List[Prediction]:
        """Get all predictions for a sample."""
        return list(self._predictions.get(sample_id, {}).values())

    # -------------------------------------------------------------------------
    # ENSEMBLE PREDICTION
    # -------------------------------------------------------------------------

    def predict(
        self,
        sample_id: str,
        voting_type: VotingType = VotingType.SOFT
    ) -> EnsemblePrediction:
        """Make ensemble prediction."""
        predictions = self.get_predictions(sample_id)

        if not predictions:
            return EnsemblePrediction(sample_id=sample_id)

        # Get weights
        weights = {
            m.model_id: m.weight
            for m in self._model_pool.all_models()
        }

        self._voting = VotingEnsemble(voting_type)
        return self._voting.vote(predictions, weights)

    def predict_batch(
        self,
        sample_ids: List[str],
        voting_type: VotingType = VotingType.SOFT
    ) -> List[EnsemblePrediction]:
        """Make batch predictions."""
        return [self.predict(sid, voting_type) for sid in sample_ids]

    # -------------------------------------------------------------------------
    # STACKING
    # -------------------------------------------------------------------------

    def train_stacking(
        self,
        sample_ids: List[str],
        true_labels: List[str]
    ) -> None:
        """Train stacking meta-learner."""
        model_predictions = {}

        for sample_id in sample_ids:
            for model_id, pred in self._predictions.get(sample_id, {}).items():
                if model_id not in model_predictions:
                    model_predictions[model_id] = []
                model_predictions[model_id].append(pred)

        self._stacking.train_meta(model_predictions, true_labels)

    def predict_stacking(self, sample_id: str) -> EnsemblePrediction:
        """Make stacking prediction."""
        predictions = self.get_predictions(sample_id)
        return self._stacking.predict(predictions)

    # -------------------------------------------------------------------------
    # DIVERSITY
    # -------------------------------------------------------------------------

    def analyze_diversity(self) -> DiversityReport:
        """Analyze ensemble diversity."""
        # Group predictions by model
        model_predictions: Dict[str, List[Prediction]] = {}

        for sample_preds in self._predictions.values():
            for model_id, pred in sample_preds.items():
                if model_id not in model_predictions:
                    model_predictions[model_id] = []
                model_predictions[model_id].append(pred)

        return self._diversity.pairwise_diversity(model_predictions)

    # -------------------------------------------------------------------------
    # DYNAMIC SELECTION
    # -------------------------------------------------------------------------

    def train_selector(
        self,
        sample_ids: List[str],
        true_labels: List[str]
    ) -> None:
        """Train dynamic selector."""
        model_predictions = {}

        for sample_id in sample_ids:
            for model_id, pred in self._predictions.get(sample_id, {}).items():
                if model_id not in model_predictions:
                    model_predictions[model_id] = []
                model_predictions[model_id].append(pred)

        self._selector.train(model_predictions, true_labels)

    def predict_dynamic(
        self,
        sample_id: str,
        n_models: int = 3
    ) -> EnsemblePrediction:
        """Make prediction with dynamic selection."""
        predictions = self.get_predictions(sample_id)
        selected = self._selector.select(sample_id, predictions, n_models)

        return self._voting.vote(selected)

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def weight_by_accuracy(self) -> None:
        """Weight models by their accuracy."""
        for model in self._model_pool.all_models():
            # Use accuracy as weight
            self._model_pool.set_weight(model.model_id, model.accuracy)

    def evaluate(
        self,
        sample_ids: List[str],
        true_labels: List[str]
    ) -> float:
        """Evaluate ensemble accuracy."""
        correct = 0

        for sample_id, true_label in zip(sample_ids, true_labels):
            pred = self.predict(sample_id)
            if pred.final_class == true_label:
                correct += 1

        return correct / len(sample_ids) if sample_ids else 0.0


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Ensemble Manager."""
    print("=" * 70)
    print("BAEL - ENSEMBLE MANAGER DEMO")
    print("Advanced Ensemble Learning and Model Combination")
    print("=" * 70)
    print()

    manager = EnsembleManager()

    # 1. Add Models
    print("1. ADD MODELS:")
    print("-" * 40)

    model1 = manager.add_model("decision_tree", "tree", 1.0)
    model2 = manager.add_model("random_forest", "forest", 1.0)
    model3 = manager.add_model("svm", "kernel", 1.0)
    model4 = manager.add_model("neural_net", "nn", 1.0)
    model5 = manager.add_model("naive_bayes", "bayes", 1.0)

    # Set accuracies
    manager.set_model_accuracy(model1.model_id, 0.75)
    manager.set_model_accuracy(model2.model_id, 0.82)
    manager.set_model_accuracy(model3.model_id, 0.78)
    manager.set_model_accuracy(model4.model_id, 0.85)
    manager.set_model_accuracy(model5.model_id, 0.70)

    for model in manager.all_models():
        print(f"   {model.name}: accuracy={model.accuracy:.2f}")
    print()

    # 2. Add Predictions
    print("2. ADD PREDICTIONS:")
    print("-" * 40)

    samples = ["s1", "s2", "s3", "s4", "s5"]
    true_labels = ["pos", "neg", "pos", "neg", "pos"]

    # Simulate model predictions
    for sample_id in samples:
        for model in manager.all_models():
            # Simulate prediction
            p = random.random()
            pred_class = "pos" if p > 0.5 else "neg"
            probs = {"pos": p, "neg": 1 - p}

            manager.add_prediction(model.model_id, sample_id, pred_class, probs)

    print(f"   Added predictions for {len(samples)} samples from {len(manager.all_models())} models")
    print()

    # 3. Hard Voting
    print("3. HARD VOTING:")
    print("-" * 40)

    for sample_id in samples[:2]:
        result = manager.predict(sample_id, VotingType.HARD)
        print(f"   {sample_id}: {result.final_class} (conf: {result.confidence:.2f})")
    print()

    # 4. Soft Voting
    print("4. SOFT VOTING:")
    print("-" * 40)

    for sample_id in samples[:2]:
        result = manager.predict(sample_id, VotingType.SOFT)
        print(f"   {sample_id}: {result.final_class} (conf: {result.confidence:.2f})")
        print(f"      Probabilities: {result.final_probabilities}")
    print()

    # 5. Weight by Accuracy
    print("5. WEIGHT BY ACCURACY:")
    print("-" * 40)

    manager.weight_by_accuracy()
    for model in manager.all_models():
        print(f"   {model.name}: weight={model.weight:.2f}")
    print()

    # 6. Weighted Voting
    print("6. WEIGHTED VOTING:")
    print("-" * 40)

    for sample_id in samples[:2]:
        result = manager.predict(sample_id, VotingType.WEIGHTED)
        print(f"   {sample_id}: {result.final_class} (conf: {result.confidence:.2f})")
    print()

    # 7. Train Stacking
    print("7. STACKING:")
    print("-" * 40)

    manager.train_stacking(samples, true_labels)

    for sample_id in samples[:2]:
        result = manager.predict_stacking(sample_id)
        print(f"   {sample_id}: {result.final_class} (conf: {result.confidence:.2f})")
    print()

    # 8. Diversity Analysis
    print("8. DIVERSITY ANALYSIS:")
    print("-" * 40)

    diversity = manager.analyze_diversity()
    print(f"   Average disagreement: {diversity.value:.2f}")
    print(f"   Pairwise values: {len(diversity.pairwise_values)} pairs analyzed")
    print()

    # 9. Dynamic Selection
    print("9. DYNAMIC SELECTION:")
    print("-" * 40)

    manager.train_selector(samples, true_labels)

    for sample_id in samples[:2]:
        result = manager.predict_dynamic(sample_id, n_models=3)
        print(f"   {sample_id}: {result.final_class} (using top 3 models)")
    print()

    # 10. Evaluate Ensemble
    print("10. EVALUATE ENSEMBLE:")
    print("-" * 40)

    accuracy = manager.evaluate(samples, true_labels)
    print(f"   Ensemble accuracy: {accuracy:.2f}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Ensemble Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
