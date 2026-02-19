"""
⚡ OMNISCIENT CORE ⚡
====================
Core omniscient capabilities.

Features:
- Universal knowledge access
- Omniscient queries
- Unified understanding
- Complete awareness
"""

import math
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid

from .universal_knowledge import UniversalKnowledge, KnowledgeUnit, KnowledgeType, KnowledgeDomain
from .knowledge_synthesis import KnowledgeSynthesizer, SynthesisMode
from .wisdom_extraction import WisdomExtractor, WisdomUnit, WisdomLevel


class OmniscienceLevel(Enum):
    """Levels of omniscience"""
    LOCAL = auto()       # Single domain
    REGIONAL = auto()    # Related domains
    GLOBAL = auto()      # All domains
    UNIVERSAL = auto()   # Beyond domains
    ABSOLUTE = auto()    # Complete knowledge


class KnowledgeScope(Enum):
    """Scope of knowledge query"""
    NARROW = auto()      # Specific
    MEDIUM = auto()      # Related
    WIDE = auto()        # Broad
    COMPLETE = auto()    # All


@dataclass
class OmniscientQuery:
    """Query for omniscient knowledge"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Query content
    query: str = ""

    # Scope
    scope: KnowledgeScope = KnowledgeScope.MEDIUM

    # Constraints
    domains: Set[str] = field(default_factory=set)
    knowledge_types: Set[KnowledgeType] = field(default_factory=set)
    min_confidence: float = 0.0

    # Preferences
    prefer_wisdom: bool = True
    include_synthesis: bool = True
    max_results: int = 100


@dataclass
class OmniscientResponse:
    """Response from omniscient query"""
    query_id: str = ""

    # Direct answers
    knowledge: List[KnowledgeUnit] = field(default_factory=list)

    # Synthesized knowledge
    synthesized: List[KnowledgeUnit] = field(default_factory=list)

    # Wisdom
    wisdom: List[WisdomUnit] = field(default_factory=list)

    # Meta information
    coverage: float = 0.0  # How much of relevant knowledge was accessed
    confidence: float = 0.0
    completeness: float = 0.0

    # Insights
    insights: List[str] = field(default_factory=list)


class OmniscientEngine:
    """
    Engine for omniscient knowledge access.
    """

    def __init__(self):
        self.universal = UniversalKnowledge()
        self.synthesizer = KnowledgeSynthesizer(self.universal)
        self.wisdom_extractor = WisdomExtractor()

        # Current level
        self.level = OmniscienceLevel.LOCAL

        # Query history
        self.history: List[Tuple[OmniscientQuery, OmniscientResponse]] = []

    def query(self, query: OmniscientQuery) -> OmniscientResponse:
        """Execute omniscient query"""
        response = OmniscientResponse(query_id=query.id)

        # Get direct knowledge
        direct_knowledge = self._get_direct_knowledge(query)
        response.knowledge = direct_knowledge

        # Synthesize if requested
        if query.include_synthesis and len(direct_knowledge) >= 2:
            synthesis_result = self.synthesizer.synthesize(
                direct_knowledge,
                SynthesisMode.EMERGENCE
            )
            response.synthesized = synthesis_result.synthesized
            response.insights.extend(synthesis_result.insights)

        # Extract wisdom if preferred
        if query.prefer_wisdom and len(direct_knowledge) >= 3:
            wisdom = self.wisdom_extractor.extract(direct_knowledge)
            response.wisdom = wisdom

        # Calculate metrics
        response.coverage = self._calculate_coverage(query, response)
        response.confidence = self._calculate_confidence(response)
        response.completeness = self._calculate_completeness(query, response)

        # Store history
        self.history.append((query, response))

        return response

    def _get_direct_knowledge(
        self,
        query: OmniscientQuery
    ) -> List[KnowledgeUnit]:
        """Get knowledge directly matching query"""
        results = []

        # Determine candidate pool based on scope
        if query.scope == KnowledgeScope.NARROW:
            candidates = self._narrow_search(query)
        elif query.scope == KnowledgeScope.WIDE:
            candidates = self._wide_search(query)
        elif query.scope == KnowledgeScope.COMPLETE:
            candidates = list(self.universal.units.values())
        else:
            candidates = self._medium_search(query)

        # Filter
        for unit in candidates:
            if unit.confidence < query.min_confidence:
                continue

            if query.knowledge_types and unit.knowledge_type not in query.knowledge_types:
                continue

            if query.domains and not (unit.domains & query.domains):
                continue

            results.append(unit)

        # Sort by importance
        results.sort(key=lambda u: -u.importance)

        return results[:query.max_results]

    def _narrow_search(self, query: OmniscientQuery) -> List[KnowledgeUnit]:
        """Narrow scope search"""
        results = []

        # Search specific domains only
        for domain in query.domains:
            for uid in self.universal.by_domain.get(domain, set()):
                if uid in self.universal.units:
                    results.append(self.universal.units[uid])

        return results

    def _medium_search(self, query: OmniscientQuery) -> List[KnowledgeUnit]:
        """Medium scope search"""
        results = []

        # Include related domains
        domains_to_search = set(query.domains)

        for domain_name in query.domains:
            domain = self.universal.domains.get(domain_name)
            if domain:
                domains_to_search.update(domain.related_domains.keys())

        for domain in domains_to_search:
            for uid in self.universal.by_domain.get(domain, set()):
                if uid in self.universal.units:
                    results.append(self.universal.units[uid])

        return results

    def _wide_search(self, query: OmniscientQuery) -> List[KnowledgeUnit]:
        """Wide scope search"""
        return list(self.universal.units.values())

    def _calculate_coverage(
        self,
        query: OmniscientQuery,
        response: OmniscientResponse
    ) -> float:
        """Calculate coverage of relevant knowledge"""
        total_relevant = 0

        for domain in query.domains:
            total_relevant += len(self.universal.by_domain.get(domain, set()))

        if total_relevant == 0:
            return 1.0

        returned = len(response.knowledge)
        return min(1.0, returned / total_relevant)

    def _calculate_confidence(
        self,
        response: OmniscientResponse
    ) -> float:
        """Calculate confidence in response"""
        if not response.knowledge:
            return 0.0

        return sum(k.confidence for k in response.knowledge) / len(response.knowledge)

    def _calculate_completeness(
        self,
        query: OmniscientQuery,
        response: OmniscientResponse
    ) -> float:
        """Calculate completeness of response"""
        has_knowledge = len(response.knowledge) > 0
        has_synthesis = len(response.synthesized) > 0
        has_wisdom = len(response.wisdom) > 0

        components = [has_knowledge, has_synthesis, has_wisdom]
        return sum(1 for c in components if c) / 3

    def elevate_level(self) -> bool:
        """Elevate omniscience level"""
        levels = list(OmniscienceLevel)
        current_idx = levels.index(self.level)

        if current_idx < len(levels) - 1:
            self.level = levels[current_idx + 1]
            return True

        return False


class UnifiedKnowledge:
    """
    Unified view of all knowledge.
    """

    def __init__(self, engine: OmniscientEngine = None):
        self.engine = engine or OmniscientEngine()

        # Unified representation
        self.unified_map: Dict[str, Any] = {}

        # Cross-references
        self.cross_refs: Dict[str, Set[str]] = defaultdict(set)

    def unify(self) -> Dict[str, Any]:
        """Create unified view of all knowledge"""
        self.unified_map = {
            'domains': {},
            'knowledge': {},
            'relationships': [],
            'meta': {}
        }

        # Map domains
        for domain_id, domain in self.engine.universal.domains.items():
            self.unified_map['domains'][domain_id] = {
                'name': domain.name,
                'knowledge_count': len(domain.knowledge_units),
                'children': list(domain.children),
                'parent': domain.parent
            }

        # Map knowledge
        for uid, unit in self.engine.universal.units.items():
            self.unified_map['knowledge'][uid] = {
                'type': unit.knowledge_type.name,
                'domains': list(unit.domains),
                'importance': unit.importance,
                'confidence': unit.confidence
            }

        # Map relationships
        for uid, unit in self.engine.universal.units.items():
            for related in unit.related:
                self.unified_map['relationships'].append({
                    'source': uid,
                    'target': related,
                    'type': 'related'
                })

        # Meta information
        self.unified_map['meta'] = {
            'total_knowledge': len(self.engine.universal.units),
            'total_domains': len(self.engine.universal.domains),
            'omniscience_level': self.engine.level.name
        }

        return self.unified_map

    def get_cross_references(
        self,
        unit_id: str
    ) -> Set[str]:
        """Get all cross-references for a knowledge unit"""
        unit = self.engine.universal.units.get(unit_id)
        if not unit:
            return set()

        refs = set()
        refs.update(unit.related)
        refs.update(unit.derived_from)
        refs.update(unit.supports)

        return refs

    def find_gaps(self) -> List[Dict[str, Any]]:
        """Find gaps in unified knowledge"""
        gaps = []

        # Domains without children or knowledge
        for domain_id, domain in self.engine.universal.domains.items():
            if not domain.knowledge_units and not domain.children:
                gaps.append({
                    'type': 'empty_domain',
                    'domain': domain_id
                })

        # Orphan knowledge (no connections)
        for uid, unit in self.engine.universal.units.items():
            if not unit.related and not unit.derived_from:
                gaps.append({
                    'type': 'orphan_knowledge',
                    'unit': uid
                })

        return gaps

    def get_completeness_score(self) -> float:
        """Get completeness score of unified knowledge"""
        if not self.unified_map:
            self.unify()

        gaps = self.find_gaps()
        total_items = len(self.engine.universal.units) + len(self.engine.universal.domains)

        if total_items == 0:
            return 1.0

        gap_count = len(gaps)
        return max(0.0, 1.0 - gap_count / total_items)


# Export all
__all__ = [
    'OmniscienceLevel',
    'KnowledgeScope',
    'OmniscientQuery',
    'OmniscientResponse',
    'OmniscientEngine',
    'UnifiedKnowledge',
]
