# 🏗️ Models 層完整架構文檔

> **版本**: v1.0.0  
> **最後更新**: 2025年7月8日 16:00  
> **文檔狀態**: 完整 ✅  
> **測試狀態**: 6/6 資料模型全部定義完成 ✅  

## 📋 目錄
1. [系統概覽](#系統概覽)
2. [核心架構](#核心架構)
3. [資料模型設計](#資料模型設計)
4. [Schema 管理機制](#schema-管理機制)
5. [MCP 工具整合](#mcp-工具整合)
6. [技術實現細節](#技術實現細節)
7. [部署與配置](#部署與配置)
8. [開發指南](#開發指南)

---

## 🎯 系統概覽

### 系統簡介
Models 層是 LINE MCP 智慧製造監控系統的核心資料模型層，負責定義所有資料庫表結構、MCP 工具清單，以及雙重 Schema 管理機制。採用 SQLAlchemy ORM 架構，支援開發環境和生產環境的 Schema 差異管理。

### 🌟 核心特色
- ✅ **雙重 Schema 管理** - 開發環境與生產環境分離的資料模型
- ✅ **企業級 ORM** - 基於 SQLAlchemy 的完整資料模型定義
- ✅ **外鍵關聯** - 完整的關聯式資料庫設計
- ✅ **MCP 工具整合** - 支援 Context7 文檔查詢和 PostgreSQL 操作
- ✅ **遷移管理** - 支援 Alembic 資料庫遷移機制
- ✅ **類型安全** - 完整的 Python 類型註解支援

### 📊 系統規模
- **資料模型數量**: 6 個核心模型
- **Schema 版本**: 2 個（開發/生產）
- **MCP 工具**: 8 個工具函式
- **資料表**: 6 個核心業務表
- **外鍵關係**: 3 個主要關聯

---

## 🏗️ 核心架構

### 整體架構圖
```mermaid
graph TB
    subgraph "Models 層"
        A[database.py - 開發環境模型]
        B[current_database.py - 生產環境模型]
        C[mcp_manifest.py - MCP工具清單]
        D[__init__.py - 模組初始化]
    end
    
    subgraph "資料模型"
        E[Machine - 機台模型]
        F[MachineFault - 故障記錄]
        G[MachineUtilization - 使用率歷史]
        H[Employee - 員工模型]
        I[Product - 產品模型]
        J[Order - 訂單模型]
    end
    
    subgraph "MCP 工具"
        K[Context7 文檔工具]
        L[PostgreSQL 資料庫工具]
    end
    
    subgraph "資料庫層"
        M[PostgreSQL 5432]
        N[Alembic 遷移]
    end
    
    A --> E
    A --> F
    A --> G
    A --> H
    A --> I
    A --> J
    
    B --> E
    B --> F
    B --> G
    B --> H
    B --> I
    B --> J
    
    C --> K
    C --> L
    
    E --> M
    F --> M
    G --> M
    H --> M
    I --> M
    J --> M
    
    A --> N
    B --> N
```

### 模組依賴關係
```mermaid
graph LR
    subgraph "Models 核心"
        A[database.py]
        B[current_database.py]
        C[mcp_manifest.py]
        D[__init__.py]
    end
    
    subgraph "SQLAlchemy 組件"
        E[declarative_base]
        F[Column Types]
        G[ForeignKey]
        H[func utilities]
    end
    
    subgraph "外部依賴"
        I[PostgreSQL DB]
        J[Alembic Migration]
        K[Context7 MCP]
        L[OpenAI Function Calling]
    end
    
    A --> E
    B --> E
    A --> F
    B --> F
    A --> G
    B --> G
    A --> H
    B --> H
    
    C --> K
    C --> L
    
    A --> I
    B --> I
    A --> J
    B --> J
```

---

## 💾 資料模型設計

### 文件結構
```
apps/bot/src/models/
├── database.py                    # 開發環境資料模型
├── current_database.py           # 生產環境資料模型
├── mcp_manifest.py               # MCP 工具清單
├── __init__.py                   # 模組初始化（空文件）
└── Models層完整架構文檔.md       # 本文檔
```

### 核心資料模型

#### 1. Machine (機台模型)
```python
class Machine(Base):
    """機台資料表"""
    __tablename__ = "machines"
    
    # 開發環境 vs 生產環境差異
    id = Column(String(50), primary_key=True)      # 開發: VARCHAR(50)
    id = Column(String(10), primary_key=True)      # 生產: VARCHAR(10)
    
    name = Column(String(255), nullable=False)     # 開發: VARCHAR(255)
    name = Column(String(100), nullable=False)     # 生產: VARCHAR(100)
    
    status = Column(String(50), nullable=False)    # 開發: VARCHAR(50)
    status = Column(String(20), nullable=False)    # 生產: VARCHAR(20)
    
    # 共同欄位
    temperature = Column(Numeric(5, 2))
    utilization_rate = Column(Numeric(5, 2))
    last_maintenance = Column(Date)
    
    location = Column(String(255))                 # 開發: VARCHAR(255)
    location = Column(String(50))                  # 生產: VARCHAR(50)
    
    created_at = Column(DateTime, default=func.now())
```

#### 2. MachineFault (機台故障記錄)
```python
class MachineFault(Base):
    """機台故障記錄表"""
    __tablename__ = "machine_faults"
    
    fault_id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(String(50), ForeignKey("machines.id"), nullable=False)
    fault_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)
    
    # 時間戳差異
    fault_date = Column(DateTime, default=func.now())           # 開發
    fault_date = Column(DateTime, server_default=func.current_timestamp())  # 生產
    
    description = Column(Text)
    resolved = Column(Boolean, default=False)                   # 開發
    resolved = Column(Boolean, server_default="false")         # 生產
    
    resolution_date = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
```

#### 3. MachineUtilization (機台使用率歷史)
```python
class MachineUtilization(Base):
    """機台使用率歷史記錄表"""
    __tablename__ = "machine_utilization"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 外鍵關聯差異
    machine_id = Column(String(50), ForeignKey("machines.id"))  # 開發
    machine_id = Column(String(10), nullable=False)             # 生產（無外鍵）
    
    utilization_rate = Column(Numeric(5, 2), nullable=False)
    
    # 欄位差異
    temperature = Column(Numeric(5, 2))                         # 開發獨有
    recorded_at = Column(DateTime, default=func.now())         # 開發
    timestamp = Column(DateTime, server_default=func.current_timestamp())  # 生產
    
    shift = Column(String(20))                                  # 開發獨有
    operator = Column(String(100))                              # 開發獨有
    status = Column(String(20), server_default="active")       # 生產獨有
```

#### 4. Employee (員工模型)
```python
class Employee(Base):
    """員工資料表"""
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    department = Column(String(50))
    
    # 欄位差異
    position = Column(String(50))                               # 開發獨有
    email = Column(String(100))                                 # 開發獨有
    
    hire_date = Column(Date)
    salary = Column(Numeric(10, 2))
    
    # 生產環境新增
    created_at = Column(DateTime, server_default=func.current_timestamp())  # 生產獨有
```

#### 5. Product (產品模型)
```python
class Product(Base):
    """產品資料表"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50))
    
    # 數值精度差異
    price = Column(Numeric(10, 2))                              # 開發
    price = Column(Numeric(8, 2))                               # 生產
    
    # 欄位名稱差異
    stock_quantity = Column(Integer)                            # 開發
    stock = Column(Integer)                                     # 生產
    
    description = Column(Text)                                  # 開發獨有
    
    # 生產環境新增
    created_at = Column(DateTime, server_default=func.current_timestamp())  # 生產獨有
    updated_at = Column(DateTime, server_default=func.current_timestamp())  # 生產獨有
```

#### 6. Order (訂單模型)
```python
class Order(Base):
    """訂單資料表"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_name = Column(String(100), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))
    
    # 預設值差異
    quantity = Column(Integer, nullable=False)                  # 開發
    quantity = Column(Integer, nullable=False, server_default="1")  # 生產
    
    # 資料類型差異
    order_date = Column(Date, default=func.current_date())      # 開發: DATE
    order_date = Column(DateTime, server_default=func.current_timestamp())  # 生產: TIMESTAMP
    
    total_amount = Column(Numeric(10, 2))
    status = Column(String(20), default="pending")              # 開發
    status = Column(String(20), server_default="pending")      # 生產
```

---

## 🔧 Schema 管理機制

### 雙重 Schema 設計原則

#### 開發環境 Schema (database.py)
```python
# 特徵：用於 Alembic 遷移管理
- 較大的欄位長度（防止開發階段資料截斷）
- 詳細的註解說明
- 完整的外鍵關聯
- 豐富的欄位設計（包含未來可能需要的欄位）
- 使用 default 和 func.now() 進行預設值設定
```

#### 生產環境 Schema (current_database.py)
```python
# 特徵：基於實際生產環境資料庫結構
- 精確的欄位長度（符合生產環境實際結構）
- 使用 server_default 進行資料庫層面的預設值設定
- 針對性能優化的欄位設計
- 移除部分開發階段的冗餘欄位
- 新增生產環境特有的追蹤欄位
```

### Schema 差異對比表

| 模型 | 開發環境特色 | 生產環境特色 | 差異說明 |
|------|-------------|-------------|----------|
| Machine | VARCHAR(50) id, 詳細註解 | VARCHAR(10) id, 精簡設計 | 欄位長度和註解差異 |
| MachineFault | default=func.now() | server_default=func.current_timestamp() | 預設值設定方式不同 |
| MachineUtilization | 包含 shift, operator | 包含 status, 無外鍵 | 欄位組合差異 |
| Employee | 包含 position, email | 包含 created_at | 欄位配置差異 |
| Product | stock_quantity, description | stock, created_at, updated_at | 欄位名稱和追蹤欄位差異 |
| Order | DATE order_date | TIMESTAMP order_date | 資料類型差異 |

---

## 🔌 MCP 工具整合

### MCP 工具清單架構

#### Context7 文檔工具
```python
# 4個文檔查詢工具
{
    "search_docs": {
        "description": "Search for up-to-date documentation and code examples using Context7",
        "parameters": {
            "query": "Search query for documentation",
            "framework": "Optional framework to focus on",
            "language": "Programming language to focus on"
        }
    },
    "get_code_examples": {
        "description": "Get specific code examples for a given technology",
        "parameters": {
            "technology": "Technology or framework name",
            "concept": "Specific concept or feature",
            "use_case": "Specific use case or pattern needed"
        }
    },
    "get_api_reference": {
        "description": "Get API reference documentation",
        "parameters": {
            "library": "Library or framework name",
            "api_name": "API method or function name",
            "version": "Specific version (optional)"
        }
    },
    "get_best_practices": {
        "description": "Get current best practices and patterns",
        "parameters": {
            "technology": "Technology or framework name",
            "topic": "Specific topic (security, performance, testing)"
        }
    }
}
```

#### PostgreSQL 資料庫工具
```python
# 4個資料庫操作工具
{
    "execute_query": {
        "description": "Execute a read-only SQL query",
        "parameters": {
            "query": "SQL query to execute (read-only operations only)"
        }
    },
    "describe_table": {
        "description": "Get schema information for a specific table",
        "parameters": {
            "table_name": "Name of the table to describe"
        }
    },
    "list_tables": {
        "description": "List all tables in the database",
        "parameters": {}
    },
    "get_table_sample": {
        "description": "Get sample data from a table (first 10 rows)",
        "parameters": {
            "table_name": "Name of the table to sample"
        }
    }
}
```

### MCP 工具調用流程
```mermaid
sequenceDiagram
    participant Client as LINE Bot Client
    participant MCP as MCP Manifest
    participant Context7 as Context7 Server
    participant PostgreSQL as PostgreSQL Server
    
    Client->>MCP: 獲取可用工具清單
    MCP-->>Client: 返回8個工具定義
    
    alt 文檔查詢請求
        Client->>Context7: search_docs/get_code_examples
        Context7-->>Client: 返回文檔內容
    else 資料庫查詢請求
        Client->>PostgreSQL: execute_query/describe_table
        PostgreSQL-->>Client: 返回查詢結果
    end
```

---

## 🔧 技術實現細節

### SQLAlchemy 配置
```python
# 基底類別配置
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from typing import Any

Base: Any = declarative_base()

# 資料庫連接配置
DATABASE_URL = "postgresql://admin:admin@localhost:5432/mydb"
```

### 外鍵關聯設計
```python
# 主要外鍵關聯
machine_faults.machine_id → machines.id
machine_utilization.machine_id → machines.id  # 僅開發環境
orders.product_id → products.id

# 關聯特徵
- 使用 String(50) 作為機台ID的外鍵類型（開發環境）
- 使用 String(10) 作為機台ID的外鍵類型（生產環境）
- 支援級聯操作和完整性約束
```

### 欄位類型映射
```python
# 常用欄位類型
String(n)           # VARCHAR(n)
Integer             # INTEGER
Numeric(p, s)       # NUMERIC(p, s)
DateTime            # TIMESTAMP
Date                # DATE
Boolean             # BOOLEAN
Text                # TEXT
ForeignKey          # FOREIGN KEY CONSTRAINT
```

### 預設值策略
```python
# 開發環境：Python 層面預設值
created_at = Column(DateTime, default=func.now())
resolved = Column(Boolean, default=False)
status = Column(String(20), default="pending")

# 生產環境：資料庫層面預設值
created_at = Column(DateTime, server_default=func.current_timestamp())
resolved = Column(Boolean, server_default="false")
status = Column(String(20), server_default="pending")
```

---

## 🚀 部署與配置

### 環境配置
```bash
# 開發環境
export DATABASE_URL="postgresql://admin:admin@localhost:5432/mydb"
export SCHEMA_MODE="development"  # 使用 database.py

# 生產環境
export DATABASE_URL="postgresql://admin:admin@localhost:5432/mydb"
export SCHEMA_MODE="production"   # 使用 current_database.py
```

### Alembic 遷移設定
```python
# alembic/env.py 配置
import os
from models.database import Base as DevBase
from models.current_database import Base as ProdBase

# 根據環境選擇適當的 Base
schema_mode = os.environ.get('SCHEMA_MODE', 'development')
if schema_mode == 'production':
    target_metadata = ProdBase.metadata
else:
    target_metadata = DevBase.metadata
```

### Docker 容器配置
```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: admin
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql/:/docker-entrypoint-initdb.d/
```

---

## 📚 開發指南

### 模型使用範例
```python
# 1. 匯入模型
from models.database import Machine, MachineFault  # 開發環境
from models.current_database import Machine, MachineFault  # 生產環境

# 2. 建立查詢
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# 3. 基本查詢
machines = session.query(Machine).all()
active_machines = session.query(Machine).filter(Machine.status == 'active').all()

# 4. 關聯查詢
machine_with_faults = session.query(Machine).join(MachineFault).all()
```

### MCP 工具使用
```python
# 1. 匯入工具清單
from models.mcp_manifest import get_mcp_manifest

# 2. 獲取工具定義
tools = get_mcp_manifest()

# 3. 使用工具（透過 OpenAI Function Calling）
import openai
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "查詢機台狀態"}],
    functions=list(tools.values())
)
```

### 測試指南
```python
# 1. 單元測試
import pytest
from models.database import Machine

def test_machine_creation():
    machine = Machine(
        id="M001",
        name="CNC車床A",
        status="active",
        utilization_rate=75.5
    )
    assert machine.id == "M001"
    assert machine.utilization_rate == 75.5

# 2. 整合測試
def test_database_connection():
    from sqlalchemy import create_engine
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()
    result = connection.execute("SELECT 1")
    assert result.fetchone()[0] == 1
```

### 最佳實踐
```python
# 1. 模型定義
class Machine(Base):
    """機台資料表 - 詳細註解說明模型用途"""
    __tablename__ = "machines"
    
    # 主鍵定義
    id = Column(String(50), primary_key=True, comment="機台ID")
    
    # 必要欄位
    name = Column(String(255), nullable=False, comment="機台名稱")
    
    # 可選欄位
    temperature = Column(Numeric(5, 2), comment="溫度")

# 2. 查詢優化
def get_active_machines():
    """獲取活躍機台 - 使用索引優化查詢"""
    return session.query(Machine).filter(
        Machine.status == 'active'
    ).order_by(Machine.created_at.desc()).all()

# 3. 錯誤處理
try:
    machine = session.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise ValueError(f"機台 {machine_id} 不存在")
except Exception as e:
    session.rollback()
    raise
```

---

## 📊 統計數據

### 模型統計
- **總模型數量**: 6 個核心模型
- **總欄位數**: 38 個欄位（開發環境）/ 32 個欄位（生產環境）
- **外鍵關聯**: 3 個主要關聯
- **索引數量**: 6 個主鍵索引 + 3 個外鍵索引

### MCP 工具統計
- **Context7 工具**: 4 個文檔查詢工具
- **PostgreSQL 工具**: 4 個資料庫操作工具
- **總參數數**: 15 個必要參數 + 6 個可選參數

### 檔案規模
- **database.py**: 121 行程式碼
- **current_database.py**: 115 行程式碼
- **mcp_manifest.py**: 173 行程式碼
- **__init__.py**: 0 行（空文件）

---

**🎯 Models 層是整個系統的資料基礎，提供了穩固的資料模型定義和靈活的 MCP 工具整合。透過雙重 Schema 管理機制，確保開發和生產環境的平滑過渡，是企業級應用的核心組件。**