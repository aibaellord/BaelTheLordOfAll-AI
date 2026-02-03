#!/usr/bin/env python3
"""
BAEL - Agent Feedback System
Collect, process, and learn from user feedback.

Features:
- Feedback collection
- Sentiment analysis
- Rating aggregation
- Improvement suggestions
- Learning from feedback
"""

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class FeedbackType(Enum):
    """Types of feedback."""
    RATING = "rating"
    THUMBS = "thumbs"
    TEXT = "text"
    CORRECTION = "correction"
    SUGGESTION = "suggestion"
    BUG_REPORT = "bug_report"


class Sentiment(Enum):
    """Feedback sentiment."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class FeedbackCategory(Enum):
    """Feedback categories."""
    ACCURACY = "accuracy"
    HELPFULNESS = "helpfulness"
    CLARITY = "clarity"
    SPEED = "speed"
    RELEVANCE = "relevance"
    SAFETY = "safety"
    OTHER = "other"


@dataclass
class Feedback:
    """User feedback entry."""
    id: str
    type: FeedbackType
    category: FeedbackCategory

    # Content
    rating: Optional[int] = None  # 1-5 scale
    thumbs_up: Optional[bool] = None
    text: Optional[str] = None
    correction: Optional[str] = None

    # Context
    session_id: Optional[str] = None
    message_id: Optional[str] = None
    user_id: Optional[str] = None
    agent_response: Optional[str] = None
    user_query: Optional[str] = None

    # Analysis
    sentiment: Optional[Sentiment] = None
    keywords: List[str] = field(default_factory=list)

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    processed: bool = False
    action_taken: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "category": self.category.value,
            "rating": self.rating,
            "thumbs_up": self.thumbs_up,
            "text": self.text,
            "correction": self.correction,
            "session_id": self.session_id,
            "message_id": self.message_id,
            "user_id": self.user_id,
            "sentiment": self.sentiment.value if self.sentiment else None,
            "keywords": self.keywords,
            "timestamp": self.timestamp.isoformat(),
            "processed": self.processed,
            "action_taken": self.action_taken,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Feedback":
        return cls(
            id=data["id"],
            type=FeedbackType(data["type"]),
            category=FeedbackCategory(data["category"]),
            rating=data.get("rating"),
            thumbs_up=data.get("thumbs_up"),
            text=data.get("text"),
            correction=data.get("correction"),
            session_id=data.get("session_id"),
            message_id=data.get("message_id"),
            user_id=data.get("user_id"),
            sentiment=Sentiment(data["sentiment"]) if data.get("sentiment") else None,
            keywords=data.get("keywords", []),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            processed=data.get("processed", False),
            action_taken=data.get("action_taken"),
            metadata=data.get("metadata", {})
        )


@dataclass
class FeedbackSummary:
    """Summary of feedback for a time period."""
    start_date: datetime
    end_date: datetime
    total_count: int = 0
    average_rating: float = 0.0
    thumbs_up_ratio: float = 0.0
    sentiment_breakdown: Dict[str, int] = field(default_factory=dict)
    category_breakdown: Dict[str, int] = field(default_factory=dict)
    top_keywords: List[Tuple[str, int]] = field(default_factory=list)
    common_issues: List[str] = field(default_factory=list)


# =============================================================================
# SENTIMENT ANALYZER
# =============================================================================

class SentimentAnalyzer:
    """Analyze feedback sentiment."""

    def __init__(self):
        # Simple keyword-based analysis
        self.positive_words = {
            "great", "excellent", "amazing", "awesome", "helpful", "good",
            "perfect", "thanks", "love", "fantastic", "wonderful", "best",
            "accurate", "useful", "clear", "fast", "easy"
        }
        self.negative_words = {
            "bad", "terrible", "awful", "wrong", "incorrect", "useless",
            "slow", "confusing", "frustrating", "broken", "error", "bug",
            "hate", "worst", "unhelpful", "inaccurate", "poor"
        }

    def analyze(self, text: str) -> Tuple[Sentiment, float, List[str]]:
        """Analyze text sentiment."""
        if not text:
            return Sentiment.NEUTRAL, 0.5, []

        words = set(text.lower().split())

        positive_count = len(words & self.positive_words)
        negative_count = len(words & self.negative_words)

        keywords = list(words & (self.positive_words | self.negative_words))

        if positive_count > negative_count:
            sentiment = Sentiment.POSITIVE
            score = min(1.0, 0.5 + (positive_count - negative_count) * 0.1)
        elif negative_count > positive_count:
            sentiment = Sentiment.NEGATIVE
            score = max(0.0, 0.5 - (negative_count - positive_count) * 0.1)
        else:
            sentiment = Sentiment.NEUTRAL
            score = 0.5

        return sentiment, score, keywords

    async def analyze_with_llm(
        self,
        text: str,
        llm_provider: Callable
    ) -> Tuple[Sentiment, float, List[str]]:
        """Analyze sentiment using LLM."""
        prompt = f"""Analyze the sentiment of this feedback:
"{text}"

Respond with JSON:
{{
    "sentiment": "positive" | "neutral" | "negative",
    "confidence": 0.0-1.0,
    "keywords": ["keyword1", "keyword2"]
}}"""

        try:
            response = await llm_provider(prompt)
            data = json.loads(response)

            sentiment = Sentiment(data["sentiment"])
            score = data.get("confidence", 0.5)
            keywords = data.get("keywords", [])

            return sentiment, score, keywords
        except:
            # Fallback to simple analysis
            return self.analyze(text)


# =============================================================================
# FEEDBACK STORE
# =============================================================================

class FeedbackStore:
    """Store and retrieve feedback."""

    def __init__(self, storage_path: str = None):
        self.feedback: Dict[str, Feedback] = {}
        self.by_session: Dict[str, List[str]] = defaultdict(list)
        self.by_user: Dict[str, List[str]] = defaultdict(list)
        self.by_category: Dict[FeedbackCategory, List[str]] = defaultdict(list)

        self.storage_path = Path(storage_path) if storage_path else None
        if self.storage_path:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            self._load()

    def _load(self) -> None:
        """Load feedback from storage."""
        if not self.storage_path:
            return

        feedback_file = self.storage_path / "feedback.json"
        if feedback_file.exists():
            try:
                with open(feedback_file) as f:
                    data = json.load(f)
                for item in data:
                    fb = Feedback.from_dict(item)
                    self._index(fb)
            except Exception as e:
                logger.error(f"Failed to load feedback: {e}")

    def _save(self) -> None:
        """Save feedback to storage."""
        if not self.storage_path:
            return

        feedback_file = self.storage_path / "feedback.json"
        try:
            with open(feedback_file, 'w') as f:
                json.dump([fb.to_dict() for fb in self.feedback.values()], f)
        except Exception as e:
            logger.error(f"Failed to save feedback: {e}")

    def _index(self, feedback: Feedback) -> None:
        """Add feedback to indexes."""
        self.feedback[feedback.id] = feedback

        if feedback.session_id:
            self.by_session[feedback.session_id].append(feedback.id)
        if feedback.user_id:
            self.by_user[feedback.user_id].append(feedback.id)
        self.by_category[feedback.category].append(feedback.id)

    def add(self, feedback: Feedback) -> None:
        """Add feedback."""
        self._index(feedback)
        self._save()
        logger.debug(f"Added feedback: {feedback.id}")

    def get(self, feedback_id: str) -> Optional[Feedback]:
        """Get feedback by ID."""
        return self.feedback.get(feedback_id)

    def get_by_session(self, session_id: str) -> List[Feedback]:
        """Get feedback for a session."""
        return [
            self.feedback[id]
            for id in self.by_session.get(session_id, [])
        ]

    def get_by_user(self, user_id: str) -> List[Feedback]:
        """Get feedback from a user."""
        return [
            self.feedback[id]
            for id in self.by_user.get(user_id, [])
        ]

    def get_by_category(self, category: FeedbackCategory) -> List[Feedback]:
        """Get feedback by category."""
        return [
            self.feedback[id]
            for id in self.by_category.get(category, [])
        ]

    def get_recent(
        self,
        days: int = 7,
        limit: int = 100
    ) -> List[Feedback]:
        """Get recent feedback."""
        cutoff = datetime.now() - timedelta(days=days)
        recent = [
            fb for fb in self.feedback.values()
            if fb.timestamp >= cutoff
        ]
        recent.sort(key=lambda x: x.timestamp, reverse=True)
        return recent[:limit]

    def get_unprocessed(self) -> List[Feedback]:
        """Get unprocessed feedback."""
        return [
            fb for fb in self.feedback.values()
            if not fb.processed
        ]

    def update(self, feedback: Feedback) -> None:
        """Update feedback."""
        if feedback.id in self.feedback:
            self.feedback[feedback.id] = feedback
            self._save()


# =============================================================================
# FEEDBACK COLLECTOR
# =============================================================================

class FeedbackCollector:
    """Collect user feedback."""

    def __init__(
        self,
        store: FeedbackStore,
        analyzer: SentimentAnalyzer = None
    ):
        self.store = store
        self.analyzer = analyzer or SentimentAnalyzer()

    async def collect_rating(
        self,
        rating: int,
        category: FeedbackCategory = FeedbackCategory.OTHER,
        session_id: str = None,
        message_id: str = None,
        user_id: str = None,
        text: str = None
    ) -> Feedback:
        """Collect rating feedback (1-5)."""
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")

        sentiment = None
        keywords = []

        if text:
            sentiment, _, keywords = self.analyzer.analyze(text)
        else:
            if rating >= 4:
                sentiment = Sentiment.POSITIVE
            elif rating <= 2:
                sentiment = Sentiment.NEGATIVE
            else:
                sentiment = Sentiment.NEUTRAL

        feedback = Feedback(
            id=str(uuid4()),
            type=FeedbackType.RATING,
            category=category,
            rating=rating,
            text=text,
            session_id=session_id,
            message_id=message_id,
            user_id=user_id,
            sentiment=sentiment,
            keywords=keywords
        )

        self.store.add(feedback)
        return feedback

    async def collect_thumbs(
        self,
        thumbs_up: bool,
        category: FeedbackCategory = FeedbackCategory.HELPFULNESS,
        session_id: str = None,
        message_id: str = None,
        user_id: str = None,
        agent_response: str = None,
        user_query: str = None
    ) -> Feedback:
        """Collect thumbs up/down feedback."""
        feedback = Feedback(
            id=str(uuid4()),
            type=FeedbackType.THUMBS,
            category=category,
            thumbs_up=thumbs_up,
            session_id=session_id,
            message_id=message_id,
            user_id=user_id,
            agent_response=agent_response,
            user_query=user_query,
            sentiment=Sentiment.POSITIVE if thumbs_up else Sentiment.NEGATIVE
        )

        self.store.add(feedback)
        return feedback

    async def collect_text(
        self,
        text: str,
        category: FeedbackCategory = FeedbackCategory.OTHER,
        session_id: str = None,
        user_id: str = None
    ) -> Feedback:
        """Collect text feedback."""
        sentiment, _, keywords = self.analyzer.analyze(text)

        feedback = Feedback(
            id=str(uuid4()),
            type=FeedbackType.TEXT,
            category=category,
            text=text,
            session_id=session_id,
            user_id=user_id,
            sentiment=sentiment,
            keywords=keywords
        )

        self.store.add(feedback)
        return feedback

    async def collect_correction(
        self,
        original_response: str,
        correction: str,
        user_query: str = None,
        session_id: str = None,
        user_id: str = None
    ) -> Feedback:
        """Collect correction feedback."""
        feedback = Feedback(
            id=str(uuid4()),
            type=FeedbackType.CORRECTION,
            category=FeedbackCategory.ACCURACY,
            agent_response=original_response,
            correction=correction,
            user_query=user_query,
            session_id=session_id,
            user_id=user_id,
            sentiment=Sentiment.NEGATIVE
        )

        self.store.add(feedback)
        return feedback

    async def collect_suggestion(
        self,
        suggestion: str,
        category: FeedbackCategory = FeedbackCategory.OTHER,
        session_id: str = None,
        user_id: str = None
    ) -> Feedback:
        """Collect improvement suggestion."""
        feedback = Feedback(
            id=str(uuid4()),
            type=FeedbackType.SUGGESTION,
            category=category,
            text=suggestion,
            session_id=session_id,
            user_id=user_id,
            sentiment=Sentiment.NEUTRAL
        )

        self.store.add(feedback)
        return feedback


# =============================================================================
# FEEDBACK AGGREGATOR
# =============================================================================

class FeedbackAggregator:
    """Aggregate and summarize feedback."""

    def __init__(self, store: FeedbackStore):
        self.store = store

    def get_summary(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        user_id: str = None,
        session_id: str = None
    ) -> FeedbackSummary:
        """Get feedback summary."""
        # Default to last 30 days
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        # Filter feedback
        feedback_list = list(self.store.feedback.values())
        feedback_list = [
            fb for fb in feedback_list
            if start_date <= fb.timestamp <= end_date
        ]

        if user_id:
            feedback_list = [fb for fb in feedback_list if fb.user_id == user_id]
        if session_id:
            feedback_list = [fb for fb in feedback_list if fb.session_id == session_id]

        summary = FeedbackSummary(
            start_date=start_date,
            end_date=end_date,
            total_count=len(feedback_list)
        )

        if not feedback_list:
            return summary

        # Calculate average rating
        ratings = [fb.rating for fb in feedback_list if fb.rating is not None]
        if ratings:
            summary.average_rating = sum(ratings) / len(ratings)

        # Calculate thumbs ratio
        thumbs = [fb.thumbs_up for fb in feedback_list if fb.thumbs_up is not None]
        if thumbs:
            summary.thumbs_up_ratio = sum(1 for t in thumbs if t) / len(thumbs)

        # Sentiment breakdown
        for fb in feedback_list:
            if fb.sentiment:
                key = fb.sentiment.value
                summary.sentiment_breakdown[key] = summary.sentiment_breakdown.get(key, 0) + 1

        # Category breakdown
        for fb in feedback_list:
            key = fb.category.value
            summary.category_breakdown[key] = summary.category_breakdown.get(key, 0) + 1

        # Top keywords
        keyword_counts: Dict[str, int] = defaultdict(int)
        for fb in feedback_list:
            for keyword in fb.keywords:
                keyword_counts[keyword] += 1
        summary.top_keywords = sorted(
            keyword_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        # Common issues (from negative feedback)
        negative = [
            fb for fb in feedback_list
            if fb.sentiment == Sentiment.NEGATIVE and fb.text
        ]
        summary.common_issues = [fb.text[:100] for fb in negative[:5]]

        return summary

    def get_trends(
        self,
        days: int = 30,
        granularity: str = "day"
    ) -> List[Dict[str, Any]]:
        """Get feedback trends over time."""
        start = datetime.now() - timedelta(days=days)
        feedback_list = [
            fb for fb in self.store.feedback.values()
            if fb.timestamp >= start
        ]

        # Group by date
        by_date: Dict[str, List[Feedback]] = defaultdict(list)
        for fb in feedback_list:
            if granularity == "day":
                key = fb.timestamp.strftime("%Y-%m-%d")
            elif granularity == "week":
                key = fb.timestamp.strftime("%Y-W%W")
            else:
                key = fb.timestamp.strftime("%Y-%m")
            by_date[key].append(fb)

        trends = []
        for date, fbs in sorted(by_date.items()):
            ratings = [fb.rating for fb in fbs if fb.rating]
            thumbs = [fb.thumbs_up for fb in fbs if fb.thumbs_up is not None]

            trends.append({
                "date": date,
                "count": len(fbs),
                "avg_rating": sum(ratings) / len(ratings) if ratings else None,
                "thumbs_up_ratio": sum(1 for t in thumbs if t) / len(thumbs) if thumbs else None,
                "positive": sum(1 for fb in fbs if fb.sentiment == Sentiment.POSITIVE),
                "negative": sum(1 for fb in fbs if fb.sentiment == Sentiment.NEGATIVE)
            })

        return trends


# =============================================================================
# FEEDBACK LEARNER
# =============================================================================

class FeedbackLearner:
    """Learn from feedback to improve responses."""

    def __init__(
        self,
        store: FeedbackStore,
        llm_provider: Callable = None
    ):
        self.store = store
        self.llm_provider = llm_provider
        self.learned_corrections: Dict[str, str] = {}

    async def process_feedback(self, feedback: Feedback) -> Optional[str]:
        """Process feedback and extract learnings."""
        if feedback.processed:
            return None

        action = None

        if feedback.type == FeedbackType.CORRECTION:
            # Store correction for future reference
            if feedback.user_query and feedback.correction:
                self.learned_corrections[feedback.user_query] = feedback.correction
                action = "stored_correction"

        elif feedback.type == FeedbackType.THUMBS and not feedback.thumbs_up:
            # Analyze negative response
            if self.llm_provider and feedback.agent_response:
                action = await self._analyze_negative_response(
                    feedback.user_query,
                    feedback.agent_response
                )

        # Mark as processed
        feedback.processed = True
        feedback.action_taken = action
        self.store.update(feedback)

        return action

    async def _analyze_negative_response(
        self,
        query: str,
        response: str
    ) -> str:
        """Analyze why a response received negative feedback."""
        if not self.llm_provider:
            return "no_llm_available"

        prompt = f"""Analyze why this response might have received negative feedback:

User Query: {query}
Agent Response: {response}

What could be improved? Respond briefly."""

        try:
            analysis = await self.llm_provider(prompt)
            logger.info(f"Response analysis: {analysis}")
            return "analyzed"
        except:
            return "analysis_failed"

    def get_correction(self, query: str) -> Optional[str]:
        """Get learned correction for a query."""
        return self.learned_corrections.get(query)

    async def generate_improvement_report(self) -> Dict[str, Any]:
        """Generate improvement suggestions based on feedback."""
        unprocessed = self.store.get_unprocessed()
        recent = self.store.get_recent(days=7)

        # Process unprocessed
        for fb in unprocessed:
            await self.process_feedback(fb)

        # Aggregate insights
        negative = [fb for fb in recent if fb.sentiment == Sentiment.NEGATIVE]
        corrections = [fb for fb in recent if fb.type == FeedbackType.CORRECTION]
        suggestions = [fb for fb in recent if fb.type == FeedbackType.SUGGESTION]

        # Category issues
        category_issues: Dict[str, int] = defaultdict(int)
        for fb in negative:
            category_issues[fb.category.value] += 1

        return {
            "period": "last_7_days",
            "total_feedback": len(recent),
            "negative_feedback": len(negative),
            "corrections_received": len(corrections),
            "suggestions_received": len(suggestions),
            "problematic_categories": sorted(
                category_issues.items(),
                key=lambda x: x[1],
                reverse=True
            ),
            "common_issues": [
                {
                    "text": fb.text[:200] if fb.text else fb.agent_response[:200] if fb.agent_response else "",
                    "category": fb.category.value
                }
                for fb in negative[:5]
            ],
            "user_suggestions": [
                fb.text for fb in suggestions[:5]
            ],
            "learned_corrections": len(self.learned_corrections)
        }


# =============================================================================
# MAIN
# =============================================================================

async def demo():
    """Demo feedback system."""
    # Create components
    store = FeedbackStore()
    analyzer = SentimentAnalyzer()
    collector = FeedbackCollector(store, analyzer)
    aggregator = FeedbackAggregator(store)
    learner = FeedbackLearner(store)

    # Collect some feedback
    print("Collecting feedback...")

    await collector.collect_rating(
        rating=5,
        category=FeedbackCategory.HELPFULNESS,
        text="Great response, very helpful!",
        session_id="session1"
    )

    await collector.collect_rating(
        rating=2,
        category=FeedbackCategory.ACCURACY,
        text="The information was wrong",
        session_id="session1"
    )

    await collector.collect_thumbs(
        thumbs_up=True,
        session_id="session2"
    )

    await collector.collect_thumbs(
        thumbs_up=False,
        agent_response="2 + 2 = 5",
        user_query="What is 2 + 2?",
        session_id="session2"
    )

    await collector.collect_correction(
        original_response="The capital of France is London",
        correction="The capital of France is Paris",
        user_query="What is the capital of France?",
        session_id="session3"
    )

    await collector.collect_suggestion(
        suggestion="It would be great to have voice input",
        category=FeedbackCategory.OTHER
    )

    print(f"Stored {len(store.feedback)} feedback entries\n")

    # Get summary
    summary = aggregator.get_summary()
    print("Feedback Summary:")
    print(f"  Total: {summary.total_count}")
    print(f"  Average Rating: {summary.average_rating:.1f}")
    print(f"  Thumbs Up Ratio: {summary.thumbs_up_ratio:.0%}")
    print(f"  Sentiment: {summary.sentiment_breakdown}")
    print(f"  Categories: {summary.category_breakdown}")
    print(f"  Top Keywords: {summary.top_keywords}\n")

    # Process and learn
    report = await learner.generate_improvement_report()
    print("Improvement Report:")
    print(f"  Negative Feedback: {report['negative_feedback']}")
    print(f"  Corrections: {report['corrections_received']}")
    print(f"  Suggestions: {report['suggestions_received']}")
    print(f"  Learned Corrections: {report['learned_corrections']}")

    # Test learned correction
    correction = learner.get_correction("What is the capital of France?")
    if correction:
        print(f"\nLearned correction: {correction}")


if __name__ == "__main__":
    asyncio.run(demo())
