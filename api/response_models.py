"""
Enhanced API response models with comprehensive validation and documentation.
Provides consistent, well-documented API responses across all endpoints.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar('T')


class MetadataResponse(BaseModel):
    """Standard metadata for API responses."""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    version: str = Field("1.0.0", description="API version")
    request_id: Optional[str] = Field(None, description="Unique request identifier")


class PaginationInfo(BaseModel):
    """Pagination information for list responses."""
    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(10, ge=1, le=100, description="Items per page")
    total_items: int = Field(0, ge=0, description="Total number of items")
    total_pages: int = Field(0, ge=0, description="Total number of pages")
    has_next: bool = Field(False, description="Whether there is a next page")
    has_prev: bool = Field(False, description="Whether there is a previous page")


class SuccessResponse(BaseModel, Generic[T]):
    """Generic success response wrapper."""
    success: bool = Field(True, description="Request success indicator")
    data: T = Field(..., description="Response data")
    metadata: MetadataResponse = Field(default_factory=MetadataResponse, description="Response metadata")


class ListResponse(BaseModel, Generic[T]):
    """Generic list response wrapper."""
    success: bool = Field(True, description="Request success indicator")
    data: List[T] = Field(..., description="List of items")
    pagination: PaginationInfo = Field(..., description="Pagination information")
    metadata: MetadataResponse = Field(default_factory=MetadataResponse, description="Response metadata")


class ChatMessage(BaseModel):
    """Chat message model."""
    id: str = Field(..., description="Message ID")
    content: str = Field(..., description="Message content")
    role: str = Field(..., description="Message role (user/assistant)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional message metadata")


class PersonaInfo(BaseModel):
    """Persona information model."""
    id: str = Field(..., description="Persona ID")
    name: str = Field(..., description="Persona name")
    role: str = Field(..., description="Persona role")
    description: str = Field(..., description="Persona description")
    icon: Optional[str] = Field(None, description="Persona icon/emoji")
    capabilities: List[str] = Field(default_factory=list, description="Persona capabilities")


class ToolInfo(BaseModel):
    """Tool information model."""
    id: str = Field(..., description="Tool ID")
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    category: str = Field(..., description="Tool category")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Tool parameters schema")
    status: str = Field("available", description="Tool status (available/deprecated/experimental)")


class MemoryEntry(BaseModel):
    """Memory entry model."""
    id: str = Field(..., description="Memory entry ID")
    type: str = Field(..., description="Memory type (episodic/semantic/procedural)")
    content: str = Field(..., description="Memory content")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Entry timestamp")
    relevance: Optional[float] = Field(None, ge=0, le=1, description="Relevance score")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class HealthStatus(BaseModel):
    """Health status model."""
    status: str = Field("healthy", description="System health status")
    version: str = Field(..., description="System version")
    uptime_seconds: float = Field(..., ge=0, description="System uptime in seconds")
    session_id: str = Field(..., description="Current session ID")
    components: Dict[str, str] = Field(default_factory=dict, description="Component statuses")


class StreamResponse(BaseModel):
    """Streaming response chunk."""
    type: str = Field(..., description="Chunk type (start/data/end/error)")
    data: Optional[str] = Field(None, description="Chunk data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Chunk metadata")
    error: Optional[str] = Field(None, description="Error message if applicable")


class ExecutionResult(BaseModel):
    """Code/tool execution result model."""
    success: bool = Field(..., description="Execution success indicator")
    output: Optional[str] = Field(None, description="Execution output")
    error: Optional[str] = Field(None, description="Error message if failed")
    duration_seconds: Optional[float] = Field(None, ge=0, description="Execution duration")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ReasoningTrace(BaseModel):
    """Reasoning trace step model."""
    step: int = Field(..., ge=1, description="Step number")
    type: str = Field(..., description="Step type (analysis/decision/action/conclusion)")
    content: str = Field(..., description="Step content")
    reasoning: Optional[str] = Field(None, description="Step reasoning")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence score")


class ThinkingResponse(BaseModel):
    """Enhanced thinking response model."""
    success: bool = Field(True, description="Request success indicator")
    response: str = Field(..., description="Generated response")
    session_id: str = Field(..., description="Session ID")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Response confidence")
    reasoning_trace: Optional[List[ReasoningTrace]] = Field(None, description="Reasoning trace")
    execution_time_ms: Optional[float] = Field(None, ge=0, description="Execution time in milliseconds")
    metadata: MetadataResponse = Field(default_factory=MetadataResponse, description="Response metadata")
