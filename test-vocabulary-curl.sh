#!/bin/bash

# 製造業詞彙庫智能解譯 CURL 測試
# 快速測試多欄位關鍵字提取功能

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# API 設定
API_URL="http://localhost:8000"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}製造業詞彙庫多欄位提取測試${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 測試函數
test_query() {
    local query="$1"
    local description="$2"
    
    echo -e "${YELLOW}測試：${NC}$description"
    echo -e "${GREEN}查詢：${NC}$query"
    
    # 構建請求體
    local body=$(cat <<EOF
{
    "events": [{
        "type": "message",
        "source": {"type": "user", "userId": "test_user"},
        "replyToken": "test_token",
        "message": {"type": "text", "text": "$query"}
    }]
}
EOF
)
    
    # 發送請求
    curl -X POST "$API_URL/webhook" \
        -H "Content-Type: application/json" \
        -H "X-Line-Signature: test" \
        -d "$body" \
        -w "\nHTTP Status: %{http_code}\n"
    
    echo -e "\n${BLUE}----------------------------------------${NC}\n"
    sleep 1
}

# 核心測試案例
echo -e "${BLUE}=== 1. 基本多欄位提取測試 ===${NC}\n"

test_query "M001機台稼動率" \
    "從單一查詢提取：機台編號(M001) + 指標類型(稼動率)"

test_query "生產部門本週的OEE指標" \
    "從單一查詢提取：部門(生產) + 時間(本週) + 指標(OEE)"

test_query "CNC車床今天不良率" \
    "從單一查詢提取：機台類型(CNC車床) + 時間(今天) + 指標(不良率)"

echo -e "${BLUE}=== 2. 同義詞識別測試 ===${NC}\n"

test_query "M001設備利用率" \
    "同義詞測試：設備利用率 = 稼動率"

test_query "機台M001使用率" \
    "同義詞測試：使用率 = 稼動率"

echo -e "${BLUE}=== 3. 複雜查詢測試 ===${NC}\n"

test_query "品質部門負責的M002銑床即時產量數據" \
    "複雜查詢：部門 + 機台編號 + 機台類型 + 時間 + 指標"

echo -e "${BLUE}=== 4. 直接 SQL 查詢測試 ===${NC}\n"

test_query "/sql SELECT machine_id, utilization_rate FROM machine_data WHERE machine_id = 'M001' LIMIT 1" \
    "直接執行 SQL 查詢"

# 總結
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}測試完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "詞彙庫特色功能："
echo "• 支援多欄位同時提取（機台、指標、時間、部門）"
echo "• 智能同義詞識別（稼動率、使用率、利用率）"
echo "• LLM 增強解譯（處理複雜查詢）"
echo "• 動態詞彙管理（使用者可自行更新）"
echo ""
echo "相關檔案："
echo "• 詞彙庫：apps/bot/src/services/nl_to_sql/config/manufacturing_vocabulary_database.yaml"
echo "• 解譯器：apps/bot/src/services/nl_to_sql/services/intelligent_vocabulary_interpreter.py"
echo "• 更新指南：task/開發指南/製造業詞彙庫使用者更新指南.md"