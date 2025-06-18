#!/usr/bin/env python3
"""
Services 資料夾重構任務規劃工具
基於分析結果創建具體的改善任務
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

class ServiceRefactorPlanner:
    def __init__(self):
        self.tasks = []
        self.task_counter = 1
    
    def add_task(self, title: str, description: str, priority: str, 
                 estimated_hours: int, dependencies: List[str] = None,
                 category: str = "refactor"):
        task = {
            "id": f"SRF-{self.task_counter:03d}",
            "title": title,
            "description": description,
            "category": category,
            "priority": priority,  # CRITICAL, HIGH, MEDIUM, LOW
            "estimated_hours": estimated_hours,
            "dependencies": dependencies or [],
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "due_date": (datetime.now() + timedelta(days=7)).isoformat()
        }
        self.tasks.append(task)
        self.task_counter += 1
        return task["id"]
    
    def generate_refactor_plan(self):
        """基於分析結果生成重構計劃"""
        
        print("🏗️ 生成 Services 資料夾重構計劃...")
        print("=" * 50)
        
        # Phase 1: 緊急重構 - 解決關鍵問題
        phase1_tasks = [
            {
                "title": "創建命令處理器抽象基類",
                "description": """
創建 CommandHandler 抽象基類和 CommandRegistry：
- 定義 CommandHandler(ABC) 介面
- 實作 CommandRegistry 用於命令註冊
- 設計依賴注入機制
- 撰寫單元測試框架

檔案位置：
- src/services/command/base.py
- src/services/command/registry.py
- tests/test_command_handlers.py
                """,
                "priority": "CRITICAL",
                "hours": 8,
                "deps": []
            },
            {
                "title": "重構 SQL 命令處理器",
                "description": """
從 MessageHandler 中提取 SQL 相關功能：
- 創建 SQLCommandHandler 類別
- 移動所有 _handle_sql_* 方法
- 實作錯誤處理和驗證
- 增加 SQL 注入防護測試

檔案：src/services/command/sql_handler.py
影響：message_handler.py 減少 ~200 行
                """,
                "priority": "CRITICAL", 
                "hours": 6,
                "deps": ["SRF-001"]
            },
            {
                "title": "重構機台狀態命令處理器",
                "description": """
提取機台相關查詢功能：
- 創建 MachineStatusHandler
- 移動 _handle_machine_query_* 方法
- 移動 _get_machine_status_async 等方法
- 優化故障統計查詢邏輯

檔案：src/services/command/machine_handler.py
影響：message_handler.py 減少 ~300 行
                """,
                "priority": "HIGH",
                "hours": 8,
                "deps": ["SRF-001"]
            },
            {
                "title": "重構 Excel/文件命令處理器",
                "description": """
提取 Excel 和文件處理功能：
- 創建 ExcelCommandHandler
- 移動所有 _handle_*_command 方法 (create, read, write, chart, pivot)
- 整合 FlexBuilder 依賴
- 增加文件操作測試

檔案：src/services/command/excel_handler.py
影響：message_handler.py 減少 ~400 行
                """,
                "priority": "HIGH",
                "hours": 10,
                "deps": ["SRF-001"]
            }
        ]
        
        # Phase 2: 架構優化
        phase2_tasks = [
            {
                "title": "統一 MCP 客戶端實作",
                "description": """
解決重複的 MCP 客戶端問題：
- 定義 MCPClientInterface 介面
- 實作 MCPClientFactory 工廠模式
- 整合 mcp_client.py 和 simple_mcp_client.py
- 移除重複程式碼
- 增加錯誤恢復機制

檔案：
- src/services/mcp/interface.py
- src/services/mcp/factory.py
- 刪除：simple_mcp_client.py
                """,
                "priority": "HIGH",
                "hours": 6,
                "deps": ["SRF-002", "SRF-003"]
            },
            {
                "title": "重構 FlexBuilder 模組化",
                "description": """
將 1,313 行的 FlexBuilder 拆分：
- 創建 BaseFlexBuilder 抽象類別
- 實作 ListFlexBuilder, ChartFlexBuilder, TableFlexBuilder
- 提取共用元件到 FlexComponents
- 使用建造者模式設計 API
- 減少硬編碼 JSON 結構

新結構：
- src/services/flex/base.py
- src/services/flex/builders/
- src/services/flex/components.py
                """,
                "priority": "MEDIUM",
                "hours": 12,
                "deps": ["SRF-004"]
            },
            {
                "title": "實作服務依賴注入容器",
                "description": """
創建依賴注入系統：
- 設計 ServiceContainer 類別
- 實作服務生命週期管理
- 配置驅動的服務選擇
- 支援服務降級和故障恢復
- 撰寫完整的整合測試

檔案：src/services/container.py
配置：src/config/services.yaml
                """,
                "priority": "MEDIUM", 
                "hours": 8,
                "deps": ["SRF-001", "SRF-005"]
            }
        ]
        
        # Phase 3: 測試和文檔
        phase3_tasks = [
            {
                "title": "建立完整測試套件",
                "description": """
為所有新的命令處理器創建測試：
- 單元測試覆蓋率 >90%
- 整合測試驗證命令路由
- 效能測試確保回應時間
- Mock 外部依賴 (OpenAI, MCP)
                """,
                "priority": "HIGH",
                "hours": 16,
                "deps": ["SRF-002", "SRF-003", "SRF-004"]
            },
            {
                "title": "更新文檔和架構圖",
                "description": """
更新專案文檔：
- 重構後的架構圖
- 新的命令處理器使用說明
- 開發者指南更新
- API 文檔生成
                """,
                "priority": "LOW",
                "hours": 4,
                "deps": ["SRF-008"]
            }
        ]
        
        # 添加所有任務
        all_phases = [
            ("Phase 1: 緊急重構", phase1_tasks),
            ("Phase 2: 架構優化", phase2_tasks), 
            ("Phase 3: 測試和文檔", phase3_tasks)
        ]
        
        for phase_name, tasks in all_phases:
            print(f"\n📋 {phase_name}")
            print("-" * 30)
            
            for task in tasks:
                task_id = self.add_task(
                    title=task["title"],
                    description=task["description"],
                    priority=task["priority"],
                    estimated_hours=task["hours"],
                    dependencies=task["deps"]
                )
                
                priority_emoji = {
                    "CRITICAL": "🔴",
                    "HIGH": "🟠", 
                    "MEDIUM": "🟡",
                    "LOW": "🟢"
                }
                
                print(f"  {priority_emoji[task['priority']]} [{task_id}] {task['title']}")
                print(f"     ⏱️ 預估: {task['hours']} 小時")
                if task['deps']:
                    print(f"     🔗 依賴: {', '.join(task['deps'])}")
                print()
    
    def generate_implementation_guide(self):
        """生成實作指南"""
        
        print("\n🛠️ 實作指南")
        print("=" * 50)
        
        print("""
📁 重構後的目錄結構：

/src/services/
├── command/                    # 命令處理器模組
│   ├── __init__.py
│   ├── base.py                # CommandHandler 抽象基類
│   ├── registry.py            # CommandRegistry
│   ├── sql_handler.py         # SQL 命令處理
│   ├── machine_handler.py     # 機台狀態命令
│   └── excel_handler.py       # Excel 文件命令
├── mcp/                       # MCP 客戶端模組
│   ├── __init__.py
│   ├── interface.py           # MCPClientInterface
│   ├── factory.py             # MCPClientFactory
│   └── clients/
│       ├── stdio_client.py    # 原 mcp_client.py
│       └── simple_client.py   # 原 simple_mcp_client.py
├── flex/                      # Flex UI 建構器模組
│   ├── __init__.py
│   ├── base.py               # BaseFlexBuilder
│   ├── components.py         # 共用 UI 元件
│   └── builders/
│       ├── list_builder.py
│       ├── chart_builder.py
│       └── table_builder.py
├── message_handler.py         # 精簡版 (僅路由邏輯)
├── container.py               # 依賴注入容器
├── cost_tracker.py           # 保持不變
├── openai_client.py          # 保持不變
└── taskmaster_integration.py # 保持不變

🎯 預期效益：

1. **程式碼品質提升**
   - MessageHandler 從 1,172 行減少到 ~200 行
   - 每個命令處理器職責單一，易於維護
   - 提升測試覆蓋率和測試品質

2. **開發效率提升**
   - 新增命令不需修改核心類別
   - 並行開發不同功能模組
   - 減少程式碼衝突和錯誤

3. **系統穩定性提升**
   - 統一的 MCP 客戶端減少錯誤
   - 依賴注入支援服務降級
   - 更好的錯誤隔離和恢復

4. **效能最佳化**
   - 延遲載入不必要的服務
   - 更好的資源管理
   - 快取策略改善

⚠️ 風險控制：

1. **漸進式重構**：一次重構一個模組，確保系統穩定
2. **完整測試**：每個階段都要有測試覆蓋
3. **回滾計劃**：保留原始程式碼備份
4. **效能監控**：確保重構不影響回應時間

📊 總預估時間：64 小時 (約 8 個工作天)
🎯 建議執行順序：Phase 1 → Phase 2 → Phase 3
        """)
    
    def save_tasks_json(self, filename: str):
        """儲存任務到 JSON 檔案"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "project": "Services 資料夾重構",
                "generated_at": datetime.now().isoformat(),
                "total_tasks": len(self.tasks),
                "total_estimated_hours": sum(task["estimated_hours"] for task in self.tasks),
                "tasks": self.tasks
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 任務清單已儲存到: {filename}")

def main():
    planner = ServiceRefactorPlanner()
    
    print("🔍 Services 資料夾結構重構計劃")
    print("=" * 50)
    print("基於架構分析，MessageHandler 已成為 1,172 行的'神類'")
    print("需要緊急重構以避免技術債務惡化")
    print()
    
    # 生成重構計劃
    planner.generate_refactor_plan()
    
    # 生成實作指南
    planner.generate_implementation_guide()
    
    # 儲存任務清單
    planner.save_tasks_json("services_refactor_tasks.json")
    
    print("\n🎯 下一步行動：")
    print("1. 執行: /task create 創建命令處理器抽象基類")
    print("2. 開始 Phase 1 的緊急重構任務")
    print("3. 確保每個階段都有完整測試")
    print("4. 監控重構對系統效能的影響")

if __name__ == "__main__":
    main()