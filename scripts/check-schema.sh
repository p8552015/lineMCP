#!/bin/bash

# Schema 一致性檢查便捷腳本

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 專案根目錄
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECKER_SCRIPT="$PROJECT_ROOT/scripts/schema-consistency-checker.py"
SCHEMA_FILE="$PROJECT_ROOT/schema/expected-schema.json"

# 預設資料庫 URL
DEFAULT_DB_URL="postgresql://admin:admin@localhost:5432/mydb"

# 使用說明
usage() {
    echo -e "${BLUE}Schema 一致性檢查工具${NC}"
    echo ""
    echo "使用方式:"
    echo "  $0 [OPTIONS] [DATABASE_URL]"
    echo ""
    echo "選項:"
    echo "  -h, --help     顯示此說明"
    echo "  -v, --verbose  詳細輸出模式"
    echo "  -q, --quiet    安靜模式（僅顯示結果）"
    echo "  -f, --format   輸出格式 (text|json) [預設: text]"
    echo "  --schema FILE  指定期望 Schema 檔案路徑"
    echo ""
    echo "範例:"
    echo "  $0                                    # 使用預設資料庫 URL"
    echo "  $0 postgresql://user:pass@host/db     # 使用自訂資料庫 URL"
    echo "  $0 --verbose                          # 詳細輸出模式"
    echo "  $0 --schema /path/to/schema.json      # 使用自訂 Schema 檔案"
    echo ""
    echo "環境變數:"
    echo "  DATABASE_URL   資料庫連接 URL （優先於命令列參數）"
    echo ""
}

# 解析命令列參數
VERBOSE=false
QUIET=false
FORMAT="text"
CUSTOM_SCHEMA=""
DATABASE_URL=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -q|--quiet)
            QUIET=true
            shift
            ;;
        -f|--format)
            FORMAT="$2"
            shift 2
            ;;
        --schema)
            CUSTOM_SCHEMA="$2"
            shift 2
            ;;
        -*)
            echo -e "${RED}錯誤: 未知選項 $1${NC}" >&2
            usage
            exit 1
            ;;
        *)
            DATABASE_URL="$1"
            shift
            ;;
    esac
done

# 檢查必要檔案
if [[ ! -f "$CHECKER_SCRIPT" ]]; then
    echo -e "${RED}❌ 錯誤: Schema 檢查腳本不存在: $CHECKER_SCRIPT${NC}" >&2
    exit 1
fi

# 設定 Schema 檔案路徑
SCHEMA_PATH="${CUSTOM_SCHEMA:-$SCHEMA_FILE}"
if [[ ! -f "$SCHEMA_PATH" ]]; then
    echo -e "${RED}❌ 錯誤: Schema 定義檔案不存在: $SCHEMA_PATH${NC}" >&2
    exit 1
fi

# 設定資料庫 URL
if [[ -n "$DATABASE_URL_ENV" ]]; then
    DATABASE_URL="$DATABASE_URL_ENV"
elif [[ -z "$DATABASE_URL" ]]; then
    DATABASE_URL="$DEFAULT_DB_URL"
fi

# 檢查 Python 環境
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 錯誤: 找不到 python3 命令${NC}" >&2
    exit 1
fi

# 檢查必要的 Python 模組
if ! python3 -c "import asyncpg, json" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  警告: 缺少必要的 Python 模組 (asyncpg)${NC}" >&2
    echo -e "${BLUE}💡 安裝方式: pip install asyncpg${NC}" >&2
fi

# 執行檢查
echo -e "${BLUE}🔍 開始 Schema 一致性檢查...${NC}"
if [[ "$VERBOSE" == true ]]; then
    echo -e "${BLUE}📋 資料庫 URL: $DATABASE_URL${NC}"
    echo -e "${BLUE}📋 Schema 檔案: $SCHEMA_PATH${NC}"
fi

# 設定輸出重導向
if [[ "$QUIET" == true ]]; then
    PYTHON_OUTPUT="/tmp/schema-check-$$"
else
    PYTHON_OUTPUT="/dev/stdout"
fi

# 執行 Python 檢查腳本
if python3 "$CHECKER_SCRIPT" "$DATABASE_URL" "$SCHEMA_PATH" > "$PYTHON_OUTPUT" 2>&1; then
    RESULT_CODE=0
    if [[ "$QUIET" == true ]]; then
        echo -e "${GREEN}✅ Schema 一致性檢查通過${NC}"
    fi
else
    RESULT_CODE=$?
    if [[ "$QUIET" == true ]]; then
        echo -e "${RED}❌ Schema 一致性檢查失敗${NC}"
        echo ""
        cat "$PYTHON_OUTPUT"
    fi
fi

# 清理臨時檔案
if [[ "$QUIET" == true ]] && [[ -f "$PYTHON_OUTPUT" ]]; then
    rm -f "$PYTHON_OUTPUT"
fi

# 根據結果顯示建議
if [[ $RESULT_CODE -eq 0 ]]; then
    if [[ "$VERBOSE" == true ]]; then
        echo -e "${GREEN}🎉 所有檢查都通過了！${NC}"
        echo -e "${BLUE}💡 建議: 將此檢查整合到 CI/CD 流程中${NC}"
    fi
else
    echo ""
    echo -e "${YELLOW}🔧 修復建議:${NC}"
    echo -e "${BLUE}1. 檢查上述錯誤訊息並修復 Schema 不一致問題${NC}"
    echo -e "${BLUE}2. 更新資料庫 Schema 或期望規範檔案${NC}"
    echo -e "${BLUE}3. 重新執行檢查確認修復結果${NC}"
    echo ""
    echo -e "${BLUE}🚀 快速修復指令:${NC}"
    echo -e "${BLUE}   # 檢視具體錯誤: $0 --verbose${NC}"
    echo -e "${BLUE}   # 更新 Schema: 編輯 $SCHEMA_PATH${NC}"
fi

exit $RESULT_CODE