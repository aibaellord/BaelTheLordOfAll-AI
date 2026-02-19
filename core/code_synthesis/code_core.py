"""
⚡ CODE CORE ⚡
==============
Core code representation.

Features:
- Universal AST
- Language-agnostic nodes
- Code structure
"""

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Union
import uuid


class NodeType(Enum):
    """AST node types"""
    # Program structure
    PROGRAM = auto()
    MODULE = auto()
    IMPORT = auto()

    # Declarations
    FUNCTION = auto()
    CLASS = auto()
    INTERFACE = auto()
    VARIABLE = auto()
    CONSTANT = auto()
    PARAMETER = auto()

    # Statements
    BLOCK = auto()
    IF = auto()
    ELSE = auto()
    FOR = auto()
    WHILE = auto()
    DO_WHILE = auto()
    SWITCH = auto()
    CASE = auto()
    TRY = auto()
    CATCH = auto()
    FINALLY = auto()
    RETURN = auto()
    BREAK = auto()
    CONTINUE = auto()
    THROW = auto()

    # Expressions
    BINARY_OP = auto()
    UNARY_OP = auto()
    CALL = auto()
    MEMBER_ACCESS = auto()
    INDEX = auto()
    CONDITIONAL = auto()
    LAMBDA = auto()

    # Literals
    LITERAL = auto()
    IDENTIFIER = auto()
    ARRAY = auto()
    OBJECT = auto()

    # Types
    TYPE = auto()
    GENERIC = auto()


class DataType(Enum):
    """Data types"""
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    BOOL = auto()
    VOID = auto()
    ANY = auto()
    ARRAY = auto()
    OBJECT = auto()
    FUNCTION = auto()
    NULL = auto()
    UNDEFINED = auto()
    CUSTOM = auto()


@dataclass
class TypeInfo:
    """Type information"""
    base_type: DataType = DataType.ANY
    custom_name: str = ""
    is_nullable: bool = False
    is_array: bool = False
    array_element_type: Optional['TypeInfo'] = None
    generic_params: List['TypeInfo'] = field(default_factory=list)

    def to_string(self, language: str = "python") -> str:
        """Convert to language-specific type string"""
        if self.base_type == DataType.INT:
            return {"python": "int", "typescript": "number", "go": "int", "rust": "i32"}.get(language, "int")
        elif self.base_type == DataType.FLOAT:
            return {"python": "float", "typescript": "number", "go": "float64", "rust": "f64"}.get(language, "float")
        elif self.base_type == DataType.STRING:
            return {"python": "str", "typescript": "string", "go": "string", "rust": "String"}.get(language, "string")
        elif self.base_type == DataType.BOOL:
            return {"python": "bool", "typescript": "boolean", "go": "bool", "rust": "bool"}.get(language, "bool")
        elif self.base_type == DataType.VOID:
            return {"python": "None", "typescript": "void", "go": "", "rust": "()"}.get(language, "void")
        elif self.base_type == DataType.ARRAY:
            elem = self.array_element_type.to_string(language) if self.array_element_type else "any"
            return {"python": f"List[{elem}]", "typescript": f"{elem}[]", "go": f"[]{elem}", "rust": f"Vec<{elem}>"}.get(language, f"array<{elem}>")
        elif self.base_type == DataType.CUSTOM:
            return self.custom_name
        return "any"


@dataclass
class ASTNode:
    """Base AST node"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_type: NodeType = NodeType.LITERAL

    # Children
    children: List['ASTNode'] = field(default_factory=list)

    # Parent reference
    parent_id: Optional[str] = None

    # Source location
    line: int = 0
    column: int = 0

    # Value for literals
    value: Any = None

    # Name for identifiers
    name: str = ""

    # Type information
    type_info: Optional[TypeInfo] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_child(self, child: 'ASTNode'):
        """Add child node"""
        child.parent_id = self.id
        self.children.append(child)

    def find_by_type(self, node_type: NodeType) -> List['ASTNode']:
        """Find all nodes of given type"""
        result = []
        if self.node_type == node_type:
            result.append(self)
        for child in self.children:
            result.extend(child.find_by_type(node_type))
        return result

    def clone(self) -> 'ASTNode':
        """Create deep copy"""
        cloned = ASTNode(
            node_type=self.node_type,
            value=self.value,
            name=self.name,
            line=self.line,
            column=self.column,
            type_info=self.type_info,
            metadata=self.metadata.copy()
        )
        for child in self.children:
            cloned.add_child(child.clone())
        return cloned


@dataclass
class Program(ASTNode):
    """Program/module node"""
    node_type: NodeType = NodeType.PROGRAM

    language: str = ""
    imports: List['ASTNode'] = field(default_factory=list)

    def add_import(self, import_node: ASTNode):
        """Add import"""
        self.imports.append(import_node)

    def get_functions(self) -> List['Function']:
        """Get all function declarations"""
        return [c for c in self.children if isinstance(c, Function)]

    def get_classes(self) -> List['Class']:
        """Get all class declarations"""
        return [c for c in self.children if isinstance(c, Class)]


@dataclass
class Function(ASTNode):
    """Function declaration"""
    node_type: NodeType = NodeType.FUNCTION

    parameters: List['Variable'] = field(default_factory=list)
    return_type: Optional[TypeInfo] = None
    body: Optional['CodeBlock'] = None

    is_async: bool = False
    is_static: bool = False
    is_public: bool = True

    decorators: List[str] = field(default_factory=list)

    def add_parameter(self, param: 'Variable'):
        """Add parameter"""
        self.parameters.append(param)

    def set_body(self, body: 'CodeBlock'):
        """Set function body"""
        self.body = body
        self.add_child(body)


@dataclass
class Class(ASTNode):
    """Class declaration"""
    node_type: NodeType = NodeType.CLASS

    base_classes: List[str] = field(default_factory=list)
    interfaces: List[str] = field(default_factory=list)

    fields: List['Variable'] = field(default_factory=list)
    methods: List['Function'] = field(default_factory=list)

    is_abstract: bool = False

    def add_field(self, field: 'Variable'):
        """Add field"""
        self.fields.append(field)
        self.add_child(field)

    def add_method(self, method: 'Function'):
        """Add method"""
        self.methods.append(method)
        self.add_child(method)


@dataclass
class Variable(ASTNode):
    """Variable/field declaration"""
    node_type: NodeType = NodeType.VARIABLE

    initial_value: Optional['Expression'] = None
    is_const: bool = False
    is_static: bool = False
    is_public: bool = True


@dataclass
class Expression(ASTNode):
    """Expression node"""
    node_type: NodeType = NodeType.BINARY_OP

    operator: str = ""
    left: Optional['ASTNode'] = None
    right: Optional['ASTNode'] = None

    @staticmethod
    def binary(op: str, left: 'ASTNode', right: 'ASTNode') -> 'Expression':
        """Create binary expression"""
        expr = Expression(operator=op, left=left, right=right)
        expr.add_child(left)
        expr.add_child(right)
        return expr

    @staticmethod
    def unary(op: str, operand: 'ASTNode') -> 'Expression':
        """Create unary expression"""
        expr = Expression(node_type=NodeType.UNARY_OP, operator=op, left=operand)
        expr.add_child(operand)
        return expr

    @staticmethod
    def call(callee: str, args: List['ASTNode']) -> 'Expression':
        """Create function call"""
        expr = Expression(node_type=NodeType.CALL, name=callee)
        for arg in args:
            expr.add_child(arg)
        return expr

    @staticmethod
    def literal(value: Any, type_info: TypeInfo = None) -> 'Expression':
        """Create literal"""
        expr = Expression(node_type=NodeType.LITERAL, value=value)
        expr.type_info = type_info
        return expr

    @staticmethod
    def identifier(name: str, type_info: TypeInfo = None) -> 'Expression':
        """Create identifier"""
        expr = Expression(node_type=NodeType.IDENTIFIER, name=name)
        expr.type_info = type_info
        return expr


@dataclass
class Statement(ASTNode):
    """Statement node"""
    pass


@dataclass
class CodeBlock(ASTNode):
    """Block of statements"""
    node_type: NodeType = NodeType.BLOCK

    statements: List[Statement] = field(default_factory=list)

    def add_statement(self, stmt: Statement):
        """Add statement"""
        self.statements.append(stmt)
        self.add_child(stmt)


# Export all
__all__ = [
    'NodeType',
    'DataType',
    'TypeInfo',
    'ASTNode',
    'Program',
    'Function',
    'Class',
    'Variable',
    'Expression',
    'Statement',
    'CodeBlock',
]
