#!/bin/bash

echo "Starting Context7 MCP Server..."
export CONTEXT7_PORT=3001
context7-mcp --transport sse --port 3001