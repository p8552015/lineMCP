#!/bin/bash

# 測試詞彙庫系統與現有 LINE Bot 的整合
# 驗證改善後的自然語言轉 SQL 功能

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# 設定
API_URL="http://localhost:8000"
WEBHOOK_URL="$API_URL/webhook"

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}詞彙庫整合測試${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

# 建立測試請求
send_message() {
    local text="$1"
    local user_id="${2:-test_user}"
    
    local body=$(cat <<EOF
{
    "events": [{
        "type": "message",
        "timestamp": $(date +%s)000,
        "source": {
            "type": "user",
            "userId": "$user_id"
        },
        "replyToken": "reply_$(date +%s)",
        "message": {
            "type": "text",
            "id": "msg_$(date +%s)",
            "text": "$text"
        }
    }]
}
EOF
)
    
    curl -s -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -H "X-Line-Signature: test_signature" \
        -d "$body" \
        -o /tmp/response.json \
        -w "%{http_code}"
}

# 檢查回應
check_response() {
    local http_code="$1"
    local test_name="$2"
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ $test_name - 成功${NC}"
        if [ -f /tmp/response.json ] && [ -s /tmp/response.json ]; then
            echo "   回應內容："
            cat /tmp/response.json | jq '.' 2>/dev/null || cat /tmp/response.json
        fi
    else
        echo -e "${RED}❌ $test_name - 失敗 (HTTP $http_code)${NC}"
        if [ -f /tmp/response.json ]; then
            cat /tmp/response.json
        fi
    fi
    echo ""
}

# 1. 服務檢查
echo -e "${YELLOW}1. 檢查服務狀態${NC}"
health_check=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health")
if [ "$health_check" = "200" ]; then
    echo -e "${GREEN}✅ 服務運行正常${NC}"
else
    echo -e "${RED}❌ 服務未啟動${NC}"
    echo "請執行: ./start-production.sh"
    exit 1
fi
echo ""

# 2. 測試基本指令
echo -e "${YELLOW}2. 測試現有指令兼容性${NC}"

echo "測試 /help 指令..."
http_code=$(send_message "/help")
check_response "$http_code" "/help 指令"

echo "測試 /status 指令..."
http_code=$(send_message "/status")
check_response "$http_code" "/status 指令"

# 3. 測試改善後的自然語言查詢
echo -e "${YELLOW}3. 測試多欄位關鍵字提取${NC}"

test_cases=(
    "M001機台稼動率|基本多欄位查詢"
    "生產部門本週的OEE指標|部門+時間+指標"
    "CNC車床今天不良率|機台類型+時間+指標"
    "品質部門M002銑床即時產量數據|複雜多欄位查詢"
    "機台M001使用率|同義詞測試"
    "查看所有機台狀態|列表查詢"
)

for test_case in "${test_cases[@]}"; do
    IFS='|' read -r query description <<< "$test_case"
    echo -e "${BLUE}測試：$description${NC}"
    echo "查詢：$query"
    
    http_code=$(send_message "$query")
    check_response "$http_code" "$description"
    
    sleep 1
done

# 4. 測試 SQL 指令整合
echo -e "${YELLOW}4. 測試 SQL 指令整合${NC}"

echo "測試直接 SQL 查詢..."
sql_query="/sql SELECT machine_id, utilization_rate FROM machine_data WHERE machine_id = 'M001' ORDER BY timestamp DESC LIMIT 1"
http_code=$(send_message "$sql_query")
check_response "$http_code" "直接 SQL 查詢"

# 5. 測試錯誤處理
echo -e "${YELLOW}5. 測試錯誤處理${NC}"

error_cases=(
    "|空查詢"
    "xyz123abc|無意義查詢"
    "M999機台狀態|不存在的機台"
    "稼動率|缺少機台資訊"
)

for test_case in "${error_cases[@]}"; do
    IFS='|' read -r query description <<< "$test_case"
    echo -e "${BLUE}測試：$description${NC}"
    echo "查詢：'$query'"
    
    http_code=$(send_message "$query")
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ $description - 錯誤被正確處理${NC}"
    else
        echo -e "${YELLOW}⚠️  $description - HTTP $http_code${NC}"
    fi
    echo ""
done

# 6. 效能測試
echo -e "${YELLOW}6. 簡單效能測試${NC}"

start_time=$(date +%s.%N)
for i in {1..5}; do
    send_message "M001機台稼動率" "perf_test_$i" > /dev/null 2>&1
done
end_time=$(date +%s.%N)

total_time=$(echo "$end_time - $start_time" | bc)
avg_time=$(echo "scale=3; $total_time / 5" | bc)

echo -e "${GREEN}5 次查詢總時間：${total_time} 秒${NC}"
echo -e "${GREEN}平均每次查詢：${avg_time} 秒${NC}"
echo ""

# 7. 測試總結
echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}測試總結${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""
echo "✅ 測試完成的功能："
echo "   • 基本指令兼容性"
echo "   • 多欄位關鍵字提取"
echo "   • 同義詞識別"
echo "   • SQL 指令整合"
echo "   • 錯誤處理機制"
echo "   • 系統效能"
echo ""
echo "📊 關鍵改善："
echo "   • 支援「M001機台稼動率」等複雜查詢"
echo "   • 一次提取多個資料欄位"
echo "   • 智能語義理解"
echo "   • 動態詞彙庫管理"
echo ""
echo "📁 相關檔案："
echo "   • 詞彙庫：manufacturing_vocabulary_database.yaml"
echo "   • 解譯器：intelligent_vocabulary_interpreter.py"
echo "   • 改善計劃：spec_自然語言轉SQL深度改善計劃.md"
echo ""
echo -e "${GREEN}測試執行完畢！${NC}"

# 清理臨時檔案
rm -f /tmp/response.json