#!/usr/bin/env python3
"""
BAEL - Modal Reasoner
Advanced modal logic reasoning beyond epistemic and deontic.

Features:
- Alethic modality (necessity/possibility)
- Temporal modality
- Kripke semantics
- Multiple modal systems (K, T, S4, S5)
- Frame conditions
- Modal proof theory
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

class ModalOperator(Enum):
    """Modal operators."""
    NECESSARY = "necessary"  # □ (box)
    POSSIBLE = "possible"  # ◇ (diamond)
    ALWAYS = "always"  # G (globally)
    EVENTUALLY = "eventually"  # F (future)
    NEXT = "next"  # X (next state)
    UNTIL = "until"  # U (until)


class ModalSystem(Enum):
    """Modal logic systems."""
    K = "K"  # Basic modal logic
    T = "T"  # K + reflexivity
    S4 = "S4"  # T + transitivity
    S5 = "S5"  # S4 + symmetry
    KD = "KD"  # K + seriality


class FrameProperty(Enum):
    """Properties of accessibility relations."""
    REFLEXIVE = "reflexive"  # Every world accesses itself
    SYMMETRIC = "symmetric"  # If w accesses v, then v accesses w
    TRANSITIVE = "transitive"  # If w->v and v->u, then w->u
    SERIAL = "serial"  # Every world accesses at least one world
    EUCLIDEAN = "euclidean"  # If w->v and w->u, then v->u


class FormulaType(Enum):
    """Types of modal formulas."""
    ATOMIC = "atomic"
    NEGATION = "negation"
    CONJUNCTION = "conjunction"
    DISJUNCTION = "disjunction"
    IMPLICATION = "implication"
    MODAL = "modal"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class World:
    """A possible world."""
    world_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    valuations: Dict[str, bool] = field(default_factory=dict)  # atom -> truth
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessibilityRelation:
    """Accessibility relation between worlds."""
    rel_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_world: str = ""
    to_world: str = ""
    label: str = ""  # Optional label for multi-modal logic


@dataclass
class Formula:
    """A modal formula."""
    formula_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    formula_type: FormulaType = FormulaType.ATOMIC
    atom: Optional[str] = None  # For atomic formulas
    operator: Optional[ModalOperator] = None  # For modal formulas
    subformulas: List['Formula'] = field(default_factory=list)

    def __str__(self) -> str:
        if self.formula_type == FormulaType.ATOMIC:
            return self.atom or "?"
        elif self.formula_type == FormulaType.NEGATION:
            return f"¬{self.subformulas[0]}"
        elif self.formula_type == FormulaType.CONJUNCTION:
            return f"({self.subformulas[0]} ∧ {self.subformulas[1]})"
        elif self.formula_type == FormulaType.DISJUNCTION:
            return f"({self.subformulas[0]} ∨ {self.subformulas[1]})"
        elif self.formula_type == FormulaType.IMPLICATION:
            return f"({self.subformulas[0]} → {self.subformulas[1]})"
        elif self.formula_type == FormulaType.MODAL:
            op_sym = "□" if self.operator == ModalOperator.NECESSARY else "◇"
            return f"{op_sym}{self.subformulas[0]}"
        return "?"


@dataclass
class KripkeModel:
    """A Kripke model."""
    model_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    worlds: Dict[str, World] = field(default_factory=dict)
    relations: List[AccessibilityRelation] = field(default_factory=list)
    designated_world: Optional[str] = None


@dataclass
class EvaluationResult:
    """Result of evaluating a formula."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    formula: str = ""
    world_id: str = ""
    value: bool = False
    explanation: str = ""
    subresults: List['EvaluationResult'] = field(default_factory=list)


@dataclass
class ModalProof:
    """A proof in modal logic."""
    proof_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conclusion: str = ""
    steps: List[str] = field(default_factory=list)
    valid: bool = False


# =============================================================================
# FORMULA BUILDER
# =============================================================================

class FormulaBuilder:
    """Build modal formulas."""

    def __init__(self):
        self._formulas: Dict[str, Formula] = {}

    def atom(self, name: str) -> Formula:
        """Create an atomic formula."""
        formula = Formula(
            formula_type=FormulaType.ATOMIC,
            atom=name
        )
        self._formulas[formula.formula_id] = formula
        return formula

    def negation(self, sub: Formula) -> Formula:
        """Create a negation."""
        formula = Formula(
            formula_type=FormulaType.NEGATION,
            subformulas=[sub]
        )
        self._formulas[formula.formula_id] = formula
        return formula

    def conjunction(self, left: Formula, right: Formula) -> Formula:
        """Create a conjunction."""
        formula = Formula(
            formula_type=FormulaType.CONJUNCTION,
            subformulas=[left, right]
        )
        self._formulas[formula.formula_id] = formula
        return formula

    def disjunction(self, left: Formula, right: Formula) -> Formula:
        """Create a disjunction."""
        formula = Formula(
            formula_type=FormulaType.DISJUNCTION,
            subformulas=[left, right]
        )
        self._formulas[formula.formula_id] = formula
        return formula

    def implication(self, antecedent: Formula, consequent: Formula) -> Formula:
        """Create an implication."""
        formula = Formula(
            formula_type=FormulaType.IMPLICATION,
            subformulas=[antecedent, consequent]
        )
        self._formulas[formula.formula_id] = formula
        return formula

    def necessary(self, sub: Formula) -> Formula:
        """Create □φ (necessarily φ)."""
        formula = Formula(
            formula_type=FormulaType.MODAL,
            operator=ModalOperator.NECESSARY,
            subformulas=[sub]
        )
        self._formulas[formula.formula_id] = formula
        return formula

    def possible(self, sub: Formula) -> Formula:
        """Create ◇φ (possibly φ)."""
        formula = Formula(
            formula_type=FormulaType.MODAL,
            operator=ModalOperator.POSSIBLE,
            subformulas=[sub]
        )
        self._formulas[formula.formula_id] = formula
        return formula

    def get_formula(self, formula_id: str) -> Optional[Formula]:
        """Get a formula by ID."""
        return self._formulas.get(formula_id)


# =============================================================================
# KRIPKE MODEL BUILDER
# =============================================================================

class KripkeModelBuilder:
    """Build Kripke models."""

    def __init__(self):
        self._models: Dict[str, KripkeModel] = {}

    def create_model(self, name: str = "") -> KripkeModel:
        """Create a new Kripke model."""
        model = KripkeModel(name=name)
        self._models[model.model_id] = model
        return model

    def add_world(
        self,
        model: KripkeModel,
        name: str,
        valuations: Optional[Dict[str, bool]] = None
    ) -> World:
        """Add a world to a model."""
        world = World(
            name=name,
            valuations=valuations or {}
        )
        model.worlds[world.world_id] = world
        return world

    def add_relation(
        self,
        model: KripkeModel,
        from_world: str,
        to_world: str,
        label: str = ""
    ) -> AccessibilityRelation:
        """Add an accessibility relation."""
        rel = AccessibilityRelation(
            from_world=from_world,
            to_world=to_world,
            label=label
        )
        model.relations.append(rel)
        return rel

    def set_designated(
        self,
        model: KripkeModel,
        world_id: str
    ) -> None:
        """Set the designated (actual) world."""
        model.designated_world = world_id

    def get_accessible(
        self,
        model: KripkeModel,
        from_world: str
    ) -> List[str]:
        """Get worlds accessible from a given world."""
        return [r.to_world for r in model.relations
                if r.from_world == from_world]

    def get_model(self, model_id: str) -> Optional[KripkeModel]:
        """Get a model by ID."""
        return self._models.get(model_id)

    def close_under(
        self,
        model: KripkeModel,
        properties: List[FrameProperty]
    ) -> None:
        """Close the accessibility relation under given properties."""
        changed = True

        while changed:
            changed = False

            for prop in properties:
                if prop == FrameProperty.REFLEXIVE:
                    for w_id in model.worlds:
                        if not self._has_relation(model, w_id, w_id):
                            self.add_relation(model, w_id, w_id)
                            changed = True

                elif prop == FrameProperty.SYMMETRIC:
                    for rel in list(model.relations):
                        if not self._has_relation(model, rel.to_world, rel.from_world):
                            self.add_relation(model, rel.to_world, rel.from_world)
                            changed = True

                elif prop == FrameProperty.TRANSITIVE:
                    for r1 in list(model.relations):
                        for r2 in list(model.relations):
                            if r1.to_world == r2.from_world:
                                if not self._has_relation(model, r1.from_world, r2.to_world):
                                    self.add_relation(model, r1.from_world, r2.to_world)
                                    changed = True

    def _has_relation(
        self,
        model: KripkeModel,
        from_w: str,
        to_w: str
    ) -> bool:
        """Check if relation exists."""
        return any(r.from_world == from_w and r.to_world == to_w
                   for r in model.relations)


# =============================================================================
# MODAL SEMANTICS
# =============================================================================

class ModalSemantics:
    """Evaluate modal formulas using Kripke semantics."""

    def __init__(self, model_builder: KripkeModelBuilder):
        self._builder = model_builder

    def evaluate(
        self,
        model: KripkeModel,
        formula: Formula,
        world_id: str
    ) -> EvaluationResult:
        """Evaluate a formula at a world."""
        world = model.worlds.get(world_id)
        if not world:
            return EvaluationResult(
                formula=str(formula),
                world_id=world_id,
                value=False,
                explanation="World not found"
            )

        result = self._eval(model, formula, world_id)
        return result

    def _eval(
        self,
        model: KripkeModel,
        formula: Formula,
        world_id: str
    ) -> EvaluationResult:
        """Internal evaluation."""
        world = model.worlds[world_id]

        if formula.formula_type == FormulaType.ATOMIC:
            val = world.valuations.get(formula.atom, False)
            return EvaluationResult(
                formula=str(formula),
                world_id=world_id,
                value=val,
                explanation=f"V({formula.atom}) = {val} at {world.name}"
            )

        elif formula.formula_type == FormulaType.NEGATION:
            sub = self._eval(model, formula.subformulas[0], world_id)
            return EvaluationResult(
                formula=str(formula),
                world_id=world_id,
                value=not sub.value,
                explanation=f"¬({sub.value}) = {not sub.value}",
                subresults=[sub]
            )

        elif formula.formula_type == FormulaType.CONJUNCTION:
            left = self._eval(model, formula.subformulas[0], world_id)
            right = self._eval(model, formula.subformulas[1], world_id)
            val = left.value and right.value
            return EvaluationResult(
                formula=str(formula),
                world_id=world_id,
                value=val,
                explanation=f"({left.value} ∧ {right.value}) = {val}",
                subresults=[left, right]
            )

        elif formula.formula_type == FormulaType.DISJUNCTION:
            left = self._eval(model, formula.subformulas[0], world_id)
            right = self._eval(model, formula.subformulas[1], world_id)
            val = left.value or right.value
            return EvaluationResult(
                formula=str(formula),
                world_id=world_id,
                value=val,
                explanation=f"({left.value} ∨ {right.value}) = {val}",
                subresults=[left, right]
            )

        elif formula.formula_type == FormulaType.IMPLICATION:
            left = self._eval(model, formula.subformulas[0], world_id)
            right = self._eval(model, formula.subformulas[1], world_id)
            val = (not left.value) or right.value
            return EvaluationResult(
                formula=str(formula),
                world_id=world_id,
                value=val,
                explanation=f"({left.value} → {right.value}) = {val}",
                subresults=[left, right]
            )

        elif formula.formula_type == FormulaType.MODAL:
            accessible = self._builder.get_accessible(model, world_id)

            if formula.operator == ModalOperator.NECESSARY:
                # □φ is true iff φ is true at all accessible worlds
                if not accessible:
                    # Vacuously true if no accessible worlds
                    return EvaluationResult(
                        formula=str(formula),
                        world_id=world_id,
                        value=True,
                        explanation="□φ vacuously true (no accessible worlds)"
                    )

                subresults = []
                all_true = True

                for acc_world in accessible:
                    sub = self._eval(model, formula.subformulas[0], acc_world)
                    subresults.append(sub)
                    if not sub.value:
                        all_true = False

                return EvaluationResult(
                    formula=str(formula),
                    world_id=world_id,
                    value=all_true,
                    explanation=f"□φ: checked {len(accessible)} accessible worlds",
                    subresults=subresults
                )

            elif formula.operator == ModalOperator.POSSIBLE:
                # ◇φ is true iff φ is true at some accessible world
                if not accessible:
                    return EvaluationResult(
                        formula=str(formula),
                        world_id=world_id,
                        value=False,
                        explanation="◇φ false (no accessible worlds)"
                    )

                subresults = []
                some_true = False

                for acc_world in accessible:
                    sub = self._eval(model, formula.subformulas[0], acc_world)
                    subresults.append(sub)
                    if sub.value:
                        some_true = True

                return EvaluationResult(
                    formula=str(formula),
                    world_id=world_id,
                    value=some_true,
                    explanation=f"◇φ: found witness in {len([s for s in subresults if s.value])} worlds",
                    subresults=subresults
                )

        return EvaluationResult(
            formula=str(formula),
            world_id=world_id,
            value=False,
            explanation="Unknown formula type"
        )

    def is_valid(
        self,
        model: KripkeModel,
        formula: Formula
    ) -> bool:
        """Check if formula is valid in model (true at all worlds)."""
        for world_id in model.worlds:
            result = self.evaluate(model, formula, world_id)
            if not result.value:
                return False
        return True


# =============================================================================
# MODAL SYSTEM MANAGER
# =============================================================================

class ModalSystemManager:
    """Manage modal logic systems."""

    def __init__(self, model_builder: KripkeModelBuilder):
        self._builder = model_builder

    def get_frame_properties(
        self,
        system: ModalSystem
    ) -> List[FrameProperty]:
        """Get frame properties for a modal system."""
        if system == ModalSystem.K:
            return []
        elif system == ModalSystem.T:
            return [FrameProperty.REFLEXIVE]
        elif system == ModalSystem.S4:
            return [FrameProperty.REFLEXIVE, FrameProperty.TRANSITIVE]
        elif system == ModalSystem.S5:
            return [FrameProperty.REFLEXIVE, FrameProperty.SYMMETRIC,
                    FrameProperty.TRANSITIVE]
        elif system == ModalSystem.KD:
            return [FrameProperty.SERIAL]
        return []

    def create_model_for_system(
        self,
        system: ModalSystem,
        name: str = ""
    ) -> KripkeModel:
        """Create a model for a specific modal system."""
        model = self._builder.create_model(name or f"{system.value} Model")
        return model

    def enforce_system(
        self,
        model: KripkeModel,
        system: ModalSystem
    ) -> None:
        """Enforce a modal system's frame conditions."""
        props = self.get_frame_properties(system)
        self._builder.close_under(model, props)

    def check_axiom(
        self,
        system: ModalSystem,
        axiom: str
    ) -> bool:
        """Check if an axiom is valid in a system."""
        # Axiom schemas for different systems
        valid_axioms = {
            ModalSystem.K: ["K"],  # □(p→q) → (□p→□q)
            ModalSystem.T: ["K", "T"],  # + □p → p
            ModalSystem.S4: ["K", "T", "4"],  # + □p → □□p
            ModalSystem.S5: ["K", "T", "4", "5", "B"],  # + ◇p → □◇p, p → □◇p
            ModalSystem.KD: ["K", "D"]  # + □p → ◇p
        }

        system_axioms = valid_axioms.get(system, [])
        return axiom in system_axioms


# =============================================================================
# MODAL REASONER
# =============================================================================

class ModalReasoner:
    """
    Modal Reasoner for BAEL.

    Advanced modal logic reasoning.
    """

    def __init__(self):
        self._formula_builder = FormulaBuilder()
        self._model_builder = KripkeModelBuilder()
        self._semantics = ModalSemantics(self._model_builder)
        self._systems = ModalSystemManager(self._model_builder)
        self._current_model: Optional[KripkeModel] = None

    # -------------------------------------------------------------------------
    # FORMULA BUILDING
    # -------------------------------------------------------------------------

    def atom(self, name: str) -> Formula:
        """Create an atomic formula."""
        return self._formula_builder.atom(name)

    def not_(self, sub: Formula) -> Formula:
        """Create ¬φ."""
        return self._formula_builder.negation(sub)

    def and_(self, left: Formula, right: Formula) -> Formula:
        """Create φ ∧ ψ."""
        return self._formula_builder.conjunction(left, right)

    def or_(self, left: Formula, right: Formula) -> Formula:
        """Create φ ∨ ψ."""
        return self._formula_builder.disjunction(left, right)

    def implies(self, antecedent: Formula, consequent: Formula) -> Formula:
        """Create φ → ψ."""
        return self._formula_builder.implication(antecedent, consequent)

    def necessary(self, sub: Formula) -> Formula:
        """Create □φ."""
        return self._formula_builder.necessary(sub)

    def possible(self, sub: Formula) -> Formula:
        """Create ◇φ."""
        return self._formula_builder.possible(sub)

    # -------------------------------------------------------------------------
    # MODEL BUILDING
    # -------------------------------------------------------------------------

    def create_model(
        self,
        name: str = "",
        system: Optional[ModalSystem] = None
    ) -> KripkeModel:
        """Create a Kripke model."""
        if system:
            model = self._systems.create_model_for_system(system, name)
        else:
            model = self._model_builder.create_model(name)
        self._current_model = model
        return model

    def add_world(
        self,
        name: str,
        valuations: Optional[Dict[str, bool]] = None,
        model: Optional[KripkeModel] = None
    ) -> World:
        """Add a world to a model."""
        m = model or self._current_model
        if not m:
            raise ValueError("No model available")
        return self._model_builder.add_world(m, name, valuations)

    def add_accessibility(
        self,
        from_world: str,
        to_world: str,
        model: Optional[KripkeModel] = None
    ) -> AccessibilityRelation:
        """Add an accessibility relation."""
        m = model or self._current_model
        if not m:
            raise ValueError("No model available")
        return self._model_builder.add_relation(m, from_world, to_world)

    def set_actual_world(
        self,
        world_id: str,
        model: Optional[KripkeModel] = None
    ) -> None:
        """Set the actual (designated) world."""
        m = model or self._current_model
        if not m:
            raise ValueError("No model available")
        self._model_builder.set_designated(m, world_id)

    def enforce_system(
        self,
        system: ModalSystem,
        model: Optional[KripkeModel] = None
    ) -> None:
        """Enforce modal system frame conditions."""
        m = model or self._current_model
        if not m:
            raise ValueError("No model available")
        self._systems.enforce_system(m, system)

    # -------------------------------------------------------------------------
    # EVALUATION
    # -------------------------------------------------------------------------

    def evaluate(
        self,
        formula: Formula,
        world_id: Optional[str] = None,
        model: Optional[KripkeModel] = None
    ) -> EvaluationResult:
        """Evaluate a formula at a world."""
        m = model or self._current_model
        if not m:
            raise ValueError("No model available")

        w_id = world_id or m.designated_world
        if not w_id:
            raise ValueError("No world specified")

        return self._semantics.evaluate(m, formula, w_id)

    def is_valid(
        self,
        formula: Formula,
        model: Optional[KripkeModel] = None
    ) -> bool:
        """Check if formula is valid (true at all worlds)."""
        m = model or self._current_model
        if not m:
            raise ValueError("No model available")
        return self._semantics.is_valid(m, formula)

    def is_satisfiable(
        self,
        formula: Formula,
        model: Optional[KripkeModel] = None
    ) -> bool:
        """Check if formula is satisfiable (true at some world)."""
        m = model or self._current_model
        if not m:
            raise ValueError("No model available")

        for world_id in m.worlds:
            result = self._semantics.evaluate(m, formula, world_id)
            if result.value:
                return True
        return False

    # -------------------------------------------------------------------------
    # MODAL SYSTEM INFO
    # -------------------------------------------------------------------------

    def get_frame_properties(
        self,
        system: ModalSystem
    ) -> List[FrameProperty]:
        """Get frame properties for a modal system."""
        return self._systems.get_frame_properties(system)

    def check_axiom(
        self,
        system: ModalSystem,
        axiom: str
    ) -> bool:
        """Check if axiom is valid in system."""
        return self._systems.check_axiom(system, axiom)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Modal Reasoner."""
    print("=" * 70)
    print("BAEL - MODAL REASONER DEMO")
    print("Advanced Modal Logic Reasoning")
    print("=" * 70)
    print()

    reasoner = ModalReasoner()

    # 1. Create Formulas
    print("1. CREATE MODAL FORMULAS:")
    print("-" * 40)

    p = reasoner.atom("p")
    q = reasoner.atom("q")

    necessary_p = reasoner.necessary(p)
    possible_q = reasoner.possible(q)

    p_implies_q = reasoner.implies(p, q)
    box_implies = reasoner.necessary(p_implies_q)

    print(f"   p: {p}")
    print(f"   □p: {necessary_p}")
    print(f"   ◇q: {possible_q}")
    print(f"   □(p → q): {box_implies}")
    print()

    # 2. Create Kripke Model
    print("2. CREATE KRIPKE MODEL:")
    print("-" * 40)

    model = reasoner.create_model("Example Model")

    w1 = reasoner.add_world("w1", {"p": True, "q": True})
    w2 = reasoner.add_world("w2", {"p": True, "q": False})
    w3 = reasoner.add_world("w3", {"p": False, "q": True})

    print(f"   World {w1.name}: p=True, q=True")
    print(f"   World {w2.name}: p=True, q=False")
    print(f"   World {w3.name}: p=False, q=True")
    print()

    # 3. Add Accessibility Relations
    print("3. ACCESSIBILITY RELATIONS:")
    print("-" * 40)

    reasoner.add_accessibility(w1.world_id, w2.world_id)
    reasoner.add_accessibility(w1.world_id, w3.world_id)
    reasoner.add_accessibility(w2.world_id, w3.world_id)
    reasoner.add_accessibility(w3.world_id, w1.world_id)

    print(f"   {w1.name} → {w2.name}")
    print(f"   {w1.name} → {w3.name}")
    print(f"   {w2.name} → {w3.name}")
    print(f"   {w3.name} → {w1.name}")
    print()

    # 4. Set Actual World
    print("4. SET ACTUAL WORLD:")
    print("-" * 40)

    reasoner.set_actual_world(w1.world_id)
    print(f"   Actual world: {w1.name}")
    print()

    # 5. Evaluate Formulas
    print("5. EVALUATE FORMULAS:")
    print("-" * 40)

    result_p = reasoner.evaluate(p)
    result_box_p = reasoner.evaluate(necessary_p)
    result_dia_q = reasoner.evaluate(possible_q)

    print(f"   p at {w1.name}: {result_p.value}")
    print(f"   □p at {w1.name}: {result_box_p.value}")
    print(f"   ◇q at {w1.name}: {result_dia_q.value}")
    print()

    # 6. Check Validity
    print("6. CHECK VALIDITY:")
    print("-" * 40)

    # ◇p: is p possible at all worlds?
    possible_p = reasoner.possible(p)
    is_valid = reasoner.is_valid(possible_p)
    print(f"   ◇p valid in model: {is_valid}")

    # □p: is p necessary at all worlds?
    necessary_p = reasoner.necessary(p)
    is_valid = reasoner.is_valid(necessary_p)
    print(f"   □p valid in model: {is_valid}")
    print()

    # 7. Check Satisfiability
    print("7. CHECK SATISFIABILITY:")
    print("-" * 40)

    is_sat = reasoner.is_satisfiable(necessary_p)
    print(f"   □p satisfiable: {is_sat}")

    # ¬p ∧ ¬q
    not_p_and_not_q = reasoner.and_(reasoner.not_(p), reasoner.not_(q))
    is_sat = reasoner.is_satisfiable(not_p_and_not_q)
    print(f"   (¬p ∧ ¬q) satisfiable: {is_sat}")
    print()

    # 8. Modal Systems
    print("8. MODAL SYSTEMS:")
    print("-" * 40)

    for sys in [ModalSystem.K, ModalSystem.T, ModalSystem.S4, ModalSystem.S5]:
        props = reasoner.get_frame_properties(sys)
        prop_names = [p.value for p in props]
        print(f"   {sys.value}: {', '.join(prop_names) if prop_names else 'no constraints'}")
    print()

    # 9. Enforce S4 System
    print("9. ENFORCE S4 SYSTEM:")
    print("-" * 40)

    s4_model = reasoner.create_model("S4 Model", ModalSystem.S4)

    w_a = reasoner.add_world("a", {"p": True})
    w_b = reasoner.add_world("b", {"p": True})

    reasoner.add_accessibility(w_a.world_id, w_b.world_id)

    print(f"   Before closing: 1 relation")

    # Enforce S4 (reflexive + transitive)
    reasoner.enforce_system(ModalSystem.S4, s4_model)

    print(f"   After S4 closure: {len(s4_model.relations)} relations")
    print(f"   (Added reflexive relations)")
    print()

    # 10. Check Axioms
    print("10. CHECK AXIOMS BY SYSTEM:")
    print("-" * 40)

    axioms = ["K", "T", "4", "5", "B", "D"]
    systems = [ModalSystem.K, ModalSystem.T, ModalSystem.S4, ModalSystem.S5]

    for sys in systems:
        valid = [a for a in axioms if reasoner.check_axiom(sys, a)]
        print(f"   {sys.value}: {', '.join(valid)}")
    print()

    # 11. Complex Formula
    print("11. COMPLEX FORMULA:")
    print("-" * 40)

    # □(p → q) → (□p → □q)  (Axiom K)
    p = reasoner.atom("p")
    q = reasoner.atom("q")

    p_implies_q = reasoner.implies(p, q)
    box_p_implies_q = reasoner.necessary(p_implies_q)

    box_p = reasoner.necessary(p)
    box_q = reasoner.necessary(q)
    box_p_implies_box_q = reasoner.implies(box_p, box_q)

    axiom_k = reasoner.implies(box_p_implies_q, box_p_implies_box_q)

    print(f"   Axiom K: {axiom_k}")

    result = reasoner.evaluate(axiom_k, w1.world_id, model)
    print(f"   Value at {w1.name}: {result.value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Modal Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
