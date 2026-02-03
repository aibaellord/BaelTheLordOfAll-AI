"""
BAEL - Tree of Thought Reasoning
Explores multiple reasoning branches in parallel, evaluating and pruning
to find optimal solution paths.
"""

import asyncio
import heapq
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from . import ThinkingConfig, ThinkingMode, ThinkingStep, ThinkingTrace

logger = logging.getLogger("BAEL.Thinking.Tree")


class NodeStatus(Enum):
    """Status of a thought node."""
    PENDING = "pending"
    EXPLORING = "exploring"
    EVALUATED = "evaluated"
    PRUNED = "pruned"
    PROMISING = "promising"
    SOLUTION = "solution"


@dataclass
class ThoughtNode:
    """A node in the tree of thoughts."""
    id: str
    content: str
    depth: int
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    score: float = 0.0
    status: NodeStatus = NodeStatus.PENDING
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        """For priority queue ordering (higher score = higher priority)."""
        return self.score > other.score


@dataclass
class TreeConfig:
    """Configuration for tree-of-thought."""
    max_depth: int = 5
    branch_factor: int = 3
    beam_width: int = 3  # Keep top-k nodes at each level
    min_score_threshold: float = 0.3
    exploration_temperature: float = 0.8
    evaluation_samples: int = 3
    parallel_branches: bool = True


class TreeOfThought:
    """
    Tree of Thought reasoning engine.

    Explores multiple reasoning paths simultaneously, using evaluation
    to prune unpromising branches and focus on high-potential solutions.

    Key features:
    - Parallel branch exploration
    - Beam search for efficiency
    - Self-evaluation scoring
    - Backtracking when stuck
    - Solution synthesis from multiple paths
    """

    def __init__(self, config: Optional[TreeConfig] = None):
        self.config = config or TreeConfig()
        self._llm = None
        self._nodes: Dict[str, ThoughtNode] = {}
        self._root_id: Optional[str] = None

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

    async def explore(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ThinkingTrace:
        """
        Explore the tree of thoughts for a query.

        Args:
            query: The problem to solve
            context: Additional context

        Returns:
            ThinkingTrace with the best solution path
        """
        # Initialize tree
        self._nodes = {}
        root = ThoughtNode(
            id=f"root_{uuid.uuid4().hex[:8]}",
            content=query,
            depth=0,
            status=NodeStatus.EXPLORING
        )
        self._nodes[root.id] = root
        self._root_id = root.id

        logger.info(f"Starting Tree-of-Thought exploration (depth={self.config.max_depth}, branches={self.config.branch_factor})")

        # Priority queue for beam search
        frontier: List[ThoughtNode] = [root]
        solutions: List[ThoughtNode] = []

        while frontier and len(solutions) < self.config.beam_width:
            # Get best node to expand
            current = heapq.heappop(frontier)

            if current.depth >= self.config.max_depth:
                # Reached max depth, evaluate as potential solution
                current.status = NodeStatus.SOLUTION
                solutions.append(current)
                continue

            # Generate branches
            branches = await self._generate_branches(current, query)

            # Evaluate branches
            if self.config.parallel_branches:
                scored_branches = await asyncio.gather(*[
                    self._evaluate_branch(b, query) for b in branches
                ])
            else:
                scored_branches = []
                for b in branches:
                    scored = await self._evaluate_branch(b, query)
                    scored_branches.append(scored)

            # Prune and add promising branches
            for node in scored_branches:
                if node.score >= self.config.min_score_threshold:
                    node.status = NodeStatus.PROMISING
                    self._nodes[node.id] = node
                    current.children_ids.append(node.id)
                    heapq.heappush(frontier, node)
                else:
                    node.status = NodeStatus.PRUNED
                    self._nodes[node.id] = node

            current.status = NodeStatus.EVALUATED

            # Keep only beam_width best nodes
            if len(frontier) > self.config.beam_width * 2:
                frontier = heapq.nsmallest(self.config.beam_width, frontier)
                heapq.heapify(frontier)

        # Build trace from best solution path
        trace = await self._build_trace(query, solutions)

        logger.info(f"Tree exploration complete: {len(self._nodes)} nodes, {len(solutions)} solutions")

        return trace

    async def _generate_branches(
        self,
        node: ThoughtNode,
        original_query: str
    ) -> List[ThoughtNode]:
        """Generate child branches from a node."""
        llm = await self._get_llm()

        # Build context from path to root
        path_context = self._get_path_to_root(node)

        prompt = f"""You are exploring different reasoning paths to solve a problem.

ORIGINAL PROBLEM: {original_query}

CURRENT REASONING PATH:
{path_context}

Generate {self.config.branch_factor} different possible next steps in the reasoning.
Each should explore a distinct approach or perspective.

Format each as:
BRANCH 1: [Your first reasoning approach]
BRANCH 2: [Your second reasoning approach]
BRANCH 3: [Your third reasoning approach]

Be creative and explore diverse possibilities."""

        response = await llm.generate(prompt, temperature=self.config.exploration_temperature)

        # Parse branches
        branches = []
        for i in range(1, self.config.branch_factor + 1):
            marker = f"BRANCH {i}:"
            if marker in response:
                start = response.find(marker) + len(marker)
                end = response.find(f"BRANCH {i+1}:") if i < self.config.branch_factor else len(response)
                content = response[start:end].strip()

                branch = ThoughtNode(
                    id=f"node_{uuid.uuid4().hex[:8]}",
                    content=content,
                    depth=node.depth + 1,
                    parent_id=node.id
                )
                branches.append(branch)

        # Fallback if parsing failed
        if not branches:
            branches.append(ThoughtNode(
                id=f"node_{uuid.uuid4().hex[:8]}",
                content=response[:500],
                depth=node.depth + 1,
                parent_id=node.id
            ))

        return branches

    async def _evaluate_branch(
        self,
        node: ThoughtNode,
        original_query: str
    ) -> ThoughtNode:
        """Evaluate a branch's promise for solving the problem."""
        llm = await self._get_llm()

        # Get path context
        parent = self._nodes.get(node.parent_id) if node.parent_id else None
        parent_content = parent.content if parent else "Start"

        prompt = f"""Evaluate how promising this reasoning step is for solving the problem.

ORIGINAL PROBLEM: {original_query}

PREVIOUS STEP: {parent_content[:300]}

CURRENT REASONING: {node.content}

Evaluate on these criteria (0-10 each):
1. RELEVANCE: How relevant is this to solving the problem?
2. PROGRESS: Does this make meaningful progress toward a solution?
3. SOUNDNESS: Is the reasoning logically sound?
4. NOVELTY: Does this explore a useful new angle?
5. COMPLETENESS: How close is this to a complete solution?

Provide scores and brief reasoning:
RELEVANCE: [score] - [reason]
PROGRESS: [score] - [reason]
SOUNDNESS: [score] - [reason]
NOVELTY: [score] - [reason]
COMPLETENESS: [score] - [reason]
OVERALL: [0-1 score]"""

        response = await llm.generate(prompt, temperature=0.3)

        # Parse overall score
        score = 0.5  # Default
        if "OVERALL:" in response:
            try:
                score_text = response.split("OVERALL:")[-1].strip()[:10]
                # Extract number
                import re
                numbers = re.findall(r'[\d.]+', score_text)
                if numbers:
                    score = float(numbers[0])
                    if score > 1:  # If they used 0-10 scale
                        score = score / 10
            except:
                pass

        node.score = score
        node.reasoning = response

        return node

    def _get_path_to_root(self, node: ThoughtNode) -> str:
        """Get the reasoning path from root to this node."""
        path = []
        current = node

        while current:
            path.append(f"[Depth {current.depth}]: {current.content[:200]}")
            if current.parent_id:
                current = self._nodes.get(current.parent_id)
            else:
                break

        path.reverse()
        return "\n".join(path)

    async def _build_trace(
        self,
        query: str,
        solutions: List[ThoughtNode]
    ) -> ThinkingTrace:
        """Build a thinking trace from the best solution path."""
        trace = ThinkingTrace(
            query=query,
            mode=ThinkingMode.TREE
        )

        if not solutions:
            trace.final_answer = "No solution found through tree exploration."
            trace.confidence = 0.3
            return trace

        # Get best solution
        best_solution = max(solutions, key=lambda n: n.score)

        # Build path
        path = []
        current = best_solution
        while current:
            step = ThinkingStep(
                id=current.id,
                content=current.content,
                step_type="tree_node",
                confidence=current.score
            )
            path.append(step)

            if current.parent_id:
                current = self._nodes.get(current.parent_id)
            else:
                break

        path.reverse()
        trace.steps = path

        # Synthesize final answer
        llm = await self._get_llm()
        path_summary = "\n".join(f"Step {i+1}: {s.content[:150]}" for i, s in enumerate(path))

        synth_prompt = f"""Based on this reasoning path, provide a complete answer to the original problem.

PROBLEM: {query}

REASONING PATH:
{path_summary}

Synthesize these steps into a clear, comprehensive answer:"""

        trace.final_answer = await llm.generate(synth_prompt, temperature=0.3)
        trace.confidence = best_solution.score

        # Record all branches explored
        trace.branches = {
            node.id: node.children_ids
            for node in self._nodes.values()
            if node.children_ids
        }

        return trace

    def get_exploration_stats(self) -> Dict[str, Any]:
        """Get statistics about the exploration."""
        if not self._nodes:
            return {}

        statuses = {}
        for node in self._nodes.values():
            status = node.status.value
            statuses[status] = statuses.get(status, 0) + 1

        depths = [n.depth for n in self._nodes.values()]
        scores = [n.score for n in self._nodes.values() if n.score > 0]

        return {
            "total_nodes": len(self._nodes),
            "status_breakdown": statuses,
            "max_depth_reached": max(depths) if depths else 0,
            "average_score": sum(scores) / len(scores) if scores else 0,
            "pruned_branches": statuses.get("pruned", 0)
        }


# Global instance
_tree_thinker: Optional[TreeOfThought] = None


def get_tree_thinker(config: Optional[TreeConfig] = None) -> TreeOfThought:
    """Get or create tree-of-thought instance."""
    global _tree_thinker
    if _tree_thinker is None or config is not None:
        _tree_thinker = TreeOfThought(config)
    return _tree_thinker


async def explore_tree(query: str, **kwargs) -> ThinkingTrace:
    """Convenience function for tree-of-thought exploration."""
    thinker = get_tree_thinker()
    return await thinker.explore(query, **kwargs)
