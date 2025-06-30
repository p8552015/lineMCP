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
        -d "{\"text\":\"$1\"}")
    
    # 解析回應內容
    response_text=$(echo "$response" | jq -r '.response // .' 2>/dev/null)
    status_code=$(echo "$response" | jq -r '.status // "unknown"' 2>/dev/null)
    
    # 判斷回應類型 - 優先檢查具體格式
    if echo "$response_text" | grep -q "📊 查詢結果"; then
        echo "✅ 返回數據庫查詢結果"
    elif echo "$response_text" | grep -q "📊.*狀態報告"; then
        echo "✅ 返回機台狀態報告"
    elif echo "$response_text" | grep -q -E "(需要指定|請.*指定|缺少.*資訊|可以嘗試|無法理解|不支援|查詢.*數據|查詢.*指標|查詢.*部門|查詢.*生產|查詢.*不良率|查詢.*產量|查詢.*在)"; then
        echo "✅ 觸發 LLM 指導回應"
    elif echo "$response_text" | grep -q "建議"; then
        # 「建議」可能出現在機台狀態報告中，需要區分
        if echo "$response_text" | grep -q "📊"; then
            echo "✅ 返回機台狀態報告"
        else
            echo "✅ 觸發 LLM 指導回應"
        fi
    else
        echo "❓ 未知回應類型"
    fi
    
    echo "$response_text"
    echo "狀態: $status_code"
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
echo "📊 預期結果（根據修復報告）"
echo "============================"
echo "✅ M001機台稼動率 → 返回機台詳細資訊（正常查詢）"
echo "✅ 生產部門本週的OEE指標 → 觸發 LLM 指導（空查詢，缺少具體資訊）"
echo "🎯 CNC車床今天不良率 → 觸發 LLM 指導（品質指標，系統不支援）"
echo "✅ 品質部門M002銑床即時產量 → 返回機台詳細資訊（正常查詢）"
echo ""
echo "⚠️ 重要：根據專案最高原則，所有空查詢都應該觸發 LLM 指導而非返回原始數據"
echo ""

# 4. 相關檔案
echo "📁 系統檔案"
echo "=========="
echo "詞彙庫: apps/bot/src/services/nl_to_sql/config/manufacturing_vocabulary_database.yaml"
echo "解譯器: apps/bot/src/services/nl_to_sql/services/intelligent_vocabulary_interpreter.py"
echo "使用指南: task/開發指南/製造業詞彙庫使用者更新指南.md"