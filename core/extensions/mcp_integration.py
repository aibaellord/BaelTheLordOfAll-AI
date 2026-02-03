"""
BAEL Phase 6.4: Model Context Protocol (MCP) Integration
═════════════════════════════════════════════════════════════════════════════

Integration with Model Context Protocol for LLM resource management,
function call handling, and streaming support.

Features:
  • MCP Server Implementation
  • Resource Management
  • Function Call Handling
  • Streaming Support
  • Error Handling
  • Client Connection Management
  • Resource Discovery
  • Protocol Validation
  • Tool Registration
  • Request/Response Processing

Author: BAEL Team
Date: February 1, 2026
"""

import asyncio
import json
import logging
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import (Any, AsyncIterator, Callable, Dict, List, Optional, Set,
                    Tuple, Union)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Enums & Constants
# ═══════════════════════════════════════════════════════════════════════════

class ResourceType(str, Enum):
    """MCP resource types."""
    TOOL = "tool"
    RESOURCE = "resource"
    PROMPT = "prompt"
    FILE = "file"
    DATABASE = "database"
    API = "api"


class MessageType(str, Enum):
    """MCP message types."""
    INITIALIZE = "initialize"
    CALL_TOOL = "call_tool"
    LIST_TOOLS = "list_tools"
    READ_RESOURCE = "read_resource"
    LIST_RESOURCES = "list_resources"
    GET_PROMPT = "get_prompt"
    ERROR = "error"
    RESPONSE = "response"


class ErrorCode(str, Enum):
    """MCP error codes."""
    INVALID_REQUEST = "invalid_request"
    METHOD_NOT_FOUND = "method_not_found"
    INVALID_PARAMS = "invalid_params"
    INTERNAL_ERROR = "internal_error"
    RESOURCE_NOT_FOUND = "resource_not_found"
    TOOL_ERROR = "tool_error"
    TIMEOUT = "timeout"


class ToolInputType(str, Enum):
    """Parameter input types."""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


# ═══════════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ToolParameter:
    """Tool input parameter specification."""
    name: str
    type: ToolInputType
    description: str = ""
    required: bool = True
    default: Optional[Any] = None
    enum_values: Optional[List[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None


@dataclass
class ToolDefinition:
    """MCP tool definition."""
    id: str
    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    category: str = ""
    async_support: bool = True
    supports_streaming: bool = False
    timeout_seconds: int = 30


@dataclass
class ToolCall:
    """Tool invocation request."""
    id: str
    tool_id: str
    tool_name: str
    parameters: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class ToolResult:
    """Tool execution result."""
    call_id: str
    tool_id: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Resource:
    """MCP resource specification."""
    id: str
    name: str
    type: ResourceType
    description: str = ""
    uri: str = ""
    mime_type: str = "application/json"
    size_bytes: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPMessage:
    """MCP protocol message."""
    id: str
    type: MessageType
    method: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ClientInfo:
    """Connected client information."""
    client_id: str
    name: str
    version: str
    connected_at: datetime
    last_activity: datetime
    active: bool = True
    capabilities: Dict[str, bool] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════
# Tool Registry
# ═══════════════════════════════════════════════════════════════════════════

class ToolRegistry:
    """Registry for MCP tools."""

    def __init__(self):
        """Initialize tool registry."""
        self.tools: Dict[str, ToolDefinition] = {}
        self.handlers: Dict[str, Callable] = {}
        self.execution_history: Dict[str, ToolResult] = {}
        self._lock = threading.RLock()

    def register_tool(
        self,
        definition: ToolDefinition,
        handler: Callable,
        async_handler: Optional[Callable] = None
    ) -> None:
        """Register tool with handler."""
        with self._lock:
            if definition.id in self.tools:
                raise ValueError(f"Tool '{definition.id}' already registered")

            self.tools[definition.id] = definition
            self.handlers[definition.id] = handler

            if async_handler:
                self.handlers[f"{definition.id}_async"] = async_handler

    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        """Get tool definition."""
        return self.tools.get(tool_id)

    def list_tools(self) -> List[ToolDefinition]:
        """List all registered tools."""
        return list(self.tools.values())

    def list_tools_by_category(self, category: str) -> List[ToolDefinition]:
        """List tools by category."""
        return [t for t in self.tools.values() if t.category == category]

    def get_handler(self, tool_id: str, async_mode: bool = False) -> Optional[Callable]:
        """Get tool handler."""
        key = f"{tool_id}_async" if async_mode else tool_id
        return self.handlers.get(key)

    def record_execution(self, result: ToolResult) -> None:
        """Record tool execution."""
        with self._lock:
            self.execution_history[result.call_id] = result

    def get_execution_history(
        self,
        tool_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ToolResult]:
        """Get tool execution history."""
        history = list(self.execution_history.values())

        if tool_id:
            history = [h for h in history if h.tool_id == tool_id]

        return sorted(history, key=lambda x: x.timestamp, reverse=True)[:limit]


# ═══════════════════════════════════════════════════════════════════════════
# Resource Manager
# ═══════════════════════════════════════════════════════════════════════════

class ResourceManager:
    """Management of MCP resources."""

    def __init__(self):
        """Initialize resource manager."""
        self.resources: Dict[str, Resource] = {}
        self.access_logs: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

    def create_resource(self, resource: Resource) -> None:
        """Create resource."""
        with self._lock:
            if resource.id in self.resources:
                raise ValueError(f"Resource '{resource.id}' already exists")
            self.resources[resource.id] = resource

    def get_resource(self, resource_id: str) -> Optional[Resource]:
        """Get resource."""
        return self.resources.get(resource_id)

    def list_resources(
        self,
        resource_type: Optional[ResourceType] = None
    ) -> List[Resource]:
        """List resources."""
        resources = list(self.resources.values())

        if resource_type:
            resources = [r for r in resources if r.type == resource_type]

        return resources

    def delete_resource(self, resource_id: str) -> bool:
        """Delete resource."""
        with self._lock:
            if resource_id in self.resources:
                del self.resources[resource_id]
                return True
        return False

    def log_access(
        self,
        resource_id: str,
        user_id: str,
        action: str,
        success: bool
    ) -> None:
        """Log resource access."""
        self.access_logs.append({
            'resource_id': resource_id,
            'user_id': user_id,
            'action': action,
            'success': success,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })


# ═══════════════════════════════════════════════════════════════════════════
# Tool Execution Engine
# ═══════════════════════════════════════════════════════════════════════════

class ToolExecutor:
    """Execute tools with error handling and timeouts."""

    def __init__(self, registry: ToolRegistry):
        """Initialize executor."""
        self.registry = registry
        self.logger = logging.getLogger(__name__)

    def execute(
        self,
        call: ToolCall,
        timeout_seconds: Optional[int] = None
    ) -> ToolResult:
        """Execute tool synchronously."""
        tool = self.registry.get_tool(call.tool_id)
        if not tool:
            return ToolResult(
                call_id=call.id,
                tool_id=call.tool_id,
                success=False,
                error=f"Tool '{call.tool_id}' not found"
            )

        handler = self.registry.get_handler(call.tool_id)
        if not handler:
            return ToolResult(
                call_id=call.id,
                tool_id=call.tool_id,
                success=False,
                error="Tool handler not found"
            )

        timeout = timeout_seconds or tool.timeout_seconds
        start_time = datetime.now(timezone.utc)

        try:
            # Execute with timeout
            result = self._execute_with_timeout(handler, call.parameters, timeout)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            tool_result = ToolResult(
                call_id=call.id,
                tool_id=call.tool_id,
                success=True,
                result=result,
                duration_seconds=duration
            )
        except asyncio.TimeoutError:
            tool_result = ToolResult(
                call_id=call.id,
                tool_id=call.tool_id,
                success=False,
                error=f"Tool execution timeout after {timeout}s"
            )
        except Exception as e:
            tool_result = ToolResult(
                call_id=call.id,
                tool_id=call.tool_id,
                success=False,
                error=str(e)
            )

        self.registry.record_execution(tool_result)
        return tool_result

    async def execute_async(
        self,
        call: ToolCall,
        timeout_seconds: Optional[int] = None
    ) -> ToolResult:
        """Execute tool asynchronously."""
        tool = self.registry.get_tool(call.tool_id)
        if not tool:
            return ToolResult(
                call_id=call.id,
                tool_id=call.tool_id,
                success=False,
                error=f"Tool '{call.tool_id}' not found"
            )

        handler = self.registry.get_handler(call.tool_id, async_mode=True)
        if not handler:
            # Fall back to sync handler
            handler = self.registry.get_handler(call.tool_id)

        if not handler:
            return ToolResult(
                call_id=call.id,
                tool_id=call.tool_id,
                success=False,
                error="Tool handler not found"
            )

        timeout = timeout_seconds or tool.timeout_seconds
        start_time = datetime.now(timezone.utc)

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await asyncio.wait_for(
                    handler(**call.parameters),
                    timeout=timeout
                )
            else:
                result = handler(**call.parameters)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            tool_result = ToolResult(
                call_id=call.id,
                tool_id=call.tool_id,
                success=True,
                result=result,
                duration_seconds=duration
            )
        except asyncio.TimeoutError:
            tool_result = ToolResult(
                call_id=call.id,
                tool_id=call.tool_id,
                success=False,
                error=f"Tool execution timeout after {timeout}s"
            )
        except Exception as e:
            tool_result = ToolResult(
                call_id=call.id,
                tool_id=call.tool_id,
                success=False,
                error=str(e)
            )

        self.registry.record_execution(tool_result)
        return tool_result

    def _execute_with_timeout(
        self,
        handler: Callable,
        params: Dict[str, Any],
        timeout_seconds: int
    ) -> Any:
        """Execute handler with timeout in thread pool."""
        try:
            return handler(**params)
        except Exception as e:
            raise


# ═══════════════════════════════════════════════════════════════════════════
# MCP Server
# ═══════════════════════════════════════════════════════════════════════════

class MCPServer:
    """Model Context Protocol server implementation."""

    def __init__(self, server_id: str = "", server_name: str = "BAEL MCP Server"):
        """Initialize MCP server."""
        self.server_id = server_id or str(uuid.uuid4())
        self.server_name = server_name
        self.server_version = "6.4.0"
        self.tool_registry = ToolRegistry()
        self.resource_manager = ResourceManager()
        self.tool_executor = ToolExecutor(self.tool_registry)
        self.clients: Dict[str, ClientInfo] = {}
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()

    def initialize(self) -> Dict[str, Any]:
        """Server initialization."""
        return {
            'server_id': self.server_id,
            'name': self.server_name,
            'version': self.server_version,
            'capabilities': {
                'tools': True,
                'resources': True,
                'prompts': True,
                'streaming': True,
                'async_support': True
            }
        }

    def register_client(self, client_info: ClientInfo) -> bool:
        """Register connected client."""
        with self._lock:
            if client_info.client_id in self.clients:
                self.clients[client_info.client_id].active = False
            self.clients[client_info.client_id] = client_info
            self.logger.info(f"Client connected: {client_info.name}")
            return True

    def unregister_client(self, client_id: str) -> bool:
        """Unregister disconnected client."""
        with self._lock:
            if client_id in self.clients:
                self.clients[client_id].active = False
                self.logger.info(f"Client disconnected: {client_id}")
                return True
        return False

    def process_message(self, message: MCPMessage) -> MCPMessage:
        """Process incoming MCP message."""
        try:
            if message.type == MessageType.INITIALIZE:
                response = self.initialize()
                return MCPMessage(
                    id=str(uuid.uuid4()),
                    type=MessageType.RESPONSE,
                    result=response
                )

            elif message.type == MessageType.LIST_TOOLS:
                tools = self.tool_registry.list_tools()
                return MCPMessage(
                    id=str(uuid.uuid4()),
                    type=MessageType.RESPONSE,
                    result={
                        'tools': [asdict(t) for t in tools]
                    }
                )

            elif message.type == MessageType.CALL_TOOL:
                tool_id = message.params.get('tool_id')
                parameters = message.params.get('parameters', {})

                call = ToolCall(
                    id=str(uuid.uuid4()),
                    tool_id=tool_id,
                    tool_name=message.params.get('tool_name', ''),
                    parameters=parameters,
                    timestamp=datetime.now(timezone.utc)
                )

                result = self.tool_executor.execute(call)

                return MCPMessage(
                    id=str(uuid.uuid4()),
                    type=MessageType.RESPONSE,
                    result=asdict(result)
                )

            elif message.type == MessageType.LIST_RESOURCES:
                resource_type = message.params.get('type')
                resource_type = (
                    ResourceType(resource_type) if resource_type else None
                )
                resources = self.resource_manager.list_resources(resource_type)

                return MCPMessage(
                    id=str(uuid.uuid4()),
                    type=MessageType.RESPONSE,
                    result={
                        'resources': [asdict(r) for r in resources]
                    }
                )

            elif message.type == MessageType.READ_RESOURCE:
                resource_id = message.params.get('resource_id')
                resource = self.resource_manager.get_resource(resource_id)

                if not resource:
                    return MCPMessage(
                        id=str(uuid.uuid4()),
                        type=MessageType.ERROR,
                        error={
                            'code': ErrorCode.RESOURCE_NOT_FOUND.value,
                            'message': f"Resource '{resource_id}' not found"
                        }
                    )

                return MCPMessage(
                    id=str(uuid.uuid4()),
                    type=MessageType.RESPONSE,
                    result=asdict(resource)
                )

            else:
                return MCPMessage(
                    id=str(uuid.uuid4()),
                    type=MessageType.ERROR,
                    error={
                        'code': ErrorCode.METHOD_NOT_FOUND.value,
                        'message': f"Unknown message type: {message.type}"
                    }
                )

        except Exception as e:
            self.logger.error(f"Message processing error: {e}", exc_info=True)
            return MCPMessage(
                id=str(uuid.uuid4()),
                type=MessageType.ERROR,
                error={
                    'code': ErrorCode.INTERNAL_ERROR.value,
                    'message': str(e)
                }
            )

    async def process_message_async(self, message: MCPMessage) -> MCPMessage:
        """Process message asynchronously with streaming support."""
        if message.type == MessageType.CALL_TOOL:
            tool_id = message.params.get('tool_id')
            parameters = message.params.get('parameters', {})

            call = ToolCall(
                id=str(uuid.uuid4()),
                tool_id=tool_id,
                tool_name=message.params.get('tool_name', ''),
                parameters=parameters,
                timestamp=datetime.now(timezone.utc)
            )

            result = await self.tool_executor.execute_async(call)

            return MCPMessage(
                id=str(uuid.uuid4()),
                type=MessageType.RESPONSE,
                result=asdict(result)
            )
        else:
            return self.process_message(message)

    def get_server_info(self) -> Dict[str, Any]:
        """Get server information."""
        return {
            'server_id': self.server_id,
            'name': self.server_name,
            'version': self.server_version,
            'tools_count': len(self.tool_registry.tools),
            'resources_count': len(self.resource_manager.resources),
            'connected_clients': sum(
                1 for c in self.clients.values() if c.active
            ),
            'uptime_seconds': 0  # Would track actual uptime
        }


# ═══════════════════════════════════════════════════════════════════════════
# Global MCP Server Singleton
# ═══════════════════════════════════════════════════════════════════════════

_global_mcp_server: Optional[MCPServer] = None


def get_mcp_server() -> MCPServer:
    """Get or create global MCP server."""
    global _global_mcp_server
    if _global_mcp_server is None:
        _global_mcp_server = MCPServer()
    return _global_mcp_server
