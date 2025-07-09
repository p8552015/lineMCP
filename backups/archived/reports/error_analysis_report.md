# 🔍 GitHub Actions 錯誤分析報告

**生成時間**: 2025-06-25 00:43:19  
**倉庫**: p8552015/lineMCP  
**Run ID**: 15855939195  
**Workflow**: Enhanced CI  
**分支**: hotfix/ci-dependencies-fix  
**提交**: 580b23c7  

## 📊 執行摘要

- **總 Jobs**: 5
- **失敗 Jobs**: 2
- **觸發事件**: push
- **執行時間**: 2025-06-24T16:19:56Z

## ❌ 失敗的 Jobs

### 🔴 Python Tests & Coverage

- **Job ID**: 44701155682
- **狀態**: completed
- **結論**: failure
- **開始時間**: 2025-06-24T16:20:00Z
- **完成時間**: 2025-06-24T16:20:39Z

⚠️ 無法分析此 job 的日誌: 403 Client Error: Forbidden for url: https://api.github.com/repos/p8552015/lineMCP/actions/jobs/44701155682/logs

### 🔴 Test Summary

- **Job ID**: 44701205228
- **狀態**: completed
- **結論**: failure
- **開始時間**: 2025-06-24T16:20:41Z
- **完成時間**: 2025-06-24T16:20:44Z

⚠️ 無法分析此 job 的日誌: 403 Client Error: Forbidden for url: https://api.github.com/repos/p8552015/lineMCP/actions/jobs/44701205228/logs

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
