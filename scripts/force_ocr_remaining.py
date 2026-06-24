#!/usr/bin/env python3
"""強制 OCR 剩下 31 個未分類 .md"""
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path("/home/hangsau/projects/taiwan-k12-curriculum")
MD_ROOT = ROOT / "exams/md"

SUBJECT_KEYWORDS = {
    "國文": ["國文科", "國語文", "國語科", "國文", "國語", "國綜", "國寫"],
    "英文": ["英文科", "英語科", "英文", "英語"],
    "數學": ["數學科", "數學"],
    "自然科學": ["自然科", "自然科學", "自然與生活科技", "物理科", "化學科", "生物科", "地科"],
    "社會": ["社會科", "社會", "歷史科", "地理科", "公民科"],
    "健康與體育": ["健康與體育", "體育科", "健體", "健康教育"],
}


def detect_subject_from_text(text: str) -> str | None:
    if not text:
        return None
    clean = re.sub(r"\s+", "", text)
    for canon, kws in SUBJECT_KEYWORDS.items():
        for kw in kws:
            if kw in clean:
                return canon
    return None


def parse_frontmatter(text: str):
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
        if v.startswith('"') and v.endswith('"'):
            v = v[1:-1]
        meta[k.strip()] = v
    return meta, body


def ocr_pdf(pdf_path: Path, timeout: int = 45) -> str:
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ppm_prefix = f"{tmpdir}/p"
            subprocess.run(
                ["pdftoppm", "-r", "200", "-f", "1", "-l", "2", "-png", str(pdf_path), ppm_prefix],
                capture_output=True, timeout=20,
            )
            ocr_results = []
            for png in sorted(Path(tmpdir).glob("*.png")):
                result = subprocess.run(
                    ["tesseract", str(png), "-", "-l", "chi_tra", "--psm", "6"],
                    capture_output=True, text=True, timeout=timeout,
                )
                if result.returncode == 0 and result.stdout.strip():
                    ocr_results.append(result.stdout)
            if ocr_results:
                return "\n".join(ocr_results)
    except Exception:
        pass
    return ""


def main():
    remaining = sorted(MD_ROOT.rglob("未分科目/*.md"))
    print(f"=== force_ocr_remaining.py ===")
    print(f"剩餘未分類: {len(remaining)}")

    relocated = 0
    still_unknown = []
    for md in remaining:
        txt = md.read_text(encoding="utf-8", errors="replace")
        meta, body = parse_frontmatter(txt)
        op = meta.get("original_path")
        if not op:
            still_unknown.append(str(md))
            continue
        orig = ROOT / op
        if not orig.exists():
            still_unknown.append(str(md))
            continue
        # 強制 OCR
        print(f"  OCR: {orig.name[:60]}")
        ocr_text = ocr_pdf(orig)
        if not ocr_text:
            still_unknown.append(str(md))
            continue
        detected = detect_subject_from_text(ocr_text)
        if not detected:
            # body 也存 OCR 結果但保留未分類
            new_meta = dict(meta)
            new_meta["extract_method"] = "tesseract-chi_tra"
            new_meta["extracted_at"] = new_meta.get("extracted_at", "") + " (OCR retry)"
            fm_lines = ["---"]
            for k, v in new_meta.items():
                if isinstance(v, str) and (":" in v or "\n" in v):
                    fm_lines.append(f'{k}: "{v}"')
                else:
                    fm_lines.append(f"{k}: {v}")
            fm_lines.append("---")
            new_md = "\n".join(fm_lines) + "\n\n" + ocr_text + "\n"
            md.write_text(new_md, encoding="utf-8")
            still_unknown.append(str(md))
            continue
        # 成功偵測到 → relocate
        new_subject = detected
        new_meta = dict(meta)
        new_meta["subject"] = new_subject
        new_meta["extract_method"] = "tesseract-chi_tra"
        new_meta["extracted_at"] = new_meta.get("extracted_at", "") + " (OCR retry)"
        fm_lines = ["---"]
        for k, v in new_meta.items():
            if isinstance(v, str) and (":" in v or "\n" in v):
                fm_lines.append(f'{k}: "{v}"')
            else:
                fm_lines.append(f"{k}: {v}")
        fm_lines.append("---")
        new_md_content = "\n".join(fm_lines) + "\n\n" + ocr_text + "\n"
        new_dir = md.parent.parent / new_subject
        new_dir.mkdir(parents=True, exist_ok=True)
        new_path = new_dir / md.name
        if new_path.exists():
            sha = meta.get("sha256", "00000000")[:8]
            new_path = new_dir / f"{md.stem}-{sha}.md"
        new_path.write_text(new_md_content, encoding="utf-8")
        md.unlink()
        relocated += 1
        print(f"    → {new_subject}")

    print(f"\n=== 結果 ===")
    print(f"重定位: {relocated}")
    print(f"仍未知: {len(still_unknown)}")


if __name__ == "__main__":
    main()
