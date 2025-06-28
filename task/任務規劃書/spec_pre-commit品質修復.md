# spec_pre-commit品質修復專案

## 🎯 專案目標
徹底解決剩餘的 Pre-commit 問題，建立完善的程式碼品質控制流程，確保專案達到企業級品質標準。

## 📋 專案背景

### 已完成基礎修復
✅ **types-all 依賴問題** - 已更新為具體類型套件  
✅ **Ruff 版本匹配** - 已升級至 v0.7.0  
✅ **模組命名衝突** - config.py → settings.py 重構完成  
✅ **Black 格式化** - 44個檔案格式化完成  

### 剩餘問題分析
⚠️ **105個行長度問題** (E501) - 需要手動修復  
⚠️ **MyPy 類型檢查** - 缺少175個類型錯誤  
⚠️ **Ruff 配置語法** - 需要現代化配置  

## 📊 任務執行表

<!-- TASKS START -->
| ID | 任務 | 描述 | 優先級 | 負責 | 狀態 | 開始 | 結束 |
|---|---|---|---|---|---|---|---|
| T-01 | 建立專案規格文件 | 建立 spec_pre-commit品質修復.md 規格文件 | High | 開發者 | DOING | 2025-06-28 21:15 | - |
| T-02 | 修復行長度問題 | 修復105個E501行長度超過88字元問題 | High | 開發者 | TODO | - | - |
| T-03 | 補充MyPy類型依賴 | 新增缺失的類型定義套件到pyproject.toml | High | 開發者 | TODO | - | - |
| T-04 | 更新ruff配置語法 | 修正pyproject.toml中的lint配置語法 | Medium | 開發者 | TODO | - | - |
| T-05 | 完整pre-commit測試 | 執行完整pre-commit檢查確保所有問題解決 | High | 開發者 | TODO | - | - |
| T-06 | 建立品質檢查腳本 | 建立自動化程式碼品質檢查腳本 | Medium | 開發者 | TODO | - | - |
| T-07 | 更新開發文檔 | 更新CLAUDE.md和相關開發指南 | Medium | 開發者 | TODO | - | - |
| T-08 | 系統整合測試 | 執行start-production.sh並驗證核心功能 | High | 開發者 | TODO | - | - |
| T-09 | Git版本提交 | 提交所有修改並建立clean baseline | Low | 開發者 | TODO | - | - |
| T-10 | 撰寫最終報告 | 建立完整的專案總結報告 | Medium | 開發者 | TODO | - | - |
<!-- TASKS END -->

## 🔧 核心修復策略

### 1. E501 行長度修復指南

參考 `docs/architecture/code-quality-best-practices.md` 的修復策略：

#### 字串分割技術
```python
# ❌ 錯誤：單行過長 
message = f"🔄 規則回退: {'✅ 啟用' if self.nl_service.fallback_to_rules else '❌ 禁用'}\n"

# ✅ 正確：字串分割
message = (
    f"🔄 規則回退: "
    f"{'✅ 啟用' if self.nl_service.fallback_to_rules else '❌ 禁用'}\n"
)
```

#### 條件換行技術
```python
# ❌ 錯誤：條件過長
if not await runtime_manager.validate_command(config.command, config.args) and config.runtime_type == RuntimeType.NODEJS:

# ✅ 正確：條件換行
if (
    not await runtime_manager.validate_command(config.command, config.args)
    and config.runtime_type == RuntimeType.NODEJS
    and config.command == "npx"
):
```

#### 函數參數垂直對齊
```python
# ❌ 錯誤：參數列表過長
result = some_function(param1, param2, param3, param4, param5, param6)

# ✅ 正確：垂直對齊
result = some_function(
    param1, param2, param3,
    param4, param5, param6
)
```

### 2. MyPy 類型依賴補強

需要新增的類型定義套件：
```toml
[tool.poetry.group.dev.dependencies]
types-structlog = "^24.1.0"
types-fastapi = "^0.104.1"  
types-prometheus-client = "^0.20.0"
types-psutil = "^5.9.5"
types-linebot = "^3.0.0"
types-httpx = "^0.27.0"
types-redis = "^4.6.0"
types-jose = "^3.3.0"
```

### 3. Ruff 配置現代化

更新 pyproject.toml 配置：
```toml
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "PT", "SIM"]
fix = true

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["E501"]  # 測試檔案可以較寬鬆
"**/migrations/*" = ["E501", "F401"]  # 遷移檔案例外
```

## 🧪 品質驗證標準

### 技術指標目標
- **Ruff 檢查**: 0錯誤、0警告 (目前105個E501錯誤)
- **Black 格式化**: 100%一致性 ✅
- **MyPy 類型檢查**: 0類型錯誤 (目前175個錯誤)
- **Pre-commit 執行**: 完全通過
- **執行時間**: <2分鐘

### 功能驗證檢查點
- ✅ M001機台稼動率查詢: 正常返回74.4%
- ✅ 所有機台狀態查詢: 完整數據顯示
- ✅ LINE Bot回應: <2秒響應時間
- ✅ MCP連接: 穩定無中斷

### 測試指令序列
```bash
# 基礎品質檢查
cd apps/bot && poetry run ruff check src/ --fix
cd apps/bot && poetry run black src/
cd apps/bot && poetry run mypy src/

# Pre-commit完整測試
cd /Users/yen/Desktop/lineMCP && pre-commit run --all-files

# 系統整合驗證
./start-production.sh test
```

## 🔧 自動化品質檢查腳本

將建立 `scripts/quality-check.sh` 腳本：
```bash
#!/bin/bash
# Pre-commit 品質檢查自動化腳本
set -e

echo "🔍 執行完整程式碼品質檢查..."

# 1. Ruff 檢查與自動修復
echo "📋 Step 1: Ruff 檢查..."
cd apps/bot
poetry run ruff check src/ --fix --statistics

# 2. Black 格式化檢查
echo "🎨 Step 2: Black 格式化..."
poetry run black src/ --check --diff

# 3. MyPy 類型檢查
echo "🏷️ Step 3: MyPy 類型檢查..."
poetry run mypy src/

# 4. Pre-commit 全面檢查
echo "✅ Step 4: Pre-commit hooks..."
cd ..
pre-commit run --all-files

# 5. 系統功能驗證
echo "🚀 Step 5: 系統功能驗證..."
./start-production.sh test

echo "✨ 所有品質檢查完成！"
```

## 📁 文檔產出規劃

### 必須產出文件
1. **測試報告**: `/Users/yen/Desktop/lineMCP/CICD/tests/reports/pre-commit-quality-test.md`
2. **最終報告**: `/Users/yen/Desktop/lineMCP/task/最終報告/pre-commit品質修復完整報告.md`

### 必須更新文檔
1. **CLAUDE.md**: 新增pre-commit使用指南
2. **code-quality-best-practices.md**: 補充E501修復經驗
3. **start-production.sh**: 整合品質檢查步驟

## ⚠️ 風險控制措施

### 修改安全檢查
- 每次修改前使用 Serena MCP 分析影響範圍
- 確保修改不破壞現有功能邏輯
- 關鍵檔案修改後立即執行相關測試

### 漸進式修復策略
1. **分批修復**: 每次處理10-15個E501錯誤
2. **即時驗證**: 每批修復後執行ruff檢查
3. **功能測試**: 關鍵模組修復後執行單元測試

### 回滾機制
- 每個任務完成後立即提交Git版本
- 保留關鍵檔案的修改前備份
- 建立快速恢復腳本

## 📊 進度追蹤機制

### 每30分鐘檢查點
- 自動執行 `git add . && git commit -m "進度檢查點: $(date)"`
- 更新任務狀態到本規格文件
- 執行漸進式品質檢查

### 階段性里程碑
- **階段一** (T-01~T-03): 核心問題修復 → 預期50%錯誤減少
- **階段二** (T-04~T-06): 工具鏈優化 → 預期80%錯誤消除
- **階段三** (T-07~T-10): 文檔整理與總結 → 達到100%品質標準

## 🎯 成功完成標準

### 必須達成指標
- [ ] Ruff檢查: 0錯誤、0警告
- [ ] MyPy檢查: 0類型錯誤
- [ ] Pre-commit: 所有hooks正常通過
- [ ] 系統功能: 核心功能100%正常
- [ ] 文檔更新: 開發指南完整更新

### 品質保證檢查
- [ ] 程式碼符合SOLID原則
- [ ] 所有修改經過測試驗證
- [ ] 系統整體穩定運行
- [ ] 長期維護機制建立

---

## 📝 專案實施記錄

### T-01 執行記錄 (進行中)
- **開始時間**: 2025-06-28 21:15
- **執行內容**: 建立完整的專案規格文件
- **預期完成**: 2025-06-28 21:30
- **狀態**: 正在撰寫規格文件內容

### 下一步行動
完成 T-01 後立即開始 T-02：修復105個E501行長度問題，採用分批處理策略。

---

*本規格文件將隨專案進展實時更新，所有任務狀態變更都會反映在任務執行表中。*