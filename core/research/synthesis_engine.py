"""
BAEL Synthesis Engine
======================

Synthesizes research findings into coherent summaries.
Combines information from multiple sources.

Features:
- Finding aggregation
- Conflict resolution
- Summary generation
- Key insight extraction
- Narrative construction
"""

import hashlib
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class FindingType(Enum):
    """Types of research findings."""
    FACT = "fact"
    CLAIM = "claim"
    OPINION = "opinion"
    STATISTIC = "statistic"
    DEFINITION = "definition"
    EXAMPLE = "example"
    QUOTE = "quote"
    CONCLUSION = "conclusion"


class ConfidenceLevel(Enum):
    """Confidence in a finding."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


class SynthesisStrategy(Enum):
    """Strategies for synthesis."""
    CONSENSUS = "consensus"  # Focus on agreed findings
    COMPREHENSIVE = "comprehensive"  # Include all perspectives
    CRITICAL = "critical"  # Focus on conflicts and debates
    CHRONOLOGICAL = "chronological"  # Order by time
    HIERARCHICAL = "hierarchical"  # Structure by importance


@dataclass
class Finding:
    """A research finding."""
    id: str
    content: str
    finding_type: FindingType

    # Source
    source_url: str = ""
    source_title: str = ""

    # Confidence
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    confidence_score: float = 0.5

    # Context
    topic: str = ""
    keywords: List[str] = field(default_factory=list)

    # Relations
    supports: List[str] = field(default_factory=list)  # IDs of supported findings
    contradicts: List[str] = field(default_factory=list)  # IDs of contradicted findings

    # Metadata
    extracted_at: datetime = field(default_factory=datetime.now)


@dataclass
class SynthesisSection:
    """A section of the synthesis."""
    title: str
    content: str

    # Findings
    findings: List[Finding] = field(default_factory=list)

    # Importance
    importance: float = 0.5


@dataclass
class Synthesis:
    """A synthesized research summary."""
    id: str
    topic: str

    # Summary
    summary: str = ""

    # Sections
    sections: List[SynthesisSection] = field(default_factory=list)

    # Key insights
    key_insights: List[str] = field(default_factory=list)

    # Conflicts
    conflicts: List[Dict[str, Any]] = field(default_factory=list)

    # Sources
    sources: List[str] = field(default_factory=list)
    source_count: int = 0

    # Findings
    finding_count: int = 0

    # Quality
    confidence: float = 0.5
    coverage: float = 0.5

    # Metadata
    strategy: SynthesisStrategy = SynthesisStrategy.COMPREHENSIVE
    synthesized_at: datetime = field(default_factory=datetime.now)


class SynthesisEngine:
    """
    Synthesis engine for BAEL.

    Synthesizes research findings.
    """

    def __init__(self):
        # Findings store
        self._findings: Dict[str, Finding] = {}

        # Topic groups
        self._by_topic: Dict[str, List[str]] = defaultdict(list)

        # Stats
        self.stats = {
            "findings_processed": 0,
            "syntheses_created": 0,
            "conflicts_detected": 0,
        }

    def add_finding(
        self,
        content: str,
        finding_type: FindingType = FindingType.FACT,
        source_url: str = "",
        source_title: str = "",
        topic: str = "",
        keywords: Optional[List[str]] = None,
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    ) -> Finding:
        """
        Add a research finding.

        Args:
            content: Finding content
            finding_type: Type of finding
            source_url: Source URL
            source_title: Source title
            topic: Topic category
            keywords: Related keywords
            confidence: Confidence level

        Returns:
            Created finding
        """
        finding_id = hashlib.md5(
            f"{content}:{source_url}".encode()
        ).hexdigest()[:12]

        finding = Finding(
            id=finding_id,
            content=content,
            finding_type=finding_type,
            source_url=source_url,
            source_title=source_title,
            topic=topic,
            keywords=keywords or [],
            confidence=confidence,
            confidence_score=self._confidence_to_score(confidence),
        )

        self._findings[finding_id] = finding
        self._by_topic[topic].append(finding_id)

        self.stats["findings_processed"] += 1

        return finding

    def _confidence_to_score(self, confidence: ConfidenceLevel) -> float:
        """Convert confidence level to score."""
        return {
            ConfidenceLevel.HIGH: 0.9,
            ConfidenceLevel.MEDIUM: 0.6,
            ConfidenceLevel.LOW: 0.3,
            ConfidenceLevel.UNCERTAIN: 0.1,
        }.get(confidence, 0.5)

    def synthesize(
        self,
        topic: str,
        findings: Optional[List[Finding]] = None,
        strategy: SynthesisStrategy = SynthesisStrategy.COMPREHENSIVE,
    ) -> Synthesis:
        """
        Synthesize findings on a topic.

        Args:
            topic: Topic to synthesize
            findings: Optional specific findings (uses stored if None)
            strategy: Synthesis strategy

        Returns:
            Synthesis result
        """
        synthesis_id = hashlib.md5(
            f"{topic}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        # Get findings
        if findings is None:
            finding_ids = self._by_topic.get(topic, [])
            findings = [self._findings[fid] for fid in finding_ids if fid in self._findings]

        synthesis = Synthesis(
            id=synthesis_id,
            topic=topic,
            strategy=strategy,
            finding_count=len(findings),
        )

        if not findings:
            return synthesis

        # Detect conflicts
        synthesis.conflicts = self._detect_conflicts(findings)
        self.stats["conflicts_detected"] += len(synthesis.conflicts)

        # Group findings
        grouped = self._group_findings(findings, strategy)

        # Generate sections
        synthesis.sections = self._generate_sections(grouped, strategy)

        # Extract key insights
        synthesis.key_insights = self._extract_insights(findings)

        # Generate summary
        synthesis.summary = self._generate_summary(synthesis)

        # Collect sources
        synthesis.sources = list({f.source_url for f in findings if f.source_url})
        synthesis.source_count = len(synthesis.sources)

        # Calculate quality metrics
        synthesis.confidence = self._calculate_confidence(findings)
        synthesis.coverage = self._calculate_coverage(findings, topic)

        self.stats["syntheses_created"] += 1

        return synthesis

    def _detect_conflicts(self, findings: List[Finding]) -> List[Dict[str, Any]]:
        """Detect conflicts between findings."""
        conflicts = []

        # Simple keyword-based conflict detection
        negation_pairs = [
            ("increase", "decrease"),
            ("improve", "worsen"),
            ("support", "oppose"),
            ("effective", "ineffective"),
            ("true", "false"),
            ("positive", "negative"),
        ]

        for i, f1 in enumerate(findings):
            for f2 in findings[i+1:]:
                content1 = f1.content.lower()
                content2 = f2.content.lower()

                for pos, neg in negation_pairs:
                    if pos in content1 and neg in content2:
                        conflicts.append({
                            "finding1_id": f1.id,
                            "finding2_id": f2.id,
                            "type": "negation",
                            "keywords": [pos, neg],
                        })
                        f1.contradicts.append(f2.id)
                        f2.contradicts.append(f1.id)
                        break

        return conflicts

    def _group_findings(
        self,
        findings: List[Finding],
        strategy: SynthesisStrategy,
    ) -> Dict[str, List[Finding]]:
        """Group findings based on strategy."""
        groups = defaultdict(list)

        if strategy == SynthesisStrategy.HIERARCHICAL:
            # Group by confidence
            for finding in findings:
                groups[finding.confidence.value].append(finding)

        elif strategy == SynthesisStrategy.CHRONOLOGICAL:
            # Group by time periods (simplified)
            for finding in findings:
                period = finding.extracted_at.strftime("%Y-%m")
                groups[period].append(finding)

        elif strategy == SynthesisStrategy.CRITICAL:
            # Separate conflicting and non-conflicting
            conflicting_ids = set()
            for finding in findings:
                conflicting_ids.update(finding.contradicts)
                if finding.id in conflicting_ids:
                    groups["conflicting"].append(finding)
                else:
                    groups["consensus"].append(finding)

        else:  # COMPREHENSIVE or CONSENSUS
            # Group by finding type
            for finding in findings:
                groups[finding.finding_type.value].append(finding)

        return groups

    def _generate_sections(
        self,
        grouped: Dict[str, List[Finding]],
        strategy: SynthesisStrategy,
    ) -> List[SynthesisSection]:
        """Generate synthesis sections."""
        sections = []

        # Sort groups by importance
        group_importance = {
            # By type
            FindingType.CONCLUSION.value: 0.9,
            FindingType.STATISTIC.value: 0.8,
            FindingType.FACT.value: 0.7,
            FindingType.CLAIM.value: 0.6,
            # By confidence
            ConfidenceLevel.HIGH.value: 0.9,
            ConfidenceLevel.MEDIUM.value: 0.6,
            # By conflict
            "consensus": 0.8,
            "conflicting": 0.7,
        }

        sorted_groups = sorted(
            grouped.items(),
            key=lambda x: group_importance.get(x[0], 0.5),
            reverse=True,
        )

        for group_name, group_findings in sorted_groups:
            if not group_findings:
                continue

            # Generate section content
            content_parts = []
            for finding in group_findings[:10]:  # Limit per section
                content_parts.append(f"• {finding.content}")

            section = SynthesisSection(
                title=group_name.replace("_", " ").title(),
                content="\n".join(content_parts),
                findings=group_findings,
                importance=group_importance.get(group_name, 0.5),
            )

            sections.append(section)

        return sections

    def _extract_insights(self, findings: List[Finding]) -> List[str]:
        """Extract key insights from findings."""
        insights = []

        # High confidence findings
        high_conf = [f for f in findings if f.confidence == ConfidenceLevel.HIGH]
        for finding in high_conf[:3]:
            insights.append(finding.content)

        # Conclusions
        conclusions = [f for f in findings if f.finding_type == FindingType.CONCLUSION]
        for finding in conclusions[:2]:
            if finding.content not in insights:
                insights.append(finding.content)

        # Statistics
        stats = [f for f in findings if f.finding_type == FindingType.STATISTIC]
        for finding in stats[:2]:
            if finding.content not in insights:
                insights.append(finding.content)

        return insights[:7]

    def _generate_summary(self, synthesis: Synthesis) -> str:
        """Generate synthesis summary."""
        parts = []

        # Opening
        parts.append(f"Research synthesis on '{synthesis.topic}'")
        parts.append(f"based on {synthesis.finding_count} findings from {synthesis.source_count} sources.")

        # Key insights
        if synthesis.key_insights:
            parts.append("\nKey insights:")
            for i, insight in enumerate(synthesis.key_insights[:3], 1):
                parts.append(f"{i}. {insight}")

        # Conflicts
        if synthesis.conflicts:
            parts.append(f"\nNote: {len(synthesis.conflicts)} conflicting findings identified.")

        # Confidence
        parts.append(f"\nOverall confidence: {synthesis.confidence:.0%}")

        return "\n".join(parts)

    def _calculate_confidence(self, findings: List[Finding]) -> float:
        """Calculate overall confidence."""
        if not findings:
            return 0.0

        scores = [f.confidence_score for f in findings]
        return sum(scores) / len(scores)

    def _calculate_coverage(self, findings: List[Finding], topic: str) -> float:
        """Calculate topic coverage."""
        # Simplified: based on finding diversity
        types_covered = len(set(f.finding_type for f in findings))
        sources_used = len(set(f.source_url for f in findings if f.source_url))

        type_coverage = types_covered / len(FindingType)
        source_diversity = min(1.0, sources_used / 5)

        return (type_coverage + source_diversity) / 2

    def get_findings_by_topic(self, topic: str) -> List[Finding]:
        """Get all findings for a topic."""
        finding_ids = self._by_topic.get(topic, [])
        return [self._findings[fid] for fid in finding_ids if fid in self._findings]

    def merge_findings(
        self,
        findings: List[Finding],
    ) -> Finding:
        """Merge multiple similar findings into one."""
        if not findings:
            raise ValueError("No findings to merge")

        # Use highest confidence finding as base
        findings.sort(key=lambda f: f.confidence_score, reverse=True)
        base = findings[0]

        # Combine content
        combined_content = base.content
        for f in findings[1:]:
            if f.content not in combined_content:
                combined_content += f" Additionally, {f.content.lower()}"

        merged_id = hashlib.md5(combined_content.encode()).hexdigest()[:12]

        # Combine sources
        sources = list(set(f.source_url for f in findings if f.source_url))

        return Finding(
            id=merged_id,
            content=combined_content[:500],
            finding_type=base.finding_type,
            source_url=sources[0] if sources else "",
            topic=base.topic,
            keywords=list(set(k for f in findings for k in f.keywords)),
            confidence=base.confidence,
            supports=[f.id for f in findings[1:]],
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            **self.stats,
            "stored_findings": len(self._findings),
            "topics": len(self._by_topic),
        }


def demo():
    """Demonstrate synthesis engine."""
    print("=" * 60)
    print("BAEL Synthesis Engine Demo")
    print("=" * 60)

    engine = SynthesisEngine()

    # Add findings
    print("\nAdding research findings...")

    engine.add_finding(
        content="Transformer models achieve state-of-the-art results on NLP tasks",
        finding_type=FindingType.FACT,
        topic="transformers",
        source_title="Attention Is All You Need",
        confidence=ConfidenceLevel.HIGH,
    )

    engine.add_finding(
        content="BERT improves performance on 11 NLP benchmarks",
        finding_type=FindingType.STATISTIC,
        topic="transformers",
        source_title="BERT Paper",
        confidence=ConfidenceLevel.HIGH,
    )

    engine.add_finding(
        content="GPT-3 contains 175 billion parameters",
        finding_type=FindingType.STATISTIC,
        topic="transformers",
        source_title="GPT-3 Paper",
        confidence=ConfidenceLevel.HIGH,
    )

    engine.add_finding(
        content="Large language models may exhibit emergent capabilities",
        finding_type=FindingType.CLAIM,
        topic="transformers",
        source_title="Emergent Abilities Paper",
        confidence=ConfidenceLevel.MEDIUM,
    )

    engine.add_finding(
        content="Scaling laws predict model performance improvements",
        finding_type=FindingType.CONCLUSION,
        topic="transformers",
        source_title="Scaling Laws Paper",
        confidence=ConfidenceLevel.HIGH,
    )

    print(f"  Added {engine.stats['findings_processed']} findings")

    # Synthesize
    print("\nSynthesizing findings...")

    synthesis = engine.synthesize(
        topic="transformers",
        strategy=SynthesisStrategy.COMPREHENSIVE,
    )

    print(f"\nSynthesis: {synthesis.topic}")
    print(f"  Findings: {synthesis.finding_count}")
    print(f"  Sources: {synthesis.source_count}")
    print(f"  Confidence: {synthesis.confidence:.0%}")
    print(f"  Coverage: {synthesis.coverage:.0%}")

    print(f"\nSections ({len(synthesis.sections)}):")
    for section in synthesis.sections:
        print(f"  - {section.title} ({len(section.findings)} findings)")

    print(f"\nKey Insights:")
    for insight in synthesis.key_insights:
        print(f"  • {insight[:70]}...")

    if synthesis.conflicts:
        print(f"\nConflicts: {len(synthesis.conflicts)}")

    print(f"\nSummary:")
    print(synthesis.summary)

    print(f"\nStats: {engine.get_stats()}")


if __name__ == "__main__":
    demo()
