#!/bin/bash

# GitHub Actions 狀態檢測腳本
# 用途: 檢查 GitHub Actions workflows 執行狀態
# 作者: Claude Code
# 日期: 2025-06-27
# 版本: 1.0.0

set -euo pipefail

# 配置變數
REPO_OWNER="p8552015"
REPO_NAME="lineMCP"
REPO_FULL="${REPO_OWNER}/${REPO_NAME}"
API_BASE="https://api.github.com/repos/${REPO_FULL}"
MAX_RUNS=5

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# 表情符號
SUCCESS_ICON="✅"
FAILURE_ICON="❌"
WARNING_ICON="⚠️"
INFO_ICON="ℹ️"
ROCKET_ICON="🚀"
GEAR_ICON="⚙️"
CLOCK_ICON="🕐"
BRANCH_ICON="🌿"

# 顯示使用說明
show_help() {
    echo -e "${WHITE}GitHub Actions 狀態檢測腳本${NC}"
    echo ""
    echo "用法: $0 [選項]"
    echo ""
    echo "選項:"
    echo "  -h, --help              顯示此幫助訊息"
    echo "  -w, --workflow <id>     檢查特定workflow ID"
    echo "  -b, --branch <name>     檢查特定分支"
    echo "  -n, --runs <number>     顯示最近N次執行 (預設: 5)"
    echo "  -r, --report            生成詳細報告"
    echo "  -s, --summary           僅顯示摘要"
    echo "  --json                  輸出JSON格式"
    echo ""
    echo "範例:"
    echo "  $0                      # 檢查所有workflows"
    echo "  $0 -w 170313960         # 檢查特定workflow"
    echo "  $0 -b main              # 檢查main分支"
    echo "  $0 -n 10                # 顯示最近10次執行"
    echo "  $0 -r                   # 生成詳細報告"
}

# 檢查依賴工具
check_dependencies() {
    local missing_tools=()
    
    if ! command -v curl &> /dev/null; then
        missing_tools+=("curl")
    fi
    
    if ! command -v jq &> /dev/null; then
        missing_tools+=("jq")
    fi
    
    if ! command -v git &> /dev/null; then
        missing_tools+=("git")
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        echo -e "${RED}${FAILURE_ICON} 缺少必要工具: ${missing_tools[*]}${NC}"
        echo "請安裝後重新執行:"
        echo "  macOS: brew install curl jq git"
        echo "  Ubuntu: sudo apt-get install curl jq git"
        exit 1
    fi
}

# 檢查是否在git repository中
check_git_repo() {
    if ! git rev-parse --git-dir &> /dev/null; then
        echo -e "${RED}${FAILURE_ICON} 不在git repository中${NC}"
        exit 1
    fi
}

# API 請求函數
api_request() {
    local endpoint="$1"
    local url="${API_BASE}${endpoint}"
    
    local response
    response=$(curl -s -H "Accept: application/vnd.github.v3+json" "$url")
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}${FAILURE_ICON} API請求失敗: $url${NC}" >&2
        return 1
    fi
    
    echo "$response"
}

# 格式化時間
format_time() {
    local iso_time="$1"
    if command -v date &> /dev/null; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            date -j -f "%Y-%m-%dT%H:%M:%SZ" "$iso_time" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "$iso_time"
        else
            # Linux
            date -d "$iso_time" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "$iso_time"
        fi
    else
        echo "$iso_time"
    fi
}

# 取得status圖示
get_status_icon() {
    local status="$1"
    local conclusion="$2"
    
    case "$status" in
        "completed")
            case "$conclusion" in
                "success") echo "${SUCCESS_ICON}" ;;
                "failure") echo "${FAILURE_ICON}" ;;
                "cancelled") echo "${WARNING_ICON}" ;;
                *) echo "${INFO_ICON}" ;;
            esac
            ;;
        "in_progress") echo "${CLOCK_ICON}" ;;
        "queued") echo "${GEAR_ICON}" ;;
        *) echo "${INFO_ICON}" ;;
    esac
}

# 取得status顏色
get_status_color() {
    local status="$1"
    local conclusion="$2"
    
    case "$status" in
        "completed")
            case "$conclusion" in
                "success") echo "${GREEN}" ;;
                "failure") echo "${RED}" ;;
                "cancelled") echo "${YELLOW}" ;;
                *) echo "${WHITE}" ;;
            esac
            ;;
        "in_progress") echo "${BLUE}" ;;
        "queued") echo "${CYAN}" ;;
        *) echo "${WHITE}" ;;
    esac
}

# 檢查所有workflows
check_workflows() {
    echo -e "${WHITE}${GEAR_ICON} 檢查所有 Workflows${NC}"
    echo "=================================================="
    
    local workflows
    workflows=$(api_request "/actions/workflows")
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}${FAILURE_ICON} 無法獲取workflows列表${NC}"
        return 1
    fi
    
    echo "$workflows" | jq -r '.workflows[] | "\(.id)|\(.name)|\(.state)"' | while IFS='|' read -r id name state; do
        local state_color
        case "$state" in
            "active") state_color="${GREEN}" ;;
            "disabled") state_color="${RED}" ;;
            *) state_color="${YELLOW}" ;;
        esac
        
        printf "%-12s ${state_color}%-8s${NC} %s\n" "$id" "$state" "$name"
    done
    
    echo ""
}

# 檢查最近的workflow執行
check_recent_runs() {
    local workflow_id="$1"
    local branch="$2"
    local max_runs="$3"
    
    echo -e "${WHITE}${ROCKET_ICON} 最近的執行狀態 (最多 $max_runs 筆)${NC}"
    echo "=================================================="
    
    local endpoint="/actions/runs?per_page=$max_runs"
    if [ -n "$workflow_id" ]; then
        endpoint="${endpoint}&workflow_id=$workflow_id"
    fi
    if [ -n "$branch" ]; then
        endpoint="${endpoint}&branch=$branch"
    fi
    
    local runs
    runs=$(api_request "$endpoint")
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}${FAILURE_ICON} 無法獲取執行記錄${NC}"
        return 1
    fi
    
    echo "$runs" | jq -r '.workflow_runs[] | "\(.status)|\(.conclusion)|\(.workflow_id)|\(.head_branch)|\(.created_at)|\(.html_url)"' | while IFS='|' read -r status conclusion workflow_id branch created_at url; do
        local icon
        local color
        icon=$(get_status_icon "$status" "$conclusion")
        color=$(get_status_color "$status" "$conclusion")
        
        local formatted_time
        formatted_time=$(format_time "$created_at")
        
        printf "%s ${color}%-10s${NC} | ${BRANCH_ICON} %-30s | %s\n" "$icon" "${status}/${conclusion}" "$branch" "$formatted_time"
        printf "   ${BLUE}%s${NC}\n" "$url"
        echo ""
    done
}

# 生成詳細報告
generate_report() {
    echo -e "${WHITE}${INFO_ICON} 生成詳細報告${NC}"
    echo "=================================================="
    
    # 檢查當前分支
    local current_branch
    current_branch=$(git branch --show-current 2>/dev/null || echo "unknown")
    echo -e "${BRANCH_ICON} 當前分支: ${CYAN}$current_branch${NC}"
    
    # 檢查最新commit
    local latest_commit
    latest_commit=$(git log --oneline -1 2>/dev/null || echo "unknown")
    echo -e "${INFO_ICON} 最新提交: ${WHITE}$latest_commit${NC}"
    echo ""
    
    # 檢查workflows
    check_workflows
    
    # 檢查最近執行
    check_recent_runs "" "$current_branch" "$MAX_RUNS"
    
    # 統計信息
    generate_statistics
}

# 生成統計信息
generate_statistics() {
    echo -e "${WHITE}${INFO_ICON} 統計信息${NC}"
    echo "=================================================="
    
    local runs
    runs=$(api_request "/actions/runs?per_page=20")
    
    if [ $? -eq 0 ]; then
        local total_runs
        local success_runs
        local failure_runs
        local in_progress_runs
        
        total_runs=$(echo "$runs" | jq '.workflow_runs | length')
        success_runs=$(echo "$runs" | jq '[.workflow_runs[] | select(.conclusion == "success")] | length')
        failure_runs=$(echo "$runs" | jq '[.workflow_runs[] | select(.conclusion == "failure")] | length')
        in_progress_runs=$(echo "$runs" | jq '[.workflow_runs[] | select(.status == "in_progress")] | length')
        
        echo -e "總執行次數: ${WHITE}$total_runs${NC}"
        echo -e "成功次數: ${GREEN}$success_runs${NC}"
        echo -e "失敗次數: ${RED}$failure_runs${NC}"
        echo -e "執行中: ${BLUE}$in_progress_runs${NC}"
        
        if [ "$total_runs" -gt 0 ]; then
            local success_rate
            success_rate=$(echo "scale=1; $success_runs * 100 / $total_runs" | bc 2>/dev/null || echo "0")
            echo -e "成功率: ${GREEN}${success_rate}%${NC}"
        fi
    fi
    
    echo ""
}

# 僅顯示摘要
show_summary() {
    echo -e "${WHITE}${ROCKET_ICON} GitHub Actions 狀態摘要${NC}"
    echo "=================================================="
    
    # 當前分支狀態
    local current_branch
    current_branch=$(git branch --show-current 2>/dev/null || echo "unknown")
    
    local runs
    runs=$(api_request "/actions/runs?branch=$current_branch&per_page=3")
    
    if [ $? -eq 0 ]; then
        local latest_status
        local latest_conclusion
        latest_status=$(echo "$runs" | jq -r '.workflow_runs[0].status // "unknown"')
        latest_conclusion=$(echo "$runs" | jq -r '.workflow_runs[0].conclusion // "unknown"')
        
        local icon
        local color
        icon=$(get_status_icon "$latest_status" "$latest_conclusion")
        color=$(get_status_color "$latest_status" "$latest_conclusion")
        
        echo -e "${BRANCH_ICON} 分支: ${CYAN}$current_branch${NC}"
        echo -e "最新狀態: $icon ${color}${latest_status}/${latest_conclusion}${NC}"
    fi
    
    echo ""
}

# 輸出JSON格式
output_json() {
    local workflow_id="$1"
    local branch="$2"
    local max_runs="$3"
    
    local endpoint="/actions/runs?per_page=$max_runs"
    if [ -n "$workflow_id" ]; then
        endpoint="${endpoint}&workflow_id=$workflow_id"
    fi
    if [ -n "$branch" ]; then
        endpoint="${endpoint}&branch=$branch"
    fi
    
    api_request "$endpoint"
}

# 主函數
main() {
    local workflow_id=""
    local branch=""
    local max_runs="$MAX_RUNS"
    local report_mode=false
    local summary_mode=false
    local json_mode=false
    
    # 解析命令行參數
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -w|--workflow)
                workflow_id="$2"
                shift 2
                ;;
            -b|--branch)
                branch="$2"
                shift 2
                ;;
            -n|--runs)
                max_runs="$2"
                shift 2
                ;;
            -r|--report)
                report_mode=true
                shift
                ;;
            -s|--summary)
                summary_mode=true
                shift
                ;;
            --json)
                json_mode=true
                shift
                ;;
            *)
                echo -e "${RED}${FAILURE_ICON} 未知選項: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 檢查依賴
    check_dependencies
    check_git_repo
    
    # 顯示標題
    if [ "$json_mode" = false ]; then
        echo -e "${WHITE}"
        echo "╔══════════════════════════════════════════════════════════════╗"
        echo "║              GitHub Actions 狀態檢測腳本 v1.0.0               ║"
        echo "║                   Repository: $REPO_FULL                    ║"
        echo "╚══════════════════════════════════════════════════════════════╝"
        echo -e "${NC}"
        echo ""
    fi
    
    # 執行對應功能
    if [ "$json_mode" = true ]; then
        output_json "$workflow_id" "$branch" "$max_runs"
    elif [ "$summary_mode" = true ]; then
        show_summary
    elif [ "$report_mode" = true ]; then
        generate_report
    else
        # 預設模式：顯示workflows和最近執行
        if [ -z "$workflow_id" ]; then
            check_workflows
        fi
        check_recent_runs "$workflow_id" "$branch" "$max_runs"
    fi
    
    if [ "$json_mode" = false ]; then
        echo -e "${GREEN}${SUCCESS_ICON} 檢查完成${NC}"
    fi
}

# 錯誤處理
trap 'echo -e "\n${RED}${FAILURE_ICON} 腳本執行被中斷${NC}"; exit 1' INT TERM

# 執行主函數
main "$@"