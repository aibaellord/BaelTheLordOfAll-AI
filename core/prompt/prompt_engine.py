#!/usr/bin/env python3
"""
BAEL - Prompt Engine
Advanced prompt management.

Features:
- Prompt templates
- Variable injection
- Chain-of-thought
- Few-shot examples
- Prompt versioning
"""

import asyncio
import hashlib
import json
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class PromptType(Enum):
    """Types of prompts."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class TemplateFormat(Enum):
    """Template formatting styles."""
    JINJA = "jinja"
    FSTRING = "fstring"
    MUSTACHE = "mustache"
    PLAIN = "plain"


class PromptStrategy(Enum):
    """Prompting strategies."""
    ZERO_SHOT = "zero_shot"
    FEW_SHOT = "few_shot"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    TREE_OF_THOUGHT = "tree_of_thought"
    SELF_CONSISTENCY = "self_consistency"


class PromptStatus(Enum):
    """Prompt status."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DRAFT = "draft"
    ARCHIVED = "archived"


class RoleType(Enum):
    """Role types."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class PromptVariable:
    """Prompt variable definition."""
    name: str
    description: str = ""
    required: bool = True
    default_value: Any = None
    var_type: str = "string"
    validators: List[str] = field(default_factory=list)


@dataclass
class PromptExample:
    """Few-shot example."""
    example_id: str = ""
    input_text: str = ""
    output_text: str = ""
    explanation: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.example_id:
            self.example_id = str(uuid.uuid4())[:8]


@dataclass
class PromptMessage:
    """Chat message."""
    role: RoleType
    content: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PromptTemplate:
    """Prompt template."""
    template_id: str = ""
    name: str = ""
    content: str = ""
    prompt_type: PromptType = PromptType.USER
    format_type: TemplateFormat = TemplateFormat.FSTRING
    variables: List[PromptVariable] = field(default_factory=list)
    examples: List[PromptExample] = field(default_factory=list)
    description: str = ""
    version: str = "1.0.0"
    status: PromptStatus = PromptStatus.ACTIVE
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.template_id:
            self.template_id = str(uuid.uuid4())[:8]


@dataclass
class CompiledPrompt:
    """Compiled prompt ready for use."""
    prompt_id: str = ""
    content: str = ""
    template_id: str = ""
    variables_used: Dict[str, Any] = field(default_factory=dict)
    token_estimate: int = 0
    compiled_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.prompt_id:
            self.prompt_id = str(uuid.uuid4())[:8]


@dataclass
class PromptChain:
    """Chain of prompts."""
    chain_id: str = ""
    name: str = ""
    prompts: List[str] = field(default_factory=list)
    strategy: PromptStrategy = PromptStrategy.ZERO_SHOT
    description: str = ""

    def __post_init__(self):
        if not self.chain_id:
            self.chain_id = str(uuid.uuid4())[:8]


@dataclass
class PromptStats:
    """Prompt usage statistics."""
    total_compilations: int = 0
    total_tokens: int = 0
    avg_tokens_per_prompt: float = 0.0
    by_template: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# TEMPLATE FORMATTERS
# =============================================================================

class BaseFormatter(ABC):
    """Abstract base formatter."""

    @property
    @abstractmethod
    def format_type(self) -> TemplateFormat:
        """Get format type."""
        pass

    @abstractmethod
    def format(self, template: str, variables: Dict[str, Any]) -> str:
        """Format template with variables."""
        pass

    @abstractmethod
    def extract_variables(self, template: str) -> List[str]:
        """Extract variable names from template."""
        pass


class FStringFormatter(BaseFormatter):
    """Python f-string style formatter."""

    @property
    def format_type(self) -> TemplateFormat:
        return TemplateFormat.FSTRING

    def format(self, template: str, variables: Dict[str, Any]) -> str:
        """Format using {variable} syntax."""
        result = template

        for name, value in variables.items():
            placeholder = "{" + name + "}"
            result = result.replace(placeholder, str(value))

        return result

    def extract_variables(self, template: str) -> List[str]:
        """Extract {variable} names."""
        pattern = r'\{(\w+)\}'
        matches = re.findall(pattern, template)
        return list(set(matches))


class MustacheFormatter(BaseFormatter):
    """Mustache style formatter."""

    @property
    def format_type(self) -> TemplateFormat:
        return TemplateFormat.MUSTACHE

    def format(self, template: str, variables: Dict[str, Any]) -> str:
        """Format using {{variable}} syntax."""
        result = template

        for name, value in variables.items():
            placeholder = "{{" + name + "}}"
            result = result.replace(placeholder, str(value))

        return result

    def extract_variables(self, template: str) -> List[str]:
        """Extract {{variable}} names."""
        pattern = r'\{\{(\w+)\}\}'
        matches = re.findall(pattern, template)
        return list(set(matches))


class JinjaFormatter(BaseFormatter):
    """Jinja-style formatter (simplified)."""

    @property
    def format_type(self) -> TemplateFormat:
        return TemplateFormat.JINJA

    def format(self, template: str, variables: Dict[str, Any]) -> str:
        """Format using {{ variable }} syntax."""
        result = template

        for name, value in variables.items():
            patterns = [
                "{{ " + name + " }}",
                "{{" + name + "}}"
            ]

            for pattern in patterns:
                result = result.replace(pattern, str(value))

        for_pattern = r'\{% for (\w+) in (\w+) %\}(.*?)\{% endfor %\}'

        def replace_for(match):
            item_name = match.group(1)
            list_name = match.group(2)
            body = match.group(3)

            if list_name not in variables:
                return ""

            items = variables[list_name]
            if not isinstance(items, list):
                return ""

            results = []
            for item in items:
                item_result = body.replace("{{ " + item_name + " }}", str(item))
                item_result = item_result.replace("{{" + item_name + "}}", str(item))
                results.append(item_result)

            return "".join(results)

        result = re.sub(for_pattern, replace_for, result, flags=re.DOTALL)

        return result

    def extract_variables(self, template: str) -> List[str]:
        """Extract variable names."""
        pattern1 = r'\{\{\s*(\w+)\s*\}\}'
        pattern2 = r'\{% for \w+ in (\w+) %\}'

        matches1 = re.findall(pattern1, template)
        matches2 = re.findall(pattern2, template)

        return list(set(matches1 + matches2))


class PlainFormatter(BaseFormatter):
    """Plain text formatter (no variables)."""

    @property
    def format_type(self) -> TemplateFormat:
        return TemplateFormat.PLAIN

    def format(self, template: str, variables: Dict[str, Any]) -> str:
        """Return template as-is."""
        return template

    def extract_variables(self, template: str) -> List[str]:
        """No variables in plain text."""
        return []


# =============================================================================
# PROMPT BUILDERS
# =============================================================================

class BasePromptBuilder(ABC):
    """Abstract prompt builder."""

    @property
    @abstractmethod
    def strategy(self) -> PromptStrategy:
        """Get prompting strategy."""
        pass

    @abstractmethod
    def build(
        self,
        template: PromptTemplate,
        variables: Dict[str, Any],
        formatter: BaseFormatter
    ) -> str:
        """Build the prompt."""
        pass


class ZeroShotBuilder(BasePromptBuilder):
    """Zero-shot prompt builder."""

    @property
    def strategy(self) -> PromptStrategy:
        return PromptStrategy.ZERO_SHOT

    def build(
        self,
        template: PromptTemplate,
        variables: Dict[str, Any],
        formatter: BaseFormatter
    ) -> str:
        """Build zero-shot prompt."""
        return formatter.format(template.content, variables)


class FewShotBuilder(BasePromptBuilder):
    """Few-shot prompt builder."""

    @property
    def strategy(self) -> PromptStrategy:
        return PromptStrategy.FEW_SHOT

    def build(
        self,
        template: PromptTemplate,
        variables: Dict[str, Any],
        formatter: BaseFormatter
    ) -> str:
        """Build few-shot prompt with examples."""
        parts = []

        if template.examples:
            parts.append("Examples:")

            for i, example in enumerate(template.examples, 1):
                parts.append(f"\nExample {i}:")
                parts.append(f"Input: {example.input_text}")
                parts.append(f"Output: {example.output_text}")

                if example.explanation:
                    parts.append(f"Explanation: {example.explanation}")

            parts.append("\n---\n")

        main_content = formatter.format(template.content, variables)
        parts.append(main_content)

        return "\n".join(parts)


class ChainOfThoughtBuilder(BasePromptBuilder):
    """Chain-of-thought prompt builder."""

    @property
    def strategy(self) -> PromptStrategy:
        return PromptStrategy.CHAIN_OF_THOUGHT

    def build(
        self,
        template: PromptTemplate,
        variables: Dict[str, Any],
        formatter: BaseFormatter
    ) -> str:
        """Build CoT prompt."""
        parts = []

        main_content = formatter.format(template.content, variables)
        parts.append(main_content)

        parts.append("\n\nLet's think step by step:")
        parts.append("\n1. First, I'll analyze the problem")
        parts.append("2. Then, I'll break it down into smaller parts")
        parts.append("3. Next, I'll solve each part systematically")
        parts.append("4. Finally, I'll combine the results for the answer")

        return "\n".join(parts)


class TreeOfThoughtBuilder(BasePromptBuilder):
    """Tree-of-thought prompt builder."""

    @property
    def strategy(self) -> PromptStrategy:
        return PromptStrategy.TREE_OF_THOUGHT

    def build(
        self,
        template: PromptTemplate,
        variables: Dict[str, Any],
        formatter: BaseFormatter
    ) -> str:
        """Build ToT prompt."""
        parts = []

        parts.append("Consider multiple solution paths:\n")

        main_content = formatter.format(template.content, variables)
        parts.append(f"Problem: {main_content}\n")

        parts.append("Path A - Direct Approach:")
        parts.append("  - Step A1: [reasoning]")
        parts.append("  - Step A2: [reasoning]")
        parts.append("  - Evaluation: [assessment]\n")

        parts.append("Path B - Alternative Approach:")
        parts.append("  - Step B1: [reasoning]")
        parts.append("  - Step B2: [reasoning]")
        parts.append("  - Evaluation: [assessment]\n")

        parts.append("Path C - Creative Approach:")
        parts.append("  - Step C1: [reasoning]")
        parts.append("  - Step C2: [reasoning]")
        parts.append("  - Evaluation: [assessment]\n")

        parts.append("Select best path and provide final answer:")

        return "\n".join(parts)


# =============================================================================
# PROMPT ENGINE
# =============================================================================

class PromptEngine:
    """
    Prompt Engine for BAEL.

    Advanced prompt management.
    """

    def __init__(self, default_format: TemplateFormat = TemplateFormat.FSTRING):
        self._default_format = default_format

        self._formatters: Dict[TemplateFormat, BaseFormatter] = {
            TemplateFormat.FSTRING: FStringFormatter(),
            TemplateFormat.MUSTACHE: MustacheFormatter(),
            TemplateFormat.JINJA: JinjaFormatter(),
            TemplateFormat.PLAIN: PlainFormatter()
        }

        self._builders: Dict[PromptStrategy, BasePromptBuilder] = {
            PromptStrategy.ZERO_SHOT: ZeroShotBuilder(),
            PromptStrategy.FEW_SHOT: FewShotBuilder(),
            PromptStrategy.CHAIN_OF_THOUGHT: ChainOfThoughtBuilder(),
            PromptStrategy.TREE_OF_THOUGHT: TreeOfThoughtBuilder()
        }

        self._templates: Dict[str, PromptTemplate] = {}
        self._template_versions: Dict[str, List[PromptTemplate]] = defaultdict(list)
        self._chains: Dict[str, PromptChain] = {}

        self._stats = PromptStats()
        self._compilation_cache: Dict[str, CompiledPrompt] = {}

    def get_formatter(self, format_type: Optional[TemplateFormat] = None) -> BaseFormatter:
        """Get formatter by type."""
        format_type = format_type or self._default_format
        return self._formatters.get(format_type, FStringFormatter())

    def get_builder(self, strategy: PromptStrategy) -> BasePromptBuilder:
        """Get builder by strategy."""
        return self._builders.get(strategy, ZeroShotBuilder())

    def register_template(
        self,
        name: str,
        content: str,
        prompt_type: PromptType = PromptType.USER,
        format_type: Optional[TemplateFormat] = None,
        description: str = "",
        tags: Optional[List[str]] = None,
        examples: Optional[List[PromptExample]] = None
    ) -> PromptTemplate:
        """Register a prompt template."""
        format_type = format_type or self._default_format
        formatter = self.get_formatter(format_type)

        var_names = formatter.extract_variables(content)
        variables = [PromptVariable(name=n) for n in var_names]

        template = PromptTemplate(
            name=name,
            content=content,
            prompt_type=prompt_type,
            format_type=format_type,
            variables=variables,
            examples=examples or [],
            description=description,
            tags=tags or []
        )

        self._templates[name] = template
        self._template_versions[name].append(template)

        return template

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get template by name."""
        return self._templates.get(name)

    def list_templates(
        self,
        status: Optional[PromptStatus] = None,
        tag: Optional[str] = None
    ) -> List[PromptTemplate]:
        """List all templates."""
        templates = list(self._templates.values())

        if status:
            templates = [t for t in templates if t.status == status]

        if tag:
            templates = [t for t in templates if tag in t.tags]

        return templates

    def compile(
        self,
        template_name: str,
        variables: Optional[Dict[str, Any]] = None,
        strategy: PromptStrategy = PromptStrategy.ZERO_SHOT,
        use_cache: bool = True
    ) -> CompiledPrompt:
        """Compile a prompt template."""
        variables = variables or {}

        cache_key = f"{template_name}:{strategy.value}:{json.dumps(variables, sort_keys=True)}"

        if use_cache and cache_key in self._compilation_cache:
            return self._compilation_cache[cache_key]

        template = self._templates.get(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")

        for var in template.variables:
            if var.required and var.name not in variables:
                if var.default_value is not None:
                    variables[var.name] = var.default_value
                else:
                    raise ValueError(f"Missing required variable: {var.name}")

        formatter = self.get_formatter(template.format_type)
        builder = self.get_builder(strategy)

        content = builder.build(template, variables, formatter)

        token_estimate = len(content.split()) * 1.3

        compiled = CompiledPrompt(
            content=content,
            template_id=template.template_id,
            variables_used=variables,
            token_estimate=int(token_estimate)
        )

        if use_cache:
            self._compilation_cache[cache_key] = compiled

        self._update_stats(template_name, compiled.token_estimate)

        return compiled

    def compile_direct(
        self,
        content: str,
        variables: Optional[Dict[str, Any]] = None,
        format_type: Optional[TemplateFormat] = None
    ) -> CompiledPrompt:
        """Compile a prompt directly without template."""
        variables = variables or {}

        formatter = self.get_formatter(format_type)
        compiled_content = formatter.format(content, variables)

        token_estimate = len(compiled_content.split()) * 1.3

        return CompiledPrompt(
            content=compiled_content,
            variables_used=variables,
            token_estimate=int(token_estimate)
        )

    def add_examples(
        self,
        template_name: str,
        examples: List[PromptExample]
    ) -> bool:
        """Add examples to a template."""
        template = self._templates.get(template_name)
        if not template:
            return False

        template.examples.extend(examples)
        template.updated_at = datetime.now()

        return True

    def create_chain(
        self,
        name: str,
        prompts: List[str],
        strategy: PromptStrategy = PromptStrategy.ZERO_SHOT,
        description: str = ""
    ) -> PromptChain:
        """Create a prompt chain."""
        chain = PromptChain(
            name=name,
            prompts=prompts,
            strategy=strategy,
            description=description
        )

        self._chains[name] = chain

        return chain

    def get_chain(self, name: str) -> Optional[PromptChain]:
        """Get a prompt chain."""
        return self._chains.get(name)

    async def execute_chain(
        self,
        chain_name: str,
        initial_variables: Dict[str, Any]
    ) -> List[CompiledPrompt]:
        """Execute a prompt chain."""
        chain = self._chains.get(chain_name)
        if not chain:
            raise ValueError(f"Chain not found: {chain_name}")

        results = []
        current_vars = initial_variables.copy()

        for i, template_name in enumerate(chain.prompts):
            compiled = self.compile(
                template_name,
                current_vars,
                strategy=chain.strategy
            )

            results.append(compiled)

            current_vars[f"step_{i}_output"] = compiled.content

        return results

    def build_messages(
        self,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Tuple[RoleType, str]]] = None
    ) -> List[PromptMessage]:
        """Build chat messages."""
        result = []

        if system_prompt:
            result.append(PromptMessage(
                role=RoleType.SYSTEM,
                content=system_prompt
            ))

        if messages:
            for role, content in messages:
                result.append(PromptMessage(
                    role=role,
                    content=content
                ))

        return result

    def deprecate_template(self, template_name: str) -> bool:
        """Deprecate a template."""
        template = self._templates.get(template_name)
        if template:
            template.status = PromptStatus.DEPRECATED
            template.updated_at = datetime.now()
            return True
        return False

    def _update_stats(self, template_name: str, tokens: int) -> None:
        """Update statistics."""
        self._stats.total_compilations += 1
        self._stats.total_tokens += tokens

        self._stats.by_template[template_name] = \
            self._stats.by_template.get(template_name, 0) + 1

        if self._stats.total_compilations > 0:
            self._stats.avg_tokens_per_prompt = \
                self._stats.total_tokens / self._stats.total_compilations

    @property
    def stats(self) -> PromptStats:
        """Get engine statistics."""
        return self._stats

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "total_templates": len(self._templates),
            "total_chains": len(self._chains),
            "cache_size": len(self._compilation_cache),
            "stats": {
                "compilations": self._stats.total_compilations,
                "total_tokens": self._stats.total_tokens,
                "avg_tokens": round(self._stats.avg_tokens_per_prompt, 2),
                "by_template": self._stats.by_template
            },
            "formats": [f.value for f in self._formatters.keys()],
            "strategies": [s.value for s in self._builders.keys()]
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Prompt Engine."""
    print("=" * 70)
    print("BAEL - PROMPT ENGINE DEMO")
    print("Advanced Prompt Management")
    print("=" * 70)
    print()

    engine = PromptEngine(default_format=TemplateFormat.FSTRING)

    # 1. Register Templates
    print("1. REGISTER TEMPLATES:")
    print("-" * 40)

    qa_template = engine.register_template(
        name="qa_prompt",
        content="Answer the following question based on the context.\n\nContext: {context}\n\nQuestion: {question}\n\nAnswer:",
        prompt_type=PromptType.USER,
        description="Question-answering prompt",
        tags=["qa", "rag"]
    )

    summary_template = engine.register_template(
        name="summary_prompt",
        content="Summarize the following text in {max_words} words or less:\n\n{text}",
        description="Text summarization prompt",
        tags=["summarization"]
    )

    code_template = engine.register_template(
        name="code_prompt",
        content="Write a {language} function that {task}. Include docstrings and comments.",
        description="Code generation prompt",
        tags=["coding", "generation"]
    )

    print(f"   Registered: {qa_template.name}")
    print(f"      Variables: {[v.name for v in qa_template.variables]}")

    print(f"   Registered: {summary_template.name}")
    print(f"   Registered: {code_template.name}")
    print()

    # 2. Compile Basic Prompt
    print("2. COMPILE BASIC PROMPT:")
    print("-" * 40)

    compiled = engine.compile(
        "qa_prompt",
        variables={
            "context": "The capital of France is Paris. It is known for the Eiffel Tower.",
            "question": "What is the capital of France?"
        }
    )

    print(f"   Template: qa_prompt")
    print(f"   Token Estimate: {compiled.token_estimate}")
    print(f"   Content Preview: {compiled.content[:80]}...")
    print()

    # 3. Few-Shot Prompting
    print("3. FEW-SHOT PROMPTING:")
    print("-" * 40)

    engine.register_template(
        name="sentiment_prompt",
        content="Classify the sentiment of the following text: {text}",
        examples=[
            PromptExample(
                input_text="I love this product!",
                output_text="Positive",
                explanation="Expresses love/enthusiasm"
            ),
            PromptExample(
                input_text="This is terrible.",
                output_text="Negative",
                explanation="Expresses disappointment"
            ),
            PromptExample(
                input_text="It's okay I guess.",
                output_text="Neutral",
                explanation="Neither positive nor negative"
            )
        ],
        tags=["sentiment", "classification"]
    )

    few_shot = engine.compile(
        "sentiment_prompt",
        variables={"text": "The movie was absolutely fantastic!"},
        strategy=PromptStrategy.FEW_SHOT
    )

    print("   Strategy: FEW_SHOT")
    print(f"   Token Estimate: {few_shot.token_estimate}")
    print(f"   Content:\n{few_shot.content[:300]}...")
    print()

    # 4. Chain-of-Thought
    print("4. CHAIN-OF-THOUGHT:")
    print("-" * 40)

    engine.register_template(
        name="math_prompt",
        content="Solve the following problem: {problem}",
        tags=["math", "reasoning"]
    )

    cot = engine.compile(
        "math_prompt",
        variables={"problem": "If John has 3 apples and buys 5 more, how many does he have?"},
        strategy=PromptStrategy.CHAIN_OF_THOUGHT
    )

    print("   Strategy: CHAIN_OF_THOUGHT")
    print(f"   Content:\n{cot.content}")
    print()

    # 5. Tree-of-Thought
    print("5. TREE-OF-THOUGHT:")
    print("-" * 40)

    tot = engine.compile(
        "math_prompt",
        variables={"problem": "Find the optimal path from A to B"},
        strategy=PromptStrategy.TREE_OF_THOUGHT
    )

    print("   Strategy: TREE_OF_THOUGHT")
    print(f"   Content Preview:\n{tot.content[:400]}...")
    print()

    # 6. Different Formats
    print("6. TEMPLATE FORMATS:")
    print("-" * 40)

    engine.register_template(
        name="mustache_template",
        content="Hello, {{name}}! You have {{count}} messages.",
        format_type=TemplateFormat.MUSTACHE
    )

    engine.register_template(
        name="jinja_template",
        content="Items: {% for item in items %}{{ item }}, {% endfor %}",
        format_type=TemplateFormat.JINJA
    )

    mustache = engine.compile(
        "mustache_template",
        variables={"name": "Alice", "count": 5}
    )

    jinja = engine.compile(
        "jinja_template",
        variables={"items": ["apple", "banana", "cherry"]}
    )

    print(f"   Mustache: {mustache.content}")
    print(f"   Jinja: {jinja.content}")
    print()

    # 7. Direct Compilation
    print("7. DIRECT COMPILATION:")
    print("-" * 40)

    direct = engine.compile_direct(
        "Write a poem about {topic} in {style} style.",
        variables={"topic": "nature", "style": "haiku"}
    )

    print(f"   Content: {direct.content}")
    print(f"   Tokens: {direct.token_estimate}")
    print()

    # 8. Prompt Chains
    print("8. PROMPT CHAINS:")
    print("-" * 40)

    engine.register_template(
        name="analyze_prompt",
        content="Analyze the key themes in: {input_text}"
    )

    engine.register_template(
        name="expand_prompt",
        content="Based on the analysis: {step_0_output}\n\nExpand on the main theme."
    )

    chain = engine.create_chain(
        name="analysis_chain",
        prompts=["analyze_prompt", "expand_prompt"],
        strategy=PromptStrategy.ZERO_SHOT,
        description="Two-step analysis chain"
    )

    results = await engine.execute_chain(
        "analysis_chain",
        initial_variables={"input_text": "The forest was quiet."}
    )

    print(f"   Chain: {chain.name}")
    print(f"   Steps: {len(results)}")

    for i, r in enumerate(results, 1):
        print(f"   Step {i}: {r.content[:60]}...")
    print()

    # 9. Chat Messages
    print("9. CHAT MESSAGES:")
    print("-" * 40)

    messages = engine.build_messages(
        system_prompt="You are a helpful assistant.",
        messages=[
            (RoleType.USER, "Hello!"),
            (RoleType.ASSISTANT, "Hi! How can I help you today?"),
            (RoleType.USER, "Tell me about AI.")
        ]
    )

    for msg in messages:
        print(f"   {msg.role.value}: {msg.content[:50]}...")
    print()

    # 10. Engine Summary
    print("10. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    print(f"   Templates: {summary['total_templates']}")
    print(f"   Chains: {summary['total_chains']}")
    print(f"   Cache Size: {summary['cache_size']}")
    print(f"   Total Compilations: {summary['stats']['compilations']}")
    print(f"   Avg Tokens: {summary['stats']['avg_tokens']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Prompt Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
