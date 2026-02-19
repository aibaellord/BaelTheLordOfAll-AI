"""
BAEL Knowledge Graph Engine
============================

Structured knowledge storage and reasoning.
Enables semantic understanding and graph queries.

Components:
- EntityExtractor: Extract entities from text
- RelationMapper: Map relationships between entities
- GraphStore: Store and query knowledge graphs
- SemanticReasoner: Reason over graph structures
- OntologyManager: Manage ontologies and schemas
- QueryEngine: Execute graph queries
"""

from .entity_extractor import (Entity, EntityExtractor, EntityType,
                               ExtractionResult)
from .graph_store import GraphEdge, GraphNode, GraphStore, SubGraph
from .ontology_manager import (Ontology, OntologyClass, OntologyManager,
                               OntologyProperty)
from .query_engine import GraphQuery, QueryEngine, QueryResult, QueryType
from .relation_mapper import (Relation, RelationMapper, RelationTriple,
                              RelationType)
from .semantic_reasoner import (Inference, InferenceType, ReasoningResult,
                                SemanticReasoner)

__all__ = [
    # Entity Extraction
    "EntityExtractor",
    "Entity",
    "EntityType",
    "ExtractionResult",
    # Relation Mapping
    "RelationMapper",
    "Relation",
    "RelationType",
    "RelationTriple",
    # Graph Store
    "GraphStore",
    "GraphNode",
    "GraphEdge",
    "SubGraph",
    # Semantic Reasoning
    "SemanticReasoner",
    "Inference",
    "InferenceType",
    "ReasoningResult",
    # Ontology Management
    "OntologyManager",
    "Ontology",
    "OntologyClass",
    "OntologyProperty",
    # Query Engine
    "QueryEngine",
    "GraphQuery",
    "QueryResult",
    "QueryType",
]
