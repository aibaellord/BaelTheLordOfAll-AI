"""
BAEL Template Engine
====================

Jinja-like templating with:
- Variable substitution
- Control structures
- Template inheritance
- Filters and macros
- Auto-escaping

"Ba'el shapes reality through patterns." — Ba'el
"""

import asyncio
import logging
import re
import html
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Tuple, Union, Pattern
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
from pathlib import Path
import threading
import os

logger = logging.getLogger("BAEL.Template")


# ============================================================================
# ENUMS
# ============================================================================

class TokenType(Enum):
    """Token types in templates."""
    TEXT = "text"
    VARIABLE_START = "variable_start"      # {{
    VARIABLE_END = "variable_end"          # }}
    BLOCK_START = "block_start"            # {%
    BLOCK_END = "block_end"                # %}
    COMMENT_START = "comment_start"        # {#
    COMMENT_END = "comment_end"            # #}
    NAME = "name"
    STRING = "string"
    NUMBER = "number"
    OPERATOR = "operator"
    LPAREN = "lparen"
    RPAREN = "rparen"
    LBRACKET = "lbracket"
    RBRACKET = "rbracket"
    DOT = "dot"
    COMMA = "comma"
    PIPE = "pipe"
    COLON = "colon"
    EOF = "eof"


class NodeType(Enum):
    """AST node types."""
    TEMPLATE = "template"
    TEXT = "text"
    OUTPUT = "output"
    IF = "if"
    FOR = "for"
    BLOCK = "block"
    EXTENDS = "extends"
    INCLUDE = "include"
    MACRO = "macro"
    CALL = "call"
    SET = "set"
    EXPRESSION = "expression"
    NAME = "name"
    LITERAL = "literal"
    BINARY = "binary"
    UNARY = "unary"
    FILTER = "filter"
    GETATTR = "getattr"
    GETITEM = "getitem"


class AutoEscapeMode(Enum):
    """Auto-escape modes."""
    NONE = "none"
    HTML = "html"
    XML = "xml"
    JSON = "json"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Token:
    """A lexer token."""
    type: TokenType
    value: Any
    line: int = 1
    column: int = 1


@dataclass
class Node:
    """An AST node."""
    type: NodeType
    value: Any = None
    children: List['Node'] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    line: int = 1


@dataclass
class Template:
    """A compiled template."""
    name: str
    source: str
    ast: Optional[Node] = None
    code: Optional[str] = None

    # Metadata
    parent: Optional[str] = None
    blocks: Dict[str, Node] = field(default_factory=dict)
    macros: Dict[str, Node] = field(default_factory=dict)

    # Timestamps
    compiled_at: Optional[datetime] = None

    def render(self, context: Dict[str, Any], engine: 'TemplateEngine') -> str:
        """Render the template."""
        return engine.render_template(self, context)


@dataclass
class TemplateConfig:
    """Template engine configuration."""
    # Delimiters
    variable_start: str = "{{"
    variable_end: str = "}}"
    block_start: str = "{%"
    block_end: str = "%}"
    comment_start: str = "{#"
    comment_end: str = "#}"

    # Options
    auto_escape: AutoEscapeMode = AutoEscapeMode.HTML
    trim_blocks: bool = True
    lstrip_blocks: bool = True

    # Paths
    template_paths: List[str] = field(default_factory=list)

    # Cache
    cache_enabled: bool = True
    cache_size: int = 400


# ============================================================================
# LEXER
# ============================================================================

class Lexer:
    """
    Template lexer - converts source to tokens.
    """

    def __init__(self, config: TemplateConfig):
        """Initialize lexer."""
        self.config = config
        self._build_patterns()

    def _build_patterns(self) -> None:
        """Build regex patterns."""
        # Escape special regex chars
        vs = re.escape(self.config.variable_start)
        ve = re.escape(self.config.variable_end)
        bs = re.escape(self.config.block_start)
        be = re.escape(self.config.block_end)
        cs = re.escape(self.config.comment_start)
        ce = re.escape(self.config.comment_end)

        # Main pattern to find tags
        self.tag_pattern = re.compile(
            f'({vs}|{bs}|{cs})'
        )

        # Patterns for tag endings
        self.variable_end_pattern = re.compile(re.escape(self.config.variable_end))
        self.block_end_pattern = re.compile(re.escape(self.config.block_end))
        self.comment_end_pattern = re.compile(re.escape(self.config.comment_end))

        # Token patterns for inside tags
        self.name_pattern = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*')
        self.string_pattern = re.compile(r'"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'')
        self.number_pattern = re.compile(r'-?\d+\.?\d*')
        self.operator_pattern = re.compile(r'==|!=|<=|>=|<|>|\+|-|\*|/|%|and|or|not|in|is')

    def tokenize(self, source: str) -> List[Token]:
        """Tokenize template source."""
        tokens = []
        pos = 0
        line = 1
        column = 1

        while pos < len(source):
            # Find next tag
            match = self.tag_pattern.search(source, pos)

            if not match:
                # Rest is text
                if pos < len(source):
                    tokens.append(Token(TokenType.TEXT, source[pos:], line, column))
                break

            # Text before tag
            if match.start() > pos:
                text = source[pos:match.start()]
                tokens.append(Token(TokenType.TEXT, text, line, column))

                # Update position
                newlines = text.count('\n')
                if newlines:
                    line += newlines
                    column = len(text) - text.rfind('\n')
                else:
                    column += len(text)

            tag_start = match.group(1)
            pos = match.end()

            if tag_start == self.config.variable_start:
                tokens.append(Token(TokenType.VARIABLE_START, tag_start, line, column))

                # Find end
                end_match = self.variable_end_pattern.search(source, pos)
                if end_match:
                    content = source[pos:end_match.start()]
                    tokens.extend(self._tokenize_expression(content, line, column))
                    tokens.append(Token(TokenType.VARIABLE_END, self.config.variable_end, line, column))
                    pos = end_match.end()

            elif tag_start == self.config.block_start:
                tokens.append(Token(TokenType.BLOCK_START, tag_start, line, column))

                # Find end
                end_match = self.block_end_pattern.search(source, pos)
                if end_match:
                    content = source[pos:end_match.start()]
                    tokens.extend(self._tokenize_expression(content, line, column))
                    tokens.append(Token(TokenType.BLOCK_END, self.config.block_end, line, column))
                    pos = end_match.end()

            elif tag_start == self.config.comment_start:
                tokens.append(Token(TokenType.COMMENT_START, tag_start, line, column))

                # Find end
                end_match = self.comment_end_pattern.search(source, pos)
                if end_match:
                    tokens.append(Token(TokenType.TEXT, source[pos:end_match.start()], line, column))
                    tokens.append(Token(TokenType.COMMENT_END, self.config.comment_end, line, column))
                    pos = end_match.end()

        tokens.append(Token(TokenType.EOF, None, line, column))
        return tokens

    def _tokenize_expression(self, expr: str, line: int, column: int) -> List[Token]:
        """Tokenize expression content."""
        tokens = []
        pos = 0
        expr = expr.strip()

        while pos < len(expr):
            # Skip whitespace
            while pos < len(expr) and expr[pos].isspace():
                pos += 1

            if pos >= len(expr):
                break

            char = expr[pos]

            # Check patterns
            remaining = expr[pos:]

            # String
            if char in '"\'':
                match = self.string_pattern.match(remaining)
                if match:
                    value = match.group()[1:-1]  # Remove quotes
                    tokens.append(Token(TokenType.STRING, value, line, column + pos))
                    pos += match.end()
                    continue

            # Number
            if char.isdigit() or (char == '-' and pos + 1 < len(expr) and expr[pos + 1].isdigit()):
                match = self.number_pattern.match(remaining)
                if match:
                    value = match.group()
                    if '.' in value:
                        tokens.append(Token(TokenType.NUMBER, float(value), line, column + pos))
                    else:
                        tokens.append(Token(TokenType.NUMBER, int(value), line, column + pos))
                    pos += match.end()
                    continue

            # Operator
            match = self.operator_pattern.match(remaining)
            if match:
                tokens.append(Token(TokenType.OPERATOR, match.group(), line, column + pos))
                pos += match.end()
                continue

            # Name
            if char.isalpha() or char == '_':
                match = self.name_pattern.match(remaining)
                if match:
                    tokens.append(Token(TokenType.NAME, match.group(), line, column + pos))
                    pos += match.end()
                    continue

            # Single character tokens
            if char == '(':
                tokens.append(Token(TokenType.LPAREN, char, line, column + pos))
            elif char == ')':
                tokens.append(Token(TokenType.RPAREN, char, line, column + pos))
            elif char == '[':
                tokens.append(Token(TokenType.LBRACKET, char, line, column + pos))
            elif char == ']':
                tokens.append(Token(TokenType.RBRACKET, char, line, column + pos))
            elif char == '.':
                tokens.append(Token(TokenType.DOT, char, line, column + pos))
            elif char == ',':
                tokens.append(Token(TokenType.COMMA, char, line, column + pos))
            elif char == '|':
                tokens.append(Token(TokenType.PIPE, char, line, column + pos))
            elif char == ':':
                tokens.append(Token(TokenType.COLON, char, line, column + pos))

            pos += 1

        return tokens


# ============================================================================
# PARSER
# ============================================================================

class Parser:
    """
    Template parser - converts tokens to AST.
    """

    def __init__(self, config: TemplateConfig):
        """Initialize parser."""
        self.config = config
        self.tokens: List[Token] = []
        self.pos = 0

    def parse(self, tokens: List[Token]) -> Node:
        """Parse tokens into AST."""
        self.tokens = tokens
        self.pos = 0

        return self._parse_template()

    def _current(self) -> Token:
        """Get current token."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, None)

    def _advance(self) -> Token:
        """Advance to next token."""
        token = self._current()
        self.pos += 1
        return token

    def _expect(self, token_type: TokenType) -> Token:
        """Expect a specific token type."""
        token = self._advance()
        if token.type != token_type:
            raise SyntaxError(
                f"Expected {token_type.value}, got {token.type.value} at line {token.line}"
            )
        return token

    def _parse_template(self) -> Node:
        """Parse template."""
        node = Node(NodeType.TEMPLATE)

        while self._current().type != TokenType.EOF:
            child = self._parse_statement()
            if child:
                node.children.append(child)

        return node

    def _parse_statement(self) -> Optional[Node]:
        """Parse a statement."""
        token = self._current()

        if token.type == TokenType.TEXT:
            self._advance()
            return Node(NodeType.TEXT, token.value, line=token.line)

        elif token.type == TokenType.VARIABLE_START:
            return self._parse_output()

        elif token.type == TokenType.BLOCK_START:
            return self._parse_block()

        elif token.type == TokenType.COMMENT_START:
            # Skip comments
            while self._current().type != TokenType.COMMENT_END:
                self._advance()
            self._advance()  # Skip comment end
            return None

        else:
            self._advance()
            return None

    def _parse_output(self) -> Node:
        """Parse output statement {{ expr }}."""
        self._expect(TokenType.VARIABLE_START)

        expr = self._parse_expression()

        self._expect(TokenType.VARIABLE_END)

        return Node(NodeType.OUTPUT, children=[expr])

    def _parse_block(self) -> Node:
        """Parse block statement {% ... %}."""
        self._expect(TokenType.BLOCK_START)

        name_token = self._advance()
        if name_token.type != TokenType.NAME:
            raise SyntaxError(f"Expected block name at line {name_token.line}")

        name = name_token.value

        if name == 'if':
            return self._parse_if()
        elif name == 'for':
            return self._parse_for()
        elif name == 'block':
            return self._parse_block_def()
        elif name == 'extends':
            return self._parse_extends()
        elif name == 'include':
            return self._parse_include()
        elif name == 'macro':
            return self._parse_macro()
        elif name == 'set':
            return self._parse_set()
        else:
            # Unknown block - skip to end
            while self._current().type != TokenType.BLOCK_END:
                self._advance()
            self._advance()
            return Node(NodeType.TEXT, '')

    def _parse_if(self) -> Node:
        """Parse if statement."""
        condition = self._parse_expression()
        self._expect(TokenType.BLOCK_END)

        node = Node(NodeType.IF)
        node.attributes['condition'] = condition
        node.attributes['else'] = []

        # Parse body
        body = []
        while True:
            token = self._current()

            if token.type == TokenType.BLOCK_START:
                # Look ahead
                next_tokens = self.tokens[self.pos:self.pos + 3]
                if len(next_tokens) >= 2 and next_tokens[1].value in ('endif', 'else', 'elif'):
                    break

            if token.type == TokenType.EOF:
                break

            stmt = self._parse_statement()
            if stmt:
                body.append(stmt)

        node.children = body

        # Handle else/elif/endif
        self._expect(TokenType.BLOCK_START)
        keyword = self._advance().value

        if keyword == 'else':
            self._expect(TokenType.BLOCK_END)

            else_body = []
            while True:
                token = self._current()

                if token.type == TokenType.BLOCK_START:
                    next_tokens = self.tokens[self.pos:self.pos + 3]
                    if len(next_tokens) >= 2 and next_tokens[1].value == 'endif':
                        break

                if token.type == TokenType.EOF:
                    break

                stmt = self._parse_statement()
                if stmt:
                    else_body.append(stmt)

            node.attributes['else'] = else_body

            self._expect(TokenType.BLOCK_START)
            self._expect(TokenType.NAME)  # endif

        self._expect(TokenType.BLOCK_END)

        return node

    def _parse_for(self) -> Node:
        """Parse for loop."""
        var_token = self._expect(TokenType.NAME)

        # Expect 'in'
        in_token = self._advance()
        if in_token.type != TokenType.NAME or in_token.value != 'in':
            raise SyntaxError(f"Expected 'in' at line {in_token.line}")

        iterable = self._parse_expression()
        self._expect(TokenType.BLOCK_END)

        node = Node(NodeType.FOR)
        node.attributes['var'] = var_token.value
        node.attributes['iterable'] = iterable

        # Parse body
        body = []
        while True:
            token = self._current()

            if token.type == TokenType.BLOCK_START:
                next_tokens = self.tokens[self.pos:self.pos + 3]
                if len(next_tokens) >= 2 and next_tokens[1].value == 'endfor':
                    break

            if token.type == TokenType.EOF:
                break

            stmt = self._parse_statement()
            if stmt:
                body.append(stmt)

        node.children = body

        self._expect(TokenType.BLOCK_START)
        self._expect(TokenType.NAME)  # endfor
        self._expect(TokenType.BLOCK_END)

        return node

    def _parse_block_def(self) -> Node:
        """Parse block definition."""
        name_token = self._expect(TokenType.NAME)
        self._expect(TokenType.BLOCK_END)

        node = Node(NodeType.BLOCK)
        node.attributes['name'] = name_token.value

        # Parse body
        body = []
        while True:
            token = self._current()

            if token.type == TokenType.BLOCK_START:
                next_tokens = self.tokens[self.pos:self.pos + 3]
                if len(next_tokens) >= 2 and next_tokens[1].value == 'endblock':
                    break

            if token.type == TokenType.EOF:
                break

            stmt = self._parse_statement()
            if stmt:
                body.append(stmt)

        node.children = body

        self._expect(TokenType.BLOCK_START)
        self._expect(TokenType.NAME)  # endblock
        self._expect(TokenType.BLOCK_END)

        return node

    def _parse_extends(self) -> Node:
        """Parse extends statement."""
        parent_token = self._expect(TokenType.STRING)
        self._expect(TokenType.BLOCK_END)

        return Node(NodeType.EXTENDS, parent_token.value)

    def _parse_include(self) -> Node:
        """Parse include statement."""
        template_token = self._expect(TokenType.STRING)
        self._expect(TokenType.BLOCK_END)

        return Node(NodeType.INCLUDE, template_token.value)

    def _parse_macro(self) -> Node:
        """Parse macro definition."""
        name_token = self._expect(TokenType.NAME)

        # Parse arguments
        args = []
        if self._current().type == TokenType.LPAREN:
            self._advance()
            while self._current().type != TokenType.RPAREN:
                if self._current().type == TokenType.NAME:
                    args.append(self._advance().value)
                elif self._current().type == TokenType.COMMA:
                    self._advance()
                else:
                    break
            self._expect(TokenType.RPAREN)

        self._expect(TokenType.BLOCK_END)

        node = Node(NodeType.MACRO)
        node.attributes['name'] = name_token.value
        node.attributes['args'] = args

        # Parse body
        body = []
        while True:
            token = self._current()

            if token.type == TokenType.BLOCK_START:
                next_tokens = self.tokens[self.pos:self.pos + 3]
                if len(next_tokens) >= 2 and next_tokens[1].value == 'endmacro':
                    break

            if token.type == TokenType.EOF:
                break

            stmt = self._parse_statement()
            if stmt:
                body.append(stmt)

        node.children = body

        self._expect(TokenType.BLOCK_START)
        self._expect(TokenType.NAME)  # endmacro
        self._expect(TokenType.BLOCK_END)

        return node

    def _parse_set(self) -> Node:
        """Parse set statement."""
        name_token = self._expect(TokenType.NAME)

        # Expect '='
        eq_token = self._advance()
        if eq_token.type != TokenType.OPERATOR or eq_token.value != '=':
            raise SyntaxError(f"Expected '=' at line {eq_token.line}")

        value = self._parse_expression()
        self._expect(TokenType.BLOCK_END)

        node = Node(NodeType.SET)
        node.attributes['name'] = name_token.value
        node.attributes['value'] = value

        return node

    def _parse_expression(self) -> Node:
        """Parse expression."""
        return self._parse_or()

    def _parse_or(self) -> Node:
        """Parse or expression."""
        left = self._parse_and()

        while self._current().type == TokenType.OPERATOR and self._current().value == 'or':
            op = self._advance().value
            right = self._parse_and()
            left = Node(NodeType.BINARY, op, children=[left, right])

        return left

    def _parse_and(self) -> Node:
        """Parse and expression."""
        left = self._parse_comparison()

        while self._current().type == TokenType.OPERATOR and self._current().value == 'and':
            op = self._advance().value
            right = self._parse_comparison()
            left = Node(NodeType.BINARY, op, children=[left, right])

        return left

    def _parse_comparison(self) -> Node:
        """Parse comparison expression."""
        left = self._parse_additive()

        ops = ('==', '!=', '<', '>', '<=', '>=', 'in', 'is')
        while self._current().type == TokenType.OPERATOR and self._current().value in ops:
            op = self._advance().value
            right = self._parse_additive()
            left = Node(NodeType.BINARY, op, children=[left, right])

        return left

    def _parse_additive(self) -> Node:
        """Parse additive expression."""
        left = self._parse_multiplicative()

        while self._current().type == TokenType.OPERATOR and self._current().value in ('+', '-'):
            op = self._advance().value
            right = self._parse_multiplicative()
            left = Node(NodeType.BINARY, op, children=[left, right])

        return left

    def _parse_multiplicative(self) -> Node:
        """Parse multiplicative expression."""
        left = self._parse_unary()

        while self._current().type == TokenType.OPERATOR and self._current().value in ('*', '/', '%'):
            op = self._advance().value
            right = self._parse_unary()
            left = Node(NodeType.BINARY, op, children=[left, right])

        return left

    def _parse_unary(self) -> Node:
        """Parse unary expression."""
        if self._current().type == TokenType.OPERATOR and self._current().value == 'not':
            op = self._advance().value
            operand = self._parse_unary()
            return Node(NodeType.UNARY, op, children=[operand])

        return self._parse_postfix()

    def _parse_postfix(self) -> Node:
        """Parse postfix expression (filters, getattr, getitem)."""
        node = self._parse_primary()

        while True:
            if self._current().type == TokenType.DOT:
                self._advance()
                attr = self._expect(TokenType.NAME).value
                node = Node(NodeType.GETATTR, attr, children=[node])

            elif self._current().type == TokenType.LBRACKET:
                self._advance()
                index = self._parse_expression()
                self._expect(TokenType.RBRACKET)
                node = Node(NodeType.GETITEM, children=[node, index])

            elif self._current().type == TokenType.PIPE:
                self._advance()
                filter_name = self._expect(TokenType.NAME).value

                args = []
                if self._current().type == TokenType.LPAREN:
                    self._advance()
                    while self._current().type != TokenType.RPAREN:
                        args.append(self._parse_expression())
                        if self._current().type == TokenType.COMMA:
                            self._advance()
                    self._expect(TokenType.RPAREN)

                node = Node(NodeType.FILTER, filter_name, children=[node] + args)

            elif self._current().type == TokenType.LPAREN:
                # Function call
                self._advance()
                args = []
                while self._current().type != TokenType.RPAREN:
                    args.append(self._parse_expression())
                    if self._current().type == TokenType.COMMA:
                        self._advance()
                self._expect(TokenType.RPAREN)
                node = Node(NodeType.CALL, children=[node] + args)

            else:
                break

        return node

    def _parse_primary(self) -> Node:
        """Parse primary expression."""
        token = self._current()

        if token.type == TokenType.NAME:
            self._advance()
            return Node(NodeType.NAME, token.value)

        elif token.type == TokenType.STRING:
            self._advance()
            return Node(NodeType.LITERAL, token.value)

        elif token.type == TokenType.NUMBER:
            self._advance()
            return Node(NodeType.LITERAL, token.value)

        elif token.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expression()
            self._expect(TokenType.RPAREN)
            return expr

        elif token.type == TokenType.LBRACKET:
            # List literal
            self._advance()
            items = []
            while self._current().type != TokenType.RBRACKET:
                items.append(self._parse_expression())
                if self._current().type == TokenType.COMMA:
                    self._advance()
            self._expect(TokenType.RBRACKET)
            return Node(NodeType.LITERAL, items)

        else:
            return Node(NodeType.LITERAL, None)


# ============================================================================
# COMPILER
# ============================================================================

class Compiler:
    """
    Compiles AST to executable code.
    """

    def __init__(self, config: TemplateConfig):
        """Initialize compiler."""
        self.config = config

    def compile(self, ast: Node, template_name: str) -> Callable:
        """Compile AST to function."""
        code = self._compile_node(ast)

        # Create function
        func_code = f"""
def render(context, engine):
    output = []
    {code}
    return ''.join(str(x) for x in output)
"""

        local_vars = {}
        exec(func_code, {'escape': self._escape}, local_vars)

        return local_vars['render']

    def _compile_node(self, node: Node, indent: int = 1) -> str:
        """Compile a node."""
        prefix = '    ' * indent

        if node.type == NodeType.TEMPLATE:
            return '\n'.join(self._compile_node(c, indent) for c in node.children)

        elif node.type == NodeType.TEXT:
            text = repr(node.value)
            return f"{prefix}output.append({text})"

        elif node.type == NodeType.OUTPUT:
            expr = self._compile_expr(node.children[0])
            if self.config.auto_escape == AutoEscapeMode.HTML:
                return f"{prefix}output.append(escape({expr}))"
            return f"{prefix}output.append({expr})"

        elif node.type == NodeType.IF:
            condition = self._compile_expr(node.attributes['condition'])
            body = '\n'.join(self._compile_node(c, indent + 1) for c in node.children)

            code = f"{prefix}if {condition}:\n{body}"

            if node.attributes.get('else'):
                else_body = '\n'.join(
                    self._compile_node(c, indent + 1) for c in node.attributes['else']
                )
                code += f"\n{prefix}else:\n{else_body}"

            return code

        elif node.type == NodeType.FOR:
            var = node.attributes['var']
            iterable = self._compile_expr(node.attributes['iterable'])
            body = '\n'.join(self._compile_node(c, indent + 1) for c in node.children)

            return f"{prefix}for {var} in {iterable}:\n{body}"

        elif node.type == NodeType.SET:
            name = node.attributes['name']
            value = self._compile_expr(node.attributes['value'])
            return f"{prefix}context['{name}'] = {value}"

        elif node.type == NodeType.BLOCK:
            # Blocks are handled specially for inheritance
            body = '\n'.join(self._compile_node(c, indent) for c in node.children)
            return body

        return ""

    def _compile_expr(self, node: Node) -> str:
        """Compile expression node."""
        if node.type == NodeType.NAME:
            return f"context.get('{node.value}', '')"

        elif node.type == NodeType.LITERAL:
            return repr(node.value)

        elif node.type == NodeType.BINARY:
            left = self._compile_expr(node.children[0])
            right = self._compile_expr(node.children[1])
            op = node.value

            if op == 'and':
                return f"({left} and {right})"
            elif op == 'or':
                return f"({left} or {right})"
            elif op == 'in':
                return f"({left} in {right})"
            else:
                return f"({left} {op} {right})"

        elif node.type == NodeType.UNARY:
            operand = self._compile_expr(node.children[0])
            if node.value == 'not':
                return f"(not {operand})"
            return operand

        elif node.type == NodeType.GETATTR:
            obj = self._compile_expr(node.children[0])
            attr = node.value
            return f"getattr({obj}, '{attr}', '')"

        elif node.type == NodeType.GETITEM:
            obj = self._compile_expr(node.children[0])
            index = self._compile_expr(node.children[1])
            return f"({obj}[{index}] if {index} in {obj} else '')"

        elif node.type == NodeType.FILTER:
            value = self._compile_expr(node.children[0])
            filter_name = node.value

            args = ', '.join(self._compile_expr(c) for c in node.children[1:])

            return f"engine.apply_filter('{filter_name}', {value}, {args})"

        return "''"

    def _escape(self, value: Any) -> str:
        """Escape a value."""
        if value is None:
            return ''
        return html.escape(str(value))


# ============================================================================
# ENVIRONMENT
# ============================================================================

class Environment:
    """
    Template environment with filters and globals.
    """

    def __init__(self):
        """Initialize environment."""
        self.filters: Dict[str, Callable] = {}
        self.globals: Dict[str, Any] = {}

        # Register default filters
        self._register_default_filters()

    def _register_default_filters(self) -> None:
        """Register default filters."""
        self.filters['upper'] = lambda x: str(x).upper()
        self.filters['lower'] = lambda x: str(x).lower()
        self.filters['title'] = lambda x: str(x).title()
        self.filters['capitalize'] = lambda x: str(x).capitalize()
        self.filters['strip'] = lambda x: str(x).strip()
        self.filters['length'] = lambda x: len(x)
        self.filters['first'] = lambda x: x[0] if x else ''
        self.filters['last'] = lambda x: x[-1] if x else ''
        self.filters['join'] = lambda x, sep='': sep.join(str(i) for i in x)
        self.filters['default'] = lambda x, d='': x if x else d
        self.filters['escape'] = lambda x: html.escape(str(x))
        self.filters['safe'] = lambda x: x  # Mark as safe
        self.filters['int'] = lambda x: int(x) if x else 0
        self.filters['float'] = lambda x: float(x) if x else 0.0
        self.filters['string'] = lambda x: str(x)
        self.filters['list'] = lambda x: list(x)
        self.filters['reverse'] = lambda x: x[::-1]
        self.filters['sort'] = lambda x: sorted(x)
        self.filters['sum'] = lambda x: sum(x)
        self.filters['min'] = lambda x: min(x) if x else None
        self.filters['max'] = lambda x: max(x) if x else None
        self.filters['abs'] = lambda x: abs(x)
        self.filters['round'] = lambda x, n=0: round(x, n)
        self.filters['truncate'] = lambda x, n=80: str(x)[:n] + ('...' if len(str(x)) > n else '')
        self.filters['wordcount'] = lambda x: len(str(x).split())
        self.filters['center'] = lambda x, n=80: str(x).center(n)
        self.filters['format'] = lambda x, *a: str(x) % a if a else str(x)
        self.filters['batch'] = lambda x, n: [x[i:i+n] for i in range(0, len(x), n)]

    def add_filter(self, name: str, func: Callable) -> None:
        """Add a filter."""
        self.filters[name] = func

    def apply_filter(self, name: str, value: Any, *args) -> Any:
        """Apply a filter."""
        if name in self.filters:
            return self.filters[name](value, *args)
        return value


# ============================================================================
# MAIN TEMPLATE ENGINE
# ============================================================================

class TemplateEngine:
    """
    Main template engine.

    Features:
    - Variable substitution
    - Control structures
    - Template inheritance
    - Filters and macros

    "Ba'el renders reality from templates of thought." — Ba'el
    """

    def __init__(self, config: Optional[TemplateConfig] = None):
        """Initialize template engine."""
        self.config = config or TemplateConfig()

        # Components
        self.lexer = Lexer(self.config)
        self.parser = Parser(self.config)
        self.compiler = Compiler(self.config)
        self.environment = Environment()

        # Template cache
        self._cache: Dict[str, Template] = {}
        self._compiled: Dict[str, Callable] = {}

        self._lock = threading.RLock()

        logger.info("TemplateEngine initialized")

    def add_filter(self, name: str, func: Callable) -> None:
        """Add a filter."""
        self.environment.add_filter(name, func)

    def apply_filter(self, name: str, value: Any, *args) -> Any:
        """Apply a filter."""
        return self.environment.apply_filter(name, value, *args)

    def compile(self, source: str, name: str = "template") -> Template:
        """Compile a template."""
        tokens = self.lexer.tokenize(source)
        ast = self.parser.parse(tokens)

        template = Template(
            name=name,
            source=source,
            ast=ast,
            compiled_at=datetime.now()
        )

        # Extract blocks and macros
        self._extract_blocks(ast, template)

        # Compile
        compiled = self.compiler.compile(ast, name)

        with self._lock:
            self._cache[name] = template
            self._compiled[name] = compiled

        return template

    def _extract_blocks(self, node: Node, template: Template) -> None:
        """Extract blocks and macros from AST."""
        if node.type == NodeType.BLOCK:
            template.blocks[node.attributes['name']] = node

        elif node.type == NodeType.MACRO:
            template.macros[node.attributes['name']] = node

        elif node.type == NodeType.EXTENDS:
            template.parent = node.value

        for child in node.children:
            self._extract_blocks(child, template)

    def render(self, source: str, context: Optional[Dict[str, Any]] = None, name: str = "template") -> str:
        """Compile and render a template."""
        template = self.compile(source, name)
        return self.render_template(template, context or {})

    def render_template(self, template: Template, context: Dict[str, Any]) -> str:
        """Render a compiled template."""
        # Merge environment globals
        full_context = {**self.environment.globals, **context}

        with self._lock:
            compiled = self._compiled.get(template.name)

        if not compiled:
            compiled = self.compiler.compile(template.ast, template.name)
            with self._lock:
                self._compiled[template.name] = compiled

        return compiled(full_context, self)

    def load_template(self, name: str) -> Optional[Template]:
        """Load a template from file."""
        # Check cache
        with self._lock:
            if name in self._cache and self.config.cache_enabled:
                return self._cache[name]

        # Search paths
        for path in self.config.template_paths:
            filepath = os.path.join(path, name)
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    source = f.read()
                return self.compile(source, name)

        return None

    def render_file(self, name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Load and render a template file."""
        template = self.load_template(name)
        if not template:
            raise FileNotFoundError(f"Template not found: {name}")
        return self.render_template(template, context or {})

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'cached_templates': len(self._cache),
            'compiled_templates': len(self._compiled),
            'filters': len(self.environment.filters),
            'template_paths': self.config.template_paths
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

template_engine = TemplateEngine()
