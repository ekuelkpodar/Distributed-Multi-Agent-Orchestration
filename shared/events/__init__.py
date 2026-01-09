"""Event handling package for Kafka producers and consumers."""

from shared.events.producers import (
    KafkaTopics,
    EventSerializer,
    EventProducer,
    event_producer,
    init_producer,
    close_producer,
)
from shared.events.consumers import (
    EventHandler,
    EventConsumer,
    TaskEventConsumer,
    AgentLifecycleConsumer,
    CommunicationConsumer,
    AllEventsConsumer,
)

__all__ = [
    # Topics
    "KafkaTopics",
    # Serialization
    "EventSerializer",
    # Producers
    "EventProducer",
    "event_producer",
    "init_producer",
    "close_producer",
    # Consumers
    "EventHandler",
    "EventConsumer",
    "TaskEventConsumer",
    "AgentLifecycleConsumer",
    "CommunicationConsumer",
    "AllEventsConsumer",
]
