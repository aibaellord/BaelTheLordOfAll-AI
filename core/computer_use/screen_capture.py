"""
BAEL - Screen Capture and Reading
Captures screen content and extracts text/UI elements.
Uses PIL for capture and pytesseract/easyocr for OCR (free/local).
"""

import asyncio
import base64
import io
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import ScreenRegion, UIElement

logger = logging.getLogger("BAEL.ComputerUse.Screen")


@dataclass
class Screenshot:
    """A captured screenshot."""
    id: str
    width: int
    height: int
    image_bytes: bytes
    timestamp: float
    region: Optional[ScreenRegion] = None

    def to_base64(self) -> str:
        """Convert to base64 for API transmission."""
        return base64.b64encode(self.image_bytes).decode('utf-8')

    def save(self, path: str) -> None:
        """Save screenshot to file."""
        with open(path, 'wb') as f:
            f.write(self.image_bytes)


class ScreenReader:
    """
    Screen capture and text extraction.

    Features:
    - Full screen and region capture
    - OCR text extraction (multiple engines)
    - UI element detection
    - Change detection between screenshots
    """

    def __init__(self):
        self._pil_available = False
        self._ocr_engine = None
        self._last_screenshot: Optional[Screenshot] = None
        self._init_dependencies()

    def _init_dependencies(self):
        """Initialize available dependencies."""
        try:
            from PIL import Image, ImageGrab
            self._pil_available = True
            logger.info("PIL available for screen capture")
        except ImportError:
            logger.warning("PIL not available - install Pillow")

        # Try OCR engines in order of preference
        try:
            import pytesseract
            self._ocr_engine = "tesseract"
            logger.info("Using Tesseract OCR")
        except ImportError:
            try:
                import easyocr
                self._ocr_engine = "easyocr"
                logger.info("Using EasyOCR")
            except ImportError:
                logger.warning("No OCR engine available - install pytesseract or easyocr")

    async def capture_screen(
        self,
        region: Optional[ScreenRegion] = None
    ) -> Screenshot:
        """
        Capture the screen or a region.

        Args:
            region: Optional region to capture (full screen if None)

        Returns:
            Screenshot object
        """
        import time

        if not self._pil_available:
            raise RuntimeError("PIL not available for screen capture")

        from PIL import ImageGrab

        # Capture
        if region:
            bbox = (region.x, region.y, region.x + region.width, region.y + region.height)
            image = await asyncio.to_thread(ImageGrab.grab, bbox=bbox)
        else:
            image = await asyncio.to_thread(ImageGrab.grab)

        # Convert to bytes
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        image_bytes = buffer.getvalue()

        screenshot = Screenshot(
            id=f"ss_{uuid.uuid4().hex[:8]}",
            width=image.width,
            height=image.height,
            image_bytes=image_bytes,
            timestamp=time.time(),
            region=region
        )

        self._last_screenshot = screenshot
        logger.debug(f"Captured screenshot: {image.width}x{image.height}")

        return screenshot

    async def extract_text(
        self,
        screenshot: Optional[Screenshot] = None,
        region: Optional[ScreenRegion] = None
    ) -> str:
        """
        Extract text from screenshot using OCR.

        Args:
            screenshot: Screenshot to process (captures new if None)
            region: Region within screenshot to process

        Returns:
            Extracted text
        """
        if screenshot is None:
            screenshot = await self.capture_screen(region)

        if not self._ocr_engine:
            return "[OCR not available - install pytesseract or easyocr]"

        from PIL import Image

        # Load image
        image = Image.open(io.BytesIO(screenshot.image_bytes))

        # Crop to region if specified
        if region:
            image = image.crop((region.x, region.y, region.x + region.width, region.y + region.height))

        # Run OCR
        if self._ocr_engine == "tesseract":
            import pytesseract
            text = await asyncio.to_thread(pytesseract.image_to_string, image)
        else:
            import easyocr
            reader = easyocr.Reader(['en'])
            results = await asyncio.to_thread(reader.readtext, image)
            text = "\n".join([r[1] for r in results])

        return text.strip()

    async def detect_elements(
        self,
        screenshot: Optional[Screenshot] = None
    ) -> List[UIElement]:
        """
        Detect UI elements in screenshot.

        Uses OCR to find text elements and basic image processing
        for buttons/inputs.

        Args:
            screenshot: Screenshot to analyze

        Returns:
            List of detected UI elements
        """
        if screenshot is None:
            screenshot = await self.capture_screen()

        elements = []

        from PIL import Image
        image = Image.open(io.BytesIO(screenshot.image_bytes))

        # OCR-based text detection
        if self._ocr_engine == "tesseract":
            import pytesseract

            # Get bounding boxes
            data = await asyncio.to_thread(
                pytesseract.image_to_data,
                image,
                output_type=pytesseract.Output.DICT
            )

            for i, text in enumerate(data['text']):
                if text.strip():
                    conf = int(data['conf'][i])
                    if conf > 50:  # Confidence threshold
                        region = ScreenRegion(
                            x=data['left'][i],
                            y=data['top'][i],
                            width=data['width'][i],
                            height=data['height'][i]
                        )

                        element = UIElement(
                            id=f"elem_{uuid.uuid4().hex[:6]}",
                            element_type=self._classify_element(text, region),
                            text=text,
                            region=region,
                            confidence=conf / 100.0
                        )
                        elements.append(element)

        elif self._ocr_engine == "easyocr":
            import easyocr
            reader = easyocr.Reader(['en'])
            results = await asyncio.to_thread(reader.readtext, image)

            for bbox, text, conf in results:
                if text.strip() and conf > 0.5:
                    # bbox is [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                    x1, y1 = int(bbox[0][0]), int(bbox[0][1])
                    x2, y2 = int(bbox[2][0]), int(bbox[2][1])

                    region = ScreenRegion(
                        x=x1,
                        y=y1,
                        width=x2 - x1,
                        height=y2 - y1
                    )

                    element = UIElement(
                        id=f"elem_{uuid.uuid4().hex[:6]}",
                        element_type=self._classify_element(text, region),
                        text=text,
                        region=region,
                        confidence=conf
                    )
                    elements.append(element)

        logger.info(f"Detected {len(elements)} UI elements")
        return elements

    def _classify_element(self, text: str, region: ScreenRegion) -> str:
        """Classify UI element type based on text and region."""
        text_lower = text.lower()

        # Button indicators
        if any(word in text_lower for word in ['ok', 'cancel', 'submit', 'save', 'close', 'open', 'click', 'button']):
            return "button"

        # Link indicators
        if text.startswith('http') or 'www.' in text:
            return "link"

        # Input field (usually has placeholder text)
        if region.height < 40 and region.width > 100:
            if any(word in text_lower for word in ['enter', 'type', 'search', 'email', 'password']):
                return "input"

        # Menu items
        if region.width < 200 and region.height < 30:
            return "menu_item"

        # Default to text
        return "text"

    async def find_element_by_text(
        self,
        text: str,
        screenshot: Optional[Screenshot] = None,
        partial_match: bool = True
    ) -> Optional[UIElement]:
        """
        Find a UI element by its text content.

        Args:
            text: Text to search for
            screenshot: Screenshot to search in
            partial_match: Allow partial text matches

        Returns:
            Matching UIElement or None
        """
        elements = await self.detect_elements(screenshot)

        text_lower = text.lower()

        for element in elements:
            elem_text = element.text.lower()

            if partial_match:
                if text_lower in elem_text or elem_text in text_lower:
                    return element
            else:
                if text_lower == elem_text:
                    return element

        return None

    async def detect_changes(
        self,
        previous: Screenshot,
        current: Optional[Screenshot] = None,
        threshold: float = 0.1
    ) -> Dict[str, Any]:
        """
        Detect changes between two screenshots.

        Args:
            previous: Previous screenshot
            current: Current screenshot (captures new if None)
            threshold: Change detection threshold (0-1)

        Returns:
            Dict with change information
        """
        if current is None:
            current = await self.capture_screen()

        import numpy as np
        from PIL import Image, ImageChops

        img1 = Image.open(io.BytesIO(previous.image_bytes)).convert('RGB')
        img2 = Image.open(io.BytesIO(current.image_bytes)).convert('RGB')

        # Resize if needed
        if img1.size != img2.size:
            img2 = img2.resize(img1.size)

        # Calculate difference
        diff = ImageChops.difference(img1, img2)
        diff_array = np.array(diff)

        # Calculate change percentage
        total_pixels = diff_array.size
        changed_pixels = np.sum(diff_array > 30)  # Threshold for "changed"
        change_ratio = changed_pixels / total_pixels

        # Find regions with most change
        changed_regions = []
        if change_ratio > threshold:
            # Simplified: find bounding box of changes
            diff_gray = diff.convert('L')
            diff_array_gray = np.array(diff_gray)

            rows = np.any(diff_array_gray > 30, axis=1)
            cols = np.any(diff_array_gray > 30, axis=0)

            if np.any(rows) and np.any(cols):
                y_min, y_max = np.where(rows)[0][[0, -1]]
                x_min, x_max = np.where(cols)[0][[0, -1]]

                changed_regions.append(ScreenRegion(
                    x=int(x_min),
                    y=int(y_min),
                    width=int(x_max - x_min),
                    height=int(y_max - y_min)
                ))

        return {
            "has_changes": change_ratio > threshold,
            "change_ratio": change_ratio,
            "changed_regions": changed_regions
        }

    def get_screen_size(self) -> Tuple[int, int]:
        """Get the screen dimensions."""
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            return img.width, img.height
        except:
            return (1920, 1080)  # Default fallback


# Global instance
_screen_reader: Optional[ScreenReader] = None


def get_screen_reader() -> ScreenReader:
    """Get or create screen reader instance."""
    global _screen_reader
    if _screen_reader is None:
        _screen_reader = ScreenReader()
    return _screen_reader
