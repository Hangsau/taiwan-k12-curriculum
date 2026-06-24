#!/usr/bin/env python3
"""
download_melances_exams.py — §16-G4：抓米蘭老師教育資訊室的全 K12 段考考古題。

來源：https://melances.com/test-bank/
每個年級（grade1-10）有 22-26 個 Google Drive 公開資料夾，按
「學科 × 版本（南一/康軒/翰林/何嘉仁）× 學期 × 階段（期中考/期末考）」組織。

授權：米蘭老師的 Drive 公開分享（無 CC 標示，當作「可下載」處理）
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import unquote, urlparse, parse_qs
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

TZ = timezone(timedelta(hours=8))
ROOT = Path(__file__).parent.parent
MELANCES = ROOT / "exams" / "melances"
MELANCES.mkdir(parents=True, exist_ok=True)

GRADES = [
    ("grade1", "https://melances.com/grade1/"),
    ("grade2", "https://melances.com/grade2/"),
    ("grade3", "https://melances.com/grade3/"),
    ("grade4", "https://melances.com/grade4/"),
    ("grade5", "https://melances.com/grade5/"),
    ("grade6", "https://melances.com/grade6/"),
    ("grade7", "https://melances.com/grade7"),
    ("grade8", "https://melances.com/grade8/"),
    ("grade9", "https://melances.com/grade9/"),
    ("grade10", "https://melances.com/grade10/"),
]


def log(msg: str):
    print(msg, flush=True)


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def fetch_grade_drive_folders(page, grade: str, url: str) -> list[dict]:
    """進 grade 頁面，抓所有 Drive folder 連結（用「科目版本學期階段」當分類依據）。"""
    page.goto(url, timeout=20000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    # 從頁面抓所有 Drive folder URL
    folders = page.eval_on_selector_all(
        "a[href*='drive.google.com/drive/folders/']",
        """els => {
            const out = [];
            for (const e of els) {
                const text = (e.innerText || '').trim();
                const href = e.href;
                // 抓 folder ID
                const m = href.match(/folders\\/([a-zA-Z0-9_-]+)/);
                if (m) {
                    out.push({text, href, folder_id: m[1]});
                }
            }
            return out;
        }"""
    )
    # 去重
    seen = set()
    unique = []
    for f in folders:
        if f["folder_id"] in seen:
            continue
        seen.add(f["folder_id"])
        unique.append(f)
    return unique


def fetch_drive_folder_files(ctx, page, folder_id: str, out_dir: Path) -> list[dict]:
    """進 Drive folder 抓所有檔案 + 下載（用 Playwright 渲染 JS 抓 file/d/）。"""
    folder_url = f"https://drive.google.com/drive/folders/{folder_id}"

    # 用 page.goto + 等 JS 渲染
    try:
        page.goto(folder_url, timeout=20000, wait_until="domcontentloaded")
        # 等 Drive SPA 渲染（JS 動態載入檔案）
        page.wait_for_timeout(5000)
        # scroll 到底觸發 lazy load
        for _ in range(3):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
    except Exception as e:
        log(f"    ERR goto: {e}")
        return []

    # 抓所有 data-id 屬性（Drive SPA 把檔案 ID 放這裡，不是 href）
    file_data = page.evaluate("""() => {
        const out = {};
        document.querySelectorAll('[data-id]').forEach(e => {
            const fid = e.getAttribute('data-id');
            // 跳過 folder ID（folder ID 是 33 chars 通常，file ID 也是 33 chars）
            // 區分方式：找包含 .pdf/.docx/.pptx 的 text 才是檔案
            const text = (e.innerText || '').trim();
            if (text && /\\.(pdf|docx?|pptx?|xlsx?)$/i.test(text.split('\\n')[0])) {
                if (!out[fid]) {
                    out[fid] = text.split('\\n')[0];  // 第一行是檔名
                }
            }
        });
        return out;
    }""")

    if not file_data:
        return []

    results = []
    out_dir.mkdir(parents=True, exist_ok=True)
    for fid, fname in file_data.items():
        # 抓根檔名（去掉多餘的 .pdf.pdf 之類）
        clean_name = re.sub(r'\.pdf\.pdf$', '.pdf', fname)
        clean_name = re.sub(r'\.docx\.docx$', '.docx', fname)
        download_url = f"https://drive.google.com/uc?export=download&id={fid}"
        try:
            resp = ctx.request.get(download_url, max_redirects=10)
            if resp.status != 200:
                continue
            ct = resp.headers.get("content-type", "")
            cd = resp.headers.get("content-disposition", "")
            ext = "bin"
            if "pdf" in ct:
                ext = "pdf"
            elif "word" in ct or "officedocument" in ct:
                ext = "docx"
            elif "presentation" in ct or "powerpoint" in ct:
                ext = "pptx"
            elif "spreadsheet" in ct or "excel" in ct:
                ext = "xlsx"
            body = resp.body()
            if not body or len(body) < 500:
                continue
            if b"<html" in body[:200].lower():
                continue
            # 從 Content-Disposition 或檔名抓
            m = re.search(r'filename\*?=["\']?([^"\';]+)', cd)
            if m:
                dl_fname = unquote(m.group(1).split("''")[-1] if "''" in m.group(1) else m.group(1))
            else:
                dl_fname = clean_name
            # 補對副檔名
            if "." not in dl_fname:
                dl_fname = f"{dl_fname}.{ext}"
            # 檔名清理（移除非法字元）
            dl_fname = re.sub(r'[\\/:*?"<>|]', '_', dl_fname)
            out = out_dir / dl_fname
            out.write_bytes(body)
            results.append({"file_id": fid, "filename": dl_fname, "size": len(body), "out": str(out.relative_to(ROOT))})
        except Exception:
            pass
        time.sleep(0.2)

    return results


def main():
    parser = argparse.ArgumentParser(description="§16-G4：抓米蘭老師 Drive 段考考古題")
    parser.add_argument("--grades", default="grade1-grade10", help="學年範圍")
    parser.add_argument("--max-folders", type=int, default=30, help="每學年最多抓幾個資料夾")
    args = parser.parse_args()

    if "-" in args.grades:
        start, end = args.grades.split("-")
        start_idx = next(i for i, (n, _) in enumerate(GRADES) if n == start)
        end_idx = next(i for i, (n, _) in enumerate(GRADES) if n == end)
        grades_list = GRADES[start_idx:end_idx + 1]
    else:
        grades_list = [(n, u) for n, u in GRADES if n in args.grades.split(",")]

    log(f"=== download_melances_exams.py ===")
    log(f"目標學年：{[n for n, _ in grades_list]}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            accept_downloads=True,
            ignore_https_errors=True,
        )
        page = ctx.new_page()

        total_files = 0
        total_size = 0
        for grade, url in grades_list:
            log(f"\n=== {grade} ===")
            try:
                folders = fetch_grade_drive_folders(page, grade, url)
                log(f"  抓到 {len(folders)} 個 Drive 資料夾")
            except Exception as e:
                log(f"  ERR fetch_grade: {e}")
                continue

            grade_dir = MELANCES / grade

            for fi, folder in enumerate(folders[:args.max_folders]):
                fid = folder["folder_id"]
                # 構造學科+版本+學期+階段的子目錄名
                # 從 folder 文字猜
                sub_name = re.sub(r'[\\/:*?"<>|]', '_', folder["text"][:50]).strip() or fid
                sub_dir = grade_dir / sub_name
                log(f"  [{fi+1}/{min(len(folders), args.max_folders)}] {sub_name[:40]} ({fid[:10]}...)")

                files = fetch_drive_folder_files(ctx, page, fid, sub_dir)
                if files:
                    log(f"      → {len(files)} 個檔案")
                    for f in files:
                        log(f"        ✓ {f['filename'][:40]} ({f['size']:,} bytes)")
                        total_files += 1
                        total_size += f["size"]
                else:
                    log(f"      (0 檔案)")

        browser.close()

    log(f"\n=== 完成 ===")
    log(f"總下載 {total_files} 個檔案")
    log(f"總大小 {total_size:,} bytes ({total_size/1024/1024:.1f} MB)")
    log(f"輸出：{MELANCES.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
