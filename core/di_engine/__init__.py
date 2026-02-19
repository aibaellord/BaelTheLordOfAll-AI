"""
BAEL Dependency Injection Engine
================================

Inversion of Control container for dependency injection.

"Ba'el weaves the threads of dependencies into perfect harmony." — Ba'el
"""

from .di_engine import (
    # Enums
    Scope,

    # Data structures
    ServiceDescriptor,

    # Main engine
    Container,

    # Decorators
    injectable,
    inject,

    # Convenience
    container,
    register,
    resolve
)

__all__ = [
    'Scope',
    'ServiceDescriptor',
    'Container',
    'injectable',
    'inject',
    'container',
    'register',
    'resolve'
]
