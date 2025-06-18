#!/bin/bash
"""
設定 Python 路徑以使用新的 mcp_common 模組
"""

# 設定環境變數
export PYTHONPATH="/Users/yen/Desktop/lineMCP/libs/python:$PYTHONPATH"

# 進入 bot 目錄
cd /Users/yen/Desktop/lineMCP/apps/bot

# 啟動 Poetry 虛擬環境
echo "🚀 啟動 Poetry 虛擬環境..."
poetry shell

echo "✅ Python 路徑已設定："
echo "   PYTHONPATH=$PYTHONPATH"
echo ""
echo "📦 可以開始使用新的 mcp_common 模組："
echo "   from mcp_common.unified_client import get_simple_mcp_client"
echo ""
echo "🧪 執行測試："
echo "   python -c 'from mcp_common import get_mcp_client; print(\"✅ 導入成功\")'"