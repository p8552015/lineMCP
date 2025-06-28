# Pre-commit 配置修復紀錄

## 修復日期
2025-06-28

## 問題分析
1. **types-all 依賴問題**: types-pkg-resources 套件不存在導致 mypy 安裝失敗
2. **ruff 版本問題**: pyproject.toml 使用新語法 `[tool.ruff.lint]` 但 pre-commit 使用舊版本
3. **config 模組衝突**: config.py 檔案和 config/ 目錄同時存在導致 mypy 報錯
4. **程式碼格式問題**: 44個檔案需要 Black 格式化
5. **行長度問題**: 105個行長度超過88字元限制

## 修復步驟

### 1. 修復 types-all 依賴
```yaml
# .pre-commit-config.yaml
# 原本：
additional_dependencies: [types-all]
# 修改為：
additional_dependencies: [
  types-requests,
  types-PyYAML,
  types-python-jose,
  types-redis,
  types-aiofiles
]
```

### 2. 更新 ruff 版本
```yaml
# .pre-commit-config.yaml
# 原本：
rev: v0.0.270
# 修改為：
rev: v0.7.0
```

### 3. 修復 pyproject.toml 的 ruff 配置
```toml
# 原本：
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "PT", "SIM"]

# 修改為：
[tool.ruff]
line-length = 88
target-version = "py311"
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "PT", "SIM"]
```

### 4. 解決 config 模組衝突
- 將 `config.py` 重新命名為 `settings.py`
- 更新所有相關 import 語句

### 5. 執行格式化
```bash
# 清理 pre-commit 快取
pre-commit clean

# 重新安裝 hooks
pre-commit install

# 執行 Black 格式化
cd apps/bot && poetry run black src/

# 嘗試修復 ruff 問題
poetry run ruff check src/ --fix
```

## 仍需處理的問題

### 1. MyPy 缺少類型定義
需要在 pyproject.toml 中添加更多類型依賴：
- types-structlog
- types-linebot
- types-fastapi
- types-prometheus-client
- types-psutil

### 2. 行長度問題
105個行長度超過88字元的問題需要手動修復，主要是：
- 錯誤訊息字串過長
- 日誌訊息過長
- 條件判斷表達式過長

## 建議的長期解決方案

1. **設置 VS Code 格式化**：
   - 安裝 Black 和 Ruff 擴展
   - 設置儲存時自動格式化
   - 設置 88 字元標尺

2. **CI/CD 整合**：
   - 在 GitHub Actions 中加入 pre-commit 檢查
   - 設置為 PR 必須通過的檢查

3. **團隊規範**：
   - 制定程式碼風格指南
   - 定期程式碼審查
   - 新成員培訓