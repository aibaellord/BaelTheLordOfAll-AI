"""
⚡ UNCERTAINTY QUANTIFICATION ⚡
================================
Rigorous uncertainty estimation for AI systems.

Types of uncertainty:
- Aleatoric: Inherent randomness (irreducible)
- Epistemic: Lack of knowledge (reducible)

Methods:
- Monte Carlo dropout
- Ensemble methods
- Bayesian inference
- Confidence calibration
"""

import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid


class UncertaintyType(Enum):
    """Types of uncertainty"""
    ALEATORIC = auto()    # Data/inherent uncertainty
    EPISTEMIC = auto()    # Model/knowledge uncertainty
    COMBINED = auto()     # Both types
    UNKNOWN = auto()      # Type not determined


@dataclass
class UncertaintyEstimate:
    """An uncertainty estimate"""
    value: float                      # Point estimate
    uncertainty: float                # Uncertainty magnitude
    confidence_interval: Tuple[float, float] = None  # CI bounds
    uncertainty_type: UncertaintyType = UncertaintyType.UNKNOWN
    method: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def relative_uncertainty(self) -> float:
        """Uncertainty relative to value"""
        if self.value == 0:
            return float('inf') if self.uncertainty > 0 else 0
        return self.uncertainty / abs(self.value)


class AleatoricUncertainty:
    """
    Quantifies aleatoric (data) uncertainty.

    This is irreducible uncertainty from inherent randomness.
    """

    def __init__(self):
        self.samples: Dict[str, List[float]] = defaultdict(list)

    def record_observation(
        self,
        category: str,
        value: float
    ):
        """Record observation for category"""
        self.samples[category].append(value)

    def estimate_variance(
        self,
        category: str
    ) -> UncertaintyEstimate:
        """Estimate aleatoric variance"""
        samples = self.samples.get(category, [])

        if len(samples) < 2:
            return UncertaintyEstimate(
                value=samples[0] if samples else 0,
                uncertainty=float('inf'),
                uncertainty_type=UncertaintyType.ALEATORIC
            )

        mean = np.mean(samples)
        std = np.std(samples, ddof=1)

        # Confidence interval (95%)
        n = len(samples)
        ci_half = 1.96 * std / np.sqrt(n)

        return UncertaintyEstimate(
            value=float(mean),
            uncertainty=float(std),
            confidence_interval=(mean - ci_half, mean + ci_half),
            uncertainty_type=UncertaintyType.ALEATORIC,
            method="sample_variance",
            metadata={'n_samples': n}
        )

    def heteroscedastic_estimate(
        self,
        x: np.ndarray,
        y: np.ndarray,
        x_query: float
    ) -> UncertaintyEstimate:
        """
        Estimate variance that varies with input.

        Uses local linear regression.
        """
        if len(x) < 5:
            return UncertaintyEstimate(
                value=0,
                uncertainty=float('inf'),
                uncertainty_type=UncertaintyType.ALEATORIC
            )

        # Local regression (Nadaraya-Watson)
        bandwidth = np.std(x) * 0.3

        weights = np.exp(-((x - x_query) ** 2) / (2 * bandwidth ** 2))
        weights /= weights.sum() + 1e-10

        # Weighted mean
        y_pred = np.sum(weights * y)

        # Local variance
        residuals = (y - y_pred) ** 2
        local_var = np.sum(weights * residuals)

        return UncertaintyEstimate(
            value=float(y_pred),
            uncertainty=float(np.sqrt(local_var)),
            uncertainty_type=UncertaintyType.ALEATORIC,
            method="heteroscedastic"
        )


class EpistemicUncertainty:
    """
    Quantifies epistemic (model) uncertainty.

    This is reducible uncertainty from lack of knowledge.
    """

    def __init__(self):
        self.predictions: Dict[str, List[float]] = defaultdict(list)
        self.model_count = 0

    def add_prediction(
        self,
        query_id: str,
        prediction: float,
        model_id: str = None
    ):
        """Add prediction from a model"""
        self.predictions[query_id].append(prediction)
        self.model_count = max(self.model_count, len(self.predictions[query_id]))

    def ensemble_uncertainty(
        self,
        query_id: str
    ) -> UncertaintyEstimate:
        """
        Estimate epistemic uncertainty from ensemble disagreement.
        """
        preds = self.predictions.get(query_id, [])

        if len(preds) < 2:
            return UncertaintyEstimate(
                value=preds[0] if preds else 0,
                uncertainty=float('inf'),
                uncertainty_type=UncertaintyType.EPISTEMIC
            )

        mean = np.mean(preds)
        std = np.std(preds)

        return UncertaintyEstimate(
            value=float(mean),
            uncertainty=float(std),
            uncertainty_type=UncertaintyType.EPISTEMIC,
            method="ensemble_disagreement",
            metadata={'n_models': len(preds)}
        )

    def monte_carlo_dropout(
        self,
        forward_fn: Callable[[Any], float],
        input_data: Any,
        n_samples: int = 30,
        dropout_rate: float = 0.1
    ) -> UncertaintyEstimate:
        """
        MC Dropout uncertainty estimation.

        Simulates by adding noise to predictions.
        """
        predictions = []

        for _ in range(n_samples):
            # Simulate dropout by adding noise
            pred = forward_fn(input_data)
            noise = np.random.normal(0, dropout_rate * abs(pred))
            predictions.append(pred + noise)

        mean = np.mean(predictions)
        std = np.std(predictions)

        return UncertaintyEstimate(
            value=float(mean),
            uncertainty=float(std),
            uncertainty_type=UncertaintyType.EPISTEMIC,
            method="mc_dropout",
            metadata={'n_samples': n_samples, 'dropout_rate': dropout_rate}
        )

    def bayesian_update(
        self,
        prior_mean: float,
        prior_var: float,
        observation: float,
        observation_var: float
    ) -> UncertaintyEstimate:
        """
        Bayesian update of belief.

        Conjugate normal-normal update.
        """
        # Posterior parameters
        posterior_var = 1 / (1/prior_var + 1/observation_var)
        posterior_mean = posterior_var * (
            prior_mean/prior_var + observation/observation_var
        )

        return UncertaintyEstimate(
            value=float(posterior_mean),
            uncertainty=float(np.sqrt(posterior_var)),
            uncertainty_type=UncertaintyType.EPISTEMIC,
            method="bayesian_update"
        )


class UncertaintyQuantifier:
    """
    Complete uncertainty quantification system.

    Combines aleatoric and epistemic uncertainty.
    """

    def __init__(self):
        self.aleatoric = AleatoricUncertainty()
        self.epistemic = EpistemicUncertainty()

    def quantify(
        self,
        category: str,
        predictions: List[float],
        observations: List[float] = None
    ) -> UncertaintyEstimate:
        """
        Quantify total uncertainty.
        """
        # Epistemic from predictions
        for i, pred in enumerate(predictions):
            self.epistemic.add_prediction(category, pred, f"model_{i}")

        epistemic_est = self.epistemic.ensemble_uncertainty(category)

        # Aleatoric from observations
        if observations:
            for obs in observations:
                self.aleatoric.record_observation(category, obs)
            aleatoric_est = self.aleatoric.estimate_variance(category)
        else:
            aleatoric_est = UncertaintyEstimate(
                value=0,
                uncertainty=0,
                uncertainty_type=UncertaintyType.ALEATORIC
            )

        # Combine (variance additivity)
        total_uncertainty = np.sqrt(
            epistemic_est.uncertainty ** 2 +
            aleatoric_est.uncertainty ** 2
        )

        return UncertaintyEstimate(
            value=epistemic_est.value,
            uncertainty=float(total_uncertainty),
            uncertainty_type=UncertaintyType.COMBINED,
            method="combined",
            metadata={
                'epistemic': epistemic_est.uncertainty,
                'aleatoric': aleatoric_est.uncertainty
            }
        )

    def decompose(
        self,
        estimate: UncertaintyEstimate
    ) -> Dict[str, float]:
        """Decompose uncertainty into components"""
        if 'epistemic' in estimate.metadata and 'aleatoric' in estimate.metadata:
            total = estimate.uncertainty ** 2
            epistemic = estimate.metadata['epistemic'] ** 2
            aleatoric = estimate.metadata['aleatoric'] ** 2

            return {
                'total': float(np.sqrt(total)),
                'epistemic': float(np.sqrt(epistemic)),
                'aleatoric': float(np.sqrt(aleatoric)),
                'epistemic_fraction': epistemic / (total + 1e-10),
                'aleatoric_fraction': aleatoric / (total + 1e-10)
            }

        return {'total': estimate.uncertainty}


@dataclass
class CalibrationBin:
    """Bin for calibration analysis"""
    predicted_confidence: float
    actual_accuracy: float
    count: int


class ConfidenceCalibrator:
    """
    Calibrates confidence scores to match actual accuracy.

    A well-calibrated model has:
    - 70% confident predictions correct 70% of the time
    - 90% confident predictions correct 90% of the time
    """

    def __init__(self, n_bins: int = 10):
        self.n_bins = n_bins

        # Tracking
        self.predictions: List[Tuple[float, bool]] = []  # (confidence, correct)

        # Calibration parameters
        self.temperature = 1.0
        self.platt_a = 0.0
        self.platt_b = 1.0

    def record_prediction(
        self,
        confidence: float,
        correct: bool
    ):
        """Record prediction and outcome"""
        self.predictions.append((confidence, correct))

    def calculate_calibration_error(self) -> float:
        """
        Calculate Expected Calibration Error (ECE).

        Lower is better (0 = perfectly calibrated).
        """
        if not self.predictions:
            return 1.0

        bins = self._bin_predictions()

        if not bins:
            return 1.0

        total = sum(b.count for b in bins)
        ece = sum(
            b.count * abs(b.predicted_confidence - b.actual_accuracy)
            for b in bins
        ) / total

        return ece

    def _bin_predictions(self) -> List[CalibrationBin]:
        """Bin predictions by confidence"""
        bins = []

        for i in range(self.n_bins):
            bin_lower = i / self.n_bins
            bin_upper = (i + 1) / self.n_bins
            bin_center = (bin_lower + bin_upper) / 2

            in_bin = [
                (conf, correct) for conf, correct in self.predictions
                if bin_lower <= conf < bin_upper
            ]

            if in_bin:
                accuracy = sum(1 for _, c in in_bin if c) / len(in_bin)
                bins.append(CalibrationBin(
                    predicted_confidence=bin_center,
                    actual_accuracy=accuracy,
                    count=len(in_bin)
                ))

        return bins

    def calibrate_temperature(
        self,
        logits: np.ndarray,
        labels: np.ndarray
    ) -> float:
        """
        Temperature scaling calibration.

        Finds temperature T that minimizes calibration error.
        """
        best_temp = 1.0
        best_ece = float('inf')

        for temp in np.linspace(0.1, 5.0, 50):
            # Apply temperature
            scaled_logits = logits / temp
            probs = self._softmax(scaled_logits)
            confidences = np.max(probs, axis=1)

            # Calculate ECE
            correct = np.argmax(probs, axis=1) == labels

            temp_predictor = ConfidenceCalibrator(self.n_bins)
            for conf, corr in zip(confidences, correct):
                temp_predictor.record_prediction(conf, corr)

            ece = temp_predictor.calculate_calibration_error()

            if ece < best_ece:
                best_ece = ece
                best_temp = temp

        self.temperature = best_temp
        return best_temp

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        """Numerically stable softmax"""
        e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return e_x / np.sum(e_x, axis=-1, keepdims=True)

    def calibrate_platt(
        self,
        logits: np.ndarray,
        labels: np.ndarray
    ):
        """
        Platt scaling calibration.

        Fits sigmoid: P(y=1|f) = 1 / (1 + exp(a*f + b))
        """
        # Simple gradient descent
        a, b = 0.0, 1.0
        lr = 0.01

        for _ in range(1000):
            # Forward
            scaled = a * logits + b
            probs = 1 / (1 + np.exp(-scaled))

            # Loss (cross entropy)
            loss = -np.mean(
                labels * np.log(probs + 1e-10) +
                (1 - labels) * np.log(1 - probs + 1e-10)
            )

            # Gradients
            diff = probs - labels
            grad_a = np.mean(diff * logits)
            grad_b = np.mean(diff)

            # Update
            a -= lr * grad_a
            b -= lr * grad_b

        self.platt_a = a
        self.platt_b = b

    def calibrated_confidence(
        self,
        raw_confidence: float
    ) -> float:
        """Apply calibration to raw confidence"""
        # Apply temperature scaling
        calibrated = raw_confidence ** (1 / self.temperature)

        return float(calibrated)

    def get_reliability_diagram(self) -> Dict[str, List[float]]:
        """Get data for reliability diagram"""
        bins = self._bin_predictions()

        return {
            'predicted': [b.predicted_confidence for b in bins],
            'actual': [b.actual_accuracy for b in bins],
            'counts': [b.count for b in bins]
        }


# Export all
__all__ = [
    'UncertaintyType',
    'UncertaintyEstimate',
    'AleatoricUncertainty',
    'EpistemicUncertainty',
    'UncertaintyQuantifier',
    'CalibrationBin',
    'ConfidenceCalibrator',
]
