"""
⚡ TEMPORAL PREDICTION ⚡
========================
Time series prediction.

Features:
- ARIMA models
- Exponential smoothing
- Deep learning predictors
- Ensemble methods
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import deque
import uuid


@dataclass
class PredictionResult:
    """Result of temporal prediction"""
    values: np.ndarray
    confidence_lower: np.ndarray = None
    confidence_upper: np.ndarray = None
    confidence_level: float = 0.95

    model_name: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)


class TimeSeriesModel:
    """Base class for time series models"""

    def __init__(self, name: str = "base"):
        self.name = name
        self.is_fitted = False
        self.history: List[float] = []

    def fit(self, data: np.ndarray):
        """Fit model to data"""
        self.history = list(data)
        self.is_fitted = True

    def predict(self, steps: int) -> PredictionResult:
        """Predict future values"""
        raise NotImplementedError

    def update(self, value: float):
        """Update model with new observation"""
        self.history.append(value)


class ARIMAPredictor(TimeSeriesModel):
    """
    ARIMA (AutoRegressive Integrated Moving Average).
    """

    def __init__(self, p: int = 1, d: int = 0, q: int = 0):
        super().__init__("ARIMA")
        self.p = p  # AR order
        self.d = d  # Differencing order
        self.q = q  # MA order

        # Coefficients
        self.ar_coeffs: np.ndarray = None
        self.ma_coeffs: np.ndarray = None
        self.intercept: float = 0.0

        # Residuals for MA
        self.residuals: deque = deque(maxlen=q if q > 0 else 1)

    def fit(self, data: np.ndarray):
        """Fit ARIMA model"""
        super().fit(data)

        # Apply differencing
        diff_data = data
        for _ in range(self.d):
            diff_data = np.diff(diff_data)

        if len(diff_data) < self.p + 1:
            return

        # Estimate AR coefficients using Yule-Walker
        if self.p > 0:
            self.ar_coeffs = self._estimate_ar(diff_data, self.p)

        # Estimate MA coefficients (simplified)
        if self.q > 0:
            self.ma_coeffs = np.zeros(self.q)
            residuals = self._get_residuals(diff_data)
            for i in range(self.q):
                if i < len(residuals):
                    self.ma_coeffs[i] = 0.5  # Simplified

        self.intercept = np.mean(diff_data)

    def _estimate_ar(self, data: np.ndarray, order: int) -> np.ndarray:
        """Estimate AR coefficients using Yule-Walker"""
        n = len(data)
        if n <= order:
            return np.zeros(order)

        # Compute autocorrelations
        mean = np.mean(data)
        centered = data - mean

        r = np.zeros(order + 1)
        for k in range(order + 1):
            r[k] = np.sum(centered[:n-k] * centered[k:]) / n

        # Normalize
        r = r / (r[0] + 1e-10)

        # Solve Yule-Walker equations
        R = np.zeros((order, order))
        for i in range(order):
            for j in range(order):
                R[i, j] = r[abs(i - j)]

        try:
            coeffs = np.linalg.solve(R, r[1:order+1])
        except np.linalg.LinAlgError:
            coeffs = np.zeros(order)

        return coeffs

    def _get_residuals(self, data: np.ndarray) -> np.ndarray:
        """Get model residuals"""
        if self.ar_coeffs is None:
            return data

        residuals = []
        for i in range(self.p, len(data)):
            pred = self.intercept
            for j in range(self.p):
                pred += self.ar_coeffs[j] * data[i - j - 1]
            residuals.append(data[i] - pred)

        return np.array(residuals)

    def predict(self, steps: int) -> PredictionResult:
        """Predict future values"""
        if not self.is_fitted or len(self.history) < self.p + self.d:
            return PredictionResult(values=np.zeros(steps), model_name=self.name)

        # Work with differenced series
        diff_data = np.array(self.history)
        for _ in range(self.d):
            diff_data = np.diff(diff_data)

        predictions = []
        extended = list(diff_data)

        for _ in range(steps):
            pred = self.intercept

            # AR component
            if self.ar_coeffs is not None:
                for j in range(self.p):
                    if len(extended) > j:
                        pred += self.ar_coeffs[j] * extended[-(j+1)]

            predictions.append(pred)
            extended.append(pred)

        # Integrate back
        result = np.array(predictions)
        for _ in range(self.d):
            last_val = self.history[-1] if self.d == 1 else self.history[-self.d]
            result = last_val + np.cumsum(result)

        # Confidence intervals
        std = np.std(self.history) if len(self.history) > 1 else 1.0
        margin = 1.96 * std * np.sqrt(np.arange(1, steps + 1))

        return PredictionResult(
            values=result,
            confidence_lower=result - margin,
            confidence_upper=result + margin,
            model_name=self.name
        )


class ExponentialSmoothing(TimeSeriesModel):
    """
    Exponential smoothing methods.
    """

    def __init__(
        self,
        alpha: float = 0.3,
        beta: float = None,  # Trend
        gamma: float = None,  # Seasonal
        seasonal_period: int = 12
    ):
        super().__init__("ExponentialSmoothing")
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.seasonal_period = seasonal_period

        # State
        self.level: float = 0.0
        self.trend: float = 0.0
        self.seasonal: List[float] = []

    def fit(self, data: np.ndarray):
        """Fit exponential smoothing model"""
        super().fit(data)

        if len(data) < 2:
            return

        # Initialize level
        self.level = data[0]

        # Initialize trend (if used)
        if self.beta is not None:
            self.trend = data[1] - data[0]

        # Initialize seasonal (if used)
        if self.gamma is not None:
            n_periods = len(data) // self.seasonal_period
            if n_periods >= 1:
                self.seasonal = [0.0] * self.seasonal_period
                for i in range(self.seasonal_period):
                    values = data[i::self.seasonal_period]
                    self.seasonal[i] = np.mean(values) / (np.mean(data) + 1e-10)
            else:
                self.seasonal = [1.0] * self.seasonal_period

        # Update state through data
        for i, y in enumerate(data):
            self._update_state(y, i)

    def _update_state(self, y: float, index: int):
        """Update state with observation"""
        if self.gamma is not None and self.seasonal:
            season_idx = index % self.seasonal_period
            deseasonalized = y / (self.seasonal[season_idx] + 1e-10)
        else:
            deseasonalized = y

        # Update level
        if self.beta is not None:
            new_level = self.alpha * deseasonalized + (1 - self.alpha) * (self.level + self.trend)
        else:
            new_level = self.alpha * deseasonalized + (1 - self.alpha) * self.level

        # Update trend
        if self.beta is not None:
            self.trend = self.beta * (new_level - self.level) + (1 - self.beta) * self.trend

        self.level = new_level

        # Update seasonal
        if self.gamma is not None and self.seasonal:
            season_idx = index % self.seasonal_period
            self.seasonal[season_idx] = (
                self.gamma * (y / (self.level + 1e-10)) +
                (1 - self.gamma) * self.seasonal[season_idx]
            )

    def predict(self, steps: int) -> PredictionResult:
        """Predict future values"""
        predictions = []

        for h in range(1, steps + 1):
            pred = self.level

            if self.beta is not None:
                pred += h * self.trend

            if self.gamma is not None and self.seasonal:
                season_idx = (len(self.history) + h - 1) % self.seasonal_period
                pred *= self.seasonal[season_idx]

            predictions.append(pred)

        result = np.array(predictions)

        # Simple confidence intervals
        std = np.std(self.history) if len(self.history) > 1 else 1.0
        margin = 1.96 * std * np.sqrt(np.arange(1, steps + 1))

        return PredictionResult(
            values=result,
            confidence_lower=result - margin,
            confidence_upper=result + margin,
            model_name=self.name
        )


class ProphetModel(TimeSeriesModel):
    """
    Prophet-like decomposition model.
    """

    def __init__(
        self,
        yearly_seasonality: bool = True,
        weekly_seasonality: bool = True,
        changepoint_prior: float = 0.05
    ):
        super().__init__("Prophet")
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.changepoint_prior = changepoint_prior

        # Components
        self.trend_params: Dict[str, float] = {}
        self.seasonality_params: Dict[str, np.ndarray] = {}
        self.changepoints: List[int] = []

    def fit(self, data: np.ndarray):
        """Fit Prophet-like model"""
        super().fit(data)

        n = len(data)
        if n < 2:
            return

        # Fit trend (piecewise linear)
        self.trend_params['slope'] = (data[-1] - data[0]) / n
        self.trend_params['intercept'] = data[0]

        # Detect changepoints
        n_changepoints = min(25, n // 10)
        self.changepoints = list(np.linspace(0, n-1, n_changepoints + 2, dtype=int))[1:-1]

        # Fit seasonality (Fourier)
        trend = self._predict_trend(np.arange(n))
        detrended = data - trend

        if self.yearly_seasonality and n >= 365:
            self.seasonality_params['yearly'] = self._fit_fourier(
                detrended, period=365, order=10
            )

        if self.weekly_seasonality and n >= 7:
            self.seasonality_params['weekly'] = self._fit_fourier(
                detrended, period=7, order=3
            )

    def _fit_fourier(
        self,
        data: np.ndarray,
        period: float,
        order: int
    ) -> np.ndarray:
        """Fit Fourier series"""
        n = len(data)
        t = np.arange(n)

        # Build design matrix
        X = np.ones((n, 2 * order + 1))
        for i in range(1, order + 1):
            X[:, 2*i - 1] = np.sin(2 * np.pi * i * t / period)
            X[:, 2*i] = np.cos(2 * np.pi * i * t / period)

        # Least squares
        try:
            coeffs = np.linalg.lstsq(X, data, rcond=None)[0]
        except np.linalg.LinAlgError:
            coeffs = np.zeros(2 * order + 1)

        return coeffs

    def _predict_trend(self, t: np.ndarray) -> np.ndarray:
        """Predict trend component"""
        return self.trend_params.get('intercept', 0) + self.trend_params.get('slope', 0) * t

    def _predict_seasonality(
        self,
        t: np.ndarray,
        name: str,
        period: float
    ) -> np.ndarray:
        """Predict seasonality component"""
        if name not in self.seasonality_params:
            return np.zeros_like(t)

        coeffs = self.seasonality_params[name]
        order = (len(coeffs) - 1) // 2

        result = np.ones_like(t, dtype=float) * coeffs[0]
        for i in range(1, order + 1):
            result += coeffs[2*i - 1] * np.sin(2 * np.pi * i * t / period)
            result += coeffs[2*i] * np.cos(2 * np.pi * i * t / period)

        return result

    def predict(self, steps: int) -> PredictionResult:
        """Predict future values"""
        n = len(self.history)
        future_t = np.arange(n, n + steps)

        # Trend
        pred = self._predict_trend(future_t)

        # Seasonality
        if 'yearly' in self.seasonality_params:
            pred += self._predict_seasonality(future_t, 'yearly', 365)
        if 'weekly' in self.seasonality_params:
            pred += self._predict_seasonality(future_t, 'weekly', 7)

        # Uncertainty
        std = np.std(self.history) if len(self.history) > 1 else 1.0
        margin = 1.96 * std * np.sqrt(np.arange(1, steps + 1) * 0.1 + 1)

        return PredictionResult(
            values=pred,
            confidence_lower=pred - margin,
            confidence_upper=pred + margin,
            model_name=self.name
        )


class DeepTemporalPredictor(TimeSeriesModel):
    """
    Deep learning-inspired temporal predictor.
    """

    def __init__(
        self,
        hidden_size: int = 64,
        sequence_length: int = 10
    ):
        super().__init__("DeepTemporal")
        self.hidden_size = hidden_size
        self.sequence_length = sequence_length

        # Simple RNN-like weights (simulated)
        self.Wh = None
        self.Wx = None
        self.Wy = None
        self.hidden_state = None

    def fit(self, data: np.ndarray):
        """Fit deep model (simplified)"""
        super().fit(data)

        # Initialize weights
        np.random.seed(42)
        self.Wh = np.random.randn(self.hidden_size, self.hidden_size) * 0.1
        self.Wx = np.random.randn(self.hidden_size, 1) * 0.1
        self.Wy = np.random.randn(1, self.hidden_size) * 0.1

        # Simple training (conceptual)
        self.hidden_state = np.zeros((self.hidden_size, 1))

        for i in range(min(100, len(data) - 1)):
            x = np.array([[data[i]]])

            # Forward pass
            self.hidden_state = np.tanh(
                self.Wh @ self.hidden_state + self.Wx @ x
            )

    def predict(self, steps: int) -> PredictionResult:
        """Predict using RNN-like forward pass"""
        if self.hidden_state is None:
            return PredictionResult(values=np.zeros(steps), model_name=self.name)

        predictions = []
        h = self.hidden_state.copy()

        # Use last value as initial input
        x = np.array([[self.history[-1]]])

        for _ in range(steps):
            # RNN step
            h = np.tanh(self.Wh @ h + self.Wx @ x)
            y = self.Wy @ h

            predictions.append(y[0, 0])
            x = y

        result = np.array(predictions)

        # Scale to reasonable range
        mean = np.mean(self.history)
        std = np.std(self.history) if len(self.history) > 1 else 1.0
        result = mean + result * std

        margin = 1.96 * std * np.sqrt(np.arange(1, steps + 1))

        return PredictionResult(
            values=result,
            confidence_lower=result - margin,
            confidence_upper=result + margin,
            model_name=self.name
        )


class EnsemblePredictor(TimeSeriesModel):
    """
    Ensemble of multiple predictors.
    """

    def __init__(self, models: List[TimeSeriesModel] = None):
        super().__init__("Ensemble")
        self.models = models or [
            ARIMAPredictor(p=2, d=1, q=0),
            ExponentialSmoothing(alpha=0.3, beta=0.1),
            ProphetModel(),
        ]
        self.weights: np.ndarray = None

    def fit(self, data: np.ndarray):
        """Fit all models"""
        super().fit(data)

        for model in self.models:
            model.fit(data)

        # Calculate weights based on historical performance
        self.weights = self._calculate_weights(data)

    def _calculate_weights(self, data: np.ndarray) -> np.ndarray:
        """Calculate model weights based on holdout performance"""
        if len(data) < 20:
            return np.ones(len(self.models)) / len(self.models)

        # Use last 20% as validation
        split = int(len(data) * 0.8)
        train_data = data[:split]
        val_data = data[split:]

        errors = []
        for model in self.models:
            model.fit(train_data)
            pred = model.predict(len(val_data))
            mse = np.mean((pred.values - val_data) ** 2)
            errors.append(mse + 1e-10)  # Avoid zero

        # Inverse error weighting
        inv_errors = 1.0 / np.array(errors)
        weights = inv_errors / inv_errors.sum()

        return weights

    def predict(self, steps: int) -> PredictionResult:
        """Predict using weighted ensemble"""
        predictions = []

        for model in self.models:
            pred = model.predict(steps)
            predictions.append(pred.values)

        predictions = np.array(predictions)

        # Weighted average
        if self.weights is not None:
            result = np.average(predictions, axis=0, weights=self.weights)
        else:
            result = np.mean(predictions, axis=0)

        # Combined uncertainty
        std = np.std(predictions, axis=0)
        margin = 1.96 * std

        return PredictionResult(
            values=result,
            confidence_lower=result - margin,
            confidence_upper=result + margin,
            model_name=self.name,
            metrics={'n_models': len(self.models)}
        )


# Export all
__all__ = [
    'PredictionResult',
    'TimeSeriesModel',
    'ARIMAPredictor',
    'ExponentialSmoothing',
    'ProphetModel',
    'DeepTemporalPredictor',
    'EnsemblePredictor',
]
