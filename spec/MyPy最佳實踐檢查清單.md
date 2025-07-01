# MyPy 最佳實踐檢查清單

> **🎯 目標**: 確保開發過程中遵循 MyPy 最佳實踐，維持零錯誤狀態
> 
> **📅 版本**: v1.0 (基於 107→0 錯誤修復經驗)
> **✅ 狀態**: 企業級類型安全標準

## 📋 開發前檢查清單

### 🚀 開始編碼前
- [ ] 確認當前 MyPy 錯誤數為 0：`poetry run mypy src/ --no-error-summary 2>&1 | grep -c "error:" || echo "0"`
- [ ] 檢查 .mypy-baseline 基準線：`cat .mypy-baseline`
- [ ] 確認 IDE 已啟用 MyPy 插件
- [ ] 確認 pre-commit hooks 正常運作

### 💻 編碼過程中
- [ ] 為新函數添加明確的返回類型註解
- [ ] 為新變量添加類型註解（特別是容器類型）
- [ ] 使用現代 Python 聯合類型語法 (`str | None`)
- [ ] 避免使用 `Any` 類型（除非必要）
- [ ] 添加必要的 None 檢查

## 📝 代碼審查檢查清單

### 🔍 類型註解審查
- [ ] **函數返回類型**: 所有函數都有明確返回類型
- [ ] **參數類型**: 所有參數都有類型註解
- [ ] **變量類型**: 容器變量有明確泛型註解
- [ ] **可選類型**: 使用 `| None` 而非 `Optional`
- [ ] **導入語句**: 必要的 typing 導入已添加

### 🛡️ 安全性檢查
- [ ] **None 檢查**: 可選類型在使用前進行 None 檢查
- [ ] **類型轉換**: 明確的類型轉換而非隱式
- [ ] **第三方庫**: 對不確定類型使用 `cast()`
- [ ] **錯誤處理**: 類型安全的異常處理

## 🧪 測試階段檢查清單

### ✅ 提交前檢查
- [ ] 運行完整 MyPy 檢查：`poetry run mypy src/`
- [ ] 確認零錯誤輸出
- [ ] 運行自動修復工具（如有需要）：`./scripts/fix-mypy-errors.sh`
- [ ] 更新 .mypy-baseline（如有變更）

### 🚦 CI/CD 整合檢查
- [ ] 確認 MyPy 檢查已加入 CI pipeline
- [ ] 檢查 CI 中的 MyPy 配置與本地一致
- [ ] 確認 CI 失敗時會阻止合併

## 📊 常見錯誤類型快速檢查

### 🔥 高風險錯誤（立即修復）
- [ ] `no-any-return`: 函數返回 Any 但聲明其他類型
- [ ] `attr-defined`: 訪問不存在的屬性
- [ ] `assignment`: 不兼容的類型賦值

### ⚠️ 中風險錯誤（優先修復）
- [ ] `union-attr`: 在可能為 None 的對象上調用方法
- [ ] `operator`: 不支持的操作數類型
- [ ] `call-overload`: 函數調用不匹配

### 📝 低風險錯誤（計劃修復）
- [ ] `var-annotated`: 缺少變量類型註解
- [ ] `valid-type`: 無效的類型表達式
- [ ] `misc`: 其他雜項錯誤

## 🛠️ 自動化工具使用清單

### 📋 日常開發工具
- [ ] 使用 IDE MyPy 插件實時檢查
- [ ] 配置 pre-commit hooks 自動檢查
- [ ] 定期運行自動修復腳本

### 🔧 專案工具
- [ ] **自動修復**: `./scripts/fix-mypy-errors.sh`
- [ ] **CI 檢查**: `./scripts/mypy-ci-check.sh`
- [ ] **版本檢查**: `./scripts/check-tool-versions.sh`
- [ ] **品質檢查**: `./scripts/quality-check.sh`

## 📈 效能優化檢查清單

### ⚡ MyPy 執行優化
- [ ] 使用 mypy daemon 加速檢查
- [ ] 配置 .mypy.ini 排除不必要的檢查
- [ ] 使用增量檢查模式
- [ ] 適當配置快取設置

### 🎯 檢查範圍優化
- [ ] 只檢查修改過的檔案（開發階段）
- [ ] 完整檢查（CI/CD 階段）
- [ ] 設置適當的錯誤基準線

## 🏆 團隊協作檢查清單

### 👥 團隊標準
- [ ] 統一的 MyPy 配置檔案
- [ ] 一致的類型註解風格指南
- [ ] 共同的錯誤處理模式
- [ ] 定期的類型安全培訓

### 📚 知識分享
- [ ] 維護類型註解最佳實踐文檔
- [ ] 記錄常見錯誤解決方案
- [ ] 建立類型安全 Code Review 標準
- [ ] 分享自動化工具使用經驗

## 🚨 緊急情況處理清單

### 🔴 CI/CD 失敗處理
- [ ] 檢查 CI 日誌中的 MyPy 錯誤
- [ ] 在本地重現錯誤環境
- [ ] 使用自動修復工具快速處理
- [ ] 手動修復複雜錯誤
- [ ] 更新錯誤基準線（如必要）

### 🆘 大量錯誤處理
- [ ] 使用 `./scripts/fix-mypy-errors.sh` 批量修復
- [ ] 按錯誤類型分類處理
- [ ] 建立臨時基準線
- [ ] 制定漸進式修復計劃

## 📊 品質指標檢查清單

### 🎯 目標指標
- [ ] MyPy 錯誤數：0 （目標）
- [ ] 類型覆蓋率：> 95%
- [ ] CI 通過率：100%
- [ ] 錯誤回歸率：< 1%

### 📈 監控指標
- [ ] 每週 MyPy 錯誤趨勢
- [ ] 新增代碼類型註解覆蓋率
- [ ] 自動修復工具效果統計
- [ ] 團隊類型安全成熟度

## 🔄 持續改進檢查清單

### 🆕 定期評估（月度）
- [ ] 評估當前類型註解標準
- [ ] 更新自動修復腳本
- [ ] 審查錯誤模式變化
- [ ] 優化工具鏈效率

### 📋 季度審查
- [ ] 評估 MyPy 版本升級需求
- [ ] 檢查新的 Python 類型特性
- [ ] 更新團隊培訓材料
- [ ] 優化 CI/CD 配置

## 📚 快速參考

### 🔧 常用命令
```bash
# 基本檢查
poetry run mypy src/

# 統計錯誤數
poetry run mypy src/ --no-error-summary 2>&1 | grep -c "error:" || echo "0"

# 自動修復
./scripts/fix-mypy-errors.sh

# CI 檢查
./scripts/mypy-ci-check.sh

# 查看基準線
cat .mypy-baseline
```

### 📝 常用類型註解
```python
# 基本類型
name: str = ""
age: int = 0
is_active: bool = True

# 可選類型
optional_name: str | None = None
optional_data: dict[str, Any] | None = None

# 容器類型
names: list[str] = []
config: dict[str, Any] = {}

# 函數類型
def process_data(data: dict[str, Any]) -> tuple[bool, str]:
    return True, "success"
```

---

## ✅ 成功案例參考

本專案的成功經驗（2025-07-01）：
- **107 → 0 錯誤**：100% 完全修復
- **修復時間**：系統化批量處理
- **零回歸**：建立完善預防機制
- **企業級品質**：達到工業標準

**記住**：類型安全檢查清單是保證代碼品質的最後一道防線！🛡️