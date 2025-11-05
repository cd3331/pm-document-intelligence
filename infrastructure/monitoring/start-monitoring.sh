#!/bin/bash
# Start the PM Document Intelligence monitoring stack

set -e

echo "==================================================="
echo "PM Document Intelligence - Monitoring Stack Startup"
echo "==================================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed. Please install docker-compose and try again."
    exit 1
fi

# Navigate to monitoring directory
cd "$(dirname "$0")"

echo "Step 1/4: Creating required directories..."
mkdir -p grafana/dashboards
mkdir -p grafana/provisioning/datasources
mkdir -p grafana/provisioning/dashboards
mkdir -p prometheus
mkdir -p alertmanager
mkdir -p loki
mkdir -p promtail
echo "✓ Directories created"
echo ""

echo "Step 2/4: Exporting Grafana dashboards..."
if [ -f "export_dashboards.py" ]; then
    python3 export_dashboards.py
    if [ $? -eq 0 ]; then
        echo "✓ Dashboards exported successfully"
    else
        echo "⚠ Dashboard export failed, but continuing..."
    fi
else
    echo "⚠ export_dashboards.py not found, skipping..."
fi
echo ""

echo "Step 3/4: Starting Docker containers..."
docker-compose up -d
echo "✓ Containers started"
echo ""

echo "Step 4/4: Waiting for services to be ready..."
sleep 5

# Check if services are running
echo ""
echo "Service Status:"
echo "---------------"
docker-compose ps
echo ""

echo "==================================================="
echo "Monitoring Stack Started Successfully!"
echo "==================================================="
echo ""
echo "Access the following services:"
echo ""
echo "📊 Grafana (Dashboards):         http://localhost:3000"
echo "   Default login: admin / admin"
echo ""
echo "📈 Prometheus (Metrics):         http://localhost:9090"
echo "🔔 Alertmanager (Alerts):        http://localhost:9093"
echo "🔍 Jaeger (Tracing):             http://localhost:16686"
echo "📝 Loki (Logs):                  http://localhost:3100"
echo "💾 Redis Commander:              http://localhost:8081"
echo "📦 cAdvisor (Containers):        http://localhost:8080"
echo "☁️  LocalStack (AWS Sim):         http://localhost:4566"
echo ""
echo "==================================================="
echo ""
echo "Useful commands:"
echo "  View logs:        docker-compose logs -f [service-name]"
echo "  Stop stack:       docker-compose down"
echo "  Restart service:  docker-compose restart [service-name]"
echo "  Service status:   docker-compose ps"
echo ""
echo "For more information, see README.md"
echo ""
