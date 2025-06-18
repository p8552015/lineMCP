#!/bin/bash

echo "🔧 Setting up PostgreSQL MCP Server"

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL not found. Please install PostgreSQL first:"
    echo "   brew install postgresql"
    exit 1
fi

# Check if pipx is installed
if ! command -v pipx &> /dev/null; then
    echo "📦 Installing pipx..."
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install postgres-mcp
echo "📦 Installing postgres-mcp..."
pipx install postgres-mcp

# Create sample environment file for MCP server
echo "📝 Creating MCP server configuration..."
cat > .env.mcp << EOF
# PostgreSQL Database Configuration
DATABASE_URI=postgresql://username:password@localhost:5432/database_name

# MCP Server Configuration  
PORT=3000
HOST=localhost
ACCESS_MODE=restricted  # Use 'unrestricted' for development, 'restricted' for production

# Optional: Enable extensions (requires superuser privileges)
ENABLE_PG_STAT_STATEMENTS=true
ENABLE_HYPOPG=true
EOF

echo "✅ PostgreSQL MCP Server installation completed!"
echo ""
echo "📋 Next steps:"
echo "1. Update .env.mcp with your PostgreSQL connection details"
echo "2. Start the MCP server: postgres-mcp --config .env.mcp"
echo "3. Update MCP_SERVER_URL in .env if using different port"
echo ""
echo "📖 MCP Server will be available at: http://localhost:3000"
echo "📖 See postgres-mcp documentation for more configuration options"