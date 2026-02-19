"""
BAEL Cognitive Reasoning Engine
================================

Multi-modal, multi-strategy cognitive reasoning.

"True intelligence lies not in knowing, but in understanding." — Ba'el
"""

import asyncio
import hashlib
import json
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import (
    Any, Callable, Dict, List, Optional, Set, Tuple, Union,
    TypeVar, Generic, AsyncIterator
)
from collections import defaultdict
import heapq


class CognitiveMode(Enum):
    """Cognitive processing modes."""
    ANALYTICAL = "analytical"        # Systematic analysis
    CREATIVE = "creative"            # Divergent thinking
    CRITICAL = "critical"            # Evaluation and critique
    INTUITIVE = "intuitive"          # Pattern-based
    LOGICAL = "logical"              # Formal logic
    EMOTIONAL = "emotional"          # Emotion-aware
    HOLISTIC = "holistic"            # Systems thinking
    FOCUSED = "focused"              # Deep concentration
    DIFFUSE = "diffuse"              # Background processing
    METACOGNITIVE = "metacognitive"  # Thinking about thinking


class ThinkingLevel(Enum):
    """Levels of cognitive processing."""
    SURFACE = 1       # Basic pattern matching
    SHALLOW = 2       # Simple reasoning
    MODERATE = 3      # Multi-step reasoning
    DEEP = 4          # Complex inference
    PROFOUND = 5      # Novel insights


class ArgumentType(Enum):
    """Types of arguments."""
    PREMISE = "premise"
    CONCLUSION = "conclusion"
    ASSUMPTION = "assumption"
    EVIDENCE = "evidence"
    COUNTERARGUMENT = "counterargument"
    REBUTTAL = "rebuttal"
    QUALIFIER = "qualifier"
    WARRANT = "warrant"


class FallacyType(Enum):
    """Common logical fallacies."""
    AD_HOMINEM = "ad_hominem"
    STRAW_MAN = "straw_man"
    FALSE_DILEMMA = "false_dilemma"
    SLIPPERY_SLOPE = "slippery_slope"
    CIRCULAR_REASONING = "circular_reasoning"
    APPEAL_TO_AUTHORITY = "appeal_to_authority"
    HASTY_GENERALIZATION = "hasty_generalization"
    RED_HERRING = "red_herring"
    EQUIVOCATION = "equivocation"
    COMPOSITION = "composition"
    DIVISION = "division"
    NONE = "none"


class BiasType(Enum):
    """Cognitive biases."""
    CONFIRMATION = "confirmation"
    ANCHORING = "anchoring"
    AVAILABILITY = "availability"
    HINDSIGHT = "hindsight"
    OVERCONFIDENCE = "overconfidence"
    SUNK_COST = "sunk_cost"
    BANDWAGON = "bandwagon"
    DUNNING_KRUGER = "dunning_kruger"
    NEGATIVITY = "negativity"
    OPTIMISM = "optimism"
    NONE = "none"


@dataclass
class Thought:
    """A unit of cognition."""
    id: str
    content: str
    thought_type: str
    confidence: float = 0.8
    supporting_thoughts: List[str] = field(default_factory=list)
    opposing_thoughts: List[str] = field(default_factory=list)
    cognitive_mode: CognitiveMode = CognitiveMode.ANALYTICAL
    thinking_level: ThinkingLevel = ThinkingLevel.MODERATE
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Argument:
    """A structured argument."""
    id: str
    claim: str
    premises: List[str]
    conclusion: str
    evidence: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    qualifiers: List[str] = field(default_factory=list)
    counterarguments: List[str] = field(default_factory=list)
    rebuttals: List[str] = field(default_factory=list)
    strength: float = 0.5
    validity: bool = True
    soundness: bool = True
    fallacies: List[FallacyType] = field(default_factory=list)


@dataclass
class Perspective:
    """A viewpoint or stance."""
    id: str
    name: str
    description: str
    values: Dict[str, float]
    biases: List[BiasType] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)


@dataclass
class Problem:
    """A problem to solve."""
    id: str
    statement: str
    context: Dict[str, Any]
    constraints: List[str] = field(default_factory=list)
    objectives: List[str] = field(default_factory=list)
    known_solutions: List[str] = field(default_factory=list)
    complexity: ThinkingLevel = ThinkingLevel.MODERATE


@dataclass
class Solution:
    """A proposed solution."""
    id: str
    problem_id: str
    description: str
    steps: List[str]
    confidence: float
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    cognitive_mode_used: CognitiveMode = CognitiveMode.ANALYTICAL
    evaluation_score: float = 0.0


@dataclass
class CognitiveState:
    """Current cognitive state."""
    mode: CognitiveMode = CognitiveMode.ANALYTICAL
    level: ThinkingLevel = ThinkingLevel.MODERATE
    focus: float = 1.0
    fatigue: float = 0.0
    active_thoughts: List[str] = field(default_factory=list)
    working_memory: List[str] = field(default_factory=list)
    biases_active: List[BiasType] = field(default_factory=list)


class ThinkingEngine:
    """Core thinking capabilities."""

    def __init__(self):
        self.thoughts: Dict[str, Thought] = {}
        self.thought_chains: List[List[str]] = []

    async def generate_thought(
        self,
        prompt: str,
        mode: CognitiveMode = CognitiveMode.ANALYTICAL,
        level: ThinkingLevel = ThinkingLevel.MODERATE
    ) -> Thought:
        """Generate a new thought."""
        thought_id = hashlib.sha256(
            f"{prompt}:{mode.value}:{time.time()}".encode()
        ).hexdigest()[:16]

        # Simulate thinking based on mode
        if mode == CognitiveMode.ANALYTICAL:
            content = await self._analytical_thinking(prompt)
        elif mode == CognitiveMode.CREATIVE:
            content = await self._creative_thinking(prompt)
        elif mode == CognitiveMode.CRITICAL:
            content = await self._critical_thinking(prompt)
        elif mode == CognitiveMode.LOGICAL:
            content = await self._logical_thinking(prompt)
        elif mode == CognitiveMode.HOLISTIC:
            content = await self._holistic_thinking(prompt)
        else:
            content = await self._analytical_thinking(prompt)

        thought = Thought(
            id=thought_id,
            content=content,
            thought_type="generated",
            cognitive_mode=mode,
            thinking_level=level,
            confidence=0.7 + (level.value * 0.05)
        )

        self.thoughts[thought_id] = thought
        return thought

    async def _analytical_thinking(self, prompt: str) -> str:
        """Systematic decomposition and analysis."""
        components = prompt.split()
        analysis = f"Analyzing: {prompt}\n"
        analysis += f"- Components identified: {len(components)}\n"
        analysis += f"- Key terms: {', '.join(set(components[:5]))}\n"
        analysis += "- Systematic breakdown required for full analysis"
        return analysis

    async def _creative_thinking(self, prompt: str) -> str:
        """Divergent, creative processing."""
        alternatives = [
            f"Alternative view 1: {prompt} from opposite perspective",
            f"Alternative view 2: {prompt} in different context",
            f"Alternative view 3: Combining {prompt} with unrelated concept"
        ]
        return "Creative exploration:\n" + "\n".join(alternatives)

    async def _critical_thinking(self, prompt: str) -> str:
        """Evaluative, critical processing."""
        evaluation = f"Critical evaluation of: {prompt}\n"
        evaluation += "- Strengths: Requires further evidence\n"
        evaluation += "- Weaknesses: Potential assumptions identified\n"
        evaluation += "- Questions: What evidence supports this?"
        return evaluation

    async def _logical_thinking(self, prompt: str) -> str:
        """Formal logical processing."""
        logic = f"Logical analysis of: {prompt}\n"
        logic += "- If P then Q structure detected\n"
        logic += "- Checking logical consistency\n"
        logic += "- Evaluating truth conditions"
        return logic

    async def _holistic_thinking(self, prompt: str) -> str:
        """Systems-level thinking."""
        holistic = f"Holistic view of: {prompt}\n"
        holistic += "- Considering all interconnections\n"
        holistic += "- Evaluating emergent properties\n"
        holistic += "- Assessing systemic impacts"
        return holistic

    async def chain_thoughts(
        self,
        initial_prompt: str,
        depth: int = 3,
        mode: CognitiveMode = CognitiveMode.ANALYTICAL
    ) -> List[Thought]:
        """Generate a chain of connected thoughts."""
        chain = []
        current_prompt = initial_prompt

        for i in range(depth):
            level = ThinkingLevel(min(i + 2, 5))
            thought = await self.generate_thought(current_prompt, mode, level)
            chain.append(thought)

            # Use thought as input for next
            current_prompt = thought.content

        # Record chain
        chain_ids = [t.id for t in chain]
        self.thought_chains.append(chain_ids)

        # Link thoughts
        for i, thought in enumerate(chain[:-1]):
            chain[i + 1].supporting_thoughts.append(thought.id)

        return chain


class ArgumentEngine:
    """Argument construction and analysis."""

    def __init__(self):
        self.arguments: Dict[str, Argument] = {}
        self.fallacy_patterns = self._init_fallacy_patterns()

    def _init_fallacy_patterns(self) -> Dict[FallacyType, List[str]]:
        """Initialize patterns for detecting fallacies."""
        return {
            FallacyType.AD_HOMINEM: ["stupid", "idiot", "character", "person is"],
            FallacyType.STRAW_MAN: ["they say that", "they believe", "distorted"],
            FallacyType.FALSE_DILEMMA: ["either", "or else", "only two", "no other"],
            FallacyType.SLIPPERY_SLOPE: ["eventually", "lead to", "before you know"],
            FallacyType.CIRCULAR_REASONING: ["because", "therefore", "proves itself"],
            FallacyType.APPEAL_TO_AUTHORITY: ["expert says", "authority", "famous"],
            FallacyType.HASTY_GENERALIZATION: ["always", "never", "everyone", "all"],
        }

    async def construct_argument(
        self,
        claim: str,
        premises: List[str],
        evidence: Optional[List[str]] = None
    ) -> Argument:
        """Construct a structured argument."""
        arg_id = hashlib.sha256(claim.encode()).hexdigest()[:16]

        # Derive conclusion from premises
        conclusion = f"Therefore, {claim}"

        argument = Argument(
            id=arg_id,
            claim=claim,
            premises=premises,
            conclusion=conclusion,
            evidence=evidence or []
        )

        # Analyze for fallacies
        argument.fallacies = await self.detect_fallacies(argument)

        # Calculate strength
        argument.strength = await self.calculate_strength(argument)

        # Check validity and soundness
        argument.validity = len(argument.fallacies) == 0
        argument.soundness = argument.validity and argument.strength > 0.6

        self.arguments[arg_id] = argument
        return argument

    async def detect_fallacies(self, argument: Argument) -> List[FallacyType]:
        """Detect logical fallacies in an argument."""
        fallacies = []
        text = (argument.claim + " " + " ".join(argument.premises)).lower()

        for fallacy, patterns in self.fallacy_patterns.items():
            for pattern in patterns:
                if pattern.lower() in text:
                    fallacies.append(fallacy)
                    break

        return fallacies

    async def calculate_strength(self, argument: Argument) -> float:
        """Calculate argument strength."""
        strength = 0.5

        # More premises = stronger (up to a point)
        premise_bonus = min(len(argument.premises) * 0.1, 0.2)
        strength += premise_bonus

        # Evidence strengthens
        evidence_bonus = min(len(argument.evidence) * 0.1, 0.2)
        strength += evidence_bonus

        # Fallacies weaken
        fallacy_penalty = len(argument.fallacies) * 0.15
        strength -= fallacy_penalty

        # Rebuttals to counterarguments strengthen
        if argument.counterarguments and argument.rebuttals:
            rebuttal_ratio = len(argument.rebuttals) / len(argument.counterarguments)
            strength += min(rebuttal_ratio * 0.1, 0.1)

        return max(0.0, min(1.0, strength))

    async def counter_argument(
        self,
        argument: Argument
    ) -> List[str]:
        """Generate counterarguments."""
        counters = []

        # Challenge premises
        for premise in argument.premises:
            counters.append(f"The premise '{premise}' may not be true because...")

        # Challenge assumptions
        for assumption in argument.assumptions:
            counters.append(f"This assumes '{assumption}' which may be invalid")

        # Point out fallacies
        for fallacy in argument.fallacies:
            counters.append(f"This argument commits the {fallacy.value} fallacy")

        return counters

    async def evaluate_debate(
        self,
        arg1: Argument,
        arg2: Argument
    ) -> Dict[str, Any]:
        """Evaluate two arguments in debate."""
        return {
            "argument_1": {
                "strength": arg1.strength,
                "validity": arg1.validity,
                "soundness": arg1.soundness,
                "fallacies": [f.value for f in arg1.fallacies]
            },
            "argument_2": {
                "strength": arg2.strength,
                "validity": arg2.validity,
                "soundness": arg2.soundness,
                "fallacies": [f.value for f in arg2.fallacies]
            },
            "winner": "argument_1" if arg1.strength > arg2.strength else "argument_2",
            "margin": abs(arg1.strength - arg2.strength)
        }


class PerspectiveEngine:
    """Multi-perspective analysis."""

    def __init__(self):
        self.perspectives: Dict[str, Perspective] = {}
        self._init_default_perspectives()

    def _init_default_perspectives(self):
        """Initialize default perspectives."""
        defaults = [
            Perspective(
                id="optimist",
                name="Optimist",
                description="Focuses on positive outcomes and opportunities",
                values={"positivity": 0.9, "risk_tolerance": 0.7, "innovation": 0.8},
                biases=[BiasType.OPTIMISM],
                strengths=["Motivation", "Opportunity finding"],
                weaknesses=["May overlook risks"]
            ),
            Perspective(
                id="pessimist",
                name="Pessimist",
                description="Focuses on potential problems and risks",
                values={"caution": 0.9, "risk_tolerance": 0.2, "stability": 0.8},
                biases=[BiasType.NEGATIVITY],
                strengths=["Risk identification", "Contingency planning"],
                weaknesses=["May miss opportunities"]
            ),
            Perspective(
                id="pragmatist",
                name="Pragmatist",
                description="Focuses on practical, actionable solutions",
                values={"practicality": 0.9, "efficiency": 0.8, "balance": 0.7},
                biases=[],
                strengths=["Actionable advice", "Balance"],
                weaknesses=["May lack innovation"]
            ),
            Perspective(
                id="innovator",
                name="Innovator",
                description="Focuses on novel, creative solutions",
                values={"creativity": 0.95, "risk_tolerance": 0.8, "novelty": 0.9},
                biases=[BiasType.OVERCONFIDENCE],
                strengths=["Creative solutions", "Breaking patterns"],
                weaknesses=["May overlook proven methods"]
            ),
            Perspective(
                id="analyst",
                name="Analyst",
                description="Focuses on data and logical analysis",
                values={"logic": 0.95, "evidence": 0.9, "objectivity": 0.85},
                biases=[],
                strengths=["Rigorous analysis", "Evidence-based"],
                weaknesses=["May miss intuitive insights"]
            ),
            Perspective(
                id="skeptic",
                name="Skeptic",
                description="Questions assumptions and claims",
                values={"doubt": 0.9, "evidence": 0.95, "verification": 0.9},
                biases=[],
                strengths=["Catches errors", "Verification"],
                weaknesses=["May slow progress"]
            ),
        ]

        for p in defaults:
            self.perspectives[p.id] = p

    async def analyze_from_perspective(
        self,
        topic: str,
        perspective_id: str
    ) -> Dict[str, Any]:
        """Analyze topic from a specific perspective."""
        perspective = self.perspectives.get(perspective_id)
        if not perspective:
            return {"error": f"Unknown perspective: {perspective_id}"}

        analysis = {
            "perspective": perspective.name,
            "topic": topic,
            "view": f"From {perspective.name} view: {topic}",
            "strengths_applied": perspective.strengths,
            "potential_biases": [b.value for b in perspective.biases],
            "key_values": perspective.values
        }

        return analysis

    async def multi_perspective_analysis(
        self,
        topic: str,
        perspective_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Analyze from multiple perspectives."""
        pids = perspective_ids or list(self.perspectives.keys())

        analyses = {}
        for pid in pids:
            analyses[pid] = await self.analyze_from_perspective(topic, pid)

        # Synthesize
        all_biases = set()
        all_strengths = set()
        for a in analyses.values():
            if isinstance(a.get("potential_biases"), list):
                all_biases.update(a["potential_biases"])
            if isinstance(a.get("strengths_applied"), list):
                all_strengths.update(a["strengths_applied"])

        return {
            "topic": topic,
            "perspectives_used": len(analyses),
            "individual_analyses": analyses,
            "synthesis": {
                "combined_biases_to_watch": list(all_biases),
                "combined_strengths": list(all_strengths),
                "recommendation": "Consider all perspectives for balanced view"
            }
        }


class ProblemSolver:
    """Advanced problem-solving capabilities."""

    def __init__(
        self,
        thinking_engine: ThinkingEngine,
        argument_engine: ArgumentEngine,
        perspective_engine: PerspectiveEngine
    ):
        self.thinking = thinking_engine
        self.arguments = argument_engine
        self.perspectives = perspective_engine
        self.problems: Dict[str, Problem] = {}
        self.solutions: Dict[str, List[Solution]] = {}

    async def define_problem(
        self,
        statement: str,
        context: Optional[Dict[str, Any]] = None,
        constraints: Optional[List[str]] = None,
        objectives: Optional[List[str]] = None
    ) -> Problem:
        """Define a problem to solve."""
        problem_id = hashlib.sha256(statement.encode()).hexdigest()[:16]

        problem = Problem(
            id=problem_id,
            statement=statement,
            context=context or {},
            constraints=constraints or [],
            objectives=objectives or ["Find optimal solution"]
        )

        self.problems[problem_id] = problem
        self.solutions[problem_id] = []
        return problem

    async def generate_solutions(
        self,
        problem: Problem,
        modes: Optional[List[CognitiveMode]] = None,
        num_solutions: int = 3
    ) -> List[Solution]:
        """Generate multiple solutions using different cognitive modes."""
        modes = modes or [
            CognitiveMode.ANALYTICAL,
            CognitiveMode.CREATIVE,
            CognitiveMode.HOLISTIC
        ]

        solutions = []

        for i, mode in enumerate(modes[:num_solutions]):
            # Generate thoughts for solution
            thoughts = await self.thinking.chain_thoughts(
                problem.statement,
                depth=3,
                mode=mode
            )

            # Construct solution from thoughts
            solution_id = hashlib.sha256(
                f"{problem.id}:{mode.value}:{i}".encode()
            ).hexdigest()[:16]

            steps = [t.content for t in thoughts]

            solution = Solution(
                id=solution_id,
                problem_id=problem.id,
                description=f"Solution via {mode.value} thinking",
                steps=steps,
                confidence=sum(t.confidence for t in thoughts) / len(thoughts),
                cognitive_mode_used=mode
            )

            # Analyze from multiple perspectives
            analysis = await self.perspectives.multi_perspective_analysis(
                problem.statement
            )

            # Extract pros and cons from perspectives
            for pid, pa in analysis.get("individual_analyses", {}).items():
                if "optimist" in pid:
                    solution.pros.append("Positive outlook from optimist")
                elif "pessimist" in pid:
                    solution.cons.append("Risks identified by pessimist")

            solutions.append(solution)

        self.solutions[problem.id].extend(solutions)
        return solutions

    async def evaluate_solutions(
        self,
        problem: Problem
    ) -> List[Tuple[Solution, float]]:
        """Evaluate and rank solutions."""
        problem_solutions = self.solutions.get(problem.id, [])

        evaluated = []
        for solution in problem_solutions:
            score = solution.confidence

            # Bonus for comprehensive steps
            step_bonus = min(len(solution.steps) * 0.05, 0.15)
            score += step_bonus

            # Balance pros and cons
            pro_con_balance = (len(solution.pros) - len(solution.cons)) * 0.05
            score += pro_con_balance

            # Penalty for risks
            risk_penalty = len(solution.risks) * 0.05
            score -= risk_penalty

            solution.evaluation_score = max(0.0, min(1.0, score))
            evaluated.append((solution, solution.evaluation_score))

        return sorted(evaluated, key=lambda x: -x[1])

    async def synthesize_best_solution(
        self,
        problem: Problem
    ) -> Solution:
        """Synthesize the best solution from all generated."""
        evaluated = await self.evaluate_solutions(problem)

        if not evaluated:
            return await self._generate_default_solution(problem)

        # Take best elements from top solutions
        top_solutions = [s for s, _ in evaluated[:3]]

        all_steps = []
        all_pros = []
        all_cons = []

        for sol in top_solutions:
            all_steps.extend(sol.steps)
            all_pros.extend(sol.pros)
            all_cons.extend(sol.cons)

        # Deduplicate
        unique_steps = list(dict.fromkeys(all_steps))[:5]
        unique_pros = list(set(all_pros))
        unique_cons = list(set(all_cons))

        synthesized = Solution(
            id=f"synth_{problem.id}",
            problem_id=problem.id,
            description="Synthesized optimal solution",
            steps=unique_steps,
            confidence=max(s.confidence for s in top_solutions),
            pros=unique_pros,
            cons=unique_cons,
            cognitive_mode_used=CognitiveMode.HOLISTIC,
            evaluation_score=max(s.evaluation_score for s in top_solutions)
        )

        return synthesized

    async def _generate_default_solution(self, problem: Problem) -> Solution:
        """Generate a default solution when none exist."""
        return Solution(
            id=f"default_{problem.id}",
            problem_id=problem.id,
            description="Default solution approach",
            steps=["Analyze problem", "Identify constraints", "Generate options", "Evaluate and select"],
            confidence=0.5,
            cognitive_mode_used=CognitiveMode.ANALYTICAL
        )


class CognitiveReasoningEngine:
    """
    The ultimate cognitive reasoning engine.

    Combines multiple cognitive capabilities for comprehensive
    reasoning and problem-solving.
    """

    def __init__(self):
        self.thinking = ThinkingEngine()
        self.arguments = ArgumentEngine()
        self.perspectives = PerspectiveEngine()
        self.problem_solver = ProblemSolver(
            self.thinking,
            self.arguments,
            self.perspectives
        )
        self.state = CognitiveState()
        self.reasoning_history: List[Dict[str, Any]] = []
        self.data_dir = Path("data/cognitive")
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def think(
        self,
        prompt: str,
        mode: Optional[CognitiveMode] = None,
        depth: int = 3
    ) -> Dict[str, Any]:
        """Think about a topic."""
        mode = mode or self.state.mode

        thoughts = await self.thinking.chain_thoughts(prompt, depth, mode)

        result = {
            "prompt": prompt,
            "mode": mode.value,
            "depth": depth,
            "thoughts": [
                {
                    "content": t.content,
                    "confidence": t.confidence,
                    "level": t.thinking_level.value
                }
                for t in thoughts
            ],
            "final_thought": thoughts[-1].content if thoughts else None
        }

        self.reasoning_history.append({
            "type": "think",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })

        return result

    async def argue(
        self,
        claim: str,
        premises: List[str],
        evidence: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Construct and analyze an argument."""
        argument = await self.arguments.construct_argument(claim, premises, evidence)
        counterargs = await self.arguments.counter_argument(argument)

        result = {
            "claim": claim,
            "argument_id": argument.id,
            "strength": argument.strength,
            "validity": argument.validity,
            "soundness": argument.soundness,
            "fallacies": [f.value for f in argument.fallacies],
            "counterarguments": counterargs
        }

        self.reasoning_history.append({
            "type": "argue",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })

        return result

    async def analyze_perspectives(
        self,
        topic: str,
        perspectives: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Analyze from multiple perspectives."""
        result = await self.perspectives.multi_perspective_analysis(topic, perspectives)

        self.reasoning_history.append({
            "type": "perspectives",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })

        return result

    async def solve_problem(
        self,
        statement: str,
        context: Optional[Dict[str, Any]] = None,
        constraints: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Solve a problem comprehensively."""
        # Define problem
        problem = await self.problem_solver.define_problem(
            statement, context, constraints
        )

        # Generate solutions
        solutions = await self.problem_solver.generate_solutions(problem)

        # Synthesize best
        best = await self.problem_solver.synthesize_best_solution(problem)

        result = {
            "problem": statement,
            "solutions_generated": len(solutions),
            "best_solution": {
                "description": best.description,
                "steps": best.steps,
                "confidence": best.confidence,
                "score": best.evaluation_score,
                "pros": best.pros,
                "cons": best.cons
            }
        }

        self.reasoning_history.append({
            "type": "solve",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })

        return result

    async def reason(
        self,
        query: str,
        mode: Optional[CognitiveMode] = None
    ) -> Dict[str, Any]:
        """Comprehensive reasoning about a query."""
        mode = mode or CognitiveMode.ANALYTICAL

        # Multi-modal reasoning
        thinking_result = await self.think(query, mode, depth=3)
        perspective_result = await self.analyze_perspectives(query)

        # Integrate results
        result = {
            "query": query,
            "mode": mode.value,
            "thinking": thinking_result,
            "perspectives": perspective_result,
            "synthesis": {
                "key_insight": thinking_result.get("final_thought"),
                "perspectives_considered": perspective_result.get("perspectives_used"),
                "confidence": thinking_result["thoughts"][-1]["confidence"] if thinking_result.get("thoughts") else 0.5
            }
        }

        return result

    def set_mode(self, mode: CognitiveMode) -> None:
        """Set the cognitive mode."""
        self.state.mode = mode

    def set_level(self, level: ThinkingLevel) -> None:
        """Set the thinking level."""
        self.state.level = level

    async def save_state(self, filename: str = "cognitive_state.json") -> None:
        """Save cognitive state."""
        state = {
            "mode": self.state.mode.value,
            "level": self.state.level.value,
            "focus": self.state.focus,
            "fatigue": self.state.fatigue,
            "active_thoughts": self.state.active_thoughts,
            "working_memory": self.state.working_memory,
            "reasoning_history_count": len(self.reasoning_history),
            "thoughts_count": len(self.thinking.thoughts),
            "arguments_count": len(self.arguments.arguments),
            "problems_count": len(self.problem_solver.problems)
        }

        filepath = self.data_dir / filename
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)

    async def load_state(self, filename: str = "cognitive_state.json") -> bool:
        """Load cognitive state."""
        filepath = self.data_dir / filename
        if not filepath.exists():
            return False

        try:
            with open(filepath) as f:
                state = json.load(f)

            self.state.mode = CognitiveMode(state["mode"])
            self.state.level = ThinkingLevel(state["level"])
            self.state.focus = state["focus"]
            self.state.fatigue = state["fatigue"]

            return True
        except Exception:
            return False

    def get_summary(self) -> Dict[str, Any]:
        """Get cognitive engine summary."""
        return {
            "mode": self.state.mode.value,
            "level": self.state.level.value,
            "focus": self.state.focus,
            "fatigue": self.state.fatigue,
            "total_thoughts": len(self.thinking.thoughts),
            "total_arguments": len(self.arguments.arguments),
            "total_problems": len(self.problem_solver.problems),
            "perspectives_available": len(self.perspectives.perspectives),
            "reasoning_history_count": len(self.reasoning_history)
        }


# Convenience instance
cognitive_engine = CognitiveReasoningEngine()
