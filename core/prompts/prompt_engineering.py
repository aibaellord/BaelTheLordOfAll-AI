#!/usr/bin/env python3
"""
BAEL - Advanced Prompt Engineering System
Sophisticated prompt construction and optimization.

Features:
- Dynamic prompt composition
- Chain-of-thought templates
- Prompt optimization
- Multi-turn conversation management
- Context injection
- Prompt versioning and A/B testing
"""

import asyncio
import hashlib
import json
import logging
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class PromptRole(Enum):
    """Role in conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class PromptStrategy(Enum):
    """Prompting strategies."""
    DIRECT = "direct"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    TREE_OF_THOUGHTS = "tree_of_thoughts"
    SELF_CONSISTENCY = "self_consistency"
    REACT = "react"  # Reasoning + Acting
    FEW_SHOT = "few_shot"
    ZERO_SHOT = "zero_shot"


class OutputFormat(Enum):
    """Expected output format."""
    TEXT = "text"
    JSON = "json"
    XML = "xml"
    MARKDOWN = "markdown"
    CODE = "code"
    STRUCTURED = "structured"


@dataclass
class PromptMessage:
    """Single message in prompt."""
    role: PromptRole
    content: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {"role": self.role.value, "content": self.content}
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class PromptTemplate:
    """Reusable prompt template."""
    id: str
    name: str
    template: str
    variables: List[str] = field(default_factory=list)
    description: str = ""
    strategy: PromptStrategy = PromptStrategy.DIRECT
    output_format: OutputFormat = OutputFormat.TEXT
    examples: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)

    def render(self, **kwargs) -> str:
        """Render template with variables."""
        result = self.template
        for var in self.variables:
            placeholder = "{" + var + "}"
            if var in kwargs:
                result = result.replace(placeholder, str(kwargs[var]))
        return result


@dataclass
class PromptStats:
    """Statistics for prompt performance."""
    template_id: str
    total_uses: int = 0
    avg_tokens: float = 0
    avg_latency_ms: float = 0
    success_rate: float = 1.0
    avg_quality_score: float = 1.0
    last_used: Optional[datetime] = None


# =============================================================================
# PROMPT COMPONENTS
# =============================================================================

class PromptComponent(ABC):
    """Abstract prompt component."""

    @abstractmethod
    def render(self, context: Dict[str, Any]) -> str:
        """Render component to string."""
        pass


class SystemPrompt(PromptComponent):
    """System instruction component."""

    def __init__(
        self,
        persona: str = "helpful assistant",
        capabilities: List[str] = None,
        constraints: List[str] = None,
        tone: str = "professional"
    ):
        self.persona = persona
        self.capabilities = capabilities or []
        self.constraints = constraints or []
        self.tone = tone

    def render(self, context: Dict[str, Any]) -> str:
        lines = [f"You are a {self.persona}."]

        if self.capabilities:
            lines.append("\nYou are capable of:")
            for cap in self.capabilities:
                lines.append(f"- {cap}")

        if self.constraints:
            lines.append("\nYou must:")
            for con in self.constraints:
                lines.append(f"- {con}")

        lines.append(f"\nMaintain a {self.tone} tone throughout.")

        return "\n".join(lines)


class ContextInjector(PromptComponent):
    """Inject relevant context."""

    def __init__(
        self,
        context_key: str,
        format_template: str = "Context:\n{context}",
        max_length: int = 2000
    ):
        self.context_key = context_key
        self.format_template = format_template
        self.max_length = max_length

    def render(self, context: Dict[str, Any]) -> str:
        ctx_value = context.get(self.context_key, "")

        if isinstance(ctx_value, list):
            ctx_value = "\n".join(str(item) for item in ctx_value)
        elif isinstance(ctx_value, dict):
            ctx_value = json.dumps(ctx_value, indent=2)
        else:
            ctx_value = str(ctx_value)

        # Truncate if needed
        if len(ctx_value) > self.max_length:
            ctx_value = ctx_value[:self.max_length] + "...[truncated]"

        return self.format_template.format(context=ctx_value)


class ExamplesComponent(PromptComponent):
    """Few-shot examples component."""

    def __init__(
        self,
        examples: List[Dict[str, str]] = None,
        input_key: str = "input",
        output_key: str = "output"
    ):
        self.examples = examples or []
        self.input_key = input_key
        self.output_key = output_key

    def render(self, context: Dict[str, Any]) -> str:
        if not self.examples:
            return ""

        lines = ["Here are some examples:"]

        for i, ex in enumerate(self.examples, 1):
            lines.append(f"\nExample {i}:")
            lines.append(f"Input: {ex.get(self.input_key, '')}")
            lines.append(f"Output: {ex.get(self.output_key, '')}")

        return "\n".join(lines)


class OutputInstructions(PromptComponent):
    """Output format instructions."""

    def __init__(
        self,
        format_type: OutputFormat,
        schema: Dict[str, Any] = None,
        additional_instructions: str = ""
    ):
        self.format_type = format_type
        self.schema = schema
        self.additional_instructions = additional_instructions

    def render(self, context: Dict[str, Any]) -> str:
        lines = []

        if self.format_type == OutputFormat.JSON:
            lines.append("Respond with valid JSON only.")
            if self.schema:
                lines.append(f"Follow this schema: {json.dumps(self.schema)}")
        elif self.format_type == OutputFormat.MARKDOWN:
            lines.append("Format your response in Markdown.")
        elif self.format_type == OutputFormat.CODE:
            lang = context.get("language", "python")
            lines.append(f"Respond with {lang} code only, no explanations.")
        elif self.format_type == OutputFormat.STRUCTURED:
            lines.append("Use a clear, structured format with headings and bullet points.")

        if self.additional_instructions:
            lines.append(self.additional_instructions)

        return "\n".join(lines)


# =============================================================================
# PROMPTING STRATEGIES
# =============================================================================

class PromptStrategyBuilder(ABC):
    """Abstract strategy builder."""

    @abstractmethod
    def build(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> List[PromptMessage]:
        """Build prompt using strategy."""
        pass


class ChainOfThoughtBuilder(PromptStrategyBuilder):
    """Chain of thought prompting."""

    def __init__(
        self,
        thinking_prefix: str = "Let me think through this step by step:",
        step_format: str = "Step {n}: {step}"
    ):
        self.thinking_prefix = thinking_prefix
        self.step_format = step_format

    def build(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> List[PromptMessage]:
        messages = []

        # System message with CoT instruction
        system_content = """You are an expert problem solver.
When given a task, think through it step by step before providing your final answer.
Show your reasoning process clearly."""

        messages.append(PromptMessage(
            role=PromptRole.SYSTEM,
            content=system_content
        ))

        # User message with thinking prompt
        user_content = f"""{task}

{self.thinking_prefix}"""

        messages.append(PromptMessage(
            role=PromptRole.USER,
            content=user_content
        ))

        return messages


class ReActBuilder(PromptStrategyBuilder):
    """ReAct (Reasoning + Acting) prompting."""

    def __init__(
        self,
        available_actions: List[str] = None
    ):
        self.available_actions = available_actions or [
            "search[query]",
            "lookup[term]",
            "calculate[expression]",
            "finish[answer]"
        ]

    def build(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> List[PromptMessage]:
        messages = []

        actions_str = "\n".join(f"- {a}" for a in self.available_actions)

        system_content = f"""You are an agent that solves tasks through a cycle of Thought, Action, and Observation.

Available actions:
{actions_str}

For each step:
1. Thought: Reason about what to do next
2. Action: Choose and execute an action
3. Observation: Process the result

Continue until you have the final answer."""

        messages.append(PromptMessage(
            role=PromptRole.SYSTEM,
            content=system_content
        ))

        user_content = f"""Task: {task}

Begin with your first thought."""

        messages.append(PromptMessage(
            role=PromptRole.USER,
            content=user_content
        ))

        return messages


class SelfConsistencyBuilder(PromptStrategyBuilder):
    """Self-consistency prompting with multiple reasoning paths."""

    def __init__(self, num_paths: int = 3):
        self.num_paths = num_paths

    def build(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> List[PromptMessage]:
        messages = []

        system_content = f"""You are an expert problem solver.
For this task, provide {self.num_paths} different reasoning approaches.
Then, determine the most consistent answer across all approaches."""

        messages.append(PromptMessage(
            role=PromptRole.SYSTEM,
            content=system_content
        ))

        user_content = f"""{task}

Provide {self.num_paths} different reasoning paths, then give your final answer based on what's most consistent."""

        messages.append(PromptMessage(
            role=PromptRole.USER,
            content=user_content
        ))

        return messages


# =============================================================================
# PROMPT COMPOSER
# =============================================================================

class PromptComposer:
    """Compose complex prompts from components."""

    def __init__(self):
        self.components: List[PromptComponent] = []
        self.strategy_builders: Dict[PromptStrategy, PromptStrategyBuilder] = {
            PromptStrategy.CHAIN_OF_THOUGHT: ChainOfThoughtBuilder(),
            PromptStrategy.REACT: ReActBuilder(),
            PromptStrategy.SELF_CONSISTENCY: SelfConsistencyBuilder()
        }

    def add_component(self, component: PromptComponent) -> 'PromptComposer':
        """Add component to composer."""
        self.components.append(component)
        return self

    def set_system_prompt(
        self,
        persona: str,
        capabilities: List[str] = None,
        constraints: List[str] = None
    ) -> 'PromptComposer':
        """Set system prompt."""
        self.components.append(SystemPrompt(
            persona=persona,
            capabilities=capabilities,
            constraints=constraints
        ))
        return self

    def add_context(
        self,
        context_key: str,
        format_template: str = "Context:\n{context}"
    ) -> 'PromptComposer':
        """Add context injection."""
        self.components.append(ContextInjector(
            context_key=context_key,
            format_template=format_template
        ))
        return self

    def add_examples(
        self,
        examples: List[Dict[str, str]]
    ) -> 'PromptComposer':
        """Add few-shot examples."""
        self.components.append(ExamplesComponent(examples=examples))
        return self

    def set_output_format(
        self,
        format_type: OutputFormat,
        schema: Dict[str, Any] = None
    ) -> 'PromptComposer':
        """Set output format."""
        self.components.append(OutputInstructions(
            format_type=format_type,
            schema=schema
        ))
        return self

    def compose(
        self,
        task: str,
        context: Dict[str, Any] = None,
        strategy: PromptStrategy = PromptStrategy.DIRECT
    ) -> List[PromptMessage]:
        """Compose final prompt."""
        context = context or {}

        # Use strategy builder if available
        if strategy in self.strategy_builders:
            return self.strategy_builders[strategy].build(task, context)

        # Manual composition
        messages = []

        # Render all components for system message
        system_parts = []
        for component in self.components:
            rendered = component.render(context)
            if rendered:
                system_parts.append(rendered)

        if system_parts:
            messages.append(PromptMessage(
                role=PromptRole.SYSTEM,
                content="\n\n".join(system_parts)
            ))

        # Add user task
        messages.append(PromptMessage(
            role=PromptRole.USER,
            content=task
        ))

        return messages


# =============================================================================
# PROMPT OPTIMIZER
# =============================================================================

class PromptOptimizer:
    """Optimize prompts for better performance."""

    def __init__(self):
        self.optimizations: List[Callable[[str], str]] = [
            self._remove_redundancy,
            self._clarify_instructions,
            self._add_structure,
            self._optimize_length
        ]

    def optimize(
        self,
        prompt: str,
        target_tokens: int = None,
        context: Dict[str, Any] = None
    ) -> str:
        """Optimize prompt."""
        result = prompt

        for optimization in self.optimizations:
            result = optimization(result)

        if target_tokens:
            result = self._fit_tokens(result, target_tokens)

        return result

    def _remove_redundancy(self, prompt: str) -> str:
        """Remove redundant phrases."""
        redundant = [
            r"\bplease\b",
            r"\bkindly\b",
            r"\bI would like you to\b",
            r"\bcan you\b",
            r"\bwould you\b"
        ]

        result = prompt
        for pattern in redundant:
            result = re.sub(pattern, "", result, flags=re.IGNORECASE)

        # Clean up extra spaces
        result = re.sub(r"\s+", " ", result)
        return result.strip()

    def _clarify_instructions(self, prompt: str) -> str:
        """Make instructions more specific."""
        # Add specificity markers if missing
        if "respond" in prompt.lower() and "format" not in prompt.lower():
            prompt += "\nBe specific and detailed in your response."
        return prompt

    def _add_structure(self, prompt: str) -> str:
        """Add structural elements."""
        # If long prompt without clear sections, add structure
        if len(prompt) > 500 and "\n\n" not in prompt:
            # Try to identify sections and add breaks
            prompt = re.sub(r"\. ([A-Z])", r".\n\n\1", prompt)
        return prompt

    def _optimize_length(self, prompt: str) -> str:
        """Optimize prompt length."""
        # Remove excessive whitespace
        prompt = re.sub(r"\n{3,}", "\n\n", prompt)
        prompt = re.sub(r"[ \t]+", " ", prompt)
        return prompt.strip()

    def _fit_tokens(self, prompt: str, target: int) -> str:
        """Fit prompt to target token count."""
        # Rough estimation: 4 chars per token
        current_estimate = len(prompt) // 4

        if current_estimate > target:
            # Truncate intelligently
            ratio = target / current_estimate
            target_len = int(len(prompt) * ratio * 0.9)  # 10% margin
            prompt = prompt[:target_len] + "..."

        return prompt


# =============================================================================
# PROMPT LIBRARY
# =============================================================================

class PromptLibrary:
    """Library of reusable prompt templates."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.templates: Dict[str, PromptTemplate] = {}
        self.stats: Dict[str, PromptStats] = {}
        self.storage_path = storage_path
        self._init_builtin_templates()

    def _init_builtin_templates(self) -> None:
        """Initialize built-in templates."""
        builtins = [
            PromptTemplate(
                id="analyze_code",
                name="Code Analysis",
                template="""Analyze the following code:

```{language}
{code}
```

Provide:
1. Summary of what the code does
2. Potential issues or bugs
3. Suggestions for improvement""",
                variables=["language", "code"],
                strategy=PromptStrategy.CHAIN_OF_THOUGHT,
                output_format=OutputFormat.MARKDOWN
            ),
            PromptTemplate(
                id="summarize",
                name="Text Summarization",
                template="""Summarize the following text in {style} style:

{text}

Target length: {length}""",
                variables=["text", "style", "length"],
                strategy=PromptStrategy.DIRECT,
                output_format=OutputFormat.TEXT
            ),
            PromptTemplate(
                id="explain",
                name="Concept Explanation",
                template="""Explain {concept} in {complexity} terms.

Target audience: {audience}

Include examples and analogies where helpful.""",
                variables=["concept", "complexity", "audience"],
                strategy=PromptStrategy.CHAIN_OF_THOUGHT,
                output_format=OutputFormat.MARKDOWN
            ),
            PromptTemplate(
                id="generate_code",
                name="Code Generation",
                template="""Generate {language} code that:

{requirements}

Requirements:
- Follow best practices
- Include error handling
- Add comments for clarity""",
                variables=["language", "requirements"],
                strategy=PromptStrategy.DIRECT,
                output_format=OutputFormat.CODE
            ),
            PromptTemplate(
                id="review_and_improve",
                name="Review and Improve",
                template="""Review the following {type}:

{content}

Provide:
1. Strengths
2. Weaknesses
3. Specific improvements
4. Revised version""",
                variables=["type", "content"],
                strategy=PromptStrategy.CHAIN_OF_THOUGHT,
                output_format=OutputFormat.STRUCTURED
            )
        ]

        for template in builtins:
            self.templates[template.id] = template

    def add_template(self, template: PromptTemplate) -> None:
        """Add template to library."""
        self.templates[template.id] = template
        self.stats[template.id] = PromptStats(template_id=template.id)

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """Get template by ID."""
        return self.templates.get(template_id)

    def render_template(
        self,
        template_id: str,
        **kwargs
    ) -> Optional[str]:
        """Render template with variables."""
        template = self.templates.get(template_id)
        if not template:
            return None

        # Update stats
        if template_id not in self.stats:
            self.stats[template_id] = PromptStats(template_id=template_id)
        self.stats[template_id].total_uses += 1
        self.stats[template_id].last_used = datetime.now()

        return template.render(**kwargs)

    def search_templates(
        self,
        query: str,
        strategy: PromptStrategy = None
    ) -> List[PromptTemplate]:
        """Search templates."""
        results = []
        query_lower = query.lower()

        for template in self.templates.values():
            score = 0

            if query_lower in template.name.lower():
                score += 3
            if query_lower in template.description.lower():
                score += 2
            if query_lower in template.template.lower():
                score += 1

            if strategy and template.strategy == strategy:
                score += 2

            if score > 0:
                results.append((template, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return [t for t, _ in results]

    def get_popular_templates(self, limit: int = 5) -> List[PromptTemplate]:
        """Get most used templates."""
        sorted_stats = sorted(
            self.stats.values(),
            key=lambda s: s.total_uses,
            reverse=True
        )[:limit]

        return [
            self.templates[s.template_id]
            for s in sorted_stats
            if s.template_id in self.templates
        ]

    def save(self, path: Path = None) -> None:
        """Save library to file."""
        path = path or self.storage_path
        if not path:
            return

        data = {
            "templates": {
                tid: {
                    "id": t.id,
                    "name": t.name,
                    "template": t.template,
                    "variables": t.variables,
                    "description": t.description,
                    "strategy": t.strategy.value,
                    "output_format": t.output_format.value,
                    "examples": t.examples,
                    "version": t.version
                }
                for tid, t in self.templates.items()
            },
            "stats": {
                tid: {
                    "total_uses": s.total_uses,
                    "avg_tokens": s.avg_tokens,
                    "success_rate": s.success_rate
                }
                for tid, s in self.stats.items()
            }
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)


# =============================================================================
# CONVERSATION MANAGER
# =============================================================================

class ConversationManager:
    """Manage multi-turn conversations."""

    def __init__(
        self,
        max_history: int = 20,
        max_tokens: int = 4000
    ):
        self.conversations: Dict[str, List[PromptMessage]] = {}
        self.max_history = max_history
        self.max_tokens = max_tokens

    def create_conversation(
        self,
        conversation_id: str = None,
        system_prompt: str = None
    ) -> str:
        """Create new conversation."""
        conv_id = conversation_id or str(uuid4())
        self.conversations[conv_id] = []

        if system_prompt:
            self.conversations[conv_id].append(PromptMessage(
                role=PromptRole.SYSTEM,
                content=system_prompt
            ))

        return conv_id

    def add_message(
        self,
        conversation_id: str,
        role: PromptRole,
        content: str
    ) -> None:
        """Add message to conversation."""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []

        self.conversations[conversation_id].append(PromptMessage(
            role=role,
            content=content
        ))

        # Trim if needed
        self._trim_conversation(conversation_id)

    def get_messages(
        self,
        conversation_id: str
    ) -> List[PromptMessage]:
        """Get conversation messages."""
        return self.conversations.get(conversation_id, [])

    def _trim_conversation(self, conversation_id: str) -> None:
        """Trim conversation to fit limits."""
        messages = self.conversations[conversation_id]

        # Keep system message if present
        system_msg = None
        if messages and messages[0].role == PromptRole.SYSTEM:
            system_msg = messages[0]
            messages = messages[1:]

        # Trim by count
        if len(messages) > self.max_history:
            messages = messages[-self.max_history:]

        # Trim by tokens (rough estimate)
        total_chars = sum(len(m.content) for m in messages)
        while total_chars > self.max_tokens * 4 and len(messages) > 2:
            messages.pop(0)
            total_chars = sum(len(m.content) for m in messages)

        # Restore system message
        if system_msg:
            messages.insert(0, system_msg)

        self.conversations[conversation_id] = messages

    def summarize_conversation(
        self,
        conversation_id: str
    ) -> str:
        """Generate conversation summary."""
        messages = self.get_messages(conversation_id)

        if not messages:
            return "Empty conversation"

        lines = []
        for msg in messages[-10:]:  # Last 10 messages
            role = msg.role.value.capitalize()
            content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            lines.append(f"{role}: {content}")

        return "\n".join(lines)

    def clear_conversation(self, conversation_id: str) -> None:
        """Clear conversation history."""
        if conversation_id in self.conversations:
            # Keep system message if present
            messages = self.conversations[conversation_id]
            if messages and messages[0].role == PromptRole.SYSTEM:
                self.conversations[conversation_id] = [messages[0]]
            else:
                self.conversations[conversation_id] = []


# =============================================================================
# PROMPT ENGINEERING SYSTEM
# =============================================================================

class PromptEngineeringSystem:
    """Main prompt engineering system."""

    def __init__(self, library_path: Optional[Path] = None):
        self.library = PromptLibrary(library_path)
        self.composer = PromptComposer()
        self.optimizer = PromptOptimizer()
        self.conversation_manager = ConversationManager()

    def create_prompt(
        self,
        task: str,
        template_id: str = None,
        strategy: PromptStrategy = PromptStrategy.DIRECT,
        context: Dict[str, Any] = None,
        optimize: bool = True,
        **template_vars
    ) -> List[PromptMessage]:
        """Create prompt for task."""
        context = context or {}

        # Use template if specified
        if template_id:
            template = self.library.get_template(template_id)
            if template:
                rendered = template.render(**template_vars)
                if optimize:
                    rendered = self.optimizer.optimize(rendered, context=context)

                return self.composer.compose(
                    rendered,
                    context=context,
                    strategy=template.strategy
                )

        # Build from scratch
        messages = self.composer.compose(task, context, strategy)

        if optimize:
            for msg in messages:
                if msg.role == PromptRole.USER:
                    msg.content = self.optimizer.optimize(msg.content, context=context)

        return messages

    def create_conversation(
        self,
        persona: str = "helpful assistant",
        conversation_id: str = None
    ) -> str:
        """Create new conversation."""
        system = SystemPrompt(persona=persona)
        system_content = system.render({})

        return self.conversation_manager.create_conversation(
            conversation_id,
            system_content
        )

    def chat(
        self,
        conversation_id: str,
        message: str
    ) -> List[PromptMessage]:
        """Add message and get conversation context."""
        self.conversation_manager.add_message(
            conversation_id,
            PromptRole.USER,
            message
        )

        return self.conversation_manager.get_messages(conversation_id)

    def add_response(
        self,
        conversation_id: str,
        response: str
    ) -> None:
        """Add assistant response."""
        self.conversation_manager.add_message(
            conversation_id,
            PromptRole.ASSISTANT,
            response
        )

    def suggest_strategy(
        self,
        task: str
    ) -> PromptStrategy:
        """Suggest best prompting strategy for task."""
        task_lower = task.lower()

        if any(w in task_lower for w in ["step by step", "explain", "how", "why"]):
            return PromptStrategy.CHAIN_OF_THOUGHT

        if any(w in task_lower for w in ["search", "find", "look up", "act"]):
            return PromptStrategy.REACT

        if any(w in task_lower for w in ["verify", "check", "multiple", "confirm"]):
            return PromptStrategy.SELF_CONSISTENCY

        if any(w in task_lower for w in ["like", "similar", "example"]):
            return PromptStrategy.FEW_SHOT

        return PromptStrategy.DIRECT

    def get_template_stats(self) -> Dict[str, PromptStats]:
        """Get usage statistics for templates."""
        return self.library.stats


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demo prompt engineering system."""
    system = PromptEngineeringSystem()

    print("=== Prompt Engineering System Demo ===\n")

    # 1. Using templates
    print("1. Using Code Analysis Template:")
    messages = system.create_prompt(
        task="Analyze this code",
        template_id="analyze_code",
        language="python",
        code="def factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)"
    )
    for msg in messages:
        print(f"   [{msg.role.value}]: {msg.content[:100]}...")

    # 2. Chain of thought
    print("\n2. Chain of Thought Prompting:")
    messages = system.create_prompt(
        task="What is 15% of 240?",
        strategy=PromptStrategy.CHAIN_OF_THOUGHT
    )
    for msg in messages:
        print(f"   [{msg.role.value}]: {msg.content[:150]}...")

    # 3. ReAct prompting
    print("\n3. ReAct Prompting:")
    messages = system.create_prompt(
        task="Find the current weather in Tokyo",
        strategy=PromptStrategy.REACT
    )
    print(f"   System: {messages[0].content[:200]}...")

    # 4. Custom composition
    print("\n4. Custom Prompt Composition:")
    composer = PromptComposer()
    composer.set_system_prompt(
        persona="expert Python developer",
        capabilities=["code review", "debugging", "optimization"],
        constraints=["be concise", "provide examples"]
    )
    composer.set_output_format(OutputFormat.MARKDOWN)

    messages = composer.compose("Review my sorting algorithm")
    print(f"   System: {messages[0].content[:200]}...")

    # 5. Conversation management
    print("\n5. Conversation Management:")
    conv_id = system.create_conversation("coding assistant")

    messages = system.chat(conv_id, "How do I read a file in Python?")
    print(f"   Messages in conversation: {len(messages)}")

    system.add_response(conv_id, "Use the open() function with a context manager...")

    messages = system.chat(conv_id, "What about writing to a file?")
    print(f"   Messages after follow-up: {len(messages)}")

    # 6. Strategy suggestion
    print("\n6. Strategy Suggestions:")
    tasks = [
        "Explain how neural networks work",
        "Find the latest news about AI",
        "Verify if this calculation is correct"
    ]

    for task in tasks:
        strategy = system.suggest_strategy(task)
        print(f"   '{task[:40]}...' -> {strategy.value}")

    # 7. Prompt optimization
    print("\n7. Prompt Optimization:")
    original = "Please kindly can you help me analyze this code and tell me what it does?"
    optimized = system.optimizer.optimize(original)
    print(f"   Original: {original}")
    print(f"   Optimized: {optimized}")

    # 8. Template search
    print("\n8. Template Search:")
    results = system.library.search_templates("code")
    for template in results[:3]:
        print(f"   - {template.name} ({template.id})")


if __name__ == "__main__":
    asyncio.run(demo())
