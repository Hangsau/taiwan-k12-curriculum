#!/usr/bin/env python3
"""
ocr_and_relocate.py — 把「未分科目」目錄的 .md 重新整理：
1. OCR 1211 個純圖檔（body 太短）→ 重新 detect_subject
2. 用 group（學年+學期+年級+校名）統計同組其他檔的科目，推算 1259 個答案卷
3. 移 .md 到正確科目目錄

執行：background 跑完後，自動 relocate + commit。
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/home/hangsau/projects/taiwan-k12-curriculum")
MD_ROOT = ROOT / "exams/md"
EXAMS = ROOT / "exams"

SUBJECT_KEYWORDS = {
    "國文": ["國文科", "國語文", "國語科", "國文", "國語", "國綜", "國寫"],
    "英文": ["英文科", "英語科", "英文", "英語"],
    "數學": ["數學科", "數學"],
    "自然科學": ["自然科", "自然科學", "自然與生活科技", "物理科", "化學科", "生物科", "地科"],
    "社會": ["社會科", "社會", "歷史科", "地理科", "公民科"],
    "健康與體育": ["健康與體育", "體育科", "健體", "健康教育"],
}


def detect_subject_from_text(text: str) -> str | None:
    """從 PDF 內容找科目 keyword（全文搜尋，不限 300 字）"""
    if not text:
        return None
    clean = re.sub(r"\s+", "", text)
    for canon, kws in SUBJECT_KEYWORDS.items():
        for kw in kws:
            if kw in clean:
                return canon
    return None


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """極簡 YAML frontmatter 解析"""
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


def ocr_pdf(pdf_path: Path, timeout: int = 30) -> str:
    """OCR 單個 PDF：pdftoppm + tesseract"""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ppm_prefix = f"{tmpdir}/p"
            subprocess.run(
                ["pdftoppm", "-r", "150", "-f", "1", "-l", "1", "-png", str(pdf_path), ppm_prefix],
                capture_output=True, timeout=15,
            )
            for png in sorted(Path(tmpdir).glob("*.png")):
                result = subprocess.run(
                    ["tesseract", str(png), "-", "-l", "chi_tra", "--psm", "6"],
                    capture_output=True, text=True, timeout=timeout,
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass
    return ""


def main():
    log_lines = []
    log = lambda m: (log_lines.append(m), print(m, flush=True))[1]

    log(f"=== ocr_and_relocate.py ===")
    log(f"掃 {MD_ROOT}")

    # 1. 找出所有「未分科目」.md
    unclassified = sorted(MD_ROOT.rglob("未分科目/*.md"))
    log(f"未分科目總數: {len(unclassified)}")

    # 2. 先 group（學年+學期+年級+校名）— 統計已知科目
    #    從正確分類的 .md 也收集 group-subject 統計
    group_subjects = defaultdict(Counter)
    for md in MD_ROOT.rglob("*.md"):
        if "/未分科目/" in str(md):
            continue
        txt = md.read_text(encoding="utf-8", errors="replace")
        meta, _ = parse_frontmatter(txt)
        if meta.get("subject") in ("未分科目", None):
            continue
        key = (
            meta.get("year_roc", "?"),
            meta.get("semester", "?"),
            meta.get("grade_label", "?"),
            meta.get("school", "?"),
        )
        group_subjects[key][meta["subject"]] += 1

    log(f"已知 group (學年+學期+年級+校名): {len(group_subjects)}")

    # 3. 處理每個未分類
    relocated = 0
    ocr_done = 0
    group_done = 0
    still_unclassified = []
    for md in unclassified:
        txt = md.read_text(encoding="utf-8", errors="replace")
        meta, body = parse_frontmatter(txt)
        detected = None
        # 先試 body keyword（全文）
        detected = detect_subject_from_text(body)
        # body 沒抓到 → 試 group 推算
        if not detected:
            key = (
                meta.get("year_roc", "?"),
                meta.get("semester", "?"),
                meta.get("grade_label", "?"),
                meta.get("school", "?"),
            )
            grp = group_subjects.get(key)
            if grp:
                # 取最常見的科目
                most = grp.most_common(1)
                if most:
                    detected = most[0][0]
                    group_done += 1
        # 還沒抓到 → body 太短就 OCR
        if not detected and len(body) < 50:
            op = meta.get("original_path")
            if op:
                orig = ROOT / op
                if orig.exists() and orig.suffix.lower() == ".pdf":
                    ocr_text = ocr_pdf(orig)
                    if ocr_text:
                        ocr_done += 1
                        detected = detect_subject_from_text(ocr_text)
                        if detected:
                            # 把 OCR body 寫回 .md（更新 frontmatter subject + body）
                            new_meta = dict(meta)
                            new_meta["subject"] = detected
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

        if not detected:
            still_unclassified.append(str(md))
            continue

        # 4. relocate：移到正確科目目錄
        new_subject = detected
        old_path = md
        new_dir = old_path.parent.parent / new_subject
        new_dir.mkdir(parents=True, exist_ok=True)
        new_path = new_dir / old_path.name
        if new_path.exists():
            # 防覆蓋
            sha = meta.get("sha256", "00000000")[:8]
            new_path = new_dir / f"{old_path.stem}-{sha}.md"
        shutil.move(str(old_path), str(new_path))
        # 5. 更新 frontmatter subject（如果沒 OCR）
        if not (len(body) < 50 and meta.get("subject") != new_subject):
            new_meta = dict(meta)
            new_meta["subject"] = new_subject
            fm_lines = ["---"]
            for k, v in new_meta.items():
                if isinstance(v, str) and (":" in v or "\n" in v):
                    fm_lines.append(f'{k}: "{v}"')
                else:
                    fm_lines.append(f"{k}: {v}")
            fm_lines.append("---")
            # 保留 body
            new_md = "\n".join(fm_lines) + "\n\n" + body + "\n"
            new_path.write_text(new_md, encoding="utf-8")
        relocated += 1

    log(f"\n=== 結果 ===")
    log(f"移動成功: {relocated}")
    log(f"  OCR 補: {ocr_done}")
    log(f"  Group 推算: {group_done}")
    log(f"仍無法分類: {len(still_unclassified)}")
    if still_unclassified:
        log(f"  前 5 個: {still_unclassified[:5]}")
    # 寫 log
    log_path = ROOT / "exams" / "md" / "RELOCATE_LOG.md"
    log_path.write_text("\n".join(log_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
