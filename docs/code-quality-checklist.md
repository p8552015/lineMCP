# 程式碼品質檢查清單

## 📋 開發者每日檢查清單

### 提交前必做事項
- [ ] 執行 `./scripts/fix-code-quality.sh` 自動修復
- [ ] 確認所有 E501 行長度錯誤已修復
- [ ] 檢查異常類別名稱是否以 "Error" 結尾
- [ ] 移除未使用的導入 (F401)
- [ ] 修復導入順序問題 (E402)

### 程式碼審查重點

#### 1. 行長度控制 (E501)
```python
# ❌ 錯誤：超過 88 字符
logger.info(f"很長的日誌訊息包含很多參數 {param1} 和 {param2} 以及 {param3}")

# ✅ 正確：適當分行
logger.info(
    f"很長的日誌訊息包含很多參數 {param1} "
    f"和 {param2} 以及 {param3}"
)
```

#### 2. 異常命名規範 (N818)
```python
# ❌ 錯誤：缺少 Error 後綴
class ValidationException(Exception):
    pass

# ✅ 正確：添加 Error 後綴
class ValidationError(Exception):
    pass
```

#### 3. 異常處理最佳實踐 (B904)
```python
# ❌ 錯誤：裸露異常重新拋出
except Exception as e:
    raise SomeError("失敗")

# ✅ 正確：保留原始異常鏈
except Exception as e:
    raise SomeError("失敗") from e
```

### Pull Request 檢查項目

- [ ] CI/CD 管道全部通過
- [ ] 程式碼覆蓋率沒有下降
- [ ] 新增異常類別名稱正確
- [ ] 長字符串已適當分割
- [ ] 複雜條件已簡化 (SIM102)
- [ ] 函數參數預設值避免可變對象 (B008)

## 🛠️ 工具使用指南

### 快速修復命令
```bash
# 自動修復所有可修復問題
./scripts/fix-code-quality.sh

# 手動步驟
cd apps/bot
poetry run ruff check src/ --fix
poetry run black src/
poetry run mypy src/
```

### 錯誤統計查看
```bash
cd apps/bot
poetry run ruff check src/ --statistics
```

### Pre-commit Hooks 測試
```bash
pre-commit run --all-files
```

## 📊 當前狀態 (2025-06-27)

### 修復進度
- ✅ **N818 異常命名錯誤**: 10/10 (100%)
- 🔄 **E501 行長度錯誤**: 12/37 (32%)
- 🔄 **B904 異常處理錯誤**: 0/15 (0%)
- 🔄 **其他錯誤**: 部分修復

### 優先級排序
1. **高優先級**: E501 (阻止 CI 通過)
2. **中優先級**: B904 (代碼安全性)
3. **低優先級**: SIM102 (代碼簡化)

## ⚠️ 常見陷阱

1. **字符串分割錯誤**: 確保引號正確關閉
2. **f-string 語法錯誤**: 注意 `{` 和 `}` 的匹配
3. **導入循環依賴**: 檢查導入順序
4. **異常鏈中斷**: 使用 `from e` 保留異常信息

## 🎯 團隊目標

- **短期目標** (本週): 修復所有 E501 錯誤
- **中期目標** (本月): 達到 < 10 個總錯誤
- **長期目標** (季度): 建立零錯誤維護機制