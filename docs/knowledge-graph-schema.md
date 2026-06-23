# Knowledge Graph Schema

> **本檔在專案中的定位**
>
> P3 全領域知識圖譜的設計依據。決定**節點怎麼切、邊怎麼畫、粒度多細、跨領域怎麼接**，給後面產資料 + 寫 generator + 驗證用。
>
> **為什麼需要它**：Open Question #4（圖譜粒度）一直沒定論。如果不先定 schema 就動 P3，跑出來的圖譜會跟 curriculum/ 對不上、或粒度飄移無法比較。先寫 schema 讓 P3 開始前有 single source of truth。
>
> **設計原則**：跟現有 curriculum/ 編碼系統對齊（不重新發明），保留 raw text fallback（schema 不夠用時下游可重 parse），盡量簡單（edge case 進 `warnings` 不擋 exit 0）。

---

## 0. 30 秒版

- **節點 = 一個 curriculum 編碼**（如 `數學/N-III-1`）
- **邊 = 前備依賴**（學會 A 才能學 B）
- **粒度 = 學習內容層**（不細到「兩位數乘法進位」這種小步）
- **領域 = 11 個 + 總綱**（跟 `curriculum/` 一致）
- **教育階段 = I / II / III / IV / V**（跟 parser 的 `stages_present` 一致）

```
domain (11)
 └─ graph.json  ←  該領域所有 nodes + edges
 └─ graph.mermaid  ←  視覺化

root
 └─ knowledge-graph/_all-graph.json  ←  跨領域聚合
```

---

## 1. 設計目標

下游遊戲端要能回答這些問題：

| 問題 | 圖譜能給的 |
|------|-----------|
| 「我該學什麼才能進入這關？」 | 從當前節點往回追 `prerequisite` 邊 |
| 「學完這個還能往哪走？」 | 從當前節點往前追 `prerequisite` 反向 |
| 「這概念在哪些領域有？」 | 跨 domain search（同 `description` 或同 `keyword`） |
| 「國小 / 國中 / 高中 各學到什麼程度？」 | 依 `stage` filter |
| 「這概念跟其他概念什麼關係？」 | 看 `related` 邊（同主題但非前備）|

不涵蓋的問題（v1 不做，之後再說）：
- 「這概念花幾小時學會」— 沒資料來源
- 「每個學生學到哪」— 個人化資料，不在這個 repo
- 「跨課綱版本（新舊課綱對照）」— 過 Open Question #2 之後

---

## 2. 節點類型（Node）

每個節點對應 curriculum/ 的一個編碼。

### 2.1 兩種節點子類型

| 子類型 | 來源 | 範例 |
|--------|------|------|
| **content** | 學習內容編碼（`content_codes`）| `數學/N-III-1` 理解分數 |
| **performance** | 學習表現編碼（`performance_codes`）| `數學/n-III-1` 理解分數的具體表現 |

預設 **content 為主節點**（圖譜的骨幹），**performance 為輔助節點**（標記「能做到什麼」）。

理由：學習內容是「教的東西」，學習表現是「教完能做到什麼」。前備依賴主要發生在 content 層（沒學會分數就沒辦法做分數的應用題），performance 層通常跟 content 一一對應、不另成節點。

**例外**：如果某 performance 編碼找不到對應 content（如健康與體育有獨立的動作技能編碼），保留為獨立節點，不強行配對。

### 2.2 Node schema

```json
{
  "id": "數學/N-III-1",
  "domain": "數學",
  "code": "N-III-1",
  "code_format": "numeric_phase",
  "stage": "III",
  "category": "N",
  "ordinal": 1,
  "type": "content",
  "title": "理解分數",
  "description": "理解分數的意義與表記方式",
  "source_file": "curriculum/數學/數學領域課程綱要.structured.json",
  "source_ref": {
    "structured_section": "content_codes",
    "index": 12
  },
  "keywords": ["分數", "分子分母"],
  "warnings": []
}
```

| 欄位 | 必填 | 說明 |
|------|------|------|
| `id` | ✓ | 唯一識別，格式 `<domain>/<code>`，用 `domain/code` 而非 `domain/section/code` 避免特殊字元 |
| `domain` | ✓ | 11 領域名（中文）+ 「總綱」 |
| `code` | ✓ | 原始編碼（如 `N-III-1`） |
| `code_format` | ✓ | `numeric_phase` 或 `roman_phase`（跟 parser 一致）|
| `stage` | ✓ | I/II/III/IV/V（羅馬數字正規化）|
| `category` | ✓ | 編碼前綴（如 `N` 表示 number） |
| `ordinal` | ✓ | 編碼序號（int）|
| `type` | ✓ | `content` / `performance` |
| `title` | ○ | 簡短標題（≤ 30 字，之後可從 curriculum 原文自動抽） |
| `description` | ○ | 一句話描述 |
| `source_file` | ✓ | 對應 `curriculum/<domain>/<...>.structured.json` 路徑 |
| `source_ref` | ○ | 指向 structured.json 內位置，便於 raw 還原 |
| `keywords` | ○ | 跨領域搜尋用 tag |
| `warnings` | ○ | 解析時的非阻擋問題（缺 title / description 等）|

### 2.3 節點生成規則

v1 generator 從 `curriculum/<domain>/<stem>.structured.json` 產 nodes：

```
for each structured in curriculum/<domain>/*.structured.json:
  for each code in structured.content_codes:
    node = Node(id=f"{domain}/{code.code}", ...)
  for each code in structured.performance_codes:
    # 同上但 type=performance
```

不重新解析 markdown — `structured.json` 是 source of truth。要 raw 文字回查 `structured.raw_section_5` 或 `source_file` 對應的 .md。

---

## 3. 邊類型（Edge）

圖譜只放一類邊：**前備依賴（prerequisite）**。

其他關係（同主題、延伸閱讀、跨領域對應）放 §3.3 輔助邊類型。

### 3.1 Prerequisite 邊 schema

```json
{
  "from": "數學/N-II-3",
  "to": "數學/N-III-1",
  "relation": "prerequisite",
  "strength": "required",
  "note": "需先理解整數與分數的關係才能進入分數運算"
}
```

| 欄位 | 必填 | 說明 |
|------|------|------|
| `from` | ✓ | 來源節點 id（前備） |
| `to` | ✓ | 目標節點 id（後學） |
| `relation` | ✓ | `prerequisite` / `related` / `extends` |
| `strength` | ○ | `required` / `recommended` / `optional` |
| `note` | ○ | 為什麼這條邊存在（一句話） |

### 3.2 邊的方向

`from → to` 表「要學 from 才能學 to」（from 是 to 的前備）。

Mermaid 圖：`from --> to`（箭頭指向後學）。

### 3.3 輔助邊類型（v1 不強求）

| 類型 | 用途 | 範例 |
|------|------|------|
| `related` | 同主題但非前備（並列概念）| `數學/N-III-1` ↔ `數學/N-III-2`（分數 vs 小數）|
| `extends` | 延伸加深（同一概念的進階）| `數學/N-IV-1` → `數學/N-V-1`（高中加深加廣）|

v1 先放 `prerequisite`，其他之後再加。

### 3.4 邊的來源

| 來源 | 範例 |
|------|------|
| **curriculum 編碼的 stage ordinal** | 同 category 不同 stage → 後 stage 是前 stage 的延伸（自動偵測）|
| **人工標註** | `plans/<domain>/edges.md` 寫人讀的邊，generator 解析成 JSON |
| **跨領域對應** | 同 `description`/`keywords` 跨 domain 配對（v2 才做）|

v1 優先 **自動偵測**（stage ordinal + 同 category），人工補 `plans/<domain>/edges.md` 補特殊依賴。

---

## 4. 教育階段定義

跟 parser 的 `stages_present` 一致：

| Stage | 中文 | 對應學制 | parser 來源 |
|-------|------|---------|------------|
| **I** | 第一學習階段 | 國小 1-2 年級 | `1` 或 `Ⅰ` |
| **II** | 第二學習階段 | 國小 3-4 年級 | `2` 或 `Ⅱ` |
| **III** | 第三學習階段 | 國小 5-6 年級 | `3` 或 `Ⅲ` |
| **IV** | 第四學習階段 | 國中 7-9 年級 | `4` 或 `Ⅳ` |
| **V** | 第五學習階段 | 高中 10-12 年級 | `5` 或 `Ⅴ` |

注意：
- **數學**用 `numeric_phase`（`1-5`），其他領域用 `roman_phase`（`Ⅰ-Ⅴ`）— parser 已正規化為 `I-V`
- **國防**只到 V（高中限定）
- **本土語文**結構特殊（閩南語 / 客家語 / 原住民族語 各 6 子檔），但都遵循同一 stage 規則

---

## 5. 領域分割（11 領域 + 總綱）

跟 `curriculum/` 目錄對齊：

```
knowledge-graph/
├── 國語文/graph.json        # 從 curriculum/國語文/ 產
├── 本土語文/graph.json      # 注意：6 個子檔，先合併再產
├── 英語文/graph.json
├── 數學/graph.json
├── 社會/graph.json          # Type B，依 stage 切
├── 自然科學/graph.json      # Type B，依 stage 切
├── 藝術/graph.json
├── 健康與體育/graph.json    # 2 個子檔，先合併
├── 綜合活動/graph.json
├── 科技/graph.json
├── 國防/graph.json
└── 總綱/graph.json          # 只有 raw，無編碼（content_codes = 0）
```

**子檔合併規則**（健康與體育 / 本土語文）：
- 同 domain 的所有 `.structured.json` 的 nodes 全收進同一份 graph.json
- `source_file` 欄位標明來源子檔
- 跨子檔重複的編碼（極少見）→ merge，warnings 加「多 source」

---

## 6. 粒度決策（Open Question #4 解答）

**決策**：圖譜粒度 = curriculum 學習內容編碼層。

不更細（不拆「兩位數乘法進位」這種小步），不更粗（不聚合到「分數」這種大主題）。

理由：
- **不更細**：curriculum 的學習內容已是教育部 / 國教院專家定的「一個教學單元粒度」，比手動拆細更權威且可追溯。細到「兩位數乘法進位」會脫離 source of truth、難以驗證
- **不更粗**：遊戲端要的是「進入下一關要會什麼」的具體節點，聚合到大主題顆粒度太粗、實用性低

**保留彈性**：如果未來遊戲端發現需要更細，加一層 `sub_concepts` 欄位在 node 裡（v2 才做）。v1 不強求。

**Title / Description 來源**：v1 先空（generator 不強求），未來從 `raw_section_5` 自動抽取（heuristic：取編碼出現的段落的標題行）。標 [TODO] 不擋 exit。

---

## 7. 跨領域依賴（v1 不做，設計保留介面）

某些概念跨領域：
- 「比例」在數學 / 自然科學 / 社會 / 藝術都出現
- 「資料分析」在數學 / 科技 / 綜合活動都出現

v1 不畫跨領域邊（避免主觀標註）。但保留：
- 每個 node 有 `keywords` 欄位，遊戲端可做 keyword 搜尋
- `knowledge-graph/_all-graph.json` 聚合所有 nodes，跨域 search 用

v2 才做：
- 跨域同 `keywords` 自動偵測 → `related` 邊
- 或人工標註 `plans/cross-domain-edges.md`

---

## 8. 檔案結構

```
knowledge-graph/
├── _all-graph.json          # 跨領域聚合（所有 nodes，domain-tagged）
├── _schema.json             # 寫死 schema 規格供下游驗證
├── 國語文/
│   ├── graph.json           # 該領域 nodes + edges
│   ├── graph.mermaid        # 視覺化
│   └── README.md            # 給人看的說明（這個領域有什麼、怎麼讀）
├── 本土語文/                # 6 子檔合併
├── ...
└── 總綱/
    ├── graph.json           # 只有 nodes（content_codes = 0，無 edges）
    └── graph.mermaid        # 空圖或只列總綱主題
```

`_all-graph.json` 結構：

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-XX-XXTHH:MM:SS+08:00",
  "domains": ["國語文", "本土語文", ..., "總綱"],
  "total_nodes": 1234,
  "total_edges": 567,
  "nodes": [...],   // 所有 nodes 加 domain 標籤
  "edges": [...]    // 所有 edges
}
```

---

## 9. 範例（片段）

### 9.1 數學 graph.json 片段

```json
{
  "schema_version": "1.0",
  "domain": "數學",
  "generated_at": "2026-XX-XXTHH:MM:SS+08:00",
  "total_nodes": 234,
  "total_edges": 89,
  "nodes": [
    {
      "id": "數學/N-II-3",
      "domain": "數學",
      "code": "N-II-3",
      "code_format": "numeric_phase",
      "stage": "II",
      "category": "N",
      "ordinal": 3,
      "type": "content",
      "title": "[TODO 從 raw_section_5 抽取]",
      "description": "",
      "source_file": "curriculum/數學/數學領域課程綱要.structured.json",
      "source_ref": {"structured_section": "content_codes", "index": 5},
      "keywords": [],
      "warnings": ["title/description 自動抽取未實作，v1 留空"]
    },
    {
      "id": "數學/N-III-1",
      "domain": "數學",
      "code": "N-III-1",
      "code_format": "numeric_phase",
      "stage": "III",
      "category": "N",
      "ordinal": 1,
      "type": "content",
      "title": "[TODO]",
      "description": "",
      "source_file": "curriculum/數學/數學領域課程綱要.structured.json",
      "source_ref": {"structured_section": "content_codes", "index": 12},
      "keywords": ["分數", "分子分母"],
      "warnings": []
    }
  ],
  "edges": [
    {
      "from": "數學/N-II-3",
      "to": "數學/N-III-1",
      "relation": "prerequisite",
      "strength": "recommended",
      "note": "[TODO 人工補 或 自動偵測]"
    }
  ]
}
```

### 9.2 Mermaid 片段

```mermaid
graph LR
  N_II_3["數學/N-II-3<br/>(II)"]
  N_III_1["數學/N-III-1<br/>(III)"]
  N_II_3 -->|prerequisite| N_III_1
```

（Mermaid 不支援 `/` 在節點 id，用 `_` 取代；視覺化時 label 顯示原編碼。）

---

## 10. 與現有資料層的對接

| 資料層 | 對圖譜的貢獻 | 從圖譜讀回 |
|--------|------------|-----------|
| `curriculum/<domain>/*.structured.json` | **nodes 的 source**（每個編碼一個 node）| `source_file` + `source_ref` 可回查 |
| `curriculum/_index.json` `structured_summary` | 驗證「圖譜 nodes 數 = structured 編碼數」| 對應 graph.json 的 `total_nodes` |
| `scripts/parse_curriculum.py` | 已抽出編碼，圖譜 generator 直接讀 `structured.json` 不重 parse | — |
| `scripts/verify_curriculum.py` | — | 加 §11 round-trip 檢查（§13 #4） |

**資料流**：`curriculum/*.md` → `parse_curriculum.py` → `*.structured.json` → `generate_graph.py`（P3 新寫）→ `knowledge-graph/<domain>/graph.json` + `graph.mermaid` + `_all-graph.json`。

---

## 11. 已知限制 / 取捨

- **Title / Description 自動抽取未實作**：v1 留空、`warnings` 標 TODO。下個 P3 階段補 heuristic（取編碼出現段落的前後 50 字）
- **跨領域邊 v1 不做**：避免主觀標註，靠 `keywords` 提供弱搜尋能力
- **人工邊標註**：v1 預設靠 stage ordinal 自動偵測，特殊依賴（跨 stage ordinal 的非單調依賴）需人工寫 `plans/<domain>/edges.md`
- **沒做 durability / 時間標記**：遊戲端想知道「學多久」目前無法回答（不在資料來源）
- **Mermaid 視覺化限制**：> 50 nodes 圖會擠，需分群或互動式（之後 v2 接 vis.js / d3）

---

## 12. 驗證方法

P3 開始時寫 `scripts/verify_graph.py`，至少檢查：

1. **node 數量一致**：每個 domain 的 `graph.total_nodes` = 對應 `structured.json` 的 `performance_count + content_count`
2. **edge 起終點存在**：所有 `from` / `to` 都對應到 graph 內的 node
3. **無循環**：prerequisite 邊不形成 cycle（A → B → A）
4. **stage 單調**（自動偵測邊）：`from.stage < to.stage`（國小不該前備高中）
5. **schema 合規**：每個 node / edge 符合本檔 §2.2 / §3.1 定義
6. **跨 domain 聚合一致**：`_all-graph.json` 的 nodes = 各 domain graph.json nodes 的聯集（無重複）

`verify_graph.py` 也應含 self-test（fixture 5+ 個 nodes / edges），exit code 區分工具壞（2）vs 資料壞（1）vs 全綠（0）。

---

## 13. 與其他文件的關係

- **上游**：`docs/motivation-research-collection-mechanics.md`（理論 — 圖譜粒度影響遊戲端設計）
- **上游**：`scripts/parse_curriculum.py` schema（圖譜 nodes 從這來）
- **下游**：`scripts/verify_graph.py`（本檔 §12 的實作）
- **下游**：P3 generator（從 `structured.json` 產 `graph.json`）
- **下游**：P4 遊戲端（讀 `graph.json` 找前備依賴）

---

## 14. 版本與維護

- **建立**：2026-06-23
- **依據**：`curriculum/*.structured.json` schema、`scripts/parse_curriculum.py` 編碼格式、Open Question #4
- **維護者**：Claude B（Linux VM 端，按 CLAUDE.md §14.1）
- **下次 review 觸發點**：
  - P3 generator 跑完後，回填真實 schema 應用案例
  - P4 遊戲端讀 graph.json 後發現欄位不足時
  - Open Question #4（粒度）若有變動決策

---

*最後更新：2026-06-23 晚（建立，給 P3 generator 當 single source of truth）*
