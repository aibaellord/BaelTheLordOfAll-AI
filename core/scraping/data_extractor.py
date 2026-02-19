"""
BAEL Data Extractor
====================

Structured data extraction from HTML/JSON/XML.
Multiple extraction strategies for different content types.

Features:
- CSS selector extraction
- XPath extraction
- Regex patterns
- JSON path extraction
- Auto-detection of data patterns
- Schema validation
- LLM-powered extraction
"""

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Pattern, Union

logger = logging.getLogger(__name__)


class ExtractorType(Enum):
    """Extraction method types."""
    CSS = "css"
    XPATH = "xpath"
    REGEX = "regex"
    JSONPATH = "jsonpath"
    AUTO = "auto"
    LLM = "llm"


@dataclass
class ExtractionPattern:
    """An extraction pattern definition."""
    name: str
    extractor_type: ExtractorType
    pattern: str

    # Processing
    attribute: Optional[str] = None  # For CSS/XPath - get attribute instead of text
    multiple: bool = False  # Return all matches or just first
    post_process: Optional[Callable[[str], Any]] = None
    default: Any = None

    # Validation
    required: bool = False
    validator: Optional[Callable[[Any], bool]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.extractor_type.value,
            "pattern": self.pattern,
            "attribute": self.attribute,
            "multiple": self.multiple,
            "required": self.required,
        }


@dataclass
class ExtractionResult:
    """Result of extraction."""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class DataExtractor:
    """
    Multi-method data extractor for BAEL.
    """

    def __init__(self):
        # Parsers (lazy loaded)
        self._bs4_available = None
        self._lxml_available = None

        # Common patterns for auto-detection
        self.auto_patterns = {
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "phone": r"[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}",
            "url": r"https?://[^\s<>\"{}|\\^`\[\]]+",
            "price": r"\$[\d,]+\.?\d*|\d+[\.,]\d{2}\s?(?:USD|EUR|GBP)",
            "date": r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{2}[-/]\d{2}",
            "ip": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
        }

    def _check_bs4(self) -> bool:
        """Check if BeautifulSoup is available."""
        if self._bs4_available is None:
            try:
                from bs4 import BeautifulSoup
                self._bs4_available = True
            except ImportError:
                self._bs4_available = False
        return self._bs4_available

    def _check_lxml(self) -> bool:
        """Check if lxml is available."""
        if self._lxml_available is None:
            try:
                from lxml import etree, html
                self._lxml_available = True
            except ImportError:
                self._lxml_available = False
        return self._lxml_available

    def extract(
        self,
        content: str,
        patterns: List[ExtractionPattern],
        content_type: str = "html",
    ) -> ExtractionResult:
        """
        Extract data using defined patterns.

        Args:
            content: HTML/JSON/XML content
            patterns: List of extraction patterns
            content_type: Type of content (html, json, xml)

        Returns:
            ExtractionResult
        """
        result = ExtractionResult(success=True)

        # Parse content
        parsed = None
        if content_type == "json":
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as e:
                result.success = False
                result.errors.append(f"JSON parse error: {e}")
                return result
        elif content_type in ("html", "xml"):
            if self._check_bs4():
                from bs4 import BeautifulSoup
                parser = "lxml" if self._check_lxml() else "html.parser"
                parsed = BeautifulSoup(content, parser)
            else:
                result.errors.append("BeautifulSoup not available")

        # Apply patterns
        for pattern in patterns:
            try:
                value = self._apply_pattern(content, parsed, pattern, content_type)

                # Validate
                if value is None and pattern.required:
                    result.errors.append(f"Required field '{pattern.name}' not found")
                    result.success = False
                elif pattern.validator and value is not None:
                    if not pattern.validator(value):
                        result.warnings.append(f"Validation failed for '{pattern.name}'")

                # Store result
                result.data[pattern.name] = value if value is not None else pattern.default

            except Exception as e:
                result.warnings.append(f"Error extracting '{pattern.name}': {e}")
                result.data[pattern.name] = pattern.default

        return result

    def _apply_pattern(
        self,
        raw_content: str,
        parsed: Any,
        pattern: ExtractionPattern,
        content_type: str,
    ) -> Any:
        """Apply a single extraction pattern."""

        if pattern.extractor_type == ExtractorType.CSS:
            return self._extract_css(parsed, pattern)

        elif pattern.extractor_type == ExtractorType.XPATH:
            return self._extract_xpath(raw_content, pattern)

        elif pattern.extractor_type == ExtractorType.REGEX:
            return self._extract_regex(raw_content, pattern)

        elif pattern.extractor_type == ExtractorType.JSONPATH:
            return self._extract_jsonpath(parsed, pattern)

        elif pattern.extractor_type == ExtractorType.AUTO:
            return self._extract_auto(raw_content, pattern)

        else:
            raise ValueError(f"Unknown extractor type: {pattern.extractor_type}")

    def _extract_css(
        self,
        soup: Any,
        pattern: ExtractionPattern,
    ) -> Any:
        """Extract using CSS selector."""
        if soup is None:
            return None

        elements = soup.select(pattern.pattern)

        if not elements:
            return [] if pattern.multiple else None

        def get_value(elem):
            if pattern.attribute:
                val = elem.get(pattern.attribute)
            else:
                val = elem.get_text(strip=True)

            if pattern.post_process:
                val = pattern.post_process(val)

            return val

        if pattern.multiple:
            return [get_value(e) for e in elements]
        else:
            return get_value(elements[0])

    def _extract_xpath(
        self,
        content: str,
        pattern: ExtractionPattern,
    ) -> Any:
        """Extract using XPath."""
        if not self._check_lxml():
            raise ImportError("lxml is required for XPath extraction")

        from lxml import html as lxml_html

        tree = lxml_html.fromstring(content)
        results = tree.xpath(pattern.pattern)

        if not results:
            return [] if pattern.multiple else None

        def process_result(r):
            if hasattr(r, 'text_content'):
                val = r.text_content().strip()
            else:
                val = str(r).strip()

            if pattern.post_process:
                val = pattern.post_process(val)

            return val

        if pattern.multiple:
            return [process_result(r) for r in results]
        else:
            return process_result(results[0])

    def _extract_regex(
        self,
        content: str,
        pattern: ExtractionPattern,
    ) -> Any:
        """Extract using regex."""
        regex = re.compile(pattern.pattern, re.IGNORECASE | re.MULTILINE)

        if pattern.multiple:
            matches = regex.findall(content)
            if pattern.post_process:
                matches = [pattern.post_process(m) for m in matches]
            return matches
        else:
            match = regex.search(content)
            if match:
                val = match.group(1) if match.groups() else match.group(0)
                if pattern.post_process:
                    val = pattern.post_process(val)
                return val
            return None

    def _extract_jsonpath(
        self,
        data: Any,
        pattern: ExtractionPattern,
    ) -> Any:
        """Extract using JSONPath-like syntax."""
        if data is None:
            return None

        # Simple JSONPath implementation
        path_parts = pattern.pattern.strip("$.").split(".")
        current = data

        for part in path_parts:
            if current is None:
                return None

            # Handle array index
            if "[" in part:
                key, idx_str = part.rstrip("]").split("[")
                if key:
                    current = current.get(key) if isinstance(current, dict) else None

                if current is not None and isinstance(current, list):
                    if idx_str == "*":
                        # Return all items
                        if pattern.post_process:
                            return [pattern.post_process(item) for item in current]
                        return current
                    else:
                        idx = int(idx_str)
                        current = current[idx] if idx < len(current) else None
            else:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None

        if pattern.post_process and current is not None:
            current = pattern.post_process(current)

        return current

    def _extract_auto(
        self,
        content: str,
        pattern: ExtractionPattern,
    ) -> Any:
        """Auto-detect and extract common patterns."""
        pattern_name = pattern.pattern.lower()

        if pattern_name in self.auto_patterns:
            regex = self.auto_patterns[pattern_name]
            matches = re.findall(regex, content, re.IGNORECASE)

            if pattern.multiple:
                return matches
            else:
                return matches[0] if matches else None

        return None

    def extract_tables(
        self,
        content: str,
    ) -> List[List[List[str]]]:
        """
        Extract all tables from HTML.

        Args:
            content: HTML content

        Returns:
            List of tables, each table is list of rows, each row is list of cells
        """
        if not self._check_bs4():
            return []

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(content, "html.parser" if not self._check_lxml() else "lxml")
        tables = []

        for table in soup.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                cells = []
                for cell in tr.find_all(["td", "th"]):
                    cells.append(cell.get_text(strip=True))
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(rows)

        return tables

    def extract_links(
        self,
        content: str,
        base_url: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Extract all links from HTML.

        Args:
            content: HTML content
            base_url: Base URL for resolving relative links

        Returns:
            List of link info dicts
        """
        if not self._check_bs4():
            return []

        from urllib.parse import urljoin

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(content, "html.parser" if not self._check_lxml() else "lxml")
        links = []

        for a in soup.find_all("a", href=True):
            href = a["href"]

            if base_url:
                href = urljoin(base_url, href)

            links.append({
                "url": href,
                "text": a.get_text(strip=True),
                "title": a.get("title"),
            })

        return links

    def extract_images(
        self,
        content: str,
        base_url: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Extract all images from HTML.

        Args:
            content: HTML content
            base_url: Base URL for resolving relative links

        Returns:
            List of image info dicts
        """
        if not self._check_bs4():
            return []

        from urllib.parse import urljoin

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(content, "html.parser" if not self._check_lxml() else "lxml")
        images = []

        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")

            if not src:
                continue

            if base_url:
                src = urljoin(base_url, src)

            images.append({
                "url": src,
                "alt": img.get("alt"),
                "width": img.get("width"),
                "height": img.get("height"),
            })

        return images

    def extract_metadata(
        self,
        content: str,
    ) -> Dict[str, Any]:
        """
        Extract page metadata (title, meta tags, OpenGraph, etc).

        Args:
            content: HTML content

        Returns:
            Metadata dict
        """
        if not self._check_bs4():
            return {}

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(content, "html.parser" if not self._check_lxml() else "lxml")
        metadata = {}

        # Title
        title = soup.find("title")
        if title:
            metadata["title"] = title.get_text(strip=True)

        # Meta tags
        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property")
            content_val = meta.get("content")

            if name and content_val:
                # Group by prefix
                if name.startswith("og:"):
                    if "opengraph" not in metadata:
                        metadata["opengraph"] = {}
                    metadata["opengraph"][name[3:]] = content_val
                elif name.startswith("twitter:"):
                    if "twitter" not in metadata:
                        metadata["twitter"] = {}
                    metadata["twitter"][name[8:]] = content_val
                else:
                    metadata[name] = content_val

        # Canonical URL
        canonical = soup.find("link", rel="canonical")
        if canonical:
            metadata["canonical"] = canonical.get("href")

        return metadata

    def create_schema(
        self,
        field_definitions: List[Dict[str, Any]],
    ) -> List[ExtractionPattern]:
        """
        Create extraction patterns from field definitions.

        Args:
            field_definitions: List of field dicts with name, selector, type, etc.

        Returns:
            List of ExtractionPattern
        """
        patterns = []

        for field_def in field_definitions:
            extractor_type = ExtractorType(field_def.get("type", "css"))

            pattern = ExtractionPattern(
                name=field_def["name"],
                extractor_type=extractor_type,
                pattern=field_def["selector"],
                attribute=field_def.get("attribute"),
                multiple=field_def.get("multiple", False),
                required=field_def.get("required", False),
                default=field_def.get("default"),
            )

            patterns.append(pattern)

        return patterns


def demo():
    """Demonstrate data extractor."""
    print("=" * 60)
    print("BAEL Data Extractor Demo")
    print("=" * 60)

    extractor = DataExtractor()

    # Sample HTML
    html = """
    <html>
        <head>
            <title>Test Page</title>
            <meta name="description" content="A test page">
        </head>
        <body>
            <h1 class="title">Hello World</h1>
            <p class="price">$99.99</p>
            <a href="https://example.com">Link</a>
            <p>Contact: test@example.com</p>
        </body>
    </html>
    """

    # Define patterns
    patterns = [
        ExtractionPattern(
            name="title",
            extractor_type=ExtractorType.CSS,
            pattern="h1.title",
        ),
        ExtractionPattern(
            name="price",
            extractor_type=ExtractorType.AUTO,
            pattern="price",
        ),
        ExtractionPattern(
            name="email",
            extractor_type=ExtractorType.AUTO,
            pattern="email",
        ),
    ]

    result = extractor.extract(html, patterns)

    print(f"\nExtraction result:")
    print(f"  Success: {result.success}")
    print(f"  Data: {result.data}")

    # Extract metadata
    metadata = extractor.extract_metadata(html)
    print(f"\nMetadata: {metadata}")


if __name__ == "__main__":
    demo()
