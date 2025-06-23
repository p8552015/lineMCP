### FILE REPORT: apps/bot/src/utils/signature_validator.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：51
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | SignatureValidator | 封裝 LINE Platform 請求的 HMAC-SHA256 簽章驗證邏輯，並提供時間戳驗證以防止重放攻擊。 | — | — | | |
  | | | validate | 執行簽章驗證，是外部呼叫的主要入口。 | | 1 | `middleware.py`
  | | | _calculate_signature | 根據請求內容和頻道密鑰計算預期的簽章。 | | |
  | | | _validate_timestamp | 檢查請求的時間戳是否在可接受的容忍範圍內。 | | |
