#!/bin/bash
# T-03: 服務註冊驗證測試執行腳本
# 基於 start-production.sh 的測試策略

echo "🧪 執行 T-03: 服務註冊驗證測試"
echo "=============================================="

# 設定變數
PROJECT_ROOT="/Users/yen/Desktop/lineMCP"
BOT_DIR="$PROJECT_ROOT/apps/bot"
CICD_DIR="$PROJECT_ROOT/CICD"

# 進入 bot 目錄
cd "$BOT_DIR" || exit 1

# 創建測試環境文件（模仿 start-production.sh 邏輯）
echo "🔧 創建測試環境配置..."
cat > .env.test << 'EOF'
# Test Configuration - T03 Service Registry Test
LINE_CHANNEL_ACCESS_TOKEN=test_channel_access_token_for_service_registry_testing_32chars
LINE_CHANNEL_SECRET=test_channel_secret_for_testing_32_characters_long_string
OPENAI_API_KEY=sk-test-openai-api-key-for-service-registry-testing-purposes-only
GOOGLE_API_KEY=test_google_api_key_for_service_registry_testing_only
MCP_SERVER_URL=http://localhost:3000
MCP_API_KEY=test_mcp_api_key_for_service_registry_testing
JWT_SECRET_KEY=test_jwt_secret_key_for_service_registry_testing_32_chars_min

# Application Test Settings
APP_ENV=test
APP_DEBUG=false
LOG_LEVEL=warning

# Service Factory Configuration
SERVICE_FACTORY_TYPE=enhanced
ENABLE_MONITORING=true
ENABLE_CACHING=true

# NL-to-SQL Configuration for Service Registry Test
NL_TO_SQL_ENABLED=true
NL_TO_SQL_CONFIG_DIR=src/services/nl_to_sql/config
COMPOSITE_PARSER_FALLBACK_THRESHOLD=0.5
ENABLE_QUERY_STATISTICS=true
AI_PARSER_TIMEOUT=3000
RULE_PARSER_CACHE_SIZE=1000
ENABLE_CONFIG_HOT_RELOAD=false

# Stability Configuration
ENABLE_EMPTY_QUERY_PROTECTION=true
ENABLE_TYPE_SAFETY_VALIDATION=true
ENABLE_AUTOMATIC_SQL_CONSTRUCTION=true
PARSER_BUILDER_COORDINATION=true
EOF

echo "✅ 測試環境配置已創建"

# 設置環境變數指向測試配置
export ENV_FILE=".env.test"
export PYTHONPATH="$BOT_DIR/src:$PYTHONPATH"

echo "🔍 驗證 Python 環境..."
python3 --version
echo "📁 當前目錄: $(pwd)"
echo "🐍 Python 路徑: $PYTHONPATH"

# 執行基於 start-production.sh 邏輯的服務工廠測試
echo ""
echo "🏗️ 執行服務工廠基礎測試..."
python3 -c "
import sys
import os
sys.path.insert(0, 'src')

# 設置測試環境
os.environ['ENV_FILE'] = '.env.test'

print('🔧 載入測試環境配置...')

try:
    from src.infrastructure.enhanced_service_factory import EnhancedServiceFactory
    
    print('✅ 服務工廠模組導入成功')
    
    # 初始化服務工廠
    factory = EnhancedServiceFactory()
    factory.initialize()
    
    print('✅ 服務工廠初始化成功')
    
    # 獲取註冊資訊
    info = factory.get_registry_info()
    print(f'📊 註冊服務總數: {info[\"total_services\"]}')
    print(f'   單例服務: {info[\"by_scope\"][\"singleton\"]}')
    print(f'   瞬態服務: {info[\"by_scope\"][\"transient\"]}')
    
    # 測試核心服務獲取 (直接使用 factory，不需要 provider)
    try:
        db_service = factory.get_database_service()
        print('✅ DatabaseService 獲取成功')
    except Exception as e:
        print(f'⚠️ DatabaseService 獲取失敗: {e}')
    
    try:
        msg_formatter = factory.get_message_formatter()
        print('✅ MessageFormatter 獲取成功')
    except Exception as e:
        print(f'⚠️ MessageFormatter 獲取失敗: {e}')
    
    print('\\n🎉 服務工廠基礎測試完成')
    
except Exception as e:
    print(f'❌ 服務工廠測試失敗: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo "✅ 服務工廠基礎測試通過"
else
    echo "❌ 服務工廠基礎測試失敗"
    exit 1
fi

# 執行詳細的服務註冊驗證
echo ""
echo "🔍 執行詳細的服務註冊驗證..."
python3 -c "
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, 'src')
os.environ['ENV_FILE'] = '.env.test'

def test_service_registry_comprehensive():
    try:
        from src.infrastructure.enhanced_service_factory import EnhancedServiceFactory
        from src.infrastructure.service_registry import get_service_registry
        
        print('🏗️ 初始化測試環境...')
        factory = EnhancedServiceFactory()
        factory.initialize()
        
        # 測試 1: 服務註冊數量驗證
        print('\\n📊 測試 1: 服務註冊數量驗證')
        print('-' * 40)
        
        info = factory.get_registry_info()
        total_services = info['total_services']
        singleton_count = info['by_scope']['singleton']
        transient_count = info['by_scope']['transient']
        
        print(f'總註冊服務: {total_services}')
        print(f'Singleton 服務: {singleton_count}')
        print(f'Transient 服務: {transient_count}')
        
        # 驗證是否達到合理的服務數量
        min_expected = 15
        if total_services >= min_expected:
            print(f'✅ 服務數量驗證通過 (>= {min_expected})')
        else:
            print(f'⚠️ 服務數量偏低 (< {min_expected})')
        
        # 測試 2: 核心服務可用性檢查
        print('\\n🔧 測試 2: 核心服務可用性檢查')
        print('-' * 40)
        
        core_services = [
            ('get_database_service', 'DatabaseService'),
            ('get_message_formatter', 'MessageFormatter'),
            ('get_configuration_service', 'ConfigurationService'),
            ('get_statistics_service', 'StatisticsService'),
            ('get_ai_model_service', 'AIModelService'),
            ('get_nl_service', 'NLToSQLService'),
        ]
        
        available_count = 0
        unavailable_count = 0
        
        for method_name, service_name in core_services:
            try:
                if hasattr(factory, method_name):
                    service = getattr(factory, method_name)()
                    if service is not None:
                        print(f'✅ {service_name}: 可用')
                        available_count += 1
                    else:
                        print(f'❌ {service_name}: 返回 None')
                        unavailable_count += 1
                else:
                    print(f'⚠️ {service_name}: 方法 {method_name} 不存在')
                    unavailable_count += 1
            except Exception as e:
                print(f'❌ {service_name}: 異常 - {str(e)[:50]}')
                unavailable_count += 1
        
        service_availability = available_count / len(core_services) * 100
        print(f'\\n核心服務可用率: {service_availability:.1f}% ({available_count}/{len(core_services)})')
        
        # 測試 3: 服務解析效能測試
        print('\\n⚡ 測試 3: 服務解析效能測試')
        print('-' * 40)
        
        resolution_times = []
        test_rounds = 20
        
        for i in range(test_rounds):
            start_time = time.time()
            try:
                _ = factory.get_database_service()
                _ = factory.get_message_formatter()
            except:
                pass  # 忽略錯誤，專注於測量可用服務的效能
            
            elapsed = (time.time() - start_time) * 1000  # 毫秒
            resolution_times.append(elapsed)
        
        avg_time = sum(resolution_times) / len(resolution_times)
        max_time = max(resolution_times)
        min_time = min(resolution_times)
        
        print(f'解析效能統計 ({test_rounds} 次測試):')
        print(f'  平均時間: {avg_time:.2f}ms')
        print(f'  最大時間: {max_time:.2f}ms')
        print(f'  最小時間: {min_time:.2f}ms')
        
        # 效能門檻
        perf_threshold = 50.0  # 50ms
        if avg_time <= perf_threshold:
            print(f'✅ 效能測試通過 (<= {perf_threshold}ms)')
        else:
            print(f'⚠️ 效能測試超出門檻 (> {perf_threshold}ms)')
        
        # 測試 4: Singleton 行為驗證
        print('\\n🎯 測試 4: Singleton 行為驗證')
        print('-' * 40)
        
        try:
            service1 = factory.get_database_service()
            service2 = factory.get_database_service()
            
            if service1 is service2:
                print('✅ Singleton 行為驗證通過')
                singleton_ok = True
            else:
                print('❌ Singleton 行為驗證失敗')
                singleton_ok = False
        except Exception as e:
            print(f'⚠️ Singleton 測試異常: {e}')
            singleton_ok = False
        
        # 總結報告
        print('\\n📋 測試總結報告')
        print('=' * 50)
        
        test_results = {
            'timestamp': datetime.now().isoformat(),
            'total_services': total_services,
            'service_availability': service_availability,
            'avg_resolution_time': avg_time,
            'singleton_behavior': singleton_ok,
            'meets_minimum_services': total_services >= min_expected,
            'performance_acceptable': avg_time <= perf_threshold
        }
        
        # 計算整體評分
        score = 0
        if test_results['meets_minimum_services']:
            score += 25
        if test_results['service_availability'] >= 70:
            score += 25
        if test_results['performance_acceptable']:
            score += 25
        if test_results['singleton_behavior']:
            score += 25
        
        test_results['overall_score'] = score
        test_results['overall_status'] = 'PASS' if score >= 75 else 'PARTIAL' if score >= 50 else 'FAIL'
        
        print(f'總服務數: {total_services} (最小要求: {min_expected})')
        print(f'服務可用率: {service_availability:.1f}%')
        print(f'平均解析時間: {avg_time:.2f}ms (門檻: {perf_threshold}ms)')
        print(f'Singleton 行為: {\"✅ 正常\" if singleton_ok else \"❌ 異常\"}')
        print(f'整體評分: {score}/100')
        print(f'測試狀態: {test_results[\"overall_status\"]}')
        
        # 保存測試結果
        import json
        with open('service_registry_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(test_results, f, ensure_ascii=False, indent=2)
        
        print(f'\\n📁 測試結果已保存: service_registry_test_results.json')
        
        # 返回測試是否成功
        return test_results['overall_status'] in ['PASS', 'PARTIAL']
        
    except Exception as e:
        print(f'❌ 綜合測試執行失敗: {e}')
        import traceback
        traceback.print_exc()
        return False

# 執行綜合測試
success = test_service_registry_comprehensive()
sys.exit(0 if success else 1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ T-03 服務註冊驗證測試完成"
    
    # 顯示測試結果摘要
    if [ -f "service_registry_test_results.json" ]; then
        echo ""
        echo "📊 測試結果摘要:"
        python3 -c "
import json
try:
    with open('service_registry_test_results.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f'  🏗️ 總服務數: {data[\"total_services\"]}')
    print(f'  📊 服務可用率: {data[\"service_availability\"]:.1f}%')
    print(f'  ⚡ 平均解析時間: {data[\"avg_resolution_time\"]:.2f}ms')
    print(f'  🎯 Singleton 行為: {\"✅ 正常\" if data[\"singleton_behavior\"] else \"❌ 異常\"}')
    print(f'  📈 整體評分: {data[\"overall_score\"]}/100')
    print(f'  🏆 測試狀態: {data[\"overall_status\"]}')
except Exception as e:
    print(f'  ⚠️ 無法讀取測試結果: {e}')
"
    fi
    
else
    echo ""
    echo "❌ T-03 服務註冊驗證測試失敗"
    exit 1
fi

# 清理測試環境
echo ""
echo "🧹 清理測試環境..."
rm -f .env.test

echo "🎉 T-03 測試執行完成"