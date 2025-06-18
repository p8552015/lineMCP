#!/bin/bash

echo "🚀 啟動 LINE MCP Webhook 系統..."
echo "======================================="

# 進入專案根目錄
PROJECT_ROOT="$(dirname "$0")/.."
cd "$PROJECT_ROOT"

# 設定顏色輸出
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# 檢查基本目錄結構
echo "🔍 檢查專案結構..."
required_dirs=("apps/bot" "apps/servers/src/sqlite" "libs/python/mcp_common")
for dir in "${required_dirs[@]}"; do
    if [ ! -d "$dir" ]; then
        echo -e "${RED}❌ 錯誤: 找不到目錄 $dir${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ 專案結構檢查完成${NC}"

# 創建日誌目錄
mkdir -p apps/bot/logs
mkdir -p logs

# 檢查 Python 和必要依賴
echo "🐍 檢查 Python 環境..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 未安裝${NC}"
    exit 1
fi

# 檢查關鍵 Python 模組
echo "📦 檢查 Python 依賴..."
cd apps/bot
missing_deps=()

# 檢查核心依賴
echo "  🔍 檢查核心模組..."
python3 -c "import fastapi, uvicorn, mcp, structlog, pydantic" 2>/dev/null || missing_deps+=("核心模組")
python3 -c "import opentelemetry.trace, opentelemetry.sdk" 2>/dev/null || missing_deps+=("OpenTelemetry")
python3 -c "import linebot.v3" 2>/dev/null || missing_deps+=("LINE Bot SDK")

if [ ${#missing_deps[@]} -gt 0 ]; then
    echo -e "${RED}❌ 缺少依賴: ${missing_deps[*]}${NC}"
    echo ""
    echo -e "${YELLOW}請手動安裝缺少的依賴：${NC}"
    echo -e "${BLUE}python3 -m pip install fastapi uvicorn mcp structlog pydantic line-bot-sdk \\${NC}"
    echo -e "${BLUE}    opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi \\${NC}"
    echo -e "${BLUE}    opentelemetry-exporter-otlp redis httpx tenacity${NC}"
    echo ""
    echo -e "${YELLOW}或者使用項目的 requirements 文件（如果存在）${NC}"
    cd ../..
    exit 1
else
    echo -e "${GREEN}✅ Python 依賴檢查完成${NC}"
fi

cd ../..

# 檢查環境變數
echo "🔧 檢查環境設定..."
if [ -z "$LINE_CHANNEL_ACCESS_TOKEN" ] || [ -z "$LINE_CHANNEL_SECRET" ]; then
    echo -e "${YELLOW}⚠️ 警告: LINE 環境變數未設定${NC}"
    echo "   請確保設定了 LINE_CHANNEL_ACCESS_TOKEN 和 LINE_CHANNEL_SECRET"
fi

# 檢查 SQLite 資料庫
DB_PATH="apps/servers/src/sqlite/test.db"
if [ ! -f "$DB_PATH" ]; then
    echo -e "${YELLOW}⚠️ 警告: SQLite 資料庫檔案不存在: $DB_PATH${NC}"
    echo "   系統將嘗試連接到預設位置的資料庫"
fi

# 清理環境函數
cleanup_environment() {
    echo "🧹 清理舊進程..."
    
    # 具體進程清理
    local processes=("mcp_server_sqlite" "uvicorn.*src.main" "python.*main.py" "ngrok")
    
    for process in "${processes[@]}"; do
        if pgrep -f "$process" > /dev/null; then
            echo -e "  🔌 停止 ${BLUE}$process${NC}..."
            pkill -f "$process" 2>/dev/null
        fi
    done
    
    # 等待進程完全停止
    sleep 2
    
    # 檢查端口並強制釋放如果需要
    for port in 8000; do
        if lsof -i :$port >/dev/null 2>&1; then
            echo -e "  ⚠️ 端口 ${YELLOW}$port${NC} 仍被占用，嘗試釋放..."
            lsof -ti :$port | xargs kill -9 2>/dev/null || true
        fi
    done
    
    echo -e "${GREEN}✅ 環境清理完成${NC}"
}

# 檢查服務狀態函數
check_service_status() {
    local service_name="$1"
    local port="$2"
    local url="$3"
    local timeout="${4:-5}"
    
    echo -e "  🔍 檢查 ${BLUE}$service_name${NC}..."
    
    # 檢查端口
    if ! lsof -i :$port >/dev/null 2>&1; then
        echo -e "    ${RED}❌ 端口 $port 未被使用${NC}"
        return 1
    fi
    
    # 檢查 HTTP 連接（如果提供了 URL）
    if [ -n "$url" ]; then
        if ! curl -s --max-time $timeout "$url" >/dev/null 2>&1; then
            echo -e "    ${YELLOW}⚠️ HTTP 連接失敗: $url${NC}"
            return 1
        fi
    fi
    
    echo -e "    ${GREEN}✅ $service_name 運行正常${NC}"
    return 0
}


# 啟動 LINE Webhook 服務
start_webhook_service() {
    echo -e "🌐 啟動 ${BLUE}LINE Webhook Service${NC} (端口 8000)..."
    
    cd apps/bot
    
    # 測試模組導入
    echo "  🧪 測試模組導入..."
    if ! python3 -c "
from src.config import get_settings
from src.services.message_handler import MessageHandler
from src.routes.webhook import router
from src.main import app
print('✅ 所有模組導入成功')
" 2>/dev/null; then
        echo -e "  ${RED}❌ 模組導入測試失敗${NC}"
        echo "  📝 檢查依賴和模組路徑"
        cd ../..
        return 1
    fi
    
    # 確保日誌目錄存在
    mkdir -p logs
    
    # 啟動 Webhook 服務
    nohup python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload > logs/webhook.log 2>&1 &
    WEBHOOK_PID=$!
    echo -e "  📋 PID: ${BLUE}$WEBHOOK_PID${NC}, 日誌: logs/webhook.log"
    
    cd ../..
    sleep 8
    
    # 檢查 webhook 服務
    if check_service_status "LINE Webhook" "8000" "http://localhost:8000/health" 10; then
        return 0
    else
        return 1
    fi
}

# 開始執行
cleanup_environment

echo ""
echo "🚀 啟動各項服務..."
echo "======================================="

# 驗證 SQLite MCP 可用性 (由 TrueMCPClient 管理)
echo -e "🗃️ 驗證 ${BLUE}SQLite MCP Server${NC} 可用性..."
cd apps/servers/src/sqlite
if [ -d "src/mcp_server_sqlite" ] && [ -f "test.db" ]; then
    echo -e "  ✅ SQLite MCP Server 模組可用"
    echo -e "  ✅ 資料庫檔案存在: test.db"
    SQLITE_STATUS="✅"
else
    echo -e "  ❌ SQLite MCP Server 不可用"
    SQLITE_STATUS="❌"
fi
cd ../../../..

# 啟動 LINE Webhook 服務
if start_webhook_service; then
    WEBHOOK_STATUS="✅"
else
    WEBHOOK_STATUS="❌"
fi

echo ""
echo "📊 系統狀態總覽"
echo "======================================="

# 顯示各服務狀態
echo "🔧 服務狀態:"
echo -e "  $SQLITE_STATUS ${BLUE}SQLite MCP Server${NC} (可用性)"
echo -e "  $WEBHOOK_STATUS ${BLUE}LINE Webhook Service${NC} (端口 8000)"

# 檢查進程狀態
echo ""
echo "🔍 運行中的進程:"
running_processes=$(ps aux | grep -E "(mcp_server_sqlite|uvicorn.*src.main)" | grep -v grep)
if [ -n "$running_processes" ]; then
    echo "$running_processes" | while read line; do
        echo -e "  ${GREEN}✅${NC} $line"
    done
else
    echo -e "  ${YELLOW}⚠️ 沒有找到運行中的 MCP 相關進程${NC}"
fi

# 端口占用檢查
echo ""
echo "🔍 端口占用情況:"
for port in 8000; do
    if lsof -i :$port >/dev/null 2>&1; then
        process_info=$(lsof -i :$port | tail -1 | awk '{print $1, $2}')
        echo -e "  ${GREEN}✅${NC} 端口 $port: $process_info"
    else
        echo -e "  ${RED}❌${NC} 端口 $port: 未使用"
    fi
done

# SQLite MCP Server 可用性檢查
echo ""
echo "🔍 MCP Server 可用性:"
if [ -d "apps/servers/src/sqlite/src/mcp_server_sqlite" ] && [ -f "apps/servers/src/sqlite/test.db" ]; then
    echo -e "  ${GREEN}✅${NC} SQLite MCP Server: 模組和資料庫可用 (由 TrueMCPClient 管理)"
else
    echo -e "  ${RED}❌${NC} SQLite MCP Server: 模組或資料庫不可用"
fi

# 資料庫連接測試
echo ""
echo "🗃️ 資料庫連接測試:"

# SQLite 測試
if [ -f "$DB_PATH" ]; then
    if sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM sqlite_master WHERE type='table'" >/dev/null 2>&1; then
        table_count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM sqlite_master WHERE type='table'" 2>/dev/null || echo "unknown")
        echo -e "  ${GREEN}✅${NC} SQLite: 連接正常 (${table_count} 個資料表)"
    else
        echo -e "  ${RED}❌${NC} SQLite: 連接失敗 ($DB_PATH)"
    fi
else
    echo -e "  ${YELLOW}⚠️${NC} SQLite: 資料庫檔案不存在 ($DB_PATH)"
fi

echo ""
echo "======================================="

# 檢查是否所有核心服務都成功啟動
core_services_ok=true
if [ "$WEBHOOK_STATUS" != "✅" ]; then
    core_services_ok=false
fi

if [ "$core_services_ok" = true ]; then
    echo -e "${GREEN}✅ 系統啟動完成！核心服務運行正常${NC}"
else
    echo -e "${YELLOW}⚠️ 系統啟動完成，但部分服務可能有問題${NC}"
    echo "   請檢查日誌檔案以獲取詳細錯誤資訊"
fi

echo ""
echo "📋 下一步操作:"
echo ""
echo "1️⃣ 設定 ngrok 隧道 (如果尚未設定):"
echo -e "   ${BLUE}ngrok http 8000${NC}"
echo ""
echo "2️⃣ 配置 LINE Developer Console:"
echo "   - 登入: https://developers.line.biz/"
echo "   - 更新 Webhook URL: https://[ngrok-url]/Webhook"
echo "   - 啟用 webhook 並驗證"
echo ""
echo "3️⃣ 測試 LINE Bot 功能:"
echo -e "   ${BLUE}故障統計${NC}"
echo -e "   ${BLUE}/sql SELECT * FROM machines LIMIT 5${NC}"
echo -e "   ${BLUE}/tables${NC}"
echo -e "   ${BLUE}/status${NC}"
echo ""
echo "4️⃣ 本地測試指令:"
echo -e "   ${BLUE}curl -X GET http://localhost:8000/health${NC}"
echo ""
echo "🔍 監控指令:"
echo "   # 查看即時日誌"
echo -e "   ${BLUE}tail -f apps/bot/logs/webhook.log${NC}"
echo -e "   ${BLUE}tail -f apps/bot/logs/sqlite-mcp.log${NC}"
echo ""
echo "   # 檢查系統狀態"
echo -e "   ${BLUE}./scripts/status-check.sh${NC}    # (如果存在)"
echo ""
echo "   # 停止所有服務"
echo -e "   ${BLUE}./scripts/stop-all.sh${NC}"
echo ""

# 提供架構資訊
echo "🏗️ 系統架構:"
echo "   LINE Bot → Webhook → MessageHandler → SimpleMCPClient"
echo "                                           ↓"
echo "                                      UnifiedMCPClient"
echo "                                           ↓"
echo "                                      TrueMCPClient"
echo "                                           ↓"
echo "                                  SQLite MCP Server (STDIO)"
echo "                                           ↓"
echo "                                      SQLite Database"
echo ""