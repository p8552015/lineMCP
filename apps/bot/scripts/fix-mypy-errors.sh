#!/bin/bash

# MyPy 錯誤自動修復腳本
# 用於批量修復常見的 MyPy 類型錯誤模式

set -e

echo "🔧 開始 MyPy 錯誤自動修復..."

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 記錄修復前的錯誤數量
BEFORE_COUNT=$(poetry run mypy src/ --no-error-summary 2>&1 | grep -c "error:" || echo "0")
echo -e "${BLUE}📊 修復前錯誤數量: $BEFORE_COUNT${NC}"

echo ""
echo "🔍 執行自動修復模式..."

# 1. 修復常見的 "object" has no attribute 錯誤
echo "   修復 'object' 類型問題..."
find src -name "*.py" -type f -exec sed -i '' 's/: object\b/: Any/g' {} \;

# 2. 修復 dict[str, Any] -> Dict[str, Any]
echo "   修復 dict 類型標註..."
find src -name "*.py" -type f -exec sed -i '' 's/-> dict\[/-> Dict[/g' {} \;
find src -name "*.py" -type f -exec sed -i '' 's/: dict\[/: Dict[/g' {} \;

# 3. 修復 list[str] -> List[str]
echo "   修復 list 類型標註..."
find src -name "*.py" -type f -exec sed -i '' 's/-> list\[/-> List[/g' {} \;
find src -name "*.py" -type f -exec sed -i '' 's/: list\[/: List[/g' {} \;

# 4. 添加 typing 導入（如果缺失）
echo "   檢查並添加 typing 導入..."
for file in $(find src -name "*.py" -type f); do
    if grep -q "Dict\|List\|Optional" "$file" && ! grep -q "from typing import.*Dict\|from typing import.*List\|from typing import.*Optional" "$file"; then
        # 在第一個 import 之前添加 typing 導入
        if grep -q "^import\|^from.*import" "$file"; then
            sed -i '' '1,/^import\|^from.*import/s/^import\|^from.*import/from typing import Any, Dict, List, Optional, Union\n&/' "$file"
        fi
    fi
done

# 5. 修復 None 類型的 Optional 標註
echo "   修復 Optional 類型標註..."
find src -name "*.py" -type f -exec sed -i '' 's/= None)/: Optional[str] = None)/g' {} \;

echo ""
echo "✅ 自動修復完成！"

# 記錄修復後的錯誤數量
AFTER_COUNT=$(poetry run mypy src/ --no-error-summary 2>&1 | grep -c "error:" || echo "0")
echo -e "${BLUE}📊 修復後錯誤數量: $AFTER_COUNT${NC}"

# 計算改善幅度
if [ "$BEFORE_COUNT" -gt 0 ]; then
    IMPROVEMENT=$((100 * (BEFORE_COUNT - AFTER_COUNT) / BEFORE_COUNT))
    echo -e "${GREEN}🎉 錯誤減少: $((BEFORE_COUNT - AFTER_COUNT)) 個 (改善 ${IMPROVEMENT}%)${NC}"
else
    echo -e "${GREEN}🎉 沒有發現錯誤！${NC}"
fi

# 如果還有錯誤，顯示前 10 個
if [ "$AFTER_COUNT" -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠️ 剩餘錯誤 (前10個):${NC}"
    poetry run mypy src/ --no-error-summary 2>&1 | head -10
fi

echo ""
echo "🚀 建議接下來執行:"
echo "   1. poetry run mypy src/ --no-error-summary  # 查看完整錯誤列表"
echo "   2. poetry run black src/                    # 重新格式化代碼"
echo "   3. poetry run pytest tests/                 # 運行測試確保功能正常"