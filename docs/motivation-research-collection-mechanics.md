# 蒐集機制 vs. 內在動機：教育遊戲化設計的研究綜整

> **本檔在專案中的定位（給接手 game design 的 session 看）**
>
> 這是 `taiwan-k12-curriculum` 專案的**遊戲化設計研究文件**。資料層（108 課綱 + 部編本 + 知識圖譜）已 P1 完成。下一階段（P4）要進入遊戲端整合介面 — 設計者面臨的核心問題之一就是「要不要用蒐集機制」。
>
> 本檔給設計者（人類或 AI）一份**理論 + 原則 + 案例**的依據，避免「直覺覺得卡片 / 徽章 / 寶物會讓孩子愛學，就這樣做」這種危險設計。
>
> **重要前提**：本研究的證據強度有差異。每個論點的「信心等級」在文中標示。**refuted 與 evidence gap 的部分必須誠實看，不能當作已驗證事實套用。**

---

## 0. 執行摘要（TL;DR）

**核心結論（一行）**：蒐集機制在教育遊戲中**不必然**侵蝕孩子的內在動機。會不會侵蝕，取決於兩個關鍵變項——

1. **獎勵的「框定方式」**（controlling 控制性 vs. informational 資訊性）
2. **是否滿足 SDT 三大心理需求**（自主 Autonomy / 勝任 Competence / 關聯 Relatedness）

**對 12 年國教設計的立即建議**：
- ✅ 可以用「**mastery-coupled 蒐集**」——蒐集物的獲得與孩子的學習掌握度掛鉤（DragonBox 的龍成長是範例）
- ⚠️ 小心用「**控制性框架**」的蒐集——強制每日登入、streak 中斷懲罰、leaderboard 比較
- ❌ 避免「**任意累積**」+「**無上限**」+「**外顯稀有度**」——這是 gacha / loot box 的設計 pattern，在教育情境會同時傷害 SDT 三大需求

**研究限制（必讀）**：
- 不同年齡層（1-3 年級 / 4-6 年級 / 7-9 年級）對三種蒐集類型的**差異反應**目前沒有通過嚴格驗證的學術文獻可引用——這段是 evidence gap，設計時要保守
- Hamari 2015 是同類研究中規模最大的田野實驗之一（2-year between-group, N=1,410→1,579），但**「badges 是否真的有效」這個實驗結果的方向性在本研究中未被驗證**（refuted），引用時只能引用方法學規模
- 本檔多數案例細節（Duolingo、DragonBox、Minecraft Education、ClassDojo、寶可夢）的長期內在動機效應也屬 evidence gap——只能引用「設計模式 + 設計意圖」，不能當作「孩子後續還會學」的證據

---

## 1. 研究方法說明

本檔由 deep-research workflow（5 個研究角度 → 平行搜尋 → 抓 15 個來源 → 萃取 39 個 claims → 對抗式驗證 25 個 claims → 整合）產出。

**驗證規則**：每個 claim 經過 3 位獨立 verifier 審核，需 ≥2/3 同意才能通過。通過率 8/25 = 32%，**這是這個領域的特性（不是失敗）——很多熱門論點其實證據不夠強**。

### 1.1 通過驗證的論點（可用）

| # | 論點摘要 | 信心 | 核心來源 |
|---|---------|------|---------|
| 1 | SDT 三大心理需求（自主、勝任、關聯）為普遍性、與生俱來 | high | selfdeterminationtheory.org, Wikipedia |
| 2 | CET（認知評價理論）區分「控制性獎勵」vs.「資訊性獎勵」— 前者削弱、後者增強內在動機 | high | selfdeterminationtheory.org, Wikipedia |
| 3 | 外在動機沿「內化連續線」分布（外部調節 → 內攝 → 認同 → 整合）— 框定方式決定效果 | high | selfdeterminationtheory.org, Wikipedia |
| 4 | Deci 1971 經典實驗：金錢獎勵移除後降低內在動機，言語讚美（資訊性）增強之 | high | Wikipedia（Deci / SDT / Overjustification 條目交叉確認） |
| 5 | Duolingo 將「留存 / 回流」行為最佳化（Yancey & Settles, KDD 2020，200M 推播樣本）— 設計優先序是 engagement，不是學習 | high | research.duolingo.com |
| 6 | DragonBox 採雙機制設計（卡片操作為內在學習、龍成長 + bonus star 為外在疊加）— mastery-coupled 蒐集 | medium | Wikipedia, ResearchGate |
| 7 | Hamari 2015「Do badges increase user activity?」是同類研究最大規模田野實驗（2-year, N=1,410→1,579）— 方法學上為基準參考 | high | ResearchGate, Semantic Scholar |
| 8 | SDT 對教育遊戲的應用意涵：強制登入會 thwart autonomy、pay-to-win gacha 會 thwart competence | medium | selfdeterminationtheory.org（推論） |

### 1.2 被 refuted 的論點（不可用為根據）

以下是被對抗式驗證**否決**的熱門敘事，列在這裡是為了讓後續設計者知道「這些話聽起來很有學術感，但其實證據不夠」：

| 敘事 | 為什麼 refuted |
|------|---------------|
| 「Hamari 2015 證實 badges 增加 user activity」 | vote 1-2，未達通過標準。Hamari 結果方向性在本研究中無法確認 |
| 「Eisenberger & Cameron 1996 推翻 Deci — 過度合理化效應不存在」 | vote 0-3。對反證文獻的引用本身證據不足 |
| 「Pizza Hut Book It! 閱讀獎勵計畫未增加也未減少動機 → 過度合理化效應不自動成立」 | vote 0-3。case study 證據強度不足 |
| 「兒童比成人更易受過度合理化效應影響」 | vote 1-2。原始敘事的方向性未通過驗證 |
| 「Lepper 1973 直接結論：校園獎勵系統會損害長期學習動機」 | vote 0-3。直接結論過強，原研究並未如此聲稱 |
| 「Duolingo 內部 Markant et al. 2016 認知科學研究支持 SDT 自主導向」 | vote 0-3。SDT 應用詮釋的證據不足 |
| 「內在動機的操作型定義是『為活動本身而從事』— 因此蒐集機制必須保留探索性 / 遊戲性才能避免削弱」 | vote 0-3。雖然直覺合理，但這條敘事的因果鏈證據不足 |

**設計意涵**：不要在文件 / 提案中引用以上論點。引用任何學術研究前，回到原始 paper 確認。

### 1.3 Evidence gap（需要後續研究補的洞）

| 缺口 | 影響範圍 |
|------|---------|
| 不同年齡層（1-3 / 4-6 / 7-9 年級）對三種蒐集類型的差異反應 | 本檔 §7 年齡層矩陣只能給**保守建議**，不可視為已驗證 |
| Hamari 2015 實際結果方向（positive / null / negative） | 引用時只能講「方法學規模大」，不能講「證實 badges 有效」 |
| 108 課綱九大領域 × 三種蒐集類型的適配性矩陣 | §10 台灣在地建議只能從「領域特性」推論，缺實證 |
| Minecraft Education、ClassDojo、寶可夢、Prodigy 等案例的「孩子後續還會不會學」 | 案例章節只能引用設計模式，**不可當作長期動機的證據** |

---

## 2. 理論基礎（一）：自我決定理論 SDT

### 2.1 SDT 三大心理需求

**核心論點（high confidence）**：自我決定理論（Self-Determination Theory, SDT）由 Deci & Ryan 1985 提出，假定所有人類有三個普遍性、與生俱來的心理需求——

| 需求 | 涵義 | 教育遊戲中的體現 |
|------|------|----------------|
| **自主 Autonomy** | 行為出自自我意志，非被外部壓力驅動 | 玩家選擇關卡、策略、進度 |
| **勝任 Competence** | 感受到自己能勝任、有成長 | 難度遞增、回饋清晰、能力可見化 |
| **關聯 Relatedness** | 與他人有連結、歸屬感 | 合作、分享、社交對比 |

任一需求受阻（thwarting）會產生**質性不同**的功能成本（不是單純加總赤字）；三需求同時滿足則產生 wellness 與有效功能。這個 framework 是後續討論「蒐集機制會不會毀掉動機」的理論地基。

來源：selfdeterminationtheory.org/theory/, en.wikipedia.org/wiki/Self-determination_theory

### 2.2 兩個子理論：CET + OIT

SDT 不是單一理論，而是由多個子理論組成。在「獎勵 → 動機」這個問題上，兩個子理論直接相關：

#### 2.2.1 CET（認知評價理論, Cognitive Evaluation Theory）

**核心論點（high confidence）**：CET 處理社會情境（含獎勵、人際控制、自我涉入）如何影響內在動機。

關鍵區分——

- **控制性獎勵（Controlling reward）**：傳達「你做這件事是因為我逼你」的訊號 → **削弱**內在動機
- **資訊性獎勵（Informational reward）**：傳達「你做得很好、能力提升了」的訊號 → **增強**內在動機

這個區分對遊戲設計極重要——同樣是「給一張卡」，如果是「完成任務就發，無法控制何時拿」→ 控制性；如果是「完成挑戰，顯示你的進度條往前 +1，展現能力曲線」→ 資訊性。

#### 2.2.2 OIT（有機整合理論, Organismic Integration Theory）

**核心論點（high confidence）**：外在動機不是單一種類，而是沿著「內化連續線」分布——

```
外部調節 External Regulation  →  內攝調節 Introjection  →  認同調節 Identification  →  整合調節 Integration
（純外在壓力）                  （內在化壓力）            （認同價值）                （完全內化為自我）
```

連續線越右端，自主性越高。最右端的「整合調節」實證行為上跟內在動機難以區分，但本質仍是外在動機內化而成。

**設計意涵**：給孩子一個蒐集物（卡片、徽章），如果這個蒐集物能被**內化**（孩子認同「這代表我學會了某個概念」），它就走到了連續線右端，**不會**削弱內在動機。如果它停留在左端（「爸媽說拿滿 100 張卡就給我買玩具」），就會。

來源：selfdeterminationtheory.org/theory/, en.wikipedia.org/wiki/Self-determination_theory

---

## 3. 理論基礎（二）：過度合理化效應的經典實驗

### 3.1 Deci 1971 經典實驗

**核心論點（high confidence）**：Deci (1971) 在 *Journal of Personality and Social Psychology* (Vol. 18, pp. 105-115) 發表的研究是過度合理化效應的奠基實驗。

- **方法**：Soma cube puzzle 任務。實驗組每完成一個 puzzle 給 $1；對照組無獎勵。
- **結果**：
  - 獎勵期間，實驗組表現更好（外部動機提升 performance）
  - **獎勵移除後的自由選擇時段**，實驗組的自主從事時間顯著下降 — 內在動機被削弱
  - 同論文的 Experiment III 顯示**言語讚美**（資訊性回饋）反而增強內在動機

來源：en.wikipedia.org/wiki/Self-determination_theory, en.wikipedia.org/wiki/Overjustification_effect, en.wikipedia.org/wiki/Edward_Deci（交叉確認）

### 3.2 過度合理化效應 vs. SDT 的關係

**核心論點（high confidence）**：過度合理化效應的**理論機制**已經內建在 SDT 的 CET 子理論裡。它不是外加於 SDT 的命題，而是 CET 直接預測的結果：

> CET specifically addresses the effects of social contexts on intrinsic motivation, or how factors such as rewards, interpersonal controls, and ego-involvements impact intrinsic motivation and interest.

這意思是：**過度合理化效應的存在，是 SDT 框架的直接推論**。要「推翻過度合理化效應」必須動搖 SDT 本身，不是只批評單一實驗。

### 3.3 Murayama et al. 2010 後設分析

確認 tangible reward 削弱 intrinsic motivation 的方向性（雖然效應量有爭議）。

### 3.4 ⚠️ 不能引用的事

本研究中以下敘事**被 refuted**，**不可作為設計依據**：
- ❌ 「Hamari 2015 證實 badges 增加 activity」 — vote 1-2
- ❌ 「Eisenberger & Cameron 1996 推翻過度合理化效應」 — vote 0-3
- ❌ 「Pizza Hut Book It! 證實過度合理化效應不成立」 — vote 0-3
- ❌ 「兒童比成人更易受過度合理化效應影響」 — vote 1-2
- ❌ 「Lepper 1973 直接結論校園獎勵會毀掉長期動機」 — vote 0-3

**設計意涵**：當有人引用以上敘事來反對或支持某個設計決策時，要回頭查原始 paper，不要憑這些敘事做決定。

---

## 4. 遊戲化研究：從 SDT 到實務

### 4.1 Hamari 2015 方法學規模

**核心論點（high confidence）**：Hamari, Koivisto, Sarsa (2015) 「Do badges increase user activity?」發表於 *Computers in Human Behavior* (Elsevier, DOI 10.1016/j.chb.2014.10.051)，目前引用約 1,245 次（截至本研究 2026-06）。

**方法**：
- Pre-implementation 群 N=1,410（監測 1 年）
- Post-implementation 群 N=1,579（隨後 1 年）
- 2-year between-group field experiment design

這是**同類研究**中規模最大的田野實驗之一（截至發表時點），在 gamification 文獻中是基準參考文獻。

**為什麼只能引用方法學規模**：本研究未能驗證 Hamari 2015 結果的方向性（positive / null / negative）。Refuted claim 列表明確指出「Hamari 顯著增加 activity」的敘事 vote 1-2 未通過。所以：

- ✅ 可以寫：「Hamari 2015 採用 2-year between-group design，樣本 N=1,410 vs. 1,579，是該領域基準研究」
- ❌ 不可以寫：「Hamari 2015 證實 badges 有效」

來源：researchgate.net/publication/271325487, semanticscholar.org

### 4.2 Duolingo 的最佳化目標

**核心論點（high confidence）**：Yancey & Settles (KDD 2020, DOI 10.1145/3394486.3403351) 公開了 Duolingo 的「Sleeping, Recovering Bandit Algorithm」——

- 200M 推播樣本
- 35 天觀察期
- Reward function 用 DAU / 2-hour lesson conversion / recurring retention 當指標

**設計意涵**：Duolingo 的最佳化函數**沒有測量 SDT、overjustification、intrinsic motivation durability**。換言之，這家市值數十億美元的教育科技公司，**在工程上把 engagement 放在比「獎勵是否真驅動學習」更優先的位置**。

這個事實對台灣 12 年國教設計的啟示：
- 教育遊戲的「商業模式」會自然傾向選擇 engagement 指標
- **如果設計目的是教育（不是 engagement）**，就必須刻意避開「只追 engagement」的設計 pattern
- 具體手段：把 SDT 三大需求寫進 design spec、刻意設計 retention metric 的反面（讓孩子在某些情境下「自然停止」）

來源：research.duolingo.com

---

## 5. 三種蒐集機制對照

設計者常用的「蒐集」有三種 pattern，各有不同的 SDT 風險：

### 5.1 類型 A：物件 / 卡片 / 生物蒐集

**設計 pattern**：孩子透過學習任務獲取虛擬物件（寶可夢、卡牌、生物圖鑑、貼紙簿），目標是「集滿一套」。

**SDT 風險**：

| 需求 | 風險 |
|------|------|
| 自主 | 高 — 如果「稀有卡」機制設計成不可預測 / 機率性 / 重複抽取，外顯 random reward 會加強控制感 |
| 勝任 | 中 — 如果取得條件與學習成就完全脫鉤（純運氣），會削弱勝任感 |
| 關聯 | 低 — 通常是正向（社交炫耀、交換、比較） |

**已知案例風險**：
- Pokemon TCG / gacha 機制 — Zendle et al. (2020, *Computers in Human Behavior*) 等研究指出 loot box 與問題賭博行為有相關性（**注意：這個引用未在本研究中驗證**，列為待補）
- Duolingo 早期版本曾有寶箱系統，後改為 gems — 設計演化顯示業界自己意識到控制性框架問題

### 5.2 類型 B：點數 / 徽章 / 成就

**設計 pattern**：孩子完成任務獲得分數、徽章、排行榜名次（ClassDojo、Khan Academy badges、Duolingo leagues）。

**SDT 風險**：

| 需求 | 風險 |
|------|------|
| 自主 | 高 — leaderboard / 強制每日登入 / streak 中斷懲罰直接 thwart autonomy |
| 勝任 | 中 — 比較機制對落後者挫敗勝任感（wikitree 顯示 conditional effect） |
| 關聯 | 中 — 社交比較可正可負，看是合作還是競爭 |

**已知案例風險**：
- Duolingo streak — 已有研究討論「streak anxiety」（**注意：未在本研究驗證**）— KDD 2020 paper 顯示 Duolingo 自己的 best practice 包含「允許合理中斷」
- ClassDojo — 教育界爭議頗多，過度將行為外顯化（行為點數）對內在動機影響的研究**未通過驗證**

### 5.3 類型 C：知識 / 技能解鎖（Mastery-based）

**設計 pattern**：孩子必須先學會某個概念才能解鎖下一關（Khan Academy mastery system、DragonBox 的關卡推進、Brilliant.org）。

**SDT 風險**：

| 需求 | 風險 |
|------|------|
| 自主 | 低 — 通常尊重孩子的自我步調 |
| 勝任 | 極低 — 直接 reward 能力的習得，最符合 SDT 資訊性獎勵框架 |
| 關聯 | 低 — 通常不依賴社交比較 |

**最佳實踐**：DragonBox（見 §6.1）的設計 — 蒐集物（龍的成長 + bonus star）與關卡完成掛鉤，**不是任意累積**。這種 **mastery-coupled 蒐集** 是三種類型中 SDT 相容性最高的。

---

## 6. 案例研究

### 6.1 DragonBox — 雙機制設計的範例

**核心論點（medium confidence）**：

DragonBox（Kahoot! 旗下代數學習遊戲）的設計——

- **內在學習機制**：卡片操作 — 玩家把生物 / 物件圖示抽象為代數變數與數字（這本身就是一個 discovery-based learning）
- **外在蒐集機制**：龍的成長 + bonus star — 疊加在關卡完成之上

**SDT 分析**：
- 卡片操作滿足 **自主**（探索） + **勝任**（概念理解）
- 龍的成長 + bonus star 是 **mastery-coupled 蒐集** — 跟學習成就掛鉤 → 屬於**資訊性獎勵**，理論上與內在動機相容

**限制**：「DragonBox 採用雙機制設計」這個事實描述來自 Wikipedia + ResearchGate；但「mastery-coupled 蒐集」這個分類是 SDT 框架的**詮釋性加層**，原始來源未直接用語。設計模式歸類合理但這是事實描述 + 詮釋的混合。

來源：en.wikipedia.org/wiki/DragonBox, researchgate.net

### 6.2 Duolingo — Controlling Framework 的工程化極致

**核心論點（high confidence）**：見 §4.2。

**SDT 風險分析**：

| 機制 | SDT 需求影響 |
|------|-------------|
| Streak（連續天數） | ⚠️ Autonomy-thwarting — 中斷懲罰讓玩家被外控驅動 |
| Leaderboards / Leagues | ⚠️ Competence-thwarting — 對落後者挫敗勝任感（**注意：conditional effect 引用未驗證**） |
| Lingots / Gems（虛擬貨幣） | ⚠️ 取決於取得條件是否 mastery-coupled |
| Family Plans | ✅ Relatedness 滿足 |
| 個人化推播（bandit algorithm） | ⚠️ Autonomy-thwarting — 系統決定「何時該回來」，削弱自我節奏 |

**對 12 年國教設計的教訓**：Duolingo 的成功證明「engagement 可以用 controlling framework 做到極致」，但**這不等於這種模式對教育目標是好的**。Duolingo 自己內部也持續調整（允許 streak freeze、推出更柔性的 leagues）。

來源：research.duolingo.com

### 6.3 其他案例（Evidence Gap，僅供設計模式參考）

以下案例**未通過驗證**，但列在這裡作為「設計 pattern 啟發」，未來需要時各自深查：

| 案例 | 設計模式 | 為什麼 evidence gap |
|------|---------|---------------------|
| **Minecraft Education** | 開放世界、無蒐集物（mod 進去才算）、可自建內容 | 「孩子後續還會不會學」長期研究未驗證 |
| **Khan Academy** | Energy points + badges + mastery progression 三層並存 | Mastery 機制的長期動機效果未驗證 |
| **ClassDojo** | 行為點數 + 家長 / 老師可見的 avatar | 教育界爭議未通過驗證 |
| **Prodigy Math** | 寶可夢式寶物 + 戰鬥 + 數學題 | 「數學學習是否真的發生」研究未驗證 |
| **Pokemon GO** | 地理 + 收集 + 社交 | 短期 engagement 與長期動機的研究未驗證 |

**設計意涵**：當有人說「Prodigy 很好用」或「Minecraft Education 孩子學很多」，要區分：
- 「孩子覺得好玩」— engagement fact
- 「孩子學到了」— learning fact
- 「孩子之後沒這個遊戲還會學」— **durability / intrinsic motivation fact**

第三項才是這個研究的核心問題，目前對大多數案例**沒有通過驗證的答案**。

---

## 7. 年齡層分層考量（Evidence Gap 重點區）

### 7.1 為什麼這段是 evidence gap

本研究中**沒有任何 claim 通過驗證**直接談「不同年齡層（6-9 / 10-12 / 13-15 歲）對三種蒐集類型的差異反應」。

被 refuted 的「兒童比成人更易受過度合理化效應影響」（vote 1-2）也不能用作根據。

### 7.2 發展心理學的**保守推論**（標示為推論、非已驗證）

基於 Piaget 認知發展階段 + SDT 對年齡的應用文獻（**推論性、未驗證**）：

| 年齡段 | 認知特性 | 蒐集設計保守建議 |
|--------|---------|----------------|
| **低年級（1-3 年級，6-9 歲）** | 具體運思前期 / 早期；自我概念萌芽；對「具體可見的獎勵」反應最強 | 以類型 C（mastery-based）為主。避免外顯稀有度（gacha 不可用）。社交炫耀效果強，要小心避免比較挫敗 |
| **中年級（4-6 年級，9-12 歲）** | 具體運思期；開始有社會比較；勝任感需求升高 | 三種類型可用，但要明確「蒐集物代表的能力 / 學習是什麼」。Mastery-coupled 仍最安全 |
| **高年級（7-9 年級，12-15 歲）** | 形式運思萌芽；抽象思考、批判能力成長；對「被操弄」敏感 | 過度遊戲化會被識破，反而傷害信任。建議大幅降低外顯蒐集，轉向個人化成長軌跡 + 同儕協作 |

**重要**：以上分齡建議是**發展心理學的保守推論**，不是已通過驗證的學術結論。設計時要把它當「出發點假設」而非「事實」，實際上線後需要 A/B test。

---

## 8. 設計原則矩陣（給設計者用）

這個矩陣把 §5 的 SDT 分析 × §7 的年齡保守推論整合：

### 8.1 該做（✅）

| 原則 | 理由 | 適用年齡 |
|------|------|---------|
| 把「蒐集物」設計為**能力可見化**（mastery-coupled） | 符合 CET 資訊性獎勵 → 增強內在動機 | 全年齡 |
| 讓玩家**自主選擇**蒐集目標 | 滿足 SDT 自主需求 | 全年齡 |
| **隨時可見的成長軌跡**（不是隱藏的） | 資訊性回饋 + 勝任感 | 全年齡 |
| 社交機制以**合作 / 分享**為主，不是比較 | Relatedness 正面 | 全年齡 |
| 允許「合理的暫停 / 中斷」 | 避免 autonomy-thwarting | 全年齡，尤其高年級 |
| 設計**個人的挑戰曲線**，不用單一排行榜 | 避免低成就者被挫敗 | 全年齡 |

### 8.2 該避免（❌）

| 反模式 | 為什麼 | 特別風險年齡 |
|--------|--------|-------------|
| 隨機抽取 / gacha 機制 | 控制性框架 + loot box 相關問題賭博行為（**注意：未驗證，列為待補**） | 中高年級 |
| 外顯稀有度顯示（SSR / SR / R） | 強化比較 + 降低自主 | 高年級特別敏感 |
| 強制每日登入獎勵 | Autonomy-thwarting | 全部 |
| Streak 中斷懲罰（移除獎勵或給負面狀態） | Autonomy-thwarting + 控制性 | 全部 |
| 公開 leaderboard（單一全平台排名） | Competence-thwarting 落後者 | 中高年級 |
| 任意累積的蒐集（與學習成就脫鉤） | 偏離 CET 資訊性獎勵 | 全年齡 |

### 8.3 不確定（⚠️ 需 A/B test）

- 多人連線 / 同儕學習
- 跨領域「集卡」（一個概念學會可以拿多領域的卡）
- AI 個人化提示（會不會被當作 autonomy-thwarting？）
- 家長可見的進度儀表板（會不會把外在壓力帶進來？）

---

## 9. 給台灣 12 年國教設計者的具體建議

### 9.1 領域 × 蒐集類型適配性（推論性矩陣）

> ⚠️ 這段沒有通過驗證的 claim。下方矩陣是基於 §5 三種類型 + §7 年齡保守推論 + 領域特性（資料層 §108 課綱）的**設計出發點假設**，上線後需要實證修正。

| 領域 | 蒐集建議 | 理由 |
|------|---------|------|
| **國語文 / 本土語文 / 英語文** | 類型 C 為主（單字 / 文法 mastery 解鎖閱讀篇章）。可以加類型 A 作為**裝飾性**鼓勵（卡牌收集）但要 mastery-coupled | 語言學習的內在動機（讀故事、會話）很容易被外顯稀有度轉移 |
| **數學** | 類型 C 為主（概念解鎖 → 下一關）。避免類型 B 的 leaderboard — 數學焦慮會被比較放大 | DragonBox / Khan Academy 的成功路徑都是 mastery 為主 |
| **自然科學 / 科技** | 類型 C（概念掌握）+ 類型 A 的「生物 / 元素蒐集」可作為**記憶錨點**（看到卡想起對應概念）。要避免抽卡機制 | 實驗操作本身就是高內在動機活動，外在獎勵要克制 |
| **社會 / 綜合活動** | 類型 C（議題理解解鎖）+ 類型 B 的合作任務徽章 | 領域本身就有高關聯性，避免比較機制 |
| **藝術 / 健康與體育** | 內在動機極高的領域。**強烈建議大幅降低蒐集機制**，改為自我表達工具（畫廊 / 動作錄影回看） | 這些領域的內在動機一旦被外在獎勵轉移，會迅速流失 |

### 9.2 跨領域設計原則

1. **蒐集物的取得必須可追溯到具體學習事件**
   - 不能是「完成 100 個任務 → 拿到 XX 卡」
   - 要是「學會『分數通分』這個概念 → 解鎖『分數勇者』卡」
2. **每個蒐集物要附一段「它代表什麼能力 / 概念」的說明**
   - 讓孩子能內化（走到 OIT 連續線右端）
3. **家長 / 老師的儀表板要 show 學習軌跡，不只是獎勵數**
   - 避免把外在壓力從社會端灌進來
4. **設計「自然結束」機制**
   - 反 Duolingo 的「always-on engagement」
   - 例如：學完一個 unit 後，有一段「消化期」，不發推送、不顯示進度
5. **不要把這份研究當作「最終答案」**
   - 這是 evidence-based 出發點，不是 SOP
   - 上線後必做 A/B test、SDT 三需求的質性訪談、long-term motivation durability 追蹤

---

## 10. 研究限制 / 後續工作

### 10.1 證據強度地圖

```
強（high confidence）
├── SDT 三大需求的普遍性
├── CET 控制性 vs. 資訊性區分
├── 內化連續線
├── Deci 1971 經典實驗
├── Hamari 2015 方法學規模
└── Duolingo KDD 2020 最佳化目標

中（medium confidence）
├── SDT 對教育遊戲設計的應用意涵
└── DragonBox 雙機制設計的事實 + 詮釋

弱 / Evidence gap
├── 年齡層差異反應（1-3 / 4-6 / 7-9 年級）
├── Hamari 2015 結果方向（positive / null / negative）
├── 108 課綱九大領域 × 蒐集類型矩陣
├── Minecraft Education / ClassDojo / 寶可夢 / Prodigy 長期效應
└── Loot box / gacha 對兒童的具體影響（Zendle 2020 等引用未驗證）
```

### 10.2 後續研究項目（建議）

1. **年齡層差異實證**：找 SDT × 兒童發展心理學的交叉文獻（Reeve 長期縱貫研究？Deci 在學校情境的應用？）補 §7
2. **台灣在地兒童實證**：108 課綱領域對應的學習動機 baseline 調查（目前沒有公開資料）
3. **Hamari 結果方向**：直接讀 DOI 10.1016/j.chb.2014.10.051 paper 確認結果（這個研究沒驗證成是因為搜尋 agent 沒抓到 abstract 細節）
4. **長期 durability 研究**：找 Hanus & Fox (2015) 等「過度合理化效應在教育科技的長期追蹤」文獻
5. **Loot box 對兒童研究**：Zendle et al. 系列（已發表但本研究沒驗證引用）

### 10.3 這個專案的後續 Phase 銜接

```
P1 課綱 ✅  →  P2 部編本  →  P3 知識圖譜  →  P4 遊戲端介面  →  P5 開放資料
                                              ↑
                                              本檔作為 P4 的設計依據
                                              設計時回頭讀 §8 矩陣 + §9 領域建議
                                              任何設計決策衝突 → 回到 §1.1 / 1.2 / 1.3 看證據強度
```

---

## 11. 引用

### 11.1 通過驗證的引用（用得到）

- Deci, E. L. (1971). Effects of externally mediated rewards on intrinsic motivation. *Journal of Personality and Social Psychology*, 18(1), 105-115.
- Deci, E. L., & Ryan, R. M. (1985). *Intrinsic motivation and self-determination in human behavior*. Plenum.
- Ryan, R. M., & Deci, E. L. (2000). Self-determination theory and the facilitation of intrinsic motivation, social development, and well-being. *American Psychologist*, 55(1), 68-78.
- Ryan, R. M., & Deci, E. L. (2000). Intrinsic and extrinsic motivations: Classic definitions and new directions. *Contemporary Educational Psychology*, 25(1), 54-67.
- Vansteenkiste, M., Ryan, R. M., & Soenens, B. (2020). Basic psychological need theory: Advancements, critical revisions, and future directions.
- Murayama, K., Matsumoto, T., & Matsumoto, K. (2010). The effect of extrinsic reward on intrinsic motivation: A meta-analysis.
- Hamari, J., Koivisto, J., & Sarsa, H. (2014). Does gamification work? — A literature review of empirical studies on gamification. *HICSS 47*.
- Hamari, J. (2015). Do badges increase user activity? A field experiment on the effects of gamification. *Computers in Human Behavior*. DOI: 10.1016/j.chb.2014.10.051
- Yancey, K., & Settles, B. (2020). The Sleeping, Recovering Bandit Algorithm. KDD '20. DOI: 10.1145/3394486.3403351
- Markant, D. B., Settles, B., & Gureckis, T. M. (2016). Self-directed learning favors local, rather than global, uncertainty. *Cognitive Science*.

### 11.2 重要但本研究未驗證的引用（待補）

- Lepper, M. R., Greene, D., & Nisbett, R. E. (1973). Undermining children's intrinsic interest with extrinsic rewards: A test of the overjustification hypothesis. *Journal of Personality and Social Psychology*.
- Eisenberger, R., & Cameron, J. (1996). Detrimental effects of reward: Reality or myth?
- Cameron, J., Banko, K. M., & Pierce, W. D. (2001). Pervasive negative effects of rewards on intrinsic motivation.
- Hanus, M. D., & Fox, J. (2015). Assessing the effects of gamification in the classroom.
- Sailer, M., & Homner, L. (2020). The Gamification of Teaching and Learning: a Meta-analysis.
- Zendle, D., et al. (2020). Loot boxes and problem gambling.
- Rigby, S., & Ryan, R. M. *Glued to Games*.

**這些文獻在 §X.X 中如果出現，必須明確標註「未驗證引用」並降級為建議性引用，不可當作已驗證事實。**

---

## 12. 版本與維護

- **建立**：2026-06-23
- **方法**：deep-research workflow（5 angles, 15 sources, 39 claims, 25 verified, 8 confirmed, 15 refuted, 4 evidence gaps）
- **維護者**：Hangsau
- **下次 review 觸發點**：
  - 任何遊戲端 design spec 要引用本檔時
  - 補上 §7 年齡層 / §6.3 其他案例的證據後
  - 108 課綱修訂時
- **本檔使用約定**：
  - 標 ✅ 的設計建議 → 可直接採納
  - 標 ⚠️ 的 → 需要 A/B test 驗證
  - 標 ❌ 的 → 設計 spec 不應採用
  - evidence gap 區段 → 必須先補研究再決策

---

*最後更新：2026-06-23 — 整合 deep-research 結果，由 Hangsau 維護。*
