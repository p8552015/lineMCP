#!/bin/bash

echo "🗃️ 啟動 SQLite MCP 服務..."

# 進入 SQLite MCP 目錄
cd "$(dirname "$0")/../apps/servers/src/sqlite"

# 檢查 test.db 是否存在，如果不存在則創建一個簡單的測試資料庫
if [ ! -f "test.db" ]; then
    echo "📝 創建測試資料庫..."
    sqlite3 test.db <<EOF
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    category TEXT,
    stock INTEGER DEFAULT 0
);

-- 插入測試資料
INSERT INTO users (name, email) VALUES 
    ('Alice Johnson', 'alice@example.com'),
    ('Bob Smith', 'bob@example.com'),
    ('Carol Davis', 'carol@example.com');

INSERT INTO products (name, price, category, stock) VALUES 
    ('筆記本電腦', 999.99, '電子產品', 10),
    ('無線滑鼠', 29.99, '電子產品', 50),
    ('辦公椅', 199.99, '家具', 5),
    ('書桌', 299.99, '家具', 3);
EOF
    echo "✅ 測試資料庫創建完成"
fi

# 檢查是否安裝了 uv
if ! command -v uv &> /dev/null; then
    echo "❌ uv 未安裝，請先安裝 uv"
    echo "安裝命令: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# 使用 uv 運行 SQLite MCP 服務
echo "🚀 啟動 SQLite MCP 服務..."
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# 啟動 SQLite MCP 服務並在背景運行
echo "資料庫路徑: $(pwd)/test.db"
exec uv run python -m mcp_server_sqlite.server "$(pwd)/test.db"