"""
BAEL - The Lord of All AI Agents
Reasoning Engine - Multi-Strategy Cognitive Processing

This module implements advanced reasoning capabilities:
- Chain of Thought (CoT) - Step-by-step logical reasoning
- Tree of Thoughts (ToT) - Branching exploration
- Graph of Thoughts (GoT) - Complex interconnected reasoning
- Meta-Cognition - Reasoning about reasoning
- Analogical Reasoning - Learning from similar cases
- Counterfactual Reasoning - What-if analysis
"""

import asyncio
import json
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("BAEL.Reasoning")


class ReasoningStrategy(Enum):
    """Available reasoning strategies."""
    CHAIN_OF_THOUGHT = "cot"          # Linear step-by-step
    TREE_OF_THOUGHTS = "tot"           # Branching exploration
    GRAPH_OF_THOUGHTS = "got"          # Complex interconnected
    ANALOGICAL = "analogical"          # Learning from similar cases
    COUNTERFACTUAL = "counterfactual"  # What-if analysis
    ABDUCTIVE = "abductive"            # Best explanation inference
    DEDUCTIVE = "deductive"            # From general to specific
    INDUCTIVE = "inductive"            # From specific to general
    META = "meta"                      # Reasoning about reasoning


@dataclass
class ThoughtNode:
    """A single thought in the reasoning process."""
    id: str
    content: str
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    score: float = 0.0
    confidence: float = 0.5
    depth: int = 0
    is_terminal: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ReasoningResult:
    """Result of a reasoning process."""
    strategy: ReasoningStrategy
    conclusion: str
    confidence: float
    reasoning_trace: List[ThoughtNode]
    alternatives: List[str] = field(default_factory=list)
    meta_analysis: Optional[str] = None
    time_taken: float = 0.0


class ThoughtEvaluator:
    """Evaluates and scores thoughts in the reasoning process."""

    def __init__(self, model_router=None):
        self.model_router = model_router

    async def evaluate(self, thought: ThoughtNode, context: Dict) -> float:
        """Evaluate a thought and return a score (0-1)."""
        # Heuristic scoring
        score = 0.5

        content = thought.content.lower()

        # Positive indicators
        if any(word in content for word in ['therefore', 'because', 'since', 'thus']):
            score += 0.1  # Logical connectors
        if any(word in content for word in ['evidence', 'data', 'shows', 'indicates']):
            score += 0.1  # Evidence-based
        if len(thought.content) > 50:
            score += 0.05  # Substantial content

        # Negative indicators
        if any(word in content for word in ['maybe', 'perhaps', 'might', 'could be']):
            score -= 0.1  # Uncertainty
        if 'i think' in content or 'i believe' in content:
            score -= 0.05  # Subjective

        # Depth bonus (deeper thoughts in valid chains are valuable)
        score += min(0.1, thought.depth * 0.02)

        return max(0.0, min(1.0, score))

    async def compare(self, thought_a: ThoughtNode, thought_b: ThoughtNode, context: Dict) -> int:
        """Compare two thoughts. Returns -1, 0, or 1."""
        score_a = await self.evaluate(thought_a, context)
        score_b = await self.evaluate(thought_b, context)

        if score_a > score_b:
            return 1
        elif score_a < score_b:
            return -1
        return 0


class ChainOfThought:
    """
    Chain of Thought (CoT) Reasoning.

    Step-by-step linear reasoning process that breaks down
    complex problems into sequential logical steps.
    """

    def __init__(self, model_router=None, max_steps: int = 10):
        self.model_router = model_router
        self.max_steps = max_steps
        self.evaluator = ThoughtEvaluator(model_router)

    async def reason(self, problem: str, context: Optional[Dict] = None) -> ReasoningResult:
        """Execute chain of thought reasoning."""
        logger.info(f"🔗 Starting Chain of Thought reasoning...")
        start_time = datetime.now()

        thoughts: List[ThoughtNode] = []
        current_reasoning = ""

        # Initial thought
        initial = ThoughtNode(
            id="cot_0",
            content=f"Let me think about this step by step: {problem}",
            depth=0
        )
        thoughts.append(initial)

        # Generate reasoning chain
        for step in range(1, self.max_steps):
            prompt = self._build_step_prompt(problem, thoughts, context)

            # Generate next step
            if self.model_router:
                next_step = await self.model_router.generate(
                    prompt=prompt,
                    model_type='reasoning'
                )
            else:
                next_step = f"Step {step}: Analyzing the problem further..."

            thought = ThoughtNode(
                id=f"cot_{step}",
                content=next_step,
                parent_id=f"cot_{step-1}",
                depth=step
            )

            # Evaluate thought
            thought.score = await self.evaluator.evaluate(thought, context or {})
            thoughts.append(thought)

            # Check for conclusion
            if self._is_conclusion(next_step):
                thought.is_terminal = True
                break

        # Extract conclusion
        conclusion = thoughts[-1].content if thoughts else "Unable to reach conclusion"
        confidence = sum(t.score for t in thoughts) / len(thoughts) if thoughts else 0

        time_taken = (datetime.now() - start_time).total_seconds()

        return ReasoningResult(
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            conclusion=conclusion,
            confidence=confidence,
            reasoning_trace=thoughts,
            time_taken=time_taken
        )

    def _build_step_prompt(self, problem: str, thoughts: List[ThoughtNode], context: Optional[Dict]) -> str:
        """Build prompt for next reasoning step."""
        previous_steps = "\n".join([f"Step {i}: {t.content}" for i, t in enumerate(thoughts)])

        return f"""
Problem: {problem}

Previous reasoning steps:
{previous_steps}

What is the next logical step in solving this problem?
If you've reached a conclusion, clearly state "Therefore, the conclusion is: [your conclusion]"
"""

    def _is_conclusion(self, text: str) -> bool:
        """Check if text contains a conclusion."""
        conclusion_markers = ['therefore', 'in conclusion', 'the answer is', 'the solution is', 'finally']
        return any(marker in text.lower() for marker in conclusion_markers)


class TreeOfThoughts:
    """
    Tree of Thoughts (ToT) Reasoning.

    Explores multiple reasoning paths in parallel,
    evaluating and pruning to find the best solution.
    """

    def __init__(self, model_router=None, branching_factor: int = 3, max_depth: int = 5):
        self.model_router = model_router
        self.branching_factor = branching_factor
        self.max_depth = max_depth
        self.evaluator = ThoughtEvaluator(model_router)

    async def reason(self, problem: str, context: Optional[Dict] = None) -> ReasoningResult:
        """Execute tree of thoughts reasoning."""
        logger.info(f"🌳 Starting Tree of Thoughts reasoning...")
        start_time = datetime.now()

        # Initialize root
        root = ThoughtNode(
            id="tot_root",
            content=f"Problem to solve: {problem}",
            depth=0
        )

        all_thoughts = {root.id: root}
        current_frontier = [root]
        best_path: List[ThoughtNode] = []
        best_score = 0.0

        for depth in range(self.max_depth):
            new_frontier = []

            for thought in current_frontier:
                # Generate branches
                branches = await self._generate_branches(thought, problem, context)

                for branch in branches:
                    branch.parent_id = thought.id
                    branch.depth = depth + 1
                    branch.score = await self.evaluator.evaluate(branch, context or {})

                    thought.children_ids.append(branch.id)
                    all_thoughts[branch.id] = branch

                    # Check if this is a better path
                    path = self._get_path(branch, all_thoughts)
                    path_score = sum(t.score for t in path) / len(path)

                    if path_score > best_score:
                        best_score = path_score
                        best_path = path

                    if not branch.is_terminal:
                        new_frontier.append(branch)

            # Prune: keep only top-k nodes
            new_frontier.sort(key=lambda t: t.score, reverse=True)
            current_frontier = new_frontier[:self.branching_factor * 2]

            if not current_frontier:
                break

        # Extract conclusion from best path
        conclusion = best_path[-1].content if best_path else "Unable to reach conclusion"

        # Collect alternative conclusions
        alternatives = []
        for thought_id, thought in all_thoughts.items():
            if thought.is_terminal and thought not in best_path:
                alternatives.append(thought.content)

        time_taken = (datetime.now() - start_time).total_seconds()

        return ReasoningResult(
            strategy=ReasoningStrategy.TREE_OF_THOUGHTS,
            conclusion=conclusion,
            confidence=best_score,
            reasoning_trace=best_path,
            alternatives=alternatives[:3],
            time_taken=time_taken
        )

    async def _generate_branches(
        self,
        thought: ThoughtNode,
        problem: str,
        context: Optional[Dict]
    ) -> List[ThoughtNode]:
        """Generate branch thoughts from current thought."""
        branches = []

        prompt = f"""
Problem: {problem}

Current reasoning: {thought.content}

Generate {self.branching_factor} different ways to continue this reasoning.
Each should explore a different angle or approach.
Format: One approach per line, starting with "Approach N:"
"""

        if self.model_router:
            response = await self.model_router.generate(
                prompt=prompt,
                model_type='reasoning'
            )

            # Parse response into branches
            lines = response.split('\n')
            for i, line in enumerate(lines):
                if line.strip() and ('approach' in line.lower() or line.strip()[0].isdigit()):
                    branch = ThoughtNode(
                        id=f"{thought.id}_b{i}",
                        content=line.strip(),
                        is_terminal=self._is_conclusion(line)
                    )
                    branches.append(branch)
                    if len(branches) >= self.branching_factor:
                        break
        else:
            # Mock branches for testing
            for i in range(self.branching_factor):
                branches.append(ThoughtNode(
                    id=f"{thought.id}_b{i}",
                    content=f"Approach {i+1}: Exploring alternative path..."
                ))

        return branches

    def _get_path(self, thought: ThoughtNode, all_thoughts: Dict[str, ThoughtNode]) -> List[ThoughtNode]:
        """Get path from root to thought."""
        path = [thought]
        current = thought

        while current.parent_id and current.parent_id in all_thoughts:
            current = all_thoughts[current.parent_id]
            path.insert(0, current)

        return path

    def _is_conclusion(self, text: str) -> bool:
        """Check if text contains a conclusion."""
        conclusion_markers = ['therefore', 'in conclusion', 'the answer is', 'the solution is', 'finally']
        return any(marker in text.lower() for marker in conclusion_markers)


class GraphOfThoughts:
    """
    Graph of Thoughts (GoT) Reasoning.

    Implements complex reasoning with interconnected thoughts,
    allowing for cycles, merges, and multi-path convergence.
    """

    def __init__(self, model_router=None, max_nodes: int = 50):
        self.model_router = model_router
        self.max_nodes = max_nodes
        self.evaluator = ThoughtEvaluator(model_router)

    async def reason(self, problem: str, context: Optional[Dict] = None) -> ReasoningResult:
        """Execute graph of thoughts reasoning."""
        logger.info(f"🕸️ Starting Graph of Thoughts reasoning...")
        start_time = datetime.now()

        # Initialize graph
        nodes: Dict[str, ThoughtNode] = {}
        edges: List[Tuple[str, str]] = []

        # Create initial thought nodes for different aspects
        aspects = await self._decompose_problem(problem)

        for i, aspect in enumerate(aspects):
            node = ThoughtNode(
                id=f"got_aspect_{i}",
                content=aspect,
                depth=0
            )
            node.score = await self.evaluator.evaluate(node, context or {})
            nodes[node.id] = node

        # Expand and connect nodes
        iterations = 0
        while len(nodes) < self.max_nodes and iterations < 10:
            iterations += 1

            # Select nodes to expand
            expandable = [n for n in nodes.values() if not n.is_terminal and len(n.children_ids) < 3]
            if not expandable:
                break

            # Expand each node
            for node in expandable[:5]:
                new_thoughts = await self._expand_thought(node, problem, nodes, context)

                for thought in new_thoughts:
                    nodes[thought.id] = thought
                    edges.append((node.id, thought.id))
                    node.children_ids.append(thought.id)

            # Try to find connections between existing nodes
            new_edges = await self._find_connections(nodes, edges, context)
            edges.extend(new_edges)

        # Synthesize conclusion from graph
        conclusion, confidence = await self._synthesize_conclusion(nodes, edges, problem, context)

        # Get key reasoning path
        key_path = self._extract_key_path(nodes, edges)

        time_taken = (datetime.now() - start_time).total_seconds()

        return ReasoningResult(
            strategy=ReasoningStrategy.GRAPH_OF_THOUGHTS,
            conclusion=conclusion,
            confidence=confidence,
            reasoning_trace=key_path,
            time_taken=time_taken
        )

    async def _decompose_problem(self, problem: str) -> List[str]:
        """Decompose problem into aspects."""
        if self.model_router:
            prompt = f"""
Decompose this problem into 3-5 distinct aspects or sub-problems:

Problem: {problem}

List each aspect on a new line, starting with a number.
"""
            response = await self.model_router.generate(prompt=prompt, model_type='reasoning')
            aspects = [line.strip() for line in response.split('\n') if line.strip() and line.strip()[0].isdigit()]
            return aspects[:5]

        return [
            f"1. Core requirement: {problem[:50]}...",
            "2. Constraints and limitations",
            "3. Potential approaches",
            "4. Trade-offs to consider"
        ]

    async def _expand_thought(
        self,
        node: ThoughtNode,
        problem: str,
        existing_nodes: Dict[str, ThoughtNode],
        context: Optional[Dict]
    ) -> List[ThoughtNode]:
        """Expand a thought node with connected thoughts."""
        thoughts = []

        if self.model_router:
            prompt = f"""
Building on this thought: {node.content}

In the context of: {problem}

What are 2-3 logical next thoughts or implications?
Each thought should build on or connect to the previous one.
"""
            response = await self.model_router.generate(prompt=prompt, model_type='reasoning')

            for i, line in enumerate(response.split('\n')):
                if line.strip():
                    thought = ThoughtNode(
                        id=f"{node.id}_exp_{i}",
                        content=line.strip(),
                        parent_id=node.id,
                        depth=node.depth + 1
                    )
                    thought.score = await self.evaluator.evaluate(thought, context or {})
                    thoughts.append(thought)
                    if len(thoughts) >= 3:
                        break

        return thoughts

    async def _find_connections(
        self,
        nodes: Dict[str, ThoughtNode],
        existing_edges: List[Tuple[str, str]],
        context: Optional[Dict]
    ) -> List[Tuple[str, str]]:
        """Find potential connections between unconnected nodes."""
        new_edges = []
        node_list = list(nodes.values())

        # Sample pairs to check for connections
        for i in range(min(10, len(node_list))):
            for j in range(i + 1, min(10, len(node_list))):
                node_a = node_list[i]
                node_b = node_list[j]

                # Check if already connected
                if (node_a.id, node_b.id) in existing_edges or (node_b.id, node_a.id) in existing_edges:
                    continue

                # Check for semantic similarity (simple heuristic)
                words_a = set(node_a.content.lower().split())
                words_b = set(node_b.content.lower().split())
                overlap = len(words_a & words_b) / max(len(words_a | words_b), 1)

                if overlap > 0.3:  # Significant overlap
                    new_edges.append((node_a.id, node_b.id))

        return new_edges

    async def _synthesize_conclusion(
        self,
        nodes: Dict[str, ThoughtNode],
        edges: List[Tuple[str, str]],
        problem: str,
        context: Optional[Dict]
    ) -> Tuple[str, float]:
        """Synthesize a conclusion from the thought graph."""
        # Get high-scoring nodes
        sorted_nodes = sorted(nodes.values(), key=lambda n: n.score, reverse=True)
        key_thoughts = [n.content for n in sorted_nodes[:5]]

        if self.model_router:
            prompt = f"""
Problem: {problem}

Key insights from analysis:
{chr(10).join(f'- {t}' for t in key_thoughts)}

Synthesize these insights into a clear, comprehensive conclusion.
"""
            conclusion = await self.model_router.generate(prompt=prompt, model_type='reasoning')
        else:
            conclusion = f"Based on analysis of {len(nodes)} interconnected thoughts, the solution involves: {key_thoughts[0] if key_thoughts else 'further analysis needed'}"

        # Calculate confidence from average scores
        confidence = sum(n.score for n in nodes.values()) / len(nodes) if nodes else 0

        return conclusion, confidence

    def _extract_key_path(self, nodes: Dict[str, ThoughtNode], edges: List[Tuple[str, str]]) -> List[ThoughtNode]:
        """Extract the key reasoning path from the graph."""
        # Sort by score and depth
        sorted_nodes = sorted(
            nodes.values(),
            key=lambda n: (n.score * 0.7 + (1 - n.depth / 10) * 0.3),
            reverse=True
        )

        return sorted_nodes[:10]


class MetaCognition:
    """
    Meta-Cognition - Reasoning about reasoning.

    Monitors and evaluates the reasoning process itself,
    adjusting strategies and improving overall reasoning quality.
    """

    def __init__(self, model_router=None):
        self.model_router = model_router
        self.reasoning_history: List[ReasoningResult] = []

    async def analyze_reasoning(self, result: ReasoningResult) -> Dict[str, Any]:
        """Analyze a reasoning result for quality and improvement opportunities."""
        analysis = {
            'strategy_used': result.strategy.value,
            'confidence': result.confidence,
            'trace_length': len(result.reasoning_trace),
            'time_taken': result.time_taken,
            'strengths': [],
            'weaknesses': [],
            'improvement_suggestions': []
        }

        # Analyze confidence
        if result.confidence > 0.8:
            analysis['strengths'].append("High confidence conclusion")
        elif result.confidence < 0.5:
            analysis['weaknesses'].append("Low confidence - consider additional reasoning")
            analysis['improvement_suggestions'].append("Try a different reasoning strategy")

        # Analyze trace
        if len(result.reasoning_trace) < 3:
            analysis['weaknesses'].append("Short reasoning trace - may be oversimplified")
        elif len(result.reasoning_trace) > 15:
            analysis['weaknesses'].append("Long reasoning trace - may be overthinking")

        # Analyze alternatives
        if result.alternatives:
            analysis['strengths'].append(f"Explored {len(result.alternatives)} alternative paths")
        else:
            analysis['improvement_suggestions'].append("Consider Tree of Thoughts for exploring alternatives")

        return analysis

    async def recommend_strategy(self, problem: str, context: Optional[Dict] = None) -> ReasoningStrategy:
        """Recommend the best reasoning strategy for a problem."""
        problem_lower = problem.lower()

        # Heuristics for strategy selection
        if any(word in problem_lower for word in ['step by step', 'how to', 'explain']):
            return ReasoningStrategy.CHAIN_OF_THOUGHT

        if any(word in problem_lower for word in ['alternatives', 'options', 'compare']):
            return ReasoningStrategy.TREE_OF_THOUGHTS

        if any(word in problem_lower for word in ['complex', 'interconnected', 'relationships']):
            return ReasoningStrategy.GRAPH_OF_THOUGHTS

        if any(word in problem_lower for word in ['similar to', 'like', 'analogous']):
            return ReasoningStrategy.ANALOGICAL

        if any(word in problem_lower for word in ['what if', 'suppose', 'imagine']):
            return ReasoningStrategy.COUNTERFACTUAL

        # Default to chain of thought
        return ReasoningStrategy.CHAIN_OF_THOUGHT

    async def improve_result(self, result: ReasoningResult, problem: str) -> ReasoningResult:
        """Attempt to improve a reasoning result."""
        analysis = await self.analyze_reasoning(result)

        if result.confidence < 0.6 and result.strategy == ReasoningStrategy.CHAIN_OF_THOUGHT:
            # Try tree of thoughts for low confidence results
            logger.info("📈 Attempting improvement with Tree of Thoughts...")
            tot = TreeOfThoughts(self.model_router)
            improved = await tot.reason(problem)

            if improved.confidence > result.confidence:
                improved.meta_analysis = f"Improved from {result.strategy.value} (conf: {result.confidence:.2f}) to {improved.strategy.value} (conf: {improved.confidence:.2f})"
                return improved

        return result

    def record_result(self, result: ReasoningResult):
        """Record reasoning result for learning."""
        self.reasoning_history.append(result)

        # Keep only last 100 results
        if len(self.reasoning_history) > 100:
            self.reasoning_history = self.reasoning_history[-100:]


class ReasoningEngine:
    """
    Central Reasoning Engine - Orchestrates all reasoning strategies.

    Provides unified interface for reasoning with automatic
    strategy selection and meta-cognitive improvement.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_router = None

        # Initialize reasoning strategies
        self.cot = ChainOfThought(max_steps=config.get('cot', {}).get('max_steps', 10))
        self.tot = TreeOfThoughts(
            branching_factor=config.get('tot', {}).get('branching_factor', 3),
            max_depth=config.get('tot', {}).get('max_depth', 5)
        )
        self.got = GraphOfThoughts(max_nodes=config.get('got', {}).get('max_nodes', 50))
        self.meta = MetaCognition()

        self.strategies = {
            ReasoningStrategy.CHAIN_OF_THOUGHT: self.cot,
            ReasoningStrategy.TREE_OF_THOUGHTS: self.tot,
            ReasoningStrategy.GRAPH_OF_THOUGHTS: self.got,
        }

    def set_model_router(self, router):
        """Set model router for all strategies."""
        self.model_router = router
        self.cot.model_router = router
        self.tot.model_router = router
        self.got.model_router = router
        self.meta.model_router = router

    async def reason(
        self,
        problem: str,
        strategy: Optional[ReasoningStrategy] = None,
        context: Optional[Dict] = None,
        auto_improve: bool = True
    ) -> ReasoningResult:
        """
        Execute reasoning on a problem.

        Args:
            problem: The problem to reason about
            strategy: Specific strategy to use (auto-selected if None)
            context: Additional context
            auto_improve: Whether to attempt improvement via meta-cognition

        Returns:
            ReasoningResult with conclusion and trace
        """
        logger.info(f"🧠 Starting reasoning process...")

        # Select strategy if not specified
        if strategy is None:
            strategy = await self.meta.recommend_strategy(problem, context)
            logger.info(f"📋 Auto-selected strategy: {strategy.value}")

        # Execute reasoning
        if strategy in self.strategies:
            result = await self.strategies[strategy].reason(problem, context)
        else:
            # Default to chain of thought
            result = await self.cot.reason(problem, context)

        # Meta-cognitive improvement
        if auto_improve and result.confidence < self.config.get('improvement_threshold', 0.7):
            logger.info(f"🔄 Attempting meta-cognitive improvement...")
            result = await self.meta.improve_result(result, problem)

        # Record for learning
        self.meta.record_result(result)

        return result

    async def decompose(self, task) -> List[Dict[str, Any]]:
        """Decompose a task into subtasks."""
        problem = f"Decompose this task into smaller subtasks: {task.description}"

        result = await self.reason(
            problem=problem,
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT
        )

        # Parse subtasks from result
        subtasks = []
        for thought in result.reasoning_trace:
            if 'subtask' in thought.content.lower() or thought.content.strip().startswith(('1', '2', '3', '-', '*')):
                subtasks.append({
                    'description': thought.content,
                    'id': thought.id,
                    'confidence': thought.score
                })

        return subtasks

    async def synthesize(self, perspectives: List[Dict], task) -> Dict[str, Any]:
        """Synthesize multiple perspectives into unified understanding."""
        # Combine perspectives
        combined = "\n".join([
            f"Perspective from {p['persona']}: {p['analysis']}"
            for p in perspectives
        ])

        problem = f"""
Synthesize these perspectives on the task: {task.description}

Perspectives:
{combined}

Identify:
1. Areas of agreement
2. Areas of conflict
3. Unified approach that incorporates the best insights
"""

        result = await self.reason(
            problem=problem,
            strategy=ReasoningStrategy.GRAPH_OF_THOUGHTS
        )

        return {
            'combined_insights': [t.content for t in result.reasoning_trace[:5]],
            'unified_approach': result.conclusion,
            'confidence': result.confidence,
            'agreements': [],
            'conflicts': []
        }

    async def counterfactual(self, scenario: str, change: str, context: Optional[Dict] = None) -> ReasoningResult:
        """Perform counterfactual reasoning (what-if analysis)."""
        problem = f"""
Counterfactual Analysis:

Current scenario: {scenario}
Proposed change: {change}

What would happen if we made this change?
Consider:
1. Immediate effects
2. Downstream consequences
3. Potential risks
4. Potential benefits
"""

        return await self.reason(problem, context=context)

    async def analogical(self, problem: str, similar_cases: List[str], context: Optional[Dict] = None) -> ReasoningResult:
        """Perform analogical reasoning using similar cases."""
        cases_text = "\n".join([f"- {case}" for case in similar_cases])

        reasoning_problem = f"""
Analogical Reasoning:

Current problem: {problem}

Similar cases:
{cases_text}

What can we learn from these similar cases?
How can their solutions be adapted to our current problem?
"""

        return await self.reason(reasoning_problem, context=context)

    def get_stats(self) -> Dict[str, Any]:
        """Get reasoning statistics."""
        history = self.meta.reasoning_history

        if not history:
            return {'total_reasoning_sessions': 0}

        return {
            'total_reasoning_sessions': len(history),
            'average_confidence': sum(r.confidence for r in history) / len(history),
            'average_time': sum(r.time_taken for r in history) / len(history),
            'strategy_distribution': {
                strategy.value: sum(1 for r in history if r.strategy == strategy)
                for strategy in ReasoningStrategy
            }
        }


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'ReasoningEngine',
    'ReasoningStrategy',
    'ReasoningResult',
    'ThoughtNode',
    'ChainOfThought',
    'TreeOfThoughts',
    'GraphOfThoughts',
    'MetaCognition'
]
