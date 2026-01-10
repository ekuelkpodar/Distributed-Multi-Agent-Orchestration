"""
Comprehensive Audit Trail Service
Provides detailed logging and audit capabilities for compliance and debugging.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any
from uuid import UUID, uuid4
import json

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
import structlog

from shared.database.connections import redis_manager

logger = structlog.get_logger()


class AuditEventType(str, Enum):
    # Agent events
    AGENT_CREATED = "agent.created"
    AGENT_UPDATED = "agent.updated"
    AGENT_DELETED = "agent.deleted"
    AGENT_STATUS_CHANGED = "agent.status_changed"
    AGENT_HEARTBEAT = "agent.heartbeat"
    AGENT_ERROR = "agent.error"

    # Task events
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    TASK_RETRIED = "task.retried"
    TASK_TIMEOUT = "task.timeout"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    SYSTEM_CONFIG_CHANGED = "system.config_changed"

    # Security events
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_FAILED = "auth.failed"
    ACCESS_DENIED = "access.denied"
    API_KEY_CREATED = "api_key.created"
    API_KEY_REVOKED = "api_key.revoked"

    # Resource events
    RESOURCE_CREATED = "resource.created"
    RESOURCE_UPDATED = "resource.updated"
    RESOURCE_DELETED = "resource.deleted"


class AuditEntry(BaseModel):
    """Single audit log entry."""
    id: str
    event_type: AuditEventType
    timestamp: datetime
    actor_id: Optional[str] = None
    actor_type: str = "system"  # system, user, agent, api
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: str
    details: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    trace_id: Optional[str] = None
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None


class AuditQuery(BaseModel):
    """Query parameters for audit log search."""
    event_types: Optional[List[AuditEventType]] = None
    actor_id: Optional[str] = None
    actor_type: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    success: Optional[bool] = None
    search_text: Optional[str] = None
    page: int = 1
    page_size: int = 50


class AuditSummary(BaseModel):
    """Summary of audit events."""
    total_events: int
    events_by_type: Dict[str, int]
    events_by_actor_type: Dict[str, int]
    success_rate: float
    time_range: Dict[str, datetime]
    top_actors: List[Dict[str, Any]]
    top_resources: List[Dict[str, Any]]


class AuditService:
    """
    Comprehensive Audit Trail Service for logging and querying audit events.
    Stores events in Redis with database backup for long-term retention.
    """

    def __init__(self, retention_days: int = 90, buffer_size: int = 100):
        self.retention_days = retention_days
        self.buffer_size = buffer_size
        self._buffer: List[AuditEntry] = []
        self._redis_prefix = "audit"

    async def log(
        self,
        event_type: AuditEventType,
        action: str,
        actor_id: Optional[str] = None,
        actor_type: str = "system",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> AuditEntry:
        """Log an audit event."""
        entry = AuditEntry(
            id=str(uuid4()),
            event_type=event_type,
            timestamp=datetime.utcnow(),
            actor_id=actor_id,
            actor_type=actor_type,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details or {},
            metadata=metadata or {},
            trace_id=trace_id,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
        )

        # Store in Redis
        await self._store_entry(entry)

        # Also log via structlog for immediate visibility
        log_method = logger.info if success else logger.error
        log_method(
            f"audit.{event_type.value}",
            action=action,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
            trace_id=trace_id,
        )

        return entry

    async def _store_entry(self, entry: AuditEntry):
        """Store audit entry in Redis."""
        try:
            redis = await redis_manager.get_client()
            if not redis:
                logger.warning("Redis not available for audit storage")
                return

            # Store by ID for direct lookup
            key = f"{self._redis_prefix}:entry:{entry.id}"
            await redis.setex(
                key,
                self.retention_days * 86400,
                entry.model_dump_json(),
            )

            # Store in sorted set by timestamp for range queries
            timeline_key = f"{self._redis_prefix}:timeline"
            await redis.zadd(
                timeline_key,
                {entry.id: entry.timestamp.timestamp()},
            )

            # Index by event type
            type_key = f"{self._redis_prefix}:type:{entry.event_type.value}"
            await redis.lpush(type_key, entry.id)
            await redis.ltrim(type_key, 0, 9999)  # Keep last 10000

            # Index by resource
            if entry.resource_type and entry.resource_id:
                resource_key = f"{self._redis_prefix}:resource:{entry.resource_type}:{entry.resource_id}"
                await redis.lpush(resource_key, entry.id)
                await redis.ltrim(resource_key, 0, 999)

            # Index by actor
            if entry.actor_id:
                actor_key = f"{self._redis_prefix}:actor:{entry.actor_id}"
                await redis.lpush(actor_key, entry.id)
                await redis.ltrim(actor_key, 0, 999)

        except Exception as e:
            logger.error(f"Failed to store audit entry: {e}")

    async def get_entry(self, entry_id: str) -> Optional[AuditEntry]:
        """Get a single audit entry by ID."""
        try:
            redis = await redis_manager.get_client()
            if not redis:
                return None

            key = f"{self._redis_prefix}:entry:{entry_id}"
            data = await redis.get(key)
            if data:
                return AuditEntry.model_validate_json(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get audit entry: {e}")
            return None

    async def query(self, query: AuditQuery) -> List[AuditEntry]:
        """Query audit entries with filters."""
        try:
            redis = await redis_manager.get_client()
            if not redis:
                return []

            # Determine which index to use
            entry_ids = set()

            if query.resource_type and query.resource_id:
                # Use resource index
                key = f"{self._redis_prefix}:resource:{query.resource_type}:{query.resource_id}"
                ids = await redis.lrange(key, 0, -1)
                entry_ids = set(id.decode() if isinstance(id, bytes) else id for id in ids)

            elif query.actor_id:
                # Use actor index
                key = f"{self._redis_prefix}:actor:{query.actor_id}"
                ids = await redis.lrange(key, 0, -1)
                entry_ids = set(id.decode() if isinstance(id, bytes) else id for id in ids)

            elif query.event_types and len(query.event_types) == 1:
                # Use type index
                key = f"{self._redis_prefix}:type:{query.event_types[0].value}"
                ids = await redis.lrange(key, 0, -1)
                entry_ids = set(id.decode() if isinstance(id, bytes) else id for id in ids)

            else:
                # Use timeline with time range
                timeline_key = f"{self._redis_prefix}:timeline"
                min_score = query.start_time.timestamp() if query.start_time else "-inf"
                max_score = query.end_time.timestamp() if query.end_time else "+inf"

                ids = await redis.zrangebyscore(
                    timeline_key,
                    min_score,
                    max_score,
                    start=0,
                    num=1000,
                )
                entry_ids = set(id.decode() if isinstance(id, bytes) else id for id in ids)

            # Fetch entries
            entries = []
            for entry_id in entry_ids:
                entry = await self.get_entry(entry_id)
                if entry:
                    entries.append(entry)

            # Apply filters
            filtered = []
            for entry in entries:
                # Event type filter
                if query.event_types and entry.event_type not in query.event_types:
                    continue

                # Actor type filter
                if query.actor_type and entry.actor_type != query.actor_type:
                    continue

                # Time range filter
                if query.start_time and entry.timestamp < query.start_time:
                    continue
                if query.end_time and entry.timestamp > query.end_time:
                    continue

                # Success filter
                if query.success is not None and entry.success != query.success:
                    continue

                # Text search in action and details
                if query.search_text:
                    search_lower = query.search_text.lower()
                    if (
                        search_lower not in entry.action.lower()
                        and search_lower not in json.dumps(entry.details).lower()
                    ):
                        continue

                filtered.append(entry)

            # Sort by timestamp descending
            filtered.sort(key=lambda x: x.timestamp, reverse=True)

            # Paginate
            start = (query.page - 1) * query.page_size
            end = start + query.page_size

            return filtered[start:end]

        except Exception as e:
            logger.error(f"Failed to query audit entries: {e}")
            return []

    async def get_summary(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> AuditSummary:
        """Get summary of audit events."""
        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=7)
        if not end_time:
            end_time = datetime.utcnow()

        query = AuditQuery(
            start_time=start_time,
            end_time=end_time,
            page_size=10000,
        )
        entries = await self.query(query)

        events_by_type: Dict[str, int] = {}
        events_by_actor_type: Dict[str, int] = {}
        actor_counts: Dict[str, int] = {}
        resource_counts: Dict[str, int] = {}
        success_count = 0

        for entry in entries:
            # Count by event type
            type_key = entry.event_type.value
            events_by_type[type_key] = events_by_type.get(type_key, 0) + 1

            # Count by actor type
            events_by_actor_type[entry.actor_type] = (
                events_by_actor_type.get(entry.actor_type, 0) + 1
            )

            # Count by actor
            if entry.actor_id:
                actor_counts[entry.actor_id] = actor_counts.get(entry.actor_id, 0) + 1

            # Count by resource
            if entry.resource_type and entry.resource_id:
                resource_key = f"{entry.resource_type}:{entry.resource_id}"
                resource_counts[resource_key] = resource_counts.get(resource_key, 0) + 1

            if entry.success:
                success_count += 1

        total_events = len(entries)
        success_rate = (success_count / total_events * 100) if total_events > 0 else 100.0

        # Get top actors
        top_actors = [
            {"actor_id": actor_id, "count": count}
            for actor_id, count in sorted(
                actor_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10]
        ]

        # Get top resources
        top_resources = [
            {
                "resource_type": key.split(":")[0],
                "resource_id": key.split(":")[1],
                "count": count,
            }
            for key, count in sorted(
                resource_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10]
        ]

        return AuditSummary(
            total_events=total_events,
            events_by_type=events_by_type,
            events_by_actor_type=events_by_actor_type,
            success_rate=success_rate,
            time_range={"start": start_time, "end": end_time},
            top_actors=top_actors,
            top_resources=top_resources,
        )

    async def get_resource_history(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """Get audit history for a specific resource."""
        query = AuditQuery(
            resource_type=resource_type,
            resource_id=resource_id,
            page_size=limit,
        )
        return await self.query(query)

    async def get_actor_activity(
        self,
        actor_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """Get all activity for a specific actor."""
        query = AuditQuery(
            actor_id=actor_id,
            start_time=start_time,
            end_time=end_time,
            page_size=limit,
        )
        return await self.query(query)

    async def get_failed_events(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """Get failed events in the specified time range."""
        query = AuditQuery(
            start_time=datetime.utcnow() - timedelta(hours=hours),
            success=False,
            page_size=limit,
        )
        return await self.query(query)

    async def get_security_events(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """Get security-related events."""
        security_types = [
            AuditEventType.AUTH_LOGIN,
            AuditEventType.AUTH_LOGOUT,
            AuditEventType.AUTH_FAILED,
            AuditEventType.ACCESS_DENIED,
            AuditEventType.API_KEY_CREATED,
            AuditEventType.API_KEY_REVOKED,
        ]
        query = AuditQuery(
            event_types=security_types,
            start_time=datetime.utcnow() - timedelta(hours=hours),
            page_size=limit,
        )
        return await self.query(query)

    # Convenience methods for common events

    async def log_agent_created(
        self,
        agent_id: UUID,
        agent_name: str,
        agent_type: str,
        actor_id: Optional[str] = None,
        **kwargs,
    ) -> AuditEntry:
        """Log agent creation event."""
        return await self.log(
            event_type=AuditEventType.AGENT_CREATED,
            action=f"Created agent '{agent_name}' of type '{agent_type}'",
            resource_type="agent",
            resource_id=str(agent_id),
            actor_id=actor_id,
            details={"agent_name": agent_name, "agent_type": agent_type},
            **kwargs,
        )

    async def log_task_created(
        self,
        task_id: UUID,
        description: str,
        priority: int,
        actor_id: Optional[str] = None,
        **kwargs,
    ) -> AuditEntry:
        """Log task creation event."""
        return await self.log(
            event_type=AuditEventType.TASK_CREATED,
            action=f"Created task with priority {priority}",
            resource_type="task",
            resource_id=str(task_id),
            actor_id=actor_id,
            details={"description": description[:200], "priority": priority},
            **kwargs,
        )

    async def log_task_completed(
        self,
        task_id: UUID,
        agent_id: UUID,
        duration_ms: float,
        **kwargs,
    ) -> AuditEntry:
        """Log task completion event."""
        return await self.log(
            event_type=AuditEventType.TASK_COMPLETED,
            action=f"Task completed by agent in {duration_ms:.0f}ms",
            resource_type="task",
            resource_id=str(task_id),
            actor_id=str(agent_id),
            actor_type="agent",
            details={"duration_ms": duration_ms},
            **kwargs,
        )

    async def log_task_failed(
        self,
        task_id: UUID,
        agent_id: Optional[UUID],
        error: str,
        **kwargs,
    ) -> AuditEntry:
        """Log task failure event."""
        return await self.log(
            event_type=AuditEventType.TASK_FAILED,
            action="Task failed",
            resource_type="task",
            resource_id=str(task_id),
            actor_id=str(agent_id) if agent_id else None,
            actor_type="agent" if agent_id else "system",
            success=False,
            error_message=error[:500],
            details={"error": error[:1000]},
            **kwargs,
        )

    async def log_auth_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_message: Optional[str] = None,
        **kwargs,
    ) -> AuditEntry:
        """Log authentication event."""
        action_map = {
            AuditEventType.AUTH_LOGIN: "User logged in" if success else "Login attempt failed",
            AuditEventType.AUTH_LOGOUT: "User logged out",
            AuditEventType.AUTH_FAILED: "Authentication failed",
        }
        return await self.log(
            event_type=event_type,
            action=action_map.get(event_type, str(event_type)),
            actor_id=user_id,
            actor_type="user",
            resource_type="session",
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
            **kwargs,
        )
