#!/usr/bin/env python3
"""
BAEL - Concept Learner
Advanced concept formation and learning.

Features:
- Concept lattice construction
- Version space learning
- Generalization hierarchies
- Concept clustering
- Feature importance
- Incremental concept learning
"""

import asyncio
import copy
import hashlib
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ConceptType(Enum):
    """Types of concepts."""
    PRIMITIVE = "primitive"
    CONJUNCTIVE = "conjunctive"
    DISJUNCTIVE = "disjunctive"
    NEGATED = "negated"
    COMPOSITE = "composite"


class GeneralizationType(Enum):
    """Types of generalization."""
    MINIMAL = "minimal"
    DROPPING_CONDITION = "dropping_condition"
    CLIMBING_TREE = "climbing_tree"
    TURNING_TO_VARIABLE = "turning_to_variable"


class SpecializationType(Enum):
    """Types of specialization."""
    ADDING_CONDITION = "adding_condition"
    DESCENDING_TREE = "descending_tree"
    BINDING_VARIABLE = "binding_variable"


class LearningStatus(Enum):
    """Status of concept learning."""
    LEARNING = "learning"
    CONVERGED = "converged"
    COLLAPSED = "collapsed"  # Version space collapsed


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Feature:
    """A feature with possible values."""
    feat_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    possible_values: List[Any] = field(default_factory=list)
    is_ordered: bool = False
    hierarchy: Dict[Any, Any] = field(default_factory=dict)  # Value -> parent


@dataclass
class Instance:
    """A training instance."""
    inst_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    features: Dict[str, Any] = field(default_factory=dict)
    is_positive: bool = True


@dataclass
class Concept:
    """A concept (conjunction of constraints)."""
    concept_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    constraints: Dict[str, Any] = field(default_factory=dict)
    concept_type: ConceptType = ConceptType.CONJUNCTIVE
    extension: Set[str] = field(default_factory=set)  # Instance IDs
    intension: Set[str] = field(default_factory=set)  # Feature constraints

    def __str__(self):
        if not self.constraints:
            return "⊤ (most general)"

        parts = []
        for feat, val in self.constraints.items():
            if val is None:
                continue
            if val == "?":
                continue
            if isinstance(val, set):
                parts.append(f"{feat} ∈ {val}")
            else:
                parts.append(f"{feat}={val}")

        if not parts:
            return "⊤ (most general)"

        return " ∧ ".join(parts)

    def covers(self, instance: Instance) -> bool:
        """Check if concept covers instance."""
        for feat, constraint in self.constraints.items():
            if constraint is None or constraint == "?":
                continue

            inst_val = instance.features.get(feat)

            if isinstance(constraint, set):
                if inst_val not in constraint:
                    return False
            else:
                if inst_val != constraint:
                    return False

        return True


@dataclass
class VersionSpace:
    """Version space for concept learning."""
    space_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    s_boundary: List[Concept] = field(default_factory=list)  # Most specific
    g_boundary: List[Concept] = field(default_factory=list)  # Most general
    status: LearningStatus = LearningStatus.LEARNING


@dataclass
class ConceptNode:
    """Node in a concept lattice."""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    concept: Concept = field(default_factory=Concept)
    parents: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    objects: Set[str] = field(default_factory=set)
    attributes: Set[str] = field(default_factory=set)


# =============================================================================
# FEATURE MANAGER
# =============================================================================

class FeatureManager:
    """Manage features."""

    def __init__(self):
        self._features: Dict[str, Feature] = {}

    def add(
        self,
        name: str,
        possible_values: List[Any],
        is_ordered: bool = False,
        hierarchy: Optional[Dict[Any, Any]] = None
    ) -> Feature:
        """Add a feature."""
        feat = Feature(
            name=name,
            possible_values=possible_values,
            is_ordered=is_ordered,
            hierarchy=hierarchy or {}
        )
        self._features[name] = feat
        return feat

    def get(self, name: str) -> Optional[Feature]:
        """Get a feature."""
        return self._features.get(name)

    def all_features(self) -> List[Feature]:
        """Get all features."""
        return list(self._features.values())

    def feature_names(self) -> List[str]:
        """Get all feature names."""
        return list(self._features.keys())

    def infer_from_instances(self, instances: List[Instance]) -> None:
        """Infer features from instances."""
        for inst in instances:
            for name, value in inst.features.items():
                if name not in self._features:
                    self.add(name, [])

                feat = self._features[name]
                if value not in feat.possible_values:
                    feat.possible_values.append(value)


# =============================================================================
# INSTANCE MANAGER
# =============================================================================

class InstanceManager:
    """Manage training instances."""

    def __init__(self):
        self._instances: Dict[str, Instance] = {}

    def add(
        self,
        features: Dict[str, Any],
        is_positive: bool = True
    ) -> Instance:
        """Add an instance."""
        inst = Instance(features=features, is_positive=is_positive)
        self._instances[inst.inst_id] = inst
        return inst

    def get(self, inst_id: str) -> Optional[Instance]:
        """Get an instance."""
        return self._instances.get(inst_id)

    def positive_instances(self) -> List[Instance]:
        """Get positive instances."""
        return [i for i in self._instances.values() if i.is_positive]

    def negative_instances(self) -> List[Instance]:
        """Get negative instances."""
        return [i for i in self._instances.values() if not i.is_positive]

    def all_instances(self) -> List[Instance]:
        """Get all instances."""
        return list(self._instances.values())


# =============================================================================
# VERSION SPACE LEARNER
# =============================================================================

class VersionSpaceLearner:
    """Learn concepts using version space."""

    def __init__(self, features: FeatureManager):
        self._features = features

    def initialize(self) -> VersionSpace:
        """Initialize version space with most general and specific concepts."""
        # Most general: no constraints
        most_general = Concept(
            name="most_general",
            constraints={f: "?" for f in self._features.feature_names()}
        )

        # Most specific: impossible concept (all values null)
        most_specific = Concept(
            name="most_specific",
            constraints={f: None for f in self._features.feature_names()}
        )

        return VersionSpace(
            s_boundary=[most_specific],
            g_boundary=[most_general]
        )

    def update(
        self,
        space: VersionSpace,
        instance: Instance
    ) -> VersionSpace:
        """Update version space with new instance."""
        if space.status == LearningStatus.COLLAPSED:
            return space

        if instance.is_positive:
            return self._update_positive(space, instance)
        else:
            return self._update_negative(space, instance)

    def _update_positive(
        self,
        space: VersionSpace,
        instance: Instance
    ) -> VersionSpace:
        """Update with positive instance."""
        # Remove from G any hypothesis inconsistent with instance
        space.g_boundary = [
            g for g in space.g_boundary
            if g.covers(instance)
        ]

        # For each s in S that doesn't cover instance
        new_s_boundary = []

        for s in space.s_boundary:
            if s.covers(instance):
                new_s_boundary.append(s)
            else:
                # Generalize s minimally to cover instance
                generalized = self._generalize(s, instance)

                for gen in generalized:
                    # Only keep if consistent with some g in G
                    if any(self._more_specific(gen, g) for g in space.g_boundary):
                        new_s_boundary.append(gen)

        # Remove from S any s that is more general than another s in S
        space.s_boundary = self._remove_subsumed(new_s_boundary, more_general=True)

        self._check_collapsed(space)

        return space

    def _update_negative(
        self,
        space: VersionSpace,
        instance: Instance
    ) -> VersionSpace:
        """Update with negative instance."""
        # Remove from S any hypothesis that covers instance
        space.s_boundary = [
            s for s in space.s_boundary
            if not s.covers(instance)
        ]

        # For each g in G that covers instance
        new_g_boundary = []

        for g in space.g_boundary:
            if not g.covers(instance):
                new_g_boundary.append(g)
            else:
                # Specialize g minimally to not cover instance
                specialized = self._specialize(g, instance)

                for spec in specialized:
                    # Only keep if consistent with some s in S
                    if any(self._more_specific(s, spec) for s in space.s_boundary):
                        new_g_boundary.append(spec)

        # Remove from G any g that is more specific than another g in G
        space.g_boundary = self._remove_subsumed(new_g_boundary, more_general=False)

        self._check_collapsed(space)

        return space

    def _generalize(
        self,
        concept: Concept,
        instance: Instance
    ) -> List[Concept]:
        """Minimally generalize concept to cover instance."""
        new_constraints = {}

        for feat in self._features.feature_names():
            c_val = concept.constraints.get(feat)
            i_val = instance.features.get(feat)

            if c_val is None:
                # Was most specific, now take instance value
                new_constraints[feat] = i_val
            elif c_val == "?":
                # Already most general
                new_constraints[feat] = "?"
            elif c_val == i_val:
                # Already matches
                new_constraints[feat] = c_val
            else:
                # Conflict - generalize to "?"
                new_constraints[feat] = "?"

        return [Concept(
            name="generalized",
            constraints=new_constraints
        )]

    def _specialize(
        self,
        concept: Concept,
        instance: Instance
    ) -> List[Concept]:
        """Minimally specialize concept to not cover instance."""
        specializations = []

        for feat in self._features.feature_names():
            c_val = concept.constraints.get(feat)
            i_val = instance.features.get(feat)

            if c_val == "?":
                # Can specialize to any value except i_val
                feat_obj = self._features.get(feat)
                if feat_obj:
                    for val in feat_obj.possible_values:
                        if val != i_val:
                            new_constraints = concept.constraints.copy()
                            new_constraints[feat] = val
                            specializations.append(Concept(
                                name="specialized",
                                constraints=new_constraints
                            ))

        return specializations

    def _more_specific(self, c1: Concept, c2: Concept) -> bool:
        """Check if c1 is more specific than or equal to c2."""
        for feat in self._features.feature_names():
            v1 = c1.constraints.get(feat)
            v2 = c2.constraints.get(feat)

            if v2 == "?":
                continue
            if v1 != v2:
                return False

        return True

    def _remove_subsumed(
        self,
        concepts: List[Concept],
        more_general: bool
    ) -> List[Concept]:
        """Remove subsumed concepts."""
        result = []

        for c in concepts:
            subsumed = False
            for other in concepts:
                if c is other:
                    continue

                if more_general:
                    # Remove if c is more general than other
                    if self._more_specific(other, c) and not self._more_specific(c, other):
                        subsumed = True
                        break
                else:
                    # Remove if c is more specific than other
                    if self._more_specific(c, other) and not self._more_specific(other, c):
                        subsumed = True
                        break

            if not subsumed:
                result.append(c)

        return result

    def _check_collapsed(self, space: VersionSpace) -> None:
        """Check if version space has collapsed."""
        if not space.s_boundary or not space.g_boundary:
            space.status = LearningStatus.COLLAPSED
        elif len(space.s_boundary) == 1 and len(space.g_boundary) == 1:
            if str(space.s_boundary[0]) == str(space.g_boundary[0]):
                space.status = LearningStatus.CONVERGED


# =============================================================================
# CONCEPT CLUSTER
# =============================================================================

class ConceptCluster:
    """Cluster instances into concepts."""

    def __init__(self, features: FeatureManager):
        self._features = features

    def cluster(
        self,
        instances: List[Instance],
        n_clusters: int = 3
    ) -> List[Concept]:
        """Cluster instances into concepts."""
        if not instances:
            return []

        # Simple clustering by feature similarity
        clusters: List[List[Instance]] = [[] for _ in range(n_clusters)]

        for i, inst in enumerate(instances):
            cluster_idx = i % n_clusters
            clusters[cluster_idx].append(inst)

        # Create concept for each cluster
        concepts = []
        for i, cluster in enumerate(clusters):
            if not cluster:
                continue

            concept = self._concept_from_cluster(cluster, f"cluster_{i}")
            concepts.append(concept)

        return concepts

    def _concept_from_cluster(
        self,
        instances: List[Instance],
        name: str
    ) -> Concept:
        """Create concept from cluster of instances."""
        constraints = {}

        for feat in self._features.feature_names():
            values = set()
            for inst in instances:
                if feat in inst.features:
                    values.add(inst.features[feat])

            if len(values) == 1:
                constraints[feat] = list(values)[0]
            elif len(values) > 1:
                constraints[feat] = values
            else:
                constraints[feat] = "?"

        return Concept(
            name=name,
            constraints=constraints,
            extension={i.inst_id for i in instances}
        )


# =============================================================================
# CONCEPT LEARNER
# =============================================================================

class ConceptLearner:
    """
    Concept Learner for BAEL.

    Advanced concept formation and learning.
    """

    def __init__(self):
        self._features = FeatureManager()
        self._instances = InstanceManager()
        self._vs_learner = VersionSpaceLearner(self._features)
        self._clusterer = ConceptCluster(self._features)
        self._version_space: Optional[VersionSpace] = None
        self._learned_concepts: List[Concept] = []

    # -------------------------------------------------------------------------
    # FEATURES
    # -------------------------------------------------------------------------

    def add_feature(
        self,
        name: str,
        possible_values: List[Any],
        is_ordered: bool = False,
        hierarchy: Optional[Dict[Any, Any]] = None
    ) -> Feature:
        """Add a feature."""
        feat = self._features.add(name, possible_values, is_ordered, hierarchy)
        # Reinitialize version space learner
        self._vs_learner = VersionSpaceLearner(self._features)
        return feat

    def get_feature(self, name: str) -> Optional[Feature]:
        """Get a feature."""
        return self._features.get(name)

    def all_features(self) -> List[Feature]:
        """Get all features."""
        return self._features.all_features()

    # -------------------------------------------------------------------------
    # INSTANCES
    # -------------------------------------------------------------------------

    def add_positive(self, features: Dict[str, Any]) -> Instance:
        """Add a positive instance."""
        return self._instances.add(features, is_positive=True)

    def add_negative(self, features: Dict[str, Any]) -> Instance:
        """Add a negative instance."""
        return self._instances.add(features, is_positive=False)

    def positive_instances(self) -> List[Instance]:
        """Get positive instances."""
        return self._instances.positive_instances()

    def negative_instances(self) -> List[Instance]:
        """Get negative instances."""
        return self._instances.negative_instances()

    def all_instances(self) -> List[Instance]:
        """Get all instances."""
        return self._instances.all_instances()

    # -------------------------------------------------------------------------
    # VERSION SPACE LEARNING
    # -------------------------------------------------------------------------

    def initialize_version_space(self) -> VersionSpace:
        """Initialize version space."""
        self._features.infer_from_instances(self._instances.all_instances())
        self._vs_learner = VersionSpaceLearner(self._features)
        self._version_space = self._vs_learner.initialize()
        return self._version_space

    def learn_from_instance(self, instance: Instance) -> VersionSpace:
        """Learn from a new instance."""
        if self._version_space is None:
            self.initialize_version_space()

        self._version_space = self._vs_learner.update(
            self._version_space, instance
        )
        return self._version_space

    def learn_all(self) -> VersionSpace:
        """Learn from all instances."""
        self.initialize_version_space()

        for inst in self._instances.all_instances():
            self._version_space = self._vs_learner.update(
                self._version_space, inst
            )

        return self._version_space

    def get_version_space(self) -> Optional[VersionSpace]:
        """Get current version space."""
        return self._version_space

    def get_s_boundary(self) -> List[Concept]:
        """Get S boundary (most specific hypotheses)."""
        if self._version_space:
            return self._version_space.s_boundary
        return []

    def get_g_boundary(self) -> List[Concept]:
        """Get G boundary (most general hypotheses)."""
        if self._version_space:
            return self._version_space.g_boundary
        return []

    def learning_status(self) -> LearningStatus:
        """Get learning status."""
        if self._version_space:
            return self._version_space.status
        return LearningStatus.LEARNING

    # -------------------------------------------------------------------------
    # CONCEPT PREDICTION
    # -------------------------------------------------------------------------

    def classify(self, features: Dict[str, Any]) -> Optional[bool]:
        """Classify a new instance."""
        if not self._version_space:
            return None

        instance = Instance(features=features)

        # Check all S boundary concepts
        all_s_cover = all(s.covers(instance) for s in self._version_space.s_boundary)

        # Check all G boundary concepts
        any_g_covers = any(g.covers(instance) for g in self._version_space.g_boundary)

        if all_s_cover:
            return True
        elif not any_g_covers:
            return False
        else:
            return None  # Uncertain

    # -------------------------------------------------------------------------
    # CLUSTERING
    # -------------------------------------------------------------------------

    def cluster_concepts(self, n_clusters: int = 3) -> List[Concept]:
        """Cluster instances into concepts."""
        self._features.infer_from_instances(self._instances.all_instances())
        self._clusterer = ConceptCluster(self._features)

        concepts = self._clusterer.cluster(
            self._instances.positive_instances(),
            n_clusters
        )

        self._learned_concepts = concepts
        return concepts

    def get_concepts(self) -> List[Concept]:
        """Get learned concepts."""
        return self._learned_concepts

    # -------------------------------------------------------------------------
    # CONCEPT OPERATIONS
    # -------------------------------------------------------------------------

    def generalize(self, concept: Concept) -> Concept:
        """Generalize a concept by dropping a constraint."""
        if not concept.constraints:
            return concept

        # Drop least important constraint
        new_constraints = concept.constraints.copy()

        for feat in new_constraints:
            if new_constraints[feat] != "?":
                new_constraints[feat] = "?"
                break

        return Concept(
            name=f"{concept.name}_generalized",
            constraints=new_constraints
        )

    def specialize(
        self,
        concept: Concept,
        feature: str,
        value: Any
    ) -> Concept:
        """Specialize a concept by adding a constraint."""
        new_constraints = concept.constraints.copy()
        new_constraints[feature] = value

        return Concept(
            name=f"{concept.name}_specialized",
            constraints=new_constraints
        )

    def concept_coverage(self, concept: Concept) -> Tuple[int, int]:
        """Get coverage of concept (positive, negative)."""
        pos_covered = sum(
            1 for inst in self._instances.positive_instances()
            if concept.covers(inst)
        )
        neg_covered = sum(
            1 for inst in self._instances.negative_instances()
            if concept.covers(inst)
        )
        return pos_covered, neg_covered


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Concept Learner."""
    print("=" * 70)
    print("BAEL - CONCEPT LEARNER DEMO")
    print("Advanced Concept Formation and Learning")
    print("=" * 70)
    print()

    learner = ConceptLearner()

    # 1. Add Features
    print("1. ADD FEATURES:")
    print("-" * 40)

    learner.add_feature("size", ["small", "medium", "large"])
    learner.add_feature("color", ["red", "blue", "green"])
    learner.add_feature("shape", ["circle", "square", "triangle"])

    for feat in learner.all_features():
        print(f"   {feat.name}: {feat.possible_values}")
    print()

    # 2. Add Training Instances
    print("2. ADD TRAINING INSTANCES:")
    print("-" * 40)

    # Positive examples (concept: large circles)
    learner.add_positive({"size": "large", "color": "red", "shape": "circle"})
    learner.add_positive({"size": "large", "color": "blue", "shape": "circle"})
    learner.add_positive({"size": "large", "color": "green", "shape": "circle"})

    # Negative examples
    learner.add_negative({"size": "small", "color": "red", "shape": "circle"})
    learner.add_negative({"size": "large", "color": "red", "shape": "square"})
    learner.add_negative({"size": "medium", "color": "blue", "shape": "triangle"})

    print(f"   Positive instances: {len(learner.positive_instances())}")
    print(f"   Negative instances: {len(learner.negative_instances())}")
    print()

    # 3. Initialize Version Space
    print("3. INITIALIZE VERSION SPACE:")
    print("-" * 40)

    space = learner.initialize_version_space()
    print(f"   S boundary: {[str(s) for s in space.s_boundary]}")
    print(f"   G boundary: {[str(g) for g in space.g_boundary]}")
    print()

    # 4. Learn from Instances
    print("4. LEARN FROM INSTANCES:")
    print("-" * 40)

    space = learner.learn_all()
    print(f"   Status: {learner.learning_status().value}")
    print()

    print("   S boundary (most specific):")
    for s in learner.get_s_boundary():
        print(f"      {s}")

    print("   G boundary (most general):")
    for g in learner.get_g_boundary():
        print(f"      {g}")
    print()

    # 5. Classify New Instances
    print("5. CLASSIFY NEW INSTANCES:")
    print("-" * 40)

    test1 = {"size": "large", "color": "red", "shape": "circle"}
    test2 = {"size": "small", "color": "blue", "shape": "circle"}
    test3 = {"size": "large", "color": "green", "shape": "circle"}
    test4 = {"size": "medium", "color": "red", "shape": "square"}

    for test in [test1, test2, test3, test4]:
        result = learner.classify(test)
        result_str = "positive" if result else ("negative" if result is False else "uncertain")
        print(f"   {test} → {result_str}")
    print()

    # 6. Concept Operations
    print("6. CONCEPT OPERATIONS:")
    print("-" * 40)

    if learner.get_s_boundary():
        concept = learner.get_s_boundary()[0]
        print(f"   Original: {concept}")

        generalized = learner.generalize(concept)
        print(f"   Generalized: {generalized}")

        specialized = learner.specialize(concept, "color", "red")
        print(f"   Specialized: {specialized}")
    print()

    # 7. Concept Coverage
    print("7. CONCEPT COVERAGE:")
    print("-" * 40)

    for s in learner.get_s_boundary():
        pos, neg = learner.concept_coverage(s)
        print(f"   {s}")
        print(f"      Covers: {pos} positive, {neg} negative")
    print()

    # 8. Cluster Concepts
    print("8. CLUSTER CONCEPTS:")
    print("-" * 40)

    # Add more instances for clustering
    learner2 = ConceptLearner()
    learner2.add_positive({"size": "large", "color": "red", "shape": "circle"})
    learner2.add_positive({"size": "large", "color": "blue", "shape": "circle"})
    learner2.add_positive({"size": "small", "color": "red", "shape": "square"})
    learner2.add_positive({"size": "small", "color": "blue", "shape": "square"})
    learner2.add_positive({"size": "medium", "color": "green", "shape": "triangle"})

    clusters = learner2.cluster_concepts(n_clusters=2)
    for i, c in enumerate(clusters):
        print(f"   Cluster {i+1}: {c}")
    print()

    # 9. Incremental Learning
    print("9. INCREMENTAL LEARNING:")
    print("-" * 40)

    learner3 = ConceptLearner()
    learner3.add_feature("size", ["small", "large"])
    learner3.add_feature("color", ["red", "blue"])

    space = learner3.initialize_version_space()
    print(f"   Initial: S={len(space.s_boundary)}, G={len(space.g_boundary)}")

    # Add instances one by one
    instances = [
        ({"size": "large", "color": "red"}, True),
        ({"size": "small", "color": "blue"}, False),
        ({"size": "large", "color": "blue"}, True),
    ]

    for features, is_positive in instances:
        inst = Instance(features=features, is_positive=is_positive)
        learner3._instances._instances[inst.inst_id] = inst
        space = learner3.learn_from_instance(inst)

        label = "+" if is_positive else "-"
        print(f"   After {label}{features}: S={len(space.s_boundary)}, G={len(space.g_boundary)}")

    print(f"\n   Final learned concept:")
    for s in learner3.get_s_boundary():
        print(f"      {s}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Concept Learner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
