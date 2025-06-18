# MCP Common 開發指南

本文檔提供 MCP Common 函式庫的開發指南，包括架構概覽、開發工作流程、測試指南和最佳實踐。

## 📋 專案完整性檢查清單

### ✅ 已完成項目

#### 核心架構
- [x] 基礎資料模型 (`models/`)
- [x] 客戶端介面定義 (`clients/interface.py`)
- [x] Mock 客戶端實作 (`clients/mock_client.py`)
- [x] 客戶端工廠 (`clients/factory.py`)
- [x] 統一客戶端 (`unified_client.py`)

#### 協定適配器
- [x] 基礎適配器介面 (`adapters/base.py`)
- [x] HTTP 適配器 (`adapters/http.py`)
- [x] WebSocket 適配器 (`adapters/websocket.py`)
- [x] STDIO 適配器 (`adapters/stdio.py`)
- [x] Simple 適配器 (`adapters/simple_adapter.py`)
- [x] Legacy 適配器 (`adapters/legacy_adapter.py`)

#### 連接管理
- [x] 連接池 (`connection/pool.py`)
- [x] 斷路器 (`connection/circuit.py`)
- [x] 健康檢查 (`connection/health.py`)
- [x] 重試機制 (`connection/retry.py`)

#### 配置系統
- [x] 配置模型 (`config/settings.py`)
- [x] 配置載入器 (`config/config_loader.py`)
- [x] 預設配置 (`config/default_config.yaml`)

#### 可觀測性
- [x] Prometheus 指標 (`observability/metrics.py`)
- [x] OpenTelemetry 追蹤 (`observability/tracing.py`)

#### 測試套件
- [x] 完整的單元測試
- [x] 整合測試
- [x] 測試配置 (pytest.ini, conftest.py)
- [x] 測試執行腳本 (run_tests.py)

#### 文檔和配置
- [x] README.md
- [x] __init__.py 匯出
- [x] setup.py
- [x] 開發指南

## 🏗️ 架構概覽

### 分層架構

```
應用層
├── UnifiedMCPClient (統一入口點)
├── 向後相容介面
└── 工廠函數

客戶端層
├── MockMCPClient (測試用)
├── HTTPMCPClient (HTTP 協定)
└── 適配器 (包裝現有客戶端)

適配器層
├── BaseProtocolAdapter (協定適配器)
│   ├── HTTPAdapter
│   ├── WebSocketAdapter
│   └── STDIOAdapter
└── BaseMCPClient (客戶端適配器)
    ├── SimpleAdapter
    └── LegacyAdapter

基礎設施層
├── 連接管理 (池化、斷路器、重試)
├── 可觀測性 (指標、追蹤)
└── 配置管理
```

### 設計原則

1. **統一介面**: 所有客戶端都實作 `MCPClientInterface`
2. **適配器模式**: 協定適配器和客戶端適配器分離
3. **可觀測性**: 內建指標和追蹤支援
4. **向後相容**: 平滑遷移路徑
5. **類型安全**: 完整的 Pydantic 模型

## 🛠️ 開發工作流程

### 環境設定

```bash
# 1. 安裝開發依賴
cd libs/python/mcp_common
pip install -e .[dev]

# 2. 安裝測試依賴
pip install pytest pytest-asyncio pytest-cov

# 3. 安裝可選依賴
pip install prometheus-client opentelemetry-api aiohttp websockets
```

### 測試

```bash
# 執行所有測試
python run_tests.py

# 執行快速整合測試
python run_tests.py --quick

# 執行特定測試
pytest tests/test_clients.py -v

# 執行覆蓋率測試
pytest --cov=mcp_common tests/

# 跳過慢速測試
pytest -m "not slow"
```

### 程式碼檢查

```bash
# 類型檢查
mypy mcp_common/

# 程式碼格式化
black mcp_common/ tests/

# 程式碼風格檢查
flake8 mcp_common/ tests/
```

## 📝 開發最佳實踐

### 錯誤處理

```python
# ✅ 好的做法
import logging
from .models.error import MCPError, MCPConnectionError

logger = logging.getLogger(__name__)

async def my_function():
    try:
        result = await risky_operation()
        return result
    except ConnectionError as e:
        logger.error(f"連線錯誤: {e}")
        raise MCPConnectionError(f"無法連接: {e}")
    except ValueError as e:
        logger.warning(f"參數錯誤: {e}")
        raise MCPError(f"無效參數: {e}")

# ❌ 避免的做法
async def bad_function():
    try:
        result = await risky_operation()
        return result
    except Exception:  # 過度廣泛
        return None  # 沉默失敗
```

### 異步資源管理

```python
# ✅ 好的做法
async with client:
    response = await client.call_tool("server", "tool", {})

# 或者
client = get_mcp_client("mock")
try:
    response = await client.call_tool("server", "tool", {})
finally:
    await client.close()

# ❌ 避免的做法
client = get_mcp_client("mock")
response = await client.call_tool("server", "tool", {})
# 忘記關閉客戶端
```

### 指標和追蹤

```python
# ✅ 好的做法
from mcp_common.observability import get_global_metrics, get_global_tracing

metrics = get_global_metrics()
tracing = get_global_tracing()

async def instrumented_function():
    with tracing.start_span("my_operation") as span:
        with metrics.time_request("server", "tool", "http"):
            result = await do_work()
            span.set_attribute("result_size", len(result))
            return result
```

### 配置管理

```python
# ✅ 好的做法
from mcp_common.config import get_config, ServerConfig

config = get_config()
server_config = ServerConfig(
    name="my_server",
    adapter_type="http",
    url="https://api.example.com"
)

# ❌ 避免的做法
# 硬編碼配置
client = HTTPClient(url="https://api.example.com", timeout=30)
```

## 🧪 測試指南

### 測試結構

```
tests/
├── test_clients.py      # 客戶端測試
├── test_models.py       # 資料模型測試
├── test_config.py       # 配置系統測試
├── test_connection.py   # 連接管理測試
├── test_adapters.py     # 適配器測試
├── test_observability.py # 可觀測性測試
├── test_unified_client.py # 統一客戶端測試
└── conftest.py         # 共用夾具
```

### 測試類型

1. **單元測試**: 測試單一模組或類別
2. **整合測試**: 測試多個元件的互動
3. **端到端測試**: 測試完整的工作流程

### 測試夾具

```python
# 使用內建夾具
def test_client_call(mock_client, sample_call, sample_response):
    # 測試邏輯
    pass

# 自訂夾具
@pytest.fixture
async def configured_client():
    client = get_mcp_client("mock")
    # 設定...
    try:
        yield client
    finally:
        await client.close()
```

## 🚀 新功能開發

### 添加新適配器

1. 繼承適當的基類:
   - 協定適配器: `BaseProtocolAdapter`
   - 客戶端適配器: `BaseMCPClient`

2. 實作必要方法:
   ```python
   async def connect(self): ...
   async def disconnect(self): ...
   async def send_request(self, call: MCPCall) -> MCPResponse: ...
   async def health_check(self) -> bool: ...
   ```

3. 在工廠函數中註冊
4. 添加測試
5. 更新文檔

### 添加新指標

1. 在 `MCPMetrics` 中定義新指標
2. 在適當位置添加記錄調用
3. 更新文檔

### 擴展配置

1. 在 `settings.py` 中添加新的配置模型
2. 更新 `default_config.yaml`
3. 添加驗證邏輯
4. 更新測試

## 🔍 除錯指南

### 常見問題

1. **導入錯誤**: 檢查 Python 路徑和依賴
2. **連接失敗**: 檢查網路和伺服器狀態
3. **配置錯誤**: 驗證配置檔案格式
4. **測試失敗**: 檢查測試環境和依賴

### 日誌配置

```python
import logging

# 啟用除錯日誌
logging.basicConfig(level=logging.DEBUG)

# 或者只針對 MCP
logging.getLogger('mcp_common').setLevel(logging.DEBUG)
```

### 性能分析

```python
# 使用內建指標
from mcp_common.observability import get_global_metrics

metrics = get_global_metrics()
print(metrics.get_metrics())  # Prometheus 格式

# 或者使用 Python profiler
import cProfile
cProfile.run('your_code_here()')
```

## 📈 性能最佳化

### 連接管理
- 使用連接池避免頻繁建立連接
- 設定適當的超時值
- 實作斷路器防止級聯失敗

### 批次處理
- 使用 `batch_call` 減少網路往返
- 設定適當的批次大小
- 實作並發控制

### 快取
- 快取工具列表和伺服器資訊
- 實作 TTL 和失效策略
- 監控快取命中率

## 📊 監控和告警

### 關鍵指標
- `mcp_requests_total`: 總請求數
- `mcp_request_duration_seconds`: 請求延遲
- `mcp_connections_active`: 活躍連接數
- `mcp_circuit_breaker_state`: 斷路器狀態

### 告警建議
- 請求錯誤率 > 5%
- 平均延遲 > 1秒
- 斷路器開啟
- 連接池耗盡

## 🔄 版本控制和發布

### 語義化版本
- MAJOR.MINOR.PATCH
- 破壞性變更增加 MAJOR
- 新功能增加 MINOR
- 錯誤修正增加 PATCH

### 發布檢查清單
- [ ] 所有測試通過
- [ ] 更新版本號
- [ ] 更新 CHANGELOG
- [ ] 更新文檔
- [ ] 標記 Git tag
- [ ] 建立發布包

---

## 🤝 貢獻指南

1. Fork 專案
2. 建立功能分支
3. 添加測試
4. 確保所有測試通過
5. 提交 Pull Request
6. 代碼審查
7. 合併

歡迎貢獻！請遵循本指南以確保代碼品質和一致性。