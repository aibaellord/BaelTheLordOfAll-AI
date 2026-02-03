"""
FastAPI integration for GraphQL API.

Provides GraphQL endpoint with Strawberry and GraphQL Playground.
"""

from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from strawberry.subscriptions import (GRAPHQL_TRANSPORT_WS_PROTOCOL,
                                      GRAPHQL_WS_PROTOCOL)

from .schema import schema


def create_graphql_router() -> GraphQLRouter:
    """
    Create GraphQL router with Strawberry.

    Returns:
        GraphQLRouter: Configured GraphQL router
    """
    graphql_app = GraphQLRouter(
        schema,
        subscription_protocols=[
            GRAPHQL_TRANSPORT_WS_PROTOCOL,
            GRAPHQL_WS_PROTOCOL,
        ],
        graphiql=True,  # Enable GraphQL Playground
    )

    return graphql_app


def mount_graphql(app: FastAPI, path: str = "/graphql"):
    """
    Mount GraphQL router to FastAPI app.

    Args:
        app: FastAPI application
        path: Path to mount GraphQL endpoint
    """
    graphql_router = create_graphql_router()
    app.include_router(graphql_router, prefix=path)

    return app


# Example usage
if __name__ == "__main__":
    from fastapi import FastAPI

    app = FastAPI(title="BAEL GraphQL API")
    mount_graphql(app)

    print("GraphQL API mounted at /graphql")
    print("GraphQL Playground available at http://localhost:8000/graphql")
