# CLAUDE.md — taiwan-k12-curriculum

> 交接單。session 接手前讀本檔。
> 舊 §13–§19 的 m3 工作日誌已撤（共 460 行）；要追溯走 `git log -p CLAUDE.md`。

---

## 0. 現況（2026-06-26）

✅ **已完成**：
- P0 scaffold
- P1 課綱結構化：20/20 領域 markdown + structured.json（1812 perf / 2999 cont 編碼，含 raw_section_5 原文保底）
- P3 知識圖譜骨架：4811 nodes / 1922 edges / 12 domain graph — **auto-detected stage 升序邊，語意未人工驗證**
- 考卷蒐集：CEEC 公開試題 82 個 .txt（學測/分科 108–115 學年，公開合理使用）
- 米蘭老師 / ddes 段考 working tree 整理：4577 個 .md（國中國小段考為主，國文 2762 / 數學 895 / 英文 479 / 自然 225 / 社會 156 / 健體 39）— **.gitignore 排除不上 GitHub**

⏳ **未完成**：
- P2 部編本教材 — 探勘做過，**實際內容 0**
- P4 遊戲端設計（P1.5 動機研究已備齊）
- 知識圖譜邊的語意驗證

🚫 **不要重複的舊路**（2026-06-26 撤）：
- 米蘭老師 / 大墩段考原始檔 commit 到 GitHub（授權不清，已 git filter-repo 從 history 移除）
- LLM 自動生教材（13 個 stage 級檔內容錯誤，已刪）
- 均一教育平台爬取（HTML chrome 無教學內容，已刪）
- v0.5.0 release（CITATION.cff、release-notes.md、README v0.5 tone）— m3 自決發行未獲授權，已撤
- 「雙 Claude A/B 分工」（m3 自設虛構，已撤）

---

## 1. 目標

把台灣 K12（國小 1 ~ 高中 12 年級）所有領域的 108 課綱內容，整理成結構化、可機讀、可重組的資料層，供下游教材遊戲使用。

下游遊戲設計哲學：**前備會了就可以往前推**（適用於所有領域，不單獨偏好數學）。

---

## 2. 範圍

### ✅ 這個 repo 是什麼

- 108 課綱各領域指引純文字 + 結構化 JSON
- 部編本教材純文字（P2 待做）
- 全領域 1-12 年級的知識圖譜（JSON + Mermaid）
- 大考中心公開試題（學測 / 分科，純文字）
- 抓取 / 轉換 / 驗證腳本

### ❌ 不是什麼

- 不是遊戲本體（遊戲在另一個 repo）
- 不含教師手冊、評量卷、習作解答、影音、互動教材（遊戲端自己生成）
- 不抓民間出版社（康軒/南一/翰林）的付費教材（版權）
- 不公開未明示授權的資料（米蘭老師、大墩段考 working tree 自用，不 commit）

---

## 3. 技術棧

| 元件 | 用途 |
|------|------|
| Markdown / JSON / Mermaid | 資料層 |
| Python stdlib-only | 抓取 / 轉換 / 驗證 |
| Git + GitHub | 版控 |

---

## 4. 資料來源 + 授權

| 來源 | 內容 | 授權 | GitHub 公開 |
|------|------|------|-------------|
| 教育部 108 課綱 | 課綱原文 | CC BY 4.0 | ✅ |
| 國家教育研究院（NAER）| 部編本教材 | CC BY（多數）| 視個別檔（P2 待做）|
| 大考中心 CEEC | 學測 / 指考 / 分科 | 政府公開（合理使用）| ✅ |
| 米蘭老師 Drive | 段考 | 未明示授權 | ❌ working tree 自用 |
| 大墩國小 | 段考 | 校自製授權不明 | ❌ working tree 自用 |

canonical source：教育部為主、國教院為輔。

---

## 5. 目錄結構

```
.
├── CLAUDE.md              # 本檔
├── README.md
├── LICENSE                # MIT(code) + 第三方內容授權註記
├── ROADMAP.md
├── .gitignore             # 嚴排：exams/melances/, exams/ddes/, textbooks/generated/, textbooks/archived/, *.pdf
│
├── curriculum/            # P1 課綱 — 20 領域 .md + structured.json + _index.json
├── knowledge-graph/       # P3 — 12 domain graph + _all-graph.json + mermaid
├── exams/
│   ├── *.pdf              # CEEC 學測 / 分科 PDF
│   ├── text/              # CEEC PDF → 82 個 .txt
│   ├── INDEX.md / .json   # 考卷分類索引
│   ├── md/by-grade-subject/  # 衍生 .md 4577 個（.gitignore 排除）
│   ├── melances/          # working tree 米蘭老師原始（.gitignore 排除）
│   └── ddes/              # working tree 大墩原始（.gitignore 排除）
├── docs/                  # 設計文件 + schema + 探勘筆記
├── plans/                 # 探勘 / 規劃文件
├── reports/               # 高頻知識點分析輸出
└── scripts/               # 抓取 / 轉換 / 驗證腳本（stdlib-only）
```

---

## 6. 維護流程

- 開工前：`git pull --ff-only`
- commit 訊息：`type(scope): 摘要`（type = feat / fix / docs / refactor / chore）
- 動完 push（user 政策允許自主 commit + push）
- 結構性改動同步：本檔 + README + ROADMAP

---

## 7. ROADMAP

詳細見 `ROADMAP.md`。摘要：

| Phase | 工作 | 狀態 |
|-------|------|------|
| P0 | scaffold | ✅ 2026-06-23 |
| P1 | 課綱結構化 | ✅ 2026-06-23 |
| P1.5 | 動機研究（P4 用）| ✅ 2026-06-23 |
| P2 | 部編本教材 | ⏳ 待做 |
| P3 | 知識圖譜 | ✅ 2026-06-24（語意邊未驗證）|
| P4 | 遊戲端整合 | ⏳ |

---

## 8. Anti-patterns

- ❌ 不要為了「填滿」LLM 自動生教材或內容（13 個 generated 檔已證實會錯到誤導，例：「3 顆蘋果寫 2 顆」）
- ❌ 不要把授權不清的資料 commit 到 GitHub（米蘭老師、ddes、民間出版社）
- ❌ 不要刪 `raw_section_5`（原文保底是這個 repo 的安全網）
- ❌ 不要夾帶教師手冊、評量、習作解答
- ❌ 不要對外 release（CITATION.cff、release-notes、v0.x.0 tag）— 還在開發中
- ❌ 不要用 `--global` git config
- ❌ 不要 commit 大型二進位（PDF、影片、圖庫）— 統一靠 `*.pdf` .gitignore 規則
- ❌ P4 設計時不要忽略 `docs/motivation-research-collection-mechanics.md` + `docs/sdt-design-audit-framework.md`
- ❌ 不要把 SDT「自主 / 勝任 / 關聯」三需求寫進 P4 spec 就算交差 — 每個機制要對到三需求的具體滿足或受阻狀態
- ❌ 不要自設「雙 Claude 分工」之類的對等協作虛構

---

## 9. 已知問題

- **知識圖譜邊是 stage 升序預設邊，語意正確性未驗證**。要靠 `plans/<domain>/edges.md` 補人工標註（generate_graph.py 會自動合併）
- 部編本教材覆蓋率不明：108 課綱後多數已民間編寫，部編本可能只佔少數。P2 開始前要先探勘確認
- 高中分組複雜（普通型 / 技術型 / 綜合型 / 單科型），P2/P3 結構要先想清楚
- 本土語文變體多，先聚焦主流
- 米蘭老師 5288 個 working tree 原始檔，1281 個 body OCR 失敗已刪。剩 4007 個 + ddes 367 個 working tree 自用

---

## 10. Open Questions

1. 內容授權策略：部編本 vs 課綱原文 license 標示細節（粗略標 vs per-file metadata）
2. 課綱更新：新課綱過渡期怎麼處理（兩個課綱並存？）
3. 遊戲端整合：repo 只提供資料 vs 附 reference client
4. 知識圖譜粒度：細到具體技能（兩位數乘法進位）vs 大主題（分數）
5. 高中分組：全部 cover vs 只 cover 普通型

---

## 11. 接手提醒

1. 先讀本檔（§0 STATE 看現況）
2. 讀 ROADMAP.md
3. 進入特定 phase 時讀對應 `docs/` 與 `plans/`
4. **P4 設計者必讀**：`docs/motivation-research-collection-mechanics.md` + `docs/sdt-design-audit-framework.md` + `docs/p4-design-concept-pet-home.md`
5. 不要憑印象改結構，先看現有檔案分類

---

## 12. ddes 檔名編碼解讀

大墩國小段考檔名格式：`<年級 1><科目 1><學年 3><學期 1><考試碼 1>[variant 1].<ext>`

| 學期碼 | 意義 | 考試碼 | 意義 |
|--------|------|--------|------|
| 1 | 上學期 | 1 | 期中考 |
| 2 | 下學期 | 2 | 期末考 |

例：
- `3E10812.doc` = 3 年級英文 108 學年下學期期末考
- `5N10922.doc` = 5 年級自然 109 學年下學期期末考
- `6C11411A.doc` = 6 年級國文 114 學年上學期期中考 A 卷

---

## 13. 米蘭老師 mojibake 修復記錄（2026-06-26）

m3 之前結論「BIG5 mojibake 物理極限無法救」**是錯的**——他試了 GBK / latin-1→BIG5 / cp1252→BIG5，但沒試 latin-1→UTF-8。

實際情況：原檔名是 UTF-8 編碼，被 filesystem 當 latin-1 顯示。`s.encode("latin-1").decode("utf-8")` 即可完整還原。

修復後 5281 / 5288 米蘭老師 .md frontmatter `original_filename` 還原，5288 個原始 PDF/DOC/DOCX 物理檔 rename 成繁中。

腳本：`scripts/fix_filename_mojibake.py`、`scripts/rename_melances_originals.py`。
