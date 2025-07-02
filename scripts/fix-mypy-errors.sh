#!/bin/bash
# MyPy 類型錯誤自動修復工具
# 基於 2025-07-01 成功修復經驗開發

set -e

echo "🔧 MyPy 類型錯誤自動修復工具"
echo "================================================"
echo "📅 版本: v1.0 (基於 107→0 錯誤修復經驗)"
echo "🎯 目標: 自動修復常見 MyPy 類型錯誤"
echo

# 切換到 apps/bot 目錄
cd "$(dirname "$0")/../apps/bot" || exit 1

# 檢查初始錯誤數
echo "📊 檢查初始 MyPy 錯誤狀態..."
INITIAL_ERRORS=$(poetry run mypy src/ --no-error-summary 2>&1 | grep -c "error:" || echo "0")
echo "初始錯誤數: $INITIAL_ERRORS"

if [ "$INITIAL_ERRORS" -eq 0 ]; then
    echo "✅ 恭喜！目前沒有 MyPy 錯誤需要修復"
    exit 0
fi

echo
echo "🛠️ 開始自動修復常見錯誤類型..."

# 修復 1: 缺少 typing 導入
echo "1️⃣ 修復缺少的 typing 導入..."
find src/ -name "*.py" -exec grep -l "dict\[" {} \; | while read -r file; do
    if ! grep -q "from typing import" "$file"; then
        sed -i '' '1i\
from typing import Any
' "$file"
        echo "  ✓ 添加 typing 導入: $file"
    fi
done

# 修復 2: 可選類型參數
echo "2️⃣ 修復可選類型參數..."
find src/ -name "*.py" -exec sed -i '' 's/: str = None/: str | None = None/g' {} \;
find src/ -name "*.py" -exec sed -i '' 's/: int = None/: int | None = None/g' {} \;
find src/ -name "*.py" -exec sed -i '' 's/: bool = None/: bool | None = None/g' {} \;
find src/ -name "*.py" -exec sed -i '' 's/: dict = None/: dict[str, Any] | None = None/g' {} \;
find src/ -name "*.py" -exec sed -i '' 's/: list = None/: list[Any] | None = None/g' {} \;

# 修復 3: 空容器類型註解
echo "3️⃣ 修復空容器類型註解..."
find src/ -name "*.py" -exec sed -i '' 's/= {}/: dict[str, Any] = {}/g' {} \;
find src/ -name "*.py" -exec sed -i '' 's/= \[\]/: list[Any] = []/g' {} \;

# 修復 4: 現代 Python 類型語法
echo "4️⃣ 轉換為現代 Python 類型語法..."
find src/ -name "*.py" -exec sed -i '' 's/from typing import Optional/# from typing import Optional  # 已改用 | None/g' {} \;
find src/ -name "*.py" -exec sed -i '' 's/Optional\[\([^]]*\)\]/\1 | None/g' {} \;
find src/ -name "*.py" -exec sed -i '' 's/Dict\[\([^,]*\), \([^]]*\)\]/dict[\1, \2]/g' {} \;
find src/ -name "*.py" -exec sed -i '' 's/List\[\([^]]*\)\]/list[\1]/g' {} \;

# 修復 5: 常見的 cast 導入
echo "5️⃣ 添加 cast 導入..."
find src/ -name "*.py" -exec grep -l "cast(" {} \; | while read -r file; do
    if ! grep -q "from typing import.*cast" "$file"; then
        sed -i '' 's/from typing import \(.*\)/from typing import \1, cast/' "$file"
        echo "  ✓ 添加 cast 導入: $file"
    fi
done

echo
echo "📊 檢查修復後的錯誤狀態..."
FINAL_ERRORS=$(poetry run mypy src/ --no-error-summary 2>&1 | grep -c "error:" || echo "0")
FIXED_ERRORS=$((INITIAL_ERRORS - FINAL_ERRORS))

echo "修復前錯誤數: $INITIAL_ERRORS"
echo "修復後錯誤數: $FINAL_ERRORS"
echo "已修復錯誤數: $FIXED_ERRORS"

if [ "$FINAL_ERRORS" -lt "$INITIAL_ERRORS" ]; then
    echo "✅ 自動修復成功！減少了 $FIXED_ERRORS 個錯誤"
    echo "💾 更新基準線..."
    echo "$FINAL_ERRORS" > ../../.mypy-baseline
else
    echo "⚠️ 自動修復未能減少錯誤，可能需要手動處理"
fi

if [ "$FINAL_ERRORS" -gt 0 ]; then
    echo
    echo "📋 剩餘錯誤需要手動修復，參考指南:"
    echo "   docs/MyPy類型錯誤預防指南.md"
    echo
    echo "🔍 查看詳細錯誤:"
    echo "   poetry run mypy src/ | head -20"
fi

echo
echo "🎉 自動修復完成！"