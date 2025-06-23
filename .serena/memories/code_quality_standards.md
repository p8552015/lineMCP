# 程式碼品質與風格標準

## 🎨 程式碼風格

### Python 風格規範
- **格式化工具**: black (line-length=88)
- **Linting**: ruff (E, F, I, N, W, UP, B, C4, PT, SIM)
- **類型檢查**: mypy (strict mode)
- **Python 版本**: 3.11+

### 命名慣例
- **類別**: PascalCase (如 ApplicationFacade)
- **函數/變數**: snake_case (如 get_service)
- **常數**: UPPER_SNAKE_CASE (如 LINE_CHANNEL_ACCESS_TOKEN)
- **私有成員**: _leading_underscore

### 檔案組織
- **模組導入順序**: 標準庫 → 第三方 → 本地模組
- **每個模組**: 單一職責，清晰的 __init__.py
- **測試**: 每個模組對應測試檔案

## 📝 文檔標準

### Docstring 規範
```python
def service_method(self, param: str) -> Dict[str, Any]:
    """
    服務方法的簡短描述
    
    Args:
        param: 參數描述
        
    Returns:
        Dict[str, Any]: 返回值描述
        
    Raises:
        ServiceException: 異常描述
    """
```

### 中文註解
- 業務邏輯使用中文註解說明
- 技術實現細節可使用英文
- 關鍵決策點必須有中文說明

## 🧪 測試標準

### 測試覆蓋率
- **單元測試**: 核心業務邏輯 90%+ 覆蓋
- **整合測試**: 關鍵流程端到端驗證
- **架構測試**: 依賴關係和服務工廠測試

### 測試組織
```
tests/
├── unit/          # 單元測試
├── integration/   # 整合測試
├── application/   # 應用層測試
├── infrastructure/ # 基礎設施測試
└── services/      # 服務層測試
```

## 🔒 品質檢查點

### 提交前檢查
- [ ] black 格式化通過
- [ ] ruff linting 無警告
- [ ] mypy 類型檢查通過
- [ ] pytest 測試全部通過
- [ ] 新增功能有對應測試

### 架構品質
- [ ] 無循環依賴
- [ ] 符合 SOLID 原則
- [ ] 清晰的分層架構
- [ ] 適當的抽象層級

## ⚠️ 技術債務管理

### 已解決問題
- ✅ FlexBuilder 重構: 移除1416行未使用代碼
- ✅ 循環依賴解決: 實現依賴倒置原則
- ✅ v5穩定性修復: 空查詢和類型安全問題
- ✅ 零警告零錯誤: 達到生產級品質標準

### 持續改進原則
- 漸進式重構，避免大爆炸式變更
- 測試驅動開發，確保重構安全
- 定期代碼審查，發現潛在問題
- 文檔同步更新，保持一致性