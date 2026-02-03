#!/usr/bin/env python3
"""
BAEL - Creativity Engine
Advanced creative reasoning and generation.

Features:
- Divergent thinking
- Concept blending
- Metaphor generation
- Analogy-based creativity
- Constraint relaxation
- Bisociation (connecting frames)
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

class CreativityMode(Enum):
    """Modes of creative thinking."""
    DIVERGENT = "divergent"
    CONVERGENT = "convergent"
    LATERAL = "lateral"
    TRANSFORMATIONAL = "transformational"


class BlendType(Enum):
    """Types of conceptual blending."""
    SIMPLE = "simple"
    MIRROR = "mirror"
    SINGLE_SCOPE = "single_scope"
    DOUBLE_SCOPE = "double_scope"


class MetaphorType(Enum):
    """Types of metaphors."""
    STRUCTURAL = "structural"
    ORIENTATIONAL = "orientational"
    ONTOLOGICAL = "ontological"
    PERSONIFICATION = "personification"


class IdeaStatus(Enum):
    """Status of a creative idea."""
    GENERATED = "generated"
    EVALUATED = "evaluated"
    SELECTED = "selected"
    REFINED = "refined"
    IMPLEMENTED = "implemented"


class NoveltyLevel(Enum):
    """Level of novelty."""
    ROUTINE = "routine"
    ADAPTIVE = "adaptive"
    ORIGINAL = "original"
    BREAKTHROUGH = "breakthrough"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Concept:
    """A concept for creative reasoning."""
    concept_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    domain: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    relations: List[Tuple[str, str]] = field(default_factory=list)  # (relation, target)
    examples: List[str] = field(default_factory=list)


@dataclass
class Frame:
    """A conceptual frame (schema)."""
    frame_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    roles: List[str] = field(default_factory=list)
    constraints: Dict[str, str] = field(default_factory=dict)
    fillers: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Metaphor:
    """A conceptual metaphor."""
    metaphor_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""
    target: str = ""
    mappings: Dict[str, str] = field(default_factory=dict)
    entailments: List[str] = field(default_factory=list)
    metaphor_type: MetaphorType = MetaphorType.STRUCTURAL


@dataclass
class Blend:
    """A conceptual blend."""
    blend_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    input_spaces: List[str] = field(default_factory=list)
    generic_space: Dict[str, str] = field(default_factory=dict)
    blended_space: Dict[str, Any] = field(default_factory=dict)
    emergent_properties: List[str] = field(default_factory=list)
    blend_type: BlendType = BlendType.SIMPLE


@dataclass
class Idea:
    """A creative idea."""
    idea_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    source_concepts: List[str] = field(default_factory=list)
    novelty: float = 0.0
    usefulness: float = 0.0
    feasibility: float = 0.0
    status: IdeaStatus = IdeaStatus.GENERATED
    novelty_level: NoveltyLevel = NoveltyLevel.ROUTINE


@dataclass
class Constraint:
    """A constraint on creativity."""
    constraint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    is_relaxable: bool = True
    priority: int = 1


@dataclass
class Association:
    """An association between concepts."""
    source: str = ""
    target: str = ""
    strength: float = 0.0
    relation: str = ""


# =============================================================================
# CONCEPT SPACE
# =============================================================================

class ConceptSpace:
    """A space of concepts."""

    def __init__(self, name: str = "default"):
        self._name = name
        self._concepts: Dict[str, Concept] = {}
        self._associations: List[Association] = []

    @property
    def name(self) -> str:
        return self._name

    def add(
        self,
        name: str,
        domain: str = "",
        attributes: Optional[Dict[str, Any]] = None,
        relations: Optional[List[Tuple[str, str]]] = None
    ) -> Concept:
        """Add a concept."""
        concept = Concept(
            name=name,
            domain=domain,
            attributes=attributes or {},
            relations=relations or []
        )
        self._concepts[name] = concept
        return concept

    def get(self, name: str) -> Optional[Concept]:
        """Get a concept."""
        return self._concepts.get(name)

    def all_concepts(self) -> List[Concept]:
        """Get all concepts."""
        return list(self._concepts.values())

    def associate(
        self,
        source: str,
        target: str,
        strength: float = 1.0,
        relation: str = ""
    ) -> None:
        """Create an association."""
        self._associations.append(Association(
            source=source,
            target=target,
            strength=strength,
            relation=relation
        ))

    def get_associations(self, concept: str) -> List[Association]:
        """Get associations for a concept."""
        return [a for a in self._associations if a.source == concept or a.target == concept]

    def find_similar(self, concept: Concept, n: int = 5) -> List[Concept]:
        """Find similar concepts."""
        similarities = []

        for c in self._concepts.values():
            if c.concept_id == concept.concept_id:
                continue

            # Attribute similarity
            common = set(concept.attributes.keys()) & set(c.attributes.keys())
            sim = len(common) / max(len(concept.attributes), len(c.attributes), 1)

            # Domain bonus
            if c.domain == concept.domain:
                sim += 0.2

            similarities.append((c, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return [c for c, _ in similarities[:n]]


# =============================================================================
# DIVERGENT THINKER
# =============================================================================

class DivergentThinker:
    """Generate many ideas through divergent thinking."""

    def __init__(self, concept_space: ConceptSpace):
        self._space = concept_space

    def brainstorm(
        self,
        seed: str,
        n_ideas: int = 10
    ) -> List[Idea]:
        """Generate ideas from a seed concept."""
        ideas = []
        seed_concept = self._space.get(seed)

        if not seed_concept:
            # Create placeholder
            seed_concept = Concept(name=seed)

        # 1. Attribute modification
        for attr, val in seed_concept.attributes.items():
            for modifier in ["bigger", "smaller", "faster", "slower", "inverted"]:
                idea = Idea(
                    description=f"{seed} with {modifier} {attr}",
                    source_concepts=[seed],
                    novelty=0.3
                )
                ideas.append(idea)
                if len(ideas) >= n_ideas:
                    break
            if len(ideas) >= n_ideas:
                break

        # 2. Combination with other concepts
        similar = self._space.find_similar(seed_concept, 5)
        for other in similar:
            idea = Idea(
                description=f"{seed} combined with {other.name}",
                source_concepts=[seed, other.name],
                novelty=0.5
            )
            ideas.append(idea)
            if len(ideas) >= n_ideas:
                break

        # 3. Association traversal
        associations = self._space.get_associations(seed)
        for assoc in associations:
            target = assoc.target if assoc.source == seed else assoc.source
            idea = Idea(
                description=f"{seed} applied to {target}",
                source_concepts=[seed, target],
                novelty=0.4
            )
            ideas.append(idea)
            if len(ideas) >= n_ideas:
                break

        return ideas[:n_ideas]

    def random_combinations(
        self,
        n_ideas: int = 5
    ) -> List[Idea]:
        """Generate random combinations."""
        ideas = []
        concepts = self._space.all_concepts()

        if len(concepts) < 2:
            return []

        for _ in range(n_ideas):
            c1, c2 = random.sample(concepts, 2)
            idea = Idea(
                description=f"{c1.name} + {c2.name}",
                source_concepts=[c1.name, c2.name],
                novelty=0.6
            )
            ideas.append(idea)

        return ideas


# =============================================================================
# CONCEPT BLENDER
# =============================================================================

class ConceptBlender:
    """Blend concepts using conceptual integration theory."""

    def __init__(self, concept_space: ConceptSpace):
        self._space = concept_space
        self._blends: Dict[str, Blend] = {}

    def blend(
        self,
        concept1: str,
        concept2: str,
        blend_type: BlendType = BlendType.DOUBLE_SCOPE
    ) -> Blend:
        """Create a conceptual blend."""
        c1 = self._space.get(concept1)
        c2 = self._space.get(concept2)

        if not c1 or not c2:
            return Blend(name=f"{concept1}+{concept2}")

        # Find generic space (common structure)
        generic = {}
        for attr in c1.attributes:
            if attr in c2.attributes:
                generic[attr] = "shared"

        # Create blended space
        blended = {}
        blended.update({f"{concept1}_{k}": v for k, v in c1.attributes.items()})
        blended.update({f"{concept2}_{k}": v for k, v in c2.attributes.items()})

        # Find emergent properties
        emergent = []
        for r1 in c1.relations:
            for r2 in c2.relations:
                if r1[0] == r2[0]:  # Same relation type
                    emergent.append(f"Shared {r1[0]} structure")

        blend = Blend(
            name=f"{concept1}_{concept2}_blend",
            input_spaces=[concept1, concept2],
            generic_space=generic,
            blended_space=blended,
            emergent_properties=emergent,
            blend_type=blend_type
        )

        self._blends[blend.blend_id] = blend
        return blend

    def get_blend(self, blend_id: str) -> Optional[Blend]:
        """Get a blend."""
        return self._blends.get(blend_id)

    def all_blends(self) -> List[Blend]:
        """Get all blends."""
        return list(self._blends.values())


# =============================================================================
# METAPHOR GENERATOR
# =============================================================================

class MetaphorGenerator:
    """Generate and process metaphors."""

    def __init__(self, concept_space: ConceptSpace):
        self._space = concept_space
        self._metaphors: Dict[str, Metaphor] = {}

    def generate(
        self,
        source: str,
        target: str,
        metaphor_type: MetaphorType = MetaphorType.STRUCTURAL
    ) -> Metaphor:
        """Generate a metaphor."""
        s_concept = self._space.get(source)
        t_concept = self._space.get(target)

        mappings = {}
        if s_concept and t_concept:
            # Map attributes
            s_attrs = list(s_concept.attributes.keys())
            t_attrs = list(t_concept.attributes.keys())

            for i, s_attr in enumerate(s_attrs):
                if i < len(t_attrs):
                    mappings[s_attr] = t_attrs[i]

        # Generate entailments
        entailments = [
            f"{target} is {source}",
            f"{target} has qualities of {source}"
        ]

        metaphor = Metaphor(
            source=source,
            target=target,
            mappings=mappings,
            entailments=entailments,
            metaphor_type=metaphor_type
        )

        self._metaphors[metaphor.metaphor_id] = metaphor
        return metaphor

    def apply_metaphor(
        self,
        metaphor: Metaphor,
        statement: str
    ) -> str:
        """Apply metaphor mappings to a statement."""
        result = statement
        for source_term, target_term in metaphor.mappings.items():
            result = result.replace(source_term, f"{target_term}(from:{source_term})")
        return result

    def get_metaphor(self, metaphor_id: str) -> Optional[Metaphor]:
        """Get a metaphor."""
        return self._metaphors.get(metaphor_id)

    def all_metaphors(self) -> List[Metaphor]:
        """Get all metaphors."""
        return list(self._metaphors.values())


# =============================================================================
# CONSTRAINT RELAXER
# =============================================================================

class ConstraintRelaxer:
    """Relax constraints to enable creativity."""

    def __init__(self):
        self._constraints: Dict[str, Constraint] = {}

    def add(
        self,
        name: str,
        description: str = "",
        is_relaxable: bool = True,
        priority: int = 1
    ) -> Constraint:
        """Add a constraint."""
        constraint = Constraint(
            name=name,
            description=description,
            is_relaxable=is_relaxable,
            priority=priority
        )
        self._constraints[name] = constraint
        return constraint

    def get(self, name: str) -> Optional[Constraint]:
        """Get a constraint."""
        return self._constraints.get(name)

    def relax(self, name: str) -> bool:
        """Relax a constraint."""
        constraint = self._constraints.get(name)
        if constraint and constraint.is_relaxable:
            del self._constraints[name]
            return True
        return False

    def relaxable_constraints(self) -> List[Constraint]:
        """Get relaxable constraints."""
        return [c for c in self._constraints.values() if c.is_relaxable]

    def relax_lowest_priority(self) -> Optional[Constraint]:
        """Relax the lowest priority constraint."""
        relaxable = self.relaxable_constraints()
        if not relaxable:
            return None

        lowest = min(relaxable, key=lambda c: c.priority)
        self.relax(lowest.name)
        return lowest


# =============================================================================
# IDEA EVALUATOR
# =============================================================================

class IdeaEvaluator:
    """Evaluate creative ideas."""

    def evaluate(
        self,
        idea: Idea,
        criteria: Optional[Dict[str, float]] = None
    ) -> Idea:
        """Evaluate an idea."""
        if criteria is None:
            criteria = {"novelty": 0.4, "usefulness": 0.4, "feasibility": 0.2}

        # Simple heuristic evaluation
        idea.novelty = random.uniform(0.3, 1.0)
        idea.usefulness = random.uniform(0.3, 1.0)
        idea.feasibility = random.uniform(0.3, 1.0)

        idea.status = IdeaStatus.EVALUATED

        # Determine novelty level
        if idea.novelty > 0.9:
            idea.novelty_level = NoveltyLevel.BREAKTHROUGH
        elif idea.novelty > 0.7:
            idea.novelty_level = NoveltyLevel.ORIGINAL
        elif idea.novelty > 0.4:
            idea.novelty_level = NoveltyLevel.ADAPTIVE
        else:
            idea.novelty_level = NoveltyLevel.ROUTINE

        return idea

    def score(self, idea: Idea) -> float:
        """Calculate overall score."""
        return 0.4 * idea.novelty + 0.4 * idea.usefulness + 0.2 * idea.feasibility

    def rank(self, ideas: List[Idea]) -> List[Idea]:
        """Rank ideas by score."""
        return sorted(ideas, key=lambda i: self.score(i), reverse=True)


# =============================================================================
# CREATIVITY ENGINE
# =============================================================================

class CreativityEngine:
    """
    Creativity Engine for BAEL.

    Advanced creative reasoning and generation.
    """

    def __init__(self):
        self._concept_space = ConceptSpace()
        self._divergent = DivergentThinker(self._concept_space)
        self._blender = ConceptBlender(self._concept_space)
        self._metaphor_gen = MetaphorGenerator(self._concept_space)
        self._constraint_relaxer = ConstraintRelaxer()
        self._evaluator = IdeaEvaluator()
        self._ideas: Dict[str, Idea] = {}

    # -------------------------------------------------------------------------
    # CONCEPTS
    # -------------------------------------------------------------------------

    def add_concept(
        self,
        name: str,
        domain: str = "",
        attributes: Optional[Dict[str, Any]] = None,
        relations: Optional[List[Tuple[str, str]]] = None
    ) -> Concept:
        """Add a concept."""
        return self._concept_space.add(name, domain, attributes, relations)

    def get_concept(self, name: str) -> Optional[Concept]:
        """Get a concept."""
        return self._concept_space.get(name)

    def associate(
        self,
        source: str,
        target: str,
        strength: float = 1.0,
        relation: str = ""
    ) -> None:
        """Create an association."""
        self._concept_space.associate(source, target, strength, relation)

    # -------------------------------------------------------------------------
    # DIVERGENT THINKING
    # -------------------------------------------------------------------------

    def brainstorm(
        self,
        seed: str,
        n_ideas: int = 10
    ) -> List[Idea]:
        """Brainstorm ideas from a seed."""
        ideas = self._divergent.brainstorm(seed, n_ideas)
        for idea in ideas:
            self._ideas[idea.idea_id] = idea
        return ideas

    def random_combinations(self, n_ideas: int = 5) -> List[Idea]:
        """Generate random combinations."""
        ideas = self._divergent.random_combinations(n_ideas)
        for idea in ideas:
            self._ideas[idea.idea_id] = idea
        return ideas

    # -------------------------------------------------------------------------
    # CONCEPT BLENDING
    # -------------------------------------------------------------------------

    def blend_concepts(
        self,
        concept1: str,
        concept2: str,
        blend_type: BlendType = BlendType.DOUBLE_SCOPE
    ) -> Blend:
        """Blend two concepts."""
        return self._blender.blend(concept1, concept2, blend_type)

    def get_blend(self, blend_id: str) -> Optional[Blend]:
        """Get a blend."""
        return self._blender.get_blend(blend_id)

    def all_blends(self) -> List[Blend]:
        """Get all blends."""
        return self._blender.all_blends()

    # -------------------------------------------------------------------------
    # METAPHORS
    # -------------------------------------------------------------------------

    def create_metaphor(
        self,
        source: str,
        target: str,
        metaphor_type: MetaphorType = MetaphorType.STRUCTURAL
    ) -> Metaphor:
        """Create a metaphor."""
        return self._metaphor_gen.generate(source, target, metaphor_type)

    def apply_metaphor(self, metaphor: Metaphor, statement: str) -> str:
        """Apply metaphor to statement."""
        return self._metaphor_gen.apply_metaphor(metaphor, statement)

    def all_metaphors(self) -> List[Metaphor]:
        """Get all metaphors."""
        return self._metaphor_gen.all_metaphors()

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    def add_constraint(
        self,
        name: str,
        description: str = "",
        is_relaxable: bool = True,
        priority: int = 1
    ) -> Constraint:
        """Add a constraint."""
        return self._constraint_relaxer.add(name, description, is_relaxable, priority)

    def relax_constraint(self, name: str) -> bool:
        """Relax a constraint."""
        return self._constraint_relaxer.relax(name)

    def relax_lowest_priority(self) -> Optional[Constraint]:
        """Relax lowest priority constraint."""
        return self._constraint_relaxer.relax_lowest_priority()

    # -------------------------------------------------------------------------
    # IDEA EVALUATION
    # -------------------------------------------------------------------------

    def evaluate_idea(self, idea: Idea) -> Idea:
        """Evaluate an idea."""
        return self._evaluator.evaluate(idea)

    def rank_ideas(self, ideas: List[Idea]) -> List[Idea]:
        """Rank ideas."""
        return self._evaluator.rank(ideas)

    def score_idea(self, idea: Idea) -> float:
        """Score an idea."""
        return self._evaluator.score(idea)

    # -------------------------------------------------------------------------
    # IDEAS
    # -------------------------------------------------------------------------

    def get_idea(self, idea_id: str) -> Optional[Idea]:
        """Get an idea."""
        return self._ideas.get(idea_id)

    def all_ideas(self) -> List[Idea]:
        """Get all ideas."""
        return list(self._ideas.values())

    def top_ideas(self, n: int = 5) -> List[Idea]:
        """Get top n ideas."""
        evaluated = [i for i in self._ideas.values() if i.status == IdeaStatus.EVALUATED]
        return self.rank_ideas(evaluated)[:n]

    # -------------------------------------------------------------------------
    # CREATIVE PROCESS
    # -------------------------------------------------------------------------

    def creative_session(
        self,
        seed: str,
        n_ideas: int = 20,
        n_selected: int = 5
    ) -> List[Idea]:
        """Run a creative session."""
        # 1. Brainstorm
        ideas = self.brainstorm(seed, n_ideas // 2)

        # 2. Random combinations
        ideas.extend(self.random_combinations(n_ideas // 2))

        # 3. Evaluate all
        for idea in ideas:
            self.evaluate_idea(idea)

        # 4. Select top
        selected = self.rank_ideas(ideas)[:n_selected]

        for idea in selected:
            idea.status = IdeaStatus.SELECTED

        return selected


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Creativity Engine."""
    print("=" * 70)
    print("BAEL - CREATIVITY ENGINE DEMO")
    print("Advanced Creative Reasoning and Generation")
    print("=" * 70)
    print()

    engine = CreativityEngine()

    # 1. Add Concepts
    print("1. ADD CONCEPTS:")
    print("-" * 40)

    engine.add_concept(
        "bird",
        domain="animals",
        attributes={"wings": True, "flies": True, "feathers": True},
        relations=[("can", "fly"), ("has", "wings")]
    )
    engine.add_concept(
        "fish",
        domain="animals",
        attributes={"fins": True, "swims": True, "scales": True},
        relations=[("can", "swim"), ("has", "fins")]
    )
    engine.add_concept(
        "airplane",
        domain="vehicles",
        attributes={"wings": True, "flies": True, "engine": True},
        relations=[("can", "fly"), ("has", "wings")]
    )
    engine.add_concept(
        "submarine",
        domain="vehicles",
        attributes={"hull": True, "dives": True, "engine": True},
        relations=[("can", "dive"), ("has", "hull")]
    )

    engine.associate("bird", "airplane", 0.8, "similar_function")
    engine.associate("fish", "submarine", 0.7, "similar_function")

    print("   Added: bird, fish, airplane, submarine")
    print("   Associations created")
    print()

    # 2. Brainstorm
    print("2. BRAINSTORM:")
    print("-" * 40)

    ideas = engine.brainstorm("bird", n_ideas=5)
    for idea in ideas:
        print(f"   - {idea.description}")
    print()

    # 3. Concept Blending
    print("3. CONCEPT BLENDING:")
    print("-" * 40)

    blend = engine.blend_concepts("bird", "fish")
    print(f"   Blend: {blend.name}")
    print(f"   Generic space: {blend.generic_space}")
    print(f"   Emergent: {blend.emergent_properties}")

    # Flying fish!
    blend2 = engine.blend_concepts("airplane", "submarine")
    print(f"\n   Blend: {blend2.name}")
    print(f"   Type: {blend2.blend_type.value}")
    print()

    # 4. Metaphor Generation
    print("4. METAPHOR GENERATION:")
    print("-" * 40)

    metaphor = engine.create_metaphor("bird", "airplane")
    print(f"   '{metaphor.target}' is '{metaphor.source}'")
    print(f"   Mappings: {metaphor.mappings}")
    print(f"   Entailments: {metaphor.entailments}")
    print()

    # 5. Constraint Relaxation
    print("5. CONSTRAINT RELAXATION:")
    print("-" * 40)

    engine.add_constraint("must_be_cheap", "Solution must be low cost", True, 1)
    engine.add_constraint("must_be_fast", "Solution must be quick", True, 2)
    engine.add_constraint("must_be_safe", "Solution must be safe", False, 10)

    relaxed = engine.relax_lowest_priority()
    if relaxed:
        print(f"   Relaxed: {relaxed.name}")

    relaxed = engine.relax_lowest_priority()
    if relaxed:
        print(f"   Relaxed: {relaxed.name}")
    print()

    # 6. Idea Evaluation
    print("6. IDEA EVALUATION:")
    print("-" * 40)

    for idea in ideas:
        engine.evaluate_idea(idea)
        score = engine.score_idea(idea)
        print(f"   {idea.description[:40]}...")
        print(f"      Score: {score:.2f}, Level: {idea.novelty_level.value}")
    print()

    # 7. Rank Ideas
    print("7. RANK IDEAS:")
    print("-" * 40)

    ranked = engine.rank_ideas(ideas)
    for i, idea in enumerate(ranked):
        print(f"   {i+1}. {idea.description[:40]}... ({engine.score_idea(idea):.2f})")
    print()

    # 8. Random Combinations
    print("8. RANDOM COMBINATIONS:")
    print("-" * 40)

    random_ideas = engine.random_combinations(n_ideas=3)
    for idea in random_ideas:
        print(f"   - {idea.description}")
    print()

    # 9. Creative Session
    print("9. CREATIVE SESSION:")
    print("-" * 40)

    engine2 = CreativityEngine()
    engine2.add_concept("robot", attributes={"metal": True, "automated": True})
    engine2.add_concept("garden", attributes={"plants": True, "nature": True})
    engine2.add_concept("teacher", attributes={"educates": True, "human": True})
    engine2.add_concept("art", attributes={"creative": True, "expressive": True})

    selected = engine2.creative_session("robot", n_ideas=10, n_selected=3)
    print("   Top ideas selected:")
    for idea in selected:
        print(f"   - {idea.description} (status: {idea.status.value})")
    print()

    # 10. All Ideas Summary
    print("10. ALL IDEAS SUMMARY:")
    print("-" * 40)

    all_ideas = engine.all_ideas()
    print(f"   Total ideas: {len(all_ideas)}")

    evaluated = [i for i in all_ideas if i.status == IdeaStatus.EVALUATED]
    print(f"   Evaluated: {len(evaluated)}")

    by_level = defaultdict(int)
    for idea in evaluated:
        by_level[idea.novelty_level.value] += 1

    print("   By novelty level:")
    for level, count in by_level.items():
        print(f"      {level}: {count}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Creativity Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
