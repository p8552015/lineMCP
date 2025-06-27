# 📋 GitHub Actions 使用指南與最佳實踐

## 🎯 概述

本指南提供 LINE MCP 專案的 GitHub Actions 標準化使用方式，確保 CI/CD 流程的安全性、穩定性和可維護性。

## 🏗️ 架構總覽

### 當前 Workflows 清單

| Workflow | 檔案 | 觸發條件 | 主要功能 |
|----------|------|----------|----------|
| **Enhanced CI Pipeline** | `ci-enhanced.yml` | Push/PR | 核心測試與程式碼品質檢查 |
| **Code Quality Checks** | `quality.yml` | Push/PR | 進階程式碼品質與文檔檢查 |
| **Security & Compliance** | `security.yml` | Push/PR | 安全掃描與合規檢查 |
| **Docker Security Scan** | `docker-security.yml` | Push/PR | 容器映像安全掃描 |
| **Performance Testing** | `performance.yml` | Push/PR | 效能基準測試 |
| **Release Automation** | `release.yml` | Tag推送 | 自動化發布流程 |

## 🔧 版本管理策略

### ✅ 推薦的版本固定方式

```yaml
# ✅ 推薦: 使用主版本標籤 (自動獲得安全更新)
uses: actions/checkout@v4
uses: actions/setup-python@v5
uses: DavidAnson/markdownlint-cli2-action@v20

# ✅ 可接受: 特定版本 (最高安全性)
uses: aquasecurity/trivy-action@0.30.0
uses: trufflesecurity/trufflehog@v3.89.2

# ❌ 避免: 分支標籤 (不穩定)
uses: some-action@main
uses: some-action@master
```

### 版本選擇原則

1. **官方 Actions**: 使用主版本標籤 (`@v4`, `@v5`)
2. **第三方 Actions**: 使用具體版本號 (`@v1.2.3`)
3. **安全掃描工具**: 使用最新穩定版本
4. **實驗性工具**: 使用具體 commit SHA

## 🛡️ 安全最佳實踐

### Actions 安全檢查清單

- [ ] 所有 Actions 來源於可信任的發布者
- [ ] 避免使用 `@latest` 或分支標籤
- [ ] 定期檢查 Actions 的安全公告
- [ ] 使用 `permissions` 限制 GITHUB_TOKEN 權限
- [ ] 敏感操作使用 `environment` 保護

### 權限設定範例

```yaml
jobs:
  secure-job:
    runs-on: ubuntu-latest
    permissions:
      contents: read          # 僅讀取倉庫內容
      security-events: write  # 僅寫入安全事件
      actions: read          # 僅讀取 Actions 資訊
    steps:
      # ... 工作步驟
```

## 📦 Dependabot 整合

### 自動化依賴更新

我們的 Dependabot 配置提供：

1. **每週一自動檢查** GitHub Actions 更新
2. **自動合併低風險更新** (patch/minor 版本)
3. **忽略破壞性更新** (major 版本的 actions/*)
4. **安全標籤追蹤** 便於識別安全相關更新

### Dependabot PR 處理流程

```bash
# 1. 檢查 Dependabot PR
gh pr list --label "dependencies,github-actions"

# 2. 審查變更
gh pr diff <PR_NUMBER>

# 3. 檢查安全影響
./scripts/actions-security-check.sh <PR_NUMBER>

# 4. 測試 workflows
gh workflow run ci-enhanced.yml

# 5. 合併 (如果測試通過)
gh pr merge <PR_NUMBER> --squash
```

## 🔍 常用 Actions 參考

### 核心 Actions

```yaml
# 代碼檢出
- uses: actions/checkout@v4
  with:
    fetch-depth: 0  # 完整歷史記錄 (適用於語義版本)

# Python 環境設置
- uses: actions/setup-python@v5
  with:
    python-version: "3.11"

# Poetry 安裝
- uses: snok/install-poetry@v1
  with:
    version: "1.8.3"
    virtualenvs-create: true
    virtualenvs-in-project: true

# 依賴快取
- uses: actions/cache@v4
  with:
    path: apps/bot/.venv
    key: venv-${{ runner.os }}-${{ hashFiles('**/poetry.lock') }}
```

### 安全掃描 Actions

```yaml
# 機密掃描
- uses: trufflesecurity/trufflehog@v3.89.2
  with:
    path: ./
    base: main
    head: HEAD

# 容器安全掃描
- uses: aquasecurity/trivy-action@0.30.0
  with:
    image-ref: ghcr.io/${{ github.repository_owner }}/line-mcp-bot:latest
    format: 'sarif'
    output: 'trivy-results.sarif'

# 文檔品質檢查
- uses: DavidAnson/markdownlint-cli2-action@v20
  with:
    config: .markdownlint.json
    globs: |
      **/*.md
      !node_modules/**/*.md
```

## 🚨 故障排除

### 常見問題與解決方案

#### 1. Action 版本不存在

**錯誤**: `Unable to resolve action some-action@v1.21.0, action not found`

**解決方案**:
```bash
# 檢查可用版本
gh api repos/OWNER/REPO/releases

# 更新到最新穩定版本
# 修改 workflow 文件中的版本號
```

#### 2. 權限不足

**錯誤**: `Resource not accessible by integration`

**解決方案**:
```yaml
# 添加必要權限
permissions:
  contents: write
  security-events: write
```

#### 3. 快取失效

**錯誤**: 依賴安裝時間過長

**解決方案**:
```yaml
# 優化快取鍵
key: venv-${{ runner.os }}-${{ env.PYTHON_VERSION }}-${{ hashFiles('**/poetry.lock') }}
restore-keys: |
  venv-${{ runner.os }}-${{ env.PYTHON_VERSION }}-
  venv-${{ runner.os }}-
```

## 📊 監控與維護

### 定期檢查項目

- [ ] **每月**: 檢查 Actions 安全公告
- [ ] **每季**: 審查 workflow 效能指標
- [ ] **每半年**: 更新 Actions 使用指南

### 效能監控指標

```yaml
# 在 workflow 中添加效能追蹤
- name: 📊 記錄執行時間
  run: echo "Workflow 執行時間: ${{ github.event.workflow_run.run_duration_ms }}ms"
```

## 🎯 開發者快速參考

### 新增 Workflow 檢查清單

- [ ] 使用推薦的 Actions 版本
- [ ] 設置適當的 `permissions`
- [ ] 添加適當的 `timeout-minutes`
- [ ] 包含錯誤處理機制
- [ ] 添加 `continue-on-error` (如適用)
- [ ] 測試 workflow 在不同分支的行為

### 緊急修復流程

```bash
# 1. 快速診斷
./github-actions-detector.sh --workflow <workflow_name>

# 2. 檢查最新執行
gh run list --workflow=<workflow_name> --limit=5

# 3. 查看詳細日誌
gh run view <run_id> --log

# 4. 緊急修復
git checkout -b hotfix/actions-fix
# 進行修復
git commit -m "fix: 緊急修復 GitHub Actions 問題"
git push origin hotfix/actions-fix
```

## 📚 進階主題

### 自定義 Actions

如需開發自定義 Actions，請參考：
- [GitHub Actions 開發指南](https://docs.github.com/en/actions/creating-actions)
- [Action 安全指南](https://docs.github.com/en/actions/security-guides)

### 企業級配置

```yaml
# 企業環境建議配置
env:
  ACTIONS_RUNNER_DEBUG: true  # 開發環境啟用
  ACTIONS_STEP_DEBUG: true    # 開發環境啟用
```

---

**最後更新**: 2025-06-27  
**維護者**: LINE MCP 開發團隊  
**版本**: v1.0

> 💡 **提示**: 這份指南會隨著專案發展持續更新。如有疑問或建議，請提交 Issue 或 PR。