# LINE Bot API認證問題診斷與修復

## 問題識別
- **Gemini API**: 429 錯誤（配額用盡，50次/天免費額度）
- **OpenAI API**: 401 錯誤（API key 無效）

## 診斷工具
### API配額檢查腳本 (`check_api_quota.sh`)
```bash
# 檢查 Gemini API
response=$(curl -s -H "Content-Type: application/json" \
    -d '{"contents":[{"parts":[{"text":"hello"}]}]}' \
    -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=$GOOGLE_API_KEY")

# 檢查 OpenAI API  
response=$(curl -s -H "Authorization: Bearer $OPENAI_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"hi"}],"max_tokens":1}' \
    "https://api.openai.com/v1/chat/completions")
```

## 解決方案
### 1. 環境變數修復 (`.env`)
```bash
# 切換主要提供商
AI_MODEL_PROVIDER=openai  # 從 google 改為 openai

# 更新有效的 API key
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxx

# 重新啟用 AI 功能
AI_ENABLE_ENHANCED_NL=true
AI_FALLBACK_TO_RULES=true
```

### 2. 緊急修復腳本 (`fix_ai_emergency.sh`)
- 自動停用 AI 模型
- 啟用純規則模式
- 重啟服務並驗證

## 最佳實踐
1. **多重備援**: 配置 Gemini + OpenAI 雙重保障
2. **配額監控**: 定期檢查 API 使用量
3. **優雅降級**: API 失效時自動切換到規則模式