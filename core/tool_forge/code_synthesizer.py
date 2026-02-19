"""
BAEL Code Synthesizer
======================

Generates executable code from specifications.
Enables automatic tool implementation.

Features:
- Template-based synthesis
- Type-safe code generation
- Error handling injection
- Documentation generation
- Test case synthesis
"""

import asyncio
import hashlib
import logging
import re
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class SynthesisMode(Enum):
    """Code synthesis modes."""
    SIMPLE = "simple"  # Basic implementation
    SAFE = "safe"  # With error handling
    VALIDATED = "validated"  # With input validation
    OPTIMIZED = "optimized"  # Performance optimized
    FULL = "full"  # All features


@dataclass
class ParameterSpec:
    """Parameter specification for synthesis."""
    name: str
    type_hint: str

    # Defaults
    default_value: Any = None
    has_default: bool = False

    # Validation
    required: bool = True
    nullable: bool = False

    # Constraints
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    choices: List[Any] = field(default_factory=list)

    # Documentation
    description: str = ""


@dataclass
class CodeTemplate:
    """Template for code synthesis."""
    name: str
    language: str = "python"

    # Template sections
    header: str = ""
    imports: List[str] = field(default_factory=list)
    body_template: str = ""
    footer: str = ""

    # Metadata
    description: str = ""


@dataclass
class SynthesisResult:
    """Result of code synthesis."""
    id: str

    # Generated code
    code: str = ""

    # Documentation
    docstring: str = ""

    # Tests
    test_code: str = ""

    # Validation
    syntax_valid: bool = False

    # Metadata
    mode: SynthesisMode = SynthesisMode.SIMPLE
    synthesized_at: datetime = field(default_factory=datetime.now)


class CodeSynthesizer:
    """
    Code synthesizer for BAEL.

    Generates executable code from specifications.
    """

    def __init__(self):
        # Templates
        self._templates: Dict[str, CodeTemplate] = {}
        self._init_templates()

        # Synthesis history
        self._history: List[SynthesisResult] = []

        # Stats
        self.stats = {
            "code_synthesized": 0,
            "tests_generated": 0,
            "syntax_errors": 0,
        }

    def _init_templates(self) -> None:
        """Initialize code templates."""
        # Basic function template
        self._templates["function"] = CodeTemplate(
            name="function",
            language="python",
            header="#!/usr/bin/env python3",
            imports=[
                "from typing import Any, Dict, List, Optional, Union",
            ],
            body_template='''
def {name}({params}) -> {return_type}:
    """{docstring}"""
{validation}
{body}
    return {return_value}
''',
        )

        # Async function template
        self._templates["async_function"] = CodeTemplate(
            name="async_function",
            language="python",
            header="#!/usr/bin/env python3",
            imports=[
                "from typing import Any, Dict, List, Optional, Union",
                "import asyncio",
            ],
            body_template='''
async def {name}({params}) -> {return_type}:
    """{docstring}"""
{validation}
{body}
    return {return_value}
''',
        )

        # Class template
        self._templates["class"] = CodeTemplate(
            name="class",
            language="python",
            header="#!/usr/bin/env python3",
            imports=[
                "from typing import Any, Dict, List, Optional, Union",
                "from dataclasses import dataclass, field",
            ],
            body_template='''
class {name}:
    """{docstring}"""

    def __init__(self{init_params}):
        """Initialize {name}."""
{init_body}

{methods}
''',
        )

        # API endpoint template
        self._templates["api_endpoint"] = CodeTemplate(
            name="api_endpoint",
            language="python",
            imports=[
                "from typing import Any, Dict, List, Optional",
                "import aiohttp",
                "import json",
            ],
            body_template='''
async def {name}({params}) -> {return_type}:
    """{docstring}"""
{validation}
    async with aiohttp.ClientSession() as session:
        async with session.{method}({url}, {body_arg}) as response:
            if response.status != 200:
                raise Exception(f"API error: {{response.status}}")
            return await response.json()
''',
        )

    def synthesize(
        self,
        name: str,
        parameters: List[ParameterSpec],
        return_type: str = "Any",
        description: str = "",
        implementation: Optional[str] = None,
        mode: SynthesisMode = SynthesisMode.SAFE,
        template_name: str = "function",
    ) -> SynthesisResult:
        """
        Synthesize code from specifications.

        Args:
            name: Function/class name
            parameters: Parameter specifications
            return_type: Return type
            description: Description
            implementation: Optional implementation code
            mode: Synthesis mode
            template_name: Template to use

        Returns:
            Synthesis result
        """
        result_id = hashlib.md5(
            f"{name}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        template = self._templates.get(template_name, self._templates["function"])

        # Build components
        params_str = self._build_params(parameters)
        validation = self._build_validation(parameters, mode)
        docstring = self._build_docstring(name, description, parameters, return_type)
        body = implementation or self._generate_body(parameters)
        return_value = self._determine_return(parameters, return_type)

        # Render template
        code = template.body_template.format(
            name=name,
            params=params_str,
            return_type=return_type,
            docstring=docstring,
            validation=validation,
            body=body,
            return_value=return_value,
        )

        # Add imports
        imports = "\n".join(template.imports)
        if template.header:
            code = f"{template.header}\n{imports}\n\n{code}"
        else:
            code = f"{imports}\n\n{code}"

        # Validate syntax
        syntax_valid = self._validate_syntax(code)

        result = SynthesisResult(
            id=result_id,
            code=code.strip(),
            docstring=docstring,
            syntax_valid=syntax_valid,
            mode=mode,
        )

        # Generate tests
        if syntax_valid:
            result.test_code = self._generate_tests(name, parameters, return_type)
            self.stats["tests_generated"] += 1
        else:
            self.stats["syntax_errors"] += 1

        self._history.append(result)
        self.stats["code_synthesized"] += 1

        return result

    def _build_params(self, parameters: List[ParameterSpec]) -> str:
        """Build parameter string."""
        parts = []

        for param in parameters:
            type_hint = param.type_hint
            if param.nullable:
                type_hint = f"Optional[{type_hint}]"

            if param.has_default:
                default = repr(param.default_value)
                parts.append(f"{param.name}: {type_hint} = {default}")
            else:
                parts.append(f"{param.name}: {type_hint}")

        return ", ".join(parts)

    def _build_validation(
        self,
        parameters: List[ParameterSpec],
        mode: SynthesisMode,
    ) -> str:
        """Build validation code."""
        if mode == SynthesisMode.SIMPLE:
            return ""

        lines = []

        for param in parameters:
            # Required check
            if param.required and not param.has_default:
                lines.append(f"    if {param.name} is None:")
                lines.append(f"        raise ValueError('{param.name} is required')")

            # Type validation (safe mode+)
            if mode.value in ["safe", "validated", "full"]:
                if param.type_hint in ["int", "float"]:
                    if param.min_value is not None:
                        lines.append(f"    if {param.name} < {param.min_value}:")
                        lines.append(f"        raise ValueError('{param.name} must be >= {param.min_value}')")
                    if param.max_value is not None:
                        lines.append(f"    if {param.name} > {param.max_value}:")
                        lines.append(f"        raise ValueError('{param.name} must be <= {param.max_value}')")

                if param.type_hint == "str":
                    if param.min_length is not None:
                        lines.append(f"    if len({param.name}) < {param.min_length}:")
                        lines.append(f"        raise ValueError('{param.name} must be at least {param.min_length} chars')")
                    if param.max_length is not None:
                        lines.append(f"    if len({param.name}) > {param.max_length}:")
                        lines.append(f"        raise ValueError('{param.name} must be at most {param.max_length} chars')")
                    if param.pattern:
                        lines.append(f"    import re")
                        lines.append(f"    if not re.match(r'{param.pattern}', {param.name}):")
                        lines.append(f"        raise ValueError('{param.name} does not match pattern')")

                if param.choices:
                    lines.append(f"    if {param.name} not in {param.choices}:")
                    lines.append(f"        raise ValueError('{param.name} must be one of {param.choices}')")

        return "\n".join(lines) if lines else ""

    def _build_docstring(
        self,
        name: str,
        description: str,
        parameters: List[ParameterSpec],
        return_type: str,
    ) -> str:
        """Build docstring."""
        lines = [description or f"{name} function."]

        if parameters:
            lines.append("")
            lines.append("Args:")
            for param in parameters:
                desc = param.description or f"The {param.name}"
                lines.append(f"    {param.name}: {desc}")

        lines.append("")
        lines.append("Returns:")
        lines.append(f"    {return_type}: Result")

        return "\n    ".join(lines)

    def _generate_body(self, parameters: List[ParameterSpec]) -> str:
        """Generate placeholder body."""
        lines = ["    # TODO: Implement logic"]

        if parameters:
            lines.append(f"    result = {parameters[0].name}")
        else:
            lines.append("    result = None")

        return "\n".join(lines)

    def _determine_return(
        self,
        parameters: List[ParameterSpec],
        return_type: str,
    ) -> str:
        """Determine return value."""
        if return_type == "bool":
            return "True"
        elif return_type in ["int", "float"]:
            return "0"
        elif return_type == "str":
            return '""'
        elif return_type.startswith("List"):
            return "[]"
        elif return_type.startswith("Dict"):
            return "{}"
        else:
            return "result"

    def _validate_syntax(self, code: str) -> bool:
        """Validate Python syntax."""
        try:
            compile(code, "<synthesized>", "exec")
            return True
        except SyntaxError:
            return False

    def _generate_tests(
        self,
        name: str,
        parameters: List[ParameterSpec],
        return_type: str,
    ) -> str:
        """Generate test code."""
        test_lines = [
            f"def test_{name}():",
            f'    """Test {name} function."""',
        ]

        # Generate test arguments
        test_args = []
        for param in parameters:
            if param.type_hint == "int":
                val = param.min_value if param.min_value is not None else 0
                test_args.append(f"{param.name}={int(val)}")
            elif param.type_hint == "float":
                val = param.min_value if param.min_value is not None else 0.0
                test_args.append(f"{param.name}={val}")
            elif param.type_hint == "str":
                test_args.append(f'{param.name}="test"')
            elif param.type_hint == "bool":
                test_args.append(f"{param.name}=True")
            elif "List" in param.type_hint:
                test_args.append(f"{param.name}=[]")
            elif "Dict" in param.type_hint:
                test_args.append(f"{param.name}={{}}")

        args_str = ", ".join(test_args)
        test_lines.append(f"    result = {name}({args_str})")
        test_lines.append("    assert result is not None")

        # Type check
        if return_type == "bool":
            test_lines.append("    assert isinstance(result, bool)")
        elif return_type == "int":
            test_lines.append("    assert isinstance(result, int)")
        elif return_type == "str":
            test_lines.append("    assert isinstance(result, str)")

        return "\n".join(test_lines)

    def synthesize_class(
        self,
        name: str,
        attributes: List[ParameterSpec],
        methods: Optional[List[Dict[str, Any]]] = None,
        description: str = "",
    ) -> SynthesisResult:
        """
        Synthesize a class.

        Args:
            name: Class name
            attributes: Class attributes
            methods: Method definitions
            description: Class description

        Returns:
            Synthesis result
        """
        result_id = hashlib.md5(
            f"class_{name}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        # Build init params
        init_params = []
        init_body_lines = []

        for attr in attributes:
            if attr.has_default:
                init_params.append(f"{attr.name}: {attr.type_hint} = {repr(attr.default_value)}")
            else:
                init_params.append(f"{attr.name}: {attr.type_hint}")

            init_body_lines.append(f"        self.{attr.name} = {attr.name}")

        init_params_str = (", " + ", ".join(init_params)) if init_params else ""
        init_body = "\n".join(init_body_lines) or "        pass"

        # Build methods
        method_code = []
        if methods:
            for method in methods:
                method_name = method.get("name", "method")
                method_params = method.get("params", [])
                method_return = method.get("return_type", "None")
                method_body = method.get("body", "pass")

                params_str = ", ".join(["self"] + [
                    f"{p['name']}: {p.get('type', 'Any')}"
                    for p in method_params
                ])

                method_code.append(f"    def {method_name}({params_str}) -> {method_return}:")
                method_code.append(f'        """Method {method_name}."""')
                method_code.append(f"        {method_body}")
                method_code.append("")

        methods_str = "\n".join(method_code) or "    pass"

        # Get template
        template = self._templates["class"]

        # Render
        code = template.body_template.format(
            name=name,
            docstring=description or f"{name} class.",
            init_params=init_params_str,
            init_body=init_body,
            methods=methods_str,
        )

        imports = "\n".join(template.imports)
        code = f"{imports}\n\n{code}"

        syntax_valid = self._validate_syntax(code)

        result = SynthesisResult(
            id=result_id,
            code=code.strip(),
            syntax_valid=syntax_valid,
            mode=SynthesisMode.FULL,
        )

        self._history.append(result)
        self.stats["code_synthesized"] += 1

        return result

    def add_template(self, template: CodeTemplate) -> None:
        """Add a custom template."""
        self._templates[template.name] = template

    def get_history(self) -> List[SynthesisResult]:
        """Get synthesis history."""
        return self._history

    def get_stats(self) -> Dict[str, Any]:
        """Get synthesizer statistics."""
        return {
            **self.stats,
            "templates": len(self._templates),
            "history_size": len(self._history),
        }


def demo():
    """Demonstrate code synthesizer."""
    print("=" * 60)
    print("BAEL Code Synthesizer Demo")
    print("=" * 60)

    synth = CodeSynthesizer()

    # Synthesize a function
    print("\nSynthesizing function...")

    params = [
        ParameterSpec(
            name="email",
            type_hint="str",
            description="Email address to validate",
            pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$",
        ),
        ParameterSpec(
            name="strict",
            type_hint="bool",
            default_value=False,
            has_default=True,
            description="Use strict validation",
        ),
    ]

    result = synth.synthesize(
        name="validate_email",
        parameters=params,
        return_type="bool",
        description="Validate an email address format.",
        mode=SynthesisMode.VALIDATED,
    )

    print(f"\nGenerated code:")
    print("-" * 40)
    print(result.code[:500])
    print("...")
    print("-" * 40)
    print(f"Syntax valid: {result.syntax_valid}")

    # Generate test
    print(f"\nGenerated test:")
    print(result.test_code)

    # Synthesize a class
    print("\nSynthesizing class...")

    attrs = [
        ParameterSpec(name="name", type_hint="str", description="User name"),
        ParameterSpec(name="age", type_hint="int", min_value=0, description="User age"),
        ParameterSpec(name="active", type_hint="bool", default_value=True, has_default=True),
    ]

    methods = [
        {
            "name": "greet",
            "params": [],
            "return_type": "str",
            "body": 'return f"Hello, {self.name}!"',
        },
    ]

    class_result = synth.synthesize_class(
        name="User",
        attributes=attrs,
        methods=methods,
        description="User class for managing user data.",
    )

    print(f"\nGenerated class:")
    print("-" * 40)
    print(class_result.code)
    print("-" * 40)

    print(f"\nStats: {synth.get_stats()}")


if __name__ == "__main__":
    demo()
