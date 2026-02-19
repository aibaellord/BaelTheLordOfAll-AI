"""
BAEL Response Aggregator
=========================

Intelligent aggregation of responses from multiple LLM providers.
Enables consensus, voting, and ensemble strategies for superior results.

Features:
- Parallel response collection
- Voting and consensus mechanisms
- Quality scoring and ranking
- Response merging and synthesis
- Contradiction detection
- Confidence calibration
- Best-of-N selection
"""

import asyncio
import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class AggregationStrategy(Enum):
    """Strategies for aggregating multiple responses."""
    FIRST_SUCCESS = "first_success"       # Return first successful response
    FASTEST = "fastest"                   # Return fastest response
    BEST_QUALITY = "best_quality"         # Score and return highest quality
    MAJORITY_VOTE = "majority_vote"       # Vote on structured answers
    CONSENSUS = "consensus"               # Find common ground
    MERGE = "merge"                       # Merge all responses
    LONGEST = "longest"                   # Return most detailed
    ENSEMBLE = "ensemble"                 # Weighted combination


@dataclass
class ScoredResponse:
    """Response with quality scores."""
    content: str
    provider: str
    model: str
    latency_ms: float
    quality_score: float = 0.0
    confidence: float = 0.0
    relevance_score: float = 0.0
    coherence_score: float = 0.0
    completeness_score: float = 0.0
    factuality_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsensusResult:
    """Result of consensus aggregation."""
    final_response: str
    strategy_used: AggregationStrategy
    num_responses: int
    agreement_score: float
    contributing_providers: List[str]
    individual_scores: List[ScoredResponse]
    contradictions: List[Dict[str, Any]] = field(default_factory=list)
    merged_insights: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResponseAggregator:
    """
    Aggregates and synthesizes responses from multiple LLM providers.
    """

    # Quality indicators (positive signals)
    QUALITY_SIGNALS = {
        "detailed": 0.1,
        "example": 0.1,
        "step": 0.05,
        "first": 0.02,
        "second": 0.02,
        "because": 0.05,
        "therefore": 0.05,
        "however": 0.05,
        "specifically": 0.05,
        "```": 0.15,  # Code blocks
    }

    # Negative quality signals
    NEGATIVE_SIGNALS = {
        "i cannot": -0.3,
        "i can't": -0.3,
        "i'm unable": -0.3,
        "as an ai": -0.2,
        "i don't have": -0.2,
        "i'm not sure": -0.1,
    }

    def __init__(
        self,
        default_strategy: AggregationStrategy = AggregationStrategy.BEST_QUALITY,
    ):
        self.default_strategy = default_strategy

    def _score_response(
        self,
        content: str,
        query: Optional[str] = None,
    ) -> Dict[str, float]:
        """Score a response on multiple dimensions."""
        content_lower = content.lower()

        # Quality score from signals
        quality_score = 0.5  # Base score
        for signal, weight in self.QUALITY_SIGNALS.items():
            if signal in content_lower:
                quality_score += weight
        for signal, weight in self.NEGATIVE_SIGNALS.items():
            if signal in content_lower:
                quality_score += weight

        quality_score = max(0.0, min(1.0, quality_score))

        # Coherence (sentence structure)
        sentences = content.split('.')
        avg_sentence_len = sum(len(s.split()) for s in sentences) / max(1, len(sentences))
        coherence_score = min(1.0, avg_sentence_len / 20)  # Optimal ~20 words

        # Completeness (length-based heuristic)
        word_count = len(content.split())
        completeness_score = min(1.0, word_count / 200)  # 200+ words = complete

        # Relevance (keyword overlap with query)
        relevance_score = 0.5
        if query:
            query_words = set(query.lower().split())
            content_words = set(content_lower.split())
            overlap = len(query_words & content_words)
            relevance_score = min(1.0, overlap / max(1, len(query_words)))

        # Confidence (presence of hedging language)
        confidence = 0.8
        hedging = ["might", "maybe", "perhaps", "possibly", "could be"]
        for hedge in hedging:
            if hedge in content_lower:
                confidence -= 0.1
        confidence = max(0.3, confidence)

        return {
            "quality_score": quality_score,
            "coherence_score": coherence_score,
            "completeness_score": completeness_score,
            "relevance_score": relevance_score,
            "confidence": confidence,
        }

    def score_responses(
        self,
        responses: List[Dict[str, Any]],
        query: Optional[str] = None,
    ) -> List[ScoredResponse]:
        """Score a list of responses."""
        scored = []

        for resp in responses:
            content = resp.get("content", "")
            scores = self._score_response(content, query)

            scored.append(ScoredResponse(
                content=content,
                provider=resp.get("provider", "unknown"),
                model=resp.get("model", "unknown"),
                latency_ms=resp.get("latency_ms", 0),
                quality_score=scores["quality_score"],
                confidence=scores["confidence"],
                relevance_score=scores["relevance_score"],
                coherence_score=scores["coherence_score"],
                completeness_score=scores["completeness_score"],
            ))

        return scored

    def _detect_contradictions(
        self,
        responses: List[ScoredResponse],
    ) -> List[Dict[str, Any]]:
        """Detect contradictions between responses."""
        contradictions = []

        # Simple contradiction detection via negation patterns
        for i, r1 in enumerate(responses):
            for r2 in responses[i+1:]:
                # Check for direct negations
                r1_lower = r1.content.lower()
                r2_lower = r2.content.lower()

                negation_pairs = [
                    ("is true", "is false"),
                    ("is correct", "is incorrect"),
                    ("yes", "no"),
                    ("can", "cannot"),
                    ("will", "will not"),
                ]

                for pos, neg in negation_pairs:
                    if (pos in r1_lower and neg in r2_lower) or \
                       (neg in r1_lower and pos in r2_lower):
                        contradictions.append({
                            "provider1": r1.provider,
                            "provider2": r2.provider,
                            "type": "negation",
                            "pattern": (pos, neg),
                        })

        return contradictions

    def _extract_key_points(self, content: str) -> List[str]:
        """Extract key points from response."""
        points = []

        # Look for bullet points
        bullet_pattern = r'[-•*]\s+(.+)'
        points.extend(re.findall(bullet_pattern, content))

        # Look for numbered points
        number_pattern = r'\d+[.)]\s+(.+)'
        points.extend(re.findall(number_pattern, content))

        # If no structured points, split by sentences
        if not points:
            sentences = content.split('.')
            points = [s.strip() for s in sentences if len(s.strip()) > 20][:5]

        return points

    def aggregate(
        self,
        responses: List[Dict[str, Any]],
        strategy: Optional[AggregationStrategy] = None,
        query: Optional[str] = None,
    ) -> ConsensusResult:
        """
        Aggregate multiple responses using specified strategy.

        Args:
            responses: List of response dicts with content, provider, model, latency_ms
            strategy: Aggregation strategy to use
            query: Original query for relevance scoring

        Returns:
            ConsensusResult with final response and metadata
        """
        strategy = strategy or self.default_strategy

        if not responses:
            return ConsensusResult(
                final_response="",
                strategy_used=strategy,
                num_responses=0,
                agreement_score=0.0,
                contributing_providers=[],
                individual_scores=[],
            )

        # Score all responses
        scored = self.score_responses(responses, query)

        # Sort by overall score
        def overall_score(r: ScoredResponse) -> float:
            return (
                r.quality_score * 0.3 +
                r.completeness_score * 0.25 +
                r.coherence_score * 0.2 +
                r.relevance_score * 0.15 +
                r.confidence * 0.1
            )

        scored.sort(key=overall_score, reverse=True)

        # Detect contradictions
        contradictions = self._detect_contradictions(scored)

        # Execute strategy
        if strategy == AggregationStrategy.FIRST_SUCCESS:
            final_response = responses[0]["content"]
            contributing = [responses[0].get("provider", "unknown")]

        elif strategy == AggregationStrategy.FASTEST:
            fastest = min(scored, key=lambda r: r.latency_ms)
            final_response = fastest.content
            contributing = [fastest.provider]

        elif strategy == AggregationStrategy.BEST_QUALITY:
            best = scored[0]
            final_response = best.content
            contributing = [best.provider]

        elif strategy == AggregationStrategy.LONGEST:
            longest = max(scored, key=lambda r: len(r.content))
            final_response = longest.content
            contributing = [longest.provider]

        elif strategy == AggregationStrategy.MAJORITY_VOTE:
            # Extract key answers and vote
            # Simplified: use first sentence as "answer"
            answers = [r.content.split('.')[0].strip().lower() for r in scored]
            most_common = Counter(answers).most_common(1)

            if most_common:
                winning_answer = most_common[0][0]
                for r in scored:
                    if r.content.split('.')[0].strip().lower() == winning_answer:
                        final_response = r.content
                        contributing = [r.provider for r in scored
                                       if r.content.split('.')[0].strip().lower() == winning_answer]
                        break
                else:
                    final_response = scored[0].content
                    contributing = [scored[0].provider]
            else:
                final_response = scored[0].content
                contributing = [scored[0].provider]

        elif strategy == AggregationStrategy.CONSENSUS:
            # Find common points across responses
            all_points = []
            for r in scored:
                points = self._extract_key_points(r.content)
                all_points.extend(points)

            # Count point frequencies (simplified)
            point_counter = Counter(p.lower()[:50] for p in all_points)
            common_points = [p for p, count in point_counter.most_common(5) if count > 1]

            if common_points:
                final_response = "Key consensus points:\n" + "\n".join(f"• {p}" for p in common_points)
                # Add best response as detail
                final_response += f"\n\nDetailed response:\n{scored[0].content}"
            else:
                final_response = scored[0].content

            contributing = [r.provider for r in scored]

        elif strategy == AggregationStrategy.MERGE:
            # Merge unique insights from all responses
            all_points = set()
            for r in scored:
                points = self._extract_key_points(r.content)
                all_points.update(points)

            merged = "Merged insights from multiple sources:\n\n"
            merged += "\n".join(f"• {p}" for p in list(all_points)[:10])
            final_response = merged
            contributing = [r.provider for r in scored]

        elif strategy == AggregationStrategy.ENSEMBLE:
            # Weighted combination based on scores
            # Use highest scored as base, append unique points from others
            base = scored[0]
            unique_additions = []

            for r in scored[1:]:
                points = self._extract_key_points(r.content)
                for p in points[:2]:  # Take top 2 points from each
                    if p.lower() not in base.content.lower():
                        unique_additions.append(f"[{r.provider}] {p}")

            final_response = base.content
            if unique_additions:
                final_response += "\n\nAdditional perspectives:\n"
                final_response += "\n".join(f"• {p}" for p in unique_additions[:5])

            contributing = [r.provider for r in scored]

        else:
            final_response = scored[0].content
            contributing = [scored[0].provider]

        # Calculate agreement score
        if len(scored) > 1:
            # Simple text similarity between responses
            def simple_similarity(a: str, b: str) -> float:
                a_words = set(a.lower().split())
                b_words = set(b.lower().split())
                intersection = len(a_words & b_words)
                union = len(a_words | b_words)
                return intersection / union if union > 0 else 0

            similarities = []
            for i, r1 in enumerate(scored):
                for r2 in scored[i+1:]:
                    similarities.append(simple_similarity(r1.content, r2.content))

            agreement_score = sum(similarities) / len(similarities) if similarities else 1.0
        else:
            agreement_score = 1.0

        return ConsensusResult(
            final_response=final_response,
            strategy_used=strategy,
            num_responses=len(responses),
            agreement_score=agreement_score,
            contributing_providers=contributing,
            individual_scores=scored,
            contradictions=contradictions,
            merged_insights=[p for r in scored for p in self._extract_key_points(r.content)[:2]],
        )


def demo():
    """Demonstrate response aggregation."""
    print("=" * 60)
    print("BAEL Response Aggregator Demo")
    print("=" * 60)

    aggregator = ResponseAggregator()

    # Simulated responses
    responses = [
        {
            "content": "Python is a high-level programming language. It's known for readability and simplicity. Here's an example:\n\n```python\nprint('Hello')\n```",
            "provider": "openrouter",
            "model": "gpt-4o",
            "latency_ms": 500,
        },
        {
            "content": "Python is an interpreted, high-level language. Key features:\n• Easy to learn\n• Large ecosystem\n• Great for beginners",
            "provider": "deepseek",
            "model": "deepseek-v3",
            "latency_ms": 300,
        },
        {
            "content": "Python is a versatile programming language used in web development, data science, AI, and automation. It has simple syntax.",
            "provider": "groq",
            "model": "llama-3.3-70b",
            "latency_ms": 150,
        },
    ]

    # Test different strategies
    for strategy in [
        AggregationStrategy.BEST_QUALITY,
        AggregationStrategy.FASTEST,
        AggregationStrategy.CONSENSUS,
    ]:
        result = aggregator.aggregate(responses, strategy=strategy, query="What is Python?")

        print(f"\n--- Strategy: {strategy.value} ---")
        print(f"Final response preview: {result.final_response[:100]}...")
        print(f"Contributing: {result.contributing_providers}")
        print(f"Agreement: {result.agreement_score:.2f}")
        print(f"Contradictions: {len(result.contradictions)}")


if __name__ == "__main__":
    demo()
