#!/bin/bash

# 自然語言轉 SQL 改善系統 CURL 測試腳本
# 測試多欄位關鍵字提取和智能解譯功能

# 設定顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# API 設定
API_URL="http://localhost:8000"
WEBHOOK_URL="${API_URL}/webhook"
HEALTH_URL="${API_URL}/health"

# LINE 設定（使用測試 token）
CHANNEL_SECRET="test_secret"
USER_ID="test_user_001"

# 顯示標題
echo -e "${PURPLE}=====================================${NC}"
echo -e "${PURPLE}自然語言轉 SQL 改善系統測試${NC}"
echo -e "${PURPLE}=====================================${NC}"
echo ""

# 檢查服務狀態
check_service_status() {
    echo -e "${BLUE}檢查服務狀態...${NC}"
    
    response=$(curl -s -X GET "${HEALTH_URL}" -w "\n%{http_code}")
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ 服務運行正常${NC}"
        echo -e "   回應：$body"
    else
        echo -e "${RED}❌ 服務無回應 (HTTP $http_code)${NC}"
        echo -e "${YELLOW}請先啟動服務：./start-production.sh${NC}"
        exit 1
    fi
    echo ""
}

# 生成 LINE Webhook 簽名
generate_signature() {
    local body="$1"
    echo -n "$body" | openssl dgst -sha256 -hmac "$CHANNEL_SECRET" -binary | base64
}

# 發送測試訊息
send_test_message() {
    local text="$1"
    local test_name="$2"
    
    # 構建 LINE Webhook 請求體
    local body=$(cat <<EOF
{
    "events": [{
        "type": "message",
        "timestamp": $(date +%s)000,
        "source": {
            "type": "user",
            "userId": "$USER_ID"
        },
        "replyToken": "test_reply_token_$(date +%s)",
        "message": {
            "type": "text",
            "id": "test_message_$(date +%s)",
            "text": "$text"
        }
    }]
}
EOF
)
    
    # 生成簽名
    local signature=$(generate_signature "$body")
    
    echo -e "${BLUE}測試：${NC}$test_name"
    echo -e "${YELLOW}查詢：${NC}$text"
    
    # 發送請求
    response=$(curl -s -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -H "X-Line-Signature: $signature" \
        -d "$body" \
        -w "\n%{http_code}")
    
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ 請求成功${NC}"
        
        # 嘗試解析回應（如果有的話）
        if [ -n "$body" ] && [ "$body" != "null" ]; then
            echo -e "   回應：$body"
        fi
    else
        echo -e "${RED}❌ 請求失敗 (HTTP $http_code)${NC}"
        echo -e "   錯誤：$body"
    fi
    echo ""
}

# 測試多欄位提取功能
test_multi_field_extraction() {
    echo -e "${PURPLE}=== 測試 1：多欄位關鍵字提取 ===${NC}"
    echo ""
    
    # 測試案例 1：基本多欄位查詢
    send_test_message "M001機台稼動率" "基本多欄位查詢"
    sleep 1
    
    # 測試案例 2：包含時間的多欄位查詢
    send_test_message "M001機台今天的稼動率" "時間+機台+指標查詢"
    sleep 1
    
    # 測試案例 3：部門+時間+指標
    send_test_message "生產部門本週的OEE指標" "部門+時間+指標查詢"
    sleep 1
    
    # 測試案例 4：複雜多欄位查詢
    send_test_message "品質部門負責的CNC車床今天不良率統計" "複雜多欄位查詢"
    sleep 1
}

# 測試同義詞和語義理解
test_synonym_understanding() {
    echo -e "${PURPLE}=== 測試 2：同義詞和語義理解 ===${NC}"
    echo ""
    
    # 測試同義詞識別
    send_test_message "機台M001使用率" "同義詞測試 - 使用率"
    sleep 1
    
    send_test_message "M-001設備利用率" "同義詞測試 - 設備利用率"
    sleep 1
    
    send_test_message "CNC車床A稼働率" "同義詞測試 - 日文稼働率"
    sleep 1
}

# 測試時間維度理解
test_time_dimension() {
    echo -e "${PURPLE}=== 測試 3：時間維度理解 ===${NC}"
    echo ""
    
    send_test_message "M002即時產量" "即時數據查詢"
    sleep 1
    
    send_test_message "生產線A本月總產量" "月度數據查詢"
    sleep 1
    
    send_test_message "昨天晚班的不良率" "班次+時間查詢"
    sleep 1
}

# 測試邊界情況
test_edge_cases() {
    echo -e "${PURPLE}=== 測試 4：邊界情況處理 ===${NC}"
    echo ""
    
    # 測試順序顛倒
    send_test_message "稼動率M001機台" "順序顛倒測試"
    sleep 1
    
    # 測試多機台查詢
    send_test_message "M001和M002機台的稼動率比較" "多機台查詢"
    sleep 1
    
    # 測試不存在的機台
    send_test_message "M999機台狀態" "不存在的機台"
    sleep 1
    
    # 測試混合語言
    send_test_message "查看Machine M001的utilization rate" "中英文混合"
    sleep 1
}

# 測試 SQL 查詢執行
test_sql_execution() {
    echo -e "${PURPLE}=== 測試 5：SQL 查詢執行 ===${NC}"
    echo ""
    
    # 使用 /sql 指令直接測試
    send_test_message "/sql SELECT machine_id, utilization_rate FROM machine_data WHERE machine_id = 'M001' ORDER BY timestamp DESC LIMIT 1" "直接 SQL 查詢"
    sleep 1
    
    # 測試自然語言轉 SQL
    send_test_message "查詢M001最新稼動率數據" "自然語言轉 SQL"
    sleep 1
}

# 測試複雜業務場景
test_business_scenarios() {
    echo -e "${PURPLE}=== 測試 6：複雜業務場景 ===${NC}"
    echo ""
    
    send_test_message "比較早班和晚班的生產效率" "班次比較分析"
    sleep 1
    
    send_test_message "哪台機器的稼動率最高" "排序查詢"
    sleep 1
    
    send_test_message "生產線A所有設備的綜合OEE" "聚合查詢"
    sleep 1
    
    send_test_message "品質異常的機台清單" "條件篩選查詢"
    sleep 1
}

# 效能測試
performance_test() {
    echo -e "${PURPLE}=== 測試 7：效能測試 ===${NC}"
    echo ""
    
    local start_time=$(date +%s.%N)
    
    # 連續發送 10 個請求
    for i in {1..10}; do
        echo -e "${YELLOW}發送第 $i 個請求...${NC}"
        send_test_message "M001機台稼動率" "效能測試 #$i" > /dev/null 2>&1
    done
    
    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)
    
    echo -e "${GREEN}完成 10 個請求，總耗時：${duration} 秒${NC}"
    echo -e "${GREEN}平均每個請求：$(echo "scale=3; $duration / 10" | bc) 秒${NC}"
    echo ""
}

# 顯示測試總結
show_test_summary() {
    echo -e "${PURPLE}=====================================${NC}"
    echo -e "${PURPLE}測試總結${NC}"
    echo -e "${PURPLE}=====================================${NC}"
    echo ""
    echo -e "${GREEN}測試重點：${NC}"
    echo "1. ✅ 多欄位關鍵字提取（如：M001機台稼動率）"
    echo "2. ✅ 同義詞和語義理解"
    echo "3. ✅ 時間維度識別"
    echo "4. ✅ 邊界情況處理"
    echo "5. ✅ SQL 查詢執行"
    echo "6. ✅ 複雜業務場景"
    echo "7. ✅ 系統效能"
    echo ""
    echo -e "${YELLOW}改善亮點：${NC}"
    echo "• 支援從單一查詢提取多個資料欄位"
    echo "• 智能識別機台編號、指標類型、時間範圍、部門等"
    echo "• LLM 增強的語義理解能力"
    echo "• 動態詞彙庫管理系統"
    echo ""
    echo -e "${BLUE}詞彙庫檔案位置：${NC}"
    echo "apps/bot/src/services/nl_to_sql/config/manufacturing_vocabulary_database.yaml"
    echo ""
    echo -e "${BLUE}核心實現檔案：${NC}"
    echo "apps/bot/src/services/nl_to_sql/services/intelligent_vocabulary_interpreter.py"
}

# 主函數
main() {
    # 檢查必要工具
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}錯誤：需要安裝 curl${NC}"
        exit 1
    fi
    
    if ! command -v openssl &> /dev/null; then
        echo -e "${RED}錯誤：需要安裝 openssl${NC}"
        exit 1
    fi
    
    # 執行測試
    check_service_status
    
    echo -e "${YELLOW}開始執行自然語言轉 SQL 改善測試...${NC}"
    echo ""
    
    test_multi_field_extraction
    test_synonym_understanding
    test_time_dimension
    test_edge_cases
    test_sql_execution
    test_business_scenarios
    performance_test
    
    show_test_summary
}

# 執行主函數
main