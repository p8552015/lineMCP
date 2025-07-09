# 資料庫Schema一致性修復專案

## 🎯 專案目標

解決生產環境與開發環境資料庫Schema不一致問題，確保LINE Bot查詢功能在生產環境正常運作，並建立完善的資料庫遷移和測試機制，防止類似問題再次發生。

## 📋 問題背景

**核心問題**：`start-production.sh` 腳本測試通過，但實際LINE查詢失敗，錯誤訊息為 `relation "machine_faults" does not exist`。

**根本原因**：
1. 測試腳本只驗證應用程式邏輯，未真正測試與生產資料庫的互動
2. 生產資料庫缺少應用程式期望的資料表結構
3. 缺乏資料庫遷移管理機制
4. 缺乏真正的端到端整合測試

## 🎯 解決方案概述

**階段一**：緊急修復 - 立即解決生產環境問題
**階段二**：根本治理 - 建立資料庫遷移機制  
**階段三**：防護加強 - 完善測試和監控體系

## 📊 任務執行計畫

<!-- TASKS START -->
| ID | 任務 | 描述 | 優先級 | 負責 | 狀態 | 開始 | 結束 |
|---|---|---|---|---|---|---|---|
| T-01 | 資料庫Schema調查 | 檢查生產環境資料庫實際結構，對比應用程式期望結構 | Critical | Serena | DONE | 2025-06-26 10:35 | 2025-06-26 10:45 |
| T-02 | 緊急Schema修復 | 在生產資料庫中建立缺失的資料表和結構 | Critical | Serena | DONE | 2025-06-26 10:45 | 2025-06-26 11:15 |
| T-03 | 生產環境驗證 | 驗證修復後LINE Bot查詢功能正常 | Critical | Serena | DOING | 2025-06-26 11:15 | - |
| T-04 | 資料庫遷移工具導入 | 安裝並配置Alembic資料庫遷移工具 | High | Serena | TODO | - | - |
| T-05 | 初始遷移腳本建立 | 將現有資料庫結構轉換為遷移腳本 | High | Serena | TODO | - | - |
| T-06 | 應用啟動健康檢查 | 在FastAPI啟動時增加資料庫Schema驗證 | High | Serena | TODO | - | - |
| T-07 | 真實整合測試建立 | 建立包含資料庫互動的端到端測試 | High | Serena | TODO | - | - |
| T-08 | 部署流程優化 | 更新部署腳本，包含資料庫遷移步驟 | Medium | Serena | TODO | - | - |
| T-09 | 監控告警機制 | 建立資料庫查詢失敗的告警機制 | Medium | Serena | TODO | - | - |
| T-10 | 文檔更新 | 更新相關文檔，包含新的部署和測試流程 | Low | Serena | TODO | - | - |
<!-- TASKS END -->

## 🔧 技術實施詳細規劃

### 階段一：緊急修復（T-01 ~ T-03）

#### T-01: 資料庫Schema調查
**目標**：釐清生產環境資料庫的實際狀況
**執行步驟**：
1. 連接生產PostgreSQL資料庫
2. 執行 `\dt` 查看現有資料表
3. 分析應用程式程式碼，找出所有期望的資料表
4. 對比差異，建立缺失資料表清單
5. 檢查現有資料表結構是否符合應用程式期望

**預期產出**：
- 生產環境資料庫現狀報告
- 缺失資料表和欄位清單
- Schema差異分析文件

#### T-02: 緊急Schema修復
**目標**：在生產資料庫中建立必要的資料表結構
**執行步驟**：
1. 根據應用程式程式碼分析，建立完整的CREATE TABLE語句
2. 在測試環境先驗證SQL語句正確性
3. 備份生產資料庫（如有重要資料）
4. 在生產環境執行資料表建立語句
5. 插入必要的測試資料（如需要）

**關鍵資料表**（基於錯誤日誌分析）：
```sql
-- 機器故障資料表
CREATE TABLE machine_faults (
    id SERIAL PRIMARY KEY,
    machine_id VARCHAR(50) NOT NULL,
    fault_type VARCHAR(100),
    severity VARCHAR(20),
    fault_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- 其他可能需要的資料表...
```

#### T-03: 生產環境驗證
**目標**：確認修復後系統正常運作
**驗證項目**：
1. 執行 `start-production.sh` 確認無迴歸
2. 透過LINE Bot發送測試查詢
3. 檢查日誌確認無錯誤
4. 驗證所有核心功能正常

### 階段二：根本治理（T-04 ~ T-06）

#### T-04: 資料庫遷移工具導入
**目標**：建立標準化的資料庫變更管理流程
**執行步驟**：
1. 安裝Alembic：`pip install alembic`
2. 初始化Alembic：`alembic init alembic`
3. 配置 `alembic.ini` 連接資料庫
4. 建立資料庫模型（使用SQLAlchemy）
5. 測試遷移工具基本功能

#### T-05: 初始遷移腳本建立
**目標**：將現有資料庫結構納入版本控制
**執行步驟**：
1. 建立SQLAlchemy模型對應所有資料表
2. 生成初始遷移腳本：`alembic revision --autogenerate -m "Initial migration"`
3. 檢查並調整生成的遷移腳本
4. 在測試環境驗證遷移腳本
5. 標記生產環境為當前版本：`alembic stamp head`

#### T-06: 應用啟動健康檢查
**目標**：防止應用程式在Schema不匹配時啟動
**實施方案**：
```python
# 在 main.py 的 startup 事件中添加
@app.on_event("startup")
async def startup_event():
    await verify_database_schema()

async def verify_database_schema():
    """驗證資料庫Schema是否符合應用程式期望"""
    required_tables = ["machine_faults", "machines", "departments"]
    for table in required_tables:
        try:
            await database.execute(f"SELECT 1 FROM {table} LIMIT 1")
        except Exception as e:
            logger.fatal(f"Required table '{table}' not found: {e}")
            raise SystemExit(1)
```

### 階段三：防護加強（T-07 ~ T-10）

#### T-07: 真實整合測試建立
**目標**：建立包含資料庫互動的完整測試套件
**測試範疇**：
1. 資料庫連接測試
2. 自然語言到SQL轉換測試
3. SQL執行和結果解析測試
4. 端到端LINE Bot互動測試

## 🧪 測試驗證標準

### 緊急修復驗證（階段一完成後）
- ✅ 生產環境LINE Bot查詢無 `relation does not exist` 錯誤
- ✅ 核心查詢功能正常：M001機台查詢、故障記錄查詢等
- ✅ `start-production.sh` 持續通過
- ✅ 系統日誌無Critical錯誤

### 完整解決方案驗證（所有階段完成後）
- ✅ 資料庫遷移流程正常運作
- ✅ 應用程式啟動時自動驗證Schema
- ✅ 整合測試套件全部通過
- ✅ 部署流程包含資料庫遷移步驟
- ✅ 監控告警機制正常運作

## 🚨 風險評估與應對

### 高風險項目
1. **生產資料庫直接修改**
   - 風險：可能影響現有資料或服務
   - 應對：充分備份、分階段執行、準備回滾方案

2. **Schema變更可能影響其他系統**
   - 風險：如果有其他應用程式使用同一資料庫
   - 應對：事前調查依賴關係、與相關團隊溝通

### 中風險項目
1. **遷移工具導入可能與現有架構衝突**
   - 應對：在測試環境充分驗證、漸進式導入

## 📋 成功標準

### 立即目標（48小時內）
- ✅ 生產環境LINE Bot查詢功能恢復正常
- ✅ 無Critical級別錯誤日誌

### 短期目標（1週內）
- ✅ 資料庫遷移機制建立完成
- ✅ 應用程式啟動健康檢查實施
- ✅ 整合測試套件建立

### 長期目標（2週內）
- ✅ 完整的資料庫變更管理流程
- ✅ 自動化部署包含資料庫遷移
- ✅ 監控告警機制完善

## 📁 相關檔案與資源

### 需要修改的檔案
- `apps/bot/src/main.py` - 添加啟動健康檢查
- `start-production.sh` - 添加資料庫遷移步驟
- `requirements.txt` - 添加Alembic依賴
- 新增：`alembic/` 目錄及相關遷移檔案

### 需要建立的檔案
- `alembic.ini` - Alembic配置檔案
- `alembic/env.py` - 遷移環境配置
- `apps/bot/src/models/database.py` - SQLAlchemy模型定義
- `tests/integration/` - 整合測試目錄

## 🔄 執行時程安排

**第1天**：T-01, T-02, T-03（緊急修復）
**第2-3天**：T-04, T-05（遷移工具導入）
**第4-5天**：T-06, T-07（健康檢查與測試）
**第6-7天**：T-08, T-09, T-10（優化與文檔）

## 📞 緊急聯絡與回滾計畫

### 緊急情況處理
如果修復過程中出現問題：
1. 立即停止當前操作
2. 檢查系統日誌和錯誤訊息
3. 如有資料庫備份，準備回滾
4. 將任務狀態設為 `BLOCKED` 並記錄詳細原因

### 回滾方案
1. **資料庫層面**：使用事前建立的備份
2. **應用程式層面**：回滾到上一個穩定版本
3. **監控確認**：確保回滾後系統恢復正常

---

## 📝 執行日誌

*此區域將記錄任務執行過程中的重要決策和發現*

**專案啟動時間**：2025-06-26 10:30
**預計完成時間**：2025-07-03 18:00
**實際完成時間**：待填入

---

## ✅ 專案完成檢查清單

- [ ] 所有任務狀態為 `DONE`
- [ ] 生產環境LINE Bot功能正常
- [ ] 資料庫遷移機制建立完成
- [ ] 整合測試套件通過
- [ ] 部署流程優化完成
- [ ] 監控告警機制運作正常
- [ ] 相關文檔更新完成
- [ ] 團隊知識轉移完成