#!/bin/bash

# 🧪 生產環境 cURL 測試腳本
# 測試機台稼動率和回退機制

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
BASE_URL="http://localhost:8000"
TIMEOUT=30

# 日誌函數
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_header() { echo -e "${PURPLE}$1${NC}"; }

# 檢查服務狀態
check_service() {
    log_info "🔍 檢查服務狀態..."
    
    local health_response=$(curl -s -X GET "$BASE_URL/health" 2>/dev/null || echo "")
    
    if [[ -n "$health_response" ]]; then
        local status=$(echo "$health_response" | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
        if [[ "$status" == "healthy" ]]; then
            log_success "✅ 服務健康運行"
            return 0
        else
            log_error "❌ 服務狀態異常: $status"
            return 1
        fi
    else
        log_error "❌ 無法連接到服務"
        return 1
    fi
}

# 直接測試 ApplicationFacade
test_application_facade() {
    local query="$1"
    local test_name="$2"
    
    log_info "🧪 測試: $test_name"
    echo "   查詢: $query"
    
    # 創建臨時測試腳本
    local temp_script="/tmp/test_facade_$$"
    
    cat > "$temp_script" << PYTHON_EOF
import asyncio
import sys
import json
import time
from datetime import datetime

sys.path.insert(0, 'apps/bot/src')

async def test_query():
    try:
        from infrastructure.enhanced_service_factory import EnhancedServiceFactory
        from application.application_facade import ApplicationFacade
        
        # 初始化
        factory = EnhancedServiceFactory()
        factory.initialize()
        
        facade = ApplicationFacade(factory)
        await facade.initialize()
        
        # 執行查詢
        start_time = time.time()
        result = await facade.process_message(
            user_id='curl_test_user',
            message_text='$query',
            reply_token='curl_test_token'
        )
        elapsed_time = time.time() - start_time
        
        # 返回結果
        return {
            'success': True,
            'elapsed_time': elapsed_time,
            'result': {
                'text': result.text if hasattr(result, 'text') else str(result),
                'type': type(result).__name__
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }

if __name__ == "__main__":
    result = asyncio.run(test_query())
    print(json.dumps(result, ensure_ascii=False, indent=2))
PYTHON_EOF

    # 執行測試
    local result=$(python3 "$temp_script" 2>/dev/null || echo '{"success": false, "error": "Execution failed"}')
    rm -f "$temp_script"
    
    # 解析結果
    local success=$(echo "$result" | jq -r '.success // false' 2>/dev/null || echo "false")
    
    if [[ "$success" == "true" ]]; then
        local elapsed=$(echo "$result" | jq -r '.elapsed_time // 0' 2>/dev/null || echo "0")
        local response_text=$(echo "$result" | jq -r '.result.text // "無回應"' 2>/dev/null || echo "無回應")
        
        log_success "✅ 測試通過"
        echo "   ⏱️  響應時間: ${elapsed}秒"
        echo "   📝 回應內容: $response_text"
        
        # 檢查是否包含預期的機台資訊
        if [[ "$response_text" == *"M001"* ]] && [[ "$response_text" == *"%"* ]]; then
            log_success "�� 包含機台稼動率資訊"
        else
            log_warning "⚠️ 回應格式可能不完整"
        fi
        
        return 0
    else
        local error=$(echo "$result" | jq -r '.error // "Unknown error"' 2>/dev/null || echo "Unknown error")
        log_error "❌ 測試失敗: $error"
        return 1
    fi
}

# 主函數
main() {
    log_header "🧪 生產環境 cURL 測試套件"
    log_header "========================="
    
    # 檢查服務
    if ! check_service; then
        log_error "服務未就緒，退出測試"
        exit 1
    fi
    
    echo
    
    # 測試 M001 機台稼動率
    test_application_facade "M001機台稼動率" "M001機台稼動率查詢"
}

main "$@"
