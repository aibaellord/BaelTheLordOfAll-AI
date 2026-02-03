#!/usr/bin/env python3
"""
BAEL - Expression Evaluator
Comprehensive mathematical and logical expression evaluation system.

Features:
- Arithmetic expressions (+, -, *, /, ^, %)
- Comparison operators (==, !=, <, >, <=, >=)
- Logical operators (and, or, not)
- Mathematical functions (sin, cos, sqrt, etc.)
- Variable support
- Custom functions
- Array/list operations
- String operations
- Type coercion
- Safe evaluation sandbox
"""

import asyncio
import logging
import math
import operator
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Callable, Dict, List, Optional, Set, Tuple, Type,
                    TypeVar, Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class TokenType(Enum):
    """Token types."""
    NUMBER = "number"
    STRING = "string"
    BOOLEAN = "boolean"
    IDENTIFIER = "identifier"
    OPERATOR = "operator"
    LPAREN = "lparen"
    RPAREN = "rparen"
    LBRACKET = "lbracket"
    RBRACKET = "rbracket"
    COMMA = "comma"
    DOT = "dot"
    COLON = "colon"
    QUESTION = "question"
    EOF = "eof"


class NodeType(Enum):
    """AST node types."""
    LITERAL = "literal"
    IDENTIFIER = "identifier"
    BINARY_OP = "binary_op"
    UNARY_OP = "unary_op"
    FUNCTION_CALL = "function_call"
    ARRAY = "array"
    INDEX = "index"
    MEMBER = "member"
    TERNARY = "ternary"


class DataType(Enum):
    """Data types."""
    NUMBER = "number"
    STRING = "string"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    NULL = "null"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Token:
    """Lexical token."""
    type: TokenType
    value: Any
    position: int = 0


@dataclass
class EvalResult:
    """Evaluation result."""
    value: Any
    type: DataType
    success: bool = True
    error: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class ExpressionInfo:
    """Expression information."""
    expression: str
    variables: Set[str]
    functions: Set[str]
    operators: Set[str]
    is_valid: bool
    parse_time: float = 0.0


# =============================================================================
# AST NODES
# =============================================================================

class ASTNode(ABC):
    """Abstract AST node."""

    @abstractmethod
    def accept(self, visitor: "ASTVisitor") -> Any:
        pass


@dataclass
class LiteralNode(ASTNode):
    """Literal value node."""
    value: Any
    data_type: DataType

    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_literal(self)


@dataclass
class IdentifierNode(ASTNode):
    """Variable identifier node."""
    name: str

    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_identifier(self)


@dataclass
class BinaryOpNode(ASTNode):
    """Binary operation node."""
    operator: str
    left: ASTNode
    right: ASTNode

    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_binary_op(self)


@dataclass
class UnaryOpNode(ASTNode):
    """Unary operation node."""
    operator: str
    operand: ASTNode

    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_unary_op(self)


@dataclass
class FunctionCallNode(ASTNode):
    """Function call node."""
    name: str
    arguments: List[ASTNode]

    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_function_call(self)


@dataclass
class ArrayNode(ASTNode):
    """Array literal node."""
    elements: List[ASTNode]

    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_array(self)


@dataclass
class IndexNode(ASTNode):
    """Array/object index access node."""
    object: ASTNode
    index: ASTNode

    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_index(self)


@dataclass
class MemberNode(ASTNode):
    """Member access node."""
    object: ASTNode
    member: str

    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_member(self)


@dataclass
class TernaryNode(ASTNode):
    """Ternary conditional node."""
    condition: ASTNode
    if_true: ASTNode
    if_false: ASTNode

    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_ternary(self)


# =============================================================================
# AST VISITOR
# =============================================================================

class ASTVisitor(ABC):
    """Abstract AST visitor."""

    @abstractmethod
    def visit_literal(self, node: LiteralNode) -> Any:
        pass

    @abstractmethod
    def visit_identifier(self, node: IdentifierNode) -> Any:
        pass

    @abstractmethod
    def visit_binary_op(self, node: BinaryOpNode) -> Any:
        pass

    @abstractmethod
    def visit_unary_op(self, node: UnaryOpNode) -> Any:
        pass

    @abstractmethod
    def visit_function_call(self, node: FunctionCallNode) -> Any:
        pass

    @abstractmethod
    def visit_array(self, node: ArrayNode) -> Any:
        pass

    @abstractmethod
    def visit_index(self, node: IndexNode) -> Any:
        pass

    @abstractmethod
    def visit_member(self, node: MemberNode) -> Any:
        pass

    @abstractmethod
    def visit_ternary(self, node: TernaryNode) -> Any:
        pass


# =============================================================================
# LEXER
# =============================================================================

class Lexer:
    """Expression lexer."""

    OPERATORS = {
        '+', '-', '*', '/', '%', '^', '**',
        '==', '!=', '<', '>', '<=', '>=',
        '&&', '||', '!', 'and', 'or', 'not',
        '&', '|', '~', '<<', '>>'
    }

    KEYWORDS = {'true', 'false', 'null', 'and', 'or', 'not', 'in'}

    def __init__(self, expression: str):
        self.expression = expression
        self.pos = 0
        self.length = len(expression)

    def tokenize(self) -> List[Token]:
        """Tokenize expression."""
        tokens = []

        while self.pos < self.length:
            self._skip_whitespace()

            if self.pos >= self.length:
                break

            token = self._next_token()
            if token:
                tokens.append(token)

        tokens.append(Token(TokenType.EOF, None, self.pos))
        return tokens

    def _skip_whitespace(self) -> None:
        """Skip whitespace."""
        while self.pos < self.length and self.expression[self.pos].isspace():
            self.pos += 1

    def _next_token(self) -> Optional[Token]:
        """Get next token."""
        char = self.expression[self.pos]
        start = self.pos

        # String
        if char in '"\'':
            return self._read_string(char)

        # Number
        if char.isdigit() or (char == '.' and self._peek().isdigit()):
            return self._read_number()

        # Identifier or keyword
        if char.isalpha() or char == '_':
            return self._read_identifier()

        # Two-character operators
        two_char = self.expression[self.pos:self.pos + 2]
        if two_char in ('==', '!=', '<=', '>=', '&&', '||', '**', '<<', '>>'):
            self.pos += 2
            return Token(TokenType.OPERATOR, two_char, start)

        # Single-character tokens
        if char == '(':
            self.pos += 1
            return Token(TokenType.LPAREN, char, start)
        elif char == ')':
            self.pos += 1
            return Token(TokenType.RPAREN, char, start)
        elif char == '[':
            self.pos += 1
            return Token(TokenType.LBRACKET, char, start)
        elif char == ']':
            self.pos += 1
            return Token(TokenType.RBRACKET, char, start)
        elif char == ',':
            self.pos += 1
            return Token(TokenType.COMMA, char, start)
        elif char == '.':
            self.pos += 1
            return Token(TokenType.DOT, char, start)
        elif char == ':':
            self.pos += 1
            return Token(TokenType.COLON, char, start)
        elif char == '?':
            self.pos += 1
            return Token(TokenType.QUESTION, char, start)
        elif char in '+-*/%^&|~!<>':
            self.pos += 1
            return Token(TokenType.OPERATOR, char, start)

        # Unknown
        self.pos += 1
        return None

    def _read_string(self, quote: str) -> Token:
        """Read string literal."""
        start = self.pos
        self.pos += 1  # Skip opening quote

        value = []
        while self.pos < self.length:
            char = self.expression[self.pos]

            if char == '\\' and self.pos + 1 < self.length:
                self.pos += 1
                escape_char = self.expression[self.pos]
                if escape_char == 'n':
                    value.append('\n')
                elif escape_char == 't':
                    value.append('\t')
                elif escape_char == 'r':
                    value.append('\r')
                else:
                    value.append(escape_char)
            elif char == quote:
                self.pos += 1
                break
            else:
                value.append(char)

            self.pos += 1

        return Token(TokenType.STRING, ''.join(value), start)

    def _read_number(self) -> Token:
        """Read number literal."""
        start = self.pos
        has_dot = False
        has_exp = False

        while self.pos < self.length:
            char = self.expression[self.pos]

            if char.isdigit():
                self.pos += 1
            elif char == '.' and not has_dot and not has_exp:
                has_dot = True
                self.pos += 1
            elif char in 'eE' and not has_exp:
                has_exp = True
                self.pos += 1
                if self.pos < self.length and self.expression[self.pos] in '+-':
                    self.pos += 1
            else:
                break

        value = self.expression[start:self.pos]
        return Token(TokenType.NUMBER, float(value) if '.' in value or 'e' in value.lower() else int(value), start)

    def _read_identifier(self) -> Token:
        """Read identifier or keyword."""
        start = self.pos

        while self.pos < self.length:
            char = self.expression[self.pos]
            if char.isalnum() or char == '_':
                self.pos += 1
            else:
                break

        value = self.expression[start:self.pos]

        # Keywords
        if value.lower() in ('true', 'false'):
            return Token(TokenType.BOOLEAN, value.lower() == 'true', start)
        elif value.lower() == 'null':
            return Token(TokenType.IDENTIFIER, None, start)
        elif value.lower() in ('and', 'or', 'not', 'in'):
            return Token(TokenType.OPERATOR, value.lower(), start)

        return Token(TokenType.IDENTIFIER, value, start)

    def _peek(self) -> str:
        """Peek next character."""
        if self.pos + 1 < self.length:
            return self.expression[self.pos + 1]
        return ''


# =============================================================================
# PARSER
# =============================================================================

class Parser:
    """Expression parser."""

    # Operator precedence (higher = tighter binding)
    PRECEDENCE = {
        'or': 1, '||': 1,
        'and': 2, '&&': 2,
        '|': 3,
        '^': 4,
        '&': 5,
        '==': 6, '!=': 6,
        '<': 7, '>': 7, '<=': 7, '>=': 7, 'in': 7,
        '<<': 8, '>>': 8,
        '+': 9, '-': 9,
        '*': 10, '/': 10, '%': 10,
        '**': 11,
        'not': 12, '!': 12, '~': 12, 'unary': 12
    }

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def parse(self) -> ASTNode:
        """Parse tokens into AST."""
        return self._parse_expression(0)

    def _parse_expression(self, min_precedence: int) -> ASTNode:
        """Parse expression with precedence climbing."""
        left = self._parse_unary()

        while True:
            token = self._current()

            if token.type != TokenType.OPERATOR:
                break

            precedence = self.PRECEDENCE.get(token.value, 0)
            if precedence < min_precedence:
                break

            # Ternary
            if token.type == TokenType.QUESTION:
                self._advance()
                if_true = self._parse_expression(0)
                self._expect(TokenType.COLON)
                if_false = self._parse_expression(0)
                left = TernaryNode(left, if_true, if_false)
                continue

            self._advance()
            right = self._parse_expression(precedence + 1)
            left = BinaryOpNode(token.value, left, right)

        # Check for ternary
        if self._current().type == TokenType.QUESTION:
            self._advance()
            if_true = self._parse_expression(0)
            self._expect(TokenType.COLON)
            if_false = self._parse_expression(0)
            left = TernaryNode(left, if_true, if_false)

        return left

    def _parse_unary(self) -> ASTNode:
        """Parse unary expression."""
        token = self._current()

        if token.type == TokenType.OPERATOR and token.value in ('-', '+', '!', 'not', '~'):
            self._advance()
            operand = self._parse_unary()
            return UnaryOpNode(token.value, operand)

        return self._parse_postfix()

    def _parse_postfix(self) -> ASTNode:
        """Parse postfix expressions (calls, indexing, member access)."""
        node = self._parse_primary()

        while True:
            token = self._current()

            if token.type == TokenType.LPAREN:
                # Function call
                if isinstance(node, IdentifierNode):
                    self._advance()
                    args = self._parse_arguments()
                    self._expect(TokenType.RPAREN)
                    node = FunctionCallNode(node.name, args)
                else:
                    break
            elif token.type == TokenType.LBRACKET:
                # Index access
                self._advance()
                index = self._parse_expression(0)
                self._expect(TokenType.RBRACKET)
                node = IndexNode(node, index)
            elif token.type == TokenType.DOT:
                # Member access
                self._advance()
                member_token = self._current()
                if member_token.type != TokenType.IDENTIFIER:
                    raise SyntaxError(f"Expected identifier after '.', got {member_token.type}")
                self._advance()
                node = MemberNode(node, member_token.value)
            else:
                break

        return node

    def _parse_primary(self) -> ASTNode:
        """Parse primary expression."""
        token = self._current()

        if token.type == TokenType.NUMBER:
            self._advance()
            return LiteralNode(token.value, DataType.NUMBER)

        elif token.type == TokenType.STRING:
            self._advance()
            return LiteralNode(token.value, DataType.STRING)

        elif token.type == TokenType.BOOLEAN:
            self._advance()
            return LiteralNode(token.value, DataType.BOOLEAN)

        elif token.type == TokenType.IDENTIFIER:
            self._advance()
            if token.value is None:
                return LiteralNode(None, DataType.NULL)
            return IdentifierNode(token.value)

        elif token.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expression(0)
            self._expect(TokenType.RPAREN)
            return expr

        elif token.type == TokenType.LBRACKET:
            self._advance()
            elements = self._parse_array_elements()
            self._expect(TokenType.RBRACKET)
            return ArrayNode(elements)

        raise SyntaxError(f"Unexpected token: {token.type} ({token.value})")

    def _parse_arguments(self) -> List[ASTNode]:
        """Parse function arguments."""
        args = []

        if self._current().type == TokenType.RPAREN:
            return args

        args.append(self._parse_expression(0))

        while self._current().type == TokenType.COMMA:
            self._advance()
            args.append(self._parse_expression(0))

        return args

    def _parse_array_elements(self) -> List[ASTNode]:
        """Parse array elements."""
        elements = []

        if self._current().type == TokenType.RBRACKET:
            return elements

        elements.append(self._parse_expression(0))

        while self._current().type == TokenType.COMMA:
            self._advance()
            elements.append(self._parse_expression(0))

        return elements

    def _current(self) -> Token:
        """Get current token."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, None, 0)

    def _advance(self) -> Token:
        """Advance to next token."""
        token = self._current()
        self.pos += 1
        return token

    def _expect(self, token_type: TokenType) -> Token:
        """Expect and consume token."""
        token = self._current()
        if token.type != token_type:
            raise SyntaxError(f"Expected {token_type}, got {token.type}")
        self._advance()
        return token


# =============================================================================
# EVALUATOR
# =============================================================================

class Evaluator(ASTVisitor):
    """Expression evaluator."""

    BINARY_OPS = {
        '+': lambda a, b: a + b,
        '-': lambda a, b: a - b,
        '*': lambda a, b: a * b,
        '/': lambda a, b: a / b if b != 0 else float('inf'),
        '%': lambda a, b: a % b if b != 0 else 0,
        '**': lambda a, b: a ** b,
        '^': lambda a, b: a ^ b if isinstance(a, int) and isinstance(b, int) else a ** b,
        '==': lambda a, b: a == b,
        '!=': lambda a, b: a != b,
        '<': lambda a, b: a < b,
        '>': lambda a, b: a > b,
        '<=': lambda a, b: a <= b,
        '>=': lambda a, b: a >= b,
        'and': lambda a, b: a and b,
        '&&': lambda a, b: a and b,
        'or': lambda a, b: a or b,
        '||': lambda a, b: a or b,
        '&': lambda a, b: int(a) & int(b),
        '|': lambda a, b: int(a) | int(b),
        '<<': lambda a, b: int(a) << int(b),
        '>>': lambda a, b: int(a) >> int(b),
        'in': lambda a, b: a in b,
    }

    UNARY_OPS = {
        '-': lambda a: -a,
        '+': lambda a: +a,
        '!': lambda a: not a,
        'not': lambda a: not a,
        '~': lambda a: ~int(a),
    }

    def __init__(self, variables: Optional[Dict[str, Any]] = None, functions: Optional[Dict[str, Callable]] = None):
        self.variables = variables or {}
        self.functions = self._default_functions()
        if functions:
            self.functions.update(functions)

    def _default_functions(self) -> Dict[str, Callable]:
        """Get default functions."""
        return {
            # Math
            'abs': abs,
            'round': round,
            'floor': math.floor,
            'ceil': math.ceil,
            'sqrt': math.sqrt,
            'pow': pow,
            'log': math.log,
            'log10': math.log10,
            'log2': math.log2,
            'exp': math.exp,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'asin': math.asin,
            'acos': math.acos,
            'atan': math.atan,
            'atan2': math.atan2,
            'sinh': math.sinh,
            'cosh': math.cosh,
            'tanh': math.tanh,
            'degrees': math.degrees,
            'radians': math.radians,
            'min': min,
            'max': max,
            'sum': sum,
            'avg': lambda *args: sum(args) / len(args) if args else 0,

            # Type conversion
            'int': int,
            'float': float,
            'str': str,
            'bool': bool,

            # String functions
            'len': len,
            'upper': lambda s: s.upper(),
            'lower': lambda s: s.lower(),
            'strip': lambda s: s.strip(),
            'split': lambda s, sep=' ': s.split(sep),
            'join': lambda sep, arr: sep.join(str(x) for x in arr),
            'replace': lambda s, old, new: s.replace(old, new),
            'startswith': lambda s, prefix: s.startswith(prefix),
            'endswith': lambda s, suffix: s.endswith(suffix),
            'contains': lambda s, sub: sub in s,
            'substr': lambda s, start, end=None: s[start:end],

            # Array functions
            'range': lambda *args: list(range(*args)),
            'reverse': lambda arr: list(reversed(arr)),
            'sort': lambda arr: sorted(arr),
            'unique': lambda arr: list(set(arr)),
            'first': lambda arr: arr[0] if arr else None,
            'last': lambda arr: arr[-1] if arr else None,
            'head': lambda arr, n=1: arr[:n],
            'tail': lambda arr, n=1: arr[-n:],
            'slice': lambda arr, start, end=None: arr[start:end],
            'concat': lambda *arrs: sum([list(a) for a in arrs], []),
            'flatten': lambda arr: [x for sub in arr for x in (sub if isinstance(sub, list) else [sub])],
            'filter': lambda func, arr: list(filter(func, arr)) if callable(func) else [x for x in arr if x],
            'map': lambda func, arr: list(map(func, arr)),

            # Conditional
            'if': lambda cond, if_true, if_false: if_true if cond else if_false,
            'coalesce': lambda *args: next((a for a in args if a is not None), None),

            # Type checking
            'typeof': lambda x: type(x).__name__,
            'isnumber': lambda x: isinstance(x, (int, float)),
            'isstring': lambda x: isinstance(x, str),
            'isarray': lambda x: isinstance(x, list),
            'isnull': lambda x: x is None,

            # Constants
            'pi': lambda: math.pi,
            'e': lambda: math.e,
            'inf': lambda: float('inf'),
            'nan': lambda: float('nan'),
        }

    def evaluate(self, node: ASTNode) -> Any:
        """Evaluate AST node."""
        return node.accept(self)

    def visit_literal(self, node: LiteralNode) -> Any:
        return node.value

    def visit_identifier(self, node: IdentifierNode) -> Any:
        if node.name in self.variables:
            return self.variables[node.name]

        # Check if it's a zero-arg function being used as constant
        if node.name in self.functions:
            func = self.functions[node.name]
            try:
                import inspect
                sig = inspect.signature(func)
                if len(sig.parameters) == 0:
                    return func()
            except:
                pass

        raise NameError(f"Undefined variable: {node.name}")

    def visit_binary_op(self, node: BinaryOpNode) -> Any:
        # Short-circuit for logical operators
        if node.operator in ('and', '&&'):
            left = self.evaluate(node.left)
            if not left:
                return left
            return self.evaluate(node.right)

        if node.operator in ('or', '||'):
            left = self.evaluate(node.left)
            if left:
                return left
            return self.evaluate(node.right)

        left = self.evaluate(node.left)
        right = self.evaluate(node.right)

        if node.operator in self.BINARY_OPS:
            return self.BINARY_OPS[node.operator](left, right)

        raise ValueError(f"Unknown operator: {node.operator}")

    def visit_unary_op(self, node: UnaryOpNode) -> Any:
        operand = self.evaluate(node.operand)

        if node.operator in self.UNARY_OPS:
            return self.UNARY_OPS[node.operator](operand)

        raise ValueError(f"Unknown unary operator: {node.operator}")

    def visit_function_call(self, node: FunctionCallNode) -> Any:
        if node.name not in self.functions:
            raise NameError(f"Undefined function: {node.name}")

        func = self.functions[node.name]
        args = [self.evaluate(arg) for arg in node.arguments]

        return func(*args)

    def visit_array(self, node: ArrayNode) -> Any:
        return [self.evaluate(elem) for elem in node.elements]

    def visit_index(self, node: IndexNode) -> Any:
        obj = self.evaluate(node.object)
        index = self.evaluate(node.index)

        if isinstance(obj, dict):
            return obj.get(index)

        return obj[int(index)]

    def visit_member(self, node: MemberNode) -> Any:
        obj = self.evaluate(node.object)

        if isinstance(obj, dict):
            return obj.get(node.member)

        if hasattr(obj, node.member):
            return getattr(obj, node.member)

        raise AttributeError(f"No such member: {node.member}")

    def visit_ternary(self, node: TernaryNode) -> Any:
        condition = self.evaluate(node.condition)

        if condition:
            return self.evaluate(node.if_true)
        else:
            return self.evaluate(node.if_false)


# =============================================================================
# COMPILED EXPRESSION
# =============================================================================

class CompiledExpression:
    """Compiled expression for repeated evaluation."""

    def __init__(self, expression: str, ast: ASTNode):
        self.expression = expression
        self.ast = ast
        self._variables: Set[str] = set()
        self._functions: Set[str] = set()
        self._collect_references(ast)

    def _collect_references(self, node: ASTNode) -> None:
        """Collect variable and function references."""
        if isinstance(node, IdentifierNode):
            self._variables.add(node.name)
        elif isinstance(node, FunctionCallNode):
            self._functions.add(node.name)
            for arg in node.arguments:
                self._collect_references(arg)
        elif isinstance(node, BinaryOpNode):
            self._collect_references(node.left)
            self._collect_references(node.right)
        elif isinstance(node, UnaryOpNode):
            self._collect_references(node.operand)
        elif isinstance(node, ArrayNode):
            for elem in node.elements:
                self._collect_references(elem)
        elif isinstance(node, IndexNode):
            self._collect_references(node.object)
            self._collect_references(node.index)
        elif isinstance(node, MemberNode):
            self._collect_references(node.object)
        elif isinstance(node, TernaryNode):
            self._collect_references(node.condition)
            self._collect_references(node.if_true)
            self._collect_references(node.if_false)

    @property
    def variables(self) -> Set[str]:
        return self._variables

    @property
    def functions(self) -> Set[str]:
        return self._functions

    def evaluate(
        self,
        variables: Optional[Dict[str, Any]] = None,
        functions: Optional[Dict[str, Callable]] = None
    ) -> Any:
        """Evaluate expression."""
        evaluator = Evaluator(variables, functions)
        return evaluator.evaluate(self.ast)


# =============================================================================
# EXPRESSION EVALUATOR
# =============================================================================

class ExpressionEvaluator:
    """
    Master Expression Evaluator for BAEL.

    Provides comprehensive expression evaluation with caching.
    """

    def __init__(self):
        self._cache: Dict[str, CompiledExpression] = {}
        self._global_variables: Dict[str, Any] = {}
        self._global_functions: Dict[str, Callable] = {}
        self._max_cache_size = 1000

    # -------------------------------------------------------------------------
    # COMPILATION
    # -------------------------------------------------------------------------

    def compile(self, expression: str) -> CompiledExpression:
        """Compile an expression."""
        if expression in self._cache:
            return self._cache[expression]

        lexer = Lexer(expression)
        tokens = lexer.tokenize()

        parser = Parser(tokens)
        ast = parser.parse()

        compiled = CompiledExpression(expression, ast)

        # Cache management
        if len(self._cache) >= self._max_cache_size:
            # Remove oldest entries
            oldest = list(self._cache.keys())[:100]
            for key in oldest:
                del self._cache[key]

        self._cache[expression] = compiled
        return compiled

    # -------------------------------------------------------------------------
    # EVALUATION
    # -------------------------------------------------------------------------

    def evaluate(
        self,
        expression: str,
        variables: Optional[Dict[str, Any]] = None,
        functions: Optional[Dict[str, Callable]] = None
    ) -> EvalResult:
        """Evaluate an expression."""
        start = datetime.now()

        try:
            compiled = self.compile(expression)

            # Merge globals with locals
            merged_vars = {**self._global_variables}
            if variables:
                merged_vars.update(variables)

            merged_funcs = {**self._global_functions}
            if functions:
                merged_funcs.update(functions)

            value = compiled.evaluate(merged_vars, merged_funcs)

            return EvalResult(
                value=value,
                type=self._get_type(value),
                success=True,
                execution_time=(datetime.now() - start).total_seconds()
            )

        except Exception as e:
            return EvalResult(
                value=None,
                type=DataType.NULL,
                success=False,
                error=str(e),
                execution_time=(datetime.now() - start).total_seconds()
            )

    def eval(
        self,
        expression: str,
        variables: Optional[Dict[str, Any]] = None,
        functions: Optional[Dict[str, Callable]] = None
    ) -> Any:
        """Evaluate expression and return value directly."""
        result = self.evaluate(expression, variables, functions)

        if not result.success:
            raise ValueError(result.error)

        return result.value

    # -------------------------------------------------------------------------
    # GLOBALS
    # -------------------------------------------------------------------------

    def set_variable(self, name: str, value: Any) -> None:
        """Set a global variable."""
        self._global_variables[name] = value

    def get_variable(self, name: str) -> Any:
        """Get a global variable."""
        return self._global_variables.get(name)

    def set_function(self, name: str, func: Callable) -> None:
        """Set a global function."""
        self._global_functions[name] = func

    def clear_globals(self) -> None:
        """Clear all global variables and functions."""
        self._global_variables.clear()
        self._global_functions.clear()

    # -------------------------------------------------------------------------
    # VALIDATION
    # -------------------------------------------------------------------------

    def is_valid(self, expression: str) -> bool:
        """Check if expression is valid."""
        try:
            self.compile(expression)
            return True
        except:
            return False

    def get_info(self, expression: str) -> ExpressionInfo:
        """Get expression information."""
        start = datetime.now()

        try:
            compiled = self.compile(expression)

            # Collect operators
            operators = set()
            self._collect_operators(compiled.ast, operators)

            return ExpressionInfo(
                expression=expression,
                variables=compiled.variables,
                functions=compiled.functions,
                operators=operators,
                is_valid=True,
                parse_time=(datetime.now() - start).total_seconds()
            )

        except Exception:
            return ExpressionInfo(
                expression=expression,
                variables=set(),
                functions=set(),
                operators=set(),
                is_valid=False,
                parse_time=(datetime.now() - start).total_seconds()
            )

    def _collect_operators(self, node: ASTNode, operators: Set[str]) -> None:
        """Collect operators from AST."""
        if isinstance(node, BinaryOpNode):
            operators.add(node.operator)
            self._collect_operators(node.left, operators)
            self._collect_operators(node.right, operators)
        elif isinstance(node, UnaryOpNode):
            operators.add(node.operator)
            self._collect_operators(node.operand, operators)
        elif isinstance(node, FunctionCallNode):
            for arg in node.arguments:
                self._collect_operators(arg, operators)
        elif isinstance(node, ArrayNode):
            for elem in node.elements:
                self._collect_operators(elem, operators)
        elif isinstance(node, IndexNode):
            self._collect_operators(node.object, operators)
            self._collect_operators(node.index, operators)
        elif isinstance(node, TernaryNode):
            self._collect_operators(node.condition, operators)
            self._collect_operators(node.if_true, operators)
            self._collect_operators(node.if_false, operators)

    def _get_type(self, value: Any) -> DataType:
        """Get data type of value."""
        if value is None:
            return DataType.NULL
        elif isinstance(value, bool):
            return DataType.BOOLEAN
        elif isinstance(value, (int, float)):
            return DataType.NUMBER
        elif isinstance(value, str):
            return DataType.STRING
        elif isinstance(value, (list, tuple)):
            return DataType.ARRAY
        elif isinstance(value, dict):
            return DataType.OBJECT
        else:
            return DataType.OBJECT

    # -------------------------------------------------------------------------
    # CACHE
    # -------------------------------------------------------------------------

    def clear_cache(self) -> None:
        """Clear expression cache."""
        self._cache.clear()

    @property
    def cache_size(self) -> int:
        """Get cache size."""
        return len(self._cache)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Expression Evaluator."""
    print("=" * 70)
    print("BAEL - EXPRESSION EVALUATOR DEMO")
    print("Comprehensive Mathematical and Logical Expression System")
    print("=" * 70)
    print()

    evaluator = ExpressionEvaluator()

    # 1. Basic Arithmetic
    print("1. BASIC ARITHMETIC:")
    print("-" * 40)

    expressions = [
        "2 + 3 * 4",
        "(2 + 3) * 4",
        "10 / 3",
        "10 % 3",
        "2 ** 10",
    ]

    for expr in expressions:
        result = evaluator.eval(expr)
        print(f"   {expr} = {result}")
    print()

    # 2. Comparison Operations
    print("2. COMPARISON OPERATIONS:")
    print("-" * 40)

    expressions = [
        "5 > 3",
        "5 == 5",
        "10 <= 10",
        "3 != 4",
    ]

    for expr in expressions:
        result = evaluator.eval(expr)
        print(f"   {expr} = {result}")
    print()

    # 3. Logical Operations
    print("3. LOGICAL OPERATIONS:")
    print("-" * 40)

    expressions = [
        "true and false",
        "true or false",
        "not false",
        "(5 > 3) && (2 < 4)",
    ]

    for expr in expressions:
        result = evaluator.eval(expr)
        print(f"   {expr} = {result}")
    print()

    # 4. Variables
    print("4. VARIABLES:")
    print("-" * 40)

    variables = {"x": 10, "y": 5, "name": "BAEL"}

    expressions = [
        "x + y",
        "x * y - 10",
        "x > y",
    ]

    for expr in expressions:
        result = evaluator.eval(expr, variables)
        print(f"   {expr} = {result} (x=10, y=5)")
    print()

    # 5. Math Functions
    print("5. MATH FUNCTIONS:")
    print("-" * 40)

    expressions = [
        "sqrt(16)",
        "sin(pi() / 2)",
        "round(3.14159, 2)",
        "abs(-42)",
        "log10(100)",
        "max(1, 5, 3, 9, 2)",
    ]

    for expr in expressions:
        result = evaluator.eval(expr)
        print(f"   {expr} = {result}")
    print()

    # 6. String Operations
    print("6. STRING OPERATIONS:")
    print("-" * 40)

    variables = {"text": "Hello, BAEL!"}

    expressions = [
        'upper("hello")',
        'len(text)',
        'contains(text, "BAEL")',
        'replace(text, "BAEL", "World")',
    ]

    for expr in expressions:
        result = evaluator.eval(expr, variables)
        print(f"   {expr} = {result}")
    print()

    # 7. Array Operations
    print("7. ARRAY OPERATIONS:")
    print("-" * 40)

    variables = {"arr": [3, 1, 4, 1, 5, 9, 2, 6]}

    expressions = [
        "[1, 2, 3, 4, 5]",
        "arr[0]",
        "len(arr)",
        "sum(arr)",
        "max(arr)",
        "sort(arr)",
        "unique(arr)",
    ]

    for expr in expressions:
        result = evaluator.eval(expr, variables)
        print(f"   {expr} = {result}")
    print()

    # 8. Ternary Operator
    print("8. TERNARY OPERATOR:")
    print("-" * 40)

    expressions = [
        "5 > 3 ? 'yes' : 'no'",
        "10 < 5 ? 'less' : 'greater'",
    ]

    for expr in expressions:
        result = evaluator.eval(expr)
        print(f"   {expr} = {result}")
    print()

    # 9. Complex Expressions
    print("9. COMPLEX EXPRESSIONS:")
    print("-" * 40)

    variables = {"data": [1, 2, 3, 4, 5]}

    expressions = [
        "sqrt(pow(3, 2) + pow(4, 2))",
        "sum(data) / len(data)",
        "if(sum(data) > 10, 'large', 'small')",
    ]

    for expr in expressions:
        result = evaluator.eval(expr, variables)
        print(f"   {expr} = {result}")
    print()

    # 10. Custom Functions
    print("10. CUSTOM FUNCTIONS:")
    print("-" * 40)

    custom_funcs = {
        'double': lambda x: x * 2,
        'triple': lambda x: x * 3,
        'greet': lambda name: f"Hello, {name}!",
    }

    expressions = [
        "double(21)",
        "triple(14)",
        'greet("BAEL")',
    ]

    for expr in expressions:
        result = evaluator.eval(expr, functions=custom_funcs)
        print(f"   {expr} = {result}")
    print()

    # 11. Global Variables
    print("11. GLOBAL VARIABLES:")
    print("-" * 40)

    evaluator.set_variable("PI", 3.14159)
    evaluator.set_variable("E", 2.71828)

    expressions = [
        "PI * 2",
        "E ** 2",
    ]

    for expr in expressions:
        result = evaluator.eval(expr)
        print(f"   {expr} = {result}")
    print()

    # 12. Expression Info
    print("12. EXPRESSION INFO:")
    print("-" * 40)

    expr = "sqrt(x ** 2 + y ** 2) > threshold"
    info = evaluator.get_info(expr)

    print(f"   Expression: {info.expression}")
    print(f"   Variables: {info.variables}")
    print(f"   Functions: {info.functions}")
    print(f"   Operators: {info.operators}")
    print(f"   Is valid: {info.is_valid}")
    print()

    # 13. Validation
    print("13. VALIDATION:")
    print("-" * 40)

    test_expressions = [
        "2 + 2",
        "sqrt(16)",
        "((invalid",
        "1 + * 2",
    ]

    for expr in test_expressions:
        is_valid = evaluator.is_valid(expr)
        print(f"   '{expr}' - Valid: {is_valid}")
    print()

    # 14. Error Handling
    print("14. ERROR HANDLING:")
    print("-" * 40)

    result = evaluator.evaluate("undefined_var + 10")
    print(f"   Expression: 'undefined_var + 10'")
    print(f"   Success: {result.success}")
    print(f"   Error: {result.error}")
    print()

    # 15. Performance
    print("15. PERFORMANCE:")
    print("-" * 40)

    expr = "sqrt(pow(x, 2) + pow(y, 2)) * 100"

    # Compile once
    compiled = evaluator.compile(expr)
    print(f"   Compiled expression cached")
    print(f"   Cache size: {evaluator.cache_size}")

    # Evaluate multiple times
    import time
    start = time.time()
    for i in range(10000):
        compiled.evaluate({"x": i % 100, "y": i % 50})
    elapsed = time.time() - start

    print(f"   10,000 evaluations in {elapsed:.4f}s")
    print(f"   Rate: {10000/elapsed:.0f} eval/sec")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Expression Evaluator Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
