"""
⚡ KNOWLEDGE SYNTHESIS ⚡
========================
Cross-domain knowledge synthesis.

Features:
- Multi-domain integration
- Emergent knowledge
- Knowledge fusion
- Insight generation
"""

import math
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid

from .universal_knowledge import KnowledgeUnit, KnowledgeType, UniversalKnowledge


class SynthesisMode(Enum):
    """Modes of knowledge synthesis"""
    INTERSECTION = auto()  # Find commonalities
    UNION = auto()         # Combine all
    ANALOGY = auto()       # Map between domains
    ABSTRACTION = auto()   # Extract principles
    COMPOSITION = auto()   # Build new from parts
    EMERGENCE = auto()     # Allow new to emerge


@dataclass
class SynthesisResult:
    """Result of knowledge synthesis"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Synthesized knowledge
    synthesized: List[KnowledgeUnit] = field(default_factory=list)

    # Source knowledge
    sources: List[str] = field(default_factory=list)

    # Mode used
    mode: SynthesisMode = SynthesisMode.UNION

    # Quality metrics
    coherence: float = 0.0
    novelty: float = 0.0
    utility: float = 0.0

    # Insights generated
    insights: List[str] = field(default_factory=list)


class KnowledgeSynthesizer:
    """
    Synthesizes knowledge across domains.
    """

    def __init__(self, universal: UniversalKnowledge = None):
        self.universal = universal or UniversalKnowledge()

        # Synthesis strategies
        self.strategies: Dict[SynthesisMode, Callable] = {
            SynthesisMode.INTERSECTION: self._intersection_synthesis,
            SynthesisMode.UNION: self._union_synthesis,
            SynthesisMode.ANALOGY: self._analogy_synthesis,
            SynthesisMode.ABSTRACTION: self._abstraction_synthesis,
            SynthesisMode.COMPOSITION: self._composition_synthesis,
            SynthesisMode.EMERGENCE: self._emergence_synthesis,
        }

        # History
        self.history: List[SynthesisResult] = []

    def synthesize(
        self,
        sources: List[KnowledgeUnit],
        mode: SynthesisMode = SynthesisMode.UNION
    ) -> SynthesisResult:
        """Synthesize knowledge from sources"""
        if mode in self.strategies:
            result = self.strategies[mode](sources)
        else:
            result = self._union_synthesis(sources)

        result.sources = [s.id for s in sources]
        result.mode = mode

        # Calculate quality metrics
        result.coherence = self._calculate_coherence(result.synthesized)
        result.novelty = self._calculate_novelty(result.synthesized, sources)
        result.utility = (result.coherence + result.novelty) / 2

        self.history.append(result)
        return result

    def _intersection_synthesis(
        self,
        sources: List[KnowledgeUnit]
    ) -> SynthesisResult:
        """Find common knowledge"""
        if not sources:
            return SynthesisResult()

        # Find common tags
        common_tags = set(sources[0].tags)
        for source in sources[1:]:
            common_tags &= source.tags

        # Find common domains
        common_domains = set(sources[0].domains)
        for source in sources[1:]:
            common_domains &= source.domains

        # Create synthesized unit
        synthesized = KnowledgeUnit(
            content=f"Common knowledge from {len(sources)} sources",
            knowledge_type=KnowledgeType.CONCEPTUAL,
            tags=common_tags,
            domains=common_domains,
            derived_from={s.id for s in sources},
            confidence=min(s.confidence for s in sources)
        )

        result = SynthesisResult(synthesized=[synthesized])
        result.insights.append(f"Found {len(common_tags)} common themes")

        return result

    def _union_synthesis(
        self,
        sources: List[KnowledgeUnit]
    ) -> SynthesisResult:
        """Combine all knowledge"""
        if not sources:
            return SynthesisResult()

        # Collect all
        all_tags = set()
        all_domains = set()

        for source in sources:
            all_tags.update(source.tags)
            all_domains.update(source.domains)

        synthesized = KnowledgeUnit(
            content=f"Combined knowledge from {len(sources)} sources",
            knowledge_type=KnowledgeType.CONCEPTUAL,
            tags=all_tags,
            domains=all_domains,
            derived_from={s.id for s in sources},
            confidence=sum(s.confidence for s in sources) / len(sources)
        )

        result = SynthesisResult(synthesized=[synthesized])
        result.insights.append(f"Combined {len(all_tags)} themes across {len(all_domains)} domains")

        return result

    def _analogy_synthesis(
        self,
        sources: List[KnowledgeUnit]
    ) -> SynthesisResult:
        """Map knowledge between domains"""
        if len(sources) < 2:
            return SynthesisResult()

        # Find analogical mappings
        source_a, source_b = sources[0], sources[1]

        # Create mapping
        synthesized = KnowledgeUnit(
            content=f"Analogical mapping: {source_a.content} <-> {source_b.content}",
            knowledge_type=KnowledgeType.RELATIONAL,
            domains=source_a.domains | source_b.domains,
            derived_from={source_a.id, source_b.id},
            confidence=(source_a.confidence + source_b.confidence) / 2 * 0.8
        )

        result = SynthesisResult(synthesized=[synthesized])
        result.insights.append("Created analogical bridge between domains")

        return result

    def _abstraction_synthesis(
        self,
        sources: List[KnowledgeUnit]
    ) -> SynthesisResult:
        """Extract abstract principles"""
        if not sources:
            return SynthesisResult()

        # Extract common patterns
        synthesized = KnowledgeUnit(
            content=f"Abstract principle from {len(sources)} instances",
            knowledge_type=KnowledgeType.METACOGNITIVE,
            derived_from={s.id for s in sources},
            importance=max(s.importance for s in sources) * 1.2,
            confidence=min(s.confidence for s in sources) * 0.9
        )

        result = SynthesisResult(synthesized=[synthesized])
        result.insights.append("Extracted higher-order principle")

        return result

    def _composition_synthesis(
        self,
        sources: List[KnowledgeUnit]
    ) -> SynthesisResult:
        """Compose new knowledge from parts"""
        if not sources:
            return SynthesisResult()

        # Build composite
        synthesized = KnowledgeUnit(
            content=f"Composite of {len(sources)} knowledge units",
            knowledge_type=KnowledgeType.CONCEPTUAL,
            tags={t for s in sources for t in s.tags},
            domains={d for s in sources for d in s.domains},
            derived_from={s.id for s in sources},
            confidence=sum(s.confidence for s in sources) / len(sources)
        )

        result = SynthesisResult(synthesized=[synthesized])
        result.insights.append("Composed structured knowledge unit")

        return result

    def _emergence_synthesis(
        self,
        sources: List[KnowledgeUnit]
    ) -> SynthesisResult:
        """Allow emergent knowledge"""
        if not sources:
            return SynthesisResult()

        # Look for emergent properties
        all_relations = set()
        for source in sources:
            all_relations.update(source.related)

        # Create emergent knowledge
        synthesized = KnowledgeUnit(
            content=f"Emergent insight from {len(sources)} sources",
            knowledge_type=KnowledgeType.TACIT,
            derived_from={s.id for s in sources},
            related=all_relations,
            confidence=0.7,  # Lower confidence for emergent
            importance=1.0  # But high importance
        )

        result = SynthesisResult(synthesized=[synthesized])
        result.insights.append("Emergent property detected from collective knowledge")

        return result

    def _calculate_coherence(self, units: List[KnowledgeUnit]) -> float:
        """Calculate coherence of synthesized knowledge"""
        if not units:
            return 0.0

        # Check for contradictions
        for unit in units:
            if unit.contradicts:
                return 0.5  # Has contradictions

        return 0.9  # Default high coherence

    def _calculate_novelty(
        self,
        synthesized: List[KnowledgeUnit],
        sources: List[KnowledgeUnit]
    ) -> float:
        """Calculate novelty of synthesized knowledge"""
        if not synthesized or not sources:
            return 0.0

        # Compare to sources
        source_content = {s.content for s in sources}

        novel_count = sum(
            1 for s in synthesized
            if s.content not in source_content
        )

        return novel_count / len(synthesized)


class CrossDomainSynthesis:
    """
    Synthesis across different domains.
    """

    def __init__(self, synthesizer: KnowledgeSynthesizer = None):
        self.synthesizer = synthesizer or KnowledgeSynthesizer()

    def bridge_domains(
        self,
        domain_a: str,
        domain_b: str
    ) -> SynthesisResult:
        """Create bridge between domains"""
        # Get knowledge from each domain
        units_a = list(self.synthesizer.universal.by_domain.get(domain_a, set()))
        units_b = list(self.synthesizer.universal.by_domain.get(domain_b, set()))

        sources = []
        for uid in units_a[:5]:
            if uid in self.synthesizer.universal.units:
                sources.append(self.synthesizer.universal.units[uid])
        for uid in units_b[:5]:
            if uid in self.synthesizer.universal.units:
                sources.append(self.synthesizer.universal.units[uid])

        return self.synthesizer.synthesize(sources, SynthesisMode.ANALOGY)

    def find_isomorphisms(
        self,
        domain_a: str,
        domain_b: str
    ) -> List[Tuple[KnowledgeUnit, KnowledgeUnit]]:
        """Find structural isomorphisms between domains"""
        isomorphisms = []

        units_a = self.synthesizer.universal.get_domain_knowledge(domain_a)
        units_b = self.synthesizer.universal.get_domain_knowledge(domain_b)

        for ua in units_a:
            if ua.embedding is None:
                continue

            best_match = None
            best_sim = 0.0

            for ub in units_b:
                if ub.embedding is None:
                    continue

                sim = np.dot(ua.embedding, ub.embedding) / (
                    np.linalg.norm(ua.embedding) *
                    np.linalg.norm(ub.embedding) + 1e-10
                )

                if sim > best_sim:
                    best_sim = sim
                    best_match = ub

            if best_match and best_sim > 0.7:
                isomorphisms.append((ua, best_match))

        return isomorphisms


class EmergentKnowledge:
    """
    Detection and cultivation of emergent knowledge.
    """

    def __init__(self, universal: UniversalKnowledge = None):
        self.universal = universal or UniversalKnowledge()

        # Emergent patterns detected
        self.patterns: List[Dict[str, Any]] = []

    def detect_emergence(
        self,
        units: List[KnowledgeUnit]
    ) -> List[Dict[str, Any]]:
        """Detect emergent patterns in knowledge"""
        patterns = []

        if len(units) < 3:
            return patterns

        # Look for clusters of related knowledge
        relation_counts = defaultdict(int)
        for unit in units:
            for related in unit.related:
                relation_counts[related] += 1

        # High-connectivity nodes suggest emergence
        for uid, count in relation_counts.items():
            if count >= 3:
                patterns.append({
                    'type': 'hub',
                    'center': uid,
                    'connections': count,
                    'emergent': True
                })

        # Look for concept bridges
        domain_sets = defaultdict(set)
        for unit in units:
            for domain in unit.domains:
                domain_sets[domain].add(unit.id)

        # Units in multiple domains are bridges
        for unit in units:
            if len(unit.domains) >= 2:
                patterns.append({
                    'type': 'bridge',
                    'unit': unit.id,
                    'domains': list(unit.domains),
                    'emergent': True
                })

        self.patterns.extend(patterns)
        return patterns

    def cultivate_emergence(
        self,
        seed_units: List[KnowledgeUnit]
    ) -> List[KnowledgeUnit]:
        """Cultivate emergent knowledge from seeds"""
        emergent = []

        # Detect patterns
        patterns = self.detect_emergence(seed_units)

        # Create emergent units from patterns
        for pattern in patterns:
            if pattern['type'] == 'hub':
                unit = KnowledgeUnit(
                    content=f"Emergent hub connecting {pattern['connections']} concepts",
                    knowledge_type=KnowledgeType.RELATIONAL,
                    derived_from={pattern['center']},
                    importance=pattern['connections'] / 10.0
                )
                emergent.append(unit)

            elif pattern['type'] == 'bridge':
                unit = KnowledgeUnit(
                    content=f"Bridge concept across {len(pattern['domains'])} domains",
                    knowledge_type=KnowledgeType.CONCEPTUAL,
                    domains=set(pattern['domains']),
                    importance=len(pattern['domains']) / 5.0
                )
                emergent.append(unit)

        return emergent


# Export all
__all__ = [
    'SynthesisMode',
    'SynthesisResult',
    'KnowledgeSynthesizer',
    'CrossDomainSynthesis',
    'EmergentKnowledge',
]
