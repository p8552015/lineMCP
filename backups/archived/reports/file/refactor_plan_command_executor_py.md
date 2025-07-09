# 📄 `command_executor.py` 重構計畫與架構分析報告

本報告由 AI 架構師 Serena 旨在分析 `apps/bot/src/domain/command_executor.py` 當前的架構問題，並提出具體的重構方案。

**分析目標**: `apps/bot/src/domain/command_executor.py`
**產出日期**: 2024-07-30
**撰寫角色**: AI 架構師 / 技術負責人

---

## 📉 現存架構缺陷分析

目前 `CommandExecutor` 的指令處理流程存在嚴重的設計缺陷，其核心問題在於**存在兩個功能重疊但實現方式不同的指令解析與驗證機制**，違反了「單一事實來源 (Single Source of Truth)」原則。

1.  **第一層解析 (靜態)**: `execute_command` 方法首先呼叫 `models/commands.py` 中的 `parse_command` 函式。此函式依賴一個**硬編碼的列表** (`supported_commands`) 來判斷指令是否有效。這充當了指令系統的**外部守門人**。

2.  **第二層解析 (動態)**: 只有當 `parse_command` 成功後，程式才會繼續從 `CommandRegistry`（一個**動態註冊表**）中查找對應的 `CommandHandler`。

這種雙重驗證機制導致了以下問題：
-   **高維護成本**: 每當新增或移除一個指令時，開發者必須**同時修改兩個地方**：
    1.  在 `CommandExecutor._register_all_commands` 中註冊或移除 `CommandHandler`。
    2.  在 `models/commands.py` 中更新 `supported_commands` 列表。
-   **高風險**: 如果忘記同步這兩個來源，就會導致 Bug。最常見的情況是，註冊了新的 Handler 卻忘記更新列表，導致新指令永遠無法執行。
-   **程式碼冗餘**: `parse_command` 的功能與 `CommandRegistry` 的 `has_command` 方法以及 `CommandHandler` 的 `command_name` 屬性完全重疊。
-   **降低可讀性**: 這種混亂的邏輯使得新開發人員很難理解指令系統的真實工作流程。

**結論**: `models/commands.py` 是一個歷史遺留的技術債，它本應被 `CommandRegistry` 的動態機制完全取代，但卻錯誤地遺留在了核心執行路徑上。

---

## 🛠️ 重構計畫 (Step-by-Step)

我們的目標是**徹底移除對 `models/commands.py` 的依賴**，讓 `CommandRegistry` 成為指令有效性的**唯一事實來源**。

### 步驟 1: 修改 `CommandExecutor`

修改 `execute_command` 方法，使其不再呼叫 `parse_command`，而是直接解析訊息並查詢 `CommandRegistry`。

**修改前**:
```python
# ...
from src.models.commands import parse_command
# ...
    async def execute_command(self, user_id: str, message_text: str) -> Message:
        # ...
        command = parse_command(message_text)
        if not command:
            raise create_command_error(message_text, "無法解析為有效指令")

        handler = self.registry.get_handler(command.name)
        # ...
```

**修改後**:
```python
# ...
# 移除: from src.models.commands import parse_command
# ...
    async def execute_command(self, user_id: str, message_text: str) -> Message:
        # ...
        # 新的、直接的解析邏輯
        if not message_text.startswith("/"):
            raise create_command_error(message_text, "訊息不是一個指令")
        
        parts = message_text[1:].strip().split(maxsplit=1)
        command_name = parts[0].lower()
        args = parts[1].split() if len(parts) > 1 else []

        # 直接查詢註冊表
        if not self.registry.has_command(command_name):
             raise create_command_error(command_name, "未知的指令")

        handler = self.registry.get_handler(command_name)
        # ...
        # 將 command 物件替換為 command_name 和 args
        # result = await handler.handle(user_id, command.args)
        result = await handler.handle(user_id, args)
        # ...
```

### 步驟 2: 修改 `Command` 資料類別的依賴

在理想情況下，`CommandHandler.handle` 應該只接收 `args: list[str]`，而不是整個 `Command` 物件。如果現有程式碼對 `Command` 物件有依賴，需要一併修改。從我們的分析來看，`handle` 簽名是 `(user_id, args)`，所以這一步相對簡單。

### 步驟 3: 重構相關的單元測試

搜索結果顯示，大量單元測試嚴重依賴 `patch("src.models.commands.parse_command")`。這些測試需要被重構。

**測試重構策略**:
-   **目標**: 測試不再模擬 `parse_command`，而是直接與 `CommandExecutor` 或真實的/Mock的 `CommandRegistry` 互動。
-   **修改前**: `patch("...parse_command", return_value=mock_command)`
-   **修改後**:
    -   可以直接實例化一個帶有 Mock Handlers 的 `CommandExecutor`。
    -   然後呼叫 `executor.execute_command("/real_command arg1")`。
    -   或者，如果需要測試找不到指令的情況，則呼叫 `executor.execute_command("/fake_command")`，並斷言它是否拋出預期的異常。

### 步驟 4: 安全刪除 `models/commands.py`

在完成以上所有重構並確保所有測試通過後，`models/commands.py` 檔案將不再被任何地方引用。此時，可以**安全地將其從專案中刪除**。

---

## ✨ 重構後的理想架構

-   `CommandRegistry` 成為**指令集的唯一事實來源**。
-   `CommandExecutor` 的 `execute_command` 邏輯變得非常清晰：
    1.  解析輸入字串得到指令名稱和參數。
    2.  使用指令名稱查詢 `CommandRegistry`。
    3.  如果找到，則執行對應 Handler 的 `handle` 方法。
    4.  如果找不到，則拋出異常。
-   新增一個指令的流程被簡化為**唯一且正確的步驟**：
    1.  創建一個新的 `CommandHandler` 子類別。
    2.  在 `CommandExecutor._register_all_commands` 中實例化並註冊它。
-   **不再有**因為忘記同步硬編碼列表而導致的潛在 Bug。
-   專案的整體架構更加內聚、更少冗餘，技術債被成功償還。 