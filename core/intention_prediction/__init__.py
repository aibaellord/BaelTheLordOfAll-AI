"""
BAEL - Intention Prediction Engine
Predicts user intentions before they express them.

This system provides:
1. Predictive action suggestion
2. Context-aware anticipation
3. Pattern recognition from behavior
4. Proactive assistance
5. Mind-reading-like capabilities

Ba'el knows what you need before you ask.
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
import pickle
from pathlib import Path

logger = logging.getLogger("BAEL.IntentionPrediction")


@dataclass
class IntentionPrediction:
    """A predicted intention."""
    prediction_id: str
    intention: str
    confidence: float  # 0-1
    reasoning: str
    suggested_action: str
    auto_execute: bool = False
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BehaviorPattern:
    """A learned behavior pattern."""
    pattern_id: str
    trigger_context: Dict[str, Any]
    resulting_action: str
    frequency: int = 1
    last_seen: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 0.5


class IntentionPredictionEngine:
    """Predicts user intentions based on context and patterns."""
    
    def __init__(self, storage_path: str = "./data/intentions"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._patterns: Dict[str, BehaviorPattern] = {}
        self._action_history: List[Dict[str, Any]] = []
        self._context_cache: Dict[str, Any] = {}
        
        self._load_data()
    
    def _load_data(self):
        """Load learned patterns."""
        patterns_file = self.storage_path / "patterns.pkl"
        if patterns_file.exists():
            try:
                with open(patterns_file, "rb") as f:
                    data = pickle.load(f)
                    self._patterns = data.get("patterns", {})
                    self._action_history = data.get("history", [])[-1000:]
            except:
                pass
    
    def _save_data(self):
        """Save learned patterns."""
        patterns_file = self.storage_path / "patterns.pkl"
        with open(patterns_file, "wb") as f:
            pickle.dump({
                "patterns": self._patterns,
                "history": self._action_history[-1000:]
            }, f)
    
    def record_action(self, action: str, context: Dict[str, Any] = None):
        """Record an action for pattern learning."""
        context = context or {}
        context.update({
            "hour": datetime.utcnow().hour,
            "day": datetime.utcnow().weekday()
        })
        
        self._action_history.append({
            "action": action,
            "context": context,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Learn pattern
        pattern_key = self._context_to_key(context)
        if pattern_key in self._patterns:
            self._patterns[pattern_key].frequency += 1
            self._patterns[pattern_key].last_seen = datetime.utcnow()
            self._patterns[pattern_key].confidence = min(0.95, self._patterns[pattern_key].frequency / 20)
        else:
            self._patterns[pattern_key] = BehaviorPattern(
                pattern_id=f"pattern_{hashlib.md5(pattern_key.encode()).hexdigest()[:8]}",
                trigger_context=context,
                resulting_action=action,
                frequency=1
            )
        
        if len(self._action_history) % 10 == 0:
            self._save_data()
    
    def _context_to_key(self, context: Dict[str, Any]) -> str:
        """Convert context to pattern key."""
        key_parts = [f"{k}:{v}" for k, v in sorted(context.items()) if k in ["hour", "day", "prev_action"]]
        return "|".join(key_parts)
    
    async def predict(self, context: Dict[str, Any] = None) -> List[IntentionPrediction]:
        """Predict likely intentions based on current context."""
        context = context or {}
        context.update({
            "hour": datetime.utcnow().hour,
            "day": datetime.utcnow().weekday()
        })
        
        # Add previous action
        if self._action_history:
            context["prev_action"] = self._action_history[-1]["action"]
        
        predictions = []
        
        # Find matching patterns
        for pattern in self._patterns.values():
            match_score = self._calculate_match(context, pattern.trigger_context)
            if match_score > 0.3:
                prediction = IntentionPrediction(
                    prediction_id=f"pred_{pattern.pattern_id}",
                    intention=f"You likely want to: {pattern.resulting_action}",
                    confidence=pattern.confidence * match_score,
                    reasoning=f"Based on {pattern.frequency} similar situations",
                    suggested_action=pattern.resulting_action,
                    auto_execute=pattern.confidence > 0.9 and match_score > 0.8
                )
                predictions.append(prediction)
        
        # Add time-based predictions
        hour = context.get("hour", datetime.utcnow().hour)
        time_predictions = self._get_time_based_predictions(hour)
        predictions.extend(time_predictions)
        
        # Sort by confidence
        predictions.sort(key=lambda p: p.confidence, reverse=True)
        
        return predictions[:5]
    
    def _calculate_match(self, current: Dict[str, Any], pattern: Dict[str, Any]) -> float:
        """Calculate how well current context matches pattern."""
        if not pattern:
            return 0.0
        
        matches = 0
        total = 0
        
        for key, value in pattern.items():
            if key in current:
                total += 1
                if current[key] == value:
                    matches += 1
                elif isinstance(value, (int, float)) and isinstance(current[key], (int, float)):
                    # Fuzzy match for numbers
                    if abs(current[key] - value) <= 1:
                        matches += 0.5
        
        return matches / total if total > 0 else 0.0
    
    def _get_time_based_predictions(self, hour: int) -> List[IntentionPrediction]:
        """Get predictions based on time of day."""
        predictions = []
        
        time_actions = {
            range(6, 9): ("Start morning routine", "Check emails and status"),
            range(9, 12): ("Focus work time", "Run development tasks"),
            range(12, 14): ("Midday break", "Review progress"),
            range(14, 17): ("Afternoon productivity", "Complete priority tasks"),
            range(17, 19): ("End of day", "Commit and push changes"),
            range(19, 22): ("Evening wrap-up", "Plan for tomorrow")
        }
        
        for time_range, (intention, action) in time_actions.items():
            if hour in time_range:
                predictions.append(IntentionPrediction(
                    prediction_id=f"time_pred_{hour}",
                    intention=intention,
                    confidence=0.6,
                    reasoning=f"Typical activity for {hour}:00",
                    suggested_action=action
                ))
        
        return predictions


# Singleton
_prediction_engine: Optional[IntentionPredictionEngine] = None


def get_prediction_engine() -> IntentionPredictionEngine:
    """Get global prediction engine."""
    global _prediction_engine
    if _prediction_engine is None:
        _prediction_engine = IntentionPredictionEngine()
    return _prediction_engine
