#!/usr/bin/env python3
"""
BAEL - API Documentation Generator
Comprehensive API documentation system.

Features:
- OpenAPI/Swagger generation
- Endpoint documentation
- Schema generation
- Request/Response examples
- Authentication docs
- Versioning support
- Markdown export
- HTML generation
- Interactive testing
- Change tracking
"""

import asyncio
import hashlib
import json
import logging
import re
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class HttpMethod(Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ParameterLocation(Enum):
    """Parameter location."""
    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    COOKIE = "cookie"
    BODY = "body"


class DataType(Enum):
    """Data types."""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    NULL = "null"


class AuthType(Enum):
    """Authentication types."""
    NONE = "none"
    API_KEY = "apiKey"
    BEARER = "bearer"
    BASIC = "basic"
    OAUTH2 = "oauth2"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SchemaProperty:
    """Schema property definition."""
    name: str
    data_type: DataType
    description: str = ""
    required: bool = False
    default: Any = None
    example: Any = None
    enum: List[Any] = field(default_factory=list)
    format: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    pattern: Optional[str] = None
    items: Optional['Schema'] = None  # For arrays


@dataclass
class Schema:
    """Schema definition."""
    name: str
    properties: List[SchemaProperty] = field(default_factory=list)
    description: str = ""
    example: Dict[str, Any] = field(default_factory=dict)

    def to_openapi(self) -> Dict[str, Any]:
        """Convert to OpenAPI schema."""
        required = [p.name for p in self.properties if p.required]

        properties = {}
        for prop in self.properties:
            prop_def = {"type": prop.data_type.value}

            if prop.description:
                prop_def["description"] = prop.description

            if prop.example is not None:
                prop_def["example"] = prop.example

            if prop.enum:
                prop_def["enum"] = prop.enum

            if prop.format:
                prop_def["format"] = prop.format

            if prop.default is not None:
                prop_def["default"] = prop.default

            if prop.min_length is not None:
                prop_def["minLength"] = prop.min_length

            if prop.max_length is not None:
                prop_def["maxLength"] = prop.max_length

            if prop.minimum is not None:
                prop_def["minimum"] = prop.minimum

            if prop.maximum is not None:
                prop_def["maximum"] = prop.maximum

            if prop.pattern:
                prop_def["pattern"] = prop.pattern

            if prop.items:
                prop_def["items"] = prop.items.to_openapi()

            properties[prop.name] = prop_def

        schema = {
            "type": "object",
            "properties": properties
        }

        if required:
            schema["required"] = required

        if self.description:
            schema["description"] = self.description

        if self.example:
            schema["example"] = self.example

        return schema


@dataclass
class Parameter:
    """API parameter."""
    name: str
    location: ParameterLocation
    data_type: DataType = DataType.STRING
    description: str = ""
    required: bool = False
    default: Any = None
    example: Any = None
    schema: Optional[Schema] = None

    def to_openapi(self) -> Dict[str, Any]:
        """Convert to OpenAPI parameter."""
        param = {
            "name": self.name,
            "in": self.location.value,
            "required": self.required,
            "schema": {"type": self.data_type.value}
        }

        if self.description:
            param["description"] = self.description

        if self.example is not None:
            param["example"] = self.example

        if self.default is not None:
            param["schema"]["default"] = self.default

        return param


@dataclass
class Response:
    """API response definition."""
    status_code: int
    description: str
    schema: Optional[Schema] = None
    example: Any = None
    headers: Dict[str, str] = field(default_factory=dict)

    def to_openapi(self) -> Dict[str, Any]:
        """Convert to OpenAPI response."""
        response = {"description": self.description}

        if self.schema:
            response["content"] = {
                "application/json": {
                    "schema": self.schema.to_openapi()
                }
            }

            if self.example:
                response["content"]["application/json"]["example"] = self.example

        if self.headers:
            response["headers"] = {
                name: {"description": desc, "schema": {"type": "string"}}
                for name, desc in self.headers.items()
            }

        return response


@dataclass
class Endpoint:
    """API endpoint definition."""
    path: str
    method: HttpMethod
    summary: str = ""
    description: str = ""
    operation_id: str = ""
    tags: List[str] = field(default_factory=list)
    parameters: List[Parameter] = field(default_factory=list)
    request_body: Optional[Schema] = None
    responses: List[Response] = field(default_factory=list)
    deprecated: bool = False
    security: List[str] = field(default_factory=list)

    def to_openapi(self) -> Dict[str, Any]:
        """Convert to OpenAPI operation."""
        operation = {}

        if self.summary:
            operation["summary"] = self.summary

        if self.description:
            operation["description"] = self.description

        if self.operation_id:
            operation["operationId"] = self.operation_id

        if self.tags:
            operation["tags"] = self.tags

        if self.parameters:
            operation["parameters"] = [p.to_openapi() for p in self.parameters]

        if self.request_body:
            operation["requestBody"] = {
                "content": {
                    "application/json": {
                        "schema": self.request_body.to_openapi()
                    }
                }
            }

        if self.responses:
            operation["responses"] = {
                str(r.status_code): r.to_openapi() for r in self.responses
            }
        else:
            operation["responses"] = {"200": {"description": "Success"}}

        if self.deprecated:
            operation["deprecated"] = True

        if self.security:
            operation["security"] = [{s: []} for s in self.security]

        return operation


@dataclass
class Tag:
    """API tag for grouping."""
    name: str
    description: str = ""
    external_docs: Optional[str] = None


@dataclass
class SecurityScheme:
    """Security scheme definition."""
    name: str
    auth_type: AuthType
    description: str = ""
    api_key_name: str = ""
    api_key_location: str = "header"
    oauth_flows: Dict[str, Any] = field(default_factory=dict)

    def to_openapi(self) -> Dict[str, Any]:
        """Convert to OpenAPI security scheme."""
        if self.auth_type == AuthType.API_KEY:
            return {
                "type": "apiKey",
                "name": self.api_key_name or "X-API-Key",
                "in": self.api_key_location,
                "description": self.description
            }

        if self.auth_type == AuthType.BEARER:
            return {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": self.description
            }

        if self.auth_type == AuthType.BASIC:
            return {
                "type": "http",
                "scheme": "basic",
                "description": self.description
            }

        if self.auth_type == AuthType.OAUTH2:
            return {
                "type": "oauth2",
                "flows": self.oauth_flows,
                "description": self.description
            }

        return {}


@dataclass
class APIInfo:
    """API information."""
    title: str
    version: str
    description: str = ""
    terms_of_service: str = ""
    contact_name: str = ""
    contact_email: str = ""
    license_name: str = ""
    license_url: str = ""


# =============================================================================
# DOCUMENTATION GENERATOR
# =============================================================================

class APIDocumentation:
    """
    Comprehensive API Documentation Generator for BAEL.

    Generates OpenAPI specs, Markdown docs, and HTML documentation.
    """

    def __init__(self, info: APIInfo):
        self.info = info
        self._endpoints: List[Endpoint] = []
        self._schemas: Dict[str, Schema] = {}
        self._tags: List[Tag] = []
        self._security_schemes: Dict[str, SecurityScheme] = {}
        self._servers: List[Dict[str, str]] = []

    # -------------------------------------------------------------------------
    # CONFIGURATION
    # -------------------------------------------------------------------------

    def add_server(self, url: str, description: str = "") -> 'APIDocumentation':
        """Add server."""
        self._servers.append({"url": url, "description": description})
        return self

    def add_tag(
        self,
        name: str,
        description: str = "",
        external_docs: str = None
    ) -> 'APIDocumentation':
        """Add tag."""
        self._tags.append(Tag(name, description, external_docs))
        return self

    def add_security_scheme(
        self,
        scheme: SecurityScheme
    ) -> 'APIDocumentation':
        """Add security scheme."""
        self._security_schemes[scheme.name] = scheme
        return self

    def add_schema(self, schema: Schema) -> 'APIDocumentation':
        """Add reusable schema."""
        self._schemas[schema.name] = schema
        return self

    # -------------------------------------------------------------------------
    # ENDPOINTS
    # -------------------------------------------------------------------------

    def add_endpoint(self, endpoint: Endpoint) -> 'APIDocumentation':
        """Add endpoint."""
        self._endpoints.append(endpoint)
        return self

    def get(
        self,
        path: str,
        summary: str = "",
        **kwargs
    ) -> 'APIDocumentation':
        """Add GET endpoint."""
        return self.add_endpoint(Endpoint(
            path=path,
            method=HttpMethod.GET,
            summary=summary,
            **kwargs
        ))

    def post(
        self,
        path: str,
        summary: str = "",
        **kwargs
    ) -> 'APIDocumentation':
        """Add POST endpoint."""
        return self.add_endpoint(Endpoint(
            path=path,
            method=HttpMethod.POST,
            summary=summary,
            **kwargs
        ))

    def put(
        self,
        path: str,
        summary: str = "",
        **kwargs
    ) -> 'APIDocumentation':
        """Add PUT endpoint."""
        return self.add_endpoint(Endpoint(
            path=path,
            method=HttpMethod.PUT,
            summary=summary,
            **kwargs
        ))

    def patch(
        self,
        path: str,
        summary: str = "",
        **kwargs
    ) -> 'APIDocumentation':
        """Add PATCH endpoint."""
        return self.add_endpoint(Endpoint(
            path=path,
            method=HttpMethod.PATCH,
            summary=summary,
            **kwargs
        ))

    def delete(
        self,
        path: str,
        summary: str = "",
        **kwargs
    ) -> 'APIDocumentation':
        """Add DELETE endpoint."""
        return self.add_endpoint(Endpoint(
            path=path,
            method=HttpMethod.DELETE,
            summary=summary,
            **kwargs
        ))

    # -------------------------------------------------------------------------
    # OPENAPI GENERATION
    # -------------------------------------------------------------------------

    def to_openapi(self) -> Dict[str, Any]:
        """Generate OpenAPI specification."""
        spec = {
            "openapi": "3.0.3",
            "info": self._build_info(),
            "paths": self._build_paths()
        }

        if self._servers:
            spec["servers"] = self._servers

        if self._tags:
            spec["tags"] = [
                {"name": t.name, "description": t.description}
                for t in self._tags
            ]

        components = {}

        if self._schemas:
            components["schemas"] = {
                name: schema.to_openapi()
                for name, schema in self._schemas.items()
            }

        if self._security_schemes:
            components["securitySchemes"] = {
                name: scheme.to_openapi()
                for name, scheme in self._security_schemes.items()
            }

        if components:
            spec["components"] = components

        return spec

    def _build_info(self) -> Dict[str, Any]:
        """Build info section."""
        info = {
            "title": self.info.title,
            "version": self.info.version
        }

        if self.info.description:
            info["description"] = self.info.description

        if self.info.terms_of_service:
            info["termsOfService"] = self.info.terms_of_service

        if self.info.contact_name or self.info.contact_email:
            info["contact"] = {}

            if self.info.contact_name:
                info["contact"]["name"] = self.info.contact_name

            if self.info.contact_email:
                info["contact"]["email"] = self.info.contact_email

        if self.info.license_name:
            info["license"] = {"name": self.info.license_name}

            if self.info.license_url:
                info["license"]["url"] = self.info.license_url

        return info

    def _build_paths(self) -> Dict[str, Any]:
        """Build paths section."""
        paths = defaultdict(dict)

        for endpoint in self._endpoints:
            method = endpoint.method.value.lower()
            paths[endpoint.path][method] = endpoint.to_openapi()

        return dict(paths)

    def to_json(self, indent: int = 2) -> str:
        """Export as JSON."""
        return json.dumps(self.to_openapi(), indent=indent)

    def to_yaml(self) -> str:
        """Export as YAML (simple implementation)."""
        def dict_to_yaml(d: Any, level: int = 0) -> str:
            indent = "  " * level
            lines = []

            if isinstance(d, dict):
                for key, value in d.items():
                    if isinstance(value, (dict, list)) and value:
                        lines.append(f"{indent}{key}:")
                        lines.append(dict_to_yaml(value, level + 1))
                    else:
                        lines.append(f"{indent}{key}: {json.dumps(value)}")

            elif isinstance(d, list):
                for item in d:
                    if isinstance(item, dict):
                        lines.append(f"{indent}-")
                        lines.append(dict_to_yaml(item, level + 1))
                    else:
                        lines.append(f"{indent}- {json.dumps(item)}")

            return "\n".join(lines)

        return dict_to_yaml(self.to_openapi())

    # -------------------------------------------------------------------------
    # MARKDOWN GENERATION
    # -------------------------------------------------------------------------

    def to_markdown(self) -> str:
        """Generate Markdown documentation."""
        lines = []

        # Title
        lines.append(f"# {self.info.title}")
        lines.append("")

        if self.info.description:
            lines.append(self.info.description)
            lines.append("")

        lines.append(f"**Version:** {self.info.version}")
        lines.append("")

        # Table of Contents
        lines.append("## Table of Contents")
        lines.append("")

        for tag in self._tags:
            lines.append(f"- [{tag.name}](#{tag.name.lower().replace(' ', '-')})")

        lines.append("")

        # Endpoints by tag
        for tag in self._tags:
            lines.append(f"## {tag.name}")
            lines.append("")

            if tag.description:
                lines.append(tag.description)
                lines.append("")

            # Find endpoints with this tag
            tag_endpoints = [e for e in self._endpoints if tag.name in e.tags]

            for endpoint in tag_endpoints:
                lines.extend(self._endpoint_to_markdown(endpoint))

        # Endpoints without tags
        untagged = [e for e in self._endpoints if not e.tags]

        if untagged:
            lines.append("## Other Endpoints")
            lines.append("")

            for endpoint in untagged:
                lines.extend(self._endpoint_to_markdown(endpoint))

        # Schemas
        if self._schemas:
            lines.append("## Schemas")
            lines.append("")

            for name, schema in self._schemas.items():
                lines.extend(self._schema_to_markdown(name, schema))

        return "\n".join(lines)

    def _endpoint_to_markdown(self, endpoint: Endpoint) -> List[str]:
        """Convert endpoint to Markdown."""
        lines = []

        method = endpoint.method.value
        deprecated = " (Deprecated)" if endpoint.deprecated else ""

        lines.append(f"### {method} {endpoint.path}{deprecated}")
        lines.append("")

        if endpoint.summary:
            lines.append(f"**{endpoint.summary}**")
            lines.append("")

        if endpoint.description:
            lines.append(endpoint.description)
            lines.append("")

        # Parameters
        if endpoint.parameters:
            lines.append("#### Parameters")
            lines.append("")
            lines.append("| Name | Location | Type | Required | Description |")
            lines.append("|------|----------|------|----------|-------------|")

            for param in endpoint.parameters:
                required = "Yes" if param.required else "No"
                lines.append(
                    f"| {param.name} | {param.location.value} | "
                    f"{param.data_type.value} | {required} | {param.description} |"
                )

            lines.append("")

        # Request Body
        if endpoint.request_body:
            lines.append("#### Request Body")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(endpoint.request_body.example or {}, indent=2))
            lines.append("```")
            lines.append("")

        # Responses
        if endpoint.responses:
            lines.append("#### Responses")
            lines.append("")

            for response in endpoint.responses:
                lines.append(f"**{response.status_code}** - {response.description}")
                lines.append("")

                if response.example:
                    lines.append("```json")
                    lines.append(json.dumps(response.example, indent=2))
                    lines.append("```")
                    lines.append("")

        lines.append("---")
        lines.append("")

        return lines

    def _schema_to_markdown(self, name: str, schema: Schema) -> List[str]:
        """Convert schema to Markdown."""
        lines = []

        lines.append(f"### {name}")
        lines.append("")

        if schema.description:
            lines.append(schema.description)
            lines.append("")

        if schema.properties:
            lines.append("| Property | Type | Required | Description |")
            lines.append("|----------|------|----------|-------------|")

            for prop in schema.properties:
                required = "Yes" if prop.required else "No"
                lines.append(
                    f"| {prop.name} | {prop.data_type.value} | "
                    f"{required} | {prop.description} |"
                )

            lines.append("")

        if schema.example:
            lines.append("**Example:**")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(schema.example, indent=2))
            lines.append("```")
            lines.append("")

        return lines

    # -------------------------------------------------------------------------
    # HTML GENERATION
    # -------------------------------------------------------------------------

    def to_html(self) -> str:
        """Generate HTML documentation."""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.info.title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        h3 {{ color: #666; }}
        .endpoint {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .method {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: bold;
            color: white;
            margin-right: 10px;
        }}
        .get {{ background: #61affe; }}
        .post {{ background: #49cc90; }}
        .put {{ background: #fca130; }}
        .patch {{ background: #50e3c2; }}
        .delete {{ background: #f93e3e; }}
        .path {{ font-family: monospace; font-size: 1.1em; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }}
        th {{ background: #f0f0f0; }}
        pre {{
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
        }}
        .deprecated {{
            opacity: 0.6;
            text-decoration: line-through;
        }}
    </style>
</head>
<body>
    <h1>{self.info.title}</h1>
    <p><strong>Version:</strong> {self.info.version}</p>
"""

        if self.info.description:
            html += f"    <p>{self.info.description}</p>\n"

        # Endpoints
        for endpoint in self._endpoints:
            method = endpoint.method.value.lower()
            deprecated = " deprecated" if endpoint.deprecated else ""

            html += f"""
    <div class="endpoint{deprecated}">
        <span class="method {method}">{endpoint.method.value}</span>
        <span class="path">{endpoint.path}</span>
        <h3>{endpoint.summary}</h3>
"""

            if endpoint.description:
                html += f"        <p>{endpoint.description}</p>\n"

            if endpoint.parameters:
                html += """
        <h4>Parameters</h4>
        <table>
            <tr><th>Name</th><th>Location</th><th>Type</th><th>Required</th><th>Description</th></tr>
"""
                for param in endpoint.parameters:
                    required = "Yes" if param.required else "No"
                    html += f"""            <tr>
                <td>{param.name}</td>
                <td>{param.location.value}</td>
                <td>{param.data_type.value}</td>
                <td>{required}</td>
                <td>{param.description}</td>
            </tr>
"""
                html += "        </table>\n"

            if endpoint.responses:
                html += "        <h4>Responses</h4>\n"

                for response in endpoint.responses:
                    html += f"        <p><strong>{response.status_code}</strong> - {response.description}</p>\n"

                    if response.example:
                        html += f"        <pre>{json.dumps(response.example, indent=2)}</pre>\n"

            html += "    </div>\n"

        html += """
</body>
</html>
"""

        return html


# =============================================================================
# ENDPOINT DECORATOR
# =============================================================================

def document(
    path: str,
    method: HttpMethod,
    summary: str = "",
    description: str = "",
    tags: List[str] = None,
    responses: List[Response] = None
) -> Callable:
    """Decorator to document endpoints."""
    def decorator(func: Callable) -> Callable:
        func._api_docs = Endpoint(
            path=path,
            method=method,
            summary=summary or func.__doc__ or "",
            description=description,
            tags=tags or [],
            responses=responses or []
        )
        return func

    return decorator


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the API Documentation Generator."""
    print("=" * 70)
    print("BAEL - API DOCUMENTATION GENERATOR DEMO")
    print("Comprehensive API Documentation System")
    print("=" * 70)
    print()

    # Create API documentation
    api = APIDocumentation(
        APIInfo(
            title="BAEL AI Agent API",
            version="1.0.0",
            description="The most advanced AI agent system ever created",
            contact_name="BAEL Team",
            contact_email="bael@example.com",
            license_name="MIT"
        )
    )

    # Add servers
    api.add_server("https://api.bael.ai/v1", "Production")
    api.add_server("https://staging-api.bael.ai/v1", "Staging")

    # Add tags
    api.add_tag("Agents", "AI Agent management endpoints")
    api.add_tag("Tasks", "Task execution and management")
    api.add_tag("Users", "User management")

    # Add security schemes
    api.add_security_scheme(SecurityScheme(
        name="BearerAuth",
        auth_type=AuthType.BEARER,
        description="JWT Bearer token authentication"
    ))

    api.add_security_scheme(SecurityScheme(
        name="ApiKeyAuth",
        auth_type=AuthType.API_KEY,
        api_key_name="X-API-Key",
        description="API key authentication"
    ))

    # Add schemas
    agent_schema = Schema(
        name="Agent",
        description="AI Agent definition",
        properties=[
            SchemaProperty("id", DataType.STRING, "Unique agent ID", required=True),
            SchemaProperty("name", DataType.STRING, "Agent name", required=True),
            SchemaProperty("type", DataType.STRING, "Agent type", enum=["assistant", "analyst", "executor"]),
            SchemaProperty("status", DataType.STRING, "Current status"),
            SchemaProperty("capabilities", DataType.ARRAY, "Agent capabilities"),
            SchemaProperty("created_at", DataType.STRING, "Creation timestamp", format="date-time")
        ],
        example={
            "id": "agent-001",
            "name": "Research Assistant",
            "type": "assistant",
            "status": "active",
            "capabilities": ["research", "summarize", "analyze"],
            "created_at": "2024-01-15T10:30:00Z"
        }
    )
    api.add_schema(agent_schema)

    task_schema = Schema(
        name="Task",
        description="Task definition",
        properties=[
            SchemaProperty("id", DataType.STRING, "Task ID", required=True),
            SchemaProperty("type", DataType.STRING, "Task type", required=True),
            SchemaProperty("priority", DataType.INTEGER, "Priority (1-10)", minimum=1, maximum=10),
            SchemaProperty("payload", DataType.OBJECT, "Task payload"),
            SchemaProperty("status", DataType.STRING, "Execution status")
        ],
        example={
            "id": "task-001",
            "type": "analysis",
            "priority": 5,
            "payload": {"data": "sample"},
            "status": "pending"
        }
    )
    api.add_schema(task_schema)

    # Add endpoints
    api.get(
        "/agents",
        summary="List all agents",
        description="Retrieve a paginated list of all AI agents",
        tags=["Agents"],
        parameters=[
            Parameter("page", ParameterLocation.QUERY, DataType.INTEGER, "Page number", default=1),
            Parameter("limit", ParameterLocation.QUERY, DataType.INTEGER, "Items per page", default=20),
            Parameter("status", ParameterLocation.QUERY, DataType.STRING, "Filter by status")
        ],
        responses=[
            Response(200, "Successful response", example={
                "data": [{"id": "agent-001", "name": "Assistant"}],
                "total": 100,
                "page": 1
            }),
            Response(401, "Unauthorized"),
            Response(500, "Server error")
        ],
        security=["BearerAuth"]
    )

    api.post(
        "/agents",
        summary="Create new agent",
        description="Create a new AI agent with specified configuration",
        tags=["Agents"],
        request_body=Schema(
            name="CreateAgent",
            properties=[
                SchemaProperty("name", DataType.STRING, "Agent name", required=True),
                SchemaProperty("type", DataType.STRING, "Agent type", required=True),
                SchemaProperty("capabilities", DataType.ARRAY, "Initial capabilities")
            ],
            example={"name": "New Agent", "type": "assistant", "capabilities": ["chat"]}
        ),
        responses=[
            Response(201, "Agent created", schema=agent_schema),
            Response(400, "Invalid request"),
            Response(401, "Unauthorized")
        ],
        security=["BearerAuth"]
    )

    api.get(
        "/agents/{agent_id}",
        summary="Get agent by ID",
        tags=["Agents"],
        parameters=[
            Parameter("agent_id", ParameterLocation.PATH, DataType.STRING, "Agent ID", required=True)
        ],
        responses=[
            Response(200, "Agent found", schema=agent_schema),
            Response(404, "Agent not found")
        ]
    )

    api.delete(
        "/agents/{agent_id}",
        summary="Delete agent",
        tags=["Agents"],
        parameters=[
            Parameter("agent_id", ParameterLocation.PATH, DataType.STRING, "Agent ID", required=True)
        ],
        responses=[
            Response(204, "Agent deleted"),
            Response(404, "Agent not found")
        ],
        security=["BearerAuth"]
    )

    api.post(
        "/tasks",
        summary="Submit new task",
        description="Submit a new task for execution by agents",
        tags=["Tasks"],
        request_body=task_schema,
        responses=[
            Response(202, "Task accepted", example={"task_id": "task-001", "status": "queued"}),
            Response(400, "Invalid task")
        ]
    )

    api.get(
        "/tasks/{task_id}",
        summary="Get task status",
        tags=["Tasks"],
        parameters=[
            Parameter("task_id", ParameterLocation.PATH, DataType.STRING, "Task ID", required=True)
        ],
        responses=[
            Response(200, "Task status", schema=task_schema),
            Response(404, "Task not found")
        ]
    )

    # Generate outputs
    print("1. OPENAPI SPECIFICATION (JSON):")
    print("-" * 40)
    print(api.to_json()[:500] + "...")
    print()

    print("2. MARKDOWN DOCUMENTATION:")
    print("-" * 40)
    markdown = api.to_markdown()
    print(markdown[:1000] + "...")
    print()

    print("3. HTML DOCUMENTATION:")
    print("-" * 40)
    html = api.to_html()
    print(html[:500] + "...")
    print()

    print("4. ENDPOINT COUNT:")
    print("-" * 40)
    print(f"   Total endpoints: {len(api._endpoints)}")
    print(f"   Total schemas: {len(api._schemas)}")
    print(f"   Total tags: {len(api._tags)}")
    print()

    print("5. SCHEMA EXAMPLE:")
    print("-" * 40)
    print(json.dumps(agent_schema.to_openapi(), indent=2)[:500] + "...")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - API Documentation Generator Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
