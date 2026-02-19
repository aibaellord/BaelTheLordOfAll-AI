"""
BAEL Code Generation Engine
============================

Advanced code synthesis and generation capabilities.

"Code is poetry written in logic." — Ba'el
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import (
    Any, Callable, Dict, List, Optional, Set, Tuple, Union
)


class Language(Enum):
    """Programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    CPP = "cpp"
    CSHARP = "csharp"
    RUBY = "ruby"
    PHP = "php"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    SQL = "sql"
    BASH = "bash"


class CodeStyle(Enum):
    """Code style/paradigm."""
    FUNCTIONAL = "functional"
    OBJECT_ORIENTED = "oop"
    PROCEDURAL = "procedural"
    DECLARATIVE = "declarative"
    REACTIVE = "reactive"


class CodePattern(Enum):
    """Design patterns."""
    SINGLETON = "singleton"
    FACTORY = "factory"
    BUILDER = "builder"
    OBSERVER = "observer"
    DECORATOR = "decorator"
    STRATEGY = "strategy"
    ADAPTER = "adapter"
    FACADE = "facade"
    REPOSITORY = "repository"
    DEPENDENCY_INJECTION = "dependency_injection"


class ComponentType(Enum):
    """Types of code components."""
    FUNCTION = "function"
    CLASS = "class"
    INTERFACE = "interface"
    MODULE = "module"
    API_ENDPOINT = "api_endpoint"
    TEST = "test"
    MIGRATION = "migration"
    CONFIG = "config"
    SCHEMA = "schema"
    SCRIPT = "script"


class TestType(Enum):
    """Types of tests."""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    SECURITY = "security"


@dataclass
class CodeSpec:
    """Specification for code generation."""
    name: str
    language: Language
    component_type: ComponentType
    description: str
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    outputs: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    style: CodeStyle = CodeStyle.OBJECT_ORIENTED
    patterns: List[CodePattern] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class GeneratedCode:
    """Generated code result."""
    code: str
    language: Language
    component_type: ComponentType
    imports: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    tests: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeTemplate:
    """Code template definition."""
    name: str
    language: Language
    template: str
    variables: List[str]
    description: str = ""


class TemplateRegistry:
    """Registry of code templates."""

    def __init__(self):
        self.templates: Dict[str, CodeTemplate] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register default templates."""
        # Python templates
        self.register(CodeTemplate(
            name="python_function",
            language=Language.PYTHON,
            template='''def {name}({params}) -> {return_type}:
    """
    {docstring}

    Args:
{args_doc}

    Returns:
        {return_doc}
    """
    {body}
''',
            variables=["name", "params", "return_type", "docstring", "args_doc", "return_doc", "body"]
        ))

        self.register(CodeTemplate(
            name="python_class",
            language=Language.PYTHON,
            template='''class {name}:
    """
    {docstring}
    """

    def __init__(self{init_params}):
        """Initialize {name}."""
{init_body}

{methods}
''',
            variables=["name", "docstring", "init_params", "init_body", "methods"]
        ))

        self.register(CodeTemplate(
            name="python_dataclass",
            language=Language.PYTHON,
            template='''@dataclass
class {name}:
    """
    {docstring}
    """

{fields}
{methods}
''',
            variables=["name", "docstring", "fields", "methods"]
        ))

        self.register(CodeTemplate(
            name="python_async_function",
            language=Language.PYTHON,
            template='''async def {name}({params}) -> {return_type}:
    """
    {docstring}

    Args:
{args_doc}

    Returns:
        {return_doc}
    """
    {body}
''',
            variables=["name", "params", "return_type", "docstring", "args_doc", "return_doc", "body"]
        ))

        self.register(CodeTemplate(
            name="python_test",
            language=Language.PYTHON,
            template='''import pytest
from {module} import {imports}


class Test{class_name}:
    """Tests for {class_name}."""

    def setup_method(self):
        """Set up test fixtures."""
        {setup}

{test_methods}
''',
            variables=["module", "imports", "class_name", "setup", "test_methods"]
        ))

        # JavaScript templates
        self.register(CodeTemplate(
            name="js_function",
            language=Language.JAVASCRIPT,
            template='''/**
 * {docstring}
{jsdoc_params}
 * @returns {{{return_type}}} {return_doc}
 */
function {name}({params}) {{
    {body}
}}
''',
            variables=["name", "params", "docstring", "jsdoc_params", "return_type", "return_doc", "body"]
        ))

        self.register(CodeTemplate(
            name="js_class",
            language=Language.JAVASCRIPT,
            template='''/**
 * {docstring}
 */
class {name} {{
    /**
     * Create a {name}.
     */
    constructor({init_params}) {{
{init_body}
    }}

{methods}
}}
''',
            variables=["name", "docstring", "init_params", "init_body", "methods"]
        ))

        # TypeScript templates
        self.register(CodeTemplate(
            name="ts_interface",
            language=Language.TYPESCRIPT,
            template='''/**
 * {docstring}
 */
interface {name} {{
{properties}
}}
''',
            variables=["name", "docstring", "properties"]
        ))

        self.register(CodeTemplate(
            name="ts_class",
            language=Language.TYPESCRIPT,
            template='''/**
 * {docstring}
 */
class {name} {{
    {fields}

    constructor({init_params}) {{
{init_body}
    }}

{methods}
}}
''',
            variables=["name", "docstring", "fields", "init_params", "init_body", "methods"]
        ))

        # Go templates
        self.register(CodeTemplate(
            name="go_struct",
            language=Language.GO,
            template='''// {name} {docstring}
type {name} struct {{
{fields}
}}

// New{name} creates a new {name}.
func New{name}({params}) *{name} {{
    return &{name}{{
{init_body}
    }}
}}

{methods}
''',
            variables=["name", "docstring", "fields", "params", "init_body", "methods"]
        ))

        # SQL templates
        self.register(CodeTemplate(
            name="sql_create_table",
            language=Language.SQL,
            template='''-- {docstring}
CREATE TABLE IF NOT EXISTS {name} (
    id SERIAL PRIMARY KEY,
{columns}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

{indexes}
''',
            variables=["name", "docstring", "columns", "indexes"]
        ))

    def register(self, template: CodeTemplate) -> None:
        """Register a template."""
        self.templates[template.name] = template

    def get(self, name: str) -> Optional[CodeTemplate]:
        """Get a template by name."""
        return self.templates.get(name)

    def get_for_language(self, language: Language) -> List[CodeTemplate]:
        """Get all templates for a language."""
        return [t for t in self.templates.values() if t.language == language]


class CodeFormatter:
    """Code formatting utilities."""

    @staticmethod
    def format_python_params(params: List[Dict[str, Any]]) -> str:
        """Format Python function parameters."""
        parts = []
        for p in params:
            name = p.get("name", "arg")
            ptype = p.get("type", "Any")
            default = p.get("default")

            if default is not None:
                parts.append(f"{name}: {ptype} = {default!r}")
            else:
                parts.append(f"{name}: {ptype}")

        return ", ".join(parts)

    @staticmethod
    def format_python_args_doc(params: List[Dict[str, Any]]) -> str:
        """Format Python args documentation."""
        lines = []
        for p in params:
            name = p.get("name", "arg")
            ptype = p.get("type", "Any")
            desc = p.get("description", "")
            lines.append(f"        {name} ({ptype}): {desc}")

        return "\n".join(lines)

    @staticmethod
    def format_js_params(params: List[Dict[str, Any]]) -> str:
        """Format JavaScript function parameters."""
        return ", ".join(p.get("name", "arg") for p in params)

    @staticmethod
    def format_jsdoc_params(params: List[Dict[str, Any]]) -> str:
        """Format JSDoc parameter documentation."""
        lines = []
        for p in params:
            name = p.get("name", "arg")
            ptype = p.get("type", "*")
            desc = p.get("description", "")
            lines.append(f" * @param {{{ptype}}} {name} - {desc}")

        return "\n".join(lines)

    @staticmethod
    def format_ts_type(ptype: str) -> str:
        """Convert generic type to TypeScript type."""
        type_map = {
            "string": "string",
            "int": "number",
            "integer": "number",
            "float": "number",
            "bool": "boolean",
            "boolean": "boolean",
            "list": "Array<any>",
            "dict": "Record<string, any>",
            "any": "any",
            "void": "void",
            "none": "void"
        }
        return type_map.get(ptype.lower(), ptype)

    @staticmethod
    def format_python_type(ptype: str) -> str:
        """Convert generic type to Python type."""
        type_map = {
            "string": "str",
            "integer": "int",
            "float": "float",
            "boolean": "bool",
            "array": "List",
            "object": "Dict",
            "any": "Any",
            "void": "None",
            "none": "None"
        }
        return type_map.get(ptype.lower(), ptype)

    @staticmethod
    def indent(code: str, spaces: int = 4) -> str:
        """Indent code by specified spaces."""
        prefix = " " * spaces
        lines = code.split("\n")
        return "\n".join(prefix + line if line.strip() else line for line in lines)


class PatternGenerator:
    """Generate code for design patterns."""

    @staticmethod
    def generate_singleton(name: str, language: Language) -> str:
        """Generate singleton pattern."""
        if language == Language.PYTHON:
            return f'''class {name}:
    """Singleton implementation of {name}."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize {name}."""
        pass
'''
        elif language == Language.TYPESCRIPT:
            return f'''class {name} {{
    private static instance: {name};

    private constructor() {{
        // Initialize
    }}

    public static getInstance(): {name} {{
        if (!{name}.instance) {{
            {name}.instance = new {name}();
        }}
        return {name}.instance;
    }}
}}
'''
        return ""

    @staticmethod
    def generate_factory(
        name: str,
        products: List[str],
        language: Language
    ) -> str:
        """Generate factory pattern."""
        if language == Language.PYTHON:
            cases = "\n".join(
                f'        elif product_type == "{p.lower()}":\n            return {p}()'
                for p in products
            )
            return f'''from abc import ABC, abstractmethod


class Product(ABC):
    """Abstract product."""

    @abstractmethod
    def operation(self) -> str:
        pass


{chr(10).join(f"class {p}(Product):{chr(10)}    def operation(self) -> str:{chr(10)}        return '{p} operation'{chr(10)}" for p in products)}

class {name}:
    """Factory for creating products."""

    @staticmethod
    def create(product_type: str) -> Product:
        """Create a product by type."""
        if product_type == "{products[0].lower() if products else 'default'}":
            return {products[0] if products else "Product"}()
{cases}
        else:
            raise ValueError(f"Unknown product type: {{product_type}}")
'''
        return ""

    @staticmethod
    def generate_observer(
        subject_name: str,
        observer_name: str,
        language: Language
    ) -> str:
        """Generate observer pattern."""
        if language == Language.PYTHON:
            return f'''from abc import ABC, abstractmethod
from typing import List


class {observer_name}(ABC):
    """Abstract observer."""

    @abstractmethod
    def update(self, subject: '{subject_name}') -> None:
        """Receive update from subject."""
        pass


class {subject_name}:
    """Subject that notifies observers."""

    def __init__(self):
        self._observers: List[{observer_name}] = []
        self._state: dict = {{}}

    def attach(self, observer: {observer_name}) -> None:
        """Attach an observer."""
        self._observers.append(observer)

    def detach(self, observer: {observer_name}) -> None:
        """Detach an observer."""
        self._observers.remove(observer)

    def notify(self) -> None:
        """Notify all observers."""
        for observer in self._observers:
            observer.update(self)

    @property
    def state(self) -> dict:
        return self._state

    @state.setter
    def state(self, value: dict) -> None:
        self._state = value
        self.notify()
'''
        return ""

    @staticmethod
    def generate_decorator(
        component_name: str,
        language: Language
    ) -> str:
        """Generate decorator pattern."""
        if language == Language.PYTHON:
            return f'''from abc import ABC, abstractmethod


class {component_name}(ABC):
    """Abstract component."""

    @abstractmethod
    def operation(self) -> str:
        pass


class Concrete{component_name}({component_name}):
    """Concrete component implementation."""

    def operation(self) -> str:
        return "Concrete{component_name}"


class {component_name}Decorator({component_name}):
    """Base decorator."""

    def __init__(self, component: {component_name}):
        self._component = component

    @property
    def component(self) -> {component_name}:
        return self._component

    def operation(self) -> str:
        return self._component.operation()


class ConcreteDecorator({component_name}Decorator):
    """Concrete decorator that adds behavior."""

    def operation(self) -> str:
        return f"ConcreteDecorator({{super().operation()}})"
'''
        return ""


class TestGenerator:
    """Generate test code."""

    @staticmethod
    def generate_python_tests(
        class_name: str,
        methods: List[Dict[str, Any]]
    ) -> str:
        """Generate Python unit tests."""
        test_methods = []

        for method in methods:
            name = method.get("name", "method")
            params = method.get("params", [])
            returns = method.get("returns", "None")

            test_methods.append(f'''    def test_{name}(self):
        """Test {name} method."""
        # Arrange
        instance = {class_name}()

        # Act
        result = instance.{name}()

        # Assert
        assert result is not None
''')

        return f'''import pytest
from your_module import {class_name}


class Test{class_name}:
    """Unit tests for {class_name}."""

    def setup_method(self):
        """Set up test fixtures."""
        self.instance = {class_name}()

{chr(10).join(test_methods)}
'''

    @staticmethod
    def generate_javascript_tests(
        class_name: str,
        methods: List[Dict[str, Any]]
    ) -> str:
        """Generate JavaScript tests."""
        test_cases = []

        for method in methods:
            name = method.get("name", "method")

            test_cases.append(f'''    it('should {name}', () => {{
        // Arrange
        const instance = new {class_name}();

        // Act
        const result = instance.{name}();

        // Assert
        expect(result).toBeDefined();
    }});
''')

        return f'''const {{ {class_name} }} = require('./your_module');

describe('{class_name}', () => {{
    let instance;

    beforeEach(() => {{
        instance = new {class_name}();
    }});

{chr(10).join(test_cases)}
}});
'''


class CodeGenerationEngine:
    """
    Main Code Generation Engine

    Generates:
    - Functions and methods
    - Classes and interfaces
    - Design patterns
    - Tests
    - Documentation
    """

    def __init__(self):
        self.templates = TemplateRegistry()
        self.formatter = CodeFormatter()
        self.pattern_gen = PatternGenerator()
        self.test_gen = TestGenerator()

        self.generation_history: List[GeneratedCode] = []

        self.data_dir = Path("data/codegen")
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def generate(self, spec: CodeSpec) -> GeneratedCode:
        """Generate code from specification."""
        if spec.component_type == ComponentType.FUNCTION:
            return await self._generate_function(spec)
        elif spec.component_type == ComponentType.CLASS:
            return await self._generate_class(spec)
        elif spec.component_type == ComponentType.INTERFACE:
            return await self._generate_interface(spec)
        elif spec.component_type == ComponentType.TEST:
            return await self._generate_test(spec)
        elif spec.component_type == ComponentType.API_ENDPOINT:
            return await self._generate_api_endpoint(spec)
        else:
            return await self._generate_function(spec)

    async def _generate_function(self, spec: CodeSpec) -> GeneratedCode:
        """Generate a function."""
        if spec.language == Language.PYTHON:
            params_str = self.formatter.format_python_params(spec.inputs)
            args_doc = self.formatter.format_python_args_doc(spec.inputs)
            return_type = self.formatter.format_python_type(
                spec.outputs.get("type", "None")
            )

            template_name = "python_async_function" if spec.style == CodeStyle.REACTIVE else "python_function"
            template = self.templates.get(template_name)

            if template:
                code = template.template.format(
                    name=spec.name,
                    params=params_str,
                    return_type=return_type,
                    docstring=spec.description,
                    args_doc=args_doc or "        None",
                    return_doc=spec.outputs.get("description", "Result"),
                    body="pass  # TODO: Implement"
                )
            else:
                code = f"def {spec.name}(): pass"

            imports = ["from typing import Any, Dict, List, Optional"]

        elif spec.language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            params_str = self.formatter.format_js_params(spec.inputs)
            jsdoc = self.formatter.format_jsdoc_params(spec.inputs)

            template = self.templates.get("js_function")
            if template:
                code = template.template.format(
                    name=spec.name,
                    params=params_str,
                    docstring=spec.description,
                    jsdoc_params=jsdoc,
                    return_type=spec.outputs.get("type", "any"),
                    return_doc=spec.outputs.get("description", "Result"),
                    body="// TODO: Implement"
                )
            else:
                code = f"function {spec.name}() {{}}"

            imports = []
        else:
            code = f"// {spec.name} function stub"
            imports = []

        result = GeneratedCode(
            code=code,
            language=spec.language,
            component_type=ComponentType.FUNCTION,
            imports=imports,
            docstring=spec.description
        )

        self.generation_history.append(result)
        return result

    async def _generate_class(self, spec: CodeSpec) -> GeneratedCode:
        """Generate a class."""
        if spec.language == Language.PYTHON:
            # Format init params
            init_params = ""
            init_body_lines = []

            for inp in spec.inputs:
                name = inp.get("name", "arg")
                ptype = self.formatter.format_python_type(inp.get("type", "Any"))
                default = inp.get("default")

                if default is not None:
                    init_params += f", {name}: {ptype} = {default!r}"
                else:
                    init_params += f", {name}: {ptype}"

                init_body_lines.append(f"        self.{name} = {name}")

            init_body = "\n".join(init_body_lines) if init_body_lines else "        pass"

            template = self.templates.get("python_class")
            if template:
                code = template.template.format(
                    name=spec.name,
                    docstring=spec.description,
                    init_params=init_params,
                    init_body=init_body,
                    methods=""
                )
            else:
                code = f"class {spec.name}: pass"

            imports = ["from typing import Any, Dict, List, Optional"]

        elif spec.language == Language.TYPESCRIPT:
            fields_lines = []
            init_params_list = []
            init_body_lines = []

            for inp in spec.inputs:
                name = inp.get("name", "arg")
                ptype = self.formatter.format_ts_type(inp.get("type", "any"))

                fields_lines.append(f"    private {name}: {ptype};")
                init_params_list.append(f"{name}: {ptype}")
                init_body_lines.append(f"        this.{name} = {name};")

            template = self.templates.get("ts_class")
            if template:
                code = template.template.format(
                    name=spec.name,
                    docstring=spec.description,
                    fields="\n".join(fields_lines),
                    init_params=", ".join(init_params_list),
                    init_body="\n".join(init_body_lines) if init_body_lines else "        // Initialize",
                    methods=""
                )
            else:
                code = f"class {spec.name} {{}}"

            imports = []
        else:
            code = f"// {spec.name} class stub"
            imports = []

        result = GeneratedCode(
            code=code,
            language=spec.language,
            component_type=ComponentType.CLASS,
            imports=imports,
            docstring=spec.description
        )

        self.generation_history.append(result)
        return result

    async def _generate_interface(self, spec: CodeSpec) -> GeneratedCode:
        """Generate an interface."""
        if spec.language == Language.TYPESCRIPT:
            props = []
            for inp in spec.inputs:
                name = inp.get("name", "prop")
                ptype = self.formatter.format_ts_type(inp.get("type", "any"))
                optional = inp.get("optional", False)

                prop = f"    {name}{'?' if optional else ''}: {ptype};"
                props.append(prop)

            template = self.templates.get("ts_interface")
            if template:
                code = template.template.format(
                    name=spec.name,
                    docstring=spec.description,
                    properties="\n".join(props) if props else "    // Properties"
                )
            else:
                code = f"interface {spec.name} {{}}"

            imports = []
        elif spec.language == Language.PYTHON:
            # Python uses Protocol or ABC
            methods = []
            for inp in spec.inputs:
                name = inp.get("name", "method")
                ptype = self.formatter.format_python_type(inp.get("type", "Any"))
                methods.append(f'''    @abstractmethod
    def {name}(self) -> {ptype}:
        """Abstract method."""
        pass
''')

            code = f'''from abc import ABC, abstractmethod


class {spec.name}(ABC):
    """
    {spec.description}
    """

{chr(10).join(methods) if methods else "    pass"}
'''
            imports = ["from abc import ABC, abstractmethod"]
        else:
            code = f"// {spec.name} interface stub"
            imports = []

        result = GeneratedCode(
            code=code,
            language=spec.language,
            component_type=ComponentType.INTERFACE,
            imports=imports,
            docstring=spec.description
        )

        self.generation_history.append(result)
        return result

    async def _generate_test(self, spec: CodeSpec) -> GeneratedCode:
        """Generate test code."""
        methods = [{"name": m.get("name", "method")} for m in spec.inputs]

        if spec.language == Language.PYTHON:
            code = self.test_gen.generate_python_tests(spec.name, methods)
            imports = ["import pytest"]
        elif spec.language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            code = self.test_gen.generate_javascript_tests(spec.name, methods)
            imports = []
        else:
            code = f"// Tests for {spec.name}"
            imports = []

        result = GeneratedCode(
            code=code,
            language=spec.language,
            component_type=ComponentType.TEST,
            imports=imports,
            docstring=f"Tests for {spec.name}"
        )

        self.generation_history.append(result)
        return result

    async def _generate_api_endpoint(self, spec: CodeSpec) -> GeneratedCode:
        """Generate API endpoint code."""
        if spec.language == Language.PYTHON:
            code = f'''from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


class {spec.name}Request(BaseModel):
    """{spec.description} request."""
{chr(10).join(f"    {p['name']}: {self.formatter.format_python_type(p.get('type', 'Any'))}" for p in spec.inputs) or "    pass"}


class {spec.name}Response(BaseModel):
    """{spec.description} response."""
    success: bool
    data: Any = None
    error: Optional[str] = None


@router.post("/{spec.name.lower()}")
async def {spec.name.lower()}_endpoint(request: {spec.name}Request) -> {spec.name}Response:
    """
    {spec.description}
    """
    try:
        # TODO: Implement
        return {spec.name}Response(success=True, data={{}})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
'''
            imports = ["from fastapi import APIRouter, HTTPException", "from pydantic import BaseModel"]
        else:
            code = f"// {spec.name} API endpoint"
            imports = []

        result = GeneratedCode(
            code=code,
            language=spec.language,
            component_type=ComponentType.API_ENDPOINT,
            imports=imports,
            docstring=spec.description
        )

        self.generation_history.append(result)
        return result

    async def generate_pattern(
        self,
        pattern: CodePattern,
        name: str,
        language: Language,
        **kwargs
    ) -> GeneratedCode:
        """Generate code for a design pattern."""
        if pattern == CodePattern.SINGLETON:
            code = self.pattern_gen.generate_singleton(name, language)
        elif pattern == CodePattern.FACTORY:
            products = kwargs.get("products", ["ProductA", "ProductB"])
            code = self.pattern_gen.generate_factory(name, products, language)
        elif pattern == CodePattern.OBSERVER:
            observer_name = kwargs.get("observer_name", "Observer")
            code = self.pattern_gen.generate_observer(name, observer_name, language)
        elif pattern == CodePattern.DECORATOR:
            code = self.pattern_gen.generate_decorator(name, language)
        else:
            code = f"# {pattern.value} pattern for {name}"

        result = GeneratedCode(
            code=code,
            language=language,
            component_type=ComponentType.CLASS,
            docstring=f"{pattern.value} pattern implementation"
        )

        self.generation_history.append(result)
        return result

    async def refactor(
        self,
        code: str,
        language: Language,
        improvements: List[str]
    ) -> GeneratedCode:
        """Suggest refactoring for code."""
        # Basic refactoring suggestions
        suggestions = []

        if "naming" in improvements:
            suggestions.append("# TODO: Rename variables to be more descriptive")

        if "documentation" in improvements:
            suggestions.append("# TODO: Add docstrings and comments")

        if "typing" in improvements and language == Language.PYTHON:
            suggestions.append("# TODO: Add type hints")

        if "error_handling" in improvements:
            suggestions.append("# TODO: Add proper error handling")

        refactored = f"{chr(10).join(suggestions)}\n\n{code}"

        return GeneratedCode(
            code=refactored,
            language=language,
            component_type=ComponentType.FUNCTION,
            metadata={"improvements": improvements}
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        by_language = {}
        for gen in self.generation_history:
            lang = gen.language.value
            by_language[lang] = by_language.get(lang, 0) + 1

        return {
            "generations": len(self.generation_history),
            "by_language": by_language,
            "templates": len(self.templates.templates),
            "supported_languages": [l.value for l in Language],
            "supported_patterns": [p.value for p in CodePattern],
            "capabilities": [
                "function_generation",
                "class_generation",
                "interface_generation",
                "test_generation",
                "api_endpoint_generation",
                "design_pattern_generation",
                "refactoring_suggestions"
            ]
        }


# Convenience instance
codegen_engine = CodeGenerationEngine()
