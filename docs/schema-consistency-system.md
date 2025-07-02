# 🔍 Schema 一致性檢查系統

## 📋 系統概述

Schema 一致性檢查系統是為了防止資料庫 Schema 與應用程式期望不一致問題而設計的自動化工具鏈。系統包含檢查、驗證、修復建議和 CI/CD 整合等完整功能。

### 🎯 系統目標

- **防範 Schema 不一致問題** - 在開發階段就發現並阻止 Schema 差異
- **自動化檢查驗證** - 透過 CI/CD 自動執行一致性檢查
- **智能修復建議** - 自動分析差異並生成修復建議和 SQL 腳本
- **開發流程整合** - 無縫整合到現有開發工作流程中

## 🏗️ 系統架構

```
Schema 一致性檢查系統
├── 📋 Schema 規範定義 (schema/expected-schema.json)
├── 🔍 一致性檢查器 (scripts/schema-consistency-checker.py)
├── 🛠️ 自動修復建議 (scripts/schema-auto-fix.py)
├── 📜 便捷執行腳本 (scripts/check-schema.sh)
├── 🔄 CI/CD 工作流程 (.github/workflows/schema-validation.yml)
└── 📖 完整文檔系統 (docs/)
```

## 🛠️ 核心組件

### 1. Schema 規範定義檔案

**位置**: `schema/expected-schema.json`

定義專案期望的資料庫 Schema 規範，包含：
- 表格結構定義
- 欄位類型和約束
- 主鍵和外鍵關係
- 索引配置要求
- 驗證規則設定

```json
{
  "version": "1.0.1",
  "description": "LINE MCP 專案資料庫 Schema 期望規範",
  "baseline_file": "postgres-init/01-init-data.sql",
  "tables": {
    "machine_faults": {
      "primary_key": "fault_id",
      "required_columns": [...],
      "foreign_keys": [...],
      "indexes": [...]
    }
  }
}
```

### 2. Schema 一致性檢查器

**位置**: `scripts/schema-consistency-checker.py`

核心檢查引擎，功能包含：
- 連接實際資料庫取得 Schema
- 與期望規範進行比對分析
- 生成詳細的差異報告
- 提供修復建議和警告

**主要檢查項目**:
- ✅ 必需表格存在性
- ✅ 欄位結構一致性
- ✅ 主鍵配置正確性
- ✅ 外鍵約束完整性
- ✅ 索引配置建議
- ✅ 資料類型相容性

### 3. 自動修復建議系統

**位置**: `scripts/schema-auto-fix.py`

智能分析工具，提供：
- 自動差異分析
- 分類修復建議 (Critical/Warning/Optimization)
- 生成可執行的 SQL 修復腳本
- 對應的回復 (Rollback) 腳本
- 影響程度評估

### 4. 便捷執行腳本

**位置**: `scripts/check-schema.sh`

使用者友善的命令列工具：
- 支援多種執行模式（詳細/安靜/幫助）
- 自動環境檢測和設定
- 彩色輸出和進度顯示
- 錯誤處理和建議提示

### 5. CI/CD 工作流程

**位置**: `.github/workflows/schema-validation.yml`

完整的 CI/CD 整合：
- 觸發條件：推送、PR、手動執行
- PostgreSQL 服務容器自動設置
- Schema 檢查和資料庫整合測試
- Schema 變更檢測和 PR 註解
- 報告產生和歸檔

## 📖 使用指南

### 🚀 快速開始

#### 1. 基本檢查
```bash
# 使用預設設定檢查
./scripts/check-schema.sh

# 使用自訂資料庫 URL
./scripts/check-schema.sh postgresql://user:pass@host:5432/db

# 詳細輸出模式
./scripts/check-schema.sh --verbose

# 安靜模式（適用於腳本）
./scripts/check-schema.sh --quiet
```

#### 2. 自動修復建議
```bash
# 生成修復建議和腳本
python3 scripts/schema-auto-fix.py postgresql://admin:admin@localhost:5432/mydb

# 指定輸出路徑
python3 scripts/schema-auto-fix.py <db_url> <schema_file> <output_path>
```

#### 3. 執行修復腳本
```bash
# 執行生成的修復腳本
psql -h localhost -U admin -d mydb -f migrations/schema_fix_20250702_163000.sql

# 如有問題，執行回復腳本
psql -h localhost -U admin -d mydb -f migrations/schema_fix_20250702_163000_rollback.sql
```

### 🔧 開發工作流程

#### 1. Schema 變更流程
```bash
# 1. 修改資料庫初始化腳本
vim postgres-init/01-init-data.sql

# 2. 更新 Schema 規範（如需要）
vim schema/expected-schema.json

# 3. 本地驗證
./scripts/check-schema.sh --verbose

# 4. 生成修復建議（如有問題）
python3 scripts/schema-auto-fix.py <db_url>

# 5. 執行整合測試
cd apps/bot && poetry run pytest tests/integration/test_database_integration.py -v

# 6. 提交變更
git add . && git commit -m "feat: 更新資料庫 Schema"
```

#### 2. 新專案設置
```bash
# 1. 從現有資料庫生成基準 Schema
python3 scripts/generate-baseline-schema.py <db_url> > schema/expected-schema.json

# 2. 設定 CI/CD 環境變數
# DATABASE_URL, POSTGRES_USER, POSTGRES_PASSWORD 等

# 3. 執行首次檢查
./scripts/check-schema.sh --verbose

# 4. 整合到開發流程
echo './scripts/check-schema.sh --quiet' >> .git/hooks/pre-commit
```

### 📊 CI/CD 整合

#### 1. GitHub Actions 觸發條件
- **Push 觸發**: `postgres-init/**`, `schema/**`, `apps/bot/src/**`
- **PR 觸發**: 對 main/develop 分支的 PR
- **手動觸發**: 支援強制執行完整檢查

#### 2. 自動檢查流程
1. 🏗️ PostgreSQL 服務容器啟動
2. 📥 程式碼檢出和環境設置
3. 🗄️ 資料庫初始化和資料匯入
4. 🔍 Schema 一致性檢查執行
5. 🧪 資料庫整合測試驗證
6. 📋 結果報告和工件上傳

#### 3. Schema 變更檢測
- 自動比較 PR 中的 Schema 變更
- 在 PR 中自動註解變更摘要
- 提供驗證清單和建議指令
- 生成變更差異報告

## ⚙️ 配置說明

### 🔧 Schema 規範配置

#### 1. 表格定義結構
```json
{
  "table_name": {
    "primary_key": "id",
    "required_columns": [
      {
        "name": "column_name",
        "type": "DATA_TYPE",
        "nullable": true/false,
        "default": "DEFAULT_VALUE",
        "constraints": ["PRIMARY KEY", "FOREIGN KEY", ...]
      }
    ],
    "foreign_keys": [
      {
        "column": "ref_column",
        "references_table": "target_table",
        "references_column": "target_column"
      }
    ],
    "indexes": [
      {
        "name": "index_name",
        "columns": ["col1", "col2"]
      }
    ]
  }
}
```

#### 2. 驗證規則設定
```json
{
  "validation_rules": {
    "naming_conventions": {
      "primary_key_suffix": "_id",
      "foreign_key_suffix": "_id",
      "index_prefix": "idx_"
    },
    "data_integrity": {
      "foreign_keys_must_exist": true,
      "primary_keys_required": true
    },
    "performance_requirements": {
      "indexes_on_foreign_keys": true
    }
  }
}
```

### 🎛️ 檢查器配置

#### 1. 環境變數
- `DATABASE_URL`: 資料庫連接字串
- `SCHEMA_FILE_PATH`: Schema 規範檔案路徑
- `CHECK_TIMEOUT`: 檢查超時時間（秒）

#### 2. 檢查級別
- **Critical**: 必須修復的嚴重問題
- **Warning**: 建議修復的警告問題
- **Optimization**: 效能優化建議

#### 3. 類型相容性映射
```python
type_mappings = {
    'SERIAL': ['INTEGER', 'BIGINT'],
    'VARCHAR': ['CHARACTER VARYING', 'TEXT'],
    'DECIMAL': ['NUMERIC'],
    'TIMESTAMP': ['TIMESTAMP WITHOUT TIME ZONE'],
    'BOOLEAN': ['BOOL']
}
```

## 🚨 故障排除

### ❌ 常見問題

#### 1. 連接失敗
```bash
# 檢查資料庫服務狀態
docker ps | grep postgres

# 驗證連接字串
psql postgresql://admin:admin@localhost:5432/mydb -c "SELECT 1;"

# 檢查防火牆和網路設定
telnet localhost 5432
```

#### 2. 權限錯誤
```bash
# 檢查資料庫權限
psql -U admin -d mydb -c "\\dt"

# 確認使用者權限
psql -U admin -d mydb -c "SELECT current_user, session_user;"
```

#### 3. Schema 檔案格式錯誤
```bash
# 驗證 JSON 格式
python3 -m json.tool schema/expected-schema.json

# 檢查檔案編碼
file schema/expected-schema.json
```

#### 4. Python 依賴問題
```bash
# 安裝必要依賴
pip install asyncpg

# 檢查 Python 版本
python3 --version  # 需要 3.8+
```

### 🔧 除錯模式

#### 1. 啟用詳細日誌
```bash
# 設定詳細輸出
export SCHEMA_DEBUG=1
./scripts/check-schema.sh --verbose

# 檢查內部執行
python3 -u scripts/schema-consistency-checker.py <db_url> 2>&1 | tee debug.log
```

#### 2. 手動驗證步驟
```bash
# 1. 測試資料庫連接
psql <database_url> -c "SELECT version();"

# 2. 檢查表格存在
psql <database_url> -c "\\dt"

# 3. 檢查 Schema 檔案
cat schema/expected-schema.json | jq .

# 4. 手動執行檢查器
python3 scripts/schema-consistency-checker.py <database_url>
```

## 📈 效能優化

### ⚡ 檢查效能

#### 1. 快取機制
- Schema 資訊快取 15 分鐘
- 連接池重用
- 批次查詢優化

#### 2. 並行處理
- 表格檢查並行執行
- 索引驗證非同步處理
- 大型資料庫分批檢查

#### 3. 最佳實踐
```bash
# 使用連接池
export DB_POOL_SIZE=5

# 設定合理超時
export CHECK_TIMEOUT=300

# 限制檢查範圍
./scripts/check-schema.sh --tables "machines,machine_faults"
```

### 🎯 CI/CD 優化

#### 1. 快取策略
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: pip-${{ hashFiles('requirements.txt') }}
```

#### 2. 並行執行
```yaml
strategy:
  matrix:
    schema-check: [critical, warning, optimization]
```

#### 3. 條件執行
```yaml
if: contains(github.event.head_commit.message, '[schema]')
```

## 🔮 進階功能

### 🤖 自動化修復

#### 1. 安全修復
- 自動執行低風險修復
- 索引自動創建
- 預設值自動設定

#### 2. 審核機制
- 高風險修復需人工審核
- 修復腳本版本控制
- 回復機制自動測試

#### 3. 批次處理
```bash
# 批次修復多個環境
for env in dev staging prod; do
  ./scripts/schema-auto-fix.py $env_db_url
done
```

### 📊 監控和報告

#### 1. 趨勢分析
- Schema 變更頻率統計
- 問題類型分佈分析
- 修復成功率追蹤

#### 2. 報告整合
- Slack/Teams 通知
- 儀表板視覺化
- 郵件報告定期發送

#### 3. 指標收集
```python
# 自訂指標
schema_check_duration = time.time() - start_time
schema_errors_count = len(validation_result.errors)
schema_warnings_count = len(validation_result.warnings)
```

## 🎯 最佳實踐

### 📋 開發流程

#### 1. Schema 變更管理
- 所有 Schema 變更都需通過檢查
- 重大變更需要遷移腳本
- 向下相容性優先考慮

#### 2. 版本控制策略
- Schema 規範與程式碼同步版本控制
- 使用語義化版本號 (SemVer)
- 變更日誌詳細記錄

#### 3. 測試策略
- 本地開發環境先行測試
- 預發佈環境完整驗證
- 生產環境謹慎部署

### 🛡️ 安全考量

#### 1. 敏感資訊保護
- 資料庫密碼使用環境變數
- 生產資料庫使用唯讀使用者
- 審核日誌完整記錄

#### 2. 訪問控制
- 檢查工具僅需 SELECT 權限
- 修復腳本需要管理員執行
- CI/CD 使用專用服務帳號

#### 3. 備份策略
- 執行修復前自動備份
- 重要變更額外備份確認
- 快速回復機制測試

### 📈 擴展性設計

#### 1. 多資料庫支援
- PostgreSQL, MySQL, SQLite
- 不同版本相容性
- 雲端資料庫服務整合

#### 2. 大型專案適配
- 微服務架構支援
- 多團隊協作工作流程
- 企業級權限管理

#### 3. 整合生態系統
- IDE 插件開發
- Git Hooks 整合
- DevOps 工具鏈串接

---

## 📞 技術支援

### 🆘 獲取幫助

- **文檔**: [完整文檔](docs/)
- **問題回報**: [GitHub Issues](https://github.com/your-org/lineMCP/issues)
- **討論**: [GitHub Discussions](https://github.com/your-org/lineMCP/discussions)

### 🔄 更新和維護

- **定期更新**: 每月檢查新版本
- **安全修補**: 及時更新依賴套件
- **效能優化**: 定期效能分析和優化

---

*🎉 Schema 一致性檢查系統幫助您的專案維持資料庫架構的穩定性和一致性！*