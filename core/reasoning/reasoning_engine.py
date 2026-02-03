#!/usr/bin/env python3
"""
BAEL - Reasoning Engine
Advanced reasoning and inference for AI agents.

Features:
- Logical inference
- Deductive reasoning
- Inductive reasoning
- Abductive reasoning
- Analogical reasoning
- Causal reasoning
- Probabilistic reasoning
- Constraint satisfaction
"""

import asyncio
import copy
import hashlib
import json
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ReasoningType(Enum):
    """Reasoning types."""
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    ANALOGICAL = "analogical"
    CAUSAL = "causal"
    PROBABILISTIC = "probabilistic"


class LogicalOperator(Enum):
    """Logical operators."""
    AND = "and"
    OR = "or"
    NOT = "not"
    IMPLIES = "implies"
    IFF = "iff"


class TruthValue(Enum):
    """Truth values."""
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"


class InferenceDirection(Enum):
    """Inference direction."""
    FORWARD = "forward"
    BACKWARD = "backward"


class ConstraintType(Enum):
    """Constraint types."""
    UNARY = "unary"
    BINARY = "binary"
    GLOBAL = "global"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Proposition:
    """Logical proposition."""
    prop_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    value: TruthValue = TruthValue.UNKNOWN
    confidence: float = 1.0
    evidence: List[str] = field(default_factory=list)


@dataclass
class Rule:
    """Inference rule."""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    antecedent: List[str] = field(default_factory=list)  # proposition names
    consequent: List[str] = field(default_factory=list)  # proposition names
    confidence: float = 1.0
    operator: LogicalOperator = LogicalOperator.AND


@dataclass
class Argument:
    """Reasoning argument."""
    arg_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    premises: List[str] = field(default_factory=list)
    conclusion: str = ""
    reasoning_type: ReasoningType = ReasoningType.DEDUCTIVE
    strength: float = 1.0
    valid: bool = False


@dataclass
class CausalLink:
    """Causal relationship."""
    cause: str
    effect: str
    strength: float = 1.0
    mechanism: str = ""
    confounders: List[str] = field(default_factory=list)


@dataclass
class Analogy:
    """Analogical mapping."""
    source_domain: str = ""
    target_domain: str = ""
    mappings: Dict[str, str] = field(default_factory=dict)
    similarity: float = 0.0


@dataclass
class Constraint:
    """Reasoning constraint."""
    constraint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    constraint_type: ConstraintType = ConstraintType.UNARY
    variables: List[str] = field(default_factory=list)
    predicate: Optional[Callable] = None


@dataclass
class InferenceResult:
    """Inference result."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conclusion: str = ""
    confidence: float = 0.0
    reasoning_type: ReasoningType = ReasoningType.DEDUCTIVE
    derivation: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


# =============================================================================
# KNOWLEDGE BASE
# =============================================================================

class KnowledgeBase:
    """Knowledge base for reasoning."""

    def __init__(self):
        self._propositions: Dict[str, Proposition] = {}
        self._rules: Dict[str, Rule] = {}
        self._facts: Set[str] = set()

    def add_proposition(
        self,
        name: str,
        value: TruthValue = TruthValue.UNKNOWN,
        confidence: float = 1.0
    ) -> Proposition:
        """Add proposition."""
        prop = Proposition(
            name=name,
            value=value,
            confidence=confidence
        )
        self._propositions[name] = prop

        if value == TruthValue.TRUE:
            self._facts.add(name)
        elif value == TruthValue.FALSE:
            self._facts.discard(name)

        return prop

    def get_proposition(self, name: str) -> Optional[Proposition]:
        """Get proposition."""
        return self._propositions.get(name)

    def set_value(
        self,
        name: str,
        value: TruthValue,
        confidence: float = 1.0
    ) -> None:
        """Set proposition value."""
        if name in self._propositions:
            self._propositions[name].value = value
            self._propositions[name].confidence = confidence

            if value == TruthValue.TRUE:
                self._facts.add(name)
            else:
                self._facts.discard(name)

    def add_rule(
        self,
        name: str,
        antecedent: List[str],
        consequent: List[str],
        confidence: float = 1.0,
        operator: LogicalOperator = LogicalOperator.AND
    ) -> Rule:
        """Add inference rule."""
        rule = Rule(
            name=name,
            antecedent=antecedent,
            consequent=consequent,
            confidence=confidence,
            operator=operator
        )
        self._rules[name] = rule
        return rule

    def get_rule(self, name: str) -> Optional[Rule]:
        """Get rule."""
        return self._rules.get(name)

    def get_facts(self) -> Set[str]:
        """Get known facts."""
        return self._facts.copy()

    def get_rules(self) -> List[Rule]:
        """Get all rules."""
        return list(self._rules.values())

    def is_true(self, name: str) -> bool:
        """Check if proposition is true."""
        return name in self._facts

    def is_false(self, name: str) -> bool:
        """Check if proposition is false."""
        prop = self._propositions.get(name)
        return prop is not None and prop.value == TruthValue.FALSE


# =============================================================================
# FORWARD CHAINING
# =============================================================================

class ForwardChainer:
    """Forward chaining inference."""

    def __init__(self, kb: KnowledgeBase):
        self._kb = kb

    def infer(self, max_iterations: int = 100) -> List[str]:
        """Perform forward chaining inference."""
        inferred = []
        changed = True
        iteration = 0

        while changed and iteration < max_iterations:
            changed = False
            iteration += 1

            for rule in self._kb.get_rules():
                if self._matches(rule):
                    for consequent in rule.consequent:
                        if not self._kb.is_true(consequent):
                            self._kb.set_value(consequent, TruthValue.TRUE, rule.confidence)
                            inferred.append(consequent)
                            changed = True

        return inferred

    def _matches(self, rule: Rule) -> bool:
        """Check if rule antecedent matches."""
        if rule.operator == LogicalOperator.AND:
            return all(self._kb.is_true(p) for p in rule.antecedent)
        elif rule.operator == LogicalOperator.OR:
            return any(self._kb.is_true(p) for p in rule.antecedent)
        return False


# =============================================================================
# BACKWARD CHAINING
# =============================================================================

class BackwardChainer:
    """Backward chaining inference."""

    def __init__(self, kb: KnowledgeBase):
        self._kb = kb
        self._visited: Set[str] = set()

    def prove(self, goal: str) -> Tuple[bool, List[str]]:
        """Prove goal using backward chaining."""
        self._visited = set()
        derivation = []
        result = self._prove_goal(goal, derivation)
        return result, derivation

    def _prove_goal(self, goal: str, derivation: List[str]) -> bool:
        """Recursively prove goal."""
        if goal in self._visited:
            return False
        self._visited.add(goal)

        # Check if already known
        if self._kb.is_true(goal):
            derivation.append(f"FACT: {goal}")
            return True

        # Try to derive from rules
        for rule in self._kb.get_rules():
            if goal in rule.consequent:
                derivation.append(f"APPLY: {rule.name}")

                if rule.operator == LogicalOperator.AND:
                    all_proven = True
                    for antecedent in rule.antecedent:
                        if not self._prove_goal(antecedent, derivation):
                            all_proven = False
                            break
                    if all_proven:
                        derivation.append(f"CONCLUDE: {goal}")
                        return True

                elif rule.operator == LogicalOperator.OR:
                    for antecedent in rule.antecedent:
                        if self._prove_goal(antecedent, derivation):
                            derivation.append(f"CONCLUDE: {goal}")
                            return True

        return False


# =============================================================================
# INDUCTIVE REASONER
# =============================================================================

class InductiveReasoner:
    """Inductive reasoning from examples."""

    def __init__(self):
        self._examples: List[Dict[str, Any]] = []
        self._patterns: Dict[str, float] = {}

    def add_example(self, example: Dict[str, Any]) -> None:
        """Add training example."""
        self._examples.append(example)

    def induce_pattern(
        self,
        attribute: str,
        value: Any
    ) -> float:
        """Induce probability of attribute having value."""
        if not self._examples:
            return 0.0

        count = sum(
            1 for ex in self._examples
            if ex.get(attribute) == value
        )

        probability = count / len(self._examples)
        pattern_key = f"{attribute}={value}"
        self._patterns[pattern_key] = probability

        return probability

    def induce_correlation(
        self,
        attr1: str,
        val1: Any,
        attr2: str,
        val2: Any
    ) -> float:
        """Induce correlation between attributes."""
        if not self._examples:
            return 0.0

        both = sum(
            1 for ex in self._examples
            if ex.get(attr1) == val1 and ex.get(attr2) == val2
        )

        cond1 = sum(1 for ex in self._examples if ex.get(attr1) == val1)

        if cond1 == 0:
            return 0.0

        return both / cond1

    def generalize(
        self,
        attributes: List[str]
    ) -> Dict[str, Dict[Any, float]]:
        """Generalize patterns from examples."""
        patterns = defaultdict(lambda: defaultdict(float))

        for attr in attributes:
            values = set(ex.get(attr) for ex in self._examples if attr in ex)
            for value in values:
                prob = self.induce_pattern(attr, value)
                patterns[attr][value] = prob

        return dict(patterns)


# =============================================================================
# ABDUCTIVE REASONER
# =============================================================================

class AbductiveReasoner:
    """Abductive reasoning (inference to best explanation)."""

    def __init__(self, kb: KnowledgeBase):
        self._kb = kb

    def explain(
        self,
        observation: str,
        candidates: List[str]
    ) -> List[Tuple[str, float]]:
        """Find best explanations for observation."""
        explanations = []

        for candidate in candidates:
            score = self._score_explanation(candidate, observation)
            if score > 0:
                explanations.append((candidate, score))

        return sorted(explanations, key=lambda x: x[1], reverse=True)

    def _score_explanation(
        self,
        hypothesis: str,
        observation: str
    ) -> float:
        """Score how well hypothesis explains observation."""
        score = 0.0

        # Check if hypothesis implies observation
        for rule in self._kb.get_rules():
            if hypothesis in rule.antecedent and observation in rule.consequent:
                score += rule.confidence

        # Check simplicity (fewer assumptions = higher score)
        prop = self._kb.get_proposition(hypothesis)
        if prop:
            score *= prop.confidence

        return score

    def abduce(
        self,
        observations: List[str]
    ) -> List[str]:
        """Abduce hypotheses from observations."""
        hypotheses = set()

        for obs in observations:
            for rule in self._kb.get_rules():
                if obs in rule.consequent:
                    hypotheses.update(rule.antecedent)

        return list(hypotheses)


# =============================================================================
# CAUSAL REASONER
# =============================================================================

class CausalReasoner:
    """Causal reasoning."""

    def __init__(self):
        self._causal_links: Dict[str, List[CausalLink]] = defaultdict(list)
        self._effects: Dict[str, List[CausalLink]] = defaultdict(list)

    def add_causal_link(
        self,
        cause: str,
        effect: str,
        strength: float = 1.0,
        mechanism: str = ""
    ) -> CausalLink:
        """Add causal link."""
        link = CausalLink(
            cause=cause,
            effect=effect,
            strength=strength,
            mechanism=mechanism
        )

        self._causal_links[cause].append(link)
        self._effects[effect].append(link)

        return link

    def get_effects(self, cause: str) -> List[CausalLink]:
        """Get effects of cause."""
        return self._causal_links.get(cause, [])

    def get_causes(self, effect: str) -> List[CausalLink]:
        """Get causes of effect."""
        return self._effects.get(effect, [])

    def trace_causal_chain(
        self,
        start: str,
        max_depth: int = 10
    ) -> List[List[str]]:
        """Trace causal chains from start."""
        chains = []

        def trace(current: str, chain: List[str], depth: int) -> None:
            if depth >= max_depth:
                return

            effects = self._causal_links.get(current, [])

            if not effects:
                if len(chain) > 1:
                    chains.append(chain.copy())
                return

            for link in effects:
                new_chain = chain + [link.effect]
                trace(link.effect, new_chain, depth + 1)

        trace(start, [start], 0)
        return chains

    def infer_intervention(
        self,
        intervention: str,
        value: bool
    ) -> Dict[str, float]:
        """Infer effects of intervention."""
        effects = {}

        def propagate(cause: str, prob: float, visited: Set[str]) -> None:
            if cause in visited:
                return
            visited.add(cause)

            for link in self._causal_links.get(cause, []):
                effect_prob = prob * link.strength

                if link.effect not in effects or effects[link.effect] < effect_prob:
                    effects[link.effect] = effect_prob

                propagate(link.effect, effect_prob, visited)

        initial_prob = 1.0 if value else 0.0
        propagate(intervention, initial_prob, set())

        return effects


# =============================================================================
# ANALOGICAL REASONER
# =============================================================================

class AnalogicalReasoner:
    """Analogical reasoning."""

    def __init__(self):
        self._domains: Dict[str, Dict[str, Any]] = {}

    def add_domain(self, name: str, structure: Dict[str, Any]) -> None:
        """Add domain."""
        self._domains[name] = structure

    def find_analogy(
        self,
        source_domain: str,
        target_domain: str
    ) -> Analogy:
        """Find analogy between domains."""
        source = self._domains.get(source_domain, {})
        target = self._domains.get(target_domain, {})

        mappings = {}
        matches = 0
        total = 0

        for source_key in source:
            total += 1
            if source_key in target:
                mappings[source_key] = source_key
                matches += 1
            else:
                # Try to find similar key
                for target_key in target:
                    if self._similar(source_key, target_key):
                        mappings[source_key] = target_key
                        matches += 0.5
                        break

        similarity = matches / total if total > 0 else 0.0

        return Analogy(
            source_domain=source_domain,
            target_domain=target_domain,
            mappings=mappings,
            similarity=similarity
        )

    def transfer(
        self,
        analogy: Analogy,
        source_property: str
    ) -> Optional[str]:
        """Transfer property through analogy."""
        return analogy.mappings.get(source_property)

    def _similar(self, s1: str, s2: str) -> bool:
        """Check if strings are similar."""
        # Simple similarity check
        s1_lower = s1.lower()
        s2_lower = s2.lower()

        if s1_lower in s2_lower or s2_lower in s1_lower:
            return True

        # Check for common substring
        common = set(s1_lower.split("_")) & set(s2_lower.split("_"))
        return len(common) > 0


# =============================================================================
# PROBABILISTIC REASONER
# =============================================================================

class ProbabilisticReasoner:
    """Probabilistic reasoning."""

    def __init__(self):
        self._priors: Dict[str, float] = {}
        self._conditionals: Dict[Tuple[str, str], float] = {}

    def set_prior(self, event: str, probability: float) -> None:
        """Set prior probability."""
        self._priors[event] = probability

    def set_conditional(
        self,
        event: str,
        given: str,
        probability: float
    ) -> None:
        """Set conditional probability P(event|given)."""
        self._conditionals[(event, given)] = probability

    def get_prior(self, event: str) -> float:
        """Get prior probability."""
        return self._priors.get(event, 0.5)

    def get_conditional(self, event: str, given: str) -> float:
        """Get conditional probability."""
        return self._conditionals.get((event, given), self.get_prior(event))

    def bayes_update(
        self,
        hypothesis: str,
        evidence: str
    ) -> float:
        """Apply Bayes' theorem."""
        prior = self.get_prior(hypothesis)
        likelihood = self.get_conditional(evidence, hypothesis)

        # Calculate P(evidence)
        p_evidence = 0.0
        for h, p_h in self._priors.items():
            p_e_given_h = self.get_conditional(evidence, h)
            p_evidence += p_e_given_h * p_h

        if p_evidence == 0:
            return prior

        posterior = (likelihood * prior) / p_evidence
        return posterior

    def chain_rule(self, events: List[str]) -> float:
        """Apply chain rule of probability."""
        if not events:
            return 1.0

        prob = self.get_prior(events[0])

        for i in range(1, len(events)):
            # P(A, B) = P(B|A) * P(A)
            conditional = self.get_conditional(events[i], events[i-1])
            prob *= conditional

        return prob


# =============================================================================
# CONSTRAINT SOLVER
# =============================================================================

class ConstraintSolver:
    """Constraint satisfaction solver."""

    def __init__(self):
        self._variables: Dict[str, List[Any]] = {}
        self._constraints: List[Constraint] = []

    def add_variable(self, name: str, domain: List[Any]) -> None:
        """Add variable with domain."""
        self._variables[name] = domain.copy()

    def add_constraint(
        self,
        name: str,
        variables: List[str],
        predicate: Callable
    ) -> Constraint:
        """Add constraint."""
        constraint = Constraint(
            name=name,
            constraint_type=ConstraintType.UNARY if len(variables) == 1 else ConstraintType.BINARY,
            variables=variables,
            predicate=predicate
        )
        self._constraints.append(constraint)
        return constraint

    def solve(self) -> Optional[Dict[str, Any]]:
        """Solve CSP using backtracking."""
        assignment = {}
        return self._backtrack(assignment)

    def _backtrack(
        self,
        assignment: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Backtracking search."""
        if len(assignment) == len(self._variables):
            return assignment

        var = self._select_variable(assignment)

        for value in self._variables[var]:
            if self._is_consistent(var, value, assignment):
                assignment[var] = value
                result = self._backtrack(assignment)
                if result is not None:
                    return result
                del assignment[var]

        return None

    def _select_variable(
        self,
        assignment: Dict[str, Any]
    ) -> str:
        """Select unassigned variable."""
        for var in self._variables:
            if var not in assignment:
                return var
        return list(self._variables.keys())[0]

    def _is_consistent(
        self,
        var: str,
        value: Any,
        assignment: Dict[str, Any]
    ) -> bool:
        """Check if assignment is consistent."""
        test_assignment = assignment.copy()
        test_assignment[var] = value

        for constraint in self._constraints:
            if var not in constraint.variables:
                continue

            # Check if all constraint variables are assigned
            if not all(v in test_assignment for v in constraint.variables):
                continue

            values = [test_assignment[v] for v in constraint.variables]

            if not constraint.predicate(*values):
                return False

        return True


# =============================================================================
# REASONING ENGINE
# =============================================================================

class ReasoningEngine:
    """
    Reasoning Engine for BAEL.

    Advanced reasoning and inference.
    """

    def __init__(self):
        self._kb = KnowledgeBase()
        self._forward_chainer = ForwardChainer(self._kb)
        self._backward_chainer = BackwardChainer(self._kb)
        self._inductive = InductiveReasoner()
        self._abductive = AbductiveReasoner(self._kb)
        self._causal = CausalReasoner()
        self._analogical = AnalogicalReasoner()
        self._probabilistic = ProbabilisticReasoner()
        self._constraint_solver = ConstraintSolver()

    # -------------------------------------------------------------------------
    # KNOWLEDGE BASE
    # -------------------------------------------------------------------------

    def add_fact(self, name: str, confidence: float = 1.0) -> Proposition:
        """Add fact."""
        return self._kb.add_proposition(name, TruthValue.TRUE, confidence)

    def add_negation(self, name: str, confidence: float = 1.0) -> Proposition:
        """Add negation."""
        return self._kb.add_proposition(name, TruthValue.FALSE, confidence)

    def add_rule(
        self,
        name: str,
        if_conditions: List[str],
        then_conclusions: List[str],
        confidence: float = 1.0,
        operator: str = "and"
    ) -> Rule:
        """Add inference rule."""
        op = LogicalOperator.AND if operator.lower() == "and" else LogicalOperator.OR
        return self._kb.add_rule(name, if_conditions, then_conclusions, confidence, op)

    def is_true(self, proposition: str) -> bool:
        """Check if proposition is true."""
        return self._kb.is_true(proposition)

    # -------------------------------------------------------------------------
    # DEDUCTIVE
    # -------------------------------------------------------------------------

    def forward_chain(self) -> List[str]:
        """Perform forward chaining."""
        return self._forward_chainer.infer()

    def prove(self, goal: str) -> InferenceResult:
        """Prove goal using backward chaining."""
        proven, derivation = self._backward_chainer.prove(goal)

        return InferenceResult(
            conclusion=goal,
            confidence=1.0 if proven else 0.0,
            reasoning_type=ReasoningType.DEDUCTIVE,
            derivation=derivation
        )

    # -------------------------------------------------------------------------
    # INDUCTIVE
    # -------------------------------------------------------------------------

    def add_example(self, example: Dict[str, Any]) -> None:
        """Add inductive example."""
        self._inductive.add_example(example)

    def induce_pattern(
        self,
        attribute: str,
        value: Any
    ) -> float:
        """Induce pattern probability."""
        return self._inductive.induce_pattern(attribute, value)

    def generalize(self, attributes: List[str]) -> Dict[str, Dict[Any, float]]:
        """Generalize from examples."""
        return self._inductive.generalize(attributes)

    # -------------------------------------------------------------------------
    # ABDUCTIVE
    # -------------------------------------------------------------------------

    def explain(
        self,
        observation: str,
        candidates: List[str]
    ) -> List[Tuple[str, float]]:
        """Find explanations."""
        return self._abductive.explain(observation, candidates)

    def abduce_hypotheses(
        self,
        observations: List[str]
    ) -> List[str]:
        """Abduce hypotheses."""
        return self._abductive.abduce(observations)

    # -------------------------------------------------------------------------
    # CAUSAL
    # -------------------------------------------------------------------------

    def add_causal_link(
        self,
        cause: str,
        effect: str,
        strength: float = 1.0
    ) -> CausalLink:
        """Add causal link."""
        return self._causal.add_causal_link(cause, effect, strength)

    def get_effects(self, cause: str) -> List[str]:
        """Get effects of cause."""
        links = self._causal.get_effects(cause)
        return [l.effect for l in links]

    def get_causes(self, effect: str) -> List[str]:
        """Get causes of effect."""
        links = self._causal.get_causes(effect)
        return [l.cause for l in links]

    def trace_causality(self, start: str) -> List[List[str]]:
        """Trace causal chains."""
        return self._causal.trace_causal_chain(start)

    def intervene(
        self,
        variable: str,
        value: bool
    ) -> Dict[str, float]:
        """Infer intervention effects."""
        return self._causal.infer_intervention(variable, value)

    # -------------------------------------------------------------------------
    # ANALOGICAL
    # -------------------------------------------------------------------------

    def add_domain(self, name: str, structure: Dict[str, Any]) -> None:
        """Add domain."""
        self._analogical.add_domain(name, structure)

    def find_analogy(
        self,
        source: str,
        target: str
    ) -> Analogy:
        """Find analogy."""
        return self._analogical.find_analogy(source, target)

    # -------------------------------------------------------------------------
    # PROBABILISTIC
    # -------------------------------------------------------------------------

    def set_prior(self, event: str, probability: float) -> None:
        """Set prior probability."""
        self._probabilistic.set_prior(event, probability)

    def set_conditional(
        self,
        event: str,
        given: str,
        probability: float
    ) -> None:
        """Set conditional probability."""
        self._probabilistic.set_conditional(event, given, probability)

    def bayes_update(
        self,
        hypothesis: str,
        evidence: str
    ) -> float:
        """Bayesian update."""
        return self._probabilistic.bayes_update(hypothesis, evidence)

    # -------------------------------------------------------------------------
    # CONSTRAINT SATISFACTION
    # -------------------------------------------------------------------------

    def add_variable(self, name: str, domain: List[Any]) -> None:
        """Add CSP variable."""
        self._constraint_solver.add_variable(name, domain)

    def add_constraint(
        self,
        name: str,
        variables: List[str],
        predicate: Callable
    ) -> Constraint:
        """Add constraint."""
        return self._constraint_solver.add_constraint(name, variables, predicate)

    def solve_constraints(self) -> Optional[Dict[str, Any]]:
        """Solve CSP."""
        return self._constraint_solver.solve()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Reasoning Engine."""
    print("=" * 70)
    print("BAEL - REASONING ENGINE DEMO")
    print("Advanced Reasoning and Inference")
    print("=" * 70)
    print()

    engine = ReasoningEngine()

    # 1. Deductive Reasoning - Forward Chaining
    print("1. FORWARD CHAINING:")
    print("-" * 40)

    engine.add_fact("is_mammal")
    engine.add_fact("has_feathers")

    engine.add_rule("bird_rule", ["has_feathers"], ["can_fly"], confidence=0.9)
    engine.add_rule("mammal_rule", ["is_mammal"], ["is_warm_blooded"])

    inferred = engine.forward_chain()

    print(f"   Facts: is_mammal, has_feathers")
    print(f"   Inferred: {inferred}")
    print()

    # 2. Backward Chaining
    print("2. BACKWARD CHAINING:")
    print("-" * 40)

    result = engine.prove("is_warm_blooded")

    print(f"   Goal: is_warm_blooded")
    print(f"   Proven: {result.confidence > 0}")
    print(f"   Derivation: {result.derivation}")
    print()

    # 3. Inductive Reasoning
    print("3. INDUCTIVE REASONING:")
    print("-" * 40)

    engine.add_example({"color": "red", "shape": "round", "fruit": "apple"})
    engine.add_example({"color": "red", "shape": "round", "fruit": "cherry"})
    engine.add_example({"color": "yellow", "shape": "curved", "fruit": "banana"})
    engine.add_example({"color": "red", "shape": "round", "fruit": "tomato"})

    patterns = engine.generalize(["color", "shape"])

    print(f"   Examples added: 4")
    print(f"   P(color=red): {patterns.get('color', {}).get('red', 0):.2f}")
    print(f"   P(shape=round): {patterns.get('shape', {}).get('round', 0):.2f}")
    print()

    # 4. Abductive Reasoning
    print("4. ABDUCTIVE REASONING:")
    print("-" * 40)

    engine.add_rule("rain_causes_wet", ["rain"], ["wet_ground"])
    engine.add_rule("sprinkler_causes_wet", ["sprinkler"], ["wet_ground"])

    engine.add_fact("rain")
    engine.add_fact("sprinkler")

    explanations = engine.explain("wet_ground", ["rain", "sprinkler"])

    print(f"   Observation: wet_ground")
    print(f"   Explanations: {explanations}")
    print()

    # 5. Causal Reasoning
    print("5. CAUSAL REASONING:")
    print("-" * 40)

    engine.add_causal_link("smoking", "lung_cancer", strength=0.7)
    engine.add_causal_link("smoking", "heart_disease", strength=0.5)
    engine.add_causal_link("lung_cancer", "death", strength=0.8)
    engine.add_causal_link("heart_disease", "death", strength=0.6)

    chains = engine.trace_causality("smoking")

    print(f"   Causal chains from 'smoking':")
    for chain in chains:
        print(f"     {' -> '.join(chain)}")
    print()

    # 6. Intervention
    print("6. INTERVENTION ANALYSIS:")
    print("-" * 40)

    effects = engine.intervene("smoking", False)

    print(f"   Intervention: stop smoking")
    print(f"   Effects:")
    for effect, prob in effects.items():
        print(f"     {effect}: {prob:.2f}")
    print()

    # 7. Analogical Reasoning
    print("7. ANALOGICAL REASONING:")
    print("-" * 40)

    engine.add_domain("solar_system", {
        "center": "sun",
        "orbiting": "planets",
        "gravity": "attraction",
        "large_body": "sun"
    })

    engine.add_domain("atom", {
        "center": "nucleus",
        "orbiting": "electrons",
        "force": "electromagnetic",
        "large_body": "nucleus"
    })

    analogy = engine.find_analogy("solar_system", "atom")

    print(f"   Source: solar_system")
    print(f"   Target: atom")
    print(f"   Similarity: {analogy.similarity:.2f}")
    print(f"   Mappings: {analogy.mappings}")
    print()

    # 8. Probabilistic Reasoning
    print("8. PROBABILISTIC REASONING:")
    print("-" * 40)

    engine.set_prior("disease", 0.01)
    engine.set_prior("healthy", 0.99)
    engine.set_conditional("positive_test", "disease", 0.95)
    engine.set_conditional("positive_test", "healthy", 0.05)

    posterior = engine.bayes_update("disease", "positive_test")

    print(f"   P(disease) prior: 0.01")
    print(f"   P(positive|disease): 0.95")
    print(f"   P(positive|healthy): 0.05")
    print(f"   P(disease|positive): {posterior:.4f}")
    print()

    # 9. Constraint Satisfaction
    print("9. CONSTRAINT SATISFACTION:")
    print("-" * 40)

    engine.add_variable("A", [1, 2, 3])
    engine.add_variable("B", [1, 2, 3])
    engine.add_variable("C", [1, 2, 3])

    engine.add_constraint("all_different", ["A", "B"], lambda a, b: a != b)
    engine.add_constraint("all_different2", ["B", "C"], lambda b, c: b != c)
    engine.add_constraint("all_different3", ["A", "C"], lambda a, c: a != c)
    engine.add_constraint("sum_constraint", ["A", "B"], lambda a, b: a + b == 4)

    solution = engine.solve_constraints()

    print(f"   Variables: A, B, C in {[1,2,3]}")
    print(f"   Constraints: all different, A+B=4")
    print(f"   Solution: {solution}")
    print()

    # 10. Complex Deductive Chain
    print("10. COMPLEX DEDUCTIVE CHAIN:")
    print("-" * 40)

    # Clear and rebuild
    engine2 = ReasoningEngine()

    engine2.add_fact("socrates_is_human")
    engine2.add_rule("humans_mortal", ["socrates_is_human"], ["socrates_is_mortal"])
    engine2.add_rule("mortals_die", ["socrates_is_mortal"], ["socrates_will_die"])

    engine2.forward_chain()

    print(f"   Fact: Socrates is human")
    print(f"   Rule: All humans are mortal")
    print(f"   Rule: All mortals die")
    print(f"   Conclusion: Socrates will die = {engine2.is_true('socrates_will_die')}")
    print()

    # 11. Cause Analysis
    print("11. CAUSE ANALYSIS:")
    print("-" * 40)

    causes = engine.get_causes("death")
    effects = engine.get_effects("smoking")

    print(f"   Causes of death: {causes}")
    print(f"   Effects of smoking: {effects}")
    print()

    # 12. Pattern Correlation
    print("12. PATTERN CORRELATION:")
    print("-" * 40)

    correlation = engine._inductive.induce_correlation("color", "red", "shape", "round")

    print(f"   P(shape=round | color=red): {correlation:.2f}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Reasoning Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
