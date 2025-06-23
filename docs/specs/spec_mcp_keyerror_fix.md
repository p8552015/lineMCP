# MCP 連接 KeyError 修復規格書

## 目標
修復 LINE Bot 在實際接收訊息時出現的 `'sqlite'` KeyError 問題，確保 MCP 連接穩定可靠。

## 問題分析
1. **錯誤原因**：`self.processes['sqlite']` 拋出 KeyError
2. **根本問題**：連接池狀態與實際進程狀態不同步
3. **影響範圍**：所有 MCP 資料庫查詢功能失效

## 任務規劃表

<!-- TASKS START -->
| ID | 任務 | 描述 | 優先級 | 負責 | 狀態 | 開始 | 結束 |
|---|---|---|---|---|---|---|---|
| T-01 | 建立遷移前錨點 | 使用 git tag 建立 baseline-mcp-fix-20250623 | 高 | Claude | DONE | 2025-06-23 19:31 | 2025-06-23 19:31 |
| T-02 | 修復 call_tool KeyError | 在 production_mcp_client.py 第 294 行前添加進程存在性檢查 | 高 | Claude | DONE | 2025-06-23 19:31 | 2025-06-23 19:32 |
| T-03 | 修復連接池同步邏輯 | 修改 connect_to_server 方法確保狀態一致性 | 高 | Claude | DONE | 2025-06-23 19:32 | 2025-06-23 19:33 |
| T-04 | 添加自動恢復機制 | 當檢測到狀態不一致時自動觸發重連 | 中 | Claude | DONE | 2025-06-23 19:33 | 2025-06-23 19:34 |
| T-05 | 執行單元測試 | 運行 pytest 確保修改沒有破壞現有功能 | 高 | Claude | DONE | 2025-06-23 19:34 | 2025-06-23 19:35 |
| T-06 | 執行生產測試 | 使用 start-production.sh test 測試 MCP 連接 | 高 | Claude | DONE | 2025-06-23 19:35 | 2025-06-23 19:41 |
| T-07 | LINE Bot 實際測試 | 測試查詢 "M001機台稼動率" 和 "查看所有機台" | 高 | Claude | BLOCKED | 2025-06-23 19:41 | | (原因：需要真實 LINE 環境測試)
| T-08 | 更新相關文檔 | 更新 CLAUDE.md 反映代碼變更 | 中 | Claude | DONE | 2025-06-23 19:41 | 2025-06-23 19:42 |
| T-09 | 更新啟動腳本 | 確保 start-production.sh 使用最新修復 | 中 | Claude | DONE | 2025-06-23 19:42 | 2025-06-23 19:42 |
| T-10 | 提交代碼變更 | 創建 commit 並標記版本 | 低 | Claude | TODO | | |
<!-- TASKS END -->

## 具體修改方案

### 1. 修復 call_tool 方法 (T-02)
```python
# 在第 294 行前添加：
if server_name not in self.processes:
    logger.warning(f"⚠️ 進程不存在於字典中：{server_name}，強制重新連接")
    self.connections[server_name] = False
    # 清理連接池狀態
    connection_info = await self.connection_pool.get_connection(server_name)
    if connection_info:
        connection_info.status = ConnectionStatus.DISCONNECTED
    if attempt < max_retries:
        continue
    return {"success": False, "error": f"進程未找到：{server_name}"}
```

### 2. 修復 connect_to_server 方法 (T-03)
```python
# 修改第 86-90 行：
if connection_info.process:
    self.processes[server_name] = connection_info.process
    self.connections[server_name] = True
    logger.info(f"🔄 重用連接池連接：{server_name}")
    return True
else:
    # 連接池狀態不一致，標記為斷開並繼續建立新連接
    logger.warning(f"⚠️ 連接池返回 CONNECTED 但無進程，重建連接：{server_name}")
    connection_info.status = ConnectionStatus.DISCONNECTED
    # 繼續執行下面的連接邏輯
```

### 3. 添加健康檢查 (T-04)
```python
async def _verify_process_health(self, server_name: str) -> bool:
    """驗證進程健康狀態"""
    if server_name not in self.processes:
        return False
    
    process = self.processes[server_name]
    if process.returncode is not None:
        # 進程已退出
        del self.processes[server_name]
        self.connections[server_name] = False
        return False
    
    return True
```

## 測試計劃
1. 單元測試：確保修改不影響現有功能
2. 集成測試：測試 MCP 連接和重連機制
3. 端到端測試：通過 LINE Bot 發送實際查詢

## 風險評估
- **低風險**：只添加防護性檢查，不改變核心邏輯
- **回滾方案**：使用 git checkout baseline-mcp-fix-20250623

## 預期結果
- 消除 KeyError 錯誤
- MCP 連接自動恢復
- LINE Bot 查詢功能正常運作