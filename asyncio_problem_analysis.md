# MCP stdio_client Asyncio Cancel Scope 問題深度分析

## 問題摘要

MCP Python SDK 的 `stdio_client` 在關閉時出現 `RuntimeError: Attempted to exit cancel scope in a different task than it was entered in` 錯誤。

## 根本原因分析

### 1. 問題核心

**AnyIO TaskGroup 的任務上下文限制**：
- AnyIO 的 `create_task_group()` 創建的 TaskGroup 和 CancelScope 必須在**同一個 asyncio.Task 中**進入和退出
- 這是 AnyIO 設計的核心安全機制，防止任務取消的競態條件

### 2. MCP SDK 的問題實作

從原始碼分析，`stdio_client` 函數的問題在於：

```python
async with (
    anyio.create_task_group() as tg,  # ← 在任務 A 中創建 TaskGroup
    process,
):
    tg.start_soon(stdout_reader)
    tg.start_soon(stdin_writer)
    try:
        yield read_stream, write_stream  # ← 控制權交給外部
    finally:
        # ← 清理邏輯可能在任務 B 中執行
```

**關鍵問題**：
1. `yield` 暫停生成器，將控制權交給調用者
2. 調用者可能在**不同的 asyncio.Task** 中調用 `__aexit__()`
3. 當 `__aexit__()` 在不同任務中被調用時，AnyIO 檢測到 TaskGroup 的退出上下文與創建上下文不匹配
4. 導致 `RuntimeError: Attempted to exit cancel scope in a different task`

### 3. 任務上下文分析

#### 正常情況（同任務）：
```
Task-1: 
  ├── 創建 stdio_client 上下文
  ├── 進入 TaskGroup (anyio.create_task_group())
  ├── yield streams
  └── 退出 TaskGroup ✅ (同一任務)
```

#### 問題情況（不同任務）：
```
Task-1: 
  ├── 創建 stdio_client 上下文
  ├── 進入 TaskGroup
  └── yield streams

Task-2:
  └── 退出 TaskGroup ❌ (不同任務，導致錯誤)
```

### 4. 我們系統中的具體場景

在我們的 MCP 會話池中：
1. **任務 A**：`_process_request_queue()` 創建 stdio_client 上下文
2. **任務 B**：`_do_close_session_in_owner_task()` 嘗試關閉會話
3. 雖然我們試圖在"擁有者任務"中關閉，但 AnyIO 的 TaskGroup 仍然檢測到任務不匹配

## 為什麼現有解決方案無效

### 1. 錯誤抑制方案的問題
- 僅隱藏症狀，不解決根本問題
- 可能導致資源洩漏
- 違反了 fail-fast 原則

### 2. 任務隊列方案的問題
- AnyIO 的檢查是在底層實現的，即使在"擁有者任務"中也無法繞過
- AsyncExitStack 本身也受到相同限制

## 根本解決方案

### 方案 1：同步退出模式（推薦）

確保 stdio_client 的生命週期完全在同一個任務中：

```python
async def create_managed_session():
    # 在單一任務中管理整個生命週期
    async with stdio_client(params) as (read, write):
        session = ClientSession(read, write)
        await session.initialize()
        
        # 使用會話...
        result = await session.call_tool(...)
        
        # 自動在同一任務中清理
    return result
```

### 方案 2：修復 MCP SDK（長期）

向 MCP Python SDK 提交 Pull Request，修改 stdio_client 實作：
- 使用 `asyncio.TaskGroup` 而非 `anyio.create_task_group()`
- 或者重新設計避免跨任務的上下文管理

### 方案 3：自定義 stdio_client 實作

實作不依賴 AnyIO TaskGroup 的版本：

```python
@asynccontextmanager
async def safe_stdio_client(server_params):
    # 使用 asyncio.TaskGroup (Python 3.11+) 或手動管理任務
    async with asyncio.TaskGroup() as tg:
        # 實作邏輯...
        yield streams
```

## 當前狀況評估

### 功能影響
- ✅ **核心功能正常**：查詢、工具調用都成功
- ✅ **性能無影響**：錯誤僅在關閉時發生
- ❌ **日誌污染**：每次關閉都產生錯誤日誌
- ❌ **潛在資源洩漏**：不完整的清理可能導致資源未釋放

### 風險等級
- **功能風險**：低（不影響主要功能）
- **維護風險**：中（錯誤日誌造成困擾）
- **安全風險**：低（無安全隱患）

## 建議行動

### 短期（立即實施）
1. 實作方案 1：修改會話管理，確保同任務生命週期
2. 添加適當的日誌級別控制，降低錯誤日誌的干擾

### 中期（1-2 週）
1. 向 MCP Python SDK 報告此問題
2. 評估自定義 stdio_client 實作的可行性

### 長期（1-2 月）
1. 跟進 MCP SDK 的修復進度
2. 如有必要，實作自定義解決方案

## 結論

這是 MCP Python SDK 的已知架構問題，而非我們實作的錯誤。雖然不影響功能，但需要適當處理以避免日誌污染和潛在的資源洩漏。推薦採用方案 1 作為根本解決方案。