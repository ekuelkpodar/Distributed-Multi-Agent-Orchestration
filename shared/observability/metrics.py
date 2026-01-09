"""
Prometheus metrics for the Multi-Agent Orchestration Platform.
Provides comprehensive metrics for monitoring agent and task performance.
"""

import os
import time
from functools import wraps
from typing import Optional, Callable, Any

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
    multiprocess,
    REGISTRY,
)
import structlog

logger = structlog.get_logger()


# Custom registry for multi-process environments
def get_registry() -> CollectorRegistry:
    """Get the appropriate registry for the environment."""
    if "prometheus_multiproc_dir" in os.environ:
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return registry
    return REGISTRY


# Agent Metrics
AGENT_SPAWNED_TOTAL = Counter(
    "agent_spawned_total",
    "Total number of agents spawned",
    ["agent_type", "pool"],
)

AGENT_ACTIVE = Gauge(
    "agent_active",
    "Number of currently active agents",
    ["agent_type", "status"],
)

AGENT_HEARTBEAT_LATENCY = Histogram(
    "agent_heartbeat_latency_seconds",
    "Latency of agent heartbeats",
    ["agent_type"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

AGENT_MEMORY_USAGE = Gauge(
    "agent_memory_usage_bytes",
    "Memory usage of agents",
    ["agent_id", "agent_type"],
)

AGENT_UPTIME = Gauge(
    "agent_uptime_seconds",
    "Uptime of agents in seconds",
    ["agent_id", "agent_type"],
)


# Task Metrics
TASK_SUBMITTED_TOTAL = Counter(
    "task_submitted_total",
    "Total number of tasks submitted",
    ["task_type", "priority"],
)

TASK_COMPLETED_TOTAL = Counter(
    "task_completed_total",
    "Total number of tasks completed",
    ["task_type", "status"],
)

TASK_FAILED_TOTAL = Counter(
    "task_failed_total",
    "Total number of failed tasks",
    ["task_type", "error_type"],
)

TASK_DURATION = Histogram(
    "task_duration_seconds",
    "Duration of task execution",
    ["task_type", "agent_type"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)

TASK_QUEUE_SIZE = Gauge(
    "task_queue_size",
    "Number of tasks in queue",
    ["queue_name", "priority"],
)

TASK_RETRY_TOTAL = Counter(
    "task_retry_total",
    "Total number of task retries",
    ["task_type"],
)


# Message Metrics
MESSAGE_SENT_TOTAL = Counter(
    "message_sent_total",
    "Total number of messages sent",
    ["topic", "message_type"],
)

MESSAGE_RECEIVED_TOTAL = Counter(
    "message_received_total",
    "Total number of messages received",
    ["topic", "message_type"],
)

MESSAGE_PROCESSING_TIME = Histogram(
    "message_processing_time_seconds",
    "Time to process messages",
    ["topic", "message_type"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

MESSAGE_FAILED_TOTAL = Counter(
    "message_failed_total",
    "Total number of failed messages",
    ["topic", "error_type"],
)


# API Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

HTTP_REQUEST_SIZE = Summary(
    "http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint"],
)

HTTP_RESPONSE_SIZE = Summary(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"],
)


# Memory Search Metrics
MEMORY_SEARCH_TOTAL = Counter(
    "memory_search_total",
    "Total number of memory searches",
    ["agent_id", "memory_type"],
)

MEMORY_SEARCH_DURATION = Histogram(
    "memory_search_duration_seconds",
    "Duration of memory searches",
    ["memory_type"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)

MEMORY_ENTRIES_TOTAL = Gauge(
    "memory_entries_total",
    "Total number of memory entries",
    ["agent_id", "memory_type"],
)


# Database Metrics
DB_QUERY_TOTAL = Counter(
    "db_query_total",
    "Total number of database queries",
    ["operation", "table"],
)

DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Duration of database queries",
    ["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

DB_CONNECTION_POOL_SIZE = Gauge(
    "db_connection_pool_size",
    "Database connection pool size",
    ["pool_name"],
)

DB_CONNECTION_POOL_USED = Gauge(
    "db_connection_pool_used",
    "Database connections in use",
    ["pool_name"],
)


# Redis Metrics
REDIS_COMMANDS_TOTAL = Counter(
    "redis_commands_total",
    "Total number of Redis commands",
    ["command"],
)

REDIS_COMMAND_DURATION = Histogram(
    "redis_command_duration_seconds",
    "Duration of Redis commands",
    ["command"],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1),
)

REDIS_CONNECTION_POOL_SIZE = Gauge(
    "redis_connection_pool_size",
    "Redis connection pool size",
)

REDIS_CONNECTION_POOL_USED = Gauge(
    "redis_connection_pool_used",
    "Redis connections in use",
)


# LLM Metrics
LLM_REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "Total number of LLM API requests",
    ["model", "operation"],
)

LLM_REQUEST_DURATION = Histogram(
    "llm_request_duration_seconds",
    "Duration of LLM API requests",
    ["model"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

LLM_TOKENS_TOTAL = Counter(
    "llm_tokens_total",
    "Total number of tokens processed",
    ["model", "token_type"],
)

LLM_ERRORS_TOTAL = Counter(
    "llm_errors_total",
    "Total number of LLM API errors",
    ["model", "error_type"],
)


# Service Info
SERVICE_INFO = Info(
    "service",
    "Service information",
)


class MetricsManager:
    """
    Manages Prometheus metrics collection and export.
    """

    def __init__(self, service_name: str, service_version: str = "1.0.0"):
        self.service_name = service_name
        self.service_version = service_version
        self._setup_service_info()

    def _setup_service_info(self) -> None:
        """Set up service information metric."""
        SERVICE_INFO.info({
            "name": self.service_name,
            "version": self.service_version,
            "environment": os.getenv("ENVIRONMENT", "development"),
        })

    def get_metrics(self) -> bytes:
        """Generate current metrics in Prometheus format."""
        registry = get_registry()
        return generate_latest(registry)

    def get_content_type(self) -> str:
        """Get the content type for metrics endpoint."""
        return CONTENT_TYPE_LATEST


def track_time(
    metric: Histogram,
    labels: Optional[dict] = None,
) -> Callable:
    """
    Decorator to track execution time of functions.

    Usage:
        @track_time(TASK_DURATION, {"task_type": "analysis", "agent_type": "worker"})
        async def process_task(task_id: str):
            # function body
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class Timer:
    """
    Context manager for timing code blocks.

    Usage:
        with Timer(TASK_DURATION, {"task_type": "analysis"}) as timer:
            # code block
        print(f"Took {timer.elapsed} seconds")
    """

    def __init__(self, metric: Histogram, labels: Optional[dict] = None):
        self.metric = metric
        self.labels = labels
        self.start_time: float = 0
        self.elapsed: float = 0

    def __enter__(self) -> "Timer":
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.elapsed = time.time() - self.start_time
        if self.labels:
            self.metric.labels(**self.labels).observe(self.elapsed)
        else:
            self.metric.observe(self.elapsed)


# Global metrics manager
metrics_manager: Optional[MetricsManager] = None


def init_metrics(service_name: str, service_version: str = "1.0.0") -> MetricsManager:
    """Initialize global metrics manager."""
    global metrics_manager
    metrics_manager = MetricsManager(service_name, service_version)
    logger.info("Metrics initialized", service=service_name, version=service_version)
    return metrics_manager


def get_metrics_manager() -> Optional[MetricsManager]:
    """Get the global metrics manager."""
    return metrics_manager
