# spec_SQL模板欄位名稱不一致修復專案

## 🎯 專案目標

修復 LINE Bot 在生產環境中出現的 SQL 查詢錯誤，主要問題是 SQL 模板中的欄位名稱與實際資料庫結構不一致，導致 `column m.machine_id does not exist` 錯誤。

## 🔍 問題分析

### 核心問題
從日誌分析發現，`start-production.sh` 腳本運行正常，但 LINE Bot webhook 查詢失敗，根本原因是：

1. **欄位名稱不一致**：
   - SQL模板使用：`m.machine_id`, `m.machine_name`, `m.department`  
   - 實際資料庫：`m.id`, `m.name`, `m.location`

2. **查詢模板錯誤**：
   - `production_stats` 模板中的 `COUNT(DISTINCT m.machine_id)` 應該是 `COUNT(DISTINCT m.id)`
   - `all_machines` 模板中的 JOIN 條件錯誤

3. **資料類型轉換問題**：
   - `fault_analysis` 查詢中出現字串和整數相加錯誤

### 影響範圍
- ❌ 生產統計報告查詢失敗
- ❌ 故障記錄查詢失敗  
- ❌ 所有機台狀態查詢可能有問題
- ✅ M001 特定機台查詢正常（已修復）

## 📋 任務執行計劃

<!-- TASKS START -->
| ID | 任務 | 描述 | 優先級 | 負責 | 狀態 | 開始 | 結束 |
|---|---|---|---|---|---|---|---|
| T-01 | 資料庫結構分析 | 詳細檢查實際資料庫結構與SQL模板的差異 | High | 開發者 | DONE | 2025-06-26 13:20 | 2025-06-26 13:35 |
| T-02 | SQL模板修正 | 修正所有SQL模板中的欄位名稱不一致問題 | Critical | 開發者 | DONE | 2025-06-26 13:35 | 2025-06-26 13:45 |
| T-03 | 資料類型修復 | 修復故障分析中的資料類型轉換問題 | High | 開發者 | DONE | 2025-06-26 13:45 | 2025-06-26 13:50 |
| T-04 | 測試驗證 | 使用 curl 測試所有查詢功能 | High | 開發者 | DONE | 2025-06-26 13:50 | 2025-06-26 14:05 |
| T-05 | 系統整合測試 | 確保修復不影響現有功能 | Medium | 開發者 | DONE | 2025-06-26 14:05 | 2025-06-26 14:15 |
<!-- TASKS END -->

## 🔧 技術實作計劃

### Phase 1: 資料庫結構對照表
建立完整的欄位映射表：

```
SQL模板欄位 → 實際資料庫欄位
─────────────────────────────
m.machine_id → m.id
m.machine_name → m.name  
m.department → m.location
u.machine_id → u.machine_id (正確)
```

### Phase 2: SQL模板修正策略
1. **production_stats 模板**：
   - 修正 `COUNT(DISTINCT m.machine_id)` → `COUNT(DISTINCT m.id)`
   - 修正 JOIN 條件：`u.machine_id = u.machine_id` → 檢查正確的關聯

2. **all_machines 模板**：
   - 統一欄位名稱使用
   - 確保 JOIN 條件正確

3. **fault_analysis 模板**：
   - 修復資料類型轉換問題
   - 確保聚合函數正確處理

### Phase 3: 測試策略
1. **單元測試**：每個 SQL 模板獨立測試
2. **整合測試**：透過 webhook 測試完整流程
3. **回歸測試**：確保 M001 查詢仍正常運作

## 🎯 預期成果

### 修復目標
- ✅ `production_stats` 查詢正常返回部門統計
- ✅ `fault_analysis` 查詢正常返回故障統計  
- ✅ `all_machines` 查詢正常返回機台概覽
- ✅ 所有 webhook 查詢通過 curl 測試

### 品質標準
- 零 SQL 語法錯誤
- 零欄位名稱不存在錯誤
- 零資料類型轉換錯誤
- 回應時間 < 2秒

## ⚠️ 風險控制

### 潛在風險
1. **修改影響現有功能**：M001 查詢可能受影響
2. **JOIN 條件錯誤**：可能導致資料不正確
3. **效能問題**：修正後的查詢可能較慢

### 緩解措施
1. **備份當前版本**：修改前先備份工作版本
2. **漸進式修復**：一次修復一個模板並測試
3. **快速回滾**：準備快速恢復機制

## 🧪 測試腳本

### curl 測試命令
```bash
# 測試 1: 生產統計報告
curl -X POST http://localhost:8000/Webhook \
  -H "Content-Type: application/json" \
  -H "X-Line-Signature: DEV_BYPASS_SIGNATURE" \
  -d '{"events":[{"type":"message","message":{"type":"text","text":"生產統計報告"},"source":{"type":"user","userId":"test-user"},"replyToken":"test-token","timestamp":1640995200000}]}'

# 測試 2: 近期故障記錄  
curl -X POST http://localhost:8000/Webhook \
  -H "Content-Type: application/json" \
  -H "X-Line-Signature: DEV_BYPASS_SIGNATURE" \
  -d '{"events":[{"type":"message","message":{"type":"text","text":"近期故障記錄"},"source":{"type":"user","userId":"test-user"},"replyToken":"test-token","timestamp":1640995200000}]}'

# 測試 3: 查看所有機台
curl -X POST http://localhost:8000/Webhook \
  -H "Content-Type: application/json" \
  -H "X-Line-Signature: DEV_BYPASS_SIGNATURE" \
  -d '{"events":[{"type":"message","message":{"type":"text","text":"查看所有機台"},"source":{"type":"user","userId":"test-user"},"replyToken":"test-token","timestamp":1640995200000}]}'

# 測試 4: M001機台稼動率 (回歸測試)
curl -X POST http://localhost:8000/Webhook \
  -H "Content-Type: application/json" \
  -H "X-Line-Signature: DEV_BYPASS_SIGNATURE" \
  -d '{"events":[{"type":"message","message":{"type":"text","text":"M001機台稼動率"},"source":{"type":"user","userId":"test-user"},"replyToken":"test-token","timestamp":1640995200000}]}'
```

## 📊 成功標準

### 完成條件
- [ ] 所有 SQL 模板欄位名稱正確
- [ ] 所有 curl 測試通過 
- [ ] 無 SQL 語法錯誤日誌
- [ ] 回應時間符合要求
- [ ] M001 查詢功能不受影響

### 驗收測試
1. **功能測試**：所有查詢類型都能正常返回資料
2. **錯誤處理**：不再出現欄位不存在錯誤
3. **效能測試**：查詢回應時間在合理範圍內
4. **整合測試**：LINE Bot 完整對話流程正常

---

## 📝 實作注意事項

### SOLID 原則遵循
- **單一職責**：每個 SQL 模板只負責一種查詢類型
- **開放封閉**：修復時不改變介面，只修正實作
- **依賴反轉**：確保上層服務不依賴具體的 SQL 語法

### 程式碼品質
- 所有修改必須通過語法檢查
- 使用參數化查詢防止 SQL 注入
- 適當的錯誤處理和日誌記錄

### 文檔更新
- 更新 SQL 模板文檔
- 記錄欄位映射關係
- 更新測試案例文檔 