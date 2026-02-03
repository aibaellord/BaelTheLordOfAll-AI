"""
BAEL API Tools - REST, GraphQL, and Webhook Utilities
Provides comprehensive API interaction capabilities.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode, urljoin

logger = logging.getLogger("BAEL.Tools.API")


# =============================================================================
# DATA CLASSES & ENUMS
# =============================================================================

class HTTPMethod(Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class AuthType(Enum):
    """Authentication types."""
    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    CUSTOM = "custom"


@dataclass
class APIResponse:
    """API response wrapper."""
    status_code: int
    headers: Dict[str, str]
    body: Any
    elapsed_ms: float
    url: str
    method: str
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def json(self) -> Optional[Dict]:
        if isinstance(self.body, dict):
            return self.body
        if isinstance(self.body, str):
            try:
                return json.loads(self.body)
            except:
                return None
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status_code": self.status_code,
            "success": self.success,
            "elapsed_ms": self.elapsed_ms,
            "url": self.url,
            "method": self.method,
            "body": self.body if isinstance(self.body, (dict, list, str, int, float, bool, type(None))) else str(self.body),
            "error": self.error
        }


@dataclass
class GraphQLResponse:
    """GraphQL response wrapper."""
    data: Optional[Dict[str, Any]]
    errors: Optional[List[Dict[str, Any]]]
    extensions: Optional[Dict[str, Any]]
    elapsed_ms: float

    @property
    def success(self) -> bool:
        return self.errors is None or len(self.errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data": self.data,
            "errors": self.errors,
            "elapsed_ms": self.elapsed_ms,
            "success": self.success
        }


@dataclass
class WebhookEvent:
    """Webhook event."""
    id: str
    event_type: str
    payload: Dict[str, Any]
    headers: Dict[str, str]
    received_at: datetime
    signature: Optional[str] = None
    verified: bool = False


# =============================================================================
# RATE LIMITER
# =============================================================================

class RateLimiter:
    """Rate limiter with token bucket algorithm."""

    def __init__(
        self,
        requests_per_second: float = 10.0,
        burst_size: int = 20
    ):
        self.rate = requests_per_second
        self.burst_size = burst_size
        self.tokens = burst_size
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self) -> float:
        """Acquire a token, waiting if necessary."""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update

            # Add tokens based on elapsed time
            self.tokens = min(
                self.burst_size,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now

            if self.tokens >= 1:
                self.tokens -= 1
                return 0.0

            # Calculate wait time
            wait_time = (1 - self.tokens) / self.rate
            await asyncio.sleep(wait_time)
            self.tokens = 0
            self.last_update = time.time()
            return wait_time

    @property
    def available_tokens(self) -> float:
        """Get current available tokens."""
        now = time.time()
        elapsed = now - self.last_update
        return min(self.burst_size, self.tokens + elapsed * self.rate)


# =============================================================================
# REST CLIENT
# =============================================================================

class RESTClient:
    """Comprehensive REST API client."""

    def __init__(
        self,
        base_url: str = "",
        auth_type: AuthType = AuthType.NONE,
        auth_credentials: Optional[Dict[str, str]] = None,
        default_headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
        rate_limit: Optional[RateLimiter] = None,
        retry_count: int = 3,
        retry_delay: float = 1.0
    ):
        self.base_url = base_url.rstrip("/")
        self.auth_type = auth_type
        self.auth_credentials = auth_credentials or {}
        self.default_headers = default_headers or {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "BAEL-Agent/1.0"
        }
        self.timeout = timeout
        self.rate_limit = rate_limit
        self.retry_count = retry_count
        self.retry_delay = retry_delay

    def _build_auth_headers(self) -> Dict[str, str]:
        """Build authentication headers."""
        headers = {}

        if self.auth_type == AuthType.BEARER:
            token = self.auth_credentials.get("token", "")
            headers["Authorization"] = f"Bearer {token}"

        elif self.auth_type == AuthType.BASIC:
            import base64
            username = self.auth_credentials.get("username", "")
            password = self.auth_credentials.get("password", "")
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"

        elif self.auth_type == AuthType.API_KEY:
            key_name = self.auth_credentials.get("key_name", "X-API-Key")
            key_value = self.auth_credentials.get("key_value", "")
            headers[key_name] = key_value

        return headers

    async def request(
        self,
        method: HTTPMethod,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> APIResponse:
        """Make an HTTP request."""
        # Build URL
        if self.base_url:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
        else:
            url = endpoint

        if params:
            url = f"{url}?{urlencode(params)}"

        # Build headers
        request_headers = {**self.default_headers}
        request_headers.update(self._build_auth_headers())
        if headers:
            request_headers.update(headers)

        # Rate limiting
        if self.rate_limit:
            await self.rate_limit.acquire()

        # Execute with retries
        last_error = None
        for attempt in range(self.retry_count):
            try:
                return await self._execute_request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    data=data,
                    json_body=json_body,
                    timeout=timeout or self.timeout
                )
            except Exception as e:
                last_error = e
                if attempt < self.retry_count - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))

        return APIResponse(
            status_code=500,
            headers={},
            body=None,
            elapsed_ms=0,
            url=url,
            method=method.value,
            error=str(last_error)
        )

    async def _execute_request(
        self,
        method: HTTPMethod,
        url: str,
        headers: Dict[str, str],
        data: Optional[Dict[str, Any]],
        json_body: Optional[Dict[str, Any]],
        timeout: float
    ) -> APIResponse:
        """Execute HTTP request (simulated - extend with aiohttp)."""
        start_time = time.time()

        # This is a simulation - in real implementation, use aiohttp
        logger.info(f"API {method.value} {url}")
        await asyncio.sleep(0.1)  # Simulate network latency

        # Simulated response
        elapsed = (time.time() - start_time) * 1000

        return APIResponse(
            status_code=200,
            headers={"content-type": "application/json"},
            body={
                "message": "Simulated response",
                "method": method.value,
                "url": url,
                "data": data or json_body,
                "timestamp": datetime.now().isoformat()
            },
            elapsed_ms=elapsed,
            url=url,
            method=method.value
        )

    # Convenience methods
    async def get(self, endpoint: str, params: Dict = None, **kwargs) -> APIResponse:
        return await self.request(HTTPMethod.GET, endpoint, params=params, **kwargs)

    async def post(self, endpoint: str, json_body: Dict = None, **kwargs) -> APIResponse:
        return await self.request(HTTPMethod.POST, endpoint, json_body=json_body, **kwargs)

    async def put(self, endpoint: str, json_body: Dict = None, **kwargs) -> APIResponse:
        return await self.request(HTTPMethod.PUT, endpoint, json_body=json_body, **kwargs)

    async def patch(self, endpoint: str, json_body: Dict = None, **kwargs) -> APIResponse:
        return await self.request(HTTPMethod.PATCH, endpoint, json_body=json_body, **kwargs)

    async def delete(self, endpoint: str, **kwargs) -> APIResponse:
        return await self.request(HTTPMethod.DELETE, endpoint, **kwargs)


# =============================================================================
# GRAPHQL CLIENT
# =============================================================================

class GraphQLClient:
    """GraphQL API client."""

    def __init__(
        self,
        endpoint: str,
        auth_headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ):
        self.endpoint = endpoint
        self.auth_headers = auth_headers or {}
        self.timeout = timeout
        self._rest = RESTClient()

    async def query(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None
    ) -> GraphQLResponse:
        """Execute a GraphQL query."""
        start_time = time.time()

        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        if operation_name:
            payload["operationName"] = operation_name

        headers = {
            "Content-Type": "application/json",
            **self.auth_headers
        }

        response = await self._rest.request(
            method=HTTPMethod.POST,
            endpoint=self.endpoint,
            json_body=payload,
            headers=headers
        )

        elapsed = (time.time() - start_time) * 1000

        if response.json:
            return GraphQLResponse(
                data=response.json.get("data"),
                errors=response.json.get("errors"),
                extensions=response.json.get("extensions"),
                elapsed_ms=elapsed
            )

        return GraphQLResponse(
            data=None,
            errors=[{"message": response.error or "Unknown error"}],
            extensions=None,
            elapsed_ms=elapsed
        )

    async def mutation(
        self,
        mutation: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> GraphQLResponse:
        """Execute a GraphQL mutation."""
        return await self.query(mutation, variables)

    def build_query(
        self,
        operation_type: str,
        name: str,
        fields: List[str],
        arguments: Optional[Dict[str, Any]] = None,
        fragments: Optional[List[str]] = None
    ) -> str:
        """Build a GraphQL query string."""
        # Format arguments
        args_str = ""
        if arguments:
            args = []
            for key, value in arguments.items():
                if isinstance(value, str):
                    args.append(f'{key}: "{value}"')
                elif isinstance(value, bool):
                    args.append(f'{key}: {str(value).lower()}')
                else:
                    args.append(f'{key}: {json.dumps(value)}')
            args_str = f"({', '.join(args)})"

        # Format fields
        fields_str = "\n    ".join(fields)

        # Build query
        query = f"""{operation_type} {{
  {name}{args_str} {{
    {fields_str}
  }}
}}"""

        if fragments:
            query += "\n" + "\n".join(fragments)

        return query


# =============================================================================
# WEBHOOK MANAGER
# =============================================================================

class WebhookManager:
    """Manage webhook endpoints and event handling."""

    def __init__(self, secret: Optional[str] = None):
        self.secret = secret
        self._handlers: Dict[str, List[Callable]] = {}
        self._events: List[WebhookEvent] = []
        self._max_events = 1000

    def register_handler(
        self,
        event_type: str,
        handler: Callable[[WebhookEvent], Any]
    ) -> None:
        """Register a handler for an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unregister_handler(
        self,
        event_type: str,
        handler: Callable
    ) -> bool:
        """Unregister a handler."""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                return True
            except ValueError:
                pass
        return False

    def verify_signature(
        self,
        payload: bytes,
        signature: str,
        algorithm: str = "sha256"
    ) -> bool:
        """Verify webhook signature."""
        if not self.secret:
            return False

        # Parse signature format (e.g., "sha256=...")
        if "=" in signature:
            algo, sig = signature.split("=", 1)
        else:
            algo = algorithm
            sig = signature

        # Compute expected signature
        if algo == "sha256":
            expected = hmac.new(
                self.secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
        elif algo == "sha1":
            expected = hmac.new(
                self.secret.encode(),
                payload,
                hashlib.sha1
            ).hexdigest()
        else:
            return False

        return hmac.compare_digest(expected, sig)

    async def process_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        signature: Optional[str] = None,
        raw_payload: Optional[bytes] = None
    ) -> WebhookEvent:
        """Process an incoming webhook event."""
        # Create event
        event = WebhookEvent(
            id=hashlib.sha256(
                f"{event_type}:{time.time()}:{json.dumps(payload)}".encode()
            ).hexdigest()[:16],
            event_type=event_type,
            payload=payload,
            headers=headers or {},
            received_at=datetime.now(),
            signature=signature
        )

        # Verify signature if provided
        if signature and raw_payload and self.secret:
            event.verified = self.verify_signature(raw_payload, signature)

        # Store event
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]

        # Dispatch to handlers
        handlers = self._handlers.get(event_type, [])
        handlers.extend(self._handlers.get("*", []))  # Wildcard handlers

        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Webhook handler error: {e}")

        return event

    def get_events(
        self,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[WebhookEvent]:
        """Get stored events."""
        events = self._events

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return events[-limit:]

    def generate_signature(
        self,
        payload: bytes,
        algorithm: str = "sha256"
    ) -> str:
        """Generate a signature for outgoing webhooks."""
        if not self.secret:
            return ""

        if algorithm == "sha256":
            sig = hmac.new(
                self.secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
        elif algorithm == "sha1":
            sig = hmac.new(
                self.secret.encode(),
                payload,
                hashlib.sha1
            ).hexdigest()
        else:
            return ""

        return f"{algorithm}={sig}"


# =============================================================================
# API TOOLKIT - UNIFIED INTERFACE
# =============================================================================

class APIToolkit:
    """
    Unified API toolkit providing REST, GraphQL, and webhook capabilities.

    Main entry point for API operations in BAEL.
    """

    def __init__(
        self,
        default_timeout: float = 30.0,
        rate_limit_rps: float = 10.0,
        webhook_secret: Optional[str] = None
    ):
        self.rate_limiter = RateLimiter(rate_limit_rps)
        self.rest = RESTClient(timeout=default_timeout, rate_limit=self.rate_limiter)
        self.webhooks = WebhookManager(webhook_secret)
        self._graphql_clients: Dict[str, GraphQLClient] = {}

    def get_graphql_client(
        self,
        endpoint: str,
        auth_headers: Optional[Dict[str, str]] = None
    ) -> GraphQLClient:
        """Get or create a GraphQL client."""
        if endpoint not in self._graphql_clients:
            self._graphql_clients[endpoint] = GraphQLClient(endpoint, auth_headers)
        return self._graphql_clients[endpoint]

    async def http_get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> APIResponse:
        """Make HTTP GET request."""
        return await self.rest.get(url, params=params, headers=headers)

    async def http_post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> APIResponse:
        """Make HTTP POST request."""
        return await self.rest.post(url, json_body=data, headers=headers)

    async def graphql_query(
        self,
        endpoint: str,
        query: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> GraphQLResponse:
        """Execute GraphQL query."""
        client = self.get_graphql_client(endpoint)
        return await client.query(query, variables)

    def register_webhook_handler(
        self,
        event_type: str,
        handler: Callable[[WebhookEvent], Any]
    ) -> None:
        """Register webhook handler."""
        self.webhooks.register_handler(event_type, handler)

    async def process_webhook(
        self,
        event_type: str,
        payload: Dict[str, Any],
        headers: Dict[str, str] = None,
        signature: str = None
    ) -> WebhookEvent:
        """Process incoming webhook."""
        return await self.webhooks.process_event(
            event_type=event_type,
            payload=payload,
            headers=headers,
            signature=signature
        )

    def create_rest_client(
        self,
        base_url: str,
        auth_type: AuthType = AuthType.NONE,
        auth_credentials: Dict[str, str] = None
    ) -> RESTClient:
        """Create a configured REST client."""
        return RESTClient(
            base_url=base_url,
            auth_type=auth_type,
            auth_credentials=auth_credentials,
            rate_limit=self.rate_limiter
        )

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for BAEL integration."""
        return [
            {
                "name": "api_get",
                "description": "Make HTTP GET request",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "params": {"type": "object"},
                        "headers": {"type": "object"}
                    },
                    "required": ["url"]
                },
                "handler": self.http_get
            },
            {
                "name": "api_post",
                "description": "Make HTTP POST request",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "data": {"type": "object"},
                        "headers": {"type": "object"}
                    },
                    "required": ["url"]
                },
                "handler": self.http_post
            },
            {
                "name": "graphql_query",
                "description": "Execute GraphQL query",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string"},
                        "query": {"type": "string"},
                        "variables": {"type": "object"}
                    },
                    "required": ["endpoint", "query"]
                },
                "handler": self.graphql_query
            }
        ]


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "APIToolkit",
    "RESTClient",
    "GraphQLClient",
    "WebhookManager",
    "RateLimiter",
    "APIResponse",
    "WebhookEvent",
    "GraphQLResponse",
    "HTTPMethod",
    "AuthType"
]
