#!/usr/bin/env python3
"""
align_and_structure.py — §15-C + §15-E：
  1. 對齊：給每個 textbooks/<...>.md 加 aligned_codes frontmatter（對應 curriculum codes）
  2. 結構化：為每個 .md 生對應的 .structured.json（含章節結構 + aligned_codes）

對齊策略（簡化版）：
  - 對均一抓的 .md（textbooks/junyi/<domain>/<slug>.md）：
    - 從 source_url（如 /topics/math-1）判斷 stage（math-1 → I 國小 1 年級）
    - 對應到 curriculum/<domain>/...structured.json，把整個 stage 的 codes 設為 aligned_codes
  - 對 AI 生成的 .md（textbooks/generated/<domain>/stage-<X>-...md）：
    - 已含 aligned_codes，直接抄進 .structured.json
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

TZ = timezone(timedelta(hours=8))
ROOT = Path(__file__).parent.parent
TEXTBOOKS = ROOT / "textbooks"
CURRICULUM = ROOT / "curriculum"

STAGE_FROM_KEYS = {
    # Junyi URL 末段 → stage
    "math-1": "I", "math-2": "I", "math-3": "II",
    "math-4": "II", "math-5": "III", "math-6": "III",
    "math-7": "IV", "math-8": "IV", "math-9": "IV",
    "math-10": "V", "math-11": "V", "math-12": "V",
    "math-9to10": "IV",  # 國中升高中銜接
    "ele-c": "I", "jun-c": "IV", "sen-c": "V",  # 國語文總覽
    "eng-senior10": "V", "eng-senior11": "V", "eng-senior12": "V",
    "eng-senior-prep": "V",
    # 社會
    "coocele-t": "II",  # 國際教育 國小?
    "main-juni-ge": "IV",  # 國中地理
    "middle-school-civics": "IV",  # 國中公民
    "junyi-geography": "IV",
    "coocind": "V",  # 高中公民?
    # 自然科學
    "junyi-middle-school-biology": "IV",
    "middle-school-physics-chemistry": "IV",
    "junyi-middle-earth-science": "IV",
}


def log(msg: str):
    print(msg, flush=True)


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """parse simple YAML frontmatter。"""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    fm_text = text[4:end]
    body = text[end + 5:]
    fm = {}
    for line in fm_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        # 處理 list / 數字 / bool
        if val.startswith("[") and val.endswith("]"):
            try:
                fm[key] = json.loads(val)
            except json.JSONDecodeError:
                fm[key] = val
        elif val.lower() in ("true", "false"):
            fm[key] = (val.lower() == "true")
        else:
            fm[key] = val.strip('"').strip("'")
    return fm, body


def get_curriculum_codes_for_stage(domain: str, stage: str) -> tuple[list[dict], list[dict]]:
    """從 curriculum/<domain>/<...>.structured.json 取該 stage 的所有 perf + cont codes。"""
    domain_dir = CURRICULUM / domain
    if not domain_dir.is_dir():
        return [], []
    sj_files = list(domain_dir.glob("*.structured.json"))
    if not sj_files:
        return [], []
    sj = json.loads(sj_files[0].read_text(encoding="utf-8"))
    perf = [c for c in sj.get("performance_codes", []) if c["stage"] == stage]
    cont = [c for c in sj.get("content_codes", []) if c["stage"] == stage]
    return perf, cont


def find_stage_from_url(source_url: str, fname: str) -> str | None:
    """從 source_url 或 fname 找 stage。"""
    if not source_url:
        return STAGE_FROM_KEYS.get(fname.replace(".md", ""))
    # source_url: https://www.junyiacademy.org/topics/math-1
    m = re.search(r"/topics/([^/?#]+)", source_url)
    if m:
        slug = m.group(1)
        if slug in STAGE_FROM_KEYS:
            return STAGE_FROM_KEYS[slug]
        # 從 stage-X-*.md
        m2 = re.search(r"stage-([IV]+)-", fname)
        if m2:
            return m2.group(1)
    return None


def extract_chapters(body: str) -> list[dict]:
    """從 .md body 抓章節列表。簡化版：找 '第N章' / '第N單元' / '### XXX' 開頭。"""
    chapters = []
    for line in body.split("\n"):
        line = line.strip()
        if line.startswith("### ") and "—" not in line and ":" not in line:
            # 跳過欄位標題（### 學習表現 / 學習內容 / 等）
            if any(k in line for k in ["學習表現", "學習內容", "教學活動", "評量", "編碼分布", "領域簡介", "學習評量"]):
                continue
            chapter_title = line[4:].strip()
            if chapter_title:
                chapters.append({"title": chapter_title, "raw_line": line})
        elif re.match(r"^第[一二三四五六七八九十百]+章", line):
            chapters.append({"title": line, "raw_line": line})
        elif re.match(r"^【?[一二三四五六七八九十]?[上中下]?】?第?[一二三四五六七八九十]?[單課單元章]", line):
            chapters.append({"title": line, "raw_line": line})
    return chapters


def parse_md_file(md_path: Path) -> tuple[dict, str, list[dict]]:
    """parse 一個 .md → (frontmatter, body, chapters)。"""
    text = md_path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    chapters = extract_chapters(body)
    return fm, body, chapters


def align_textbook(md_path: Path) -> dict | None:
    """對齊一個 .md，回傳對應的 structured dict（要寫到 .structured.json）。"""
    fm, body, chapters = parse_md_file(md_path)
    domain = fm.get("domain", "")
    if not domain:
        log(f"    ⚠ {md_path.name} 沒 domain field, 跳過")
        return None

    # 找 stage
    stage = None
    if "stage" in fm:
        stage = fm["stage"]
    else:
        source_url = fm.get("source_url", "")
        stage = find_stage_from_url(source_url, md_path.name)

    # 找 curriculum codes
    if stage:
        perf, cont = get_curriculum_codes_for_stage(domain, stage)
    else:
        # 全部 stages（總覽頁）
        domain_dir = CURRICULUM / domain
        sj_files = list(domain_dir.glob("*.structured.json"))
        if not sj_files:
            perf, cont = [], []
        else:
            sj = json.loads(sj_files[0].read_text(encoding="utf-8"))
            perf = sj.get("performance_codes", [])
            cont = sj.get("content_codes", [])

    if not perf and not cont:
        log(f"    ⚠ {md_path.name} 找不到 curriculum codes for {domain} stage={stage}")
        aligned_codes = []
    else:
        aligned_codes = sorted(set([c["code"] for c in perf] + [c["code"] for c in cont]))

    # 結構化
    structured = {
        "schema_version": "1.0",
        "type": "textbook",
        "title": fm.get("title", md_path.stem),
        "domain": domain,
        "stage": stage,
        "source_md": str(md_path.relative_to(ROOT)),
        "source_url": fm.get("source_url", ""),
        "license": fm.get("license", ""),
        "license_url": fm.get("license_url", ""),
        "downloaded_date": fm.get("downloaded_date") or fm.get("generated_date") or now_iso(),
        "chapters": chapters,
        "aligned_codes": aligned_codes,
        "aligned_performance_count": len(perf),
        "aligned_content_count": len(cont),
        "structured_at": now_iso(),
    }
    return structured


def update_md_frontmatter(md_path: Path, aligned_codes: list[str]):
    """更新 .md frontmatter 加 aligned_codes。"""
    text = md_path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    fm["aligned_codes"] = aligned_codes
    fm["aligned_at"] = now_iso()
    # 重寫 frontmatter
    new_fm = "---\n" + "\n".join(
        f"{k}: {json.dumps(v, ensure_ascii=False) if isinstance(v, (list, str)) else v}"
        for k, v in fm.items()
    ) + "\n---\n\n"
    md_path.write_text(new_fm + body, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="§15-C + §15-E：對齊 + 結構化教材")
    parser.add_argument("--all", action="store_true", help="處理全部 textbooks/")
    parser.add_argument("--domain", type=str, help="指定領域")
    parser.add_argument("--dry-run", action="store_true", help="不寫檔，只印報告")
    args = parser.parse_args()

    log("=== align_and_structure.py ===")

    md_files = []
    if args.domain:
        # 指定領域時，往下找 <textbooks>/<source>/<domain>/*.md 或 <textbooks>/<domain>/*.md
        for pattern in [f"*/{args.domain}/*.md", f"{args.domain}/*.md", f"{args.domain}/**/*.md"]:
            md_files.extend(sorted(TEXTBOOKS.glob(pattern)))
    else:
        md_files = sorted(TEXTBOOKS.rglob("*.md"))

    # 去重
    seen = set()
    md_files = [m for m in md_files if str(m) not in seen and not seen.add(str(m))] if hasattr(set(), 'add') else md_files

    log(f"找到 {len(md_files)} 個 .md 檔\n")

    results = []
    for md in md_files:
        log(f"[{md.relative_to(ROOT)}]")
        structured = align_textbook(md)
        if structured is None:
            continue
        aligned = structured["aligned_codes"]
        log(f"  domain={structured['domain']} stage={structured['stage']} "
            f"aligned_codes={len(aligned)} chapters={len(structured['chapters'])}")

        if not args.dry_run:
            # 1. 更新 .md frontmatter
            update_md_frontmatter(md, aligned)
            # 2. 寫 .structured.json
            sj_path = md.with_suffix(".structured.json")
            sj_path.write_text(
                json.dumps(structured, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            log(f"    ✓ {md.relative_to(ROOT)} (frontmatter 更新)")
            log(f"    ✓ {sj_path.relative_to(ROOT)} ({len(aligned)} codes)")
        results.append({"md": str(md.relative_to(ROOT)), "aligned": len(aligned),
                       "chapters": len(structured["chapters"])})

    log(f"\n=== 完成 ===")
    log(f"處理 {len(results)} 個 .md")
    total_aligned = sum(r["aligned"] for r in results)
    log(f"總對齊 codes：{total_aligned}")


if __name__ == "__main__":
    main()
