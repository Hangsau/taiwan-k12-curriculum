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

## Phase 1 — 抓 108 課綱 🚧 2026-06-23 部分完成

> 目標：把教育部 108 課綱各領域指引整理成純文字 + 結構化 JSON

- [x] 探勘：教育部 / 國教院哪些領域有完整指引文件（NAER PageSyllabus?fid=52）
- [x] 抓全部領域：國語文、本土語文、英語文、數學、社會、自然科學、藝術、健康與體育、綜合活動、科技、國防（高中） — **20/20 完成**
- [x] 轉純文字（PDF → Markdown，pdftotext）
- [x] 寫 `scripts/download_curriculum.py`（可重跑）
- [x] 為每個領域生 `_index.md` MOC
- [ ] 結構化（每個學習內容 / 學習表現 → JSON）
- [ ] 寫驗證腳本（檢查必填欄位、跨年級連續性）

---

## Phase 2 — 抓部編本教材 ⏳

> 目標：把國家教育院部編本教材整理成純文字
> 注意：108 課綱後多數領域已委由民間編寫（審定版），部編本可能只佔少數，先探勘

- [ ] 探勘：哪些領域仍有部編本（國小 / 國中 / 高中）
- [ ] 抓純文字（OCR 或官方提供的文字檔）
- [ ] 對齊課綱（標出對應的學習內容）
- [ ] 結構化（單元 / 課次 / 段落 → JSON）

---

## Phase 3 — 全領域知識圖譜 ⏳

> 目標：為每個領域畫出 1-12 年級的知識點前備依賴圖譜

- [ ] 設計知識圖譜 schema（節點 = 知識點，邊 = 前備依賴）
- [ ] 全領域並行：國語文、本土語文、英語文、數學、社會、自然科學、藝術、健康與體育、綜合活動、科技、國防
- [ ] 結構化：`graph.json`（機器讀）+ `graph.mermaid`（人讀）
- [ ] 寫 README 說明怎麼看、怎麼用

---

## Phase 4 — 遊戲端整合介面 ⏳

> 目標：定義這個 repo 怎麼被遊戲端使用

- [ ] 資料 schema 定義（給遊戲端讀的格式）
- [ ] API 契約（REST / static JSON / SQLite？之後定）
- [ ] 版本管理（資料更新不破壞遊戲端）
- [ ] 範例 client（reference implementation）

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
