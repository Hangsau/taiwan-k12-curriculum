#!/usr/bin/env python3
"""
rename 米蘭老師原始檔 (mojibake → 繁中)，並同步更新對應 .md 的 frontmatter original_path / original_filename。
- 原始檔在 exams/melances/grade*/<test_type>/<mojibake>.pdf|doc|docx|xlsx
- 對每個 .md 讀 frontmatter sha256，搜對應原始檔，rename
- idempotent: 已修過會跳過
"""
import os, re, glob, sys, hashlib
from pathlib import Path

dry = "--dry" in sys.argv

def fix_mojibake(s):
    try:
        f = s.encode("latin-1").decode("utf-8")
        return f
    except (UnicodeDecodeError, UnicodeEncodeError):
        return None

def has_mojibake(s):
    """判斷字串裡有 latin-1 supplement byte 連續"""
    cnt = 0
    for ch in s:
        if 0x80 <= ord(ch) <= 0xff:
            cnt += 1
            if cnt >= 3: return True
        else: cnt = 0
    return False

def fix_path_segments(path_str):
    """path 分段，只對 mojibake segment fix"""
    parts = path_str.split("/")
    new_parts = []
    changed = False
    for p in parts:
        if has_mojibake(p):
            f = fix_mojibake(p)
            if f and any("\u4e00" <= ch <= "\u9fff" for ch in f):
                new_parts.append(f)
                changed = True
                continue
        new_parts.append(p)
    return "/".join(new_parts), changed

stats = {"md_total":0, "orig_renamed":0, "orig_already_clean":0, "orig_missing":0, "orig_failed_rename":0, "md_path_updated":0}
file_moves = []  # (src, dst)
md_updates = []  # (md_path, old_orig_path, new_orig_path, old_filename, new_filename)

for md_file in glob.glob("exams/md/by-grade-subject/**/*.md", recursive=True):
    with open(md_file, encoding="utf-8") as fh: content = fh.read()
    if "source: melances" not in content: continue
    stats["md_total"] += 1
    fm_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not fm_match: continue
    fm = fm_match.group(1)
    op_match = re.search(r"^original_path: (.+)$", fm, re.MULTILINE)
    of_match = re.search(r"^original_filename: (.+)$", fm, re.MULTILINE)
    if not op_match: continue
    orig_path = op_match.group(1).strip()
    orig_filename = of_match.group(1).strip() if of_match else None
    if not os.path.exists(orig_path):
        # 試 fix path 看看修完是否存在
        fixed_path, changed = fix_path_segments(orig_path)
        if changed and os.path.exists(fixed_path):
            # 已經 rename 過了
            stats["orig_already_clean"] += 1
            # 更新 frontmatter
            if not dry:
                content = content.replace(orig_path, fixed_path, 1)
                with open(md_file, "w", encoding="utf-8") as fh: fh.write(content)
            md_updates.append((md_file, orig_path, fixed_path, None, None))
            stats["md_path_updated"] += 1
        else:
            stats["orig_missing"] += 1
        continue
    # 原始檔還在，rename it
    fixed_path, changed = fix_path_segments(orig_path)
    if not changed or fixed_path == orig_path:
        stats["orig_already_clean"] += 1
        continue
    # mkdir for new path
    new_dir = os.path.dirname(fixed_path)
    if not dry:
        os.makedirs(new_dir, exist_ok=True)
        try:
            os.rename(orig_path, fixed_path)
            stats["orig_renamed"] += 1
            file_moves.append((orig_path, fixed_path))
            # 更新 frontmatter
            content = content.replace(orig_path, fixed_path, 1)
            with open(md_file, "w", encoding="utf-8") as fh: fh.write(content)
            stats["md_path_updated"] += 1
        except OSError as e:
            stats["orig_failed_rename"] += 1
            print(f"FAIL rename: {orig_path} -> {fixed_path}: {e}", file=sys.stderr)
    else:
        stats["orig_renamed"] += 1
        file_moves.append((orig_path, fixed_path))

print("--- stats ---")
for k,v in stats.items(): print(f"  {k}: {v}")
print(f"\n--- 前 5 個 rename preview ---")
for src, dst in file_moves[:5]:
    print(f"  {src}")
    print(f"  -> {dst}\n")
