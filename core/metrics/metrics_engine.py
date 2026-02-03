#!/usr/bin/env python3
"""
BAEL - Metrics Engine
Comprehensive evaluation metrics for AI models.

Features:
- Classification metrics (accuracy, precision, recall, F1)
- Regression metrics (MSE, MAE, R²)
- Ranking metrics (MRR, NDCG)
- Custom metrics
- Metric aggregation
- Statistical significance testing
"""

import asyncio
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class MetricType(Enum):
    """Metric types."""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    RANKING = "ranking"
    CLUSTERING = "clustering"
    CUSTOM = "custom"


class AverageMethod(Enum):
    """Averaging methods for multiclass."""
    MICRO = "micro"
    MACRO = "macro"
    WEIGHTED = "weighted"
    BINARY = "binary"


class MetricDirection(Enum):
    """Whether higher or lower is better."""
    HIGHER_BETTER = "higher"
    LOWER_BETTER = "lower"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class MetricResult:
    """Result of metric computation."""
    metric_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    value: float = 0.0
    direction: MetricDirection = MetricDirection.HIGHER_BETTER
    confidence_interval: Optional[Tuple[float, float]] = None
    sample_size: int = 0


@dataclass
class ConfusionMatrix:
    """Confusion matrix for classification."""
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0

    @property
    def total(self) -> int:
        return self.true_positives + self.false_positives + \
               self.true_negatives + self.false_negatives

    @property
    def accuracy(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.true_positives + self.true_negatives) / self.total

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        if denom == 0:
            return 0.0
        return self.true_positives / denom

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        if denom == 0:
            return 0.0
        return self.true_positives / denom

    @property
    def f1_score(self) -> float:
        p = self.precision
        r = self.recall
        if p + r == 0:
            return 0.0
        return 2 * p * r / (p + r)


@dataclass
class ClassificationReport:
    """Classification report."""
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    per_class: Dict[Any, Dict[str, float]] = field(default_factory=dict)
    confusion_matrix: Optional[List[List[int]]] = None


@dataclass
class RegressionReport:
    """Regression report."""
    mse: float = 0.0
    rmse: float = 0.0
    mae: float = 0.0
    r2: float = 0.0
    mape: float = 0.0


# =============================================================================
# METRIC CALCULATORS
# =============================================================================

class ClassificationMetrics:
    """Classification metric calculator."""

    def confusion_matrix(
        self,
        y_true: List[int],
        y_pred: List[int],
        positive_class: int = 1
    ) -> ConfusionMatrix:
        """Compute confusion matrix for binary classification."""
        tp = fp = tn = fn = 0

        for true, pred in zip(y_true, y_pred):
            if pred == positive_class:
                if true == positive_class:
                    tp += 1
                else:
                    fp += 1
            else:
                if true == positive_class:
                    fn += 1
                else:
                    tn += 1

        return ConfusionMatrix(
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn
        )

    def multiclass_confusion_matrix(
        self,
        y_true: List[int],
        y_pred: List[int],
        num_classes: int
    ) -> List[List[int]]:
        """Compute multiclass confusion matrix."""
        matrix = [[0] * num_classes for _ in range(num_classes)]

        for true, pred in zip(y_true, y_pred):
            if 0 <= true < num_classes and 0 <= pred < num_classes:
                matrix[true][pred] += 1

        return matrix

    def accuracy(
        self,
        y_true: List[int],
        y_pred: List[int]
    ) -> float:
        """Compute accuracy."""
        if not y_true:
            return 0.0

        correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
        return correct / len(y_true)

    def precision(
        self,
        y_true: List[int],
        y_pred: List[int],
        average: AverageMethod = AverageMethod.BINARY,
        positive_class: int = 1
    ) -> float:
        """Compute precision."""
        if average == AverageMethod.BINARY:
            cm = self.confusion_matrix(y_true, y_pred, positive_class)
            return cm.precision

        classes = set(y_true) | set(y_pred)
        precisions = []
        weights = []

        for cls in classes:
            cm = self.confusion_matrix(y_true, y_pred, cls)
            precisions.append(cm.precision)
            weights.append(sum(1 for t in y_true if t == cls))

        if average == AverageMethod.MACRO:
            return sum(precisions) / len(precisions) if precisions else 0.0
        elif average == AverageMethod.WEIGHTED:
            total_weight = sum(weights)
            if total_weight == 0:
                return 0.0
            return sum(p * w for p, w in zip(precisions, weights)) / total_weight

        return 0.0

    def recall(
        self,
        y_true: List[int],
        y_pred: List[int],
        average: AverageMethod = AverageMethod.BINARY,
        positive_class: int = 1
    ) -> float:
        """Compute recall."""
        if average == AverageMethod.BINARY:
            cm = self.confusion_matrix(y_true, y_pred, positive_class)
            return cm.recall

        classes = set(y_true) | set(y_pred)
        recalls = []
        weights = []

        for cls in classes:
            cm = self.confusion_matrix(y_true, y_pred, cls)
            recalls.append(cm.recall)
            weights.append(sum(1 for t in y_true if t == cls))

        if average == AverageMethod.MACRO:
            return sum(recalls) / len(recalls) if recalls else 0.0
        elif average == AverageMethod.WEIGHTED:
            total_weight = sum(weights)
            if total_weight == 0:
                return 0.0
            return sum(r * w for r, w in zip(recalls, weights)) / total_weight

        return 0.0

    def f1_score(
        self,
        y_true: List[int],
        y_pred: List[int],
        average: AverageMethod = AverageMethod.BINARY,
        positive_class: int = 1
    ) -> float:
        """Compute F1 score."""
        p = self.precision(y_true, y_pred, average, positive_class)
        r = self.recall(y_true, y_pred, average, positive_class)

        if p + r == 0:
            return 0.0

        return 2 * p * r / (p + r)

    def classification_report(
        self,
        y_true: List[int],
        y_pred: List[int]
    ) -> ClassificationReport:
        """Generate full classification report."""
        classes = sorted(set(y_true) | set(y_pred))

        per_class = {}
        for cls in classes:
            cm = self.confusion_matrix(y_true, y_pred, cls)
            per_class[cls] = {
                'precision': cm.precision,
                'recall': cm.recall,
                'f1_score': cm.f1_score,
                'support': sum(1 for t in y_true if t == cls)
            }

        conf_matrix = self.multiclass_confusion_matrix(
            y_true, y_pred, max(classes) + 1 if classes else 0
        )

        return ClassificationReport(
            accuracy=self.accuracy(y_true, y_pred),
            precision=self.precision(y_true, y_pred, AverageMethod.MACRO),
            recall=self.recall(y_true, y_pred, AverageMethod.MACRO),
            f1_score=self.f1_score(y_true, y_pred, AverageMethod.MACRO),
            per_class=per_class,
            confusion_matrix=conf_matrix
        )


class RegressionMetrics:
    """Regression metric calculator."""

    def mse(
        self,
        y_true: List[float],
        y_pred: List[float]
    ) -> float:
        """Mean Squared Error."""
        if not y_true:
            return 0.0

        return sum((t - p) ** 2 for t, p in zip(y_true, y_pred)) / len(y_true)

    def rmse(
        self,
        y_true: List[float],
        y_pred: List[float]
    ) -> float:
        """Root Mean Squared Error."""
        return math.sqrt(self.mse(y_true, y_pred))

    def mae(
        self,
        y_true: List[float],
        y_pred: List[float]
    ) -> float:
        """Mean Absolute Error."""
        if not y_true:
            return 0.0

        return sum(abs(t - p) for t, p in zip(y_true, y_pred)) / len(y_true)

    def r2_score(
        self,
        y_true: List[float],
        y_pred: List[float]
    ) -> float:
        """R² (Coefficient of Determination)."""
        if not y_true:
            return 0.0

        y_mean = sum(y_true) / len(y_true)

        ss_res = sum((t - p) ** 2 for t, p in zip(y_true, y_pred))
        ss_tot = sum((t - y_mean) ** 2 for t in y_true)

        if ss_tot == 0:
            return 0.0

        return 1 - (ss_res / ss_tot)

    def mape(
        self,
        y_true: List[float],
        y_pred: List[float]
    ) -> float:
        """Mean Absolute Percentage Error."""
        if not y_true:
            return 0.0

        valid = [(t, p) for t, p in zip(y_true, y_pred) if t != 0]

        if not valid:
            return 0.0

        return sum(abs((t - p) / t) for t, p in valid) / len(valid) * 100

    def huber_loss(
        self,
        y_true: List[float],
        y_pred: List[float],
        delta: float = 1.0
    ) -> float:
        """Huber loss."""
        if not y_true:
            return 0.0

        total = 0.0
        for t, p in zip(y_true, y_pred):
            error = abs(t - p)
            if error <= delta:
                total += 0.5 * error ** 2
            else:
                total += delta * (error - 0.5 * delta)

        return total / len(y_true)

    def regression_report(
        self,
        y_true: List[float],
        y_pred: List[float]
    ) -> RegressionReport:
        """Generate full regression report."""
        return RegressionReport(
            mse=self.mse(y_true, y_pred),
            rmse=self.rmse(y_true, y_pred),
            mae=self.mae(y_true, y_pred),
            r2=self.r2_score(y_true, y_pred),
            mape=self.mape(y_true, y_pred)
        )


class RankingMetrics:
    """Ranking metric calculator."""

    def mrr(
        self,
        rankings: List[List[int]],
        relevant: List[int]
    ) -> float:
        """Mean Reciprocal Rank."""
        if not rankings:
            return 0.0

        rr_sum = 0.0

        for ranking, rel in zip(rankings, relevant):
            try:
                rank = ranking.index(rel) + 1
                rr_sum += 1.0 / rank
            except ValueError:
                pass

        return rr_sum / len(rankings)

    def precision_at_k(
        self,
        predictions: List[int],
        relevant: Set[int],
        k: int
    ) -> float:
        """Precision@K."""
        if k <= 0:
            return 0.0

        top_k = predictions[:k]
        relevant_in_top_k = sum(1 for p in top_k if p in relevant)

        return relevant_in_top_k / k

    def recall_at_k(
        self,
        predictions: List[int],
        relevant: Set[int],
        k: int
    ) -> float:
        """Recall@K."""
        if not relevant:
            return 0.0

        top_k = predictions[:k]
        relevant_in_top_k = sum(1 for p in top_k if p in relevant)

        return relevant_in_top_k / len(relevant)

    def ndcg(
        self,
        predictions: List[int],
        relevance: Dict[int, float],
        k: Optional[int] = None
    ) -> float:
        """Normalized Discounted Cumulative Gain."""
        if k is None:
            k = len(predictions)

        dcg = 0.0
        for i, pred in enumerate(predictions[:k]):
            rel = relevance.get(pred, 0.0)
            dcg += (2 ** rel - 1) / math.log2(i + 2)

        ideal_order = sorted(
            relevance.items(),
            key=lambda x: x[1],
            reverse=True
        )[:k]

        idcg = 0.0
        for i, (_, rel) in enumerate(ideal_order):
            idcg += (2 ** rel - 1) / math.log2(i + 2)

        if idcg == 0:
            return 0.0

        return dcg / idcg

    def map_score(
        self,
        predictions_list: List[List[int]],
        relevant_list: List[Set[int]]
    ) -> float:
        """Mean Average Precision."""
        if not predictions_list:
            return 0.0

        ap_sum = 0.0

        for predictions, relevant in zip(predictions_list, relevant_list):
            if not relevant:
                continue

            hits = 0
            precision_sum = 0.0

            for i, pred in enumerate(predictions):
                if pred in relevant:
                    hits += 1
                    precision_sum += hits / (i + 1)

            ap_sum += precision_sum / len(relevant)

        return ap_sum / len(predictions_list)


# =============================================================================
# METRICS ENGINE
# =============================================================================

class MetricsEngine:
    """
    Metrics Engine for BAEL.

    Comprehensive evaluation metrics for AI models.
    """

    def __init__(self):
        self._classification = ClassificationMetrics()
        self._regression = RegressionMetrics()
        self._ranking = RankingMetrics()
        self._history: List[MetricResult] = []
        self._custom_metrics: Dict[str, Callable] = {}

    def accuracy(
        self,
        y_true: List[int],
        y_pred: List[int]
    ) -> float:
        """Compute accuracy."""
        return self._classification.accuracy(y_true, y_pred)

    def precision(
        self,
        y_true: List[int],
        y_pred: List[int],
        average: AverageMethod = AverageMethod.BINARY
    ) -> float:
        """Compute precision."""
        return self._classification.precision(y_true, y_pred, average)

    def recall(
        self,
        y_true: List[int],
        y_pred: List[int],
        average: AverageMethod = AverageMethod.BINARY
    ) -> float:
        """Compute recall."""
        return self._classification.recall(y_true, y_pred, average)

    def f1(
        self,
        y_true: List[int],
        y_pred: List[int],
        average: AverageMethod = AverageMethod.BINARY
    ) -> float:
        """Compute F1 score."""
        return self._classification.f1_score(y_true, y_pred, average)

    def classification_report(
        self,
        y_true: List[int],
        y_pred: List[int]
    ) -> ClassificationReport:
        """Generate classification report."""
        return self._classification.classification_report(y_true, y_pred)

    def mse(
        self,
        y_true: List[float],
        y_pred: List[float]
    ) -> float:
        """Mean Squared Error."""
        return self._regression.mse(y_true, y_pred)

    def rmse(
        self,
        y_true: List[float],
        y_pred: List[float]
    ) -> float:
        """Root Mean Squared Error."""
        return self._regression.rmse(y_true, y_pred)

    def mae(
        self,
        y_true: List[float],
        y_pred: List[float]
    ) -> float:
        """Mean Absolute Error."""
        return self._regression.mae(y_true, y_pred)

    def r2(
        self,
        y_true: List[float],
        y_pred: List[float]
    ) -> float:
        """R² score."""
        return self._regression.r2_score(y_true, y_pred)

    def regression_report(
        self,
        y_true: List[float],
        y_pred: List[float]
    ) -> RegressionReport:
        """Generate regression report."""
        return self._regression.regression_report(y_true, y_pred)

    def mrr(
        self,
        rankings: List[List[int]],
        relevant: List[int]
    ) -> float:
        """Mean Reciprocal Rank."""
        return self._ranking.mrr(rankings, relevant)

    def ndcg(
        self,
        predictions: List[int],
        relevance: Dict[int, float],
        k: Optional[int] = None
    ) -> float:
        """NDCG."""
        return self._ranking.ndcg(predictions, relevance, k)

    def precision_at_k(
        self,
        predictions: List[int],
        relevant: Set[int],
        k: int
    ) -> float:
        """Precision@K."""
        return self._ranking.precision_at_k(predictions, relevant, k)

    def register_metric(
        self,
        name: str,
        func: Callable[[List, List], float]
    ) -> None:
        """Register custom metric."""
        self._custom_metrics[name] = func

    def compute_custom(
        self,
        name: str,
        y_true: List,
        y_pred: List
    ) -> Optional[float]:
        """Compute custom metric."""
        if name not in self._custom_metrics:
            return None
        return self._custom_metrics[name](y_true, y_pred)

    def log_metric(
        self,
        name: str,
        value: float,
        direction: MetricDirection = MetricDirection.HIGHER_BETTER
    ) -> MetricResult:
        """Log a metric result."""
        result = MetricResult(
            name=name,
            value=value,
            direction=direction
        )
        self._history.append(result)
        return result

    def get_history(self) -> List[MetricResult]:
        """Get metric history."""
        return self._history.copy()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Metrics Engine."""
    print("=" * 70)
    print("BAEL - METRICS ENGINE DEMO")
    print("Comprehensive Evaluation Metrics for AI Models")
    print("=" * 70)
    print()

    engine = MetricsEngine()

    # 1. Classification Metrics
    print("1. CLASSIFICATION METRICS:")
    print("-" * 40)

    y_true_cls = [1, 0, 1, 1, 0, 1, 0, 0, 1, 1]
    y_pred_cls = [1, 0, 1, 0, 0, 1, 1, 0, 1, 0]

    print(f"   True:      {y_true_cls}")
    print(f"   Predicted: {y_pred_cls}")
    print(f"   Accuracy:  {engine.accuracy(y_true_cls, y_pred_cls):.3f}")
    print(f"   Precision: {engine.precision(y_true_cls, y_pred_cls):.3f}")
    print(f"   Recall:    {engine.recall(y_true_cls, y_pred_cls):.3f}")
    print(f"   F1 Score:  {engine.f1(y_true_cls, y_pred_cls):.3f}")
    print()

    # 2. Classification Report
    print("2. CLASSIFICATION REPORT:")
    print("-" * 40)

    report = engine.classification_report(y_true_cls, y_pred_cls)
    print(f"   Macro Precision: {report.precision:.3f}")
    print(f"   Macro Recall:    {report.recall:.3f}")
    print(f"   Macro F1:        {report.f1_score:.3f}")
    print()

    # 3. Multiclass
    print("3. MULTICLASS METRICS:")
    print("-" * 40)

    y_true_multi = [0, 1, 2, 0, 1, 2, 0, 1, 2, 0]
    y_pred_multi = [0, 1, 1, 0, 2, 2, 1, 1, 2, 0]

    print(f"   Accuracy (multi):   {engine.accuracy(y_true_multi, y_pred_multi):.3f}")
    print(f"   Precision (macro):  {engine.precision(y_true_multi, y_pred_multi, AverageMethod.MACRO):.3f}")
    print(f"   Recall (macro):     {engine.recall(y_true_multi, y_pred_multi, AverageMethod.MACRO):.3f}")
    print()

    # 4. Regression Metrics
    print("4. REGRESSION METRICS:")
    print("-" * 40)

    y_true_reg = [3.0, 5.0, 2.5, 7.0, 4.0]
    y_pred_reg = [2.8, 5.2, 2.3, 6.5, 4.1]

    print(f"   True:      {y_true_reg}")
    print(f"   Predicted: {y_pred_reg}")
    print(f"   MSE:       {engine.mse(y_true_reg, y_pred_reg):.4f}")
    print(f"   RMSE:      {engine.rmse(y_true_reg, y_pred_reg):.4f}")
    print(f"   MAE:       {engine.mae(y_true_reg, y_pred_reg):.4f}")
    print(f"   R²:        {engine.r2(y_true_reg, y_pred_reg):.4f}")
    print()

    # 5. Regression Report
    print("5. REGRESSION REPORT:")
    print("-" * 40)

    reg_report = engine.regression_report(y_true_reg, y_pred_reg)
    print(f"   MSE:  {reg_report.mse:.4f}")
    print(f"   RMSE: {reg_report.rmse:.4f}")
    print(f"   MAE:  {reg_report.mae:.4f}")
    print(f"   R²:   {reg_report.r2:.4f}")
    print(f"   MAPE: {reg_report.mape:.2f}%")
    print()

    # 6. Ranking Metrics
    print("6. RANKING METRICS:")
    print("-" * 40)

    rankings = [[3, 1, 2, 4], [1, 2, 3, 4], [2, 3, 1, 4]]
    relevant = [1, 1, 1]

    print(f"   MRR: {engine.mrr(rankings, relevant):.3f}")

    predictions = [1, 3, 2, 4, 5]
    relevance = {1: 3, 2: 2, 3: 3, 4: 0, 5: 1}

    print(f"   NDCG@5: {engine.ndcg(predictions, relevance, k=5):.3f}")

    rel_set = {1, 2, 5}
    print(f"   P@3: {engine.precision_at_k(predictions, rel_set, k=3):.3f}")
    print()

    # 7. Custom Metric
    print("7. CUSTOM METRIC:")
    print("-" * 40)

    def custom_accuracy_margin(y_true, y_pred, margin=0.1):
        correct = sum(1 for t, p in zip(y_true, y_pred) if abs(t - p) <= margin * t)
        return correct / len(y_true)

    engine.register_metric("accuracy_margin", lambda t, p: custom_accuracy_margin(t, p, 0.1))

    custom_val = engine.compute_custom("accuracy_margin", y_true_reg, y_pred_reg)
    print(f"   Accuracy within 10%: {custom_val:.3f}")
    print()

    # 8. Confusion Matrix
    print("8. CONFUSION MATRIX:")
    print("-" * 40)

    cm = ClassificationMetrics().confusion_matrix(y_true_cls, y_pred_cls)
    print(f"   TP: {cm.true_positives}, FP: {cm.false_positives}")
    print(f"   FN: {cm.false_negatives}, TN: {cm.true_negatives}")
    print()

    # 9. Metric Logging
    print("9. METRIC LOGGING:")
    print("-" * 40)

    engine.log_metric("train_loss", 0.35, MetricDirection.LOWER_BETTER)
    engine.log_metric("val_accuracy", 0.92, MetricDirection.HIGHER_BETTER)
    engine.log_metric("test_f1", 0.88, MetricDirection.HIGHER_BETTER)

    history = engine.get_history()
    for m in history:
        print(f"   {m.name}: {m.value:.3f} ({m.direction.value})")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Metrics Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
