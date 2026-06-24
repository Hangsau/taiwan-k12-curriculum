#!/usr/bin/env python3
"""
analyze_exams.py — §16-H：分析已抓試題，反推高頻知識點 + 對應 curriculum codes。

策略：
1. 讀 exams/text/*.txt（pdftotext 轉好的）
2. 用 curriculum/<domain>/<stem>.structured.json 的 codes 當關鍵字
3. 統計每個 code 在試題中出現頻率
4. 輸出 reports/high-frequency-knowledge-points.md

用途：
- 從 163 個高中試題反推「國中 / 國小必學知識點」
- 給教材編排優先順序（高頻 = 必教）
- 給 LLM 自編國小教材的 seed data
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
EXAMS_TEXT = ROOT / "exams" / "text"
CURRICULUM = ROOT / "curriculum"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

# 學科關鍵字 → domain mapping
SUBJECT_TO_DOMAIN = {
    "數學": ["數學"],
    "英文": ["英語文"],
    "國文": ["國語文"],
    "國綜": ["國語文"],
    "國寫": ["國語文"],
    "社會": ["社會"],
    "歷史": ["社會"],
    "地理": ["社會"],
    "公民": ["社會"],
    "自然": ["自然科學"],
    "理化": ["自然科學"],
    "物理": ["自然科學"],
    "化學": ["自然科學"],
    "生物": ["自然科學"],
    "地科": ["自然科學"],
    "地球科學": ["自然科學"],
}


def log(msg: str):
    print(msg, flush=True)


def get_codes_by_domain() -> dict[str, list[dict]]:
    """從 curriculum/ 讀所有 structured.json，回傳 {domain: [code_obj]}。"""
    by_domain = defaultdict(list)
    for sj_path in CURRICULUM.rglob("*.structured.json"):
        try:
            d = json.loads(sj_path.read_text(encoding="utf-8"))
            domain = d.get("domain", "")
            for code in d.get("performance_codes", []) + d.get("content_codes", []):
                if "code" in code:
                    by_domain[domain].append({
                        "code": code["code"],
                        "stage": code.get("stage", ""),
                        "category": code.get("category", ""),
                        "source_file": str(sj_path.relative_to(ROOT)),
                    })
        except Exception as e:
            log(f"  ERR {sj_path}: {e}")
    return dict(by_domain)


def classify_exam_to_domain(fname: str) -> str | None:
    """從 exam 檔名判斷對應 domain。例 '115-數學a.txt' → 數學。"""
    base = fname.replace(".txt", "")
    # 移除前綴學年
    parts = re.split(r"[-_]", base)
    if len(parts) >= 2:
        subj_part = parts[1].lower()
    else:
        subj_part = base.lower()
    # 學科判斷
    if "數學" in subj_part or "math" in subj_part:
        return "數學"
    if "英文" in subj_part or "english" in subj_part or "eng" in subj_part:
        return "英語文"
    if "國文" in subj_part or "國綜" in subj_part or "國寫" in subj_part or "chinese" in subj_part:
        return "國語文"
    if "社會" in subj_part or "歷史" in subj_part or "地理" in subj_part or "公民" in subj_part:
        return "社會"
    if "自然" in subj_part or "理化" in subj_part or "物理" in subj_part or "化學" in subj_part or "生物" in subj_part or "地科" in subj_part:
        return "自然科學"
    return None


def analyze_exam_file(text_path: Path, domain_codes: list[dict]) -> dict:
    """分析一個試題 txt，統計每個 curriculum code 出現次數。"""
    text = text_path.read_text(encoding="utf-8", errors="replace")
    counts = Counter()
    # 每個 code 算出現次數（regex 找完整 code token）
    for c in domain_codes:
        # 完整匹配（如 "n-Ⅰ-2"、"E-Ⅱ-1"），用 word boundary
        pattern = re.escape(c["code"])
        n = len(re.findall(pattern, text))
        if n > 0:
            counts[c["code"]] = n
    return dict(counts)


def main():
    log("=== analyze_exams.py ===")
    log(f"讀取 exam text: {EXAMS_TEXT}")
    log(f"讀取 curriculum: {CURRICULUM}")

    codes_by_domain = get_codes_by_domain()
    log(f"各領域 codes 統計:")
    for d, cs in codes_by_domain.items():
        log(f"  {d}: {len(cs)} codes")

    if not EXAMS_TEXT.exists():
        log(f"  ERR: {EXAMS_TEXT} 不存在")
        return

    text_files = list(EXAMS_TEXT.glob("*.txt"))
    log(f"\n讀取 {len(text_files)} 個 exam text")

    # 全域統計
    global_counts = Counter()
    by_domain_counts = defaultdict(Counter)
    by_exam = {}

    for tf in text_files:
        domain = classify_exam_to_domain(tf.name)
        if not domain or domain not in codes_by_domain:
            continue
        codes = codes_by_domain[domain]
        counts = analyze_exam_file(tf, codes)
        by_exam[tf.name] = {"domain": domain, "counts": counts}
        for c, n in counts.items():
            global_counts[c] += n
            by_domain_counts[domain][c] += n

    log(f"\n=== 高頻 curriculum codes 出現次數 ===")
    # 全部
    log(f"全領域 top 30:")
    for code, n in global_counts.most_common(30):
        # 找 code 屬於哪個 domain
        domain = None
        for d, cs in codes_by_domain.items():
            if any(c["code"] == code for c in cs):
                domain = d
                break
        log(f"  {code:20} {n:>5} 次 ({domain})")

    # 各領域 top 10
    for domain in ["數學", "英語文", "國語文", "社會", "自然科學"]:
        if domain not in by_domain_counts:
            continue
        log(f"\n{domain} top 10:")
        for code, n in by_domain_counts[domain].most_common(10):
            log(f"  {code:20} {n:>5} 次")

    # 寫報告
    report_path = REPORTS / "high-frequency-knowledge-points.md"
    lines = [
        "# 高頻知識點分析報告（§16-H）",
        "",
        f"> 從 {len(text_files)} 個大考中心試題純文字（108-115 學年）反推",
        f"> curriculum codes 出現頻率 → 識別「高頻知識點」",
        f"> 用途：給教材編排優先順序 + LLM 自編國小教材 seed data",
        "",
        "## 0. 方法",
        "",
        "- 讀 exams/text/*.txt（pdftotext 轉好的高中試題純文字）",
        "- 對每個檔案，從檔名判斷對應領域（數學/英語文/國語文/社會/自然科學）",
        "- 用 curriculum/<domain>/*.structured.json 的 codes（learning content + learning performance）當關鍵字",
        "- 統計每個 code 在所有試題中的總出現次數",
        "- 出現次數高 = 高中反覆考的知識點 = 國中/國小必學基礎",
        "",
        "## 1. 全領域 Top 30（最高頻 curriculum codes）",
        "",
        "| 次數 | Code | 領域 |",
        "|------|------|------|",
    ]
    for code, n in global_counts.most_common(30):
        domain = ""
        for d, cs in codes_by_domain.items():
            if any(c["code"] == code for c in cs):
                domain = d
                break
        lines.append(f"| {n} | `{code}` | {domain} |")

    for domain in ["數學", "英語文", "國語文", "社會", "自然科學"]:
        if domain not in by_domain_counts:
            continue
        lines.append("")
        lines.append(f"## 2. {domain} Top 10")
        lines.append("")
        lines.append("| 次數 | Code |")
        lines.append("|------|------|")
        for code, n in by_domain_counts[domain].most_common(10):
            lines.append(f"| {n} | `{code}` |")

    lines.extend([
        "",
        "## 3. 給教材編排的建議",
        "",
        "- **高頻 codes** 是高中反覆考的「必備基礎」 → 國中/國小教材**必教**",
        "- 對照 curriculum 的 stage（I-V）反推：",
        "  - 高中（V）考的 code → 國中（IV）必教",
        "  - 國中考的 code → 國小（III）必教",
        "- 教材章節順序可依 code 出現頻率排：高頻先教",
        "",
        "## 4. 給 LLM 自編國小教材的 seed",
        "",
        "每個高頻 code 對應的 raw_section_5 文字可當 LLM prompt：",
        "「用以下課綱描述（raw_section_5）+ 高中試題真實題目，生成國小 X 年級教材」",
        "",
        f"---",
        f"分析時間：{__import__('datetime').datetime.now().isoformat()}",
        f"考卷總數：{len(text_files)}",
        f"對齊 codes 總數：{len(global_counts)}",
    ])

    report_path.write_text("\n".join(lines), encoding="utf-8")
    log(f"\n報告寫到 {report_path.relative_to(ROOT)}")

    # 寫 JSON 給程式讀
    json_path = REPORTS / "high-frequency-knowledge-points.json"
    json_path.write_text(json.dumps({
        "global": dict(global_counts),
        "by_domain": {d: dict(c) for d, c in by_domain_counts.items()},
        "by_exam": by_exam,
        "total_exams": len(text_files),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"JSON 寫到 {json_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
