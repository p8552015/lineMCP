---
description: 使用 git 記錄當前版本狀態並生成自動化提交訊息
allowed-tools: Bash(git:*)
---

# 🔄 Git 版本記錄

自動記錄當前專案狀態並建立 Git 提交，針對 **$ARGUMENTS** 生成適當的提交訊息。

## 📊 當前 Git 狀態

### 工作目錄狀態
!`git status --porcelain`

### 分支資訊
- 當前分支: !`git branch --show-current`
- 最近提交: !`git log --oneline -1`

### 變更摘要
- 暫存檔案: !`git diff --cached --name-only`
- 未暫存檔案: !`git diff --name-only`
- 未追蹤檔案: !`git ls-files --others --exclude-standard`

## 🎯 執行任務

根據當前變更狀態，為 **$ARGUMENTS** 建立版本記錄提交。

### 📝 提交訊息格式

遵循 CLAUDE.md 中的慣例：
```
feat/fix/docs/style: 簡潔描述

詳細說明（可選）

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## ⚡ 自動化流程

### 步驟 1: 檢查並暫存變更
```bash
# 如果有未暫存的變更，自動暫存
git add .
```

### 步驟 2: 生成智能提交訊息
根據變更類型自動判斷：
- **程式碼修改** → `feat:` 或 `fix:`
- **文檔更新** → `docs:`
- **格式調整** → `style:`
- **配置變更** → `chore:`

### 步驟 3: 建立提交
```bash
git commit -m "$(cat <<'EOF'
[自動生成的提交訊息基於: $ARGUMENTS]

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### 步驟 4: 確認提交結果
!`git log --oneline -1`

## 🛡️ 安全檢查

### 提交前驗證
- ✅ 檢查是否有敏感資訊（API keys、密碼等）
- ✅ 確認變更範圍合理
- ✅ 驗證提交訊息符合專案規範

### 錯誤處理
- 如果工作目錄乾淨，顯示提示訊息
- 如果有合併衝突，暫停並提供指引
- 如果提交失敗，顯示錯誤原因

## 📋 使用範例

```bash
# 記錄功能開發
/git 完成用戶登入功能

# 記錄錯誤修復  
/git 修復資料庫連接問題

# 記錄文檔更新
/git 更新 API 文檔

# 記錄定期儲存
/git 定期版本記錄
```

## 🎯 立即執行

現在開始處理「**$ARGUMENTS**」的版本記錄，自動分析變更並建立適當的 Git 提交。