# Claude CLI 自定義指令（可接受參數版本）：find-root-cause

這份文件說明如何建立一個 **可傳入參數** 的 Claude CLI 自定義指令 `find-root-cause`。  
指令可接受 `--topic` 參數，動態提醒不同的研究範疇。

---

## 📁 步驟 1：建立 Plugin 資料夾與檔案

```bash
mkdir -p ~/claude-plugins
cd ~/claude-plugins
nano find-root-cause.yaml
```

---

## ✍️ 步驟 2：在 `find-root-cause.yaml` 貼上以下內容

```yaml
name: find-root-cause
description: 針對指定問題提醒先使用Serena進行深入研究
args:
  - name: topic
    description: 要分析的問題主題
    required: true
run: |
  echo "針對 {{topic}}，請使用Serena進行深度研究，找到真正問題的原因才能進行，程式碼的修改"
```

---

## 🛠️ 步驟 3：設定 Plugin 路徑環境變數

將下列內容加入你的 `~/.bashrc` 或 `~/.zshrc`：

```bash
export CLAUDE_PLUGIN_DIR=$HOME/claude-plugins
```

儲存後重新載入：

```bash
source ~/.zshrc  # 或 source ~/.bashrc
```

---

## 🚀 步驟 4：執行自定義指令

### 範例

```bash
claude find-root-cause --topic "登入流程錯誤"
```

輸出範例：

```
針對 登入流程錯誤，請使用Serena進行深度研究，找到真正問題的原因才能進行，程式碼的修改
```

---

## 🔄 常見延伸整合

1. **Git pre-commit hook**  
   在 `pre-commit` 腳本中呼叫此指令，強制開發者在提交前檢查並標註研究主題。

2. **CI/CD Pipeline**  
   在 CI 階段提醒開發團隊釐清問題根因後再佈署修改。

3. **Shell Script 整合**  
   將指令封裝於專案的 `scripts/validate.sh` 供團隊統一使用。

---

如需更多進階功能（​例如：自動開啟 Serena 分析報告、推送 Slack 通知等），請再提出需求！