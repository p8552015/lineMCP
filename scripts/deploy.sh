#!/bin/bash

set -e

echo "🚀 Starting LINE MCP Webhook Deployment"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy .env.example to .env and configure your settings."
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check required environment variables
required_vars=(
    "LINE_CHANNEL_ACCESS_TOKEN"
    "LINE_CHANNEL_SECRET"
    "OPENAI_API_KEY"
    "MCP_SERVER_URL"
    "MCP_API_KEY"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Error: $var is not set in .env file!"
        exit 1
    fi
done

echo "✅ Environment variables validated"

# Build Docker image
echo "🔨 Building Docker image..."
docker-compose build

# Start services
echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check health
echo "🏥 Checking service health..."
health_check=$(curl -s http://localhost:8000/health | jq -r '.status' 2>/dev/null || echo "failed")

if [ "$health_check" = "healthy" ]; then
    echo "✅ Service is healthy!"
else
    echo "❌ Health check failed!"
    echo "Checking logs..."
    docker-compose logs --tail=50 webhook
    exit 1
fi

echo "✅ Deployment completed successfully!"
echo ""
echo "📊 Services running:"
echo "  - Webhook API: http://localhost:8000"
echo "  - Prometheus: http://localhost:9090"
echo "  - Grafana: http://localhost:3000 (admin/admin)"
echo ""
echo "📝 Logs: docker-compose logs -f webhook"
echo "🛑 Stop: docker-compose down"