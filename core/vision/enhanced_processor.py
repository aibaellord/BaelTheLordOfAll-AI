"""
BAEL - Enhanced Vision Processor
Zero-cost image analysis using free local libraries.
Additional capabilities on top of the base vision processor.
"""

import asyncio
import base64
import hashlib
import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from . import (AnalysisType, BoundingBox, DetectedObject, ImageType,
               SceneAnalysis, VisionConfig)

logger = logging.getLogger("BAEL.Vision.Enhanced")


# Try to import image processing libraries
try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageStat
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("PIL not available - enhanced vision limited")

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


@dataclass
class EnhancedImageInfo:
    """Enhanced image information."""
    width: int
    height: int
    format: str
    mode: str
    size_bytes: int
    hash: str
    aspect_ratio: float
    is_portrait: bool
    estimated_quality: float


class EnhancedVisionProcessor:
    """
    Enhanced vision processing with additional zero-cost capabilities.

    Features:
    - Advanced color analysis
    - Image enhancement
    - Template matching
    - Visual diff detection
    - Quality assessment
    """

    def __init__(self, config: Optional[VisionConfig] = None):
        self.config = config or VisionConfig()
        self._cache: Dict[str, Any] = {}

    async def load_image(
        self,
        source: Union[str, bytes, Path]
    ) -> Optional[Any]:
        """Load image from various sources."""
        if not HAS_PIL:
            logger.error("PIL required for image loading")
            return None

        try:
            if isinstance(source, bytes):
                return Image.open(io.BytesIO(source))
            elif isinstance(source, (str, Path)):
                path = Path(source)
                if path.exists():
                    return Image.open(path)
                elif str(source).startswith(("http://", "https://")):
                    try:
                        import urllib.request
                        with urllib.request.urlopen(str(source)) as response:
                            data = response.read()
                            return Image.open(io.BytesIO(data))
                    except Exception as e:
                        logger.error(f"Failed to fetch URL: {e}")
                        return None
            return None
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            return None

    async def get_enhanced_info(
        self,
        image: Any
    ) -> Optional[EnhancedImageInfo]:
        """Get enhanced image information."""
        if not HAS_PIL:
            return None

        try:
            buffer = io.BytesIO()
            image.save(buffer, format=image.format or "PNG")
            image_bytes = buffer.getvalue()

            aspect_ratio = image.width / image.height

            # Estimate quality based on file size and resolution
            pixels = image.width * image.height
            bytes_per_pixel = len(image_bytes) / pixels if pixels > 0 else 0
            quality = min(1.0, bytes_per_pixel / 3.0)  # Rough estimate

            return EnhancedImageInfo(
                width=image.width,
                height=image.height,
                format=image.format or "unknown",
                mode=image.mode,
                size_bytes=len(image_bytes),
                hash=hashlib.md5(image_bytes).hexdigest(),
                aspect_ratio=aspect_ratio,
                is_portrait=image.height > image.width,
                estimated_quality=quality
            )
        except Exception as e:
            logger.error(f"Failed to get enhanced info: {e}")
            return None

    async def enhance_image(
        self,
        image: Any,
        brightness: float = 1.0,
        contrast: float = 1.0,
        sharpness: float = 1.0,
        color: float = 1.0
    ) -> Optional[Any]:
        """
        Enhance image quality.

        Args:
            image: PIL Image
            brightness: Brightness factor (1.0 = original)
            contrast: Contrast factor
            sharpness: Sharpness factor
            color: Color saturation factor

        Returns:
            Enhanced image
        """
        if not HAS_PIL:
            return image

        try:
            result = image.copy()

            if brightness != 1.0:
                enhancer = ImageEnhance.Brightness(result)
                result = enhancer.enhance(brightness)

            if contrast != 1.0:
                enhancer = ImageEnhance.Contrast(result)
                result = enhancer.enhance(contrast)

            if sharpness != 1.0:
                enhancer = ImageEnhance.Sharpness(result)
                result = enhancer.enhance(sharpness)

            if color != 1.0:
                enhancer = ImageEnhance.Color(result)
                result = enhancer.enhance(color)

            return result
        except Exception as e:
            logger.error(f"Enhancement failed: {e}")
            return image

    async def detect_changes(
        self,
        image1: Any,
        image2: Any,
        threshold: float = 30
    ) -> Dict[str, Any]:
        """
        Detect changes between two images.

        Args:
            image1: First image
            image2: Second image
            threshold: Difference threshold

        Returns:
            Change detection results
        """
        if not HAS_PIL or not HAS_NUMPY:
            return {"error": "PIL and NumPy required"}

        try:
            # Resize to same size
            size = (min(image1.width, image2.width),
                    min(image1.height, image2.height))
            img1 = image1.copy().resize(size).convert("RGB")
            img2 = image2.copy().resize(size).convert("RGB")

            # Convert to arrays
            arr1 = np.array(img1, dtype=np.float32)
            arr2 = np.array(img2, dtype=np.float32)

            # Calculate difference
            diff = np.abs(arr1 - arr2)
            diff_mean = np.mean(diff, axis=2)

            # Find changed regions
            changed = diff_mean > threshold
            change_percentage = np.sum(changed) / changed.size * 100

            # Find bounding boxes of changes
            change_regions = []
            if np.any(changed):
                # Simple connected component analysis
                rows, cols = np.where(changed)
                if len(rows) > 0:
                    change_regions.append({
                        "x": int(np.min(cols)),
                        "y": int(np.min(rows)),
                        "width": int(np.max(cols) - np.min(cols)),
                        "height": int(np.max(rows) - np.min(rows))
                    })

            return {
                "has_changes": change_percentage > 1,
                "change_percentage": round(change_percentage, 2),
                "change_regions": change_regions,
                "mean_difference": float(np.mean(diff_mean))
            }
        except Exception as e:
            logger.error(f"Change detection failed: {e}")
            return {"error": str(e)}

    async def find_template(
        self,
        image: Any,
        template: Any,
        threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """
        Find template in image (basic template matching).

        Args:
            image: Main image
            template: Template to find
            threshold: Match threshold

        Returns:
            List of match locations
        """
        if not HAS_PIL or not HAS_NUMPY:
            return []

        try:
            # Convert to grayscale
            img_gray = np.array(image.convert("L"), dtype=np.float32)
            tmpl_gray = np.array(template.convert("L"), dtype=np.float32)

            th, tw = tmpl_gray.shape
            ih, iw = img_gray.shape

            if th > ih or tw > iw:
                return []

            matches = []

            # Sliding window matching
            step = max(1, min(th, tw) // 4)

            for y in range(0, ih - th + 1, step):
                for x in range(0, iw - tw + 1, step):
                    window = img_gray[y:y+th, x:x+tw]

                    # Normalized cross-correlation
                    correlation = np.corrcoef(
                        window.flatten(),
                        tmpl_gray.flatten()
                    )[0, 1]

                    if correlation >= threshold:
                        matches.append({
                            "x": x,
                            "y": y,
                            "width": tw,
                            "height": th,
                            "confidence": float(correlation)
                        })

            # Remove overlapping matches
            return self._remove_overlapping(matches)

        except Exception as e:
            logger.error(f"Template matching failed: {e}")
            return []

    def _remove_overlapping(
        self,
        matches: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove overlapping match regions."""
        if not matches:
            return []

        # Sort by confidence
        matches = sorted(matches, key=lambda x: x["confidence"], reverse=True)

        result = []
        for match in matches:
            overlaps = False
            for existing in result:
                # Check for significant overlap
                x_overlap = max(0, min(match["x"] + match["width"],
                                       existing["x"] + existing["width"]) -
                               max(match["x"], existing["x"]))
                y_overlap = max(0, min(match["y"] + match["height"],
                                       existing["y"] + existing["height"]) -
                               max(match["y"], existing["y"]))

                overlap_area = x_overlap * y_overlap
                match_area = match["width"] * match["height"]

                if overlap_area > match_area * 0.5:
                    overlaps = True
                    break

            if not overlaps:
                result.append(match)

        return result

    async def extract_dominant_colors(
        self,
        image: Any,
        n_colors: int = 5,
        algorithm: str = "kmeans"
    ) -> List[Dict[str, Any]]:
        """
        Extract dominant colors using clustering.

        Args:
            image: PIL Image
            n_colors: Number of colors to extract
            algorithm: Clustering algorithm (kmeans or quantize)

        Returns:
            List of dominant colors with percentages
        """
        if not HAS_PIL:
            return []

        try:
            # Resize for speed
            img = image.copy()
            img.thumbnail((100, 100))

            if img.mode != "RGB":
                img = img.convert("RGB")

            if algorithm == "quantize":
                # Use PIL's built-in quantization
                quantized = img.quantize(colors=n_colors)
                palette = quantized.getpalette()[:n_colors*3]

                colors = []
                for i in range(n_colors):
                    r = palette[i*3]
                    g = palette[i*3+1]
                    b = palette[i*3+2]
                    colors.append({
                        "rgb": (r, g, b),
                        "hex": f"#{r:02x}{g:02x}{b:02x}",
                        "percentage": 100.0 / n_colors  # Approximate
                    })
                return colors

            elif HAS_NUMPY:
                # K-means clustering
                pixels = np.array(img).reshape(-1, 3).astype(np.float32)

                # Simple k-means
                centers = pixels[np.random.choice(len(pixels), n_colors, replace=False)]

                for _ in range(10):  # Iterations
                    # Assign to nearest center
                    distances = np.sqrt(np.sum((pixels[:, np.newaxis] - centers) ** 2, axis=2))
                    labels = np.argmin(distances, axis=1)

                    # Update centers
                    new_centers = np.array([
                        pixels[labels == i].mean(axis=0) if np.sum(labels == i) > 0 else centers[i]
                        for i in range(n_colors)
                    ])

                    if np.allclose(centers, new_centers):
                        break
                    centers = new_centers

                # Calculate percentages
                colors = []
                for i in range(n_colors):
                    count = np.sum(labels == i)
                    percentage = count / len(labels) * 100
                    r, g, b = int(centers[i, 0]), int(centers[i, 1]), int(centers[i, 2])
                    colors.append({
                        "rgb": (r, g, b),
                        "hex": f"#{r:02x}{g:02x}{b:02x}",
                        "percentage": round(percentage, 1)
                    })

                return sorted(colors, key=lambda x: x["percentage"], reverse=True)

            return []

        except Exception as e:
            logger.error(f"Color extraction failed: {e}")
            return []

    async def assess_quality(
        self,
        image: Any
    ) -> Dict[str, Any]:
        """
        Assess image quality metrics.

        Returns:
            Quality assessment including blur, noise, exposure
        """
        if not HAS_PIL or not HAS_NUMPY:
            return {"error": "PIL and NumPy required"}

        try:
            # Convert to grayscale
            gray = np.array(image.convert("L"), dtype=np.float32)

            # Blur detection (Laplacian variance)
            laplacian = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]])
            from scipy.signal import convolve2d
            blur_var = np.var(convolve2d(gray, laplacian, mode='valid'))
            is_blurry = blur_var < 100

        except ImportError:
            # Without scipy, use simpler method
            blur_var = np.var(gray)
            is_blurry = blur_var < 500

        try:
            # Exposure analysis
            hist = np.histogram(gray.flatten(), bins=256, range=(0, 255))[0]
            hist = hist.astype(float) / hist.sum()

            dark_pixels = np.sum(hist[:50])
            bright_pixels = np.sum(hist[205:])

            exposure = "normal"
            if dark_pixels > 0.5:
                exposure = "underexposed"
            elif bright_pixels > 0.5:
                exposure = "overexposed"

            # Noise estimation (standard deviation of smooth regions)
            noise_estimate = np.std(gray[::2, ::2] - gray[1::2, 1::2])

            # Overall quality score
            quality_score = 100.0
            if is_blurry:
                quality_score -= 30
            if exposure != "normal":
                quality_score -= 20
            if noise_estimate > 30:
                quality_score -= 20

            return {
                "blur_variance": float(blur_var),
                "is_blurry": is_blurry,
                "exposure": exposure,
                "noise_estimate": float(noise_estimate),
                "quality_score": max(0, quality_score),
                "recommendations": self._get_quality_recommendations(
                    is_blurry, exposure, noise_estimate
                )
            }

        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            return {"error": str(e)}

    def _get_quality_recommendations(
        self,
        is_blurry: bool,
        exposure: str,
        noise: float
    ) -> List[str]:
        """Get recommendations for improving image quality."""
        recommendations = []

        if is_blurry:
            recommendations.append("Image appears blurry - try sharpening or using a higher resolution source")

        if exposure == "underexposed":
            recommendations.append("Image is underexposed - try increasing brightness")
        elif exposure == "overexposed":
            recommendations.append("Image is overexposed - try reducing brightness")

        if noise > 30:
            recommendations.append("Image has significant noise - consider noise reduction")

        return recommendations if recommendations else ["Image quality is good"]

    async def to_base64(
        self,
        image: Any,
        format: str = "PNG"
    ) -> str:
        """Convert image to base64 string."""
        if not HAS_PIL:
            return ""

        try:
            buffer = io.BytesIO()
            image.save(buffer, format=format)
            return base64.b64encode(buffer.getvalue()).decode()
        except Exception as e:
            logger.error(f"Base64 conversion failed: {e}")
            return ""


# Global instance
_enhanced_processor: Optional[EnhancedVisionProcessor] = None


def get_enhanced_vision_processor(
    config: Optional[VisionConfig] = None
) -> EnhancedVisionProcessor:
    """Get or create enhanced vision processor instance."""
    global _enhanced_processor
    if _enhanced_processor is None or config is not None:
        _enhanced_processor = EnhancedVisionProcessor(config)
    return _enhanced_processor
