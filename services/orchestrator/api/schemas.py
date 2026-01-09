"""
API-specific schemas for the Orchestrator Service.
Extends the shared schemas with API-specific models.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from shared.models.schemas import (
    AgentType,
    AgentStatus,
    TaskStatus,
    MemoryType,
    AgentCapabilities,
    AgentConfig,
)


# Request Models
class SpawnAgentRequest(BaseModel):
    """Request to spawn a new agent."""
    agent_type: AgentType
    name: Optional[str] = None
    capabilities: Optional[list[str]] = None
    config: Optional[dict[str, Any]] = None
    parent_id: Optional[UUID] = None


class SubmitTaskRequest(BaseModel):
    """Request to submit a new task."""
    description: str = Field(..., min_length=1, max_length=10000)
    priority: int = Field(default=0, ge=-10, le=10)
    deadline: Optional[datetime] = None
    context: Optional[dict[str, Any]] = None
    agent_type: Optional[AgentType] = None
    agent_id: Optional[UUID] = None


class UpdateTaskRequest(BaseModel):
    """Request to update task status or progress."""
    status: Optional[TaskStatus] = None
    progress: Optional[float] = Field(None, ge=0.0, le=1.0)
    result: Optional[Any] = None
    error: Optional[str] = None


class AddDependencyRequest(BaseModel):
    """Request to add task dependency."""
    depends_on_task_id: UUID


class CreateMemoryRequest(BaseModel):
    """Request to create a memory entry."""
    agent_id: UUID
    memory_type: MemoryType
    content: str = Field(..., min_length=1)
    metadata: Optional[dict[str, Any]] = None


class SearchMemoryRequest(BaseModel):
    """Request to search memories."""
    query: str = Field(..., min_length=1)
    agent_id: Optional[UUID] = None
    memory_type: Optional[MemoryType] = None
    limit: int = Field(default=10, ge=1, le=100)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class SendMessageRequest(BaseModel):
    """Request to send inter-agent message."""
    from_agent_id: UUID
    to_agent_id: Optional[UUID] = None  # None for broadcast
    content: dict[str, Any]
    message_type: str = "request"


# Response Models
class AgentResponse(BaseModel):
    """Agent details response."""
    id: UUID
    name: str
    type: AgentType
    status: AgentStatus
    capabilities: AgentCapabilities
    config: AgentConfig
    parent_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    last_heartbeat: Optional[datetime]


class AgentListResponse(BaseModel):
    """List of agents response."""
    agents: list[AgentResponse]
    total: int
    page: int
    page_size: int


class SpawnAgentResponse(BaseModel):
    """Response after spawning agent."""
    agent_id: UUID
    name: str
    status: AgentStatus
    message: str


class TaskResponse(BaseModel):
    """Task details response."""
    id: UUID
    description: str
    status: TaskStatus
    priority: int
    agent_id: Optional[UUID]
    parent_task_id: Optional[UUID]
    input_data: Optional[dict[str, Any]]
    output_data: Optional[dict[str, Any]]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class TaskListResponse(BaseModel):
    """List of tasks response."""
    tasks: list[TaskResponse]
    total: int
    page: int
    page_size: int


class SubmitTaskResponse(BaseModel):
    """Response after submitting task."""
    task_id: UUID
    status: TaskStatus
    assigned_agent: Optional[UUID]
    message: str


class TaskStatusResponse(BaseModel):
    """Task status response."""
    task_id: UUID
    status: TaskStatus
    assigned_agent: Optional[UUID]
    progress: Optional[float]
    started_at: Optional[datetime]
    estimated_completion: Optional[datetime]
    result: Optional[Any]


class MemoryResponse(BaseModel):
    """Memory entry response."""
    id: UUID
    agent_id: UUID
    memory_type: MemoryType
    content: str
    metadata: Optional[dict[str, Any]]
    created_at: datetime


class MemorySearchResponse(BaseModel):
    """Memory search results response."""
    results: list[dict[str, Any]]
    total: int
    query: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    version: str
    components: dict[str, dict[str, Any]]


class MetricsResponse(BaseModel):
    """Metrics summary response."""
    active_agents: int
    pending_tasks: int
    completed_tasks_24h: int
    failed_tasks_24h: int
    average_task_duration: float


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# WebSocket Event Models
class WebSocketEvent(BaseModel):
    """WebSocket event message."""
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: dict[str, Any]


class AgentEvent(WebSocketEvent):
    """Agent-related WebSocket event."""
    agent_id: UUID
    status: Optional[AgentStatus] = None


class TaskEvent(WebSocketEvent):
    """Task-related WebSocket event."""
    task_id: UUID
    agent_id: Optional[UUID] = None
    progress: Optional[float] = None
    result: Optional[Any] = None
