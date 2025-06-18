# 📌 MCP Client 設計與最佳實務建議

> **請先啟動虛擬環境再進行任何測試**
> ```bash
> cd apps/bot
> poetry shell     # 或 source $(poetry env info --path)/bin/activate
> pytest -q        # 執行測試前務必在 venv 內
> ```

---

## 1. 現況診斷

| 問題 | 描述 | 風險 |
|------|------|------|
| 重複實作 | `mcp_client.py` 與 `simple_mcp_client.py` 兩套邏輯，介面與行為不一致 | ✗ 減低維護性，易產生 Bug |
| 同步 / 非同步混用 | 有的 API 使用 `requests`，有的使用 `httpx.AsyncClient` | ✗ 阻塞 I/O、效能受限 |
| 錯誤處理薄弱 | 缺少 Retry、Circuit-Breaker，Exception 隨意拋出 | ✗ 線上不穩定；使用者體驗差 |
| 型別不明確 | 回傳值直接 `dict`，未使用 Pydantic | ✗ 缺乏型別保障，難以 IDE 自動補全 |
| 可觀測性不足 | 無結構化日誌、缺少 Prometheus metrics | ✗ 難以快速定位問題 |


## 2. 設計目標

1. **單一介面，對外一致**：所有呼叫端只依賴 `MCPClientInterface`，杜絕重複實作。
2. **全非同步**：使用 `httpx.AsyncClient` + 連線池，提高 Throughput。
3. **可靠性**：內建 Retry（Exponential Backoff）、Circuit Breaker、Timeout。
4. **可觀測性**：結構化日誌、Prometheus 指標（成功率、延遲、錯誤率）。
5. **型別安全**：Pydantic Model 作為參數與回傳值，提升可讀性與 IDE 支援。
6. **可測試性**：介面層易於 Mock；提供 `MockMCPClient`。
7. **可組態**：統一由 `settings.py` (Pydantic BaseSettings) 注入端點、超時、重試次數。


## 3. 架構設計

```text
libs/
└── python/
    └── mcp_common/
        ├── clients/
        │   ├── interface.py        # MCPClientInterface
        │   ├── http_client.py      # MCPHttpClient (default impl.)
        │   ├── mock_client.py      # MockMCPClient (測試用)
        │   └── factory.py          # MCPClientFactory
        ├── models/
        │   ├── base.py             # 共同欄位
        │   ├── query.py            # Query / Result schema
        │   └── error.py            # Error schema
        └── observability/
            ├── metrics.py          # Prometheus Counter / Histogram
            └── logging.py          # structlog wrapper
```

### 3.1 MCPClientInterface
```python
class MCPClientInterface(Protocol):
    async def query(self, sql: str, *, database: str | None = None) -> QueryResult: ...
    async def table_list(self) -> list[str]: ...
    async def status(self) -> HealthStatus: ...
```

### 3.2 MCPHttpClient
* **Dependency**: `httpx.AsyncClient`
* **功能**:
  * 保持連線池 (`limits=...)`。
  * `retry` 使用 `tenacity`，設定 `wait_exponential`、`stop_after_attempt`。
  * Circuit Breaker 可用 `aiobreaker` 實作。
  * 所有請求統一加上  
    ```http
    X-Request-ID,  X-Service-Version
    ```
  * 回傳 JSON 解析為 Pydantic Model；錯誤轉為 `MCPClientError` 子類。

### 3.3 MCPClientFactory
```python
def get_mcp_client(server: str, *, mock: bool = False) -> MCPClientInterface:
    if mock:
        return MockMCPClient()
    if server.startswith("http"):
        return MCPHttpClient(base_url=server)
    raise ValueError("Unsupported MCP server")
```

### 3.4 Observability
* **Metrics**：
  * `mcp_client_requests_total{status="success|error"}`
  * `mcp_client_latency_seconds_bucket`
* **Logging**：使用 `structlog` 輸出 JSON
  ```json
  {"event":"mcp_query","sql":"SELECT ...","latency_ms":12,"status":"success"}
  ```


## 4. 錯誤處理策略
| 類別 | 說明 | 重試? | Circuit Breaker |
|-------|------|-------|-----------------|
| NetworkError | 連線逾時、DNS | ✅ | ✅ |
| ServerError (5xx) | MCP Server 內部錯誤 | ✅ (最多 2) | ✅ |
| ClientError (4xx) | SQL 語法錯、權限不足 | ✗ | ✗ |
| ParseError | JSON 格式錯誤 | ✗ | ✗ |

* 若連續 `N` 次 (預設 5) 失敗，CB 開啟 60 秒。


## 5. 設定項目 (settings.py)
| 變數 | 預設 | 說明 |
|------|------|------|
| `MCP_SERVER_URL` | `http://localhost:3003` | MCP 端點 |
| `MCP_TIMEOUT` | `5.0` | 單次請求秒數 |
| `MCP_MAX_RETRY` | `3` | 最大重試次數 |
| `MCP_CIRCUIT_FAIL_THRESHOLD` | `5` | CB 觸發次數 |
| `MCP_CIRCUIT_RESET_TIMEOUT` | `60` | CB 半開時間 |

> **建議**：全部由 `.env` 控制，並在 CI/CD 時以 K8s Secret / Docker secrets 注入。


## 6. CI/CD 與測試
1. **單元測試**：
   * 使用 `pytest-asyncio`；Mock `httpx` via `respx`。
   * 分支覆蓋率 ≥ 90%。
2. **整合測試**：
   * 啟動 `sqlite-mcp` 與 `postgres-mcp` 容器；測實際端到端。
3. **效能基準**：
   * `pytest-benchmark` 確保 QPS ≥ 200 (本地 4C CPU)。
4. **安全檢查**：
   * 使用 `bandit`、`safety` 於 CI 階段掃描。


## 7. 遷移步驟
1. **建立新 `mcp_common.clients` 模組**。
2. **替換舊呼叫點**：
   * `from services.mcp_client import query_sql` ➜ `from mcp_common.clients import get_mcp_client`。
3. **移除 `simple_mcp_client.py`**。
4. **更新測試**。
5. **文件**：`README`、開發者指南同步更新。


## 8. 未來方向
* **gRPC 傳輸層**：若需高效串流，可研究 gRPC + `grpclib`。
* **Batch API**：加入批次查詢，減少 RTT。
* **分散式追蹤**：整合 OpenTelemetry；傳遞 `traceparent` 至 MCP Server。

---
#### 🏗️ **新一代 MCP Client 架構設計**

##### **1. 統一連接管理器 (Unified Connection Manager)**

```python
# 新架構：apps/bot/src/services/mcp/
├── connection_manager.py      # 統一連接管理
├── connection_pool.py         # 企業級連接池
├── health_checker.py          # 健康檢查機制
├── circuit_breaker.py         # 熔斷器實作
├── retry_policy.py            # 智能重試策略
├── load_balancer.py           # 負載均衡器
├── protocol_adapters/         # 多協議適配器
│   ├── stdio_adapter.py       # STDIO 協議
│   ├── http_adapter.py        # HTTP 協議
│   └── websocket_adapter.py   # WebSocket 協議
└── observability/             # 可觀測性
    ├── metrics_collector.py   # 指標收集
    └── tracing_wrapper.py     # 分散式追蹤
```

##### **2. 企業級連接池設計**

```python
class MCPConnectionPool:
    """
    企業級 MCP 連接池實作
    - 支援連接重用和生命週期管理
    - 內建健康檢查和自動修復
    - 動態擴縮容和負載均衡
    """
    
    def __init__(self, config: PoolConfig):
        self.min_connections = config.min_size      # 最小連接數: 2
        self.max_connections = config.max_size      # 最大連接數: 20
        self.connection_timeout = config.timeout    # 連接超時: 30s
        self.idle_timeout = config.idle_timeout     # 空閒超時: 300s
        self.health_check_interval = 60             # 健康檢查間隔
        
    async def get_connection(self, server_name: str) -> MCPConnection:
        """智能連接獲取 - 負載均衡 + 健康檢查"""
        
    async def return_connection(self, connection: MCPConnection):
        """連接歸還 - 狀態檢查 + 池管理"""
        
    async def health_check_all(self):
        """全面健康檢查 - 自動修復故障連接"""
```

##### **3. 熔斷器 + 重試策略**

```python
class MCPCircuitBreaker:
    """
    智能熔斷器實作
    - 基於成功率的動態熔斷
    - 指數退避重試策略
    - 半開狀態探測恢復
    """
    
    def __init__(self):
        self.failure_threshold = 5      # 失敗次數閾值
        self.success_threshold = 3      # 恢復成功次數
        self.timeout = 60              # 熔斷超時時間
        self.state = CircuitState.CLOSED
        
    async def call_with_protection(self, func, *args, **kwargs):
        """受保護的呼叫 - 自動熔斷 + 重試"""
        
    async def attempt_recovery(self):
        """智能恢復機制 - 漸進式流量恢復"""
```

##### **4. 多協議統一介面**

```python
class UnifiedMCPClient:
    """
    統一 MCP 客戶端介面
    - 支援 STDIO, HTTP, WebSocket 協議
    - 自動協議選擇和故障轉移
    - 透明的協議切換
    """
    
    def __init__(self, config: MCPClientConfig):
        self.connection_pool = MCPConnectionPool(config.pool)
        self.circuit_breaker = MCPCircuitBreaker(config.circuit_breaker)
        self.load_balancer = LoadBalancer(config.servers)
        self.metrics = MetricsCollector()
        
    async def call_tool(
        self, 
        server_name: str, 
        tool_name: str, 
        parameters: Dict[str, Any],
        options: CallOptions = None
    ) -> MCPResponse:
        """
        統一工具呼叫介面
        - 自動選擇最佳協議
        - 內建重試和熔斷保護
        - 完整的可觀測性
        """
        
    async def batch_call(
        self, 
        calls: List[MCPCall]
    ) -> List[MCPResponse]:
        """批次呼叫 - 並行處理 + 結果聚合"""
        
    async def stream_call(
        self, 
        server_name: str, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> AsyncIterator[MCPResponse]:
        """串流呼叫 - 支援長時間運行的查詢"""
```

##### **5. 智能配置管理**

```yaml
# config/mcp_client.yaml - 動態配置支援
mcp_client:
  connection_pool:
    min_size: 2
    max_size: 20
    connection_timeout: 30s
    idle_timeout: 300s
    
  circuit_breaker:
    failure_threshold: 5
    success_threshold: 3
    timeout: 60s
    
  servers:
    sqlite:
      primary:
        protocol: stdio
        command: uv
        args: ["run", "--project", "/path/to/sqlite"]
        weight: 100
      fallback:
        protocol: http
        url: "http://localhost:3003"
        weight: 50
        
    postgres:
      cluster:
        - protocol: stdio
          command: node
          args: ["/path/to/postgres/dist/index.js"]
          weight: 100
        - protocol: http
          url: "http://localhost:3002"
          weight: 80
          
  observability:
    metrics_enabled: true
    tracing_enabled: true
    health_check_interval: 60s
```

##### **6. 可觀測性增強**

```python
class MCPObservability:
    """
    MCP 客戶端可觀測性
    - 詳細的連接和呼叫指標
    - 分散式追蹤支援
    - 異常檢測和告警
    """
    
    def __init__(self):
        # Prometheus 指標
        self.connection_pool_size = Gauge('mcp_connection_pool_size')
        self.active_connections = Gauge('mcp_active_connections')
        self.call_duration = Histogram('mcp_call_duration_seconds')
        self.call_success_rate = Counter('mcp_call_success_total')
        self.circuit_breaker_state = Enum('mcp_circuit_breaker_state')
        
    @trace_calls
    async def trace_mcp_call(self, operation: str, server: str):
        """分散式追蹤包裝器"""
        
    async def collect_health_metrics(self):
        """收集健康狀態指標"""
        
    async def detect_anomalies(self):
        """異常檢測 - 基於歷史基線"""
```

#### 🎯 **實施路線圖**

##### **階段 1: 基礎架構重構 (2週)**
- [ ] 建立統一 MCP 客戶端介面
- [ ] 實作企業級連接池
- [ ] 整合熔斷器和重試機制
- [ ] 基本可觀測性支援

##### **階段 2: 協議擴展 (3週)**
- [ ] HTTP 協議適配器實作
- [ ] WebSocket 協議支援
- [ ] 自動協議選擇邏輯
- [ ] 負載均衡和故障轉移

##### **階段 3: 高級特性 (2週)**
- [ ] 批次和串流呼叫支援
- [ ] 動態配置熱更新
- [ ] 進階監控和告警
- [ ] 效能最佳化調校

##### **階段 4: 生產就緒 (1週)**
- [ ] 完整測試覆蓋
- [ ] 文檔和範例更新
- [ ] 生產環境部署
- [ ] 監控儀表板設置

#### 📊 **預期效益**

| 指標 | 現況 | 目標 | 改善幅度 |
|------|------|------|----------|
| **連接建立時間** | 2-5秒 | 50-100ms | 95% ↓ |
| **併發處理能力** | 10/秒 | 100/秒 | 900% ↑ |
| **錯誤恢復時間** | 手動 | 自動 < 30s | 自動化 |
| **系統可用性** | 95% | 99.9% | 5% ↑ |
| **資源使用效率** | 基準 | 50% ↓ | 最佳化 |

#### 🔧 **遷移策略**

```python
# 平滑遷移計畫
class MCPClientMigration:
    """
    無縫遷移策略
    - 漸進式功能切換
    - A/B 測試支援
    - 回滾機制
    """
    
    def __init__(self):
        self.legacy_client = get_simple_mcp_client()
        self.new_client = UnifiedMCPClient(config)
        self.migration_percentage = 0  # 0-100%
        
    async def call_tool_with_migration(self, *args, **kwargs):
        """遷移期間的雙重呼叫策略"""
        if random.random() * 100 < self.migration_percentage:
            return await self.new_client.call_tool(*args, **kwargs)
        else:
            return await self.legacy_client.call_tool(*args, **kwargs)
```

#### 🎮 **使用範例**

```python
# 新架構使用範例
from src.services.mcp import UnifiedMCPClient, MCPClientConfig

# 初始化客戶端
config = MCPClientConfig.from_file("config/mcp_client.yaml")
mcp_client = UnifiedMCPClient(config)

# 單一呼叫 - 自動最佳化
result = await mcp_client.call_tool(
    server_name="sqlite",
    tool_name="execute_query", 
    parameters={"query": "SELECT * FROM machines"},
    options=CallOptions(timeout=30, retry_count=3)
)

# 批次呼叫 - 高效並行處理
batch_calls = [
    MCPCall("sqlite", "list_tables", {}),
    MCPCall("postgres", "get_machine_status", {"machine_id": "M001"}),
    MCPCall("context7", "analyze_trends", {"days": 7})
]
results = await mcp_client.batch_call(batch_calls)

# 串流呼叫 - 長時間查詢
async for chunk in mcp_client.stream_call(
    "analytics", "generate_report", {"report_type": "monthly"}
):
    process_chunk(chunk)
```

這個最佳化方案將把 LINE MCP 系統提升到企業級的可靠性和擴展性水準，為未來的功能擴展和高負載場景奠定堅實基礎。

> 完成上述設計，可使 MCP Client 具備高效能、可觀測、易維護與安全等特性，為後續微服務擴充奠定穩健基礎。 