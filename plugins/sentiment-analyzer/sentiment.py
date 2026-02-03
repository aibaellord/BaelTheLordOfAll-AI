"""
Sentiment Analysis Plugin for BAEL
Simple rule-based sentiment analyzer.
"""

import logging
import re
from typing import Any, Dict

from core.plugins.registry import PluginInterface, PluginManifest

logger = logging.getLogger("BAEL.Plugin.Sentiment")


class SentimentAnalyzer(PluginInterface):
    """Simple sentiment analyzer using keyword matching."""

    # Positive and negative word lists
    POSITIVE_WORDS = {
        'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
        'love', 'happy', 'joy', 'excited', 'perfect', 'best', 'awesome',
        'brilliant', 'outstanding', 'superb', 'delightful', 'pleased'
    }

    NEGATIVE_WORDS = {
        'bad', 'terrible', 'awful', 'horrible', 'worst', 'hate', 'angry',
        'sad', 'disappointing', 'poor', 'useless', 'frustrating', 'annoying',
        'disgusting', 'pathetic', 'miserable', 'dreadful', 'inferior'
    }

    def __init__(self, manifest: PluginManifest, config: Dict[str, Any]):
        super().__init__(manifest, config)
        self.threshold = config.get("threshold", 0.5)

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        self.logger.info("✅ Sentiment analyzer initialized")
        return True

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text.

        Args:
            text: Text to analyze

        Returns:
            Sentiment analysis result with score and label
        """
        # Tokenize and lowercase
        words = re.findall(r'\b\w+\b', text.lower())

        if not words:
            return {
                "text": text,
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "positive_words": [],
                "negative_words": []
            }

        # Count positive and negative words
        positive_found = [w for w in words if w in self.POSITIVE_WORDS]
        negative_found = [w for w in words if w in self.NEGATIVE_WORDS]

        positive_count = len(positive_found)
        negative_count = len(negative_found)
        total_sentiment_words = positive_count + negative_count

        if total_sentiment_words == 0:
            sentiment = "neutral"
            score = 0.0
            confidence = 0.0
        else:
            # Calculate sentiment score (-1 to 1)
            score = (positive_count - negative_count) / len(words)
            confidence = total_sentiment_words / len(words)

            # Determine sentiment label
            if score > self.threshold:
                sentiment = "positive"
            elif score < -self.threshold:
                sentiment = "negative"
            else:
                sentiment = "neutral"

        result = {
            "text": text[:100] + "..." if len(text) > 100 else text,
            "sentiment": sentiment,
            "score": round(score, 3),
            "confidence": round(confidence, 3),
            "positive_words": positive_found,
            "negative_words": negative_found,
            "word_count": len(words)
        }

        self.logger.debug(f"Sentiment: {sentiment} (score={score:.3f})")

        return result

    async def shutdown(self):
        """Cleanup resources."""
        self.logger.info("Sentiment analyzer shutdown")


def register(manifest: PluginManifest, config: Dict[str, Any]) -> SentimentAnalyzer:
    """
    Plugin entry point.

    Args:
        manifest: Plugin manifest
        config: Plugin configuration

    Returns:
        SentimentAnalyzer instance
    """
    return SentimentAnalyzer(manifest, config)
