# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions 發布自動化工作流程
- 語義化版本管理
- 自動 changelog 生成
- Docker 多平台構建支援
- 安全掃描整合

## [0.1.0] - 2025-06-23

### Added
- 🚀 完整 GitHub Actions CI/CD 自動化流程
- 🔒 安全掃描與合規檢查 (Trivy, Bandit, Safety)
- 📊 效能測試工作流程 (Locust)
- 🧪 程式碼品質檢查 (Black, Ruff, MyPy)
- 🐳 Docker 容器化支援
- 📈 測試覆蓋率報告
- 🏗️ 多階段建構最佳化

### Changed
- 🔧 改進現有 CI 流程，加入 MCP 測試
- 📚 更新專案文檔與使用指南
- ⚡ 優化系統效能與穩定性

### Fixed
- 🐛 修復 MCP KeyError 問題
- 🔄 解決循環依賴問題
- 🛡️ 修復安全漏洞與類型安全

### Security
- 🔐 實施零容忍安全政策
- 🕵️ 新增祕密掃描機制
- 📋 整合 SBOM 生成

---

## Release Notes Template

### Version Format
- **Major** (X.0.0): Breaking changes, major feature additions
- **Minor** (0.X.0): New features, backward compatible
- **Patch** (0.0.X): Bug fixes, minor improvements

### Commit Message Convention
- `feat:` 新功能
- `fix:` 錯誤修復
- `docs:` 文檔更新
- `style:` 格式化變更
- `refactor:` 代碼重構
- `perf:` 效能優化
- `test:` 測試相關
- `chore:` 雜項任務

### Changelog Sections
- **Added**: 新功能
- **Changed**: 功能變更
- **Deprecated**: 即將移除的功能
- **Removed**: 已移除的功能
- **Fixed**: 錯誤修復
- **Security**: 安全相關變更

---

*此檔案由 GitHub Actions 自動維護。手動變更可能會被覆蓋。*