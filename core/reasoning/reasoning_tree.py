"""
BAEL Reasoning Tree
====================

Tree-based exploration of reasoning paths.
Enables branching logic and parallel hypothesis testing.

Features:
- Branching exploration
- Path scoring
- Backtracking
- Best-first search
- Pruning strategies
"""

import asyncio
import hashlib
import heapq
import logging
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class NodeStatus(Enum):
    """Status of a reasoning node."""
    PENDING = "pending"
    EXPLORING = "exploring"
    COMPLETE = "complete"
    PRUNED = "pruned"
    FAILED = "failed"


class BranchStrategy(Enum):
    """Branching strategies."""
    BREADTH_FIRST = "breadth_first"
    DEPTH_FIRST = "depth_first"
    BEST_FIRST = "best_first"
    BEAM_SEARCH = "beam_search"
    MONTE_CARLO = "monte_carlo"


@dataclass
class TreeNode:
    """A node in the reasoning tree."""
    id: str
    content: str

    # Tree structure
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    depth: int = 0

    # Scoring
    score: float = 0.0
    heuristic: float = 0.0
    cumulative_score: float = 0.0

    # Status
    status: NodeStatus = NodeStatus.PENDING

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    exploration_order: int = 0

    # Results
    result: Any = None

    def __lt__(self, other: "TreeNode") -> bool:
        """Compare for priority queue (higher score first)."""
        return self.cumulative_score > other.cumulative_score


@dataclass
class ExplorationResult:
    """Result of tree exploration."""
    root_id: str

    # Best path
    best_path: List[TreeNode] = field(default_factory=list)
    best_score: float = 0.0

    # All paths explored
    paths_explored: int = 0
    nodes_visited: int = 0

    # Pruned
    nodes_pruned: int = 0

    # Timing
    duration_ms: float = 0.0

    # Solution found?
    solution_found: bool = False


class ReasoningTree:
    """
    Reasoning tree for BAEL.

    Enables tree-based exploration of solution spaces.
    """

    def __init__(
        self,
        strategy: BranchStrategy = BranchStrategy.BEST_FIRST,
        max_depth: int = 10,
        max_branches: int = 5,
        beam_width: int = 3,
    ):
        self.strategy = strategy
        self.max_depth = max_depth
        self.max_branches = max_branches
        self.beam_width = beam_width

        # Nodes
        self._nodes: Dict[str, TreeNode] = {}

        # Exploration state
        self._frontier: List[TreeNode] = []
        self._explored: Set[str] = set()

        # Best solution tracking
        self._best_solution: Optional[TreeNode] = None
        self._solutions: List[TreeNode] = []

        # Order counter
        self._order_counter = 0

        # Stats
        self.stats = {
            "trees_built": 0,
            "nodes_created": 0,
            "paths_explored": 0,
            "solutions_found": 0,
        }

    def create_root(
        self,
        content: str,
        heuristic: float = 0.5,
    ) -> TreeNode:
        """
        Create a root node.

        Args:
            content: Root content/problem
            heuristic: Initial heuristic estimate

        Returns:
            Root node
        """
        node_id = hashlib.md5(
            f"root:{content}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        root = TreeNode(
            id=node_id,
            content=content,
            depth=0,
            heuristic=heuristic,
            cumulative_score=heuristic,
            exploration_order=0,
        )

        self._nodes[node_id] = root
        self._frontier = [root]
        self._explored.clear()
        self._order_counter = 1

        self.stats["trees_built"] += 1
        self.stats["nodes_created"] += 1

        return root

    def add_child(
        self,
        parent_id: str,
        content: str,
        score: float = 0.0,
        heuristic: float = 0.0,
    ) -> Optional[TreeNode]:
        """
        Add a child node.

        Args:
            parent_id: Parent node ID
            content: Child content
            score: Node score
            heuristic: Heuristic estimate

        Returns:
            Child node or None if limit reached
        """
        if parent_id not in self._nodes:
            return None

        parent = self._nodes[parent_id]

        # Check limits
        if parent.depth >= self.max_depth:
            return None

        if len(parent.children) >= self.max_branches:
            return None

        node_id = hashlib.md5(
            f"{parent_id}:{content}:{len(parent.children)}".encode()
        ).hexdigest()[:12]

        child = TreeNode(
            id=node_id,
            content=content,
            parent_id=parent_id,
            depth=parent.depth + 1,
            score=score,
            heuristic=heuristic,
            cumulative_score=parent.cumulative_score + score + heuristic,
            exploration_order=self._order_counter,
        )

        self._order_counter += 1
        self._nodes[node_id] = child
        parent.children.append(node_id)

        # Add to frontier
        if self.strategy == BranchStrategy.BEST_FIRST:
            heapq.heappush(self._frontier, child)
        else:
            self._frontier.append(child)

        self.stats["nodes_created"] += 1

        return child

    def expand_node(
        self,
        node_id: str,
        expansions: List[Tuple[str, float, float]],  # (content, score, heuristic)
    ) -> List[TreeNode]:
        """
        Expand a node with multiple children.

        Args:
            node_id: Node to expand
            expansions: List of (content, score, heuristic) tuples

        Returns:
            Created child nodes
        """
        children = []

        for content, score, heuristic in expansions:
            child = self.add_child(node_id, content, score, heuristic)
            if child:
                children.append(child)

        return children

    async def explore(
        self,
        goal_test: Callable[[TreeNode], bool],
        expand_fn: Callable[[TreeNode], List[Tuple[str, float, float]]],
        max_nodes: int = 1000,
    ) -> ExplorationResult:
        """
        Explore the tree to find solutions.

        Args:
            goal_test: Function to test if node is a solution
            expand_fn: Function to generate expansions
            max_nodes: Maximum nodes to explore

        Returns:
            Exploration result
        """
        import time
        start = time.time()

        nodes_visited = 0
        nodes_pruned = 0

        while self._frontier and nodes_visited < max_nodes:
            # Select next node based on strategy
            node = self._select_next()

            if node is None or node.id in self._explored:
                continue

            self._explored.add(node.id)
            node.status = NodeStatus.EXPLORING
            nodes_visited += 1

            # Check if goal
            if goal_test(node):
                node.status = NodeStatus.COMPLETE
                self._solutions.append(node)
                self.stats["solutions_found"] += 1

                # Update best
                if (self._best_solution is None or
                    node.cumulative_score > self._best_solution.cumulative_score):
                    self._best_solution = node
            else:
                # Expand
                expansions = expand_fn(node)
                self.expand_node(node.id, expansions)

                # Prune if using beam search
                if self.strategy == BranchStrategy.BEAM_SEARCH:
                    pruned = self._beam_prune()
                    nodes_pruned += pruned

            node.status = NodeStatus.COMPLETE
            self.stats["paths_explored"] += 1

        # Build result
        duration = (time.time() - start) * 1000

        result = ExplorationResult(
            root_id=list(self._nodes.keys())[0] if self._nodes else "",
            nodes_visited=nodes_visited,
            nodes_pruned=nodes_pruned,
            duration_ms=duration,
            paths_explored=self.stats["paths_explored"],
        )

        if self._best_solution:
            result.best_path = self._trace_path(self._best_solution.id)
            result.best_score = self._best_solution.cumulative_score
            result.solution_found = True

        return result

    def _select_next(self) -> Optional[TreeNode]:
        """Select next node based on strategy."""
        if not self._frontier:
            return None

        if self.strategy == BranchStrategy.BREADTH_FIRST:
            return self._frontier.pop(0)

        elif self.strategy == BranchStrategy.DEPTH_FIRST:
            return self._frontier.pop()

        elif self.strategy == BranchStrategy.BEST_FIRST:
            return heapq.heappop(self._frontier)

        elif self.strategy == BranchStrategy.BEAM_SEARCH:
            # Sort by score and take best
            self._frontier.sort(key=lambda n: n.cumulative_score, reverse=True)
            return self._frontier.pop(0) if self._frontier else None

        else:
            return self._frontier.pop(0)

    def _beam_prune(self) -> int:
        """Prune frontier for beam search."""
        if len(self._frontier) <= self.beam_width:
            return 0

        # Sort by score
        self._frontier.sort(key=lambda n: n.cumulative_score, reverse=True)

        # Keep top beam_width
        pruned = self._frontier[self.beam_width:]
        self._frontier = self._frontier[:self.beam_width]

        # Mark pruned
        for node in pruned:
            node.status = NodeStatus.PRUNED

        return len(pruned)

    def _trace_path(self, node_id: str) -> List[TreeNode]:
        """Trace path from root to node."""
        path = []
        current = node_id

        while current:
            if current not in self._nodes:
                break

            node = self._nodes[current]
            path.append(node)
            current = node.parent_id

        path.reverse()
        return path

    def get_node(self, node_id: str) -> Optional[TreeNode]:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_children(self, node_id: str) -> List[TreeNode]:
        """Get children of a node."""
        if node_id not in self._nodes:
            return []

        node = self._nodes[node_id]
        return [self._nodes[cid] for cid in node.children if cid in self._nodes]

    def get_solutions(self) -> List[TreeNode]:
        """Get all solutions found."""
        return self._solutions

    def visualize(self, max_depth: int = 3) -> str:
        """Visualize tree as text."""
        if not self._nodes:
            return "Empty tree"

        lines = ["Reasoning Tree:"]

        # Find root
        root = None
        for node in self._nodes.values():
            if node.parent_id is None:
                root = node
                break

        if not root:
            return "No root found"

        def _visualize_node(node: TreeNode, prefix: str = "", is_last: bool = True):
            if node.depth > max_depth:
                return

            status_icon = {
                NodeStatus.PENDING: "○",
                NodeStatus.EXPLORING: "◐",
                NodeStatus.COMPLETE: "●",
                NodeStatus.PRUNED: "✗",
                NodeStatus.FAILED: "✗",
            }.get(node.status, "?")

            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{status_icon} {node.content[:40]}... (s:{node.cumulative_score:.2f})")

            children = self.get_children(node.id)
            child_prefix = prefix + ("    " if is_last else "│   ")

            for i, child in enumerate(children):
                _visualize_node(child, child_prefix, i == len(children) - 1)

        _visualize_node(root, "", True)

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Get tree statistics."""
        return {
            **self.stats,
            "current_nodes": len(self._nodes),
            "frontier_size": len(self._frontier),
            "explored": len(self._explored),
            "solutions": len(self._solutions),
        }


def demo():
    """Demonstrate reasoning tree."""
    import asyncio

    print("=" * 60)
    print("BAEL Reasoning Tree Demo")
    print("=" * 60)

    async def run_demo():
        tree = ReasoningTree(
            strategy=BranchStrategy.BEST_FIRST,
            max_depth=5,
            max_branches=3,
        )

        # Create root
        root = tree.create_root(
            "Find the bug causing database connection timeout",
            heuristic=0.5,
        )

        print(f"\nRoot created: {root.id}")

        # Define goal test
        def goal_test(node: TreeNode) -> bool:
            return "solution" in node.content.lower()

        # Define expansion function
        step = [0]
        def expand_fn(node: TreeNode) -> List[Tuple[str, float, float]]:
            step[0] += 1

            # Simulate reasoning branches
            if node.depth == 0:
                return [
                    ("Check connection pool settings", 0.3, 0.6),
                    ("Check database server logs", 0.2, 0.5),
                    ("Check network latency", 0.1, 0.4),
                ]
            elif "pool" in node.content.lower():
                return [
                    ("Pool size too small - SOLUTION", 0.9, 0.1),
                    ("Pool timeout configured incorrectly", 0.4, 0.3),
                ]
            elif "logs" in node.content.lower():
                return [
                    ("Too many connections - investigate", 0.3, 0.4),
                    ("Query deadlock detected", 0.2, 0.3),
                ]
            elif "network" in node.content.lower():
                return [
                    ("High latency to database - SOLUTION", 0.7, 0.2),
                ]
            elif "connections" in node.content.lower():
                return [
                    ("Connection leak in application - SOLUTION", 0.8, 0.1),
                ]

            return []

        # Explore
        print("\nExploring tree...")
        result = await tree.explore(
            goal_test=goal_test,
            expand_fn=expand_fn,
            max_nodes=20,
        )

        print(f"\nExploration complete:")
        print(f"  Nodes visited: {result.nodes_visited}")
        print(f"  Solutions found: {result.solution_found}")
        print(f"  Best score: {result.best_score:.2f}")
        print(f"  Duration: {result.duration_ms:.1f}ms")

        if result.best_path:
            print(f"\nBest path:")
            for node in result.best_path:
                print(f"  [{node.depth}] {node.content}")

        # Visualize
        print(f"\n{tree.visualize()}")

        print(f"\nStats: {tree.get_stats()}")

    asyncio.run(run_demo())


if __name__ == "__main__":
    demo()
