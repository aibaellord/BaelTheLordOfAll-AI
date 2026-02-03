#!/usr/bin/env python3
"""
BAEL - Image Processor
Comprehensive image manipulation and processing system.

Features:
- Image loading and saving
- Color manipulation
- Transformations (resize, crop, rotate)
- Filters and effects
- Format conversion
- Histogram analysis
- Watermarking
- Batch processing
- Thumbnail generation
- Metadata extraction
"""

import asyncio
import base64
import hashlib
import io
import json
import logging
import math
import struct
import uuid
import zlib
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

class ImageFormat(Enum):
    """Supported image formats."""
    PNG = "png"
    PPM = "ppm"
    BMP = "bmp"
    RAW = "raw"


class ResizeMode(Enum):
    """Resize mode."""
    STRETCH = "stretch"
    FIT = "fit"
    FILL = "fill"
    COVER = "cover"


class FlipDirection(Enum):
    """Flip direction."""
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class BlendMode(Enum):
    """Blend mode."""
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    DARKEN = "darken"
    LIGHTEN = "lighten"
    ADD = "add"


class FilterType(Enum):
    """Filter type."""
    BLUR = "blur"
    SHARPEN = "sharpen"
    EDGE = "edge"
    EMBOSS = "emboss"
    GRAYSCALE = "grayscale"
    SEPIA = "sepia"
    INVERT = "invert"
    BRIGHTNESS = "brightness"
    CONTRAST = "contrast"
    SATURATION = "saturation"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Color:
    """RGBA color."""
    r: int = 0
    g: int = 0
    b: int = 0
    a: int = 255

    def __post_init__(self):
        self.r = max(0, min(255, self.r))
        self.g = max(0, min(255, self.g))
        self.b = max(0, min(255, self.b))
        self.a = max(0, min(255, self.a))

    @classmethod
    def from_hex(cls, hex_str: str) -> "Color":
        """Create from hex string."""
        hex_str = hex_str.lstrip('#')

        if len(hex_str) == 6:
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            return cls(r, g, b)
        elif len(hex_str) == 8:
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            a = int(hex_str[6:8], 16)
            return cls(r, g, b, a)

        return cls()

    def to_hex(self, include_alpha: bool = False) -> str:
        """Convert to hex string."""
        if include_alpha:
            return f"#{self.r:02x}{self.g:02x}{self.b:02x}{self.a:02x}"
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"

    def to_tuple(self) -> Tuple[int, int, int, int]:
        return (self.r, self.g, self.b, self.a)

    def luminance(self) -> float:
        """Calculate luminance."""
        return 0.299 * self.r + 0.587 * self.g + 0.114 * self.b

    def grayscale(self) -> "Color":
        """Convert to grayscale."""
        gray = int(self.luminance())
        return Color(gray, gray, gray, self.a)


@dataclass
class Point:
    """2D point."""
    x: int
    y: int


@dataclass
class Rectangle:
    """Rectangle."""
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def contains(self, point: Point) -> bool:
        return (
            self.x <= point.x < self.right and
            self.y <= point.y < self.bottom
        )


@dataclass
class ImageMetadata:
    """Image metadata."""
    width: int = 0
    height: int = 0
    format: ImageFormat = ImageFormat.PNG
    channels: int = 4
    bit_depth: int = 8
    file_size: int = 0
    created: Optional[datetime] = None
    modified: Optional[datetime] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Histogram:
    """Image histogram."""
    red: List[int] = field(default_factory=lambda: [0] * 256)
    green: List[int] = field(default_factory=lambda: [0] * 256)
    blue: List[int] = field(default_factory=lambda: [0] * 256)
    luminance: List[int] = field(default_factory=lambda: [0] * 256)


# =============================================================================
# IMAGE CLASS
# =============================================================================

class Image:
    """
    Image class with pixel manipulation.
    Pure Python implementation.
    """

    def __init__(self, width: int, height: int, fill: Optional[Color] = None):
        self.width = width
        self.height = height
        self._pixels: List[List[Color]] = []

        fill_color = fill or Color(0, 0, 0, 0)

        for y in range(height):
            row = [Color(fill_color.r, fill_color.g, fill_color.b, fill_color.a)
                   for _ in range(width)]
            self._pixels.append(row)

    def get_pixel(self, x: int, y: int) -> Color:
        """Get pixel color."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self._pixels[y][x]
        return Color()

    def set_pixel(self, x: int, y: int, color: Color) -> None:
        """Set pixel color."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self._pixels[y][x] = color

    def fill(self, color: Color) -> None:
        """Fill entire image with color."""
        for y in range(self.height):
            for x in range(self.width):
                self._pixels[y][x] = Color(color.r, color.g, color.b, color.a)

    def clone(self) -> "Image":
        """Create a copy of the image."""
        new_img = Image(self.width, self.height)

        for y in range(self.height):
            for x in range(self.width):
                c = self._pixels[y][x]
                new_img._pixels[y][x] = Color(c.r, c.g, c.b, c.a)

        return new_img

    def get_metadata(self) -> ImageMetadata:
        """Get image metadata."""
        return ImageMetadata(
            width=self.width,
            height=self.height,
            format=ImageFormat.PNG,
            channels=4,
            bit_depth=8
        )

    def get_histogram(self) -> Histogram:
        """Calculate histogram."""
        hist = Histogram()

        for y in range(self.height):
            for x in range(self.width):
                c = self._pixels[y][x]
                hist.red[c.r] += 1
                hist.green[c.g] += 1
                hist.blue[c.b] += 1
                lum = int(c.luminance())
                hist.luminance[lum] += 1

        return hist

    def __repr__(self) -> str:
        return f"Image({self.width}x{self.height})"


# =============================================================================
# FILTERS
# =============================================================================

class Filter(ABC):
    """Abstract filter."""

    @abstractmethod
    def apply(self, image: Image) -> Image:
        """Apply filter to image."""
        pass


class GrayscaleFilter(Filter):
    """Grayscale filter."""

    def apply(self, image: Image) -> Image:
        result = image.clone()

        for y in range(result.height):
            for x in range(result.width):
                c = result.get_pixel(x, y)
                gray = c.grayscale()
                result.set_pixel(x, y, gray)

        return result


class SepiaFilter(Filter):
    """Sepia tone filter."""

    def apply(self, image: Image) -> Image:
        result = image.clone()

        for y in range(result.height):
            for x in range(result.width):
                c = result.get_pixel(x, y)

                tr = int(0.393 * c.r + 0.769 * c.g + 0.189 * c.b)
                tg = int(0.349 * c.r + 0.686 * c.g + 0.168 * c.b)
                tb = int(0.272 * c.r + 0.534 * c.g + 0.131 * c.b)

                result.set_pixel(x, y, Color(
                    min(255, tr),
                    min(255, tg),
                    min(255, tb),
                    c.a
                ))

        return result


class InvertFilter(Filter):
    """Invert colors filter."""

    def apply(self, image: Image) -> Image:
        result = image.clone()

        for y in range(result.height):
            for x in range(result.width):
                c = result.get_pixel(x, y)
                result.set_pixel(x, y, Color(
                    255 - c.r,
                    255 - c.g,
                    255 - c.b,
                    c.a
                ))

        return result


class BrightnessFilter(Filter):
    """Brightness adjustment filter."""

    def __init__(self, factor: float = 1.0):
        self.factor = factor

    def apply(self, image: Image) -> Image:
        result = image.clone()

        for y in range(result.height):
            for x in range(result.width):
                c = result.get_pixel(x, y)
                result.set_pixel(x, y, Color(
                    int(max(0, min(255, c.r * self.factor))),
                    int(max(0, min(255, c.g * self.factor))),
                    int(max(0, min(255, c.b * self.factor))),
                    c.a
                ))

        return result


class ContrastFilter(Filter):
    """Contrast adjustment filter."""

    def __init__(self, factor: float = 1.0):
        self.factor = factor

    def apply(self, image: Image) -> Image:
        result = image.clone()

        for y in range(result.height):
            for x in range(result.width):
                c = result.get_pixel(x, y)

                r = int(max(0, min(255, (c.r - 128) * self.factor + 128)))
                g = int(max(0, min(255, (c.g - 128) * self.factor + 128)))
                b = int(max(0, min(255, (c.b - 128) * self.factor + 128)))

                result.set_pixel(x, y, Color(r, g, b, c.a))

        return result


class ConvolutionFilter(Filter):
    """Convolution-based filter."""

    def __init__(self, kernel: List[List[float]], divisor: float = 1.0):
        self.kernel = kernel
        self.divisor = divisor
        self.size = len(kernel)
        self.offset = self.size // 2

    def apply(self, image: Image) -> Image:
        result = image.clone()

        for y in range(result.height):
            for x in range(result.width):
                r, g, b = 0.0, 0.0, 0.0

                for ky in range(self.size):
                    for kx in range(self.size):
                        px = x + kx - self.offset
                        py = y + ky - self.offset

                        # Edge handling
                        px = max(0, min(image.width - 1, px))
                        py = max(0, min(image.height - 1, py))

                        c = image.get_pixel(px, py)
                        k = self.kernel[ky][kx]

                        r += c.r * k
                        g += c.g * k
                        b += c.b * k

                r = int(max(0, min(255, r / self.divisor)))
                g = int(max(0, min(255, g / self.divisor)))
                b = int(max(0, min(255, b / self.divisor)))

                result.set_pixel(x, y, Color(r, g, b, image.get_pixel(x, y).a))

        return result


class BlurFilter(ConvolutionFilter):
    """Blur filter."""

    def __init__(self, radius: int = 1):
        size = radius * 2 + 1
        kernel = [[1.0] * size for _ in range(size)]
        super().__init__(kernel, size * size)


class SharpenFilter(ConvolutionFilter):
    """Sharpen filter."""

    def __init__(self):
        kernel = [
            [0, -1, 0],
            [-1, 5, -1],
            [0, -1, 0]
        ]
        super().__init__(kernel)


class EdgeFilter(ConvolutionFilter):
    """Edge detection filter."""

    def __init__(self):
        kernel = [
            [-1, -1, -1],
            [-1, 8, -1],
            [-1, -1, -1]
        ]
        super().__init__(kernel)


class EmbossFilter(ConvolutionFilter):
    """Emboss filter."""

    def __init__(self):
        kernel = [
            [-2, -1, 0],
            [-1, 1, 1],
            [0, 1, 2]
        ]
        super().__init__(kernel)


# =============================================================================
# TRANSFORMATIONS
# =============================================================================

class Transform(ABC):
    """Abstract transformation."""

    @abstractmethod
    def apply(self, image: Image) -> Image:
        """Apply transformation."""
        pass


class ResizeTransform(Transform):
    """Resize transformation."""

    def __init__(
        self,
        width: int,
        height: int,
        mode: ResizeMode = ResizeMode.STRETCH
    ):
        self.target_width = width
        self.target_height = height
        self.mode = mode

    def apply(self, image: Image) -> Image:
        """Resize using nearest neighbor."""
        result = Image(self.target_width, self.target_height)

        x_ratio = image.width / self.target_width
        y_ratio = image.height / self.target_height

        for y in range(self.target_height):
            for x in range(self.target_width):
                src_x = int(x * x_ratio)
                src_y = int(y * y_ratio)

                src_x = min(src_x, image.width - 1)
                src_y = min(src_y, image.height - 1)

                result.set_pixel(x, y, image.get_pixel(src_x, src_y))

        return result


class CropTransform(Transform):
    """Crop transformation."""

    def __init__(self, rect: Rectangle):
        self.rect = rect

    def apply(self, image: Image) -> Image:
        result = Image(self.rect.width, self.rect.height)

        for y in range(self.rect.height):
            for x in range(self.rect.width):
                src_x = self.rect.x + x
                src_y = self.rect.y + y

                if 0 <= src_x < image.width and 0 <= src_y < image.height:
                    result.set_pixel(x, y, image.get_pixel(src_x, src_y))

        return result


class RotateTransform(Transform):
    """Rotate transformation."""

    def __init__(self, degrees: float):
        self.degrees = degrees
        self.radians = math.radians(degrees)

    def apply(self, image: Image) -> Image:
        cos_a = math.cos(self.radians)
        sin_a = math.sin(self.radians)

        # Calculate new dimensions
        corners = [
            (0, 0),
            (image.width, 0),
            (0, image.height),
            (image.width, image.height)
        ]

        rotated = []
        for x, y in corners:
            rx = x * cos_a - y * sin_a
            ry = x * sin_a + y * cos_a
            rotated.append((rx, ry))

        min_x = min(r[0] for r in rotated)
        max_x = max(r[0] for r in rotated)
        min_y = min(r[1] for r in rotated)
        max_y = max(r[1] for r in rotated)

        new_width = int(max_x - min_x)
        new_height = int(max_y - min_y)

        result = Image(new_width, new_height)

        cx = image.width / 2
        cy = image.height / 2
        ncx = new_width / 2
        ncy = new_height / 2

        for y in range(new_height):
            for x in range(new_width):
                # Transform back to source
                dx = x - ncx
                dy = y - ncy

                src_x = dx * cos_a + dy * sin_a + cx
                src_y = -dx * sin_a + dy * cos_a + cy

                if 0 <= src_x < image.width and 0 <= src_y < image.height:
                    result.set_pixel(x, y, image.get_pixel(int(src_x), int(src_y)))

        return result


class FlipTransform(Transform):
    """Flip transformation."""

    def __init__(self, direction: FlipDirection):
        self.direction = direction

    def apply(self, image: Image) -> Image:
        result = Image(image.width, image.height)

        for y in range(image.height):
            for x in range(image.width):
                if self.direction == FlipDirection.HORIZONTAL:
                    result.set_pixel(image.width - 1 - x, y, image.get_pixel(x, y))
                else:
                    result.set_pixel(x, image.height - 1 - y, image.get_pixel(x, y))

        return result


# =============================================================================
# DRAWING
# =============================================================================

class DrawingContext:
    """Drawing operations on image."""

    def __init__(self, image: Image):
        self.image = image

    def draw_line(
        self,
        x1: int, y1: int,
        x2: int, y2: int,
        color: Color
    ) -> None:
        """Draw line using Bresenham's algorithm."""
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        x, y = x1, y1

        while True:
            self.image.set_pixel(x, y, color)

            if x == x2 and y == y2:
                break

            e2 = 2 * err

            if e2 > -dy:
                err -= dy
                x += sx

            if e2 < dx:
                err += dx
                y += sy

    def draw_rect(
        self,
        rect: Rectangle,
        color: Color,
        fill: bool = False
    ) -> None:
        """Draw rectangle."""
        if fill:
            for y in range(rect.y, rect.bottom):
                for x in range(rect.x, rect.right):
                    self.image.set_pixel(x, y, color)
        else:
            # Top and bottom
            for x in range(rect.x, rect.right):
                self.image.set_pixel(x, rect.y, color)
                self.image.set_pixel(x, rect.bottom - 1, color)

            # Left and right
            for y in range(rect.y, rect.bottom):
                self.image.set_pixel(rect.x, y, color)
                self.image.set_pixel(rect.right - 1, y, color)

    def draw_circle(
        self,
        cx: int, cy: int,
        radius: int,
        color: Color,
        fill: bool = False
    ) -> None:
        """Draw circle using midpoint algorithm."""
        if fill:
            for y in range(cy - radius, cy + radius + 1):
                for x in range(cx - radius, cx + radius + 1):
                    dx = x - cx
                    dy = y - cy
                    if dx * dx + dy * dy <= radius * radius:
                        self.image.set_pixel(x, y, color)
        else:
            x = radius
            y = 0
            d = 1 - radius

            while x >= y:
                self.image.set_pixel(cx + x, cy + y, color)
                self.image.set_pixel(cx - x, cy + y, color)
                self.image.set_pixel(cx + x, cy - y, color)
                self.image.set_pixel(cx - x, cy - y, color)
                self.image.set_pixel(cx + y, cy + x, color)
                self.image.set_pixel(cx - y, cy + x, color)
                self.image.set_pixel(cx + y, cy - x, color)
                self.image.set_pixel(cx - y, cy - x, color)

                y += 1

                if d <= 0:
                    d += 2 * y + 1
                else:
                    x -= 1
                    d += 2 * (y - x) + 1

    def flood_fill(self, x: int, y: int, color: Color) -> None:
        """Flood fill from point."""
        if not (0 <= x < self.image.width and 0 <= y < self.image.height):
            return

        target = self.image.get_pixel(x, y)

        if target.to_tuple() == color.to_tuple():
            return

        stack = [(x, y)]
        visited = set()

        while stack:
            cx, cy = stack.pop()

            if (cx, cy) in visited:
                continue

            if not (0 <= cx < self.image.width and 0 <= cy < self.image.height):
                continue

            if self.image.get_pixel(cx, cy).to_tuple() != target.to_tuple():
                continue

            visited.add((cx, cy))
            self.image.set_pixel(cx, cy, color)

            stack.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])


# =============================================================================
# BLENDING
# =============================================================================

class Blender:
    """Image blending operations."""

    @staticmethod
    def blend(
        base: Image,
        overlay: Image,
        x: int = 0,
        y: int = 0,
        mode: BlendMode = BlendMode.NORMAL,
        opacity: float = 1.0
    ) -> Image:
        """Blend overlay onto base."""
        result = base.clone()

        for oy in range(overlay.height):
            for ox in range(overlay.width):
                bx = x + ox
                by = y + oy

                if not (0 <= bx < result.width and 0 <= by < result.height):
                    continue

                bc = result.get_pixel(bx, by)
                oc = overlay.get_pixel(ox, oy)

                # Apply opacity
                alpha = (oc.a / 255) * opacity

                # Blend based on mode
                if mode == BlendMode.NORMAL:
                    nr = int(bc.r * (1 - alpha) + oc.r * alpha)
                    ng = int(bc.g * (1 - alpha) + oc.g * alpha)
                    nb = int(bc.b * (1 - alpha) + oc.b * alpha)

                elif mode == BlendMode.MULTIPLY:
                    nr = int((bc.r * oc.r / 255) * alpha + bc.r * (1 - alpha))
                    ng = int((bc.g * oc.g / 255) * alpha + bc.g * (1 - alpha))
                    nb = int((bc.b * oc.b / 255) * alpha + bc.b * (1 - alpha))

                elif mode == BlendMode.SCREEN:
                    sr = 255 - ((255 - bc.r) * (255 - oc.r) // 255)
                    sg = 255 - ((255 - bc.g) * (255 - oc.g) // 255)
                    sb = 255 - ((255 - bc.b) * (255 - oc.b) // 255)
                    nr = int(sr * alpha + bc.r * (1 - alpha))
                    ng = int(sg * alpha + bc.g * (1 - alpha))
                    nb = int(sb * alpha + bc.b * (1 - alpha))

                elif mode == BlendMode.ADD:
                    nr = int(min(255, bc.r + oc.r) * alpha + bc.r * (1 - alpha))
                    ng = int(min(255, bc.g + oc.g) * alpha + bc.g * (1 - alpha))
                    nb = int(min(255, bc.b + oc.b) * alpha + bc.b * (1 - alpha))

                elif mode == BlendMode.DARKEN:
                    nr = int(min(bc.r, oc.r) * alpha + bc.r * (1 - alpha))
                    ng = int(min(bc.g, oc.g) * alpha + bc.g * (1 - alpha))
                    nb = int(min(bc.b, oc.b) * alpha + bc.b * (1 - alpha))

                elif mode == BlendMode.LIGHTEN:
                    nr = int(max(bc.r, oc.r) * alpha + bc.r * (1 - alpha))
                    ng = int(max(bc.g, oc.g) * alpha + bc.g * (1 - alpha))
                    nb = int(max(bc.b, oc.b) * alpha + bc.b * (1 - alpha))

                else:
                    nr, ng, nb = bc.r, bc.g, bc.b

                result.set_pixel(bx, by, Color(
                    max(0, min(255, nr)),
                    max(0, min(255, ng)),
                    max(0, min(255, nb)),
                    bc.a
                ))

        return result


# =============================================================================
# SERIALIZATION
# =============================================================================

class ImageSerializer:
    """Serialize/deserialize images."""

    @staticmethod
    def to_ppm(image: Image) -> bytes:
        """Convert to PPM format."""
        header = f"P6\n{image.width} {image.height}\n255\n"
        data = bytearray(header.encode('ascii'))

        for y in range(image.height):
            for x in range(image.width):
                c = image.get_pixel(x, y)
                data.extend([c.r, c.g, c.b])

        return bytes(data)

    @staticmethod
    def from_ppm(data: bytes) -> Optional[Image]:
        """Load from PPM format."""
        try:
            lines = data.split(b'\n', 3)

            if lines[0] != b'P6':
                return None

            dims = lines[1].decode().split()
            width, height = int(dims[0]), int(dims[1])

            # Skip header
            header_end = data.find(b'\n', data.find(b'\n', data.find(b'\n') + 1) + 1) + 1
            pixel_data = data[header_end:]

            image = Image(width, height)
            idx = 0

            for y in range(height):
                for x in range(width):
                    r = pixel_data[idx]
                    g = pixel_data[idx + 1]
                    b = pixel_data[idx + 2]
                    idx += 3

                    image.set_pixel(x, y, Color(r, g, b))

            return image
        except:
            return None

    @staticmethod
    def to_raw(image: Image) -> bytes:
        """Convert to raw RGBA bytes."""
        data = bytearray()

        # Header: width, height (4 bytes each)
        data.extend(struct.pack('>II', image.width, image.height))

        # Pixel data
        for y in range(image.height):
            for x in range(image.width):
                c = image.get_pixel(x, y)
                data.extend([c.r, c.g, c.b, c.a])

        return bytes(data)

    @staticmethod
    def from_raw(data: bytes) -> Optional[Image]:
        """Load from raw format."""
        try:
            width, height = struct.unpack('>II', data[:8])

            image = Image(width, height)
            idx = 8

            for y in range(height):
                for x in range(width):
                    r = data[idx]
                    g = data[idx + 1]
                    b = data[idx + 2]
                    a = data[idx + 3]
                    idx += 4

                    image.set_pixel(x, y, Color(r, g, b, a))

            return image
        except:
            return None


# =============================================================================
# IMAGE PROCESSOR
# =============================================================================

class ImageProcessor:
    """
    Comprehensive Image Processor for BAEL.

    Provides image manipulation and processing capabilities.
    """

    def __init__(self):
        self._filters: Dict[FilterType, Filter] = {
            FilterType.GRAYSCALE: GrayscaleFilter(),
            FilterType.SEPIA: SepiaFilter(),
            FilterType.INVERT: InvertFilter(),
            FilterType.BLUR: BlurFilter(),
            FilterType.SHARPEN: SharpenFilter(),
            FilterType.EDGE: EdgeFilter(),
            FilterType.EMBOSS: EmbossFilter(),
        }
        self._stats: Dict[str, int] = defaultdict(int)

    # -------------------------------------------------------------------------
    # IMAGE CREATION
    # -------------------------------------------------------------------------

    def create_image(
        self,
        width: int,
        height: int,
        fill: Optional[Color] = None
    ) -> Image:
        """Create new image."""
        self._stats["images_created"] += 1
        return Image(width, height, fill)

    def create_gradient(
        self,
        width: int,
        height: int,
        start_color: Color,
        end_color: Color,
        horizontal: bool = True
    ) -> Image:
        """Create gradient image."""
        image = Image(width, height)

        for y in range(height):
            for x in range(width):
                if horizontal:
                    t = x / max(1, width - 1)
                else:
                    t = y / max(1, height - 1)

                r = int(start_color.r + (end_color.r - start_color.r) * t)
                g = int(start_color.g + (end_color.g - start_color.g) * t)
                b = int(start_color.b + (end_color.b - start_color.b) * t)
                a = int(start_color.a + (end_color.a - start_color.a) * t)

                image.set_pixel(x, y, Color(r, g, b, a))

        return image

    def create_checkerboard(
        self,
        width: int,
        height: int,
        cell_size: int = 8,
        color1: Optional[Color] = None,
        color2: Optional[Color] = None
    ) -> Image:
        """Create checkerboard pattern."""
        c1 = color1 or Color(255, 255, 255)
        c2 = color2 or Color(200, 200, 200)

        image = Image(width, height)

        for y in range(height):
            for x in range(width):
                cell_x = x // cell_size
                cell_y = y // cell_size

                if (cell_x + cell_y) % 2 == 0:
                    image.set_pixel(x, y, c1)
                else:
                    image.set_pixel(x, y, c2)

        return image

    # -------------------------------------------------------------------------
    # FILTERS
    # -------------------------------------------------------------------------

    def apply_filter(self, image: Image, filter_type: FilterType) -> Image:
        """Apply predefined filter."""
        self._stats["filters_applied"] += 1

        if filter_type in self._filters:
            return self._filters[filter_type].apply(image)

        return image.clone()

    def apply_brightness(self, image: Image, factor: float) -> Image:
        """Adjust brightness."""
        return BrightnessFilter(factor).apply(image)

    def apply_contrast(self, image: Image, factor: float) -> Image:
        """Adjust contrast."""
        return ContrastFilter(factor).apply(image)

    def apply_blur(self, image: Image, radius: int = 1) -> Image:
        """Apply blur."""
        return BlurFilter(radius).apply(image)

    def apply_custom_filter(
        self,
        image: Image,
        kernel: List[List[float]],
        divisor: float = 1.0
    ) -> Image:
        """Apply custom convolution filter."""
        return ConvolutionFilter(kernel, divisor).apply(image)

    # -------------------------------------------------------------------------
    # TRANSFORMATIONS
    # -------------------------------------------------------------------------

    def resize(
        self,
        image: Image,
        width: int,
        height: int,
        mode: ResizeMode = ResizeMode.STRETCH
    ) -> Image:
        """Resize image."""
        self._stats["transforms_applied"] += 1
        return ResizeTransform(width, height, mode).apply(image)

    def crop(self, image: Image, rect: Rectangle) -> Image:
        """Crop image."""
        self._stats["transforms_applied"] += 1
        return CropTransform(rect).apply(image)

    def rotate(self, image: Image, degrees: float) -> Image:
        """Rotate image."""
        self._stats["transforms_applied"] += 1
        return RotateTransform(degrees).apply(image)

    def flip(self, image: Image, direction: FlipDirection) -> Image:
        """Flip image."""
        self._stats["transforms_applied"] += 1
        return FlipTransform(direction).apply(image)

    def thumbnail(
        self,
        image: Image,
        max_size: int
    ) -> Image:
        """Create thumbnail."""
        ratio = min(max_size / image.width, max_size / image.height)
        new_width = int(image.width * ratio)
        new_height = int(image.height * ratio)

        return self.resize(image, new_width, new_height)

    # -------------------------------------------------------------------------
    # BLENDING
    # -------------------------------------------------------------------------

    def blend(
        self,
        base: Image,
        overlay: Image,
        x: int = 0,
        y: int = 0,
        mode: BlendMode = BlendMode.NORMAL,
        opacity: float = 1.0
    ) -> Image:
        """Blend images."""
        return Blender.blend(base, overlay, x, y, mode, opacity)

    def add_watermark(
        self,
        image: Image,
        watermark: Image,
        position: str = "bottom-right",
        margin: int = 10,
        opacity: float = 0.5
    ) -> Image:
        """Add watermark to image."""
        if position == "top-left":
            x, y = margin, margin
        elif position == "top-right":
            x = image.width - watermark.width - margin
            y = margin
        elif position == "bottom-left":
            x = margin
            y = image.height - watermark.height - margin
        else:  # bottom-right
            x = image.width - watermark.width - margin
            y = image.height - watermark.height - margin

        return self.blend(image, watermark, x, y, BlendMode.NORMAL, opacity)

    # -------------------------------------------------------------------------
    # DRAWING
    # -------------------------------------------------------------------------

    def get_drawing_context(self, image: Image) -> DrawingContext:
        """Get drawing context for image."""
        return DrawingContext(image)

    # -------------------------------------------------------------------------
    # ANALYSIS
    # -------------------------------------------------------------------------

    def get_histogram(self, image: Image) -> Histogram:
        """Get image histogram."""
        return image.get_histogram()

    def get_dominant_color(self, image: Image) -> Color:
        """Get dominant color."""
        r_total, g_total, b_total = 0, 0, 0
        count = image.width * image.height

        for y in range(image.height):
            for x in range(image.width):
                c = image.get_pixel(x, y)
                r_total += c.r
                g_total += c.g
                b_total += c.b

        return Color(
            r_total // count,
            g_total // count,
            b_total // count
        )

    def compare(self, image1: Image, image2: Image) -> float:
        """Compare two images, return similarity (0-1)."""
        if image1.width != image2.width or image1.height != image2.height:
            return 0.0

        total_diff = 0
        max_diff = image1.width * image1.height * 255 * 3

        for y in range(image1.height):
            for x in range(image1.width):
                c1 = image1.get_pixel(x, y)
                c2 = image2.get_pixel(x, y)

                total_diff += abs(c1.r - c2.r)
                total_diff += abs(c1.g - c2.g)
                total_diff += abs(c1.b - c2.b)

        return 1.0 - (total_diff / max_diff)

    # -------------------------------------------------------------------------
    # SERIALIZATION
    # -------------------------------------------------------------------------

    def to_bytes(
        self,
        image: Image,
        format: ImageFormat = ImageFormat.RAW
    ) -> bytes:
        """Serialize image to bytes."""
        if format == ImageFormat.PPM:
            return ImageSerializer.to_ppm(image)
        else:
            return ImageSerializer.to_raw(image)

    def from_bytes(
        self,
        data: bytes,
        format: ImageFormat = ImageFormat.RAW
    ) -> Optional[Image]:
        """Deserialize image from bytes."""
        if format == ImageFormat.PPM:
            return ImageSerializer.from_ppm(data)
        else:
            return ImageSerializer.from_raw(data)

    def to_base64(
        self,
        image: Image,
        format: ImageFormat = ImageFormat.RAW
    ) -> str:
        """Convert image to base64."""
        data = self.to_bytes(image, format)
        return base64.b64encode(data).decode('ascii')

    def from_base64(
        self,
        data: str,
        format: ImageFormat = ImageFormat.RAW
    ) -> Optional[Image]:
        """Load image from base64."""
        raw = base64.b64decode(data)
        return self.from_bytes(raw, format)

    # -------------------------------------------------------------------------
    # BATCH PROCESSING
    # -------------------------------------------------------------------------

    async def batch_process(
        self,
        images: List[Image],
        operation: Callable[[Image], Image]
    ) -> List[Image]:
        """Process multiple images."""
        results = []

        for image in images:
            result = operation(image)
            results.append(result)

        return results

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, int]:
        """Get processor statistics."""
        return dict(self._stats)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Image Processor."""
    print("=" * 70)
    print("BAEL - IMAGE PROCESSOR DEMO")
    print("Comprehensive Image Manipulation System")
    print("=" * 70)
    print()

    processor = ImageProcessor()

    # 1. Create Image
    print("1. CREATE IMAGE:")
    print("-" * 40)

    image = processor.create_image(100, 100, Color(255, 128, 64))
    print(f"   Created: {image}")
    print(f"   Metadata: {image.get_metadata()}")
    print()

    # 2. Gradient
    print("2. CREATE GRADIENT:")
    print("-" * 40)

    gradient = processor.create_gradient(
        200, 100,
        Color(255, 0, 0),
        Color(0, 0, 255)
    )
    print(f"   Gradient: {gradient}")
    print(f"   Corner colors:")
    print(f"      Top-left: {gradient.get_pixel(0, 0).to_hex()}")
    print(f"      Top-right: {gradient.get_pixel(199, 0).to_hex()}")
    print()

    # 3. Checkerboard
    print("3. CREATE CHECKERBOARD:")
    print("-" * 40)

    checker = processor.create_checkerboard(64, 64, 8)
    print(f"   Checkerboard: {checker}")
    print(f"   Cell (0,0): {checker.get_pixel(0, 0).to_hex()}")
    print(f"   Cell (8,0): {checker.get_pixel(8, 0).to_hex()}")
    print()

    # 4. Filters
    print("4. FILTERS:")
    print("-" * 40)

    # Create colorful test image
    test_img = processor.create_image(50, 50, Color(200, 100, 50))

    grayscale = processor.apply_filter(test_img, FilterType.GRAYSCALE)
    print(f"   Grayscale: Original {test_img.get_pixel(25, 25).to_hex()} -> {grayscale.get_pixel(25, 25).to_hex()}")

    sepia = processor.apply_filter(test_img, FilterType.SEPIA)
    print(f"   Sepia: {sepia.get_pixel(25, 25).to_hex()}")

    inverted = processor.apply_filter(test_img, FilterType.INVERT)
    print(f"   Inverted: {inverted.get_pixel(25, 25).to_hex()}")
    print()

    # 5. Brightness/Contrast
    print("5. BRIGHTNESS & CONTRAST:")
    print("-" * 40)

    bright = processor.apply_brightness(test_img, 1.5)
    print(f"   Brightness 1.5x: {test_img.get_pixel(25, 25).to_hex()} -> {bright.get_pixel(25, 25).to_hex()}")

    contrast = processor.apply_contrast(test_img, 1.5)
    print(f"   Contrast 1.5x: {test_img.get_pixel(25, 25).to_hex()} -> {contrast.get_pixel(25, 25).to_hex()}")
    print()

    # 6. Transformations
    print("6. TRANSFORMATIONS:")
    print("-" * 40)

    # Resize
    resized = processor.resize(test_img, 25, 25)
    print(f"   Resize: {test_img} -> {resized}")

    # Crop
    cropped = processor.crop(test_img, Rectangle(10, 10, 30, 30))
    print(f"   Crop: {test_img} -> {cropped}")

    # Flip
    flipped = processor.flip(test_img, FlipDirection.HORIZONTAL)
    print(f"   Flip horizontal: {flipped}")

    # Rotate
    rotated = processor.rotate(test_img, 45)
    print(f"   Rotate 45°: {test_img} -> {rotated}")
    print()

    # 7. Thumbnail
    print("7. THUMBNAIL:")
    print("-" * 40)

    large = processor.create_image(400, 300)
    thumb = processor.thumbnail(large, 50)
    print(f"   Original: {large}")
    print(f"   Thumbnail (max 50): {thumb}")
    print()

    # 8. Drawing
    print("8. DRAWING:")
    print("-" * 40)

    canvas = processor.create_image(100, 100, Color(255, 255, 255))
    ctx = processor.get_drawing_context(canvas)

    ctx.draw_line(0, 0, 99, 99, Color(255, 0, 0))
    ctx.draw_rect(Rectangle(10, 10, 30, 30), Color(0, 255, 0))
    ctx.draw_circle(70, 70, 20, Color(0, 0, 255), fill=True)

    print(f"   Drew line, rectangle, and filled circle")
    print(f"   Center line pixel: {canvas.get_pixel(50, 50).to_hex()}")
    print()

    # 9. Blending
    print("9. BLENDING:")
    print("-" * 40)

    base = processor.create_image(100, 100, Color(255, 0, 0))
    overlay = processor.create_image(50, 50, Color(0, 0, 255))

    blended = processor.blend(base, overlay, 25, 25, BlendMode.NORMAL, 0.5)
    print(f"   Base: red, Overlay: blue")
    print(f"   Blended center: {blended.get_pixel(50, 50).to_hex()}")

    # Different modes
    for mode in [BlendMode.MULTIPLY, BlendMode.SCREEN, BlendMode.ADD]:
        result = processor.blend(base, overlay, 25, 25, mode, 1.0)
        print(f"   Mode {mode.value}: {result.get_pixel(50, 50).to_hex()}")
    print()

    # 10. Histogram
    print("10. HISTOGRAM ANALYSIS:")
    print("-" * 40)

    hist = processor.get_histogram(gradient)
    red_peak = max(range(256), key=lambda i: hist.red[i])
    print(f"   Red channel peak at: {red_peak}")
    print(f"   Total red samples: {sum(hist.red)}")
    print()

    # 11. Dominant Color
    print("11. DOMINANT COLOR:")
    print("-" * 40)

    dominant = processor.get_dominant_color(gradient)
    print(f"   Gradient dominant: {dominant.to_hex()}")
    print()

    # 12. Image Comparison
    print("12. IMAGE COMPARISON:")
    print("-" * 40)

    img1 = processor.create_image(50, 50, Color(100, 100, 100))
    img2 = processor.create_image(50, 50, Color(100, 100, 100))
    img3 = processor.create_image(50, 50, Color(200, 200, 200))

    similarity1 = processor.compare(img1, img2)
    similarity2 = processor.compare(img1, img3)

    print(f"   Identical images: {similarity1:.2%} similar")
    print(f"   Different images: {similarity2:.2%} similar")
    print()

    # 13. Serialization
    print("13. SERIALIZATION:")
    print("-" * 40)

    original = processor.create_image(20, 20, Color(128, 64, 192))

    # Raw format
    raw_bytes = processor.to_bytes(original, ImageFormat.RAW)
    restored = processor.from_bytes(raw_bytes, ImageFormat.RAW)
    print(f"   RAW bytes: {len(raw_bytes)}")
    print(f"   Restored: {restored}")

    # Base64
    b64 = processor.to_base64(original)
    print(f"   Base64 length: {len(b64)}")
    print()

    # 14. Color Operations
    print("14. COLOR OPERATIONS:")
    print("-" * 40)

    color = Color.from_hex("#FF8040")
    print(f"   From hex #FF8040: RGB({color.r}, {color.g}, {color.b})")
    print(f"   To hex: {color.to_hex()}")
    print(f"   Luminance: {color.luminance():.1f}")
    print(f"   Grayscale: {color.grayscale().to_hex()}")
    print()

    # 15. Statistics
    print("15. PROCESSOR STATISTICS:")
    print("-" * 40)

    stats = processor.get_stats()
    print(f"   Stats: {stats}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Image Processor Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
