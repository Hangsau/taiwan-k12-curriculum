#!/usr/bin/env python3
"""
parse_curriculum.py — 把 curriculum/<domain>/*.md 純文字轉成結構化 JSON。

每個 markdown 對應一個 structured.json（同目錄下）。同時更新 per-domain _index.md
（加 structured.json link）與 aggregate curriculum/_index.json（加 structured 欄位）。

Schema 設計為單一 universal，含三種變體：
  - Type A (17 領域)：一、學習表現 + 二、學習內容 連續展開，階段寫在編碼
  - Type B (2 領域：自然科學、社會)：依教育階段切子小節
  - Type none (1 領域：總綱)：無學習表現/學習內容編碼

Parsing 哲學：
  - 「lightweight + raw preserved」— 不解析表格欄位（pdftotext 抽出常壞）
  - raw_section_5 完整保留給下游重 parse
  - best-effort 抓對應表（related_codes），抓不到就空，不擋

Usage:
  python3 scripts/parse_curriculum.py                # 跑全部 20 領域
  python3 scripts/parse_curriculum.py --dry-run      # 不寫檔，只印 stats
  python3 scripts/parse_curriculum.py 數學 自然科學   # 只跑指定領域
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent  # taiwan-k12-curriculum/
CURRICULUM = ROOT / "curriculum"
SCHEMA_VERSION = "1.0"

# 時區固定 +08:00 (Asia/Taipei)
TZ = timezone(timedelta(hours=8))

# 羅馬數字正規化（full-width → half-width, Arabic → Roman）
ROMAN_MAP = {
    "Ⅰ": "I", "Ⅱ": "II", "Ⅲ": "III", "Ⅳ": "IV", "Ⅴ": "V",
    "I": "I", "II": "II", "III": "III", "IV": "IV", "V": "V",
    "1": "I", "2": "II", "3": "III", "4": "IV", "5": "V",
}

# 編碼偵測 regex（單一通用，prefix 區分 perf / cont）
# 群組：(full_code, prefix, stage_raw, ordinal)
# prefix 形態：
#   - perf: 1-3 個小寫字母 (n, ti) / 數字 + 可選小寫 (1, 1a, 2b)
#   - cont: 1-3 個大寫+小寫混 (Ab, INa, POc) / 中文 prefix (歷Aa, 地Ba)
# 注意：social / science 有「歷Aa-IV-1」這種 subject + 主題混合 prefix，需允許中文
ALL_CODE_RE = re.compile(
    r"(?<![A-Za-z0-9])"
    r"((?:[一-鿿]{0,2}([a-z]{1,3}|\d[a-z]?|[A-Z][A-Z]?[a-z]?)|([A-Z][a-z]?))-"
    r"(Ⅰ|Ⅱ|Ⅲ|Ⅳ|Ⅴ|I{1,3}|IV|V{1,3}|[1-5])-"
    r"(\d+))"
)

# 數學內容專用：N-1-1 (uppercase + Arabic stage 1-5)
MATH_CONT_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z])-([1-5])-(\d+)(?![A-Za-z0-9])")

# 階段標題 regex（Type B 用）
STAGE_HEADING_RE = re.compile(
    r"^[ \t]*(?:[一二三四五六七八九十]、)?\s*"
    r"(國民小學(?:教育階段)?|國民中學(?:教育階段)?(?:及普通型高級中等學校)?(?:必修課程)?|"
    r"普通型(?:高級中等學校)?(?:必修課程)?(?:加深加廣選修(?:課程)?)?)\s*$",
    re.MULTILINE,
)

# Section 5 開頭（總綱變體）。注意：
#   - 目次裡的「伍、學習重點 ............. 6」要排除（後面跟 dot leader）
#   - pdftotext 抽出的真 section 5 heading 前面可能帶 form feed (\f) 或空白
#   - 有些檔在 `、` 與 `學習` 之間有空白（pdftotext 排版變體）
# 用 negative lookahead 排除 dot leader；允許中間空白
SECTION_5_PATTERNS = [
    re.compile(r"(?:^|\n)[\f \t]*伍、[ \t　]*學習重點(?![ \t]*\.{3,})"),
    re.compile(r"(?:^|\n)[\f \t]*伍、[ \t　]*學習階段(?![ \t]*\.{3,})"),
]

# Section 5 結尾（同樣要排除目次）
SECTION_5_END = re.compile(r"(?:^|\n)[\f \t]*陸、[ \t　]*(?:實施要點)?(?![ \t]*\.{3,})")


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def parse_frontmatter(md_text: str) -> dict:
    """簡單 regex 抓 YAML frontmatter（不依賴 PyYAML）。"""
    m = re.match(r"^---\n(.+?)\n---\n", md_text, re.DOTALL)
    if not m:
        return {}
    fm_text = m.group(1)
    fm = {}
    for line in fm_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # title: "..."  / key: value  / tags: [a, "b"]
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        # 去掉引號
        if (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            val = val[1:-1]
        # tags list
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1]
            val = [v.strip().strip('"').strip("'") for v in inner.split(",") if v.strip()]
        fm[key] = val
    return fm


def extract_section_5(md_text: str) -> tuple[str, str]:
    """
    抽出 section 5 內容（伍、學習重點 ... 陸、）。
    回傳 (section_title, raw_text)。
    """
    # 找開頭
    title = None
    start = None
    for pat in SECTION_5_PATTERNS:
        m = pat.search(md_text)
        if m:
            title = m.group(0)
            start = m.end()
            break
    if start is None:
        return "", ""

    # 找結尾
    end_m = SECTION_5_END.search(md_text, start)
    end = end_m.start() if end_m else len(md_text)

    return title, md_text[start:end].strip()


def detect_structure_type(section_5_text: str) -> str:
    """
    偵測結構類型。
    Type B 特徵：section 5 內有「國民小學教育階段」「國民中學教育階段」等明顯子節標題
                  且這些是 ## 級或一、級（不是「依學習階段排序」這種說明文字）
    """
    # 粗略啟發：有「國民小學教育階段」+「國民中學教育階段」同時出現，且
    # 第二個不是「（一）國民小學」這種小節編號，而是真的大節
    if STAGE_HEADING_RE.search(section_5_text):
        # 統計 stage heading 出現次數
        headings = STAGE_HEADING_RE.findall(section_5_text)
        # 自然科學：國小 / 國中 / 高中必修 / 高中選修 (4 個)
        # 社會：國小 / 國中及高中必修 / 高中選修 (3 個)
        # 數學雖然也提「第一學習階段」但不命中這個 regex
        if len(headings) >= 2:
            return "B"
    return "A"


def split_type_b_by_stage(section_5_text: str) -> list[dict]:
    """Type B：依 stage heading 切段。"""
    matches = list(STAGE_HEADING_RE.finditer(section_5_text))
    if not matches:
        return [{"stage_label": "all", "raw": section_5_text}]

    stages = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(section_5_text)
        # heading line 本身
        line_start = section_5_text.rfind("\n", 0, start) + 1
        line_end = section_5_text.find("\n", start)
        if line_end == -1:
            line_end = len(section_5_text)
        stages.append({
            "stage_label": m.group(1),
            "raw": section_5_text[line_start:end],
        })
    return stages


def normalize_stage(raw: str) -> str:
    """正規化階段標記為 I/II/III/IV/V enum。"""
    return ROMAN_MAP.get(raw, raw)


def parse_code(code: str, prefix: str, stage_raw: str, ordinal: str) -> dict:
    """把 regex match 拆解為結構化 code object。"""
    code_format = "numeric_phase" if stage_raw in ("1", "2", "3", "4", "5") else "roman_phase"
    return {
        "code": code,
        "stage": normalize_stage(stage_raw),
        "category": prefix,
        "ordinal": int(ordinal),
        "code_format": code_format,
    }


def extract_codes(section_text: str, is_math: bool = False) -> tuple[list[dict], list[dict], set[str]]:
    """
    從 section text 抽出 (performance_codes, content_codes, stages_present)。
    - lowercase / digit prefix → performance
    - uppercase prefix → content
    - 數學額外跑 MATH_CONT_RE（捕 N-1-1 風格）
    """
    perf = []
    cont = []
    seen_perf = set()
    seen_cont = set()
    stages = set()

    # 一般 regex
    # group 1=full, group 2=prefix (with Chinese subject), group 3=prefix (no Chinese),
    # group 4=stage, group 5=ordinal
    for m in ALL_CODE_RE.finditer(section_text):
        full = m.group(1)
        prefix = m.group(2) or m.group(3)  # 取有 match 的那個
        stage_raw = m.group(4)
        ordinal = m.group(5)
        # 排除 prefix 太長的（> 4 chars 的 letter+letter 不太可能）
        if len(prefix) > 4:
            continue
        # 分類
        if prefix[0].isupper():
            # uppercase = content
            if full in seen_cont:
                continue
            seen_cont.add(full)
            cont.append(parse_code(full, prefix, stage_raw, ordinal))
        else:
            # lowercase / digit = performance
            if full in seen_perf:
                continue
            seen_perf.add(full)
            perf.append(parse_code(full, prefix, stage_raw, ordinal))
        stages.add(normalize_stage(stage_raw))

    # 數學內容專用 regex
    if is_math:
        for m in MATH_CONT_RE.finditer(section_text):
            full = m.group(0)
            if full in seen_cont:
                continue
            seen_cont.add(full)
            cont.append({
                "code": full,
                "stage": normalize_stage(m.group(2)),
                "category": m.group(1),
                "ordinal": int(m.group(3)),
                "code_format": "numeric_phase",
            })
            stages.add(normalize_stage(m.group(2)))

    return perf, cont, stages


def parse_single_md(md_path: Path, dry_run: bool = False) -> dict | None:
    """處理單一 .md 檔，回傳 structured dict 或 None（失敗）。"""
    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  ERR read {md_path.name}: {e}", file=sys.stderr)
        return None

    fm = parse_frontmatter(text)
    if not fm:
        print(f"  WARN no frontmatter: {md_path.name}", file=sys.stderr)
        return None

    section_title, section_5 = extract_section_5(text)
    domain = fm.get("domain", md_path.parent.name)
    is_total = "總綱" in domain

    structured = {
        "schema_version": SCHEMA_VERSION,
        "domain": domain,
        "source_file": str(md_path.relative_to(ROOT)),
        "frontmatter": {
            "title": fm.get("title", ""),
            "domain": fm.get("domain", ""),
            "source": fm.get("source", ""),
            "source_url": fm.get("source_url", ""),
            "published_date": fm.get("published_date", ""),
            "downloaded_date": fm.get("downloaded_date", ""),
        },
        "parsed_at": now_iso(),
    }

    # 總綱特殊處理
    if is_total:
        structured["structure_type"] = "none"
        structured["no_codes"] = True
        structured["section_5_title"] = section_title or "伍、學習階段"
        structured["raw_section_5"] = section_5
        structured["performance_codes"] = []
        structured["content_codes"] = []
        structured["performance_count"] = 0
        structured["content_count"] = 0
        structured["stages_present"] = []
        structured["warnings"] = ["總綱無學習表現/學習內容編碼，符合預期"]
        return structured

    if not section_5:
        structured["structure_type"] = "unknown"
        structured["no_codes"] = False
        structured["section_5_title"] = ""
        structured["raw_section_5"] = ""
        structured["performance_codes"] = []
        structured["content_codes"] = []
        structured["performance_count"] = 0
        structured["content_count"] = 0
        structured["stages_present"] = []
        structured["warnings"] = [f"找不到伍、學習重點章節：{md_path.name}"]
        return structured

    structure_type = detect_structure_type(section_5)
    is_math = domain == "數學"

    if structure_type == "A":
        perf, cont, stages = extract_codes(section_5, is_math=is_math)
        structured["structure_type"] = "A"
        structured["section_5_title"] = section_title
        structured["raw_section_5"] = section_5
        structured["performance_codes"] = perf
        structured["content_codes"] = cont
        structured["performance_count"] = len(perf)
        structured["content_count"] = len(cont)
        structured["stages_present"] = sorted(stages, key=lambda s: ["I", "II", "III", "IV", "V"].index(s) if s in ["I", "II", "III", "IV", "V"] else 99)
        structured["warnings"] = []
        structured["no_codes"] = False
    else:
        # Type B
        stage_chunks = split_type_b_by_stage(section_5)
        all_perf = []
        all_cont = []
        all_stages = set()
        structured_stages = []
        for chunk in stage_chunks:
            perf, cont, stages = extract_codes(chunk["raw"], is_math=is_math)
            all_perf.extend(perf)
            all_cont.extend(cont)
            all_stages.update(stages)
            structured_stages.append({
                "stage_label": chunk["stage_label"],
                "performance_codes": perf,
                "content_codes": cont,
                "performance_count": len(perf),
                "content_count": len(cont),
            })
        structured["structure_type"] = "B"
        structured["section_5_title"] = section_title
        structured["raw_section_5"] = section_5
        structured["stages"] = structured_stages
        structured["performance_codes"] = all_perf
        structured["content_codes"] = all_cont
        structured["performance_count"] = len(all_perf)
        structured["content_count"] = len(all_cont)
        structured["stages_present"] = sorted(all_stages, key=lambda s: ["I", "II", "III", "IV", "V"].index(s) if s in ["I", "II", "III", "IV", "V"] else 99)
        structured["warnings"] = []
        structured["no_codes"] = False

    return structured


def update_moc(moc_path: Path, structured: dict, structured_filename: str = "structured.json") -> None:
    """更新 _index.md，加 structured.json link 與 summary。"""
    text = moc_path.read_text(encoding="utf-8")

    # 已經有 structured section？刪掉再加新的
    text = re.sub(
        r"\n## 結構化資料\n.*?(?=\n## |\Z)",
        "",
        text,
        flags=re.DOTALL,
    )

    lines = [
        "",
        "## 結構化資料",
        "",
        f"- **結構化 JSON**：[`{structured_filename}`](./{structured_filename})",
        f"- 結構類型：`{structured['structure_type']}`",
    ]
    if structured.get("no_codes"):
        lines.append("- 學習表現編碼：0（無，符合預期）")
        lines.append("- 學習內容編碼：0（無，符合預期）")
    else:
        lines.append(f"- 學習表現編碼：{structured['performance_count']}")
        lines.append(f"- 學習內容編碼：{structured['content_count']}")
        lines.append(f"- 涵蓋階段：{', '.join(structured.get('stages_present', []))}")

    if structured.get("warnings"):
        lines.append("")
        lines.append("### ⚠️ Warnings")
        for w in structured["warnings"]:
            lines.append(f"- {w}")

    text = text.rstrip() + "\n" + "\n".join(lines) + "\n"
    moc_path.write_text(text, encoding="utf-8")


def discover_domains(filter_names: list[str] | None = None) -> list[Path]:
    """掃 curriculum/*/，回傳包含 .md 的 domain dirs。"""
    domains = []
    for d in sorted(CURRICULUM.iterdir()):
        if not d.is_dir():
            continue
        md_files = [f for f in d.iterdir() if f.suffix == ".md" and not f.name.startswith("_")]
        if not md_files:
            continue
        if filter_names and d.name not in filter_names:
            continue
        domains.append(d)
    return domains


def process_domain(domain_dir: Path, dry_run: bool = False) -> list[dict]:
    """處理一個 domain dir（可能含多個 .md，如本土語文 6 子檔）。回傳所有 structured。"""
    structured_list = []
    md_files = sorted([f for f in domain_dir.iterdir() if f.suffix == ".md" and not f.name.startswith("_")])

    for md in md_files:
        print(f"  [{domain_dir.name}/{md.name}]", end=" ")
        structured = parse_single_md(md, dry_run=dry_run)
        if structured is None:
            print("SKIP")
            continue

        # 印 stats
        print(
            f"type={structured['structure_type']} "
            f"perf={structured['performance_count']} "
            f"cont={structured['content_count']} "
            f"stages={','.join(structured.get('stages_present', []))}"
        )

        if not dry_run:
            # per-md filename：避免多 .md 的 domain（本土語文 6 個、健康與體育 2 個等）
            # 互相覆蓋 structured.json
            md_stem = md.stem  # e.g. "數學領域課程綱要"
            out = md.parent / f"{md_stem}.structured.json"
            out.write_text(
                json.dumps(structured, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            structured_list.append(structured)

            # 更新 _index.md
            moc = md.parent / "_index.md"
            if moc.exists():
                update_moc(moc, structured, structured_filename=out.name)

    return structured_list


def update_aggregate_index(all_structured: list[dict]) -> None:
    """更新 curriculum/_index.json，加 structured 欄位 summary。"""
    index_path = CURRICULUM / "_index.json"
    if not index_path.exists():
        print("WARN aggregate _index.json 不存在，跳過更新", file=sys.stderr)
        return

    data = json.loads(index_path.read_text(encoding="utf-8"))

    # 把每個 item 對應到 structured
    by_key = {}
    for s in all_structured:
        key = (s["domain"], s["frontmatter"].get("title", ""))
        by_key[key] = s

    for item in data.get("items", []):
        key = (item.get("domain", ""), item.get("name", ""))
        s = by_key.get(key)
        if s:
            item["structured"] = {
                "source_file": s["source_file"],
                "structure_type": s["structure_type"],
                "performance_count": s["performance_count"],
                "content_count": s["content_count"],
                "stages_present": s.get("stages_present", []),
                "warnings": s.get("warnings", []),
                "parsed_at": s["parsed_at"],
            }

    # 頂層加個 summary
    data["structured_parsed_at"] = now_iso()
    total_perf = sum(s["performance_count"] for s in all_structured)
    total_cont = sum(s["content_count"] for s in all_structured)
    data["structured_summary"] = {
        "total_files": len(all_structured),
        "total_performance_codes": total_perf,
        "total_content_codes": total_cont,
    }

    index_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(description="把 curriculum markdown 轉結構化 JSON")
    parser.add_argument("--dry-run", action="store_true", help="不寫檔，只印 stats")
    parser.add_argument("domains", nargs="*", help="只處理指定 domain（預設全部）")
    args = parser.parse_args()

    domains = discover_domains(args.domains if args.domains else None)
    print(f"=== parse_curriculum.py ===")
    print(f"目標：{len(domains)} 個 domain\n")

    all_structured = []
    for d in domains:
        print(f"[{d.name}]")
        result = process_domain(d, dry_run=args.dry_run)
        all_structured.extend(result)

    if not args.dry_run:
        update_aggregate_index(all_structured)

    # Summary
    total_perf = sum(s["performance_count"] for s in all_structured)
    total_cont = sum(s["content_count"] for s in all_structured)
    by_type = {}
    for s in all_structured:
        by_type.setdefault(s["structure_type"], 0)
        by_type[s["structure_type"]] += 1

    print(f"\n=== 完成 ===")
    print(f"處理 {len(all_structured)} 個檔案")
    print(f"結構類型分佈：{by_type}")
    print(f"學習表現編碼總數：{total_perf}")
    print(f"學習內容編碼總數：{total_cont}")
    if args.dry_run:
        print("(dry-run 模式，未寫任何檔)")


if __name__ == "__main__":
    main()
