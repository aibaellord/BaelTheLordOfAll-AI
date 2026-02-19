"""
🎨 CONCEPTUAL BLENDING 🎨
=========================
Blend concepts to create new ideas.

Features:
- Conceptual spaces
- Analogical mapping
- Emergent structure
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid
import math

from .creativity_core import Idea, IdeaType


@dataclass
class Concept:
    """A concept for blending"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    name: str = ""

    # Properties
    properties: Dict[str, Any] = field(default_factory=dict)

    # Relations to other concepts
    relations: Dict[str, List[str]] = field(default_factory=dict)

    # Slots (fillable roles)
    slots: Dict[str, Optional[str]] = field(default_factory=dict)

    # Domain
    domain: str = ""

    def add_property(self, name: str, value: Any):
        """Add property"""
        self.properties[name] = value

    def add_relation(self, relation_type: str, target: str):
        """Add relation"""
        if relation_type not in self.relations:
            self.relations[relation_type] = []
        self.relations[relation_type].append(target)

    def fill_slot(self, slot: str, value: str):
        """Fill a slot"""
        self.slots[slot] = value

    def get_structure(self) -> Dict[str, Any]:
        """Get structural description"""
        return {
            'properties': list(self.properties.keys()),
            'relations': list(self.relations.keys()),
            'slots': list(self.slots.keys())
        }


class ConceptualSpace:
    """
    A space of related concepts.
    """

    def __init__(self, domain: str = ""):
        self.domain = domain

        self.concepts: Dict[str, Concept] = {}

        # Dimensions of the space
        self.dimensions: List[str] = []

        # Exemplars
        self.exemplars: List[str] = []

    def add_concept(self, concept: Concept):
        """Add concept to space"""
        concept.domain = self.domain
        self.concepts[concept.name] = concept

    def add_dimension(self, dimension: str):
        """Add dimension to space"""
        if dimension not in self.dimensions:
            self.dimensions.append(dimension)

    def get_concept(self, name: str) -> Optional[Concept]:
        """Get concept by name"""
        return self.concepts.get(name)

    def find_similar(self, concept: Concept, n: int = 5) -> List[Tuple[str, float]]:
        """Find similar concepts"""
        similarities = []

        concept_props = set(concept.properties.keys())

        for name, other in self.concepts.items():
            if name == concept.name:
                continue

            other_props = set(other.properties.keys())

            # Jaccard similarity
            intersection = len(concept_props & other_props)
            union = len(concept_props | other_props)

            similarity = intersection / union if union > 0 else 0
            similarities.append((name, similarity))

        return sorted(similarities, key=lambda x: x[1], reverse=True)[:n]

    def interpolate(
        self,
        concept1: str,
        concept2: str,
        ratio: float = 0.5
    ) -> Concept:
        """Interpolate between two concepts"""
        c1 = self.concepts.get(concept1)
        c2 = self.concepts.get(concept2)

        if not c1 or not c2:
            return Concept()

        # Blend properties
        blended = Concept(
            name=f"{c1.name}_{c2.name}_blend"
        )

        all_props = set(c1.properties.keys()) | set(c2.properties.keys())

        for prop in all_props:
            v1 = c1.properties.get(prop)
            v2 = c2.properties.get(prop)

            if v1 is not None and v2 is not None:
                # Both have property - blend
                if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                    blended.properties[prop] = v1 * (1 - ratio) + v2 * ratio
                else:
                    blended.properties[prop] = v1 if ratio < 0.5 else v2
            elif v1 is not None:
                blended.properties[prop] = v1
            elif v2 is not None:
                blended.properties[prop] = v2

        return blended


@dataclass
class Blend:
    """Result of conceptual blending"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Input spaces
    input1: str = ""
    input2: str = ""

    # Generic space (shared structure)
    generic_space: Dict[str, Any] = field(default_factory=dict)

    # Blended space
    blended_concept: Optional[Concept] = None

    # Emergent structure
    emergent_properties: List[str] = field(default_factory=list)
    emergent_relations: List[str] = field(default_factory=list)

    # Quality metrics
    integration: float = 0.0      # How well inputs integrate
    web: float = 0.0              # Connections to background knowledge
    unpacking: float = 0.0        # Ability to trace back to inputs
    relevance: float = 0.0        # Relevance of blend to goals

    def get_quality(self) -> float:
        """Get overall blend quality"""
        return (
            self.integration * 0.3 +
            self.web * 0.2 +
            self.unpacking * 0.2 +
            self.relevance * 0.3
        )


class AnalogicalMapper:
    """
    Maps structure between concepts.
    """

    def __init__(self):
        self.mappings: Dict[str, Dict[str, str]] = {}

    def find_mapping(
        self,
        source: Concept,
        target: Concept
    ) -> Dict[str, str]:
        """Find structural mapping between concepts"""
        mapping = {}

        # Map properties with same values
        for s_prop, s_val in source.properties.items():
            for t_prop, t_val in target.properties.items():
                if type(s_val) == type(t_val):
                    if s_val == t_val:
                        mapping[s_prop] = t_prop
                    elif isinstance(s_val, (int, float)) and isinstance(t_val, (int, float)):
                        # Similar numeric values
                        if abs(s_val - t_val) < 0.1 * max(abs(s_val), abs(t_val), 1):
                            mapping[s_prop] = t_prop

        # Map relations by type
        for s_rel, s_targets in source.relations.items():
            for t_rel, t_targets in target.relations.items():
                if s_rel == t_rel:
                    mapping[f"rel:{s_rel}"] = f"rel:{t_rel}"

        # Map slots by name similarity
        for s_slot in source.slots:
            for t_slot in target.slots:
                if s_slot == t_slot:
                    mapping[f"slot:{s_slot}"] = f"slot:{t_slot}"

        return mapping

    def apply_mapping(
        self,
        concept: Concept,
        mapping: Dict[str, str],
        target_template: Concept
    ) -> Concept:
        """Apply mapping to transfer structure"""
        result = Concept(name=f"{concept.name}_mapped")

        # Transfer properties according to mapping
        for s_prop, t_prop in mapping.items():
            if s_prop.startswith("rel:") or s_prop.startswith("slot:"):
                continue

            if s_prop in concept.properties:
                result.properties[t_prop] = concept.properties[s_prop]

        # Transfer relations
        for s_rel, t_rel in mapping.items():
            if s_rel.startswith("rel:"):
                rel_name = s_rel[4:]
                new_rel = t_rel[4:]
                if rel_name in concept.relations:
                    result.relations[new_rel] = concept.relations[rel_name].copy()

        return result

    def get_mapping_strength(
        self,
        source: Concept,
        target: Concept,
        mapping: Dict[str, str]
    ) -> float:
        """Evaluate mapping strength"""
        if not mapping:
            return 0.0

        # Coverage
        source_features = (
            len(source.properties) +
            len(source.relations) +
            len(source.slots)
        )

        coverage = len(mapping) / source_features if source_features > 0 else 0

        return coverage


class ConceptualBlender:
    """
    Blends concepts to create new ideas.
    """

    def __init__(self):
        self.spaces: Dict[str, ConceptualSpace] = {}
        self.mapper = AnalogicalMapper()

        self.blends: List[Blend] = []

    def add_space(self, space: ConceptualSpace):
        """Add conceptual space"""
        self.spaces[space.domain] = space

    def find_generic_space(
        self,
        concept1: Concept,
        concept2: Concept
    ) -> Dict[str, Any]:
        """Find shared generic structure"""
        generic = {
            'shared_properties': [],
            'shared_relations': [],
            'shared_slots': []
        }

        # Shared properties
        props1 = set(concept1.properties.keys())
        props2 = set(concept2.properties.keys())
        generic['shared_properties'] = list(props1 & props2)

        # Shared relations
        rels1 = set(concept1.relations.keys())
        rels2 = set(concept2.relations.keys())
        generic['shared_relations'] = list(rels1 & rels2)

        # Shared slots
        slots1 = set(concept1.slots.keys())
        slots2 = set(concept2.slots.keys())
        generic['shared_slots'] = list(slots1 & slots2)

        return generic

    def blend(
        self,
        concept1: Concept,
        concept2: Concept
    ) -> Blend:
        """Blend two concepts"""
        blend = Blend(
            input1=concept1.name,
            input2=concept2.name
        )

        # Find generic space
        blend.generic_space = self.find_generic_space(concept1, concept2)

        # Create blended concept
        blended = Concept(
            name=f"blend_{concept1.name}_{concept2.name}"
        )

        # Selective projection
        # Include all shared elements
        for prop in blend.generic_space['shared_properties']:
            # Average numeric, prefer first for others
            v1 = concept1.properties.get(prop)
            v2 = concept2.properties.get(prop)

            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                blended.properties[prop] = (v1 + v2) / 2
            else:
                blended.properties[prop] = v1

        # Include unique elements that don't conflict
        for prop, val in concept1.properties.items():
            if prop not in blended.properties:
                blended.properties[f"{prop}_1"] = val

        for prop, val in concept2.properties.items():
            if prop not in blended.properties:
                blended.properties[f"{prop}_2"] = val

        # Emergent structure
        blend.emergent_properties = [
            f"{concept1.name}_{concept2.name}_synergy"
        ]

        # Calculate quality metrics
        total1 = len(concept1.properties) + len(concept1.relations)
        total2 = len(concept2.properties) + len(concept2.relations)
        shared = len(blend.generic_space['shared_properties'])

        blend.integration = shared / max(total1, total2, 1)
        blend.web = 0.5  # Placeholder
        blend.unpacking = 0.8  # Can trace back
        blend.relevance = 0.6  # Placeholder

        blend.blended_concept = blended
        self.blends.append(blend)

        return blend

    def blend_to_idea(self, blend: Blend) -> Idea:
        """Convert blend to idea"""
        return Idea(
            content=blend.blended_concept,
            description=f"Blend of {blend.input1} and {blend.input2}",
            idea_type=IdeaType.COMBINATION,
            quality=blend.get_quality(),
            novelty=1.0 - blend.integration,  # Less integration = more novel
            parent_ideas=[blend.input1, blend.input2],
            generation_method="conceptual_blending"
        )

    def multi_blend(self, concepts: List[Concept]) -> Blend:
        """Blend multiple concepts iteratively"""
        if len(concepts) < 2:
            return Blend()

        # Pairwise blending
        current_blend = self.blend(concepts[0], concepts[1])

        for concept in concepts[2:]:
            # Blend result with next concept
            blended_concept = current_blend.blended_concept
            current_blend = self.blend(blended_concept, concept)

        return current_blend


# Export all
__all__ = [
    'Concept',
    'ConceptualSpace',
    'Blend',
    'AnalogicalMapper',
    'ConceptualBlender',
]
