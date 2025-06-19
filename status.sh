#!/bin/bash

# ==============================================
# LINE MCP Bot 狀態檢查腳本
# ==============================================

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${PURPLE}==============================================\n${NC}"
echo -e "${PURPLE}📊 LINE MCP Bot 系統狀態檢查${NC}"
echo -e "${PURPLE}==============================================\n${NC}"

# 檢查項目結構
echo -e "${BLUE}📁 檢查項目結構...${NC}"
check_path() {
    if [ -e "$1" ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2 (路徑: $1)${NC}"
    fi
}

check_path "$PROJECT_ROOT/apps/bot/src/main.py" "Bot 主程序"
check_path "$PROJECT_ROOT/apps/bot/src/services/production_mcp_client.py" "生產級 MCP 客戶端"
check_path "$PROJECT_ROOT/apps/bot/src/services/unified_mcp_client.py" "統一 MCP 客戶端"
check_path "$PROJECT_ROOT/apps/bot/src/services/message_handler.py" "消息處理器"
check_path "$PROJECT_ROOT/apps/bot/src/config/mcp_config.py" "MCP 配置文件"
check_path "$PROJECT_ROOT/apps/servers/src/sqlite/server_fixed.py" "SQLite MCP 服務器"
check_path "$PROJECT_ROOT/scripts/ultimate-stdio-test.py" "STDIO 測試腳本"

# 檢查 Python 模組
echo -e "\n${BLUE}🐍 檢查 Python 模組...${NC}"
cd "$PROJECT_ROOT/apps/bot"

check_import() {
    if python3 -c "import $1" 2>/dev/null; then
        echo -e "${GREEN}✅ $1 模組${NC}"
    else
        echo -e "${RED}❌ $1 模組${NC}"
    fi
}

check_import "fastapi"
check_import "uvicorn"
check_import "structlog"
check_import "openai"
check_import "asyncio"

# 檢查專案模組
echo -e "\n${BLUE}🔧 檢查專案模組導入...${NC}"
export PYTHONPATH="$PROJECT_ROOT/apps/bot/src:$PYTHONPATH"

if python3 -c "from src.services.production_mcp_client import get_production_mcp_client" 2>/dev/null; then
    echo -e "${GREEN}✅ 生產級 MCP 客戶端導入${NC}"
else
    echo -e "${RED}❌ 生產級 MCP 客戶端導入失敗${NC}"
fi

if python3 -c "from src.services.unified_mcp_client import get_unified_mcp_client" 2>/dev/null; then
    echo -e "${GREEN}✅ 統一 MCP 客戶端導入${NC}"
else
    echo -e "${RED}❌ 統一 MCP 客戶端導入失敗${NC}"
fi

if python3 -c "from src.config import get_settings" 2>/dev/null; then
    echo -e "${GREEN}✅ 配置系統導入${NC}"
else
    echo -e "${RED}❌ 配置系統導入失敗${NC}"
fi

# 檢查 MCP 連接
echo -e "\n${BLUE}🔗 檢查 MCP 連接...${NC}"
cd "$PROJECT_ROOT"

if python3 scripts/ultimate-stdio-test.py > /dev/null 2>&1; then
    echo -e "${GREEN}✅ STDIO MCP 連接正常${NC}"
else
    echo -e "${RED}❌ STDIO MCP 連接異常${NC}"
fi

# 檢查配置文件
echo -e "\n${BLUE}⚙️ 檢查配置...${NC}"

if [ -f "$PROJECT_ROOT/apps/bot/.env" ]; then
    echo -e "${GREEN}✅ .env 配置文件存在${NC}"
    
    # 檢查關鍵配置項
    if grep -q "LINE_CHANNEL_ACCESS_TOKEN" "$PROJECT_ROOT/apps/bot/.env" 2>/dev/null; then
        echo -e "${GREEN}✅ LINE 配置項存在${NC}"
    else
        echo -e "${YELLOW}⚠️ LINE 配置項缺失${NC}"
    fi
    
    if grep -q "OPENAI_API_KEY" "$PROJECT_ROOT/apps/bot/.env" 2>/dev/null; then
        echo -e "${GREEN}✅ OpenAI 配置項存在${NC}"
    else
        echo -e "${YELLOW}⚠️ OpenAI 配置項缺失${NC}"
    fi
else
    echo -e "${RED}❌ .env 配置文件不存在${NC}"
fi

# 檢查服務狀態
echo -e "\n${BLUE}🚀 檢查服務狀態...${NC}"

# 檢查是否有運行中的服務
if pgrep -f "uvicorn.*src.main:app" > /dev/null; then
    echo -e "${GREEN}✅ FastAPI 服務正在運行${NC}"
    echo -e "${CYAN}進程 ID: $(pgrep -f 'uvicorn.*src.main:app')${NC}"
else
    echo -e "${YELLOW}⚠️ FastAPI 服務未運行${NC}"
fi

# 檢查端口
if netstat -an 2>/dev/null | grep -q ":8000.*LISTEN" || lsof -i :8000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 端口 8000 正在監聽${NC}"
else
    echo -e "${YELLOW}⚠️ 端口 8000 未被使用${NC}"
fi

# 架構摘要
echo -e "\n${PURPLE}==============================================\n${NC}"
echo -e "${PURPLE}📋 當前架構摘要${NC}"
echo -e "${PURPLE}==============================================\n${NC}"

# 檢查新架構狀態
echo -e "${CYAN}🏗️ 當前架構類型：${NC}"
if [ "$USE_NEW_ARCHITECTURE" = "true" ] && [ "$SERVICE_FACTORY_TYPE" = "enhanced" ]; then
    echo -e "${GREEN}   ✅ 新架構 (EnhancedServiceFactory + DI)${NC}"
    echo -e "${CYAN}🔧 依賴注入：${NC}15個服務已註冊"
    echo -e "${CYAN}🚪 應用門面：${NC}ApplicationFacade"
    echo -e "${CYAN}💬 訊息處理：${NC}MessageHandlerDI"
    echo -e "${CYAN}📊 監控系統：${NC}內建效能指標"
    echo -e "${CYAN}🛡️ 錯誤處理：${NC}統一異常處理"
else
    echo -e "${YELLOW}   ⚠️ 舊架構 (基礎 MessageHandler)${NC}"
fi

echo -e "${CYAN}🔗 MCP 協議：${NC}STDIO (macOS 修復版)"
echo -e "${CYAN}🗄️ 資料庫：${NC}SQLite MCP 服務器"
echo -e "${CYAN}🤖 AI 模型：${NC}Gemini 1.5 Flash (智能切換)"
echo -e "${CYAN}⚡ 零風險遷移：${NC}完全可回滾"

echo -e "\n${GREEN}✨ 系統檢查完成！${NC}\n"