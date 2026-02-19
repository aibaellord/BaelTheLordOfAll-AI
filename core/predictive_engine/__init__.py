"""
BAEL Predictive Engine Package
==============================

Advanced prediction and forecasting capabilities.
"""

from .predictive_analytics import (
    # Enums
    PredictionType,
    ModelType,
    ConfidenceLevel,
    AnomalyType,

    # Dataclasses
    DataPoint,
    TimeSeries,
    Prediction,
    Anomaly,
    Forecast,

    # Classes
    StatisticalAnalyzer,
    TimeSeriesPredictor,
    AnomalyDetector,
    CausalPredictor,
    PredictiveAnalyticsEngine,

    # Convenience instance
    predictive_engine
)

__all__ = [
    # Enums
    "PredictionType",
    "ModelType",
    "ConfidenceLevel",
    "AnomalyType",

    # Dataclasses
    "DataPoint",
    "TimeSeries",
    "Prediction",
    "Anomaly",
    "Forecast",

    # Classes
    "StatisticalAnalyzer",
    "TimeSeriesPredictor",
    "AnomalyDetector",
    "CausalPredictor",
    "PredictiveAnalyticsEngine",

    # Instance
    "predictive_engine"
]
