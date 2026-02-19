"""
⚡ LANGUAGE ADAPTERS ⚡
======================
Language-specific code generation.

Features:
- Python, JS, TS, Rust, Go
- Syntax generation
- Idiom translation
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .code_core import (
    ASTNode, NodeType, DataType, TypeInfo,
    Program, Function, Class, Variable, Expression, CodeBlock
)


class LanguageAdapter(ABC):
    """Base language adapter"""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        pass

    @abstractmethod
    def generate(self, node: ASTNode) -> str:
        """Generate code from AST"""
        pass

    @abstractmethod
    def indent(self, code: str, level: int = 1) -> str:
        """Indent code"""
        pass

    def type_to_string(self, type_info: TypeInfo) -> str:
        """Convert type to string"""
        return type_info.to_string(self.name) if type_info else ""


class PythonAdapter(LanguageAdapter):
    """Python code generator"""

    @property
    def name(self) -> str:
        return "python"

    @property
    def file_extension(self) -> str:
        return ".py"

    def indent(self, code: str, level: int = 1) -> str:
        indent_str = "    " * level
        lines = code.split("\n")
        return "\n".join(indent_str + line if line.strip() else line for line in lines)

    def generate(self, node: ASTNode) -> str:
        """Generate Python code"""
        if isinstance(node, Program):
            return self._gen_program(node)
        elif isinstance(node, Function):
            return self._gen_function(node)
        elif isinstance(node, Class):
            return self._gen_class(node)
        elif isinstance(node, Variable):
            return self._gen_variable(node)
        elif isinstance(node, Expression):
            return self._gen_expression(node)
        elif isinstance(node, CodeBlock):
            return self._gen_block(node)
        elif node.node_type == NodeType.RETURN:
            return f"return {self.generate(node.children[0]) if node.children else ''}"
        elif node.node_type == NodeType.IF:
            return self._gen_if(node)
        elif node.node_type == NodeType.FOR:
            return self._gen_for(node)
        elif node.node_type == NodeType.WHILE:
            return self._gen_while(node)
        return ""

    def _gen_program(self, prog: Program) -> str:
        lines = []

        # Imports
        for imp in prog.imports:
            lines.append(f"import {imp.name}")

        if prog.imports:
            lines.append("")

        # Content
        for child in prog.children:
            lines.append(self.generate(child))
            lines.append("")

        return "\n".join(lines)

    def _gen_function(self, func: Function) -> str:
        lines = []

        # Decorators
        for dec in func.decorators:
            lines.append(f"@{dec}")

        # Signature
        params = []
        for p in func.parameters:
            param_str = p.name
            if p.type_info:
                param_str += f": {self.type_to_string(p.type_info)}"
            if p.initial_value:
                param_str += f" = {self.generate(p.initial_value)}"
            params.append(param_str)

        async_prefix = "async " if func.is_async else ""
        return_type = f" -> {self.type_to_string(func.return_type)}" if func.return_type else ""

        lines.append(f"{async_prefix}def {func.name}({', '.join(params)}){return_type}:")

        # Body
        if func.body:
            body_code = self.generate(func.body)
            lines.append(self.indent(body_code if body_code.strip() else "pass"))
        else:
            lines.append(self.indent("pass"))

        return "\n".join(lines)

    def _gen_class(self, cls: Class) -> str:
        lines = []

        # Class definition
        bases = ", ".join(cls.base_classes) if cls.base_classes else ""
        lines.append(f"class {cls.name}({bases}):" if bases else f"class {cls.name}:")

        # Fields and __init__
        if cls.fields:
            init_params = ["self"]
            init_body = []
            for f in cls.fields:
                if f.type_info:
                    init_params.append(f"{f.name}: {self.type_to_string(f.type_info)}")
                else:
                    init_params.append(f.name)
                init_body.append(f"self.{f.name} = {f.name}")

            lines.append(self.indent(f"def __init__({', '.join(init_params)}):"))
            for line in init_body:
                lines.append(self.indent(line, 2))
            lines.append("")

        # Methods
        for method in cls.methods:
            if not method.parameters or method.parameters[0].name != "self":
                method.parameters.insert(0, Variable(name="self"))
            method_code = self._gen_function(method)
            lines.append(self.indent(method_code))
            lines.append("")

        if not cls.fields and not cls.methods:
            lines.append(self.indent("pass"))

        return "\n".join(lines)

    def _gen_variable(self, var: Variable) -> str:
        result = var.name
        if var.type_info:
            result += f": {self.type_to_string(var.type_info)}"
        if var.initial_value:
            result += f" = {self.generate(var.initial_value)}"
        return result

    def _gen_expression(self, expr: Expression) -> str:
        if expr.node_type == NodeType.LITERAL:
            if isinstance(expr.value, str):
                return f'"{expr.value}"'
            elif expr.value is None:
                return "None"
            elif isinstance(expr.value, bool):
                return "True" if expr.value else "False"
            return str(expr.value)

        elif expr.node_type == NodeType.IDENTIFIER:
            return expr.name

        elif expr.node_type == NodeType.BINARY_OP:
            left = self.generate(expr.left)
            right = self.generate(expr.right)
            return f"({left} {expr.operator} {right})"

        elif expr.node_type == NodeType.UNARY_OP:
            operand = self.generate(expr.left)
            return f"{expr.operator}{operand}"

        elif expr.node_type == NodeType.CALL:
            args = ", ".join(self.generate(c) for c in expr.children)
            return f"{expr.name}({args})"

        elif expr.node_type == NodeType.MEMBER_ACCESS:
            obj = self.generate(expr.left)
            return f"{obj}.{expr.name}"

        elif expr.node_type == NodeType.INDEX:
            obj = self.generate(expr.left)
            idx = self.generate(expr.right)
            return f"{obj}[{idx}]"

        elif expr.node_type == NodeType.ARRAY:
            elements = ", ".join(self.generate(c) for c in expr.children)
            return f"[{elements}]"

        return ""

    def _gen_block(self, block: CodeBlock) -> str:
        if not block.statements:
            return "pass"
        return "\n".join(self.generate(stmt) for stmt in block.statements)

    def _gen_if(self, node: ASTNode) -> str:
        # Expect: condition, then_block, [else_block]
        cond = self.generate(node.children[0]) if node.children else "True"
        then_block = self.generate(node.children[1]) if len(node.children) > 1 else "pass"

        lines = [f"if {cond}:", self.indent(then_block)]

        if len(node.children) > 2:
            else_block = self.generate(node.children[2])
            lines.extend(["else:", self.indent(else_block)])

        return "\n".join(lines)

    def _gen_for(self, node: ASTNode) -> str:
        var = node.metadata.get('var', 'i')
        iterable = self.generate(node.children[0]) if node.children else "range(10)"
        body = self.generate(node.children[1]) if len(node.children) > 1 else "pass"

        return f"for {var} in {iterable}:\n{self.indent(body)}"

    def _gen_while(self, node: ASTNode) -> str:
        cond = self.generate(node.children[0]) if node.children else "True"
        body = self.generate(node.children[1]) if len(node.children) > 1 else "pass"

        return f"while {cond}:\n{self.indent(body)}"


class JavaScriptAdapter(LanguageAdapter):
    """JavaScript code generator"""

    @property
    def name(self) -> str:
        return "javascript"

    @property
    def file_extension(self) -> str:
        return ".js"

    def indent(self, code: str, level: int = 1) -> str:
        indent_str = "  " * level
        lines = code.split("\n")
        return "\n".join(indent_str + line if line.strip() else line for line in lines)

    def generate(self, node: ASTNode) -> str:
        """Generate JavaScript code"""
        if isinstance(node, Program):
            return self._gen_program(node)
        elif isinstance(node, Function):
            return self._gen_function(node)
        elif isinstance(node, Class):
            return self._gen_class(node)
        elif isinstance(node, Variable):
            return self._gen_variable(node)
        elif isinstance(node, Expression):
            return self._gen_expression(node)
        elif isinstance(node, CodeBlock):
            return self._gen_block(node)
        elif node.node_type == NodeType.RETURN:
            return f"return {self.generate(node.children[0]) if node.children else ''};"
        return ""

    def _gen_program(self, prog: Program) -> str:
        lines = []

        for imp in prog.imports:
            lines.append(f"import {imp.name};")

        if prog.imports:
            lines.append("")

        for child in prog.children:
            lines.append(self.generate(child))
            lines.append("")

        return "\n".join(lines)

    def _gen_function(self, func: Function) -> str:
        params = ", ".join(p.name for p in func.parameters)
        async_prefix = "async " if func.is_async else ""

        lines = [f"{async_prefix}function {func.name}({params}) {{"]

        if func.body:
            body_code = self.generate(func.body)
            lines.append(self.indent(body_code))

        lines.append("}")
        return "\n".join(lines)

    def _gen_class(self, cls: Class) -> str:
        extends = f" extends {cls.base_classes[0]}" if cls.base_classes else ""
        lines = [f"class {cls.name}{extends} {{"]

        # Constructor
        if cls.fields:
            params = ", ".join(f.name for f in cls.fields)
            lines.append(self.indent(f"constructor({params}) {{"))
            for f in cls.fields:
                lines.append(self.indent(f"this.{f.name} = {f.name};", 2))
            lines.append(self.indent("}"))
            lines.append("")

        # Methods
        for method in cls.methods:
            async_prefix = "async " if method.is_async else ""
            params = ", ".join(p.name for p in method.parameters)
            lines.append(self.indent(f"{async_prefix}{method.name}({params}) {{"))
            if method.body:
                lines.append(self.indent(self.generate(method.body), 2))
            lines.append(self.indent("}"))
            lines.append("")

        lines.append("}")
        return "\n".join(lines)

    def _gen_variable(self, var: Variable) -> str:
        keyword = "const" if var.is_const else "let"
        result = f"{keyword} {var.name}"
        if var.initial_value:
            result += f" = {self.generate(var.initial_value)}"
        return result + ";"

    def _gen_expression(self, expr: Expression) -> str:
        if expr.node_type == NodeType.LITERAL:
            if isinstance(expr.value, str):
                return f'"{expr.value}"'
            elif expr.value is None:
                return "null"
            elif isinstance(expr.value, bool):
                return "true" if expr.value else "false"
            return str(expr.value)

        elif expr.node_type == NodeType.IDENTIFIER:
            return expr.name

        elif expr.node_type == NodeType.BINARY_OP:
            left = self.generate(expr.left)
            right = self.generate(expr.right)
            return f"({left} {expr.operator} {right})"

        elif expr.node_type == NodeType.CALL:
            args = ", ".join(self.generate(c) for c in expr.children)
            return f"{expr.name}({args})"

        elif expr.node_type == NodeType.ARRAY:
            elements = ", ".join(self.generate(c) for c in expr.children)
            return f"[{elements}]"

        return ""

    def _gen_block(self, block: CodeBlock) -> str:
        return "\n".join(self.generate(stmt) for stmt in block.statements)


class TypeScriptAdapter(JavaScriptAdapter):
    """TypeScript code generator"""

    @property
    def name(self) -> str:
        return "typescript"

    @property
    def file_extension(self) -> str:
        return ".ts"

    def _gen_function(self, func: Function) -> str:
        params = []
        for p in func.parameters:
            param_str = p.name
            if p.type_info:
                param_str += f": {self.type_to_string(p.type_info)}"
            params.append(param_str)

        return_type = f": {self.type_to_string(func.return_type)}" if func.return_type else ""
        async_prefix = "async " if func.is_async else ""

        lines = [f"{async_prefix}function {func.name}({', '.join(params)}){return_type} {{"]

        if func.body:
            lines.append(self.indent(self.generate(func.body)))

        lines.append("}")
        return "\n".join(lines)

    def _gen_variable(self, var: Variable) -> str:
        keyword = "const" if var.is_const else "let"
        result = f"{keyword} {var.name}"
        if var.type_info:
            result += f": {self.type_to_string(var.type_info)}"
        if var.initial_value:
            result += f" = {self.generate(var.initial_value)}"
        return result + ";"


class RustAdapter(LanguageAdapter):
    """Rust code generator"""

    @property
    def name(self) -> str:
        return "rust"

    @property
    def file_extension(self) -> str:
        return ".rs"

    def indent(self, code: str, level: int = 1) -> str:
        indent_str = "    " * level
        lines = code.split("\n")
        return "\n".join(indent_str + line if line.strip() else line for line in lines)

    def generate(self, node: ASTNode) -> str:
        if isinstance(node, Function):
            return self._gen_function(node)
        elif isinstance(node, Class):
            return self._gen_struct(node)
        elif isinstance(node, Variable):
            return self._gen_variable(node)
        elif isinstance(node, Expression):
            return self._gen_expression(node)
        return ""

    def _gen_function(self, func: Function) -> str:
        params = []
        for p in func.parameters:
            type_str = self.type_to_string(p.type_info) if p.type_info else "i32"
            params.append(f"{p.name}: {type_str}")

        return_type = f" -> {self.type_to_string(func.return_type)}" if func.return_type else ""
        pub = "pub " if func.is_public else ""
        async_prefix = "async " if func.is_async else ""

        lines = [f"{pub}{async_prefix}fn {func.name}({', '.join(params)}){return_type} {{"]

        if func.body:
            lines.append(self.indent(self.generate(func.body)))

        lines.append("}")
        return "\n".join(lines)

    def _gen_struct(self, cls: Class) -> str:
        lines = [f"pub struct {cls.name} {{"]

        for f in cls.fields:
            type_str = self.type_to_string(f.type_info) if f.type_info else "i32"
            pub = "pub " if f.is_public else ""
            lines.append(self.indent(f"{pub}{f.name}: {type_str},"))

        lines.append("}")

        # impl block
        if cls.methods:
            lines.append("")
            lines.append(f"impl {cls.name} {{")
            for method in cls.methods:
                method_code = self._gen_function(method)
                lines.append(self.indent(method_code))
            lines.append("}")

        return "\n".join(lines)

    def _gen_variable(self, var: Variable) -> str:
        keyword = "let" if not var.is_const else "const"
        mut = " mut" if not var.is_const else ""
        result = f"{keyword}{mut} {var.name}"
        if var.type_info:
            result += f": {self.type_to_string(var.type_info)}"
        if var.initial_value:
            result += f" = {self.generate(var.initial_value)}"
        return result + ";"

    def _gen_expression(self, expr: Expression) -> str:
        if expr.node_type == NodeType.LITERAL:
            if isinstance(expr.value, str):
                return f'"{expr.value}"'
            return str(expr.value).lower()
        elif expr.node_type == NodeType.IDENTIFIER:
            return expr.name
        return ""


class GoAdapter(LanguageAdapter):
    """Go code generator"""

    @property
    def name(self) -> str:
        return "go"

    @property
    def file_extension(self) -> str:
        return ".go"

    def indent(self, code: str, level: int = 1) -> str:
        indent_str = "\t" * level
        lines = code.split("\n")
        return "\n".join(indent_str + line if line.strip() else line for line in lines)

    def generate(self, node: ASTNode) -> str:
        if isinstance(node, Function):
            return self._gen_function(node)
        elif isinstance(node, Class):
            return self._gen_struct(node)
        elif isinstance(node, Variable):
            return self._gen_variable(node)
        return ""

    def _gen_function(self, func: Function) -> str:
        params = []
        for p in func.parameters:
            type_str = self.type_to_string(p.type_info) if p.type_info else "int"
            params.append(f"{p.name} {type_str}")

        return_type = f" {self.type_to_string(func.return_type)}" if func.return_type else ""

        lines = [f"func {func.name}({', '.join(params)}){return_type} {{"]

        if func.body:
            lines.append(self.indent(self.generate(func.body)))

        lines.append("}")
        return "\n".join(lines)

    def _gen_struct(self, cls: Class) -> str:
        lines = [f"type {cls.name} struct {{"]

        for f in cls.fields:
            type_str = self.type_to_string(f.type_info) if f.type_info else "int"
            name = f.name.title()  # Go uses Title case for public
            lines.append(self.indent(f"{name} {type_str}"))

        lines.append("}")
        return "\n".join(lines)

    def _gen_variable(self, var: Variable) -> str:
        type_str = self.type_to_string(var.type_info) if var.type_info else ""
        if var.initial_value:
            return f"{var.name} := {self.generate(var.initial_value)}"
        elif type_str:
            return f"var {var.name} {type_str}"
        return f"var {var.name}"


# Export all
__all__ = [
    'LanguageAdapter',
    'PythonAdapter',
    'JavaScriptAdapter',
    'TypeScriptAdapter',
    'RustAdapter',
    'GoAdapter',
]
