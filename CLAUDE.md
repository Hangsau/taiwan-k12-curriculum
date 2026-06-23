# CLAUDE.md — taiwan-k12-curriculum

> **這是交接單，不是 README。** 給未來接手這個專案的 Claude session 看。
> 建立：2026-06-23
> 維護者：Hangsau

---

## 0. 接手前先讀這段（STATE）

接手 session 開始時，**先看這個區塊**判斷最新狀態：

- **最後更新**：2026-06-23 晚（§13 4 個待改進全做完）
- **當前 Phase**：P1 結構化 + 驗證 ✅ + **P1.5 遊戲化動機研究 ✅** + **§13 #1-#4 全做完** + **P2 探勘 + P3 schema 已設計**
- **內容進度**：
  - 20/20 領域純文字 markdown（P1 上半）
  - 20/20 領域結構化 JSON（P1 下半 + §13 #1 自然科學從 A 改 B、社會加表格型 warning）
  - `scripts/parse_curriculum.py` + `scripts/verify_curriculum.py` + `scripts/probe_textbooks.py` 三個 stdlib-only 腳本
  - `docs/motivation-research-collection-mechanics.md` — 蒐集機制 vs. 內在動機研究（~18K 字，deep-research 8 confirmed / 15 refuted / 4 evidence gap）— **P4 遊戲端設計必讀**
  - `docs/knowledge-graph-schema.md` — P3 知識圖譜 schema 設計（節點 = curriculum 編碼、邊 = prerequisite、粒度 = 學習內容層、階段 I-V）
  - `plans/P2-coverage-survey.md` — P2 部編本覆蓋率探勘報告（含 11 領域 × 3 階段矩陣初步判斷 + 4 個入口 URL probe 結果）
- **本次更新重點**：
  - **§13 #1 Type B 偵測修好（2026-06-23 晚）**：
    - 自然科學從 A 改 B（依「國民小學/國民中學/普通型高中」heading 切段，3 段結構）
    - ROMAN_MAP 擴充加 `Ⅴc`/`Ⅴa`（普通型高中必修/加深加廣選修），補進 39 perf + 426 cont = 465 個高中編碼
    - 社會保持 A（表格型，stage label 在 cell 內不在 heading 行），加 DOMAIN_HINTS warning
  - **§13 #2 P2 探勘完成（2026-06-23 晚）**：
    - `scripts/probe_textbooks.py`（URL probe + 關鍵字偵測 + SSL fallback）
    - `plans/P2-coverage-survey.md`（11 領域 × 3 階段矩陣 + 4 入口 URL probe + 待 user 補 SOURCES）
    - 探勘結論：國語文 / 數學 / 自然科學 (高中) 仍有部編本；其他多數改審定版（民間版不抓）
  - **§13 #3 P3 schema 設計完成（2026-06-23 晚）**：
    - `docs/knowledge-graph-schema.md`（節點 = curriculum 編碼、邊 = prerequisite、粒度 = 學習內容層）
    - 解答 Open Question #4（圖譜粒度）：定在 curriculum 學習內容編碼層，不更細不更粗
  - **§13 #4 round-trip 驗證加好（2026-06-23 晚）**：
    - verify check #11：每個 structured code 反查 raw_section_5 找得到才算 pass
    - 20/20 全 pass（0 failure / 0 warning）
  - **§14 雙 Claude 協作分工矩陣（2026-06-23 晚）**：
    - Claude A（Windows）管 P4 設計、B（Linux VM）管 P2/P3/curriculum/verify
    - 同步機制 + 衝突處理 + shared files 約定
- **本地協作約定**：每次 session 開始時，先 `git pull` + 看 STATE 區塊 + 看 §13 評估是否過時（已做 ✅ 的從清單移走）
- **§13 4 個待改進全完成**：
  - #1 Type B 偵測 ✅
  - #2 P2 探勘 ✅
  - #3 knowledge-graph-schema ✅
  - #4 round-trip ✅
  - #5 協作同步靠人工紀律 ✅（改用 §14 雙 Claude 矩陣）
- **結構類型分佈**：Type A = 17、Type B = 1（自然科學）、Type none（總綱）= 2
- **總編碼**：perf 1812 / cont 2999（從 §13 修前的 1773 / 2573 補進自然科學高中段 39 + 426）

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
| P1 | 抓 108 課綱（全部領域）+ 結構化 + 驗證 + Type B 修 + round-trip | ✅ 2026-06-23 |
| P1.5 | 遊戲化動機研究（前置研究給 P4） | ✅ 2026-06-23 |
| P2 | 抓部編本教材 — **教材全 K12 完成（21 均一 + 12 AI 衍生 + 6 章節 POC，11/11 領域覆蓋）**，對齊 + 結構化完成 | ✅ |
| P3 | 全領域知識圖譜 — schema 設計完成，generator 待寫 | 🚧 |
| P4 | 遊戲端整合介面 | ⏳（設計前必讀 `docs/motivation-research-collection-mechanics.md` + `docs/sdt-design-audit-framework.md` + `docs/p4-design-concept-pet-home.md`）|
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
- ❌ **P4 遊戲端設計時，不要忽略 `docs/motivation-research-collection-mechanics.md`**。這份是 evidence-based 出發點，不讀就設計 → 容易踩 overjustification / 控制性框架陷阱。
- ❌ **P4 設計時，不要把 SDT 「自主 / 勝任 / 關聯」三需求寫進 spec 就算交差**。每個具體遊戲機制都要對到三需求的具體滿足或受阻狀態。

---

## 9. 已知問題

- **部編本覆蓋率矩陣待 user 親查 NAER 確認**（§13 #2 完成探勘腳本 + 矩陣初版，但 SOURCES 清單只有 4 個入口 URL，需 user 補各領域各階段的 NAER PageSyllabus URL → probe 重跑 → 矩陣定稿）
- 高中分組複雜（普通型 / 技術型 / 綜合型 / 單科型），資料結構要先想清楚再抓。
- 本土語文（閩南語 / 客家語 / 原住民族語）變體多，先聚焦主流。
- **社會領域是表格型 Type B**：stage label 在 cell 內（非獨立 heading 行），parser 不切段；stages_present 欄位已標明實際分布（II/III/IV/V）。若課綱修訂改用 heading 切段，從 `DOMAIN_HINTS` 移除即可。

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
3. 再讀 `docs/` 跟 `plans/` 看有沒有更深設計
4. 不要憑印象改結構，先看現有檔案怎麼分類

---

## 12. P4 遊戲端設計必讀文件

- **`docs/motivation-research-collection-mechanics.md`** — 蒐集機制 vs. 內在動機研究
  - **為什麼必讀**：P4 設計者會遇到「要不要用蒐集機制」這個問題。這份研究用對抗式驗證（3-vote）把通過 / refuted / evidence gap 清楚區分，避免用「聽起來對」的理論設計出毀掉內在動機的遊戲
  - **核心結論（一行）**：蒐集機制不必然毀掉內在動機，關鍵在「**框定方式**」（controlling vs. informational）+ 是否滿足 SDT 三大需求
  - **設計三步驟**：(1) 讀 §8 設計原則矩陣（年齡 × 蒐集類型）(2) 讀 §9 領域 × 蒐集類型矩陣（對應 108 課綱）(3) §1.2 / 1.3 確認哪些 claim 可以當事實用、哪些只是推論
  - **更新時間**：2026-06-23（建立）
- **`docs/sdt-design-audit-framework.md`** — SDT 機制級設計稽核框架。把上面的研究操作化成「輸入一個機制 → 跑三道閘門 → 輸出 ✅/⚠️/❌」的決策工具。設計每個機制時各跑一次。
- **`docs/p4-design-concept-pet-home.md`** — 寵物養成 + 居家擺飾玩法的設計概念藍本（framework 的完整應用範例：含「該拆掉哪兩個毒核」）。

---

## 12.5 §15 教材章節（2026-06-24 補上 — P2 完整流程）

**§15 是 P2「教材生成」的完整工作流**，5 個子任務 + 對應 script + 對應產出。

### 12.5.1 §15 結構

| 子任務 | Script | 產出 |
|--------|--------|------|
| §15-A 探索來源 | （手動探勘 + docs/textbook-sources-survey.md）| 6 個來源評估表 |
| §15-B 下載 | `scripts/download_junyi.py` + `download_junyi_chapters.py` | 21 年級總覽 .md + 6 章節 .md（POC）|
| §15-C 對齊 | `scripts/align_and_structure.py`（前半）| 33 .md 加 aligned_codes |
| §15-D AI 衍生 | `scripts/generate_textbooks.py` | 12 個 AI 教材 .md（5 缺漏領域）|
| §15-E 結構化 | `scripts/align_and_structure.py`（後半）| 33 .structured.json |

### 12.5.2 教材產出（2026-06-24 統計）

| 來源 | 數量 | 領域覆蓋 | 授權 |
|------|------|---------|------|
| 均一教育平台（junyi/）| 21 個年級總覽 + 6 個章節（POC）| 國語文/英語文/數學/社會/自然科學 5 領域 | CC BY-NC-SA 3.0 TW |
| AI 衍生（generated/）| 12 個 stage 教材 | 藝術/健康/綜合/科技/國防 5 領域 + 國語文補 | 衍生自 CC BY 4.0 課綱 |
| **總計** | **39 .md + 33 .structured.json** | **11/11 領域** | |

### 12.5.3 結構與對齊

每個 .md 都有：frontmatter（title / domain / stage / source / license / aligned_codes）+ 內容（領域簡介 + 章節列表 + 學習內容 + 學習表現 + 教學活動建議 + 評量建議）

每個 .structured.json 含：chapters（從 .md 抓的章節列表）+ aligned_codes（對齊的 curriculum codes）+ aligned_performance_count + aligned_content_count

**總對齊 codes：3237 個 curriculum codes**

### 12.5.4 已知限制 / TODO

- 章節內文（v3）只做 POC（數學一年級 6 章節）：完整 21 年級 × 5 版本 × 6 章節 = 630 章節，預估 50 分鐘，下次 session 可 `download_junyi_chapters.py --all` 一鍵跑
- 本土語文 0 個：均一沒課程，curriculum 本土語文 6 個子檔結構複雜，未自動處理
- 影片內容：均一教材影片是 YouTube 嵌入，純文字抓不到，要 ASR 或字幕檔
- 子節深層內容：v3 抓到「章節 → 子節標題」，子節內文要再深入一層（4 層 fetch）— TODO
- 章節對齊精度：現在對齊是「整個 stage 的所有 codes 設為 aligned」，未來可改為「每章對齊部分 codes」

### 12.5.5 下游使用

- 遊戲設計端：讀 `textbooks/junyi/<domain>/<year>.md` 拿章節結構 → 設計關卡
- P3 knowledge-graph：用每個 .md 的 `aligned_codes` 對應 `curriculum/<domain>/.structured.json` 畫前備依賴
- P4 遊戲端契約：用每個 .structured.json 的 chapters + aligned_codes 設計遊戲資料層

---

## 13. 現況評估與建議（2026-06-23 Opus session）

> 給下一個接手的 Claude：這節記錄「目前做得好的」與「待改進的」，照著往前推。

### ✅ 做得好的（保持）

- **P1 紮實**：20/20 領域純文字 + 結構化 JSON 全到位，`verify_curriculum.py` 含 14 個 regex fixture self-test，工具壞掉會 exit 2 擋住，不會默默產垃圾。這是可信的資料基礎。
- **schema 保守正確**：`raw_section_5` 完整保留原文，就算 Type 偵測錯、下游仍可重 parse —— 沒有資訊損失。這個「lightweight + raw preserved」哲學要延續到 P2/P3。
- **腳本 idempotent + stdlib-only**：可重跑、無外部依賴，跨環境（Windows / Linux VM）都能跑，協作門檻低。
- **範圍紀律清楚**：§2 / §8 把「不抓盜版、不夾教師手冊、不混遊戲 repo」講死，避免 scope creep。

### ✅ §13 4 個待改進全完成（2026-06-23 晚）

1. ✅ **Type B 偵測修好**（§13 #1）：自然科學從 A 改 B（heading 切段 3 段）；社會保持 A 加 warning（表格型）
2. ✅ **P2 探勘完成**（§13 #2）：`scripts/probe_textbooks.py` + `plans/P2-coverage-survey.md` + 矩陣初步判斷；待 user 補 SOURCES 重跑
3. ✅ **knowledge-graph-schema.md 完成**（§13 #3）：節點 = curriculum 編碼、邊 = prerequisite、粒度 = 學習內容層、Open Question #4 解答
4. ✅ **round-trip 驗證加好**（§13 #4）：verify check #11，每個 structured code 反查 raw 找得到；20/20 全 pass
5. ✅ **協作同步**（§13 #5）：改用 §14 雙 Claude 矩陣（commit 必標 by A/B + 開頭 pull + 結尾 push）

詳細 commit 見 §0 STATE。

### 🚫 不要做的（除了 §8，再加這些）

- **不要為了「填滿」而建 P2/P3 的空內容**：`textbooks/` 和 `knowledge-graph/` 現在是空骨架，沒探勘清楚來源/schema 前不要硬塞。空目錄比錯結構好改。
- **不要刪 `raw_section_5`**：就算覺得結構化欄位夠用了，原文保底是這個 repo 的安全網。

---

## 14. 雙 Claude 協作分工（2026-06-23 確立）

兩個 Claude 同時維護這個 repo，按以下分工避免互相覆蓋：

| Client | 環境 | Model | 識別 |
|--------|------|-------|------|
| **Claude A** | user 的 Windows 端 | Opus 4.7 | Co-Authored-By 標 `Claude Opus 4.7` |
| **Claude B** | Linux VM（hangsau user）| Opus 4.7 | Co-Authored-By 標 `Claude Opus 4.7` |

兩個都用同一份 repo、同樣的 GitHub remote、同樣的 `main` branch。**這節是 single source of truth，分工有變動就改這節。**

### 14.1 分工矩陣

| 範圍 | Owner | 對應 Phase / 工作 | 不做 |
|------|-------|-------------------|------|
| `docs/P4-*` / `docs/sdt-*` / `docs/motivation-*` / `docs/p4-design-concept-*` | **Claude A（Windows）** | P4 遊戲端設計 + 動機研究後續（含 evidence gap 補研究） | 不改 `scripts/` / `curriculum/` / `knowledge-graph/` / `textbooks/` |
| `textbooks/`（探勘 + 抓取 + 對齊課綱 + 結構化） | **Claude B（Linux VM）** | P2 部編本教材 | 不寫 P4 設計文件 |
| `knowledge-graph/` 設計 + `docs/knowledge-graph-schema.md` + `scripts/parse_curriculum.py` Type B 偵測修 | **Claude B（Linux VM）** | P3 全領域知識圖譜 + §13 #1 | 不寫 P4 設計 |
| `curriculum/` 純文字 + `scripts/parse_curriculum.py` 結構化 schema 演進 | **Claude B（Linux VM）** | P1 維護 + 補強 | A 不改 curriculum/（除非 B 授權） |
| `scripts/verify_curriculum.py` 加 round-trip / count-consistency | **Claude B（Linux VM）** | §13 #4 | — |
| `docs/` 與 `plans/` 內知識圖譜 schema 文件 | **Claude B（Linux VM）** | §13 #3 | A 不寫 P3 schema（避免衝突） |
| `CLAUDE.md` / `ROADMAP.md` / `README.md` / `LICENSE` | **雙方皆可**，commit 必標 `[by A]` 或 `[by B]` | 跨 phase 共編 | — |

### 14.2 同步機制

**每次 session 開始（雙方都做）**：
1. `cd ~/projects/taiwan-k12-curriculum && git pull --ff-only`
2. 讀本檔 §0 STATE + §13 待改進清單
3. 讀 `ROADMAP.md` 對應 phase 的 ✅/⏳ 狀態
4. 寫一筆 `~/.claude/decisions.log`：「本 session（環境 A/B、日期）計畫做 X」

**每次 session 結束前（雙方都做）**：
1. `git add` + `commit`（message 格式：`type(scope): 摘要 [by A]` 或 `[by B]`）
2. `git push`（user 政策覆寫 §6.1「不主動 commit」）
3. 寫 `decisions.log`：「完成 Y，下個 session 接 Z」
4. Claude B 還要更新 `~/.claude/SYSTEM_HANDOVER.md` §0 變更紀錄

### 14.3 衝突處理

- **同一檔案同時改** → 後 push 的解 merge conflict。先 commit 自己的，再用 `git pull --rebase` 或 `git pull` + 手解。
- **跨分工邊界想動對方的檔** → 先在 `decisions.log` 寫「我想動 X，原因 Y」，等對方下次 session 看到才動。
- **分工矩陣變更** → 改本節（§14.1），雙方都 commit。
- **緊急情況**（對方 1 週沒 push、卡住） → 在 `decisions.log` 寫「A 1 週沒回應，B 暫時接管 X」，A 回來看到再協商。

### 14.4 shared files 約定

- `CLAUDE.md`：任一可改。§0 STATE / §13 評估 / §14 矩陣是 high-traffic，commit 必清楚標。
- `ROADMAP.md`：✅/⏳ 狀態更新誰都能改；新增 phase 段要對方下個 session pull 後生效。
- `~/.claude/decisions.log` + `SYSTEM_HANDOVER.md`：由 **Claude B（Linux VM）** 單方寫入（這兩檔在本機 `~/.claude/`，Windows 端沒對應位置）。Claude A 從 GitHub 看本 repo 的 commit message + ROADMAP 變化掌握進度，不直接寫這兩檔。
- 任何檔案 size > 1MB 或外部 binary → 不要 commit（§8 既有的 anti-pattern）。

### 14.5 範例：兩邊如何開始一個 phase

**Claude A 開 P4 第一份 design spec**：
1. pull → 看 §0 / §13 / §14.1 確認分工沒變
2. 讀 `docs/sdt-design-audit-framework.md` §1-3 複習稽核流程
3. 寫 `docs/P4-mechanisms-design-v1.md`，每個機制附「跑過 framework 的結果」
4. commit `[by A]` + push

**Claude B 開 §13 #2 P2 覆蓋率探勘**：
1. pull → 看 §0 / §13 / §14.1
2. 探勘教育部 / 國教院哪些階段哪些領域還有部編本純文字源
3. 寫 `plans/P2-coverage-survey.md`（不直接動 `textbooks/` 結構，先報告）
4. 寫 `scripts/probe_textbooks.py` 探勘腳本
5. commit `[by B]` + push + 寫 decisions.log

---

*最後更新：2026-06-23 晚（scaffold + URL 修復 + P1 完成 20/20 + P1 結構化 + P1.5 遊戲化動機研究 + §13 Opus 現況評估復原 + §14 雙 Claude 協作分工確立）*
