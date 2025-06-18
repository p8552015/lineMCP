# MCP 客戶端統一介面遷移指南

## 概述

本文檔說明如何從現有的 MCP 客戶端實作遷移到新的統一介面。新介面提供：

- 🔄 **統一 API**: 所有協議使用相同介面
- 🛡️ **企業級可靠性**: 重試、熔斷器、連接池
- 📊 **完整監控**: 內建指標與追蹤
- 🧪 **易於測試**: 模擬客戶端支援
- ⚡ **高效能**: 批次與串流操作

## 快速開始

### 1. 最簡單的遷移（推薦）

只需要替換導入語句：

```python
# 舊版本
from src.services.simple_mcp_client import get_simple_mcp_client
mcp_client = get_simple_mcp_client()

# 新版本（向後相容）
from mcp_common.unified_client import get_simple_mcp_client
mcp_client = get_simple_mcp_client()

# API 呼叫完全相同
result = await mcp_client.call_tool("sqlite", "list_tables", {})
```

### 2. 使用新的統一介面

```python
from mcp_common.unified_client import get_unified_mcp_client

# 創建統一客戶端
client = get_unified_mcp_client(client_type="simple")

# 使用新的統一 API
response = await client.call_tool("sqlite", "list_tables", {})
print(f"狀態: {response['success']}")
print(f"資料: {response['data']}")
```

### 3. 使用工廠方法（最靈活）

```python
from mcp_common import get_mcp_client

# 不同類型的客戶端
simple_client = get_mcp_client(client_type="simple")
mock_client = get_mcp_client(client_type="mock")
http_client = get_mcp_client(client_type="http", servers={"api": "http://localhost:8080"})

# 使用原生 API
response = await simple_client.call_tool("sqlite", "list_tables", {})
print(f"回應狀態: {response.status}")  # MCPStatusCode.SUCCESS
```

## 詳細遷移步驟

### 步驟 1: 檢查現有程式碼

掃描專案中的 MCP 客戶端使用：

```bash
# 查找所有使用點
grep -r "get_mcp_client\|get_simple_mcp_client" src/
grep -r "from.*mcp_client import" src/
```

### 步驟 2: 選擇遷移策略

**策略 A: 漸進式遷移（推薦）**
- 先替換導入，保持原有 API
- 逐步遷移到新 API
- 零風險，完全向後相容

**策略 B: 一次性遷移**
- 直接使用新的統一介面
- 需要修改呼叫代碼
- 立即獲得所有新功能

### 步驟 3: 更新導入語句

```python
# message_handler.py 中的修改
# 舊版本
from src.services.simple_mcp_client import get_simple_mcp_client

# 新版本（向後相容）
from mcp_common.unified_client import get_simple_mcp_client

# 或使用新介面
from mcp_common.unified_client import get_unified_mcp_client
```

### 步驟 4: 配置客戶端

創建 `config/mcp_client.yaml`：

```yaml
mcp_client:
  client_type: simple  # simple, legacy, http, mock
  servers:
    sqlite: http://localhost:3003
    postgres: http://localhost:3002
  default_options:
    timeout: 30.0
    max_retries: 3
    enable_circuit_breaker: true
```

### 步驟 5: 更新程式碼（可選）

如果要使用新功能，可以更新程式碼：

```python
class MessageHandler:
    def __init__(self):
        # 使用新的統一客戶端
        self.mcp_client = get_unified_mcp_client(client_type="simple")
    
    async def _handle_sql_command(self, user_id: str, args: List[str]) -> Message:
        # 使用新的統一 API
        response = await self.mcp_client.call_tool(
            server="sqlite",
            tool="read_query", 
            params={"query": " ".join(args)}
        )
        
        # 新的回應格式
        if response["success"]:
            data = response["data"]
            duration = response.get("duration_ms", 0)
            return TextMessage(text=f"查詢成功，耗時 {duration:.1f}ms\n{data}")
        else:
            return TextMessage(text=f"查詢失敗：{response['error']}")
```

## 新功能使用

### 批次操作

```python
from mcp_common.models.base import MCPCall

# 批次呼叫
calls = [
    MCPCall(server="sqlite", tool="list_tables", params={}),
    MCPCall(server="sqlite", tool="read_query", params={"query": "SELECT 1"}),
]

responses = await client.batch_call(calls)
for response in responses:
    print(f"結果: {response.status}")
```

### 串流操作

```python
# 串流呼叫
async for response in client.stream_call("api", "stream_data", {"limit": 100}):
    print(f"收到資料: {response.data}")
```

### 健康檢查

```python
# 檢查所有伺服器
health = await client.health_check()
print(f"整體狀態: {health.overall}")
print(f"伺服器狀態: {health.servers}")

# 檢查特定伺服器
sqlite_health = await client.health_check("sqlite")
```

### 監控與指標

```python
# 自動收集指標
response = await client.call_tool("sqlite", "query", {"sql": "SELECT 1"})

# 檢查執行時間
print(f"執行時間: {response.duration_ms}ms")

# 檢查元資料
print(f"元資料: {response.metadata}")
```

## 測試支援

### 使用模擬客戶端

```python
from mcp_common import get_mcp_client

# 測試中使用模擬客戶端
mock_client = get_mcp_client(client_type="mock")

# 設定模擬回應
mock_client.set_mock_response("sqlite", "list_tables", ["users", "orders"])

# 測試業務邏輯
result = await some_business_function(mock_client)
assert result["success"] == True
```

### 自訂模擬回應

```python
# 設定成功回應
mock_client.set_mock_response("api", "get_user", {"id": 1, "name": "測試用戶"})

# 設定錯誤回應
mock_client.set_mock_error("api", "invalid_tool", Exception("工具不存在"))

# 設定延遲
mock_client.set_mock_delay("api", "slow_tool", 2.0)  # 2秒延遲
```

## 效能優化

### 連接池配置

```yaml
mcp_client:
  connection_pool:
    min_size: 2
    max_size: 20
    timeout: 30.0
    idle_timeout: 300.0
```

### 重試與熔斷器

```yaml
mcp_client:
  default_options:
    max_retries: 3
    retry_delay: 1.0
    enable_circuit_breaker: true
  circuit_breaker:
    failure_threshold: 5
    success_threshold: 3
    timeout: 60
```

## 故障排除

### 常見問題

**Q: 導入錯誤 "ModuleNotFoundError"**
```bash
# 確保路徑正確
export PYTHONPATH="/path/to/lineMCP/libs/python:$PYTHONPATH"
```

**Q: "YAML 模組未安裝" 警告**
```bash
# 可選，如果需要配置檔案支援
pip install pyyaml
```

**Q: HTTP 客戶端錯誤**
```bash
# 如果需要 HTTP 協議支援
pip install httpx tenacity
```

### 除錯技巧

```python
# 啟用詳細日誌
import logging
logging.basicConfig(level=logging.DEBUG)

# 檢查客戶端狀態
health = await client.health_check()
print(f"詳細資訊: {health.details}")

# 檢查配置
from mcp_common.clients.factory import _factory
print(f"載入的配置: {_factory._config_cache}")
```

## 遷移檢查清單

- [ ] 備份現有程式碼
- [ ] 檢查所有 MCP 客戶端使用點
- [ ] 選擇遷移策略（漸進式 vs 一次性）
- [ ] 更新導入語句
- [ ] 建立配置檔案（可選）
- [ ] 執行測試驗證功能
- [ ] 更新文檔
- [ ] 監控新實作的效能

## 支援

如果遇到問題：

1. 查看 `simple_test.py` 的範例
2. 檢查日誌輸出
3. 使用模擬客戶端進行隔離測試
4. 參考 `test_unified_client.py` 的完整測試

---

**注意**: 新介面完全向後相容，可以安全地漸進式遷移，不會影響現有功能。