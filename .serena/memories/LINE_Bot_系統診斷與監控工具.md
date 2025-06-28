# LINE Bot 系統診斷與監控工具

## 核心診斷指令
### 1. 服務健康檢查
```bash
# 檢查服務狀態
curl -s http://localhost:8000/health | jq

# 預期結果
{
  "status": "healthy",
  "checks": {
    "service_factory": {"services_count": 28},
    "ai_service": {"status": "ok"},
    "nl_to_sql": {"status": "ok"}
  }
}
```

### 2. 進程管理
```bash
# 檢查 uvicorn 進程
ps aux | grep uvicorn

# 安全重啟服務
pkill -f uvicorn
sleep 2
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000 &
```

### 3. 日誌監控
```bash
# 查看服務日誌
tail -f /tmp/linebot_new.log

# 關鍵日誌標記
# ✅ "LLM 成功生成用戶指導" (confidence=0.85)
# ✅ "OpenAI解析完成" (model=gpt-4o-mini)
# ⚠️ "檢測到空 SQL 查詢" (需要檢查)
# ❌ "ConnectionError" (API問題)
```

## 性能指標監控
### 關鍵指標
- **查詢成功率**: 目標 100%
- **回應時間**: < 1.5秒
- **服務註冊**: 28個服務正常
- **健康檢查**: 6項全部通過
- **LLM confidence**: > 0.8

### 故障排除檢查清單
```bash
□ API狀態正常 (./check_api_quota.sh)
□ 服務運行正常 (curl http://localhost:8000/health)
□ 查詢功能正常 (測試M001機台查詢)
□ LLM指導正常 (檢查日誌中的confidence值)
□ 錯誤日誌無異常 (tail -f logs/webhook.log)
```

## 緊急恢復程序
1. **立即診斷**: `./check_api_quota.sh`
2. **切換緊急模式**: `./fix_ai_emergency.sh`
3. **重啟服務**: `pkill -f uvicorn && ./start-production.sh`
4. **驗證恢復**: `curl http://localhost:8000/health`