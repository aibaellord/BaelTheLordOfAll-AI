"""
🎨 CREATIVE SYNTHESIS 🎨
========================
Synthesize creative solutions.

Features:
- Constraint handling
- Divergent thinking
- Solution synthesis
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set
import uuid
import random

from .creativity_core import Idea, IdeaType, CreativityMode, CreativeSpace


class ConstraintType(Enum):
    """Types of creative constraints"""
    MUST_HAVE = auto()       # Required
    NICE_TO_HAVE = auto()    # Preferred
    MUST_NOT_HAVE = auto()   # Prohibited
    RANGE = auto()           # Within bounds
    RELATIONSHIP = auto()    # Relational constraint


@dataclass
class CreativeConstraint:
    """A constraint on creative solutions"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    name: str = ""
    constraint_type: ConstraintType = ConstraintType.MUST_HAVE

    # Constraint specification
    property_name: str = ""
    target_value: Any = None
    min_value: float = None
    max_value: float = None

    # Weight (for soft constraints)
    weight: float = 1.0

    # Is hard constraint?
    is_hard: bool = True

    def check(self, idea: Idea) -> Tuple[bool, float]:
        """Check constraint satisfaction"""
        if self.property_name in idea.__dict__:
            value = getattr(idea, self.property_name)
        elif hasattr(idea, 'content') and isinstance(idea.content, dict):
            value = idea.content.get(self.property_name)
        else:
            return (False, 0.0) if self.is_hard else (True, 0.5)

        if self.constraint_type == ConstraintType.MUST_HAVE:
            satisfied = value == self.target_value
            return (satisfied, 1.0 if satisfied else 0.0)

        elif self.constraint_type == ConstraintType.MUST_NOT_HAVE:
            satisfied = value != self.target_value
            return (satisfied, 1.0 if satisfied else 0.0)

        elif self.constraint_type == ConstraintType.RANGE:
            if isinstance(value, (int, float)):
                in_range = True
                if self.min_value is not None:
                    in_range = in_range and value >= self.min_value
                if self.max_value is not None:
                    in_range = in_range and value <= self.max_value
                return (in_range, 1.0 if in_range else 0.0)

        return (True, 0.5)


from typing import Tuple


class SolutionSpace:
    """
    Space of possible solutions.
    """

    def __init__(self):
        self.constraints: List[CreativeConstraint] = []
        self.solutions: List[Idea] = []

        # Pareto front of solutions
        self.pareto_front: List[Idea] = []

    def add_constraint(self, constraint: CreativeConstraint):
        """Add constraint"""
        self.constraints.append(constraint)

    def evaluate(self, idea: Idea) -> Dict[str, Any]:
        """Evaluate solution against constraints"""
        results = {
            'satisfies_all_hard': True,
            'hard_satisfied': 0,
            'hard_total': 0,
            'soft_score': 0.0,
            'soft_total': 0.0,
            'violations': []
        }

        for constraint in self.constraints:
            satisfied, score = constraint.check(idea)

            if constraint.is_hard:
                results['hard_total'] += 1
                if satisfied:
                    results['hard_satisfied'] += 1
                else:
                    results['satisfies_all_hard'] = False
                    results['violations'].append(constraint.name)
            else:
                results['soft_total'] += constraint.weight
                results['soft_score'] += score * constraint.weight

        return results

    def is_feasible(self, idea: Idea) -> bool:
        """Check if solution is feasible"""
        evaluation = self.evaluate(idea)
        return evaluation['satisfies_all_hard']

    def add_solution(self, idea: Idea):
        """Add solution if feasible"""
        if self.is_feasible(idea):
            self.solutions.append(idea)
            self._update_pareto_front(idea)

    def _update_pareto_front(self, new_idea: Idea):
        """Update Pareto front with new solution"""
        # Check if new idea dominates any in front
        dominated = []
        for existing in self.pareto_front:
            if self._dominates(new_idea, existing):
                dominated.append(existing)

        # Remove dominated
        for d in dominated:
            self.pareto_front.remove(d)

        # Check if new idea is dominated
        for existing in self.pareto_front:
            if self._dominates(existing, new_idea):
                return  # New idea is dominated

        # Add to front
        self.pareto_front.append(new_idea)

    def _dominates(self, idea1: Idea, idea2: Idea) -> bool:
        """Check if idea1 dominates idea2 (better in all objectives)"""
        objectives = ['novelty', 'quality', 'feasibility']

        better_in_any = False
        for obj in objectives:
            v1 = getattr(idea1, obj, 0)
            v2 = getattr(idea2, obj, 0)

            if v1 < v2:
                return False
            if v1 > v2:
                better_in_any = True

        return better_in_any


class DivergentThinker:
    """
    Divergent thinking strategies.
    """

    def __init__(self):
        self.strategies: Dict[str, Callable[[Idea], List[Idea]]] = {}

        # Initialize default strategies
        self._init_strategies()

    def _init_strategies(self):
        """Initialize divergent thinking strategies"""

        # SCAMPER strategies
        self.strategies['substitute'] = self._substitute
        self.strategies['combine'] = self._combine
        self.strategies['adapt'] = self._adapt
        self.strategies['modify'] = self._modify
        self.strategies['put_to_other_uses'] = self._other_uses
        self.strategies['eliminate'] = self._eliminate
        self.strategies['reverse'] = self._reverse

    def _substitute(self, idea: Idea) -> List[Idea]:
        """Substitute components"""
        variants = []

        # Create variant with substituted elements
        variant = Idea(
            content=f"substitute_{idea.content}" if isinstance(idea.content, str) else idea.content,
            description=f"Substituted version of: {idea.description}",
            idea_type=IdeaType.TRANSFORMATION,
            parent_ideas=[idea.id],
            generation_method="substitute"
        )
        variants.append(variant)

        return variants

    def _combine(self, idea: Idea) -> List[Idea]:
        """Combine with other elements"""
        variants = []

        combiners = ["technology", "nature", "art", "science", "culture"]

        for combiner in combiners[:3]:
            variant = Idea(
                content=f"{idea.content} + {combiner}",
                description=f"Combined with {combiner}",
                idea_type=IdeaType.COMBINATION,
                parent_ideas=[idea.id],
                generation_method="combine"
            )
            variants.append(variant)

        return variants

    def _adapt(self, idea: Idea) -> List[Idea]:
        """Adapt to new contexts"""
        variants = []

        contexts = ["mobile", "cloud", "distributed", "embedded", "quantum"]

        for context in contexts[:3]:
            variant = Idea(
                content=f"{idea.content} for {context}",
                description=f"Adapted for {context} context",
                idea_type=IdeaType.TRANSFORMATION,
                parent_ideas=[idea.id],
                generation_method="adapt"
            )
            variants.append(variant)

        return variants

    def _modify(self, idea: Idea) -> List[Idea]:
        """Modify aspects"""
        variants = []

        modifications = ["larger", "smaller", "faster", "simpler", "more powerful"]

        for mod in modifications[:3]:
            variant = Idea(
                content=f"{mod} {idea.content}",
                description=f"Modified to be {mod}",
                idea_type=IdeaType.TRANSFORMATION,
                parent_ideas=[idea.id],
                generation_method="modify"
            )
            variants.append(variant)

        return variants

    def _other_uses(self, idea: Idea) -> List[Idea]:
        """Find other uses"""
        variants = []

        domains = ["healthcare", "education", "entertainment", "security", "finance"]

        for domain in domains[:3]:
            variant = Idea(
                content=f"{idea.content} for {domain}",
                description=f"Applied to {domain}",
                idea_type=IdeaType.TRANSFORMATION,
                parent_ideas=[idea.id],
                generation_method="other_uses"
            )
            variants.append(variant)

        return variants

    def _eliminate(self, idea: Idea) -> List[Idea]:
        """Eliminate components"""
        variants = []

        variant = Idea(
            content=f"minimal {idea.content}",
            description="Simplified by elimination",
            idea_type=IdeaType.TRANSFORMATION,
            parent_ideas=[idea.id],
            generation_method="eliminate"
        )
        variants.append(variant)

        return variants

    def _reverse(self, idea: Idea) -> List[Idea]:
        """Reverse/invert"""
        variants = []

        variant = Idea(
            content=f"inverted {idea.content}",
            description="Reversed/inverted approach",
            idea_type=IdeaType.INVERSION,
            parent_ideas=[idea.id],
            generation_method="reverse"
        )
        variants.append(variant)

        return variants

    def diverge(
        self,
        idea: Idea,
        strategies: List[str] = None
    ) -> List[Idea]:
        """Apply divergent thinking"""
        all_variants = []

        strategies = strategies or list(self.strategies.keys())

        for strategy_name in strategies:
            if strategy_name in self.strategies:
                variants = self.strategies[strategy_name](idea)
                all_variants.extend(variants)

        return all_variants


class CreativeSynthesizer:
    """
    Synthesizes creative solutions.
    """

    def __init__(self):
        self.creative_space = CreativeSpace()
        self.solution_space = SolutionSpace()
        self.divergent_thinker = DivergentThinker()

        # Synthesis methods
        self.methods: List[str] = [
            "evolutionary",
            "divergent",
            "constraint_relaxation",
            "analogical",
            "random"
        ]

    def synthesize(
        self,
        problem: str,
        constraints: List[CreativeConstraint] = None,
        n_solutions: int = 10,
        method: str = "evolutionary"
    ) -> List[Idea]:
        """Synthesize solutions to problem"""
        # Set up constraints
        if constraints:
            for c in constraints:
                self.solution_space.add_constraint(c)

        if method == "evolutionary":
            return self._evolutionary_synthesis(problem, n_solutions)
        elif method == "divergent":
            return self._divergent_synthesis(problem, n_solutions)
        elif method == "constraint_relaxation":
            return self._relaxation_synthesis(problem, n_solutions)
        else:
            return self._random_synthesis(problem, n_solutions)

    def _evolutionary_synthesis(
        self,
        problem: str,
        n_solutions: int
    ) -> List[Idea]:
        """Evolutionary approach"""
        population = []

        # Initial population
        for i in range(n_solutions * 2):
            idea = Idea(
                content=f"solution_{i}_for_{problem}",
                description=f"Candidate solution {i}",
                idea_type=IdeaType.SOLUTION,
                novelty=random.random(),
                quality=random.random(),
                feasibility=random.random()
            )
            population.append(idea)

        # Evolution
        for generation in range(10):
            # Evaluate and sort
            population.sort(key=lambda i: i.get_fitness(), reverse=True)

            # Select top half
            survivors = population[:len(population) // 2]

            # Crossover and mutation
            children = []
            while len(children) < len(population) - len(survivors):
                parent = random.choice(survivors)

                # Mutate via divergent thinking
                variants = self.divergent_thinker.diverge(parent, ['modify', 'combine'])
                if variants:
                    child = variants[0]
                    child.novelty = random.random()
                    child.quality = parent.quality * (0.8 + 0.4 * random.random())
                    child.feasibility = parent.feasibility * (0.8 + 0.4 * random.random())
                    children.append(child)

            population = survivors + children

        # Return best feasible
        feasible = [i for i in population if self.solution_space.is_feasible(i)]
        feasible.sort(key=lambda i: i.get_fitness(), reverse=True)

        return feasible[:n_solutions] if feasible else population[:n_solutions]

    def _divergent_synthesis(
        self,
        problem: str,
        n_solutions: int
    ) -> List[Idea]:
        """Divergent thinking approach"""
        # Start with seed idea
        seed = Idea(
            content=problem,
            description="Seed idea",
            idea_type=IdeaType.CONCEPT
        )

        # Apply all divergent strategies
        all_variants = self.divergent_thinker.diverge(seed)

        # Second level divergence
        for variant in all_variants[:5]:
            more_variants = self.divergent_thinker.diverge(variant, ['modify', 'adapt'])
            all_variants.extend(more_variants)

        # Evaluate
        for idea in all_variants:
            idea.novelty = random.random()
            idea.quality = random.random()
            idea.feasibility = random.random()

        # Return most novel
        all_variants.sort(key=lambda i: i.novelty, reverse=True)
        return all_variants[:n_solutions]

    def _relaxation_synthesis(
        self,
        problem: str,
        n_solutions: int
    ) -> List[Idea]:
        """Constraint relaxation approach"""
        solutions = []

        # Start with strict constraints, relax if needed
        for i in range(n_solutions):
            idea = Idea(
                content=f"relaxed_solution_{i}",
                description=f"Solution with relaxed constraints",
                idea_type=IdeaType.SOLUTION,
                novelty=random.random(),
                quality=0.8,
                feasibility=0.9
            )
            solutions.append(idea)

        return solutions

    def _random_synthesis(
        self,
        problem: str,
        n_solutions: int
    ) -> List[Idea]:
        """Random exploration"""
        solutions = []

        for i in range(n_solutions * 3):
            idea = Idea(
                content=f"random_solution_{i}",
                description=f"Random solution {i}",
                idea_type=IdeaType.SOLUTION,
                novelty=random.random(),
                quality=random.random(),
                feasibility=random.random()
            )

            if self.solution_space.is_feasible(idea):
                solutions.append(idea)

                if len(solutions) >= n_solutions:
                    break

        return solutions


# Export all
__all__ = [
    'ConstraintType',
    'CreativeConstraint',
    'SolutionSpace',
    'DivergentThinker',
    'CreativeSynthesizer',
]
