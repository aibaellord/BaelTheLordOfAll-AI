#!/usr/bin/env python3
"""
BAEL - Formula Parser and Evaluator
Comprehensive mathematical formula parsing and evaluation system.

Features:
- Expression parsing
- Operator precedence
- Functions (sin, cos, log, etc.)
- Variables and constants
- Custom functions
- Symbolic differentiation
- Expression simplification
- Unit conversion
- Formula validation
- Expression trees
"""

import asyncio
import logging
import math
import operator
import re
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class TokenType(Enum):
    """Token types."""
    NUMBER = "number"
    IDENTIFIER = "identifier"
    OPERATOR = "operator"
    LPAREN = "lparen"
    RPAREN = "rparen"
    COMMA = "comma"
    EOF = "eof"


class NodeType(Enum):
    """AST node types."""
    NUMBER = "number"
    VARIABLE = "variable"
    BINARY_OP = "binary_op"
    UNARY_OP = "unary_op"
    FUNCTION = "function"


class OperatorAssoc(Enum):
    """Operator associativity."""
    LEFT = "left"
    RIGHT = "right"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Token:
    """Lexer token."""
    type: TokenType
    value: Any
    position: int = 0


@dataclass
class OperatorInfo:
    """Operator information."""
    symbol: str
    precedence: int
    associativity: OperatorAssoc
    func: Callable[[float, float], float]


@dataclass
class FunctionInfo:
    """Function information."""
    name: str
    arg_count: int
    func: Callable[..., float]
    description: str = ""


@dataclass
class ParseError:
    """Parse error."""
    message: str
    position: int
    token: Optional[Token] = None


@dataclass
class EvalResult:
    """Evaluation result."""
    value: float
    variables_used: Set[str]
    functions_used: Set[str]
    success: bool = True
    error: Optional[str] = None


# =============================================================================
# AST NODES
# =============================================================================

class ASTNode(ABC):
    """Abstract syntax tree node."""

    @abstractmethod
    def evaluate(self, context: Dict[str, float]) -> float:
        """Evaluate node."""
        pass

    @abstractmethod
    def to_string(self) -> str:
        """Convert to string."""
        pass

    @abstractmethod
    def get_variables(self) -> Set[str]:
        """Get variables used."""
        pass

    @abstractmethod
    def get_functions(self) -> Set[str]:
        """Get functions used."""
        pass

    @abstractmethod
    def simplify(self) -> "ASTNode":
        """Simplify expression."""
        pass


class NumberNode(ASTNode):
    """Number literal node."""

    def __init__(self, value: float):
        self.value = value

    def evaluate(self, context: Dict[str, float]) -> float:
        return self.value

    def to_string(self) -> str:
        if self.value == int(self.value):
            return str(int(self.value))
        return str(self.value)

    def get_variables(self) -> Set[str]:
        return set()

    def get_functions(self) -> Set[str]:
        return set()

    def simplify(self) -> ASTNode:
        return self


class VariableNode(ASTNode):
    """Variable reference node."""

    def __init__(self, name: str):
        self.name = name

    def evaluate(self, context: Dict[str, float]) -> float:
        if self.name not in context:
            raise ValueError(f"Undefined variable: {self.name}")
        return context[self.name]

    def to_string(self) -> str:
        return self.name

    def get_variables(self) -> Set[str]:
        return {self.name}

    def get_functions(self) -> Set[str]:
        return set()

    def simplify(self) -> ASTNode:
        return self


class BinaryOpNode(ASTNode):
    """Binary operator node."""

    def __init__(self, op: str, left: ASTNode, right: ASTNode):
        self.op = op
        self.left = left
        self.right = right

    def evaluate(self, context: Dict[str, float]) -> float:
        left_val = self.left.evaluate(context)
        right_val = self.right.evaluate(context)

        ops = {
            '+': operator.add,
            '-': operator.sub,
            '*': operator.mul,
            '/': operator.truediv,
            '^': operator.pow,
            '%': operator.mod,
        }

        if self.op not in ops:
            raise ValueError(f"Unknown operator: {self.op}")

        return ops[self.op](left_val, right_val)

    def to_string(self) -> str:
        return f"({self.left.to_string()} {self.op} {self.right.to_string()})"

    def get_variables(self) -> Set[str]:
        return self.left.get_variables() | self.right.get_variables()

    def get_functions(self) -> Set[str]:
        return self.left.get_functions() | self.right.get_functions()

    def simplify(self) -> ASTNode:
        left = self.left.simplify()
        right = self.right.simplify()

        # Constant folding
        if isinstance(left, NumberNode) and isinstance(right, NumberNode):
            return NumberNode(BinaryOpNode(self.op, left, right).evaluate({}))

        # Identity simplifications
        if self.op == '+':
            if isinstance(left, NumberNode) and left.value == 0:
                return right
            if isinstance(right, NumberNode) and right.value == 0:
                return left

        elif self.op == '-':
            if isinstance(right, NumberNode) and right.value == 0:
                return left

        elif self.op == '*':
            if isinstance(left, NumberNode) and left.value == 1:
                return right
            if isinstance(right, NumberNode) and right.value == 1:
                return left
            if isinstance(left, NumberNode) and left.value == 0:
                return NumberNode(0)
            if isinstance(right, NumberNode) and right.value == 0:
                return NumberNode(0)

        elif self.op == '/':
            if isinstance(right, NumberNode) and right.value == 1:
                return left

        elif self.op == '^':
            if isinstance(right, NumberNode) and right.value == 0:
                return NumberNode(1)
            if isinstance(right, NumberNode) and right.value == 1:
                return left

        return BinaryOpNode(self.op, left, right)


class UnaryOpNode(ASTNode):
    """Unary operator node."""

    def __init__(self, op: str, operand: ASTNode):
        self.op = op
        self.operand = operand

    def evaluate(self, context: Dict[str, float]) -> float:
        val = self.operand.evaluate(context)

        if self.op == '-':
            return -val
        elif self.op == '+':
            return val

        raise ValueError(f"Unknown unary operator: {self.op}")

    def to_string(self) -> str:
        return f"({self.op}{self.operand.to_string()})"

    def get_variables(self) -> Set[str]:
        return self.operand.get_variables()

    def get_functions(self) -> Set[str]:
        return self.operand.get_functions()

    def simplify(self) -> ASTNode:
        operand = self.operand.simplify()

        if isinstance(operand, NumberNode):
            return NumberNode(UnaryOpNode(self.op, operand).evaluate({}))

        # Double negation
        if self.op == '-' and isinstance(operand, UnaryOpNode) and operand.op == '-':
            return operand.operand

        return UnaryOpNode(self.op, operand)


class FunctionNode(ASTNode):
    """Function call node."""

    def __init__(
        self,
        name: str,
        args: List[ASTNode],
        func: Callable[..., float]
    ):
        self.name = name
        self.args = args
        self.func = func

    def evaluate(self, context: Dict[str, float]) -> float:
        arg_values = [arg.evaluate(context) for arg in self.args]
        return self.func(*arg_values)

    def to_string(self) -> str:
        args_str = ", ".join(arg.to_string() for arg in self.args)
        return f"{self.name}({args_str})"

    def get_variables(self) -> Set[str]:
        result = set()
        for arg in self.args:
            result |= arg.get_variables()
        return result

    def get_functions(self) -> Set[str]:
        result = {self.name}
        for arg in self.args:
            result |= arg.get_functions()
        return result

    def simplify(self) -> ASTNode:
        simplified_args = [arg.simplify() for arg in self.args]

        # Constant folding
        if all(isinstance(arg, NumberNode) for arg in simplified_args):
            values = [arg.value for arg in simplified_args]
            return NumberNode(self.func(*values))

        return FunctionNode(self.name, simplified_args, self.func)


# =============================================================================
# LEXER
# =============================================================================

class Lexer:
    """Tokenize formula strings."""

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.length = len(text)

    def tokenize(self) -> List[Token]:
        """Tokenize the input."""
        tokens = []

        while self.pos < self.length:
            self._skip_whitespace()

            if self.pos >= self.length:
                break

            char = self.text[self.pos]

            if char.isdigit() or char == '.':
                tokens.append(self._read_number())

            elif char.isalpha() or char == '_':
                tokens.append(self._read_identifier())

            elif char in '+-*/%^':
                tokens.append(Token(TokenType.OPERATOR, char, self.pos))
                self.pos += 1

            elif char == '(':
                tokens.append(Token(TokenType.LPAREN, char, self.pos))
                self.pos += 1

            elif char == ')':
                tokens.append(Token(TokenType.RPAREN, char, self.pos))
                self.pos += 1

            elif char == ',':
                tokens.append(Token(TokenType.COMMA, char, self.pos))
                self.pos += 1

            else:
                raise ValueError(f"Unexpected character '{char}' at position {self.pos}")

        tokens.append(Token(TokenType.EOF, None, self.pos))
        return tokens

    def _skip_whitespace(self):
        while self.pos < self.length and self.text[self.pos].isspace():
            self.pos += 1

    def _read_number(self) -> Token:
        start = self.pos
        has_dot = False
        has_e = False

        while self.pos < self.length:
            char = self.text[self.pos]

            if char.isdigit():
                self.pos += 1
            elif char == '.' and not has_dot:
                has_dot = True
                self.pos += 1
            elif char in 'eE' and not has_e:
                has_e = True
                self.pos += 1
                if self.pos < self.length and self.text[self.pos] in '+-':
                    self.pos += 1
            else:
                break

        value = float(self.text[start:self.pos])
        return Token(TokenType.NUMBER, value, start)

    def _read_identifier(self) -> Token:
        start = self.pos

        while self.pos < self.length:
            char = self.text[self.pos]
            if char.isalnum() or char == '_':
                self.pos += 1
            else:
                break

        name = self.text[start:self.pos]
        return Token(TokenType.IDENTIFIER, name, start)


# =============================================================================
# PARSER
# =============================================================================

class Parser:
    """Parse tokens into AST."""

    def __init__(
        self,
        tokens: List[Token],
        functions: Dict[str, FunctionInfo],
        constants: Dict[str, float]
    ):
        self.tokens = tokens
        self.functions = functions
        self.constants = constants
        self.pos = 0

    def parse(self) -> ASTNode:
        """Parse expression."""
        node = self._parse_expression()

        if self._current().type != TokenType.EOF:
            raise ValueError(f"Unexpected token: {self._current().value}")

        return node

    def _current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, None, -1)

    def _advance(self) -> Token:
        token = self._current()
        self.pos += 1
        return token

    def _parse_expression(self) -> ASTNode:
        """Parse expression with operator precedence."""
        return self._parse_additive()

    def _parse_additive(self) -> ASTNode:
        left = self._parse_multiplicative()

        while self._current().type == TokenType.OPERATOR and self._current().value in '+-':
            op = self._advance().value
            right = self._parse_multiplicative()
            left = BinaryOpNode(op, left, right)

        return left

    def _parse_multiplicative(self) -> ASTNode:
        left = self._parse_power()

        while self._current().type == TokenType.OPERATOR and self._current().value in '*/%':
            op = self._advance().value
            right = self._parse_power()
            left = BinaryOpNode(op, left, right)

        return left

    def _parse_power(self) -> ASTNode:
        left = self._parse_unary()

        if self._current().type == TokenType.OPERATOR and self._current().value == '^':
            self._advance()
            right = self._parse_power()  # Right associative
            return BinaryOpNode('^', left, right)

        return left

    def _parse_unary(self) -> ASTNode:
        if self._current().type == TokenType.OPERATOR and self._current().value in '+-':
            op = self._advance().value
            operand = self._parse_unary()
            return UnaryOpNode(op, operand)

        return self._parse_primary()

    def _parse_primary(self) -> ASTNode:
        token = self._current()

        if token.type == TokenType.NUMBER:
            self._advance()
            return NumberNode(token.value)

        if token.type == TokenType.IDENTIFIER:
            name = token.value
            self._advance()

            # Function call
            if self._current().type == TokenType.LPAREN:
                return self._parse_function_call(name)

            # Constant
            if name in self.constants:
                return NumberNode(self.constants[name])

            # Variable
            return VariableNode(name)

        if token.type == TokenType.LPAREN:
            self._advance()
            node = self._parse_expression()

            if self._current().type != TokenType.RPAREN:
                raise ValueError("Expected ')'")

            self._advance()
            return node

        raise ValueError(f"Unexpected token: {token.value}")

    def _parse_function_call(self, name: str) -> ASTNode:
        if name not in self.functions:
            raise ValueError(f"Unknown function: {name}")

        func_info = self.functions[name]

        self._advance()  # Skip '('

        args = []

        if self._current().type != TokenType.RPAREN:
            args.append(self._parse_expression())

            while self._current().type == TokenType.COMMA:
                self._advance()
                args.append(self._parse_expression())

        if self._current().type != TokenType.RPAREN:
            raise ValueError("Expected ')'")

        self._advance()

        # Check argument count
        if func_info.arg_count >= 0 and len(args) != func_info.arg_count:
            raise ValueError(
                f"Function {name} expects {func_info.arg_count} arguments, "
                f"got {len(args)}"
            )

        return FunctionNode(name, args, func_info.func)


# =============================================================================
# DIFFERENTIATOR
# =============================================================================

class Differentiator:
    """Symbolic differentiation."""

    @staticmethod
    def differentiate(node: ASTNode, variable: str) -> ASTNode:
        """Compute derivative with respect to variable."""
        if isinstance(node, NumberNode):
            return NumberNode(0)

        if isinstance(node, VariableNode):
            if node.name == variable:
                return NumberNode(1)
            return NumberNode(0)

        if isinstance(node, UnaryOpNode):
            inner_deriv = Differentiator.differentiate(node.operand, variable)

            if node.op == '-':
                return UnaryOpNode('-', inner_deriv)
            return inner_deriv

        if isinstance(node, BinaryOpNode):
            left_deriv = Differentiator.differentiate(node.left, variable)
            right_deriv = Differentiator.differentiate(node.right, variable)

            if node.op == '+':
                return BinaryOpNode('+', left_deriv, right_deriv)

            if node.op == '-':
                return BinaryOpNode('-', left_deriv, right_deriv)

            if node.op == '*':
                # Product rule: (f*g)' = f'*g + f*g'
                return BinaryOpNode('+',
                    BinaryOpNode('*', left_deriv, node.right),
                    BinaryOpNode('*', node.left, right_deriv)
                )

            if node.op == '/':
                # Quotient rule: (f/g)' = (f'*g - f*g') / g^2
                return BinaryOpNode('/',
                    BinaryOpNode('-',
                        BinaryOpNode('*', left_deriv, node.right),
                        BinaryOpNode('*', node.left, right_deriv)
                    ),
                    BinaryOpNode('^', node.right, NumberNode(2))
                )

            if node.op == '^':
                # Power rule for constant exponent
                if isinstance(node.right, NumberNode):
                    # f^n -> n * f^(n-1) * f'
                    return BinaryOpNode('*',
                        BinaryOpNode('*',
                            node.right,
                            BinaryOpNode('^', node.left, NumberNode(node.right.value - 1))
                        ),
                        left_deriv
                    )

        # Default case
        return NumberNode(0)


# =============================================================================
# FORMULA ENGINE
# =============================================================================

class FormulaEngine:
    """
    Comprehensive Formula Parser and Evaluator for BAEL.

    Provides mathematical expression parsing and evaluation.
    """

    def __init__(self):
        self._constants: Dict[str, float] = {
            'pi': math.pi,
            'e': math.e,
            'tau': math.tau,
            'inf': float('inf'),
        }

        self._functions: Dict[str, FunctionInfo] = {}
        self._register_builtin_functions()

        self._variables: Dict[str, float] = {}
        self._formula_cache: Dict[str, ASTNode] = {}
        self._stats: Dict[str, int] = defaultdict(int)

    def _register_builtin_functions(self):
        """Register built-in functions."""
        builtins = [
            # Basic math
            FunctionInfo('abs', 1, abs, "Absolute value"),
            FunctionInfo('ceil', 1, math.ceil, "Ceiling"),
            FunctionInfo('floor', 1, math.floor, "Floor"),
            FunctionInfo('round', 1, round, "Round"),
            FunctionInfo('trunc', 1, math.trunc, "Truncate"),

            # Powers and logarithms
            FunctionInfo('sqrt', 1, math.sqrt, "Square root"),
            FunctionInfo('cbrt', 1, lambda x: x ** (1/3), "Cube root"),
            FunctionInfo('pow', 2, math.pow, "Power"),
            FunctionInfo('exp', 1, math.exp, "Exponential"),
            FunctionInfo('log', 1, math.log, "Natural logarithm"),
            FunctionInfo('log10', 1, math.log10, "Base-10 logarithm"),
            FunctionInfo('log2', 1, math.log2, "Base-2 logarithm"),

            # Trigonometric
            FunctionInfo('sin', 1, math.sin, "Sine"),
            FunctionInfo('cos', 1, math.cos, "Cosine"),
            FunctionInfo('tan', 1, math.tan, "Tangent"),
            FunctionInfo('asin', 1, math.asin, "Arc sine"),
            FunctionInfo('acos', 1, math.acos, "Arc cosine"),
            FunctionInfo('atan', 1, math.atan, "Arc tangent"),
            FunctionInfo('atan2', 2, math.atan2, "Two-argument arc tangent"),

            # Hyperbolic
            FunctionInfo('sinh', 1, math.sinh, "Hyperbolic sine"),
            FunctionInfo('cosh', 1, math.cosh, "Hyperbolic cosine"),
            FunctionInfo('tanh', 1, math.tanh, "Hyperbolic tangent"),

            # Angular conversion
            FunctionInfo('degrees', 1, math.degrees, "Radians to degrees"),
            FunctionInfo('radians', 1, math.radians, "Degrees to radians"),

            # Special
            FunctionInfo('factorial', 1, lambda x: math.factorial(int(x)), "Factorial"),
            FunctionInfo('gcd', 2, lambda a, b: math.gcd(int(a), int(b)), "GCD"),

            # Statistics
            FunctionInfo('min', -1, min, "Minimum"),
            FunctionInfo('max', -1, max, "Maximum"),

            # Utility
            FunctionInfo('sign', 1, lambda x: -1 if x < 0 else (1 if x > 0 else 0), "Sign"),
            FunctionInfo('clamp', 3, lambda x, lo, hi: max(lo, min(hi, x)), "Clamp value"),
            FunctionInfo('lerp', 3, lambda a, b, t: a + (b - a) * t, "Linear interpolation"),
        ]

        for func in builtins:
            self._functions[func.name] = func

    # -------------------------------------------------------------------------
    # PARSING
    # -------------------------------------------------------------------------

    def parse(self, formula: str) -> ASTNode:
        """Parse formula string to AST."""
        self._stats["formulas_parsed"] += 1

        # Check cache
        if formula in self._formula_cache:
            return self._formula_cache[formula]

        lexer = Lexer(formula)
        tokens = lexer.tokenize()

        parser = Parser(tokens, self._functions, self._constants)
        ast = parser.parse()

        # Cache
        self._formula_cache[formula] = ast

        return ast

    def validate(self, formula: str) -> Tuple[bool, Optional[str]]:
        """Validate formula syntax."""
        try:
            self.parse(formula)
            return True, None
        except Exception as e:
            return False, str(e)

    # -------------------------------------------------------------------------
    # EVALUATION
    # -------------------------------------------------------------------------

    def evaluate(
        self,
        formula: str,
        variables: Optional[Dict[str, float]] = None
    ) -> EvalResult:
        """Evaluate formula."""
        self._stats["evaluations"] += 1

        try:
            ast = self.parse(formula)

            # Merge variables
            context = dict(self._variables)
            if variables:
                context.update(variables)

            value = ast.evaluate(context)

            return EvalResult(
                value=value,
                variables_used=ast.get_variables(),
                functions_used=ast.get_functions()
            )

        except Exception as e:
            return EvalResult(
                value=float('nan'),
                variables_used=set(),
                functions_used=set(),
                success=False,
                error=str(e)
            )

    def evaluate_with_range(
        self,
        formula: str,
        variable: str,
        start: float,
        end: float,
        step: float
    ) -> List[Tuple[float, float]]:
        """Evaluate formula over a range."""
        ast = self.parse(formula)
        results = []

        x = start
        while x <= end:
            try:
                y = ast.evaluate({variable: x})
                results.append((x, y))
            except:
                results.append((x, float('nan')))

            x += step

        return results

    # -------------------------------------------------------------------------
    # SIMPLIFICATION
    # -------------------------------------------------------------------------

    def simplify(self, formula: str) -> str:
        """Simplify formula."""
        ast = self.parse(formula)
        simplified = ast.simplify()
        return simplified.to_string()

    # -------------------------------------------------------------------------
    # DIFFERENTIATION
    # -------------------------------------------------------------------------

    def differentiate(self, formula: str, variable: str) -> str:
        """Compute derivative."""
        ast = self.parse(formula)
        derivative = Differentiator.differentiate(ast, variable)
        simplified = derivative.simplify()
        return simplified.to_string()

    # -------------------------------------------------------------------------
    # VARIABLES AND CONSTANTS
    # -------------------------------------------------------------------------

    def set_variable(self, name: str, value: float) -> None:
        """Set variable value."""
        self._variables[name] = value

    def get_variable(self, name: str) -> Optional[float]:
        """Get variable value."""
        return self._variables.get(name)

    def clear_variables(self) -> None:
        """Clear all variables."""
        self._variables.clear()

    def add_constant(self, name: str, value: float) -> None:
        """Add constant."""
        self._constants[name] = value

    def get_constants(self) -> Dict[str, float]:
        """Get all constants."""
        return dict(self._constants)

    # -------------------------------------------------------------------------
    # CUSTOM FUNCTIONS
    # -------------------------------------------------------------------------

    def add_function(
        self,
        name: str,
        func: Callable[..., float],
        arg_count: int = -1,
        description: str = ""
    ) -> None:
        """Add custom function."""
        self._functions[name] = FunctionInfo(
            name=name,
            arg_count=arg_count,
            func=func,
            description=description
        )

    def get_functions(self) -> List[str]:
        """Get all function names."""
        return list(self._functions.keys())

    def get_function_info(self, name: str) -> Optional[FunctionInfo]:
        """Get function info."""
        return self._functions.get(name)

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def to_string(self, formula: str) -> str:
        """Convert formula to canonical string form."""
        ast = self.parse(formula)
        return ast.to_string()

    def get_variables_used(self, formula: str) -> Set[str]:
        """Get variables used in formula."""
        ast = self.parse(formula)
        return ast.get_variables()

    def get_functions_used(self, formula: str) -> Set[str]:
        """Get functions used in formula."""
        ast = self.parse(formula)
        return ast.get_functions()

    def clear_cache(self) -> None:
        """Clear formula cache."""
        self._formula_cache.clear()

    def get_stats(self) -> Dict[str, int]:
        """Get engine statistics."""
        return dict(self._stats)


# =============================================================================
# UNIT CONVERTER
# =============================================================================

class UnitConverter:
    """Unit conversion system."""

    def __init__(self):
        self._conversions: Dict[str, Dict[str, float]] = {
            # Length
            'length': {
                'm': 1.0,
                'km': 1000.0,
                'cm': 0.01,
                'mm': 0.001,
                'mi': 1609.344,
                'yd': 0.9144,
                'ft': 0.3048,
                'in': 0.0254,
            },
            # Mass
            'mass': {
                'kg': 1.0,
                'g': 0.001,
                'mg': 0.000001,
                'lb': 0.453592,
                'oz': 0.0283495,
            },
            # Time
            'time': {
                's': 1.0,
                'ms': 0.001,
                'min': 60.0,
                'h': 3600.0,
                'd': 86400.0,
            },
            # Temperature (special handling)
            'temperature': {
                'K': 1.0,  # Base unit
                'C': 1.0,  # Offset: +273.15 to K
                'F': 5/9,  # Scale + offset
            },
            # Angle
            'angle': {
                'rad': 1.0,
                'deg': math.pi / 180,
                'grad': math.pi / 200,
            },
            # Data
            'data': {
                'B': 1.0,
                'KB': 1024.0,
                'MB': 1024 ** 2,
                'GB': 1024 ** 3,
                'TB': 1024 ** 4,
            },
        }

    def convert(
        self,
        value: float,
        from_unit: str,
        to_unit: str
    ) -> Optional[float]:
        """Convert between units."""
        # Find category
        category = None

        for cat, units in self._conversions.items():
            if from_unit in units and to_unit in units:
                category = cat
                break

        if category is None:
            return None

        # Special handling for temperature
        if category == 'temperature':
            return self._convert_temperature(value, from_unit, to_unit)

        # Standard conversion
        units = self._conversions[category]
        base_value = value * units[from_unit]
        return base_value / units[to_unit]

    def _convert_temperature(
        self,
        value: float,
        from_unit: str,
        to_unit: str
    ) -> float:
        """Convert temperature."""
        # Convert to Kelvin first
        if from_unit == 'C':
            kelvin = value + 273.15
        elif from_unit == 'F':
            kelvin = (value - 32) * 5/9 + 273.15
        else:  # K
            kelvin = value

        # Convert from Kelvin
        if to_unit == 'C':
            return kelvin - 273.15
        elif to_unit == 'F':
            return (kelvin - 273.15) * 9/5 + 32
        else:  # K
            return kelvin

    def get_units(self, category: str) -> List[str]:
        """Get units for category."""
        return list(self._conversions.get(category, {}).keys())

    def get_categories(self) -> List[str]:
        """Get all categories."""
        return list(self._conversions.keys())


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Formula Parser."""
    print("=" * 70)
    print("BAEL - FORMULA PARSER DEMO")
    print("Comprehensive Mathematical Expression System")
    print("=" * 70)
    print()

    engine = FormulaEngine()

    # 1. Basic Expressions
    print("1. BASIC EXPRESSIONS:")
    print("-" * 40)

    expressions = [
        "2 + 3",
        "10 - 4 * 2",
        "2 ^ 3 ^ 2",  # Right associative
        "(2 + 3) * 4",
        "100 / 4 / 5",
    ]

    for expr in expressions:
        result = engine.evaluate(expr)
        print(f"   {expr} = {result.value}")
    print()

    # 2. Functions
    print("2. BUILT-IN FUNCTIONS:")
    print("-" * 40)

    function_exprs = [
        "sqrt(16)",
        "sin(pi / 2)",
        "cos(0)",
        "log(e)",
        "abs(-5)",
        "max(3, 7, 2, 9)",
        "round(3.7)",
        "pow(2, 10)",
    ]

    for expr in function_exprs:
        result = engine.evaluate(expr)
        print(f"   {expr} = {result.value}")
    print()

    # 3. Constants
    print("3. CONSTANTS:")
    print("-" * 40)

    print(f"   Available constants: {engine.get_constants()}")

    result = engine.evaluate("2 * pi")
    print(f"   2 * pi = {result.value}")

    result = engine.evaluate("e ^ 2")
    print(f"   e ^ 2 = {result.value}")
    print()

    # 4. Variables
    print("4. VARIABLES:")
    print("-" * 40)

    engine.set_variable("x", 5)
    engine.set_variable("y", 3)

    result = engine.evaluate("x^2 + y^2")
    print(f"   x=5, y=3")
    print(f"   x^2 + y^2 = {result.value}")

    result = engine.evaluate("2*x + 3*y", {"x": 10, "y": 20})
    print(f"   2*x + 3*y (x=10, y=20) = {result.value}")
    print()

    # 5. Custom Functions
    print("5. CUSTOM FUNCTIONS:")
    print("-" * 40)

    engine.add_function(
        "hypot",
        lambda a, b: math.sqrt(a**2 + b**2),
        arg_count=2,
        description="Hypotenuse"
    )

    engine.add_function(
        "avg",
        lambda *args: sum(args) / len(args),
        arg_count=-1,
        description="Average"
    )

    result = engine.evaluate("hypot(3, 4)")
    print(f"   hypot(3, 4) = {result.value}")

    result = engine.evaluate("avg(10, 20, 30, 40)")
    print(f"   avg(10, 20, 30, 40) = {result.value}")
    print()

    # 6. Expression Simplification
    print("6. EXPRESSION SIMPLIFICATION:")
    print("-" * 40)

    simplifications = [
        "x + 0",
        "x * 1",
        "x * 0",
        "x ^ 1",
        "x ^ 0",
        "0 + x + 0",
        "2 + 3 + x",
    ]

    for expr in simplifications:
        simplified = engine.simplify(expr)
        print(f"   {expr} => {simplified}")
    print()

    # 7. Differentiation
    print("7. DIFFERENTIATION:")
    print("-" * 40)

    derivatives = [
        ("x^2", "x"),
        ("3*x + 5", "x"),
        ("x^3", "x"),
        ("x*y", "x"),
        ("x*y", "y"),
    ]

    for formula, var in derivatives:
        deriv = engine.differentiate(formula, var)
        print(f"   d/d{var}({formula}) = {deriv}")
    print()

    # 8. Range Evaluation
    print("8. RANGE EVALUATION:")
    print("-" * 40)

    results = engine.evaluate_with_range("x^2", "x", 0, 5, 1)
    print(f"   f(x) = x^2 for x in [0, 5]:")
    for x, y in results:
        print(f"      f({x}) = {y}")
    print()

    # 9. Formula Validation
    print("9. FORMULA VALIDATION:")
    print("-" * 40)

    formulas = [
        "2 + 3",
        "2 + ",
        "sin(x)",
        "unknown(x)",
        "(2 + 3",
    ]

    for formula in formulas:
        valid, error = engine.validate(formula)
        status = "✓ Valid" if valid else f"✗ Invalid: {error}"
        print(f"   '{formula}' - {status}")
    print()

    # 10. Variable/Function Analysis
    print("10. EXPRESSION ANALYSIS:")
    print("-" * 40)

    formula = "sin(x) + cos(y) * sqrt(z)"

    variables = engine.get_variables_used(formula)
    functions = engine.get_functions_used(formula)

    print(f"   Formula: {formula}")
    print(f"   Variables used: {variables}")
    print(f"   Functions used: {functions}")
    print()

    # 11. Unit Conversion
    print("11. UNIT CONVERSION:")
    print("-" * 40)

    converter = UnitConverter()

    conversions = [
        (100, 'm', 'km'),
        (1, 'mi', 'm'),
        (32, 'F', 'C'),
        (100, 'C', 'F'),
        (1024, 'MB', 'GB'),
        (180, 'deg', 'rad'),
    ]

    for value, from_u, to_u in conversions:
        result = converter.convert(value, from_u, to_u)
        print(f"   {value} {from_u} = {result:.4f} {to_u}")
    print()

    # 12. Complex Expression
    print("12. COMPLEX EXPRESSION:")
    print("-" * 40)

    formula = "(-b + sqrt(b^2 - 4*a*c)) / (2*a)"
    print(f"   Quadratic formula: {formula}")

    # Solve x^2 - 5x + 6 = 0 (roots: 2, 3)
    result = engine.evaluate(formula, {"a": 1, "b": -5, "c": 6})
    print(f"   For x^2 - 5x + 6 = 0:")
    print(f"   x1 = {result.value}")

    # Other root
    formula = "(-b - sqrt(b^2 - 4*a*c)) / (2*a)"
    result = engine.evaluate(formula, {"a": 1, "b": -5, "c": 6})
    print(f"   x2 = {result.value}")
    print()

    # 13. Statistics
    print("13. ENGINE STATISTICS:")
    print("-" * 40)

    stats = engine.get_stats()
    print(f"   Stats: {stats}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Formula Parser Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
