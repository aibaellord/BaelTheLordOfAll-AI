"""
BAEL - Scene Understanding
High-level scene analysis and visual reasoning.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from . import BoundingBox, DetectedObject, ImageType, SceneAnalysis

logger = logging.getLogger("BAEL.Vision.Scene")


class SceneCategory(Enum):
    """High-level scene categories."""
    INDOOR = "indoor"
    OUTDOOR = "outdoor"
    WORKSPACE = "workspace"
    NATURE = "nature"
    URBAN = "urban"
    DIGITAL = "digital"
    ABSTRACT = "abstract"
    UNKNOWN = "unknown"


class ContentType(Enum):
    """Types of content in scene."""
    TEXT_HEAVY = "text_heavy"
    IMAGE_HEAVY = "image_heavy"
    MIXED = "mixed"
    CODE = "code"
    UI_ELEMENTS = "ui_elements"
    DATA_VISUALIZATION = "data_visualization"


@dataclass
class SceneContext:
    """Context information about a scene."""
    category: SceneCategory
    content_type: ContentType
    activity: Optional[str]
    objects_summary: str
    text_summary: Optional[str]
    suggested_actions: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class SceneAnalyzer:
    """
    Scene understanding and visual reasoning.

    Features:
    - Scene categorization
    - Context extraction
    - Activity detection
    - Visual Q&A preparation
    - Action suggestions
    """

    def __init__(self):
        self._vision_processor = None
        self._ocr_engine = None
        self._llm = None

    async def _get_vision_processor(self):
        """Lazy load vision processor."""
        if self._vision_processor is None:
            from .vision_processor import get_vision_processor
            self._vision_processor = get_vision_processor()
        return self._vision_processor

    async def _get_ocr_engine(self):
        """Lazy load OCR engine."""
        if self._ocr_engine is None:
            from .ocr_engine import get_ocr_engine
            self._ocr_engine = get_ocr_engine()
        return self._ocr_engine

    async def _get_llm(self):
        """Lazy load LLM for reasoning."""
        if self._llm is None:
            try:
                from core.llm import get_provider
                self._llm = get_provider()
            except ImportError:
                pass
        return self._llm

    async def analyze_scene(
        self,
        image: Any,
        include_text: bool = True
    ) -> SceneContext:
        """
        Perform comprehensive scene analysis.

        Args:
            image: PIL Image object
            include_text: Whether to extract and analyze text

        Returns:
            SceneContext with full analysis
        """
        vision = await self._get_vision_processor()

        # Get basic analysis
        basic = await vision.analyze(image)

        # Determine scene category
        category = self._categorize_scene(basic)

        # Determine content type
        content_type = await self._determine_content_type(image, basic)

        # Get text if applicable
        text_summary = None
        if include_text and basic.text_content:
            text_summary = self._summarize_text(basic.text_content)

        # Detect activity
        activity = self._detect_activity(basic, text_summary)

        # Generate object summary
        objects_summary = self._summarize_objects(basic)

        # Suggest actions
        suggested_actions = self._suggest_actions(
            category, content_type, activity, basic
        )

        return SceneContext(
            category=category,
            content_type=content_type,
            activity=activity,
            objects_summary=objects_summary,
            text_summary=text_summary,
            suggested_actions=suggested_actions,
            metadata={
                "image_type": basic.image_type.value,
                "dominant_colors": basic.dominant_colors,
                "dimensions": basic.attributes.get("width", 0)
            }
        )

    def _categorize_scene(self, analysis: SceneAnalysis) -> SceneCategory:
        """Categorize the scene."""
        image_type = analysis.image_type

        # Digital content
        if image_type in [ImageType.SCREENSHOT, ImageType.CODE, ImageType.UI]:
            return SceneCategory.DIGITAL

        # Documents and diagrams
        if image_type in [ImageType.DOCUMENT, ImageType.DIAGRAM, ImageType.CHART]:
            return SceneCategory.WORKSPACE

        # For photographs, would need object detection
        # For now, use color heuristics
        colors = analysis.dominant_colors

        if "green" in colors and "blue" in colors:
            return SceneCategory.NATURE
        if "gray" in colors:
            return SceneCategory.URBAN

        return SceneCategory.UNKNOWN

    async def _determine_content_type(
        self,
        image: Any,
        analysis: SceneAnalysis
    ) -> ContentType:
        """Determine the type of content in the image."""
        image_type = analysis.image_type
        has_text = bool(analysis.text_content)

        if image_type == ImageType.CODE:
            return ContentType.CODE

        if image_type == ImageType.CHART:
            return ContentType.DATA_VISUALIZATION

        if image_type in [ImageType.SCREENSHOT, ImageType.UI]:
            return ContentType.UI_ELEMENTS

        if image_type == ImageType.DOCUMENT:
            return ContentType.TEXT_HEAVY

        if has_text and len(analysis.text_content or "") > 200:
            return ContentType.TEXT_HEAVY

        return ContentType.MIXED

    def _summarize_text(
        self,
        text: str,
        max_length: int = 200
    ) -> str:
        """Summarize extracted text."""
        if not text:
            return ""

        # Clean text
        text = " ".join(text.split())

        if len(text) <= max_length:
            return text

        # Truncate with ellipsis
        return text[:max_length-3] + "..."

    def _detect_activity(
        self,
        analysis: SceneAnalysis,
        text_summary: Optional[str]
    ) -> Optional[str]:
        """Detect what activity the scene represents."""
        image_type = analysis.image_type

        # Code activity
        if image_type == ImageType.CODE:
            if text_summary:
                if "error" in text_summary.lower():
                    return "debugging code"
                if "test" in text_summary.lower():
                    return "running tests"
            return "coding or programming"

        # Document activity
        if image_type == ImageType.DOCUMENT:
            return "reading or editing a document"

        # Chart activity
        if image_type == ImageType.CHART:
            return "analyzing data or statistics"

        # Screenshot activity
        if image_type == ImageType.SCREENSHOT:
            if text_summary:
                if "error" in text_summary.lower():
                    return "troubleshooting an issue"
                if "chat" in text_summary.lower() or "message" in text_summary.lower():
                    return "messaging or communication"
            return "using an application"

        return None

    def _summarize_objects(self, analysis: SceneAnalysis) -> str:
        """Generate summary of detected objects."""
        if not analysis.objects:
            return f"A {analysis.image_type.value} image"

        labels = [obj.label for obj in analysis.objects[:5]]
        return f"Contains: {', '.join(labels)}"

    def _suggest_actions(
        self,
        category: SceneCategory,
        content_type: ContentType,
        activity: Optional[str],
        analysis: SceneAnalysis
    ) -> List[str]:
        """Suggest relevant actions based on scene analysis."""
        suggestions = []

        # Based on content type
        if content_type == ContentType.CODE:
            suggestions.extend([
                "I can help analyze this code",
                "I can explain what this code does",
                "I can suggest improvements"
            ])

        elif content_type == ContentType.TEXT_HEAVY:
            suggestions.extend([
                "I can summarize this text",
                "I can extract key points",
                "I can answer questions about it"
            ])

        elif content_type == ContentType.DATA_VISUALIZATION:
            suggestions.extend([
                "I can help interpret this chart",
                "I can extract data points",
                "I can explain the trends"
            ])

        elif content_type == ContentType.UI_ELEMENTS:
            suggestions.extend([
                "I can help navigate this interface",
                "I can identify clickable elements",
                "I can describe the UI structure"
            ])

        # Based on activity
        if activity and "error" in activity:
            suggestions.insert(0, "I can help debug this error")

        if activity and "debug" in activity:
            suggestions.insert(0, "I can suggest debugging steps")

        return suggestions[:3]

    async def answer_visual_question(
        self,
        image: Any,
        question: str
    ) -> str:
        """
        Answer a question about the image.

        Uses available information to answer without
        expensive vision APIs.
        """
        # Get scene context
        context = await self.analyze_scene(image)

        # Prepare context for LLM
        context_text = f"""
Scene Analysis:
- Category: {context.category.value}
- Content Type: {context.content_type.value}
- Activity: {context.activity or 'unknown'}
- Objects: {context.objects_summary}
- Text Content: {context.text_summary or 'none detected'}
- Colors: {', '.join(context.metadata.get('dominant_colors', []))}

Question: {question}

Based on the scene analysis above, answer the question. If the information
is not available, say what you can determine and what would require visual inspection.
"""

        llm = await self._get_llm()
        if llm:
            try:
                response = await llm.generate(context_text, temperature=0.5)
                return response
            except Exception as e:
                logger.warning(f"LLM call failed: {e}")

        # Fallback to rule-based answer
        return self._rule_based_answer(context, question)

    def _rule_based_answer(
        self,
        context: SceneContext,
        question: str
    ) -> str:
        """Generate answer using rules when LLM unavailable."""
        question_lower = question.lower()

        # What is this / describe
        if any(w in question_lower for w in ["what is", "describe", "what does"]):
            return f"This appears to be a {context.content_type.value} scene, likely {context.activity or 'showing ' + context.objects_summary}."

        # Text-related questions
        if any(w in question_lower for w in ["text", "say", "read", "written"]):
            if context.text_summary:
                return f"The text reads: {context.text_summary}"
            return "I couldn't detect readable text in this image."

        # Color questions
        if "color" in question_lower:
            colors = context.metadata.get("dominant_colors", [])
            if colors:
                return f"The dominant colors are: {', '.join(colors)}"
            return "I couldn't determine the dominant colors."

        # Activity questions
        if any(w in question_lower for w in ["doing", "activity", "happening"]):
            if context.activity:
                return f"It appears someone is {context.activity}."
            return "I couldn't determine the specific activity."

        return f"Based on my analysis, this is a {context.category.value} scene with {context.content_type.value} content. {context.objects_summary}."

    async def compare_scenes(
        self,
        image1: Any,
        image2: Any
    ) -> Dict[str, Any]:
        """
        Compare two scenes.

        Returns:
            Comparison results including similarities and differences
        """
        vision = await self._get_vision_processor()

        # Analyze both
        analysis1 = await vision.analyze(image1)
        analysis2 = await vision.analyze(image2)

        context1 = await self.analyze_scene(image1)
        context2 = await self.analyze_scene(image2)

        # Compute visual similarity
        similarity = await vision.compute_similarity(image1, image2)

        # Find similarities
        similarities = []
        if context1.category == context2.category:
            similarities.append(f"Both are {context1.category.value} scenes")
        if context1.content_type == context2.content_type:
            similarities.append(f"Both contain {context1.content_type.value} content")

        common_colors = set(analysis1.dominant_colors) & set(analysis2.dominant_colors)
        if common_colors:
            similarities.append(f"Share colors: {', '.join(common_colors)}")

        # Find differences
        differences = []
        if context1.category != context2.category:
            differences.append(f"Different categories: {context1.category.value} vs {context2.category.value}")
        if context1.activity != context2.activity:
            act1 = context1.activity or "unknown"
            act2 = context2.activity or "unknown"
            differences.append(f"Different activities: {act1} vs {act2}")

        return {
            "visual_similarity": similarity,
            "similarities": similarities,
            "differences": differences,
            "scene1": {
                "category": context1.category.value,
                "content_type": context1.content_type.value,
                "activity": context1.activity
            },
            "scene2": {
                "category": context2.category.value,
                "content_type": context2.content_type.value,
                "activity": context2.activity
            }
        }

    async def extract_structured_data(
        self,
        image: Any,
        data_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from image.

        Args:
            image: PIL Image
            data_type: Expected data type (table, form, chart, etc.)

        Returns:
            Extracted structured data
        """
        vision = await self._get_vision_processor()
        ocr = await self._get_ocr_engine()

        analysis = await vision.analyze(image)

        result = {
            "type": data_type or analysis.image_type.value,
            "data": {}
        }

        # For text-heavy content
        if analysis.image_type in [ImageType.DOCUMENT, ImageType.SCREENSHOT]:
            ocr_result = await ocr.extract_with_details(image)

            # Group text by vertical position (for table-like structure)
            rows = {}
            for block in ocr_result.blocks:
                row_key = block.bbox.y // 30  # Group by ~30px rows
                if row_key not in rows:
                    rows[row_key] = []
                rows[row_key].append({
                    "text": block.text,
                    "x": block.bbox.x,
                    "confidence": block.confidence
                })

            # Sort each row by x position
            structured_rows = []
            for row_key in sorted(rows.keys()):
                row = sorted(rows[row_key], key=lambda x: x["x"])
                structured_rows.append([item["text"] for item in row])

            result["data"]["rows"] = structured_rows
            result["data"]["raw_text"] = ocr_result.full_text

        return result


# Global instance
_scene_analyzer: Optional[SceneAnalyzer] = None


def get_scene_analyzer() -> SceneAnalyzer:
    """Get or create scene analyzer instance."""
    global _scene_analyzer
    if _scene_analyzer is None:
        _scene_analyzer = SceneAnalyzer()
    return _scene_analyzer
