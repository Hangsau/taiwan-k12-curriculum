# 高頻知識點分析報告（§16-H）

> 從 82 個大考中心試題純文字（108-115 學年）反推
> curriculum codes 出現頻率 → 識別「高頻知識點」
> 用途：給教材編排優先順序 + LLM 自編國小教材 seed data

## 0. 方法

- 讀 exams/text/*.txt（pdftotext 轉好的高中試題純文字）
- 對每個檔案，從檔名判斷對應領域（數學/英語文/國語文/社會/自然科學）
- 用 curriculum/<domain>/*.structured.json 的 codes（learning content + learning performance）當關鍵字
- 統計每個 code 在所有試題中的總出現次數
- 出現次數高 = 高中反覆考的知識點 = 國中/國小必學基礎

## 1. 全領域 Top 30（最高頻 curriculum codes）

| 次數 | Code | 領域 |
|------|------|------|

## 3. 給教材編排的建議

- **高頻 codes** 是高中反覆考的「必備基礎」 → 國中/國小教材**必教**
- 對照 curriculum 的 stage（I-V）反推：
  - 高中（V）考的 code → 國中（IV）必教
  - 國中考的 code → 國小（III）必教
- 教材章節順序可依 code 出現頻率排：高頻先教

## 4. 給 LLM 自編國小教材的 seed

每個高頻 code 對應的 raw_section_5 文字可當 LLM prompt：
「用以下課綱描述（raw_section_5）+ 高中試題真實題目，生成國小 X 年級教材」

---
分析時間：2026-06-24T08:51:29.466233
考卷總數：82
對齊 codes 總數：0