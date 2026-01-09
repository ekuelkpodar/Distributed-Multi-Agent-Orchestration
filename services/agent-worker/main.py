"""
Main entry point for the Agent Worker Service.
Runs as a Kafka consumer processing task assignments.
"""

import asyncio
import signal
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import structlog

from config import get_settings
from execution.task_executor import TaskExecutor, TaskEventHandler
from shared.database.connections import init_databases, close_databases
from shared.events.producers import init_producer, close_producer
from shared.events.consumers import TaskEventConsumer
from shared.observability.logging import configure_logging
from shared.observability.tracing import init_tracing, shutdown_tracing
from shared.observability.metrics import init_metrics, AGENT_ACTIVE

settings = get_settings()

# Configure logging
configure_logging(
    service_name=settings.service_name,
    log_level=settings.log_level,
    json_format=settings.environment != "development",
)

logger = structlog.get_logger()

# Global instances
task_executor: TaskExecutor = None
task_consumer: TaskEventConsumer = None
event_handler: TaskEventHandler = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    global task_executor, task_consumer, event_handler

    worker_id = settings.worker_id or f"worker-{uuid4().hex[:8]}"

    logger.info(
        "Starting agent worker service",
        worker_id=worker_id,
        version=settings.service_version,
        environment=settings.environment,
    )

    # Initialize observability
    if settings.jaeger_agent_host:
        init_tracing(
            service_name=settings.service_name,
            jaeger_host=settings.jaeger_agent_host,
            jaeger_port=settings.jaeger_agent_port,
        )

    init_metrics(settings.service_name, settings.service_version)

    # Initialize databases
    await init_databases()
    logger.info("Database connections initialized")

    # Initialize Kafka producer
    try:
        await init_producer()
        logger.info("Kafka producer initialized")
    except Exception as e:
        logger.warning("Failed to initialize Kafka producer", error=str(e))

    # Initialize task executor
    task_executor = TaskExecutor(
        worker_id=worker_id,
        max_concurrent_tasks=settings.max_concurrent_tasks,
        task_timeout=settings.task_timeout,
        retry_attempts=settings.retry_attempts,
    )
    await task_executor.start()

    # Initialize event handler
    event_handler = TaskEventHandler(task_executor)

    # Initialize and start Kafka consumer
    task_consumer = TaskEventConsumer(
        group_id=f"{settings.kafka_group_id}-{worker_id}",
        bootstrap_servers=settings.kafka_bootstrap_servers,
    )

    # Register event handlers
    task_consumer.on_task_assigned(event_handler.handle_task_assigned)

    # Start consumer in background
    consumer_task = asyncio.create_task(run_consumer())

    # Start heartbeat task
    heartbeat_task = asyncio.create_task(heartbeat_loop(worker_id))

    logger.info("Agent worker service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down agent worker service")

    # Cancel background tasks
    consumer_task.cancel()
    heartbeat_task.cancel()

    try:
        await consumer_task
    except asyncio.CancelledError:
        pass

    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass

    # Stop task executor
    if task_executor:
        await task_executor.stop()

    # Close Kafka consumer
    if task_consumer:
        await task_consumer.stop()

    # Close connections
    await close_producer()
    await close_databases()

    # Shutdown tracing
    shutdown_tracing()

    logger.info("Agent worker service shutdown complete")


async def run_consumer() -> None:
    """Run the Kafka consumer loop."""
    try:
        await task_consumer.consume()
    except asyncio.CancelledError:
        logger.info("Consumer loop cancelled")
    except Exception as e:
        logger.error("Consumer loop error", error=str(e))


async def heartbeat_loop(worker_id: str) -> None:
    """Send periodic heartbeats."""
    from shared.events.producers import event_producer

    while True:
        try:
            await asyncio.sleep(settings.heartbeat_interval)

            # Get worker metrics
            metrics = {
                "active_tasks": task_executor.get_active_task_count() if task_executor else 0,
                "agent_count": task_executor.get_agent_count() if task_executor else 0,
                "worker_id": worker_id,
            }

            # Publish system health event
            await event_producer.publish_system_event(
                service=f"agent-worker-{worker_id}",
                severity="info",
                message="Worker heartbeat",
                details=metrics,
            )

            logger.debug("Sent worker heartbeat", **metrics)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Heartbeat error", error=str(e))


# Create FastAPI app for health checks and metrics
app = FastAPI(
    title="Agent Worker",
    description="Agent Worker Service for task execution",
    version=settings.service_version,
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.service_version,
        "active_tasks": task_executor.get_active_task_count() if task_executor else 0,
    }


@app.get("/ready")
async def readiness():
    """Readiness probe."""
    if task_executor is None:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready"},
        )
    return {"status": "ready"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/status")
async def status():
    """Detailed status endpoint."""
    return {
        "worker_id": settings.worker_id,
        "status": "running",
        "active_tasks": task_executor.get_active_task_count() if task_executor else 0,
        "agent_count": task_executor.get_agent_count() if task_executor else 0,
        "max_concurrent_tasks": settings.max_concurrent_tasks,
    }


def handle_signals():
    """Set up signal handlers for graceful shutdown."""
    loop = asyncio.get_event_loop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda s=sig: asyncio.create_task(shutdown(s)),
        )


async def shutdown(sig):
    """Handle shutdown signal."""
    logger.info(f"Received signal {sig.name}, shutting down...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.worker_host,
        port=settings.worker_port,
        reload=settings.debug,
        workers=1,  # Single worker for proper Kafka consumer coordination
    )
