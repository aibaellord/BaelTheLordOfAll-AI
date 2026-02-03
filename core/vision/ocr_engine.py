"""
BAEL - OCR Engine
Text extraction from images using free/local OCR backends.
"""

import asyncio
import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from . import BoundingBox

logger = logging.getLogger("BAEL.Vision.OCR")


@dataclass
class TextBlock:
    """A block of detected text."""
    text: str
    confidence: float
    bbox: BoundingBox
    line_number: int = 0
    block_number: int = 0


@dataclass
class OCRResult:
    """Complete OCR result."""
    full_text: str
    blocks: List[TextBlock]
    language: str
    confidence: float
    metadata: Dict[str, Any]


class OCREngine:
    """
    OCR engine using free local backends.

    Supported backends:
    - pytesseract (Tesseract OCR)
    - easyocr

    Features:
    - Multi-language support
    - Layout preservation
    - Confidence scoring
    - Text block detection
    """

    def __init__(self, backend: str = "auto"):
        self.backend = self._detect_backend(backend)
        self._easyocr_reader = None

    def _detect_backend(self, requested: str) -> str:
        """Detect available OCR backend."""
        if requested != "auto":
            return requested

        # Try pytesseract first (more common)
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return "tesseract"
        except Exception:
            pass

        # Try easyocr
        try:
            import easyocr
            return "easyocr"
        except ImportError:
            pass

        logger.warning("No OCR backend available")
        return "none"

    async def _get_easyocr_reader(self, languages: List[str] = None):
        """Lazy load easyocr reader."""
        if self._easyocr_reader is None:
            try:
                import easyocr
                langs = languages or ["en"]
                self._easyocr_reader = easyocr.Reader(langs, gpu=False)
            except Exception as e:
                logger.error(f"Failed to initialize easyocr: {e}")
        return self._easyocr_reader

    async def extract_text(
        self,
        image: Any,
        language: str = "eng",
        preserve_layout: bool = False
    ) -> str:
        """
        Extract text from image.

        Args:
            image: PIL Image object
            language: OCR language code
            preserve_layout: Whether to preserve spatial layout

        Returns:
            Extracted text
        """
        if self.backend == "tesseract":
            return await self._extract_tesseract(image, language, preserve_layout)
        elif self.backend == "easyocr":
            return await self._extract_easyocr(image, language)
        else:
            logger.error("No OCR backend available")
            return ""

    async def _extract_tesseract(
        self,
        image: Any,
        language: str,
        preserve_layout: bool
    ) -> str:
        """Extract text using Tesseract."""
        try:
            import pytesseract

            # Set page segmentation mode
            config = "--psm 6" if preserve_layout else "--psm 3"

            # Run OCR
            text = pytesseract.image_to_string(
                image,
                lang=language,
                config=config
            )

            return text.strip()

        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            return ""

    async def _extract_easyocr(
        self,
        image: Any,
        language: str
    ) -> str:
        """Extract text using EasyOCR."""
        try:
            import numpy as np

            # Map language code
            lang_map = {"eng": "en", "fra": "fr", "deu": "de", "spa": "es"}
            lang = lang_map.get(language, language)

            reader = await self._get_easyocr_reader([lang])
            if not reader:
                return ""

            # Convert PIL to numpy
            img_array = np.array(image)

            # Run OCR
            results = reader.readtext(img_array)

            # Extract text
            texts = [text for _, text, _ in results]
            return "\n".join(texts)

        except Exception as e:
            logger.error(f"EasyOCR failed: {e}")
            return ""

    async def extract_with_details(
        self,
        image: Any,
        language: str = "eng"
    ) -> OCRResult:
        """
        Extract text with full details including positions.

        Returns:
            OCRResult with text blocks and metadata
        """
        if self.backend == "tesseract":
            return await self._detailed_tesseract(image, language)
        elif self.backend == "easyocr":
            return await self._detailed_easyocr(image, language)
        else:
            return OCRResult(
                full_text="",
                blocks=[],
                language=language,
                confidence=0.0,
                metadata={"error": "No OCR backend"}
            )

    async def _detailed_tesseract(
        self,
        image: Any,
        language: str
    ) -> OCRResult:
        """Get detailed OCR results from Tesseract."""
        try:
            import pytesseract

            # Get detailed data
            data = pytesseract.image_to_data(
                image,
                lang=language,
                output_type=pytesseract.Output.DICT
            )

            blocks = []
            confidences = []

            n_boxes = len(data["text"])
            for i in range(n_boxes):
                text = data["text"][i].strip()
                conf = float(data["conf"][i])

                if text and conf > 0:
                    blocks.append(TextBlock(
                        text=text,
                        confidence=conf / 100.0,
                        bbox=BoundingBox(
                            x=data["left"][i],
                            y=data["top"][i],
                            width=data["width"][i],
                            height=data["height"][i]
                        ),
                        line_number=data["line_num"][i],
                        block_number=data["block_num"][i]
                    ))
                    confidences.append(conf)

            # Combine text
            full_text = " ".join([b.text for b in blocks])
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

            return OCRResult(
                full_text=full_text,
                blocks=blocks,
                language=language,
                confidence=avg_conf / 100.0,
                metadata={"backend": "tesseract", "block_count": len(blocks)}
            )

        except Exception as e:
            logger.error(f"Detailed Tesseract OCR failed: {e}")
            return OCRResult(
                full_text="",
                blocks=[],
                language=language,
                confidence=0.0,
                metadata={"error": str(e)}
            )

    async def _detailed_easyocr(
        self,
        image: Any,
        language: str
    ) -> OCRResult:
        """Get detailed OCR results from EasyOCR."""
        try:
            import numpy as np

            lang_map = {"eng": "en", "fra": "fr", "deu": "de", "spa": "es"}
            lang = lang_map.get(language, language)

            reader = await self._get_easyocr_reader([lang])
            if not reader:
                return OCRResult(
                    full_text="",
                    blocks=[],
                    language=language,
                    confidence=0.0,
                    metadata={"error": "EasyOCR not available"}
                )

            img_array = np.array(image)
            results = reader.readtext(img_array)

            blocks = []
            confidences = []

            for i, (bbox_points, text, conf) in enumerate(results):
                # Convert points to bounding box
                x_coords = [p[0] for p in bbox_points]
                y_coords = [p[1] for p in bbox_points]

                blocks.append(TextBlock(
                    text=text,
                    confidence=conf,
                    bbox=BoundingBox(
                        x=int(min(x_coords)),
                        y=int(min(y_coords)),
                        width=int(max(x_coords) - min(x_coords)),
                        height=int(max(y_coords) - min(y_coords))
                    ),
                    line_number=i
                ))
                confidences.append(conf)

            full_text = " ".join([b.text for b in blocks])
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

            return OCRResult(
                full_text=full_text,
                blocks=blocks,
                language=language,
                confidence=avg_conf,
                metadata={"backend": "easyocr", "block_count": len(blocks)}
            )

        except Exception as e:
            logger.error(f"Detailed EasyOCR failed: {e}")
            return OCRResult(
                full_text="",
                blocks=[],
                language=language,
                confidence=0.0,
                metadata={"error": str(e)}
            )

    async def detect_language(self, image: Any) -> Tuple[str, float]:
        """
        Detect language from image text.

        Returns:
            Tuple of (language_code, confidence)
        """
        try:
            # Extract some text first
            text = await self.extract_text(image)

            if not text or len(text) < 20:
                return ("eng", 0.5)

            # Simple language detection based on character patterns
            # Could be enhanced with langdetect library

            # Check for common language indicators
            if any(ord(c) > 0x4E00 and ord(c) < 0x9FFF for c in text):
                return ("chi_sim", 0.8)  # Chinese
            if any(ord(c) > 0x3040 and ord(c) < 0x30FF for c in text):
                return ("jpn", 0.8)  # Japanese
            if any(ord(c) > 0xAC00 and ord(c) < 0xD7AF for c in text):
                return ("kor", 0.8)  # Korean
            if any(ord(c) > 0x0400 and ord(c) < 0x04FF for c in text):
                return ("rus", 0.8)  # Russian
            if any(ord(c) > 0x0600 and ord(c) < 0x06FF for c in text):
                return ("ara", 0.8)  # Arabic

            # Default to English
            return ("eng", 0.7)

        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return ("eng", 0.5)

    async def find_text(
        self,
        image: Any,
        search_text: str,
        case_sensitive: bool = False
    ) -> List[TextBlock]:
        """
        Find specific text in image.

        Args:
            image: PIL Image
            search_text: Text to find
            case_sensitive: Case sensitive search

        Returns:
            List of matching text blocks
        """
        result = await self.extract_with_details(image)

        matches = []
        search = search_text if case_sensitive else search_text.lower()

        for block in result.blocks:
            text = block.text if case_sensitive else block.text.lower()
            if search in text:
                matches.append(block)

        return matches

    def get_backend_info(self) -> Dict[str, Any]:
        """Get information about the OCR backend."""
        info = {
            "backend": self.backend,
            "available": self.backend != "none"
        }

        if self.backend == "tesseract":
            try:
                import pytesseract
                info["version"] = pytesseract.get_tesseract_version().vstring
                info["languages"] = pytesseract.get_languages()
            except Exception:
                pass

        return info


# Global instance
_ocr_engine: Optional[OCREngine] = None


def get_ocr_engine(backend: str = "auto") -> OCREngine:
    """Get or create OCR engine instance."""
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = OCREngine(backend)
    return _ocr_engine
