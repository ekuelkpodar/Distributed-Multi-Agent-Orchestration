"""
Distributed tracing with OpenTelemetry for the Multi-Agent Orchestration Platform.
Provides request tracing across all services.
"""

import os
from contextlib import contextmanager
from typing import Optional, Any, Dict

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Status, StatusCode
import structlog

logger = structlog.get_logger()


class TracingConfig:
    """Configuration for distributed tracing."""

    def __init__(
        self,
        service_name: str,
        jaeger_host: Optional[str] = None,
        jaeger_port: Optional[int] = None,
        otlp_endpoint: Optional[str] = None,
        enable_console_export: bool = False,
        sample_rate: float = 1.0,
    ):
        self.service_name = service_name
        self.jaeger_host = jaeger_host or os.getenv("JAEGER_AGENT_HOST", "localhost")
        self.jaeger_port = jaeger_port or int(os.getenv("JAEGER_AGENT_PORT", "6831"))
        self.otlp_endpoint = otlp_endpoint or os.getenv("OTLP_ENDPOINT")
        self.enable_console_export = enable_console_export
        self.sample_rate = sample_rate


class TracingManager:
    """
    Manages OpenTelemetry tracing setup and instrumentation.
    """

    def __init__(self, config: TracingConfig):
        self.config = config
        self._tracer_provider: Optional[TracerProvider] = None
        self._tracer: Optional[trace.Tracer] = None

    def setup(self) -> None:
        """Initialize tracing with configured exporters."""
        logger.info(
            "Setting up distributed tracing",
            service=self.config.service_name,
            jaeger_host=self.config.jaeger_host,
            jaeger_port=self.config.jaeger_port,
        )

        # Create resource with service information
        resource = Resource.create({
            "service.name": self.config.service_name,
            "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
        })

        # Create tracer provider
        self._tracer_provider = TracerProvider(resource=resource)

        # Add Jaeger exporter
        try:
            jaeger_exporter = JaegerExporter(
                agent_host_name=self.config.jaeger_host,
                agent_port=self.config.jaeger_port,
            )
            self._tracer_provider.add_span_processor(
                BatchSpanProcessor(jaeger_exporter)
            )
            logger.info("Jaeger exporter configured")
        except Exception as e:
            logger.warning("Failed to configure Jaeger exporter", error=str(e))

        # Add OTLP exporter if configured
        if self.config.otlp_endpoint:
            try:
                otlp_exporter = OTLPSpanExporter(
                    endpoint=self.config.otlp_endpoint,
                    insecure=True,
                )
                self._tracer_provider.add_span_processor(
                    BatchSpanProcessor(otlp_exporter)
                )
                logger.info("OTLP exporter configured", endpoint=self.config.otlp_endpoint)
            except Exception as e:
                logger.warning("Failed to configure OTLP exporter", error=str(e))

        # Add console exporter for debugging
        if self.config.enable_console_export:
            self._tracer_provider.add_span_processor(
                BatchSpanProcessor(ConsoleSpanExporter())
            )

        # Set global tracer provider
        trace.set_tracer_provider(self._tracer_provider)

        # Set up propagator for distributed context
        set_global_textmap(B3MultiFormat())

        # Get tracer instance
        self._tracer = trace.get_tracer(self.config.service_name)

        logger.info("Distributed tracing setup complete")

    def instrument_fastapi(self, app) -> None:
        """Instrument FastAPI application."""
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumented for tracing")

    def instrument_sqlalchemy(self, engine) -> None:
        """Instrument SQLAlchemy engine."""
        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.info("SQLAlchemy instrumented for tracing")

    def instrument_redis(self) -> None:
        """Instrument Redis client."""
        RedisInstrumentor().instrument()
        logger.info("Redis instrumented for tracing")

    def instrument_http_clients(self) -> None:
        """Instrument HTTP clients."""
        HTTPXClientInstrumentor().instrument()
        AioHttpClientInstrumentor().instrument()
        logger.info("HTTP clients instrumented for tracing")

    def shutdown(self) -> None:
        """Shutdown tracing and flush pending spans."""
        if self._tracer_provider:
            self._tracer_provider.shutdown()
            logger.info("Tracing shutdown complete")

    @property
    def tracer(self) -> trace.Tracer:
        """Get the tracer instance."""
        if not self._tracer:
            self._tracer = trace.get_tracer(self.config.service_name)
        return self._tracer

    @contextmanager
    def span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    ):
        """
        Create a tracing span context manager.

        Usage:
            with tracing.span("my_operation", {"key": "value"}) as span:
                # do work
                span.set_attribute("result", "success")
        """
        with self.tracer.start_as_current_span(
            name,
            kind=kind,
            attributes=attributes or {},
        ) as span:
            try:
                yield span
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    def current_span(self) -> trace.Span:
        """Get the current active span."""
        return trace.get_current_span()

    def get_trace_id(self) -> Optional[str]:
        """Get the current trace ID as a hex string."""
        span = self.current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().trace_id, "032x")
        return None

    def get_span_id(self) -> Optional[str]:
        """Get the current span ID as a hex string."""
        span = self.current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().span_id, "016x")
        return None

    def inject_context(self, headers: dict) -> dict:
        """Inject trace context into headers for propagation."""
        from opentelemetry.propagate import inject
        inject(headers)
        return headers

    def extract_context(self, headers: dict):
        """Extract trace context from headers."""
        from opentelemetry.propagate import extract
        return extract(headers)


# Helper functions for easy span creation
def create_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
):
    """
    Decorator to automatically create spans for functions.

    Usage:
        @create_span("process_task", {"task.type": "analysis"})
        async def process_task(task_id: str):
            # function body
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(name, kind=kind, attributes=attributes or {}) as span:
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        def sync_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(name, kind=kind, attributes=attributes or {}) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Global tracing manager (initialized on service startup)
tracing_manager: Optional[TracingManager] = None


def init_tracing(
    service_name: str,
    jaeger_host: Optional[str] = None,
    jaeger_port: Optional[int] = None,
    otlp_endpoint: Optional[str] = None,
    enable_console_export: bool = False,
) -> TracingManager:
    """Initialize global tracing manager."""
    global tracing_manager

    config = TracingConfig(
        service_name=service_name,
        jaeger_host=jaeger_host,
        jaeger_port=jaeger_port,
        otlp_endpoint=otlp_endpoint,
        enable_console_export=enable_console_export,
    )

    tracing_manager = TracingManager(config)
    tracing_manager.setup()

    return tracing_manager


def get_tracing_manager() -> Optional[TracingManager]:
    """Get the global tracing manager."""
    return tracing_manager


def shutdown_tracing() -> None:
    """Shutdown global tracing manager."""
    global tracing_manager
    if tracing_manager:
        tracing_manager.shutdown()
        tracing_manager = None
