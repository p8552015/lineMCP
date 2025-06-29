#!/usr/bin/env python3
"""
簡化調試：只測試關鍵的 LLM 指導生成
"""
import asyncio
import sys
import os

# 設置環境變數（使用實際的 API keys）
os.environ['ASYNCIO_FORCE_SELECT_SELECTOR'] = '1'
os.environ['LINE_CHANNEL_ACCESS_TOKEN'] = 'test_token'
os.environ['LINE_CHANNEL_SECRET'] = 'test_secret'
os.environ['OPENAI_API_KEY'] = 'test_openai_key'
os.environ['JWT_SECRET_KEY'] = 'test_jwt_secret'
os.environ['AI_MODEL_PROVIDER'] = 'google'

# 手動設置關鍵的環境變數
os.environ['AI_ENABLE_ENHANCED_NL'] = 'true'
os.environ['NL_FALLBACK_TO_RULES'] = 'true'
os.environ['DB_CONNECTION_STRING'] = 'postgresql://admin:admin@localhost:5432/mydb'

# 嘗試讀取實際的 API keys（如果存在）
try:
    with open('/Users/yen/Desktop/lineMCP/apps/bot/.env', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # 清理值，去除註釋
                if '#' in value:
                    value = value.split('#')[0].strip()
                # 去除引號
                value = value.strip('\'"')
                if key in ['GOOGLE_API_KEY', 'OPENAI_API_KEY']:
                    os.environ[key] = value
except FileNotFoundError:
    print("⚠️ .env 文件未找到，使用測試配置")

# 添加項目路徑
sys.path.append('/Users/yen/Desktop/lineMCP/apps/bot/src')

async def test_llm_guidance():
    try:
        from services.nl_to_sql.models.query_models import QueryType
        from infrastructure.enhanced_service_factory import get_enhanced_service_factory
        
        # 獲取服務
        factory = get_enhanced_service_factory()
        factory.initialize()
        nl_service = factory.get_nl_service()
        
        print("🔍 測試 LLM 指導生成")
        print("=" * 30)
        
        # 測試參數
        query_type = QueryType.MACHINE_STATUS
        parameters = {}
        user_input = "CNC車床今天不良率"
        
        print(f"查詢類型: {query_type}")
        print(f"參數: {parameters}")
        print(f"用戶輸入: {user_input}")
        print()
        
        try:
            print("🔄 調用 _generate_user_guidance...")
            guidance = await nl_service._generate_user_guidance(
                query_type, parameters, user_input
            )
            
            print("✅ LLM 指導生成成功")
            print(f"指導長度: {len(guidance)} 字符")
            print(f"指導內容:")
            print("-" * 40)
            print(guidance)
            print("-" * 40)
            
        except Exception as e:
            print(f"❌ LLM 指導生成失敗: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llm_guidance())