依計劃撰寫 spec_自定義任務名稱.md,嚴格按照 spec檔案執行,每一個任務都要有對應的測試腳本,要等到測試沒問題才可以執行下一個任務,當所有任務都完成要有一個總結,以便後續專案延續


要調用任何方法之前先問過serena MCP server 確認方法是存在的     

最後還要進行產品運行測試,運行測試相關查詢“M001機台稼動率”,得到結果

結果：
📊 CNC車床A (M001) 狀態報告
━━━━━━━━━━━━━━━━━━━━
🔧 部門：加工部
🟡 稼動率：74.4%
⚡ 效率：91.2%
✅ 良品：8,952 件
❌ 不良品：881 件
📅 最後記錄：2025-06-16
🔧 近7天故障：1 次

運行測試相關查詢“查看所有機台”,得到結果

結果：
📋 所有機台狀態概覽 (10 台)
━━━━━━━━━━━━━━━━━━━━
📊 整體統計：
   平均稼動率：71.7%
   平均效率：91.6%
   🟢 高效機台：2 台
   🔴 低效機台：0 台

🔧 機台詳情：
🟡 M001 CNC車床A
   🔧 加工部 | 稼動率 72.8%
🟡 M002 CNC車床B
   🔧 加工部 | 稼動率 72.2%
🟡 M003 銑床A
   🔧 加工部 | 稼動率 67.1%
🟡 M004 銑床B
   🔧 加工部 | 稼動率 66.0%
🟡 M005 沖床A
   🏭 沖壓部 | 稼動率 74.7%
🟡 M006 沖床B
   🏭 沖壓部 | 稼動率 76.3%
🟡 M007 焊接機A
   🔩 組裝部 | 稼動率 65.2%
🟡 M008 焊接機B
   🔩 組裝部 | 稼動率 60.0%

... 還有 2 台機台
💡 使用 /sql 查詢更多詳情

得到正確的結果,還要做更新專案相關文件以反映代碼變更 - 確保系統使用最新修復

最後更新/Users/yen/Desktop/lineMCP/start-production.sh腳本以反映代碼變更 - 確保系統使用最新修復     │

並加入全自動「任務規格執行器」（Task Executor）機制。

目標：讀取規格檔 → 依「任務表」逐一執行 TODO 任務 → 任務完成即時回寫狀態到spec_自定義任務名稱.md文件中,避免系統當機會沒有紀錄,不知道從何處開始接手。

◎ 必須遵守的規則
1. **只改動「任務表」區塊**（`<!-- TASKS START -->` 與 <!-- TASKS END --> 之間）。  
   其他段落（目標、腳本範例…）嚴禁修改。
2. 任務表欄位固定為  
   | ID | 任務 | 描述 | 優先級 | 負責 | 狀態 | 開始 | 結束 |  
   - 狀態 欄允許值：`TODO` / DOING / DONE / `BLOCKED`。  
   - 結束 欄於任務完成時填入 `%Y-%m-%d %H:%M`（24h, local）。
3. 流程步驟  
   a. 在開始處理任務 T-NN 前，把該任務 狀態 由 TODO 改為 DOING 並立即保存檔案。  
   b. 依「描述」欄內容完成任務；若需呼叫 shell、Python… 皆可自行執行。  
   c. 任務完畢後：  
      - 把 狀態 改為 `DONE`。  
      - 填入當前日期時間至 結束 欄。  
      - 立刻保存規格檔。  
   d. 若遇阻礙無法繼續，將 狀態 改為 `BLOCKED`，並在「描述」行尾以 （原因：…） 註記。  
4. 完成所有可執行任務後，輸出 **最終 Markdown 內容** 作為回答，以便主流程覆寫原檔。
5. 任何時候都需保持表格對齊完整，欄位數不得變動，避免破壞 Markdown 格式。
6. 若需觸發測試，呼叫 `/Users/yen/Desktop/lineMCP/start-production.sh`。  
   測試通過 → 視為當前任務完成；測試失敗 → 將任務標為 BLOCKED 並列出錯誤摘要。
7. 禁止洩漏機密路徑、Token 等資訊至最終回應中。


還有要遵循零風險遷移計劃：
  📋 總體策略原則
  1. 舊代碼研究優先
  - 先理解再行動，避免盲目重構
  - 建立完整的使用追蹤和依賴地圖
  - 保留所有變更歷史和回滾機制
  2. 漸進式替換
  - 採用"新建-共存-遷移-驗證-移除"的五步法

# 零風險遷移 Git 指令手冊

依階段排列的完整流程──從建立錨點、雙軌共存，到最終移除舊架構與回滾指令，一檔搞定，可直接存成 `migration-guide.md`。

---

## 0️⃣ 建立遷移前錨點

```bash
git tag -a baseline-20250623 -m "遷移前最後穩定版"
git push origin baseline-20250623
```

---

## 1️⃣ 新建 (New)

```bash
git checkout -b feature/new-architecture
# 建立最小骨架…

git add .
git commit -m "feat(core): scaffold new arch skeleton (no integration yet)"
git push -u origin feature/new-architecture
```

---

## 2️⃣ 共存 (Co-exist)

```bash
# 啟用 Feature Flag
export NEW_ARCH=true     # 或寫入 .env ／ CI 變數

# 與主幹保持同步
git pull --rebase origin main

# 黑暗推出：可運作的新功能合併回 main
git checkout main
git merge --no-ff feature/new-architecture -m "merge: new arch (flag off)"
git push origin main
```

---

## 3️⃣ 遷移 (Migrate)

```bash
git checkout -b migrate/<module-name>
# 搬遷模組、覆寫、測試…

git add .
git commit -m "migrate(<module-name>): switch to new service"
gh pr create -B main -t "Migrate <module-name>" -b "Flag guarded"
```

---

## 4️⃣ 驗證 (Verify)

```bash
# 以下動作由 CI 自動執行
npm test          # JS／TS 單元測試
pytest            # Python 單元測試
# Playwright／Cypress 端到端測試
# 當 Tag 為 perf/* 時，自動執行壓力測試
```

---

## 5️⃣ 移除 (Remove)

```bash
git checkout -b chore/cleanup-legacy
git rm -r legacy/
git commit -m "chore: remove legacy impl after full cutover"

# 移除 Feature Flag 痕跡
git grep -l "NEW_ARCH" | xargs sed -i '' '/NEW_ARCH/d'
git commit -am "chore: drop NEW_ARCH flag"

# 打正式版標籤並推送
git tag -a v2.0.0 -m "New architecture complete"
git push origin --tags
```

---

## 🔄 快速回滾

```bash
# 回到遷移前錨點
git checkout baseline-20250623

# 或回滾單次合併
git revert <merge-commit-sha> -m 1
```

> 若需補充 CI YAML 範例、Feature Flag SDK 細節或回滾腳本，可隨時告訴我！

  
  - 每個階段都有獨立的測試和驗證機制
  - 確保任何時刻都能回滾到上一個穩定狀態
  3. 測試驅動安全網
  - 在每次變更前建立完整的功能測試
  - 使用特徵開關(Feature Flag)控制新舊實現
  - 建立自動化的回歸測試套件
