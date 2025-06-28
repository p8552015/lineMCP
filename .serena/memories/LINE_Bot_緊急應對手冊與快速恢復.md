# LINE Bot 緊急應對手冊與快速恢復

## 常見問題快速診斷
### 1. tuple 錯誤症狀
**錯誤**: `'tuple' object has no attribute 'strip'`
**快速檢查**: 
```bash
grep -n "ai_response.strip()" apps/bot/src/services/nl_to_sql_service.py
```
**修復要點**: 添加 `isinstance(ai_response, tuple)` 檢查

### 2. API 認證失敗
**症狀**: 429 (配額用盡) 或 401 (認證失敗)
**快速診斷**: `./check_api_quota.sh`
**修復策略**: 
- Gemini 429 → 切換到 OpenAI
- OpenAI 401 → 檢查 API key 格式
- 全部失效 → 啟用純規則模式

### 3. 空 SQL 查詢問題
**症狀**: "檢測到空 SQL 查詢"
**快速檢查**: 測試 `all_machines` 查詢類型
**修復要點**: 檢查查詢建構器和模板管理

## 30秒快速恢復程序
```bash
# 1. 立即診斷 (5秒)
curl -f http://localhost:8000/health || echo "SERVICE DOWN"

# 2. 檢查 API (10秒)  
./check_api_quota.sh | grep -E "✅|❌"

# 3. 緊急重啟 (15秒)
pkill -f uvicorn
sleep 2
cd /Users/yen/Desktop/lineMCP/apps/bot
nohup poetry run uvicorn src.main:app --port 8000 &
sleep 5
curl -f http://localhost:8000/health
```

## 2分鐘完整恢復程序
```bash
# 1. 全面診斷
./check_api_quota.sh
curl -s http://localhost:8000/health | jq '.checks'

# 2. 如果 API 失效，啟用緊急模式
if [[ $? -ne 0 ]]; then
    ./fix_ai_emergency.sh
fi

# 3. 功能驗證
echo "測試查詢: M001 機台狀態"
# 通過 LINE Bot 或直接 API 測試

# 4. 監控確認
tail -f /tmp/linebot_new.log | grep -E "✅|❌|⚠️" | head -10
```

## 關鍵檔案備份與恢復
### 核心配置檔案
```bash
# 備份關鍵配置
cp apps/bot/.env apps/bot/.env.backup
cp apps/bot/src/services/nl_to_sql_service.py apps/bot/src/services/nl_to_sql_service.py.backup

# 緊急回滾
git checkout HEAD~1 -- apps/bot/src/services/nl_to_sql_service.py
```

### 最小工作配置
```bash
# .env 最小配置
LINE_CHANNEL_ACCESS_TOKEN=xxxxx
LINE_CHANNEL_SECRET=xxxxx
AI_MODEL_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxxx
AI_ENABLE_ENHANCED_NL=true
AI_FALLBACK_TO_RULES=true
```

## 聯絡支援清單
1. **GitHub Issues**: https://github.com/p8552015/lineMCP/issues
2. **完整修復指南**: `/task/最終報告/LINE_Bot_tuple錯誤修復專案_完整指南.md`
3. **系統日誌位置**: `/tmp/linebot_new.log`
4. **健康檢查端點**: `http://localhost:8000/health`

## 預防性維護檢查
### 每日檢查 (自動化)
- API 配額狀態
- 服務健康指標
- 錯誤日誌監控

### 每週檢查 (手動)
- 完整功能測試
- 效能指標評估
- 配置檔案審查