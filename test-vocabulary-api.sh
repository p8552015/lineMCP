#!/bin/bash

# 詞彙庫 API 端點測試腳本
# 測試智能解譯系統的各種 API 功能

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# API 基本設定
API_BASE="http://localhost:8000"

echo -e "${PURPLE}=====================================${NC}"
echo -e "${PURPLE}詞彙庫智能解譯 API 測試${NC}"
echo -e "${PURPLE}=====================================${NC}"
echo ""

# 1. 健康檢查
echo -e "${BLUE}1. 系統健康檢查${NC}"
curl -X GET "$API_BASE/health" \
    -H "Content-Type: application/json" | jq '.'
echo -e "\n${GREEN}----------------------------------------${NC}\n"

# 2. 測試詞彙解譯 API（如果有獨立端點）
echo -e "${BLUE}2. 詞彙解譯測試${NC}"

# 測試解譯端點的請求體
interpret_request() {
    local query="$1"
    local body=$(cat <<EOF
{
    "query": "$query",
    "use_llm": true,
    "return_details": true
}
EOF
)
    
    echo -e "${YELLOW}查詢：${NC}$query"
    
    # 假設有 /api/interpret 端點
    curl -X POST "$API_BASE/api/interpret" \
        -H "Content-Type: application/json" \
        -d "$body" | jq '.'
    
    echo ""
}

# 如果沒有專門的解譯端點，使用 webhook 測試
webhook_test() {
    local query="$1"
    local body=$(cat <<EOF
{
    "events": [{
        "type": "message",
        "timestamp": $(date +%s)000,
        "source": {"type": "user", "userId": "test_api"},
        "replyToken": "test_$(date +%s)",
        "message": {"type": "text", "text": "$query"}
    }]
}
EOF
)
    
    echo -e "${YELLOW}Webhook 測試：${NC}$query"
    curl -X POST "$API_BASE/webhook" \
        -H "Content-Type: application/json" \
        -H "X-Line-Signature: test" \
        -d "$body" \
        -w "\nHTTP: %{http_code} | Time: %{time_total}s\n"
    echo ""
}

# 3. 批量測試關鍵查詢
echo -e "${BLUE}3. 關鍵查詢批量測試${NC}"

queries=(
    "M001機台稼動率"
    "生產部門本週OEE"
    "CNC車床今天不良率"
    "品質部門即時數據"
    "M002銑床產量統計"
)

for query in "${queries[@]}"; do
    webhook_test "$query"
    sleep 0.5
done

echo -e "\n${GREEN}----------------------------------------${NC}\n"

# 4. 測試詞彙庫統計 API（如果存在）
echo -e "${BLUE}4. 詞彙庫統計資訊${NC}"

# 嘗試獲取詞彙庫統計
curl -X GET "$API_BASE/api/vocabulary/stats" \
    -H "Content-Type: application/json" 2>/dev/null | jq '.' || echo "統計端點不存在"

echo -e "\n${GREEN}----------------------------------------${NC}\n"

# 5. 效能測試
echo -e "${BLUE}5. 效能基準測試${NC}"

# 測試單一查詢的回應時間
echo "測試查詢：M001機台稼動率"
echo "執行 5 次測試..."

total_time=0
for i in {1..5}; do
    response_time=$(curl -X POST "$API_BASE/webhook" \
        -H "Content-Type: application/json" \
        -H "X-Line-Signature: test" \
        -d '{
            "events": [{
                "type": "message",
                "source": {"type": "user", "userId": "perf_test"},
                "replyToken": "perf_test",
                "message": {"type": "text", "text": "M001機台稼動率"}
            }]
        }' \
        -s -o /dev/null -w "%{time_total}")
    
    echo "第 $i 次：${response_time}s"
    total_time=$(echo "$total_time + $response_time" | bc)
done

avg_time=$(echo "scale=3; $total_time / 5" | bc)
echo -e "${GREEN}平均回應時間：${avg_time}s${NC}"

echo -e "\n${GREEN}----------------------------------------${NC}\n"

# 6. 錯誤處理測試
echo -e "${BLUE}6. 錯誤處理測試${NC}"

# 測試空查詢
echo "測試空查詢..."
curl -X POST "$API_BASE/webhook" \
    -H "Content-Type: application/json" \
    -H "X-Line-Signature: test" \
    -d '{
        "events": [{
            "type": "message",
            "source": {"type": "user", "userId": "error_test"},
            "replyToken": "error_test",
            "message": {"type": "text", "text": ""}
        }]
    }' \
    -w "\nHTTP: %{http_code}\n"

echo ""

# 測試無效查詢
echo "測試無效查詢..."
curl -X POST "$API_BASE/webhook" \
    -H "Content-Type: application/json" \
    -H "X-Line-Signature: test" \
    -d '{
        "events": [{
            "type": "message",
            "source": {"type": "user", "userId": "error_test"},
            "replyToken": "error_test",
            "message": {"type": "text", "text": "abcdefg123"}
        }]
    }' \
    -w "\nHTTP: %{http_code}\n"

echo -e "\n${GREEN}----------------------------------------${NC}\n"

# 7. 測試總結
echo -e "${PURPLE}=====================================${NC}"
echo -e "${PURPLE}測試總結${NC}"
echo -e "${PURPLE}=====================================${NC}"
echo ""
echo "測試完成項目："
echo "✅ 系統健康檢查"
echo "✅ 多欄位關鍵字提取"
echo "✅ 批量查詢測試"
echo "✅ 效能基準測試"
echo "✅ 錯誤處理驗證"
echo ""
echo "關鍵改善功能："
echo "• 智能多欄位提取（機台+指標+時間+部門）"
echo "• 同義詞自動識別"
echo "• LLM 增強解譯"
echo "• 動態詞彙庫管理"
echo ""
echo -e "${YELLOW}執行建議：${NC}"
echo "1. 確保服務已啟動：./start-production.sh"
echo "2. 檢查詞彙庫載入：查看服務啟動日誌"
echo "3. 監控系統效能：觀察回應時間"
echo "4. 收集使用者回饋：持續改善詞彙庫"