"""
Kafka event consumers for the Multi-Agent Orchestration Platform.
Provides async event consumption with at-least-once delivery guarantees.
"""

import asyncio
import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Callable, Optional, Any
from uuid import UUID

from aiokafka import AIOKafkaConsumer, TopicPartition
from aiokafka.errors import KafkaError
import structlog

from shared.events.producers import KafkaTopics, EventSerializer

logger = structlog.get_logger()


class EventHandler(ABC):
    """Abstract base class for event handlers."""

    @abstractmethod
    async def handle(self, event: dict) -> None:
        """Handle an event."""
        pass


class EventConsumer:
    """
    Async Kafka consumer for consuming events.
    Provides at-least-once delivery with manual offset commits.
    """

    def __init__(
        self,
        topics: list[str],
        group_id: Optional[str] = None,
        bootstrap_servers: Optional[str] = None,
        client_id: str = "agent-consumer",
        auto_offset_reset: str = "earliest",
        enable_auto_commit: bool = False,
        max_poll_records: int = 50,
    ):
        self.topics = topics
        self.group_id = group_id or os.getenv("KAFKA_GROUP_ID", "agent-workers")
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )
        self.client_id = client_id
        self.auto_offset_reset = auto_offset_reset
        self.enable_auto_commit = enable_auto_commit
        self.max_poll_records = max_poll_records

        self._consumer: Optional[AIOKafkaConsumer] = None
        self._started = False
        self._running = False
        self._handlers: dict[str, list[Callable]] = {}

    async def start(self) -> None:
        """Start the Kafka consumer."""
        if self._started:
            return

        logger.info(
            "Starting Kafka consumer",
            topics=self.topics,
            group_id=self.group_id,
            bootstrap_servers=self.bootstrap_servers,
        )

        self._consumer = AIOKafkaConsumer(
            *self.topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            client_id=self.client_id,
            auto_offset_reset=self.auto_offset_reset,
            enable_auto_commit=self.enable_auto_commit,
            max_poll_records=self.max_poll_records,
            value_deserializer=EventSerializer.deserialize,
            key_deserializer=lambda k: k.decode("utf-8") if k else None,
        )

        await self._consumer.start()
        self._started = True
        logger.info("Kafka consumer started successfully")

    async def stop(self) -> None:
        """Stop the Kafka consumer gracefully."""
        self._running = False
        if self._consumer and self._started:
            logger.info("Stopping Kafka consumer")
            await self._consumer.stop()
            self._started = False
            logger.info("Kafka consumer stopped")

    def register_handler(
        self,
        event_type: str,
        handler: Callable[[dict], Any],
    ) -> None:
        """
        Register an event handler for a specific event type.

        Args:
            event_type: The event type to handle (e.g., "task.assigned")
            handler: Async function to handle the event
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug("Registered handler for event type", event_type=event_type)

    async def consume(self) -> None:
        """
        Start consuming events and dispatch to handlers.
        Runs until stop() is called.
        """
        if not self._started:
            await self.start()

        self._running = True
        logger.info("Starting event consumption loop")

        try:
            async for message in self._consumer:
                if not self._running:
                    break

                try:
                    await self._process_message(message)

                    # Manual offset commit for at-least-once delivery
                    if not self.enable_auto_commit:
                        tp = TopicPartition(message.topic, message.partition)
                        await self._consumer.commit({tp: message.offset + 1})

                except Exception as e:
                    logger.error(
                        "Error processing message",
                        error=str(e),
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset,
                    )
                    # Continue processing other messages
                    continue

        except asyncio.CancelledError:
            logger.info("Consumer loop cancelled")
        except Exception as e:
            logger.error("Consumer loop error", error=str(e))
            raise

    async def _process_message(self, message) -> None:
        """Process a single Kafka message."""
        event = message.value
        event_type = event.get("event_type")

        logger.debug(
            "Processing event",
            event_type=event_type,
            topic=message.topic,
            partition=message.partition,
            offset=message.offset,
        )

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            logger.debug("No handlers for event type", event_type=event_type)
            return

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(
                    "Handler error",
                    error=str(e),
                    event_type=event_type,
                    handler=handler.__name__,
                )

    async def consume_one(self, timeout_ms: int = 5000) -> Optional[dict]:
        """
        Consume a single message with timeout.
        Useful for testing or batch processing.
        """
        if not self._started:
            await self.start()

        try:
            records = await self._consumer.getmany(
                timeout_ms=timeout_ms,
                max_records=1,
            )

            for tp, messages in records.items():
                for message in messages:
                    if not self.enable_auto_commit:
                        await self._consumer.commit({tp: message.offset + 1})
                    return message.value

            return None

        except KafkaError as e:
            logger.error("Error consuming message", error=str(e))
            return None

    async def seek_to_beginning(self, topic: Optional[str] = None) -> None:
        """Seek to the beginning of all partitions."""
        if not self._started:
            await self.start()

        partitions = self._consumer.assignment()
        if topic:
            partitions = [p for p in partitions if p.topic == topic]

        await self._consumer.seek_to_beginning(*partitions)
        logger.info("Seeked to beginning", partitions=[str(p) for p in partitions])

    async def seek_to_end(self, topic: Optional[str] = None) -> None:
        """Seek to the end of all partitions."""
        if not self._started:
            await self.start()

        partitions = self._consumer.assignment()
        if topic:
            partitions = [p for p in partitions if p.topic == topic]

        await self._consumer.seek_to_end(*partitions)
        logger.info("Seeked to end", partitions=[str(p) for p in partitions])


class TaskEventConsumer(EventConsumer):
    """
    Specialized consumer for task-related events.
    Pre-configured with task topics and common handlers.
    """

    def __init__(
        self,
        group_id: str = "task-workers",
        **kwargs,
    ):
        super().__init__(
            topics=[KafkaTopics.AGENT_TASKS],
            group_id=group_id,
            **kwargs,
        )

    def on_task_assigned(self, handler: Callable[[dict], Any]) -> None:
        """Register handler for task.assigned events."""
        self.register_handler("task.assigned", handler)

    def on_task_completed(self, handler: Callable[[dict], Any]) -> None:
        """Register handler for task.completed events."""
        self.register_handler("task.completed", handler)

    def on_task_failed(self, handler: Callable[[dict], Any]) -> None:
        """Register handler for task.failed events."""
        self.register_handler("task.failed", handler)


class AgentLifecycleConsumer(EventConsumer):
    """
    Specialized consumer for agent lifecycle events.
    Pre-configured with lifecycle topic and common handlers.
    """

    def __init__(
        self,
        group_id: str = "lifecycle-monitor",
        **kwargs,
    ):
        super().__init__(
            topics=[KafkaTopics.AGENT_LIFECYCLE],
            group_id=group_id,
            **kwargs,
        )

    def on_agent_spawned(self, handler: Callable[[dict], Any]) -> None:
        """Register handler for agent.spawned events."""
        self.register_handler("agent.spawned", handler)

    def on_agent_heartbeat(self, handler: Callable[[dict], Any]) -> None:
        """Register handler for agent.heartbeat events."""
        self.register_handler("agent.heartbeat", handler)

    def on_agent_stopped(self, handler: Callable[[dict], Any]) -> None:
        """Register handler for agent.stopped events."""
        self.register_handler("agent.stopped", handler)


class CommunicationConsumer(EventConsumer):
    """
    Specialized consumer for inter-agent communication events.
    Pre-configured with communication topic.
    """

    def __init__(
        self,
        agent_id: UUID,
        group_id: Optional[str] = None,
        **kwargs,
    ):
        self.agent_id = agent_id
        super().__init__(
            topics=[KafkaTopics.AGENT_COMMUNICATION],
            group_id=group_id or f"agent-{agent_id}",
            **kwargs,
        )

    def on_message(self, handler: Callable[[dict], Any]) -> None:
        """Register handler for agent.message events."""
        # Wrap handler to filter for this agent
        async def filtered_handler(event: dict):
            to_agent = event.get("to_agent_id")
            # Handle broadcast (to_agent is None) or direct message
            if to_agent is None or str(to_agent) == str(self.agent_id):
                await handler(event)

        self.register_handler("agent.message", filtered_handler)


class AllEventsConsumer(EventConsumer):
    """
    Consumer that subscribes to all event topics.
    Useful for monitoring and audit logging.
    """

    def __init__(
        self,
        group_id: str = "all-events-monitor",
        **kwargs,
    ):
        super().__init__(
            topics=KafkaTopics.all_topics(),
            group_id=group_id,
            **kwargs,
        )

    def on_any_event(self, handler: Callable[[dict], Any]) -> None:
        """Register a handler that receives all events."""
        for event_type in [
            "agent.spawned", "agent.started", "agent.stopped",
            "agent.failed", "agent.heartbeat",
            "task.created", "task.assigned", "task.started",
            "task.progress", "task.completed", "task.failed", "task.cancelled",
            "agent.message", "agent.request", "agent.response", "agent.broadcast",
            "state.updated", "state.synced",
            "system.alert", "system.health",
        ]:
            self.register_handler(event_type, handler)
