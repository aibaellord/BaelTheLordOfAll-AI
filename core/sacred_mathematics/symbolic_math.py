"""
⚡ SYMBOLIC MATHEMATICS ⚡
=========================
Symbolic computation engine.

Features:
- Expression representation
- Algebraic manipulation
- Simplification
- Symbolic differentiation/integration
"""

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from collections import defaultdict
import uuid


class OperationType(Enum):
    """Mathematical operations"""
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    POW = auto()
    NEG = auto()
    SIN = auto()
    COS = auto()
    TAN = auto()
    EXP = auto()
    LOG = auto()
    SQRT = auto()
    ABS = auto()


@dataclass
class Symbol:
    """Symbolic variable"""
    name: str
    assumptions: Dict[str, bool] = field(default_factory=dict)  # e.g., {'positive': True}

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, Symbol):
            return self.name == other.name
        return False

    def __repr__(self):
        return self.name

    def __add__(self, other):
        return Expression(OperationType.ADD, [self, other])

    def __radd__(self, other):
        return Expression(OperationType.ADD, [other, self])

    def __mul__(self, other):
        return Expression(OperationType.MUL, [self, other])

    def __rmul__(self, other):
        return Expression(OperationType.MUL, [other, self])

    def __sub__(self, other):
        return Expression(OperationType.SUB, [self, other])

    def __rsub__(self, other):
        return Expression(OperationType.SUB, [other, self])

    def __truediv__(self, other):
        return Expression(OperationType.DIV, [self, other])

    def __pow__(self, other):
        return Expression(OperationType.POW, [self, other])

    def __neg__(self):
        return Expression(OperationType.NEG, [self])


@dataclass
class Expression:
    """Symbolic expression"""
    operation: Optional[OperationType] = None
    operands: List[Any] = field(default_factory=list)

    def __repr__(self):
        if self.operation is None:
            return str(self.operands[0]) if self.operands else "0"

        op_symbols = {
            OperationType.ADD: '+',
            OperationType.SUB: '-',
            OperationType.MUL: '*',
            OperationType.DIV: '/',
            OperationType.POW: '**',
        }

        if self.operation in op_symbols:
            return f"({self.operands[0]} {op_symbols[self.operation]} {self.operands[1]})"
        elif self.operation == OperationType.NEG:
            return f"-{self.operands[0]}"
        else:
            return f"{self.operation.name.lower()}({self.operands[0]})"

    def __add__(self, other):
        return Expression(OperationType.ADD, [self, other])

    def __radd__(self, other):
        return Expression(OperationType.ADD, [other, self])

    def __mul__(self, other):
        return Expression(OperationType.MUL, [self, other])

    def __rmul__(self, other):
        return Expression(OperationType.MUL, [other, self])

    def __sub__(self, other):
        return Expression(OperationType.SUB, [self, other])

    def __truediv__(self, other):
        return Expression(OperationType.DIV, [self, other])

    def __pow__(self, other):
        return Expression(OperationType.POW, [self, other])

    def __neg__(self):
        return Expression(OperationType.NEG, [self])

    def get_symbols(self) -> Set[Symbol]:
        """Get all symbols in expression"""
        symbols = set()

        for operand in self.operands:
            if isinstance(operand, Symbol):
                symbols.add(operand)
            elif isinstance(operand, Expression):
                symbols.update(operand.get_symbols())

        return symbols

    def substitute(self, mapping: Dict[str, Any]) -> 'Expression':
        """Substitute values for symbols"""
        new_operands = []

        for operand in self.operands:
            if isinstance(operand, Symbol):
                if operand.name in mapping:
                    new_operands.append(mapping[operand.name])
                else:
                    new_operands.append(operand)
            elif isinstance(operand, Expression):
                new_operands.append(operand.substitute(mapping))
            else:
                new_operands.append(operand)

        return Expression(self.operation, new_operands)

    def evaluate(self, mapping: Dict[str, float] = None) -> float:
        """Evaluate expression numerically"""
        mapping = mapping or {}

        def eval_operand(op):
            if isinstance(op, (int, float)):
                return float(op)
            elif isinstance(op, Symbol):
                if op.name in mapping:
                    return float(mapping[op.name])
                raise ValueError(f"No value for symbol {op.name}")
            elif isinstance(op, Expression):
                return op.evaluate(mapping)
            else:
                return float(op)

        if self.operation is None:
            return eval_operand(self.operands[0]) if self.operands else 0.0

        vals = [eval_operand(op) for op in self.operands]

        if self.operation == OperationType.ADD:
            return vals[0] + vals[1]
        elif self.operation == OperationType.SUB:
            return vals[0] - vals[1]
        elif self.operation == OperationType.MUL:
            return vals[0] * vals[1]
        elif self.operation == OperationType.DIV:
            return vals[0] / vals[1]
        elif self.operation == OperationType.POW:
            return vals[0] ** vals[1]
        elif self.operation == OperationType.NEG:
            return -vals[0]
        elif self.operation == OperationType.SIN:
            return math.sin(vals[0])
        elif self.operation == OperationType.COS:
            return math.cos(vals[0])
        elif self.operation == OperationType.TAN:
            return math.tan(vals[0])
        elif self.operation == OperationType.EXP:
            return math.exp(vals[0])
        elif self.operation == OperationType.LOG:
            return math.log(vals[0])
        elif self.operation == OperationType.SQRT:
            return math.sqrt(vals[0])
        elif self.operation == OperationType.ABS:
            return abs(vals[0])

        return 0.0


@dataclass
class Polynomial:
    """Polynomial representation"""
    # Coefficients: index = power, value = coefficient
    # [1, 2, 3] = 1 + 2x + 3x²
    coefficients: List[float] = field(default_factory=list)
    variable: str = "x"

    @property
    def degree(self) -> int:
        """Get polynomial degree"""
        for i in range(len(self.coefficients) - 1, -1, -1):
            if abs(self.coefficients[i]) > 1e-10:
                return i
        return 0

    def __repr__(self):
        terms = []
        for i, c in enumerate(self.coefficients):
            if abs(c) < 1e-10:
                continue

            if i == 0:
                terms.append(str(c))
            elif i == 1:
                if c == 1:
                    terms.append(self.variable)
                else:
                    terms.append(f"{c}{self.variable}")
            else:
                if c == 1:
                    terms.append(f"{self.variable}^{i}")
                else:
                    terms.append(f"{c}{self.variable}^{i}")

        return " + ".join(terms) if terms else "0"

    def __add__(self, other: 'Polynomial') -> 'Polynomial':
        max_len = max(len(self.coefficients), len(other.coefficients))
        result = [0.0] * max_len

        for i, c in enumerate(self.coefficients):
            result[i] += c
        for i, c in enumerate(other.coefficients):
            result[i] += c

        return Polynomial(result, self.variable)

    def __mul__(self, other: 'Polynomial') -> 'Polynomial':
        result = [0.0] * (len(self.coefficients) + len(other.coefficients) - 1)

        for i, c1 in enumerate(self.coefficients):
            for j, c2 in enumerate(other.coefficients):
                result[i + j] += c1 * c2

        return Polynomial(result, self.variable)

    def evaluate(self, x: float) -> float:
        """Evaluate polynomial at x"""
        result = 0.0
        for i, c in enumerate(self.coefficients):
            result += c * (x ** i)
        return result

    def derivative(self) -> 'Polynomial':
        """Get derivative"""
        if len(self.coefficients) <= 1:
            return Polynomial([0], self.variable)

        result = [i * c for i, c in enumerate(self.coefficients) if i > 0]
        return Polynomial(result, self.variable)

    def integrate(self) -> 'Polynomial':
        """Get indefinite integral (constant = 0)"""
        result = [0] + [c / (i + 1) for i, c in enumerate(self.coefficients)]
        return Polynomial(result, self.variable)


@dataclass
class Rational:
    """Rational number representation"""
    numerator: int
    denominator: int = 1

    def __post_init__(self):
        self._reduce()

    def _reduce(self):
        """Reduce to lowest terms"""
        def gcd(a, b):
            while b:
                a, b = b, a % b
            return a

        g = gcd(abs(self.numerator), abs(self.denominator))
        self.numerator //= g
        self.denominator //= g

        if self.denominator < 0:
            self.numerator = -self.numerator
            self.denominator = -self.denominator

    def __repr__(self):
        if self.denominator == 1:
            return str(self.numerator)
        return f"{self.numerator}/{self.denominator}"

    def __float__(self):
        return self.numerator / self.denominator

    def __add__(self, other: 'Rational') -> 'Rational':
        num = self.numerator * other.denominator + other.numerator * self.denominator
        den = self.denominator * other.denominator
        return Rational(num, den)

    def __mul__(self, other: 'Rational') -> 'Rational':
        return Rational(
            self.numerator * other.numerator,
            self.denominator * other.denominator
        )

    def __truediv__(self, other: 'Rational') -> 'Rational':
        return Rational(
            self.numerator * other.denominator,
            self.denominator * other.numerator
        )


class SymbolicEngine:
    """
    Core symbolic computation engine.
    """

    def __init__(self):
        self.symbols: Dict[str, Symbol] = {}
        self.constants: Dict[str, float] = {
            'pi': math.pi,
            'e': math.e,
            'phi': (1 + math.sqrt(5)) / 2,  # Golden ratio
        }

    def symbol(self, name: str, **assumptions) -> Symbol:
        """Create or get symbol"""
        if name not in self.symbols:
            self.symbols[name] = Symbol(name, assumptions)
        return self.symbols[name]

    def sin(self, expr: Union[Symbol, Expression]) -> Expression:
        return Expression(OperationType.SIN, [expr])

    def cos(self, expr: Union[Symbol, Expression]) -> Expression:
        return Expression(OperationType.COS, [expr])

    def exp(self, expr: Union[Symbol, Expression]) -> Expression:
        return Expression(OperationType.EXP, [expr])

    def log(self, expr: Union[Symbol, Expression]) -> Expression:
        return Expression(OperationType.LOG, [expr])

    def sqrt(self, expr: Union[Symbol, Expression]) -> Expression:
        return Expression(OperationType.SQRT, [expr])

    def diff(
        self,
        expr: Expression,
        symbol: Symbol
    ) -> Expression:
        """Symbolic differentiation"""
        return self._differentiate(expr, symbol)

    def _differentiate(
        self,
        expr: Any,
        symbol: Symbol
    ) -> Any:
        """Internal differentiation"""
        if isinstance(expr, (int, float)):
            return 0

        if isinstance(expr, Symbol):
            return 1 if expr == symbol else 0

        if not isinstance(expr, Expression):
            return 0

        op = expr.operation

        if op == OperationType.ADD:
            return Expression(
                OperationType.ADD,
                [self._differentiate(expr.operands[0], symbol),
                 self._differentiate(expr.operands[1], symbol)]
            )

        elif op == OperationType.SUB:
            return Expression(
                OperationType.SUB,
                [self._differentiate(expr.operands[0], symbol),
                 self._differentiate(expr.operands[1], symbol)]
            )

        elif op == OperationType.MUL:
            # Product rule: (uv)' = u'v + uv'
            u, v = expr.operands
            du = self._differentiate(u, symbol)
            dv = self._differentiate(v, symbol)
            return Expression(OperationType.ADD, [
                Expression(OperationType.MUL, [du, v]),
                Expression(OperationType.MUL, [u, dv])
            ])

        elif op == OperationType.DIV:
            # Quotient rule: (u/v)' = (u'v - uv')/v²
            u, v = expr.operands
            du = self._differentiate(u, symbol)
            dv = self._differentiate(v, symbol)
            return Expression(OperationType.DIV, [
                Expression(OperationType.SUB, [
                    Expression(OperationType.MUL, [du, v]),
                    Expression(OperationType.MUL, [u, dv])
                ]),
                Expression(OperationType.POW, [v, 2])
            ])

        elif op == OperationType.POW:
            # Power rule for constant exponent: (x^n)' = n*x^(n-1)
            base, exp = expr.operands
            if isinstance(exp, (int, float)):
                return Expression(OperationType.MUL, [
                    exp,
                    Expression(OperationType.MUL, [
                        Expression(OperationType.POW, [base, exp - 1]),
                        self._differentiate(base, symbol)
                    ])
                ])

        elif op == OperationType.SIN:
            # (sin u)' = cos(u) * u'
            u = expr.operands[0]
            return Expression(OperationType.MUL, [
                Expression(OperationType.COS, [u]),
                self._differentiate(u, symbol)
            ])

        elif op == OperationType.COS:
            # (cos u)' = -sin(u) * u'
            u = expr.operands[0]
            return Expression(OperationType.MUL, [
                Expression(OperationType.NEG, [
                    Expression(OperationType.SIN, [u])
                ]),
                self._differentiate(u, symbol)
            ])

        elif op == OperationType.EXP:
            # (e^u)' = e^u * u'
            u = expr.operands[0]
            return Expression(OperationType.MUL, [
                expr,
                self._differentiate(u, symbol)
            ])

        elif op == OperationType.LOG:
            # (ln u)' = u'/u
            u = expr.operands[0]
            return Expression(OperationType.DIV, [
                self._differentiate(u, symbol),
                u
            ])

        return 0


class AlgebraicManipulator:
    """
    Algebraic expression manipulation.
    """

    def expand(self, expr: Expression) -> Expression:
        """Expand expression"""
        # Simple implementation - expand (a+b)(c+d)
        if expr.operation != OperationType.MUL:
            return expr

        left, right = expr.operands

        if isinstance(left, Expression) and left.operation == OperationType.ADD:
            if isinstance(right, Expression) and right.operation == OperationType.ADD:
                # (a+b)(c+d) = ac + ad + bc + bd
                a, b = left.operands
                c, d = right.operands
                return Expression(OperationType.ADD, [
                    Expression(OperationType.ADD, [
                        Expression(OperationType.MUL, [a, c]),
                        Expression(OperationType.MUL, [a, d])
                    ]),
                    Expression(OperationType.ADD, [
                        Expression(OperationType.MUL, [b, c]),
                        Expression(OperationType.MUL, [b, d])
                    ])
                ])

        return expr

    def factor(self, poly: Polynomial) -> List[Polynomial]:
        """Factor polynomial (simple cases)"""
        # Try to find rational roots
        factors = []

        if poly.degree == 2:
            # ax² + bx + c
            a = poly.coefficients[2] if len(poly.coefficients) > 2 else 0
            b = poly.coefficients[1] if len(poly.coefficients) > 1 else 0
            c = poly.coefficients[0] if len(poly.coefficients) > 0 else 0

            discriminant = b**2 - 4*a*c

            if discriminant >= 0:
                r1 = (-b + math.sqrt(discriminant)) / (2*a)
                r2 = (-b - math.sqrt(discriminant)) / (2*a)

                # (x - r1)(x - r2) * a
                factors.append(Polynomial([-r1, 1], poly.variable))
                factors.append(Polynomial([-r2, 1], poly.variable))

        return factors if factors else [poly]


class ExpressionSimplifier:
    """
    Simplifies mathematical expressions.
    """

    def simplify(self, expr: Expression) -> Expression:
        """Simplify expression"""
        if not isinstance(expr, Expression):
            return expr

        # Simplify operands first
        simplified_operands = [
            self.simplify(op) if isinstance(op, Expression) else op
            for op in expr.operands
        ]

        op = expr.operation

        # Simplification rules
        if op == OperationType.ADD:
            left, right = simplified_operands

            # x + 0 = x
            if self._is_zero(right):
                return left
            if self._is_zero(left):
                return right

            # Combine constants
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                return left + right

        elif op == OperationType.MUL:
            left, right = simplified_operands

            # x * 0 = 0
            if self._is_zero(left) or self._is_zero(right):
                return 0

            # x * 1 = x
            if self._is_one(left):
                return right
            if self._is_one(right):
                return left

            # Combine constants
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                return left * right

        elif op == OperationType.POW:
            base, exp = simplified_operands

            # x^0 = 1
            if self._is_zero(exp):
                return 1

            # x^1 = x
            if self._is_one(exp):
                return base

        elif op == OperationType.NEG:
            inner = simplified_operands[0]

            # --x = x
            if isinstance(inner, Expression) and inner.operation == OperationType.NEG:
                return inner.operands[0]

        return Expression(op, simplified_operands)

    def _is_zero(self, val) -> bool:
        if isinstance(val, (int, float)):
            return abs(val) < 1e-10
        return False

    def _is_one(self, val) -> bool:
        if isinstance(val, (int, float)):
            return abs(val - 1) < 1e-10
        return False


# Export all
__all__ = [
    'OperationType',
    'Symbol',
    'Expression',
    'Polynomial',
    'Rational',
    'SymbolicEngine',
    'AlgebraicManipulator',
    'ExpressionSimplifier',
]
