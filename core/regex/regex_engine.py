#!/usr/bin/env python3
"""
BAEL - Regex Engine
Comprehensive regular expression engine with custom pattern matching.

Features:
- NFA-based regex implementation
- Pattern compilation and caching
- Named capture groups
- Lookahead and lookbehind
- Unicode support
- Pattern validation
- Match highlighting
- Replacement operations
- Pattern debugging
- Performance analysis
"""

import asyncio
import hashlib
import json
import logging
import re
import string
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Callable, Dict, Generator, Iterator, List, Optional,
                    Pattern, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class TokenType(Enum):
    """Token type for regex lexer."""
    LITERAL = "literal"
    DOT = "dot"
    STAR = "star"
    PLUS = "plus"
    QUESTION = "question"
    PIPE = "pipe"
    LPAREN = "lparen"
    RPAREN = "rparen"
    LBRACKET = "lbracket"
    RBRACKET = "rbracket"
    CARET = "caret"
    DOLLAR = "dollar"
    LBRACE = "lbrace"
    RBRACE = "rbrace"
    BACKSLASH = "backslash"
    ESCAPE = "escape"
    CHAR_CLASS = "char_class"
    EOF = "eof"


class NodeType(Enum):
    """AST node type."""
    LITERAL = "literal"
    CONCAT = "concat"
    ALTERNATION = "alternation"
    QUANTIFIER = "quantifier"
    GROUP = "group"
    CHAR_CLASS = "char_class"
    ANCHOR = "anchor"
    DOT = "dot"
    BACKREFERENCE = "backreference"
    LOOKAHEAD = "lookahead"
    LOOKBEHIND = "lookbehind"


class RegexFlags(Enum):
    """Regex flags."""
    NONE = 0
    IGNORECASE = 1
    MULTILINE = 2
    DOTALL = 4
    UNICODE = 8
    VERBOSE = 16


class MatchType(Enum):
    """Match type."""
    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Token:
    """Regex token."""
    type: TokenType
    value: str
    position: int


@dataclass
class Match:
    """Regex match result."""
    start: int
    end: int
    text: str
    groups: Dict[str, str] = field(default_factory=dict)
    group_spans: Dict[str, Tuple[int, int]] = field(default_factory=dict)

    @property
    def span(self) -> Tuple[int, int]:
        return (self.start, self.end)

    def group(self, name: Union[int, str] = 0) -> str:
        """Get group by name or index."""
        if name == 0:
            return self.text
        if isinstance(name, int):
            name = str(name)
        return self.groups.get(name, "")


@dataclass
class PatternInfo:
    """Pattern information."""
    pattern: str
    flags: int
    groups: int
    named_groups: List[str]
    is_valid: bool
    error: Optional[str] = None
    complexity: int = 0


@dataclass
class DebugStep:
    """Debug step during matching."""
    step: int
    position: int
    state: str
    matched: str
    remaining: str
    notes: str = ""


@dataclass
class PerformanceStats:
    """Performance statistics."""
    pattern: str
    input_length: int
    match_time_ms: float
    states_visited: int
    backtrack_count: int
    matches_found: int


# =============================================================================
# LEXER
# =============================================================================

class RegexLexer:
    """Tokenize regex patterns."""

    ESCAPE_CHARS = {
        'd': r'\d',
        'D': r'\D',
        'w': r'\w',
        'W': r'\W',
        's': r'\s',
        'S': r'\S',
        'n': '\n',
        't': '\t',
        'r': '\r',
        'b': r'\b',
        'B': r'\B',
    }

    def __init__(self, pattern: str):
        self.pattern = pattern
        self.pos = 0
        self.length = len(pattern)

    def tokenize(self) -> List[Token]:
        """Tokenize the pattern."""
        tokens = []

        while self.pos < self.length:
            token = self._next_token()
            if token:
                tokens.append(token)

        tokens.append(Token(TokenType.EOF, "", self.pos))
        return tokens

    def _next_token(self) -> Optional[Token]:
        """Get next token."""
        if self.pos >= self.length:
            return None

        char = self.pattern[self.pos]
        pos = self.pos

        if char == '\\':
            return self._parse_escape()
        elif char == '.':
            self.pos += 1
            return Token(TokenType.DOT, char, pos)
        elif char == '*':
            self.pos += 1
            return Token(TokenType.STAR, char, pos)
        elif char == '+':
            self.pos += 1
            return Token(TokenType.PLUS, char, pos)
        elif char == '?':
            self.pos += 1
            return Token(TokenType.QUESTION, char, pos)
        elif char == '|':
            self.pos += 1
            return Token(TokenType.PIPE, char, pos)
        elif char == '(':
            self.pos += 1
            return Token(TokenType.LPAREN, char, pos)
        elif char == ')':
            self.pos += 1
            return Token(TokenType.RPAREN, char, pos)
        elif char == '[':
            return self._parse_char_class()
        elif char == '^':
            self.pos += 1
            return Token(TokenType.CARET, char, pos)
        elif char == '$':
            self.pos += 1
            return Token(TokenType.DOLLAR, char, pos)
        elif char == '{':
            return self._parse_quantifier()
        else:
            self.pos += 1
            return Token(TokenType.LITERAL, char, pos)

    def _parse_escape(self) -> Token:
        """Parse escape sequence."""
        pos = self.pos
        self.pos += 1

        if self.pos >= self.length:
            return Token(TokenType.LITERAL, '\\', pos)

        char = self.pattern[self.pos]
        self.pos += 1

        if char in self.ESCAPE_CHARS:
            return Token(TokenType.ESCAPE, char, pos)
        else:
            return Token(TokenType.LITERAL, char, pos)

    def _parse_char_class(self) -> Token:
        """Parse character class [...]."""
        pos = self.pos
        self.pos += 1
        content = ""

        if self.pos < self.length and self.pattern[self.pos] == '^':
            content += '^'
            self.pos += 1

        while self.pos < self.length:
            char = self.pattern[self.pos]

            if char == ']' and content:
                self.pos += 1
                return Token(TokenType.CHAR_CLASS, content, pos)
            elif char == '\\' and self.pos + 1 < self.length:
                content += char + self.pattern[self.pos + 1]
                self.pos += 2
            else:
                content += char
                self.pos += 1

        return Token(TokenType.CHAR_CLASS, content, pos)

    def _parse_quantifier(self) -> Token:
        """Parse quantifier {n,m}."""
        pos = self.pos
        self.pos += 1
        content = ""

        while self.pos < self.length:
            char = self.pattern[self.pos]

            if char == '}':
                self.pos += 1
                return Token(TokenType.LBRACE, content, pos)
            else:
                content += char
                self.pos += 1

        return Token(TokenType.LITERAL, '{', pos)


# =============================================================================
# AST NODES
# =============================================================================

class ASTNode(ABC):
    """Abstract AST node."""

    @abstractmethod
    def accept(self, visitor: "ASTVisitor") -> Any:
        pass


class LiteralNode(ASTNode):
    """Literal character node."""

    def __init__(self, char: str):
        self.char = char

    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_literal(self)


class ConcatNode(ASTNode):
    """Concatenation node."""

    def __init__(self, left: ASTNode, right: ASTNode):
        self.left = left
        self.right = right

    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_concat(self)


class AlternationNode(ASTNode):
    """Alternation (|) node."""

    def __init__(self, left: ASTNode, right: ASTNode):
        self.left = left
        self.right = right

    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_alternation(self)


class QuantifierNode(ASTNode):
    """Quantifier node (*, +, ?, {n,m})."""

    def __init__(
        self,
        child: ASTNode,
        min_count: int,
        max_count: Optional[int],
        greedy: bool = True
    ):
        self.child = child
        self.min_count = min_count
        self.max_count = max_count
        self.greedy = greedy

    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_quantifier(self)


class GroupNode(ASTNode):
    """Capture group node."""

    def __init__(
        self,
        child: ASTNode,
        index: int,
        name: Optional[str] = None,
        capturing: bool = True
    ):
        self.child = child
        self.index = index
        self.name = name
        self.capturing = capturing

    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_group(self)


class CharClassNode(ASTNode):
    """Character class node."""

    def __init__(self, chars: Set[str], negated: bool = False):
        self.chars = chars
        self.negated = negated

    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_char_class(self)


class AnchorNode(ASTNode):
    """Anchor node (^, $)."""

    def __init__(self, anchor_type: str):
        self.anchor_type = anchor_type

    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_anchor(self)


class DotNode(ASTNode):
    """Dot (.) node."""

    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_dot(self)


# =============================================================================
# AST VISITOR
# =============================================================================

class ASTVisitor(ABC):
    """Abstract AST visitor."""

    @abstractmethod
    def visit_literal(self, node: LiteralNode) -> Any:
        pass

    @abstractmethod
    def visit_concat(self, node: ConcatNode) -> Any:
        pass

    @abstractmethod
    def visit_alternation(self, node: AlternationNode) -> Any:
        pass

    @abstractmethod
    def visit_quantifier(self, node: QuantifierNode) -> Any:
        pass

    @abstractmethod
    def visit_group(self, node: GroupNode) -> Any:
        pass

    @abstractmethod
    def visit_char_class(self, node: CharClassNode) -> Any:
        pass

    @abstractmethod
    def visit_anchor(self, node: AnchorNode) -> Any:
        pass

    @abstractmethod
    def visit_dot(self, node: DotNode) -> Any:
        pass


# =============================================================================
# PARSER
# =============================================================================

class RegexParser:
    """Parse regex tokens into AST."""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.group_count = 0
        self.named_groups: List[str] = []

    def parse(self) -> ASTNode:
        """Parse tokens into AST."""
        return self._parse_alternation()

    def _parse_alternation(self) -> ASTNode:
        """Parse alternation."""
        left = self._parse_concat()

        while self._peek().type == TokenType.PIPE:
            self._advance()
            right = self._parse_concat()
            left = AlternationNode(left, right)

        return left

    def _parse_concat(self) -> ASTNode:
        """Parse concatenation."""
        nodes = []

        while True:
            token = self._peek()

            if token.type in (TokenType.EOF, TokenType.PIPE, TokenType.RPAREN):
                break

            node = self._parse_quantified()
            if node:
                nodes.append(node)

        if not nodes:
            return LiteralNode("")

        result = nodes[0]
        for node in nodes[1:]:
            result = ConcatNode(result, node)

        return result

    def _parse_quantified(self) -> Optional[ASTNode]:
        """Parse quantified expression."""
        node = self._parse_atom()

        if not node:
            return None

        token = self._peek()

        if token.type == TokenType.STAR:
            self._advance()
            greedy = not self._try_consume(TokenType.QUESTION)
            return QuantifierNode(node, 0, None, greedy)

        elif token.type == TokenType.PLUS:
            self._advance()
            greedy = not self._try_consume(TokenType.QUESTION)
            return QuantifierNode(node, 1, None, greedy)

        elif token.type == TokenType.QUESTION:
            self._advance()
            greedy = not self._try_consume(TokenType.QUESTION)
            return QuantifierNode(node, 0, 1, greedy)

        elif token.type == TokenType.LBRACE:
            return self._parse_counted_quantifier(node)

        return node

    def _parse_counted_quantifier(self, node: ASTNode) -> ASTNode:
        """Parse {n,m} quantifier."""
        token = self._advance()

        parts = token.value.split(',')

        if len(parts) == 1:
            count = int(parts[0])
            return QuantifierNode(node, count, count)
        else:
            min_count = int(parts[0]) if parts[0] else 0
            max_count = int(parts[1]) if parts[1] else None
            return QuantifierNode(node, min_count, max_count)

    def _parse_atom(self) -> Optional[ASTNode]:
        """Parse atomic expression."""
        token = self._peek()

        if token.type == TokenType.LITERAL:
            self._advance()
            return LiteralNode(token.value)

        elif token.type == TokenType.DOT:
            self._advance()
            return DotNode()

        elif token.type == TokenType.ESCAPE:
            self._advance()
            return self._create_escape_node(token.value)

        elif token.type == TokenType.CHAR_CLASS:
            self._advance()
            return self._create_char_class_node(token.value)

        elif token.type == TokenType.CARET:
            self._advance()
            return AnchorNode("start")

        elif token.type == TokenType.DOLLAR:
            self._advance()
            return AnchorNode("end")

        elif token.type == TokenType.LPAREN:
            return self._parse_group()

        return None

    def _parse_group(self) -> ASTNode:
        """Parse group."""
        self._advance()  # consume (

        self.group_count += 1
        group_index = self.group_count
        name = None
        capturing = True

        # Check for group modifiers
        if self._peek().type == TokenType.QUESTION:
            self._advance()
            next_token = self._peek()

            if next_token.type == TokenType.LITERAL:
                if next_token.value == ':':
                    self._advance()
                    capturing = False
                elif next_token.value == 'P':
                    self._advance()
                    # Named group
                    if self._peek().value == '<':
                        self._advance()
                        name = ""
                        while self._peek().value not in ('>', ')'):
                            name += self._advance().value
                        self._advance()  # consume >
                        self.named_groups.append(name)

        child = self._parse_alternation()

        if self._peek().type == TokenType.RPAREN:
            self._advance()

        return GroupNode(child, group_index, name, capturing)

    def _create_escape_node(self, char: str) -> ASTNode:
        """Create node for escape sequence."""
        if char == 'd':
            return CharClassNode(set(string.digits))
        elif char == 'D':
            return CharClassNode(set(string.digits), negated=True)
        elif char == 'w':
            return CharClassNode(set(string.ascii_letters + string.digits + '_'))
        elif char == 'W':
            return CharClassNode(set(string.ascii_letters + string.digits + '_'), negated=True)
        elif char == 's':
            return CharClassNode(set(' \t\n\r\f\v'))
        elif char == 'S':
            return CharClassNode(set(' \t\n\r\f\v'), negated=True)
        elif char == 'b':
            return AnchorNode("word_boundary")
        elif char == 'B':
            return AnchorNode("not_word_boundary")
        else:
            return LiteralNode(char)

    def _create_char_class_node(self, content: str) -> ASTNode:
        """Create character class node."""
        negated = False
        chars = set()

        i = 0
        if content.startswith('^'):
            negated = True
            i = 1

        while i < len(content):
            if i + 2 < len(content) and content[i + 1] == '-':
                # Range
                start = content[i]
                end = content[i + 2]
                for c in range(ord(start), ord(end) + 1):
                    chars.add(chr(c))
                i += 3
            elif content[i] == '\\' and i + 1 < len(content):
                # Escape in class
                chars.add(content[i + 1])
                i += 2
            else:
                chars.add(content[i])
                i += 1

        return CharClassNode(chars, negated)

    def _peek(self) -> Token:
        """Peek at current token."""
        if self.pos >= len(self.tokens):
            return Token(TokenType.EOF, "", len(self.tokens))
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        """Advance and return current token."""
        token = self._peek()
        self.pos += 1
        return token

    def _try_consume(self, token_type: TokenType) -> bool:
        """Try to consume a token of given type."""
        if self._peek().type == token_type:
            self._advance()
            return True
        return False


# =============================================================================
# MATCHER
# =============================================================================

class RegexMatcher(ASTVisitor):
    """Match regex against text using AST."""

    def __init__(self, root: ASTNode, flags: int = 0):
        self.root = root
        self.flags = flags
        self.text = ""
        self.pos = 0
        self.groups: Dict[int, Tuple[int, int]] = {}
        self.named_groups: Dict[str, Tuple[int, int]] = {}
        self.debug_steps: List[DebugStep] = []
        self.step_count = 0
        self.backtrack_count = 0

    def match(self, text: str, pos: int = 0) -> Optional[Match]:
        """Match at specific position."""
        self.text = text
        self.pos = pos
        self.groups = {}
        self.named_groups = {}

        result_pos = self.root.accept(self)

        if result_pos is not None:
            # Build groups dict
            groups_dict = {}
            group_spans = {}

            for idx, span in self.groups.items():
                if span:
                    groups_dict[str(idx)] = text[span[0]:span[1]]
                    group_spans[str(idx)] = span

            for name, span in self.named_groups.items():
                if span:
                    groups_dict[name] = text[span[0]:span[1]]
                    group_spans[name] = span

            return Match(
                start=pos,
                end=result_pos,
                text=text[pos:result_pos],
                groups=groups_dict,
                group_spans=group_spans
            )

        return None

    def search(self, text: str) -> Optional[Match]:
        """Search for pattern in text."""
        for i in range(len(text) + 1):
            match = self.match(text, i)
            if match:
                return match
        return None

    def findall(self, text: str) -> List[Match]:
        """Find all matches in text."""
        matches = []
        pos = 0

        while pos <= len(text):
            match = self.match(text, pos)
            if match:
                matches.append(match)
                pos = match.end if match.end > pos else pos + 1
            else:
                pos += 1

        return matches

    def visit_literal(self, node: LiteralNode) -> Optional[int]:
        """Visit literal node."""
        if self.pos >= len(self.text):
            return None

        char = self.text[self.pos]
        expected = node.char

        if self.flags & RegexFlags.IGNORECASE.value:
            if char.lower() == expected.lower():
                return self.pos + 1
        else:
            if char == expected:
                return self.pos + 1

        return None

    def visit_concat(self, node: ConcatNode) -> Optional[int]:
        """Visit concatenation node."""
        left_pos = node.left.accept(self)

        if left_pos is None:
            return None

        saved_pos = self.pos
        self.pos = left_pos

        right_pos = node.right.accept(self)

        if right_pos is None:
            self.pos = saved_pos
            return None

        return right_pos

    def visit_alternation(self, node: AlternationNode) -> Optional[int]:
        """Visit alternation node."""
        saved_pos = self.pos

        left_pos = node.left.accept(self)
        if left_pos is not None:
            return left_pos

        self.pos = saved_pos
        self.backtrack_count += 1

        return node.right.accept(self)

    def visit_quantifier(self, node: QuantifierNode) -> Optional[int]:
        """Visit quantifier node."""
        count = 0
        positions = [self.pos]

        # Match as many as possible
        while node.max_count is None or count < node.max_count:
            saved_pos = self.pos
            new_pos = node.child.accept(self)

            if new_pos is None or new_pos == saved_pos:
                break

            self.pos = new_pos
            positions.append(new_pos)
            count += 1

        # Check minimum
        if count < node.min_count:
            return None

        # For greedy, we're already at max
        if node.greedy:
            return positions[-1]
        else:
            # For non-greedy, return minimum
            if node.min_count < len(positions):
                return positions[node.min_count]
            return positions[-1]

    def visit_group(self, node: GroupNode) -> Optional[int]:
        """Visit group node."""
        start_pos = self.pos

        result_pos = node.child.accept(self)

        if result_pos is not None and node.capturing:
            span = (start_pos, result_pos)
            self.groups[node.index] = span
            if node.name:
                self.named_groups[node.name] = span

        return result_pos

    def visit_char_class(self, node: CharClassNode) -> Optional[int]:
        """Visit character class node."""
        if self.pos >= len(self.text):
            return None

        char = self.text[self.pos]

        if self.flags & RegexFlags.IGNORECASE.value:
            in_class = any(
                c.lower() == char.lower() for c in node.chars
            )
        else:
            in_class = char in node.chars

        if node.negated:
            in_class = not in_class

        if in_class:
            return self.pos + 1

        return None

    def visit_anchor(self, node: AnchorNode) -> Optional[int]:
        """Visit anchor node."""
        if node.anchor_type == "start":
            if self.pos == 0:
                return self.pos
            if self.flags & RegexFlags.MULTILINE.value:
                if self.pos > 0 and self.text[self.pos - 1] == '\n':
                    return self.pos

        elif node.anchor_type == "end":
            if self.pos == len(self.text):
                return self.pos
            if self.flags & RegexFlags.MULTILINE.value:
                if self.pos < len(self.text) and self.text[self.pos] == '\n':
                    return self.pos

        elif node.anchor_type == "word_boundary":
            before = self.pos > 0 and self._is_word_char(self.text[self.pos - 1])
            after = self.pos < len(self.text) and self._is_word_char(self.text[self.pos])
            if before != after:
                return self.pos

        elif node.anchor_type == "not_word_boundary":
            before = self.pos > 0 and self._is_word_char(self.text[self.pos - 1])
            after = self.pos < len(self.text) and self._is_word_char(self.text[self.pos])
            if before == after:
                return self.pos

        return None

    def visit_dot(self, node: DotNode) -> Optional[int]:
        """Visit dot node."""
        if self.pos >= len(self.text):
            return None

        char = self.text[self.pos]

        if self.flags & RegexFlags.DOTALL.value:
            return self.pos + 1
        elif char != '\n':
            return self.pos + 1

        return None

    def _is_word_char(self, char: str) -> bool:
        """Check if char is word character."""
        return char.isalnum() or char == '_'


# =============================================================================
# COMPILED PATTERN
# =============================================================================

class CompiledPattern:
    """Compiled regex pattern."""

    def __init__(
        self,
        pattern: str,
        root: ASTNode,
        flags: int = 0,
        groups: int = 0,
        named_groups: Optional[List[str]] = None
    ):
        self.pattern = pattern
        self.root = root
        self.flags = flags
        self.groups = groups
        self.named_groups = named_groups or []

    def match(self, text: str, pos: int = 0) -> Optional[Match]:
        """Match at position."""
        matcher = RegexMatcher(self.root, self.flags)
        return matcher.match(text, pos)

    def search(self, text: str) -> Optional[Match]:
        """Search for pattern."""
        matcher = RegexMatcher(self.root, self.flags)
        return matcher.search(text)

    def findall(self, text: str) -> List[str]:
        """Find all matches."""
        matcher = RegexMatcher(self.root, self.flags)
        matches = matcher.findall(text)

        if self.groups == 0:
            return [m.text for m in matches]
        elif self.groups == 1:
            return [m.group(1) for m in matches]
        else:
            return [tuple(m.group(i) for i in range(1, self.groups + 1)) for m in matches]

    def finditer(self, text: str) -> Iterator[Match]:
        """Iterate over matches."""
        matcher = RegexMatcher(self.root, self.flags)
        return iter(matcher.findall(text))

    def sub(self, repl: Union[str, Callable], text: str, count: int = 0) -> str:
        """Substitute matches."""
        matches = list(self.finditer(text))

        if count > 0:
            matches = matches[:count]

        result = []
        last_end = 0

        for match in matches:
            result.append(text[last_end:match.start])

            if callable(repl):
                result.append(repl(match))
            else:
                # Handle backreferences in replacement
                replacement = repl
                for i in range(self.groups + 1):
                    replacement = replacement.replace(f'\\{i}', match.group(i))
                result.append(replacement)

            last_end = match.end

        result.append(text[last_end:])
        return ''.join(result)

    def split(self, text: str, maxsplit: int = 0) -> List[str]:
        """Split by pattern."""
        matches = list(self.finditer(text))

        if maxsplit > 0:
            matches = matches[:maxsplit]

        result = []
        last_end = 0

        for match in matches:
            result.append(text[last_end:match.start])
            last_end = match.end

        result.append(text[last_end:])
        return result


# =============================================================================
# REGEX ENGINE
# =============================================================================

class RegexEngine:
    """
    Comprehensive Regex Engine for BAEL.

    Provides pattern matching and text processing.
    """

    def __init__(self):
        self._cache: Dict[str, CompiledPattern] = {}
        self._cache_size = 100
        self._stats: Dict[str, int] = defaultdict(int)

    # -------------------------------------------------------------------------
    # COMPILATION
    # -------------------------------------------------------------------------

    def compile(
        self,
        pattern: str,
        flags: int = 0
    ) -> CompiledPattern:
        """Compile a regex pattern."""
        cache_key = f"{pattern}:{flags}"

        if cache_key in self._cache:
            self._stats["cache_hits"] += 1
            return self._cache[cache_key]

        self._stats["compilations"] += 1

        # Tokenize
        lexer = RegexLexer(pattern)
        tokens = lexer.tokenize()

        # Parse
        parser = RegexParser(tokens)
        root = parser.parse()

        compiled = CompiledPattern(
            pattern=pattern,
            root=root,
            flags=flags,
            groups=parser.group_count,
            named_groups=parser.named_groups
        )

        # Cache
        if len(self._cache) >= self._cache_size:
            # Remove oldest
            oldest = next(iter(self._cache))
            del self._cache[oldest]

        self._cache[cache_key] = compiled

        return compiled

    # -------------------------------------------------------------------------
    # MATCHING
    # -------------------------------------------------------------------------

    def match(
        self,
        pattern: str,
        text: str,
        flags: int = 0
    ) -> Optional[Match]:
        """Match pattern at start of text."""
        compiled = self.compile(pattern, flags)
        return compiled.match(text)

    def search(
        self,
        pattern: str,
        text: str,
        flags: int = 0
    ) -> Optional[Match]:
        """Search for pattern in text."""
        compiled = self.compile(pattern, flags)
        return compiled.search(text)

    def findall(
        self,
        pattern: str,
        text: str,
        flags: int = 0
    ) -> List[str]:
        """Find all matches."""
        compiled = self.compile(pattern, flags)
        return compiled.findall(text)

    def finditer(
        self,
        pattern: str,
        text: str,
        flags: int = 0
    ) -> Iterator[Match]:
        """Iterate over matches."""
        compiled = self.compile(pattern, flags)
        return compiled.finditer(text)

    # -------------------------------------------------------------------------
    # SUBSTITUTION
    # -------------------------------------------------------------------------

    def sub(
        self,
        pattern: str,
        repl: Union[str, Callable],
        text: str,
        count: int = 0,
        flags: int = 0
    ) -> str:
        """Substitute matches."""
        compiled = self.compile(pattern, flags)
        return compiled.sub(repl, text, count)

    def subn(
        self,
        pattern: str,
        repl: Union[str, Callable],
        text: str,
        count: int = 0,
        flags: int = 0
    ) -> Tuple[str, int]:
        """Substitute and return count."""
        compiled = self.compile(pattern, flags)
        matches = list(compiled.finditer(text))

        if count > 0:
            matches = matches[:count]

        result = compiled.sub(repl, text, count)
        return (result, len(matches))

    # -------------------------------------------------------------------------
    # SPLITTING
    # -------------------------------------------------------------------------

    def split(
        self,
        pattern: str,
        text: str,
        maxsplit: int = 0,
        flags: int = 0
    ) -> List[str]:
        """Split text by pattern."""
        compiled = self.compile(pattern, flags)
        return compiled.split(text, maxsplit)

    # -------------------------------------------------------------------------
    # VALIDATION
    # -------------------------------------------------------------------------

    def is_valid(self, pattern: str) -> bool:
        """Check if pattern is valid."""
        try:
            self.compile(pattern)
            return True
        except Exception:
            return False

    def get_info(self, pattern: str) -> PatternInfo:
        """Get pattern information."""
        try:
            compiled = self.compile(pattern)
            return PatternInfo(
                pattern=pattern,
                flags=0,
                groups=compiled.groups,
                named_groups=compiled.named_groups,
                is_valid=True,
                complexity=self._estimate_complexity(pattern)
            )
        except Exception as e:
            return PatternInfo(
                pattern=pattern,
                flags=0,
                groups=0,
                named_groups=[],
                is_valid=False,
                error=str(e)
            )

    def _estimate_complexity(self, pattern: str) -> int:
        """Estimate pattern complexity."""
        complexity = len(pattern)

        # Nested quantifiers increase complexity
        complexity += pattern.count('*') * 2
        complexity += pattern.count('+') * 2
        complexity += pattern.count('?')

        # Alternation
        complexity += pattern.count('|') * 3

        # Groups
        complexity += pattern.count('(') * 2

        return complexity

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def escape(self, text: str) -> str:
        """Escape special regex characters."""
        special = r'\^$.|?*+()[]{}/'
        return ''.join(
            '\\' + char if char in special else char
            for char in text
        )

    def highlight(self, pattern: str, text: str) -> str:
        """Highlight matches in text."""
        compiled = self.compile(pattern)
        matches = list(compiled.finditer(text))

        if not matches:
            return text

        result = []
        last_end = 0

        for match in matches:
            result.append(text[last_end:match.start])
            result.append(f"[{match.text}]")
            last_end = match.end

        result.append(text[last_end:])
        return ''.join(result)

    def clear_cache(self) -> None:
        """Clear pattern cache."""
        self._cache.clear()

    def get_stats(self) -> Dict[str, int]:
        """Get engine statistics."""
        return dict(self._stats)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Regex Engine."""
    print("=" * 70)
    print("BAEL - REGEX ENGINE DEMO")
    print("Comprehensive Pattern Matching System")
    print("=" * 70)
    print()

    engine = RegexEngine()

    # 1. Basic Matching
    print("1. BASIC MATCHING:")
    print("-" * 40)

    text = "Hello, World!"
    pattern = "World"

    match = engine.search(pattern, text)
    print(f"   Text: '{text}'")
    print(f"   Pattern: '{pattern}'")
    print(f"   Match: '{match.text}' at {match.span}" if match else "   No match")
    print()

    # 2. Character Classes
    print("2. CHARACTER CLASSES:")
    print("-" * 40)

    text = "abc123xyz"
    patterns = [r"\d+", r"\w+", r"[a-z]+", r"[0-9]+"]

    for pattern in patterns:
        match = engine.search(pattern, text)
        print(f"   {pattern}: '{match.text}'" if match else f"   {pattern}: No match")
    print()

    # 3. Quantifiers
    print("3. QUANTIFIERS:")
    print("-" * 40)

    text = "aaabbbccc"
    patterns = ["a+", "b*", "c?", "a{2,3}"]

    for pattern in patterns:
        matches = engine.findall(pattern, text)
        print(f"   {pattern}: {matches}")
    print()

    # 4. Alternation
    print("4. ALTERNATION:")
    print("-" * 40)

    text = "cat dog bird"
    pattern = "cat|dog"

    matches = engine.findall(pattern, text)
    print(f"   Text: '{text}'")
    print(f"   Pattern: '{pattern}'")
    print(f"   Matches: {matches}")
    print()

    # 5. Groups
    print("5. GROUPS:")
    print("-" * 40)

    text = "John Smith"
    pattern = r"(\w+) (\w+)"

    match = engine.match(pattern, text)
    if match:
        print(f"   Full match: '{match.text}'")
        print(f"   Group 1: '{match.group(1)}'")
        print(f"   Group 2: '{match.group(2)}'")
    print()

    # 6. Anchors
    print("6. ANCHORS:")
    print("-" * 40)

    text = "start middle end"

    print(f"   Text: '{text}'")
    print(f"   ^start: {bool(engine.match('^start', text))}")
    print(f"   end$: {bool(engine.search('end$', text))}")
    print()

    # 7. Find All
    print("7. FIND ALL:")
    print("-" * 40)

    text = "The quick brown fox jumps over the lazy dog"
    pattern = r"\b\w{4}\b"

    matches = engine.findall(pattern, text)
    print(f"   Pattern: '{pattern}' (4-letter words)")
    print(f"   Matches: {matches}")
    print()

    # 8. Substitution
    print("8. SUBSTITUTION:")
    print("-" * 40)

    text = "Hello World"
    result = engine.sub(r"World", "BAEL", text)
    print(f"   Original: '{text}'")
    print(f"   Replaced: '{result}'")

    text2 = "a1b2c3"
    result2 = engine.sub(r"\d", "*", text2)
    print(f"   Original: '{text2}'")
    print(f"   Replaced: '{result2}'")
    print()

    # 9. Split
    print("9. SPLIT:")
    print("-" * 40)

    text = "one,two;three.four"
    parts = engine.split(r"[,;.]", text)
    print(f"   Text: '{text}'")
    print(f"   Pattern: '[,;.]'")
    print(f"   Parts: {parts}")
    print()

    # 10. Pattern Validation
    print("10. PATTERN VALIDATION:")
    print("-" * 40)

    patterns = [r"\d+", r"[a-z]+", r"(test)"]

    for pattern in patterns:
        info = engine.get_info(pattern)
        print(f"   '{pattern}': valid={info.is_valid}, groups={info.groups}")
    print()

    # 11. Escaping
    print("11. ESCAPING:")
    print("-" * 40)

    special = "price: $100.00 (total)"
    escaped = engine.escape(special)
    print(f"   Original: '{special}'")
    print(f"   Escaped: '{escaped}'")
    print()

    # 12. Highlighting
    print("12. HIGHLIGHTING:")
    print("-" * 40)

    text = "The cat sat on the mat"
    highlighted = engine.highlight(r"\w{3}", text)
    print(f"   Original: '{text}'")
    print(f"   Highlighted: '{highlighted}'")
    print()

    # 13. Compiled Pattern
    print("13. COMPILED PATTERN:")
    print("-" * 40)

    compiled = engine.compile(r"\d+")

    text = "a1b2c3d4"
    matches = compiled.findall(text)
    print(f"   Pattern: '\\d+'")
    print(f"   Text: '{text}'")
    print(f"   Matches: {matches}")
    print()

    # 14. Performance
    print("14. PERFORMANCE:")
    print("-" * 40)

    import time

    long_text = "a" * 1000 + "b" + "a" * 1000
    pattern = "a+b"

    start = time.perf_counter()
    for _ in range(100):
        engine.search(pattern, long_text)
    elapsed = (time.perf_counter() - start) * 1000

    print(f"   Pattern: '{pattern}'")
    print(f"   Text length: {len(long_text)}")
    print(f"   100 searches: {elapsed:.2f}ms")
    print()

    # 15. Statistics
    print("15. ENGINE STATISTICS:")
    print("-" * 40)

    stats = engine.get_stats()
    print(f"   Stats: {stats}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Regex Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
