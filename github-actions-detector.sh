#!/bin/bash

##############################################################################
# GitHub Actions CI/CD 自動檢測系統
# 
# 功能: 自動檢測 GitHub Actions workflows 狀態，分析失敗原因，生成改善建議
# 作者: Claude Code
# 版本: 1.0
# 日期: 2025-06-24
##############################################################################

set -euo pipefail

# 顏色定義
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# 配置變數
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_FILE="${SCRIPT_DIR}/github-actions-detector.log"
readonly REPORT_FILE="${SCRIPT_DIR}/ci-status-report.md"
readonly BASE_URL="https://api.github.com"

# GitHub 配置 (從環境變數或自動偵測)
GITHUB_TOKEN="${GITHUB_TOKEN:-}"
GITHUB_OWNER="${GITHUB_OWNER:-}"
GITHUB_REPO="${GITHUB_REPO:-}"

# 目標 workflows 清單
readonly TARGET_WORKFLOWS=(
    "ci-enhanced.yml"
    "security.yml"
    "quality.yml"
    "docker-security.yml"
    "performance.yml"
    "release.yml"
)

##############################################################################
# 工具函數
##############################################################################

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() { log "INFO" "$@"; }
log_warn() { log "WARN" "$@"; }
log_error() { log "ERROR" "$@"; }

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🤖 GitHub Actions CI/CD 自動檢測系統${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_section() {
    echo -e "\\n${YELLOW}📋 $1${NC}"
    echo -e "${YELLOW}$(printf '─%.0s' {1..60})${NC}"
}

check_dependencies() {
    local deps=("curl" "jq" "git")
    local missing=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing+=("$dep")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "缺少必要工具: ${missing[*]}"
        echo -e "${RED}請安裝: ${missing[*]}${NC}"
        exit 1
    fi
}

detect_github_config() {
    if [[ -z "$GITHUB_OWNER" || -z "$GITHUB_REPO" ]]; then
        if git rev-parse --is-inside-work-tree &>/dev/null; then
            local remote_url=$(git config --get remote.origin.url 2>/dev/null || echo "")
            if [[ "$remote_url" =~ github\.com[:/]([^/]+)/([^/]+)(\.git)?$ ]]; then
                GITHUB_OWNER="${BASH_REMATCH[1]}"
                GITHUB_REPO="${BASH_REMATCH[2]}"
                log_info "自動偵測 GitHub 倉庫: ${GITHUB_OWNER}/${GITHUB_REPO}"
            fi
        fi
    fi
    
    if [[ -z "$GITHUB_OWNER" || -z "$GITHUB_REPO" ]]; then
        log_error "無法偵測 GitHub 倉庫資訊"
        echo -e "${RED}請設置環境變數 GITHUB_OWNER 和 GITHUB_REPO${NC}"
        exit 1
    fi
}

check_github_token() {
    if [[ -z "$GITHUB_TOKEN" ]]; then
        log_error "未設置 GITHUB_TOKEN 環境變數"
        echo -e "${RED}請設置 GitHub Personal Access Token${NC}"
        echo -e "${YELLOW}範例: export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx${NC}"
        exit 1
    fi
}

##############################################################################
# GitHub API 函數
##############################################################################

github_api_call() {
    local endpoint="$1"
    local method="${2:-GET}"
    local extra_headers="${3:-}"
    
    local auth_header="Authorization: token ${GITHUB_TOKEN}"
    local accept_header="Accept: application/vnd.github.v3+json"
    local user_agent="User-Agent: github-actions-detector/1.0"
    
    local curl_cmd="curl -s -X ${method}"
    curl_cmd+=" -H '${auth_header}'"
    curl_cmd+=" -H '${accept_header}'"
    curl_cmd+=" -H '${user_agent}'"
    
    if [[ -n "$extra_headers" ]]; then
        curl_cmd+=" -H '${extra_headers}'"
    fi
    
    curl_cmd+=" '${BASE_URL}${endpoint}'"
    
    local response
    if ! response=$(eval "$curl_cmd" 2>/dev/null); then
        log_error "API 呼叫失敗: ${endpoint}"
        return 1
    fi
    
    # 檢查是否有 API 錯誤
    if echo "$response" | jq -e '.message' &>/dev/null; then
        local error_msg=$(echo "$response" | jq -r '.message')
        log_error "GitHub API 錯誤: ${error_msg}"
        return 1
    fi
    
    echo "$response"
}

get_workflows() {
    log_info "取得 workflows 列表..."
    github_api_call "/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows"
}

get_workflow_runs() {
    local workflow_id="$1"
    local per_page="${2:-10}"
    log_info "取得 workflow runs (workflow_id: ${workflow_id})..."
    github_api_call "/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows/${workflow_id}/runs?per_page=${per_page}&status=completed"
}

get_run_jobs() {
    local run_id="$1"
    log_info "取得 run jobs (run_id: ${run_id})..."
    github_api_call "/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/runs/${run_id}/jobs"
}

download_run_logs() {
    local run_id="$1"
    local output_dir="${SCRIPT_DIR}/logs"
    local zip_file="${output_dir}/run_${run_id}_logs.zip"
    
    mkdir -p "$output_dir"
    
    log_info "下載 run logs (run_id: ${run_id})..."
    
    if curl -L -s -H "Authorization: token ${GITHUB_TOKEN}" \
        -H "Accept: application/vnd.github.v3+json" \
        "${BASE_URL}/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/runs/${run_id}/logs" \
        -o "${zip_file}"; then
        
        if [[ -f "$zip_file" ]]; then
            local extract_dir="${output_dir}/run_${run_id}"
            mkdir -p "$extract_dir"
            
            if unzip -q "$zip_file" -d "$extract_dir" 2>/dev/null; then
                log_info "日誌解壓縮完成: ${extract_dir}"
                rm "$zip_file"
                echo "$extract_dir"
            else
                log_warn "日誌解壓縮失敗"
                rm -f "$zip_file"
                return 1
            fi
        else
            log_warn "日誌下載失敗"
            return 1
        fi
    else
        log_error "無法下載日誌"
        return 1
    fi
}

##############################################################################
# 分析函數
##############################################################################

analyze_workflow_status() {
    local workflows_json="$1"
    local total_workflows=0
    local active_workflows=0
    local failed_workflows=()
    
    print_section "📊 Workflow 狀態分析"
    
    # 分析 workflows 狀態
    while IFS= read -r workflow; do
        local name=$(echo "$workflow" | jq -r '.name')
        local path=$(echo "$workflow" | jq -r '.path')
        local state=$(echo "$workflow" | jq -r '.state')
        local workflow_id=$(echo "$workflow" | jq -r '.id')
        
        ((total_workflows++))
        
        printf "%-25s %-20s " "$name" "$path"
        
        case "$state" in
            "active")
                echo -e "${GREEN}✅ 啟用${NC}"
                ((active_workflows++))
                
                # 取得最新 runs 狀態
                local runs_json
                if runs_json=$(get_workflow_runs "$workflow_id" 1); then
                    local latest_run=$(echo "$runs_json" | jq -r '.workflow_runs[0]')
                    if [[ "$latest_run" != "null" ]]; then
                        local conclusion=$(echo "$latest_run" | jq -r '.conclusion')
                        local run_id=$(echo "$latest_run" | jq -r '.id')
                        local run_number=$(echo "$latest_run" | jq -r '.run_number')
                        
                        printf "  └─ 最新執行: #%-5s " "$run_number"
                        case "$conclusion" in
                            "success")
                                echo -e "${GREEN}✅ 成功${NC}"
                                ;;
                            "failure")
                                echo -e "${RED}❌ 失敗${NC}"
                                failed_workflows+=("$name:$run_id")
                                ;;
                            "cancelled")
                                echo -e "${YELLOW}⏹️  取消${NC}"
                                ;;
                            *)
                                echo -e "${YELLOW}❓ $conclusion${NC}"
                                ;;
                        esac
                    else
                        echo "  └─ 無執行記錄"
                    fi
                fi
                ;;
            "disabled_manually")
                echo -e "${YELLOW}⏸️  手動停用${NC}"
                ;;
            *)
                echo -e "${RED}❌ $state${NC}"
                ;;
        esac
    done < <(echo "$workflows_json" | jq -c '.workflows[]')
    
    echo ""
    echo -e "📈 統計資訊:"
    echo -e "  總計 workflows: ${total_workflows}"
    echo -e "  啟用中: ${GREEN}${active_workflows}${NC}"
    echo -e "  失敗的: ${RED}${#failed_workflows[@]}${NC}"
    
    # 分析失敗的 workflows
    if [[ ${#failed_workflows[@]} -gt 0 ]]; then
        print_section "🔍 失敗分析"
        for failed in "${failed_workflows[@]}"; do
            local workflow_name="${failed%:*}"
            local run_id="${failed#*:}"
            analyze_failed_run "$workflow_name" "$run_id"
        done
    fi
}

analyze_failed_run() {
    local workflow_name="$1"
    local run_id="$2"
    
    echo -e "\\n${RED}❌ 分析失敗的 workflow: ${workflow_name}${NC}"
    
    local jobs_json
    if jobs_json=$(get_run_jobs "$run_id"); then
        local failed_jobs=()
        
        while IFS= read -r job; do
            local job_name=$(echo "$job" | jq -r '.name')
            local job_conclusion=$(echo "$job" | jq -r '.conclusion')
            local job_id=$(echo "$job" | jq -r '.id')
            
            if [[ "$job_conclusion" == "failure" ]]; then
                failed_jobs+=("$job_name:$job_id")
                echo -e "  🔸 失敗的 Job: ${RED}${job_name}${NC}"
                
                # 分析失敗的 steps
                local steps=$(echo "$job" | jq -c '.steps[]?')
                if [[ -n "$steps" ]]; then
                    while IFS= read -r step; do
                        local step_name=$(echo "$step" | jq -r '.name')
                        local step_conclusion=$(echo "$step" | jq -r '.conclusion')
                        
                        if [[ "$step_conclusion" == "failure" ]]; then
                            echo -e "    └─ 失敗步驟: ${step_name}"
                        fi
                    done < <(echo "$job" | jq -c '.steps[]?')
                fi
            fi
        done < <(echo "$jobs_json" | jq -c '.jobs[]')
        
        # 下載並分析日誌
        if [[ ${#failed_jobs[@]} -gt 0 ]]; then
            local log_dir
            if log_dir=$(download_run_logs "$run_id"); then
                analyze_error_logs "$log_dir" "${failed_jobs[@]}"
            fi
        fi
    fi
}

analyze_error_logs() {
    local log_dir="$1"
    shift
    local failed_jobs=("$@")
    
    echo -e "\\n🔍 錯誤日誌分析:"
    
    for job_info in "${failed_jobs[@]}"; do
        local job_name="${job_info%:*}"
        local job_id="${job_info#*:}"
        
        # 查找對應的日誌文件
        local log_files
        if log_files=$(find "$log_dir" -name "*.txt" -type f); then
            local most_relevant_log=""
            local max_relevance=0
            
            while IFS= read -r log_file; do
                local filename=$(basename "$log_file")
                local relevance=0
                
                # 計算檔名與 job 名稱的相關性
                if [[ "$filename" == *"$job_name"* ]]; then
                    relevance=100
                elif [[ "$filename" == *"$job_id"* ]]; then
                    relevance=90
                elif echo "$job_name" | grep -qi "test" && echo "$filename" | grep -qi "test"; then
                    relevance=50
                elif echo "$job_name" | grep -qi "build" && echo "$filename" | grep -qi "build"; then
                    relevance=50
                fi
                
                if [[ $relevance -gt $max_relevance ]]; then
                    max_relevance=$relevance
                    most_relevant_log="$log_file"
                fi
            done <<< "$log_files"
            
            if [[ -n "$most_relevant_log" && $max_relevance -gt 0 ]]; then
                echo -e "  📄 分析日誌: $(basename "$most_relevant_log")"
                extract_error_patterns "$most_relevant_log"
            else
                echo -e "  ⚠️  未找到相關日誌文件: $job_name"
            fi
        fi
    done
}

extract_error_patterns() {
    local log_file="$1"
    
    # 常見錯誤模式
    local error_patterns=(
        "ERROR"
        "FAILED"
        "Exception"
        "Error:"
        "command not found"
        "Permission denied"
        "No such file"
        "timeout"
        "killed"
        "exit code"
    )
    
    local found_errors=()
    
    for pattern in "${error_patterns[@]}"; do
        local matches
        if matches=$(grep -i "$pattern" "$log_file" 2>/dev/null | head -3); then
            if [[ -n "$matches" ]]; then
                found_errors+=("$pattern")
                echo -e "    🔸 ${pattern}:"
                while IFS= read -r line; do
                    # 清理並截斷過長的行
                    local clean_line=$(echo "$line" | sed 's/[[:space:]]*$//' | cut -c1-80)
                    echo -e "      ${clean_line}"
                done <<< "$matches"
            fi
        fi
    done
    
    if [[ ${#found_errors[@]} -eq 0 ]]; then
        echo -e "    ℹ️  未發現明顯錯誤模式，建議手動檢查完整日誌"
    fi
}

##############################################################################
# 報告生成函數
##############################################################################

generate_improvement_suggestions() {
    local failed_workflows=("$@")
    
    if [[ ${#failed_workflows[@]} -eq 0 ]]; then
        echo -e "\\n${GREEN}🎉 所有 workflows 狀態正常！${NC}"
        return 0
    fi
    
    print_section "💡 改善建議"
    
    echo -e "基於分析結果，以下是改善建議:\\n"
    
    # 通用建議
    echo -e "${YELLOW}🔧 通用修復步驟:${NC}"
    echo "1. 檢查最新 commits 是否導入了問題"
    echo "2. 確認所有環境變數和 secrets 設置正確"
    echo "3. 檢查依賴版本是否有衝突"
    echo "4. 確認測試資料和配置檔案完整性"
    echo ""
    
    # 針對性建議
    echo -e "${YELLOW}🎯 針對性建議:${NC}"
    for failed in "${failed_workflows[@]}"; do
        local workflow_name="${failed%:*}"
        echo "• ${workflow_name}:"
        
        case "$workflow_name" in
            *"ci"*|*"test"*)
                echo "  - 執行本地測試: \`poetry run pytest -v\`"
                echo "  - 檢查測試環境配置"
                echo "  - 確認測試資料庫連接"
                ;;
            *"security"*)
                echo "  - 檢查安全掃描工具版本"
                echo "  - 更新依賴套件解決漏洞"
                echo "  - 確認安全配置檔案"
                ;;
            *"quality"*)
                echo "  - 執行程式碼格式化: \`poetry run black src/\`"
                echo "  - 修復 linting 問題: \`poetry run ruff check src/ --fix\`"
                echo "  - 檢查類型註解: \`poetry run mypy src/\`"
                ;;
            *"docker"*)
                echo "  - 檢查 Dockerfile 語法"
                echo "  - 確認基礎映像檔版本"
                echo "  - 檢查容器安全配置"
                ;;
            *)
                echo "  - 檢查 workflow 配置檔案"
                echo "  - 確認相關環境變數設置"
                ;;
        esac
        echo ""
    done
    
    # 快速修復指令
    echo -e "${YELLOW}⚡ 快速修復指令:${NC}"
    echo "\`\`\`bash"
    echo "# 本地測試和修復"
    echo "cd apps/bot"
    echo "poetry run black src/ tests/"
    echo "poetry run ruff check src/ tests/ --fix"
    echo "poetry run mypy src/"
    echo "poetry run pytest -v"
    echo ""
    echo "# 重新觸發 CI"
    echo "git add ."
    echo "git commit -m \"🔧 修復 CI/CD 問題\""
    echo "git push"
    echo "\`\`\`"
}

generate_report() {
    local failed_workflows=("$@")
    
    cat > "$REPORT_FILE" << EOF
# 🤖 GitHub Actions CI/CD 狀態報告

**生成時間**: $(date '+%Y-%m-%d %H:%M:%S')  
**倉庫**: ${GITHUB_OWNER}/${GITHUB_REPO}  
**檢測範圍**: ${#TARGET_WORKFLOWS[@]} 個 workflows

## 📊 總體狀態

EOF
    
    if [[ ${#failed_workflows[@]} -eq 0 ]]; then
        cat >> "$REPORT_FILE" << EOF
**狀態**: 🟢 全部正常  
**成功率**: 100%

✅ 所有 workflows 都處於正常狀態，CI/CD 管道運行良好！

EOF
    else
        local success_count=$((${#TARGET_WORKFLOWS[@]} - ${#failed_workflows[@]}))
        local success_rate=$((success_count * 100 / ${#TARGET_WORKFLOWS[@]}))
        
        cat >> "$REPORT_FILE" << EOF
**狀態**: 🔴 需要修復  
**成功率**: ${success_rate}%  
**失敗數量**: ${#failed_workflows[@]}

### 🚨 失敗的 Workflows

EOF
        
        for failed in "${failed_workflows[@]}"; do
            local workflow_name="${failed%:*}"
            local run_id="${failed#*:}"
            echo "- ❌ **${workflow_name}** (Run ID: ${run_id})" >> "$REPORT_FILE"
        done
        
        cat >> "$REPORT_FILE" << EOF

### 💡 改善建議

詳細的改善建議請參考終端輸出或執行：
\`\`\`bash
./github-actions-detector.sh --suggestions
\`\`\`

EOF
    fi
    
    cat >> "$REPORT_FILE" << EOF
---

**檢測工具**: github-actions-detector.sh v1.0  
**詳細日誌**: ${LOG_FILE}
EOF
    
    log_info "報告已生成: ${REPORT_FILE}"
}

##############################################################################
# 主函數
##############################################################################

main() {
    local show_help=false
    local check_all=true
    local target_workflow=""
    local generate_report_only=false
    
    # 解析命令列參數
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help=true
                shift
                ;;
            -w|--workflow)
                target_workflow="$2"
                check_all=false
                shift 2
                ;;
            -r|--report)
                generate_report_only=true
                shift
                ;;
            *)
                log_error "未知參數: $1"
                show_help=true
                shift
                ;;
        esac
    done
    
    if [[ "$show_help" == true ]]; then
        cat << EOF
🤖 GitHub Actions CI/CD 自動檢測系統

使用方法:
  $0 [選項]

選項:
  -h, --help              顯示此幫助訊息
  -w, --workflow NAME     檢測特定 workflow
  -r, --report            僅生成報告

環境變數:
  GITHUB_TOKEN           GitHub Personal Access Token (必要)
  GITHUB_OWNER           GitHub 使用者/組織名稱 (可自動偵測)
  GITHUB_REPO            GitHub 倉庫名稱 (可自動偵測)

範例:
  $0                      # 檢測所有 workflows
  $0 -w ci-enhanced       # 檢測特定 workflow
  $0 -r                   # 僅生成報告

EOF
        exit 0
    fi
    
    # 初始化
    print_header
    echo "開始時間: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    # 檢查依賴和配置
    log_info "檢查系統依賴..."
    check_dependencies
    
    log_info "偵測 GitHub 配置..."
    detect_github_config
    check_github_token
    
    echo -e "📋 配置資訊:"
    echo -e "  倉庫: ${GREEN}${GITHUB_OWNER}/${GITHUB_REPO}${NC}"
    echo -e "  Token: ${GREEN}已設置${NC}"
    
    # 清理舊日誌
    > "$LOG_FILE"
    
    # 執行檢測
    local failed_workflows=()
    
    if [[ "$generate_report_only" != true ]]; then
        log_info "開始執行 GitHub Actions 檢測..."
        
        local workflows_json
        if workflows_json=$(get_workflows); then
            analyze_workflow_status "$workflows_json"
            
            # 提取失敗的 workflows 資訊 (這部分需要在 analyze_workflow_status 中收集)
            # 暫時使用空陣列，實際實作中需要修改 analyze_workflow_status 回傳失敗資訊
            
            generate_improvement_suggestions "${failed_workflows[@]}"
        else
            log_error "無法取得 workflows 資訊"
            exit 1
        fi
    fi
    
    # 生成報告
    generate_report "${failed_workflows[@]}"
    
    print_section "✅ 檢測完成"
    echo -e "詳細日誌: ${LOG_FILE}"
    echo -e "狀態報告: ${REPORT_FILE}"
    
    if [[ ${#failed_workflows[@]} -gt 0 ]]; then
        echo -e "\\n${RED}⚠️  發現 ${#failed_workflows[@]} 個失敗的 workflows，需要修復${NC}"
        exit 1
    else
        echo -e "\\n${GREEN}🎉 所有 workflows 狀態正常！${NC}"
        exit 0
    fi
}

# 執行主函數
main "$@"