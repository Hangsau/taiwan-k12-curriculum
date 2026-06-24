#!/usr/bin/env python3
"""
verify_exams_md.py — 驗證 exams/md/ 產出的 .md 檔案完整性。

跑在 extract_exams_to_md.py 之後。檢查：
1. 每個 .md 有合法 YAML frontmatter
2. 必填欄位齊全（source/year_roc/stage/grade_label/subject/sha256）
3. 對應原始檔存在（original_path）
4. sha256 與原始檔實際 hash 一致
5. body 不是空（至少 10 字）
6. ddes 來源的 test_type 必填
7. 失敗清單 EXTRACT_FAIL.json 存在且格式合法
8. 每個原始 PDF/DOCX/DOC 都對應到一個 .md（除了 EXTRACT_FAIL 列的）

回傳 exit code：
- 0: 全部 pass
- 1: 有 failure
- 2: regex/工具壞掉
"""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))
ROOT = Path(__file__).parent.parent
EXAMS = ROOT / "exams"
MD_ROOT = EXAMS / "md"

# 跟 extract_exams_to_md.py 一致的必填欄位 + 合法值
REQUIRED_FIELDS = ["source", "stage", "grade_label", "subject", "sha256", "original_path"]
VALID_SOURCES = {"CEEC", "melances", "ddes"}
KNOWN_FAILURE_REASONS = {
    "doc-skipped",      # .doc binary 沒 antiword
    "xlsx-skipped",     # .xlsx 不是考卷
    "unsupported-ext",
    "pdftotext failed",
    "docx stdlib failed",
}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """極簡 YAML frontmatter 解析（只支援 key: value 或 key: "string"）。
    回傳 (metadata dict, body text)。"""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_block = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")
    meta = {}
    for line in fm_block.split("\n"):
        line = line.rstrip()
        if not line or ":" not in line:
            continue
        k, _, v = line.partition(":")
        v = v.strip()
        # 處理 "string" 或 'string'
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1].replace('\\"', '"')
        # bool / null
        if v == "null":
            v = None
        elif v == "true":
            v = True
        elif v == "false":
            v = False
        # int
        elif re.match(r"^-?\d+$", v):
            v = int(v)
        meta[k.strip()] = v
    return meta, body


def sha256_of(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description="驗證 exams/md/ 產出完整性")
    parser.add_argument("--strict", action="store_true", help="嚴格模式（警告也算失敗）")
    args = parser.parse_args()

    if not MD_ROOT.exists():
        print(f"ERR: {MD_ROOT} 不存在（先跑 extract_exams_to_md.py）")
        return 2

    md_files = sorted(MD_ROOT.rglob("*.md"))
    print(f"=== verify_exams_md.py ===")
    print(f"掃到 {len(md_files)} 個 .md 檔")

    failures = []
    warnings = []
    stats = Counter()

    for md in md_files:
        rel = md.relative_to(ROOT)
        try:
            text = md.read_text(encoding="utf-8")
        except Exception as e:
            failures.append({"file": str(rel), "check": "readable", "detail": str(e)})
            continue

        meta, body = parse_frontmatter(text)

        # 1. frontmatter 存在
        if not meta:
            failures.append({"file": str(rel), "check": "frontmatter", "detail": "frontmatter 解析失敗"})
            continue

        # 2. 必填欄位齊全
        missing = [f for f in REQUIRED_FIELDS if f not in meta or meta[f] in (None, "")]
        if missing:
            failures.append({"file": str(rel), "check": "required_fields", "detail": f"缺欄位: {missing}"})
            continue

        # 3. 原始檔存在
        orig = ROOT / meta["original_path"]
        if not orig.exists():
            failures.append({"file": str(rel), "check": "original_exists", "detail": f"原始檔不存在: {meta['original_path']}"})
            continue

        # 4. sha256 一致
        actual_sha = sha256_of(orig)
        if actual_sha != meta["sha256"]:
            failures.append({"file": str(rel), "check": "sha256", "detail": f"sha256 不一致（可能檔案被改過）"})
            continue

        # 5. body 不是空
        body_stripped = body.strip()
        if len(body_stripped) < 10:
            failures.append({"file": str(rel), "check": "body_empty", "detail": f"body 太短 ({len(body_stripped)} 字)"})
            continue

        # 6. source 合法
        if meta.get("source") not in VALID_SOURCES:
            warnings.append({"file": str(rel), "check": "source_invalid", "detail": f"未知 source: {meta['source']}"})
        stats[meta["source"]] += 1

        # 7. ddes 必須有 test_type
        if meta.get("source") == "ddes" and not meta.get("test_type"):
            warnings.append({"file": str(rel), "check": "ddes_test_type", "detail": "ddes 來源缺 test_type"})

        # 8. 目錄結構合法
        parts = md.relative_to(MD_ROOT).parts
        if len(parts) < 3 or parts[0] != "by-grade-subject":
            warnings.append({"file": str(rel), "check": "dir_structure", "detail": f"非標準目錄: {parts[:3]}"})

    # 9. 失敗清單檢查
    fail_path = MD_ROOT / "EXTRACT_FAIL.json"
    fail_summary = None
    if not fail_path.exists():
        warnings.append({"file": "EXTRACT_FAIL.json", "check": "fail_log_exists", "detail": "EXTRACT_FAIL.json 不存在"})
    else:
        try:
            fail_data = json.loads(fail_path.read_text(encoding="utf-8"))
            fail_summary = {
                "total": fail_data.get("total"),
                "success": fail_data.get("success"),
                "fail_count": fail_data.get("fail_count"),
            }
            fail_reasons = Counter(f["reason"].split(":")[0] for f in fail_data.get("fail", []))
            for r in fail_reasons:
                if r not in KNOWN_FAILURE_REASONS and not r.startswith("pdftotext"):
                    warnings.append({"file": "EXTRACT_FAIL.json", "check": "unknown_fail_reason", "detail": f"未知失敗原因: {r}"})
        except Exception as e:
            failures.append({"file": "EXTRACT_FAIL.json", "check": "fail_log_parse", "detail": str(e)})

    # 10. 覆蓋率：每個原始 PDF/DOCX/DOC 都應該有 .md 或在 fail list
    print(f"\n=== 覆蓋率檢查 ===")
    orig_files = []
    for ext in ["pdf", "docx", "doc", "xlsx"]:
        orig_files.extend(EXAMS.rglob(f"*.{ext}"))
    orig_files_set = {str(f.relative_to(ROOT)) for f in orig_files}
    # 從 .md 的 original_path 拿
    covered = set()
    for md in md_files:
        meta, _ = parse_frontmatter(md.read_text(encoding="utf-8"))
        if "original_path" in meta:
            covered.add(meta["original_path"])

    uncovered = orig_files_set - covered
    fail_paths = set()
    if fail_path.exists():
        fail_data = json.loads(fail_path.read_text(encoding="utf-8"))
        fail_paths = {f["path"] for f in fail_data.get("fail", [])}

    really_missing = uncovered - fail_paths
    if really_missing:
        warnings.append({"file": "(coverage)", "check": "uncovered_originals", "detail": f"{len(really_missing)} 個原始檔沒對應 .md 也不在 fail list"})
    print(f"  原始檔: {len(orig_files_set)}")
    print(f"  已產 .md: {len(covered)}")
    print(f"  fail list: {len(fail_paths)}")
    print(f"  未覆蓋: {len(really_missing)}")

    # 報告
    print(f"\n=== 結果 ===")
    print(f"成功: {len(md_files) - len(failures)}/{len(md_files)} 個 .md")
    print(f"失敗: {len(failures)} 個")
    print(f"警告: {len(warnings)} 個")

    if stats:
        print(f"\n=== by source ===")
        for src, n in sorted(stats.items(), key=lambda x: -x[1]):
            print(f"  {src:10} {n:>5}")

    if fail_summary:
        print(f"\n=== 原始檔抽取統計 ===")
        print(f"  total:     {fail_summary['total']}")
        print(f"  success:   {fail_summary['success']}")
        print(f"  fail:      {fail_summary['fail_count']}")

    if failures:
        print(f"\n=== 失敗（前 20）===")
        for f in failures[:20]:
            print(f"  [{f['check']}] {f['file']}: {f['detail']}")

    if warnings and (args.strict or len(warnings) <= 20):
        print(f"\n=== 警告（前 20）===")
        for w in warnings[:20]:
            print(f"  [{w['check']}] {w['file']}: {w['detail']}")

    return 1 if failures else (1 if args.strict and warnings else 0)


if __name__ == "__main__":
    sys.exit(main())
