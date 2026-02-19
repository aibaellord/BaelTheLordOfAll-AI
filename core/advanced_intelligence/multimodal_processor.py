"""
BAEL Multi-Modal Processing Engine
===================================

Process and integrate multiple modalities: text, code, data, structured, etc.

"All forms of information are unified in understanding." — Ba'el
"""

import asyncio
import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import (
    Any, Callable, Dict, List, Optional, Set, Tuple, Union,
    TypeVar, Generic, AsyncIterator
)
from collections import defaultdict
import base64


class Modality(Enum):
    """Types of input modalities."""
    TEXT = "text"                    # Natural language text
    CODE = "code"                    # Programming code
    DATA = "data"                    # Structured data (JSON, CSV)
    MARKDOWN = "markdown"            # Markdown documents
    HTML = "html"                    # HTML content
    SQL = "sql"                      # SQL queries
    REGEX = "regex"                  # Regular expressions
    MATH = "math"                    # Mathematical expressions
    CONFIG = "config"                # Configuration files
    LOG = "log"                      # Log files
    COMMAND = "command"              # Shell commands
    API = "api"                      # API specifications
    SCHEMA = "schema"                # Data schemas


class ProcessingStage(Enum):
    """Stages of processing."""
    DETECTION = "detection"          # Detect modality
    PARSING = "parsing"              # Parse content
    VALIDATION = "validation"        # Validate structure
    NORMALIZATION = "normalization"  # Normalize format
    ENRICHMENT = "enrichment"        # Add metadata
    TRANSFORMATION = "transformation"  # Transform if needed
    INTEGRATION = "integration"      # Integrate with other modalities


class ContentQuality(Enum):
    """Quality assessment of content."""
    EXCELLENT = 5
    GOOD = 4
    ACCEPTABLE = 3
    POOR = 2
    INVALID = 1


@dataclass
class ModalitySignature:
    """Signature for detecting a modality."""
    modality: Modality
    patterns: List[str]
    keywords: List[str]
    extensions: List[str]
    priority: int = 5


@dataclass
class ParsedContent:
    """Result of parsing content."""
    id: str
    original: str
    modality: Modality
    structured: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    quality: ContentQuality = ContentQuality.ACCEPTABLE
    confidence: float = 0.8
    parsing_time_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class TransformResult:
    """Result of content transformation."""
    source_modality: Modality
    target_modality: Modality
    original: str
    transformed: str
    success: bool
    confidence: float = 0.8
    notes: List[str] = field(default_factory=list)


@dataclass
class IntegrationResult:
    """Result of integrating multiple modalities."""
    modalities_used: List[Modality]
    unified_content: Dict[str, Any]
    relationships: List[Dict[str, Any]]
    confidence: float
    processing_time_ms: float


class ModalityDetector:
    """Detect the modality of content."""

    def __init__(self):
        self.signatures = self._init_signatures()

    def _init_signatures(self) -> List[ModalitySignature]:
        """Initialize modality signatures."""
        return [
            ModalitySignature(
                modality=Modality.CODE,
                patterns=[
                    r"^(def|class|function|import|from|const|let|var|public|private)\s",
                    r"^\s*(if|for|while|try|catch|switch)\s*[\(\{]",
                    r"^#include\s+[<\"]",
                    r"^package\s+\w+",
                ],
                keywords=["def ", "class ", "import ", "function", "return ", "const ", "let ", "var "],
                extensions=[".py", ".js", ".ts", ".java", ".cpp", ".go", ".rs", ".rb"],
                priority=10
            ),
            ModalitySignature(
                modality=Modality.SQL,
                patterns=[
                    r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\s",
                    r"\bFROM\s+\w+",
                    r"\bWHERE\s+\w+",
                ],
                keywords=["SELECT ", "FROM ", "WHERE ", "INSERT ", "UPDATE ", "CREATE TABLE"],
                extensions=[".sql"],
                priority=9
            ),
            ModalitySignature(
                modality=Modality.HTML,
                patterns=[
                    r"^<!DOCTYPE\s+html",
                    r"^<html",
                    r"<(div|span|p|a|img|table|form)\s",
                ],
                keywords=["<html", "<body", "<div", "<head>", "</html>"],
                extensions=[".html", ".htm"],
                priority=8
            ),
            ModalitySignature(
                modality=Modality.MARKDOWN,
                patterns=[
                    r"^#+\s+",
                    r"^\*\*[^*]+\*\*",
                    r"^\-\s+\[[\sx]\]",
                    r"^```\w*\n",
                ],
                keywords=["# ", "## ", "```", "**", "- [ ]", "- [x]"],
                extensions=[".md", ".markdown"],
                priority=7
            ),
            ModalitySignature(
                modality=Modality.DATA,
                patterns=[
                    r'^\s*[\{\[]',  # JSON start
                    r'^[\w,]+\n[\w,]+',  # CSV pattern
                ],
                keywords=["{", "}", "[", "]", '": "', '": {'],
                extensions=[".json", ".csv", ".yaml", ".yml"],
                priority=6
            ),
            ModalitySignature(
                modality=Modality.CONFIG,
                patterns=[
                    r'^\[[\w\s]+\]',  # INI section
                    r'^\w+\s*[=:]\s*\w+',  # Key-value
                ],
                keywords=["[section]", "=", ": "],
                extensions=[".ini", ".conf", ".cfg", ".toml"],
                priority=5
            ),
            ModalitySignature(
                modality=Modality.LOG,
                patterns=[
                    r'^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}',
                    r'^\[\w+\]\s+\d{4}',
                    r'^(INFO|DEBUG|WARN|ERROR|FATAL)\s+',
                ],
                keywords=["INFO", "DEBUG", "WARN", "ERROR", "FATAL", "Exception"],
                extensions=[".log"],
                priority=5
            ),
            ModalitySignature(
                modality=Modality.COMMAND,
                patterns=[
                    r'^(sudo|cd|ls|cat|echo|grep|curl|wget|npm|pip|git)\s',
                    r'^\$\s+\w+',
                ],
                keywords=["sudo ", "cd ", "ls ", "cat ", "echo ", "grep ", "curl ", "git "],
                extensions=[".sh", ".bash", ".zsh"],
                priority=4
            ),
            ModalitySignature(
                modality=Modality.REGEX,
                patterns=[
                    r'^[\^/].*[\$/]$',
                    r'\\[dwsDWS]',
                    r'[\[\(]\?[:\!]',
                ],
                keywords=["\\d", "\\w", "\\s", "[a-z]", "(.*)", "^", "$"],
                extensions=[],
                priority=3
            ),
            ModalitySignature(
                modality=Modality.MATH,
                patterns=[
                    r'[\+\-\*/\^]=',
                    r'\b(sin|cos|tan|log|sqrt|sum|integral)\b',
                    r'\\frac\{',
                ],
                keywords=["x =", "y =", "f(x)", "dx", "integral", "sum", "sqrt"],
                extensions=[".tex"],
                priority=3
            ),
            ModalitySignature(
                modality=Modality.TEXT,
                patterns=[],
                keywords=[],
                extensions=[".txt"],
                priority=1  # Default fallback
            ),
        ]

    async def detect(self, content: str, hint: Optional[Modality] = None) -> Tuple[Modality, float]:
        """Detect the modality of content."""
        if hint:
            return hint, 1.0

        if not content or not content.strip():
            return Modality.TEXT, 0.5

        scores: Dict[Modality, float] = defaultdict(float)
        content_lower = content.lower()

        for sig in self.signatures:
            score = 0.0

            # Check patterns
            for pattern in sig.patterns:
                try:
                    if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                        score += 2.0
                except re.error:
                    pass

            # Check keywords
            for keyword in sig.keywords:
                if keyword.lower() in content_lower:
                    score += 1.0

            # Apply priority weight
            score *= (sig.priority / 10.0)
            scores[sig.modality] = score

        # Find best match
        if not scores or max(scores.values()) == 0:
            return Modality.TEXT, 0.5

        best_modality = max(scores, key=scores.get)
        max_score = scores[best_modality]

        # Normalize confidence
        total_score = sum(scores.values())
        confidence = max_score / total_score if total_score > 0 else 0.5

        return best_modality, min(confidence, 1.0)


class TextParser:
    """Parse text content."""

    async def parse(self, content: str) -> Dict[str, Any]:
        """Parse text into structured form."""
        lines = content.split('\n')
        words = content.split()
        sentences = re.split(r'[.!?]+', content)

        return {
            "type": "text",
            "content": content,
            "metrics": {
                "lines": len(lines),
                "words": len(words),
                "characters": len(content),
                "sentences": len([s for s in sentences if s.strip()]),
                "paragraphs": len([p for p in content.split('\n\n') if p.strip()])
            },
            "structure": {
                "lines": lines[:100],  # First 100 lines
                "first_sentence": sentences[0].strip() if sentences else "",
                "word_frequency": self._word_frequency(words)
            }
        }

    def _word_frequency(self, words: List[str], top_n: int = 20) -> Dict[str, int]:
        """Calculate word frequency."""
        freq = defaultdict(int)
        for word in words:
            cleaned = re.sub(r'[^\w]', '', word.lower())
            if cleaned and len(cleaned) > 2:
                freq[cleaned] += 1
        return dict(sorted(freq.items(), key=lambda x: -x[1])[:top_n])


class CodeParser:
    """Parse code content."""

    def __init__(self):
        self.language_patterns = {
            "python": [r"^def\s+\w+", r"^class\s+\w+", r"^import\s+", r"^from\s+\w+\s+import"],
            "javascript": [r"\bfunction\s+\w+", r"\bconst\s+\w+", r"\blet\s+\w+", r"=>"],
            "typescript": [r"\binterface\s+\w+", r":\s+(string|number|boolean)", r"\btype\s+\w+"],
            "java": [r"\bpublic\s+class", r"\bprivate\s+", r"\bpackage\s+\w+"],
            "go": [r"\bfunc\s+\w+", r"\bpackage\s+\w+", r"\btype\s+\w+\s+struct"],
            "rust": [r"\bfn\s+\w+", r"\blet\s+mut", r"\bimpl\s+\w+"],
            "cpp": [r"#include\s+[<\"]", r"\bstd::", r"\btemplate\s*<"],
        }

    async def parse(self, content: str) -> Dict[str, Any]:
        """Parse code into structured form."""
        language = await self._detect_language(content)
        lines = content.split('\n')

        return {
            "type": "code",
            "language": language,
            "content": content,
            "metrics": {
                "lines": len(lines),
                "code_lines": len([l for l in lines if l.strip() and not l.strip().startswith('#')]),
                "comment_lines": len([l for l in lines if l.strip().startswith('#')]),
                "blank_lines": len([l for l in lines if not l.strip()]),
                "characters": len(content)
            },
            "structure": {
                "imports": self._extract_imports(content, language),
                "functions": self._extract_functions(content, language),
                "classes": self._extract_classes(content, language)
            }
        }

    async def _detect_language(self, content: str) -> str:
        """Detect programming language."""
        scores = defaultdict(int)

        for lang, patterns in self.language_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.MULTILINE):
                    scores[lang] += 1

        return max(scores, key=scores.get) if scores else "unknown"

    def _extract_imports(self, content: str, language: str) -> List[str]:
        """Extract import statements."""
        imports = []

        if language == "python":
            imports = re.findall(r'^(?:from\s+[\w.]+\s+)?import\s+.+$', content, re.MULTILINE)
        elif language in ("javascript", "typescript"):
            imports = re.findall(r'^import\s+.+$', content, re.MULTILINE)
        elif language == "java":
            imports = re.findall(r'^import\s+[\w.]+;$', content, re.MULTILINE)
        elif language == "go":
            imports = re.findall(r'^\s*"[\w/]+"', content, re.MULTILINE)

        return imports[:50]  # Limit

    def _extract_functions(self, content: str, language: str) -> List[str]:
        """Extract function names."""
        functions = []

        if language == "python":
            functions = re.findall(r'^def\s+(\w+)\s*\(', content, re.MULTILINE)
        elif language in ("javascript", "typescript"):
            functions = re.findall(r'\bfunction\s+(\w+)\s*\(', content)
            functions += re.findall(r'\bconst\s+(\w+)\s*=\s*(?:async\s+)?\(', content)
        elif language == "go":
            functions = re.findall(r'^func\s+(\w+)\s*\(', content, re.MULTILINE)
        elif language == "rust":
            functions = re.findall(r'^fn\s+(\w+)\s*\(', content, re.MULTILINE)

        return functions[:100]

    def _extract_classes(self, content: str, language: str) -> List[str]:
        """Extract class names."""
        classes = []

        if language == "python":
            classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
        elif language in ("javascript", "typescript"):
            classes = re.findall(r'\bclass\s+(\w+)', content)
        elif language == "java":
            classes = re.findall(r'\bclass\s+(\w+)', content)
        elif language == "go":
            classes = re.findall(r'\btype\s+(\w+)\s+struct', content)

        return classes[:50]


class DataParser:
    """Parse structured data content."""

    async def parse(self, content: str) -> Dict[str, Any]:
        """Parse data into structured form."""
        # Try JSON
        try:
            data = json.loads(content)
            return {
                "type": "data",
                "format": "json",
                "content": data,
                "metrics": {
                    "keys": self._count_keys(data) if isinstance(data, dict) else 0,
                    "items": len(data) if isinstance(data, list) else 1,
                    "depth": self._calculate_depth(data)
                },
                "structure": {
                    "schema": self._infer_schema(data)
                }
            }
        except json.JSONDecodeError:
            pass

        # Try CSV
        lines = content.strip().split('\n')
        if len(lines) > 1:
            delimiter = self._detect_delimiter(lines[0])
            if delimiter:
                headers = lines[0].split(delimiter)
                rows = [line.split(delimiter) for line in lines[1:]]
                return {
                    "type": "data",
                    "format": "csv",
                    "content": {"headers": headers, "rows": rows},
                    "metrics": {
                        "columns": len(headers),
                        "rows": len(rows)
                    },
                    "structure": {
                        "headers": headers
                    }
                }

        # Unknown format
        return {
            "type": "data",
            "format": "unknown",
            "content": content,
            "metrics": {"lines": len(lines)}
        }

    def _detect_delimiter(self, line: str) -> Optional[str]:
        """Detect CSV delimiter."""
        for delim in [',', '\t', ';', '|']:
            if line.count(delim) >= 2:
                return delim
        return None

    def _count_keys(self, data: Any) -> int:
        """Count total keys in nested structure."""
        if isinstance(data, dict):
            return len(data) + sum(self._count_keys(v) for v in data.values())
        elif isinstance(data, list):
            return sum(self._count_keys(item) for item in data)
        return 0

    def _calculate_depth(self, data: Any, current: int = 0) -> int:
        """Calculate nesting depth."""
        if isinstance(data, dict):
            if not data:
                return current + 1
            return max(self._calculate_depth(v, current + 1) for v in data.values())
        elif isinstance(data, list):
            if not data:
                return current + 1
            return max(self._calculate_depth(item, current + 1) for item in data)
        return current

    def _infer_schema(self, data: Any) -> Dict[str, Any]:
        """Infer schema from data."""
        if isinstance(data, dict):
            return {k: self._infer_type(v) for k, v in list(data.items())[:20]}
        elif isinstance(data, list) and data:
            return {"[items]": self._infer_type(data[0])}
        return {"type": type(data).__name__}

    def _infer_type(self, value: Any) -> str:
        """Infer type of value."""
        if isinstance(value, dict):
            return "object"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif value is None:
            return "null"
        return "string"


class MarkdownParser:
    """Parse Markdown content."""

    async def parse(self, content: str) -> Dict[str, Any]:
        """Parse Markdown into structured form."""
        lines = content.split('\n')

        headers = []
        code_blocks = []
        links = []
        lists = []

        in_code_block = False
        current_code = []

        for line in lines:
            # Headers
            if line.startswith('#'):
                level = len(re.match(r'^#+', line).group())
                text = line.lstrip('#').strip()
                headers.append({"level": level, "text": text})

            # Code blocks
            if line.startswith('```'):
                if in_code_block:
                    code_blocks.append('\n'.join(current_code))
                    current_code = []
                    in_code_block = False
                else:
                    in_code_block = True
            elif in_code_block:
                current_code.append(line)

            # Links
            link_matches = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', line)
            links.extend([{"text": m[0], "url": m[1]} for m in link_matches])

            # Lists
            if re.match(r'^\s*[-*+]\s+', line):
                lists.append(line.strip())
            elif re.match(r'^\s*\d+\.\s+', line):
                lists.append(line.strip())

        return {
            "type": "markdown",
            "content": content,
            "metrics": {
                "lines": len(lines),
                "headers": len(headers),
                "code_blocks": len(code_blocks),
                "links": len(links),
                "list_items": len(lists)
            },
            "structure": {
                "headers": headers[:50],
                "code_blocks": code_blocks[:20],
                "links": links[:50],
                "list_items": lists[:100]
            }
        }


class MultiModalProcessor:
    """
    The ultimate multi-modal processing engine.

    Detects, parses, transforms, and integrates multiple content modalities.
    """

    def __init__(self):
        self.detector = ModalityDetector()
        self.parsers: Dict[Modality, Any] = {
            Modality.TEXT: TextParser(),
            Modality.CODE: CodeParser(),
            Modality.DATA: DataParser(),
            Modality.MARKDOWN: MarkdownParser(),
        }
        self.processing_history: List[ParsedContent] = []
        self.data_dir = Path("data/multimodal")
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def process(
        self,
        content: str,
        hint: Optional[Modality] = None
    ) -> ParsedContent:
        """Process content of any modality."""
        start_time = time.time()

        # Detect modality
        modality, confidence = await self.detector.detect(content, hint)

        # Parse based on modality
        parser = self.parsers.get(modality, self.parsers[Modality.TEXT])
        structured = await parser.parse(content)

        # Create result
        content_id = hashlib.sha256(content.encode()).hexdigest()[:16]

        result = ParsedContent(
            id=content_id,
            original=content,
            modality=modality,
            structured=structured,
            metadata={
                "detected_at": datetime.now().isoformat(),
                "detection_confidence": confidence
            },
            confidence=confidence,
            parsing_time_ms=(time.time() - start_time) * 1000
        )

        # Assess quality
        result.quality = self._assess_quality(result)

        self.processing_history.append(result)
        return result

    def _assess_quality(self, result: ParsedContent) -> ContentQuality:
        """Assess content quality."""
        score = 0

        # Has structured content
        if result.structured:
            score += 2

        # Good detection confidence
        if result.confidence > 0.8:
            score += 2
        elif result.confidence > 0.6:
            score += 1

        # No errors
        if not result.errors:
            score += 1

        # Map to quality
        if score >= 5:
            return ContentQuality.EXCELLENT
        elif score >= 4:
            return ContentQuality.GOOD
        elif score >= 3:
            return ContentQuality.ACCEPTABLE
        elif score >= 2:
            return ContentQuality.POOR
        return ContentQuality.INVALID

    async def transform(
        self,
        content: str,
        source_modality: Modality,
        target_modality: Modality
    ) -> TransformResult:
        """Transform content from one modality to another."""
        result = TransformResult(
            source_modality=source_modality,
            target_modality=target_modality,
            original=content,
            transformed="",
            success=False
        )

        # Code to Markdown
        if source_modality == Modality.CODE and target_modality == Modality.MARKDOWN:
            parsed = await self.parsers[Modality.CODE].parse(content)
            md = f"# Code Analysis\n\n"
            md += f"**Language**: {parsed.get('language', 'unknown')}\n\n"
            md += f"## Metrics\n"
            for key, value in parsed.get('metrics', {}).items():
                md += f"- {key}: {value}\n"
            md += f"\n## Code\n```{parsed.get('language', '')}\n{content}\n```\n"
            result.transformed = md
            result.success = True
            result.confidence = 0.9

        # Data to Markdown
        elif source_modality == Modality.DATA and target_modality == Modality.MARKDOWN:
            parsed = await self.parsers[Modality.DATA].parse(content)
            md = f"# Data Summary\n\n"
            md += f"**Format**: {parsed.get('format', 'unknown')}\n\n"
            md += f"## Metrics\n"
            for key, value in parsed.get('metrics', {}).items():
                md += f"- {key}: {value}\n"
            md += f"\n## Data\n```json\n{json.dumps(parsed.get('content', {}), indent=2)[:2000]}\n```\n"
            result.transformed = md
            result.success = True
            result.confidence = 0.85

        # Text to Markdown
        elif source_modality == Modality.TEXT and target_modality == Modality.MARKDOWN:
            parsed = await self.parsers[Modality.TEXT].parse(content)
            lines = content.split('\n')
            md = "# Document\n\n"
            for line in lines:
                if line.strip():
                    md += f"{line}\n\n"
            result.transformed = md
            result.success = True
            result.confidence = 0.8

        # Data to Code (Python)
        elif source_modality == Modality.DATA and target_modality == Modality.CODE:
            parsed = await self.parsers[Modality.DATA].parse(content)
            code = "# Generated Python code from data\n\n"
            code += f"data = {repr(parsed.get('content', {}))}\n\n"
            code += "def process_data(data):\n"
            code += "    '''Process the loaded data.'''\n"
            code += "    # Add your processing logic here\n"
            code += "    return data\n"
            result.transformed = code
            result.success = True
            result.confidence = 0.75

        else:
            result.notes.append(f"Transformation from {source_modality.value} to {target_modality.value} not supported")

        return result

    async def integrate(
        self,
        contents: List[Tuple[str, Optional[Modality]]]
    ) -> IntegrationResult:
        """Integrate multiple pieces of content."""
        start_time = time.time()

        parsed_contents = []
        for content, hint in contents:
            parsed = await self.process(content, hint)
            parsed_contents.append(parsed)

        # Build unified view
        unified = {
            "items": [
                {
                    "id": p.id,
                    "modality": p.modality.value,
                    "quality": p.quality.name,
                    "summary": self._summarize(p.structured)
                }
                for p in parsed_contents
            ]
        }

        # Find relationships
        relationships = []
        for i, p1 in enumerate(parsed_contents):
            for j, p2 in enumerate(parsed_contents):
                if i < j:
                    rel = await self._find_relationship(p1, p2)
                    if rel:
                        relationships.append(rel)

        # Calculate overall confidence
        avg_confidence = sum(p.confidence for p in parsed_contents) / len(parsed_contents)

        return IntegrationResult(
            modalities_used=[p.modality for p in parsed_contents],
            unified_content=unified,
            relationships=relationships,
            confidence=avg_confidence,
            processing_time_ms=(time.time() - start_time) * 1000
        )

    def _summarize(self, structured: Dict[str, Any]) -> str:
        """Create a brief summary of structured content."""
        content_type = structured.get("type", "unknown")
        metrics = structured.get("metrics", {})

        if content_type == "code":
            return f"Code ({structured.get('language', 'unknown')}): {metrics.get('lines', 0)} lines"
        elif content_type == "data":
            return f"Data ({structured.get('format', 'unknown')}): {metrics.get('keys', 0)} keys"
        elif content_type == "text":
            return f"Text: {metrics.get('words', 0)} words"
        elif content_type == "markdown":
            return f"Markdown: {metrics.get('headers', 0)} headers"
        return f"{content_type}: processed"

    async def _find_relationship(
        self,
        p1: ParsedContent,
        p2: ParsedContent
    ) -> Optional[Dict[str, Any]]:
        """Find relationship between two parsed contents."""
        # Check for shared terms
        terms1 = set(str(p1.structured).lower().split())
        terms2 = set(str(p2.structured).lower().split())
        overlap = terms1 & terms2

        if len(overlap) > 10:
            return {
                "type": "similar_content",
                "source": p1.id,
                "target": p2.id,
                "shared_terms": len(overlap),
                "confidence": min(len(overlap) / 20, 1.0)
            }

        # Check for modality relationship
        if p1.modality == Modality.CODE and p2.modality == Modality.DATA:
            return {
                "type": "code_uses_data",
                "source": p1.id,
                "target": p2.id,
                "confidence": 0.6
            }

        return None

    async def save_state(self, filename: str = "multimodal_state.json") -> None:
        """Save processing state."""
        state = {
            "processing_count": len(self.processing_history),
            "modality_counts": defaultdict(int),
            "quality_counts": defaultdict(int)
        }

        for item in self.processing_history:
            state["modality_counts"][item.modality.value] += 1
            state["quality_counts"][item.quality.name] += 1

        state["modality_counts"] = dict(state["modality_counts"])
        state["quality_counts"] = dict(state["quality_counts"])

        filepath = self.data_dir / filename
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)

    def get_summary(self) -> Dict[str, Any]:
        """Get processing summary."""
        modality_counts = defaultdict(int)
        quality_counts = defaultdict(int)

        for item in self.processing_history:
            modality_counts[item.modality.value] += 1
            quality_counts[item.quality.name] += 1

        return {
            "total_processed": len(self.processing_history),
            "modality_distribution": dict(modality_counts),
            "quality_distribution": dict(quality_counts),
            "avg_processing_time_ms": (
                sum(p.parsing_time_ms for p in self.processing_history) / len(self.processing_history)
                if self.processing_history else 0
            )
        }


# Convenience instance
multimodal_processor = MultiModalProcessor()
