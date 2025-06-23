# 代碼優化重構規格書

## 🎯 目標
根據代碼審計報告分析，系統性清理重複代碼、重構巨石模組、建立代碼健康監控機制，提升系統可維護性與可擴展性。

## 📋 執行範圍
- 清理 `utils/observability.py` 和 `application/monitoring_service.py` 中的重複定義
- 重構 `enhanced_service_factory.py` (512 LOC) 為模組化架構
- 建立未使用代碼生命週期管理機制
- 實施系統功能完整性測試
- 更新相關文檔與啟動腳本

## 📊 成功標準
1. 重複代碼完全移除，無編譯錯誤
2. 模組拆分後保持原有功能完整性
3. 系統測試通過："M001機台稼動率" 查詢正常返回預期結果
4. 代碼覆蓋率維持在85%以上
5. 啟動時間不超過30秒

<!-- TASKS START -->
| ID | 任務 | 描述 | 優先級 | 負責 | 狀態 | 開始 | 結束 |
|:---|:---|:---|:---:|:---:|:---:|:---|:---|
| T-01 | 清理重複get_tracer | 移除utils/observability.py中第二次定義的get_tracer方法 | 高 | Claude | DONE | 2025-06-23 02:47 | 2025-06-23 02:50 |
| T-02 | 清理重複health_checks | 移除application/monitoring_service.py中重複的_perform_health_checks方法 | 高 | Claude | DONE | 2025-06-23 02:50 | 2025-06-23 02:52 |
| T-03 | 代碼清理測試 | 執行start-production.sh驗證重複代碼清理無破壞性 | 高 | Claude | DONE | 2025-06-23 02:52 | 2025-06-23 02:58 |
| T-04 | 設計service_factory重構 | 分析enhanced_service_factory.py拆分為3個專門模組的架構設計 | 中 | Claude | DONE | 2025-06-23 02:58 | 2025-06-23 03:00 |
| T-05 | 創建核心服務註冊模組 | 提取核心服務註冊邏輯到core_services_registry.py | 中 | Claude | DONE | 2025-06-23 03:00 | 2025-06-23 03:03 |
| T-06 | 創建應用服務註冊模組 | 提取應用層服務註冊到application_services_registry.py | 中 | Claude | DONE | 2025-06-23 03:03 | 2025-06-23 03:06 |
| T-07 | 創建基礎設施註冊模組 | 提取基礎設施服務註冊到infrastructure_services_registry.py | 中 | Claude | DONE | 2025-06-23 03:06 | 2025-06-23 03:10 |
| T-08 | 重構service_factory主體 | 修改enhanced_service_factory.py使用新的模組化註冊器 | 中 | Claude | DONE | 2025-06-23 03:10 | 2025-06-23 03:15 |
| T-09 | 重構完整性測試 | 執行完整系統測試確保重構無功能損失 | 高 | Claude | DONE | 2025-06-23 03:15 | 2025-06-23 03:17 |
| T-10 | 建立代碼審查機制 | 創建未使用代碼生命週期管理腳本與流程文檔 | 低 | Claude | DONE | 2025-06-23 03:25 | 2025-06-23 03:27 |
| T-11 | 功能驗證測試 | 執行"M001機台稼動率"查詢驗證系統正常運行 | 高 | Claude | DONE | 2025-06-23 03:17 | 2025-06-23 03:23 |
| T-12 | 更新啟動腳本 | 更新start-production.sh反映代碼變更 | 中 | Claude | DONE | 2025-06-23 03:27 | 2025-06-23 03:30 |
| T-13 | 更新架構文檔 | 更新CLAUDE.md和相關文檔反映新的模組化架構 | 低 | Claude | DONE | 2025-06-23 03:30 | 2025-06-23 03:33 |
| T-14 | 生成總結報告 | 創建完整的重構總結報告 | 低 | Claude | DONE | 2025-06-23 03:23 | 2025-06-23 03:24 |
| T-15 | 緊急修復統計服務錯誤 | 修復 '>=' not supported between instances of 'str' and 'float' 類型錯誤 | 高 | Claude | DOING | 2025-06-23 03:35 | |
<!-- TASKS END -->

## 🧪 測試腳本
```bash
# 功能完整性測試
./start-production.sh

# 特定功能測試 - M001機台稼動率查詢
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"events":[{"type":"message","message":{"text":"M001機台稼動率"}}]}'
```

## 📝 回滾計劃
如遇重大問題，執行以下回滾步驟：
1. `git stash` 暫存當前變更
2. `git checkout code-cleanup-backup` 回到穩定版本
3. 分析問題並制定修復方案
4. 重新執行受影響的任務

## 🔍 風險評估
- **低風險**：重複代碼清理（純移除操作）
- **中風險**：service_factory重構（需要謹慎處理依賴關係）
- **緩解措施**：每個階段都執行完整測試，確保功能無損

## 📚 參考資料
- `/Users/yen/Desktop/lineMCP/code_audit_reports/summary_report_apps_bot_src.md`
- `/Users/yen/Desktop/lineMCP/code_audit_reports/unreferenced_code_analysis.md`
- `/Users/yen/Desktop/lineMCP/CLAUDE.md`