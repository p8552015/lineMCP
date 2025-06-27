#!/bin/bash

# 🔐 完整的 API Key 管理系統
# 防止截斷、驗證有效性、自動測試連接

set -euo pipefail

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BOT_DIR="$PROJECT_ROOT/apps/bot"
ENV_FILE="$BOT_DIR/.env"
BACKUP_DIR="$BOT_DIR/.env.backups"

# 創建備份目錄
mkdir -p "$BACKUP_DIR"

# 日誌函數
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_header() { echo -e "${PURPLE}$1${NC}"; }

# 創建時間戳備份
create_backup() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="$BACKUP_DIR/.env.backup_$timestamp"
    
    if [[ -f "$ENV_FILE" ]]; then
        cp "$ENV_FILE" "$backup_file"
        log_success "環境文件已備份: $backup_file"
        return 0
    else
        log_error "環境文件不存在: $ENV_FILE"
        return 1
    fi
}

# 驗證 OpenAI API Key 格式
validate_openai_format() {
    local key="$1"
    
    # 長度檢查
    if [[ ${#key} -lt 100 ]]; then
        echo "❌ 長度太短 (${#key} < 100)"
        return 1
    fi
    
    if [[ ${#key} -gt 200 ]]; then
        echo "❌ 長度太長 (${#key} > 200)"
        return 1
    fi
    
    # 前綴檢查
    if [[ ! "$key" =~ ^sk-proj- ]]; then
        echo "❌ 前綴錯誤，應以 'sk-proj-' 開始"
        return 1
    fi
    
    # 必要部分檢查
    if [[ "$key" != *"T3BlbkFJ"* ]]; then
        echo "❌ 缺少必要部分 'T3BlbkFJ'"
        return 1
    fi
    
    # 字符集檢查
    if [[ ! "$key" =~ ^[A-Za-z0-9_-]+$ ]]; then
        echo "❌ 包含無效字符"
        return 1
    fi
    
    echo "✅ 格式正確 (長度: ${#key})"
    return 0
}

# 測試 OpenAI API 連接
test_openai_connection() {
    local api_key="$1"
    local temp_script="/tmp/test_openai_$$"
    
    cat > "$temp_script" << 'EOF'
import asyncio
import aiohttp
import sys
import json

async def test_api(api_key):
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': 'gpt-4o-mini',
        'messages': [{'role': 'user', 'content': 'Test'}],
        'max_tokens': 5
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                result = {
                    'status': response.status,
                    'success': response.status == 200
                }
                
                if response.status == 200:
                    data = await response.json()
                    result['response'] = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                else:
                    error_data = await response.json()
                    result['error'] = error_data.get('error', {}).get('message', 'Unknown error')
                    result['error_code'] = error_data.get('error', {}).get('code', 'unknown')
                
                return result
                
    except Exception as e:
        return {
            'status': 0,
            'success': False,
            'error': str(e),
            'error_code': 'connection_error'
        }

if __name__ == "__main__":
    api_key = sys.argv[1] if len(sys.argv) > 1 else ""
    result = asyncio.run(test_api(api_key))
    print(json.dumps(result))
EOF

    local result=$(python3 "$temp_script" "$api_key" 2>/dev/null || echo '{"success": false, "error": "Python execution failed"}')
    rm -f "$temp_script"
    
    echo "$result"
}

# 驗證 Gemini API Key 格式
validate_gemini_format() {
    local key="$1"
    
    if [[ ${#key} -ne 39 ]]; then
        echo "❌ 長度錯誤 (${#key} != 39)"
        return 1
    fi
    
    if [[ ! "$key" =~ ^AIza ]]; then
        echo "❌ 前綴錯誤，應以 'AIza' 開始"
        return 1
    fi
    
    if [[ ! "$key" =~ ^[A-Za-z0-9_-]+$ ]]; then
        echo "❌ 包含無效字符"
        return 1
    fi
    
    echo "✅ 格式正確 (長度: ${#key})"
    return 0
}

# 完整的 API Key 檢查
comprehensive_check() {
    log_header "🔍 執行完整 API Key 檢查"
    log_header "================================"
    
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "環境文件不存在: $ENV_FILE"
        return 1
    fi
    
    cd "$BOT_DIR"
    source .env 2>/dev/null || true
    
    # 檢查 OpenAI
    if [[ -n "${OPENAI_API_KEY:-}" ]]; then
        log_info "🤖 檢查 OpenAI API Key..."
        echo "   長度: ${#OPENAI_API_KEY}"
        echo "   前綴: ${OPENAI_API_KEY:0:20}..."
        
        # 格式驗證
        if validate_openai_format "$OPENAI_API_KEY"; then
            log_success "格式驗證通過"
            
            # 連接測試
            log_info "測試 API 連接..."
            local test_result=$(test_openai_connection "$OPENAI_API_KEY")
            local success=$(echo "$test_result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('success', False))")
            
            if [[ "$success" == "True" ]]; then
                log_success "✅ OpenAI API 連接測試成功"
            else
                local error=$(echo "$test_result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error', 'Unknown error'))")
                local error_code=$(echo "$test_result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error_code', 'unknown'))")
                log_error "❌ OpenAI API 連接失敗: $error (代碼: $error_code)"
                
                if [[ "$error_code" == "invalid_api_key" ]]; then
                    log_warning "💡 建議: 請檢查 API Key 是否正確，或前往 https://platform.openai.com/account/api-keys 重新生成"
                fi
            fi
        else
            log_error "格式驗證失敗"
        fi
    else
        log_warning "未找到 OpenAI API Key"
    fi
    
    echo
    
    # 檢查 Gemini
    if [[ -n "${GOOGLE_API_KEY:-}" ]]; then
        log_info "🔮 檢查 Gemini API Key..."
        echo "   長度: ${#GOOGLE_API_KEY}"
        echo "   前綴: ${GOOGLE_API_KEY:0:10}..."
        
        if validate_gemini_format "$GOOGLE_API_KEY"; then
            log_success "✅ Gemini API Key 格式正確"
        else
            log_error "❌ Gemini API Key 格式錯誤"
        fi
    else
        log_warning "未找到 Gemini API Key"
    fi
}

# 安全更新 API Key
safe_update() {
    local provider="$1"
    local new_key="$2"
    
    case "$provider" in
        "openai")
            log_info "🤖 更新 OpenAI API Key..."
            if validate_openai_format "$new_key"; then
                if create_backup; then
                    # 更新環境文件
                    if grep -q "^OPENAI_API_KEY=" "$ENV_FILE"; then
                        sed -i.tmp "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=$new_key|" "$ENV_FILE"
                        rm -f "${ENV_FILE}.tmp"
                    else
                        echo "OPENAI_API_KEY=$new_key" >> "$ENV_FILE"
                    fi
                    
                    log_success "✅ OpenAI API Key 更新成功"
                    
                    # 測試新 Key
                    log_info "測試新 API Key..."
                    local test_result=$(test_openai_connection "$new_key")
                    local success=$(echo "$test_result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('success', False))")
                    
                    if [[ "$success" == "True" ]]; then
                        log_success "🎉 新 API Key 測試成功！"
                    else
                        log_error "⚠️ 新 API Key 測試失敗，但已保存"
                    fi
                fi
            else
                log_error "新 API Key 格式驗證失敗"
                return 1
            fi
            ;;
        "gemini")
            log_info "🔮 更新 Gemini API Key..."
            if validate_gemini_format "$new_key"; then
                if create_backup; then
                    if grep -q "^GOOGLE_API_KEY=" "$ENV_FILE"; then
                        sed -i.tmp "s|^GOOGLE_API_KEY=.*|GOOGLE_API_KEY=$new_key|" "$ENV_FILE"
                        rm -f "${ENV_FILE}.tmp"
                    else
                        echo "GOOGLE_API_KEY=$new_key" >> "$ENV_FILE"
                    fi
                    log_success "✅ Gemini API Key 更新成功"
                fi
            else
                log_error "新 API Key 格式驗證失敗"
                return 1
            fi
            ;;
        *)
            log_error "不支援的提供商: $provider"
            return 1
            ;;
    esac
}

# 主函數
main() {
    log_header "🔐 API Key 管理系統"
    log_header "==================="
    
    # 檢查環境
    if [[ ! -d "$BOT_DIR" ]]; then
        log_error "Bot 目錄不存在: $BOT_DIR"
        exit 1
    fi
    
    case "${1:-}" in
        "check"|"scan")
            comprehensive_check
            ;;
        "update-openai")
            if [[ $# -eq 2 ]]; then
                safe_update "openai" "$2"
            else
                log_error "用法: $0 update-openai <API_KEY>"
            fi
            ;;
        "update-gemini")
            if [[ $# -eq 2 ]]; then
                safe_update "gemini" "$2"
            else
                log_error "用法: $0 update-gemini <API_KEY>"
            fi
            ;;
        "test-openai")
            cd "$BOT_DIR"
            source .env 2>/dev/null || true
            if [[ -n "${OPENAI_API_KEY:-}" ]]; then
                log_info "🧪 測試 OpenAI API 連接..."
                local result=$(test_openai_connection "$OPENAI_API_KEY")
                echo "$result" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('success'):
    print('✅ 連接成功')
    print(f'📝 回應: {data.get(\"response\", \"\")}')
else:
    print('❌ 連接失敗')
    print(f'🚨 錯誤: {data.get(\"error\", \"Unknown\")}')
    print(f'📋 代碼: {data.get(\"error_code\", \"unknown\")}')
"
            else
                log_error "未找到 OpenAI API Key"
            fi
            ;;
        "help"|"-h"|"--help")
            echo "🔐 API Key 管理系統"
            echo ""
            echo "用法: $0 [命令] [參數]"
            echo ""
            echo "命令:"
            echo "  check, scan              完整檢查所有 API Keys"
            echo "  update-openai <KEY>      更新 OpenAI API Key"
            echo "  update-gemini <KEY>      更新 Gemini API Key"
            echo "  test-openai              測試 OpenAI API 連接"
            echo "  help                     顯示此幫助"
            echo ""
            echo "功能特色:"
            echo "  ✅ 防止 API Key 截斷"
            echo "  ✅ 格式完整性驗證"
            echo "  ✅ 實際連接測試"
            echo "  ✅ 自動備份機制"
            echo "  ✅ 詳細錯誤診斷"
            ;;
        "")
            comprehensive_check
            ;;
        *)
            log_error "未知命令: $1"
            log_info "使用 '$0 help' 查看幫助"
            exit 1
            ;;
    esac
}

main "$@" 