#!/usr/bin/env python3
"""刪除 body 完全空或極短的考卷 .md + 對應原始檔（已試 OCR 多次失敗）"""
import os, glob, re, sys
from collections import Counter

dry = "--dry" in sys.argv
deleted_md = 0
deleted_orig = 0
orig_missing = 0
by_source = Counter()
by_grade = Counter()
preview = []

for f in glob.glob("exams/md/by-grade-subject/**/*.md", recursive=True):
    with open(f, encoding="utf-8") as fh: c = fh.read()
    parts = c.split("---\n")
    body = parts[2] if len(parts)>=3 else ""
    if len(body.strip()) >= 200: continue  # 留下 >= 200 字的
    fm = parts[1] if len(parts)>=2 else ""
    src = re.search(r"^source: (.+)$", fm, re.MULTILINE)
    op = re.search(r"^original_path: (.+)$", fm, re.MULTILINE)
    grade = re.search(r"^grade_label: (.+)$", fm, re.MULTILINE)
    by_source[src.group(1) if src else "?"] += 1
    by_grade[grade.group(1) if grade else "?"] += 1
    if op and os.path.exists(op.group(1).strip()):
        if not dry: os.remove(op.group(1).strip())
        deleted_orig += 1
    else:
        orig_missing += 1
    if not dry: os.remove(f)
    deleted_md += 1
    if len(preview) < 3: preview.append((f, op.group(1) if op else None))

print(f"--- 待刪 ---")
print(f"  md: {deleted_md}")
print(f"  原始檔: {deleted_orig}")
print(f"  原始檔已不存在: {orig_missing}")
print("--- by source ---")
for k,v in by_source.most_common(): print(f"  {k}: {v}")
print("--- by grade ---")
for k,v in sorted(by_grade.items()): print(f"  {k}: {v}")
print("--- preview ---")
for md, op in preview[:3]: print(f"  md={md}\n  orig={op}")
