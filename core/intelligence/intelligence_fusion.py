"""
BAEL Intelligence Fusion
=========================

Combine insights from multiple sources.
Creates unified understanding from diverse inputs.

Features:
- Multi-source aggregation
- Insight correlation
- Confidence weighting
- Conflict resolution
- Synthesis generation
"""

import asyncio
import hashlib
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class InsightType(Enum):
    """Types of insights."""
    PATTERN = "pattern"
    ARCHITECTURE = "architecture"
    BEST_PRACTICE = "best_practice"
    ANTI_PATTERN = "anti_pattern"
    OPTIMIZATION = "optimization"
    SECURITY = "security"
    DEPENDENCY = "dependency"
    QUALITY = "quality"


class SourceType(Enum):
    """Insight source types."""
    CODE_ANALYSIS = "code_analysis"
    PATTERN_LEARNING = "pattern_learning"
    REPO_SEARCH = "repo_search"
    KNOWLEDGE_BASE = "knowledge_base"
    USER_FEEDBACK = "user_feedback"
    EXTERNAL_DOCS = "external_docs"


class FusionStrategy(Enum):
    """Fusion strategies."""
    WEIGHTED_AVERAGE = "weighted_average"
    VOTING = "voting"
    CONFIDENCE_MAX = "confidence_max"
    BAYESIAN = "bayesian"


@dataclass
class RawInsight:
    """A raw insight from a source."""
    id: str
    content: Dict[str, Any]

    # Source
    source_type: SourceType
    source_id: str = ""

    # Classification
    insight_type: InsightType = InsightType.PATTERN

    # Confidence
    confidence: float = 0.5

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)


@dataclass
class FusedInsight:
    """A fused insight from multiple sources."""
    id: str
    title: str
    description: str

    # Classification
    insight_type: InsightType = InsightType.PATTERN

    # Fused content
    content: Dict[str, Any] = field(default_factory=dict)

    # Sources
    source_insights: List[str] = field(default_factory=list)
    source_count: int = 0

    # Confidence
    confidence: float = 0.0
    agreement_score: float = 0.0

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)


@dataclass
class InsightCluster:
    """A cluster of related insights."""
    id: str
    insights: List[str] = field(default_factory=list)
    centroid: Dict[str, Any] = field(default_factory=dict)
    coherence: float = 0.0


@dataclass
class FusionConfig:
    """Fusion configuration."""
    # Strategy
    strategy: FusionStrategy = FusionStrategy.WEIGHTED_AVERAGE

    # Thresholds
    min_confidence: float = 0.3
    min_sources: int = 1
    agreement_threshold: float = 0.6

    # Source weights
    source_weights: Dict[str, float] = field(default_factory=lambda: {
        SourceType.CODE_ANALYSIS.value: 1.0,
        SourceType.PATTERN_LEARNING.value: 0.9,
        SourceType.REPO_SEARCH.value: 0.8,
        SourceType.KNOWLEDGE_BASE.value: 0.85,
        SourceType.USER_FEEDBACK.value: 1.1,
        SourceType.EXTERNAL_DOCS.value: 0.7,
    })


class IntelligenceFusion:
    """
    Intelligence fusion system for BAEL.
    """

    def __init__(
        self,
        config: Optional[FusionConfig] = None,
    ):
        self.config = config or FusionConfig()

        # Raw insights storage
        self.raw_insights: Dict[str, RawInsight] = {}

        # Fused insights
        self.fused_insights: Dict[str, FusedInsight] = {}

        # Clusters
        self.clusters: Dict[str, InsightCluster] = {}

        # Correlation matrix
        self._correlations: Dict[Tuple[str, str], float] = {}

        # Stats
        self.stats = {
            "raw_insights": 0,
            "fused_insights": 0,
            "fusions_performed": 0,
        }

    def add_insight(
        self,
        content: Dict[str, Any],
        source_type: SourceType,
        insight_type: InsightType = InsightType.PATTERN,
        confidence: float = 0.5,
        source_id: str = "",
        tags: Optional[List[str]] = None,
    ) -> RawInsight:
        """
        Add a raw insight.

        Args:
            content: Insight content
            source_type: Type of source
            insight_type: Type of insight
            confidence: Confidence score
            source_id: Source identifier
            tags: Optional tags

        Returns:
            RawInsight
        """
        insight_id = hashlib.md5(
            f"{content}:{datetime.now().timestamp()}".encode()
        ).hexdigest()[:12]

        insight = RawInsight(
            id=insight_id,
            content=content,
            source_type=source_type,
            source_id=source_id,
            insight_type=insight_type,
            confidence=confidence,
            tags=tags or [],
        )

        self.raw_insights[insight_id] = insight
        self.stats["raw_insights"] += 1

        return insight

    async def fuse(
        self,
        insight_ids: Optional[List[str]] = None,
        insight_type: Optional[InsightType] = None,
    ) -> List[FusedInsight]:
        """
        Fuse insights into unified understanding.

        Args:
            insight_ids: Optional list of insight IDs to fuse
            insight_type: Optional filter by insight type

        Returns:
            List of fused insights
        """
        self.stats["fusions_performed"] += 1

        # Get insights to fuse
        if insight_ids:
            insights = [self.raw_insights[id] for id in insight_ids if id in self.raw_insights]
        else:
            insights = list(self.raw_insights.values())

        # Filter by type
        if insight_type:
            insights = [i for i in insights if i.insight_type == insight_type]

        # Filter by confidence
        insights = [i for i in insights if i.confidence >= self.config.min_confidence]

        if not insights:
            return []

        # Cluster related insights
        clusters = self._cluster_insights(insights)

        # Fuse each cluster
        fused = []
        for cluster in clusters:
            fused_insight = await self._fuse_cluster(cluster)
            if fused_insight:
                self.fused_insights[fused_insight.id] = fused_insight
                fused.append(fused_insight)

        self.stats["fused_insights"] += len(fused)

        return fused

    def _cluster_insights(
        self,
        insights: List[RawInsight],
    ) -> List[List[RawInsight]]:
        """Cluster related insights."""
        if not insights:
            return []

        # Simple clustering by insight type and tags
        clusters = defaultdict(list)

        for insight in insights:
            # Create cluster key
            key = insight.insight_type.value
            if insight.tags:
                key += ":" + ":".join(sorted(insight.tags[:2]))

            clusters[key].append(insight)

        return list(clusters.values())

    async def _fuse_cluster(
        self,
        cluster: List[RawInsight],
    ) -> Optional[FusedInsight]:
        """Fuse a cluster of insights."""
        if len(cluster) < self.config.min_sources:
            # Single insight, just promote it
            if cluster:
                insight = cluster[0]
                return FusedInsight(
                    id=hashlib.md5(f"fused:{insight.id}".encode()).hexdigest()[:12],
                    title=insight.content.get("title", "Insight"),
                    description=insight.content.get("description", str(insight.content)),
                    insight_type=insight.insight_type,
                    content=insight.content,
                    source_insights=[insight.id],
                    source_count=1,
                    confidence=insight.confidence,
                    agreement_score=1.0,
                    tags=insight.tags,
                )
            return None

        # Apply fusion strategy
        if self.config.strategy == FusionStrategy.WEIGHTED_AVERAGE:
            return self._fuse_weighted_average(cluster)
        elif self.config.strategy == FusionStrategy.VOTING:
            return self._fuse_voting(cluster)
        elif self.config.strategy == FusionStrategy.CONFIDENCE_MAX:
            return self._fuse_confidence_max(cluster)
        else:
            return self._fuse_bayesian(cluster)

    def _fuse_weighted_average(
        self,
        cluster: List[RawInsight],
    ) -> FusedInsight:
        """Fuse using weighted average."""
        # Calculate weighted content
        fused_content = {}
        total_weight = 0

        for insight in cluster:
            weight = self.config.source_weights.get(
                insight.source_type.value, 1.0
            ) * insight.confidence

            total_weight += weight

            # Merge content with weights
            for key, value in insight.content.items():
                if key not in fused_content:
                    fused_content[key] = {"value": value, "weight": weight}
                else:
                    # For numeric values, weight them
                    if isinstance(value, (int, float)) and isinstance(
                        fused_content[key]["value"], (int, float)
                    ):
                        old_val = fused_content[key]["value"]
                        old_weight = fused_content[key]["weight"]
                        new_val = (old_val * old_weight + value * weight) / (old_weight + weight)
                        fused_content[key] = {"value": new_val, "weight": old_weight + weight}
                    else:
                        # Keep highest weight value
                        if weight > fused_content[key]["weight"]:
                            fused_content[key] = {"value": value, "weight": weight}

        # Extract final values
        final_content = {k: v["value"] for k, v in fused_content.items()}

        # Calculate agreement
        agreement = self._calculate_agreement(cluster)

        # Calculate combined confidence
        avg_confidence = sum(i.confidence for i in cluster) / len(cluster)
        combined_confidence = avg_confidence * (0.5 + 0.5 * agreement)

        # Collect tags
        all_tags = set()
        for insight in cluster:
            all_tags.update(insight.tags)

        # Generate title and description
        title = self._generate_title(cluster)
        description = self._generate_description(cluster, final_content)

        return FusedInsight(
            id=hashlib.md5(f"fused:{cluster[0].id}:{len(cluster)}".encode()).hexdigest()[:12],
            title=title,
            description=description,
            insight_type=cluster[0].insight_type,
            content=final_content,
            source_insights=[i.id for i in cluster],
            source_count=len(cluster),
            confidence=combined_confidence,
            agreement_score=agreement,
            recommendations=self._generate_recommendations(final_content),
            tags=list(all_tags),
        )

    def _fuse_voting(
        self,
        cluster: List[RawInsight],
    ) -> FusedInsight:
        """Fuse using voting."""
        # Count votes for each content value
        votes = defaultdict(lambda: defaultdict(int))

        for insight in cluster:
            for key, value in insight.content.items():
                str_value = str(value)
                votes[key][str_value] += 1

        # Select winning values
        final_content = {}
        for key, value_votes in votes.items():
            winner = max(value_votes.items(), key=lambda x: x[1])
            final_content[key] = winner[0]

        agreement = self._calculate_agreement(cluster)
        avg_confidence = sum(i.confidence for i in cluster) / len(cluster)

        return FusedInsight(
            id=hashlib.md5(f"voted:{cluster[0].id}".encode()).hexdigest()[:12],
            title=self._generate_title(cluster),
            description=self._generate_description(cluster, final_content),
            insight_type=cluster[0].insight_type,
            content=final_content,
            source_insights=[i.id for i in cluster],
            source_count=len(cluster),
            confidence=avg_confidence * agreement,
            agreement_score=agreement,
        )

    def _fuse_confidence_max(
        self,
        cluster: List[RawInsight],
    ) -> FusedInsight:
        """Fuse by taking highest confidence insight."""
        best = max(cluster, key=lambda i: i.confidence)

        return FusedInsight(
            id=hashlib.md5(f"max:{best.id}".encode()).hexdigest()[:12],
            title=best.content.get("title", "High Confidence Insight"),
            description=best.content.get("description", str(best.content)),
            insight_type=best.insight_type,
            content=best.content,
            source_insights=[i.id for i in cluster],
            source_count=len(cluster),
            confidence=best.confidence,
            agreement_score=self._calculate_agreement(cluster),
            tags=best.tags,
        )

    def _fuse_bayesian(
        self,
        cluster: List[RawInsight],
    ) -> FusedInsight:
        """Fuse using Bayesian approach."""
        # Simplified Bayesian fusion
        # Combine confidences using odds multiplication
        log_odds = 0

        for insight in cluster:
            p = insight.confidence
            if p > 0 and p < 1:
                import math
                log_odds += math.log(p / (1 - p))

        # Convert back to probability
        import math
        combined_conf = 1 / (1 + math.exp(-log_odds)) if log_odds != 0 else 0.5

        # Use most common values
        return self._fuse_voting(cluster)

    def _calculate_agreement(self, cluster: List[RawInsight]) -> float:
        """Calculate agreement score for cluster."""
        if len(cluster) <= 1:
            return 1.0

        # Compare content keys and values
        all_keys = set()
        for insight in cluster:
            all_keys.update(insight.content.keys())

        if not all_keys:
            return 1.0

        agreements = 0
        comparisons = 0

        for key in all_keys:
            values = [
                str(i.content.get(key)) for i in cluster if key in i.content
            ]
            if len(values) > 1:
                # Count matching pairs
                for i in range(len(values)):
                    for j in range(i + 1, len(values)):
                        comparisons += 1
                        if values[i] == values[j]:
                            agreements += 1

        return agreements / comparisons if comparisons > 0 else 1.0

    def _generate_title(self, cluster: List[RawInsight]) -> str:
        """Generate title for fused insight."""
        # Use title from content if available
        for insight in cluster:
            if "title" in insight.content:
                return insight.content["title"]
            if "name" in insight.content:
                return insight.content["name"]

        # Generate from type
        return f"{cluster[0].insight_type.value.replace('_', ' ').title()} Insight"

    def _generate_description(
        self,
        cluster: List[RawInsight],
        content: Dict[str, Any],
    ) -> str:
        """Generate description for fused insight."""
        # Use description from content
        for insight in cluster:
            if "description" in insight.content:
                return insight.content["description"]

        # Generate summary
        parts = []
        for key, value in list(content.items())[:3]:
            parts.append(f"{key}: {value}")

        return f"Fused from {len(cluster)} sources. " + "; ".join(parts)

    def _generate_recommendations(
        self,
        content: Dict[str, Any],
    ) -> List[str]:
        """Generate recommendations from content."""
        recs = []

        # Extract any recommendations from content
        if "recommendations" in content:
            recs.extend(content["recommendations"])

        if "suggestion" in content:
            recs.append(content["suggestion"])

        if "action" in content:
            recs.append(f"Consider: {content['action']}")

        return recs

    def correlate(
        self,
        insight_id1: str,
        insight_id2: str,
    ) -> float:
        """Get or calculate correlation between insights."""
        key = tuple(sorted([insight_id1, insight_id2]))

        if key in self._correlations:
            return self._correlations[key]

        insight1 = self.raw_insights.get(insight_id1)
        insight2 = self.raw_insights.get(insight_id2)

        if not insight1 or not insight2:
            return 0.0

        # Calculate correlation
        correlation = 0.0

        # Same type
        if insight1.insight_type == insight2.insight_type:
            correlation += 0.3

        # Shared tags
        shared_tags = set(insight1.tags) & set(insight2.tags)
        if shared_tags:
            correlation += 0.2 * len(shared_tags) / max(
                len(insight1.tags), len(insight2.tags), 1
            )

        # Content similarity
        shared_keys = set(insight1.content.keys()) & set(insight2.content.keys())
        if shared_keys:
            matching = sum(
                1 for k in shared_keys
                if insight1.content[k] == insight2.content[k]
            )
            correlation += 0.5 * matching / len(shared_keys)

        self._correlations[key] = correlation

        return correlation

    def get_related(
        self,
        insight_id: str,
        limit: int = 5,
    ) -> List[Tuple[str, float]]:
        """Get related insights."""
        related = []

        target = self.raw_insights.get(insight_id)
        if not target:
            return []

        for other_id in self.raw_insights:
            if other_id == insight_id:
                continue

            correlation = self.correlate(insight_id, other_id)
            if correlation > 0:
                related.append((other_id, correlation))

        related.sort(key=lambda x: x[1], reverse=True)

        return related[:limit]

    def get_insight(self, insight_id: str) -> Optional[FusedInsight]:
        """Get fused insight by ID."""
        return self.fused_insights.get(insight_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get fusion statistics."""
        return {
            **self.stats,
            "correlations_computed": len(self._correlations),
        }


def demo():
    """Demonstrate intelligence fusion."""
    import asyncio

    print("=" * 60)
    print("BAEL Intelligence Fusion Demo")
    print("=" * 60)

    fusion = IntelligenceFusion()

    # Add insights from different sources
    fusion.add_insight(
        content={
            "title": "Singleton Pattern Usage",
            "description": "Found singleton pattern in database module",
            "location": "db/connection.py",
        },
        source_type=SourceType.CODE_ANALYSIS,
        insight_type=InsightType.PATTERN,
        confidence=0.9,
        tags=["singleton", "database"],
    )

    fusion.add_insight(
        content={
            "title": "Singleton Pattern",
            "best_practice": "Use for shared resources",
            "caveat": "Consider thread safety",
        },
        source_type=SourceType.KNOWLEDGE_BASE,
        insight_type=InsightType.PATTERN,
        confidence=0.85,
        tags=["singleton"],
    )

    fusion.add_insight(
        content={
            "title": "Database Connection Pattern",
            "suggestion": "Implement connection pooling",
        },
        source_type=SourceType.EXTERNAL_DOCS,
        insight_type=InsightType.PATTERN,
        confidence=0.7,
        tags=["database", "connection"],
    )

    print(f"\nAdded {fusion.stats['raw_insights']} raw insights")

    # Fuse insights
    async def do_fusion():
        return await fusion.fuse(insight_type=InsightType.PATTERN)

    fused = asyncio.run(do_fusion())

    print(f"\nFused into {len(fused)} insights:")
    for insight in fused:
        print(f"\n  {insight.title}")
        print(f"  - Sources: {insight.source_count}")
        print(f"  - Confidence: {insight.confidence:.2f}")
        print(f"  - Agreement: {insight.agreement_score:.2f}")
        print(f"  - Tags: {', '.join(insight.tags)}")

    # Find related
    if fused:
        raw_ids = list(fusion.raw_insights.keys())
        if len(raw_ids) >= 2:
            corr = fusion.correlate(raw_ids[0], raw_ids[1])
            print(f"\nCorrelation between first two insights: {corr:.2f}")

    print(f"\nStats: {fusion.get_stats()}")


if __name__ == "__main__":
    demo()
