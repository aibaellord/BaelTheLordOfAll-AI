"""
BAEL - Neural Symbolic Reasoning
Combines neural networks with symbolic AI for hybrid reasoning.

This module implements:
- Symbolic knowledge representation
- Neural embedding of symbols
- Hybrid inference combining both approaches
- Logical reasoning with neural flexibility
"""

import asyncio
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# =============================================================================
# SYMBOLIC REPRESENTATION
# =============================================================================

class LogicalOperator(Enum):
    """Logical operators for symbolic reasoning."""
    AND = "and"
    OR = "or"
    NOT = "not"
    IMPLIES = "implies"
    IFF = "iff"
    FORALL = "forall"
    EXISTS = "exists"


class ExpressionType(Enum):
    """Types of logical expressions."""
    ATOM = "atom"
    COMPOUND = "compound"
    QUANTIFIED = "quantified"
    RULE = "rule"
    FACT = "fact"


@dataclass
class Symbol:
    """A symbol in the knowledge base."""
    name: str
    type: str  # concept, relation, function, variable
    arity: int = 0
    domain: Optional[str] = None
    embedding: Optional[List[float]] = None

    def __hash__(self):
        return hash((self.name, self.type))

    def __eq__(self, other):
        if isinstance(other, Symbol):
            return self.name == other.name and self.type == other.type
        return False


@dataclass
class LogicalExpression:
    """A logical expression."""
    type: ExpressionType
    operator: Optional[LogicalOperator] = None
    symbol: Optional[Symbol] = None
    arguments: List[Any] = field(default_factory=list)
    confidence: float = 1.0

    def __str__(self) -> str:
        if self.type == ExpressionType.ATOM:
            if not self.arguments:
                return self.symbol.name if self.symbol else "?"
            args = ", ".join(str(a) for a in self.arguments)
            return f"{self.symbol.name}({args})" if self.symbol else f"?({args})"
        elif self.type == ExpressionType.COMPOUND:
            if self.operator == LogicalOperator.NOT:
                return f"NOT {self.arguments[0]}"
            elif self.operator in [LogicalOperator.AND, LogicalOperator.OR]:
                op_str = f" {self.operator.value.upper()} "
                return f"({op_str.join(str(a) for a in self.arguments)})"
            elif self.operator == LogicalOperator.IMPLIES:
                return f"({self.arguments[0]} -> {self.arguments[1]})"
            elif self.operator == LogicalOperator.IFF:
                return f"({self.arguments[0]} <-> {self.arguments[1]})"
        elif self.type == ExpressionType.QUANTIFIED:
            quantifier = self.operator.value.upper() if self.operator else "?"
            var = self.arguments[0] if self.arguments else "x"
            body = self.arguments[1] if len(self.arguments) > 1 else "?"
            return f"{quantifier} {var}: {body}"
        return "?"


@dataclass
class Rule:
    """An inference rule."""
    id: str
    name: str
    premises: List[LogicalExpression]
    conclusion: LogicalExpression
    confidence: float = 1.0
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Fact:
    """A fact in the knowledge base."""
    id: str
    expression: LogicalExpression
    source: str = "unknown"
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)


# =============================================================================
# KNOWLEDGE BASE
# =============================================================================

class SymbolicKnowledgeBase:
    """Symbolic knowledge base with facts and rules."""

    def __init__(self):
        self.symbols: Dict[str, Symbol] = {}
        self.facts: Dict[str, Fact] = {}
        self.rules: Dict[str, Rule] = {}
        self.type_hierarchy: Dict[str, Set[str]] = {}  # type -> parent types

    def add_symbol(self, symbol: Symbol) -> None:
        """Add a symbol to the knowledge base."""
        self.symbols[symbol.name] = symbol

    def get_symbol(self, name: str) -> Optional[Symbol]:
        """Get a symbol by name."""
        return self.symbols.get(name)

    def add_fact(self, fact: Fact) -> None:
        """Add a fact to the knowledge base."""
        self.facts[fact.id] = fact

    def remove_fact(self, fact_id: str) -> None:
        """Remove a fact from the knowledge base."""
        if fact_id in self.facts:
            del self.facts[fact_id]

    def add_rule(self, rule: Rule) -> None:
        """Add an inference rule."""
        self.rules[rule.id] = rule

    def query_facts(
        self,
        predicate: Optional[str] = None,
        min_confidence: float = 0.0
    ) -> List[Fact]:
        """Query facts matching criteria."""
        results = []

        for fact in self.facts.values():
            if fact.confidence < min_confidence:
                continue

            if predicate:
                if fact.expression.symbol and fact.expression.symbol.name == predicate:
                    results.append(fact)
            else:
                results.append(fact)

        return results

    def define_type_hierarchy(self, type_name: str, parent_types: List[str]) -> None:
        """Define type hierarchy relationships."""
        self.type_hierarchy[type_name] = set(parent_types)

    def is_subtype(self, type_a: str, type_b: str) -> bool:
        """Check if type_a is a subtype of type_b."""
        if type_a == type_b:
            return True

        parents = self.type_hierarchy.get(type_a, set())
        if type_b in parents:
            return True

        # Recursive check
        for parent in parents:
            if self.is_subtype(parent, type_b):
                return True

        return False


# =============================================================================
# UNIFICATION
# =============================================================================

class Unifier:
    """Implements unification for logical expressions."""

    def unify(
        self,
        expr1: LogicalExpression,
        expr2: LogicalExpression,
        substitution: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Attempt to unify two expressions."""
        if substitution is None:
            substitution = {}

        # Apply existing substitutions
        expr1 = self._apply_substitution(expr1, substitution)
        expr2 = self._apply_substitution(expr2, substitution)

        # Same expression
        if self._expressions_equal(expr1, expr2):
            return substitution

        # Variable unification
        if self._is_variable(expr1):
            return self._unify_variable(expr1, expr2, substitution)
        if self._is_variable(expr2):
            return self._unify_variable(expr2, expr1, substitution)

        # Compound expression unification
        if expr1.type == ExpressionType.ATOM and expr2.type == ExpressionType.ATOM:
            if expr1.symbol != expr2.symbol:
                return None
            if len(expr1.arguments) != len(expr2.arguments):
                return None

            for arg1, arg2 in zip(expr1.arguments, expr2.arguments):
                if isinstance(arg1, LogicalExpression) and isinstance(arg2, LogicalExpression):
                    result = self.unify(arg1, arg2, substitution)
                    if result is None:
                        return None
                    substitution = result
                elif arg1 != arg2:
                    return None

            return substitution

        return None

    def _is_variable(self, expr: LogicalExpression) -> bool:
        """Check if expression is a variable."""
        return (
            expr.type == ExpressionType.ATOM and
            expr.symbol is not None and
            expr.symbol.type == "variable"
        )

    def _unify_variable(
        self,
        var: LogicalExpression,
        expr: LogicalExpression,
        substitution: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Unify a variable with an expression."""
        if not var.symbol:
            return None

        var_name = var.symbol.name

        if var_name in substitution:
            return self.unify(substitution[var_name], expr, substitution)

        if self._occurs_check(var_name, expr):
            return None

        new_substitution = substitution.copy()
        new_substitution[var_name] = expr
        return new_substitution

    def _occurs_check(self, var_name: str, expr: LogicalExpression) -> bool:
        """Check if variable occurs in expression (for infinite loop prevention)."""
        if self._is_variable(expr):
            return expr.symbol is not None and expr.symbol.name == var_name

        for arg in expr.arguments:
            if isinstance(arg, LogicalExpression):
                if self._occurs_check(var_name, arg):
                    return True

        return False

    def _apply_substitution(
        self,
        expr: LogicalExpression,
        substitution: Dict[str, Any]
    ) -> LogicalExpression:
        """Apply a substitution to an expression."""
        if self._is_variable(expr) and expr.symbol:
            if expr.symbol.name in substitution:
                return substitution[expr.symbol.name]

        if expr.arguments:
            new_args = []
            for arg in expr.arguments:
                if isinstance(arg, LogicalExpression):
                    new_args.append(self._apply_substitution(arg, substitution))
                else:
                    new_args.append(arg)
            return LogicalExpression(
                type=expr.type,
                operator=expr.operator,
                symbol=expr.symbol,
                arguments=new_args,
                confidence=expr.confidence
            )

        return expr

    def _expressions_equal(
        self,
        expr1: LogicalExpression,
        expr2: LogicalExpression
    ) -> bool:
        """Check if two expressions are equal."""
        if expr1.type != expr2.type:
            return False
        if expr1.symbol != expr2.symbol:
            return False
        if len(expr1.arguments) != len(expr2.arguments):
            return False
        for a1, a2 in zip(expr1.arguments, expr2.arguments):
            if isinstance(a1, LogicalExpression) and isinstance(a2, LogicalExpression):
                if not self._expressions_equal(a1, a2):
                    return False
            elif a1 != a2:
                return False
        return True


# =============================================================================
# INFERENCE ENGINE
# =============================================================================

class SymbolicInferenceEngine:
    """Performs symbolic inference using rules."""

    def __init__(self, kb: SymbolicKnowledgeBase):
        self.kb = kb
        self.unifier = Unifier()
        self.inference_trace: List[Dict[str, Any]] = []

    async def forward_chain(
        self,
        max_iterations: int = 100
    ) -> List[Fact]:
        """Forward chaining inference."""
        new_facts = []
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            added_this_round = []

            # Try each rule
            for rule in sorted(
                self.kb.rules.values(),
                key=lambda r: r.priority,
                reverse=True
            ):
                # Try to match premises
                bindings = await self._match_premises(rule.premises)

                for binding in bindings:
                    # Generate conclusion with binding
                    conclusion = self._apply_binding(rule.conclusion, binding)

                    # Check if fact already exists
                    if not self._fact_exists(conclusion):
                        fact_id = hashlib.md5(str(conclusion).encode()).hexdigest()[:12]
                        new_fact = Fact(
                            id=fact_id,
                            expression=conclusion,
                            source=f"inferred by rule {rule.name}",
                            confidence=rule.confidence * min(
                                f.confidence for f in self._get_supporting_facts(binding)
                            ) if self._get_supporting_facts(binding) else rule.confidence
                        )
                        self.kb.add_fact(new_fact)
                        added_this_round.append(new_fact)

                        self.inference_trace.append({
                            "iteration": iteration,
                            "rule": rule.name,
                            "binding": {k: str(v) for k, v in binding.items()},
                            "conclusion": str(conclusion)
                        })

            new_facts.extend(added_this_round)

            if not added_this_round:
                break  # No new facts, reached fixpoint

        return new_facts

    async def backward_chain(
        self,
        goal: LogicalExpression,
        depth: int = 0,
        max_depth: int = 10
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Backward chaining to prove a goal."""
        if depth > max_depth:
            return False, None

        # Check if goal is directly in knowledge base
        for fact in self.kb.facts.values():
            binding = self.unifier.unify(goal, fact.expression)
            if binding is not None:
                return True, binding

        # Try to prove using rules
        for rule in self.kb.rules.values():
            binding = self.unifier.unify(goal, rule.conclusion)
            if binding is not None:
                # Try to prove all premises
                all_premises_proved = True
                combined_binding = binding.copy()

                for premise in rule.premises:
                    applied_premise = self._apply_binding(premise, combined_binding)
                    proved, new_binding = await self.backward_chain(
                        applied_premise,
                        depth + 1,
                        max_depth
                    )

                    if not proved:
                        all_premises_proved = False
                        break

                    if new_binding:
                        combined_binding.update(new_binding)

                if all_premises_proved:
                    return True, combined_binding

        return False, None

    async def _match_premises(
        self,
        premises: List[LogicalExpression]
    ) -> List[Dict[str, Any]]:
        """Find all bindings that satisfy premises."""
        if not premises:
            return [{}]

        # Start with first premise
        first_premise = premises[0]
        bindings = []

        for fact in self.kb.facts.values():
            binding = self.unifier.unify(first_premise, fact.expression)
            if binding is not None:
                bindings.append(binding)

        if len(premises) == 1:
            return bindings

        # Extend bindings for remaining premises
        result_bindings = []

        for binding in bindings:
            # Apply binding to remaining premises
            remaining = [
                self._apply_binding(p, binding)
                for p in premises[1:]
            ]

            # Recursively match
            sub_bindings = await self._match_premises(remaining)

            for sub_binding in sub_bindings:
                combined = binding.copy()
                combined.update(sub_binding)
                result_bindings.append(combined)

        return result_bindings

    def _apply_binding(
        self,
        expr: LogicalExpression,
        binding: Dict[str, Any]
    ) -> LogicalExpression:
        """Apply variable binding to expression."""
        return self.unifier._apply_substitution(expr, binding)

    def _fact_exists(self, expr: LogicalExpression) -> bool:
        """Check if a fact already exists."""
        for fact in self.kb.facts.values():
            if self.unifier._expressions_equal(expr, fact.expression):
                return True
        return False

    def _get_supporting_facts(
        self,
        binding: Dict[str, Any]
    ) -> List[Fact]:
        """Get facts that support a binding."""
        supporting = []
        for value in binding.values():
            if isinstance(value, LogicalExpression):
                for fact in self.kb.facts.values():
                    if self.unifier._expressions_equal(value, fact.expression):
                        supporting.append(fact)
        return supporting


# =============================================================================
# NEURAL COMPONENT
# =============================================================================

class NeuralEmbedder:
    """Provides neural embeddings for symbols and expressions."""

    def __init__(self, embedding_dim: int = 256):
        self.embedding_dim = embedding_dim
        self.symbol_embeddings: Dict[str, List[float]] = {}
        self.relation_embeddings: Dict[str, List[float]] = {}

    async def embed_symbol(self, symbol: Symbol) -> List[float]:
        """Get or create embedding for a symbol."""
        if symbol.name in self.symbol_embeddings:
            return self.symbol_embeddings[symbol.name]

        # Create embedding (in real implementation, would use neural network)
        embedding = self._create_embedding(symbol.name)
        self.symbol_embeddings[symbol.name] = embedding
        symbol.embedding = embedding

        return embedding

    async def embed_expression(
        self,
        expr: LogicalExpression
    ) -> List[float]:
        """Create embedding for a logical expression."""
        if expr.type == ExpressionType.ATOM:
            if expr.symbol:
                base = await self.embed_symbol(expr.symbol)
            else:
                base = [0.0] * self.embedding_dim

            # Combine with argument embeddings
            if expr.arguments:
                arg_embeddings = []
                for arg in expr.arguments:
                    if isinstance(arg, LogicalExpression):
                        arg_emb = await self.embed_expression(arg)
                        arg_embeddings.append(arg_emb)

                if arg_embeddings:
                    # Combine base with arguments
                    combined = base.copy()
                    for i, arg_emb in enumerate(arg_embeddings):
                        weight = 1.0 / (i + 2)  # Decreasing weight for later args
                        combined = [
                            c + weight * a
                            for c, a in zip(combined, arg_emb)
                        ]
                    return combined

            return base

        elif expr.type == ExpressionType.COMPOUND:
            # Combine sub-expression embeddings
            sub_embeddings = []
            for arg in expr.arguments:
                if isinstance(arg, LogicalExpression):
                    sub_emb = await self.embed_expression(arg)
                    sub_embeddings.append(sub_emb)

            if not sub_embeddings:
                return [0.0] * self.embedding_dim

            # Combine based on operator
            if expr.operator == LogicalOperator.AND:
                return self._element_wise_min(sub_embeddings)
            elif expr.operator == LogicalOperator.OR:
                return self._element_wise_max(sub_embeddings)
            elif expr.operator == LogicalOperator.NOT:
                return [-x for x in sub_embeddings[0]]
            else:
                return self._element_wise_mean(sub_embeddings)

        return [0.0] * self.embedding_dim

    async def similarity(
        self,
        expr1: LogicalExpression,
        expr2: LogicalExpression
    ) -> float:
        """Calculate similarity between expressions using embeddings."""
        emb1 = await self.embed_expression(expr1)
        emb2 = await self.embed_expression(expr2)
        return self._cosine_similarity(emb1, emb2)

    def _create_embedding(self, text: str) -> List[float]:
        """Create embedding from text (simplified)."""
        import random
        random.seed(hash(text))
        return [random.gauss(0, 1) for _ in range(self.embedding_dim)]

    def _cosine_similarity(
        self,
        v1: List[float],
        v2: List[float]
    ) -> float:
        """Calculate cosine similarity."""
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _element_wise_min(
        self,
        embeddings: List[List[float]]
    ) -> List[float]:
        """Element-wise minimum of embeddings."""
        if not embeddings:
            return [0.0] * self.embedding_dim
        return [min(emb[i] for emb in embeddings) for i in range(self.embedding_dim)]

    def _element_wise_max(
        self,
        embeddings: List[List[float]]
    ) -> List[float]:
        """Element-wise maximum of embeddings."""
        if not embeddings:
            return [0.0] * self.embedding_dim
        return [max(emb[i] for emb in embeddings) for i in range(self.embedding_dim)]

    def _element_wise_mean(
        self,
        embeddings: List[List[float]]
    ) -> List[float]:
        """Element-wise mean of embeddings."""
        if not embeddings:
            return [0.0] * self.embedding_dim
        n = len(embeddings)
        return [sum(emb[i] for emb in embeddings) / n for i in range(self.embedding_dim)]


# =============================================================================
# HYBRID REASONER
# =============================================================================

class NeuralSymbolicReasoner:
    """Hybrid reasoner combining neural and symbolic approaches."""

    def __init__(self):
        self.kb = SymbolicKnowledgeBase()
        self.inference_engine = SymbolicInferenceEngine(self.kb)
        self.neural_embedder = NeuralEmbedder()
        self.reasoning_trace: List[Dict[str, Any]] = []

    async def add_knowledge(
        self,
        predicate: str,
        arguments: List[str],
        confidence: float = 1.0,
        source: str = "user"
    ) -> Fact:
        """Add knowledge to the system."""
        # Create symbols
        pred_symbol = Symbol(name=predicate, type="relation", arity=len(arguments))
        self.kb.add_symbol(pred_symbol)

        arg_exprs = []
        for arg in arguments:
            arg_symbol = Symbol(name=arg, type="concept")
            self.kb.add_symbol(arg_symbol)
            arg_expr = LogicalExpression(
                type=ExpressionType.ATOM,
                symbol=arg_symbol
            )
            arg_exprs.append(arg_expr)

        # Create fact expression
        expression = LogicalExpression(
            type=ExpressionType.ATOM,
            symbol=pred_symbol,
            arguments=arg_exprs,
            confidence=confidence
        )

        fact_id = hashlib.md5(str(expression).encode()).hexdigest()[:12]
        fact = Fact(
            id=fact_id,
            expression=expression,
            source=source,
            confidence=confidence
        )

        self.kb.add_fact(fact)

        # Embed the fact
        await self.neural_embedder.embed_expression(expression)

        return fact

    async def add_rule(
        self,
        name: str,
        premises: List[Tuple[str, List[str]]],
        conclusion: Tuple[str, List[str]],
        confidence: float = 1.0
    ) -> Rule:
        """Add an inference rule."""
        # Build premise expressions
        premise_exprs = []
        for pred, args in premises:
            pred_symbol = self.kb.get_symbol(pred) or Symbol(name=pred, type="relation", arity=len(args))
            self.kb.add_symbol(pred_symbol)

            arg_exprs = []
            for arg in args:
                if arg.startswith("?"):  # Variable
                    arg_symbol = Symbol(name=arg, type="variable")
                else:
                    arg_symbol = self.kb.get_symbol(arg) or Symbol(name=arg, type="concept")
                    self.kb.add_symbol(arg_symbol)
                arg_expr = LogicalExpression(type=ExpressionType.ATOM, symbol=arg_symbol)
                arg_exprs.append(arg_expr)

            premise_exprs.append(LogicalExpression(
                type=ExpressionType.ATOM,
                symbol=pred_symbol,
                arguments=arg_exprs
            ))

        # Build conclusion expression
        conc_pred, conc_args = conclusion
        conc_symbol = self.kb.get_symbol(conc_pred) or Symbol(name=conc_pred, type="relation", arity=len(conc_args))
        self.kb.add_symbol(conc_symbol)

        conc_arg_exprs = []
        for arg in conc_args:
            if arg.startswith("?"):
                arg_symbol = Symbol(name=arg, type="variable")
            else:
                arg_symbol = self.kb.get_symbol(arg) or Symbol(name=arg, type="concept")
                self.kb.add_symbol(arg_symbol)
            conc_arg_exprs.append(LogicalExpression(type=ExpressionType.ATOM, symbol=arg_symbol))

        conclusion_expr = LogicalExpression(
            type=ExpressionType.ATOM,
            symbol=conc_symbol,
            arguments=conc_arg_exprs
        )

        rule = Rule(
            id=hashlib.md5(name.encode()).hexdigest()[:12],
            name=name,
            premises=premise_exprs,
            conclusion=conclusion_expr,
            confidence=confidence
        )

        self.kb.add_rule(rule)
        return rule

    async def reason(
        self,
        query: Optional[str] = None,
        mode: str = "hybrid"
    ) -> Dict[str, Any]:
        """Perform reasoning."""
        start_time = datetime.now()
        results = {
            "mode": mode,
            "inferred_facts": [],
            "similar_facts": [],
            "trace": []
        }

        if mode in ["symbolic", "hybrid"]:
            # Forward chaining
            new_facts = await self.inference_engine.forward_chain()
            results["inferred_facts"] = [
                {
                    "expression": str(f.expression),
                    "confidence": f.confidence,
                    "source": f.source
                }
                for f in new_facts
            ]
            results["trace"].extend(self.inference_engine.inference_trace)

        if mode in ["neural", "hybrid"] and query:
            # Neural similarity search
            query_parts = query.split()
            if len(query_parts) >= 1:
                query_symbol = Symbol(name=query_parts[0], type="relation")
                query_expr = LogicalExpression(
                    type=ExpressionType.ATOM,
                    symbol=query_symbol
                )

                similar = []
                for fact in self.kb.facts.values():
                    sim = await self.neural_embedder.similarity(
                        query_expr,
                        fact.expression
                    )
                    if sim > 0.5:  # Threshold
                        similar.append({
                            "expression": str(fact.expression),
                            "similarity": sim,
                            "confidence": fact.confidence
                        })

                similar.sort(key=lambda x: x["similarity"], reverse=True)
                results["similar_facts"] = similar[:10]

        results["duration_ms"] = (datetime.now() - start_time).total_seconds() * 1000

        self.reasoning_trace.append(results)
        return results

    async def query(
        self,
        predicate: str,
        arguments: List[str]
    ) -> Dict[str, Any]:
        """Query the knowledge base."""
        # Build query expression
        pred_symbol = self.kb.get_symbol(predicate) or Symbol(name=predicate, type="relation")

        arg_exprs = []
        for arg in arguments:
            if arg.startswith("?"):
                arg_symbol = Symbol(name=arg, type="variable")
            else:
                arg_symbol = self.kb.get_symbol(arg) or Symbol(name=arg, type="concept")
            arg_exprs.append(LogicalExpression(type=ExpressionType.ATOM, symbol=arg_symbol))

        goal = LogicalExpression(
            type=ExpressionType.ATOM,
            symbol=pred_symbol,
            arguments=arg_exprs
        )

        # Try backward chaining
        proved, binding = await self.inference_engine.backward_chain(goal)

        # Also check direct facts
        direct_matches = []
        for fact in self.kb.facts.values():
            match_binding = self.inference_engine.unifier.unify(goal, fact.expression)
            if match_binding is not None:
                direct_matches.append({
                    "fact": str(fact.expression),
                    "binding": {k: str(v) for k, v in match_binding.items()},
                    "confidence": fact.confidence
                })

        return {
            "query": str(goal),
            "proved": proved,
            "binding": {k: str(v) for k, v in binding.items()} if binding else None,
            "direct_matches": direct_matches
        }

    async def explain(
        self,
        fact_id: str
    ) -> Dict[str, Any]:
        """Explain how a fact was derived."""
        fact = self.kb.facts.get(fact_id)
        if not fact:
            return {"error": "Fact not found"}

        explanation = {
            "fact": str(fact.expression),
            "source": fact.source,
            "confidence": fact.confidence,
            "derivation_steps": []
        }

        # Find derivation in trace
        for step in self.inference_engine.inference_trace:
            if step.get("conclusion") == str(fact.expression):
                explanation["derivation_steps"].append(step)

        return explanation


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def example_reasoning():
    """Demonstrate neural-symbolic reasoning."""
    reasoner = NeuralSymbolicReasoner()

    # Add knowledge
    await reasoner.add_knowledge("parent", ["Alice", "Bob"])
    await reasoner.add_knowledge("parent", ["Bob", "Charlie"])
    await reasoner.add_knowledge("human", ["Alice"])
    await reasoner.add_knowledge("human", ["Bob"])
    await reasoner.add_knowledge("human", ["Charlie"])

    # Add rules
    await reasoner.add_rule(
        name="grandparent",
        premises=[
            ("parent", ["?x", "?y"]),
            ("parent", ["?y", "?z"])
        ],
        conclusion=("grandparent", ["?x", "?z"])
    )

    await reasoner.add_rule(
        name="mortal",
        premises=[("human", ["?x"])],
        conclusion=("mortal", ["?x"])
    )

    # Perform reasoning
    results = await reasoner.reason(mode="symbolic")
    print(f"Inferred {len(results['inferred_facts'])} new facts")

    for fact in results["inferred_facts"]:
        print(f"  - {fact['expression']} (confidence: {fact['confidence']:.2f})")

    # Query
    query_result = await reasoner.query("grandparent", ["Alice", "?who"])
    print(f"\nQuery: grandparent(Alice, ?who)")
    print(f"Result: {query_result}")


if __name__ == "__main__":
    asyncio.run(example_reasoning())
