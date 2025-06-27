#!/bin/bash
set -e

echo "🔧 開始自動修復程式碼品質問題..."

# 切換到正確的目錄
cd "$(dirname "$0")/.."

# 檢查 poetry 是否可用
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry 未安裝或不在 PATH 中"
    exit 1
fi

# 進入 bot 應用目錄
cd apps/bot

echo "📁 當前工作目錄: $(pwd)"

# 1. 自動修復 Ruff 可修復的問題
echo "📝 步驟 1: 修復 Ruff 問題..."
if poetry run ruff check src/ --fix; then
    echo "✅ Ruff 自動修復完成"
else
    echo "⚠️  Ruff 修復過程中發現無法自動修復的問題"
fi

# 2. Black 格式化
echo "🎨 步驟 2: 執行 Black 格式化..."
if poetry run black src/; then
    echo "✅ Black 格式化完成"
else
    echo "❌ Black 格式化失敗"
    exit 1
fi

# 3. 顯示剩餘問題統計
echo "📊 步驟 3: 檢查剩餘問題..."
echo "=================================="
poetry run ruff check src/ --statistics || true

# 4. 最終詳細檢查
echo ""
echo "🔍 步驟 4: 最終詳細檢查..."
echo "=================================="
if poetry run ruff check src/; then
    echo "🎉 所有 Ruff 檢查通過！"
else
    echo "⚠️  仍有需要手動修復的問題，請查看上方輸出"
fi

# 5. MyPy 類型檢查
echo ""
echo "🏷️  步驟 5: MyPy 類型檢查..."
echo "=================================="
if poetry run mypy src/ --ignore-missing-imports; then
    echo "✅ MyPy 類型檢查通過"
else
    echo "⚠️  MyPy 發現類型問題，但不影響程式運行"
fi

echo ""
echo "🎉 程式碼品質修復腳本執行完成！"
echo "💡 建議: 請檢查上方輸出，手動修復剩餘問題"