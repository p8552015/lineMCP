# 自然語言轉 SQL 改善系統測試指南

## 🎯 測試目標

本測試套件用於驗證改善後的自然語言轉 SQL 系統，特別是**多欄位關鍵字提取**功能。系統現在能夠從單一查詢（如「M001機台稼動率」）中同時提取多個資料欄位。

## 📋 測試腳本清單

### 1. **quick-test-vocabulary.sh** - 快速驗證腳本
最簡單的測試腳本，用於快速驗證核心功能。

```bash
./quick-test-vocabulary.sh
```

**測試內容**：
- 服務健康檢查
- 4 個核心查詢測試
- 顯示預期結果解讀

**適用場景**：快速驗證系統是否正常運作

---

### 2. **test-vocabulary-curl.sh** - 基礎功能測試
專注於多欄位提取和同義詞識別的測試。

```bash
./test-vocabulary-curl.sh
```

**測試內容**：
- 基本多欄位提取（機台+指標）
- 複雜多欄位提取（部門+時間+指標）
- 同義詞識別（稼動率/使用率/利用率）
- 直接 SQL 查詢

**適用場景**：驗證詞彙庫核心功能

---

### 3. **test-vocabulary-api.sh** - API 端點測試
測試系統的 API 端點和效能。

```bash
./test-vocabulary-api.sh
```

**測試內容**：
- 健康檢查 API
- 批量查詢測試
- 效能基準測試（5 次平均）
- 錯誤處理驗證
- 詞彙庫統計

**適用場景**：API 功能和效能評估

---

### 4. **test-integration-vocabulary.sh** - 系統整合測試
測試新功能與現有 LINE Bot 的整合。

```bash
./test-integration-vocabulary.sh
```

**測試內容**：
- 現有指令兼容性（/help, /status）
- 多欄位查詢整合
- SQL 指令整合
- 錯誤處理機制
- 簡單效能測試

**適用場景**：確保新功能不影響現有系統

---

### 5. **test-nl-to-sql-improvements.sh** - 完整測試套件
最全面的測試腳本，涵蓋所有改善功能。

```bash
./test-nl-to-sql-improvements.sh
```

**測試內容**：
- 多欄位關鍵字提取
- 同義詞和語義理解
- 時間維度識別
- 邊界情況處理
- SQL 查詢執行
- 複雜業務場景
- 效能測試（10 次）

**適用場景**：完整的系統驗證

---

## 🚀 使用步驟

### 1. 啟動服務
```bash
./start-production.sh
```

### 2. 等待服務就緒
確保看到以下訊息：
```
✅ 服務啟動成功！
API 服務運行在: http://localhost:8000
```

### 3. 執行測試
建議按照以下順序執行：

```bash
# 1. 快速驗證
./quick-test-vocabulary.sh

# 2. 核心功能測試
./test-vocabulary-curl.sh

# 3. 整合測試
./test-integration-vocabulary.sh

# 4. 完整測試（可選）
./test-nl-to-sql-improvements.sh
```

## 📊 預期結果

### 成功的多欄位提取範例：

**查詢**：`M001機台稼動率`
**提取結果**：
- machine_id: "M001"
- metric_type: "utilization_rate"

**查詢**：`生產部門本週的OEE指標`
**提取結果**：
- department: "production"
- time_period: "this_week"
- metric_type: "oee"

**查詢**：`品質部門M002銑床即時產量數據`
**提取結果**：
- department: "quality"
- machine_id: "M002"
- machine_type: "MILLING_MACHINE"
- time_period: "real_time"
- metric_type: "throughput"

## 🔧 疑難排解

### 問題 1：服務未啟動
**症狀**：`服務無回應` 或 `Connection refused`
**解決方案**：
```bash
# 確認服務狀態
./status.sh

# 重新啟動服務
./start-production.sh
```

### 問題 2：詞彙庫未載入
**症狀**：查詢無法正確識別關鍵字
**解決方案**：
1. 檢查詞彙庫檔案是否存在：
   ```bash
   ls -la apps/bot/src/services/nl_to_sql/config/manufacturing_vocabulary_database.yaml
   ```
2. 查看服務啟動日誌中是否有載入成功訊息

### 問題 3：回應時間過長
**症狀**：查詢回應超過 2 秒
**解決方案**：
1. 檢查系統資源使用情況
2. 確認 LLM API 連線正常
3. 考慮關閉 LLM 增強模式進行測試

## 📁 相關檔案

### 核心實作
- **詞彙庫配置**：`apps/bot/src/services/nl_to_sql/config/manufacturing_vocabulary_database.yaml`
- **智能解譯器**：`apps/bot/src/services/nl_to_sql/services/intelligent_vocabulary_interpreter.py`

### 文檔指南
- **改善計劃書**：`task/任務規劃書/spec_自然語言轉SQL深度改善計劃.md`
- **詞彙庫管理**：`task/任務規劃書/spec_製造業詞彙庫智能管理系統.md`
- **使用者指南**：`task/開發指南/製造業詞彙庫使用者更新指南.md`

### 測試工具
- **Python 測試**：`test_vocabulary_interpreter.py`
- **CURL 測試**：本目錄下的所有 `.sh` 腳本

## 💡 測試建議

1. **定期執行**：建議每次更新詞彙庫後執行快速測試
2. **監控效能**：關注平均回應時間，應保持在 500ms 以內
3. **收集案例**：記錄失敗的查詢案例，用於改善詞彙庫
4. **漸進測試**：從簡單測試開始，逐步執行複雜測試

## 🎯 成功標準

- ✅ 所有基本查詢正確識別（準確率 > 90%）
- ✅ 多欄位提取功能正常（可同時提取 2-4 個欄位）
- ✅ 同義詞識別正確（稼動率/使用率/利用率）
- ✅ 平均回應時間 < 500ms
- ✅ 錯誤處理適當（無系統崩潰）

---

**最後更新**：2025-06-28
**維護者**：系統開發團隊