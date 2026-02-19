"""
⚡ CODE GENERATOR ⚡
===================
High-level code generation.

Features:
- Template-based generation
- Pattern library
- Context-aware generation
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import uuid

from .code_core import (
    ASTNode, NodeType, DataType, TypeInfo,
    Program, Function, Class, Variable, Expression, CodeBlock
)
from .language_adapters import (
    LanguageAdapter, PythonAdapter, JavaScriptAdapter,
    TypeScriptAdapter, RustAdapter, GoAdapter
)


@dataclass
class GenerationContext:
    """Context for code generation"""
    language: str = "python"

    # Options
    use_types: bool = True
    use_async: bool = False
    use_classes: bool = True

    # Naming conventions
    class_prefix: str = ""
    function_prefix: str = ""
    variable_style: str = "snake_case"  # snake_case, camelCase, PascalCase

    # Imports to include
    imports: List[str] = field(default_factory=list)

    # Custom metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def format_name(self, name: str, style: str = None) -> str:
        """Format name according to style"""
        style = style or self.variable_style

        words = name.replace('_', ' ').replace('-', ' ').split()

        if style == "snake_case":
            return '_'.join(w.lower() for w in words)
        elif style == "camelCase":
            return words[0].lower() + ''.join(w.title() for w in words[1:])
        elif style == "PascalCase":
            return ''.join(w.title() for w in words)

        return name


@dataclass
class CodeTemplate:
    """A code template"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""

    # Template type
    template_type: str = ""  # function, class, pattern

    # Template content (AST or code string)
    ast_template: Optional[ASTNode] = None
    code_template: str = ""

    # Parameters
    parameters: List[str] = field(default_factory=list)

    # Languages supported
    languages: List[str] = field(default_factory=lambda: ["python"])

    def instantiate(self, params: Dict[str, Any]) -> ASTNode:
        """Create AST from template with parameters"""
        if self.ast_template:
            node = self.ast_template.clone()
            self._apply_params(node, params)
            return node
        return ASTNode()

    def _apply_params(self, node: ASTNode, params: Dict[str, Any]):
        """Apply parameters to AST node"""
        # Replace placeholder names
        if node.name and node.name.startswith("$"):
            param_name = node.name[1:]
            if param_name in params:
                node.name = str(params[param_name])

        # Replace values
        if node.value and isinstance(node.value, str) and node.value.startswith("$"):
            param_name = node.value[1:]
            if param_name in params:
                node.value = params[param_name]

        # Recurse
        for child in node.children:
            self._apply_params(child, params)


class PatternLibrary:
    """Library of code patterns"""

    def __init__(self):
        self.patterns: Dict[str, CodeTemplate] = {}
        self._init_default_patterns()

    def _init_default_patterns(self):
        """Initialize default patterns"""
        # Singleton pattern
        self.add_pattern(CodeTemplate(
            name="singleton",
            template_type="class",
            parameters=["class_name"],
            languages=["python", "javascript", "typescript"]
        ))

        # Factory pattern
        self.add_pattern(CodeTemplate(
            name="factory",
            template_type="class",
            parameters=["factory_name", "product_type"],
            languages=["python", "javascript", "typescript"]
        ))

        # Observer pattern
        self.add_pattern(CodeTemplate(
            name="observer",
            template_type="class",
            parameters=["subject_name", "observer_name"],
            languages=["python", "javascript", "typescript"]
        ))

        # CRUD operations
        self.add_pattern(CodeTemplate(
            name="crud",
            template_type="functions",
            parameters=["entity_name", "fields"],
            languages=["python", "javascript", "typescript"]
        ))

    def add_pattern(self, template: CodeTemplate):
        """Add pattern to library"""
        self.patterns[template.name] = template

    def get_pattern(self, name: str) -> Optional[CodeTemplate]:
        """Get pattern by name"""
        return self.patterns.get(name)

    def list_patterns(self) -> List[str]:
        """List available patterns"""
        return list(self.patterns.keys())


class CodeGenerator:
    """
    High-level code generation.
    """

    def __init__(self):
        self.adapters: Dict[str, LanguageAdapter] = {
            "python": PythonAdapter(),
            "javascript": JavaScriptAdapter(),
            "typescript": TypeScriptAdapter(),
            "rust": RustAdapter(),
            "go": GoAdapter(),
        }

        self.pattern_library = PatternLibrary()
        self.context = GenerationContext()

    def set_language(self, language: str):
        """Set target language"""
        self.context.language = language

    def get_adapter(self, language: str = None) -> LanguageAdapter:
        """Get adapter for language"""
        lang = language or self.context.language
        return self.adapters.get(lang, self.adapters["python"])

    def generate(self, node: ASTNode, language: str = None) -> str:
        """Generate code from AST"""
        adapter = self.get_adapter(language)
        return adapter.generate(node)

    def create_function(
        self,
        name: str,
        parameters: List[Dict[str, Any]] = None,
        return_type: DataType = None,
        body: List[ASTNode] = None,
        is_async: bool = False
    ) -> Function:
        """Create a function"""
        func = Function(
            name=self.context.format_name(name),
            is_async=is_async or self.context.use_async
        )

        # Parameters
        for p in (parameters or []):
            param = Variable(
                name=p.get("name", ""),
                type_info=TypeInfo(base_type=p.get("type", DataType.ANY))
            )
            func.add_parameter(param)

        # Return type
        if return_type:
            func.return_type = TypeInfo(base_type=return_type)

        # Body
        if body:
            block = CodeBlock()
            for stmt in body:
                block.add_statement(stmt)
            func.set_body(block)

        return func

    def create_class(
        self,
        name: str,
        fields: List[Dict[str, Any]] = None,
        methods: List[Function] = None,
        bases: List[str] = None
    ) -> Class:
        """Create a class"""
        cls = Class(
            name=self.context.format_name(name, "PascalCase"),
            base_classes=bases or []
        )

        # Fields
        for f in (fields or []):
            field = Variable(
                name=f.get("name", ""),
                type_info=TypeInfo(base_type=f.get("type", DataType.ANY)),
                is_public=f.get("public", True)
            )
            cls.add_field(field)

        # Methods
        for method in (methods or []):
            cls.add_method(method)

        return cls

    def create_program(
        self,
        content: List[ASTNode],
        imports: List[str] = None
    ) -> Program:
        """Create a program"""
        prog = Program(language=self.context.language)

        for imp in (imports or self.context.imports):
            imp_node = ASTNode(node_type=NodeType.IMPORT, name=imp)
            prog.add_import(imp_node)

        for node in content:
            prog.add_child(node)

        return prog

    def from_pattern(
        self,
        pattern_name: str,
        params: Dict[str, Any]
    ) -> Optional[ASTNode]:
        """Generate code from pattern"""
        pattern = self.pattern_library.get_pattern(pattern_name)
        if not pattern:
            return None

        return pattern.instantiate(params)

    def generate_crud(
        self,
        entity_name: str,
        fields: List[Dict[str, Any]]
    ) -> List[Function]:
        """Generate CRUD functions"""
        functions = []

        # Create
        create_func = self.create_function(
            name=f"create_{entity_name}",
            parameters=fields,
            return_type=DataType.OBJECT
        )
        functions.append(create_func)

        # Read
        read_func = self.create_function(
            name=f"get_{entity_name}",
            parameters=[{"name": "id", "type": DataType.STRING}],
            return_type=DataType.OBJECT
        )
        functions.append(read_func)

        # Update
        update_func = self.create_function(
            name=f"update_{entity_name}",
            parameters=[{"name": "id", "type": DataType.STRING}] + fields,
            return_type=DataType.OBJECT
        )
        functions.append(update_func)

        # Delete
        delete_func = self.create_function(
            name=f"delete_{entity_name}",
            parameters=[{"name": "id", "type": DataType.STRING}],
            return_type=DataType.BOOL
        )
        functions.append(delete_func)

        # List
        list_func = self.create_function(
            name=f"list_{entity_name}s",
            parameters=[],
            return_type=DataType.ARRAY
        )
        functions.append(list_func)

        return functions

    def generate_api_handler(
        self,
        route: str,
        method: str = "GET",
        handler_name: str = None
    ) -> Function:
        """Generate API handler function"""
        handler_name = handler_name or f"handle_{method.lower()}_{route.replace('/', '_')}"

        func = self.create_function(
            name=handler_name,
            parameters=[
                {"name": "request", "type": DataType.OBJECT},
                {"name": "response", "type": DataType.OBJECT}
            ],
            is_async=True
        )

        func.metadata = {
            "route": route,
            "method": method
        }

        return func

    def transpile(
        self,
        code: str,
        from_language: str,
        to_language: str
    ) -> str:
        """Transpile code between languages (simplified)"""
        # This is a simplified transpilation
        # Full implementation would parse source and regenerate

        replacements = {
            ("python", "javascript"): [
                ("def ", "function "),
                ("elif ", "} else if ("),
                ("else:", "} else {"),
                ("True", "true"),
                ("False", "false"),
                ("None", "null"),
                ("print(", "console.log("),
            ],
            ("javascript", "python"): [
                ("function ", "def "),
                ("} else if (", "elif "),
                ("} else {", "else:"),
                ("true", "True"),
                ("false", "False"),
                ("null", "None"),
                ("console.log(", "print("),
                ("let ", ""),
                ("const ", ""),
                (";", ""),
            ]
        }

        result = code
        for old, new in replacements.get((from_language, to_language), []):
            result = result.replace(old, new)

        return result


# Export all
__all__ = [
    'GenerationContext',
    'CodeTemplate',
    'PatternLibrary',
    'CodeGenerator',
]
