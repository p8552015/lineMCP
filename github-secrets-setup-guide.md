# 🔐 GitHub Secrets 設置完整指引

## 📋 快速設置清單

### 必要 Secrets (優先級：🔴 高)
```bash
LINE_CHANNEL_ACCESS_TOKEN    # LINE Bot 存取權杖
LINE_CHANNEL_SECRET         # LINE Bot 頻道密鑰  
GOOGLE_API_KEY              # Google Gemini API 金鑰
OPENAI_API_KEY              # OpenAI API 金鑰 (備用)
JWT_SECRET_KEY              # JWT 簽名密鑰
```

### 選用 Secrets (優先級：🟡 中)
```bash
REDIS_PASSWORD              # Redis 密碼 (如使用認證)
OTEL_EXPORTER_OTLP_ENDPOINT # 可觀測性服務端點
```

## 🛠️ 設置步驟

### 第一步：進入 GitHub 設定
1. 前往: `https://github.com/p8552015/lineMCP/settings`
2. 點選左側選單: `Secrets and variables` → `Actions`

### 第二步：新增 Repository Secrets
點擊 `New repository secret`，依序新增：

| 名稱 | 來源 | 注意事項 |
|------|------|----------|
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Developers Console | 長期有效，需妥善保管 |
| `LINE_CHANNEL_SECRET` | LINE Developers Console | 用於簽名驗證 |
| `GOOGLE_API_KEY` | Google Cloud Console | 15M 免費額度/月 |
| `OPENAI_API_KEY` | OpenAI Platform | 備用模型，按使用付費 |
| `JWT_SECRET_KEY` | 自行生成 | 至少32字元隨機字串 |

### 第三步：JWT Secret 生成範例
```bash
# 生成安全的 JWT Secret (32字元)
openssl rand -base64 32

# 或使用 Python
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 🔧 GitHub Actions 中的使用方式

### 基本用法
```yaml
steps:
  - name: Setup environment
    env:
      LINE_CHANNEL_ACCESS_TOKEN: ${{ secrets.LINE_CHANNEL_ACCESS_TOKEN }}
      GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
    run: |
      echo "Environment configured"
```

### 進階用法：環境別管理
```yaml
env:
  # 根據分支選擇不同環境的金鑰
  GOOGLE_API_KEY: ${{ 
    github.ref == 'refs/heads/main' && secrets.GOOGLE_API_KEY_PROD || 
    secrets.GOOGLE_API_KEY_DEV 
  }}
  LINE_CHANNEL_ACCESS_TOKEN: ${{ 
    github.ref == 'refs/heads/main' && secrets.LINE_TOKEN_PROD || 
    secrets.LINE_TOKEN_DEV 
  }}
```

## ⚠️ 安全最佳實踐

### 🔴 高風險操作 - 避免
- ❌ 在日誌中輸出 Secrets 值
- ❌ 將 Secrets 作為參數傳遞
- ❌ 在 Pull Request 中暴露 Secrets

### ✅ 推薦作法
- ✅ 使用環境變數方式引用
- ✅ 定期輪換金鑰
- ✅ 實施最小權限原則
- ✅ 監控 API 使用情況

### 🛡️ 防護機制
```yaml
# 防止 Secrets 洩漏的檢查
- name: Security Check
  run: |
    if echo "$GOOGLE_API_KEY" | grep -q "AIza"; then
      echo "::error::Potential API key exposure detected"
      exit 1
    fi
  env:
    GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
```

## 🚀 進階功能

### 1. 條件式 Secrets 使用
```yaml
- name: Production Deploy
  if: github.ref == 'refs/heads/main'
  env:
    PROD_API_KEY: ${{ secrets.GOOGLE_API_KEY_PROD }}
  run: ./deploy-prod.sh
```

### 2. Secrets 驗證
```yaml
- name: Validate Secrets
  run: |
    if [ -z "$LINE_CHANNEL_ACCESS_TOKEN" ]; then
      echo "::error::LINE_CHANNEL_ACCESS_TOKEN not set"
      exit 1
    fi
    if [ ${#JWT_SECRET_KEY} -lt 32 ]; then
      echo "::error::JWT_SECRET_KEY too short"
      exit 1
    fi
  env:
    LINE_CHANNEL_ACCESS_TOKEN: ${{ secrets.LINE_CHANNEL_ACCESS_TOKEN }}
    JWT_SECRET_KEY: ${{ secrets.JWT_SECRET_KEY }}
```

### 3. 動態環境配置
```yaml
jobs:
  test:
    strategy:
      matrix:
        environment: [dev, staging, prod]
    steps:
      - name: Configure Environment
        env:
          API_KEY: ${{ secrets[format('GOOGLE_API_KEY_{0}', matrix.environment)] }}
        run: echo "Configured for ${{ matrix.environment }}"
```

## 📊 監控與維護

### 金鑰使用監控
1. **API 配額監控** - 設置 Google Cloud/OpenAI 用量告警
2. **存取日誌** - 定期檢查 API 金鑰使用記錄
3. **異常偵測** - 監控非預期的高用量或錯誤率

### 定期維護檢查清單
- [ ] 每季度輪換 JWT_SECRET_KEY
- [ ] 每半年檢查 API 金鑰權限
- [ ] 每年更新 LINE Bot 權杖
- [ ] 定期備份重要配置

## 🎯 完成後驗證

### 驗證 Secrets 設置
1. 進入 Actions 頁面檢查工作流程執行
2. 確認沒有 "Secret not found" 錯誤
3. 測試實際 API 呼叫功能

### 安全檢查
```bash
# 本地檢查是否有硬編碼金鑰
git log --all -p | grep -i -E "(api[_-]?key|secret|token|password)" | grep -v "your_"
```

---

**📝 注意**: 設置完成後，原本的 `.env` 檔案中的敏感資訊應該移除或註解，僅保留範例值。