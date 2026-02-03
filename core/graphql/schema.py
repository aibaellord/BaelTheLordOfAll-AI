"""
GraphQL schema definition for BAEL API.
"""

import strawberry

from .resolvers import Mutation, Query, Subscription

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription
)
