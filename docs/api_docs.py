#!/usr/bin/env python3
"""
BAEL - API Documentation Generator
Automatic OpenAPI/Swagger documentation generation.

Features:
- OpenAPI 3.0 spec generation
- Swagger UI integration
- ReDoc support
- Markdown documentation
- SDK generation helpers
"""

import inspect
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, List, Optional, Type, Union,
                    get_type_hints)

# =============================================================================
# OPENAPI TYPES
# =============================================================================

class ParameterLocation(Enum):
    """Parameter location in request."""
    QUERY = "query"
    PATH = "path"
    HEADER = "header"
    COOKIE = "cookie"


class HTTPMethod(Enum):
    """HTTP methods."""
    GET = "get"
    POST = "post"
    PUT = "put"
    DELETE = "delete"
    PATCH = "patch"
    OPTIONS = "options"
    HEAD = "head"


@dataclass
class SchemaProperty:
    """OpenAPI schema property."""
    name: str
    type: str
    description: str = ""
    required: bool = False
    default: Any = None
    enum: Optional[List[Any]] = None
    format: Optional[str] = None
    example: Any = None
    nullable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        result = {"type": self.type}

        if self.description:
            result["description"] = self.description
        if self.default is not None:
            result["default"] = self.default
        if self.enum:
            result["enum"] = self.enum
        if self.format:
            result["format"] = self.format
        if self.example is not None:
            result["example"] = self.example
        if self.nullable:
            result["nullable"] = True

        return result


@dataclass
class Schema:
    """OpenAPI schema object."""
    type: str = "object"
    title: Optional[str] = None
    description: Optional[str] = None
    properties: Dict[str, SchemaProperty] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    items: Optional["Schema"] = None
    ref: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        if self.ref:
            return {"$ref": f"#/components/schemas/{self.ref}"}

        result: Dict[str, Any] = {"type": self.type}

        if self.title:
            result["title"] = self.title
        if self.description:
            result["description"] = self.description

        if self.type == "object" and self.properties:
            result["properties"] = {
                name: prop.to_dict()
                for name, prop in self.properties.items()
            }
            if self.required:
                result["required"] = self.required

        if self.type == "array" and self.items:
            result["items"] = self.items.to_dict()

        return result


@dataclass
class Parameter:
    """OpenAPI parameter."""
    name: str
    location: ParameterLocation
    description: str = ""
    required: bool = False
    schema: Optional[Schema] = None
    example: Any = None
    deprecated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "in": self.location.value,
            "required": self.required
        }

        if self.description:
            result["description"] = self.description
        if self.schema:
            result["schema"] = self.schema.to_dict()
        if self.example is not None:
            result["example"] = self.example
        if self.deprecated:
            result["deprecated"] = True

        return result


@dataclass
class RequestBody:
    """OpenAPI request body."""
    content_type: str = "application/json"
    schema: Optional[Schema] = None
    description: str = ""
    required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "required": self.required,
            "content": {
                self.content_type: {}
            }
        }

        if self.description:
            result["description"] = self.description
        if self.schema:
            result["content"][self.content_type]["schema"] = self.schema.to_dict()

        return result


@dataclass
class Response:
    """OpenAPI response."""
    status_code: int
    description: str
    schema: Optional[Schema] = None
    content_type: str = "application/json"
    headers: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {"description": self.description}

        if self.schema:
            result["content"] = {
                self.content_type: {
                    "schema": self.schema.to_dict()
                }
            }

        if self.headers:
            result["headers"] = self.headers

        return result


@dataclass
class Operation:
    """OpenAPI operation (endpoint)."""
    method: HTTPMethod
    path: str
    summary: str = ""
    description: str = ""
    operation_id: str = ""
    tags: List[str] = field(default_factory=list)
    parameters: List[Parameter] = field(default_factory=list)
    request_body: Optional[RequestBody] = None
    responses: Dict[int, Response] = field(default_factory=dict)
    deprecated: bool = False
    security: List[Dict[str, List[str]]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        if self.summary:
            result["summary"] = self.summary
        if self.description:
            result["description"] = self.description
        if self.operation_id:
            result["operationId"] = self.operation_id
        if self.tags:
            result["tags"] = self.tags
        if self.parameters:
            result["parameters"] = [p.to_dict() for p in self.parameters]
        if self.request_body:
            result["requestBody"] = self.request_body.to_dict()
        if self.responses:
            result["responses"] = {
                str(code): resp.to_dict()
                for code, resp in self.responses.items()
            }
        if self.deprecated:
            result["deprecated"] = True
        if self.security:
            result["security"] = self.security

        return result


@dataclass
class Tag:
    """OpenAPI tag."""
    name: str
    description: str = ""
    external_docs: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"name": self.name}
        if self.description:
            result["description"] = self.description
        if self.external_docs:
            result["externalDocs"] = self.external_docs
        return result


@dataclass
class SecurityScheme:
    """OpenAPI security scheme."""
    type: str  # apiKey, http, oauth2, openIdConnect
    name: str
    scheme: str = ""  # bearer, basic
    bearer_format: str = ""
    location: str = "header"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        result = {"type": self.type}

        if self.type == "apiKey":
            result["name"] = self.name
            result["in"] = self.location
        elif self.type == "http":
            result["scheme"] = self.scheme
            if self.bearer_format:
                result["bearerFormat"] = self.bearer_format

        if self.description:
            result["description"] = self.description

        return result


@dataclass
class OpenAPISpec:
    """Complete OpenAPI specification."""
    title: str
    version: str
    description: str = ""
    terms_of_service: str = ""
    contact: Dict[str, str] = field(default_factory=dict)
    license: Dict[str, str] = field(default_factory=dict)
    servers: List[Dict[str, str]] = field(default_factory=list)
    tags: List[Tag] = field(default_factory=list)
    paths: Dict[str, Dict[str, Operation]] = field(default_factory=dict)
    schemas: Dict[str, Schema] = field(default_factory=dict)
    security_schemes: Dict[str, SecurityScheme] = field(default_factory=dict)

    def add_operation(self, operation: Operation) -> None:
        """Add an operation to the spec."""
        if operation.path not in self.paths:
            self.paths[operation.path] = {}
        self.paths[operation.path][operation.method.value] = operation

    def add_schema(self, name: str, schema: Schema) -> None:
        """Add a schema to components."""
        self.schemas[name] = schema

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "openapi": "3.0.3",
            "info": {
                "title": self.title,
                "version": self.version
            }
        }

        if self.description:
            result["info"]["description"] = self.description
        if self.terms_of_service:
            result["info"]["termsOfService"] = self.terms_of_service
        if self.contact:
            result["info"]["contact"] = self.contact
        if self.license:
            result["info"]["license"] = self.license

        if self.servers:
            result["servers"] = self.servers

        if self.tags:
            result["tags"] = [t.to_dict() for t in self.tags]

        if self.paths:
            result["paths"] = {}
            for path, methods in self.paths.items():
                result["paths"][path] = {
                    method: op.to_dict()
                    for method, op in methods.items()
                }

        components: Dict[str, Any] = {}
        if self.schemas:
            components["schemas"] = {
                name: schema.to_dict()
                for name, schema in self.schemas.items()
            }
        if self.security_schemes:
            components["securitySchemes"] = {
                name: scheme.to_dict()
                for name, scheme in self.security_schemes.items()
            }
        if components:
            result["components"] = components

        return result

    def to_json(self, indent: int = 2) -> str:
        """Export as JSON."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_yaml(self) -> str:
        """Export as YAML."""
        import yaml
        return yaml.dump(self.to_dict(), sort_keys=False, allow_unicode=True)


# =============================================================================
# TYPE TO SCHEMA CONVERTER
# =============================================================================

class TypeConverter:
    """Convert Python types to OpenAPI schemas."""

    TYPE_MAP = {
        str: ("string", None),
        int: ("integer", None),
        float: ("number", None),
        bool: ("boolean", None),
        bytes: ("string", "binary"),
        datetime: ("string", "date-time"),
    }

    @classmethod
    def convert(cls, python_type: Type) -> Schema:
        """Convert Python type to OpenAPI schema."""
        origin = getattr(python_type, "__origin__", None)

        # Handle None
        if python_type is type(None):
            return Schema(type="null")

        # Handle basic types
        if python_type in cls.TYPE_MAP:
            type_str, format_str = cls.TYPE_MAP[python_type]
            schema = Schema(type=type_str)
            if format_str:
                schema.properties["format"] = SchemaProperty(
                    name="format", type=format_str
                )
            return schema

        # Handle List/list
        if origin in (list, List):
            args = getattr(python_type, "__args__", (Any,))
            item_schema = cls.convert(args[0]) if args else Schema(type="object")
            return Schema(type="array", items=item_schema)

        # Handle Dict/dict
        if origin in (dict, Dict):
            return Schema(type="object")

        # Handle Optional
        if origin is Union:
            args = getattr(python_type, "__args__", ())
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1:
                schema = cls.convert(non_none[0])
                # Mark as nullable
                return schema

        # Handle Enum
        if isinstance(python_type, type) and issubclass(python_type, Enum):
            values = [e.value for e in python_type]
            return Schema(
                type="string",
                properties={"enum": SchemaProperty(name="enum", type="string", enum=values)}
            )

        # Handle dataclass
        if hasattr(python_type, "__dataclass_fields__"):
            return cls._convert_dataclass(python_type)

        # Handle Pydantic models
        if hasattr(python_type, "__fields__"):
            return cls._convert_pydantic(python_type)

        # Default to object
        return Schema(type="object")

    @classmethod
    def _convert_dataclass(cls, dc_type: Type) -> Schema:
        """Convert dataclass to schema."""
        fields = dc_type.__dataclass_fields__
        hints = get_type_hints(dc_type)

        properties = {}
        required = []

        for name, dc_field in fields.items():
            field_type = hints.get(name, Any)
            field_schema = cls.convert(field_type)

            prop = SchemaProperty(
                name=name,
                type=field_schema.type,
                description=dc_field.metadata.get("description", ""),
                default=dc_field.default if dc_field.default is not dc_field.default_factory else None
            )
            properties[name] = prop

            # Check if required
            if dc_field.default is dc_field.default_factory and dc_field.default_factory is type(None):
                required.append(name)

        return Schema(
            type="object",
            title=dc_type.__name__,
            description=dc_type.__doc__ or "",
            properties=properties,
            required=required
        )

    @classmethod
    def _convert_pydantic(cls, model_type: Type) -> Schema:
        """Convert Pydantic model to schema."""
        properties = {}
        required = []

        for name, field in model_type.__fields__.items():
            field_schema = cls.convert(field.outer_type_)

            prop = SchemaProperty(
                name=name,
                type=field_schema.type,
                description=field.field_info.description or "",
                default=field.default if field.default is not None else None
            )
            properties[name] = prop

            if field.required:
                required.append(name)

        return Schema(
            type="object",
            title=model_type.__name__,
            description=model_type.__doc__ or "",
            properties=properties,
            required=required
        )


# =============================================================================
# DOCSTRING PARSER
# =============================================================================

class DocstringParser:
    """Parse docstrings into structured documentation."""

    @staticmethod
    def parse(docstring: str) -> Dict[str, Any]:
        """Parse docstring into components."""
        if not docstring:
            return {"summary": "", "description": "", "params": {}, "returns": ""}

        lines = docstring.strip().split("\n")

        result = {
            "summary": "",
            "description": "",
            "params": {},
            "returns": "",
            "raises": []
        }

        # First non-empty line is summary
        for i, line in enumerate(lines):
            line = line.strip()
            if line:
                result["summary"] = line
                lines = lines[i+1:]
                break

        # Parse remaining lines
        current_section = "description"
        current_param = None
        description_lines = []

        for line in lines:
            line = line.strip()

            # Check for section headers
            if line.startswith("Args:") or line.startswith("Parameters:"):
                current_section = "params"
                continue
            elif line.startswith("Returns:"):
                current_section = "returns"
                continue
            elif line.startswith("Raises:"):
                current_section = "raises"
                continue
            elif line.startswith("Example"):
                current_section = "example"
                continue

            if current_section == "description":
                description_lines.append(line)

            elif current_section == "params":
                # Parse parameter
                match = re.match(r"(\w+)\s*(?:\(([^)]+)\))?:\s*(.+)", line)
                if match:
                    param_name = match.group(1)
                    param_type = match.group(2) or ""
                    param_desc = match.group(3)
                    result["params"][param_name] = {
                        "type": param_type,
                        "description": param_desc
                    }
                    current_param = param_name
                elif current_param and line:
                    # Continuation of previous param
                    result["params"][current_param]["description"] += " " + line

            elif current_section == "returns":
                if result["returns"]:
                    result["returns"] += " " + line
                else:
                    result["returns"] = line

            elif current_section == "raises":
                match = re.match(r"(\w+):\s*(.+)", line)
                if match:
                    result["raises"].append({
                        "exception": match.group(1),
                        "description": match.group(2)
                    })

        result["description"] = " ".join(description_lines).strip()

        return result


# =============================================================================
# DOCUMENTATION GENERATOR
# =============================================================================

class DocGenerator:
    """Generate documentation from code."""

    def __init__(self):
        self.spec = OpenAPISpec(
            title="BAEL API",
            version="1.0.0",
            description="The Lord of All AI Agents - REST API"
        )

    def add_default_info(self) -> None:
        """Add default API information."""
        self.spec.description = """
# BAEL - The Lord of All AI Agents

Enterprise-grade AI agent orchestration platform with advanced reasoning,
multi-model support, and comprehensive tool integration.

## Features

- **Multi-Model Routing**: Intelligent routing between OpenAI, Anthropic, and local models
- **Advanced Reasoning**: Chain of Thought, Tree of Thoughts, Graph of Thoughts
- **5-Layer Memory**: Episodic, semantic, procedural, working, and vector memory
- **Tool Execution**: Sandboxed tool execution with 50+ built-in tools
- **Multi-Agent Collaboration**: Swarm orchestration and consensus mechanisms

## Authentication

All endpoints require an API key passed in the `Authorization` header:

```
Authorization: Bearer YOUR_API_KEY
```

## Rate Limits

- Default: 100 requests/minute
- Premium: 1000 requests/minute
        """

        self.spec.contact = {
            "name": "BAEL Support",
            "email": "support@bael.ai",
            "url": "https://bael.ai"
        }

        self.spec.license = {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT"
        }

        self.spec.servers = [
            {"url": "http://localhost:8000", "description": "Development"},
            {"url": "https://api.bael.ai", "description": "Production"}
        ]

        # Add security scheme
        self.spec.security_schemes["bearerAuth"] = SecurityScheme(
            type="http",
            name="bearerAuth",
            scheme="bearer",
            bearer_format="JWT",
            description="JWT token authentication"
        )

        self.spec.security_schemes["apiKey"] = SecurityScheme(
            type="apiKey",
            name="X-API-Key",
            location="header",
            description="API key authentication"
        )

    def add_standard_tags(self) -> None:
        """Add standard API tags."""
        tags = [
            Tag("Chat", "Chat and conversation endpoints"),
            Tag("Agents", "Agent management and orchestration"),
            Tag("Tasks", "Task execution and management"),
            Tag("Memory", "Memory operations and retrieval"),
            Tag("Tools", "Tool registry and execution"),
            Tag("Analytics", "Metrics and analytics"),
            Tag("System", "System status and configuration")
        ]

        self.spec.tags = tags

    def add_standard_schemas(self) -> None:
        """Add standard response schemas."""
        # ChatMessage schema
        self.spec.add_schema("ChatMessage", Schema(
            type="object",
            title="ChatMessage",
            description="A chat message",
            properties={
                "role": SchemaProperty("role", "string", enum=["user", "assistant", "system"]),
                "content": SchemaProperty("content", "string", description="Message content"),
                "timestamp": SchemaProperty("timestamp", "string", format="date-time")
            },
            required=["role", "content"]
        ))

        # ChatRequest schema
        self.spec.add_schema("ChatRequest", Schema(
            type="object",
            title="ChatRequest",
            description="Chat completion request",
            properties={
                "messages": SchemaProperty("messages", "array", description="Conversation messages"),
                "model": SchemaProperty("model", "string", description="Model to use"),
                "temperature": SchemaProperty("temperature", "number", default=0.7),
                "max_tokens": SchemaProperty("max_tokens", "integer", default=1000),
                "stream": SchemaProperty("stream", "boolean", default=False)
            },
            required=["messages"]
        ))

        # ChatResponse schema
        self.spec.add_schema("ChatResponse", Schema(
            type="object",
            title="ChatResponse",
            description="Chat completion response",
            properties={
                "id": SchemaProperty("id", "string", description="Response ID"),
                "content": SchemaProperty("content", "string", description="Generated content"),
                "model": SchemaProperty("model", "string"),
                "usage": SchemaProperty("usage", "object")
            }
        ))

        # Error schema
        self.spec.add_schema("Error", Schema(
            type="object",
            title="Error",
            description="Error response",
            properties={
                "error": SchemaProperty("error", "string"),
                "code": SchemaProperty("code", "integer"),
                "details": SchemaProperty("details", "object")
            },
            required=["error", "code"]
        ))

        # Agent schema
        self.spec.add_schema("Agent", Schema(
            type="object",
            title="Agent",
            description="AI Agent configuration",
            properties={
                "id": SchemaProperty("id", "string"),
                "name": SchemaProperty("name", "string"),
                "persona": SchemaProperty("persona", "string"),
                "capabilities": SchemaProperty("capabilities", "array"),
                "status": SchemaProperty("status", "string")
            }
        ))

        # Task schema
        self.spec.add_schema("Task", Schema(
            type="object",
            title="Task",
            description="Task definition",
            properties={
                "id": SchemaProperty("id", "string"),
                "type": SchemaProperty("type", "string"),
                "description": SchemaProperty("description", "string"),
                "status": SchemaProperty("status", "string"),
                "result": SchemaProperty("result", "object"),
                "created_at": SchemaProperty("created_at", "string", format="date-time"),
                "completed_at": SchemaProperty("completed_at", "string", format="date-time")
            }
        ))

    def add_standard_endpoints(self) -> None:
        """Add standard API endpoints."""
        # Chat endpoint
        self.spec.add_operation(Operation(
            method=HTTPMethod.POST,
            path="/api/chat",
            summary="Create chat completion",
            description="Generate a response to a conversation",
            operation_id="createChatCompletion",
            tags=["Chat"],
            request_body=RequestBody(
                schema=Schema(ref="ChatRequest"),
                description="Chat request"
            ),
            responses={
                200: Response(200, "Successful response", Schema(ref="ChatResponse")),
                400: Response(400, "Bad request", Schema(ref="Error")),
                401: Response(401, "Unauthorized", Schema(ref="Error")),
                500: Response(500, "Server error", Schema(ref="Error"))
            },
            security=[{"bearerAuth": []}]
        ))

        # Agents endpoints
        self.spec.add_operation(Operation(
            method=HTTPMethod.GET,
            path="/api/agents",
            summary="List agents",
            description="Get all configured agents",
            operation_id="listAgents",
            tags=["Agents"],
            responses={
                200: Response(200, "List of agents", Schema(type="array", items=Schema(ref="Agent")))
            }
        ))

        self.spec.add_operation(Operation(
            method=HTTPMethod.POST,
            path="/api/agents",
            summary="Create agent",
            description="Create a new agent",
            operation_id="createAgent",
            tags=["Agents"],
            request_body=RequestBody(schema=Schema(ref="Agent")),
            responses={
                201: Response(201, "Agent created", Schema(ref="Agent")),
                400: Response(400, "Bad request", Schema(ref="Error"))
            }
        ))

        # Tasks endpoints
        self.spec.add_operation(Operation(
            method=HTTPMethod.POST,
            path="/api/tasks",
            summary="Create task",
            description="Submit a new task for execution",
            operation_id="createTask",
            tags=["Tasks"],
            request_body=RequestBody(schema=Schema(ref="Task")),
            responses={
                201: Response(201, "Task created", Schema(ref="Task")),
                400: Response(400, "Bad request", Schema(ref="Error"))
            }
        ))

        self.spec.add_operation(Operation(
            method=HTTPMethod.GET,
            path="/api/tasks/{task_id}",
            summary="Get task",
            description="Get task details and status",
            operation_id="getTask",
            tags=["Tasks"],
            parameters=[
                Parameter(
                    name="task_id",
                    location=ParameterLocation.PATH,
                    required=True,
                    schema=Schema(type="string")
                )
            ],
            responses={
                200: Response(200, "Task details", Schema(ref="Task")),
                404: Response(404, "Task not found", Schema(ref="Error"))
            }
        ))

        # System endpoints
        self.spec.add_operation(Operation(
            method=HTTPMethod.GET,
            path="/api/system/health",
            summary="Health check",
            description="Check system health status",
            operation_id="healthCheck",
            tags=["System"],
            responses={
                200: Response(200, "System healthy", Schema(type="object"))
            }
        ))

        self.spec.add_operation(Operation(
            method=HTTPMethod.GET,
            path="/api/system/status",
            summary="System status",
            description="Get detailed system status",
            operation_id="systemStatus",
            tags=["System"],
            responses={
                200: Response(200, "System status", Schema(type="object"))
            }
        ))

    def generate_full_spec(self) -> OpenAPISpec:
        """Generate complete API specification."""
        self.add_default_info()
        self.add_standard_tags()
        self.add_standard_schemas()
        self.add_standard_endpoints()
        return self.spec

    def export_json(self, path: str) -> None:
        """Export specification as JSON."""
        with open(path, 'w') as f:
            f.write(self.spec.to_json())

    def export_yaml(self, path: str) -> None:
        """Export specification as YAML."""
        with open(path, 'w') as f:
            f.write(self.spec.to_yaml())


# =============================================================================
# SWAGGER UI GENERATOR
# =============================================================================

class SwaggerUIGenerator:
    """Generate Swagger UI HTML page."""

    TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - API Documentation</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.10.3/swagger-ui.css">
    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
        .swagger-ui .topbar {{
            background-color: #1a1a2e;
        }}
        .swagger-ui .info .title {{
            color: #1a1a2e;
        }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5.10.3/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5.10.3/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {{
            const ui = SwaggerUIBundle({{
                url: "{spec_url}",
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                persistAuthorization: true
            }});
            window.ui = ui;
        }};
    </script>
</body>
</html>"""

    @classmethod
    def generate(cls, title: str, spec_url: str) -> str:
        """Generate Swagger UI HTML."""
        return cls.TEMPLATE.format(title=title, spec_url=spec_url)

    @classmethod
    def save(cls, path: str, title: str, spec_url: str) -> None:
        """Save Swagger UI HTML to file."""
        html = cls.generate(title, spec_url)
        with open(path, 'w') as f:
            f.write(html)


# =============================================================================
# REDOC GENERATOR
# =============================================================================

class ReDocGenerator:
    """Generate ReDoc HTML page."""

    TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>{title} - API Documentation</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
    </style>
</head>
<body>
    <redoc spec-url='{spec_url}'></redoc>
    <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
</body>
</html>"""

    @classmethod
    def generate(cls, title: str, spec_url: str) -> str:
        """Generate ReDoc HTML."""
        return cls.TEMPLATE.format(title=title, spec_url=spec_url)

    @classmethod
    def save(cls, path: str, title: str, spec_url: str) -> None:
        """Save ReDoc HTML to file."""
        html = cls.generate(title, spec_url)
        with open(path, 'w') as f:
            f.write(html)


# =============================================================================
# MARKDOWN GENERATOR
# =============================================================================

class MarkdownDocGenerator:
    """Generate Markdown documentation from OpenAPI spec."""

    def __init__(self, spec: OpenAPISpec):
        self.spec = spec

    def generate(self) -> str:
        """Generate full Markdown documentation."""
        sections = [
            self._generate_header(),
            self._generate_authentication(),
            self._generate_endpoints(),
            self._generate_schemas()
        ]

        return "\n\n".join(sections)

    def _generate_header(self) -> str:
        """Generate header section."""
        return f"""# {self.spec.title}

Version: {self.spec.version}

{self.spec.description}

## Servers

| Environment | URL |
|-------------|-----|
""" + "\n".join(
            f"| {s.get('description', 'Server')} | `{s['url']}` |"
            for s in self.spec.servers
        )

    def _generate_authentication(self) -> str:
        """Generate authentication section."""
        if not self.spec.security_schemes:
            return ""

        lines = ["## Authentication\n"]

        for name, scheme in self.spec.security_schemes.items():
            lines.append(f"### {name}")
            lines.append(f"\n{scheme.description}")
            lines.append(f"\n- Type: `{scheme.type}`")
            if scheme.scheme:
                lines.append(f"- Scheme: `{scheme.scheme}`")
            lines.append("")

        return "\n".join(lines)

    def _generate_endpoints(self) -> str:
        """Generate endpoints section."""
        lines = ["## Endpoints\n"]

        # Group by tag
        by_tag: Dict[str, List[Operation]] = {}

        for path, methods in self.spec.paths.items():
            for method, op in methods.items():
                for tag in op.tags or ["Other"]:
                    if tag not in by_tag:
                        by_tag[tag] = []
                    by_tag[tag].append(op)

        for tag, operations in by_tag.items():
            lines.append(f"### {tag}\n")

            for op in operations:
                method_upper = op.method.value.upper()
                lines.append(f"#### {method_upper} {op.path}")
                lines.append(f"\n{op.summary}")

                if op.description:
                    lines.append(f"\n{op.description}")

                if op.parameters:
                    lines.append("\n**Parameters:**\n")
                    lines.append("| Name | Location | Type | Required | Description |")
                    lines.append("|------|----------|------|----------|-------------|")

                    for param in op.parameters:
                        param_type = param.schema.type if param.schema else "string"
                        lines.append(
                            f"| {param.name} | {param.location.value} | "
                            f"{param_type} | {param.required} | {param.description} |"
                        )

                if op.request_body:
                    lines.append("\n**Request Body:**\n")
                    lines.append(f"Content-Type: `{op.request_body.content_type}`")

                lines.append("\n**Responses:**\n")
                lines.append("| Code | Description |")
                lines.append("|------|-------------|")

                for code, resp in op.responses.items():
                    lines.append(f"| {code} | {resp.description} |")

                lines.append("")

        return "\n".join(lines)

    def _generate_schemas(self) -> str:
        """Generate schemas section."""
        if not self.spec.schemas:
            return ""

        lines = ["## Schemas\n"]

        for name, schema in self.spec.schemas.items():
            lines.append(f"### {name}")

            if schema.description:
                lines.append(f"\n{schema.description}")

            if schema.properties:
                lines.append("\n| Property | Type | Required | Description |")
                lines.append("|----------|------|----------|-------------|")

                for prop_name, prop in schema.properties.items():
                    required = "Yes" if prop_name in schema.required else "No"
                    lines.append(
                        f"| {prop_name} | {prop.type} | {required} | {prop.description} |"
                    )

            lines.append("")

        return "\n".join(lines)

    def save(self, path: str) -> None:
        """Save documentation to file."""
        with open(path, 'w') as f:
            f.write(self.generate())


# =============================================================================
# MAIN
# =============================================================================

def generate_docs(output_dir: str = "docs/api") -> None:
    """Generate all API documentation."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate OpenAPI spec
    generator = DocGenerator()
    spec = generator.generate_full_spec()

    # Export JSON
    json_path = output_path / "openapi.json"
    generator.export_json(str(json_path))
    print(f"Generated: {json_path}")

    # Export YAML
    try:
        yaml_path = output_path / "openapi.yaml"
        generator.export_yaml(str(yaml_path))
        print(f"Generated: {yaml_path}")
    except ImportError:
        print("Skipping YAML (pyyaml not installed)")

    # Generate Swagger UI
    swagger_path = output_path / "swagger.html"
    SwaggerUIGenerator.save(str(swagger_path), spec.title, "openapi.json")
    print(f"Generated: {swagger_path}")

    # Generate ReDoc
    redoc_path = output_path / "redoc.html"
    ReDocGenerator.save(str(redoc_path), spec.title, "openapi.json")
    print(f"Generated: {redoc_path}")

    # Generate Markdown
    md_gen = MarkdownDocGenerator(spec)
    md_path = output_path / "API.md"
    md_gen.save(str(md_path))
    print(f"Generated: {md_path}")

    print(f"\nDocumentation generated in: {output_path}")


if __name__ == "__main__":
    generate_docs()
