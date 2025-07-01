# Claude Code 自定義指令創建完整指南

## 📖 概述

本指南基於 2025 年 Claude Code 1.0.38+ 版本，提供完整的自定義 Slash 指令創建流程。經過實際測試驗證，確保每個步驟都能正確執行。

## 🎯 適用範圍

- **Claude Code 版本**: 1.0.38 或更新版本
- **支援格式**: Markdown 檔案 + YAML Front Matter
- **參數傳遞**: `$ARGUMENTS` 語法
- **作用域**: 專案級與全域級指令

---

## 📋 建立流程

### 步驟 1：確認環境

#### 檢查 Claude Code 版本
```bash
claude --version
```
*應顯示 1.0.38 或更高版本*

#### 確認當前專案目錄
```bash
pwd
# 應在您的專案根目錄，例如：/Users/username/project-name
```

### 步驟 2：建立目錄結構

#### 專案級指令（推薦）
```bash
mkdir -p .claude/commands
```

#### 全域指令（可選）
```bash
mkdir -p ~/.claude/commands
```

### 步驟 3：建立指令檔案

#### 檔案命名規則
- **基本指令**: `.claude/commands/command-name.md`
- **分類指令**: `.claude/commands/category/command-name.md`

#### 呼叫語法
- **專案級**: `/project:command-name`
- **分類指令**: `/project:category:command-name`
- **全域指令**: `/command-name`

### 步驟 4：編寫指令內容

#### 基本檔案結構
```markdown
---
description: 指令的簡短描述
allowed-tools: Tool1, Tool2 (可選)
---

# 指令標題

這裡是指令的主要內容，可以使用 $ARGUMENTS 接收參數。

## 使用方式

針對 **$ARGUMENTS**，執行以下操作：

1. 第一步操作
2. 第二步操作
3. 第三步操作

## 指導原則

- 原則一
- 原則二
- 原則三
```

#### 進階功能

##### 1. 工具限制
```yaml
---
description: 指令描述
allowed-tools: Bash(git:*), Read, Edit
---
```

##### 2. 檔案引用
```markdown
# 檢查這個檔案的內容
@src/main.py

# 比較兩個檔案
比較 @src/old-version.js 與 @src/new-version.js
```

##### 3. Shell 命令執行
```markdown
# 當前 Git 狀態
!`git status`

# 最近的提交記錄
!`git log --oneline -5`
```

---

## 🧪 實際範例

### 範例 1：問題根源分析指令

**檔案路徑**: `.claude/commands/find-root-cause.md`

```markdown
---
description: 針對指定問題提醒先使用Serena進行深入研究
---

# Find Root Cause

針對 **$ARGUMENTS**，請使用Serena進行深度研究，找到真正問題的原因才能進行程式碼的修改。

## 🔍 指導原則

1. **深度研究優先**：使用 Serena MCP 工具進行詳細分析
2. **問題根源定位**：找到真正的問題原因，而非表面症狀  
3. **謹慎修改**：確認問題原因後才進行程式碼修改
4. **系統性思考**：考慮修改對整體系統的影響

## 📋 建議步驟

- 使用 Serena 工具檢查相關檔案和程式碼
- 分析問題的根本原因
- 評估可能的解決方案
- 考慮修改的風險和影響
- 實施修改並驗證結果

## ⚡ 立即行動

請開始使用 Serena MCP 工具深入分析「**$ARGUMENTS**」相關的程式碼和配置。
```

**使用方式**: `/project:find-root-cause 檢查程式品質`

### 範例 2：Git 提交指令

**檔案路徑**: `.claude/commands/git/commit.md`

```markdown
---
description: 建立 Git 提交並生成適當的提交訊息
allowed-tools: Bash(git:*)
---

# Git Commit with Context

## 當前狀態
- Git 狀態: !`git status`
- 暫存變更: !`git diff --cached`
- 未暫存變更: !`git diff`

## 任務

基於上述變更，為 **$ARGUMENTS** 建立一個有意義的 Git 提交。

### 提交訊息格式
- 使用簡潔明確的描述
- 說明變更的原因和影響
- 遵循專案的提交訊息慣例

### 執行步驟
1. 檢查所有變更是否已正確暫存
2. 生成適當的提交訊息
3. 執行提交操作
4. 確認提交成功
```

**使用方式**: `/project:git:commit 修復登入驗證問題`

### 範例 3：程式碼審查指令

**檔案路徑**: `.claude/commands/review/security.md`

```markdown
---
description: 對指定檔案進行安全性程式碼審查
allowed-tools: Read, Grep
---

# Security Code Review

## 審查範圍

對 **$ARGUMENTS** 進行全面的安全性程式碼審查。

## 檢查項目

### 1. 常見安全漏洞
- SQL 注入風險
- XSS 攻擊防護
- CSRF 保護機制
- 輸入驗證和清理
- 認證和授權機制

### 2. 敏感資料處理
- 密碼和金鑰的儲存
- 個人資料保護
- 日誌記錄安全
- 錯誤訊息洩露

### 3. 依賴項安全
- 第三方套件版本
- 已知安全漏洞
- 許可證相容性

## 審查流程

1. 讀取並分析指定檔案: @$ARGUMENTS
2. 識別潛在的安全風險
3. 提供具體的修改建議
4. 評估風險等級和優先序
5. 建議相關的測試方案

## 報告格式

- **高風險**: 需要立即修復
- **中風險**: 建議在下次更新時修復  
- **低風險**: 改善建議
- **資訊**: 最佳實踐建議
```

**使用方式**: `/project:review:security src/auth/login.py`

---

## 🚀 測試與驗證

### 步驟 1：啟動 Claude Code
```bash
cd /path/to/your/project
claude
```

### 步驟 2：測試指令
```bash
# 測試基本指令
/project:find-root-cause 測試問題

# 測試分類指令
/project:git:commit 測試提交

# 查看可用指令
/
```

### 步驟 3：驗證輸出
確認：
- ✅ `$ARGUMENTS` 正確替換為輸入的參數
- ✅ YAML Front Matter 被正確解析
- ✅ 格式和結構符合預期
- ✅ 工具限制正常運作

---

## 🔧 故障排除

### 常見問題與解決方案

#### 1. 指令無法識別
**症狀**: 輸入 `/project:command-name` 沒有反應

**可能原因**:
- 檔案路徑錯誤
- YAML Front Matter 格式錯誤
- Claude Code 未在正確目錄啟動

**解決方案**:
```bash
# 檢查檔案是否存在
ls -la .claude/commands/

# 檢查 YAML 語法
head -5 .claude/commands/your-command.md

# 確認在專案根目錄
pwd
```

#### 2. 參數無法傳遞
**症狀**: `$ARGUMENTS` 沒有被替換

**解決方案**:
- 確認使用正確的 `$ARGUMENTS` 語法
- 檢查 YAML Front Matter 是否正確
- 驗證指令調用語法

#### 3. 工具權限錯誤
**症狀**: 指令中的工具無法執行

**解決方案**:
```yaml
---
description: 指令描述
allowed-tools: Bash(git:*), Read, Edit, Grep
---
```

### 除錯技巧

#### 1. 檢查指令清單
```bash
# 在 Claude Code 中輸入
/
```

#### 2. 驗證檔案結構
```bash
find .claude/commands -name "*.md" -type f
```

#### 3. 測試簡單指令
建立最基本的測試指令：
```markdown
---
description: 測試指令
---

# Test Command

這是一個測試指令，參數是：**$ARGUMENTS**
```

---

## 📚 最佳實踐

### 1. 命名慣例
- 使用小寫字母和連字號：`find-root-cause`
- 使用有意義的分類：`git/commit`、`review/security`
- 避免過長的指令名稱

### 2. 文檔結構
- 開頭使用清晰的標題
- 使用表情符號增強可讀性
- 提供具體的執行步驟
- 包含使用範例

### 3. 參數設計
- 明確說明參數的用途
- 提供參數格式範例
- 考慮參數的驗證機制

### 4. 工具使用
- 只授權必要的工具權限
- 使用具體的工具限制：`Bash(git:*)`
- 測試工具權限是否正常

### 5. 維護建議
- 定期檢查指令是否仍然有效
- 根據使用情況調整指令內容
- 建立指令版本管理
- 與團隊成員分享指令庫

---

## 📖 進階功能

### 1. 條件執行
```markdown
# 根據檔案類型執行不同操作
{% if $ARGUMENTS.endswith('.py') %}
這是 Python 檔案，執行 Python 相關操作
{% else %}
這是其他類型檔案，執行通用操作
{% endif %}
```

### 2. 環境變數使用
```markdown
# 檢查環境變數
當前環境：!`echo $NODE_ENV`
專案路徑：!`pwd`
```

### 3. 多步驟工作流
```markdown
---
description: 完整的功能開發工作流
allowed-tools: Bash(git:*), Read, Edit, Grep
---

# Feature Development Workflow

## 步驟 1：準備工作
- 當前分支：!`git branch --show-current`
- 建立功能分支：基於 **$ARGUMENTS**

## 步驟 2：程式碼實作
- 分析相關檔案
- 實作功能邏輯
- 添加必要測試

## 步驟 3：品質檢查
- 執行 linting
- 運行測試套件
- 檢查程式碼覆蓋率

## 步驟 4：提交和合併
- 建立提交
- 推送到遠端
- 建立 Pull Request
```

---

## 🎯 範例指令庫

### 開發相關
- `/project:feature:new` - 建立新功能
- `/project:bug:fix` - 修復問題
- `/project:test:run` - 執行測試
- `/project:deploy:staging` - 部署到測試環境

### 程式碼品質
- `/project:review:code` - 程式碼審查
- `/project:review:security` - 安全性審查
- `/project:refactor:suggest` - 重構建議
- `/project:docs:update` - 更新文檔

### 專案管理
- `/project:status:check` - 檢查專案狀態
- `/project:deps:update` - 更新依賴項
- `/project:config:validate` - 驗證配置
- `/project:backup:create` - 建立備份

---

## 📝 建立檢查清單

### 指令建立前
- [ ] 確認 Claude Code 版本 >= 1.0.38
- [ ] 確定指令的具體用途和範圍
- [ ] 規劃指令的分類和命名
- [ ] 確認所需的工具權限

### 檔案建立中
- [ ] 建立正確的目錄結構
- [ ] 添加完整的 YAML Front Matter
- [ ] 使用正確的 `$ARGUMENTS` 語法
- [ ] 提供清晰的使用說明
- [ ] 包含具體的執行步驟

### 測試驗證後
- [ ] 在正確目錄啟動 Claude Code
- [ ] 測試指令識別和執行
- [ ] 驗證參數傳遞功能
- [ ] 確認工具權限正常
- [ ] 測試邊界情況和錯誤處理

---

## 🎉 結語

本指南提供了 Claude Code 自定義指令的完整建立流程，從基礎設置到進階功能，從實際範例到故障排除。遵循這個指南，您可以建立強大、實用的自定義指令，大幅提升開發效率。

建議將此指南保存為參考文檔，並根據實際使用經驗持續更新和完善。

---

## 📞 支援資源

- **Claude Code 官方文檔**: https://docs.anthropic.com/en/docs/claude-code
- **社群範例庫**: https://github.com/hesreallyhim/awesome-claude-code
- **問題回報**: 透過 Claude Code 的 GitHub Issues

*最後更新：2025-07-01*
*版本：v1.0*
*測試環境：Claude Code 1.0.38, macOS*