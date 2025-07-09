# spec_空SQL查詢LLM指導修復專案.md

## 📋 專案目標

修復 LINE Bot 空 SQL 查詢處理中 LLM 用戶指導生成失敗的問題，具體為 `'tuple' object has no attribute 'strip'` 錯誤。

## 🔍 問題分析

### 根本原因分析
1. **API 介面不匹配**：`enhance_natural_language_query` 方法返回 `tuple[str, float]`
2. **錯誤調用**：代碼期望返回字符串，直接調用 `.strip()` 方法
3. **錯誤位置**：`/apps/bot/src/services/nl_to_sql_service.py:439`

### 錯誤日誌分析
```
❌ LLM 用戶指導生成失敗 error='tuple' object has no attribute 'strip'
```

### 受影響功能
- 查看所有機台 → 空SQL查詢 → LLM指導生成失敗
- M005 機台運行情況 → 空SQL查詢 → LLM指導生成失敗
- 所有需要 LLM 智能指導的場景

## 🛠️ 技術修復方案

### 方案A：修正返回值處理（推薦）
在 `nl_to_sql_service.py` 中正確處理 tuple 返回值：
```python
# 修改前（第433-439行）
ai_response = await self.ai_model_service.enhance_natural_language_query(
    user_query=prompt,
    database_schema={}
)
if ai_response and ai_response.strip():

# 修改後
ai_response = await self.ai_model_service.enhance_natural_language_query(
    user_query=prompt,
    database_schema={}
)
if isinstance(ai_response, tuple):
    enhanced_query, confidence = ai_response
    if enhanced_query and enhanced_query.strip():
        return enhanced_query.strip()
```

### 方案B：修改 AI 服務介面（備用）
修改 `enhance_natural_language_query` 方法增加僅返回字符串的選項。

## 📊 任務執行表

<!-- TASKS START -->
| ID | 任務 | 描述 | 優先級 | 負責 | 狀態 | 開始 | 結束 |
|---|---|---|---|---|---|---|---|
| T-01 | 問題診斷完成 | 使用serena檢查錯誤原因並定位具體問題 | High | 開發者 | DONE | 2025-06-28 12:10 | 2025-06-28 12:25 |
| T-02 | 代碼修復 | 修正 nl_to_sql_service.py 中的 tuple 處理錯誤 | High | 開發者 | DONE | 2025-06-28 12:30 | 2025-06-28 12:35 |
| T-03 | 單元測試 | 為修復的代碼添加測試用例 | Medium | 開發者 | BLOCKED | - | - |
| T-04 | 功能驗證 | 測試「查看所有機台」和「M005機台運行情況」功能 | High | 開發者 | DONE | 2025-06-28 12:35 | 2025-06-28 12:45 |
| T-05 | 系統整合測試 | 執行完整系統測試確保無其他破壞 | High | 開發者 | DONE | 2025-06-28 12:35 | 2025-06-28 12:45 |
| T-06 | 代碼品質檢查 | 執行 lint, format, type check | Medium | 開發者 | DONE | 2025-06-28 12:30 | 2025-06-28 12:35 |
| T-07 | 文檔更新 | 更新相關技術文檔和註釋 | Low | 開發者 | DONE | 2025-06-28 12:45 | 2025-06-28 12:50 |
<!-- TASKS END -->

## 🧪 測試驗證計劃

### 必要測試案例
1. **基本功能測試**
   - 輸入：「查看所有機台」
   - 期望：正常返回 LLM 生成的用戶指導
   
2. **特定機台測試**
   - 輸入：「M005 機台運行情況」
   - 期望：正常返回 LLM 生成的用戶指導

3. **錯誤邊界測試**
   - 輸入：「今天天氣好嗎」
   - 期望：正確識別為非業務查詢並提供指導

### 系統測試標準
- ✅ 啟動腳本：`./start-production.sh` 執行成功
- ✅ 核心功能：M001機台稼動率查詢正常
- ✅ 錯誤日誌：無 `'tuple' object has no attribute 'strip'` 錯誤
- ✅ LLM 指導：正常生成智能用戶指導

## 🔧 實施細節

### 修復位置
**文件**: `/apps/bot/src/services/nl_to_sql_service.py`
**函數**: `_generate_user_guidance` (第396-451行)
**問題行**: 第439行

### 修復代碼
```python
# 在第433行之後添加正確的 tuple 處理
ai_response = await self.ai_model_service.enhance_natural_language_query(
    user_query=prompt,
    database_schema={}
)

# 正確處理 tuple 返回值
if isinstance(ai_response, tuple):
    enhanced_query, confidence = ai_response
    if enhanced_query and enhanced_query.strip():
        logger.info("✅ LLM 成功生成用戶指導", 
                   input_length=len(user_input),
                   response_length=len(enhanced_query),
                   confidence=confidence)
        return enhanced_query.strip()
    else:
        return self._get_fallback_guidance(query_type, parameters)
else:
    # 處理意外的返回類型
    logger.warning("⚠️ AI服務返回意外類型", response_type=type(ai_response))
    return self._get_fallback_guidance(query_type, parameters)
```

## ⚠️ 風險評估

### 低風險項目
- 修復範圍小，僅涉及單一函數
- 有完整的備用機制 `_get_fallback_guidance`
- 修復邏輯清晰，容易理解

### 潛在風險
- AI 服務可能返回其他意外類型（已添加防護）
- 需要確保向後兼容性（保持原有介面）

### 緩解措施
- 添加類型檢查和錯誤處理
- 保留原有備用機制
- 充分測試各種輸入場景

## 📈 驗收標準

### 功能完成標準
- ✅ 所有測試用例通過
- ✅ 無相關錯誤日誌
- ✅ LLM 指導功能正常運作
- ✅ 系統整體穩定性維持

### 代碼品質標準
- ✅ Black 格式化通過
- ✅ Ruff 檢查通過
- ✅ MyPy 類型檢查通過
- ✅ 新增適當的錯誤處理

## 🚀 部署計劃

### 部署步驟
1. 備份當前代碼
2. 應用修復補丁
3. 執行測試套件
4. 重啟服務
5. 驗證核心功能

### 回滾計劃
如果修復失敗，可以：
1. 恢復備份代碼
2. 重啟服務
3. 重新分析問題

## 📝 完成檢查清單

- [ ] T-01: 問題診斷完成 ✅
- [ ] T-02: 代碼修復
- [ ] T-03: 單元測試
- [ ] T-04: 功能驗證
- [ ] T-05: 系統整合測試
- [ ] T-06: 代碼品質檢查
- [ ] T-07: 文檔更新

---

**創建日期**: 2025-06-28  
**預計完成**: 2025-06-28  
**負責開發者**: Claude + 開發團隊  
**審核者**: 技術主管