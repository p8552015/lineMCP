#!/bin/bash

# MyPy CI 檢查腳本
# 確保類型錯誤不會增加

set -e

echo "🔍 MyPy CI 類型檢查..."

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 讀取基準線
if [ -f ".mypy-baseline" ]; then
    BASELINE=$(cat .mypy-baseline)
    echo -e "📊 基準線錯誤數量: ${BASELINE}"
else
    echo -e "${YELLOW}⚠️ 未找到基準線文件，創建新的基準線${NC}"
    BASELINE=0
fi

# 執行 MyPy 檢查
echo "🔍 執行 MyPy 檢查..."
CURRENT_ERRORS=$(poetry run mypy src/ --no-error-summary 2>&1 | grep -c "error:" || echo "0")

echo -e "📊 當前錯誤數量: ${CURRENT_ERRORS}"

# 比較結果
if [ "$CURRENT_ERRORS" -eq 0 ]; then
    echo -e "${GREEN}🎉 完美！沒有類型錯誤${NC}"
    exit 0
elif [ "$CURRENT_ERRORS" -le "$BASELINE" ]; then
    IMPROVEMENT=$((BASELINE - CURRENT_ERRORS))
    if [ "$IMPROVEMENT" -gt 0 ]; then
        echo -e "${GREEN}✅ 類型品質改善！減少了 ${IMPROVEMENT} 個錯誤${NC}"
        # 更新基準線
        echo "$CURRENT_ERRORS" > .mypy-baseline
        echo -e "${GREEN}📝 基準線已更新${NC}"
    else
        echo -e "${GREEN}✅ 類型品質維持穩定${NC}"
    fi
    exit 0
else
    REGRESSION=$((CURRENT_ERRORS - BASELINE))
    echo -e "${RED}❌ 類型品質退化！增加了 ${REGRESSION} 個錯誤${NC}"
    echo ""
    echo -e "${RED}🚫 CI 檢查失敗 - 請修復類型錯誤後再提交${NC}"
    echo ""
    echo "前 10 個錯誤："
    poetry run mypy src/ --no-error-summary 2>&1 | head -10
    exit 1
fi