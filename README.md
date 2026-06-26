# taiwan-k12-curriculum

> 台灣 108 課綱 K12 課程結構化資料集 — 課綱 + 全領域知識圖譜 + 公開試題

---

## 為什麼做這個

做一個教材遊戲，讓小朋友**邊玩邊學、不用等學校教到才學會**。

前備會了就可以往前推（這對所有領域都適用，不只數學）。

這個 repo 是**遊戲要吃的內容資料層**，不是遊戲本體。

---

## 目前狀態

| Phase | 工作 | 狀態 |
|-------|------|------|
| P0 | scaffold | ✅ 2026-06-23 |
| P1 | 課綱結構化（20 領域）| ✅ 2026-06-23 |
| P1.5 | 動機研究（P4 用）| ✅ 2026-06-23 |
| P2 | 部編本教材 | ⏳ 待做 |
| P2-B | 公開試題（CEEC 學測/分科）| ✅ 2026-06-26 |
| P3 | 知識圖譜骨架 | ✅ 2026-06-24（語意邊未驗證）|
| P4 | 遊戲端整合 | ⏳ |

詳細看 [`ROADMAP.md`](./ROADMAP.md)。

---

## 量化指標

| 項目 | 數量 |
|------|-----:|
| 領域數（課綱）| 11 |
| 學習階段 | I–V（國小低中高年級 / 國中 / 高中）|
| 結構化檔（curriculum structured.json）| 20 |
| 學習表現編碼（perf）| 1812 |
| 學習內容編碼（cont）| 2999 |
| 知識圖譜節點 | 4811 |
| 知識圖譜邊 | 1922（auto-detected，**語意未人工驗證**）|
| 知識圖譜 domain graph | 12 |
| CEEC 公開試題 | 163 PDF + 82 .txt |

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
    {"id": "數學/N-1-1", "domain": "數學", "category": "content", "stage": "I", "ordinal": 1}
  ],
  "edges": [
    {"from": "數學/N-1-1", "to": "數學/N-2-1", "type": "prerequisite"}
  ]
}
```

從當前節點往前追 `prerequisite` 邊，回答「要學什麼才能進入這關」。

每個領域獨立 graph 在 `knowledge-graph/<領域>/graph.json`。

**注意**：當前邊都是 auto-detected stage 升序預設邊（`N-1-X → N-2-X → ... → N-5-X`），**語意正確性未人工驗證**。要在 `plans/<domain>/edges.md` 加人工標註，`generate_graph.py` 會自動合併。

### 給老師 / 教材編者

讀 [`curriculum/`](./curriculum/) 對應領域：
- `<領域>_index.md` — 目錄索引
- `*.structured.json` — 結構化（含 perf / cont 編碼、aligned_codes、raw_section_5 原文保底）
- `*.md` — 原文 markdown

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

- ❌ 教師手冊、評量卷、習作解答（遊戲端自己生成）
- ❌ 影音、互動教材（遊戲端自己生成）
- ❌ 民間出版社（康軒/南一/翰林）的付費教材（版權）
- ❌ 來源未授權的段考題（米蘭老師 Drive、地方學校段考 — working tree 自用不公開）

---

## 資料來源 + 授權

| 來源 | 內容 | 授權 | 公開在 GitHub |
|------|------|------|---------------|
| 教育部 108 課綱 | 課綱原文 | CC BY 4.0 | ✅ |
| 國家教育研究院（NAER）| 部編本教材 | CC BY（多數）| 待 P2 |
| 大考中心 CEEC | 學測 / 分科 / 指考 | 政府公開（合理使用）| ✅ |

**程式碼授權**：MIT（見 [`LICENSE`](./LICENSE)）。
**第三方內容**：原始發布單位之授權，再散布時保留原始出處與授權標示。

canonical source 以**教育部**為主、**國教院**為輔。

---

## 結構

```
.
├── CLAUDE.md              # 給 AI 接手的交接單
├── README.md              # 本檔（給人看）
├── LICENSE                # MIT(code) + 第三方授權註記
├── ROADMAP.md             # TODO 進度
├── docs/
│   ├── knowledge-graph-schema.md
│   ├── motivation-research-collection-mechanics.md
│   ├── sdt-design-audit-framework.md
│   ├── p4-design-concept-pet-home.md
│   └── textbook-sources-survey.md
├── curriculum/            # 108 課綱（純文字 + structured.json）
├── knowledge-graph/       # 全領域知識圖譜（graph.json + graph.mermaid）
├── exams/                 # CEEC 公開試題（PDF + txt）
├── scripts/               # 抓取 / 轉換 / 驗證腳本（stdlib-only）
├── plans/                 # 規劃文件
└── reports/               # 分析輸出
```
