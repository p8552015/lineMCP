#!/bin/bash

# 快速測試製造業詞彙庫多欄位提取功能
# 最簡化的 CURL 測試

echo "🔍 製造業詞彙庫快速測試"
echo "========================="
echo ""

# API URL
URL="http://localhost:8000/Webhook"

# 測試函數
test() {
    echo "📝 測試：$1"
    response=$(curl -s -X POST http://localhost:8000/test-llm \
        -H "Content-Type: application/json" \
        -d "{\"text\":\"$1\"}" \
        -w "\n狀態碼: %{http_code}\n")
    echo "$response" | jq -r '.response // .' 2>/dev/null || echo "$response"
    echo "---"
    echo ""
}

# 1. 檢查服務
echo "檢查服務狀態..."
curl -s http://localhost:8000/health || echo "⚠️  服務未啟動，請執行: ./start-production.sh"
echo ""

# 2. 核心測試
echo "🎯 核心功能測試"
echo "==============="

test "M001機台稼動率"
test "生產部門本週的OEE指標"
test "CNC車床今天不良率"
test "品質部門M002銑床即時產量"

# 3. 測試結果解讀
echo "📊 預期結果"
echo "==========="
echo "✅ M001機台稼動率 → 提取: 機台(M001) + 指標(稼動率)"
echo "✅ 生產部門本週的OEE指標 → 提取: 部門(生產) + 時間(本週) + 指標(OEE)"
echo "✅ CNC車床今天不良率 → 提取: 機台類型(CNC車床) + 時間(今天) + 指標(不良率)"
echo "✅ 品質部門M002銑床即時產量 → 提取: 部門(品質) + 機台(M002) + 時間(即時) + 指標(產量)"
echo ""

# 4. 相關檔案
echo "📁 系統檔案"
echo "=========="
echo "詞彙庫: apps/bot/src/services/nl_to_sql/config/manufacturing_vocabulary_database.yaml"
echo "解譯器: apps/bot/src/services/nl_to_sql/services/intelligent_vocabulary_interpreter.py"
echo "使用指南: task/開發指南/製造業詞彙庫使用者更新指南.md"