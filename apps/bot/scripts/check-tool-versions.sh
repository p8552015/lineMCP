#!/bin/bash

# 工具版本一致性檢查腳本
# 檢查 Pre-commit 與 Poetry 中各工具版本是否一致

set -e

echo "🔍 開始檢查工具版本一致性..."

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 錯誤計數
ERRORS=0

# 檢查 Black 版本
echo "📝 檢查 Black 版本一致性..."
BLACK_PRECOMMIT=$(grep -A1 "repo.*black" .pre-commit-config.yaml | grep "rev:" | sed 's/.*rev: //' | tr -d ' ')
BLACK_POETRY=$(grep "black.*=" apps/bot/pyproject.toml | sed 's/.*"\^//' | sed 's/".*//')

echo "   Pre-commit Black 版本: $BLACK_PRECOMMIT"
echo "   Poetry Black 版本: ^$BLACK_POETRY"

if [ "$BLACK_PRECOMMIT" != "$BLACK_POETRY" ]; then
    echo -e "   ${RED}❌ Black版本不一致${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "   ${GREEN}✅ Black版本一致${NC}"
fi

# 檢查 Ruff 版本
echo ""
echo "🔧 檢查 Ruff 版本一致性..."
RUFF_PRECOMMIT=$(grep -A1 "repo.*ruff" .pre-commit-config.yaml | grep "rev:" | sed 's/.*rev: v//' | tr -d ' ')
RUFF_POETRY=$(grep "ruff.*=" apps/bot/pyproject.toml | sed 's/.*"\^//' | sed 's/".*//')

echo "   Pre-commit Ruff 版本: v$RUFF_PRECOMMIT"
echo "   Poetry Ruff 版本: ^$RUFF_POETRY"

if [ "$RUFF_PRECOMMIT" != "$RUFF_POETRY" ]; then
    echo -e "   ${RED}❌ Ruff版本不一致${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "   ${GREEN}✅ Ruff版本一致${NC}"
fi

# 檢查 MyPy 版本
echo ""
echo "🔬 檢查 MyPy 版本一致性..."
MYPY_PRECOMMIT=$(grep -A1 "repo.*mypy" .pre-commit-config.yaml | grep "rev:" | sed 's/.*rev: v//' | tr -d ' ')
MYPY_POETRY=$(grep "mypy.*=" apps/bot/pyproject.toml | sed 's/.*"\^//' | sed 's/".*//')

echo "   Pre-commit MyPy 版本: v$MYPY_PRECOMMIT"
echo "   Poetry MyPy 版本: ^$MYPY_POETRY"

if [ "$MYPY_PRECOMMIT" != "$MYPY_POETRY" ]; then
    echo -e "   ${RED}❌ MyPy版本不一致${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "   ${GREEN}✅ MyPy版本一致${NC}"
fi

# 總結報告
echo ""
echo "📊 版本一致性檢查總結:"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}🎉 所有工具版本都一致！${NC}"
    exit 0
else
    echo -e "${RED}💥 發現 $ERRORS 個版本不一致問題${NC}"
    echo ""
    echo "🛠️  修復建議:"
    echo "1. 更新 .pre-commit-config.yaml 中的版本"
    echo "2. 或更新 apps/bot/pyproject.toml 中的版本"
    echo "3. 執行 poetry update 同步依賴"
    echo "4. 執行 pre-commit autoupdate 更新 hooks"
    exit 1
fi