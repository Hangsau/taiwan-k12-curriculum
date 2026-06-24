# 藝術 — 知識圖譜

> 自動產生於 2026-06-24T20:19:31+08:00
> 工具：`scripts/generate_graph.py`
> 來源 schema：`docs/knowledge-graph-schema.md`

## 統計

- **總 nodes**：117（content 54 + performance 63）
- **總 edges**：79（auto-detect 79 + manual 0）
- **來源 .structured.json**：1 個

### 各 stage 分布

| Stage | 數量 |
|-------|------|
| II | 32 |
| III | 32 |
| IV | 23 |
| V | 30 |

### 各 category 分布（取前 10）

| Category | 數量 |
|----------|------|
| 1 | 25 |
| E | 21 |
| 2 | 20 |
| P | 18 |
| 3 | 18 |
| A | 15 |

## 檔案

- `graph.json` — 完整 nodes + edges
- `graph.mermaid` — Mermaid 視覺化（> 50 nodes 圖會擠，可到 https://mermaid.live 渲染）
- 本 README — 給人看的領域摘要

## 如何讀這個圖譜

- `node.id` 格式：`<domain>/<code>`，例如 `數學/N-3-1`
- `node.type`：`content`（學習內容）/ `performance`（學習表現）
- `edge.from → edge.to`：學完 from 才能學 to（from 是 to 的前備）
- `edge.strength`：`required` / `recommended` / `optional`
- `edge.source`：`auto`（自動偵測）或 `manual:<file>`（人工標註）

## 邊的來源

- **auto-detect**：同 category + 同 ordinal + 跨 stage 升序（推薦起點，不一定語意正確）
- **manual**：plans/藝術/edges.md（如有）

## 下一步

- 加 `plans/<domain>/edges.md` 補特殊依賴（auto-detect 不夠時）
- 從 `raw_section_5` 自動抽取 `node.title` / `node.description`（heuristic）
- 跨 domain 邊（v2 才做）

*由 generate_graph.py 自動產生於 2026-06-24T20:19:31+08:00*
