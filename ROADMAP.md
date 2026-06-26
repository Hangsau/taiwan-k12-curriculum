# ROADMAP

> TODO 清單。詳細交接單看 `CLAUDE.md`。
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

- [x] 探勘：教育部 / 國教院哪些領域有完整指引文件
- [x] 抓全部領域：國語文、本土語文、英語文、數學、社會、自然科學、藝術、健康與體育、綜合活動、科技、國防（高中） — **20/20 完成**
- [x] 轉純文字（PDF → Markdown，pdftotext）
- [x] 寫 `scripts/download_curriculum.py`（可重跑）
- [x] 為每個領域生 `_index.md` MOC
- [x] 結構化：20 個 `<stem>.structured.json`（universal schema，Type A/B/none 三變體）
- [x] 寫 `scripts/parse_curriculum.py`（stdlib only，可重跑、idempotent）
- [x] 寫 `scripts/verify_curriculum.py`（含 regex self-test，20/20 pass exit 0）
- [x] 更新 aggregate `curriculum/_index.json` 加 structured_summary（總 perf 1812 / cont 2999）

---

## Phase 1.5 — 遊戲化動機研究 ✅ 2026-06-23

> 目標：在 P4 遊戲端設計前，先研究「蒐集機制會不會毀掉內在動機」這個核心問題，避免設計出踩 SDT / overjustification 陷阱的遊戲

- [x] `docs/motivation-research-collection-mechanics.md`（~18K 字）— deep-research workflow（5 angles, 15 sources, 39 claims, 25 verified, **8 confirmed / 15 refuted / 4 evidence gap**）
  - 理論：SDT 三大需求 + CET controlling vs. informational + OIT 內化連續線 + Deci 1971 經典實驗
  - 設計原則矩陣（年齡 × 蒐集類型）— 該做 ✅ / 該避免 ❌ / 不確定 ⚠️
  - 9 大領域 × 蒐集類型適配性矩陣（推論性，標明 evidence gap）
  - 案例研究：DragonBox（mastery-coupled 範例）/ Duolingo（controlling framework 警示）
- [x] `docs/sdt-design-audit-framework.md` — SDT 機制級設計稽核框架（每個機制跑三道閘門）
- [x] `docs/p4-design-concept-pet-home.md` — 寵物養成 + 居家擺飾玩法的設計概念藍本
- [ ] 補年齡層差異研究（1-3 / 4-6 / 7-9 年級對三種蒐集類型反應）— evidence gap
- [ ] Hamari 2015 結果方向驗證（DOI 直讀 paper）— evidence gap
- [ ] Loot box / gacha 對兒童長期影響（Zendle 2020 等）— evidence gap

---

## Phase 2 — 抓部編本教材 ⏳

> 目標：把國家教育院部編本教材整理成純文字
> 注意：108 課綱後多數領域已委由民間編寫（審定版），部編本可能只佔少數，先探勘

- [x] 探勘腳本 + 矩陣初版（`scripts/probe_textbooks.py` + `plans/P2-coverage-survey.md`）
- [x] 6 來源探勘（均一/學習吧/國教署/NAER/因材網/data.gov.tw）→ 詳見 `docs/textbook-sources-survey.md`
- [ ] 真正的部編本教材抓取（仍待做）
- [ ] 對齊 curriculum codes
- [ ] 結構化 JSON

### 已撤回（2026-06-26）

之前 m3 標 ✅ 的內容實際上不堪用，已全刪：

- ~~均一教育平台 21 年級總覽（archived/junyi/）~~：抓到的是網站 HTML chrome（「支持均一」「立即支持」「登入註冊」），真實教學內容極少
- ~~AI 衍生 12 stage 教材（generated/）~~：LLM 機械式重複展開課綱（「`1-Ⅱ-1`（學生能做到第 1 項表現）」），加上抽查發現「3 顆蘋果寫 2 顆」錯誤
- ~~章節深入 POC 6 章節~~：同上
- ~~33 .structured.json + 3237 對齊 codes~~：依附在不存在的教材上

教訓：教材內容必須有人類審查或來自既定權威教材源，不可純 LLM 機械填空。

---

## Phase 2-B — 考卷蒐集 ✅ 2026-06-26（公開部分）

> 目標：蒐集大考中心 + 段考考卷作為 P4 遊戲端的題目素材

### ✅ 公開（GitHub）

- [x] CEEC 大考中心學測 / 指考 / 分科：163 個 PDF + 82 個 .txt（108–115 學年）— 政府公開合理使用
- [x] 寫 `scripts/download_ceec_all_years.py`、`scripts/extract_exams_to_md.py`、`scripts/verify_exams_md.py`

### 🔒 working tree 自用（不公開）

- [x] 米蘭老師 Drive 段考：4007 個 PDF/DOC/DOCX（國中 1-3 + 國小 1-6 為主）— 來源未明示授權散布
- [x] 大墩國小段考：367 個 PDF/DOC（國小 1-6）— 校自製授權不明
- [x] 衍生 .md 4577 個按 (學段, 年級, 科目) 分類，frontmatter 含 sha256 / source / year_roc / test_type / grade_label / subject
- [x] mojibake 修復（latin-1 → UTF-8 還原檔名與 frontmatter）

### 已撤回（2026-06-26）

- ~~米蘭老師 506 + ddes 73 個原始檔 commit 到 GitHub~~：未授權散布，已 git filter-repo 從 history 移除 + force push
- ~~OCR 救 1301 個純圖檔~~：tesseract aggressive 3 次失敗，原圖品質物理極限，直接刪除

---

## Phase 3 — 全領域知識圖譜 ✅ 2026-06-24

> 目標：為每個領域畫出 1-12 年級的知識點前備依賴圖譜

- [x] 設計知識圖譜 schema（`docs/knowledge-graph-schema.md`）— 解答 Open Question #4
- [x] 寫 `scripts/generate_graph.py` 從 `structured.json` 產 `graph.json` + `graph.mermaid`
- [x] 全 12 領域 graph：4811 nodes / 1922 edges
- [x] 寫 `scripts/verify_graph.py`（schema 合規、無循環、stage 單調、node 數一致、跨域一致性）
- [x] 12/12 domain PASS + 6/6 self-test + 跨域一致性 PASS
- [ ] **語意邊驗證**：當前 1922 邊都是 auto-detected stage 升序預設邊，**未經人工驗證語意正確**。要靠 `plans/<domain>/edges.md` 補人工標註（generate_graph.py 會自動合併手動 + auto）
- [ ] 跨 domain 邊（v1 不做，靠 keywords 弱搜尋）
- [ ] Title / Description 自動抽取（v1 留空）

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

## Phase 5 — 開放資料釋出 ❌ 取消

> 撤回原因（2026-06-26）：m3 自決發行 v0.5.0，未獲使用者授權；且當前 P2 教材實際為 0、P3 語意邊未驗證、考卷品質參差，repo 還在開發中不應對外 release。
>
> 已撤：CITATION.cff、docs/release-notes.md、README v0.5.0 tone、bibtex 引用範例。
>
> 未來如要 release：先把 P2 教材實做完 + P3 語意邊驗證完 + 與使用者確認 license + 重新評估發行策略。

---

## 圖例

- ✅ 完成
- ⏳ 待辦
- 🚧 進行中
- ❌ 取消 / 不做
