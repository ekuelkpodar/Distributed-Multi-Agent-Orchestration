"""Shared models package."""

from shared.models.schemas import (
    # Enums
    AgentType,
    AgentStatus,
    TaskStatus,
    MemoryType,
    EventType,
    MessageType,
    HealthStatus,
    # Agent models
    AgentCapabilities,
    AgentConfig,
    AgentBase,
    AgentCreate,
    AgentUpdate,
    Agent,
    AgentSpawnRequest,
    AgentSpawnResponse,
    # Task models
    TaskInput,
    TaskOutput,
    TaskMetadata,
    TaskBase,
    TaskCreate,
    TaskUpdate,
    Task,
    TaskSubmitRequest,
    TaskSubmitResponse,
    TaskStatusResponse,
    # Memory models
    MemoryBase,
    MemoryCreate,
    Memory,
    MemorySearchRequest,
    MemorySearchResult,
    # Event models
    EventBase,
    AgentLifecycleEvent,
    TaskEvent,
    AgentMessageEvent,
    SystemEvent,
    # Health models
    ComponentHealth,
    HealthCheckResponse,
    # API models
    APIResponse,
    PaginatedResponse,
)

__all__ = [
    # Enums
    "AgentType",
    "AgentStatus",
    "TaskStatus",
    "MemoryType",
    "EventType",
    "MessageType",
    "HealthStatus",
    # Agent models
    "AgentCapabilities",
    "AgentConfig",
    "AgentBase",
    "AgentCreate",
    "AgentUpdate",
    "Agent",
    "AgentSpawnRequest",
    "AgentSpawnResponse",
    # Task models
    "TaskInput",
    "TaskOutput",
    "TaskMetadata",
    "TaskBase",
    "TaskCreate",
    "TaskUpdate",
    "Task",
    "TaskSubmitRequest",
    "TaskSubmitResponse",
    "TaskStatusResponse",
    # Memory models
    "MemoryBase",
    "MemoryCreate",
    "Memory",
    "MemorySearchRequest",
    "MemorySearchResult",
    # Event models
    "EventBase",
    "AgentLifecycleEvent",
    "TaskEvent",
    "AgentMessageEvent",
    "SystemEvent",
    # Health models
    "ComponentHealth",
    "HealthCheckResponse",
    # API models
    "APIResponse",
    "PaginatedResponse",
]
