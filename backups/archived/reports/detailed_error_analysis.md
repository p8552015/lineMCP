# 🔍 GitHub Actions 錯誤分析報告

**生成時間**: 2025-06-24 23:35:01  
**倉庫**: p8552015/lineMCP  
**Run ID**: 15854778365  
**Workflow**: Code Quality Checks  
**分支**: hotfix/ci-dependencies-fix  
**提交**: 02c82daa  

## 📊 執行摘要

- **總 Jobs**: 6
- **失敗 Jobs**: 5
- **觸發事件**: push
- **執行時間**: 2025-06-24T15:28:22Z

## ❌ 失敗的 Jobs

### 🔴 Python Code Quality

- **Job ID**: 44697190939
- **狀態**: completed
- **結論**: failure
- **開始時間**: 2025-06-24T15:28:25Z
- **完成時間**: 2025-06-24T15:29:01Z

⚠️ 無法分析此 job 的日誌: 403 Client Error: Forbidden for url: https://api.github.com/repos/p8552015/lineMCP/actions/jobs/44697190939/logs

### 🔴 Docker Quality Checks

- **Job ID**: 44697190958
- **狀態**: completed
- **結論**: failure
- **開始時間**: 2025-06-24T15:28:26Z
- **完成時間**: 2025-06-24T15:28:45Z

⚠️ 無法分析此 job 的日誌: 403 Client Error: Forbidden for url: https://api.github.com/repos/p8552015/lineMCP/actions/jobs/44697190958/logs

### 🔴 Python Code Complexity

- **Job ID**: 44697190991
- **狀態**: completed
- **結論**: failure
- **開始時間**: 2025-06-24T15:28:26Z
- **完成時間**: 2025-06-24T15:28:34Z

⚠️ 無法分析此 job 的日誌: 403 Client Error: Forbidden for url: https://api.github.com/repos/p8552015/lineMCP/actions/jobs/44697190991/logs

### 🔴 Documentation Quality

- **Job ID**: 44697191034
- **狀態**: completed
- **結論**: failure
- **開始時間**: 2025-06-24T15:28:26Z
- **完成時間**: 2025-06-24T15:28:28Z

⚠️ 無法分析此 job 的日誌: 403 Client Error: Forbidden for url: https://api.github.com/repos/p8552015/lineMCP/actions/jobs/44697191034/logs

### 🔴 Quality Summary

- **Job ID**: 44697244388
- **狀態**: completed
- **結論**: failure
- **開始時間**: 2025-06-24T15:29:08Z
- **完成時間**: 2025-06-24T15:29:10Z

⚠️ 無法分析此 job 的日誌: 403 Client Error: Forbidden for url: https://api.github.com/repos/p8552015/lineMCP/actions/jobs/44697244388/logs

## 🚀 快速修復

```bash
# 1. 修復 pytest 參數問題
cd apps/bot
# 檢查 pytest.ini 或 pyproject.toml 中的配置
grep -r "timeout" . --include="*.ini" --include="*.toml"

# 2. 更新依賴
poetry update
poetry install

# 3. 本地測試
poetry run pytest -v

# 4. 檢查 CI 配置
cat .github/workflows/ci-enhanced.yml | grep pytest
```

## 📝 備註

- 此報告基於自動分析生成，可能需要人工確認
- 完整日誌已下載到 `./logs` 目錄
- 建議查看原始日誌以獲取更多上下文

---

**生成工具**: GitHub Actions Error Analyzer v1.0
