# LINE MCP Bot

LINE Bot 整合 Model Context Protocol (MCP) 的智慧製造監控系統。

## 特色功能

- 🤖 LINE Bot 整合
- 🔗 MCP 協議支援
- 🏭 製造業資料查詢
- 🧠 AI 增強的自然語言處理
- 📊 即時監控與分析

## 快速開始

```bash
# 安裝依賴
poetry install

# 設置環境變數
cp .env.example .env

# 啟動服務
poetry run uvicorn src.main:app --reload
```

## 環境變數

參考專案根目錄的 CLAUDE.md 文件了解完整的環境變數配置。

## API 文檔

### LINE Bot 指令

系統支援以下 LINE Bot 指令：

#### 基本指令
- `/help` - 顯示幫助資訊
- `/status` - 查看系統狀態
- `/info` - 查看系統資訊
- `/models` - 查看可用的 AI 模型
- `/tables` - 查看資料庫表格清單

#### SQL 查詢指令
```bash
/sql <PostgreSQL查詢語句>
```

### MCP 工具調用範例

系統使用 PostgreSQL MCP 服務器，以下是標準的工具調用範例：

#### 基本查詢
```python
# Python MCP 客戶端調用
result = await mcp_client.call_tool(
    server_name="postgres",
    tool_name="query",
    parameters={"sql": "SELECT * FROM machine_data LIMIT 5"}
)
```

#### 表格結構查詢
```python
# 查看表格清單
result = await mcp_client.call_tool(
    server_name="postgres",
    tool_name="query",
    parameters={
        "sql": "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    }
)

# 查看表格欄位結構
result = await mcp_client.call_tool(
    server_name="postgres",
    tool_name="query", 
    parameters={
        "sql": "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'machine_data'"
    }
)
```

#### 機台數據查詢
```python
# M001 機台稼動率查詢
result = await mcp_client.call_tool(
    server_name="postgres",
    tool_name="query",
    parameters={
        "sql": "SELECT machine_id, AVG(utilization_rate) as avg_rate FROM machine_data WHERE machine_id = 'M001' GROUP BY machine_id"
    }
)
```

### 錯誤處理

MCP 工具調用的錯誤處理模式：

```python
try:
    result = await mcp_client.call_tool(
        server_name="postgres",
        tool_name="query",
        parameters={"sql": query},
        timeout=30.0  # 可選的超時設置
    )
    
    if result.get("success"):
        data = result.get("data", [])
        # 處理成功結果
    else:
        error_msg = result.get("error", "未知錯誤")
        # 處理錯誤
        
except Exception as e:
    # 處理連接或其他異常
    logger.error(f"MCP 調用失敗: {e}")
```

### 配置範例

#### PostgreSQL MCP 服務器配置
```yaml
# docker-compose.postgres.yml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: admin  
      POSTGRES_PASSWORD: admin
    ports:
      - "5432:5432"
```

#### MCP 客戶端配置
```python
# MCP 服務器連接配置
server_configs = {
    "postgres": {
        "command": "npx",
        "args": [
            "@modelcontextprotocol/server-postgres",
            "postgresql://admin:admin@localhost:5432/mydb"
        ],
        "transport": {
            "type": "stdio"
        }
    }
}
```

## 開發

參考專案根目錄的開發指南和 CI/CD 文檔。

### 測試

```bash
# 執行所有測試
poetry run pytest -v

# 執行 PostgreSQL MCP 測試
python test_m001_final.py

# 執行整合測試  
python test_complete_integration.py
```

### 程式碼品質

```bash
# 格式化程式碼
poetry run black src/

# 檢查程式碼風格
poetry run ruff check src/

# 類型檢查
poetry run mypy src/
```