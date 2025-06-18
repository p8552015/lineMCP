# 🛠️ MCP Client 全面改善藍圖

> 在執行任何測試前，請務必先啟動 Poetry 虛擬環境：
> ```bash
> cd apps/bot
> poetry shell    # or source $(poetry env info --path)/bin/activate
> pytest -q       # 於 venv 內執行測試
> ```

---

## 1. 問題總覽
| # | 痛點 | 說明 |
|---|------|------|
| 1 | 兩套 Client 實作 | `mcp_client.py`、`simple_mcp_client.py` 介面/邏輯不一致，維護成本高 |
| 2 | 同步阻塞 | 同步 `requests` 與非同步 `httpx` 混用，降低吞吐 |
| 3 | 可靠性不足 | 缺 Retry、Circuit Breaker，失敗風險高 |
| 4 | 型別與驗證 | 無 Pydantic Model，IDE 沒補全，易出錯 |
| 5 | 可觀測性不足 | 無 metrics / tracing，難以問題定位 |
| 6 | 配置發散 | 端點、超時分散各處，不易統一管理 |

---

## 2. 改善目標
1. **單一介面**：`MCPClientInterface` 為唯一入口。
2. **全非同步**：`httpx.AsyncClient` + 連線池。
3. **企業級可靠性**：Retry、Circuit Breaker、Timeout、健康檢查。
4. **型別安全**：全面 Pydantic schema；自動驗證、補全。
5. **可觀測性**：Prometheus 指標 + OpenTelemetry tracing。
6. **集中設定**：`settings.py` + `.env` + `mcp_client.yaml`。
7. **易測試**：Mock Client + 高覆蓋率單元/整合測試。

---

## 3. 模組目錄規劃
```text
libs/python/mcp_common/
├── clients/
│   ├── interface.py      # Protocol 介面
│   ├── http_client.py    # 預設實作 (HTTP)
│   ├── mock_client.py    # 測試用
│   └── factory.py        # get_mcp_client()
├── connection/
│   ├── pool.py           # 連接池
│   ├── circuit.py        # 熔斷器
│   ├── retry.py          # 重試策略
│   └── health.py         # 健康檢查
├── adapters/             # 協議適配器
│   ├── stdio.py
│   ├── websocket.py
│   └── http.py
├── models/               # Pydantic schema
│   ├── base.py
│   ├── query.py
│   └── error.py
└── observability/
    ├── metrics.py
    └── tracing.py
```

---

## 4. 核心元件設計
### 4.1 MCPClientInterface
```python
class MCPClientInterface(Protocol):
    async def call_tool(
        self,
        server: str,
        tool: str,
        params: dict[str, Any],
        *,
        options: CallOptions | None = None,
    ) -> MCPResponse: ...

    async def batch_call(self, calls: list[MCPCall]) -> list[MCPResponse]: ...
    async def stream_call(self, ...) -> AsyncIterator[MCPResponse]: ...
    async def status(self) -> HealthStatus: ...
```

### 4.2 HTTP 實作 (MCPHttpClient)
* `httpx.AsyncClient(limits=...)` 共享連線池。
* `tenacity.AsyncRetrying`：指數退避，最多 3 次。
* `aiobreaker.CircuitBreaker`：失敗 5 次熔斷 60s。
* 自動注入 `X-Request-ID`、`X-Service-Version`。

### 4.3 連接池與負載均衡
* `MCPConnectionPool`：針對每個伺服器維持 2~20 條連線。
* `LoadBalancer` (Round-Robin + 服務權重)。

### 4.4 可觀測性
* Metrics：
  * `mcp_client_requests_total{status}`
  * `mcp_client_latency_seconds_bucket`
  * `mcp_circuit_state`
* Tracing：`@trace_calls` decorator；傳遞 `traceparent`。

### 4.5 設定檔 (YAML + env)
```yaml
mcp_client:
  pool: {min_size: 2, max_size: 20, timeout: 30}
  circuit: {failure_threshold: 5, success_threshold: 3, timeout: 60}
  servers:
    sqlite: http://localhost:3003
    postgres: http://localhost:3002
```

### 4.6 遠端 MCP 整合（OpenAI Responses API）
參考官方文件 <https://platform.openai.com/docs/guides/tools-remote-mcp>，OpenAI 已支援在 `responses.create` API 內直接掛載遠端 MCP 伺服器。

**設計要點**
1. `UnifiedMCPClient` 應能辨識 `server_url` 為外部網域時，自動切換為「Remote Mode」，以 **單次** HTTP/HTTPS 連線完成 LLM→MCP 交互，減少延遲。  
2. 遵循 OpenAI 定義的 `server_label`、`allowed_tools` 欄位來做白名單控制，確保安全。  
3. 透過 `headers` 支援附加 API Key、簽章等認證資訊。  
4. 對遠端 MCP 的健康檢查改以 **HEAD /mcp/health** 或 OpenAI 規範的 ping 機制。  

**Python 範例**
```python
from openai import OpenAI
from mcp_common.clients import get_mcp_client

client = OpenAI()

# 呼叫遠端 calendar MCP 直接由 OpenAI SDK 處理
resp = client.responses.create(
    model="gpt-4o-mini",
    input=[{"role": "user", "content": "Add lunch with Sarah Friday"}],
    tools=[{
        "type": "mcp",
        "server_label": "calendar",
        "server_url": "https://mcp.calendar.ai/mcp",
        "allowed_tools": ["create_event", "check_availability"],
        "require_approval": "auto"
    }]
)

# 在本地 UnifiedMCPClient 混合管理本地與遠端 MCP
mcp = get_mcp_client("calendar")    # 透過 factory 讀取 config/mcp_client.yaml
await mcp.call_tool(
    server="calendar",
    tool="create_event",
    params={"title": "Lunch", "time": "2025-06-21T12:00"}
)
```

**YAML 設定片段**
```yaml
mcp_client:
  servers:
    calendar:
      protocol: remote   # remote 代表交由 OpenAI SDK route
      server_url: https://mcp.calendar.ai/mcp
      allowed_tools: [create_event, check_availability]
      headers:
        x-calendar-signature: "${CALENDAR_SIGNATURE}"
```

> 如此即可在本地 AI Agent 與 OpenAI Responses API 之間共用同一套 MCP Client，並且對外擴充到任何符合規範的遠端 MCP 服務。

---

## 5. 實施里程碑
| 階段 | 內容 | 估時 |
|------|------|------|
| P0 | 建立 `mcp_common` 基礎結構 (interface, http_client, models) | 2 天 |
| P0 | 重構現有呼叫點 → `get_mcp_client()` | 1 天 |
| P1 | 連接池 + Retry + CB 整合 | 3 天 |
| P1 | Prometheus metrics + structlog | 1 天 |
| P2 | WebSocket / STDIO 適配器 | 4 天 |
| P2 | Batch / Stream API | 2 天 |
| P3 | OpenTelemetry tracing + Grafana Dashboard | 2 天 |

---

## 6. 測試與驗證策略
1. **單元測試**：`pytest-asyncio` + `respx`；覆蓋率 ≥ 90%。
2. **整合測試**：使用 Docker Compose 啟動 MCP Servers，跑真實 query。
3. **效能測試**：`pytest-benchmark`；目標 QPS ≥ 200 (4C)。
4. **混沌測試**：利用 `toxiproxy` 注入延遲/丟包，驗證熔斷與重試行為。

---

## 7. 漸進式遷移方案
```python
legacy = get_simple_mcp_client()
modern = get_mcp_client()

async def call_with_migration(*args, **kw):
    ratio = float(os.getenv("MCP_MIGRATION_RATIO", 0))
    if random.random() < ratio:
        return await modern.call_tool(*args, **kw)
    return await legacy.call_tool(*args, **kw)
```
* 透過環境變數 `MCP_MIGRATION_RATIO` 控制流量比例。
* 支援即時回滾：將比例設 0 → 全流量回舊 Client。

---

## 8. 預期成效
| 指標 | 基準 | 目標 |
|------|------|------|
| 建立連接耗時 | 2-5 s | 100 ms |
| 併發能力 | 10 rps | ≥ 100 rps |
| 失敗恢復 | 手動 | < 30 s 自動 |
| 可用性 SLA | 95% | 99.9% |
| 錯誤率 | 1% | < 0.1% |

---

## 9. 參考實作
* `aiobreaker`：熔斷器函式庫
* `tenacity`：Retry 策略
* `httpx`：非同步 HTTP
* `prometheus_client`：Metrics 暴露
* `opentelemetry-sdk`：Tracing

---

> 依照本藍圖落實，可確保 MCP Client 達到高效能、可靠度與可維護性，並為後續多協議與雲端擴充打下堅實基礎。 