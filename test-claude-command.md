# Claude Code 自定義指令測試指南

## ✅ 已完成設置

### 📁 檔案結構
```
/Users/yen/Desktop/lineMCP/
└── .claude/
    └── commands/
        └── find-root-cause.md
```

### 📄 指令內容
檔案路徑：`.claude/commands/find-root-cause.md`

指令使用 `$ARGUMENTS` 語法來接收參數，符合 Claude Code 2025 年的標準。

## 🧪 測試步驟

### 1. 確認當前目錄
確保您在 `/Users/yen/Desktop/lineMCP` 目錄中執行 Claude Code

### 2. 啟動 Claude Code
```bash
cd /Users/yen/Desktop/lineMCP
claude
```

### 3. 測試自定義指令
在 Claude Code 互動環境中輸入：
```
/project:find-root-cause 檢查程式品質
```

### 4. 預期輸出
```
針對 檢查程式品質，請使用Serena進行深度研究，找到真正問題的原因才能進行，程式碼的修改。

## 指導原則

1. **深度研究優先**：使用 Serena MCP 工具進行詳細分析
2. **問題根源定位**：找到真正的問題原因，而非表面症狀
3. **謹慎修改**：確認問題原因後才進行程式碼修改
4. **系統性思考**：考慮修改對整體系統的影響

## 建議步驟

- 使用 Serena 工具檢查相關檔案和程式碼
- 分析問題的根本原因
- 評估可能的解決方案
- 考慮修改的風險和影響
- 實施修改並驗證結果
```

## 🔍 故障排除

### 如果指令無法使用：
1. 確認檔案路徑正確：`.claude/commands/find-root-cause.md`
2. 確認在專案根目錄啟動 Claude Code
3. 確認 Claude Code 版本為 1.0.38 或更新版本
4. 嘗試輸入 `/` 查看可用指令列表

### 替代測試方法：
如果專案指令無法使用，可以建立全域指令：
```bash
mkdir -p ~/.claude/commands
cp .claude/commands/find-root-cause.md ~/.claude/commands/
```

然後使用 `/find-root-cause 檢查程式品質`

## 📝 使用範例

```
/project:find-root-cause 登入流程錯誤
/project:find-root-cause 資料庫連接問題  
/project:find-root-cause API回應超時
/project:find-root-cause 記憶體洩漏
```