"""
BAEL Tool Generator
====================

Generates tools from natural language descriptions.
Enables dynamic capability expansion.

Features:
- Natural language to tool conversion
- Template-based generation
- Type inference
- Documentation generation
- Test generation
"""

import asyncio
import hashlib
import inspect
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type

logger = logging.getLogger(__name__)


class ToolType(Enum):
    """Types of tools."""
    FUNCTION = "function"
    ASYNC_FUNCTION = "async_function"
    CLASS = "class"
    API = "api"
    COMMAND = "command"
    TRANSFORMER = "transformer"


class ParameterType(Enum):
    """Parameter types."""
    STRING = "str"
    INTEGER = "int"
    FLOAT = "float"
    BOOLEAN = "bool"
    LIST = "list"
    DICT = "dict"
    ANY = "Any"
    OPTIONAL = "Optional"


@dataclass
class ParameterDefinition:
    """Definition of a tool parameter."""
    name: str
    param_type: ParameterType

    # Metadata
    description: str = ""
    default: Any = None
    required: bool = True

    # Validation
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None
    choices: List[Any] = field(default_factory=list)

    def type_annotation(self) -> str:
        """Get Python type annotation."""
        type_map = {
            ParameterType.STRING: "str",
            ParameterType.INTEGER: "int",
            ParameterType.FLOAT: "float",
            ParameterType.BOOLEAN: "bool",
            ParameterType.LIST: "List[Any]",
            ParameterType.DICT: "Dict[str, Any]",
            ParameterType.ANY: "Any",
            ParameterType.OPTIONAL: f"Optional[{self.param_type.value}]",
        }
        return type_map.get(self.param_type, "Any")


@dataclass
class ToolSpec:
    """Specification for a tool to be generated."""
    name: str
    description: str

    # Type
    tool_type: ToolType = ToolType.FUNCTION

    # Parameters
    parameters: List[ParameterDefinition] = field(default_factory=list)
    return_type: str = "Any"

    # Behavior
    async_mode: bool = False

    # Examples
    examples: List[Dict[str, Any]] = field(default_factory=list)

    # Dependencies
    imports: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class ToolTemplate:
    """Template for tool generation."""
    name: str
    template: str

    # Placeholders
    placeholders: List[str] = field(default_factory=list)

    # Metadata
    description: str = ""
    category: str = "general"


@dataclass
class GeneratedTool:
    """A generated tool."""
    id: str
    spec: ToolSpec

    # Generated code
    code: str = ""

    # Compiled function
    function: Optional[Callable] = None

    # Validation
    validated: bool = False
    validation_errors: List[str] = field(default_factory=list)

    # Usage
    usage_count: int = 0
    success_count: int = 0

    # Metadata
    generated_at: datetime = field(default_factory=datetime.now)
    version: int = 1


class ToolGenerator:
    """
    Tool generator for BAEL.

    Creates tools from natural language descriptions.
    """

    def __init__(self):
        # Generated tools
        self._tools: Dict[str, GeneratedTool] = {}

        # Templates
        self._templates: Dict[str, ToolTemplate] = {}
        self._init_templates()

        # Stats
        self.stats = {
            "tools_generated": 0,
            "successful_generations": 0,
            "failed_generations": 0,
        }

    def _init_templates(self) -> None:
        """Initialize built-in templates."""
        # Function template
        self._templates["function"] = ToolTemplate(
            name="function",
            template='''
{imports}

def {name}({parameters}) -> {return_type}:
    """
    {description}

    Args:
{param_docs}

    Returns:
        {return_type}: {return_description}
    """
{body}
''',
            placeholders=["name", "parameters", "return_type", "description",
                         "param_docs", "return_description", "body", "imports"],
        )

        # Async function template
        self._templates["async_function"] = ToolTemplate(
            name="async_function",
            template='''
{imports}

async def {name}({parameters}) -> {return_type}:
    """
    {description}

    Args:
{param_docs}

    Returns:
        {return_type}: {return_description}
    """
{body}
''',
            placeholders=["name", "parameters", "return_type", "description",
                         "param_docs", "return_description", "body", "imports"],
        )

        # Transformer template
        self._templates["transformer"] = ToolTemplate(
            name="transformer",
            template='''
{imports}

class {name}Transformer:
    """
    {description}
    """

    def __init__(self):
        pass

    def transform(self, {parameters}) -> {return_type}:
        """Transform input data."""
{body}

    def inverse_transform(self, data: {return_type}) -> {input_type}:
        """Reverse transformation."""
        raise NotImplementedError("Inverse transform not implemented")
''',
            placeholders=["name", "parameters", "return_type", "input_type",
                         "description", "body", "imports"],
        )

    def parse_description(
        self,
        description: str,
    ) -> ToolSpec:
        """
        Parse natural language description into tool spec.

        Args:
            description: Natural language description

        Returns:
            Parsed tool specification
        """
        # Extract tool name
        name_match = re.search(r"(?:create|make|build|generate)\s+(?:a\s+)?(?:tool\s+)?(?:called\s+|named\s+)?['\"]?(\w+)['\"]?", description.lower())
        name = name_match.group(1) if name_match else self._generate_name(description)

        # Determine type
        tool_type = ToolType.FUNCTION
        if "async" in description.lower() or "await" in description.lower():
            tool_type = ToolType.ASYNC_FUNCTION
        elif "class" in description.lower() or "transformer" in description.lower():
            tool_type = ToolType.CLASS
        elif "api" in description.lower() or "endpoint" in description.lower():
            tool_type = ToolType.API

        # Extract parameters
        parameters = self._extract_parameters(description)

        # Determine return type
        return_type = self._infer_return_type(description)

        # Extract imports
        imports = self._extract_imports(description)

        spec = ToolSpec(
            name=name,
            description=description,
            tool_type=tool_type,
            parameters=parameters,
            return_type=return_type,
            async_mode=tool_type == ToolType.ASYNC_FUNCTION,
            imports=imports,
        )

        return spec

    def _generate_name(self, description: str) -> str:
        """Generate a name from description."""
        # Extract key verbs and nouns
        words = description.lower().split()
        action_words = ["process", "transform", "convert", "calculate", "fetch",
                       "parse", "validate", "format", "extract", "analyze"]

        name_parts = []
        for word in words:
            if word in action_words:
                name_parts.append(word)
                break

        # Add object
        for word in words:
            if len(word) > 4 and word not in action_words:
                name_parts.append(word)
                break

        if name_parts:
            return "_".join(name_parts)

        return "generated_tool"

    def _extract_parameters(
        self,
        description: str,
    ) -> List[ParameterDefinition]:
        """Extract parameters from description."""
        params = []

        # Pattern: "takes X as input" or "parameter X"
        patterns = [
            r"(?:takes?\s+|parameter\s+|input\s+)(\w+)\s*(?:as\s+)?(?:a\s+)?(\w+)?",
            r"(\w+)\s+(?:as\s+)?(?:the\s+)?(?:input|parameter|argument)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, description.lower())
            for match in matches:
                if isinstance(match, tuple):
                    name = match[0]
                    type_hint = match[1] if len(match) > 1 else "any"
                else:
                    name = match
                    type_hint = "any"

                # Map type hint
                param_type = self._map_type(type_hint)

                if name and name not in [p.name for p in params]:
                    params.append(ParameterDefinition(
                        name=name,
                        param_type=param_type,
                        description=f"The {name} parameter",
                    ))

        # Default parameter if none found
        if not params:
            params.append(ParameterDefinition(
                name="data",
                param_type=ParameterType.ANY,
                description="Input data",
            ))

        return params

    def _map_type(self, type_hint: str) -> ParameterType:
        """Map string type hint to ParameterType."""
        type_map = {
            "str": ParameterType.STRING,
            "string": ParameterType.STRING,
            "text": ParameterType.STRING,
            "int": ParameterType.INTEGER,
            "integer": ParameterType.INTEGER,
            "number": ParameterType.INTEGER,
            "float": ParameterType.FLOAT,
            "decimal": ParameterType.FLOAT,
            "bool": ParameterType.BOOLEAN,
            "boolean": ParameterType.BOOLEAN,
            "list": ParameterType.LIST,
            "array": ParameterType.LIST,
            "dict": ParameterType.DICT,
            "object": ParameterType.DICT,
        }
        return type_map.get(type_hint.lower(), ParameterType.ANY)

    def _infer_return_type(self, description: str) -> str:
        """Infer return type from description."""
        if "returns" in description.lower():
            # Extract what it returns
            match = re.search(r"returns?\s+(?:a\s+)?(\w+)", description.lower())
            if match:
                return_hint = match.group(1)
                return self._map_type(return_hint).value

        # Default based on action
        if "calculate" in description.lower():
            return "float"
        elif "list" in description.lower() or "find all" in description.lower():
            return "List[Any]"
        elif "validate" in description.lower():
            return "bool"

        return "Any"

    def _extract_imports(self, description: str) -> List[str]:
        """Extract required imports from description."""
        imports = ["from typing import Any, Dict, List, Optional"]

        if "async" in description.lower():
            imports.append("import asyncio")
        if "json" in description.lower():
            imports.append("import json")
        if "http" in description.lower() or "api" in description.lower():
            imports.append("import aiohttp")
        if "regex" in description.lower() or "pattern" in description.lower():
            imports.append("import re")
        if "date" in description.lower() or "time" in description.lower():
            imports.append("from datetime import datetime")

        return imports

    async def generate(
        self,
        description: str,
        validate: bool = True,
    ) -> GeneratedTool:
        """
        Generate a tool from natural language.

        Args:
            description: Natural language description
            validate: Whether to validate the generated code

        Returns:
            Generated tool
        """
        # Parse description
        spec = self.parse_description(description)

        return await self.generate_from_spec(spec, validate)

    async def generate_from_spec(
        self,
        spec: ToolSpec,
        validate: bool = True,
    ) -> GeneratedTool:
        """
        Generate a tool from specification.

        Args:
            spec: Tool specification
            validate: Whether to validate

        Returns:
            Generated tool
        """
        tool_id = hashlib.md5(
            f"{spec.name}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        # Get template
        template_name = "async_function" if spec.async_mode else "function"
        if spec.tool_type == ToolType.CLASS:
            template_name = "transformer"

        template = self._templates.get(template_name)
        if not template:
            template = self._templates["function"]

        # Generate code
        code = self._render_template(template, spec)

        tool = GeneratedTool(
            id=tool_id,
            spec=spec,
            code=code,
        )

        # Validate if requested
        if validate:
            tool.validated = self._validate_code(tool)

        # Compile if valid
        if tool.validated or not validate:
            tool.function = self._compile_tool(tool)

        self._tools[tool_id] = tool
        self.stats["tools_generated"] += 1

        if tool.validated:
            self.stats["successful_generations"] += 1
        else:
            self.stats["failed_generations"] += 1

        logger.info(f"Generated tool: {spec.name} (validated={tool.validated})")

        return tool

    def _render_template(
        self,
        template: ToolTemplate,
        spec: ToolSpec,
    ) -> str:
        """Render template with spec values."""
        # Build parameters string
        param_strs = []
        param_docs = []

        for param in spec.parameters:
            default_str = f" = {repr(param.default)}" if param.default is not None else ""
            param_strs.append(f"{param.name}: {param.type_annotation()}{default_str}")
            param_docs.append(f"        {param.name}: {param.description}")

        # Build body
        body = self._generate_body(spec)

        # Render
        code = template.template.format(
            name=spec.name,
            parameters=", ".join(param_strs),
            return_type=spec.return_type,
            description=spec.description,
            param_docs="\n".join(param_docs) or "        None",
            return_description="Result",
            body=body,
            imports="\n".join(spec.imports),
            input_type=spec.parameters[0].type_annotation() if spec.parameters else "Any",
        )

        return code.strip()

    def _generate_body(self, spec: ToolSpec) -> str:
        """Generate function body based on spec."""
        lines = []

        # Add validation
        for param in spec.parameters:
            if param.required and param.default is None:
                lines.append(f"    if {param.name} is None:")
                lines.append(f"        raise ValueError(\"{param.name} is required\")")

        # Add basic implementation
        lines.append("    # TODO: Implement tool logic")
        lines.append(f"    result = {param.name if spec.parameters else 'None'}")
        lines.append("    return result")

        return "\n".join(lines)

    def _validate_code(self, tool: GeneratedTool) -> bool:
        """Validate generated code."""
        try:
            compile(tool.code, "<generated>", "exec")
            return True
        except SyntaxError as e:
            tool.validation_errors.append(f"Syntax error: {e}")
            return False

    def _compile_tool(self, tool: GeneratedTool) -> Optional[Callable]:
        """Compile tool to callable."""
        try:
            namespace = {}
            exec(tool.code, namespace)

            # Get the function/class
            return namespace.get(tool.spec.name)
        except Exception as e:
            tool.validation_errors.append(f"Compilation error: {e}")
            return None

    def get_tool(self, tool_id: str) -> Optional[GeneratedTool]:
        """Get a generated tool."""
        return self._tools.get(tool_id)

    def list_tools(self) -> List[GeneratedTool]:
        """List all generated tools."""
        return list(self._tools.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get generator statistics."""
        return {
            **self.stats,
            "active_tools": len(self._tools),
            "templates": len(self._templates),
        }


def demo():
    """Demonstrate tool generation."""
    import asyncio

    print("=" * 60)
    print("BAEL Tool Generator Demo")
    print("=" * 60)

    async def run_demo():
        gen = ToolGenerator()

        # Generate from description
        descriptions = [
            "Create a tool called validate_email that takes email as string and returns boolean",
            "Make an async function to fetch_data from url parameter",
            "Build a tool to calculate_average that takes numbers as list",
        ]

        for desc in descriptions:
            print(f"\nGenerating: {desc[:50]}...")

            tool = await gen.generate(desc)

            print(f"  Name: {tool.spec.name}")
            print(f"  Type: {tool.spec.tool_type.value}")
            print(f"  Parameters: {[p.name for p in tool.spec.parameters]}")
            print(f"  Return: {tool.spec.return_type}")
            print(f"  Validated: {tool.validated}")

            if tool.validation_errors:
                print(f"  Errors: {tool.validation_errors}")

            # Show generated code snippet
            code_lines = tool.code.split("\n")
            print(f"  Code preview:")
            for line in code_lines[:10]:
                print(f"    {line}")

        print(f"\nStats: {gen.get_stats()}")

    asyncio.run(run_demo())


if __name__ == "__main__":
    demo()
