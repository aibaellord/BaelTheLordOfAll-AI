#!/usr/bin/env python3
"""
BAEL - Argumentation Engine
Advanced argumentation and debate reasoning.

Features:
- Argument construction
- Attack and support relations
- Dung's abstract argumentation
- Structured argumentation (ASPIC+)
- Argument evaluation
- Debate management
- Burden of proof
"""

import asyncio
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

class ArgumentType(Enum):
    """Types of arguments."""
    CLAIM = "claim"
    PREMISE = "premise"
    CONCLUSION = "conclusion"
    REBUTTAL = "rebuttal"
    UNDERCUTTER = "undercutter"
    DEFEATER = "defeater"


class AttackType(Enum):
    """Types of attacks between arguments."""
    REBUT = "rebut"           # Attack on conclusion
    UNDERCUT = "undercut"     # Attack on inference
    UNDERMINE = "undermine"   # Attack on premise


class SupportType(Enum):
    """Types of support relations."""
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    ANALOGICAL = "analogical"


class ArgumentStatus(Enum):
    """Status of an argument in evaluation."""
    IN = "in"                 # Accepted
    OUT = "out"               # Rejected
    UNDECIDED = "undecided"   # Cannot determine
    BLOCKED = "blocked"       # Self-defeating


class SemanticType(Enum):
    """Argumentation semantics."""
    GROUNDED = "grounded"
    PREFERRED = "preferred"
    STABLE = "stable"
    COMPLETE = "complete"
    ADMISSIBLE = "admissible"


class DebatePhase(Enum):
    """Phases of a debate."""
    OPENING = "opening"
    ARGUMENTATION = "argumentation"
    REBUTTAL = "rebuttal"
    CLOSING = "closing"
    CONCLUDED = "concluded"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Argument:
    """An argument in the framework."""
    argument_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    argument_type: ArgumentType = ArgumentType.CLAIM
    premises: List[str] = field(default_factory=list)
    conclusion: str = ""
    strength: float = 1.0
    author: str = ""
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class Attack:
    """An attack between arguments."""
    attack_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    attacker_id: str = ""
    target_id: str = ""
    attack_type: AttackType = AttackType.REBUT
    strength: float = 1.0


@dataclass
class Support:
    """A support relation between arguments."""
    support_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    supporter_id: str = ""
    supported_id: str = ""
    support_type: SupportType = SupportType.DEDUCTIVE
    strength: float = 1.0


@dataclass
class Extension:
    """A set of acceptable arguments."""
    extension_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    semantic: SemanticType = SemanticType.GROUNDED
    arguments: Set[str] = field(default_factory=set)


@dataclass
class Debate:
    """A debate between parties."""
    debate_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    phase: DebatePhase = DebatePhase.OPENING
    participants: List[str] = field(default_factory=list)
    arguments: List[str] = field(default_factory=list)
    winner: Optional[str] = None


@dataclass
class EvaluationResult:
    """Result of argument evaluation."""
    argument_id: str = ""
    status: ArgumentStatus = ArgumentStatus.UNDECIDED
    credibility: float = 0.0
    attackers: List[str] = field(default_factory=list)
    defenders: List[str] = field(default_factory=list)


# =============================================================================
# ARGUMENT BUILDER
# =============================================================================

class ArgumentBuilder:
    """Build structured arguments."""

    def __init__(self):
        self._premises: List[str] = []
        self._conclusion: str = ""
        self._name: str = ""
        self._argument_type: ArgumentType = ArgumentType.CLAIM
        self._strength: float = 1.0

    def name(self, name: str) -> 'ArgumentBuilder':
        """Set argument name."""
        self._name = name
        return self

    def premise(self, premise: str) -> 'ArgumentBuilder':
        """Add a premise."""
        self._premises.append(premise)
        return self

    def premises(self, *premises: str) -> 'ArgumentBuilder':
        """Add multiple premises."""
        self._premises.extend(premises)
        return self

    def conclusion(self, conclusion: str) -> 'ArgumentBuilder':
        """Set conclusion."""
        self._conclusion = conclusion
        return self

    def type(self, arg_type: ArgumentType) -> 'ArgumentBuilder':
        """Set argument type."""
        self._argument_type = arg_type
        return self

    def strength(self, strength: float) -> 'ArgumentBuilder':
        """Set argument strength."""
        self._strength = max(0.0, min(1.0, strength))
        return self

    def build(self) -> Argument:
        """Build the argument."""
        return Argument(
            name=self._name,
            argument_type=self._argument_type,
            premises=self._premises.copy(),
            conclusion=self._conclusion,
            strength=self._strength
        )

    def reset(self) -> 'ArgumentBuilder':
        """Reset builder."""
        self._premises.clear()
        self._conclusion = ""
        self._name = ""
        self._argument_type = ArgumentType.CLAIM
        self._strength = 1.0
        return self


# =============================================================================
# ATTACK GRAPH
# =============================================================================

class AttackGraph:
    """Manage attack relations."""

    def __init__(self):
        self._attacks: Dict[str, Attack] = {}
        self._attackers: Dict[str, Set[str]] = defaultdict(set)  # target -> attackers
        self._targets: Dict[str, Set[str]] = defaultdict(set)    # attacker -> targets

    def add_attack(
        self,
        attacker_id: str,
        target_id: str,
        attack_type: AttackType = AttackType.REBUT,
        strength: float = 1.0
    ) -> Attack:
        """Add an attack."""
        attack = Attack(
            attacker_id=attacker_id,
            target_id=target_id,
            attack_type=attack_type,
            strength=strength
        )

        self._attacks[attack.attack_id] = attack
        self._attackers[target_id].add(attacker_id)
        self._targets[attacker_id].add(target_id)

        return attack

    def get_attackers(self, argument_id: str) -> Set[str]:
        """Get all attackers of an argument."""
        return self._attackers[argument_id].copy()

    def get_targets(self, argument_id: str) -> Set[str]:
        """Get all arguments attacked by an argument."""
        return self._targets[argument_id].copy()

    def is_attacked(self, argument_id: str) -> bool:
        """Check if argument is attacked."""
        return len(self._attackers[argument_id]) > 0

    def attacks(self, attacker_id: str, target_id: str) -> bool:
        """Check if attacker attacks target."""
        return target_id in self._targets[attacker_id]

    def remove_attack(self, attack_id: str) -> bool:
        """Remove an attack."""
        attack = self._attacks.get(attack_id)
        if not attack:
            return False

        self._attackers[attack.target_id].discard(attack.attacker_id)
        self._targets[attack.attacker_id].discard(attack.target_id)
        del self._attacks[attack_id]

        return True

    def get_all_attacks(self) -> List[Attack]:
        """Get all attacks."""
        return list(self._attacks.values())


# =============================================================================
# SUPPORT GRAPH
# =============================================================================

class SupportGraph:
    """Manage support relations."""

    def __init__(self):
        self._supports: Dict[str, Support] = {}
        self._supporters: Dict[str, Set[str]] = defaultdict(set)
        self._supported: Dict[str, Set[str]] = defaultdict(set)

    def add_support(
        self,
        supporter_id: str,
        supported_id: str,
        support_type: SupportType = SupportType.DEDUCTIVE,
        strength: float = 1.0
    ) -> Support:
        """Add a support relation."""
        support = Support(
            supporter_id=supporter_id,
            supported_id=supported_id,
            support_type=support_type,
            strength=strength
        )

        self._supports[support.support_id] = support
        self._supporters[supported_id].add(supporter_id)
        self._supported[supporter_id].add(supported_id)

        return support

    def get_supporters(self, argument_id: str) -> Set[str]:
        """Get all supporters of an argument."""
        return self._supporters[argument_id].copy()

    def get_supported(self, argument_id: str) -> Set[str]:
        """Get all arguments supported by an argument."""
        return self._supported[argument_id].copy()

    def is_supported(self, argument_id: str) -> bool:
        """Check if argument is supported."""
        return len(self._supporters[argument_id]) > 0


# =============================================================================
# SEMANTICS EVALUATOR
# =============================================================================

class SemanticsEvaluator:
    """
    Evaluate arguments using Dung's semantics.
    """

    def __init__(self, attack_graph: AttackGraph):
        self._attack_graph = attack_graph

    def is_conflict_free(
        self,
        extension: Set[str],
        arguments: Set[str]
    ) -> bool:
        """Check if extension is conflict-free."""
        for arg1 in extension:
            for arg2 in extension:
                if arg1 != arg2:
                    if self._attack_graph.attacks(arg1, arg2):
                        return False
        return True

    def defends(
        self,
        extension: Set[str],
        argument: str
    ) -> bool:
        """Check if extension defends an argument."""
        attackers = self._attack_graph.get_attackers(argument)

        for attacker in attackers:
            # Extension must attack each attacker
            defended = False
            for defender in extension:
                if self._attack_graph.attacks(defender, attacker):
                    defended = True
                    break

            if not defended:
                return False

        return True

    def is_admissible(
        self,
        extension: Set[str],
        arguments: Set[str]
    ) -> bool:
        """Check if extension is admissible."""
        if not self.is_conflict_free(extension, arguments):
            return False

        for arg in extension:
            if not self.defends(extension, arg):
                return False

        return True

    def grounded_extension(
        self,
        arguments: Set[str]
    ) -> Extension:
        """Compute grounded extension (skeptical)."""
        extension: Set[str] = set()
        changed = True

        while changed:
            changed = False

            for arg in arguments:
                if arg in extension:
                    continue

                # Check if unattacked or defended by current extension
                attackers = self._attack_graph.get_attackers(arg)

                if not attackers:
                    # Unattacked
                    extension.add(arg)
                    changed = True
                elif self.defends(extension, arg):
                    extension.add(arg)
                    changed = True

        return Extension(
            semantic=SemanticType.GROUNDED,
            arguments=extension
        )

    def preferred_extensions(
        self,
        arguments: Set[str]
    ) -> List[Extension]:
        """Compute preferred extensions (credulous)."""
        admissible_sets = self._find_admissible_sets(arguments)

        # Find maximal admissible sets
        preferred = []

        for adm_set in admissible_sets:
            is_maximal = True
            for other in admissible_sets:
                if adm_set < other:  # Strict subset
                    is_maximal = False
                    break

            if is_maximal:
                preferred.append(Extension(
                    semantic=SemanticType.PREFERRED,
                    arguments=adm_set
                ))

        return preferred if preferred else [Extension(semantic=SemanticType.PREFERRED)]

    def stable_extensions(
        self,
        arguments: Set[str]
    ) -> List[Extension]:
        """Compute stable extensions."""
        stable = []

        for ext in self._power_set(arguments):
            if not self.is_conflict_free(ext, arguments):
                continue

            # Check if attacks all outside arguments
            attacks_all = True
            for arg in arguments - ext:
                attacked = False
                for defender in ext:
                    if self._attack_graph.attacks(defender, arg):
                        attacked = True
                        break

                if not attacked:
                    attacks_all = False
                    break

            if attacks_all:
                stable.append(Extension(
                    semantic=SemanticType.STABLE,
                    arguments=ext
                ))

        return stable

    def _find_admissible_sets(
        self,
        arguments: Set[str]
    ) -> List[Set[str]]:
        """Find all admissible sets."""
        admissible = []

        for subset in self._power_set(arguments):
            if self.is_admissible(subset, arguments):
                admissible.append(subset)

        return admissible

    def _power_set(self, s: Set[str]) -> List[Set[str]]:
        """Generate power set (limited for efficiency)."""
        result = [set()]

        for elem in s:
            new_subsets = [subset | {elem} for subset in result]
            result.extend(new_subsets)

            # Limit for large sets
            if len(result) > 1000:
                break

        return result


# =============================================================================
# ARGUMENT EVALUATOR
# =============================================================================

class ArgumentEvaluator:
    """Evaluate individual arguments."""

    def __init__(
        self,
        attack_graph: AttackGraph,
        support_graph: SupportGraph
    ):
        self._attack_graph = attack_graph
        self._support_graph = support_graph

    def evaluate(
        self,
        argument_id: str,
        arguments: Dict[str, Argument],
        accepted: Set[str]
    ) -> EvaluationResult:
        """Evaluate an argument."""
        attackers = list(self._attack_graph.get_attackers(argument_id))
        supporters = list(self._support_graph.get_supporters(argument_id))

        # Check if in accepted set
        if argument_id in accepted:
            status = ArgumentStatus.IN
        elif self._all_attackers_out(argument_id, accepted):
            status = ArgumentStatus.IN
        elif self._has_accepted_attacker(argument_id, accepted):
            status = ArgumentStatus.OUT
        else:
            status = ArgumentStatus.UNDECIDED

        # Calculate credibility
        argument = arguments.get(argument_id)
        base_strength = argument.strength if argument else 0.5

        attack_penalty = sum(
            arguments.get(a, Argument()).strength
            for a in attackers
            if a in accepted
        ) * 0.2

        support_bonus = sum(
            arguments.get(s, Argument()).strength
            for s in supporters
            if s in accepted
        ) * 0.1

        credibility = max(0.0, min(1.0, base_strength - attack_penalty + support_bonus))

        return EvaluationResult(
            argument_id=argument_id,
            status=status,
            credibility=credibility,
            attackers=attackers,
            defenders=supporters
        )

    def _all_attackers_out(
        self,
        argument_id: str,
        accepted: Set[str]
    ) -> bool:
        """Check if all attackers are out."""
        attackers = self._attack_graph.get_attackers(argument_id)

        if not attackers:
            return True

        for attacker in attackers:
            # Check if attacker has no accepted attackers
            attacker_attackers = self._attack_graph.get_attackers(attacker)
            if not any(a in accepted for a in attacker_attackers):
                return False

        return True

    def _has_accepted_attacker(
        self,
        argument_id: str,
        accepted: Set[str]
    ) -> bool:
        """Check if has an accepted attacker."""
        attackers = self._attack_graph.get_attackers(argument_id)
        return any(a in accepted for a in attackers)


# =============================================================================
# DEBATE MANAGER
# =============================================================================

class DebateManager:
    """Manage debates between parties."""

    def __init__(self, argumentation_framework: 'ArgumentationEngine'):
        self._framework = argumentation_framework
        self._debates: Dict[str, Debate] = {}

    def create_debate(
        self,
        topic: str,
        participants: List[str]
    ) -> Debate:
        """Create a new debate."""
        debate = Debate(
            topic=topic,
            participants=participants,
            phase=DebatePhase.OPENING
        )
        self._debates[debate.debate_id] = debate
        return debate

    def submit_argument(
        self,
        debate_id: str,
        argument: Argument,
        participant: str
    ) -> bool:
        """Submit an argument to a debate."""
        debate = self._debates.get(debate_id)
        if not debate:
            return False

        if participant not in debate.participants:
            return False

        if debate.phase == DebatePhase.CONCLUDED:
            return False

        argument.author = participant
        self._framework.add_argument(argument)
        debate.arguments.append(argument.argument_id)

        return True

    def advance_phase(self, debate_id: str) -> DebatePhase:
        """Advance debate to next phase."""
        debate = self._debates.get(debate_id)
        if not debate:
            return DebatePhase.CONCLUDED

        phase_order = [
            DebatePhase.OPENING,
            DebatePhase.ARGUMENTATION,
            DebatePhase.REBUTTAL,
            DebatePhase.CLOSING,
            DebatePhase.CONCLUDED
        ]

        current_idx = phase_order.index(debate.phase)
        if current_idx < len(phase_order) - 1:
            debate.phase = phase_order[current_idx + 1]

        return debate.phase

    def conclude_debate(
        self,
        debate_id: str
    ) -> Optional[str]:
        """Conclude debate and determine winner."""
        debate = self._debates.get(debate_id)
        if not debate:
            return None

        debate.phase = DebatePhase.CONCLUDED

        # Count accepted arguments per participant
        arguments = set(debate.arguments)
        grounded = self._framework.compute_grounded_extension()

        accepted_by_participant: Dict[str, int] = defaultdict(int)

        for arg_id in grounded.arguments:
            if arg_id in arguments:
                arg = self._framework.get_argument(arg_id)
                if arg:
                    accepted_by_participant[arg.author] += 1

        if accepted_by_participant:
            winner = max(
                accepted_by_participant.keys(),
                key=lambda p: accepted_by_participant[p]
            )
            debate.winner = winner
            return winner

        return None


# =============================================================================
# ARGUMENTATION ENGINE
# =============================================================================

class ArgumentationEngine:
    """
    Argumentation Engine for BAEL.

    Advanced argumentation and debate reasoning.
    """

    def __init__(self):
        self._arguments: Dict[str, Argument] = {}
        self._attack_graph = AttackGraph()
        self._support_graph = SupportGraph()
        self._semantics = SemanticsEvaluator(self._attack_graph)
        self._evaluator = ArgumentEvaluator(self._attack_graph, self._support_graph)
        self._debate_manager = DebateManager(self)

    # -------------------------------------------------------------------------
    # ARGUMENT MANAGEMENT
    # -------------------------------------------------------------------------

    def add_argument(self, argument: Argument) -> None:
        """Add an argument."""
        self._arguments[argument.argument_id] = argument

    def create_argument(
        self,
        name: str,
        premises: List[str],
        conclusion: str,
        strength: float = 1.0
    ) -> Argument:
        """Create and add an argument."""
        argument = Argument(
            name=name,
            premises=premises,
            conclusion=conclusion,
            strength=strength
        )
        self._arguments[argument.argument_id] = argument
        return argument

    def get_argument(self, argument_id: str) -> Optional[Argument]:
        """Get an argument."""
        return self._arguments.get(argument_id)

    def get_all_arguments(self) -> List[Argument]:
        """Get all arguments."""
        return list(self._arguments.values())

    def builder(self) -> ArgumentBuilder:
        """Get an argument builder."""
        return ArgumentBuilder()

    # -------------------------------------------------------------------------
    # ATTACK RELATIONS
    # -------------------------------------------------------------------------

    def add_attack(
        self,
        attacker_id: str,
        target_id: str,
        attack_type: AttackType = AttackType.REBUT,
        strength: float = 1.0
    ) -> Attack:
        """Add an attack."""
        return self._attack_graph.add_attack(
            attacker_id, target_id, attack_type, strength
        )

    def rebuts(
        self,
        attacker_id: str,
        target_id: str
    ) -> Attack:
        """Add a rebuttal attack."""
        return self.add_attack(attacker_id, target_id, AttackType.REBUT)

    def undercuts(
        self,
        attacker_id: str,
        target_id: str
    ) -> Attack:
        """Add an undercut attack."""
        return self.add_attack(attacker_id, target_id, AttackType.UNDERCUT)

    def undermines(
        self,
        attacker_id: str,
        target_id: str
    ) -> Attack:
        """Add an undermine attack."""
        return self.add_attack(attacker_id, target_id, AttackType.UNDERMINE)

    def get_attackers(self, argument_id: str) -> Set[str]:
        """Get attackers of an argument."""
        return self._attack_graph.get_attackers(argument_id)

    # -------------------------------------------------------------------------
    # SUPPORT RELATIONS
    # -------------------------------------------------------------------------

    def add_support(
        self,
        supporter_id: str,
        supported_id: str,
        support_type: SupportType = SupportType.DEDUCTIVE,
        strength: float = 1.0
    ) -> Support:
        """Add a support relation."""
        return self._support_graph.add_support(
            supporter_id, supported_id, support_type, strength
        )

    def get_supporters(self, argument_id: str) -> Set[str]:
        """Get supporters of an argument."""
        return self._support_graph.get_supporters(argument_id)

    # -------------------------------------------------------------------------
    # SEMANTICS
    # -------------------------------------------------------------------------

    def compute_grounded_extension(self) -> Extension:
        """Compute grounded extension."""
        return self._semantics.grounded_extension(set(self._arguments.keys()))

    def compute_preferred_extensions(self) -> List[Extension]:
        """Compute preferred extensions."""
        return self._semantics.preferred_extensions(set(self._arguments.keys()))

    def compute_stable_extensions(self) -> List[Extension]:
        """Compute stable extensions."""
        return self._semantics.stable_extensions(set(self._arguments.keys()))

    def is_skeptically_accepted(self, argument_id: str) -> bool:
        """Check if argument is skeptically accepted."""
        grounded = self.compute_grounded_extension()
        return argument_id in grounded.arguments

    def is_credulously_accepted(self, argument_id: str) -> bool:
        """Check if argument is credulously accepted."""
        preferred = self.compute_preferred_extensions()
        return any(argument_id in ext.arguments for ext in preferred)

    # -------------------------------------------------------------------------
    # EVALUATION
    # -------------------------------------------------------------------------

    def evaluate_argument(
        self,
        argument_id: str
    ) -> EvaluationResult:
        """Evaluate a single argument."""
        grounded = self.compute_grounded_extension()
        return self._evaluator.evaluate(
            argument_id, self._arguments, grounded.arguments
        )

    def evaluate_all(self) -> Dict[str, EvaluationResult]:
        """Evaluate all arguments."""
        grounded = self.compute_grounded_extension()

        results = {}
        for arg_id in self._arguments:
            results[arg_id] = self._evaluator.evaluate(
                arg_id, self._arguments, grounded.arguments
            )

        return results

    # -------------------------------------------------------------------------
    # DEBATE
    # -------------------------------------------------------------------------

    def create_debate(
        self,
        topic: str,
        participants: List[str]
    ) -> Debate:
        """Create a debate."""
        return self._debate_manager.create_debate(topic, participants)

    def submit_to_debate(
        self,
        debate_id: str,
        argument: Argument,
        participant: str
    ) -> bool:
        """Submit argument to debate."""
        return self._debate_manager.submit_argument(debate_id, argument, participant)

    def conclude_debate(self, debate_id: str) -> Optional[str]:
        """Conclude a debate."""
        return self._debate_manager.conclude_debate(debate_id)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Argumentation Engine."""
    print("=" * 70)
    print("BAEL - ARGUMENTATION ENGINE DEMO")
    print("Advanced Argumentation and Debate Reasoning")
    print("=" * 70)
    print()

    engine = ArgumentationEngine()

    # 1. Create Arguments
    print("1. CREATE ARGUMENTS:")
    print("-" * 40)

    a = engine.create_argument(
        "A",
        premises=["The sky is clear"],
        conclusion="It will not rain",
        strength=0.8
    )

    b = engine.create_argument(
        "B",
        premises=["Weather forecast says rain"],
        conclusion="It will rain",
        strength=0.9
    )

    c = engine.create_argument(
        "C",
        premises=["Forecast is often wrong in summer"],
        conclusion="Forecast is unreliable",
        strength=0.7
    )

    d = engine.create_argument(
        "D",
        premises=["Barometer shows low pressure"],
        conclusion="It will rain",
        strength=0.85
    )

    print(f"   {a.name}: {a.conclusion} (strength={a.strength})")
    print(f"   {b.name}: {b.conclusion} (strength={b.strength})")
    print(f"   {c.name}: {c.conclusion} (strength={c.strength})")
    print(f"   {d.name}: {d.conclusion} (strength={d.strength})")
    print()

    # 2. Add Attack Relations
    print("2. ATTACK RELATIONS:")
    print("-" * 40)

    engine.rebuts(a.argument_id, b.argument_id)
    print(f"   A rebuts B")

    engine.rebuts(b.argument_id, a.argument_id)
    print(f"   B rebuts A")

    engine.undercuts(c.argument_id, b.argument_id)
    print(f"   C undercuts B")

    engine.rebuts(d.argument_id, a.argument_id)
    print(f"   D rebuts A")
    print()

    # 3. Grounded Extension
    print("3. GROUNDED EXTENSION (Skeptical):")
    print("-" * 40)

    grounded = engine.compute_grounded_extension()
    accepted_names = [
        engine.get_argument(aid).name
        for aid in grounded.arguments
        if engine.get_argument(aid)
    ]
    print(f"   Accepted arguments: {accepted_names}")
    print()

    # 4. Preferred Extensions
    print("4. PREFERRED EXTENSIONS (Credulous):")
    print("-" * 40)

    preferred = engine.compute_preferred_extensions()
    for i, ext in enumerate(preferred):
        names = [
            engine.get_argument(aid).name
            for aid in ext.arguments
            if engine.get_argument(aid)
        ]
        print(f"   Extension {i+1}: {names}")
    print()

    # 5. Acceptance Tests
    print("5. ACCEPTANCE TESTS:")
    print("-" * 40)

    for arg in [a, b, c, d]:
        skeptical = engine.is_skeptically_accepted(arg.argument_id)
        credulous = engine.is_credulously_accepted(arg.argument_id)
        print(f"   {arg.name}: skeptical={skeptical}, credulous={credulous}")
    print()

    # 6. Argument Evaluation
    print("6. ARGUMENT EVALUATION:")
    print("-" * 40)

    for arg in [a, b, c, d]:
        result = engine.evaluate_argument(arg.argument_id)
        print(f"   {arg.name}:")
        print(f"     Status: {result.status.value}")
        print(f"     Credibility: {result.credibility:.2f}")
    print()

    # 7. Using Builder
    print("7. ARGUMENT BUILDER:")
    print("-" * 40)

    builder = engine.builder()
    e = (builder
        .name("E")
        .premise("Historical data shows pattern")
        .premise("Current conditions match pattern")
        .conclusion("Pattern will repeat")
        .strength(0.75)
        .build())

    engine.add_argument(e)
    print(f"   Built argument: {e.name}")
    print(f"   Premises: {e.premises}")
    print(f"   Conclusion: {e.conclusion}")
    print()

    # 8. Support Relations
    print("8. SUPPORT RELATIONS:")
    print("-" * 40)

    engine.add_support(e.argument_id, d.argument_id, SupportType.INDUCTIVE)
    print(f"   E supports D (inductive)")

    supporters = engine.get_supporters(d.argument_id)
    print(f"   D's supporters: {len(supporters)}")
    print()

    # 9. Debate Simulation
    print("9. DEBATE SIMULATION:")
    print("-" * 40)

    debate = engine.create_debate(
        "Will it rain tomorrow?",
        ["Alice", "Bob"]
    )
    print(f"   Debate topic: {debate.topic}")

    alice_arg = engine.create_argument(
        "Alice-1",
        ["Cloud cover is increasing"],
        "Rain is likely",
        strength=0.8
    )

    bob_arg = engine.create_argument(
        "Bob-1",
        ["Wind is blowing clouds away"],
        "Rain is unlikely",
        strength=0.7
    )

    engine.submit_to_debate(debate.debate_id, alice_arg, "Alice")
    engine.submit_to_debate(debate.debate_id, bob_arg, "Bob")

    engine.rebuts(bob_arg.argument_id, alice_arg.argument_id)

    winner = engine.conclude_debate(debate.debate_id)
    print(f"   Winner: {winner}")
    print()

    # 10. Complex Framework
    print("10. COMPLEX ARGUMENTATION:")
    print("-" * 40)

    # Add more interconnected arguments
    f = engine.create_argument("F", ["Premise F"], "Conclusion F", 0.6)
    g = engine.create_argument("G", ["Premise G"], "Conclusion G", 0.9)

    engine.rebuts(f.argument_id, g.argument_id)
    engine.rebuts(g.argument_id, f.argument_id)

    all_results = engine.evaluate_all()

    in_count = sum(1 for r in all_results.values() if r.status == ArgumentStatus.IN)
    out_count = sum(1 for r in all_results.values() if r.status == ArgumentStatus.OUT)
    undecided = sum(1 for r in all_results.values() if r.status == ArgumentStatus.UNDECIDED)

    print(f"   Total arguments: {len(all_results)}")
    print(f"   IN: {in_count}, OUT: {out_count}, UNDECIDED: {undecided}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Argumentation Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
