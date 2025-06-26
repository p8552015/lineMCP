# CI 測試計劃執行規格 v2.0

## 🎯 專案目標

建立符合 LINE MCP 最新架構的全面 CI/CD 測試體系，確保系統在四層架構、PostgreSQL MCP、nodecomman 多運行時環境下的穩定性和可靠性。

### 核心目標
1. **測試覆蓋率提升**: 65% → 85% (單元測試) / 75% (整合測試)
2. **CI 執行效率**: 15分鐘 → 10分鐘內完成全部測試
3. **零錯誤部署**: 建立完整的測試把關機制
4. **自動化程度**: 100% 測試流程自動化

## 🏗️ 專案範圍

### 測試架構對應
根據四層架構設計對應的測試策略：

1. **Application Layer (應用層)**
   - ApplicationFacade 統一入口測試
   - MessagingService 訊息處理測試
   - MonitoringService 監控服務測試
   - QueryService 查詢服務測試

2. **Domain Layer (領域層)**
   - CommandExecutor 指令執行器測試
   - 6個 CommandHandler 處理器測試
   - 領域異常處理測試

3. **Infrastructure Layer (基礎設施層)**
   - EnhancedServiceFactory 服務工廠測試
   - ServiceRegistry 26個服務註冊測試
   - 依賴注入機制測試
   - 循環依賴檢測測試

4. **Services Layer (服務層)**
   - PostgreSQL MCP 客戶端測試
   - nodecomman 多運行時測試
   - AI 模型服務測試 (Gemini/OpenAI)
   - NL-to-SQL 服務測試

## 📊 任務執行計劃

<!-- TASKS START -->
| ID | 任務 | 描述 | 優先級 | 負責 | 狀態 | 開始 | 結束 |
|---|---|---|---|---|---|---|---|
| T-01 | PostgreSQL MCP 連接測試套件 | 建立 PostgreSQL Docker 連接測試，驗證 MCP 通訊協議 | High | 開發者 | TODO | - | - |
| T-02 | 四層架構單元測試完善 | 補充應用層、領域層、基礎設施層、服務層的單元測試 | High | 開發者 | TODO | - | - |
| T-03 | 26個服務註冊驗證測試 | 驗證所有服務的註冊、依賴注入和生命週期管理 | High | 開發者 | TODO | - | - |
| T-04 | nodecomman 多運行時測試 | 測試 Node.js 和 Python 運行時的切換和兼容性 | High | 開發者 | TODO | - | - |
| T-05 | M001 機台查詢 E2E 測試 | 端到端測試 M001 稼動率查詢完整流程 | High | 開發者 | TODO | - | - |
| T-06 | AI 模型整合測試強化 | 測試 Gemini 和 OpenAI 的切換、錯誤處理、成本追蹤 | Medium | 開發者 | TODO | - | - |
| T-07 | LINE Webhook 安全測試 | 驗證簽名驗證、請求限流、錯誤處理 | Medium | 開發者 | TODO | - | - |
| T-08 | 效能基準測試建立 | 建立 API 回應時間、資源使用率的基準測試 | Medium | 開發者 | TODO | - | - |
| T-09 | CI Pipeline 並行優化 | 優化測試執行順序，實現並行測試策略 | Low | 開發者 | TODO | - | - |
| T-10 | 測試報告自動化生成 | 建立自動化測試報告生成和發布機制 | Low | 開發者 | TODO | - | - |
<!-- TASKS END -->

## 🧪 測試驗證標準

### T-01: PostgreSQL MCP 連接測試套件
**完成標準**:
- ✅ Docker PostgreSQL 容器成功啟動
- ✅ MCP 客戶端成功連接
- ✅ 基本 CRUD 操作測試通過
- ✅ 連接池管理測試通過
- ✅ 錯誤恢復機制測試通過

**驗證命令**:
```bash
cd apps/bot && python -m pytest tests/integration/test_postgres_mcp.py -v
```

### T-02: 四層架構單元測試完善
**完成標準**:
- ✅ Application Layer 測試覆蓋率 > 90%
- ✅ Domain Layer 測試覆蓋率 > 85%
- ✅ Infrastructure Layer 測試覆蓋率 > 80%
- ✅ Services Layer 測試覆蓋率 > 75%

**驗證命令**:
```bash
cd apps/bot && poetry run pytest tests/unit/ --cov=src --cov-report=term-missing
```

### T-03: 26個服務註冊驗證測試
**完成標準**:
- ✅ 所有 26 個服務成功註冊
- ✅ Singleton 服務單例驗證
- ✅ Transient 服務多例驗證
- ✅ 循環依賴檢測正常
- ✅ 服務解析效能 < 100ms

**驗證命令**:
```bash
cd apps/bot && python -m pytest tests/infrastructure/test_service_registry.py -v
```

### T-04: nodecomman 多運行時測試
**完成標準**:
- ✅ Node.js 運行時檢測正常
- ✅ Python 運行時檢測正常
- ✅ npx 命令執行成功
- ✅ 運行時切換無錯誤
- ✅ 進程生命週期管理正常

**驗證命令**:
```bash
cd apps/bot && python -m pytest tests/nodecomman/ -v
```

### T-05: M001 機台查詢 E2E 測試
**完成標準**:
- ✅ LINE 訊息接收正常
- ✅ NL-to-SQL 轉換正確
- ✅ PostgreSQL 查詢成功
- ✅ 稼動率計算準確 (74.4%)
- ✅ 回應格式符合預期

**驗證命令**:
```bash
./start-production.sh && cd apps/bot && python test_m001_final.py
```

### T-06: AI 模型整合測試強化
**完成標準**:
- ✅ Gemini API 調用成功
- ✅ OpenAI 備用方案啟動
- ✅ Token 使用量追蹤準確
- ✅ 錯誤重試機制正常
- ✅ 成本計算正確

**驗證命令**:
```bash
cd apps/bot && python -m pytest tests/services/test_ai_model_service.py -v
```

### T-07: LINE Webhook 安全測試
**完成標準**:
- ✅ 簽名驗證阻擋偽造請求
- ✅ 請求限流防止 DDoS
- ✅ 錯誤回應不洩露系統資訊
- ✅ 異常處理覆蓋所有場景
- ✅ 日誌記錄完整但安全

**驗證命令**:
```bash
cd apps/bot && python -m pytest tests/integration/test_webhook_security.py -v
```

### T-08: 效能基準測試建立
**完成標準**:
- ✅ API 平均回應時間 < 200ms
- ✅ 並發 100 請求處理正常
- ✅ CPU 使用率 < 50%
- ✅ 記憶體使用 < 1GB
- ✅ 無記憶體洩漏

**驗證命令**:
```bash
cd apps/bot && python -m pytest tests/performance/test_benchmarks.py -v
```

### T-09: CI Pipeline 並行優化
**完成標準**:
- ✅ 測試分組合理
- ✅ 並行執行無衝突
- ✅ 總執行時間 < 10分鐘
- ✅ 快取命中率 > 80%
- ✅ 失敗快速反饋

**驗證檔案**:
```yaml
# .github/workflows/ci-enhanced-v2.yml
```

### T-10: 測試報告自動化生成
**完成標準**:
- ✅ HTML 報告自動生成
- ✅ 覆蓋率圖表可視化
- ✅ 失敗案例詳細分析
- ✅ 趨勢分析圖表
- ✅ 自動發布到 GitHub Pages

**驗證命令**:
```bash
cd apps/bot && ./scripts/generate_test_report.sh
```

## 📁 測試檔案組織

### 新增測試檔案
```
tests/
├── integration/
│   ├── test_postgres_mcp.py      # T-01
│   ├── test_webhook_security.py  # T-07
│   └── test_m001_e2e.py         # T-05
├── unit/
│   ├── application/              # T-02
│   ├── domain/                   # T-02
│   ├── infrastructure/           # T-02
│   └── services/                 # T-02
├── performance/
│   └── test_benchmarks.py        # T-08
└── reports/
    └── templates/                # T-10
```

### CI 配置更新
```yaml
# .github/workflows/ci-enhanced-v2.yml
# 實現 T-09 的並行策略
```

## 🚀 執行計劃

### 第一階段 (第1週)
- 執行 T-01: PostgreSQL MCP 連接測試
- 執行 T-03: 服務註冊驗證測試
- 執行 T-04: nodecomman 測試

### 第二階段 (第2週)
- 執行 T-02: 四層架構單元測試
- 執行 T-05: M001 E2E 測試
- 執行 T-06: AI 模型測試

### 第三階段 (第3週)
- 執行 T-07: Webhook 安全測試
- 執行 T-08: 效能基準測試

### 第四階段 (第4週)
- 執行 T-09: CI Pipeline 優化
- 執行 T-10: 報告自動化

## ⚠️ 風險管理

### 識別的風險
1. **PostgreSQL Docker 環境不一致**
   - 緩解: 使用 docker-compose 標準化環境
   
2. **測試資料污染**
   - 緩解: 每個測試使用獨立的資料庫 schema
   
3. **CI 資源限制**
   - 緩解: 優化測試分組，減少資源消耗

## 🎯 成功標準

### 量化指標
- 測試覆蓋率: 85% (單元) / 75% (整合)
- CI 執行時間: < 10 分鐘
- 測試通過率: > 99%
- 零生產環境事故

### 交付成果
- 完整的測試套件
- 自動化 CI/CD 流程
- 測試報告模板
- 效能基準文檔

## 📚 參考資源

- [專案 CLAUDE.md](../../CLAUDE.md)
- [任務規劃模板](../architecture/任務規劃template.md)
- [四層架構設計文檔](../architecture/four-layer-architecture.md)
- [PostgreSQL MCP 配置](../../docker-compose.postgres.yml)

---

**文檔版本**: 2.0.0  
**創建日期**: 2025-06-26  
**最後更新**: 2025-06-26  
**狀態**: 執行中