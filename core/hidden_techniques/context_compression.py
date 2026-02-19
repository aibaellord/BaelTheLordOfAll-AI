"""
Context Compression - Infinite Context Through Compression
============================================================

Advanced context compression for handling massive codebases.

"Compress the universe, retain the essence." — Ba'el
"""

import re
import ast
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("BAEL.HiddenTechniques.ContextCompression")


class CompressionLevel(Enum):
    """Compression aggressiveness levels."""
    NONE = 0           # No compression
    LIGHT = 1          # Remove comments only
    MODERATE = 2       # Remove comments + docstrings + blank lines
    AGGRESSIVE = 3     # + Simplify code structure
    EXTREME = 4        # + Extract only signatures and key logic
    SEMANTIC = 5       # + Semantic summarization


class ContentType(Enum):
    """Types of content for specialized compression."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"
    LOG = "log"
    CONFIG = "config"


@dataclass
class CompressionStats:
    """Statistics about compression."""
    original_chars: int = 0
    compressed_chars: int = 0
    original_lines: int = 0
    compressed_lines: int = 0
    compression_ratio: float = 0.0
    tokens_saved_estimate: int = 0


@dataclass
class CompressedContent:
    """Result of content compression."""
    content: str
    content_type: ContentType
    level: CompressionLevel
    stats: CompressionStats
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def summary(self) -> str:
        return f"Compressed {self.stats.compression_ratio:.1%} ({self.stats.original_chars} → {self.stats.compressed_chars} chars)"


class ContextCompressor:
    """
    Advanced context compression system.

    Reduces context size while preserving essential information
    for LLM understanding.
    """

    def __init__(self, default_level: CompressionLevel = CompressionLevel.MODERATE):
        self.default_level = default_level
        self._stats_history: List[CompressionStats] = []

    def compress(
        self,
        content: str,
        content_type: ContentType = None,
        level: CompressionLevel = None,
        preserve_patterns: List[str] = None,
    ) -> CompressedContent:
        """
        Compress content for context efficiency.

        Args:
            content: Content to compress
            content_type: Type of content (auto-detected if None)
            level: Compression level
            preserve_patterns: Regex patterns to preserve unchanged

        Returns:
            CompressedContent with compressed text and stats
        """
        if not content:
            return CompressedContent(
                content="",
                content_type=ContentType.TEXT,
                level=CompressionLevel.NONE,
                stats=CompressionStats(),
            )

        # Auto-detect content type
        if content_type is None:
            content_type = self._detect_content_type(content)

        level = level or self.default_level
        original_chars = len(content)
        original_lines = content.count('\n') + 1

        # Apply compression based on content type
        if content_type == ContentType.PYTHON:
            compressed = self._compress_python(content, level, preserve_patterns)
        elif content_type in (ContentType.JAVASCRIPT, ContentType.TYPESCRIPT):
            compressed = self._compress_javascript(content, level, preserve_patterns)
        elif content_type == ContentType.JSON:
            compressed = self._compress_json(content, level)
        elif content_type == ContentType.MARKDOWN:
            compressed = self._compress_markdown(content, level)
        elif content_type == ContentType.LOG:
            compressed = self._compress_logs(content, level)
        else:
            compressed = self._compress_text(content, level)

        # Calculate stats
        stats = CompressionStats(
            original_chars=original_chars,
            compressed_chars=len(compressed),
            original_lines=original_lines,
            compressed_lines=compressed.count('\n') + 1,
            compression_ratio=1 - (len(compressed) / original_chars) if original_chars > 0 else 0,
            tokens_saved_estimate=(original_chars - len(compressed)) // 4,
        )

        self._stats_history.append(stats)

        return CompressedContent(
            content=compressed,
            content_type=content_type,
            level=level,
            stats=stats,
        )

    def compress_file(
        self,
        file_path: Path,
        level: CompressionLevel = None,
    ) -> CompressedContent:
        """Compress a file's contents."""
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        content_type = self._detect_file_type(file_path)
        return self.compress(content, content_type, level)

    def compress_codebase(
        self,
        directory: Path,
        level: CompressionLevel = None,
        max_files: int = 100,
        extensions: List[str] = None,
    ) -> str:
        """
        Compress an entire codebase into a single context.

        Returns a compressed representation suitable for LLM context.
        """
        extensions = extensions or ['.py', '.js', '.ts', '.tsx', '.jsx', '.json', '.md']
        level = level or CompressionLevel.AGGRESSIVE

        files_content = []
        file_count = 0

        for ext in extensions:
            for file_path in directory.rglob(f'*{ext}'):
                if file_count >= max_files:
                    break

                # Skip common non-essential directories
                if any(skip in str(file_path) for skip in [
                    'node_modules', '.git', '__pycache__', 'venv', '.venv',
                    'dist', 'build', '.next', 'coverage'
                ]):
                    continue

                try:
                    result = self.compress_file(file_path, level)
                    if result.content.strip():
                        relative_path = file_path.relative_to(directory)
                        files_content.append(f"### {relative_path}\n{result.content}")
                        file_count += 1
                except Exception as e:
                    logger.debug(f"Failed to compress {file_path}: {e}")

        # Build combined context
        header = f"# Codebase Summary ({file_count} files)\n\n"
        return header + "\n\n".join(files_content)

    def _detect_content_type(self, content: str) -> ContentType:
        """Detect content type from content."""
        # Python indicators
        if re.search(r'^(import |from .+ import |def |class |async def )', content, re.MULTILINE):
            return ContentType.PYTHON

        # JavaScript/TypeScript indicators
        if re.search(r'^(import |export |const |let |var |function |class )', content, re.MULTILINE):
            if 'interface ' in content or ': ' in content and '=>' in content:
                return ContentType.TYPESCRIPT
            return ContentType.JAVASCRIPT

        # JSON
        content_stripped = content.strip()
        if content_stripped.startswith('{') or content_stripped.startswith('['):
            try:
                import json
                json.loads(content_stripped)
                return ContentType.JSON
            except Exception:
                pass

        # Markdown
        if re.search(r'^#{1,6} ', content, re.MULTILINE) or '```' in content:
            return ContentType.MARKDOWN

        # Log file
        if re.search(r'\d{4}-\d{2}-\d{2}.*\d{2}:\d{2}:\d{2}', content):
            return ContentType.LOG

        return ContentType.TEXT

    def _detect_file_type(self, path: Path) -> ContentType:
        """Detect content type from file extension."""
        ext_map = {
            '.py': ContentType.PYTHON,
            '.js': ContentType.JAVASCRIPT,
            '.jsx': ContentType.JAVASCRIPT,
            '.ts': ContentType.TYPESCRIPT,
            '.tsx': ContentType.TYPESCRIPT,
            '.json': ContentType.JSON,
            '.md': ContentType.MARKDOWN,
            '.markdown': ContentType.MARKDOWN,
            '.log': ContentType.LOG,
            '.yaml': ContentType.CONFIG,
            '.yml': ContentType.CONFIG,
            '.toml': ContentType.CONFIG,
            '.ini': ContentType.CONFIG,
        }
        return ext_map.get(path.suffix.lower(), ContentType.TEXT)

    def _compress_python(
        self,
        content: str,
        level: CompressionLevel,
        preserve_patterns: List[str] = None,
    ) -> str:
        """Compress Python code."""
        if level == CompressionLevel.NONE:
            return content

        result = content

        # Level 1+: Remove comments
        if level.value >= CompressionLevel.LIGHT.value:
            result = re.sub(r'#[^\n]*\n', '\n', result)

        # Level 2+: Remove docstrings and blank lines
        if level.value >= CompressionLevel.MODERATE.value:
            # Remove multi-line docstrings
            result = re.sub(r'"""[\s\S]*?"""', '"""..."""', result)
            result = re.sub(r"'''[\s\S]*?'''", "'''...'''", result)
            # Collapse multiple blank lines
            result = re.sub(r'\n{3,}', '\n\n', result)

        # Level 3+: Simplify structure
        if level.value >= CompressionLevel.AGGRESSIVE.value:
            # Remove all docstrings completely
            result = re.sub(r'"""[\s\S]*?"""', '', result)
            result = re.sub(r"'''[\s\S]*?'''", '', result)
            # Single blank line max
            result = re.sub(r'\n{2,}', '\n', result)
            # Remove trailing whitespace
            result = re.sub(r'[ \t]+$', '', result, flags=re.MULTILINE)

        # Level 4+: Extract only signatures
        if level.value >= CompressionLevel.EXTREME.value:
            result = self._extract_python_signatures(result)

        # Level 5: Semantic summary
        if level.value >= CompressionLevel.SEMANTIC.value:
            result = self._semantic_summarize_python(result)

        return result.strip()

    def _extract_python_signatures(self, content: str) -> str:
        """Extract only function/class signatures from Python code."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return content

        lines = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = ', '.join(ast.unparse(b) for b in node.bases)
                lines.append(f"class {node.name}({bases}): ...")

            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                args = ast.unparse(node.args)
                returns = ""
                if node.returns:
                    returns = f" -> {ast.unparse(node.returns)}"
                lines.append(f"{prefix} {node.name}({args}){returns}: ...")

        return '\n'.join(lines)

    def _semantic_summarize_python(self, content: str) -> str:
        """Create a semantic summary of Python code."""
        # Count elements
        class_count = len(re.findall(r'^class \w+', content, re.MULTILINE))
        func_count = len(re.findall(r'^(?:async )?def \w+', content, re.MULTILINE))

        # Find imports
        imports = re.findall(r'^(?:from .+ )?import .+$', content, re.MULTILINE)

        # Extract class names
        classes = re.findall(r'^class (\w+)', content, re.MULTILINE)

        # Extract function names (top-level only approximately)
        functions = re.findall(r'^def (\w+)', content, re.MULTILINE)

        summary = f"""# Code Summary
- Classes ({class_count}): {', '.join(classes[:10])}{'...' if len(classes) > 10 else ''}
- Functions ({func_count}): {', '.join(functions[:10])}{'...' if len(functions) > 10 else ''}
- Key imports: {', '.join(imports[:5])}"""

        return summary

    def _compress_javascript(
        self,
        content: str,
        level: CompressionLevel,
        preserve_patterns: List[str] = None,
    ) -> str:
        """Compress JavaScript/TypeScript code."""
        if level == CompressionLevel.NONE:
            return content

        result = content

        # Level 1+: Remove comments
        if level.value >= CompressionLevel.LIGHT.value:
            result = re.sub(r'//[^\n]*\n', '\n', result)
            result = re.sub(r'/\*[\s\S]*?\*/', '', result)

        # Level 2+: Collapse blank lines
        if level.value >= CompressionLevel.MODERATE.value:
            result = re.sub(r'\n{3,}', '\n\n', result)

        # Level 3+: More aggressive
        if level.value >= CompressionLevel.AGGRESSIVE.value:
            result = re.sub(r'\n{2,}', '\n', result)
            result = re.sub(r'[ \t]+$', '', result, flags=re.MULTILINE)

        # Level 4+: Extract only exports and function signatures
        if level.value >= CompressionLevel.EXTREME.value:
            result = self._extract_js_signatures(result)

        return result.strip()

    def _extract_js_signatures(self, content: str) -> str:
        """Extract function/class signatures from JS/TS."""
        lines = []

        # Extract exports
        exports = re.findall(r'^export (?:default )?(const|let|var|function|class|interface|type) (\w+)', content, re.MULTILINE)
        for kind, name in exports:
            lines.append(f"export {kind} {name}")

        # Extract functions
        functions = re.findall(r'^(?:export )?(?:async )?function (\w+)\([^)]*\)', content, re.MULTILINE)
        for func in functions:
            if f"function {func}" not in '\n'.join(lines):
                lines.append(f"function {func}(...)")

        # Extract classes
        classes = re.findall(r'^(?:export )?class (\w+)', content, re.MULTILINE)
        for cls in classes:
            if f"class {cls}" not in '\n'.join(lines):
                lines.append(f"class {cls}")

        return '\n'.join(lines)

    def _compress_json(self, content: str, level: CompressionLevel) -> str:
        """Compress JSON content."""
        if level == CompressionLevel.NONE:
            return content

        try:
            import json
            data = json.loads(content)

            if level.value >= CompressionLevel.AGGRESSIVE.value:
                # Minify
                return json.dumps(data, separators=(',', ':'))
            else:
                # Compact but readable
                return json.dumps(data, indent=2)
        except Exception:
            return content

    def _compress_markdown(self, content: str, level: CompressionLevel) -> str:
        """Compress Markdown content."""
        if level == CompressionLevel.NONE:
            return content

        result = content

        # Level 2+: Collapse multiple blank lines
        if level.value >= CompressionLevel.MODERATE.value:
            result = re.sub(r'\n{3,}', '\n\n', result)

        # Level 3+: Remove code blocks content, keep headers
        if level.value >= CompressionLevel.AGGRESSIVE.value:
            result = re.sub(r'```[\s\S]*?```', '```...```', result)

        # Level 4+: Keep only headers
        if level.value >= CompressionLevel.EXTREME.value:
            headers = re.findall(r'^#{1,6} .+$', result, re.MULTILINE)
            result = '\n'.join(headers)

        return result.strip()

    def _compress_logs(self, content: str, level: CompressionLevel) -> str:
        """Compress log content."""
        if level == CompressionLevel.NONE:
            return content

        lines = content.split('\n')

        # Level 2+: Remove DEBUG logs
        if level.value >= CompressionLevel.MODERATE.value:
            lines = [l for l in lines if 'DEBUG' not in l.upper()]

        # Level 3+: Remove INFO logs, keep only WARN/ERROR
        if level.value >= CompressionLevel.AGGRESSIVE.value:
            lines = [l for l in lines if any(x in l.upper() for x in ['WARN', 'ERROR', 'CRITICAL', 'FATAL'])]

        # Level 4+: Deduplicate similar errors
        if level.value >= CompressionLevel.EXTREME.value:
            seen = set()
            unique_lines = []
            for line in lines:
                # Extract error type/message for deduplication
                key = re.sub(r'\d+', '#', line)[:100]
                if key not in seen:
                    seen.add(key)
                    unique_lines.append(line)
            lines = unique_lines

        return '\n'.join(lines)

    def _compress_text(self, content: str, level: CompressionLevel) -> str:
        """Compress generic text content."""
        if level == CompressionLevel.NONE:
            return content

        result = content

        # Level 2+: Collapse whitespace
        if level.value >= CompressionLevel.MODERATE.value:
            result = re.sub(r'\n{3,}', '\n\n', result)
            result = re.sub(r' {2,}', ' ', result)

        # Level 3+: Single line mode
        if level.value >= CompressionLevel.AGGRESSIVE.value:
            result = re.sub(r'\n{2,}', '\n', result)

        return result.strip()

    def get_cumulative_stats(self) -> Dict[str, Any]:
        """Get cumulative compression statistics."""
        if not self._stats_history:
            return {}

        total_original = sum(s.original_chars for s in self._stats_history)
        total_compressed = sum(s.compressed_chars for s in self._stats_history)

        return {
            "compressions_performed": len(self._stats_history),
            "total_original_chars": total_original,
            "total_compressed_chars": total_compressed,
            "total_savings": total_original - total_compressed,
            "average_ratio": sum(s.compression_ratio for s in self._stats_history) / len(self._stats_history),
            "total_tokens_saved": sum(s.tokens_saved_estimate for s in self._stats_history),
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_compressor = ContextCompressor()


def compress_context(content: str, level: CompressionLevel = CompressionLevel.MODERATE) -> str:
    """Quick function to compress context."""
    result = _compressor.compress(content, level=level)
    return result.content


def compress_code(code: str, language: str = "python") -> str:
    """Compress code for context."""
    content_type = {
        "python": ContentType.PYTHON,
        "javascript": ContentType.JAVASCRIPT,
        "typescript": ContentType.TYPESCRIPT,
    }.get(language.lower(), ContentType.TEXT)

    result = _compressor.compress(code, content_type, CompressionLevel.AGGRESSIVE)
    return result.content


def compress_codebase(directory: Path, max_files: int = 50) -> str:
    """Compress an entire codebase into context."""
    return _compressor.compress_codebase(directory, CompressionLevel.AGGRESSIVE, max_files)
