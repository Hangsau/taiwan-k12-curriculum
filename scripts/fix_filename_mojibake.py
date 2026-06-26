#!/usr/bin/env python3
"""修 .md frontmatter 的 original_filename mojibake (latin1->utf8)"""
import os, glob, re, sys

def try_fix(s):
    """還原後 CJK 字數明顯增加才採用，否則回 None"""
    try:
        fixed = s.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return None
    cjk_before = sum(1 for c in s if "\u4e00" <= c <= "\u9fff")
    cjk_after = sum(1 for c in fixed if "\u4e00" <= c <= "\u9fff")
    if cjk_after >= cjk_before + 3:
        return fixed
    return None

dry_run = "--dry" in sys.argv
stats = {"total":0, "original_filename_fixed":0, "original_filename_raw_fixed":0, "original_path_fixed":0, "unchanged":0}
preview = []
fields = ["original_filename", "original_filename_raw", "original_path"]

for f in glob.glob("exams/md/by-grade-subject/**/*.md", recursive=True):
    stats["total"] += 1
    with open(f, encoding="utf-8") as fh:
        content = fh.read()
    new_content = content
    changed = []
    for field in fields:
        m = re.search(rf"^{field}: (.+)$", new_content, re.MULTILINE)
        if m:
            fixed = try_fix(m.group(1))
            if fixed:
                new_content = re.sub(rf"^{field}: .+$", f"{field}: {fixed}", new_content, count=1, flags=re.MULTILINE)
                stats[f"{field}_fixed"] += 1
                changed.append((field, m.group(1)[:60], fixed[:60]))
    if changed:
        if len(preview) < 3: preview.append((f, changed))
        if not dry_run:
            with open(f, "w", encoding="utf-8") as fh: fh.write(new_content)
    else:
        stats["unchanged"] += 1

print("--- stats ---")
for k,v in stats.items(): print(f"  {k}: {v}")
print("--- preview ---")
for f, ch in preview:
    print(f)
    for field, before, after in ch:
        print(f"  [{field}]")
        print(f"    before: {before}")
        print(f"    after:  {after}")
