#!/bin/bash

# ==============================================
# LINE MCP Bot 快速啟動腳本
# 簡化版本，適合開發和測試
# ==============================================

set -e

# 顏色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${PURPLE}🚀 LINE MCP Bot 快速啟動${NC}\n"

# 設置環境
cd "$PROJECT_ROOT/apps/bot"
export PYTHONPATH="$PROJECT_ROOT/apps/bot/src:$PYTHONPATH"

# 快速測試 MCP 連接
echo -e "${BLUE}🧪 快速 MCP 測試...${NC}"
cd "$PROJECT_ROOT"
python3 "$PROJECT_ROOT/scripts/ultimate-stdio-test.py" > /dev/null 2>&1 && echo -e "${GREEN}✅ MCP 連接正常${NC}" || echo -e "${RED}❌ MCP 連接異常${NC}"

# 啟動服務
echo -e "\n${CYAN}🎊 啟動 LINE Bot (開發模式)...${NC}"
cd "$PROJECT_ROOT/apps/bot"

python3 -m uvicorn src.main:app --reload --port 8000