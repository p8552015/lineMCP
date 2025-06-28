# AI 模型啟動流程檢查指南

## 📋 問題記錄

### 重複出現的問題
1. **Gemini API**: 429 Too Many Requests (配額用盡)
2. **OpenAI API**: 401 Unauthorized (認證失敗)
3. **結果**: 系統回退到備用指導，但無法提供真正的 AI 智能回應

### 問題發生時間記錄
- 2025-06-28 12:28 - Gemini 429 + OpenAI 401
- 2025-06-28 12:21 - Gemini 429 + OpenAI 401  
- 2025-06-28 12:17 - Gemini 429 + OpenAI 401

## 🔍 AI 模型狀態檢查流程

### 1. 環境變數檢查
```bash
# 檢查關鍵 API keys
cd /Users/yen/Desktop/lineMCP/apps/bot
echo "GOOGLE_API_KEY: ${GOOGLE_API_KEY:0:20}..."
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:0:20}..."
echo "AI_MODEL_PROVIDER: $AI_MODEL_PROVIDER"
```

### 2. Gemini API 狀態檢查
```bash
# 測試 Gemini API 連接和配額
curl -H "Content-Type: application/json" \
     -d '{"contents":[{"parts":[{"text":"test"}]}]}' \
     -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=$GOOGLE_API_KEY"
```

**預期結果**:
- ✅ 200 OK: API 正常
- ❌ 429: 配額用盡
- ❌ 403: API key 無效

### 3. OpenAI API 狀態檢查
```bash
# 測試 OpenAI API 連接
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"test"}],"max_tokens":5}' \
     "https://api.openai.com/v1/chat/completions"
```

**預期結果**:
- ✅ 200 OK: API 正常
- ❌ 401: API key 無效
- ❌ 429: 速率限制

### 4. 系統內建 AI 模型檢查
```bash
# 執行內建的 AI 模型測試
cd /Users/yen/Desktop/lineMCP/apps/bot
python -c "
import asyncio
import sys
sys.path.append('src')
from services.ai_model_service import AIModelService

async def test_ai_models():
    service = AIModelService()
    print(f'可用模型: {list(service.models.keys())}')
    print(f'預設模型: {service.default_model}')
    
    # 測試每個模型
    for model in service.models.keys():
        try:
            result = await service.enhance_natural_language_query(
                'test query', {}, model
            )
            print(f'✅ {model}: 成功')
        except Exception as e:
            print(f'❌ {model}: {str(e)[:100]}')

asyncio.run(test_ai_models())
"
```

## 🛠️ 修復流程

### 步驟 1: API Key 驗證
1. **檢查 Gemini API Key**:
   - 前往 [Google AI Studio](https://makersuite.google.com/app/apikey)
   - 確認 API key 有效且有配額
   - 檢查使用限制和配額狀態

2. **檢查 OpenAI API Key**:
   - 前往 [OpenAI Platform](https://platform.openai.com/api-keys)
   - 確認 API key 有效且有餘額
   - 檢查使用限制和配額狀態

### 步驟 2: 配額管理
```bash
# 建立 API 配額檢查腳本
cat > check_api_quota.sh << 'EOF'
#!/bin/bash

echo "🔍 檢查 API 配額狀態..."

# Gemini 配額檢查
echo "📊 Gemini API 狀態:"
response=$(curl -s -H "Content-Type: application/json" \
    -d '{"contents":[{"parts":[{"text":"hello"}]}]}' \
    -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=$GOOGLE_API_KEY")

if echo "$response" | grep -q "error"; then
    echo "❌ Gemini API 錯誤:"
    echo "$response" | jq '.error' 2>/dev/null || echo "$response"
else
    echo "✅ Gemini API 正常"
fi

# OpenAI 配額檢查
echo -e "\n📊 OpenAI API 狀態:"
response=$(curl -s -H "Authorization: Bearer $OPENAI_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"hi"}],"max_tokens":1}' \
    "https://api.openai.com/v1/chat/completions")

if echo "$response" | grep -q "error"; then
    echo "❌ OpenAI API 錯誤:"
    echo "$response" | jq '.error' 2>/dev/null || echo "$response"
else
    echo "✅ OpenAI API 正常"
fi
EOF

chmod +x check_api_quota.sh
./check_api_quota.sh
```

### 步驟 3: 備用方案配置
```bash
# 修改 .env 設置為優先使用 OpenAI（如果 Gemini 配額用盡）
sed -i.bak 's/AI_MODEL_PROVIDER=google/AI_MODEL_PROVIDER=openai/' apps/bot/.env

# 或設為自動切換
sed -i.bak 's/AI_MODEL_PROVIDER=google/AI_MODEL_PROVIDER=auto/' apps/bot/.env
```

## 🚨 緊急修復方案

當所有 AI 模型都失效時，啟用純規則模式：

```bash
# 停用 AI 模型，僅使用規則解析
cat >> apps/bot/.env << 'EOF'

# 緊急模式：停用 AI 模型
AI_ENABLE_ENHANCED_NL=false
AI_FALLBACK_TO_RULES=true
EOF

# 重啟服務
pkill -f uvicorn
sleep 2
cd /Users/yen/Desktop/lineMCP && ./start-production.sh
```

## 📊 監控和預警

### 建立 API 狀態監控
```python
# api_monitor.py
import asyncio
import httpx
import os
from datetime import datetime

async def check_api_status():
    """檢查所有 AI API 狀態"""
    results = {}
    
    # Gemini API 檢查
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={os.getenv('GOOGLE_API_KEY')}",
                json={"contents":[{"parts":[{"text":"test"}]}]},
                timeout=10
            )
            results['gemini'] = {
                'status': response.status_code,
                'available': response.status_code == 200
            }
    except Exception as e:
        results['gemini'] = {'status': 'error', 'available': False, 'error': str(e)}
    
    # OpenAI API 檢查
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 1
                },
                timeout=10
            )
            results['openai'] = {
                'status': response.status_code,
                'available': response.status_code == 200
            }
    except Exception as e:
        results['openai'] = {'status': 'error', 'available': False, 'error': str(e)}
    
    # 輸出結果
    print(f"[{datetime.now()}] API 狀態檢查:")
    for api, result in results.items():
        status = "✅" if result['available'] else "❌"
        print(f"  {status} {api}: {result['status']}")
        if 'error' in result:
            print(f"    錯誤: {result['error']}")
    
    return results

if __name__ == "__main__":
    asyncio.run(check_api_status())
```

### 自動修復腳本
```bash
# auto_fix_ai.sh
#!/bin/bash

echo "🔧 AI 模型自動修復流程..."

# 1. 檢查 API 狀態
python api_monitor.py

# 2. 根據結果調整配置
if ! grep -q "✅ gemini" <(python api_monitor.py); then
    echo "⚠️ Gemini API 失效，切換到 OpenAI"
    sed -i.bak 's/AI_MODEL_PROVIDER=.*/AI_MODEL_PROVIDER=openai/' apps/bot/.env
fi

if ! grep -q "✅ openai" <(python api_monitor.py); then
    echo "⚠️ OpenAI API 失效，檢查 Gemini"
    if grep -q "✅ gemini" <(python api_monitor.py); then
        sed -i.bak 's/AI_MODEL_PROVIDER=.*/AI_MODEL_PROVIDER=google/' apps/bot/.env
    else
        echo "🚨 所有 API 失效，啟用純規則模式"
        echo "AI_ENABLE_ENHANCED_NL=false" >> apps/bot/.env
    fi
fi

# 3. 重啟服務
echo "🔄 重啟服務..."
pkill -f uvicorn
sleep 3
./start-production.sh &
```

## 📝 故障排除清單

### 常見問題和解決方案

1. **Gemini 429 錯誤**:
   - ✅ 等待配額重置 (通常24小時)
   - ✅ 切換到 OpenAI
   - ✅ 申請配額增加

2. **OpenAI 401 錯誤**:
   - ✅ 檢查 API key 格式 (sk-proj-...)
   - ✅ 確認帳戶餘額
   - ✅ 檢查 API key 權限

3. **所有 API 失效**:
   - ✅ 啟用純規則模式
   - ✅ 提供預設回應
   - ✅ 通知管理員

### 預防措施

1. **配額監控**: 每日檢查 API 使用量
2. **多重備援**: 至少配置兩個不同的 AI 提供商
3. **優雅降級**: 當 AI 失效時提供有意義的規則回應
4. **自動切換**: 實現智能的 API 切換機制

## 🎯 下次發生此問題時的快速操作

```bash
# 1. 快速診斷
cd /Users/yen/Desktop/lineMCP
./check_api_quota.sh

# 2. 如果需要切換 API
# 切換到 OpenAI
echo "AI_MODEL_PROVIDER=openai" >> apps/bot/.env

# 或停用 AI (緊急模式)
echo "AI_ENABLE_ENHANCED_NL=false" >> apps/bot/.env

# 3. 重啟服務
pkill -f uvicorn; sleep 2; ./start-production.sh
```

---

**創建日期**: 2025-06-28  
**更新記錄**: 記錄重複 API 失效問題並建立標準檢查流程