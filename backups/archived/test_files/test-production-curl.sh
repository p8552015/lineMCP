#!/bin/bash

# ==============================================
# LINE MCP Bot 生產環境 cURL 測試腳本
# 機台稼動率超時修復與回退機制驗證 v1.0
# 
# 🎯 測試目標：
# ✅ M001機台稼動率查詢（25秒內響應）
# ✅ AI解析失敗→規則解析回退機制
# ✅ SuggestionService 智能建議系統
# ✅ 超時修復驗證（webhook 25秒設定）
# ✅ 真實情境下的系統穩定性
# ==============================================

set -e  # 遇到錯誤立即退出

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置變數
BOT_URL="${BOT_URL:-http://localhost:8000}"
WEBHOOK_PATH="/webhook"
TIMEOUT_SECONDS=30  # 比服務器超時稍長，確保能收到響應
TEST_RESULTS_FILE="curl_test_results.json"

echo -e "${PURPLE}==============================================\n${NC}"
echo -e "${PURPLE}🧪 LINE MCP Bot 生產環境 cURL 測試器 v1.0${NC}"
echo -e "${PURPLE}🔄 機台稼動率超時修復與回退機制驗證${NC}"
echo -e "${PURPLE}==============================================\n${NC}"

# 函數：檢查服務是否運行
check_service_status() {
    echo -e "${BLUE}🔍 檢查服務狀態...${NC}"
    
    # 檢查健康端點
    if curl -s --max-time 5 "$BOT_URL/health" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ 服務運行中: $BOT_URL${NC}"
        
        # 獲取服務資訊
        echo -e "${CYAN}📊 服務資訊：${NC}"
        health_info=$(curl -s --max-time 5 "$BOT_URL/health" | python3 -m json.tool 2>/dev/null || echo "{}")
        echo "$health_info" | head -10
        return 0
    else
        echo -e "${RED}❌ 服務未運行或無法連接: $BOT_URL${NC}"
        echo -e "${YELLOW}💡 請先啟動服務：./start-production.sh${NC}"
        return 1
    fi
}

# 函數：創建測試用的 LINE 訊息格式
create_line_message() {
    local message_text="$1"
    local user_id="${2:-test_curl_user_$(date +%s)}"
    local reply_token="${3:-test_reply_token_$(date +%s)}"
    
    cat << EOF
{
  "events": [
    {
      "type": "message",
      "message": {
        "type": "text",
        "text": "$message_text"
      },
      "source": {
        "type": "user",
        "userId": "$user_id"
      },
      "replyToken": "$reply_token",
      "timestamp": $(date +%s)000
    }
  ]
}
EOF
}

# 函數：執行 cURL 測試並解析結果
execute_curl_test() {
    local test_name="$1"
    local message_text="$2"
    local expected_keywords="$3"  # 逗號分隔的關鍵詞
    local max_response_time="${4:-25}"
    
    echo -e "\n${CYAN}🧪 測試: $test_name${NC}"
    echo -e "${CYAN}📝 查詢: \"$message_text\"${NC}"
    echo -e "${CYAN}⏱️ 預期響應時間: < ${max_response_time}秒${NC}"
    
    # 創建測試訊息
    local json_payload=$(create_line_message "$message_text")
    
    # 記錄開始時間
    local start_time=$(date +%s.%N)
    
    # 執行 cURL 請求
    local response=$(curl -s \
        --max-time $TIMEOUT_SECONDS \
        -X POST \
        -H "Content-Type: application/json" \
        -H "X-Line-Signature: test_signature" \
        -d "$json_payload" \
        "$BOT_URL$WEBHOOK_PATH" 2>/dev/null)
    
    local curl_exit_code=$?
    local end_time=$(date +%s.%N)
    local response_time=$(echo "$end_time - $start_time" | bc -l)
    
    # 分析結果
    local test_result
    if [ $curl_exit_code -eq 0 ]; then
        if [ ! -z "$response" ]; then
            echo -e "${GREEN}✅ 收到響應 (${response_time}秒)${NC}"
            
            # 檢查關鍵詞
            local keyword_check="通過"
            if [ ! -z "$expected_keywords" ]; then
                IFS=',' read -ra keywords <<< "$expected_keywords"
                for keyword in "${keywords[@]}"; do
                    if ! echo "$response" | grep -q "$keyword"; then
                        keyword_check="部分失敗"
                        echo -e "${YELLOW}⚠️ 缺少關鍵詞: $keyword${NC}"
                    fi
                done
            fi
            
            # 檢查響應時間
            local timeout_check="通過"
            if (( $(echo "$response_time > $max_response_time" | bc -l) )); then
                timeout_check="超時"
                echo -e "${RED}❌ 響應超時: ${response_time}秒 > ${max_response_time}秒${NC}"
            fi
            
            # 顯示響應預覽
            echo -e "${CYAN}📄 響應預覽:${NC}"
            echo "$response" | head -3 | sed 's/^/  /'
            
            # 判斷整體結果
            if [[ "$keyword_check" == "通過" && "$timeout_check" == "通過" ]]; then
                test_result="PASSED"
                echo -e "${GREEN}🎉 測試通過${NC}"
            else
                test_result="FAILED"
                echo -e "${RED}❌ 測試失敗${NC}"
            fi
        else
            test_result="NO_RESPONSE"
            echo -e "${RED}❌ 無響應內容${NC}"
        fi
    else
        test_result="CURL_ERROR"
        echo -e "${RED}❌ cURL 錯誤 (退出碼: $curl_exit_code)${NC}"
    fi
    
    # 記錄測試結果
    echo "$test_name|$message_text|$test_result|$response_time|$response" >> "/tmp/curl_test_log.txt"
    
    return $([ "$test_result" = "PASSED" ] && echo 0 || echo 1)
}

# 函數：執行完整的回退機制測試套件
run_complete_fallback_tests() {
    echo -e "\n${BLUE}🔄 開始執行完整回退機制測試套件...${NC}"
    
    # 初始化結果記錄
    echo "test_name|message|result|response_time|response" > "/tmp/curl_test_log.txt"
    
    local tests_passed=0
    local tests_total=0
    
    # 測試 1: M001機台稼動率查詢（核心功能）
    echo -e "\n${PURPLE}📊 測試 1: M001機台稼動率查詢 (核心回退機制)${NC}"
    tests_total=$((tests_total + 1))
    if execute_curl_test "M001機台稼動率查詢" "M001機台稼動率" "M001,稼動率" 25; then
        tests_passed=$((tests_passed + 1))
    fi
    
    # 測試 2: 所有機台查詢
    echo -e "\n${PURPLE}🏭 測試 2: 查看所有機台 (規則解析測試)${NC}"
    tests_total=$((tests_total + 1))
    if execute_curl_test "查看所有機台" "查看所有機台" "機台" 15; then
        tests_passed=$((tests_passed + 1))
    fi
    
    # 測試 3: 未知查詢 - SuggestionService 測試
    echo -e "\n${PURPLE}💡 測試 3: 智能建議系統 (SuggestionService)${NC}"
    tests_total=$((tests_total + 1))
    if execute_curl_test "智能建議測試" "不清楚的機台問題" "建議,推薦,可以" 10; then
        tests_passed=$((tests_passed + 1))
    fi
    
    # 測試 4: 複雜查詢 - 壓力測試
    echo -e "\n${PURPLE}⚡ 測試 4: 複雜查詢壓力測試${NC}"
    tests_total=$((tests_total + 1))
    if execute_curl_test "複雜查詢測試" "CNC車床機台的詳細稼動率和故障記錄" "CNC,車床" 25; then
        tests_passed=$((tests_passed + 1))
    fi
    
    # 測試 5: 錯誤處理測試
    echo -e "\n${PURPLE}🛡️ 測試 5: 錯誤處理機制${NC}"
    tests_total=$((tests_total + 1))
    if execute_curl_test "錯誤處理測試" "無效的機台代碼XYZ999" "" 15; then
        tests_passed=$((tests_passed + 1))
    fi
    
    # 生成測試報告
    generate_test_report $tests_passed $tests_total
}

# 函數：生成詳細測試報告
generate_test_report() {
    local passed=$1
    local total=$2
    local success_rate=$(echo "scale=1; $passed * 100 / $total" | bc -l)
    
    echo -e "\n${BLUE}📊 測試結果總結${NC}"
    echo -e "═══════════════════════════════════════"
    echo -e "${CYAN}總測試數: $total${NC}"
    echo -e "${GREEN}通過數量: $passed${NC}"
    echo -e "${RED}失敗數量: $((total - passed))${NC}"
    echo -e "${YELLOW}成功率: ${success_rate}%${NC}"
    
    # 創建 JSON 報告
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    cat > "$TEST_RESULTS_FILE" << EOF
{
  "timestamp": "$timestamp",
  "test_type": "curl_production_test",
  "bot_url": "$BOT_URL",
  "summary": {
    "total_tests": $total,
    "passed_tests": $passed,
    "failed_tests": $((total - passed)),
    "success_rate": "${success_rate}%"
  },
  "tests": [
EOF
    
    # 解析測試日誌並添加到 JSON
    local first_test=true
    while IFS='|' read -r test_name message result response_time response; do
        if [[ "$test_name" != "test_name" ]]; then  # 跳過標題行
            if [[ "$first_test" == "false" ]]; then
                echo "," >> "$TEST_RESULTS_FILE"
            fi
            
            cat >> "$TEST_RESULTS_FILE" << EOF
    {
      "name": "$test_name",
      "message": "$message",
      "status": "$result",
      "response_time_seconds": "$response_time",
      "response_preview": "$(echo "$response" | head -1 | sed 's/"/\\"/g')"
    }
EOF
            first_test=false
        fi
    done < "/tmp/curl_test_log.txt"
    
    cat >> "$TEST_RESULTS_FILE" << EOF
  ],
  "performance_analysis": {
    "avg_response_time": "$(awk -F'|' 'NR>1 {sum+=$4; count++} END {print sum/count}' /tmp/curl_test_log.txt)",
    "max_response_time": "$(awk -F'|' 'NR>1 {if($4>max) max=$4} END {print max}' /tmp/curl_test_log.txt)",
    "timeout_threshold": "25 seconds"
  }
}
EOF
    
    echo -e "\n${CYAN}📁 詳細報告已保存至: $TEST_RESULTS_FILE${NC}"
    
    # 顯示效能分析
    echo -e "\n${CYAN}⚡ 效能分析:${NC}"
    local avg_time=$(awk -F'|' 'NR>1 {sum+=$4; count++} END {printf "%.2f", sum/count}' /tmp/curl_test_log.txt)
    local max_time=$(awk -F'|' 'NR>1 {if($4>max) max=$4} END {printf "%.2f", max}' /tmp/curl_test_log.txt)
    echo -e "  平均響應時間: ${avg_time}秒"
    echo -e "  最大響應時間: ${max_time}秒"
    echo -e "  超時閾值: 25秒"
    
    # 清理臨時文件
    rm -f "/tmp/curl_test_log.txt"
    
    # 返回結果
    if [[ $success_rate > 80 ]]; then
        echo -e "\n${GREEN}🎉 測試套件通過！系統運行正常${NC}"
        return 0
    else
        echo -e "\n${RED}❌ 測試套件失敗！需要檢查系統狀態${NC}"
        return 1
    fi
}

# 函數：顯示幫助信息
show_help() {
    echo -e "${PURPLE}🎯 LINE MCP Bot cURL 測試器${NC}"
    echo -e ""
    echo -e "${PURPLE}使用方法：${NC}"
    echo -e "  $0 [選項]"
    echo -e ""
    echo -e "${PURPLE}選項：${NC}"
    echo -e "  ${GREEN}test${NC}        執行完整回退機制測試套件 (預設)"
    echo -e "  ${GREEN}quick${NC}       快速測試基本功能"
    echo -e "  ${GREEN}m001${NC}        僅測試 M001機台稼動率查詢"
    echo -e "  ${GREEN}suggestion${NC}  僅測試智能建議系統"
    echo -e "  ${GREEN}status${NC}      檢查服務狀態"
    echo -e "  ${GREEN}help${NC}        顯示此幫助"
    echo -e ""
    echo -e "${PURPLE}環境變數：${NC}"
    echo -e "  ${CYAN}BOT_URL${NC}     Bot 服務 URL (預設: http://localhost:8000)"
    echo -e ""
    echo -e "${PURPLE}示例：${NC}"
    echo -e "  $0              # 完整測試"
    echo -e "  $0 quick        # 快速測試"
    echo -e "  $0 m001         # 僅測試 M001"
    echo -e "  BOT_URL=http://prod-server:8000 $0  # 測試生產服務器"
}

# 主邏輯
case "${1:-test}" in
    "test")
        if check_service_status; then
            run_complete_fallback_tests
        else
            exit 1
        fi
        ;;
    "quick")
        echo -e "${BLUE}⚡ 快速測試模式${NC}"
        if check_service_status; then
            execute_curl_test "快速M001測試" "M001機台稼動率" "M001" 25
        fi
        ;;
    "m001")
        echo -e "${BLUE}📊 M001機台稼動率專項測試${NC}"
        if check_service_status; then
            execute_curl_test "M001專項測試" "M001機台稼動率" "M001,稼動率,74" 25
        fi
        ;;
    "suggestion")
        echo -e "${BLUE}💡 智能建議系統專項測試${NC}"
        if check_service_status; then
            execute_curl_test "智能建議專項測試" "不知道怎麼查機台" "建議,推薦" 10
        fi
        ;;
    "status")
        check_service_status
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo -e "${RED}❌ 未知選項：$1${NC}"
        show_help
        exit 1
        ;;
esac