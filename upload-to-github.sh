#!/bin/bash

echo "🚀 準備上傳 Claude Code 自定義指令完整指南到 GitHub"
echo "=========================================="

# 切換到專案目錄
cd "/Users/yen/Desktop/lineMCP"

echo "📍 當前目錄: $(pwd)"

# 檢查 Git 狀態
echo ""
echo "📋 檢查 Git 狀態..."
git status

# 檢查是否有變更
if git diff --quiet && git diff --cached --quiet; then
    echo "⚠️  沒有發現任何變更需要提交"
    exit 0
fi

echo ""
echo "📁 檢查新增的檔案..."
echo "✅ Claude Code 自定義指令完整指南: spec/Claude_Code_自定義指令創建完整指南.md"
echo "✅ Claude 自定義指令檔案: .claude/commands/find-root-cause.md"
echo "✅ 測試指南檔案: test-claude-command.md"

# 將變更加入暫存區
echo ""
echo "📦 將變更加入暫存區..."
git add .

# 查看暫存的變更
echo ""
echo "📝 查看即將提交的變更..."
git diff --cached --name-only

# 建立提交
echo ""
echo "💾 建立 Git 提交..."
git commit -m "$(cat <<'EOF'
feat: 新增 Claude Code 自定義指令完整指南

- 建立完整的自定義指令創建指南 (spec/Claude_Code_自定義指令創建完整指南.md)
- 包含 YAML Front Matter 格式和 $ARGUMENTS 語法
- 提供 3 個實際可用的指令範例
- 添加故障排除和最佳實踐指南
- 修復自定義指令參數傳遞問題
- 新增 .claude/commands/find-root-cause.md 示範指令
- 建立測試驗證文檔

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

# 檢查提交是否成功
if [ $? -eq 0 ]; then
    echo "✅ 提交成功！"
else
    echo "❌ 提交失敗！請檢查錯誤訊息"
    exit 1
fi

# 檢查遠端分支
echo ""
echo "🔗 檢查遠端分支..."
CURRENT_BRANCH=$(git branch --show-current)
echo "當前分支: $CURRENT_BRANCH"

# 推送到 GitHub
echo ""
echo "⬆️  推送到 GitHub..."
git push origin "$CURRENT_BRANCH"

# 檢查推送是否成功
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 成功上傳到 GitHub！"
    echo ""
    echo "📊 提交摘要:"
    echo "- 分支: $CURRENT_BRANCH"
    echo "- 新增檔案: Claude Code 自定義指令完整指南"
    echo "- 修復問題: 自定義指令參數傳遞"
    echo "- 範例指令: find-root-cause 工作正常"
    echo ""
    echo "🔍 檢視變更: git log --oneline -3"
    git log --oneline -3
else
    echo "❌ 推送失敗！請檢查網路連接和 GitHub 權限"
    exit 1
fi

echo ""
echo "✨ 上傳完成！現在團隊成員可以使用這個完整指南建立自己的 Claude Code 自定義指令。"