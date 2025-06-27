#!/bin/bash

# API Key 自動修復和驗證腳本
# 防止 API Key 截斷問題的完整解決方案

set -euo pipefail

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BOT_DIR="$PROJECT_ROOT/apps/bot"
ENV_FILE="$BOT_DIR/.env"
BACKUP_DIR="$BOT_DIR/.env.backups"

# 創建備份目錄
mkdir -p "$BACKUP_DIR"

# 日誌函數
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "${PURPLE}$1${NC}"
}

# 創建備份
create_backup() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="$BACKUP_DIR/.env.backup_$timestamp"
    
    if [[ -f "$ENV_FILE" ]]; then
        cp "$ENV_FILE" "$backup_file"
        log_success "環境文件已備份到: $backup_file"
        return 0
    else
        log_error "環境文件不存在: $ENV_FILE"
        return 1
    fi
}

# 驗證 OpenAI API Key
validate_openai_key() {
    local key="$1"
    local min_length=100
    local max_length=200
    
    # 檢查長度
    if [[ ${#key} -lt $min_length ]]; then
        echo "ERROR: API Key 太短 (${#key} < $min_length)"
        return 1
    fi
    
    if [[ ${#key} -gt $max_length ]]; then
        echo "ERROR: API Key 太長 (${#key} > $max_length)"
        return 1
    fi
    
    # 檢查前綴
    if [[ ! "$key" =~ ^sk-proj- ]]; then
        echo "ERROR: API Key 前綴錯誤，應以 'sk-proj-' 開始"
        return 1
    fi
    
    # 檢查必要部分
    if [[ "$key" != *"T3BlbkFJ"* ]]; then
        echo "ERROR: API Key 缺少必要部分 'T3BlbkFJ'"
        return 1
    fi
    
    # 檢查字符集
    if [[ ! "$key" =~ ^[A-Za-z0-9_-]+$ ]]; then
        echo "ERROR: API Key 包含無效字符"
        return 1
    fi
    
    echo "OK: API Key 格式正確 (長度: ${#key})"
    return 0
}

# 驗證 Gemini API Key
validate_gemini_key() {
    local key="$1"
    local expected_length=39
    
    # 檢查長度
    if [[ ${#key} -ne $expected_length ]]; then
        echo "ERROR: API Key 長度錯誤 (${#key} != $expected_length)"
        return 1
    fi
    
    # 檢查前綴
    if [[ ! "$key" =~ ^AIza ]]; then
        echo "ERROR: API Key 前綴錯誤，應以 'AIza' 開始"
        return 1
    fi
    
    # 檢查字符集
    if [[ ! "$key" =~ ^[A-Za-z0-9_-]+$ ]]; then
        echo "ERROR: API Key 包含無效字符"
        return 1
    fi
    
    echo "OK: API Key 格式正確 (長度: ${#key})"
    return 0
}

# 掃描和驗證 API Keys
scan_api_keys() {
    log_header "🔍 掃描 API Keys..."
    
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "環境文件不存在: $ENV_FILE"
        return 1
    fi
    
    local found_keys=0
    local valid_keys=0
    local invalid_keys=0
    
    # 掃描 OpenAI Keys
    while IFS= read -r line; do
        if [[ "$line" =~ ^OPENAI_API_KEY= ]]; then
            found_keys=$((found_keys + 1))
            local key_value="${line#*=}"
            key_value="${key_value%\"}"  # 移除尾部引號
            key_value="${key_value#\"}"  # 移除頭部引號
            
            log_info "找到 OpenAI API Key (長度: ${#key_value})"
            
            if validate_openai_key "$key_value"; then
                log_success "✅ OpenAI API Key 驗證通過"
                valid_keys=$((valid_keys + 1))
            else
                log_error "❌ OpenAI API Key 驗證失敗"
                invalid_keys=$((invalid_keys + 1))
            fi
        fi
    done < "$ENV_FILE"
    
    # 掃描 Gemini Keys
    while IFS= read -r line; do
        if [[ "$line" =~ ^GOOGLE_API_KEY= ]]; then
            found_keys=$((found_keys + 1))
            local key_value="${line#*=}"
            key_value="${key_value%\"}"  # 移除尾部引號
            key_value="${key_value#\"}"  # 移除頭部引號
            
            log_info "找到 Gemini API Key (長度: ${#key_value})"
            
            if validate_gemini_key "$key_value"; then
                log_success "✅ Gemini API Key 驗證通過"
                valid_keys=$((valid_keys + 1))
            else
                log_error "❌ Gemini API Key 驗證失敗"
                invalid_keys=$((invalid_keys + 1))
            fi
        fi
    done < "$ENV_FILE"
    
    log_header "📊 掃描結果:"
    echo "   找到 API Keys: $found_keys"
    echo "   有效 Keys: $valid_keys"
    echo "   無效 Keys: $invalid_keys"
    
    return $invalid_keys
}

# 安全更新 API Key
safe_update_key() {
    local key_name="$1"
    local new_key="$2"
    local provider="$3"
    
    log_info "準備更新 $key_name..."
    
    # 驗證新 Key
    case "$provider" in
        "openai")
            if ! validate_openai_key "$new_key"; then
                log_error "新 OpenAI API Key 驗證失敗"
                return 1
            fi
            ;;
        "gemini")
            if ! validate_gemini_key "$new_key"; then
                log_error "新 Gemini API Key 驗證失敗"
                return 1
            fi
            ;;
        *)
            log_error "不支援的提供商: $provider"
            return 1
            ;;
    esac
    
    # 創建備份
    if ! create_backup; then
        log_error "無法創建備份，取消更新"
        return 1
    fi
    
    # 更新 Key
    if grep -q "^${key_name}=" "$ENV_FILE"; then
        # 更新現有 Key
        if sed -i.tmp "s|^${key_name}=.*|${key_name}=${new_key}|" "$ENV_FILE"; then
            rm -f "${ENV_FILE}.tmp"
            log_success "✅ $key_name 更新成功"
            return 0
        else
            log_error "更新失敗"
            return 1
        fi
    else
        # 添加新 Key
        echo "${key_name}=${new_key}" >> "$ENV_FILE"
        log_success "✅ $key_name 添加成功"
        return 0
    fi
}

# 交互式修復
interactive_fix() {
    log_header "🔧 交互式 API Key 修復"
    
    echo "請選擇要修復的 API Key:"
    echo "1) OpenAI API Key"
    echo "2) Gemini API Key"
    echo "3) 掃描並顯示所有 Keys"
    echo "4) 退出"
    
    read -p "請輸入選項 (1-4): " choice
    
    case "$choice" in
        1)
            read -p "請輸入完整的 OpenAI API Key: " openai_key
            if [[ -n "$openai_key" ]]; then
                safe_update_key "OPENAI_API_KEY" "$openai_key" "openai"
            else
                log_error "API Key 不能為空"
            fi
            ;;
        2)
            read -p "請輸入完整的 Gemini API Key: " gemini_key
            if [[ -n "$gemini_key" ]]; then
                safe_update_key "GOOGLE_API_KEY" "$gemini_key" "gemini"
            else
                log_error "API Key 不能為空"
            fi
            ;;
        3)
            scan_api_keys
            ;;
        4)
            log_info "退出"
            exit 0
            ;;
        *)
            log_error "無效選項"
            ;;
    esac
}

# 主函數
main() {
    log_header "🔐 API Key 自動修復工具"
    log_header "================================"
    
    # 檢查環境
    if [[ ! -d "$BOT_DIR" ]]; then
        log_error "Bot 目錄不存在: $BOT_DIR"
        exit 1
    fi
    
    cd "$BOT_DIR"
    
    # 解析命令行參數
    case "${1:-}" in
        "scan"|"check")
            scan_api_keys
            ;;
        "fix")
            if [[ $# -eq 4 ]]; then
                # 命令行模式: ./fix-api-keys.sh fix KEY_NAME KEY_VALUE PROVIDER
                safe_update_key "$2" "$3" "$4"
            else
                interactive_fix
            fi
            ;;
        "openai")
            if [[ $# -eq 2 ]]; then
                safe_update_key "OPENAI_API_KEY" "$2" "openai"
            else
                log_error "用法: $0 openai <API_KEY>"
            fi
            ;;
        "gemini")
            if [[ $# -eq 2 ]]; then
                safe_update_key "GOOGLE_API_KEY" "$2" "gemini"
            else
                log_error "用法: $0 gemini <API_KEY>"
            fi
            ;;
        "help"|"-h"|"--help")
            echo "用法: $0 [命令] [參數]"
            echo ""
            echo "命令:"
            echo "  scan, check           掃描並驗證所有 API Keys"
            echo "  fix                   交互式修復 API Keys"
            echo "  fix KEY_NAME KEY_VALUE PROVIDER  直接更新指定 Key"
            echo "  openai <API_KEY>      更新 OpenAI API Key"
            echo "  gemini <API_KEY>      更新 Gemini API Key"
            echo "  help                  顯示此幫助信息"
            echo ""
            echo "範例:"
            echo "  $0 scan"
            echo "  $0 openai sk-proj-..."
            echo "  $0 gemini AIza..."
            ;;
        "")
            # 默認執行掃描
            scan_api_keys
            ;;
        *)
            log_error "未知命令: $1"
            log_info "使用 '$0 help' 查看幫助"
            exit 1
            ;;
    esac
}

# 執行主函數
main "$@" 