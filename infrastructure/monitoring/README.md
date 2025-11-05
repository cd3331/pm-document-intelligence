# PM Document Intelligence - Monitoring Infrastructure

This directory contains the complete monitoring, observability, and logging stack for the PM Document Intelligence platform.

## Stack Components

### Core Monitoring
- **Prometheus**: Metrics collection and storage
- **Grafana**: Metrics visualization and dashboards
- **Alertmanager**: Alert routing and delivery
- **Jaeger**: Distributed tracing
- **Loki**: Log aggregation
- **Promtail**: Log collection and forwarding

### Supporting Services
- **Redis**: Caching layer
- **Redis Commander**: Redis GUI
- **LocalStack**: AWS services simulation for development
- **Node Exporter**: System-level metrics
- **cAdvisor**: Container metrics

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- At least 4GB of available RAM
- Ports 3000, 8080, 8081, 9090, 9093, 16686 available

### Starting the Stack

```bash
# Navigate to monitoring directory
cd infrastructure/monitoring

# Export Grafana dashboards from Python configs
python export_dashboards.py

# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### Stopping the Stack

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v
```

## Accessing Services

### Grafana
- **URL**: http://localhost:3000
- **Default credentials**: admin / admin
- **Pre-configured dashboards**:
  - System Overview: Request rates, errors, latency, CPU, memory
  - Document Processing: Upload rates, processing duration, failures
  - Cost Tracking: AWS and OpenAI costs

### Prometheus
- **URL**: http://localhost:9090
- **Targets**: http://localhost:9090/targets
- **Alerts**: http://localhost:9090/alerts

### Jaeger (Distributed Tracing)
- **URL**: http://localhost:16686
- **Search traces** by service, operation, tags
- **View trace flamegraphs** and dependency graphs

### Alertmanager
- **URL**: http://localhost:9093
- **View active alerts** and silence notifications

### Redis Commander
- **URL**: http://localhost:8081
- **Browse Redis keys** and monitor cache

### cAdvisor (Container Metrics)
- **URL**: http://localhost:8080
- **View container** resource usage

### LocalStack (AWS Simulation)
- **Gateway URL**: http://localhost:4566
- **Services**: S3, Textract, Comprehend, Bedrock, SQS, SNS

## Configuration

### Prometheus

**Configuration**: `prometheus/prometheus.yml`

```yaml
# Scrape interval
global:
  scrape_interval: 15s

# Add new scrape targets
scrape_configs:
  - job_name: 'my-service'
    static_configs:
      - targets: ['my-service:9090']
```

**Alert Rules**: `prometheus/alerts.yml`

Add custom alert rules following the existing patterns.

### Alertmanager

**Configuration**: `alertmanager/alertmanager.yml`

Configure notification channels:

```yaml
receivers:
  - name: 'my-receiver'
    slack_configs:
      - channel: '#alerts'
        webhook_url: 'YOUR_SLACK_WEBHOOK'
    email_configs:
      - to: 'team@example.com'
        from: 'alerts@example.com'
```

**Required for production**:
1. Update Slack webhook URL
2. Configure email SMTP settings
3. Add PagerDuty service key

### Grafana Dashboards

**Auto-provisioned from**: `backend/app/monitoring/dashboard_config.py`

To update dashboards:
1. Edit `backend/app/monitoring/dashboard_config.py`
2. Run `python export_dashboards.py`
3. Restart Grafana: `docker-compose restart grafana`

**Manual dashboard creation**:
1. Create dashboard in Grafana UI
2. Export JSON via Settings → JSON Model
3. Save to `grafana/dashboards/`

### Loki & Promtail

**Loki config**: `loki/loki-config.yml`
**Promtail config**: `promtail/promtail-config.yml`

Retention period (default 31 days):
```yaml
limits_config:
  retention_period: 744h
```

## Instrumentation

### Application Setup

The backend application is already instrumented with:

1. **Prometheus metrics** (`backend/app/monitoring/metrics.py`)
2. **OpenTelemetry tracing** (`backend/app/monitoring/tracing.py`)
3. **Structured logging** (`backend/app/monitoring/log_aggregation.py`)

### Using Metrics in Code

```python
from app.monitoring.metrics import (
    http_requests_total,
    track_request_duration,
    track_document_processing
)

# Track HTTP requests
@track_request_duration(method="GET", endpoint="/api/documents")
def get_documents():
    http_requests_total.labels(
        method="GET",
        endpoint="/api/documents",
        status_code=200
    ).inc()
    # ... your code

# Track document processing
with track_document_processing(document_id=123, document_type="pdf"):
    # ... processing logic
```

### Using Tracing

```python
from app.monitoring.tracing import trace_span, trace_document_processing

# Trace a function
with trace_span("process_document", attributes={"doc_id": 123}):
    # ... processing logic

# Trace document pipeline
with trace_document_processing(document_id=123, document_type="pdf"):
    # ... pipeline stages
```

### Using Structured Logging

```python
from app.monitoring.log_aggregation import app_logger

# Log with automatic PII masking and trace context
app_logger.info(
    "Document processed successfully",
    document_id=123,
    user_id="user-456",
    duration_ms=1500
)
```

## Alert Configuration

### Available Alerts

| Alert | Severity | Threshold | Description |
|-------|----------|-----------|-------------|
| HighErrorRate | Critical | >5% error rate | HTTP 5xx errors exceed threshold |
| SlowResponseTime | Warning | >2s P95 latency | API response time degraded |
| AWSServiceFailure | Critical | >0.1 errors/sec | AWS API failures |
| DatabaseConnectionError | Critical | >0 failures | Database connection issues |
| HighDailyCost | Warning | >$100/day | Daily spending exceeds budget |
| HighMemoryUsage | Warning | >90% | System memory exhausted |
| HighCPUUsage | Warning | >80% | CPU utilization high |
| LowDiskSpace | Critical | <10% free | Disk space running out |
| ContainerDown | Critical | Service unavailable | Service container stopped |

### Notification Channels

Configure in `alertmanager/alertmanager.yml`:

- **Email**: ops-team@example.com
- **Slack**: #alerts, #critical-alerts, #database-alerts
- **PagerDuty**: For critical alerts

### Runbooks

Each alert includes a runbook URL pointing to resolution steps. Create runbooks at:
- `docs/runbooks/high-error-rate.md`
- `docs/runbooks/slow-response.md`
- `docs/runbooks/aws-failures.md`
- etc.

## Cost Tracking

The system automatically tracks costs for:

### AWS Services
- **S3**: Storage and requests
- **Textract**: Page analysis
- **Comprehend**: Entity detection
- **Bedrock**: Claude API calls (tokens)

### OpenAI Services
- **GPT-4**: Prompt and completion tokens
- **GPT-3.5 Turbo**: Prompt and completion tokens
- **Embeddings**: text-embedding-ada-002

### Viewing Costs

1. **Grafana Dashboard**: Cost Tracking dashboard
2. **Prometheus Query**: `total_cost_usd_daily`
3. **By Service**: `rate(aws_cost_usd_total[1d])`

## Health Checks

### Kubernetes Integration

The application exposes health check endpoints:

```yaml
# Liveness probe
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30

# Readiness probe
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

### Health Check Details

- **/health/live**: Is the application running?
- **/health/ready**: Can the application serve traffic?
  - Checks: Database, AWS services, Redis, disk, memory

## Performance Profiling

### CPU Profiling

```python
from app.monitoring.performance_profiling import profile_function

@profile_function
def expensive_operation():
    # ... code to profile
```

### Memory Profiling

```python
from memory_profiler import profile

@profile
def memory_intensive_operation():
    # ... code to profile
```

## Troubleshooting

### Services Not Starting

```bash
# Check logs
docker-compose logs <service-name>

# Common issues:
# 1. Port conflicts - check if ports are in use
netstat -tulpn | grep -E '3000|9090|16686'

# 2. Insufficient resources
docker stats

# 3. Permission issues
sudo chown -R $(whoami):$(whoami) .
```

### Metrics Not Appearing

1. **Check Prometheus targets**: http://localhost:9090/targets
2. **Verify application metrics endpoint**: http://localhost:8000/metrics
3. **Check scrape configuration** in `prometheus/prometheus.yml`

### Alerts Not Firing

1. **Check Prometheus alerts**: http://localhost:9090/alerts
2. **Verify alert rules** in `prometheus/alerts.yml`
3. **Check Alertmanager** http://localhost:9093

### No Traces in Jaeger

1. **Verify Jaeger is running**: http://localhost:16686
2. **Check application tracing configuration**
3. **Ensure OTEL_EXPORTER_JAEGER_ENDPOINT is set**

## Production Deployment

### Security Checklist

- [ ] Change default Grafana admin password
- [ ] Configure TLS/SSL for all services
- [ ] Set up authentication for Prometheus/Alertmanager
- [ ] Use secrets management (not hardcoded credentials)
- [ ] Configure firewall rules
- [ ] Enable audit logging
- [ ] Set up backup for Grafana dashboards

### Scaling Considerations

- **Prometheus**: Use remote storage (Thanos, Cortex) for long-term retention
- **Loki**: Switch to object storage (S3, GCS) for log retention
- **Jaeger**: Use Elasticsearch or Cassandra backend
- **Grafana**: Enable clustering for high availability

### Environment Variables

```bash
# Production settings
export ENVIRONMENT=production
export PROMETHEUS_RETENTION_DAYS=90
export LOKI_RETENTION_DAYS=31
export GRAFANA_ADMIN_PASSWORD=<secure-password>
export SLACK_WEBHOOK_URL=<your-webhook>
export PAGERDUTY_SERVICE_KEY=<your-key>
```

## Maintenance

### Backup

```bash
# Backup Grafana dashboards and datasources
docker exec grafana grafana-cli admin export-all-dashboards > backup.json

# Backup Prometheus data
docker cp prometheus:/prometheus ./prometheus-backup

# Backup Loki data
docker cp loki:/loki ./loki-backup
```

### Updates

```bash
# Pull latest images
docker-compose pull

# Restart with new images
docker-compose up -d
```

### Cleanup

```bash
# Remove old data
docker-compose exec prometheus promtool tsdb clean-tombstones
docker-compose exec loki rm -rf /loki/chunks/old-*

# Prune Docker resources
docker system prune -a
```

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)

## Support

For issues or questions:
1. Check logs: `docker-compose logs <service>`
2. Review documentation above
3. Contact the DevOps team
