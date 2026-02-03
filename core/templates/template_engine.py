#!/usr/bin/env python3
"""
BAEL - Template Engine
Comprehensive text templating and rendering system.

This module provides a complete template engine for
dynamic text generation and rendering.

Features:
- Variable substitution
- Control structures (if/for/while)
- Template inheritance
- Filters and functions
- Custom delimiters
- Template caching
- Includes and extends
- Macros and blocks
- Auto-escaping
- Template compilation
"""

import asyncio
import hashlib
import html
import json
import logging
import os
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from functools import lru_cache
from pathlib import Path
from typing import (
    Any, Awaitable, Callable, Dict, Generic, List, Optional, Pattern,
    Set, Tuple, Type, TypeVar, Union
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class TokenType(Enum):
    """Template token types."""
    TEXT = "text"
    VAR = "var"
    BLOCK = "block"
    COMMENT = "comment"


class NodeType(Enum):
    """AST node types."""
    ROOT = "root"
    TEXT = "text"
    VAR = "var"
    IF = "if"
    ELIF = "elif"
    ELSE = "else"
    FOR = "for"
    BLOCK = "block"
    EXTENDS = "extends"
    INCLUDE = "include"
    MACRO = "macro"
    CALL = "call"
    SET = "set"
    RAW = "raw"


class EscapeMode(Enum):
    """Auto-escape modes."""
    NONE = "none"
    HTML = "html"
    JSON = "json"
    URL = "url"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Token:
    """A template token."""
    type: TokenType
    value: str
    line: int = 0
    col: int = 0


@dataclass
class ASTNode:
    """Abstract syntax tree node."""
    type: NodeType
    value: Any = None
    children: List['ASTNode'] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TemplateContext:
    """Template rendering context."""
    variables: Dict[str, Any] = field(default_factory=dict)
    parent: Optional['TemplateContext'] = None

    def get(self, key: str, default: Any = None) -> Any:
        """Get variable with dot notation support."""
        keys = key.split('.')
        value = self.variables.get(keys[0])

        if value is None and self.parent:
            return self.parent.get(key, default)

        for k in keys[1:]:
            if isinstance(value, dict):
                value = value.get(k)
            elif hasattr(value, k):
                value = getattr(value, k)
            else:
                return default

            if value is None:
                return default

        return value if value is not None else default

    def set(self, key: str, value: Any) -> None:
        """Set a variable."""
        self.variables[key] = value

    def child(self) -> 'TemplateContext':
        """Create child context."""
        return TemplateContext(parent=self)


@dataclass
class CompiledTemplate:
    """A compiled template."""
    source: str
    ast: ASTNode
    compiled_at: float = field(default_factory=time.time)
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            self.hash = hashlib.md5(self.source.encode()).hexdigest()


# =============================================================================
# FILTERS
# =============================================================================

class FilterRegistry:
    """Registry of template filters."""

    def __init__(self):
        self.filters: Dict[str, Callable] = {}
        self._register_builtins()

    def _register_builtins(self):
        """Register built-in filters."""
        self.register("upper", lambda x: str(x).upper())
        self.register("lower", lambda x: str(x).lower())
        self.register("title", lambda x: str(x).title())
        self.register("capitalize", lambda x: str(x).capitalize())
        self.register("strip", lambda x: str(x).strip())
        self.register("trim", lambda x: str(x).strip())
        self.register("escape", lambda x: html.escape(str(x)))
        self.register("safe", lambda x: x)  # Mark as safe
        self.register("length", lambda x: len(x))
        self.register("default", lambda x, d="": x if x else d)
        self.register("first", lambda x: x[0] if x else None)
        self.register("last", lambda x: x[-1] if x else None)
        self.register("join", lambda x, sep=", ": sep.join(str(i) for i in x))
        self.register("split", lambda x, sep=" ": str(x).split(sep))
        self.register("reverse", lambda x: list(reversed(x)) if isinstance(x, list) else str(x)[::-1])
        self.register("sort", lambda x: sorted(x))
        self.register("unique", lambda x: list(dict.fromkeys(x)))
        self.register("int", lambda x: int(x))
        self.register("float", lambda x: float(x))
        self.register("str", lambda x: str(x))
        self.register("bool", lambda x: bool(x))
        self.register("abs", lambda x: abs(x))
        self.register("round", lambda x, n=0: round(float(x), n))
        self.register("format", lambda x, fmt: fmt.format(x))
        self.register("date", lambda x, fmt="%Y-%m-%d": x.strftime(fmt) if hasattr(x, 'strftime') else str(x))
        self.register("replace", lambda x, old, new: str(x).replace(old, new))
        self.register("truncate", lambda x, n=100, end="...": str(x)[:n] + end if len(str(x)) > n else str(x))
        self.register("wordwrap", lambda x, n=80: self._wordwrap(x, n))
        self.register("nl2br", lambda x: str(x).replace("\n", "<br>"))
        self.register("json", lambda x: json.dumps(x))
        self.register("batch", lambda x, n=10: [x[i:i+n] for i in range(0, len(x), n)])
        self.register("slice", lambda x, start=0, end=None: x[start:end])
        self.register("map", lambda x, attr: [getattr(i, attr, i.get(attr) if isinstance(i, dict) else None) for i in x])
        self.register("select", lambda x, attr: [i for i in x if getattr(i, attr, i.get(attr) if isinstance(i, dict) else None)])
        self.register("reject", lambda x, attr: [i for i in x if not getattr(i, attr, i.get(attr) if isinstance(i, dict) else None)])

    def _wordwrap(self, text: str, width: int) -> str:
        """Word wrap text."""
        words = str(text).split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 <= width:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)

        if current_line:
            lines.append(" ".join(current_line))

        return "\n".join(lines)

    def register(self, name: str, func: Callable) -> None:
        """Register a filter."""
        self.filters[name] = func

    def get(self, name: str) -> Optional[Callable]:
        """Get a filter."""
        return self.filters.get(name)

    def apply(self, name: str, value: Any, *args, **kwargs) -> Any:
        """Apply a filter."""
        func = self.get(name)
        if func:
            return func(value, *args, **kwargs)
        return value


# =============================================================================
# LEXER
# =============================================================================

class TemplateLexer:
    """Template lexer for tokenizing templates."""

    def __init__(
        self,
        var_start: str = "{{",
        var_end: str = "}}",
        block_start: str = "{%",
        block_end: str = "%}",
        comment_start: str = "{#",
        comment_end: str = "#}"
    ):
        self.var_start = var_start
        self.var_end = var_end
        self.block_start = block_start
        self.block_end = block_end
        self.comment_start = comment_start
        self.comment_end = comment_end

        self._build_patterns()

    def _build_patterns(self):
        """Build regex patterns."""
        self.token_pattern = re.compile(
            r'(' +
            re.escape(self.var_start) + r'.*?' + re.escape(self.var_end) + r'|' +
            re.escape(self.block_start) + r'.*?' + re.escape(self.block_end) + r'|' +
            re.escape(self.comment_start) + r'.*?' + re.escape(self.comment_end) +
            r')',
            re.DOTALL
        )

    def tokenize(self, source: str) -> List[Token]:
        """Tokenize template source."""
        tokens = []
        line = 1
        col = 1

        parts = self.token_pattern.split(source)

        for part in parts:
            if not part:
                continue

            if part.startswith(self.var_start) and part.endswith(self.var_end):
                content = part[len(self.var_start):-len(self.var_end)].strip()
                tokens.append(Token(TokenType.VAR, content, line, col))

            elif part.startswith(self.block_start) and part.endswith(self.block_end):
                content = part[len(self.block_start):-len(self.block_end)].strip()
                tokens.append(Token(TokenType.BLOCK, content, line, col))

            elif part.startswith(self.comment_start) and part.endswith(self.comment_end):
                content = part[len(self.comment_start):-len(self.comment_end)].strip()
                tokens.append(Token(TokenType.COMMENT, content, line, col))

            else:
                tokens.append(Token(TokenType.TEXT, part, line, col))

            # Update position
            for char in part:
                if char == '\n':
                    line += 1
                    col = 1
                else:
                    col += 1

        return tokens


# =============================================================================
# PARSER
# =============================================================================

class TemplateParser:
    """Template parser for building AST."""

    BLOCK_KEYWORDS = {
        'if', 'elif', 'else', 'endif',
        'for', 'endfor',
        'block', 'endblock',
        'macro', 'endmacro',
        'raw', 'endraw',
        'extends', 'include', 'set', 'call'
    }

    def __init__(self):
        self.tokens: List[Token] = []
        self.pos = 0

    def parse(self, tokens: List[Token]) -> ASTNode:
        """Parse tokens into AST."""
        self.tokens = tokens
        self.pos = 0

        root = ASTNode(NodeType.ROOT)
        root.children = self._parse_nodes()

        return root

    def _current(self) -> Optional[Token]:
        """Get current token."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _advance(self) -> Optional[Token]:
        """Advance to next token."""
        token = self._current()
        self.pos += 1
        return token

    def _parse_nodes(
        self,
        end_keywords: Set[str] = None
    ) -> List[ASTNode]:
        """Parse multiple nodes."""
        nodes = []
        end_keywords = end_keywords or set()

        while self.pos < len(self.tokens):
            token = self._current()

            if token.type == TokenType.BLOCK:
                keyword = self._get_keyword(token.value)

                if keyword in end_keywords:
                    break

                node = self._parse_block(token)
                if node:
                    nodes.append(node)

            elif token.type == TokenType.VAR:
                nodes.append(self._parse_var(token))

            elif token.type == TokenType.TEXT:
                nodes.append(ASTNode(NodeType.TEXT, token.value))
                self._advance()

            elif token.type == TokenType.COMMENT:
                self._advance()

            else:
                self._advance()

        return nodes

    def _get_keyword(self, value: str) -> str:
        """Extract keyword from block value."""
        parts = value.split(None, 1)
        return parts[0] if parts else ""

    def _parse_var(self, token: Token) -> ASTNode:
        """Parse variable node."""
        self._advance()

        # Parse filters
        parts = token.value.split('|')
        var_expr = parts[0].strip()
        filters = [f.strip() for f in parts[1:]]

        node = ASTNode(NodeType.VAR, var_expr)
        node.attributes['filters'] = filters

        return node

    def _parse_block(self, token: Token) -> Optional[ASTNode]:
        """Parse block node."""
        self._advance()

        keyword = self._get_keyword(token.value)
        rest = token.value[len(keyword):].strip()

        if keyword == 'if':
            return self._parse_if(rest)
        elif keyword == 'for':
            return self._parse_for(rest)
        elif keyword == 'block':
            return self._parse_block_tag(rest)
        elif keyword == 'extends':
            return ASTNode(NodeType.EXTENDS, rest.strip('"\''))
        elif keyword == 'include':
            return ASTNode(NodeType.INCLUDE, rest.strip('"\''))
        elif keyword == 'set':
            return self._parse_set(rest)
        elif keyword == 'macro':
            return self._parse_macro(rest)
        elif keyword == 'call':
            return ASTNode(NodeType.CALL, rest)
        elif keyword == 'raw':
            return self._parse_raw()

        return None

    def _parse_if(self, condition: str) -> ASTNode:
        """Parse if block."""
        node = ASTNode(NodeType.IF, condition)

        node.children = self._parse_nodes({'elif', 'else', 'endif'})

        # Handle elif/else
        while self.pos < len(self.tokens):
            token = self._current()
            if token.type != TokenType.BLOCK:
                break

            keyword = self._get_keyword(token.value)

            if keyword == 'elif':
                self._advance()
                rest = token.value[4:].strip()
                elif_node = ASTNode(NodeType.ELIF, rest)
                elif_node.children = self._parse_nodes({'elif', 'else', 'endif'})
                node.children.append(elif_node)

            elif keyword == 'else':
                self._advance()
                else_node = ASTNode(NodeType.ELSE)
                else_node.children = self._parse_nodes({'endif'})
                node.children.append(else_node)

            elif keyword == 'endif':
                self._advance()
                break

            else:
                break

        return node

    def _parse_for(self, expression: str) -> ASTNode:
        """Parse for loop."""
        # Parse: item in items
        parts = expression.split(' in ', 1)
        if len(parts) != 2:
            raise SyntaxError(f"Invalid for syntax: {expression}")

        var_name = parts[0].strip()
        iterable = parts[1].strip()

        node = ASTNode(NodeType.FOR)
        node.attributes['var'] = var_name
        node.attributes['iterable'] = iterable

        node.children = self._parse_nodes({'endfor'})

        # Consume endfor
        if self._current() and self._get_keyword(self._current().value) == 'endfor':
            self._advance()

        return node

    def _parse_block_tag(self, name: str) -> ASTNode:
        """Parse block tag."""
        node = ASTNode(NodeType.BLOCK, name.strip())
        node.children = self._parse_nodes({'endblock'})

        if self._current() and self._get_keyword(self._current().value) == 'endblock':
            self._advance()

        return node

    def _parse_set(self, expression: str) -> ASTNode:
        """Parse set statement."""
        parts = expression.split('=', 1)
        if len(parts) != 2:
            raise SyntaxError(f"Invalid set syntax: {expression}")

        node = ASTNode(NodeType.SET)
        node.attributes['var'] = parts[0].strip()
        node.attributes['value'] = parts[1].strip()

        return node

    def _parse_macro(self, signature: str) -> ASTNode:
        """Parse macro definition."""
        # Parse: name(arg1, arg2)
        match = re.match(r'(\w+)\s*\((.*)\)', signature)
        if not match:
            raise SyntaxError(f"Invalid macro syntax: {signature}")

        node = ASTNode(NodeType.MACRO, match.group(1))
        args = [a.strip() for a in match.group(2).split(',') if a.strip()]
        node.attributes['args'] = args

        node.children = self._parse_nodes({'endmacro'})

        if self._current() and self._get_keyword(self._current().value) == 'endmacro':
            self._advance()

        return node

    def _parse_raw(self) -> ASTNode:
        """Parse raw block."""
        content = []

        while self.pos < len(self.tokens):
            token = self._advance()

            if token.type == TokenType.BLOCK and self._get_keyword(token.value) == 'endraw':
                break

            content.append(token.value if token.type == TokenType.TEXT else str(token.value))

        return ASTNode(NodeType.RAW, ''.join(content))


# =============================================================================
# EXPRESSION EVALUATOR
# =============================================================================

class ExpressionEvaluator:
    """Evaluates template expressions."""

    def __init__(self, filters: FilterRegistry):
        self.filters = filters

    def evaluate(self, expr: str, context: TemplateContext) -> Any:
        """Evaluate an expression."""
        expr = expr.strip()

        # Handle literals
        if expr.startswith('"') and expr.endswith('"'):
            return expr[1:-1]
        if expr.startswith("'") and expr.endswith("'"):
            return expr[1:-1]

        # Handle numbers
        try:
            if '.' in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass

        # Handle booleans
        if expr.lower() == 'true':
            return True
        if expr.lower() == 'false':
            return False
        if expr.lower() == 'none':
            return None

        # Handle lists
        if expr.startswith('[') and expr.endswith(']'):
            inner = expr[1:-1]
            if not inner.strip():
                return []
            items = self._split_list(inner)
            return [self.evaluate(i.strip(), context) for i in items]

        # Handle dicts
        if expr.startswith('{') and expr.endswith('}'):
            inner = expr[1:-1]
            if not inner.strip():
                return {}
            result = {}
            for pair in self._split_list(inner):
                key, value = pair.split(':', 1)
                result[self.evaluate(key.strip(), context)] = self.evaluate(value.strip(), context)
            return result

        # Handle comparisons
        for op in ['==', '!=', '>=', '<=', '>', '<', ' in ', ' not in ', ' and ', ' or ']:
            if op in expr:
                return self._evaluate_comparison(expr, op, context)

        # Handle negation
        if expr.startswith('not '):
            return not self.evaluate(expr[4:], context)

        # Handle variable access
        return context.get(expr)

    def _split_list(self, s: str) -> List[str]:
        """Split list items respecting nesting."""
        items = []
        current = []
        depth = 0

        for char in s:
            if char == ',' and depth == 0:
                items.append(''.join(current))
                current = []
            else:
                current.append(char)
                if char in '[{(':
                    depth += 1
                elif char in ']})':
                    depth -= 1

        if current:
            items.append(''.join(current))

        return items

    def _evaluate_comparison(
        self,
        expr: str,
        op: str,
        context: TemplateContext
    ) -> bool:
        """Evaluate comparison expression."""
        parts = expr.split(op, 1)
        left = self.evaluate(parts[0].strip(), context)
        right = self.evaluate(parts[1].strip(), context)

        if op == '==':
            return left == right
        elif op == '!=':
            return left != right
        elif op == '>=':
            return left >= right
        elif op == '<=':
            return left <= right
        elif op == '>':
            return left > right
        elif op == '<':
            return left < right
        elif op == ' in ':
            return left in right
        elif op == ' not in ':
            return left not in right
        elif op == ' and ':
            return bool(left) and bool(right)
        elif op == ' or ':
            return bool(left) or bool(right)

        return False

    def apply_filters(
        self,
        value: Any,
        filter_chain: List[str],
        context: TemplateContext
    ) -> Any:
        """Apply filter chain to value."""
        for filter_str in filter_chain:
            # Parse filter name and arguments
            match = re.match(r'(\w+)(?:\((.*)\))?', filter_str)
            if not match:
                continue

            name = match.group(1)
            args_str = match.group(2)

            args = []
            kwargs = {}

            if args_str:
                for arg in self._split_list(args_str):
                    arg = arg.strip()
                    if '=' in arg:
                        k, v = arg.split('=', 1)
                        kwargs[k.strip()] = self.evaluate(v.strip(), context)
                    else:
                        args.append(self.evaluate(arg, context))

            value = self.filters.apply(name, value, *args, **kwargs)

        return value


# =============================================================================
# RENDERER
# =============================================================================

class TemplateRenderer:
    """Renders template AST."""

    def __init__(
        self,
        filters: FilterRegistry,
        escape_mode: EscapeMode = EscapeMode.HTML
    ):
        self.filters = filters
        self.evaluator = ExpressionEvaluator(filters)
        self.escape_mode = escape_mode
        self.macros: Dict[str, ASTNode] = {}
        self.blocks: Dict[str, ASTNode] = {}

    def render(self, ast: ASTNode, context: TemplateContext) -> str:
        """Render AST to string."""
        return self._render_node(ast, context)

    def _render_node(self, node: ASTNode, context: TemplateContext) -> str:
        """Render a single node."""
        if node.type == NodeType.ROOT:
            return self._render_children(node, context)

        elif node.type == NodeType.TEXT:
            return node.value

        elif node.type == NodeType.VAR:
            return self._render_var(node, context)

        elif node.type == NodeType.IF:
            return self._render_if(node, context)

        elif node.type == NodeType.FOR:
            return self._render_for(node, context)

        elif node.type == NodeType.BLOCK:
            return self._render_block(node, context)

        elif node.type == NodeType.SET:
            return self._render_set(node, context)

        elif node.type == NodeType.MACRO:
            return self._register_macro(node)

        elif node.type == NodeType.CALL:
            return self._call_macro(node, context)

        elif node.type == NodeType.RAW:
            return node.value

        return ""

    def _render_children(
        self,
        node: ASTNode,
        context: TemplateContext
    ) -> str:
        """Render all children."""
        return ''.join(self._render_node(child, context) for child in node.children)

    def _render_var(self, node: ASTNode, context: TemplateContext) -> str:
        """Render variable."""
        value = self.evaluator.evaluate(node.value, context)

        # Apply filters
        filters = node.attributes.get('filters', [])
        if filters:
            value = self.evaluator.apply_filters(value, filters, context)

        # Auto-escape
        if self.escape_mode == EscapeMode.HTML:
            if 'safe' not in filters and isinstance(value, str):
                value = html.escape(value)

        return str(value) if value is not None else ""

    def _render_if(self, node: ASTNode, context: TemplateContext) -> str:
        """Render if block."""
        condition = self.evaluator.evaluate(node.value, context)

        if condition:
            # Render main if body (non-elif/else children)
            return ''.join(
                self._render_node(child, context)
                for child in node.children
                if child.type not in (NodeType.ELIF, NodeType.ELSE)
            )

        # Check elif/else
        for child in node.children:
            if child.type == NodeType.ELIF:
                elif_condition = self.evaluator.evaluate(child.value, context)
                if elif_condition:
                    return self._render_children(child, context)

            elif child.type == NodeType.ELSE:
                return self._render_children(child, context)

        return ""

    def _render_for(self, node: ASTNode, context: TemplateContext) -> str:
        """Render for loop."""
        var_name = node.attributes['var']
        iterable_expr = node.attributes['iterable']
        iterable = self.evaluator.evaluate(iterable_expr, context)

        if not iterable:
            return ""

        result = []
        items = list(iterable)

        for i, item in enumerate(items):
            loop_context = context.child()
            loop_context.set(var_name, item)

            # Loop metadata
            loop_context.set('loop', {
                'index': i + 1,
                'index0': i,
                'first': i == 0,
                'last': i == len(items) - 1,
                'length': len(items)
            })

            result.append(self._render_children(node, loop_context))

        return ''.join(result)

    def _render_block(self, node: ASTNode, context: TemplateContext) -> str:
        """Render block."""
        block_name = node.value

        # Check for override
        if block_name in self.blocks:
            return self._render_children(self.blocks[block_name], context)

        return self._render_children(node, context)

    def _render_set(self, node: ASTNode, context: TemplateContext) -> str:
        """Render set statement."""
        var_name = node.attributes['var']
        value = self.evaluator.evaluate(node.attributes['value'], context)
        context.set(var_name, value)
        return ""

    def _register_macro(self, node: ASTNode) -> str:
        """Register macro."""
        self.macros[node.value] = node
        return ""

    def _call_macro(self, node: ASTNode, context: TemplateContext) -> str:
        """Call macro."""
        # Parse call: name(arg1, arg2)
        match = re.match(r'(\w+)\s*\((.*)\)', node.value)
        if not match:
            return ""

        name = match.group(1)
        args_str = match.group(2)

        macro = self.macros.get(name)
        if not macro:
            return ""

        # Build macro context
        macro_context = context.child()

        # Parse arguments
        arg_values = [
            self.evaluator.evaluate(a.strip(), context)
            for a in args_str.split(',') if a.strip()
        ]

        # Bind arguments
        for i, arg_name in enumerate(macro.attributes.get('args', [])):
            if i < len(arg_values):
                macro_context.set(arg_name, arg_values[i])

        return self._render_children(macro, macro_context)


# =============================================================================
# TEMPLATE ENGINE
# =============================================================================

class TemplateEngine:
    """
    Core template engine.
    """

    def __init__(
        self,
        template_dirs: List[str] = None,
        escape_mode: EscapeMode = EscapeMode.HTML
    ):
        self.template_dirs = template_dirs or []
        self.escape_mode = escape_mode

        # Components
        self.lexer = TemplateLexer()
        self.parser = TemplateParser()
        self.filters = FilterRegistry()

        # Cache
        self.cache: Dict[str, CompiledTemplate] = {}
        self.cache_enabled = True

    def compile(self, source: str) -> CompiledTemplate:
        """Compile template source."""
        tokens = self.lexer.tokenize(source)
        ast = self.parser.parse(tokens)

        return CompiledTemplate(source=source, ast=ast)

    def render(
        self,
        source: str,
        context: Dict[str, Any] = None
    ) -> str:
        """Render template source."""
        compiled = self.compile(source)
        ctx = TemplateContext(variables=context or {})

        renderer = TemplateRenderer(self.filters, self.escape_mode)
        return renderer.render(compiled.ast, ctx)

    def render_file(
        self,
        template_name: str,
        context: Dict[str, Any] = None
    ) -> str:
        """Render template from file."""
        source = self._load_template(template_name)

        # Check cache
        if self.cache_enabled and template_name in self.cache:
            cached = self.cache[template_name]
            current_hash = hashlib.md5(source.encode()).hexdigest()

            if cached.hash == current_hash:
                ctx = TemplateContext(variables=context or {})
                renderer = TemplateRenderer(self.filters, self.escape_mode)
                return renderer.render(cached.ast, ctx)

        # Compile and cache
        compiled = self.compile(source)
        self.cache[template_name] = compiled

        ctx = TemplateContext(variables=context or {})
        renderer = TemplateRenderer(self.filters, self.escape_mode)

        # Handle extends
        extends_node = self._find_extends(compiled.ast)
        if extends_node:
            return self._render_with_extends(compiled, extends_node, ctx, renderer)

        return renderer.render(compiled.ast, ctx)

    def _load_template(self, name: str) -> str:
        """Load template from file."""
        for dir_path in self.template_dirs:
            path = Path(dir_path) / name
            if path.exists():
                return path.read_text()

        raise FileNotFoundError(f"Template not found: {name}")

    def _find_extends(self, ast: ASTNode) -> Optional[ASTNode]:
        """Find extends node in AST."""
        for child in ast.children:
            if child.type == NodeType.EXTENDS:
                return child
        return None

    def _render_with_extends(
        self,
        child_template: CompiledTemplate,
        extends_node: ASTNode,
        context: TemplateContext,
        renderer: TemplateRenderer
    ) -> str:
        """Render template with inheritance."""
        parent_source = self._load_template(extends_node.value)
        parent_compiled = self.compile(parent_source)

        # Collect child blocks
        self._collect_blocks(child_template.ast, renderer.blocks)

        return renderer.render(parent_compiled.ast, context)

    def _collect_blocks(
        self,
        node: ASTNode,
        blocks: Dict[str, ASTNode]
    ) -> None:
        """Collect block definitions."""
        for child in node.children:
            if child.type == NodeType.BLOCK:
                blocks[child.value] = child
            self._collect_blocks(child, blocks)

    def register_filter(self, name: str, func: Callable) -> None:
        """Register a custom filter."""
        self.filters.register(name, func)

    def add_template_dir(self, path: str) -> None:
        """Add template directory."""
        self.template_dirs.append(path)

    def clear_cache(self) -> None:
        """Clear template cache."""
        self.cache.clear()


# =============================================================================
# TEMPLATE ENGINE MANAGER
# =============================================================================

class TemplateEngineManager:
    """
    Master template engine manager for BAEL.
    """

    def __init__(self, template_dirs: List[str] = None):
        self.engine = TemplateEngine(template_dirs or [])
        self.globals: Dict[str, Any] = {}

    def add_template_dir(self, path: str) -> None:
        """Add template directory."""
        self.engine.add_template_dir(path)

    def register_filter(self, name: str, func: Callable) -> None:
        """Register custom filter."""
        self.engine.register_filter(name, func)

    def set_global(self, name: str, value: Any) -> None:
        """Set global variable."""
        self.globals[name] = value

    def render(
        self,
        source: str,
        context: Dict[str, Any] = None
    ) -> str:
        """Render template string."""
        ctx = {**self.globals, **(context or {})}
        return self.engine.render(source, ctx)

    def render_file(
        self,
        template_name: str,
        context: Dict[str, Any] = None
    ) -> str:
        """Render template file."""
        ctx = {**self.globals, **(context or {})}
        return self.engine.render_file(template_name, ctx)

    def clear_cache(self) -> None:
        """Clear cache."""
        self.engine.clear_cache()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Template Engine."""
    print("=" * 70)
    print("BAEL - TEMPLATE ENGINE DEMO")
    print("Dynamic Text Templating System")
    print("=" * 70)
    print()

    manager = TemplateEngineManager()

    # 1. Simple Variables
    print("1. SIMPLE VARIABLES:")
    print("-" * 40)

    result = manager.render("Hello, {{ name }}!", {"name": "World"})
    print(f"   Result: {result}")
    print()

    # 2. Dot Notation
    print("2. DOT NOTATION:")
    print("-" * 40)

    result = manager.render(
        "User: {{ user.name }}, Email: {{ user.email }}",
        {"user": {"name": "John", "email": "john@example.com"}}
    )
    print(f"   Result: {result}")
    print()

    # 3. Filters
    print("3. FILTERS:")
    print("-" * 40)

    result = manager.render("{{ name | upper }}", {"name": "john"})
    print(f"   upper: {result}")

    result = manager.render("{{ text | truncate(20) }}", {"text": "This is a very long text that should be truncated"})
    print(f"   truncate: {result}")

    result = manager.render("{{ items | join(' - ') }}", {"items": ["a", "b", "c"]})
    print(f"   join: {result}")

    result = manager.render("{{ price | round(2) }}", {"price": 19.999})
    print(f"   round: {result}")
    print()

    # 4. Conditionals
    print("4. CONDITIONALS:")
    print("-" * 40)

    template = """
{% if user.admin %}
Admin User
{% elif user.active %}
Active User
{% else %}
Guest
{% endif %}
"""

    result = manager.render(template, {"user": {"admin": True}})
    print(f"   Admin: {result.strip()}")

    result = manager.render(template, {"user": {"admin": False, "active": True}})
    print(f"   Active: {result.strip()}")

    result = manager.render(template, {"user": {"admin": False, "active": False}})
    print(f"   Guest: {result.strip()}")
    print()

    # 5. Loops
    print("5. LOOPS:")
    print("-" * 40)

    template = """{% for item in items %}{{ loop.index }}. {{ item }}
{% endfor %}"""

    result = manager.render(template, {"items": ["Apple", "Banana", "Cherry"]})
    print(f"   List:\n{result}")

    # 6. Nested Loops
    print("6. NESTED LOOPS:")
    print("-" * 40)

    template = """{% for row in matrix %}{% for cell in row %}{{ cell }} {% endfor %}
{% endfor %}"""

    result = manager.render(template, {"matrix": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]})
    print(f"   Matrix:\n{result}")

    # 7. Set Variables
    print("7. SET VARIABLES:")
    print("-" * 40)

    template = """{% set total = 100 %}{% set discount = 0.2 %}{% set price = total %}
Price: {{ price }} (Discount: {{ discount | round(0) }}%)"""

    result = manager.render(template, {})
    print(f"   {result.strip()}")
    print()

    # 8. Comparisons
    print("8. COMPARISONS:")
    print("-" * 40)

    templates = [
        ("{% if age >= 18 %}Adult{% else %}Minor{% endif %}", {"age": 25}),
        ("{% if name == 'John' %}Hi John!{% endif %}", {"name": "John"}),
        ("{% if item in list %}Found{% else %}Not found{% endif %}", {"item": "b", "list": ["a", "b", "c"]})
    ]

    for template, ctx in templates:
        result = manager.render(template, ctx)
        print(f"   {result}")
    print()

    # 9. Loop Metadata
    print("9. LOOP METADATA:")
    print("-" * 40)

    template = """{% for item in items %}{% if loop.first %}[{% endif %}{{ item }}{% if not loop.last %}, {% endif %}{% if loop.last %}]{% endif %}{% endfor %}"""

    result = manager.render(template, {"items": ["x", "y", "z"]})
    print(f"   With metadata: {result}")
    print()

    # 10. Macros
    print("10. MACROS:")
    print("-" * 40)

    template = """{% macro greet(name, greeting) %}{{ greeting }}, {{ name }}!{% endmacro %}{% call greet("World", "Hello") %} - {% call greet("BAEL", "Welcome") %}"""

    result = manager.render(template, {})
    print(f"   {result}")
    print()

    # 11. Custom Filters
    print("11. CUSTOM FILTERS:")
    print("-" * 40)

    manager.register_filter("double", lambda x: x * 2)
    manager.register_filter("currency", lambda x: f"${x:,.2f}")

    result = manager.render("{{ value | double }}", {"value": 42})
    print(f"   Double 42: {result}")

    result = manager.render("{{ price | currency }}", {"price": 1234.56})
    print(f"   Currency: {result}")
    print()

    # 12. Global Variables
    print("12. GLOBAL VARIABLES:")
    print("-" * 40)

    manager.set_global("app_name", "BAEL")
    manager.set_global("version", "1.0.0")

    result = manager.render("{{ app_name }} v{{ version }}", {})
    print(f"   {result}")
    print()

    # 13. Raw Blocks
    print("13. RAW BLOCKS:")
    print("-" * 40)

    template = "Template syntax: {% raw %}{{ variable }} {% if cond %}...{% endif %}{% endraw %}"
    result = manager.render(template, {})
    print(f"   {result}")
    print()

    # 14. Filter Chaining
    print("14. FILTER CHAINING:")
    print("-" * 40)

    result = manager.render("{{ text | lower | truncate(15) | upper }}", {"text": "Hello World and Beyond"})
    print(f"   Chained: {result}")
    print()

    # 15. Complex Template
    print("15. COMPLEX TEMPLATE:")
    print("-" * 40)

    email_template = """
Subject: Order Confirmation #{{ order.id }}

Dear {{ customer.name | title }},

Thank you for your order!

Items:
{% for item in order.items %}
  - {{ item.name | title }} (x{{ item.quantity }}): {{ item.price | currency }}
{% endfor %}

Subtotal: {{ order.subtotal | currency }}
{% if order.discount > 0 %}
Discount: -{{ order.discount | currency }}
{% endif %}
Total: {{ order.total | currency }}

{% if customer.premium %}
As a premium member, you get free shipping!
{% else %}
Shipping: {{ order.shipping | currency }}
{% endif %}

Best regards,
{{ app_name }} Team
"""

    result = manager.render(email_template, {
        "customer": {"name": "john doe", "premium": True},
        "order": {
            "id": "ORD-12345",
            "items": [
                {"name": "widget", "quantity": 2, "price": 29.99},
                {"name": "gadget", "quantity": 1, "price": 49.99}
            ],
            "subtotal": 109.97,
            "discount": 10.00,
            "total": 99.97,
            "shipping": 5.99
        }
    })
    print(result)

    print("=" * 70)
    print("DEMO COMPLETE - Template Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
