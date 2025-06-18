#!/bin/bash

echo "🛑 關閉 LINE MCP Webhook 系統..."
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

# 查找運行中的服務函數
find_running_services() {
    echo "🔍 查找運行中的服務..."
    
    # 定義要查找的進程模式
    local patterns=(
        "mcp_server_sqlite" 
        "uvicorn.*src.main"
        "python.*main.py"
        "fastapi"
        "ngrok"
    )
    
    local found_any=false
    
    for pattern in "${patterns[@]}"; do
        local processes=$(ps aux | grep -E "$pattern" | grep -v grep)
        if [ -n "$processes" ]; then
            if [ "$found_any" = false ]; then
                echo ""
                echo "將停止以下服務:"
                echo "----------------------------------------"
                found_any=true
            fi
            echo "$processes" | while read line; do
                local pid=$(echo "$line" | awk '{print $2}')
                local cmd=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}')
                echo -e "  📋 PID ${BLUE}$pid${NC}: ${cmd:0:60}..."
            done
        fi
    done
    
    if [ "$found_any" = false ]; then
        echo -e "${GREEN}ℹ️ 沒有找到運行中的相關服務${NC}"
        return 1
    fi
    
    return 0
}

# 停止服務的函數
stop_service() {
    local service_name="$1"
    local process_pattern="$2"
    local force_kill="${3:-false}"
    
    echo -e "  🔌 停止 ${BLUE}$service_name${NC}..."
    
    # 查找匹配的進程
    local pids=$(pgrep -f "$process_pattern" 2>/dev/null)
    
    if [ -z "$pids" ]; then
        echo -e "    ${GREEN}ℹ️ 無 $service_name 進程運行${NC}"
        return 0
    fi
    
    echo -e "    📋 找到進程: ${BLUE}$pids${NC}"
    
    # 嘗試優雅停止
    if pkill -TERM -f "$process_pattern" 2>/dev/null; then
        echo -e "    ⏳ 發送 ${YELLOW}SIGTERM${NC} 信號..."
        
        # 等待進程停止
        local wait_count=0
        while [ $wait_count -lt 10 ]; do
            if ! pgrep -f "$process_pattern" >/dev/null 2>&1; then
                echo -e "    ${GREEN}✅ $service_name 進程已停止${NC}"
                return 0
            fi
            sleep 1
            wait_count=$((wait_count + 1))
        done
        
        # 如果優雅停止失敗，強制終止
        echo -e "    ${YELLOW}⚠️ 優雅停止失敗，嘗試強制終止...${NC}"
        if pkill -KILL -f "$process_pattern" 2>/dev/null; then
            sleep 2
            if ! pgrep -f "$process_pattern" >/dev/null 2>&1; then
                echo -e "    ${GREEN}✅ $service_name 進程已強制停止${NC}"
                return 0
            else
                echo -e "    ${RED}❌ $service_name 進程停止失敗${NC}"
                return 1
            fi
        fi
    else
        echo -e "    ${RED}❌ 無法停止 $service_name${NC}"
        return 1
    fi
}

# 檢查並釋放端口
release_ports() {
    echo ""
    echo "🔍 檢查端口狀態..."
    
    local ports=(3003 8000 4040)  # SQLite MCP, Webhook, ngrok 的預設端口
    local ports_in_use=()
    
    for port in "${ports[@]}"; do
        if lsof -i :$port >/dev/null 2>&1; then
            local process_info=$(lsof -i :$port | tail -1)
            local pid=$(echo "$process_info" | awk '{print $2}')
            local name=$(echo "$process_info" | awk '{print $1}')
            
            echo -e "  ${YELLOW}⚠️${NC} 端口 ${BLUE}$port${NC}: 被進程 ${BLUE}$name${NC} (PID: ${BLUE}$pid${NC}) 占用"
            ports_in_use+=("$port:$pid")
        else
            echo -e "  ${GREEN}✅${NC} 端口 ${BLUE}$port${NC}: 已釋放"
        fi
    done
    
    # 如果有端口仍被占用，嘗試強制釋放
    if [ ${#ports_in_use[@]} -gt 0 ]; then
        echo ""
        echo -e "${YELLOW}⚠️ 發現 ${#ports_in_use[@]} 個端口仍被占用${NC}"
        echo "🔧 嘗試強制釋放被占用的端口..."
        
        for port_pid in "${ports_in_use[@]}"; do
            local port=$(echo "$port_pid" | cut -d: -f1)
            local pid=$(echo "$port_pid" | cut -d: -f2)
            
            echo -e "  🔌 強制釋放端口 ${BLUE}$port${NC} (PID: ${BLUE}$pid${NC})..."
            if kill -9 "$pid" 2>/dev/null; then
                sleep 1
                if ! lsof -i :$port >/dev/null 2>&1; then
                    echo -e "    ${GREEN}✅ 端口 $port 已釋放${NC}"
                else
                    echo -e "    ${RED}❌ 端口 $port 釋放失敗${NC}"
                fi
            else
                echo -e "    ${RED}❌ 無法終止進程 $pid${NC}"
            fi
        done
    fi
}

# 清理日誌檔案函數
cleanup_logs() {
    echo ""
    echo "🧹 清理日誌檔案..."
    
    local log_files=(
        "apps/bot/logs/webhook.log"
        "apps/bot/logs/sqlite-mcp.log"
    )
    
    for log_file in "${log_files[@]}"; do
        if [ -f "$log_file" ]; then
            # 保留最後 1000 行
            if [ -s "$log_file" ]; then
                tail -1000 "$log_file" > "${log_file}.tmp" && mv "${log_file}.tmp" "$log_file"
                echo -e "  ${GREEN}🗂️ 已清理 $log_file${NC}"
            fi
        fi
    done
}

# 驗證停止狀態
verify_shutdown() {
    echo ""
    echo "🔍 驗證關閉狀態..."
    
    # 檢查是否還有相關進程
    local remaining_processes=$(ps aux | grep -E "(mcp_server_sqlite|uvicorn.*src.main|python.*main.py|fastapi)" | grep -v grep)
    
    if [ -n "$remaining_processes" ]; then
        echo -e "  ${YELLOW}⚠️ 發現殘留進程:${NC}"
        echo "$remaining_processes" | while read line; do
            echo -e "    ${BLUE}🔸${NC} $line"
        done
        return 1
    else
        echo -e "  ${GREEN}✅ 所有相關進程已成功停止${NC}"
    fi
    
    # 檢查關鍵端口
    local critical_ports=(3003 8000)  # SQLite MCP 和 Webhook 是核心服務
    local ports_ok=true
    
    for port in "${critical_ports[@]}"; do
        if lsof -i :$port >/dev/null 2>&1; then
            echo -e "  ${YELLOW}⚠️ 關鍵端口 $port 仍被占用${NC}"
            ports_ok=false
        fi
    done
    
    if [ "$ports_ok" = true ]; then
        echo -e "  ${GREEN}✅ 所有關鍵端口已釋放${NC}"
    fi
    
    return $([[ "$ports_ok" = true ]] && echo 0 || echo 1)
}

# 檢查並停止特定系統資源
cleanup_system_resources() {
    echo ""
    echo "🧹 清理系統資源..."
    
    # 清理可能的臨時檔案
    temp_dirs=("/tmp/mcp_*" "/tmp/line_*")
    for temp_pattern in "${temp_dirs[@]}"; do
        if ls $temp_pattern 1> /dev/null 2>&1; then
            echo -e "  🗑️ 清理臨時檔案: ${BLUE}$temp_pattern${NC}"
            rm -rf $temp_pattern 2>/dev/null
        fi
    done
    
    # 檢查是否有殭屍進程
    zombies=$(ps aux | awk '$8 ~ /^Z/ { print $2 }')
    if [ -n "$zombies" ]; then
        echo -e "  ${YELLOW}⚠️ 發現殭屍進程: $zombies${NC}"
        echo "  💡 建議重啟系統以完全清理"
    fi
}

# 主執行流程
main() {
    # 查找運行中的服務
    find_running_services
    local has_services=$?
    
    if [ $has_services -eq 1 ]; then
        echo ""
        echo -e "${GREEN}✅ 系統未運行，無需停止${NC}"
        exit 0
    fi
    
    echo ""
    echo "🛑 開始停止服務..."
    echo "======================================="
    
    # 按順序停止服務（反向啟動順序）
    stop_service "LINE Webhook Service" "uvicorn.*src.main"
    stop_service "SQLite MCP Server" "mcp_server_sqlite"
    stop_service "Python 主程式" "python.*main.py"
    stop_service "ngrok 隧道" "ngrok"
    
    echo ""
    echo "⏳ 等待進程完全停止..."
    sleep 3
    
    # 檢查並釋放端口
    release_ports
    
    # 清理日誌檔案
    cleanup_logs
    
    # 清理系統資源
    cleanup_system_resources
    
    # 驗證停止狀態
    verify_shutdown
    local verification_result=$?
    
    echo ""
    echo "======================================="
    
    if [ $verification_result -eq 0 ]; then
        echo -e "${GREEN}✅ LINE MCP Webhook 系統已完全關閉${NC}"
    else
        echo -e "${YELLOW}⚠️ 系統已停止，但可能存在殘留進程或端口占用${NC}"
        echo "   如果問題持續，請考慮重啟系統"
    fi
    
    echo ""
    echo "📋 系統管理指令:"
    echo -e "   🚀 重新啟動: ${BLUE}./scripts/start-all.sh${NC}"
    echo -e "   📊 查看狀態: ${BLUE}ps aux | grep -E '(mcp|uvicorn)' | grep -v grep${NC}"
    echo -e "   🔍 檢查端口: ${BLUE}lsof -i :8000,3003${NC}"
    echo ""
    echo "🗂️ 日誌檔案位置:"
    echo -e "   📝 Webhook: ${BLUE}apps/bot/logs/webhook.log${NC}"
    echo -e "   🗃️ SQLite MCP: ${BLUE}apps/bot/logs/sqlite-mcp.log${NC}"
    echo ""
    echo "💡 故障排除提示:"
    echo "   • 如果遇到端口被占用問題，檢查是否有其他應用程式在使用相同端口"
    echo "   • 如果進程無法停止，嘗試以下指令:"
    echo -e "     ${BLUE}sudo lsof -i :8000${NC}  # 查看端口 8000 的占用情況"
    echo -e "     ${BLUE}sudo kill -9 <PID>${NC}  # 強制終止特定進程"
    echo ""
    echo "🏗️ 系統架構概覽:"
    echo "   停止順序: Webhook → SQLite MCP Server → 系統資源清理"
    echo "   關鍵端口: 8000 (Webhook), 3003 (SQLite MCP)"
    echo ""
}

# 執行主函數
main "$@"