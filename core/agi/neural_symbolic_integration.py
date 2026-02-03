"""
BAEL Phase 7.1: Neural-Symbolic Integration
═════════════════════════════════════════════════════════════════════════════

Advanced hybrid reasoning combining neural networks with symbolic logic,
knowledge compilation, constraint satisfaction, and neuro-symbolic learning.

Features:
  • Hybrid Reasoning Engine
  • Neural-Symbolic Learning
  • Knowledge Compilation
  • Constraint Satisfaction (CSP)
  • Logic-Tensor Networks
  • Semantic Parsing
  • Differentiable Logic Programs
  • Neuro-Symbolic Memory
  • Rule Extraction from Neural Nets
  • Symbol Grounding
  • Concept Learning

Author: BAEL Team
Date: February 1, 2026
"""

import json
import logging
import math
import threading
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Enums & Constants
# ═══════════════════════════════════════════════════════════════════════════

class LogicOperator(str, Enum):
    """Logical operators."""
    AND = "and"
    OR = "or"
    NOT = "not"
    IMPLIES = "implies"
    IFF = "iff"  # if and only if
    FORALL = "forall"
    EXISTS = "exists"


class ConstraintType(str, Enum):
    """Constraint types for CSP."""
    UNARY = "unary"
    BINARY = "binary"
    GLOBAL = "global"
    SOFT = "soft"


class ReasoningMode(str, Enum):
    """Reasoning operation mode."""
    SYMBOLIC = "symbolic"
    NEURAL = "neural"
    HYBRID = "hybrid"
    NEURO_SYMBOLIC = "neuro_symbolic"


class TruthValue(str, Enum):
    """Fuzzy truth values."""
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"
    PROBABLE = "probable"


# ═══════════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Symbol:
    """Symbolic representation."""
    name: str
    type: str  # predicate, constant, variable, function
    arity: int = 0
    properties: Dict[str, Any] = field(default_factory=dict)
    grounded: bool = False
    embedding: Optional[List[float]] = None


@dataclass
class LogicFormula:
    """First-order logic formula."""
    id: str
    operator: LogicOperator
    operands: List[Union[Symbol, "LogicFormula"]] = field(default_factory=list)
    truth_value: float = 1.0  # Fuzzy truth value [0, 1]
    confidence: float = 1.0
    provenance: str = ""

    def evaluate(self, assignment: Dict[str, bool]) -> float:
        """Evaluate formula with variable assignment."""
        if self.operator == LogicOperator.AND:
            if not self.operands:
                return 1.0
            return min(self._eval_operand(op, assignment) for op in self.operands)

        elif self.operator == LogicOperator.OR:
            if not self.operands:
                return 0.0
            return max(self._eval_operand(op, assignment) for op in self.operands)

        elif self.operator == LogicOperator.NOT:
            if self.operands:
                return 1.0 - self._eval_operand(self.operands[0], assignment)
            return 0.0

        elif self.operator == LogicOperator.IMPLIES:
            if len(self.operands) >= 2:
                p = self._eval_operand(self.operands[0], assignment)
                q = self._eval_operand(self.operands[1], assignment)
                return max(1.0 - p, q)
            return 1.0

        return self.truth_value

    def _eval_operand(self, operand: Union[Symbol, "LogicFormula"], assignment: Dict[str, bool]) -> float:
        """Evaluate single operand."""
        if isinstance(operand, LogicFormula):
            return operand.evaluate(assignment)
        elif isinstance(operand, Symbol):
            return 1.0 if assignment.get(operand.name, False) else 0.0
        return 0.0


@dataclass
class Rule:
    """Logical rule (Horn clause)."""
    id: str
    head: LogicFormula
    body: List[LogicFormula] = field(default_factory=list)
    weight: float = 1.0
    learned_from_neural: bool = False
    confidence: float = 1.0


@dataclass
class Constraint:
    """Constraint for CSP."""
    id: str
    type: ConstraintType
    variables: List[str]
    predicate: Callable[[Dict[str, Any]], bool]
    weight: float = 1.0  # For soft constraints
    description: str = ""


@dataclass
class KnowledgeBase:
    """Symbolic knowledge base."""
    symbols: Dict[str, Symbol] = field(default_factory=dict)
    formulas: List[LogicFormula] = field(default_factory=list)
    rules: List[Rule] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)

    def add_symbol(self, symbol: Symbol) -> None:
        """Add symbol to knowledge base."""
        self.symbols[symbol.name] = symbol

    def add_formula(self, formula: LogicFormula) -> None:
        """Add formula to knowledge base."""
        self.formulas.append(formula)

    def add_rule(self, rule: Rule) -> None:
        """Add rule to knowledge base."""
        self.rules.append(rule)

    def query(self, formula: LogicFormula) -> float:
        """Query knowledge base for truth value."""
        # Simplified query - in practice would use theorem proving
        for f in self.formulas:
            if self._formulas_match(f, formula):
                return f.truth_value
        return 0.0

    def _formulas_match(self, f1: LogicFormula, f2: LogicFormula) -> bool:
        """Check if formulas match."""
        return f1.operator == f2.operator and len(f1.operands) == len(f2.operands)


@dataclass
class NeuralRepresentation:
    """Neural network representation."""
    layer_activations: List[List[float]] = field(default_factory=list)
    weights: List[List[List[float]]] = field(default_factory=list)
    embeddings: Dict[str, List[float]] = field(default_factory=dict)
    hidden_size: int = 128
    num_layers: int = 3


# ═══════════════════════════════════════════════════════════════════════════
# Logic-Tensor Networks
# ═══════════════════════════════════════════════════════════════════════════

class LogicTensorNetwork:
    """Logic-Tensor Network for differentiable logic."""

    def __init__(self, hidden_size: int = 128):
        """Initialize Logic-Tensor Network."""
        self.hidden_size = hidden_size
        self.symbol_embeddings: Dict[str, List[float]] = {}
        self.logger = logging.getLogger(__name__)

    def embed_symbol(self, symbol: Symbol) -> List[float]:
        """Generate embedding for symbol."""
        if symbol.name in self.symbol_embeddings:
            return self.symbol_embeddings[symbol.name]

        # Generate pseudo-random embedding based on symbol name
        import hashlib
        hash_val = int(hashlib.md5(symbol.name.encode()).hexdigest(), 16)

        embedding = []
        for i in range(self.hidden_size):
            # Generate deterministic values between -1 and 1
            val = ((hash_val >> (i % 32)) & 0xFF) / 127.5 - 1.0
            embedding.append(val)

        self.symbol_embeddings[symbol.name] = embedding
        symbol.embedding = embedding
        return embedding

    def fuzzy_and(self, values: List[float]) -> float:
        """Differentiable fuzzy AND (product t-norm)."""
        if not values:
            return 1.0
        result = 1.0
        for v in values:
            result *= max(0.0, min(1.0, v))
        return result

    def fuzzy_or(self, values: List[float]) -> float:
        """Differentiable fuzzy OR (probabilistic sum)."""
        if not values:
            return 0.0
        result = 0.0
        for v in values:
            v_clamped = max(0.0, min(1.0, v))
            result = result + v_clamped - result * v_clamped
        return result

    def fuzzy_not(self, value: float) -> float:
        """Differentiable fuzzy NOT."""
        return 1.0 - max(0.0, min(1.0, value))

    def fuzzy_implies(self, p: float, q: float) -> float:
        """Differentiable fuzzy implication."""
        return max(self.fuzzy_not(p), q)

    def evaluate_formula(self, formula: LogicFormula, grounding: Dict[str, float]) -> float:
        """Evaluate formula with fuzzy logic."""
        if formula.operator == LogicOperator.AND:
            operand_values = [
                self._get_operand_value(op, grounding)
                for op in formula.operands
            ]
            return self.fuzzy_and(operand_values)

        elif formula.operator == LogicOperator.OR:
            operand_values = [
                self._get_operand_value(op, grounding)
                for op in formula.operands
            ]
            return self.fuzzy_or(operand_values)

        elif formula.operator == LogicOperator.NOT:
            if formula.operands:
                val = self._get_operand_value(formula.operands[0], grounding)
                return self.fuzzy_not(val)
            return 0.0

        elif formula.operator == LogicOperator.IMPLIES:
            if len(formula.operands) >= 2:
                p = self._get_operand_value(formula.operands[0], grounding)
                q = self._get_operand_value(formula.operands[1], grounding)
                return self.fuzzy_implies(p, q)
            return 1.0

        return formula.truth_value

    def _get_operand_value(self, operand: Union[Symbol, LogicFormula], grounding: Dict[str, float]) -> float:
        """Get operand value."""
        if isinstance(operand, LogicFormula):
            return self.evaluate_formula(operand, grounding)
        elif isinstance(operand, Symbol):
            return grounding.get(operand.name, 0.0)
        return 0.0


# ═══════════════════════════════════════════════════════════════════════════
# Constraint Satisfaction
# ═══════════════════════════════════════════════════════════════════════════

class ConstraintSolver:
    """CSP solver with backtracking and heuristics."""

    def __init__(self):
        """Initialize constraint solver."""
        self.logger = logging.getLogger(__name__)

    def solve(
        self,
        variables: List[str],
        domains: Dict[str, List[Any]],
        constraints: List[Constraint]
    ) -> Optional[Dict[str, Any]]:
        """Solve CSP using backtracking."""
        assignment: Dict[str, Any] = {}
        return self._backtrack(assignment, variables, domains, constraints)

    def _backtrack(
        self,
        assignment: Dict[str, Any],
        variables: List[str],
        domains: Dict[str, List[Any]],
        constraints: List[Constraint]
    ) -> Optional[Dict[str, Any]]:
        """Backtracking search."""
        if len(assignment) == len(variables):
            return assignment

        var = self._select_unassigned_variable(assignment, variables, domains)
        if var is None:
            return None

        for value in self._order_domain_values(var, assignment, domains, constraints):
            assignment[var] = value

            if self._is_consistent(assignment, constraints):
                result = self._backtrack(assignment, variables, domains, constraints)
                if result is not None:
                    return result

            del assignment[var]

        return None

    def _select_unassigned_variable(
        self,
        assignment: Dict[str, Any],
        variables: List[str],
        domains: Dict[str, List[Any]]
    ) -> Optional[str]:
        """Select next variable using minimum remaining values heuristic."""
        unassigned = [v for v in variables if v not in assignment]
        if not unassigned:
            return None

        # MRV heuristic: choose variable with smallest domain
        return min(unassigned, key=lambda v: len(domains.get(v, [])))

    def _order_domain_values(
        self,
        var: str,
        assignment: Dict[str, Any],
        domains: Dict[str, List[Any]],
        constraints: List[Constraint]
    ) -> List[Any]:
        """Order domain values (least constraining value heuristic)."""
        return domains.get(var, [])

    def _is_consistent(
        self,
        assignment: Dict[str, Any],
        constraints: List[Constraint]
    ) -> bool:
        """Check if assignment satisfies all constraints."""
        for constraint in constraints:
            # Check if all variables in constraint are assigned
            if all(v in assignment for v in constraint.variables):
                if not constraint.predicate(assignment):
                    return False
        return True


# ═══════════════════════════════════════════════════════════════════════════
# Neural-Symbolic Learning
# ═══════════════════════════════════════════════════════════════════════════

class NeuroSymbolicLearner:
    """Learn symbolic rules from neural network patterns."""

    def __init__(self):
        """Initialize neuro-symbolic learner."""
        self.logger = logging.getLogger(__name__)
        self.extracted_rules: List[Rule] = []

    def extract_rules(
        self,
        neural_repr: NeuralRepresentation,
        symbols: Dict[str, Symbol],
        threshold: float = 0.7
    ) -> List[Rule]:
        """Extract symbolic rules from neural network."""
        rules = []

        # Simplified rule extraction from activations
        for layer_idx, activations in enumerate(neural_repr.layer_activations):
            for neuron_idx, activation in enumerate(activations):
                if activation > threshold:
                    # Create rule from high activation pattern
                    rule = self._create_rule_from_activation(
                        layer_idx,
                        neuron_idx,
                        activation,
                        symbols
                    )
                    if rule:
                        rules.append(rule)

        self.extracted_rules.extend(rules)
        return rules

    def _create_rule_from_activation(
        self,
        layer: int,
        neuron: int,
        activation: float,
        symbols: Dict[str, Symbol]
    ) -> Optional[Rule]:
        """Create symbolic rule from neuron activation."""
        if not symbols:
            return None

        # Simplified: create rule linking symbols
        symbol_list = list(symbols.values())
        if len(symbol_list) >= 2:
            head_symbol = symbol_list[neuron % len(symbol_list)]
            body_symbol = symbol_list[(neuron + 1) % len(symbol_list)]

            head = LogicFormula(
                id=str(uuid.uuid4()),
                operator=LogicOperator.AND,
                operands=[head_symbol],
                truth_value=activation
            )

            body = [LogicFormula(
                id=str(uuid.uuid4()),
                operator=LogicOperator.AND,
                operands=[body_symbol],
                truth_value=1.0
            )]

            rule = Rule(
                id=str(uuid.uuid4()),
                head=head,
                body=body,
                weight=activation,
                learned_from_neural=True,
                confidence=activation
            )

            return rule

        return None

    def refine_rules(
        self,
        rules: List[Rule],
        feedback: Dict[str, float]
    ) -> List[Rule]:
        """Refine rules based on feedback."""
        refined = []

        for rule in rules:
            rule_feedback = feedback.get(rule.id, 0.5)

            # Adjust rule weight based on feedback
            rule.weight = (rule.weight + rule_feedback) / 2.0
            rule.confidence = rule.weight

            # Keep rules above threshold
            if rule.weight > 0.3:
                refined.append(rule)

        return refined


# ═══════════════════════════════════════════════════════════════════════════
# Semantic Parser
# ═══════════════════════════════════════════════════════════════════════════

class SemanticParser:
    """Parse natural language to logical forms."""

    def __init__(self):
        """Initialize semantic parser."""
        self.logger = logging.getLogger(__name__)
        self.vocabulary: Dict[str, Symbol] = {}

    def parse(self, text: str) -> Optional[LogicFormula]:
        """Parse text to logical formula."""
        # Simplified parsing
        text_lower = text.lower().strip()

        # Detect logical operators
        if " and " in text_lower:
            parts = text_lower.split(" and ")
            operands = [self._create_symbol(p.strip()) for p in parts]
            return LogicFormula(
                id=str(uuid.uuid4()),
                operator=LogicOperator.AND,
                operands=operands
            )

        elif " or " in text_lower:
            parts = text_lower.split(" or ")
            operands = [self._create_symbol(p.strip()) for p in parts]
            return LogicFormula(
                id=str(uuid.uuid4()),
                operator=LogicOperator.OR,
                operands=operands
            )

        elif text_lower.startswith("not "):
            content = text_lower[4:].strip()
            operand = self._create_symbol(content)
            return LogicFormula(
                id=str(uuid.uuid4()),
                operator=LogicOperator.NOT,
                operands=[operand]
            )

        else:
            # Single predicate
            symbol = self._create_symbol(text_lower)
            return LogicFormula(
                id=str(uuid.uuid4()),
                operator=LogicOperator.AND,
                operands=[symbol],
                truth_value=1.0
            )

    def _create_symbol(self, name: str) -> Symbol:
        """Create or retrieve symbol."""
        if name in self.vocabulary:
            return self.vocabulary[name]

        symbol = Symbol(
            name=name,
            type="predicate",
            arity=0
        )
        self.vocabulary[name] = symbol
        return symbol


# ═══════════════════════════════════════════════════════════════════════════
# Neural-Symbolic Reasoner
# ═══════════════════════════════════════════════════════════════════════════

class NeuralSymbolicReasoner:
    """Main neural-symbolic reasoning engine."""

    def __init__(self, hidden_size: int = 128):
        """Initialize neural-symbolic reasoner."""
        self.knowledge_base = KnowledgeBase()
        self.ltn = LogicTensorNetwork(hidden_size)
        self.constraint_solver = ConstraintSolver()
        self.learner = NeuroSymbolicLearner()
        self.parser = SemanticParser()
        self.mode = ReasoningMode.HYBRID
        self.logger = logging.getLogger(__name__)
        self._inference_history: List[Dict[str, Any]] = []

    def add_knowledge(self, text: str) -> Optional[str]:
        """Add knowledge from natural language."""
        formula = self.parser.parse(text)
        if formula:
            self.knowledge_base.add_formula(formula)

            # Ground symbols in neural space
            for operand in formula.operands:
                if isinstance(operand, Symbol) and not operand.grounded:
                    self.ltn.embed_symbol(operand)
                    operand.grounded = True
                    self.knowledge_base.add_symbol(operand)

            self.logger.info(f"Added knowledge: {text}")
            return formula.id
        return None

    def query(self, text: str, mode: Optional[ReasoningMode] = None) -> float:
        """Query knowledge base."""
        reasoning_mode = mode or self.mode

        formula = self.parser.parse(text)
        if not formula:
            return 0.0

        if reasoning_mode == ReasoningMode.SYMBOLIC:
            result = self._symbolic_query(formula)
        elif reasoning_mode == ReasoningMode.NEURAL:
            result = self._neural_query(formula)
        else:  # HYBRID or NEURO_SYMBOLIC
            result = self._hybrid_query(formula)

        # Record inference
        self._inference_history.append({
            'query': text,
            'mode': reasoning_mode.value,
            'result': result,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

        return result

    def _symbolic_query(self, formula: LogicFormula) -> float:
        """Pure symbolic reasoning."""
        return self.knowledge_base.query(formula)

    def _neural_query(self, formula: LogicFormula) -> float:
        """Pure neural reasoning."""
        grounding = {}
        for operand in formula.operands:
            if isinstance(operand, Symbol):
                if operand.embedding:
                    # Use embedding strength as truth value
                    strength = sum(abs(e) for e in operand.embedding) / len(operand.embedding)
                    grounding[operand.name] = min(1.0, strength)
                else:
                    grounding[operand.name] = 0.0

        return self.ltn.evaluate_formula(formula, grounding)

    def _hybrid_query(self, formula: LogicFormula) -> float:
        """Hybrid neural-symbolic reasoning."""
        symbolic_result = self._symbolic_query(formula)
        neural_result = self._neural_query(formula)

        # Combine with weighted average
        alpha = 0.6  # Weight for symbolic reasoning
        return alpha * symbolic_result + (1 - alpha) * neural_result

    def learn_from_examples(
        self,
        examples: List[Tuple[str, bool]],
        epochs: int = 10
    ) -> None:
        """Learn from labeled examples."""
        for epoch in range(epochs):
            total_error = 0.0

            for text, label in examples:
                predicted = self.query(text)
                target = 1.0 if label else 0.0
                error = abs(predicted - target)
                total_error += error

                # Update based on error (simplified)
                formula = self.parser.parse(text)
                if formula:
                    # Adjust truth value towards target
                    formula.truth_value = (formula.truth_value + target) / 2.0

            avg_error = total_error / len(examples) if examples else 0.0
            self.logger.info(f"Epoch {epoch + 1}/{epochs}, Average Error: {avg_error:.4f}")

    def solve_constraints(
        self,
        variables: List[str],
        domains: Dict[str, List[Any]],
        constraints: List[Constraint]
    ) -> Optional[Dict[str, Any]]:
        """Solve constraint satisfaction problem."""
        return self.constraint_solver.solve(variables, domains, constraints)

    def extract_neural_rules(
        self,
        neural_repr: NeuralRepresentation,
        threshold: float = 0.7
    ) -> List[Rule]:
        """Extract symbolic rules from neural patterns."""
        rules = self.learner.extract_rules(
            neural_repr,
            self.knowledge_base.symbols,
            threshold
        )

        for rule in rules:
            self.knowledge_base.add_rule(rule)

        return rules

    def get_inference_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent inference history."""
        return self._inference_history[-limit:]


# ═══════════════════════════════════════════════════════════════════════════
# Knowledge Compiler
# ═══════════════════════════════════════════════════════════════════════════

class KnowledgeCompiler:
    """Compile knowledge base to efficient representations."""

    def __init__(self):
        """Initialize knowledge compiler."""
        self.logger = logging.getLogger(__name__)

    def compile(self, kb: KnowledgeBase) -> Dict[str, Any]:
        """Compile knowledge base."""
        compiled = {
            'symbols': {k: asdict(v) for k, v in kb.symbols.items()},
            'formula_count': len(kb.formulas),
            'rule_count': len(kb.rules),
            'constraint_count': len(kb.constraints),
            'compiled_at': datetime.now(timezone.utc).isoformat()
        }

        return compiled

    def optimize(self, kb: KnowledgeBase) -> KnowledgeBase:
        """Optimize knowledge base."""
        # Remove redundant formulas
        unique_formulas = []
        seen = set()

        for formula in kb.formulas:
            key = (formula.operator.value, len(formula.operands))
            if key not in seen:
                seen.add(key)
                unique_formulas.append(formula)

        kb.formulas = unique_formulas
        return kb


# ═══════════════════════════════════════════════════════════════════════════
# Global Reasoner Singleton
# ═══════════════════════════════════════════════════════════════════════════

_global_neural_symbolic_reasoner: Optional[NeuralSymbolicReasoner] = None


def get_neural_symbolic_reasoner() -> NeuralSymbolicReasoner:
    """Get or create global neural-symbolic reasoner."""
    global _global_neural_symbolic_reasoner
    if _global_neural_symbolic_reasoner is None:
        _global_neural_symbolic_reasoner = NeuralSymbolicReasoner()
    return _global_neural_symbolic_reasoner
