# 安全政策

## 支援的版本

目前支援安全更新的版本：

| 版本 | 支援 |
| --- | --- |
| 2.x.x | ✅ |
| 1.x.x | ❌ |

## 回報安全漏洞

我們非常重視系統的安全性。如果您發現安全漏洞，請遵循以下步驟：

### 🔒 私密回報

**請勿**在公開的 GitHub Issues 中回報安全漏洞。

請透過以下方式私密回報：

1. **GitHub Security Advisories**（推薦）
   - 前往本專案的 [Security 頁籤](../../security)
   - 點擊 "Report a vulnerability"
   - 填寫詳細資訊

2. **電子郵件**
   - 發送至：security@yourcompany.com
   - 主旨：[SECURITY] 漏洞回報 - [簡短描述]

### 📝 回報內容

請在您的安全回報中包含以下資訊：

- **漏洞類型**：例如 SQL 注入、XSS、CSRF 等
- **影響範圍**：哪些系統/功能受到影響
- **重現步驟**：詳細的重現方法
- **影響評估**：可能造成的損害
- **建議修復**：如果有修復建議請提供
- **您的聯繫方式**：以便我們跟進

### ⏱️ 回應時程

我們承諾：

- **24 小時內**：確認收到您的回報
- **7 天內**：提供初步評估和時程規劃
- **30 天內**：發布修復程式（視嚴重程度而定）

### 🏆 致謝政策

對於回報有效安全漏洞的研究人員，我們將：

1. 在修復發布後公開致謝（如您同意）
2. 在我們的安全致謝頁面列出您的貢獻
3. 對於嚴重漏洞，可能提供合理的獎勵

### 🛡️ 安全最佳實踐

在使用本系統時，請遵循以下安全最佳實踐：

#### 環境變數管理
- 絕不在代碼中硬編碼祕密
- 使用 `.env` 檔案存放敏感資訊
- 確保 `.env` 檔案已加入 `.gitignore`
- 定期輪換 API 金鑰和密碼

#### 依賴管理
- 定期更新依賴套件
- 監控安全告警
- 使用 `poetry audit` 和 `npm audit` 檢查漏洞

#### 部署安全
- 使用 HTTPS 加密傳輸
- 實施適當的防火牆規則
- 啟用日誌監控
- 定期備份重要資料

#### 代碼安全
- 進行代碼審查
- 使用靜態安全分析工具
- 實施輸入驗證
- 遵循最小權限原則

### 🚨 已知安全注意事項

#### LINE Bot Webhook
- Webhook 端點需要適當的簽名驗證
- 避免在日誌中記錄敏感使用者資料
- 實施速率限制防止濫用

#### MCP 連接
- MCP 服務器連接應在受信任環境中運行
- 避免暴露 MCP 端點到公網
- 監控異常的 MCP 查詢活動

#### 資料庫安全
- 使用參數化查詢防止 SQL 注入
- 限制資料庫使用者權限
- 加密敏感資料欄位

### 📋 安全檢查清單

在部署前，請確保：

- [ ] 所有環境變數正確設置
- [ ] 敏感資訊未提交到版本控制
- [ ] 依賴套件無已知安全漏洞
- [ ] 實施適當的存取控制
- [ ] 啟用安全日誌記錄
- [ ] 配置備份和災難恢復

### 🔍 自動化安全檢查

本專案實施了以下自動化安全檢查：

- **祕密掃描**：TruffleHog + detect-secrets
- **依賴掃描**：Safety (Python) + npm audit (Node.js)
- **靜態分析**：CodeQL + Semgrep + Bandit
- **容器掃描**：Trivy + Grype
- **許可證檢查**：自動檢查禁用許可證
- **SBOM 生成**：軟體物料清單追蹤

### 📚 安全資源

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE/SANS Top 25](https://www.sans.org/top25-software-errors/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Python Security Best Practices](https://python.org/dev/security/)
- [Node.js Security Best Practices](https://nodejs.org/en/docs/guides/security/)

### 📞 緊急聯繫

對於嚴重安全事件，請立即聯繫：

- **緊急熱線**：+886-XXX-XXXX-XXXX
- **事件回應小組**：incident-response@yourcompany.com

---

**最後更新**：2025-06-23  
**版本**：1.0