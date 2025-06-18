#!/bin/bash

echo "Starting PostgreSQL MCP Server..."

# 進入專案根目錄
cd "$(dirname "$0")/.."

# Start the PostgreSQL MCP server with database URL
cd apps/servers/src/postgres
if [ ! -d "dist" ]; then
    echo "Building PostgreSQL MCP server..."
    npm run build
fi
node dist/index.js "postgresql://localhost:5432/mcp_test"