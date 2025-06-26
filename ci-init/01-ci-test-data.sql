-- CI 專用的 PostgreSQL 測試數據初始化
-- 針對測試驅動 CI 管道 (T-01 到 T-05) 優化
-- 輕量級數據結構，專注於核心測試需求

-- ============================================
-- T-01 & T-05: PostgreSQL MCP 和 M001 E2E 測試數據
-- ============================================

-- 創建機台表（核心測試數據）
CREATE TABLE IF NOT EXISTS machines (
    id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    temperature DECIMAL(5,2),
    utilization_rate DECIMAL(5,2),
    last_maintenance DATE,
    location VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入 M001 關鍵測試數據（T-05 E2E 測試需要）
INSERT INTO machines (id, name, status, temperature, utilization_rate, last_maintenance, location) VALUES
('M001', 'CNC車床A', '運行中', 45.5, 74.4, '2024-06-01', '工廠A-1樓'),
('M002', 'CNC車床B', '待機中', 25.0, 45.2, '2024-06-15', '工廠A-2樓'),
('M003', '銑床A', '維護中', 35.0, 0.0, '2024-06-20', '工廠B-1樓')
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    status = EXCLUDED.status,
    temperature = EXCLUDED.temperature,
    utilization_rate = EXCLUDED.utilization_rate,
    last_maintenance = EXCLUDED.last_maintenance,
    location = EXCLUDED.location;

-- 創建機台使用率歷史記錄表（T-05 E2E 查詢測試）
CREATE TABLE IF NOT EXISTS machine_utilization (
    id SERIAL PRIMARY KEY,
    machine_id VARCHAR(10) REFERENCES machines(id),
    date DATE NOT NULL,
    utilization_rate DECIMAL(5,2),
    efficiency_rate DECIMAL(5,2),
    good_parts INTEGER DEFAULT 0,
    defective_parts INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入 M001 近期使用率數據（支援趨勢查詢測試）
INSERT INTO machine_utilization (machine_id, date, utilization_rate, efficiency_rate, good_parts, defective_parts) VALUES
-- M001 最近7天數據（T-05 E2E 測試驗證）
('M001', CURRENT_DATE - INTERVAL '6 days', 75.5, 92.3, 1200, 25),
('M001', CURRENT_DATE - INTERVAL '5 days', 78.2, 89.1, 1180, 30),
('M001', CURRENT_DATE - INTERVAL '4 days', 72.8, 91.5, 1150, 20),
('M001', CURRENT_DATE - INTERVAL '3 days', 80.1, 88.7, 1220, 35),
('M001', CURRENT_DATE - INTERVAL '2 days', 74.2, 90.2, 1190, 28),
('M001', CURRENT_DATE - INTERVAL '1 day', 76.8, 93.1, 1210, 22),
('M001', CURRENT_DATE, 74.4, 91.8, 1175, 24),

-- M002 測試數據
('M002', CURRENT_DATE - INTERVAL '3 days', 45.3, 85.2, 850, 45),
('M002', CURRENT_DATE - INTERVAL '2 days', 44.8, 82.8, 820, 50),
('M002', CURRENT_DATE - INTERVAL '1 day', 45.5, 84.1, 840, 42),
('M002', CURRENT_DATE, 45.2, 83.5, 830, 47),

-- M003 維護中數據
('M003', CURRENT_DATE - INTERVAL '7 days', 68.5, 87.2, 950, 38),
('M003', CURRENT_DATE - INTERVAL '6 days', 65.9, 86.1, 920, 42),
('M003', CURRENT_DATE - INTERVAL '5 days', 0.0, 0.0, 0, 0),
('M003', CURRENT_DATE - INTERVAL '4 days', 0.0, 0.0, 0, 0),
('M003', CURRENT_DATE - INTERVAL '3 days', 0.0, 0.0, 0, 0),
('M003', CURRENT_DATE - INTERVAL '2 days', 0.0, 0.0, 0, 0),
('M003', CURRENT_DATE - INTERVAL '1 day', 0.0, 0.0, 0, 0),
('M003', CURRENT_DATE, 0.0, 0.0, 0, 0)
ON CONFLICT DO NOTHING;

-- ============================================
-- T-01: PostgreSQL MCP 連接測試支援表
-- ============================================

-- 簡化的員工表（測試基本查詢功能）
CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(50),
    salary DECIMAL(10,2),
    hire_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 最小測試數據集
INSERT INTO employees (name, department, salary, hire_date) VALUES
('張測試', '工程部', 75000.00, '2023-01-15'),
('李測試', '銷售部', 65000.00, '2023-02-20'),
('王測試', '人資部', 70000.00, '2023-03-10')
ON CONFLICT DO NOTHING;

-- ============================================
-- T-05: M001 E2E 測試專用視圖
-- ============================================

-- M001 機台性能摘要視圖（支援自然語言查詢）
CREATE OR REPLACE VIEW m001_performance_summary AS
SELECT 
    m.id as machine_id,
    m.name as machine_name,
    m.status,
    m.temperature,
    m.utilization_rate as current_utilization,
    m.location,
    COALESCE(AVG(u.utilization_rate), 0) as avg_utilization_7days,
    COALESCE(AVG(u.efficiency_rate), 0) as avg_efficiency_7days,
    COALESCE(SUM(u.good_parts), 0) as total_good_parts_7days,
    COALESCE(SUM(u.defective_parts), 0) as total_defective_parts_7days,
    MAX(u.date) as last_record_date,
    m.last_maintenance
FROM machines m
LEFT JOIN machine_utilization u ON m.id = u.machine_id 
    AND u.date >= CURRENT_DATE - INTERVAL '7 days'
WHERE m.id = 'M001'
GROUP BY m.id, m.name, m.status, m.temperature, m.utilization_rate, m.location, m.last_maintenance;

-- 機台狀態概覽視圖（支援多機台查詢測試）
CREATE OR REPLACE VIEW machine_status_overview AS
SELECT 
    id as machine_id,
    name as machine_name,
    status,
    utilization_rate,
    temperature,
    location,
    CASE 
        WHEN status = '運行中' THEN '🟢'
        WHEN status = '待機中' THEN '🟡'
        WHEN status = '維護中' THEN '🔴'
        ELSE '⚪'
    END as status_icon,
    CASE 
        WHEN utilization_rate >= 80 THEN '高效'
        WHEN utilization_rate >= 60 THEN '正常'
        WHEN utilization_rate >= 30 THEN '低效'
        ELSE '停機'
    END as performance_level
FROM machines
ORDER BY utilization_rate DESC;

-- ============================================
-- T-01: PostgreSQL MCP 連接測試索引
-- ============================================

-- 基本索引（提升 CI 測試查詢速度）
CREATE INDEX IF NOT EXISTS idx_machines_id ON machines(id);
CREATE INDEX IF NOT EXISTS idx_machines_status ON machines(status);
CREATE INDEX IF NOT EXISTS idx_machine_utilization_machine_id ON machine_utilization(machine_id);
CREATE INDEX IF NOT EXISTS idx_machine_utilization_date ON machine_utilization(date);
CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department);

-- ============================================
-- CI 測試驗證查詢
-- ============================================

-- 驗證 M001 數據完整性（T-05 E2E 測試預檢）
DO $$
DECLARE
    m001_count INTEGER;
    m001_utilization DECIMAL(5,2);
    hist_count INTEGER;
BEGIN
    -- 檢查 M001 機台是否存在
    SELECT COUNT(*), MAX(utilization_rate) INTO m001_count, m001_utilization
    FROM machines WHERE id = 'M001';
    
    IF m001_count = 0 THEN
        RAISE EXCEPTION '❌ M001 機台數據缺失！CI 測試無法進行。';
    END IF;
    
    -- 檢查 M001 歷史數據
    SELECT COUNT(*) INTO hist_count
    FROM machine_utilization WHERE machine_id = 'M001';
    
    IF hist_count < 7 THEN
        RAISE WARNING '⚠️ M001 歷史數據不足（%），部分測試可能受影響。', hist_count;
    END IF;
    
    -- 顯示測試環境狀態
    RAISE NOTICE '✅ CI 測試數據初始化完成！';
    RAISE NOTICE '🎯 M001 機台: CNC車床A，當前稼動率: %%%', m001_utilization;
    RAISE NOTICE '📊 歷史數據記錄: % 筆', hist_count;
    RAISE NOTICE '🧪 支援測試: T-01 PostgreSQL MCP 連接, T-05 M001 E2E';
    
    -- 驗證關鍵查詢能力
    PERFORM * FROM m001_performance_summary;
    RAISE NOTICE '👁️ M001 性能摘要視圖: 可用';
    
    PERFORM * FROM machine_status_overview;
    RAISE NOTICE '📋 機台狀態概覽視圖: 可用';
    
END $$;

-- ============================================
-- CI 性能優化設定
-- ============================================

-- 分析表格統計資訊（提升查詢計劃）
ANALYZE machines;
ANALYZE machine_utilization;
ANALYZE employees;

-- CI 測試完成標記
CREATE TABLE IF NOT EXISTS ci_test_metadata (
    key VARCHAR(50) PRIMARY KEY,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO ci_test_metadata (key, value) VALUES 
('ci_init_version', '1.0.0'),
('ci_init_date', CURRENT_TIMESTAMP::TEXT),
('supported_tests', 'T-01,T-05'),
('m001_ready', 'true'),
('data_source', 'ci-test-driven')
ON CONFLICT (key) DO UPDATE SET 
    value = EXCLUDED.value,
    created_at = CURRENT_TIMESTAMP;