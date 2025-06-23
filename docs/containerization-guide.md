# 🐳 容器化部署指南

本文檔說明 LINE MCP Bot 的 Docker 容器化架構和部署方案。

## 📋 容器化概覽

### 🏗️ 多階段建構架構

```mermaid
graph TD
    A[Base Dependencies] --> B[Dependencies Builder]
    B --> C[Development Dependencies]
    B --> D[Application Builder]
    D --> E[Production Runtime]
    C --> F[Development Runtime]
    C --> G[Testing Runtime]
    
    E --> H[生產部署]
    F --> I[開發環境]
    G --> J[CI/CD 測試]
```

### 🎯 優化特色

- **🔒 安全性**: 非 root 用戶、最小權限原則
- **📦 體積優化**: 多階段建構、最小化依賴
- **⚡ 快取優化**: 分層快取、GitHub Actions 整合
- **🛡️ 安全掃描**: Trivy、Hadolint、Dockle 整合
- **🔄 多環境支援**: 生產、開發、測試環境

## 🏗️ Dockerfile 架構

### Stage 1: Base Dependencies
```dockerfile
FROM python:3.11-slim-bookworm AS base
# 建立非 root 用戶
# 安裝最小系統依賴
# 配置 Poetry 環境
```

### Stage 2: Dependencies Builder
```dockerfile
FROM base AS deps-builder
# 安裝生產依賴
# 清理快取
```

### Stage 3: Application Builder
```dockerfile
FROM deps-builder AS app-builder
# 複製應用程式碼
# 建構應用
```

### Stage 4: Production Runtime
```dockerfile
FROM python:3.11-slim-bookworm AS production
# 最小運行時環境
# 安全配置
# 健康檢查
```

## 🚀 部署方式

### 1. 單容器部署

```bash
# 建構映像
docker build -f apps/bot/Dockerfile.optimized --target production -t line-mcp-bot .

# 運行容器
docker run -d \
  --name line-mcp-bot \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  line-mcp-bot
```

### 2. Docker Compose 部署

#### 生產環境
```bash
# 使用優化配置
docker-compose -f docker-compose.optimized.yml up -d

# 檢查狀態
docker-compose -f docker-compose.optimized.yml ps
```

#### 開發環境
```bash
# 啟動開發模式
docker-compose -f docker-compose.optimized.yml --profile development up -d

# 熱重載開發
docker-compose -f docker-compose.optimized.yml exec line-mcp-bot-dev bash
```

#### 測試環境
```bash
# 運行測試
docker-compose -f docker-compose.optimized.yml --profile testing run --rm line-mcp-bot-test
```

### 3. 腳本化部署

```bash
# 使用優化腳本
./scripts/docker-optimize.sh v1.0.0 production

# 開發建構
./scripts/docker-optimize.sh latest development

# 完整建構（所有環境）
./scripts/docker-optimize.sh v1.0.0 all
```

## 🔧 配置管理

### 環境變數配置

```bash
# 建立環境檔案
cp .env.example .env

# 編輯配置
vi .env
```

### 必要環境變數

```bash
# LINE Bot 配置
LINE_CHANNEL_ACCESS_TOKEN=your_token
LINE_CHANNEL_SECRET=your_secret

# AI 模型配置
GOOGLE_API_KEY=your_google_key
OPENAI_API_KEY=your_openai_key

# 資料庫配置
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://redis:6379/0

# 應用配置
LOG_LEVEL=INFO
ENVIRONMENT=production
WORKERS=1
```

### Docker Compose 變數

```bash
# 服務端口
APP_PORT=8000
POSTGRES_PORT=5432
REDIS_PORT=6379

# 安全配置
POSTGRES_PASSWORD=secure_password
GRAFANA_PASSWORD=admin_password

# 域名配置
DOMAIN=your-domain.com
```

## 🔒 安全配置

### 1. 非 root 用戶

```dockerfile
# 建立專用用戶
ARG APP_USER=appuser
ARG APP_UID=1000
ARG APP_GID=1000

RUN groupadd -g ${APP_GID} ${APP_USER} && \
    useradd -u ${APP_UID} -g ${APP_GID} -m -s /bin/bash ${APP_USER}

# 切換到非特權用戶
USER ${APP_USER}
```

### 2. 文件權限

```dockerfile
# 設定正確權限
COPY --chown=${APP_USER}:${APP_USER} src/ ./src/
RUN chown -R ${APP_USER}:${APP_USER} /app
```

### 3. 最小化攻擊面

```dockerfile
# 清理不必要文件
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /tmp/* && \
    rm -rf /var/tmp/*
```

### 4. 安全掃描

```bash
# Trivy 漏洞掃描
trivy image line-mcp-bot:latest

# Hadolint Dockerfile 檢查
hadolint apps/bot/Dockerfile.optimized

# Dockle 最佳實踐檢查
dockle line-mcp-bot:latest
```

## 📊 效能優化

### 1. 建構快取

```dockerfile
# 分層快取優化
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-dev

# 程式碼變更不影響依賴快取
COPY src/ ./src/
```

### 2. 映像大小優化

```bash
# 使用 .dockerignore
echo "*.md" >> .dockerignore
echo ".git/" >> .dockerignore
echo "tests/" >> .dockerignore

# 多階段建構
docker build --target production -t line-mcp-bot .
```

### 3. 啟動優化

```dockerfile
# 使用 tini 處理信號
ENTRYPOINT ["/usr/bin/tini", "--"]

# 優化啟動命令
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

## 🔍 監控與日誌

### 1. 健康檢查

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

### 2. 日誌配置

```yaml
# Docker Compose 日誌
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 3. 指標收集

```yaml
# Prometheus 監控
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
```

## 🛠️ 開發工作流程

### 1. 本地開發

```bash
# 建構開發映像
docker build -f apps/bot/Dockerfile.optimized --target development -t line-mcp-bot:dev apps/bot

# 啟動開發容器
docker run -it --rm \
  -v $(pwd)/apps/bot:/app \
  -p 8000:8000 \
  line-mcp-bot:dev
```

### 2. 測試環境

```bash
# 運行測試
docker build -f apps/bot/Dockerfile.optimized --target testing -t line-mcp-bot:test apps/bot
docker run --rm line-mcp-bot:test
```

### 3. CI/CD 整合

```yaml
# GitHub Actions
- name: Build and Test
  uses: docker/build-push-action@v5
  with:
    context: ./apps/bot
    file: ./apps/bot/Dockerfile.optimized
    target: testing
    load: true
    tags: test-image:latest
```

## 🔧 故障排除

### 常見問題

#### 1. 權限問題
```bash
# 檢查用戶 ID
docker exec container-name id

# 修復權限
docker exec container-name chown -R appuser:appuser /app
```

#### 2. 網路問題
```bash
# 檢查網路連接
docker network ls
docker network inspect line-mcp-network
```

#### 3. 依賴問題
```bash
# 重新建構清除快取
docker build --no-cache -f apps/bot/Dockerfile.optimized --target production -t line-mcp-bot apps/bot
```

#### 4. 記憶體問題
```bash
# 檢查資源使用
docker stats container-name

# 限制記憶體使用
docker run -m 512m line-mcp-bot
```

### 除錯技巧

```bash
# 進入容器除錯
docker exec -it container-name bash

# 查看日誌
docker logs -f container-name

# 檢查健康狀態
docker inspect container-name | jq '.[0].State.Health'
```

## 📈 最佳實踐

### 1. 映像標籤策略
- `latest`: 最新穩定版本
- `v1.2.3`: 語義化版本
- `main`: 主分支最新建構
- `pr-123`: Pull Request 建構

### 2. 環境隔離
- 生產: 獨立的 Docker Compose 配置
- 測試: 專用網路和數據卷
- 開發: 本地掛載和熱重載

### 3. 安全原則
- 定期更新基礎映像
- 掃描已知漏洞
- 最小權限運行
- 祕密管理外部化

### 4. 監控指標
- 容器健康狀態
- 資源使用情況
- 應用效能指標
- 安全事件記錄

---

## 📚 參考資源

- [Docker 最佳實踐](https://docs.docker.com/develop/dev-best-practices/)
- [多階段建構指南](https://docs.docker.com/build/building/multi-stage/)
- [Docker 安全指南](https://docs.docker.com/engine/security/)
- [容器映像掃描](https://docs.docker.com/engine/scan/)

---

*最後更新：2025-06-23*