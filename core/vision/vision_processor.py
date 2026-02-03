"""
BAEL - Vision & Multimodal Processing
Advanced image, video, and multimodal content processing.

Features:
- Image analysis and description
- OCR text extraction
- Object detection
- Visual question answering
- Image generation prompts
- Video frame analysis
"""

import asyncio
import base64
import hashlib
import io
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ImageFormat(Enum):
    """Supported image formats."""
    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    WEBP = "webp"
    BMP = "bmp"


class AnalysisType(Enum):
    """Types of image analysis."""
    DESCRIPTION = "description"
    OCR = "ocr"
    OBJECTS = "objects"
    FACES = "faces"
    TEXT_EXTRACTION = "text_extraction"
    SCENE = "scene"
    COLORS = "colors"
    CUSTOM = "custom"


class ModelProvider(Enum):
    """Vision model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    LOCAL = "local"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ImageData:
    """Image data container."""
    data: bytes
    format: ImageFormat
    width: Optional[int] = None
    height: Optional[int] = None
    size_bytes: int = 0

    @classmethod
    def from_file(cls, path: str) -> "ImageData":
        """Load image from file."""
        ext = Path(path).suffix.lower().lstrip('.')
        format_map = {
            'jpg': ImageFormat.JPEG,
            'jpeg': ImageFormat.JPEG,
            'png': ImageFormat.PNG,
            'gif': ImageFormat.GIF,
            'webp': ImageFormat.WEBP,
            'bmp': ImageFormat.BMP
        }

        with open(path, 'rb') as f:
            data = f.read()

        return cls(
            data=data,
            format=format_map.get(ext, ImageFormat.JPEG),
            size_bytes=len(data)
        )

    @classmethod
    def from_base64(cls, b64_string: str, format: ImageFormat = ImageFormat.JPEG) -> "ImageData":
        """Load image from base64 string."""
        data = base64.b64decode(b64_string)
        return cls(
            data=data,
            format=format,
            size_bytes=len(data)
        )

    @classmethod
    def from_url(cls, url: str) -> "ImageData":
        """Create image reference from URL."""
        # This is a placeholder - in real implementation would fetch
        return cls(
            data=url.encode(),
            format=ImageFormat.JPEG,
            size_bytes=0
        )

    def to_base64(self) -> str:
        """Convert to base64 string."""
        return base64.b64encode(self.data).decode()

    def to_data_url(self) -> str:
        """Convert to data URL."""
        mime = f"image/{self.format.value}"
        return f"data:{mime};base64,{self.to_base64()}"


@dataclass
class BoundingBox:
    """Bounding box for detected objects."""
    x: float  # 0-1 normalized
    y: float
    width: float
    height: float

    def to_pixels(self, img_width: int, img_height: int) -> Tuple[int, int, int, int]:
        """Convert to pixel coordinates."""
        return (
            int(self.x * img_width),
            int(self.y * img_height),
            int(self.width * img_width),
            int(self.height * img_height)
        )


@dataclass
class DetectedObject:
    """Detected object in image."""
    label: str
    confidence: float
    bounding_box: Optional[BoundingBox] = None
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TextRegion:
    """Detected text region."""
    text: str
    confidence: float
    bounding_box: Optional[BoundingBox] = None
    language: Optional[str] = None


@dataclass
class ColorInfo:
    """Color information."""
    hex_code: str
    rgb: Tuple[int, int, int]
    percentage: float
    name: Optional[str] = None


@dataclass
class AnalysisResult:
    """Result of image analysis."""
    analysis_type: AnalysisType
    description: Optional[str] = None
    objects: List[DetectedObject] = field(default_factory=list)
    text_regions: List[TextRegion] = field(default_factory=list)
    colors: List[ColorInfo] = field(default_factory=list)
    scene: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    processing_time: float = 0.0


@dataclass
class VisionRequest:
    """Request for vision analysis."""
    images: List[ImageData]
    analysis_types: List[AnalysisType]
    prompt: Optional[str] = None
    max_tokens: int = 1024
    detail: str = "auto"  # low, high, auto


# =============================================================================
# VISION PROVIDERS
# =============================================================================

class VisionProvider(ABC):
    """Abstract vision provider."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def analyze(
        self,
        image: ImageData,
        prompt: str,
        **kwargs
    ) -> str:
        pass

    @abstractmethod
    async def detect_objects(
        self,
        image: ImageData
    ) -> List[DetectedObject]:
        pass


class OpenAIVisionProvider(VisionProvider):
    """OpenAI GPT-4 Vision provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    @property
    def name(self) -> str:
        return "openai"

    async def analyze(
        self,
        image: ImageData,
        prompt: str,
        model: str = "gpt-4o",
        max_tokens: int = 1024,
        detail: str = "auto"
    ) -> str:
        """Analyze image with GPT-4 Vision."""
        try:
            import httpx

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # Build message content
            content = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image.to_data_url(),
                        "detail": detail
                    }
                }
            ]

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": content}],
                "max_tokens": max_tokens
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                )

                response.raise_for_status()
                data = response.json()

                return data["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"OpenAI Vision error: {e}")
            return f"Error analyzing image: {e}"

    async def detect_objects(
        self,
        image: ImageData
    ) -> List[DetectedObject]:
        """Detect objects using GPT-4 Vision."""
        prompt = """Analyze this image and list all distinct objects you can identify.
For each object, provide:
1. Label (what it is)
2. Confidence (0-1)
3. Brief description

Format as JSON array: [{"label": "...", "confidence": 0.95, "description": "..."}]"""

        response = await self.analyze(image, prompt)

        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                objects_data = json.loads(json_match.group())
                return [
                    DetectedObject(
                        label=obj["label"],
                        confidence=obj.get("confidence", 0.8),
                        attributes={"description": obj.get("description", "")}
                    )
                    for obj in objects_data
                ]
        except Exception as e:
            logger.warning(f"Failed to parse objects: {e}")

        return []


class AnthropicVisionProvider(VisionProvider):
    """Anthropic Claude Vision provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

    @property
    def name(self) -> str:
        return "anthropic"

    async def analyze(
        self,
        image: ImageData,
        prompt: str,
        model: str = "claude-3-sonnet-20240229",
        max_tokens: int = 1024
    ) -> str:
        """Analyze image with Claude Vision."""
        try:
            import httpx

            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }

            # Build message content
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": f"image/{image.format.value}",
                        "data": image.to_base64()
                    }
                },
                {"type": "text", "text": prompt}
            ]

            payload = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": content}]
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload
                )

                response.raise_for_status()
                data = response.json()

                return data["content"][0]["text"]

        except Exception as e:
            logger.error(f"Anthropic Vision error: {e}")
            return f"Error analyzing image: {e}"

    async def detect_objects(
        self,
        image: ImageData
    ) -> List[DetectedObject]:
        """Detect objects using Claude Vision."""
        prompt = """List all distinct objects visible in this image.
Return as JSON: [{"label": "object name", "confidence": 0.95}]"""

        response = await self.analyze(image, prompt)

        try:
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                objects_data = json.loads(json_match.group())
                return [
                    DetectedObject(
                        label=obj["label"],
                        confidence=obj.get("confidence", 0.8)
                    )
                    for obj in objects_data
                ]
        except Exception:
            pass

        return []


# =============================================================================
# VISION ANALYZER
# =============================================================================

class VisionAnalyzer:
    """High-level vision analysis system."""

    def __init__(self, default_provider: str = "openai"):
        self._providers: Dict[str, VisionProvider] = {}
        self._default_provider = default_provider
        self._cache: Dict[str, AnalysisResult] = {}

        # Initialize default providers
        self._providers["openai"] = OpenAIVisionProvider()
        self._providers["anthropic"] = AnthropicVisionProvider()

    def add_provider(self, provider: VisionProvider) -> None:
        """Add vision provider."""
        self._providers[provider.name] = provider

    async def describe(
        self,
        image: Union[ImageData, str],
        detail_level: str = "detailed",
        provider: Optional[str] = None
    ) -> str:
        """Get natural language description of image."""
        if isinstance(image, str):
            image = ImageData.from_file(image)

        prompts = {
            "brief": "Describe this image in one sentence.",
            "detailed": "Provide a detailed description of this image, including objects, scene, colors, and any notable elements.",
            "technical": "Analyze this image technically: composition, lighting, colors, subjects, and visual elements."
        }

        prompt = prompts.get(detail_level, prompts["detailed"])

        provider_obj = self._providers.get(provider or self._default_provider)
        if not provider_obj:
            raise ValueError(f"Unknown provider: {provider}")

        return await provider_obj.analyze(image, prompt)

    async def extract_text(
        self,
        image: Union[ImageData, str],
        provider: Optional[str] = None
    ) -> List[TextRegion]:
        """Extract text from image (OCR)."""
        if isinstance(image, str):
            image = ImageData.from_file(image)

        prompt = """Extract all visible text from this image.
Return as JSON: [{"text": "...", "confidence": 0.95}]
Include all readable text, numbers, and symbols."""

        provider_obj = self._providers.get(provider or self._default_provider)
        response = await provider_obj.analyze(image, prompt)

        try:
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                text_data = json.loads(json_match.group())
                return [
                    TextRegion(
                        text=t["text"],
                        confidence=t.get("confidence", 0.8)
                    )
                    for t in text_data
                ]
        except Exception:
            # Fallback: return response as single text region
            return [TextRegion(text=response, confidence=0.5)]

        return []

    async def detect_objects(
        self,
        image: Union[ImageData, str],
        provider: Optional[str] = None
    ) -> List[DetectedObject]:
        """Detect objects in image."""
        if isinstance(image, str):
            image = ImageData.from_file(image)

        provider_obj = self._providers.get(provider or self._default_provider)
        return await provider_obj.detect_objects(image)

    async def analyze_colors(
        self,
        image: Union[ImageData, str],
        provider: Optional[str] = None
    ) -> List[ColorInfo]:
        """Analyze dominant colors in image."""
        if isinstance(image, str):
            image = ImageData.from_file(image)

        prompt = """Analyze the dominant colors in this image.
Return as JSON: [{"hex": "#RRGGBB", "name": "color name", "percentage": 25.5}]
List top 5-7 most prominent colors."""

        provider_obj = self._providers.get(provider or self._default_provider)
        response = await provider_obj.analyze(image, prompt)

        try:
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                colors_data = json.loads(json_match.group())
                return [
                    ColorInfo(
                        hex_code=c["hex"],
                        rgb=tuple(int(c["hex"][i:i+2], 16) for i in (1, 3, 5)),
                        percentage=c.get("percentage", 10.0),
                        name=c.get("name")
                    )
                    for c in colors_data
                ]
        except Exception:
            pass

        return []

    async def answer_question(
        self,
        image: Union[ImageData, str],
        question: str,
        provider: Optional[str] = None
    ) -> str:
        """Answer a question about an image (VQA)."""
        if isinstance(image, str):
            image = ImageData.from_file(image)

        provider_obj = self._providers.get(provider or self._default_provider)
        return await provider_obj.analyze(image, question)

    async def compare_images(
        self,
        images: List[Union[ImageData, str]],
        aspect: str = "all",
        provider: Optional[str] = None
    ) -> str:
        """Compare multiple images."""
        # Convert to ImageData
        image_data = []
        for img in images:
            if isinstance(img, str):
                image_data.append(ImageData.from_file(img))
            else:
                image_data.append(img)

        aspects = {
            "all": "Compare these images in terms of content, style, colors, composition, and any notable differences or similarities.",
            "content": "Compare the content and subjects of these images.",
            "style": "Compare the artistic style and visual treatment of these images.",
            "quality": "Compare the technical quality of these images (resolution, clarity, lighting)."
        }

        prompt = aspects.get(aspect, aspects["all"])

        # For now, describe each and compare
        # In production, would use models that support multiple images
        descriptions = []
        provider_obj = self._providers.get(provider or self._default_provider)

        for i, img in enumerate(image_data):
            desc = await provider_obj.analyze(img, "Describe this image briefly.")
            descriptions.append(f"Image {i+1}: {desc}")

        return f"Image Comparison:\n" + "\n".join(descriptions)

    async def full_analysis(
        self,
        image: Union[ImageData, str],
        provider: Optional[str] = None
    ) -> AnalysisResult:
        """Perform comprehensive image analysis."""
        if isinstance(image, str):
            image = ImageData.from_file(image)

        start_time = time.time()

        # Run analyses in parallel
        description_task = self.describe(image, "detailed", provider)
        objects_task = self.detect_objects(image, provider)
        text_task = self.extract_text(image, provider)
        colors_task = self.analyze_colors(image, provider)

        description, objects, text_regions, colors = await asyncio.gather(
            description_task,
            objects_task,
            text_task,
            colors_task,
            return_exceptions=True
        )

        return AnalysisResult(
            analysis_type=AnalysisType.DESCRIPTION,
            description=description if isinstance(description, str) else None,
            objects=objects if isinstance(objects, list) else [],
            text_regions=text_regions if isinstance(text_regions, list) else [],
            colors=colors if isinstance(colors, list) else [],
            confidence=0.85,
            processing_time=time.time() - start_time
        )


# =============================================================================
# IMAGE GENERATION PROMPT BUILDER
# =============================================================================

class ImagePromptBuilder:
    """Build prompts for image generation."""

    def __init__(self):
        self._subject: str = ""
        self._style: str = ""
        self._medium: str = ""
        self._mood: str = ""
        self._lighting: str = ""
        self._colors: List[str] = []
        self._composition: str = ""
        self._quality: List[str] = []
        self._negative: List[str] = []

    def subject(self, subject: str) -> "ImagePromptBuilder":
        """Set the main subject."""
        self._subject = subject
        return self

    def style(self, style: str) -> "ImagePromptBuilder":
        """Set artistic style."""
        self._style = style
        return self

    def medium(self, medium: str) -> "ImagePromptBuilder":
        """Set art medium (oil painting, digital art, etc.)."""
        self._medium = medium
        return self

    def mood(self, mood: str) -> "ImagePromptBuilder":
        """Set mood/atmosphere."""
        self._mood = mood
        return self

    def lighting(self, lighting: str) -> "ImagePromptBuilder":
        """Set lighting style."""
        self._lighting = lighting
        return self

    def colors(self, *colors: str) -> "ImagePromptBuilder":
        """Set color palette."""
        self._colors.extend(colors)
        return self

    def composition(self, composition: str) -> "ImagePromptBuilder":
        """Set composition style."""
        self._composition = composition
        return self

    def quality(self, *quality_tags: str) -> "ImagePromptBuilder":
        """Add quality tags."""
        self._quality.extend(quality_tags)
        return self

    def negative(self, *negative_prompts: str) -> "ImagePromptBuilder":
        """Add negative prompts."""
        self._negative.extend(negative_prompts)
        return self

    def build(self) -> Dict[str, str]:
        """Build the final prompt."""
        parts = []

        if self._subject:
            parts.append(self._subject)

        if self._style:
            parts.append(f"in the style of {self._style}")

        if self._medium:
            parts.append(f"{self._medium}")

        if self._mood:
            parts.append(f"{self._mood} mood")

        if self._lighting:
            parts.append(f"{self._lighting} lighting")

        if self._colors:
            parts.append(f"color palette: {', '.join(self._colors)}")

        if self._composition:
            parts.append(f"{self._composition} composition")

        if self._quality:
            parts.extend(self._quality)

        return {
            "prompt": ", ".join(parts),
            "negative_prompt": ", ".join(self._negative) if self._negative else ""
        }


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def main():
    """Demonstrate vision capabilities."""
    print("=== BAEL Vision & Multimodal Processing ===\n")

    # Create analyzer
    analyzer = VisionAnalyzer()

    # Example: Build image generation prompt
    print("--- Image Generation Prompt ---")
    prompt = (
        ImagePromptBuilder()
        .subject("A majestic lion standing on a rocky cliff")
        .style("National Geographic photography")
        .lighting("golden hour sunlight")
        .mood("powerful and serene")
        .colors("warm orange", "deep gold", "earth tones")
        .composition("rule of thirds")
        .quality("8k", "highly detailed", "award-winning photo")
        .negative("cartoon", "blurry", "low quality")
        .build()
    )

    print(f"Prompt: {prompt['prompt']}")
    print(f"Negative: {prompt['negative_prompt']}")

    # Example: Create image data
    print("\n--- Image Data Handling ---")

    # Create sample base64 image (1x1 pixel)
    sample_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    image = ImageData.from_base64(sample_b64, ImageFormat.PNG)

    print(f"Image format: {image.format.value}")
    print(f"Size: {image.size_bytes} bytes")
    print(f"Data URL: {image.to_data_url()[:50]}...")

    # Example: Color info
    print("\n--- Color Analysis Example ---")
    colors = [
        ColorInfo("#FF6B6B", (255, 107, 107), 35.0, "Coral Red"),
        ColorInfo("#4ECDC4", (78, 205, 196), 25.0, "Turquoise"),
        ColorInfo("#2C3E50", (44, 62, 80), 20.0, "Dark Blue Gray")
    ]

    for color in colors:
        print(f"  {color.name}: {color.hex_code} ({color.percentage}%)")

    # Example: Object detection result
    print("\n--- Object Detection Example ---")
    objects = [
        DetectedObject("person", 0.95, attributes={"description": "Standing near center"}),
        DetectedObject("car", 0.89, attributes={"description": "Red sedan in background"}),
        DetectedObject("tree", 0.92, attributes={"description": "Large oak tree"})
    ]

    for obj in objects:
        print(f"  {obj.label}: {obj.confidence:.0%} - {obj.attributes.get('description', '')}")

    # Example: Full analysis result
    print("\n--- Full Analysis Result Structure ---")
    result = AnalysisResult(
        analysis_type=AnalysisType.DESCRIPTION,
        description="A vibrant street scene with people walking...",
        objects=objects,
        text_regions=[TextRegion("STOP", 0.98), TextRegion("Main St", 0.85)],
        colors=colors,
        scene="urban street",
        confidence=0.87,
        processing_time=2.34
    )

    print(f"Analysis Type: {result.analysis_type.value}")
    print(f"Description: {result.description[:50]}...")
    print(f"Objects Found: {len(result.objects)}")
    print(f"Text Regions: {len(result.text_regions)}")
    print(f"Colors Analyzed: {len(result.colors)}")
    print(f"Processing Time: {result.processing_time:.2f}s")
    print(f"Confidence: {result.confidence:.0%}")

    print("\n=== Vision module ready for use ===")
    print("To analyze real images, provide API keys:")
    print("  export OPENAI_API_KEY=your-key")
    print("  export ANTHROPIC_API_KEY=your-key")


if __name__ == "__main__":
    asyncio.run(main())
