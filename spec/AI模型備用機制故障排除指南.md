# AI 模型備用機制故障排除指南
**版本**: v1.0  
**日期**: 2025-06-30  
**適用場景**: Gemini 配額用盡 → OpenAI 自動切換失敗

## 🎯 指南目的

解決 AI 模型備用機制失效問題，確保當 Gemini 配額用盡 (429 錯誤) 時能自動切換到 OpenAI，並生成正確的用戶友善回應。

## 🚨 問題症狀識別

### 典型錯誤模式
```
❌ Gemini 429 錯誤 → 直接返回錯誤訊息
✅ Gemini 429 錯誤 → 自動切換 OpenAI → 成功回應
```

### 實際案例對比
```bash
# 錯誤行為
"無法處理查詢「CNC車床今天不良率」，請稍後再試。"

# 正確行為  
"您好！很抱歉，目前系統無法直接查詢 CNC 車床的不良率數據..."
```

## 🔍 診斷檢查清單

### 1. 基礎配置檢查
```bash
# 環境變數確認
cd apps/bot && python -c "
from dotenv import load_dotenv
import os
load_dotenv()
print('GOOGLE_API_KEY 存在:', 'GOOGLE_API_KEY' in os.environ)
print('OPENAI_API_KEY 存在:', 'OPENAI_API_KEY' in os.environ)
print('AI_MODEL_PROVIDER:', os.environ.get('AI_MODEL_PROVIDER', 'unset'))
"
```

### 2. 服務實例檢查
```bash
# 確認使用增強版服務
cd apps/bot && python -c "
from src.infrastructure.enhanced_service_factory import get_enhanced_service_factory
factory = get_enhanced_service_factory()
service = factory.get_ai_model_service()
print('服務類型:', type(service).__name__)
print('備用模型:', getattr(service, 'fallback_models', '無'))
print('可用模型:', list(service.models.keys()))
"
```

### 3. 方法存在性檢查
```bash
# 檢查關鍵方法
cd apps/bot && python -c "
from src.services.ai_model_service_enhanced import EnhancedAIModelService
service = EnhancedAIModelService()
print('有 generate_user_guidance:', hasattr(service, 'generate_user_guidance'))
print('有 _is_model_healthy:', hasattr(service, '_is_model_healthy'))
print('有 fallback_models:', hasattr(service, 'fallback_models'))
"
```

## 🔧 常見問題與修復

### 問題 1: 基類方法不支援備用模型
**症狀**: `generate_user_guidance` 在 429 錯誤時直接返回錯誤  
**原因**: 基類 `AIModelService` 的方法沒有備用機制  
**解決**: 在 `EnhancedAIModelService` 中覆寫方法

```python
# 在 EnhancedAIModelService 中添加
async def generate_user_guidance(
    self,
    user_input: str,
    guidance_prompt: str,
    model_name: str | None = None,
) -> tuple[str, float]:
    """支援備用模型的用戶指導生成"""
    
    # 🔥 關鍵：使用備用模型列表
    target_models = self.fallback_models if not model_name else [model_name] + self.fallback_models
    
    for model in target_models:
        if not self._is_model_healthy(model):
            continue
            
        try:
            # 調用具體模型
            result = await self._call_model_for_guidance(model, ...)
            return result
        except Exception as e:
            # 記錄錯誤並嘗試下一個模型
            self._handle_model_error(model, e)
            continue
    
    # 所有模型都失敗
    return "抱歉，系統暫時無法處理...", 0.3
```

### 問題 2: 模型健康檢查過於嚴格
**症狀**: OpenAI 被標記為不健康而跳過  
**原因**: `_is_model_healthy` 檢查過於嚴格  
**解決**: 調整健康檢查邏輯

```python
def _is_model_healthy(self, model_name: str) -> bool:
    """調整後的健康檢查"""
    health = self._model_health[model_name]
    
    # 🔥 關鍵：配額用盡檢查
    if health.get("quota_exhausted", False):
        quota_time = health.get("quota_exhausted_at", 0)
        # 24小時後重新嘗試
        if time.time() - quota_time > 86400:
            health["quota_exhausted"] = False
            health["failures"] = 0
            return True
        return False
    
    # 失敗次數檢查（放寬標準）
    return health["failures"] < 5
```

### 問題 3: 錯誤類型識別不準確
**症狀**: 429 錯誤沒有被識別為配額問題  
**原因**: 錯誤訊息匹配模式不完整  
**解決**: 擴展錯誤模式識別

```python
def _is_quota_error(self, error_message: str) -> bool:
    """擴展的配額錯誤識別"""
    error_lower = error_message.lower()
    quota_keywords = [
        "quota", "rate limit", "429", "too many requests",
        "insufficient_quota", "resource_exhausted", 
        "billing", "payment", "exceeded", "limit reached"
    ]
    return any(keyword in error_lower for keyword in quota_keywords)
```

### 問題 4: 系統提示詞錯誤
**症狀**: 回應格式不是友善指導  
**原因**: 使用了技術性系統提示詞  
**解決**: 使用專門的友善提示詞

```python
# 正確的友善系統提示詞
system_prompt = """你是一個友善、專業的製造業智能助手。
用戶向你詢問了一個關於工業設備或生產的問題，但系統無法直接處理這個查詢。

請以自然、友善的語氣回應用戶，幫助他們：
1. 理解為什麼無法直接處理他們的查詢
2. 提供具體、實用的建議  
3. 給出 2-3 個相關的查詢範例

回應要求：
- 使用繁體中文
- 語氣友善專業，避免過於技術性
- 直接回應，不要使用JSON格式
- 保持簡潔實用（200字以內）
- 聚焦在幫助用戶獲得所需資訊"""
```

## 🧪 測試與驗證

### 單獨測試備用機制
```python
# test_fallback_mechanism.py
import asyncio
from src.services.ai_model_service_enhanced import EnhancedAIModelService

async def test_fallback():
    service = EnhancedAIModelService()
    
    # 模擬 Gemini 配額用盡
    service._model_health["gemini-1.5-flash"]["quota_exhausted"] = True
    service._model_health["gemini-1.5-flash"]["failures"] = 3
    
    # 測試是否切換到 OpenAI
    result = await service.generate_user_guidance(
        "CNC車床今天不良率",
        "測試提示詞"
    )
    
    print(f"結果: {result[0]}")
    print(f"信心度: {result[1]}")
    
    # 驗證結果是否友善
    is_friendly = "您好" in result[0] or "抱歉" in result[0]
    print(f"友善回應: {is_friendly}")

if __name__ == "__main__":
    asyncio.run(test_fallback())
```

### 完整流程測試
```bash
# 執行完整備用機制測試
python test_fallback_mechanism.py

# 預期輸出
# 結果: 您好！很抱歉，目前系統無法直接查詢...
# 信心度: 0.9
# 友善回應: True
```

### Web API 測試
```bash
# 測試實際 Web 端點
curl -X POST http://localhost:8000/test-llm \
  -H "Content-Type: application/json" \
  -d '{"text":"CNC車床今天不良率"}' | jq -r '.response'

# 預期：友善的指導而非技術性描述
```

## 🔄 修復流程模板

### Step 1: 診斷問題
```bash
# 執行診斷腳本
./diagnose-fallback.sh

# 或手動檢查
python -c "
from src.services.ai_model_service_enhanced import EnhancedAIModelService
service = EnhancedAIModelService()
print('備用模型:', service.fallback_models)
print('模型健康:', [(m, service._is_model_healthy(m)) for m in service.models])
"
```

### Step 2: 實施修復
```python
# 1. 確保增強版服務有完整的 generate_user_guidance 方法
# 2. 檢查 _is_model_healthy 邏輯
# 3. 驗證錯誤識別模式
# 4. 確認系統提示詞正確
```

### Step 3: 驗證修復
```bash
# 1. 單獨測試
python test_fallback_mechanism.py

# 2. 重啟服務
./fix-env-diff.sh

# 3. Web API 測試
curl 測試端點

# 4. 完整測試
./quick-test-vocabulary.sh
```

## 📊 監控與日誌

### 關鍵日誌模式
```
✅ 正常切換
2025-06-30 20:41:25 [error] ❌ 模型 gemini-1.5-flash 配額已用盡: 429 Too Many Requests
2025-06-30 20:41:25 [info] 🔄 切換到備用模型...
2025-06-30 20:41:25 [info] 🔄 嘗試使用模型: gpt-4o-mini
2025-06-30 20:41:29 [info] ✅ 模型 gpt-4o-mini 用戶指導生成成功

❌ 異常情況
2025-06-30 20:41:25 [error] ❌ 所有 AI 模型都調用失敗，返回基礎結果
```

### 健康狀態監控
```bash
# 檢查模型健康狀態
curl -s http://localhost:8000/models | jq '.models[] | {name: .name, healthy: .healthy, failures: .failures}'
```

## 🚀 自動化腳本

### diagnose-fallback.sh
```bash
#!/bin/bash
echo "🔍 備用機制診斷..."

# 檢查環境變數
echo "1️⃣ 環境變數檢查"
cd apps/bot && python -c "
from dotenv import load_dotenv
import os
load_dotenv()
google_key = 'GOOGLE_API_KEY' in os.environ
openai_key = 'OPENAI_API_KEY' in os.environ
print(f'Google API: {\"✅\" if google_key else \"❌\"}')
print(f'OpenAI API: {\"✅\" if openai_key else \"❌\"}')
"

# 檢查服務配置
echo "2️⃣ 服務配置檢查"
cd apps/bot && python -c "
from src.services.ai_model_service_enhanced import EnhancedAIModelService
service = EnhancedAIModelService()
print(f'預設模型: {service.default_model}')
print(f'備用模型: {service.fallback_models}')
print(f'方法存在: {hasattr(service, \"generate_user_guidance\")}')
"

# 測試備用機制
echo "3️⃣ 備用機制測試"
cd apps/bot && python -c "
import asyncio
from src.services.ai_model_service_enhanced import EnhancedAIModelService

async def test():
    service = EnhancedAIModelService()
    # 模擬 Gemini 問題
    service._model_health['gemini-1.5-flash']['quota_exhausted'] = True
    
    result = await service.generate_user_guidance('測試', '測試提示')
    print(f'備用結果: {result[0][:50]}...')
    print(f'信心度: {result[1]}')

asyncio.run(test())
"

echo "✅ 診斷完成"
```

### fix-fallback.sh
```bash
#!/bin/bash
echo "🔧 修復備用機制..."

# 1. 檢查必要文件
if [ ! -f "apps/bot/src/services/ai_model_service_enhanced.py" ]; then
    echo "❌ 增強版服務文件不存在"
    exit 1
fi

# 2. 語法檢查
python -m py_compile apps/bot/src/services/ai_model_service_enhanced.py
if [ $? -ne 0 ]; then
    echo "❌ 語法錯誤，請先修復"
    exit 1
fi

# 3. 重啟服務
echo "重啟服務..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
sleep 2
./start-production.sh &
sleep 10

# 4. 測試修復
echo "測試修復結果..."
RESULT=$(curl -s -X POST http://localhost:8000/test-llm \
  -H "Content-Type: application/json" \
  -d '{"text":"CNC車床今天不良率"}' | jq -r '.response')

if [[ "$RESULT" == *"您好"* ]] || [[ "$RESULT" == *"抱歉"* ]]; then
    echo "✅ 備用機制修復成功"
else
    echo "❌ 修復失敗: $RESULT"
fi
```

## 📝 故障記錄模板

```markdown
## 備用機制故障記錄

**日期**: YYYY-MM-DD  
**故障類型**: Gemini → OpenAI 切換失敗

### 故障現象
- Gemini 錯誤: 429 Too Many Requests
- OpenAI 切換: [ ] 成功 [ ] 失敗
- 最終回應: 

### 診斷結果
- [ ] 環境變數配置正確
- [ ] 服務實例為增強版
- [ ] 方法存在且正確實現
- [ ] 模型健康檢查正常

### 根本原因


### 修復措施


### 驗證結果
- [ ] 單獨測試通過
- [ ] Web API 測試通過
- [ ] 完整流程正常

### 預防措施

```

---

**使用建議**: 當發現 AI 模型切換不正常時，立即參考此指南  
**更新原則**: 每次遇到新的備用機制問題都要更新此文檔  
**相關文檔**: [問題解決流程標準指南](./問題解決流程標準指南.md)