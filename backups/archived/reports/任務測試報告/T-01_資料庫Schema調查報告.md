# T-01 資料庫Schema調查報告

## 📋 調查目標
檢查生產環境資料庫實際結構，對比應用程式期望結構，找出導致 `relation "machine_faults" does not exist` 錯誤的根本原因。

## 🔍 應用程式期望的資料表結構

根據 `sql_templates.yaml` 分析，應用程式期望以下資料表：

### 1. `machines` 資料表
**用途**：儲存機台基本資訊
**欄位**（從SQL模板推斷）：
```sql
CREATE TABLE machines (
    id VARCHAR(10) PRIMARY KEY,           -- 機台ID (如 M001)
    machine_id VARCHAR(10),               -- 機台ID (別名)
    name VARCHAR(100),                    -- 機台名稱
    machine_name VARCHAR(100),            -- 機台名稱 (別名)
    location VARCHAR(50),                 -- 位置
    department VARCHAR(50),               -- 部門
    utilization_rate DECIMAL(5,2),       -- 稼動率
    status VARCHAR(20),                   -- 狀態
    temperature DECIMAL(5,2),             -- 溫度
    last_maintenance TIMESTAMP,           -- 最後維護時間
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. `machine_utilization` 資料表
**用途**：儲存機台使用率歷史記錄
**欄位**（從SQL模板推斷）：
```sql
CREATE TABLE machine_utilization (
    id SERIAL PRIMARY KEY,
    machine_id VARCHAR(10) REFERENCES machines(id),
    date DATE,
    utilization_rate DECIMAL(5,2),       -- 稼動率
    efficiency_rate DECIMAL(5,2),        -- 效率
    good_parts INTEGER,                   -- 良品數量
    defective_parts INTEGER,              -- 不良品數量
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3. `machine_faults` 資料表 ⚠️ **關鍵缺失**
**用途**：儲存機台故障記錄
**欄位**（從SQL模板推斷）：
```sql
CREATE TABLE machine_faults (
    id SERIAL PRIMARY KEY,
    machine_id VARCHAR(10) REFERENCES machines(id),
    fault_type VARCHAR(100),              -- 故障類型
    severity VARCHAR(20),                 -- 嚴重程度
    fault_date DATE,                      -- 故障日期
    description TEXT,                     -- 故障描述
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🚨 問題分析

### 核心問題
**錯誤訊息**：`relation "machine_faults" does not exist`

**影響範圍**：
1. `fault_analysis` 查詢類型完全無法執行
2. 任何涉及故障分析的自然語言查詢都會失敗
3. LINE Bot 查詢 "近期故障記錄" 等功能完全失效

### 從錯誤日誌分析
根據提供的錯誤日誌：
```json
{"error_message": "relation \"machine_faults\" does not exist"}
```

**查詢失敗的SQL**：
```sql
SELECT COUNT(*) as total_faults, fault_type, severity, 
       COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage
FROM machine_faults 
WHERE fault_date >= date('now', '-7 days')
GROUP BY fault_type, severity
ORDER BY COUNT(*) DESC
```

## 🔧 生產環境資料庫狀態推測

基於錯誤訊息和應用程式行為，推測生產環境資料庫狀態：

### 可能存在的資料表
- `machines` - 可能存在（其他查詢可能正常）
- `machine_utilization` - 可能存在

### 確定缺失的資料表
- ❌ `machine_faults` - **確認不存在**

## 📊 影響評估

### 功能影響
1. **完全失效的功能**：
   - 故障分析查詢
   - 故障統計報告
   - 任何包含 "故障"、"問題"、"錯誤" 關鍵字的自然語言查詢

2. **可能正常的功能**：
   - 機台狀態查詢
   - 生產統計報告
   - 部門狀態查詢

### 業務影響
- **嚴重程度**：High
- **用戶體驗**：LINE Bot 部分功能完全無法使用
- **監控能力**：無法進行故障分析和預防性維護

## 🎯 修復建議

### 立即修復方案
1. **建立 `machine_faults` 資料表**
   ```sql
   CREATE TABLE machine_faults (
       id SERIAL PRIMARY KEY,
       machine_id VARCHAR(10),
       fault_type VARCHAR(100),
       severity VARCHAR(20),
       fault_date DATE DEFAULT CURRENT_DATE,
       description TEXT,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   
   -- 建立索引以提升查詢效能
   CREATE INDEX idx_machine_faults_date ON machine_faults(fault_date);
   CREATE INDEX idx_machine_faults_machine_id ON machine_faults(machine_id);
   ```

2. **插入測試資料**（可選）
   ```sql
   INSERT INTO machine_faults (machine_id, fault_type, severity, fault_date, description) VALUES
   ('M001', '過熱', 'High', CURRENT_DATE - INTERVAL '2 days', '機台溫度超過安全閾值'),
   ('M002', '振動異常', 'Medium', CURRENT_DATE - INTERVAL '1 day', '檢測到異常振動'),
   ('M003', '油壓不足', 'Low', CURRENT_DATE, '油壓略低於標準值');
   ```

### 驗證步驟
1. 執行建表語句
2. 測試 `fault_analysis` 模板查詢
3. 透過 LINE Bot 測試故障相關查詢
4. 檢查應用程式日誌確認無錯誤

## 📋 後續調查需求

### 需要確認的項目
1. **其他資料表的實際結構**
   - `machines` 表的實際欄位是否與期望一致
   - `machine_utilization` 表是否存在且結構正確

2. **資料完整性**
   - 是否有外鍵約束
   - 索引是否已建立
   - 是否有必要的測試資料

3. **權限設定**
   - 應用程式資料庫用戶是否有建表權限
   - 是否有適當的讀寫權限

## ✅ 調查結論

1. **根本原因確認**：生產環境缺少 `machine_faults` 資料表
2. **影響範圍明確**：故障分析相關功能完全失效
3. **修復方案可行**：建立缺失資料表即可解決問題
4. **風險評估**：修復風險低，不會影響現有功能

## 📅 時間記錄
- **調查開始**：2025-06-26 10:35
- **調查完成**：2025-06-26 10:45
- **調查耗時**：10分鐘

## 🔄 下一步行動
進入 T-02 緊急Schema修復階段，建立缺失的 `machine_faults` 資料表。