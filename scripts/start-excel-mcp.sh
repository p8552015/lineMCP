#!/bin/bash
export EXCEL_FILES_PATH="./excel_files"
export FASTMCP_PORT=3000
uvx excel-mcp-server sse
