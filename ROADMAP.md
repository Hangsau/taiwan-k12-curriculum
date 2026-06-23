# ROADMAP

> TODO 清單（簡潔版）。詳細交接單看 `CLAUDE.md`。
> 更新：每完成一項就把 `⏳` 改 `✅`，加日期。

---

## Phase 0 — Scaffold ✅ 2026-06-23

- [x] 建 local project dir + git init
- [x] 寫 LICENSE + .gitignore
- [x] 寫 CLAUDE.md
- [x] 寫 README.md
- [x] 建空目錄骨架
- [x] 建 GitHub repo + 初始 push

---

## Phase 1 — 抓 108 課綱 ✅ 2026-06-23

> 目標：把教育部 108 課綱各領域指引整理成純文字 + 結構化 JSON

- [x] 探勘：教育部 / 國教院哪些領域有完整指引文件（NAER PageSyllabus?fid=52）
- [x] 抓全部領域：國語文、本土語文、英語文、數學、社會、自然科學、藝術、健康與體育、綜合活動、科技、國防（高中） — **20/20 完成**
- [x] 轉純文字（PDF → Markdown，pdftotext）
- [x] 寫 `scripts/download_curriculum.py`（可重跑）
- [x] 為每個領域生 `_index.md` MOC
- [x] 結構化：20 個 `<stem>.structured.json`（universal schema，Type A/B/none 三變體）
- [x] 寫 `scripts/parse_curriculum.py`（stdlib only，可重跑、idempotent）
- [x] 寫 `scripts/verify_curriculum.py`（含 regex self-test，20/20 pass exit 0）
- [x] 更新 aggregate `curriculum/_index.json` 加 structured_summary（總 perf 1773 / cont 2573）

---

## Phase 1.5 — 遊戲化動機研究 ✅ 2026-06-23

> 目標：在 P4 遊戲端設計前，先研究「蒐集機制會不會毀掉內在動機」這個核心問題，避免設計出踩 SDT / overjustification 陷阱的遊戲

- [x] `docs/motivation-research-collection-mechanics.md`（~18K 字）— deep-research workflow（5 angles, 15 sources, 39 claims, 25 verified, **8 confirmed / 15 refuted / 4 evidence gap**）
  - 理論：SDT 三大需求 + CET controlling vs. informational + OIT 內化連續線 + Deci 1971 經典實驗
  - 設計原則矩陣（年齡 × 蒐集類型）— 該做 ✅ / 該避免 ❌ / 不確定 ⚠️
  - 9 大領域 × 蒐集類型適配性矩陣（推論性，標明 evidence gap）
  - 案例研究：DragonBox（mastery-coupled 範例）/ Duolingo（controlling framework 警示）
- [ ] 補年齡層差異研究（1-3 / 4-6 / 7-9 年級對三種蒐集類型反應）— evidence gap
- [ ] Hamari 2015 結果方向驗證（DOI 直讀 paper）— evidence gap
- [ ] Loot box / gacha 對兒童長期影響（Zendle 2020 等）— evidence gap

---

## Phase 2 — 抓部編本教材 🚧

> 目標：把國家教育院部編本教材整理成純文字
> 注意：108 課綱後多數領域已委由民間編寫（審定版），部編本可能只佔少數，先探勘

- [x] 探勘腳本 + 矩陣初版（2026-06-23，`scripts/probe_textbooks.py` + `plans/P2-coverage-survey.md`，commit `4bb090c`）— 待 user 補 SOURCES 重跑
- [ ] user 補各領域各階段 NAER PageSyllabus URL（矩陣未定稿）
- [ ] 抓純文字（OCR 或官方提供的文字檔）
- [ ] 對齊課綱（標出對應的學習內容）
- [ ] 結構化（單元 / 課次 / 段落 → JSON）

---

## Phase 3 — 全領域知識圖譜 🚧

> 目標：為每個領域畫出 1-12 年級的知識點前備依賴圖譜

- [x] 設計知識圖譜 schema（2026-06-23，`docs/knowledge-graph-schema.md`，commit `b6bca8a`）— 解答 Open Question #4
- [ ] 寫 `scripts/generate_graph.py` 從 `structured.json` 產 `graph.json` + `graph.mermaid`
- [ ] 全領域並行：國語文、本土語文、英語文、數學、社會、自然科學、藝術、健康與體育、綜合活動、科技、國防
- [ ] 寫 `scripts/verify_graph.py`（schema 合規、無循環、stage 單調、node 數一致 — 6 項檢查）
- [ ] 寫 README 說明怎麼看、怎麼用

---

## Phase 4 — 遊戲端整合介面 ⏳

> 目標：定義這個 repo 怎麼被遊戲端使用
> 設計前必讀：`docs/motivation-research-collection-mechanics.md`（研究）+ `docs/sdt-design-audit-framework.md`（稽核框架）+ `docs/p4-design-concept-pet-home.md`（寵物+居家擺飾設計概念）

- [ ] 資料 schema 定義（給遊戲端讀的格式）
- [ ] API 契約（REST / static JSON / SQLite？之後定）
- [ ] 版本管理（資料更新不破壞遊戲端）
- [ ] 範例 client（reference implementation）
- [x] 遊戲化動機研究 + SDT 稽核框架 + 寵物/居家擺飾設計概念（前置設計，2026-06-23）

---

## Phase 5 — 開放資料釋出 ⏳

> 目標：讓其他人也能用這份資料

- [ ] GitHub Pages 文件站
- [ ] 下載 zip（per phase / per 領域）
- [ ] 資料儀表板（覆蓋率、更新時間）
- [ ] 引用文檔（citation.cff / DOI？）

---

## 圖例

- ✅ 完成
- ⏳ 待辦
- 🚧 進行中
- ❌ 取消 / 不做
