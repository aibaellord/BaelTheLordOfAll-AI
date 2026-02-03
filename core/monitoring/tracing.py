"""
OpenTelemetry distributed tracing for BAEL.

Provides distributed tracing with span creation and context propagation.
"""

import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


def setup_tracing(
    service_name: str = "bael",
    jaeger_host: str = "localhost",
    jaeger_port: int = 6831,
    sample_rate: float = 0.1
) -> TracerProvider:
    """
    Set up OpenTelemetry tracing with Jaeger exporter.

    Args:
        service_name: Name of the service
        jaeger_host: Jaeger agent host
        jaeger_port: Jaeger agent port
        sample_rate: Sampling rate (0.0 to 1.0)

    Returns:
        TracerProvider: Configured tracer provider
    """
    # Create resource with service name
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "3.0.0",
        "deployment.environment": "production"
    })

    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)

    # Create Jaeger exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name=jaeger_host,
        agent_port=jaeger_port,
    )

    # Add span processor
    span_processor = BatchSpanProcessor(jaeger_exporter)
    tracer_provider.add_span_processor(span_processor)

    # Set global tracer provider
    trace.set_tracer_provider(tracer_provider)

    logger.info(f"Tracing configured: {service_name} -> {jaeger_host}:{jaeger_port}")

    return tracer_provider


def instrument_fastapi(app):
    """
    Instrument FastAPI app with OpenTelemetry.

    Args:
        app: FastAPI application
    """
    FastAPIInstrumentor.instrument_app(app)
    logger.info("FastAPI instrumented with OpenTelemetry")


def instrument_libraries():
    """Instrument common libraries with OpenTelemetry."""
    # Instrument requests library
    RequestsInstrumentor().instrument()

    # Instrument Redis
    RedisInstrumentor().instrument()

    logger.info("Libraries instrumented with OpenTelemetry")


def get_tracer(name: str = "bael") -> trace.Tracer:
    """
    Get tracer instance.

    Args:
        name: Tracer name

    Returns:
        Tracer: OpenTelemetry tracer
    """
    return trace.get_tracer(name)


class TracingMiddleware:
    """Custom tracing middleware for additional context."""

    def __init__(self, app, tracer: Optional[trace.Tracer] = None):
        self.app = app
        self.tracer = tracer or get_tracer()

    async def __call__(self, scope, receive, send):
        """Process request with tracing."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Create span for request
        with self.tracer.start_as_current_span(
            f"{scope['method']} {scope['path']}",
            kind=trace.SpanKind.SERVER
        ) as span:
            # Add span attributes
            span.set_attribute("http.method", scope["method"])
            span.set_attribute("http.url", scope["path"])
            span.set_attribute("http.scheme", scope["scheme"])

            try:
                await self.app(scope, receive, send)
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise


# Example usage
if __name__ == "__main__":
    # Setup tracing
    setup_tracing(
        service_name="bael",
        jaeger_host="localhost",
        jaeger_port=6831
    )

    # Instrument libraries
    instrument_libraries()

    # Create tracer
    tracer = get_tracer()

    # Example span
    with tracer.start_as_current_span("example_operation") as span:
        span.set_attribute("user_id", "user-123")
        span.add_event("Processing started")

        # Simulate work
        import time
        time.sleep(0.1)

        span.add_event("Processing completed")

    print("Tracing example completed")
