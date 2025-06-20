# ADR-005: MCP 客戶端統一策略

## 狀態
**提議** - 待定

## 背景

在 LINE MCP 智慧製造監控系統的架構演進過程中，我們發現了一個重要的架構不一致問題：OpenAI 相關服務（OpenAIClient、NaturalLanguageToSQLService）繞過了統一的 MCP 客戶端抽象層（UnifiedMCPClient），直接實現自己的通訊邏輯。

這種不一致性違反了架構設計的統一性原則，也與我們在 ADR-001（依賴注入架構）和 ADR-004（SOLID 原則實現）中建立的企業級標準相矛盾。

### 當前架構狀況
- **統一抽象**: `UnifiedMCPClient` 提供標準化的 MCP 通訊介面
- **大部分服務**: 通過 `ProductionMCPClient` 統一接入 MCP 服務器
- **異常服務**: OpenAI 相關服務直接調用 OpenAI API，繞過 MCP 架構
- **影響範圍**: AI 模型服務、自然語言處理服務

### 問題發現
- **代碼審查期間**: 2025-06-20 企業級架構審查
- **觸發因素**: SOLID 原則實施過程中發現的不一致性
- **影響評估**: 架構完整性、維護複雜度、監控困難

## 問題

### 架構不一致性問題

#### 1. 混合通訊模式
```python
# 統一 MCP 模式 (ProductionMCPClient)
database_result = mcp_client.execute_query(sql_query)

# 直接 API 模式 (OpenAIClient)  
openai_result = openai_client.chat.completions.create(...)
```

#### 2. 配置管理分散
- **MCP 服務**: 統一配置在 `mcp_config.py`
- **OpenAI 服務**: 獨立配置在環境變數中
- **監控困難**: 無法統一監控所有外部服務調用

#### 3. 錯誤處理不一致
- **MCP 錯誤**: 統一的 `MCPException` 處理
- **OpenAI 錯誤**: 獨立的錯誤處理邏輯
- **日誌格式**: 不同的日誌結構和格式

#### 4. 測試複雜度
- **MCP 服務**: 可通過 Mock UnifiedMCPClient 統一測試
- **OpenAI 服務**: 需要額外的 Mock 機制
- **整合測試**: 需要處理兩套不同的 Mock 策略

### 具體影響分析

#### 維護複雜度
- **雙重維護負擔**: 需要維護兩套不同的通訊機制
- **知識分散**: 團隊需要掌握 MCP 協議和 OpenAI API 兩套知識
- **調試困難**: 問題排查需要檢查不同的日誌和監控點

#### 架構完整性
- **違反統一性**: 破壞了統一 MCP 架構的完整性
- **擴展困難**: 新增 AI 服務時面臨選擇困難
- **監控盲點**: 無法統一監控所有外部服務的效能和可用性

## 考慮的選項

### 選項 1: 維持現狀，接受雙重架構
- **優點**:
  - 無需重構，風險最低
  - OpenAI 服務繼續正常運作
  - 短期內無額外開發成本
- **缺點**:
  - 架構不一致問題持續存在
  - 違反 SOLID 原則和企業級標準
  - 長期維護成本增加
  - 監控和錯誤處理分散
  - 團隊認知負擔加重

### 選項 2: OpenAI 服務完全脫離 MCP 架構
- **優點**:
  - 清晰的架構邊界
  - OpenAI 服務可專注於自身優化
  - 避免 MCP 協議的限制
- **缺點**:
  - 進一步破壞架構統一性
  - 失去統一監控和管理的優勢
  - 違背 MCP 作為統一通訊協議的初衷
  - 不符合企業級標準

### 選項 3: 將 OpenAI API 包裝為 MCP 服務 (推薦)
- **優點**:
  - 完全統一 MCP 架構
  - 保持 OpenAI 功能不變
  - 統一的監控、錯誤處理、配置管理
  - 符合 SOLID 原則和企業級標準
  - 易於測試和維護
- **缺點**:
  - 需要額外的 MCP 包裝層
  - 短期內有重構成本
  - 可能增加輕微的效能開銷

### 選項 4: 創建抽象的外部服務閘道
- **優點**:
  - 統一外部服務接入模式
  - 保持各服務的獨立性
  - 相對較小的重構範圍
- **缺點**:
  - 增加額外的抽象層
  - 未完全解決 MCP 架構統一性問題
  - 複雜度增加

## 決策

我們**暫時提議**選擇 **選項 3: 將 OpenAI API 包裝為 MCP 服務**，理由如下：

1. **架構統一性**: 實現完全統一的 MCP 通訊架構
2. **SOLID 原則**: 符合依賴倒置和介面隔離原則
3. **企業級標準**: 滿足統一監控、錯誤處理、配置管理的要求
4. **長期價值**: 為未來整合更多 AI 服務奠定基礎
5. **可維護性**: 統一的架構模式降低維護複雜度

**注意**: 此決策目前為提議狀態，需要進一步的技術驗證和團隊討論。

## 結果和影響

### 正面影響（如果實施）
- **架構完整性**: 實現 100% 統一的 MCP 通訊架構
- **監控統一**: 所有外部服務調用統一監控和日誌
- **錯誤處理統一**: 一致的錯誤處理和恢復機制
- **測試簡化**: 統一的 Mock 策略，提升測試效率
- **配置集中**: 所有外部服務配置集中管理
- **擴展便利**: 新增 AI 服務時遵循統一模式

### 負面影響（如果實施）
- **重構成本**: 需要重構 OpenAI 相關服務
- **效能開銷**: MCP 包裝層可能帶來輕微效能影響
- **學習成本**: 團隊需要學習 OpenAI MCP 包裝實現
- **風險增加**: 重構過程中的潛在風險

### 技術風險
- **相容性風險**: OpenAI API 的某些特性可能難以透過 MCP 協議表達
- **效能風險**: 額外的協議轉換可能影響 AI 服務回應時間
- **維護風險**: MCP 包裝層需要隨 OpenAI API 變更而更新

## 實施細節（提議）

### Phase 1: 設計 OpenAI MCP 服務器

#### MCP 服務器架構
```typescript
// openai-mcp-server/src/index.ts
interface OpenAIMCPServer extends MCPServer {
  // 支援的工具
  tools: {
    "openai_chat": OpenAIChatTool,
    "openai_completion": OpenAICompletionTool,
    "openai_embedding": OpenAIEmbeddingTool
  }
}

// 範例工具定義
interface OpenAIChatTool {
  name: "openai_chat",
  description: "使用 OpenAI Chat API 進行對話",
  inputSchema: {
    type: "object",
    properties: {
      model: { type: "string" },
      messages: { type: "array" },
      temperature: { type: "number" },
      max_tokens: { type: "number" }
    }
  }
}
```

#### 工具實現範例
```typescript
async function handleOpenAIChat(args: OpenAIChatArgs): Promise<ToolResult> {
  try {
    const response = await openaiClient.chat.completions.create({
      model: args.model,
      messages: args.messages,
      temperature: args.temperature,
      max_tokens: args.max_tokens
    });
    
    return {
      content: [{
        type: "text",
        text: JSON.stringify(response)
      }]
    };
  } catch (error) {
    return {
      content: [{
        type: "text", 
        text: `錯誤: ${error.message}`
      }],
      isError: true
    };
  }
}
```

### Phase 2: 重構 Python 客戶端

#### 統一的 OpenAI 服務
```python
class OpenAIMCPService:
    """透過 MCP 協議調用 OpenAI 服務"""
    
    def __init__(self, mcp_client: IUnifiedMCPClient):
        self._mcp_client = mcp_client
    
    async def chat_completion(
        self, 
        model: str, 
        messages: List[Dict], 
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> ChatCompletionResponse:
        """透過 MCP 協議調用 OpenAI Chat API"""
        
        result = await self._mcp_client.call_tool(
            "openai_chat",
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        )
        
        if result.is_error:
            raise OpenAIException(result.content)
        
        return ChatCompletionResponse.from_json(result.content)
```

#### 重構現有服務
```python
class NaturalLanguageToSQLService:
    """重構後的 NL to SQL 服務"""
    
    def __init__(self, openai_service: OpenAIMCPService):
        self._openai_service = openai_service
    
    async def convert_to_sql(self, natural_query: str) -> SQLQuery:
        """使用統一的 MCP 介面調用 OpenAI"""
        
        response = await self._openai_service.chat_completion(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": natural_query}
            ]
        )
        
        return self._parse_sql_response(response)
```

### Phase 3: 配置統一

#### MCP 配置更新
```python
# config/mcp_config.py
MCP_SERVERS = {
    "sqlite": {
        "url": "http://localhost:3003",
        "tools": ["query", "schema"]
    },
    "postgres": {
        "url": "http://localhost:3002", 
        "tools": ["query", "schema"]
    },
    "openai": {  # 新增
        "url": "http://localhost:3004",
        "tools": ["openai_chat", "openai_completion", "openai_embedding"]
    }
}
```

### Phase 4: 測試和驗證

#### 統一測試策略
```python
class TestOpenAIMCPService:
    def setup_method(self):
        # 統一的 Mock 策略
        self.mock_mcp_client = Mock(spec=IUnifiedMCPClient)
        self.openai_service = OpenAIMCPService(self.mock_mcp_client)
    
    async def test_chat_completion(self):
        # 模擬 MCP 回應
        self.mock_mcp_client.call_tool.return_value = ToolResult(
            content='{"choices": [{"message": {"content": "SELECT * FROM users"}}]}'
        )
        
        result = await self.openai_service.chat_completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Show all users"}]
        )
        
        assert result.choices[0].message.content == "SELECT * FROM users"
```

## 驗證標準

### 技術驗證
- [ ] **OpenAI MCP 服務器**: 成功包裝所有必要的 OpenAI API
- [ ] **協議相容性**: 確保 OpenAI 功能完全透過 MCP 協議可用
- [ ] **效能基準**: MCP 包裝不影響 AI 服務回應時間（增加 < 100ms）
- [ ] **錯誤處理**: OpenAI 錯誤正確透過 MCP 協議傳遞

### 架構驗證
- [ ] **統一性檢查**: 所有外部服務調用都通過 UnifiedMCPClient
- [ ] **配置集中**: 所有 MCP 服務器配置在 mcp_config.py 中管理
- [ ] **監控統一**: 統一的監控儀表板顯示所有 MCP 服務狀態
- [ ] **日誌一致**: 所有 MCP 調用使用相同的日誌格式

### 功能驗證
- [ ] **AI 功能**: 所有現有 AI 功能在重構後正常運作
- [ ] **測試通過**: 所有相關單元測試和整合測試通過
- [ ] **效能要求**: 系統整體效能不受影響
- [ ] **錯誤處理**: 錯誤情況下的行為與重構前一致

## 相關資源

- [ADR-001: 依賴注入架構設計](./001-dependency-injection-architecture.md)
- [ADR-004: SOLID 原則實現策略](./004-solid-principles-implementation.md)
- [UnifiedMCPClient 實現](../../../apps/bot/src/services/unified_mcp_client.py)
- [ProductionMCPClient 實現](../../../apps/bot/src/services/production_mcp_client.py)
- [OpenAIClient 當前實現](../../../apps/bot/src/services/openai_client.py)
- [NaturalLanguageToSQLService 實現](../../../apps/bot/src/services/nl_to_sql_service.py)
- [MCP 協議規範](https://spec.modelcontextprotocol.io/)
- [OpenAI API 文檔](https://platform.openai.com/docs/api-reference)

## 修訂歷史

| 日期 | 變更 | 作者 |
|------|------|------|
| 2025-06-20 | 初始版本，提議 MCP 客戶端統一策略 | Claude Code Assistant |

---

## 下一步行動

### 即時行動
1. **技術驗證**: 創建 OpenAI MCP 服務器原型
2. **效能測試**: 測量 MCP 包裝的效能影響
3. **相容性測試**: 驗證 OpenAI API 功能的 MCP 表達能力

### 決策標準
- **技術可行性**: 原型驗證成功
- **效能接受度**: 效能影響在可接受範圍內
- **團隊共識**: 開發團隊達成一致意見
- **業務影響**: 確保不影響現有業務功能

### 替代方案
如果技術驗證發現重大問題，將考慮：
- **選項 4**: 創建抽象的外部服務閘道
- **混合方案**: 部分統一，保留關鍵服務的獨立性

---

*📝 注意：此 ADR 目前處於提議狀態，需要進行技術驗證和團隊討論後才能最終決定是否實施。*