"""
Distributed tracing with OpenTelemetry
Traces requests and operations across services
"""

import os
from contextlib import contextmanager
from functools import wraps
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.zipkin.json import ZipkinExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# ============================================================================
# Tracer Setup
# ============================================================================

# Create resource with service information
resource = Resource(
    attributes={
        SERVICE_NAME: "pm-document-intelligence",
        "service.version": "1.0.0",
        "deployment.environment": os.getenv("ENVIRONMENT", "production"),
    }
)

# Create tracer provider
tracer_provider = TracerProvider(resource=resource)

# Configure Jaeger exporter
jaeger_exporter = JaegerExporter(
    agent_host_name=os.getenv("JAEGER_AGENT_HOST", "localhost"),
    agent_port=int(os.getenv("JAEGER_AGENT_PORT", "6831")),
)

# Configure Zipkin exporter (alternative)
zipkin_exporter = ZipkinExporter(
    endpoint=os.getenv("ZIPKIN_ENDPOINT", "http://localhost:9411/api/v2/spans"),
)

# Add span processors
tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
# Uncomment to use Zipkin instead:
# tracer_provider.add_span_processor(BatchSpanProcessor(zipkin_exporter))

# Set global tracer provider
trace.set_tracer_provider(tracer_provider)

# Get tracer
tracer = trace.get_tracer(__name__)

# Propagator for context propagation
propagator = TraceContextTextMapPropagator()


# ============================================================================
# Instrumentation
# ============================================================================


def instrument_app(app):
    """Instrument FastAPI application with OpenTelemetry"""
    FastAPIInstrumentor.instrument_app(app)


def instrument_sqlalchemy(engine):
    """Instrument SQLAlchemy with OpenTelemetry"""
    SQLAlchemyInstrumentor().instrument(engine=engine)


def instrument_redis(client):
    """Instrument Redis with OpenTelemetry"""
    RedisInstrumentor().instrument(redis_client=client)


# ============================================================================
# Tracing Utilities
# ============================================================================


@contextmanager
def trace_span(
    name: str,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: dict[str, Any] | None = None,
):
    """
    Context manager to create and manage a trace span

    Args:
        name: Name of the span
        kind: Type of span (INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER)
        attributes: Additional attributes to add to span

    Usage:
        with trace_span("process_document", attributes={"document_id": 123}):
            # Your code here
            pass
    """
    with tracer.start_as_current_span(name, kind=kind) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))

        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


def trace_function(name: str | None = None, attributes: dict[str, Any] | None = None):
    """
    Decorator to trace function execution

    Args:
        name: Custom span name (defaults to function name)
        attributes: Additional attributes to add to span

    Usage:
        @trace_function(attributes={"operation": "database_query"})
        def my_function():
            pass
    """

    def decorator(func):
        span_name = name or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with trace_span(span_name, attributes=attributes):
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with trace_span(span_name, attributes=attributes):
                return func(*args, **kwargs)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ============================================================================
# Document Processing Tracing
# ============================================================================


@contextmanager
def trace_document_upload(document_id: int, filename: str, size_bytes: int):
    """Trace document upload"""
    with trace_span(
        "document.upload",
        kind=SpanKind.SERVER,
        attributes={
            "document.id": document_id,
            "document.filename": filename,
            "document.size_bytes": size_bytes,
        },
    ) as span:
        yield span


@contextmanager
def trace_document_processing(document_id: int, document_type: str):
    """Trace complete document processing pipeline"""
    with trace_span(
        "document.processing.pipeline",
        kind=SpanKind.INTERNAL,
        attributes={"document.id": document_id, "document.type": document_type},
    ) as span:
        yield span


@contextmanager
def trace_text_extraction(document_id: int, extractor: str):
    """Trace text extraction"""
    with trace_span(
        "document.processing.text_extraction",
        attributes={"document.id": document_id, "extractor": extractor},
    ) as span:
        yield span


@contextmanager
def trace_entity_extraction(document_id: int, text_length: int):
    """Trace entity extraction"""
    with trace_span(
        "document.processing.entity_extraction",
        attributes={"document.id": document_id, "text_length": text_length},
    ) as span:
        yield span


@contextmanager
def trace_action_item_extraction(document_id: int):
    """Trace action item extraction"""
    with trace_span(
        "document.processing.action_items", attributes={"document.id": document_id}
    ) as span:
        yield span


# ============================================================================
# AWS Service Tracing
# ============================================================================


@contextmanager
def trace_aws_service_call(service: str, operation: str, **kwargs):
    """Trace AWS service call"""
    with trace_span(
        f"aws.{service}.{operation}",
        kind=SpanKind.CLIENT,
        attributes={
            "aws.service": service,
            "aws.operation": operation,
            **{f"aws.{k}": str(v) for k, v in kwargs.items()},
        },
    ) as span:
        yield span


@contextmanager
def trace_s3_operation(operation: str, bucket: str, key: str):
    """Trace S3 operation"""
    with trace_aws_service_call("s3", operation, bucket=bucket, key=key) as span:
        yield span


@contextmanager
def trace_textract_operation(operation: str, pages: int):
    """Trace Textract operation"""
    with trace_aws_service_call("textract", operation, pages=pages) as span:
        yield span


@contextmanager
def trace_comprehend_operation(operation: str, text_length: int):
    """Trace Comprehend operation"""
    with trace_aws_service_call("comprehend", operation, text_length=text_length) as span:
        yield span


@contextmanager
def trace_bedrock_operation(operation: str, model: str, input_tokens: int):
    """Trace Bedrock operation"""
    with trace_aws_service_call(
        "bedrock", operation, model=model, input_tokens=input_tokens
    ) as span:
        yield span


# ============================================================================
# OpenAI Service Tracing
# ============================================================================


@contextmanager
def trace_openai_call(operation: str, model: str):
    """Trace OpenAI API call"""
    with trace_span(
        f"openai.{operation}",
        kind=SpanKind.CLIENT,
        attributes={"openai.operation": operation, "openai.model": model},
    ) as span:
        yield span


@contextmanager
def trace_embedding_generation(model: str, text_count: int):
    """Trace embedding generation"""
    with trace_openai_call("embedding", model) as span:
        span.set_attribute("openai.text_count", text_count)
        yield span


# ============================================================================
# Database Tracing
# ============================================================================


@contextmanager
def trace_database_query(operation: str, table: str | None = None):
    """Trace database query"""
    attributes = {"db.operation": operation}
    if table:
        attributes["db.table"] = table

    with trace_span(f"db.query.{operation}", kind=SpanKind.CLIENT, attributes=attributes) as span:
        yield span


# ============================================================================
# AI Agent Tracing
# ============================================================================


@contextmanager
def trace_agent_execution(agent_type: str, document_id: int | None = None):
    """Trace AI agent execution"""
    attributes = {"agent.type": agent_type}
    if document_id:
        attributes["document.id"] = document_id

    with trace_span(f"agent.execute.{agent_type}", attributes=attributes) as span:
        yield span


@contextmanager
def trace_agent_orchestration(num_agents: int):
    """Trace agent orchestration"""
    with trace_span("agent.orchestration", attributes={"agent.count": num_agents}) as span:
        yield span


# ============================================================================
# Vector Search Tracing
# ============================================================================


@contextmanager
def trace_vector_search(query: str, search_type: str):
    """Trace vector search"""
    with trace_span(
        f"vector_search.{search_type}",
        attributes={
            "search.query": query[:100],  # Limit query length
            "search.type": search_type,
        },
    ) as span:
        yield span


@contextmanager
def trace_vector_indexing(document_id: int, text_length: int):
    """Trace vector indexing"""
    with trace_span(
        "vector_search.indexing",
        attributes={"document.id": document_id, "text.length": text_length},
    ) as span:
        yield span


# ============================================================================
# API Request Tracing
# ============================================================================


@contextmanager
def trace_api_request(method: str, endpoint: str, user_id: int | None = None):
    """Trace API request"""
    attributes = {"http.method": method, "http.endpoint": endpoint}
    if user_id:
        attributes["user.id"] = user_id

    with trace_span(
        f"http.{method}.{endpoint}", kind=SpanKind.SERVER, attributes=attributes
    ) as span:
        yield span


# ============================================================================
# Context Propagation
# ============================================================================


def inject_trace_context(headers: dict[str, str]) -> dict[str, str]:
    """
    Inject trace context into headers for propagation

    Args:
        headers: Dictionary of headers

    Returns:
        Headers with trace context injected
    """
    propagator.inject(headers)
    return headers


def extract_trace_context(headers: dict[str, str]):
    """
    Extract trace context from headers

    Args:
        headers: Dictionary of headers containing trace context
    """
    return propagator.extract(headers)


# ============================================================================
# Span Utilities
# ============================================================================


def add_span_event(name: str, attributes: dict[str, Any] | None = None):
    """Add event to current span"""
    span = trace.get_current_span()
    if span:
        span.add_event(name, attributes=attributes or {})


def set_span_attribute(key: str, value: Any):
    """Set attribute on current span"""
    span = trace.get_current_span()
    if span:
        span.set_attribute(key, str(value))


def set_span_error(error: Exception):
    """Mark current span as error"""
    span = trace.get_current_span()
    if span:
        span.set_status(Status(StatusCode.ERROR, str(error)))
        span.record_exception(error)


def get_trace_id() -> str | None:
    """Get current trace ID"""
    span = trace.get_current_span()
    if span and span.is_recording():
        return format(span.get_span_context().trace_id, "032x")
    return None


def get_span_id() -> str | None:
    """Get current span ID"""
    span = trace.get_current_span()
    if span and span.is_recording():
        return format(span.get_span_context().span_id, "016x")
    return None


# ============================================================================
# Sampling Configuration
# ============================================================================


def should_sample_trace() -> bool:
    """
    Determine if trace should be sampled
    Can be customized based on environment, endpoint, etc.
    """
    # Sample 100% in development, 10% in production
    environment = os.getenv("ENVIRONMENT", "production")
    if environment == "development":
        return True

    # Sample based on trace ID for consistent sampling
    import random

    return random.random() < 0.1  # 10% sampling


# ============================================================================
# Cleanup
# ============================================================================


def shutdown_tracing():
    """Shutdown tracing and flush remaining spans"""
    tracer_provider.shutdown()
