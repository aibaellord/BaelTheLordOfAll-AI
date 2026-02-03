#!/usr/bin/env python3
"""
BAEL - Default Reasoner
Advanced non-monotonic reasoning with defaults.

Features:
- Default rules
- Exception handling
- Non-monotonic inference
- Belief revision
- Specificity ordering
- Reasoning with incomplete information
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

class ReasoningMode(Enum):
    """Reasoning mode for default logic."""
    CREDULOUS = "credulous"  # At least one extension supports conclusion
    SKEPTICAL = "skeptical"  # All extensions support conclusion


class DefaultStatus(Enum):
    """Status of a default rule."""
    APPLICABLE = "applicable"
    BLOCKED = "blocked"
    APPLIED = "applied"
    INAPPLICABLE = "inapplicable"


class InferenceType(Enum):
    """Types of inference."""
    MONOTONIC = "monotonic"
    NON_MONOTONIC = "non_monotonic"
    DEFAULT = "default"
    EXCEPTION = "exception"


class ConflictResolution(Enum):
    """Conflict resolution strategies."""
    SPECIFICITY = "specificity"
    PRIORITY = "priority"
    RECENCY = "recency"
    CREDIBILITY = "credibility"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Literal:
    """A propositional literal."""
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

    def negate(self) -> 'Literal':
        """Return the negation of this literal."""
        return Literal(
            predicate=self.predicate,
            arguments=self.arguments.copy(),
            negated=not self.negated
        )


@dataclass
class DefaultRule:
    """A default rule: prerequisite : justification / consequent."""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    prerequisite: Optional[Literal] = None  # The prerequisite (can be None for normal defaults)
    justifications: List[Literal] = field(default_factory=list)  # What must be consistent
    consequent: Literal = field(default_factory=Literal)  # The conclusion
    priority: int = 0  # Higher = more priority
    specificity: int = 0  # Higher = more specific


@dataclass
class Extension:
    """An extension in default logic."""
    ext_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    facts: Set[str] = field(default_factory=set)  # Literal strings
    applied_defaults: List[str] = field(default_factory=list)


@dataclass
class InferenceResult:
    """Result of an inference."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    supported: bool = False
    inference_type: InferenceType = InferenceType.DEFAULT
    supporting_extensions: List[str] = field(default_factory=list)
    applied_rules: List[str] = field(default_factory=list)
    reasoning_chain: List[str] = field(default_factory=list)


@dataclass
class ExceptionRecord:
    """Record of an exception to a default."""
    exception_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    default_id: str = ""
    exception: Literal = field(default_factory=Literal)
    reason: str = ""


# =============================================================================
# LITERAL MANAGER
# =============================================================================

class LiteralManager:
    """Manage literals."""

    def __init__(self):
        self._literals: Dict[str, Literal] = {}

    def create_literal(
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
        self._literals[lit.lit_id] = lit
        return lit

    def negate(self, literal: Literal) -> Literal:
        """Get the negation of a literal."""
        return literal.negate()

    def parse(self, text: str) -> Literal:
        """Parse a literal from text."""
        negated = text.startswith("¬") or text.startswith("~") or text.startswith("not ")
        clean = text.lstrip("¬~").replace("not ", "")

        # Parse predicate(arg1, arg2, ...)
        if "(" in clean:
            pred = clean[:clean.index("(")]
            args_str = clean[clean.index("(") + 1:clean.rindex(")")]
            args = [a.strip() for a in args_str.split(",")] if args_str else []
        else:
            pred = clean.strip()
            args = []

        return self.create_literal(pred, args, negated)

    def get_literal(self, lit_id: str) -> Optional[Literal]:
        """Get a literal by ID."""
        return self._literals.get(lit_id)


# =============================================================================
# DEFAULT RULE MANAGER
# =============================================================================

class DefaultRuleManager:
    """Manage default rules."""

    def __init__(self, literal_manager: LiteralManager):
        self._literals = literal_manager
        self._rules: Dict[str, DefaultRule] = {}

    def create_default(
        self,
        name: str,
        prerequisite: Optional[Literal] = None,
        justifications: Optional[List[Literal]] = None,
        consequent: Optional[Literal] = None,
        priority: int = 0,
        specificity: int = 0
    ) -> DefaultRule:
        """Create a default rule."""
        rule = DefaultRule(
            name=name,
            prerequisite=prerequisite,
            justifications=justifications or [],
            consequent=consequent or Literal(),
            priority=priority,
            specificity=specificity
        )
        self._rules[rule.rule_id] = rule
        return rule

    def get_rule(self, rule_id: str) -> Optional[DefaultRule]:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def all_rules(self) -> List[DefaultRule]:
        """Get all rules."""
        return list(self._rules.values())

    def get_by_consequent(self, predicate: str) -> List[DefaultRule]:
        """Get rules with given consequent predicate."""
        return [r for r in self._rules.values()
                if r.consequent.predicate == predicate]


# =============================================================================
# KNOWLEDGE BASE
# =============================================================================

class DefaultKnowledgeBase:
    """Knowledge base with facts and defaults."""

    def __init__(self):
        self._facts: Set[str] = set()  # String representations
        self._fact_literals: Dict[str, Literal] = {}

    def add_fact(self, literal: Literal) -> None:
        """Add a fact to the knowledge base."""
        lit_str = str(literal)
        self._facts.add(lit_str)
        self._fact_literals[lit_str] = literal

    def remove_fact(self, literal: Literal) -> bool:
        """Remove a fact from the knowledge base."""
        lit_str = str(literal)
        if lit_str in self._facts:
            self._facts.remove(lit_str)
            del self._fact_literals[lit_str]
            return True
        return False

    def contains(self, literal: Literal) -> bool:
        """Check if literal is in knowledge base."""
        return str(literal) in self._facts

    def is_consistent_with(self, literal: Literal) -> bool:
        """Check if literal is consistent with KB (negation not present)."""
        return str(literal.negate()) not in self._facts

    def all_facts(self) -> Set[str]:
        """Get all facts."""
        return self._facts.copy()

    def copy(self) -> 'DefaultKnowledgeBase':
        """Create a copy of this KB."""
        new_kb = DefaultKnowledgeBase()
        new_kb._facts = self._facts.copy()
        new_kb._fact_literals = self._fact_literals.copy()
        return new_kb


# =============================================================================
# EXCEPTION HANDLER
# =============================================================================

class ExceptionHandler:
    """Handle exceptions to defaults."""

    def __init__(self):
        self._exceptions: Dict[str, List[ExceptionRecord]] = defaultdict(list)

    def add_exception(
        self,
        default_id: str,
        exception: Literal,
        reason: str = ""
    ) -> ExceptionRecord:
        """Add an exception to a default."""
        record = ExceptionRecord(
            default_id=default_id,
            exception=exception,
            reason=reason
        )
        self._exceptions[default_id].append(record)
        return record

    def has_exception(
        self,
        default_id: str,
        kb: DefaultKnowledgeBase
    ) -> bool:
        """Check if a default has an active exception."""
        exceptions = self._exceptions.get(default_id, [])
        for exc in exceptions:
            if kb.contains(exc.exception):
                return True
        return False

    def get_exceptions(self, default_id: str) -> List[ExceptionRecord]:
        """Get exceptions for a default."""
        return self._exceptions.get(default_id, [])


# =============================================================================
# EXTENSION BUILDER
# =============================================================================

class ExtensionBuilder:
    """Build extensions in default logic."""

    def __init__(
        self,
        rule_manager: DefaultRuleManager,
        exception_handler: ExceptionHandler
    ):
        self._rules = rule_manager
        self._exceptions = exception_handler

    def compute_extensions(
        self,
        initial_kb: DefaultKnowledgeBase,
        conflict_resolution: ConflictResolution = ConflictResolution.PRIORITY
    ) -> List[Extension]:
        """Compute all extensions."""
        extensions = []

        # Start with initial facts
        base_ext = Extension(facts=initial_kb.all_facts())

        # Get applicable defaults
        applicable = self._get_applicable_defaults(initial_kb)

        if not applicable:
            extensions.append(base_ext)
            return extensions

        # Order by conflict resolution
        ordered = self._order_defaults(applicable, conflict_resolution)

        # Build extensions by applying defaults
        self._build_extensions(initial_kb, ordered, [], extensions)

        return extensions if extensions else [base_ext]

    def _get_applicable_defaults(
        self,
        kb: DefaultKnowledgeBase
    ) -> List[DefaultRule]:
        """Get defaults that are applicable given KB."""
        applicable = []

        for rule in self._rules.all_rules():
            # Check if has active exception
            if self._exceptions.has_exception(rule.rule_id, kb):
                continue

            # Check prerequisite
            if rule.prerequisite:
                if not kb.contains(rule.prerequisite):
                    continue

            # Check justifications (must be consistent)
            consistent = True
            for just in rule.justifications:
                if not kb.is_consistent_with(just):
                    consistent = False
                    break

            if consistent:
                applicable.append(rule)

        return applicable

    def _order_defaults(
        self,
        defaults: List[DefaultRule],
        resolution: ConflictResolution
    ) -> List[DefaultRule]:
        """Order defaults by conflict resolution strategy."""
        if resolution == ConflictResolution.PRIORITY:
            return sorted(defaults, key=lambda d: -d.priority)
        elif resolution == ConflictResolution.SPECIFICITY:
            return sorted(defaults, key=lambda d: -d.specificity)
        return defaults

    def _build_extensions(
        self,
        kb: DefaultKnowledgeBase,
        remaining: List[DefaultRule],
        applied: List[str],
        extensions: List[Extension]
    ) -> None:
        """Recursively build extensions."""
        if not remaining:
            ext = Extension(
                facts=kb.all_facts(),
                applied_defaults=applied.copy()
            )
            extensions.append(ext)
            return

        # Try applying first default
        rule = remaining[0]
        rest = remaining[1:]

        # Check if still applicable
        if self._is_applicable(rule, kb):
            # Apply the default
            new_kb = kb.copy()
            new_kb.add_fact(rule.consequent)
            new_applied = applied + [rule.rule_id]

            # Filter remaining rules that become inapplicable
            still_applicable = [r for r in rest if self._is_applicable(r, new_kb)]

            self._build_extensions(new_kb, still_applicable, new_applied, extensions)

        # Also try not applying it (if blocked)
        if not self._is_applicable(rule, kb) or len(remaining) > 1:
            self._build_extensions(kb, rest, applied, extensions)

    def _is_applicable(
        self,
        rule: DefaultRule,
        kb: DefaultKnowledgeBase
    ) -> bool:
        """Check if a rule is applicable in current KB state."""
        # Check prerequisite
        if rule.prerequisite:
            if not kb.contains(rule.prerequisite):
                return False

        # Check justifications
        for just in rule.justifications:
            if not kb.is_consistent_with(just):
                return False

        # Check consequent not already derived
        if kb.contains(rule.consequent):
            return False

        # Check consequent doesn't conflict
        if not kb.is_consistent_with(rule.consequent):
            return False

        return True


# =============================================================================
# DEFAULT INFERENCE ENGINE
# =============================================================================

class DefaultInferenceEngine:
    """Perform default logic inference."""

    def __init__(
        self,
        rule_manager: DefaultRuleManager,
        extension_builder: ExtensionBuilder
    ):
        self._rules = rule_manager
        self._extensions = extension_builder

    def infer(
        self,
        kb: DefaultKnowledgeBase,
        query: Literal,
        mode: ReasoningMode = ReasoningMode.SKEPTICAL
    ) -> InferenceResult:
        """Perform inference for a query."""
        query_str = str(query)

        # Compute extensions
        extensions = self._extensions.compute_extensions(kb)

        # Check query in extensions
        supporting = []

        for ext in extensions:
            if query_str in ext.facts:
                supporting.append(ext.ext_id)

        if mode == ReasoningMode.SKEPTICAL:
            # Must be in ALL extensions
            supported = len(supporting) == len(extensions) and len(extensions) > 0
        else:
            # Must be in at least one extension
            supported = len(supporting) > 0

        # Build reasoning chain
        chain = []
        if supporting:
            ext = next((e for e in extensions if e.ext_id == supporting[0]), None)
            if ext:
                for rule_id in ext.applied_defaults:
                    rule = self._rules.get_rule(rule_id)
                    if rule:
                        chain.append(f"Applied: {rule.name} -> {rule.consequent}")

        return InferenceResult(
            query=query_str,
            supported=supported,
            inference_type=InferenceType.DEFAULT,
            supporting_extensions=supporting,
            reasoning_chain=chain
        )

    def all_conclusions(
        self,
        kb: DefaultKnowledgeBase,
        mode: ReasoningMode = ReasoningMode.SKEPTICAL
    ) -> Set[str]:
        """Get all conclusions in given mode."""
        extensions = self._extensions.compute_extensions(kb)

        if not extensions:
            return set()

        if mode == ReasoningMode.SKEPTICAL:
            # Intersection of all extensions
            result = extensions[0].facts.copy()
            for ext in extensions[1:]:
                result &= ext.facts
            return result
        else:
            # Union of all extensions
            result = set()
            for ext in extensions:
                result |= ext.facts
            return result


# =============================================================================
# DEFAULT REASONER
# =============================================================================

class DefaultReasoner:
    """
    Default Reasoner for BAEL.

    Advanced non-monotonic reasoning with defaults.
    """

    def __init__(self):
        self._literals = LiteralManager()
        self._rules = DefaultRuleManager(self._literals)
        self._exceptions = ExceptionHandler()
        self._extensions = ExtensionBuilder(self._rules, self._exceptions)
        self._inference = DefaultInferenceEngine(self._rules, self._extensions)
        self._kb = DefaultKnowledgeBase()

    # -------------------------------------------------------------------------
    # LITERAL MANAGEMENT
    # -------------------------------------------------------------------------

    def create_literal(
        self,
        predicate: str,
        arguments: Optional[List[str]] = None,
        negated: bool = False
    ) -> Literal:
        """Create a literal."""
        return self._literals.create_literal(predicate, arguments, negated)

    def parse_literal(self, text: str) -> Literal:
        """Parse a literal from text."""
        return self._literals.parse(text)

    def negate(self, literal: Literal) -> Literal:
        """Get the negation of a literal."""
        return self._literals.negate(literal)

    # -------------------------------------------------------------------------
    # DEFAULT RULE MANAGEMENT
    # -------------------------------------------------------------------------

    def add_default(
        self,
        name: str,
        prerequisite: Optional[Literal] = None,
        justifications: Optional[List[Literal]] = None,
        consequent: Optional[Literal] = None,
        priority: int = 0,
        specificity: int = 0
    ) -> DefaultRule:
        """Add a default rule."""
        return self._rules.create_default(
            name, prerequisite, justifications, consequent, priority, specificity
        )

    def get_rule(self, rule_id: str) -> Optional[DefaultRule]:
        """Get a rule by ID."""
        return self._rules.get_rule(rule_id)

    def all_rules(self) -> List[DefaultRule]:
        """Get all rules."""
        return self._rules.all_rules()

    # -------------------------------------------------------------------------
    # KNOWLEDGE BASE
    # -------------------------------------------------------------------------

    def add_fact(self, literal: Literal) -> None:
        """Add a fact."""
        self._kb.add_fact(literal)

    def remove_fact(self, literal: Literal) -> bool:
        """Remove a fact."""
        return self._kb.remove_fact(literal)

    def has_fact(self, literal: Literal) -> bool:
        """Check if fact exists."""
        return self._kb.contains(literal)

    def all_facts(self) -> Set[str]:
        """Get all facts."""
        return self._kb.all_facts()

    # -------------------------------------------------------------------------
    # EXCEPTIONS
    # -------------------------------------------------------------------------

    def add_exception(
        self,
        default_id: str,
        exception: Literal,
        reason: str = ""
    ) -> ExceptionRecord:
        """Add an exception to a default."""
        return self._exceptions.add_exception(default_id, exception, reason)

    def get_exceptions(self, default_id: str) -> List[ExceptionRecord]:
        """Get exceptions for a default."""
        return self._exceptions.get_exceptions(default_id)

    # -------------------------------------------------------------------------
    # INFERENCE
    # -------------------------------------------------------------------------

    def infer(
        self,
        query: Literal,
        mode: ReasoningMode = ReasoningMode.SKEPTICAL
    ) -> InferenceResult:
        """Infer whether query holds."""
        return self._inference.infer(self._kb, query, mode)

    def all_conclusions(
        self,
        mode: ReasoningMode = ReasoningMode.SKEPTICAL
    ) -> Set[str]:
        """Get all conclusions."""
        return self._inference.all_conclusions(self._kb, mode)

    def compute_extensions(
        self,
        conflict_resolution: ConflictResolution = ConflictResolution.PRIORITY
    ) -> List[Extension]:
        """Compute all extensions."""
        return self._extensions.compute_extensions(
            self._kb, conflict_resolution
        )


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Default Reasoner."""
    print("=" * 70)
    print("BAEL - DEFAULT REASONER DEMO")
    print("Advanced Non-Monotonic Reasoning with Defaults")
    print("=" * 70)
    print()

    reasoner = DefaultReasoner()

    # 1. Create Literals
    print("1. CREATE LITERALS:")
    print("-" * 40)

    bird = reasoner.create_literal("bird", ["tweety"])
    penguin = reasoner.create_literal("penguin", ["tweety"])
    flies = reasoner.create_literal("flies", ["tweety"])
    not_flies = reasoner.negate(flies)

    ostrich = reasoner.create_literal("ostrich", ["oscar"])
    bird_oscar = reasoner.create_literal("bird", ["oscar"])
    flies_oscar = reasoner.create_literal("flies", ["oscar"])

    print(f"   {bird}")
    print(f"   {penguin}")
    print(f"   {flies}")
    print(f"   {not_flies}")
    print()

    # 2. Add Default Rules
    print("2. ADD DEFAULT RULES:")
    print("-" * 40)

    # Birds typically fly (unless we know otherwise)
    birds_fly = reasoner.add_default(
        name="Birds typically fly",
        prerequisite=reasoner.create_literal("bird", ["X"]),
        justifications=[reasoner.create_literal("flies", ["X"])],
        consequent=reasoner.create_literal("flies", ["X"]),
        priority=1
    )

    # Penguins are birds
    penguins_birds = reasoner.add_default(
        name="Penguins are birds",
        prerequisite=reasoner.create_literal("penguin", ["X"]),
        justifications=[],
        consequent=reasoner.create_literal("bird", ["X"]),
        priority=2
    )

    # Penguins don't fly (more specific)
    penguins_no_fly = reasoner.add_default(
        name="Penguins don't fly",
        prerequisite=reasoner.create_literal("penguin", ["X"]),
        justifications=[reasoner.negate(reasoner.create_literal("flies", ["X"]))],
        consequent=reasoner.negate(reasoner.create_literal("flies", ["X"])),
        priority=3,
        specificity=2
    )

    print(f"   Rule 1: {birds_fly.name}")
    print(f"   Rule 2: {penguins_birds.name}")
    print(f"   Rule 3: {penguins_no_fly.name}")
    print()

    # 3. Add Facts
    print("3. ADD FACTS:")
    print("-" * 40)

    reasoner.add_fact(bird)
    reasoner.add_fact(penguin)

    print(f"   Added: {bird}")
    print(f"   Added: {penguin}")
    print(f"   All facts: {reasoner.all_facts()}")
    print()

    # 4. Add Exception
    print("4. ADD EXCEPTION:")
    print("-" * 40)

    # Penguins are an exception to "birds fly"
    exc = reasoner.add_exception(
        birds_fly.rule_id,
        penguin,
        "Penguins are flightless birds"
    )

    print(f"   Exception: {exc.exception} blocks '{birds_fly.name}'")
    print(f"   Reason: {exc.reason}")
    print()

    # 5. Compute Extensions
    print("5. COMPUTE EXTENSIONS:")
    print("-" * 40)

    extensions = reasoner.compute_extensions(ConflictResolution.SPECIFICITY)

    for i, ext in enumerate(extensions):
        print(f"   Extension {i + 1}:")
        print(f"      Facts: {ext.facts}")
        print(f"      Applied: {len(ext.applied_defaults)} defaults")
    print()

    # 6. Skeptical Inference
    print("6. SKEPTICAL INFERENCE:")
    print("-" * 40)

    result = reasoner.infer(flies, ReasoningMode.SKEPTICAL)
    print(f"   Query: Does Tweety fly?")
    print(f"   Result: {result.supported}")
    print(f"   Supporting extensions: {len(result.supporting_extensions)}")

    result2 = reasoner.infer(not_flies, ReasoningMode.SKEPTICAL)
    print(f"   Query: Does Tweety NOT fly?")
    print(f"   Result: {result2.supported}")
    print()

    # 7. Credulous Inference
    print("7. CREDULOUS INFERENCE:")
    print("-" * 40)

    result = reasoner.infer(flies, ReasoningMode.CREDULOUS)
    print(f"   Query: Does Tweety fly? (credulous)")
    print(f"   Result: {result.supported}")
    print()

    # 8. All Conclusions
    print("8. ALL CONCLUSIONS:")
    print("-" * 40)

    skeptical_conc = reasoner.all_conclusions(ReasoningMode.SKEPTICAL)
    credulous_conc = reasoner.all_conclusions(ReasoningMode.CREDULOUS)

    print(f"   Skeptical: {skeptical_conc}")
    print(f"   Credulous: {credulous_conc}")
    print()

    # 9. Non-Monotonicity Demo
    print("9. NON-MONOTONICITY DEMO:")
    print("-" * 40)

    # Create a new reasoner
    r2 = DefaultReasoner()

    robin = r2.create_literal("bird", ["robin"])
    robin_flies = r2.create_literal("flies", ["robin"])
    wounded = r2.create_literal("wounded", ["robin"])

    # Add rule: birds fly
    r2.add_default(
        "Birds fly",
        robin,
        [robin_flies],
        robin_flies,
        priority=1
    )

    r2.add_fact(robin)

    print(f"   Initial facts: {r2.all_facts()}")
    conc1 = r2.all_conclusions()
    print(f"   Conclusions: {conc1}")

    # Add new information: robin is wounded
    r2.add_fact(wounded)
    print(f"   After adding 'wounded': {r2.all_facts()}")

    # Add exception: wounded birds don't fly
    wounded_exception = r2.add_default(
        "Wounded birds don't fly",
        wounded,
        [r2.negate(robin_flies)],
        r2.negate(robin_flies),
        priority=2
    )

    conc2 = r2.all_conclusions()
    print(f"   New conclusions: {conc2}")
    print(f"   (Conclusions changed non-monotonically)")
    print()

    # 10. Priority Ordering
    print("10. PRIORITY-BASED CONFLICT RESOLUTION:")
    print("-" * 40)

    r3 = DefaultReasoner()

    legal_age = r3.create_literal("legal_age", ["john"])
    adult = r3.create_literal("adult", ["john"])
    minor = r3.create_literal("minor", ["john"])

    # Low priority: assume minor
    r3.add_default(
        "Assume minor",
        None,
        [minor],
        minor,
        priority=1
    )

    # High priority: legal age means adult
    r3.add_default(
        "Legal age means adult",
        legal_age,
        [adult],
        adult,
        priority=5
    )

    r3.add_fact(legal_age)

    ext = r3.compute_extensions(ConflictResolution.PRIORITY)
    print(f"   With priority-based resolution:")
    for e in ext:
        print(f"      Extension facts: {e.facts}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Default Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
