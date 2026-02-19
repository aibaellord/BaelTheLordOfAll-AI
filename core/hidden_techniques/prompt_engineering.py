"""
Prompt Engineering - Maximum LLM Power
=======================================

Advanced prompt engineering techniques for optimal LLM responses.

"The prompt is the spell, and we are the master wizards." — Ba'el
"""

import re
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from string import Template

logger = logging.getLogger("BAEL.HiddenTechniques.PromptEngineer")


class PromptStyle(Enum):
    """Prompt styling approaches."""
    DIRECT = "direct"              # Straightforward instruction
    CHAIN_OF_THOUGHT = "cot"       # Step-by-step reasoning
    FEW_SHOT = "few_shot"          # Examples included
    ZERO_SHOT = "zero_shot"        # No examples
    SELF_CONSISTENCY = "self_consistency"  # Multiple paths
    TREE_OF_THOUGHT = "tot"        # Branching reasoning
    REACT = "react"                # Reasoning + Acting
    PERSONA = "persona"            # Role-based
    STRUCTURED = "structured"      # Structured output
    SOCRATIC = "socratic"          # Question-based


class OutputFormat(Enum):
    """Expected output formats."""
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    CODE = "code"
    LIST = "list"
    TABLE = "table"
    XML = "xml"
    YAML = "yaml"


class Role(Enum):
    """Personas for role-based prompting."""
    EXPERT = "expert"
    CRITIC = "critic"
    TEACHER = "teacher"
    ANALYST = "analyst"
    CREATIVE = "creative"
    DEBUGGER = "debugger"
    ARCHITECT = "architect"
    SECURITY_EXPERT = "security_expert"
    PERFORMANCE_EXPERT = "performance_expert"


@dataclass
class PromptTemplate:
    """A reusable prompt template."""
    name: str
    template: str
    style: PromptStyle = PromptStyle.DIRECT
    output_format: OutputFormat = OutputFormat.TEXT
    role: Optional[Role] = None
    variables: List[str] = field(default_factory=list)
    examples: List[Dict[str, str]] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    system_prompt: Optional[str] = None

    def render(self, **kwargs) -> str:
        """Render template with variables."""
        result = self.template

        for key, value in kwargs.items():
            result = result.replace(f"{{{key}}}", str(value))
            result = result.replace(f"${key}", str(value))

        return result


@dataclass
class PromptConfig:
    """Configuration for prompt generation."""
    style: PromptStyle = PromptStyle.DIRECT
    output_format: OutputFormat = OutputFormat.TEXT
    role: Optional[Role] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    include_examples: bool = False
    include_constraints: bool = True
    think_step_by_step: bool = False
    verify_output: bool = False


# =============================================================================
# PROMPT TEMPLATES
# =============================================================================

TEMPLATES = {
    # Code Analysis
    "code_review": PromptTemplate(
        name="code_review",
        template="""Review the following code for quality, bugs, and improvements:

```{language}
{code}
```

Provide:
1. Critical issues (bugs, security vulnerabilities)
2. Code quality concerns
3. Suggested improvements
4. Overall assessment (1-10)""",
        style=PromptStyle.STRUCTURED,
        output_format=OutputFormat.MARKDOWN,
        role=Role.EXPERT,
        variables=["language", "code"],
    ),

    # Security Audit
    "security_audit": PromptTemplate(
        name="security_audit",
        template="""As a security expert, analyze this code for vulnerabilities:

```{language}
{code}
```

Check for:
- Injection vulnerabilities (SQL, Command, XSS)
- Authentication/Authorization issues
- Hardcoded secrets
- Insecure data handling
- OWASP Top 10 violations

Output as JSON with format:
{{
    "vulnerabilities": [
        {{"type": "...", "severity": "critical|high|medium|low", "line": N, "description": "...", "fix": "..."}}
    ],
    "risk_score": 0-100,
    "summary": "..."
}}""",
        style=PromptStyle.STRUCTURED,
        output_format=OutputFormat.JSON,
        role=Role.SECURITY_EXPERT,
        variables=["language", "code"],
    ),

    # Performance Optimization
    "performance_analysis": PromptTemplate(
        name="performance_analysis",
        template="""Analyze this code for performance issues and optimization opportunities:

```{language}
{code}
```

Consider:
- Algorithm complexity (time and space)
- Memory usage
- I/O operations
- Caching opportunities
- Parallelization potential

Provide specific recommendations with expected impact.""",
        style=PromptStyle.CHAIN_OF_THOUGHT,
        output_format=OutputFormat.MARKDOWN,
        role=Role.PERFORMANCE_EXPERT,
        variables=["language", "code"],
    ),

    # Architecture Design
    "architecture_design": PromptTemplate(
        name="architecture_design",
        template="""Design a software architecture for the following requirements:

Requirements:
{requirements}

Constraints:
{constraints}

Provide:
1. High-level architecture diagram (text-based)
2. Component descriptions
3. Technology recommendations
4. Scalability considerations
5. Security considerations""",
        style=PromptStyle.TREE_OF_THOUGHT,
        output_format=OutputFormat.MARKDOWN,
        role=Role.ARCHITECT,
        variables=["requirements", "constraints"],
    ),

    # Test Generation
    "generate_tests": PromptTemplate(
        name="generate_tests",
        template="""Generate comprehensive unit tests for this code:

```{language}
{code}
```

Include:
- Happy path tests
- Edge cases
- Error handling tests
- Boundary conditions
- Mock/stub setup where needed

Use {test_framework} framework.""",
        style=PromptStyle.FEW_SHOT,
        output_format=OutputFormat.CODE,
        variables=["language", "code", "test_framework"],
        examples=[
            {
                "input": "def add(a, b): return a + b",
                "output": """def test_add_positive():
    assert add(2, 3) == 5

def test_add_negative():
    assert add(-1, -1) == -2

def test_add_zero():
    assert add(0, 0) == 0"""
            }
        ],
    ),

    # Documentation
    "generate_docs": PromptTemplate(
        name="generate_docs",
        template="""Generate comprehensive documentation for this code:

```{language}
{code}
```

Include:
- Overview/Purpose
- Parameters (with types)
- Return values
- Example usage
- Edge cases/limitations
- Related functions/classes""",
        style=PromptStyle.STRUCTURED,
        output_format=OutputFormat.MARKDOWN,
        role=Role.TEACHER,
        variables=["language", "code"],
    ),

    # Bug Finding
    "find_bugs": PromptTemplate(
        name="find_bugs",
        template="""Act as a meticulous code debugger. Find ALL bugs in this code:

```{language}
{code}
```

Think step by step:
1. First, understand what the code is trying to do
2. Trace through execution paths
3. Identify edge cases
4. Look for common bug patterns
5. Check for logic errors

For each bug, provide:
- Location (line number if possible)
- Description of the bug
- Why it's a problem
- How to fix it""",
        style=PromptStyle.CHAIN_OF_THOUGHT,
        output_format=OutputFormat.MARKDOWN,
        role=Role.DEBUGGER,
        variables=["language", "code"],
    ),

    # Refactoring
    "refactor_code": PromptTemplate(
        name="refactor_code",
        template="""Refactor this code to improve quality and maintainability:

```{language}
{code}
```

Apply:
- SOLID principles
- DRY (Don't Repeat Yourself)
- Clean Code practices
- Design patterns where appropriate
- Better naming conventions

Provide the refactored code with explanations of changes made.""",
        style=PromptStyle.CHAIN_OF_THOUGHT,
        output_format=OutputFormat.CODE,
        role=Role.EXPERT,
        variables=["language", "code"],
    ),

    # General Task
    "general_task": PromptTemplate(
        name="general_task",
        template="""{task}

{context}

Requirements:
{requirements}""",
        style=PromptStyle.DIRECT,
        output_format=OutputFormat.TEXT,
        variables=["task", "context", "requirements"],
    ),
}


# =============================================================================
# PROMPT ENGINEER
# =============================================================================

class PromptEngineer:
    """
    Advanced prompt engineering system.

    Features:
    - Template-based prompts
    - Multiple prompting styles (CoT, Few-shot, etc.)
    - Output format enforcement
    - Role/persona injection
    - Automatic optimization
    """

    def __init__(self):
        self.templates = TEMPLATES.copy()
        self._optimization_cache: Dict[str, str] = {}

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get a prompt template by name."""
        return self.templates.get(name)

    def register_template(self, template: PromptTemplate) -> None:
        """Register a custom template."""
        self.templates[template.name] = template

    def build_prompt(
        self,
        template_name: str = None,
        template: PromptTemplate = None,
        config: PromptConfig = None,
        **variables,
    ) -> str:
        """
        Build an optimized prompt.

        Args:
            template_name: Name of registered template
            template: Custom template object
            config: Prompt configuration
            **variables: Variables to fill in template

        Returns:
            Optimized prompt string
        """
        # Get template
        if template is None and template_name:
            template = self.templates.get(template_name)

        if template is None:
            template = TEMPLATES["general_task"]

        config = config or PromptConfig()

        # Build prompt parts
        parts = []

        # System/Role prompt
        if template.role or config.role:
            role = template.role or config.role
            parts.append(self._build_role_prompt(role))

        if template.system_prompt:
            parts.append(template.system_prompt)

        # Main template
        main_prompt = template.render(**variables)

        # Add examples for few-shot
        if config.include_examples and template.examples:
            examples_text = self._format_examples(template.examples)
            main_prompt = f"{examples_text}\n\n{main_prompt}"

        # Add chain-of-thought instruction
        if config.think_step_by_step or template.style == PromptStyle.CHAIN_OF_THOUGHT:
            main_prompt += "\n\nThink step by step before providing your answer."

        # Add output format instruction
        format_instruction = self._get_format_instruction(template.output_format)
        if format_instruction:
            main_prompt += f"\n\n{format_instruction}"

        # Add constraints
        if config.include_constraints and template.constraints:
            constraints_text = "\n".join(f"- {c}" for c in template.constraints)
            main_prompt += f"\n\nConstraints:\n{constraints_text}"

        # Add verification request
        if config.verify_output:
            main_prompt += "\n\nAfter your answer, verify it is correct and complete."

        parts.append(main_prompt)

        return "\n\n".join(parts)

    def build_chat_prompt(
        self,
        template_name: str = None,
        template: PromptTemplate = None,
        config: PromptConfig = None,
        **variables,
    ) -> List[Dict[str, str]]:
        """
        Build prompt as chat messages.

        Returns list of message dicts for chat API.
        """
        if template is None and template_name:
            template = self.templates.get(template_name)

        if template is None:
            template = TEMPLATES["general_task"]

        config = config or PromptConfig()
        messages = []

        # System message
        system_parts = []

        if template.role or config.role:
            role = template.role or config.role
            system_parts.append(self._build_role_prompt(role))

        if template.system_prompt:
            system_parts.append(template.system_prompt)

        format_instruction = self._get_format_instruction(template.output_format)
        if format_instruction:
            system_parts.append(format_instruction)

        if system_parts:
            messages.append({
                "role": "system",
                "content": "\n\n".join(system_parts),
            })

        # Examples as assistant/user pairs
        if config.include_examples and template.examples:
            for example in template.examples:
                if "input" in example:
                    messages.append({"role": "user", "content": example["input"]})
                if "output" in example:
                    messages.append({"role": "assistant", "content": example["output"]})

        # User message
        user_content = template.render(**variables)

        if config.think_step_by_step:
            user_content += "\n\nThink step by step."

        messages.append({"role": "user", "content": user_content})

        return messages

    def optimize_prompt(self, prompt: str) -> str:
        """
        Optimize a prompt for token efficiency and clarity.

        Applies various optimization techniques.
        """
        # Check cache
        if prompt in self._optimization_cache:
            return self._optimization_cache[prompt]

        optimized = prompt

        # Remove redundant whitespace
        optimized = re.sub(r'\n{3,}', '\n\n', optimized)
        optimized = re.sub(r' {2,}', ' ', optimized)

        # Remove filler phrases
        filler_patterns = [
            r'\b(please|kindly|would you|could you|can you)\b',
            r'\b(I want you to|I need you to|I would like you to)\b',
        ]
        for pattern in filler_patterns:
            optimized = re.sub(pattern, '', optimized, flags=re.IGNORECASE)

        # Compress common phrases
        compressions = {
            "in order to": "to",
            "make sure to": "ensure",
            "as well as": "and",
            "in addition to": "plus",
        }
        for long, short in compressions.items():
            optimized = optimized.replace(long, short)

        # Clean up double spaces
        optimized = re.sub(r'  +', ' ', optimized)
        optimized = optimized.strip()

        # Cache result
        self._optimization_cache[prompt] = optimized

        return optimized

    def _build_role_prompt(self, role: Role) -> str:
        """Build role/persona prompt."""
        role_prompts = {
            Role.EXPERT: "You are a world-class expert in software development with decades of experience across multiple technologies.",
            Role.CRITIC: "You are a critical code reviewer who finds issues others miss. Be thorough and constructive.",
            Role.TEACHER: "You are a patient and thorough teacher who explains concepts clearly with examples.",
            Role.ANALYST: "You are an analytical expert who breaks down complex problems systematically.",
            Role.CREATIVE: "You are a creative problem solver who thinks outside the box and finds innovative solutions.",
            Role.DEBUGGER: "You are a meticulous debugger who traces code execution to find even the most subtle bugs.",
            Role.ARCHITECT: "You are a senior software architect with expertise in designing scalable, maintainable systems.",
            Role.SECURITY_EXPERT: "You are a security expert who identifies vulnerabilities and recommends secure coding practices.",
            Role.PERFORMANCE_EXPERT: "You are a performance optimization expert who identifies bottlenecks and suggests improvements.",
        }
        return role_prompts.get(role, "You are a helpful AI assistant.")

    def _get_format_instruction(self, output_format: OutputFormat) -> Optional[str]:
        """Get output format instruction."""
        instructions = {
            OutputFormat.JSON: "Respond with valid JSON only. No markdown code blocks.",
            OutputFormat.MARKDOWN: "Format your response using Markdown.",
            OutputFormat.CODE: "Provide code in proper code blocks with language specified.",
            OutputFormat.LIST: "Format your response as a numbered or bulleted list.",
            OutputFormat.TABLE: "Format your response as a Markdown table.",
            OutputFormat.XML: "Respond with valid XML only.",
            OutputFormat.YAML: "Respond with valid YAML only.",
        }
        return instructions.get(output_format)

    def _format_examples(self, examples: List[Dict[str, str]]) -> str:
        """Format examples for few-shot prompting."""
        formatted = ["Here are some examples:\n"]

        for i, example in enumerate(examples, 1):
            formatted.append(f"Example {i}:")
            if "input" in example:
                formatted.append(f"Input: {example['input']}")
            if "output" in example:
                formatted.append(f"Output: {example['output']}")
            formatted.append("")

        return "\n".join(formatted)

    def create_chain_of_thought(
        self,
        task: str,
        steps: List[str] = None,
    ) -> str:
        """Create a chain-of-thought prompt."""
        if steps is None:
            steps = [
                "Understand the problem",
                "Break down into sub-problems",
                "Solve each sub-problem",
                "Combine solutions",
                "Verify the answer",
            ]

        steps_text = "\n".join(f"{i}. {step}" for i, step in enumerate(steps, 1))

        return f"""{task}

Let's solve this step by step:
{steps_text}

Now work through each step:"""

    def create_react_prompt(
        self,
        task: str,
        tools: List[str],
    ) -> str:
        """Create a ReAct (Reasoning + Acting) prompt."""
        tools_text = "\n".join(f"- {tool}" for tool in tools)

        return f"""You have access to the following tools:
{tools_text}

Use the following format:
Thought: Consider what to do next
Action: Choose a tool to use
Action Input: Input for the tool
Observation: Result of the action
... (repeat Thought/Action/Observation as needed)
Final Answer: The final answer to the task

Task: {task}

Begin!

Thought:"""

    def create_self_consistency(
        self,
        task: str,
        num_paths: int = 3,
    ) -> str:
        """Create a self-consistency prompt."""
        return f"""{task}

Solve this problem using {num_paths} different approaches:

Approach 1:
[Your first solution]

Approach 2:
[Your second solution using a different method]

Approach 3:
[Your third solution using yet another method]

Final Answer (based on consensus of approaches):
[Your final answer after comparing all approaches]"""


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_engineer = PromptEngineer()


def build_prompt(template_name: str, **variables) -> str:
    """Quick function to build a prompt from template."""
    return _engineer.build_prompt(template_name, **variables)


def optimize_prompt(prompt: str) -> str:
    """Quick function to optimize a prompt."""
    return _engineer.optimize_prompt(prompt)


def get_code_review_prompt(code: str, language: str = "python") -> str:
    """Get a code review prompt."""
    return _engineer.build_prompt("code_review", code=code, language=language)


def get_security_audit_prompt(code: str, language: str = "python") -> str:
    """Get a security audit prompt."""
    return _engineer.build_prompt("security_audit", code=code, language=language)


def get_test_generation_prompt(
    code: str,
    language: str = "python",
    framework: str = "pytest",
) -> str:
    """Get a test generation prompt."""
    return _engineer.build_prompt(
        "generate_tests",
        code=code,
        language=language,
        test_framework=framework,
    )
