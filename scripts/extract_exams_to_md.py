#!/usr/bin/env python3
"""
extract_exams_to_md.py — 把所有考卷（PDF / DOCX）抽成純文字 .md 並按年級×科目歸檔。

跟 §16 index_exams.py 搭配使用：
- index_exams.py 產 INDEX.json 提供 metadata
- 本 script 用同樣的分類邏輯 + 自己擴充（ddes 學期拆解、補 metadata 欄位）+ 抽文字 + 寫 .md

產出結構：
exams/md/
├── by-grade-subject/
│   ├── 國小-1年級-國文/         # stage-grade-subject 作目錄名
│   │   ├── 108-上學期-期末考-南一-美和國小.md
│   │   ├── ...
│   ├── 國小-1年級-數學/
│   └── ...
├── by-source/
│   ├── CEEC/                    # 大考中心
│   ├── melances/                # 米蘭老師
│   └── ddes/                    # 教育部
└── EXTRACT_FAIL.json            # 失敗清單（pdftotext 失敗、.doc 跳過、xlsx 等）

每個 .md 的 frontmatter（YAML）：
---
source: CEEC | melances | ddes
year_roc: 108
stage: 國小 | 國中 | 高中
grade: 國小 1 年級
subject: 國文
semester: 上學期 | 下學期 | null
test_type: 期中考 | 期末考 | 段考 | 學測 | 指考 | 分科 | null
school: 美和國小 | null
version: 康軒 | 南一 | 翰林 | null
original_filename: ...
original_path: exams/ddes/108/上學期期末考/3E10812.docx
sha256: ...
extracted_at: 2026-06-25T...
extract_method: pdftotext | docx-stdlib | doc-skipped
license: 不明（米蘭老師 Drive，無明確授權 — 僅作 metadata 參考，不對外散佈）
---

每個 .md body：抽出的純文字試題內容（保留 layout）

設計原則：
- stdlib only（pdftotext 是外部 CLI，但已經預裝）
- 不 commit exams/md/*（太大 + license 不清 — 加 .gitignore）
- 只 commit EXTRACT_FAIL.json + INDEX.md 重跑結果
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path  # noqa: E402

# 確保 Path 用（被下面用）
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

TZ = timezone(timedelta(hours=8))
ROOT = Path(__file__).parent.parent
EXAMS = ROOT / "exams"
MD_ROOT = EXAMS / "md"
FAIL_PATH = MD_ROOT / "EXTRACT_FAIL.json"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

# 學段年級中文 label
STAGE_LABEL = {"國小": "國小", "國中": "國中", "高中": "高中"}
def safe_filename(name: str) -> str:
    """檔名如果是 BIG5 / GBK mojibake（被當 UTF-8 解碼的亂碼），嘗試 reverse 回正確 UTF-8。
    米蘭老師 Drive 來源的檔案常常是某種編碼被誤存：raw bytes 是 UTF-8 encoded Latin-1 chars。
    嘗試多條 decode 路徑找含 CJK 的版本。
    """
    # 嘗試 1：直接 decode raw bytes 為 GBK（即使解出來是簡體 mojibake 也保留 raw 結構）
    try:
        raw_bytes = name.encode("utf-8", errors="strict")
        decoded = raw_bytes.decode("gbk", errors="strict")
        if any("一" <= c <= "鿿" for c in decoded):
            return decoded
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    # 嘗試 2：latin-1 → big5
    try:
        decoded = name.encode("latin-1", errors="strict").decode("big5", errors="strict")
        if any("一" <= c <= "鿿" for c in decoded):
            return decoded
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    # 嘗試 3：cp1252 → big5
    try:
        decoded = name.encode("cp1252", errors="strict").decode("big5", errors="strict")
        if any("一" <= c <= "鿿" for c in decoded):
            return decoded
    except (UnicodeEncodeError, UnicodeDecodeError, LookupError):
        pass
    return name


SUBJECT_CANONICAL = {
    "國文": "國文", "國語": "國文", "國綜": "國文", "國寫": "國文", "chinese": "國文",
    "英文": "英文", "英語": "英文", "english": "英文", "eng": "英文",
    "數學": "數學", "數甲": "數學", "數乙": "數學", "math": "數學",
    "社會": "社會", "歷史": "社會", "地理": "社會", "公民": "社會", "social": "社會",
    "自然": "自然科學", "自然科學": "自然科學", "理化": "自然科學",
    "物理": "自然科學", "化學": "自然科學", "生物": "自然科學",
    "地科": "自然科學", "地球科學": "自然科學", "science": "自然科學",
    "生活": "生活",
    "健康": "健康與體育", "體育": "健康與體育", "健體": "健康與體育", "健康與體育": "健康與體育",
}

# ddes 檔名代碼 → 科目中文
DDES_SUBJECT_CODE = {
    "C": "國文", "M": "數學", "S": "社會", "N": "自然科學",
    "H": "健康與體育", "E": "英文", "A": "自然科學",
}


def log(msg: str):
    print(msg, flush=True)


# ============================================================
# 文字抽取（3 種格式）
# ============================================================

def extract_pdf(path: Path) -> str:
    """抽 PDF 文字：用 pdftotext（穩定、timeout 控制）。
    純圖檔會回空字串（body_empty），script 會 fallback OCR。
    """
    try:
        result = subprocess.run(
            ["pdftotext", "-enc", "UTF-8", "-layout", str(path), "-"],
            capture_output=True, text=True, timeout=20,  # 短 timeout 防卡
        )
        if result.returncode == 0:
            return result.stdout
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass
    # fallback：OCR（純圖檔掃描，限時）
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ppm_prefix = f"{tmpdir}/p"
            subprocess.run(
                ["pdftoppm", "-r", "150", "-f", "1", "-l", "1", "-png", str(path), ppm_prefix],
                capture_output=True, timeout=15,
            )
            for png in sorted(Path(tmpdir).glob("*.png")):
                result = subprocess.run(
                    ["tesseract", str(png), "-", "-l", "chi_tra", "--psm", "6"],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass
    raise RuntimeError(f"pdf extraction failed: {path.name}")


def extract_docx(path: Path) -> str:
    """Python stdlib 抽 .docx（zipfile + ElementTree）。"""
    text_lines = []
    try:
        with zipfile.ZipFile(path) as z:
            with z.open("word/document.xml") as x:
                tree = ET.parse(x)
                for p in tree.getroot().iter(f"{{{W_NS}}}p"):
                    line = "".join(t.text or "" for t in p.iter(f"{{{W_NS}}}t"))
                    text_lines.append(line)
        return "\n".join(text_lines)
    except Exception as e:
        raise RuntimeError(f"docx stdlib failed: {e}")


def extract_doc(path: Path) -> str:
    """舊版 .doc binary 格式 — 用 antiword 或 catdoc（Arch 官方套件）。"""
    # 優先 antiword（PDF/Word → text）
    for cmd in [["antiword", str(path)], ["catdoc", str(path)]]:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
        except FileNotFoundError:
            continue
        except Exception as e:
            last_err = str(e)
    raise RuntimeError(f"doc-skipped: antiword+catdoc 都失敗，{locals().get('last_err', 'binary not in PATH')}")


def extract_xlsx(path: Path) -> str:
    """.xlsx 不是考卷內容（只是 3 個檔），跳過。"""
    raise RuntimeError("xlsx-skipped: 不是考卷內容")


EXTRACTORS = {
    "pdf": extract_pdf,
    "docx": extract_docx,
    "doc": extract_doc,
    "xlsx": extract_xlsx,
}


# ============================================================
# Metadata 解析
# ============================================================

def decode_ddes_filename(name: str) -> dict | None:
    """解析 ddes 編碼：<年級><科目><學年><學期碼><考試碼>[variant]
    編碼規則（依教育部大墩國小公開資料）：
      - 學期碼：1=上學期, 2=下學期
      - 考試碼：1=期中考, 2=期末考
    例 3E10812.doc → 3年級英文 108學年 上學期 期末考
       5C10811.doc → 5年級國文 108學年 上學期 期中考
       6C11411A.doc → 6年級國文 114學年 上學期 期中考 A卷
       5N10922.doc → 5年級自然 109學年 下學期 期末考
    """
    m = re.match(r"^(\d)([A-Z])(\d{3})(\d)(\d)([A-Z]?)\.(doc|docx|pdf)$", name)
    if not m:
        # 容錯：原本以為 month 是 2 位數，但實際是學期+考試各 1 位
        return None
    grade, subj_code, year, sem_code, test_code, variant, ext = m.groups()
    semester = "上學期" if sem_code == "1" else "下學期"
    test_type = "期中考" if test_code == "1" else "期末考"
    return {
        "grade_num": int(grade),
        "subject": DDES_SUBJECT_CODE.get(subj_code, "?"),
        "year_roc": year,
        "semester": semester,
        "test_type": test_type,
        "variant": variant or None,
        "source": "ddes",
    }


SUBJECT_KEYWORDS = {
    "國文": ["國文科", "國語文", "國語科", "國文", "國語", "國綜", "國寫"],
    "英文": ["英文科", "英語科", "英文", "英語"],
    "數學": ["數學科", "數學"],
    "自然科學": ["自然科", "自然科學", "自然與生活科技", "理化", "物理科", "化學科", "生物科", "地科"],
    "社會": ["社會科", "社會", "歷史科", "地理科", "公民科"],
    "健康與體育": ["健康與體育", "體育科", "健體", "健康教育"],
}


def detect_subject_from_text(text: str) -> str | None:
    """從 PDF 內容找科目 keyword（國文科 / 英文科 / 數學科 / 等）。
    移除空白/換行後搜尋，避免「國 中 文」這種 OCR 結果干擾。
    """
    if not text:
        return None
    # 清掉所有空白
    clean = re.sub(r"\s+", "", text)
    # 優先匹配較長的 keyword（如「國文科」比「國文」精準）
    for canon in ["自然科學", "健康與體育", "國文", "英文", "數學", "社會"]:
        for kw in SUBJECT_KEYWORDS[canon]:
            if kw in clean:
                return canon
    return None


def parse_melances_path(rel: str) -> dict:
    """從米蘭老師路徑解析年級 / 科目 / 學期 / 學年 / 版本 / 校名。
    路徑樣式: melances/grade3/期末考/<校名> ... <年級> ... <學年> <學期> ... <科目> ... <版本> ...pdf
    BIG5 編碼的檔名我們只取 path 結構跟檔名的英數部分。
    """
    info = {"source": "melances"}
    m = re.search(r"grade(\d+)", rel)
    if m:
        gn = int(m.group(1))
        info["grade_num"] = gn
        info["stage"] = "國小" if gn <= 6 else ("國中" if gn <= 9 else "高中")
        info["grade_label"] = (
            f"國小 {gn} 年級" if gn <= 6
            else f"國中 {gn - 6} 年級" if gn <= 9
            else "高中 1 年級"
        )
    # 學年 / 學期 / 學期考試 從路徑段
    parts = rel.split("/")
    for seg in parts:
        if seg in ("上學期", "下學期"):
            info["semester"] = seg
        elif seg in ("期中考", "期末考"):
            info["test_type"] = seg
        elif seg in ("第一次段考", "第二次段考", "第三次段考"):
            info["test_type"] = seg
    # 從檔名抓 ROC 學年（3 位數）
    fname = Path(rel).name
    fname_decoded = safe_filename(fname)
    year_m = re.search(r"(10[8-9]|11[0-5])", fname_decoded)
    if year_m:
        info["year_roc"] = year_m.group(1)
    # 從檔名抓科目（看哪個 SUBJECT_CANONICAL key 出現在 decoded 檔名）
    # 也試 ASCII path 內 subject 標記（如「math」、「english」）
    for canon in SUBJECT_CANONICAL.values():
        for kw in [canon, canon.replace("科學", "")]:
            if kw and kw in fname_decoded:
                info["subject"] = canon
                break
        if "subject" in info:
            break
    # 從路徑段「math」「english」抓
    if "subject" not in info:
        if "/math" in rel.lower() or "math" in fname.lower():
            info["subject"] = "數學"
        elif "/english" in rel.lower() or "english" in fname.lower() or "eng" in fname.lower():
            info["subject"] = "英文"
    # 從 PDF 內容抓科目（最可靠：fitz/pdftotext/OCR 抽出後是 UTF-8 中文）
    if "subject" not in info:
        # 從路徑拿 content（透過 classify_file 傳入 — 見 classify_file 那邊）
        pass  # 實際 detect 在 classify_file 內跑
    return info
    # 抓版本
    version_kws = ["南一", "康軒", "翰林", "何嘉仁", "龍騰", "泰宇", "全華", "五南", "旗立", "佳音"]
    for v in version_kws:
        if v in fname_decoded:
            info["version"] = v
            break
    # 抓校名
    school_m = re.search(r"(?:[縣市]立)?([一-鿿]{2,5})(?:國小|國中|高中)", fname_decoded)
    if school_m:
        info["school"] = f"{school_m.group(0)}"
    # 抓校名 - 第二輪：更精準
    if "school" not in info:
        school_m2 = re.search(r"([一-鿿]{2,5})(?:國小|國中|高中)", fname_decoded)
        if school_m2:
            info["school"] = school_m2.group(0)
    return info


def parse_ceec_filename(name: str) -> dict:
    """CEEC 大考中心：108-國寫試卷定稿.pdf / 110-英文.pdf / 111-數學a.pdf
    """
    info = {"source": "CEEC", "stage": "高中", "grade_label": "高中"}
    m = re.match(r"^(\d{2,3})[-_](.+)\.(pdf|docx)$", name)
    if m:
        info["year_roc"] = m.group(1)
        subj_part = m.group(2)
        # 反覆去「試卷定稿 / 試卷 / 試題 / 定稿 / docx / doc / draft / 科」等後綴直到不再 match
        ceec_strip_re = re.compile(r"(試卷定稿|試卷|試題|定稿|docx|docx檔|doc|draft|科)$")
        prev = None
        while prev != subj_part:
            prev = subj_part
            subj_part = ceec_strip_re.sub("", subj_part)
        # 處理「a / b / 甲 / 乙」之類的 variant
        variant_m = re.search(r"([ab甲乙])$", subj_part)
        if variant_m:
            info["variant"] = variant_m.group(1)
            subj_part = subj_part[:-1]
        subj_clean = subj_part.strip()
        # 先查表，查不到用更寬鬆的 keyword 匹配（國文選擇題 → 國文、公民與社會 → 社會 等）
        if subj_clean in SUBJECT_CANONICAL:
            info["subject"] = SUBJECT_CANONICAL[subj_clean]
        else:
            ceec_keyword_map = [
                ("國文", ["國文", "國語", "國綜", "國寫", "國文選擇題"]),
                ("英文", ["英文", "英語", "eng"]),
                ("數學", ["數學", "數甲", "數乙", "數a", "數b"]),
                ("自然科學", ["自然", "理化", "物理", "化學", "生物", "地科", "地球科學"]),
                ("社會", ["社會", "歷史", "地理", "公民"]),
                ("健康與體育", ["健康", "體育", "健體"]),
            ]
            info["subject"] = subj_clean  # fallback
            for canon, kws in ceec_keyword_map:
                if any(kw in subj_clean for kw in kws):
                    info["subject"] = canon
                    break
        # CEEC 沒明顯 test_type 時預設學測（CEEC 高中試題就是學測/指考/分科）
        if "test_type" not in info and 108 <= int(info.get("year_roc", 0)) <= 115:
            info["test_type"] = "學測"
        # 學測/指考/分科
        if "分科" in name or "分科" in subj_part:
            info["test_type"] = "分科"
        elif "指考" in name:
            info["test_type"] = "指考"
        elif "學測" in name or "國寫" in name or "選擇題" in name:
            info["test_type"] = "學測"
    return info


def classify_file(path: Path) -> dict:
    """綜合分類一個考卷檔案。"""
    rel = str(path.relative_to(ROOT))
    name = path.name
    size = path.stat().st_size if path.exists() else 0
    ext = path.suffix.lower().lstrip(".")
    sha256 = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

    info = {
        "path": rel,
        "filename": name,
        "size": size,
        "ext": ext,
        "sha256": sha256,
    }

    # 來源
    if "ddes" in rel:
        ddes = decode_ddes_filename(name)
        if ddes:
            info.update(ddes)
            gn = info["grade_num"]
            info["stage"] = "國小" if gn <= 6 else ("國中" if gn <= 9 else "高中")
            info["grade_label"] = (
                f"國小 {gn} 年級" if gn <= 6
                else f"國中 {gn - 6} 年級" if gn <= 9
                else "高中"
            )
            info["test_type"] = info.get("test_type") or "?"
            info["source"] = "ddes"
            info["school"] = "大墩國小"  # ddes 全是台中南屯大墩國小
        else:
            info["source"] = "ddes-未解析"
    elif "melances" in rel:
        info.update(parse_melances_path(rel))
    elif path.parent.name == "exams" and re.match(r"^\d{2,3}[-_].+\.(pdf|docx)$", name):
        info.update(parse_ceec_filename(name))
    else:
        info["source"] = "其他"

    # 補 license / extract method
    info["license"] = (
        "不明（米蘭老師 Drive，無明確授權 — 僅作 metadata 參考，不對外散佈）"
        if info.get("source") == "melances"
        else "教育部公開資料"
        if info.get("source") == "ddes"
        else "CEEC 大考中心（依官方授權）"
        if info.get("source") == "CEEC"
        else "不明"
    )
    info["extracted_at"] = datetime.now(TZ).isoformat()

    # melances BIG5 mojibake fallback：把 GBK decoded str 存 frontmatter
    if info.get("source") == "melances":
        info["original_filename_raw"] = safe_filename(name)

    # clean empty
    info = {k: v for k, v in info.items() if v is not None and v != ""}
    return info


# ============================================================
# .md 輸出
# ============================================================

def build_frontmatter(info: dict) -> str:
    """產 YAML frontmatter。"""
    # 預設值：subject / grade_label / stage 缺失時填「未分」
    info = dict(info)  # copy
    if "subject" not in info or not info["subject"]:
        info["subject"] = "未分科目"
    if "grade_label" not in info or not info["grade_label"]:
        info["grade_label"] = "未分年級"
    if "stage" not in info or not info["stage"]:
        info["stage"] = "未分"
    keys_order = [
        "source", "year_roc", "stage", "grade_label", "grade_num",
        "subject", "semester", "test_type", "variant",
        "school", "version",
        "original_filename", "original_filename_raw", "original_path", "sha256",
        "size", "ext",
        "license", "extracted_at",
    ]
    lines = ["---"]
    for k in keys_order:
        if k in info and k not in ("filename",):
            v = info[k]
            if isinstance(v, str) and (":" in v or "\n" in v or v.startswith("[") or v.startswith("{") or v.startswith("'") or v.startswith("\"")):
                v_escaped = v.replace('"', '\\"')
                lines.append(f'{k}: "{v_escaped}"')
            else:
                lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def build_output_path(info: dict) -> Path:
    """決定 .md 輸出路徑：by-grade-subject/<stage>-<grade>/<subject>/<stem>-<sha8>.md
    加 sha256 短碼避免同名覆蓋（melances 同年級同考試類型檔案很多）
    """
    stage = info.get("stage") or "未分"
    grade = info.get("grade_label") or "未分年級"
    subject = info.get("subject") or "未分科目"
    # 移除檔名禁用字元
    safe = lambda s: re.sub(r'[\\/:*?"<>|\s]', '_', str(s))
    folder = MD_ROOT / "by-grade-subject" / f"{safe(stage)}-{safe(grade)}" / safe(subject)
    # 檔名 stem
    parts = []
    if info.get("year_roc"):
        parts.append(info["year_roc"])
    if info.get("semester"):
        parts.append(info["semester"])
    if info.get("test_type"):
        parts.append(info["test_type"])
    if info.get("variant"):
        parts.append(info["variant"])
    if info.get("version"):
        parts.append(info["version"])
    if info.get("school"):
        parts.append(info["school"])
    if info.get("source"):
        parts.append(f"[{info['source']}]")
    stem = "-".join(parts) if parts else "unknown"
    # 加 sha8 短碼保證唯一性
    sha8 = (info.get("sha256") or "00000000")[:8]
    return folder / f"{stem}-{sha8}.md"


def extract_text(info: dict) -> str:
    """依副檔名抽文字。"""
    path = ROOT / info["path"]
    ext = info["ext"]
    extractor = EXTRACTORS.get(ext)
    if not extractor:
        raise RuntimeError(f"unsupported-ext: {ext}")
    return extractor(path)


def write_md(info: dict, body: str) -> Path:
    """寫 .md 到 by-grade-subject/。若檔案已存在（sha256 重複），跳過避免覆蓋。"""
    out_path = build_output_path(info)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    info["original_filename"] = info.get("filename") or Path(info["path"]).name
    info["original_path"] = info["path"]
    front = build_frontmatter(info)
    md_content = f"{front}\n\n{body}\n"
    # 防覆蓋：若檔案已存在就跳過
    if out_path.exists():
        # 用 sha256 + index 強制唯一
        sha = info.get("sha256", "00000000")[:12]
        out_path = out_path.parent / f"{out_path.stem}-{sha[:4]}.md"
    out_path.write_text(md_content, encoding="utf-8")
    return out_path


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="把考卷抽成 .md 並按年級×科目歸檔")
    parser.add_argument("--limit", type=int, default=0, help="只處理前 N 個（測試用）")
    parser.add_argument("--dry-run", action="store_true", help="不寫檔，只統計")
    args = parser.parse_args()

    if not EXAMS.exists():
        log(f"ERR: {EXAMS} 不存在")
        return 1

    MD_ROOT.mkdir(parents=True, exist_ok=True)

    # 掃所有 PDF / DOCX / DOC / XLSX
    all_files = []
    for ext in ["pdf", "docx", "doc", "xlsx"]:
        all_files.extend(EXAMS.rglob(f"*.{ext}"))
    all_files = sorted(all_files)
    if args.limit:
        all_files = all_files[:args.limit]

    log(f"=== extract_exams_to_md.py ===")
    log(f"掃到 {len(all_files)} 個檔案")
    if args.dry_run:
        log("(dry-run 不寫檔)")

    success = []
    fail = []
    by_target_dir = defaultdict(int)

    for i, path in enumerate(all_files, 1):
        try:
            info = classify_file(path)
            if args.dry_run:
                target = build_output_path(info)
                by_target_dir[str(target.parent.relative_to(MD_ROOT))] += 1
                success.append(info)
                continue
            body = extract_text(info)
            # 用 body 內容補抓 subject（melances BIG5 mojibake 救回用）
            if (not info.get("subject") or info["subject"] == "未分科目") and body:
                detected = detect_subject_from_text(body)
                if detected:
                    info["subject"] = detected
            out = write_md(info, body)
            info["output_path"] = str(out.relative_to(ROOT))
            by_target_dir[str(out.parent.relative_to(MD_ROOT))] += 1
            success.append(info)
        except Exception as e:
            fail.append({
                "path": str(path.relative_to(ROOT)),
                "reason": str(e),
            })

        if i % 200 == 0 or i == len(all_files):
            log(f"  [{i}/{len(all_files)}] success={len(success)} fail={len(fail)}")

    log(f"\n=== 完成 ===")
    log(f"成功：{len(success)} 個")
    log(f"失敗：{len(fail)} 個")

    # 寫失敗清單
    if fail and not args.dry_run:
        FAIL_PATH.write_text(json.dumps({
            "generated_at": datetime.now(TZ).isoformat(),
            "total": len(all_files),
            "success": len(success),
            "fail_count": len(fail),
            "fail": fail,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"失敗清單寫到 {FAIL_PATH.relative_to(ROOT)}")

    # 分佈
    log(f"\n=== 目標目錄分佈（top 20）===")
    for d, n in sorted(by_target_dir.items(), key=lambda x: -x[1])[:20]:
        log(f"  {n:>5}  {d}")

    log(f"\n=== 失敗原因分佈 ===")
    fail_reasons = defaultdict(int)
    for f in fail:
        reason = f["reason"].split(":")[0] if ":" in f["reason"] else f["reason"]
        fail_reasons[reason] += 1
    for r, n in sorted(fail_reasons.items(), key=lambda x: -x[1]):
        log(f"  {n:>5}  {r}")

    return 0 if not fail else 0  # fail 不擋 exit code


if __name__ == "__main__":
    sys.exit(main())
