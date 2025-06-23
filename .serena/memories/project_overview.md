# LINE MCP 智慧製造監控系統項目概覽

## 🎯 項目宗旨
LINE MCP 是一個企業級工業 4.0 解決方案，透過 LINE 平台提供即時機台監控、AI 驅動的智能分析和預測性維護。

## 🏗️ 技術架構

### 核心技術棧
- **後端**: Python 3.11+ / FastAPI / uvicorn 
- **AI 引擎**: Google Gemini 1.5 Flash + OpenAI GPT-4o-mini
- **通訊協議**: Model Context Protocol (MCP)
- **資料庫**: SQLite (透過 MCP 服務)
- **監控**: Prometheus + OpenTelemetry + 結構化日誌
- **部署**: Docker + docker-compose
- **依賴管理**: Poetry

### 分層架構設計 (SOLID 原則)
1. **應用層 (application/)**: 業務邏輯協調
   - ApplicationFacade: 統一應用入口
   - MessagingService: 訊息處理
   - MonitoringService: 監控服務
   - QueryService: 查詢服務

2. **領域層 (domain/)**: 核心業務規則
   - CommandExecutor: 指令執行器
   - CommandHandler: 指令處理器
   - Exceptions: 領域異常

3. **基礎設施層 (infrastructure/)**: 依賴注入和服務工廠
   - IServiceFactory: 抽象服務工廠介面 (DIP)
   - EnhancedServiceFactory: 具體實現
   - ServiceRegistry: 14個服務註冊管理

4. **服務層 (services/)**: 具體實現
   - 12個核心服務包含AI模型、資料庫、NL-to-SQL等

## 🌟 核心特色
- **企業級架構**: 完全解決循環依賴，實現依賴倒置原則 (DIP)
- **AI 驅動**: 雙引擎架構，成本優化 (Gemini 免費15M tokens/月)
- **零技術債**: 成功移除1416行未使用代碼
- **生產級穩定**: v5修復完成，零錯誤零警告運行
- **完整監控**: 結構化日誌 + Prometheus + OpenTelemetry

## 📊 規模指標
- **程式碼行數**: ~33萬行 (包含依賴)
- **Python 檔案**: 94個
- **文檔檔案**: 711個 Markdown 文檔
- **測試覆蓋**: 完整的單元測試和整合測試套件
- **服務數量**: 14個註冊服務 (12 singleton + 2 transient)

## 🎯 業務價值
- **即時監控**: 機台狀態即時追蹤與預警
- **智能分析**: 自然語言轉SQL，秒級生成洞察
- **預測維護**: AI輔助的故障預測與維護建議
- **成本優化**: 大幅降低運營成本透過免費AI額度