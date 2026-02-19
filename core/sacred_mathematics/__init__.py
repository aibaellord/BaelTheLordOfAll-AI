"""
⚡ SACRED MATHEMATICS ENGINE ⚡
===============================
Advanced mathematical reasoning.

This module provides:
- Symbolic mathematics
- Theorem proving
- Numerical methods
- Mathematical reasoning
"""

from .symbolic_math import (
    Symbol,
    Expression,
    Polynomial,
    Rational,
    SymbolicEngine,
    AlgebraicManipulator,
    ExpressionSimplifier,
)

from .theorem_prover import (
    Proposition,
    LogicalOperator,
    ProofStep,
    Proof,
    Axiom,
    Theorem,
    ProofStrategy,
    TheoremProver,
    NaturalDeduction,
)

from .numerical_methods import (
    NumericalSolver,
    RootFinder,
    Integrator,
    Differentiator,
    LinearAlgebraSolver,
    OptimizationSolver,
    ODESolver,
)

from .mathematical_reasoning import (
    MathematicalConcept,
    MathematicalRelation,
    MathematicalDomain,
    ConceptGraph,
    MathematicalReasoner,
    ProofAssistant,
)

__all__ = [
    # Symbolic Math
    'Symbol',
    'Expression',
    'Polynomial',
    'Rational',
    'SymbolicEngine',
    'AlgebraicManipulator',
    'ExpressionSimplifier',

    # Theorem Prover
    'Proposition',
    'LogicalOperator',
    'ProofStep',
    'Proof',
    'Axiom',
    'Theorem',
    'ProofStrategy',
    'TheoremProver',
    'NaturalDeduction',

    # Numerical Methods
    'NumericalSolver',
    'RootFinder',
    'Integrator',
    'Differentiator',
    'LinearAlgebraSolver',
    'OptimizationSolver',
    'ODESolver',

    # Mathematical Reasoning
    'MathematicalConcept',
    'MathematicalRelation',
    'MathematicalDomain',
    'ConceptGraph',
    'MathematicalReasoner',
    'ProofAssistant',
]
