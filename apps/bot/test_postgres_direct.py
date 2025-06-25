#!/usr/bin/env python3
"""
直接測試 PostgreSQL MCP 進程
"""

import asyncio
import subprocess
import time
import signal
import os


async def test_postgres_mcp_direct():
    """直接測試 PostgreSQL MCP 服務器"""
    print("🐘 直接測試 PostgreSQL MCP 服務器")
    
    try:
        # 構建命令
        npx_path = "/Users/yen/.nvm/versions/node/v22.16.0/bin/npx"
        command = [
            npx_path,
            "-y",
            "@modelcontextprotocol/server-postgres",
            "postgresql://admin:admin@localhost:5432/mydb"
        ]
        
        print(f"📋 執行命令: {' '.join(command)}")
        
        # 啟動進程
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(os.environ, NODE_ENV="production", PYTHONUNBUFFERED="1")
        )
        
        print(f"✅ 進程已啟動: PID {process.pid}")
        
        # 發送初始化請求
        init_request = '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0.0"}}}\n'
        
        print("📤 發送初始化請求...")
        process.stdin.write(init_request.encode())
        await process.stdin.drain()
        
        # 等待響應
        print("📥 等待響應...")
        try:
            stdout_data = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
            if stdout_data:
                response = stdout_data.decode().strip()
                print(f"✅ 收到響應: {response[:200]}...")
                
                # 發送工具列表請求
                tools_request = '{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}\n'
                print("📤 發送工具列表請求...")
                process.stdin.write(tools_request.encode())
                await process.stdin.drain()
                
                # 等待工具列表響應
                tools_data = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
                if tools_data:
                    tools_response = tools_data.decode().strip()
                    print(f"✅ 工具列表響應: {tools_response[:200]}...")
                    print("🎉 PostgreSQL MCP 服務器正常工作")
                    result = True
                else:
                    print("❌ 未收到工具列表響應")
                    result = False
            else:
                print("❌ 未收到初始化響應")
                result = False
                
        except asyncio.TimeoutError:
            print("❌ 響應超時")
            result = False
        
        # 檢查進程狀態
        if process.returncode is None:
            print(f"🔄 進程仍在運行: PID {process.pid}")
        else:
            print(f"❌ 進程已退出: code {process.returncode}")
            stderr_data = await process.stderr.read()
            if stderr_data:
                print(f"❌ 錯誤輸出: {stderr_data.decode()}")
        
        # 清理進程
        try:
            print("🧹 終止進程...")
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=5.0)
            print("✅ 進程已終止")
        except Exception as e:
            print(f"⚠️ 進程終止失敗: {e}")
            try:
                process.kill()
                await process.wait()
                print("✅ 進程已強制終止")
            except Exception as kill_e:
                print(f"❌ 強制終止失敗: {kill_e}")
        
        return result
        
    except Exception as e:
        print(f"❌ 測試異常: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函數"""
    print("🚀 開始 PostgreSQL MCP 直接測試")
    
    success = await test_postgres_mcp_direct()
    
    if success:
        print("🎉 PostgreSQL MCP 服務器測試成功")
        return 0
    else:
        print("❌ PostgreSQL MCP 服務器測試失敗")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))