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

-- 創建機台使用率歷史記錄表
CREATE TABLE machine_utilization (
    id SERIAL PRIMARY KEY,
    machine_id VARCHAR(10) REFERENCES machines(id),
    date DATE NOT NULL,
    utilization_rate DECIMAL(5,2),
    efficiency_rate DECIMAL(5,2),
    good_parts INTEGER DEFAULT 0,
    defective_parts INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入機台使用率歷史數據
INSERT INTO machine_utilization (machine_id, date, utilization_rate, efficiency_rate, good_parts, defective_parts) VALUES
-- M001 近7天數據
('M001', CURRENT_DATE - INTERVAL '6 days', 75.5, 92.3, 1200, 25),
('M001', CURRENT_DATE - INTERVAL '5 days', 78.2, 89.1, 1180, 30),
('M001', CURRENT_DATE - INTERVAL '4 days', 72.8, 91.5, 1150, 20),
('M001', CURRENT_DATE - INTERVAL '3 days', 80.1, 88.7, 1220, 35),
('M001', CURRENT_DATE - INTERVAL '2 days', 74.2, 90.2, 1190, 28),
('M001', CURRENT_DATE - INTERVAL '1 day', 76.8, 93.1, 1210, 22),
('M001', CURRENT_DATE, 74.2, 91.8, 1175, 24),

-- M002 近7天數據（停機狀態）
('M002', CURRENT_DATE - INTERVAL '6 days', 65.3, 85.2, 850, 45),
('M002', CURRENT_DATE - INTERVAL '5 days', 62.1, 82.8, 820, 50),
('M002', CURRENT_DATE - INTERVAL '4 days', 0.0, 0.0, 0, 0),
('M002', CURRENT_DATE - INTERVAL '3 days', 0.0, 0.0, 0, 0),
('M002', CURRENT_DATE - INTERVAL '2 days', 0.0, 0.0, 0, 0),
('M002', CURRENT_DATE - INTERVAL '1 day', 0.0, 0.0, 0, 0),
('M002', CURRENT_DATE, 0.0, 0.0, 0, 0),

-- M004 近7天數據
('M004', CURRENT_DATE - INTERVAL '6 days', 70.2, 87.5, 950, 38),
('M004', CURRENT_DATE - INTERVAL '5 days', 68.9, 86.2, 920, 42),
('M004', CURRENT_DATE - INTERVAL '4 days', 71.5, 88.9, 980, 35),
('M004', CURRENT_DATE - INTERVAL '3 days', 69.8, 85.7, 940, 40),
('M004', CURRENT_DATE - INTERVAL '2 days', 68.9, 87.1, 930, 37),
('M004', CURRENT_DATE - INTERVAL '1 day', 72.3, 89.4, 990, 33),
('M004', CURRENT_DATE, 68.9, 86.8, 945, 39),

-- M005 近7天數據
('M005', CURRENT_DATE - INTERVAL '6 days', 88.5, 94.2, 1580, 15),
('M005', CURRENT_DATE - INTERVAL '5 days', 91.2, 95.8, 1620, 12),
('M005', CURRENT_DATE - INTERVAL '4 days', 87.9, 93.5, 1550, 18),
('M005', CURRENT_DATE - INTERVAL '3 days', 89.7, 96.1, 1590, 10),
('M005', CURRENT_DATE - INTERVAL '2 days', 89.1, 94.8, 1575, 13),
('M005', CURRENT_DATE - INTERVAL '1 day', 90.3, 95.2, 1600, 11),
('M005', CURRENT_DATE, 89.1, 94.5, 1580, 14);

-- 創建機台故障記錄表
CREATE TABLE machine_faults (
    fault_id SERIAL PRIMARY KEY,
    machine_id VARCHAR(10) REFERENCES machines(id),
    fault_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    fault_date DATE NOT NULL DEFAULT CURRENT_DATE,
    description TEXT,
    resolved BOOLEAN DEFAULT FALSE,
    resolution_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入機台故障記錄數據
INSERT INTO machine_faults (machine_id, fault_type, severity, fault_date, description, resolved, resolution_date) VALUES
-- 最近的故障記錄
('M001', '過熱', 'High', CURRENT_DATE - INTERVAL '3 days', 'CNC車床A溫度達到58°C，超過安全閾值55°C', TRUE, CURRENT_DATE - INTERVAL '2 days'),
('M002', '電機故障', 'Critical', CURRENT_DATE - INTERVAL '5 days', '包裝機主電機異常，無法正常運轉', FALSE, NULL),
('M002', '感應器失效', 'Medium', CURRENT_DATE - INTERVAL '4 days', '位置感應器回傳異常數值', FALSE, NULL),
('M003', '油壓不足', 'Medium', CURRENT_DATE - INTERVAL '7 days', '焊接機油壓系統壓力下降至80%', TRUE, CURRENT_DATE - INTERVAL '6 days'),
('M004', '振動異常', 'Low', CURRENT_DATE - INTERVAL '2 days', '切割機運行時檢測到輕微振動', TRUE, CURRENT_DATE - INTERVAL '1 day'),
('M005', '皮帶鬆動', 'Low', CURRENT_DATE - INTERVAL '1 day', '組裝線傳送帶略有鬆動', TRUE, CURRENT_DATE),

-- 歷史故障記錄
('M001', '刀具磨損', 'Medium', CURRENT_DATE - INTERVAL '15 days', 'CNC刀具磨損需要更換', TRUE, CURRENT_DATE - INTERVAL '14 days'),
('M002', '潤滑油不足', 'Low', CURRENT_DATE - INTERVAL '20 days', '包裝機潤滑系統需要補充潤滑油', TRUE, CURRENT_DATE - INTERVAL '19 days'),
('M003', '焊條用盡', 'Low', CURRENT_DATE - INTERVAL '12 days', '焊接機焊條庫存不足', TRUE, CURRENT_DATE - INTERVAL '11 days'),
('M004', '冷卻液溫度高', 'Medium', CURRENT_DATE - INTERVAL '18 days', '切割機冷卻系統效率下降', TRUE, CURRENT_DATE - INTERVAL '16 days'),
('M005', '品檢感應器校準', 'Low', CURRENT_DATE - INTERVAL '25 days', '組裝線品檢感應器需要重新校準', TRUE, CURRENT_DATE - INTERVAL '24 days');

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

-- 創建機台效能摘要視圖
CREATE VIEW machine_performance_summary AS
SELECT 
    m.id as machine_id,
    m.name as machine_name,
    m.status,
    COALESCE(AVG(u.utilization_rate), 0) as avg_utilization,
    COALESCE(AVG(u.efficiency_rate), 0) as avg_efficiency,
    COALESCE(SUM(u.good_parts), 0) as total_good_parts,
    COALESCE(SUM(u.defective_parts), 0) as total_defective_parts,
    MAX(u.date) as last_record_date
FROM machines m
LEFT JOIN machine_utilization u ON m.id = u.machine_id 
    AND u.date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY m.id, m.name, m.status;

-- 創建故障統計視圖
CREATE VIEW fault_statistics AS
SELECT 
    fault_type,
    severity,
    COUNT(*) as fault_count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage,
    COUNT(CASE WHEN resolved = TRUE THEN 1 END) as resolved_count,
    COUNT(CASE WHEN resolved = FALSE THEN 1 END) as unresolved_count
FROM machine_faults 
WHERE fault_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY fault_type, severity
ORDER BY fault_count DESC;

-- 創建索引提升查詢性能
CREATE INDEX idx_employees_department ON employees(department);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_machines_status ON machines(status);

-- 機台相關索引
CREATE INDEX idx_machine_utilization_machine_id ON machine_utilization(machine_id);
CREATE INDEX idx_machine_utilization_date ON machine_utilization(date);
CREATE INDEX idx_machine_utilization_machine_date ON machine_utilization(machine_id, date);

-- 故障記錄索引
CREATE INDEX idx_machine_faults_machine_id ON machine_faults(machine_id);
CREATE INDEX idx_machine_faults_date ON machine_faults(fault_date);
CREATE INDEX idx_machine_faults_severity ON machine_faults(severity);
CREATE INDEX idx_machine_faults_resolved ON machine_faults(resolved);

-- 顯示初始化完成信息
DO $$
BEGIN
    RAISE NOTICE '✅ PostgreSQL 數據庫初始化完成！';
    RAISE NOTICE '📊 已創建表格：employees, products, orders, machines';
    RAISE NOTICE '👁️ 已創建視圖：employee_summary, product_inventory, machine_status_summary';
    RAISE NOTICE '🔍 已創建索引：department, category, status';
END $$;