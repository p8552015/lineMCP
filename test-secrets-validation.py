#!/usr/bin/env python3
"""
GitHub Secrets 驗證測試腳本
測試關鍵環境變數是否正確載入
"""
import os
import sys

def test_secrets_validation():
    """驗證 GitHub Secrets 環境變數"""
    print("🔐 GitHub Secrets 驗證測試")
    print("=" * 50)
    
    # 必要的環境變數清單
    required_secrets = {
        'LINE_CHANNEL_ACCESS_TOKEN': '驗證 LINE Bot 存取權杖',
        'LINE_CHANNEL_SECRET': '驗證 LINE Bot 頻道密鑰', 
        'GOOGLE_API_KEY': '驗證 Google Gemini API 金鑰',
        'OPENAI_API_KEY': '驗證 OpenAI API 金鑰 (備用)',
        'JWT_SECRET_KEY': '驗證 JWT 簽名密鑰'
    }
    
    results = {}
    all_passed = True
    
    for env_var, description in required_secrets.items():
        value = os.getenv(env_var)
        
        if value:
            # 檢查金鑰格式和長度
            if env_var == 'GOOGLE_API_KEY' and value.startswith('AIza'):
                status = "✅ 正確"
            elif env_var == 'OPENAI_API_KEY' and value.startswith('sk-'):
                status = "✅ 正確" 
            elif env_var == 'LINE_CHANNEL_ACCESS_TOKEN' and len(value) > 50:
                status = "✅ 正確"
            elif env_var == 'LINE_CHANNEL_SECRET' and len(value) > 20:
                status = "✅ 正確"
            elif env_var == 'JWT_SECRET_KEY' and len(value) >= 32:
                status = "✅ 正確"
            else:
                status = f"⚠️  可能有問題 (長度: {len(value)})"
                
            print(f"{description}: {status}")
            results[env_var] = True
        else:
            print(f"{description}: ❌ 未設置")
            results[env_var] = False
            all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("🎉 所有 Secrets 驗證通過！")
        print("CI/CD 流程現在可以正常執行完整測試")
        return 0
    else:
        print("⚠️  部分 Secrets 未正確設置")
        print("請檢查 GitHub Repository Settings > Secrets and variables > Actions")
        return 1

if __name__ == "__main__":
    exit_code = test_secrets_validation()
    sys.exit(exit_code)