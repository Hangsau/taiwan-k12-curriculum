# taiwan-k12-curriculum

> 台灣 108 課綱 K12 課程結構化資料集 — 課綱 + 部編本教材 + 全領域知識圖譜

---

## 為什麼做這個

做一個教材遊戲，讓小朋友**邊玩邊學、不用等學校教到才學會**。

前備會了就可以往前推（這對所有領域都適用，不只數學）。

這個 repo 是**遊戲要吃的內容資料層**，不是遊戲本體。

---

## 目前狀態

✅ **Phase 0–3 + 2-B 全部完成**（2026-06-25）

| Phase | 工作 | 狀態 |
|-------|------|------|
| P0 | scaffold（開專案 + 寫 TODO）| ✅ 2026-06-23 |
| P1 | 抓 108 課綱（20/20 領域）+ 結構化 + 驗證 | ✅ 2026-06-23 |
| P1.5 | 遊戲化動機研究（給 P4 設計用）| ✅ 2026-06-23 |
| P2 | 抓部編本教材（11/11 領域覆蓋）+ 對齊 + 結構化 | ✅ 2026-06-24 |
| P2-B | 抓考卷/試題（5655 個，metadata 索引）| ✅ 2026-06-24 |
| P3 | 全領域知識圖譜（12 domain graph）| ✅ 2026-06-24 |
| **P4** | 遊戲端整合介面 | ⏳（歸 Claude A 管）|
| **P5** | 開放資料釋出 | 🚧（本 PR）|

詳細 TODO 看 [`ROADMAP.md`](./ROADMAP.md)。歷次釋出看 [`docs/release-notes.md`](./docs/release-notes.md)。

---

## 量化指標（v0.5.0）

| 項目 | 數量 |
|------|-----:|
| 領域數（課綱）| 11 |
| 學習階段 | 3（國小 / 國中 / 高中）|
| 結構化檔（curriculum structured.json）| 20 |
| 學習表現編碼（perf）| 1812 |
| 學習內容編碼（cont）| 2999 |
| 知識圖譜節點（總計）| **4811** |
| 知識圖譜邊（總計）| **1922** |
| 知識圖譜 domain graph | 12（含總綱）|
| 部編本教材 .md | 33 |
| 對齊到 curriculum 的編碼 | 3237 |
| 考卷 metadata 索引 | 5655 |
| 考卷 .md（衍生，working tree，**不上 github**）| 5277 |

跑驗證：

```bash
python3 scripts/verify_curriculum.py   # 20/20 PASS
python3 scripts/verify_graph.py        # 12/12 PASS, 4811/1922
```

---

## 怎麼用

### 給下游遊戲端開發者

讀 [`knowledge-graph/_all-graph.json`](./knowledge-graph/_all-graph.json)：

```json
{
  "nodes": [
    {"id": "數學/N-1-1", "domain": "數學", "category": "content", "stage": "I", "ordinal": 1, ...}
  ],
  "edges": [
    {"from": "數學/N-1-1", "to": "數學/N-2-1", "type": "prerequisite"}
  ]
}
```

從當前節點往前追 `prerequisite` 邊，回答「要學什麼才能進入這關」。

每個領域獨立 graph 在 `knowledge-graph/<領域>/graph.json`，可單獨發布。

### 給老師 / 教材編者

讀 [`curriculum/`](./curriculum/) 對應領域的 `<領域>_index.md`（目錄索引）+ `*.structured.json`（結構化）+ `*.md`（原文）。

### 給研究者

- 課綱 schema：見 `scripts/parse_curriculum.py`（Type A / B 兩種結構變體）
- 知識圖譜 schema：見 [`docs/knowledge-graph-schema.md`](./docs/knowledge-graph-schema.md)
- 動機研究（P4 設計用）：見 [`docs/motivation-research-collection-mechanics.md`](./docs/motivation-research-collection-mechanics.md)

---

## 內容範圍

### 領域

國語文、本土語文、英語文、數學、社會、自然科學、藝術、健康與體育、綜合活動、科技、國防（高中）

### 年級

| 階段 | 年級 |
|------|------|
| 國小 | 1–6 年級 |
| 國中 | 7–9 年級 |
| 高中 | 10–12 年級 |

---

## 不包含

- ❌ 教師手冊、評量卷、習作解答（自己會做 / 遊戲端自己生成）
- ❌ 影音、互動教材（遊戲端自己生成）
- ❌ 民間出版社（康軒／南一／翰林）的付費教材（版權）

---

## 資料來源 + 授權

| 來源 | 內容 | 授權 |
|------|------|------|
| 教育部 108 課綱 | 課綱原文 | CC BY 4.0 |
| 國家教育研究院（NAER）| 部編本教材 | CC BY（多數）|
| 國教署普通型高中學科資源平臺 | 高中教科書 PDF | 視檔案而定 |
| 均一教育平台 | 教材 .md | CC BY-NC-SA 3.0 TW |
| 大考中心 | 學測 / 指考 / 分科 | 政府公開 |
| 米蘭老師 Drive | 考卷（working tree，**不上 github**）| 授權待釐清 |

**程式碼授權**：MIT（見 [`LICENSE`](./LICENSE)）。
**第三方內容**：原始發布單位之授權，再散布時保留原始出處與授權標示。

canonical source 以**教育部**為主、**國教院**為輔。

---

## 引用本資料集

詳見 [`CITATION.cff`](./CITATION.cff)。GitHub 會在 repo 頁面自動顯示「Cite this repository」按鈕。

```bibtex
@dataset{hangsau_2026_taiwan_k12,
  author = {Hangsau},
  title = {Taiwan K-12 Curriculum Structured Dataset (108 Curriculum)},
  year = {2026},
  version = {0.5.0},
  publisher = {GitHub},
  url = {https://github.com/Hangsau/taiwan-k12-curriculum}
}
```

---

## 給 AI session 接手

接手前先讀 [`CLAUDE.md`](./CLAUDE.md) — 那是交接單（含目標、範圍、Anti-patterns、雙 Claude 協作分工）。

---

## 結構

```
.
├── CLAUDE.md              # 給 AI 的交接單
├── README.md              # 本檔（給人看）
├── LICENSE                # MIT + 第三方內容授權註記
├── CITATION.cff           # 學術引用 metadata
├── ROADMAP.md             # TODO 進度
├── docs/
│   ├── release-notes.md   # 歷次釋出紀錄
│   ├── knowledge-graph-schema.md
│   ├── motivation-research-collection-mechanics.md
│   ├── sdt-design-audit-framework.md
│   ├── p4-design-concept-pet-home.md
│   └── textbook-sources-survey.md
├── curriculum/            # 108 課綱各領域指引（純文字 + structured.json）
├── textbooks/             # 部編本教材（純文字）
├── knowledge-graph/       # 全領域知識圖譜（graph.json + graph.mermaid）
├── exams/                 # 考卷原始檔（metadata 上 github，.md 不上）
├── scripts/               # 抓取 / 轉換 / 驗證腳本（stdlib-only）
├── plans/                 # 規劃文件
└── reports/               # 分析輸出
```
