# LINE MCP 智慧製造監控系統 - 使用者手冊

## 系統概述

LINE MCP 智慧製造監控系統是一個基於 Model Context Protocol (MCP) 的企業級 LINE Bot，整合 AI 模型與 PostgreSQL 工業資料庫，提供智能化的製造業監控與查詢服務。

## 快速開始

### 1. 加入 LINE Bot
- 掃描 QR Code 或搜尋 Bot ID 加入 LINE Bot
- 輸入 `/help` 查看可用指令

### 2. 基本指令
```
/help    - 顯示幫助資訊
/status  - 查看系統狀態  
/info    - 查看系統資訊
/models  - 查看可用的 AI 模型
/tables  - 查看資料庫表格清單
```

## 資料庫查詢指南 🔍

### PostgreSQL 查詢語法

系統使用 PostgreSQL 資料庫，支援標準 SQL 語法。以下是完整的查詢指南：

#### 基本查詢格式
```sql
/sql <PostgreSQL查詢語句>
```

### 常用查詢範例

#### 1. 查看資料庫結構

**查看所有表格：**
```sql
/sql SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'
```

**查看表格欄位結構：**
```sql
/sql SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'machine_data'
```

**查看表格索引：**
```sql
/sql SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'machine_data'
```

#### 2. 機台數據查詢

**查看所有機台清單：**
```sql
/sql SELECT DISTINCT machine_id FROM machine_data ORDER BY machine_id
```

**查詢特定機台的最新數據：**
```sql
/sql SELECT * FROM machine_data WHERE machine_id = 'M001' ORDER BY timestamp DESC LIMIT 10
```

**機台稼動率查詢：**
```sql
/sql SELECT machine_id, AVG(utilization_rate) as avg_utilization FROM machine_data WHERE machine_id = 'M001' GROUP BY machine_id
```

**機台狀態統計：**
```sql
/sql SELECT status, COUNT(*) as count FROM machine_data WHERE machine_id = 'M001' GROUP BY status
```

#### 3. 時間範圍查詢

**最近24小時數據：**
```sql
/sql SELECT * FROM machine_data WHERE timestamp >= NOW() - INTERVAL '1 day' ORDER BY timestamp DESC
```

**特定日期範圍：**
```sql
/sql SELECT * FROM machine_data WHERE timestamp BETWEEN '2024-01-01' AND '2024-01-31'
```

**按小時彙總：**
```sql
/sql SELECT DATE_TRUNC('hour', timestamp) as hour, AVG(utilization_rate) FROM machine_data GROUP BY hour ORDER BY hour
```

#### 4. 故障數據查詢

**查看故障記錄：**
```sql
/sql SELECT * FROM machine_faults WHERE machine_id = 'M001' ORDER BY fault_time DESC
```

**故障統計分析：**
```sql
/sql SELECT fault_type, COUNT(*) as fault_count FROM machine_faults GROUP BY fault_type ORDER BY fault_count DESC
```

**故障嚴重程度分布：**
```sql
/sql SELECT severity, COUNT(*) as count FROM machine_faults GROUP BY severity
```

#### 5. 效能分析查詢

**機台效率排名：**
```sql
/sql SELECT machine_id, AVG(utilization_rate) as avg_rate FROM machine_data GROUP BY machine_id ORDER BY avg_rate DESC
```

**生產力趨勢分析：**
```sql
/sql SELECT DATE(timestamp) as date, AVG(utilization_rate) as daily_avg FROM machine_data WHERE machine_id = 'M001' GROUP BY DATE(timestamp) ORDER BY date
```

### 進階查詢技巧

#### 聯合查詢 (JOIN)
```sql
/sql SELECT md.machine_id, md.utilization_rate, mf.fault_type FROM machine_data md LEFT JOIN machine_faults mf ON md.machine_id = mf.machine_id WHERE md.timestamp >= NOW() - INTERVAL '1 hour'
```

#### 條件過濾
```sql
/sql SELECT * FROM machine_data WHERE utilization_rate > 80 AND status = 'running'
```

#### 數據彙總
```sql
/sql SELECT machine_id, MIN(utilization_rate) as min_rate, MAX(utilization_rate) as max_rate, AVG(utilization_rate) as avg_rate FROM machine_data GROUP BY machine_id
```

## 自然語言查詢 🤖

系統支援自然語言查詢，AI 會自動將您的問題轉換為 SQL 語句：

### 支援的自然語言範例

**機台狀態查詢：**
- "M001機台的稼動率是多少？"
- "顯示所有機台的運行狀態"
- "哪些機台正在運行？"

**故障分析：**
- "最近有哪些故障？"
- "M001機台有什麼故障記錄？"
- "最常見的故障類型是什麼？"

**效能分析：**
- "哪台機台效率最高？"
- "今天的平均稼動率是多少？"
- "上週的生產趨勢如何？"

## 錯誤處理與疑難排解 ❗

### 常見錯誤訊息

**1. 語法錯誤**
```
❌ 錯誤：語法錯誤在或附近 "SELCT"
✅ 解決：檢查 SQL 語法，確保關鍵字拼寫正確
```

**2. 表格不存在**
```
❌ 錯誤：關係 "machine_dat" 不存在
✅ 解決：使用 /tables 查看可用表格，確認表格名稱
```

**3. 欄位不存在**
```
❌ 錯誤：欄位 "utiliztion_rate" 不存在
✅ 解決：使用 information_schema.columns 查看正確欄位名稱
```

### 查詢優化建議

**1. 使用適當的索引**
- 在 WHERE 條件中使用有索引的欄位
- 避免在大表上進行全表掃描

**2. 限制結果數量**
```sql
-- 好的做法
/sql SELECT * FROM machine_data LIMIT 100

-- 避免的做法  
/sql SELECT * FROM machine_data
```

**3. 使用適當的時間範圍**
```sql
-- 好的做法
/sql SELECT * FROM machine_data WHERE timestamp >= NOW() - INTERVAL '1 day'

-- 避免的做法
/sql SELECT * FROM machine_data WHERE timestamp > '2020-01-01'
```

## 系統限制與注意事項 ⚠️

### 查詢限制
- 單次查詢結果最多返回 1000 筆記錄
- 查詢執行時間限制為 30 秒
- 不支援 DDL 操作（CREATE, ALTER, DROP）
- 不支援 DML 操作（INSERT, UPDATE, DELETE）

### 安全限制
- 所有查詢都是唯讀的
- 自動過濾敏感資訊
- 記錄所有查詢操作

### 效能建議
- 避免複雜的多表聯合查詢
- 使用 LIMIT 限制結果數量
- 在時間欄位上使用索引範圍查詢

## 最佳實踐 🌟

### 1. 查詢設計原則
- **明確目標**：清楚知道要查詢什麼資訊
- **範圍限制**：使用時間、機台等條件縮小查詢範圍
- **結果驗證**：檢查查詢結果是否合理

### 2. 效率優化
- **索引使用**：優先使用有索引的欄位作為查詢條件
- **資料分頁**：大量資料使用 LIMIT 和 OFFSET
- **快取利用**：重複查詢會自動使用快取

### 3. 可讀性提升
- **註解說明**：複雜查詢添加註解
- **格式整齊**：使用適當的縮排和換行
- **命名規範**：使用有意義的別名

## 聯絡支援 📞

如果遇到技術問題或需要協助：

1. **系統狀態檢查**：使用 `/status` 確認系統運行狀態
2. **重新啟動**：輸入 `/help` 重新載入指令清單
3. **技術支援**：聯絡系統管理員

---

**版本：** v2.0
**更新日期：** 2025-06-26
**系統狀態：** ✅ 正常運行