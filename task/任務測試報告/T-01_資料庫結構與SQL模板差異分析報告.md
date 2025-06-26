# T-01 資料庫結構與SQL模板差異分析報告

## 📋 分析目標
詳細檢查實際資料庫結構與 SQL 模板的欄位名稱差異，找出導致 `column m.machine_id does not exist` 錯誤的具體原因。

## 🗄️ 實際資料庫結構

### 1. `machines` 表結構
```sql
CREATE TABLE machines (
    id               VARCHAR(10) PRIMARY KEY,     -- ⚠️ 注意：不是 machine_id
    name             VARCHAR(100) NOT NULL,       -- ⚠️ 注意：不是 machine_name  
    status           VARCHAR(20) NOT NULL,
    temperature      NUMERIC(5,2),
    utilization_rate NUMERIC(5,2),
    last_maintenance DATE,
    location         VARCHAR(50),                 -- ⚠️ 注意：不是 department
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. `machine_utilization` 表結構
```sql
CREATE TABLE machine_utilization (
    id               INTEGER PRIMARY KEY,
    machine_id       VARCHAR(10),                 -- ✅ 正確：關聯到 machines.id
    date             DATE NOT NULL,
    utilization_rate NUMERIC(5,2),
    efficiency_rate  NUMERIC(5,2),
    good_parts       INTEGER DEFAULT 0,
    defective_parts  INTEGER DEFAULT 0,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (machine_id) REFERENCES machines(id)
);
```

### 3. `machine_faults` 表結構
```sql
CREATE TABLE machine_faults (
    fault_id        INTEGER PRIMARY KEY,
    machine_id      VARCHAR(50) NOT NULL,        -- ✅ 正確：關聯到 machines.id
    fault_type      VARCHAR(100) NOT NULL,
    severity        VARCHAR(20) NOT NULL,
    fault_date      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description     TEXT,
    resolved        BOOLEAN DEFAULT FALSE,
    resolution_date TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (machine_id) REFERENCES machines(id)
);
```

## 🔍 SQL 模板錯誤分析

### 1. `production_stats` 模板 ❌ **嚴重錯誤**

**當前錯誤模板**：
```sql
SELECT 
    m.department,                                -- ❌ 應該是 m.location
    COUNT(DISTINCT m.machine_id) as machine_count, -- ❌ 應該是 m.id
    COALESCE(AVG(u.utilization_rate), 0) as avg_utilization,
    COALESCE(AVG(u.efficiency_rate), 0) as avg_efficiency,
    COALESCE(SUM(u.good_parts), 0) as total_good_parts,
    COALESCE(SUM(u.defective_parts), 0) as total_defective_parts
FROM machines m
LEFT JOIN machine_utilization u ON m.machine_id = u.machine_id  -- ❌ 應該是 m.id = u.machine_id
    AND u.date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY m.department                            -- ❌ 應該是 m.location
ORDER BY avg_utilization DESC
```

**錯誤原因**：
1. `m.machine_id` 不存在，應該是 `m.id`
2. `m.department` 不存在，應該是 `m.location`  
3. JOIN 條件錯誤：`m.machine_id = u.machine_id` 應該是 `m.id = u.machine_id`

### 2. `all_machines` 模板 ❌ **部分錯誤**

**當前錯誤模板**：
```sql
SELECT 
    m.machine_id,                                -- ❌ 應該是 m.id
    m.machine_name,                              -- ❌ 應該是 m.name
    m.department,                                -- ❌ 應該是 m.location
    COALESCE(AVG(u.utilization_rate), 0) as avg_utilization,
    COALESCE(AVG(u.efficiency_rate), 0) as avg_efficiency,
    MAX(u.date) as last_record_date
FROM machines m
LEFT JOIN machine_utilization u ON m.machine_id = u.machine_id  -- ❌ JOIN 條件錯誤
    AND u.date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY m.machine_id, m.machine_name, m.department  -- ❌ 全部錯誤
ORDER BY m.machine_id                            -- ❌ 應該是 m.id
```

### 3. `specific_machine` 模板 ⚠️ **混合錯誤**

**當前模板**：
```sql
SELECT 
    m.id as machine_id,                          -- ✅ 正確
    m.name as machine_name,                      -- ✅ 正確
    m.location as department,                    -- ✅ 正確
    m.utilization_rate,
    m.status,
    m.temperature,
    COALESCE(AVG(u.utilization_rate), 0) as avg_utilization,
    COALESCE(AVG(u.efficiency_rate), 0) as avg_efficiency,
    COALESCE(SUM(u.good_parts), 0) as total_good_parts,
    COALESCE(SUM(u.defective_parts), 0) as total_defective_parts,
    MAX(u.date) as last_record_date
FROM machines m
LEFT JOIN machine_utilization u ON m.id = u.machine_id  -- ✅ 正確
WHERE m.id = '{machine_id}'                     -- ✅ 正確
GROUP BY m.id, m.name, m.location, m.utilization_rate, m.status, m.temperature
```

**狀態**：✅ **此模板已正確** - 這解釋了為什麼 M001 查詢能正常工作！

### 4. `fault_analysis` 模板 ⚠️ **資料類型問題**

**當前模板**：
```sql
SELECT 
    COUNT(*) as total_faults,
    fault_type,
    severity,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage
FROM machine_faults 
WHERE fault_date >= CURRENT_DATE - INTERVAL '{days} days'
GROUP BY fault_type, severity
ORDER BY COUNT(*) DESC
```

**問題**：在 `_format_fault_analysis` 函數中出現類型轉換錯誤：
```python
total_faults = sum(row.get("total_faults", 0) for row in data)  # ❌ 字串 + 整數錯誤
```

## 📊 欄位映射對照表

| SQL模板中的欄位 | 實際資料庫欄位 | 狀態 | 影響的模板 |
|---|---|---|---|
| `m.machine_id` | `m.id` | ❌ 錯誤 | `production_stats`, `all_machines` |
| `m.machine_name` | `m.name` | ❌ 錯誤 | `all_machines` |
| `m.department` | `m.location` | ❌ 錯誤 | `production_stats`, `all_machines` |
| `u.machine_id` | `u.machine_id` | ✅ 正確 | 所有模板 |
| `JOIN ON m.machine_id = u.machine_id` | `JOIN ON m.id = u.machine_id` | ❌ 錯誤 | `production_stats`, `all_machines` |

## 🎯 修復優先級

### Critical 級別 (立即修復)
1. **`production_stats` 模板** - 完全無法執行
2. **`all_machines` 模板** - 完全無法執行

### High 級別 (高優先級)
3. **`fault_analysis` 資料類型處理** - 查詢成功但格式化失敗

### Medium 級別 (已正常)
4. **`specific_machine` 模板** - ✅ 已正確，無需修復

## 🔧 修復策略

### 策略 1: 直接修正 SQL 模板
**優點**：直接解決問題，修改範圍小
**缺點**：需要修改多個文件

### 策略 2: 建立資料庫視圖
**優點**：不需修改應用程式代碼
**缺點**：增加資料庫複雜度

### 策略 3: 建立欄位別名映射
**優點**：統一處理，易於維護
**缺點**：需要較大的架構調整

## 📋 建議修復順序

1. **第一階段**：修復 `production_stats` 模板（最嚴重）
2. **第二階段**：修復 `all_machines` 模板  
3. **第三階段**：修復 `fault_analysis` 資料類型處理
4. **第四階段**：驗證 `specific_machine` 模板不受影響

## 🧪 測試驗證計劃

### 單元測試
```sql
-- 測試 1: 驗證欄位存在性
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'machines' AND column_name IN ('id', 'name', 'location');

-- 測試 2: 驗證 JOIN 關係
SELECT COUNT(*) FROM machines m 
LEFT JOIN machine_utilization u ON m.id = u.machine_id;

-- 測試 3: 驗證資料類型
SELECT pg_typeof(COUNT(*)) FROM machine_faults;
```

### 整合測試
使用修復後的模板執行實際查詢，確保返回正確結果。

## 💡 結論

**根本原因確認**：
1. ✅ M001 查詢正常是因為 `specific_machine` 模板已經使用正確的欄位名稱
2. ❌ 其他查詢失敗是因為 `production_stats` 和 `all_machines` 模板使用了錯誤的欄位名稱
3. ⚠️ `fault_analysis` 查詢成功但資料處理時發生類型轉換錯誤

**修復可行性**：✅ 高度可行，問題明確且解決方案直接

**影響評估**：✅ 修復不會影響現有正常功能，只會讓失敗的功能變成正常 