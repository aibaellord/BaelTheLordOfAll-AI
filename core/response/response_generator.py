#!/usr/bin/env python3
"""
BAEL - Response Generator
Advanced response generation for AI agents.

Features:
- Template-based responses
- Dynamic response building
- Multi-format output
- Response streaming
- Context-aware responses
- Response validation
- Response caching
- Response metrics
"""

import asyncio
import copy
import hashlib
import json
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, AsyncIterator, Awaitable, Callable, Dict, Generic,
                    Iterator, List, Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ResponseFormat(Enum):
    """Response format."""
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    XML = "xml"
    YAML = "yaml"


class ResponseType(Enum):
    """Response type."""
    ANSWER = "answer"
    CLARIFICATION = "clarification"
    ERROR = "error"
    PROGRESS = "progress"
    COMPLETION = "completion"
    PARTIAL = "partial"


class ToneStyle(Enum):
    """Response tone."""
    FORMAL = "formal"
    CASUAL = "casual"
    TECHNICAL = "technical"
    FRIENDLY = "friendly"
    CONCISE = "concise"


class ResponseStatus(Enum):
    """Response status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETE = "complete"
    FAILED = "failed"
    CACHED = "cached"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ResponseTemplate:
    """Response template."""
    template_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    template: str = ""
    format: ResponseFormat = ResponseFormat.TEXT
    variables: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResponseConfig:
    """Response configuration."""
    format: ResponseFormat = ResponseFormat.TEXT
    response_type: ResponseType = ResponseType.ANSWER
    tone: ToneStyle = ToneStyle.FRIENDLY
    max_length: int = 0  # 0 = no limit
    include_metadata: bool = False
    stream: bool = False


@dataclass
class Response:
    """Generated response."""
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    format: ResponseFormat = ResponseFormat.TEXT
    response_type: ResponseType = ResponseType.ANSWER
    status: ResponseStatus = ResponseStatus.COMPLETE
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    generation_time: float = 0.0


@dataclass
class ResponsePart:
    """Part of a streaming response."""
    content: str = ""
    index: int = 0
    is_final: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResponseMetrics:
    """Response metrics."""
    total_responses: int = 0
    avg_generation_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    error_count: int = 0


# =============================================================================
# TEMPLATE ENGINE
# =============================================================================

class TemplateEngine:
    """Template engine for responses."""

    def __init__(self):
        self._templates: Dict[str, ResponseTemplate] = {}

    def register_template(
        self,
        name: str,
        template: str,
        format: ResponseFormat = ResponseFormat.TEXT
    ) -> ResponseTemplate:
        """Register template."""
        # Extract variables
        variables = re.findall(r'\{(\w+)\}', template)

        tmpl = ResponseTemplate(
            name=name,
            template=template,
            format=format,
            variables=variables
        )

        self._templates[name] = tmpl
        return tmpl

    def get_template(self, name: str) -> Optional[ResponseTemplate]:
        """Get template."""
        return self._templates.get(name)

    def render(
        self,
        template_name: str,
        variables: Dict[str, Any]
    ) -> str:
        """Render template with variables."""
        template = self._templates.get(template_name)

        if not template:
            raise ValueError(f"Template not found: {template_name}")

        content = template.template

        for var, value in variables.items():
            content = content.replace(f"{{{var}}}", str(value))

        return content

    def render_string(
        self,
        template_str: str,
        variables: Dict[str, Any]
    ) -> str:
        """Render template string."""
        content = template_str

        for var, value in variables.items():
            content = content.replace(f"{{{var}}}", str(value))

        return content


# =============================================================================
# RESPONSE BUILDER
# =============================================================================

class ResponseBuilder:
    """Builder for responses."""

    def __init__(self):
        self._content_parts: List[str] = []
        self._config = ResponseConfig()
        self._metadata: Dict[str, Any] = {}

    def text(self, text: str) -> "ResponseBuilder":
        """Add text."""
        self._content_parts.append(text)
        return self

    def line(self, text: str = "") -> "ResponseBuilder":
        """Add line."""
        self._content_parts.append(text + "\n")
        return self

    def paragraph(self, text: str) -> "ResponseBuilder":
        """Add paragraph."""
        self._content_parts.append(text + "\n\n")
        return self

    def heading(self, text: str, level: int = 1) -> "ResponseBuilder":
        """Add heading (markdown)."""
        prefix = "#" * level
        self._content_parts.append(f"{prefix} {text}\n\n")
        self._config.format = ResponseFormat.MARKDOWN
        return self

    def bullet(self, text: str) -> "ResponseBuilder":
        """Add bullet point."""
        self._content_parts.append(f"• {text}\n")
        return self

    def numbered(self, number: int, text: str) -> "ResponseBuilder":
        """Add numbered item."""
        self._content_parts.append(f"{number}. {text}\n")
        return self

    def code(
        self,
        code: str,
        language: str = ""
    ) -> "ResponseBuilder":
        """Add code block."""
        self._content_parts.append(f"```{language}\n{code}\n```\n")
        self._config.format = ResponseFormat.MARKDOWN
        return self

    def json_block(self, data: Any) -> "ResponseBuilder":
        """Add JSON block."""
        json_str = json.dumps(data, indent=2)
        return self.code(json_str, "json")

    def table(
        self,
        headers: List[str],
        rows: List[List[str]]
    ) -> "ResponseBuilder":
        """Add table (markdown)."""
        header_row = "| " + " | ".join(headers) + " |"
        separator = "| " + " | ".join(["---"] * len(headers)) + " |"

        self._content_parts.append(header_row + "\n")
        self._content_parts.append(separator + "\n")

        for row in rows:
            row_str = "| " + " | ".join(row) + " |"
            self._content_parts.append(row_str + "\n")

        self._content_parts.append("\n")
        self._config.format = ResponseFormat.MARKDOWN
        return self

    def format(self, format: ResponseFormat) -> "ResponseBuilder":
        """Set format."""
        self._config.format = format
        return self

    def type(self, response_type: ResponseType) -> "ResponseBuilder":
        """Set type."""
        self._config.response_type = response_type
        return self

    def tone(self, tone: ToneStyle) -> "ResponseBuilder":
        """Set tone."""
        self._config.tone = tone
        return self

    def metadata(self, key: str, value: Any) -> "ResponseBuilder":
        """Add metadata."""
        self._metadata[key] = value
        return self

    def build(self) -> Response:
        """Build response."""
        content = "".join(self._content_parts)

        return Response(
            content=content,
            format=self._config.format,
            response_type=self._config.response_type,
            metadata=self._metadata
        )


# =============================================================================
# FORMAT CONVERTER
# =============================================================================

class FormatConverter:
    """Convert between response formats."""

    def to_json(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Convert to JSON."""
        data = {
            "content": content,
            "metadata": metadata or {}
        }
        return json.dumps(data, indent=2)

    def to_markdown(self, content: str, title: Optional[str] = None) -> str:
        """Convert to Markdown."""
        if title:
            return f"# {title}\n\n{content}"
        return content

    def to_html(self, content: str, title: Optional[str] = None) -> str:
        """Convert to HTML."""
        # Simple conversion
        html_content = content.replace("\n", "<br>\n")

        if title:
            return f"<html><head><title>{title}</title></head><body><h1>{title}</h1><p>{html_content}</p></body></html>"
        return f"<html><body><p>{html_content}</p></body></html>"

    def to_xml(self, content: str, root: str = "response") -> str:
        """Convert to XML."""
        escaped = (content
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))
        return f"<?xml version=\"1.0\"?><{root}>{escaped}</{root}>"

    def convert(
        self,
        content: str,
        from_format: ResponseFormat,
        to_format: ResponseFormat
    ) -> str:
        """Convert between formats."""
        if from_format == to_format:
            return content

        if to_format == ResponseFormat.JSON:
            return self.to_json(content)
        elif to_format == ResponseFormat.MARKDOWN:
            return self.to_markdown(content)
        elif to_format == ResponseFormat.HTML:
            return self.to_html(content)
        elif to_format == ResponseFormat.XML:
            return self.to_xml(content)

        return content


# =============================================================================
# RESPONSE CACHE
# =============================================================================

class ResponseCache:
    """Cache for responses."""

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: int = 3600
    ):
        self._cache: Dict[str, Tuple[Response, datetime]] = {}
        self._max_size = max_size
        self._ttl = timedelta(seconds=ttl_seconds)
        self._hits = 0
        self._misses = 0

    def _make_key(self, query: str, config: ResponseConfig) -> str:
        """Make cache key."""
        key_str = f"{query}:{config.format.value}:{config.tone.value}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(
        self,
        query: str,
        config: ResponseConfig
    ) -> Optional[Response]:
        """Get cached response."""
        key = self._make_key(query, config)

        if key in self._cache:
            response, expires = self._cache[key]

            if datetime.now() < expires:
                self._hits += 1
                response.status = ResponseStatus.CACHED
                return response
            else:
                del self._cache[key]

        self._misses += 1
        return None

    def set(
        self,
        query: str,
        config: ResponseConfig,
        response: Response
    ) -> None:
        """Cache response."""
        if len(self._cache) >= self._max_size:
            # Remove oldest entry
            oldest = min(self._cache.items(), key=lambda x: x[1][1])
            del self._cache[oldest[0]]

        key = self._make_key(query, config)
        expires = datetime.now() + self._ttl
        self._cache[key] = (response, expires)

    def clear(self) -> int:
        """Clear cache."""
        count = len(self._cache)
        self._cache.clear()
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate
        }


# =============================================================================
# RESPONSE VALIDATOR
# =============================================================================

class ResponseValidator:
    """Validate responses."""

    def __init__(self):
        self._validators: List[Callable[[Response], bool]] = []

    def add_validator(
        self,
        validator: Callable[[Response], bool]
    ) -> None:
        """Add validator."""
        self._validators.append(validator)

    def validate(self, response: Response) -> Tuple[bool, List[str]]:
        """Validate response."""
        errors = []

        # Check content
        if not response.content:
            errors.append("Empty content")

        # Check length
        if len(response.content) > 100000:
            errors.append("Content too long")

        # Run custom validators
        for validator in self._validators:
            try:
                if not validator(response):
                    errors.append("Custom validation failed")
            except Exception as e:
                errors.append(f"Validator error: {str(e)}")

        return len(errors) == 0, errors

    def validate_json(self, response: Response) -> bool:
        """Validate JSON response."""
        if response.format != ResponseFormat.JSON:
            return True

        try:
            json.loads(response.content)
            return True
        except json.JSONDecodeError:
            return False


# =============================================================================
# RESPONSE STREAM
# =============================================================================

class ResponseStream:
    """Stream responses."""

    def __init__(self):
        self._buffer: List[ResponsePart] = []
        self._complete = False

    async def write(self, content: str, is_final: bool = False) -> None:
        """Write to stream."""
        part = ResponsePart(
            content=content,
            index=len(self._buffer),
            is_final=is_final
        )

        self._buffer.append(part)
        self._complete = is_final

    async def stream(self) -> AsyncIterator[ResponsePart]:
        """Stream response parts."""
        for part in self._buffer:
            yield part

    def get_full_content(self) -> str:
        """Get full content."""
        return "".join(p.content for p in self._buffer)

    def is_complete(self) -> bool:
        """Check if complete."""
        return self._complete


# =============================================================================
# RESPONSE GENERATOR
# =============================================================================

class ResponseGenerator:
    """
    Response Generator for BAEL.

    Advanced response generation.
    """

    def __init__(self):
        self._template_engine = TemplateEngine()
        self._format_converter = FormatConverter()
        self._cache = ResponseCache()
        self._validator = ResponseValidator()
        self._response_history: List[Response] = []
        self._metrics = ResponseMetrics()

    # -------------------------------------------------------------------------
    # TEMPLATES
    # -------------------------------------------------------------------------

    def register_template(
        self,
        name: str,
        template: str,
        format: str = "text"
    ) -> ResponseTemplate:
        """Register template."""
        format_map = {
            "text": ResponseFormat.TEXT,
            "json": ResponseFormat.JSON,
            "markdown": ResponseFormat.MARKDOWN,
            "html": ResponseFormat.HTML,
            "xml": ResponseFormat.XML
        }

        return self._template_engine.register_template(
            name,
            template,
            format_map.get(format.lower(), ResponseFormat.TEXT)
        )

    def render_template(
        self,
        template_name: str,
        variables: Dict[str, Any]
    ) -> Response:
        """Render template."""
        start_time = time.time()

        template = self._template_engine.get_template(template_name)

        if not template:
            return Response(
                content="",
                status=ResponseStatus.FAILED,
                metadata={"error": f"Template not found: {template_name}"}
            )

        content = self._template_engine.render(template_name, variables)

        response = Response(
            content=content,
            format=template.format,
            generation_time=time.time() - start_time
        )

        self._record_response(response)
        return response

    # -------------------------------------------------------------------------
    # BUILDER
    # -------------------------------------------------------------------------

    def builder(self) -> ResponseBuilder:
        """Get response builder."""
        return ResponseBuilder()

    # -------------------------------------------------------------------------
    # GENERATION
    # -------------------------------------------------------------------------

    def generate(
        self,
        content: str,
        format: str = "text",
        response_type: str = "answer",
        use_cache: bool = True
    ) -> Response:
        """Generate response."""
        start_time = time.time()

        format_map = {
            "text": ResponseFormat.TEXT,
            "json": ResponseFormat.JSON,
            "markdown": ResponseFormat.MARKDOWN,
            "html": ResponseFormat.HTML,
            "xml": ResponseFormat.XML
        }

        type_map = {
            "answer": ResponseType.ANSWER,
            "clarification": ResponseType.CLARIFICATION,
            "error": ResponseType.ERROR,
            "progress": ResponseType.PROGRESS,
            "completion": ResponseType.COMPLETION
        }

        config = ResponseConfig(
            format=format_map.get(format.lower(), ResponseFormat.TEXT),
            response_type=type_map.get(response_type.lower(), ResponseType.ANSWER)
        )

        # Check cache
        if use_cache:
            cached = self._cache.get(content, config)
            if cached:
                return cached

        response = Response(
            content=content,
            format=config.format,
            response_type=config.response_type,
            generation_time=time.time() - start_time
        )

        # Cache response
        if use_cache:
            self._cache.set(content, config, response)

        self._record_response(response)
        return response

    def generate_json(self, data: Any) -> Response:
        """Generate JSON response."""
        content = json.dumps(data, indent=2, default=str)
        return self.generate(content, format="json")

    def generate_error(
        self,
        error: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Response:
        """Generate error response."""
        builder = self.builder()
        builder.text(f"Error: {error}")

        if details:
            builder.line()
            builder.json_block(details)

        response = builder.type(ResponseType.ERROR).build()
        self._record_response(response)
        return response

    def generate_progress(
        self,
        message: str,
        progress: float,
        total: Optional[float] = None
    ) -> Response:
        """Generate progress response."""
        builder = self.builder()
        builder.text(message)

        if total:
            percent = (progress / total) * 100
            builder.line(f" [{progress}/{total}] {percent:.1f}%")
        else:
            builder.line(f" {progress:.1f}%")

        response = builder.type(ResponseType.PROGRESS).build()
        self._record_response(response)
        return response

    # -------------------------------------------------------------------------
    # FORMAT CONVERSION
    # -------------------------------------------------------------------------

    def convert_format(
        self,
        response: Response,
        to_format: str
    ) -> Response:
        """Convert response format."""
        format_map = {
            "text": ResponseFormat.TEXT,
            "json": ResponseFormat.JSON,
            "markdown": ResponseFormat.MARKDOWN,
            "html": ResponseFormat.HTML,
            "xml": ResponseFormat.XML
        }

        target_format = format_map.get(to_format.lower(), ResponseFormat.TEXT)

        converted_content = self._format_converter.convert(
            response.content,
            response.format,
            target_format
        )

        return Response(
            content=converted_content,
            format=target_format,
            response_type=response.response_type,
            metadata=response.metadata
        )

    # -------------------------------------------------------------------------
    # STREAMING
    # -------------------------------------------------------------------------

    async def stream_generate(
        self,
        content: str,
        chunk_size: int = 50
    ) -> AsyncIterator[ResponsePart]:
        """Generate streaming response."""
        stream = ResponseStream()

        chunks = [
            content[i:i+chunk_size]
            for i in range(0, len(content), chunk_size)
        ]

        for i, chunk in enumerate(chunks):
            is_final = i == len(chunks) - 1
            await stream.write(chunk, is_final)

            async for part in stream.stream():
                if part.index == i:
                    yield part
                    break

            await asyncio.sleep(0.01)  # Simulate streaming delay

    # -------------------------------------------------------------------------
    # VALIDATION
    # -------------------------------------------------------------------------

    def validate(self, response: Response) -> Tuple[bool, List[str]]:
        """Validate response."""
        return self._validator.validate(response)

    def add_validator(
        self,
        validator: Callable[[Response], bool]
    ) -> None:
        """Add custom validator."""
        self._validator.add_validator(validator)

    # -------------------------------------------------------------------------
    # CACHING
    # -------------------------------------------------------------------------

    def clear_cache(self) -> int:
        """Clear response cache."""
        return self._cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._cache.get_stats()

    # -------------------------------------------------------------------------
    # METRICS
    # -------------------------------------------------------------------------

    def _record_response(self, response: Response) -> None:
        """Record response metrics."""
        self._response_history.append(response)
        self._metrics.total_responses += 1

        if response.status == ResponseStatus.FAILED:
            self._metrics.error_count += 1

        # Update average generation time
        n = self._metrics.total_responses
        old_avg = self._metrics.avg_generation_time
        self._metrics.avg_generation_time = (
            (old_avg * (n - 1) + response.generation_time) / n
        )

    def get_metrics(self) -> ResponseMetrics:
        """Get response metrics."""
        cache_stats = self._cache.get_stats()
        self._metrics.cache_hits = cache_stats["hits"]
        self._metrics.cache_misses = cache_stats["misses"]
        return self._metrics

    def get_history(self, limit: int = 100) -> List[Response]:
        """Get response history."""
        return self._response_history[-limit:]


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Response Generator."""
    print("=" * 70)
    print("BAEL - RESPONSE GENERATOR DEMO")
    print("Advanced Response Generation")
    print("=" * 70)
    print()

    generator = ResponseGenerator()

    # 1. Simple Response
    print("1. SIMPLE RESPONSE:")
    print("-" * 40)

    response = generator.generate(
        "Hello! I'm BAEL, your AI assistant.",
        format="text"
    )

    print(f"   Content: {response.content}")
    print(f"   Format: {response.format.value}")
    print()

    # 2. Response Builder
    print("2. RESPONSE BUILDER:")
    print("-" * 40)

    response = (generator.builder()
        .heading("Welcome to BAEL")
        .paragraph("This is an advanced AI agent system.")
        .bullet("Multi-agent coordination")
        .bullet("Advanced reasoning")
        .bullet("Goal management")
        .build())

    print(f"   {response.content}")
    print()

    # 3. JSON Response
    print("3. JSON RESPONSE:")
    print("-" * 40)

    response = generator.generate_json({
        "status": "success",
        "data": {
            "agents": 5,
            "tasks_completed": 42
        }
    })

    print(f"   {response.content}")
    print()

    # 4. Template-Based Response
    print("4. TEMPLATE RESPONSE:")
    print("-" * 40)

    generator.register_template(
        "greeting",
        "Hello {name}! Welcome to {system}. You have {count} messages.",
        format="text"
    )

    response = generator.render_template("greeting", {
        "name": "User",
        "system": "BAEL",
        "count": 3
    })

    print(f"   {response.content}")
    print()

    # 5. Error Response
    print("5. ERROR RESPONSE:")
    print("-" * 40)

    response = generator.generate_error(
        "Task execution failed",
        {"task_id": "123", "reason": "Timeout"}
    )

    print(f"   {response.content}")
    print()

    # 6. Progress Response
    print("6. PROGRESS RESPONSE:")
    print("-" * 40)

    response = generator.generate_progress(
        "Processing files",
        progress=75,
        total=100
    )

    print(f"   {response.content}")
    print()

    # 7. Table in Response
    print("7. TABLE RESPONSE:")
    print("-" * 40)

    response = (generator.builder()
        .heading("Agent Status", level=2)
        .table(
            ["Agent", "Status", "Tasks"],
            [
                ["Agent-1", "Active", "5"],
                ["Agent-2", "Idle", "0"],
                ["Agent-3", "Busy", "3"]
            ]
        )
        .build())

    print(response.content)
    print()

    # 8. Code Block
    print("8. CODE BLOCK:")
    print("-" * 40)

    response = (generator.builder()
        .text("Here's an example:")
        .line()
        .code("def hello():\n    print('Hello, BAEL!')", "python")
        .build())

    print(response.content)
    print()

    # 9. Format Conversion
    print("9. FORMAT CONVERSION:")
    print("-" * 40)

    text_response = generator.generate("Hello, World!", format="text")
    html_response = generator.convert_format(text_response, "html")

    print(f"   Original: {text_response.content}")
    print(f"   HTML: {html_response.content[:50]}...")
    print()

    # 10. Streaming Response
    print("10. STREAMING RESPONSE:")
    print("-" * 40)

    content = "This is a streaming response that arrives in chunks."

    print("   Streaming: ", end="")
    async for part in generator.stream_generate(content, chunk_size=10):
        print(part.content, end="", flush=True)
        await asyncio.sleep(0.05)
    print()
    print()

    # 11. Response Caching
    print("11. RESPONSE CACHING:")
    print("-" * 40)

    # First request
    response1 = generator.generate("Cached content test", use_cache=True)

    # Second request (should be cached)
    response2 = generator.generate("Cached content test", use_cache=True)

    cache_stats = generator.get_cache_stats()

    print(f"   First response status: {response1.status.value}")
    print(f"   Second response status: {response2.status.value}")
    print(f"   Cache hits: {cache_stats['hits']}")
    print()

    # 12. Response Validation
    print("12. RESPONSE VALIDATION:")
    print("-" * 40)

    valid_response = generator.generate("Valid content")
    is_valid, errors = generator.validate(valid_response)

    print(f"   Valid: {is_valid}")
    print(f"   Errors: {errors}")
    print()

    # 13. Custom Validator
    print("13. CUSTOM VALIDATOR:")
    print("-" * 40)

    generator.add_validator(lambda r: len(r.content) < 1000)

    short_response = generator.generate("Short")
    is_valid, _ = generator.validate(short_response)

    print(f"   Short response valid: {is_valid}")
    print()

    # 14. Response Metrics
    print("14. RESPONSE METRICS:")
    print("-" * 40)

    metrics = generator.get_metrics()

    print(f"   Total responses: {metrics.total_responses}")
    print(f"   Avg generation time: {metrics.avg_generation_time:.6f}s")
    print(f"   Cache hits: {metrics.cache_hits}")
    print(f"   Error count: {metrics.error_count}")
    print()

    # 15. Response History
    print("15. RESPONSE HISTORY:")
    print("-" * 40)

    history = generator.get_history(limit=5)

    print(f"   Recent responses: {len(history)}")
    for r in history[:3]:
        print(f"     - {r.content[:30]}... ({r.format.value})")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Response Generator Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
