# CLAUDE.md — taiwan-k12-curriculum

> **這是交接單，不是 README。** 給未來接手這個專案的 Claude session 看。
> 建立：2026-06-23
> 維護者：Hangsau

---

## 0. 接手前先讀這段（STATE）

接手 session 開始時，**先看這個區塊**判斷最新狀態：

- **最後更新**：2026-06-23
- **當前 Phase**：P1 抓 108 課綱 **已完成 20/20 個領域**
- **內容進度**：所有領域資料夾從 `.gitkeep` → 純文字課程綱要 + index MOC
- **本次更新重點**：
  - **P1 完成**：從 NAER 下載 20 個 108 課綱 PDF → 純文字 markdown（含總綱、本土語文 6 種、英語文、數學、自然科學、社會、藝術、綜合活動、科技、健康與體育、生活課程、國防、全民國防）
  - 寫 `scripts/download_curriculum.py`：可重跑、已驗證 20/20 success
  - 為每個領域生 `_index.md` MOC
  - 修 README.md / CLAUDE.md 中 5 個失效 URL
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
| P1 | 抓 108 課綱（全部領域） | ⏳ |
| P2 | 抓部編本教材 | ⏳ |
| P3 | 全領域知識圖譜 | ⏳ |
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
3. 再讀 `docs/` 跟 `plans/` 看有沒有更深設計
4. 不要憑印象改結構，先看現有檔案怎麼分類

---

*最後更新：2026-06-23（scaffold + URL 修復 + P1 完成 20/20）*
