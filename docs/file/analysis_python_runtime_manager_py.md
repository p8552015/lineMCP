# 📄 `python_runtime_manager.py` 檔案架構分析報告

本報告由 AI 架構師 Serena 根據 `LLM_文件問答樣板_架構師升級完整版.md` 模板，對 `apps/bot/src/nodecomman/implementations/python_runtime_manager.py` 進行分析。

**分析目標**: `apps/bot/src/nodecomman/implementations/python_runtime_manager.py`
**產出日期**: 2024-07-30
**撰寫角色**: AI 架構師 / 技術負責人

---

## 🧩 樣板 1：檔案在專案中扮演的角色

【文件角色摘要】
- 📌 **主要功能與責任**:
  - 此檔案定義了 `PythonRuntimeManager` 和 `PythonProcess` 兩個類別，是 `nodecomman` 子系統中負責**與本地 Python 環境進行實際互動**的具體實現。
  - **核心職責** (`PythonRuntimeManager`):
    1.  **智慧型環境探測**: 這是此類別最亮眼的功能。它不僅僅是檢查 `python` 命令，而是**智慧地探測**多種可能性，包括：
        -   當前正在運行的 Python 解釋器 (`sys.executable`)。
        -   虛擬環境中的 `python` (`os.environ.get('VIRTUAL_ENV')`)。
        -   系統 `PATH` 中的 `python3` 或 `python`。
        -   這種多層次的探測策略極大地提高了在複雜 Python 環境中找到正確解釋器的機率。
    2.  **套件管理器檢測**: 同樣地，它會檢查 `pip3`, `pip` 是否可用，甚至會檢查 `poetry` 是否安裝。
    3.  **依賴管理**: 執行 `pip install` 來安裝指定的 Python 套件。
    4.  **進程工廠**: 創建 `PythonProcess` 的實例。
  - **核心職責** (`PythonProcess`):
    - 與 `NodeJSProcess` 類似，它封裝了 `asyncio.subprocess.Process`，提供了啟動、停止、通訊等生命週期管理功能。

- 🧠 **在系統架構中的定位**:
  - **定位**：`nodecomman` 子系統的**Python 執行引擎**。它是 `UniversalMCPServerFactory` 用來管理 Python 子進程的「策略」實現。
  - **上層來源**：`UniversalMCPServerFactory`。
  - **下游依賴**：Python 的 `sys`, `os`, `shutil`, `asyncio` 等標準庫。

- 🎯 **與 `Node.js` 管理器的比較**:
  - **共同點**: 兩者都實現了相同的 `IRuntimeManager` 和 `IProcess` 介面，都負責環境探測、依賴安裝和進程管理。`Process` 類別的實現（如優雅停止邏輯）非常相似。
  - **差異點**:
    - **環境複雜性**: `PythonRuntimeManager` 的環境探測邏輯遠比 `Node.js` 的複雜。這是因為 Python 的環境管理方式（全域安裝、使用者安裝、虛擬環境、pyenv 等）本身就比 Node.js（通常是單一的全域安裝或透過 nvm 管理）要複雜得多。`_detect_python_executable` 方法中的多步探測策略正是這種複雜性的直接體現。
    - **套件管理器**: `PythonRuntimeManager` 額外檢查了 `poetry` 的可用性，顯示了對現代 Python 開發工具的支援。
    - **信號處理**: `PythonProcess` 的 `send_signal` 方法中包含了對 Windows 平台信號支援有限的特殊處理，這是一個非常細緻且健壯的設計。

---

## 🧩 樣板 2：有哪些類別，以及創建目的與結構特性

【類別分析】
- 類別名稱：`PythonRuntimeManager`
  - 📌 **創建目的**: 實現 `IRuntimeManager`，**應對 Python 環境多樣性和複雜性帶來的挑戰**，為上層提供一個簡單、統一的 Python 環境管理介面。
  - 🧩 **內含哪些關鍵方法與邏輯功能**:
    - `_detect_python_executable`, `_detect_pip_executable`, `_check_poetry_availability`: 這些私有方法構成了環境探測的核心，展示了清晰的邏輯層次和對細節的關注。
    - `get_runtime_info()`: 透過執行 `python --version` 和 `pip --version`，並解析其輸出來獲取資訊。它還會收集已安裝的套件列表，提供了更豐富的環境快照。
    - `install_dependencies()`: 使用探測到的 `pip` 可執行檔來執行 `pip install`。
- 類別名稱：`PythonProcess`
  - 📌 **創建目的**: 實現 `IProcess`，為上層模組提供一個與 `NodeJSProcess` 行為一致的 Python 進程管理物件，從而實現了**多態**。上層的 `UniversalMCPServerFactory` 無需關心它拿到的是 `NodeJSProcess` 還是 `PythonProcess`，因為它們都遵循相同的介面契約。
  - 💡 **設計考量**:
    - **健壯性**: `_detect_*` 方法中的多重 `shutil.which` 呼叫和對 `VIRTUAL_ENV` 的檢查，確保了管理器在各種環境下的健壯性。
    - **跨平台意識**: `send_signal` 中對 `platform.system() == "Windows"` 的判斷，表明開發者充分考慮了跨平台兼容性問題。

---

## 🧱 額外架構師視角建議補充欄位

- 🗂️ **高耦合風險**：**低**。與 `nodejs_runtime_manager.py` 一樣，它對外只暴露標準介面，與外部模組低耦合。
- 🧪 **可測試性**：**中等到高**。與 `Node.js` 管理器類似，測試需要 Mock `sys.executable`, `os.environ`, `shutil.which` 和 `asyncio.create_subprocess_exec` 等。測試的重點應該是驗證其探測邏輯的優先級順序是否正確（例如，虛擬環境中的 Python 是否優先於系統全域的 Python）。
- 🧠 **重構潛力**:
  - **依賴安裝策略**: 目前 `install_dependencies` 只支援 `pip`。可以將其擴展為一個策略模式，如果檢測到 `poetry.lock` 或 `pyproject.toml`，就優先使用 `poetry install`。
  - **虛擬環境創建**: 目前管理器只能**使用**已存在的虛擬環境。一個更強大的版本可以增加 `create_virtual_environment()` 方法，使其能夠為特定的 MCP 伺服器動態創建和管理隔離的虛擬環境，進一步增強環境隔離性。 