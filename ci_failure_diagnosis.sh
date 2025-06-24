#!/bin/bash
# T-01 CI 失敗診斷分析腳本

echo "🔍 === CI 失敗診斷分析開始 ==="
echo "時間: $(date)"
echo "分支: $(git branch --show-current)"
echo ""

# 1. 檢查當前 Git 狀態
echo "📊 當前 Git 狀態："
git status --porcelain
echo ""

# 2. 檢查最近的 commits
echo "📝 最近 5 個 commits："
git log --oneline -5
echo ""

# 3. 檢查 CI 配置文件
echo "⚙️ CI 配置文件檢查："
ls -la .github/workflows/
echo ""

# 4. 檢查 Python 環境
echo "🐍 Python 環境檢查："
cd apps/bot
echo "Poetry 狀態："
poetry --version
poetry env info
echo ""

# 5. 檢查 Node.js 環境
echo "📦 Node.js 環境檢查："
cd ../../apps/servers
if [ -f package.json ]; then
    echo "發現 package.json:"
    cat package.json | head -20
    echo "..."
else
    echo "未發現 package.json"
fi
echo ""

# 6. 檢查依賴文件
echo "📋 依賴文件檢查："
echo "Python dependencies (pyproject.toml):"
cd ../bot
head -20 pyproject.toml
echo ""

# 7. 嘗試運行基本測試
echo "🧪 基本測試執行："
echo "Python 環境測試："
poetry run python --version
echo "基本導入測試："
poetry run python -c "import sys; print('Python path:', sys.path[:3])" || echo "Python 導入失敗"

echo ""
echo "✅ === CI 失敗診斷分析完成 ==="