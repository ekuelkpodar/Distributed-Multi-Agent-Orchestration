"""
SQLAlchemy ORM models for the Multi-Agent Orchestration Platform.
These models map to the PostgreSQL database tables.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    CheckConstraint,
    UniqueConstraint,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from shared.database.connections import Base
from shared.models.schemas import AgentType, AgentStatus, TaskStatus, MemoryType


class Agent(Base):
    """Agent database model."""
    __tablename__ = "agents"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="idle"
    )
    capabilities: Mapped[dict] = mapped_column(JSONB, default=dict)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    parent_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    parent = relationship("Agent", remote_side=[id], back_populates="children")
    children = relationship("Agent", back_populates="parent")
    tasks = relationship("Task", back_populates="agent")
    memories = relationship("AgentMemory", back_populates="agent", cascade="all, delete-orphan")
    events = relationship("AgentEvent", back_populates="agent", cascade="all, delete-orphan")
    pool_memberships = relationship("AgentPoolMembership", back_populates="agent", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("name <> ''", name="agents_name_not_empty"),
        Index("idx_agents_status", "status"),
        Index("idx_agents_type", "type"),
        Index("idx_agents_parent", "parent_id"),
        Index("idx_agents_last_heartbeat", "last_heartbeat"),
    )


class Task(Base):
    """Task database model."""
    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    agent_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True
    )
    parent_task_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending"
    )
    priority: Mapped[int] = mapped_column(Integer, default=0)
    input_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    output_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    agent = relationship("Agent", back_populates="tasks")
    parent_task = relationship("Task", remote_side=[id], back_populates="subtasks")
    subtasks = relationship("Task", back_populates="parent_task")
    events = relationship("AgentEvent", back_populates="task")
    dependencies = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.task_id",
        back_populates="task",
        cascade="all, delete-orphan"
    )
    dependents = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.depends_on_task_id",
        back_populates="depends_on_task",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("description <> ''", name="tasks_description_not_empty"),
        CheckConstraint("priority >= -10 AND priority <= 10", name="tasks_priority_range"),
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_agent", "agent_id"),
        Index("idx_tasks_parent", "parent_task_id"),
        Index("idx_tasks_priority", priority.desc()),
        Index("idx_tasks_created", "created_at"),
    )


class AgentMemory(Base):
    """Agent memory database model with vector embeddings."""
    __tablename__ = "agent_memory"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    agent_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False
    )
    memory_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(1536), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    agent = relationship("Agent", back_populates="memories")

    __table_args__ = (
        CheckConstraint("content <> ''", name="memory_content_not_empty"),
        Index("idx_agent_memory_agent", "agent_id"),
        Index("idx_agent_memory_type", "memory_type"),
    )


class AgentEvent(Base):
    """Agent event database model for audit trail."""
    __tablename__ = "agent_events"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=True
    )
    task_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True
    )
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    trace_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )

    # Relationships
    agent = relationship("Agent", back_populates="events")
    task = relationship("Task", back_populates="events")

    __table_args__ = (
        Index("idx_agent_events_type", "event_type"),
        Index("idx_agent_events_agent", "agent_id"),
        Index("idx_agent_events_task", "task_id"),
        Index("idx_agent_events_trace", "trace_id"),
        Index("idx_agent_events_created", "created_at"),
    )


class TaskDependency(Base):
    """Task dependency database model for DAG-based execution."""
    __tablename__ = "task_dependencies"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    task_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False
    )
    depends_on_task_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )

    # Relationships
    task = relationship("Task", foreign_keys=[task_id], back_populates="dependencies")
    depends_on_task = relationship("Task", foreign_keys=[depends_on_task_id], back_populates="dependents")

    __table_args__ = (
        UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependency"),
        CheckConstraint("task_id <> depends_on_task_id", name="no_self_dependency"),
        Index("idx_task_deps_task", "task_id"),
        Index("idx_task_deps_depends", "depends_on_task_id"),
    )


class AgentPool(Base):
    """Agent pool database model for grouping and load balancing."""
    __tablename__ = "agent_pools"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agent_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    min_agents: Mapped[int] = mapped_column(Integer, default=1)
    max_agents: Mapped[int] = mapped_column(Integer, default=10)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    memberships = relationship("AgentPoolMembership", back_populates="pool", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("min_agents >= 0", name="min_agents_non_negative"),
        CheckConstraint("max_agents >= 1", name="max_agents_positive"),
    )


class AgentPoolMembership(Base):
    """Agent pool membership database model."""
    __tablename__ = "agent_pool_membership"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    agent_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False
    )
    pool_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_pools.id", ondelete="CASCADE"),
        nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )

    # Relationships
    agent = relationship("Agent", back_populates="pool_memberships")
    pool = relationship("AgentPool", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("agent_id", "pool_id", name="uq_agent_pool_membership"),
    )
