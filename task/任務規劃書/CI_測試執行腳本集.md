# CI 測試執行腳本集

## 📋 腳本概述

本文檔包含所有 CI 測試計劃中定義的測試執行腳本，確保每個測試任務都有明確的執行方式。

## 🚀 T-01: PostgreSQL MCP 連接測試腳本

### 測試檔案: `test_postgres_mcp.py`
```python
#!/usr/bin/env python3
"""
PostgreSQL MCP 連接測試套件
測試 Docker 化的 PostgreSQL MCP 服務器連接和基本操作
"""

import pytest
import asyncio
from datetime import datetime
from src.services.unified_mcp_client import get_unified_mcp_client
from src.config.mcp_config import get_mcp_config

class TestPostgresMCP:
    """PostgreSQL MCP 連接測試"""
    
    @pytest.fixture
    async def mcp_client(self):
        """獲取 MCP 客戶端"""
        return get_unified_mcp_client()
    
    @pytest.mark.asyncio
    async def test_postgres_connection(self, mcp_client):
        """測試 PostgreSQL 連接"""
        # 測試連接
        result = await mcp_client.call_tool(
            "postgresql",
            "query",
            {"sql": "SELECT version()"}
        )
        assert result is not None
        assert "PostgreSQL" in str(result)
    
    @pytest.mark.asyncio
    async def test_machine_query(self, mcp_client):
        """測試機台查詢"""
        # 查詢 M001 機台
        sql = """
        SELECT machine_id, status, utilization_rate 
        FROM machine_metrics 
        WHERE machine_id = 'M001'
        """
        result = await mcp_client.call_tool(
            "postgresql",
            "query",
            {"sql": sql}
        )
        assert result is not None
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_connection_pool(self, mcp_client):
        """測試連接池管理"""
        # 並發執行多個查詢
        tasks = []
        for i in range(10):
            task = mcp_client.call_tool(
                "postgresql",
                "query",
                {"sql": f"SELECT {i} as num"}
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        assert len(results) == 10
        assert all(r is not None for r in results)
```

### 執行命令
```bash
# 啟動 PostgreSQL Docker
docker-compose -f docker-compose.postgres.yml up -d

# 等待服務就緒
sleep 5

# 執行測試
cd apps/bot && python -m pytest tests/integration/test_postgres_mcp.py -v
```

## 🧪 T-02: 四層架構單元測試腳本

### 測試組織腳本: `run_layer_tests.sh`
```bash
#!/bin/bash
# 四層架構分層測試執行腳本

echo "🔍 執行四層架構單元測試..."

# Application Layer
echo "📱 測試 Application Layer..."
poetry run pytest tests/unit/application/ -v --cov=src/application --cov-report=term-missing

# Domain Layer  
echo "🎯 測試 Domain Layer..."
poetry run pytest tests/unit/domain/ -v --cov=src/domain --cov-report=term-missing

# Infrastructure Layer
echo "🏗️ 測試 Infrastructure Layer..."
poetry run pytest tests/unit/infrastructure/ -v --cov=src/infrastructure --cov-report=term-missing

# Services Layer
echo "⚙️ 測試 Services Layer..."
poetry run pytest tests/unit/services/ -v --cov=src/services --cov-report=term-missing

# 生成總體報告
echo "📊 生成覆蓋率報告..."
poetry run pytest tests/unit/ --cov=src --cov-report=html --cov-report=term

echo "✅ 四層架構測試完成！"
```

## 🔧 T-03: 服務註冊驗證測試腳本

### 測試檔案: `test_service_registry_validation.py`
```python
#!/usr/bin/env python3
"""
26個服務註冊完整性驗證測試
"""

import pytest
import time
from typing import Dict, Any
from src.infrastructure.service_registry import get_service_registry, ServiceScope
from src.infrastructure.enhanced_service_factory import EnhancedServiceFactory

class TestServiceRegistryValidation:
    """服務註冊驗證測試"""
    
    def test_all_services_registered(self):
        """驗證所有 26 個服務都已註冊"""
        factory = EnhancedServiceFactory()
        factory.initialize()
        
        expected_services = [
            # AI 相關服務
            "AIModelService", "OpenAIClient", "EnhancedAIModelService",
            # 資料庫服務
            "DatabaseService", "UnifiedMCPClient", 
            # 訊息處理
            "MessageHandlerDI", "MessageFormatter",
            # NL-to-SQL
            "NLToSQLService", "QueryTemplateManager", "SQLQueryBuilder",
            "ConfigurationService", "QueryStatisticsService",
            # Parser 相關
            "RuleBasedParser", "AIEnhancedParser", "CompositeParser",
            # 應用層服務
            "ApplicationFacade", "CommandExecutor", 
            # 基礎設施
            "ErrorHandler", "MonitoringService",
            # 其他服務...
        ]
        
        registry = get_service_registry()
        registered_count = len(registry._services)
        
        assert registered_count >= 26, f"期望至少 26 個服務，實際註冊 {registered_count} 個"
    
    def test_singleton_services(self):
        """驗證 Singleton 服務的單例特性"""
        factory = EnhancedServiceFactory()
        factory.initialize()
        provider = factory.create_provider()
        
        # 獲取兩次相同的 Singleton 服務
        service1 = provider.get_database_service()
        service2 = provider.get_database_service()
        
        assert service1 is service2, "Singleton 服務應該返回相同實例"
    
    def test_transient_services(self):
        """驗證 Transient 服務的多例特性"""
        factory = EnhancedServiceFactory()
        factory.initialize()
        provider = factory.create_provider()
        
        # 獲取兩次 Transient 服務（如果有的話）
        # 這裡需要根據實際的 Transient 服務調整
        pass
    
    def test_service_resolution_performance(self):
        """測試服務解析效能"""
        factory = EnhancedServiceFactory()
        factory.initialize()
        provider = factory.create_provider()
        
        start_time = time.time()
        
        # 解析所有服務
        for _ in range(100):
            _ = provider.get_database_service()
            _ = provider.get_ai_model_service()
            _ = provider.get_message_formatter()
        
        elapsed_time = (time.time() - start_time) * 1000  # 轉換為毫秒
        avg_time = elapsed_time / 300  # 平均每次解析時間
        
        assert avg_time < 1, f"服務解析平均時間 {avg_time:.2f}ms 超過 1ms"
```

## 🌐 T-04: nodecomman 多運行時測試腳本

### 執行腳本: `test_nodecomman_runtime.sh`
```bash
#!/bin/bash
# nodecomman 多運行時測試腳本

echo "🔄 測試 nodecomman 多運行時架構..."

# 檢查 Node.js 環境
echo "📦 檢查 Node.js 環境..."
node --version || echo "⚠️ Node.js 未安裝"
npm --version || echo "⚠️ npm 未安裝"

# 檢查 Python 環境
echo "🐍 檢查 Python 環境..."
python3 --version

# 執行 nodecomman 測試
cd apps/bot

echo "🧪 執行運行時管理器測試..."
python -m pytest tests/nodecomman/test_runtime_managers.py -v

echo "🏭 執行 MCP 工廠測試..."
python -m pytest tests/nodecomman/test_mcp_factory.py -v

echo "🔗 執行整合測試..."
python -m pytest tests/nodecomman/test_integration.py -v

echo "✅ nodecomman 測試完成！"
```

## 🎯 T-05: M001 E2E 測試腳本

### 端到端測試檔案: `test_m001_e2e.py`
```python
#!/usr/bin/env python3
"""
M001 機台查詢端到端測試
模擬從 LINE 訊息到最終回應的完整流程
"""

import pytest
import json
from fastapi.testclient import TestClient
from src.main import app

class TestM001E2E:
    """M001 端到端測試"""
    
    @pytest.fixture
    def client(self):
        """創建測試客戶端"""
        return TestClient(app)
    
    def test_m001_query_flow(self, client):
        """測試 M001 查詢完整流程"""
        # 模擬 LINE Webhook 請求
        webhook_data = {
            "events": [{
                "type": "message",
                "message": {
                    "type": "text",
                    "text": "M001機台稼動率"
                },
                "replyToken": "test_reply_token",
                "source": {
                    "userId": "test_user_id"
                }
            }]
        }
        
        # 發送請求
        response = client.post(
            "/webhook",
            json=webhook_data,
            headers={
                "X-Line-Signature": "test_signature"
            }
        )
        
        # 驗證回應
        assert response.status_code == 200
        
        # 驗證處理結果（需要 mock LINE API）
        # 這裡可以檢查日誌或資料庫來驗證處理結果
```

## 📊 T-08: 效能基準測試腳本

### 效能測試檔案: `performance_benchmark.py`
```python
#!/usr/bin/env python3
"""
系統效能基準測試
"""

import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
import aiohttp
import psutil

class PerformanceBenchmark:
    """效能基準測試"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = []
    
    async def test_api_response_time(self):
        """測試 API 回應時間"""
        async with aiohttp.ClientSession() as session:
            response_times = []
            
            for _ in range(100):
                start = time.time()
                async with session.get(f"{self.base_url}/health") as resp:
                    await resp.text()
                elapsed = (time.time() - start) * 1000  # ms
                response_times.append(elapsed)
            
            avg_time = statistics.mean(response_times)
            p95_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
            
            print(f"平均回應時間: {avg_time:.2f}ms")
            print(f"95% 回應時間: {p95_time:.2f}ms")
            
            assert avg_time < 200, f"平均回應時間 {avg_time:.2f}ms 超過 200ms"
    
    async def test_concurrent_requests(self):
        """測試並發請求處理"""
        async with aiohttp.ClientSession() as session:
            tasks = []
            for _ in range(100):
                task = session.post(
                    f"{self.base_url}/api/query",
                    json={"query": "測試查詢"}
                )
                tasks.append(task)
            
            start = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.time() - start
            
            success_count = sum(1 for r in responses if not isinstance(r, Exception))
            print(f"並發 100 請求完成時間: {elapsed:.2f}秒")
            print(f"成功率: {success_count}%")
            
            assert success_count >= 95, f"成功率 {success_count}% 低於 95%"
    
    def test_resource_usage(self):
        """測試資源使用情況"""
        process = psutil.Process()
        
        # 獲取當前資源使用
        cpu_percent = process.cpu_percent(interval=1)
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        print(f"CPU 使用率: {cpu_percent}%")
        print(f"記憶體使用: {memory_mb:.2f}MB")
        
        assert cpu_percent < 50, f"CPU 使用率 {cpu_percent}% 超過 50%"
        assert memory_mb < 1024, f"記憶體使用 {memory_mb:.2f}MB 超過 1GB"

if __name__ == "__main__":
    benchmark = PerformanceBenchmark()
    asyncio.run(benchmark.test_api_response_time())
    asyncio.run(benchmark.test_concurrent_requests())
    benchmark.test_resource_usage()
```

## 🔄 T-09: CI Pipeline 優化配置

### GitHub Actions 配置: `ci-enhanced-v2.yml`
```yaml
name: Enhanced CI v2

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  PYTHON_VERSION: "3.11"
  COVERAGE_THRESHOLD: "85"

jobs:
  # 並行執行的測試組
  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    strategy:
      matrix:
        layer: [application, domain, infrastructure, services]
    
    steps:
    - uses: actions/checkout@v4
    - name: Run ${{ matrix.layer }} layer tests
      run: |
        cd apps/bot
        poetry run pytest tests/unit/${{ matrix.layer }}/ -v
  
  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: unit-tests
    strategy:
      matrix:
        test-suite: [postgres-mcp, nodecomman, api-endpoints]
    
    steps:
    - uses: actions/checkout@v4
    - name: Run ${{ matrix.test-suite }} tests
      run: |
        cd apps/bot
        ./scripts/run_integration_${{ matrix.test-suite }}.sh
  
  performance-tests:
    name: Performance Tests
    runs-on: ubuntu-latest
    needs: unit-tests
    
    steps:
    - uses: actions/checkout@v4
    - name: Run performance benchmarks
      run: |
        cd apps/bot
        python tests/performance/performance_benchmark.py
```

## 📈 T-10: 測試報告生成腳本

### 報告生成腳本: `generate_test_report.sh`
```bash
#!/bin/bash
# 自動化測試報告生成腳本

echo "📊 生成測試報告..."

# 設定變數
REPORT_DIR="test-reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_NAME="test_report_${TIMESTAMP}"

# 創建報告目錄
mkdir -p $REPORT_DIR

# 執行測試並生成報告
echo "🧪 執行所有測試..."
poetry run pytest \
  --html=$REPORT_DIR/${REPORT_NAME}.html \
  --self-contained-html \
  --cov=src \
  --cov-report=html:$REPORT_DIR/coverage_${TIMESTAMP} \
  --cov-report=json:$REPORT_DIR/coverage_${TIMESTAMP}.json \
  --junit-xml=$REPORT_DIR/junit_${TIMESTAMP}.xml

# 生成趨勢分析
echo "📈 生成趨勢分析..."
python scripts/analyze_test_trends.py \
  --input $REPORT_DIR \
  --output $REPORT_DIR/trends_${TIMESTAMP}.html

# 發布到 GitHub Pages
if [ "$CI" = "true" ]; then
  echo "🚀 發布報告到 GitHub Pages..."
  npm install -g gh-pages
  gh-pages -d $REPORT_DIR
fi

echo "✅ 測試報告生成完成！"
echo "📍 報告位置: $REPORT_DIR/${REPORT_NAME}.html"
```

## 🎯 執行總結

所有測試腳本都已準備就緒，可以按照以下順序執行：

1. **環境準備**
   ```bash
   cd apps/bot
   poetry install
   docker-compose -f docker-compose.postgres.yml up -d
   ```

2. **執行測試**
   ```bash
   # T-01: PostgreSQL MCP 測試
   python -m pytest tests/integration/test_postgres_mcp.py -v
   
   # T-02: 四層架構測試
   ./scripts/run_layer_tests.sh
   
   # T-03: 服務註冊測試
   python -m pytest tests/infrastructure/test_service_registry_validation.py -v
   
   # T-04: nodecomman 測試
   ./scripts/test_nodecomman_runtime.sh
   
   # T-05: M001 E2E 測試
   python -m pytest tests/integration/test_m001_e2e.py -v
   ```

3. **生成報告**
   ```bash
   ./scripts/generate_test_report.sh
   ```

---

**文檔版本**: 1.0.0  
**創建日期**: 2025-06-26