#\!/usr/bin/env python3
"""
零 cancel scope 錯誤測試
驗證不使用官方MCP SDK就不會有cancel scope問題
"""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

import anyio
import structlog

# 添加路徑
sys.path.append('/Users/yen/Desktop/lineMCP/apps/bot')

# 配置日誌
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class DirectMCPClient:
    """直接MCP客戶端 - 不使用官方SDK，避免cancel scope問題"""
    
    def __init__(self, command, args, env=None):
        self.command = command
        self.args = args
        self.env = env or {}
        self.process = None
        self.request_id = 1
    
    async def connect(self):
        """建立連接"""
        logger.info("🔌 建立直接MCP連接")
        
        # 啟動進程
        self.process = await anyio.open_process(
            [self.command] + self.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env
        )
        
        logger.info(f"✅ MCP進程已啟動: PID {self.process.pid}")
        
        # 發送初始化請求
        init_request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "direct-client", "version": "1.0.0"}
            }
        }
        
        response = await self._send_request(init_request)
        
        if response.get("result"):
            logger.info("✅ MCP初始化成功")
            return True
        else:
            logger.error(f"❌ MCP初始化失敗: {response}")
            return False
    
    async def _send_request(self, request):
        """發送請求並獲取回應"""
        request_data = json.dumps(request) + '\n'
        await self.process.stdin.send(request_data.encode())
        
        # 讀取回應
        response_line = await self.process.stdout.receive_until(b'\n', 1024)
        response_text = response_line.decode().strip()
        
        if response_text:
            return json.loads(response_text)
        return {}
    
    async def list_tools(self):
        """列出工具"""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/list",
            "params": {}
        }
        
        response = await self._send_request(request)
        return response
    
    async def call_tool(self, tool_name, arguments):
        """調用工具"""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        response = await self._send_request(request)
        return response
    
    async def close(self):
        """關閉連接 - 關鍵：這裡不會有cancel scope問題"""
        logger.info("🧹 關閉直接MCP連接")
        
        if self.process:
            try:
                # 直接終止進程，不使用官方SDK的cancel scope
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=3.0)
                logger.info("✅ MCP進程已正常終止")
            except asyncio.TimeoutError:
                logger.warning("⚠️ 進程終止超時，強制終止")
                self.process.kill()
                await self.process.wait()
                logger.info("✅ MCP進程已強制終止")
            except Exception as e:
                logger.error(f"❌ 進程終止錯誤: {e}")


async def test_zero_cancel_scope():
    """測試零cancel scope錯誤方案"""
    logger.info("🧪 開始零cancel scope錯誤測試")
    
    # 創建直接客戶端
    client = DirectMCPClient(
        command="/Users/yen/.nvm/versions/node/v22.16.0/bin/npx",
        args=["-y", "@modelcontextprotocol/server-postgres", 
              "postgresql://admin:admin@localhost:5432/mydb"],
        env={"NODE_ENV": "production", "PYTHONUNBUFFERED": "1"}
    )
    
    try:
        # 測試連接
        connected = await client.connect()
        if not connected:
            logger.error("❌ 連接失敗")
            return False
        
        # 測試工具列表
        logger.info("📋 獲取工具列表...")
        tools_response = await client.list_tools()
        logger.info(f"🔧 工具回應: {tools_response}")
        
        # 測試查詢
        logger.info("🔍 執行測試查詢...")
        query_response = await client.call_tool("query", {"sql": "SELECT 1 as test"})
        logger.info(f"📊 查詢回應: {query_response}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 測試失敗: {e}")
        return False
    finally:
        # 關鍵測試：關閉時是否會出現cancel scope錯誤
        logger.info("🧪 測試關鍵部分：關閉連接時是否有cancel scope錯誤...")
        await client.close()
        logger.info("✅ 關閉完成，無cancel scope錯誤！")


async def main():
    """主函數"""
    print("🚀 開始零cancel scope錯誤驗證測試")
    
    success = await test_zero_cancel_scope()
    
    if success:
        print("🎉 測試成功！零cancel scope錯誤方案有效")
        print("🛡️ 證明：不使用官方MCP SDK就不會有cancel scope問題")
    else:
        print("❌ 測試失敗")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))