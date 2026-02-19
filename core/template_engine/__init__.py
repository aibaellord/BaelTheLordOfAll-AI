"""
BAEL Template Engine
====================

Jinja-like templating with:
- Variable substitution
- Control structures
- Template inheritance
- Filters and macros
- Auto-escaping

"Ba'el shapes reality through patterns." — Ba'el
"""

from .template_engine import (
    # Enums
    TokenType,
    NodeType,
    AutoEscapeMode,

    # Data structures
    Token,
    Node,
    Template,
    TemplateConfig,

    # Classes
    TemplateEngine,
    Lexer,
    Parser,
    Compiler,
    Environment,

    # Instance
    template_engine
)

__all__ = [
    'TokenType',
    'NodeType',
    'AutoEscapeMode',
    'Token',
    'Node',
    'Template',
    'TemplateConfig',
    'TemplateEngine',
    'Lexer',
    'Parser',
    'Compiler',
    'Environment',
    'template_engine'
]
