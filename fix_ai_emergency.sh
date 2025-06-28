#!/bin/bash

echo "🚨 緊急修復：啟用純規則模式"

cd /Users/yen/Desktop/lineMCP/apps/bot

# 1. 停用 AI 模型，僅使用規則解析
echo "" >> .env
echo "# 緊急模式：停用 AI 模型 ($(date))" >> .env
echo "AI_ENABLE_ENHANCED_NL=false" >> .env
echo "AI_FALLBACK_TO_RULES=true" >> .env

echo "✅ 已配置為純規則模式"

# 2. 重啟服務
echo "🔄 重啟服務..."
pkill -f uvicorn
sleep 3

cd /Users/yen/Desktop/lineMCP
nohup ./start-production.sh > startup_emergency.log 2>&1 &

echo "⏱️ 等待服務啟動..."
sleep 5

# 3. 檢查服務狀態
if pgrep -f uvicorn > /dev/null; then
    echo "✅ 服務已重啟 (純規則模式)"
    echo "📋 現在系統將僅使用規則匹配，不依賴 AI 模型"
    echo ""
    echo "🧪 測試查詢："
    echo "  - M005 機台運行情況 → 應該能正確識別為 specific_machine"
    echo "  - 查看所有機台 → 應該能正確識別為 all_machines"
else
    echo "❌ 服務啟動失敗，請檢查日誌"
fi