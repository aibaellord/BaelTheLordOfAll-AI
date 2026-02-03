#!/usr/bin/env python3
"""
BAEL - Integration Engine
System integration and external connectivity for agents.

Features:
- API integration
- Protocol adapters
- Data transformation
- Webhook handling
- Service orchestration
"""

import asyncio
import base64
import hashlib
import hmac
import json
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)
from urllib.parse import urlencode, urlparse

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class IntegrationType(Enum):
    """Integration types."""
    REST = "rest"
    GRAPHQL = "graphql"
    GRPC = "grpc"
    WEBSOCKET = "websocket"
    WEBHOOK = "webhook"
    MESSAGE_QUEUE = "message_queue"


class AuthType(Enum):
    """Authentication types."""
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    BASIC = "basic"
    OAUTH2 = "oauth2"
    HMAC = "hmac"


class HttpMethod(Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class DataFormat(Enum):
    """Data formats."""
    JSON = "json"
    XML = "xml"
    FORM = "form"
    MULTIPART = "multipart"
    RAW = "raw"


class IntegrationState(Enum):
    """Integration states."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


class WebhookEvent(Enum):
    """Webhook event types."""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    CUSTOM = "custom"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class AuthConfig:
    """Authentication configuration."""
    auth_type: AuthType = AuthType.NONE
    api_key: str = ""
    api_key_header: str = "X-API-Key"
    bearer_token: str = ""
    username: str = ""
    password: str = ""
    oauth_token: str = ""
    hmac_secret: str = ""


@dataclass
class Integration:
    """An integration definition."""
    integration_id: str = ""
    name: str = ""
    integration_type: IntegrationType = IntegrationType.REST
    base_url: str = ""
    auth: AuthConfig = field(default_factory=AuthConfig)
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
    state: IntegrationState = IntegrationState.INACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.integration_id:
            self.integration_id = str(uuid.uuid4())[:8]


@dataclass
class Request:
    """An API request."""
    request_id: str = ""
    method: HttpMethod = HttpMethod.GET
    url: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    format: DataFormat = DataFormat.JSON
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.request_id:
            self.request_id = str(uuid.uuid4())[:8]


@dataclass
class Response:
    """An API response."""
    response_id: str = ""
    status_code: int = 0
    headers: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    duration_ms: float = 0.0
    success: bool = False
    error: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.response_id:
            self.response_id = str(uuid.uuid4())[:8]


@dataclass
class Endpoint:
    """An API endpoint."""
    endpoint_id: str = ""
    name: str = ""
    path: str = ""
    method: HttpMethod = HttpMethod.GET
    params: List[str] = field(default_factory=list)
    body_schema: Dict[str, Any] = field(default_factory=dict)
    response_schema: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.endpoint_id:
            self.endpoint_id = str(uuid.uuid4())[:8]


@dataclass
class Webhook:
    """A webhook configuration."""
    webhook_id: str = ""
    name: str = ""
    url: str = ""
    events: List[WebhookEvent] = field(default_factory=list)
    secret: str = ""
    active: bool = True
    last_triggered: Optional[datetime] = None

    def __post_init__(self):
        if not self.webhook_id:
            self.webhook_id = str(uuid.uuid4())[:8]


@dataclass
class TransformRule:
    """Data transformation rule."""
    rule_id: str = ""
    source_path: str = ""
    target_path: str = ""
    transform: Optional[Callable] = None
    default: Any = None

    def __post_init__(self):
        if not self.rule_id:
            self.rule_id = str(uuid.uuid4())[:8]


@dataclass
class IntegrationConfig:
    """Integration engine configuration."""
    default_timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_logging: bool = True


# =============================================================================
# AUTH HANDLER
# =============================================================================

class AuthHandler:
    """Handle authentication for requests."""

    def apply(self, request: Request, auth: AuthConfig) -> Request:
        """Apply authentication to request."""
        if auth.auth_type == AuthType.NONE:
            return request

        elif auth.auth_type == AuthType.API_KEY:
            request.headers[auth.api_key_header] = auth.api_key

        elif auth.auth_type == AuthType.BEARER:
            request.headers["Authorization"] = f"Bearer {auth.bearer_token}"

        elif auth.auth_type == AuthType.BASIC:
            credentials = base64.b64encode(
                f"{auth.username}:{auth.password}".encode()
            ).decode()
            request.headers["Authorization"] = f"Basic {credentials}"

        elif auth.auth_type == AuthType.OAUTH2:
            request.headers["Authorization"] = f"Bearer {auth.oauth_token}"

        elif auth.auth_type == AuthType.HMAC:
            signature = self._generate_hmac(request, auth.hmac_secret)
            request.headers["X-Signature"] = signature

        return request

    def _generate_hmac(self, request: Request, secret: str) -> str:
        """Generate HMAC signature."""
        message = f"{request.method.value}{request.url}"

        if request.body:
            message += json.dumps(request.body)

        signature = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature


# =============================================================================
# DATA TRANSFORMER
# =============================================================================

class DataTransformer:
    """Transform data between formats."""

    def __init__(self):
        self._rules: Dict[str, List[TransformRule]] = defaultdict(list)

    def add_rule(
        self,
        transform_name: str,
        source_path: str,
        target_path: str,
        transform: Optional[Callable] = None,
        default: Any = None
    ) -> TransformRule:
        """Add transformation rule."""
        rule = TransformRule(
            source_path=source_path,
            target_path=target_path,
            transform=transform,
            default=default
        )

        self._rules[transform_name].append(rule)

        return rule

    def transform(self, transform_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply transformation rules."""
        rules = self._rules.get(transform_name, [])

        if not rules:
            return data

        result = {}

        for rule in rules:
            value = self._get_path(data, rule.source_path)

            if value is None:
                value = rule.default

            if value is not None and rule.transform:
                value = rule.transform(value)

            if value is not None:
                self._set_path(result, rule.target_path, value)

        return result

    def _get_path(self, data: Dict[str, Any], path: str) -> Any:
        """Get value at path."""
        parts = path.split(".")
        current = data

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    current = current[idx]
                except (ValueError, IndexError):
                    return None
            else:
                return None

            if current is None:
                return None

        return current

    def _set_path(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """Set value at path."""
        parts = path.split(".")
        current = data

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value


# =============================================================================
# REQUEST BUILDER
# =============================================================================

class RequestBuilder:
    """Build API requests."""

    def __init__(self, integration: Integration):
        self._integration = integration
        self._method = HttpMethod.GET
        self._path = ""
        self._params: Dict[str, str] = {}
        self._body: Any = None
        self._headers: Dict[str, str] = {}
        self._format = DataFormat.JSON

    def get(self, path: str = "") -> "RequestBuilder":
        """Set GET method."""
        self._method = HttpMethod.GET
        self._path = path
        return self

    def post(self, path: str = "") -> "RequestBuilder":
        """Set POST method."""
        self._method = HttpMethod.POST
        self._path = path
        return self

    def put(self, path: str = "") -> "RequestBuilder":
        """Set PUT method."""
        self._method = HttpMethod.PUT
        self._path = path
        return self

    def patch(self, path: str = "") -> "RequestBuilder":
        """Set PATCH method."""
        self._method = HttpMethod.PATCH
        self._path = path
        return self

    def delete(self, path: str = "") -> "RequestBuilder":
        """Set DELETE method."""
        self._method = HttpMethod.DELETE
        self._path = path
        return self

    def params(self, params: Dict[str, str]) -> "RequestBuilder":
        """Set query parameters."""
        self._params.update(params)
        return self

    def body(self, body: Any) -> "RequestBuilder":
        """Set request body."""
        self._body = body
        return self

    def header(self, name: str, value: str) -> "RequestBuilder":
        """Add header."""
        self._headers[name] = value
        return self

    def json(self) -> "RequestBuilder":
        """Set JSON format."""
        self._format = DataFormat.JSON
        return self

    def form(self) -> "RequestBuilder":
        """Set form format."""
        self._format = DataFormat.FORM
        return self

    def build(self) -> Request:
        """Build the request."""
        url = self._integration.base_url.rstrip("/")

        if self._path:
            url = f"{url}/{self._path.lstrip('/')}"

        if self._params:
            url = f"{url}?{urlencode(self._params)}"

        headers = dict(self._integration.headers)
        headers.update(self._headers)

        if self._format == DataFormat.JSON:
            headers["Content-Type"] = "application/json"
        elif self._format == DataFormat.FORM:
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        return Request(
            method=self._method,
            url=url,
            headers=headers,
            params=self._params,
            body=self._body,
            format=self._format
        )


# =============================================================================
# MOCK HTTP CLIENT
# =============================================================================

class MockHttpClient:
    """Mock HTTP client for demo."""

    def __init__(self):
        self._responses: Dict[str, Response] = {}
        self._calls: List[Request] = []

    def mock_response(self, method: HttpMethod, path: str, response: Response) -> None:
        """Set mock response."""
        key = f"{method.value}:{path}"
        self._responses[key] = response

    async def send(self, request: Request) -> Response:
        """Send request (mock)."""
        self._calls.append(request)

        parsed = urlparse(request.url)
        path = parsed.path

        key = f"{request.method.value}:{path}"

        if key in self._responses:
            response = self._responses[key]
            response.response_id = str(uuid.uuid4())[:8]
            return response

        return Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body={"status": "ok", "path": path, "method": request.method.value},
            success=True,
            duration_ms=10.0
        )

    def get_calls(self) -> List[Request]:
        """Get recorded calls."""
        return self._calls


# =============================================================================
# WEBHOOK HANDLER
# =============================================================================

class WebhookHandler:
    """Handle webhook events."""

    def __init__(self):
        self._webhooks: Dict[str, Webhook] = {}
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)

    def register(
        self,
        name: str,
        url: str,
        events: List[WebhookEvent],
        secret: str = ""
    ) -> Webhook:
        """Register a webhook."""
        if not secret:
            secret = str(uuid.uuid4())

        webhook = Webhook(
            name=name,
            url=url,
            events=events,
            secret=secret
        )

        self._webhooks[webhook.webhook_id] = webhook

        return webhook

    def add_handler(self, event: WebhookEvent, handler: Callable) -> None:
        """Add event handler."""
        self._handlers[event.value].append(handler)

    async def trigger(
        self,
        webhook_id: str,
        event: WebhookEvent,
        data: Dict[str, Any]
    ) -> bool:
        """Trigger webhook event."""
        webhook = self._webhooks.get(webhook_id)

        if not webhook or not webhook.active:
            return False

        if event not in webhook.events:
            return False

        webhook.last_triggered = datetime.now()

        handlers = self._handlers.get(event.value, [])

        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler(webhook, event, data)
            else:
                handler(webhook, event, data)

        return True

    def verify_signature(self, webhook_id: str, payload: str, signature: str) -> bool:
        """Verify webhook signature."""
        webhook = self._webhooks.get(webhook_id)

        if not webhook:
            return False

        expected = hmac.new(
            webhook.secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def get(self, webhook_id: str) -> Optional[Webhook]:
        """Get webhook."""
        return self._webhooks.get(webhook_id)

    def list(self) -> List[Webhook]:
        """List all webhooks."""
        return list(self._webhooks.values())


# =============================================================================
# RETRY HANDLER
# =============================================================================

class RetryHandler:
    """Handle request retries."""

    def __init__(self, max_retries: int = 3, delay: float = 1.0):
        self._max_retries = max_retries
        self._delay = delay

    async def execute(
        self,
        operation: Callable,
        should_retry: Optional[Callable[[Response], bool]] = None
    ) -> Response:
        """Execute with retries."""
        if should_retry is None:
            should_retry = lambda r: r.status_code >= 500

        last_response = None

        for attempt in range(self._max_retries + 1):
            response = await operation()

            if response.success or not should_retry(response):
                return response

            last_response = response

            if attempt < self._max_retries:
                delay = self._delay * (2 ** attempt)
                await asyncio.sleep(delay)

        return last_response or Response(
            status_code=0,
            success=False,
            error="Max retries exceeded"
        )


# =============================================================================
# INTEGRATION ENGINE
# =============================================================================

class IntegrationEngine:
    """
    Integration Engine for BAEL.

    System integration and external connectivity.
    """

    def __init__(self, config: Optional[IntegrationConfig] = None):
        self._config = config or IntegrationConfig()

        self._integrations: Dict[str, Integration] = {}
        self._auth_handler = AuthHandler()
        self._transformer = DataTransformer()
        self._webhook_handler = WebhookHandler()
        self._retry_handler = RetryHandler(
            self._config.max_retries,
            self._config.retry_delay
        )

        self._http_client = MockHttpClient()
        self._call_history: List[Tuple[Request, Response]] = []

    # ----- Integration Management -----

    def create_integration(
        self,
        name: str,
        base_url: str,
        integration_type: IntegrationType = IntegrationType.REST,
        auth: Optional[AuthConfig] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Integration:
        """Create a new integration."""
        integration = Integration(
            name=name,
            base_url=base_url,
            integration_type=integration_type,
            auth=auth or AuthConfig(),
            headers=headers or {},
            timeout=self._config.default_timeout
        )

        self._integrations[integration.integration_id] = integration

        return integration

    def get_integration(self, integration_id: str) -> Optional[Integration]:
        """Get integration by ID."""
        return self._integrations.get(integration_id)

    def get_by_name(self, name: str) -> Optional[Integration]:
        """Get integration by name."""
        for integration in self._integrations.values():
            if integration.name == name:
                return integration
        return None

    def activate(self, integration_id: str) -> bool:
        """Activate an integration."""
        integration = self._integrations.get(integration_id)
        if integration:
            integration.state = IntegrationState.ACTIVE
            return True
        return False

    def deactivate(self, integration_id: str) -> bool:
        """Deactivate an integration."""
        integration = self._integrations.get(integration_id)
        if integration:
            integration.state = IntegrationState.INACTIVE
            return True
        return False

    def remove(self, integration_id: str) -> bool:
        """Remove an integration."""
        if integration_id in self._integrations:
            del self._integrations[integration_id]
            return True
        return False

    # ----- Request Building -----

    def request(self, integration_id: str) -> Optional[RequestBuilder]:
        """Create request builder for integration."""
        integration = self._integrations.get(integration_id)

        if not integration:
            return None

        return RequestBuilder(integration)

    # ----- Request Execution -----

    async def execute(
        self,
        integration_id: str,
        request: Request,
        with_retry: bool = False
    ) -> Response:
        """Execute a request."""
        integration = self._integrations.get(integration_id)

        if not integration:
            return Response(
                status_code=0,
                success=False,
                error="Integration not found"
            )

        authed_request = self._auth_handler.apply(request, integration.auth)

        if with_retry:
            response = await self._retry_handler.execute(
                lambda: self._http_client.send(authed_request)
            )
        else:
            response = await self._http_client.send(authed_request)

        self._call_history.append((request, response))

        return response

    async def get(
        self,
        integration_id: str,
        path: str,
        params: Optional[Dict[str, str]] = None
    ) -> Response:
        """Execute GET request."""
        builder = self.request(integration_id)

        if not builder:
            return Response(status_code=0, success=False, error="Integration not found")

        request = builder.get(path)

        if params:
            request = request.params(params)

        return await self.execute(integration_id, request.build())

    async def post(
        self,
        integration_id: str,
        path: str,
        body: Any = None
    ) -> Response:
        """Execute POST request."""
        builder = self.request(integration_id)

        if not builder:
            return Response(status_code=0, success=False, error="Integration not found")

        request = builder.post(path)

        if body:
            request = request.body(body)

        return await self.execute(integration_id, request.build())

    async def put(
        self,
        integration_id: str,
        path: str,
        body: Any = None
    ) -> Response:
        """Execute PUT request."""
        builder = self.request(integration_id)

        if not builder:
            return Response(status_code=0, success=False, error="Integration not found")

        request = builder.put(path)

        if body:
            request = request.body(body)

        return await self.execute(integration_id, request.build())

    async def delete(
        self,
        integration_id: str,
        path: str
    ) -> Response:
        """Execute DELETE request."""
        builder = self.request(integration_id)

        if not builder:
            return Response(status_code=0, success=False, error="Integration not found")

        return await self.execute(integration_id, builder.delete(path).build())

    # ----- Data Transformation -----

    def add_transform(
        self,
        name: str,
        source_path: str,
        target_path: str,
        transform: Optional[Callable] = None
    ) -> TransformRule:
        """Add transformation rule."""
        return self._transformer.add_rule(name, source_path, target_path, transform)

    def transform(self, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply transformation."""
        return self._transformer.transform(name, data)

    # ----- Webhooks -----

    def register_webhook(
        self,
        name: str,
        url: str,
        events: List[WebhookEvent],
        secret: str = ""
    ) -> Webhook:
        """Register a webhook."""
        return self._webhook_handler.register(name, url, events, secret)

    def on_webhook(self, event: WebhookEvent, handler: Callable) -> None:
        """Add webhook event handler."""
        self._webhook_handler.add_handler(event, handler)

    async def trigger_webhook(
        self,
        webhook_id: str,
        event: WebhookEvent,
        data: Dict[str, Any]
    ) -> bool:
        """Trigger webhook event."""
        return await self._webhook_handler.trigger(webhook_id, event, data)

    def verify_webhook(self, webhook_id: str, payload: str, signature: str) -> bool:
        """Verify webhook signature."""
        return self._webhook_handler.verify_signature(webhook_id, payload, signature)

    def list_webhooks(self) -> List[Webhook]:
        """List all webhooks."""
        return self._webhook_handler.list()

    # ----- History -----

    def get_history(self, limit: int = 100) -> List[Tuple[Request, Response]]:
        """Get call history."""
        return self._call_history[-limit:]

    def clear_history(self) -> int:
        """Clear call history."""
        count = len(self._call_history)
        self._call_history.clear()
        return count

    # ----- Mock Responses -----

    def mock(self, method: HttpMethod, path: str, response: Response) -> None:
        """Set mock response."""
        self._http_client.mock_response(method, path, response)

    # ----- Summary -----

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        by_type = defaultdict(int)
        by_state = defaultdict(int)

        for integration in self._integrations.values():
            by_type[integration.integration_type.value] += 1
            by_state[integration.state.value] += 1

        return {
            "integrations": len(self._integrations),
            "by_type": dict(by_type),
            "by_state": dict(by_state),
            "webhooks": len(self._webhook_handler.list()),
            "call_history": len(self._call_history)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Integration Engine."""
    print("=" * 70)
    print("BAEL - INTEGRATION ENGINE DEMO")
    print("System Integration and External Connectivity")
    print("=" * 70)
    print()

    engine = IntegrationEngine()

    # 1. Create Integration
    print("1. CREATE INTEGRATION:")
    print("-" * 40)

    api = engine.create_integration(
        "github_api",
        "https://api.github.com",
        auth=AuthConfig(
            auth_type=AuthType.BEARER,
            bearer_token="ghp_test_token_12345"
        ),
        headers={"Accept": "application/vnd.github.v3+json"}
    )

    print(f"   Created: {api.name}")
    print(f"   ID: {api.integration_id}")
    print(f"   Base URL: {api.base_url}")
    print(f"   Auth: {api.auth.auth_type.value}")
    print()

    # 2. Activate Integration
    print("2. ACTIVATE INTEGRATION:")
    print("-" * 40)

    print(f"   State before: {api.state.value}")
    engine.activate(api.integration_id)
    print(f"   State after: {api.state.value}")
    print()

    # 3. Build Request
    print("3. BUILD REQUEST:")
    print("-" * 40)

    builder = engine.request(api.integration_id)
    request = (builder
        .get("/repos/owner/repo")
        .params({"page": "1", "per_page": "10"})
        .header("X-Custom", "value")
        .build())

    print(f"   Method: {request.method.value}")
    print(f"   URL: {request.url}")
    print(f"   Headers: {len(request.headers)}")
    print()

    # 4. Execute Request
    print("4. EXECUTE REQUEST:")
    print("-" * 40)

    response = await engine.execute(api.integration_id, request)

    print(f"   Status: {response.status_code}")
    print(f"   Success: {response.success}")
    print(f"   Duration: {response.duration_ms}ms")
    print(f"   Body: {response.body}")
    print()

    # 5. Convenience Methods
    print("5. CONVENIENCE METHODS:")
    print("-" * 40)

    get_resp = await engine.get(api.integration_id, "/users/test")
    print(f"   GET /users/test: {get_resp.status_code}")

    post_resp = await engine.post(api.integration_id, "/repos", {"name": "test-repo"})
    print(f"   POST /repos: {post_resp.status_code}")

    put_resp = await engine.put(api.integration_id, "/repos/test", {"description": "Updated"})
    print(f"   PUT /repos/test: {put_resp.status_code}")

    del_resp = await engine.delete(api.integration_id, "/repos/test")
    print(f"   DELETE /repos/test: {del_resp.status_code}")
    print()

    # 6. Mock Responses
    print("6. MOCK RESPONSES:")
    print("-" * 40)

    engine.mock(
        HttpMethod.GET,
        "/api/v1/special",
        Response(
            status_code=201,
            body={"special": "mocked response"},
            success=True
        )
    )

    special_api = engine.create_integration("special", "https://example.com")
    engine.activate(special_api.integration_id)

    resp = await engine.get(special_api.integration_id, "/api/v1/special")
    print(f"   Mocked response: {resp.body}")
    print()

    # 7. Data Transformation
    print("7. DATA TRANSFORMATION:")
    print("-" * 40)

    engine.add_transform("github_to_internal", "login", "username")
    engine.add_transform("github_to_internal", "avatar_url", "profile.image")
    engine.add_transform("github_to_internal", "email", "contact.email")
    engine.add_transform(
        "github_to_internal", "created_at", "joined",
        transform=lambda x: x[:10] if x else None
    )

    github_data = {
        "login": "octocat",
        "avatar_url": "https://github.com/avatar.png",
        "email": "octo@github.com",
        "created_at": "2023-01-15T12:00:00Z"
    }

    internal_data = engine.transform("github_to_internal", github_data)
    print(f"   Original: {github_data}")
    print(f"   Transformed: {internal_data}")
    print()

    # 8. Register Webhooks
    print("8. REGISTER WEBHOOKS:")
    print("-" * 40)

    webhook = engine.register_webhook(
        "repo_events",
        "https://myapp.com/webhooks/github",
        events=[WebhookEvent.CREATED, WebhookEvent.UPDATED],
        secret="webhook_secret_123"
    )

    print(f"   Webhook: {webhook.name}")
    print(f"   URL: {webhook.url}")
    print(f"   Events: {[e.value for e in webhook.events]}")
    print(f"   Secret: {webhook.secret[:10]}...")
    print()

    # 9. Webhook Handlers
    print("9. WEBHOOK HANDLERS:")
    print("-" * 40)

    events_received = []

    def on_created(webhook, event, data):
        events_received.append(("created", data))

    def on_updated(webhook, event, data):
        events_received.append(("updated", data))

    engine.on_webhook(WebhookEvent.CREATED, on_created)
    engine.on_webhook(WebhookEvent.UPDATED, on_updated)

    await engine.trigger_webhook(
        webhook.webhook_id,
        WebhookEvent.CREATED,
        {"repo": "test-repo", "action": "created"}
    )

    await engine.trigger_webhook(
        webhook.webhook_id,
        WebhookEvent.UPDATED,
        {"repo": "test-repo", "action": "updated"}
    )

    print(f"   Events received: {len(events_received)}")
    for event_type, data in events_received:
        print(f"   - {event_type}: {data}")
    print()

    # 10. Verify Webhook Signature
    print("10. VERIFY WEBHOOK SIGNATURE:")
    print("-" * 40)

    payload = '{"event": "push", "ref": "refs/heads/main"}'
    signature = hmac.new(
        webhook.secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    valid = engine.verify_webhook(webhook.webhook_id, payload, signature)
    print(f"   Payload: {payload[:40]}...")
    print(f"   Signature valid: {valid}")

    invalid = engine.verify_webhook(webhook.webhook_id, payload, "wrong_signature")
    print(f"   Invalid signature check: {invalid}")
    print()

    # 11. Multiple Integrations
    print("11. MULTIPLE INTEGRATIONS:")
    print("-" * 40)

    slack = engine.create_integration(
        "slack",
        "https://slack.com/api",
        auth=AuthConfig(auth_type=AuthType.BEARER, bearer_token="xoxb-slack-token")
    )

    discord = engine.create_integration(
        "discord",
        "https://discord.com/api/v10",
        auth=AuthConfig(auth_type=AuthType.BEARER, bearer_token="discord-bot-token")
    )

    print(f"   Integrations created:")
    for integration in engine._integrations.values():
        print(f"   - {integration.name}: {integration.base_url}")
    print()

    # 12. Get by Name
    print("12. GET BY NAME:")
    print("-" * 40)

    github = engine.get_by_name("github_api")
    print(f"   Found 'github_api': {github is not None}")
    print(f"   Integration ID: {github.integration_id if github else 'N/A'}")
    print()

    # 13. Call History
    print("13. CALL HISTORY:")
    print("-" * 40)

    history = engine.get_history()
    print(f"   Total calls: {len(history)}")
    for req, resp in history[:3]:
        print(f"   - {req.method.value} {req.url[:40]}... -> {resp.status_code}")
    print()

    # 14. List Webhooks
    print("14. LIST WEBHOOKS:")
    print("-" * 40)

    webhooks = engine.list_webhooks()
    print(f"   Total webhooks: {len(webhooks)}")
    for wh in webhooks:
        print(f"   - {wh.name}: {wh.url}")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Integration Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
