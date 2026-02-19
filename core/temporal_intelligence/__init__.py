"""
⚡ TEMPORAL INTELLIGENCE ENGINE ⚡
==================================
Time-aware reasoning and prediction.

This module provides:
- Temporal logic reasoning
- Time series analysis
- Future prediction
- Causal temporal analysis
"""

from .temporal_core import (
    TimePoint,
    TimeInterval,
    TemporalRelation,
    TemporalEntity,
    Timeline,
    TemporalGraph,
)

from .temporal_logic import (
    TemporalOperator,
    TemporalFormula,
    LTLFormula,
    CTLFormula,
    TemporalReasoner,
    ModelChecker,
)

from .temporal_prediction import (
    TimeSeriesModel,
    ARIMAPredictor,
    ExponentialSmoothing,
    ProphetModel,
    DeepTemporalPredictor,
    EnsemblePredictor,
)

from .causal_temporal import (
    TemporalCause,
    CausalChain,
    TemporalCausalGraph,
    GrangerCausality,
    TemporalIntervention,
)

__all__ = [
    # Temporal Core
    'TimePoint',
    'TimeInterval',
    'TemporalRelation',
    'TemporalEntity',
    'Timeline',
    'TemporalGraph',

    # Temporal Logic
    'TemporalOperator',
    'TemporalFormula',
    'LTLFormula',
    'CTLFormula',
    'TemporalReasoner',
    'ModelChecker',

    # Temporal Prediction
    'TimeSeriesModel',
    'ARIMAPredictor',
    'ExponentialSmoothing',
    'ProphetModel',
    'DeepTemporalPredictor',
    'EnsemblePredictor',

    # Causal Temporal
    'TemporalCause',
    'CausalChain',
    'TemporalCausalGraph',
    'GrangerCausality',
    'TemporalIntervention',
]
