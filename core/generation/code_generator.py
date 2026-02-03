"""
BAEL - Code Generator
Advanced code generation with multiple paradigms.

Features:
- Multi-language support
- Pattern-based generation
- Template system
- Best practices enforcement
- Style consistency
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("BAEL.CodeGenerator")


# =============================================================================
# TYPES & ENUMS
# =============================================================================

class Language(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CSHARP = "csharp"
    GO = "go"
    RUST = "rust"
    CPP = "cpp"
    RUBY = "ruby"
    PHP = "php"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    SQL = "sql"
    BASH = "bash"
    YAML = "yaml"
    JSON = "json"


class CodeStyle(Enum):
    """Code style preferences."""
    MINIMAL = "minimal"
    STANDARD = "standard"
    VERBOSE = "verbose"
    DOCUMENTED = "documented"


class Pattern(Enum):
    """Design patterns."""
    SINGLETON = "singleton"
    FACTORY = "factory"
    BUILDER = "builder"
    OBSERVER = "observer"
    STRATEGY = "strategy"
    DECORATOR = "decorator"
    ADAPTER = "adapter"
    REPOSITORY = "repository"
    SERVICE = "service"
    CONTROLLER = "controller"


@dataclass
class CodeSpec:
    """Specification for code generation."""
    name: str
    description: str
    language: Language

    # Structure
    pattern: Optional[Pattern] = None
    imports: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

    # Content
    methods: List[Dict[str, Any]] = field(default_factory=list)
    properties: List[Dict[str, Any]] = field(default_factory=list)

    # Style
    style: CodeStyle = CodeStyle.STANDARD
    include_tests: bool = True
    include_docs: bool = True


@dataclass
class GeneratedCode:
    """Generated code result."""
    spec: CodeSpec
    code: str
    tests: Optional[str] = None
    documentation: Optional[str] = None

    filepath: Optional[str] = None
    language: Language = Language.PYTHON

    created_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# LANGUAGE TEMPLATES
# =============================================================================

class LanguageTemplates:
    """Templates for different languages."""

    @staticmethod
    def get_class_template(language: Language) -> str:
        """Get class template for language."""
        templates = {
            Language.PYTHON: '''
class {name}:
    """{description}"""

    def __init__(self{init_params}):
        """Initialize {name}."""
{init_body}

{methods}
''',
            Language.TYPESCRIPT: '''
/**
 * {description}
 */
export class {name} {{
{properties}

    constructor({init_params}) {{
{init_body}
    }}

{methods}
}}
''',
            Language.JAVASCRIPT: '''
/**
 * {description}
 */
class {name} {{
{properties}

    constructor({init_params}) {{
{init_body}
    }}

{methods}
}}

module.exports = {{ {name} }};
''',
            Language.JAVA: '''
/**
 * {description}
 */
public class {name} {{
{properties}

    public {name}({init_params}) {{
{init_body}
    }}

{methods}
}}
''',
            Language.GO: '''
// {name} - {description}
type {name} struct {{
{properties}
}}

// New{name} creates a new {name}
func New{name}({init_params}) *{name} {{
    return &{name}{{
{init_body}
    }}
}}

{methods}
''',
            Language.RUST: '''
/// {description}
pub struct {name} {{
{properties}
}}

impl {name} {{
    /// Creates a new {name}
    pub fn new({init_params}) -> Self {{
        Self {{
{init_body}
        }}
    }}

{methods}
}}
'''
        }
        return templates.get(language, templates[Language.PYTHON])

    @staticmethod
    def get_function_template(language: Language) -> str:
        """Get function template for language."""
        templates = {
            Language.PYTHON: '''
def {name}({params}) -> {return_type}:
    """{description}"""
{body}
''',
            Language.TYPESCRIPT: '''
/**
 * {description}
 */
export function {name}({params}): {return_type} {{
{body}
}}
''',
            Language.JAVASCRIPT: '''
/**
 * {description}
 */
function {name}({params}) {{
{body}
}}
''',
            Language.GO: '''
// {name} - {description}
func {name}({params}) {return_type} {{
{body}
}}
''',
            Language.RUST: '''
/// {description}
pub fn {name}({params}) -> {return_type} {{
{body}
}}
'''
        }
        return templates.get(language, templates[Language.PYTHON])


# =============================================================================
# CODE GENERATOR
# =============================================================================

class CodeGenerator:
    """Advanced code generator."""

    def __init__(self, model_router=None):
        self.model_router = model_router
        self.templates = LanguageTemplates()

        # Type mappings between languages
        self.type_mappings = {
            Language.PYTHON: {
                "string": "str",
                "integer": "int",
                "boolean": "bool",
                "array": "List",
                "object": "Dict",
                "void": "None",
                "any": "Any"
            },
            Language.TYPESCRIPT: {
                "string": "string",
                "integer": "number",
                "boolean": "boolean",
                "array": "Array",
                "object": "Record<string, any>",
                "void": "void",
                "any": "any"
            },
            Language.GO: {
                "string": "string",
                "integer": "int",
                "boolean": "bool",
                "array": "[]",
                "object": "map[string]interface{}",
                "void": "",
                "any": "interface{}"
            }
        }

    async def generate(self, spec: CodeSpec) -> GeneratedCode:
        """Generate code from specification."""
        logger.info(f"Generating {spec.language.value} code: {spec.name}")

        # Build code structure
        if self.model_router:
            code = await self._ai_generate(spec)
        else:
            code = self._template_generate(spec)

        # Generate tests if requested
        tests = None
        if spec.include_tests:
            tests = await self._generate_tests(spec, code)

        # Generate documentation if requested
        docs = None
        if spec.include_docs:
            docs = self._generate_docs(spec)

        return GeneratedCode(
            spec=spec,
            code=code,
            tests=tests,
            documentation=docs,
            language=spec.language
        )

    async def _ai_generate(self, spec: CodeSpec) -> str:
        """Generate code using AI."""
        prompt = f"""Generate {spec.language.value} code with these specifications:

Name: {spec.name}
Description: {spec.description}
Pattern: {spec.pattern.value if spec.pattern else "None"}
Style: {spec.style.value}

Methods:
{self._format_methods(spec.methods)}

Properties:
{self._format_properties(spec.properties)}

Requirements:
- Follow {spec.language.value} best practices
- Include type hints/annotations
- Add appropriate error handling
- Use {spec.style.value} style ({"minimal comments" if spec.style == CodeStyle.MINIMAL else "comprehensive documentation"})

Generate only the code, no explanations."""

        try:
            response = await self.model_router.generate(
                prompt,
                model_type='coding'
            )

            # Extract code from response
            code = self._extract_code(response, spec.language)
            return code

        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            return self._template_generate(spec)

    def _template_generate(self, spec: CodeSpec) -> str:
        """Generate code using templates."""
        template = self.templates.get_class_template(spec.language)

        # Build components
        init_params = self._build_init_params(spec)
        init_body = self._build_init_body(spec)
        properties = self._build_properties(spec)
        methods = self._build_methods(spec)

        # Fill template
        code = template.format(
            name=spec.name,
            description=spec.description,
            init_params=init_params,
            init_body=init_body,
            properties=properties,
            methods=methods
        )

        # Add imports
        imports = self._build_imports(spec)
        if imports:
            code = imports + "\n\n" + code

        return code.strip()

    def _build_init_params(self, spec: CodeSpec) -> str:
        """Build constructor parameters."""
        if not spec.properties:
            return ""

        params = []
        for prop in spec.properties:
            name = prop.get('name', 'value')
            ptype = self._map_type(prop.get('type', 'any'), spec.language)
            default = prop.get('default')

            if spec.language == Language.PYTHON:
                if default is not None:
                    params.append(f"{name}: {ptype} = {repr(default)}")
                else:
                    params.append(f"{name}: {ptype}")
            elif spec.language == Language.TYPESCRIPT:
                if default is not None:
                    params.append(f"{name}: {ptype} = {repr(default)}")
                else:
                    params.append(f"{name}: {ptype}")

        if spec.language == Language.PYTHON:
            return ", " + ", ".join(params) if params else ""
        return ", ".join(params)

    def _build_init_body(self, spec: CodeSpec) -> str:
        """Build constructor body."""
        if not spec.properties:
            return "        pass" if spec.language == Language.PYTHON else ""

        lines = []
        for prop in spec.properties:
            name = prop.get('name', 'value')

            if spec.language == Language.PYTHON:
                lines.append(f"        self.{name} = {name}")
            elif spec.language == Language.TYPESCRIPT:
                lines.append(f"        this.{name} = {name};")
            elif spec.language == Language.GO:
                lines.append(f"        {name}: {name},")

        return "\n".join(lines)

    def _build_properties(self, spec: CodeSpec) -> str:
        """Build property declarations."""
        if not spec.properties:
            return ""

        lines = []
        for prop in spec.properties:
            name = prop.get('name', 'value')
            ptype = self._map_type(prop.get('type', 'any'), spec.language)

            if spec.language == Language.TYPESCRIPT:
                lines.append(f"    private {name}: {ptype};")
            elif spec.language == Language.JAVA:
                lines.append(f"    private {ptype} {name};")
            elif spec.language == Language.GO:
                lines.append(f"    {name.title()} {ptype}")
            elif spec.language == Language.RUST:
                lines.append(f"    pub {name}: {ptype},")

        return "\n".join(lines)

    def _build_methods(self, spec: CodeSpec) -> str:
        """Build method definitions."""
        if not spec.methods:
            return ""

        methods = []
        for method in spec.methods:
            name = method.get('name', 'method')
            params = method.get('params', [])
            return_type = self._map_type(method.get('return_type', 'void'), spec.language)
            description = method.get('description', f'{name} method')
            body = method.get('body', 'pass')

            if spec.language == Language.PYTHON:
                param_str = ", ".join(
                    f"{p['name']}: {self._map_type(p.get('type', 'any'), spec.language)}"
                    for p in params
                )
                method_code = f'''    def {name}(self, {param_str}) -> {return_type}:
        """{description}"""
        {body}
'''
            elif spec.language == Language.TYPESCRIPT:
                param_str = ", ".join(
                    f"{p['name']}: {self._map_type(p.get('type', 'any'), spec.language)}"
                    for p in params
                )
                method_code = f'''    /**
     * {description}
     */
    public {name}({param_str}): {return_type} {{
        {body}
    }}
'''
            else:
                method_code = f"    // {name}: {description}\n"

            methods.append(method_code)

        return "\n".join(methods)

    def _build_imports(self, spec: CodeSpec) -> str:
        """Build import statements."""
        if not spec.imports:
            # Add default imports based on language
            if spec.language == Language.PYTHON:
                return "from typing import Any, Dict, List, Optional"
            elif spec.language == Language.TYPESCRIPT:
                return ""
            return ""

        if spec.language == Language.PYTHON:
            return "\n".join(f"from {imp} import *" for imp in spec.imports)
        elif spec.language in [Language.TYPESCRIPT, Language.JAVASCRIPT]:
            return "\n".join(f"import {{ {imp} }} from './{imp}';" for imp in spec.imports)
        elif spec.language == Language.GO:
            return 'import (\n' + "\n".join(f'    "{imp}"' for imp in spec.imports) + '\n)'

        return ""

    def _map_type(self, type_name: str, language: Language) -> str:
        """Map generic type to language-specific type."""
        mappings = self.type_mappings.get(language, self.type_mappings[Language.PYTHON])
        return mappings.get(type_name.lower(), type_name)

    async def _generate_tests(self, spec: CodeSpec, code: str) -> str:
        """Generate tests for the code."""
        if self.model_router:
            prompt = f"""Generate comprehensive unit tests for this {spec.language.value} code:

{code}

Requirements:
- Test all public methods
- Include edge cases
- Use appropriate testing framework
- Include setup/teardown if needed"""

            try:
                response = await self.model_router.generate(prompt, model_type='coding')
                return self._extract_code(response, spec.language)
            except:
                pass

        # Generate template tests
        if spec.language == Language.PYTHON:
            return f'''
import pytest
from {spec.name.lower()} import {spec.name}


class Test{spec.name}:
    """Tests for {spec.name}."""

    @pytest.fixture
    def instance(self):
        """Create test instance."""
        return {spec.name}()

    def test_creation(self, instance):
        """Test instance creation."""
        assert instance is not None
'''
        elif spec.language == Language.TYPESCRIPT:
            return f'''
import {{ {spec.name} }} from './{spec.name.lower()}';

describe('{spec.name}', () => {{
    let instance: {spec.name};

    beforeEach(() => {{
        instance = new {spec.name}();
    }});

    it('should create instance', () => {{
        expect(instance).toBeDefined();
    }});
}});
'''
        return ""

    def _generate_docs(self, spec: CodeSpec) -> str:
        """Generate documentation."""
        return f"""# {spec.name}

{spec.description}

## Overview

This module provides the `{spec.name}` class for {spec.description.lower()}.

## Usage

```{spec.language.value}
# Import the class
from {spec.name.lower()} import {spec.name}

# Create an instance
instance = {spec.name}()
```

## API Reference

### Constructor

Creates a new `{spec.name}` instance.

### Methods

{self._document_methods(spec.methods)}

## Properties

{self._document_properties(spec.properties)}
"""

    def _document_methods(self, methods: List[Dict]) -> str:
        """Document methods."""
        docs = []
        for method in methods:
            name = method.get('name', 'method')
            desc = method.get('description', '')
            docs.append(f"- `{name}()`: {desc}")
        return "\n".join(docs) if docs else "None"

    def _document_properties(self, properties: List[Dict]) -> str:
        """Document properties."""
        docs = []
        for prop in properties:
            name = prop.get('name', 'property')
            ptype = prop.get('type', 'any')
            docs.append(f"- `{name}` ({ptype})")
        return "\n".join(docs) if docs else "None"

    def _format_methods(self, methods: List[Dict]) -> str:
        """Format methods for prompt."""
        if not methods:
            return "None specified"
        return "\n".join(
            f"- {m.get('name')}: {m.get('description', '')}"
            for m in methods
        )

    def _format_properties(self, properties: List[Dict]) -> str:
        """Format properties for prompt."""
        if not properties:
            return "None specified"
        return "\n".join(
            f"- {p.get('name')} ({p.get('type', 'any')}): {p.get('description', '')}"
            for p in properties
        )

    def _extract_code(self, response: str, language: Language) -> str:
        """Extract code from AI response."""
        # Try to extract code blocks
        lang_names = {
            Language.PYTHON: ["python", "py"],
            Language.TYPESCRIPT: ["typescript", "ts"],
            Language.JAVASCRIPT: ["javascript", "js"],
            Language.GO: ["go", "golang"],
            Language.RUST: ["rust", "rs"]
        }

        names = lang_names.get(language, [language.value])

        for name in names:
            pattern = rf"```{name}\n(.*?)```"
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Try generic code block
        pattern = r"```\n(.*?)```"
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Return as-is if no code blocks
        return response.strip()


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Test code generator."""
    generator = CodeGenerator()

    spec = CodeSpec(
        name="UserService",
        description="Service for managing user operations",
        language=Language.PYTHON,
        pattern=Pattern.SERVICE,
        style=CodeStyle.DOCUMENTED,
        properties=[
            {"name": "db", "type": "object", "description": "Database connection"},
            {"name": "cache", "type": "object", "description": "Cache client"}
        ],
        methods=[
            {
                "name": "get_user",
                "description": "Retrieve user by ID",
                "params": [{"name": "user_id", "type": "string"}],
                "return_type": "object",
                "body": "return self.db.get('users', user_id)"
            },
            {
                "name": "create_user",
                "description": "Create a new user",
                "params": [{"name": "data", "type": "object"}],
                "return_type": "object",
                "body": "return self.db.insert('users', data)"
            }
        ],
        include_tests=True,
        include_docs=True
    )

    result = await generator.generate(spec)

    print("=" * 60)
    print("GENERATED CODE")
    print("=" * 60)
    print(result.code)

    print("\n" + "=" * 60)
    print("GENERATED TESTS")
    print("=" * 60)
    print(result.tests)

    print("\n" + "=" * 60)
    print("GENERATED DOCUMENTATION")
    print("=" * 60)
    print(result.documentation)


if __name__ == "__main__":
    asyncio.run(main())
