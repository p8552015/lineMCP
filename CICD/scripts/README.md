# GitHub Actions 狀態檢測腳本使用指南

## 📝 腳本簡介

`github-actions-status-checker.sh` 是一個專為 LINE MCP 專案設計的 GitHub Actions 狀態檢測工具，提供豐富的檢查功能和美觀的輸出格式。

## 🚀 快速開始

### 基本檢查
```bash
# 檢查所有 workflows 和最近執行狀態
./CICD/scripts/github-actions-status-checker.sh

# 顯示簡要摘要
./CICD/scripts/github-actions-status-checker.sh -s

# 生成詳細報告
./CICD/scripts/github-actions-status-checker.sh -r
```

### 特定檢查
```bash
# 檢查特定 workflow (Enhanced CI Pipeline)
./CICD/scripts/github-actions-status-checker.sh -w 170313960

# 檢查特定分支
./CICD/scripts/github-actions-status-checker.sh -b main

# 檢查最近 10 次執行
./CICD/scripts/github-actions-status-checker.sh -n 10
```

### 進階用法
```bash
# 組合使用：檢查特定 workflow 在特定分支的最近 3 次執行
./CICD/scripts/github-actions-status-checker.sh -w 170313960 -b feature/ci-enhanced-config-fix -n 3

# JSON 輸出（適合腳本處理）
./CICD/scripts/github-actions-status-checker.sh --json

# JSON 輸出配合 jq 處理
./CICD/scripts/github-actions-status-checker.sh --json | jq '.workflow_runs[0]'
```

## 📋 完整選項列表

| 選項 | 說明 | 範例 |
|------|------|------|
| `-h, --help` | 顯示幫助訊息 | `./script.sh --help` |
| `-w, --workflow <id>` | 檢查特定workflow ID | `./script.sh -w 170313960` |
| `-b, --branch <name>` | 檢查特定分支 | `./script.sh -b main` |
| `-n, --runs <number>` | 顯示最近N次執行 | `./script.sh -n 10` |
| `-r, --report` | 生成詳細報告 | `./script.sh -r` |
| `-s, --summary` | 僅顯示摘要 | `./script.sh -s` |
| `--json` | 輸出JSON格式 | `./script.sh --json` |

## 🎯 常用 Workflow ID 清單

| Workflow Name | ID | 用途 |
|---------------|----|----- |
| Enhanced CI Pipeline | 170313960 | 主要CI管道 |
| Code Quality Checks | 170313963 | 程式碼品質檢查 |
| Security & Compliance Checks | 170313964 | 安全性檢查 |
| Performance Testing | 170313962 | 效能測試 |
| Docker Security Scan | 170313961 | Docker安全掃描 |
| Release Automation | 169329961 | 發布自動化 |
| Test-Driven CI Pipeline | 170860521 | 測試驅動CI |

## 📊 輸出說明

### 狀態圖示
- ✅ `completed/success` - 執行成功
- ❌ `completed/failure` - 執行失敗
- ⚠️ `completed/cancelled` - 執行取消
- 🕐 `in_progress` - 執行中
- ⚙️ `queued` - 排隊中

### 色彩編碼
- 🟢 **綠色**: 成功狀態
- 🔴 **紅色**: 失敗狀態
- 🟡 **黃色**: 警告/取消狀態
- 🔵 **藍色**: 執行中狀態
- 🟦 **青色**: 排隊狀態

## 🔧 系統需求

### 必需工具
- `curl` - API 請求
- `jq` - JSON 處理
- `git` - Git 資訊獲取
- `bc` - 數學計算（統計功能）

### 安裝依賴
```bash
# macOS
brew install curl jq git bc

# Ubuntu/Debian
sudo apt-get install curl jq git bc

# CentOS/RHEL
sudo yum install curl jq git bc
```

## 📈 實用範例

### 1. 監控CI狀態
```bash
# 持續監控當前分支的CI狀態
while true; do
    clear
    ./CICD/scripts/github-actions-status-checker.sh -s
    sleep 30
done
```

### 2. 檢查特定功能分支
```bash
# 檢查feature分支的CI狀態
./CICD/scripts/github-actions-status-checker.sh -b feature/ci-enhanced-config-fix -n 5
```

### 3. 生成狀態報告
```bash
# 生成完整報告並保存
./CICD/scripts/github-actions-status-checker.sh -r > ci-status-report.txt
```

### 4. 自動化腳本整合
```bash
# 在其他腳本中使用
#!/bin/bash
status=$(./CICD/scripts/github-actions-status-checker.sh --json | jq -r '.workflow_runs[0].conclusion')
if [ "$status" = "success" ]; then
    echo "CI通過，可以部署"
else
    echo "CI失敗，請檢查問題"
fi
```

## 🐛 故障排除

### 常見問題

1. **API 請求失敗**
   ```bash
   # 檢查網路連接
   curl -s https://api.github.com/rate_limit
   ```

2. **jq 命令未找到**
   ```bash
   # 安裝 jq
   brew install jq  # macOS
   sudo apt-get install jq  # Ubuntu
   ```

3. **權限問題**
   ```bash
   # 確保腳本有執行權限
   chmod +x ./CICD/scripts/github-actions-status-checker.sh
   ```

### 除錯模式
```bash
# 啟用詳細輸出
bash -x ./CICD/scripts/github-actions-status-checker.sh
```

## 🔄 更新記錄

### v1.0.0 (2025-06-27)
- 初始版本發布
- 支援多種檢查模式
- 美觀的色彩輸出
- JSON 格式支援
- 統計功能
- 錯誤處理機制

## 📞 支援

如有問題或建議，請：
1. 檢查本文檔的故障排除章節
2. 使用 `--help` 查看最新使用說明
3. 檢查 GitHub repository 的 issues

---

**建立時間**: 2025-06-27  
**適用專案**: LINE MCP (p8552015/lineMCP)  
**維護者**: Claude Code