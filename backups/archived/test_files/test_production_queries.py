#!/usr/bin/env python3
"""
生產環境查詢測試腳本
測試 LINE MCP Bot 的核心查詢功能
"""

import sys
import os
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
import traceback
from pathlib import Path

# 載入環境變數
from dotenv import load_dotenv

# 設定 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps', 'bot'))

# 載入環境變數檔案
env_path = Path(__file__).parent / 'apps' / 'bot' / '.env'
load_dotenv(env_path)

# 設定環境變數
os.environ['PYTHONPATH'] = os.path.join(os.path.dirname(__file__), 'apps', 'bot')
os.environ['ASYNCIO_FORCE_SELECT_SELECTOR'] = '1'  # macOS 修復

from src.infrastructure.enhanced_service_factory import EnhancedServiceFactory
from src.application.application_facade import ApplicationFacade
import structlog

# 初始化日誌
logger = structlog.get_logger(__name__)

class ProductionQueryTester:
    """生產環境查詢測試器"""
    
    def __init__(self):
        self.factory = None
        self.facade = None
        self.mcp_client = None
        self.test_results = []
        
    async def setup(self):
        """初始化測試環境"""
        try:
            logger.info("=== 開始設定生產環境測試 ===")
            
            # 初始化服務工廠
            self.factory = EnhancedServiceFactory()
            logger.info("✓ 服務工廠初始化完成")
            
            # 跳過 MCP 客戶端初始化，直接測試應用門面
            logger.info("✓ 跳過 MCP 客戶端初始化（使用應用門面進行測試）")
            
            # 初始化應用門面
            self.facade = ApplicationFacade(self.factory)
            await self.facade.initialize()
            logger.info("✓ 應用門面初始化完成")
            
            return True
            
        except Exception as e:
            logger.error(f"設定失敗: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    async def test_query(self, query: str, description: str) -> Dict[str, Any]:
        """測試單一查詢"""
        logger.info(f"\n--- 測試查詢: {description} ---")
        logger.info(f"查詢內容: {query}")
        
        start_time = datetime.now()
        result = {
            "query": query,
            "description": description,
            "success": False,
            "response": None,
            "error": None,
            "execution_time": None
        }
        
        try:
            # 執行查詢
            response = await self.facade.process_message(
                user_id="test_user",
                message_text=query,
                reply_token="test_reply_token"
            )
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            result["success"] = True
            result["response"] = response
            result["execution_time"] = execution_time
            
            logger.info(f"✓ 查詢成功 (執行時間: {execution_time:.3f}秒)")
            logger.info(f"回應內容:\n{response}")
            
        except Exception as e:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            result["error"] = str(e)
            result["execution_time"] = execution_time
            
            logger.error(f"✗ 查詢失敗: {str(e)}")
            logger.error(traceback.format_exc())
        
        self.test_results.append(result)
        return result
    
    async def run_tests(self):
        """執行所有測試"""
        logger.info("\n=== 開始執行生產環境查詢測試 ===")
        
        # 設定測試環境
        if not await self.setup():
            logger.error("環境設定失敗，終止測試")
            return False
        
        # 測試查詢列表
        test_queries = [
            ("M001機台稼動率", "測試特定機台稼動率查詢"),
            ("查看所有機台", "測試列出所有機台功能")
        ]
        
        # 執行測試
        for query, description in test_queries:
            await self.test_query(query, description)
            # 等待一秒避免過快請求
            await asyncio.sleep(1)
        
        # 生成測試報告
        self.generate_report()
        
        # 清理資源
        await self.cleanup()
        
        # 返回測試是否全部通過
        return all(result["success"] for result in self.test_results)
    
    def generate_report(self):
        """生成測試報告"""
        logger.info("\n=== 測試報告 ===")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests
        
        logger.info(f"總測試數: {total_tests}")
        logger.info(f"通過: {passed_tests}")
        logger.info(f"失敗: {failed_tests}")
        logger.info(f"成功率: {(passed_tests/total_tests*100):.1f}%")
        
        logger.info("\n=== 詳細結果 ===")
        for i, result in enumerate(self.test_results, 1):
            logger.info(f"\n測試 {i}: {result['description']}")
            logger.info(f"查詢: {result['query']}")
            logger.info(f"狀態: {'✓ 通過' if result['success'] else '✗ 失敗'}")
            logger.info(f"執行時間: {result['execution_time']:.3f}秒")
            
            if result['success']:
                # 格式化回應內容
                response = result['response']
                if isinstance(response, str):
                    # 截取回應的前500個字符以便查看
                    preview = response[:500] + "..." if len(response) > 500 else response
                    logger.info(f"回應預覽:\n{preview}")
            else:
                logger.info(f"錯誤: {result['error']}")
        
        # 儲存詳細報告
        self.save_detailed_report()
    
    def save_detailed_report(self):
        """儲存詳細測試報告"""
        report_file = os.path.join(os.path.dirname(__file__), 'test_results.json')
        
        report_data = {
            "test_time": datetime.now().isoformat(),
            "summary": {
                "total": len(self.test_results),
                "passed": sum(1 for r in self.test_results if r["success"]),
                "failed": sum(1 for r in self.test_results if not r["success"])
            },
            "results": self.test_results
        }
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            logger.info(f"\n詳細報告已儲存至: {report_file}")
        except Exception as e:
            logger.error(f"儲存報告失敗: {str(e)}")
    
    async def cleanup(self):
        """清理資源"""
        try:
            if self.facade and hasattr(self.facade, 'shutdown'):
                await self.facade.shutdown()
            logger.info("\n✓ 資源清理完成")
        except Exception as e:
            logger.error(f"清理資源時發生錯誤: {str(e)}")

async def main():
    """主程式"""
    print("=" * 60)
    print("LINE MCP Bot 生產環境查詢測試")
    print("=" * 60)
    
    tester = ProductionQueryTester()
    
    try:
        # 執行測試
        success = await tester.run_tests()
        
        # 返回適當的退出碼
        exit_code = 0 if success else 1
        
        print("\n" + "=" * 60)
        if success:
            print("✓ 所有測試通過！")
        else:
            print("✗ 部分測試失敗，請檢查日誌")
        print("=" * 60)
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n測試被使用者中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n測試過程中發生錯誤: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # 確保在正確的目錄執行
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # 執行測試
    asyncio.run(main())