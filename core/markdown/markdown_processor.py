#!/usr/bin/env python3
"""
BAEL - Markdown Processor
Comprehensive Markdown parsing, rendering, and manipulation system.

Features:
- Full Markdown parsing
- HTML rendering
- Custom renderers
- Syntax highlighting support
- Table of contents generation
- Link extraction
- Image processing
- Custom extensions
- AST manipulation
- Document analysis
"""

import asyncio
import hashlib
import html
import json
import logging
import re
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Pattern, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class NodeType(Enum):
    """Markdown node types."""
    DOCUMENT = "document"
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    BLOCKQUOTE = "blockquote"
    CODE_BLOCK = "code_block"
    HORIZONTAL_RULE = "hr"
    UNORDERED_LIST = "unordered_list"
    ORDERED_LIST = "ordered_list"
    LIST_ITEM = "list_item"
    TABLE = "table"
    TABLE_ROW = "table_row"
    TABLE_CELL = "table_cell"
    TEXT = "text"
    EMPHASIS = "emphasis"
    STRONG = "strong"
    STRIKETHROUGH = "strikethrough"
    CODE = "code"
    LINK = "link"
    IMAGE = "image"
    LINE_BREAK = "line_break"
    HTML = "html"


class TableAlign(Enum):
    """Table alignment."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class MarkdownNode:
    """AST node for Markdown."""
    type: NodeType
    content: str = ""
    children: List["MarkdownNode"] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def add_child(self, child: "MarkdownNode") -> "MarkdownNode":
        self.children.append(child)
        return child

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "content": self.content,
            "children": [c.to_dict() for c in self.children],
            "attributes": self.attributes
        }


@dataclass
class TOCEntry:
    """Table of contents entry."""
    level: int
    text: str
    slug: str
    children: List["TOCEntry"] = field(default_factory=list)


@dataclass
class Link:
    """Extracted link."""
    text: str
    url: str
    title: Optional[str] = None


@dataclass
class DocumentStats:
    """Document statistics."""
    word_count: int = 0
    char_count: int = 0
    line_count: int = 0
    paragraph_count: int = 0
    heading_count: int = 0
    link_count: int = 0
    image_count: int = 0
    code_block_count: int = 0
    list_count: int = 0
    table_count: int = 0


# =============================================================================
# INLINE PARSER
# =============================================================================

class InlineParser:
    """Parse inline Markdown elements."""

    def __init__(self):
        self._patterns: List[Tuple[Pattern, Callable]] = []
        self._setup_patterns()

    def _setup_patterns(self):
        # Strong (bold) - must come before emphasis
        self._patterns.append((
            re.compile(r'\*\*(.+?)\*\*|__(.+?)__'),
            self._parse_strong
        ))

        # Emphasis (italic)
        self._patterns.append((
            re.compile(r'\*(.+?)\*|_(.+?)_'),
            self._parse_emphasis
        ))

        # Strikethrough
        self._patterns.append((
            re.compile(r'~~(.+?)~~'),
            self._parse_strikethrough
        ))

        # Code
        self._patterns.append((
            re.compile(r'`([^`]+)`'),
            self._parse_code
        ))

        # Image
        self._patterns.append((
            re.compile(r'!\[([^\]]*)\]\(([^)]+)\)'),
            self._parse_image
        ))

        # Link
        self._patterns.append((
            re.compile(r'\[([^\]]+)\]\(([^)]+)\)'),
            self._parse_link
        ))

        # Auto link
        self._patterns.append((
            re.compile(r'<(https?://[^>]+)>'),
            self._parse_autolink
        ))

        # Line break
        self._patterns.append((
            re.compile(r'  \n'),
            self._parse_linebreak
        ))

    def parse(self, text: str) -> List[MarkdownNode]:
        """Parse inline elements."""
        nodes = []
        self._parse_inline(text, nodes)
        return nodes

    def _parse_inline(self, text: str, nodes: List[MarkdownNode]):
        """Recursively parse inline elements."""
        if not text:
            return

        # Find earliest match
        best_match = None
        best_handler = None
        best_start = len(text)

        for pattern, handler in self._patterns:
            match = pattern.search(text)
            if match and match.start() < best_start:
                best_match = match
                best_handler = handler
                best_start = match.start()

        if best_match:
            # Text before match
            if best_start > 0:
                nodes.append(MarkdownNode(
                    type=NodeType.TEXT,
                    content=text[:best_start]
                ))

            # Handle match
            node = best_handler(best_match)
            nodes.append(node)

            # Continue after match
            self._parse_inline(text[best_match.end():], nodes)
        else:
            # No more matches, remaining text
            if text:
                nodes.append(MarkdownNode(
                    type=NodeType.TEXT,
                    content=text
                ))

    def _parse_strong(self, match: re.Match) -> MarkdownNode:
        content = match.group(1) or match.group(2)
        node = MarkdownNode(type=NodeType.STRONG)
        self._parse_inline(content, node.children)
        return node

    def _parse_emphasis(self, match: re.Match) -> MarkdownNode:
        content = match.group(1) or match.group(2)
        node = MarkdownNode(type=NodeType.EMPHASIS)
        self._parse_inline(content, node.children)
        return node

    def _parse_strikethrough(self, match: re.Match) -> MarkdownNode:
        content = match.group(1)
        node = MarkdownNode(type=NodeType.STRIKETHROUGH)
        self._parse_inline(content, node.children)
        return node

    def _parse_code(self, match: re.Match) -> MarkdownNode:
        return MarkdownNode(
            type=NodeType.CODE,
            content=match.group(1)
        )

    def _parse_image(self, match: re.Match) -> MarkdownNode:
        return MarkdownNode(
            type=NodeType.IMAGE,
            content=match.group(1),  # Alt text
            attributes={"src": match.group(2)}
        )

    def _parse_link(self, match: re.Match) -> MarkdownNode:
        node = MarkdownNode(
            type=NodeType.LINK,
            attributes={"href": match.group(2)}
        )
        self._parse_inline(match.group(1), node.children)
        return node

    def _parse_autolink(self, match: re.Match) -> MarkdownNode:
        url = match.group(1)
        return MarkdownNode(
            type=NodeType.LINK,
            children=[MarkdownNode(type=NodeType.TEXT, content=url)],
            attributes={"href": url}
        )

    def _parse_linebreak(self, match: re.Match) -> MarkdownNode:
        return MarkdownNode(type=NodeType.LINE_BREAK)


# =============================================================================
# BLOCK PARSER
# =============================================================================

class BlockParser:
    """Parse block-level Markdown elements."""

    def __init__(self):
        self.inline_parser = InlineParser()

    def parse(self, text: str) -> MarkdownNode:
        """Parse Markdown text into AST."""
        document = MarkdownNode(type=NodeType.DOCUMENT)
        lines = text.split('\n')

        i = 0
        while i < len(lines):
            i = self._parse_block(lines, i, document)

        return document

    def _parse_block(
        self,
        lines: List[str],
        start: int,
        parent: MarkdownNode
    ) -> int:
        """Parse a block element."""
        if start >= len(lines):
            return start

        line = lines[start]

        # Empty line
        if not line.strip():
            return start + 1

        # Heading (ATX style)
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            content = heading_match.group(2).rstrip('#').strip()

            node = MarkdownNode(
                type=NodeType.HEADING,
                attributes={"level": level}
            )
            node.children = self.inline_parser.parse(content)
            parent.add_child(node)

            return start + 1

        # Horizontal rule
        if re.match(r'^[-*_]{3,}\s*$', line):
            parent.add_child(MarkdownNode(type=NodeType.HORIZONTAL_RULE))
            return start + 1

        # Code block (fenced)
        fence_match = re.match(r'^```(\w*)\s*$', line)
        if fence_match:
            language = fence_match.group(1)
            code_lines = []
            i = start + 1

            while i < len(lines) and not lines[i].startswith('```'):
                code_lines.append(lines[i])
                i += 1

            node = MarkdownNode(
                type=NodeType.CODE_BLOCK,
                content='\n'.join(code_lines),
                attributes={"language": language}
            )
            parent.add_child(node)

            return i + 1

        # Blockquote
        if line.startswith('>'):
            return self._parse_blockquote(lines, start, parent)

        # Unordered list
        if re.match(r'^[-*+]\s+', line):
            return self._parse_unordered_list(lines, start, parent)

        # Ordered list
        if re.match(r'^\d+\.\s+', line):
            return self._parse_ordered_list(lines, start, parent)

        # Table
        if '|' in line and start + 1 < len(lines) and '---' in lines[start + 1]:
            return self._parse_table(lines, start, parent)

        # HTML block
        if line.startswith('<'):
            parent.add_child(MarkdownNode(
                type=NodeType.HTML,
                content=line
            ))
            return start + 1

        # Default: paragraph
        return self._parse_paragraph(lines, start, parent)

    def _parse_paragraph(
        self,
        lines: List[str],
        start: int,
        parent: MarkdownNode
    ) -> int:
        """Parse paragraph."""
        para_lines = []
        i = start

        while i < len(lines):
            line = lines[i]

            # Empty line ends paragraph
            if not line.strip():
                break

            # Other block elements end paragraph
            if (line.startswith('#') or
                line.startswith('>') or
                line.startswith('```') or
                re.match(r'^[-*+]\s+', line) or
                re.match(r'^\d+\.\s+', line) or
                re.match(r'^[-*_]{3,}\s*$', line)):
                break

            para_lines.append(line)
            i += 1

        if para_lines:
            content = ' '.join(para_lines)
            node = MarkdownNode(type=NodeType.PARAGRAPH)
            node.children = self.inline_parser.parse(content)
            parent.add_child(node)

        return i

    def _parse_blockquote(
        self,
        lines: List[str],
        start: int,
        parent: MarkdownNode
    ) -> int:
        """Parse blockquote."""
        quote_lines = []
        i = start

        while i < len(lines):
            line = lines[i]

            if line.startswith('>'):
                # Remove '>' and optional space
                content = re.sub(r'^>\s?', '', line)
                quote_lines.append(content)
                i += 1
            elif line.strip() and quote_lines:
                # Continuation line
                quote_lines.append(line)
                i += 1
            else:
                break

        if quote_lines:
            node = MarkdownNode(type=NodeType.BLOCKQUOTE)
            # Parse nested content
            nested_doc = self.parse('\n'.join(quote_lines))
            node.children = nested_doc.children
            parent.add_child(node)

        return i

    def _parse_unordered_list(
        self,
        lines: List[str],
        start: int,
        parent: MarkdownNode
    ) -> int:
        """Parse unordered list."""
        list_node = MarkdownNode(type=NodeType.UNORDERED_LIST)
        i = start

        while i < len(lines):
            line = lines[i]

            match = re.match(r'^[-*+]\s+(.+)$', line)
            if match:
                item = MarkdownNode(type=NodeType.LIST_ITEM)
                item.children = self.inline_parser.parse(match.group(1))
                list_node.add_child(item)
                i += 1
            elif line.startswith('  ') and list_node.children:
                # Continuation
                last_item = list_node.children[-1]
                last_item.children.extend(
                    self.inline_parser.parse(' ' + line.strip())
                )
                i += 1
            else:
                break

        if list_node.children:
            parent.add_child(list_node)

        return i

    def _parse_ordered_list(
        self,
        lines: List[str],
        start: int,
        parent: MarkdownNode
    ) -> int:
        """Parse ordered list."""
        list_node = MarkdownNode(
            type=NodeType.ORDERED_LIST,
            attributes={"start": 1}
        )
        i = start

        while i < len(lines):
            line = lines[i]

            match = re.match(r'^(\d+)\.\s+(.+)$', line)
            if match:
                if not list_node.children:
                    list_node.attributes["start"] = int(match.group(1))

                item = MarkdownNode(type=NodeType.LIST_ITEM)
                item.children = self.inline_parser.parse(match.group(2))
                list_node.add_child(item)
                i += 1
            elif line.startswith('  ') and list_node.children:
                last_item = list_node.children[-1]
                last_item.children.extend(
                    self.inline_parser.parse(' ' + line.strip())
                )
                i += 1
            else:
                break

        if list_node.children:
            parent.add_child(list_node)

        return i

    def _parse_table(
        self,
        lines: List[str],
        start: int,
        parent: MarkdownNode
    ) -> int:
        """Parse table."""
        table_node = MarkdownNode(type=NodeType.TABLE)

        # Header row
        header_cells = self._parse_table_row(lines[start])
        header_row = MarkdownNode(
            type=NodeType.TABLE_ROW,
            attributes={"header": True}
        )

        for cell_content in header_cells:
            cell = MarkdownNode(type=NodeType.TABLE_CELL)
            cell.children = self.inline_parser.parse(cell_content)
            header_row.add_child(cell)

        table_node.add_child(header_row)

        # Alignment row
        align_row = lines[start + 1]
        alignments = self._parse_alignments(align_row)
        table_node.attributes["alignments"] = alignments

        # Data rows
        i = start + 2
        while i < len(lines):
            line = lines[i]

            if not line.strip() or '|' not in line:
                break

            cells = self._parse_table_row(line)
            row = MarkdownNode(type=NodeType.TABLE_ROW)

            for j, cell_content in enumerate(cells):
                cell = MarkdownNode(
                    type=NodeType.TABLE_CELL,
                    attributes={"align": alignments[j] if j < len(alignments) else "left"}
                )
                cell.children = self.inline_parser.parse(cell_content)
                row.add_child(cell)

            table_node.add_child(row)
            i += 1

        parent.add_child(table_node)
        return i

    def _parse_table_row(self, line: str) -> List[str]:
        """Parse table row cells."""
        # Remove leading/trailing pipes
        line = line.strip()
        if line.startswith('|'):
            line = line[1:]
        if line.endswith('|'):
            line = line[:-1]

        return [cell.strip() for cell in line.split('|')]

    def _parse_alignments(self, line: str) -> List[str]:
        """Parse table alignment row."""
        cells = self._parse_table_row(line)
        alignments = []

        for cell in cells:
            cell = cell.strip()

            if cell.startswith(':') and cell.endswith(':'):
                alignments.append("center")
            elif cell.endswith(':'):
                alignments.append("right")
            else:
                alignments.append("left")

        return alignments


# =============================================================================
# RENDERER BASE
# =============================================================================

class Renderer(ABC):
    """Abstract renderer."""

    @abstractmethod
    def render(self, node: MarkdownNode) -> str:
        """Render node to string."""
        pass


# =============================================================================
# HTML RENDERER
# =============================================================================

class HTMLRenderer(Renderer):
    """Render Markdown AST to HTML."""

    def __init__(self, options: Optional[Dict[str, Any]] = None):
        self.options = options or {}
        self._heading_ids: Set[str] = set()

    def render(self, node: MarkdownNode) -> str:
        """Render node to HTML."""
        method_name = f"_render_{node.type.value}"
        method = getattr(self, method_name, self._render_default)
        return method(node)

    def _render_children(self, node: MarkdownNode) -> str:
        return ''.join(self.render(child) for child in node.children)

    def _render_document(self, node: MarkdownNode) -> str:
        return self._render_children(node)

    def _render_paragraph(self, node: MarkdownNode) -> str:
        content = self._render_children(node)
        return f"<p>{content}</p>\n"

    def _render_heading(self, node: MarkdownNode) -> str:
        level = node.attributes.get("level", 1)
        content = self._render_children(node)

        # Generate ID
        slug = self._generate_slug(self._get_text_content(node))

        return f'<h{level} id="{slug}">{content}</h{level}>\n'

    def _render_blockquote(self, node: MarkdownNode) -> str:
        content = self._render_children(node)
        return f"<blockquote>\n{content}</blockquote>\n"

    def _render_code_block(self, node: MarkdownNode) -> str:
        language = node.attributes.get("language", "")
        escaped = html.escape(node.content)

        if language:
            return f'<pre><code class="language-{language}">{escaped}</code></pre>\n'
        return f"<pre><code>{escaped}</code></pre>\n"

    def _render_hr(self, node: MarkdownNode) -> str:
        return "<hr>\n"

    def _render_unordered_list(self, node: MarkdownNode) -> str:
        items = self._render_children(node)
        return f"<ul>\n{items}</ul>\n"

    def _render_ordered_list(self, node: MarkdownNode) -> str:
        start = node.attributes.get("start", 1)
        items = self._render_children(node)

        if start != 1:
            return f'<ol start="{start}">\n{items}</ol>\n'
        return f"<ol>\n{items}</ol>\n"

    def _render_list_item(self, node: MarkdownNode) -> str:
        content = self._render_children(node)
        return f"<li>{content}</li>\n"

    def _render_table(self, node: MarkdownNode) -> str:
        rows = self._render_children(node)
        return f"<table>\n{rows}</table>\n"

    def _render_table_row(self, node: MarkdownNode) -> str:
        cells = self._render_children(node)
        return f"<tr>\n{cells}</tr>\n"

    def _render_table_cell(self, node: MarkdownNode) -> str:
        content = self._render_children(node)
        align = node.attributes.get("align", "")
        is_header = node.attributes.get("header", False)

        tag = "th" if is_header else "td"

        if align:
            return f'<{tag} style="text-align: {align}">{content}</{tag}>\n'
        return f"<{tag}>{content}</{tag}>\n"

    def _render_text(self, node: MarkdownNode) -> str:
        return html.escape(node.content)

    def _render_emphasis(self, node: MarkdownNode) -> str:
        content = self._render_children(node)
        return f"<em>{content}</em>"

    def _render_strong(self, node: MarkdownNode) -> str:
        content = self._render_children(node)
        return f"<strong>{content}</strong>"

    def _render_strikethrough(self, node: MarkdownNode) -> str:
        content = self._render_children(node)
        return f"<del>{content}</del>"

    def _render_code(self, node: MarkdownNode) -> str:
        escaped = html.escape(node.content)
        return f"<code>{escaped}</code>"

    def _render_link(self, node: MarkdownNode) -> str:
        href = html.escape(node.attributes.get("href", ""))
        content = self._render_children(node)
        return f'<a href="{href}">{content}</a>'

    def _render_image(self, node: MarkdownNode) -> str:
        src = html.escape(node.attributes.get("src", ""))
        alt = html.escape(node.content)
        return f'<img src="{src}" alt="{alt}">'

    def _render_line_break(self, node: MarkdownNode) -> str:
        return "<br>\n"

    def _render_html(self, node: MarkdownNode) -> str:
        return node.content + "\n"

    def _render_default(self, node: MarkdownNode) -> str:
        return self._render_children(node)

    def _generate_slug(self, text: str) -> str:
        """Generate URL slug from text."""
        slug = text.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = slug.strip('-')

        # Ensure unique
        original = slug
        counter = 1

        while slug in self._heading_ids:
            slug = f"{original}-{counter}"
            counter += 1

        self._heading_ids.add(slug)
        return slug

    def _get_text_content(self, node: MarkdownNode) -> str:
        """Extract text content from node."""
        if node.type == NodeType.TEXT:
            return node.content

        return ''.join(self._get_text_content(child) for child in node.children)


# =============================================================================
# TEXT RENDERER
# =============================================================================

class TextRenderer(Renderer):
    """Render Markdown AST to plain text."""

    def render(self, node: MarkdownNode) -> str:
        method_name = f"_render_{node.type.value}"
        method = getattr(self, method_name, self._render_default)
        return method(node)

    def _render_children(self, node: MarkdownNode) -> str:
        return ''.join(self.render(child) for child in node.children)

    def _render_document(self, node: MarkdownNode) -> str:
        return self._render_children(node)

    def _render_paragraph(self, node: MarkdownNode) -> str:
        return self._render_children(node) + "\n\n"

    def _render_heading(self, node: MarkdownNode) -> str:
        return self._render_children(node) + "\n\n"

    def _render_blockquote(self, node: MarkdownNode) -> str:
        content = self._render_children(node)
        lines = content.split('\n')
        return '\n'.join('> ' + line for line in lines) + "\n"

    def _render_code_block(self, node: MarkdownNode) -> str:
        return node.content + "\n\n"

    def _render_hr(self, node: MarkdownNode) -> str:
        return "-" * 40 + "\n\n"

    def _render_list_item(self, node: MarkdownNode) -> str:
        return "• " + self._render_children(node) + "\n"

    def _render_unordered_list(self, node: MarkdownNode) -> str:
        return self._render_children(node) + "\n"

    def _render_ordered_list(self, node: MarkdownNode) -> str:
        result = []
        for i, child in enumerate(node.children, 1):
            content = self._render_children(child)
            result.append(f"{i}. {content}")
        return '\n'.join(result) + "\n\n"

    def _render_text(self, node: MarkdownNode) -> str:
        return node.content

    def _render_emphasis(self, node: MarkdownNode) -> str:
        return self._render_children(node)

    def _render_strong(self, node: MarkdownNode) -> str:
        return self._render_children(node)

    def _render_strikethrough(self, node: MarkdownNode) -> str:
        return self._render_children(node)

    def _render_code(self, node: MarkdownNode) -> str:
        return node.content

    def _render_link(self, node: MarkdownNode) -> str:
        text = self._render_children(node)
        href = node.attributes.get("href", "")
        return f"{text} ({href})"

    def _render_image(self, node: MarkdownNode) -> str:
        return f"[Image: {node.content}]"

    def _render_line_break(self, node: MarkdownNode) -> str:
        return "\n"

    def _render_default(self, node: MarkdownNode) -> str:
        return self._render_children(node)


# =============================================================================
# MARKDOWN PROCESSOR
# =============================================================================

class MarkdownProcessor:
    """
    Comprehensive Markdown Processor for BAEL.

    Provides Markdown parsing, rendering, and analysis.
    """

    def __init__(self):
        self._parser = BlockParser()
        self._html_renderer = HTMLRenderer()
        self._text_renderer = TextRenderer()
        self._stats: Dict[str, int] = defaultdict(int)

    # -------------------------------------------------------------------------
    # PARSING
    # -------------------------------------------------------------------------

    def parse(self, text: str) -> MarkdownNode:
        """Parse Markdown text to AST."""
        self._stats["documents_parsed"] += 1
        return self._parser.parse(text)

    # -------------------------------------------------------------------------
    # RENDERING
    # -------------------------------------------------------------------------

    def to_html(self, text: str) -> str:
        """Convert Markdown to HTML."""
        self._stats["html_renders"] += 1
        ast = self.parse(text)
        self._html_renderer._heading_ids.clear()
        return self._html_renderer.render(ast)

    def to_text(self, text: str) -> str:
        """Convert Markdown to plain text."""
        self._stats["text_renders"] += 1
        ast = self.parse(text)
        return self._text_renderer.render(ast)

    def render_ast(self, ast: MarkdownNode, format: str = "html") -> str:
        """Render AST to specified format."""
        if format == "html":
            self._html_renderer._heading_ids.clear()
            return self._html_renderer.render(ast)
        elif format == "text":
            return self._text_renderer.render(ast)
        else:
            raise ValueError(f"Unknown format: {format}")

    # -------------------------------------------------------------------------
    # TABLE OF CONTENTS
    # -------------------------------------------------------------------------

    def generate_toc(
        self,
        text: str,
        max_level: int = 6
    ) -> List[TOCEntry]:
        """Generate table of contents."""
        ast = self.parse(text)
        entries = []

        self._extract_toc(ast, entries, max_level)

        return entries

    def _extract_toc(
        self,
        node: MarkdownNode,
        entries: List[TOCEntry],
        max_level: int
    ):
        """Extract TOC entries from AST."""
        if node.type == NodeType.HEADING:
            level = node.attributes.get("level", 1)

            if level <= max_level:
                text = self._get_text_content(node)
                slug = self._generate_slug(text)

                entries.append(TOCEntry(
                    level=level,
                    text=text,
                    slug=slug
                ))

        for child in node.children:
            self._extract_toc(child, entries, max_level)

    def render_toc_html(self, entries: List[TOCEntry]) -> str:
        """Render TOC as HTML."""
        if not entries:
            return ""

        html = ['<nav class="toc">', '<ul>']

        for entry in entries:
            indent = "  " * entry.level
            html.append(f'{indent}<li><a href="#{entry.slug}">{entry.text}</a></li>')

        html.extend(['</ul>', '</nav>'])

        return '\n'.join(html)

    # -------------------------------------------------------------------------
    # LINK EXTRACTION
    # -------------------------------------------------------------------------

    def extract_links(self, text: str) -> List[Link]:
        """Extract all links from Markdown."""
        ast = self.parse(text)
        links = []

        self._extract_links(ast, links)

        return links

    def _extract_links(self, node: MarkdownNode, links: List[Link]):
        """Extract links from AST."""
        if node.type == NodeType.LINK:
            text = self._get_text_content(node)
            href = node.attributes.get("href", "")

            links.append(Link(
                text=text,
                url=href
            ))

        for child in node.children:
            self._extract_links(child, links)

    def extract_images(self, text: str) -> List[Link]:
        """Extract all images from Markdown."""
        ast = self.parse(text)
        images = []

        self._extract_images(ast, images)

        return images

    def _extract_images(self, node: MarkdownNode, images: List[Link]):
        """Extract images from AST."""
        if node.type == NodeType.IMAGE:
            images.append(Link(
                text=node.content,
                url=node.attributes.get("src", "")
            ))

        for child in node.children:
            self._extract_images(child, images)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_document_stats(self, text: str) -> DocumentStats:
        """Get document statistics."""
        ast = self.parse(text)
        stats = DocumentStats()

        # Basic counts
        stats.line_count = len(text.split('\n'))
        stats.char_count = len(text)

        # Word count from plain text
        plain_text = self.to_text(text)
        stats.word_count = len(plain_text.split())

        # AST-based counts
        self._count_nodes(ast, stats)

        return stats

    def _count_nodes(self, node: MarkdownNode, stats: DocumentStats):
        """Count node types in AST."""
        if node.type == NodeType.PARAGRAPH:
            stats.paragraph_count += 1
        elif node.type == NodeType.HEADING:
            stats.heading_count += 1
        elif node.type == NodeType.LINK:
            stats.link_count += 1
        elif node.type == NodeType.IMAGE:
            stats.image_count += 1
        elif node.type == NodeType.CODE_BLOCK:
            stats.code_block_count += 1
        elif node.type in (NodeType.UNORDERED_LIST, NodeType.ORDERED_LIST):
            stats.list_count += 1
        elif node.type == NodeType.TABLE:
            stats.table_count += 1

        for child in node.children:
            self._count_nodes(child, stats)

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def _get_text_content(self, node: MarkdownNode) -> str:
        """Get plain text content from node."""
        if node.type == NodeType.TEXT:
            return node.content

        if node.type == NodeType.CODE:
            return node.content

        return ''.join(self._get_text_content(child) for child in node.children)

    def _generate_slug(self, text: str) -> str:
        """Generate URL slug."""
        slug = text.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        return slug.strip('-')

    def ast_to_json(self, node: MarkdownNode) -> str:
        """Convert AST to JSON."""
        return json.dumps(node.to_dict(), indent=2)

    def get_stats(self) -> Dict[str, int]:
        """Get processor statistics."""
        return dict(self._stats)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Markdown Processor."""
    print("=" * 70)
    print("BAEL - MARKDOWN PROCESSOR DEMO")
    print("Comprehensive Markdown Processing System")
    print("=" * 70)
    print()

    processor = MarkdownProcessor()

    # Sample Markdown
    sample_md = """# Welcome to BAEL

This is a **comprehensive** AI agent system with *advanced* capabilities.

## Features

- Natural language processing
- Task automation
- Multi-agent coordination
- ~~Deprecated feature~~

### Code Example

```python
def hello_world():
    print("Hello, BAEL!")
```

## Links and Images

Check out [BAEL Documentation](https://example.com/docs) for more info.

![BAEL Logo](https://example.com/logo.png)

## Data Table

| Feature | Status | Priority |
|---------|:------:|----------|
| NLP | ✓ | High |
| Vision | ✓ | Medium |
| Audio | WIP | Low |

> BAEL represents the next generation of AI agent systems.

---

That's all for now!
"""

    # 1. Parse to AST
    print("1. PARSE TO AST:")
    print("-" * 40)

    ast = processor.parse(sample_md)
    print(f"   Document parsed")
    print(f"   Top-level children: {len(ast.children)}")
    print(f"   First child: {ast.children[0].type.value}")
    print()

    # 2. Render to HTML
    print("2. RENDER TO HTML:")
    print("-" * 40)

    html_output = processor.to_html(sample_md)
    print(f"   HTML output ({len(html_output)} chars):")
    print(f"   {html_output[:300]}...")
    print()

    # 3. Render to Plain Text
    print("3. RENDER TO PLAIN TEXT:")
    print("-" * 40)

    text_output = processor.to_text(sample_md)
    print(f"   Plain text ({len(text_output)} chars):")
    print(f"   {text_output[:200]}...")
    print()

    # 4. Table of Contents
    print("4. TABLE OF CONTENTS:")
    print("-" * 40)

    toc = processor.generate_toc(sample_md)
    print(f"   Entries:")

    for entry in toc:
        indent = "  " * (entry.level - 1)
        print(f"      {indent}[{entry.level}] {entry.text} (#{entry.slug})")
    print()

    # 5. Extract Links
    print("5. EXTRACT LINKS:")
    print("-" * 40)

    links = processor.extract_links(sample_md)
    print(f"   Found {len(links)} links:")

    for link in links:
        print(f"      - {link.text}: {link.url}")
    print()

    # 6. Extract Images
    print("6. EXTRACT IMAGES:")
    print("-" * 40)

    images = processor.extract_images(sample_md)
    print(f"   Found {len(images)} images:")

    for img in images:
        print(f"      - {img.text}: {img.url}")
    print()

    # 7. Document Statistics
    print("7. DOCUMENT STATISTICS:")
    print("-" * 40)

    stats = processor.get_document_stats(sample_md)
    print(f"   Word count: {stats.word_count}")
    print(f"   Character count: {stats.char_count}")
    print(f"   Line count: {stats.line_count}")
    print(f"   Paragraph count: {stats.paragraph_count}")
    print(f"   Heading count: {stats.heading_count}")
    print(f"   Link count: {stats.link_count}")
    print(f"   Image count: {stats.image_count}")
    print(f"   Code block count: {stats.code_block_count}")
    print(f"   List count: {stats.list_count}")
    print(f"   Table count: {stats.table_count}")
    print()

    # 8. Inline Elements
    print("8. INLINE ELEMENTS:")
    print("-" * 40)

    inline_md = "This has **bold**, *italic*, `code`, and ~~strikethrough~~."
    html = processor.to_html(inline_md)
    print(f"   Input: {inline_md}")
    print(f"   HTML: {html.strip()}")
    print()

    # 9. Code Blocks
    print("9. CODE BLOCKS:")
    print("-" * 40)

    code_md = """```javascript
function greet(name) {
    return `Hello, ${name}!`;
}
```"""

    html = processor.to_html(code_md)
    print(f"   HTML output:")
    print(f"   {html[:200]}...")
    print()

    # 10. Blockquotes
    print("10. BLOCKQUOTES:")
    print("-" * 40)

    quote_md = """> This is a quote
> It can span multiple lines
>
> And have multiple paragraphs"""

    html = processor.to_html(quote_md)
    print(f"   HTML: {html}")
    print()

    # 11. Tables
    print("11. TABLES:")
    print("-" * 40)

    table_md = """| Left | Center | Right |
|:-----|:------:|------:|
| A | B | C |
| 1 | 2 | 3 |"""

    html = processor.to_html(table_md)
    print(f"   HTML output:")
    print(f"   {html}")
    print()

    # 12. AST to JSON
    print("12. AST TO JSON:")
    print("-" * 40)

    simple_md = "# Hello\n\nWorld"
    ast = processor.parse(simple_md)
    json_output = processor.ast_to_json(ast)

    print(f"   JSON representation:")
    print(f"   {json_output[:300]}...")
    print()

    # 13. Processor Statistics
    print("13. PROCESSOR STATISTICS:")
    print("-" * 40)

    stats = processor.get_stats()
    print(f"   Stats: {stats}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Markdown Processor Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
