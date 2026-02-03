"""
BAEL - Advanced Prompt Engineering System
Dynamic prompt generation, optimization, and management.

Features:
- Template-based prompt construction
- Dynamic prompt optimization
- Multi-turn context management
- Persona injection
- Chain-of-thought prompting
- Prompt versioning and A/B testing
"""

import asyncio
import hashlib
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS & TYPES
# =============================================================================

class PromptStyle(Enum):
    """Styles of prompting."""
    DIRECT = "direct"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    TREE_OF_THOUGHT = "tree_of_thought"
    SOCRATIC = "socratic"
    STEP_BY_STEP = "step_by_step"
    FEW_SHOT = "few_shot"
    ZERO_SHOT = "zero_shot"
    SELF_CONSISTENCY = "self_consistency"
    REACT = "react"  # Reasoning + Acting


class PromptRole(Enum):
    """Roles in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    FUNCTION = "function"


class PromptSection(Enum):
    """Sections of a structured prompt."""
    IDENTITY = "identity"
    CONTEXT = "context"
    INSTRUCTIONS = "instructions"
    CONSTRAINTS = "constraints"
    EXAMPLES = "examples"
    FORMAT = "format"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    TASK = "task"
    OUTPUT = "output"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PromptTemplate:
    """A reusable prompt template."""
    id: str
    name: str
    template: str
    variables: List[str]
    style: PromptStyle = PromptStyle.DIRECT
    version: str = "1.0.0"
    description: str = ""
    examples: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def render(self, **kwargs) -> str:
        """Render the template with given values."""
        result = self.template
        for var in self.variables:
            placeholder = f"{{{var}}}"
            value = kwargs.get(var, "")
            result = result.replace(placeholder, str(value))
        return result

    def validate(self, **kwargs) -> List[str]:
        """Validate that all required variables are provided."""
        missing = []
        for var in self.variables:
            if var not in kwargs or kwargs[var] is None:
                missing.append(var)
        return missing


@dataclass
class PromptMessage:
    """A single message in a prompt."""
    role: PromptRole
    content: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        msg = {
            "role": self.role.value,
            "content": self.content
        }
        if self.name:
            msg["name"] = self.name
        return msg


@dataclass
class PromptChain:
    """A chain of prompts for multi-step reasoning."""
    id: str
    name: str
    steps: List[PromptTemplate]
    aggregation: str = "sequential"  # sequential, parallel, conditional

    async def execute(
        self,
        initial_context: Dict[str, Any],
        executor: Callable
    ) -> Dict[str, Any]:
        """Execute the prompt chain."""
        context = initial_context.copy()
        results = []

        for i, step in enumerate(self.steps):
            prompt = step.render(**context)
            result = await executor(prompt)
            results.append(result)
            context[f"step_{i}_result"] = result

        return {
            "final_result": results[-1] if results else None,
            "all_results": results,
            "context": context
        }


@dataclass
class PromptVersion:
    """A version of a prompt for A/B testing."""
    id: str
    template_id: str
    variant: str  # A, B, C, etc.
    template: str
    metrics: Dict[str, float] = field(default_factory=dict)
    usage_count: int = 0
    success_count: int = 0

    @property
    def success_rate(self) -> float:
        return self.success_count / self.usage_count if self.usage_count > 0 else 0.0


# =============================================================================
# PROMPT BUILDER
# =============================================================================

class PromptBuilder:
    """Fluent builder for constructing prompts."""

    def __init__(self):
        self._sections: Dict[PromptSection, str] = {}
        self._messages: List[PromptMessage] = []
        self._examples: List[Dict[str, str]] = []
        self._constraints: List[str] = []
        self._style: PromptStyle = PromptStyle.DIRECT

    def identity(self, text: str) -> "PromptBuilder":
        """Set the identity/persona section."""
        self._sections[PromptSection.IDENTITY] = text
        return self

    def context(self, text: str) -> "PromptBuilder":
        """Set the context section."""
        self._sections[PromptSection.CONTEXT] = text
        return self

    def instructions(self, text: str) -> "PromptBuilder":
        """Set the main instructions."""
        self._sections[PromptSection.INSTRUCTIONS] = text
        return self

    def task(self, text: str) -> "PromptBuilder":
        """Set the specific task."""
        self._sections[PromptSection.TASK] = text
        return self

    def add_constraint(self, constraint: str) -> "PromptBuilder":
        """Add a constraint."""
        self._constraints.append(constraint)
        return self

    def add_example(
        self,
        input_text: str,
        output_text: str,
        explanation: Optional[str] = None
    ) -> "PromptBuilder":
        """Add an example."""
        example = {
            "input": input_text,
            "output": output_text
        }
        if explanation:
            example["explanation"] = explanation
        self._examples.append(example)
        return self

    def output_format(self, format_desc: str) -> "PromptBuilder":
        """Specify output format."""
        self._sections[PromptSection.FORMAT] = format_desc
        return self

    def style(self, style: PromptStyle) -> "PromptBuilder":
        """Set the prompting style."""
        self._style = style
        return self

    def add_message(
        self,
        role: PromptRole,
        content: str,
        name: Optional[str] = None
    ) -> "PromptBuilder":
        """Add a message (for chat-style prompts)."""
        self._messages.append(PromptMessage(role=role, content=content, name=name))
        return self

    def system(self, content: str) -> "PromptBuilder":
        """Add system message."""
        return self.add_message(PromptRole.SYSTEM, content)

    def user(self, content: str) -> "PromptBuilder":
        """Add user message."""
        return self.add_message(PromptRole.USER, content)

    def assistant(self, content: str) -> "PromptBuilder":
        """Add assistant message."""
        return self.add_message(PromptRole.ASSISTANT, content)

    def build(self) -> str:
        """Build the final prompt string."""
        parts = []

        # Identity
        if PromptSection.IDENTITY in self._sections:
            parts.append(self._sections[PromptSection.IDENTITY])
            parts.append("")

        # Context
        if PromptSection.CONTEXT in self._sections:
            parts.append("## Context")
            parts.append(self._sections[PromptSection.CONTEXT])
            parts.append("")

        # Instructions
        if PromptSection.INSTRUCTIONS in self._sections:
            parts.append("## Instructions")
            parts.append(self._sections[PromptSection.INSTRUCTIONS])
            parts.append("")

        # Constraints
        if self._constraints:
            parts.append("## Constraints")
            for i, constraint in enumerate(self._constraints, 1):
                parts.append(f"{i}. {constraint}")
            parts.append("")

        # Examples
        if self._examples:
            parts.append("## Examples")
            for i, example in enumerate(self._examples, 1):
                parts.append(f"### Example {i}")
                parts.append(f"Input: {example['input']}")
                if "explanation" in example:
                    parts.append(f"Reasoning: {example['explanation']}")
                parts.append(f"Output: {example['output']}")
                parts.append("")

        # Chain of thought
        if self._style == PromptStyle.CHAIN_OF_THOUGHT:
            parts.append("## Thinking Process")
            parts.append("Please think through this step by step:")
            parts.append("1. First, understand the problem")
            parts.append("2. Break it down into smaller parts")
            parts.append("3. Solve each part")
            parts.append("4. Combine for final answer")
            parts.append("")

        # Output format
        if PromptSection.FORMAT in self._sections:
            parts.append("## Output Format")
            parts.append(self._sections[PromptSection.FORMAT])
            parts.append("")

        # Task
        if PromptSection.TASK in self._sections:
            parts.append("## Task")
            parts.append(self._sections[PromptSection.TASK])

        return "\n".join(parts)

    def build_messages(self) -> List[Dict[str, Any]]:
        """Build chat-style messages."""
        if self._messages:
            return [msg.to_dict() for msg in self._messages]

        # Convert sections to messages
        messages = []

        # System message from identity + instructions
        system_parts = []
        if PromptSection.IDENTITY in self._sections:
            system_parts.append(self._sections[PromptSection.IDENTITY])
        if PromptSection.INSTRUCTIONS in self._sections:
            system_parts.append(self._sections[PromptSection.INSTRUCTIONS])
        if self._constraints:
            system_parts.append("Constraints:\n" + "\n".join(f"- {c}" for c in self._constraints))

        if system_parts:
            messages.append({
                "role": "system",
                "content": "\n\n".join(system_parts)
            })

        # Examples as conversation
        for example in self._examples:
            messages.append({
                "role": "user",
                "content": example["input"]
            })
            messages.append({
                "role": "assistant",
                "content": example["output"]
            })

        # User message from task
        if PromptSection.TASK in self._sections:
            messages.append({
                "role": "user",
                "content": self._sections[PromptSection.TASK]
            })

        return messages


# =============================================================================
# PROMPT LIBRARY
# =============================================================================

class PromptLibrary:
    """Library of reusable prompts and templates."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("prompts")
        self.templates: Dict[str, PromptTemplate] = {}
        self.chains: Dict[str, PromptChain] = {}
        self.versions: Dict[str, List[PromptVersion]] = {}

        self._load_builtin_templates()

    def _load_builtin_templates(self) -> None:
        """Load built-in prompt templates."""
        # Code generation template
        self.add_template(PromptTemplate(
            id="code_gen",
            name="Code Generation",
            template="""You are an expert programmer.

Task: {task}
Language: {language}
Requirements:
{requirements}

Generate clean, well-documented code that:
- Follows best practices for {language}
- Includes error handling
- Is properly formatted
- Has inline comments explaining complex logic

```{language}
""",
            variables=["task", "language", "requirements"],
            style=PromptStyle.DIRECT
        ))

        # Analysis template
        self.add_template(PromptTemplate(
            id="analysis",
            name="Analysis",
            template="""Analyze the following:

{content}

Please provide:
1. Summary
2. Key findings
3. Recommendations

Format your response as structured markdown.""",
            variables=["content"],
            style=PromptStyle.STEP_BY_STEP
        ))

        # Chain of thought template
        self.add_template(PromptTemplate(
            id="cot_reasoning",
            name="Chain of Thought Reasoning",
            template="""Let's solve this problem step by step.

Problem: {problem}

Step 1: Understand what we're being asked
Step 2: Identify the key information
Step 3: Plan our approach
Step 4: Execute the solution
Step 5: Verify our answer

Begin your reasoning:""",
            variables=["problem"],
            style=PromptStyle.CHAIN_OF_THOUGHT
        ))

        # ReAct template
        self.add_template(PromptTemplate(
            id="react",
            name="ReAct (Reasoning + Acting)",
            template="""You have access to the following tools:
{tools}

Use the following format:

Thought: I need to think about what to do
Action: the action to take, one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (repeat Thought/Action/Observation as needed)
Thought: I now know the final answer
Final Answer: the final answer to the original question

Question: {question}

Begin!

Thought:""",
            variables=["tools", "tool_names", "question"],
            style=PromptStyle.REACT
        ))

        # Self-consistency template
        self.add_template(PromptTemplate(
            id="self_consistency",
            name="Self-Consistency",
            template="""Solve this problem {n_paths} different ways, then identify the most consistent answer.

Problem: {problem}

For each approach:
1. State your reasoning path
2. Arrive at an answer
3. Rate your confidence (1-10)

After all paths, select the most consistent answer.""",
            variables=["problem", "n_paths"],
            style=PromptStyle.SELF_CONSISTENCY
        ))

    def add_template(self, template: PromptTemplate) -> None:
        """Add a template to the library."""
        self.templates[template.id] = template

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """Get a template by ID."""
        return self.templates.get(template_id)

    def create_chain(
        self,
        name: str,
        template_ids: List[str]
    ) -> PromptChain:
        """Create a prompt chain from templates."""
        templates = [self.templates[tid] for tid in template_ids if tid in self.templates]
        chain = PromptChain(
            id=hashlib.md5(name.encode()).hexdigest()[:12],
            name=name,
            steps=templates
        )
        self.chains[chain.id] = chain
        return chain

    def create_version(
        self,
        template_id: str,
        variant: str,
        new_template: str
    ) -> PromptVersion:
        """Create a version of a template for A/B testing."""
        version = PromptVersion(
            id=hashlib.md5(f"{template_id}:{variant}".encode()).hexdigest()[:12],
            template_id=template_id,
            variant=variant,
            template=new_template
        )

        if template_id not in self.versions:
            self.versions[template_id] = []
        self.versions[template_id].append(version)

        return version

    def get_best_version(self, template_id: str) -> Optional[PromptVersion]:
        """Get the best performing version of a template."""
        versions = self.versions.get(template_id, [])
        if not versions:
            return None

        # Filter versions with sufficient usage
        qualified = [v for v in versions if v.usage_count >= 10]
        if not qualified:
            return versions[0]  # Return first if none qualified

        return max(qualified, key=lambda v: v.success_rate)


# =============================================================================
# PROMPT OPTIMIZER
# =============================================================================

class PromptOptimizer:
    """Optimizes prompts based on performance data."""

    def __init__(self, library: PromptLibrary):
        self.library = library
        self.optimization_history: List[Dict[str, Any]] = []

    async def optimize_template(
        self,
        template_id: str,
        feedback_data: List[Dict[str, Any]]
    ) -> PromptTemplate:
        """Optimize a template based on feedback."""
        template = self.library.get_template(template_id)
        if not template:
            raise ValueError(f"Unknown template: {template_id}")

        # Analyze feedback
        analysis = self._analyze_feedback(feedback_data)

        # Generate optimization suggestions
        suggestions = await self._generate_suggestions(template, analysis)

        # Apply optimizations
        optimized = self._apply_optimizations(template, suggestions)

        self.optimization_history.append({
            "template_id": template_id,
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis,
            "suggestions": suggestions
        })

        return optimized

    def _analyze_feedback(
        self,
        feedback_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze feedback data for patterns."""
        analysis = {
            "total_samples": len(feedback_data),
            "success_rate": 0.0,
            "common_issues": [],
            "improvement_areas": []
        }

        if not feedback_data:
            return analysis

        # Calculate success rate
        successes = sum(1 for f in feedback_data if f.get("success", False))
        analysis["success_rate"] = successes / len(feedback_data)

        # Find common issues
        issues: Dict[str, int] = {}
        for item in feedback_data:
            if not item.get("success"):
                issue = item.get("issue", "unknown")
                issues[issue] = issues.get(issue, 0) + 1

        analysis["common_issues"] = sorted(
            issues.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return analysis

    async def _generate_suggestions(
        self,
        template: PromptTemplate,
        analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate optimization suggestions."""
        suggestions = []

        # Low success rate suggestions
        if analysis["success_rate"] < 0.7:
            suggestions.append("Add more specific examples")
            suggestions.append("Clarify constraints")
            suggestions.append("Break down complex instructions")

        # Issue-based suggestions
        for issue, count in analysis.get("common_issues", []):
            if "format" in issue.lower():
                suggestions.append("Provide explicit output format specification")
            if "unclear" in issue.lower():
                suggestions.append("Add step-by-step breakdown")
            if "incomplete" in issue.lower():
                suggestions.append("Request confirmation of understanding")

        return suggestions

    def _apply_optimizations(
        self,
        template: PromptTemplate,
        suggestions: List[str]
    ) -> PromptTemplate:
        """Apply optimization suggestions to template."""
        new_template = template.template

        for suggestion in suggestions:
            if "examples" in suggestion.lower():
                new_template += "\n\n[Include relevant examples here]"
            if "format" in suggestion.lower():
                new_template += "\n\n## Output Format\n[Specify expected format]"
            if "step-by-step" in suggestion.lower():
                new_template = "Let's approach this step by step.\n\n" + new_template

        return PromptTemplate(
            id=f"{template.id}_optimized",
            name=f"{template.name} (Optimized)",
            template=new_template,
            variables=template.variables,
            style=template.style,
            version=f"{template.version}.optimized",
            description=f"Optimized version of {template.name}"
        )


# =============================================================================
# CONTEXT MANAGER
# =============================================================================

class PromptContextManager:
    """Manages context for multi-turn conversations."""

    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self.context_window: List[PromptMessage] = []
        self.summary_buffer: List[str] = []
        self.important_facts: Set[str] = set()

    def add_message(self, message: PromptMessage) -> None:
        """Add a message to context."""
        self.context_window.append(message)
        self._prune_if_needed()

    def add_user_message(self, content: str) -> None:
        """Add a user message."""
        self.add_message(PromptMessage(role=PromptRole.USER, content=content))

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message."""
        self.add_message(PromptMessage(role=PromptRole.ASSISTANT, content=content))

    def add_important_fact(self, fact: str) -> None:
        """Mark a fact as important to preserve."""
        self.important_facts.add(fact)

    def get_context(self) -> List[Dict[str, Any]]:
        """Get current context as messages."""
        return [msg.to_dict() for msg in self.context_window]

    def get_context_string(self) -> str:
        """Get context as a single string."""
        parts = []

        # Include summaries
        if self.summary_buffer:
            parts.append("Previous conversation summary:")
            parts.extend(self.summary_buffer)
            parts.append("")

        # Include important facts
        if self.important_facts:
            parts.append("Important context:")
            parts.extend(f"- {fact}" for fact in self.important_facts)
            parts.append("")

        # Include recent messages
        for msg in self.context_window:
            role = msg.role.value.capitalize()
            parts.append(f"{role}: {msg.content}")

        return "\n".join(parts)

    def _prune_if_needed(self) -> None:
        """Prune context if too long."""
        # Estimate token count (rough: 4 chars per token)
        total_chars = sum(len(msg.content) for msg in self.context_window)
        estimated_tokens = total_chars / 4

        if estimated_tokens > self.max_tokens:
            self._summarize_and_prune()

    def _summarize_and_prune(self) -> None:
        """Summarize old messages and remove them."""
        if len(self.context_window) <= 4:
            return

        # Take first half of messages
        to_summarize = self.context_window[:len(self.context_window) // 2]
        self.context_window = self.context_window[len(self.context_window) // 2:]

        # Create summary (simplified)
        summary_parts = []
        for msg in to_summarize:
            summary_parts.append(f"{msg.role.value}: {msg.content[:100]}...")

        self.summary_buffer.append(
            f"[Earlier discussion: {len(to_summarize)} messages about "
            f"{', '.join(summary_parts[:2])}]"
        )

    def clear(self) -> None:
        """Clear all context."""
        self.context_window.clear()
        self.summary_buffer.clear()
        self.important_facts.clear()


# =============================================================================
# PERSONA INJECTOR
# =============================================================================

class PersonaInjector:
    """Injects persona characteristics into prompts."""

    def __init__(self):
        self.personas: Dict[str, Dict[str, Any]] = {}
        self._load_default_personas()

    def _load_default_personas(self) -> None:
        """Load default personas."""
        self.personas = {
            "architect": {
                "name": "System Architect",
                "traits": ["analytical", "methodical", "big-picture thinking"],
                "speaking_style": "structured and precise",
                "focus_areas": ["design patterns", "scalability", "maintainability"],
                "system_prompt": """You are a senior system architect with decades of experience.
You approach problems methodically, always considering long-term implications.
You communicate in a structured manner, often using diagrams and bullet points.
Your focus is on creating robust, scalable, and maintainable solutions."""
            },
            "coder": {
                "name": "Expert Developer",
                "traits": ["detail-oriented", "pragmatic", "efficient"],
                "speaking_style": "concise and code-focused",
                "focus_areas": ["implementation", "optimization", "best practices"],
                "system_prompt": """You are an expert software developer.
You write clean, efficient code and follow industry best practices.
You focus on practical solutions and working implementations.
Your responses include code examples when appropriate."""
            },
            "researcher": {
                "name": "Research Specialist",
                "traits": ["curious", "thorough", "academic"],
                "speaking_style": "detailed and evidence-based",
                "focus_areas": ["analysis", "synthesis", "citations"],
                "system_prompt": """You are a meticulous research specialist.
You approach topics with intellectual curiosity and rigor.
You provide evidence-based responses with citations when available.
You explore multiple perspectives before drawing conclusions."""
            },
            "teacher": {
                "name": "Patient Educator",
                "traits": ["patient", "clear", "encouraging"],
                "speaking_style": "simple and educational",
                "focus_areas": ["explanation", "examples", "understanding"],
                "system_prompt": """You are an experienced and patient educator.
You explain complex concepts in simple, understandable terms.
You use analogies, examples, and step-by-step breakdowns.
You encourage questions and celebrate learning progress."""
            },
            "debugger": {
                "name": "Debug Detective",
                "traits": ["methodical", "persistent", "analytical"],
                "speaking_style": "investigative and systematic",
                "focus_areas": ["root cause", "reproduction", "solutions"],
                "system_prompt": """You are a skilled debugging specialist.
You approach problems like a detective, gathering evidence systematically.
You ask probing questions to narrow down issues.
You consider multiple hypotheses and test them methodically."""
            }
        }

    def inject(
        self,
        prompt: str,
        persona_id: str
    ) -> str:
        """Inject persona into a prompt."""
        persona = self.personas.get(persona_id)
        if not persona:
            return prompt

        system_prompt = persona["system_prompt"]
        return f"{system_prompt}\n\n{prompt}"

    def get_system_prompt(self, persona_id: str) -> Optional[str]:
        """Get the system prompt for a persona."""
        persona = self.personas.get(persona_id)
        return persona["system_prompt"] if persona else None

    def add_persona(
        self,
        id: str,
        name: str,
        traits: List[str],
        speaking_style: str,
        focus_areas: List[str],
        system_prompt: str
    ) -> None:
        """Add a custom persona."""
        self.personas[id] = {
            "name": name,
            "traits": traits,
            "speaking_style": speaking_style,
            "focus_areas": focus_areas,
            "system_prompt": system_prompt
        }


# =============================================================================
# PROMPT ENGINE
# =============================================================================

class PromptEngine:
    """Central prompt engineering engine."""

    def __init__(self):
        self.library = PromptLibrary()
        self.optimizer = PromptOptimizer(self.library)
        self.context_manager = PromptContextManager()
        self.persona_injector = PersonaInjector()

    def builder(self) -> PromptBuilder:
        """Get a new prompt builder."""
        return PromptBuilder()

    def from_template(
        self,
        template_id: str,
        **kwargs
    ) -> str:
        """Generate prompt from template."""
        template = self.library.get_template(template_id)
        if not template:
            raise ValueError(f"Unknown template: {template_id}")

        missing = template.validate(**kwargs)
        if missing:
            raise ValueError(f"Missing variables: {missing}")

        return template.render(**kwargs)

    def with_persona(
        self,
        prompt: str,
        persona_id: str
    ) -> str:
        """Add persona to prompt."""
        return self.persona_injector.inject(prompt, persona_id)

    def with_context(self, prompt: str) -> str:
        """Add conversation context to prompt."""
        context = self.context_manager.get_context_string()
        if context:
            return f"{context}\n\n{prompt}"
        return prompt

    async def optimize(
        self,
        template_id: str,
        feedback: List[Dict[str, Any]]
    ) -> PromptTemplate:
        """Optimize a template."""
        return await self.optimizer.optimize_template(template_id, feedback)

    def create_cot_prompt(
        self,
        problem: str,
        examples: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Create a chain-of-thought prompt."""
        builder = self.builder()
        builder.style(PromptStyle.CHAIN_OF_THOUGHT)
        builder.instructions("Solve this problem step by step, showing your reasoning.")

        if examples:
            for ex in examples:
                builder.add_example(
                    ex["input"],
                    ex["output"],
                    ex.get("reasoning")
                )

        builder.task(problem)
        return builder.build()

    def create_react_prompt(
        self,
        question: str,
        tools: List[Dict[str, str]]
    ) -> str:
        """Create a ReAct (Reasoning + Acting) prompt."""
        tools_desc = "\n".join(
            f"- {t['name']}: {t['description']}"
            for t in tools
        )
        tool_names = ", ".join(t["name"] for t in tools)

        return self.from_template(
            "react",
            tools=tools_desc,
            tool_names=tool_names,
            question=question
        )


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def example_prompts():
    """Demonstrate prompt engineering capabilities."""
    engine = PromptEngine()

    # Using builder
    prompt = (
        engine.builder()
        .identity("You are a helpful coding assistant.")
        .context("The user is working on a Python project.")
        .instructions("Help the user with their coding questions.")
        .add_constraint("Always explain your code")
        .add_constraint("Follow PEP 8 style guidelines")
        .add_example(
            "How do I read a file?",
            "```python\nwith open('file.txt', 'r') as f:\n    content = f.read()\n```",
            "Using context manager ensures file is closed"
        )
        .task("Write a function to calculate factorial")
        .style(PromptStyle.CHAIN_OF_THOUGHT)
        .build()
    )

    print("Built prompt:")
    print(prompt)
    print("\n" + "="*50 + "\n")

    # Using template
    code_prompt = engine.from_template(
        "code_gen",
        task="Create a REST API endpoint",
        language="python",
        requirements="- Use FastAPI\n- Include validation\n- Return JSON"
    )

    print("Template prompt:")
    print(code_prompt)
    print("\n" + "="*50 + "\n")

    # With persona
    persona_prompt = engine.with_persona(
        "How should I structure this large application?",
        "architect"
    )

    print("Persona prompt:")
    print(persona_prompt)


if __name__ == "__main__":
    asyncio.run(example_prompts())
