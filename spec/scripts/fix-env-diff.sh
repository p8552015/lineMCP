#!/bin/bash
# 自動修復環境差異

echo "🔧 環境差異修復開始..."

# 切換到正確目錄
cd "$(dirname "$0")/../.." || exit 1

# 1. 停止服務
echo "1️⃣ 停止當前服務..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
sleep 2

# 2. 清理進程
echo "2️⃣ 清理殘留進程..."
ps aux | grep uvicorn | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null
sleep 1

# 3. 語法檢查
echo "3️⃣ 最終語法檢查..."
python -m py_compile apps/bot/src/services/*.py
if [ $? -ne 0 ]; then
    echo "❌ 語法錯誤未修復，請先修復語法問題"
    exit 1
fi

# 4. 重啟服務
echo "4️⃣ 重啟服務..."
./start-production.sh &
sleep 10

# 5. 健康檢查
echo "5️⃣ 健康檢查..."
for i in {1..5}; do
    if curl -s http://localhost:8000/health >/dev/null; then
        echo "✅ 服務已啟動"
        break
    fi
    echo "⏳ 等待服務啟動... ($i/5)"
    sleep 2
done

# 6. 功能驗證
echo "6️⃣ 功能驗證..."
RESULT=$(curl -s -X POST http://localhost:8000/test-llm \
  -H "Content-Type: application/json" \
  -d '{"text":"CNC車床今天不良率"}' | jq -r '.response // "ERROR"')

echo "驗證結果: $RESULT"

if [[ "$RESULT" == *"您好"* ]] || [[ "$RESULT" == *"抱歉"* ]]; then
    echo "✅ 修復成功！回應已改為友善指導"
elif [[ "$RESULT" == *"查詢CNC車床"* ]]; then
    echo "❌ 修復失敗，仍返回技術性描述"
    exit 1
else
    echo "⚠️ 結果不明確，需要手動檢查"
fi