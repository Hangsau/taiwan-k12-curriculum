# CLAUDE.md — taiwan-k12-curriculum

> **這是交接單，不是 README。** 給未來接手這個專案的 Claude session 看。
> 建立：2026-06-23
> 維護者：Hangsau

---

## 0. 接手前先讀這段（STATE）

接手 session 開始時，**先看這個區塊**判斷最新狀態：

- **最後更新**：2026-06-23（Opus session：跨平台修復 + 文件對齊 + 現況評估）
- **當前 Phase**：P1 結構化 + 驗證 ✅ 完成；P2 / P3 尚未開工
- **內容進度**：
  - 20/20 領域純文字 markdown（P1 上半）
  - 20/20 領域結構化 JSON（P1 下半，新增）
  - `scripts/parse_curriculum.py` + `scripts/verify_curriculum.py` 兩個 stdlib-only 腳本
  - `textbooks/`（P2）與 `knowledge-graph/`（P3）目前**只有空目錄骨架 + .gitkeep，零內容**
- **本次（Opus）更新**：
  - 三個腳本加 Windows cp950 編碼防護（`sys.stdout.reconfigure(utf-8)`）：原本 verify 在 Windows console 會因輸出 `✓` 拋 UnicodeEncodeError 崩潰（m3 在 Linux VM 跑碰不到，未來 Windows Claude 會中）；修後 `python3 scripts/verify_curriculum.py` 直接 20/20 pass exit 0，不需 `PYTHONIOENCODING`
  - README「目前狀態」原停在 Phase 0 scaffold，與 ROADMAP/CLAUDE 矛盾 → 已對齊到 P1 完成
  - 新增「§12 現況評估與建議」（好的 / 待改進），給下個 session 接力
- **前次（m3）更新重點**：
  - **P1 結構化完成**：
    - 寫 `scripts/parse_curriculum.py`：20 markdown → 20 `<stem>.structured.json`（per-md filename 避免多檔 domain 互相覆蓋）
    - 寫 `scripts/verify_curriculum.py`：含 regex self-test（14 fixtures + ROMAN_MAP smoke），20/20 pass exit 0
    - Schema：universal + 3 變體（Type A/B/none），frontmatter + 編碼清單 + raw_section_5 完整保留
    - Roman 數字正規化為 I/II/III/IV/V；數學 N-1-1 標 `code_format: numeric_phase`
    - 更新 20 個 `_index.md` 加結構化區塊
    - 更新 aggregate `curriculum/_index.json` 加 structured_summary（總 perf 1773 / cont 2573 / 20 files）
  - 結構類型分佈：Type A = 18、Type none（總綱）= 2；Type B 偵測待加強（自然科學/社會歸 A，但 raw_section_5 保留全部原文，下游可重 parse）
- **本地協作約定**：每次 session 開始時，先 `git pull` + 看 STATE 區塊 + 跑 `python3 scripts/download_curriculum.py` 確認新 URL

### ⚠️ 已知 URL 失效（不要再用）

| 失效 URL | 原因 | 替代 |
|----------|------|------|
| `https://cirn.moe.edu.tw/` | 連線 reset（CIRN 站死掉）| `https://www.edu.tw/` |
| `https://naer.edu.tw/` | DNS 不解析 | `https://www.naer.edu.tw/` |
| `https://moe.gov.tw/` / `https://moe.edu.tw/` | DNS 不解析 | `https://www.edu.tw/` |
| `https://k12ea.gov.tw/` / `https://cirk12.edu.tw/` | DNS 不解析 | `https://ghresource.k12ea.gov.tw/` |
| `https://12basic.edu.tw/` | timeout | （12basic 整體離線）|

### ✓ 已驗證可用（2026-06-23）

| URL | 用途 |
|-----|------|
| `https://www.naer.edu.tw/` | 國家教育研究院（部編本） |
| `https://www.edu.tw/` | 教育部全球資訊網 |
| `https://ghresource.k12ea.gov.tw/` | 國教署普通型高中學科資源平臺（教科書 PDF） |
| `https://ref.ncl.edu.tw/` | 國家圖書館（教科書備援） |

---

## 1. 目標

把台灣 K12（國小 1～國中 9～高中 10-12 年級）所有領域的課程內容，整理成**結構化、可機讀、可重組**的資料層，供下游「教材遊戲」使用。

下游遊戲的設計哲學：**不一定要等學校教到，前備會了就可以往前推**（適用於所有領域，不單獨偏好數學）。

---

## 2. 範圍

### ✅ 這個 repo 是什麼

- 108 課綱各領域指引的**純文字 + 結構化版本**
- 部編本教材的**純文字版本**
- 全領域 1-12 年級的**知識圖譜**（JSON + Mermaid）
- 抓取 / 轉換 / 驗證的**腳本**
- 對應的文件與規劃

### ❌ 這個 repo **不是**什麼

- 不是遊戲本體（遊戲在另一個 repo）
- 不含教師手冊、評量卷、習作解答、影音、題庫、互動教材（這些由遊戲端自己生成）
- 不抓民間出版社（康軒／南一／翰林）的付費教材（版權問題）

---

## 3. 技術棧

| 元件 | 用途 |
|------|------|
| 純 Markdown | 課綱 / 教材純文字 |
| JSON | 結構化資料 + 知識圖譜 |
| Mermaid | 知識圖譜視覺化 |
| Python（之後） | 抓取 / 轉換 / 驗證腳本 |
| Git + GitHub | 版本控制 + 開放釋出 |

---

## 4. 內容 / 資料來源

| 來源 | 路徑 | 授權 |
|------|------|------|
| 教育部 108 課綱 | https://www.edu.tw/ | CC BY |
| 國家教育研究院 部編本 | https://www.naer.edu.tw/ | CC BY（多數）|
| 教育部 教科書 PDF | https://ghresource.k12ea.gov.tw/ | 視檔案而定 |

canonical source 以**教育部**為主、**國教院**為輔。所有內容重新發布時保留原始出處。

---

## 5. 目錄結構

```
.
├── CLAUDE.md              # 本檔（交接單）
├── README.md              # 給人看的專案說明
├── LICENSE                # MIT（code）+ 第三方內容授權註記
├── ROADMAP.md             # TODO 清單（簡潔版）
├── .gitignore
│
├── curriculum/            # 108 課綱各領域指引
├── textbooks/             # 部編本教材（純文字）
├── knowledge-graph/       # 知識圖譜（全領域）
├── scripts/               # 抓取 / 轉換 / 驗證腳本
├── docs/                  # 設計文件
└── plans/                 # 規劃文件
```

---

## 6. 維護機制

- **本機工作目錄**：`~/projects/taiwan-k12-curriculum/`
- **GitHub repo**：`https://github.com/Hangsau/taiwan-k12-curriculum`
- **branch**：`main`（trunk-based，之後如需要可加 `dev`）
- **commit 規範**：`type(scope): 摘要`（type = feat/fix/docs/refactor/data/chore）
- **不要做的事**（詳見 §8）

更新流程：
1. 修改 / 新增內容
2. 跑驗證腳本（之後會寫 `scripts/verify.py`）
3. commit + push
4. 觸發 INDEX.md / HANDOVER 變更紀錄

---

## 7. ROADMAP 指向

完整 TODO 看 `ROADMAP.md`。摘要：

| Phase | 工作 | 狀態 |
|-------|------|------|
| P0 | scaffold（開專案 + 寫 TODO） | ✅ 2026-06-23 |
| P1 | 抓 108 課綱（全部領域）+ 結構化 | ✅ 2026-06-23（20/20）|
| P1.5 | 收尾 / 跨平台修復 | 🚧（見 ROADMAP）|
| P2 | 抓部編本教材 | ⏳（開工前先探勘覆蓋率）|
| P3 | 全領域知識圖譜 | ⏳（先寫 schema 文件）|
| P4 | 遊戲端整合介面 | ⏳ |
| P5 | 開放資料釋出 | ⏳ |

---

## 8. 不要做的事（Anti-patterns）

- ❌ **不要抓民間出版社（康軒／南一／翰林）的付費教材**。版權保護，會出事。
- ❌ **不要夾帶教師手冊 / 評量 / 習作解答**。使用者會自己做。
- ❌ **不要把影音、互動教材納入這個 repo**。下游遊戲端自行處理。
- ❌ **不要為了「完整性」硬塞資料**：找不到合法來源的就標 `TODO: 待補`，不要從盜版來源補。
- ❌ **不要把這個 repo 跟遊戲 repo 混在一起**。這個是純資料層。
- ❌ **不要 commit 大型二進位（PDF、影片、圖庫原始檔）**。純文字為主。
- ❌ **不要用 `--global` git config**。這個 repo 用 local config。

---

## 9. 已知問題

- 部編本教材的覆蓋率不明：108 課綱後多數領域已委由民間編寫（審定版），部編本可能只佔少數。P2 開始前要先探勘。
- 高中分組複雜（普通型 / 技術型 / 綜合型 / 單科型），資料結構要先想清楚再抓。
- 本土語文（閩南語 / 客家語 / 原住民族語）變體多，先聚焦主流。

---

## 10. Open Questions（之後 Phase 決定）

1. **內容授權策略**：部編本 vs 課綱原文的 license 標示細節（粗略標？還是 per-file metadata？）
2. **資料更新頻率**：108 → 新課綱過渡期怎麼處理（兩個課綱並存？）
3. **遊戲端整合**：這個 repo 只提供資料就好？還是要附 reference client？
4. **知識圖譜粒度**：要細到「兩位數乘法進位」這種具體技能？還是只到「分數」這種大主題？
5. **高中分組**：要全部 cover？還是只 cover 普通型？

---

## 11. 接手提醒

接手時：
1. 先讀這份 CLAUDE.md
2. 再讀 `ROADMAP.md` 看當前進度
3. 再讀 `docs/` 跟 `plans/` 看有沒有更深設計（注意：目前兩者都**只有 .gitkeep，還沒有設計文件**）
4. 不要憑印象改結構，先看現有檔案怎麼分類

---

## 12. 現況評估與建議（2026-06-23 Opus session）

> 給下一個接手的 Claude：這節記錄「目前做得好的」與「待改進的」，照著往前推。

### ✅ 做得好的（保持）

- **P1 紮實**：20/20 領域純文字 + 結構化 JSON 全到位，`verify_curriculum.py` 含 14 個 regex fixture self-test，工具壞掉會 exit 2 擋住，不會默默產垃圾。這是可信的資料基礎。
- **schema 保守正確**：`raw_section_5` 完整保留原文，就算 Type 偵測錯、下游仍可重 parse —— 沒有資訊損失。這個「lightweight + raw preserved」哲學要延續到 P2/P3。
- **腳本 idempotent + stdlib-only**：可重跑、無外部依賴，跨環境（Windows / Linux VM）都能跑，協作門檻低。
- **範圍紀律清楚**：§2 / §8 把「不抓盜版、不夾教師手冊、不混遊戲 repo」講死，避免 scope creep。

### ⚠️ 待改進的（優先序由高到低）

1. **Type B 偵測待修**（P3 前必處理）：`parse_curriculum.py` docstring 宣稱自然科學/社會是 Type B（依教育階段切小節），但實際分類把它們歸成 Type A。目前靠 `raw_section_5` 保底不丟資料，但要畫知識圖譜（P3）時「依教育階段分段」是關鍵維度，這時必須修對。修法：在 parser 加「偵測 `第N教育階段` / `國小／國中／高中` 子標題」的分支，不要只看編碼格式。
2. **P2 開工前先做覆蓋率探勘**（§9 已點出但還沒做）：108 課綱後多數領域改審定版，部編本可能只剩少數。**不要假設 12 年級 × 多領域都有部編本**就建一堆空目錄。先寫一個探勘腳本/筆記，確認「哪些階段哪些領域真的有合法部編本純文字源」，再決定 `textbooks/` 結構。目前 `textbooks/國中|國小|高中/<grade>/` 的空骨架是猜的，可能要重排。
3. **`docs/` 與 `plans/` 是空的**：schema 設計、知識圖譜 schema（P3 節點/邊定義）目前只活在 commit message 和這份 CLAUDE.md 裡。P3 開工前應在 `docs/` 寫一份 `knowledge-graph-schema.md`（節點粒度、邊類型、前備依賴怎麼表示），先對齊再產資料。Open Question #4（圖譜粒度）要先有答案。
4. **驗證沒涵蓋 round-trip**：verify 只查 structured.json 的欄位/格式，沒驗「structured.json 能不能還原回 markdown 的關鍵內容」。P2/P3 資料量變大後，建議加一個 round-trip 或 count-consistency 檢查（如：編碼總數 vs 原文出現次數）。
5. **協作同步靠人工紀律**：GitHub 是唯一共享層，但「動手前 git pull」目前靠人記得。若 m3 與 Opus 撞車風險升高，可考慮在 scripts 加一個 `make check`（pull + verify）一鍵入口，降低忘記 pull 的機會。

### 🚫 不要做的（除了 §8，再加這些）

- **不要為了「填滿」而建 P2/P3 的空內容**：`textbooks/` 和 `knowledge-graph/` 現在是空骨架，沒探勘清楚來源/schema 前不要硬塞。空目錄比錯結構好改。
- **不要刪 `raw_section_5`**：就算覺得結構化欄位夠用了，原文保底是這個 repo 的安全網。

---

*最後更新：2026-06-23（Opus session：cp950 編碼修復 + README 對齊 + §12 現況評估；前次 m3：P1 完成 20/20）*
