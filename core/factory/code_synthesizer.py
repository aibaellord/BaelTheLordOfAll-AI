"""
BAEL Code Synthesizer
======================

AI-powered code synthesis and generation.
Creates high-quality code from specifications.

Features:
- Multi-provider code generation
- Context-aware synthesis
- Code quality assessment
- Iterative refinement
- Style enforcement
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class CodeQuality(Enum):
    """Code quality levels."""
    EXCELLENT = 5
    GOOD = 4
    ACCEPTABLE = 3
    NEEDS_IMPROVEMENT = 2
    POOR = 1


class SynthesisProvider(Enum):
    """Code synthesis providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    LOCAL = "local"


class CodeLanguage(Enum):
    """Programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    RUST = "rust"
    GO = "go"
    JAVA = "java"
    CSHARP = "csharp"


@dataclass
class SynthesisConfig:
    """Code synthesis configuration."""
    # Provider
    provider: SynthesisProvider = SynthesisProvider.OPENAI
    model: str = "gpt-4"
    api_key: Optional[str] = None

    # Generation
    language: CodeLanguage = CodeLanguage.PYTHON
    temperature: float = 0.2
    max_tokens: int = 4096

    # Quality
    min_quality: CodeQuality = CodeQuality.ACCEPTABLE
    max_iterations: int = 3

    # Style
    code_style: str = "black"
    docstring_style: str = "google"
    type_hints: bool = True

    # Context
    include_imports: bool = True
    include_docstrings: bool = True
    include_type_hints: bool = True


@dataclass
class CodeContext:
    """Context for code synthesis."""
    # Project context
    project_name: str = ""
    existing_imports: List[str] = field(default_factory=list)
    existing_classes: List[str] = field(default_factory=list)
    existing_functions: List[str] = field(default_factory=list)

    # Dependencies
    available_packages: List[str] = field(default_factory=list)

    # Style hints
    naming_convention: str = "snake_case"

    # Example code
    examples: List[str] = field(default_factory=list)


@dataclass
class QualityMetrics:
    """Code quality metrics."""
    complexity: float = 0.0  # Cyclomatic complexity
    maintainability: float = 0.0  # Maintainability index
    readability: float = 0.0  # Readability score
    coverage_potential: float = 0.0  # Testability

    # Issues
    linting_issues: int = 0
    type_errors: int = 0
    security_issues: int = 0

    @property
    def overall_score(self) -> float:
        base_score = (self.maintainability + self.readability) / 2
        penalty = (self.linting_issues * 0.1 + self.type_errors * 0.2 + self.security_issues * 0.3)
        return max(0, min(1, base_score - penalty))

    @property
    def quality_level(self) -> CodeQuality:
        score = self.overall_score
        if score >= 0.9:
            return CodeQuality.EXCELLENT
        elif score >= 0.75:
            return CodeQuality.GOOD
        elif score >= 0.5:
            return CodeQuality.ACCEPTABLE
        elif score >= 0.25:
            return CodeQuality.NEEDS_IMPROVEMENT
        return CodeQuality.POOR


@dataclass
class SynthesizedCode:
    """Result of code synthesis."""
    code: str
    language: CodeLanguage

    # Quality
    metrics: QualityMetrics = field(default_factory=QualityMetrics)

    # Metadata
    provider: SynthesisProvider = SynthesisProvider.LOCAL
    model: str = ""
    iterations: int = 1

    # Timing
    synthesis_time_ms: float = 0.0

    # Errors
    error: Optional[str] = None

    @property
    def quality(self) -> CodeQuality:
        return self.metrics.quality_level

    @property
    def success(self) -> bool:
        return self.error is None and bool(self.code)


class CodeSynthesizer:
    """
    AI-powered code synthesis for BAEL.
    """

    def __init__(
        self,
        config: Optional[SynthesisConfig] = None,
        llm_client: Optional[Any] = None,
    ):
        self.config = config or SynthesisConfig()
        self.llm_client = llm_client

        # Prompt templates
        self._prompts: Dict[str, str] = {}
        self._load_prompts()

        # Stats
        self.stats = {
            "syntheses": 0,
            "successful": 0,
            "total_tokens": 0,
            "total_time_ms": 0.0,
        }

    def _load_prompts(self) -> None:
        """Load synthesis prompts."""
        self._prompts["function"] = """Generate a Python function with the following specification:

Function Name: {name}
Description: {description}
Parameters: {parameters}
Return Type: {return_type}

Requirements:
- Include type hints
- Include comprehensive docstring (Google style)
- Handle edge cases and errors
- Be efficient and readable

{context}

Generate only the function code, no explanations:
"""

        self._prompts["class"] = """Generate a Python class with the following specification:

Class Name: {name}
Description: {description}
Methods: {methods}
Attributes: {attributes}

Requirements:
- Include type hints for all methods and attributes
- Include comprehensive docstrings (Google style)
- Follow SOLID principles
- Include proper error handling

{context}

Generate only the class code, no explanations:
"""

        self._prompts["refine"] = """Improve the following code:

```{language}
{code}
```

Issues to fix:
{issues}

Requirements:
- Maintain the same functionality
- Fix all listed issues
- Improve code quality
- Add missing error handling

Generate only the improved code, no explanations:
"""

    async def synthesize_function(
        self,
        name: str,
        description: str,
        parameters: List[Dict[str, str]],
        return_type: str = "Any",
        context: Optional[CodeContext] = None,
    ) -> SynthesizedCode:
        """
        Synthesize a function.

        Args:
            name: Function name
            description: Function description
            parameters: List of parameter definitions
            return_type: Return type
            context: Code context

        Returns:
            SynthesizedCode
        """
        param_str = ", ".join(
            f"{p['name']}: {p.get('type', 'Any')}"
            for p in parameters
        )

        context_str = ""
        if context:
            if context.existing_imports:
                context_str += f"Available imports: {', '.join(context.existing_imports)}\n"
            if context.examples:
                context_str += f"Example style:\n{context.examples[0]}\n"

        prompt = self._prompts["function"].format(
            name=name,
            description=description,
            parameters=param_str,
            return_type=return_type,
            context=context_str,
        )

        return await self._synthesize(prompt, context)

    async def synthesize_class(
        self,
        name: str,
        description: str,
        methods: List[Dict[str, Any]],
        attributes: List[Dict[str, str]],
        context: Optional[CodeContext] = None,
    ) -> SynthesizedCode:
        """
        Synthesize a class.

        Args:
            name: Class name
            description: Class description
            methods: Method specifications
            attributes: Attribute specifications
            context: Code context

        Returns:
            SynthesizedCode
        """
        methods_str = "\n".join(
            f"- {m['name']}: {m.get('description', '')}"
            for m in methods
        )

        attrs_str = "\n".join(
            f"- {a['name']}: {a.get('type', 'Any')}"
            for a in attributes
        )

        context_str = ""
        if context:
            if context.existing_imports:
                context_str += f"Available imports: {', '.join(context.existing_imports)}\n"

        prompt = self._prompts["class"].format(
            name=name,
            description=description,
            methods=methods_str,
            attributes=attrs_str,
            context=context_str,
        )

        return await self._synthesize(prompt, context)

    async def synthesize_from_spec(
        self,
        spec: Dict[str, Any],
        context: Optional[CodeContext] = None,
    ) -> SynthesizedCode:
        """
        Synthesize code from a specification dictionary.

        Args:
            spec: Code specification
            context: Code context

        Returns:
            SynthesizedCode
        """
        spec_type = spec.get("type", "function")

        if spec_type == "function":
            return await self.synthesize_function(
                name=spec.get("name", "unnamed"),
                description=spec.get("description", ""),
                parameters=spec.get("parameters", []),
                return_type=spec.get("return_type", "Any"),
                context=context,
            )
        elif spec_type == "class":
            return await self.synthesize_class(
                name=spec.get("name", "Unnamed"),
                description=spec.get("description", ""),
                methods=spec.get("methods", []),
                attributes=spec.get("attributes", []),
                context=context,
            )
        else:
            return await self._synthesize(
                f"Generate code for: {spec}",
                context,
            )

    async def _synthesize(
        self,
        prompt: str,
        context: Optional[CodeContext] = None,
    ) -> SynthesizedCode:
        """Core synthesis logic."""
        self.stats["syntheses"] += 1
        start_time = time.time()

        try:
            # Generate code
            if self.llm_client:
                code = await self._call_llm(prompt)
            else:
                code = self._generate_stub(prompt)

            # Clean code
            code = self._clean_code(code)

            # Assess quality
            metrics = self._assess_quality(code)

            # Refine if needed
            iterations = 1
            while (
                metrics.quality_level.value < self.config.min_quality.value
                and iterations < self.config.max_iterations
            ):
                code = await self._refine(code, metrics)
                metrics = self._assess_quality(code)
                iterations += 1

            elapsed = (time.time() - start_time) * 1000
            self.stats["total_time_ms"] += elapsed
            self.stats["successful"] += 1

            return SynthesizedCode(
                code=code,
                language=self.config.language,
                metrics=metrics,
                provider=self.config.provider,
                model=self.config.model,
                iterations=iterations,
                synthesis_time_ms=elapsed,
            )

        except Exception as e:
            logger.error(f"Synthesis error: {e}")
            return SynthesizedCode(
                code="",
                language=self.config.language,
                error=str(e),
            )

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM for code generation."""
        # Would integrate with actual LLM client
        # For now, return stub
        return self._generate_stub(prompt)

    def _generate_stub(self, prompt: str) -> str:
        """Generate stub code (fallback)."""
        # Extract name from prompt
        import re

        name_match = re.search(r"(?:Function|Class) Name:\s*(\w+)", prompt)
        name = name_match.group(1) if name_match else "generated"

        desc_match = re.search(r"Description:\s*(.+?)(?:\n|$)", prompt)
        desc = desc_match.group(1) if desc_match else "Generated code"

        if "Class Name" in prompt:
            return f'''class {name}:
    """
    {desc}
    """

    def __init__(self):
        """Initialize the {name}."""
        pass

    def execute(self, *args, **kwargs):
        """Execute the main operation."""
        raise NotImplementedError("Implementation required")
'''
        else:
            return f'''def {name}(*args, **kwargs):
    """
    {desc}

    Args:
        *args: Variable positional arguments
        **kwargs: Variable keyword arguments

    Returns:
        Result of operation
    """
    raise NotImplementedError("Implementation required")
'''

    def _clean_code(self, code: str) -> str:
        """Clean generated code."""
        # Remove markdown code blocks
        code = code.strip()
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        return code.strip()

    def _assess_quality(self, code: str) -> QualityMetrics:
        """Assess code quality."""
        metrics = QualityMetrics()

        if not code:
            return metrics

        lines = code.split("\n")

        # Basic metrics
        has_docstrings = '"""' in code or "'''" in code
        has_type_hints = ":" in code and "->" in code
        has_error_handling = "try:" in code or "except" in code

        # Readability score
        avg_line_length = sum(len(l) for l in lines) / max(len(lines), 1)
        metrics.readability = max(0, 1 - (avg_line_length - 50) / 100)

        # Maintainability
        metrics.maintainability = 0.5
        if has_docstrings:
            metrics.maintainability += 0.2
        if has_type_hints:
            metrics.maintainability += 0.2
        if has_error_handling:
            metrics.maintainability += 0.1

        # Check for issues
        if "pass" in code and "raise" not in code:
            metrics.linting_issues += 1
        if "TODO" in code or "FIXME" in code:
            metrics.linting_issues += 1

        return metrics

    async def _refine(self, code: str, metrics: QualityMetrics) -> str:
        """Refine code to improve quality."""
        issues = []

        if metrics.readability < 0.5:
            issues.append("Improve readability - use shorter lines")
        if metrics.maintainability < 0.5:
            issues.append("Add docstrings and type hints")
        if metrics.linting_issues > 0:
            issues.append("Fix linting issues")

        prompt = self._prompts["refine"].format(
            language="python",
            code=code,
            issues="\n".join(f"- {i}" for i in issues),
        )

        if self.llm_client:
            refined = await self._call_llm(prompt)
            return self._clean_code(refined)

        return code

    async def complete_code(
        self,
        partial_code: str,
        instruction: str = "",
    ) -> SynthesizedCode:
        """
        Complete partial code.

        Args:
            partial_code: Incomplete code
            instruction: What to complete

        Returns:
            SynthesizedCode
        """
        prompt = f"""Complete the following code:

```python
{partial_code}
```

{f"Instructions: {instruction}" if instruction else ""}

Complete the code maintaining consistency and quality:
"""

        return await self._synthesize(prompt)

    def get_stats(self) -> Dict[str, Any]:
        """Get synthesizer statistics."""
        avg_time = 0.0
        if self.stats["syntheses"] > 0:
            avg_time = self.stats["total_time_ms"] / self.stats["syntheses"]

        return {
            **self.stats,
            "provider": self.config.provider.value,
            "model": self.config.model,
            "avg_time_ms": avg_time,
        }


def demo():
    """Demonstrate code synthesizer."""
    import asyncio

    print("=" * 60)
    print("BAEL Code Synthesizer Demo")
    print("=" * 60)

    synthesizer = CodeSynthesizer()

    # Synthesize a function
    async def synthesize():
        result = await synthesizer.synthesize_function(
            name="process_data",
            description="Process input data and return transformed result",
            parameters=[
                {"name": "data", "type": "Dict[str, Any]"},
                {"name": "options", "type": "Optional[Dict]"},
            ],
            return_type="Dict[str, Any]",
        )
        return result

    result = asyncio.run(synthesize())

    print(f"\nSynthesis result:")
    print(f"  Success: {result.success}")
    print(f"  Quality: {result.quality.name}")
    print(f"  Iterations: {result.iterations}")
    print(f"  Time: {result.synthesis_time_ms:.2f}ms")

    print(f"\nGenerated code:")
    print("-" * 40)
    print(result.code)
    print("-" * 40)

    print(f"\nQuality metrics:")
    print(f"  Readability: {result.metrics.readability:.2f}")
    print(f"  Maintainability: {result.metrics.maintainability:.2f}")
    print(f"  Overall: {result.metrics.overall_score:.2f}")

    print(f"\nStats: {synthesizer.get_stats()}")


if __name__ == "__main__":
    demo()
