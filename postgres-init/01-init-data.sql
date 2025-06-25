-- 初始化 PostgreSQL 數據庫
-- 創建示例表格和數據，用於 MCP 測試

-- 創建員工表
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(50),
    salary DECIMAL(10,2),
    hire_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入員工示例數據
INSERT INTO employees (name, department, salary, hire_date) VALUES
('張三', '工程部', 75000.00, '2023-01-15'),
('李四', '銷售部', 65000.00, '2023-02-20'),
('王五', '人資部', 70000.00, '2023-03-10'),
('趙六', '財務部', 72000.00, '2023-04-05'),
('錢七', '工程部', 80000.00, '2023-05-12'),
('孫八', '銷售部', 68000.00, '2023-06-18'),
('周九', '工程部', 82000.00, '2023-07-22'),
('吳十', '市場部', 71000.00, '2023-08-30');

-- 創建產品表
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    price DECIMAL(8,2),
    stock INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入產品數據
INSERT INTO products (name, category, price, stock) VALUES
('筆記本電腦 MacBook Pro', '電子產品', 89000.00, 25),
('智能手機 iPhone 15', '電子產品', 35000.00, 50),
('辦公桌 IKEA', '家具', 12000.00, 15),
('無線耳機 AirPods', '電子產品', 8000.00, 100),
('辦公椅 Herman Miller', '家具', 35000.00, 8),
('平板電腦 iPad Pro', '電子產品', 28000.00, 30),
('智能手錶 Apple Watch', '電子產品', 12000.00, 40),
('書桌燈', '家具', 2500.00, 60);

-- 創建訂單表
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL DEFAULT 1,
    total_amount DECIMAL(10,2),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending'
);

-- 插入訂單數據
INSERT INTO orders (customer_name, product_id, quantity, total_amount, status) VALUES
('客戶A', 1, 1, 89000.00, 'completed'),
('客戶B', 2, 2, 70000.00, 'completed'),
('客戶C', 4, 3, 24000.00, 'pending'),
('客戶D', 3, 1, 12000.00, 'shipped'),
('客戶E', 6, 1, 28000.00, 'completed'),
('客戶F', 8, 2, 5000.00, 'pending');

-- 創建機台表（對應原有的 SQLite 數據）
CREATE TABLE machines (
    id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    temperature DECIMAL(5,2),
    utilization_rate DECIMAL(5,2),
    last_maintenance DATE,
    location VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入機台數據
INSERT INTO machines (id, name, status, temperature, utilization_rate, last_maintenance, location) VALUES
('M001', 'CNC車床A', '運行中', 45.5, 74.2, '2024-06-01', '工廠A-1樓'),
('M002', '包裝機1號', '停機', 25.0, 0.0, '2024-06-15', '工廠A-2樓'),
('M003', '焊接機3號', '維護中', 35.0, 0.0, '2024-06-20', '工廠B-1樓'),
('M004', '切割機B', '運行中', 52.3, 68.9, '2024-05-28', '工廠A-1樓'),
('M005', '組裝線C', '運行中', 28.5, 89.1, '2024-06-10', '工廠B-2樓');

-- 創建一些視圖方便查詢
CREATE VIEW employee_summary AS
SELECT 
    department,
    COUNT(*) as employee_count,
    AVG(salary) as avg_salary,
    MAX(salary) as max_salary,
    MIN(salary) as min_salary
FROM employees 
GROUP BY department;

CREATE VIEW product_inventory AS
SELECT 
    category,
    COUNT(*) as product_count,
    SUM(stock) as total_stock,
    AVG(price) as avg_price
FROM products 
GROUP BY category;

CREATE VIEW machine_status_summary AS
SELECT 
    status,
    COUNT(*) as machine_count,
    AVG(utilization_rate) as avg_utilization
FROM machines 
GROUP BY status;

-- 創建索引提升查詢性能
CREATE INDEX idx_employees_department ON employees(department);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_machines_status ON machines(status);

-- 顯示初始化完成信息
DO $$
BEGIN
    RAISE NOTICE '✅ PostgreSQL 數據庫初始化完成！';
    RAISE NOTICE '📊 已創建表格：employees, products, orders, machines';
    RAISE NOTICE '👁️ 已創建視圖：employee_summary, product_inventory, machine_status_summary';
    RAISE NOTICE '🔍 已創建索引：department, category, status';
END $$;