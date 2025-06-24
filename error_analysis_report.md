# 🔍 GitHub Actions 錯誤分析報告

**生成時間**: 2025-06-24 23:44:36  
**倉庫**: p8552015/lineMCP  
**Run ID**: 15855015342  
**Workflow**: Code Quality Checks  
**分支**: hotfix/ci-dependencies-fix  
**提交**: 7f8845d8  

## 📊 執行摘要

- **總 Jobs**: 6
- **失敗 Jobs**: 5
- **觸發事件**: push
- **執行時間**: 2025-06-24T15:38:29Z

## ❌ 失敗的 Jobs

### 🔴 Docker Quality Checks

- **Job ID**: 44697994971
- **狀態**: completed
- **結論**: failure
- **開始時間**: 2025-06-24T15:38:32Z
- **完成時間**: 2025-06-24T15:38:47Z

⚠️ 無法分析此 job 的日誌: 403 Client Error: Forbidden for url: https://api.github.com/repos/p8552015/lineMCP/actions/jobs/44697994971/logs

### 🔴 Python Code Quality

- **Job ID**: 44697994987
- **狀態**: completed
- **結論**: failure
- **開始時間**: 2025-06-24T15:38:32Z
- **完成時間**: 2025-06-24T15:39:01Z

⚠️ 無法分析此 job 的日誌: 403 Client Error: Forbidden for url: https://api.github.com/repos/p8552015/lineMCP/actions/jobs/44697994987/logs

### 🔴 Python Code Complexity

- **Job ID**: 44697994999
- **狀態**: completed
- **結論**: failure
- **開始時間**: 2025-06-24T15:38:32Z
- **完成時間**: 2025-06-24T15:38:39Z

⚠️ 無法分析此 job 的日誌: 403 Client Error: Forbidden for url: https://api.github.com/repos/p8552015/lineMCP/actions/jobs/44697994999/logs

### 🔴 Documentation Quality

- **Job ID**: 44697995091
- **狀態**: completed
- **結論**: failure
- **開始時間**: 2025-06-24T15:38:32Z
- **完成時間**: 2025-06-24T15:38:34Z

⚠️ 無法分析此 job 的日誌: 403 Client Error: Forbidden for url: https://api.github.com/repos/p8552015/lineMCP/actions/jobs/44697995091/logs

### 🔴 Quality Summary

- **Job ID**: 44698038313
- **狀態**: completed
- **結論**: failure
- **開始時間**: 2025-06-24T15:39:07Z
- **完成時間**: 2025-06-24T15:39:09Z

⚠️ 無法分析此 job 的日誌: 403 Client Error: Forbidden for url: https://api.github.com/repos/p8552015/lineMCP/actions/jobs/44698038313/logs

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
