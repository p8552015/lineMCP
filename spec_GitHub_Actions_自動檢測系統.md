# 🤖 GitHub Actions CI/CD 自動檢測系統規格文件

## 📋 專案目標

建立智能化的 GitHub Actions 監控和診斷系統，透過 API 自動檢測所有 workflows 狀態，識別失敗原因，並生成針對性的改善建議，確保 CI/CD 管道達到完美綠燈狀態。

## 🎯 核心需求

### 功能性需求
1. **自動狀態檢測**: 查詢所有 GitHub workflows 的最新執行狀態
2. **錯誤深度分析**: 解析失敗 jobs 的詳細錯誤訊息和日誌
3. **智能建議生成**: 基於錯誤模式提供具體的修復建議和腳本
4. **即時報告輸出**: 生成結構化的狀態報告和改善行動計劃
5. **系統整合**: 與現有的 start-production.sh 腳本整合

### 非功能性需求
1. **執行效率**: 完整檢測時間 < 2 分鐘
2. **準確性**: 錯誤識別準確率 > 95%
3. **可靠性**: 支援 API 限流和錯誤重試機制
4. **可維護性**: 模組化設計，易於擴展和維護

## 🔧 技術架構

### 主要組件
- **github-actions-detector.sh**: 主要檢測腳本
- **GitHub Actions API 客戶端**: REST API 呼叫封裝
- **錯誤分析引擎**: 日誌解析和模式識別
- **建議生成器**: 自動修復建議系統
- **報告生成器**: 多格式輸出支援

### API 端點規劃
- `GET /repos/{owner}/{repo}/actions/workflows` - 取得 workflows 列表
- `GET /repos/{owner}/{repo}/actions/runs` - 取得最新 runs 狀態
- `GET /repos/{owner}/{repo}/actions/runs/{run_id}/jobs` - 取得 jobs 詳情
- `GET /repos/{owner}/{repo}/actions/runs/{run_id}/logs` - 下載執行日誌

## 📊 目標 Workflows 清單

本系統將監控以下 6 個關鍵 workflows：
1. **ci-enhanced.yml** - 主要 CI 測試流程
2. **security.yml** - 安全性檢查
3. **quality.yml** - 程式碼品質檢查  
4. **docker-security.yml** - Docker 安全掃描
5. **performance.yml** - 效能測試
6. **release.yml** - 發布流程

## 🧪 測試驗證策略

### 單元測試
- API 呼叫功能測試
- 錯誤解析邏輯測試
- 建議生成準確性測試

### 整合測試
- GitHub API 實際連接測試
- 多 workflow 並行處理測試
- 完整檢測流程驗證

### 生產驗證
- M001 機台稼動率查詢功能測試
- "查看所有機台" 功能驗證
- 系統核心業務邏輯確認

---

<!-- TASKS START -->
| ID | 任務 | 描述 | 優先級 | 負責 | 狀態 | 開始 | 結束 |
|----|------|------|--------|------|------|------|------|
| T-01 | GitHub API 方法驗證 | 透過 Serena MCP 驗證所有 GitHub Actions API 端點和方法的正確性，確認認證方式和回應格式 | HIGH | Claude | DONE | 2025-06-24 16:15 | 2025-06-24 16:25 |
| T-02 | 核心檢測腳本開發 | 開發 github-actions-detector.sh 主腳本，實現 workflows 狀態查詢和基本錯誤檢測功能 | HIGH | Claude | DONE | 2025-06-24 16:25 | 2025-06-24 16:45 |
| T-03 | API 客戶端模組 | 建立 GitHub Actions REST API 呼叫封裝，包含認證、錯誤處理和重試機制 | HIGH | Claude | DONE | 2025-06-24 16:25 | 2025-06-24 16:45 |
| T-04 | 日誌分析系統 | 實現 workflow run logs 擷取和錯誤模式識別演算法，建立失敗原因分類體系 | MED | Claude | DONE | 2025-06-24 16:25 | 2025-06-24 16:45 |
| T-05 | 建議生成引擎 | 開發基於錯誤類型的自動化改善建議系統，包含修復腳本生成功能 | MED | Claude | DONE | 2025-06-24 16:25 | 2025-06-24 16:45 |
| T-06 | 報告輸出系統 | 實現多格式報告生成（JSON/Markdown/終端），包含狀態視覺化和進度追蹤 | MED | Claude | DONE | 2025-06-24 16:25 | 2025-06-24 16:45 |
| T-07 | 系統整合測試 | 建立完整的端到端測試流程，驗證所有模組協作和 API 呼叫正確性 | MED | Claude | DONE | 2025-06-24 16:45 | 2025-06-24 17:20 |
| T-08 | 生產環境驗證 | 執行 M001 機台稼動率查詢和"查看所有機台"功能測試，確認核心業務邏輯正常 | HIGH | Claude | DONE | 2025-06-24 16:45 | 2025-06-24 17:20 |
| T-09 | start-production.sh 整合 | 將檢測腳本整合到現有啟動腳本中，實現自動化 CI/CD 健康檢查 | LOW | Claude | DONE | 2025-06-24 17:20 | 2025-06-24 17:30 |
| T-10 | 文檔和配置更新 | 更新 CLAUDE.md 專案文檔，建立使用指南和故障排除文檔，完善配置管理 | LOW | Claude | DONE | 2025-06-24 17:30 | 2025-06-24 17:40 |
<!-- TASKS END -->

---

## 🚀 執行腳本範例

### 基本使用
```bash
# 檢測所有 workflows 狀態
./github-actions-detector.sh --check-all

# 檢測特定 workflow
./github-actions-detector.sh --workflow ci-enhanced

# 生成詳細報告
./github-actions-detector.sh --report --format markdown
```

### 環境變數配置
```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"
export GITHUB_REPO="yen/lineMCP"
export CI_CHECK_TIMEOUT="120"
```

## 📈 成功指標

### 技術指標
- ✅ 所有 6 個 workflows 達到綠燈狀態
- ✅ 檢測腳本執行時間 < 2 分鐘
- ✅ 錯誤識別準確率 > 95%
- ✅ API 呼叫成功率 > 99%

### 業務指標
- ✅ M001 機台查詢功能正常（預期稼動率 74.4%）
- ✅ "查看所有機台" 功能運作正常
- ✅ 核心業務邏輯 100% 可用
- ✅ 系統整體穩定性提升

## 🔄 零風險遷移策略

### Git 錨點建立
```bash
git tag -a github-detector-baseline -m "GitHub 檢測系統開發前基線"
git push origin github-detector-baseline
```

### 漸進式開發
1. **新建階段**: 建立獨立的功能分支
2. **共存階段**: 與現有系統並行運行
3. **遷移階段**: 逐步整合到主流程
4. **驗證階段**: 完整測試和效能驗證
5. **移除階段**: 清理臨時代碼和配置

### 回滾機制
- 任何階段出現問題可立即回到 baseline 標籤
- 保留原始 start-production.sh 備份
- 建立自動化回滾腳本

---

## 📝 變更記錄

| 版本 | 日期 | 變更內容 | 負責人 |
|------|------|----------|--------|
| 1.0 | 2025-06-24 | 初始規格文件建立 | Claude |

---

**最後更新**: 2025-06-24
**專案狀態**: 開發中
**預計完成**: 2025-06-24 20:00