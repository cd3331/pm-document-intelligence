"""
Prometheus metrics for monitoring application performance and business metrics
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    Info,
    generate_latest,
    REGISTRY,
    CollectorRegistry,
)
from typing import Optional, Dict, Any
import time
from functools import wraps
from contextlib import contextmanager


# ============================================================================
# Application Info
# ============================================================================

app_info = Info("pm_document_intelligence", "Application information")
app_info.info({"version": "1.0.0", "environment": "production"})


# ============================================================================
# HTTP Request Metrics
# ============================================================================

http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status_code"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"],
)


# ============================================================================
# Document Processing Metrics
# ============================================================================

documents_uploaded_total = Counter(
    "documents_uploaded_total",
    "Total number of documents uploaded",
    ["document_type", "status"],
)

document_processing_duration_seconds = Histogram(
    "document_processing_duration_seconds",
    "Document processing duration in seconds",
    ["document_type", "processing_stage"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)

documents_processing_current = Gauge(
    "documents_processing_current",
    "Number of documents currently being processed",
    ["processing_stage"],
)

document_size_bytes = Histogram(
    "document_size_bytes",
    "Size of uploaded documents in bytes",
    ["document_type"],
    buckets=[1024, 10240, 102400, 1024000, 10240000, 104857600],  # 1KB to 100MB
)

documents_failed_total = Counter(
    "documents_failed_total",
    "Total number of failed document processing",
    ["document_type", "error_type"],
)


# ============================================================================
# AWS Service Metrics
# ============================================================================

aws_api_calls_total = Counter(
    "aws_api_calls_total", "Total AWS API calls", ["service", "operation", "status"]
)

aws_api_latency_seconds = Histogram(
    "aws_api_latency_seconds",
    "AWS API call latency in seconds",
    ["service", "operation"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

aws_textract_pages_processed = Counter(
    "aws_textract_pages_processed_total",
    "Total pages processed by Textract",
    ["status"],
)

aws_bedrock_tokens_used = Counter(
    "aws_bedrock_tokens_used_total",
    "Total tokens used by Bedrock",
    ["model", "token_type"],  # token_type: input, output
)


# ============================================================================
# OpenAI API Metrics
# ============================================================================

openai_api_calls_total = Counter(
    "openai_api_calls_total", "Total OpenAI API calls", ["operation", "model", "status"]
)

openai_api_latency_seconds = Histogram(
    "openai_api_latency_seconds",
    "OpenAI API call latency in seconds",
    ["operation", "model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0],
)

openai_tokens_used = Counter(
    "openai_tokens_used_total",
    "Total tokens used by OpenAI",
    ["model", "token_type"],  # token_type: prompt, completion
)

openai_embedding_dimensions = Gauge(
    "openai_embedding_dimensions", "Dimensions of OpenAI embeddings", ["model"]
)


# ============================================================================
# Database Metrics
# ============================================================================

db_connections_active = Gauge("db_connections_active", "Number of active database connections")

db_connections_idle = Gauge("db_connections_idle", "Number of idle database connections")

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],  # SELECT, INSERT, UPDATE, DELETE
    buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0],
)

db_queries_total = Counter("db_queries_total", "Total database queries", ["operation", "status"])


# ============================================================================
# Cache Metrics
# ============================================================================

cache_operations_total = Counter(
    "cache_operations_total",
    "Total cache operations",
    ["operation", "result"],  # operation: get/set/delete, result: hit/miss/success
)

cache_hit_ratio = Gauge("cache_hit_ratio", "Cache hit ratio (0-1)")

cache_size_bytes = Gauge("cache_size_bytes", "Current cache size in bytes")

cache_evictions_total = Counter(
    "cache_evictions_total",
    "Total cache evictions",
    ["reason"],  # reason: size, ttl, manual
)


# ============================================================================
# User Activity Metrics
# ============================================================================

active_users_current = Gauge("active_users_current", "Number of currently active users")

user_sessions_total = Counter(
    "user_sessions_total", "Total user sessions", ["status"]  # status: started, ended
)

user_actions_total = Counter(
    "user_actions_total",
    "Total user actions",
    ["action_type"],  # upload, search, qa, download
)


# ============================================================================
# Error Metrics
# ============================================================================

errors_total = Counter(
    "errors_total",
    "Total errors",
    ["error_type", "severity"],  # severity: warning, error, critical
)

exceptions_total = Counter(
    "exceptions_total", "Total exceptions raised", ["exception_type", "endpoint"]
)


# ============================================================================
# Cost Metrics
# ============================================================================

aws_cost_usd = Counter("aws_cost_usd_total", "Total AWS costs in USD", ["service"])

openai_cost_usd = Counter(
    "openai_cost_usd_total", "Total OpenAI costs in USD", ["model", "operation"]
)

total_cost_usd = Gauge("total_cost_usd_daily", "Total daily costs in USD")


# ============================================================================
# System Resource Metrics
# ============================================================================

system_cpu_usage_percent = Gauge("system_cpu_usage_percent", "System CPU usage percentage")

system_memory_usage_bytes = Gauge("system_memory_usage_bytes", "System memory usage in bytes")

system_disk_usage_bytes = Gauge(
    "system_disk_usage_bytes", "System disk usage in bytes", ["mount_point"]
)

system_network_bytes_sent = Counter("system_network_bytes_sent_total", "Total network bytes sent")

system_network_bytes_received = Counter(
    "system_network_bytes_received_total", "Total network bytes received"
)


# ============================================================================
# AI Agent Metrics
# ============================================================================

agent_executions_total = Counter(
    "agent_executions_total", "Total AI agent executions", ["agent_type", "status"]
)

agent_execution_duration_seconds = Histogram(
    "agent_execution_duration_seconds",
    "AI agent execution duration in seconds",
    ["agent_type"],
    buckets=[1, 5, 10, 30, 60, 120],
)

agent_retries_total = Counter(
    "agent_retries_total", "Total agent retry attempts", ["agent_type", "reason"]
)


# ============================================================================
# Vector Search Metrics
# ============================================================================

vector_search_queries_total = Counter(
    "vector_search_queries_total",
    "Total vector search queries",
    ["search_type"],  # semantic, keyword, hybrid
)

vector_search_latency_seconds = Histogram(
    "vector_search_latency_seconds",
    "Vector search latency in seconds",
    ["search_type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
)

vector_search_results_count = Histogram(
    "vector_search_results_count",
    "Number of search results returned",
    buckets=[0, 1, 5, 10, 20, 50, 100],
)

embeddings_generated_total = Counter(
    "embeddings_generated_total", "Total embeddings generated", ["model"]
)


# ============================================================================
# Helper Functions
# ============================================================================


@contextmanager
def track_request_duration(method: str, endpoint: str):
    """Context manager to track HTTP request duration"""
    http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()
    start_time = time.time()

    try:
        yield
    finally:
        duration = time.time() - start_time
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
        http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()


def track_http_request(method: str, endpoint: str, status_code: int):
    """Track HTTP request completion"""
    http_requests_total.labels(method=method, endpoint=endpoint, status_code=status_code).inc()


def track_document_upload(document_type: str, status: str, size_bytes: int):
    """Track document upload"""
    documents_uploaded_total.labels(document_type=document_type, status=status).inc()

    document_size_bytes.labels(document_type=document_type).observe(size_bytes)


@contextmanager
def track_document_processing(document_type: str, stage: str):
    """Context manager to track document processing"""
    documents_processing_current.labels(processing_stage=stage).inc()
    start_time = time.time()

    try:
        yield
    finally:
        duration = time.time() - start_time
        document_processing_duration_seconds.labels(
            document_type=document_type, processing_stage=stage
        ).observe(duration)
        documents_processing_current.labels(processing_stage=stage).dec()


def track_document_failure(document_type: str, error_type: str):
    """Track document processing failure"""
    documents_failed_total.labels(document_type=document_type, error_type=error_type).inc()


@contextmanager
def track_aws_api_call(service: str, operation: str):
    """Context manager to track AWS API call"""
    start_time = time.time()
    status = "success"

    try:
        yield
    except Exception as e:
        status = "error"
        raise
    finally:
        duration = time.time() - start_time
        aws_api_latency_seconds.labels(service=service, operation=operation).observe(duration)

        aws_api_calls_total.labels(service=service, operation=operation, status=status).inc()


def track_aws_textract(pages: int, status: str = "success"):
    """Track Textract page processing"""
    aws_textract_pages_processed.labels(status=status).inc(pages)


def track_aws_bedrock_tokens(model: str, input_tokens: int, output_tokens: int):
    """Track Bedrock token usage"""
    aws_bedrock_tokens_used.labels(model=model, token_type="input").inc(input_tokens)
    aws_bedrock_tokens_used.labels(model=model, token_type="output").inc(output_tokens)


@contextmanager
def track_openai_call(operation: str, model: str):
    """Context manager to track OpenAI API call"""
    start_time = time.time()
    status = "success"

    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        duration = time.time() - start_time
        openai_api_latency_seconds.labels(operation=operation, model=model).observe(duration)

        openai_api_calls_total.labels(operation=operation, model=model, status=status).inc()


def track_openai_tokens(model: str, prompt_tokens: int, completion_tokens: int):
    """Track OpenAI token usage"""
    openai_tokens_used.labels(model=model, token_type="prompt").inc(prompt_tokens)
    openai_tokens_used.labels(model=model, token_type="completion").inc(completion_tokens)


@contextmanager
def track_db_query(operation: str):
    """Context manager to track database query"""
    start_time = time.time()
    status = "success"

    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        duration = time.time() - start_time
        db_query_duration_seconds.labels(operation=operation).observe(duration)
        db_queries_total.labels(operation=operation, status=status).inc()


def track_cache_operation(operation: str, result: str):
    """Track cache operation"""
    cache_operations_total.labels(operation=operation, result=result).inc()


def update_cache_hit_ratio(hits: int, total: int):
    """Update cache hit ratio"""
    if total > 0:
        ratio = hits / total
        cache_hit_ratio.set(ratio)


def track_error(error_type: str, severity: str = "error"):
    """Track application error"""
    errors_total.labels(error_type=error_type, severity=severity).inc()


def track_exception(exception_type: str, endpoint: str = "unknown"):
    """Track exception"""
    exceptions_total.labels(exception_type=exception_type, endpoint=endpoint).inc()


def track_cost(service: str, cost_usd: float):
    """Track service cost"""
    if service.startswith("aws_"):
        aws_cost_usd.labels(service=service).inc(cost_usd)
    elif service.startswith("openai_"):
        parts = service.split("_", 2)
        model = parts[1] if len(parts) > 1 else "unknown"
        operation = parts[2] if len(parts) > 2 else "unknown"
        openai_cost_usd.labels(model=model, operation=operation).inc(cost_usd)


@contextmanager
def track_agent_execution(agent_type: str):
    """Context manager to track agent execution"""
    start_time = time.time()
    status = "success"

    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        duration = time.time() - start_time
        agent_execution_duration_seconds.labels(agent_type=agent_type).observe(duration)
        agent_executions_total.labels(agent_type=agent_type, status=status).inc()


def track_agent_retry(agent_type: str, reason: str):
    """Track agent retry"""
    agent_retries_total.labels(agent_type=agent_type, reason=reason).inc()


@contextmanager
def track_vector_search(search_type: str):
    """Context manager to track vector search"""
    start_time = time.time()

    try:
        yield
    finally:
        duration = time.time() - start_time
        vector_search_latency_seconds.labels(search_type=search_type).observe(duration)
        vector_search_queries_total.labels(search_type=search_type).inc()


def track_search_results(count: int):
    """Track number of search results"""
    vector_search_results_count.observe(count)


def track_embedding_generation(model: str, count: int = 1):
    """Track embedding generation"""
    embeddings_generated_total.labels(model=model).inc(count)


# ============================================================================
# Decorator for automatic metric tracking
# ============================================================================


def track_endpoint_metrics(endpoint: str):
    """Decorator to automatically track endpoint metrics"""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            method = kwargs.get("request", args[0] if args else None)
            method_name = getattr(method, "method", "GET") if method else "GET"

            with track_request_duration(method_name, endpoint):
                try:
                    response = await func(*args, **kwargs)
                    status_code = getattr(response, "status_code", 200)
                    track_http_request(method_name, endpoint, status_code)
                    return response
                except Exception as e:
                    track_http_request(method_name, endpoint, 500)
                    track_exception(type(e).__name__, endpoint)
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            method = kwargs.get("request", args[0] if args else None)
            method_name = getattr(method, "method", "GET") if method else "GET"

            with track_request_duration(method_name, endpoint):
                try:
                    response = func(*args, **kwargs)
                    status_code = getattr(response, "status_code", 200)
                    track_http_request(method_name, endpoint, status_code)
                    return response
                except Exception as e:
                    track_http_request(method_name, endpoint, 500)
                    track_exception(type(e).__name__, endpoint)
                    raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ============================================================================
# System metrics collector
# ============================================================================


def collect_system_metrics():
    """Collect system-level metrics"""
    import psutil

    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    system_cpu_usage_percent.set(cpu_percent)

    # Memory
    memory = psutil.virtual_memory()
    system_memory_usage_bytes.set(memory.used)

    # Disk
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            system_disk_usage_bytes.labels(mount_point=partition.mountpoint).set(usage.used)
        except (PermissionError, OSError):
            pass

    # Network
    net_io = psutil.net_io_counters()
    system_network_bytes_sent.inc(net_io.bytes_sent)
    system_network_bytes_received.inc(net_io.bytes_recv)


def get_metrics():
    """Get all metrics in Prometheus format"""
    collect_system_metrics()
    return generate_latest(REGISTRY)
