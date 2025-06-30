#!/bin/bash
# 自動診斷環境差異

echo "🔍 環境差異診斷開始..."

# 切換到正確目錄
cd "$(dirname "$0")/../.." || exit 1

# 1. 語法檢查
echo "1️⃣ 檢查語法錯誤..."
python -m py_compile apps/bot/src/services/*.py
SYNTAX_OK=$?

# 2. 直接測試
echo "2️⃣ 執行直接測試..."
cd apps/bot
DIRECT_RESULT=$(python -c "
from src.services.ai_model_service_enhanced import EnhancedAIModelService
import asyncio
from dotenv import load_dotenv
load_dotenv()

async def test():
    try:
        service = EnhancedAIModelService()
        result = await service.generate_user_guidance('CNC車床今天不良率', '測試提示')
        print(result[0][:100])
        return True
    except Exception as e:
        print('ERROR:', str(e))
        return False
asyncio.run(test())
" 2>&1)

cd ..

# 3. Web API 測試
echo "3️⃣ 執行 Web API 測試..."
WEB_RESULT=$(curl -s -X POST http://localhost:8000/test-llm \
  -H "Content-Type: application/json" \
  -d '{"text":"CNC車床今天不良率"}' | jq -r '.response // "ERROR"')

# 4. 結果分析
echo ""
echo "📊 診斷結果:"
echo "語法檢查: $([ $SYNTAX_OK -eq 0 ] && echo '✅ 通過' || echo '❌ 失敗')"
echo "直接測試: $DIRECT_RESULT"
echo "Web API: $WEB_RESULT"

# 5. 建議
echo ""
echo "💡 建議:"
if [ $SYNTAX_OK -ne 0 ]; then
    echo "🔴 修復語法錯誤"
elif [[ "$WEB_RESULT" == *"查詢CNC車床"* ]]; then
    echo "🟡 重啟服務以清除快取"
elif [[ "$WEB_RESULT" == "ERROR" ]]; then
    echo "🟠 檢查服務狀態和配置"
else
    echo "✅ 環境一致，無差異"
fi