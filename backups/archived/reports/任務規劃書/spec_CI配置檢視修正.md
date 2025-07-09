# spec_CI配置檢視修正專案

## 🎯 專案目標
使用Serena MCP深度檢視CI配置文件，確保所有測試文件路徑、類別、方法都存在且環境設置一致，並修正發現的問題。

## 📊 任務規劃表

<!-- TASKS START -->
| ID | 任務 | 描述 | 優先級 | 負責 | 狀態 | 開始 | 結束 |
|---|---|---|---|---|---|---|---|
| T-01 | 建立任務規劃書 | 根據template建立spec_CI配置檢視修正.md規劃文件 | High | Serena | DOING | 2025-06-27 15:30 | - |
| T-02 | 驗證單元測試路徑 | 檢查CI中引用的5個單元測試文件是否存在 | High | Serena | TODO | - | - |
| T-03 | 驗證整合測試路徑 | 檢查CI中引用的9個整合測試文件路徑正確性 | High | Serena | TODO | - | - |
| T-04 | 檢查架構層測試 | 驗證6個架構層目錄(application/domain/infrastructure/services/monitoring/models)是否存在 | Medium | Serena | TODO | - | - |
| T-05 | 環境變數一致性檢查 | 確保所有job的環境變數設置一致,包括GOOGLE_API_KEY引用 | Medium | Serena | TODO | - | - |
| T-06 | 測試數據初始化檢查 | 驗證ci-init/01-ci-test-data.sql文件是否存在或需要建立 | High | Serena | TODO | - | - |
| T-07 | 修正整合測試矩陣 | 修正integration-tests的矩陣策略,確保文件路徑正確 | High | Serena | TODO | - | - |
| T-08 | 修正環境變數配置 | 添加缺失的GOOGLE_API_KEY引用到所有需要的job | Medium | Serena | TODO | - | - |
| T-09 | 建立測試數據文件 | 建立ci-init目錄和01-ci-test-data.sql初始化腳本 | Medium | Serena | TODO | - | - |
| T-10 | 執行CI配置驗證 | 運行修正後的CI配置進行完整驗證測試 | High | Serena | TODO | - | - |
| T-11 | 生成驗證報告 | 產出完整的檢視結果和修正報告 | Medium | Serena | TODO | - | - |
<!-- TASKS END -->

## 🔍 問題分析結果

### 已確認存在的文件
- ✅ **單元測試文件** (5個) - 全部存在於 `CICD/tests/unit/`
- ✅ **整合測試文件** (10個) - 全部存在於 `CICD/tests/integration/`
- ✅ **架構層測試目錄** (6個) - 全部存在於 `CICD/tests/`
- ✅ **nodecomman測試** - 存在於 `CICD/tests/nodecomman/`

### 發現的主要問題

#### 1. 整合測試路徑錯誤 ❌
**問題位置**: `.github/workflows/ci-enhanced.yml` 行212
```yaml
# 錯誤的配置
poetry run pytest CICD/tests/integration/test_${{ matrix.test-suite }}.py
```

**矩陣配置問題**:
```yaml
matrix:
  test-suite: [
    'postgres_mcp',        # 實際文件: test_postgres_mcp.py
    'database_integration', # 實際文件: test_database_integration.py
    'mcp_connection',      # 實際文件: test_mcp_connection.py
    # ... 其他文件
  ]
```

**影響**: 9個整合測試文件無法正確執行，CI會失敗

#### 2. 缺失測試數據初始化 ❌
**問題位置**: `.github/workflows/ci-enhanced.yml` 行199-201
```yaml
if [ -f "ci-init/01-ci-test-data.sql" ]; then
  PGPASSWORD=admin psql -h localhost -U admin -d mydb -f ci-init/01-ci-test-data.sql
fi
```

**搜尋結果**: `ci-init/01-ci-test-data.sql` 文件不存在
**影響**: PostgreSQL測試無法正確初始化測試數據

#### 3. 環境變數不完整 ⚠️
**問題**: 部分job缺少`GOOGLE_API_KEY`環境變數引用
**影響**: AI模型相關測試可能失敗
**需要檢查**: 所有job的環境變數設置一致性

## 🛠️ 修正策略

### 階段1: 驗證與分析 (T-02 ~ T-06)
1. **單元測試路徑驗證**: 確認5個單元測試文件路徑正確
2. **整合測試路徑驗證**: 詳細檢查9個整合測試文件名稱匹配
3. **架構層測試檢查**: 驗證6個架構層目錄完整性
4. **環境變數分析**: 檢查所有job環境變數設置
5. **測試數據需求**: 分析是否需要建立初始化腳本

### 階段2: 問題修正 (T-07 ~ T-09)
1. **修正整合測試矩陣**: 調整矩陣值使其與實際文件名匹配
2. **統一環境變數**: 確保所有job都有必要的環境變數
3. **建立測試數據**: 創建ci-init目錄和初始化腳本(如需要)

### 階段3: 驗證與報告 (T-10 ~ T-11)
1. **CI配置驗證**: 執行修正後的CI進行完整測試
2. **生成完整報告**: 產出檢視結果和修正詳情

## 📁 文件存放規範

### 測試報告存放位置
- `/Users/yen/Desktop/lineMCP/CICD/tests/reports/`
- 每個任務產生對應的驗證報告

### 最終報告存放位置
- `/Users/yen/Desktop/lineMCP/task/最終報告/CI配置檢視修正完整報告.md`

## 🧪 驗證標準

### 必要測試
1. **CI語法驗證**: YAML格式正確性
2. **路徑存在性**: 所有引用的測試文件存在
3. **環境變數**: 所有secrets正確引用
4. **PostgreSQL連接**: 測試數據初始化成功

### 通過標準
- ✅ 所有測試文件路徑驗證通過
- ✅ CI配置無語法錯誤
- ✅ 環境變數設置一致
- ✅ 測試數據初始化腳本可執行

## 🔧 品質保證

### SOLID原則遵循
- **S - 單一職責**: 每個job專注特定測試類型
- **O - 開放封閉**: CI配置易於擴展新測試
- **L - 里氏替換**: 測試環境可替換
- **I - 接口隔離**: job間依賴關係清晰
- **D - 依賴倒置**: 使用環境變數抽象化配置

### Serena MCP驗證
- 所有文件存在性透過Serena確認
- 路徑正確性經過實際檢查
- 環境設置經過一致性驗證

## 📝 執行記錄

### T-01 執行詳情
- **開始時間**: 2025-06-27 15:30
- **任務內容**: 建立任務規劃書
- **完成項目**:
  - ✅ 檢查目標目錄結構
  - ✅ 創建規劃文件 spec_CI配置檢視修正.md
  - ✅ 定義完整任務表和執行策略
- **下一步**: 開始執行T-02驗證單元測試路徑

## ⚠️ 風險評估

### 高風險項目
- **整合測試矩陣錯誤**: 可能導致所有整合測試失敗
- **測試數據缺失**: PostgreSQL相關測試無法執行

### 中風險項目  
- **環境變數不一致**: 部分測試可能因缺少API key而失敗

### 低風險項目
- **架構層測試**: 目錄結構基本正確，風險較低

## 🚀 預期成果

執行完成後，CI配置文件將能夠：
- ✅ 正確執行所有208+測試用例
- ✅ 無路徑引用錯誤
- ✅ 環境變數設置統一一致
- ✅ PostgreSQL測試數據正確初始化
- ✅ 所有job並行執行無障礙