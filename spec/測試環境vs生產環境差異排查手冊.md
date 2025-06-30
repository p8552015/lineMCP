# 測試環境 vs 生產環境差異排查手冊
**版本**: v1.0  
**日期**: 2025-06-30  
**目的**: 快速識別並解決環境差異問題

## 🚨 問題識別矩陣

| 現象 | 測試環境 | 生產環境 | 可能原因 | 優先級 |
|------|----------|----------|----------|--------|
| 語法錯誤 | ❌ | ❌ | 代碼問題 | 🔴 高 |
| 功能異常 | ✅ | ❌ | 服務快取/配置 | 🟡 中 |
| API 回應錯誤 | ✅ | ❌ | 路由/實例問題 | 🟡 中 |
| 模型切換失敗 | ✅ | ❌ | 服務版本差異 | 🟠 中高 |

## 🔍 快速診斷流程 (5分鐘)

### Step 1: 基礎檢查 (1分鐘)
```bash
# 語法檢查
python -m py_compile apps/bot/src/services/*.py
echo $?  # 0=成功，非0=語法錯誤

# 服務狀態
curl -s http://localhost:8000/health | jq '.status'
```

### Step 2: 環境對比 (2分鐘)
```bash
# 直接測試 (模擬測試環境)
cd apps/bot && python -c "
from src.services.ai_model_service_enhanced import EnhancedAIModelService
import asyncio
async def test():
    service = EnhancedAIModelService()
    result = await service.generate_user_guidance('測試', '測試提示')
    print('直接測試:', result[0][:50])
asyncio.run(test())
"

# Web API 測試 (生產環境)
curl -X POST http://localhost:8000/test-llm \
  -H "Content-Type: application/json" \
  -d '{"text":"測試"}' | jq -r '.response'
```

### Step 3: 差異分析 (2分鐘)
```bash
# 服務實例類型檢查
python -c "
from src.infrastructure.enhanced_service_factory import get_enhanced_service_factory
factory = get_enhanced_service_factory()
service = factory.get_ai_model_service()
print('服務類型:', type(service).__name__)
print('有新方法:', hasattr(service, 'generate_user_guidance'))
"
```

## 🔧 標準修復流程

### 情況一：語法錯誤 🔴
```bash
# 檢查語法
python -m py_compile apps/bot/src/services/ai_model_service.py

# 修復後重新檢查
python -m py_compile apps/bot/src/services/ai_model_service.py
echo "語法錯誤已修復: $?"
```

### 情況二：服務快取問題 🟡
```bash
# 1. 停止服務
lsof -ti:8000 | xargs kill -9

# 2. 清理進程
ps aux | grep uvicorn | awk '{print $2}' | xargs kill -9

# 3. 重啟服務
./start-production.sh

# 4. 驗證修復
curl -X POST http://localhost:8000/test-llm \
  -H "Content-Type: application/json" \
  -d '{"text":"CNC車床今天不良率"}'
```

### 情況三：方法路由錯誤 🟠
```bash
# 檢查方法調用路徑
grep -r "generate_user_guidance" apps/bot/src/
grep -r "enhance_natural_language_query" apps/bot/src/

# 確認服務註冊
python -c "
from src.infrastructure.enhanced_service_factory import get_enhanced_service_factory
factory = get_enhanced_service_factory()
service = factory.get_ai_model_service()
print('服務類型:', type(service).__mro__)
"
```

## 📋 檢查清單模板

### 修復前檢查
- [ ] 語法錯誤檢查完成
- [ ] 直接測試執行正常
- [ ] Web API 測試確認問題
- [ ] 服務實例類型確認
- [ ] 方法存在性驗證

### 修復後驗證
- [ ] 語法錯誤已解決
- [ ] 服務已重啟
- [ ] 直接測試仍正常
- [ ] Web API 測試已修復
- [ ] 完整測試套件通過

## 🚀 自動化腳本

### diagnose-env-diff.sh
```bash
#!/bin/bash
# 自動診斷環境差異

echo "🔍 環境差異診斷開始..."

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
```

### fix-env-diff.sh
```bash
#!/bin/bash
# 自動修復環境差異

echo "🔧 環境差異修復開始..."

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
```

## 📊 常見問題與解決方案

### Q1: 直接測試正常，Web API 異常
**原因**: 服務實例快取  
**解決**: 重啟服務
```bash
./fix-env-diff.sh
```

### Q2: 語法檢查通過，但功能異常
**原因**: 方法未正確覆寫  
**解決**: 檢查方法實現
```python
# 確認增強版服務中有新方法
class EnhancedAIModelService(AIModelService):
    async def generate_user_guidance(self, ...):
        # 必須有完整實現
```

### Q3: 模型切換不工作
**原因**: 基類方法不支援備用模型  
**解決**: 在增強版中實現完整備用邏輯
```python
# 在增強版服務中實現
for model in target_models:
    try:
        result = await self._call_model(...)
        return result
    except Exception:
        continue  # 切換到下一個模型
```

### Q4: 回應格式錯誤
**原因**: 調用了錯誤的方法  
**解決**: 確認調用路徑
```python
# 正確調用
await self.ai_model_service.generate_user_guidance(...)

# 錯誤調用  
await self.ai_model_service.enhance_natural_language_query(...)
```

## 🎯 成功標準定義

### 語法層面
```bash
python -m py_compile apps/bot/src/services/*.py
# 返回值必須為 0
```

### 功能層面
```bash
# 輸入
{"text": "CNC車床今天不良率"}

# 期望輸出（友善指導）
"您好！很抱歉，目前系統無法直接查詢..."

# 錯誤輸出（技術性描述）
"查詢CNC車床在今天的生產不良率，包含..."
```

### 性能層面
```bash
# Gemini → OpenAI 切換
Gemini 429 錯誤 → 自動切換 → OpenAI 成功回應
```

## 📝 問題追蹤模板

```markdown
## 環境差異問題記錄

**日期**: YYYY-MM-DD  
**問題編號**: ENV-DIFF-001

### 問題描述
- 測試環境行為: 
- 生產環境行為: 
- 差異點: 

### 診斷過程
- [ ] 語法檢查: 
- [ ] 直接測試: 
- [ ] Web API 測試: 
- [ ] 服務實例檢查: 

### 根本原因
- 技術原因: 
- 環境因素: 

### 解決步驟
1. 
2. 
3. 

### 驗證結果
- [ ] 語法正常
- [ ] 直接測試通過  
- [ ] Web API 正常
- [ ] 完整測試通過

### 預防措施
- 代碼: 
- 流程: 
- 監控: 
```

---

**維護指南**: 每次遇到環境差異問題時，請更新此手冊  
**使用建議**: 保存為書籤，問題發生時立即查閱  
**更新頻率**: 月度回顧，持續完善