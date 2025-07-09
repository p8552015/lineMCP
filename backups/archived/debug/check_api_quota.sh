#!/bin/bash

# 加載環境變數
cd /Users/yen/Desktop/lineMCP/apps/bot

# 確保正確載入 .env
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ 已載入 .env 文件"
else
    echo "❌ 找不到 .env 文件"
    exit 1
fi

echo "🔍 檢查 API 配額狀態..."
echo "GOOGLE_API_KEY: ${GOOGLE_API_KEY:0:20}..."
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:0:20}..."

# Gemini 配額檢查
echo "📊 Gemini API 狀態:"
response=$(curl -s -H "Content-Type: application/json" \
    -d '{"contents":[{"parts":[{"text":"hello"}]}]}' \
    -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=$GOOGLE_API_KEY")

if echo "$response" | grep -q "error"; then
    echo "❌ Gemini API 錯誤:"
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
else
    echo "✅ Gemini API 正常"
    echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print('回應:', data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'N/A')[:50])" 2>/dev/null
fi

# OpenAI 配額檢查
echo -e "\n📊 OpenAI API 狀態:"
response=$(curl -s -H "Authorization: Bearer $OPENAI_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"hi"}],"max_tokens":1}' \
    "https://api.openai.com/v1/chat/completions")

if echo "$response" | grep -q "error"; then
    echo "❌ OpenAI API 錯誤:"
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
else
    echo "✅ OpenAI API 正常"
    echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print('回應:', data.get('choices', [{}])[0].get('message', {}).get('content', 'N/A'))" 2>/dev/null
fi

echo -e "\n💡 建議操作:"
if echo "$response" | grep -q '"error"'; then
    echo "  1. 檢查 API keys 是否有效"
    echo "  2. 確認帳戶餘額/配額"
    echo "  3. 考慮切換 AI 提供商或啟用純規則模式"
fi