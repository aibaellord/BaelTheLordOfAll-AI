"""
GraphQL API module for BAEL.

Provides GraphQL schema, resolvers, and subscriptions for flexible querying.
"""

from .resolvers import *
from .schema import schema
from .types import *

__all__ = ['schema']
