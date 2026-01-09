"""
Kafka event producers for the Multi-Agent Orchestration Platform.
Provides async event publishing with reliability guarantees.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError
import structlog

from shared.models.schemas import (
    EventType,
    AgentStatus,
    TaskStatus,
    MessageType,
)

logger = structlog.get_logger()


class KafkaTopics:
    """Kafka topic definitions."""
    AGENT_LIFECYCLE = "agent.lifecycle"
    AGENT_TASKS = "agent.tasks"
    AGENT_COMMUNICATION = "agent.communication"
    AGENT_STATE = "agent.state"
    SYSTEM_EVENTS = "system.events"
    DEAD_LETTER = "dead.letter"

    @classmethod
    def all_topics(cls) -> list[str]:
        """Return all topic names."""
        return [
            cls.AGENT_LIFECYCLE,
            cls.AGENT_TASKS,
            cls.AGENT_COMMUNICATION,
            cls.AGENT_STATE,
            cls.SYSTEM_EVENTS,
            cls.DEAD_LETTER,
        ]


class EventSerializer:
    """Serialize events to JSON bytes for Kafka."""

    @staticmethod
    def serialize(event: dict) -> bytes:
        """Serialize event dict to JSON bytes."""
        def json_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, UUID):
                return str(obj)
            if hasattr(obj, "value"):  # Enum
                return obj.value
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        return json.dumps(event, default=json_serializer).encode("utf-8")

    @staticmethod
    def deserialize(data: bytes) -> dict:
        """Deserialize JSON bytes to event dict."""
        return json.loads(data.decode("utf-8"))


class EventProducer:
    """
    Async Kafka producer for publishing events.
    Provides reliable event delivery with automatic retries.
    """

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        client_id: str = "agent-orchestrator",
        acks: str = "all",
        retries: int = 3,
        compression_type: str = "gzip",
        enable_idempotence: bool = True,
    ):
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )
        self.client_id = client_id
        self.acks = acks
        self.retries = retries
        self.compression_type = compression_type
        self.enable_idempotence = enable_idempotence
        self._producer: Optional[AIOKafkaProducer] = None
        self._started = False

    async def start(self) -> None:
        """Start the Kafka producer."""
        if self._started:
            return

        logger.info(
            "Starting Kafka producer",
            bootstrap_servers=self.bootstrap_servers,
            client_id=self.client_id
        )

        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            client_id=self.client_id,
            acks=self.acks,
            enable_idempotence=self.enable_idempotence,
            compression_type=self.compression_type,
            value_serializer=EventSerializer.serialize,
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )

        await self._producer.start()
        self._started = True
        logger.info("Kafka producer started successfully")

    async def stop(self) -> None:
        """Stop the Kafka producer gracefully."""
        if self._producer and self._started:
            logger.info("Stopping Kafka producer")
            await self._producer.stop()
            self._started = False
            logger.info("Kafka producer stopped")

    async def _ensure_started(self) -> None:
        """Ensure producer is started before sending."""
        if not self._started:
            await self.start()

    async def send(
        self,
        topic: str,
        event: dict,
        key: Optional[str] = None,
        partition: Optional[int] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> bool:
        """
        Send an event to a Kafka topic.

        Args:
            topic: Target topic name
            event: Event data dict
            key: Optional message key for partitioning
            partition: Optional specific partition
            headers: Optional message headers

        Returns:
            True if successful, False otherwise
        """
        await self._ensure_started()

        try:
            kafka_headers = None
            if headers:
                kafka_headers = [
                    (k, v.encode("utf-8")) for k, v in headers.items()
                ]

            result = await self._producer.send_and_wait(
                topic=topic,
                value=event,
                key=key,
                partition=partition,
                headers=kafka_headers,
            )

            logger.debug(
                "Event sent successfully",
                topic=topic,
                partition=result.partition,
                offset=result.offset,
                event_type=event.get("event_type"),
            )
            return True

        except KafkaError as e:
            logger.error(
                "Failed to send event",
                topic=topic,
                error=str(e),
                event_type=event.get("event_type"),
            )
            return False

    # Convenience methods for specific event types

    async def publish_agent_spawned(
        self,
        agent_id: UUID,
        agent_type: str,
        agent_name: str,
        trace_id: Optional[str] = None,
    ) -> bool:
        """Publish agent spawned event."""
        event = {
            "event_id": str(uuid4()),
            "event_type": EventType.AGENT_SPAWNED.value,
            "timestamp": datetime.utcnow(),
            "agent_id": agent_id,
            "agent_type": agent_type,
            "agent_name": agent_name,
            "status": AgentStatus.STARTING.value,
            "trace_id": trace_id or str(uuid4()),
        }
        return await self.send(
            KafkaTopics.AGENT_LIFECYCLE,
            event,
            key=str(agent_id),
        )

    async def publish_agent_started(
        self,
        agent_id: UUID,
        trace_id: Optional[str] = None,
    ) -> bool:
        """Publish agent started event."""
        event = {
            "event_id": str(uuid4()),
            "event_type": EventType.AGENT_STARTED.value,
            "timestamp": datetime.utcnow(),
            "agent_id": agent_id,
            "status": AgentStatus.IDLE.value,
            "trace_id": trace_id or str(uuid4()),
        }
        return await self.send(
            KafkaTopics.AGENT_LIFECYCLE,
            event,
            key=str(agent_id),
        )

    async def publish_agent_stopped(
        self,
        agent_id: UUID,
        reason: str = "normal",
        trace_id: Optional[str] = None,
    ) -> bool:
        """Publish agent stopped event."""
        event = {
            "event_id": str(uuid4()),
            "event_type": EventType.AGENT_STOPPED.value,
            "timestamp": datetime.utcnow(),
            "agent_id": agent_id,
            "status": AgentStatus.OFFLINE.value,
            "reason": reason,
            "trace_id": trace_id or str(uuid4()),
        }
        return await self.send(
            KafkaTopics.AGENT_LIFECYCLE,
            event,
            key=str(agent_id),
        )

    async def publish_agent_heartbeat(
        self,
        agent_id: UUID,
        status: AgentStatus,
        metrics: Optional[dict] = None,
    ) -> bool:
        """Publish agent heartbeat event."""
        event = {
            "event_id": str(uuid4()),
            "event_type": EventType.AGENT_HEARTBEAT.value,
            "timestamp": datetime.utcnow(),
            "agent_id": agent_id,
            "status": status.value if hasattr(status, "value") else status,
            "metrics": metrics or {},
        }
        return await self.send(
            KafkaTopics.AGENT_LIFECYCLE,
            event,
            key=str(agent_id),
        )

    async def publish_task_assigned(
        self,
        task_id: UUID,
        agent_id: UUID,
        description: str,
        priority: int = 0,
        deadline: Optional[datetime] = None,
        input_data: Optional[dict] = None,
        trace_id: Optional[str] = None,
    ) -> bool:
        """Publish task assigned event."""
        event = {
            "event_id": str(uuid4()),
            "event_type": EventType.TASK_ASSIGNED.value,
            "timestamp": datetime.utcnow(),
            "task_id": task_id,
            "agent_id": agent_id,
            "task_data": {
                "description": description,
                "priority": priority,
                "deadline": deadline,
                "input_data": input_data or {},
            },
            "trace_id": trace_id or str(uuid4()),
        }
        return await self.send(
            KafkaTopics.AGENT_TASKS,
            event,
            key=str(agent_id),
        )

    async def publish_task_started(
        self,
        task_id: UUID,
        agent_id: UUID,
        trace_id: Optional[str] = None,
    ) -> bool:
        """Publish task started event."""
        event = {
            "event_id": str(uuid4()),
            "event_type": EventType.TASK_STARTED.value,
            "timestamp": datetime.utcnow(),
            "task_id": task_id,
            "agent_id": agent_id,
            "status": TaskStatus.IN_PROGRESS.value,
            "trace_id": trace_id or str(uuid4()),
        }
        return await self.send(
            KafkaTopics.AGENT_TASKS,
            event,
            key=str(task_id),
        )

    async def publish_task_progress(
        self,
        task_id: UUID,
        agent_id: UUID,
        progress: float,
        message: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> bool:
        """Publish task progress event."""
        event = {
            "event_id": str(uuid4()),
            "event_type": EventType.TASK_PROGRESS.value,
            "timestamp": datetime.utcnow(),
            "task_id": task_id,
            "agent_id": agent_id,
            "progress": progress,
            "message": message,
            "trace_id": trace_id or str(uuid4()),
        }
        return await self.send(
            KafkaTopics.AGENT_TASKS,
            event,
            key=str(task_id),
        )

    async def publish_task_completed(
        self,
        task_id: UUID,
        agent_id: UUID,
        result: Any = None,
        trace_id: Optional[str] = None,
    ) -> bool:
        """Publish task completed event."""
        event = {
            "event_id": str(uuid4()),
            "event_type": EventType.TASK_COMPLETED.value,
            "timestamp": datetime.utcnow(),
            "task_id": task_id,
            "agent_id": agent_id,
            "status": TaskStatus.COMPLETED.value,
            "result": result,
            "trace_id": trace_id or str(uuid4()),
        }
        return await self.send(
            KafkaTopics.AGENT_TASKS,
            event,
            key=str(task_id),
        )

    async def publish_task_failed(
        self,
        task_id: UUID,
        agent_id: UUID,
        error: str,
        retry_count: int = 0,
        trace_id: Optional[str] = None,
    ) -> bool:
        """Publish task failed event."""
        event = {
            "event_id": str(uuid4()),
            "event_type": EventType.TASK_FAILED.value,
            "timestamp": datetime.utcnow(),
            "task_id": task_id,
            "agent_id": agent_id,
            "status": TaskStatus.FAILED.value,
            "error": error,
            "retry_count": retry_count,
            "trace_id": trace_id or str(uuid4()),
        }
        return await self.send(
            KafkaTopics.AGENT_TASKS,
            event,
            key=str(task_id),
        )

    async def publish_agent_message(
        self,
        from_agent_id: UUID,
        to_agent_id: Optional[UUID],
        message_type: MessageType,
        content: dict,
        trace_id: Optional[str] = None,
    ) -> bool:
        """Publish inter-agent message event."""
        event = {
            "event_id": str(uuid4()),
            "event_type": EventType.AGENT_MESSAGE.value,
            "timestamp": datetime.utcnow(),
            "from_agent_id": from_agent_id,
            "to_agent_id": to_agent_id,  # None for broadcast
            "message_type": message_type.value if hasattr(message_type, "value") else message_type,
            "content": content,
            "trace_id": trace_id or str(uuid4()),
        }

        key = str(to_agent_id) if to_agent_id else str(from_agent_id)
        return await self.send(
            KafkaTopics.AGENT_COMMUNICATION,
            event,
            key=key,
        )

    async def publish_state_update(
        self,
        agent_id: UUID,
        state_key: str,
        state_value: Any,
        trace_id: Optional[str] = None,
    ) -> bool:
        """Publish state update event."""
        event = {
            "event_id": str(uuid4()),
            "event_type": EventType.STATE_UPDATED.value,
            "timestamp": datetime.utcnow(),
            "agent_id": agent_id,
            "state_key": state_key,
            "state_value": state_value,
            "trace_id": trace_id or str(uuid4()),
        }
        return await self.send(
            KafkaTopics.AGENT_STATE,
            event,
            key=str(agent_id),
        )

    async def publish_system_event(
        self,
        service: str,
        severity: str,
        message: str,
        details: Optional[dict] = None,
        trace_id: Optional[str] = None,
    ) -> bool:
        """Publish system-wide event."""
        event = {
            "event_id": str(uuid4()),
            "event_type": EventType.SYSTEM_ALERT.value,
            "timestamp": datetime.utcnow(),
            "service": service,
            "severity": severity,
            "message": message,
            "details": details or {},
            "trace_id": trace_id or str(uuid4()),
        }
        return await self.send(
            KafkaTopics.SYSTEM_EVENTS,
            event,
            key=service,
        )


# Global producer instance
event_producer = EventProducer()


async def init_producer() -> None:
    """Initialize the global event producer."""
    await event_producer.start()


async def close_producer() -> None:
    """Close the global event producer."""
    await event_producer.stop()
