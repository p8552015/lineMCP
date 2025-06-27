# LINE MCP 程式碼品質最佳實踐準則

## 📋 總覽
本準則基於 2025-06-27 完成的程式碼品質改善工作流（105個錯誤 → 0個錯誤），為後續開發者提供具體的編碼標準和最佳實踐。

## 🚨 關鍵錯誤類型與防範措施

### 1. E501 - 行長度限制 (最常見：38個錯誤)

**問題**: 程式碼行超過 88 字元限制

**防範措施**:
```python
# ❌ 錯誤：單行過長
message = f"🔄 規則回退: {'✅ 啟用' if self.nl_service.fallback_to_rules else '❌ 禁用'}\n"

# ✅ 正確：字串分割
message = (
    f"🔄 規則回退: "
    f"{'✅ 啟用' if self.nl_service.fallback_to_rules else '❌ 禁用'}\n"
)

# ✅ 正確：條件式換行
if (
    not await runtime_manager.validate_command(config.command, config.args)
    and config.runtime_type == RuntimeType.NODEJS
    and config.command == "npx"
):
```

**最佳實踐**:
- 使用括號進行多行條件判斷
- 字串使用括號自動連接
- 函數調用參數垂直對齊
- 編輯器設置 88 字元標記線

### 2. B904 - 異常處理鏈 (15個錯誤)

**問題**: 在 except 區塊中重新拋出異常時未保留原始異常資訊

**防範措施**:
```python
# ❌ 錯誤：遺失異常鏈
try:
    await some_operation()
except Exception as e:
    logger.error(f"操作失敗: {e}")
    raise HTTPException(status_code=500, detail="內部錯誤")

# ✅ 正確：保留異常鏈
try:
    await some_operation()
except Exception as e:
    logger.error(f"操作失敗: {e}")
    raise HTTPException(status_code=500, detail="內部錯誤") from e

# ✅ 正確：刻意隱藏異常鏈
try:
    await some_operation()
except Exception as e:
    logger.error(f"操作失敗: {e}")
    raise UserFriendlyError("操作失敗，請稍後再試") from None
```

**最佳實踐**:
- 總是使用 `from e` 保留異常鏈
- 僅在需要隱藏技術細節時使用 `from None`
- 記錄原始異常後再重新拋出

### 3. SIM102 - 可合併的 if 語句 (4個錯誤)

**問題**: 巢狀 if 語句可以合併為單一條件

**防範措施**:
```python
# ❌ 錯誤：巢狀 if
if self.protocol in [MCPProtocol.HTTP, MCPProtocol.WEBSOCKET]:
    if not self.url and not (self.host and self.port):
        errors.append("網路協議需要指定 URL 或 host/port")

# ✅ 正確：合併條件
if (self.protocol in [MCPProtocol.HTTP, MCPProtocol.WEBSOCKET] and
    not self.url and not (self.host and self.port)):
    errors.append("網路協議需要指定 URL 或 host/port")
```

**最佳實踐**:
- 檢查巢狀 if 是否可以用 `and` 合併
- 使用括號提高可讀性
- 保持邏輯清晰

### 4. B008 - 函數預設參數調用 (2個錯誤)

**問題**: 在函數參數預設值中調用函數

**防範措施**:
```python
# ❌ 錯誤：參數中調用函數
@router.get("/health")
async def health_check(checker: HealthChecker = Depends(get_health_checker)):
    pass

# ✅ 正確：模組級變數
_health_checker_dependency = Depends(get_health_checker)

@router.get("/health")
async def health_check(checker: HealthChecker = _health_checker_dependency):
    pass
```

**最佳實踐**:
- 將 Depends() 調用移到模組級
- 使用描述性的變數名稱
- 避免在函數簽名中進行複雜計算

### 5. E402 - 模組導入位置 (9個錯誤)

**問題**: 導入語句位置不正確

**防範措施**:
```python
# ❌ 錯誤：sys.path 修改後才導入
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.nodecomman.implementations import SomeModule  # 錯誤位置

# ✅ 正確：先導入，後修改路徑
import sys
from pathlib import Path

from src.nodecomman.implementations import SomeModule  # 正確位置

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
```

**最佳實踐**:
- 所有導入放在檔案頂部
- 按照 isort 標準排序
- 避免動態修改 sys.path

### 6. N818 - 異常命名規範 (10個錯誤)

**問題**: 異常類別名稱未遵循命名規範

**防範措施**:
```python
# ❌ 錯誤：異常名稱不以 Error 結尾
class InvalidConfiguration(Exception):
    pass

class DatabaseTimeout(Exception):
    pass

# ✅ 正確：異常名稱以 Error 結尾
class InvalidConfigurationError(Exception):
    pass

class DatabaseTimeoutError(Exception):
    pass
```

**最佳實踐**:
- 所有異常類別名稱必須以 `Error` 結尾
- 使用描述性的名稱說明異常類型
- 遵循 PEP 8 命名規範

### 7. E722 - 裸露 except 語句 (1個錯誤)

**問題**: 使用裸露的 except 子句

**防範措施**:
```python
# ❌ 錯誤：裸露 except
try:
    risky_operation()
except:
    handle_error()

# ✅ 正確：明確指定異常類型
try:
    risky_operation()
except Exception:
    handle_error()

# ✅ 更好：指定具體異常
try:
    risky_operation()
except (ValueError, TypeError) as e:
    handle_error(e)
```

**最佳實踐**:
- 總是指定要捕獲的異常類型
- 使用 `except Exception:` 而非裸露 `except:`
- 盡可能捕獲具體的異常類型

### 8. F401 - 未使用的導入 (1個錯誤)

**問題**: 導入了但未使用的模組

**防範措施**:
```python
# ❌ 錯誤：導入但未使用
from typing import Dict, List, Optional
from src.models import User  # 未使用

def get_users() -> List[Dict[str, str]]:
    return []

# ✅ 正確：移除未使用的導入
from typing import Dict, List

def get_users() -> List[Dict[str, str]]:
    return []
```

**最佳實踐**:
- 定期檢查並清理未使用的導入
- 使用 IDE 的自動導入清理功能
- 在 CI/CD 中啟用 F401 檢查

## 🛠️ 開發工具配置

### 1. 編輯器設置
```json
// VS Code settings.json
{
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "editor.rulers": [88],
    "editor.formatOnSave": true,
    "python.linting.ruffArgs": [
        "--select", "E,F,I,N,W,UP,B,C4,PT,SIM"
    ]
}
```

### 2. Pre-commit Hook
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: ["--fix"]
        exclude: ^tests/
```

### 3. pyproject.toml 配置
```toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''

[tool.ruff]
line-length = 88
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "PT", "SIM"]
fix = true
target-version = "py311"

[tool.ruff.per-file-ignores]
"tests/*" = ["E501"]  # 測試檔案可以較寬鬆
"**/migrations/*" = ["E501", "F401"]  # 遷移檔案例外

[tool.ruff.isort]
known-first-party = ["src"]
```

## 📋 日常開發檢查清單

### 提交前檢查 (必須)
- [ ] 執行 `poetry run ruff check src/` 確保無錯誤
- [ ] 執行 `poetry run black src/` 格式化代碼
- [ ] 檢查行長度不超過 88 字元
- [ ] 確保異常處理使用 `from e` 或 `from None`
- [ ] 檢查是否有巢狀 if 可以合併
- [ ] 驗證導入順序正確
- [ ] 確認所有異常類別名稱以 Error 結尾

### 程式碼審查重點
1. **異常處理**: 檢查 raise 語句是否保留異常鏈
2. **異常命名**: 確保所有異常類別以 Error 結尾
3. **條件邏輯**: 尋找可簡化的巢狀條件
4. **導入管理**: 確保導入位置和順序正確
5. **函數簽名**: 避免在參數中調用函數
6. **異常捕獲**: 避免裸露的 except 語句

### 週期性檢查 (每週)
- [ ] 執行完整的靜態分析報告
- [ ] 檢查程式碼覆蓋率
- [ ] 審查新增的技術債務
- [ ] 更新依賴套件版本

## 🚀 自動化修復指令

```bash
# 日常品質檢查和自動修復
poetry run ruff check src/ --fix
poetry run black src/

# 詳細錯誤分析
poetry run ruff check src/ --statistics

# 完整驗證流程
poetry run ruff check src/ && poetry run black src/ --check

# 檢查特定錯誤類型
poetry run ruff check src/ --select E501  # 只檢查行長度
poetry run ruff check src/ --select B904  # 只檢查異常處理鏈
poetry run ruff check src/ --select N818  # 只檢查異常命名

# 生成詳細報告
poetry run ruff check src/ --format=json > quality_report.json
```

## 📊 品質指標與監控

### 目標標準
- **Ruff 檢查**: 0 錯誤，0 警告
- **Black 格式化**: 100% 一致性
- **行長度**: ≤ 88 字元
- **異常處理**: 100% 使用異常鏈
- **異常命名**: 100% 符合 N818 規範
- **導入順序**: 符合 isort 標準
- **程式碼覆蓋率**: ≥ 85%

### 監控方法
```bash
# CI/CD 管道檢查腳本
#!/bin/bash
set -e

echo "🔍 執行程式碼品質檢查..."

# Ruff 檢查
poetry run ruff check src/
if [ $? -ne 0 ]; then
    echo "❌ Ruff 檢查失敗"
    exit 1
fi

# Black 格式檢查
poetry run black src/ --check
if [ $? -ne 0 ]; then
    echo "❌ Black 格式檢查失敗"
    exit 1
fi

# MyPy 類型檢查
poetry run mypy src/
if [ $? -ne 0 ]; then
    echo "❌ MyPy 類型檢查失敗"
    exit 1
fi

echo "✅ 所有程式碼品質檢查通過"
```

## 🎯 常見問題與解決方案

### Q1: 如何處理過長的字串？
```python
# 方法1：括號自動連接
message = (
    "這是一個很長的字串 "
    "需要分成多行來處理"
)

# 方法2：f-string 分割
error_msg = (
    f"處理 {operation} 時發生錯誤: "
    f"{error_details}"
)

# 方法3：多行字串
sql_query = """
    SELECT column1, column2, column3
    FROM table_name 
    WHERE condition = %s
    ORDER BY column1
"""
```

### Q2: 如何正確處理異常鏈？
```python
# 情境1：保留完整異常資訊（推薦）
try:
    database_operation()
except DatabaseError as e:
    logger.error(f"資料庫操作失敗: {e}")
    raise ServiceError("服務暫時不可用") from e

# 情境2：隱藏內部實作細節
try:
    internal_api_call()
except InternalAPIError as e:
    logger.error(f"內部API錯誤: {e}")
    raise UserError("請稍後再試") from None

# 情境3：添加上下文資訊
try:
    process_user_data(user_id)
except ValidationError as e:
    raise ValidationError(f"用戶 {user_id} 資料驗證失敗") from e
```

### Q3: 如何組織複雜的條件判斷？
```python
# 複雜條件的可讀性優化
def is_valid_config(config):
    return (
        config.name and
        config.protocol in SUPPORTED_PROTOCOLS and
        (config.url or (config.host and config.port)) and
        config.timeout > 0 and
        config.retry_attempts >= 0
    )

# 使用早期返回簡化邏輯
def validate_user(user):
    if not user:
        return False
    
    if not user.email:
        return False
    
    if not user.is_active:
        return False
    
    return True
```

## 🔄 持續改善流程

### 月度回顧
1. 分析新增的程式碼品質問題
2. 更新最佳實踐指南
3. 檢討工具配置是否需要調整
4. 團隊分享改善經驗

### 季度更新
1. 評估新的 linting 規則
2. 更新開發工具版本
3. 檢討程式碼標準的有效性
4. 培訓新加入的開發者

### 年度審查
1. 全面檢討編碼標準
2. 評估程式碼品質趨勢
3. 制定下一年改善目標
4. 工具鏈升級規劃

## 🎓 學習資源

### 推薦閱讀
- [PEP 8 -- Style Guide for Python Code](https://pep.python.org/pep-0008/)
- [Ruff 官方文檔](https://docs.astral.sh/ruff/)
- [Black 程式碼格式化指南](https://black.readthedocs.io/)

### 實用工具
- [Python AST Explorer](https://python-ast-explorer.com/) - 理解 AST 結構
- [Ruff Playground](https://play.ruff.rs/) - 測試 Ruff 規則
- [MyPy Playground](https://mypy-play.net/) - 類型檢查測試

---

## 📝 版本資訊

- **建立日期**: 2025-06-27
- **版本**: v1.0
- **基於**: 105 → 0 錯誤修復經驗
- **適用範圍**: LINE MCP 專案及相關 Python 代碼庫
- **下次更新**: 2025-09-27 (季度回顧)

---

*本準則是活文檔，將根據專案發展和最佳實踐演進持續更新。所有開發者都有責任遵循並改善這些標準。*