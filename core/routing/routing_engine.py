#!/usr/bin/env python3
"""
BAEL - Routing Engine
Request routing and dispatch for agents.

Features:
- URL/path routing
- Pattern matching
- Route priorities
- Middleware support
- Route groups
"""

import asyncio
import hashlib
import json
import math
import random
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Pattern, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class RouteMethod(Enum):
    """HTTP-like methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    ANY = "ANY"


class MatchType(Enum):
    """Route matching types."""
    EXACT = "exact"
    PREFIX = "prefix"
    REGEX = "regex"
    PATTERN = "pattern"


class RouteStatus(Enum):
    """Route statuses."""
    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


class MiddlewarePosition(Enum):
    """Middleware positions."""
    BEFORE = "before"
    AFTER = "after"


class DispatchResult(Enum):
    """Dispatch results."""
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    ERROR = "error"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class RouteMatch:
    """Result of route matching."""
    matched: bool = False
    route: Optional['Route'] = None
    params: Dict[str, str] = field(default_factory=dict)
    score: float = 0.0


@dataclass
class Route:
    """A route definition."""
    route_id: str = ""
    path: str = ""
    handler: Optional[Callable] = None
    methods: List[RouteMethod] = field(default_factory=list)
    match_type: MatchType = MatchType.EXACT
    priority: int = 0
    status: RouteStatus = RouteStatus.ACTIVE
    middleware: List[Callable] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    name: str = ""

    def __post_init__(self):
        if not self.route_id:
            self.route_id = str(uuid.uuid4())[:8]
        if not self.methods:
            self.methods = [RouteMethod.ANY]


@dataclass
class Request:
    """A request to route."""
    request_id: str = ""
    path: str = ""
    method: RouteMethod = RouteMethod.GET
    params: Dict[str, str] = field(default_factory=dict)
    query: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.request_id:
            self.request_id = str(uuid.uuid4())[:8]


@dataclass
class Response:
    """A response from handler."""
    response_id: str = ""
    status: int = 200
    data: Any = None
    headers: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None

    def __post_init__(self):
        if not self.response_id:
            self.response_id = str(uuid.uuid4())[:8]


@dataclass
class RouteGroup:
    """A group of routes."""
    group_id: str = ""
    prefix: str = ""
    routes: List[Route] = field(default_factory=list)
    middleware: List[Callable] = field(default_factory=list)
    name: str = ""

    def __post_init__(self):
        if not self.group_id:
            self.group_id = str(uuid.uuid4())[:8]


# =============================================================================
# PATTERN MATCHER
# =============================================================================

class PatternMatcher:
    """Match paths against patterns."""

    PARAM_PATTERN = re.compile(r'\{(\w+)(?::([^}]+))?\}')

    def __init__(self):
        self._compiled: Dict[str, Pattern] = {}

    def match_exact(self, path: str, pattern: str) -> RouteMatch:
        """Exact path matching."""
        if path == pattern:
            return RouteMatch(matched=True, score=1.0)
        return RouteMatch(matched=False)

    def match_prefix(self, path: str, pattern: str) -> RouteMatch:
        """Prefix matching."""
        if path.startswith(pattern):
            score = len(pattern) / len(path) if path else 0
            return RouteMatch(matched=True, score=score)
        return RouteMatch(matched=False)

    def match_regex(self, path: str, pattern: str) -> RouteMatch:
        """Regex matching."""
        if pattern not in self._compiled:
            try:
                self._compiled[pattern] = re.compile(pattern)
            except re.error:
                return RouteMatch(matched=False)

        match = self._compiled[pattern].match(path)

        if match:
            return RouteMatch(
                matched=True,
                params=match.groupdict(),
                score=0.8
            )

        return RouteMatch(matched=False)

    def match_pattern(self, path: str, pattern: str) -> RouteMatch:
        """Pattern matching with parameters."""
        regex_pattern = self._pattern_to_regex(pattern)

        if regex_pattern not in self._compiled:
            self._compiled[regex_pattern] = re.compile(f'^{regex_pattern}$')

        match = self._compiled[regex_pattern].match(path)

        if match:
            return RouteMatch(
                matched=True,
                params=match.groupdict(),
                score=0.9
            )

        return RouteMatch(matched=False)

    def _pattern_to_regex(self, pattern: str) -> str:
        """Convert URL pattern to regex."""
        def replace_param(match):
            name = match.group(1)
            regex = match.group(2) or r'[^/]+'
            return f'(?P<{name}>{regex})'

        escaped = re.escape(pattern)
        escaped = escaped.replace(r'\{', '{').replace(r'\}', '}')

        return self.PARAM_PATTERN.sub(replace_param, escaped)

    def match(
        self,
        path: str,
        pattern: str,
        match_type: MatchType
    ) -> RouteMatch:
        """Match path against pattern."""
        if match_type == MatchType.EXACT:
            return self.match_exact(path, pattern)
        elif match_type == MatchType.PREFIX:
            return self.match_prefix(path, pattern)
        elif match_type == MatchType.REGEX:
            return self.match_regex(path, pattern)
        elif match_type == MatchType.PATTERN:
            return self.match_pattern(path, pattern)

        return RouteMatch(matched=False)


# =============================================================================
# ROUTE REGISTRY
# =============================================================================

class RouteRegistry:
    """Registry for routes."""

    def __init__(self):
        self._routes: Dict[str, Route] = {}
        self._by_path: Dict[str, List[Route]] = defaultdict(list)
        self._by_name: Dict[str, Route] = {}

    def add(self, route: Route) -> Route:
        """Add a route."""
        self._routes[route.route_id] = route
        self._by_path[route.path].append(route)

        if route.name:
            self._by_name[route.name] = route

        self._by_path[route.path].sort(
            key=lambda r: r.priority,
            reverse=True
        )

        return route

    def get(self, route_id: str) -> Optional[Route]:
        """Get route by ID."""
        return self._routes.get(route_id)

    def get_by_name(self, name: str) -> Optional[Route]:
        """Get route by name."""
        return self._by_name.get(name)

    def get_by_path(self, path: str) -> List[Route]:
        """Get routes by path."""
        return self._by_path.get(path, [])

    def remove(self, route_id: str) -> bool:
        """Remove a route."""
        route = self._routes.get(route_id)

        if not route:
            return False

        del self._routes[route_id]

        if route.path in self._by_path:
            self._by_path[route.path] = [
                r for r in self._by_path[route.path]
                if r.route_id != route_id
            ]

        if route.name in self._by_name:
            del self._by_name[route.name]

        return True

    def update_status(
        self,
        route_id: str,
        status: RouteStatus
    ) -> bool:
        """Update route status."""
        route = self._routes.get(route_id)

        if route:
            route.status = status
            return True

        return False

    def count(self) -> int:
        """Count routes."""
        return len(self._routes)

    def all(self) -> List[Route]:
        """Get all routes."""
        return list(self._routes.values())

    def active(self) -> List[Route]:
        """Get active routes."""
        return [r for r in self._routes.values()
                if r.status == RouteStatus.ACTIVE]


# =============================================================================
# MIDDLEWARE CHAIN
# =============================================================================

class MiddlewareChain:
    """Chain of middleware."""

    def __init__(self):
        self._before: List[Callable] = []
        self._after: List[Callable] = []

    def add(
        self,
        middleware: Callable,
        position: MiddlewarePosition = MiddlewarePosition.BEFORE
    ) -> None:
        """Add middleware."""
        if position == MiddlewarePosition.BEFORE:
            self._before.append(middleware)
        else:
            self._after.append(middleware)

    async def run_before(
        self,
        request: Request
    ) -> Tuple[Request, Optional[Response]]:
        """Run before middleware."""
        for mw in self._before:
            try:
                if asyncio.iscoroutinefunction(mw):
                    result = await mw(request)
                else:
                    result = mw(request)

                if isinstance(result, Response):
                    return request, result
                elif isinstance(result, Request):
                    request = result
            except Exception as e:
                return request, Response(status=500, error=str(e))

        return request, None

    async def run_after(
        self,
        request: Request,
        response: Response
    ) -> Response:
        """Run after middleware."""
        for mw in self._after:
            try:
                if asyncio.iscoroutinefunction(mw):
                    result = await mw(request, response)
                else:
                    result = mw(request, response)

                if isinstance(result, Response):
                    response = result
            except Exception:
                pass

        return response

    def clear(self) -> None:
        """Clear all middleware."""
        self._before.clear()
        self._after.clear()


# =============================================================================
# ROUTER
# =============================================================================

class Router:
    """Route matching and dispatch."""

    def __init__(self):
        self._registry = RouteRegistry()
        self._matcher = PatternMatcher()
        self._middleware = MiddlewareChain()
        self._groups: Dict[str, RouteGroup] = {}

    def add_route(
        self,
        path: str,
        handler: Callable,
        methods: Optional[List[RouteMethod]] = None,
        match_type: MatchType = MatchType.EXACT,
        priority: int = 0,
        name: str = ""
    ) -> Route:
        """Add a route."""
        route = Route(
            path=path,
            handler=handler,
            methods=methods or [RouteMethod.ANY],
            match_type=match_type,
            priority=priority,
            name=name
        )

        return self._registry.add(route)

    def get(
        self,
        path: str,
        handler: Callable,
        **kwargs
    ) -> Route:
        """Add GET route."""
        return self.add_route(path, handler, [RouteMethod.GET], **kwargs)

    def post(
        self,
        path: str,
        handler: Callable,
        **kwargs
    ) -> Route:
        """Add POST route."""
        return self.add_route(path, handler, [RouteMethod.POST], **kwargs)

    def put(
        self,
        path: str,
        handler: Callable,
        **kwargs
    ) -> Route:
        """Add PUT route."""
        return self.add_route(path, handler, [RouteMethod.PUT], **kwargs)

    def delete(
        self,
        path: str,
        handler: Callable,
        **kwargs
    ) -> Route:
        """Add DELETE route."""
        return self.add_route(path, handler, [RouteMethod.DELETE], **kwargs)

    def match(
        self,
        path: str,
        method: RouteMethod = RouteMethod.GET
    ) -> RouteMatch:
        """Find matching route."""
        best_match = RouteMatch(matched=False)

        for route in self._registry.active():
            if RouteMethod.ANY not in route.methods and method not in route.methods:
                continue

            match = self._matcher.match(path, route.path, route.match_type)

            if match.matched:
                adjusted_score = match.score + (route.priority * 0.01)

                if adjusted_score > best_match.score:
                    best_match = RouteMatch(
                        matched=True,
                        route=route,
                        params=match.params,
                        score=adjusted_score
                    )

        return best_match

    async def dispatch(self, request: Request) -> Tuple[DispatchResult, Response]:
        """Dispatch request to handler."""
        request, early_response = await self._middleware.run_before(request)

        if early_response:
            return DispatchResult.SUCCESS, early_response

        match = self.match(request.path, request.method)

        if not match.matched:
            for route in self._registry.active():
                if self._matcher.match(request.path, route.path, route.match_type).matched:
                    return DispatchResult.METHOD_NOT_ALLOWED, Response(
                        status=405,
                        error="Method not allowed"
                    )

            return DispatchResult.NOT_FOUND, Response(
                status=404,
                error="Not found"
            )

        request.params.update(match.params)

        try:
            handler = match.route.handler

            if asyncio.iscoroutinefunction(handler):
                result = await handler(request)
            else:
                result = handler(request)

            if isinstance(result, Response):
                response = result
            else:
                response = Response(data=result)

            response = await self._middleware.run_after(request, response)

            return DispatchResult.SUCCESS, response

        except Exception as e:
            return DispatchResult.ERROR, Response(
                status=500,
                error=str(e)
            )

    def create_group(
        self,
        prefix: str,
        name: str = ""
    ) -> RouteGroup:
        """Create a route group."""
        group = RouteGroup(prefix=prefix, name=name)
        self._groups[group.group_id] = group
        return group

    def add_to_group(
        self,
        group_id: str,
        path: str,
        handler: Callable,
        methods: Optional[List[RouteMethod]] = None,
        **kwargs
    ) -> Optional[Route]:
        """Add route to group."""
        group = self._groups.get(group_id)

        if not group:
            return None

        full_path = f"{group.prefix}{path}"

        route = self.add_route(full_path, handler, methods, **kwargs)
        route.middleware.extend(group.middleware)

        group.routes.append(route)

        return route

    def add_middleware(
        self,
        middleware: Callable,
        position: MiddlewarePosition = MiddlewarePosition.BEFORE
    ) -> None:
        """Add global middleware."""
        self._middleware.add(middleware, position)

    def remove_route(self, route_id: str) -> bool:
        """Remove a route."""
        return self._registry.remove(route_id)

    def get_route(self, name: str) -> Optional[Route]:
        """Get route by name."""
        return self._registry.get_by_name(name)

    def url_for(self, name: str, **params) -> Optional[str]:
        """Generate URL for named route."""
        route = self._registry.get_by_name(name)

        if not route:
            return None

        url = route.path

        for key, value in params.items():
            url = url.replace(f'{{{key}}}', str(value))

        return url

    def count(self) -> int:
        """Count routes."""
        return self._registry.count()

    def all_routes(self) -> List[Route]:
        """Get all routes."""
        return self._registry.all()


# =============================================================================
# ROUTING ENGINE
# =============================================================================

class RoutingEngine:
    """
    Routing Engine for BAEL.

    Request routing and dispatch.
    """

    def __init__(self):
        self._router = Router()
        self._stats = {
            "requests": 0,
            "successes": 0,
            "not_found": 0,
            "errors": 0
        }

    # ----- Route Registration -----

    def route(
        self,
        path: str,
        handler: Callable,
        methods: Optional[List[RouteMethod]] = None,
        match_type: MatchType = MatchType.EXACT,
        name: str = ""
    ) -> Route:
        """Register a route."""
        return self._router.add_route(
            path, handler, methods, match_type, name=name
        )

    def get(self, path: str, handler: Callable, **kwargs) -> Route:
        """Register GET route."""
        return self._router.get(path, handler, **kwargs)

    def post(self, path: str, handler: Callable, **kwargs) -> Route:
        """Register POST route."""
        return self._router.post(path, handler, **kwargs)

    def put(self, path: str, handler: Callable, **kwargs) -> Route:
        """Register PUT route."""
        return self._router.put(path, handler, **kwargs)

    def delete(self, path: str, handler: Callable, **kwargs) -> Route:
        """Register DELETE route."""
        return self._router.delete(path, handler, **kwargs)

    def pattern(
        self,
        path: str,
        handler: Callable,
        methods: Optional[List[RouteMethod]] = None,
        **kwargs
    ) -> Route:
        """Register pattern route."""
        return self._router.add_route(
            path, handler, methods, MatchType.PATTERN, **kwargs
        )

    def prefix(
        self,
        path: str,
        handler: Callable,
        methods: Optional[List[RouteMethod]] = None,
        **kwargs
    ) -> Route:
        """Register prefix route."""
        return self._router.add_route(
            path, handler, methods, MatchType.PREFIX, **kwargs
        )

    # ----- Route Groups -----

    def group(self, prefix: str, name: str = "") -> RouteGroup:
        """Create route group."""
        return self._router.create_group(prefix, name)

    def add_to_group(
        self,
        group_id: str,
        path: str,
        handler: Callable,
        methods: Optional[List[RouteMethod]] = None
    ) -> Optional[Route]:
        """Add route to group."""
        return self._router.add_to_group(group_id, path, handler, methods)

    # ----- Middleware -----

    def use(
        self,
        middleware: Callable,
        position: MiddlewarePosition = MiddlewarePosition.BEFORE
    ) -> None:
        """Add middleware."""
        self._router.add_middleware(middleware, position)

    # ----- Dispatch -----

    async def handle(self, request: Request) -> Response:
        """Handle a request."""
        self._stats["requests"] += 1

        result, response = await self._router.dispatch(request)

        if result == DispatchResult.SUCCESS:
            self._stats["successes"] += 1
        elif result == DispatchResult.NOT_FOUND:
            self._stats["not_found"] += 1
        elif result == DispatchResult.ERROR:
            self._stats["errors"] += 1

        return response

    async def dispatch(
        self,
        path: str,
        method: RouteMethod = RouteMethod.GET,
        body: Any = None,
        **kwargs
    ) -> Response:
        """Dispatch request by path."""
        request = Request(
            path=path,
            method=method,
            body=body,
            **kwargs
        )

        return await self.handle(request)

    # ----- URL Generation -----

    def url_for(self, name: str, **params) -> Optional[str]:
        """Generate URL for named route."""
        return self._router.url_for(name, **params)

    # ----- Route Management -----

    def remove(self, route_id: str) -> bool:
        """Remove a route."""
        return self._router.remove_route(route_id)

    def get_route(self, name: str) -> Optional[Route]:
        """Get route by name."""
        return self._router.get_route(name)

    def list_routes(self) -> List[Dict[str, Any]]:
        """List all routes."""
        return [
            {
                "id": r.route_id,
                "path": r.path,
                "methods": [m.value for m in r.methods],
                "status": r.status.value,
                "name": r.name
            }
            for r in self._router.all_routes()
        ]

    # ----- Stats -----

    def get_stats(self) -> Dict[str, Any]:
        """Get routing stats."""
        return dict(self._stats)

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "routes": self._router.count(),
            "requests": self._stats["requests"],
            "success_rate": (
                self._stats["successes"] / self._stats["requests"]
                if self._stats["requests"] > 0 else 0
            )
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Routing Engine."""
    print("=" * 70)
    print("BAEL - ROUTING ENGINE DEMO")
    print("Request Routing and Dispatch")
    print("=" * 70)
    print()

    engine = RoutingEngine()

    # 1. Basic Routes
    print("1. BASIC ROUTES:")
    print("-" * 40)

    def home_handler(req):
        return {"message": "Welcome home!"}

    def about_handler(req):
        return {"message": "About us"}

    engine.get("/", home_handler, name="home")
    engine.get("/about", about_handler, name="about")

    print("   Registered: GET /")
    print("   Registered: GET /about")
    print()

    # 2. Route Methods
    print("2. ROUTE METHODS:")
    print("-" * 40)

    def users_get(req):
        return {"users": ["Alice", "Bob"]}

    def users_post(req):
        return {"created": True}

    def users_delete(req):
        return {"deleted": True}

    engine.get("/users", users_get)
    engine.post("/users", users_post)
    engine.delete("/users", users_delete)

    print("   GET /users -> list users")
    print("   POST /users -> create user")
    print("   DELETE /users -> delete user")
    print()

    # 3. Dispatch Requests
    print("3. DISPATCH REQUESTS:")
    print("-" * 40)

    response = await engine.dispatch("/", RouteMethod.GET)
    print(f"   GET /: {response.data}")

    response = await engine.dispatch("/users", RouteMethod.GET)
    print(f"   GET /users: {response.data}")

    response = await engine.dispatch("/users", RouteMethod.POST)
    print(f"   POST /users: {response.data}")
    print()

    # 4. Pattern Routes
    print("4. PATTERN ROUTES:")
    print("-" * 40)

    def user_detail(req):
        return {"user_id": req.params.get("id")}

    def post_detail(req):
        return {
            "user_id": req.params.get("user_id"),
            "post_id": req.params.get("post_id")
        }

    engine.pattern("/users/{id}", user_detail, name="user_detail")
    engine.pattern("/users/{user_id}/posts/{post_id}", post_detail)

    response = await engine.dispatch("/users/123", RouteMethod.GET)
    print(f"   GET /users/123: {response.data}")

    response = await engine.dispatch("/users/456/posts/789", RouteMethod.GET)
    print(f"   GET /users/456/posts/789: {response.data}")
    print()

    # 5. Prefix Routes
    print("5. PREFIX ROUTES:")
    print("-" * 40)

    def api_handler(req):
        return {"path": req.path, "prefix_matched": True}

    engine.prefix("/api/", api_handler)

    response = await engine.dispatch("/api/anything", RouteMethod.GET)
    print(f"   GET /api/anything: {response.data}")

    response = await engine.dispatch("/api/v1/users", RouteMethod.GET)
    print(f"   GET /api/v1/users: {response.data}")
    print()

    # 6. Route Groups
    print("6. ROUTE GROUPS:")
    print("-" * 40)

    api_group = engine.group("/api/v2", "api_v2")

    def v2_users(req):
        return {"version": "v2", "endpoint": "users"}

    def v2_items(req):
        return {"version": "v2", "endpoint": "items"}

    engine.add_to_group(api_group.group_id, "/users", v2_users)
    engine.add_to_group(api_group.group_id, "/items", v2_items)

    response = await engine.dispatch("/api/v2/users", RouteMethod.GET)
    print(f"   GET /api/v2/users: {response.data}")

    response = await engine.dispatch("/api/v2/items", RouteMethod.GET)
    print(f"   GET /api/v2/items: {response.data}")
    print()

    # 7. Middleware
    print("7. MIDDLEWARE:")
    print("-" * 40)

    request_count = [0]

    def logging_middleware(req):
        request_count[0] += 1
        print(f"   [MW] Request #{request_count[0]}: {req.method.value} {req.path}")
        return req

    engine.use(logging_middleware, MiddlewarePosition.BEFORE)

    await engine.dispatch("/", RouteMethod.GET)
    await engine.dispatch("/about", RouteMethod.GET)
    print()

    # 8. Not Found
    print("8. NOT FOUND:")
    print("-" * 40)

    response = await engine.dispatch("/nonexistent", RouteMethod.GET)
    print(f"   GET /nonexistent: status={response.status}, error={response.error}")
    print()

    # 9. Method Not Allowed
    print("9. METHOD NOT ALLOWED:")
    print("-" * 40)

    response = await engine.dispatch("/about", RouteMethod.DELETE)
    print(f"   DELETE /about: status={response.status}, error={response.error}")
    print()

    # 10. Named Routes and URL Generation
    print("10. URL GENERATION:")
    print("-" * 40)

    url = engine.url_for("home")
    print(f"   URL for 'home': {url}")

    url = engine.url_for("user_detail", id="999")
    print(f"   URL for 'user_detail' with id=999: {url}")
    print()

    # 11. Async Handler
    print("11. ASYNC HANDLER:")
    print("-" * 40)

    async def async_handler(req):
        await asyncio.sleep(0.01)
        return {"async": True, "processed": req.path}

    engine.get("/async", async_handler)

    response = await engine.dispatch("/async", RouteMethod.GET)
    print(f"   GET /async: {response.data}")
    print()

    # 12. Request with Body
    print("12. REQUEST WITH BODY:")
    print("-" * 40)

    def create_item(req):
        return {"created": req.body}

    engine.post("/items", create_item)

    response = await engine.dispatch(
        "/items",
        RouteMethod.POST,
        body={"name": "Test Item", "price": 99}
    )
    print(f"   POST /items: {response.data}")
    print()

    # 13. List Routes
    print("13. LIST ROUTES:")
    print("-" * 40)

    routes = engine.list_routes()

    for route in routes[:5]:
        print(f"   {route['methods']} {route['path']}")
    print(f"   ... and {len(routes) - 5} more")
    print()

    # 14. Stats
    print("14. ROUTING STATS:")
    print("-" * 40)

    stats = engine.get_stats()

    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Routing Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
