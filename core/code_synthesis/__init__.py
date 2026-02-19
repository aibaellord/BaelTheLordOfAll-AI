"""
⚡ UNIVERSAL CODE SYNTHESIS ENGINE ⚡
=====================================
Multi-language code generation.

Features:
- Language-agnostic AST
- Code generation
- Transpilation
- Code optimization
"""

from .code_core import (
    ASTNode,
    NodeType,
    Program,
    Function,
    Class,
    Variable,
    Expression,
    Statement,
    CodeBlock,
)

from .language_adapters import (
    LanguageAdapter,
    PythonAdapter,
    JavaScriptAdapter,
    TypeScriptAdapter,
    RustAdapter,
    GoAdapter,
)

from .code_generator import (
    CodeGenerator,
    GenerationContext,
    CodeTemplate,
    PatternLibrary,
)

from .transpiler import (
    Transpiler,
    TranspilationRule,
    ASTTransformer,
    CodeAnalyzer,
)

from .optimizer import (
    CodeOptimizer,
    OptimizationPass,
    DeadCodeElimination,
    ConstantFolding,
    InlineExpansion,
)

__all__ = [
    # Code Core
    'ASTNode',
    'NodeType',
    'Program',
    'Function',
    'Class',
    'Variable',
    'Expression',
    'Statement',
    'CodeBlock',

    # Language Adapters
    'LanguageAdapter',
    'PythonAdapter',
    'JavaScriptAdapter',
    'TypeScriptAdapter',
    'RustAdapter',
    'GoAdapter',

    # Code Generator
    'CodeGenerator',
    'GenerationContext',
    'CodeTemplate',
    'PatternLibrary',

    # Transpiler
    'Transpiler',
    'TranspilationRule',
    'ASTTransformer',
    'CodeAnalyzer',

    # Optimizer
    'CodeOptimizer',
    'OptimizationPass',
    'DeadCodeElimination',
    'ConstantFolding',
    'InlineExpansion',
]
