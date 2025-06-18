#!/bin/bash

echo "🐳 Starting PostgreSQL MCP Server with Docker"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

# Pull the latest image
echo "📦 Pulling latest postgres-mcp Docker image..."
docker pull crystaldba/postgres-mcp:latest

# Start the services
echo "🚀 Starting PostgreSQL and MCP Server..."
docker-compose -f docker-compose.mcp.yml up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
if docker-compose -f docker-compose.mcp.yml ps | grep -q "Up"; then
    echo "✅ Services started successfully!"
    echo ""
    echo "📊 Service Information:"
    echo "  - PostgreSQL: localhost:5432"
    echo "    - Username: postgres"
    echo "    - Password: password"
    echo "    - Database: mydb"
    echo ""
    echo "  - MCP Server: http://localhost:3000"
    echo ""
    echo "🔧 To connect your own PostgreSQL database:"
    echo "  1. Stop the containers: docker-compose -f docker-compose.mcp.yml down"
    echo "  2. Edit docker-compose.mcp.yml and update DATABASE_URI"
    echo "  3. Restart: docker-compose -f docker-compose.mcp.yml up -d"
    echo ""
    echo "📝 View logs: docker-compose -f docker-compose.mcp.yml logs -f"
else
    echo "❌ Failed to start services"
    docker-compose -f docker-compose.mcp.yml logs
    exit 1
fi