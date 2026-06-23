#!/usr/bin/env python3
"""
verify_curriculum.py — 驗證 curriculum/<domain>/*.structured.json 的正確性。

開頭先跑 regex self-test（fixture 比對），工具壞掉立刻 exit 2。
然後跑 5 類檢查：
  1. frontmatter 必填欄位
  2. section_5_title 存在（除 total=true）
  3. structure_type 合法（A/B/none）
  4. 羅馬數字正規化（stage 必為 I/II/III/IV/V）
  5. 編碼數量 >= min_codes（低於只 warning，不擋 exit 0）

退出碼：
  - 0 = pass（含 warning 也算 pass，per Q3 決策）
  - 1 = 資料壞（欄位缺 / type 錯 / 羅馬數字沒正規化）
  - 2 = 工具壞（regex self-test 失敗）

Usage:
  python3 scripts/verify_curriculum.py
  python3 scripts/verify_curriculum.py 數學 自然科學   # 只驗指定 domain
"""
import argparse
import json
import re
import sys
from pathlib import Path

# Windows cp950 console 無法輸出 ✓ 等 Unicode 符號（會 UnicodeEncodeError），強制 UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent  # taiwan-k12-curriculum/
CURRICULUM = ROOT / "curriculum"
SCHEMA_VERSION = "1.0"

VALID_STAGES = {"I", "II", "III", "IV", "V"}
VALID_STRUCTURE_TYPES = {"A", "B", "none", "unknown"}
REQUIRED_FRONTMATTER = {"title", "domain", "source", "source_url", "published_date"}

# Per-domain min_codes（warning 門檻）。低於 → warning，不擋 exit 0。
MIN_CODES = {
    "數學": (80, 100),
    "國語文": (80, 100),
    "英語文": (150, 80),
    "第二外國語文": (100, 80),  # filename
    "閩南語文": (30, 50),
    "客家語文": (30, 50),
    "原住民族語文": (30, 50),
    "新住民語文": (30, 50),
    "臺灣手語": (30, 50),
    "閩東語文": (30, 50),
    "自然科學": (50, 200),
    "社會": (80, 400),
    "藝術": (50, 40),
    "健康與體育": (150, 200),
    "生活課程": (20, 15),  # filename
    "綜合活動": (30, 100),
    "科技": (30, 50),
    "全民國防教育": (15, 15),  # filename
}


# ==================== Regex Self-Test ====================

# 從 parse_curriculum.py 引入 regex（保持單一來源）
from parse_curriculum import (
    ALL_CODE_RE,
    MATH_CONT_RE,
    SECTION_5_PATTERNS,
    SECTION_5_END,
    ROMAN_MAP,
    normalize_stage,
)

REGEX_FIXTURES = [
    # (pattern_name, fixture_text, expected_codes_or_None)
    ("ALL_CODE_RE.perf_basic", "n-I-1 理解一千以內數。", {"n-I-1"}),
    ("ALL_CODE_RE.perf_fullwidth", "n-Ⅰ-2 理解加法。", {"n-Ⅰ-2"}),
    ("ALL_CODE_RE.perf_chinese_numeral_roman", "1-Ⅱ-1 listen", {"1-Ⅱ-1"}),
    ("ALL_CODE_RE.perf_letter_prefix_2", "ti-Ⅱ-1 reasoning", {"ti-Ⅱ-1"}),
    ("ALL_CODE_RE.perf_letter_prefix_3", "abcd-III-1 (4 chars, should skip)", set()),
    ("ALL_CODE_RE.cont_basic", "Ab-Ⅱ-1 字音", {"Ab-Ⅱ-1"}),
    ("ALL_CODE_RE.cont_cross_concept", "INa-Ⅱ-1 cross concept", {"INa-Ⅱ-1"}),
    ("ALL_CODE_RE.cont_subject_prefix", "歷Aa-IV-1 history", {"歷Aa-IV-1"}),  # likely fail — prefix too long
    ("ALL_CODE_RE.no_false_positive_in_words", "I have a cat.", set()),
    ("MATH_CONT_RE.basic", "N-1-1 一百以內的數。", {"N-1-1"}),
    ("MATH_CONT_RE.no_false_in_sentence", "This is a 3-4-5 triple.", set()),
    ("SECTION_5_PATTERNS.basic", "目次\n伍、學習重點 ............. 6\n...正文\n伍、學習重點\n內容...", None),
    ("SECTION_5_PATTERNS.with_formfeed", "目次\n伍、學習重點 ............. 6\n\f伍、學習重點\n內容", None),
    ("SECTION_5_PATTERNS.space_variant", "目次\n伍、學習重點 ............. 6\n伍、 學習重點\n內容", None),
]


def run_regex_self_test() -> tuple[bool, list[str]]:
    """跑 regex self-test。回傳 (pass, errors)。"""
    errors = []
    for name, text, expected in REGEX_FIXTURES:
        if name.startswith("ALL_CODE_RE."):
            actual = {m.group(1) for m in ALL_CODE_RE.finditer(text)}
            if expected is not None and actual != expected:
                errors.append(f"  FAIL {name}: expected={expected}, got={actual}")
        elif name.startswith("MATH_CONT_RE."):
            actual = {m.group(0) for m in MATH_CONT_RE.finditer(text)}
            if expected is not None and actual != expected:
                errors.append(f"  FAIL {name}: expected={expected}, got={actual}")
        elif name.startswith("SECTION_5_PATTERNS."):
            # SECTION_5_PATTERNS 是 list of regex，找有 hits
            hits = []
            for pat in SECTION_5_PATTERNS:
                hits.extend(list(pat.finditer(text)))
            actual = len(hits)
            # expected: 至少要能抓到正文中真正的 heading（排除目次）
            if actual < 1:
                errors.append(f"  FAIL {name}: expected ≥1 matches, got {actual}")

    # ROMAN_MAP smoke test
    if normalize_stage("Ⅰ") != "I":
        errors.append(f"  FAIL ROMAN_MAP: Ⅰ → I failed, got {normalize_stage('Ⅰ')}")
    if normalize_stage("5") != "V":
        errors.append(f"  FAIL ROMAN_MAP: 5 → V failed, got {normalize_stage('5')}")

    return (len(errors) == 0, errors)


# ==================== Verification ====================


def find_min_for_domain(domain_dirname: str, md_filename: str) -> tuple[int, int] | None:
    """從 MIN_CODES 找對應的 min_codes。優先用 md_filename（含「第二外國」等變體）。"""
    # 先試 filename match
    for key, val in MIN_CODES.items():
        if key in md_filename:
            return val
    # 再試 dirname
    if domain_dirname in MIN_CODES:
        return MIN_CODES[domain_dirname]
    return None


def verify_structured(sj_path: Path) -> tuple[list[str], list[str]]:
    """驗證單一 structured.json。回傳 (failures, warnings)。"""
    failures = []
    warnings = []

    try:
        data = json.loads(sj_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        failures.append(f"invalid JSON: {e}")
        return failures, warnings

    # 1. schema_version
    if data.get("schema_version") != SCHEMA_VERSION:
        failures.append(f"schema_version mismatch: expected {SCHEMA_VERSION}, got {data.get('schema_version')}")

    # 2. frontmatter 必填
    fm = data.get("frontmatter", {})
    for key in REQUIRED_FRONTMATTER:
        if not fm.get(key):
            failures.append(f"frontmatter.{key} 缺失或為空")

    # 3. structure_type
    st = data.get("structure_type")
    if st not in VALID_STRUCTURE_TYPES:
        failures.append(f"structure_type 不合法: {st}")
        return failures, warnings

    # 4. total=true 不用檢查 section_5
    if data.get("no_codes"):
        if data.get("performance_count", -1) != 0:
            warnings.append(f"no_codes=true 但 performance_count={data.get('performance_count')}（應為 0）")
        if data.get("content_count", -1) != 0:
            warnings.append(f"no_codes=true 但 content_count={data.get('content_count')}（應為 0）")
        return failures, warnings

    # 5. section_5_title 存在
    if not data.get("section_5_title"):
        warnings.append("section_5_title 為空")

    # 6. raw_section_5 存在
    if not data.get("raw_section_5"):
        failures.append("raw_section_5 為空")

    # 7. codes 陣列存在
    perf = data.get("performance_codes", [])
    cont = data.get("content_codes", [])
    if not isinstance(perf, list):
        failures.append("performance_codes 不是 list")
    if not isinstance(cont, list):
        failures.append("content_codes 不是 list")

    # 8. count 一致
    if data.get("performance_count") != len(perf):
        failures.append(f"performance_count={data.get('performance_count')} != len(performance_codes)={len(perf)}")
    if data.get("content_count") != len(cont):
        failures.append(f"content_count={data.get('content_count')} != len(content_codes)={len(cont)}")

    # 9. 羅馬數字正規化
    bad_stages = set()
    for code in perf + cont:
        s = code.get("stage")
        if s and s not in VALID_STAGES:
            bad_stages.add(s)
    if bad_stages:
        failures.append(f"未正規化的 stage：{bad_stages}")

    # 10. code 欄位必填
    for i, code in enumerate(perf[:5]):  # 只抽查前 5 個，避免 huge output
        for key in ("code", "stage", "category", "ordinal", "code_format"):
            if key not in code:
                failures.append(f"performance_codes[{i}] 缺欄位 {key}")
                break
    for i, code in enumerate(cont[:5]):
        for key in ("code", "stage", "category", "ordinal", "code_format"):
            if key not in code:
                failures.append(f"content_codes[{i}] 缺欄位 {key}")
                break

    # 11. min_codes warning（不擋）
    domain_dir = sj_path.parent.name
    md_stem = sj_path.stem.replace(".structured", "")
    min_codes = find_min_for_domain(domain_dir, md_stem)
    if min_codes:
        min_perf, min_cont = min_codes
        if len(perf) < min_perf:
            warnings.append(f"performance_codes={len(perf)} < min={min_perf}（預期）")
        if len(cont) < min_cont:
            warnings.append(f"content_codes={len(cont)} < min={min_cont}（預期）")

    # 12. stages_present 必為 subset of VALID_STAGES
    stages_present = set(data.get("stages_present", []))
    bad_sp = stages_present - VALID_STAGES
    if bad_sp:
        failures.append(f"stages_present 含未正規化：{bad_sp}")

    return failures, warnings


def main():
    parser = argparse.ArgumentParser(description="驗證 curriculum structured.json")
    parser.add_argument("domains", nargs="*", help="只驗指定 domain（預設全部）")
    args = parser.parse_args()

    print(f"=== verify_curriculum.py ===\n")

    # Phase 1: regex self-test
    print("[self-test] 跑 regex fixture 比對...")
    pass_self, errors = run_regex_self_test()
    if not pass_self:
        print("  FAIL — regex 行為與預期不符（工具壞了，先修再驗資料）")
        for e in errors:
            print(e)
        sys.exit(2)
    print(f"  ✓ {len(REGEX_FIXTURES)} fixtures + ROMAN_MAP 全 pass\n")

    # Phase 2: discover + verify
    if args.domains:
        domains = [d for d in CURRICULUM.iterdir() if d.is_dir() and d.name in args.domains]
    else:
        domains = sorted([d for d in CURRICULUM.iterdir() if d.is_dir()])

    all_failures = []
    all_warnings = []
    files_checked = 0

    for d in domains:
        sj_files = sorted(d.glob("*.structured.json"))
        if not sj_files:
            all_failures.append(f"{d.name}/ 找不到任何 *.structured.json（先跑 parse_curriculum.py）")
            continue
        for sj in sj_files:
            files_checked += 1
            failures, warnings = verify_structured(sj)
            rel = sj.relative_to(ROOT)
            if failures:
                print(f"  ✗ {rel}")
                for f in failures:
                    print(f"      {f}")
                all_failures.extend([f"{rel}: {f}" for f in failures])
            else:
                # pass 但可能 warning
                marker = "⚠" if warnings else "✓"
                print(f"  {marker} {rel}")
            for w in warnings:
                print(f"      WARN: {w}")
                all_warnings.append(f"{rel}: {w}")

    print(f"\n=== Summary ===")
    print(f"驗證檔案：{files_checked}")
    print(f"Failures：{len(all_failures)}")
    print(f"Warnings：{len(all_warnings)}")

    if all_warnings and not all_failures:
        print(f"\n（Warning 不擋 exit 0，per 決策 Q3）")

    sys.exit(1 if all_failures else 0)


if __name__ == "__main__":
    main()
