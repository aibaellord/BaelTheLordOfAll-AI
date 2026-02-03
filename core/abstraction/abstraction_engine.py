#!/usr/bin/env python3
"""
BAEL - Abstraction Engine
Abstraction levels and concept modeling for agents.

Features:
- Abstraction level management
- Concept hierarchy
- Feature extraction
- Generalization/specialization
- Abstract reasoning
"""

import asyncio
import hashlib
import json
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class AbstractionLevel(Enum):
    """Abstraction levels."""
    CONCRETE = "concrete"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ABSTRACT = "abstract"


class ConceptType(Enum):
    """Concept types."""
    ENTITY = "entity"
    ATTRIBUTE = "attribute"
    RELATION = "relation"
    ACTION = "action"
    STATE = "state"


class FeatureType(Enum):
    """Feature types."""
    ESSENTIAL = "essential"
    OPTIONAL = "optional"
    DERIVED = "derived"
    INHERITED = "inherited"


class RelationType(Enum):
    """Relation types."""
    IS_A = "is_a"
    HAS_A = "has_a"
    PART_OF = "part_of"
    DEPENDS_ON = "depends_on"
    ASSOCIATED = "associated"


class TransformType(Enum):
    """Transformation types."""
    GENERALIZE = "generalize"
    SPECIALIZE = "specialize"
    COMPOSE = "compose"
    DECOMPOSE = "decompose"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Feature:
    """A concept feature."""
    feature_id: str = ""
    name: str = ""
    value: Any = None
    feature_type: FeatureType = FeatureType.ESSENTIAL
    weight: float = 1.0

    def __post_init__(self):
        if not self.feature_id:
            self.feature_id = str(uuid.uuid4())[:8]


@dataclass
class Concept:
    """An abstract concept."""
    concept_id: str = ""
    name: str = ""
    concept_type: ConceptType = ConceptType.ENTITY
    level: AbstractionLevel = AbstractionLevel.MEDIUM
    features: Dict[str, Feature] = field(default_factory=dict)
    parents: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.concept_id:
            self.concept_id = str(uuid.uuid4())[:8]


@dataclass
class Relation:
    """A relation between concepts."""
    relation_id: str = ""
    source_id: str = ""
    target_id: str = ""
    relation_type: RelationType = RelationType.ASSOCIATED
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.relation_id:
            self.relation_id = str(uuid.uuid4())[:8]


@dataclass
class Transformation:
    """A concept transformation."""
    transform_id: str = ""
    transform_type: TransformType = TransformType.GENERALIZE
    source_ids: List[str] = field(default_factory=list)
    result_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.transform_id:
            self.transform_id = str(uuid.uuid4())[:8]


@dataclass
class AbstractionConfig:
    """Abstraction engine configuration."""
    max_concepts: int = 10000
    max_depth: int = 10
    auto_generalize: bool = True
    similarity_threshold: float = 0.7


# =============================================================================
# FEATURE EXTRACTOR
# =============================================================================

class FeatureExtractor:
    """Extract features from data."""

    def extract(self, data: Any) -> List[Feature]:
        """Extract features from data."""
        features = []

        if isinstance(data, dict):
            for key, value in data.items():
                feature = Feature(
                    name=key,
                    value=value,
                    feature_type=FeatureType.ESSENTIAL
                )
                features.append(feature)

        elif isinstance(data, (list, tuple)):
            for i, value in enumerate(data):
                feature = Feature(
                    name=f"item_{i}",
                    value=value,
                    feature_type=FeatureType.OPTIONAL
                )
                features.append(feature)

        elif hasattr(data, "__dict__"):
            for key, value in data.__dict__.items():
                if not key.startswith("_"):
                    feature = Feature(
                        name=key,
                        value=value,
                        feature_type=FeatureType.ESSENTIAL
                    )
                    features.append(feature)

        else:
            feature = Feature(
                name="value",
                value=data,
                feature_type=FeatureType.ESSENTIAL
            )
            features.append(feature)

        return features

    def extract_common(self, concepts: List[Concept]) -> List[Feature]:
        """Extract common features from concepts."""
        if not concepts:
            return []

        feature_counts: Dict[str, int] = defaultdict(int)
        feature_values: Dict[str, List[Any]] = defaultdict(list)

        for concept in concepts:
            for name, feature in concept.features.items():
                feature_counts[name] += 1
                feature_values[name].append(feature.value)

        common_features = []
        threshold = len(concepts) * 0.7

        for name, count in feature_counts.items():
            if count >= threshold:
                values = feature_values[name]

                if len(set(str(v) for v in values)) == 1:
                    value = values[0]
                else:
                    value = None

                feature = Feature(
                    name=name,
                    value=value,
                    feature_type=FeatureType.INHERITED,
                    weight=count / len(concepts)
                )
                common_features.append(feature)

        return common_features


# =============================================================================
# SIMILARITY CALCULATOR
# =============================================================================

class SimilarityCalculator:
    """Calculate similarity between concepts."""

    def calculate(self, concept1: Concept, concept2: Concept) -> float:
        """Calculate similarity between concepts."""
        if not concept1.features or not concept2.features:
            return 0.0

        features1 = set(concept1.features.keys())
        features2 = set(concept2.features.keys())

        common = features1.intersection(features2)
        total = features1.union(features2)

        if not total:
            return 0.0

        jaccard = len(common) / len(total)

        value_similarity = 0.0
        if common:
            matching_values = 0
            for name in common:
                v1 = concept1.features[name].value
                v2 = concept2.features[name].value
                if v1 == v2:
                    matching_values += 1
            value_similarity = matching_values / len(common)

        return (jaccard + value_similarity) / 2

    def find_similar(
        self,
        concept: Concept,
        concepts: List[Concept],
        threshold: float = 0.5
    ) -> List[Tuple[Concept, float]]:
        """Find similar concepts."""
        results = []

        for other in concepts:
            if other.concept_id != concept.concept_id:
                similarity = self.calculate(concept, other)
                if similarity >= threshold:
                    results.append((other, similarity))

        results.sort(key=lambda x: x[1], reverse=True)

        return results


# =============================================================================
# CONCEPT HIERARCHY
# =============================================================================

class ConceptHierarchy:
    """Manage concept hierarchy."""

    def __init__(self, max_depth: int = 10):
        self._concepts: Dict[str, Concept] = {}
        self._max_depth = max_depth

    def add(self, concept: Concept) -> None:
        """Add concept to hierarchy."""
        self._concepts[concept.concept_id] = concept

    def get(self, concept_id: str) -> Optional[Concept]:
        """Get concept by ID."""
        return self._concepts.get(concept_id)

    def get_by_name(self, name: str) -> Optional[Concept]:
        """Get concept by name."""
        for concept in self._concepts.values():
            if concept.name == name:
                return concept
        return None

    def set_parent(self, child_id: str, parent_id: str) -> bool:
        """Set parent-child relationship."""
        child = self._concepts.get(child_id)
        parent = self._concepts.get(parent_id)

        if not child or not parent:
            return False

        if parent_id not in child.parents:
            child.parents.append(parent_id)

        if child_id not in parent.children:
            parent.children.append(child_id)

        return True

    def get_parents(self, concept_id: str) -> List[Concept]:
        """Get parent concepts."""
        concept = self._concepts.get(concept_id)
        if not concept:
            return []

        return [self._concepts[pid] for pid in concept.parents if pid in self._concepts]

    def get_children(self, concept_id: str) -> List[Concept]:
        """Get child concepts."""
        concept = self._concepts.get(concept_id)
        if not concept:
            return []

        return [self._concepts[cid] for cid in concept.children if cid in self._concepts]

    def get_ancestors(self, concept_id: str, max_depth: Optional[int] = None) -> List[Concept]:
        """Get all ancestors."""
        if max_depth is None:
            max_depth = self._max_depth

        ancestors = []
        visited = set()
        queue = [concept_id]
        depth = 0

        while queue and depth < max_depth:
            current_id = queue.pop(0)

            if current_id in visited:
                continue
            visited.add(current_id)

            concept = self._concepts.get(current_id)
            if concept:
                for parent_id in concept.parents:
                    if parent_id not in visited:
                        parent = self._concepts.get(parent_id)
                        if parent:
                            ancestors.append(parent)
                            queue.append(parent_id)

            depth += 1

        return ancestors

    def get_descendants(self, concept_id: str, max_depth: Optional[int] = None) -> List[Concept]:
        """Get all descendants."""
        if max_depth is None:
            max_depth = self._max_depth

        descendants = []
        visited = set()
        queue = [concept_id]
        depth = 0

        while queue and depth < max_depth:
            current_id = queue.pop(0)

            if current_id in visited:
                continue
            visited.add(current_id)

            concept = self._concepts.get(current_id)
            if concept:
                for child_id in concept.children:
                    if child_id not in visited:
                        child = self._concepts.get(child_id)
                        if child:
                            descendants.append(child)
                            queue.append(child_id)

            depth += 1

        return descendants

    def get_depth(self, concept_id: str) -> int:
        """Get depth in hierarchy."""
        concept = self._concepts.get(concept_id)
        if not concept or not concept.parents:
            return 0

        parent_depths = []
        for parent_id in concept.parents:
            parent_depths.append(self.get_depth(parent_id) + 1)

        return max(parent_depths) if parent_depths else 0

    def get_by_level(self, level: AbstractionLevel) -> List[Concept]:
        """Get concepts by abstraction level."""
        return [c for c in self._concepts.values() if c.level == level]

    def count(self) -> int:
        """Count concepts."""
        return len(self._concepts)

    def all(self) -> List[Concept]:
        """Get all concepts."""
        return list(self._concepts.values())

    def remove(self, concept_id: str) -> bool:
        """Remove concept."""
        if concept_id not in self._concepts:
            return False

        concept = self._concepts[concept_id]

        for parent_id in concept.parents:
            parent = self._concepts.get(parent_id)
            if parent and concept_id in parent.children:
                parent.children.remove(concept_id)

        for child_id in concept.children:
            child = self._concepts.get(child_id)
            if child and concept_id in child.parents:
                child.parents.remove(concept_id)

        del self._concepts[concept_id]

        return True


# =============================================================================
# RELATION MANAGER
# =============================================================================

class RelationManager:
    """Manage concept relations."""

    def __init__(self):
        self._relations: Dict[str, Relation] = {}
        self._by_source: Dict[str, List[str]] = defaultdict(list)
        self._by_target: Dict[str, List[str]] = defaultdict(list)

    def add(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType = RelationType.ASSOCIATED,
        weight: float = 1.0
    ) -> Relation:
        """Add a relation."""
        relation = Relation(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight
        )

        self._relations[relation.relation_id] = relation
        self._by_source[source_id].append(relation.relation_id)
        self._by_target[target_id].append(relation.relation_id)

        return relation

    def get(self, relation_id: str) -> Optional[Relation]:
        """Get relation by ID."""
        return self._relations.get(relation_id)

    def get_from(self, source_id: str) -> List[Relation]:
        """Get relations from source."""
        relation_ids = self._by_source.get(source_id, [])
        return [self._relations[rid] for rid in relation_ids if rid in self._relations]

    def get_to(self, target_id: str) -> List[Relation]:
        """Get relations to target."""
        relation_ids = self._by_target.get(target_id, [])
        return [self._relations[rid] for rid in relation_ids if rid in self._relations]

    def get_between(self, source_id: str, target_id: str) -> List[Relation]:
        """Get relations between two concepts."""
        from_source = self.get_from(source_id)
        return [r for r in from_source if r.target_id == target_id]

    def remove(self, relation_id: str) -> bool:
        """Remove a relation."""
        relation = self._relations.get(relation_id)
        if not relation:
            return False

        if relation_id in self._by_source.get(relation.source_id, []):
            self._by_source[relation.source_id].remove(relation_id)

        if relation_id in self._by_target.get(relation.target_id, []):
            self._by_target[relation.target_id].remove(relation_id)

        del self._relations[relation_id]

        return True

    def count(self) -> int:
        """Count relations."""
        return len(self._relations)


# =============================================================================
# GENERALIZER
# =============================================================================

class Generalizer:
    """Generalize concepts."""

    def __init__(self):
        self._feature_extractor = FeatureExtractor()

    def generalize(
        self,
        concepts: List[Concept],
        name: str = ""
    ) -> Concept:
        """Generalize multiple concepts into one."""
        if not concepts:
            return Concept(name=name or "empty_concept")

        if len(concepts) == 1:
            return concepts[0]

        common_features = self._feature_extractor.extract_common(concepts)

        max_level = max(c.level.value for c in concepts)
        level_order = [
            AbstractionLevel.CONCRETE,
            AbstractionLevel.LOW,
            AbstractionLevel.MEDIUM,
            AbstractionLevel.HIGH,
            AbstractionLevel.ABSTRACT
        ]

        current_idx = next(
            (i for i, l in enumerate(level_order) if l.value == max_level),
            2
        )
        new_level = level_order[min(current_idx + 1, len(level_order) - 1)]

        if not name:
            names = [c.name for c in concepts]
            name = f"generalization_of_{'_'.join(names[:3])}"

        generalized = Concept(
            name=name,
            level=new_level,
            features={f.name: f for f in common_features}
        )

        generalized.children = [c.concept_id for c in concepts]

        return generalized


# =============================================================================
# SPECIALIZER
# =============================================================================

class Specializer:
    """Specialize concepts."""

    def specialize(
        self,
        concept: Concept,
        additional_features: Dict[str, Any],
        name: str = ""
    ) -> Concept:
        """Create specialized concept."""
        if not name:
            name = f"{concept.name}_specialized"

        level_order = [
            AbstractionLevel.CONCRETE,
            AbstractionLevel.LOW,
            AbstractionLevel.MEDIUM,
            AbstractionLevel.HIGH,
            AbstractionLevel.ABSTRACT
        ]

        current_idx = next(
            (i for i, l in enumerate(level_order) if l == concept.level),
            2
        )
        new_level = level_order[max(current_idx - 1, 0)]

        new_features = {}
        for name_key, feature in concept.features.items():
            inherited = Feature(
                name=feature.name,
                value=feature.value,
                feature_type=FeatureType.INHERITED,
                weight=feature.weight
            )
            new_features[name_key] = inherited

        for name_key, value in additional_features.items():
            new_features[name_key] = Feature(
                name=name_key,
                value=value,
                feature_type=FeatureType.ESSENTIAL
            )

        specialized = Concept(
            name=name,
            level=new_level,
            features=new_features,
            parents=[concept.concept_id]
        )

        return specialized


# =============================================================================
# ABSTRACTION ENGINE
# =============================================================================

class AbstractionEngine:
    """
    Abstraction Engine for BAEL.

    Abstraction levels and concept modeling.
    """

    def __init__(self, config: Optional[AbstractionConfig] = None):
        self._config = config or AbstractionConfig()

        self._hierarchy = ConceptHierarchy(self._config.max_depth)
        self._relations = RelationManager()
        self._feature_extractor = FeatureExtractor()
        self._similarity_calc = SimilarityCalculator()
        self._generalizer = Generalizer()
        self._specializer = Specializer()

        self._transformations: List[Transformation] = []

    # ----- Concept Operations -----

    def create_concept(
        self,
        name: str,
        features: Optional[Dict[str, Any]] = None,
        concept_type: ConceptType = ConceptType.ENTITY,
        level: AbstractionLevel = AbstractionLevel.MEDIUM
    ) -> Concept:
        """Create a new concept."""
        feature_objs = {}

        if features:
            for key, value in features.items():
                feature_objs[key] = Feature(
                    name=key,
                    value=value,
                    feature_type=FeatureType.ESSENTIAL
                )

        concept = Concept(
            name=name,
            concept_type=concept_type,
            level=level,
            features=feature_objs
        )

        self._hierarchy.add(concept)

        return concept

    def from_data(
        self,
        name: str,
        data: Any,
        level: AbstractionLevel = AbstractionLevel.CONCRETE
    ) -> Concept:
        """Create concept from data."""
        features = self._feature_extractor.extract(data)

        concept = Concept(
            name=name,
            level=level,
            features={f.name: f for f in features}
        )

        self._hierarchy.add(concept)

        return concept

    def get_concept(self, concept_id: str) -> Optional[Concept]:
        """Get concept by ID."""
        return self._hierarchy.get(concept_id)

    def get_by_name(self, name: str) -> Optional[Concept]:
        """Get concept by name."""
        return self._hierarchy.get_by_name(name)

    def remove_concept(self, concept_id: str) -> bool:
        """Remove concept."""
        return self._hierarchy.remove(concept_id)

    # ----- Hierarchy Operations -----

    def set_parent(self, child_id: str, parent_id: str) -> bool:
        """Set parent-child relationship."""
        result = self._hierarchy.set_parent(child_id, parent_id)

        if result:
            self._relations.add(child_id, parent_id, RelationType.IS_A)

        return result

    def get_parents(self, concept_id: str) -> List[Concept]:
        """Get parent concepts."""
        return self._hierarchy.get_parents(concept_id)

    def get_children(self, concept_id: str) -> List[Concept]:
        """Get child concepts."""
        return self._hierarchy.get_children(concept_id)

    def get_ancestors(self, concept_id: str) -> List[Concept]:
        """Get all ancestors."""
        return self._hierarchy.get_ancestors(concept_id)

    def get_descendants(self, concept_id: str) -> List[Concept]:
        """Get all descendants."""
        return self._hierarchy.get_descendants(concept_id)

    def get_depth(self, concept_id: str) -> int:
        """Get concept depth."""
        return self._hierarchy.get_depth(concept_id)

    # ----- Relation Operations -----

    def relate(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType = RelationType.ASSOCIATED,
        weight: float = 1.0
    ) -> Relation:
        """Create relation between concepts."""
        return self._relations.add(source_id, target_id, relation_type, weight)

    def get_relations(self, concept_id: str) -> Tuple[List[Relation], List[Relation]]:
        """Get relations from and to concept."""
        from_relations = self._relations.get_from(concept_id)
        to_relations = self._relations.get_to(concept_id)
        return from_relations, to_relations

    # ----- Similarity -----

    def similarity(self, concept1_id: str, concept2_id: str) -> float:
        """Calculate similarity between concepts."""
        concept1 = self._hierarchy.get(concept1_id)
        concept2 = self._hierarchy.get(concept2_id)

        if not concept1 or not concept2:
            return 0.0

        return self._similarity_calc.calculate(concept1, concept2)

    def find_similar(
        self,
        concept_id: str,
        threshold: float = 0.5
    ) -> List[Tuple[Concept, float]]:
        """Find similar concepts."""
        concept = self._hierarchy.get(concept_id)

        if not concept:
            return []

        return self._similarity_calc.find_similar(
            concept,
            self._hierarchy.all(),
            threshold
        )

    # ----- Transformation Operations -----

    def generalize(
        self,
        concept_ids: List[str],
        name: str = ""
    ) -> Optional[Concept]:
        """Generalize concepts."""
        concepts = [self._hierarchy.get(cid) for cid in concept_ids]
        concepts = [c for c in concepts if c is not None]

        if not concepts:
            return None

        generalized = self._generalizer.generalize(concepts, name)
        self._hierarchy.add(generalized)

        for c in concepts:
            self._hierarchy.set_parent(c.concept_id, generalized.concept_id)

        transform = Transformation(
            transform_type=TransformType.GENERALIZE,
            source_ids=concept_ids,
            result_id=generalized.concept_id
        )
        self._transformations.append(transform)

        return generalized

    def specialize(
        self,
        concept_id: str,
        additional_features: Dict[str, Any],
        name: str = ""
    ) -> Optional[Concept]:
        """Specialize a concept."""
        concept = self._hierarchy.get(concept_id)

        if not concept:
            return None

        specialized = self._specializer.specialize(concept, additional_features, name)
        self._hierarchy.add(specialized)
        self._hierarchy.set_parent(specialized.concept_id, concept_id)

        transform = Transformation(
            transform_type=TransformType.SPECIALIZE,
            source_ids=[concept_id],
            result_id=specialized.concept_id
        )
        self._transformations.append(transform)

        return specialized

    # ----- Level Operations -----

    def get_by_level(self, level: AbstractionLevel) -> List[Concept]:
        """Get concepts by level."""
        return self._hierarchy.get_by_level(level)

    def abstract(self, concept_id: str) -> bool:
        """Raise abstraction level."""
        concept = self._hierarchy.get(concept_id)
        if not concept:
            return False

        level_order = [
            AbstractionLevel.CONCRETE,
            AbstractionLevel.LOW,
            AbstractionLevel.MEDIUM,
            AbstractionLevel.HIGH,
            AbstractionLevel.ABSTRACT
        ]

        current_idx = level_order.index(concept.level)
        if current_idx < len(level_order) - 1:
            concept.level = level_order[current_idx + 1]
            return True

        return False

    def concretize(self, concept_id: str) -> bool:
        """Lower abstraction level."""
        concept = self._hierarchy.get(concept_id)
        if not concept:
            return False

        level_order = [
            AbstractionLevel.CONCRETE,
            AbstractionLevel.LOW,
            AbstractionLevel.MEDIUM,
            AbstractionLevel.HIGH,
            AbstractionLevel.ABSTRACT
        ]

        current_idx = level_order.index(concept.level)
        if current_idx > 0:
            concept.level = level_order[current_idx - 1]
            return True

        return False

    # ----- Feature Operations -----

    def add_feature(
        self,
        concept_id: str,
        name: str,
        value: Any,
        feature_type: FeatureType = FeatureType.ESSENTIAL
    ) -> bool:
        """Add feature to concept."""
        concept = self._hierarchy.get(concept_id)
        if not concept:
            return False

        concept.features[name] = Feature(
            name=name,
            value=value,
            feature_type=feature_type
        )

        return True

    def get_features(self, concept_id: str) -> Dict[str, Feature]:
        """Get concept features."""
        concept = self._hierarchy.get(concept_id)
        if not concept:
            return {}
        return concept.features

    def inherit_features(self, child_id: str, parent_id: str) -> int:
        """Inherit features from parent."""
        child = self._hierarchy.get(child_id)
        parent = self._hierarchy.get(parent_id)

        if not child or not parent:
            return 0

        count = 0
        for name, feature in parent.features.items():
            if name not in child.features:
                inherited = Feature(
                    name=feature.name,
                    value=feature.value,
                    feature_type=FeatureType.INHERITED,
                    weight=feature.weight
                )
                child.features[name] = inherited
                count += 1

        return count

    # ----- Summary -----

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        concepts = self._hierarchy.all()

        by_level = defaultdict(int)
        by_type = defaultdict(int)

        for c in concepts:
            by_level[c.level.value] += 1
            by_type[c.concept_type.value] += 1

        return {
            "total_concepts": len(concepts),
            "by_level": dict(by_level),
            "by_type": dict(by_type),
            "relations": self._relations.count(),
            "transformations": len(self._transformations)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Abstraction Engine."""
    print("=" * 70)
    print("BAEL - ABSTRACTION ENGINE DEMO")
    print("Abstraction Levels and Concept Modeling")
    print("=" * 70)
    print()

    engine = AbstractionEngine()

    # 1. Create Concepts
    print("1. CREATE CONCEPTS:")
    print("-" * 40)

    dog = engine.create_concept(
        "Dog",
        features={"legs": 4, "sound": "bark", "fur": True},
        level=AbstractionLevel.CONCRETE
    )
    print(f"   Created: {dog.name} (level: {dog.level.value})")

    cat = engine.create_concept(
        "Cat",
        features={"legs": 4, "sound": "meow", "fur": True},
        level=AbstractionLevel.CONCRETE
    )
    print(f"   Created: {cat.name} (level: {cat.level.value})")

    bird = engine.create_concept(
        "Bird",
        features={"legs": 2, "sound": "chirp", "feathers": True},
        level=AbstractionLevel.CONCRETE
    )
    print(f"   Created: {bird.name} (level: {bird.level.value})")
    print()

    # 2. Create from Data
    print("2. CREATE FROM DATA:")
    print("-" * 40)

    car_data = {"wheels": 4, "engine": "gasoline", "doors": 4}
    car = engine.from_data("Car", car_data)
    print(f"   Created: {car.name} from dict")
    print(f"   Features: {[f.name for f in car.features.values()]}")
    print()

    # 3. Generalization
    print("3. GENERALIZATION:")
    print("-" * 40)

    mammal = engine.generalize([dog.concept_id, cat.concept_id], "Mammal")
    print(f"   Generalized Dog + Cat -> {mammal.name}")
    print(f"   Level: {mammal.level.value}")
    print(f"   Common features: {[f.name for f in mammal.features.values()]}")
    print()

    # 4. Specialization
    print("4. SPECIALIZATION:")
    print("-" * 40)

    golden = engine.specialize(
        dog.concept_id,
        {"breed": "Golden Retriever", "size": "large"},
        "GoldenRetriever"
    )
    print(f"   Specialized Dog -> {golden.name}")
    print(f"   Level: {golden.level.value}")
    print(f"   Features: {len(golden.features)}")
    print()

    # 5. Hierarchy
    print("5. HIERARCHY:")
    print("-" * 40)

    animal = engine.create_concept("Animal", level=AbstractionLevel.ABSTRACT)
    engine.set_parent(mammal.concept_id, animal.concept_id)
    engine.set_parent(bird.concept_id, animal.concept_id)

    print(f"   Animal children: {[c.name for c in engine.get_children(animal.concept_id)]}")
    print(f"   Dog ancestors: {[c.name for c in engine.get_ancestors(dog.concept_id)]}")
    print(f"   Golden depth: {engine.get_depth(golden.concept_id)}")
    print()

    # 6. Relations
    print("6. RELATIONS:")
    print("-" * 40)

    engine.relate(dog.concept_id, cat.concept_id, RelationType.ASSOCIATED)
    engine.relate(car.concept_id, dog.concept_id, RelationType.HAS_A)

    from_rel, to_rel = engine.get_relations(dog.concept_id)
    print(f"   Relations from Dog: {len(from_rel)}")
    print(f"   Relations to Dog: {len(to_rel)}")
    print()

    # 7. Similarity
    print("7. SIMILARITY:")
    print("-" * 40)

    dog_cat_sim = engine.similarity(dog.concept_id, cat.concept_id)
    dog_bird_sim = engine.similarity(dog.concept_id, bird.concept_id)
    dog_car_sim = engine.similarity(dog.concept_id, car.concept_id)

    print(f"   Dog-Cat similarity: {dog_cat_sim:.2f}")
    print(f"   Dog-Bird similarity: {dog_bird_sim:.2f}")
    print(f"   Dog-Car similarity: {dog_car_sim:.2f}")
    print()

    # 8. Find Similar
    print("8. FIND SIMILAR:")
    print("-" * 40)

    similar = engine.find_similar(dog.concept_id, threshold=0.3)
    print(f"   Similar to Dog:")
    for concept, score in similar[:3]:
        print(f"   - {concept.name}: {score:.2f}")
    print()

    # 9. Abstraction Level Changes
    print("9. ABSTRACTION LEVEL CHANGES:")
    print("-" * 40)

    print(f"   Dog level before: {dog.level.value}")
    engine.abstract(dog.concept_id)
    print(f"   Dog level after abstract(): {dog.level.value}")
    engine.concretize(dog.concept_id)
    print(f"   Dog level after concretize(): {dog.level.value}")
    print()

    # 10. Feature Operations
    print("10. FEATURE OPERATIONS:")
    print("-" * 40)

    engine.add_feature(dog.concept_id, "domesticated", True)
    features = engine.get_features(dog.concept_id)
    print(f"   Dog features: {len(features)}")
    for name, feature in features.items():
        print(f"   - {name}: {feature.value} ({feature.feature_type.value})")
    print()

    # 11. Inherit Features
    print("11. INHERIT FEATURES:")
    print("-" * 40)

    engine.add_feature(animal.concept_id, "living", True)
    engine.add_feature(animal.concept_id, "breathes", True)

    inherited = engine.inherit_features(dog.concept_id, animal.concept_id)
    print(f"   Inherited {inherited} features from Animal to Dog")

    features = engine.get_features(dog.concept_id)
    inherited_features = [f for f in features.values() if f.feature_type == FeatureType.INHERITED]
    print(f"   Dog inherited features: {[f.name for f in inherited_features]}")
    print()

    # 12. Get by Level
    print("12. GET BY LEVEL:")
    print("-" * 40)

    for level in AbstractionLevel:
        concepts = engine.get_by_level(level)
        if concepts:
            print(f"   {level.value}: {[c.name for c in concepts]}")
    print()

    # 13. Descendants
    print("13. DESCENDANTS:")
    print("-" * 40)

    descendants = engine.get_descendants(animal.concept_id)
    print(f"   Animal descendants: {[d.name for d in descendants]}")
    print()

    # 14. Concept Details
    print("14. CONCEPT DETAILS:")
    print("-" * 40)

    concept = engine.get_concept(mammal.concept_id)
    if concept:
        print(f"   ID: {concept.concept_id}")
        print(f"   Name: {concept.name}")
        print(f"   Type: {concept.concept_type.value}")
        print(f"   Level: {concept.level.value}")
        print(f"   Parents: {concept.parents}")
        print(f"   Children: {concept.children}")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Abstraction Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
