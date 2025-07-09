# spec_T02_四層架構測試改善計劃

## 🎯 專案目標

基於 T-02 四層架構單元測試報告（覆蓋率 48.05%，55 個失敗測試），制定系統性改善計劃，解決從 SQLite 到 PostgreSQL 遷移過程中的架構問題，提升測試覆蓋率至 65%+ 並確保系統穩定性。

## 📊 現況分析

### 🔍 問題摘要
- **測試覆蓋率**: 48.05% (目標: 65%+)
- **失敗測試數**: 55 個
- **錯誤數量**: 24 個
- **核心問題**: SQLite → PostgreSQL 遷移不完整

### 🚨 關鍵問題分類
1. **基礎設施問題**: PostgreSQL 連接配置、Docker 服務設定
2. **架構一致性問題**: 依賴注入系統缺陷、API 介面不統一
3. **測試覆蓋問題**: Mock 物件缺失、測試數據管理
4. **品質保證問題**: 程式碼檢查、系統驗證機制

## 📋 任務規劃表

<!-- TASKS START -->
| ID | 任務 | 描述 | 優先級 | 負責 | 狀態 | 開始 | 結束 |
|---|---|---|---|---|---|---|---|
| T-01 | 修復測試環境 PostgreSQL 連接配置 | 解決所有資料庫整合測試失敗問題，確保 Docker PostgreSQL 服務正常啟動 | High | 開發者 | TODO | - | - |
| T-02 | 統一依賴注入系統和服務註冊機制 | 修復 EnhancedServiceFactory 參數不匹配問題，統一服務註冊 API | High | 開發者 | TODO | - | - |
| T-03 | 標準化 API 介面和方法簽名 | 修復 ProductionMCPClient、UnifiedMCPClient 缺失屬性和方法 | High | 開發者 | TODO | - | - |
| T-04 | 適配 PostgreSQL 查詢語句 | 將所有 SQLite 特定語法改為 PostgreSQL 兼容語句 | Medium | 開發者 | TODO | - | - |
| T-05 | 統一配置物件和環境變數管理 | 建立統一的配置管理介面，解決配置不一致問題 | Medium | 開發者 | TODO | - | - |
| T-06 | 修復 mock 物件屬性和測試輔助工具 | 為所有測試添加必要的 mock 屬性和方法 | Medium | 開發者 | TODO | - | - |
| T-07 | 增強單元測試覆蓋率至 65%+ | 針對核心業務邏輯添加完整的單元測試 | Medium | 開發者 | TODO | - | - |
| T-08 | 完善整合測試和端到端測試 | 建立完整的四層架構整合測試和 M001 E2E 測試 | Medium | 開發者 | TODO | - | - |
| T-09 | 建立測試數據管理和清理機制 | 實現測試數據的自動創建、清理和重置機制 | Low | 開發者 | TODO | - | - |
| T-10 | 執行程式碼品質檢查和優化 | 運行 Black、Ruff、MyPy 檢查並修復所有問題 | Low | 開發者 | TODO | - | - |
| T-11 | 系統整體驗證和效能測試 | 執行完整的系統測試，確保所有功能正常運作 | Low | 開發者 | TODO | - | - |
| T-12 | 文檔更新和部署驗證 | 更新 CLAUDE.md、啟動腳本和相關文檔 | Low | 開發者 | TODO | - | - |
<!-- TASKS END -->

## 🏗️ 架構修復策略

### Phase 1: 關鍵基礎設施修復 (T-01 到 T-03)
**目標**: 修復系統核心架構問題，確保基本服務正常運作

#### T-01: PostgreSQL 連接修復
**問題**: 所有資料庫整合測試失敗，錯誤訊息 "Multiple exceptions: [Errno 111] Connect call failed"
**解決方案**:
1. 檢查 Docker PostgreSQL 服務配置
2. 修復測試環境的資料庫連接字串
3. 確保測試數據正確初始化
4. 驗證 psycopg2-binary 依賴安裝

#### T-02: 依賴注入系統統一
**問題**: `MessagingApplicationService.__init__() missing 1 required positional argument: 'command_executor'`
**解決方案**:
1. 統一所有服務的構造函數參數
2. 修復 ServiceRegistry 註冊方法（`factory` → `implementation`）
3. 確保所有服務正確實現依賴注入介面
4. 添加構造函數參數驗證

#### T-03: API 介面標準化
**問題**: `AttributeError: 'ProductionMCPClient' object has no attribute 'server_configs'`
**解決方案**:
1. 為所有 MCP 客戶端添加標準屬性和方法
2. 統一 `call_tool` 方法簽名（支援 timeout 參數）
3. 修復 `get_server_names()` → `list_servers()` 方法名稱
4. 確保向後兼容性

### Phase 2: 架構一致性改善 (T-04 到 T-06)
**目標**: 解決 SQLite 到 PostgreSQL 遷移遺留問題

#### T-04: PostgreSQL 查詢適配
**解決方案**:
1. 將所有 SQLite 特定語法轉換為 PostgreSQL
2. 修復日期時間函數差異
3. 調整索引和約束定義
4. 測試所有查詢語句的正確性

#### T-05: 配置管理統一
**解決方案**:
1. 建立 `ConfigManager` 統一介面
2. 合併分散的配置檔案
3. 統一環境變數命名規範
4. 實現配置熱重載機制

#### T-06: Mock 物件完善
**解決方案**:
1. 為所有 mock 物件添加必要屬性
2. 實現 mock 方法的完整行為
3. 建立測試輔助工具庫
4. 自動生成 mock 物件配置

### Phase 3: 測試覆蓋率提升 (T-07 到 T-09)
**目標**: 將測試覆蓋率從 48.05% 提升至 65%+

#### T-07: 單元測試增強
**重點領域**:
1. Application Layer: ApplicationFacade、指令處理器
2. Domain Layer: 業務邏輯核心功能
3. Infrastructure Layer: 服務工廠、註冊器
4. Services Layer: MCP 客戶端、AI 模型服務

#### T-08: 整合測試完善
**測試類型**:
1. 四層架構整合測試
2. M001 機台 E2E 測試
3. 服務註冊驗證測試
4. PostgreSQL MCP 完整測試

#### T-09: 測試數據管理
**功能**:
1. 測試數據自動生成
2. 測試環境隔離
3. 數據清理和重置
4. 測試報告生成

### Phase 4: 品質保證和驗證 (T-10 到 T-12)
**目標**: 確保系統品質和文檔完整性

#### T-10: 程式碼品質檢查
**檢查項目**:
1. Black 程式碼格式化
2. Ruff 程式碼風格檢查
3. MyPy 類型檢查
4. 安全性掃描

#### T-11: 系統整體驗證
**驗證項目**:
1. 所有 26 個服務正常註冊
2. M001 機台查詢功能正常
3. CI/CD 管道完整通過
4. 效能指標符合要求

#### T-12: 文檔和部署
**更新內容**:
1. CLAUDE.md 系統配置
2. 啟動腳本說明
3. API 文檔
4. 故障排除指南

## 🧪 測試驗證策略

### 核心驗證指標
- **測試覆蓋率**: 65%+ (當前: 48.05%)
- **單元測試通過率**: 95%+ (當前: ~60%)
- **整合測試通過率**: 90%+ (當前: ~40%)
- **E2E 測試通過率**: 85%+ (新增)

### 關鍵功能驗證
1. **M001 機台查詢**: 稼動率查詢功能正常
2. **PostgreSQL MCP**: 完整的資料庫操作功能
3. **服務註冊**: 26+ 服務正確註冊和解析
4. **四層架構**: 各層級間正確的依賴關係

### 自動化測試流程
```bash
# Phase 1: 基礎設施驗證
./start-production.sh test-db       # PostgreSQL 連接測試
poetry run pytest tests/unit/infrastructure/ -v

# Phase 2: 架構一致性驗證
poetry run pytest tests/unit/ -v --cov=src --cov-report=html

# Phase 3: 完整功能驗證
poetry run pytest tests/integration/ -v
poetry run pytest tests/e2e/ -v

# Phase 4: 品質檢查
poetry run black --check src/ tests/
poetry run ruff check src/ tests/
poetry run mypy src/
```

## 📊 成功標準

### 必須達成的目標
- ✅ 所有資料庫連接測試通過
- ✅ 測試覆蓋率達到 65%+
- ✅ 26 個服務正確註冊
- ✅ M001 E2E 測試 100% 通過
- ✅ CI/CD 管道完全通過

### 次要目標
- 🎯 單元測試執行時間 < 5 分鐘
- 🎯 整合測試執行時間 < 10 分鐘
- 🎯 程式碼品質檢查 100% 通過
- 🎯 文檔更新完整性 95%+

### 風險評估和緩解策略

#### 高風險項目
1. **PostgreSQL 遷移複雜度**: 可能需要重寫部分查詢邏輯
   - 緩解: 逐步遷移，保留 SQLite 作為備用
   
2. **依賴注入系統重構**: 可能影響現有服務穩定性
   - 緩解: 建立向後兼容層，分階段重構

#### 中風險項目
1. **測試數據一致性**: 測試環境和生產環境數據差異
   - 緩解: 建立統一的測試數據生成工具
   
2. **CI/CD 管道穩定性**: 新配置可能導致構建失敗
   - 緩解: 並行執行新舊 CI，逐步切換

## 🚀 執行時程表

### Week 1: Phase 1 基礎設施修復
- Day 1-2: T-01 PostgreSQL 連接修復
- Day 3-4: T-02 依賴注入系統統一
- Day 5: T-03 API 介面標準化

### Week 2: Phase 2 架構一致性
- Day 1-2: T-04 PostgreSQL 查詢適配
- Day 3: T-05 配置管理統一
- Day 4-5: T-06 Mock 物件完善

### Week 3: Phase 3 測試覆蓋率提升
- Day 1-3: T-07 單元測試增強
- Day 4-5: T-08 整合測試完善
- Day 5: T-09 測試數據管理

### Week 4: Phase 4 品質保證
- Day 1-2: T-10 程式碼品質檢查
- Day 3-4: T-11 系統整體驗證
- Day 5: T-12 文檔更新和部署驗證

## 🔧 技術資源需求

### 開發工具
- **IDE**: 支援 Python 3.11 和 TypeScript
- **資料庫**: PostgreSQL 15, Docker Compose
- **測試工具**: pytest, pytest-cov, pytest-asyncio
- **品質工具**: Black, Ruff, MyPy

### 環境需求
- **開發環境**: Python 3.11, Poetry 1.8.3, Node.js 22
- **測試環境**: Docker, GitHub Actions
- **監控工具**: CI/CD 狀態監控，測試報告生成

### 文檔資源
- **參考文檔**: CLAUDE.md, 任務規劃 template
- **測試報告**: `/Users/yen/Desktop/lineMCP/CICD/tests/reports`
- **配置檔案**: ci-test-driven.yml, docker-compose.yml

## 📝 品質檢查清單

### 每日檢查項目
- [ ] 執行相關單元測試
- [ ] 檢查程式碼格式和風格
- [ ] 更新任務狀態
- [ ] 記錄遇到的問題和解決方案

### 階段檢查項目
- [ ] Phase 完成後執行完整測試套件
- [ ] 測試覆蓋率檢查
- [ ] 系統整體功能驗證
- [ ] 文檔同步更新

### 最終驗證項目
- [ ] 所有任務狀態為 DONE
- [ ] 測試覆蓋率 ≥ 65%
- [ ] CI/CD 管道 100% 通過
- [ ] M001 E2E 測試完全正常
- [ ] 程式碼品質檢查通過
- [ ] 文檔更新完整

---

**專案建立時間**: 2025-06-26  
**預計完成時間**: 2025-07-24 (4週)  
**專案狀態**: 🔄 **進行中**  
**風險等級**: 🟡 **中等風險**  
**成功機率**: 🎯 **85%**