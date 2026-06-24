#!/usr/bin/env python3
"""
index_exams.py — 掃所有考卷，產出分類 INDEX.md（按來源/學年/學科分類）。

不動檔案結構，只生成索引文檔給人類快速找考卷用。

分類維度：
1. 來源 (source): CEEC / melances / ddes / studyark / ...
2. 學段 (stage): 國小 / 國中 / 高中 / 不明
3. 學年 (year): 學年或學年度
4. 學科 (subject): 國文 / 英文 / 數學 / ...

產出：
- exams/INDEX.md（人類可讀，分類表）
- exams/INDEX.json（機器可讀，完整 metadata）
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))
ROOT = Path(__file__).parent.parent
EXAMS = ROOT / "exams"


def log(msg: str):
    print(msg, flush=True)

# 領域關鍵字 → 學科
SUBJECT_KEYWORDS = {
    "國文": ["國文", "國綜", "國寫", "國語", "chinese"],
    "英文": ["英文", "英語", "eng"],
    "數學": ["數學", "數甲", "數乙", "數a", "數b", "math"],
    "社會": ["社會", "歷史", "地理", "公民", "social"],
    "自然科學": ["自然", "理化", "物理", "化學", "生物", "地科", "地球科學", "science"],
    "社會(分科)": ["分科", "歷", "地", "公"],
    "自然(分科)": ["物", "化", "生", "地科"],
}

# 學段判斷
STAGE_PATTERNS = {
    "國小": ["grade1", "grade2", "grade3", "grade4", "grade5", "grade6",
             "國小1", "國小2", "國小3", "國小4", "國小5", "國小6",
             "國小一年級", "國小二年級", "國小三年級", "國小四年級", "國小五年級", "國小六年級",
             "國小一", "國小二", "國小三", "國小四", "國小五", "國小六",
             "一年級", "二年級", "三年級", "四年級", "五年級", "六年級",
             "上學期", "下學期", "期中考", "期末考"],
    "國中": ["grade7", "grade8", "grade9",
             "國中7", "國中8", "國中9",
             "國中七年級", "國中八年級", "國中九年級",
             "七年級", "八年級", "九年級"],
    "高中": ["學測", "分科", "指考", "GSAT", "grade10"],
}

# 來源
SOURCE_PATTERNS = {
    "米蘭老師 Drive": lambda f: "melances" in str(f),
    "大墩國小 ddes.tc.edu.tw": lambda f: "ddes" in str(f),
    "學習方舟 studyark.org": lambda f: "studyark" in str(f),
    # CEEC：檔名格式「{yy}-{學科}.pdf/docx」位於 exams/ 直下（不是子目錄）
    "CEEC 大考中心（高中試題）": lambda f: (
        f.parent.name == "exams"  # 直接在 exams/ 下
        and re.match(r"^\d{2,3}[-_].+\.(pdf|docx)$", f.name) is not None
        and "text" not in f.name
    ),
    "CEEC 純文字 (pdftotext 轉檔)": lambda f: "text" in str(f) and f.suffix == ".txt",
}


def classify_file(path: Path) -> dict:
    """分類一個考卷檔案：年級、科目、版本、考試類型。"""
    name = path.name
    rel = str(path.relative_to(ROOT))
    size = path.stat().st_size if path.exists() else 0
    ext = path.suffix.lower().lstrip(".")

    # 來源（必須在學段判斷前，因為學段判斷依賴 source）
    source = "其他"
    for src_name, matcher in SOURCE_PATTERNS.items():
        try:
            if matcher(path):
                source = src_name
                break
        except Exception:
            pass

    # ===== 學段 =====
    stage = None
    grade = None
    rel_lower = rel.lower()

    # CEEC = 高中（固定）
    if source == "CEEC 大考中心（高中試題）":
        stage = "高中"
        grade = "高中"  # 高中不分年級（混合多年級）
    else:
        # 米蘭老師：從路徑 gradeN 拿
        gm = re.search(r"grade(\d+)", rel_lower)
        if gm:
            gn = int(gm.group(1))
            if 1 <= gn <= 6:
                stage = "國小"
                grade = f"國小 {gn} 年級"
            elif 7 <= gn <= 9:
                stage = "國中"
                grade = f"國中 {gn - 6} 年級"
            elif gn == 10:
                stage = "高中"
                grade = "高中 1 年級"  # grade10 約略對應高中
        # Fallback：從檔名/路徑其他關鍵字
        if stage is None:
            for st, patterns in STAGE_PATTERNS.items():
                if any(p in rel_lower for p in patterns):
                    stage = st
                    break

    # ===== 學年（西元）=====
    year_m = re.match(r"^(\d{2,3})[-_]", name)
    year_roc = year_m.group(1) if year_m else None

    # ===== 學科（更精準解析）=====
    subject = None
    # 米蘭老師檔名格式：「國語1上」或「數學3下」等
    # 第一個字/詞通常就是科目
    subject_patterns = [
        ("國文", ["國文", "國語", "國綜", "國寫"]),
        ("英文", ["英文", "英語", "english"]),
        ("數學", ["數學", "數甲", "數乙", "數a", "數b"]),
        ("自然科學", ["自然", "理化", "物理", "化學", "生物", "地科", "地球科學"]),
        ("社會", ["社會", "歷史", "地理", "公民", "史", "地", "公"]),
        ("生活", ["生活"]),
        ("健康與體育", ["健康", "體育", "健體"]),
    ]
    name_for_subj = name  # 保留原始大小寫（中文）
    for subj, kws in subject_patterns:
        if any(kw in name_for_subj for kw in kws):
            subject = subj
            break

    # 學期（上/下）
    semester = None
    if "上學期" in rel or "上學期" in name:
        semester = "上學期"
    elif "下學期" in rel or "下學期" in name:
        semester = "下學期"

    # 考試類型
    test_type = None
    if "期中考" in rel or "期中考" in name:
        test_type = "期中考"
    elif "期末考" in rel or "期末考" in name:
        test_type = "期末考"
    elif "段考" in rel or "段考" in name:
        test_type = "段考"
    elif "第一次" in name or "1st" in name.lower():
        test_type = "第一次段考"
    elif "第二次" in name or "2nd" in name.lower():
        test_type = "第二次段考"
    elif "第三次" in name or "3rd" in name.lower():
        test_type = "第三次段考"

    # 教科書版本
    version = None
    version_kws = ["南一", "康軒", "翰林", "何嘉仁", "龍騰", "泰宇", "全華", "五南", "旗立", "佳音"]
    for v in version_kws:
        if v in name:
            version = v
            break

    # 校名
    school = None
    school_m = re.search(r"(市立[一-鿿]{1,5}(?:國小|國中|高中))", name)
    if not school_m:
        school_m = re.search(r"([一-鿿]{2,5}(?:國小|國中|高中))", name)
    if school_m:
        school = school_m.group(1)

    return {
        "path": rel,
        "filename": name,
        "size": size,
        "ext": ext,
        "year_roc": year_roc,
        "stage": stage,
        "grade": grade,
        "subject": subject,
        "version": version,
        "test_type": test_type,
        "semester": semester,
        "source": source,
        "school": school,
    }


def main():
    parser = argparse.ArgumentParser(description="§16-K：考卷分類 INDEX")
    parser.add_argument("--no-write", action="store_true", help="不寫檔，只印統計")
    args = parser.parse_args()

    if not EXAMS.exists():
        log(f"  ERR: {EXAMS} 不存在")
        return

    # 掃所有 PDF / DOCX / PPTX
    all_files = []
    for ext in ["pdf", "docx", "pptx"]:
        all_files.extend(EXAMS.rglob(f"*.{ext}"))

    log(f"=== index_exams.py ===")
    log(f"掃到 {len(all_files)} 個考卷檔案\n")

    classifications = [classify_file(f) for f in all_files]

    # 統計
    by_source = defaultdict(list)
    by_stage = defaultdict(list)
    by_grade = defaultdict(list)
    by_year = defaultdict(list)
    by_subject = defaultdict(list)
    for c in classifications:
        by_source[c["source"]].append(c)
        if c["stage"]:
            by_stage[c["stage"]].append(c)
        if c["grade"]:
            by_grade[c["grade"]].append(c)
        if c["year_roc"]:
            by_year[c["year_roc"]].append(c)
        if c["subject"]:
            by_subject[c["subject"]].append(c)

    log(f"按來源分：")
    for src, items in sorted(by_source.items(), key=lambda x: -len(x[1])):
        log(f"  {src:30} {len(items):>4} 個")
    log(f"\n按學段分：")
    for st, items in sorted(by_stage.items(), key=lambda x: -len(x[1])):
        log(f"  {st:10} {len(items):>4} 個")
    log(f"\n按年級分 (國小/國中)：")
    for gr in sorted(by_grade.keys()):
        log(f"  {gr:15} {len(by_grade[gr]):>4} 個")
    log(f"\n按學年分 (top 10)：")
    for yr, items in sorted(by_year.items())[-10:]:
        log(f"  {yr:10} {len(items):>4} 個")
    log(f"\n按學科分：")
    for subj, items in sorted(by_subject.items(), key=lambda x: -len(x[1])):
        log(f"  {subj:15} {len(items):>4} 個")

    # 寫 JSON
    json_path = EXAMS / "INDEX.json"
    json_path.write_text(json.dumps({
        "generated_at": datetime.now(TZ).isoformat(),
        "total": len(classifications),
        "by_source": {k: len(v) for k, v in by_source.items()},
        "by_stage": {k: len(v) for k, v in by_stage.items()},
        "by_year": {k: len(v) for k, v in by_year.items()},
        "by_subject": {k: len(v) for k, v in by_subject.items()},
        "files": classifications,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"\nJSON 寫到 {json_path.relative_to(ROOT)}")

    # 寫 INDEX.md（分類表）
    md_lines = [
        "# 考卷分類索引",
        "",
        f"> 自動產生：{datetime.now(TZ).isoformat()}",
        f"> 總考卷：{len(classifications)} 個檔案",
        f"> 來源：CEEC 大考中心（高中試題）+ 米蘭老師 Drive（國小/國中/高中段考）",
        "",
        "## 1. 按來源分",
        "",
        "| 來源 | 數量 |",
        "|------|------|",
    ]
    for src, items in sorted(by_source.items(), key=lambda x: -len(x[1])):
        md_lines.append(f"| {src} | {len(items)} |")

    md_lines.extend([
        "",
        "## 2. 按學段分",
        "",
        "| 學段 | 數量 |",
        "|------|------|",
    ])
    for st, items in sorted(by_stage.items(), key=lambda x: -len(x[1])):
        md_lines.append(f"| {st} | {len(items)} |")

    md_lines.extend([
        "",
        "## 3. 按學年分（依西元）",
        "",
        "| 學年 | 數量 |",
        "|------|------|",
    ])
    for yr in sorted(by_year.keys()):
        md_lines.append(f"| {yr}（{int(yr)+1911}） | {len(by_year[yr])} |")

    md_lines.extend([
        "",
        "## 4. 按學科分",
        "",
        "| 學科 | 數量 |",
        "|------|------|",
    ])
    for subj, items in sorted(by_subject.items(), key=lambda x: -len(x[1])):
        md_lines.append(f"| {subj} | {len(items)} |")

    md_lines.extend([
        "",
        "## 5. CEEC 高中試題詳細清單（按學年）",
        "",
    ])
    ceec_items = by_source.get("CEEC 大考中心（高中試題）", [])
    if ceec_items:
        # 按學年分組
        ceec_by_year = defaultdict(list)
        for c in ceec_items:
            y = c["year_roc"] or "未明"
            ceec_by_year[y].append(c)
        for yr in sorted(ceec_by_year.keys()):
            md_lines.append(f"### {yr} 學年度")
            md_lines.append("")
            md_lines.append("| 檔名 | 大小 | 學科 |")
            md_lines.append("|------|------|------|")
            for c in sorted(ceec_by_year[yr], key=lambda x: x["filename"]):
                size_kb = c["size"] / 1024
                md_lines.append(f"| `{c['filename']}` | {size_kb:.1f} KB | {c['subject'] or '?'} |")
            md_lines.append("")

    md_lines.extend([
        "## 6. 米蘭老師 Drive 段考考古題（按年級 → 科目 → 版本）",
        "",
    ])
    mel_items = by_source.get("米蘭老師 Drive", [])
    if mel_items:
        # 按年級 → 科目 → 版本分組
        mel_by_grade = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for c in mel_items:
            y = "未明"
            gm = re.search(r"grade(\d+)", c["path"])
            if gm:
                gn = int(gm.group(1))
                if 1 <= gn <= 6:
                    y = f"國小 {gn} 年級"
                elif 7 <= gn <= 9:
                    y = f"國中 {gn - 6} 年級"
                elif gn == 10:
                    y = "高中"
            subj = c["subject"] or "未分類"
            ver = c["version"] or "未標示"
            mel_by_grade[y][subj][ver].append(c)

        for y in sorted(mel_by_grade.keys()):
            md_lines.append(f"### {y}")
            md_lines.append("")
            md_lines.append("| 科目 | 版本 | 考試類型/學期 | 數量 |")
            md_lines.append("|------|------|---------------|------|")
            for subj in sorted(mel_by_grade[y].keys()):
                for ver in sorted(mel_by_grade[y][subj].keys()):
                    items = mel_by_grade[y][subj][ver]
                    by_test = defaultdict(list)
                    for it in items:
                        tt = it["test_type"] or "?"
                        sm = it["semester"] or "?"
                        by_test[(tt, sm)].append(it)
                    test_summary = ", ".join(
                        f"{tt}{sm}×{len(its)}"
                        for (tt, sm), its in sorted(by_test.items())
                    )
                    md_lines.append(f"| {subj} | {ver} | {test_summary} | {len(items)} |")
            md_lines.append("")

        # 詳細每個檔案
        md_lines.append("### 詳細清單（按年級）")
        md_lines.append("")
        for y in sorted(mel_by_grade.keys()):
            md_lines.append(f"#### {y}")
            md_lines.append("")
            md_lines.append("| 檔名 | 科目 | 版本 | 考試 | 學期 | 學校 | 大小 |")
            md_lines.append("|------|------|------|------|------|------|------|")
            for subj in sorted(mel_by_grade[y].keys()):
                for ver in sorted(mel_by_grade[y][subj].keys()):
                    for c in sorted(mel_by_grade[y][subj][ver], key=lambda x: x["filename"]):
                        size_kb = c["size"] / 1024
                        md_lines.append(
                            f"| `{c['filename'][:45]}` | {subj} | {ver} | "
                            f"{c['test_type'] or '?'} | {c['semester'] or '?'} | "
                            f"{c['school'] or '?'} | {size_kb:.0f} KB |"
                        )
            md_lines.append("")

    md_lines.extend([
        "---",
        "",
        "*此索引由 `scripts/index_exams.py` 自動產生。檔案結構未動，僅建立分類 metadata。*",
    ])

    md_path = EXAMS / "INDEX.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    log(f"INDEX.md 寫到 {md_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
