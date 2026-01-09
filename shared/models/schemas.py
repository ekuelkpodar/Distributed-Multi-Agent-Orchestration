"""
Shared Pydantic models and schemas for the Multi-Agent Orchestration Platform.
These models are used across all services for consistent data validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


# Enums
class AgentType(str, Enum):
    ORCHESTRATOR = "orchestrator"
    WORKER = "worker"
    SPECIALIST = "specialist"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    COORDINATOR = "coordinator"


class AgentStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    FAILED = "failed"
    STARTING = "starting"
    STOPPING = "stopping"


class TaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class MemoryType(str, Enum):
    CONVERSATION = "conversation"
    KNOWLEDGE = "knowledge"
    CONTEXT = "context"
    SHORT_TERM = "short_term"
    MID_TERM = "mid_term"
    LONG_TERM = "long_term"


class EventType(str, Enum):
    # Agent lifecycle events
    AGENT_SPAWNED = "agent.spawned"
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_FAILED = "agent.failed"
    AGENT_HEARTBEAT = "agent.heartbeat"

    # Task events
    TASK_CREATED = "task.created"
    TASK_ASSIGNED = "task.assigned"
    TASK_STARTED = "task.started"
    TASK_PROGRESS = "task.progress"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"

    # Agent communication
    AGENT_MESSAGE = "agent.message"
    AGENT_REQUEST = "agent.request"
    AGENT_RESPONSE = "agent.response"
    AGENT_BROADCAST = "agent.broadcast"

    # State events
    STATE_UPDATED = "state.updated"
    STATE_SYNCED = "state.synced"

    # System events
    SYSTEM_ALERT = "system.alert"
    SYSTEM_HEALTH = "system.health"


class MessageType(str, Enum):
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"


# Base Models
class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True
    )


# Agent Models
class AgentCapabilities(BaseSchema):
    """Agent capabilities configuration."""
    skills: list[str] = Field(default_factory=list)
    max_concurrent_tasks: int = Field(default=5, ge=1, le=100)
    supported_task_types: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)


class AgentConfig(BaseSchema):
    """Agent-specific configuration."""
    model: str = Field(default="claude-sonnet-4-20250514")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1)
    timeout_seconds: int = Field(default=300)
    retry_attempts: int = Field(default=3)
    memory_enabled: bool = Field(default=True)


class AgentBase(BaseSchema):
    """Base agent schema."""
    name: str = Field(..., min_length=1, max_length=255)
    type: AgentType
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    config: AgentConfig = Field(default_factory=AgentConfig)


class AgentCreate(AgentBase):
    """Schema for creating a new agent."""
    parent_id: Optional[UUID] = None


class AgentUpdate(BaseSchema):
    """Schema for updating an agent."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[AgentStatus] = None
    capabilities: Optional[AgentCapabilities] = None
    config: Optional[AgentConfig] = None


class Agent(AgentBase):
    """Full agent schema with all fields."""
    id: UUID = Field(default_factory=uuid4)
    status: AgentStatus = Field(default=AgentStatus.IDLE)
    parent_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_heartbeat: Optional[datetime] = None


class AgentSpawnRequest(BaseSchema):
    """Request to spawn a new agent."""
    agent_type: AgentType
    name: Optional[str] = None
    capabilities: Optional[list[str]] = None
    config: Optional[dict[str, Any]] = None
    parent_id: Optional[UUID] = None


class AgentSpawnResponse(BaseSchema):
    """Response after spawning an agent."""
    agent_id: UUID
    status: AgentStatus
    message: str


# Task Models
class TaskInput(BaseSchema):
    """Task input data."""
    query: Optional[str] = None
    context: Optional[dict[str, Any]] = None
    parameters: Optional[dict[str, Any]] = None


class TaskOutput(BaseSchema):
    """Task output data."""
    result: Optional[Any] = None
    artifacts: Optional[list[dict[str, Any]]] = None
    metadata: Optional[dict[str, Any]] = None


class TaskMetadata(BaseSchema):
    """Task metadata."""
    source: Optional[str] = None
    trace_id: Optional[str] = None
    retry_count: int = Field(default=0)
    estimated_duration_seconds: Optional[int] = None


class TaskBase(BaseSchema):
    """Base task schema."""
    description: str = Field(..., min_length=1)
    priority: int = Field(default=0, ge=-10, le=10)
    input_data: Optional[TaskInput] = None
    metadata: Optional[TaskMetadata] = None


class TaskCreate(TaskBase):
    """Schema for creating a new task."""
    agent_id: Optional[UUID] = None
    parent_task_id: Optional[UUID] = None
    deadline: Optional[datetime] = None


class TaskUpdate(BaseSchema):
    """Schema for updating a task."""
    status: Optional[TaskStatus] = None
    output_data: Optional[TaskOutput] = None
    metadata: Optional[TaskMetadata] = None


class Task(TaskBase):
    """Full task schema with all fields."""
    id: UUID = Field(default_factory=uuid4)
    agent_id: Optional[UUID] = None
    parent_task_id: Optional[UUID] = None
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    output_data: Optional[TaskOutput] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskSubmitRequest(BaseSchema):
    """Request to submit a new task."""
    description: str = Field(..., min_length=1)
    priority: int = Field(default=0, ge=-10, le=10)
    deadline: Optional[datetime] = None
    context: Optional[dict[str, Any]] = None
    agent_type: Optional[AgentType] = None
    agent_id: Optional[UUID] = None


class TaskSubmitResponse(BaseSchema):
    """Response after submitting a task."""
    task_id: UUID
    status: TaskStatus
    assigned_agent: Optional[UUID] = None
    message: str


class TaskStatusResponse(BaseSchema):
    """Task status response."""
    task_id: UUID
    status: TaskStatus
    assigned_agent: Optional[UUID] = None
    progress: Optional[float] = Field(None, ge=0.0, le=1.0)
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    result: Optional[Any] = None


# Memory Models
class MemoryBase(BaseSchema):
    """Base memory schema."""
    memory_type: MemoryType
    content: str
    metadata: Optional[dict[str, Any]] = None


class MemoryCreate(MemoryBase):
    """Schema for creating a memory entry."""
    agent_id: UUID
    embedding: Optional[list[float]] = None


class Memory(MemoryBase):
    """Full memory schema."""
    id: UUID = Field(default_factory=uuid4)
    agent_id: UUID
    embedding: Optional[list[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MemorySearchRequest(BaseSchema):
    """Request to search memories."""
    query: str
    agent_id: Optional[UUID] = None
    memory_type: Optional[MemoryType] = None
    limit: int = Field(default=10, ge=1, le=100)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class MemorySearchResult(BaseSchema):
    """Memory search result."""
    memory: Memory
    similarity_score: float


# Event Models
class EventBase(BaseSchema):
    """Base event schema."""
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trace_id: Optional[str] = None


class AgentLifecycleEvent(EventBase):
    """Agent lifecycle event."""
    agent_id: UUID
    status: AgentStatus
    details: Optional[dict[str, Any]] = None


class TaskEvent(EventBase):
    """Task-related event."""
    task_id: UUID
    agent_id: Optional[UUID] = None
    task_data: Optional[dict[str, Any]] = None
    progress: Optional[float] = None
    result: Optional[Any] = None


class AgentMessageEvent(EventBase):
    """Agent communication event."""
    event_id: UUID = Field(default_factory=uuid4)
    from_agent_id: UUID
    to_agent_id: Optional[UUID] = None  # None for broadcast
    message_type: MessageType
    content: dict[str, Any]


class SystemEvent(EventBase):
    """System-wide event."""
    service: str
    severity: str = Field(default="info")
    message: str
    details: Optional[dict[str, Any]] = None


# Health Check Models
class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseSchema):
    """Health status of a component."""
    name: str
    status: HealthStatus
    latency_ms: Optional[float] = None
    message: Optional[str] = None


class HealthCheckResponse(BaseSchema):
    """Health check response."""
    status: HealthStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str
    components: list[ComponentHealth] = Field(default_factory=list)


# API Response Models
class APIResponse(BaseSchema):
    """Standard API response wrapper."""
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[list[str]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseSchema):
    """Paginated response wrapper."""
    items: list[Any]
    total: int
    page: int
    page_size: int
    pages: int
