#!/bin/bash

echo "📊 LINE MCP Webhook 系統狀態檢查"
echo "======================================="
echo "⏰ 檢查時間: $(date)"
echo ""

# 檢查進程狀態
echo "🔍 進程狀態:"
echo "--------------------------------------"

services_found=false

# 檢查 Context7 MCP
context7_pid=$(ps aux | grep context7 | grep -v grep | awk '{print $2}' | head -1)
if [ ! -z "$context7_pid" ]; then
    echo "  ✅ Context7 MCP (PID: $context7_pid) - 運行中"
    services_found=true
else
    echo "  ❌ Context7 MCP - 未運行"
fi

# 檢查 PostgreSQL MCP
postgres_mcp_pid=$(ps aux | grep "postgres.*mcp" | grep -v grep | awk '{print $2}' | head -1)
if [ ! -z "$postgres_mcp_pid" ]; then
    echo "  ✅ PostgreSQL MCP (PID: $postgres_mcp_pid) - 運行中"
    services_found=true
else
    echo "  ❌ PostgreSQL MCP - 未運行"
fi

# 檢查 LINE Webhook
webhook_pid=$(ps aux | grep "python.*simple\|uvicorn" | grep -v grep | awk '{print $2}' | head -1)
if [ ! -z "$webhook_pid" ]; then
    echo "  ✅ LINE Webhook (PID: $webhook_pid) - 運行中"
    services_found=true
else
    echo "  ❌ LINE Webhook - 未運行"
fi

# 檢查 ngrok
ngrok_pid=$(ps aux | grep ngrok | grep -v grep | awk '{print $2}' | head -1)
if [ ! -z "$ngrok_pid" ]; then
    echo "  ✅ ngrok (PID: $ngrok_pid) - 運行中"
    services_found=true
else
    echo "  ⚠️ ngrok - 未運行 (需要手動啟動)"
fi

if [ "$services_found" = false ]; then
    echo "  ❌ 沒有發現任何服務在運行"
fi

echo ""

# 檢查端口狀態
echo "🔌 端口狀態:"
echo "--------------------------------------"
for port in 3001 3002 8000; do
    if lsof -i :$port >/dev/null 2>&1; then
        process=$(lsof -i :$port | tail -1 | awk '{print $1}')
        echo "  ✅ 端口 $port: 被 $process 使用"
    else
        echo "  ❌ 端口 $port: 未使用"
    fi
done

echo ""

# 檢查服務連接
echo "🌐 服務連接測試:"
echo "--------------------------------------"

# 測試 Context7 MCP
if curl -s --max-time 3 http://localhost:3001/mcp >/dev/null 2>&1; then
    echo "  ✅ Context7 MCP (http://localhost:3001): 可連接"
else
    echo "  ❌ Context7 MCP (http://localhost:3001): 連接失敗"
fi

# 測試 LINE Webhook
webhook_test=$(curl -s --max-time 3 -w "%{http_code}" http://localhost:8000/ 2>/dev/null | tail -1)
if [ "$webhook_test" = "200" ]; then
    echo "  ✅ LINE Webhook (http://localhost:8000): 可連接 (HTTP 200)"
elif [ ! -z "$webhook_test" ]; then
    echo "  ⚠️ LINE Webhook (http://localhost:8000): 回應 HTTP $webhook_test"
else
    echo "  ❌ LINE Webhook (http://localhost:8000): 連接失敗"
fi

# 測試 PostgreSQL
if psql -d mcp_test -c "SELECT 1" >/dev/null 2>&1; then
    user_count=$(psql -d mcp_test -t -c "SELECT COUNT(*) FROM users" 2>/dev/null | xargs)
    order_count=$(psql -d mcp_test -t -c "SELECT COUNT(*) FROM orders" 2>/dev/null | xargs)
    echo "  ✅ PostgreSQL (mcp_test): 可連接 ($user_count users, $order_count orders)"
else
    echo "  ❌ PostgreSQL (mcp_test): 連接失敗"
fi

echo ""

# 檢查日誌檔案
echo "📋 日誌檔案狀態:"
echo "--------------------------------------"
if [ -d "logs" ]; then
    for log_file in logs/*.log; do
        if [ -f "$log_file" ]; then
            size=$(ls -lh "$log_file" | awk '{print $5}')
            modified=$(ls -l "$log_file" | awk '{print $6, $7, $8}')
            echo "  📄 $(basename $log_file): $size (修改: $modified)"
        fi
    done
    
    if [ ! -f "logs/webhook.log" ] && [ ! -f "logs/context7-mcp.log" ] && [ ! -f "logs/postgres-mcp.log" ]; then
        echo "  ℹ️ 沒有找到日誌檔案"
    fi
else
    echo "  ℹ️ logs 目錄不存在"
fi

echo ""

# 提供建議
echo "💡 系統建議:"
echo "--------------------------------------"

if [ -z "$context7_pid" ] && [ -z "$postgres_mcp_pid" ] && [ -z "$webhook_pid" ]; then
    echo "  🚀 系統未運行，使用以下指令啟動:"
    echo "     ./start-all.sh"
elif [ ! -z "$context7_pid" ] && [ ! -z "$postgres_mcp_pid" ] && [ ! -z "$webhook_pid" ]; then
    echo "  ✅ 所有核心服務正常運行"
    if [ -z "$ngrok_pid" ]; then
        echo "  🌐 需要啟動 ngrok 隧道:"
        echo "     ngrok http 8000"
    fi
    echo "  🧪 可以進行功能測試:"
    echo "     poetry run python quick_mcp_test.py"
else
    echo "  ⚠️ 部分服務未運行，建議重新啟動:"
    echo "     ./stop-all.sh && ./start-all.sh"
fi

echo ""

# 快速操作指令
echo "🔧 快速操作:"
echo "--------------------------------------"
echo "  啟動系統: ./start-all.sh"
echo "  停止系統: ./stop-all.sh"
echo "  查看日誌: tail -f logs/webhook.log"
echo "  測試功能: poetry run python quick_mcp_test.py"
echo "  檢查狀態: ./status-check.sh"

echo ""
echo "======================================="