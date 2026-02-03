#!/usr/bin/env python3
"""
BAEL - Defeasible Reasoner
Advanced defeasible reasoning and argumentation.

Features:
- Defeasible rules
- Strict vs defeasible inference
- Superiority relations
- Conflict resolution
- Argument chains
- Skeptical/credulous reasoning
"""

import asyncio
import copy
import hashlib
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class RuleType(Enum):
    """Types of rules in defeasible logic."""
    STRICT = "strict"  # A -> B (strict implication)
    DEFEASIBLE = "defeasible"  # A => B (defeasible implication)
    DEFEATER = "defeater"  # A ~> B (defeater only)


class ProofStatus(Enum):
    """Status of a proof."""
    DEFINITELY_PROVABLE = "definitely_provable"  # +Δ
    DEFEASIBLY_PROVABLE = "defeasibly_provable"  # +∂
    NOT_DEFINITELY = "not_definitely"  # -Δ
    NOT_DEFEASIBLY = "not_defeasibly"  # -∂
    UNDECIDED = "undecided"


class ConflictResolution(Enum):
    """Conflict resolution methods."""
    SPECIFICITY = "specificity"
    PRIORITY = "priority"
    EXPLICIT_SUPERIORITY = "explicit_superiority"
    TEAM_DEFEAT = "team_defeat"


class ReasoningMode(Enum):
    """Reasoning modes."""
    SKEPTICAL = "skeptical"
    CREDULOUS = "credulous"
    AMBIGUITY_PROPAGATING = "ambiguity_propagating"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Literal:
    """A literal (positive or negative atom)."""
    lit_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    predicate: str = ""
    arguments: List[str] = field(default_factory=list)
    negated: bool = False

    def __hash__(self):
        return hash((self.predicate, tuple(self.arguments), self.negated))

    def __eq__(self, other):
        if not isinstance(other, Literal):
            return False
        return (self.predicate == other.predicate and
                self.arguments == other.arguments and
                self.negated == other.negated)

    def __str__(self):
        args = ", ".join(self.arguments) if self.arguments else ""
        pred = f"{self.predicate}({args})" if args else self.predicate
        return f"¬{pred}" if self.negated else pred

    def complement(self) -> 'Literal':
        """Get the complement of this literal."""
        return Literal(
            predicate=self.predicate,
            arguments=self.arguments.copy(),
            negated=not self.negated
        )


@dataclass
class DefeasibleRule:
    """A defeasible rule."""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    antecedent: List[Literal] = field(default_factory=list)
    consequent: Literal = field(default_factory=Literal)
    rule_type: RuleType = RuleType.DEFEASIBLE
    priority: int = 0


@dataclass
class SuperiorityRelation:
    """A superiority relation between rules."""
    sup_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    superior_rule: str = ""  # Rule ID
    inferior_rule: str = ""  # Rule ID


@dataclass
class ProofResult:
    """Result of a proof attempt."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    literal: str = ""
    status: ProofStatus = ProofStatus.UNDECIDED
    supporting_rules: List[str] = field(default_factory=list)
    attacking_rules: List[str] = field(default_factory=list)
    proof_tree: List[str] = field(default_factory=list)


@dataclass
class ArgumentChain:
    """A chain of arguments for a conclusion."""
    chain_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conclusion: str = ""
    rules: List[str] = field(default_factory=list)
    strength: float = 1.0
    defeated: bool = False
    defeaters: List[str] = field(default_factory=list)


@dataclass
class TheoryAnalysis:
    """Analysis of a defeasible theory."""
    analysis_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    definitely_provable: Set[str] = field(default_factory=set)
    defeasibly_provable: Set[str] = field(default_factory=set)
    not_provable: Set[str] = field(default_factory=set)
    conflicts: List[Tuple[str, str]] = field(default_factory=list)


# =============================================================================
# LITERAL MANAGER
# =============================================================================

class LiteralManager:
    """Manage literals."""

    def __init__(self):
        self._literals: Dict[str, Literal] = {}

    def create(
        self,
        predicate: str,
        arguments: Optional[List[str]] = None,
        negated: bool = False
    ) -> Literal:
        """Create a literal."""
        lit = Literal(
            predicate=predicate,
            arguments=arguments or [],
            negated=negated
        )
        self._literals[str(lit)] = lit
        return lit

    def parse(self, text: str) -> Literal:
        """Parse a literal from text."""
        negated = text.startswith("¬") or text.startswith("~") or text.startswith("-")
        clean = text.lstrip("¬~-")

        if "(" in clean:
            pred = clean[:clean.index("(")]
            args_str = clean[clean.index("(") + 1:clean.rindex(")")]
            args = [a.strip() for a in args_str.split(",")] if args_str else []
        else:
            pred = clean.strip()
            args = []

        return self.create(pred, args, negated)

    def get(self, text: str) -> Optional[Literal]:
        """Get a literal by string."""
        return self._literals.get(text)


# =============================================================================
# RULE MANAGER
# =============================================================================

class RuleManager:
    """Manage defeasible rules."""

    def __init__(self, literal_manager: LiteralManager):
        self._literals = literal_manager
        self._rules: Dict[str, DefeasibleRule] = {}
        self._by_consequent: Dict[str, List[str]] = defaultdict(list)

    def add_strict(
        self,
        name: str,
        antecedent: List[Literal],
        consequent: Literal
    ) -> DefeasibleRule:
        """Add a strict rule: A -> B."""
        rule = DefeasibleRule(
            name=name,
            antecedent=antecedent,
            consequent=consequent,
            rule_type=RuleType.STRICT
        )
        self._rules[rule.rule_id] = rule
        self._by_consequent[str(consequent)].append(rule.rule_id)
        return rule

    def add_defeasible(
        self,
        name: str,
        antecedent: List[Literal],
        consequent: Literal,
        priority: int = 0
    ) -> DefeasibleRule:
        """Add a defeasible rule: A => B."""
        rule = DefeasibleRule(
            name=name,
            antecedent=antecedent,
            consequent=consequent,
            rule_type=RuleType.DEFEASIBLE,
            priority=priority
        )
        self._rules[rule.rule_id] = rule
        self._by_consequent[str(consequent)].append(rule.rule_id)
        return rule

    def add_defeater(
        self,
        name: str,
        antecedent: List[Literal],
        consequent: Literal
    ) -> DefeasibleRule:
        """Add a defeater: A ~> B."""
        rule = DefeasibleRule(
            name=name,
            antecedent=antecedent,
            consequent=consequent,
            rule_type=RuleType.DEFEATER
        )
        self._rules[rule.rule_id] = rule
        self._by_consequent[str(consequent)].append(rule.rule_id)
        return rule

    def get_rule(self, rule_id: str) -> Optional[DefeasibleRule]:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def rules_for(self, literal: Literal) -> List[DefeasibleRule]:
        """Get rules with given consequent."""
        lit_str = str(literal)
        rule_ids = self._by_consequent.get(lit_str, [])
        return [self._rules[rid] for rid in rule_ids if rid in self._rules]

    def all_rules(self) -> List[DefeasibleRule]:
        """Get all rules."""
        return list(self._rules.values())


# =============================================================================
# SUPERIORITY MANAGER
# =============================================================================

class SuperiorityManager:
    """Manage superiority relations between rules."""

    def __init__(self):
        self._relations: List[SuperiorityRelation] = []
        self._superior_to: Dict[str, Set[str]] = defaultdict(set)

    def add_superiority(
        self,
        superior_rule: str,
        inferior_rule: str
    ) -> SuperiorityRelation:
        """Add r1 > r2 (r1 is superior to r2)."""
        rel = SuperiorityRelation(
            superior_rule=superior_rule,
            inferior_rule=inferior_rule
        )
        self._relations.append(rel)
        self._superior_to[superior_rule].add(inferior_rule)
        return rel

    def is_superior(self, r1: str, r2: str) -> bool:
        """Check if r1 > r2."""
        return r2 in self._superior_to.get(r1, set())

    def get_superior_rules(self, rule_id: str) -> List[str]:
        """Get rules that are superior to given rule."""
        return [r.superior_rule for r in self._relations
                if r.inferior_rule == rule_id]

    def get_inferior_rules(self, rule_id: str) -> Set[str]:
        """Get rules that are inferior to given rule."""
        return self._superior_to.get(rule_id, set())


# =============================================================================
# KNOWLEDGE BASE
# =============================================================================

class DefeasibleKnowledgeBase:
    """Knowledge base with facts."""

    def __init__(self):
        self._facts: Set[str] = set()  # Definite facts
        self._fact_literals: Dict[str, Literal] = {}

    def add_fact(self, literal: Literal) -> None:
        """Add a definite fact."""
        lit_str = str(literal)
        self._facts.add(lit_str)
        self._fact_literals[lit_str] = literal

    def remove_fact(self, literal: Literal) -> bool:
        """Remove a fact."""
        lit_str = str(literal)
        if lit_str in self._facts:
            self._facts.remove(lit_str)
            del self._fact_literals[lit_str]
            return True
        return False

    def is_fact(self, literal: Literal) -> bool:
        """Check if literal is a definite fact."""
        return str(literal) in self._facts

    def all_facts(self) -> Set[str]:
        """Get all facts."""
        return self._facts.copy()


# =============================================================================
# PROOF ENGINE
# =============================================================================

class ProofEngine:
    """Prove literals in defeasible logic."""

    def __init__(
        self,
        kb: DefeasibleKnowledgeBase,
        rules: RuleManager,
        superiority: SuperiorityManager
    ):
        self._kb = kb
        self._rules = rules
        self._superiority = superiority

        # Proof caches
        self._definitely: Dict[str, bool] = {}
        self._defeasibly: Dict[str, bool] = {}

    def reset_caches(self) -> None:
        """Reset proof caches."""
        self._definitely.clear()
        self._defeasibly.clear()

    def prove(
        self,
        literal: Literal,
        mode: ReasoningMode = ReasoningMode.SKEPTICAL
    ) -> ProofResult:
        """Prove a literal."""
        lit_str = str(literal)

        # Check definite provability
        is_definite = self._prove_definitely(literal)

        if is_definite:
            return ProofResult(
                literal=lit_str,
                status=ProofStatus.DEFINITELY_PROVABLE,
                proof_tree=[f"+Δ {lit_str}"]
            )

        # Check defeasible provability
        is_defeasible = self._prove_defeasibly(literal)

        if is_defeasible:
            return ProofResult(
                literal=lit_str,
                status=ProofStatus.DEFEASIBLY_PROVABLE,
                proof_tree=[f"+∂ {lit_str}"]
            )

        # Check if complement is provable
        comp = literal.complement()
        comp_defeasible = self._prove_defeasibly(comp)

        if comp_defeasible:
            return ProofResult(
                literal=lit_str,
                status=ProofStatus.NOT_DEFEASIBLY,
                proof_tree=[f"-∂ {lit_str} (complement provable)"]
            )

        return ProofResult(
            literal=lit_str,
            status=ProofStatus.UNDECIDED,
            proof_tree=[f"? {lit_str}"]
        )

    def _prove_definitely(self, literal: Literal) -> bool:
        """Prove +Δ (definitely provable)."""
        lit_str = str(literal)

        if lit_str in self._definitely:
            return self._definitely[lit_str]

        # Prevent infinite recursion
        self._definitely[lit_str] = False

        # P1: Is it a fact?
        if self._kb.is_fact(literal):
            self._definitely[lit_str] = True
            return True

        # P2: Is there a strict rule with provable antecedent?
        rules = self._rules.rules_for(literal)
        strict_rules = [r for r in rules if r.rule_type == RuleType.STRICT]

        for rule in strict_rules:
            all_proved = True
            for ant in rule.antecedent:
                if not self._prove_definitely(ant):
                    all_proved = False
                    break

            if all_proved:
                self._definitely[lit_str] = True
                return True

        return False

    def _prove_defeasibly(self, literal: Literal) -> bool:
        """Prove +∂ (defeasibly provable)."""
        lit_str = str(literal)

        if lit_str in self._defeasibly:
            return self._defeasibly[lit_str]

        # Prevent infinite recursion
        self._defeasibly[lit_str] = False

        # P1: If definitely provable, then defeasibly provable
        if self._prove_definitely(literal):
            self._defeasibly[lit_str] = True
            return True

        # P2: Need an applicable rule
        rules = self._rules.rules_for(literal)
        applicable_rules = []

        for rule in rules:
            if rule.rule_type == RuleType.DEFEATER:
                continue  # Defeaters don't support conclusions

            all_proved = True
            for ant in rule.antecedent:
                if not self._prove_defeasibly(ant):
                    all_proved = False
                    break

            if all_proved:
                applicable_rules.append(rule)

        if not applicable_rules:
            return False

        # P3: Check if complement is blocked
        comp = literal.complement()
        comp_str = str(comp)

        # Get rules for complement
        comp_rules = self._rules.rules_for(comp)

        for comp_rule in comp_rules:
            # Check if comp_rule is applicable
            comp_applicable = True
            for ant in comp_rule.antecedent:
                if not self._prove_defeasibly(ant):
                    comp_applicable = False
                    break

            if not comp_applicable:
                continue

            # Check if we can defeat this rule
            defeated = False
            for my_rule in applicable_rules:
                if self._superiority.is_superior(my_rule.rule_id, comp_rule.rule_id):
                    defeated = True
                    break

            if not defeated:
                # Conflict not resolved in our favor
                return False

        self._defeasibly[lit_str] = True
        return True


# =============================================================================
# ARGUMENT BUILDER
# =============================================================================

class ArgumentBuilder:
    """Build argument chains."""

    def __init__(
        self,
        rules: RuleManager,
        proof_engine: ProofEngine
    ):
        self._rules = rules
        self._proof = proof_engine

    def build_arguments(self, literal: Literal) -> List[ArgumentChain]:
        """Build all argument chains for a literal."""
        arguments = []

        rules = self._rules.rules_for(literal)

        for rule in rules:
            if rule.rule_type == RuleType.DEFEATER:
                continue

            # Check if antecedent is supportable
            supported = True
            for ant in rule.antecedent:
                result = self._proof.prove(ant)
                if result.status not in [ProofStatus.DEFINITELY_PROVABLE,
                                          ProofStatus.DEFEASIBLY_PROVABLE]:
                    supported = False
                    break

            if supported:
                chain = ArgumentChain(
                    conclusion=str(literal),
                    rules=[rule.rule_id],
                    strength=1.0 if rule.rule_type == RuleType.STRICT else 0.8
                )
                arguments.append(chain)

        return arguments

    def find_defeaters(
        self,
        argument: ArgumentChain
    ) -> List[ArgumentChain]:
        """Find arguments that defeat given argument."""
        # Get the conclusion
        lit = self._rules._literals.parse(argument.conclusion)
        comp = lit.complement()

        # Find arguments for complement
        return self.build_arguments(comp)


# =============================================================================
# DEFEASIBLE REASONER
# =============================================================================

class DefeasibleReasoner:
    """
    Defeasible Reasoner for BAEL.

    Advanced defeasible reasoning and argumentation.
    """

    def __init__(self):
        self._literals = LiteralManager()
        self._rules = RuleManager(self._literals)
        self._superiority = SuperiorityManager()
        self._kb = DefeasibleKnowledgeBase()
        self._proof = ProofEngine(self._kb, self._rules, self._superiority)
        self._arguments = ArgumentBuilder(self._rules, self._proof)

    # -------------------------------------------------------------------------
    # LITERAL MANAGEMENT
    # -------------------------------------------------------------------------

    def literal(
        self,
        predicate: str,
        arguments: Optional[List[str]] = None,
        negated: bool = False
    ) -> Literal:
        """Create a literal."""
        return self._literals.create(predicate, arguments, negated)

    def parse(self, text: str) -> Literal:
        """Parse a literal from text."""
        return self._literals.parse(text)

    # -------------------------------------------------------------------------
    # RULE MANAGEMENT
    # -------------------------------------------------------------------------

    def add_strict(
        self,
        name: str,
        antecedent: List[Literal],
        consequent: Literal
    ) -> DefeasibleRule:
        """Add a strict rule: A -> B."""
        return self._rules.add_strict(name, antecedent, consequent)

    def add_defeasible(
        self,
        name: str,
        antecedent: List[Literal],
        consequent: Literal,
        priority: int = 0
    ) -> DefeasibleRule:
        """Add a defeasible rule: A => B."""
        return self._rules.add_defeasible(name, antecedent, consequent, priority)

    def add_defeater(
        self,
        name: str,
        antecedent: List[Literal],
        consequent: Literal
    ) -> DefeasibleRule:
        """Add a defeater: A ~> B."""
        return self._rules.add_defeater(name, antecedent, consequent)

    def get_rule(self, rule_id: str) -> Optional[DefeasibleRule]:
        """Get a rule by ID."""
        return self._rules.get_rule(rule_id)

    def all_rules(self) -> List[DefeasibleRule]:
        """Get all rules."""
        return self._rules.all_rules()

    # -------------------------------------------------------------------------
    # SUPERIORITY
    # -------------------------------------------------------------------------

    def add_superiority(
        self,
        superior_rule: str,
        inferior_rule: str
    ) -> SuperiorityRelation:
        """Add superiority relation: r1 > r2."""
        return self._superiority.add_superiority(superior_rule, inferior_rule)

    def is_superior(self, r1: str, r2: str) -> bool:
        """Check if r1 > r2."""
        return self._superiority.is_superior(r1, r2)

    # -------------------------------------------------------------------------
    # KNOWLEDGE BASE
    # -------------------------------------------------------------------------

    def add_fact(self, literal: Literal) -> None:
        """Add a definite fact."""
        self._kb.add_fact(literal)
        self._proof.reset_caches()

    def remove_fact(self, literal: Literal) -> bool:
        """Remove a fact."""
        result = self._kb.remove_fact(literal)
        self._proof.reset_caches()
        return result

    def is_fact(self, literal: Literal) -> bool:
        """Check if literal is a fact."""
        return self._kb.is_fact(literal)

    def all_facts(self) -> Set[str]:
        """Get all facts."""
        return self._kb.all_facts()

    # -------------------------------------------------------------------------
    # PROOF
    # -------------------------------------------------------------------------

    def prove(
        self,
        literal: Literal,
        mode: ReasoningMode = ReasoningMode.SKEPTICAL
    ) -> ProofResult:
        """Prove a literal."""
        return self._proof.prove(literal, mode)

    def is_definitely_provable(self, literal: Literal) -> bool:
        """Check if literal is definitely provable."""
        result = self.prove(literal)
        return result.status == ProofStatus.DEFINITELY_PROVABLE

    def is_defeasibly_provable(self, literal: Literal) -> bool:
        """Check if literal is defeasibly provable."""
        result = self.prove(literal)
        return result.status in [ProofStatus.DEFINITELY_PROVABLE,
                                  ProofStatus.DEFEASIBLY_PROVABLE]

    # -------------------------------------------------------------------------
    # ARGUMENTS
    # -------------------------------------------------------------------------

    def build_arguments(self, literal: Literal) -> List[ArgumentChain]:
        """Build argument chains for a literal."""
        return self._arguments.build_arguments(literal)

    def find_defeaters(self, argument: ArgumentChain) -> List[ArgumentChain]:
        """Find defeaters for an argument."""
        return self._arguments.find_defeaters(argument)

    # -------------------------------------------------------------------------
    # ANALYSIS
    # -------------------------------------------------------------------------

    def analyze_theory(self) -> TheoryAnalysis:
        """Analyze the current theory."""
        analysis = TheoryAnalysis()

        # Collect all literals that could be proved
        candidates: Set[str] = set()

        for fact in self._kb.all_facts():
            candidates.add(fact)

        for rule in self._rules.all_rules():
            candidates.add(str(rule.consequent))
            candidates.add(str(rule.consequent.complement()))

        # Check each candidate
        for lit_str in candidates:
            literal = self._literals.parse(lit_str)
            result = self.prove(literal)

            if result.status == ProofStatus.DEFINITELY_PROVABLE:
                analysis.definitely_provable.add(lit_str)
            elif result.status == ProofStatus.DEFEASIBLY_PROVABLE:
                analysis.defeasibly_provable.add(lit_str)
            else:
                analysis.not_provable.add(lit_str)

        # Find conflicts
        for lit_str in analysis.defeasibly_provable:
            literal = self._literals.parse(lit_str)
            comp_str = str(literal.complement())
            if comp_str in analysis.defeasibly_provable:
                analysis.conflicts.append((lit_str, comp_str))

        return analysis


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Defeasible Reasoner."""
    print("=" * 70)
    print("BAEL - DEFEASIBLE REASONER DEMO")
    print("Advanced Defeasible Reasoning and Argumentation")
    print("=" * 70)
    print()

    reasoner = DefeasibleReasoner()

    # 1. Create Literals
    print("1. CREATE LITERALS:")
    print("-" * 40)

    bird = reasoner.literal("bird", ["tweety"])
    penguin = reasoner.literal("penguin", ["tweety"])
    flies = reasoner.literal("flies", ["tweety"])
    not_flies = flies.complement()

    print(f"   {bird}")
    print(f"   {penguin}")
    print(f"   {flies}")
    print(f"   {not_flies}")
    print()

    # 2. Add Facts
    print("2. ADD FACTS:")
    print("-" * 40)

    reasoner.add_fact(bird)
    reasoner.add_fact(penguin)

    print(f"   Facts: {reasoner.all_facts()}")
    print()

    # 3. Add Rules
    print("3. ADD RULES:")
    print("-" * 40)

    # Birds defeasibly fly
    r1 = reasoner.add_defeasible(
        "birds_fly",
        [bird],
        flies,
        priority=1
    )

    # Penguins strictly are birds
    r2 = reasoner.add_strict(
        "penguins_birds",
        [penguin],
        bird
    )

    # Penguins defeasibly don't fly
    r3 = reasoner.add_defeasible(
        "penguins_no_fly",
        [penguin],
        not_flies,
        priority=2
    )

    print(f"   r1: bird(X) => flies(X)")
    print(f"   r2: penguin(X) -> bird(X)")
    print(f"   r3: penguin(X) => ¬flies(X)")
    print()

    # 4. Add Superiority
    print("4. ADD SUPERIORITY RELATION:")
    print("-" * 40)

    reasoner.add_superiority(r3.rule_id, r1.rule_id)
    print(f"   r3 > r1 (penguins_no_fly > birds_fly)")
    print()

    # 5. Prove Literals
    print("5. PROVE LITERALS:")
    print("-" * 40)

    result_bird = reasoner.prove(bird)
    print(f"   bird(tweety): {result_bird.status.value}")

    result_flies = reasoner.prove(flies)
    print(f"   flies(tweety): {result_flies.status.value}")

    result_not_flies = reasoner.prove(not_flies)
    print(f"   ¬flies(tweety): {result_not_flies.status.value}")
    print()

    # 6. Check Provability
    print("6. CHECK PROVABILITY:")
    print("-" * 40)

    print(f"   bird(tweety) definitely provable: {reasoner.is_definitely_provable(bird)}")
    print(f"   bird(tweety) defeasibly provable: {reasoner.is_defeasibly_provable(bird)}")
    print(f"   flies(tweety) defeasibly provable: {reasoner.is_defeasibly_provable(flies)}")
    print(f"   ¬flies(tweety) defeasibly provable: {reasoner.is_defeasibly_provable(not_flies)}")
    print()

    # 7. Build Arguments
    print("7. BUILD ARGUMENTS:")
    print("-" * 40)

    args_flies = reasoner.build_arguments(flies)
    args_not_flies = reasoner.build_arguments(not_flies)

    print(f"   Arguments for flies(tweety): {len(args_flies)}")
    print(f"   Arguments for ¬flies(tweety): {len(args_not_flies)}")

    if args_flies:
        print(f"      Argument 1 strength: {args_flies[0].strength}")
    print()

    # 8. Find Defeaters
    print("8. FIND DEFEATERS:")
    print("-" * 40)

    if args_flies:
        defeaters = reasoner.find_defeaters(args_flies[0])
        print(f"   Defeaters for 'flies(tweety)': {len(defeaters)}")
    print()

    # 9. Theory Analysis
    print("9. THEORY ANALYSIS:")
    print("-" * 40)

    analysis = reasoner.analyze_theory()
    print(f"   Definitely provable: {analysis.definitely_provable}")
    print(f"   Defeasibly provable: {analysis.defeasibly_provable}")
    print(f"   Not provable: {len(analysis.not_provable)} literals")
    print()

    # 10. New Example: Nixon Diamond
    print("10. NIXON DIAMOND:")
    print("-" * 40)

    nixon = DefeasibleReasoner()

    quaker = nixon.literal("quaker", ["nixon"])
    republican = nixon.literal("republican", ["nixon"])
    pacifist = nixon.literal("pacifist", ["nixon"])
    not_pacifist = pacifist.complement()

    nixon.add_fact(quaker)
    nixon.add_fact(republican)

    r_quaker = nixon.add_defeasible("quakers_pacifist", [quaker], pacifist)
    r_repub = nixon.add_defeasible("republicans_not_pacifist", [republican], not_pacifist)

    print(f"   quaker(nixon) => pacifist(nixon)")
    print(f"   republican(nixon) => ¬pacifist(nixon)")
    print()

    # Without superiority: both are blocked
    result_pac = nixon.prove(pacifist)
    result_not_pac = nixon.prove(not_pacifist)

    print(f"   Without superiority:")
    print(f"      pacifist(nixon): {result_pac.status.value}")
    print(f"      ¬pacifist(nixon): {result_not_pac.status.value}")

    # Add superiority
    nixon.add_superiority(r_quaker.rule_id, r_repub.rule_id)
    nixon._proof.reset_caches()

    result_pac = nixon.prove(pacifist)
    result_not_pac = nixon.prove(not_pacifist)

    print(f"   With quaker > republican:")
    print(f"      pacifist(nixon): {result_pac.status.value}")
    print(f"      ¬pacifist(nixon): {result_not_pac.status.value}")
    print()

    # 11. Defeaters (non-supporting)
    print("11. DEFEATERS:")
    print("-" * 40)

    d = DefeasibleReasoner()

    d_bird = d.literal("bird", ["X"])
    d_flies = d.literal("flies", ["X"])
    d_heavy = d.literal("heavy", ["X"])
    d_not_flies = d_flies.complement()

    d.add_defeasible("birds_fly", [d_bird], d_flies)
    # Defeater: heavy things don't fly (but doesn't conclude ¬flies directly)
    d.add_defeater("heavy_blocks", [d_heavy], d_not_flies)

    print(f"   bird(X) => flies(X)")
    print(f"   heavy(X) ~> ¬flies(X)  (defeater)")
    print(f"   Defeaters block but don't support conclusions")
    print()

    # 12. All Rules
    print("12. ALL RULES:")
    print("-" * 40)

    for rule in reasoner.all_rules():
        rule_sym = {
            RuleType.STRICT: "->",
            RuleType.DEFEASIBLE: "=>",
            RuleType.DEFEATER: "~>"
        }
        ant = ", ".join(str(a) for a in rule.antecedent)
        print(f"   {rule.name}: {ant} {rule_sym[rule.rule_type]} {rule.consequent}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Defeasible Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
