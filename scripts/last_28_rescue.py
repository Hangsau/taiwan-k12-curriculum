#!/usr/bin/env python3
"""救最後 28 個：激進 OCR（600 DPI + chi_tra+chi_sim + 全頁 + 長 timeout）"""
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path("/home/hangsau/projects/taiwan-k12-curriculum")
MD_ROOT = ROOT / "exams/md"

# 更寬鬆的 keyword 偵測（含所有可能的科目變體）
KEYWORDS = {
    "國文": ["國文科", "國語文", "國語科", "國文", "國語", "國綜", "國寫", "語文領域"],
    "英文": ["英文科", "英語科", "英文", "英語", "English"],
    "數學": ["數學科", "數學", "數"],
    "自然科學": ["自然科", "自然科學", "自然與生活科技", "理化", "物理科", "化學科", "生物科", "地科", "自然科學領域", "自然"],
    "社會": ["社會科", "社會", "歷史科", "地理科", "公民科", "社會領域"],
    "健康與體育": ["健康與體育", "體育科", "健體", "健康教育", "體育", "健康"],
    "綜合活動": ["綜合活動", "綜合活動領域"],
    "藝術": ["藝術", "音樂", "美術", "表演藝術", "視覺藝術"],
    "科技": ["科技", "資訊", "生活科技"],
}


def detect_subject(text: str) -> str | None:
    if not text:
        return None
    clean = re.sub(r"\s+", "", text)
    # 用頻率：哪個科目 keyword 出現最多？
    counts = Counter()
    for canon, kws in KEYWORDS.items():
        for kw in kws:
            counts[canon] += clean.count(kw)
    # 也找明確 keyword
    if "國文科" in clean or "國語科" in clean or "語文領域" in clean:
        return "國文"
    if "英文科" in clean or "英語科" in clean or "English" in clean:
        return "英文"
    if "數學科" in clean or "數學領域" in clean:
        return "數學"
    if "自然科" in clean or "自然與生活科技" in clean:
        return "自然科學"
    if "社會科" in clean or "社會領域" in clean:
        return "社會"
    if "健體" in clean or "健康與體育" in clean or "體育科" in clean:
        return "健康與體育"
    if "綜合活動" in clean:
        return "綜合活動"
    # fallback: 最多次數
    if counts:
        most = counts.most_common(1)[0]
        if most[1] >= 2:
            return most[0]
    return None


def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    meta = {}
    for line in text[3:end].split("\n"):
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        v = v.strip().strip('"')
        meta[k.strip()] = v
    return meta, text[end + 4:].lstrip("\n")


def ocr_aggressive(pdf_path: Path) -> str:
    """激進 OCR：200 DPI + 1 頁 only + chi_tra + chi_sim + 短 timeout"""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ppm_prefix = f"{tmpdir}/p"
            # 只 1 頁、200 DPI（防卡）
            subprocess.run(
                ["pdftoppm", "-r", "200", "-f", "1", "-l", "1", "-png", str(pdf_path), ppm_prefix],
                capture_output=True, timeout=15,
            )
            results = []
            for png in sorted(Path(tmpdir).glob("*.png"))[:1]:  # 只第 1 頁
                for lang in ["chi_tra", "chi_sim"]:
                    try:
                        result = subprocess.run(
                            ["tesseract", str(png), "-", "-l", lang, "--psm", "6"],
                            capture_output=True, text=True, timeout=20,  # 短 timeout
                        )
                        if result.returncode == 0 and result.stdout.strip():
                            results.append((lang, result.stdout))
                            break  # 一個語言成功就夠
                    except Exception:
                        pass
            return "\n".join(r[1] for r in results)
    except Exception:
        return ""


def main():
    remaining = sorted(MD_ROOT.rglob("未分科目/*.md"))
    print(f"=== last_28_rescue.py ===")
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
        if not orig.exists() or orig.suffix.lower() != ".pdf":
            still_unknown.append(str(md))
            continue
        print(f"  OCR: {Path(orig).name[:60]}")
        ocr_text = ocr_aggressive(orig)
        if not ocr_text:
            still_unknown.append(str(md))
            continue
        detected = detect_subject(ocr_text)
        if not detected:
            # 把 OCR 結果保留在 .md（即使沒抓到）
            new_meta = dict(meta)
            new_meta["extract_method"] = "tesseract-aggressive"
            new_meta["extracted_at"] = new_meta.get("extracted_at", "") + " (aggressive OCR)"
            fm_lines = ["---"]
            for k, v in new_meta.items():
                if isinstance(v, str) and (":" in v or "\n" in v):
                    fm_lines.append(f'{k}: "{v}"')
                else:
                    fm_lines.append(f"{k}: {v}")
            fm_lines.append("---")
            new_md_content = "\n".join(fm_lines) + "\n\n" + ocr_text + "\n"
            md.write_text(new_md_content, encoding="utf-8")
            still_unknown.append(str(md))
            continue
        # relocate
        new_meta = dict(meta)
        new_meta["subject"] = detected
        new_meta["extract_method"] = "tesseract-aggressive"
        new_meta["extracted_at"] = new_meta.get("extracted_at", "") + " (aggressive OCR)"
        fm_lines = ["---"]
        for k, v in new_meta.items():
            if isinstance(v, str) and (":" in v or "\n" in v):
                fm_lines.append(f'{k}: "{v}"')
            else:
                fm_lines.append(f"{k}: {v}")
        fm_lines.append("---")
        new_md_content = "\n".join(fm_lines) + "\n\n" + ocr_text + "\n"
        new_dir = md.parent.parent / detected
        new_dir.mkdir(parents=True, exist_ok=True)
        new_path = new_dir / md.name
        if new_path.exists():
            sha = meta.get("sha256", "00000000")[:8]
            new_path = new_dir / f"{md.stem}-{sha}.md"
        new_path.write_text(new_md_content, encoding="utf-8")
        md.unlink()
        relocated += 1
        print(f"    → {detected}")

    print(f"\n=== 結果 ===")
    print(f"重定位: {relocated}")
    print(f"仍未知: {len(still_unknown)}")
    if still_unknown:
        for p in still_unknown:
            print(f"  - {p}")


if __name__ == "__main__":
    main()
