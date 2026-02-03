"""
BAEL - Vision Processing Module
Zero-cost image analysis, scene understanding, and visual reasoning.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("BAEL.Vision")


class ImageType(Enum):
    """Types of images."""
    PHOTOGRAPH = "photograph"
    SCREENSHOT = "screenshot"
    DIAGRAM = "diagram"
    DOCUMENT = "document"
    CHART = "chart"
    UI = "ui"
    CODE = "code"
    DRAWING = "drawing"
    UNKNOWN = "unknown"


class AnalysisType(Enum):
    """Types of image analysis."""
    CLASSIFICATION = "classification"
    DETECTION = "detection"
    OCR = "ocr"
    SCENE = "scene"
    FACE = "face"
    COLOR = "color"
    SIMILARITY = "similarity"


@dataclass
class BoundingBox:
    """Bounding box for detected objects."""
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def area(self) -> int:
        return self.width * self.height


@dataclass
class DetectedObject:
    """A detected object in an image."""
    label: str
    confidence: float
    bbox: BoundingBox
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SceneAnalysis:
    """Analysis results for a scene."""
    image_type: ImageType
    description: str
    objects: List[DetectedObject]
    text_content: Optional[str]
    dominant_colors: List[str]
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisionConfig:
    """Configuration for vision processing."""
    ocr_backend: str = "tesseract"  # tesseract or easyocr
    enable_face_detection: bool = False
    max_objects: int = 100
    confidence_threshold: float = 0.5
    enable_scene_description: bool = True


# Lazy imports
def get_vision_processor():
    """Get the vision processor."""
    from .vision_processor import VisionProcessor
    return VisionProcessor()


def get_ocr_engine():
    """Get the OCR engine."""
    from .ocr_engine import OCREngine
    return OCREngine()


def get_scene_analyzer():
    """Get the scene analyzer."""
    from .scene_understanding import SceneAnalyzer
    return SceneAnalyzer()


__all__ = [
    "ImageType",
    "AnalysisType",
    "BoundingBox",
    "DetectedObject",
    "SceneAnalysis",
    "VisionConfig",
    "get_vision_processor",
    "get_ocr_engine",
    "get_scene_analyzer"
]
