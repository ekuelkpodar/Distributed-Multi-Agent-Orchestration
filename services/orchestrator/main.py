"""
Main entry point for the Orchestrator Service.
Initializes FastAPI application with all middleware and routes.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import structlog

from config import get_settings
from api import routes
from api import analytics_routes, audit_routes, webhook_routes
from core.agent_manager import AgentManager
from core.task_scheduler import TaskScheduler
from services.metrics_service import MetricsService
from services.insights_service import AIInsightsService
from services.audit_service import AuditService
from services.webhook_service import WebhookService
from services.scheduler_service import AdvancedScheduler, SchedulerConfig, SchedulingStrategy
from shared.database.connections import init_databases, close_databases
from shared.events.producers import init_producer, close_producer
from shared.observability.logging import configure_logging
from shared.observability.tracing import init_tracing, shutdown_tracing
from shared.observability.metrics import init_metrics

settings = get_settings()

# Configure logging
configure_logging(
    service_name=settings.service_name,
    log_level=settings.log_level,
    json_format=settings.environment != "development",
)

logger = structlog.get_logger()

# Initialize tracing early (before app creation)
_tracing = None
if settings.enable_tracing:
    _tracing = init_tracing(
        service_name=settings.service_name,
        jaeger_host=settings.jaeger_agent_host,
        jaeger_port=settings.jaeger_agent_port,
    )

# Initialize metrics early
if settings.enable_metrics:
    init_metrics(settings.service_name, settings.service_version)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager for startup and shutdown."""
    logger.info(
        "Starting orchestrator service",
        version=settings.service_version,
        environment=settings.environment,
    )

    # Initialize databases
    await init_databases()
    logger.info("Database connections initialized")

    # Initialize Kafka producer
    try:
        await init_producer()
        logger.info("Kafka producer initialized")
    except Exception as e:
        logger.warning("Failed to initialize Kafka producer", error=str(e))

    # Initialize core managers
    routes.agent_manager = AgentManager(
        heartbeat_interval=settings.agent_heartbeat_interval,
        heartbeat_timeout=settings.agent_heartbeat_timeout,
        max_agents=settings.max_concurrent_agents,
    )
    await routes.agent_manager.start()

    routes.task_scheduler = TaskScheduler(
        default_timeout=settings.task_default_timeout,
        max_retries=settings.task_max_retries,
        retry_delay=settings.task_retry_delay,
        queue_max_size=settings.task_queue_max_size,
    )
    await routes.task_scheduler.start()

    # Initialize advanced services
    # Metrics Service
    analytics_routes.metrics_service = MetricsService(
        retention_days=settings.metrics_retention_days
    )
    await analytics_routes.metrics_service.start()
    logger.info("Metrics service initialized")

    # AI Insights Service
    analytics_routes.insights_service = AIInsightsService(
        cache_ttl=settings.insights_cache_ttl
    )
    logger.info("AI Insights service initialized")

    # Audit Service
    audit_routes.audit_service = AuditService(
        retention_days=settings.audit_retention_days
    )
    logger.info("Audit service initialized")

    # Webhook Service
    webhook_routes.webhook_service = WebhookService()
    await webhook_routes.webhook_service.start(
        worker_count=settings.webhook_worker_count
    )
    logger.info("Webhook service initialized")

    # Advanced Scheduler
    scheduler_config = SchedulerConfig(
        strategy=SchedulingStrategy(settings.scheduler_strategy),
        max_queue_size=settings.task_queue_max_size,
        aging_factor=settings.scheduler_aging_factor,
    )
    routes.advanced_scheduler = AdvancedScheduler(scheduler_config)
    await routes.advanced_scheduler.start()
    logger.info("Advanced scheduler initialized")

    logger.info("Orchestrator service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down orchestrator service")

    # Stop advanced services
    if hasattr(routes, 'advanced_scheduler') and routes.advanced_scheduler:
        await routes.advanced_scheduler.stop()
    if webhook_routes.webhook_service:
        await webhook_routes.webhook_service.stop()
    if analytics_routes.metrics_service:
        await analytics_routes.metrics_service.stop()

    # Stop core managers
    if routes.agent_manager:
        await routes.agent_manager.stop()
    if routes.task_scheduler:
        await routes.task_scheduler.stop()

    # Close connections
    await close_producer()
    await close_databases()

    # Shutdown tracing
    if settings.enable_tracing:
        shutdown_tracing()

    logger.info("Orchestrator service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Multi-Agent Orchestrator",
    description="Distributed Multi-Agent Orchestration Platform API",
    version=settings.service_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instrument FastAPI with tracing (must be done after app creation, before it starts)
if _tracing:
    _tracing.instrument_fastapi(app)


# Request/Response logging middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all requests and responses."""
    from shared.observability.logging import bind_context, clear_context
    from shared.observability.metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION
    import time
    from uuid import uuid4

    # Generate request ID
    request_id = str(uuid4())
    bind_context(request_id=request_id)

    start_time = time.time()

    try:
        response = await call_next(request)
        duration = time.time() - start_time

        # Log request
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )

        # Update metrics
        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=request.url.path,
            status=str(response.status_code),
        ).inc()

        HTTP_REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "Request failed",
            method=request.method,
            path=request.url.path,
            error=str(e),
            duration_ms=round(duration * 1000, 2),
        )
        raise
    finally:
        clear_context()


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        error=str(exc),
        error_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else None,
        },
    )


# Metrics endpoint
@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# Include API routes
app.include_router(routes.router, prefix=settings.api_prefix)
app.include_router(analytics_routes.router, prefix=settings.api_prefix)
app.include_router(audit_routes.router, prefix=settings.api_prefix)
app.include_router(webhook_routes.router, prefix=settings.api_prefix)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else 4,
    )
