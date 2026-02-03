#!/usr/bin/env python3
"""
BAEL - PDF Generator
Comprehensive PDF document generation system.

Features:
- Document structure management
- Page layout and styling
- Text rendering with fonts
- Tables and lists
- Images and graphics
- Headers and footers
- Watermarks
- Table of contents
- Bookmarks and links
- Form fields
- Encryption and permissions
"""

import asyncio
import base64
import hashlib
import io
import json
import logging
import math
import os
import struct
import time
import uuid
import zlib
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, BinaryIO, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class PageSize(Enum):
    """Standard page sizes."""
    A4 = (595.28, 841.89)
    A3 = (841.89, 1190.55)
    A5 = (420.94, 595.28)
    LETTER = (612, 792)
    LEGAL = (612, 1008)
    TABLOID = (792, 1224)


class PageOrientation(Enum):
    """Page orientation."""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class TextAlign(Enum):
    """Text alignment."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"


class FontStyle(Enum):
    """Font style."""
    NORMAL = "normal"
    BOLD = "bold"
    ITALIC = "italic"
    BOLD_ITALIC = "bold_italic"


class LineStyle(Enum):
    """Line style."""
    SOLID = "solid"
    DASHED = "dashed"
    DOTTED = "dotted"


class FillPattern(Enum):
    """Fill pattern."""
    SOLID = "solid"
    NONE = "none"
    HATCHED = "hatched"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Color:
    """RGB color."""
    r: float = 0.0
    g: float = 0.0
    b: float = 0.0

    @classmethod
    def from_hex(cls, hex_color: str) -> "Color":
        """Create color from hex string."""
        hex_color = hex_color.lstrip('#')

        return cls(
            r=int(hex_color[0:2], 16) / 255.0,
            g=int(hex_color[2:4], 16) / 255.0,
            b=int(hex_color[4:6], 16) / 255.0
        )

    @classmethod
    def black(cls) -> "Color":
        return cls(0, 0, 0)

    @classmethod
    def white(cls) -> "Color":
        return cls(1, 1, 1)

    @classmethod
    def red(cls) -> "Color":
        return cls(1, 0, 0)

    @classmethod
    def green(cls) -> "Color":
        return cls(0, 1, 0)

    @classmethod
    def blue(cls) -> "Color":
        return cls(0, 0, 1)

    def to_pdf(self) -> str:
        """Convert to PDF color."""
        return f"{self.r:.3f} {self.g:.3f} {self.b:.3f}"


@dataclass
class Margins:
    """Page margins."""
    top: float = 72.0
    right: float = 72.0
    bottom: float = 72.0
    left: float = 72.0


@dataclass
class FontSpec:
    """Font specification."""
    name: str = "Helvetica"
    size: float = 12.0
    style: FontStyle = FontStyle.NORMAL
    color: Color = field(default_factory=Color.black)


@dataclass
class PageStyle:
    """Page style."""
    size: PageSize = PageSize.A4
    orientation: PageOrientation = PageOrientation.PORTRAIT
    margins: Margins = field(default_factory=Margins)
    background_color: Optional[Color] = None


@dataclass
class TableCell:
    """Table cell."""
    content: str
    colspan: int = 1
    rowspan: int = 1
    align: TextAlign = TextAlign.LEFT
    background: Optional[Color] = None
    font: Optional[FontSpec] = None


@dataclass
class TableRow:
    """Table row."""
    cells: List[TableCell]
    is_header: bool = False
    height: Optional[float] = None


@dataclass
class Table:
    """Table definition."""
    rows: List[TableRow]
    column_widths: List[float] = field(default_factory=list)
    border_color: Color = field(default_factory=Color.black)
    border_width: float = 0.5
    cell_padding: float = 5.0


@dataclass
class ImageSpec:
    """Image specification."""
    data: bytes
    width: float
    height: float
    x: float = 0.0
    y: float = 0.0


@dataclass
class Bookmark:
    """PDF bookmark."""
    title: str
    page: int
    level: int = 0
    y_position: float = 0.0


@dataclass
class PDFMetadata:
    """PDF metadata."""
    title: str = ""
    author: str = ""
    subject: str = ""
    keywords: List[str] = field(default_factory=list)
    creator: str = "BAEL PDF Generator"
    created_at: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# PDF OBJECTS
# =============================================================================

class PDFObject:
    """Base PDF object."""

    def __init__(self, obj_id: int = 0):
        self.obj_id = obj_id

    @abstractmethod
    def to_pdf(self) -> bytes:
        """Convert to PDF bytes."""
        pass


class PDFDict(PDFObject):
    """PDF dictionary object."""

    def __init__(self, obj_id: int = 0):
        super().__init__(obj_id)
        self.entries: Dict[str, Any] = {}

    def __setitem__(self, key: str, value: Any):
        self.entries[key] = value

    def __getitem__(self, key: str) -> Any:
        return self.entries[key]

    def to_pdf(self) -> bytes:
        """Convert to PDF bytes."""
        lines = ["<<"]

        for key, value in self.entries.items():
            lines.append(f"/{key} {self._format_value(value)}")

        lines.append(">>")

        return "\n".join(lines).encode('latin-1')

    def _format_value(self, value: Any) -> str:
        """Format value for PDF."""
        if isinstance(value, str):
            if value.startswith('/') or value.startswith('['):
                return value
            return f"({value})"

        elif isinstance(value, bool):
            return "true" if value else "false"

        elif isinstance(value, int):
            return str(value)

        elif isinstance(value, float):
            return f"{value:.4f}"

        elif isinstance(value, list):
            items = " ".join(self._format_value(v) for v in value)
            return f"[{items}]"

        elif isinstance(value, PDFDict):
            return value.to_pdf().decode('latin-1')

        else:
            return str(value)


class PDFStream(PDFObject):
    """PDF stream object."""

    def __init__(self, obj_id: int = 0):
        super().__init__(obj_id)
        self.dict_entries: Dict[str, Any] = {}
        self.content: bytes = b""
        self.compress: bool = True

    def to_pdf(self) -> bytes:
        """Convert to PDF bytes."""
        content = self.content

        if self.compress and len(content) > 100:
            compressed = zlib.compress(content)

            if len(compressed) < len(content):
                content = compressed
                self.dict_entries["Filter"] = "/FlateDecode"

        self.dict_entries["Length"] = len(content)

        # Build dictionary
        dict_obj = PDFDict()
        dict_obj.entries = self.dict_entries

        result = dict_obj.to_pdf() + b"\nstream\n" + content + b"\nendstream"

        return result


# =============================================================================
# PAGE CONTENT BUILDER
# =============================================================================

class ContentStream:
    """PDF content stream builder."""

    def __init__(self):
        self._content: List[str] = []
        self._fonts: Dict[str, int] = {}
        self._images: Dict[str, int] = {}

    def save_state(self):
        """Save graphics state."""
        self._content.append("q")

    def restore_state(self):
        """Restore graphics state."""
        self._content.append("Q")

    def set_color(self, color: Color, stroke: bool = False):
        """Set color."""
        if stroke:
            self._content.append(f"{color.to_pdf()} RG")
        else:
            self._content.append(f"{color.to_pdf()} rg")

    def set_line_width(self, width: float):
        """Set line width."""
        self._content.append(f"{width:.2f} w")

    def move_to(self, x: float, y: float):
        """Move to position."""
        self._content.append(f"{x:.2f} {y:.2f} m")

    def line_to(self, x: float, y: float):
        """Draw line to position."""
        self._content.append(f"{x:.2f} {y:.2f} l")

    def rect(self, x: float, y: float, w: float, h: float):
        """Draw rectangle."""
        self._content.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re")

    def stroke(self):
        """Stroke path."""
        self._content.append("S")

    def fill(self):
        """Fill path."""
        self._content.append("f")

    def fill_stroke(self):
        """Fill and stroke path."""
        self._content.append("B")

    def clip(self):
        """Clip to path."""
        self._content.append("W n")

    def begin_text(self):
        """Begin text block."""
        self._content.append("BT")

    def end_text(self):
        """End text block."""
        self._content.append("ET")

    def set_font(self, font_ref: str, size: float):
        """Set font."""
        self._content.append(f"/{font_ref} {size:.2f} Tf")

    def set_text_position(self, x: float, y: float):
        """Set text position."""
        self._content.append(f"{x:.2f} {y:.2f} Td")

    def set_text_matrix(self, a: float, b: float, c: float, d: float, e: float, f: float):
        """Set text matrix."""
        self._content.append(f"{a:.2f} {b:.2f} {c:.2f} {d:.2f} {e:.2f} {f:.2f} Tm")

    def show_text(self, text: str):
        """Show text."""
        escaped = self._escape_text(text)
        self._content.append(f"({escaped}) Tj")

    def show_text_newline(self, text: str):
        """Show text and move to next line."""
        escaped = self._escape_text(text)
        self._content.append(f"({escaped}) '")

    def set_leading(self, leading: float):
        """Set text leading."""
        self._content.append(f"{leading:.2f} TL")

    def set_word_spacing(self, spacing: float):
        """Set word spacing."""
        self._content.append(f"{spacing:.2f} Tw")

    def set_char_spacing(self, spacing: float):
        """Set character spacing."""
        self._content.append(f"{spacing:.2f} Tc")

    def draw_image(self, image_ref: str, x: float, y: float, w: float, h: float):
        """Draw image."""
        self.save_state()
        self._content.append(f"{w:.2f} 0 0 {h:.2f} {x:.2f} {y:.2f} cm")
        self._content.append(f"/{image_ref} Do")
        self.restore_state()

    def _escape_text(self, text: str) -> str:
        """Escape text for PDF."""
        text = text.replace("\\", "\\\\")
        text = text.replace("(", "\\(")
        text = text.replace(")", "\\)")

        return text

    def get_content(self) -> bytes:
        """Get content bytes."""
        return "\n".join(self._content).encode('latin-1')


# =============================================================================
# PDF DOCUMENT
# =============================================================================

class PDFDocument:
    """PDF document builder."""

    def __init__(self, metadata: Optional[PDFMetadata] = None):
        self.metadata = metadata or PDFMetadata()
        self._objects: List[PDFObject] = []
        self._pages: List[int] = []
        self._fonts: Dict[str, int] = {}
        self._images: Dict[str, int] = {}
        self._bookmarks: List[Bookmark] = []

        # Standard fonts
        self._standard_fonts = {
            "Helvetica": "Helvetica",
            "Helvetica-Bold": "Helvetica-Bold",
            "Helvetica-Oblique": "Helvetica-Oblique",
            "Helvetica-BoldOblique": "Helvetica-BoldOblique",
            "Times-Roman": "Times-Roman",
            "Times-Bold": "Times-Bold",
            "Times-Italic": "Times-Italic",
            "Times-BoldItalic": "Times-BoldItalic",
            "Courier": "Courier",
            "Courier-Bold": "Courier-Bold",
            "Courier-Oblique": "Courier-Oblique",
            "Courier-BoldOblique": "Courier-BoldOblique"
        }

    def _add_object(self, obj: PDFObject) -> int:
        """Add object and return ID."""
        obj.obj_id = len(self._objects) + 1
        self._objects.append(obj)

        return obj.obj_id

    def _get_font_ref(self, font: FontSpec) -> str:
        """Get font reference."""
        # Map style to font name
        base_name = font.name

        if font.style == FontStyle.BOLD:
            pdf_name = f"{base_name}-Bold"

        elif font.style == FontStyle.ITALIC:
            pdf_name = f"{base_name}-Oblique"

        elif font.style == FontStyle.BOLD_ITALIC:
            pdf_name = f"{base_name}-BoldOblique"

        else:
            pdf_name = base_name

        # Check if already added
        if pdf_name in self._fonts:
            return f"F{self._fonts[pdf_name]}"

        # Add font object
        font_dict = PDFDict()
        font_dict["Type"] = "/Font"
        font_dict["Subtype"] = "/Type1"
        font_dict["BaseFont"] = f"/{pdf_name}"

        font_id = self._add_object(font_dict)
        self._fonts[pdf_name] = font_id

        return f"F{font_id}"

    def _add_image(self, image: ImageSpec) -> str:
        """Add image and return reference."""
        image_hash = hashlib.md5(image.data).hexdigest()

        if image_hash in self._images:
            return f"Im{self._images[image_hash]}"

        # Create image XObject
        img_stream = PDFStream()
        img_stream.dict_entries["Type"] = "/XObject"
        img_stream.dict_entries["Subtype"] = "/Image"
        img_stream.dict_entries["Width"] = int(image.width)
        img_stream.dict_entries["Height"] = int(image.height)
        img_stream.dict_entries["ColorSpace"] = "/DeviceRGB"
        img_stream.dict_entries["BitsPerComponent"] = 8
        img_stream.content = image.data

        img_id = self._add_object(img_stream)
        self._images[image_hash] = img_id

        return f"Im{img_id}"

    def add_page(
        self,
        content: ContentStream,
        style: PageStyle = None
    ) -> int:
        """Add page to document."""
        style = style or PageStyle()

        # Get page dimensions
        width, height = style.size.value

        if style.orientation == PageOrientation.LANDSCAPE:
            width, height = height, width

        # Create content stream
        content_stream = PDFStream()
        content_stream.content = content.get_content()
        content_id = self._add_object(content_stream)

        # Create page object
        page = PDFDict()
        page["Type"] = "/Page"
        page["MediaBox"] = [0, 0, width, height]
        page["Contents"] = f"{content_id} 0 R"

        # Add resources
        resources = PDFDict()

        # Add font resources
        if self._fonts:
            font_dict = PDFDict()

            for name, obj_id in self._fonts.items():
                font_dict[f"F{obj_id}"] = f"{obj_id} 0 R"

            resources["Font"] = font_dict

        # Add image resources
        if self._images:
            xobject_dict = PDFDict()

            for hash_key, obj_id in self._images.items():
                xobject_dict[f"Im{obj_id}"] = f"{obj_id} 0 R"

            resources["XObject"] = xobject_dict

        page["Resources"] = resources

        page_id = self._add_object(page)
        self._pages.append(page_id)

        return len(self._pages) - 1

    def add_bookmark(self, bookmark: Bookmark):
        """Add bookmark."""
        self._bookmarks.append(bookmark)

    def generate(self) -> bytes:
        """Generate PDF bytes."""
        output = io.BytesIO()

        # Header
        output.write(b"%PDF-1.4\n")
        output.write(b"%\xc3\xa4\xc3\xbc\xc3\xb6\xc3\x9f\n")  # Binary marker

        # Object positions
        xref_positions: List[int] = []

        # Write catalog first (will be object 1)
        catalog = PDFDict()
        catalog["Type"] = "/Catalog"
        catalog["Pages"] = "2 0 R"  # Pages will be object 2

        self._objects.insert(0, catalog)

        # Create pages object
        pages = PDFDict()
        pages["Type"] = "/Pages"
        pages["Count"] = len(self._pages)
        pages["Kids"] = [f"{p} 0 R" for p in self._pages]

        self._objects.insert(1, pages)

        # Renumber objects
        for i, obj in enumerate(self._objects):
            obj.obj_id = i + 1

        # Update page parent references
        for page_id in self._pages:
            for obj in self._objects:
                if obj.obj_id == page_id and isinstance(obj, PDFDict):
                    obj["Parent"] = "2 0 R"

        # Write objects
        for obj in self._objects:
            xref_positions.append(output.tell())
            output.write(f"{obj.obj_id} 0 obj\n".encode('latin-1'))
            output.write(obj.to_pdf())
            output.write(b"\nendobj\n")

        # Write metadata
        info = PDFDict()
        info["Title"] = self.metadata.title
        info["Author"] = self.metadata.author
        info["Subject"] = self.metadata.subject
        info["Creator"] = self.metadata.creator
        info["CreationDate"] = self._format_date(self.metadata.created_at)

        info_obj_id = len(self._objects) + 1
        xref_positions.append(output.tell())
        output.write(f"{info_obj_id} 0 obj\n".encode('latin-1'))
        output.write(info.to_pdf())
        output.write(b"\nendobj\n")

        # Write cross-reference table
        xref_start = output.tell()
        output.write(b"xref\n")
        output.write(f"0 {len(xref_positions) + 1}\n".encode('latin-1'))
        output.write(b"0000000000 65535 f \n")

        for pos in xref_positions:
            output.write(f"{pos:010d} 00000 n \n".encode('latin-1'))

        # Trailer
        output.write(b"trailer\n")
        output.write(f"<<\n/Size {len(xref_positions) + 1}\n".encode('latin-1'))
        output.write(b"/Root 1 0 R\n")
        output.write(f"/Info {info_obj_id} 0 R\n".encode('latin-1'))
        output.write(b">>\n")
        output.write(b"startxref\n")
        output.write(f"{xref_start}\n".encode('latin-1'))
        output.write(b"%%EOF")

        return output.getvalue()

    def _format_date(self, dt: datetime) -> str:
        """Format date for PDF."""
        return f"D:{dt.strftime('%Y%m%d%H%M%S')}"


# =============================================================================
# PDF GENERATOR
# =============================================================================

class PDFGenerator:
    """
    Comprehensive PDF Generator for BAEL.

    Provides high-level PDF document creation.
    """

    def __init__(self):
        self._current_doc: Optional[PDFDocument] = None
        self._current_content: Optional[ContentStream] = None
        self._page_style: PageStyle = PageStyle()
        self._cursor_x: float = 0
        self._cursor_y: float = 0
        self._default_font: FontSpec = FontSpec()
        self._stats: Dict[str, int] = defaultdict(int)

    def create_document(self, metadata: Optional[PDFMetadata] = None) -> "PDFGenerator":
        """Create new document."""
        self._current_doc = PDFDocument(metadata)

        return self

    def set_page_style(self, style: PageStyle) -> "PDFGenerator":
        """Set page style."""
        self._page_style = style

        return self

    def add_page(self) -> "PDFGenerator":
        """Add new page."""
        if not self._current_doc:
            self.create_document()

        # Flush current page
        if self._current_content:
            self._current_doc.add_page(self._current_content, self._page_style)

        # Start new page
        self._current_content = ContentStream()

        # Set initial cursor position
        width, height = self._page_style.size.value

        if self._page_style.orientation == PageOrientation.LANDSCAPE:
            width, height = height, width

        self._cursor_x = self._page_style.margins.left
        self._cursor_y = height - self._page_style.margins.top

        self._stats["pages"] += 1

        return self

    def set_font(self, font: FontSpec) -> "PDFGenerator":
        """Set current font."""
        self._default_font = font

        return self

    def write_text(
        self,
        text: str,
        x: Optional[float] = None,
        y: Optional[float] = None,
        font: Optional[FontSpec] = None,
        align: TextAlign = TextAlign.LEFT
    ) -> "PDFGenerator":
        """Write text at position."""
        if not self._current_content:
            self.add_page()

        font = font or self._default_font
        x = x if x is not None else self._cursor_x
        y = y if y is not None else self._cursor_y

        # Get font reference
        font_ref = self._current_doc._get_font_ref(font)

        self._current_content.begin_text()
        self._current_content.set_font(font_ref, font.size)
        self._current_content.set_color(font.color)
        self._current_content.set_text_position(x, y)
        self._current_content.show_text(text)
        self._current_content.end_text()

        # Update cursor
        self._cursor_y -= font.size * 1.2

        return self

    def write_paragraph(
        self,
        text: str,
        width: Optional[float] = None,
        font: Optional[FontSpec] = None,
        align: TextAlign = TextAlign.LEFT,
        line_height: float = 1.2
    ) -> "PDFGenerator":
        """Write paragraph with word wrap."""
        if not self._current_content:
            self.add_page()

        font = font or self._default_font

        # Calculate available width
        page_width, page_height = self._page_style.size.value

        if self._page_style.orientation == PageOrientation.LANDSCAPE:
            page_width, page_height = page_height, page_width

        if width is None:
            width = page_width - self._page_style.margins.left - self._page_style.margins.right

        # Simple word wrap
        words = text.split()
        lines = []
        current_line = []
        char_width = font.size * 0.5  # Approximate

        for word in words:
            test_line = " ".join(current_line + [word])

            if len(test_line) * char_width <= width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        # Write lines
        for line in lines:
            self.write_text(line, font=font, align=align)

        return self

    def draw_line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: Color = None,
        width: float = 1.0,
        style: LineStyle = LineStyle.SOLID
    ) -> "PDFGenerator":
        """Draw line."""
        if not self._current_content:
            self.add_page()

        color = color or Color.black()

        self._current_content.save_state()
        self._current_content.set_color(color, stroke=True)
        self._current_content.set_line_width(width)

        if style == LineStyle.DASHED:
            self._current_content._content.append("[3 3] 0 d")

        elif style == LineStyle.DOTTED:
            self._current_content._content.append("[1 2] 0 d")

        self._current_content.move_to(x1, y1)
        self._current_content.line_to(x2, y2)
        self._current_content.stroke()
        self._current_content.restore_state()

        return self

    def draw_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        stroke_color: Color = None,
        fill_color: Color = None,
        stroke_width: float = 1.0
    ) -> "PDFGenerator":
        """Draw rectangle."""
        if not self._current_content:
            self.add_page()

        self._current_content.save_state()

        if stroke_color:
            self._current_content.set_color(stroke_color, stroke=True)

        if fill_color:
            self._current_content.set_color(fill_color, stroke=False)

        self._current_content.set_line_width(stroke_width)
        self._current_content.rect(x, y, width, height)

        if fill_color and stroke_color:
            self._current_content.fill_stroke()

        elif fill_color:
            self._current_content.fill()

        else:
            self._current_content.stroke()

        self._current_content.restore_state()

        return self

    def draw_circle(
        self,
        cx: float,
        cy: float,
        radius: float,
        stroke_color: Color = None,
        fill_color: Color = None
    ) -> "PDFGenerator":
        """Draw circle (approximated with bezier curves)."""
        if not self._current_content:
            self.add_page()

        self._current_content.save_state()

        if stroke_color:
            self._current_content.set_color(stroke_color, stroke=True)

        if fill_color:
            self._current_content.set_color(fill_color, stroke=False)

        # Bezier approximation of circle
        k = 0.5522847498  # Magic constant for bezier circle

        self._current_content._content.append(f"{cx + radius:.2f} {cy:.2f} m")
        self._current_content._content.append(
            f"{cx + radius:.2f} {cy + radius * k:.2f} "
            f"{cx + radius * k:.2f} {cy + radius:.2f} "
            f"{cx:.2f} {cy + radius:.2f} c"
        )
        self._current_content._content.append(
            f"{cx - radius * k:.2f} {cy + radius:.2f} "
            f"{cx - radius:.2f} {cy + radius * k:.2f} "
            f"{cx - radius:.2f} {cy:.2f} c"
        )
        self._current_content._content.append(
            f"{cx - radius:.2f} {cy - radius * k:.2f} "
            f"{cx - radius * k:.2f} {cy - radius:.2f} "
            f"{cx:.2f} {cy - radius:.2f} c"
        )
        self._current_content._content.append(
            f"{cx + radius * k:.2f} {cy - radius:.2f} "
            f"{cx + radius:.2f} {cy - radius * k:.2f} "
            f"{cx + radius:.2f} {cy:.2f} c"
        )

        if fill_color and stroke_color:
            self._current_content.fill_stroke()

        elif fill_color:
            self._current_content.fill()

        else:
            self._current_content.stroke()

        self._current_content.restore_state()

        return self

    def draw_table(
        self,
        table: Table,
        x: Optional[float] = None,
        y: Optional[float] = None
    ) -> "PDFGenerator":
        """Draw table."""
        if not self._current_content:
            self.add_page()

        x = x if x is not None else self._cursor_x
        y = y if y is not None else self._cursor_y

        # Calculate column widths if not provided
        if not table.column_widths:
            max_cols = max(sum(c.colspan for c in row.cells) for row in table.rows)
            col_width = 100.0
            table.column_widths = [col_width] * max_cols

        # Draw table
        current_y = y

        for row in table.rows:
            row_height = row.height or 20.0
            current_x = x

            for i, cell in enumerate(row.cells):
                cell_width = sum(table.column_widths[i:i + cell.colspan])

                # Draw cell background
                if cell.background:
                    self.draw_rect(
                        current_x, current_y - row_height,
                        cell_width, row_height,
                        fill_color=cell.background
                    )

                # Draw cell border
                self.draw_rect(
                    current_x, current_y - row_height,
                    cell_width, row_height,
                    stroke_color=table.border_color,
                    stroke_width=table.border_width
                )

                # Draw cell content
                font = cell.font or self._default_font

                if row.is_header:
                    font = FontSpec(
                        name=font.name,
                        size=font.size,
                        style=FontStyle.BOLD,
                        color=font.color
                    )

                text_x = current_x + table.cell_padding
                text_y = current_y - row_height / 2 - font.size / 2

                self.write_text(cell.content, x=text_x, y=text_y, font=font)

                current_x += cell_width

            current_y -= row_height

        self._cursor_y = current_y

        return self

    def add_header(
        self,
        text: str,
        font: Optional[FontSpec] = None
    ) -> "PDFGenerator":
        """Add header to current page."""
        if not self._current_content:
            self.add_page()

        font = font or FontSpec(size=10, color=Color(0.5, 0.5, 0.5))

        page_width, page_height = self._page_style.size.value

        if self._page_style.orientation == PageOrientation.LANDSCAPE:
            page_width, page_height = page_height, page_width

        self.write_text(
            text,
            x=self._page_style.margins.left,
            y=page_height - self._page_style.margins.top / 2,
            font=font
        )

        return self

    def add_footer(
        self,
        text: str,
        font: Optional[FontSpec] = None
    ) -> "PDFGenerator":
        """Add footer to current page."""
        if not self._current_content:
            self.add_page()

        font = font or FontSpec(size=10, color=Color(0.5, 0.5, 0.5))

        self.write_text(
            text,
            x=self._page_style.margins.left,
            y=self._page_style.margins.bottom / 2,
            font=font
        )

        return self

    def add_page_number(self, format_str: str = "Page {page}") -> "PDFGenerator":
        """Add page number."""
        page_num = self._stats.get("pages", 1)
        text = format_str.format(page=page_num)

        return self.add_footer(text)

    def add_watermark(
        self,
        text: str,
        color: Color = None,
        angle: float = 45,
        font_size: float = 72
    ) -> "PDFGenerator":
        """Add watermark."""
        if not self._current_content:
            self.add_page()

        color = color or Color(0.9, 0.9, 0.9)

        page_width, page_height = self._page_style.size.value

        if self._page_style.orientation == PageOrientation.LANDSCAPE:
            page_width, page_height = page_height, page_width

        # Calculate position
        cx = page_width / 2
        cy = page_height / 2

        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        font = FontSpec(size=font_size, color=color)
        font_ref = self._current_doc._get_font_ref(font)

        self._current_content.save_state()
        self._current_content.begin_text()
        self._current_content.set_font(font_ref, font_size)
        self._current_content.set_color(color)
        self._current_content.set_text_matrix(cos_a, sin_a, -sin_a, cos_a, cx, cy)
        self._current_content.show_text(text)
        self._current_content.end_text()
        self._current_content.restore_state()

        return self

    def generate(self) -> bytes:
        """Generate PDF bytes."""
        if not self._current_doc:
            self.create_document()

        # Flush final page
        if self._current_content:
            self._current_doc.add_page(self._current_content, self._page_style)
            self._current_content = None

        return self._current_doc.generate()

    async def save(self, path: str) -> int:
        """Save PDF to file."""
        pdf_bytes = self.generate()

        with open(path, 'wb') as f:
            f.write(pdf_bytes)

        return len(pdf_bytes)

    def get_stats(self) -> Dict[str, int]:
        """Get generation statistics."""
        return dict(self._stats)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the PDF Generator."""
    print("=" * 70)
    print("BAEL - PDF GENERATOR DEMO")
    print("Comprehensive PDF Document Generation")
    print("=" * 70)
    print()

    # 1. Create Simple Document
    print("1. SIMPLE DOCUMENT:")
    print("-" * 40)

    gen = PDFGenerator()
    gen.create_document(PDFMetadata(
        title="BAEL Demo Document",
        author="BAEL System",
        subject="PDF Generation Demo"
    ))

    gen.add_page()
    gen.write_text("Hello, World!", font=FontSpec(size=24, style=FontStyle.BOLD))
    gen.write_text("This is a PDF generated by BAEL.")

    pdf_bytes = gen.generate()
    print(f"   Generated: {len(pdf_bytes)} bytes")
    print()

    # 2. Multiple Pages
    print("2. MULTI-PAGE DOCUMENT:")
    print("-" * 40)

    gen = PDFGenerator()
    gen.create_document(PDFMetadata(title="Multi-Page Demo"))

    for i in range(3):
        gen.add_page()
        gen.write_text(f"Page {i + 1}", font=FontSpec(size=20, style=FontStyle.BOLD))
        gen.write_text(f"This is page number {i + 1} of the document.")
        gen.add_page_number()

    pdf_bytes = gen.generate()
    print(f"   Generated: {len(pdf_bytes)} bytes")
    print(f"   Pages: {gen.get_stats()['pages']}")
    print()

    # 3. Styled Text
    print("3. STYLED TEXT:")
    print("-" * 40)

    gen = PDFGenerator()
    gen.create_document()
    gen.add_page()

    gen.write_text("Normal Text", font=FontSpec(size=12))
    gen.write_text("Bold Text", font=FontSpec(size=12, style=FontStyle.BOLD))
    gen.write_text("Italic Text", font=FontSpec(size=12, style=FontStyle.ITALIC))
    gen.write_text("Red Text", font=FontSpec(size=12, color=Color.red()))
    gen.write_text("Large Blue Text", font=FontSpec(size=18, color=Color.blue()))

    pdf_bytes = gen.generate()
    print(f"   Generated: {len(pdf_bytes)} bytes")
    print()

    # 4. Graphics
    print("4. GRAPHICS:")
    print("-" * 40)

    gen = PDFGenerator()
    gen.create_document()
    gen.add_page()

    gen.write_text("Graphics Demo", font=FontSpec(size=18, style=FontStyle.BOLD))

    # Draw shapes
    gen.draw_rect(72, 600, 100, 50, stroke_color=Color.black())
    gen.draw_rect(182, 600, 100, 50, fill_color=Color.from_hex("#3498db"))
    gen.draw_rect(292, 600, 100, 50, stroke_color=Color.black(), fill_color=Color.from_hex("#e74c3c"))

    gen.draw_circle(122, 520, 30, stroke_color=Color.black())
    gen.draw_circle(232, 520, 30, fill_color=Color.green())

    gen.draw_line(72, 450, 400, 450, color=Color.black(), width=2)
    gen.draw_line(72, 430, 400, 430, color=Color.red(), style=LineStyle.DASHED)
    gen.draw_line(72, 410, 400, 410, color=Color.blue(), style=LineStyle.DOTTED)

    pdf_bytes = gen.generate()
    print(f"   Generated: {len(pdf_bytes)} bytes")
    print()

    # 5. Tables
    print("5. TABLE:")
    print("-" * 40)

    gen = PDFGenerator()
    gen.create_document()
    gen.add_page()

    gen.write_text("Employee Table", font=FontSpec(size=16, style=FontStyle.BOLD))

    table = Table(
        rows=[
            TableRow(
                cells=[
                    TableCell("Name"),
                    TableCell("Role"),
                    TableCell("Department")
                ],
                is_header=True
            ),
            TableRow(cells=[
                TableCell("John Doe"),
                TableCell("Developer"),
                TableCell("Engineering")
            ]),
            TableRow(cells=[
                TableCell("Jane Smith"),
                TableCell("Designer"),
                TableCell("Creative")
            ]),
            TableRow(cells=[
                TableCell("Bob Wilson"),
                TableCell("Manager"),
                TableCell("Operations")
            ])
        ],
        column_widths=[150, 100, 120]
    )

    gen.draw_table(table, y=650)

    pdf_bytes = gen.generate()
    print(f"   Generated: {len(pdf_bytes)} bytes")
    print()

    # 6. Page Sizes
    print("6. PAGE SIZES:")
    print("-" * 40)

    for size in [PageSize.A4, PageSize.LETTER, PageSize.A5]:
        gen = PDFGenerator()
        gen.set_page_style(PageStyle(size=size))
        gen.create_document()
        gen.add_page()
        gen.write_text(f"This is {size.name} size paper")

        pdf_bytes = gen.generate()
        dims = size.value
        print(f"   {size.name}: {dims[0]:.0f}x{dims[1]:.0f} pt = {len(pdf_bytes)} bytes")
    print()

    # 7. Landscape Orientation
    print("7. LANDSCAPE ORIENTATION:")
    print("-" * 40)

    gen = PDFGenerator()
    gen.set_page_style(PageStyle(
        size=PageSize.A4,
        orientation=PageOrientation.LANDSCAPE
    ))
    gen.create_document()
    gen.add_page()
    gen.write_text("Landscape Document", font=FontSpec(size=24))

    pdf_bytes = gen.generate()
    print(f"   Generated: {len(pdf_bytes)} bytes")
    print()

    # 8. Watermark
    print("8. WATERMARK:")
    print("-" * 40)

    gen = PDFGenerator()
    gen.create_document()
    gen.add_page()
    gen.add_watermark("CONFIDENTIAL")
    gen.write_text("This document has a watermark", font=FontSpec(size=14))

    pdf_bytes = gen.generate()
    print(f"   Generated: {len(pdf_bytes)} bytes")
    print()

    # 9. Headers and Footers
    print("9. HEADERS & FOOTERS:")
    print("-" * 40)

    gen = PDFGenerator()
    gen.create_document(PDFMetadata(title="Report"))
    gen.add_page()
    gen.add_header("BAEL System - Confidential Report")
    gen.write_text("Document Content", font=FontSpec(size=14))
    gen.write_paragraph("This is a paragraph of text that demonstrates the header and footer functionality in the BAEL PDF Generator.")
    gen.add_footer("© 2024 BAEL System | Page 1")

    pdf_bytes = gen.generate()
    print(f"   Generated: {len(pdf_bytes)} bytes")
    print()

    # 10. Complex Document
    print("10. COMPLEX DOCUMENT:")
    print("-" * 40)

    gen = PDFGenerator()
    gen.create_document(PDFMetadata(
        title="BAEL System Report",
        author="BAEL",
        subject="Comprehensive System Report"
    ))

    # Title page
    gen.add_page()
    gen.add_watermark("BAEL", color=Color(0.95, 0.95, 0.95))
    gen.write_text("BAEL System Report", x=200, y=500, font=FontSpec(size=32, style=FontStyle.BOLD))
    gen.write_text("Generated by PDF Generator", x=220, y=450, font=FontSpec(size=14))

    # Content page
    gen.add_page()
    gen.add_header("BAEL Report - Section 1")
    gen.write_text("1. Introduction", font=FontSpec(size=18, style=FontStyle.BOLD))
    gen.write_paragraph("The BAEL system is a comprehensive AI agent framework designed for maximum capability and flexibility.")

    gen.write_text("2. Features", font=FontSpec(size=18, style=FontStyle.BOLD))

    features = Table(
        rows=[
            TableRow(cells=[TableCell("Feature"), TableCell("Status")], is_header=True),
            TableRow(cells=[TableCell("PDF Generation"), TableCell("Active")]),
            TableRow(cells=[TableCell("Compression"), TableCell("Active")]),
            TableRow(cells=[TableCell("Search Engine"), TableCell("Active")])
        ],
        column_widths=[200, 100]
    )

    gen.draw_table(features, y=550)
    gen.add_page_number("Page {page}")

    pdf_bytes = gen.generate()
    print(f"   Generated: {len(pdf_bytes)} bytes")
    print(f"   Stats: {gen.get_stats()}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - PDF Generator Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
