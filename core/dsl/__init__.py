"""
BAEL - Domain Specific Language Module
Custom DSL for reasoning rules.
"""

from .reasoning_dsl import (  # Enums; Token & Lexer; AST Nodes; Rule; Parser; Engine; Factory functions
    ASTNode, BinaryOpNode, DSLBuilder, FunctionCallNode, IdentifierNode, Lexer,
    LiteralNode, Operator, Parser, QuantifierNode, Rule, RuleEngine, Token,
    TokenType, UnaryOpNode, compile_rules, create_dsl_builder,
    create_rule_engine)

__all__ = [
    # Enums
    "TokenType",
    "Operator",

    # Token & Lexer
    "Token",
    "Lexer",

    # AST Nodes
    "ASTNode",
    "LiteralNode",
    "IdentifierNode",
    "BinaryOpNode",
    "UnaryOpNode",
    "QuantifierNode",
    "FunctionCallNode",

    # Rule
    "Rule",

    # Parser
    "Parser",

    # Engine
    "RuleEngine",
    "DSLBuilder",

    # Factory functions
    "create_rule_engine",
    "create_dsl_builder",
    "compile_rules"
]
