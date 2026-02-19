"""
⚡ WISDOM EXTRACTION ⚡
======================
Extract wisdom from knowledge.

Features:
- Pattern recognition
- Principle derivation
- Deep understanding
- Practical wisdom
"""

import math
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid

from .universal_knowledge import KnowledgeUnit, KnowledgeType


class WisdomLevel(Enum):
    """Levels of wisdom"""
    DATA = auto()         # Raw data
    INFORMATION = auto()  # Organized data
    KNOWLEDGE = auto()    # Understood info
    INSIGHT = auto()      # Deep understanding
    WISDOM = auto()       # Applied insight
    ENLIGHTENMENT = auto() # Transcendent wisdom


@dataclass
class WisdomUnit:
    """A unit of wisdom"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Content
    content: str = ""
    level: WisdomLevel = WisdomLevel.KNOWLEDGE

    # Source knowledge
    source_knowledge: Set[str] = field(default_factory=set)

    # Applicability
    domains: Set[str] = field(default_factory=set)
    universal: bool = False  # Applies universally

    # Quality
    depth: float = 0.5
    clarity: float = 0.5
    actionability: float = 0.5

    # Validation
    validated: bool = False
    validation_count: int = 0


class WisdomExtractor:
    """
    Extracts wisdom from knowledge.
    """

    def __init__(self):
        self.wisdom_units: Dict[str, WisdomUnit] = {}

        # Extraction patterns
        self.patterns: List[Dict[str, Any]] = []

        # Extraction history
        self.history: List[Dict[str, Any]] = []

    def extract(
        self,
        knowledge_units: List[KnowledgeUnit]
    ) -> List[WisdomUnit]:
        """Extract wisdom from knowledge"""
        wisdom = []

        if len(knowledge_units) < 2:
            return wisdom

        # Look for patterns
        patterns = self._find_patterns(knowledge_units)

        # Derive principles
        principles = self._derive_principles(knowledge_units, patterns)

        # Create wisdom units
        for principle in principles:
            unit = WisdomUnit(
                content=principle['content'],
                level=WisdomLevel.INSIGHT,
                source_knowledge={k.id for k in knowledge_units},
                depth=principle.get('depth', 0.5),
                clarity=principle.get('clarity', 0.5)
            )
            wisdom.append(unit)
            self.wisdom_units[unit.id] = unit

        # Record history
        self.history.append({
            'input_count': len(knowledge_units),
            'wisdom_count': len(wisdom),
            'patterns_found': len(patterns)
        })

        return wisdom

    def _find_patterns(
        self,
        units: List[KnowledgeUnit]
    ) -> List[Dict[str, Any]]:
        """Find patterns in knowledge"""
        patterns = []

        # Look for recurring themes
        tag_counts = defaultdict(int)
        for unit in units:
            for tag in unit.tags:
                tag_counts[tag] += 1

        for tag, count in tag_counts.items():
            if count >= len(units) * 0.5:
                patterns.append({
                    'type': 'recurring_theme',
                    'theme': tag,
                    'frequency': count / len(units)
                })

        # Look for causal chains
        for unit in units:
            if unit.knowledge_type == KnowledgeType.CAUSAL:
                patterns.append({
                    'type': 'causal_chain',
                    'unit_id': unit.id
                })

        self.patterns.extend(patterns)
        return patterns

    def _derive_principles(
        self,
        units: List[KnowledgeUnit],
        patterns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Derive principles from patterns"""
        principles = []

        for pattern in patterns:
            if pattern['type'] == 'recurring_theme':
                principles.append({
                    'content': f"Principle: {pattern['theme']} is fundamental",
                    'depth': pattern['frequency'],
                    'clarity': 0.8
                })

            elif pattern['type'] == 'causal_chain':
                principles.append({
                    'content': "Principle: Causal relationship exists",
                    'depth': 0.7,
                    'clarity': 0.9
                })

        # Meta-principle from number of patterns
        if len(patterns) >= 3:
            principles.append({
                'content': "Meta-principle: Rich interconnection exists",
                'depth': 0.9,
                'clarity': 0.7
            })

        return principles

    def elevate_wisdom(
        self,
        wisdom_unit: WisdomUnit
    ) -> WisdomUnit:
        """Elevate wisdom to higher level"""
        levels = list(WisdomLevel)
        current_idx = levels.index(wisdom_unit.level)

        if current_idx < len(levels) - 1:
            wisdom_unit.level = levels[current_idx + 1]
            wisdom_unit.depth *= 1.2

        return wisdom_unit


class PatternRecognizer:
    """
    Recognizes patterns across knowledge.
    """

    def __init__(self):
        self.recognized_patterns: List[Dict[str, Any]] = []

    def recognize(
        self,
        units: List[KnowledgeUnit]
    ) -> List[Dict[str, Any]]:
        """Recognize patterns in knowledge units"""
        patterns = []

        # Structural patterns
        patterns.extend(self._structural_patterns(units))

        # Semantic patterns
        patterns.extend(self._semantic_patterns(units))

        # Temporal patterns (if timestamps available)
        patterns.extend(self._temporal_patterns(units))

        self.recognized_patterns.extend(patterns)
        return patterns

    def _structural_patterns(
        self,
        units: List[KnowledgeUnit]
    ) -> List[Dict[str, Any]]:
        """Find structural patterns"""
        patterns = []

        # Hub and spoke
        for unit in units:
            if len(unit.related) >= 5:
                patterns.append({
                    'type': 'hub_spoke',
                    'hub': unit.id,
                    'spokes': len(unit.related)
                })

        # Chains
        visited = set()
        for unit in units:
            if unit.id in visited:
                continue

            chain = [unit.id]
            current = unit

            while current.derived_from and len(current.derived_from) == 1:
                parent_id = list(current.derived_from)[0]
                if parent_id in visited:
                    break
                chain.append(parent_id)
                visited.add(parent_id)
                # Find parent unit
                parent = next((u for u in units if u.id == parent_id), None)
                if not parent:
                    break
                current = parent

            if len(chain) >= 3:
                patterns.append({
                    'type': 'derivation_chain',
                    'chain': chain,
                    'length': len(chain)
                })

        return patterns

    def _semantic_patterns(
        self,
        units: List[KnowledgeUnit]
    ) -> List[Dict[str, Any]]:
        """Find semantic patterns"""
        patterns = []

        # Group by type
        by_type = defaultdict(list)
        for unit in units:
            by_type[unit.knowledge_type].append(unit)

        # Dominant type
        if by_type:
            dominant_type = max(by_type.items(), key=lambda x: len(x[1]))
            patterns.append({
                'type': 'dominant_knowledge_type',
                'knowledge_type': dominant_type[0].name,
                'count': len(dominant_type[1])
            })

        return patterns

    def _temporal_patterns(
        self,
        units: List[KnowledgeUnit]
    ) -> List[Dict[str, Any]]:
        """Find temporal patterns"""
        patterns = []

        # Sort by creation time
        sorted_units = sorted(units, key=lambda u: u.created_at)

        if len(sorted_units) >= 2:
            # Check for acceleration
            times = [u.created_at for u in sorted_units]
            if times[-1] > times[0]:
                patterns.append({
                    'type': 'temporal_span',
                    'start': times[0],
                    'end': times[-1]
                })

        return patterns


class PrincipleDeriver:
    """
    Derives principles from knowledge.
    """

    def __init__(self):
        self.principles: List[Dict[str, Any]] = []

    def derive(
        self,
        units: List[KnowledgeUnit],
        patterns: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Derive principles from knowledge and patterns"""
        principles = []

        patterns = patterns or []

        # From patterns
        for pattern in patterns:
            principle = self._pattern_to_principle(pattern)
            if principle:
                principles.append(principle)

        # From knowledge relationships
        principles.extend(self._relationship_principles(units))

        # From knowledge types
        principles.extend(self._type_based_principles(units))

        self.principles.extend(principles)
        return principles

    def _pattern_to_principle(
        self,
        pattern: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Convert pattern to principle"""
        pattern_type = pattern.get('type', '')

        if pattern_type == 'hub_spoke':
            return {
                'content': f"Central concept connects {pattern['spokes']} ideas",
                'type': 'connectivity',
                'strength': min(1.0, pattern['spokes'] / 10)
            }

        elif pattern_type == 'derivation_chain':
            return {
                'content': f"Knowledge evolves through {pattern['length']} stages",
                'type': 'evolution',
                'strength': min(1.0, pattern['length'] / 5)
            }

        elif pattern_type == 'dominant_knowledge_type':
            return {
                'content': f"Domain emphasizes {pattern['knowledge_type']} knowledge",
                'type': 'emphasis',
                'strength': 0.7
            }

        return None

    def _relationship_principles(
        self,
        units: List[KnowledgeUnit]
    ) -> List[Dict[str, Any]]:
        """Derive principles from relationships"""
        principles = []

        # Support relationships
        support_count = sum(len(u.supports) for u in units)
        if support_count > 0:
            principles.append({
                'content': "Knowledge in this domain is mutually reinforcing",
                'type': 'reinforcement',
                'strength': min(1.0, support_count / (len(units) * 2))
            })

        # Contradiction relationships
        contradiction_count = sum(len(u.contradicts) for u in units)
        if contradiction_count > 0:
            principles.append({
                'content': "Domain contains unresolved tensions",
                'type': 'tension',
                'strength': min(1.0, contradiction_count / (len(units) * 2))
            })

        return principles

    def _type_based_principles(
        self,
        units: List[KnowledgeUnit]
    ) -> List[Dict[str, Any]]:
        """Derive principles from knowledge types"""
        principles = []

        # Count types
        type_counts = defaultdict(int)
        for unit in units:
            type_counts[unit.knowledge_type] += 1

        # Derive from distribution
        if type_counts[KnowledgeType.PROCEDURAL] > len(units) * 0.3:
            principles.append({
                'content': "Domain is practice-oriented",
                'type': 'orientation',
                'strength': type_counts[KnowledgeType.PROCEDURAL] / len(units)
            })

        if type_counts[KnowledgeType.METACOGNITIVE] > 0:
            principles.append({
                'content': "Domain includes self-reflective knowledge",
                'type': 'meta',
                'strength': 0.8
            })

        return principles


# Export all
__all__ = [
    'WisdomLevel',
    'WisdomUnit',
    'WisdomExtractor',
    'PatternRecognizer',
    'PrincipleDeriver',
]
