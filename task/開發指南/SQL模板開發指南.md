# SQL 模板開發指南

## 目的
本指南旨在防止 SQL 模板與資料庫結構不一致的問題，確保系統穩定性和資料準確性。

## 背景
在 SQL 模板欄位名稱不一致修復專案中，我們發現了多個關鍵問題：
- SQL 模板中的欄位名稱與實際資料庫結構不符
- JOIN 條件使用錯誤的欄位名稱
- 資料類型轉換處理不當
- 缺乏自動化驗證機制

## 開發規範

### 1. 資料庫結構文檔化

#### 1.1 維護資料庫結構文檔
```yaml
# docs/database/schema_reference.yaml
tables:
  machines:
    columns:
      - name: id
        type: integer
        primary_key: true
        description: 機台唯一識別碼
      - name: name
        type: varchar(100)
        description: 機台名稱
      - name: location
        type: varchar(100)
        description: 機台位置/部門
    
  machine_utilization:
    columns:
      - name: machine_id
        type: integer
        foreign_key: machines.id
        description: 關聯機台ID
      - name: efficiency_rate
        type: decimal(5,2)
        description: 效率百分比
```

#### 1.2 自動生成結構文檔
```bash
# 使用腳本自動生成資料庫結構文檔
python scripts/generate_schema_docs.py
```

### 2. SQL 模板開發規範

#### 2.1 欄位名稱命名規則
- **使用實際資料庫欄位名稱**：確保 SQL 模板中的欄位名稱與資料庫完全一致
- **避免假設性命名**：不要使用 `machine_name`，應使用實際的 `name`
- **統一別名規則**：表別名使用首字母，如 `machines` → `m`

```sql
-- ✅ 正確示例
SELECT 
    m.id,           -- 使用實際欄位名 id
    m.name,         -- 使用實際欄位名 name
    m.location      -- 使用實際欄位名 location
FROM machines m

-- ❌ 錯誤示例
SELECT 
    m.machine_id,   -- 錯誤：machines 表沒有 machine_id 欄位
    m.machine_name, -- 錯誤：應該是 name
    m.department    -- 錯誤：應該是 location
FROM machines m
```

#### 2.2 JOIN 條件規範
```sql
-- ✅ 正確的 JOIN 條件
SELECT m.name, u.efficiency_rate
FROM machines m
JOIN machine_utilization u ON m.id = u.machine_id

-- ❌ 錯誤的 JOIN 條件
SELECT m.name, u.efficiency_rate
FROM machines m
JOIN machine_utilization u ON m.machine_id = u.machine_id  -- machines 表沒有 machine_id
```

#### 2.3 資料類型處理
```python
# ✅ 安全的資料類型轉換
def safe_int_conversion(value):
    """安全地將值轉換為整數"""
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))  # 處理 "123.0" 格式
        except (ValueError, TypeError):
            return 0
    return 0

# ❌ 危險的資料類型處理
def unsafe_conversion(value):
    return int(value)  # 可能拋出異常
```

### 3. 開發流程

#### 3.1 開發前檢查清單
- [ ] 查閱最新的資料庫結構文檔
- [ ] 驗證所有欄位名稱的正確性
- [ ] 確認 JOIN 條件的準確性
- [ ] 檢查資料類型轉換的安全性

#### 3.2 程式碼審查清單
- [ ] SQL 模板中的欄位名稱與資料庫結構一致
- [ ] JOIN 條件使用正確的欄位
- [ ] 資料類型轉換有適當的錯誤處理
- [ ] 添加了相應的測試用例

#### 3.3 測試要求
```python
# 每個 SQL 模板都應該有對應的測試
def test_production_stats_template():
    """測試生產統計 SQL 模板"""
    # 驗證 SQL 語法正確性
    # 驗證欄位名稱存在
    # 驗證返回資料格式
    pass

def test_database_field_consistency():
    """測試資料庫欄位一致性"""
    # 自動檢查 SQL 模板中的欄位是否存在於資料庫中
    pass
```

### 4. 自動化工具

#### 4.1 欄位驗證腳本
```python
# scripts/validate_sql_templates.py
import yaml
import re
from sqlalchemy import inspect

def validate_template_fields(template_file, database_url):
    """驗證 SQL 模板中的欄位是否存在於資料庫中"""
    with open(template_file, 'r') as f:
        templates = yaml.safe_load(f)
    
    # 連接資料庫並獲取結構
    inspector = inspect(create_engine(database_url))
    
    for template_name, template_sql in templates.items():
        # 解析 SQL 中的欄位名稱
        fields = extract_fields_from_sql(template_sql)
        
        # 驗證欄位是否存在
        validate_fields_exist(fields, inspector)
```

#### 4.2 CI/CD 集成
```yaml
# .github/workflows/sql_validation.yml
name: SQL Template Validation
on: [push, pull_request]

jobs:
  validate-sql:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Validate SQL Templates
        run: |
          python scripts/validate_sql_templates.py
          python scripts/test_sql_templates.py
```

### 5. 錯誤處理最佳實踐

#### 5.1 SQL 執行錯誤處理
```python
def execute_template_query(template_name, params):
    """執行模板查詢並處理錯誤"""
    try:
        sql = get_template(template_name)
        result = database.execute(sql, params)
        return result
    except SQLAlchemyError as e:
        logger.error(f"SQL 執行錯誤 - 模板: {template_name}, 錯誤: {str(e)}")
        # 檢查是否是欄位不存在錯誤
        if "column" in str(e).lower() and "does not exist" in str(e).lower():
            raise FieldNotExistError(f"欄位不存在錯誤，請檢查 SQL 模板: {template_name}")
        raise
```

#### 5.2 資料驗證
```python
def validate_query_result(result, expected_fields):
    """驗證查詢結果的欄位完整性"""
    if not result:
        return True
    
    first_row = result[0] if isinstance(result, list) else result
    actual_fields = set(first_row.keys()) if hasattr(first_row, 'keys') else set()
    expected_fields = set(expected_fields)
    
    missing_fields = expected_fields - actual_fields
    if missing_fields:
        raise ValidationError(f"查詢結果缺少欄位: {missing_fields}")
```

### 6. 監控和告警

#### 6.1 SQL 錯誤監控
```python
# 在應用程式中添加 SQL 錯誤監控
@monitor_sql_errors
def execute_nl_to_sql_query(query_type, params):
    """執行自然語言轉 SQL 查詢並監控錯誤"""
    try:
        return nl_to_sql_service.execute(query_type, params)
    except FieldNotExistError as e:
        # 發送告警通知
        alert_service.send_alert(
            title="SQL 欄位不存在錯誤",
            message=str(e),
            severity="high"
        )
        raise
```

#### 6.2 健康檢查
```python
def sql_template_health_check():
    """SQL 模板健康檢查"""
    health_status = {}
    
    for template_name in get_all_template_names():
        try:
            # 執行簡單的語法檢查
            validate_template_syntax(template_name)
            health_status[template_name] = "healthy"
        except Exception as e:
            health_status[template_name] = f"error: {str(e)}"
    
    return health_status
```

### 7. 文檔維護

#### 7.1 變更記錄
```markdown
# SQL 模板變更記錄

## 2025-01-24
- 修復 production_stats 模板中的欄位名稱錯誤
- 修正 machines 表的 JOIN 條件
- 添加資料類型安全轉換

## 變更影響分析
- 影響的查詢類型：生產統計、機台狀態
- 測試覆蓋率：100%
- 向後兼容性：是
```

#### 7.2 故障排除指南
```markdown
# SQL 模板故障排除

## 常見錯誤

### 1. column "field_name" does not exist
**原因**：SQL 模板中的欄位名稱與資料庫不一致
**解決方案**：
1. 檢查資料庫實際結構
2. 更新 SQL 模板中的欄位名稱
3. 執行驗證測試

### 2. 資料類型轉換錯誤
**原因**：嘗試將不相容的資料類型進行轉換
**解決方案**：
1. 添加類型檢查
2. 使用安全轉換函數
3. 提供預設值處理
```

## 實施計劃

### 階段 1：立即實施（1-2 天）
1. 建立資料庫結構文檔
2. 實施欄位驗證腳本
3. 添加基本的錯誤處理

### 階段 2：短期實施（1 週）
1. 完善測試覆蓋率
2. 集成 CI/CD 驗證
3. 添加監控告警

### 階段 3：長期維護（持續）
1. 定期更新文檔
2. 優化自動化工具
3. 培訓團隊成員

## 結論

通過遵循本開發指南，我們可以：
- **預防** SQL 模板欄位不一致問題
- **提高** 系統穩定性和資料準確性
- **減少** 生產環境故障
- **提升** 開發效率和程式碼品質

定期檢查和更新本指南，確保其與專案需求保持同步。 