#!/usr/bin/env python3
"""
BAEL - Machine Learning Pipeline
Advanced ML pipeline orchestration and execution.

Features:
- Pipeline stages (preprocessing, feature engineering, training, evaluation)
- Data transformers
- Feature selectors
- Model wrappers
- Cross-validation
- Hyperparameter tuning
- Model serialization
- Pipeline persistence
- Experiment tracking
- Metrics calculation
"""

import asyncio
import json
import logging
import math
import pickle
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class StageType(Enum):
    """Pipeline stage types."""
    PREPROCESSING = "preprocessing"
    FEATURE_ENGINEERING = "feature_engineering"
    FEATURE_SELECTION = "feature_selection"
    TRAINING = "training"
    EVALUATION = "evaluation"
    POSTPROCESSING = "postprocessing"


class MetricType(Enum):
    """Metric types."""
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1 = "f1"
    MSE = "mse"
    RMSE = "rmse"
    MAE = "mae"
    R2 = "r2"
    AUC = "auc"
    LOG_LOSS = "log_loss"


class TaskType(Enum):
    """ML task types."""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    ANOMALY_DETECTION = "anomaly_detection"


class SplitStrategy(Enum):
    """Data split strategies."""
    RANDOM = "random"
    STRATIFIED = "stratified"
    TIME_SERIES = "time_series"
    K_FOLD = "k_fold"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class DataSample:
    """A single data sample."""
    features: List[float]
    label: Optional[Any] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Dataset:
    """Dataset container."""
    samples: List[DataSample] = field(default_factory=list)
    feature_names: List[str] = field(default_factory=list)
    label_name: str = "target"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def X(self) -> List[List[float]]:
        return [s.features for s in self.samples]

    @property
    def y(self) -> List[Any]:
        return [s.label for s in self.samples]

    def __len__(self) -> int:
        return len(self.samples)


@dataclass
class SplitResult:
    """Train/test split result."""
    train: Dataset
    test: Dataset
    validation: Optional[Dataset] = None


@dataclass
class PredictionResult:
    """Model prediction result."""
    predictions: List[Any]
    probabilities: Optional[List[List[float]]] = None
    confidence: Optional[List[float]] = None


@dataclass
class EvaluationResult:
    """Model evaluation result."""
    metrics: Dict[str, float]
    confusion_matrix: Optional[List[List[int]]] = None
    predictions: Optional[PredictionResult] = None


@dataclass
class ExperimentRun:
    """Experiment run record."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    pipeline_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str = "pending"
    artifacts: Dict[str, str] = field(default_factory=dict)


@dataclass
class HyperparameterSpace:
    """Hyperparameter search space."""
    name: str
    values: List[Any] = field(default_factory=list)
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    log_scale: bool = False


# =============================================================================
# TRANSFORMERS
# =============================================================================

class Transformer(ABC):
    """Base transformer."""

    @abstractmethod
    def fit(self, X: List[List[float]], y: Optional[List[Any]] = None) -> 'Transformer':
        """Fit transformer to data."""
        pass

    @abstractmethod
    def transform(self, X: List[List[float]]) -> List[List[float]]:
        """Transform data."""
        pass

    def fit_transform(self, X: List[List[float]], y: Optional[List[Any]] = None) -> List[List[float]]:
        """Fit and transform data."""
        self.fit(X, y)
        return self.transform(X)


class StandardScaler(Transformer):
    """Standardize features by removing mean and scaling to unit variance."""

    def __init__(self):
        self.means: List[float] = []
        self.stds: List[float] = []

    def fit(self, X: List[List[float]], y: Optional[List[Any]] = None) -> 'StandardScaler':
        if not X:
            return self

        n_features = len(X[0])
        n_samples = len(X)

        self.means = [0.0] * n_features
        self.stds = [0.0] * n_features

        # Calculate means
        for row in X:
            for i, val in enumerate(row):
                self.means[i] += val
        self.means = [m / n_samples for m in self.means]

        # Calculate stds
        for row in X:
            for i, val in enumerate(row):
                self.stds[i] += (val - self.means[i]) ** 2
        self.stds = [math.sqrt(s / n_samples) if s > 0 else 1.0 for s in self.stds]

        return self

    def transform(self, X: List[List[float]]) -> List[List[float]]:
        result = []
        for row in X:
            scaled = []
            for i, val in enumerate(row):
                if self.stds[i] > 0:
                    scaled.append((val - self.means[i]) / self.stds[i])
                else:
                    scaled.append(val - self.means[i])
            result.append(scaled)
        return result


class MinMaxScaler(Transformer):
    """Scale features to a given range."""

    def __init__(self, feature_range: Tuple[float, float] = (0, 1)):
        self.feature_range = feature_range
        self.mins: List[float] = []
        self.maxs: List[float] = []

    def fit(self, X: List[List[float]], y: Optional[List[Any]] = None) -> 'MinMaxScaler':
        if not X:
            return self

        n_features = len(X[0])
        self.mins = [float('inf')] * n_features
        self.maxs = [float('-inf')] * n_features

        for row in X:
            for i, val in enumerate(row):
                self.mins[i] = min(self.mins[i], val)
                self.maxs[i] = max(self.maxs[i], val)

        return self

    def transform(self, X: List[List[float]]) -> List[List[float]]:
        result = []
        min_range, max_range = self.feature_range

        for row in X:
            scaled = []
            for i, val in enumerate(row):
                range_val = self.maxs[i] - self.mins[i]
                if range_val > 0:
                    normalized = (val - self.mins[i]) / range_val
                    scaled.append(normalized * (max_range - min_range) + min_range)
                else:
                    scaled.append(min_range)
            result.append(scaled)

        return result


class PolynomialFeatures(Transformer):
    """Generate polynomial features."""

    def __init__(self, degree: int = 2, include_bias: bool = True):
        self.degree = degree
        self.include_bias = include_bias

    def fit(self, X: List[List[float]], y: Optional[List[Any]] = None) -> 'PolynomialFeatures':
        return self

    def transform(self, X: List[List[float]]) -> List[List[float]]:
        result = []

        for row in X:
            features = []

            if self.include_bias:
                features.append(1.0)

            # Add original features
            features.extend(row)

            # Add polynomial features
            if self.degree >= 2:
                for i in range(len(row)):
                    for j in range(i, len(row)):
                        features.append(row[i] * row[j])

            if self.degree >= 3:
                for i in range(len(row)):
                    for j in range(i, len(row)):
                        for k in range(j, len(row)):
                            features.append(row[i] * row[j] * row[k])

            result.append(features)

        return result


class PCA(Transformer):
    """Principal Component Analysis (simplified)."""

    def __init__(self, n_components: int = 2):
        self.n_components = n_components
        self.components: List[List[float]] = []
        self.mean: List[float] = []

    def fit(self, X: List[List[float]], y: Optional[List[Any]] = None) -> 'PCA':
        if not X:
            return self

        n_features = len(X[0])
        n_samples = len(X)

        # Calculate mean
        self.mean = [0.0] * n_features
        for row in X:
            for i, val in enumerate(row):
                self.mean[i] += val
        self.mean = [m / n_samples for m in self.mean]

        # Center data
        centered = []
        for row in X:
            centered.append([row[i] - self.mean[i] for i in range(n_features)])

        # Compute covariance matrix (simplified)
        cov = [[0.0] * n_features for _ in range(n_features)]
        for row in centered:
            for i in range(n_features):
                for j in range(n_features):
                    cov[i][j] += row[i] * row[j]

        for i in range(n_features):
            for j in range(n_features):
                cov[i][j] /= (n_samples - 1)

        # Power iteration for eigenvectors (simplified)
        self.components = []
        for _ in range(min(self.n_components, n_features)):
            v = [random.random() for _ in range(n_features)]

            for _ in range(100):  # Iterations
                # Matrix-vector multiplication
                new_v = [0.0] * n_features
                for i in range(n_features):
                    for j in range(n_features):
                        new_v[i] += cov[i][j] * v[j]

                # Normalize
                norm = math.sqrt(sum(x**2 for x in new_v))
                v = [x / norm if norm > 0 else x for x in new_v]

            self.components.append(v)

            # Deflation
            for i in range(n_features):
                for j in range(n_features):
                    cov[i][j] -= v[i] * v[j]

        return self

    def transform(self, X: List[List[float]]) -> List[List[float]]:
        result = []

        for row in X:
            centered = [row[i] - self.mean[i] for i in range(len(row))]

            projected = []
            for component in self.components:
                dot = sum(centered[i] * component[i] for i in range(len(centered)))
                projected.append(dot)

            result.append(projected)

        return result


# =============================================================================
# FEATURE SELECTORS
# =============================================================================

class FeatureSelector(ABC):
    """Base feature selector."""

    @abstractmethod
    def fit(self, X: List[List[float]], y: List[Any]) -> 'FeatureSelector':
        pass

    @abstractmethod
    def transform(self, X: List[List[float]]) -> List[List[float]]:
        pass

    @abstractmethod
    def get_support(self) -> List[int]:
        """Get selected feature indices."""
        pass


class VarianceThreshold(FeatureSelector):
    """Remove features with low variance."""

    def __init__(self, threshold: float = 0.0):
        self.threshold = threshold
        self.variances: List[float] = []
        self.selected_indices: List[int] = []

    def fit(self, X: List[List[float]], y: List[Any]) -> 'VarianceThreshold':
        if not X:
            return self

        n_features = len(X[0])
        n_samples = len(X)

        # Calculate variances
        means = [0.0] * n_features
        for row in X:
            for i, val in enumerate(row):
                means[i] += val
        means = [m / n_samples for m in means]

        self.variances = [0.0] * n_features
        for row in X:
            for i, val in enumerate(row):
                self.variances[i] += (val - means[i]) ** 2
        self.variances = [v / n_samples for v in self.variances]

        # Select features
        self.selected_indices = [
            i for i, v in enumerate(self.variances) if v > self.threshold
        ]

        return self

    def transform(self, X: List[List[float]]) -> List[List[float]]:
        return [[row[i] for i in self.selected_indices] for row in X]

    def get_support(self) -> List[int]:
        return self.selected_indices


class SelectKBest(FeatureSelector):
    """Select K best features based on correlation with target."""

    def __init__(self, k: int = 10):
        self.k = k
        self.scores: List[float] = []
        self.selected_indices: List[int] = []

    def fit(self, X: List[List[float]], y: List[Any]) -> 'SelectKBest':
        if not X:
            return self

        n_features = len(X[0])

        # Calculate correlation scores
        self.scores = []
        y_numeric = [float(v) if isinstance(v, (int, float)) else hash(str(v)) for v in y]

        for j in range(n_features):
            feature_col = [row[j] for row in X]

            # Pearson correlation (simplified)
            mean_x = sum(feature_col) / len(feature_col)
            mean_y = sum(y_numeric) / len(y_numeric)

            num = sum((feature_col[i] - mean_x) * (y_numeric[i] - mean_y) for i in range(len(X)))
            den_x = math.sqrt(sum((x - mean_x) ** 2 for x in feature_col))
            den_y = math.sqrt(sum((y - mean_y) ** 2 for y in y_numeric))

            if den_x > 0 and den_y > 0:
                corr = abs(num / (den_x * den_y))
            else:
                corr = 0.0

            self.scores.append(corr)

        # Select top k
        indices_scores = [(i, s) for i, s in enumerate(self.scores)]
        indices_scores.sort(key=lambda x: x[1], reverse=True)
        self.selected_indices = sorted([i for i, _ in indices_scores[:self.k]])

        return self

    def transform(self, X: List[List[float]]) -> List[List[float]]:
        return [[row[i] for i in self.selected_indices] for row in X]

    def get_support(self) -> List[int]:
        return self.selected_indices


# =============================================================================
# MODELS
# =============================================================================

class Model(ABC):
    """Base model."""

    @abstractmethod
    def fit(self, X: List[List[float]], y: List[Any]) -> 'Model':
        pass

    @abstractmethod
    def predict(self, X: List[List[float]]) -> List[Any]:
        pass


class LinearRegression(Model):
    """Simple linear regression."""

    def __init__(self, learning_rate: float = 0.01, iterations: int = 1000):
        self.learning_rate = learning_rate
        self.iterations = iterations
        self.weights: List[float] = []
        self.bias: float = 0.0

    def fit(self, X: List[List[float]], y: List[Any]) -> 'LinearRegression':
        if not X:
            return self

        n_samples = len(X)
        n_features = len(X[0])

        self.weights = [0.0] * n_features
        self.bias = 0.0

        y_float = [float(v) for v in y]

        for _ in range(self.iterations):
            # Predictions
            predictions = []
            for row in X:
                pred = self.bias + sum(self.weights[i] * row[i] for i in range(n_features))
                predictions.append(pred)

            # Gradients
            d_weights = [0.0] * n_features
            d_bias = 0.0

            for i in range(n_samples):
                error = predictions[i] - y_float[i]
                d_bias += error
                for j in range(n_features):
                    d_weights[j] += error * X[i][j]

            # Update
            self.bias -= self.learning_rate * d_bias / n_samples
            for j in range(n_features):
                self.weights[j] -= self.learning_rate * d_weights[j] / n_samples

        return self

    def predict(self, X: List[List[float]]) -> List[float]:
        predictions = []
        for row in X:
            pred = self.bias + sum(self.weights[i] * row[i] for i in range(len(row)))
            predictions.append(pred)
        return predictions


class LogisticRegression(Model):
    """Simple logistic regression."""

    def __init__(self, learning_rate: float = 0.01, iterations: int = 1000):
        self.learning_rate = learning_rate
        self.iterations = iterations
        self.weights: List[float] = []
        self.bias: float = 0.0
        self.classes: List[Any] = []

    @staticmethod
    def sigmoid(z: float) -> float:
        if z < -500:
            return 0.0
        if z > 500:
            return 1.0
        return 1.0 / (1.0 + math.exp(-z))

    def fit(self, X: List[List[float]], y: List[Any]) -> 'LogisticRegression':
        if not X:
            return self

        self.classes = list(set(y))

        n_samples = len(X)
        n_features = len(X[0])

        self.weights = [0.0] * n_features
        self.bias = 0.0

        # Binary encoding
        y_binary = [1.0 if v == self.classes[1] else 0.0 for v in y] if len(self.classes) == 2 else [float(v) for v in y]

        for _ in range(self.iterations):
            # Predictions
            predictions = []
            for row in X:
                z = self.bias + sum(self.weights[i] * row[i] for i in range(n_features))
                predictions.append(self.sigmoid(z))

            # Gradients
            d_weights = [0.0] * n_features
            d_bias = 0.0

            for i in range(n_samples):
                error = predictions[i] - y_binary[i]
                d_bias += error
                for j in range(n_features):
                    d_weights[j] += error * X[i][j]

            # Update
            self.bias -= self.learning_rate * d_bias / n_samples
            for j in range(n_features):
                self.weights[j] -= self.learning_rate * d_weights[j] / n_samples

        return self

    def predict(self, X: List[List[float]]) -> List[Any]:
        predictions = []
        for row in X:
            z = self.bias + sum(self.weights[i] * row[i] for i in range(len(row)))
            prob = self.sigmoid(z)
            if len(self.classes) == 2:
                predictions.append(self.classes[1] if prob >= 0.5 else self.classes[0])
            else:
                predictions.append(1 if prob >= 0.5 else 0)
        return predictions

    def predict_proba(self, X: List[List[float]]) -> List[List[float]]:
        probas = []
        for row in X:
            z = self.bias + sum(self.weights[i] * row[i] for i in range(len(row)))
            p = self.sigmoid(z)
            probas.append([1 - p, p])
        return probas


class KNeighborsClassifier(Model):
    """K-Nearest Neighbors classifier."""

    def __init__(self, k: int = 5):
        self.k = k
        self.X_train: List[List[float]] = []
        self.y_train: List[Any] = []

    def fit(self, X: List[List[float]], y: List[Any]) -> 'KNeighborsClassifier':
        self.X_train = X
        self.y_train = y
        return self

    def predict(self, X: List[List[float]]) -> List[Any]:
        predictions = []

        for row in X:
            # Calculate distances
            distances = []
            for i, train_row in enumerate(self.X_train):
                dist = math.sqrt(sum((row[j] - train_row[j]) ** 2 for j in range(len(row))))
                distances.append((dist, self.y_train[i]))

            # Get k nearest
            distances.sort(key=lambda x: x[0])
            k_nearest = distances[:self.k]

            # Vote
            votes = defaultdict(int)
            for _, label in k_nearest:
                votes[label] += 1

            predictions.append(max(votes.keys(), key=lambda x: votes[x]))

        return predictions


class DecisionTree(Model):
    """Simple decision tree."""

    def __init__(self, max_depth: int = 10, min_samples_split: int = 2):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.tree: Optional[Dict] = None

    def fit(self, X: List[List[float]], y: List[Any]) -> 'DecisionTree':
        self.tree = self._build_tree(X, y, depth=0)
        return self

    def _build_tree(self, X: List[List[float]], y: List[Any], depth: int) -> Dict:
        if len(set(y)) == 1:
            return {"leaf": True, "value": y[0]}

        if depth >= self.max_depth or len(y) < self.min_samples_split:
            return {"leaf": True, "value": max(set(y), key=y.count)}

        # Find best split
        best_feature = 0
        best_threshold = 0.0
        best_gain = -float('inf')

        n_features = len(X[0]) if X else 0

        for feature in range(n_features):
            values = sorted(set(row[feature] for row in X))

            for i in range(len(values) - 1):
                threshold = (values[i] + values[i + 1]) / 2

                left_y = [y[j] for j in range(len(X)) if X[j][feature] <= threshold]
                right_y = [y[j] for j in range(len(X)) if X[j][feature] > threshold]

                if not left_y or not right_y:
                    continue

                gain = self._information_gain(y, left_y, right_y)

                if gain > best_gain:
                    best_gain = gain
                    best_feature = feature
                    best_threshold = threshold

        # Split data
        left_X = [X[i] for i in range(len(X)) if X[i][best_feature] <= best_threshold]
        left_y = [y[i] for i in range(len(X)) if X[i][best_feature] <= best_threshold]
        right_X = [X[i] for i in range(len(X)) if X[i][best_feature] > best_threshold]
        right_y = [y[i] for i in range(len(X)) if X[i][best_feature] > best_threshold]

        if not left_X or not right_X:
            return {"leaf": True, "value": max(set(y), key=y.count)}

        return {
            "leaf": False,
            "feature": best_feature,
            "threshold": best_threshold,
            "left": self._build_tree(left_X, left_y, depth + 1),
            "right": self._build_tree(right_X, right_y, depth + 1)
        }

    def _information_gain(self, parent: List, left: List, right: List) -> float:
        def entropy(y: List) -> float:
            counts = defaultdict(int)
            for v in y:
                counts[v] += 1

            total = len(y)
            return -sum((c / total) * math.log2(c / total + 1e-10) for c in counts.values())

        n = len(parent)
        n_left = len(left)
        n_right = len(right)

        return entropy(parent) - (n_left / n * entropy(left) + n_right / n * entropy(right))

    def predict(self, X: List[List[float]]) -> List[Any]:
        return [self._predict_one(row, self.tree) for row in X]

    def _predict_one(self, row: List[float], node: Dict) -> Any:
        if node["leaf"]:
            return node["value"]

        if row[node["feature"]] <= node["threshold"]:
            return self._predict_one(row, node["left"])
        else:
            return self._predict_one(row, node["right"])


# =============================================================================
# METRICS
# =============================================================================

class MetricsCalculator:
    """Calculate evaluation metrics."""

    @staticmethod
    def accuracy(y_true: List[Any], y_pred: List[Any]) -> float:
        correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
        return correct / len(y_true) if y_true else 0.0

    @staticmethod
    def precision(y_true: List[Any], y_pred: List[Any], pos_label: Any = 1) -> float:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == pos_label and p == pos_label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != pos_label and p == pos_label)
        return tp / (tp + fp) if (tp + fp) > 0 else 0.0

    @staticmethod
    def recall(y_true: List[Any], y_pred: List[Any], pos_label: Any = 1) -> float:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == pos_label and p == pos_label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == pos_label and p != pos_label)
        return tp / (tp + fn) if (tp + fn) > 0 else 0.0

    @staticmethod
    def f1(y_true: List[Any], y_pred: List[Any], pos_label: Any = 1) -> float:
        p = MetricsCalculator.precision(y_true, y_pred, pos_label)
        r = MetricsCalculator.recall(y_true, y_pred, pos_label)
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @staticmethod
    def mse(y_true: List[float], y_pred: List[float]) -> float:
        return sum((t - p) ** 2 for t, p in zip(y_true, y_pred)) / len(y_true) if y_true else 0.0

    @staticmethod
    def rmse(y_true: List[float], y_pred: List[float]) -> float:
        return math.sqrt(MetricsCalculator.mse(y_true, y_pred))

    @staticmethod
    def mae(y_true: List[float], y_pred: List[float]) -> float:
        return sum(abs(t - p) for t, p in zip(y_true, y_pred)) / len(y_true) if y_true else 0.0

    @staticmethod
    def r2(y_true: List[float], y_pred: List[float]) -> float:
        mean_true = sum(y_true) / len(y_true) if y_true else 0.0
        ss_tot = sum((t - mean_true) ** 2 for t in y_true)
        ss_res = sum((t - p) ** 2 for t, p in zip(y_true, y_pred))
        return 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    @staticmethod
    def confusion_matrix(y_true: List[Any], y_pred: List[Any]) -> Tuple[List[List[int]], List[Any]]:
        classes = sorted(set(y_true) | set(y_pred))
        class_to_idx = {c: i for i, c in enumerate(classes)}

        n_classes = len(classes)
        matrix = [[0] * n_classes for _ in range(n_classes)]

        for t, p in zip(y_true, y_pred):
            matrix[class_to_idx[t]][class_to_idx[p]] += 1

        return matrix, classes


# =============================================================================
# DATA SPLITTER
# =============================================================================

class DataSplitter:
    """Split data into train/test sets."""

    @staticmethod
    def train_test_split(
        dataset: Dataset,
        test_size: float = 0.2,
        random_state: Optional[int] = None,
        stratify: bool = False
    ) -> SplitResult:
        if random_state is not None:
            random.seed(random_state)

        samples = dataset.samples.copy()

        if stratify:
            # Group by label
            label_groups: Dict[Any, List[DataSample]] = defaultdict(list)
            for sample in samples:
                label_groups[sample.label].append(sample)

            train_samples = []
            test_samples = []

            for label, group in label_groups.items():
                random.shuffle(group)
                n_test = max(1, int(len(group) * test_size))
                test_samples.extend(group[:n_test])
                train_samples.extend(group[n_test:])
        else:
            random.shuffle(samples)
            n_test = int(len(samples) * test_size)
            test_samples = samples[:n_test]
            train_samples = samples[n_test:]

        train_dataset = Dataset(
            samples=train_samples,
            feature_names=dataset.feature_names,
            label_name=dataset.label_name
        )

        test_dataset = Dataset(
            samples=test_samples,
            feature_names=dataset.feature_names,
            label_name=dataset.label_name
        )

        return SplitResult(train=train_dataset, test=test_dataset)

    @staticmethod
    def k_fold(dataset: Dataset, k: int = 5, random_state: Optional[int] = None) -> Iterator[SplitResult]:
        if random_state is not None:
            random.seed(random_state)

        samples = dataset.samples.copy()
        random.shuffle(samples)

        fold_size = len(samples) // k

        for i in range(k):
            start = i * fold_size
            end = start + fold_size if i < k - 1 else len(samples)

            test_samples = samples[start:end]
            train_samples = samples[:start] + samples[end:]

            yield SplitResult(
                train=Dataset(
                    samples=train_samples,
                    feature_names=dataset.feature_names,
                    label_name=dataset.label_name
                ),
                test=Dataset(
                    samples=test_samples,
                    feature_names=dataset.feature_names,
                    label_name=dataset.label_name
                )
            )


# =============================================================================
# PIPELINE
# =============================================================================

class Pipeline:
    """ML Pipeline with stages."""

    def __init__(self, name: str = "pipeline"):
        self.name = name
        self.steps: List[Tuple[str, Any]] = []
        self._fitted = False

    def add_step(self, name: str, estimator: Any) -> 'Pipeline':
        """Add a step to the pipeline."""
        self.steps.append((name, estimator))
        return self

    def fit(self, X: List[List[float]], y: List[Any]) -> 'Pipeline':
        """Fit all steps."""
        X_transformed = X

        for name, estimator in self.steps[:-1]:
            if hasattr(estimator, 'fit_transform'):
                X_transformed = estimator.fit_transform(X_transformed, y)
            else:
                estimator.fit(X_transformed, y)
                X_transformed = estimator.transform(X_transformed)

        # Fit final estimator
        if self.steps:
            name, estimator = self.steps[-1]
            estimator.fit(X_transformed, y)

        self._fitted = True
        return self

    def predict(self, X: List[List[float]]) -> List[Any]:
        """Transform and predict."""
        X_transformed = X

        for name, estimator in self.steps[:-1]:
            X_transformed = estimator.transform(X_transformed)

        if self.steps:
            name, estimator = self.steps[-1]
            return estimator.predict(X_transformed)

        return []

    def fit_predict(self, X: List[List[float]], y: List[Any]) -> List[Any]:
        """Fit and predict."""
        self.fit(X, y)
        return self.predict(X)


# =============================================================================
# EXPERIMENT TRACKER
# =============================================================================

class ExperimentTracker:
    """Track ML experiments."""

    def __init__(self, experiment_dir: str = "./experiments"):
        self.experiment_dir = Path(experiment_dir)
        self.experiment_dir.mkdir(parents=True, exist_ok=True)
        self.runs: List[ExperimentRun] = []
        self._current_run: Optional[ExperimentRun] = None

    def start_run(self, name: str, pipeline_name: str = "") -> ExperimentRun:
        """Start a new experiment run."""
        run = ExperimentRun(
            name=name,
            pipeline_name=pipeline_name,
            status="running"
        )
        self._current_run = run
        self.runs.append(run)
        return run

    def log_param(self, key: str, value: Any) -> None:
        """Log a parameter."""
        if self._current_run:
            self._current_run.parameters[key] = value

    def log_params(self, params: Dict[str, Any]) -> None:
        """Log multiple parameters."""
        if self._current_run:
            self._current_run.parameters.update(params)

    def log_metric(self, key: str, value: float) -> None:
        """Log a metric."""
        if self._current_run:
            self._current_run.metrics[key] = value

    def log_metrics(self, metrics: Dict[str, float]) -> None:
        """Log multiple metrics."""
        if self._current_run:
            self._current_run.metrics.update(metrics)

    def end_run(self, status: str = "completed") -> None:
        """End the current run."""
        if self._current_run:
            self._current_run.status = status
            self._current_run.completed_at = datetime.utcnow()
            self._save_run(self._current_run)
            self._current_run = None

    def _save_run(self, run: ExperimentRun) -> None:
        """Save run to disk."""
        run_file = self.experiment_dir / f"{run.id}.json"

        run_data = {
            "id": run.id,
            "name": run.name,
            "pipeline_name": run.pipeline_name,
            "parameters": run.parameters,
            "metrics": run.metrics,
            "started_at": run.started_at.isoformat(),
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "status": run.status
        }

        with open(run_file, 'w') as f:
            json.dump(run_data, f, indent=2)

    def get_best_run(self, metric: str, minimize: bool = False) -> Optional[ExperimentRun]:
        """Get best run by metric."""
        valid_runs = [r for r in self.runs if metric in r.metrics]

        if not valid_runs:
            return None

        if minimize:
            return min(valid_runs, key=lambda r: r.metrics[metric])
        else:
            return max(valid_runs, key=lambda r: r.metrics[metric])


# =============================================================================
# ML PIPELINE MANAGER
# =============================================================================

class MLPipeline:
    """
    ML Pipeline for BAEL.

    Complete ML workflow management.
    """

    def __init__(self, name: str = "bael_ml_pipeline"):
        self.name = name
        self._pipelines: Dict[str, Pipeline] = {}
        self._models: Dict[str, Model] = {}
        self._transformers: Dict[str, Transformer] = {}
        self._tracker = ExperimentTracker()
        self._metrics = MetricsCalculator()

    # -------------------------------------------------------------------------
    # PIPELINE MANAGEMENT
    # -------------------------------------------------------------------------

    def create_pipeline(self, name: str) -> Pipeline:
        """Create a new pipeline."""
        pipeline = Pipeline(name=name)
        self._pipelines[name] = pipeline
        return pipeline

    def get_pipeline(self, name: str) -> Optional[Pipeline]:
        """Get pipeline by name."""
        return self._pipelines.get(name)

    # -------------------------------------------------------------------------
    # PREPROCESSING
    # -------------------------------------------------------------------------

    def standard_scaler(self) -> StandardScaler:
        return StandardScaler()

    def min_max_scaler(self, feature_range: Tuple[float, float] = (0, 1)) -> MinMaxScaler:
        return MinMaxScaler(feature_range)

    def polynomial_features(self, degree: int = 2) -> PolynomialFeatures:
        return PolynomialFeatures(degree)

    def pca(self, n_components: int = 2) -> PCA:
        return PCA(n_components)

    # -------------------------------------------------------------------------
    # FEATURE SELECTION
    # -------------------------------------------------------------------------

    def variance_threshold(self, threshold: float = 0.0) -> VarianceThreshold:
        return VarianceThreshold(threshold)

    def select_k_best(self, k: int = 10) -> SelectKBest:
        return SelectKBest(k)

    # -------------------------------------------------------------------------
    # MODELS
    # -------------------------------------------------------------------------

    def linear_regression(self, **kwargs) -> LinearRegression:
        return LinearRegression(**kwargs)

    def logistic_regression(self, **kwargs) -> LogisticRegression:
        return LogisticRegression(**kwargs)

    def knn(self, k: int = 5) -> KNeighborsClassifier:
        return KNeighborsClassifier(k)

    def decision_tree(self, **kwargs) -> DecisionTree:
        return DecisionTree(**kwargs)

    # -------------------------------------------------------------------------
    # DATA OPERATIONS
    # -------------------------------------------------------------------------

    def split_data(
        self,
        dataset: Dataset,
        test_size: float = 0.2,
        stratify: bool = False
    ) -> SplitResult:
        """Split dataset."""
        return DataSplitter.train_test_split(dataset, test_size, stratify=stratify)

    def cross_validate(
        self,
        pipeline: Pipeline,
        dataset: Dataset,
        k: int = 5,
        metrics: List[str] = None
    ) -> Dict[str, List[float]]:
        """Perform k-fold cross-validation."""
        metrics = metrics or ["accuracy"]
        results: Dict[str, List[float]] = {m: [] for m in metrics}

        for fold, split in enumerate(DataSplitter.k_fold(dataset, k)):
            pipeline.fit(split.train.X, split.train.y)
            predictions = pipeline.predict(split.test.X)

            for metric in metrics:
                if metric == "accuracy":
                    results[metric].append(self._metrics.accuracy(split.test.y, predictions))
                elif metric == "f1":
                    results[metric].append(self._metrics.f1(split.test.y, predictions))
                elif metric == "mse":
                    results[metric].append(self._metrics.mse(split.test.y, predictions))

        return results

    # -------------------------------------------------------------------------
    # EVALUATION
    # -------------------------------------------------------------------------

    def evaluate(
        self,
        y_true: List[Any],
        y_pred: List[Any],
        task: TaskType = TaskType.CLASSIFICATION
    ) -> EvaluationResult:
        """Evaluate predictions."""
        metrics = {}

        if task == TaskType.CLASSIFICATION:
            metrics["accuracy"] = self._metrics.accuracy(y_true, y_pred)
            metrics["precision"] = self._metrics.precision(y_true, y_pred)
            metrics["recall"] = self._metrics.recall(y_true, y_pred)
            metrics["f1"] = self._metrics.f1(y_true, y_pred)

            cm, _ = self._metrics.confusion_matrix(y_true, y_pred)
            return EvaluationResult(metrics=metrics, confusion_matrix=cm)

        elif task == TaskType.REGRESSION:
            metrics["mse"] = self._metrics.mse(y_true, y_pred)
            metrics["rmse"] = self._metrics.rmse(y_true, y_pred)
            metrics["mae"] = self._metrics.mae(y_true, y_pred)
            metrics["r2"] = self._metrics.r2(y_true, y_pred)

            return EvaluationResult(metrics=metrics)

        return EvaluationResult(metrics=metrics)

    # -------------------------------------------------------------------------
    # EXPERIMENT TRACKING
    # -------------------------------------------------------------------------

    def start_experiment(self, name: str, pipeline_name: str = "") -> ExperimentRun:
        return self._tracker.start_run(name, pipeline_name)

    def log_params(self, params: Dict[str, Any]) -> None:
        self._tracker.log_params(params)

    def log_metrics(self, metrics: Dict[str, float]) -> None:
        self._tracker.log_metrics(metrics)

    def end_experiment(self, status: str = "completed") -> None:
        self._tracker.end_run(status)

    def get_best_experiment(self, metric: str, minimize: bool = False) -> Optional[ExperimentRun]:
        return self._tracker.get_best_run(metric, minimize)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the ML Pipeline."""
    print("=" * 70)
    print("BAEL - ML PIPELINE DEMO")
    print("Machine Learning Pipeline Orchestration")
    print("=" * 70)
    print()

    ml = MLPipeline()

    # 1. Create Sample Dataset
    print("1. CREATE SAMPLE DATASET:")
    print("-" * 40)

    samples = []
    for i in range(100):
        # Simple classification: x1 + x2 > 1 => class 1
        x1 = random.uniform(0, 2)
        x2 = random.uniform(0, 2)
        label = 1 if x1 + x2 > 1 else 0

        samples.append(DataSample(
            features=[x1, x2, x1 * x2, x1 ** 2],
            label=label
        ))

    dataset = Dataset(
        samples=samples,
        feature_names=["x1", "x2", "x1*x2", "x1^2"],
        label_name="target"
    )

    print(f"   Created dataset with {len(dataset)} samples")
    print(f"   Features: {dataset.feature_names}")
    print()

    # 2. Split Data
    print("2. SPLIT DATA:")
    print("-" * 40)

    split = ml.split_data(dataset, test_size=0.2, stratify=True)
    print(f"   Train: {len(split.train)} samples")
    print(f"   Test: {len(split.test)} samples")
    print()

    # 3. Create Pipeline
    print("3. CREATE PIPELINE:")
    print("-" * 40)

    pipeline = ml.create_pipeline("classification_pipeline")
    pipeline.add_step("scaler", ml.standard_scaler())
    pipeline.add_step("selector", ml.select_k_best(k=3))
    pipeline.add_step("classifier", ml.logistic_regression(iterations=500))

    print(f"   Pipeline: {pipeline.name}")
    print(f"   Steps: {[s[0] for s in pipeline.steps]}")
    print()

    # 4. Train Pipeline
    print("4. TRAIN PIPELINE:")
    print("-" * 40)

    ml.start_experiment("logistic_regression_exp", pipeline.name)
    ml.log_params({"iterations": 500, "k_features": 3})

    pipeline.fit(split.train.X, split.train.y)
    print("   Pipeline fitted successfully")
    print()

    # 5. Evaluate
    print("5. EVALUATE:")
    print("-" * 40)

    predictions = pipeline.predict(split.test.X)
    result = ml.evaluate(split.test.y, predictions, TaskType.CLASSIFICATION)

    ml.log_metrics(result.metrics)
    ml.end_experiment()

    print(f"   Accuracy:  {result.metrics['accuracy']:.4f}")
    print(f"   Precision: {result.metrics['precision']:.4f}")
    print(f"   Recall:    {result.metrics['recall']:.4f}")
    print(f"   F1:        {result.metrics['f1']:.4f}")
    print()

    # 6. Cross-Validation
    print("6. CROSS-VALIDATION:")
    print("-" * 40)

    cv_pipeline = ml.create_pipeline("cv_pipeline")
    cv_pipeline.add_step("scaler", ml.standard_scaler())
    cv_pipeline.add_step("classifier", ml.knn(k=3))

    cv_results = ml.cross_validate(cv_pipeline, dataset, k=5, metrics=["accuracy", "f1"])

    print(f"   5-Fold CV Results:")
    for metric, scores in cv_results.items():
        avg = sum(scores) / len(scores)
        print(f"      {metric}: {avg:.4f} (+/- {max(scores) - min(scores):.4f})")
    print()

    # 7. Compare Models
    print("7. COMPARE MODELS:")
    print("-" * 40)

    models = [
        ("LogisticRegression", ml.logistic_regression()),
        ("KNN", ml.knn(k=5)),
        ("DecisionTree", ml.decision_tree(max_depth=5))
    ]

    for name, model in models:
        ml.start_experiment(f"{name}_exp", name)

        p = ml.create_pipeline(name)
        p.add_step("scaler", ml.standard_scaler())
        p.add_step("model", model)

        p.fit(split.train.X, split.train.y)
        preds = p.predict(split.test.X)

        acc = ml._metrics.accuracy(split.test.y, preds)
        ml.log_metric("accuracy", acc)
        ml.end_experiment()

        print(f"   {name}: accuracy = {acc:.4f}")
    print()

    # 8. Transformers Demo
    print("8. TRANSFORMERS DEMO:")
    print("-" * 40)

    sample_data = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

    scaler = StandardScaler()
    scaled = scaler.fit_transform(sample_data)
    print(f"   StandardScaler: {sample_data[0]} -> {[f'{x:.2f}' for x in scaled[0]]}")

    pca = PCA(n_components=2)
    reduced = pca.fit_transform(sample_data)
    print(f"   PCA(2): {sample_data[0]} -> {[f'{x:.2f}' for x in reduced[0]]}")

    poly = PolynomialFeatures(degree=2)
    expanded = poly.fit_transform(sample_data)
    print(f"   Polynomial(2): {len(sample_data[0])} features -> {len(expanded[0])} features")
    print()

    # 9. Feature Selection
    print("9. FEATURE SELECTION:")
    print("-" * 40)

    selector = SelectKBest(k=2)
    selector.fit(split.train.X, split.train.y)
    selected = selector.get_support()

    print(f"   Selected features: {selected}")
    print(f"   Feature scores: {[f'{s:.3f}' for s in selector.scores]}")
    print()

    # 10. Regression Example
    print("10. REGRESSION EXAMPLE:")
    print("-" * 40)

    reg_samples = []
    for i in range(50):
        x = random.uniform(0, 10)
        y = 2 * x + 1 + random.gauss(0, 0.5)  # y = 2x + 1 + noise
        reg_samples.append(DataSample(features=[x], label=y))

    reg_dataset = Dataset(samples=reg_samples)
    reg_split = ml.split_data(reg_dataset, test_size=0.2)

    reg_model = ml.linear_regression(iterations=1000, learning_rate=0.01)
    reg_model.fit(reg_split.train.X, reg_split.train.y)
    reg_preds = reg_model.predict(reg_split.test.X)

    reg_result = ml.evaluate(reg_split.test.y, reg_preds, TaskType.REGRESSION)

    print(f"   MSE:  {reg_result.metrics['mse']:.4f}")
    print(f"   RMSE: {reg_result.metrics['rmse']:.4f}")
    print(f"   R2:   {reg_result.metrics['r2']:.4f}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - ML Pipeline Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
