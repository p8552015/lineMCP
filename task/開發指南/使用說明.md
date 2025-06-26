# SQL 模板開發指南使用說明

## 文檔結構

本開發指南包含以下文檔：

### 1. SQL模板開發指南.md
**用途**：完整的開發規範和最佳實踐指南  
**適用對象**：所有開發人員  
**內容包括**：
- 開發規範和命名規則
- 錯誤處理最佳實踐
- 監控和告警機制
- 實施計劃

### 2. 資料庫結構參考文檔.yaml
**用途**：標準的資料庫結構參考  
**適用對象**：開發人員、資料庫管理員  
**內容包括**：
- 實際資料庫表結構
- 常見錯誤對照表
- SQL 模板最佳實踐範例
- 資料類型轉換注意事項

### 3. SQL模板驗證腳本.py
**用途**：自動化驗證工具  
**適用對象**：開發人員、CI/CD 流程  
**功能包括**：
- 自動檢查欄位名稱一致性
- SQL 語法驗證
- 生成驗證報告

## 使用方法

### 開發階段

#### 1. 開發前準備
```bash
# 1. 查閱資料庫結構文檔
cat task/開發指南/資料庫結構參考文檔.yaml

# 2. 閱讀開發指南
cat task/開發指南/SQL模板開發指南.md
```

#### 2. 開發過程中
- 遵循 SQL模板開發指南.md 中的規範
- 參考 資料庫結構參考文檔.yaml 中的欄位名稱
- 使用提供的 SQL 範例作為模板

#### 3. 開發完成後
```bash
# 執行自動驗證
python task/開發指南/SQL模板驗證腳本.py \
  "postgresql://username:password@localhost:5432/database" \
  "apps/bot/src/services/nl_to_sql/config/sql_templates.yaml"
```

### CI/CD 集成

#### 1. GitHub Actions 配置
在 `.github/workflows/` 中添加：

```yaml
name: SQL Template Validation
on: [push, pull_request]

jobs:
  validate-sql:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install sqlalchemy psycopg2-binary pyyaml
      - name: Validate SQL Templates
        run: |
          python task/開發指南/SQL模板驗證腳本.py \
            ${{ secrets.DATABASE_URL }} \
            apps/bot/src/services/nl_to_sql/config/sql_templates.yaml
```

#### 2. 本地開發環境
```bash
# 安裝依賴
pip install sqlalchemy psycopg2-binary pyyaml

# 設置環境變數
export DATABASE_URL="postgresql://username:password@localhost:5432/database"

# 執行驗證
python task/開發指南/SQL模板驗證腳本.py \
  $DATABASE_URL \
  apps/bot/src/services/nl_to_sql/config/sql_templates.yaml
```

## 常見使用場景

### 場景 1：新增 SQL 模板
1. 查閱 `資料庫結構參考文檔.yaml`
2. 按照 `SQL模板開發指南.md` 編寫模板
3. 執行 `SQL模板驗證腳本.py` 驗證
4. 提交程式碼

### 場景 2：修復現有模板
1. 執行驗證腳本找出問題
2. 參考錯誤對照表修正
3. 重新驗證確認修復
4. 提交修復

### 場景 3：資料庫結構變更
1. 更新 `資料庫結構參考文檔.yaml`
2. 執行驗證腳本找出影響的模板
3. 批量修復受影響的模板
4. 更新開發指南（如需要）

## 錯誤處理

### 常見錯誤類型

#### 1. 欄位不存在錯誤
```
表 'machines' 中不存在欄位 'machine_id'，建議使用 'id'
```
**解決方案**：參考資料庫結構文檔，使用正確的欄位名稱

#### 2. 表不存在錯誤
```
表 'machine_status' 不存在於資料庫中
```
**解決方案**：檢查表名拼寫或確認表是否已創建

#### 3. SQL 語法錯誤
```
SQL 語法錯誤: syntax error at or near "SELCT"
```
**解決方案**：檢查 SQL 語法拼寫

### 故障排除步驟

1. **檢查錯誤訊息**：仔細閱讀驗證腳本的錯誤輸出
2. **查閱參考文檔**：對照資料庫結構參考文檔
3. **使用錯誤對照表**：查看常見錯誤的修正建議
4. **測試修復**：重新執行驗證腳本
5. **更新文檔**：如發現新的錯誤模式，更新指南

## 維護和更新

### 定期維護任務

#### 每月檢查
- [ ] 更新資料庫結構文檔
- [ ] 檢查驗證腳本的準確性
- [ ] 更新常見錯誤對照表

#### 每季度檢查
- [ ] 審查開發指南的完整性
- [ ] 收集開發團隊反饋
- [ ] 優化驗證腳本性能

#### 重大更新時
- [ ] 資料庫結構變更時立即更新文檔
- [ ] 新增錯誤類型時更新對照表
- [ ] 工具升級時測試兼容性

### 文檔版本控制

所有文檔都應該：
- 記錄變更歷史
- 標註版本號
- 說明變更原因
- 保留舊版本備份

## 團隊培訓

### 新成員入職
1. 閱讀完整的開發指南
2. 實際操作驗證腳本
3. 練習修復常見錯誤
4. 參與程式碼審查

### 定期培訓
1. 分享最佳實踐
2. 討論新發現的問題
3. 更新團隊知識庫
4. 改進開發流程

## 聯絡方式

如有問題或建議，請聯絡：
- 專案負責人：SQL模板修復專案小組
- 技術支援：參考 GitHub Issues
- 文檔更新：提交 Pull Request

---

**最後更新**：2025-01-24  
**版本**：1.0  
**維護者**：SQL模板修復專案小組 