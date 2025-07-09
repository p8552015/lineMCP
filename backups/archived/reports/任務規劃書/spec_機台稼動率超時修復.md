# spec_機台稼動率超時修復.md

## 專案目標
解決自然語言查詢（如「機台稼動率」）因 8 秒硬性逾時而僅回覆「⏳ 正在處理…」卻無最終答案的問題；確保 P95 回應 ≤ 25 秒，且逾時仍能以 PushMessage 補發結果。

<!-- TASKS START -->
| ID | 任務 | 描述 | 優先級 | 負責 | 狀態 | 開始 | 結束 |
|---|---|---|---|---|---|---|---|
| T-01 | 解析耗時量測 | 以 10 筆真實句子量測 `process_message` 各階段耗時；輸出統計報告 | High | Backend | DOING | 2025-06-26 18:15 | - |
| T-02 | 超時策略決策 | 根據 T-01 結果制定 Reply 與 Push 併用或延長 timeout 方案 | High | Arch | TODO | - | - |
| T-03 | Timeout 參數調整 | 將 `asyncio.wait_for` 自 8 s 改為 25 s（暫行）並驗證 | Medium | Backend | TODO | - | - |
| T-04 | 背景推播機制 | 逾時後持續處理並以 PushMessage 回送結果；更新 quick-reply 文案 | High | Backend | TODO | - | - |
| T-05 | NL-to-SQL 效能優化 | 快取 DB schema、關閉 AI 增強 fallback 測試；降低單次解析耗時 | Medium | AI | TODO | - | - |
| T-06 | 例外與退化處理 | 背景任務失敗時推播錯誤說明；新增錯誤日誌 | High | Backend | TODO | - | - |
| T-07 | 測試與驗證 | 新增 pytest 模擬 >8 s 情境；E2E 測試三大核心場景 | High | QA | TODO | - | - |
| T-08 | 文檔與最終報告 | 更新架構圖、撰寫最終報告並提交至 `/task/最終報告` | Medium | Docs | TODO | - | - |
<!-- TASKS END -->

## 關鍵里程碑
1. **M1：T-01 + T-02（48 h）** — 完成耗時統計與策略定案  
2. **M2：T-03 + T-04（72 h）** — 用戶可於逾時後收到最終答案  
3. **M3：T-05 + T-06（+2 d）** — 穩定化效能與錯誤處理  
4. **M4：T-07 + T-08（+1 d）** — 測試通過並提交完整報告

## 驗收標準
- P95 回應時間 ≤ 25 秒
- 逾時背景推播成功率 ≥ 99 %
- 新增 pytest & E2E 測試全部通過
- `start-production.sh` 跑起來後「機台稼動率」查詢必回最終結果
- 任務規劃與最終報告檔案依樣板路徑保存 