"""
⚡ VECTOR SYMBOLIC ARCHITECTURE ⚡
=================================
High-level symbolic reasoning with hyperdimensional vectors.

VSA enables:
- Symbolic computation with distributed representations
- Compositional semantics
- Robust reasoning under noise
- One-shot learning
"""

import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import uuid
import json
import hashlib

from .hyperdimensional_core import (
    HyperdimensionalVector,
    HyperdimensionalSpace,
    HDBinding,
    HDBundling,
    HDPermutation,
    HDSimilarity,
    VectorType,
)


@dataclass
class Symbol:
    """A symbolic concept with HD representation"""
    name: str
    vector: HyperdimensionalVector
    concept_type: str = "atomic"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Relation:
    """A relation between symbols"""
    name: str
    subject: str
    object: str
    vector: HyperdimensionalVector
    confidence: float = 1.0


@dataclass
class CompositeSymbol:
    """
    A composite symbol built from atomic symbols.

    Can represent complex structures like:
    - Frames: {role: filler, ...}
    - Sequences: [item1, item2, ...]
    - Graphs: relations between concepts
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    structure_type: str = "frame"  # frame, sequence, graph
    components: Dict[str, str] = field(default_factory=dict)  # role -> filler
    vector: Optional[HyperdimensionalVector] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SymbolicEncoder:
    """
    Encodes symbolic structures as HD vectors.
    """

    def __init__(self, space: HyperdimensionalSpace):
        self.space = space

    def encode_atom(self, name: str) -> HyperdimensionalVector:
        """Encode atomic symbol"""
        return self.space.get_or_create(name)

    def encode_pair(
        self,
        role: str,
        filler: str
    ) -> HyperdimensionalVector:
        """
        Encode role-filler pair.

        Uses binding: role ⊛ filler
        """
        role_vec = self.encode_atom(role)
        filler_vec = self.encode_atom(filler)
        return HDBinding.bind(role_vec, filler_vec)

    def encode_frame(
        self,
        frame: Dict[str, str]
    ) -> HyperdimensionalVector:
        """
        Encode frame structure.

        Frame = {role1: filler1, role2: filler2, ...}
        Encoded as: (role1 ⊛ filler1) + (role2 ⊛ filler2) + ...
        """
        pairs = []
        for role, filler in frame.items():
            pair_vec = self.encode_pair(role, filler)
            pairs.append(pair_vec)

        if not pairs:
            return HyperdimensionalVector()

        return HDBundling.bundle(pairs)

    def encode_sequence(
        self,
        items: List[str]
    ) -> HyperdimensionalVector:
        """
        Encode sequence with position.

        Uses permutation for position encoding.
        """
        vectors = [self.encode_atom(item) for item in items]
        return HDPermutation.encode_sequence(vectors)

    def encode_relation(
        self,
        relation: str,
        subject: str,
        obj: str
    ) -> HyperdimensionalVector:
        """
        Encode semantic triple.

        (subject, relation, object)
        """
        rel_vec = self.encode_atom(relation)
        subj_vec = self.encode_atom(subject)
        obj_vec = self.encode_atom(obj)

        # Encode as: relation ⊛ (subject ⊛ ρ(object))
        # Position distinguishes subject from object
        obj_shifted = obj_vec.permute(1)
        subj_obj = HDBinding.bind(subj_vec, obj_shifted)
        return HDBinding.bind(rel_vec, subj_obj)

    def encode_graph(
        self,
        triples: List[Tuple[str, str, str]]
    ) -> HyperdimensionalVector:
        """
        Encode knowledge graph as single vector.

        Bundles all relation encodings.
        """
        relation_vecs = []
        for subj, rel, obj in triples:
            vec = self.encode_relation(rel, subj, obj)
            relation_vecs.append(vec)

        if not relation_vecs:
            return HyperdimensionalVector()

        return HDBundling.bundle(relation_vecs)


class SymbolicDecoder:
    """
    Decodes HD vectors back to symbolic structures.
    """

    def __init__(self, space: HyperdimensionalSpace):
        self.space = space

    def decode_atom(
        self,
        vector: HyperdimensionalVector,
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """Decode to most similar atomic symbols"""
        return self.space.fast_query(vector, top_k)

    def decode_filler(
        self,
        frame_vector: HyperdimensionalVector,
        role: str,
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Decode filler for given role.

        Unbind role from frame, query for filler.
        """
        role_vec = self.space.get_or_create(role)
        filler_vec = HDBinding.unbind(frame_vector, role_vec)
        return self.decode_atom(filler_vec, top_k)

    def decode_frame(
        self,
        frame_vector: HyperdimensionalVector,
        roles: List[str]
    ) -> Dict[str, str]:
        """Decode frame given known roles"""
        result = {}
        for role in roles:
            fillers = self.decode_filler(frame_vector, role, top_k=1)
            if fillers:
                result[role] = fillers[0][0]
        return result

    def decode_sequence_item(
        self,
        seq_vector: HyperdimensionalVector,
        position: int,
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """Decode item at specific position"""
        # Create position query
        query = seq_vector.permute(-position)  # Inverse permute
        return self.decode_atom(query, top_k)

    def decode_subject(
        self,
        relation_vector: HyperdimensionalVector,
        relation: str,
        obj: str
    ) -> List[Tuple[str, float]]:
        """Decode subject given relation and object"""
        rel_vec = self.space.get_or_create(relation)
        obj_vec = self.space.get_or_create(obj).permute(1)

        # Unbind relation
        subj_obj = HDBinding.unbind(relation_vector, rel_vec)
        # Unbind object
        subj_vec = HDBinding.unbind(subj_obj, obj_vec)

        return self.decode_atom(subj_vec)


class SymbolicMemory:
    """
    Associative memory for symbolic structures.

    Stores and retrieves frames, sequences, and graphs.
    """

    def __init__(self, dimension: int = 10000):
        self.dimension = dimension
        self.space = HyperdimensionalSpace(dimension)
        self.encoder = SymbolicEncoder(self.space)
        self.decoder = SymbolicDecoder(self.space)

        # Memory stores
        self.frames: Dict[str, CompositeSymbol] = {}
        self.sequences: Dict[str, CompositeSymbol] = {}
        self.relations: List[Relation] = []
        self.graph_vector: Optional[HyperdimensionalVector] = None

    def store_frame(
        self,
        name: str,
        frame: Dict[str, str]
    ) -> CompositeSymbol:
        """Store a frame structure"""
        vector = self.encoder.encode_frame(frame)

        composite = CompositeSymbol(
            name=name,
            structure_type="frame",
            components=frame,
            vector=vector
        )

        self.frames[name] = composite
        self.space.add_concept(name, vector)

        return composite

    def query_frame(
        self,
        query: Dict[str, str],
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """Query for similar frames"""
        query_vec = self.encoder.encode_frame(query)

        results = []
        for name, frame in self.frames.items():
            sim = query_vec.similarity(frame.vector)
            results.append((name, sim))

        results.sort(key=lambda x: -x[1])
        return results[:top_k]

    def complete_frame(
        self,
        partial: Dict[str, str],
        missing_roles: List[str]
    ) -> Dict[str, str]:
        """Complete partial frame by analogy"""
        # Find similar complete frames
        similar = self.query_frame(partial, top_k=3)

        # Get fillers from most similar frame
        result = partial.copy()

        for name, sim in similar:
            frame = self.frames.get(name)
            if frame:
                for role in missing_roles:
                    if role in frame.components and role not in result:
                        result[role] = frame.components[role]

        return result

    def store_sequence(
        self,
        name: str,
        items: List[str]
    ) -> CompositeSymbol:
        """Store a sequence"""
        vector = self.encoder.encode_sequence(items)

        composite = CompositeSymbol(
            name=name,
            structure_type="sequence",
            components={str(i): item for i, item in enumerate(items)},
            vector=vector
        )

        self.sequences[name] = composite
        return composite

    def store_relation(
        self,
        relation: str,
        subject: str,
        obj: str
    ) -> Relation:
        """Store a relation triple"""
        vector = self.encoder.encode_relation(relation, subject, obj)

        rel = Relation(
            name=relation,
            subject=subject,
            object=obj,
            vector=vector
        )

        self.relations.append(rel)

        # Update graph vector
        if self.graph_vector is None:
            self.graph_vector = vector
        else:
            self.graph_vector = HDBundling.bundle([self.graph_vector, vector])

        return rel

    def query_relations(
        self,
        subject: Optional[str] = None,
        relation: Optional[str] = None,
        obj: Optional[str] = None
    ) -> List[Relation]:
        """Query relations matching pattern"""
        results = []

        for rel in self.relations:
            if subject and rel.subject != subject:
                continue
            if relation and rel.name != relation:
                continue
            if obj and rel.object != obj:
                continue
            results.append(rel)

        return results

    def infer_relation(
        self,
        subject: str,
        obj: str
    ) -> List[Tuple[str, float]]:
        """Infer most likely relation between subject and object"""
        subj_vec = self.space.get_or_create(subject)
        obj_vec = self.space.get_or_create(obj).permute(1)

        # What relation binds these?
        bound = HDBinding.bind(subj_vec, obj_vec)

        if self.graph_vector is None:
            return []

        # Unbind from graph to find relation
        rel_vec = HDBinding.unbind(self.graph_vector, bound)

        return self.decoder.decode_atom(rel_vec)


class VectorSymbolicArchitecture:
    """
    Complete Vector Symbolic Architecture system.

    Provides high-level interface for symbolic reasoning
    with hyperdimensional representations.
    """

    def __init__(self, dimension: int = 10000):
        self.dimension = dimension
        self.memory = SymbolicMemory(dimension)
        self.space = self.memory.space
        self.encoder = self.memory.encoder
        self.decoder = self.memory.decoder

    def define_concept(self, name: str) -> HyperdimensionalVector:
        """Define atomic concept"""
        return self.space.get_or_create(name)

    def bind(
        self,
        a: Union[str, HyperdimensionalVector],
        b: Union[str, HyperdimensionalVector]
    ) -> HyperdimensionalVector:
        """Bind two concepts"""
        if isinstance(a, str):
            a = self.define_concept(a)
        if isinstance(b, str):
            b = self.define_concept(b)
        return HDBinding.bind(a, b)

    def bundle(
        self,
        items: List[Union[str, HyperdimensionalVector]]
    ) -> HyperdimensionalVector:
        """Bundle concepts"""
        vectors = [
            self.define_concept(i) if isinstance(i, str) else i
            for i in items
        ]
        return HDBundling.bundle(vectors)

    def query(
        self,
        vector: HyperdimensionalVector,
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """Query for similar concepts"""
        return self.space.fast_query(vector, top_k)

    def analogy(
        self,
        a: str,
        b: str,
        c: str
    ) -> List[Tuple[str, float]]:
        """
        Solve analogy: a is to b as c is to ?

        d = c + (b - a)
        """
        a_vec = self.define_concept(a)
        b_vec = self.define_concept(b)
        c_vec = self.define_concept(c)

        # Compute analogy
        relation = HyperdimensionalVector(
            vector=b_vec.vector - a_vec.vector,
            dimension=self.dimension
        )
        d_vec = HyperdimensionalVector(
            vector=c_vec.vector + relation.vector,
            dimension=self.dimension
        )

        return self.query(d_vec)

    def semantic_similarity(self, a: str, b: str) -> float:
        """Compute semantic similarity between concepts"""
        a_vec = self.define_concept(a)
        b_vec = self.define_concept(b)
        return a_vec.similarity(b_vec)

    def compose(
        self,
        structure: Dict[str, Any]
    ) -> HyperdimensionalVector:
        """
        Compose complex structure.

        Recursively encodes nested structures.
        """
        if isinstance(structure, str):
            return self.define_concept(structure)

        if isinstance(structure, list):
            vectors = [self.compose(item) for item in structure]
            return HDPermutation.encode_sequence(vectors)

        if isinstance(structure, dict):
            pairs = []
            for role, filler in structure.items():
                role_vec = self.define_concept(role)
                filler_vec = self.compose(filler)
                pair = HDBinding.bind(role_vec, filler_vec)
                pairs.append(pair)
            return HDBundling.bundle(pairs)

        # Fallback
        return self.define_concept(str(structure))

    def decompose(
        self,
        vector: HyperdimensionalVector,
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Decompose vector according to schema.

        Schema defines expected structure.
        """
        result = {}

        for role, expected_type in schema.items():
            role_vec = self.define_concept(role)
            filler_vec = HDBinding.unbind(vector, role_vec)

            if expected_type == "atom":
                matches = self.query(filler_vec, 1)
                result[role] = matches[0][0] if matches else None
            elif isinstance(expected_type, list):
                # Sequence expected
                items = []
                for i in range(len(expected_type)):
                    item_vec = filler_vec.permute(-i)
                    matches = self.query(item_vec, 1)
                    items.append(matches[0][0] if matches else None)
                result[role] = items
            elif isinstance(expected_type, dict):
                result[role] = self.decompose(filler_vec, expected_type)

        return result


# Export all
__all__ = [
    'Symbol',
    'Relation',
    'CompositeSymbol',
    'SymbolicEncoder',
    'SymbolicDecoder',
    'SymbolicMemory',
    'VectorSymbolicArchitecture',
]
