# LINE Bot 查詢模式配置與擴展

## specific_machine 模式配置
### 1. 查詢模式定義 (`query_patterns.yaml`)
```yaml
specific_machine:
  patterns:
    - "[Mm]\\d{3,4}.*機台"
    - "[Mm]\\d{3,4}.*狀態"
    - "[Mm]\\d{3,4}.*狀況"
    - "[Mm]\\d{3,4}.*運行"
    - "[Mm]\\d{3,4}.*運轉"
    - "[Mm]\\d{3,4}.*情況"
    - "[Mm]\\d{3,4}.*概況"
    - "機台.*[Mm]\\d{3,4}"
  confidence: 0.9
  description: "查詢特定機台的詳細狀態和效能資料"
```

### 2. 參數提取邏輯 (`rule_based_parser.py`)
```python
if query_type == QueryType.SPECIFIC_MACHINE:
    # 提取機台 ID 參數
    machine_match = self._machine_id_pattern.search(normalized_text)
    if machine_match:
        digits = machine_match.group(1)
        machine_id = f"M{digits.zfill(3)}" if len(digits) <= 3 else f"M{digits}"
        parameters["machine_id"] = machine_id
```

## 支援的查詢類型
1. **all_machines**: 查看所有機台 (SQL長度: 386)
2. **specific_machine**: M001機台狀態 (SQL長度: 549)
3. **department_status**: 加工部機台狀態 (SQL長度: 389)
4. **fault_analysis**: 故障分析
5. **production_stats**: 生產統計
6. **machine_status**: 機台運行狀態

## 擴展新查詢類型流程
1. 在 `query_patterns.yaml` 添加模式定義
2. 在 `QueryType` 枚舉中添加新類型
3. 在 `rule_based_parser.py` 添加參數提取邏輯
4. 在 `sql_templates.yaml` 添加對應的 SQL 模板
5. 進行完整測試驗證