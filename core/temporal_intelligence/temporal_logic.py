"""
⚡ TEMPORAL LOGIC ⚡
===================
Temporal logic reasoning.

Features:
- Linear Temporal Logic (LTL)
- Computation Tree Logic (CTL)
- Model checking
- Temporal verification
"""

import math
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid


class TemporalOperator(Enum):
    """Temporal logic operators"""
    # LTL operators
    NEXT = auto()       # X (next state)
    EVENTUALLY = auto() # F (finally/future)
    ALWAYS = auto()     # G (globally)
    UNTIL = auto()      # U (until)
    RELEASE = auto()    # R (release)

    # CTL path quantifiers
    ALL_PATHS = auto()  # A (all paths)
    EXISTS_PATH = auto() # E (exists path)

    # Propositional
    AND = auto()
    OR = auto()
    NOT = auto()
    IMPLIES = auto()


@dataclass
class TemporalFormula:
    """A temporal logic formula"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Atomic proposition or operator
    is_atomic: bool = True
    proposition: str = ""  # If atomic

    # If not atomic
    operator: Optional[TemporalOperator] = None
    operands: List['TemporalFormula'] = field(default_factory=list)

    def __repr__(self):
        if self.is_atomic:
            return self.proposition

        op_symbols = {
            TemporalOperator.NEXT: 'X',
            TemporalOperator.EVENTUALLY: 'F',
            TemporalOperator.ALWAYS: 'G',
            TemporalOperator.UNTIL: 'U',
            TemporalOperator.RELEASE: 'R',
            TemporalOperator.ALL_PATHS: 'A',
            TemporalOperator.EXISTS_PATH: 'E',
            TemporalOperator.AND: '∧',
            TemporalOperator.OR: '∨',
            TemporalOperator.NOT: '¬',
            TemporalOperator.IMPLIES: '→',
        }

        symbol = op_symbols.get(self.operator, '?')

        if self.operator == TemporalOperator.NOT:
            return f"¬{self.operands[0]}"
        elif self.operator in [TemporalOperator.NEXT, TemporalOperator.EVENTUALLY,
                               TemporalOperator.ALWAYS]:
            return f"{symbol}({self.operands[0]})"
        elif len(self.operands) == 2:
            return f"({self.operands[0]} {symbol} {self.operands[1]})"

        return f"{symbol}[{', '.join(str(o) for o in self.operands)}]"

    @staticmethod
    def atomic(prop: str) -> 'TemporalFormula':
        """Create atomic proposition"""
        return TemporalFormula(is_atomic=True, proposition=prop)

    @staticmethod
    def next(formula: 'TemporalFormula') -> 'TemporalFormula':
        """Create NEXT formula"""
        return TemporalFormula(
            is_atomic=False,
            operator=TemporalOperator.NEXT,
            operands=[formula]
        )

    @staticmethod
    def eventually(formula: 'TemporalFormula') -> 'TemporalFormula':
        """Create EVENTUALLY formula"""
        return TemporalFormula(
            is_atomic=False,
            operator=TemporalOperator.EVENTUALLY,
            operands=[formula]
        )

    @staticmethod
    def always(formula: 'TemporalFormula') -> 'TemporalFormula':
        """Create ALWAYS formula"""
        return TemporalFormula(
            is_atomic=False,
            operator=TemporalOperator.ALWAYS,
            operands=[formula]
        )

    @staticmethod
    def until(left: 'TemporalFormula', right: 'TemporalFormula') -> 'TemporalFormula':
        """Create UNTIL formula"""
        return TemporalFormula(
            is_atomic=False,
            operator=TemporalOperator.UNTIL,
            operands=[left, right]
        )

    def negate(self) -> 'TemporalFormula':
        """Negate formula"""
        return TemporalFormula(
            is_atomic=False,
            operator=TemporalOperator.NOT,
            operands=[self]
        )

    def and_with(self, other: 'TemporalFormula') -> 'TemporalFormula':
        """AND with another formula"""
        return TemporalFormula(
            is_atomic=False,
            operator=TemporalOperator.AND,
            operands=[self, other]
        )

    def or_with(self, other: 'TemporalFormula') -> 'TemporalFormula':
        """OR with another formula"""
        return TemporalFormula(
            is_atomic=False,
            operator=TemporalOperator.OR,
            operands=[self, other]
        )


class LTLFormula(TemporalFormula):
    """Linear Temporal Logic formula"""
    pass


class CTLFormula(TemporalFormula):
    """Computation Tree Logic formula"""

    @staticmethod
    def all_next(formula: 'CTLFormula') -> 'CTLFormula':
        """AX - in all paths, next state satisfies"""
        ax = CTLFormula(
            is_atomic=False,
            operator=TemporalOperator.ALL_PATHS,
            operands=[TemporalFormula.next(formula)]
        )
        return ax

    @staticmethod
    def exists_eventually(formula: 'CTLFormula') -> 'CTLFormula':
        """EF - exists a path where eventually"""
        ef = CTLFormula(
            is_atomic=False,
            operator=TemporalOperator.EXISTS_PATH,
            operands=[TemporalFormula.eventually(formula)]
        )
        return ef

    @staticmethod
    def all_always(formula: 'CTLFormula') -> 'CTLFormula':
        """AG - in all paths, always"""
        ag = CTLFormula(
            is_atomic=False,
            operator=TemporalOperator.ALL_PATHS,
            operands=[TemporalFormula.always(formula)]
        )
        return ag


@dataclass
class KripkeState:
    """State in a Kripke structure"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""

    # Atomic propositions true in this state
    labels: Set[str] = field(default_factory=set)

    # Successors
    successors: Set[str] = field(default_factory=set)


class KripkeStructure:
    """
    Kripke structure for model checking.
    """

    def __init__(self):
        self.states: Dict[str, KripkeState] = {}
        self.initial_states: Set[str] = set()
        self.atomic_props: Set[str] = set()

    def add_state(self, state: KripkeState, is_initial: bool = False):
        """Add state to structure"""
        self.states[state.id] = state
        self.atomic_props.update(state.labels)

        if is_initial:
            self.initial_states.add(state.id)

    def add_transition(self, from_id: str, to_id: str):
        """Add transition between states"""
        if from_id in self.states:
            self.states[from_id].successors.add(to_id)

    def get_successors(self, state_id: str) -> Set[str]:
        """Get successor states"""
        if state_id in self.states:
            return self.states[state_id].successors
        return set()

    def get_predecessors(self, state_id: str) -> Set[str]:
        """Get predecessor states"""
        preds = set()
        for sid, state in self.states.items():
            if state_id in state.successors:
                preds.add(sid)
        return preds


class TemporalReasoner:
    """
    Temporal logic reasoning engine.
    """

    def __init__(self):
        self.formulas: Dict[str, TemporalFormula] = {}
        self.traces: List[List[Set[str]]] = []  # Execution traces

    def add_formula(self, formula: TemporalFormula):
        """Add formula to reasoner"""
        self.formulas[formula.id] = formula

    def add_trace(self, trace: List[Set[str]]):
        """Add execution trace"""
        self.traces.append(trace)

    def evaluate_ltl(
        self,
        formula: TemporalFormula,
        trace: List[Set[str]],
        position: int = 0
    ) -> bool:
        """Evaluate LTL formula on trace"""
        if position >= len(trace):
            return False

        if formula.is_atomic:
            return formula.proposition in trace[position]

        op = formula.operator

        if op == TemporalOperator.NOT:
            return not self.evaluate_ltl(formula.operands[0], trace, position)

        elif op == TemporalOperator.AND:
            return (self.evaluate_ltl(formula.operands[0], trace, position) and
                    self.evaluate_ltl(formula.operands[1], trace, position))

        elif op == TemporalOperator.OR:
            return (self.evaluate_ltl(formula.operands[0], trace, position) or
                    self.evaluate_ltl(formula.operands[1], trace, position))

        elif op == TemporalOperator.NEXT:
            if position + 1 >= len(trace):
                return False
            return self.evaluate_ltl(formula.operands[0], trace, position + 1)

        elif op == TemporalOperator.EVENTUALLY:
            # F φ = true U φ
            for i in range(position, len(trace)):
                if self.evaluate_ltl(formula.operands[0], trace, i):
                    return True
            return False

        elif op == TemporalOperator.ALWAYS:
            # G φ = ¬F¬φ
            for i in range(position, len(trace)):
                if not self.evaluate_ltl(formula.operands[0], trace, i):
                    return False
            return True

        elif op == TemporalOperator.UNTIL:
            # φ U ψ: ψ eventually holds, and φ holds until then
            for i in range(position, len(trace)):
                if self.evaluate_ltl(formula.operands[1], trace, i):
                    return True
                if not self.evaluate_ltl(formula.operands[0], trace, i):
                    return False
            return False

        return False

    def find_counterexample(
        self,
        formula: TemporalFormula
    ) -> Optional[List[Set[str]]]:
        """Find trace that violates formula"""
        for trace in self.traces:
            if not self.evaluate_ltl(formula, trace):
                return trace
        return None


class ModelChecker:
    """
    CTL model checking on Kripke structures.
    """

    def __init__(self, structure: KripkeStructure = None):
        self.structure = structure or KripkeStructure()

    def check(
        self,
        formula: CTLFormula
    ) -> Set[str]:
        """
        Check CTL formula, return states where it holds.
        """
        return self._sat(formula)

    def _sat(self, formula: CTLFormula) -> Set[str]:
        """Compute satisfaction set"""
        if formula.is_atomic:
            # Return states where proposition holds
            return {
                sid for sid, state in self.structure.states.items()
                if formula.proposition in state.labels
            }

        op = formula.operator

        if op == TemporalOperator.NOT:
            all_states = set(self.structure.states.keys())
            return all_states - self._sat(formula.operands[0])

        elif op == TemporalOperator.AND:
            return self._sat(formula.operands[0]) & self._sat(formula.operands[1])

        elif op == TemporalOperator.OR:
            return self._sat(formula.operands[0]) | self._sat(formula.operands[1])

        elif op == TemporalOperator.EXISTS_PATH:
            inner = formula.operands[0]
            if inner.operator == TemporalOperator.NEXT:
                return self._sat_ex(inner.operands[0])
            elif inner.operator == TemporalOperator.EVENTUALLY:
                return self._sat_ef(inner.operands[0])
            elif inner.operator == TemporalOperator.ALWAYS:
                return self._sat_eg(inner.operands[0])

        elif op == TemporalOperator.ALL_PATHS:
            inner = formula.operands[0]
            if inner.operator == TemporalOperator.NEXT:
                return self._sat_ax(inner.operands[0])
            elif inner.operator == TemporalOperator.EVENTUALLY:
                return self._sat_af(inner.operands[0])
            elif inner.operator == TemporalOperator.ALWAYS:
                return self._sat_ag(inner.operands[0])

        return set()

    def _sat_ex(self, formula: CTLFormula) -> Set[str]:
        """EX φ - exists successor where φ holds"""
        phi_sat = self._sat(formula)
        result = set()

        for sid in self.structure.states:
            succs = self.structure.get_successors(sid)
            if succs & phi_sat:
                result.add(sid)

        return result

    def _sat_ax(self, formula: CTLFormula) -> Set[str]:
        """AX φ - all successors satisfy φ"""
        phi_sat = self._sat(formula)
        result = set()

        for sid in self.structure.states:
            succs = self.structure.get_successors(sid)
            if succs and succs <= phi_sat:
                result.add(sid)

        return result

    def _sat_ef(self, formula: CTLFormula) -> Set[str]:
        """EF φ - exists path to φ (reachability)"""
        phi_sat = self._sat(formula)

        # Fixed point: EF φ = φ ∨ EX EF φ
        result = phi_sat.copy()
        changed = True

        while changed:
            changed = False
            for sid in self.structure.states:
                if sid in result:
                    continue
                succs = self.structure.get_successors(sid)
                if succs & result:
                    result.add(sid)
                    changed = True

        return result

    def _sat_eg(self, formula: CTLFormula) -> Set[str]:
        """EG φ - exists path where φ always holds"""
        phi_sat = self._sat(formula)

        # Greatest fixed point
        result = phi_sat.copy()
        changed = True

        while changed:
            changed = False
            to_remove = set()

            for sid in result:
                succs = self.structure.get_successors(sid)
                if not succs:
                    to_remove.add(sid)
                elif not (succs & result):
                    to_remove.add(sid)

            if to_remove:
                result -= to_remove
                changed = True

        return result

    def _sat_af(self, formula: CTLFormula) -> Set[str]:
        """AF φ - on all paths, φ eventually holds"""
        # AF φ = ¬EG¬φ
        not_phi = formula.negate()
        eg_not_phi = self._sat_eg(not_phi)
        return set(self.structure.states.keys()) - eg_not_phi

    def _sat_ag(self, formula: CTLFormula) -> Set[str]:
        """AG φ - on all paths, φ always holds"""
        # AG φ = ¬EF¬φ
        not_phi = formula.negate()
        ef_not_phi = self._sat_ef(not_phi)
        return set(self.structure.states.keys()) - ef_not_phi

    def verify(
        self,
        formula: CTLFormula
    ) -> Tuple[bool, Optional[List[str]]]:
        """Verify formula holds in all initial states"""
        sat_states = self.check(formula)

        if self.structure.initial_states <= sat_states:
            return True, None

        # Find counterexample (state not satisfying)
        violating = self.structure.initial_states - sat_states
        return False, list(violating)


# Export all
__all__ = [
    'TemporalOperator',
    'TemporalFormula',
    'LTLFormula',
    'CTLFormula',
    'KripkeState',
    'KripkeStructure',
    'TemporalReasoner',
    'ModelChecker',
]
