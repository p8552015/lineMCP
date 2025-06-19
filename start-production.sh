#!/bin/bash

# ==============================================
# LINE MCP Bot 生產級啟動腳本
# 基於簡化後的架構設計
# ==============================================

set -e  # 遇到錯誤立即退出

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 項目根目錄
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_DIR="$PROJECT_ROOT/apps/bot"
SERVERS_DIR="$PROJECT_ROOT/apps/servers"

echo -e "${PURPLE}==============================================\n${NC}"
echo -e "${PURPLE}🚀 LINE MCP Bot 生產級啟動器${NC}"
echo -e "${PURPLE}==============================================\n${NC}"

# 函數：檢查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}❌ 缺少必要命令：$1${NC}"
        return 1
    fi
}

# 函數：檢查 Python 環境
check_python_env() {
    echo -e "${BLUE}🔍 檢查 Python 環境...${NC}"
    
    check_command python3
    check_command pip3
    
    # 檢查 Python 版本
    python_version=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✅ Python 版本：$python_version${NC}"
    
    # 檢查是否在虛擬環境中
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        echo -e "${GREEN}✅ 已在虛擬環境：$VIRTUAL_ENV${NC}"
    else
        echo -e "${YELLOW}⚠️ 未檢測到虛擬環境${NC}"
    fi
}

# 函數：檢查依賴快取
check_dependency_cache() {
    local cache_file="$PROJECT_ROOT/.dependency-cache"
    
    if [ -f "$cache_file" ]; then
        local last_check=$(grep -E '^[0-9]+:' "$cache_file" 2>/dev/null | tail -1 | cut -d: -f1)
        local current_time=$(date +%s)
        
        # 如果上次檢查在 1 小時內，則跳過檢查
        if [ -n "$last_check" ] && [ "$last_check" -gt 0 ] 2>/dev/null && [ $((current_time - last_check)) -lt 3600 ]; then
            echo -e "${GREEN}✅ 依賴快取有效（1小時內已檢查）${NC}"
            return 0
        fi
    fi
    
    return 1
}

# 函數：更新依賴快取
update_dependency_cache() {
    local cache_file="$PROJECT_ROOT/.dependency-cache"
    local current_time=$(date +%s)
    local deps_hash=$(python3 -c "import sys; print(hash(str(sys.path)))" 2>/dev/null || echo "0")
    
    echo "$current_time:$deps_hash" >> "$cache_file"
    
    # 保持快取文件不超過 10 行
    if [ -f "$cache_file" ]; then
        tail -10 "$cache_file" > "$cache_file.tmp" && mv "$cache_file.tmp" "$cache_file"
    fi
}

# 函數：檢查依賴是否已安裝
check_dependencies() {
    echo -e "\n${BLUE}🔍 檢查依賴狀態...${NC}"
    
    # 檢查快取
    if check_dependency_cache; then
        return 0
    fi
    
    # 檢查核心 Python 依賴
    local missing_deps=()
    
    echo -e "${CYAN}檢查核心依賴...${NC}"
    python3 -c "import fastapi, uvicorn, structlog, openai" 2>/dev/null || missing_deps+=("core")
    python3 -c "import mcp" 2>/dev/null || missing_deps+=("mcp")
    
    if [ ${#missing_deps[@]} -eq 0 ]; then
        echo -e "${GREEN}✅ 所有核心依賴已安裝${NC}"
        update_dependency_cache
        return 0
    else
        echo -e "${YELLOW}⚠️ 缺少依賴：${missing_deps[*]}${NC}"
        return 1
    fi
}

# 函數：智能安裝依賴
install_dependencies() {
    # 先檢查是否需要安裝
    if check_dependencies; then
        echo -e "${GREEN}✅ 依賴檢查通過，跳過安裝${NC}"
        return 0
    fi
    
    echo -e "\n${BLUE}📦 安裝 Bot 依賴...${NC}"
    cd "$BOT_DIR"
    
    if [ -f "pyproject.toml" ]; then
        echo -e "${CYAN}使用 Poetry 安裝依賴...${NC}"
        if command -v poetry &> /dev/null; then
            # 檢查是否已安裝
            if poetry check &>/dev/null && [ -d ".venv" ] || poetry env info &>/dev/null; then
                echo -e "${GREEN}✅ Poetry 環境已存在，檢查更新...${NC}"
                poetry install --only=main --sync 2>/dev/null || poetry install
            else
                echo -e "${CYAN}首次安裝 Poetry 依賴...${NC}"
                poetry install --only=main 2>/dev/null || poetry install
            fi
        else
            echo -e "${YELLOW}⚠️ 未安裝 Poetry，使用 pip 安裝...${NC}"
            pip3 install -r requirements.txt 2>/dev/null || echo -e "${YELLOW}requirements.txt 不存在，跳過${NC}"
        fi
    else
        pip3 install -r requirements.txt 2>/dev/null || echo -e "${YELLOW}requirements.txt 不存在，跳過${NC}"
    fi
    
    # 檢查 SQLite Server 是否已安裝
    echo -e "\n${BLUE}📦 檢查 SQLite Server 依賴...${NC}"
    if python3 -c "import mcp_server_sqlite" 2>/dev/null; then
        echo -e "${GREEN}✅ SQLite Server 已安裝${NC}"
    else
        echo -e "${CYAN}安裝 SQLite Server...${NC}"
        cd "$SERVERS_DIR/src/sqlite"
        pip3 install -e . 2>/dev/null || echo -e "${YELLOW}⚠️ SQLite Server 安裝可能有問題${NC}"
    fi
}

# 函數：檢查配置文件
check_config() {
    echo -e "\n${BLUE}🔧 檢查配置文件...${NC}"
    
    # 檢查 .env 文件
    if [ ! -f "$BOT_DIR/.env" ]; then
        echo -e "${RED}❌ 缺少 .env 文件${NC}"
        echo -e "${CYAN}創建示例 .env 文件...${NC}"
        cat > "$BOT_DIR/.env" << 'EOF'
# LINE Configuration
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here
LINE_CHANNEL_SECRET=your_line_channel_secret_here

# OpenAI Configuration  
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o
OPENAI_MAX_TOKENS=1000
OPENAI_TEMPERATURE=0.7

# MCP Configuration
MCP_SERVER_URL=http://localhost:3000
MCP_API_KEY=your_mcp_api_key_here

# JWT Configuration
JWT_SECRET_KEY=your_very_secure_secret_key_here

# Application
APP_ENV=production
APP_DEBUG=false
APP_PORT=8000
EOF
        echo -e "${YELLOW}⚠️ 請編輯 $BOT_DIR/.env 文件並填入正確的配置值${NC}"
        return 1
    else
        echo -e "${GREEN}✅ .env 文件存在${NC}"
    fi
    
    # 檢查 MCP 配置
    if [ ! -f "$BOT_DIR/src/config/mcp_config.py" ]; then
        echo -e "${RED}❌ MCP 配置文件不存在${NC}"
        return 1
    else
        echo -e "${GREEN}✅ MCP 配置文件存在${NC}"
    fi
}

# 函數：測試 MCP 連接
test_mcp_connection() {
    echo -e "\n${BLUE}🧪 測試 MCP 連接...${NC}"
    cd "$BOT_DIR"
    
    # 使用統一客戶端進行快速連接測試
    echo -e "${CYAN}運行 MCP 統一客戶端連接測試...${NC}"
    
    python3 -c "
import asyncio
import sys
import os
sys.path.insert(0, 'src')
from src.services.unified_mcp_client import get_unified_mcp_client

async def test_connection():
    try:
        print('🔗 初始化統一 MCP 客戶端...')
        client = await get_unified_mcp_client()
        
        print('📋 測試工具列表...')
        tools_result = await client.list_tools('sqlite')
        
        if tools_result.get('success'):
            tools = tools_result.get('tools', [])
            print(f'✅ 成功獲取 {len(tools)} 個可用工具')
            for tool in tools[:3]:  # 只顯示前3個
                print(f'   - {tool.get(\"name\", \"未知工具\")}')
            if len(tools) > 3:
                print(f'   ... 還有 {len(tools)-3} 個工具')
        else:
            print(f'❌ 獲取工具列表失敗: {tools_result.get(\"error\")}')
            return False
            
        print('🔍 測試簡單查詢...')
        test_result = await client.call_tool('sqlite', 'list_tables', {})
        
        if test_result.get('success'):
            print('✅ 簡單查詢測試通過')
        else:
            print(f'❌ 簡單查詢測試失敗: {test_result.get(\"error\")}')
            return False
            
        print('🧹 清理連接...')
        await client.close()
        print('✅ MCP 連接測試完全通過')
        return True
        
    except Exception as e:
        print(f'❌ 連接測試異常: {e}')
        return False

# 執行測試
result = asyncio.run(test_connection())
sys.exit(0 if result else 1)
" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ MCP 統一客戶端連接測試通過${NC}"
    else
        echo -e "${RED}❌ MCP 統一客戶端連接測試失敗${NC}"
        echo -e "${YELLOW}💡 嘗試使用詳細模式再次測試...${NC}"
        
        # 詳細模式測試
        python3 -c "
import asyncio
import sys
sys.path.insert(0, 'src')
from src.services.unified_mcp_client import get_unified_mcp_client

async def detailed_test():
    try:
        client = await get_unified_mcp_client()
        print('📊 客戶端類型:', client.client_type)
        
        # 更詳細的錯誤信息
        tools_result = await client.list_tools('sqlite')
        print('📋 工具列表結果:', tools_result)
        
        await client.close()
        return tools_result.get('success', False)
    except Exception as e:
        print('❌ 詳細測試異常:', str(e))
        import traceback
        traceback.print_exc()
        return False

result = asyncio.run(detailed_test())
sys.exit(0 if result else 1)
"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ 詳細測試通過${NC}"
        else
            echo -e "${RED}❌ 詳細測試也失敗，但服務仍可啟動${NC}"
            echo -e "${YELLOW}⚠️ 建議檢查 MCP 服務器配置${NC}"
        fi
    fi
}

# 函數：啟動服務
start_services() {
    echo -e "\n${BLUE}🚀 啟動 LINE Bot 服務...${NC}"
    cd "$BOT_DIR"
    
    # 設置 PYTHONPATH
    export PYTHONPATH="$BOT_DIR/src:$PYTHONPATH"
    
    echo -e "${CYAN}當前架構概覽：${NC}"
    echo -e "  📁 Bot 服務：$BOT_DIR"
    echo -e "  🗄️ SQLite 服務：$SERVERS_DIR/src/sqlite"
    echo -e "  🔗 連接方式：STDIO (生產級修復版)"
    echo -e "  🛠️ MCP 客戶端：production_mcp_client.py (核心實作)"
    echo -e "  ⚙️ 統一介面：unified_mcp_client.py (單一入口)"
    echo -e "  🤖 AI 模型：Gemini 1.5 Flash + OpenAI GPT-4o-mini"
    echo -e "  🧠 自然語言：規則優先 + AI 增強"
    
    echo -e "\n${GREEN}🎊 準備啟動 FastAPI 應用...${NC}"
    echo -e "${YELLOW}使用 Ctrl+C 停止服務${NC}\n"
    
    # 啟動 FastAPI 應用
    python3 -m uvicorn src.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        --log-level info
}

# 函數：顯示幫助信息
show_help() {
    echo -e "${PURPLE}使用方法：${NC}"
    echo -e "  $0 [選項]"
    echo -e ""
    echo -e "${PURPLE}選項：${NC}"
    echo -e "  ${GREEN}start${NC}          啟動完整服務 (預設)"
    echo -e "  ${GREEN}test${NC}           僅測試 MCP 連接"
    echo -e "  ${GREEN}install${NC}        智能安裝依賴（跳過已安裝）"
    echo -e "  ${GREEN}install-force${NC}  強制重新安裝所有依賴"
    echo -e "  ${GREEN}config${NC}         檢查配置文件"
    echo -e "  ${GREEN}help${NC}           顯示此幫助信息"
    echo -e ""
    echo -e "${PURPLE}示例：${NC}"
    echo -e "  $0                # 完整啟動流程"
    echo -e "  $0 test           # 僅測試連接"
    echo -e "  $0 install        # 智能安裝依賴"
    echo -e "  $0 install-force  # 強制重新安裝"
    echo -e ""
    echo -e "${PURPLE}智能安裝特性：${NC}"
    echo -e "  • 自動檢查依賴是否已安裝"
    echo -e "  • 1小時內快取檢查結果"
    echo -e "  • 僅安裝缺失的依賴"
    echo -e "  • 支援 Poetry 環境檢測"
}

# 函數：完整啟動流程
full_startup() {
    check_python_env
    install_dependencies
    check_config || exit 1
    
    # MCP 連接測試失敗不會阻止啟動，因為服務可能仍可運行
    if ! test_mcp_connection; then
        echo -e "${YELLOW}⚠️ MCP 連接測試失敗，但繼續啟動服務${NC}"
        echo -e "${YELLOW}💡 服務啟動後將自動重試 MCP 連接${NC}"
    fi
    
    start_services
}

# 主邏輯
case "${1:-start}" in
    "start")
        full_startup
        ;;
    "test")
        echo -e "${BLUE}🧪 僅執行連接測試${NC}"
        test_mcp_connection
        ;;
    "install")
        echo -e "${BLUE}📦 僅安裝依賴${NC}"
        check_python_env
        install_dependencies
        ;;
    "install-force")
        echo -e "${BLUE}📦 強制重新安裝依賴${NC}"
        # 清除快取，強制重新安裝
        rm -f "$PROJECT_ROOT/.dependency-cache"
        check_python_env
        install_dependencies
        ;;
    "config")
        echo -e "${BLUE}🔧 僅檢查配置${NC}"
        check_config
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo -e "${RED}❌ 未知選項：$1${NC}"
        show_help
        exit 1
        ;;
esac