---
description: 將專案上傳到 GitHub，包含倉庫創建、推送和配置
allowed-tools: Bash(git:*, gh:*), Read
---

# 🚀 GitHub 專案上傳

將當前專案上傳到 GitHub，針對 **$ARGUMENTS** 進行完整的 GitHub 整合設置。

## 📊 當前專案狀態

### Git 倉庫檢查
- 當前分支: !`git branch --show-current`
- 遠端設定: !`git remote -v`
- 最近提交: !`git log --oneline -3`

### 專案資訊
- 專案目錄: !`pwd`
- 專案檔案: !`find . -maxdepth 2 -type f -name "*.md" -o -name "*.json" -o -name "*.py" | head -10`

## 🎯 上傳任務

為 **$ARGUMENTS** 建立 GitHub 倉庫並完成專案上傳。

## ⚡ 自動化上傳流程

### 步驟 1: 環境檢查
```bash
# 檢查 GitHub CLI 是否已安裝
gh --version

# 檢查登入狀態
gh auth status
```

### 步驟 2: 專案準備
```bash
# 確保所有變更已提交
git status

# 如果有未提交的變更，先建立提交
git add .
git commit -m "feat: 準備上傳到 GitHub - $ARGUMENTS

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 步驟 3: GitHub 倉庫創建
```bash
# 創建 GitHub 倉庫（私有）
gh repo create --private --source=. --remote=origin --push

# 或創建公開倉庫
# gh repo create --public --source=. --remote=origin --push
```

### 步驟 4: 推送代碼
```bash
# 設置預設分支並推送
git branch -M main
git push -u origin main
```

### 步驟 5: 設置倉庫描述
```bash
# 根據專案內容設置描述
gh repo edit --description "$ARGUMENTS - LINE MCP 智慧製造監控系統"
```

## 📋 智能倉庫配置

### 自動檢測專案類型
根據專案內容自動配置：

#### Python 專案
- 檢查 `pyproject.toml` 或 `requirements.txt`
- 設置適當的 `.gitignore`
- 配置 GitHub Actions for Python

#### Node.js 專案
- 檢查 `package.json`
- 設置 npm/yarn 相關配置

#### 通用配置
- README.md 檢查和優化建議
- LICENSE 檔案檢查
- .gitignore 完整性驗證

### 🛡️ 安全配置

#### 敏感資訊檢查
```bash
# 檢查可能的敏感檔案
find . -name "*.env*" -o -name "*secret*" -o -name "*key*" | grep -v node_modules
```

#### GitHub Secrets 建議
根據專案需求建議設置的 Secrets：
- `GOOGLE_API_KEY`
- `OPENAI_API_KEY` 
- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_CHANNEL_SECRET`
- `JWT_SECRET_KEY`

### 📚 專案文檔優化

#### README.md 增強
檢查並建議 README.md 內容：
- 專案描述和功能
- 安裝和使用說明
- 貢獻指南
- 授權資訊

#### GitHub 專案設置
```bash
# 設置專案主題標籤
gh repo edit --add-topic "line-bot,mcp,manufacturing,ai,python"

# 設置主頁 URL（如果有）
# gh repo edit --homepage "https://your-project-url.com"
```

## 🔄 進階功能

### GitHub Actions 整合
如果專案包含 `.github/workflows/`：
```bash
# 檢查現有 workflows
ls -la .github/workflows/

# 驗證 workflow 語法
gh workflow list
```

### Issue 和 PR 模板
檢查並建議創建：
- `.github/ISSUE_TEMPLATE/`
- `.github/PULL_REQUEST_TEMPLATE.md`

### 分支保護規則
```bash
# 設置主分支保護（可選）
gh api repos/:owner/:repo/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":[]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1}' \
  --field restrictions=null
```

## ✅ 上傳完成驗證

### 確認檢查清單
- [ ] GitHub 倉庫成功創建
- [ ] 代碼成功推送到 main 分支
- [ ] 遠端分支正確設置
- [ ] 專案描述和標籤設置完成
- [ ] 敏感資訊已正確排除
- [ ] README.md 內容完整

### 最終驗證
```bash
# 檢查遠端倉庫狀態
git remote show origin

# 確認推送成功
git log --oneline origin/main -3

# 查看 GitHub 倉庫資訊
gh repo view
```

## 📱 使用範例

```bash
# 首次上傳專案
/github 全新 LINE MCP 監控系統專案

# 更新現有倉庫
/github 更新專案到最新版本

# 備份專案到 GitHub
/github 程式碼備份和版本控制

# 開源專案發布
/github 開源發布智慧製造監控系統
```

## ⚠️ 注意事項

### 首次使用準備
1. **安裝 GitHub CLI**: `brew install gh` (macOS)
2. **登入 GitHub**: `gh auth login`
3. **確認權限**: 需要 repo 創建和管理權限

### 隱私考量
- 預設創建私有倉庫，避免意外公開敏感資訊
- 自動檢查 `.env` 和敏感檔案
- 建議使用 GitHub Secrets 管理敏感配置

### 錯誤處理
- 如果倉庫已存在，提供覆蓋或重新命名選項
- 網路連接問題的重試機制
- 權限不足時的明確錯誤提示

## 🎯 立即執行

現在開始處理「**$ARGUMENTS**」的 GitHub 上傳，自動檢測專案類型並完成完整的 GitHub 整合設置。