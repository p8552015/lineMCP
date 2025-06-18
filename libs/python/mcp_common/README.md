# MCP Common Library

統一的 MCP (Model Context Protocol) 客戶端函式庫，提供現代化、類型安全且可擴展的 MCP 通訊解決方案。

## ✨ 主要功能

- 🔧 **統一介面**: 支援多種 MCP 協定 (HTTP, WebSocket, STDIO)
- 🛡️ **類型安全**: 完整的 Pydantic 資料模型和類型提示
- 🔄 **向後相容**: 無縫替換現有的 MCP 客戶端
- 📊 **可觀測性**: 內建 Prometheus 指標和 OpenTelemetry 追蹤
- ⚡ **高效能**: 連接池、斷路器模式和批次處理
- 🧪 **易於測試**: Mock 客戶端和完整的測試支援

## 🏗️ 架構概覽

```
mcp_common/
├── models/          # 資料模型 (Pydantic)
├── clients/         # 客戶端實現
├── adapters/        # 協定適配器
├── connection/      # 連接管理
├── config/          # 配置系統
├── observability/   # 可觀測性
└── unified_client.py # 統一入口點
```

## 🚀 快速開始

### 安裝

```bash
# 開發模式安裝
cd libs/python/mcp_common
pip install -e .

# 或者從專案根目錄
pip install -e libs/python/mcp_common
```

### 基本使用

```python
from mcp_common import get_mcp_client

# 創建客戶端
client = get_mcp_client(client_type="mock")

# 呼叫工具
response = await client.call_tool(
    server="test_server",
    tool="test_tool",
    params={"key": "value"}
)

print(f"結果: {response.status}")
print(f"資料: {response.data}")

# 關閉客戶端
await client.close()
```

### 向後相容使用

```python
from mcp_common.unified_client import get_unified_mcp_client

# 替換現有的客戶端
client = get_unified_mcp_client(client_type="simple")

# 使用原有的 API
result = await client.call_tool_legacy(
    server_name="sqlite",
    tool_name="query",
    parameters={"sql": "SELECT 1"}
)

print(f"成功: {result['success']}")
```

## 🔧 支援的客戶端類型

| 類型 | 描述 | 使用場景 |
|------|------|----------|
| `mock` | Mock 客戶端 | 測試和開發 |
| `http` | HTTP/HTTPS 協定 | 遠端 MCP 伺服器 |
| `websocket` | WebSocket 協定 | 即時通訊 |
| `stdio` | STDIO 協定 | 本地進程通訊 |
| `simple` | 簡單適配器 | 包裝現有 SimpleMCPClient |
| `legacy` | 遺留適配器 | 包裝現有 MCPClient |

## 📚 進階功能

### 批次呼叫

```python
from mcp_common.models.base import MCPCall

calls = [
    MCPCall(server="db", tool="query", params={"sql": "SELECT 1"}),
    MCPCall(server="api", tool="fetch", params={"url": "https://example.com"}),
]

responses = await client.batch_call(calls)
```

### 串流處理

```python
async for chunk in client.stream_call("server", "tool", params):
    print(f"收到資料: {chunk.data}")
```

### 健康檢查

```python
health = await client.health_check()
print(f"整體狀態: {health.overall}")
print(f"伺服器狀態: {health.servers}")
```

### 配置管理

```python
from mcp_common.config.settings import ServerConfig, MCPClientConfig

# 創建伺服器配置
server_config = ServerConfig(
    name="my_server",
    adapter_type="http",
    url="https://api.example.com",
    timeout=30.0
)

# 創建客戶端配置
client_config = MCPClientConfig(
    environment="production",
    servers={"my_server": server_config}
)
```

## 📊 可觀測性

### Prometheus 指標

- `mcp_requests_total`: 總請求數
- `mcp_request_duration_seconds`: 請求執行時間
- `mcp_connections_active`: 活躍連接數
- `mcp_circuit_breaker_state`: 斷路器狀態

### OpenTelemetry 追蹤

自動為所有 MCP 呼叫產生分散式追蹤資訊。

## 🧪 測試

```bash
# 運行基本測試
cd libs/python/mcp_common
python test_simple_working.py

# 運行整合測試
python test_integration.py
```

## 🔄 遷移指南

### 從 SimpleMCPClient 遷移

```python
# 舊代碼
from src.services.simple_mcp_client import get_simple_mcp_client
client = get_simple_mcp_client()

# 新代碼
from mcp_common.unified_client import get_unified_mcp_client
client = get_unified_mcp_client(client_type="simple")
```

### 從 MCPClient 遷移

```python
# 舊代碼
from src.services.mcp_client import get_mcp_client
client = get_mcp_client()

# 新代碼
from mcp_common.unified_client import get_unified_mcp_client
client = get_unified_mcp_client(client_type="legacy")
```

## 🛠️ 開發

### 項目結構

```
mcp_common/
├── models/
│   ├── base.py          # 基本資料模型
│   ├── error.py         # 錯誤定義
│   └── query.py         # 查詢模型
├── clients/
│   ├── interface.py     # 客戶端介面
│   ├── mock_client.py   # Mock 實現
│   ├── http_client.py   # HTTP 客戶端
│   └── factory.py       # 工廠函數
├── adapters/
│   ├── base.py          # 基礎適配器
│   ├── http.py          # HTTP 適配器
│   ├── websocket.py     # WebSocket 適配器
│   ├── stdio.py         # STDIO 適配器
│   ├── simple_adapter.py # 簡單適配器
│   └── legacy_adapter.py # 遺留適配器
├── connection/
│   ├── pool.py          # 連接池
│   ├── circuit.py       # 斷路器
│   ├── health.py        # 健康檢查
│   └── retry.py         # 重試機制
├── config/
│   ├── settings.py      # 配置模型
│   ├── config_loader.py # 配置載入
│   └── default_config.yaml # 預設配置
├── observability/
│   ├── metrics.py       # Prometheus 指標
│   └── tracing.py       # OpenTelemetry 追蹤
└── unified_client.py    # 統一客戶端
```

### 添加新的適配器

1. 繼承 `BaseProtocolAdapter`
2. 實現必要的方法
3. 在工廠函數中註冊

### 運行測試

```bash
# 安裝開發依賴
pip install -e .[dev]

# 運行測試
pytest tests/

# 運行覆蓋率測試
pytest --cov=mcp_common tests/
```

## 📝 版本歷史

### v0.1.0 (2024-12-30)
- ✅ 初始版本發布
- ✅ 統一客戶端介面
- ✅ 多協定適配器支援
- ✅ 向後相容性
- ✅ 完整的類型安全
- ✅ 可觀測性支援

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📄 授權

MIT License

---

**注意**: 這是 LINE MCP 專案的內部函式庫。使用前請確保已正確設定 Python 環境和依賴項目。 