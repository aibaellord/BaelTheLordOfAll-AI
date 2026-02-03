#!/usr/bin/env python3
"""
BAEL - Assumption-Based Reasoner
Advanced assumption-based argumentation and reasoning.

Features:
- Assumption-based argumentation (ABA)
- Defeasible assumptions
- Contrary relations
- Argument construction
- Attack relations
- Skeptical/credulous semantics
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

class AssumptionStatus(Enum):
    """Status of an assumption."""
    ACTIVE = "active"
    DEFEATED = "defeated"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


class SemanticsType(Enum):
    """Types of argumentation semantics."""
    GROUNDED = "grounded"
    PREFERRED = "preferred"
    STABLE = "stable"
    COMPLETE = "complete"
    ADMISSIBLE = "admissible"


class AttackType(Enum):
    """Types of attacks."""
    UNDERCUT = "undercut"  # Attack on assumption
    REBUT = "rebut"  # Attack on conclusion
    UNDERMINE = "undermine"  # Attack on premise


class DerivationMode(Enum):
    """Modes of derivation."""
    FORWARD = "forward"
    BACKWARD = "backward"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Sentence:
    """A sentence (proposition)."""
    sent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    is_assumption: bool = False
    contrary: Optional[str] = None  # Sentence that contradicts this

    def __hash__(self):
        return hash(self.content)

    def __eq__(self, other):
        if not isinstance(other, Sentence):
            return False
        return self.content == other.content

    def __str__(self):
        return self.content


@dataclass
class Rule:
    """A derivation rule."""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    body: List[str] = field(default_factory=list)  # Premises
    head: str = ""  # Conclusion

    def __str__(self):
        body_str = ", ".join(self.body) if self.body else "⊤"
        return f"{body_str} → {self.head}"


@dataclass
class Assumption:
    """An assumption in ABA."""
    asm_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    contrary: str = ""  # The contrary of this assumption
    status: AssumptionStatus = AssumptionStatus.ACTIVE


@dataclass
class Argument:
    """An argument derived from assumptions."""
    arg_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conclusion: str = ""
    assumptions: Set[str] = field(default_factory=set)  # Assumption contents
    derivation: List[str] = field(default_factory=list)  # Rule sequence


@dataclass
class Attack:
    """An attack between arguments."""
    attack_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    attacker: str = ""  # Argument ID
    target: str = ""  # Argument ID
    attack_type: AttackType = AttackType.UNDERCUT
    target_assumption: str = ""  # Which assumption is attacked


@dataclass
class Extension:
    """An extension (set of acceptable assumptions)."""
    ext_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    assumptions: Set[str] = field(default_factory=set)
    arguments: Set[str] = field(default_factory=set)
    semantics: SemanticsType = SemanticsType.GROUNDED


# =============================================================================
# SENTENCE MANAGER
# =============================================================================

class SentenceManager:
    """Manage sentences."""

    def __init__(self):
        self._sentences: Dict[str, Sentence] = {}

    def add(
        self,
        content: str,
        is_assumption: bool = False,
        contrary: Optional[str] = None
    ) -> Sentence:
        """Add a sentence."""
        sent = Sentence(
            content=content,
            is_assumption=is_assumption,
            contrary=contrary
        )
        self._sentences[content] = sent
        return sent

    def get(self, content: str) -> Optional[Sentence]:
        """Get a sentence by content."""
        return self._sentences.get(content)

    def all_sentences(self) -> List[Sentence]:
        """Get all sentences."""
        return list(self._sentences.values())

    def assumptions(self) -> List[Sentence]:
        """Get all assumptions."""
        return [s for s in self._sentences.values() if s.is_assumption]


# =============================================================================
# RULE MANAGER
# =============================================================================

class RuleManager:
    """Manage derivation rules."""

    def __init__(self):
        self._rules: Dict[str, Rule] = {}
        self._by_head: Dict[str, List[str]] = defaultdict(list)

    def add(
        self,
        name: str,
        body: List[str],
        head: str
    ) -> Rule:
        """Add a rule: body → head."""
        rule = Rule(name=name, body=body, head=head)
        self._rules[rule.rule_id] = rule
        self._by_head[head].append(rule.rule_id)
        return rule

    def get(self, rule_id: str) -> Optional[Rule]:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def rules_for(self, head: str) -> List[Rule]:
        """Get rules with given head."""
        rule_ids = self._by_head.get(head, [])
        return [self._rules[rid] for rid in rule_ids if rid in self._rules]

    def all_rules(self) -> List[Rule]:
        """Get all rules."""
        return list(self._rules.values())


# =============================================================================
# ASSUMPTION MANAGER
# =============================================================================

class AssumptionManager:
    """Manage assumptions."""

    def __init__(self, sentences: SentenceManager):
        self._sentences = sentences
        self._assumptions: Dict[str, Assumption] = {}
        self._contraries: Dict[str, str] = {}  # assumption -> contrary

    def add(
        self,
        content: str,
        contrary: str
    ) -> Assumption:
        """Add an assumption with its contrary."""
        # Add sentence
        self._sentences.add(content, is_assumption=True, contrary=contrary)

        # Add assumption
        asm = Assumption(content=content, contrary=contrary)
        self._assumptions[content] = asm
        self._contraries[content] = contrary

        return asm

    def get(self, content: str) -> Optional[Assumption]:
        """Get an assumption."""
        return self._assumptions.get(content)

    def get_contrary(self, assumption: str) -> Optional[str]:
        """Get the contrary of an assumption."""
        return self._contraries.get(assumption)

    def all_assumptions(self) -> List[Assumption]:
        """Get all assumptions."""
        return list(self._assumptions.values())

    def is_assumption(self, content: str) -> bool:
        """Check if content is an assumption."""
        return content in self._assumptions


# =============================================================================
# DERIVATION ENGINE
# =============================================================================

class DerivationEngine:
    """Derive conclusions from assumptions and rules."""

    def __init__(
        self,
        rules: RuleManager,
        assumptions: AssumptionManager
    ):
        self._rules = rules
        self._assumptions = assumptions

    def derive(
        self,
        goal: str,
        available_assumptions: Set[str]
    ) -> Optional[Argument]:
        """
        Derive goal using backward chaining.
        Returns argument if derivable.
        """
        used_assumptions: Set[str] = set()
        derivation: List[str] = []

        if self._derive_recursive(goal, available_assumptions,
                                   used_assumptions, derivation, set()):
            return Argument(
                conclusion=goal,
                assumptions=used_assumptions,
                derivation=derivation
            )
        return None

    def _derive_recursive(
        self,
        goal: str,
        available: Set[str],
        used: Set[str],
        derivation: List[str],
        visited: Set[str]
    ) -> bool:
        """Recursive backward derivation."""
        if goal in visited:
            return False  # Cycle detection

        visited = visited | {goal}

        # Check if goal is an available assumption
        if self._assumptions.is_assumption(goal) and goal in available:
            used.add(goal)
            return True

        # Try to derive using rules
        rules = self._rules.rules_for(goal)

        for rule in rules:
            if not rule.body:
                # Fact (empty body)
                derivation.append(f"{rule.name}: ⊤ → {rule.head}")
                return True

            # Try to prove all premises
            all_proved = True
            temp_used: Set[str] = set()
            temp_derivation: List[str] = []

            for premise in rule.body:
                if not self._derive_recursive(premise, available,
                                              temp_used, temp_derivation, visited):
                    all_proved = False
                    break

            if all_proved:
                used.update(temp_used)
                derivation.extend(temp_derivation)
                derivation.append(f"{rule.name}: {rule}")
                return True

        return False

    def derive_all(
        self,
        assumptions: Set[str]
    ) -> Dict[str, Argument]:
        """Derive all conclusions from assumptions."""
        conclusions: Dict[str, Argument] = {}

        # Forward chaining
        derived: Set[str] = assumptions.copy()
        changed = True

        while changed:
            changed = False
            for rule in self._rules.all_rules():
                if rule.head not in derived:
                    if all(p in derived for p in rule.body):
                        derived.add(rule.head)
                        arg = self.derive(rule.head, assumptions)
                        if arg:
                            conclusions[rule.head] = arg
                        changed = True

        return conclusions


# =============================================================================
# ATTACK MANAGER
# =============================================================================

class AttackManager:
    """Compute attacks between arguments."""

    def __init__(
        self,
        assumptions: AssumptionManager,
        derivation: DerivationEngine
    ):
        self._assumptions = assumptions
        self._derivation = derivation
        self._attacks: List[Attack] = []

    def compute_attacks(
        self,
        arguments: Dict[str, Argument]
    ) -> List[Attack]:
        """Compute all attacks between arguments."""
        attacks = []

        for arg_id, arg in arguments.items():
            # Check if this argument attacks any assumption
            for other_id, other in arguments.items():
                if arg_id == other_id:
                    continue

                # Check each assumption in other
                for asm in other.assumptions:
                    contrary = self._assumptions.get_contrary(asm)
                    if contrary and arg.conclusion == contrary:
                        # arg attacks other by deriving contrary of asm
                        attack = Attack(
                            attacker=arg_id,
                            target=other_id,
                            attack_type=AttackType.UNDERCUT,
                            target_assumption=asm
                        )
                        attacks.append(attack)

        self._attacks = attacks
        return attacks

    def get_attacks_on(self, argument_id: str) -> List[Attack]:
        """Get attacks on an argument."""
        return [a for a in self._attacks if a.target == argument_id]

    def get_attacks_by(self, argument_id: str) -> List[Attack]:
        """Get attacks by an argument."""
        return [a for a in self._attacks if a.attacker == argument_id]


# =============================================================================
# EXTENSION CALCULATOR
# =============================================================================

class ExtensionCalculator:
    """Calculate extensions under different semantics."""

    def __init__(
        self,
        assumptions: AssumptionManager,
        derivation: DerivationEngine,
        attacks: AttackManager
    ):
        self._assumptions = assumptions
        self._derivation = derivation
        self._attacks = attacks

    def _is_conflict_free(
        self,
        assumption_set: Set[str]
    ) -> bool:
        """Check if assumption set is conflict-free."""
        args = self._derivation.derive_all(assumption_set)

        for asm in assumption_set:
            contrary = self._assumptions.get_contrary(asm)
            if contrary and contrary in args:
                return False

        return True

    def _defends(
        self,
        defender_set: Set[str],
        target_assumption: str
    ) -> bool:
        """Check if defender_set defends target_assumption."""
        args = self._derivation.derive_all(defender_set)
        attacks = self._attacks.compute_attacks(args)

        # Find attacks on arguments using target_assumption
        target_args = {aid for aid, arg in args.items()
                      if target_assumption in arg.assumptions}

        for attack in attacks:
            if attack.target in target_args:
                # Check if we can counter-attack
                attacker_assumptions = args[attack.attacker].assumptions \
                    if attack.attacker in args else set()

                counter_attacked = False
                for att_asm in attacker_assumptions:
                    contrary = self._assumptions.get_contrary(att_asm)
                    if contrary and contrary in args:
                        counter_attacked = True
                        break

                if not counter_attacked:
                    return False

        return True

    def grounded_extension(self) -> Extension:
        """Compute grounded extension (skeptical)."""
        all_asms = {a.content for a in self._assumptions.all_assumptions()}

        # Start with empty set
        grounded: Set[str] = set()
        changed = True

        while changed:
            changed = False
            for asm in all_asms - grounded:
                # Check if asm is defended by grounded
                if self._is_conflict_free(grounded | {asm}):
                    if self._defends(grounded | {asm}, asm):
                        grounded.add(asm)
                        changed = True

        args = self._derivation.derive_all(grounded)

        return Extension(
            assumptions=grounded,
            arguments=set(args.keys()),
            semantics=SemanticsType.GROUNDED
        )

    def preferred_extensions(self) -> List[Extension]:
        """Compute preferred extensions (credulous)."""
        all_asms = list(self._assumptions.all_assumptions())

        # Find maximal admissible sets
        admissible_sets: List[Set[str]] = []

        # Check all subsets (simplified - exponential)
        for i in range(1 << len(all_asms)):
            subset = {all_asms[j].content for j in range(len(all_asms))
                     if (i >> j) & 1}

            if self._is_conflict_free(subset):
                # Check admissibility
                is_admissible = True
                for asm in subset:
                    if not self._defends(subset, asm):
                        is_admissible = False
                        break

                if is_admissible:
                    admissible_sets.append(subset)

        # Filter to maximal
        preferred = []
        for s in admissible_sets:
            is_maximal = True
            for other in admissible_sets:
                if s < other:  # Proper subset
                    is_maximal = False
                    break

            if is_maximal:
                args = self._derivation.derive_all(s)
                ext = Extension(
                    assumptions=s,
                    arguments=set(args.keys()),
                    semantics=SemanticsType.PREFERRED
                )
                preferred.append(ext)

        return preferred


# =============================================================================
# ASSUMPTION-BASED REASONER
# =============================================================================

class AssumptionReasoner:
    """
    Assumption-Based Reasoner for BAEL.

    Advanced assumption-based argumentation (ABA).
    """

    def __init__(self):
        self._sentences = SentenceManager()
        self._rules = RuleManager()
        self._assumptions = AssumptionManager(self._sentences)
        self._derivation = DerivationEngine(self._rules, self._assumptions)
        self._attacks = AttackManager(self._assumptions, self._derivation)
        self._extensions = ExtensionCalculator(
            self._assumptions, self._derivation, self._attacks
        )

    # -------------------------------------------------------------------------
    # ASSUMPTIONS
    # -------------------------------------------------------------------------

    def add_assumption(
        self,
        content: str,
        contrary: str
    ) -> Assumption:
        """Add an assumption with its contrary."""
        return self._assumptions.add(content, contrary)

    def get_assumption(self, content: str) -> Optional[Assumption]:
        """Get an assumption."""
        return self._assumptions.get(content)

    def get_contrary(self, assumption: str) -> Optional[str]:
        """Get contrary of an assumption."""
        return self._assumptions.get_contrary(assumption)

    def all_assumptions(self) -> List[Assumption]:
        """Get all assumptions."""
        return self._assumptions.all_assumptions()

    def is_assumption(self, content: str) -> bool:
        """Check if content is an assumption."""
        return self._assumptions.is_assumption(content)

    # -------------------------------------------------------------------------
    # RULES
    # -------------------------------------------------------------------------

    def add_rule(
        self,
        name: str,
        body: List[str],
        head: str
    ) -> Rule:
        """Add a rule: body → head."""
        return self._rules.add(name, body, head)

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def all_rules(self) -> List[Rule]:
        """Get all rules."""
        return self._rules.all_rules()

    # -------------------------------------------------------------------------
    # DERIVATION
    # -------------------------------------------------------------------------

    def derive(
        self,
        goal: str,
        assumptions: Set[str]
    ) -> Optional[Argument]:
        """Derive goal from assumptions."""
        return self._derivation.derive(goal, assumptions)

    def derive_all(
        self,
        assumptions: Set[str]
    ) -> Dict[str, Argument]:
        """Derive all conclusions from assumptions."""
        return self._derivation.derive_all(assumptions)

    # -------------------------------------------------------------------------
    # ATTACKS
    # -------------------------------------------------------------------------

    def compute_attacks(
        self,
        arguments: Dict[str, Argument]
    ) -> List[Attack]:
        """Compute attacks between arguments."""
        return self._attacks.compute_attacks(arguments)

    def get_attacks_on(self, argument_id: str) -> List[Attack]:
        """Get attacks on an argument."""
        return self._attacks.get_attacks_on(argument_id)

    def get_attacks_by(self, argument_id: str) -> List[Attack]:
        """Get attacks by an argument."""
        return self._attacks.get_attacks_by(argument_id)

    # -------------------------------------------------------------------------
    # EXTENSIONS
    # -------------------------------------------------------------------------

    def grounded_extension(self) -> Extension:
        """Compute grounded extension."""
        return self._extensions.grounded_extension()

    def preferred_extensions(self) -> List[Extension]:
        """Compute preferred extensions."""
        return self._extensions.preferred_extensions()

    def skeptical_conclusions(self) -> Set[str]:
        """Get skeptically justified conclusions."""
        ext = self.grounded_extension()
        args = self.derive_all(ext.assumptions)
        return set(args.keys())

    def credulous_conclusions(self) -> Set[str]:
        """Get credulously justified conclusions."""
        exts = self.preferred_extensions()
        conclusions: Set[str] = set()

        for ext in exts:
            args = self.derive_all(ext.assumptions)
            conclusions.update(args.keys())

        return conclusions

    # -------------------------------------------------------------------------
    # QUERY
    # -------------------------------------------------------------------------

    def query_skeptical(self, goal: str) -> bool:
        """Query if goal is skeptically justified."""
        return goal in self.skeptical_conclusions()

    def query_credulous(self, goal: str) -> bool:
        """Query if goal is credulously justified."""
        return goal in self.credulous_conclusions()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Assumption-Based Reasoner."""
    print("=" * 70)
    print("BAEL - ASSUMPTION-BASED REASONER DEMO")
    print("Advanced Assumption-Based Argumentation (ABA)")
    print("=" * 70)
    print()

    reasoner = AssumptionReasoner()

    # 1. Set Up ABA Framework
    print("1. SET UP ABA FRAMEWORK:")
    print("-" * 40)

    # Add assumptions with contraries
    reasoner.add_assumption("ab_bird", "not_ab_bird")
    reasoner.add_assumption("ab_penguin", "not_ab_penguin")

    print("   Assumptions:")
    print("     ab_bird (contrary: not_ab_bird)")
    print("     ab_penguin (contrary: not_ab_penguin)")
    print()

    # 2. Add Rules
    print("2. ADD RULES:")
    print("-" * 40)

    # Tweety is a bird
    reasoner.add_rule("r1", [], "bird")

    # Birds that are not abnormal fly
    reasoner.add_rule("r2", ["bird", "ab_bird"], "flies")

    # Tweety is a penguin
    reasoner.add_rule("r3", [], "penguin")

    # Penguins are birds
    reasoner.add_rule("r4", ["penguin"], "bird")

    # Penguins don't fly (contrary of ab_penguin)
    reasoner.add_rule("r5", ["penguin"], "not_ab_bird")

    for rule in reasoner.all_rules():
        print(f"   {rule.name}: {rule}")
    print()

    # 3. Derive with All Assumptions
    print("3. DERIVE WITH ALL ASSUMPTIONS:")
    print("-" * 40)

    all_asms = {a.content for a in reasoner.all_assumptions()}
    args = reasoner.derive_all(all_asms)

    print(f"   Using assumptions: {all_asms}")
    print(f"   Derived conclusions:")
    for conc, arg in args.items():
        print(f"     {conc}: uses {arg.assumptions}")
    print()

    # 4. Compute Attacks
    print("4. COMPUTE ATTACKS:")
    print("-" * 40)

    attacks = reasoner.compute_attacks(args)
    print(f"   Found {len(attacks)} attacks:")
    for attack in attacks:
        print(f"     {attack.attacker[:8]}... attacks {attack.target[:8]}...")
        print(f"       Target assumption: {attack.target_assumption}")
    print()

    # 5. Grounded Extension
    print("5. GROUNDED EXTENSION (SKEPTICAL):")
    print("-" * 40)

    grounded = reasoner.grounded_extension()
    print(f"   Accepted assumptions: {grounded.assumptions}")
    print(f"   Derived arguments: {len(grounded.arguments)}")
    print()

    # 6. Skeptical Conclusions
    print("6. SKEPTICAL CONCLUSIONS:")
    print("-" * 40)

    skeptical = reasoner.skeptical_conclusions()
    print(f"   Conclusions: {skeptical}")
    print()

    # 7. Query
    print("7. QUERY:")
    print("-" * 40)

    print(f"   'bird' skeptically justified: {reasoner.query_skeptical('bird')}")
    print(f"   'flies' skeptically justified: {reasoner.query_skeptical('flies')}")
    print(f"   'penguin' skeptically justified: {reasoner.query_skeptical('penguin')}")
    print()

    # 8. Another Example: Nixon Diamond
    print("8. NIXON DIAMOND EXAMPLE:")
    print("-" * 40)

    nixon = AssumptionReasoner()

    # Assumptions
    nixon.add_assumption("asm_quaker", "not_quaker_pacifist")
    nixon.add_assumption("asm_republican", "not_republican_hawk")

    # Rules
    nixon.add_rule("n1", [], "quaker")
    nixon.add_rule("n2", [], "republican")
    nixon.add_rule("n3", ["quaker", "asm_quaker"], "pacifist")
    nixon.add_rule("n4", ["republican", "asm_republican"], "hawk")
    nixon.add_rule("n5", ["pacifist"], "not_republican_hawk")
    nixon.add_rule("n6", ["hawk"], "not_quaker_pacifist")

    print("   Setup:")
    print("     Nixon is a Quaker and a Republican")
    print("     Quakers are normally pacifists")
    print("     Republicans are normally hawks")
    print("     Pacifists are not hawks (and vice versa)")
    print()

    # Preferred extensions
    preferred = nixon.preferred_extensions()
    print(f"   Preferred extensions: {len(preferred)}")
    for i, ext in enumerate(preferred):
        print(f"     Extension {i+1}: assumptions = {ext.assumptions}")
        concs = nixon.derive_all(ext.assumptions)
        print(f"       Conclusions: {set(concs.keys())}")
    print()

    # 9. Credulous Conclusions
    print("9. CREDULOUS CONCLUSIONS:")
    print("-" * 40)

    credulous = nixon.credulous_conclusions()
    print(f"   Nixon credulous conclusions: {credulous}")
    print()

    # 10. All Assumptions Status
    print("10. ALL ASSUMPTIONS:")
    print("-" * 40)

    for asm in reasoner.all_assumptions():
        print(f"   {asm.content}")
        print(f"     Contrary: {asm.contrary}")
        print(f"     Status: {asm.status.value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Assumption-Based Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
