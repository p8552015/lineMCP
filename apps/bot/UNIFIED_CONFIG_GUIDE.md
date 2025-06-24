# 統一配置管理指南

## 概述

本專案已實施統一配置管理，將原本分散的 YAML 配置文件整合到 `mcp_config.py` 中，支援環境變數覆蓋，實現更靈活的配置管理。

## 配置層級（優先級由高到低）

1. **環境變數** - 最高優先級，適用於生產環境
2. **YAML 配置文件** - 中等優先級，向後兼容
3. **程式碼預設值** - 最低優先級，保證基本功能

## NL-to-SQL 配置

### 環境變數配置

所有 NL-to-SQL 相關環境變數都使用 `NL_TO_SQL_` 前綴：

```bash
# 解析器設定
export NL_TO_SQL_CONFIDENCE_THRESHOLD=0.7
export NL_TO_SQL_MAX_PARSE_TIME=6000
export NL_TO_SQL_VERBOSE_LOGGING=true

# 並行解析設定
export NL_TO_SQL_PARALLEL_PARSING=true
export NL_TO_SQL_MAX_CONCURRENT_PARSERS=3
export NL_TO_SQL_TIMEOUT_PER_PARSER=2000

# 解析器權重
export NL_TO_SQL_RULE_PARSER_WEIGHT=1.0
export NL_TO_SQL_AI_PARSER_WEIGHT=1.2

# 回退策略
export NL_TO_SQL_FALLBACK_ENABLED=true
export NL_TO_SQL_FALLBACK_THRESHOLD=0.5

# AI 服務設定
export NL_TO_SQL_AI_TIMEOUT=3000
export NL_TO_SQL_AI_MAX_RETRIES=2

# 快取設定
export NL_TO_SQL_CACHE_ENABLED=true
export NL_TO_SQL_CACHE_SIZE=1000
export NL_TO_SQL_CACHE_TTL=300

# 統計設定
export NL_TO_SQL_STATISTICS_ENABLED=true

# 熱重載設定
export NL_TO_SQL_HOT_RELOAD=false
```

### 程式碼使用範例

```python
from src.config.mcp_config import get_nl_to_sql_config, get_nl_to_sql_config_dict

# 獲取配置物件
config = get_nl_to_sql_config()
print(f"信心度門檻: {config.default_confidence_threshold}")
print(f"最大解析時間: {config.max_parse_time}ms")

# 獲取配置字典
config_dict = get_nl_to_sql_config_dict()
print(f"並行解析啟用: {config_dict['parallel_parsing_enabled']}")

# 動態更新配置
from src.config.mcp_config import update_nl_to_sql_config
update_nl_to_sql_config(
    default_confidence_threshold=0.8,
    max_parse_time=7000
)
```

### 配置項說明

| 配置項 | 預設值 | 說明 |
|--------|--------|------|
| `default_confidence_threshold` | 0.5 | 解析器信心度門檻 |
| `max_parse_time` | 5000 | 最大解析時間（毫秒） |
| `verbose_logging` | true | 啟用詳細日誌 |
| `parallel_parsing_enabled` | true | 啟用並行解析 |
| `max_concurrent_parsers` | 3 | 最大並行解析器數量 |
| `timeout_per_parser` | 2000 | 每個解析器超時時間（毫秒） |
| `rule_based_parser_weight` | 1.0 | 規則解析器權重 |
| `ai_enhanced_parser_weight` | 1.2 | AI 解析器權重 |
| `fallback_strategy_enabled` | true | 啟用回退策略 |
| `fallback_threshold` | 0.5 | 回退策略信心度門檻 |
| `ai_service_timeout` | 3000 | AI 服務超時時間（毫秒） |
| `ai_service_max_retries` | 2 | AI 服務最大重試次數 |
| `cache_enabled` | true | 啟用快取 |
| `cache_size` | 1000 | 快取大小 |
| `cache_ttl` | 300 | 快取生存時間（秒） |
| `statistics_enabled` | true | 啟用統計 |
| `hot_reload_enabled` | false | 啟用熱重載 |

## 統一配置摘要

可以使用以下方式獲取完整的配置摘要：

```python
from src.config.mcp_config import get_mcp_config

config_manager = get_mcp_config()
summary = config_manager.get_config_summary()

print("=== 配置摘要 ===")
print(f"MCP 服務器數量: {len(summary['servers'])}")
print(f"NL-to-SQL 信心度門檻: {summary['nl_to_sql']['confidence_threshold']}")
print(f"並行解析啟用: {summary['nl_to_sql']['parallel_parsing']}")
print(f"快取啟用: {summary['nl_to_sql']['cache_enabled']}")
```

## 向後兼容性

統一配置管理完全向後兼容：
- 現有的 YAML 配置文件仍會被讀取
- 環境變數會覆蓋 YAML 配置
- 未設置的配置項會使用合理的預設值

## 最佳實踐

### 開發環境
- 使用程式碼預設值或 YAML 文件
- 啟用詳細日誌和統計

### 生產環境
- 使用環境變數覆蓋關鍵配置
- 調整超時時間和重試次數
- 關閉詳細日誌以提升效能

### 容器化部署
```dockerfile
# Dockerfile 範例
ENV NL_TO_SQL_CONFIDENCE_THRESHOLD=0.7
ENV NL_TO_SQL_MAX_PARSE_TIME=6000
ENV NL_TO_SQL_VERBOSE_LOGGING=false
ENV NL_TO_SQL_CACHE_SIZE=2000
```

### Docker Compose
```yaml
# docker-compose.yml 範例
services:
  line-bot:
    environment:
      - NL_TO_SQL_CONFIDENCE_THRESHOLD=0.7
      - NL_TO_SQL_MAX_PARSE_TIME=6000
      - NL_TO_SQL_PARALLEL_PARSING=true
      - NL_TO_SQL_STATISTICS_ENABLED=true
```

## 配置驗證

配置管理器提供內建的驗證功能：

```python
from src.config.mcp_config import get_mcp_config

config_manager = get_mcp_config()

# 驗證 MCP 服務器配置
is_valid, error_msg = config_manager.validate_server_config("sqlite")
if not is_valid:
    print(f"配置錯誤: {error_msg}")

# 驗證配置完整性
summary = config_manager.get_config_summary()
if summary['nl_to_sql']['confidence_threshold'] < 0 or summary['nl_to_sql']['confidence_threshold'] > 1:
    print("警告: 信心度門檻超出有效範圍")
```

## 故障排除

### 常見問題

1. **環境變數不生效**
   - 確保環境變數名稱正確（包含 `NL_TO_SQL_` 前綴）
   - 檢查值的格式（布林值使用 'true'/'false'，數值使用純數字）

2. **配置重置**
   ```python
   # 重置為預設配置
   from src.config.mcp_config import get_mcp_config
   config_manager = get_mcp_config()
   config_manager._nl_to_sql_config = NLToSQLConfig()
   ```

3. **配置調試**
   ```python
   # 查看當前所有配置
   config_dict = get_nl_to_sql_config_dict()
   import json
   print(json.dumps(config_dict, indent=2))
   ```

---

**更新時間**: 2025-06-23  
**負責人**: Claude  
**狀態**: ✅ 完成