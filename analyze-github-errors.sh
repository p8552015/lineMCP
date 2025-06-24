#!/bin/bash

##############################################################################
# GitHub Actions 錯誤快速分析腳本
# 
# 功能: 快速從失敗的 workflow 中提取錯誤信息
# 用法: ./analyze-github-errors.sh [RUN_ID]
##############################################################################

set -euo pipefail

# 顏色定義
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly NC='\033[0m' # No Color

# 配置
OWNER="${GITHUB_REPOSITORY_OWNER:-p8552015}"
REPO="${GITHUB_REPOSITORY_NAME:-lineMCP}"
TOKEN="${GITHUB_TOKEN:-}"
RUN_ID="${1:-}"

# 檢查依賴
check_dependencies() {
    local deps=("curl" "jq" "grep")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            echo -e "${RED}❌ 缺少工具: $dep${NC}"
            exit 1
        fi
    done
}

# GitHub API 調用
gh_api() {
    local endpoint="$1"
    local auth_header=""
    
    if [[ -n "$TOKEN" ]]; then
        auth_header="-H \"Authorization: Bearer $TOKEN\""
    fi
    
    eval "curl -s $auth_header \
        -H \"Accept: application/vnd.github+json\" \
        -H \"X-GitHub-Api-Version: 2022-11-28\" \
        \"https://api.github.com$endpoint\""
}

# 獲取最新失敗的 run
get_latest_failed_run() {
    echo -e "${BLUE}🔍 尋找最新的失敗 workflow...${NC}"
    
    local runs=$(gh_api "/repos/$OWNER/$REPO/actions/runs?status=failure&per_page=1")
    local run_id=$(echo "$runs" | jq -r '.workflow_runs[0].id // empty')
    
    if [[ -z "$run_id" ]]; then
        echo -e "${RED}❌ 沒有找到失敗的 workflow${NC}"
        exit 1
    fi
    
    local run_name=$(echo "$runs" | jq -r '.workflow_runs[0].name // "Unknown"')
    local branch=$(echo "$runs" | jq -r '.workflow_runs[0].head_branch // "Unknown"')
    
    echo -e "${GREEN}✅ 找到失敗的 Run:${NC}"
    echo -e "  Run ID: $run_id"
    echo -e "  名稱: $run_name"
    echo -e "  分支: $branch"
    
    echo "$run_id"
}

# 分析特定 job 的錯誤
analyze_job_errors() {
    local job_id="$1"
    local job_name="$2"
    
    echo -e "\n${YELLOW}📋 分析 Job: $job_name${NC}"
    
    # 下載日誌（跟隨重定向）
    local log_url="/repos/$OWNER/$REPO/actions/jobs/$job_id/logs"
    local log_content=""
    
    if [[ -n "$TOKEN" ]]; then
        log_content=$(curl -sL \
            -H "Authorization: Bearer $TOKEN" \
            -H "Accept: application/vnd.github+json" \
            "https://api.github.com$log_url")
    else
        echo -e "${YELLOW}⚠️  無認證模式，某些日誌可能無法訪問${NC}"
        return
    fi
    
    # 創建臨時文件存儲日誌
    local temp_log=$(mktemp)
    echo "$log_content" > "$temp_log"
    
    # 提取各種錯誤
    echo -e "\n${PURPLE}🐛 發現的錯誤:${NC}"
    
    # pytest 錯誤
    echo -e "\n${BLUE}pytest 錯誤:${NC}"
    grep -n -E "pytest: error:|ERROR:" "$temp_log" | head -10 || echo "  (無)"
    
    # 測試失敗
    echo -e "\n${BLUE}失敗的測試:${NC}"
    grep -n "FAILED" "$temp_log" | grep -E "\.py::" | head -10 || echo "  (無)"
    
    # Python 錯誤
    echo -e "\n${BLUE}Python 錯誤:${NC}"
    grep -n -E "(ImportError|ModuleNotFoundError|SyntaxError|TypeError|ValueError|AssertionError):" "$temp_log" | head -10 || echo "  (無)"
    
    # Exit code
    echo -e "\n${BLUE}退出碼:${NC}"
    grep -n "Process completed with exit code" "$temp_log" | tail -1 || echo "  (無)"
    
    # 清理臨時文件
    rm -f "$temp_log"
}

# 生成修復建議
generate_suggestions() {
    local errors="$1"
    
    echo -e "\n${GREEN}🔧 修復建議:${NC}"
    
    if echo "$errors" | grep -q "unrecognized arguments.*--timeout"; then
        echo -e "\n${YELLOW}問題: pytest 不識別 --timeout 參數${NC}"
        echo "解決方案:"
        echo "1. 安裝 pytest-timeout: poetry add --dev pytest-timeout"
        echo "2. 或從 CI 配置中移除 --timeout 參數"
        echo "3. 檢查 .github/workflows/*.yml 中的 pytest 命令"
    fi
    
    if echo "$errors" | grep -q "ModuleNotFoundError"; then
        echo -e "\n${YELLOW}問題: 缺少 Python 模組${NC}"
        echo "解決方案:"
        echo "1. 更新依賴: cd apps/bot && poetry install"
        echo "2. 檢查 pyproject.toml 中的依賴列表"
        echo "3. 確認 CI 環境正確安裝了所有依賴"
    fi
    
    if echo "$errors" | grep -q "FAILED.*test_"; then
        echo -e "\n${YELLOW}問題: 單元測試失敗${NC}"
        echo "解決方案:"
        echo "1. 本地運行測試: cd apps/bot && poetry run pytest -v"
        echo "2. 查看具體的斷言錯誤"
        echo "3. 檢查最近的代碼變更是否影響了測試"
    fi
}

# 主函數
main() {
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${PURPLE}🔍 GitHub Actions 錯誤分析工具${NC}"
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    check_dependencies
    
    # 確定要分析的 run ID
    if [[ -z "$RUN_ID" ]]; then
        RUN_ID=$(get_latest_failed_run)
    else
        echo -e "${BLUE}📍 使用指定的 Run ID: $RUN_ID${NC}"
    fi
    
    # 獲取 run 詳情
    echo -e "\n${BLUE}📊 獲取 Run 詳情...${NC}"
    local run_info=$(gh_api "/repos/$OWNER/$REPO/actions/runs/$RUN_ID")
    local workflow_name=$(echo "$run_info" | jq -r '.name // "Unknown"')
    local conclusion=$(echo "$run_info" | jq -r '.conclusion // "Unknown"')
    
    echo -e "Workflow: $workflow_name"
    echo -e "結論: $conclusion"
    
    # 獲取失敗的 jobs
    echo -e "\n${BLUE}🔍 檢查失敗的 Jobs...${NC}"
    local jobs=$(gh_api "/repos/$OWNER/$REPO/actions/runs/$RUN_ID/jobs")
    local failed_jobs=$(echo "$jobs" | jq -r '.jobs[] | select(.conclusion == "failure") | "\(.id)|\(.name)"')
    
    if [[ -z "$failed_jobs" ]]; then
        echo -e "${YELLOW}沒有找到失敗的 jobs${NC}"
        exit 0
    fi
    
    # 收集所有錯誤
    local all_errors=""
    
    # 分析每個失敗的 job
    while IFS='|' read -r job_id job_name; do
        analyze_job_errors "$job_id" "$job_name"
        
        # 收集錯誤用於後續建議
        if [[ -n "$TOKEN" ]]; then
            local job_errors=$(curl -sL \
                -H "Authorization: Bearer $TOKEN" \
                -H "Accept: application/vnd.github+json" \
                "https://api.github.com/repos/$OWNER/$REPO/actions/jobs/$job_id/logs" | \
                grep -E "pytest: error:|ERROR:|FAILED|Error:|Exception:")
            all_errors+="$job_errors\n"
        fi
    done <<< "$failed_jobs"
    
    # 生成修復建議
    generate_suggestions "$all_errors"
    
    # 快速修復命令
    echo -e "\n${GREEN}🚀 快速修復命令:${NC}"
    cat << 'EOF'

# 1. 查看具體的 pytest 配置
cd apps/bot
grep -r "timeout" . --include="*.toml" --include="*.ini" --include="*.yml"

# 2. 安裝缺失的依賴（如 pytest-timeout）
poetry add --dev pytest-timeout

# 3. 本地測試
poetry run pytest -v

# 4. 提交修復
git add .
git commit -m "🔧 修復 CI 測試配置"
git push
EOF
    
    echo -e "\n${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ 分析完成！${NC}"
    
    # 提示使用 Python 版本獲取更詳細的分析
    echo -e "\n${YELLOW}💡 提示: 使用 Python 版本可獲得更詳細的分析報告:${NC}"
    echo -e "   python3 github_actions_error_analyzer.py --latest"
}

# 執行主函數
main