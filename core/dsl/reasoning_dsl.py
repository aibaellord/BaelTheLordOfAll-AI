"""
BAEL - Domain Specific Language (DSL) for Reasoning Rules
Custom language for defining reasoning patterns and rules.

Features:
- Rule definition DSL
- Pattern matching expressions
- Logical operators (AND, OR, NOT, IMPLIES)
- Quantifiers (FORALL, EXISTS)
- Temporal operators (ALWAYS, EVENTUALLY, UNTIL)
- Rule compilation and optimization
- Runtime evaluation engine
"""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("BAEL.DSL")


# =============================================================================
# ENUMS
# =============================================================================

class TokenType(Enum):
    """Token types in DSL."""
    # Literals
    IDENTIFIER = auto()
    STRING = auto()
    NUMBER = auto()
    BOOLEAN = auto()

    # Operators
    AND = auto()
    OR = auto()
    NOT = auto()
    IMPLIES = auto()
    IFF = auto()

    # Quantifiers
    FORALL = auto()
    EXISTS = auto()

    # Temporal
    ALWAYS = auto()
    EVENTUALLY = auto()
    UNTIL = auto()
    NEXT = auto()

    # Comparison
    EQ = auto()
    NE = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()

    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LBRACE = auto()
    RBRACE = auto()
    COMMA = auto()
    DOT = auto()
    COLON = auto()
    ARROW = auto()

    # Keywords
    RULE = auto()
    IF = auto()
    THEN = auto()
    WHEN = auto()
    WITH = auto()
    PRIORITY = auto()

    # Special
    EOF = auto()
    NEWLINE = auto()


class Operator(Enum):
    """Operators for expressions."""
    AND = "and"
    OR = "or"
    NOT = "not"
    IMPLIES = "implies"
    IFF = "iff"
    EQ = "=="
    NE = "!="
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="
    FORALL = "forall"
    EXISTS = "exists"
    ALWAYS = "always"
    EVENTUALLY = "eventually"
    UNTIL = "until"


# =============================================================================
# TOKEN & LEXER
# =============================================================================

@dataclass
class Token:
    """A token in the DSL."""
    type: TokenType
    value: Any
    line: int = 0
    column: int = 0


class Lexer:
    """Tokenizer for DSL."""

    KEYWORDS = {
        "and": TokenType.AND,
        "or": TokenType.OR,
        "not": TokenType.NOT,
        "implies": TokenType.IMPLIES,
        "iff": TokenType.IFF,
        "forall": TokenType.FORALL,
        "exists": TokenType.EXISTS,
        "always": TokenType.ALWAYS,
        "eventually": TokenType.EVENTUALLY,
        "until": TokenType.UNTIL,
        "next": TokenType.NEXT,
        "rule": TokenType.RULE,
        "if": TokenType.IF,
        "then": TokenType.THEN,
        "when": TokenType.WHEN,
        "with": TokenType.WITH,
        "priority": TokenType.PRIORITY,
        "true": TokenType.BOOLEAN,
        "false": TokenType.BOOLEAN,
    }

    OPERATORS = {
        "==": TokenType.EQ,
        "!=": TokenType.NE,
        "<=": TokenType.LE,
        ">=": TokenType.GE,
        "<": TokenType.LT,
        ">": TokenType.GT,
        "->": TokenType.ARROW,
    }

    DELIMITERS = {
        "(": TokenType.LPAREN,
        ")": TokenType.RPAREN,
        "[": TokenType.LBRACKET,
        "]": TokenType.RBRACKET,
        "{": TokenType.LBRACE,
        "}": TokenType.RBRACE,
        ",": TokenType.COMMA,
        ".": TokenType.DOT,
        ":": TokenType.COLON,
    }

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

    def tokenize(self) -> List[Token]:
        """Tokenize the source."""
        while self.pos < len(self.source):
            self._skip_whitespace()
            if self.pos >= len(self.source):
                break

            char = self.source[self.pos]

            # Comments
            if char == '#':
                self._skip_comment()
                continue

            # Newlines
            if char == '\n':
                self.tokens.append(Token(TokenType.NEWLINE, '\n', self.line, self.column))
                self.line += 1
                self.column = 1
                self.pos += 1
                continue

            # String literals
            if char in '"\'':
                self.tokens.append(self._read_string())
                continue

            # Numbers
            if char.isdigit() or (char == '-' and self.pos + 1 < len(self.source) and self.source[self.pos + 1].isdigit()):
                self.tokens.append(self._read_number())
                continue

            # Two-character operators
            if self.pos + 1 < len(self.source):
                two_char = self.source[self.pos:self.pos + 2]
                if two_char in self.OPERATORS:
                    self.tokens.append(Token(self.OPERATORS[two_char], two_char, self.line, self.column))
                    self.pos += 2
                    self.column += 2
                    continue

            # Single-character operators/delimiters
            if char in self.DELIMITERS:
                self.tokens.append(Token(self.DELIMITERS[char], char, self.line, self.column))
                self.pos += 1
                self.column += 1
                continue

            if char in '<>':
                self.tokens.append(Token(self.OPERATORS[char], char, self.line, self.column))
                self.pos += 1
                self.column += 1
                continue

            # Identifiers and keywords
            if char.isalpha() or char == '_':
                self.tokens.append(self._read_identifier())
                continue

            # Unknown character
            raise SyntaxError(f"Unexpected character '{char}' at line {self.line}, column {self.column}")

        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return self.tokens

    def _skip_whitespace(self) -> None:
        """Skip whitespace except newlines."""
        while self.pos < len(self.source) and self.source[self.pos] in ' \t\r':
            self.pos += 1
            self.column += 1

    def _skip_comment(self) -> None:
        """Skip comment until end of line."""
        while self.pos < len(self.source) and self.source[self.pos] != '\n':
            self.pos += 1

    def _read_string(self) -> Token:
        """Read string literal."""
        quote = self.source[self.pos]
        start_col = self.column
        self.pos += 1
        self.column += 1

        value = ""
        while self.pos < len(self.source) and self.source[self.pos] != quote:
            if self.source[self.pos] == '\\' and self.pos + 1 < len(self.source):
                self.pos += 1
                self.column += 1
                escape_char = self.source[self.pos]
                value += {'n': '\n', 't': '\t', 'r': '\r'}.get(escape_char, escape_char)
            else:
                value += self.source[self.pos]
            self.pos += 1
            self.column += 1

        self.pos += 1  # Skip closing quote
        self.column += 1
        return Token(TokenType.STRING, value, self.line, start_col)

    def _read_number(self) -> Token:
        """Read number literal."""
        start = self.pos
        start_col = self.column

        if self.source[self.pos] == '-':
            self.pos += 1
            self.column += 1

        while self.pos < len(self.source) and (self.source[self.pos].isdigit() or self.source[self.pos] == '.'):
            self.pos += 1
            self.column += 1

        value = self.source[start:self.pos]
        return Token(TokenType.NUMBER, float(value) if '.' in value else int(value), self.line, start_col)

    def _read_identifier(self) -> Token:
        """Read identifier or keyword."""
        start = self.pos
        start_col = self.column

        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == '_'):
            self.pos += 1
            self.column += 1

        value = self.source[start:self.pos]

        if value.lower() in self.KEYWORDS:
            token_type = self.KEYWORDS[value.lower()]
            if token_type == TokenType.BOOLEAN:
                return Token(token_type, value.lower() == 'true', self.line, start_col)
            return Token(token_type, value.lower(), self.line, start_col)

        return Token(TokenType.IDENTIFIER, value, self.line, start_col)


# =============================================================================
# AST NODES
# =============================================================================

class ASTNode(ABC):
    """Base class for AST nodes."""

    @abstractmethod
    def evaluate(self, context: Dict[str, Any]) -> Any:
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        pass


@dataclass
class LiteralNode(ASTNode):
    """Literal value node."""
    value: Any

    def evaluate(self, context: Dict[str, Any]) -> Any:
        return self.value

    def to_dict(self) -> Dict[str, Any]:
        return {"type": "literal", "value": self.value}


@dataclass
class IdentifierNode(ASTNode):
    """Variable/identifier reference."""
    name: str

    def evaluate(self, context: Dict[str, Any]) -> Any:
        parts = self.name.split('.')
        value = context
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None
        return value

    def to_dict(self) -> Dict[str, Any]:
        return {"type": "identifier", "name": self.name}


@dataclass
class BinaryOpNode(ASTNode):
    """Binary operation node."""
    operator: Operator
    left: ASTNode
    right: ASTNode

    def evaluate(self, context: Dict[str, Any]) -> Any:
        left_val = self.left.evaluate(context)

        # Short-circuit for AND/OR
        if self.operator == Operator.AND:
            return left_val and self.right.evaluate(context)
        if self.operator == Operator.OR:
            return left_val or self.right.evaluate(context)

        right_val = self.right.evaluate(context)

        if self.operator == Operator.EQ:
            return left_val == right_val
        if self.operator == Operator.NE:
            return left_val != right_val
        if self.operator == Operator.LT:
            return left_val < right_val
        if self.operator == Operator.LE:
            return left_val <= right_val
        if self.operator == Operator.GT:
            return left_val > right_val
        if self.operator == Operator.GE:
            return left_val >= right_val
        if self.operator == Operator.IMPLIES:
            return (not left_val) or right_val
        if self.operator == Operator.IFF:
            return left_val == right_val

        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "binary_op",
            "operator": self.operator.value,
            "left": self.left.to_dict(),
            "right": self.right.to_dict()
        }


@dataclass
class UnaryOpNode(ASTNode):
    """Unary operation node."""
    operator: Operator
    operand: ASTNode

    def evaluate(self, context: Dict[str, Any]) -> Any:
        val = self.operand.evaluate(context)
        if self.operator == Operator.NOT:
            return not val
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "unary_op",
            "operator": self.operator.value,
            "operand": self.operand.to_dict()
        }


@dataclass
class QuantifierNode(ASTNode):
    """Quantifier node (forall, exists)."""
    quantifier: Operator
    variable: str
    domain: ASTNode
    body: ASTNode

    def evaluate(self, context: Dict[str, Any]) -> Any:
        domain_val = self.domain.evaluate(context)
        if not hasattr(domain_val, '__iter__'):
            return False

        if self.quantifier == Operator.FORALL:
            for item in domain_val:
                local_context = {**context, self.variable: item}
                if not self.body.evaluate(local_context):
                    return False
            return True

        elif self.quantifier == Operator.EXISTS:
            for item in domain_val:
                local_context = {**context, self.variable: item}
                if self.body.evaluate(local_context):
                    return True
            return False

        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "quantifier",
            "quantifier": self.quantifier.value,
            "variable": self.variable,
            "domain": self.domain.to_dict(),
            "body": self.body.to_dict()
        }


@dataclass
class FunctionCallNode(ASTNode):
    """Function call node."""
    name: str
    arguments: List[ASTNode]

    def evaluate(self, context: Dict[str, Any]) -> Any:
        func = context.get(f"_fn_{self.name}") or context.get(self.name)
        if callable(func):
            args = [arg.evaluate(context) for arg in self.arguments]
            return func(*args)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "function_call",
            "name": self.name,
            "arguments": [arg.to_dict() for arg in self.arguments]
        }


# =============================================================================
# RULE
# =============================================================================

@dataclass
class Rule:
    """A reasoning rule."""
    name: str
    condition: ASTNode
    action: ASTNode
    priority: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def matches(self, context: Dict[str, Any]) -> bool:
        """Check if rule condition matches."""
        try:
            return bool(self.condition.evaluate(context))
        except Exception as e:
            logger.error(f"Rule {self.name} evaluation error: {e}")
            return False

    def execute(self, context: Dict[str, Any]) -> Any:
        """Execute rule action."""
        try:
            return self.action.evaluate(context)
        except Exception as e:
            logger.error(f"Rule {self.name} execution error: {e}")
            return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "condition": self.condition.to_dict(),
            "action": self.action.to_dict(),
            "priority": self.priority,
            "enabled": self.enabled,
            "metadata": self.metadata
        }


# =============================================================================
# PARSER
# =============================================================================

class Parser:
    """Parser for DSL."""

    def __init__(self, tokens: List[Token]):
        self.tokens = [t for t in tokens if t.type != TokenType.NEWLINE]
        self.pos = 0

    @property
    def current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, None)

    def advance(self) -> Token:
        token = self.current
        self.pos += 1
        return token

    def expect(self, token_type: TokenType) -> Token:
        if self.current.type != token_type:
            raise SyntaxError(f"Expected {token_type}, got {self.current.type} at line {self.current.line}")
        return self.advance()

    def match(self, *token_types: TokenType) -> bool:
        return self.current.type in token_types

    def parse_rules(self) -> List[Rule]:
        """Parse multiple rules."""
        rules = []
        while not self.match(TokenType.EOF):
            if self.match(TokenType.RULE):
                rules.append(self.parse_rule())
            else:
                self.advance()  # Skip unknown tokens
        return rules

    def parse_rule(self) -> Rule:
        """Parse a single rule."""
        self.expect(TokenType.RULE)

        name = self.expect(TokenType.IDENTIFIER).value

        # Optional priority
        priority = 0
        if self.match(TokenType.WITH):
            self.advance()
            self.expect(TokenType.PRIORITY)
            priority = int(self.expect(TokenType.NUMBER).value)

        self.expect(TokenType.COLON)

        # Condition
        self.expect(TokenType.IF)
        condition = self.parse_expression()

        # Action
        self.expect(TokenType.THEN)
        action = self.parse_expression()

        return Rule(
            name=name,
            condition=condition,
            action=action,
            priority=priority
        )

    def parse_expression(self) -> ASTNode:
        """Parse expression (handles implies/iff)."""
        left = self.parse_or()

        while self.match(TokenType.IMPLIES, TokenType.IFF):
            op = Operator.IMPLIES if self.current.type == TokenType.IMPLIES else Operator.IFF
            self.advance()
            right = self.parse_or()
            left = BinaryOpNode(op, left, right)

        return left

    def parse_or(self) -> ASTNode:
        """Parse OR expression."""
        left = self.parse_and()

        while self.match(TokenType.OR):
            self.advance()
            right = self.parse_and()
            left = BinaryOpNode(Operator.OR, left, right)

        return left

    def parse_and(self) -> ASTNode:
        """Parse AND expression."""
        left = self.parse_not()

        while self.match(TokenType.AND):
            self.advance()
            right = self.parse_not()
            left = BinaryOpNode(Operator.AND, left, right)

        return left

    def parse_not(self) -> ASTNode:
        """Parse NOT expression."""
        if self.match(TokenType.NOT):
            self.advance()
            operand = self.parse_not()
            return UnaryOpNode(Operator.NOT, operand)
        return self.parse_comparison()

    def parse_comparison(self) -> ASTNode:
        """Parse comparison expression."""
        left = self.parse_quantifier()

        if self.match(TokenType.EQ, TokenType.NE, TokenType.LT, TokenType.LE, TokenType.GT, TokenType.GE):
            op_map = {
                TokenType.EQ: Operator.EQ,
                TokenType.NE: Operator.NE,
                TokenType.LT: Operator.LT,
                TokenType.LE: Operator.LE,
                TokenType.GT: Operator.GT,
                TokenType.GE: Operator.GE,
            }
            op = op_map[self.current.type]
            self.advance()
            right = self.parse_quantifier()
            return BinaryOpNode(op, left, right)

        return left

    def parse_quantifier(self) -> ASTNode:
        """Parse quantifier expression."""
        if self.match(TokenType.FORALL, TokenType.EXISTS):
            quantifier = Operator.FORALL if self.current.type == TokenType.FORALL else Operator.EXISTS
            self.advance()
            variable = self.expect(TokenType.IDENTIFIER).value

            # Parse domain (in brackets)
            self.expect(TokenType.LBRACKET)
            domain = self.parse_expression()
            self.expect(TokenType.RBRACKET)

            # Parse body
            self.expect(TokenType.COLON)
            body = self.parse_expression()

            return QuantifierNode(quantifier, variable, domain, body)

        return self.parse_primary()

    def parse_primary(self) -> ASTNode:
        """Parse primary expression."""
        if self.match(TokenType.LPAREN):
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr

        if self.match(TokenType.NUMBER):
            return LiteralNode(self.advance().value)

        if self.match(TokenType.STRING):
            return LiteralNode(self.advance().value)

        if self.match(TokenType.BOOLEAN):
            return LiteralNode(self.advance().value)

        if self.match(TokenType.IDENTIFIER):
            name = self.advance().value

            # Handle dotted names
            while self.match(TokenType.DOT):
                self.advance()
                name += "." + self.expect(TokenType.IDENTIFIER).value

            # Check for function call
            if self.match(TokenType.LPAREN):
                self.advance()
                args = []
                while not self.match(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    if self.match(TokenType.COMMA):
                        self.advance()
                self.expect(TokenType.RPAREN)
                return FunctionCallNode(name, args)

            return IdentifierNode(name)

        raise SyntaxError(f"Unexpected token {self.current.type} at line {self.current.line}")


# =============================================================================
# RULE ENGINE
# =============================================================================

class RuleEngine:
    """
    Rule evaluation engine for BAEL.

    Executes rules based on context and priorities.
    """

    def __init__(self):
        self.rules: Dict[str, Rule] = {}
        self.functions: Dict[str, Callable] = {}
        self.execution_history: List[Tuple[str, datetime, Any]] = []

        # Register built-in functions
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register built-in functions."""
        self.register_function("len", len)
        self.register_function("abs", abs)
        self.register_function("min", min)
        self.register_function("max", max)
        self.register_function("sum", sum)
        self.register_function("all", all)
        self.register_function("any", any)
        self.register_function("str", str)
        self.register_function("int", int)
        self.register_function("float", float)
        self.register_function("bool", bool)
        self.register_function("isinstance", isinstance)
        self.register_function("contains", lambda x, y: y in x if hasattr(x, '__contains__') else False)
        self.register_function("startswith", lambda x, y: x.startswith(y) if isinstance(x, str) else False)
        self.register_function("endswith", lambda x, y: x.endswith(y) if isinstance(x, str) else False)

    def register_function(self, name: str, func: Callable) -> None:
        """Register a custom function."""
        self.functions[f"_fn_{name}"] = func

    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the engine."""
        self.rules[rule.name] = rule
        logger.info(f"Added rule: {rule.name} (priority={rule.priority})")

    def remove_rule(self, name: str) -> None:
        """Remove a rule."""
        if name in self.rules:
            del self.rules[name]
            logger.info(f"Removed rule: {name}")

    def parse_and_add(self, dsl_source: str) -> List[Rule]:
        """Parse DSL source and add rules."""
        lexer = Lexer(dsl_source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        rules = parser.parse_rules()

        for rule in rules:
            self.add_rule(rule)

        return rules

    def evaluate(self, context: Dict[str, Any]) -> List[Tuple[str, Any]]:
        """
        Evaluate all matching rules.

        Args:
            context: Evaluation context

        Returns:
            List of (rule_name, result) tuples
        """
        # Merge functions into context
        eval_context = {**self.functions, **context}

        results = []

        # Sort rules by priority (higher first)
        sorted_rules = sorted(
            [r for r in self.rules.values() if r.enabled],
            key=lambda r: r.priority,
            reverse=True
        )

        for rule in sorted_rules:
            if rule.matches(eval_context):
                result = rule.execute(eval_context)
                results.append((rule.name, result))
                self.execution_history.append((rule.name, datetime.now(), result))
                logger.debug(f"Rule {rule.name} fired with result: {result}")

        return results

    def evaluate_first(self, context: Dict[str, Any]) -> Optional[Tuple[str, Any]]:
        """Evaluate and return first matching rule."""
        results = self.evaluate(context)
        return results[0] if results else None

    def get_matching_rules(self, context: Dict[str, Any]) -> List[Rule]:
        """Get all rules that would match the context."""
        eval_context = {**self.functions, **context}
        return [
            rule for rule in self.rules.values()
            if rule.enabled and rule.matches(eval_context)
        ]

    def explain(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Explain which rules match and why."""
        eval_context = {**self.functions, **context}
        explanations = []

        for rule in self.rules.values():
            try:
                matches = rule.matches(eval_context)
                explanations.append({
                    "rule": rule.name,
                    "priority": rule.priority,
                    "enabled": rule.enabled,
                    "matches": matches,
                    "condition": rule.condition.to_dict()
                })
            except Exception as e:
                explanations.append({
                    "rule": rule.name,
                    "error": str(e)
                })

        return explanations

    def to_dict(self) -> Dict[str, Any]:
        """Serialize engine state."""
        return {
            "rules": {name: rule.to_dict() for name, rule in self.rules.items()},
            "functions": list(self.functions.keys()),
            "history_count": len(self.execution_history)
        }


# =============================================================================
# DSL BUILDER
# =============================================================================

class DSLBuilder:
    """Fluent builder for creating rules programmatically."""

    def __init__(self, engine: Optional[RuleEngine] = None):
        self.engine = engine or RuleEngine()
        self._name: Optional[str] = None
        self._condition: Optional[ASTNode] = None
        self._action: Optional[ASTNode] = None
        self._priority: int = 0

    def rule(self, name: str) -> "DSLBuilder":
        """Start building a rule."""
        self._name = name
        self._condition = None
        self._action = None
        self._priority = 0
        return self

    def when(self, condition_str: str) -> "DSLBuilder":
        """Set rule condition from string."""
        lexer = Lexer(condition_str)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        self._condition = parser.parse_expression()
        return self

    def when_eq(self, left: str, right: Any) -> "DSLBuilder":
        """Set equality condition."""
        left_node = IdentifierNode(left) if isinstance(left, str) else LiteralNode(left)
        right_node = LiteralNode(right) if not isinstance(right, str) else IdentifierNode(right)
        self._condition = BinaryOpNode(Operator.EQ, left_node, right_node)
        return self

    def when_gt(self, left: str, right: Any) -> "DSLBuilder":
        """Set greater-than condition."""
        left_node = IdentifierNode(left)
        right_node = LiteralNode(right) if not isinstance(right, str) else IdentifierNode(right)
        self._condition = BinaryOpNode(Operator.GT, left_node, right_node)
        return self

    def then(self, action_str: str) -> "DSLBuilder":
        """Set rule action from string."""
        lexer = Lexer(action_str)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        self._action = parser.parse_expression()
        return self

    def then_value(self, value: Any) -> "DSLBuilder":
        """Set literal value as action."""
        self._action = LiteralNode(value)
        return self

    def priority(self, p: int) -> "DSLBuilder":
        """Set rule priority."""
        self._priority = p
        return self

    def build(self) -> Rule:
        """Build and add the rule."""
        if not self._name or not self._condition or not self._action:
            raise ValueError("Rule requires name, condition, and action")

        rule = Rule(
            name=self._name,
            condition=self._condition,
            action=self._action,
            priority=self._priority
        )

        self.engine.add_rule(rule)
        return rule

    def get_engine(self) -> RuleEngine:
        """Get the rule engine."""
        return self.engine


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_rule_engine() -> RuleEngine:
    """Create a new rule engine."""
    return RuleEngine()


def create_dsl_builder(engine: Optional[RuleEngine] = None) -> DSLBuilder:
    """Create a DSL builder."""
    return DSLBuilder(engine)


def compile_rules(source: str) -> RuleEngine:
    """Compile DSL source into a rule engine."""
    engine = RuleEngine()
    engine.parse_and_add(source)
    return engine


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "TokenType",
    "Operator",

    # Token & Lexer
    "Token",
    "Lexer",

    # AST Nodes
    "ASTNode",
    "LiteralNode",
    "IdentifierNode",
    "BinaryOpNode",
    "UnaryOpNode",
    "QuantifierNode",
    "FunctionCallNode",

    # Rule
    "Rule",

    # Parser
    "Parser",

    # Engine
    "RuleEngine",
    "DSLBuilder",

    # Factory functions
    "create_rule_engine",
    "create_dsl_builder",
    "compile_rules"
]
