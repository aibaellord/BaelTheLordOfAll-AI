# BAEL - Predictive Intent Engine
# "Knowing What You Need Before You Know It"

"""
Predictive Intent Engine - Predicts user intent before it's expressed.

This module provides intelligent intent prediction:
- Intent pattern matching
- Behavior learning
- Pre-computation of likely actions
- Frustration detection
- Proactive assistance

Usage:
    from core.predictive_intent import PredictiveIntentEngine, IntentCategory

    engine = await PredictiveIntentEngine.create()
    predictions = await engine.predict_next(context, top_k=5)
"""

from .predictive_intent_engine import (
    PredictiveIntentEngine,
    IntentCategory,
    Intent,
    Prediction,
    UserContext,
    IntentMatcher,
)

__all__ = [
    "PredictiveIntentEngine",
    "IntentCategory",
    "Intent",
    "Prediction",
    "UserContext",
    "IntentMatcher",
]
