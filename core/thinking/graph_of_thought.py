"""
BAEL - Graph of Thought Reasoning
Non-linear reasoning with cycles, backtracking, and concept interconnection.
More powerful than tree-of-thought for complex interconnected problems.
"""

import asyncio
import logging
import math
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from . import ThinkingConfig, ThinkingMode, ThinkingStep, ThinkingTrace

logger = logging.getLogger("BAEL.Thinking.Graph")


@dataclass
class ConceptNode:
    """A concept node in the reasoning graph."""
    id: str
    concept: str
    description: str
    node_type: str = "concept"  # concept, hypothesis, evidence, conclusion
    activation: float = 0.0  # How active/relevant this node is
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConceptEdge:
    """An edge connecting two concept nodes."""
    source_id: str
    target_id: str
    relation: str  # supports, contradicts, requires, implies, related
    weight: float = 1.0
    bidirectional: bool = False


@dataclass
class GraphConfig:
    """Configuration for graph-of-thought."""
    max_nodes: int = 50
    max_edges_per_node: int = 5
    activation_threshold: float = 0.3
    spreading_factor: float = 0.7
    convergence_threshold: float = 0.01
    max_iterations: int = 10
    enable_cycles: bool = True
    enable_backtracking: bool = True


class GraphOfThought:
    """
    Graph of Thought reasoning engine.

    Unlike tree-based reasoning, this allows:
    - Non-linear connections between ideas
    - Cycles and feedback loops
    - Spreading activation for relevance
    - Concept synthesis from multiple paths
    - Dynamic graph restructuring

    Inspired by semantic networks and neural activation patterns.
    """

    def __init__(self, config: Optional[GraphConfig] = None):
        self.config = config or GraphConfig()
        self._llm = None
        self._nodes: Dict[str, ConceptNode] = {}
        self._edges: List[ConceptEdge] = []
        self._adjacency: Dict[str, List[str]] = defaultdict(list)

    async def _get_llm(self):
        """Lazy load LLM provider."""
        if self._llm is None:
            try:
                from core.llm import get_provider
                self._llm = get_provider()
            except ImportError:
                from .extended_thinking import MockLLM
                self._llm = MockLLM()
        return self._llm

    async def reason(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ThinkingTrace:
        """
        Perform graph-based reasoning on a query.

        Args:
            query: The problem to solve
            context: Additional context

        Returns:
            ThinkingTrace with reasoning process
        """
        # Initialize graph
        self._nodes = {}
        self._edges = []
        self._adjacency = defaultdict(list)

        logger.info("Starting Graph-of-Thought reasoning")

        # Step 1: Extract initial concepts from query
        initial_concepts = await self._extract_concepts(query)
        for concept in initial_concepts:
            self._add_node(concept)

        # Step 2: Generate hypotheses
        hypotheses = await self._generate_hypotheses(query, initial_concepts)
        for hyp in hypotheses:
            self._add_node(hyp)
            # Connect to relevant concepts
            await self._connect_to_relevant(hyp)

        # Step 3: Gather evidence
        evidence_nodes = await self._gather_evidence(query, hypotheses)
        for ev in evidence_nodes:
            self._add_node(ev)
            await self._connect_to_relevant(ev)

        # Step 4: Spreading activation
        await self._spread_activation(query)

        # Step 5: Identify conflicts and resolve
        conflicts = self._find_conflicts()
        if conflicts:
            await self._resolve_conflicts(conflicts)

        # Step 6: Synthesize conclusion
        conclusion = await self._synthesize_conclusion(query)
        self._add_node(conclusion)

        # Step 7: Build trace
        trace = self._build_trace(query, conclusion)

        logger.info(f"Graph reasoning complete: {len(self._nodes)} nodes, {len(self._edges)} edges")

        return trace

    def _add_node(self, node: ConceptNode) -> None:
        """Add a node to the graph."""
        if len(self._nodes) >= self.config.max_nodes:
            # Remove lowest activation node
            min_node = min(self._nodes.values(), key=lambda n: n.activation)
            self._remove_node(min_node.id)

        self._nodes[node.id] = node

    def _remove_node(self, node_id: str) -> None:
        """Remove a node and its edges."""
        if node_id in self._nodes:
            del self._nodes[node_id]

        self._edges = [e for e in self._edges if e.source_id != node_id and e.target_id != node_id]

        if node_id in self._adjacency:
            del self._adjacency[node_id]
        for adj_list in self._adjacency.values():
            if node_id in adj_list:
                adj_list.remove(node_id)

    def _add_edge(self, edge: ConceptEdge) -> None:
        """Add an edge to the graph."""
        source_node = self._nodes.get(edge.source_id)
        if source_node and len(self._adjacency[edge.source_id]) >= self.config.max_edges_per_node:
            return  # Don't add more edges

        self._edges.append(edge)
        self._adjacency[edge.source_id].append(edge.target_id)
        if edge.bidirectional:
            self._adjacency[edge.target_id].append(edge.source_id)

    async def _extract_concepts(self, query: str) -> List[ConceptNode]:
        """Extract key concepts from the query."""
        llm = await self._get_llm()

        prompt = f"""Extract the key concepts from this problem/query.

QUERY: {query}

List 3-5 key concepts, each on a new line:
CONCEPT: [name] - [brief description]"""

        response = await llm.generate(prompt, temperature=0.5)

        concepts = []
        for line in response.split("\n"):
            if "CONCEPT:" in line:
                parts = line.split("CONCEPT:")[-1].strip()
                if " - " in parts:
                    name, desc = parts.split(" - ", 1)
                else:
                    name, desc = parts, parts

                concepts.append(ConceptNode(
                    id=f"concept_{uuid.uuid4().hex[:8]}",
                    concept=name.strip(),
                    description=desc.strip(),
                    node_type="concept",
                    activation=1.0  # Initial concepts start active
                ))

        return concepts if concepts else [ConceptNode(
            id=f"concept_{uuid.uuid4().hex[:8]}",
            concept="main_query",
            description=query[:100],
            node_type="concept",
            activation=1.0
        )]

    async def _generate_hypotheses(
        self,
        query: str,
        concepts: List[ConceptNode]
    ) -> List[ConceptNode]:
        """Generate hypotheses based on concepts."""
        llm = await self._get_llm()

        concept_list = "\n".join(f"- {c.concept}: {c.description}" for c in concepts)

        prompt = f"""Given these concepts related to a problem, generate possible hypotheses or approaches.

PROBLEM: {query}

KEY CONCEPTS:
{concept_list}

Generate 2-3 hypotheses:
HYPOTHESIS: [statement] - [reasoning]"""

        response = await llm.generate(prompt, temperature=0.7)

        hypotheses = []
        for line in response.split("\n"):
            if "HYPOTHESIS:" in line:
                parts = line.split("HYPOTHESIS:")[-1].strip()
                if " - " in parts:
                    stmt, reason = parts.split(" - ", 1)
                else:
                    stmt, reason = parts, ""

                hypotheses.append(ConceptNode(
                    id=f"hyp_{uuid.uuid4().hex[:8]}",
                    concept=stmt.strip()[:100],
                    description=reason.strip(),
                    node_type="hypothesis",
                    activation=0.8
                ))

        return hypotheses

    async def _gather_evidence(
        self,
        query: str,
        hypotheses: List[ConceptNode]
    ) -> List[ConceptNode]:
        """Gather evidence for or against hypotheses."""
        llm = await self._get_llm()

        evidence_nodes = []

        for hyp in hypotheses[:3]:  # Limit for efficiency
            prompt = f"""For this hypothesis, identify supporting or contradicting evidence.

PROBLEM: {query}
HYPOTHESIS: {hyp.concept}

List evidence points:
EVIDENCE [supports/contradicts]: [description]"""

            response = await llm.generate(prompt, temperature=0.5)

            for line in response.split("\n"):
                if "EVIDENCE" in line:
                    if "supports" in line.lower():
                        relation = "supports"
                    elif "contradicts" in line.lower():
                        relation = "contradicts"
                    else:
                        relation = "related"

                    desc = line.split(":")[-1].strip() if ":" in line else line

                    ev = ConceptNode(
                        id=f"ev_{uuid.uuid4().hex[:8]}",
                        concept=f"Evidence for {hyp.concept[:30]}",
                        description=desc,
                        node_type="evidence",
                        activation=0.6
                    )
                    evidence_nodes.append(ev)

                    # Create edge to hypothesis
                    self._add_edge(ConceptEdge(
                        source_id=ev.id,
                        target_id=hyp.id,
                        relation=relation,
                        weight=0.8
                    ))

        return evidence_nodes

    async def _connect_to_relevant(self, node: ConceptNode) -> None:
        """Connect a node to relevant existing nodes."""
        if len(self._nodes) < 2:
            return

        llm = await self._get_llm()

        existing = [f"{n.id}: {n.concept}" for n in self._nodes.values() if n.id != node.id][:10]

        prompt = f"""Which of these existing concepts is most related to the new concept?

NEW: {node.concept} - {node.description}

EXISTING:
{chr(10).join(existing)}

Reply with the ID of the most related concept and the relationship type:
RELATED_TO: [id] - [supports/contradicts/requires/implies/related]"""

        response = await llm.generate(prompt, temperature=0.3)

        if "RELATED_TO:" in response:
            parts = response.split("RELATED_TO:")[-1].strip()
            for existing_id in self._nodes.keys():
                if existing_id in parts:
                    relation = "related"
                    for r in ["supports", "contradicts", "requires", "implies"]:
                        if r in parts.lower():
                            relation = r
                            break

                    self._add_edge(ConceptEdge(
                        source_id=node.id,
                        target_id=existing_id,
                        relation=relation,
                        weight=0.7,
                        bidirectional=True
                    ))
                    break

    async def _spread_activation(self, query: str) -> None:
        """Spread activation through the graph to find relevant paths."""
        # Initialize activation based on query relevance
        for node in self._nodes.values():
            if node.node_type == "concept":
                node.activation = 1.0
            elif node.node_type == "hypothesis":
                node.activation = 0.8

        # Iterative spreading
        for iteration in range(self.config.max_iterations):
            prev_activations = {n.id: n.activation for n in self._nodes.values()}
            max_change = 0

            for node in self._nodes.values():
                # Collect activation from neighbors
                neighbor_activation = 0
                neighbor_count = 0

                for edge in self._edges:
                    if edge.target_id == node.id:
                        source = self._nodes.get(edge.source_id)
                        if source:
                            # Reduce activation for contradicting edges
                            factor = -0.5 if edge.relation == "contradicts" else edge.weight
                            neighbor_activation += source.activation * factor
                            neighbor_count += 1
                    elif edge.bidirectional and edge.source_id == node.id:
                        target = self._nodes.get(edge.target_id)
                        if target:
                            neighbor_activation += target.activation * edge.weight
                            neighbor_count += 1

                if neighbor_count > 0:
                    spread = (neighbor_activation / neighbor_count) * self.config.spreading_factor
                    node.activation = max(0, min(1, node.activation * 0.5 + spread * 0.5))

                change = abs(node.activation - prev_activations[node.id])
                max_change = max(max_change, change)

            if max_change < self.config.convergence_threshold:
                logger.info(f"Activation converged after {iteration + 1} iterations")
                break

    def _find_conflicts(self) -> List[Tuple[str, str]]:
        """Find conflicting nodes in the graph."""
        conflicts = []

        for edge in self._edges:
            if edge.relation == "contradicts":
                source = self._nodes.get(edge.source_id)
                target = self._nodes.get(edge.target_id)

                if source and target:
                    # Both active = conflict
                    if source.activation > self.config.activation_threshold and \
                       target.activation > self.config.activation_threshold:
                        conflicts.append((edge.source_id, edge.target_id))

        return conflicts

    async def _resolve_conflicts(self, conflicts: List[Tuple[str, str]]) -> None:
        """Resolve conflicting nodes by evaluation."""
        llm = await self._get_llm()

        for source_id, target_id in conflicts:
            source = self._nodes.get(source_id)
            target = self._nodes.get(target_id)

            if not source or not target:
                continue

            prompt = f"""Two conflicting ideas need resolution:

IDEA A: {source.concept} - {source.description}
IDEA B: {target.concept} - {target.description}

Which is more likely correct and why? Reply:
WINNER: [A or B]
REASON: [explanation]"""

            response = await llm.generate(prompt, temperature=0.3)

            if "WINNER:" in response:
                winner = "A" if "A" in response.split("WINNER:")[-1][:10] else "B"

                # Reduce activation of loser
                if winner == "A":
                    target.activation *= 0.3
                else:
                    source.activation *= 0.3

    async def _synthesize_conclusion(self, query: str) -> ConceptNode:
        """Synthesize conclusion from high-activation nodes."""
        llm = await self._get_llm()

        # Get most active nodes
        active_nodes = sorted(
            self._nodes.values(),
            key=lambda n: n.activation,
            reverse=True
        )[:7]

        node_summary = "\n".join(
            f"- {n.concept} (type: {n.node_type}, activation: {n.activation:.2f})"
            for n in active_nodes
        )

        prompt = f"""Based on this reasoning graph, synthesize a conclusion.

ORIGINAL PROBLEM: {query}

MOST RELEVANT NODES:
{node_summary}

Provide a clear, well-reasoned conclusion:"""

        conclusion_text = await llm.generate(prompt, temperature=0.4)

        return ConceptNode(
            id=f"conclusion_{uuid.uuid4().hex[:8]}",
            concept="Final Conclusion",
            description=conclusion_text,
            node_type="conclusion",
            activation=1.0,
            confidence=sum(n.activation for n in active_nodes) / len(active_nodes) if active_nodes else 0.5
        )

    def _build_trace(self, query: str, conclusion: ConceptNode) -> ThinkingTrace:
        """Build thinking trace from the graph."""
        trace = ThinkingTrace(
            query=query,
            mode=ThinkingMode.GRAPH
        )

        # Order nodes by type and activation
        type_order = {"concept": 0, "hypothesis": 1, "evidence": 2, "conclusion": 3}
        ordered_nodes = sorted(
            self._nodes.values(),
            key=lambda n: (type_order.get(n.node_type, 4), -n.activation)
        )

        for node in ordered_nodes:
            if node.activation >= self.config.activation_threshold:
                step = ThinkingStep(
                    id=node.id,
                    content=f"[{node.node_type.upper()}] {node.concept}\n{node.description}",
                    step_type=node.node_type,
                    confidence=node.confidence
                )
                trace.steps.append(step)

        trace.final_answer = conclusion.description
        trace.confidence = conclusion.confidence

        return trace

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the reasoning graph."""
        type_counts = defaultdict(int)
        for node in self._nodes.values():
            type_counts[node.node_type] += 1

        relation_counts = defaultdict(int)
        for edge in self._edges:
            relation_counts[edge.relation] += 1

        activations = [n.activation for n in self._nodes.values()]

        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "node_types": dict(type_counts),
            "edge_relations": dict(relation_counts),
            "avg_activation": sum(activations) / len(activations) if activations else 0,
            "active_nodes": sum(1 for a in activations if a >= self.config.activation_threshold)
        }


# Global instance
_graph_thinker: Optional[GraphOfThought] = None


def get_graph_thinker(config: Optional[GraphConfig] = None) -> GraphOfThought:
    """Get or create graph-of-thought instance."""
    global _graph_thinker
    if _graph_thinker is None or config is not None:
        _graph_thinker = GraphOfThought(config)
    return _graph_thinker


async def reason_graph(query: str, **kwargs) -> ThinkingTrace:
    """Convenience function for graph-of-thought reasoning."""
    thinker = get_graph_thinker()
    return await thinker.reason(query, **kwargs)
