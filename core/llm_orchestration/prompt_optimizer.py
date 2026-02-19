"""
BAEL Prompt Optimizer
======================

Intelligent prompt optimization for maximum effectiveness.
Automatically improves prompts for better results across providers.

Features:
- Provider-specific prompt formatting
- Context window optimization
- Token budget management
- System prompt injection
- Few-shot example selection
- Chain-of-thought formatting
- Prompt compression
- A/B testing support
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class OptimizationStrategy(Enum):
    """Prompt optimization strategies."""
    NONE = "none"                     # No optimization
    COMPRESS = "compress"             # Reduce token count
    ENHANCE = "enhance"               # Add helpful context
    PROVIDER_SPECIFIC = "provider"    # Optimize for provider
    CHAIN_OF_THOUGHT = "cot"          # Add CoT formatting
    FEW_SHOT = "few_shot"             # Add examples
    STRUCTURED = "structured"          # Add structure markers
    AGGRESSIVE = "aggressive"          # Maximum optimization


class ProviderFormat(Enum):
    """Provider-specific formatting requirements."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    MISTRAL = "mistral"
    LLAMA = "llama"
    GENERIC = "generic"


@dataclass
class OptimizedPrompt:
    """Result of prompt optimization."""
    messages: List[Dict[str, str]]
    original_tokens: int
    optimized_tokens: int
    strategy_used: OptimizationStrategy
    modifications: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PromptTemplate:
    """Reusable prompt template."""
    name: str
    template: str
    variables: List[str]
    category: str
    examples: List[Dict[str, str]] = field(default_factory=list)
    system_prompt: Optional[str] = None


class PromptOptimizer:
    """
    Optimizes prompts for maximum effectiveness.
    """

    # Provider-specific system prompt prefixes
    PROVIDER_PREFIXES = {
        ProviderFormat.ANTHROPIC: "Human: ",
        ProviderFormat.LLAMA: "[INST]",
        ProviderFormat.MISTRAL: "<s>[INST]",
    }

    # Provider-specific formatting
    PROVIDER_FORMATTING = {
        ProviderFormat.ANTHROPIC: {
            "prefer_xml": True,
            "use_human_assistant": True,
            "supports_system": True,
        },
        ProviderFormat.OPENAI: {
            "prefer_markdown": True,
            "use_system_role": True,
            "supports_json_mode": True,
        },
        ProviderFormat.DEEPSEEK: {
            "prefer_structured": True,
            "use_think_step": True,
            "supports_r1_format": True,
        },
        ProviderFormat.GOOGLE: {
            "prefer_markdown": True,
            "supports_grounding": True,
        },
    }

    # Chain of thought triggers
    COT_TRIGGERS = [
        "Let's think step by step.",
        "Let me work through this carefully.",
        "I'll break this down systematically.",
    ]

    # Compression patterns (remove without losing meaning)
    COMPRESSION_PATTERNS = [
        (r"\s+", " "),  # Multiple spaces to single
        (r"\n\n+", "\n\n"),  # Multiple newlines to double
        (r"Please\s+", ""),  # Filler words
        (r"\s+also\s+", " "),
        (r"I would like you to\s+", ""),
        (r"Could you please\s+", ""),
        (r"Can you\s+", ""),
    ]

    def __init__(
        self,
        default_strategy: OptimizationStrategy = OptimizationStrategy.ENHANCE,
        max_context_tokens: int = 128000,
    ):
        self.default_strategy = default_strategy
        self.max_context_tokens = max_context_tokens

        # Template library
        self.templates: Dict[str, PromptTemplate] = {}

        # A/B testing variants
        self.variants: Dict[str, List[str]] = {}

        # Performance tracking
        self.performance: Dict[str, Dict[str, float]] = {}

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count."""
        return len(text) // 4

    def _count_message_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens in message list."""
        total = 0
        for msg in messages:
            total += self._estimate_tokens(msg.get("content", ""))
            total += 4  # Role overhead
        return total

    def _compress_text(self, text: str) -> str:
        """Apply compression patterns to reduce token count."""
        result = text
        for pattern, replacement in self.COMPRESSION_PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result.strip()

    def _add_chain_of_thought(
        self,
        messages: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        """Add chain of thought prompting."""
        result = messages.copy()

        # Find last user message
        for i in range(len(result) - 1, -1, -1):
            if result[i]["role"] == "user":
                # Append CoT trigger
                result[i]["content"] += "\n\n" + self.COT_TRIGGERS[0]
                break

        return result

    def _add_structure_markers(
        self,
        messages: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        """Add structure markers for better parsing."""
        result = messages.copy()

        # Find last user message
        for i in range(len(result) - 1, -1, -1):
            if result[i]["role"] == "user":
                content = result[i]["content"]

                # Add structure if not already present
                if not any(marker in content for marker in ["##", "```", "<", "1.", "-"]):
                    # Try to identify sections
                    lines = content.split("\n")
                    if len(lines) > 3:
                        # Add markdown headers
                        structured = "## Request\n" + content
                        structured += "\n\n## Expected Output\nProvide a comprehensive response."
                        result[i]["content"] = structured
                break

        return result

    def _format_for_provider(
        self,
        messages: List[Dict[str, str]],
        provider: ProviderFormat,
    ) -> List[Dict[str, str]]:
        """Format messages for specific provider."""
        result = messages.copy()
        formatting = self.PROVIDER_FORMATTING.get(provider, {})

        if provider == ProviderFormat.ANTHROPIC:
            # Ensure system message is first
            has_system = any(m["role"] == "system" for m in result)
            if not has_system:
                result.insert(0, {
                    "role": "system",
                    "content": "You are a helpful AI assistant."
                })

            # Convert to XML-style if complex
            for msg in result:
                content = msg["content"]
                if len(content) > 500 and "<" not in content:
                    # Wrap in XML tags
                    msg["content"] = f"<request>\n{content}\n</request>"

        elif provider == ProviderFormat.DEEPSEEK:
            # Add thinking step for R1
            for i, msg in enumerate(result):
                if msg["role"] == "user":
                    content = msg["content"]
                    if "think" not in content.lower() and "step" not in content.lower():
                        result[i]["content"] = content + "\n\nThink through this carefully before responding."

        return result

    def _truncate_to_context(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        preserve_recent: int = 3,
    ) -> List[Dict[str, str]]:
        """Truncate messages to fit context window."""
        total_tokens = self._count_message_tokens(messages)

        if total_tokens <= max_tokens:
            return messages

        # Preserve system message and recent messages
        system_msg = None
        if messages[0]["role"] == "system":
            system_msg = messages[0]
            messages = messages[1:]

        # Keep last N messages
        recent = messages[-preserve_recent:]
        older = messages[:-preserve_recent]

        # Truncate older messages
        result = []
        if system_msg:
            result.append(system_msg)

        available = max_tokens - self._count_message_tokens(result + recent)

        for msg in older:
            msg_tokens = self._estimate_tokens(msg.get("content", ""))
            if msg_tokens <= available:
                result.append(msg)
                available -= msg_tokens
            else:
                # Truncate content
                truncated = msg.copy()
                truncated["content"] = msg["content"][:available * 4] + "... [truncated]"
                result.append(truncated)
                break

        result.extend(recent)
        return result

    def optimize(
        self,
        messages: List[Dict[str, str]],
        strategy: Optional[OptimizationStrategy] = None,
        provider: Optional[ProviderFormat] = None,
        max_tokens: Optional[int] = None,
    ) -> OptimizedPrompt:
        """
        Optimize messages for better results.

        Args:
            messages: Input messages
            strategy: Optimization strategy
            provider: Target provider format
            max_tokens: Maximum context tokens

        Returns:
            OptimizedPrompt with optimized messages
        """
        strategy = strategy or self.default_strategy
        max_tokens = max_tokens or self.max_context_tokens
        provider = provider or ProviderFormat.GENERIC

        original_tokens = self._count_message_tokens(messages)
        modifications = []
        result = [m.copy() for m in messages]

        if strategy == OptimizationStrategy.NONE:
            return OptimizedPrompt(
                messages=result,
                original_tokens=original_tokens,
                optimized_tokens=original_tokens,
                strategy_used=strategy,
                modifications=[],
            )

        if strategy in (OptimizationStrategy.COMPRESS, OptimizationStrategy.AGGRESSIVE):
            # Compress text
            for msg in result:
                original = msg["content"]
                compressed = self._compress_text(original)
                if compressed != original:
                    msg["content"] = compressed
                    modifications.append("Compressed text")

        if strategy in (OptimizationStrategy.ENHANCE, OptimizationStrategy.AGGRESSIVE):
            # Ensure system prompt exists
            has_system = any(m["role"] == "system" for m in result)
            if not has_system:
                result.insert(0, {
                    "role": "system",
                    "content": "You are an expert AI assistant. Provide detailed, accurate, and helpful responses."
                })
                modifications.append("Added system prompt")

        if strategy in (OptimizationStrategy.CHAIN_OF_THOUGHT, OptimizationStrategy.AGGRESSIVE):
            result = self._add_chain_of_thought(result)
            modifications.append("Added chain of thought")

        if strategy in (OptimizationStrategy.STRUCTURED, OptimizationStrategy.AGGRESSIVE):
            result = self._add_structure_markers(result)
            modifications.append("Added structure markers")

        if strategy == OptimizationStrategy.PROVIDER_SPECIFIC or provider != ProviderFormat.GENERIC:
            result = self._format_for_provider(result, provider)
            modifications.append(f"Formatted for {provider.value}")

        # Always truncate if needed
        result = self._truncate_to_context(result, max_tokens)

        optimized_tokens = self._count_message_tokens(result)

        if optimized_tokens < original_tokens:
            modifications.append(f"Reduced tokens: {original_tokens} → {optimized_tokens}")

        return OptimizedPrompt(
            messages=result,
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            strategy_used=strategy,
            modifications=modifications,
        )

    def add_template(self, template: PromptTemplate) -> None:
        """Add a reusable prompt template."""
        self.templates[template.name] = template

    def render_template(
        self,
        name: str,
        variables: Dict[str, str],
    ) -> Optional[str]:
        """Render a template with variables."""
        if name not in self.templates:
            return None

        template = self.templates[name]
        result = template.template

        for var in template.variables:
            if var in variables:
                result = result.replace(f"{{{var}}}", variables[var])

        return result

    def create_few_shot(
        self,
        task: str,
        examples: List[Tuple[str, str]],
        query: str,
    ) -> List[Dict[str, str]]:
        """Create few-shot prompt with examples."""
        messages = [
            {
                "role": "system",
                "content": f"You are an expert at {task}. Learn from the examples provided."
            }
        ]

        for input_text, output_text in examples:
            messages.append({"role": "user", "content": input_text})
            messages.append({"role": "assistant", "content": output_text})

        messages.append({"role": "user", "content": query})

        return messages


def demo():
    """Demonstrate prompt optimization."""
    print("=" * 60)
    print("BAEL Prompt Optimizer Demo")
    print("=" * 60)

    optimizer = PromptOptimizer()

    # Test optimization
    messages = [
        {"role": "user", "content": "Could you please help me write a Python function that can sort a list of numbers? I would also like you to explain how it works."}
    ]

    result = optimizer.optimize(
        messages,
        strategy=OptimizationStrategy.AGGRESSIVE,
        provider=ProviderFormat.ANTHROPIC,
    )

    print(f"\nOriginal tokens: {result.original_tokens}")
    print(f"Optimized tokens: {result.optimized_tokens}")
    print(f"Modifications: {result.modifications}")
    print(f"\nOptimized messages:")
    for msg in result.messages:
        print(f"  [{msg['role']}]: {msg['content'][:100]}...")


if __name__ == "__main__":
    demo()
