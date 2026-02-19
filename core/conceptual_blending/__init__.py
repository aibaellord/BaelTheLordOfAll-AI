"""
BAEL Conceptual Blending Engine
================================

Conceptual integration and creative combination.
Fauconnier & Turner's blending theory.

"Ba'el blends concepts." — Ba'el
"""

import logging
import threading
import time
import math
import random
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import defaultdict, deque
import copy

logger = logging.getLogger("BAEL.ConceptualBlending")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class SpaceType(Enum):
    """Types of mental spaces."""
    INPUT = auto()      # Input space
    GENERIC = auto()    # Generic space (shared structure)
    BLEND = auto()      # Blended space


class RelationType(Enum):
    """Cross-space relation types."""
    IDENTITY = auto()      # Same element
    ANALOGY = auto()       # Analogous elements
    CONTRAST = auto()      # Contrasting elements
    ROLE = auto()          # Role-value mapping
    PART_WHOLE = auto()    # Part-whole relation
    CAUSE_EFFECT = auto()  # Causal relation


class BlendType(Enum):
    """Types of blends."""
    SIMPLEX = auto()       # Simple combination
    MIRROR = auto()        # Mirror network
    SINGLE_SCOPE = auto()  # Single organizing frame
    DOUBLE_SCOPE = auto()  # Both frames contribute


class VitalRelation(Enum):
    """Vital relations in blending."""
    CHANGE = auto()
    IDENTITY = auto()
    TIME = auto()
    SPACE = auto()
    CAUSE_EFFECT = auto()
    PART_WHOLE = auto()
    REPRESENTATION = auto()
    ROLE = auto()
    ANALOGY = auto()
    DISANALOGY = auto()
    PROPERTY = auto()
    SIMILARITY = auto()
    CATEGORY = auto()
    INTENTIONALITY = auto()
    UNIQUENESS = auto()


@dataclass
class Element:
    """
    An element in a mental space.
    """
    id: str
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    relations: List[Tuple[str, RelationType, str]] = field(default_factory=list)


@dataclass
class Frame:
    """
    An organizing frame/schema.
    """
    id: str
    name: str
    roles: List[str]
    constraints: List[str] = field(default_factory=list)


@dataclass
class MentalSpace:
    """
    A mental space.
    """
    id: str
    name: str
    space_type: SpaceType
    elements: Dict[str, Element]
    frame: Optional[Frame] = None


@dataclass
class CrossSpaceMapping:
    """
    Mapping between spaces.
    """
    source_space: str
    target_space: str
    element_mappings: Dict[str, str]  # source_id -> target_id
    relation_type: RelationType = RelationType.ANALOGY


@dataclass
class Blend:
    """
    A conceptual blend.
    """
    id: str
    name: str
    input_spaces: List[str]
    generic_space: Optional[str]
    blended_space: MentalSpace
    mappings: List[CrossSpaceMapping]
    emergent_structure: List[str]  # New elements/relations in blend
    blend_type: BlendType


@dataclass
class BlendQuality:
    """
    Quality assessment of blend.
    """
    integration: float      # How well inputs integrate
    web: float             # Cross-space connection density
    unpacking: float       # Can trace back to inputs
    topology: float        # Structure preservation
    relevance: float       # Goal relevance
    compression: float     # Vital relation compression


# ============================================================================
# MENTAL SPACE BUILDER
# ============================================================================

class MentalSpaceBuilder:
    """
    Build mental spaces.

    "Ba'el constructs spaces." — Ba'el
    """

    def __init__(self):
        """Initialize builder."""
        self._element_counter = 0
        self._space_counter = 0
        self._lock = threading.RLock()

    def _generate_element_id(self) -> str:
        self._element_counter += 1
        return f"elem_{self._element_counter}"

    def _generate_space_id(self) -> str:
        self._space_counter += 1
        return f"space_{self._space_counter}"

    def create_space(
        self,
        name: str,
        space_type: SpaceType = SpaceType.INPUT
    ) -> MentalSpace:
        """Create mental space."""
        with self._lock:
            return MentalSpace(
                id=self._generate_space_id(),
                name=name,
                space_type=space_type,
                elements={}
            )

    def add_element(
        self,
        space: MentalSpace,
        name: str,
        properties: Dict[str, Any] = None
    ) -> Element:
        """Add element to space."""
        with self._lock:
            element = Element(
                id=self._generate_element_id(),
                name=name,
                properties=properties or {}
            )

            space.elements[element.id] = element
            return element

    def add_relation(
        self,
        space: MentalSpace,
        element1_id: str,
        relation_type: RelationType,
        element2_id: str
    ) -> None:
        """Add relation between elements."""
        if element1_id in space.elements:
            space.elements[element1_id].relations.append(
                (element1_id, relation_type, element2_id)
            )

    def set_frame(
        self,
        space: MentalSpace,
        frame_name: str,
        roles: List[str]
    ) -> Frame:
        """Set organizing frame for space."""
        with self._lock:
            frame = Frame(
                id=f"frame_{space.id}",
                name=frame_name,
                roles=roles
            )
            space.frame = frame
            return frame


# ============================================================================
# CROSS-SPACE MAPPER
# ============================================================================

class CrossSpaceMapper:
    """
    Map between mental spaces.

    "Ba'el finds correspondences." — Ba'el
    """

    def __init__(self):
        """Initialize mapper."""
        self._lock = threading.RLock()

    def find_mappings(
        self,
        space1: MentalSpace,
        space2: MentalSpace,
        similarity_threshold: float = 0.5
    ) -> CrossSpaceMapping:
        """Find mappings between spaces."""
        with self._lock:
            element_mappings = {}

            # Map by property similarity
            for id1, elem1 in space1.elements.items():
                best_match = None
                best_score = 0.0

                for id2, elem2 in space2.elements.items():
                    if id2 in element_mappings.values():
                        continue

                    score = self._compute_similarity(elem1, elem2)
                    if score > best_score and score >= similarity_threshold:
                        best_score = score
                        best_match = id2

                if best_match:
                    element_mappings[id1] = best_match

            return CrossSpaceMapping(
                source_space=space1.id,
                target_space=space2.id,
                element_mappings=element_mappings
            )

    def _compute_similarity(
        self,
        elem1: Element,
        elem2: Element
    ) -> float:
        """Compute element similarity."""
        # Name similarity
        name_sim = 0.0
        if elem1.name.lower() == elem2.name.lower():
            name_sim = 1.0
        elif any(w in elem2.name.lower() for w in elem1.name.lower().split()):
            name_sim = 0.5

        # Property overlap
        props1 = set(elem1.properties.keys())
        props2 = set(elem2.properties.keys())

        if props1 and props2:
            prop_sim = len(props1 & props2) / len(props1 | props2)
        else:
            prop_sim = 0.0

        return (name_sim + prop_sim) / 2

    def extract_generic_space(
        self,
        spaces: List[MentalSpace],
        mappings: List[CrossSpaceMapping]
    ) -> MentalSpace:
        """Extract generic space (shared structure)."""
        with self._lock:
            generic = MentalSpace(
                id="generic",
                name="Generic Space",
                space_type=SpaceType.GENERIC,
                elements={}
            )

            # Find elements that appear in multiple mappings
            element_counts: Dict[str, int] = defaultdict(int)

            for mapping in mappings:
                for elem_id in mapping.element_mappings.keys():
                    element_counts[elem_id] += 1

            # Add common elements
            for space in spaces:
                for elem_id, elem in space.elements.items():
                    if element_counts.get(elem_id, 0) > 0:
                        # Generalize element
                        generic.elements[f"gen_{elem_id}"] = Element(
                            id=f"gen_{elem_id}",
                            name=f"[{elem.name}]",
                            properties={'source': elem_id}
                        )

            return generic


# ============================================================================
# BLENDING ENGINE
# ============================================================================

class BlendingEngine:
    """
    Perform conceptual blending.

    "Ba'el integrates concepts." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._blend_counter = 0
        self._lock = threading.RLock()

    def _generate_blend_id(self) -> str:
        self._blend_counter += 1
        return f"blend_{self._blend_counter}"

    def blend(
        self,
        input_spaces: List[MentalSpace],
        mappings: List[CrossSpaceMapping],
        generic_space: MentalSpace = None,
        blend_name: str = "Blend"
    ) -> Blend:
        """Create conceptual blend."""
        with self._lock:
            # Determine blend type
            blend_type = self._determine_blend_type(input_spaces, mappings)

            # Create blended space
            blended = MentalSpace(
                id="blended",
                name=blend_name,
                space_type=SpaceType.BLEND,
                elements={}
            )

            # Project elements from inputs
            for space in input_spaces:
                for elem_id, elem in space.elements.items():
                    # Project with modification
                    projected = Element(
                        id=f"proj_{elem_id}",
                        name=elem.name,
                        properties=elem.properties.copy()
                    )
                    projected.properties['source_space'] = space.id
                    blended.elements[projected.id] = projected

            # Fuse mapped elements
            emergent = []
            for mapping in mappings:
                for src_id, tgt_id in mapping.element_mappings.items():
                    # Create fused element
                    src_elem = None
                    tgt_elem = None

                    for space in input_spaces:
                        if src_id in space.elements:
                            src_elem = space.elements[src_id]
                        if tgt_id in space.elements:
                            tgt_elem = space.elements[tgt_id]

                    if src_elem and tgt_elem:
                        fused = Element(
                            id=f"fused_{src_id}_{tgt_id}",
                            name=f"{src_elem.name}-{tgt_elem.name}",
                            properties={
                                **src_elem.properties,
                                **tgt_elem.properties,
                                'fused_from': [src_id, tgt_id]
                            }
                        )
                        blended.elements[fused.id] = fused
                        emergent.append(fused.id)

            # Run completion (add emergent structure)
            completion = self._run_completion(blended, input_spaces)
            emergent.extend(completion)

            return Blend(
                id=self._generate_blend_id(),
                name=blend_name,
                input_spaces=[s.id for s in input_spaces],
                generic_space=generic_space.id if generic_space else None,
                blended_space=blended,
                mappings=mappings,
                emergent_structure=emergent,
                blend_type=blend_type
            )

    def _determine_blend_type(
        self,
        spaces: List[MentalSpace],
        mappings: List[CrossSpaceMapping]
    ) -> BlendType:
        """Determine type of blend."""
        # Check for frames
        frames = [s.frame for s in spaces if s.frame]

        if len(frames) == 0:
            return BlendType.SIMPLEX
        elif len(frames) == 1:
            return BlendType.SINGLE_SCOPE
        elif len(set(f.name for f in frames)) == 1:
            return BlendType.MIRROR
        else:
            return BlendType.DOUBLE_SCOPE

    def _run_completion(
        self,
        blend: MentalSpace,
        inputs: List[MentalSpace]
    ) -> List[str]:
        """Run completion to add emergent structure."""
        emergent = []

        # Pattern completion: if elements have relations in inputs,
        # add corresponding relations in blend
        for space in inputs:
            for elem in space.elements.values():
                for src, rel_type, tgt in elem.relations:
                    # Find corresponding elements in blend
                    proj_src = f"proj_{src}"
                    proj_tgt = f"proj_{tgt}"

                    if proj_src in blend.elements and proj_tgt in blend.elements:
                        blend.elements[proj_src].relations.append(
                            (proj_src, rel_type, proj_tgt)
                        )
                        emergent.append(f"rel_{proj_src}_{proj_tgt}")

        return emergent

    def elaborate(
        self,
        blend: Blend,
        elaboration: str
    ) -> Blend:
        """Elaborate blend with new content."""
        with self._lock:
            # Add new element representing elaboration
            new_elem = Element(
                id=f"elab_{len(blend.blended_space.elements)}",
                name=elaboration,
                properties={'type': 'elaboration'}
            )

            blend.blended_space.elements[new_elem.id] = new_elem
            blend.emergent_structure.append(new_elem.id)

            return blend


# ============================================================================
# BLEND EVALUATOR
# ============================================================================

class BlendEvaluator:
    """
    Evaluate blend quality.

    "Ba'el judges blends." — Ba'el
    """

    def __init__(self):
        """Initialize evaluator."""
        self._lock = threading.RLock()

    def evaluate(
        self,
        blend: Blend,
        input_spaces: List[MentalSpace]
    ) -> BlendQuality:
        """Evaluate blend quality."""
        with self._lock:
            # Integration: how well elements combine
            integration = self._evaluate_integration(blend)

            # Web: cross-space mapping density
            web = self._evaluate_web(blend)

            # Unpacking: can trace to inputs
            unpacking = self._evaluate_unpacking(blend, input_spaces)

            # Topology: structure preservation
            topology = self._evaluate_topology(blend, input_spaces)

            # Relevance (would need goal)
            relevance = 0.5

            # Compression: vital relation compression
            compression = self._evaluate_compression(blend)

            return BlendQuality(
                integration=integration,
                web=web,
                unpacking=unpacking,
                topology=topology,
                relevance=relevance,
                compression=compression
            )

    def _evaluate_integration(self, blend: Blend) -> float:
        """Evaluate integration."""
        # Count fused elements
        fused = sum(
            1 for e in blend.blended_space.elements.values()
            if 'fused_from' in e.properties
        )
        total = len(blend.blended_space.elements)

        if total == 0:
            return 0.0

        return min(1.0, fused / (total * 0.3))

    def _evaluate_web(self, blend: Blend) -> float:
        """Evaluate web (mapping density)."""
        total_mappings = sum(len(m.element_mappings) for m in blend.mappings)
        total_elements = len(blend.blended_space.elements)

        if total_elements == 0:
            return 0.0

        return min(1.0, total_mappings / total_elements)

    def _evaluate_unpacking(
        self,
        blend: Blend,
        inputs: List[MentalSpace]
    ) -> float:
        """Evaluate unpacking (traceability)."""
        traceable = 0

        for elem in blend.blended_space.elements.values():
            if 'source_space' in elem.properties or 'fused_from' in elem.properties:
                traceable += 1

        total = len(blend.blended_space.elements)

        if total == 0:
            return 0.0

        return traceable / total

    def _evaluate_topology(
        self,
        blend: Blend,
        inputs: List[MentalSpace]
    ) -> float:
        """Evaluate topology preservation."""
        # Count preserved relations
        input_relations = sum(
            len(e.relations) for s in inputs for e in s.elements.values()
        )

        blend_relations = sum(
            len(e.relations) for e in blend.blended_space.elements.values()
        )

        if input_relations == 0:
            return 1.0

        return min(1.0, blend_relations / input_relations)

    def _evaluate_compression(self, blend: Blend) -> float:
        """Evaluate compression."""
        # More emergent structure = better compression
        emergent = len(blend.emergent_structure)
        total = len(blend.blended_space.elements)

        if total == 0:
            return 0.0

        return min(1.0, emergent / total)


# ============================================================================
# CONCEPTUAL BLENDING ENGINE
# ============================================================================

class ConceptualBlendingEngine:
    """
    Complete conceptual blending engine.

    "Ba'el's creative fusion." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._builder = MentalSpaceBuilder()
        self._mapper = CrossSpaceMapper()
        self._blender = BlendingEngine()
        self._evaluator = BlendEvaluator()

        self._spaces: Dict[str, MentalSpace] = {}
        self._blends: Dict[str, Blend] = {}

        self._lock = threading.RLock()

    # Space creation

    def create_space(
        self,
        name: str,
        elements: Dict[str, Dict[str, Any]] = None
    ) -> MentalSpace:
        """Create input space."""
        with self._lock:
            space = self._builder.create_space(name, SpaceType.INPUT)

            if elements:
                for elem_name, props in elements.items():
                    self._builder.add_element(space, elem_name, props)

            self._spaces[space.id] = space
            return space

    def add_element(
        self,
        space_id: str,
        name: str,
        properties: Dict[str, Any] = None
    ) -> Optional[Element]:
        """Add element to space."""
        space = self._spaces.get(space_id)
        if space:
            return self._builder.add_element(space, name, properties)
        return None

    def add_relation(
        self,
        space_id: str,
        elem1_id: str,
        relation: RelationType,
        elem2_id: str
    ) -> None:
        """Add relation between elements."""
        space = self._spaces.get(space_id)
        if space:
            self._builder.add_relation(space, elem1_id, relation, elem2_id)

    # Blending

    def blend_spaces(
        self,
        space_ids: List[str],
        name: str = "Blend"
    ) -> Optional[Blend]:
        """Blend multiple spaces."""
        with self._lock:
            spaces = [self._spaces.get(sid) for sid in space_ids]
            spaces = [s for s in spaces if s is not None]

            if len(spaces) < 2:
                return None

            # Find mappings
            mappings = []
            for i in range(len(spaces)):
                for j in range(i + 1, len(spaces)):
                    mapping = self._mapper.find_mappings(spaces[i], spaces[j])
                    mappings.append(mapping)

            # Extract generic space
            generic = self._mapper.extract_generic_space(spaces, mappings)

            # Create blend
            blend = self._blender.blend(spaces, mappings, generic, name)

            self._blends[blend.id] = blend
            return blend

    def quick_blend(
        self,
        concept1: Dict[str, Any],
        concept2: Dict[str, Any],
        name: str = "Quick Blend"
    ) -> Blend:
        """Quick blend of two concepts."""
        with self._lock:
            # Create spaces from concepts
            space1 = self.create_space("Input1", concept1)
            space2 = self.create_space("Input2", concept2)

            return self.blend_spaces([space1.id, space2.id], name)

    def elaborate(
        self,
        blend_id: str,
        elaboration: str
    ) -> Optional[Blend]:
        """Elaborate blend."""
        blend = self._blends.get(blend_id)
        if blend:
            return self._blender.elaborate(blend, elaboration)
        return None

    # Evaluation

    def evaluate_blend(
        self,
        blend_id: str
    ) -> Optional[BlendQuality]:
        """Evaluate blend quality."""
        blend = self._blends.get(blend_id)
        if not blend:
            return None

        input_spaces = [
            self._spaces.get(sid) for sid in blend.input_spaces
        ]
        input_spaces = [s for s in input_spaces if s]

        return self._evaluator.evaluate(blend, input_spaces)

    def get_blend(self, blend_id: str) -> Optional[Blend]:
        """Get blend by ID."""
        return self._blends.get(blend_id)

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'spaces': len(self._spaces),
            'blends': len(self._blends)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_blending_engine() -> ConceptualBlendingEngine:
    """Create conceptual blending engine."""
    return ConceptualBlendingEngine()


def blend_concepts(
    concept1: Dict[str, Any],
    concept2: Dict[str, Any]
) -> Dict[str, Any]:
    """Quick concept blending."""
    engine = create_blending_engine()
    blend = engine.quick_blend(concept1, concept2)

    if blend:
        return {
            'name': blend.name,
            'type': blend.blend_type.name,
            'elements': len(blend.blended_space.elements),
            'emergent': len(blend.emergent_structure)
        }
    return {}
