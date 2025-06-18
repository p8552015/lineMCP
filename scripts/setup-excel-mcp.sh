#!/bin/bash

echo "🔧 Setting up Excel MCP Server"

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.10"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
    echo "❌ Python 3.10+ is required. Current version: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Install uvx if not installed
if ! command -v uvx &> /dev/null; then
    echo "📦 Installing uvx..."
    pip3 install uvx
fi

# Create Excel files directory
echo "📁 Creating Excel files directory..."
mkdir -p excel_files

# Start Excel MCP Server in SSE mode
echo "🚀 Starting Excel MCP Server in SSE mode..."
export EXCEL_FILES_PATH="./excel_files"
export FASTMCP_PORT=3000

cat > start-excel-mcp.sh << 'EOF'
#!/bin/bash
export EXCEL_FILES_PATH="./excel_files"
export FASTMCP_PORT=3000
uvx excel-mcp-server sse
EOF

chmod +x start-excel-mcp.sh

echo "✅ Excel MCP Server setup completed!"
echo ""
echo "📋 To start the server:"
echo "   ./start-excel-mcp.sh"
echo ""
echo "📊 The server will:"
echo "   - Run on http://localhost:3000/sse"
echo "   - Store Excel files in ./excel_files/"
echo ""
echo "🔧 Update your .env file:"
echo "   MCP_SERVER_URL=http://localhost:3000"