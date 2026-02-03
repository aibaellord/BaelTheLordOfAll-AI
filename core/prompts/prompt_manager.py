#!/usr/bin/env python3
"""
BAEL - Prompt Manager
Advanced prompt engineering and template management for AI/LLM interactions.

Features:
- Prompt templates with variables
- Template inheritance
- Context injection
- Few-shot examples
- Chain-of-thought prompts
- Role-based prompting
- Prompt optimization
- Version management
- Token counting
- Prompt validation
- Output parsing
"""

import asyncio
import json
import logging
import re
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Pattern, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class PromptRole(Enum):
    """Prompt roles."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class PromptStyle(Enum):
    """Prompt styles."""
    DIRECT = "direct"
    INSTRUCTION = "instruction"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    FEW_SHOT = "few_shot"
    SOCRATIC = "socratic"
    PERSONA = "persona"


class OutputFormat(Enum):
    """Output formats."""
    TEXT = "text"
    JSON = "json"
    XML = "xml"
    MARKDOWN = "markdown"
    CODE = "code"
    LIST = "list"
    TABLE = "table"


class ValidationLevel(Enum):
    """Validation levels."""
    NONE = "none"
    BASIC = "basic"
    STRICT = "strict"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class PromptVariable:
    """Prompt variable definition."""
    name: str
    description: str = ""
    required: bool = True
    default: Optional[Any] = None
    validator: Optional[Callable[[Any], bool]] = None
    transformer: Optional[Callable[[Any], str]] = None


@dataclass
class PromptMessage:
    """Single prompt message."""
    role: PromptRole
    content: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FewShotExample:
    """Few-shot learning example."""
    input: str
    output: str
    explanation: Optional[str] = None


@dataclass
class PromptTemplate:
    """Prompt template definition."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    template: str = ""
    variables: List[PromptVariable] = field(default_factory=list)
    style: PromptStyle = PromptStyle.DIRECT
    output_format: OutputFormat = OutputFormat.TEXT
    examples: List[FewShotExample] = field(default_factory=list)
    parent_id: Optional[str] = None
    system_prompt: Optional[str] = None
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PromptResult:
    """Rendered prompt result."""
    messages: List[PromptMessage]
    template_id: str
    variables_used: Dict[str, Any]
    token_count: int = 0
    warnings: List[str] = field(default_factory=list)


@dataclass
class ParsedOutput:
    """Parsed LLM output."""
    raw: str
    parsed: Any = None
    format: OutputFormat = OutputFormat.TEXT
    success: bool = True
    errors: List[str] = field(default_factory=list)


@dataclass
class PromptMetrics:
    """Prompt usage metrics."""
    template_id: str
    render_count: int = 0
    avg_token_count: float = 0.0
    last_used: Optional[datetime] = None
    success_rate: float = 1.0


# =============================================================================
# TOKEN COUNTER
# =============================================================================

class TokenCounter:
    """Estimate token counts."""

    # Approximate tokens per character for different models
    TOKENS_PER_CHAR = {
        "gpt-4": 0.25,
        "gpt-3.5-turbo": 0.25,
        "claude": 0.28,
        "default": 0.25
    }

    def __init__(self, model: str = "default"):
        self.model = model
        self.ratio = self.TOKENS_PER_CHAR.get(model, self.TOKENS_PER_CHAR["default"])

    def count(self, text: str) -> int:
        """Count tokens in text (approximate)."""
        # Simple estimation: split on whitespace and punctuation
        # For production, use tiktoken or model-specific tokenizer
        words = re.findall(r'\b\w+\b|[^\w\s]', text)

        # Estimate: 1 word ≈ 1.3 tokens on average
        return int(len(words) * 1.3)

    def count_messages(self, messages: List[PromptMessage]) -> int:
        """Count tokens in messages."""
        total = 0

        for msg in messages:
            # Message overhead
            total += 4  # role, content markers
            total += self.count(msg.content)
            if msg.name:
                total += self.count(msg.name) + 1

        return total


# =============================================================================
# TEMPLATE RENDERER
# =============================================================================

class TemplateRenderer:
    """Render prompt templates."""

    VARIABLE_PATTERN = re.compile(r'\{\{(\w+)(?:\|([^}]+))?\}\}')
    BLOCK_PATTERN = re.compile(r'\{%\s*(\w+)\s+(\w+)\s*%\}(.*?)\{%\s*end\1\s*%\}', re.DOTALL)

    def render(
        self,
        template: str,
        variables: Dict[str, Any],
        var_defs: Optional[List[PromptVariable]] = None
    ) -> Tuple[str, List[str]]:
        """Render template with variables."""
        warnings = []
        result = template

        # Build variable lookup
        var_lookup = {}
        if var_defs:
            for v in var_defs:
                var_lookup[v.name] = v

        # Process blocks first (if/for)
        result = self._process_blocks(result, variables)

        # Replace variables
        def replace_var(match):
            name = match.group(1)
            default = match.group(2)

            if name in variables:
                value = variables[name]

                # Apply transformer if defined
                if name in var_lookup and var_lookup[name].transformer:
                    value = var_lookup[name].transformer(value)

                return str(value)
            elif default is not None:
                return default
            elif name in var_lookup and var_lookup[name].default is not None:
                return str(var_lookup[name].default)
            else:
                warnings.append(f"Variable '{name}' not provided")
                return f"{{{{name}}}}"

        result = self.VARIABLE_PATTERN.sub(replace_var, result)

        return result, warnings

    def _process_blocks(self, template: str, variables: Dict[str, Any]) -> str:
        """Process conditional and loop blocks."""
        result = template

        # Process if blocks
        if_pattern = re.compile(r'\{%\s*if\s+(\w+)\s*%\}(.*?)\{%\s*endif\s*%\}', re.DOTALL)

        def replace_if(match):
            var_name = match.group(1)
            content = match.group(2)

            if variables.get(var_name):
                return content
            return ""

        result = if_pattern.sub(replace_if, result)

        # Process for loops
        for_pattern = re.compile(r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}(.*?)\{%\s*endfor\s*%\}', re.DOTALL)

        def replace_for(match):
            item_name = match.group(1)
            list_name = match.group(2)
            content = match.group(3)

            items = variables.get(list_name, [])
            if not isinstance(items, (list, tuple)):
                return ""

            parts = []
            for item in items:
                item_vars = variables.copy()
                item_vars[item_name] = item
                rendered, _ = self.render(content, item_vars)
                parts.append(rendered)

            return "".join(parts)

        result = for_pattern.sub(replace_for, result)

        return result

    def extract_variables(self, template: str) -> List[str]:
        """Extract variable names from template."""
        matches = self.VARIABLE_PATTERN.findall(template)
        return list(set(m[0] for m in matches))


# =============================================================================
# OUTPUT PARSER
# =============================================================================

class OutputParser:
    """Parse LLM outputs."""

    def parse(self, output: str, format: OutputFormat) -> ParsedOutput:
        """Parse output according to format."""
        result = ParsedOutput(raw=output, format=format)

        try:
            if format == OutputFormat.JSON:
                result.parsed = self._parse_json(output)
            elif format == OutputFormat.XML:
                result.parsed = self._parse_xml(output)
            elif format == OutputFormat.LIST:
                result.parsed = self._parse_list(output)
            elif format == OutputFormat.CODE:
                result.parsed = self._parse_code(output)
            elif format == OutputFormat.TABLE:
                result.parsed = self._parse_table(output)
            else:
                result.parsed = output.strip()

            result.success = True

        except Exception as e:
            result.success = False
            result.errors.append(str(e))

        return result

    def _parse_json(self, output: str) -> Any:
        """Parse JSON from output."""
        # Try to find JSON in output
        json_match = re.search(r'```json\s*(.*?)\s*```', output, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))

        # Try direct parse
        json_match = re.search(r'\{.*\}|\[.*\]', output, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))

        return json.loads(output)

    def _parse_xml(self, output: str) -> Dict[str, Any]:
        """Parse XML from output (simplified)."""
        result = {}

        tag_pattern = re.compile(r'<(\w+)>(.*?)</\1>', re.DOTALL)
        for match in tag_pattern.finditer(output):
            tag = match.group(1)
            content = match.group(2).strip()
            result[tag] = content

        return result

    def _parse_list(self, output: str) -> List[str]:
        """Parse list from output."""
        items = []

        # Try numbered list
        for match in re.finditer(r'^\d+\.\s*(.+)$', output, re.MULTILINE):
            items.append(match.group(1).strip())

        if items:
            return items

        # Try bullet list
        for match in re.finditer(r'^[-*]\s*(.+)$', output, re.MULTILINE):
            items.append(match.group(1).strip())

        if items:
            return items

        # Fall back to line split
        return [line.strip() for line in output.split('\n') if line.strip()]

    def _parse_code(self, output: str) -> str:
        """Parse code from output."""
        # Extract from code blocks
        code_match = re.search(r'```(?:\w+)?\s*(.*?)\s*```', output, re.DOTALL)
        if code_match:
            return code_match.group(1)

        return output.strip()

    def _parse_table(self, output: str) -> List[List[str]]:
        """Parse table from output."""
        rows = []

        for line in output.split('\n'):
            if '|' in line:
                cells = [cell.strip() for cell in line.split('|')]
                cells = [c for c in cells if c and c != '-' * len(c)]
                if cells:
                    rows.append(cells)

        return rows


# =============================================================================
# PROMPT BUILDER
# =============================================================================

class PromptBuilder:
    """Build prompts with fluent interface."""

    def __init__(self):
        self._system: Optional[str] = None
        self._messages: List[PromptMessage] = []
        self._examples: List[FewShotExample] = []
        self._context: Dict[str, Any] = {}
        self._style: PromptStyle = PromptStyle.DIRECT
        self._output_format: OutputFormat = OutputFormat.TEXT

    def system(self, content: str) -> 'PromptBuilder':
        """Set system message."""
        self._system = content
        return self

    def user(self, content: str) -> 'PromptBuilder':
        """Add user message."""
        self._messages.append(PromptMessage(
            role=PromptRole.USER,
            content=content
        ))
        return self

    def assistant(self, content: str) -> 'PromptBuilder':
        """Add assistant message."""
        self._messages.append(PromptMessage(
            role=PromptRole.ASSISTANT,
            content=content
        ))
        return self

    def example(self, input: str, output: str, explanation: Optional[str] = None) -> 'PromptBuilder':
        """Add few-shot example."""
        self._examples.append(FewShotExample(
            input=input,
            output=output,
            explanation=explanation
        ))
        return self

    def context(self, key: str, value: Any) -> 'PromptBuilder':
        """Add context variable."""
        self._context[key] = value
        return self

    def style(self, style: PromptStyle) -> 'PromptBuilder':
        """Set prompt style."""
        self._style = style
        return self

    def format(self, format: OutputFormat) -> 'PromptBuilder':
        """Set output format."""
        self._output_format = format
        return self

    def chain_of_thought(self) -> 'PromptBuilder':
        """Enable chain-of-thought prompting."""
        self._style = PromptStyle.CHAIN_OF_THOUGHT
        return self

    def build(self) -> List[PromptMessage]:
        """Build final prompt messages."""
        messages = []

        # System message
        system_content = self._system or ""

        # Add style instructions
        if self._style == PromptStyle.CHAIN_OF_THOUGHT:
            system_content += "\n\nThink through this step-by-step. Show your reasoning process before giving the final answer."

        # Add format instructions
        if self._output_format == OutputFormat.JSON:
            system_content += "\n\nRespond with valid JSON only."
        elif self._output_format == OutputFormat.LIST:
            system_content += "\n\nRespond with a numbered list."

        if system_content:
            messages.append(PromptMessage(
                role=PromptRole.SYSTEM,
                content=system_content.strip()
            ))

        # Add examples
        for example in self._examples:
            messages.append(PromptMessage(
                role=PromptRole.USER,
                content=example.input
            ))

            output = example.output
            if example.explanation:
                output = f"{example.explanation}\n\n{output}"

            messages.append(PromptMessage(
                role=PromptRole.ASSISTANT,
                content=output
            ))

        # Add conversation messages
        messages.extend(self._messages)

        return messages


# =============================================================================
# PROMPT LIBRARY
# =============================================================================

class PromptLibrary:
    """Store and manage prompt templates."""

    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}
        self._versions: Dict[str, List[PromptTemplate]] = defaultdict(list)
        self._tags: Dict[str, Set[str]] = defaultdict(set)

    def add(self, template: PromptTemplate) -> str:
        """Add template to library."""
        self._templates[template.id] = template
        self._versions[template.name].append(template)

        # Index by tags
        for tag in template.metadata.get("tags", []):
            self._tags[tag].add(template.id)

        return template.id

    def get(self, template_id: str) -> Optional[PromptTemplate]:
        """Get template by ID."""
        return self._templates.get(template_id)

    def get_by_name(self, name: str, version: Optional[int] = None) -> Optional[PromptTemplate]:
        """Get template by name and optional version."""
        versions = self._versions.get(name, [])

        if not versions:
            return None

        if version is not None:
            for v in versions:
                if v.version == version:
                    return v
            return None

        # Return latest version
        return max(versions, key=lambda t: t.version)

    def list_all(self) -> List[PromptTemplate]:
        """List all templates."""
        return list(self._templates.values())

    def search_by_tag(self, tag: str) -> List[PromptTemplate]:
        """Search templates by tag."""
        template_ids = self._tags.get(tag, set())
        return [self._templates[tid] for tid in template_ids if tid in self._templates]

    def delete(self, template_id: str) -> bool:
        """Delete template."""
        if template_id in self._templates:
            template = self._templates[template_id]
            del self._templates[template_id]

            # Remove from versions
            if template.name in self._versions:
                self._versions[template.name] = [
                    t for t in self._versions[template.name]
                    if t.id != template_id
                ]

            # Remove from tags
            for tag_set in self._tags.values():
                tag_set.discard(template_id)

            return True

        return False


# =============================================================================
# PROMPT OPTIMIZER
# =============================================================================

class PromptOptimizer:
    """Optimize prompts for better results."""

    def __init__(self):
        self._token_counter = TokenCounter()

    def optimize(
        self,
        messages: List[PromptMessage],
        max_tokens: int = 4000,
        preserve_system: bool = True
    ) -> List[PromptMessage]:
        """Optimize prompt to fit token limit."""
        current_tokens = self._token_counter.count_messages(messages)

        if current_tokens <= max_tokens:
            return messages

        optimized = messages.copy()

        # Remove examples first (if they exist in message history)
        while len(optimized) > 2 and self._token_counter.count_messages(optimized) > max_tokens:
            # Find and remove example pairs (user + assistant)
            for i in range(len(optimized) - 2, 0, -2):
                if (optimized[i].role == PromptRole.USER and
                    optimized[i + 1].role == PromptRole.ASSISTANT):
                    # Check if this looks like an example
                    if len(optimized[i].content) < 500:
                        optimized.pop(i + 1)
                        optimized.pop(i)
                        break
            else:
                break

        # Truncate long messages if still over limit
        if self._token_counter.count_messages(optimized) > max_tokens:
            for msg in optimized:
                if msg.role == PromptRole.SYSTEM and preserve_system:
                    continue

                if len(msg.content) > 1000:
                    # Truncate message
                    msg.content = msg.content[:800] + "... [truncated]"

        return optimized

    def suggest_improvements(self, template: PromptTemplate) -> List[str]:
        """Suggest improvements for prompt template."""
        suggestions = []

        # Check for missing elements
        if not template.system_prompt:
            suggestions.append("Add a system prompt to set context and behavior")

        if template.style == PromptStyle.FEW_SHOT and not template.examples:
            suggestions.append("Add few-shot examples for better results")

        # Check template content
        if len(template.template) < 50:
            suggestions.append("Template is quite short - consider adding more detail")

        if "{{" not in template.template:
            suggestions.append("No variables found - consider making the prompt more dynamic")

        # Check for good practices
        if "step by step" not in template.template.lower() and "chain of thought" not in template.template.lower():
            suggestions.append("Consider adding chain-of-thought prompting for complex tasks")

        if template.output_format != OutputFormat.TEXT and "format" not in template.template.lower():
            suggestions.append(f"Explicitly instruct the format: {template.output_format.value}")

        return suggestions


# =============================================================================
# PROMPT MANAGER
# =============================================================================

class PromptManager:
    """
    Prompt Manager for BAEL.

    Advanced prompt engineering and management.
    """

    def __init__(self):
        self._library = PromptLibrary()
        self._renderer = TemplateRenderer()
        self._parser = OutputParser()
        self._optimizer = PromptOptimizer()
        self._token_counter = TokenCounter()
        self._metrics: Dict[str, PromptMetrics] = {}

    # -------------------------------------------------------------------------
    # TEMPLATE MANAGEMENT
    # -------------------------------------------------------------------------

    def create_template(
        self,
        name: str,
        template: str,
        description: str = "",
        variables: Optional[List[PromptVariable]] = None,
        style: PromptStyle = PromptStyle.DIRECT,
        output_format: OutputFormat = OutputFormat.TEXT,
        system_prompt: Optional[str] = None,
        examples: Optional[List[FewShotExample]] = None,
        **metadata
    ) -> PromptTemplate:
        """Create a new prompt template."""
        pt = PromptTemplate(
            name=name,
            description=description,
            template=template,
            variables=variables or [],
            style=style,
            output_format=output_format,
            system_prompt=system_prompt,
            examples=examples or [],
            metadata=metadata
        )

        self._library.add(pt)
        self._metrics[pt.id] = PromptMetrics(template_id=pt.id)

        return pt

    def get_template(self, name_or_id: str) -> Optional[PromptTemplate]:
        """Get template by name or ID."""
        # Try by ID first
        template = self._library.get(name_or_id)
        if template:
            return template

        # Try by name
        return self._library.get_by_name(name_or_id)

    def list_templates(self) -> List[PromptTemplate]:
        """List all templates."""
        return self._library.list_all()

    def delete_template(self, template_id: str) -> bool:
        """Delete template."""
        return self._library.delete(template_id)

    # -------------------------------------------------------------------------
    # RENDERING
    # -------------------------------------------------------------------------

    def render(
        self,
        template: Union[str, PromptTemplate],
        variables: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> PromptResult:
        """Render a prompt template."""
        if isinstance(template, str):
            pt = self.get_template(template)
            if not pt:
                # Treat as raw template
                pt = PromptTemplate(template=template)
        else:
            pt = template

        variables = variables or {}
        variables.update(kwargs)

        # Render template
        rendered, warnings = self._renderer.render(
            pt.template,
            variables,
            pt.variables
        )

        # Build messages
        messages = []

        # System prompt
        if pt.system_prompt:
            sys_content, sys_warnings = self._renderer.render(pt.system_prompt, variables)
            messages.append(PromptMessage(
                role=PromptRole.SYSTEM,
                content=sys_content
            ))
            warnings.extend(sys_warnings)

        # Add examples
        for example in pt.examples:
            messages.append(PromptMessage(
                role=PromptRole.USER,
                content=example.input
            ))
            messages.append(PromptMessage(
                role=PromptRole.ASSISTANT,
                content=example.output
            ))

        # Main prompt
        messages.append(PromptMessage(
            role=PromptRole.USER,
            content=rendered
        ))

        # Count tokens
        token_count = self._token_counter.count_messages(messages)

        # Update metrics
        if pt.id in self._metrics:
            metrics = self._metrics[pt.id]
            metrics.render_count += 1
            metrics.avg_token_count = (
                (metrics.avg_token_count * (metrics.render_count - 1) + token_count) /
                metrics.render_count
            )
            metrics.last_used = datetime.utcnow()

        return PromptResult(
            messages=messages,
            template_id=pt.id,
            variables_used=variables,
            token_count=token_count,
            warnings=warnings
        )

    # -------------------------------------------------------------------------
    # BUILDER
    # -------------------------------------------------------------------------

    def builder(self) -> PromptBuilder:
        """Create a new prompt builder."""
        return PromptBuilder()

    # -------------------------------------------------------------------------
    # PARSING
    # -------------------------------------------------------------------------

    def parse_output(
        self,
        output: str,
        format: OutputFormat = OutputFormat.TEXT
    ) -> ParsedOutput:
        """Parse LLM output."""
        return self._parser.parse(output, format)

    def parse_json(self, output: str) -> ParsedOutput:
        """Parse JSON output."""
        return self._parser.parse(output, OutputFormat.JSON)

    def parse_list(self, output: str) -> ParsedOutput:
        """Parse list output."""
        return self._parser.parse(output, OutputFormat.LIST)

    # -------------------------------------------------------------------------
    # OPTIMIZATION
    # -------------------------------------------------------------------------

    def optimize(
        self,
        messages: List[PromptMessage],
        max_tokens: int = 4000
    ) -> List[PromptMessage]:
        """Optimize prompt to fit token limit."""
        return self._optimizer.optimize(messages, max_tokens)

    def suggest_improvements(self, template: Union[str, PromptTemplate]) -> List[str]:
        """Get improvement suggestions for template."""
        if isinstance(template, str):
            pt = self.get_template(template)
            if not pt:
                return ["Template not found"]
        else:
            pt = template

        return self._optimizer.suggest_improvements(pt)

    # -------------------------------------------------------------------------
    # TOKEN COUNTING
    # -------------------------------------------------------------------------

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return self._token_counter.count(text)

    def count_message_tokens(self, messages: List[PromptMessage]) -> int:
        """Count tokens in messages."""
        return self._token_counter.count_messages(messages)

    # -------------------------------------------------------------------------
    # METRICS
    # -------------------------------------------------------------------------

    def get_metrics(self, template_id: str) -> Optional[PromptMetrics]:
        """Get template metrics."""
        return self._metrics.get(template_id)

    def get_all_metrics(self) -> Dict[str, PromptMetrics]:
        """Get all metrics."""
        return self._metrics.copy()

    # -------------------------------------------------------------------------
    # UTILITY
    # -------------------------------------------------------------------------

    def extract_variables(self, template: str) -> List[str]:
        """Extract variable names from template."""
        return self._renderer.extract_variables(template)

    def validate_variables(
        self,
        template: PromptTemplate,
        variables: Dict[str, Any]
    ) -> List[str]:
        """Validate variables against template requirements."""
        errors = []

        for var in template.variables:
            if var.required and var.name not in variables:
                if var.default is None:
                    errors.append(f"Required variable '{var.name}' not provided")

            if var.name in variables and var.validator:
                if not var.validator(variables[var.name]):
                    errors.append(f"Variable '{var.name}' failed validation")

        return errors


# =============================================================================
# COMMON TEMPLATES
# =============================================================================

class CommonTemplates:
    """Pre-built common prompt templates."""

    @staticmethod
    def summarize() -> PromptTemplate:
        """Summarization template."""
        return PromptTemplate(
            name="summarize",
            description="Summarize text content",
            system_prompt="You are a helpful assistant that creates clear, concise summaries.",
            template="""Please summarize the following text:

{{text}}

{% if max_length %}Target length: {{max_length}} words{% endif %}
{% if style %}Style: {{style}}{% endif %}""",
            variables=[
                PromptVariable(name="text", description="Text to summarize", required=True),
                PromptVariable(name="max_length", description="Target summary length", required=False),
                PromptVariable(name="style", description="Summary style (bullet, paragraph)", required=False),
            ],
            style=PromptStyle.INSTRUCTION,
            output_format=OutputFormat.TEXT
        )

    @staticmethod
    def analyze() -> PromptTemplate:
        """Analysis template."""
        return PromptTemplate(
            name="analyze",
            description="Analyze content and provide insights",
            system_prompt="You are an expert analyst. Provide thorough, structured analysis.",
            template="""Analyze the following {{content_type|content}}:

{{content}}

Focus areas:
{% for area in focus_areas %}
- {{area}}
{% endfor %}

Provide your analysis in a structured format.""",
            variables=[
                PromptVariable(name="content", description="Content to analyze", required=True),
                PromptVariable(name="content_type", description="Type of content", required=False),
                PromptVariable(name="focus_areas", description="Areas to focus on", required=False),
            ],
            style=PromptStyle.CHAIN_OF_THOUGHT,
            output_format=OutputFormat.MARKDOWN
        )

    @staticmethod
    def classify() -> PromptTemplate:
        """Classification template."""
        return PromptTemplate(
            name="classify",
            description="Classify content into categories",
            system_prompt="You are a classification expert. Classify content accurately and explain your reasoning.",
            template="""Classify the following {{item_type|item}} into one of these categories: {{categories}}

Item to classify:
{{content}}

Respond with JSON: {"category": "...", "confidence": 0.0-1.0, "reasoning": "..."}""",
            variables=[
                PromptVariable(name="content", description="Content to classify", required=True),
                PromptVariable(name="categories", description="Available categories", required=True),
                PromptVariable(name="item_type", description="Type of item", required=False),
            ],
            style=PromptStyle.INSTRUCTION,
            output_format=OutputFormat.JSON
        )

    @staticmethod
    def extract() -> PromptTemplate:
        """Extraction template."""
        return PromptTemplate(
            name="extract",
            description="Extract structured information from text",
            system_prompt="You are a data extraction specialist. Extract information accurately and completely.",
            template="""Extract the following information from the text:

Fields to extract:
{% for field in fields %}
- {{field}}
{% endfor %}

Text:
{{text}}

Respond with JSON containing the extracted fields.""",
            variables=[
                PromptVariable(name="text", description="Text to extract from", required=True),
                PromptVariable(name="fields", description="Fields to extract", required=True),
            ],
            style=PromptStyle.INSTRUCTION,
            output_format=OutputFormat.JSON
        )


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Prompt Manager."""
    print("=" * 70)
    print("BAEL - PROMPT MANAGER DEMO")
    print("Advanced Prompt Engineering")
    print("=" * 70)
    print()

    manager = PromptManager()

    # 1. Create Simple Template
    print("1. CREATE SIMPLE TEMPLATE:")
    print("-" * 40)

    template = manager.create_template(
        name="greeting",
        template="Hello, {{name}}! Welcome to {{place|BAEL}}.",
        description="Simple greeting template"
    )

    print(f"   Template: {template.name}")
    print(f"   ID: {template.id[:8]}...")
    print()

    # 2. Render Template
    print("2. RENDER TEMPLATE:")
    print("-" * 40)

    result = manager.render(template, name="User", place="the System")

    print(f"   Variables: {result.variables_used}")
    print(f"   Token count: {result.token_count}")
    print(f"   Message: {result.messages[-1].content}")
    print()

    # 3. Template with System Prompt
    print("3. TEMPLATE WITH SYSTEM PROMPT:")
    print("-" * 40)

    assistant_template = manager.create_template(
        name="assistant",
        template="{{query}}",
        system_prompt="You are {{role}}, an AI assistant specialized in {{domain}}. Be helpful and concise.",
        variables=[
            PromptVariable(name="query", description="User query", required=True),
            PromptVariable(name="role", description="Assistant role", default="BAEL"),
            PromptVariable(name="domain", description="Specialization domain", default="general tasks"),
        ]
    )

    result = manager.render(assistant_template, query="What is machine learning?", domain="AI")

    for msg in result.messages:
        print(f"   [{msg.role.value}]: {msg.content[:60]}...")
    print()

    # 4. Few-Shot Template
    print("4. FEW-SHOT TEMPLATE:")
    print("-" * 40)

    sentiment_template = manager.create_template(
        name="sentiment",
        template="Classify the sentiment of: {{text}}",
        system_prompt="Classify text sentiment as positive, negative, or neutral.",
        style=PromptStyle.FEW_SHOT,
        examples=[
            FewShotExample("I love this product!", "positive"),
            FewShotExample("This is terrible.", "negative"),
            FewShotExample("It's okay, nothing special.", "neutral"),
        ]
    )

    result = manager.render(sentiment_template, text="This is amazing!")

    print(f"   Total messages: {len(result.messages)}")
    print(f"   Examples included: {len(sentiment_template.examples)}")
    print()

    # 5. Prompt Builder
    print("5. PROMPT BUILDER:")
    print("-" * 40)

    messages = (manager.builder()
        .system("You are a helpful coding assistant.")
        .example("How do I print in Python?", "Use print('Hello')")
        .user("How do I read a file?")
        .chain_of_thought()
        .format(OutputFormat.CODE)
        .build())

    print(f"   Built {len(messages)} messages")
    for msg in messages:
        print(f"      [{msg.role.value}]: {msg.content[:50]}...")
    print()

    # 6. Output Parsing
    print("6. OUTPUT PARSING:")
    print("-" * 40)

    json_output = '```json\n{"name": "BAEL", "version": "1.0"}\n```'
    parsed = manager.parse_json(json_output)

    print(f"   Raw: {json_output[:30]}...")
    print(f"   Parsed: {parsed.parsed}")
    print(f"   Success: {parsed.success}")

    list_output = "1. First item\n2. Second item\n3. Third item"
    parsed_list = manager.parse_list(list_output)

    print(f"   List: {parsed_list.parsed}")
    print()

    # 7. Token Counting
    print("7. TOKEN COUNTING:")
    print("-" * 40)

    text = "This is a sample text for token counting. It contains multiple words and sentences."
    tokens = manager.count_tokens(text)

    print(f"   Text length: {len(text)} chars")
    print(f"   Estimated tokens: {tokens}")
    print()

    # 8. Variable Extraction
    print("8. VARIABLE EXTRACTION:")
    print("-" * 40)

    template_str = "Hello {{name}}, you have {{count}} messages from {{sender}}."
    variables = manager.extract_variables(template_str)

    print(f"   Template: {template_str}")
    print(f"   Variables: {variables}")
    print()

    # 9. Prompt Optimization
    print("9. PROMPT OPTIMIZATION:")
    print("-" * 40)

    long_messages = [
        PromptMessage(role=PromptRole.SYSTEM, content="System prompt"),
        PromptMessage(role=PromptRole.USER, content="Example 1 input"),
        PromptMessage(role=PromptRole.ASSISTANT, content="Example 1 output"),
        PromptMessage(role=PromptRole.USER, content="Example 2 input"),
        PromptMessage(role=PromptRole.ASSISTANT, content="Example 2 output"),
        PromptMessage(role=PromptRole.USER, content="Actual query"),
    ]

    optimized = manager.optimize(long_messages, max_tokens=50)

    print(f"   Original messages: {len(long_messages)}")
    print(f"   Optimized messages: {len(optimized)}")
    print()

    # 10. Improvement Suggestions
    print("10. IMPROVEMENT SUGGESTIONS:")
    print("-" * 40)

    simple_template = manager.create_template(
        name="simple",
        template="Do something."
    )

    suggestions = manager.suggest_improvements(simple_template)

    for suggestion in suggestions:
        print(f"   - {suggestion}")
    print()

    # 11. Common Templates
    print("11. COMMON TEMPLATES:")
    print("-" * 40)

    summarize = CommonTemplates.summarize()
    analyze = CommonTemplates.analyze()
    classify = CommonTemplates.classify()

    manager._library.add(summarize)
    manager._library.add(analyze)
    manager._library.add(classify)

    print(f"   Available templates:")
    for t in manager.list_templates():
        print(f"      - {t.name}: {t.description[:40]}...")
    print()

    # 12. Template Metrics
    print("12. TEMPLATE METRICS:")
    print("-" * 40)

    # Render a few times
    for _ in range(5):
        manager.render("greeting", name="Test")

    metrics = manager.get_metrics(template.id)

    print(f"   Template: {template.name}")
    print(f"   Render count: {metrics.render_count}")
    print(f"   Avg tokens: {metrics.avg_token_count:.1f}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Prompt Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
