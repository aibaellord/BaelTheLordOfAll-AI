"""
BAEL Query Engine
==================

Query execution for knowledge graphs.
Supports graph pattern matching and SPARQL-like queries.

Features:
- Pattern matching queries
- Path queries
- Aggregation queries
- Filter expressions
- Query optimization
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from .graph_store import GraphEdge, GraphNode, GraphStore, SubGraph

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of queries."""
    SELECT = "select"
    CONSTRUCT = "construct"
    ASK = "ask"
    DESCRIBE = "describe"
    INSERT = "insert"
    DELETE = "delete"


class Operator(Enum):
    """Filter operators."""
    EQ = "="
    NE = "!="
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    MATCHES = "matches"
    IN = "in"
    NOT_IN = "not_in"


@dataclass
class Filter:
    """A filter condition."""
    variable: str
    operator: Operator
    value: Any


@dataclass
class Pattern:
    """A triple pattern."""
    subject: str  # Variable (?x) or literal
    predicate: str  # Relation or variable
    object: str  # Variable or literal

    def is_subject_var(self) -> bool:
        return self.subject.startswith("?")

    def is_predicate_var(self) -> bool:
        return self.predicate.startswith("?")

    def is_object_var(self) -> bool:
        return self.object.startswith("?")


@dataclass
class GraphQuery:
    """A graph query."""
    id: str
    query_type: QueryType = QueryType.SELECT

    # SELECT clause
    select_vars: List[str] = field(default_factory=list)

    # WHERE clause
    patterns: List[Pattern] = field(default_factory=list)
    filters: List[Filter] = field(default_factory=list)

    # OPTIONAL patterns
    optional_patterns: List[Pattern] = field(default_factory=list)

    # ORDER BY
    order_by: Optional[str] = None
    order_desc: bool = False

    # LIMIT/OFFSET
    limit: Optional[int] = None
    offset: int = 0

    # Query text
    query_text: str = ""


@dataclass
class QueryResult:
    """Result of a query execution."""
    query_id: str

    # Results
    bindings: List[Dict[str, Any]] = field(default_factory=list)

    # For ASK queries
    answer: Optional[bool] = None

    # For CONSTRUCT queries
    subgraph: Optional[SubGraph] = None

    # Stats
    result_count: int = 0
    execution_time_ms: float = 0.0

    # Metadata
    executed_at: datetime = field(default_factory=datetime.now)


class QueryEngine:
    """
    Query engine for BAEL knowledge graphs.

    Executes graph queries with pattern matching.
    """

    def __init__(self, graph: GraphStore):
        self.graph = graph

        # Query cache
        self._cache: Dict[str, QueryResult] = {}
        self._cache_enabled = True

        # Stats
        self.stats = {
            "queries_executed": 0,
            "cache_hits": 0,
            "patterns_matched": 0,
        }

    def parse(self, query_text: str) -> GraphQuery:
        """
        Parse a query string.

        Args:
            query_text: Query in simplified SPARQL-like syntax

        Returns:
            Parsed query
        """
        query_id = hashlib.md5(query_text.encode()).hexdigest()[:12]

        query = GraphQuery(
            id=query_id,
            query_text=query_text,
        )

        # Determine query type
        text_upper = query_text.strip().upper()
        if text_upper.startswith("SELECT"):
            query.query_type = QueryType.SELECT
        elif text_upper.startswith("ASK"):
            query.query_type = QueryType.ASK
        elif text_upper.startswith("CONSTRUCT"):
            query.query_type = QueryType.CONSTRUCT
        elif text_upper.startswith("DESCRIBE"):
            query.query_type = QueryType.DESCRIBE

        # Parse SELECT variables
        if query.query_type == QueryType.SELECT:
            select_match = re.search(
                r'SELECT\s+((?:\?\w+\s*)+)',
                query_text,
                re.IGNORECASE,
            )
            if select_match:
                vars_str = select_match.group(1)
                query.select_vars = re.findall(r'\?(\w+)', vars_str)

        # Parse WHERE patterns
        where_match = re.search(
            r'WHERE\s*\{([^}]+)\}',
            query_text,
            re.IGNORECASE,
        )
        if where_match:
            patterns_text = where_match.group(1)
            query.patterns = self._parse_patterns(patterns_text)

        # Parse FILTER
        for filter_match in re.finditer(
            r'FILTER\s*\(\s*\?(\w+)\s*(=|!=|<|>|<=|>=)\s*["\']?([^"\')\s]+)["\']?\s*\)',
            query_text,
            re.IGNORECASE,
        ):
            var = filter_match.group(1)
            op_str = filter_match.group(2)
            value = filter_match.group(3)

            op_map = {
                "=": Operator.EQ, "!=": Operator.NE,
                "<": Operator.LT, "<=": Operator.LE,
                ">": Operator.GT, ">=": Operator.GE,
            }

            query.filters.append(Filter(
                variable=var,
                operator=op_map.get(op_str, Operator.EQ),
                value=value,
            ))

        # Parse LIMIT
        limit_match = re.search(r'LIMIT\s+(\d+)', query_text, re.IGNORECASE)
        if limit_match:
            query.limit = int(limit_match.group(1))

        # Parse OFFSET
        offset_match = re.search(r'OFFSET\s+(\d+)', query_text, re.IGNORECASE)
        if offset_match:
            query.offset = int(offset_match.group(1))

        # Parse ORDER BY
        order_match = re.search(
            r'ORDER\s+BY\s+(DESC\s*)?\?(\w+)',
            query_text,
            re.IGNORECASE,
        )
        if order_match:
            query.order_desc = order_match.group(1) is not None
            query.order_by = order_match.group(2)

        return query

    def _parse_patterns(self, patterns_text: str) -> List[Pattern]:
        """Parse triple patterns."""
        patterns = []

        # Simple pattern: ?s relation ?o or ?s ?p ?o
        for match in re.finditer(
            r'(\?\w+|[\w:]+)\s+(\?\w+|[\w:]+)\s+(\?\w+|[\w:]+)\s*\.?',
            patterns_text,
        ):
            patterns.append(Pattern(
                subject=match.group(1),
                predicate=match.group(2),
                object=match.group(3),
            ))

        return patterns

    def execute(self, query: Union[str, GraphQuery]) -> QueryResult:
        """
        Execute a query.

        Args:
            query: Query string or GraphQuery object

        Returns:
            Query result
        """
        import time
        start = time.time()

        if isinstance(query, str):
            query = self.parse(query)

        # Check cache
        cache_key = query.query_text
        if self._cache_enabled and cache_key in self._cache:
            self.stats["cache_hits"] += 1
            return self._cache[cache_key]

        result = QueryResult(query_id=query.id)

        # Execute based on query type
        if query.query_type == QueryType.SELECT:
            result.bindings = self._execute_select(query)
            result.result_count = len(result.bindings)

        elif query.query_type == QueryType.ASK:
            result.answer = self._execute_ask(query)

        elif query.query_type == QueryType.CONSTRUCT:
            result.subgraph = self._execute_construct(query)
            result.result_count = result.subgraph.node_count() if result.subgraph else 0

        result.execution_time_ms = (time.time() - start) * 1000

        # Cache result
        if self._cache_enabled:
            self._cache[cache_key] = result

        self.stats["queries_executed"] += 1

        return result

    def _execute_select(self, query: GraphQuery) -> List[Dict[str, Any]]:
        """Execute SELECT query."""
        # Start with all possible bindings
        bindings = [{}]

        # Match each pattern
        for pattern in query.patterns:
            new_bindings = []

            for binding in bindings:
                matches = self._match_pattern(pattern, binding)
                new_bindings.extend(matches)
                self.stats["patterns_matched"] += len(matches)

            bindings = new_bindings

            if not bindings:
                break

        # Apply filters
        bindings = self._apply_filters(bindings, query.filters)

        # Project to selected variables
        if query.select_vars:
            bindings = [
                {var: b.get(var) for var in query.select_vars if var in b}
                for b in bindings
            ]

        # Order
        if query.order_by and bindings:
            bindings.sort(
                key=lambda b: b.get(query.order_by, ""),
                reverse=query.order_desc,
            )

        # Offset and limit
        if query.offset:
            bindings = bindings[query.offset:]
        if query.limit:
            bindings = bindings[:query.limit]

        return bindings

    def _match_pattern(
        self,
        pattern: Pattern,
        binding: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Match a pattern against the graph."""
        matches = []

        for edge in self.graph._edges.values():
            source = self.graph.get_node(edge.source_id)
            target = self.graph.get_node(edge.target_id)

            if not source or not target:
                continue

            new_binding = dict(binding)
            match = True

            # Match subject
            if pattern.is_subject_var():
                var = pattern.subject[1:]
                if var in binding:
                    if binding[var] != source.label:
                        match = False
                else:
                    new_binding[var] = source.label
                    new_binding[f"{var}_id"] = source.id
                    new_binding[f"{var}_type"] = source.node_type
            else:
                if pattern.subject != source.label:
                    match = False

            # Match predicate
            if match and pattern.is_predicate_var():
                var = pattern.predicate[1:]
                if var in binding:
                    if binding[var] != edge.label:
                        match = False
                else:
                    new_binding[var] = edge.label
            elif match:
                if pattern.predicate != edge.label:
                    match = False

            # Match object
            if match and pattern.is_object_var():
                var = pattern.object[1:]
                if var in binding:
                    if binding[var] != target.label:
                        match = False
                else:
                    new_binding[var] = target.label
                    new_binding[f"{var}_id"] = target.id
                    new_binding[f"{var}_type"] = target.node_type
            elif match:
                if pattern.object != target.label:
                    match = False

            if match:
                matches.append(new_binding)

        return matches

    def _apply_filters(
        self,
        bindings: List[Dict[str, Any]],
        filters: List[Filter],
    ) -> List[Dict[str, Any]]:
        """Apply filters to bindings."""
        for f in filters:
            bindings = [
                b for b in bindings
                if self._evaluate_filter(f, b)
            ]
        return bindings

    def _evaluate_filter(
        self,
        f: Filter,
        binding: Dict[str, Any],
    ) -> bool:
        """Evaluate a filter condition."""
        if f.variable not in binding:
            return False

        value = binding[f.variable]
        filter_value = f.value

        # Type coercion
        if isinstance(value, (int, float)):
            try:
                filter_value = type(value)(filter_value)
            except (ValueError, TypeError):
                pass

        if f.operator == Operator.EQ:
            return value == filter_value
        elif f.operator == Operator.NE:
            return value != filter_value
        elif f.operator == Operator.LT:
            return value < filter_value
        elif f.operator == Operator.LE:
            return value <= filter_value
        elif f.operator == Operator.GT:
            return value > filter_value
        elif f.operator == Operator.GE:
            return value >= filter_value
        elif f.operator == Operator.CONTAINS:
            return str(filter_value) in str(value)
        elif f.operator == Operator.STARTS_WITH:
            return str(value).startswith(str(filter_value))
        elif f.operator == Operator.ENDS_WITH:
            return str(value).endswith(str(filter_value))
        elif f.operator == Operator.IN:
            return value in filter_value
        elif f.operator == Operator.NOT_IN:
            return value not in filter_value

        return False

    def _execute_ask(self, query: GraphQuery) -> bool:
        """Execute ASK query."""
        bindings = self._execute_select(query)
        return len(bindings) > 0

    def _execute_construct(self, query: GraphQuery) -> SubGraph:
        """Execute CONSTRUCT query."""
        bindings = self._execute_select(query)

        nodes = []
        edges = []
        seen_nodes = set()

        for binding in bindings:
            # Extract node IDs from bindings
            for key, value in binding.items():
                if key.endswith("_id") and value not in seen_nodes:
                    node = self.graph.get_node(value)
                    if node:
                        nodes.append(node)
                        seen_nodes.add(value)

        return SubGraph(nodes=nodes, edges=edges)

    def query_by_entity(
        self,
        entity_label: str,
        relation: Optional[str] = None,
        depth: int = 1,
    ) -> QueryResult:
        """
        Query by entity.

        Args:
            entity_label: Entity to start from
            relation: Optional relation filter
            depth: Traversal depth

        Returns:
            Query result
        """
        # Find starting node
        nodes = self.graph.find_nodes(label=entity_label)

        if not nodes:
            return QueryResult(query_id="entity_query")

        start_node = nodes[0]

        # Traverse
        def edge_filter(e):
            return relation is None or e.label == relation

        subgraph = self.graph.traverse_bfs(
            start_node.id,
            max_depth=depth,
            edge_filter=edge_filter,
        )

        # Convert to bindings
        bindings = []
        for node in subgraph.nodes:
            bindings.append({
                "node": node.label,
                "type": node.node_type,
            })

        result = QueryResult(
            query_id="entity_query",
            bindings=bindings,
            subgraph=subgraph,
            result_count=len(bindings),
        )

        return result

    def clear_cache(self) -> None:
        """Clear query cache."""
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            **self.stats,
            "cache_size": len(self._cache),
        }


def demo():
    """Demonstrate query engine."""
    print("=" * 60)
    print("BAEL Query Engine Demo")
    print("=" * 60)

    # Create graph
    store = GraphStore()

    # Add data
    python = store.add_node("Python", "language")
    tensorflow = store.add_node("TensorFlow", "framework")
    pytorch = store.add_node("PyTorch", "framework")
    google = store.add_node("Google", "organization")
    meta = store.add_node("Meta", "organization")

    store.add_edge(tensorflow.id, python.id, "built_with")
    store.add_edge(pytorch.id, python.id, "built_with")
    store.add_edge(google.id, tensorflow.id, "created")
    store.add_edge(meta.id, pytorch.id, "created")

    # Create query engine
    engine = QueryEngine(store)

    # Simple query
    print("\nQuery 1: Find all frameworks")
    query1 = """
    SELECT ?framework ?lang
    WHERE {
        ?framework built_with ?lang .
    }
    """
    result1 = engine.execute(query1)
    print(f"  Results: {result1.result_count}")
    for b in result1.bindings:
        print(f"    {b}")

    # Query with pattern
    print("\nQuery 2: What did Google create?")
    query2 = """
    SELECT ?product
    WHERE {
        Google created ?product .
    }
    """
    result2 = engine.execute(query2)
    print(f"  Results: {result2.result_count}")
    for b in result2.bindings:
        print(f"    {b}")

    # ASK query
    print("\nQuery 3: Did Meta create something?")
    query3 = """
    ASK
    WHERE {
        Meta created ?x .
    }
    """
    result3 = engine.execute(query3)
    print(f"  Answer: {result3.answer}")

    # Query by entity
    print("\nQuery 4: Entity query from Python")
    result4 = engine.query_by_entity("Python", depth=2)
    print(f"  Results: {result4.result_count}")
    for b in result4.bindings:
        print(f"    {b}")

    print(f"\nStats: {engine.get_stats()}")


if __name__ == "__main__":
    demo()
